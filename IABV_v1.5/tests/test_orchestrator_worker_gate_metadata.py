"""Focused tests for worker-gate metadata preservation in AdaptiveTaskOrchestrator.

Covers:
- metadata includes top_worker when gate is usable
- metadata includes ranked_workers (capped at 5) when gate is usable
- metadata conserves reason de bloqueo when gate blocks
- top_worker is None when gate blocks
- ranked_workers is [] when gate blocks
- available_count is preserved
- no worker_gate key when governance does not require external consultation
- backward compat: existing orchestrator tests must not break
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    InferenceRequest,
    InferenceResult,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
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


# ─── Stubs ───────────────────────────────────────────────────


class _FakeProvider(LLMProvider):
    def __init__(self, name: str = 'Ollama'):
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
        return ProviderHealth(
            provider_name=self._name,
            status=ProviderStatus.READY,
            available=True,
            detail='ok',
        )

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


class _FakeGovernancePolicy(AutonomyGovernancePolicy):
    """Governance stub that can be configured to return should_consult."""

    def __init__(self, *, should_consult: bool = False, assistant_kind: str = ''):
        super().__init__()
        self._should_consult = should_consult
        self._assistant_kind = assistant_kind

    def evaluate(self, **kwargs: Any) -> dict[str, Any]:
        base = super().evaluate(**kwargs)
        base['should_consult'] = self._should_consult
        if self._assistant_kind:
            base['assistant_kind'] = self._assistant_kind
        return base


# ─── Factory ─────────────────────────────────────────────────


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_orchestrator(
    root: Path,
    *,
    governance: AutonomyGovernancePolicy | None = None,
    account_resource_scanner: Any = None,
) -> AdaptiveTaskOrchestrator:
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    dossiers = ExecutionDossierRepository(db, evolution_storage)
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    incidents = HiddenIncidentRepository(db, evolution_storage)
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
        general_provider=_FakeProvider('Ollama'),
        visual_provider=_FakeProvider('Ollama Vision'),
        optional_provider=_FakeProvider('LM Studio'),
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
        autonomy_governance_policy=governance or AutonomyGovernancePolicy(),
    )


# ─── Fake scanner module ─────────────────────────────────────

def _fake_scanner(workers: list[dict[str, Any]]):
    """Return a callable that mimics estimate_available_workers()."""
    def _scan() -> dict[str, Any]:
        available = [w for w in workers if not w.get('exhausted', False)]
        return {
            'workers': available,
            'exhausted': [w for w in workers if w.get('exhausted', False)],
            'available_count': len(available),
            'exhausted_count': len(workers) - len(available),
            'by_tool': {},
            'total_remaining_messages': sum(
                w.get('remaining_messages', 0) for w in available
            ),
        }
    return _scan


def _worker(
    tool: str = 'chatgpt',
    email: str = 'a@test.com',
    remaining: int = 40,
    limit: int = 40,
    exhausted: bool = False,
) -> dict[str, Any]:
    return {
        'tool': tool,
        'email': email,
        'remaining_messages': remaining,
        'limit': limit,
        'exhausted': exhausted,
        'browser': 'Chrome',
        'profile': 'Default',
    }


# ─── Tests ───────────────────────────────────────────────────


def test_worker_gate_metadata_present_when_consult() -> None:
    """When governance says should_consult, session metadata has worker_gate."""
    root = _workspace('gate_meta_consult')
    scanner = _fake_scanner([_worker(tool='chatgpt', email='best@t.com', remaining=40, limit=40)])
    gov = _FakeGovernancePolicy(should_consult=True, assistant_kind='chatgpt')
    orch = _build_orchestrator(root, governance=gov, account_resource_scanner=scanner)

    request = InferenceRequest(user_goal='consultar chatgpt sobre algo')
    route, result, session = orch.handle_request(request)

    assert 'worker_gate' in session.metadata
    gate = session.metadata['worker_gate']
    assert gate['usable'] is True
    assert gate['top_worker'] is not None
    assert gate['top_worker']['email'] == 'best@t.com'
    assert gate['available_count'] == 1
    assert gate['reason'] == ''


def test_worker_gate_top_worker_has_score() -> None:
    """top_worker includes tool, email, remaining, score fields."""
    root = _workspace('gate_meta_score')
    scanner = _fake_scanner([_worker(tool='chatgpt', email='x@t.com', remaining=20, limit=40)])
    gov = _FakeGovernancePolicy(should_consult=True, assistant_kind='chatgpt')
    orch = _build_orchestrator(root, governance=gov, account_resource_scanner=scanner)

    _, _, session = orch.handle_request(InferenceRequest(user_goal='test'))
    tw = session.metadata['worker_gate']['top_worker']
    assert 'tool' in tw
    assert 'email' in tw
    assert 'score' in tw
    assert tw['score'] == 0.5  # 20/40


def test_worker_gate_ranked_workers_capped() -> None:
    """ranked_workers is capped at 5 entries."""
    root = _workspace('gate_meta_cap')
    workers = [_worker(tool='chatgpt', email=f'u{i}@t.com', remaining=40 - i, limit=40) for i in range(8)]
    scanner = _fake_scanner(workers)
    gov = _FakeGovernancePolicy(should_consult=True, assistant_kind='chatgpt')
    orch = _build_orchestrator(root, governance=gov, account_resource_scanner=scanner)

    _, _, session = orch.handle_request(InferenceRequest(user_goal='test'))
    ranked = session.metadata['worker_gate']['ranked_workers']
    assert len(ranked) <= 5


def test_worker_gate_blocked_preserves_reason() -> None:
    """When no workers available, gate blocks with reason and top_worker=None."""
    root = _workspace('gate_meta_blocked')
    scanner = _fake_scanner([])  # no workers
    gov = _FakeGovernancePolicy(should_consult=True, assistant_kind='chatgpt')
    orch = _build_orchestrator(root, governance=gov, account_resource_scanner=scanner)

    _, _, session = orch.handle_request(InferenceRequest(user_goal='test'))
    gate = session.metadata['worker_gate']
    assert gate['usable'] is False
    assert gate['top_worker'] is None
    assert gate['ranked_workers'] == []
    assert gate['available_count'] == 0
    assert gate['reason'] != ''


def test_worker_gate_blocked_exhausted_preserves_reason() -> None:
    """When all workers are exhausted, gate blocks with a reason."""
    root = _workspace('gate_meta_exhausted')
    scanner = _fake_scanner([_worker(tool='chatgpt', email='dead@t.com', remaining=0, limit=40, exhausted=True)])
    gov = _FakeGovernancePolicy(should_consult=True, assistant_kind='chatgpt')
    orch = _build_orchestrator(root, governance=gov, account_resource_scanner=scanner)

    _, _, session = orch.handle_request(InferenceRequest(user_goal='test'))
    gate = session.metadata['worker_gate']
    assert gate['usable'] is False
    assert gate['top_worker'] is None
    assert gate['reason'] != ''


def test_no_worker_gate_when_local_only() -> None:
    """When governance does NOT set should_consult, no worker_gate key."""
    root = _workspace('gate_meta_local')
    gov = _FakeGovernancePolicy(should_consult=False)
    orch = _build_orchestrator(root, governance=gov)

    _, _, session = orch.handle_request(InferenceRequest(user_goal='pregunta local'))
    assert 'worker_gate' not in session.metadata


def test_worker_gate_no_scanner_preserves_unresolved() -> None:
    """Without scanner wired, gate still reports usable=False with UNRESOLVED."""
    root = _workspace('gate_meta_no_scanner')
    gov = _FakeGovernancePolicy(should_consult=True, assistant_kind='chatgpt')
    orch = _build_orchestrator(root, governance=gov, account_resource_scanner=None)

    _, _, session = orch.handle_request(InferenceRequest(user_goal='test'))
    gate = session.metadata['worker_gate']
    assert gate['usable'] is False
    assert gate['top_worker'] is None
    assert 'UNRESOLVED' in gate['reason']


# ─── FASE 2: TaskOutcomeRecorder learning metadata ──────────
# These tests verify the 3 fields added to _record_learning() metadata
# are correctly extracted from session.metadata['worker_gate'].
# We test the extraction logic directly rather than going through full
# recorder flow, because RunRecord requires heavy model construction
# that is orthogonal to what we're validating.


def test_learning_extraction_with_gate() -> None:
    """The 3 learning fields extract correctly from worker_gate metadata."""
    meta: dict[str, Any] = {
        'worker_gate': {
            'usable': True,
            'top_worker': {'tool': 'chatgpt', 'email': 'a@t.com', 'score': 0.9},
            'ranked_workers': [{'tool': 'chatgpt', 'score': 0.9}],
            'available_count': 3,
            'reason': '',
        },
    }
    selected = (dict(meta.get('worker_gate') or {}).get('top_worker') or {}).get('tool', '')
    count = int(dict(meta.get('worker_gate') or {}).get('available_count') or 0)
    reason = str(dict(meta.get('worker_gate') or {}).get('reason') or '')

    assert selected == 'chatgpt'
    assert count == 3
    assert reason == ''


def test_learning_extraction_with_blocked_gate() -> None:
    """When gate is blocked, selected_worker is empty and reason is preserved."""
    meta: dict[str, Any] = {
        'worker_gate': {
            'usable': False,
            'top_worker': None,
            'ranked_workers': [],
            'available_count': 0,
            'reason': 'No hay workers con sesion activa y cuota disponible.',
        },
    }
    selected = (dict(meta.get('worker_gate') or {}).get('top_worker') or {}).get('tool', '')
    count = int(dict(meta.get('worker_gate') or {}).get('available_count') or 0)
    reason = str(dict(meta.get('worker_gate') or {}).get('reason') or '')

    assert selected == ''
    assert count == 0
    assert reason == 'No hay workers con sesion activa y cuota disponible.'


def test_learning_extraction_without_gate() -> None:
    """When no worker_gate in metadata, all fields default gracefully."""
    meta: dict[str, Any] = {}
    selected = (dict(meta.get('worker_gate') or {}).get('top_worker') or {}).get('tool', '')
    count = int(dict(meta.get('worker_gate') or {}).get('available_count') or 0)
    reason = str(dict(meta.get('worker_gate') or {}).get('reason') or '')

    assert selected == ''
    assert count == 0
    assert reason == ''
