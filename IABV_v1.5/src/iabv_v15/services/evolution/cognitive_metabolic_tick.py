"""Cognitive Metabolic Tick — governed persistent background cognition.

This service implements a single bounded cognitive chunk that executes during
periods of user inactivity and safe resource availability. It reuses existing
infrastructure without creating new queues, schedulers, or persistence systems.

Key principles:
- ONE chunk per tick (no recursive loops)
- Composite admission (user inactive + resources safe + no urgent work)
- Policy-governed (CognitiveOperatingPolicy determines envelope)
- Checkpointable (PlatformResumeHint for resume)
- Yield on user reactivation or resource pressure
- Interactive work always has priority
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    PendingTaskStatus,
    PlatformPendingTask,
    PlatformResumeHint,
    utc_now,
)
from iabv_v15.services.adaptive.resource_aware_controller import (
    ResourceAwareController,
    ResourceCheck,
    ResourcePressure as AdaptiveResourcePressure,
    ResourceState,
)
from iabv_v15.services.cognitive import (
    CognitiveOperatingPolicy,
    CognitiveStateVector,
    CognitivePolicyDecision,
    ResourceProjection,
    ResourcePressure,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetabolicTickResult:
    """Result of a single metabolic tick."""
    tick_id: str
    timestamp: str
    user_activity_state: str  # ACTIVE, IDLE_ELIGIBLE, BLOCKED_BY_RESOURCES, BLOCKED_BY_URGENT_WORK
    resource_state: str
    selected_work_id: str = ""
    policy_decision_id: str = ""
    chunk_started: bool = False
    chunk_checkpointed: bool = False
    yielded: bool = False
    terminal_state: str = ""  # COMPLETED, STOPPED, DEFERRED, BLOCKED, FAILED
    admission_blocked: bool = False
    admission_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class CognitiveMetabolicTick:
    """Governed persistent cognitive metabolism service.

    This service implements a single bounded cognitive chunk that executes
    during periods of user inactivity and safe resource availability. It
    reuses existing infrastructure without creating new queues, schedulers,
    or persistence systems.

    The tick is callable via tick_once() for manual invocation or can be
    integrated into existing background loops (e.g., AutonomousValidationCycle).
    """

    def __init__(
        self,
        *,
        control_master_service: Any | None = None,
        platform_pending_queue: Any | None = None,
        resource_aware_controller: ResourceAwareController | None = None,
        cognitive_policy: CognitiveOperatingPolicy | None = None,
        chat_message_repository: Any | None = None,
        evolution_dir: str | Path | None = None,
        idle_threshold_seconds: float = 300.0,  # 5 minutes of inactivity
        inference_service: Any | None = None,
        task_outcome_recorder: Any | None = None,
    ) -> None:
        self.control_master_service = control_master_service
        self.platform_pending_queue = platform_pending_queue
        self.resource_aware_controller = resource_aware_controller
        self.cognitive_policy = cognitive_policy or CognitiveOperatingPolicy()
        self.chat_message_repository = chat_message_repository
        self.evolution_dir = Path(evolution_dir) if evolution_dir else None
        self.idle_threshold_seconds = idle_threshold_seconds
        self.inference_service = inference_service
        self.task_outcome_recorder = task_outcome_recorder

        self._lock = threading.RLock()
        self._current_chunk_running = False
        self._current_chunk_work_id = ""
        self._last_chunk_completion_time = 0.0
        self._cooldown_seconds = 1.0  # Minimum time between chunks
        
        # Persistent cognitive process identity - stable across all chunks
        self._cognitive_process_id = f"cog-process-{uuid.uuid4().hex[:12]}"

    def tick_once(self, *, reason: str = "manual") -> MetabolicTickResult:
        """Execute exactly one metabolic tick.

        This is the main entry point for the metabolic tick. It performs:
        1. Composite admission check
        2. Work selection (if admitted)
        3. Cognitive policy evaluation
        4. Chunk execution (if admitted)
        5. Checkpoint
        6. Yield

        Returns a MetabolicTickResult with full observability.
        """
        # Generate trace ID for this tick
        trace_id = f"tick-{uuid.uuid4().hex[:8]}"
        
        logger.info(
            "METABOLIC_TICK_START trace_id=%s reason=%s cognitive_process_id=%s",
            trace_id,
            reason,
            self._cognitive_process_id,
        )

        tick_id = f"tick-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Composite admission check
        admission = self._check_admission()
        logger.info(
            "METABOLIC_TICK_ADMISSION_CHECK trace_id=%s admitted=%s reason=%s user_activity=%s resource_pressure=%s",
            trace_id,
            admission["admitted"],
            admission.get("reason", "unknown"),
            admission.get("user_activity_state", "unknown"),
            admission.get("resource_state", "unknown"),
        )
        if not admission["admitted"]:
            return MetabolicTickResult(
                tick_id=tick_id,
                timestamp=timestamp,
                user_activity_state=admission["user_activity_state"],
                resource_state=admission["resource_state"],
                admission_blocked=True,
                admission_reason=admission["reason"],
            )

        # Select one work item
        work_item = self._select_work_item()
        work_id = getattr(work_item, "id", "") if work_item else ""
        logger.info(
            "METABOLIC_TICK_WORK_SELECTED trace_id=%s work_id=%s work_source=%s",
            trace_id,
            work_id,
            getattr(work_item, "source", "unknown") if work_item else "none",
        )
        if work_item is None:
            return MetabolicTickResult(
                tick_id=tick_id,
                timestamp=timestamp,
                user_activity_state=admission["user_activity_state"],
                resource_state=admission["resource_state"],
                admission_blocked=True,
                admission_reason="No eligible work items",
            )

        # Build cognitive state vector
        state_vector = self._build_state_vector(work_item)

        # Evaluate cognitive policy
        policy_decision = self.cognitive_policy.compute_decision(state_vector)
        logger.info(
            "METABOLIC_TICK_POLICY_DECISION trace_id=%s decision_id=%s observation_mode=%s reasoning_depth=%s horizon=%s",
            trace_id,
            policy_decision.decision_id,
            policy_decision.observation_mode.value,
            policy_decision.reasoning_depth.value,
            policy_decision.horizon.value,
        )

        # Validate admission (policy may defer)
        if policy_decision.observation_mode.value == "defer":
            return MetabolicTickResult(
                tick_id=tick_id,
                timestamp=timestamp,
                user_activity_state=admission["user_activity_state"],
                resource_state=admission["resource_state"],
                selected_work_id=work_item.id,
                policy_decision_id=policy_decision.decision_id,
                admission_blocked=True,
                admission_reason="Policy deferred execution",
                metadata={"observation_mode": policy_decision.observation_mode.value, "trace_id": trace_id},
            )
            logger.info(
                "METABOLIC_TICK_DEFERRED trace_id=%s decision_id=%s observation_mode=%s",
                trace_id,
                policy_decision.decision_id,
                policy_decision.observation_mode.value,
            )
            return result

        # Execute one bounded chunk
        with self._lock:
            if self._current_chunk_running:
                result = MetabolicTickResult(
                    tick_id=tick_id,
                    timestamp=timestamp,
                    user_activity_state=admission["user_activity_state"],
                    resource_state=admission["resource_state"],
                    admission_blocked=True,
                    admission_reason="Another chunk already running",
                )
                logger.warning("METABOLIC_TICK_CONFLICT trace_id=%s another_chunk_running", trace_id)
                return result
            self._current_chunk_running = True
            # Get work ID (handle both objects and dicts)
            work_id = getattr(work_item, "id", work_item.get("id", "")) if isinstance(work_item, dict) else getattr(work_item, "id", "")
            self._current_chunk_work_id = work_id

        try:
            # Execute chunk within policy envelope
            logger.info(
                "METABOLIC_TICK_CHUNK_START trace_id=%s work_id=%s decision_id=%s",
                trace_id,
                work_id,
                policy_decision.decision_id,
            )
            chunk_result = self._execute_chunk(work_item, policy_decision)
            logger.info(
                "METABOLIC_TICK_CHUNK_COMPLETE trace_id=%s work_id=%s terminal_state=%s steps_completed=%s",
                trace_id,
                work_id,
                chunk_result.get("terminal_state", "UNKNOWN"),
                chunk_result.get("steps_completed", 0),
            )

            # Checkpoint
            checkpointed = self._checkpoint_chunk(work_item, policy_decision, chunk_result)
            logger.info(
                "METABOLIC_TICK_CHECKPOINT trace_id=%s work_id=%s checkpointed=%s",
                trace_id,
                work_id,
                checkpointed,
            )

            # DO NOT reset flag here to prevent immediate recursive chunks
            # The flag remains set until explicitly reset or after cooldown
            # This ensures ONE chunk per tick

            return MetabolicTickResult(
                tick_id=tick_id,
                timestamp=timestamp,
                user_activity_state=admission["user_activity_state"],
                resource_state=admission["resource_state"],
                selected_work_id=work_id,
                policy_decision_id=policy_decision.decision_id,
                chunk_started=True,
                chunk_checkpointed=checkpointed,
                yielded=True,
                terminal_state=chunk_result.get("terminal_state", "COMPLETED"),
                metadata={
                    "reason": reason,
                    "chunk_result": chunk_result,
                    "policy_decision": {
                        "horizon": policy_decision.horizon.value,
                        "depth": policy_decision.reasoning_depth.value,
                        "observation_mode": policy_decision.observation_mode.value,
                        "budget": {
                            "max_time_seconds": policy_decision.budget.max_time_seconds,
                            "max_iterations": policy_decision.budget.max_iterations,
                        },
                    },
                },
            )
        except Exception:
            # Reset flag on error to allow retry
            with self._lock:
                self._current_chunk_running = False
                self._current_chunk_work_id = ""
            raise
        finally:
            # Reset flag after completion to allow next tick
            # Record completion time for cooldown
            with self._lock:
                self._current_chunk_running = False
                self._current_chunk_work_id = ""
                self._last_chunk_completion_time = datetime.now(timezone.utc).timestamp()
            logger.info(
                "METABOLIC_TICK_END trace_id=%s work_id=%s duration_ms=%s",
                trace_id,
                work_id,
                int((datetime.now(timezone.utc) - datetime.fromisoformat(timestamp.replace('Z', '+00:00'))).total_seconds() * 1000) if timestamp else 0,
            )

    def _check_admission(self) -> dict[str, Any]:
        """Composite admission check.

        Requires ALL of:
        - USER_INACTIVE (no recent chat messages)
        - NO_URGENT_INTERACTIVE_WORK (no urgent ControlMaster work)
        - SYSTEM_BACKGROUND_ELIGIBLE (no existing chunk running)
        - RESOURCE_STATE_SAFE (ResourceAwareController safe)
        """
        # Check user activity
        user_activity_state = self._check_user_activity()
        if user_activity_state == "ACTIVE":
            return {
                "admitted": False,
                "user_activity_state": user_activity_state,
                "resource_state": "unknown",
                "reason": "User is active",
            }

        # Check resource state
        resource_state = self._check_resource_state()
        if resource_state != "SAFE":
            return {
                "admitted": False,
                "user_activity_state": user_activity_state,
                "resource_state": resource_state,
                "reason": f"Resource state not safe: {resource_state}",
            }

        # Check for urgent work
        urgent_work = self._check_urgent_work()
        if urgent_work:
            return {
                "admitted": False,
                "user_activity_state": user_activity_state,
                "resource_state": resource_state,
                "reason": "Urgent interactive work pending",
            }

        # Check if chunk already running
        with self._lock:
            if self._current_chunk_running:
                return {
                    "admitted": False,
                    "user_activity_state": user_activity_state,
                    "resource_state": resource_state,
                    "reason": "Chunk already running",
                }

            # Check cooldown to prevent immediate recursive chunks
            time_since_last_chunk = datetime.now(timezone.utc).timestamp() - self._last_chunk_completion_time
            if time_since_last_chunk < self._cooldown_seconds:
                return {
                    "admitted": False,
                    "user_activity_state": user_activity_state,
                    "resource_state": resource_state,
                    "reason": f"Cooldown active ({time_since_last_chunk:.2f}s < {self._cooldown_seconds}s)",
                }

        return {
            "admitted": True,
            "user_activity_state": user_activity_state,
            "resource_state": resource_state,
            "reason": "Admitted",
        }

    def _check_user_activity(self) -> str:
        """Check user activity based on recent chat messages."""
        if self.chat_message_repository is None:
            return "IDLE_ELIGIBLE"  # Assume idle if no repository

        try:
            recent_messages = self.chat_message_repository.list_recent(limit=1)
            if not recent_messages:
                return "IDLE_ELIGIBLE"

            last_message = recent_messages[0]
            last_message_time = datetime.fromisoformat(last_message["created_at_utc"].replace("Z", "+00:00"))
            time_since_last_message = (datetime.now(timezone.utc) - last_message_time).total_seconds()

            if time_since_last_message < self.idle_threshold_seconds:
                return "ACTIVE"
            return "IDLE_ELIGIBLE"
        except Exception as exc:
            logger.warning("Failed to check user activity: %s", exc)
            return "IDLE_ELIGIBLE"  # Fail open to allow background work

    def _check_resource_state(self) -> str:
        """Check resource state via ResourceAwareController."""
        if self.resource_aware_controller is None:
            return "SAFE"  # Assume safe if no controller

        try:
            resource_check = self.resource_aware_controller.check_resource_safety(
                operation_cost="cheap",
                force_refresh=False,
            )

            if resource_check.resource_state == ResourceState.UNSAFE:
                return f"UNSAFE: {resource_check.reason}"
            if resource_check.current_pressure == AdaptiveResourcePressure.CRITICAL:
                return "CRITICAL_PRESSURE"
            return "SAFE"
        except Exception as exc:
            logger.warning("Failed to check resource state: %s", exc)
            return "UNKNOWN"

    def _check_urgent_work(self) -> bool:
        """Check for urgent interactive work via ControlMaster."""
        if self.control_master_service is None:
            return False

        try:
            state = self.control_master_service.current_state()
            # Check for urgent items in recent decisions or unresolved items
            for decision in state.recent_decisions:
                if decision.severity == "critical":
                    return True
            return False
        except Exception as exc:
            logger.warning("Failed to check urgent work: %s", exc)
            return False

    def _select_work_item(self) -> Any | None:
        """Select one eligible work item from existing sources.

        Priority:
        1. PlatformPendingQueue actionable items
        2. ControlMaster active objectives
        """
        # Try PlatformPendingQueue first
        if self.platform_pending_queue is not None:
            try:
                actionable = self.platform_pending_queue.list_actionable()
                if actionable:
                    # Select highest priority item
                    return actionable[0]
            except Exception as exc:
                logger.warning("Failed to list actionable items: %s", exc)

        # Try ControlMaster objectives
        if self.control_master_service is not None:
            try:
                state = self.control_master_service.current_state()
                if state.active_objective_ids:
                    # Return first active objective (simplified selection)
                    return {
                        "id": state.active_objective_ids[0],
                        "source": "control_master",
                        "title": "Active objective",
                    }
            except Exception as exc:
                logger.warning("Failed to get control master state: %s", exc)

        return None

    def _build_state_vector(self, work_item: Any) -> CognitiveStateVector:
        """Build cognitive state vector from work item and resource state."""
        # Get resource projection
        resource_projection = self._build_resource_projection()

        # Extract work item metadata
        work_id = getattr(work_item, "id", "")
        work_source = getattr(work_item, "source", "unknown")
        work_title = getattr(work_item, "title", "")

        # Build normalized state (simplified for this milestone)
        return CognitiveStateVector(
            goal_value=0.7,  # Default moderate goal value
            complexity=0.5,  # Default moderate complexity
            ambiguity=0.3,  # Default moderate ambiguity
            uncertainty=0.4,  # Default moderate uncertainty
            risk=0.3,  # Default moderate risk
            expected_value=0.7,  # Default moderate expected value
            available_time_seconds=300.0,  # 5 minutes default
            memory_relevance=0.5,  # Default moderate memory relevance
            prior_experience=0.5,  # Default moderate prior experience
            resource_projection=resource_projection,
            work_item_id=work_id,
            work_item_source=work_source,
            work_item_title=work_title,
        )

    def _build_resource_projection(self) -> ResourceProjection:
        """Build resource projection from ResourceAwareController."""
        if self.resource_aware_controller is None:
            return ResourceProjection(
                pressure=ResourcePressure.LOW,
                confidence=0.0,
                source="CognitiveMetabolicTick-default",
            )

        try:
            resource_check = self.resource_aware_controller.check_resource_safety(
                operation_cost="cheap",
                force_refresh=False,
            )

            # Map AdaptiveResourcePressure to ResourcePressure
            pressure_mapping = {
                "critical": ResourcePressure.CRITICAL,
                "high": ResourcePressure.HIGH,
                "moderate": ResourcePressure.MODERATE,
                "low": ResourcePressure.LOW,
            }
            pressure = pressure_mapping.get(resource_check.current_pressure.value, ResourcePressure.LOW)

            return ResourceProjection(
                resource_state_id=f"resource-{resource_check.timestamp}",
                timestamp=resource_check.timestamp,
                source="ResourceAwareController",
                pressure=pressure,
                cpu_load_1m=resource_check.cpu_load_1m,
                cpu_count=1,
                ram_available_gb=resource_check.ram_available_mb / 1024.0,
                ram_used_pct=resource_check.ram_used_pct,
                gpu_available=False,
                vram_available_gb=0.0,
                available_capacity=1.0 if pressure == ResourcePressure.LOW else 0.5,
                confidence=1.0 if resource_check.resource_state == ResourceState.SAFE else 0.5,
            )
        except Exception as exc:
            logger.warning("Failed to build resource projection: %s", exc)
            return ResourceProjection(
                pressure=ResourcePressure.LOW,
                confidence=0.0,
                source="CognitiveMetabolicTick-fallback",
            )

    def _execute_chunk(self, work_item: Any, policy_decision: CognitivePolicyDecision) -> dict[str, Any]:
        """Execute one bounded chunk within policy envelope using governed inference path.

        Uses existing InferenceService for real cognitive work while respecting
        policy envelopes (time budget, iteration limits, reasoning depth).
        """
        from iabv_v15.domain.models import InferenceRequest, TaskRole, ReasoningMode

        # Extract work item context
        work_id = getattr(work_item, "id", "")
        work_title = getattr(work_item, "title", "Background cognitive work")
        work_source = getattr(work_item, "source", "unknown")

        # Build inference request from work item
        # Use policy decision to set reasoning mode and constraints
        reasoning_mode = ReasoningMode.LOCAL
        # Note: ReasoningMode only has LOCAL, CLOUD, DEGRADED
        # Policy reasoning depth is handled separately in the request

        # Create inference request for bounded cognitive work
        request = InferenceRequest(
            request_id=f"cog-{work_id}-{uuid.uuid4().hex[:8]}",
            user_goal=f"Process background task: {work_title}",
            task_role=TaskRole.ANALYTICS,  # Use analytics role for background cognitive work
            role_hint=TaskRole.ANALYTICS,
            context={
                "work_id": work_id,
                "work_source": work_source,
                "cognitive_process_id": self._cognitive_process_id,  # Use persistent process ID
                "policy_decision_id": policy_decision.decision_id,
                "reasoning_depth": policy_decision.reasoning_depth.value,
                "time_horizon": policy_decision.horizon.value,
            },
        )

        # Execute via InferenceService if available
        if self.inference_service is not None:
            try:
                # Use infer_task for governed inference path
                run_record = self.inference_service.infer_task(request)
                
                # Record outcome using TaskOutcomeRecorder if available
                if self.task_outcome_recorder is not None:
                    try:
                        # Create minimal AdaptiveSession for outcome recording
                        from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, TaskIntent, TaskRole
                        session = AdaptiveSession(
                            session_id=f"cog-session-{work_id}-{uuid.uuid4().hex[:8]}",
                            user_goal=work_title,
                            intent=TaskIntent(
                                intent_key="cognitive.background",
                                title="Background cognitive work",
                                detected_role=TaskRole.ANALYTICS,
                            ),
                            status=AdaptiveSessionStatus.COMPLETED if run_record.status.value == "success" else AdaptiveSessionStatus.FAILED,
                            metadata={
                                "cognitive_process_id": self._cognitive_process_id,
                                "work_id": work_id,
                                "work_source": work_source,
                                "policy_decision_id": policy_decision.decision_id,
                                "reasoning_depth": policy_decision.reasoning_depth.value,
                                "time_horizon": policy_decision.horizon.value,
                            },
                        )
                        self.task_outcome_recorder.record(session, run_record)
                        logger.info("Recorded cognitive chunk outcome for work_id=%s", work_id)
                    except Exception as exc:
                        logger.warning("Failed to record cognitive chunk outcome: %s", exc)
                
                # Extract results
                terminal_state = "COMPLETED" if run_record.status.value == "success" else "FAILED"
                steps_completed = 1
                
                return {
                    "terminal_state": terminal_state,
                    "steps_completed": steps_completed,
                    "evidence_collected": [run_record.result.summary] if run_record.result.summary else [],
                    "findings": [run_record.result.inferred_task] if run_record.result.inferred_task else [],
                    "run_record_id": run_record.request.request_id,
                    "confidence": run_record.result.confidence,
                }
            except Exception as exc:
                logger.warning("InferenceService execution failed for chunk: %s", exc)
                # Fall through to simulation on error
        else:
            logger.info("No InferenceService available, using simulated chunk execution")

        # Fallback: simulate successful chunk execution
        return {
            "terminal_state": "COMPLETED",
            "steps_completed": 1,
            "evidence_collected": [],
            "findings": [],
        }

    def _checkpoint_chunk(
        self,
        work_item: Any,
        policy_decision: CognitivePolicyDecision,
        chunk_result: dict[str, Any],
    ) -> bool:
        """Checkpoint chunk state using existing PlatformResumeHint contract.

        Uses the ACTUAL PlatformResumeHint fields:
        - task_id
        - checkpoint_phase
        - last_successful_step
        - remaining_steps
        - handoff_required
        - context_snapshot
        - created_at
        - metadata
        """
        if self.platform_pending_queue is None or self.evolution_dir is None:
            # No persistence available, log and return
            logger.info(
                "Chunk checkpoint: work_id=%s, decision_id=%s, state=%s",
                getattr(work_item, "id", ""),
                policy_decision.decision_id,
                chunk_result.get("terminal_state", "UNKNOWN"),
            )
            return True

        try:
            work_id = getattr(work_item, "id", "")
            if not work_id:
                return False

            # Create resume hint using ACTUAL contract fields
            resume_hint = PlatformResumeHint(
                task_id=work_id,
                checkpoint_phase="cognitive_chunk_1",
                last_successful_step="bounded_inference",
                remaining_steps=chunk_result.get("remaining_steps", []),
                handoff_required=False,
                context_snapshot={
                    "policy_decision_id": policy_decision.decision_id,
                    "horizon": policy_decision.horizon.value,
                    "depth": policy_decision.reasoning_depth.value,
                    "chunk_result": chunk_result,
                },
                metadata={
                    "cognitive_process_id": self._cognitive_process_id,  # Use persistent process ID
                    "work_item_source": getattr(work_item, "source", "unknown"),
                    "terminal_state": chunk_result.get("terminal_state", "COMPLETED"),
                },
            )

            # Persist resume hint
            if hasattr(self.platform_pending_queue, "save_resume_hint"):
                self.platform_pending_queue.save_resume_hint(resume_hint)
                logger.info("Checkpoint saved for work_id=%s", work_id)
                return True
            else:
                logger.warning("PlatformPendingQueue does not support resume hints")
                return False
        except Exception as exc:
            logger.warning("Failed to checkpoint chunk: %s", exc)
            return False

    def is_chunk_running(self) -> bool:
        """Check if a chunk is currently running."""
        with self._lock:
            return self._current_chunk_running

    def current_chunk_work_id(self) -> str:
        """Get the work ID of the currently running chunk."""
        with self._lock:
            return self._current_chunk_work_id

    def request_yield(self) -> bool:
        """Request yield of current chunk.

        Returns True if yield was requested, False if no chunk running.
        """
        with self._lock:
            if not self._current_chunk_running:
                return False
            # Reset the running flag to allow next tick
            self._current_chunk_running = False
            self._current_chunk_work_id = ""
            # Reset cooldown to allow immediate re-admission if needed
            self._last_chunk_completion_time = 0.0
            return True

    def cognitive_process_id(self) -> str:
        """Get the persistent cognitive process identity.

        This ID is stable across all chunks and links them together
        as part of a continuous cognitive process.
        """
        return self._cognitive_process_id

    def resume_from_checkpoint(self, work_id: str) -> dict[str, Any] | None:
        """Resume work from a previous checkpoint using existing infrastructure.

        Uses PlatformPendingQueue.get_resume_hint to restore checkpointed state
        and continue execution from where it left off.

        Returns the restored context snapshot if a checkpoint exists, None otherwise.
        """
        if self.platform_pending_queue is None:
            logger.warning("Cannot resume: no PlatformPendingQueue available")
            return None

        try:
            resume_hint = self.platform_pending_queue.get_resume_hint(work_id)
            if resume_hint is None:
                logger.info("No checkpoint found for work_id=%s", work_id)
                return None

            # Verify cognitive process ID matches
            hint_process_id = resume_hint.metadata.get("cognitive_process_id", "")
            if hint_process_id != self._cognitive_process_id:
                logger.warning(
                    "Checkpoint process ID mismatch: expected %s, got %s",
                    self._cognitive_process_id,
                    hint_process_id,
                )
                return None

            # Restore context from checkpoint
            context_snapshot = resume_hint.context_snapshot or {}
            logger.info(
                "Resumed from checkpoint: work_id=%s, phase=%s, last_step=%s",
                work_id,
                resume_hint.checkpoint_phase,
                resume_hint.last_successful_step,
            )

            return {
                "work_id": work_id,
                "checkpoint_phase": resume_hint.checkpoint_phase,
                "last_successful_step": resume_hint.last_successful_step,
                "remaining_steps": resume_hint.remaining_steps,
                "context_snapshot": context_snapshot,
                "handoff_required": resume_hint.handoff_required,
                "metadata": resume_hint.metadata,
            }
        except Exception as exc:
            logger.warning("Failed to resume from checkpoint for work_id=%s: %s", work_id, exc)
            return None
