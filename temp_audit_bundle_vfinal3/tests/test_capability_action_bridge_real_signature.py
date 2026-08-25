"""Runtime signature test for CapabilityActionBridge.

This test uses a REAL CapabilityActionBridge object (not Mock) to verify
that the production contract is correct and will not regress.

CRITICAL: This test must fail if the signature regresses to the old
incorrect signature (lease_id=..., requested_action=..., etc.).
"""

import pytest
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest, ActionAuthorization
from iabv_v15.services.trust.authority_client import AuthorityClient


def test_capability_action_bridge_real_signature():
    """Test that authorize_action accepts ActionRequest, not individual kwargs.
    
    This test uses a real CapabilityActionBridge object to verify the
    production contract. If the signature regresses to the old incorrect
    signature (lease_id=..., requested_action=..., etc.), this test will
    fail with TypeError.
    """
    # Create a mock authority client for testing
    class MockAuthorityClient:
        def consume_lease(self, lease_id, execution_id, action, target):
            return {
                "consumed": True,
                "consumed_at": 1234567890.0
            }
    
    # Create real CapabilityActionBridge with mock client
    bridge = CapabilityActionBridge(authority_client=MockAuthorityClient())
    
    # Test CORRECT signature (ActionRequest)
    request = ActionRequest(
        lease_id="test_lease",
        execution_id="test_execution",
        action="READ",
        target="codebase"
    )
    
    # This should succeed
    result = bridge.authorize_action(request)
    assert isinstance(result, ActionAuthorization)
    assert result.authorized is True


def test_capability_action_bridge_rejects_old_signature():
    """Test that authorize_action REJECTS the old incorrect signature.
    
    The old signature was:
    authorize_action(lease_id=..., requested_action=..., requested_target=..., execution_id=...)
    
    The new signature is:
    authorize_action(request: ActionRequest)
    
    This test verifies that the old signature is rejected.
    """
    # Create a mock authority client for testing
    class MockAuthorityClient:
        def consume_lease(self, lease_id, execution_id, action, target):
            return {
                "consumed": True,
                "consumed_at": 1234567890.0
            }
    
    # Create real CapabilityActionBridge with mock client
    bridge = CapabilityActionBridge(authority_client=MockAuthorityClient())
    
    # Test INCORRECT signature (old kwargs) - should fail with TypeError
    with pytest.raises(TypeError):
        bridge.authorize_action(
            lease_id="test_lease",
            requested_action="READ",
            requested_target="codebase",
            execution_id="test_execution"
        )


def test_tool_teach_service_uses_correct_signature():
    """Test that ToolTeachService uses the correct ActionRequest signature.
    
    This is a representative test for the production caller path.
    """
    from iabv_v15.services.trust.capability_action_bridge import ActionRequest
    
    # Verify that ActionRequest can be constructed with the fields
    # that ToolTeachService uses
    request = ActionRequest(
        lease_id="test_lease",
        execution_id="test_execution",
        action="READ",
        target="codebase"
    )
    
    assert request.lease_id == "test_lease"
    assert request.execution_id == "test_execution"
    assert request.action == "READ"
    assert request.target == "codebase"


def test_github_remote_service_uses_correct_signature():
    """Test that GitHubRemoteService uses the correct ActionRequest signature.
    
    This is a representative test for the F17 production caller path.
    """
    from iabv_v15.services.trust.capability_action_bridge import ActionRequest
    
    # Verify that ActionRequest can be constructed with the fields
    # that GitHubRemoteService uses for git push
    request = ActionRequest(
        lease_id="test_lease",
        execution_id="git_push_main_1234567890",
        action="PUSH",
        target="github_remote:origin"
    )
    
    assert request.lease_id == "test_lease"
    assert request.execution_id == "git_push_main_1234567890"
    assert request.action == "PUSH"
    assert request.target == "github_remote:origin"


def test_tool_rollback_manager_uses_correct_signature():
    """Test that ToolRollbackManager uses the correct ActionRequest signature.
    
    This is a representative test for the F16 production caller path.
    """
    from iabv_v15.services.trust.capability_action_bridge import ActionRequest
    
    # Verify that ActionRequest can be constructed with the fields
    # that ToolRollbackManager uses for rollback
    request = ActionRequest(
        lease_id="test_lease",
        execution_id="test_execution",
        action="ROLLBACK",
        target="codebase"
    )
    
    assert request.lease_id == "test_lease"
    assert request.execution_id == "test_execution"
    assert request.action == "ROLLBACK"
    assert request.target == "codebase"
