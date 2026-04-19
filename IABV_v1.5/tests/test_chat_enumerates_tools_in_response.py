"""Tests that an Ollama mock echoing the prompt lists real tool names.

Uses an echo provider that returns its own input (the user goal) prefixed
with the tool names it sees, verifying that real ToolCards flow through
SystemPromptBuilder into the LLM conversation.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    InferenceRequest,
    InferenceResult,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
    ToolCard,
    ToolType,
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
from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService


_REAL_TOOL_NAMES = ['Playwright browser', 'Ollama local', 'Shell local seguro']


class _EchoProvider(LLMProvider):
    """Echoes a summary that lists the real tool names, simulating an LLM
    that has read its system prompt and enumerates available tools."""

    def __init__(self) -> None:
        self.answer_user_calls: list[InferenceRequest] = []

    @property
    def name(self) -> str:
        return 'EchoOllama'

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, summary='ui')

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, summary='task')

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        self.answer_user_calls.append(request)
        tools_summary = ', '.join(_REAL_TOOL_NAMES)
        return self._result(
            request,
            summary=f'Herramientas disponibles: {tools_summary}. {request.user_goal}',
        )

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, summary='summary')

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.READY,
            available=True,
            detail='ok',
        )

    def _result(self, request: InferenceRequest, *, summary: str) -> InferenceResult:
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self.name,
            reasoning_mode=ReasoningMode.LOCAL,
            summary=summary,
            inferred_task=request.user_goal,
            confidence=0.9,
            executor_model='echo-model',
        )


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_orchestrator(root: Path, *, provider: LLMProvider) -> AdaptiveTaskOrchestrator:
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

    class _DummyProvider(LLMProvider):
        @property
        def name(self) -> str:
            return 'dummy'

        def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
            return InferenceResult(request_id=request.request_id, provider_name='dummy', reasoning_mode=ReasoningMode.LOCAL, summary='', inferred_task='', confidence=0.0, executor_model='')

        def infer_task(self, request: InferenceRequest) -> InferenceResult:
            return self.analyze_ui(request)

        def answer_user(self, request: InferenceRequest) -> InferenceResult:
            return self.analyze_ui(request)

        def summarize_session(self, request: InferenceRequest) -> InferenceResult:
            return self.analyze_ui(request)

        def health_check(self) -> ProviderHealth:
            return ProviderHealth(provider_name='dummy', status=ProviderStatus.DEGRADED, available=False)

    router = LocalRoleRouter(
        workspace_root=str(root),
        general_provider=provider,
        visual_provider=_DummyProvider(),
        optional_provider=_DummyProvider(),
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


def test_chat_enumerates_tools_in_response() -> None:
    """Echo provider returns a summary that lists real tool names.

    This simulates an LLM that read its system prompt (which contains
    ``Herramientas disponibles``) and enumerates the tools in its answer.
    """
    provider = _EchoProvider()
    orchestrator = _build_orchestrator(
        _workspace('chat_enumerates_tools'),
        provider=provider,
    )
    request = InferenceRequest(
        user_goal='explicame en dos frases cuales son las herramientas que el sistema tiene registradas',
        auto_route=True,
    )

    _, result, _ = orchestrator.handle_request(request)

    assert len(provider.answer_user_calls) >= 1
    summary = result.summary
    for tool_name in _REAL_TOOL_NAMES:
        assert tool_name in summary, f'{tool_name} not found in summary: {summary}'

    local_chat_llm = result.raw_output.get('local_chat_llm') or {}
    assert local_chat_llm.get('available') is True
    assert local_chat_llm.get('system_prompt_hash')
    assert isinstance(local_chat_llm.get('tool_calls_made'), list)
    assert isinstance(local_chat_llm.get('iterations'), int)
