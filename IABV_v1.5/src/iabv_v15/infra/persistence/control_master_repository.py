"""Persistence for the Control Master governance layer.

Stores `ControlMasterState`, `ControlRule` and `ControlDecision` as
atomic JSON artifacts under ``data/evolution/control_master/``:

- ``latest.json``            -> most recent `ControlMasterState`.
- ``latest.md``              -> readable markdown projection.
- ``history/<ts>.json``      -> versioned snapshots.
- ``rules/<rule_id>.json``   -> individual rules (for direct lookup).
- ``decisions/<decision_id>.json`` -> individual decisions.

The repository only persists governance artifacts; live projections
(objectives, backlog, risks) are rebuilt from their source repos by
`ControlMasterService` and never stored twice.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    ControlDecision,
    ControlMasterState,
    ControlRule,
    utc_now,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


_CONTROL_MASTER_SUBDIR = "control_master"


class ControlMasterRepository:
    """Thin atomic-JSON repository for Control Master artifacts."""

    def __init__(self, storage: ArtifactStorage) -> None:
        self.storage = storage

    # ------------------------------------------------------------------
    # State (composite)
    # ------------------------------------------------------------------

    def save_state(self, state: ControlMasterState) -> ControlMasterState:
        payload = state.model_dump(mode="json")
        self.storage.save_json_atomic(
            f"{_CONTROL_MASTER_SUBDIR}/latest.json", payload
        )
        history_name = _timestamp_slug(state.last_updated) + ".json"
        self.storage.save_json_atomic(
            f"{_CONTROL_MASTER_SUBDIR}/history/{history_name}", payload
        )
        markdown = render_state_markdown(state)
        self.storage.save_bytes(
            f"{_CONTROL_MASTER_SUBDIR}/latest.md", markdown.encode("utf-8")
        )
        return state

    def load_latest_state(self) -> ControlMasterState | None:
        relative = f"{_CONTROL_MASTER_SUBDIR}/latest.json"
        if not self.storage.exists(relative):
            return None
        payload = self.storage.load_json(relative)
        return ControlMasterState.model_validate(payload)

    def list_history(self) -> list[str]:
        directory = f"{_CONTROL_MASTER_SUBDIR}/history"
        return self.storage.list(directory)

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def upsert_rule(self, rule: ControlRule) -> ControlRule:
        self.storage.save_json_atomic(
            f"{_CONTROL_MASTER_SUBDIR}/rules/{rule.rule_id}.json",
            rule.model_dump(mode="json"),
        )
        return rule

    def get_rule(self, rule_id: str) -> ControlRule | None:
        relative = f"{_CONTROL_MASTER_SUBDIR}/rules/{rule_id}.json"
        if not self.storage.exists(relative):
            return None
        return ControlRule.model_validate(self.storage.load_json(relative))

    def list_rules(self) -> list[ControlRule]:
        directory = f"{_CONTROL_MASTER_SUBDIR}/rules"
        items = self.storage.list(directory)
        rules: list[ControlRule] = []
        for absolute_path in items:
            path = Path(absolute_path)
            if path.suffix != ".json":
                continue
            rules.append(ControlRule.model_validate_json(path.read_text(encoding="utf-8")))
        return rules

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def record_decision(self, decision: ControlDecision) -> ControlDecision:
        self.storage.save_json_atomic(
            f"{_CONTROL_MASTER_SUBDIR}/decisions/{decision.decision_id}.json",
            decision.model_dump(mode="json"),
        )
        return decision

    def get_decision(self, decision_id: str) -> ControlDecision | None:
        relative = f"{_CONTROL_MASTER_SUBDIR}/decisions/{decision_id}.json"
        if not self.storage.exists(relative):
            return None
        return ControlDecision.model_validate(self.storage.load_json(relative))

    def list_decisions(self) -> list[ControlDecision]:
        directory = f"{_CONTROL_MASTER_SUBDIR}/decisions"
        items = self.storage.list(directory)
        decisions: list[ControlDecision] = []
        for absolute_path in items:
            path = Path(absolute_path)
            if path.suffix != ".json":
                continue
            decisions.append(ControlDecision.model_validate_json(path.read_text(encoding="utf-8")))
        return decisions


def _timestamp_slug(ts: datetime | None = None) -> str:
    if ts is None:
        ts = utc_now()
    return ts.strftime("%Y%m%dT%H%M%S_%f")


def render_state_markdown(state: ControlMasterState) -> str:
    """Markdown projection of a ControlMasterState.

    Follows the readability pattern of ``portable_context/latest.md``
    but narrows the scope to governance.
    """

    lines: list[str] = []
    lines.append("# IABV v1.5 - Control Maestro")
    lines.append("")
    lines.append(f"Generado: {state.last_updated.isoformat()}")
    lines.append(f"Version: {state.version}")
    lines.append("")
    lines.append("## Vision actual")
    lines.append(state.current_vision or "(sin vision registrada)")
    lines.append("")

    lines.append("## Objetivos")
    lines.append(f"- Activos: {len(state.active_objective_ids)}")
    lines.append(f"- Completados: {len(state.completed_objective_ids)}")
    lines.append(f"- Pausados: {len(state.paused_objective_ids)}")
    lines.append(f"- Descartados: {len(state.discarded_objective_ids)}")
    lines.append("")

    lines.append("## Reglas globales")
    if state.global_rules:
        for rule in state.global_rules:
            lines.append(
                f"- [{rule.severity.value}] **{rule.title}** ({rule.status.value})"
            )
            if rule.description:
                lines.append(f"  - {rule.description}")
            if rule.source_refs:
                lines.append(f"  - refs: {', '.join(rule.source_refs)}")
    else:
        lines.append("(sin reglas registradas)")
    lines.append("")

    lines.append("## Backlog tecnico")
    if state.technical_backlog:
        for item in state.technical_backlog[:10]:
            title = item.get("title") or item.get("summary") or item.get("id") or ""
            lines.append(f"- {title}")
    else:
        lines.append("(sin backlog persistido)")
    lines.append("")

    lines.append("## Decisiones recientes")
    if state.recent_decisions:
        for decision in state.recent_decisions[:10]:
            lines.append(
                f"- [{decision.status.value}] {decision.summary} ({decision.timestamp.isoformat()})"
            )
            if decision.reason:
                lines.append(f"  - razon: {decision.reason}")
    else:
        lines.append("(sin decisiones registradas)")
    lines.append("")

    lines.append("## Riesgos actuales")
    if state.current_risks:
        for risk in state.current_risks[:10]:
            title = risk.get("title") or risk.get("summary") or ""
            severity = risk.get("severity") or ""
            lines.append(f"- [{severity}] {title}")
    else:
        lines.append("(sin riesgos registrados)")
    lines.append("")

    lines.append("## Estado de tests")
    tests_state = state.current_tests_state or {}
    if tests_state:
        for key, value in tests_state.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("(sin snapshot de tests)")
    lines.append("")

    lines.append("## UNRESOLVED")
    if state.unresolved_items:
        for item in state.unresolved_items:
            lines.append(f"- {item}")
    else:
        lines.append("(sin items UNRESOLVED)")
    lines.append("")

    if state.evidence_links:
        lines.append("## Evidencia")
        for link in state.evidence_links:
            lines.append(f"- {link}")
        lines.append("")

    return "\n".join(lines)


_ = Any  # keep typing import referenced for future extensions
