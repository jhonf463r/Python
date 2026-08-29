"""Lesson retrieval service for operational decision making.

Provides lightweight, bounded retrieval of verified operational lessons
that influence tool/action selection without recreating the interactive freeze.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

from iabv_v15.domain.models import OperationalLesson


@dataclass(frozen=True)
class RetrievalContext:
    """Context for lesson retrieval."""
    goal: str = ""
    tool_id: str = ""
    action: str = ""
    resource_state: dict[str, Any] | None = None
    action_risk: str = "low"  # low, medium, high, critical
    timestamp: datetime | None = None

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now(timezone.utc))


@dataclass(frozen=True)
class RetrievalResult:
    """Result of lesson retrieval."""
    lessons: list[OperationalLesson]
    retrieval_time_ms: float
    cache_hit: bool = False
    filtered_by_risk: bool = False
    filtered_by_applicability: bool = False


class LessonRetrieval:
    """Lightweight lesson retrieval with bounded execution.

    Designed to avoid the 49-63 second interactive freeze by:
    - Using in-memory lesson cache
    - Bounded retrieval time
    - Fast pattern matching
    - No deep world-model scans
    """

    def __init__(self, cache_ttl_seconds: float = 60.0):
        self._lessons: list[OperationalLesson] = []
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)

    def load_lessons(self, lessons: list[OperationalLesson]) -> None:
        """Load lessons into cache."""
        self._lessons = lessons
        self._cache_timestamp = datetime.now(timezone.utc)

    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        age = datetime.now(timezone.utc) - self._cache_timestamp
        return age < self._cache_ttl

    def retrieve_relevant_lessons(
        self,
        context: RetrievalContext,
        max_lessons: int = 20,
        min_risk_level: str = "low",
    ) -> RetrievalResult:
        """Retrieve lessons relevant to current context.

        Lightweight, bounded retrieval suitable for fast path.
        """
        import time
        start = time.perf_counter()

        # Filter by applicability
        applicable = [
            lesson for lesson in self._lessons
            if lesson.active and lesson.is_applicable(
                goal=context.goal,
                tool_id=context.tool_id,
                action=context.action,
            )
        ]

        # Filter by risk level (only return lessons >= min_risk_level)
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_risk = risk_order.get(min_risk_level, 0)
        risk_filtered = [
            lesson for lesson in applicable
            if risk_order.get(lesson.risk_level, 0) >= min_risk
        ]

        # Sort by confidence and recency
        sorted_lessons = sorted(
            risk_filtered,
            key=lambda l: (l.confidence, l.created_at_utc),
            reverse=True,
        )

        # Limit results
        result_lessons = sorted_lessons[:max_lessons]

        elapsed_ms = (time.perf_counter() - start) * 1000

        return RetrievalResult(
            lessons=result_lessons,
            retrieval_time_ms=elapsed_ms,
            cache_hit=self.is_cache_valid(),
            filtered_by_risk=len(risk_filtered) < len(applicable),
            filtered_by_applicability=len(applicable) < len(self._lessons),
        )

    def retrieve_for_tool(
        self,
        tool_id: str,
        goal: str = "",
        action_risk: str = "low",
    ) -> list[OperationalLesson]:
        """Convenience method for tool-specific retrieval."""
        context = RetrievalContext(
            goal=goal,
            tool_id=tool_id,
            action_risk=action_risk,
        )
        result = self.retrieve_relevant_lessons(context)
        return result.lessons

    def retrieve_for_high_risk_action(
        self,
        action: str,
        goal: str = "",
    ) -> list[OperationalLesson]:
        """Retrieve lessons for high-risk action evaluation."""
        context = RetrievalContext(
            goal=goal,
            action=action,
            action_risk="critical",
        )
        result = self.retrieve_relevant_lessons(context, min_risk_level="high")
        return result.lessons

    def get_lesson_count(self) -> int:
        """Get total number of cached lessons."""
        return len(self._lessons)

    def clear_cache(self) -> None:
        """Clear lesson cache."""
        self._lessons = []
        self._cache_timestamp = None


# Pre-populated verified lessons from Codex audit
VERIFIED_LESSONS: list[OperationalLesson] = [
    OperationalLesson(
        rule="Agent completion claims require independent verification.",
        context="External tool execution results must be verified before accepting completion claims.",
        applicability="External tool selection and result validation",
        risk_level="high",
        evidence_level="verified",
        confidence=0.95,
        source="Codex cross-agent audit",
        goal_patterns=["external", "tool", "devin", "assistant"],
        tool_patterns=["devin_api", "external_assistant", "mcp"],
        action_patterns=["run", "execute", "invoke"],
    ),
    OperationalLesson(
        rule="Commit/branch identity is not source truth by itself.",
        context="Local commit/branch state may not match remote. Verify remote state before high-impact Git actions.",
        applicability="Git operations, branch switching, source-of-truth verification",
        risk_level="critical",
        evidence_level="verified",
        confidence=0.98,
        source="Codex cross-agent audit",
        goal_patterns=["git", "branch", "commit", "merge", "push"],
        action_patterns=["checkout", "switch", "reset", "merge", "push"],
    ),
    OperationalLesson(
        rule="Historical success does not establish current applicability.",
        context="Past success does not guarantee current conditions are suitable for the same action.",
        applicability="Tool selection, action authorization, resource decisions",
        risk_level="medium",
        evidence_level="verified",
        confidence=0.90,
        source="Codex cross-agent audit",
        goal_patterns=["tool", "action", "execute", "run"],
        action_patterns=["select", "authorize", "execute"],
    ),
    OperationalLesson(
        rule="Mock success does not establish real external capability.",
        context="Mocked test success does not prove real external system capability.",
        applicability="External tool validation, capability assessment",
        risk_level="high",
        evidence_level="verified",
        confidence=0.95,
        source="Codex cross-agent audit",
        goal_patterns=["devin", "external", "api", "validation"],
        tool_patterns=["devin_api", "external_assistant"],
        action_patterns=["validate", "test", "verify"],
    ),
    OperationalLesson(
        rule="Local timeout does not imply remote cancellation.",
        context="Local timeout does not guarantee remote operation was cancelled.",
        applicability="External tool execution, timeout handling",
        risk_level="high",
        evidence_level="verified",
        confidence=0.92,
        source="Codex cross-agent audit",
        goal_patterns=["devin", "external", "timeout", "cancel"],
        tool_patterns=["devin_api", "external_assistant"],
        action_patterns=["run", "execute", "timeout"],
    ),
    OperationalLesson(
        rule="Unknown repository identity blocks high-impact Git actions.",
        context="Do not perform branch switch, deletion, or push without verifying repository identity.",
        applicability="Git operations, source-of-truth verification",
        risk_level="critical",
        evidence_level="verified",
        confidence=0.99,
        source="Codex cross-agent audit",
        goal_patterns=["git", "branch", "commit", "push", "delete"],
        action_patterns=["checkout", "switch", "delete", "push", "merge"],
    ),
    OperationalLesson(
        rule="Resource-driven decisions require fresh timestamped state.",
        context="Resource state must be current with timestamp before resource-intensive decisions.",
        applicability="Resource allocation, model selection, GPU operations",
        risk_level="medium",
        evidence_level="verified",
        confidence=0.88,
        source="Codex cross-agent audit",
        goal_patterns=["resource", "gpu", "model", "preload"],
        action_patterns=["allocate", "preload", "select"],
    ),
    OperationalLesson(
        rule="Expensive observation should not precede ordinary responses unless goal-required.",
        context="Deep world-model scans and expensive observations should not block ordinary chat.",
        applicability="World model refresh, environment scanning, cognitive work",
        risk_level="medium",
        evidence_level="verified",
        confidence=0.85,
        source="Codex cross-agent audit",
        goal_patterns=["world_model", "scan", "observation", "chat"],
        action_patterns=["refresh", "scan", "observe"],
    ),
    OperationalLesson(
        rule="External operations require owner/deadline/recovery/side-effect state.",
        context="External tool execution must track ownership, deadlines, recovery, and side effects.",
        applicability="External tool execution, Devin API, MCP tools",
        risk_level="high",
        evidence_level="verified",
        confidence=0.93,
        source="Codex cross-agent audit",
        goal_patterns=["devin", "external", "api", "execute"],
        tool_patterns=["devin_api", "external_assistant", "mcp"],
        action_patterns=["run", "execute", "invoke"],
    ),
    OperationalLesson(
        rule="High-impact changes require independent verification.",
        context="Code modifications, self-updates, and high-impact changes need verification.",
        applicability="Code modification, self-update, high-impact changes",
        risk_level="critical",
        evidence_level="verified",
        confidence=0.97,
        source="Codex cross-agent audit",
        goal_patterns=["code", "modify", "update", "self"],
        action_patterns=["modify", "update", "change", "edit"],
    ),
]
