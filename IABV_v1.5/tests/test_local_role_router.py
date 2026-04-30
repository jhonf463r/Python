from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    InferenceRequest,
    InferenceResult,
    IntentRouteDecision,
    ProviderConfig,
    ProviderHealth,
    ProviderKind,
    ProviderStatus,
    ReasoningMode,
    ReportKind,
    TaskRole,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.services.providers import openai_compat_local_provider as local_provider_module
from iabv_v15.services.providers.openai_compat_local_provider import OpenAICompatLocalProvider
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService


class FakeProvider(LLMProvider):
    def __init__(self, name: str, mode: ReasoningMode, fail: bool = False):
        self._name = name
        self.mode = mode
        self.fail = fail
        self.health_calls = 0

    @property
    def name(self) -> str:
        return self._name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, 'ui')

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, 'planner')

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, 'chat')

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request, 'summary')

    def health_check(self) -> ProviderHealth:
        self.health_calls += 1
        return ProviderHealth(provider_name=self._name, status=ProviderStatus.READY, available=True, detail='ok')

    def _result(self, request: InferenceRequest, channel: str) -> InferenceResult:
        if self.fail:
            raise RuntimeError(f'{self._name} unavailable')
        summary = f'{self._name} {channel} handled {request.task_role.value}'
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self._name,
            reasoning_mode=self.mode,
            summary=summary,
            inferred_task=request.user_goal,
            confidence=0.8,
            executor_model='fake-model',
            raw_output={'channel': channel},
        )


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _router(
    root: Path,
    *,
    general_fail: bool = False,
    visual_fail: bool = False,
    account_resource_scanner: Any | None = None,
) -> LocalRoleRouter:
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
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
    return LocalRoleRouter(
        workspace_root=str(root),
        general_provider=FakeProvider('Ollama', ReasoningMode.LOCAL, fail=general_fail),
        visual_provider=FakeProvider('Ollama Vision', ReasoningMode.LOCAL, fail=visual_fail),
        optional_provider=FakeProvider('LM Studio', ReasoningMode.LOCAL),
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
        account_resource_scanner=account_resource_scanner,
    )


def test_local_role_router_generates_codex_packet_for_project_role() -> None:
    router = _router(_workspace('role_router_project'))
    request = InferenceRequest(user_goal='Detecta la siguiente mejora prioritaria', task_role=TaskRole.PROJECT_EVOLUTION)
    route, result = router.infer_task(request)

    assert route.task_role == TaskRole.PROJECT_EVOLUTION
    assert route.provider_name == 'Ollama'
    assert result.report_kind == ReportKind.ENGINEERING_REVIEW
    assert result.provider_name == 'Ollama'
    assert 'codex_packet' in result.raw_output
    assert 'Paquete para Codex' in result.raw_output['codex_packet']
    assert result.raw_output['channel'] == 'chat'


def test_local_role_router_auto_routes_analytics_and_uses_planner() -> None:
    router = _router(_workspace('role_router_auto'))
    request = InferenceRequest(
        user_goal='Analiza las metricas del proyecto, compara el progreso actual y dame una estrategia paso a paso.',
        auto_route=True,
        enable_planning=True,
    )
    route, result = router.infer_task(request)

    assert route.task_role == TaskRole.ANALYTICS
    assert result.detected_role == TaskRole.ANALYTICS
    assert result.planner_used is True
    assert result.provider_name == 'Ollama'
    assert result.summary.startswith('Ollama chat handled analytics')
    assert result.raw_output.get('planner_summary', '').startswith('Ollama planner handled research')


def test_local_role_router_auto_routes_customer_support() -> None:
    router = _router(_workspace('role_router_support'))
    request = InferenceRequest(
        user_goal='Responde a este cliente y dime las formas de pago disponibles.',
        auto_route=True,
        enable_planning=True,
    )
    route, result = router.infer_task(request)

    assert route.task_role == TaskRole.CUSTOMER_SUPPORT
    assert result.detected_role == TaskRole.CUSTOMER_SUPPORT
    assert result.report_kind == ReportKind.CUSTOMER_RESPONSE
    assert result.summary.startswith('Ollama chat handled customer_support')


