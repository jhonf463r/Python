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
from threading import local
from typing import TypeVar

from iabv_v15.domain.models import (
    ControlDecision,
    ControlMasterState,
    ControlRule,
    utc_now,
)
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_file,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


_CONTROL_MASTER_SUBDIR = "control_master"
T = TypeVar("T")


class ControlMasterRepository:
    """Thin atomic-JSON repository for Control Master artifacts."""

    def __init__(self, storage: ArtifactStorage) -> None:
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[object] | None:
        """Diagnostics for the most recent read on this thread."""
        return getattr(self._read_state, "report", None)

    def _remember_report(self, report: RepositoryReadReport[T]) -> RepositoryReadReport[T]:
        self._read_state.report = report
        return report

    def _single_report(self, result: ArtifactReadResult[T]) -> RepositoryReadReport[T]:
        return RepositoryReadReport.from_results("DIRECT_ARTIFACT_LOOKUP", [result])

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

    def load_latest_state_with_diagnostics(self) -> ArtifactReadResult[ControlMasterState]:
        path = self.storage.root / _CONTROL_MASTER_SUBDIR / "latest.json"
        result = read_model_file(path, "latest", ControlMasterState)
        self._remember_report(self._single_report(result))
        return result

    def load_latest_state(self) -> ControlMasterState | None:
        result = self.load_latest_state_with_diagnostics()
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND:
            return None
        report = self.last_read_report
        assert report is not None
        raise RepositoryReadError(report)

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

    def get_rule_with_diagnostics(self, rule_id: str) -> ArtifactReadResult[ControlRule]:
        path = self.storage.root / _CONTROL_MASTER_SUBDIR / "rules" / f"{rule_id}.json"
        result = read_model_file(path, rule_id, ControlRule)
        self._remember_report(self._single_report(result))
        return result

    def get_rule(self, rule_id: str) -> ControlRule | None:
        result = self.get_rule_with_diagnostics(rule_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND:
            return None
        report = self.last_read_report
        assert report is not None
        raise RepositoryReadError(report)

    def list_rules_with_diagnostics(self) -> RepositoryReadReport[ControlRule]:
        return self._list_model_artifacts("rules", ControlRule)

    def list_rules(self) -> list[ControlRule]:
        return self.list_rules_with_diagnostics().require_complete()

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def record_decision(self, decision: ControlDecision) -> ControlDecision:
        self.storage.save_json_atomic(
            f"{_CONTROL_MASTER_SUBDIR}/decisions/{decision.decision_id}.json",
            decision.model_dump(mode="json"),
        )
        return decision

    def get_decision_with_diagnostics(
        self, decision_id: str
    ) -> ArtifactReadResult[ControlDecision]:
        path = self.storage.root / _CONTROL_MASTER_SUBDIR / "decisions" / f"{decision_id}.json"
        result = read_model_file(path, decision_id, ControlDecision)
        self._remember_report(self._single_report(result))
        return result

    def get_decision(self, decision_id: str) -> ControlDecision | None:
        result = self.get_decision_with_diagnostics(decision_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND:
            return None
        report = self.last_read_report
        assert report is not None
        raise RepositoryReadError(report)

    def list_decisions_with_diagnostics(self) -> RepositoryReadReport[ControlDecision]:
        return self._list_model_artifacts("decisions", ControlDecision)

    def list_decisions(self) -> list[ControlDecision]:
        return self.list_decisions_with_diagnostics().require_complete()

    def _list_model_artifacts(
        self,
        subdirectory: str,
        model_type: type[T],
    ) -> RepositoryReadReport[T]:
        directory = self.storage.root / _CONTROL_MASTER_SUBDIR / subdirectory
        try:
            paths = sorted(
                path for path in directory.iterdir()
                if path.suffix == ".json"
            )
        except FileNotFoundError:
            return self._remember_report(
                RepositoryReadReport.from_results("DIRECTORY_LISTING", [])
            )
        except OSError as exc:
            report = RepositoryReadReport.from_collection_error("DIRECTORY_LISTING", exc)
            return self._remember_report(report)

        results = [
            read_model_file(path, path.stem, model_type)
            for path in paths
        ]
        return self._remember_report(
            RepositoryReadReport.from_results("DIRECTORY_LISTING", results)
        )


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
