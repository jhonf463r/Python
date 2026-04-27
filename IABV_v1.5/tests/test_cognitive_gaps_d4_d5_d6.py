"""Tests for cognitive gaps D4-D6: CognitiveMonitor, TemporalAwareness, DeepAnalysisQueue.

D4: _background_decision_review_findings — meta-observer via DecisionAuditTrail
D5: _temporal_awareness_findings — latency anomalies, regression, stalled ops
D6: _deep_analysis_queue_findings — EMA drift, correlated failures, IQR outliers

Also tests _record_task_timing / _check_temporal_anomaly on the Orchestrator.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
    InferenceRequest,
    InferenceResult,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    SelfExaminationFinding,
    TaskRole,
    ToolCapability,
    utc_now,
)
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_oses(root: Path) -> OperationalSelfExaminationService:
    from iabv_v15.infra.persistence.storage import ArtifactStorage
    storage = ArtifactStorage(str(root))
    return OperationalSelfExaminationService(
        workspace_root=str(root),
        storage=storage,
    )


def _make_experiment_run(
    *,
    assistant_kind: str = 'ollama',
    success: bool = True,
    execution_ms: int = 100,
) -> ExperimentRun:
    return ExperimentRun(
        domain=ExperimentDomain.CODE,
        suite_name='cognitive_test',
        objective='test',
        subject_key='general',
        route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
        candidate_label=assistant_kind,
        success=success,
        observed_summary='test run',
        assistant_kind=assistant_kind,
        metrics=ExperimentMetric(execution_ms=execution_ms),
    )


def _make_run_record(
    *,
    status: RunStatus = RunStatus.SUCCESS,
    minutes_ago: int = 0,
) -> RunRecord:
    created = utc_now() - timedelta(minutes=minutes_ago)
    request = InferenceRequest(user_goal='test goal')
    result = InferenceResult(
        request_id=request.request_id,
        provider_name='Ollama',
        reasoning_mode=ReasoningMode.LOCAL,
        summary='ok' if status == RunStatus.SUCCESS else 'fallo',
        inferred_task='goal',
        confidence=0.5,
    )
    route = RoleRoute(
        task_role=TaskRole.TRAINING,
        role_title='stub',
        provider_name='Ollama',
        model_profile_id='general-qwen',
        model_name='qwen3:8b',
        tool_chain=[ToolCapability.ANALYTICS],
        reason='stub',
    )
    return RunRecord(
        request=request,
        result=result,
        route=route,
        status=status,
        created_at_utc=created,
    )


# ---------------------------------------------------------------
# D4: Background decision review (CognitiveMonitor)
# ---------------------------------------------------------------


class FakeDecisionAuditTrail:
    def __init__(self, entries: list[dict]) -> None:
        self._entries = entries

    def load_recent(self, limit: int = 100) -> list[dict]:
        return self._entries[-limit:]


def test_background_decision_review_detects_provider_underperformance() -> None:
    root = _workspace('d4_provider')
    try:
        oses = _make_oses(root)
        entries = [
            {'provider_id': 'chatgpt', 'outcome': 'failed', 'confidence': 0.8, 'error_detail': ''},
            {'provider_id': 'chatgpt', 'outcome': 'failed', 'confidence': 0.7, 'error_detail': ''},
            {'provider_id': 'chatgpt', 'outcome': 'failed', 'confidence': 0.6, 'error_detail': ''},
            {'provider_id': 'ollama', 'outcome': 'success', 'confidence': 0.9, 'error_detail': ''},
            {'provider_id': 'ollama', 'outcome': 'success', 'confidence': 0.8, 'error_detail': ''},
        ]
        oses.decision_audit_trail = FakeDecisionAuditTrail(entries)
        findings = oses._background_decision_review_findings(experiment_runs=[])
        categories = [f.category for f in findings]
        assert 'background_provider_underperformance' in categories
        provider_finding = [f for f in findings if f.category == 'background_provider_underperformance'][0]
        assert 'chatgpt' in provider_finding.title
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_background_decision_review_detects_confidence_miscalibration() -> None:
    root = _workspace('d4_confidence')
    try:
        oses = _make_oses(root)
        entries = [
            {'provider_id': 'a', 'outcome': 'failed', 'confidence': 0.2, 'error_detail': ''},
            {'provider_id': 'b', 'outcome': 'timeout', 'confidence': 0.3, 'error_detail': ''},
            {'provider_id': 'c', 'outcome': 'rate_limited', 'confidence': 0.1, 'error_detail': ''},
            {'provider_id': 'd', 'outcome': 'success', 'confidence': 0.9, 'error_detail': ''},
            {'provider_id': 'e', 'outcome': 'success', 'confidence': 0.8, 'error_detail': ''},
        ]
        oses.decision_audit_trail = FakeDecisionAuditTrail(entries)
        findings = oses._background_decision_review_findings(experiment_runs=[])
        categories = [f.category for f in findings]
        assert 'background_confidence_miscalibration' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_background_decision_review_detects_error_stagnation() -> None:
    root = _workspace('d4_errors')
    try:
        oses = _make_oses(root)
        err = 'Connection refused to provider X'
        entries = [
            {'provider_id': f'p{i}', 'outcome': 'success', 'confidence': 0.9, 'error_detail': ''}
            for i in range(5)
        ] + [
            {'provider_id': f'q{i}', 'outcome': 'failed', 'confidence': 0.5, 'error_detail': err}
            for i in range(4)
        ]
        oses.decision_audit_trail = FakeDecisionAuditTrail(entries)
        findings = oses._background_decision_review_findings(experiment_runs=[])
        categories = [f.category for f in findings]
        assert 'background_error_stagnation' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_background_decision_review_no_findings_without_trail() -> None:
    root = _workspace('d4_none')
    try:
        oses = _make_oses(root)
        oses.decision_audit_trail = None
        findings = oses._background_decision_review_findings(experiment_runs=[])
        assert findings == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------
# D5: TemporalAwareness
# ---------------------------------------------------------------


def test_temporal_awareness_detects_latency_anomaly() -> None:
    root = _workspace('d5_latency')
    try:
        oses = _make_oses(root)
        runs = [
            _make_experiment_run(assistant_kind='ollama', execution_ms=5000),
        ] + [
            _make_experiment_run(assistant_kind='ollama', execution_ms=100)
            for _ in range(10)
        ]
        recent_runs = [_make_run_record() for _ in range(5)]
        findings = oses._temporal_awareness_findings(
            recent_runs=recent_runs,
            experiment_runs=runs,
        )
        categories = [f.category for f in findings]
        assert 'temporal_latency_anomaly' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_temporal_awareness_detects_latency_regression() -> None:
    root = _workspace('d5_regression')
    try:
        oses = _make_oses(root)
        runs = (
            [_make_experiment_run(assistant_kind='ollama', execution_ms=500) for _ in range(5)]
            + [_make_experiment_run(assistant_kind='ollama', execution_ms=100) for _ in range(5)]
        )
        recent_runs = [_make_run_record() for _ in range(5)]
        findings = oses._temporal_awareness_findings(
            recent_runs=recent_runs,
            experiment_runs=runs,
        )
        categories = [f.category for f in findings]
        assert 'temporal_latency_regression' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_temporal_awareness_detects_stalled_operations() -> None:
    root = _workspace('d5_stalled')
    try:
        oses = _make_oses(root)
        stalled_runs = [
            _make_run_record(status=RunStatus.PARTIAL, minutes_ago=10)
            for _ in range(3)
        ]
        findings = oses._temporal_awareness_findings(
            recent_runs=stalled_runs,
            experiment_runs=[],
        )
        categories = [f.category for f in findings]
        assert 'temporal_stalled_operations' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_temporal_awareness_no_findings_with_normal_data() -> None:
    root = _workspace('d5_normal')
    try:
        oses = _make_oses(root)
        runs = [_make_experiment_run(execution_ms=100) for _ in range(10)]
        recent_runs = [_make_run_record() for _ in range(5)]
        findings = oses._temporal_awareness_findings(
            recent_runs=recent_runs,
            experiment_runs=runs,
        )
        assert len(findings) == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------
# D6: DeepAnalysisQueue
# ---------------------------------------------------------------


def test_deep_analysis_queue_detects_ema_drift() -> None:
    root = _workspace('d6_ema')
    try:
        oses = _make_oses(root)
        recent_runs = (
            [_make_run_record(status=RunStatus.FAILED) for _ in range(10)]
            + [_make_run_record(status=RunStatus.SUCCESS) for _ in range(10)]
        )
        findings = oses._deep_analysis_queue_findings(
            experiment_runs=[],
            recent_runs=recent_runs,
        )
        categories = [f.category for f in findings]
        assert 'deep_analysis_ema_drift' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deep_analysis_queue_detects_correlated_failures() -> None:
    root = _workspace('d6_correlated')
    try:
        oses = _make_oses(root)
        entries = [
            {'provider_id': 'chatgpt', 'outcome': 'failed', 'timestamp_utc': '2026-04-27T00'},
            {'provider_id': 'ollama', 'outcome': 'failed', 'timestamp_utc': '2026-04-27T00'},
            {'provider_id': 'chatgpt', 'outcome': 'timeout', 'timestamp_utc': '2026-04-27T01'},
            {'provider_id': 'claude', 'outcome': 'failed', 'timestamp_utc': '2026-04-27T01'},
        ] + [
            {'provider_id': f'p{i}', 'outcome': 'success', 'timestamp_utc': f'2026-04-26T{i:02d}'}
            for i in range(8)
        ]
        oses.decision_audit_trail = FakeDecisionAuditTrail(entries)
        findings = oses._deep_analysis_queue_findings(
            experiment_runs=[],
            recent_runs=[],
        )
        categories = [f.category for f in findings]
        assert 'deep_analysis_correlated_failures' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deep_analysis_queue_detects_latency_outliers() -> None:
    root = _workspace('d6_iqr')
    try:
        oses = _make_oses(root)
        runs = (
            [_make_experiment_run(execution_ms=100 + i) for i in range(20)]
            + [_make_experiment_run(execution_ms=10000) for _ in range(5)]
        )
        findings = oses._deep_analysis_queue_findings(
            experiment_runs=runs,
            recent_runs=[],
        )
        categories = [f.category for f in findings]
        assert 'deep_analysis_latency_outliers' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------
# Orchestrator TemporalAwareness: _record_task_timing / _check_temporal_anomaly
# ---------------------------------------------------------------


def test_orchestrator_temporal_awareness_records_timing() -> None:
    from iabv_v15.bootstrap import AppBootstrap
    root = _workspace('orch_timing')
    try:
        bootstrap = AppBootstrap(str(root))
        orch = bootstrap.adaptive_task_orchestrator
        orch._record_task_timing('code_review', 1.5)
        orch._record_task_timing('code_review', 1.2)
        orch._record_task_timing('code_review', 1.8)
        assert len(orch._task_timing_history['code_review']) == 3
        assert orch._task_timing_history['code_review'][0] == 1.8
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orchestrator_temporal_awareness_detects_anomaly() -> None:
    from iabv_v15.bootstrap import AppBootstrap
    root = _workspace('orch_anomaly')
    try:
        bootstrap = AppBootstrap(str(root))
        orch = bootstrap.adaptive_task_orchestrator
        for i in range(10):
            orch._record_task_timing('code_review', 1.0 + i * 0.05)
        anomaly = orch._check_temporal_anomaly('code_review', 10.0)
        assert anomaly is not None
        assert anomaly['anomaly'] is True
        assert anomaly['z_score'] > 2.0
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orchestrator_temporal_awareness_no_anomaly_for_normal_task() -> None:
    from iabv_v15.bootstrap import AppBootstrap
    root = _workspace('orch_normal')
    try:
        bootstrap = AppBootstrap(str(root))
        orch = bootstrap.adaptive_task_orchestrator
        for _ in range(10):
            orch._record_task_timing('code_review', 1.0)
        anomaly = orch._check_temporal_anomaly('code_review', 1.1)
        assert anomaly is None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orchestrator_temporal_awareness_history_is_bounded() -> None:
    from iabv_v15.bootstrap import AppBootstrap
    root = _workspace('orch_bounded')
    try:
        bootstrap = AppBootstrap(str(root))
        orch = bootstrap.adaptive_task_orchestrator
        for i in range(50):
            orch._record_task_timing('code_review', float(i))
        assert len(orch._task_timing_history['code_review']) == orch._TIMING_HISTORY_MAX
    finally:
        shutil.rmtree(root, ignore_errors=True)
