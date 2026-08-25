"""Tests for audit-fix batch: cpu_frequency, dossier correlation, portable
context tool_coordination, and session_id propagation in ExperimentLab.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from unittest.mock import MagicMock

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    InferenceRequest,
    InferenceResult,
    ReasoningMode,
    RouteDecision,
    RunRecord,
    RunStatus,
)


_BASE = Path(__file__).resolve().parent.parent / 'data'


def _workspace(name: str) -> Path:
    p = _BASE / f'test_{name}_{uuid.uuid4().hex[:8]}'
    p.mkdir(parents=True, exist_ok=True)
    return p


def _minimal_inference_result(**overrides) -> InferenceResult:
    defaults = dict(
        request_id='req-1',
        provider_name='test',
        reasoning_mode=ReasoningMode.LOCAL,
        summary='ok',
        inferred_task='test',
        confidence=0.9,
        raw_output={},
    )
    defaults.update(overrides)
    return InferenceResult(**defaults)


# ---------------------------------------------------------------
# P1: cpu_frequency classification
# ---------------------------------------------------------------
def test_cpu_frequency_classified_as_not_available_on_any_platform() -> None:
    """cpu_frequency missing → sensor_not_exposed_on_this_host (not UNRESOLVED)."""
    from iabv_v15.services.evolution.environment_self_awareness_service import (
        EnvironmentSelfAwarenessService,
    )

    root = _workspace('cpu_freq_fix')
    try:
        evo = root / 'evolution'
        evo.mkdir(parents=True, exist_ok=True)
        svc = EnvironmentSelfAwarenessService(
            workspace_root=str(root), evolution_dir=str(evo),
            auto_start=False, bootstrap_scan=False,
        )
        svc._memory_snapshot = lambda: {}
        svc._disk_snapshot = lambda: {}
        svc._cpu_snapshot = lambda *, full: {}
        svc._gpu_snapshot = lambda *, full: {}
        svc._battery_snapshot = lambda *, full: {}
        svc._detect_throttling = lambda *, cpu_info, gpu_info: False

        _, unresolved = svc._scan_hardware(full=False)
        assert 'UNRESOLVED:cpu_frequency' not in unresolved
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------
# P1: Dossier correlation fields
# ---------------------------------------------------------------
def test_dossier_metadata_includes_correlation_fields() -> None:
    """build_for_run() must emit correlated_session_id, tool_selection_reason, gate_ran."""
    from iabv_v15.services.evolution.execution_dossier_service import (
        ExecutionDossierService,
    )

    mock_repo = MagicMock()
    mock_repo.save = lambda d: d
    mock_hidden = MagicMock()
    mock_hidden.find_by_run = MagicMock(return_value=[])
    mock_clue = MagicMock()
    mock_clue.find_by_run = MagicMock(return_value=[])
    mock_check = MagicMock()
    mock_check.run_light_checks_for_run = MagicMock(return_value=[])
    mock_router = MagicMock()
    mock_router.health_snapshot = MagicMock(return_value=[])

    svc = ExecutionDossierService(
        repository=mock_repo,
        hidden_incident_repository=mock_hidden,
        user_clue_repository=mock_clue,
        self_check_orchestrator=mock_check,
        role_router=mock_router,
    )

    run_record = RunRecord(
        run_id='run-test-123',
        request=InferenceRequest(user_goal='test goal'),
        result=_minimal_inference_result(
            raw_output={
                'adaptive_session': {
                    'session_id': 'sess-abc-123',
                    'metadata': {
                        'tool_selection_summary': {
                            'selected_tool': 'chatgpt',
                            'reason': 'source=auto_ranked',
                        },
                    },
                }
            },
        ),
        route=RouteDecision(primary_provider='ollama', primary_kind='local', reason='test'),
        status=RunStatus.SUCCESS,
    )

    dossier = svc.build_for_run(run_record)
    meta = dossier.metadata

    assert meta['correlated_session_id'] == 'sess-abc-123'
    assert meta['tool_selection_reason'] == 'source=auto_ranked'
    assert meta['gate_ran'] is True


def test_dossier_metadata_gate_not_ran() -> None:
    """When gate didn't run, gate_ran=False and reason='gate_not_ran'."""
    from iabv_v15.services.evolution.execution_dossier_service import (
        ExecutionDossierService,
    )

    mock_repo = MagicMock()
    mock_repo.save = lambda d: d
    mock_hidden = MagicMock()
    mock_hidden.find_by_run = MagicMock(return_value=[])
    mock_clue = MagicMock()
    mock_clue.find_by_run = MagicMock(return_value=[])
    mock_check = MagicMock()
    mock_check.run_light_checks_for_run = MagicMock(return_value=[])
    mock_router = MagicMock()
    mock_router.health_snapshot = MagicMock(return_value=[])

    svc = ExecutionDossierService(
        repository=mock_repo,
        hidden_incident_repository=mock_hidden,
        user_clue_repository=mock_clue,
        self_check_orchestrator=mock_check,
        role_router=mock_router,
    )

    run_record = RunRecord(
        run_id='run-test-456',
        request=InferenceRequest(user_goal='test goal'),
        result=_minimal_inference_result(
            raw_output={
                'adaptive_session': {
                    'session_id': 'sess-xyz-789',
                    'metadata': {
                        'tool_selection_summary': {
                            'selected_tool': '',
                            'reason': 'gate_not_ran',
                        },
                    },
                }
            },
        ),
        route=RouteDecision(primary_provider='ollama', primary_kind='local', reason='test'),
        status=RunStatus.SUCCESS,
    )

    dossier = svc.build_for_run(run_record)
    meta = dossier.metadata

    assert meta['correlated_session_id'] == 'sess-xyz-789'
    assert meta['tool_selection_reason'] == 'gate_not_ran'
    assert meta['gate_ran'] is False


