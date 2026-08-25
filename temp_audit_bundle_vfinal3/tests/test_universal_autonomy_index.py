"""Tests for UniversalAutonomyIndex (Fase 7).

Validates that ``_universal_autonomy_index_findings`` in
``OperationalSelfExaminationService`` correctly calculates
AutonomyScore, ResilienceScore, CalibrationError and BlindSpotRatio,
and that the digest builder renders them in the governance digest.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    ControlMasterDigest,
    ControlMasterState,
    ExperimentDomain,
    ExperimentRun,
    EvaluationRoute,
    ExperimentMetric,
    InferenceRequest,
    InferenceResult,
    IssueSeverity,
    ObservationPermissionGate,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    SelfExaminationFinding,
    TaskIntent,
    TaskRole,
    ToolCapability,
    ToolLiveStatus,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.control_master_digest_builder import (
    ControlMasterDigestBuilder,
    _render_autonomy_metrics,
    render_digest_markdown,
)
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_storage() -> ArtifactStorage:
    tmp = tempfile.mkdtemp()
    return ArtifactStorage(root=tmp)


def _make_oses(**kwargs: Any) -> OperationalSelfExaminationService:
    return OperationalSelfExaminationService(
        workspace_root=kwargs.pop('workspace_root', tempfile.mkdtemp()),
        storage=kwargs.pop('storage', _make_storage()),
        **kwargs,
    )


def _make_run(*, status: RunStatus = RunStatus.SUCCESS) -> RunRecord:
    request = InferenceRequest(user_goal='test')
    result = InferenceResult(
        request_id=request.request_id,
        provider_name='Ollama',
        reasoning_mode=ReasoningMode.LOCAL,
        summary='ok',
        inferred_task='test',
        confidence=0.5,
    )
    route = RoleRoute(
        task_role=TaskRole.TRAINING,
        role_title='stub',
        provider_name='Ollama',
        model_profile_id='general',
        model_name='qwen3:8b',
        tool_chain=[ToolCapability.ANALYTICS],
        reason='stub',
    )
    return RunRecord(
        request=request,
        result=result,
        route=route,
        status=status,
    )


def _make_experiment(
    *,
    success: bool = True,
    confidence: float = 0.8,
    assistant_kind: str = 'gemini',
) -> ExperimentRun:
    return ExperimentRun(
        domain=ExperimentDomain.LANGUAGE,
        suite_name='test_suite',
        objective='test',
        route=EvaluationRoute.CLOUD,
        assistant_kind=assistant_kind,
        success=success,
        metrics=ExperimentMetric(precision=confidence),
    )


def _make_session(
    *,
    status: AdaptiveSessionStatus = AdaptiveSessionStatus.COMPLETED,
    metadata: dict[str, Any] | None = None,
) -> AdaptiveSession:
    return AdaptiveSession(
        user_goal='test',
        intent=TaskIntent(intent_key='test', description='test'),
        status=status,
        metadata=metadata or {},
    )


def _make_world(
    *,
    tools: int = 5,
    unresolved: int = 1,
    gates: int = 1,
    worker_pool: dict[str, Any] | None = None,
) -> WorldModelSnapshot:
    tool_statuses = [
        ToolLiveStatus(
            tool_id=f'tool_{i}',
            available=True,
            status='ready',
            metadata={'fallback_available': i % 2 == 0},
        )
        for i in range(tools)
    ]
    permission_gates = [
        ObservationPermissionGate(
            scope=f'gate_{i}',
            assistant_kind=f'tool_{i}',
        )
        for i in range(gates)
    ]
    return WorldModelSnapshot(
        tool_live_status=tool_statuses,
        permission_gates=permission_gates,
        unresolved_fields=[f'field_{i}' for i in range(unresolved)],
        worker_pool_snapshot=worker_pool or {},
    )


def _make_findings(
    *,
    total: int = 10,
    low_confidence: int = 2,
) -> list[SelfExaminationFinding]:
    findings: list[SelfExaminationFinding] = []
    for i in range(total):
        conf = 0.5 if i < low_confidence else 0.85
        findings.append(SelfExaminationFinding(
            category=f'cat_{i}',
            title=f'Finding {i}',
            summary=f'Summary {i}',
            confidence=conf,
            status='observed',
        ))
    return findings


# ---------------------------------------------------------------------------
# Tests: _universal_autonomy_index_findings
# ---------------------------------------------------------------------------

class TestUniversalAutonomyIndex:

    def test_insufficient_data_returns_unresolved(self):
        oses = _make_oses()
        result = oses._universal_autonomy_index_findings(
            recent_runs=[_make_run()],
            adaptive_sessions=[],
            experiment_runs=[],
            world=_make_world(),
            findings_so_far=[],
        )
        assert len(result) == 1
        assert result[0].category == 'autonomy_index_insufficient_data'
        assert result[0].status == 'unresolved'

    def test_sufficient_data_produces_index_finding(self):
        oses = _make_oses()
        runs = [_make_run(status=RunStatus.SUCCESS) for _ in range(5)]
        experiments = [_make_experiment() for _ in range(4)]
        sessions = [_make_session() for _ in range(3)]
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(),
            findings_so_far=_make_findings(),
        )
        assert any(f.category == 'universal_autonomy_index' for f in result)
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        assert 'autonomy_score' in idx.metadata
        assert 'resilience_score' in idx.metadata
        assert 'calibration_error' in idx.metadata
        assert 'blind_spot_ratio' in idx.metadata
        assert 'verdict' in idx.metadata

    def test_high_success_rate_gives_high_autonomy(self):
        oses = _make_oses()
        runs = [_make_run(status=RunStatus.SUCCESS) for _ in range(10)]
        experiments = [
            _make_experiment(success=True, confidence=0.9, assistant_kind=f'a{i}')
            for i in range(5)
        ]
        sessions = [
            _make_session(metadata={'checkpoint_saved': True})
            for _ in range(5)
        ]
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(tools=5, unresolved=0, gates=0),
            findings_so_far=_make_findings(total=10, low_confidence=0),
        )
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        assert idx.metadata['autonomy_score'] >= 0.80
        # ResilienceScore depends on fallback coverage, worker diversity
        # and checkpoint coverage — with checkpoints + diverse workers it
        # should be healthy enough for SALUDABLE or at least PARCIAL.
        assert idx.metadata['verdict'] in ('SALUDABLE', 'PARCIAL')
        assert idx.severity in (IssueSeverity.LOW, IssueSeverity.MEDIUM)

    def test_many_handoffs_lower_autonomy(self):
        oses = _make_oses()
        runs = [_make_run() for _ in range(5)]
        experiments = [_make_experiment() for _ in range(4)]
        sessions = [
            _make_session(status=AdaptiveSessionStatus.WAITING_APPROVAL)
            for _ in range(4)
        ] + [_make_session()]
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(),
            findings_so_far=[],
        )
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        # 4/5 blocked → high handoff rate → lower autonomy
        assert idx.metadata['components']['handoff_required_rate'] >= 0.7

    def test_calibration_error_with_overconfident_failures(self):
        oses = _make_oses()
        runs = [_make_run() for _ in range(5)]
        # High confidence but all fail → big calibration error
        experiments = [
            _make_experiment(success=False, confidence=0.95)
            for _ in range(6)
        ]
        sessions = [_make_session() for _ in range(3)]
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(),
            findings_so_far=_make_findings(),
        )
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        assert idx.metadata['calibration_error'] > 0.5
        # Should also emit calibration drift finding
        drift = [f for f in result if f.category == 'autonomy_calibration_drift']
        assert len(drift) == 1

    def test_blind_spot_ratio_counts_low_confidence_observed(self):
        oses = _make_oses()
        runs = [_make_run() for _ in range(5)]
        experiments = [_make_experiment() for _ in range(4)]
        sessions = [_make_session() for _ in range(3)]
        findings_in = _make_findings(total=10, low_confidence=7)
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(),
            findings_so_far=findings_in,
        )
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        assert idx.metadata['blind_spot_ratio'] >= 0.5

    def test_worker_diversity_from_experiments(self):
        oses = _make_oses()
        runs = [_make_run() for _ in range(5)]
        experiments = [
            _make_experiment(assistant_kind=kind)
            for kind in ['gemini', 'groq', 'chatgpt', 'claude', 'ollama']
        ]
        sessions = [_make_session() for _ in range(3)]
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(tools=5),
            findings_so_far=[],
        )
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        assert idx.metadata['components']['worker_diversity'] >= 0.9

    def test_resume_success_rate(self):
        oses = _make_oses()
        runs = [_make_run() for _ in range(5)]
        experiments = [_make_experiment() for _ in range(4)]
        sessions = [
            _make_session(
                status=AdaptiveSessionStatus.COMPLETED,
                metadata={'resumed_from': 'hint_1'},
            ),
            _make_session(
                status=AdaptiveSessionStatus.COMPLETED,
                metadata={'resume_hint_id': 'hint_2'},
            ),
            _make_session(status=AdaptiveSessionStatus.COMPLETED),
            _make_session(status=AdaptiveSessionStatus.COMPLETED),
        ]
        result = oses._universal_autonomy_index_findings(
            recent_runs=runs,
            adaptive_sessions=sessions,
            experiment_runs=experiments,
            world=_make_world(),
            findings_so_far=[],
        )
        idx = next(f for f in result if f.category == 'universal_autonomy_index')
        # No interrupted sessions → resume_success_rate defaults to 1.0
        assert idx.metadata['components']['resume_success_rate'] == 1.0


# ---------------------------------------------------------------------------
# Tests: ControlMasterDigest autonomy_metrics_brief
# ---------------------------------------------------------------------------

class TestDigestAutonomyMetrics:

    def test_render_autonomy_metrics_empty(self):
        assert _render_autonomy_metrics(None) == ""
        assert _render_autonomy_metrics({}) == ""

    def test_render_autonomy_metrics_full(self):
        metrics = {
            'autonomy_score': 0.85,
            'resilience_score': 0.72,
            'calibration_error': 0.08,
            'blind_spot_ratio': 0.15,
            'verdict': 'SALUDABLE',
        }
        result = _render_autonomy_metrics(metrics)
        assert 'autonomy=85%' in result
        assert 'resilience=72%' in result
        assert 'calibration_err=0.08' in result
        assert 'blind_spots=15%' in result
        assert 'verdict=SALUDABLE' in result

    def test_digest_builder_includes_autonomy(self):
        state = ControlMasterState()
        builder = ControlMasterDigestBuilder()
        metrics = {
            'autonomy_score': 0.75,
            'resilience_score': 0.60,
            'calibration_error': 0.12,
            'blind_spot_ratio': 0.25,
            'verdict': 'PARCIAL',
        }
        digest = builder.build(state, autonomy_metrics=metrics)
        assert 'autonomy=75%' in digest.autonomy_metrics_brief
        assert 'PARCIAL' in digest.autonomy_metrics_brief

    def test_digest_markdown_includes_autonomy_line(self):
        digest = ControlMasterDigest(
            autonomy_metrics_brief='autonomy=80% | resilience=70% | verdict=PARCIAL',
        )
        md = render_digest_markdown(digest)
        assert 'Autonomia:' in md
        assert 'autonomy=80%' in md

    def test_digest_builder_without_autonomy_metrics(self):
        state = ControlMasterState()
        builder = ControlMasterDigestBuilder()
        digest = builder.build(state)
        assert digest.autonomy_metrics_brief == ""

    def test_truncation_drops_autonomy_first(self):
        state = ControlMasterState(
            current_vision='V' * 1500,
        )
        metrics = {
            'autonomy_score': 0.85,
            'resilience_score': 0.72,
            'calibration_error': 0.08,
            'blind_spot_ratio': 0.15,
            'verdict': 'SALUDABLE',
        }
        # First verify it would be included without tight limit
        builder_big = ControlMasterDigestBuilder(max_chars=3000)
        digest_big = builder_big.build(state, autonomy_metrics=metrics)
        assert digest_big.autonomy_metrics_brief != ""
        # Now force truncation with a very tight limit
        builder = ControlMasterDigestBuilder(max_chars=1540)
        digest = builder.build(state, autonomy_metrics=metrics)
        # When truncating, autonomy_metrics_brief is dropped first
        assert digest.autonomy_metrics_brief == ""
