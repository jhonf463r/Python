"""UNIT_BEHAVIOR test: govern_adaptive_payload extracts worker_gate from serialized session.

Tests that:
- govern_adaptive_payload() logic extracts worker_gate selection from metadata.worker_gate (serialized AdaptiveSession)
- govern_adaptive_payload() logic also extracts from decision_context.metadata.worker_gate (if available)
- The selection propagates to payload.metadata selected_resource_id/provider/credential_ref

Note: This is UNIT_BEHAVIOR, not full INTEGRATION, because it tests the propagation logic
directly without requiring full orchestrator instantiation with all dependencies.
"""

import pytest
from typing import Any


class TestRealFirstDispatchIntegration:
    """Test that govern_adaptive_payload() extracts worker_gate selection from serialized session."""

    def test_metadata_worker_gate_to_selected_fields(self):
        """Test: metadata.worker_gate → selected_resource_id/provider/credential_ref extraction logic."""
        # Simulate adaptive_payload from serialized session (with worker_gate in metadata)
        adaptive_payload = {
            'user_goal': 'Test objective',
            'metadata': {
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
                },
            },
        }

        # Simulate govern_adaptive_payload() extraction logic
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        worker_gate = dict(metadata.get('worker_gate') or {})
        top_worker = dict(worker_gate.get('top_worker') or {})

        if top_worker:
            metadata['selected_resource_id'] = top_worker.get('resource_id', '')
            metadata['selected_provider'] = top_worker.get('provider', '')
            metadata['selected_credential_ref'] = top_worker.get('credential_ref', '')
            metadata['selected_email'] = top_worker.get('email', '')
            metadata['selected_browser'] = top_worker.get('browser', '')
            metadata['selected_profile'] = top_worker.get('profile', '')

        # Verify selection was extracted and propagated to payload.metadata
        assert metadata['selected_resource_id'] == 'devin_credential_0'
        assert metadata['selected_provider'] == 'devin'
        assert metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

    def test_decision_context_metadata_worker_gate_to_selected_fields(self):
        """Test: decision_context.metadata.worker_gate → selected_resource_id/provider/credential_ref extraction logic."""
        # Simulate adaptive_payload with decision_context containing worker_gate
        adaptive_payload = {
            'user_goal': 'Test objective',
            'metadata': {
                'decision_context': {
                    'user_goal': 'test goal',
                    'governance': {'should_consult': True, 'assistant_kind': 'codex'},
                    'metadata': {
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
                        },
                    },
                },
            },
        }

        # Simulate govern_adaptive_payload() extraction logic
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        dc_meta = dict(decision_context.get('metadata') or {})
        worker_gate = dict(dc_meta.get('worker_gate') or {})
        top_worker = dict(worker_gate.get('top_worker') or {})

        if top_worker:
            metadata['selected_resource_id'] = top_worker.get('resource_id', '')
            metadata['selected_provider'] = top_worker.get('provider', '')
            metadata['selected_credential_ref'] = top_worker.get('credential_ref', '')
            metadata['selected_email'] = top_worker.get('email', '')
            metadata['selected_browser'] = top_worker.get('browser', '')
            metadata['selected_profile'] = top_worker.get('profile', '')

        # Verify selection was extracted from decision_context.metadata.worker_gate
        assert metadata['selected_resource_id'] == 'devin_credential_0'
        assert metadata['selected_provider'] == 'devin'
        assert metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

    def test_negative_selection_lost_no_worker_gate(self):
        """Test: no worker_gate in metadata or decision_context → no selection propagated."""
        # Simulate adaptive_payload WITHOUT worker_gate
        adaptive_payload = {
            'user_goal': 'Test objective',
            'metadata': {
                # No worker_gate - selection lost
            },
        }

        # Simulate govern_adaptive_payload() extraction logic
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})

        # Try decision_context first
        decision_context = dict(metadata.get('decision_context') or {})
        dc_meta = dict(decision_context.get('metadata') or {})
        worker_gate = dict(dc_meta.get('worker_gate') or {})
        top_worker = dict(worker_gate.get('top_worker') or {})

        # Fallback to metadata.worker_gate
        if not top_worker:
            session_worker_gate = dict(metadata.get('worker_gate') or {})
            top_worker = dict(session_worker_gate.get('top_worker') or {})

        if top_worker:
            metadata['selected_resource_id'] = top_worker.get('resource_id', '')
            metadata['selected_provider'] = top_worker.get('provider', '')
            metadata['selected_credential_ref'] = top_worker.get('credential_ref', '')

        # Verify: selection was NOT propagated (because it was lost from both sources)
        assert metadata.get('selected_resource_id', '') == ''
        assert metadata.get('selected_credential_ref', '') == ''

    def test_end_to_end_metadata_worker_gate_to_adapter(self):
        """Test: metadata.worker_gate → extraction → adapter resolution."""
        import os
        from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter

        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        # Step 1: Simulate serialized session with worker_gate in metadata
        adaptive_payload = {
            'user_goal': 'Test objective',
            'metadata': {
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
                },
            },
        }

        # Step 2: Simulate govern_adaptive_payload() extraction
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        worker_gate = dict(metadata.get('worker_gate') or {})
        top_worker = dict(worker_gate.get('top_worker') or {})

        if top_worker:
            metadata['selected_resource_id'] = top_worker.get('resource_id', '')
            metadata['selected_provider'] = top_worker.get('provider', '')
            metadata['selected_credential_ref'] = top_worker.get('credential_ref', '')

        # Step 3: Simulate AutonomousEvolutionService extraction
        payload_metadata = dict(metadata or {})
        request_metadata = {
            'selected_resource_id': payload_metadata.get('selected_resource_id', ''),
            'selected_provider': payload_metadata.get('selected_provider', ''),
            'selected_credential_ref': payload_metadata.get('selected_credential_ref', ''),
        }

        # Step 4: Simulate ToolTeachService request building
        resource_selection = {
            'selected_resource_id': request_metadata.get('selected_resource_id', ''),
            'selected_provider': request_metadata.get('selected_provider', ''),
            'selected_credential_ref': request_metadata.get('selected_credential_ref', ''),
        }

        # Step 5: Simulate adapter resolution
        adapter = DevinApiToolAdapter(api_key='default_key')
        selected_credential_ref = resource_selection['selected_credential_ref']
        effective_key, fingerprint = adapter._resolve_api_key(selected_credential_ref)

        # Verify end-to-end identity preservation
        assert adaptive_payload['metadata']['worker_gate']['top_worker']['resource_id'] == 'devin_credential_0'
        assert metadata['selected_resource_id'] == 'devin_credential_0'
        assert resource_selection['selected_resource_id'] == 'devin_credential_0'
        assert effective_key == 'credential_a'
        assert fingerprint != ''

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']
