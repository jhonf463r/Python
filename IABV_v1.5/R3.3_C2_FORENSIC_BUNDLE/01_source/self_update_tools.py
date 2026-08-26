"""MCP tools for autonomous self-modification.

Registers write-capable tools that allow the program to:
- Write/create files in its own workspace
- Apply text patches to existing files
- Commit and push changes to GitHub

This module makes the program 100% autonomous: it can detect issues
(via gpu_metacognition_check, self_examination, etc.) AND fix them
(via write_repo_file, apply_text_patch, git_commit_and_push).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# C-2: Import canonical authority components
try:
    from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest
except ImportError:
    CapabilityActionBridge = None
    ActionRequest = None


# ============================================================================
# Core self-update functions (extracted for testing)
# ============================================================================

def _safe_path(workspace_root: Path, relative_path: str) -> Path | None:
    """Resolve and validate a relative path within the workspace."""
    resolved = (workspace_root / relative_path).resolve()
    if not resolved.is_relative_to(workspace_root.resolve()):
        return None  # directory traversal attempt
    return resolved


def write_repo_file_impl(
    workspace_root: Path,
    relative_path: str,
    content: str,
    create_dirs: bool = True,
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
    lease_id: str | None = None,
    execution_id: str | None = None,
) -> dict[str, Any]:
    """Core implementation of write_repo_file (extracted for testing)."""
    # C-2: Canonical authority check - REJECT if authority unavailable
    if not capability_action_bridge:
        return {"status": "error", "detail": "Authorization denied: capability_action_bridge required for file write"}
    
    if ActionRequest is None:
        # ActionRequest not available - fail closed
        return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
    
    # C-2-CRIT-2: Use correct ActionRequest contract
    # In production, lease_id and execution_id must come from genuine capability context
    # For testing, they can be provided as parameters
    if lease_id is None or execution_id is None:
        return {"status": "error", "detail": "Authorization denied: lease_id and execution_id required from capability context"}
    
    action_request = ActionRequest(
        lease_id=lease_id,
        execution_id=execution_id,
        action='WRITE_REPOSITORY_FILE',
        target=f'file:{relative_path}',
        action_context={'requested_scope': 'self_update'},
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.authorized:
        return {"status": "error", "detail": f"Authorization denied: {auth_result.error or 'capability required for file write'}"}
    
    if governance_fn:
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=False,
        )
        if block is not None:
            return block

    target = _safe_path(workspace_root, relative_path)
    if target is None:
        return {"status": "error", "detail": "path escapes workspace (directory traversal)"}

    # Reject sensitive paths (normalize to forward slashes for Windows compat)
    sensitive = ['.git/config', '.git/hooks', '.env', 'secrets']
    target_str = str(target).replace('\\', '/')
    for s in sensitive:
        if s in target_str:
            return {"status": "error", "detail": f"cannot write to sensitive path containing '{s}'"}

    try:
        if create_dirs:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("write_repo_file: wrote %d bytes to %s", len(content), relative_path)
        return {
            "status": "ok",
            "path": relative_path,
            "bytes_written": len(content),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def apply_text_patch_impl(
    workspace_root: Path,
    relative_path: str,
    old_text: str,
    new_text: str,
    description: str = "",
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
    lease_id: str | None = None,
    execution_id: str | None = None,
) -> dict[str, Any]:
    """Core implementation of apply_text_patch (extracted for testing)."""
    # C-2: Canonical authority check - REJECT if authority unavailable
    if not capability_action_bridge:
        return {"status": "error", "detail": "Authorization denied: capability_action_bridge required for patch application"}
    
    if ActionRequest is None:
        return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
    
    # C-2-CRIT-2: Use correct ActionRequest contract
    # In production, lease_id and execution_id must come from genuine capability context
    # For testing, they can be provided as parameters
    if lease_id is None or execution_id is None:
        return {"status": "error", "detail": "Authorization denied: lease_id and execution_id required from capability context"}
    
    action_request = ActionRequest(
        lease_id=lease_id,
        execution_id=execution_id,
        action='APPLY_PATCH',
        target=f'file:{relative_path}',
        action_context={'requested_scope': 'self_update'},
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.authorized:
        return {"status": "error", "detail": f"Authorization denied: {auth_result.error or 'capability required for patch application'}"}
    
    if governance_fn:
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=False,
        )
        if block is not None:
            return block

    target = _safe_path(workspace_root, relative_path)
    if target is None:
        return {"status": "error", "detail": "path escapes workspace (directory traversal)"}

    # Reject sensitive paths
    sensitive = ['.git/config', '.git/hooks', '.env', 'secrets']
    target_str = str(target).replace('\\', '/')
    for s in sensitive:
        if s in target_str:
            return {"status": "error", "detail": f"cannot patch sensitive path containing '{s}'"}

    if not target.exists():
        return {"status": "error", "detail": "file does not exist"}

    try:
        current_content = target.read_text(encoding="utf-8")
        if old_text not in current_content:
            return {"status": "error", "detail": "old_text not found in file"}

        patched_content = current_content.replace(old_text, new_text)
        replacements = current_content.count(old_text)
        target.write_text(patched_content, encoding="utf-8")
        logger.info("apply_text_patch: %d replacements in %s", replacements, relative_path)
        return {
            "status": "ok",
            "path": relative_path,
            "replacements_made": replacements,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def git_commit_and_push_impl(
    workspace_root: Path,
    message: str,
    push: bool = False,
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
    lease_id: str | None = None,
    execution_id: str | None = None,
) -> dict[str, Any]:
    """Core implementation of git_commit_and_push (extracted for testing)."""
    # C-2: Canonical authority check - REJECT if authority unavailable
    if not capability_action_bridge:
        return {"status": "error", "detail": "Authorization denied: capability_action_bridge required for git commit"}
    
    if ActionRequest is None:
        return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
    
    # C-2-CRIT-2: Use correct ActionRequest contract
    # In production, lease_id and execution_id must come from genuine capability context
    # For testing, they can be provided as parameters
    if lease_id is None or execution_id is None:
        return {"status": "error", "detail": "Authorization denied: lease_id and execution_id required from capability context"}
    
    # C-2: Canonical authority check for commit
    action_request = ActionRequest(
        lease_id=lease_id,
        execution_id=execution_id,
        action='GIT_COMMIT',
        target='git:workspace',
        action_context={'requested_scope': 'self_update'},
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.authorized:
        return {"status": "error", "detail": f"Authorization denied: {auth_result.error or 'capability required for git commit'}"}
    
    # C-2: Canonical authority check for push
    if push:
        action_request = ActionRequest(
            lease_id=lease_id,
            execution_id=execution_id,
            action='GIT_PUSH',
            target='git:workspace',
            action_context={'requested_scope': 'self_update'},
        )
        auth_result = capability_action_bridge.authorize_action(action_request)
        if not auth_result.authorized:
            return {"status": "error", "detail": f"Authorization denied: {auth_result.error or 'capability required for git push'}"}
    
    if governance_fn:
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=True if push else False,
        )
        if block is not None:
            return block

    if len(message) < 5:
        return {"status": "error", "detail": "commit message too short (min 5 chars)"}

    try:
        # Add all changes
        add_result = subprocess.run(
            ['git', 'add', '-A'],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if add_result.returncode != 0:
            return {"status": "error", "detail": f"git add failed: {add_result.stderr}"}

        # Commit
        commit_result = subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if commit_result.returncode != 0:
            if "nothing to commit" in commit_result.stderr or "nothing added to commit" in commit_result.stdout:
                return {"status": "ok", "detail": "nothing to commit"}
            return {"status": "error", "detail": f"git commit failed: {commit_result.stderr}"}

        # Get commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = hash_result.stdout.strip()

        # Get branch name
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=True,
        )
        branch_name = branch_result.stdout.strip()

        result = {
            "status": "ok",
            "commit_hash": commit_hash,
            "branch": branch_name,
            "message": message,
        }

        # Push if requested
        if push:
            push_result = subprocess.run(
                ['git', 'push'],
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if push_result.returncode != 0:
                return {"status": "error", "detail": f"git push failed: {push_result.stderr}"}
            result["pushed"] = True

        logger.info("git_commit_and_push: %s on %s", commit_hash[:8], branch_name)
        return result

    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ============================================================================
# MCP Registration
# ============================================================================

def register_self_update_tools(mcp: Any, workspace_root_fn: Any, governance_fn: Any, to_jsonable_fn: Any, capability_action_bridge: Any = None) -> int:
    """Register write-capable tools on the MCP server.

    Args:
        mcp: The MCP FastMCP instance.
        workspace_root_fn: Callable that returns the workspace root Path.
        governance_fn: Callable for governance gate checks.
        to_jsonable_fn: Callable to convert results to JSON-safe dicts.
        capability_action_bridge: Canonical P0.213 authority bridge (C-2 integration).

    Returns:
        Number of tools registered.
    """
    count = 0

    def _safe_path(relative_path: str) -> Path | None:
        """Resolve and validate a relative path within the workspace."""
        ws = Path(workspace_root_fn())
        resolved = (ws / relative_path).resolve()
        if not resolved.is_relative_to(ws.resolve()):
            return None  # directory traversal attempt
        return resolved

    # -----------------------------------------------------------------
    # write_repo_file
    # -----------------------------------------------------------------
    @mcp.tool()
    def write_repo_file(
        relative_path: str,
        content: str,
        create_dirs: bool = True,
        # C2 VFINAL5: Trusted execution context parameters
        execution_id: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        """Escribe (crea o sobreescribe) un archivo en el workspace.

        Metacognicion: el programa puede crear o modificar sus propios
        archivos de codigo para auto-mejorarse.

        Args:
            relative_path: ruta relativa desde el workspace root.
            content: contenido completo del archivo.
            create_dirs: crear directorios intermedios si no existen.
            execution_id: Existing execution identifier for causal attribution.
            run_id: Existing run identifier for causal attribution.
            session_id: Session identifier for causal attribution.
            episode_id: Episode identifier for causal attribution.

        Returns:
            dict con status, path, bytes_written.
        """
        # C2 VFINAL5: Require trusted execution context for self-update
        if not execution_id or not run_id:
            return {"status": "error", "detail": "Authorization denied: missing execution context (execution_id, run_id required)"}
        
        # C2 VFINAL5: Acquire capability for EXISTING execution
        lease_id = None
        capability_execution_id = None
        
        if capability_action_bridge:
            try:
                from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_existing_execution
                capability = acquire_capability_for_existing_execution(
                    execution_id=execution_id,
                    run_id=run_id,
                    action='WRITE_REPOSITORY_FILE',
                    target=f'file:{relative_path}',
                    requested_scope='self_update',
                    invocation_id='write_repo_file',
                    episode_id=episode_id,
                    session_id=session_id,
                )
                lease_id = capability.get('lease_id')
                capability_execution_id = capability.get('execution_id')
            except Exception as e:
                # Authority unavailable - FAIL CLOSED
                return {"status": "error", "detail": f"Authorization denied: capability acquisition failed: {e}"}
        else:
            # Authority unavailable - FAIL CLOSED
            return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}
        
        # C-2-CRIT-3: Thin wrapper calling tested implementation
        return write_repo_file_impl(
            workspace_root=Path(workspace_root_fn()),
            relative_path=relative_path,
            content=content,
            create_dirs=create_dirs,
            governance_fn=governance_fn,
            capability_action_bridge=capability_action_bridge,
            lease_id=lease_id,
            execution_id=capability_execution_id,
        )

    count += 1

    # -----------------------------------------------------------------
    # apply_text_patch
    # -----------------------------------------------------------------
    @mcp.tool()
    def apply_text_patch(
        relative_path: str,
        old_text: str,
        new_text: str,
        description: str = "",
        # C2 VFINAL5: Trusted execution context parameters
        execution_id: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        """Aplica un parche de texto (buscar y reemplazar) a un archivo.

        Metacognicion: el programa puede corregir bugs en su propio codigo
        de forma precisa sin reescribir archivos completos.

        Args:
            relative_path: ruta relativa al archivo.
            old_text: texto exacto a buscar.
            new_text: texto de reemplazo.
            description: descripcion del cambio (para logging).
            execution_id: Existing execution identifier for causal attribution.
            run_id: Existing run identifier for causal attribution.
            session_id: Session identifier for causal attribution.
            episode_id: Episode identifier for causal attribution.

        Returns:
            dict con status, replacements_made.
        """
        # C2 VFINAL5: Require trusted execution context for self-update
        if not execution_id or not run_id:
            return {"status": "error", "detail": "Authorization denied: missing execution context (execution_id, run_id required)"}
        
        # C2 VFINAL5: Acquire capability for EXISTING execution
        lease_id = None
        capability_execution_id = None
        
        if capability_action_bridge:
            try:
                from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_existing_execution
                capability = acquire_capability_for_existing_execution(
                    execution_id=execution_id,
                    run_id=run_id,
                    action='APPLY_PATCH',
                    target=f'file:{relative_path}',
                    requested_scope='self_update',
                    invocation_id='apply_text_patch',
                    episode_id=episode_id,
                    session_id=session_id,
                )
                lease_id = capability.get('lease_id')
                capability_execution_id = capability.get('execution_id')
            except Exception as e:
                # Authority unavailable - FAIL CLOSED
                return {"status": "error", "detail": f"Authorization denied: capability acquisition failed: {e}"}
        else:
            # Authority unavailable - FAIL CLOSED
            return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}
        
        # C-2-CRIT-3: Thin wrapper calling tested implementation
        return apply_text_patch_impl(
            workspace_root=Path(workspace_root_fn()),
            relative_path=relative_path,
            old_text=old_text,
            new_text=new_text,
            description=description,
            governance_fn=governance_fn,
            capability_action_bridge=capability_action_bridge,
            lease_id=lease_id,
            execution_id=capability_execution_id,
        )

    count += 1

    # -----------------------------------------------------------------
    # git_commit_and_push
    # -----------------------------------------------------------------
    @mcp.tool()
    def git_commit_and_push(
        message: str,
        files: str = ".",
        push: bool = True,
        # C2 VFINAL5: Trusted execution context parameters
        execution_id: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        """Hace git add + commit + push de los cambios del programa.

        Metacognicion: el programa puede persistir sus auto-mejoras
        en el repositorio remoto sin intervencion humana.

        Args:
            message: mensaje de commit.
            files: archivos a agregar (default: todos los modificados).
            push: si hacer push al remoto (default: True).
            execution_id: Existing execution identifier for causal attribution.
            run_id: Existing run identifier for causal attribution.
            session_id: Session identifier for causal attribution.
            episode_id: Episode identifier for causal attribution.

        Returns:
            dict con status, commit_hash, branch, push_output.
        """
        # C2 VFINAL5: Require trusted execution context for self-update
        if not execution_id or not run_id:
            return {"status": "error", "detail": "Authorization denied: missing execution context (execution_id, run_id required)"}
        
        # C2 VFINAL5: Acquire capability for EXISTING execution
        lease_id = None
        capability_execution_id = None
        
        if capability_action_bridge:
            try:
                from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_existing_execution
                capability = acquire_capability_for_existing_execution(
                    execution_id=execution_id,
                    run_id=run_id,
                    action='GIT_COMMIT',
                    target='git:workspace',
                    requested_scope='self_update',
                    invocation_id='git_commit',
                    episode_id=episode_id,
                    session_id=session_id,
                )
                lease_id = capability.get('lease_id')
                capability_execution_id = capability.get('execution_id')
            except Exception as e:
                # Authority unavailable - FAIL CLOSED
                return {"status": "error", "detail": f"Authorization denied: capability acquisition failed: {e}"}
        else:
            # Authority unavailable - FAIL CLOSED
            return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}
        
        # C-2-CRIT-3: Thin wrapper calling tested implementation
        # Note: The _impl function uses a simpler interface, so we need to adapt
        # For now, this is a simplified wrapper - full integration requires _impl to support files parameter
        return git_commit_and_push_impl(
            workspace_root=Path(workspace_root_fn()),
            message=message,
            push=push,
            governance_fn=governance_fn,
            capability_action_bridge=capability_action_bridge,
            lease_id=lease_id,
            execution_id=capability_execution_id,
        )

    count += 1

    logger.info("self_update_tools: %d tools registered", count)
    return count
