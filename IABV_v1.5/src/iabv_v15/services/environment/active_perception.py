"""Active Perception Service - minimal decision structure for observation needs.

Answers "What do I need to know for this goal?" for each decision.

Structure:
- GOAL: The current goal/objective
- REQUIRED_STATE: State required for the goal
- AVAILABLE_STATE: Currently available state
- STALE_STATE: State that is stale (beyond TTL)
- UNKNOWN_STATE: State that has never been observed
- OBSERVATION_REQUIRED: Whether observation is needed
- OBSERVATION_SCOPE: What level of observation is needed (LEVEL_0/1/2)
- EXPECTED_COST: Estimated cost of the observation

Reuses GoalEngine / existing context assembly where possible.
Does not implement a new planning engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from iabv_v15.services.environment.environment_baseline import (
    EnvironmentBaseline,
    ObservationFreshness,
    ObservationLevel,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observation Scope
# ---------------------------------------------------------------------------

class ObservationScope(Enum):
    """Scope of observation needed."""
    NONE = "none"  # No observation needed
    LIGHTWEIGHT = "lightweight"  # LEVEL_0 or LEVEL_1
    DEEP = "deep"  # LEVEL_2


# ---------------------------------------------------------------------------
# Active Perception Decision
# ---------------------------------------------------------------------------

@dataclass
class ActivePerceptionDecision:
    """Decision structure for observation needs."""
    goal: str
    required_state: list[str] = field(default_factory=list)
    available_state: dict[str, Any] = field(default_factory=dict)
    stale_state: list[str] = field(default_factory=list)
    unknown_state: list[str] = field(default_factory=list)
    observation_required: bool = False
    observation_scope: ObservationScope = ObservationScope.NONE
    expected_cost_mb: int = 0
    recommended_actions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Active Perception Service
# ---------------------------------------------------------------------------

class ActivePerceptionService:
    """Minimal decision structure for observation needs.

    Determines what observations are needed for a given goal based on:
    - Current baseline state
    - Freshness of observations
    - Goal requirements
    - Resource constraints
    """

    # Goal-specific observation requirements
    GOAL_OBSERVATION_REQUIREMENTS: dict[str, dict[str, Any]] = {
        'git_operation': {
            'required_state': ['git', 'workspace_root'],
            'scope': ObservationScope.LIGHTWEIGHT,
            'cost_mb': 10,
        },
        'gpu_inference': {
            'required_state': ['gpu', 'ram_cpu'],
            'scope': ObservationScope.LIGHTWEIGHT,
            'cost_mb': 50,
        },
        'model_selection': {
            'required_state': ['ollama', 'models', 'ram_cpu'],
            'scope': ObservationScope.LIGHTWEIGHT,
            'cost_mb': 50,
        },
        'tool_execution': {
            'required_state': ['tools', 'ram_cpu'],
            'scope': ObservationScope.LIGHTWEIGHT,
            'cost_mb': 20,
        },
        'deep_discovery': {
            'required_state': ['hardware', 'software', 'services'],
            'scope': ObservationScope.DEEP,
            'cost_mb': 200,
        },
        'network_operation': {
            'required_state': ['network'],
            'scope': ObservationScope.LIGHTWEIGHT,
            'cost_mb': 10,
        },
        'github_operation': {
            'required_state': ['github', 'git'],
            'scope': ObservationScope.LIGHTWEIGHT,
            'cost_mb': 10,
        },
    }

    def __init__(
        self,
        baseline_service: Any | None = None,
    ) -> None:
        self._baseline_service = baseline_service

    def decide_observations_needed(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
    ) -> ActivePerceptionDecision:
        """Determine what observations are needed for a given goal.

        Args:
            goal: The current goal/objective
            context: Additional context for the decision

        Returns:
            ActivePerceptionDecision with observation requirements
        """
        context = context or {}
        baseline = self._get_baseline()

        # Get goal-specific requirements
        requirements = self.GOAL_OBSERVATION_REQUIREMENTS.get(goal, {})
        required_keys = requirements.get('required_state', [])
        scope = requirements.get('scope', ObservationScope.LIGHTWEIGHT)
        cost_mb = requirements.get('cost_mb', 0)

        # Analyze current state
        available_state = {}
        stale_state = []
        unknown_state = []

        for key in required_keys:
            value, freshness = baseline.get_observation(key)
            if freshness == ObservationFreshness.FRESH:
                available_state[key] = value
            elif freshness == ObservationFreshness.STALE:
                stale_state.append(key)
            else:  # UNKNOWN
                unknown_state.append(key)

        # Determine if observation is required
        observation_required = len(stale_state) > 0 or len(unknown_state) > 0

        # Generate recommended actions
        recommended_actions = []
        if unknown_state:
            recommended_actions.extend([
                f"Observe {key} (unknown)"
                for key in unknown_state
            ])
        if stale_state:
            recommended_actions.extend([
                f"Refresh {key} (stale)"
                for key in stale_state
            ])

        return ActivePerceptionDecision(
            goal=goal,
            required_state=required_keys,
            available_state=available_state,
            stale_state=stale_state,
            unknown_state=unknown_state,
            observation_required=observation_required,
            observation_scope=scope,
            expected_cost_mb=cost_mb,
            recommended_actions=recommended_actions,
        )

    def should_perform_observation(
        self,
        decision: ActivePerceptionDecision,
        resource_pressure: str = "low",
    ) -> bool:
        """Determine if an observation should be performed based on resource pressure.

        Args:
            decision: The active perception decision
            resource_pressure: Current resource pressure (low, moderate, high, critical)

        Returns:
            True if observation should be performed
        """
        if not decision.observation_required:
            return False

        # Resource pressure constraints
        if resource_pressure == "critical":
            # Only essential observations under CRITICAL
            return decision.observation_scope == ObservationScope.LIGHTWEIGHT and decision.expected_cost_mb < 50
        elif resource_pressure == "high":
            # Suppress deep discovery under HIGH
            return decision.observation_scope != ObservationScope.DEEP
        elif resource_pressure == "moderate":
            # Reduce deep discovery under MODERATE
            return decision.expected_cost_mb < 200
        else:  # low
            return True

    def get_observation_level_for_scope(
        self,
        scope: ObservationScope,
    ) -> ObservationLevel:
        """Map observation scope to observation level.

        Args:
            scope: Observation scope

        Returns:
            Observation level
        """
        if scope == ObservationScope.DEEP:
            return ObservationLevel.LEVEL_2_DEEP_DISCOVERY
        else:
            return ObservationLevel.LEVEL_1_LIGHT_RUNTIME

    def _get_baseline(self) -> EnvironmentBaseline:
        """Get the current baseline."""
        if self._baseline_service is not None:
            return self._baseline_service.get_baseline()
        # Return empty baseline if service not available
        return EnvironmentBaseline()


# Global instance
_global_active_perception_service: ActivePerceptionService | None = None


def get_active_perception_service() -> ActivePerceptionService:
    """Get the global active perception service instance."""
    global _global_active_perception_service
    if _global_active_perception_service is None:
        raise RuntimeError("ActivePerceptionService not initialized")
    return _global_active_perception_service
