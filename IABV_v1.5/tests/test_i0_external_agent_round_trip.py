"""I0 External Agent Round Trip Experiment

Demonstrates:
IABV → authorized external API invocation → real Devin session → real execution → result → independent observation → verification

This is the minimum experiment to prove IABV can invoke an external agent, receive its result, and independently verify the effect occurred.

Experiment constraints:
- No MCP client implementation
- No multi-agent orchestration
- No I1/I2
- L5 evidence remains untouched
- Isolated branch/worktree/evidence namespace
"""

import hashlib
import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.bootstrap import _resolve_devin_api_key
from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


class I0ExperimentContext:
    """Manages I0 experiment workspace and provenance."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.experiment_id = f"i0_experiment_{int(time.time())}"
        self.task_id = str(uuid.uuid4())
        self.authorization_id = str(uuid.uuid4())
        self.invocation_id = str(uuid.uuid4())
        self.attempt_id = str(uuid.uuid4())
        self.result_id = str(uuid.uuid4())
        
        # Create isolated experimental workspace
        self.experiment_workspace = workspace_root / "data" / "i0_experiments" / self.experiment_id
        self.experiment_workspace.mkdir(parents=True, exist_ok=True)
        
        # Provenance data
        self.provenance = {
            "experiment_id": self.experiment_id,
            "task_id": self.task_id,
            "authorization_id": self.authorization_id,
            "invocation_id": self.invocation_id,
            "attempt_id": self.attempt_id,
            "result_id": self.result_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace": str(self.experiment_workspace),
        }

    def capture_git_provenance(self) -> dict[str, Any]:
        """Capture Git provenance during execution."""
        import subprocess
        
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.workspace_root,
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            head = "UNKNOWN"
        
        try:
            parent = subprocess.check_output(
                ["git", "rev-parse", "HEAD^"],
                cwd=self.workspace_root,
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            parent = "UNKNOWN"
        
        try:
            tree = subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=self.workspace_root,
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            tree = "UNKNOWN"
        
        try:
            status = subprocess.check_output(
                ["git", "status", "--short"],
                cwd=self.workspace_root,
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            status = "UNKNOWN"
        
        return {
            "tested_head": head,
            "parent": parent,
            "tree_sha": tree,
            "worktree_status": status,
        }

    def cleanup(self):
        """Remove experimental workspace after verification."""
        if self.experiment_workspace.exists():
            shutil.rmtree(self.experiment_workspace)


def generate_nonce() -> str:
    """Generate a unique nonce for the experimental task."""
    return f"i0_nonce_{uuid.uuid4().hex[:16]}_{int(time.time())}"


def test_i0_external_agent_round_trip():
    """
    I0: Prove IABV can invoke external agent, receive result, and independently verify effect.
    
    Experimental chain:
    1. IABV creates task with nonce
    2. IABV authorizes external API invocation
    3. IABV invokes Devin API to create session
    4. Devin executes with real external agent
    5. IABV receives result
    6. IABV independently observes effect (filesystem)
    7. IABV verifies effect matches nonce
    """
    
    # Setup
    workspace_root = Path(__file__).parent.parent
    context = I0ExperimentContext(workspace_root)
    
    try:
        # Capture Git provenance before execution
        git_provenance = context.provenance.update(context.capture_git_provenance())
        
        # Generate experimental nonce
        nonce = generate_nonce()
        target_file = context.experiment_workspace / "i0_artifact.txt"
        
        # Verify API key available
        # Explicitly check all possible env vars for I0 experiment
        api_key_candidates = [
            os.environ.get('DEVIN_API_KEY_IABV', ''),
            os.environ.get('IABV_DEVIN_API_KEY', ''),
            os.environ.get('DEVIN_API_KEY', ''),
        ]
        api_key = next((k for k in api_key_candidates if k.strip()), '')
        assert api_key, "DEVIN_API_KEY must be available for I0 experiment"
        
        # Create Devin API adapter
        adapter = DevinApiToolAdapter(
            api_key=api_key,
            timeout_seconds=120.0,
            poll_interval_seconds=5.0,
        )
        
        # Create tool card for external agent
        card = ToolCard(
            tool_id="devin_api",
            title="Devin API",
            tool_type=ToolType.MCP_CLIENT,
            adapter_key="devin",
            available=True,
        )
        
        # Create experimental task
        task = ToolTask(
            tool_id="devin_api",
            title="I0 External Agent Round Trip",
            task_id=context.task_id,
            objective=f"Create a file at {target_file} containing exactly this nonce: {nonce}. "
                     f"Do not modify any other files. This is an isolated experimental workspace.",
            metadata={
                "authorization_id": context.authorization_id,
                "invocation_id": context.invocation_id,
                "attempt_id": context.attempt_id,
                "nonce": nonce,
                "target_file": str(target_file),
                "experiment_id": context.experiment_id,
            },
        )
        
        # Execute external invocation
        context.provenance["invoked_at"] = datetime.now(timezone.utc).isoformat()
        
        result = adapter.run(card, task, sandbox=False)
        
        context.provenance["completed_at"] = datetime.now(timezone.utc).isoformat()
        context.provenance["devin_result"] = {
            "success": result.get("success"),
            "output_text": result.get("output_text", "")[:500],  # Truncate for evidence
            "error_message": result.get("error_message", "")[:500],
            "execution_ms": result.get("execution_ms"),
        }
        
        # Verify invocation succeeded
        assert result.get("success"), f"External invocation failed: {result.get('error_message')}"
        
        # Capture session identity if available
        session_id = result.get("metadata", {}).get("session_id", "UNKNOWN")
        context.provenance["devin_session_id"] = session_id
        
        # INDEPENDENT OBSERVATION: Check filesystem independently of Devin response
        context.provenance["verified_at"] = datetime.now(timezone.utc).isoformat()
        
        independent_observation = {
            "file_exists": target_file.exists(),
            "file_size_bytes": target_file.stat().st_size if target_file.exists() else 0,
        }
        
        if target_file.exists():
            file_content = target_file.read_text()
            independent_observation["file_content"] = file_content
            independent_observation["file_sha256"] = hashlib.sha256(file_content.encode()).hexdigest()
            independent_observation["nonce_present"] = nonce in file_content
        else:
            independent_observation["file_content"] = None
            independent_observation["file_sha256"] = None
            independent_observation["nonce_present"] = False
        
        context.provenance["independent_observation"] = independent_observation
        
        # VERIFICATION: Effect must be independently observable
        assert independent_observation["file_exists"], "Target file was not created"
        assert independent_observation["nonce_present"], f"Nonce {nonce} not found in file content"
        
        # Final verification status
        verification_status = "VERIFIED" if (
            independent_observation["file_exists"] and
            independent_observation["nonce_present"]
        ) else "FAILED"
        
        context.provenance["verification_status"] = verification_status
        
        # Save evidence artifact
        evidence_file = context.experiment_workspace / "i0_evidence.json"
        with open(evidence_file, "w") as f:
            json.dump(context.provenance, f, indent=2, default=str)
        
        print(f"\n=== I0 EXPERIMENT SUCCESS ===")
        print(f"Experiment ID: {context.experiment_id}")
        print(f"Task ID: {context.task_id}")
        print(f"Invocation ID: {context.invocation_id}")
        print(f"Devin Session ID: {session_id}")
        print(f"Target File: {target_file}")
        print(f"File Exists: {independent_observation['file_exists']}")
        print(f"Nonce Present: {independent_observation['nonce_present']}")
        print(f"Verification Status: {verification_status}")
        print(f"Evidence saved to: {evidence_file}")
        
        # Critical assertions for I0 closure
        assert verification_status == "VERIFIED", "I0 verification failed"
        assert session_id != "UNKNOWN", "Devin session ID not captured"
        
    finally:
        # Cleanup experimental workspace (evidence already saved)
        context.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-s"])
