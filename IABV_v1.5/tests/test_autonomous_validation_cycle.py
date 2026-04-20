from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    EnvironmentRiskSignal,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    IssueSeverity,
    ProposalValidationResult,
    SandboxExperiment,
    SandboxExperimentVerdict,
    ToolEvolutionDecisionLog,
    ToolEvolutionProposal,
    ToolEvolutionStatus,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.self_teach.autonomous_validation_cycle import AutonomousValidationCycleService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _lab(root: Path) -> tuple[ExperimentLab, ExperimentLabRepository, ArtifactStorage]:
    storage = ArtifactStorage(str(root / 'evolution'))
    repository = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), storage)
    lab = ExperimentLab(
        repository=repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer()),
    )
    return lab, repository, storage


class _StaticMonitor:
    def __init__(self, status: ToolEvolutionStatus) -> None:
        self.status = status

    def current_status(self, *, refresh: bool = False) -> ToolEvolutionStatus:
        return self.status


class _StaticService:
    def __init__(self, model) -> None:
        self._model = model

    def current_model(self):
        return self._model


class _SandboxStub:
    def __init__(self, experiment: SandboxExperiment) -> None:
        self.experiment = experiment
        self.calls = 0
        self.last_recommendation = None

    def validate_recommendation(self, recommendation, *, world_model, environment_model=None, reason='manual'):
        self.calls += 1
        self.last_recommendation = recommendation
        return self.experiment


def _proposal(subject_key: str = 'wplay:bridge-lag') -> ToolEvolutionProposal:
    return ToolEvolutionProposal(
        proposal_id='proposal-1',
        proposal_key='wplay:bridge-lag|validate_replacement|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|codex-plan',
        domain=ExperimentDomain.CODE,
        subject_key=subject_key,
        status='pending',
        proposal_kind='validate_replacement',
        title='Validar reemplazo de chatgpt en wplay:bridge-lag',
        summary='Codex ya muestra mejor puntaje ponderado para este problema.',
        rationale='La herramienta actual se degradó y la propuesta tiene mejor evidencia reciente.',
        current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
        current_assistant_kind='chatgpt',
        current_config_signature='chatgpt-browser',
        candidate_route=EvaluationRoute.CODE_AGENT,
        candidate_assistant_kind='codex',
        candidate_config_signature='codex-plan',
        confidence=0.84,
        evidence_refs=['run-a', 'run-b'],
        comparison_scope_keys=[subject_key],
        metadata={
            'score_margin': 0.19,
            'baseline_weighted_score': 0.42,
            'alternative_weighted_score': 0.61,
            'baseline_profile': {
                'sample_count': 4,
                'success_rate': 0.25,
                'blocked_rate': 0.5,
                'fallback_rate': 0.5,
                'trend_score': -0.21,
            },
            'candidate_profile': {
                'sample_count': 3,
                'success_rate': 1.0,
                'blocked_rate': 0.0,
                'fallback_rate': 0.0,
                'trend_score': 0.18,
            },
            'ranked_configurations': [
                {
                    'route': EvaluationRoute.LANGUAGE_UNDERSTANDING.value,
                    'assistant_kind': 'chatgpt',
                    'config_signature': 'chatgpt-browser',
                    'weighted_score': 0.42,
                    'score': 0.4,
                    'samples': 4,
                },
                {
                    'route': EvaluationRoute.CODE_AGENT.value,
                    'assistant_kind': 'codex',
                    'config_signature': 'codex-plan',
                    'weighted_score': 0.61,
                    'score': 0.59,
                    'samples': 3,
                },
            ],
        },
    )


def _status(proposal: ToolEvolutionProposal) -> ToolEvolutionStatus:
    return ToolEvolutionStatus(
        summary='Hay una propuesta prioritaria de reemplazo.',
        proposals=[proposal],
    )


