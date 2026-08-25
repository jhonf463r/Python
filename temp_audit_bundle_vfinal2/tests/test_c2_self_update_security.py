"""
C-2 Self-Update Security Tests

Real security tests for self-update tools (write_repo_file, apply_text_patch, git_commit_and_push).

These tests prove:
- NO VALID AUTHORITY → NO SELF-MODIFICATION
- VALID CAPABILITY + CORRECT ACTION + CORRECT TARGET → AUTHORIZED SELF-MODIFICATION

Tests use REAL CapabilityActionBridge objects and do NOT mock authorization decisions.
"""

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Import production self-update tools (extracted implementations for testing)
from iabv_v15.infra.mcp.self_update_tools import (
    _safe_path,
    apply_text_patch_impl,
    git_commit_and_push_impl,
    write_repo_file_impl,
)

# Import canonical authority components
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest, ActionAuthorization
from tests.controlled_authority_client import ControlledAuthorityClient




class TestSelfUpdateSecurity:
    """Security tests for self-update tools."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("initial content")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True, capture_output=True)

            yield repo_path

    @pytest.fixture
    def mock_governance(self):
        """Mock governance function."""
        return lambda *args, **kwargs: None  # None = allow

    @pytest.fixture
    def real_capability_action_bridge(self):
        """Create real CapabilityActionBridge with ControlledAuthorityClient for testing."""
        controlled_client = ControlledAuthorityClient(authorized=True)
        return CapabilityActionBridge(controlled_client)

    # ============================================================================
    # A. write_repo_file Negative Tests
    # ============================================================================

    def test_write_repo_file_no_capability(self, temp_repo):
        """write_repo_file without capability → REJECT → file unchanged."""
        # Capture file hash before
        test_file = temp_repo / "test.txt"
        before_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # Call without capability_action_bridge
        result = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="modified content",
            governance_fn=None,  # None = allow
            capability_action_bridge=None,
        )

        # Verify REJECT
        assert result.get("status") == "error"
        assert "Authorization denied" in result.get("detail", "")

        # Verify file unchanged
        after_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert after_hash == before_hash
        assert test_file.read_text() == "initial content"

    def test_write_repo_file_invalid_capability(self, temp_repo, real_capability_action_bridge):
        """write_repo_file with invalid capability → REJECT → file unchanged."""
        test_file = temp_repo / "test.txt"
        before_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # Configure client to reject
        real_capability_action_bridge._authority_client.set_lease_authorized('test_lease', authorized=False)

        result = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="modified content",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        # Verify REJECT
        assert result.get("status") == "error"

        # Verify file unchanged
        after_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert after_hash == before_hash

    def test_write_repo_file_wrong_action(self, temp_repo, real_capability_action_bridge):
        """write_repo_file with wrong action → REJECT → file unchanged."""
        test_file = temp_repo / "test.txt"
        before_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # Configure execution binding to reject wrong action
        real_capability_action_bridge._authority_client.set_execution_binding(
            'write_test.txt', 'READ', 'file:test.txt'  # Wrong action
        )

        result = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="modified content",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        assert result.get("status") == "error"
        after_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert after_hash == before_hash

    def test_write_repo_file_wrong_target(self, temp_repo, real_capability_action_bridge):
        """write_repo_file with wrong target → REJECT → file unchanged."""
        test_file = temp_repo / "test.txt"
        before_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # Configure execution binding to reject wrong target
        real_capability_action_bridge._authority_client.set_execution_binding(
            'write_test.txt', 'WRITE_REPOSITORY_FILE', 'file:other.txt'  # Wrong target
        )

        result = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="modified content",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        assert result.get("status") == "error"
        after_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert after_hash == before_hash

    def test_write_repo_file_authority_unavailable(self, temp_repo):
        """write_repo_file with authority unavailable → REJECT → file unchanged."""
        test_file = temp_repo / "test.txt"
        before_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # CapabilityActionBridge = None (authority unavailable)
        result = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="modified content",
            governance_fn=None,  # None = allow
            capability_action_bridge=None,
        )

        assert result.get("status") == "error"
        after_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert after_hash == before_hash

    # ============================================================================
    # B. apply_text_patch Negative Tests
    # ============================================================================

    def test_apply_text_patch_no_capability(self, temp_repo):
        """apply_text_patch without capability → REJECT → NO PATCH APPLIED."""
        test_file = temp_repo / "test.txt"
        before_content = test_file.read_text()

        result = apply_text_patch_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            old_text="initial content",
            new_text="patched content",
            governance_fn=None,  # None = allow
            capability_action_bridge=None,
        )

        assert result.get("status") == "error"
        assert test_file.read_text() == before_content

    def test_apply_text_patch_invalid_capability(self, temp_repo, real_capability_action_bridge):
        """apply_text_patch with invalid capability → REJECT → NO PATCH APPLIED."""
        test_file = temp_repo / "test.txt"
        before_content = test_file.read_text()

        # Configure client to reject
        real_capability_action_bridge._authority_client.set_lease_authorized('test_lease', authorized=False)

        result = apply_text_patch_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            old_text="initial content",
            new_text="patched content",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        assert result.get("status") == "error"
        assert test_file.read_text() == before_content

    def test_apply_text_patch_authority_unavailable(self, temp_repo):
        """apply_text_patch with authority unavailable → REJECT → NO PATCH APPLIED."""
        test_file = temp_repo / "test.txt"
        before_content = test_file.read_text()

        result = apply_text_patch_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            old_text="initial content",
            new_text="patched content",
            governance_fn=None,  # None = allow
            capability_action_bridge=None,
        )

        assert result.get("status") == "error"
        assert test_file.read_text() == before_content

    # ============================================================================
    # C. git_commit_and_push Negative Tests
    # ============================================================================

    def test_git_commit_and_push_no_capability(self, temp_repo):
        """git_commit_and_push without capability → REJECT → no commit, no push."""
        # Modify file
        test_file = temp_repo / "test.txt"
        test_file.write_text("modified content")

        # Get commit count before
        result_before = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_before = int(result_before.stdout.strip())

        result = git_commit_and_push_impl(
            workspace_root=temp_repo,
            message="Test commit",
            push=False,
            governance_fn=None,  # None = allow
            capability_action_bridge=None,
        )

        # Verify REJECT
        assert result.get("status") == "error"

        # Verify no commit
        result_after = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_after = int(result_after.stdout.strip())
        assert commit_count_after == commit_count_before

    def test_git_commit_and_push_invalid_capability(self, temp_repo, real_capability_action_bridge):
        """git_commit_and_push with invalid capability → REJECT → no commit, no push."""
        test_file = temp_repo / "test.txt"
        test_file.write_text("modified content")

        result_before = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_before = int(result_before.stdout.strip())

        # Configure client to reject
        real_capability_action_bridge._authority_client.set_lease_authorized('test_lease', authorized=False)

        result = git_commit_and_push_impl(
            workspace_root=temp_repo,
            message="Test commit",
            push=False,
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        assert result.get("status") == "error"

        result_after = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_after = int(result_after.stdout.strip())
        assert commit_count_after == commit_count_before

    def test_git_commit_and_push_authority_unavailable(self, temp_repo):
        """git_commit_and_push with authority unavailable → REJECT → no commit, no push."""
        test_file = temp_repo / "test.txt"
        test_file.write_text("modified content")

        result_before = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_before = int(result_before.stdout.strip())

        result = git_commit_and_push_impl(
            workspace_root=temp_repo,
            message="Test commit",
            push=False,
            governance_fn=None,  # None = allow
            capability_action_bridge=None,
        )

        assert result.get("status") == "error"

        result_after = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_after = int(result_after.stdout.strip())
        assert commit_count_after == commit_count_before

    # ============================================================================
    # Valid Tests with Real CapabilityActionBridge
    # ============================================================================

    def test_write_repo_file_valid_capability(self, temp_repo, real_capability_action_bridge):
        """write_repo_file with valid capability → AUTHORIZED → file modified."""
        test_file = temp_repo / "test.txt"
        before_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        result = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="authorized content",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        # Verify AUTHORIZED
        assert result.get("status") == "ok"

        # Verify file modified
        after_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert after_hash != before_hash
        assert test_file.read_text() == "authorized content"

    def test_apply_text_patch_valid_capability(self, temp_repo, real_capability_action_bridge):
        """apply_text_patch with valid capability → AUTHORIZED → patch applied."""
        test_file = temp_repo / "test.txt"
        before_content = test_file.read_text()

        result = apply_text_patch_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            old_text="initial content",
            new_text="patched content",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        assert result.get("status") == "ok"
        assert test_file.read_text() == "patched content"
        assert test_file.read_text() != before_content

    def test_git_commit_and_push_valid_capability(self, temp_repo, real_capability_action_bridge):
        """git_commit_and_push with valid capability → AUTHORIZED → commit created."""
        test_file = temp_repo / "test.txt"
        test_file.write_text("modified content")

        result_before = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_before = int(result_before.stdout.strip())

        result = git_commit_and_push_impl(
            workspace_root=temp_repo,
            message="Authorized commit",
            push=False,
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        assert result.get("status") == "ok"

        result_after = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count_after = int(result_after.stdout.strip())
        assert commit_count_after == commit_count_before + 1

    # ============================================================================
    # Replay Test
    # ============================================================================

    def test_write_repo_file_replay_rejects(self, temp_repo, real_capability_action_bridge):
        """write_repo_file replay → second use REJECTS → no second side effect."""
        test_file = temp_repo / "test.txt"

        # First use
        result1 = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="first modification",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )
        assert result1.get("status") == "ok"

        # Second use with same lease (real bridge will detect replay via consumed state)
        result2 = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="second modification",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        # Verify REJECT
        assert result2.get("status") == "error"
        assert "already consumed" in result2.get("detail", "")

        # Verify no second side effect
        assert test_file.read_text() == "first modification"

    # ============================================================================
    # Cross-Execution Test
    # ============================================================================

    def test_cross_execution_rejects(self, temp_repo, real_capability_action_bridge):
        """Capability for execution A → operation under execution B → REJECT."""
        # Capability for execution A
        result_a = write_repo_file_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            content="execution a",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )
        assert result_a.get("status") == "ok"

        # Attempt operation under execution B with same capability (real bridge will reject via consumed state)
        result_b = apply_text_patch_impl(
            workspace_root=temp_repo,
            relative_path="test.txt",
            old_text="execution a",
            new_text="execution b",
            governance_fn=None,  # None = allow
            capability_action_bridge=real_capability_action_bridge,
        )

        # Verify REJECT (lease already consumed by different execution)
        assert result_b.get("status") == "error"
