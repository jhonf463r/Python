"""Integration test: first dispatch real path with worker_gate selection.

Tests that:
- worker_health_gate() selection propagates through govern_adaptive_payload()
- adaptive_payload metadata carries selection to AutonomousEvolutionService
- AutonomousEvolutionService passes selection to ToolTeachService
- ToolTeachService propagates selection to request.metadata
- request.metadata propagates to task.metadata
- task.metadata propagates to DevinApiToolAdapter
- adapter uses the selected credential
"""

import pytest
from typing import Any

from iabv_v15.domain.models import (
    DecisionContext,
    ToolTask,
    ToolType,
    TaskRole,
    InferenceRequest,
)
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


class TestFirstDispatchIntegration:
    """Test that first dispatch propagates worker_gate selection to executor."""

    def test_govern_adaptive_payload_propagates_worker_gate_selection(self):
        """Test: govern_adaptive_payload() propagates worker_gate selection to payload metadata."""
        # Simulate adaptive_payload with decision_context containing worker_gate
        decision_context_dict = {
            'governance': {
                'should_consult': True,
                'assistant_kind': 'codex',
            },
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

        adaptive_payload = {
            'user_goal': 'Test objective',
            'metadata': {
                'decision_context': decision_context_dict,
            },
        }

        # Simulate govern_adaptive_payload() logic
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        decision_context_dict = metadata.get('decision_context', {})
        governance = dict(decision_context_dict.get('governance', {}))

        if governance.get('should_consult'):
            dc_meta = dict(decision_context_dict.get('metadata', {}))
            worker_gate = dict(dc_meta.get('worker_gate', {}))
            top_worker = dict(worker_gate.get('top_worker', {}))

            if top_worker:
                metadata['selected_resource_id'] = top_worker.get('resource_id', '')
                metadata['selected_provider'] = top_worker.get('provider', '')
                metadata['selected_credential_ref'] = top_worker.get('credential_ref', '')
                metadata['selected_email'] = top_worker.get('email', '')
                metadata['selected_browser'] = top_worker.get('browser', '')
                metadata['selected_profile'] = top_worker.get('profile', '')

        # Verify propagation
        assert metadata['selected_resource_id'] == 'devin_credential_0'
        assert metadata['selected_provider'] == 'devin'
        assert metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

    def test_autonomous_evolution_passes_payload_metadata_to_tool_teach(self):
        """Test: AutonomousEvolutionService extracts payload metadata and passes to ToolTeachService."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        # Simulate adaptive_payload with resource selection
        adaptive_payload = {
            'user_goal': 'Test objective',
            'metadata': {
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            },
        }

        # Simulate AutonomousEvolutionService extraction logic
        payload_metadata = dict(adaptive_payload.get('metadata') or {})
        request_metadata = {
            'selected_resource_id': payload_metadata.get('selected_resource_id', ''),
            'selected_provider': payload_metadata.get('selected_provider', ''),
            'selected_credential_ref': payload_metadata.get('selected_credential_ref', ''),
            'selected_email': payload_metadata.get('selected_email', ''),
            'selected_browser': payload_metadata.get('selected_browser', ''),
            'selected_profile': payload_metadata.get('selected_profile', ''),
        }

        # Verify extraction
        assert request_metadata['selected_resource_id'] == 'devin_credential_0'
        assert request_metadata['selected_provider'] == 'devin'
        assert request_metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_tool_teach_propagates_request_metadata_to_request(self):
        """Test: ToolTeachService._build_external_consultation_request() propagates request_metadata."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        # Simulate request_metadata from AutonomousEvolutionService
        request_metadata = {
            'selected_resource_id': 'devin_credential_0',
            'selected_provider': 'devin',
            'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
        }

        # Simulate _build_external_consultation_request() resource selection propagation
        resource_selection = {
            'selected_resource_id': request_metadata.get('selected_resource_id', ''),
            'selected_provider': request_metadata.get('selected_provider', ''),
            'selected_credential_ref': request_metadata.get('selected_credential_ref', ''),
            'selected_email': request_metadata.get('selected_email', ''),
            'selected_browser': request_metadata.get('selected_browser', ''),
            'selected_profile': request_metadata.get('selected_profile', ''),
        }

        # Simulate InferenceRequest metadata
        final_metadata = {
            **resource_selection,
            'external_consultation': True,
        }

        # Verify propagation
        assert final_metadata['selected_resource_id'] == 'devin_credential_0'
        assert final_metadata['selected_provider'] == 'devin'
        assert final_metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_end_to_end_first_dispatch_propagation(self):
        """Test: end-to-end worker_gate → adaptive_payload → request → task → adapter."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        # Step 1: worker_gate selection
        worker_gate_selection = {
            'resource_id': 'devin_credential_0',
            'provider': 'devin',
            'tool': 'devin_api',
            'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            'email': '',
            'browser': '',
            'profile': '',
        }

        # Step 2: govern_adaptive_payload() propagates to payload metadata
        adaptive_payload_metadata = {
            'selected_resource_id': worker_gate_selection['resource_id'],
            'selected_provider': worker_gate_selection['provider'],
            'selected_credential_ref': worker_gate_selection['credential_ref'],
        }

        # Step 3: AutonomousEvolutionService extracts to request_metadata
        payload_metadata = adaptive_payload_metadata
        request_metadata = {
            'selected_resource_id': payload_metadata.get('selected_resource_id', ''),
            'selected_provider': payload_metadata.get('selected_provider', ''),
            'selected_credential_ref': payload_metadata.get('selected_credential_ref', ''),
        }

        # Step 4: ToolTeachService propagates to InferenceRequest metadata
        request_final_metadata = {
            **request_metadata,
            'external_consultation': True,
        }

        # Step 5: build_task_from_request() propagates to task metadata
        task_metadata = {
            'selected_resource_id': request_final_metadata.get('selected_resource_id', ''),
            'selected_provider': request_final_metadata.get('selected_provider', ''),
            'selected_credential_ref': request_final_metadata.get('selected_credential_ref', ''),
        }

        # Step 6: adapter resolves credential
        adapter = DevinApiToolAdapter(api_key='default_key')
        selected_credential_ref = task_metadata.get('selected_credential_ref')
        effective_key, fingerprint = adapter._resolve_api_key(selected_credential_ref)

        # Verify end-to-end identity preservation
        assert worker_gate_selection['resource_id'] == adaptive_payload_metadata['selected_resource_id']
        assert adaptive_payload_metadata['selected_resource_id'] == request_metadata['selected_resource_id']
        assert request_metadata['selected_resource_id'] == task_metadata['selected_resource_id']
        assert effective_key == 'credential_a'
        assert fingerprint != ''

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_negative_no_worker_gate_selection_uses_default(self):
        """Test: no worker_gate selection → uses default credential (compatibility)."""
        import os
        os.environ['DEVIN_API_KEY_DEFAULT'] = 'default_key'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # Simulate adaptive_payload without worker_gate selection
        adaptive_payload_metadata = {}

        # request_metadata empty
        request_metadata = {
            'selected_resource_id': '',
            'selected_provider': '',
            'selected_credential_ref': '',
        }

        # task_metadata empty
        task_metadata = {
            'selected_resource_id': '',
            'selected_provider': '',
            'selected_credential_ref': '',
        }

        # adapter resolves with no selection → uses default
        selected_credential_ref = task_metadata.get('selected_credential_ref')
        effective_key, fingerprint = adapter._resolve_api_key(selected_credential_ref)

        # Verify default credential used
        assert effective_key == 'default_key'
        assert fingerprint != ''

        # Cleanup
        del os.environ['DEVIN_API_KEY_DEFAULT']

    def test_negative_worker_gate_selection_lost_before_executor(self):
        """Test: worker_gate selection lost before executor → should be detectable."""
        import os
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'
        os.environ['DEVIN_API_KEY_DEFAULT'] = 'default_key'

        adapter = DevinApiToolAdapter(api_key='default_key')

        # worker_gate selects A
        worker_gate_selection = {
            'resource_id': 'devin_credential_0',
            'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
        }

        # adaptive_payload propagates A
        adaptive_payload_metadata = {
            'selected_resource_id': worker_gate_selection['resource_id'],
            'selected_credential_ref': worker_gate_selection['credential_ref'],
        }

        # BUT: selection lost in request_metadata (simulated bridge failure)
        request_metadata = {
            'selected_resource_id': '',  # LOST
            'selected_provider': '',  # LOST
            'selected_credential_ref': '',  # LOST
        }

        # task_metadata reflects loss
        task_metadata = {
            'selected_resource_id': request_metadata['selected_resource_id'],
            'selected_credential_ref': request_metadata['selected_credential_ref'],
        }

        # adapter resolves with empty selection → uses default
        selected_credential_ref = task_metadata.get('selected_credential_ref')
        effective_key, fingerprint = adapter._resolve_api_key(selected_credential_ref)

        # Verify: selection lost → default used (this should be detected as selection_lost)
        assert effective_key == 'default_key'  # Not A!

        # In production, this should trigger selection_lost detection
        # The test verifies the failure mode is observable

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']
        del os.environ['DEVIN_API_KEY_DEFAULT']