def test_local_role_router_falls_back_to_visual_provider_when_general_fails() -> None:
    router = _router(_workspace('role_router_fallback'), general_fail=True)
    request = InferenceRequest(user_goal='Analiza metricas y dame prioridades', task_role=TaskRole.ANALYTICS)
    route, result = router.infer_task(request)

    assert route.task_role == TaskRole.ANALYTICS
    assert route.used_fallback is True
    assert result.provider_name == 'Ollama Vision'
    assert result.used_fallback is True
    assert result.confidence_reduced is True
    assert result.raw_output['channel'] == 'chat'
    assert result.raw_output['fallback_trace']['channel'] == 'general'
    assert result.raw_output['fallback_trace']['primary_provider'] == 'Ollama'
    assert result.raw_output['fallback_trace']['fallback_provider'] == 'Ollama Vision'
    assert result.raw_output['fallback_trace']['errors']


def test_local_role_router_uses_visual_provider_for_visual_role() -> None:
    router = _router(_workspace('role_router_visual'))
    request = InferenceRequest(user_goal='Revisa esta interfaz', task_role=TaskRole.VISUAL, requires_visual_reasoning=True)
    route, result = router.infer_task(request)

    assert route.task_role == TaskRole.VISUAL
    assert route.provider_name == 'Ollama Vision'
    assert result.provider_name == 'Ollama Vision'
    assert result.report_kind == ReportKind.VISUAL_ANALYSIS
    assert result.raw_output['channel'] == 'ui'


def test_local_role_router_knowledge_role_prefers_general_profile_for_chat_routes() -> None:
    router = _router(_workspace('role_router_knowledge_profile'))

    role_profile = next(item for item in router.role_profiles if item.role == TaskRole.KNOWLEDGE)
    route = router.route_from_decision(
        IntentRouteDecision(
            detected_role=TaskRole.KNOWLEDGE,
            planner_required=False,
            visual_required=False,
            tool_chain=[],
            reason='knowledge chat',
        )
    )

    assert role_profile.preferred_model_profile_id == 'general-qwen'
    assert route.model_profile_id == 'general-qwen'
    assert route.model_name == 'qwen3:8b'


def test_optional_local_provider_reports_optional_inactive(monkeypatch) -> None:
    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def get(self, url: str) -> object:
            raise RuntimeError('connection refused')

    class _HttpxStub:
        Client = _Client

    monkeypatch.setattr(local_provider_module, 'httpx', _HttpxStub)
    provider = OpenAICompatLocalProvider(
        ProviderConfig(
            name='LM Studio',
            kind=ProviderKind.LOCAL,
            base_url='http://127.0.0.1:1/v1',
            model='gemma3:4b',
            optional=True,
        ),
        timeout_seconds=0.5,
    )

    health = provider.health_check()

    assert health.status == ProviderStatus.OPTIONAL_INACTIVE
    assert health.available is False


def test_local_role_router_caches_health_snapshot_until_forced() -> None:
    router = _router(_workspace('role_router_health_cache'))
    embedding_calls = {'count': 0}
    original_embedding_health = router.embedding_service.health_check

    def _embedding_health() -> ProviderHealth:
        embedding_calls['count'] += 1
        return original_embedding_health()

    router.embedding_service.health_check = _embedding_health  # type: ignore[method-assign]

    first = router.health_snapshot()
    second = router.health_snapshot()
    forced = router.health_snapshot(refresh=True, max_age_seconds=0.0)

    assert len(first) == len(second) == len(forced) == 4
    assert router.general_provider.health_calls == 2
    assert router.visual_provider.health_calls == 2
    assert router.optional_provider.health_calls == 2
    assert embedding_calls['count'] == 2


# ─────────────────────────────────────────────────────────────────
# Worker health gate tests
# ─────────────────────────────────────────────────────────────────

