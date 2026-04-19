"""Integracion: bootstrap expone el servicio, el digest alimenta SystemPromptBuilder,
y el contrato no depende del historial completo del chat."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ControlMasterState,
    ControlRule,
    ControlRuleSeverity,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
)
from iabv_v15.services.evolution.control_master_digest_builder import (
    ControlMasterDigestBuilder,
    render_digest_markdown,
)
from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / "data" / "test_runs"
    base.mkdir(parents=True, exist_ok=True)
    root = base / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_bootstrap_wires_control_master_service_and_digest_builder() -> None:
    root = _workspace("control_master_bootstrap")
    try:
        boot = AppBootstrap(str(root))
        assert boot.control_master_service is not None
        assert boot.control_master_repository is not None
        assert boot.control_master_digest_builder is not None
        # The service composes existing repos, not fresh duplicates.
        assert boot.control_master_service.objective_repository is boot.objective_repository
        assert boot.control_master_service.pending_issue_repository is boot.pending_issue_repository
        assert boot.control_master_service.self_examination_service is boot.operational_self_examination_service
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_digest_feeds_system_prompt_builder_via_governance_rules() -> None:
    """SystemPromptBuilder already exposes a `governance_rules: dict` parameter.

    The digest (as a dict) must be injectable there without breaking the
    existing prompt contract.
    """

    builder = ControlMasterDigestBuilder()
    state = ControlMasterState(
        current_vision="Vivo y gobernable",
        global_rules=[
            ControlRule(title="No duplicar cerebro", severity=ControlRuleSeverity.IRREVOCABLE),
        ],
    )
    digest = builder.build(state)
    prompt = SystemPromptBuilder().build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
        governance_rules=digest.model_dump(mode="json"),
    )
    assert "Reglas de gobernanza" in prompt
    # The prompt must still fit the ~4 k-token budget.
    assert len(prompt) <= 15_000


def test_digest_markdown_can_be_appended_to_system_prompt_without_overflow() -> None:
    """The markdown projection is what the local chat would actually inject."""
    state = ControlMasterState(
        current_vision="v",
        global_rules=[ControlRule(title=f"R{i}", severity=ControlRuleSeverity.STRICT) for i in range(50)],
    )
    markdown = render_digest_markdown(ControlMasterDigestBuilder().build(state))
    assert len(markdown) < 3_000
    assert "Control Maestro" in markdown


def test_control_master_state_is_stateless_about_chat_history() -> None:
    """Core contract: governance state never carries chat messages."""
    fields = set(ControlMasterState.model_fields.keys())
    forbidden = {"chat_history", "messages", "transcript", "history"}
    assert fields.isdisjoint(forbidden)


def test_service_current_state_projects_live_objectives_via_real_bootstrap() -> None:
    root = _workspace("control_master_live_objectives")
    try:
        boot = AppBootstrap(str(root))
        node = boot.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title="Cerrar capa control maestro",
                status=ObjectiveStatus.ACTIVE,
            )
        )
        boot.control_master_service.record_decision(
            ControlDecision(
                summary="Consolidar capa control maestro",
                status=ControlDecisionStatus.ACCEPTED,
                related_objective_ids=[node.objective_id],
            )
        )
        state = boot.control_master_service.current_state()
        assert node.objective_id in state.active_objective_ids
        assert state.recent_decisions
        assert state.recent_decisions[0].summary == "Consolidar capa control maestro"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_seed_from_agents_md_via_bootstrap_is_idempotent() -> None:
    root = _workspace("control_master_seed_bootstrap")
    try:
        boot = AppBootstrap(str(root))
        agents_md = Path(__file__).resolve().parents[1] / "AGENTS.md"
        first = boot.control_master_service.seed_from_agents_md(agents_md)
        second = boot.control_master_service.seed_from_agents_md(agents_md)
        assert first == second > 0
        state = boot.control_master_service.current_state()
        assert len(state.global_rules) == first
    finally:
        shutil.rmtree(root, ignore_errors=True)
