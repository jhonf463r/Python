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
    SandboxExperiment,
    SandboxExperimentVerdict,
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