# ---------------------------------------------------------------
# P2: PortableContext tool_coordination includes gate_not_ran sessions
# ---------------------------------------------------------------
def test_tool_coordination_includes_gate_not_ran_sessions() -> None:
    """_tool_coordination_section() must include sessions with reason but no selected_tool."""
    from iabv_v15.services.evolution.portable_context_service import (
        PortableContextService,
    )

    root = _workspace('tool_coord_fix')
    try:
        evo = root / 'evolution'
        evo.mkdir(parents=True, exist_ok=True)

        mock_session = MagicMock()
        mock_session.metadata = {
            'task_packet': {
                'tool_selection_summary': {
                    'selected_tool': '',
                    'reason': 'gate_not_ran',
                    'fallback_used': False,
                    'quota_confirmed': False,
                    'alternatives_discarded': [],
                },
            },
        }

        mock_repo = MagicMock()
        mock_repo.list_recent = MagicMock(return_value=[mock_session])

        svc = PortableContextService.__new__(PortableContextService)
        svc.adaptive_session_repository = mock_repo

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        section = svc._tool_coordination_section(now=now)

        assert len(section.items) == 1
        assert 'gate_not_ran' in section.items[0]['label']
        assert section.confidence == 0.7
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------
# P1: session_id explicit in ExperimentLab.record_outcome()
# ---------------------------------------------------------------
def test_experiment_lab_record_outcome_includes_session_id() -> None:
    """record_outcome() must write session_id explicitly in run metadata."""
    from iabv_v15.services.lab.experiment_lab import ExperimentLab

    root = _workspace('session_id_lab')
    try:
        evo = root / 'evolution'
        evo.mkdir(parents=True, exist_ok=True)

        mock_repo = MagicMock()
        mock_repo.list_runs = MagicMock(return_value=[])
        saved_runs = []

        def capture_run(run):
            saved_runs.append(run)
        mock_repo.save_run = capture_run
        mock_repo.save_recommendation = MagicMock()
        mock_repo.latest_recommendation = MagicMock(return_value=None)

        mock_strategy = MagicMock()
        mock_strategy.recommend = MagicMock(return_value=MagicMock())

        mock_scoring = MagicMock()
        mock_scoring.score = MagicMock(return_value=ExperimentMetric(
            total_score=0.7,
            precision=0.7,
            execution_ms=100,
            operational_cost=0.1,
            robustness=0.8,
            reuse_score=0.5,
            user_progress=0.6,
        ))

        mock_registry = MagicMock()

        lab = ExperimentLab(
            repository=mock_repo,
            registry=mock_registry,
            strategy_selector=mock_strategy,
            scoring_engine=mock_scoring,
        )

        lab.record_outcome(
            domain=ExperimentDomain.LANGUAGE,
            objective='test',
            subject_key='test_key',
            route=EvaluationRoute.LOCAL,
            candidate_label='chatgpt',
            success=True,
            observed_summary='worked',
            metadata={
                'session_id': 'sess-propagation-test',
                'trace_id': 'abc12345',
            },
        )

        assert len(saved_runs) == 1
        run = saved_runs[0]
        assert run.metadata.get('session_id') == 'sess-propagation-test'
        assert run.metadata.get('trace_id') == 'abc12345'
    finally:
        shutil.rmtree(root, ignore_errors=True)
