"""
ActionRequest Contract Regression Test

This test ensures that the ActionRequest dataclass contract is used correctly
and prevents future regressions where incorrect parameters are passed.
"""

import pytest
from iabv_v15.services.trust.capability_action_bridge import ActionRequest


def test_actionrequest_contract_correct_fields():
    """ActionRequest must use lease_id, execution_id, action, target, action_context."""
    # This should succeed with correct contract
    action_request = ActionRequest(
        lease_id='test_lease',
        execution_id='test_execution',
        action='WRITE_REPOSITORY_FILE',
        target='file:test.txt',
        action_context={'requested_scope': 'self_update'},
    )
    
    assert action_request.lease_id == 'test_lease'
    assert action_request.execution_id == 'test_execution'
    assert action_request.action == 'WRITE_REPOSITORY_FILE'
    assert action_request.target == 'file:test.txt'
    assert action_request.action_context == {'requested_scope': 'self_update'}


def test_actionrequest_rejects_invalid_fields():
    """ActionRequest must reject invalid fields like requested_scope, invocation_id."""
    # These should fail with TypeError (incorrect field names)
    with pytest.raises(TypeError):
        ActionRequest(
            action='WRITE_REPOSITORY_FILE',
            target='file:test.txt',
            requested_scope='self_update',  # INVALID FIELD
            invocation_id='write_test.txt',  # INVALID FIELD
        )


def test_actionrequest_requires_lease_id():
    """ActionRequest requires lease_id parameter."""
    with pytest.raises(TypeError):
        ActionRequest(
            execution_id='test_execution',
            action='WRITE_REPOSITORY_FILE',
            target='file:test.txt',
            action_context={'requested_scope': 'self_update'},
        )


def test_actionrequest_requires_execution_id():
    """ActionRequest requires execution_id parameter."""
    with pytest.raises(TypeError):
        ActionRequest(
            lease_id='test_lease',
            action='WRITE_REPOSITORY_FILE',
            target='file:test.txt',
            action_context={'requested_scope': 'self_update'},
        )


def test_actionrequest_requires_action():
    """ActionRequest requires action parameter."""
    with pytest.raises(TypeError):
        ActionRequest(
            lease_id='test_lease',
            execution_id='test_execution',
            target='file:test.txt',
            action_context={'requested_scope': 'self_update'},
        )


def test_actionrequest_requires_target():
    """ActionRequest requires target parameter."""
    with pytest.raises(TypeError):
        ActionRequest(
            lease_id='test_lease',
            execution_id='test_execution',
            action='WRITE_REPOSITORY_FILE',
            action_context={'requested_scope': 'self_update'},
        )


def test_actionrequest_action_context_is_dict():
    """ActionRequest action_context should be a dict."""
    action_request = ActionRequest(
        lease_id='test_lease',
        execution_id='test_execution',
        action='WRITE_REPOSITORY_FILE',
        target='file:test.txt',
        action_context={'requested_scope': 'self_update'},
    )
    
    assert isinstance(action_request.action_context, dict)


def test_actionrequest_no_dict_contract_allowed():
    """ActionRequest does not accept dict-style construction."""
    # This ensures we can't accidentally use dict contract in production
    with pytest.raises(TypeError):
        ActionRequest(**{
            'action': 'WRITE_REPOSITORY_FILE',
            'target': 'file:test.txt',
            'requested_scope': 'self_update',  # INVALID
        })
