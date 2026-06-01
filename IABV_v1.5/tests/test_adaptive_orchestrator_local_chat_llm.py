"""Tests for local-chat LLM invocation inside AdaptiveTaskOrchestrator.

Verifies that conversational flows (``knowledge.query`` / ``general.assistance``)
call the local Ollama provider via ``general_provider.answer_user`` and use
the captured summary as the user-facing answer, instead of the templated
``assistant_guidance.prompt`` fallback.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    AdaptiveSession,
    InferenceRequest,
    InferenceResult,
    IntentDisposition,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
    TaskIntent,
    TaskRole,
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
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService


class _RecordingProvider(LLMProvider):
    """Deterministic provider used to observe whether ``answer_user`` fires."""

    def __init__(self, *, name: str, answer: str, available: bool = True, model: str = 'recording-model') -> None:
        self._name = name
        self._answer = answer
        self._available = available
        self.model = model
        self.answer_user_calls: list[InferenceRequest] = []

    @property
    def name(self) -> str:
        return self._name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, summary=f'{self._name} ui {request.user_goal}')

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, summary=f'{self._name} task {request.user_goal}')

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        self.answer_user_calls.append(request)
        return self._result(request, summary=self._answer)

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, summary=f'{self._name} summary {request.user_goal}')

    def health_check(self) -> ProviderHealth:
        status = ProviderStatus.READY if self._available else ProviderStatus.DEGRADED
        return ProviderHealth(
            provider_name=self._name,
            status=status,
            available=self._available,
            detail='ok' if self._available else 'simulated_unavailable',
        )

    def _result(self, request: InferenceRequest, *, summary: str) -> InferenceResult:
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self._name,
            reasoning_mode=ReasoningMode.LOCAL,
            summary=summary,
            inferred_task=request.user_goal,
            confidence=0.9,
            executor_model='recording-model',
        )


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_orchestrator(
    root: Path,
    *,
    general_provider: LLMProvider,
) -> AdaptiveTaskOrchestrator:
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    dossiers = ExecutionDossierRepository(db, evolution_storage)
    experiment_lab_repository = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    incidents = HiddenIncidentRepository(db, evolution_storage)
    UserClueRepository(db, evolution_storage)
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
    visual_provider = _RecordingProvider(name='Ollama Vision', answer='visual')
    router = LocalRoleRouter(
        workspace_root=str(root),
        general_provider=general_provider,
        visual_provider=visual_provider,
        optional_provider=_RecordingProvider(name='LM Studio', answer='optional'),
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
        experiment_lab_repository=experiment_lab_repository,
    )
    return AdaptiveTaskOrchestrator(
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
            experiment_lab=experiment_lab,
            adaptive_weight_layer=adaptive_weight_layer,
        ),
        autonomy_governance_policy=AutonomyGovernancePolicy(),
    )


def test_local_chat_flow_uses_ollama_answer_as_summary() -> None:
    provider = _RecordingProvider(
        name='Ollama',
        answer='La neuroplasticidad operativa en IABV ajusta rutas con evidencia real.',
        available=True,
    )
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_success'),
        general_provider=provider,
    )
    request = InferenceRequest(
        user_goal='explicame en dos frases que es la neuroplasticidad operativa en IABV',
        auto_route=True,
    )

    _, result, _ = orchestrator.handle_request(request)

    assert len(provider.answer_user_calls) == 1
    assert result.summary == 'La neuroplasticidad operativa en IABV ajusta rutas con evidencia real.'
    local_chat_llm = result.raw_output.get('local_chat_llm') or {}
    assert local_chat_llm.get('available') is True
    assert local_chat_llm.get('provider_name') == 'Ollama'
    assert local_chat_llm.get('summary') == result.summary
    assert not local_chat_llm.get('error')


def test_local_chat_falls_back_to_template_when_provider_unavailable() -> None:
    provider = _RecordingProvider(
        name='Ollama',
        answer='never used',
        available=False,
    )
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_unavailable'),
        general_provider=provider,
    )
    request = InferenceRequest(
        user_goal='explicame en dos frases que es la neuroplasticidad operativa',
        auto_route=True,
    )

    _, result, _ = orchestrator.handle_request(request)

    assert provider.answer_user_calls == []
    assert result.summary
    assert result.summary != 'never used'
    local_chat_llm = result.raw_output.get('local_chat_llm') or {}
    assert local_chat_llm.get('available') is False


def test_local_chat_falls_back_to_template_on_provider_exception() -> None:
    class _BrokenProvider(_RecordingProvider):
        def answer_user(self, request: InferenceRequest) -> InferenceResult:
            self.answer_user_calls.append(request)
            raise RuntimeError('simulated ollama outage')

    provider = _BrokenProvider(name='Ollama', answer='unused', available=True)
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_exception'),
        general_provider=provider,
    )
    request = InferenceRequest(
        user_goal='explicame en dos frases que es la neuroplasticidad operativa',
        auto_route=True,
    )

    _, result, _ = orchestrator.handle_request(request)

    assert len(provider.answer_user_calls) == 1
    assert 'simulated ollama outage' not in result.summary
    local_chat_llm = result.raw_output.get('local_chat_llm') or {}
    assert local_chat_llm.get('available') is True
    assert local_chat_llm.get('error') == 'simulated ollama outage'
    assert local_chat_llm.get('summary') == ''


def test_non_chat_flow_does_not_invoke_llm() -> None:
    provider = _RecordingProvider(
        name='Ollama',
        answer='should not be used for wplay login',
        available=True,
    )
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_non_chat'),
        general_provider=provider,
    )
    request = InferenceRequest(
        user_goal='abre Wplay e inicia sesion',
        auto_route=True,
        enable_planning=True,
        site_hint='wplay',
    )

    _, result, _ = orchestrator.handle_request(request)

    assert provider.answer_user_calls == []
    assert 'should not be used for wplay login' not in result.summary
    local_chat_llm = result.raw_output.get('local_chat_llm') or {}
    assert local_chat_llm == {}


def test_metacognitive_intent_invokes_local_llm_directly() -> None:
    provider = _RecordingProvider(
        name='Ollama',
        answer='Uso WorldModel, OSES, contexto portable y pruebas antes de responder.',
        available=True,
    )
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_metacognition'),
        general_provider=provider,
    )
    request = InferenceRequest(
        user_goal='me entiendes y que evidencia tienes de tu metacognicion',
        auto_route=True,
    )
    session = AdaptiveSession(
        user_goal=request.user_goal,
        intent=TaskIntent(
            intent_key='system.metacognition',
            disposition=IntentDisposition.ANSWER_NOW,
            detected_role=TaskRole.KNOWLEDGE,
        ),
    )

    llm_chat = orchestrator._maybe_invoke_local_chat_llm(session=session, request=request)

    assert llm_chat is not None
    assert llm_chat['summary'] == 'Uso WorldModel, OSES, contexto portable y pruebas antes de responder.'
    assert len(provider.answer_user_calls) == 1
    assert provider.answer_user_calls[0].metadata.get('system_prompt_override')


def test_expanded_local_chat_intents_are_llm_eligible() -> None:
    provider = _RecordingProvider(name='Ollama', answer='respuesta local', available=True)
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_expanded_intents'),
        general_provider=provider,
    )
    request = InferenceRequest(user_goal='dame una estrategia local para entender esto', auto_route=True)

    for intent_key in (
        'system.self_awareness',
        'system.metacognition',
        'analytics.strategy',
        'customer.support',
        'research.local',
    ):
        metadata = {}
        if intent_key in {'analytics.strategy', 'customer.support', 'research.local'}:
            metadata['conversational_prompt'] = True
        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key=intent_key,
                disposition=IntentDisposition.ANSWER_NOW,
                detected_role=TaskRole.KNOWLEDGE,
                metadata=metadata,
            ),
        )
        llm_chat = orchestrator._maybe_invoke_local_chat_llm(session=session, request=request)
        assert llm_chat is not None, intent_key
        assert llm_chat['summary'] == 'respuesta local'

    assert len(provider.answer_user_calls) == 5


def test_small_local_model_receives_compact_system_prompt() -> None:
    provider = _RecordingProvider(
        name='Ollama',
        answer='respuesta compacta',
        available=True,
        model='qwen3:8b',
    )
    orchestrator = _build_orchestrator(
        _workspace('adaptive_local_chat_llm_compact_prompt'),
        general_provider=provider,
    )
    request = InferenceRequest(user_goal='que sabes de tu estado vivo', auto_route=True)
    session = AdaptiveSession(
        user_goal=request.user_goal,
        intent=TaskIntent(
            intent_key='system.self_awareness',
            disposition=IntentDisposition.ANSWER_NOW,
            detected_role=TaskRole.KNOWLEDGE,
        ),
    )

    llm_chat = orchestrator._maybe_invoke_local_chat_llm(session=session, request=request)

    assert llm_chat is not None
    assert llm_chat['system_prompt_mode'] == 'compact'
    assert llm_chat['system_prompt_chars'] <= 3500
    prompt = provider.answer_user_calls[0].metadata['system_prompt_override']
    assert 'PERMISOS OPERATIVOS' in prompt
    assert 'Contrato de razonamiento compacto' in prompt
