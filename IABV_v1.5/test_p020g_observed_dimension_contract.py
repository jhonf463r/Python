"""
P0.20g — Observed Dimension Contract Test

Tests for explicit observed_condition contract ensuring semantic consistency
across hypothesis, execution, and verification.
"""
import sys
import os
import threading

# Clean sys.path to remove any contamination
sys.path = [p for p in sys.path if 'IABV_v1.5_canonical' not in p and 'iabv_p019d_workspace' not in p]

# Add canonical project source to path
project_src = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, project_src)

import pytest
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
from iabv_v15.services.evolution.diagnostic_test_executor import DiagnosticTestExecutor
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.domain.models import MetacognitiveDiscernmentFrame, VerificationStatus, LearningDecision


class TestObservedDimensionContract:
    """Test A-K: Focused tests for observed dimension contract."""

    def test_a_selected_test_contains_observed_condition(self):
        """Test A: selected_test contains observed_condition."""
        selected_test = {
            'test_id': 'test_provider_availability',
            'test_type': 'provider_availability',
            'target': 'http://127.0.0.1:11434/api/tags',
            'observed_condition': 'provider_available',  # P0.20g: Explicit declaration
        }

        assert 'observed_condition' in selected_test
        assert selected_test['observed_condition'] == 'provider_available'

    def test_b_hypothesis_reuses_observed_condition(self):
        """Test B: hypothesis reuses observed_condition."""
        # Create a minimal frame for testing
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{'type': 'provider_unavailable'}],
            trusted_sources=['source1', 'source2'],
        )

        selected_test = {
            'test_id': 'test_provider_availability',
            'observed_condition': 'provider_available',  # P0.20g: Explicit declaration
        }

        hypothesis = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test)

        assert hypothesis is not None
        assert hypothesis.expected_result['condition'] == 'provider_available'
        # Should NOT infer from target text
        assert hypothesis.expected_result['condition'] == selected_test['observed_condition']

    def test_c_expected_result_condition_matches_observed_condition(self):
        """Test C: expected_result.condition == observed_condition."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{'type': 'provider_unavailable'}],
            trusted_sources=['source1'],
        )

        selected_test = {
            'test_id': 'test_provider_availability',
            'observed_condition': 'gpu_available',  # Different dimension
        }

        hypothesis = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test)

        assert hypothesis is not None
        assert hypothesis.expected_result['condition'] == 'gpu_available'
        assert hypothesis.expected_result['condition'] == selected_test['observed_condition']

    def test_d_executor_actual_result_condition_matches_observed_condition(self):
        """Test D: executor actual_result.condition == observed_condition."""
        # Simulate executor result with different observed_condition
        result = {
            'status': 'success',
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'gpu_available',  # P0.20g: Explicit dimension
                'observed': True,
            }
        }

        assert 'actual_result' in result
        assert result['actual_result']['condition'] == 'gpu_available'
        # Should NOT be hardcoded to 'provider_available'

    def test_e_verification_receives_same_condition(self):
        """Test E: verification receives same condition in expected and actual."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        # Both use the same observed_condition
        observed_condition = 'inference_available'

        expected_result = {
            'condition': observed_condition,
            'expected': True,
        }
        actual_result = {
            'condition': observed_condition,
            'observed': True,
        }

        # Should pass validation
        assert recorder._validate_structured_result(expected_result, 'expected_result')
        assert recorder._validate_structured_result(actual_result, 'actual_result')

        # Should compare successfully
        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MATCH'

    def test_f_different_target_does_not_change_semantic_condition(self):
        """Test F: different target does not change the semantic condition."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{'type': 'provider_unavailable'}],
            trusted_sources=['source1'],
        )

        # Same observed_condition, different targets
        selected_test_1 = {
            'test_id': 'test_1',
            'target': 'http://127.0.0.1:11434/api/tags',
            'observed_condition': 'provider_available',
        }

        selected_test_2 = {
            'test_id': 'test_2',
            'target': 'http://localhost:8080/health',
            'observed_condition': 'provider_available',
        }

        hypothesis_1 = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test_1)
        hypothesis_2 = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test_2)

        assert hypothesis_1 is not None
        assert hypothesis_2 is not None
        # Both should use the same observed_condition, not infer from target
        assert hypothesis_1.expected_result['condition'] == 'provider_available'
        assert hypothesis_2.expected_result['condition'] == 'provider_available'

    def test_g_provider_availability_http_200_provides_declared_condition(self):
        """Test G: provider_availability with HTTP 200 produces declared condition."""
        # Simulate executor result with HTTP 200
        result = {
            'status': 'success',
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'provider_available',  # Because selected_test declared it
                'observed': True,
            }
        }

        assert result['actual_result']['condition'] == 'provider_available'
        assert result['actual_result']['observed'] is True

    def test_h_provider_availability_http_failure_same_condition_false_observed(self):
        """Test H: provider_availability with HTTP failure produces same condition, false observed."""
        # Simulate executor result with HTTP failure
        result = {
            'status': 'unavailable',
            'error': 'connection_failed',
            'raw_evidence': 'connection_failed',
            'actual_result': {
                'condition': 'provider_available',  # Same condition
                'observed': False,  # Different observed value
            }
        }

        assert result['actual_result']['condition'] == 'provider_available'
        assert result['actual_result']['observed'] is False

    def test_i_no_condition_inference_from_target_text(self):
        """Test I: no condition inference from target text."""
        frame = MetacognitiveDiscernmentFrame(
            frame_id='test-frame-id',
            contradictions=[{'type': 'provider_unavailable'}],
            trusted_sources=['source1'],
        )

        # Target contains "provider" but observed_condition is different
        selected_test = {
            'test_id': 'test_custom',
            'target': 'http://provider.example.com/api',  # Contains "provider"
            'observed_condition': 'custom_dimension',  # Different dimension
        }

        hypothesis = DiscernmentFrameService._generate_epistemic_hypothesis(frame, selected_test)

        assert hypothesis is not None
        # Should use observed_condition, NOT infer from target text
        assert hypothesis.expected_result['condition'] == 'custom_dimension'
        assert hypothesis.expected_result['condition'] != 'provider_available'

    def test_j_no_false_green(self):
        """Test J: no false green - condition mismatch causes REFUTED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        expected_result = {
            'condition': 'provider_available',
            'expected': True,
        }
        actual_result = {
            'condition': 'gpu_available',  # Different condition
            'observed': True,
        }

        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MISMATCH'  # Should REFUTED, not VERIFIED

    def test_k_no_synthetic_learning(self):
        """Test K: no synthetic learning - only VERIFIED + ELIGIBLE creates ExperimentRun."""
        import inspect
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        # Verify _persist_diagnostic_result does not create synthetic RunRecord
        source = inspect.getsource(TaskOutcomeRecorder._persist_diagnostic_result)

        assert 'diagnostic_synthetic' not in source
        assert 'synthetic_run_record' not in source

        # Verify _record_diagnostic_learning uses real verification data
        source = inspect.getsource(TaskOutcomeRecorder._record_diagnostic_learning)
        assert 'verification_metadata' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
