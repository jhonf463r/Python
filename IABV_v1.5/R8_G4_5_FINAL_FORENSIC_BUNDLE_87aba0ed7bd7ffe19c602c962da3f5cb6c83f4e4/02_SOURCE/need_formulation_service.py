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
# These are the actual categories produced by OperationalSelfExaminationService
# that represent real capability or knowledge gaps
CAPABILITY_SHAPED_CATEGORIES = {
    # Original G4 categories (not currently produced by OSES but kept for compatibility)
    "capability_discovery",
    "missing_capability",
    "missing_knowledge",
    "inability",
    "uncertainty",
    "limitation",
    # Real OSES categories that represent capability gaps
    "capability_promised_but_unavailable",  # P0.32+P0.37: capability promised but not wired in build
    "windows_capability_missing",  # Windows-specific capabilities missing from environment
    "research_gap",  # P0.38: user-declared capabilities needing investigation
}

# Operational finding categories that should NOT produce needs
# These are the actual categories produced by OperationalSelfExaminationService
# that represent operational problems, not capability gaps
OPERATIONAL_CATEGORIES = {
    # Original G4 operational categories
    "provider_underperformance",
    "route_failure",
    "latency_high",
    "performance_degradation",
    "resource_pressure",
    "network_failure",
    "timeout",
    "throughput_issue",
    "load_issue",
    # Real OSES operational categories
    "functional_gap",  # Underutilized resources, not missing capabilities
    "configuration_gap",  # Missing configuration/secrets, not capability gaps
    "underutilized_resource",  # Resources available but not used
    "background_error_stagnation",
    "temporal_latency_anomaly",
    "temporal_latency_regression",
    "temporal_stalled_operations",
    "deep_analysis_ema_drift",
    "deep_analysis_correlated_failures",
    "deep_analysis_latency_outliers",
    "metacognitive_feedback_applied",
    "metacognitive_loop_closure_improving",
    "recurring_failure",
    "repeated_stall",
    "inertial_route",
    "repeated_block",
    "weak_correction",
    "token_rotation",
    "ui_heartbeat_stall",
    "interaction_episode_stalls",
    "interaction_episode_failures",
    "interaction_episode_blocked",
    "interaction_episode_pending",
    "dispatch_lifecycle_anomaly",
    "external_failure_followup_misrouted_to_local",
    "human_assist_bridge",
    "startup_degradation",
    "startup_false_ready",
    "qml_event_loop_starvation",
    "startup_populate_ui_freeze",
    "startup_populate_ui_incomplete",
    "startup_memory_spike",
    "startup_chat_bridge_missing",
    "startup_chat_bridge_late",
    "startup_priority_inversion",
    "boot_profile_degradation",
    "boot_profile_regression",
    "cloud_reasoning_degradation",
    "cloud_provider_degradation",
    "cloud_rate_limiting",
    "cloud_provider_improving",
    "cloud_no_functional_provider",
    "resource_degradation",
    "repeated_resource_pressure_blocks",
    "startup_heavy_work_starvation",
    "stale_security_verification_repeated",
    "web_skill_profile_missing",
    "devin_repair_worker_available_but_unused",
    "web_session_expired",
    "task_packet_high_unresolved",
    "task_packet_recurring_approval",
    "task_packet_no_worker",
    "task_packet_gate_unusable",
    "task_packet_worker_budget_exhausted",
    "task_packet_worker_handoff_unresolved",
    "task_packet_worker_high_corrections",
    "task_packet_worker_good_compression",
    "task_packet_performance_jump",
    "task_packet_metacognitive_miscalibration",
    "task_packet_metacognitive_overconfidence",
    "task_packet_metacognitive_underconfidence",
    "adaptive_threshold_shift",
    "windows_integration_gaps",
    "autonomy_index_insufficient_data",
    "universal_autonomy_index",
    "autonomy_calibration_drift",
    "oses_finding",
    "repeated_visual_mismatch",
    "user_browser_differs_from_iabv_session",
    "black_capture_repeated",
    "user_needed_to_explain_same_gap",
    "repeated_restore_without_recapture",
    "repeated_win32_restore_unavailable",
    "repeated_user_selection_needed",
    "repeated_restore_attempted",
    "isolated_profile_blocks_user_logged_in_browser",
    "metacognitive_maintenance_starved",
    "incident_followup_falls_to_local_chat",
    "external_readiness_missing",
    "build_stale_repeated",
    "cdp_unavailable_repeated",
    "external_intent_misrouted_local",
    "startup_truth_refresh_stall_repeated",
    "startup_evolution_stall_repeated",
    "prebuild_resource_snapshot_stall_repeated",
    "post_result_development_packet_slow",
    "ui_display_sqlite_stall_repeated",
    "ui_portable_context_scan_stall_repeated",
    "discernment_frame_missing_in_task_context",
    "action_without_grounding",
    "contradiction_ignored",
    "low_confidence_acted_as_high",
    "failed_attractor_repeated",
    "external_source_bias",
    "stale_external_data_overrode_live_world_model",
    "bridge_claimed_ready_but_no_vm",
    "local_chat_slow_after_continuity",
    "ui_stall_without_causal_phase",
    "duplicate_ui_bridge_owner",
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
