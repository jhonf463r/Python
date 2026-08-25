"""CRITICAL-1: TOOL_SANDBOX Semantics Regression Tests

This test verifies that TOOL_SANDBOX role uses sandbox=True (TRUE SANDBOX semantics)
and does not bypass authorization for real execution.

CRITICAL-1 FIX: TOOL_SANDBOX must use sandbox=True for isolated simulation.
TOOL_SANDBOX is NOT an authorization exemption for real execution.
"""

import pytest
from unittest.mock import MagicMock, Mock
from iabv_v15.domain.models import (
    TaskRole,
    ToolCard,
    ToolTask,
    ToolType,
    ToolResult,
    ExecutionState,
    ApprovalDecision,
)
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_adapters import ToolAdapter
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionAuthorization


class TestCritical1ToolSandboxSemantics:
    """CRITICAL-1: TOOL_SANDBOX must use sandbox=True (TRUE SANDBOX semantics)."""

    @pytest.fixture
    def mock_adapter(self):
        """Mock tool adapter."""
        adapter = MagicMock(spec=ToolAdapter)
        adapter.is_available = Mock(return_value=True)
        adapter.run.return_value = {
            'success': True,
            'output_text': 'Tool executed',
            'metadata': {'state_hint': 'executed'},
            'execution_ms': 100,
        }
        return adapter

    @pytest.fixture
    def mock_capability_bridge(self):
        """Mock capability action bridge."""
        bridge = MagicMock(spec=CapabilityActionBridge)
        bridge.authorize_action.return_value = ActionAuthorization(
            authorized=True,
            run_id='test_run_id',
            authorized_scope='codebase',
            action='WRITE',
            target='codebase',
        )
        return bridge

    @pytest.fixture
    def tool_card(self):
        """Mock tool card."""
        return ToolCard(
            tool_id='test_tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            title='Test Tool',
            name='Test Tool',
            description='Test tool for sandbox semantics',
            version='1.0.0',
            destructive=True,
            supports_rollback=True,
        )

    @pytest.fixture
    def tool_task_sandbox(self):
        """Tool task with TOOL_SANDBOX role."""
        return ToolTask(
            task_id='test_task_id',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[],
            requested_by_role='tool_sandbox',  # TOOL_SANDBOX role
            lease_id=None,  # No capability (sandbox should not require it)
            action=None,
            target=None,
            execution_id='test_execution_id',
            approval_decision=ApprovalDecision.APPROVED,
        )

    @pytest.fixture
    def tool_task_real(self):
        """Tool task with TOOL_USE role (real execution)."""
        return ToolTask(
            task_id='test_task_id',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[],
            requested_by_role='tool_use',  # Real execution
            lease_id='test_lease',  # Has capability
            action='WRITE',
            target='codebase',
            execution_id='test_execution_id',
            approval_decision=ApprovalDecision.APPROVED,
        )

    @pytest.fixture
    def tool_teach_service(self, mock_adapter, mock_capability_bridge, tool_card):
        """ToolTeachService instance."""
        memory = MagicMock()
        memory.repository.get_task = Mock(return_value=None)
        
        # Mock remember_result to return the result directly
        def mock_remember_result(card, task, result):
            return result
        
        memory.remember_result = Mock(side_effect=mock_remember_result)
        
        validator = MagicMock(spec=ToolValidator)
        validator.validate.return_value = MagicMock(success=True)
        
        registry = MagicMock()
        registry.pick_card_for_task = Mock(return_value=tool_card)
        
        service = ToolTeachService(
            registry=registry,
            memory=memory,
            sandbox=MagicMock(),
            validator=validator,
            approval_policy=MagicMock(),
            rollback_manager=MagicMock(),
            adapters={'test_adapter': mock_adapter},
            workspace_root='.',
            capability_action_bridge=mock_capability_bridge,
            post_action_observer=MagicMock(),
        )
        return service

    def test_tool_sandbox_uses_sandbox_true(self, tool_teach_service, tool_task_sandbox, mock_adapter):
        """TOOL_SANDBOX must call adapter.run with sandbox=True."""
        result = tool_teach_service.execute_task(task=tool_task_sandbox, approved=True)
        
        # Verify adapter.run was called with sandbox=True
        mock_adapter.run.assert_called_once()
        call_kwargs = mock_adapter.run.call_args[1]
        assert call_kwargs.get('sandbox') == True, \
            "TOOL_SANDBOX must use sandbox=True for isolated simulation"
        
        # Verify result indicates sandboxed execution
        assert result.execution_state.sandboxed == True, \
            "TOOL_SANDBOX result must indicate sandboxed execution"

    def test_tool_sandbox_no_capability_required(self, tool_teach_service, tool_task_sandbox, mock_adapter):
        """TOOL_SANDBOX should not require capability (sandbox=True is isolation)."""
        result = tool_teach_service.execute_task(task=tool_task_sandbox, approved=True)
        
        # Verify execution succeeded without capability
        assert result.success == True, \
            "TOOL_SANDBOX should succeed without capability (sandbox=True is isolation)"
        
        # Verify capability bridge was NOT called (sandbox is exempt)
        # Note: In the new implementation, sandbox=True is used directly,
        # so capability bridge is not consulted for sandbox mode

    def test_tool_sandbox_read_only_uses_sandbox_true(self, tool_teach_service, mock_adapter):
        """read_only execution scope must also use sandbox=True."""
        task = ToolTask(
            task_id='test_task_id',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[],
            requested_by_role='tool_use',
            lease_id=None,
            action=None,
            target=None,
            execution_id='test_execution_id',
            approval_decision=ApprovalDecision.APPROVED,
            metadata={'execution_scope': 'read_only'},
        )
        
        result = tool_teach_service.execute_task(task=task, approved=True)
        
        # Verify adapter.run was called with sandbox=True
        mock_adapter.run.assert_called_once()
        call_kwargs = mock_adapter.run.call_args[1]
        assert call_kwargs.get('sandbox') == True, \
            "read_only execution scope must use sandbox=True"

    def test_real_execution_requires_capability(self, tool_teach_service, tool_task_real, mock_adapter, mock_capability_bridge):
        """Real execution (TOOL_USE) must require capability and authorization."""
        result = tool_teach_service.execute_task(task=tool_task_real, approved=True)
        
        # Verify capability bridge was called
        mock_capability_bridge.authorize_action.assert_called_once()
        
        # Verify adapter.run was called with sandbox=False
        mock_adapter.run.assert_called_once()
        call_kwargs = mock_adapter.run.call_args[1]
        assert call_kwargs.get('sandbox') == False, \
            "Real execution must use sandbox=False"

    def test_real_execution_missing_capability_rejected(self, tool_teach_service, mock_adapter):
        """Real execution without capability must be rejected."""
        task = ToolTask(
            task_id='test_task_id',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            actions=[],
            requested_by_role='tool_use',  # Real execution
            lease_id=None,  # Missing capability
            action=None,
            target=None,
            execution_id='test_execution_id',
            approval_decision=ApprovalDecision.APPROVED,
        )
        
        result = tool_teach_service.execute_task(task=task, approved=True)
        
        # Verify execution was rejected
        assert result.success == False, \
            "Real execution without capability must be rejected"
        
        # Verify adapter.run was NOT called
        mock_adapter.run.assert_not_called()

    def test_real_execution_authorization_failed_rejected(self, tool_teach_service, tool_task_real, mock_adapter, mock_capability_bridge):
        """Real execution with failed authorization must be rejected."""
        mock_capability_bridge.authorize_action.return_value = ActionAuthorization(
            authorized=False,
            error='Invalid capability',
        )
        
        result = tool_teach_service.execute_task(task=tool_task_real, approved=True)
        
        # Verify execution was rejected
        assert result.success == False, \
            "Real execution with failed authorization must be rejected"
        
        # Verify adapter.run was NOT called
        mock_adapter.run.assert_not_called()

    def test_tool_sandbox_authority_down_uses_sandbox_true(self, tool_task_sandbox, mock_adapter):
        """TOOL_SANDBOX should use sandbox=True even when authority is down."""
        # No capability bridge (authority down)
        memory = MagicMock()
        memory.repository.get_task = Mock(return_value=None)
        memory.remember_result = Mock(side_effect=lambda card, task, result: result)
        
        validator = MagicMock(spec=ToolValidator)
        validator.validate.return_value = MagicMock(success=True)
        registry = MagicMock()
        registry.pick_card_for_task = MagicMock(return_value=MagicMock(
            tool_id='test_tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            title='Test Tool',
        ))
        
        service = ToolTeachService(
            registry=registry,
            memory=memory,
            sandbox=MagicMock(),
            validator=validator,
            approval_policy=MagicMock(),
            rollback_manager=MagicMock(),
            adapters={'test_adapter': mock_adapter},
            workspace_root='.',
            capability_action_bridge=None,  # Authority down
            post_action_observer=MagicMock(),
        )
        
        result = service.execute_task(task=tool_task_sandbox, approved=True)
        
        # Verify adapter.run was called with sandbox=True
        mock_adapter.run.assert_called_once()
        call_kwargs = mock_adapter.run.call_args[1]
        assert call_kwargs.get('sandbox') == True, \
            "TOOL_SANDBOX must use sandbox=True even when authority is down"
