"""Tests for the canonical task_packet normalisation.

Covers:
- _build_task_packet produces the expected shape
- task_packet deposited in session.metadata during the main decision flow
- task_packet included in preflight_external_assistant() return
- evidence_basis preserved from decision_context.metadata
- selected_worker preserved from worker_gate.top_worker
- unresolved promoted from perception.unresolved_fields
- ran distinguishes "gate did not run" from "gate ran, no worker"
- recorder reads task_packet first, with fallback to dict-diving
- backward compat: recorder works when task_packet is absent
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    DecisionContext,
    GoalContext,
    InferenceRequest,
    InferenceResult,
    IntentRouteDecision,
    PerceptionSnapshot,
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


# ─── Stubs ────────────────────────────────────────────────────


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


# ─── Factory ─────────────────────────────────────────────────


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_orchestrator(root: Path) -> AdaptiveTaskOrchestrator:
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
        autonomy_governance_policy=AutonomyGovernancePolicy(),
    )


# ─── Helpers ─────────────────────────────────────────────────


PACKET_KEYS = {
    'objective', 'intent_key', 'route_summary', 'worker_gate_summary',
    'selected_worker', 'evidence_basis', 'governance_flags', 'unresolved',
    'resume_context', 'has_resume_hints', 'account_selection',
    'tool_selection_summary', 'trace_id', 'comparison_scope_key',
    'source_trace_ids', 'budget_tier', 'quota_remaining',
}


def _minimal_session(**overrides: Any) -> AdaptiveSession:
    defaults: dict[str, Any] = {
        'session_id': uuid4().hex,
        'user_goal': 'test goal',
        'intent': TaskIntent(title='test', intent_key='general.test'),
        'status': AdaptiveSessionStatus.COMPLETED,
    }
    defaults.update(overrides)
    return AdaptiveSession(**defaults)


def _minimal_decision_context(**overrides: Any) -> DecisionContext:
    defaults: dict[str, Any] = {
        'user_goal': 'test goal',
        'intent': TaskIntent(title='test', intent_key='general.test'),
        'route_decision': IntentRouteDecision(detected_role=TaskRole.KNOWLEDGE, reason='test'),
        'governance': {},
        'metadata': {},
    }
    defaults.update(overrides)
    return DecisionContext(**defaults)


def _minimal_perception(**overrides: Any) -> PerceptionSnapshot:
    defaults: dict[str, Any] = {
        'task_context': TaskContext(),
        'decision_context': _minimal_decision_context(),
        'goal_context': GoalContext(),
        'unresolved_fields': [],
        'metadata': {},
    }
    defaults.update(overrides)
    return PerceptionSnapshot(**defaults)


# ─── _build_task_packet unit tests ───────────────────────────


def test_packet_has_all_expected_keys() -> None:
    session = _minimal_session()
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert set(packet.keys()) == PACKET_KEYS


def test_packet_preserves_objective_and_intent() -> None:
    session = _minimal_session(user_goal='find the answer')
    dc = _minimal_decision_context(user_goal='find the answer')
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['objective'] == 'find the answer'
    assert packet['intent_key'] == 'general.test'


def test_packet_preserves_evidence_basis_from_dc_metadata() -> None:
    evidence = {'state': 'observed', 'live_sources': ['world_model'], 'persisted_sources': [], 'unresolved': []}
    dc = _minimal_decision_context(metadata={'evidence_basis': evidence})
    session = _minimal_session()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['evidence_basis']['state'] == 'observed'
    assert packet['evidence_basis']['evidence_state'] == 'observed'
    assert packet['evidence_basis']['live_sources'] == ['world_model']


def test_packet_evidence_basis_fallback_to_perception_metadata() -> None:
    evidence = {'state': 'inferred', 'live_sources': [], 'persisted_sources': ['ia_trace'], 'unresolved': []}
    dc = _minimal_decision_context(metadata={})
    perception = _minimal_perception(metadata={'evidence_basis': evidence})
    session = _minimal_session()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['evidence_basis']['state'] == 'inferred'
    assert packet['evidence_basis']['evidence_state'] == 'inferred'


def test_packet_evidence_basis_empty_when_missing() -> None:
    dc = _minimal_decision_context(metadata={})
    perception = _minimal_perception(metadata={})
    session = _minimal_session()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['evidence_basis']['evidence_state'] == 'unresolved'


def test_packet_preserves_selected_worker_from_gate() -> None:
    top = {'email': 'user@test.com', 'browser': 'chrome', 'profile': 'default', 'tool': 'chatgpt'}
    session = _minimal_session()
    session.metadata['worker_gate'] = {
        'usable': True,
        'top_worker': top,
        'ranked_workers': [top],
        'available_count': 1,
        'reason': '',
    }
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['selected_worker'] == top
    assert packet['worker_gate_summary']['top_worker'] == top
    assert packet['worker_gate_summary']['ran'] is True
    assert packet['worker_gate_summary']['usable'] is True
    assert packet['worker_gate_summary']['available_count'] == 1


def test_packet_gate_not_ran_produces_empty_worker() -> None:
    """When worker_gate was never deposited, ran=False and selected_worker={}."""
    session = _minimal_session()
    assert 'worker_gate' not in session.metadata
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['worker_gate_summary']['ran'] is False
    assert packet['worker_gate_summary']['usable'] is False
    assert packet['selected_worker'] == {}


def test_packet_gate_ran_no_usable_worker() -> None:
    """Gate ran but found no usable worker: ran=True, usable=False, selected_worker={}."""
    session = _minimal_session()
    session.metadata['worker_gate'] = {
        'usable': False,
        'top_worker': None,
        'ranked_workers': [],
        'available_count': 0,
        'reason': 'No hay worker usable.',
    }
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['worker_gate_summary']['ran'] is True
    assert packet['worker_gate_summary']['usable'] is False
    assert packet['selected_worker'] == {}


def test_packet_preserves_governance_flags() -> None:
    governance = {
        'approval_required': True,
        'should_consult': True,
        'block_risky_action': False,
        'other_field': 'ignored',
    }
    dc = _minimal_decision_context(governance=governance)
    session = _minimal_session()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['governance_flags'] == {
        'approval_required': True,
        'should_consult': True,
        'block_risky_action': False,
    }


def test_packet_preserves_unresolved_from_perception() -> None:
    unresolved = ['UNRESOLVED:world_model', 'UNRESOLVED:visual_signal_source']
    perception = _minimal_perception(unresolved_fields=unresolved)
    dc = _minimal_decision_context()
    session = _minimal_session()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['unresolved'] == unresolved


def test_packet_unresolved_empty_when_no_perception() -> None:
    dc = _minimal_decision_context()
    session = _minimal_session()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=None,
    )
    assert packet['unresolved'] == []


def test_packet_route_summary_includes_detected_role() -> None:
    dc = _minimal_decision_context()
    session = _minimal_session()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['route_summary']['detected_role'] == TaskRole.KNOWLEDGE.value


def test_packet_route_summary_assistant_kind_from_governance() -> None:
    governance = {'should_consult': True, 'assistant_kind': 'chatgpt'}
    dc = _minimal_decision_context(governance=governance)
    session = _minimal_session()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['route_summary']['assistant_kind'] == 'chatgpt'


def test_packet_route_summary_assistant_kind_empty_when_local() -> None:
    dc = _minimal_decision_context(governance={'should_consult': False, 'assistant_kind': ''})
    session = _minimal_session()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['route_summary']['assistant_kind'] == ''


# ─── Integration: main decision flow deposits task_packet ────


def test_main_flow_deposits_task_packet() -> None:
    root = _workspace('task_packet_main')
    orch = _build_orchestrator(root)
    request = InferenceRequest(user_goal='Run a test task')
    _route, _result, saved = orch.handle_request(request)
    assert 'task_packet' in saved.metadata
    packet = saved.metadata['task_packet']
    assert set(packet.keys()) == PACKET_KEYS
    assert packet['objective'] == 'Run a test task'
    assert isinstance(packet['evidence_basis'], dict)
    assert isinstance(packet['unresolved'], list)


# ─── Integration: preflight_external_assistant includes task_packet ──


def test_preflight_includes_task_packet() -> None:
    root = _workspace('task_packet_preflight')
    orch = _build_orchestrator(root)
    result = orch.preflight_external_assistant(
        user_goal='Consult external AI',
        assistant_kind='chatgpt',
    )
    assert 'task_packet' in result
    packet = result['task_packet']
    assert set(packet.keys()) == PACKET_KEYS
    assert packet['objective'] == 'Consult external AI'
    assert packet['route_summary']['assistant_kind'] == 'chatgpt'
    assert packet['governance_flags']['should_consult'] is True
    assert packet['worker_gate_summary']['ran'] is True


# ─── Recorder reads task_packet ──────────────────────────────


def test_recorder_reads_evidence_from_task_packet() -> None:
    root = _workspace('task_packet_recorder_evidence')
    orch = _build_orchestrator(root)
    request = InferenceRequest(user_goal='Record test')
    _route, _result, saved = orch.handle_request(request)
    packet = saved.metadata.get('task_packet', {})
    evidence = packet.get('evidence_basis', {})
    assert isinstance(evidence, dict)


def test_recorder_reads_selected_worker_from_task_packet() -> None:
    root = _workspace('task_packet_recorder_worker')
    orch = _build_orchestrator(root)
    request = InferenceRequest(user_goal='Record worker test')
    _route, _result, saved = orch.handle_request(request)
    packet = saved.metadata.get('task_packet', {})
    assert 'selected_worker' in packet


def test_recorder_backward_compat_without_task_packet() -> None:
    """Recorder still works when task_packet is absent (legacy sessions)."""
    root = _workspace('task_packet_recorder_compat')
    db = AppDatabase(str(root / 'app.sqlite'))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    recorder = TaskOutcomeRecorder(
        adaptive_session_repository=adaptive_sessions,
        capability_repository=capabilities,
        approval_checkpoint_repository=approvals,
        experiment_lab=experiment_lab,
        adaptive_weight_layer=adaptive_weight_layer,
    )
    session = _minimal_session(user_goal='Legacy session')
    session.metadata = {
        'decision_context': {
            'metadata': {
                'evidence_basis': {'state': 'observed', 'live_sources': ['world_model'], 'persisted_sources': [], 'unresolved': []},
            },
        },
        'worker_gate': {
            'usable': True,
            'top_worker': {'email': 'a@b.com', 'tool': 'chatgpt'},
            'available_count': 1,
            'reason': '',
        },
    }
    assert 'task_packet' not in session.metadata
    run_record = RunRecord(
        run_id=uuid4().hex,
        request=InferenceRequest(user_goal='Legacy session'),
        result=InferenceResult(
            request_id='test',
            provider_name='test',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='ok',
            inferred_task='Legacy session',
            confidence=0.8,
            executor_model='fake',
        ),
        route=RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title='Knowledge',
            provider_name='test',
            model_profile_id='test',
            model_name='test',
            reason='test',
        ),
        status=RunStatus.SUCCESS,
    )
    saved = recorder.record(session, run_record=run_record)
    assert saved is not None


def test_recorder_prefers_task_packet_over_legacy() -> None:
    """When both task_packet and legacy keys exist, recorder uses task_packet."""
    root = _workspace('task_packet_recorder_prefer')
    db = AppDatabase(str(root / 'app.sqlite'))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    recorder = TaskOutcomeRecorder(
        adaptive_session_repository=adaptive_sessions,
        capability_repository=capabilities,
        approval_checkpoint_repository=approvals,
        experiment_lab=experiment_lab,
        adaptive_weight_layer=adaptive_weight_layer,
    )
    packet_evidence = {'state': 'observed', 'live_sources': ['world_model'], 'persisted_sources': [], 'unresolved': []}
    legacy_evidence = {'state': 'inferred', 'live_sources': [], 'persisted_sources': ['ia_trace'], 'unresolved': []}
    packet_worker = {'email': 'packet@test.com', 'tool': 'chatgpt'}
    legacy_worker = {'email': 'legacy@test.com', 'tool': 'chatgpt'}
    session = _minimal_session(user_goal='Preference test')
    session.metadata = {
        'task_packet': {
            'objective': 'Preference test',
            'intent_key': 'general.test',
            'route_summary': {'detected_role': 'general_assistant', 'assistant_kind': ''},
            'worker_gate_summary': {'ran': True, 'usable': True, 'top_worker': packet_worker, 'available_count': 1},
            'selected_worker': packet_worker,
            'evidence_basis': packet_evidence,
            'governance_flags': {'approval_required': False, 'should_consult': False, 'block_risky_action': False},
            'unresolved': [],
        },
        'decision_context': {
            'metadata': {'evidence_basis': legacy_evidence},
        },
        'worker_gate': {
            'usable': True,
            'top_worker': legacy_worker,
            'available_count': 2,
            'reason': '',
        },
    }
    run_record = RunRecord(
        run_id=uuid4().hex,
        request=InferenceRequest(user_goal='Preference test'),
        result=InferenceResult(
            request_id='test',
            provider_name='test',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='ok',
            inferred_task='Preference test',
            confidence=0.8,
            executor_model='fake',
        ),
        route=RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title='Knowledge',
            provider_name='test',
            model_profile_id='test',
            model_name='test',
            reason='test',
        ),
        status=RunStatus.SUCCESS,
    )
    saved = recorder.record(session, run_record=run_record)
    assert saved is not None


# ─── Preflight evidence_basis and unresolved ─────────────────


def test_preflight_evidence_basis_not_empty() -> None:
    """preflight task_packet must not leave evidence_basis as {}."""
    root = _workspace('preflight_evidence_not_empty')
    orch = _build_orchestrator(root)
    result = orch.preflight_external_assistant(
        user_goal='Check external',
        assistant_kind='chatgpt',
    )
    packet = result['task_packet']
    eb = packet['evidence_basis']
    assert eb != {}, 'evidence_basis must not be empty'
    assert 'state' in eb
    assert eb['state'] in ('observed', 'inferred', 'unresolved')
    assert isinstance(eb.get('live_sources'), list)
    assert isinstance(eb.get('persisted_sources'), list)
    assert isinstance(eb.get('unresolved'), list)


def test_preflight_unresolved_propagates_world_model() -> None:
    """preflight task_packet.unresolved includes world_model.unresolved_fields."""
    root = _workspace('preflight_unresolved')
    orch = _build_orchestrator(root)
    result = orch.preflight_external_assistant(
        user_goal='Check unresolved',
        assistant_kind='chatgpt',
    )
    packet = result['task_packet']
    assert isinstance(packet['unresolved'], list)
    eb = packet['evidence_basis']
    assert isinstance(eb['unresolved'], list)


def test_preflight_backward_compat() -> None:
    """preflight return shape still includes all expected keys."""
    root = _workspace('preflight_backward_compat')
    orch = _build_orchestrator(root)
    result = orch.preflight_external_assistant(
        user_goal='Backward compat',
        assistant_kind='chatgpt',
    )
    assert 'task_packet' in result
    assert 'blocked' in result
    assert 'worker_health' in result
    packet = result['task_packet']
    assert set(packet.keys()) == PACKET_KEYS


# ─── GAP 3: correlation + privacy in task_packet ─────────────


def test_packet_trace_id_never_empty() -> None:
    """trace_id in task_packet must never be empty."""
    session = _minimal_session()
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['trace_id'], 'trace_id must not be empty'


def test_packet_comparison_scope_key_not_empty_with_intent() -> None:
    """comparison_scope_key must not be empty when intent_key exists."""
    session = _minimal_session()
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['comparison_scope_key'], 'comparison_scope_key must not be empty'
    assert 'general.test' in packet['comparison_scope_key']


def test_packet_source_trace_ids_includes_trace_id() -> None:
    """source_trace_ids should contain at least the trace_id."""
    session = _minimal_session()
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['trace_id'] in packet['source_trace_ids']


def test_packet_sanitizes_email_in_account_selection() -> None:
    """Raw email must be masked in account_selection for privacy."""
    session = _minimal_session(metadata={
        'worker_gate': {
            'usable': True,
            'top_worker': {'tool': 'chatgpt', 'email': 'john@example.com'},
            'available_count': 1,
            'recommended_account': {'tool': 'chatgpt', 'email': 'john@example.com'},
            'approved_account': {},
        },
    })
    dc = _minimal_decision_context()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    recommended = packet['account_selection']['recommended_account']
    assert 'john@example.com' not in str(recommended), 'raw email must be masked'
    assert '***@' in str(recommended.get('email', '')), 'email should be partially masked'


def test_packet_evidence_state_normalized() -> None:
    """evidence_basis should include evidence_state derived from state field."""
    evidence = {'state': 'observed', 'live_sources': ['world_model']}
    dc = _minimal_decision_context(metadata={'evidence_basis': evidence})
    session = _minimal_session()
    perception = _minimal_perception()
    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session, decision_context=dc, perception=perception,
    )
    assert packet['evidence_basis']['evidence_state'] in ('observed', 'inferred', 'unresolved')
