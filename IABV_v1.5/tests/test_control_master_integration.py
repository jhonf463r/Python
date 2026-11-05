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
    _EXPECTED_WORK_QUEUE_SOURCE_KEYS,
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
        digest = orch._control_master_digest()
        assert digest is not None
        assert digest.signal_status == "UNAVAILABLE"
        assert digest.work_queue_status == "UNAVAILABLE"
        assert digest.control_master_signal_status == "UNAVAILABLE"
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


def test_export_control_master_digest_queue_exception_is_not_empty() -> None:
    root = _workspace("control_master_export_queue_failure")
    try:
        boot = AppBootstrap(str(root))
        boot.control_master_service.set_vision("Vision de prueba con cola no disponible")

        def _raise_queue_error(*, limit: int = 10):
            raise RuntimeError("queue unavailable")

        boot.control_master_service.current_work_queue = _raise_queue_error
        payload = boot.export_control_master_digest()

        assert payload["signal_status"] == "AVAILABLE"
        assert payload["work_queue_status"] == "UNAVAILABLE"
        assert payload["control_master_signal_status"] == "FRESH"
        assert payload["work_queue_brief"] == []
        assert "CONTROL_MASTER_QUEUE_READ_FAILED:RuntimeError" == payload["signal_reason"]
    finally:
        shutil.rmtree(root, ignore_errors=True)



def _state_with_source_provenance(state_id: str, source_digest: str) -> ControlMasterState:
    from datetime import datetime, timezone

    observed_at = datetime.now(timezone.utc)
    return ControlMasterState(
        current_vision='Vision from one persisted state',
        metadata={
            '_space_time_control_master_source_provenance': {
                'read_status': 'READ_OK',
                'freshness_status': 'FRESH',
                'source_state_id': state_id,
                'source_revision_or_digest': source_digest,
                'source_generated_at_utc': observed_at.isoformat(),
                'source_observed_at_utc': observed_at.isoformat(),
                'workspace_scope_id': 'scope-test',
            },
        },
    )


class _DigestQueueService:
    def __init__(self, states: list[ControlMasterState]) -> None:
        self._states = list(states)
        self.state_reads = 0
        self.last_work_queue_errors: tuple[str, ...] = ()
        self.last_work_queue_source_coverage = {
            source: 'READ_OK' for source in _EXPECTED_WORK_QUEUE_SOURCE_KEYS
        }

    def current_state(self, *, refresh: bool = False) -> ControlMasterState:
        self.state_reads += 1
        index = min(self.state_reads - 1, len(self._states) - 1)
        return self._states[index]

    def current_work_queue(self, *, limit: int = 10) -> list[dict]:
        return [{
            'id': 'task-1',
            'title': 'Synthetic work item',
            'status': 'pending',
            'priority_score': 10,
            'priority_label': 'HIGH',
            'source': 'objective_repository',
            'next_action': 'Inspect evidence',
            'evidence_refs': ['objective:task-1'],
        }][:limit]


def test_digest_marks_work_queue_unverified_when_state_changes_during_projection() -> None:
    service = _DigestQueueService([
        _state_with_source_provenance('state-1', 'sha256:before'),
        _state_with_source_provenance('state-2', 'sha256:after'),
    ])

    digest = ControlMasterDigestBuilder().build_from_service(service)

    assert service.state_reads == 2
    assert digest.work_queue_status == 'UNVERIFIED'
    assert digest.work_queue_brief == []
    assert digest.top_work_queue_items == []
    assert digest.signal_reason == 'CONTROL_MASTER_STATE_CHANGED_DURING_WORK_QUEUE_READ'
    assert digest.source_state_id == 'state-2'


def test_digest_detects_state_content_change_without_state_id_change() -> None:
    service = _DigestQueueService([
        _state_with_source_provenance('state-1', 'sha256:before'),
        _state_with_source_provenance('state-1', 'sha256:after'),
    ])

    digest = ControlMasterDigestBuilder().build_from_service(service)

    assert digest.work_queue_status == 'UNVERIFIED'
    assert digest.top_work_queue_items == []
    assert digest.signal_reason == 'CONTROL_MASTER_STATE_CHANGED_DURING_WORK_QUEUE_READ'


def test_digest_fails_closed_when_state_recheck_fails() -> None:
    class RecheckFails(_DigestQueueService):
        def current_state(self, *, refresh: bool = False) -> ControlMasterState:
            self.state_reads += 1
            if self.state_reads == 1:
                return _state_with_source_provenance('state-1', 'sha256:before')
            raise PermissionError('synthetic state recheck failure')

    digest = ControlMasterDigestBuilder().build_from_service(RecheckFails([]))

    assert digest.signal_status == 'UNAVAILABLE'
    assert digest.work_queue_status == 'UNAVAILABLE'
    assert digest.work_queue_brief == []
    assert 'CONTROL_MASTER_STATE_RECHECK_FAILED:PermissionError' == digest.signal_reason


def test_digest_preserves_queue_when_state_is_stable_during_projection() -> None:
    service = _DigestQueueService([
        _state_with_source_provenance('state-1', 'sha256:stable'),
        _state_with_source_provenance('state-1', 'sha256:stable'),
    ])

    digest = ControlMasterDigestBuilder().build_from_service(service)

    assert service.state_reads == 2
    assert digest.work_queue_status == 'AVAILABLE'
    assert digest.top_work_queue_items[0]['item_id'] == 'task-1'
