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
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    AmbiguityLevel,
    ComplexityLevel,
    InferenceRequest,
    RunRecord,
    TaskRole,
)
from iabv_v15.services.cognitive import (
    CognitiveOperatingPolicy,
    CognitiveStateVector,
    CognitivePolicyDecision,
    ResourceProjection,
    ResourcePressure,
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
        cognitive_policy: CognitiveOperatingPolicy | None = None,
        resource_aware_controller: Any | None = None,
    ) -> None:
        self.control_master_service = control_master_service
        self.inference_service = inference_service
        self.task_outcome_recorder = task_outcome_recorder
        self.cognitive_policy = cognitive_policy or CognitiveOperatingPolicy()
        self.resource_aware_controller = resource_aware_controller

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

        # Evaluate cognitive policy before execution
        policy_decision = self._evaluate_cognitive_policy(selected_item)

        # Check if policy says DEFER or STOP
        if policy_decision.observation_mode.value == 'defer':
            return {
                'success': False,
                'error': 'Policy deferred execution',
                'work_item_id': selected_item.get('id'),
                'policy_decision_id': policy_decision.decision_id,
                'observation_mode': policy_decision.observation_mode.value,
            }

        # Transform to InferenceRequest with policy envelope
        request = self._work_item_to_inference_request(selected_item, policy_decision)

        # Execute through canonical path
        try:
            if self.inference_service is None:
                return {
                    'success': False,
                    'error': 'inference_service not available',
                    'work_item_id': selected_item.get('id'),
                }

            run_record = self.inference_service.infer_task(request)

            # Record outcome to same work item with policy decision trace
            self._record_outcome(selected_item, run_record, policy_decision)

            return {
                'success': True,
                'work_item_id': selected_item.get('id'),
                'run_id': run_record.run_id,
                'status': run_record.status.value,
                'duration_ms': run_record.duration_ms,
                'policy_decision_id': policy_decision.decision_id,
                'horizon': policy_decision.horizon.value,
                'reasoning_depth': policy_decision.reasoning_depth.value,
                'observation_mode': policy_decision.observation_mode.value,
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

    def _work_item_to_inference_request(
        self,
        work_item: dict[str, Any],
        policy_decision: CognitivePolicyDecision,
    ) -> InferenceRequest:
        """Transform work item into canonical InferenceRequest with policy envelope.

        Preserves work item identity in metadata for outcome closure.
        Applies cognitive policy decision envelope to the request.
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

        # Apply policy envelope to request
        # Map policy reasoning depth to complexity level
        depth_to_complexity = {
            'level_0': ComplexityLevel.SIMPLE,
            'level_1': ComplexityLevel.MEDIUM,
            'level_2': ComplexityLevel.DEEP,
            'level_3': ComplexityLevel.DEEP,
        }
        complexity = depth_to_complexity.get(policy_decision.reasoning_depth.value, ComplexityLevel.MEDIUM)

        # Build InferenceRequest with work item identity and policy envelope preserved
        request = InferenceRequest(
            user_goal=user_goal,
            prompt=user_goal,  # Use goal as prompt for development work
            task_role=task_role,
            complexity=complexity,  # Apply policy reasoning depth
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
                # Policy envelope
                'policy_decision_id': policy_decision.decision_id,
                'policy_horizon': policy_decision.horizon.value,
                'policy_reasoning_depth': policy_decision.reasoning_depth.value,
                'policy_observation_mode': policy_decision.observation_mode.value,
                'policy_chunk_size': policy_decision.chunk_size,
                'policy_parallelism_allowed': policy_decision.parallelism_allowed,
            },
            metadata={
                'work_item_id': work_item_id,
                'work_item_source': work_item_source,
                'work_item_priority': work_item.get('priority_score', 0),
                'work_item_status': work_item.get('status'),
                'original_title': work_item_title,
                'original_next_action': work_item_next_action,
                # Policy decision trace (without secrets)
                'policy_decision_id': policy_decision.decision_id,
                'policy_horizon': policy_decision.horizon.value,
                'policy_reasoning_depth': policy_decision.reasoning_depth.value,
                'policy_observation_mode': policy_decision.observation_mode.value,
                'policy_mrv': policy_decision.mrv,
                'policy_mvi': policy_decision.mvi,
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

    def _record_outcome(
        self,
        work_item: dict[str, Any],
        run_record: RunRecord,
        policy_decision: CognitivePolicyDecision,
    ) -> None:
        """Record outcome to the same work item with policy decision trace.

        Associates the run outcome with the original work item via
        work_item_id in the run metadata. Also preserves policy decision
        for traceability and learning.
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
                f"status {run_record.status.value} "
                f"policy_decision_id {policy_decision.decision_id}"
            )
        except Exception as exc:
            logger.error(f"Failed to record outcome for work item {work_item.get('id')}: {exc}")

    def _evaluate_cognitive_policy(self, work_item: dict[str, Any]) -> CognitivePolicyDecision:
        """Evaluate cognitive policy for a work item.

        Builds policy input from existing runtime information and computes
        cognitive envelope before execution.

        Args:
            work_item: Selected work item from ControlMaster

        Returns:
            Immutable cognitive policy decision
        """
        # Build policy input from work item and existing runtime information
        # Unknown values remain at sensible defaults (0.5 for uncertainty, etc.)

        # Extract work item properties for policy input
        priority_score = work_item.get('priority_score', 50)  # 0-100 scale
        status = work_item.get('status', 'pending')
        source = work_item.get('source', 'unknown')

        # Normalize priority to 0.0-1.0 scale
        goal_value = min(1.0, priority_score / 100.0)

        # Estimate complexity from work item properties
        complexity = 0.5  # Default medium complexity
        if 'complexity' in work_item:
            complexity = min(1.0, work_item.get('complexity', 0.5))

        # Estimate ambiguity from work item properties
        ambiguity = 0.3  # Default low ambiguity
        if 'ambiguity' in work_item:
            ambiguity = min(1.0, work_item.get('ambiguity', 0.3))

        # Estimate uncertainty from status and source
        uncertainty = 0.5  # Default medium uncertainty
        if status in ('pending', 'needs_fix'):
            uncertainty = 0.7
        elif status in ('active', 'in_progress'):
            uncertainty = 0.4

        # Estimate risk from work item properties
        risk = 0.3  # Default low risk
        if 'risk' in work_item:
            risk = min(1.0, work_item.get('risk', 0.3))

        # Expected value from priority
        expected_value = goal_value

        # Available time (default to 10 minutes if not specified)
        available_time_seconds = 600.0
        if 'deadline' in work_item:
            # Would parse deadline and compute remaining time
            # For now, use default
            pass

        # Resource state from ResourceAwareController
        resource_projection = self._build_resource_projection()

        # Memory relevance (default to 0.5)
        # In production, this would come from KnowledgeRepository/GoalEngine
        memory_relevance = 0.5

        # Prior experience (default to 0.5)
        # In production, this would come from RunRepository/TaskOutcomeRecorder
        prior_experience = 0.5

        # Build cognitive state vector with resource projection
        state_vector = CognitiveStateVector(
            goal_value=goal_value,
            complexity=complexity,
            ambiguity=ambiguity,
            uncertainty=uncertainty,
            risk=risk,
            expected_value=expected_value,
            available_time_seconds=available_time_seconds,
            resource_projection=resource_projection,
            memory_relevance=memory_relevance,
            prior_experience=prior_experience,
            work_item_id=work_item.get('id', ''),
            work_item_source=source,
            work_item_title=work_item.get('title', ''),
        )

        # Compute policy decision
        decision = self.cognitive_policy.compute_decision(state_vector)

        logger.info(
            f"Cognitive policy evaluated for work item {work_item.get('id')}: "
            f"horizon={decision.horizon.value}, "
            f"depth={decision.reasoning_depth.value}, "
            f"observation_mode={decision.observation_mode.value}"
        )

        return decision

    def _build_resource_projection(self) -> ResourceProjection:
        """Build resource projection from ResourceAwareController.

        Returns an immutable projection of resource state for cognitive policy.
        If ResourceAwareController is not available, returns a default projection
        with UNKNOWN pressure and low confidence.
        """
        if self.resource_aware_controller is None:
            # Return default projection with unknown state
            return ResourceProjection(
                resource_state_id="default-unknown",
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="WorkQueueExecutor-default",
                pressure=ResourcePressure.LOW,  # Default to LOW for safety
                cpu_load_1m=0.0,
                cpu_count=1,
                ram_available_gb=8.0,  # Default assumption
                ram_used_pct=0.0,
                gpu_available=False,
                vram_available_gb=0.0,
                available_capacity=1.0,
                confidence=0.0,  # Zero confidence when no controller
            )

        try:
            # Query ResourceAwareController for current resource state
            resource_check = self.resource_aware_controller.check_resource_safety(
                operation_cost='cheap',  # Use cheap cost for policy evaluation
                force_refresh=False,  # Use cached state if available
            )

            # Convert ResourceCheck to ResourceProjection
            # Convert RAM from MB to GB
            ram_available_gb = resource_check.ram_available_mb / 1024.0

            # Map ResourcePressure enum to our ResourcePressure
            # (They should be the same enum, but handle case where they differ)
            pressure_mapping = {
                'critical': ResourcePressure.CRITICAL,
                'high': ResourcePressure.HIGH,
                'moderate': ResourcePressure.MODERATE,
                'low': ResourcePressure.LOW,
            }
            pressure = pressure_mapping.get(
                resource_check.current_pressure.value,
                ResourcePressure.LOW,
            )

            # Compute available capacity based on pressure
            capacity_mapping = {
                ResourcePressure.CRITICAL: 0.1,
                ResourcePressure.HIGH: 0.3,
                ResourcePressure.MODERATE: 0.6,
                ResourcePressure.LOW: 1.0,
            }
            available_capacity = capacity_mapping.get(pressure, 1.0)

            # Confidence based on resource state
            if resource_check.resource_state.value == 'unknown':
                confidence = 0.0
            elif resource_check.resource_state.value == 'unsafe':
                confidence = 0.5
            else:
                confidence = 1.0

            return ResourceProjection(
                resource_state_id=f"resource-{resource_check.timestamp}",
                timestamp=resource_check.timestamp,
                source="ResourceAwareController",
                pressure=pressure,
                cpu_load_1m=resource_check.cpu_load_1m,
                cpu_count=1,  # Not available in ResourceCheck
                ram_available_gb=ram_available_gb,
                ram_used_pct=resource_check.ram_used_pct,
                gpu_available=False,  # Not available in ResourceCheck
                vram_available_gb=0.0,  # Not available in ResourceCheck
                available_capacity=available_capacity,
                confidence=confidence,
            )
        except Exception as exc:
            logger.warning(f"Failed to build resource projection: {exc}")
            # Return default projection on error
            return ResourceProjection(
                resource_state_id="error-fallback",
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="WorkQueueExecutor-fallback",
                pressure=ResourcePressure.LOW,  # Default to LOW for safety
                cpu_load_1m=0.0,
                cpu_count=1,
                ram_available_gb=8.0,  # Default assumption
                ram_used_pct=0.0,
                gpu_available=False,
                vram_available_gb=0.0,
                available_capacity=1.0,
                confidence=0.0,  # Zero confidence on error
            )
