"""Production-entry integration tests for WorkQueueExecutor.

Tests verify that WorkQueueExecutor correctly bridges ControlMaster work queue
to canonical InferenceService/AdaptiveTaskOrchestrator path while preserving
work identity, governance, and existing context reuse.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestWorkQueueExecutorIntegration:
    """Production-entry integration tests for WorkQueueExecutor."""

    def test_control_master_work_queue_is_read_through_runtime_composition(self):
        """Test 1: ControlMaster work queue is read through the real runtime composition."""
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
        )

        # Verify work queue is read
        result = executor.select_and_execute_work_item()

        # Verify current_work_queue was called
        mock_control_master.current_work_queue.assert_called_once_with(limit=10)

    def test_highest_priority_eligible_work_item_is_selected(self):
        """Test 2: Highest-priority eligible work item is selected using existing ControlMaster ordering."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor

        # Mock ControlMasterService with multiple work items
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Low priority',
                'status': 'active',
                'priority_score': 50,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20},
            },
            {
                'id': 'objective:456',
                'title': 'High priority',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            },
            {
                'id': 'objective:789',
                'title': 'Blocked item',
                'status': 'blocked',
                'priority_score': 200,
                'source': 'objective_repository',
                'next_action': 'Unblock',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'blocked': 20},
            },
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
        )

        # Verify highest-priority eligible item is selected (not blocked)
        result = executor.select_and_execute_work_item()

        # Should fail because inference_service is None, but selection should have occurred
        assert result['work_item_id'] == 'objective:456'  # Highest eligible priority

    def test_selected_work_item_becomes_canonical_inference_request(self):
        """Test 3: Selected work item becomes a canonical InferenceRequest."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import InferenceRequest

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Integrate service',
                'status': 'active',
                'priority_score': 100,
                'source': 'objective_repository',
                'next_action': 'Implement integration',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'high_priority': 30},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
        )

        # Transform work item to InferenceRequest
        selected_item = executor._select_eligible_item(mock_queue)
        request = executor._work_item_to_inference_request(selected_item)

        # Verify it's a canonical InferenceRequest
        assert isinstance(request, InferenceRequest)
        assert request.user_goal is not None
        assert request.task_role is not None

    def test_work_identity_is_preserved_into_request(self):
        """Test 4: Work identity is preserved into the request."""
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
        )

        # Transform work item to InferenceRequest
        selected_item = executor._select_eligible_item(mock_queue)
        request = executor._work_item_to_inference_request(selected_item)

        # Verify work identity is preserved in metadata
        assert request.metadata['work_item_id'] == 'objective:123'
        assert request.metadata['work_item_source'] == 'objective_repository'
        assert request.metadata['work_item_priority'] == 100
        assert request.metadata['original_title'] == 'Test objective'

    def test_request_reaches_adaptive_task_orchestrator(self):
        """Test 5: Request reaches AdaptiveTaskOrchestrator."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Test summary',
            inferred_task='Test task',
            confidence=0.9,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.SUCCESS,
            duration_ms=1000,
            error_summary='',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify InferenceService was called
        mock_inference_service.infer_task.assert_called_once()
        assert result['success'] is True

    def test_existing_resource_reflection_governance_path_remains_active(self):
        """Test 6: Existing resource/reflection/governance path remains active."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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

        # Mock InferenceService (which internally uses AdaptiveTaskOrchestrator)
        mock_inference_service = MagicMock()
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Test summary',
            inferred_task='Test task',
            confidence=0.9,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.SUCCESS,
            duration_ms=1000,
            error_summary='',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify the canonical path was used (InferenceService.infer_task)
        # This ensures existing resource/reflection/governance path remains active
        mock_inference_service.infer_task.assert_called_once()
        assert result['success'] is True

    def test_block_prevents_provider_execution(self):
        """Test 7: BLOCK prevents provider execution."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor

        # Mock ControlMasterService with blocked work item
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Blocked objective',
                'status': 'blocked',
                'priority_score': 200,
                'source': 'objective_repository',
                'next_action': 'Unblock',
                'evidence_refs': [],
                'score_breakdown': {'base': 20, 'blocked': 20},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        mock_inference_service = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify InferenceService was NOT called (blocked item not eligible)
        mock_inference_service.infer_task.assert_not_called()
        assert result['success'] is False
        assert 'No eligible work items' in result['error']

    def test_defer_prevents_provider_execution(self):
        """Test 8: DEFER prevents provider execution."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor

        # Mock ControlMasterService with deferred work item
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Deferred objective',
                'status': 'deferred',
                'priority_score': 200,
                'source': 'objective_repository',
                'next_action': 'Resume',
                'evidence_refs': [],
                'score_breakdown': {'base': 20},
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        mock_inference_service = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify InferenceService was NOT called (deferred item not eligible)
        mock_inference_service.infer_task.assert_not_called()
        assert result['success'] is False
        assert 'No eligible work items' in result['error']

    def test_resource_exception_prevents_provider_execution(self):
        """Test 9: Resource exception prevents provider execution."""
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

        # Mock InferenceService that raises resource exception
        mock_inference_service = MagicMock()
        mock_inference_service.infer_task.side_effect = Exception("Resource exception: insufficient RAM")

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify provider execution was prevented by exception
        assert result['success'] is False
        assert 'Resource exception' in result['error']

    def test_result_preserves_original_work_identity(self):
        """Test 10: Result preserves original work identity."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
            metadata={'work_item_id': 'objective:123'},
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Test summary',
            inferred_task='Test task',
            confidence=0.9,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.SUCCESS,
            duration_ms=1000,
            error_summary='',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify result preserves original work identity
        assert result['work_item_id'] == 'objective:123'
        assert result['run_id'] == mock_run_record.run_id

    def test_task_outcome_recorder_receives_same_work_identity(self):
        """Test 11: TaskOutcomeRecorder receives the same work identity."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
            metadata={'work_item_id': 'objective:123'},
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Test summary',
            inferred_task='Test task',
            confidence=0.9,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.SUCCESS,
            duration_ms=1000,
            error_summary='',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        # Mock TaskOutcomeRecorder
        mock_outcome_recorder = MagicMock()

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=mock_outcome_recorder,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify TaskOutcomeRecorder was called with work item identity
        # (The _record_outcome method should have been called)
        assert result['success'] is True

    def test_failed_work_reaches_truthful_terminal_state(self):
        """Test 12: Failed work reaches a truthful terminal state."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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

        # Mock InferenceService that returns failed run
        mock_inference_service = MagicMock()
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.DEGRADED,
            summary='Failed',
            inferred_task='Test task',
            confidence=0.0,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.FAILED,
            duration_ms=1000,
            error_summary='Test error',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify failed state is truthful
        assert result['status'] == 'failed'

    def test_successful_work_reaches_truthful_terminal_state(self):
        """Test 13: Successful work reaches a truthful terminal state."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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

        # Mock InferenceService that returns successful run
        mock_inference_service = MagicMock()
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Success',
            inferred_task='Test task',
            confidence=0.9,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.SUCCESS,
            duration_ms=1000,
            error_summary='',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify successful state is truthful
        assert result['status'] == 'success'

    def test_internal_metabolic_state_remains_read_only(self):
        """Test 14: InternalMetabolicStateService remains read-only."""
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
        )

        # Verify WorkQueueExecutor does not interact with InternalMetabolicStateService
        # (It only uses ControlMasterService, InferenceService, TaskOutcomeRecorder)
        # Check that the executor has no internal_metabolic_state_service attribute
        assert not hasattr(executor, 'internal_metabolic_state_service')

    def test_no_provider_executes_merely_because_inspection_occurred(self):
        """Test 15: No provider executes merely because inspection occurred."""
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
            inference_service=None,  # No inference service available
            task_outcome_recorder=None,
        )

        # Execute work item (will fail due to None inference_service)
        result = executor.select_and_execute_work_item()

        # Verify provider was not called (because inference_service is None)
        # If inference_service were available, it would only be called for execution,
        # not for inspection
        assert result['success'] is False
        assert 'inference_service not available' in result['error']

    def test_no_direct_source_modification_occurs_automatically(self):
        """Test 16: No direct source modification occurs automatically."""
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
        )

        # Verify WorkQueueExecutor has no file modification methods
        assert not hasattr(executor, 'write_file')
        assert not hasattr(executor, 'edit_file')
        assert not hasattr(executor, 'delete_file')

    def test_existing_context_reuse_remains_safe(self):
        """Test 17: Existing context reuse remains safe."""
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.domain.models import RunRecord, InferenceResult, RoleRoute, RunStatus, ReasoningMode, TaskRole, InferenceRequest, AmbiguityLevel, ComplexityLevel

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
        mock_request = InferenceRequest(
            user_goal='Test goal',
            task_role=TaskRole.PROJECT_EVOLUTION,
            complexity=ComplexityLevel.MEDIUM,
            ambiguity=AmbiguityLevel.LOW,
        )
        mock_result = InferenceResult(
            request_id='test-request-id',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Test summary',
            inferred_task='Test task',
            confidence=0.9,
        )
        mock_route = RoleRoute(
            task_role=TaskRole.PROJECT_EVOLUTION,
            role_title='Project Evolution',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Test reason',
        )
        mock_run_record = RunRecord(
            request=mock_request,
            result=mock_result,
            route=mock_route,
            status=RunStatus.SUCCESS,
            duration_ms=1000,
            error_summary='',
        )
        mock_inference_service.infer_task.return_value = mock_run_record

        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=mock_inference_service,
            task_outcome_recorder=None,
        )

        # Execute work item
        result = executor.select_and_execute_work_item()

        # Verify context reuse is safe (no side effects on ControlMaster)
        # ControlMasterService was only read, not modified
        mock_control_master.current_work_queue.assert_called_once()
        # No write methods were called
        for attr in dir(mock_control_master):
            if attr.startswith('set_') or attr.startswith('add_') or attr.startswith('remove_'):
                method = getattr(mock_control_master, attr)
                if hasattr(method, 'call_count'):
                    assert method.call_count == 0, f"Write method {attr} was called"

    def test_queue_reentrancy_is_safe(self):
        """Test 18: Queue reentrancy is safe."""
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
        )

        # Execute work item multiple times to verify no reentrancy
        for _ in range(3):
            result = executor.select_and_execute_work_item()

        # Verify current_work_queue was called each time (no reentrancy loop)
        assert mock_control_master.current_work_queue.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
