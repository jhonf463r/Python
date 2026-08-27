"""Need Formulation Service — R8-G4.

Transforms SelfExaminationFinding into StructuredNeed when a capability gap
is detected. This closes the GAP → NEED edge in the self-construction loop.

The service distinguishes between:
- CAPABILITY GAP: missing capability, missing knowledge, inability, uncertainty, limitation
- OPERATIONAL GAP: provider slow, route failing, latency high

Only capability-shaped findings produce StructuredNeed objects.
"""

from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    SelfExaminationFinding,
    StructuredNeed,
    NeedStatus,
)


# Capability-shaped finding categories that should produce needs
CAPABILITY_SHAPED_CATEGORIES = {
    "capability_discovery",
    "missing_capability",
    "missing_knowledge",
    "inability",
    "uncertainty",
    "limitation",
}

# Operational finding categories that should NOT produce needs
OPERATIONAL_CATEGORIES = {
    "provider_underperformance",
    "route_failure",
    "latency_high",
    "performance_degradation",
    "resource_pressure",
    "network_failure",
    "timeout",
    "throughput_issue",
    "load_issue",
}


class NeedFormulationService:
    """Transforms findings into structured needs."""

    def __init__(self) -> None:
        self._needs_created: int = 0

    def formulate_need_from_finding(
        self,
        finding: SelfExaminationFinding,
    ) -> StructuredNeed | None:
        """Transform a capability-shaped finding into a StructuredNeed.

        Returns None if the finding is operational (not a capability gap).

        Args:
            finding: SelfExaminationFinding to transform

        Returns:
            StructuredNeed if finding is capability-shaped, None otherwise
        """
        # Check if finding is capability-shaped
        if not self._is_capability_shaped(finding):
            return None

        # Extract need information from finding
        need = StructuredNeed(
            source_finding_id=finding.finding_id,
            category=finding.category,
            capability_gap=self._extract_capability_gap(finding),
            current_state=self._extract_current_state(finding),
            desired_state=self._extract_desired_state(finding),
            knowledge_required=self._extract_knowledge_required(finding),
            reason=finding.summary or finding.recommendation,
            evidence=finding.evidence_refs,
            priority=self._map_severity_to_priority(finding.severity),
            status=NeedStatus.PENDING,
        )

        self._needs_created += 1
        return need

    def _is_capability_shaped(self, finding: SelfExaminationFinding) -> bool:
        """Determine if a finding represents a capability gap.

        Returns True if the finding is about missing capability/knowledge.
        Returns False if the finding is operational (latency, provider issues, etc).

        FAIL-CLOSED: Ambiguous findings do NOT create needs.
        """
        # First check if explicitly operational - reject immediately
        if finding.category.lower() in OPERATIONAL_CATEGORIES:
            return False

        # Check if explicitly capability-shaped
        if finding.category.lower() in CAPABILITY_SHAPED_CATEGORIES:
            return True

        # FAIL-CLOSED: For ambiguous categories, do NOT create needs
        # Do not use keyword detection to override semantic category
        # "provider cannot handle load" must remain operational
        # "we need a faster route" must remain operational
        return False

    def _extract_capability_gap(self, finding: SelfExaminationFinding) -> str:
        """Extract what capability is missing.

        Only uses finding.title if present. Otherwise returns empty string
        to indicate insufficient specification.
        """
        if finding.title:
            return finding.title
        return ""

    def _extract_current_state(self, finding: SelfExaminationFinding) -> str:
        """Extract current state (what IABV cannot do now).

        Only extracts if summary contains explicit "cannot" pattern.
        Otherwise returns empty string to indicate insufficient specification.
        """
        # Try to extract from summary only if explicit pattern exists
        if "cannot" in finding.summary.lower():
            parts = finding.summary.lower().split("cannot")
            if len(parts) > 1:
                return f"Cannot {parts[1].strip()}"
        return ""

    def _extract_desired_state(self, finding: SelfExaminationFinding) -> str:
        """Extract desired state (what IABV should be able to do).

        Only uses finding.recommendation if present and non-empty.
        Otherwise returns empty string to indicate insufficient specification.
        """
        if finding.recommendation:
            return finding.recommendation
        return ""

    def _extract_knowledge_required(self, finding: SelfExaminationFinding) -> str:
        """Extract what knowledge/capability would address the gap.

        Only uses category if it is a known capability-shaped category.
        Otherwise returns empty string to indicate insufficient specification.
        """
        if finding.category and finding.category.lower() in CAPABILITY_SHAPED_CATEGORIES:
            return finding.category
        return ""

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map finding severity to need priority."""
        severity_lower = severity.lower()
        if "critical" in severity_lower:
            return "critical"
        if "high" in severity_lower:
            return "high"
        if "low" in severity_lower:
            return "low"
        return "medium"

    def get_needs_created_count(self) -> int:
        """Return the number of needs created by this service."""
        return self._needs_created
