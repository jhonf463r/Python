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

    def list_children(
        self,
        parent_id: str,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        limit: int = 40,
    ) -> list[ObjectiveNode]:
        out: list[ObjectiveNode] = []
        for node in self._items.values():
            if node.parent_id != parent_id:
                continue
            if kind is not None and node.kind != kind:
                continue
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


# ----------------------------------------------------------------------
# Auto-close: when every direct child is COMPLETED, the parent closes
# automatically so the digest reflects the real state without manual PRs.
# ----------------------------------------------------------------------


def _make_tree(objectives: _FakeObjectiveRepository) -> tuple[ObjectiveNode, list[ObjectiveNode]]:
    root = objectives.save(
        ObjectiveNode(
            objective_id="obj-root",
            kind=ObjectiveNodeKind.OBJECTIVE,
            title="super sync root",
            status=ObjectiveStatus.ACTIVE,
        )
    )
    children = [
        objectives.save(
            ObjectiveNode(
                objective_id=f"obj-child-{i}",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title=f"super sync child {i}",
                status=ObjectiveStatus.ACTIVE,
                parent_id=root.objective_id,
                root_id=root.objective_id,
            )
        )
        for i in range(1, 4)
    ]
    return root, children


def test_auto_close_root_when_all_children_complete() -> None:
    root = _workspace()
    try:
        service, objectives = _build_service(root)
        root_node, children = _make_tree(objectives)
        # Close the first two children: root stays ACTIVE.
        service.mark_objective(children[0].objective_id, "completed")
        service.mark_objective(children[1].objective_id, "completed")
        assert objectives.get(root_node.objective_id).status == ObjectiveStatus.ACTIVE
        # Closing the last child auto-closes the root with an audit note.
        service.mark_objective(children[2].objective_id, "completed", note="manual")
        parent = objectives.get(root_node.objective_id)
        assert parent.status == ObjectiveStatus.COMPLETED
        notes = parent.metadata.get("control_master_notes", [])
        assert any("auto-closed" in n["note"] for n in notes)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_close_respects_non_completed_siblings() -> None:
    root = _workspace()
    try:
        service, objectives = _build_service(root)
        root_node, children = _make_tree(objectives)
        service.mark_objective(children[0].objective_id, "completed")
        service.mark_objective(children[1].objective_id, "blocked")
        service.mark_objective(children[2].objective_id, "completed")
        # root must stay ACTIVE because child 1 is blocked, not completed.
        assert objectives.get(root_node.objective_id).status == ObjectiveStatus.ACTIVE
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_close_leaves_paused_parent_alone() -> None:
    root = _workspace()
    try:
        service, objectives = _build_service(root)
        root_node, children = _make_tree(objectives)
        # User explicitly paused the root before children finished.
        service.mark_objective(root_node.objective_id, "paused", note="on hold")
        for child in children:
            service.mark_objective(child.objective_id, "completed")
        # Auto-close must NOT override the user's paused decision.
        parent = objectives.get(root_node.objective_id)
        assert parent.status == ObjectiveStatus.PAUSED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_close_walks_up_multiple_levels() -> None:
    root = _workspace()
    try:
        service, objectives = _build_service(root)
        grand = objectives.save(
            ObjectiveNode(
                objective_id="obj-grand",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="grandparent",
                status=ObjectiveStatus.ACTIVE,
            )
        )
        parent = objectives.save(
            ObjectiveNode(
                objective_id="obj-parent",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="parent",
                status=ObjectiveStatus.ACTIVE,
                parent_id=grand.objective_id,
                root_id=grand.objective_id,
            )
        )
        leaf = objectives.save(
            ObjectiveNode(
                objective_id="obj-leaf",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="leaf",
                status=ObjectiveStatus.ACTIVE,
                parent_id=parent.objective_id,
                root_id=grand.objective_id,
            )
        )
        service.mark_objective(leaf.objective_id, "completed")
        # parent closes because its only child is completed; then
        # grandparent closes because its only child (parent) is completed.
        assert objectives.get(parent.objective_id).status == ObjectiveStatus.COMPLETED
        assert objectives.get(grand.objective_id).status == ObjectiveStatus.COMPLETED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_close_passes_explicit_large_limit_to_list_children() -> None:
    """ObjectiveRepository.list_children defaults to 40; auto-close needs ALL children.

    Devin Review flagged that relying on the default limit could miss
    uncompleted siblings on parents with >40 direct children. Assert the
    service passes an explicit large limit.
    """

    root = _workspace()
    try:
        service, objectives = _build_service(root)
        root_node = objectives.save(
            ObjectiveNode(
                objective_id="obj-big-root",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="big root",
                status=ObjectiveStatus.ACTIVE,
            )
        )

        observed: list[dict[str, object]] = []
        original = objectives.list_children

        def spy_list_children(parent_id: str, **kwargs: object) -> list[ObjectiveNode]:
            observed.append({"parent_id": parent_id, **kwargs})
            return original(parent_id, **kwargs)

        object.__setattr__(objectives, "list_children", spy_list_children)

        last = None
        for i in range(3):
            last = objectives.save(
                ObjectiveNode(
                    objective_id=f"obj-big-child-{i}",
                    kind=ObjectiveNodeKind.OBJECTIVE,
                    title=f"big child {i}",
                    status=ObjectiveStatus.ACTIVE,
                    parent_id=root_node.objective_id,
                    root_id=root_node.objective_id,
                )
            )

        for i in range(3):
            service.mark_objective(f"obj-big-child-{i}", "completed")

        assert objectives.get(root_node.objective_id).status == ObjectiveStatus.COMPLETED
        # At least one call must have been made with an explicit limit that
        # dwarfs the default 40 display cap.
        assert any(
            call.get("limit", 0) >= 1000 for call in observed
        ), f"expected explicit large limit, saw: {observed}"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_close_respects_visited_set_to_prevent_cycles() -> None:
    """The visited guard is defense-in-depth next to the ACTIVE guard.

    Devin Review flagged that routing recursion through ``mark_objective``
    reset the visited set (making it dead code). Fix threaded the set
    through direct recursion. Assert the guard works by invoking the
    private helper with the target already marked visited — it must bail
    out without closing the otherwise-eligible parent.
    """

    root = _workspace()
    try:
        service, objectives = _build_service(root)
        parent = objectives.save(
            ObjectiveNode(
                objective_id="obj-visited-parent",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="parent",
                status=ObjectiveStatus.ACTIVE,
            )
        )
        child = objectives.save(
            ObjectiveNode(
                objective_id="obj-visited-child",
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="child already completed",
                status=ObjectiveStatus.COMPLETED,
                parent_id=parent.objective_id,
            )
        )
        # Preload parent in visited set → helper must bail out *before*
        # closing it, even though its only child is completed.
        service._auto_close_ancestors_if_children_done(
            parent.objective_id, {parent.objective_id}
        )
        assert objectives.get(parent.objective_id).status == ObjectiveStatus.ACTIVE
        # Sanity: without preloading, the helper would have closed it.
        service._auto_close_ancestors_if_children_done(parent.objective_id, set())
        assert objectives.get(parent.objective_id).status == ObjectiveStatus.COMPLETED
        # Irrelevant child kept for scope clarity in the assertion above.
        assert objectives.get(child.objective_id).status == ObjectiveStatus.COMPLETED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_close_is_safe_when_repository_has_no_list_children() -> None:
    """Legacy repositories without ``list_children`` must keep working."""

    root = _workspace()
    try:
        service, objectives = _build_service(root)
        # Monkeypatch: strip list_children to simulate a legacy repo.
        object.__setattr__(objectives, "list_children", None)
        node = objectives.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="orphan completion",
                status=ObjectiveStatus.ACTIVE,
                parent_id="obj-missing-parent",
            )
        )
        updated = service.mark_objective(node.objective_id, "completed")
        assert updated is not None
        assert updated.status == ObjectiveStatus.COMPLETED
    finally:
        shutil.rmtree(root, ignore_errors=True)
