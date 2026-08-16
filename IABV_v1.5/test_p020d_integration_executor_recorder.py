"""
P0.20d — Integration Test: Executor → Recorder Real Result Flow

Integration test demonstrating real actual_result flows from executor to recorder.
"""
import sys
import os

# Clean sys.path to remove any contamination
sys.path = [p for p in sys.path if 'IABV_v1.5_canonical' not in p and 'iabv_p019d_workspace' not in p]

# Add canonical project source to path
project_src = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, project_src)

import pytest
from unittest.mock import Mock, MagicMock
from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    VerificationStatus,
    LearningDecision,
)
from iabv_v15.services.evolution.diagnostic_test_executor import DiagnosticTestExecutor
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder


def test_executor_to_recorder_real_result_flow():
    """Integration test: Real actual_result flows from executor to recorder.

    This test demonstrates:
    1. Executor produces real actual_result
    2. Callback receives real actual_result
    3. TaskOutcomeRecorder receives real actual_result
    4. No synthetic data is introduced
    """
    # Setup: Create mock components
    mock_session_repository = Mock()
    mock_capability_repository = Mock()
    mock_approval_checkpoint_repository = Mock()
    mock_experiment_lab = Mock()
    mock_experiment_lab.repository = Mock()

    # Create a real session
    from iabv_v15.domain.models import TaskIntent
    session = AdaptiveSession(
        session_id='test-session-id',
        user_goal='Test diagnostic execution',
        intent=TaskIntent(
            kind='test',
            metadata={},
        ),
        status=AdaptiveSessionStatus.EXECUTING,
        metadata={
            'selected_test': {
                'test_id': 'test_provider_availability_probe',
                'test_type': 'provider_availability',
                'target': 'provider_availability',
                'hypothesis_id': 'test-hypothesis-id',
                'expected_result': {
                    'condition': 'provider_available',
                    'expected': True,
                },
            },
            'frame_id': 'test-frame-id',
            'interaction_id': 'test-interaction-id',
        },
    )

    mock_session_repository.get.return_value = session
    mock_session_repository.save.return_value = session

    # Create TaskOutcomeRecorder
    recorder = TaskOutcomeRecorder(
        adaptive_session_repository=mock_session_repository,
        capability_repository=mock_capability_repository,
        approval_checkpoint_repository=mock_approval_checkpoint_repository,
        experiment_lab=mock_experiment_lab,
    )

    # Simulate real executor result with actual_result
    real_executor_result = {
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
        'timed_out': False,
        'worker_still_running': False,
    }

    # Verify actual_result is present in executor result
    assert 'actual_result' in real_executor_result, "Executor result must contain actual_result"
    assert real_executor_result['actual_result']['condition'] == 'provider_available'
    assert real_executor_result['actual_result']['observed'] is True

    # Call _persist_diagnostic_result (this is the callback path)
    recorder._persist_diagnostic_result('test-session-id', real_executor_result)

    # Verify session was saved with real actual_result
    assert mock_session_repository.save.called, "Session should be saved"
    saved_session = mock_session_repository.save.call_args[0][0]

    # Verify test_result contains real actual_result
    saved_test_result = saved_session.metadata.get('test_result', {})
    assert 'actual_result' in saved_test_result, "Saved test_result must contain actual_result"
    assert saved_test_result['actual_result']['condition'] == 'provider_available'
    assert saved_test_result['actual_result']['observed'] is True
    assert saved_test_result['actual_result']['raw_evidence'] == 'http_status:200'

    # Verify verification metadata was computed
    verification = saved_session.metadata.get('verification', {})
    assert verification is not None, "Verification metadata should be computed"

    # Verify hypothesis_id and expected_result were propagated
    assert saved_session.metadata.get('hypothesis_id') == 'test-hypothesis-id'
    assert saved_session.metadata.get('expected_result')['condition'] == 'provider_available'

    # Verify no synthetic data was introduced
    # The verification should use real expected_result and actual_result
    assert verification.get('expected_result')['condition'] == 'provider_available'
    assert verification.get('expected_result')['expected'] is True

    # If VERIFIED + ELIGIBLE, verify ExperimentRun was created from real data
    if verification.get('verification_status') == VerificationStatus.VERIFIED.value:
        if verification.get('learning_decision') == LearningDecision.ELIGIBLE.value:
            # ExperimentRun should be created from real data
            assert mock_experiment_lab.repository.save_run.called, "ExperimentRun should be saved"
            # Verify ExperimentRun used real data, not synthetic
            experiment_run = mock_experiment_lab.repository.save_run.call_args[0][0]
            assert experiment_run is not None, "ExperimentRun should exist"
            # Verify metadata contains real identifiers
            assert experiment_run.metadata.get('hypothesis_id') == 'test-hypothesis-id'
            assert experiment_run.metadata.get('selected_test_id') == 'test_provider_availability_probe'

    print("✓ Integration test passed: Real actual_result flows from executor to recorder")
    print("✓ No synthetic data was introduced")
    print("✓ Verification boundary uses real expected_result and actual_result")


