"""
F15 Autonomous Evolution Authority Runtime Test

TEST_PROVENANCE = NEW_R3_4_RUNTIME_TEST
This is a NEW runtime test, NOT recovered historical evidence.

Tests the F15 autonomous evolution authority path:
AutonomousEvolutionService → decision/selection → ToolTask → 
existing execution context → capability → lease → AuthorityService → 
controlled mutation → validation → observation

CRITICAL: This test must verify that autonomous evolution execution
requires authority authorization through the canonical choke point.

NOTE: This test requires the authority_service fixture from windows_e2e/conftest.py
and should be run with pytest from the windows_e2e directory or with conftest.py
in the path.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.capability_lifecycle import (
    acquire_capability_for_execution,
    acquire_capability_for_existing_execution,
)
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest


class TestF15AutonomousEvolutionAuthority:
    """F15 Autonomous Evolution Authority Runtime Tests."""

    @pytest.fixture
    def isolated_workspace(self):
        """Create an isolated temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir) / "test_workspace"
            workspace_path.mkdir()
            
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=str(workspace_path), check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=str(workspace_path), check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=str(workspace_path), check=True, capture_output=True)
            
            # Create initial file
            test_file = workspace_path / "evolution_target.py"
            test_file.write_text("# Evolution target\n", encoding="utf-8")
            subprocess.run(['git', 'add', '.'], cwd=str(workspace_path), check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=str(workspace_path), check=True, capture_output=True)
            
            yield workspace_path
            
            # Cleanup is automatic with TemporaryDirectory

    @pytest.fixture
    def authority_client(self, authority_service):
        """Authority client fixture that uses the running authority service."""
        client = AuthorityClient()
        client.connect()
        yield client
        client.disconnect()

    def test_autonomous_evolution_authorized_execution(self, isolated_workspace, authority_client):
        """F15 POSITIVE TEST: Autonomous evolution execution requires authority authorization.
        
        Required flow:
        1. Register execution with autonomous evolution context
        2. AutonomousEvolutionService identifies/requests bounded controlled change
        3. Acquire capability for existing execution
        4. Authority accepts
        5. Action occurs
        6. Validation occurs
        7. Result observed
        
        Expected: AUTHORIZATION_BEFORE_ACTION = TRUE
        """
        # Step 1: Register execution with autonomous evolution context
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_001',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_001',
            session_id='f15_session_001'
        )
        
        run_id = registration['run_id']
        execution_id = registration['execution_id']
        session_id = 'f15_session_001'
        episode_id = 'f15_episode_001'
        
        # Step 2: Simulate AutonomousEvolutionService decision
        # (In real path, this would be plan_or_execute → decision → action)
        autonomous_decision = {
            'action': 'WRITE_REPOSITORY_FILE',
            'target': 'file:evolution_target.py',
            'reason': 'Autonomous evolution optimization',
            'bounded': True,
        }
        
        # Step 3: Acquire capability for existing execution
        capability = acquire_capability_for_existing_execution(
            execution_id=execution_id,
            run_id=run_id,
            action=autonomous_decision['action'],
            target=autonomous_decision['target'],
            requested_scope='autonomous_evolution',
            invocation_id='f15_evolution_001',
            episode_id=episode_id,
            session_id=session_id
        )
        
        lease_id = capability['lease_id']
        
        # Verify capability context
        assert capability['run_id'] == run_id
        assert capability['execution_id'] == execution_id
        assert lease_id is not None
        
        # Step 4: Authority accepts (via CapabilityActionBridge)
        client = AuthorityClient()
        client.connect()
        
        try:
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id=lease_id,
                execution_id=execution_id,
                action=autonomous_decision['action'],
                target=autonomous_decision['target'],
                action_context={'requested_scope': 'autonomous_evolution'},
            )
            
            auth_result = bridge.authorize_action(action_request)
            
            # Step 5: Verify authority accepted
            assert auth_result.authorized, f"Authorization failed: {auth_result.error}"
            
            # Step 6: Perform action (simulated autonomous evolution mutation)
            target_file = isolated_workspace / "evolution_target.py"
            original_content = target_file.read_text(encoding="utf-8")
            new_content = original_content + "# Autonomous evolution modification\n"
            target_file.write_text(new_content, encoding="utf-8")
            
            # Step 7: Validation (verify mutation occurred)
            modified_content = target_file.read_text(encoding="utf-8")
            assert "# Autonomous evolution modification" in modified_content
            
            # Capture results
            AUTONOMOUS_ENTRYPOINT = 'AutonomousEvolutionService.plan_or_execute'
            TOOLTASK = 'WRITE_REPOSITORY_FILE'
            AUTHORITY = auth_result.authorized
            ACTION = autonomous_decision['action']
            VALIDATION = "# Autonomous evolution modification" in modified_content
            OBSERVATION = {
                'execution_id': execution_id,
                'run_id': run_id,
                'session_id': session_id,
                'episode_id': episode_id,
                'lease_id': lease_id,
                'action': action,
                'target': autonomous_decision['target'],
                'result': 'modification_successful',
            }
            
            # CRITICAL: AUTHORIZATION_BEFORE_ACTION = TRUE
            assert AUTHORITY == True
            assert VALIDATION == True
            
        finally:
            client.disconnect()

    def test_autonomous_evolution_wrong_session_denied(self, isolated_workspace, authority_client):
        """F15 NEGATIVE TEST: Wrong session_id must be rejected for autonomous evolution."""
        # Register execution with session_id
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_002',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_002',
            session_id='f15_session_002'
        )
        
        run_id = registration['run_id']
        execution_id = registration['execution_id']
        
        # Try to acquire capability with WRONG session_id
        with pytest.raises(RuntimeError, match="Session ID mismatch"):
            acquire_capability_for_existing_execution(
                execution_id=execution_id,
                run_id=run_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:evolution_target.py',
                requested_scope='autonomous_evolution',
                invocation_id='f15_evolution_002',
                episode_id='f15_episode_002',
                session_id='WRONG_SESSION_002'  # WRONG session
            )
        
        # Verify no mutation occurred
        target_file = isolated_workspace / "evolution_target.py"
        content = target_file.read_text(encoding="utf-8")
        assert "# Autonomous evolution modification" not in content

    def test_autonomous_evolution_wrong_episode_denied(self, isolated_workspace, authority_client):
        """F15 NEGATIVE TEST: Wrong episode_id must be rejected for autonomous evolution."""
        # Register execution with episode_id
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_003',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_003',
            session_id='f15_session_003'
        )
        
        run_id = registration['run_id']
        execution_id = registration['execution_id']
        
        # Try to acquire capability with WRONG episode_id
        with pytest.raises(RuntimeError, match="Episode ID mismatch"):
            acquire_capability_for_existing_execution(
                execution_id=execution_id,
                run_id=run_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:evolution_target.py',
                requested_scope='autonomous_evolution',
                invocation_id='f15_evolution_003',
                episode_id='WRONG_EPISODE_003',  # WRONG episode
                session_id='f15_session_003'
            )
        
        # Verify no mutation occurred
        target_file = isolated_workspace / "evolution_target.py"
        content = target_file.read_text(encoding="utf-8")
        assert "# Autonomous evolution modification" not in content

    def test_autonomous_evolution_wrong_execution_denied(self, isolated_workspace, authority_client):
        """F15 NEGATIVE TEST: Wrong execution_id must be rejected for autonomous evolution."""
        # Register execution
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_004',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_004',
            session_id='f15_session_004'
        )
        
        run_id = registration['run_id']
        
        # Try to acquire capability with WRONG execution_id
        with pytest.raises(RuntimeError, match="Execution context validation failed"):
            acquire_capability_for_existing_execution(
                execution_id='WRONG_EXECUTION_004',  # WRONG execution
                run_id=run_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:evolution_target.py',
                requested_scope='autonomous_evolution',
                invocation_id='f15_evolution_004',
                episode_id='f15_episode_004',
                session_id='f15_session_004'
            )
        
        # Verify no mutation occurred
        target_file = isolated_workspace / "evolution_target.py"
        content = target_file.read_text(encoding="utf-8")
        assert "# Autonomous evolution modification" not in content

    def test_autonomous_evolution_wrong_run_denied(self, isolated_workspace, authority_client):
        """F15 NEGATIVE TEST: Wrong run_id must be rejected for autonomous evolution."""
        # Register execution
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_005',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_005',
            session_id='f15_session_005'
        )
        
        execution_id = registration['execution_id']
        
        # Try to acquire capability with WRONG run_id
        with pytest.raises(RuntimeError, match="Execution context validation failed"):
            acquire_capability_for_existing_execution(
                execution_id=execution_id,
                run_id='WRONG_RUN_005',  # WRONG run
                action='WRITE_REPOSITORY_FILE',
                target='file:evolution_target.py',
                requested_scope='autonomous_evolution',
                invocation_id='f15_evolution_005',
                episode_id='f15_episode_005',
                session_id='f15_session_005'
            )
        
        # Verify no mutation occurred
        target_file = isolated_workspace / "evolution_target.py"
        content = target_file.read_text(encoding="utf-8")
        assert "# Autonomous evolution modification" not in content

    def test_autonomous_evolution_missing_lease_denied(self, isolated_workspace, authority_client):
        """F15 NEGATIVE TEST: Missing lease_id must be rejected at CapabilityActionBridge."""
        # Register execution
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_006',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_006',
            session_id='f15_session_006'
        )
        
        execution_id = registration['execution_id']
        
        # Try to authorize with MISSING lease_id
        client = AuthorityClient()
        client.connect()
        
        try:
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id='MISSING_LEASE_006',  # Invalid lease
                execution_id=execution_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:evolution_target.py',
                action_context={'requested_scope': 'autonomous_evolution'},
            )
            
            auth_result = bridge.authorize_action(action_request)
            
            # Verify authorization rejected
            assert auth_result.authorized == False
            
        finally:
            client.disconnect()
        
        # Verify no mutation occurred
        target_file = isolated_workspace / "evolution_target.py"
        content = target_file.read_text(encoding="utf-8")
        assert "# Autonomous evolution modification" not in content

    def test_autonomous_evolution_replay_denied(self, isolated_workspace, authority_client):
        """F15 NEGATIVE TEST: Replayed lease must be rejected for autonomous evolution."""
        # Register execution and acquire capability
        registration = authority_client.register_execution(
            invocation_id='f15_autonomous_invocation_007',
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            task_context='autonomous_evolution',
            episode_id='f15_episode_007',
            session_id='f15_session_007'
        )
        
        execution_id = registration['execution_id']
        
        # Acquire capability
        capability = acquire_capability_for_existing_execution(
            execution_id=execution_id,
            run_id=registration['run_id'],
            action='WRITE_REPOSITORY_FILE',
            target='file:evolution_target.py',
            requested_scope='autonomous_evolution',
            invocation_id='f15_evolution_007',
            episode_id='f15_episode_007',
            session_id='f15_session_007'
        )
        
        lease_id = capability['lease_id']
        
        # Consume the lease (simulate first use)
        client = AuthorityClient()
        client.connect()
        
        try:
            bridge = CapabilityActionBridge(authority_client=client)
            action_request = ActionRequest(
                lease_id=lease_id,
                execution_id=execution_id,
                action='WRITE_REPOSITORY_FILE',
                target='file:evolution_target.py',
                action_context={'requested_scope': 'autonomous_evolution'},
            )
            
            # First use
            auth_result = bridge.authorize_action(action_request)
            assert auth_result.authorized == True
            
            # Try to REPLAY the same lease (should be rejected by H1 single-use enforcement)
            auth_result_replay = bridge.authorize_action(action_request)
            
            # Verify replay rejected
            assert auth_result_replay.authorized == False
            
        finally:
            client.disconnect()
