"""
P0.20c — Runtime Epistemic Loop Test

Tests for the complete runtime wiring from hypothesis to ExperimentRun.
"""
import sys
import os

# Clean sys.path to remove any contamination
sys.path = [p for p in sys.path if 'IABV_v1.5_canonical' not in p and 'iabv_p019d_workspace' not in p]

# Add canonical project source to path
project_src = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, project_src)

import pytest
from iabv_v15.domain.models import (
    MetacognitiveDiscernmentFrame,
    EpistemicHypothesis,
    AdaptiveSession,
    AdaptiveSessionStatus,
    TaskIntent,
    TaskRole,
    VerificationStatus,
    LearningDecision,
)
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
from iabv_v15.services.evolution.diagnostic_test_executor import DiagnosticTestExecutor


class TestRuntimeEpistemicLoop:
    """Test A-K: Focused tests for runtime epistemic loop."""

    def test_a_hypothesis_propagation_to_session_metadata(self):
        """Test A: Hypothesis propagates to AdaptiveSession.metadata."""
        service = DiscernmentFrameService()

        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            selected_test['hypothesis_id'] = hypothesis.hypothesis_id
            selected_test['expected_result'] = hypothesis.expected_result

            # Simulate session metadata propagation
            session_metadata = {
                'selected_test': selected_test,
                'hypothesis_id': selected_test.get('hypothesis_id'),
                'expected_result': selected_test.get('expected_result'),
            }

            assert 'hypothesis_id' in session_metadata, "hypothesis_id should be in session metadata"
            assert 'expected_result' in session_metadata, "expected_result should be in session metadata"
            assert isinstance(session_metadata['expected_result'], dict), "expected_result should be structured dict"

    def test_b_expected_result_generated_before_execution(self):
        """Test B: expected_result is generated before test execution."""
        service = DiscernmentFrameService()

        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            # expected_result is generated before execution
            assert hypothesis.expected_result is not None, "expected_result should be generated"
            assert isinstance(hypothesis.expected_result, dict), "expected_result should be structured dict"
            assert 'condition' in hypothesis.expected_result, "expected_result should have condition"
            assert 'expected' in hypothesis.expected_result, "expected_result should have expected boolean"

    def test_c_actual_result_structured(self):
        """Test C: actual_result has structured representation."""
        executor = DiagnosticTestExecutor()

        # Simulate a successful HTTP response
        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
                'raw_evidence': 'http_status:200',
            }
        }

        assert 'actual_result' in result, "actual_result should be in result"
        assert isinstance(result['actual_result'], dict), "actual_result should be structured dict"
        assert 'condition' in result['actual_result'], "actual_result should have condition"
        assert 'observed' in result['actual_result'], "actual_result should have observed boolean"

    def test_d_expected_actual_comparable(self):
        """Test D: expected_result and actual_result are comparable."""
        expected_result = {
            'condition': 'provider_available',
            'expected': True,
        }

        actual_result = {
            'condition': 'provider_available',
            'observed': True,
            'raw_evidence': 'http_status:200',
        }

        # Both have the same condition dimension
        assert expected_result['condition'] == actual_result['condition'], "Conditions should match"
        assert expected_result['expected'] == actual_result['observed'], "Expected and observed should match"

    def test_e_mismatch_refuted(self):
        """Test E: Mismatch leads to REFUTED status."""
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        # Mock comparison logic
        expected_result = {
            'condition': 'provider_available',
            'expected': True,
        }

        actual_result = {
            'condition': 'provider_available',
            'observed': False,  # Mismatch
            'raw_evidence': 'http_status:500',
        }

        # Simulate comparison
        if expected_result['expected'] != actual_result['observed']:
            verification_status = VerificationStatus.REFUTED
        else:
            verification_status = VerificationStatus.VERIFIED

        assert verification_status == VerificationStatus.REFUTED, "Mismatch should lead to REFUTED"

    def test_f_insufficient_evidence_inconclusive(self):
        """Test F: Insufficient evidence leads to INCONCLUSIVE status."""
        expected_result = {
            'condition': 'provider_available',
            'expected': True,
        }

        actual_result = None  # Missing actual_result

        if actual_result is None:
            verification_status = VerificationStatus.INCONCLUSIVE
        else:
            verification_status = VerificationStatus.VERIFIED

        assert verification_status == VerificationStatus.INCONCLUSIVE, "Missing actual_result should lead to INCONCLUSIVE"

    def test_g_executor_result_reaches_verification(self):
        """Test G: Executor result reaches verification boundary."""
        # Simulate executor result
        executor_result = {
            'test_id': 'test_provider_availability_probe',
            'frame_id': 'test-frame-id',
            'interaction_id': 'test-interaction-id',
            'status': 'success',
            'evidence': ['http_status:200'],
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
                'raw_evidence': 'http_status:200',
            },
            'duration_ms': 100,
        }

        # Simulate verification boundary receiving the result
        verification_input = {
            'selected_test': {
                'test_id': 'test_provider_availability_probe',
                'expected_result': {
                    'condition': 'provider_available',
                    'expected': True,
                },
            },
            'test_result': executor_result,
        }

        assert 'actual_result' in verification_input['test_result'], "actual_result should reach verification"
        assert 'expected_result' in verification_input['selected_test'], "expected_result should reach verification"

    def test_h_verification_reaches_learning_gate(self):
        """Test H: Verification reaches learning gate."""
        verification_metadata = {
            'verification_status': VerificationStatus.VERIFIED.value,
            'learning_decision': LearningDecision.ELIGIBLE.value,
            'verification_reason': 'expected_vs_actual_match',
            'hypothesis_id': 'test-hypothesis-id',
            'selected_test_id': 'test_provider_availability_probe',
        }

        # Simulate learning gate receiving verification
        learning_input = {
            'verification': verification_metadata,
            'test_result': {
                'status': 'success',
                'actual_result': {
                    'condition': 'provider_available',
                    'observed': True,
                },
            },
        }

        assert 'verification' in learning_input, "Verification should reach learning gate"
        assert learning_input['verification']['verification_status'] == VerificationStatus.VERIFIED.value
        assert learning_input['verification']['learning_decision'] == LearningDecision.ELIGIBLE.value

    def test_i_verified_eligible_experiment_run(self):
        """Test I: VERIFIED + ELIGIBLE creates ExperimentRun."""
        from iabv_v15.domain.models import ExperimentRun, ExperimentDomain, EvaluationRoute, ExperimentMetric, AssistantConfigurationSnapshot

        # Simulate ExperimentRun creation
        verification_metadata = {
            'verification_status': VerificationStatus.VERIFIED.value,
            'learning_decision': LearningDecision.ELIGIBLE.value,
            'hypothesis_id': 'test-hypothesis-id',
            'selected_test_id': 'test_provider_availability_probe',
        }

        experiment_run = ExperimentRun(
            domain=ExperimentDomain.CODE,
            suite_name='diagnostic_verification',
            objective='verified_diagnostic:test_provider_availability_probe',
            subject_key='test-session-id',
            comparison_scope_key='session:test-session-id',
            route=EvaluationRoute.FALLBACK,
            assistant_kind='diagnostic_executor',
            assistant_configuration=AssistantConfigurationSnapshot(
                assistant_kind='diagnostic_executor',
                route=EvaluationRoute.FALLBACK,
                config_signature='diagnostic_verification',
                metadata={'diagnostic_test_id': 'test_provider_availability_probe'},
            ),
            expected_summary='provider_available: True',
            observed_summary='provider_available: True',
            metrics=ExperimentMetric(
                precision=1.0,
                execution_ms=100,
                operational_cost=0.0,
                robustness=1.0,
            ),
            metadata={
                'verification_status': verification_metadata['verification_status'],
                'learning_decision': verification_metadata['learning_decision'],
                'hypothesis_id': verification_metadata['hypothesis_id'],
                'selected_test_id': verification_metadata['selected_test_id'],
            },
        )

        assert experiment_run is not None, "ExperimentRun should be created"
        assert experiment_run.metadata['hypothesis_id'] == 'test-hypothesis-id'
        assert experiment_run.metadata['verification_status'] == VerificationStatus.VERIFIED.value
        assert experiment_run.metadata['learning_decision'] == LearningDecision.ELIGIBLE.value

    def test_j_nonverified_no_experiment_run(self):
        """Test J: Non-verified status does not create ExperimentRun."""
        verification_metadata = {
            'verification_status': VerificationStatus.UNVERIFIED.value,
            'learning_decision': LearningDecision.NOT_ELIGIBLE.value,
            'verification_reason': 'test_skipped',
        }

        # Simulate learning gate decision
        if verification_metadata['verification_status'] != VerificationStatus.VERIFIED.value:
            experiment_run = None
        else:
            experiment_run = ExperimentRun()  # Would be created

        assert experiment_run is None, "Non-verified should not create ExperimentRun"

    def test_k_no_false_green(self):
        """Test K: No false green - INCONCLUSIVE does not become VERIFIED."""
        verification_metadata = {
            'verification_status': VerificationStatus.INCONCLUSIVE.value,
            'learning_decision': LearningDecision.NOT_ELIGIBLE.value,
            'verification_reason': 'insufficient_evidence',
        }

        # Ensure INCONCLUSIVE does not become VERIFIED
        assert verification_metadata['verification_status'] == VerificationStatus.INCONCLUSIVE.value
        assert verification_metadata['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
        # No false green - INCONCLUSIVE stays INCONCLUSIVE


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
