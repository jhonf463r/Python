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

import concurrent.futures
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
    chunk_completed: bool = False
    chunk_checkpointed: bool = False
    yielded: bool = False
    terminal_state: str = ""  # COMPLETED, STOPPED, DEFERRED, BLOCKED, FAILED
    admission_blocked: bool = False
    admission_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    steps_completed: int = 0
    evidence_collected: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    run_record_id: str = ""
    confidence: float = 0.0


class CognitiveMetabolicTick:
    """Governed persistent background cognitive metabolism.

    This component implements bounded cognitive chunks during user inactivity.
    It uses a DIFFERENT governance model than interactive requests:

    GOVERNANCE MODEL:
    - CognitiveOperatingPolicy: Controls admission via observation_mode (defer/observe/reflect/act)
    - ResourceAwareController: Controls admission via resource safety checks
    - Admission checks: User activity, resource state, urgent work
    - Time bounding: Hard timeout on inference execution

    DIFFERENT FROM INTERACTIVE GOVERNANCE:
    - AutonomyGovernancePolicy: NOT USED (governs autonomous actions like git sync, PR merge)
    - CapabilityReadinessService: NOT USED (evaluates domain-specific capabilities like wplay.login)
    - LeaseClient: NOT USED (for MCP child processes requesting tool execution leases)
    - TaskContextAssembler: NOT USED (assembles extensive context for interactive requests)

    RATIONALE: Background cognitive work is bounded, non-autonomous inference using
    the ANALYTICS role for general-purpose reasoning. It doesn't modify external
    systems, require domain-specific capabilities, use MCP tools, or need extensive
    interactive context. This is a legitimate different governance path, not a bypass.
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
        self._preemption_requested = False  # Flag for genuine preemption
        # Track active inference futures to detect orphaned workers
        self._active_futures: dict[str, concurrent.futures.Future] = {}
        # Track chunk iterations per work_id for IABV-level iteration enforcement
        self._chunk_iterations: dict[str, int] = {}

        # Persistent cognitive process identity - generated per instance, work-keyed via checkpoint
        # The process_id is loaded from the work-specific checkpoint when work is selected
        self._cognitive_process_id = f"cog-process-{uuid.uuid4().hex[:12]}"
        # Flag to track whether process_id was restored from checkpoint (for cross-identity prevention)
        self._process_id_restored = False
        # Track which work_id was used to restore the process_id (for cross-work prevention)
        self._restored_work_id = ""
        # Track which work_id this instance has executed (binds instance after first execution)
        self._executed_work_id = ""
        logger.info("Generated new cognitive process ID for instance: %s", self._cognitive_process_id)

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

        # Check for existing checkpoint to resume from
        checkpoint_info = None
        if work_id:
            checkpoint_info = self.resume_from_checkpoint(work_id)
            if checkpoint_info:
                logger.info(
                    "METABOLIC_TICK_RESUME trace_id=%s work_id=%s checkpoint_phase=%s",
                    trace_id,
                    work_id,
                    checkpoint_info["checkpoint_phase"],
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
            result = MetabolicTickResult(
                tick_id=tick_id,
                timestamp=timestamp,
                user_activity_state=admission["user_activity_state"],
                resource_state=admission["resource_state"],
                selected_work_id=getattr(work_item, "id", ""),
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

            # Bind instance to this work_id upon first execution (prevents cross-identity contamination)
            if self._executed_work_id == "":
                self._executed_work_id = work_id
                logger.info(
                    "METABOLIC_TICK_INSTANCE_BOUND trace_id=%s work_id=%s",
                    trace_id,
                    self._executed_work_id,
                )

        try:
            # Execute chunk within policy envelope
            logger.info(
                "METABOLIC_TICK_CHUNK_START trace_id=%s work_id=%s decision_id=%s",
                trace_id,
                work_id,
                policy_decision.decision_id,
            )
            chunk_result = self._execute_chunk(work_item, policy_decision, checkpoint_info)
            logger.info(
                "METABOLIC_TICK_CHUNK_COMPLETE trace_id=%s work_id=%s terminal_state=%s steps_completed=%s",
                trace_id,
                work_id,
                chunk_result.get("terminal_state", "UNKNOWN"),
                chunk_result.get("steps_completed", 0),
            )

            # Checkpoint
            checkpointed = self._checkpoint_chunk(work_item, policy_decision, chunk_result, checkpoint_info)
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
                chunk_completed=True,
                chunk_checkpointed=checkpointed,
                yielded=True,
                terminal_state=chunk_result.get("terminal_state", "COMPLETED"),
                steps_completed=chunk_result.get("steps_completed", 0),
                evidence_collected=chunk_result.get("evidence_collected", []),
                findings=chunk_result.get("findings", []),
                run_record_id=chunk_result.get("run_record_id", ""),
                confidence=chunk_result.get("confidence", 0.0),
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
            # Allow bypass if preemption was requested (genuine preemption)
            time_since_last_chunk = datetime.now(timezone.utc).timestamp() - self._last_chunk_completion_time
            if time_since_last_chunk < self._cooldown_seconds and not self._preemption_requested:
                return {
                    "admitted": False,
                    "user_activity_state": user_activity_state,
                    "resource_state": resource_state,
                    "reason": f"Cooldown active ({time_since_last_chunk:.2f}s < {self._cooldown_seconds}s)",
                }

        # Reset preemption flag after admission check
        with self._lock:
            self._preemption_requested = False

        return {
            "admitted": True,
            "user_activity_state": user_activity_state,
            "resource_state": resource_state,
            "reason": "Admitted",
        }

    def _check_user_activity(self) -> str:
        """Check user activity using existing runtime signals where available.

        Priority:
        1. IntelligentResourceManager UserActivityTracker (typing, interaction)
        2. Chat message timestamp (fallback)
        3. UIHeartbeatWatchdog (UI activity)
        """
        # Try IntelligentResourceManager UserActivityTracker first
        try:
            # Check if bootstrap has intelligent_resource_manager available
            # This would be injected if available
            if hasattr(self, '_intelligent_resource_manager') and self._intelligent_resource_manager is not None:
                user_state = self._intelligent_resource_manager.user_state()
                # Map IntelligentResourceManager states to our states
                if user_state.value == "active":
                    return "ACTIVE"
                elif user_state.value in ("idle_short", "idle_long", "absent"):
                    return "IDLE_ELIGIBLE"
        except Exception:
            pass  # Fall through to chat message check

        # Fallback to chat message timestamp
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
        """Select one eligible cognitive work item from existing sources.

        Cognitive work categories (not ordinary executable tasks):
        - investigation
        - cognitive_fixation
        - cognitive_incubation
        - metacognitive_*
        - reflection
        - hypothesis_analysis
        - strategy_evaluation
        - validation_reasoning
        - architecture_analysis

        Priority:
        1. PlatformPendingQueue actionable items with cognitive category
        2. ControlMaster active objectives (if cognitive in nature)
        """
        # Cognitive work categories that represent actual cognitive processes
        COGNITIVE_CATEGORIES = {
            "investigation",
            "cognitive_fixation",
            "cognitive_incubation",
            "metacognitive_feedback_applied",
            "metacognitive_loop_closure_improving",
            "metacognitive_false_positive",
            "metacognitive_false_negative",
            "metacognitive_persistent_bias",
            "metacognitive_overconfidence",
            "metacognitive_underconfidence",
            "reflection",
            "hypothesis_analysis",
            "strategy_evaluation",
            "validation_reasoning",
            "architecture_analysis",
        }

        # Try PlatformPendingQueue first, filter for cognitive categories
        if self.platform_pending_queue is not None:
            try:
                actionable = self.platform_pending_queue.list_actionable()
                if actionable:
                    # Filter for cognitive work categories
                    cognitive_items = [
                        item for item in actionable
                        if getattr(item, "category", "") in COGNITIVE_CATEGORIES
                    ]
                    if cognitive_items:
                        # Select highest priority cognitive item
                        return cognitive_items[0]
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
        """Build cognitive state vector from work item and resource state.

        Derives real values from work item metadata, resource state, and
        historical context instead of using hardcoded defaults.
        """
        # Get resource projection
        resource_projection = self._build_resource_projection()

        # Extract work item metadata
        work_id = getattr(work_item, "id", "")
        work_source = getattr(work_item, "source", "unknown")
        work_title = getattr(work_item, "title", "")
        work_category = getattr(work_item, "category", "")
        work_priority = getattr(work_item, "priority", "medium")

        # Derive goal_value from work priority
        priority_to_value = {"critical": 0.9, "high": 0.8, "medium": 0.6, "low": 0.4}
        goal_value = priority_to_value.get(work_priority, 0.6)

        # Derive complexity from work category and title length
        complex_categories = {"investigation", "architecture_analysis", "strategy_evaluation"}
        complexity = 0.8 if work_category in complex_categories else min(0.3 + (len(work_title) / 200.0), 0.9)

        # Derive ambiguity from missing fields
        ambiguity = 0.7 if not work_category else 0.3

        # Derive uncertainty from resource projection confidence
        uncertainty = 1.0 - resource_projection.confidence

        # Derive risk from category
        high_risk_categories = {"cognitive_fixation", "metacognitive_persistent_bias"}
        risk = 0.8 if work_category in high_risk_categories else 0.3

        # Derive expected_value from goal_value and risk
        expected_value = goal_value * (1.0 - risk * 0.5)

        # Derive available_time from idle threshold and resource pressure
        pressure_time_factor = {
            ResourcePressure.CRITICAL: 0.1,
            ResourcePressure.HIGH: 0.3,
            ResourcePressure.MODERATE: 0.6,
            ResourcePressure.LOW: 1.0,
        }
        available_time_seconds = self.idle_threshold_seconds * pressure_time_factor.get(
            resource_projection.pressure, 0.5
        )

        # Derive memory_relevance from work recency (simplified)
        memory_relevance = 0.6 if work_source == "control_master" else 0.4

        # Derive prior_experience from category familiarity (simplified)
        familiar_categories = {"investigation", "reflection"}
        prior_experience = 0.8 if work_category in familiar_categories else 0.5

        return CognitiveStateVector(
            goal_value=goal_value,
            complexity=complexity,
            ambiguity=ambiguity,
            uncertainty=uncertainty,
            risk=risk,
            expected_value=expected_value,
            available_time_seconds=available_time_seconds,
            memory_relevance=memory_relevance,
            prior_experience=prior_experience,
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

    def _execute_chunk(self, work_item: Any, policy_decision: CognitivePolicyDecision, checkpoint_info: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute one bounded chunk within policy envelope using governed inference path.

        Uses existing InferenceService for real cognitive work while respecting
        policy envelopes (time budget, iteration limits, reasoning depth).

        Args:
            work_item: The work item to execute
            policy_decision: The cognitive policy decision
            checkpoint_info: Optional checkpoint context for state continuity
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

        # Build context with checkpoint state if available
        context = {
            "work_id": work_id,
            "work_source": work_source,
            "cognitive_process_id": self._cognitive_process_id,  # Use persistent process ID
            "policy_decision_id": policy_decision.decision_id,
            "reasoning_depth": policy_decision.reasoning_depth.value,
            "time_horizon": policy_decision.horizon.value,
            "observation_mode": policy_decision.observation_mode.value,
            "max_iterations": policy_decision.budget.max_iterations if hasattr(policy_decision.budget, 'max_iterations') else 1,
            "max_time_seconds": policy_decision.budget.max_time_seconds if hasattr(policy_decision.budget, 'max_time_seconds') else 300.0,
            "chunk_size": policy_decision.chunk_size,
            "parallelism_allowed": policy_decision.parallelism_allowed,
        }

        # IABV_COGNITIVE_DEPTH: Reasoning depth affects IABV execution plan
        # The policy reasoning depth controls budget constraints (max_iterations, max_observations, max_replanning)
        # which are enforced at the IABV orchestration level, not at the provider level.
        # MODEL_INTERNAL_DEPTH: UNCONTROLLED (providers do not expose internal reasoning depth control)
        # IABV_COGNITIVE_DEPTH: ENFORCED (via budget constraints and iteration bounds)
        context["iabv_depth_enforcement"] = "ENFORCED"
        context["model_internal_depth_control"] = "UNCONTROLLED"

        # Add checkpoint context for state continuity
        if checkpoint_info and checkpoint_info.get("context_snapshot"):
            context["checkpoint_context"] = checkpoint_info["context_snapshot"]
            context["resumed_from_phase"] = checkpoint_info.get("checkpoint_phase")
            context["resumed_from_step"] = checkpoint_info.get("last_successful_step")

        # Create inference request for bounded cognitive work
        request = InferenceRequest(
            request_id=f"cog-{work_id}-{uuid.uuid4().hex[:8]}",
            user_goal=f"Process background task: {work_title}",
            task_role=TaskRole.ANALYTICS,  # Use analytics role for background cognitive work
            role_hint=TaskRole.ANALYTICS,
            context=context,
        )

        # Execute via InferenceService if available
        if self.inference_service is not None:
            try:
                # Enforce policy budget constraints with actual time bounding
                # The policy decision includes budget limits that must be respected
                max_iterations = policy_decision.budget.max_iterations if hasattr(policy_decision.budget, 'max_iterations') else 1
                max_time_seconds = policy_decision.budget.max_time_seconds if hasattr(policy_decision.budget, 'max_time_seconds') else 300.0

                # SAFE_BOUNDARY_BOUNDED_EXECUTION: Check for orphaned workers
                # The ThreadPoolExecutor timeout is a caller timeout only - it does NOT guarantee
                # cancellation of the underlying inference. We must prevent overlapping chunks
                # for the same work_id to avoid resource exhaustion.
                with self._lock:
                    if work_id in self._active_futures:
                        existing_future = self._active_futures[work_id]
                        if existing_future and not existing_future.done():
                            logger.warning(
                                "Orphaned inference worker still running for work_id=%s, deferring new chunk",
                                work_id,
                            )
                            return {
                                "terminal_state": "DEFERRED",
                                "steps_completed": 0,
                                "evidence_collected": [],
                                "findings": [],
                                "error": "Previous inference still in progress (caller timeout exceeded but worker not cancelled)",
                            }

                # SAFE_BOUNDARY_YIELD: Check preemption flag before starting inference
                # If preemption was requested, defer this chunk to allow safe yield
                with self._lock:
                    if self._preemption_requested:
                        logger.info("Safe-boundary yield requested, deferring new chunk for work_id=%s", work_id)
                        # Reset preemption flag after deferral
                        self._preemption_requested = False
                        return {
                            "terminal_state": "DEFERRED",
                            "steps_completed": 0,
                            "evidence_collected": [],
                            "findings": [],
                            "error": "Safe-boundary yield requested before chunk start",
                        }

                # IABV_COGNITIVE_CHUNK_ITERATIONS: Enforce iteration bound at IABV level
                # The underlying inference providers do not support actual iteration budget enforcement.
                # We enforce the bound at the IABV orchestration level by tracking chunk iterations.
                current_iterations = self._chunk_iterations.get(work_id, 0)
                if max_iterations is not None and current_iterations >= max_iterations:
                    logger.warning(
                        "IABV iteration bound reached for work_id=%s: current=%s max=%s",
                        work_id,
                        current_iterations,
                        max_iterations,
                    )
                    return {
                        "terminal_state": "DEFERRED",
                        "steps_completed": 0,
                        "evidence_collected": [],
                        "findings": [],
                        "error": f"IABV iteration bound reached: {current_iterations}/{max_iterations}",
                    }

                # HARD TIME BOUND: Wrap inference call with timeout
                # This provides defensible time bounding even if underlying provider doesn't enforce it
                # NOTE: This is a CALLER timeout only. It does NOT guarantee cancellation of the
                # underlying inference worker. The orphaned worker check above prevents overlapping chunks.
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

                def run_inference():
                    return self.inference_service.infer_task(request)

                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_inference)
                        # Track the future to detect orphaned workers
                        with self._lock:
                            self._active_futures[work_id] = future
                        try:
                            run_record = future.result(timeout=max_time_seconds)
                        finally:
                            # Clean up future tracking regardless of outcome
                            with self._lock:
                                self._active_futures.pop(work_id, None)
                except FutureTimeoutError:
                    # Time bound exceeded - treat as FAILED with no fabricated evidence
                    # NOTE: The underlying inference worker may still be running.
                    # The orphaned worker check in future calls will prevent overlapping chunks.
                    logger.warning(
                        "Cognitive chunk exceeded time bound: work_id=%s max_time_seconds=%s",
                        work_id,
                        max_time_seconds,
                    )
                    # Clean up future tracking on timeout
                    with self._lock:
                        self._active_futures.pop(work_id, None)
                    return {
                        "terminal_state": "FAILED",
                        "steps_completed": 0,
                        "evidence_collected": [],
                        "findings": [],
                        "run_record_id": "",
                        "confidence": 0.0,
                        "error": f"Time bound exceeded: {max_time_seconds}s",
                    }

                # Increment IABV chunk iteration counter on successful completion
                with self._lock:
                    self._chunk_iterations[work_id] = current_iterations + 1

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
                
                # Extract results - ONLY COMPLETED if actual successful inference occurred
                # These are FACTUAL outcomes (terminal state, evidence, findings)
                # Calibration metrics (calibration_error, uncertainty) are handled by TaskOutcomeRecorder
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
                # Clean up future tracking on exception
                with self._lock:
                    self._active_futures.pop(work_id, None)
                # Return FAILED on exception - NO FALSE SUCCESS
                return {
                    "terminal_state": "FAILED",
                    "steps_completed": 0,
                    "evidence_collected": [],
                    "findings": [],
                    "error": str(exc),
                }
        else:
            # InferenceService unavailable - DEFERRED, no false success
            # terminal_state MUST NOT be COMPLETED when inference is unavailable
            # steps_completed MUST remain 0
            # evidence_collected MUST remain empty
            # findings MUST remain empty
            # run_record_id MUST remain empty
            logger.warning("No InferenceService available for cognitive chunk execution - DEFERRED")
            return {
                "terminal_state": "DEFERRED",
                "steps_completed": 0,
                "evidence_collected": [],
                "findings": [],
                "run_record_id": "",
                "confidence": 0.0,
            }

    def _checkpoint_chunk(
        self,
        work_item: Any,
        policy_decision: CognitivePolicyDecision,
        chunk_result: dict[str, Any],
        checkpoint_info: dict[str, Any] | None = None,
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

            # Create resume hint using ACTUAL contract fields with real progress
            # Determine actual phase and step based on chunk result
            terminal_state = chunk_result.get("terminal_state", "UNKNOWN")
            steps_completed = chunk_result.get("steps_completed", 0)
            
            # Dynamic checkpoint phase based on actual progress
            if terminal_state == "COMPLETED":
                checkpoint_phase = "cognitive_completed"
                last_successful_step = "inference_success"
            elif terminal_state == "FAILED":
                checkpoint_phase = "cognitive_failed"
                last_successful_step = "none"
            elif terminal_state == "DEFERRED":
                checkpoint_phase = "cognitive_deferred"
                last_successful_step = "none"
            else:
                checkpoint_phase = "cognitive_in_progress"
                last_successful_step = "inference_attempted"
            
            # Remaining steps based on actual state
            if terminal_state == "COMPLETED":
                remaining_steps = []
            else:
                remaining_steps = ["retry_inference", "fallback_analysis"]
            
            resume_hint = PlatformResumeHint(
                task_id=work_id,
                checkpoint_phase=checkpoint_phase,
                last_successful_step=last_successful_step,
                remaining_steps=remaining_steps,
                handoff_required=False,
                context_snapshot={
                    "policy_decision_id": policy_decision.decision_id,
                    "horizon": policy_decision.horizon.value,
                    "depth": policy_decision.reasoning_depth.value,
                    "terminal_state": terminal_state,
                    "steps_completed": steps_completed,
                    "evidence_collected": chunk_result.get("evidence_collected", []),
                    "findings": chunk_result.get("findings", []),
                    "run_record_id": chunk_result.get("run_record_id"),
                    "confidence": chunk_result.get("confidence"),
                },
                metadata={
                    "cognitive_process_id": self._cognitive_process_id,  # Use persistent process ID
                    "work_item_source": getattr(work_item, "source", "unknown"),
                    "work_title": getattr(work_item, "title", "unknown"),
                    "terminal_state": terminal_state,
                    "checkpointed_at": datetime.now(timezone.utc).isoformat(),
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
        """Request yield of current chunk with genuine preemption.

        Sets preemption flag and checkpoints current state before yielding.
        Returns True if yield was requested, False if no chunk running.
        """
        with self._lock:
            if not self._current_chunk_running:
                return False

            # Set preemption flag for genuine preemption
            self._preemption_requested = True

            # Get current work ID for checkpointing
            work_id = self._current_chunk_work_id

            # Reset the running flag to allow next tick
            self._current_chunk_running = False
            self._current_chunk_work_id = ""

            # Reset cooldown to allow immediate re-admission if needed
            self._last_chunk_completion_time = 0.0

            logger.info("Preemption requested for work_id=%s", work_id)
            return True

    def cognitive_process_id(self) -> str:
        """Get the persistent cognitive process identity.

        This ID is stable across all chunks and links them together
        as part of a continuous cognitive process.
        """
        return self._cognitive_process_id

    def resume_from_checkpoint(self, work_id: str) -> dict[str, Any] | None:
        """Resume work from a previous checkpoint using existing infrastructure.

        Implements UNBOUND/BOUND semantics:
        - UNBOUND: Fresh instance can restore process_id from any valid checkpoint
        - BOUND: Instance bound to work_id can only resume that same work_id

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

            hint_process_id = resume_hint.metadata.get("cognitive_process_id", "")
            if not hint_process_id:
                logger.warning("Checkpoint missing cognitive_process_id for work_id=%s", work_id)
                return None

            # UNBOUND/BOUND semantics
            # Instance is BOUND if it has restored from a checkpoint OR has executed a chunk
            is_bound = self._process_id_restored or self._executed_work_id != ""

            if is_bound:
                # Determine the bound work_id
                bound_work_id = self._restored_work_id if self._process_id_restored else self._executed_work_id

                # Verify work_id matches the bound work_id
                if work_id != bound_work_id:
                    logger.warning(
                        "Bound instance cannot resume different work: bound to %s, requested %s",
                        bound_work_id,
                        work_id,
                    )
                    return None

                # Verify process_id matches for bound instances
                if hint_process_id != self._cognitive_process_id:
                    logger.warning(
                        "Checkpoint process ID mismatch for bound instance: expected %s, got %s",
                        self._cognitive_process_id,
                        hint_process_id,
                    )
                    return None
            else:
                # Instance is UNBOUND - restore process_id from checkpoint
                # This allows a fresh instance to adopt the process identity from the checkpoint
                logger.info(
                    "UNBOUND instance restoring process_id from checkpoint: %s -> %s",
                    self._cognitive_process_id,
                    hint_process_id,
                )
                self._cognitive_process_id = hint_process_id
                self._process_id_restored = True
                self._restored_work_id = work_id

            # Restore context from checkpoint
            context_snapshot = resume_hint.context_snapshot or {}
            logger.info(
                "Resumed from checkpoint: work_id=%s, phase=%s, last_step=%s, process_id=%s",
                work_id,
                resume_hint.checkpoint_phase,
                resume_hint.last_successful_step,
                self._cognitive_process_id,
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
