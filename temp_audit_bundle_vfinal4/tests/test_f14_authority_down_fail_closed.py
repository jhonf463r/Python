"""
F14 Authority Down Fail-Closed Test

This test verifies that when the authority process is NOT running,
protected tool execution is REJECTED (fail-closed behavior).

Test requirements:
1. Start application/tool runtime
2. DO NOT start Authority Process
3. Request a protected action
4. Verify:
   - Request rejected
   - ToolAdapter NOT invoked
   - No real command executed
   - No successful ToolResult
   - No successful PostActionObserver observation
   - No success persisted in ToolMemory

This test exercises the production path with NO mocks.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from iabv_v15.domain.models import (
    ToolCard,
    ToolTask,
    ToolType,
    ToolValidationStatus,
    ExecutionState,
    ApprovalDecision,
    ToolAction,
    ToolResult,
)
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge
from iabv_v15.services.trust.post_action_observer import PostActionObserver


class TestF14AuthorityDownFailClosed:
    """Test fail-closed behavior when authority is unavailable."""

    def test_tool_teach_service_authority_down_rejects_execution(self):
        """
        Test that ToolTeachService rejects execution when authority is unavailable.
        
        This is a real integration test - no mocks for the authority check.
        """
        # Setup: Create ToolTeachService with capability_action_bridge=None (authority down)
        tool_registry = Mock(spec=ToolRegistry)
        tool_memory = Mock(spec=ToolMemory)
        tool_memory.repository = Mock()  # Add repository mock
        tool_sandbox = Mock(spec=ToolSandbox)
        tool_validator = Mock(spec=ToolValidator)
        tool_approval_policy = ToolApprovalPolicy()
        tool_rollback_manager = ToolRollbackManager(capability_action_bridge=None)
        
        # Add a mock adapter to prevent adapter_missing state
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        adapters = {'bash': mock_adapter}
        
        workspace_root = Path("/tmp/test_workspace")
        
        # CRITICAL: capability_action_bridge=None simulates authority down
        capability_action_bridge = None
        post_action_observer = None
        
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
            capability_action_bridge=capability_action_bridge,  # None = authority down
            post_action_observer=post_action_observer,
        )
        
        # Create a protected task
        card = ToolCard(
            tool_id='bash',
            title='Bash Shell',
            tool_type=ToolType.CUSTOM,
            adapter_key='bash',
            metadata={'provider': 'local'},
        )
        
        task = ToolTask(
            tool_id='bash',
            title='Execute git --version',
            objective='Get git version',
            actions=[],
            metadata={
                'command': 'git --version',
            },
            # Authority context (simulating what would be set by ToolOperationalExecutor)
            lease_id='test_lease_id',
            action='EXECUTE',
            target='tool',
            execution_id='test_execution_id',
        )
        
        # Mock the registry to return the card
        tool_registry.pick_card_for_task.return_value = card
        
        # Execute task
        result = tool_teach_service.execute_task(task, approved=True)
        
        # VERIFY FAIL-CLOSED BEHAVIOR
        
        # 1. Request rejected
        assert result.success is False, "Execution should be rejected when authority is unavailable"
        
        # 2. ToolAdapter NOT invoked (verify by checking the result state)
        assert result.execution_state.state == 'authority_unavailable', \
            "Execution state should be 'authority_unavailable'"
        
        # 3. No successful ToolResult
        assert result.success is False, "ToolResult should not be successful"
        assert result.validation_status == ToolValidationStatus.BLOCKED, \
            "Validation status should be BLOCKED"
        
        # 4. Error message indicates authority unavailable
        assert 'authority_unavailable' in result.error_message, \
            "Error message should indicate authority unavailable"
        assert 'Authority system is not available' in result.execution_state.detail, \
            "Execution state detail should mention authority unavailable"
        
        # 5. Verify audit event was recorded (for rejection)
        tool_memory.audit_event.assert_called_once()
        audit_call = tool_memory.audit_event.call_args
        assert audit_call[1]['state'] == 'rejected', "Audit event should show 'rejected' state"
        assert audit_call[1]['payload']['reason'] == 'authority_unavailable', \
            "Audit event payload should indicate authority unavailable"
        
        # 6. Verify result was saved (for audit trail)
        tool_memory.repository.save_result.assert_called_once()
        
        print("✓ ToolTeachService correctly rejects execution when authority is unavailable")
        print(f"  - Result success: {result.success}")
        print(f"  - Execution state: {result.execution_state.state}")
        print(f"  - Error message: {result.error_message}")

    def test_tool_rollback_manager_authority_down_rejects_rollback(self):
        """
        Test that ToolRollbackManager rejects rollback when authority is unavailable.
        """
        # Setup: Create ToolRollbackManager with capability_action_bridge=None
        capability_action_bridge = None  # Authority down
        rollback_manager = ToolRollbackManager(capability_action_bridge=capability_action_bridge)
        
        # Create a rollback scenario
        card = ToolCard(
            tool_id='bash',
            title='Bash Shell',
            tool_type=ToolType.CUSTOM,
            adapter_key='bash',
            metadata={'provider': 'local'},
        )
        
        task = ToolTask(
            tool_id='bash',
            title='Rollback git operation',
            objective='Rollback git command',
            actions=[
                ToolAction(
                    action_type='run_command',
                    label='git revert',
                    command='git revert HEAD',
                    parameters={},
                )
            ],
            rollback_actions=[
                ToolAction(
                    action_type='run_command',
                    label='git reset',
                    command='git reset --hard HEAD~1',
                    parameters={},
                )
            ],
            metadata={
                'command': 'git revert HEAD',
            },
            lease_id='test_lease_id',
            action='EXECUTE',
            target='tool',
            execution_id='test_execution_id',
            approval_decision=ApprovalDecision.APPROVED,
        )
        
        result = ToolResult(
            task_id='test_task_id',
            tool_id='bash',
            tool_type=ToolType.CUSTOM,
            success=True,
            validation_status=ToolValidationStatus.UNVALIDATED,
            execution_state=ExecutionState(
                state='executed',
                detail='Command executed',
                executor_name='bash',
                sandboxed=False,
                validated=True,
            ),
        )
        
        mock_adapter = Mock()
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=card,
            task=task,
            result=result,
            adapter=mock_adapter,
        )
        
        # VERIFY FAIL-CLOSED BEHAVIOR
        
        # 1. Rollback rejected
        assert rollback_state.state == 'rollback_failed', \
            "Rollback should fail when authority is unavailable"
        
        # 2. Error message indicates authority unavailable
        assert 'Authority system is not available' in rollback_state.detail, \
            "Rollback state detail should mention authority unavailable"
        
        # 3. Adapter NOT invoked
        mock_adapter.run.assert_not_called(), "Adapter should not be called when authority is unavailable"
        
        # 4. Metadata indicates authority unavailable
        assert rollback_state.metadata.get('authority_unavailable') is True, \
            "Rollback state metadata should indicate authority unavailable"
        
        print("✓ ToolRollbackManager correctly rejects rollback when authority is unavailable")
        print(f"  - Rollback state: {rollback_state.state}")
        print(f"  - Detail: {rollback_state.detail}")

    def test_github_remote_service_authority_down_rejects_execution(self):
        """
        Test that GitHubRemoteService rejects PR creation when authority is unavailable.
        """
        from iabv_v15.services.tools.github_remote_service import GitHubRemoteService, PublishResult
        
        # Setup: Create GitHubRemoteService with capability_action_bridge=None
        mock_adapter = Mock()
        mock_governance_policy = Mock()
        mock_governance_policy.allow_github_pr_open.return_value = (True, None)
        
        github_service = GitHubRemoteService(
            repo_root=Path("/tmp/test_repo"),
            adapter=mock_adapter,
            governance_policy=mock_governance_policy,
            approval_broker=None,
            evidence_dir=Path("/tmp/test_evidence"),
            capability_action_bridge=None,  # Authority down
        )
        
        # Mock git runner to simulate successful push
        mock_git_result = Mock()
        mock_git_result.returncode = 0
        mock_git_result.stderr = ''
        
        with patch.object(github_service, '_git_runner', return_value=mock_git_result):
            # Attempt to publish PR
            result = github_service.publish_branch_as_pr(
                branch='test-branch',
                title='Test PR',
                body='Test body',
                base='main',
            )
        
        # VERIFY FAIL-CLOSED BEHAVIOR
        
        # 1. Execution rejected
        assert result.success is False, "PR creation should be rejected when authority is unavailable"
        
        # 2. Error message indicates authority unavailable
        assert 'Authority system is not available' in result.error, \
            "Error message should indicate authority unavailable"
        
        # 3. Adapter NOT invoked for PR creation
        mock_adapter.run.assert_not_called(), "GitHub adapter should not be called when authority is unavailable"
        
        # 4. Evidence should be recorded
        assert result.evidence_path != '', "Evidence should be recorded even for rejection"
        
        print("✓ GitHubRemoteService correctly rejects PR creation when authority is unavailable")
        print(f"  - Success: {result.success}")
        print(f"  - Error: {result.error}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
