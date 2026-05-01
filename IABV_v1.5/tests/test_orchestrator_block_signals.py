"""Tests for live block-signal wiring from world model to worker gate.

Covers:
- _extract_block_signals_from_world_model: extracts per-tool signals
  from ToolLiveStatus.external_state_flags, detected_blocks, and status
- _enrich_gate_with_block_signals: re-ranks gate workers when signals present
- backward compat: empty signals leave gate unchanged
- flag mapping: canonical flags map to scanner signal names
- no signals when world_model is None or has no tool_live_status
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from iabv_v15.domain.models import (
    InferenceRequest,
    InferenceResult,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
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


# ─── _extract_block_signals_from_world_model ─────────────────


def test_extract_signals_none_world_model() -> None:
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(None)
    assert result == {}


def test_extract_signals_empty_tool_live_status() -> None:
    wm = WorldModelSnapshot(tool_live_status=[])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {}


def test_extract_signals_no_flags_no_blocks() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='codex-1',
            assistant_kind='codex',
            available=True,
            status='activo',
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {}


def test_extract_signals_from_external_state_flags() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            available=True,
            status='activo',
            external_state_flags=['wrong_thread', 'awaiting_response'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert 'chatgpt' in result
    assert 'wrong_thread' in result['chatgpt']
    assert 'awaiting_response' in result['chatgpt']


def test_extract_signals_from_detected_blocks() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            available=True,
            status='activo',
            detected_blocks=['capture_unverified'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {'chatgpt': ['capture_unverified']}


def test_extract_signals_status_no_disponible() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='codex-1',
            assistant_kind='codex',
            status='no_disponible',
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {'codex': ['no_disponible']}


def test_extract_signals_flag_mapping_account_limited() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='activo',
            external_state_flags=['account_limited'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {'chatgpt': ['rate_limited']}


def test_extract_signals_flag_mapping_session_expired() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='activo',
            external_state_flags=['session_expired'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {'chatgpt': ['auth_expired']}


def test_extract_signals_flag_mapping_assistant_login_required() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='activo',
            external_state_flags=['assistant_login_required'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {'chatgpt': ['auth_expired']}


def test_extract_signals_deduplication() -> None:
    """Same signal from external_state_flags and detected_blocks → one entry."""
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='activo',
            external_state_flags=['wrong_thread'],
            detected_blocks=['wrong_thread'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result['chatgpt'] == ['wrong_thread']


def test_extract_signals_multiple_tools() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='activo',
            external_state_flags=['wrong_thread'],
        ),
        ToolLiveStatus(
            tool_id='codex-1',
            assistant_kind='codex',
            status='no_disponible',
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert set(result.keys()) == {'chatgpt', 'codex'}
    assert result['chatgpt'] == ['wrong_thread']
    assert result['codex'] == ['no_disponible']


def test_extract_signals_skips_empty_assistant_kind() -> None:
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='unknown-1',
            assistant_kind='',
            status='activo',
            external_state_flags=['wrong_thread'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    assert result == {}


def test_extract_signals_combined_flags_blocks_status() -> None:
    """All three sources contribute signals for the same tool."""
    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='no_disponible',
            external_state_flags=['wrong_thread'],
            detected_blocks=['capture_unverified'],
        ),
    ])
    result = AdaptiveTaskOrchestrator._extract_block_signals_from_world_model(wm)
    sigs = result['chatgpt']
    assert 'wrong_thread' in sigs
    assert 'capture_unverified' in sigs
    assert 'no_disponible' in sigs


# ─── _enrich_gate_with_block_signals ─────────────────────────


def _usable_gate() -> dict[str, Any]:
    return {
        'usable': True,
        'reason': '',
        'available_count': 2,
        'workers': [
            {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 40, 'score': 100.0},
            {'tool': 'chatgpt', 'email': 'b@test.com', 'remaining': 40, 'score': 100.0},
        ],
        'top_worker': {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 40, 'score': 100.0},
        'ranked_workers': [
            {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 40, 'score': 100.0},
            {'tool': 'chatgpt', 'email': 'b@test.com', 'remaining': 40, 'score': 100.0},
        ],
    }


def _blocked_gate() -> dict[str, Any]:
    return {
        'usable': False,
        'reason': 'No hay workers.',
        'available_count': 0,
        'workers': [],
        'top_worker': None,
        'ranked_workers': [],
    }


def test_enrich_gate_empty_signals_unchanged() -> None:
    root = _workspace('enrich_empty')
    orch = _build_orchestrator(root)
    gate = _usable_gate()
    original_top = gate['top_worker']
    result = orch._enrich_gate_with_block_signals(gate, 'chatgpt', {})
    assert result['top_worker'] == original_top
    assert 'block_signals_applied' not in result


def test_enrich_gate_blocked_gate_unchanged() -> None:
    root = _workspace('enrich_blocked')
    orch = _build_orchestrator(root)
    gate = _blocked_gate()
    result = orch._enrich_gate_with_block_signals(gate, 'chatgpt', {'chatgpt': ['wrong_thread']})
    assert result['usable'] is False
    assert 'block_signals_applied' not in result


def test_enrich_gate_applies_signals() -> None:
    """With block_signals, re-ranking should change top_worker and add block_signals_applied."""
    root = _workspace('enrich_applies')
    orch = _build_orchestrator(root)
    gate = _usable_gate()

    def _fake_pool() -> dict[str, Any]:
        return {
            'available_count': 2,
            'workers': [
                {
                    'tool': 'chatgpt',
                    'email': 'a@test.com',
                    'browser': 'Chrome',
                    'profile': 'Default',
                    'remaining_messages': 40,
                    'limit': 40,
                    'exhausted': False,
                },
                {
                    'tool': 'chatgpt',
                    'email': 'b@test.com',
                    'browser': 'Chrome',
                    'profile': 'Profile 1',
                    'remaining_messages': 40,
                    'limit': 40,
                    'exhausted': False,
                },
            ],
        }

    with patch(
        'iabv_v15.services.account_resource_scanner.estimate_available_workers',
        side_effect=_fake_pool,
    ):
        result = orch._enrich_gate_with_block_signals(
            gate, 'chatgpt', {'chatgpt': ['wrong_thread']},
        )

    assert result.get('block_signals_applied') == {'chatgpt': ['wrong_thread']}
    assert result['usable'] is True
    for w in result.get('ranked_workers', []):
        assert 'block_risk' in w or w.get('tool') != 'chatgpt'


def test_enrich_gate_all_workers_blocked() -> None:
    """When all workers are eliminated by signals, gate becomes non-usable."""
    root = _workspace('enrich_all_blocked')
    orch = _build_orchestrator(root)
    gate = _usable_gate()

    def _fake_pool_single() -> dict[str, Any]:
        return {
            'available_count': 1,
            'workers': [
                {
                    'tool': 'chatgpt',
                    'email': 'a@test.com',
                    'browser': 'Chrome',
                    'profile': 'Default',
                    'remaining_messages': 0,
                    'limit': 40,
                    'exhausted': True,
                },
            ],
        }

    with patch(
        'iabv_v15.services.account_resource_scanner.estimate_available_workers',
        side_effect=_fake_pool_single,
    ):
        result = orch._enrich_gate_with_block_signals(
            gate, 'chatgpt', {'chatgpt': ['auth_expired']},
        )

    assert result['usable'] is False
    assert result['top_worker'] is None
    assert result['ranked_workers'] == []


def test_enrich_gate_scanner_exception_returns_original() -> None:
    """If estimate_available_workers raises, original gate returned unchanged."""
    root = _workspace('enrich_exception')
    orch = _build_orchestrator(root)
    gate = _usable_gate()
    original_top = gate['top_worker']

    with patch(
        'iabv_v15.services.account_resource_scanner.estimate_available_workers',
        side_effect=RuntimeError('scanner down'),
    ):
        result = orch._enrich_gate_with_block_signals(
            gate, 'chatgpt', {'chatgpt': ['wrong_thread']},
        )

    assert result['top_worker'] == original_top
    assert 'block_signals_applied' not in result


# ─── Integration: preflight wiring ───────────────────────────


def _usable_gate_for_router() -> dict[str, Any]:
    return {
        'usable': True,
        'reason': '',
        'available_count': 2,
        'workers': [
            {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 40, 'score': 100.0},
            {'tool': 'chatgpt', 'email': 'b@test.com', 'remaining': 40, 'score': 100.0},
        ],
        'top_worker': {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 40, 'score': 100.0},
        'ranked_workers': [
            {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 40, 'score': 100.0},
            {'tool': 'chatgpt', 'email': 'b@test.com', 'remaining': 40, 'score': 100.0},
        ],
    }


def _fake_pool_2_workers() -> dict[str, Any]:
    return {
        'available_count': 2,
        'workers': [
            {
                'tool': 'chatgpt',
                'email': 'a@test.com',
                'browser': 'Chrome',
                'profile': 'Default',
                'remaining_messages': 40,
                'limit': 40,
                'exhausted': False,
            },
            {
                'tool': 'chatgpt',
                'email': 'b@test.com',
                'browser': 'Chrome',
                'profile': 'Profile 1',
                'remaining_messages': 40,
                'limit': 40,
                'exhausted': False,
            },
        ],
    }


def test_preflight_passes_block_signals_to_gate() -> None:
    """preflight_external_assistant extracts signals and enriches the gate."""
    root = _workspace('preflight_signals')
    orch = _build_orchestrator(root)

    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            status='activo',
            external_state_flags=['wrong_thread'],
        ),
    ])

    with (
        patch.object(orch, '_world_model', return_value=wm),
        patch.object(
            orch.role_router, 'worker_health_gate',
            return_value=_usable_gate_for_router(),
        ),
        patch(
            'iabv_v15.services.account_resource_scanner.estimate_available_workers',
            side_effect=_fake_pool_2_workers,
        ),
    ):
        result = orch.preflight_external_assistant(
            user_goal='test', assistant_kind='chatgpt',
        )

    gate = result.get('worker_health', {})
    assert gate.get('block_signals_applied') == {'chatgpt': ['wrong_thread']}


def test_preflight_no_signals_backward_compat() -> None:
    """Without live signals, preflight returns gate unchanged (no block_signals_applied key)."""
    root = _workspace('preflight_compat')
    orch = _build_orchestrator(root)

    wm = WorldModelSnapshot(tool_live_status=[
        ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            available=True,
            status='activo',
        ),
    ])

    with patch.object(orch, '_world_model', return_value=wm):
        result = orch.preflight_external_assistant(
            user_goal='test', assistant_kind='chatgpt',
        )

    gate = result.get('worker_health', {})
    assert 'block_signals_applied' not in gate
