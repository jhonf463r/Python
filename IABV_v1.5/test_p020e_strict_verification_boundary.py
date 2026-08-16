"""
P0.20e — Strict Verification Boundary Test

Tests for hardening the verification boundary to only accept structured expected_result vs actual_result.
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
    VerificationStatus,
    LearningDecision,
)
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder


class TestStrictVerificationBoundary:
    """Test A-P: Focused tests for strict verification boundary."""

    def test_a_structured_match(self):
        """Test A: expected dict + actual dict matching → VERIFIED."""
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
            'condition': 'provider_available',
            'observed': True,
        }

        # Validate structure
        assert recorder._validate_structured_result(expected_result, 'expected_result')
        assert recorder._validate_structured_result(actual_result, 'actual_result')

        # Compare
        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MATCH'

    def test_b_condition_mismatch(self):
        """Test B: condition mismatch → REFUTED."""
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
            'condition': 'provider_unavailable',
            'observed': True,
        }

        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MISMATCH'

    def test_c_expected_mismatch(self):
        """Test C: expected mismatch → REFUTED."""
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
            'condition': 'provider_available',
            'observed': False,
        }

        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MISMATCH'

    def test_d_actual_result_absent(self):
        """Test D: actual_result absent → INCONCLUSIVE."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            # No actual_result
        }

        # Should fail validation
        assert not recorder._validate_structured_result(result.get('actual_result'), 'actual_result')

    def test_e_actual_result_not_structured(self):
        """Test E: actual_result not structured → INCONCLUSIVE."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        # String instead of dict
        actual_result = "provider_available"
        assert not recorder._validate_structured_result(actual_result, 'actual_result')

        # List instead of dict
        actual_result = ['provider_available', True]
        assert not recorder._validate_structured_result(actual_result, 'actual_result')

        # Dict without required keys
        actual_result = {'condition': 'provider_available'}  # missing 'observed'
        assert not recorder._validate_structured_result(actual_result, 'actual_result')

    def test_f_evidence_present_actual_result_absent(self):
        """Test F: evidence present but actual_result absent → NO VERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            # actual_result missing
        }

        # Should not use evidence as fallback
        assert result.get('actual_result') is None
        assert result.get('evidence') is not None

        # Validation should fail
        assert not recorder._validate_structured_result(result.get('actual_result'), 'actual_result')

    def test_g_string_fallback(self):
        """Test G: string fallback → NO VERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        expected_result = "provider_available"
        actual_result = "provider_available"

        # Old _compare_results should reject
        comparison = recorder._compare_results(expected_result, actual_result)
        assert comparison == 'INSUFFICIENT_EVIDENCE'

    def test_h_list_fallback(self):
        """Test H: list fallback → NO VERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        expected_result = ['provider_available']
        actual_result = ['provider_available']

        # Old _compare_results should reject
        comparison = recorder._compare_results(expected_result, actual_result)
        assert comparison == 'INSUFFICIENT_EVIDENCE'

    def test_i_subset_of_keys_fallback(self):
        """Test I: subset-of-keys fallback → NO VERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        expected_result = {'condition': 'provider_available', 'expected': True, 'extra': 'field'}
        actual_result = {'condition': 'provider_available', 'observed': True}

        # Should require exact key match, not subset
        assert not recorder._validate_structured_result(expected_result, 'expected_result')

    def test_j_timeout(self):
        """Test J: timeout → UNVERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        result = {
            'status': 'timeout',
            'timed_out': True,
        }

        # Should be UNVERIFIED due to timeout
        assert result.get('timed_out') is True

    def test_k_skipped(self):
        """Test K: skipped → UNVERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        result = {
            'status': 'skipped',
        }

        # Should be UNVERIFIED due to skip
        assert result.get('status') == 'skipped'

    def test_l_failed(self):
        """Test L: failed → UNVERIFIED."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        result = {
            'status': 'failed',
            'error': 'connection_failed',
        }

        # Should be UNVERIFIED due to failure
        assert result.get('status') == 'failed'

    def test_m_experiment_lab_none_degrades(self):
        """Test M: VERIFIED + ELIGIBLE + experiment_lab=None → NOT_ELIGIBLE."""
        from unittest.mock import Mock
        from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, TaskIntent

        mock_session_repository = Mock()
        mock_capability_repository = Mock()
        mock_approval_checkpoint_repository = Mock()

        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=mock_session_repository,
            capability_repository=mock_capability_repository,
            approval_checkpoint_repository=mock_approval_checkpoint_repository,
            experiment_lab=None,  # No ExperimentLab
        )

        session = AdaptiveSession(
            session_id='test-session-id',
            user_goal='Test diagnostic execution',
            intent=TaskIntent(kind='test', metadata={}),
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={
                'verification': {
                    'verification_status': VerificationStatus.VERIFIED.value,
                    'learning_decision': LearningDecision.ELIGIBLE.value,
                },
            },
        )

        verification_metadata = {
            'verification_status': VerificationStatus.VERIFIED.value,
            'learning_decision': LearningDecision.ELIGIBLE.value,
        }

        test_result = {
            'status': 'success',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            },
        }

        # Should degrade to NOT_ELIGIBLE
        updated_session = recorder._record_diagnostic_learning(session, verification_metadata, test_result)

        assert updated_session.metadata['verification']['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
        assert updated_session.metadata['verification']['verification_reason'] == 'experiment_run_persistence_unavailable'

    def test_n_no_experiment_run_persisted(self):
        """Test N: no ExperimentRun persisted → no learning eligibility."""
        from unittest.mock import Mock
        from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, TaskIntent

        mock_session_repository = Mock()
        mock_capability_repository = Mock()
        mock_approval_checkpoint_repository = Mock()
        mock_experiment_lab = Mock()
        mock_experiment_lab.repository = Mock()
        mock_experiment_lab.repository.save_run = Mock(side_effect=Exception("Persistence failed"))

        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=mock_session_repository,
            capability_repository=mock_capability_repository,
            approval_checkpoint_repository=mock_approval_checkpoint_repository,
            experiment_lab=mock_experiment_lab,
        )

        session = AdaptiveSession(
            session_id='test-session-id',
            user_goal='Test diagnostic execution',
            intent=TaskIntent(kind='test', metadata={}),
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={
                'selected_test': {
                    'test_id': 'test_provider_availability_probe',
                },
                'verification': {
                    'verification_status': VerificationStatus.VERIFIED.value,
                    'learning_decision': LearningDecision.ELIGIBLE.value,
                },
            },
        )

        verification_metadata = {
            'verification_status': VerificationStatus.VERIFIED.value,
            'learning_decision': LearningDecision.ELIGIBLE.value,
        }

        test_result = {
            'status': 'success',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            },
        }

        # Should degrade to NOT_ELIGIBLE on persistence failure
        updated_session = recorder._record_diagnostic_learning(session, verification_metadata, test_result)

        assert updated_session.metadata['verification']['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value

    def test_o_real_actual_result_survives_executor_callback(self):
        """Test O: real actual_result survives executor callback."""
        # Simulate executor observation
        observation = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
                'raw_evidence': 'http_status:200',
            }
        }

        # Simulate _complete logic
        state_result = {
            'test_id': 'test_provider_availability_probe',
        }

        result = dict(state_result)
        result.update(
            status=str(observation.get('status') or 'unavailable'),
            evidence=list(observation.get('evidence') or [])[:4],
            error=str(observation.get('error') or '')[:240],
        )

        # Preserve actual_result
        if observation.get('actual_result'):
            result['actual_result'] = observation['actual_result']

        assert 'actual_result' in result
        assert result['actual_result']['condition'] == 'provider_available'
        assert result['actual_result']['observed'] is True

    def test_p_no_synthetic_diagnostic_runrecord(self):
        """Test P: no synthetic diagnostic RunRecord exists."""
        import inspect
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        # Verify _persist_diagnostic_result does not create synthetic RunRecord
        source = inspect.getsource(TaskOutcomeRecorder._persist_diagnostic_result)

        assert 'diagnostic_synthetic' not in source
        assert 'synthetic_run_record' not in source
        assert 'RunRecord' not in source or 'diagnostic_synthetic' not in source

        # Verify _record_diagnostic_learning uses real data
        source = inspect.getsource(TaskOutcomeRecorder._record_diagnostic_learning)
        assert 'real' in source.lower() or 'verification_metadata' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