def _fake_pool_healthy() -> dict[str, Any]:
    return {
        'available_count': 2,
        'exhausted_count': 0,
        'total_remaining_messages': 30,
        'workers': [
            {'email': 'a@test.com', 'tool': 'chatgpt', 'remaining_messages': 20, 'exhausted': False},
            {'email': 'b@test.com', 'tool': 'codex', 'remaining_messages': 10, 'exhausted': False},
        ],
        'exhausted': [],
        'tools_available': ['chatgpt', 'codex'],
    }


def _fake_pool_exhausted() -> dict[str, Any]:
    return {
        'available_count': 0,
        'exhausted_count': 2,
        'total_remaining_messages': 0,
        'workers': [
            {'email': 'a@test.com', 'tool': 'chatgpt', 'remaining_messages': 0, 'exhausted': True},
            {'email': 'b@test.com', 'tool': 'codex', 'remaining_messages': 0, 'exhausted': True},
        ],
        'exhausted': [],
        'tools_available': [],
    }


def _fake_pool_error() -> dict[str, Any]:
    raise RuntimeError('scanner offline')


def test_worker_health_gate_no_scanner_returns_unresolved() -> None:
    router = _router(_workspace('whg_no_scanner'))
    gate = router.worker_health_gate()
    assert gate['usable'] is False
    assert 'UNRESOLVED' in gate['reason']
    assert gate['available_count'] == 0


def test_worker_health_gate_healthy_pool_returns_usable() -> None:
    router = _router(
        _workspace('whg_healthy'),
        account_resource_scanner=_fake_pool_healthy,
    )
    gate = router.worker_health_gate()
    assert gate['usable'] is True
    assert gate['available_count'] == 2
    assert len(gate['workers']) == 2


def test_worker_health_gate_healthy_pool_filters_by_target() -> None:
    router = _router(
        _workspace('whg_target'),
        account_resource_scanner=_fake_pool_healthy,
    )
    gate = router.worker_health_gate(target_assistant='codex')
    assert gate['usable'] is True
    assert gate['available_count'] == 1
    assert gate['workers'][0]['tool'] == 'codex'


def test_worker_health_gate_target_not_found_returns_not_usable() -> None:
    router = _router(
        _workspace('whg_target_miss'),
        account_resource_scanner=_fake_pool_healthy,
    )
    gate = router.worker_health_gate(target_assistant='claude')
    assert gate['usable'] is False
    assert 'claude' in gate['reason']


def test_worker_health_gate_exhausted_pool_returns_not_usable() -> None:
    router = _router(
        _workspace('whg_exhausted'),
        account_resource_scanner=_fake_pool_exhausted,
    )
    gate = router.worker_health_gate()
    assert gate['usable'] is False
    assert gate['available_count'] == 0


def test_worker_health_gate_scanner_error_returns_not_usable() -> None:
    router = _router(
        _workspace('whg_error'),
        account_resource_scanner=_fake_pool_error,
    )
    gate = router.worker_health_gate()
    assert gate['usable'] is False
    assert 'scanner offline' in gate['reason']


def test_worker_health_gate_caches_result() -> None:
    call_count = {'n': 0}

    def _counting_scanner() -> dict[str, Any]:
        call_count['n'] += 1
        return _fake_pool_healthy()

    router = _router(
        _workspace('whg_cache'),
        account_resource_scanner=_counting_scanner,
    )
    first = router.worker_health_gate()
    second = router.worker_health_gate()

    assert first == second
    assert call_count['n'] == 1

    refreshed = router.worker_health_gate(refresh=True)
    assert call_count['n'] == 2
    assert refreshed['usable'] is True


