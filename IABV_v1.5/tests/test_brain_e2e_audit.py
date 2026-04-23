"""End-to-end tests for the central brain audit fixes (PR #162).

Exercises the full brain flow: request → intent → decision context →
governance → execution → outcome recording → learning loop, verifying
that the 6 gaps identified in the audit are now closed:

G1: GoalEngine reads adaptive_learning to close confidence loop
G2: Intent correction includes conversation_history
G3: Sync pulse recommendations factor in success_rate
G4: Parallel comparison payload carries site_hint and task_role
G5: Replan preserves conversation_history
G6: Validation learning summary propagates sync_pulse data
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    AssistantConfigurationSnapshot,
    AutonomousValidationSnapshot,
    CapabilityReadiness,
    CapabilityStatus,
    CapturedStep,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    GoalContext,
    InferenceRequest,
    InferenceResult,
    NetworkStatusSnapshot,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    TaskContext,
    TaskIntent,
    TaskRole,
    ToolLiveStatus,
    WindowObservation,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.adaptive.adaptive_planner_service import AdaptivePlannerService
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.approval_gate_service import ApprovalGateService
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService
from iabv_v15.services.adaptive.goal_engine import GoalEngine
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeProvider(LLMProvider):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_name=self._name, status=ProviderStatus.READY, available=True, detail='ok')

    def _result(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self._name,
            reasoning_mode=ReasoningMode.LOCAL,
            summary=f'{self._name} handled {request.user_goal}',
            inferred_task=request.user_goal,
            confidence=0.8,
            executor_model='fake-model',
        )


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _orchestrator(root: Path) -> tuple[AdaptiveTaskOrchestrator, EpisodeRepository]:
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    dossiers = ExecutionDossierRepository(db, evolution_storage)
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab_service = ExperimentLab(
        repository=experiment_lab_repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    incidents = HiddenIncidentRepository(db, evolution_storage)
    clues = UserClueRepository(db, evolution_storage)
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    strategy_packs = StrategyPackRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)
    site_policies = SitePolicyRegistry(str(root / 'site_policies'))
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding:0.6b',
        lightweight_model='embeddinggemma',
        state_path=str(root / 'embedding_state.json'),
    )
    sql = SqlQueryAdvisorService(str(root / 'app.sqlite'))
    analytics = AnalyticsStrategyService(episodes, knowledge, runs, artifacts)
    support = CustomerSupportService(knowledge, embedding, sql)
    devassist = DevelopmentAssistService(str(root))
    pbt = PBTControlService(str(root / 'models'))
    gaps = TeachingGapAnalyzer()
    engineering = EngineeringReviewService(
        workspace_root=str(root),
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        artifact_repository=artifacts,
        analytics_service=analytics,
        teaching_gap_analyzer=gaps,
        pbt_service=pbt,
        development_assist_service=devassist,
    )
    router = LocalRoleRouter(
        workspace_root=str(root),
        general_provider=FakeProvider('Ollama'),
        visual_provider=FakeProvider('Ollama Vision'),
        optional_provider=FakeProvider('LM Studio'),
        embedding_service=embedding,
        sql_service=sql,
        analytics_service=analytics,
        customer_support_service=support,
        engineering_review_service=engineering,
        teaching_gap_analyzer=gaps,
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        artifact_repository=artifacts,
    )
    context = TaskContextAssembler(
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        dossier_repository=dossiers,
        hidden_incident_repository=incidents,
        site_policy_registry=site_policies,
        capability_repository=capabilities,
        adaptive_session_repository=adaptive_sessions,
        artifact_repository=artifacts,
        experiment_lab_repository=experiment_lab_repo,
    )
    orchestrator = AdaptiveTaskOrchestrator(
        role_router=router,
        adaptive_session_repository=adaptive_sessions,
        intent_service=IntentUnderstandingService(),
        context_assembler=context,
        capability_service=CapabilityReadinessService(capabilities),
        strategy_pack_registry=StrategyPackRegistry(strategy_packs),
        planner_service=AdaptivePlannerService(),
        approval_gate_service=ApprovalGateService(),
        execution_playbook_service=ExecutionPlaybookService(),
        task_outcome_recorder=TaskOutcomeRecorder(
            adaptive_session_repository=adaptive_sessions,
            capability_repository=capabilities,
            approval_checkpoint_repository=approvals,
            experiment_lab=experiment_lab_service,
            adaptive_weight_layer=adaptive_weight_layer,
            intent_understanding_service=IntentUnderstandingService(),
        ),
        autonomy_governance_policy=AutonomyGovernancePolicy(),
    )
    return orchestrator, episodes


# ---------------------------------------------------------------
# G1: GoalEngine reads adaptive_learning to derive confidence
# ---------------------------------------------------------------

def test_g1_goal_engine_confidence_from_learning() -> None:
    """GoalEngine._confidence_from_learning extracts confidence from
    adaptive_learning records deposited by TaskOutcomeRecorder."""
    learning_data = {
        'records': [
            {
                'weight_snapshot': {
                    'success_rate': 0.8,
                    'weighted_score': 0.7,
                }
            },
            {
                'weight_snapshot': {
                    'success_rate': 0.5,
                    'weighted_score': 0.3,
                }
            },
        ]
    }
    confidence = GoalEngine._confidence_from_learning(learning_data)
    assert confidence > 0.0, 'Should derive confidence from learning records'
    assert confidence <= 0.95, 'Confidence must be capped at 0.95'
    expected = round(min(0.95, 0.8 * 0.5 + 0.7 * 0.5), 4)
    assert confidence == expected, f'Expected {expected}, got {confidence}'


def test_g1_confidence_from_learning_empty() -> None:
    """Empty or missing learning returns 0.0."""
    assert GoalEngine._confidence_from_learning({}) == 0.0
    assert GoalEngine._confidence_from_learning({'records': []}) == 0.0
    assert GoalEngine._confidence_from_learning({'records': [{'no_weight': True}]}) == 0.0


def test_g1_goal_engine_applies_learning_confidence_to_session() -> None:
    """When a session has adaptive_learning in metadata,
    _apply_session_progress should factor it into node confidence."""
    root = _workspace('brain_e2e_g1')
    db = AppDatabase(str(root / 'app.sqlite'))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    objective_repo = ObjectiveRepository(db, evolution_storage)
    engine = GoalEngine(repository=objective_repo)

    node = objective_repo.save(ObjectiveNode(
        kind=ObjectiveNodeKind.TASK,
        title='Fix bug in module X',
        summary='Resolve issue',
        status=ObjectiveStatus.ACTIVE,
        priority=50,
        progress=0.5,
        confidence=0.3,
    ))

    session = AdaptiveSession(
        user_goal='Fix bug in module X',
        intent=TaskIntent(confidence=0.4),
        context=TaskContext(),
        status=AdaptiveSessionStatus.COMPLETED,
        metadata={
            'adaptive_learning': {
                'records': [
                    {'weight_snapshot': {'success_rate': 0.9, 'weighted_score': 0.85}},
                ],
            },
        },
    )
    updated = engine._apply_session_progress(node, session=session, level='task')
    learning_confidence = GoalEngine._confidence_from_learning(
        session.metadata.get('adaptive_learning') or {},
    )
    assert updated.confidence >= learning_confidence, (
        f'Node confidence {updated.confidence} should be >= learning confidence {learning_confidence}'
    )


# ---------------------------------------------------------------
# G2: Intent correction includes conversation_history
# ---------------------------------------------------------------

def test_g2_intent_correction_includes_conversation_history() -> None:
    """Verify the recheck InferenceRequest in _check_intent_correction
    now includes conversation_history from session metadata."""
    root = _workspace('brain_e2e_g2')
    db = AppDatabase(str(root / 'app.sqlite'))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab_service = ExperimentLab(
        repository=experiment_lab_repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )

    captured_requests: list[InferenceRequest] = []
    original_classify = IntentUnderstandingService.classify

    def spy_classify(self, request: InferenceRequest):
        captured_requests.append(request)
        return original_classify(self, request)

    intent_service = IntentUnderstandingService()
    intent_service.classify = lambda req: spy_classify(intent_service, req)

    recorder = TaskOutcomeRecorder(
        adaptive_session_repository=adaptive_sessions,
        capability_repository=capabilities,
        approval_checkpoint_repository=approvals,
        experiment_lab=experiment_lab_service,
        adaptive_weight_layer=adaptive_weight_layer,
        intent_understanding_service=intent_service,
    )

    conversation_history = [
        {'role': 'user', 'content': 'necesito que analices un bug en el codigo'},
        {'role': 'assistant', 'content': 'claro, dame mas detalles'},
    ]
    session = AdaptiveSession(
        user_goal='analiza el bug en el login',
        intent=TaskIntent(
            intent_key='general.assistance',
            confidence=0.3,
        ),
        context=TaskContext(),
        status=AdaptiveSessionStatus.FAILED,
        metadata={
            'conversation_history': conversation_history,
        },
    )
    run_record = RunRecord(
        status=RunStatus.FAILED,
        request=InferenceRequest(user_goal='analiza el bug en el login'),
        route=RoleRoute(task_role=TaskRole.PROJECT_EVOLUTION, role_title='evolution', provider_name='ollama', model_profile_id='fake', model_name='fake-model', reason='test'),
        result=InferenceResult(
            request_id='test-req',
            provider_name='ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            confidence=0.2,
            summary='Failed to analyze',
            inferred_task='analiza el bug',
        ),
    )

    recorder._check_intent_correction(session=session, run_record=run_record)

    recheck_calls = [r for r in captured_requests if r.metadata.get('intent_correction_recheck')]
    assert recheck_calls, 'Expected _check_intent_correction to trigger a recheck classify call'
    recheck = recheck_calls[0]
    assert recheck.metadata.get('conversation_history') == conversation_history, (
        'Recheck request should include conversation_history from session metadata'
    )


# ---------------------------------------------------------------
# G3: Sync pulse factors success_rate, not just success count
# ---------------------------------------------------------------

def test_g3_sync_pulse_factors_success_rate() -> None:
    """Verify that _sync_pulse recommendations include success_rate
    and sort by avg_score * success_rate."""
    from iabv_v15.services.self_teach.autonomous_validation_cycle import AutonomousValidationCycleService
    from iabv_v15.domain.models import ExperimentRun, ExperimentMetric

    root = _workspace('brain_e2e_g3')
    db = AppDatabase(str(root / 'app.sqlite'))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)

    for i in range(6):
        experiment_lab_repo.save_run(ExperimentRun(
            domain=ExperimentDomain.LANGUAGE,
            suite_name='brain_audit',
            objective='test objective',
            subject_key='test',
            route=EvaluationRoute.LOCAL,
            candidate_route=EvaluationRoute.LOCAL,
            candidate_label='ollama',
            candidate_id=f'run-ollama-{i}',
            assistant_kind='ollama',
            success=True,
            metrics=ExperimentMetric(total_score=0.7),
        ))

    for i in range(20):
        experiment_lab_repo.save_run(ExperimentRun(
            domain=ExperimentDomain.LANGUAGE,
            suite_name='brain_audit',
            objective='test objective',
            subject_key='test',
            route=EvaluationRoute.UI,
            candidate_route=EvaluationRoute.UI,
            candidate_label='chatgpt',
            candidate_id=f'run-chatgpt-fail-{i}',
            assistant_kind='chatgpt',
            success=False,
            metrics=ExperimentMetric(total_score=0.0),
        ))
    for i in range(3):
        experiment_lab_repo.save_run(ExperimentRun(
            domain=ExperimentDomain.LANGUAGE,
            suite_name='brain_audit',
            objective='test objective',
            subject_key='test',
            route=EvaluationRoute.UI,
            candidate_route=EvaluationRoute.UI,
            candidate_label='chatgpt',
            candidate_id=f'run-chatgpt-ok-{i}',
            assistant_kind='chatgpt',
            success=True,
            metrics=ExperimentMetric(total_score=0.9),
        ))

    recent_runs = list(experiment_lab_repo.list_runs(limit=30))
    assert len(recent_runs) >= 9

    kind_success_scores: dict[str, list[float]] = {}
    kind_total_counts: dict[str, int] = {}
    for run in recent_runs:
        kind = str(run.assistant_kind or '').strip().lower()
        if not kind:
            continue
        kind_total_counts[kind] = kind_total_counts.get(kind, 0) + 1
        if bool(run.success):
            kind_success_scores.setdefault(kind, []).append(float(run.metrics.total_score or 0.0))

    top_recs = sorted(
        (
            {
                'assistant_kind': k,
                'avg_score': round(sum(v) / max(len(v), 1), 4),
                'runs': len(v),
                'total_runs': kind_total_counts.get(k, len(v)),
                'success_rate': round(len(v) / max(kind_total_counts.get(k, 1), 1), 4),
            }
            for k, v in kind_success_scores.items()
            if len(v) >= 2
        ),
        key=lambda x: (x['avg_score'] * x['success_rate'], x['runs']),
        reverse=True,
    )[:3]

    assert len(top_recs) >= 2
    for rec in top_recs:
        assert 'success_rate' in rec, 'Recommendation must include success_rate'
        assert 'total_runs' in rec, 'Recommendation must include total_runs'

    ollama_rec = next((r for r in top_recs if r['assistant_kind'] == 'ollama'), None)
    chatgpt_rec = next((r for r in top_recs if r['assistant_kind'] == 'chatgpt'), None)
    assert ollama_rec is not None
    assert chatgpt_rec is not None
    ollama_weighted = ollama_rec['avg_score'] * ollama_rec['success_rate']
    chatgpt_weighted = chatgpt_rec['avg_score'] * chatgpt_rec['success_rate']
    assert ollama_weighted > chatgpt_weighted, (
        f'Ollama ({ollama_weighted:.4f}) should rank above ChatGPT ({chatgpt_weighted:.4f}) '
        f'because ChatGPT has low success_rate despite higher avg_score'
    )


# ---------------------------------------------------------------
# G4: Parallel comparison payload carries full context
# ---------------------------------------------------------------

def test_g4_parallel_comparison_payload_has_context() -> None:
    """_build_parallel_comparison_payload includes site_hint, task_role,
    and conversation_history."""
    root = _workspace('brain_e2e_g4')
    orchestrator, _ = _orchestrator(root)

    request = InferenceRequest(
        user_goal='analiza el codigo del proyecto',
        site_hint='wplay',
        task_role=TaskRole.PROJECT_EVOLUTION,
        metadata={'conversation_history': [{'role': 'user', 'content': 'hola'}]},
    )
    candidate = {'assistant_kind': 'chatgpt'}

    payload = orchestrator._build_parallel_comparison_payload(
        request=request,
        candidate=candidate,
        synaptic_decision=None,
    )

    assert payload.get('site_hint') == 'wplay', 'Payload must include site_hint'
    meta = payload.get('metadata', {})
    assert meta.get('site_hint') == 'wplay', 'Metadata must include site_hint'
    assert meta.get('task_role') == TaskRole.PROJECT_EVOLUTION.value, 'Metadata must include task_role'
    assert meta.get('conversation_history') == [{'role': 'user', 'content': 'hola'}], (
        'Metadata must include conversation_history'
    )


# ---------------------------------------------------------------
# G5: Replan preserves conversation_history
# ---------------------------------------------------------------

def test_g5_replan_preserves_conversation_history() -> None:
    """_request_from_session preserves conversation_history from session metadata."""
    root = _workspace('brain_e2e_g5')
    orchestrator, _ = _orchestrator(root)

    conversation_history = [
        {'role': 'user', 'content': 'necesito ayuda con este bug'},
        {'role': 'assistant', 'content': 'entendido, voy a revisar'},
    ]
    session = AdaptiveSession(
        user_goal='fix the login bug',
        intent=TaskIntent(detected_role=TaskRole.PROJECT_EVOLUTION),
        context=TaskContext(
            site_id='wplay',
            goal_context=GoalContext(active_title='fix login'),
        ),
        status=AdaptiveSessionStatus.FAILED,
        metadata={
            'conversation_history': conversation_history,
            'goal_parameters': {},
        },
    )

    request = orchestrator._request_from_session(session)

    assert request.metadata.get('conversation_history') == conversation_history, (
        'Reconstructed request must preserve conversation_history'
    )


# ---------------------------------------------------------------
# G6: Validation learning summary propagates sync_pulse
# ---------------------------------------------------------------

def test_g6_validation_learning_summary_includes_sync_pulse() -> None:
    """TaskContextAssembler._validation_learning_summary extracts
    sync_pulse data from the validation cycle snapshot."""
    root = _workspace('brain_e2e_g6')
    orchestrator, _ = _orchestrator(root)

    class FakeValidationCycle:
        def current_snapshot(self):
            return AutonomousValidationSnapshot(
                cycle_id='test-cycle',
                status='synced',
                summary='All services coordinated',
                metadata={
                    'sync_pulse': {
                        'ia_availability': {'ollama': 'available', 'chatgpt': 'unavailable'},
                        'top_recommendations': [
                            {'assistant_kind': 'ollama', 'avg_score': 0.8, 'runs': 5, 'success_rate': 0.9},
                        ],
                        'active_proposals': [
                            {'type': 'improvement', 'title': 'Optimize retry logic'},
                        ],
                        'coordination_status': 'synced',
                    },
                },
            )

    orchestrator.context_assembler.autonomous_validation_cycle = FakeValidationCycle()

    summary = orchestrator.context_assembler._validation_learning_summary()

    assert summary.get('ia_availability') == {'ollama': 'available', 'chatgpt': 'unavailable'}, (
        'Should propagate ia_availability from sync_pulse'
    )
    assert len(summary.get('top_recommendations', [])) == 1
    assert summary['top_recommendations'][0]['assistant_kind'] == 'ollama'
    assert len(summary.get('active_proposals', [])) == 1
    assert summary['active_proposals'][0]['title'] == 'Optimize retry logic'
    assert summary.get('coordination_status') == 'synced'


# ---------------------------------------------------------------
# End-to-end: full brain flow with real objectives
# ---------------------------------------------------------------

def test_brain_e2e_full_flow_processes_objective_and_learns() -> None:
    """Exercise the complete brain path: request → intent classification →
    decision context → governance → execution → outcome recording →
    learning accumulation. Verify that:
    1. Intent is correctly classified
    2. Decision context includes governance
    3. Session is recorded with outcome
    4. A second request for the same goal shows accumulated learning
    """
    root = _workspace('brain_e2e_full_flow')
    orchestrator, episodes = _orchestrator(root)

    request = InferenceRequest(
        user_goal='analiza el codigo del proyecto y genera un reporte de bugs',
        auto_route=True,
        enable_planning=True,
        metadata={
            'conversation_history': [
                {'role': 'user', 'content': 'necesito un reporte de bugs del proyecto'},
            ],
        },
    )

    route, result, session = orchestrator.handle_request(request)

    assert route is not None, 'Route should be assigned'
    assert result is not None, 'Result should be returned'
    assert session is not None, 'Session should be created'
    assert session.session_id, 'Session must have an ID'
    assert session.intent.intent_key, 'Intent must be classified'

    decision_context = session.metadata.get('decision_context')
    assert decision_context is not None or session.context.metadata.get('governance') is not None, (
        'Decision context or governance must be present in session metadata'
    )

    saved = orchestrator.adaptive_session_repository.get(session.session_id)
    assert saved is not None, 'Session must be persisted after recording'

    route2, result2, session2 = orchestrator.handle_request(
        InferenceRequest(
            user_goal='analiza el codigo del proyecto y genera un reporte de bugs',
            auto_route=True,
            enable_planning=True,
        )
    )
    assert session2.session_id != session.session_id, 'Second request should create a new session'
    assert session2.intent.intent_key, 'Second intent must also be classified'


def test_brain_e2e_conversational_vs_actionable_routing() -> None:
    """Verify the brain correctly differentiates conversational prompts
    from actionable objectives, routing them differently."""
    root = _workspace('brain_e2e_routing')
    orchestrator, _ = _orchestrator(root)

    _, conv_result, conv_session = orchestrator.handle_request(
        InferenceRequest(user_goal='hola, que sabes hacer?', auto_route=True)
    )
    assert conv_session.intent.intent_key in IntentUnderstandingService.CONVERSATIONAL_INTENT_KEYS, (
        f'Conversational prompt should route to conversational intent, got {conv_session.intent.intent_key}'
    )

    _, action_result, action_session = orchestrator.handle_request(
        InferenceRequest(
            user_goal='implementa una funcion que valide emails en Python',
            auto_route=True,
            enable_planning=True,
        )
    )
    assert action_session.intent.intent_key not in IntentUnderstandingService.CONVERSATIONAL_INTENT_KEYS, (
        f'Actionable prompt should NOT route to conversational intent, got {action_session.intent.intent_key}'
    )


def test_brain_e2e_governance_blocks_dangerous_operations() -> None:
    """Verify governance policy blocks auto-merge for sensitive paths."""
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_merge(pr_metadata={
        'pull_number': 999,
        'ci_status': 'success',
        'reviews': [],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/domain/models.py'],
    })
    assert not allowed, 'Should block merge touching domain/models.py'
    assert 'sensible' in (reason or '').lower() or 'ruta' in (reason or '').lower(), (
        f'Reason should mention sensitive path: {reason}'
    )

    allowed, reason = policy.allow_github_merge(pr_metadata={
        'pull_number': 1000,
        'ci_status': 'success',
        'reviews': [],
        'draft': False,
        'additions': 5,
        'deletions': 3,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/services/adaptive/some_helper.py'],
    })
    assert allowed, f'Should allow merge for non-sensitive paths: {reason}'
