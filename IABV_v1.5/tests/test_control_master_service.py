"""ControlMasterService: vision, rules, decisions, mark_objective, seed idempotente."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ControlRule,
    ControlRuleSeverity,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
)
from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.control_master_service import (
    ControlMasterService,
    _deterministic_rule_id,
)


class _FakeObjectiveRepository:
    def __init__(self) -> None:
        self._items: dict[str, ObjectiveNode] = {}

    def save(self, node: ObjectiveNode) -> ObjectiveNode:
        self._items[node.objective_id] = node
        return node

    def get(self, objective_id: str) -> ObjectiveNode | None:
        return self._items.get(objective_id)

    def list_recent(
        self,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[ObjectiveNode]:
        out: list[ObjectiveNode] = []
        for node in self._items.values():
            if status is not None and node.status != status:
                continue
            out.append(node)
        return out[:limit]


class _FakePendingIssueRepository:
    def __init__(self, items: list[dict]) -> None:
        self._items = items

    def list_recent(self) -> list[dict]:
        return list(self._items)


class _FakeSelfExaminationService:
    def __init__(self, snapshot) -> None:
        self._snapshot = snapshot

    def current_snapshot(self):
        return self._snapshot


def _workspace() -> Path:
    root = Path(__file__).resolve().parents[1] / "data" / "test_runs" / f"cm_svc_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_service(root: Path) -> tuple[ControlMasterService, _FakeObjectiveRepository]:
    storage = ArtifactStorage(str(root))
    repo = ControlMasterRepository(storage)
    objectives = _FakeObjectiveRepository()
    service = ControlMasterService(
        repository=repo,
        objective_repository=objectives,
        pending_issue_repository=_FakePendingIssueRepository(
            [{"title": "Refactorizar X"}, {"title": "Cerrar Y"}]
        ),
    )
    return service, objectives


def test_current_state_is_empty_when_nothing_saved() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        state = service.current_state()
        assert state.current_vision == ""
        assert state.global_rules == []
        assert state.recent_decisions == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_set_vision_persists_and_includes_evidence() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        service.set_vision("Vivo y gobernable", evidence=["AGENTS.md"])
        state = service.current_state()
        assert state.current_vision == "Vivo y gobernable"
        assert "AGENTS.md" in state.evidence_links
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_upsert_rule_is_idempotent_by_id_and_preserves_created_at() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        rule = ControlRule(
            rule_id="rule-1",
            title="No romper contratos",
            severity=ControlRuleSeverity.IRREVOCABLE,
        )
        saved_first = service.upsert_rule(rule)
        updated = rule.model_copy(update={"description": "descripcion ampliada"})
        saved_second = service.upsert_rule(updated)
        assert saved_first.created_at_utc == saved_second.created_at_utc
        assert saved_second.updated_at_utc >= saved_first.updated_at_utc
        assert saved_second.description == "descripcion ampliada"

        state = service.current_state()
        assert len(state.global_rules) == 1
        assert state.global_rules[0].description == "descripcion ampliada"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_record_decision_shows_in_recent_decisions() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        decision = ControlDecision(
            summary="Consolidar capa control maestro",
            status=ControlDecisionStatus.ACCEPTED,
        )
        service.record_decision(decision)
        state = service.current_state()
        assert [d.decision_id for d in state.recent_decisions] == [decision.decision_id]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_mark_objective_updates_repository_and_records_note() -> None:
    root = _workspace()
    try:
        service, objectives = _build_service(root)
        node = objectives.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="Consolidar memoria portable",
                status=ObjectiveStatus.ACTIVE,
            )
        )
        updated = service.mark_objective(node.objective_id, "completed", note="cerrado en PR")
        assert updated is not None
        assert updated.status == ObjectiveStatus.COMPLETED
        notes = updated.metadata.get("control_master_notes", [])
        assert notes and notes[0]["note"] == "cerrado en PR"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_mark_objective_discarded_uses_tag_to_preserve_enum() -> None:
    root = _workspace()
    try:
        service, objectives = _build_service(root)
        node = objectives.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="Idea descartada",
                status=ObjectiveStatus.ACTIVE,
            )
        )
        updated = service.mark_objective(node.objective_id, "discarded")
        assert updated is not None
        assert updated.status == ObjectiveStatus.PAUSED
        assert "discarded" in updated.tags
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_mark_unresolved_deduplicates() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        service.mark_unresolved("falta observar Codex vivo")
        service.mark_unresolved("falta observar Codex vivo")
        state = service.current_state()
        assert state.unresolved_items.count("falta observar Codex vivo") == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_seed_from_agents_md_is_idempotent() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        agents_md = Path(__file__).resolve().parents[1] / "AGENTS.md"
        first_count = service.seed_from_agents_md(agents_md)
        second_count = service.seed_from_agents_md(agents_md)
        assert first_count == second_count
        assert first_count > 0
        state = service.current_state()
        assert len(state.global_rules) == first_count
        # At least one rule should be IRREVOCABLE (from "Contratos Que No Debes Romper").
        irrevocables = [r for r in state.global_rules if r.severity == ControlRuleSeverity.IRREVOCABLE]
        assert irrevocables, "Se esperaba al menos una regla IRREVOCABLE desde AGENTS.md"
        # And every rule must carry a source ref pointing back to AGENTS.md.
        for rule in state.global_rules:
            assert any(ref.startswith("AGENTS.md#") for ref in rule.source_refs)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deterministic_rule_id_is_stable_per_title() -> None:
    assert _deterministic_rule_id("No duplicar cerebro") == _deterministic_rule_id("No duplicar cerebro")
    assert _deterministic_rule_id("No duplicar cerebro").startswith("rule-")
    assert _deterministic_rule_id("A") != _deterministic_rule_id("B")


def test_technical_backlog_is_projected_from_pending_issues() -> None:
    root = _workspace()
    try:
        service, _ = _build_service(root)
        state = service.current_state()
        titles = [item.get("title") for item in state.technical_backlog]
        assert titles == ["Refactorizar X", "Cerrar Y"]
    finally:
        shutil.rmtree(root, ignore_errors=True)