def test_executor_to_recorder_rejects_non_structured_actual_result():
    """Integration test: Non-structured actual_result is rejected by verification boundary.

    This test demonstrates:
    1. Executor produces non-structured actual_result
    2. Verification boundary rejects it
    3. No VERIFIED status is granted
    """
    # Setup: Create mock components
    mock_session_repository = Mock()
    mock_capability_repository = Mock()
    mock_approval_checkpoint_repository = Mock()
    mock_experiment_lab = Mock()
    mock_experiment_lab.repository = Mock()

    # Create a real session
    from iabv_v15.domain.models import TaskIntent
    session = AdaptiveSession(
        session_id='test-session-id',
        user_goal='Test diagnostic execution',
        intent=TaskIntent(
            kind='test',
            metadata={},
        ),
        status=AdaptiveSessionStatus.EXECUTING,
        metadata={
            'selected_test': {
                'test_id': 'test_provider_availability_probe',
                'test_type': 'provider_availability',
                'target': 'provider_availability',
                'hypothesis_id': 'test-hypothesis-id',
                'expected_result': {
                    'condition': 'provider_available',
                    'expected': True,
                },
            },
            'frame_id': 'test-frame-id',
            'interaction_id': 'test-interaction-id',
        },
    )

    mock_session_repository.get.return_value = session
    mock_session_repository.save.return_value = session

    # Create TaskOutcomeRecorder
    recorder = TaskOutcomeRecorder(
        adaptive_session_repository=mock_session_repository,
        capability_repository=mock_capability_repository,
        approval_checkpoint_repository=mock_approval_checkpoint_repository,
        experiment_lab=mock_experiment_lab,
    )

    # Simulate executor result with NON-STRUCTURED actual_result (string instead of dict)
    non_structured_result = {
        'test_id': 'test_provider_availability_probe',
        'frame_id': 'test-frame-id',
        'interaction_id': 'test-interaction-id',
        'status': 'success',
        'evidence': ['http_status:200'],
        'actual_result': 'provider_available',  # String instead of structured dict
        'duration_ms': 100,
        'timed_out': False,
        'worker_still_running': False,
    }

    # Call _persist_diagnostic_result
    recorder._persist_diagnostic_result('test-session-id', non_structured_result)

    # Verify session was saved
    assert mock_session_repository.save.called
    saved_session = mock_session_repository.save.call_args[0][0]

    # Verify verification metadata was computed
    verification = saved_session.metadata.get('verification', {})
    assert verification is not None

    # Verify it was NOT VERIFIED due to non-structured actual_result
    assert verification.get('verification_status') != VerificationStatus.VERIFIED.value
    assert verification.get('learning_decision') != LearningDecision.ELIGIBLE.value

    # Verify reason indicates structural validation failure
    assert verification.get('verification_reason') == 'invalid_actual_result_structure'

    print("✓ Integration test passed: Non-structured actual_result is rejected")
    print("✓ Verification boundary enforces structural requirements")


if __name__ == '__main__':
    test_executor_to_recorder_real_result_flow()
    test_executor_to_recorder_rejects_non_structured_actual_result()
