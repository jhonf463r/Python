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
    ) -> None:
        self.control_master_service = control_master_service
        self.platform_pending_queue = platform_pending_queue
        self.resource_aware_controller = resource_aware_controller
        self.cognitive_policy = cognitive_policy or CognitiveOperatingPolicy()
        self.chat_message_repository = chat_message_repository
        self.evolution_dir = Path(evolution_dir) if evolution_dir else None
        self.idle_threshold_seconds = idle_threshold_seconds

        self._lock = threading.RLock()
        self._current_chunk_running = False
        self._current_chunk_work_id = ""
        self._last_chunk_completion_time = 0.0
        self._cooldown_seconds = 1.0  # Minimum time between chunks

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
        tick_id = f"tick-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Composite admission check
        admission = self._check_admission()
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
                metadata={"observation_mode": policy_decision.observation_mode.value},
            )

        # Execute one bounded chunk
        with self._lock:
            if self._current_chunk_running:
                return MetabolicTickResult(
                    tick_id=tick_id,
                    timestamp=timestamp,
                    user_activity_state=admission["user_activity_state"],
                    resource_state=admission["resource_state"],
                    admission_blocked=True,
                    admission_reason="Another chunk already running",
                )
            self._current_chunk_running = True
            # Get work ID (handle both objects and dicts)
            work_id = getattr(work_item, "id", work_item.get("id", "")) if isinstance(work_item, dict) else getattr(work_item, "id", "")
            self._current_chunk_work_id = work_id

        try:
            # Execute chunk within policy envelope
            chunk_result = self._execute_chunk(work_item, policy_decision)

            # Checkpoint
            checkpointed = self._checkpoint_chunk(work_item, policy_decision, chunk_result)

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
        """Execute one bounded chunk within policy envelope.

        This is a placeholder for actual chunk execution. In this milestone,
        we simulate chunk execution without actual inference or provider calls.
        """
        # In a full implementation, this would:
        # 1. Use the policy envelope to govern execution
        # 2. Execute bounded cognitive work
        # 3. Respect time/iteration budgets
        # 4. Yield on user reactivation or resource pressure

        # For this milestone, simulate successful chunk execution
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
        """Checkpoint chunk state using existing persistence.

        Uses PlatformResumeHint if available, otherwise logs checkpoint.
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

            # Create resume hint
            resume_hint = PlatformResumeHint(
                task_id=work_id,
                last_phase="cognitive_chunk",
                last_step="completed",
                remaining_work=chunk_result.get("remaining_steps", []),
                accumulated_evidence=chunk_result.get("evidence_collected", []),
                findings=chunk_result.get("findings", []),
                resume_condition="idle_safe",
                stopping_condition=chunk_result.get("terminal_state", "COMPLETED"),
                updated_at=utc_now(),
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
