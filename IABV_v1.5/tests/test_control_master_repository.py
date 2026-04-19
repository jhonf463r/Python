"""Persistencia atomica + history + rules/decisions del control maestro."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ControlMasterState,
    ControlRule,
    ControlRuleSeverity,
)
from iabv_v15.infra.persistence.control_master_repository import (
    ControlMasterRepository,
    render_state_markdown,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _storage() -> tuple[ArtifactStorage, Path]:
    root = Path(__file__).resolve().parents[1] / "data" / "test_runs" / f"cm_repo_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return ArtifactStorage(str(root)), root


def test_save_state_writes_latest_history_and_markdown() -> None:
    storage, root = _storage()
    try:
        repo = ControlMasterRepository(storage)
        state = ControlMasterState(current_vision="Vivo y gobernable")
        repo.save_state(state)
        assert (root / "control_master" / "latest.json").exists()
        assert (root / "control_master" / "latest.md").exists()
        history = list((root / "control_master" / "history").iterdir())
        assert len(history) == 1

        loaded = repo.load_latest_state()
        assert loaded is not None
        assert loaded.current_vision == "Vivo y gobernable"
        assert loaded.state_id == state.state_id

        text = (root / "control_master" / "latest.md").read_text(encoding="utf-8")
        assert "Vivo y gobernable" in text
        assert "Control Maestro" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_save_state_creates_multiple_history_snapshots() -> None:
    storage, root = _storage()
    try:
        repo = ControlMasterRepository(storage)
        repo.save_state(ControlMasterState(current_vision="v1"))
        repo.save_state(ControlMasterState(current_vision="v2"))
        history_dir = root / "control_master" / "history"
        snapshots = list(history_dir.iterdir())
        assert len(snapshots) == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_rules_upsert_and_list_roundtrip() -> None:
    storage, root = _storage()
    try:
        repo = ControlMasterRepository(storage)
        rule = ControlRule(
            title="No duplicar cerebro",
            severity=ControlRuleSeverity.IRREVOCABLE,
            source_refs=["AGENTS.md#contratos"],
        )
        repo.upsert_rule(rule)
        fetched = repo.get_rule(rule.rule_id)
        assert fetched is not None
        assert fetched.title == "No duplicar cerebro"
        all_rules = repo.list_rules()
        assert [r.rule_id for r in all_rules] == [rule.rule_id]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_decisions_upsert_and_list_roundtrip() -> None:
    storage, root = _storage()
    try:
        repo = ControlMasterRepository(storage)
        decision = ControlDecision(
            summary="Consolidar capa control maestro",
            status=ControlDecisionStatus.ACCEPTED,
            affected_modules=["services/evolution"],
        )
        repo.record_decision(decision)
        fetched = repo.get_decision(decision.decision_id)
        assert fetched is not None
        assert fetched.summary == "Consolidar capa control maestro"
        all_decisions = repo.list_decisions()
        assert [d.decision_id for d in all_decisions] == [decision.decision_id]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_render_state_markdown_has_all_governance_sections() -> None:
    state = ControlMasterState(
        current_vision="Vision viva",
        global_rules=[ControlRule(title="Regla X", severity=ControlRuleSeverity.STRICT)],
        unresolved_items=["item-a"],
        evidence_links=["AGENTS.md"],
    )
    text = render_state_markdown(state)
    for heading in (
        "# IABV v1.5 - Control Maestro",
        "## Vision actual",
        "## Reglas globales",
        "## UNRESOLVED",
        "## Evidencia",
    ):
        assert heading in text
    assert "Regla X" in text
    assert "item-a" in text
