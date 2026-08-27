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


def test_bootstrap_auto_seeds_agents_md_when_available() -> None:
    """The bootstrap should idempotently seed governance rules from AGENTS.md at startup."""
    root = _workspace("control_master_auto_seed")
    try:
        boot = AppBootstrap(str(root))
        rules = boot.control_master_service.repository.list_rules()
        # AGENTS.md sits in repo root; auto-seed should have produced at least one rule.
        assert len(rules) > 0, "Expected AGENTS.md auto-seed to register rules at bootstrap"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orchestrator_exposes_control_master_dependencies_after_bootstrap() -> None:
    """The orchestrator must reach the governance digest without user wiring."""
    root = _workspace("control_master_orchestrator_wiring")
    try:
        boot = AppBootstrap(str(root))
        orch = boot.adaptive_task_orchestrator
        assert orch.control_master_service is boot.control_master_service
        assert orch.control_master_digest_builder is boot.control_master_digest_builder
        digest = orch._control_master_digest()
        assert digest is not None
        assert hasattr(digest, "current_vision")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orchestrator_digest_helper_is_safe_without_service() -> None:
    """Defensive: orchestrator must tolerate missing control master service."""
    root = _workspace("control_master_orchestrator_safe")
    try:
        boot = AppBootstrap(str(root))
        orch = boot.adaptive_task_orchestrator
        orch.control_master_service = None
        assert orch._control_master_digest() is None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_export_control_master_digest_returns_json_dict() -> None:
    root = _workspace("control_master_export_digest")
    try:
        boot = AppBootstrap(str(root))
        boot.control_master_service.set_vision("Vision persistida para export")
        payload = boot.export_control_master_digest()
        assert isinstance(payload, dict)
        assert payload.get("current_vision") == "Vision persistida para export"
        assert "rules_brief" in payload
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orchestrator_digest_preserves_persisted_vision() -> None:
    """Regression: the orchestrator helper must not drop fields like current_vision.

    Previously the helper called current_state(refresh=True) which skipped the
    persisted base state and left current_vision/current_tests_state/
    evidence_links/metadata at their empty defaults.
    """
    root = _workspace("control_master_orchestrator_vision")
    try:
        boot = AppBootstrap(str(root))
        boot.control_master_service.set_vision("Vision gobernable viva")
        digest = boot.adaptive_task_orchestrator._control_master_digest()
        assert digest is not None
        assert digest.current_vision == "Vision gobernable viva"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_r10_production_integration_structured_need_in_work_queue() -> None:
    """R10.3: Verify production bootstrap wires StructuredNeedRepository to ControlMasterService.

    This test proves the REAL production construction path, not manual dependency injection.
    It verifies:
    1. ControlMasterService receives StructuredNeedRepository from bootstrap
    2. A real pending StructuredNeed can be created through the repository
    3. current_work_queue() includes the StructuredNeed-derived item
    4. Provenance (need_id, source_finding_id) is preserved
    5. Deterministic priority projection works
    """
    from iabv_v15.domain.models import StructuredNeed, NeedStatus

    root = _workspace("r10_production_integration")
    try:
        boot = AppBootstrap(str(root))
        
        # Verify production wiring: ControlMasterService has StructuredNeedRepository
        assert boot.control_master_service.structured_need_repository is not None
        assert boot.control_master_service.structured_need_repository is boot.operational_self_examination_service.structured_need_repository
        
        repo = boot.control_master_service.structured_need_repository
        
        # Create a real pending StructuredNeed through the repository
        test_need = StructuredNeed(
            source_finding_id="test_finding_123",
            category="capability_gap",
            capability_gap="Missing test capability",
            current_state="Not implemented",
            desired_state="Fully implemented",
            knowledge_required="Test knowledge",
            reason="R10.3 production integration test",
            evidence=["Evidence item 1"],
            priority="high",
            status=NeedStatus.PENDING,
        )
        
        persisted_need = repo.upsert(test_need)
        assert persisted_need.need_id == test_need.need_id
        assert persisted_need.status == NeedStatus.PENDING
        
        # Call the REAL current_work_queue() from production ControlMasterService
        queue = boot.control_master_service.current_work_queue(limit=20)
        
        # Verify the queue contains the StructuredNeed-derived item
        need_item_id = f'need:{persisted_need.need_id}'
        matching_items = [item for item in queue if item.get('item_id') == need_item_id]
        assert len(matching_items) == 1, f"Expected 1 item with id {need_item_id}, got {len(matching_items)}"
        
        item = matching_items[0]
        
        # Verify provenance
        assert item['source'] == 'structured_need_repository'
        assert persisted_need.source_finding_id in item.get('evidence_refs', [])
        
        # Verify deterministic priority projection
        assert 'priority_score' in item
        assert item['priority_score'] > 0
        assert 'score_breakdown' in item
        
        # Verify the item contains expected fields
        assert item['title'] == test_need.capability_gap
        assert item['status'] == NeedStatus.PENDING.value
        
        # Clean up: delete the test need
        repo.update_status(persisted_need.need_id, NeedStatus.RESOLVED)
        
    finally:
        shutil.rmtree(root, ignore_errors=True)
