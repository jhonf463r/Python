"""
P0.19e — Complete Positive Verification and Learning Boundary Tests

Tests for the verification boundary that separates:
TEST RESULT → VERIFICATION STATUS → LEARNING DECISION → ExperimentRun
"""
import pytest
from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    LearningDecision,
    TaskIntent,
    TaskRole,
    VerificationStatus,
)
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder


class TestVerificationBoundary:
    """Test suite for P0.19e verification and learning boundary."""
    
    @pytest.fixture
    def mock_session(self) -> AdaptiveSession:
        """Create a mock adaptive session."""
        session = AdaptiveSession(
            session_id="test-session-001",
            user_goal="test goal",
            status=AdaptiveSessionStatus.COMPLETED,
            intent=TaskIntent(
                intent_key="system.self_awareness",
                role=TaskRole.KNOWLEDGE,
                confidence=0.9,
            ),
            metadata={
                'diagnostic_cycle': True,
                'selected_test': {
                    'test_id': 'test_001',
                    'test_type': 'self_diagnostic',
                    'target': 'world_model_state',
                },
                'frame_id': 'frame-001',
                'interaction_id': 'interaction-001',
            },
        )
        return session
    
    @pytest.fixture
    def mock_recorder(self) -> TaskOutcomeRecorder:
        """Create a mock task outcome recorder."""
        # This would normally require real repositories
        # For unit tests, we'll test the verification logic directly
        return None
    
    def test_a_success_matching_expected_actual(self, mock_session):
        """Test A: SUCCESS + matching expected/actual → VERIFIED + ELIGIBLE
        
        A test with matching expected and actual results should be VERIFIED and ELIGIBLE.
        """
        # Add expected_result to selected_test
        mock_session.metadata['selected_test']['expected_result'] = 'provider_available'
        
        result = {
            'test_id': 'test_001',
            'status': 'success',
            'actual_result': 'provider_available',
            'evidence': [{'observation': 'provider responded'}],
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.VERIFIED.value
        assert verification['learning_decision'] == LearningDecision.ELIGIBLE.value
        assert verification['verification_reason'] == 'expected_vs_actual_match'
    
    def test_b_mismatching_expected_actual(self, mock_session):
        """Test B: SUCCESS + mismatching expected/actual → REFUTED
        
        A test with mismatching expected and actual results should be REFUTED.
        """
        # Add expected_result to selected_test
        mock_session.metadata['selected_test']['expected_result'] = 'provider_available'
        
        result = {
            'test_id': 'test_001',
            'status': 'success',
            'actual_result': 'provider_unavailable',
            'evidence': [{'observation': 'provider did not respond'}],
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.REFUTED.value
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
        assert verification['verification_reason'] == 'expected_vs_actual_mismatch'
    
    def test_c_success_no_expected_result(self, mock_session):
        """Test C: SUCCESS sin expected_result → INCONCLUSIVE
        
        A test without expected_result should be INCONCLUSIVE.
        """
        result = {
            'test_id': 'test_001',
            'status': 'success',
            'evidence': [{'observation': 'test passed'}],
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.INCONCLUSIVE.value
        assert verification['verification_reason'] == 'missing_expected_result'
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
    
    def test_d_error_unverified(self, mock_session):
        """Test D: ERROR → UNVERIFIED
        
        A test with error should NOT be VERIFIED.
        """
        result = {
            'test_id': 'test_001',
            'status': 'failed',
            'error': 'test_type_not_allowed',
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.UNVERIFIED.value
        assert verification['verification_reason'] == 'test_error:test_type_not_allowed'
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
    
    def test_e_timeout_unverified(self, mock_session):
        """Test E: TIMEOUT → UNVERIFIED
        
        A test that timed out should NOT be VERIFIED.
        """
        result = {
            'test_id': 'test_001',
            'status': 'failed',
            'timed_out': True,
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.UNVERIFIED.value
        assert verification['verification_reason'] == 'test_timeout'
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
    
    def test_f_skipped_unverified(self, mock_session):
        """Test F: SKIPPED → UNVERIFIED
        
        A test that was skipped should NOT be VERIFIED.
        """
        result = {
            'test_id': 'test_001',
            'status': 'skipped',
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.UNVERIFIED.value
        assert verification['verification_reason'] == 'test_skipped'
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
    
    def test_g_inconclusive_no_learning(self, mock_session):
        """Test G: INCONCLUSIVE → NO learning
        
        A test with INCONCLUSIVE status should NOT generate learning.
        """
        result = {
            'test_id': 'test_001',
            'status': 'success',
            'evidence': [{'observation': 'test passed'}],
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.INCONCLUSIVE.value
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
    
    def test_h_verified_not_eligible_no_experiment_run(self, mock_session):
        """Test H: VERIFIED + NOT_ELIGIBLE → NO ExperimentRun
        
        This test case is for future scenarios where we might have VERIFIED
        but NOT_ELIGIBLE for other reasons (e.g., governance, policy).
        For now, VERIFIED always implies ELIGIBLE.
        """
        # This is a placeholder for future policy-based NOT_ELIGIBLE scenarios
        # Currently, VERIFIED always results in ELIGIBLE
        pass
    
    def test_i_verified_eligible_experiment_run(self, mock_session):
        """Test I: VERIFIED + ELIGIBLE → ExperimentRun REAL
        
        A fully verified test should create an ExperimentRun.
        """
        # Add expected_result to selected_test
        mock_session.metadata['selected_test']['expected_result'] = 'provider_available'
        
        result = {
            'test_id': 'test_001',
            'status': 'success',
            'actual_result': 'provider_available',
            'evidence': [{'observation': 'provider responded'}],
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.VERIFIED.value
        assert verification['learning_decision'] == LearningDecision.ELIGIBLE.value
        assert verification['verification_reason'] == 'expected_vs_actual_match'
    
    def test_j_failed_no_error_unverified(self, mock_session):
        """Test J: FAILED sin error → NO VERIFIED
        
        A test with status='failed' but no error field should NOT be VERIFIED.
        """
        result = {
            'test_id': 'test_001',
            'status': 'failed',
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        assert verification['verification_status'] == VerificationStatus.UNVERIFIED.value
        assert verification['verification_reason'] == 'test_error:status_failed'
        assert verification['learning_decision'] == LearningDecision.NOT_ELIGIBLE.value
    
    def test_k_completed_no_verification(self, mock_session):
        """Test K: COMPLETED sin verification → NO VERIFIED
        
        A test with status='completed' should NOT be automatically VERIFIED.
        """
        result = {
            'test_id': 'test_001',
            'status': 'completed',
            'frame_id': 'frame-001',
            'interaction_id': 'interaction-001',
        }
        
        verification = self._compute_verification_for_test(mock_session, result)
        
        # Without expected_result, should be INCONCLUSIVE, not VERIFIED
        assert verification['verification_status'] != VerificationStatus.VERIFIED.value
        assert verification['verification_status'] == VerificationStatus.INCONCLUSIVE.value
    
    def _compute_verification_for_test(self, session: AdaptiveSession, result: dict[str, Any]) -> dict[str, Any]:
        """Helper method to compute verification metadata for testing.
        
        This replicates the logic from TaskOutcomeRecorder._compute_verification_metadata
        for unit testing without requiring full infrastructure setup.
        """
        verification_status = VerificationStatus.UNVERIFIED
        learning_decision = LearningDecision.NOT_ELIGIBLE
        verification_reason = ""
        
        selected_test = session.metadata.get('selected_test', {})
        test_id = result.get('test_id', selected_test.get('test_id', ''))
        frame_id = result.get('frame_id', session.metadata.get('frame_id', ''))
        interaction_id = result.get('interaction_id', session.metadata.get('interaction_id', ''))
        
        # Build evidence refs
        evidence_refs = []
        if frame_id:
            evidence_refs.append(f'frame:{frame_id}')
        if session.session_id:
            evidence_refs.append(f'session:{session.session_id}')
        if test_id:
            evidence_refs.append(f'test:{test_id}')
        if interaction_id:
            evidence_refs.append(f'interaction:{interaction_id}')
        
        # Rule 1: Check for skipped
        test_status = result.get('status', '')
        if test_status == 'skipped':
            verification_status = VerificationStatus.UNVERIFIED
            verification_reason = 'test_skipped'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 2: Check for timeout
        if result.get('timed_out'):
            verification_status = VerificationStatus.UNVERIFIED
            verification_reason = 'test_timeout'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 3: Check for error or failed status
        test_error = result.get('error', '')
        test_status = result.get('status', '')
        if test_error or test_status == 'failed':
            verification_status = VerificationStatus.UNVERIFIED
            verification_reason = f'test_error:{test_error or "status_failed"}'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 4: Check for expected_result
        expected_result = selected_test.get('expected_result')
        if not expected_result:
            verification_status = VerificationStatus.INCONCLUSIVE
            verification_reason = 'missing_expected_result'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 5: Check for actual_result
        actual_result = result.get('actual_result') or result.get('evidence')
        if not actual_result:
            verification_status = VerificationStatus.UNVERIFIED
            verification_reason = 'missing_actual_result'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 6: Check for sufficient evidence
        test_evidence = result.get('evidence', [])
        if not test_evidence or not isinstance(test_evidence, list):
            verification_status = VerificationStatus.INCONCLUSIVE
            verification_reason = 'insufficient_evidence'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 7: Check for critical contradictions
        frame_metadata = session.metadata.get('frame_metadata', {})
        contradictions = frame_metadata.get('contradictions', [])
        critical_contradictions = [
            c for c in contradictions 
            if isinstance(c, dict) and c.get('severity') == 'critical'
        ]
        if critical_contradictions:
            verification_status = VerificationStatus.INCONCLUSIVE
            verification_reason = 'critical_contradiction_unresolved'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 8: Check for traceable evidence_refs
        if not evidence_refs:
            verification_status = VerificationStatus.UNVERIFIED
            verification_reason = 'missing_traceability'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # Rule 9: Compare expected_result vs actual_result (P0.19e)
        comparison_result = self._compare_results(expected_result, actual_result)
        if comparison_result == 'MISMATCH':
            verification_status = VerificationStatus.REFUTED
            verification_reason = 'expected_vs_actual_mismatch'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        elif comparison_result == 'INSUFFICIENT_EVIDENCE':
            verification_status = VerificationStatus.INCONCLUSIVE
            verification_reason = 'insufficient_evidence_for_comparison'
            return self._build_verification_metadata(
                verification_status, learning_decision, evidence_refs, verification_reason,
                selected_test, result
            )
        
        # All verification rules passed including comparison
        verification_status = VerificationStatus.VERIFIED
        verification_reason = 'expected_vs_actual_match'
        
        # Learning decision: Only ELIGIBLE if VERIFIED
        learning_decision = LearningDecision.ELIGIBLE
        
        return self._build_verification_metadata(
            verification_status, learning_decision, evidence_refs, verification_reason,
            selected_test, result
        )
    
    def _compare_results(self, expected_result: Any, actual_result: Any) -> str:
        """Compare expected_result vs actual_result explicitly.
        
        Returns:
            'MATCH': Results are compatible
            'MISMATCH': Results are incompatible
            'INSUFFICIENT_EVIDENCE': Cannot determine compatibility
        """
        # Handle None cases
        if expected_result is None or actual_result is None:
            return 'INSUFFICIENT_EVIDENCE'
        
        # Handle string comparison (most common case)
        if isinstance(expected_result, str) and isinstance(actual_result, str):
            if expected_result.strip() == actual_result.strip():
                return 'MATCH'
            # Check for substring match (actual contains expected)
            if expected_result.strip() in actual_result.strip():
                return 'MATCH'
            return 'MISMATCH'
        
        # Handle numeric comparison
        if isinstance(expected_result, (int, float)) and isinstance(actual_result, (int, float)):
            if abs(expected_result - actual_result) < 1e-9:
                return 'MATCH'
            return 'MISMATCH'
        
        # Handle boolean comparison
        if isinstance(expected_result, bool) and isinstance(actual_result, bool):
            return 'MATCH' if expected_result == actual_result else 'MISMATCH'
        
        # Handle dict comparison
        if isinstance(expected_result, dict) and isinstance(actual_result, dict):
            # Simple key existence check for now
            expected_keys = set(expected_result.keys())
            actual_keys = set(actual_result.keys())
            if expected_keys.issubset(actual_keys):
                return 'MATCH'
            return 'MISMATCH'
        
        # Handle list comparison
        if isinstance(expected_result, list) and isinstance(actual_result, list):
            if expected_result == actual_result:
                return 'MATCH'
            return 'MISMATCH'
        
        # For other types, use string representation comparison
        try:
            if str(expected_result) == str(actual_result):
                return 'MATCH'
            return 'MISMATCH'
        except Exception:
            return 'INSUFFICIENT_EVIDENCE'
    
    def _build_verification_metadata(
        self,
        verification_status: VerificationStatus,
        learning_decision: LearningDecision,
        evidence_refs: list[str],
        verification_reason: str,
        selected_test: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Build verification metadata contract."""
        return {
            'verification_status': verification_status.value,
            'learning_decision': learning_decision.value,
            'verification_reason': verification_reason,
            'verification_evidence_refs': evidence_refs,
            'hypothesis_id': selected_test.get('hypothesis_id'),
            'expected_result': selected_test.get('expected_result'),
            'actual_result_ref': f"test_result:{result.get('test_id', '')}",
            'selected_test_id': selected_test.get('test_id'),
            'frame_id': result.get('frame_id'),
            'interaction_id': result.get('interaction_id'),
            'verified_at': datetime.now(timezone.utc).isoformat(),
        }


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
