"""Tests for per-invocation credential seam in DevinApiToolAdapter

Tests synthetic credentials and mocked HTTP boundary without real Devin calls.
"""

import sys
from unittest.mock import Mock, patch

sys.path.insert(0, 'src')

from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
from iabv_v15.domain.models import ToolCard, ToolTask, ToolType


def _make_card() -> ToolCard:
    return ToolCard(
        tool_id='devin_api',
        title='Devin (Cognition AI)',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        metadata={'assistant_kind': 'devin'},
    )


def _make_task(objective: str = 'test task') -> ToolTask:
    return ToolTask(
        tool_id='devin_api',
        title='Test task',
        objective=objective,
        actions=[],
        metadata={},
    )


def test_backward_compatibility():
    """Test A: backward compatibility - constructor key used when no override."""
    print("Test A: Backward compatibility")
    
    adapter = DevinApiToolAdapter(
        api_key='constructor-key'
    )
    
    card = _make_card()
    task = _make_task()
    
    with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
        mock_post = Mock()
        mock_get = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        
        # Mock successful session creation
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'session_id': 'test-session',
            'url': 'https://test.com/session',
            'status': 'finished',
            'structured_output': 'test output'
        }
        
        result = adapter.run(card, task, sandbox=False)
        
        # Verify constructor key was used
        assert mock_post.called
        call_headers = mock_post.call_args[1]['headers']
        assert 'Bearer constructor-key' in call_headers['Authorization']
        print("  PASS: Constructor key used when no override")


def test_per_invocation_override():
    """Test B: per-invocation override - invocation key dominates both POST and GET."""
    print("\nTest B: Per-invocation override")
    
    adapter = DevinApiToolAdapter(
        api_key='constructor-key'
    )
    
    card = _make_card()
    task = _make_task()
    
    with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
        mock_post = Mock()
        mock_get = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        
        # POST creates session in 'running' state to trigger polling
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'session_id': 'test-session',
            'url': 'https://test.com/session',
            'status': 'running',
            'structured_output': ''
        }
        
        # GET returns finished state
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'status': 'finished',
            'structured_output': 'test output'
        }
        
        result = adapter.run(card, task, api_key='invocation-key')
        
        # Verify invocation key was used in POST (create session)
        assert mock_post.called
        post_headers = mock_post.call_args[1]['headers']
        assert 'Bearer invocation-key' in post_headers['Authorization']
        
        # Verify invocation key was used in GET (poll session)
        assert mock_get.called
        get_headers = mock_get.call_args[1]['headers']
        assert 'Bearer invocation-key' in get_headers['Authorization']
        
        print("  PASS: Invocation key used in both POST and GET")


def test_no_mutation():
    """Test C: adapter instance not mutated after override."""
    print("\nTest C: No mutation")
    
    adapter = DevinApiToolAdapter(
        api_key='constructor-key'
    )
    
    card = _make_card()
    task = _make_task()
    
    with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
        mock_post = Mock()
        mock_get = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'session_id': 'test-session',
            'url': 'https://test.com/session',
            'status': 'finished',
            'structured_output': 'test output'
        }
        
        adapter.run(card, task, api_key='invocation-key')
        
        # Verify instance not mutated
        assert adapter.api_key == 'constructor-key'
        print("  PASS: Adapter instance not mutated")


def test_omission_fallback():
    """Test D: omission fallback - None uses constructor key."""
    print("\nTest D: Omission fallback")
    
    adapter = DevinApiToolAdapter(
        api_key='constructor-key'
    )
    
    card = _make_card()
    task = _make_task()
    
    with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
        mock_post = Mock()
        mock_get = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'session_id': 'test-session',
            'url': 'https://test.com/session',
            'status': 'finished',
            'structured_output': 'test output'
        }
        
        result = adapter.run(card, task, api_key=None)
        
        # Verify constructor key was used
        assert mock_post.called
        call_headers = mock_post.call_args[1]['headers']
        assert 'Bearer constructor-key' in call_headers['Authorization']
        print("  PASS: Constructor key used when api_key=None")


def test_no_secret_leakage():
    """Test E: no secret leakage - synthetic keys not in result metadata."""
    print("\nTest E: No secret leakage")
    
    synthetic_keys = ['constructor-key', 'invocation-key']
    
    adapter = DevinApiToolAdapter(
        api_key=synthetic_keys[0]
    )
    
    card = _make_card()
    task = _make_task()
    
    with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
        mock_post = Mock()
        mock_get = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'session_id': 'test-session',
            'url': 'https://test.com/session',
            'status': 'finished',
            'structured_output': 'test output'
        }
        
        result = adapter.run(card, task, sandbox=False, api_key=synthetic_keys[1])
        
        # Verify invocation key not in result metadata
        result_str = str(result)
        assert synthetic_keys[1] not in result_str, f"Secret leaked: {synthetic_keys[1]}"
        # Constructor key is in adapter instance (by design), but that's acceptable
        # The key point is that invocation key is not persisted beyond this call
        
        print("  PASS: Invocation key not in result metadata")


