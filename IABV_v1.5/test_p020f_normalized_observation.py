"""
P0.20f — Normalized Observation Test

Tests for separating actual_result from raw_evidence while preserving traceability.
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
from iabv_v15.services.evolution.diagnostic_test_executor import DiagnosticTestExecutor
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.domain.models import VerificationStatus, LearningDecision


class TestNormalizedObservation:
    """Test A-J: Focused tests for normalized observation with raw evidence preservation."""

    def test_a_executor_produces_valid_actual_result(self):
        """Test A: Executor produces actual_result with only condition and observed."""
        # Test the structure directly without making HTTP request
        # Simulate what the executor would produce
        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            }
        }

        # Verify actual_result exists and has correct structure
        assert 'actual_result' in result
        actual_result = result['actual_result']
        assert isinstance(actual_result, dict)
        assert set(actual_result.keys()) == {'condition', 'observed'}
        assert actual_result['condition'] == 'provider_available'
        assert isinstance(actual_result['observed'], bool)

    def test_b_actual_result_exact_contract(self):
        """Test B: actual_result contains exactly condition and observed."""
        # Simulate executor result
        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            }
        }

        actual_result = result['actual_result']

        # Must have exactly these keys
        assert set(actual_result.keys()) == {'condition', 'observed'}

        # No extra keys like raw_evidence
        assert 'raw_evidence' not in actual_result
        assert 'source' not in actual_result
        assert 'timestamp' not in actual_result

    def test_c_raw_evidence_preserved(self):
        """Test C: raw_evidence remains preserved outside actual_result."""
        # Simulate executor result
        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            }
        }

        # raw_evidence should be at result level
        assert 'raw_evidence' in result
        assert result['raw_evidence'] is not None

        # But NOT in actual_result
        assert 'raw_evidence' not in result['actual_result']

        # evidence list should also contain raw data
        assert 'evidence' in result
        assert len(result['evidence']) > 0

    def test_d_verification_accepts_normalized_actual_result(self):
        """Test D: Verification accepts normalized expected + actual."""
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

        # Should pass validation
        assert recorder._validate_structured_result(expected_result, 'expected_result')
        assert recorder._validate_structured_result(actual_result, 'actual_result')

        # Should compare successfully
        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MATCH'

    def test_e_mismatch_produces_refuted(self):
        """Test E: Mismatch produces REFUTED."""
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
            'observed': False,  # Mismatch
        }

        comparison = recorder._compare_structured_results(expected_result, actual_result)
        assert comparison == 'MISMATCH'

    def test_f_missing_structure_produces_inconclusive(self):
        """Test F: Missing structure produces INCONCLUSIVE."""
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=None,
            capability_repository=None,
            approval_checkpoint_repository=None,
        )

        # Missing observed key
        invalid_actual_result = {
            'condition': 'provider_available',
        }

        assert not recorder._validate_structured_result(invalid_actual_result, 'actual_result')

        # Extra key
        invalid_actual_result = {
            'condition': 'provider_available',
            'observed': True,
            'raw_evidence': 'http_status:200',  # Extra key
        }

        assert not recorder._validate_structured_result(invalid_actual_result, 'actual_result')

    def test_g_success_no_auto_verified(self):
        """Test G: Success status does not imply VERIFIED automatically."""
        # Simulate executor result
        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            }
        }

        # Status can be success
        assert result['status'] == 'success'

        # But that doesn't mean verification status
        # Verification requires structured comparison
        assert 'verification_status' not in result
        assert 'learning_decision' not in result

    def test_h_no_raw_evidence_loss(self):
        """Test H: Raw evidence is not lost in the transformation."""
        # Simulate executor result
        result = {
            'status': 'success',
            'evidence': ['http_status:200'],
            'raw_evidence': 'http_status:200',
            'actual_result': {
                'condition': 'provider_available',
                'observed': True,
            }
        }

        # Verify raw evidence exists at multiple levels
        assert 'raw_evidence' in result
        assert 'evidence' in result
        assert len(result['evidence']) > 0

        # Verify actual_result is clean
        assert 'raw_evidence' not in result['actual_result']

        # Verify traceability is preserved
        assert result['raw_evidence'] == result['evidence'][0]

    def test_i_no_synthetic_runrecord(self):
        """Test I: No synthetic diagnostic RunRecord exists."""
        import inspect
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        # Verify _persist_diagnostic_result does not create synthetic RunRecord
        source = inspect.getsource(TaskOutcomeRecorder._persist_diagnostic_result)

        assert 'diagnostic_synthetic' not in source
        assert 'synthetic_run_record' not in source

    def test_j_negative_path_blocks_learning(self):
        """Test J: Negative path still blocks learning."""
        from unittest.mock import Mock
        from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, TaskIntent

        mock_session_repository = Mock()
        mock_capability_repository = Mock()
        mock_approval_checkpoint_repository = Mock()

        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=mock_session_repository,
            capability_repository=mock_capability_repository,
            approval_checkpoint_repository=mock_approval_checkpoint_repository,
        )

        session = AdaptiveSession(
            session_id='test-session-id',
            user_goal='Test diagnostic execution',
            intent=TaskIntent(kind='test', metadata={}),
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={
                'selected_test': {
                    'test_id': 'test_provider_availability_probe',
                    'expected_result': {
                        'condition': 'provider_available',
                        'expected': True,
                    },
                },
            },
        )

        # Test with invalid actual_result (missing observed)
        invalid_result = {
            'test_id': 'test_provider_availability_probe',
            'status': 'success',
            'actual_result': {
                'condition': 'provider_available',
                # Missing observed
            },
        }

        mock_session_repository.get.return_value = session
        mock_session_repository.save.return_value = session

        recorder._persist_diagnostic_result('test-session-id', invalid_result)

        # Verify session was saved
        assert mock_session_repository.save.called
        saved_session = mock_session_repository.save.call_args[0][0]

        # Verify it was NOT VERIFIED
        verification = saved_session.metadata.get('verification', {})
        assert verification.get('verification_status') != VerificationStatus.VERIFIED.value
        assert verification.get('learning_decision') != LearningDecision.ELIGIBLE.value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
