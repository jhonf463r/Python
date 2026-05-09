"""Tests for the Control Center freeze fix.

Covers:
- ToolRecordRepository.latest_results_by_task_ids() batch API
- AutonomyActivityProjector.project() uses batch instead of N+1
- ControlCenterViewModel._refresh_autonomy_dock_async() runs off UI thread
- UIBridgeService readiness contract preserved
- Regression: existing list_results() not broken
"""
from __future__ import annotations

import shutil
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    TaskRole,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_repo() -> tuple[ToolRecordRepository, Path]:
    root = _workspace('freeze_fix')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    return ToolRecordRepository(db, storage), root


def _save_task(repo: ToolRecordRepository, tool_id: str = 'codex_installed') -> ToolTask:
    task = ToolTask(
        tool_id=tool_id,
        title='Test task',
        objective='test',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'updated_at_utc': datetime.now(timezone.utc).isoformat(),
            'consultation_scope': 'external_assistant',
        },
    )
    repo.save_task(task)
    return task


def _save_result(repo: ToolRecordRepository, task: ToolTask, *, ts_suffix: str = '00') -> ToolResult:
    result = ToolResult(
        task_id=task.task_id,
        tool_id=task.tool_id,
        tool_type=ToolType.SHELL,
        success=True,
        validation_status=ToolValidationStatus.APPROVED,
        execution_state=ExecutionState(state='executed', detail='ok', sandboxed=False, validated=True),
        output_text='ok',
        created_at_utc=datetime.fromisoformat(f'2026-04-02T00:00:{ts_suffix}+00:00'),
    )
    repo.save_result(result)
    return result


# ── ToolRecordRepository batch API ──────────────────────────────────

def test_latest_results_by_task_ids_returns_dict() -> None:
    """Batch API returns dict[str, ToolResult] keyed by task_id."""
    repo, root = _make_repo()
    try:
        t1 = _save_task(repo, 'codex_installed')
        t2 = _save_task(repo, 'claude_installed')
        _save_result(repo, t1, ts_suffix='01')
        _save_result(repo, t2, ts_suffix='02')

        result = repo.latest_results_by_task_ids([t1.task_id, t2.task_id])

        assert isinstance(result, dict)
        assert t1.task_id in result
        assert t2.task_id in result
        assert isinstance(result[t1.task_id], ToolResult)
        assert isinstance(result[t2.task_id], ToolResult)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_latest_results_by_task_ids_returns_latest() -> None:
    """When multiple results exist per task, returns the most recent."""
    repo, root = _make_repo()
    try:
        t1 = _save_task(repo)
        old = _save_result(repo, t1, ts_suffix='01')
        new = _save_result(repo, t1, ts_suffix='59')

        result = repo.latest_results_by_task_ids([t1.task_id])

        assert result[t1.task_id].result_id == new.result_id
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_latest_results_by_task_ids_single_query() -> None:
    """Batch API executes a single SQL query, not N queries."""
    repo, root = _make_repo()
    try:
        tasks = [_save_task(repo, f'tool_{i}') for i in range(5)]
        for t in tasks:
            _save_result(repo, t, ts_suffix='01')

        call_count = {'n': 0}
        original_fetchall = repo.db.fetchall

        def counting_fetchall(*args, **kwargs):
            call_count['n'] += 1
            return original_fetchall(*args, **kwargs)

        repo.db.fetchall = counting_fetchall  # type: ignore[method-assign]

        task_ids = [t.task_id for t in tasks]
        result = repo.latest_results_by_task_ids(task_ids)

        assert call_count['n'] == 1, f'Expected 1 SQL call, got {call_count["n"]}'
        assert len(result) == 5
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_latest_results_by_task_ids_empty_input() -> None:
    """Empty task_ids returns empty dict without hitting DB."""
    repo, root = _make_repo()
    try:
        result = repo.latest_results_by_task_ids([])
        assert result == {}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_latest_results_by_task_ids_missing_task() -> None:
    """Unknown task_ids are simply absent from the result."""
    repo, root = _make_repo()
    try:
        result = repo.latest_results_by_task_ids(['nonexistent-id'])
        assert result == {}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_list_results_still_works() -> None:
    """Existing list_results() API is not broken by batch addition."""
    repo, root = _make_repo()
    try:
        t1 = _save_task(repo)
        r1 = _save_result(repo, t1, ts_suffix='01')

        results = repo.list_results(task_id=t1.task_id, limit=1)
        assert len(results) == 1
        assert results[0].result_id == r1.result_id
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ── AutonomyActivityProjector uses batch ────────────────────────────

