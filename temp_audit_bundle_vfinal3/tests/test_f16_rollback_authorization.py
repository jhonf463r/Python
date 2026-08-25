"""F16 Rollback Authorization Tests - Default-Deny Enforcement

Tests for F16: ToolRollbackManager.attempt() default-deny authorization.

Covers:
- Rollback without capability (REJECT)
- Rollback invalid capability (REJECT)
- Rollback wrong action (REJECT)
- Rollback wrong target (REJECT)
- Rollback authority unavailable (REJECT)
- Valid rollback capability (AUTHORIZE)
"""

import pytest
from unittest.mock import Mock

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolTaskStatus,
    ToolAction,
    ToolActionType,
    ToolType,
)
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionAuthorization


class TestF16RollbackAuthorization:
    """Test F16: ToolRollbackManager.attempt() requires authority authorization."""
    
    @pytest.fixture
    def mock_adapter(self):
        """Mock adapter for rollback execution."""
        adapter = Mock()
        adapter.run = Mock(return_value={
            'success': True,
            'output_text': 'rollback executed',
            'metadata': {'state_hint': 'rolled_back', 'detail': 'Rollback successful'}
        })
        return adapter
    
    @pytest.fixture
    def mock_capability_action_bridge(self):
        """Mock CapabilityActionBridge."""
        return Mock(spec=CapabilityActionBridge)
    
    @pytest.fixture
    def tool_card(self):
        """Mock tool card."""
        return ToolCard(
            tool_id='test_tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            title='Test Tool',
            name='Test Tool',
            description='Test tool for rollback',
            version='1.0.0',
            destructive=True,
            supports_rollback=True,
        )
    
    @pytest.fixture
    def task_with_rollback(self):
        """Task with rollback actions."""
        return ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[
                ToolAction(
                    action_type=ToolActionType.RUN_COMMAND,
                    label='test',
                    command='echo test',
                    parameters={},
                )
            ],
            rollback_actions=[
                ToolAction(
                    action_type=ToolActionType.RUN_COMMAND,
                    label='rollback',
                    command='echo rollback',
                    parameters={},
                )
            ],
            requested_by_role='tool_use',
            lease_id='test_lease',
            action='WRITE',
            target='codebase',
            execution_id='test_execution_id',
        )
    
    @pytest.fixture
    def failed_result(self):
        """Failed result to trigger rollback."""
        return ToolResult(
            task_id='test_task_id',
            tool_id='test_tool',
            tool_type=ToolType.SHELL,
            success=False,
            execution_state=ExecutionState(
                state='failed',
                detail='Test failure',
                executor_name='test_adapter',
                sandboxed=False,
            ),
            output_text='Test failed',
        )
    
    def test_rollback_rejects_missing_capability_fields(self, tool_card, task_with_rollback, failed_result, mock_adapter):
        """Test A: Rollback without capability fields is rejected."""
        # Create rollback manager with capability bridge
        rollback_manager = ToolRollbackManager(capability_action_bridge=Mock(spec=CapabilityActionBridge))
        
        # Task without capability fields
        task_no_capability = task_with_rollback.model_copy(
            update={
                'lease_id': None,
                'action': None,
                'target': None,
            }
        )
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_no_capability,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback rejected
        assert rollback_state.state == 'rollback_failed', \
            "Rollback should fail when capability fields missing"
        assert 'Protected rollback requires capability' in rollback_state.detail, \
            "Rollback state detail should mention capability requirement"
        assert rollback_state.metadata.get('authorization_required') is True, \
            "Rollback state metadata should indicate authorization required"
        
        # Adapter should NOT be called
        mock_adapter.run.assert_not_called()
    
    def test_rollback_rejects_invalid_capability(self, tool_card, task_with_rollback, failed_result, mock_adapter, mock_capability_action_bridge):
        """Test B: Rollback with invalid capability is rejected."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Invalid capability'
        )
        
        rollback_manager = ToolRollbackManager(capability_action_bridge=mock_capability_action_bridge)
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_with_rollback,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback rejected
        assert rollback_state.state == 'rollback_failed', \
            "Rollback should fail with invalid capability"
        assert 'Rollback authorization failed' in rollback_state.detail, \
            "Rollback state detail should mention authorization failure"
        assert rollback_state.metadata.get('authorization_error') == 'Invalid capability', \
            "Rollback state metadata should contain authorization error"
        
        # Adapter should NOT be called
        mock_adapter.run.assert_not_called()
    
    def test_rollback_rejects_wrong_action(self, tool_card, task_with_rollback, failed_result, mock_adapter, mock_capability_action_bridge):
        """Test C: Rollback with wrong action is rejected."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Action mismatch'
        )
        
        rollback_manager = ToolRollbackManager(capability_action_bridge=mock_capability_action_bridge)
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_with_rollback,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback rejected
        assert rollback_state.state == 'rollback_failed', \
            "Rollback should fail with wrong action"
        assert 'Rollback authorization failed' in rollback_state.detail, \
            "Rollback state detail should mention authorization failure"
        
        # Adapter should NOT be called
        mock_adapter.run.assert_not_called()
    
    def test_rollback_rejects_wrong_target(self, tool_card, task_with_rollback, failed_result, mock_adapter, mock_capability_action_bridge):
        """Test D: Rollback with wrong target is rejected."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Target mismatch'
        )
        
        rollback_manager = ToolRollbackManager(capability_action_bridge=mock_capability_action_bridge)
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_with_rollback,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback rejected
        assert rollback_state.state == 'rollback_failed', \
            "Rollback should fail with wrong target"
        assert 'Rollback authorization failed' in rollback_state.detail, \
            "Rollback state detail should mention authorization failure"
        
        # Adapter should NOT be called
        mock_adapter.run.assert_not_called()
    
    def test_rollback_authority_down_rejects(self, tool_card, task_with_rollback, failed_result, mock_adapter):
        """Test E: Rollback when authority unavailable is rejected."""
        # Create rollback manager without capability bridge (authority down)
        rollback_manager = ToolRollbackManager(capability_action_bridge=None)
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_with_rollback,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback rejected
        assert rollback_state.state == 'rollback_failed', \
            "Rollback should fail when authority unavailable"
        assert 'Authority system is not available' in rollback_state.detail, \
            "Rollback state detail should mention authority unavailable"
        assert rollback_state.metadata.get('authority_unavailable') is True, \
            "Rollback state metadata should indicate authority unavailable"
        
        # Adapter should NOT be called
        mock_adapter.run.assert_not_called()
    
    def test_rollback_allows_valid_capability(self, tool_card, task_with_rollback, failed_result, mock_adapter, mock_capability_action_bridge):
        """Test F: Rollback with valid capability is authorized."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=True,
            run_id='test_run_id',
        )
        
        rollback_manager = ToolRollbackManager(capability_action_bridge=mock_capability_action_bridge)
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_with_rollback,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback authorized and executed
        assert rollback_state.state == 'rolled_back', \
            "Rollback should succeed with valid capability"
        assert 'Rollback ejecutado correctamente' in rollback_state.detail, \
            "Rollback state detail should indicate successful execution"
        
        # Adapter SHOULD be called
        mock_adapter.run.assert_called_once()
        call_kwargs = mock_adapter.run.call_args[1]
        assert call_kwargs.get('sandbox') == False, \
            "Adapter should be called with sandbox=False for real rollback execution"
    
    def test_rollback_no_actions_unavailable(self, tool_card, failed_result, mock_adapter):
        """Test: Rollback unavailable when task has no rollback actions."""
        rollback_manager = ToolRollbackManager(capability_action_bridge=Mock(spec=CapabilityActionBridge))
        
        # Task without rollback actions
        task_no_rollback = ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[
                ToolAction(
                    action_type=ToolActionType.RUN_COMMAND,
                    label='test',
                    command='echo test',
                    parameters={},
                )
            ],
            rollback_actions=[],  # No rollback actions
            requested_by_role='tool_use',
        )
        
        # Attempt rollback
        rollback_state = rollback_manager.attempt(
            card=tool_card,
            task=task_no_rollback,
            result=failed_result,
            adapter=mock_adapter,
        )
        
        # Verify rollback unavailable
        assert rollback_state.state == 'rollback_unavailable', \
            "Rollback should be unavailable when task has no rollback actions"
        assert 'no define rollback_actions' in rollback_state.detail.lower(), \
            "Rollback state detail should mention no rollback actions"
        
        # Adapter should NOT be called
        mock_adapter.run.assert_not_called()