def test_autonomous_validation_cycle_consumes_tool_evolution_proposal_and_records_promoted_decision() -> None:
    root = _workspace('autonomous_validation_cycle_promoted')
    try:
        lab, repository, storage = _lab(root)
        proposal = _proposal()
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key=proposal.subject_key,
                sandbox_subject_key=f'sandbox:{proposal.subject_key}',
                domain=proposal.domain,
                candidate_route=proposal.candidate_route,
                candidate_assistant_kind=proposal.candidate_assistant_kind,
                candidate_config_signature=proposal.candidate_config_signature,
                promote_to_primary=True,
                verdict=SandboxExperimentVerdict.VALID,
                summary='Codex ganó en sandbox y debe promoverse.',
                supporting_run_ids=['run-a', 'run-b'],
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(_status(proposal)),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')
        decision_log = cycle.current_decision_log()
        summary = cycle.get_status()

        assert snapshot.status == 'promoted'
        assert sandbox.calls == 1
        assert sandbox.last_recommendation.metadata['proposal_key'] == proposal.proposal_key
        assert decision_log.entries[-1].decision == 'promoted'
        assert decision_log.entries[-1].winner == 'proposed_tool'
        assert decision_log.summary_by_problem[proposal.subject_key] == 'codex'
        assert summary['winning_by_problem'][proposal.subject_key] == 'codex'
        assert Path(decision_log.package_path).exists()
        assert Path(storage.resolve(f'tool_evolution/validated_proposals/{decision_log.entries[-1].result_id}.json')).exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_records_discarded_decision_when_current_tool_stays_best() -> None:
    root = _workspace('autonomous_validation_cycle_discarded')
    try:
        lab, repository, storage = _lab(root)
        proposal = _proposal('incident.bridge')
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key=proposal.subject_key,
                sandbox_subject_key=f'sandbox:{proposal.subject_key}',
                domain=proposal.domain,
                candidate_route=proposal.candidate_route,
                candidate_assistant_kind=proposal.candidate_assistant_kind,
                candidate_config_signature=proposal.candidate_config_signature,
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
                summary='La herramienta actual sigue siendo mas coherente para este problema.',
                supporting_run_ids=['run-a'],
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(_status(proposal)),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')
        decision_log = cycle.current_decision_log()

        assert snapshot.status == 'discarded'
        assert decision_log.entries[-1].decision == 'discarded'
        assert decision_log.entries[-1].winner == 'current_tool'
        assert decision_log.summary_by_problem[proposal.subject_key] == 'chatgpt'
        assert decision_log.summary_by_tool['chatgpt'] in {'estable', 'degradado'}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_marks_deferred_when_environment_is_not_safe() -> None:
    root = _workspace('autonomous_validation_cycle_deferred')
    try:
        lab, repository, storage = _lab(root)
        proposal = _proposal('wplay:slow-login')
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key=proposal.subject_key,
                sandbox_subject_key=f'sandbox:{proposal.subject_key}',
                domain=proposal.domain,
                candidate_route=proposal.candidate_route,
                candidate_assistant_kind=proposal.candidate_assistant_kind,
                candidate_config_signature=proposal.candidate_config_signature,
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        env_model = EnvironmentSelfModel(
            scan_status='warning',
            risk_signals=[
                EnvironmentRiskSignal(
                    kind='cpu_pressure',
                    severity=IssueSeverity.HIGH,
                    summary='CPU bajo presion alta.',
                )
            ],
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(env_model),
            tool_evolution_monitor=_StaticMonitor(_status(proposal)),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')
        decision_log = cycle.current_decision_log()
        summary = cycle.get_status()

        assert snapshot.status == 'deferred'
        assert sandbox.calls == 0
        assert decision_log.entries[-1].decision == 'deferred'
        assert decision_log.entries[-1].proposal_key == proposal.proposal_key
        assert proposal.proposal_key in summary['in_validation']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_initial_snapshot_is_bootstrapping_without_unresolved() -> None:
    root = _workspace('autonomous_validation_cycle_bootstrapping')
    try:
        lab, repository, storage = _lab(root)
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key='noop',
                sandbox_subject_key='sandbox:noop',
                domain=ExperimentDomain.CODE,
                candidate_route=EvaluationRoute.CODE_AGENT,
                candidate_assistant_kind='codex',
                candidate_config_signature='codex-plan',
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(ToolEvolutionStatus(summary='sin propuestas', proposals=[])),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.current_snapshot()
        assert snapshot.status == 'bootstrapping'
        assert snapshot.unresolved_fields == []
        assert 'UNRESOLVED:autonomous_validation_cycle' not in snapshot.unresolved_fields
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_transitions_to_idle_empty_when_no_proposals() -> None:
    root = _workspace('autonomous_validation_cycle_idle_empty')
    try:
        lab, repository, storage = _lab(root)
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key='noop',
                sandbox_subject_key='sandbox:noop',
                domain=ExperimentDomain.CODE,
                candidate_route=EvaluationRoute.CODE_AGENT,
                candidate_assistant_kind='codex',
                candidate_config_signature='codex-plan',
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(ToolEvolutionStatus(summary='sin propuestas', proposals=[])),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')

        assert snapshot.status == 'idle_empty'
        assert snapshot.unresolved_fields == []
        assert sandbox.calls == 0
        assert snapshot.summary
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_records_error_snapshot_when_run_once_raises() -> None:
    root = _workspace('autonomous_validation_cycle_error')
    try:
        lab, repository, storage = _lab(root)
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key='noop',
                sandbox_subject_key='sandbox:noop',
                domain=ExperimentDomain.CODE,
                candidate_route=EvaluationRoute.CODE_AGENT,
                candidate_assistant_kind='codex',
                candidate_config_signature='codex-plan',
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )

        class _BrokenMonitor:
            def current_status(self, *, refresh: bool = False) -> ToolEvolutionStatus:
                raise RuntimeError('boom')

        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_BrokenMonitor(),
            storage=storage,
            auto_start=False,
        )

        def _break(*_args, **_kwargs):
            raise RuntimeError('boom en run_once')

        cycle.run_once = _break  # type: ignore[method-assign]
        cycle._safe_tick(reason='bootstrap_validation')

        snapshot = cycle.current_snapshot()
        assert snapshot.status == 'error'
        assert 'UNRESOLVED:autonomous_validation_cycle_error' in snapshot.unresolved_fields
        assert 'boom' in snapshot.summary
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_transitions_from_bootstrapping_within_two_ticks() -> None:
    root = _workspace('autonomous_validation_cycle_transitions')
    try:
        lab, repository, storage = _lab(root)
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key='noop',
                sandbox_subject_key='sandbox:noop',
                domain=ExperimentDomain.CODE,
                candidate_route=EvaluationRoute.CODE_AGENT,
                candidate_assistant_kind='codex',
                candidate_config_signature='codex-plan',
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(ToolEvolutionStatus(summary='sin propuestas', proposals=[])),
            storage=storage,
            auto_start=False,
        )

        initial = cycle.current_snapshot()
        assert initial.status == 'bootstrapping'

        cycle._safe_tick(reason='bootstrap_validation')
        after_first = cycle.current_snapshot()
        assert after_first.status in {'idle_empty', 'validating', 'error'}
        assert after_first.status != 'bootstrapping'
        if after_first.status != 'error':
            assert 'UNRESOLVED:autonomous_validation_cycle' not in after_first.unresolved_fields
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _seed_decision_log_with_inertia(
    storage: ArtifactStorage,
    *,
    subject_key: str,
    winner_kind: str,
    count: int,
) -> None:
    """Minimal fixture: deja un tool_evolution/decision_log.json con
    ``count`` entries promovidas sobre ``subject_key`` con
    ``current_assistant_kind=winner_kind``; eso simula un loop que ya
    consolido ganador."""
    entries = [
        ProposalValidationResult(
            proposal_id=f'proposal-{i}',
            proposal_key=f'{subject_key}|validate_discovery|chatgpt-{i}',
            domain=ExperimentDomain.LANGUAGE,
            subject_key=subject_key,
            proposal_kind='validate_discovery',
            decision='promoted',
            winner='current_tool',
            current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            current_assistant_kind=winner_kind,
            current_config_signature='local',
            candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_assistant_kind=f'chatgpt-{i}',
            candidate_config_signature='web',
            confidence=0.88,
        )
        for i in range(count)
    ]
    log = ToolEvolutionDecisionLog(entries=entries)
    storage.save_json_atomic('tool_evolution/decision_log.json', log.model_dump(mode='json'))


