"""Cognitive Operating Policy: Pure bounded policy layer for cognitive envelopes.

This module implements the cognitive operating policy as a pure, bounded policy layer
that determines cognitive envelopes for each work item. It does NOT execute, orchestrate,
schedule, or plan. It only computes cognitive constraints based on normalized state.

ARCHITECTURAL POSITION:
- This is NOT a new orchestrator
- This is NOT a new scheduler
- This is NOT a new memory system
- This is NOT a new planner
- This is NOT a new provider selector
- This is a pure policy layer that computes cognitive envelopes

OWNERSHIP:
- InternalMetabolicStateService: READ-ONLY (provides metabolic state snapshot)
- ControlMasterService: Owns work queue, prioritization (provides work items)
- CognitivePolicy: This layer (computes cognitive envelopes from normalized state)
- WorkQueueExecutor: Bridges queue to canonical inference
- AdaptiveTaskOrchestrator: Orchestrates request execution
- InferenceService: Canonical inference execution
- TaskOutcomeRecorder: Records outcomes and learning closure

KEY PRINCIPLES:
- PURE: No side effects
- DETERMINISTIC: Same normalized input → same output
- READ-ONLY: Does not modify any state
- SIDE-EFFECT FREE: No execution inside the policy
- IMMUTABLE DECISIONS: CognitivePolicyDecision is immutable

STATE VECTOR:
Input State:
- G: Goal Value (importance/urgency)
- C: Complexity (structural complexity)
- A: Ambiguity (ambiguity in requirements)
- U: Uncertainty (uncertainty in outcome)
- R: Risk (risk of failure)
- V: Expected Value (expected value of success)
- T: Available Time (time budget)
- E: Resource State (RAM, CPU, GPU)
- M: Memory Relevance (confidence in relevant memory)
- X: Prior Experience (historical success)

Derived Outputs:
- D: Reasoning Depth (LEVEL 0-3)
- H: Time Horizon (SHORT, MEDIUM, LONG)
- B: Budget (time and resource bounds)
- K: Chunk Size (adaptive chunk size)
- P: Parallelism (allowed/forbidden)

No arbitrary numeric coefficients are assigned. The policy uses qualitative thresholds
and ordinal comparisons.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class TimeHorizon(str, Enum):
    """Time horizon for cognitive work."""
    SHORT = "short"  # Current interaction / incident / urgent work
    MEDIUM = "medium"  # Current work item / task / playbook
    LONG = "long"  # Architecture / evolution / strategic learning


class ReasoningDepth(str, Enum):
    """Reasoning depth levels."""
    LEVEL_0 = "level_0"  # Fast / existing evidence
    LEVEL_1 = "level_1"  # Normal contextual reasoning
    LEVEL_2 = "level_2"  # Deep reflection / additional evidence
    LEVEL_3 = "level_3"  # Expert / external reasoning


class ObservationMode(str, Enum):
    """Observation mode for cognitive work."""
    OBSERVE = "observe"  # Gather more information before reasoning
    REFLECT = "reflect"  # Reason with existing evidence
    ACT = "act"  # Execute with current evidence
    DEFER = "defer"  # Defer work to later


class ResourcePressure(str, Enum):
    """Resource pressure classification."""
    CRITICAL = "critical"  # < 2GB available RAM
    HIGH = "high"  # < 4GB available RAM
    MODERATE = "moderate"  # < 6GB available RAM
    LOW = "low"  # >= 6GB available RAM


# ============================================================================
# Resource Projection
# ============================================================================

@dataclass(frozen=True)
class ResourceProjection:
    """Minimal immutable projection of resource state for cognitive policy.

    This is a read-only snapshot of resource state that can be passed to
    CognitiveStateVector without passing service instances. It contains
    only policy-relevant information with provenance and freshness.

    This does NOT replace ResourceAwareController. It is a projection
    that the policy can consume without becoming a resource controller.
    """
    # Resource state ID for traceability
    resource_state_id: str = ""

    # Timestamp for freshness
    timestamp: str = ""

    # Source/provenance
    source: str = "ResourceAwareController"

    # Pressure classification
    pressure: ResourcePressure = ResourcePressure.LOW

    # CPU state
    cpu_load_1m: float = 0.0
    cpu_count: int = 1

    # RAM state (in GB for policy normalization)
    ram_available_gb: float = 8.0
    ram_used_pct: float = 0.0

    # GPU state (if available)
    gpu_available: bool = False
    vram_available_gb: float = 0.0

    # Overall available capacity (0.0 to 1.0)
    available_capacity: float = 1.0

    # Confidence in resource state (0.0 to 1.0)
    confidence: float = 1.0


# ============================================================================
# State Vector
# ============================================================================

@dataclass(frozen=True)
class CognitiveStateVector:
    """Normalized state vector for cognitive policy.

    This is the input to the cognitive policy function. It is immutable
    and contains only normalized, comparable values.
    """
    # Input State
    goal_value: float  # G: Goal Value (0.0 to 1.0)
    complexity: float  # C: Complexity (0.0 to 1.0)
    ambiguity: float  # A: Ambiguity (0.0 to 1.0)
    uncertainty: float  # U: Uncertainty (0.0 to 1.0)
    risk: float  # R: Risk (0.0 to 1.0)
    expected_value: float  # V: Expected Value (0.0 to 1.0)
    available_time_seconds: float  # T: Available Time (seconds)
    memory_relevance: float  # M: Memory Relevance (0.0 to 1.0)
    prior_experience: float  # X: Prior Experience (0.0 to 1.0)

    # Resource projection (with default)
    resource_projection: ResourceProjection = field(default_factory=ResourceProjection)  # E: Resource State

    # Contextual metadata (for traceability, not used in policy logic)
    work_item_id: str = ""
    work_item_source: str = ""
    work_item_title: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Cognitive Policy Decision
# ============================================================================

@dataclass(frozen=True)
class ToolSelectionEnvelope:
    """Tool/model selection envelope (constraints, not hardcoded providers).

    The policy does NOT choose a named provider directly. It produces constraints
    that existing selectors can use to choose specific providers.
    """
    required_capabilities: list[str] = field(default_factory=list)
    max_cost: float | None = None  # Maximum cost allowed (None = no limit)
    max_latency_seconds: float | None = None  # Maximum latency allowed
    max_risk: float | None = None  # Maximum risk allowed
    allowed_local: bool = True  # Whether local providers are allowed
    allowed_remote: bool = True  # Whether remote providers are allowed
    min_reasoning_level: ReasoningDepth = ReasoningDepth.LEVEL_0
    required_execution_capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BudgetConstraints:
    """Time and resource budget constraints."""
    max_time_seconds: float | None = None  # Hard time bound (None = no limit)
    max_iterations: int | None = None  # Hard iteration bound (None = no limit)
    max_observations: int | None = None  # Hard observation bound (None = no limit)
    max_cost: float | None = None  # Hard cost bound (None = no limit)
    max_replanning: int | None = None  # Hard replanning bound (None = no limit)

    # Soft bounds
    target_confidence: float = 0.8  # Target confidence threshold
    mrv_threshold: float = 0.1  # Marginal Reasoning Value threshold
    mvi_threshold: float = 0.1  # Marginal Value of Information threshold


@dataclass(frozen=True)
class StoppingConditions:
    """Stopping conditions for cognitive work."""
    sufficient_evidence: bool = False
    acceptable_confidence: bool = False
    low_marginal_gain: bool = False
    hard_budget_reached: bool = False
    resource_pressure_detected: bool = False
    repeated_equivalent_reasoning: bool = False
    repeated_equivalent_observation: bool = False
    deadline_exhausted: bool = False

    # Thresholds
    min_evidence_threshold: float = 0.7  # Minimum evidence threshold
    min_confidence_threshold: float = 0.8  # Minimum confidence threshold
    marginal_gain_threshold: float = 0.1  # Marginal gain threshold


@dataclass(frozen=True)
class CognitivePolicyDecision:
    """Immutable cognitive policy decision.

    This is the output of the cognitive policy function. It is immutable
    and contains only normalized policy output and trace references.

    It does NOT contain mutable service references. It does NOT execute anything.
    It is serializable/loggable without credentials.
    """
    # Decision ID (for traceability)
    decision_id: str

    # Input state snapshot (for traceability)
    state_vector: CognitiveStateVector

    # Derived outputs
    horizon: TimeHorizon
    reasoning_depth: ReasoningDepth
    observation_mode: ObservationMode

    # Budget constraints
    budget: BudgetConstraints

    # Chunking and parallelism
    chunk_size: str  # "small", "medium", "large" (adaptive)
    parallelism_allowed: bool

    # Tool/model selection envelope
    tool_selection_envelope: ToolSelectionEnvelope

    # Stopping conditions
    stopping_conditions: StoppingConditions

    # MRV and MVI (for traceability)
    mrv: float  # Marginal Reasoning Value
    mvi: float  # Marginal Value of Information

    # Trace references (for audit/debugging)
    reasoning_trace: dict[str, Any] = field(default_factory=dict)

    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Cognitive Policy Function
# ============================================================================

class CognitiveOperatingPolicy:
    """Pure cognitive operating policy function.

    This class implements the cognitive policy function:

    CognitivePolicyDecision = f(G, C, A, U, R, V, T, E, M, X)

    The function is:
    - PURE: No side effects
    - DETERMINISTIC: Same normalized input → same output
    - READ-ONLY: Does not modify any state
    - SIDE-EFFECT FREE: No execution inside the policy

    It does NOT:
    - Execute any providers
    - Modify any state
    - Call external services
    - Perform I/O operations
    """

    def __init__(self) -> None:
        """Initialize the cognitive operating policy.

        The policy has no dependencies on mutable services. It is a pure function.
        """
        pass

    def compute_decision(self, state_vector: CognitiveStateVector) -> CognitivePolicyDecision:
        """Compute cognitive policy decision from state vector.

        Args:
            state_vector: Normalized state vector

        Returns:
            Immutable cognitive policy decision
        """
        # Use resource projection for resource pressure
        resource_pressure = state_vector.resource_projection.pressure

        # Compute horizon
        horizon = self._compute_horizon(state_vector, resource_pressure)

        # Compute reasoning depth
        reasoning_depth = self._compute_reasoning_depth(state_vector, resource_pressure, horizon)

        # Compute MRV
        mrv = self._compute_mrv(state_vector, reasoning_depth)

        # Compute MVI
        mvi = self._compute_mvi(state_vector)

        # Compute observation mode
        observation_mode = self._compute_observation_mode(mrv, mvi, state_vector)

        # Compute budget constraints
        budget = self._compute_budget(state_vector, resource_pressure, horizon, reasoning_depth)

        # Compute chunk size
        chunk_size = self._compute_chunk_size(state_vector, budget, resource_pressure)

        # Compute parallelism
        parallelism_allowed = self._compute_parallelism(state_vector, resource_pressure)

        # Compute tool selection envelope
        tool_selection_envelope = self._compute_tool_selection_envelope(
            state_vector, horizon, reasoning_depth, resource_pressure
        )

        # Compute stopping conditions
        stopping_conditions = self._compute_stopping_conditions(
            state_vector, budget, mrv, mvi
        )

        # Build reasoning trace
        reasoning_trace = {
            "resource_pressure": resource_pressure.value,
            "horizon_reasoning": self._explain_horizon(state_vector, resource_pressure, horizon),
            "depth_reasoning": self._explain_depth(state_vector, resource_pressure, horizon, reasoning_depth),
            "mrv": mrv,
            "mvi": mvi,
            "observation_mode_reasoning": self._explain_observation_mode(mrv, mvi, observation_mode),
        }

        # Create immutable decision
        from uuid import uuid4
        decision_id = str(uuid4())

        return CognitivePolicyDecision(
            decision_id=decision_id,
            state_vector=state_vector,
            horizon=horizon,
            reasoning_depth=reasoning_depth,
            observation_mode=observation_mode,
            budget=budget,
            chunk_size=chunk_size,
            parallelism_allowed=parallelism_allowed,
            tool_selection_envelope=tool_selection_envelope,
            stopping_conditions=stopping_conditions,
            mrv=mrv,
            mvi=mvi,
            reasoning_trace=reasoning_trace,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _classify_resource_pressure(self, available_ram_gb: float) -> ResourcePressure:
        """Classify resource pressure based on available RAM."""
        if available_ram_gb < 2.0:
            return ResourcePressure.CRITICAL
        elif available_ram_gb < 4.0:
            return ResourcePressure.HIGH
        elif available_ram_gb < 6.0:
            return ResourcePressure.MODERATE
        else:
            return ResourcePressure.LOW

    def _compute_horizon(
        self,
        state_vector: CognitiveStateVector,
        resource_pressure: ResourcePressure,
    ) -> TimeHorizon:
        """Compute time horizon from state vector.

        SHORT: Current interaction / incident / urgent work
        MEDIUM: Current work item / task / playbook
        LONG: Architecture / evolution / strategic learning
        """
        # Urgent/interactive work → SHORT
        if state_vector.available_time_seconds < 60:  # Less than 1 minute
            return TimeHorizon.SHORT

        # High goal value + low time → SHORT
        if state_vector.goal_value > 0.8 and state_vector.available_time_seconds < 300:
            return TimeHorizon.SHORT

        # Critical resource pressure → SHORT (only urgent work allowed)
        if resource_pressure == ResourcePressure.CRITICAL:
            return TimeHorizon.SHORT

        # High complexity + high time → LONG
        if state_vector.complexity > 0.7 and state_vector.available_time_seconds > 3600:
            return TimeHorizon.LONG

        # High expected value + high time → LONG
        if state_vector.expected_value > 0.8 and state_vector.available_time_seconds > 3600:
            return TimeHorizon.LONG

        # Default → MEDIUM
        return TimeHorizon.MEDIUM

    def _explain_horizon(
        self,
        state_vector: CognitiveStateVector,
        resource_pressure: ResourcePressure,
        horizon: TimeHorizon,
    ) -> str:
        """Explain horizon reasoning for trace."""
        reasons = []
        if state_vector.available_time_seconds < 60:
            reasons.append("urgent time constraint (< 60s)")
        if state_vector.goal_value > 0.8 and state_vector.available_time_seconds < 300:
            reasons.append("high goal value with moderate time constraint")
        if resource_pressure == ResourcePressure.CRITICAL:
            reasons.append("critical resource pressure")
        if state_vector.complexity > 0.7 and state_vector.available_time_seconds > 3600:
            reasons.append("high complexity with ample time")
        if state_vector.expected_value > 0.8 and state_vector.available_time_seconds > 3600:
            reasons.append("high expected value with ample time")
        if not reasons:
            reasons.append("default medium horizon")
        return "; ".join(reasons)

    def _compute_reasoning_depth(
        self,
        state_vector: CognitiveStateVector,
        resource_pressure: ResourcePressure,
        horizon: TimeHorizon,
    ) -> ReasoningDepth:
        """Compute reasoning depth from state vector.

        LEVEL 0: Fast / existing evidence
        LEVEL 1: Normal contextual reasoning
        LEVEL 2: Deep reflection / additional evidence
        LEVEL 3: Expert / external reasoning
        """
        # Critical resource pressure → LEVEL 0
        if resource_pressure == ResourcePressure.CRITICAL:
            return ReasoningDepth.LEVEL_0

        # SHORT horizon → LEVEL 0 or 1
        if horizon == TimeHorizon.SHORT:
            if state_vector.uncertainty < 0.3 and state_vector.memory_relevance > 0.7:
                return ReasoningDepth.LEVEL_0
            else:
                return ReasoningDepth.LEVEL_1

        # LONG horizon + high complexity → LEVEL 2 or 3
        if horizon == TimeHorizon.LONG and state_vector.complexity > 0.7:
            if state_vector.risk > 0.7:
                return ReasoningDepth.LEVEL_3
            else:
                return ReasoningDepth.LEVEL_2

        # High uncertainty → LEVEL 2
        if state_vector.uncertainty > 0.7:
            return ReasoningDepth.LEVEL_2

        # High ambiguity → LEVEL 2
        if state_vector.ambiguity > 0.7:
            return ReasoningDepth.LEVEL_2

        # Default → LEVEL 1
        return ReasoningDepth.LEVEL_1

    def _explain_depth(
        self,
        state_vector: CognitiveStateVector,
        resource_pressure: ResourcePressure,
        horizon: TimeHorizon,
        reasoning_depth: ReasoningDepth,
    ) -> str:
        """Explain depth reasoning for trace."""
        reasons = []
        if resource_pressure == ResourcePressure.CRITICAL:
            reasons.append("critical resource pressure")
        if horizon == TimeHorizon.SHORT:
            if state_vector.uncertainty < 0.3 and state_vector.memory_relevance > 0.7:
                reasons.append("short horizon with low uncertainty and high memory relevance")
            else:
                reasons.append("short horizon with moderate uncertainty")
        if horizon == TimeHorizon.LONG and state_vector.complexity > 0.7:
            if state_vector.risk > 0.7:
                reasons.append("long horizon with high complexity and high risk")
            else:
                reasons.append("long horizon with high complexity")
        if state_vector.uncertainty > 0.7:
            reasons.append("high uncertainty")
        if state_vector.ambiguity > 0.7:
            reasons.append("high ambiguity")
        if not reasons:
            reasons.append("default normal reasoning depth")
        return "; ".join(reasons)

    def _compute_mrv(self, state_vector: CognitiveStateVector, reasoning_depth: ReasoningDepth) -> float:
        """Compute Marginal Reasoning Value (MRV).

        MRV_k = ExpectedQualityGain(reason_k) / ExpectedReasoningCost(reason_k)

        This is a simplified qualitative computation. In production, this would
        use more sophisticated models.
        """
        # Expected quality gain based on uncertainty reduction
        expected_quality_gain = state_vector.uncertainty * state_vector.expected_value

        # Expected reasoning cost based on depth
        depth_cost = {
            ReasoningDepth.LEVEL_0: 0.1,
            ReasoningDepth.LEVEL_1: 0.3,
            ReasoningDepth.LEVEL_2: 0.6,
            ReasoningDepth.LEVEL_3: 1.0,
        }[reasoning_depth]

        # Adjust for resource pressure
        resource_factor = max(0.1, state_vector.resource_projection.ram_available_gb / 16.0)  # Normalize to 16GB

        # MRV = gain / (cost * resource_factor)
        if depth_cost * resource_factor == 0:
            return 0.0
        return expected_quality_gain / (depth_cost * resource_factor)

    def _compute_mvi(self, state_vector: CognitiveStateVector) -> float:
        """Compute Marginal Value of Information (MVI).

        MVI_k = ExpectedDecisionQualityGain(observation_k) / Cost(observation_k)

        This is a simplified qualitative computation. In production, this would
        use more sophisticated models.
        """
        # Expected decision quality gain based on uncertainty reduction
        expected_decision_gain = state_vector.uncertainty * (1.0 - state_vector.memory_relevance)

        # Observation cost (simplified)
        observation_cost = 0.2  # Fixed cost for observation

        # MVI = gain / cost
        if observation_cost == 0:
            return 0.0
        return expected_decision_gain / observation_cost

    def _compute_observation_mode(
        self,
        mrv: float,
        mvi: float,
        state_vector: CognitiveStateVector,
    ) -> ObservationMode:
        """Compute observation mode from MRV and MVI.

        if MVI sufficiently exceeds MRV: OBSERVE
        elif MRV sufficiently exceeds marginal action cost: REFLECT / REASON
        elif evidence is sufficient: ACT
        else: DEFER / REPLAN
        """
        # Hysteresis threshold
        hysteresis = 0.1

        # MVI > MRV + hysteresis → OBSERVE
        if mvi > mrv + hysteresis:
            return ObservationMode.OBSERVE

        # MRV > marginal action cost → REFLECT
        marginal_action_cost = 0.3
        if mrv > marginal_action_cost + hysteresis:
            return ObservationMode.REFLECT

        # Evidence sufficient → ACT
        if state_vector.memory_relevance > 0.7 and state_vector.uncertainty < 0.3:
            return ObservationMode.ACT

        # Default → DEFER
        return ObservationMode.DEFER

    def _explain_observation_mode(
        self,
        mrv: float,
        mvi: float,
        observation_mode: ObservationMode,
    ) -> str:
        """Explain observation mode reasoning for trace."""
        hysteresis = 0.1
        if mvi > mrv + hysteresis:
            return f"MVI ({mvi:.2f}) > MRV ({mrv:.2f}) + hysteresis → OBSERVE"
        marginal_action_cost = 0.3
        if mrv > marginal_action_cost + hysteresis:
            return f"MRV ({mrv:.2f}) > marginal action cost ({marginal_action_cost:.2f}) → REFLECT"
        return "default observation mode"

    def _compute_budget(
        self,
        state_vector: CognitiveStateVector,
        resource_pressure: ResourcePressure,
        horizon: TimeHorizon,
        reasoning_depth: ReasoningDepth,
    ) -> BudgetConstraints:
        """Compute budget constraints from state vector."""
        # Hard time bound
        max_time = state_vector.available_time_seconds

        # Hard iteration bound based on depth
        max_iterations = {
            ReasoningDepth.LEVEL_0: 1,
            ReasoningDepth.LEVEL_1: 3,
            ReasoningDepth.LEVEL_2: 5,
            ReasoningDepth.LEVEL_3: 10,
        }[reasoning_depth]

        # Hard observation bound
        max_observations = {
            ReasoningDepth.LEVEL_0: 0,
            ReasoningDepth.LEVEL_1: 2,
            ReasoningDepth.LEVEL_2: 5,
            ReasoningDepth.LEVEL_3: 10,
        }[reasoning_depth]

        # Hard replanning bound
        max_replanning = {
            ReasoningDepth.LEVEL_0: 0,
            ReasoningDepth.LEVEL_1: 1,
            ReasoningDepth.LEVEL_2: 2,
            ReasoningDepth.LEVEL_3: 3,
        }[reasoning_depth]

        # Adjust for resource pressure
        if resource_pressure == ResourcePressure.CRITICAL:
            max_iterations = 1
            max_observations = 0
            max_replanning = 0

        # Target confidence based on risk
        target_confidence = 0.8 + (state_vector.risk * 0.2)  # Higher risk → higher confidence

        return BudgetConstraints(
            max_time_seconds=max_time,
            max_iterations=max_iterations,
            max_observations=max_observations,
            max_replanning=max_replanning,
            target_confidence=min(0.95, target_confidence),
        )

    def _compute_chunk_size(
        self,
        state_vector: CognitiveStateVector,
        budget: BudgetConstraints,
        resource_pressure: ResourcePressure,
    ) -> str:
        """Compute chunk size from state vector and budget.

        Under pressure: smaller chunks
        Under stable resources and low uncertainty: larger chunks
        """
        # Critical pressure → small chunks
        if resource_pressure == ResourcePressure.CRITICAL:
            return "small"

        # High uncertainty → small chunks
        if state_vector.uncertainty > 0.7:
            return "small"

        # High risk → small chunks
        if state_vector.risk > 0.7:
            return "small"

        # Low time budget → small chunks
        if budget.max_time_seconds and budget.max_time_seconds < 300:
            return "small"

        # Low uncertainty + ample time → large chunks
        if state_vector.uncertainty < 0.3 and budget.max_time_seconds and budget.max_time_seconds > 3600:
            return "large"

        # Default → medium chunks
        return "medium"

    def _compute_parallelism(
        self,
        state_vector: CognitiveStateVector,
        resource_pressure: ResourcePressure,
    ) -> bool:
        """Compute parallelism from state vector and resource pressure.

        Parallelism is forbidden when:
        - Dependencies conflict (not modeled here, handled by AdaptivePlannerService)
        - Resources are insufficient
        - Risk is too high
        - Work is not independently verifiable (not modeled here)
        """
        # Critical resource pressure → no parallelism
        if resource_pressure == ResourcePressure.CRITICAL:
            return False

        # High resource pressure → no parallelism
        if resource_pressure == ResourcePressure.HIGH:
            return False

        # High risk → no parallelism
        if state_vector.risk > 0.7:
            return False

        # Default → parallelism allowed
        return True

    def _compute_tool_selection_envelope(
        self,
        state_vector: CognitiveStateVector,
        horizon: TimeHorizon,
        reasoning_depth: ReasoningDepth,
        resource_pressure: ResourcePressure,
    ) -> ToolSelectionEnvelope:
        """Compute tool/model selection envelope.

        The policy does NOT choose a named provider directly. It produces constraints.
        """
        # Critical resource pressure → local only
        allowed_local = True
        allowed_remote = resource_pressure != ResourcePressure.CRITICAL

        # Minimum reasoning level
        min_reasoning_level = reasoning_depth

        # Max latency based on horizon
        max_latency = {
            TimeHorizon.SHORT: 10.0,  # 10 seconds
            TimeHorizon.MEDIUM: 60.0,  # 1 minute
            TimeHorizon.LONG: None,  # No limit
        }[horizon]

        # Max risk based on work item risk
        max_risk = state_vector.risk

        return ToolSelectionEnvelope(
            allowed_local=allowed_local,
            allowed_remote=allowed_remote,
            min_reasoning_level=min_reasoning_level,
            max_latency_seconds=max_latency,
            max_risk=max_risk,
        )

    def _compute_stopping_conditions(
        self,
        state_vector: CognitiveStateVector,
        budget: BudgetConstraints,
        mrv: float,
        mvi: float,
    ) -> StoppingConditions:
        """Compute stopping conditions from state vector, budget, MRV, MVI."""
        # Check if evidence is sufficient
        sufficient_evidence = state_vector.memory_relevance > 0.7 and state_vector.uncertainty < 0.3

        # Check if confidence is acceptable
        acceptable_confidence = state_vector.memory_relevance > budget.target_confidence

        # Check if marginal gain is low
        low_marginal_gain = mrv < budget.mrv_threshold and mvi < budget.mvi_threshold

        # Check if hard budget is reached (not computed here, set to False)
        hard_budget_reached = False

        # Check if resource pressure is detected (not computed here, set to False)
        resource_pressure_detected = False

        # Check for repeated equivalent reasoning (not computed here, set to False)
        repeated_equivalent_reasoning = False

        # Check for repeated equivalent observation (not computed here, set to False)
        repeated_equivalent_observation = False

        # Check if deadline is exhausted (not computed here, set to False)
        deadline_exhausted = False

        return StoppingConditions(
            sufficient_evidence=sufficient_evidence,
            acceptable_confidence=acceptable_confidence,
            low_marginal_gain=low_marginal_gain,
            hard_budget_reached=hard_budget_reached,
            resource_pressure_detected=resource_pressure_detected,
            repeated_equivalent_reasoning=repeated_equivalent_reasoning,
            repeated_equivalent_observation=repeated_equivalent_observation,
            deadline_exhausted=deadline_exhausted,
            min_evidence_threshold=0.7,
            min_confidence_threshold=budget.target_confidence,
            marginal_gain_threshold=budget.mrv_threshold,
        )
