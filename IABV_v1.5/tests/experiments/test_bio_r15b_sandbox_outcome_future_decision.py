from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import mkdtemp
from types import SimpleNamespace

from iabv_v15.domain.models import (
    EvaluationRoute, ExperimentDomain, InferenceRequest, IntentRouteDecision, SandboxExperiment,
    SandboxExperimentVerdict, TaskIntent, TaskRole, WorldModelSnapshot,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.self_teach.sandbox_experiment_service import SandboxExperimentService

GOAL = 'code bio r15b future decision'
SOURCE_SUBJECT = 'general:code-bio-r15b-future-decision'
SANDBOX_SUBJECT = f'sandbox:{SOURCE_SUBJECT}'
SITE = 'sandbox:general'


class _FixedRouter:
    def build_decision_from_intent(self, *, request, intent):
        return IntentRouteDecision(detected_role=intent.detected_role, reason='BIO-R15B matched route fixture')


def _lab(root: Path):
    storage = ArtifactStorage(str(root / 'evolution'))
    repo = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), storage)
    return ExperimentLab(repository=repo, registry=AlgorithmBenchmarkRegistry(), scoring_engine=DecisionScoringEngine(), strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer())), repo, storage


def _assembler(root: Path, repo: ExperimentLabRepository, storage: ArtifactStorage) -> TaskContextAssembler:
    db = repo.db
    return TaskContextAssembler(
        episode_repository=EpisodeRepository(str(root / 'episodes'), db), knowledge_repository=KnowledgeRepository(db),
        run_repository=RunRepository(db), dossier_repository=ExecutionDossierRepository(db, storage),
        hidden_incident_repository=HiddenIncidentRepository(db, storage), site_policy_registry=SitePolicyRegistry(str(root / 'policies')),
        capability_repository=CapabilityRepository(db, storage), adaptive_session_repository=AdaptiveSessionRepository(db, storage),
        experiment_lab_repository=repo,
    )


def _run_case(root: Path, *, verdict: SandboxExperimentVerdict, promote: bool, trace_id: str) -> dict:
    lab, writer_repo, storage = _lab(root)
    # Matched prior evidence: only the subsequent sandbox outcome differs.
    lab.record_outcome(domain=ExperimentDomain.CODE, objective=GOAL, subject_key=SANDBOX_SUBJECT,
        route=EvaluationRoute.LANGUAGE_UNDERSTANDING, candidate_label='chatgpt', success=True,
        observed_summary='matched prior baseline', precision=.72, robustness=.8, reuse_score=.4, user_progress=.2,
        metadata={'assistant_kind': 'chatgpt', 'config_signature': 'chatgpt-baseline', 'comparison_scope_key': SANDBOX_SUBJECT, 'trace_id': trace_id})
    experiment = SandboxExperiment(subject_key=SOURCE_SUBJECT, sandbox_subject_key=SANDBOX_SUBJECT, domain=ExperimentDomain.CODE,
        hypothesis='BIO-R15B controlled sandbox outcome', baseline_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
        baseline_assistant_kind='chatgpt', baseline_config_signature='chatgpt-baseline', candidate_route=EvaluationRoute.CODE_AGENT,
        candidate_assistant_kind='codex', candidate_config_signature='codex-sandbox', verdict=verdict, status='observed',
        promote_to_primary=promote, evidence_strength=.82, supporting_run_ids=['bio-r15b-evidence-a'])
    # Real production persistence for the already-formed sandbox outcome.
    SandboxExperimentService(experiment_lab=lab)._record_sandbox_run(experiment=experiment)
    # Fresh reader boundary: writer objects are discarded before context construction.
    fresh_repo = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), ArtifactStorage(str(root / 'evolution')))
    recommendations = fresh_repo.list_recommendations(domain=ExperimentDomain.CODE.value, subject_key=SANDBOX_SUBJECT, limit=3)
    request = InferenceRequest(user_goal=GOAL, site_hint=SITE)
    intent = TaskIntent(intent_key='bio.r15b', title='BIO-R15B', detected_role=TaskRole.PROJECT_EVOLUTION, site_hint=SITE, summary=GOAL)
    fresh_assembler = _assembler(root, fresh_repo, ArtifactStorage(str(root / 'evolution')))
    context = fresh_assembler.build(request, intent)
    orchestrator = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
    orchestrator.autonomy_governance_policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)
    orchestrator.unified_memory_layer = None
    orchestrator.role_router = _FixedRouter()
    orchestrator.context_assembler = fresh_assembler
    session = SimpleNamespace(session_id='bio-r15b-fresh-session', intent=intent, context=context, evidence_refs=[], capability_readiness=[], approval_checkpoints=[], status=SimpleNamespace(value='planned'), metadata={})
    decision = orchestrator._build_decision_context(request=request, session=session, pack=SimpleNamespace(pack_id='bio-r15b', title='BIO-R15B'), assistant_guidance={})
    return {'experiment': {'experiment_id': experiment.experiment_id, 'verdict': verdict.value, 'promote_to_primary': promote, 'sandbox_subject_key': experiment.sandbox_subject_key},
        'fresh_recommendations': [{'id': r.recommendation_id, 'assistant': r.recommended_assistant_kind, 'route': r.recommended_route.value, 'score': r.score} for r in recommendations],
        'experiment_insights': context.experiment_insights, 'adaptive_learning_summary': context.metadata.get('adaptive_learning_summary', {}),
        'decision': {'historical_preferred_assistant_kind': decision.metadata.get('preferred_assistant_kind', ''), 'historical_preferred_config_signature': decision.metadata.get('preferred_config_signature', ''), 'governance_assistant': decision.governance.get('assistant_kind', ''), 'route': decision.route_decision.detected_role.value}}


def test_bio_r15b_sandbox_outcome_to_future_adaptive_decision() -> None:
    root = Path(mkdtemp(prefix='bio_r15b_'))
    try:
        control = _run_case(root / 'control', verdict=SandboxExperimentVerdict.FAILED, promote=False, trace_id='trace-control')
        treatment = _run_case(root / 'treatment', verdict=SandboxExperimentVerdict.VALID, promote=True, trace_id='trace-control')
        negative = _run_case(root / 'negative', verdict=SandboxExperimentVerdict.FAILED, promote=False, trace_id='trace-negative-only')
        assert control['experiment_insights'] and treatment['experiment_insights']
        control_projection = control['decision']
        treatment_projection = treatment['decision']
        assert control_projection != treatment_projection
        assert control_projection == negative['decision']
        def projection(case):
            insight = case['experiment_insights'][0]
            return {
                'experiment': case['experiment'],
                'fresh_recommendation': case['fresh_recommendations'][0],
                'experiment_insight': {
                    'subject_key': insight['subject_key'],
                    'recommended_assistant_kind': insight['recommended_assistant_kind'],
                    'recommended_route': insight['recommended_route'],
                    'recommended_config_signature': insight['recommended_config_signature'],
                },
                'adaptive_learning_summary': case['adaptive_learning_summary'],
                'decision': case['decision'],
            }
        print(json.dumps({'control': projection(control), 'treatment': projection(treatment), 'negative_control': projection(negative)}, sort_keys=True))
    finally:
        shutil.rmtree(root, ignore_errors=True)
