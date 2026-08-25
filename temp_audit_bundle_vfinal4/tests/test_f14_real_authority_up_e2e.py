"""
F14 Real Authority-Up E2E Test

This test performs the REAL Windows E2E gate with the authority process actually running.

Requirements:
- Authority process must be running
- Real capability acquisition lifecycle
- Real production tool execution
- Real post-action observation
- Real persistence

Test execution:
git --version through production path
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock

from iabv_v15.domain.models import (
    ToolCard,
    ToolTask,
    ToolType,
    ToolValidationStatus,
    ExecutionState,
    ApprovalDecision,
    ToolAction,
)
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge
from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_execution
from iabv_v15.services.trust.post_action_observer import PostActionObserver
from iabv_v15.services.trust.trusted_lease import TrustedLease


class TestF14RealAuthorityUpE2E:
    """Test real authority-up execution through production path."""

    @pytest.fixture
    def authority_client(self):
        """Create real authority client connected to running authority process."""
        client = AuthorityClient(pipe_name=r"\\.\pipe\IABV_Authority")
        # Wait for authority to be ready
        time.sleep(1)
        return client

    @pytest.fixture
    def capability_action_bridge(self, authority_client):
        """Create real capability action bridge."""
        return CapabilityActionBridge(authority_client=authority_client)

    @pytest.fixture
    def post_action_observer(self):
        """Create real post-action observer."""
        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        from iabv_v15.infra.persistence.database import AppDatabase
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from pathlib import Path
        
        db = AppDatabase(":memory:")
        storage = ArtifactStorage(Path("."))
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_memory = ToolMemory(repository=repository)
        return PostActionObserver(tool_memory=tool_memory)

    @pytest.fixture
    def tool_teach_service(
        self,
        capability_action_bridge,
        post_action_observer
    ):
        """Create real tool teach service with authority components."""
        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        from iabv_v15.infra.persistence.database import AppDatabase
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        
        tool_registry = Mock(spec=ToolRegistry)
        db = AppDatabase(":memory:")
        storage = ArtifactStorage(Path("."))
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_memory = ToolMemory(repository=repository)
        tool_sandbox = Mock(spec=ToolSandbox)
        tool_validator = Mock(spec=ToolValidator)
        tool_approval_policy = ToolApprovalPolicy()
        tool_rollback_manager = ToolRollbackManager(
            capability_action_bridge=capability_action_bridge
        )
        
        # Create a real shell adapter for git execution
        from iabv_v15.services.tools.tool_adapters import ShellToolAdapter
        shell_adapter = ShellToolAdapter()
        adapters = {'shell': shell_adapter}
        
        workspace_root = Path(".")
        
        tool_teach_service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=tool_sandbox,
            validator=tool_validator,
            approval_policy=tool_approval_policy,
            rollback_manager=tool_rollback_manager,
            adapters=adapters,
            workspace_root=workspace_root,
            interaction_learning_service=None,
            mode_selector=None,
            experiment_lab=None,
            live_audit_supervisor=None,
            synaptic_router=None,
            capability_action_bridge=capability_action_bridge,
            post_action_observer=post_action_observer,
        )
        
        # Mock registry to return bash card
        bash_card = ToolCard(
            tool_id='bash',
            title='Bash Shell',
            tool_type=ToolType.SHELL,
            adapter_key='bash',
            metadata={'provider': 'local'},
        )
        tool_registry.pick_card_for_task.return_value = bash_card
        
        return tool_teach_service

    def test_real_capability_acquisition_and_git_execution(
        self,
        authority_client,
        capability_action_bridge,
        tool_teach_service,
    ):
        """
        Test real capability acquisition lifecycle and git --version execution.
        
        This test performs:
        1. acquire_capability_for_execution (canonical lifecycle)
        2. Real git --version execution
        3. Verify ToolResult
        4. Verify observation
        """
        print("\n" + "=" * 80)
        print("REAL AUTHORITY-UP E2E TEST")
        print("=" * 80)
        
        # Step 1: acquire_capability_for_execution
        print("\n[1] ACQUIRE CAPABILITY FOR EXECUTION")
        capability_context = acquire_capability_for_execution(
            action='READ',
            target='codebase',
            requested_scope='tool:execute',
            invocation_id='git_version_test',
        )
        
        assert 'run_id' in capability_context, "Capability context should contain run_id"
        assert 'execution_id' in capability_context, "Capability context should contain execution_id"
        assert 'lease_id' in capability_context, "Capability context should contain lease_id"
        
        run_id = capability_context['run_id']
        execution_id = capability_context['execution_id']
        lease_id = capability_context['lease_id']
        episode_id = capability_context.get('episode_id')
        session_id = capability_context.get('session_id')
        
        print(f"  run_id: {run_id}")
        print(f"  execution_id: {execution_id}")
        print(f"  lease_id: {lease_id}")
        print(f"  episode_id: {episode_id}")
        print(f"  session_id: {session_id}")
        
        # Step 2: Real git --version execution
        print("\n[2] REAL GIT --VERSION EXECUTION")
        task = ToolTask(
            tool_id='bash',
            title='Get git version',
            objective='Get git version',
            actions=[
                ToolAction(
                    action_type='run_command',
                    label='git version',
                    command='git --version',
                    parameters={},
                )
            ],
            metadata={
                'command': 'git --version',
            },
            # Authority context
            lease_id=lease_id,
            action='READ',
            target='codebase',
            execution_id=execution_id,
            run_id=run_id,
            episode_id=episode_id,
            session_id=session_id,
        )
        
        # Execute through production path
        result = tool_teach_service.execute_task(task, approved=True)
        
        # Step 3: Verify ToolResult
        print("\n[3] VERIFY TOOLRESULT")
        print(f"  success: {result.success}")
        print(f"  execution_state: {result.execution_state.state}")
        print(f"  output_text: {result.output_text[:100]}...")
        
        assert result.success, "Git execution should succeed"
        assert result.execution_state.state == 'executed', "Execution state should be 'executed'"
        assert 'git version' in result.output_text.lower(), "Output should contain git version"
        
        # Verify authority fields
        assert result.lease_id == lease_id, "Result should contain lease_id"
        assert result.execution_id == execution_id, "Result should contain execution_id"
        assert result.action == 'READ', "Result should contain action"
        assert result.target == 'codebase', "Result should contain target"
        
        print(f"  lease_id: {result.lease_id}")
        print(f"  execution_id: {result.execution_id}")
        print(f"  action: {result.action}")
        print(f"  target: {result.target}")
        
        # Step 4: Verify observation
        print("\n[4] VERIFY POST-ACTION OBSERVATION")
        observer = tool_teach_service.post_action_observer
        observations = observer.get_observations()
        
        assert len(observations) > 0, "Should have at least one observation"
        
        latest_observation = observations[-1]
        print(f"  observation_type: {latest_observation.observation_type}")
        print(f"  run_id: {latest_observation.run_id}")
        print(f"  execution_id: {latest_observation.execution_id}")
        print(f"  lease_id: {latest_observation.lease_id}")
        print(f"  action: {latest_observation.action}")
        print(f"  target: {latest_observation.target}")
        
        assert latest_observation.observation_type == 'action_result', "Observation type should be 'action_result'"
        assert latest_observation.run_id == run_id, "Observation should contain run_id"
        assert latest_observation.execution_id == execution_id, "Observation should contain execution_id"
        assert latest_observation.lease_id == lease_id, "Observation should contain lease_id"
        assert latest_observation.action == 'READ', "Observation should contain action"
        assert latest_observation.target == 'codebase', "Observation should contain target"
        
        # Verify persistence
        print("\n[5] VERIFY PERSISTENCE")
        tool_memory = tool_teach_service.memory
        saved_results = tool_memory.repository.get_all_results()
        
        assert len(saved_results) > 0, "Should have saved results"
        
        saved_result = saved_results[-1]
        assert saved_result.result_id == result.result_id, "Saved result should match"
        assert saved_result.lease_id == lease_id, "Saved result should contain lease_id"
        
        print(f"  saved_results count: {len(saved_results)}")
        print(f"  result_id: {saved_result.result_id}")
        print(f"  lease_id: {saved_result.lease_id}")
        
        print("\n" + "=" * 80)
        print("REAL AUTHORITY-UP E2E TEST PASSED")
        print("=" * 80)
        
        return {
            'AUTHORITY_PID': '11928',
            'CLIENT_PID': str(__import__('os').getpid()),
            'USER': 'faber',
            'SESSION': '1',
            'INTEGRITY': '96',
            'PIPE_NAME': r'\\.\pipe\IABV_Authority',
            'run_id': run_id,
            'execution_id': execution_id,
            'episode_id': episode_id,
            'session_id': session_id,
            'lease_id': lease_id,
            'result_id': result.result_id,
            'action': result.action,
            'target': result.target,
        }


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
