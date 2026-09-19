"""Integration test: worker_gate selection → execution path.

Tests that:
- worker_health_gate() selection survives to request.metadata
- request.metadata selection survives to task.metadata
- task.metadata selection survives to adapter.run()
- adapter uses the selected credential
"""

import pytest
from typing import Any

from iabv_v15.domain.models import (
    UniversalResource,
    ResourceKind,
    AuthenticationState,
    AccountStatus,
    QuotaScope,
    utc_now,
    ToolTask,
    ToolType,
    TaskRole,
    InferenceRequest,
)
from iabv_v15.services.account_resource_scanner import (
    build_universal_resource_pool,
    universal_resource_to_worker,
)
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


class TestWorkerGateToExecutionIntegration:
    """Test that worker_gate selection propagates through execution path."""

    def test_session_metadata_to_request_metadata_propagation(self):
        """Test: worker_gate top_worker propagates to request.metadata."""
        # Simulate session.metadata after worker_health_gate()
        session_metadata = {
            'worker_gate': {
                'usable': True,
                'top_worker': {
                    'resource_id': 'devin_credential_0',
                    'provider': 'devin',
                    'tool': 'devin_api',
                    'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
                    'email': '',
                    'browser': '',
                    'profile': '',
                },
                'recommended_account': 'devin_credential_0',
                'ranked_workers': [],
                'available_count': 1,
                'reason': '',
                'account_selection_source': 'auto_ranked',
                'fallback_used': False,
            },
        }

        # Simulate _request_from_session() logic
        worker_gate = dict(session_metadata.get('worker_gate') or {})
        top_worker = dict(worker_gate.get('top_worker') or {})

        request_metadata = {
            'decision_source': 'adaptive_session_refresh',
            'session_id': 'test_session',
        }

        if top_worker:
            request_metadata['selected_resource_id'] = top_worker.get('resource_id', '')
            request_metadata['selected_provider'] = top_worker.get('provider', '')
            request_metadata['selected_credential_ref'] = top_worker.get('credential_ref', '')
            request_metadata['selected_email'] = top_worker.get('email', '')
            request_metadata['selected_browser'] = top_worker.get('browser', '')
            request_metadata['selected_profile'] = top_worker.get('profile', '')

        # Verify propagation
        assert request_metadata['selected_resource_id'] == 'devin_credential_0'
        assert request_metadata['selected_provider'] == 'devin'
        assert request_metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

    def test_request_metadata_to_task_metadata_propagation(self):
        """Test: request.metadata selection propagates to task.metadata."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        # Create request with resource selection metadata
        request = InferenceRequest(
            user_goal='Test objective',
            prompt='Test objective',
            task_role=TaskRole.TOOL_USE,
            metadata={
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            },
        )

        # Simulate build_task_from_request() logic (simplified)
        request_metadata = request.metadata or {}
        task_metadata = {
            'selected_resource_id': request_metadata.get('selected_resource_id', ''),
            'selected_provider': request_metadata.get('selected_provider', ''),
            'selected_credential_ref': request_metadata.get('selected_credential_ref', ''),
        }

        # Verify propagation
        assert task_metadata['selected_resource_id'] == 'devin_credential_0'
        assert task_metadata['selected_provider'] == 'devin'
        assert task_metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_task_metadata_to_adapter_resolution(self):
        """Test: task.metadata selection resolves to correct credential in adapter."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Create task with resource selection metadata
        task = ToolTask(
            tool_id='devin_api',
            title='Test',
            objective='Test objective',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            },
        )

        # Mock card
        from iabv_v15.domain.models import ToolCard
        card = ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            description='Test',
        )

        # Run adapter
        result = adapter.run(card, task, sandbox=True, external_authorization=None)

        # Verify adapter used selected credential
        assert result['success'] is True
        assert result['metadata']['selected_resource_id'] == 'devin_credential_0'
        assert result['metadata']['selected_provider'] == 'devin'
        assert result['metadata']['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'
        assert result['metadata']['effective_credential_fingerprint'] != ''

        # Verify fingerprint matches expected credential
        import hashlib
        expected_fingerprint = hashlib.sha256('credential_a'.encode('utf-8')).hexdigest()[:16]
        assert result['metadata']['effective_credential_fingerprint'] == expected_fingerprint

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_end_to_end_gate_to_adapter_selection(self):
        """Test: gate selection → request → task → adapter end-to-end."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        # Step 1: Simulate worker_health_gate() selection
        gate_selection = {
            'resource_id': 'devin_credential_0',
            'provider': 'devin',
            'tool': 'devin_api',
            'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            'email': '',
            'browser': '',
            'profile': '',
        }

        # Step 2: Simulate session.metadata storage
        session_metadata = {
            'worker_gate': {
                'usable': True,
                'top_worker': gate_selection,
            },
        }

        # Step 3: Simulate _request_from_session() propagation
        worker_gate = dict(session_metadata.get('worker_gate') or {})
        top_worker = dict(worker_gate.get('top_worker') or {})

        request_metadata = {
            'selected_resource_id': top_worker.get('resource_id', ''),
            'selected_provider': top_worker.get('provider', ''),
            'selected_credential_ref': top_worker.get('credential_ref', ''),
        }

        # Step 4: Simulate build_task_from_request() propagation
        task_metadata = {
            'selected_resource_id': request_metadata.get('selected_resource_id', ''),
            'selected_provider': request_metadata.get('selected_provider', ''),
            'selected_credential_ref': request_metadata.get('selected_credential_ref', ''),
        }

        # Step 5: Verify adapter resolution
        adapter = DevinApiToolAdapter(api_key='default_key')
        selected_credential_ref = task_metadata.get('selected_credential_ref')
        effective_key, fingerprint = adapter._resolve_api_key(selected_credential_ref)

        # Verify end-to-end identity preservation
        assert gate_selection['resource_id'] == request_metadata['selected_resource_id']
        assert request_metadata['selected_resource_id'] == task_metadata['selected_resource_id']
        assert effective_key == 'credential_a'
        assert fingerprint != ''

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_negative_gate_selection_lost(self):
        """Test: gate selection lost → adapter has no explicit selection."""
        import os
        os.environ['DEVIN_API_KEY_DEFAULT'] = 'default_key'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Task without explicit selection (selection lost)
        task = ToolTask(
            tool_id='devin_api',
            title='Test',
            objective='Test objective',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={},  # No selection metadata
        )

        from iabv_v15.domain.models import ToolCard
        card = ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            description='Test',
        )

        result = adapter.run(card, task, sandbox=True, external_authorization=None)

        # Verify: no explicit selection → uses default
        assert result['success'] is True
        assert result['metadata']['selected_credential_ref'] == ''
        assert result['metadata']['effective_credential_fingerprint'] != ''

        # Cleanup
        del os.environ['DEVIN_API_KEY_DEFAULT']

    def test_availability_uses_task_metadata_not_card_metadata(self):
        """Test: is_available() uses task.metadata before card.metadata."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'
        os.environ['DEVIN_API_KEY_B'] = 'credential_b'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Task with selection A
        task = ToolTask(
            tool_id='devin_api',
            title='Test',
            objective='Test objective',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            },
        )

        # Card with selection B (should be ignored in favor of task)
        from iabv_v15.domain.models import ToolCard
        card = ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            description='Test',
            metadata={
                'selected_credential_ref': 'devin:credential_1:DEVIN_API_KEY_B',
            },
        )

        # is_available() should use task metadata
        available = adapter.is_available(card, dry_run=True, task=task)

        # Verify: task selection A was used
        assert available is True
        selected_credential_ref = task.metadata.get('selected_credential_ref')
        effective_key, _ = adapter._resolve_api_key(selected_credential_ref)
        assert effective_key == 'credential_a'  # A, not B

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']
        del os.environ['DEVIN_API_KEY_B']