def test_autonomous_validation_cycle_defers_proposal_when_scope_has_route_inertia() -> None:
    root = _workspace('autonomous_validation_cycle_scope_inertia')
    try:
        lab, repository, storage = _lab(root)
        _seed_decision_log_with_inertia(
            storage,
            subject_key='general',
            winner_kind='ollama',
            count=3,
        )
        proposal = _proposal(subject_key='general')
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key=proposal.subject_key,
                sandbox_subject_key=f'sandbox:{proposal.subject_key}',
                domain=proposal.domain,
                candidate_route=proposal.candidate_route,
                candidate_assistant_kind=proposal.candidate_assistant_kind,
                candidate_config_signature=proposal.candidate_config_signature,
                promote_to_primary=True,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(_status(proposal)),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')

        assert snapshot.status == 'deferred', (
            'scope con inercia de ruta debe diferir la validacion, no promover/descartar en vacio'
        )
        assert snapshot.paused_reason.startswith('scope_inertia_cooldown')
        assert sandbox.calls == 0, 'sandbox no debe ejecutarse cuando hay cooldown por inercia'
        latest = cycle.current_decision_log().entries[-1]
        assert latest.decision == 'deferred'
        assert 'ollama' in latest.reason
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_does_not_defer_when_recent_decisions_have_diverse_winners() -> None:
    root = _workspace('autonomous_validation_cycle_no_inertia')
    try:
        lab, repository, storage = _lab(root)
        entries = [
            ProposalValidationResult(
                proposal_id='p1', proposal_key='general|v|a', domain=ExperimentDomain.LANGUAGE,
                subject_key='general', proposal_kind='validate_discovery',
                decision='promoted', winner='current_tool',
                current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                current_assistant_kind='ollama', current_config_signature='local',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                candidate_assistant_kind='chatgpt', candidate_config_signature='web',
                confidence=0.8,
            ),
            ProposalValidationResult(
                proposal_id='p2', proposal_key='general|v|b', domain=ExperimentDomain.LANGUAGE,
                subject_key='general', proposal_kind='validate_discovery',
                decision='promoted', winner='proposed_tool',
                current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                current_assistant_kind='codex', current_config_signature='plan',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                candidate_assistant_kind='claude', candidate_config_signature='web',
                confidence=0.8,
            ),
            ProposalValidationResult(
                proposal_id='p3', proposal_key='other|v|c', domain=ExperimentDomain.LANGUAGE,
                subject_key='other', proposal_kind='validate_discovery',
                decision='promoted', winner='proposed_tool',
                current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                current_assistant_kind='claude', current_config_signature='web',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                candidate_assistant_kind='ollama', candidate_config_signature='local',
                confidence=0.8,
            ),
        ]
        log = ToolEvolutionDecisionLog(entries=entries)
        storage.save_json_atomic('tool_evolution/decision_log.json', log.model_dump(mode='json'))

        proposal = _proposal(subject_key='general')
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key=proposal.subject_key,
                sandbox_subject_key=f'sandbox:{proposal.subject_key}',
                domain=proposal.domain,
                candidate_route=proposal.candidate_route,
                candidate_assistant_kind=proposal.candidate_assistant_kind,
                candidate_config_signature=proposal.candidate_config_signature,
                promote_to_primary=True,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(_status(proposal)),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')

        assert snapshot.status == 'promoted', 'sin inercia consolidada, el ciclo debe validar normal'
        assert sandbox.calls == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write_self_exam_probe(storage: ArtifactStorage, probes: list[dict]) -> None:
    """Minimal fixture: deja un self_examination/latest.json con el shape que
    produce OperationalSelfExaminationService (sólo los campos relevantes
    para este test)."""
    payload = {
        'snapshot_id': 'snap-test',
        'status': 'needs_attention',
        'updated_at_utc': '2026-04-20T12:00:00+00:00',
        'findings': [],
        'recommended_adjustments': [],
        'metadata': {'pending_auto_probes': probes},
    }
    storage.save_json_atomic('self_examination/latest.json', payload)


