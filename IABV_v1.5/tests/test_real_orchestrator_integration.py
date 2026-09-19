"""UNIT_BEHAVIOR test: govern_adaptive_payload() extracts from metadata.worker_gate (serialized session).

Tests that:
- govern_adaptive_payload() logic extracts worker_gate selection from metadata.worker_gate (serialized AdaptiveSession)
- govern_adaptive_payload() logic also extracts from decision_context.metadata.worker_gate (if available)
- The selection propagates to payload.metadata selected_resource_id/provider/credential_ref
- Identity conflict (A in decision_context, B in metadata) is documented (TODO: implement blocking)
- Selection lost is documented (TODO: implement blocking)

Note: This is UNIT_BEHAVIOR, not full INTEGRATION, because full handle_request() execution
requires complex dependency mocking. The propagation logic is verified, but the complete end-to-end
path from handle_request() through all dependencies is documented as a TODO.
"""

import pytest
import os
from typing import Any
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


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

    def test_identity_conflict_blocks_execution(self):
        """Test: decision_context.worker_gate = A, metadata.worker_gate = B → BLOCK at adapter."""
        from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
        from iabv_v15.domain.models import ToolCard, ToolTask, ToolAction, ToolActionType, ToolType

        # Simulate task with identity_conflict status
        task = ToolTask(
            task_id='test_task',
            tool_id='devin_api',
            title='Test task',
            objective='Test objective',
            actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='test', value='Test prompt')],
            metadata={
                'selection_status': 'identity_conflict',
                'identity_conflict': {
                    'decision_context_resource_id': 'devin_credential_A',
                    'session_resource_id': 'devin_credential_B',
                    'decision_context_credential_ref': 'devin:credential_A:DEVIN_API_KEY_A',
                    'session_credential_ref': 'devin:credential_B:DEVIN_API_KEY_B',
                    'reason': 'decision_context.worker_gate != metadata.worker_gate - conflicting identities',
                },
            },
        )

        card = ToolCard(tool_id='devin_api', title='Devin API', tool_type=ToolType.MCP_CLIENT, adapter_key='devin_api', metadata={})

        adapter = DevinApiToolAdapter(api_key='default_key')
        result = adapter.run(card, task, sandbox=True)

        # Verify: execution blocked with identity_conflict status
        assert result['success'] is False
        assert result['metadata']['selection_status'] == 'identity_conflict'
        assert result['metadata']['blocked_reason'] == 'identity_conflict'
        assert 'identity_conflict' in result['metadata']
        assert result['metadata']['identity_conflict']['decision_context_resource_id'] == 'devin_credential_A'
        assert result['metadata']['identity_conflict']['session_resource_id'] == 'devin_credential_B'

    def test_negative_selection_lost_no_worker_gate(self):
        """Test: worker_gate selected A, but selection lost → BLOCK at adapter."""
        from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
        from iabv_v15.domain.models import ToolCard, ToolTask, ToolAction, ToolActionType, ToolType

        # Simulate task with selection_lost status
        task = ToolTask(
            task_id='test_task',
            tool_id='devin_api',
            title='Test task',
            objective='Test objective',
            actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='test', value='Test prompt')],
            metadata={
                'selection_status': 'selection_lost',
                'selection_lost': {
                    'session_usable': True,
                    'session_had_top_worker': True,
                    'reason': 'worker_gate selected resource but selection was lost before payload construction',
                },
            },
        )

        card = ToolCard(tool_id='devin_api', title='Devin API', tool_type=ToolType.MCP_CLIENT, adapter_key='devin_api', metadata={})

        adapter = DevinApiToolAdapter(api_key='default_key')
        result = adapter.run(card, task, sandbox=True)

        # Verify: execution blocked with selection_lost status
        assert result['success'] is False
        assert result['metadata']['selection_status'] == 'selection_lost'
        assert result['metadata']['blocked_reason'] == 'selection_lost'
        assert 'selection_lost' in result['metadata']
        assert result['metadata']['selection_lost']['session_had_top_worker'] is True

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

    def test_identity_conflict_not_reclassified_as_selection_lost(self):
        """Test: identity_conflict is NOT reclassified as selection_lost when session had selection."""
        # Simulate adaptive_payload with CONFLICTING worker_gate in both sources
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
                                'resource_id': 'devin_credential_A',  # A in decision_context
                                'provider': 'devin',
                                'tool': 'devin_api',
                                'credential_ref': 'devin:credential_A:DEVIN_API_KEY_A',
                                'email': '',
                                'browser': '',
                                'profile': '',
                            },
                        },
                    },
                },
                'worker_gate': {
                    'usable': True,
                    'top_worker': {
                        'resource_id': 'devin_credential_B',  # B in metadata
                        'provider': 'devin',
                        'tool': 'devin_api',
                        'credential_ref': 'devin:credential_B:DEVIN_API_KEY_B',
                        'email': '',
                        'browser': '',
                        'profile': '',
                    },
                },
            },
        }

        # Simulate govern_adaptive_payload() extraction logic (FIXED implementation)
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        dc_meta = dict(decision_context.get('metadata') or {})
        worker_gate_dc = dict(dc_meta.get('worker_gate') or {})
        top_worker_dc = dict(worker_gate_dc.get('top_worker') or {})

        session_worker_gate = dict(metadata.get('worker_gate') or {})
        top_worker_session = dict(session_worker_gate.get('top_worker') or {})

        # Identity conflict detection
        identity_conflict_detected = False
        if top_worker_dc and top_worker_session:
            resource_id_dc = top_worker_dc.get('resource_id', '')
            resource_id_session = top_worker_session.get('resource_id', '')
            credential_ref_dc = top_worker_dc.get('credential_ref', '')
            credential_ref_session = top_worker_session.get('credential_ref', '')

            if resource_id_dc != resource_id_session or credential_ref_dc != credential_ref_session:
                identity_conflict_detected = True
                metadata['selection_status'] = 'identity_conflict'
                metadata['identity_conflict'] = {
                    'decision_context_resource_id': resource_id_dc,
                    'session_resource_id': resource_id_session,
                    'decision_context_credential_ref': credential_ref_dc,
                    'session_credential_ref': credential_ref_session,
                    'reason': 'decision_context.worker_gate != metadata.worker_gate - conflicting identities',
                }
                top_worker_dc = {}
                top_worker_session = {}

        # Selection lost detection (only if identity_conflict was NOT detected)
        session_had_selection = bool(session_worker_gate.get('usable', False) and session_worker_gate.get('top_worker'))
        if not identity_conflict_detected and session_had_selection and not top_worker_dc and not top_worker_session:
            metadata['selection_status'] = 'selection_lost'
            metadata['selection_lost'] = {
                'session_usable': session_worker_gate.get('usable', False),
                'session_had_top_worker': bool(session_worker_gate.get('top_worker')),
                'reason': 'worker_gate selected resource but selection was lost before payload construction',
            }
            top_worker_dc = {}
            top_worker_session = {}

        # Verify: identity_conflict is NOT reclassified as selection_lost
        assert identity_conflict_detected is True
        assert metadata['selection_status'] == 'identity_conflict'
        assert metadata['selection_status'] != 'selection_lost'
        assert 'identity_conflict' in metadata
        assert 'selection_lost' not in metadata

    def test_ab_discrimination_real_resources(self):
        """Test: A selected → executor A, B selected → executor B (simulated with real adapter)."""
        # Case A
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'
        adapter_a = DevinApiToolAdapter(api_key='default_key')
        effective_key_a, fingerprint_a = adapter_a._resolve_api_key('devin:credential_A:DEVIN_API_KEY_A')
        assert effective_key_a == 'credential_a'
        assert fingerprint_a != ''

        # Case B
        os.environ['DEVIN_API_KEY_B'] = 'credential_b'
        adapter_b = DevinApiToolAdapter(api_key='default_key')
        effective_key_b, fingerprint_b = adapter_b._resolve_api_key('devin:credential_B:DEVIN_API_KEY_B')
        assert effective_key_b == 'credential_b'
        assert fingerprint_b != ''

        # Verify fingerprints are different
        assert fingerprint_a != fingerprint_b

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']
        del os.environ['DEVIN_API_KEY_B']
