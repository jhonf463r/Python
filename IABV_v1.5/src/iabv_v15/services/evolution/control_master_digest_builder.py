"""Build a compact `ControlMasterDigest` from a `ControlMasterState`.

The digest is intentionally smaller than `PortableContextPackage` and
narrower in scope: it exists only to give any IA/assistant a fresh
governance picture (vision + irrevocable rules + active objectives +
risks + recent decisions + unresolved) without pasting the full chat
history.

The `build()` method is a pure projection from an existing state object.
The shared `build_from_service()` adapter performs the authorized state/queue
read and applies the same failure/coverage contract for orchestrator, UI and
export consumers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from iabv_v15.domain.models import (
    ControlMasterDigest,
    ControlMasterState,
    ControlRuleSeverity,
    ControlRuleStatus,
    utc_now,
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

    def build_from_service(
        self,
        service: Any | None,
        *,
        limit: int = 10,
        refresh: bool = False,
    ) -> ControlMasterDigest:
        """Read Control Master once and build a digest without collapsing failures.

        Shared by the task orchestrator and Evolution Center so both consumers
        apply the same queue/source-coverage contract.
        """
        if service is None:
            return ControlMasterDigest(
                signal_status="UNAVAILABLE",
                signal_reason="CONTROL_MASTER_SERVICE_NOT_CONFIGURED",
                work_queue_status="UNAVAILABLE",
                source_coverage={"control_master": "NOT_CONFIGURED"},
                control_master_signal_status="UNAVAILABLE",
            )

        try:
            state = service.current_state(refresh=refresh)
        except Exception as exc:
            return ControlMasterDigest(
                signal_status="UNAVAILABLE",
                signal_reason="CONTROL_MASTER_STATE_READ_FAILED:" + type(exc).__name__,
                work_queue_status="UNAVAILABLE",
                source_coverage={"control_master_state": "READ_FAILED"},
                control_master_signal_status="UNAVAILABLE",
            )

        work_queue: list[dict[str, Any]] | None = None
        work_queue_status = "UNVERIFIED"
        signal_reason = "WORK_QUEUE_NOT_VERIFIED"
        source_coverage: dict[str, str] = {}
        try:
            observed_queue = service.current_work_queue(limit=limit)
        except Exception as exc:
            work_queue_status = "UNAVAILABLE"
            signal_reason = "CONTROL_MASTER_QUEUE_READ_FAILED:" + type(exc).__name__
        else:
            source_errors = tuple(getattr(service, "last_work_queue_errors", ()) or ())
            source_coverage = dict(getattr(service, "last_work_queue_source_coverage", {}) or {})
            if not isinstance(observed_queue, list):
                work_queue_status = "UNVERIFIED"
                signal_reason = "WORK_QUEUE_RESULT_NOT_LIST"
            elif source_errors:
                work_queue_status = "UNAVAILABLE"
                signal_reason = "QUEUE_SOURCE_ERRORS:" + ",".join(source_errors)
            else:
                read_failures = {
                    key: value for key, value in source_coverage.items()
                    if value in {"READ_PARTIAL", "READ_FAILED", "READER_UNAVAILABLE"}
                }
                unresolved_sources = {
                    key: value for key, value in source_coverage.items()
                    if value in {"NOT_CONFIGURED", "NO_FILE"}
                }
                unknown_sources = {
                    key: value for key, value in source_coverage.items()
                    if value != "READ_OK"
                    and value not in {
                        "READ_PARTIAL", "READ_FAILED", "READER_UNAVAILABLE",
                        "NOT_CONFIGURED", "NO_FILE",
                    }
                }
                if read_failures:
                    work_queue_status = "UNAVAILABLE"
                    signal_reason = "SOURCE_COVERAGE_READ_INCOMPLETE"
                elif unresolved_sources or unknown_sources or not source_coverage:
                    work_queue_status = "UNVERIFIED"
                    signal_reason = "SOURCE_APPLICABILITY_OR_COVERAGE_UNRESOLVED"
                else:
                    work_queue = observed_queue
                    work_queue_status = "EMPTY_QUEUE" if not observed_queue else "AVAILABLE"
                    signal_reason = ""

        if not source_coverage:
            source_coverage = dict(
                getattr(service, "last_work_queue_source_coverage", {}) or {}
            )
        if work_queue_status == "UNAVAILABLE" and not source_coverage:
            source_coverage = {"work_queue": "READ_FAILED"}
        try:
            return self.build(
                state,
                work_queue=work_queue,
                work_queue_status=work_queue_status,
                signal_reason=signal_reason,
                source_coverage=source_coverage,
                observed_at_utc=utc_now(),
            )
        except Exception as exc:
            return ControlMasterDigest(
                signal_status="UNAVAILABLE",
                signal_reason="CONTROL_MASTER_DIGEST_BUILD_FAILED:" + type(exc).__name__,
                work_queue_status="UNAVAILABLE",
                source_coverage=source_coverage,
                control_master_signal_status="UNAVAILABLE",
            )

    def build(
        self,
        state: ControlMasterState,
        autonomy_metrics: dict[str, Any] | None = None,
        coordination_patterns: list[dict[str, Any]] | None = None,
        work_queue: list[dict[str, Any]] | None = None,
        work_queue_status: str | None = None,
        signal_reason: str = "",
        source_coverage: dict[str, str] | None = None,
        observed_at_utc: datetime | None = None,
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
        if work_queue_status is None:
            resolved_queue_status = (
                "UNVERIFIED" if work_queue is None
                else ("EMPTY_QUEUE" if not work_queue else "AVAILABLE")
            )
        else:
            resolved_queue_status = str(work_queue_status).strip().upper()
            if resolved_queue_status not in {
                "AVAILABLE", "EMPTY_QUEUE", "UNAVAILABLE", "UNVERIFIED",
            }:
                resolved_queue_status = "UNVERIFIED"

        # Enforce agreement between the declared queue state and the actual read value.
        # Contradictory caller input is epistemically UNVERIFIED, never silently repaired.
        if resolved_queue_status == "AVAILABLE" and (
            not isinstance(work_queue, list) or not work_queue
        ):
            resolved_queue_status = "UNVERIFIED"
        elif resolved_queue_status == "EMPTY_QUEUE" and (
            not isinstance(work_queue, list) or bool(work_queue)
        ):
            resolved_queue_status = "UNVERIFIED"

        if resolved_queue_status in {"UNAVAILABLE", "UNVERIFIED"}:
            # Do not expose partial/unverified queue items as actionable prompt content.
            wq_brief, wq_counts = [], {}

        top_queue_items = _compact_work_queue_items(
            work_queue if resolved_queue_status == "AVAILABLE" else None
        )
        source_evidence_refs = list(dict.fromkeys(
            str(value).strip()
            for value in (state.evidence_links or [])
            if str(value).strip()
        ))[:20]
        source_provenance = dict(
            state.metadata.get("_space_time_control_master_source_provenance") or {}
        )
        freshness_status = str(source_provenance.get("freshness_status") or "UNVERIFIED").upper()
        if freshness_status not in {
            "FRESH", "STALE", "UNAVAILABLE", "UNVERIFIED", "CONFLICTED", "NOT_APPLICABLE",
        }:
            freshness_status = "UNVERIFIED"

        # Signal availability answers whether the Control Master state source
        # was actually read. Queue coverage is an independent dimension.
        source_read_status = str(source_provenance.get("read_status") or "").upper()
        if source_read_status == "READ_OK":
            resolved_signal_status = "AVAILABLE"
        elif source_read_status in {"NO_SOURCE_SNAPSHOT", "READ_FAILED"}:
            resolved_signal_status = "UNAVAILABLE"
        else:
            resolved_signal_status = "UNVERIFIED"

        resolved_signal_reason = str(signal_reason or "").strip()
        if not resolved_signal_reason and resolved_queue_status == "UNAVAILABLE":
            resolved_signal_reason = "WORK_QUEUE_UNAVAILABLE"
        elif not resolved_signal_reason and resolved_queue_status == "UNVERIFIED":
            resolved_signal_reason = "WORK_QUEUE_NOT_VERIFIED"

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
            work_queue_status=resolved_queue_status,
            signal_status=resolved_signal_status,
            signal_reason=resolved_signal_reason,
            source_coverage=dict(source_coverage or {}),
            source_state_id=str(source_provenance.get("source_state_id") or ""),
            project_id=str(source_provenance.get("project_id") or ""),
            source_object=str(source_provenance.get("source_object") or ""),
            workspace_scope_id=str(source_provenance.get("workspace_scope_id") or ""),
            source_revision_or_digest=str(source_provenance.get("source_revision_or_digest") or ""),
            source_generated_at_utc=source_provenance.get("source_generated_at_utc"),
            observed_at_utc=observed_at_utc or utc_now(),
            control_master_signal_status=freshness_status,
            source_evidence_refs=source_evidence_refs,
            top_work_queue_items=top_queue_items,
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
        item_id = str(item.get('id') or item.get('item_id') or '')[:48]
        identity = f"#{item_id} " if item_id else ""
        brief.append(f"[{label}] {identity}{title} ({source}) {action}")
    for item in work_queue:
        status = item.get('status', 'unknown')
        counts[status] = counts.get(status, 0) + 1
    return brief, counts


def _compact_work_queue_items(
    work_queue: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Keep decision-bearing queue provenance in a bounded structured form."""
    if not isinstance(work_queue, list):
        return []
    compact: list[dict[str, Any]] = []
    for item in work_queue[:5]:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or item.get("item_id") or "").strip()
        if not item_id:
            continue
        raw_dependencies = item.get("dependencies") or item.get("depends_on") or []
        if isinstance(raw_dependencies, str):
            dependencies = [raw_dependencies[:100]]
        elif isinstance(raw_dependencies, list):
            dependencies = [str(value)[:100] for value in raw_dependencies[:4] if value is not None]
        else:
            dependencies = []
        raw_evidence = item.get("evidence_refs") or []
        if isinstance(raw_evidence, str):
            evidence_refs = [raw_evidence[:160]]
        elif isinstance(raw_evidence, list):
            evidence_refs = [str(value)[:160] for value in raw_evidence[:4] if value is not None]
        else:
            evidence_refs = []
        compact.append({
            "item_id": item_id[:96],
            "source": str(item.get("source") or "")[:64],
            "priority_label": str(item.get("priority_label") or "")[:24],
            "priority_score": item.get("priority_score"),
            "title": str(item.get("title") or "")[:120],
            "status": str(item.get("status") or "")[:32],
            "next_action": str(item.get("next_action") or "")[:160],
            "dependencies": dependencies,
            "evidence_refs": evidence_refs,
        })
    return compact


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
    lines.append(f"Estado de señal: {digest.signal_status}")
    if digest.signal_reason:
        lines.append(f"Diagnóstico de señal: {digest.signal_reason}")
    if digest.source_coverage:
        coverage = ", ".join(f"{key}={value}" for key, value in sorted(digest.source_coverage.items()))
        lines.append(f"Cobertura de fuentes: {coverage}")
    lines.append(f"Estado de cola: {digest.work_queue_status}")
    lines.append(f"Vigencia D021: {digest.control_master_signal_status}")
    lines.append(f"Digest ID: {digest.digest_id}")
    if digest.project_id:
        lines.append(f"Proyecto: {digest.project_id}")
    if digest.source_object:
        lines.append(f"Fuente: {digest.source_object}")
    if digest.workspace_scope_id:
        lines.append(f"Scope ID: {digest.workspace_scope_id}")
    if digest.source_state_id:
        lines.append(f"Source state ID: {digest.source_state_id}")
    if digest.source_revision_or_digest:
        lines.append(f"Source revision/digest: {digest.source_revision_or_digest}")
    if digest.source_evidence_refs:
        lines.append("Control Master source evidence:")
        for evidence_ref in digest.source_evidence_refs[:20]:
            lines.append(f"- {evidence_ref}")
    if digest.source_generated_at_utc:
        lines.append(f"Source generated: {digest.source_generated_at_utc.isoformat()}")
    if digest.generated_at_utc:
        lines.append(f"Digest generated: {digest.generated_at_utc.isoformat()}")
    if digest.observed_at_utc:
        lines.append(f"Observed at: {digest.observed_at_utc.isoformat()}")
    if digest.work_queue_status == "EMPTY_QUEUE":
        lines.append("Cola consultada correctamente: vacía.")
    elif digest.work_queue_status == "UNAVAILABLE":
        lines.append("Cola no disponible: la consulta falló; no inferir que está vacía.")
    elif digest.work_queue_status == "UNVERIFIED":
        lines.append("Cola no verificada; no inferir que está vacía.")
    if digest.source_state_id:
        lines.append(f"Control Master state: {digest.source_state_id}")
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
    if digest.top_work_queue_items:
        lines.append("Queue item provenance:")
        for item in digest.top_work_queue_items[:5]:
            item_parts = [
                f"id={item.get('item_id', '')}",
                f"priority={item.get('priority_label') or item.get('priority_score') or 'UNSPECIFIED'}",
                f"next={str(item.get('next_action') or '')[:80]}",
            ]
            if item.get("dependencies"):
                item_parts.append("deps=" + ",".join(item["dependencies"][:2]))
            if item.get("evidence_refs"):
                item_parts.append("evidence=" + ",".join(item["evidence_refs"][:2]))
            lines.append("- " + " ".join(item_parts))
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
        "top_work_queue_items",
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
