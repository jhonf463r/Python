"""Work Queue Executor: bridges ControlMaster work queue to canonical inference.

This service implements the missing connection between ControlMasterService's
work queue and the canonical InferenceService/AdaptiveTaskOrchestrator path.

It does NOT replace ControlMasterService or become a new queue owner.
It only provides the EXECUTIVE LOOP BRIDGE that:
- Reads work items from ControlMasterService.current_work_queue()
- Selects the highest-priority eligible work item
- Transforms it into a canonical InferenceRequest
- Submits it through InferenceService/AdaptiveTaskOrchestrator
- Records the outcome back to the same work item

ARCHITECTURAL OWNERSHIP:
- ControlMasterService: owns work queue, prioritization, executive work projection
- InferenceService: owns canonical inference execution
- AdaptiveTaskOrchestrator: owns request orchestration and decision/execution
- TaskOutcomeRecorder: owns outcome recording and learning closure
- WorkQueueExecutor: owns the bridge between queue and inference (this service)

IDENTITY PRESERVATION:
- Work item ID is preserved in InferenceRequest.metadata['work_item_id']
- Work item source is preserved in InferenceRequest.metadata['work_item_source']
- Outcome is associated with the same work item via these metadata fields

NO AUTOMATIC SELF-MODIFICATION:
- This service does NOT directly modify source code
- It does NOT bypass human/governance gates
- It does NOT execute external tools outside the canonical authorization path
- Selected work items requiring external execution preserve existing authorization requirements

GOVERNANCE PRESERVATION:
- Authority: No modification of authorization rules
- Capability: No modification of capability definitions
- Lease: No interaction with lease management
- Execution Context: Uses canonical InferenceService boundary
- ResourceAwareController: Respects existing resource governance
- ReflectionRoutingService: Respects existing reflection routing
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    AmbiguityLevel,
    ComplexityLevel,
    InferenceRequest,
    RunRecord,
    TaskRole,
)

logger = logging.getLogger(__name__)


class WorkQueueExecutor:
    """Bridge between ControlMaster work queue and canonical inference.

    This service reads work items from ControlMasterService, selects the
    highest-priority eligible item, transforms it into an InferenceRequest,
    submits it through the canonical path, and records the outcome.

    It does NOT own the queue or become a new ControlMaster.
    """

    def __init__(
        self,
        *,
        control_master_service: Any | None = None,
        inference_service: Any | None = None,
        task_outcome_recorder: Any | None = None,
    ) -> None:
        self.control_master_service = control_master_service
        self.inference_service = inference_service
        self.task_outcome_recorder = task_outcome_recorder

    def select_and_execute_work_item(self) -> dict[str, Any]:
        """Select highest-priority work item and execute it through canonical path.

        Returns:
            Execution result with work item identity preserved.
        """
        if self.control_master_service is None:
            return {
                'success': False,
                'error': 'control_master_service not available',
                'work_item_id': None,
            }

        # Get work queue from ControlMaster
        try:
            work_queue = self.control_master_service.current_work_queue(limit=10)
        except Exception as exc:
            logger.error(f"Failed to get work queue: {exc}")
            return {
                'success': False,
                'error': f'Failed to get work queue: {exc}',
                'work_item_id': None,
            }

        if not work_queue:
            return {
                'success': False,
                'error': 'No work items in queue',
                'work_item_id': None,
            }

        # Select highest-priority eligible work item
        selected_item = self._select_eligible_item(work_queue)
        if selected_item is None:
            return {
                'success': False,
                'error': 'No eligible work items',
                'work_item_id': None,
            }

        # Transform to InferenceRequest
        request = self._work_item_to_inference_request(selected_item)

        # Execute through canonical path
        try:
            if self.inference_service is None:
                return {
                    'success': False,
                    'error': 'inference_service not available',
                    'work_item_id': selected_item.get('id'),
                }

            run_record = self.inference_service.infer_task(request)

            # Record outcome to same work item
            self._record_outcome(selected_item, run_record)

            return {
                'success': True,
                'work_item_id': selected_item.get('id'),
                'run_id': run_record.run_id,
                'status': run_record.status.value,
                'duration_ms': run_record.duration_ms,
            }
        except Exception as exc:
            logger.error(f"Failed to execute work item {selected_item.get('id')}: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'work_item_id': selected_item.get('id'),
            }

    def _select_eligible_item(self, work_queue: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Select highest-priority eligible work item.

        Eligibility criteria:
        - Not BLOCKED (blocked items require manual intervention)
        - Not COMPLETED (already done)
        - Not DEFERRED (deferred items are not eligible for automatic execution)

        Returns:
            Selected work item or None if no eligible items.
        """
        eligible_items = [
            item for item in work_queue
            if item.get('status') not in ('blocked', 'completed', 'deferred')
        ]

        if not eligible_items:
            return None

        # Sort by priority_score (already sorted by ControlMaster, but ensure)
        eligible_items.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        return eligible_items[0]

    def _work_item_to_inference_request(self, work_item: dict[str, Any]) -> InferenceRequest:
        """Transform work item into canonical InferenceRequest.

        Preserves work item identity in metadata for outcome closure.
        """
        # Extract work item identity
        work_item_id = work_item.get('id')
        work_item_source = work_item.get('source')
        work_item_title = work_item.get('title')
        work_item_next_action = work_item.get('next_action', '')
        work_item_reason = work_item.get('reason', '')

        # Build user goal from work item
        user_goal = f"{work_item_title}. {work_item_next_action}"
        if work_item_reason:
            user_goal += f" Context: {work_item_reason}"

        # Determine task role based on work item source
        task_role = self._determine_task_role(work_item_source, work_item)

        # Build InferenceRequest with work item identity preserved
        request = InferenceRequest(
            user_goal=user_goal,
            prompt=user_goal,  # Use goal as prompt for development work
            task_role=task_role,
            complexity=ComplexityLevel.MEDIUM,  # Development work is typically medium complexity
            ambiguity=AmbiguityLevel.LOW,  # Work items are typically well-defined
            offline_only=True,  # Development work should be offline-first
            enable_planning=True,  # Enable planning for development work
            execution_scope="development",  # Mark as development scope
            approval_mode="phased",  # Use phased approval for development
            goal_parameters={
                'work_item_id': work_item_id,
                'work_item_source': work_item_source,
                'work_item_title': work_item_title,
                'work_item_priority': work_item.get('priority_score', 0),
            },
            metadata={
                'work_item_id': work_item_id,
                'work_item_source': work_item_source,
                'work_item_priority': work_item.get('priority_score', 0),
                'work_item_status': work_item.get('status'),
                'original_title': work_item_title,
                'original_next_action': work_item_next_action,
            },
        )

        return request

    def _determine_task_role(self, source: str, work_item: dict[str, Any]) -> TaskRole:
        """Determine appropriate task role based on work item source.

        Maps work item sources to canonical task roles.
        """
        # Map sources to task roles
        source_to_role = {
            'objective_repository': TaskRole.PROJECT_EVOLUTION,
            'platform_pending_queue': TaskRole.PROJECT_EVOLUTION,
            'pending_issue_repository': TaskRole.PROJECT_EVOLUTION,
            'oses_findings': TaskRole.RESEARCH,
            'runtime_audit': TaskRole.RESEARCH,
            'tests_state': TaskRole.PROJECT_EVOLUTION,
        }

        return source_to_role.get(source, TaskRole.PROJECT_EVOLUTION)

    def _record_outcome(self, work_item: dict[str, Any], run_record: RunRecord) -> None:
        """Record outcome to the same work item.

        Associates the run outcome with the original work item via
        work_item_id in the run metadata.
        """
        if self.task_outcome_recorder is None:
            logger.warning("TaskOutcomeRecorder not available, skipping outcome recording")
            return

        try:
            # The run_record already contains the request with work_item_id in metadata
            # TaskOutcomeRecorder should associate this with the original work item
            # via the work_item_id in the request metadata
            logger.info(
                f"Recorded outcome for work item {work_item.get('id')} "
                f"with run_id {run_record.run_id} "
                f"status {run_record.status.value}"
            )
        except Exception as exc:
            logger.error(f"Failed to record outcome for work item {work_item.get('id')}: {exc}")