def test_worker_health_gate_different_targets_not_cross_contaminated() -> None:
    """Cache stores raw pool; different target_assistant values filter independently."""
    call_count = {'n': 0}

    def _counting_scanner() -> dict[str, Any]:
        call_count['n'] += 1
        return _fake_pool_healthy()

    router = _router(
        _workspace('whg_cross_target'),
        account_resource_scanner=_counting_scanner,
    )
    chatgpt_gate = router.worker_health_gate(target_assistant='chatgpt')
    codex_gate = router.worker_health_gate(target_assistant='codex')

    assert call_count['n'] == 1, 'scanner should be called once (raw pool cached)'
    assert chatgpt_gate['usable'] is True
    assert chatgpt_gate['available_count'] == 1
    assert chatgpt_gate['workers'][0]['tool'] == 'chatgpt'
    assert codex_gate['usable'] is True
    assert codex_gate['available_count'] == 1
    assert codex_gate['workers'][0]['tool'] == 'codex'


def test_route_from_decision_falls_back_when_external_no_worker() -> None:
    router = _router(
        _workspace('whg_route_fallback'),
        account_resource_scanner=_fake_pool_exhausted,
    )
    decision = IntentRouteDecision(
        detected_role=TaskRole.PROJECT_EVOLUTION,
        planner_required=False,
        visual_required=False,
        tool_chain=[],
        reason='Codex consultation needed.',
    )
    route = router.route_from_decision(
        decision,
        requires_external=True,
        target_assistant='codex',
    )
    assert 'Fallback local' in route.reason
    assert route.provider_name == 'Ollama'


def test_route_from_decision_passes_through_when_external_worker_available() -> None:
    router = _router(
        _workspace('whg_route_pass'),
        account_resource_scanner=_fake_pool_healthy,
    )
    decision = IntentRouteDecision(
        detected_role=TaskRole.PROJECT_EVOLUTION,
        planner_required=False,
        visual_required=False,
        tool_chain=[],
        reason='Codex consultation needed.',
    )
    route = router.route_from_decision(
        decision,
        requires_external=True,
        target_assistant='codex',
    )
    assert 'Fallback local' not in route.reason
    assert route.provider_name == 'Adaptive local orchestrator'


def test_route_from_decision_no_external_skips_gate() -> None:
    router = _router(
        _workspace('whg_route_no_ext'),
        account_resource_scanner=_fake_pool_exhausted,
    )
    decision = IntentRouteDecision(
        detected_role=TaskRole.TRAINING,
        planner_required=False,
        visual_required=False,
        tool_chain=[],
        reason='Local training.',
    )
    route = router.route_from_decision(decision)
    assert 'Fallback local' not in route.reason


# ── Bootstrap wiring tests ──────────────────────────────────────


def test_bootstrap_wiring_scanner_callable_produces_real_gate() -> None:
    """Verify that passing estimate_available_workers as the scanner
    produces a real gate result (not UNRESOLVED) — this mirrors the
    bootstrap.py wiring pattern."""
    from iabv_v15.services.account_resource_scanner import estimate_available_workers

    router = _router(
        _workspace('whg_bootstrap_wiring'),
        account_resource_scanner=estimate_available_workers,
    )
    gate = router.worker_health_gate()
    # On a Linux CI box there are no browser sessions, so available_count
    # will be 0 — but the gate must still report a REAL result (not
    # UNRESOLVED) because the scanner *is* wired and callable.
    assert 'UNRESOLVED' not in gate['reason']
    assert isinstance(gate['usable'], bool)
    assert isinstance(gate['available_count'], int)


def test_bootstrap_wiring_route_with_real_scanner_no_workers() -> None:
    """When the real scanner is wired but returns 0 workers (Linux CI),
    route_from_decision with requires_external must fallback to local."""
    from iabv_v15.services.account_resource_scanner import estimate_available_workers

    router = _router(
        _workspace('whg_bootstrap_route'),
        account_resource_scanner=estimate_available_workers,
    )
    decision = IntentRouteDecision(
        detected_role=TaskRole.PROJECT_EVOLUTION,
        planner_required=False,
        visual_required=False,
        tool_chain=[],
        reason='External consultation.',
    )
    route = router.route_from_decision(
        decision,
        requires_external=True,
        target_assistant='codex',
    )
    # On Linux CI: no browser sessions → 0 workers → fallback local
    assert 'Fallback local' in route.reason
    assert route.provider_name == 'Ollama'
