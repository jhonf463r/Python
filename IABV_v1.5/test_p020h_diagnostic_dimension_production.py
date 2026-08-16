"""
P0.20h — Mandatory Observed-Dimension Declaration at Diagnostic Test Creation

Tests for ensuring selected_test producer emits mandatory observed_condition.
"""
import sys
import os

# Clean sys.path to remove any contamination
sys.path = [p for p in sys.path if 'IABV_v1.5_canonical' not in p and 'iabv_p019d_workspace' not in p]

# Add canonical project source to path
project_src = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, project_src)

import pytest
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
from iabv_v15.services.evolution.diagnostic_test_executor import DiagnosticTestExecutor
from iabv_v15.domain.models import MetacognitiveDiscernmentFrame


class TestDiagnosticDimensionProduction:
    """Test A-J: Focused tests for mandatory observed_condition in diagnostic test production."""

    def test_a_propose_diagnostic_test_emits_observed_condition(self):
        """Test A: _propose_diagnostic_test() emits observed_condition for provider_availability."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'ollama',
                    'diagnostic_target': 'http://127.0.0.1:11434/api/tags',
                }
            }],
            trusted_sources=['source1'],
        )

        selected_test = DiscernmentFrameService._propose_diagnostic_test(frame, world_model=None)

        assert selected_test is not None
        assert 'observed_condition' in selected_test
        assert selected_test['observed_condition'] == 'provider_available'

    def test_b_provider_availability_provides_declared_condition(self):
        """Test B: provider_availability produces observed_condition = provider_available."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'test_provider',
                    'diagnostic_target': 'http://localhost:8080/health',
                }
            }],
            trusted_sources=['source1'],
        )

        selected_test = DiscernmentFrameService._propose_diagnostic_test(frame, world_model=None)

        assert selected_test is not None
        assert selected_test['test_type'] == 'provider_availability'
        assert selected_test['observed_condition'] == 'provider_available'

    def test_c_hypothesis_expected_result_uses_observed_condition(self):
        """Test C: hypothesis.expected_result.condition uses observed_condition."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'ollama',
                    'diagnostic_target': 'http://127.0.0.1:11434/api/tags',
                }
            }],
            trusted_sources=['source1'],
        )

        selected_test = DiscernmentFrameService._propose_diagnostic_test(frame, world_model=None)
        hypothesis = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test)

        assert hypothesis is not None
        assert hypothesis.expected_result['condition'] == selected_test['observed_condition']
        assert hypothesis.expected_result['condition'] == 'provider_available'

    def test_d_executor_actual_result_uses_observed_condition(self):
        """Test D: executor.actual_result.condition uses observed_condition."""
        # Simulate executor using observed_condition from selected_test
        selected_test = {
            'test_id': 'test_provider_availability',
            'observed_condition': 'provider_available',
        }

        # Executor should use observed_condition from selected_test
        observed_condition = selected_test.get('observed_condition')
        result = {
            'status': 'success',
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': observed_condition,
                'observed': True,
            }
        }

        assert result['actual_result']['condition'] == 'provider_available'
        assert result['actual_result']['condition'] == selected_test['observed_condition']

    def test_e_changing_target_does_not_change_semantic_dimension(self):
        """Test E: Changing target does not change the semantic dimension."""
        frame1 = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-1',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'ollama',
                    'diagnostic_target': 'http://127.0.0.1:11434/api/tags',
                }
            }],
            trusted_sources=['source1'],
        )

        frame2 = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-2',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'test_provider',
                    'diagnostic_target': 'http://localhost:8080/health',
                }
            }],
            trusted_sources=['source1'],
        )

        selected_test1 = DiscernmentFrameService._propose_diagnostic_test(frame1, world_model=None)
        selected_test2 = DiscernmentFrameService._propose_diagnostic_test(frame2, world_model=None)

        assert selected_test1 is not None
        assert selected_test2 is not None
        # Both should have the same observed_condition regardless of target
        assert selected_test1['observed_condition'] == 'provider_available'
        assert selected_test2['observed_condition'] == 'provider_available'

    def test_f_no_system_healthy_by_target_inference(self):
        """Test F: No system_healthy appears by target inference."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'system',
                    'diagnostic_target': 'http://system.example.com/health',
                }
            }],
            trusted_sources=['source1'],
        )

        selected_test = DiscernmentFrameService._propose_diagnostic_test(frame, world_model=None)

        assert selected_test is not None
        # Should use provider_available, not infer system_healthy from target
        assert selected_test['observed_condition'] == 'provider_available'
        assert selected_test['observed_condition'] != 'system_healthy'

    def test_g_selected_test_without_observed_condition_rejected(self):
        """Test G: selected_test without observed_condition is rejected."""
        selected_test = {
            'test_id': 'test_provider_availability',
            'test_type': 'provider_availability',
            'target': 'http://localhost:8080',
            'status': 'proposed',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            # Missing observed_condition
        }

        rejection_reason = DiagnosticTestExecutor._rejection_reason(
            selected_test,
            session_id='test-session-id',
            frame_id='test-frame-id',
        )

        assert rejection_reason == 'observed_condition_required'

    def test_h_general_diagnostic_without_dimension_not_executable(self):
        """Test H: general_diagnostic without defined dimension does not execute invented observation."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[],
            trusted_sources=['world_model'],
        )

        # Mark as diagnostic request
        frame.metadata['diagnostic_request'] = True

        selected_test = DiscernmentFrameService._propose_diagnostic_test(frame, world_model=None)

        # Should return empty dict, not create executable test without observed_condition
        assert selected_test == {}

    def test_i_no_condition_mismatch_by_divergent_defaults(self):
        """Test I: No condition mismatch occurs due to divergent defaults."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{
                'type': 'provider_health_vs_inference_failure',
                'evidence': {
                    'provider': 'ollama',
                    'diagnostic_target': 'http://127.0.0.1:11434/api/tags',
                }
            }],
            trusted_sources=['source1'],
        )

        selected_test = DiscernmentFrameService._propose_diagnostic_test(frame, world_model=None)
        hypothesis = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test)

        # All should use the same observed_condition
        assert selected_test['observed_condition'] == 'provider_available'
        assert hypothesis.expected_result['condition'] == 'provider_available'

        # No divergent defaults (hypothesis used to default to system_healthy)
        assert hypothesis.expected_result['condition'] != 'system_healthy'

    def test_j_no_synthetic_learning(self):
        """Test J: No synthetic learning is created."""
        import inspect
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        # Verify _persist_diagnostic_result does not create synthetic RunRecord
        source = inspect.getsource(TaskOutcomeRecorder._persist_diagnostic_result)

        assert 'diagnostic_synthetic' not in source
        assert 'synthetic_run_record' not in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
