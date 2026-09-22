from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import mkdtemp

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
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
from iabv_v15.services.self_teach.sandbox_experiment_service import SandboxExperimentService


class _StaticService:
    def __init__(self, model: WorldModelSnapshot) -> None:
        self._model = model

    def current_model(self) -> WorldModelSnapshot:
        return self._model


class _StaticMonitor:
    def __init__(self, status: ToolEvolutionStatus) -> None:
        self._status = status

    def current_status(self, *, refresh: bool = False) -> ToolEvolutionStatus:
        return self._status


class _RecordingSandboxExperimentService(SandboxExperimentService):
    """Spy that records the call while executing the production implementation."""

    def __init__(self, *, experiment_lab: ExperimentLab) -> None:
        super().__init__(experiment_lab=experiment_lab)
        self.calls: list[dict[str, object]] = []
        self.returned_experiments = []

    def validate_recommendation(self, recommendation, *, world_model, environment_model=None, reason='manual'):
        self.calls.append(
            {
                'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                'recommended_route': recommendation.recommended_route.value,
                'recommended_config_signature': recommendation.recommended_config_signature,
                'score': recommendation.score,
                'confidence': recommendation.confidence,
                'proposal_key': recommendation.metadata.get('proposal_key', ''),
                'reason': reason,
            }
        )
        experiment = super().validate_recommendation(
            recommendation,
            world_model=world_model,
            environment_model=environment_model,
            reason=reason,
        )
        self.returned_experiments.append(experiment)
        return experiment


def _proposal() -> ToolEvolutionProposal:
    subject_key = 'bio-r15a:proposal-to-sandbox'
    return ToolEvolutionProposal(
        proposal_id='bio-r15a-proposal-control',
        proposal_key='bio-r15a:proposal-to-sandbox|validate_replacement|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|codex-plan',
        domain=ExperimentDomain.CODE,
        subject_key=subject_key,
        status='pending',
        proposal_kind='validate_replacement',
        title='BIO-R15A controlled proposal',
        summary='A real proposal is available for production validation.',
        rationale='The consumer boundary is under observation.',
        current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
        current_assistant_kind='chatgpt',
        current_config_signature='chatgpt-browser',
        candidate_route=EvaluationRoute.CODE_AGENT,
        candidate_assistant_kind='codex',
        candidate_config_signature='codex-plan',
        confidence=0.84,
        evidence_refs=['bio-r15a-run-a', 'bio-r15a-run-b'],
        comparison_scope_keys=[subject_key],
        metadata={
            'score_margin': 0.19,
            'baseline_weighted_score': 0.42,
            'alternative_weighted_score': 0.61,
            'baseline_profile': {
                'sample_count': 4,
                'success_rate': 0.25,
                'blocked_rate': 0.0,
                'fallback_rate': 0.0,
                'trend_score': -0.21,
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


def _cycle(root: Path, proposals: list[ToolEvolutionProposal]):
    lab, repository, storage = _lab(root)
    sandbox = _RecordingSandboxExperimentService(experiment_lab=lab)
    cycle = AutonomousValidationCycleService(
        experiment_lab=lab,
        experiment_lab_repository=repository,
        sandbox_experiment_service=sandbox,
        world_model_service=_StaticService(WorldModelSnapshot(block_records=[])),
        environment_self_awareness_service=None,
        tool_evolution_monitor=_StaticMonitor(ToolEvolutionStatus(summary='BIO-R15A controlled status', proposals=proposals)),
        storage=storage,
        auto_start=False,
    )
    return cycle, sandbox


def _experiment_identity(experiment) -> dict[str, object]:
    return {
        'experiment_id': experiment.experiment_id,
        'sandbox_subject_key': experiment.sandbox_subject_key,
        'baseline_assistant_kind': experiment.baseline_assistant_kind,
        'candidate_assistant_kind': experiment.candidate_assistant_kind,
        'verdict': experiment.verdict.value,
        'status': experiment.status,
        'promote_to_primary': experiment.promote_to_primary,
        'evidence_strength': experiment.evidence_strength,
    }


def test_bio_r15a_proposal_to_sandbox_runtime() -> None:
    proposal = _proposal()
    root = Path(mkdtemp(prefix='bio_r15a_'))
    try:
        control_cycle, control_spy = _cycle(root / 'control', [proposal])
        control_snapshot = control_cycle.run_once(reason='bio-r15a-control')

        assert control_snapshot.paused_reason == ''
        assert len(control_spy.calls) == 1
        assert len(control_spy.returned_experiments) == 1
        recommendation = control_spy.calls[0]
        experiment = control_spy.returned_experiments[0]
        assert recommendation['proposal_key'] == proposal.proposal_key
        assert experiment.subject_key == proposal.subject_key
        assert experiment.sandbox_subject_key == f'sandbox:{proposal.subject_key}'
        assert control_snapshot.last_experiment_id == experiment.experiment_id

        treatment_cycle, treatment_spy = _cycle(root / 'treatment', [])
        treatment_snapshot = treatment_cycle.run_once(reason='bio-r15a-treatment')

        assert treatment_snapshot.paused_reason == ''
        assert treatment_snapshot.status == 'idle_empty'
        assert treatment_spy.calls == []
        assert treatment_spy.returned_experiments == []

        print(
            json.dumps(
                {
                    'control': {
                        'proposal': {
                            'proposal_key': proposal.proposal_key,
                            'proposal_id': proposal.proposal_id,
                            'proposal_kind': proposal.proposal_kind,
                            'subject_key': proposal.subject_key,
                            'current_assistant_kind': proposal.current_assistant_kind,
                            'candidate_assistant_kind': proposal.candidate_assistant_kind,
                            'current_route': proposal.current_route.value,
                            'candidate_route': proposal.candidate_route.value,
                        },
                        'recommendation': recommendation,
                        'sandbox_experiment': _experiment_identity(experiment),
                        'snapshot': {
                            'status': control_snapshot.status,
                            'paused_reason': control_snapshot.paused_reason,
                            'inertia_reason': '',
                            'last_experiment_id': control_snapshot.last_experiment_id,
                        },
                    },
                    'treatment': {
                        'proposal_available': False,
                        'validate_recommendation_calls': len(treatment_spy.calls),
                        'sandbox_experiments_returned': len(treatment_spy.returned_experiments),
                        'snapshot': {
                            'status': treatment_snapshot.status,
                            'paused_reason': treatment_snapshot.paused_reason,
                            'inertia_reason': 'not_evaluated_no_candidate',
                        },
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)