def test_autonomous_validation_cycle_surfaces_pending_auto_probes_from_self_exam() -> None:
    root = _workspace('autonomous_validation_cycle_probes')
    try:
        lab, repository, storage = _lab(root)
        _write_self_exam_probe(
            storage,
            probes=[
                {
                    'finding_id': 'finding-recurring-1',
                    'category': 'recurring_failure',
                    'scope': 'general:training',
                    'title': 'Fallo repetido en general:training',
                    'severity': 'high',
                    'confidence': 0.92,
                    'evidence_refs': ['run-a', 'run-b', 'run-c'],
                    'source_refs': [],
                    'suggested_tests': [
                        'pytest -q -p no:cacheprovider tests/',
                        'reproduce_run_ids=run-a,run-b,run-c',
                        'scope=general:training',
                    ],
                    'trigger_reason': "Finding HIGH 'recurring_failure' con confianza 0.92 >= 0.85; autotests=0 no cierra el loop P4.",
                    'requested_at_utc': '2026-04-20T12:00:00+00:00',
                    'status': 'requested',
                }
            ],
        )
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key='noop',
                sandbox_subject_key='sandbox:noop',
                domain=ExperimentDomain.CODE,
                candidate_route=EvaluationRoute.CODE_AGENT,
                candidate_assistant_kind='codex',
                candidate_config_signature='codex-plan',
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(ToolEvolutionStatus(summary='sin propuestas', proposals=[])),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')

        probes_in_snapshot = list((snapshot.metadata or {}).get('pending_auto_probes') or [])
        assert probes_in_snapshot, 'run_once must surface pending_auto_probes on snapshot.metadata'
        assert probes_in_snapshot[0]['finding_id'] == 'finding-recurring-1'
        assert probes_in_snapshot[0]['status'] == 'requested'

        summary_probes = list(cycle.decision_log_summary().get('pending_auto_probes') or [])
        assert summary_probes, 'decision_log_summary must expose pending_auto_probes for MCP/UI consumers'
        assert summary_probes[0]['finding_id'] == 'finding-recurring-1'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_autonomous_validation_cycle_returns_empty_probes_when_self_exam_absent() -> None:
    root = _workspace('autonomous_validation_cycle_probes_missing')
    try:
        lab, repository, storage = _lab(root)
        # No write to self_examination/latest.json — aislado, fail-observable.
        sandbox = _SandboxStub(
            SandboxExperiment(
                subject_key='noop',
                sandbox_subject_key='sandbox:noop',
                domain=ExperimentDomain.CODE,
                candidate_route=EvaluationRoute.CODE_AGENT,
                candidate_assistant_kind='codex',
                candidate_config_signature='codex-plan',
                promote_to_primary=False,
                verdict=SandboxExperimentVerdict.VALID,
            )
        )
        cycle = AutonomousValidationCycleService(
            experiment_lab=lab,
            experiment_lab_repository=repository,
            sandbox_experiment_service=sandbox,
            world_model_service=_StaticService(WorldModelSnapshot()),
            environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
            tool_evolution_monitor=_StaticMonitor(ToolEvolutionStatus(summary='sin propuestas', proposals=[])),
            storage=storage,
            auto_start=False,
        )

        snapshot = cycle.run_once(reason='manual')

        # snapshot.metadata no debe tener pending_auto_probes cuando no hay señal.
        assert 'pending_auto_probes' not in (snapshot.metadata or {})
        assert cycle.decision_log_summary().get('pending_auto_probes') == []
    finally:
        shutil.rmtree(root, ignore_errors=True)
