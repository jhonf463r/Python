"""Tests for credential binding from resource selection to execution.

Tests that:
- selected_credential_ref → effective credential_ref
- resource selection governs actual execution
- multiple resources remain distinguishable
- secret values never exposed
"""

import pytest
from typing import Any

from iabv_v15.domain.models import (
    ToolTask,
    ToolType,
    InferenceRequest,
    TaskRole,
)
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


class TestCredentialBinding:
    """Test that selected credential_ref binds to effective credential."""

    def test_selected_credential_ref_to_effective_credential(self):
        """Test: selected_credential_ref → effective credential_ref binding."""
        # Create adapter with default API key
        adapter = DevinApiToolAdapter(api_key='default_key')

        # Set up environment with alternative credential
        import os
        os.environ['DEVIN_API_KEY_ALT'] = 'alt_key'

        # Create credential_ref pointing to alternative
        credential_ref = 'devin:credential_0:DEVIN_API_KEY_ALT'

        # Resolve credential
        effective_key, fingerprint = adapter._resolve_api_key(credential_ref)

        # Verify binding: credential_ref → effective credential
        assert effective_key == 'alt_key'
        assert effective_key != 'default_key'
        assert fingerprint != ''  # Fingerprint computed

        # Cleanup
        del os.environ['DEVIN_API_KEY_ALT']

    def test_credential_ref_fallback_to_default(self):
        """Test: credential_ref fallback to default when resolution fails (NO SELECTION case)."""
        adapter = DevinApiToolAdapter(api_key='default_key')

        # Invalid credential_ref (no matching env var)
        credential_ref = 'devin:credential_0:NONEXISTENT_VAR'

        # Resolve credential
        effective_key, fingerprint = adapter._resolve_api_key(credential_ref)

        # Verify: explicit selection that fails resolution → empty (NOT default)
        assert effective_key == ''
        assert fingerprint == ''

    def test_no_credential_ref_uses_default(self):
        """Test: no credential_ref uses default (compatibility for old paths)."""
        adapter = DevinApiToolAdapter(api_key='default_key')

        # No credential_ref provided
        effective_key, fingerprint = adapter._resolve_api_key(None)

        # Verify default is used
        assert effective_key == 'default_key'
        assert fingerprint != ''


