"""Build a compact `ControlMasterDigest` from a `ControlMasterState`.

The digest is intentionally smaller than `PortableContextPackage` and
narrower in scope: it exists only to give any IA/assistant a fresh
governance picture (vision + irrevocable rules + active objectives +
risks + recent decisions + unresolved) without pasting the full chat
history.

This builder is a pure helper -- no IO, no services, no side effects --
so it can be composed into `SystemPromptBuilder` via the existing
``governance_rules`` parameter.
"""

from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    ControlMasterDigest,
    ControlMasterState,
    ControlRuleSeverity,
    ControlRuleStatus,
)


_SEVERITY_WEIGHT = {
    ControlRuleSeverity.IRREVOCABLE: 0,
    ControlRuleSeverity.STRICT: 1,
    ControlRuleSeverity.ADVISORY: 2,
    ControlRuleSeverity.INFO: 3,
}


class ControlMasterDigestBuilder:
    def __init__(
        self,
        *,
        max_rules: int = 8,
        max_objectives: int = 5,
        max_backlog: int = 5,
        max_risks: int = 5,
        max_decisions: int = 5,
        max_unresolved: int = 5,
        max_chars: int = 2000,
    ) -> None:
        self.max_rules = max_rules
        self.max_objectives = max_objectives
        self.max_backlog = max_backlog
        self.max_risks = max_risks
        self.max_decisions = max_decisions
        self.max_unresolved = max_unresolved
        self.max_chars = max_chars

    def build(
        self,
        state: ControlMasterState,
        autonomy_metrics: dict[str, Any] | None = None,
        coordination_patterns: list[dict[str, Any]] | None = None,
        work_queue: list[dict[str, Any]] | None = None,
    ) -> ControlMasterDigest:
        rules = [
            rule
            for rule in state.global_rules
            if rule.status == ControlRuleStatus.ACTIVE
            and rule.severity in (ControlRuleSeverity.IRREVOCABLE, ControlRuleSeverity.STRICT)
        ]
        rules.sort(key=lambda r: (_SEVERITY_WEIGHT.get(r.severity, 9), r.title))
        rules_brief = [
            f"[{rule.severity.value}] {rule.title}"
            for rule in rules[: self.max_rules]
        ]

        active_brief = [
            f"active:{oid}" for oid in state.active_objective_ids[: self.max_objectives]
        ]

        backlog_brief: list[str] = []
        for item in state.technical_backlog[: self.max_backlog]:
            title = (
                item.get("title")
                or item.get("summary")
                or item.get("name")
                or item.get("id")
                or ""
            )
            if title:
                backlog_brief.append(str(title))

        risks_brief: list[str] = []
        for risk in state.current_risks[: self.max_risks]:
            title = risk.get("title") or risk.get("summary") or ""
            severity = risk.get("severity") or ""
            if title:
                risks_brief.append(f"[{severity}] {title}" if severity else str(title))

        decisions_brief = [
            f"[{d.status.value}] {d.summary}"
            for d in state.recent_decisions[: self.max_decisions]
        ]

        tests_state_brief = _render_tests_brief(state.current_tests_state)
        autonomy_brief = _render_autonomy_metrics(autonomy_metrics)
        coordination_brief = _render_coordination_patterns(coordination_patterns)
        wq_brief, wq_counts = _render_work_queue(work_queue, limit=5)

        digest = ControlMasterDigest(
            current_vision=(state.current_vision or "").strip(),
            active_objectives_brief=active_brief,
            rules_brief=rules_brief,
            top_backlog=backlog_brief,
            current_risks=risks_brief,
            recent_decisions_brief=decisions_brief,
            unresolved=list(state.unresolved_items)[: self.max_unresolved],
            tests_state_brief=tests_state_brief,
            autonomy_metrics_brief=autonomy_brief,
            coordination_patterns_brief=coordination_brief,
            work_queue_brief=wq_brief,
            work_queue_counts=wq_counts,
            source_state_id=state.state_id,
        )
        return _truncate(digest, self.max_chars)

    def build_markdown(self, state: ControlMasterState) -> str:
        """Convenience: renders the digest as markdown (for injection)."""
        return render_digest_markdown(self.build(state))


def _render_work_queue(
    work_queue: list[dict[str, Any]] | None,
    limit: int = 5,
) -> tuple[list[str], dict[str, int]]:
    if not work_queue:
        return [], {}
    brief: list[str] = []
    counts: dict[str, int] = {}
    for item in work_queue[:limit]:
        label = item.get('priority_label', '')
        source = item.get('source', '')
        title = str(item.get('title', ''))[:40]
        action = str(item.get('next_action', ''))[:30]
        brief.append(f"[{label}] {title} ({source}) {action}")
    for item in work_queue:
        status = item.get('status', 'unknown')
        counts[status] = counts.get(status, 0) + 1
    return brief, counts


def _render_autonomy_metrics(metrics: dict[str, Any] | None) -> str:
    if not metrics:
        return ""
    parts: list[str] = []
    autonomy = metrics.get('autonomy_score')
    resilience = metrics.get('resilience_score')
    calibration = metrics.get('calibration_error')
    blind_spot = metrics.get('blind_spot_ratio')
    verdict = metrics.get('verdict', '')
    if autonomy is not None:
        parts.append(f"autonomy={autonomy:.0%}")
    if resilience is not None:
        parts.append(f"resilience={resilience:.0%}")
    if calibration is not None:
        parts.append(f"calibration_err={calibration:.2f}")
    if blind_spot is not None:
        parts.append(f"blind_spots={blind_spot:.0%}")
    if verdict:
        parts.append(f"verdict={verdict}")
    return " | ".join(parts)