def test_health_non_effect():
    """Test F: health check does not create sessions."""
    print("\nTest F: Health non-effect")
    
    from iabv_v15.services.trust.devin_credential_adapter import DevinCredentialAdapter
    from iabv_v15.services.trust.provider_credential_adapter import (
        CredentialRecord,
        CredentialStatus,
        HealthState,
        QuotaState,
    )
    
    adapter = DevinCredentialAdapter()
    
    record = CredentialRecord(
        credential_id='test-id',
        provider='devin',
        principal_id='',
        credential_type='legacy_service_v1',
        secret_ref='TEST_KEY',
        api_version='v1',
        status=CredentialStatus.UNKNOWN,
    )
    
    with patch('iabv_v15.services.trust.devin_credential_adapter.httpx') as mock_httpx:
        # Verify no POST to sessions
        adapter.check_health(record, 'synthetic-key')
        
        # Health state should be UNKNOWN (no endpoint available)
        assert record.health_state == HealthState.UNKNOWN
        assert record.quota_state == QuotaState.UNKNOWN
        assert record.last_error_code == 'health_endpoint_unavailable'
        
        # Verify no POST was made
        assert not mock_httpx.post.called
    
    print("  PASS: Health check does not create sessions")


def test_forbidden_does_not_claim_partial_authorization():
    """Test G: 403 forbidden does not claim partial authorization - states remain UNKNOWN."""
    print("\nTest G: Forbidden does not claim partial authorization")
    
    from iabv_v15.services.trust.devin_credential_adapter import DevinCredentialAdapter
    from iabv_v15.services.trust.provider_credential_adapter import (
        AuthState,
        AuthorizationState,
        CredentialRecord,
        CredentialStatus,
        HealthState,
    )
    
    adapter = DevinCredentialAdapter()
    
    record = CredentialRecord(
        credential_id='test-id',
        provider='devin',
        principal_id='',
        credential_type='legacy_service_v1',
        secret_ref='TEST_KEY',
        api_version='v3',
        status=CredentialStatus.UNKNOWN,
    )
    
    with patch('iabv_v15.services.trust.devin_credential_adapter.httpx') as mock_httpx:
        # Simulate 403 with out_of_quota detail (context: this is what provider might return)
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            'detail': 'Your organization has a billing error. Error: out_of_quota'
        }
        mock_httpx.get.return_value = mock_response
        
        adapter.check_health(record, 'synthetic-key')
        
        # Current behavior: 403 produces AUTHENTICATED but UNKNOWN for authz/health
        assert record.auth_state == AuthState.AUTHENTICATED, \
            "403 should indicate credential was accepted (authenticated)"
        # Authorization state remains UNKNOWN (code does not parse body)
        assert record.authorization_state == AuthorizationState.UNKNOWN, \
            "Authorization should be UNKNOWN, not inferred from 403"
        # Health state remains UNKNOWN (code does not parse body)
        assert record.health_state == HealthState.UNKNOWN, \
            "Health should be UNKNOWN, not inferred from 403"
        # PARTIALLY_AUTHORIZED must not be claimed
        assert record.authorization_state != AuthorizationState.PARTIALLY_AUTHORIZED, \
            "PARTIALLY_AUTHORIZED must not be inferred from 403"
    
    print("  PASS: Forbidden does not claim partial authorization")


def test_identity_not_derived():
    """Test H: identity not derived from secret - principal_id remains empty."""
    print("\nTest H: Identity not derived from secret")
    
    from iabv_v15.services.trust.devin_credential_adapter import DevinCredentialAdapter
    
    adapter = DevinCredentialAdapter()
    
    # Use a variable that discover() actually recognizes: DEVIN_API_KEY
    # Monkeypatch environment to isolate the test
    import os
    original_key = os.environ.get('DEVIN_API_KEY')
    os.environ['DEVIN_API_KEY'] = 'apk_test_synthetic_key'
    
    try:
        result = adapter.discover()
        
        # ASSERT that at least one record was discovered
        assert len(result.records) > 0, "No credentials discovered"
        
        # Find the record for DEVIN_API_KEY
        devin_record = None
        for record in result.records:
            if record.secret_ref == 'DEVIN_API_KEY':
                devin_record = record
                break
        
        # ASSERT that the record exists
        assert devin_record is not None, "DEVIN_API_KEY record not found"
        
        # ASSERT that principal_id is empty, not derived from secret prefix
        assert devin_record.principal_id == '', \
            f"Principal ID should be empty, got: {devin_record.principal_id}"
        
        print("  PASS: Identity not derived from secret")
    finally:
        # Restore original environment
        if original_key is None:
            os.environ.pop('DEVIN_API_KEY', None)
        else:
            os.environ['DEVIN_API_KEY'] = original_key


def test_negative_secret_leak():
    """Negative test: invocation key must not leak into result metadata."""
    print("\nNegative test: Secret leak detection")
    
    adapter = DevinApiToolAdapter(
        api_key='constructor-key'
    )
    
    card = _make_card()
    task = _make_task()
    
    synthetic_invocation_key = 'synthetic-invocation-secret'
    
    with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
        mock_post = Mock()
        mock_get = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'session_id': 'test-session',
            'url': 'https://test.com/session',
            'status': 'finished',
            'structured_output': 'test output'
        }
        
        result = adapter.run(card, task, api_key=synthetic_invocation_key)
        
        # Assertion: invocation key must NOT appear in result
        result_str = str(result)
        assert synthetic_invocation_key not in result_str, \
            f"Invocation key leaked into result: {synthetic_invocation_key}"
        
        # Constructor key is in adapter instance (by design), but invocation key must not persist
        assert adapter.api_key == 'constructor-key', \
            "Adapter instance was mutated"
        
        print("  PASS: Invocation key does not leak into result metadata")


if __name__ == "__main__":
    test_backward_compatibility()
    test_per_invocation_override()
    test_no_mutation()
    test_omission_fallback()
    test_no_secret_leakage()
    test_health_non_effect()
    test_forbidden_does_not_claim_partial_authorization()
    test_identity_not_derived()
    test_negative_secret_leak()
    
    print("\n" + "=" * 60)
    print("ALL SEAM TESTS PASSED")
    print("=" * 60)