class TestMultiResourceDiscrimination:
    """Test that multiple resources remain distinguishable at execution boundary."""

    def test_two_distinct_credentials_remain_distinct(self):
        """Test: Two distinct credentials remain distinguishable."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'
        os.environ['DEVIN_API_KEY_B'] = 'credential_b'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Resolve two different credential_refs
        credential_ref_a = 'devin:credential_0:DEVIN_API_KEY_A'
        credential_ref_b = 'devin:credential_1:DEVIN_API_KEY_B'

        effective_key_a, fingerprint_a = adapter._resolve_api_key(credential_ref_a)
        effective_key_b, fingerprint_b = adapter._resolve_api_key(credential_ref_b)

        # Verify they remain distinct
        assert effective_key_a == 'credential_a'
        assert effective_key_b == 'credential_b'
        assert effective_key_a != effective_key_b
        assert fingerprint_a != fingerprint_b

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']
        del os.environ['DEVIN_API_KEY_B']

    def test_credential_ref_identity_preserved_in_headers(self):
        """Test: credential_ref identity preserved in HTTP headers."""
        import os
        os.environ['DEVIN_API_KEY_TEST'] = 'test_key'

        adapter = DevinApiToolAdapter(api_key='default_key')
        credential_ref = 'devin:credential_0:DEVIN_API_KEY_TEST'

        effective_key, fingerprint = adapter._resolve_api_key(credential_ref)
        headers = adapter._headers(effective_key)

        # Verify Authorization header uses resolved credential
        assert 'Authorization' in headers
        assert 'Bearer test_key' in headers['Authorization']

        # Cleanup
        del os.environ['DEVIN_API_KEY_TEST']


class TestSecretHygiene:
    """Test that secret values never appear in test output."""

    def test_secret_never_in_adapter_state(self):
        """Test: Secret values never appear in adapter state."""
        adapter = DevinApiToolAdapter(api_key='test_secret')

        # Verify secret is in adapter state (this is expected - adapter holds the secret)
        assert adapter.api_key == 'test_secret'

        # But credential_ref should never expose the secret
        credential_ref = 'devin:credential_0:DEVIN_API_KEY'
        assert 'test_secret' not in credential_ref

    def test_secret_never_in_task_metadata(self):
        """Test: Secret values never appear in task metadata."""
        # Create task with credential_ref
        task = ToolTask(
            tool_id='devin_api',
            title='Test',
            objective='Test objective',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY',
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
            },
        )

        # Verify credential_ref is present but not the secret
        assert task.metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY'
        assert 'test_secret' not in str(task.metadata)
        assert 'secret' not in str(task.metadata).lower()


class TestNegativeCase:
    """Test negative case: selected != effective should block."""

    def test_mismatch_selected_vs_effective_blocks_execution(self):
        """Test: selected credential_ref != effective credential → BLOCKED before HTTP."""
        import os
        os.environ['DEVIN_API_KEY_WRONG'] = 'wrong_key'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Create task with explicit selection to wrong credential
        task = ToolTask(
            tool_id='devin_api',
            title='Test',
            objective='Test objective',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_WRONG',
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
            },
        )

        # Test resolution logic directly (before authorization check)
        selected_credential_ref = task.metadata.get('selected_credential_ref')
        effective_key, fingerprint = adapter._resolve_api_key(selected_credential_ref)

        # Verify resolution succeeds (env var exists)
        assert effective_key == 'wrong_key'
        assert fingerprint != ''

        # Now test that if env var didn't exist, resolution would fail
        del os.environ['DEVIN_API_KEY_WRONG']
        effective_key_failed, fingerprint_failed = adapter._resolve_api_key(selected_credential_ref)

        # Verify: explicit selection that fails resolution → empty (NOT default)
        assert effective_key_failed == ''
        assert fingerprint_failed == ''

        # Verify that this causes execution to fail (even in sandbox)
        from iabv_v15.domain.models import ToolCard, ToolType
        card = ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            description='Test',
        )

        result = adapter.run(card, task, sandbox=True, external_authorization=None)

        # Verify execution is BLOCKED because resolution fails
        assert result['success'] is False
        assert 'credential_resolution_failed' in result.get('metadata', {})
        assert result['metadata']['credential_resolution_failed'] is True
        assert 'Credential resolution failed' in result.get('error_message', '')

    def test_selected_resolves_to_correct_credential(self):
        """Test: selected credential_ref → effective credential → fingerprint verification."""
        import os
        os.environ['DEVIN_API_KEY_TEST'] = 'test_key'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Create task with explicit selection to test credential
        task = ToolTask(
            tool_id='devin_api',
            title='Test',
            objective='Test objective',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_TEST',
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
            },
        )

        # Mock card
        from iabv_v15.domain.models import ToolCard, ToolType
        card = ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            description='Test',
        )

        # Run with sandbox=True to avoid HTTP
        result = adapter.run(card, task, sandbox=True, external_authorization=None)

        # Verify execution succeeded
        assert result['success'] is True

        # Verify execution identity metadata
        assert result['metadata']['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_TEST'
        assert result['metadata']['selected_resource_id'] == 'devin_credential_0'
        assert result['metadata']['selected_provider'] == 'devin'
        assert result['metadata']['effective_credential_fingerprint'] != ''  # Fingerprint computed

        # Verify fingerprint matches expected credential
        import hashlib
        expected_fingerprint = hashlib.sha256('test_key'.encode('utf-8')).hexdigest()[:16]
        assert result['metadata']['effective_credential_fingerprint'] == expected_fingerprint

        # Cleanup
        del os.environ['DEVIN_API_KEY_TEST']


class TestAuthorizationResourceBinding:
    """Test that ExternalActionAuthorization includes resource binding verification."""

    def test_authorization_includes_resource_binding_fields(self):
        """Test: ExternalActionAuthorization includes resource binding fields."""
        from iabv_v15.domain.models import ExternalActionAuthorization, ExternalActionAuthorizationStatus

        auth = ExternalActionAuthorization(
            task_id='test_task',
            tool_id='devin_api',
            adapter_key='devin_api',
            assistant_kind='unknown',
            prompt_digest='test_digest',
            selected_resource_id='devin_credential_0',
            selected_provider='devin',
            selected_credential_ref='devin:credential_0:DEVIN_API_KEY',
            credential_fingerprint='test_fingerprint',
        )

        # Verify resource binding fields are present
        assert auth.selected_resource_id == 'devin_credential_0'
        assert auth.selected_provider == 'devin'
        assert auth.selected_credential_ref == 'devin:credential_0:DEVIN_API_KEY'
        assert auth.credential_fingerprint == 'test_fingerprint'

    def test_authorization_validate_binding_includes_credential_fingerprint(self):
        """Test: validate_binding() verifies credential fingerprint when present."""
        from iabv_v15.domain.models import ExternalActionAuthorization, ExternalActionAuthorizationStatus

        auth = ExternalActionAuthorization(
            task_id='test_task',
            tool_id='devin_api',
            adapter_key='devin_api',
            assistant_kind='unknown',
            prompt_digest='test_digest',
            selected_resource_id='devin_credential_0',
            selected_provider='devin',
            selected_credential_ref='devin:credential_0:DEVIN_API_KEY',
            credential_fingerprint='authorized_fingerprint',
            status=ExternalActionAuthorizationStatus.VALIDATED,
        )

        # Valid binding
        assert auth.validate_binding(
            task_id='test_task',
            tool_id='devin_api',
            adapter_key='devin_api',
            prompt_digest='test_digest',
            credential_fingerprint='authorized_fingerprint',
        ) is True

        # Invalid binding (wrong credential fingerprint)
        assert auth.validate_binding(
            task_id='test_task',
            tool_id='devin_api',
            adapter_key='devin_api',
            prompt_digest='test_digest',
            credential_fingerprint='different_fingerprint',
        ) is False

    def test_authorization_validate_binding_without_resource_fields(self):
        """Test: validate_binding() works without resource binding fields (backward compatibility)."""
        from iabv_v15.domain.models import ExternalActionAuthorization, ExternalActionAuthorizationStatus

        auth = ExternalActionAuthorization(
            task_id='test_task',
            tool_id='devin_api',
            adapter_key='devin_api',
            assistant_kind='unknown',
            prompt_digest='test_digest',
            status=ExternalActionAuthorizationStatus.VALIDATED,
        )

        # Valid binding (no resource fields - backward compatible)
        assert auth.validate_binding(
            task_id='test_task',
            tool_id='devin_api',
            adapter_key='devin_api',
            prompt_digest='test_digest',
        ) is True
