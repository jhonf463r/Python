"""Tests for TaskOutcomeRecorder — trace_id/session_id propagation and metadata integrity.

Validates that the learning loop correctly propagates correlation IDs
(trace_id, session_id) and key metadata fields into ExperimentRun records,
enabling downstream consumers (StrategySelector, OSES, PortableContext)
to join runs back to their originating sessions.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    EvaluationRoute,
    ExperimentDomain,
    InferenceRequest,
    InferenceResult,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    TaskContext,
    TaskIntent,
    TaskRole,
)


def _workspace(label: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'tor_{label}_{uuid.uuid4().hex[:8]}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_record(*, status: RunStatus = RunStatus.SUCCESS) -> RunRecord:
    return RunRecord(
        request=InferenceRequest(user_goal='test goal'),
        result=InferenceResult(
            request_id='req-1',
            provider_name='ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='test summary',
            inferred_task='test',
            confidence=0.85,
        ),
        route=RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title='Knowledge',
            provider_name='ollama',
            model_profile_id='local',
            model_name='llama3',
            reason='test',
        ),
        status=status,
        duration_ms=100,
    )


def _session(
    *,
    user_goal: str = 'Resolver consulta de prueba',
    status: AdaptiveSessionStatus = AdaptiveSessionStatus.COMPLETED,
    metadata: dict | None = None,
    session_id: str | None = None,
) -> AdaptiveSession:
    s = AdaptiveSession(
        user_goal=user_goal,
        intent=TaskIntent(intent_key='general.assistance'),
        context=TaskContext(),
        status=status,
        metadata=dict(metadata or {}),
    )
    if session_id is not None:
        s.session_id = session_id
    return s


# ---- 1. trace_id propagation ----

def test_record_learning_propagates_trace_id() -> None:
    """trace_id in ExperimentRun metadata must be non-empty after recording."""
    root = _workspace('trace_id')
    try:
        boot = AppBootstrap(str(root))
        session = _session()
        run_record = _run_record()
        boot.task_outcome_recorder.record(session, run_record=run_record)
        runs = boot.experiment_lab.repository.list_runs(
            domain=ExperimentDomain.LANGUAGE.value, subject_key='general', limit=10,
        )
        assert len(runs) >= 1
        latest = runs[-1]
        trace_id = latest.metadata.get('trace_id', '')
        assert trace_id, 'trace_id should not be empty'
        assert len(trace_id) == 8, 'trace_id should be first 8 chars of session_id'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 2. session_id propagation ----

def test_record_learning_propagates_session_id() -> None:
    """session_id in ExperimentRun metadata must match the session."""
    root = _workspace('session_id')
    try:
        boot = AppBootstrap(str(root))
        fixed_id = str(uuid.uuid4())
        session = _session(session_id=fixed_id)
        run_record = _run_record()
        boot.task_outcome_recorder.record(session, run_record=run_record)
        runs = boot.experiment_lab.repository.list_runs(
            domain=ExperimentDomain.LANGUAGE.value, subject_key='general', limit=10,
        )
        assert len(runs) >= 1
        latest = runs[-1]
        assert latest.metadata.get('session_id') == fixed_id
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 3. trace_id fallback when ia_trace_summary empty ----

def test_source_trace_ids_fallback() -> None:
    """When ia_trace_summary is empty, trace_id should be session_id[:8]."""
    root = _workspace('trace_fallback')
    try:
        boot = AppBootstrap(str(root))
        fixed_id = 'abcdef12-3456-7890-abcd-ef1234567890'
        session = _session(session_id=fixed_id)
        run_record = _run_record()
        boot.task_outcome_recorder.record(session, run_record=run_record)
        runs = boot.experiment_lab.repository.list_runs(
            domain=ExperimentDomain.LANGUAGE.value, subject_key='general', limit=10,
        )
        assert len(runs) >= 1
        latest = runs[-1]
        assert latest.metadata.get('trace_id') == fixed_id[:8]
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 4. comparison_scope_key not empty for known intent ----

def test_comparison_scope_key_not_empty() -> None:
    """CSK should be non-empty when a session has a known intent."""
    root = _workspace('csk')
    try:
        boot = AppBootstrap(str(root))
        session = _session(user_goal='Revisar bug en modulo de login')
        run_record = _run_record()
        result = boot.task_outcome_recorder.record(session, run_record=run_record)
        adaptive = result.metadata.get('adaptive_learning', {})
        csk = adaptive.get('comparison_scope_key', '')
        assert csk, 'comparison_scope_key should not be empty'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 5. evidence_basis preserved from task_packet ----

def test_evidence_basis_preserved() -> None:
    """evidence_basis from task_packet should be preserved in run metadata."""
    root = _workspace('evidence_basis')
    try:
        boot = AppBootstrap(str(root))
        evidence = {'source': 'world_model', 'confidence': 0.9}
        session = _session(metadata={'task_packet': {'evidence_basis': evidence}})
        run_record = _run_record()
        boot.task_outcome_recorder.record(session, run_record=run_record)
        runs = boot.experiment_lab.repository.list_runs(
            domain=ExperimentDomain.LANGUAGE.value, subject_key='general', limit=10,
        )
        assert len(runs) >= 1
        latest = runs[-1]
        eb = latest.metadata.get('evidence_basis', {})
        assert eb.get('source') == 'world_model'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 6. linked_run_id present ----

def test_linked_run_id_present() -> None:
    """linked_run_id should match the RunRecord's run_id."""
    root = _workspace('linked_run')
    try:
        boot = AppBootstrap(str(root))
        session = _session()
        run_record = _run_record()
        boot.task_outcome_recorder.record(session, run_record=run_record)
        runs = boot.experiment_lab.repository.list_runs(
            domain=ExperimentDomain.LANGUAGE.value, subject_key='general', limit=10,
        )
        assert len(runs) >= 1
        latest = runs[-1]
        assert latest.metadata.get('linked_run_id') == run_record.run_id
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 7. backward compat with session without task_packet ----

def test_backward_compat_no_task_packet() -> None:
    """Recording should succeed even when session.metadata has no task_packet."""
    root = _workspace('no_packet')
    try:
        boot = AppBootstrap(str(root))
        session = _session(metadata={})
        run_record = _run_record()
        result = boot.task_outcome_recorder.record(session, run_record=run_record)
        assert result is not None
        assert result.session_id == session.session_id
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 8. weight_snapshot generated ----

def test_weight_snapshot_generated() -> None:
    """adaptive_learning in session metadata should contain weight_snapshot."""
    root = _workspace('weight_snap')
    try:
        boot = AppBootstrap(str(root))
        session = _session()
        run_record = _run_record()
        result = boot.task_outcome_recorder.record(session, run_record=run_record)
        adaptive = result.metadata.get('adaptive_learning', {})
        assert adaptive, 'adaptive_learning should be populated'
        records = adaptive.get('records', [])
        assert len(records) >= 1
        assert 'weight_snapshot' in records[0]
    finally:
        shutil.rmtree(root, ignore_errors=True)