def test_projector_uses_batch_api() -> None:
    """project() uses latest_results_by_task_ids instead of N calls to list_results."""
    repo, root = _make_repo()
    try:
        t1 = _save_task(repo, 'codex_installed')
        t2 = _save_task(repo, 'claude_installed')
        _save_result(repo, t1, ts_suffix='01')
        _save_result(repo, t2, ts_suffix='02')

        from iabv_v15.services.evolution.autonomy_activity_projector import AutonomyActivityProjector
        projector = AutonomyActivityProjector(tool_record_repository=repo)

        list_results_calls = {'n': 0}
        original_list_results = repo.list_results

        def counting_list_results(**kwargs):
            list_results_calls['n'] += 1
            return original_list_results(**kwargs)

        repo.list_results = counting_list_results  # type: ignore[method-assign]

        projected = projector.project()

        assert list_results_calls['n'] == 0, (
            f'project() should not call list_results(), but called it {list_results_calls["n"]} times'
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_projector_project_returns_expected_keys() -> None:
    """project() still returns live_process_summary, live_work_items, etc."""
    repo, root = _make_repo()
    try:
        from iabv_v15.services.evolution.autonomy_activity_projector import AutonomyActivityProjector
        projector = AutonomyActivityProjector(tool_record_repository=repo)
        projected = projector.project()
        assert 'live_process_summary' in projected
        assert 'live_work_items' in projected
        assert 'assistant_session_cards' in projected
        assert 'autonomy_timeline' in projected
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ── ControlCenterViewModel async refresh ────────────────────────────

def test_refresh_autonomy_dock_async_runs_off_ui_thread() -> None:
    """_refresh_autonomy_dock_async() delegates projection to _bg_pool."""
    from iabv_v15.bootstrap import AppBootstrap

    workspace = Path.cwd() / 'data' / f'test_freeze_fix_async_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.control_center_viewmodel
        assert vm is not None

        projection_thread_names: list[str] = []
        original_project = vm.autonomy_activity_projector.project if vm.autonomy_activity_projector else None

        if original_project is not None:
            def tracking_project(**kwargs):
                projection_thread_names.append(threading.current_thread().name)
                return original_project(**kwargs)

            vm.autonomy_activity_projector.project = tracking_project  # type: ignore[method-assign]

        vm._refresh_autonomy_dock_async()
        time.sleep(1.0)

        if projection_thread_names:
            assert any('ccvm-bg' in name for name in projection_thread_names), (
                f'Projection ran on threads: {projection_thread_names}, expected ccvm-bg pool'
            )
    finally:
        stop = getattr(bootstrap, 'stop', None)
        if callable(stop):
            stop()
        shutil.rmtree(workspace, ignore_errors=True)


def test_refresh_autonomy_dock_generation_coalesces() -> None:
    """Multiple rapid calls to _refresh_autonomy_dock_async do not pile up work."""
    from iabv_v15.bootstrap import AppBootstrap

    workspace = Path.cwd() / 'data' / f'test_freeze_fix_gen_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.control_center_viewmodel
        assert vm is not None
        vm._autonomy_dock_rest_window_started_at = time.monotonic() - 300.0

        # Read generation after bootstrap (may have been incremented by deferred init)
        gen_before = vm._autonomy_dock_generation
        vm._refresh_autonomy_dock_async()
        gen_1 = vm._autonomy_dock_generation
        vm._refresh_autonomy_dock_async()
        gen_2 = vm._autonomy_dock_generation
        vm._refresh_autonomy_dock_async()
        gen_3 = vm._autonomy_dock_generation

        assert gen_1 == gen_before + 1
        assert gen_2 == gen_1
        assert gen_3 == gen_1
    finally:
        stop = getattr(bootstrap, 'stop', None)
        if callable(stop):
            stop()
        shutil.rmtree(workspace, ignore_errors=True)


def test_public_refresh_autonomy_dock_slot_is_non_blocking() -> None:
    """QML entrypoint delegates to async refresh instead of sync projection."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self.async_calls = 0
            self.sync_calls = 0

        def _refresh_autonomy_dock_async(self, **_kwargs: Any) -> None:
            self.async_calls += 1

        def _refresh_autonomy_dock(self) -> None:
            self.sync_calls += 1

    dummy = DummyViewModel()

    ControlCenterViewModel.refreshAutonomyDock(dummy)  # type: ignore[arg-type]

    assert dummy.async_calls == 1
    assert dummy.sync_calls == 0


def test_autonomy_dock_projection_applies_on_matching_generation() -> None:
    """UI projection apply is isolated from the worker callback."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._autonomy_dock_generation = 7
            self._autonomy_dock_last_fingerprint = ''
            self._autonomy_dock_status = ''
            self._autonomy_dock_last_result = ''
            self._autonomy_dock_last_summary = ''
            self.dataChanged = Emitter()
            self.autonomyDockChanged = Emitter()
            self.autonomyDockStatusChanged = Emitter()
            self.traces: list[dict[str, Any]] = []

        def _trace_autonomy_dock(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

        def _process_rss_mb(self) -> float:
            return 123.4

    dummy = DummyViewModel()
    projected = {
        'live_process_summary': {'status': 'ok'},
        'live_work_items': [{'task_id': 'task-1'}],
        'assistant_session_cards': [{'assistant_kind': 'chatgpt'}],
        'autonomy_timeline': [{'trace_id': 'trace-1'}],
    }

    ControlCenterViewModel._apply_autonomy_dock_projection(dummy, 7, projected)  # type: ignore[arg-type]

    assert dummy._live_process_summary == {'status': 'ok'}
    assert dummy._live_work_items == [{'task_id': 'task-1'}]
    assert dummy._assistant_session_cards == [{'assistant_kind': 'chatgpt'}]
    assert dummy._autonomy_timeline == [{'trace_id': 'trace-1'}]
    assert dummy.dataChanged.count == 0
    assert dummy.autonomyDockChanged.count == 1
    assert dummy.autonomyDockStatusChanged.count == 1
    assert dummy.traces[-1]['kind'] == 'control_autonomy_dock_refresh_applied'
    assert dummy.traces[-1]['rss_mb'] == 123.4
    assert dummy.traces[-1]['emitted_signals'] == ['autonomyDockStatusChanged', 'autonomyDockChanged']


def test_autonomy_dock_projection_ignores_stale_generation() -> None:
    """Older background projections cannot overwrite newer dock state."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._autonomy_dock_generation = 8
            self._live_process_summary = {'status': 'new'}
            self.dataChanged = Emitter()
            self.autonomyDockChanged = Emitter()
            self.autonomyDockStatusChanged = Emitter()

    dummy = DummyViewModel()

    ControlCenterViewModel._apply_autonomy_dock_projection(  # type: ignore[arg-type]
        dummy,
        7,
        {'live_process_summary': {'status': 'old'}},
    )

    assert dummy._live_process_summary == {'status': 'new'}
    assert dummy.dataChanged.count == 0
    assert dummy.autonomyDockChanged.count == 0


def test_autonomy_dock_projection_unchanged_emits_status_only() -> None:
    """Repeated equal projection must not re-evaluate the whole dock QML tree."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._autonomy_dock_generation = 7
            self._autonomy_dock_last_fingerprint = ''
            self._autonomy_dock_status = ''
            self._autonomy_dock_last_result = ''
            self._autonomy_dock_last_summary = ''
            self.dataChanged = Emitter()
            self.autonomyDockChanged = Emitter()
            self.autonomyDockStatusChanged = Emitter()
            self.traces: list[dict[str, Any]] = []

        def _trace_autonomy_dock(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

        def _process_rss_mb(self) -> float:
            return 123.4

    projected = {
        'live_process_summary': {'status': 'ok'},
        'live_work_items': [{'task_id': 'task-1'}],
        'assistant_session_cards': [{'assistant_kind': 'chatgpt'}],
        'autonomy_timeline': [{'trace_id': 'trace-1'}],
    }
    dummy = DummyViewModel()
    ControlCenterViewModel._apply_autonomy_dock_projection(dummy, 7, dict(projected))  # type: ignore[arg-type]
    dummy.autonomyDockChanged.count = 0
    dummy.autonomyDockStatusChanged.count = 0
    dummy.dataChanged.count = 0
    ControlCenterViewModel._apply_autonomy_dock_projection(dummy, 7, dict(projected))  # type: ignore[arg-type]

    assert dummy._autonomy_dock_last_result == 'unchanged'
    assert dummy.dataChanged.count == 0
    assert dummy.autonomyDockChanged.count == 0
    assert dummy.autonomyDockStatusChanged.count == 1
    assert dummy.traces[-1]['rss_mb'] == 123.4
    assert dummy.traces[-1]['emitted_signals'] == ['autonomyDockStatusChanged']


def test_manual_autonomy_dock_refresh_bypasses_cooldown() -> None:
    """Manual QML button must force refresh while timer ticks stay throttled."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def _refresh_autonomy_dock_async(self, **kwargs: Any) -> None:
            self.calls.append(kwargs)

    dummy = DummyViewModel()

    ControlCenterViewModel.refreshAutonomyDock(dummy)  # type: ignore[arg-type]
    ControlCenterViewModel.refreshAutonomyDockFromUser(dummy)  # type: ignore[arg-type]

    assert dummy.calls[0] == {'source': 'timer', 'force': False}
    assert dummy.calls[1] == {'source': 'user_click', 'force': True}


def test_qml_autonomy_dock_timer_pauses_while_chat_working() -> None:
    """The live dock timer must not run while the user is waiting on chat."""
    qml = Path('src/iabv_v15/ui/qml/pages/ControlCenterPage.qml').read_text(encoding='utf-8')

    assert '!workingState' in qml
    assert 'workingState\n            ||' not in qml
    assert 'controlCenterViewModel.refreshAutonomyDock()' in qml


def test_timer_autonomy_dock_refresh_deferred_during_visible_query() -> None:
    """Timer refreshes are suspended while foreground query work is active."""
    from iabv_v15.bootstrap import AppBootstrap

    workspace = Path.cwd() / 'data' / f'test_freeze_fix_query_defer_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.control_center_viewmodel
        assert vm is not None
        traces: list[dict[str, Any]] = []

        def trace(kind: str, **data: Any) -> None:
            traces.append({'kind': kind, **data})

        vm._trace_autonomy_dock = trace  # type: ignore[method-assign]
        vm._working = True
        vm._live_status = 'processing'
        vm._refresh_autonomy_dock_async(source='timer', force=False)

        assert vm._autonomy_dock_refresh_in_flight is False
        assert traces[-1]['kind'] == 'control_autonomy_dock_refresh_deferred'
        assert traces[-1]['reason'] == 'visible_query_wait_active'
    finally:
        stop = getattr(bootstrap, 'stop', None)
        if callable(stop):
            stop()
        shutil.rmtree(workspace, ignore_errors=True)


def test_timer_autonomy_dock_skip_trace_is_rate_limited() -> None:
    """Routine timer skip telemetry is sparse, not one sync file write per tick."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self.traces: list[dict[str, Any]] = []
            self._autonomy_dock_last_skip_trace_key = ''
            self._autonomy_dock_last_skip_trace_at = 0.0

        def _trace_autonomy_dock(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

    dummy = DummyViewModel()

    ControlCenterViewModel._trace_autonomy_dock_skip_once(  # type: ignore[arg-type]
        dummy,
        event='control_autonomy_dock_refresh_skipped',
        source='timer',
        reason='in_flight',
    )
    ControlCenterViewModel._trace_autonomy_dock_skip_once(  # type: ignore[arg-type]
        dummy,
        event='control_autonomy_dock_refresh_skipped',
        source='timer',
        reason='in_flight',
    )

    assert len(dummy.traces) == 1
    assert dummy.traces[0]['reason'] == 'in_flight'


def test_timer_autonomy_dock_refresh_waits_for_rest_window() -> None:
    """Timer-driven dock work must wait until the user/system has a rest window."""
    from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self.adaptive_orchestrator = SimpleNamespace(autonomy_governance_policy=AutonomyGovernancePolicy())
            self._working = False
            self._live_status = 'idle'
            self._active_interaction_id = ''
            self._provider_refreshing = False
            self._ui_heartbeat_watchdog = None
            self._autonomy_dock_rest_window_started_at = time.monotonic()
            self._autonomy_dock_last_budget_decision: dict[str, Any] = {}

        def _process_rss_mb(self) -> float:
            return 210.0

        def _visible_query_wait_active(self) -> bool:
            return ControlCenterViewModel._visible_query_wait_active(self)  # type: ignore[arg-type]

        def _recent_ui_stall_ms(self) -> float:
            return 0.0

        def _autonomy_dock_budget_decision(self, **kwargs: Any) -> dict[str, Any]:
            return ControlCenterViewModel._autonomy_dock_budget_decision(self, **kwargs)  # type: ignore[arg-type]

    dummy = DummyViewModel()

    reason, rss_mb = ControlCenterViewModel._autonomy_dock_defer_reason(  # type: ignore[arg-type]
        dummy,
        source='timer',
        force=False,
    )

    assert reason == 'rest_window_not_reached'
    assert rss_mb == 210.0
    assert dummy._autonomy_dock_last_budget_decision['decision_source'] == (
        'autonomy_governance_policy.operational_budget'
    )


def test_user_click_autonomy_dock_refresh_bypasses_rest_window_when_safe() -> None:
    """Manual refresh can run before the rest window if resources are safe."""
    from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self.adaptive_orchestrator = SimpleNamespace(autonomy_governance_policy=AutonomyGovernancePolicy())
            self._working = False
            self._live_status = 'idle'
            self._active_interaction_id = ''
            self._provider_refreshing = False
            self._ui_heartbeat_watchdog = None
            self._autonomy_dock_rest_window_started_at = time.monotonic()
            self._autonomy_dock_last_budget_decision: dict[str, Any] = {}

        def _process_rss_mb(self) -> float:
            return 210.0

        def _visible_query_wait_active(self) -> bool:
            return ControlCenterViewModel._visible_query_wait_active(self)  # type: ignore[arg-type]

        def _recent_ui_stall_ms(self) -> float:
            return 0.0

        def _autonomy_dock_budget_decision(self, **kwargs: Any) -> dict[str, Any]:
            return ControlCenterViewModel._autonomy_dock_budget_decision(self, **kwargs)  # type: ignore[arg-type]

    dummy = DummyViewModel()

    reason, rss_mb = ControlCenterViewModel._autonomy_dock_defer_reason(  # type: ignore[arg-type]
        dummy,
        source='user_click',
        force=True,
    )

    assert reason == ''
    assert rss_mb == 210.0
    assert dummy._autonomy_dock_last_budget_decision['allowed'] is True


def test_user_click_autonomy_dock_refresh_is_deferred_under_rss_pressure() -> None:
    """Even manual refresh must not force a heavy organ under memory pressure."""
    from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self.adaptive_orchestrator = SimpleNamespace(autonomy_governance_policy=AutonomyGovernancePolicy())
            self._working = False
            self._live_status = 'idle'
            self._active_interaction_id = ''
            self._provider_refreshing = False
            self._ui_heartbeat_watchdog = None
            self._autonomy_dock_rest_window_started_at = time.monotonic() - 300.0
            self._autonomy_dock_last_budget_decision: dict[str, Any] = {}

        def _process_rss_mb(self) -> float:
            return 3200.0

        def _visible_query_wait_active(self) -> bool:
            return ControlCenterViewModel._visible_query_wait_active(self)  # type: ignore[arg-type]

        def _recent_ui_stall_ms(self) -> float:
            return 0.0

        def _autonomy_dock_budget_decision(self, **kwargs: Any) -> dict[str, Any]:
            return ControlCenterViewModel._autonomy_dock_budget_decision(self, **kwargs)  # type: ignore[arg-type]

    dummy = DummyViewModel()

    reason, rss_mb = ControlCenterViewModel._autonomy_dock_defer_reason(  # type: ignore[arg-type]
        dummy,
        source='user_click',
        force=True,
    )

    assert reason == 'resource_pressure_high'
    assert rss_mb == 3200.0
    assert dummy._autonomy_dock_last_budget_decision['allowed'] is False


def test_chat_display_text_truncates_large_auto_analysis_for_ui() -> None:
    """Large self-analysis reports stay persisted but are compact in QML."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    raw = 'x' * (ControlCenterViewModel._CHAT_INLINE_TEXT_LIMIT + 500)
    display = ControlCenterViewModel._chat_display_text(raw)

    assert len(display) < len(raw)
    assert 'historial local' in display
    assert 'mantener la UI fluida' in display


def test_release_visible_query_wait_clears_watchdog_query_pending() -> None:
    """Background follow-up must not leave the visible query flag stuck."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyWatchdog:
        def __init__(self) -> None:
            self.query_values: list[bool] = []

        def set_query_pending(self, value: bool) -> None:
            self.query_values.append(value)

    class DummyViewModel:
        def __init__(self) -> None:
            self._ui_heartbeat_watchdog = DummyWatchdog()
            self._live_status = 'processing'
            self._active_interaction_id = 'chat-test'

        def _set_live_status(self, status: str) -> None:
            self._live_status = status

    dummy = DummyViewModel()

    ControlCenterViewModel._release_visible_query_wait(  # type: ignore[arg-type]
        dummy,
        reason='background_followup:prepared',
    )

    assert dummy._ui_heartbeat_watchdog.query_values == [False]
    assert dummy._live_status == 'idle'


def test_build_development_packet_slot_is_non_blocking() -> None:
    """Manual QML packet rebuild delegates to background refresh."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool]] = []
            self._busy_label = ''
            self.dataChanged = Emitter()

        def _refresh_development_packet_async(self, text: str, *, force: bool = False) -> None:
            self.calls.append((text, force))

        def _refresh_development_packet(self, text: str, *, force: bool = False) -> None:
            raise AssertionError('sync development packet refresh must not run from QML slot')

    dummy = DummyViewModel()

    ControlCenterViewModel.buildDevelopmentPacket(dummy, 'estado actual')  # type: ignore[arg-type]

    assert dummy.calls == [('estado actual', True)]
    assert 'segundo plano' in dummy._busy_label
    assert dummy.dataChanged.count == 1


def test_development_packet_apply_ignores_stale_generation() -> None:
    """Older packet builds cannot overwrite the latest packet."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._development_packet_generation = 2
            self._development_packet = 'new packet'
            self.dataChanged = Emitter()

    dummy = DummyViewModel()

    ControlCenterViewModel._apply_development_packet(dummy, 1, 'old packet')  # type: ignore[arg-type]

    assert dummy._development_packet == 'new packet'
    assert dummy.dataChanged.count == 0


def test_development_packet_apply_accepts_current_generation() -> None:
    """Current async packet result is applied on the UI side."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._development_packet_generation = 3
            self._development_packet = ''
            self.dataChanged = Emitter()

    dummy = DummyViewModel()

    ControlCenterViewModel._apply_development_packet(dummy, 3, 'packet ready')  # type: ignore[arg-type]

    assert dummy._development_packet == 'packet ready'
    assert dummy.dataChanged.count == 1


def test_evolution_snapshot_apply_ignores_stale_generation() -> None:
    """Older evolution snapshots cannot overwrite current UI state."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._evolution_snapshot_generation = 4
            self._evolution_overview = {'status': 'new'}
            self.dataChanged = Emitter()

    dummy = DummyViewModel()

    ControlCenterViewModel._apply_evolution_snapshot(  # type: ignore[arg-type]
        dummy,
        3,
        {'overview': {'status': 'old'}},
    )

    assert dummy._evolution_overview == {'status': 'new'}
    assert dummy.dataChanged.count == 0


def test_evolution_snapshot_apply_accepts_current_generation() -> None:
    """Current async evolution snapshot result updates the UI model."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._evolution_snapshot_generation = 5
            self.dataChanged = Emitter()

    dummy = DummyViewModel()
    snapshot = {
        'overview': {'status': 'active'},
        'area_cards': [{'title': 'Aprendizaje'}],
        'blockers': [{'title': 'Bloqueo'}],
    }

    ControlCenterViewModel._apply_evolution_snapshot(dummy, 5, snapshot)  # type: ignore[arg-type]

    assert dummy._evolution_overview == {'status': 'active'}
    assert dummy._evolution_area_cards == [{'title': 'Aprendizaje'}]
    assert dummy._evolution_blockers == [{'title': 'Bloqueo'}]
    assert dummy.dataChanged.count == 1


def test_agent_cards_apply_accepts_current_generation() -> None:
    """Current async agent card result updates the UI model."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._agent_cards_generation = 4
            self._agent_cards = []
            self.dataChanged = Emitter()

    dummy = DummyViewModel()

    ControlCenterViewModel._apply_agent_cards(  # type: ignore[arg-type]
        dummy,
        4,
        [{'name': 'Tool registry', 'status': 'listo'}],
    )

    assert dummy._agent_cards == [{'name': 'Tool registry', 'status': 'listo'}]
    assert dummy.dataChanged.count == 1


def test_agent_cards_apply_ignores_stale_generation() -> None:
    """Older background card builds cannot overwrite newer UI state."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyViewModel:
        def __init__(self) -> None:
            self._agent_cards_generation = 8
            self._agent_cards = [{'name': 'actual'}]
            self.dataChanged = Emitter()

    dummy = DummyViewModel()

    ControlCenterViewModel._apply_agent_cards(  # type: ignore[arg-type]
        dummy,
        7,
        [{'name': 'stale'}],
    )

    assert dummy._agent_cards == [{'name': 'actual'}]
    assert dummy.dataChanged.count == 0


def test_autonomy_dock_async_skips_when_projection_in_flight() -> None:
    """QML timer must not pile up autonomy dock projections."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class BgPool:
        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError('submit must not run while refresh is in-flight')

    dummy = SimpleNamespace(
        _autonomy_dock_refresh_in_flight=True,
        _bg_pool=BgPool(),
        _trace_autonomy_dock=lambda *_args, **_kwargs: None,
    )

    ControlCenterViewModel._refresh_autonomy_dock_async(dummy)  # type: ignore[arg-type]


def test_autonomy_dock_async_respects_min_interval() -> None:
    """Repeated QML timer ticks are coalesced even after the prior run."""
    import time as _time
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class BgPool:
        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError('submit must not run during cooldown')

    dummy = SimpleNamespace(
        _autonomy_dock_refresh_in_flight=False,
        _autonomy_dock_last_refresh_started=_time.monotonic(),
        _autonomy_dock_min_interval_s=8.0,
        _bg_pool=BgPool(),
        _trace_autonomy_dock=lambda *_args, **_kwargs: None,
    )

    ControlCenterViewModel._refresh_autonomy_dock_async(dummy)  # type: ignore[arg-type]


def test_startup_truth_refresh_defers_under_resource_pressure() -> None:
    """Startup truth refresh must not build OSES/PC when resources are hot."""
    from iabv_v15.bootstrap import AppBootstrap

    marks: list[dict[str, Any]] = []
    dummy = SimpleNamespace(
        _truth_refresh_active=True,
        _truth_refresh_attempt=3,
        _timeline=SimpleNamespace(mark=lambda phase, **extra: marks.append({'phase': phase, **extra})),
        operational_self_examination_service=SimpleNamespace(build_review=MagicMock()),
        portable_context_service=SimpleNamespace(build_package=MagicMock()),
        _tracer=SimpleNamespace(trace=MagicMock()),
        _startup_truth_refresh_defer_reason=lambda: 'ram_used_pct_high',
        _metacognition_data_is_stale=lambda: False,
        _push_bootstrap_flags_to_watchdog=MagicMock(),
        _check_startup_followup_done=MagicMock(),
    )

    AppBootstrap._final_startup_truth_refresh(dummy)  # type: ignore[arg-type]

    assert dummy._truth_refresh_active is False
    assert marks and marks[-1]['phase'] == 'startup_truth_refresh_deferred'
    assert marks[-1]['reason'] == 'ram_used_pct_high'
    dummy.operational_self_examination_service.build_review.assert_not_called()
    dummy.portable_context_service.build_package.assert_not_called()


# ── UIBridgeService readiness contract ──────────────────────────────

def test_bridge_readiness_contract_preserved() -> None:
    """readiness_snapshot() returns expected keys and reflects mark_shell_ready."""
    from iabv_v15.services.ui_bridge_service import UIBridgeServer

    bridge = UIBridgeServer(host='127.0.0.1', port=0)

    snap_before = bridge.readiness_snapshot()
    assert snap_before['shell_ready'] is False
    assert snap_before['ready_source'] == ''
    assert 'pending_count' in snap_before
    assert 'deferred_setup_active' in snap_before

    bridge.mark_shell_ready(source='test_fix')

    snap_after = bridge.readiness_snapshot()
    assert snap_after['shell_ready'] is True
    assert snap_after['ready_source'] == 'test_fix'
    assert snap_after['ready_at'] > 0


def test_bridge_mark_shell_ready_idempotent() -> None:
    """Calling mark_shell_ready twice doesn't crash or change source."""
    from iabv_v15.services.ui_bridge_service import UIBridgeServer

    bridge = UIBridgeServer(host='127.0.0.1', port=0)
    bridge.mark_shell_ready(source='first')
    bridge.mark_shell_ready(source='second')

    snap = bridge.readiness_snapshot()
    assert snap['shell_ready'] is True
    assert snap['ready_source'] == 'first'


# ── Dominant phase instrumentation ──────────────────────────────────

def test_dominant_phase_set_during_projection() -> None:
    """_refresh_autonomy_dock_async sets dominant_phase on watchdog during projection."""
    from iabv_v15.bootstrap import AppBootstrap

    workspace = Path.cwd() / 'data' / f'test_freeze_fix_phase_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.control_center_viewmodel
        assert vm is not None

        phases_seen: list[str] = []
        watchdog = SimpleNamespace(
            set_dominant_phase=lambda p: phases_seen.append(p),
            set_query_pending=lambda p: None,
            set_active_interaction=lambda i: None,
            _window_active=True,
            _window_visible=True,
        )
        vm._ui_heartbeat_watchdog = watchdog  # type: ignore[attr-defined]
        vm._autonomy_dock_rest_window_started_at = time.monotonic() - 300.0

        vm._refresh_autonomy_dock_async()
        time.sleep(1.0)

        assert 'control_center_refresh_autonomy_dock' in phases_seen, (
            f'Expected phase set during projection, saw: {phases_seen}'
        )
        assert phases_seen[-1] == '', 'Phase should be cleared after projection'
    finally:
        stop = getattr(bootstrap, 'stop', None)
        if callable(stop):
            stop()
        shutil.rmtree(workspace, ignore_errors=True)
