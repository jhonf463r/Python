"""P0.213 Phase 4: Capability Action Bridge Tests

Tests for the capability → action → result → observation pipeline.

Phase 4 Status: IMPLEMENTED
"""

from __future__ import annotations

import time
from unittest.mock import Mock

from iabv_v15.domain.models import (
    ExecutionState,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.services.trust.authority_protocol import ConsumeLeaseResponse
from iabv_v15.services.trust.capability_action_bridge import (
    ActionAuthorization,
    ActionRequest,
    CapabilityActionBridge,
)
from iabv_v15.services.trust.post_action_observer import (
    ActionObservation,
    PostActionObserver,
)


def _mock_tool_result(success: bool = True) -> ToolResult:
    """Create a mock ToolResult."""
    return ToolResult(
        result_id="test_result_id",
        task_id="test_task_id",
        tool_id="test_tool",
        tool_type=ToolType.SHELL,
        success=success,
        output_text="test output" if success else "",
        error_message="test error" if not success else "",
        execution_state=ExecutionState(state="executed" if success else "failed"),
        created_at=time.time(),
    )


def _mock_tool_card() -> ToolCard:
    """Create a mock ToolCard."""
    return ToolCard(
        tool_id="test_tool",
        title="Test Tool",
        tool_type=ToolType.SHELL,
        adapter_key="local_cli",
        requires_human_approval=False,
        available=True,
        success_count=0,
        failure_count=0,
        validation_status=ToolValidationStatus.VALID,
        metadata={"command_name": "echo", "allowed_verbs": ["--version"]},
    )


def test_authorize_action_with_valid_capability():
    """Test F: valid capability - expected = ACCEPTED, action executed = TRUE."""
    # Arrange
    mock_client = Mock()
    mock_client.consume_lease.return_value = ConsumeLeaseResponse(
        consumed=True,
        consumed_at=time.time()
    ).to_dict()
    
    bridge = CapabilityActionBridge(mock_client)
    request = ActionRequest(
        lease_id="test_lease_id",
        execution_id="test_execution_id",
        action="READ",
        target="codebase",
    )
    
    # Act
    authorization = bridge.authorize_action(request)
    
    # Assert
    assert authorization.authorized is True
    assert authorization.consumed_at is not None
    assert authorization.error is None
    mock_client.consume_lease.assert_called_once_with(
        "test_lease_id",
        "test_execution_id",
        "READ",
        "codebase"
    )


def test_authorize_action_with_invalid_capability():
    """Test E: fabricated/invalid capability - expected = REJECTED, action executed = FALSE."""
    # Arrange
    mock_client = Mock()
    mock_client.consume_lease.side_effect = Exception("Lease not found")
    
    bridge = CapabilityActionBridge(mock_client)
    request = ActionRequest(
        lease_id="invalid_lease_id",
        execution_id="test_execution_id",
        action="READ",
        target="codebase",
    )
    
    # Act
    authorization = bridge.authorize_action(request)
    
    # Assert
    assert authorization.authorized is False
    assert authorization.error is not None
    assert "Capability consumption failed" in authorization.error


def test_authorize_action_with_replayed_capability():
    """Test D: replayed capability - expected = REJECTED, action executed = FALSE."""
    # Arrange
    mock_client = Mock()
    mock_client.consume_lease.return_value = ConsumeLeaseResponse(
        consumed=False,
        consumed_at=None
    ).to_dict()
    
    bridge = CapabilityActionBridge(mock_client)
    request = ActionRequest(
        lease_id="replayed_lease_id",
        execution_id="test_execution_id",
        action="READ",
        target="codebase",
    )
    
    # Act
    authorization = bridge.authorize_action(request)
    
    # Assert
    assert authorization.authorized is False
    assert authorization.error == "Capability not consumed"


def test_authorize_action_with_cross_execution_capability():
    """Test C: cross-execution capability - expected = REJECTED, action executed = FALSE."""
    # Arrange
    mock_client = Mock()
    mock_client.consume_lease.side_effect = Exception("Execution ID mismatch")
    
    bridge = CapabilityActionBridge(mock_client)
    request = ActionRequest(
        lease_id="cross_execution_lease_id",
        execution_id="wrong_execution_id",
        action="READ",
        target="codebase",
    )
    
    # Act
    authorization = bridge.authorize_action(request)
    
    # Assert
    assert authorization.authorized is False
    assert authorization.error is not None


def test_authorize_action_with_wrong_target():
    """Test B: wrong target - expected = REJECTED, action executed = FALSE.
    
    Note: In the minimal implementation, target validation is deferred to the authority
    during consumption. This test verifies the bridge correctly handles rejection.
    """
    # Arrange
    mock_client = Mock()
    mock_client.consume_lease.side_effect = Exception("Target mismatch")
    
    bridge = CapabilityActionBridge(mock_client)
    request = ActionRequest(
        lease_id="test_lease_id",
        execution_id="test_execution_id",
        action="READ",
        target="wrong_target",
    )
    
    # Act
    authorization = bridge.authorize_action(request)
    
    # Assert
    assert authorization.authorized is False
    assert authorization.error is not None


def test_authorize_action_with_wrong_action():
    """Test A: wrong action - expected = REJECTED, action executed = FALSE.
    
    Note: In the minimal implementation, action validation is deferred to the authority
    during consumption. This test verifies the bridge correctly handles rejection.
    """
    # Arrange
    mock_client = Mock()
    mock_client.consume_lease.side_effect = Exception("Action mismatch")
    
    bridge = CapabilityActionBridge(mock_client)
    request = ActionRequest(
        lease_id="test_lease_id",
        execution_id="test_execution_id",
        action="WRITE",
        target="codebase",
    )
    
    # Act
    authorization = bridge.authorize_action(request)
    
    # Assert
    assert authorization.authorized is False
    assert authorization.error is not None


def test_post_action_observer_creates_observation():
    """Test G: valid action result - expected = OBSERVATION_CREATED."""
    # Arrange
    observer = PostActionObserver()
    result = _mock_tool_result(success=True)
    
    # Act
    observation = observer.observe_action_result(
        run_id="test_run_id",
        execution_id="test_execution_id",
        lease_id="test_lease_id",
        action="READ",
        target="codebase",
        result=result,
    )
    
    # Assert
    assert observation.run_id == "test_run_id"
    assert observation.execution_id == "test_execution_id"
    assert observation.lease_id == "test_lease_id"
    assert observation.action == "READ"
    assert observation.target == "codebase"
    assert observation.success is True
    assert observation.result_id == "test_result_id"
    assert observation.observed_at is not None
    assert len(observer.get_observations()) == 1


def test_post_action_observer_records_failure():
    """Test that observer records failed actions."""
    # Arrange
    observer = PostActionObserver()
    result = _mock_tool_result(success=False)
    
    # Act
    observation = observer.observe_action_result(
        run_id="test_run_id",
        execution_id="test_execution_id",
        lease_id="test_lease_id",
        action="READ",
        target="codebase",
        result=result,
    )
    
    # Assert
    assert observation.success is False
    assert observation.metadata["error_message"] == "test error"


def test_post_action_observer_filters_by_execution():
    """Test that observer can filter observations by execution_id."""
    # Arrange
    observer = PostActionObserver()
    
    result1 = _mock_tool_result(success=True)
    observer.observe_action_result(
        run_id="run1",
        execution_id="exec1",
        lease_id="lease1",
        action="READ",
        target="codebase",
        result=result1,
    )
    
    result2 = _mock_tool_result(success=True)
    observer.observe_action_result(
        run_id="run2",
        execution_id="exec2",
        lease_id="lease2",
        action="WRITE",
        target="codebase",
        result=result2,
    )
    
    # Act
    exec1_observations = observer.get_observations_for_execution("exec1")
    exec2_observations = observer.get_observations_for_execution("exec2")
    
    # Assert
    assert len(exec1_observations) == 1
    assert len(exec2_observations) == 1
    assert exec1_observations[0].execution_id == "exec1"
    assert exec2_observations[0].execution_id == "exec2"


def test_validate_action_binding_with_valid_authorization():
    """Test action binding validation with valid authorization."""
    # Arrange
    bridge = CapabilityActionBridge(Mock())
    authorization = ActionAuthorization(
        authorized=True,
        consumed_at=time.time()
    )
    
    # Act
    valid = bridge.validate_action_binding(
        authorization,
        requested_action="READ",
        requested_target="codebase"
    )
    
    # Assert
    assert valid is True


def test_validate_action_binding_with_invalid_authorization():
    """Test action binding validation with invalid authorization."""
    # Arrange
    bridge = CapabilityActionBridge(Mock())
    authorization = ActionAuthorization(
        authorized=False,
        error="Invalid capability"
    )
    
    # Act
    valid = bridge.validate_action_binding(
        authorization,
        requested_action="READ",
        requested_target="codebase"
    )
    
    # Assert
    assert valid is False
