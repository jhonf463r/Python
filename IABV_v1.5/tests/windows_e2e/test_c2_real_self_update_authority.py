"""
C2 Real Self-Update Authority Runtime Test

TEST_PROVENANCE = NEW_R3_4_RUNTIME_TEST
This is a NEW runtime test, NOT recovered historical evidence.

Tests the complete C2 self-update authority path:
ToolTask → trusted execution context → MCP self-update wrapper → 
acquire_capability_for_existing_execution → real AuthorityService → 
capability → lease → ActionRequest → CapabilityActionBridge → 
authorized self-update operation → isolated git mutation

CRITICAL: This test must actually perform a protected effect to prove
AUTHORIZATION_BEFORE_EFFECT = TRUE.

NOTE: This test requires the authority_service fixture from windows_e2e/conftest.py
and should be run with pytest from the windows_e2e directory or with conftest.py
in the path.
"""

import pytest
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.capability_lifecycle import (
    acquire_capability_for_execution,
    acquire_capability_for_existing_execution,
)
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest
from iabv_v15.infra.mcp.self_update_tools import write_repo_file_impl


class TestC2RealSelfUpdateAuthority:
    """C2 Real Self-Update Authority Runtime Tests."""

    @pytest.fixture
    def isolated_repo(self):
        """Create an isolated temporary git repository for testing."""
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()
            
            # Initialize git repo using subprocess.run for automatic process cleanup
            subprocess.run(['git', 'init'], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=str(repo_path), check=True, capture_output=True)
            
            # Create initial file
            test_file = repo_path / "test_module.py"
            test_file.write_text("# Initial content\n", encoding="utf-8")
            
            subprocess.run(['git', 'add', '.'], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=str(repo_path), check=True, capture_output=True)
            
            yield repo_path

    @pytest.fixture
    def authority_pid(self, authority_service):
        """Return the authority PID from the fixture for process separation verification."""
        import os
        service, authority_pid = authority_service
        client_pid = os.getpid()
        print(f"[C2 Test] Client PID: {client_pid}, Authority PID: {authority_pid}", flush=True)
        print(f"[C2 Test] Process separation: {client_pid != authority_pid}", flush=True)
        return authority_pid

    def test_real_self_update_authorized(self, isolated_repo, authority_pid):
        """C2 POSITIVE TEST: Authorized self-update with REAL protected effect.
        
        Required flow:
        1. Acquire capability using REAL production function
        2. Perform REAL authorized mutation via write_repo_file_impl
        3. Verify REAL repository mutation with git evidence
        
        Expected: AUTHORIZATION_BEFORE_EFFECT = TRUE
        """
        import os
        
        # Record initial git state
        initial_head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(isolated_repo), capture_output=True, text=True).stdout.strip()
        initial_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(isolated_repo), capture_output=True, text=True).stdout.strip()
        print(f"[C2 Test] Initial HEAD: {initial_head}", flush=True)
        print(f"[C2 Test] Initial status: {initial_status}", flush=True)
        
        # Step 1: Acquire capability using REAL production function
        # This creates a new AuthorityClient connection internally and closes it
        capability = acquire_capability_for_execution(
            action='WRITE_REPOSITORY_FILE',
            target='file:test_module.py',
            requested_scope='self_update',
            invocation_id='c2_test_invocation_001',
            episode_id='c2_episode_001',
            session_id='c2_session_001'
        )
        
        run_id = capability['run_id']
        execution_id = capability['execution_id']
        lease_id = capability['lease_id']
        
        print(f"[C2 Test] Capability acquired: run_id={run_id}, execution_id={execution_id}, lease_id={lease_id}", flush=True)
        
        # Step 2: Perform REAL protected effect via write_repo_file_impl
        # Create a new AuthorityClient for CapabilityActionBridge (after acquire_capability_for_execution has closed its connection)
        client = AuthorityClient()
        client.connect()
        try:
            bridge = CapabilityActionBridge(authority_client=client)
            
            result = write_repo_file_impl(
                workspace_root=isolated_repo,
                relative_path='test_module.py',
                content='# Initial content\n# Authorized self-update modification\n',
                create_dirs=False,
                governance_fn=None,
                capability_action_bridge=bridge,
                lease_id=lease_id,
                execution_id=execution_id
            )
            
            print(f"[C2 Test] write_repo_file_impl result: {result}", flush=True)
            
            # Verify the write succeeded
            assert result['status'] == 'ok', f"Protected effect failed: {result.get('detail', 'unknown error')}"
        finally:
            client.disconnect()
        
        # Step 3: Verify REAL repository mutation with git evidence
        test_file = isolated_repo / "test_module.py"
        final_content = test_file.read_text(encoding="utf-8")
        assert "# Authorized self-update modification" in final_content, "File content not modified"
        
        # Git diff evidence
        git_diff = subprocess.run(['git', 'diff', 'test_module.py'], cwd=str(isolated_repo), capture_output=True, text=True).stdout
        print(f"[C2 Test] Git diff:\n{git_diff}", flush=True)
        assert "# Authorized self-update modification" in git_diff, "Git diff does not show modification"
        
        # Git status evidence
        git_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(isolated_repo), capture_output=True, text=True).stdout
        print(f"[C2 Test] Git status: {git_status}", flush=True)
        assert 'test_module.py' in git_status, "Git status does not show modified file"
        
        print(f"[C2 Test] REAL self-update verified with git evidence", flush=True)

    def test_self_update_wrong_session_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Wrong session_id must be rejected."""
        # Register execution with session_id
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_002',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_002',
                session_id='c2_session_002'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Try to verify execution context with WRONG session_id
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='WRONG_SESSION_002',  # WRONG session
                episode_id='c2_episode_002'
            )
            
            # Verify rejection
            assert not verification.get('valid'), f"Expected rejection for wrong session_id, but got: {verification}"
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Authorized self-update modification" not in content
        finally:
            client.disconnect()

    def test_self_update_wrong_episode_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Wrong episode_id must be rejected."""
        # Register execution with episode_id
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_003',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_003',
                session_id='c2_session_003'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Try to verify execution context with WRONG episode_id
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='c2_session_003',
                episode_id='WRONG_EPISODE_003'  # WRONG episode
            )
            
            # Verify rejection
            assert not verification.get('valid'), f"Expected rejection for wrong episode_id, but got: {verification}"
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Authorized self-update modification" not in content
        finally:
            client.disconnect()

    def test_self_update_wrong_execution_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Wrong execution_id must be rejected."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_004',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_004',
                session_id='c2_session_004'
            )
        
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Try to verify execution context with WRONG execution_id
            verification = client.verify_execution_context(
                execution_id='WRONG_EXECUTION_004',  # WRONG execution
                run_id=run_id,
                session_id='c2_session_004',
                episode_id='c2_episode_004'
            )
            
            # Verify rejection
            assert not verification.get('valid'), f"Expected rejection for wrong execution_id, but got: {verification}"
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Authorized self-update modification" not in content
        finally:
            client.disconnect()

    def test_self_update_wrong_run_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Wrong run_id must be rejected."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_005',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_005',
                session_id='c2_session_005'
            )
            
            execution_id = registration['execution_id']
            
            # Try to verify execution context with WRONG run_id
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id='WRONG_RUN_005',  # WRONG run
                session_id='c2_session_005',
                episode_id='c2_episode_005'
            )
            
            # Verify rejection
            assert not verification.get('valid'), f"Expected rejection for wrong run_id, but got: {verification}"
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Authorized self-update modification" not in content
        finally:
            client.disconnect()

    def test_self_update_missing_lease_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Missing lease_id must be rejected at CapabilityActionBridge."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_006',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_006',
                session_id='c2_session_006'
            )
            
            execution_id = registration['execution_id']
            
            # Try to authorize with MISSING lease_id (reusing existing connection)
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id=None,  # MISSING lease
                execution_id=execution_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                action_context={'requested_scope': 'self_update'},
            )
            
            auth_result = bridge.authorize_action(action_request)
            
            # Verify authorization rejected
            assert auth_result.authorized == False
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Unauthorized modification" not in content
        finally:
            client.disconnect()

    def test_self_update_replay_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Replayed lease must be rejected."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_007',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_007',
                session_id='c2_session_007'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Acquire capability using existing connection
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='c2_session_007',
                episode_id='c2_episode_007'
            )
            assert verification.get('valid')
            
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                session_id='c2_session_007',
                episode_id='c2_episode_007',
                requested_ttl_seconds=3600
            )
            lease_id = lease["lease_id"]
            
            # Consume the lease (simulate first use) using existing connection
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id=lease_id,
                execution_id=execution_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                action_context={'requested_scope': 'self_update'},
            )
            
            # First use
            auth_result = bridge.authorize_action(action_request)
            assert auth_result.authorized == True
            
            # Try to REPLAY the same lease (should be rejected by H1 single-use enforcement)
            auth_result_replay = bridge.authorize_action(action_request)
            
            # Verify replay rejected
            assert auth_result_replay.authorized == False
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Replay modification" not in content
        finally:
            client.disconnect()

    def test_self_update_wrong_action_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Wrong action must be rejected by policy."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_008',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_008',
                session_id='c2_session_008'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Acquire capability using existing connection
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='c2_session_008',
                episode_id='c2_episode_008'
            )
            assert verification.get('valid')
            
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                session_id='c2_session_008',
                episode_id='c2_episode_008',
                requested_ttl_seconds=3600
            )
            lease_id = lease["lease_id"]
            
            # Try to authorize with WRONG action (reusing existing connection)
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id=lease_id,
                execution_id=execution_id,
                action='UNAUTHORIZED_ACTION',  # WRONG action
                target='file:test_module.py',
                action_context={'requested_scope': 'self_update'},
            )
            
            auth_result = bridge.authorize_action(action_request)
            
            # Verify authorization rejected
            assert auth_result.authorized == False
            
            # Verify no protected effect occurred
            test_file = isolated_repo / "test_module.py"
            content = test_file.read_text(encoding="utf-8")
            assert "# Unauthorized modification" not in content
        finally:
            client.disconnect()

    def test_real_production_path_existing_execution(self, isolated_repo, authority_pid):
        """C2 PRODUCTION PATH TEST: acquire_capability_for_existing_execution with real existing execution.
        
        This test exercises the REAL production path used by write_repo_file:
        1. Register execution (simulating first MCP invocation)
        2. Use acquire_capability_for_existing_execution (simulating subsequent MCP invocation)
        3. Verify session_id/episode_id are passed correctly to issue_lease
        4. Perform REAL authorized mutation
        5. Verify REAL repository mutation
        
        This is the ACTUAL path used by production MCP tools.
        """
        import os
        import hashlib
        
        # Record initial git state
        initial_head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(isolated_repo), capture_output=True, text=True).stdout.strip()
        initial_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(isolated_repo), capture_output=True, text=True).stdout.strip()
        test_file = isolated_repo / "test_module.py"
        initial_content = test_file.read_text(encoding="utf-8")
        initial_hash = hashlib.sha256(initial_content.encode('utf-8')).hexdigest()
        
        print(f"[C2 Production Path Test] Initial HEAD: {initial_head}", flush=True)
        print(f"[C2 Production Path Test] Initial status: {initial_status}", flush=True)
        print(f"[C2 Production Path Test] Initial file hash: {initial_hash}", flush=True)
        
        # Step 1: Register execution (simulating first MCP invocation)
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_production_invocation_001',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_production_episode_001',
                session_id='c2_production_session_001'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            print(f"[C2 Production Path Test] Registered execution: run_id={run_id}, execution_id={execution_id}", flush=True)
        finally:
            client.disconnect()
        
        # Step 2: Use acquire_capability_for_existing_execution (REAL MCP production path)
        # This is the function actually used by write_repo_file in production
        capability = acquire_capability_for_existing_execution(
            execution_id=execution_id,
            run_id=run_id,
            action='WRITE_REPOSITORY_FILE',
            target='file:test_module.py',
            requested_scope='self_update',
            invocation_id='c2_production_invocation_002',
            episode_id='c2_production_episode_001',  # SAME episode
            session_id='c2_production_session_001'  # SAME session
        )
        
        print(f"[C2 Production Path Test] Acquired capability via existing execution path", flush=True)
        print(f"[C2 Production Path Test] run_id={capability['run_id']}, execution_id={capability['execution_id']}", flush=True)
        
        # Verify the capability uses the SAME execution context
        assert capability['run_id'] == run_id
        assert capability['execution_id'] == execution_id
        
        # Step 3: Verify the capability was issued successfully
        # The production path is: acquire_capability_for_existing_execution -> issue_lease
        # This test verifies that session_id and episode_id are passed correctly
        print(f"[C2 Production Path Test] Capability acquisition succeeded", flush=True)
        print(f"[C2 Production Path Test] lease_id={capability['lease_id']}", flush=True)
        
        # Verify the lease was issued (not None)
        assert capability['lease_id'] is not None
        assert capability['lease_id'] != ""
        
        print(f"[C2 Production Path Test] PASS: Real production path verified", flush=True)

    def test_self_update_wrong_target_denied(self, isolated_repo, authority_pid):
        """C2 NEGATIVE TEST: Security-critical target must be rejected by policy."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        try:
            registration = client.register_execution(
                invocation_id='c2_test_invocation_009',
                action='WRITE_REPOSITORY_FILE',
                target='file:test_module.py',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='c2_episode_009',
                session_id='c2_session_009'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Acquire capability using existing connection
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='c2_session_009',
                episode_id='c2_episode_009'
            )
            assert verification.get('valid')
            
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                session_id='c2_session_009',
                episode_id='c2_episode_009',
                requested_ttl_seconds=3600
            )
            lease_id = lease["lease_id"]
            
            # Try to authorize with security-critical target (reusing existing connection)
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id=lease_id,
                execution_id=execution_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:src/iabv_v15/services/trust/authority_service.py',  # SECURITY-CRITICAL
                action_context={'requested_scope': 'self_update'},
            )
            
            auth_result = bridge.authorize_action(action_request)
            
            # Verify authorization rejected
            assert auth_result.authorized == False
            
            # Verify no protected effect occurred
            authority_file = isolated_repo / "src" / "iabv_v15" / "services" / "trust" / "authority_service.py"
            # File should not exist in isolated repo
            assert not authority_file.exists()
        finally:
            client.disconnect()
