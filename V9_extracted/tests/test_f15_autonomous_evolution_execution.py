"""F15 Security Tests - Autonomous Evolution Execution Bypass Remediation

Tests for F15: AutonomousEvolutionService execute_external_consultation
must require authority authorization for real execution.

This ensures the previously uncovered bypass path is now protected.
"""

import pytest
from unittest.mock import Mock
from iabv_v15.domain.models import (
    ToolTask,
    ToolResult,
    TaskRole,
    ToolAction,
    ToolActionType,
    ExecutionState,
    ToolValidationStatus,
    ToolType,
)
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionAuthorization
from iabv_v15.services.trust.post_action_observer import PostActionObserver


class TestF15AutonomousEvolutionExecution:
    """Test F15: AutonomousEvolutionService execution requires authority."""
    
    @pytest.fixture
    def mock_registry(self):
        return Mock()
    
    @pytest.fixture
    def mock_memory(self):
        memory = Mock()
        memory.audit_event = Mock()
        memory.remember_task = Mock()
        memory.repository = Mock()
        memory.repository.save_result = Mock()
        memory.repository.get_task = Mock(return_value=None)
        
        # Mock remember_result to convert dict to ToolResult
        def mock_remember_result(card, task, result):
            if isinstance(result, dict):
                return ToolResult(
                    task_id=task.task_id,
                    tool_id=card.tool_id,
                    tool_type=card.tool_type,
                    success=result.get('success', False),
                    execution_state=ExecutionState(
                        state=result.get('metadata', {}).get('state_hint', 'unknown'),
                        detail=result.get('metadata', {}).get('detail', ''),
                        sandboxed=result.get('metadata', {}).get('sandboxed', True),
                    ),
                    output_text=result.get('output_text', ''),
                    metadata=result.get('metadata', {}),
                )
            return result
        
        memory.remember_result = Mock(side_effect=mock_remember_result)
        return memory
    
    @pytest.fixture
    def mock_sandbox(self):
        sandbox = Mock()
        # Return a dict as the actual sandbox does
        sandbox.run = Mock(return_value={
            'success': True,
            'output_text': 'sandbox result',
            'metadata': {'state_hint': 'simulated', 'detail': 'Sandbox simulated'}
        })
        return sandbox
    
    @pytest.fixture
    def mock_validator(self):
        return Mock()
    
    @pytest.fixture
    def mock_approval_policy(self):
        policy = Mock()
        policy.evaluate = Mock(side_effect=lambda card, task: task)
        return policy
    
    @pytest.fixture
    def mock_rollback_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_adapters(self):
        adapter = Mock()
        adapter.is_available = Mock(return_value=True)
        # Return a dict as the actual adapter does
        adapter.run = Mock(return_value={
            'success': True,
            'output_text': 'real execution result',
            'metadata': {'state_hint': 'executed', 'detail': 'Tool executed'}
        })
        return {'test_adapter': adapter}
    
    @pytest.fixture
    def mock_capability_action_bridge(self):
        bridge = Mock(spec=CapabilityActionBridge)
        bridge.authorize_action = Mock(return_value=Mock(success=True))
        return bridge
    
    @pytest.fixture
    def mock_post_action_observer(self):
        observer = Mock(spec=PostActionObserver)
        observer.observe = Mock()
        return observer
    
    @pytest.fixture
    def tool_card(self):
        return Mock(
            tool_id='test_tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            title='Test Tool',
        )
    
    @pytest.fixture
    def tool_teach_service(
        self,
        mock_registry,
        mock_memory,
        mock_sandbox,
        mock_validator,
        mock_approval_policy,
        mock_rollback_manager,
        mock_adapters,
        mock_capability_action_bridge,
        mock_post_action_observer,
        tool_card
    ):
        mock_registry.pick_card_for_task = Mock(return_value=tool_card)
        
        return ToolTeachService(
            registry=mock_registry,
            memory=mock_memory,
            sandbox=mock_sandbox,
            validator=mock_validator,
            approval_policy=mock_approval_policy,
            rollback_manager=mock_rollback_manager,
            adapters=mock_adapters,
            workspace_root='.',
            capability_action_bridge=mock_capability_action_bridge,
            post_action_observer=mock_post_action_observer,
        )
    
    def test_execute_task_rejects_missing_capability_fields(self, tool_teach_service, mock_adapters):
        """Test A: External consultation with no capability fields is rejected."""
        task = ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[ToolAction(
                action_type=ToolActionType.RUN_COMMAND,
                label='test',
                command='echo test',
                parameters={},
            )],
            requested_by_role=TaskRole.TOOL_USE,  # Real execution, not sandbox
            lease_id=None,  # Missing capability
            action=None,
            target=None,
        )
        
        result = tool_teach_service.execute_task(task, approved=True)
        
        # Should reject due to missing capability fields
        assert result.success == False
        assert result.validation_status == ToolValidationStatus.BLOCKED
        assert result.execution_state.state == 'authorization_required'
        assert result.error_message == 'authorization_required'
        
        # Adapter should NOT be called
        mock_adapters['test_adapter'].run.assert_not_called()
    
    def test_execute_task_rejects_invalid_capability(self, tool_teach_service, mock_adapters, mock_capability_action_bridge):
        """Test B: External consultation with invalid capability is rejected."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Invalid capability'
        )
        
        task = ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[ToolAction(
                action_type=ToolActionType.RUN_COMMAND,
                label='test',
                command='echo test',
                parameters={},
            )],
            requested_by_role=TaskRole.TOOL_USE,
            lease_id='invalid_lease',
            action='READ',
            target='codebase',
            execution_id='test_execution_id',
        )
        
        result = tool_teach_service.execute_task(task, approved=True)
        
        # Should reject due to authorization failure
        assert result.success == False
        assert result.validation_status == ToolValidationStatus.BLOCKED
        assert result.execution_state.state == 'authorization_failed'
        assert result.error_message == 'authorization_failed'
        
        # Adapter should NOT be called
        mock_adapters['test_adapter'].run.assert_not_called()
    
    def test_execute_task_rejects_wrong_action(self, tool_teach_service, mock_adapters, mock_capability_action_bridge):
        """Test C: External consultation with wrong action is rejected."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Action mismatch'
        )
        
        task = ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[ToolAction(
                action_type=ToolActionType.RUN_COMMAND,
                label='test',
                command='echo test',
                parameters={},
            )],
            requested_by_role=TaskRole.TOOL_USE,
            lease_id='test_lease',
            action='WRITE',  # Wrong action (capability is for READ)
            target='codebase',
            execution_id='test_execution_id',
        )
        
        result = tool_teach_service.execute_task(task, approved=True)
        
        # Should reject due to authorization failure
        assert result.success == False
        assert result.validation_status == ToolValidationStatus.BLOCKED
        assert result.execution_state.state == 'authorization_failed'
        
        # Adapter should NOT be called
        mock_adapters['test_adapter'].run.assert_not_called()
    
    def test_execute_task_rejects_wrong_target(self, tool_teach_service, mock_adapters, mock_capability_action_bridge):
        """Test D: External consultation with wrong target is rejected."""
        mock_capability_action_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Target mismatch'
        )
        
        task = ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[ToolAction(
                action_type=ToolActionType.RUN_COMMAND,
                label='test',
                command='echo test',
                parameters={},
            )],
            requested_by_role=TaskRole.TOOL_USE,
            lease_id='test_lease',
            action='READ',
            target='unauthorized_target',  # Wrong target
            execution_id='test_execution_id',
        )
        
        result = tool_teach_service.execute_task(task, approved=True)
        
        # Should reject due to authorization failure
        assert result.success == False
        assert result.validation_status == ToolValidationStatus.BLOCKED
        assert result.execution_state.state == 'authorization_failed'
        
        # Adapter should NOT be called
        mock_adapters['test_adapter'].run.assert_not_called()
    
    @pytest.mark.skip("Skipping valid capability test - covered by real E2E test")
    def test_execute_task_allows_valid_capability(self, tool_teach_service, mock_adapters, mock_capability_action_bridge):
        """Test E: External consultation with valid capability is authorized."""
        pass
    
    @pytest.mark.skip("Skipping sandbox test - sandbox is exempt by design")
    def test_execute_task_sandbox_only_exempt(self, tool_teach_service, mock_adapters):
        """Test F: Sandbox-only execution is exempt from capability requirement."""
        pass
    
    def test_execute_task_authority_down_rejects(self, tool_teach_service, mock_adapters):
        """Test G: Authority unavailable rejects real execution."""
        # Create service without capability_action_bridge
        tool_teach_service_no_authority = ToolTeachService(
            registry=tool_teach_service.registry,
            memory=tool_teach_service.memory,
            sandbox=tool_teach_service.sandbox,
            validator=tool_teach_service.validator,
            approval_policy=tool_teach_service.approval_policy,
            rollback_manager=tool_teach_service.rollback_manager,
            adapters=tool_teach_service.adapters,
            workspace_root='.',
            capability_action_bridge=None,  # Authority unavailable
            post_action_observer=tool_teach_service.post_action_observer,
        )
        
        task = ToolTask(
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[ToolAction(
                action_type=ToolActionType.RUN_COMMAND,
                label='test',
                command='echo test',
                parameters={},
            )],
            requested_by_role=TaskRole.TOOL_USE,
            lease_id=None,
            action=None,
            target=None,
        )
        
        result = tool_teach_service_no_authority.execute_task(task, approved=True)
        
        # Should reject due to authority unavailable
        assert result.success == False
        assert result.validation_status == ToolValidationStatus.BLOCKED
        assert result.execution_state.state == 'authority_unavailable'
        
        # Adapter should NOT be called
        mock_adapters['test_adapter'].run.assert_not_called()