def _render_coordination_patterns(patterns: list[dict[str, Any]] | None) -> str:
    if not patterns:
        return ""
    parts: list[str] = []
    for p in patterns[:4]:
        ptype = str(p.get('pattern_type') or '')
        primary = str(p.get('primary_ia') or '')
        secondary = str(p.get('secondary_ia') or '')
        domain = str(p.get('domain') or '')
        if ptype == 'SPECIALIZATION':
            parts.append(f"{primary}→specialist({domain})")
        elif ptype == 'FALLBACK':
            parts.append(f"{primary}→fallback→{secondary}")
        elif ptype == 'COMPLEMENTARY':
            parts.append(f"{primary}+{secondary}=complementary")
        elif ptype == 'SEQUENCE':
            parts.append(f"{primary}-first→{secondary}-validate")
        else:
            parts.append(f"{ptype}:{primary}")
    return " | ".join(parts)


def _render_tests_brief(tests_state: dict) -> str:
    if not tests_state:
        return ""
    parts: list[str] = []
    passed = tests_state.get("passed")
    failed = tests_state.get("failed")
    total = tests_state.get("total")
    if passed is not None or failed is not None or total is not None:
        parts.append(f"passed={passed}, failed={failed}, total={total}")
    summary = tests_state.get("summary")
    if summary:
        parts.append(str(summary))
    return " | ".join(parts)


def render_digest_markdown(digest: ControlMasterDigest) -> str:
    lines: list[str] = ["## Control Maestro (digest)"]
    if digest.current_vision:
        lines.append(f"Vision: {digest.current_vision}")
    if digest.rules_brief:
        lines.append("Reglas estrictas:")
        for item in digest.rules_brief:
            lines.append(f"- {item}")
    if digest.active_objectives_brief:
        lines.append(f"Objetivos activos: {', '.join(digest.active_objectives_brief)}")
    if digest.top_backlog:
        lines.append("Backlog prioritario:")
        for item in digest.top_backlog:
            lines.append(f"- {item}")
    if digest.current_risks:
        lines.append("Riesgos actuales:")
        for item in digest.current_risks:
            lines.append(f"- {item}")
    if digest.recent_decisions_brief:
        lines.append("Decisiones recientes:")
        for item in digest.recent_decisions_brief:
            lines.append(f"- {item}")
    if digest.unresolved:
        lines.append("UNRESOLVED:")
        for item in digest.unresolved:
            lines.append(f"- {item}")
    if digest.work_queue_brief:
        lines.append("Cola de trabajo (top next actions):")
        for item in digest.work_queue_brief:
            lines.append(f"- {item}")
    if digest.work_queue_counts:
        parts = [f"{k}={v}" for k, v in sorted(digest.work_queue_counts.items())]
        lines.append(f"Work queue counts: {', '.join(parts)}")
    if digest.tests_state_brief:
        lines.append(f"Tests: {digest.tests_state_brief}")
    if digest.autonomy_metrics_brief:
        lines.append(f"Autonomia: {digest.autonomy_metrics_brief}")
    if digest.coordination_patterns_brief:
        lines.append(f"Coordinacion IA-IA: {digest.coordination_patterns_brief}")
    return "\n".join(lines)


def _truncate(digest: ControlMasterDigest, max_chars: int) -> ControlMasterDigest:
    if len(render_digest_markdown(digest)) <= max_chars:
        return digest
    # Drop lowest-priority sections first.  work_queue_brief is kept
    # longer than most sections because it is the canonical next-actions
    # view that downstream consumers rely on.
    for attr in (
        "coordination_patterns_brief",
        "autonomy_metrics_brief",
        "work_queue_counts",
        "tests_state_brief",
        "recent_decisions_brief",
        "top_backlog",
        "current_risks",
        "active_objectives_brief",
    ):
        current = getattr(digest, attr)
        if isinstance(current, list):
            digest = digest.model_copy(update={attr: []})
        elif isinstance(current, dict):
            digest = digest.model_copy(update={attr: {}})
        else:
            digest = digest.model_copy(update={attr: ""})
        if len(render_digest_markdown(digest)) <= max_chars:
            return digest
    # Trim work_queue_brief progressively before removing it entirely.
    while len(digest.work_queue_brief) > 1 and len(render_digest_markdown(digest)) > max_chars:
        digest = digest.model_copy(update={"work_queue_brief": digest.work_queue_brief[:-1]})
    if len(render_digest_markdown(digest)) <= max_chars:
        return digest
    if digest.work_queue_brief and len(render_digest_markdown(digest)) > max_chars:
        digest = digest.model_copy(update={"work_queue_brief": []})
    if len(render_digest_markdown(digest)) <= max_chars:
        return digest
    # Trim rules progressively (keep highest priority first).
    while digest.rules_brief and len(render_digest_markdown(digest)) > max_chars:
        digest = digest.model_copy(update={"rules_brief": digest.rules_brief[:-1]})
    # Only drop unresolved items if we are still over budget -- they are
    # important governance signals per AGENTS.md.
    if digest.unresolved and len(render_digest_markdown(digest)) > max_chars:
        digest = digest.model_copy(update={"unresolved": digest.unresolved[:1]})
    # Last resort: hard-truncate the vision string.
    if len(render_digest_markdown(digest)) > max_chars and digest.current_vision:
        over = len(render_digest_markdown(digest)) - max_chars
        clipped = max(0, len(digest.current_vision) - over - 1)
        digest = digest.model_copy(update={"current_vision": digest.current_vision[:clipped]})
    return digest
