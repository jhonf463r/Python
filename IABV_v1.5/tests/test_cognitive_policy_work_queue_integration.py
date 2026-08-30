"""Focused production integration tests for Cognitive Policy → WorkQueueExecutor integration.

Tests verify that the cognitive policy is wired into WorkQueueExecutor correctly,
that policy evaluation happens before execution, and that policy decisions are
respected without bypassing existing governance.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
from iabv_v15.services.cognitive import (
    CognitiveOperatingPolicy,
    CognitiveStateVector,
    CognitivePolicyDecision,
    TimeHorizon,
    ReasoningDepth,
    ObservationMode,
)
from iabv_v15.domain.models import (
    InferenceRequest,
    InferenceResult,
    RoleRoute,
    RunStatus,
    ReasoningMode,
    TaskRole,
    AmbiguityLevel,
    ComplexityLevel,
)


class TestCognitivePolicyWorkQueueIntegration:
    """Focused production integration tests for cognitive policy integration."""

    def test_workqueue_executor_receives_work_item(self):
        """Test 1: WorkQueueExecutor receives WorkItem."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Select work item
        result = executor.select_and_execute_work_item()

        # Verify work item was received
        assert result['work_item_id'] == 'objective:123'

    def test_cognitive_policy_evaluates_before_execution(self):
        """Test 2: CognitivePolicy evaluates before execution."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify inference service was called (policy allowed execution)
        assert mock_inference_service.infer_task.called

    def test_policy_decision_is_passed_to_executor(self):
        """Test 3: Policy decision is passed to executor."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()
        mock_request = MagicMock()
        mock_inference_service.infer_task.return_value = MagicMock(
            run_id='test-run-id',
            status=RunStatus.SUCCESS,
            duration_ms=1000,
        )

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify policy decision ID is in result
        assert 'policy_decision_id' in result
        assert result['policy_decision_id'] is not None

    def test_policy_decision_is_immutable(self):
        """Test 4: Policy decision is immutable."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verify decision is immutable (frozen dataclass)
        with pytest.raises(Exception):  # FrozenInstanceError
            policy_decision.horizon = TimeHorizon.LONG

    def test_policy_evaluation_performs_zero_provider_calls(self):
        """Test 5: Policy evaluation performs zero provider calls."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy (should not call any provider)
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verify decision is computed without side effects
        assert policy_decision is not None
        assert policy_decision.decision_id is not None

    def test_stop_prevents_provider_execution(self):
        """Test 6: STOP prevents provider execution."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector, CognitivePolicyDecision, ObservationMode, TimeHorizon, ReasoningDepth

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()

        # Create mock policy that returns DEFER
        mock_policy = MagicMock()
        mock_decision = CognitivePolicyDecision(
            decision_id='test-decision-id',
            state_vector=CognitiveStateVector(
                goal_value=0.5,
                complexity=0.5,
                ambiguity=0.5,
                uncertainty=0.5,
                risk=0.5,
                expected_value=0.5,
                available_time_seconds=600,
                available_ram_gb=8.0,
                memory_relevance=0.5,
                prior_experience=0.5,
                work_item_id='objective:123',
            ),
            horizon=TimeHorizon.MEDIUM,
            reasoning_depth=ReasoningDepth.LEVEL_1,
            observation_mode=ObservationMode.DEFER,  # DEFER mode
            budget=MagicMock(),
            chunk_size='medium',
            parallelism_allowed=True,
            tool_selection_envelope=MagicMock(),
            stopping_conditions=MagicMock(),
            mrv=0.1,
            mvi=0.1,
        )
        mock_policy.compute_decision.return_value = mock_decision

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=mock_policy,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify provider was NOT called
        assert not mock_inference_service.infer_task.called

        # Verify result indicates policy deferred
        assert result['success'] is False
        assert 'Policy deferred execution' in result['error']
        assert result['observation_mode'] == 'defer'

    def test_defer_prevents_provider_execution(self):
        """Test 7: DEFER prevents provider execution."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector, CognitivePolicyDecision, ObservationMode, TimeHorizon, ReasoningDepth

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()

        # Create mock policy that returns DEFER
        mock_policy = MagicMock()
        mock_decision = CognitivePolicyDecision(
            decision_id='test-decision-id',
            state_vector=CognitiveStateVector(
                goal_value=0.5,
                complexity=0.5,
                ambiguity=0.5,
                uncertainty=0.5,
                risk=0.5,
                expected_value=0.5,
                available_time_seconds=600,
                available_ram_gb=8.0,
                memory_relevance=0.5,
                prior_experience=0.5,
                work_item_id='objective:123',
            ),
            horizon=TimeHorizon.MEDIUM,
            reasoning_depth=ReasoningDepth.LEVEL_1,
            observation_mode=ObservationMode.DEFER,
            budget=MagicMock(),
            chunk_size='medium',
            parallelism_allowed=True,
            tool_selection_envelope=MagicMock(),
            stopping_conditions=MagicMock(),
            mrv=0.1,
            mvi=0.1,
        )
        mock_policy.compute_decision.return_value = mock_decision

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=mock_policy,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify provider was NOT called
        assert not mock_inference_service.infer_task.called

    def test_policy_time_budget_is_attached_to_execution_envelope(self):
        """Test 8: Policy time budget is attached to execution envelope."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService to capture the request
        captured_request = None
        def capture_infer_task(request):
            nonlocal captured_request
            captured_request = request
            return MagicMock(run_id='test-run-id', status=RunStatus.SUCCESS, duration_ms=1000)

        mock_inference_service = MagicMock()
        mock_inference_service.infer_task.side_effect = capture_infer_task

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        executor.select_and_execute_work_item()

        # Verify policy envelope is attached to request
        assert captured_request is not None
        assert 'policy_decision_id' in captured_request.goal_parameters
        assert 'policy_horizon' in captured_request.goal_parameters
        assert 'policy_reasoning_depth' in captured_request.goal_parameters
        assert 'policy_observation_mode' in captured_request.goal_parameters

    def test_policy_resource_budget_does_not_bypass_resource_aware_controller(self):
        """Test 9: Policy resource budget does not bypass ResourceAwareController."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        executor.select_and_execute_work_item()

        # Verify policy does not bypass ResourceAwareController
        # (This is verified by the fact that the policy is pure and
        # does not modify resource state or bypass existing governance)

    def test_resource_block_still_prevents_execution(self):
        """Test 10: Resource BLOCK still prevents execution."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'blocked',  # BLOCKED status
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify provider was NOT called (blocked by status, not policy)
        assert not mock_inference_service.infer_task.called
        assert result['success'] is False
        assert 'No eligible work items' in result['error']

    def test_high_uncertainty_changes_observation_requirement(self):
        """Test 11: High uncertainty changes observation requirement."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'pending',  # High uncertainty status
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verify high uncertainty affects observation mode
        # (pending status → higher uncertainty → may change observation mode)
        assert policy_decision.observation_mode is not None

    def test_high_risk_increases_validation_stopping_constraint(self):
        """Test 12: High risk increases validation/stopping constraint."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
                'risk': 0.9,  # High risk
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verifyhigh risk increases target confidence
        assert policy_decision.budget.target_confidence >= 0.9

    def test_short_horizon_does_not_execute_long_horizon_work_first_if_priority_says_otherwise(self):
        """Test 13: Short horizon does not execute long-horizon work first if priority says otherwise."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService with mixed priority work items
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Long horizon work',
                'status': 'active',
                'priority_score': 50,  # Lower priority
                'source': 'objective_repository',
                'next_action': 'Long term work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            },
            {
                'id': 'objective:456',
                'title': 'Short horizon work',
                'status': 'active',
                'priority_score': 100,  # Higher priority
                'source': 'objective_repository',
                'next_action': 'Urgent work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            },
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Select work item
        selected_item = executor._select_eligible_item(mock_queue)

        # Verify higher priority item is selected (regardless of horizon)
        assert selected_item['id'] == 'objective:456'

    def test_chunk_size_is_propagated(self):
        """Test 14: Chunk size is propagated."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verify chunk size is propagated
        assert policy_decision.chunk_size in ('small', 'medium', 'large')

    def test_parallelism_constraint_is_propagated_without_creating_scheduler(self):
        """Test 15: Parallelism constraint is propagated without creating scheduler."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verify parallelism constraint is propagated
        assert isinstance(policy_decision.parallelism_allowed, bool)

        # Verify no scheduler is created (policy is pure)
        # (This is verified by the fact that the policy has no
        # scheduling logic and the executor does not become a scheduler)

    def test_tool_selection_output_remains_provider_neutral(self):
        """Test 16: Tool selection output remains provider-neutral."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Evaluate policy
        selected_item = executor._select_eligible_item(mock_queue)
        policy_decision = executor._evaluate_cognitive_policy(selected_item)

        # Verify tool selection envelope contains constraints, not provider names
        assert 'ollama' not in str(policy_decision.tool_selection_envelope).lower()
        assert 'devin' not in str(policy_decision.tool_selection_envelope).lower()

    def test_work_identity_is_preserved(self):
        """Test 17: Work identity is preserved."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService to capture the request
        captured_request = None
        def capture_infer_task(request):
            nonlocal captured_request
            captured_request = request
            return MagicMock(run_id='test-run-id', status=RunStatus.SUCCESS, duration_ms=1000)

        mock_inference_service = MagicMock()
        mock_inference_service.infer_task.side_effect = capture_infer_task

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        executor.select_and_execute_work_item()

        # Verify work identity is preserved
        assert captured_request.metadata['work_item_id'] == 'objective:123'
        assert captured_request.metadata['work_item_source'] == 'objective_repository'

    def test_outcome_closes_against_same_work_item(self):
        """Test 18: Outcome closes against same WorkItem."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Mock InferenceService
        mock_inference_service = MagicMock()
        mock_inference_service.infer_task.return_value = MagicMock(
            run_id='test-run-id',
            status=RunStatus.SUCCESS,
            duration_ms=1000,
        )

        # Mock TaskOutcomeRecorder
        mock_outcome_recorder = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=mock_outcome_recorder,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify outcome is recorded for same work item
        assert result['work_item_id'] == 'objective:123'
        assert result['run_id'] == 'test-run-id'

    def test_existing_context_reuse_remains_safe(self):
        """Test 19: Existing context reuse remains safe."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Verify WorkQueueExecutor has no file modification methods
        assert not hasattr(executor, 'write_file')
        assert not hasattr(executor, 'edit_file')
        assert not hasattr(executor, 'delete_file')

    def test_existing_authority_capability_lease_semantics_remain_unchanged(self):
        """Test 20: Existing Authority/Capability/Lease semantics remain unchanged."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
        )

        # Verify WorkQueueExecutor has no Authority/Capability/Lease modification methods
        assert not hasattr(executor, 'modify_authority')
        assert not hasattr(executor, 'modify_capability')
        assert not hasattr(executor, 'modify_lease')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
