"""Tests for the Control Center freeze fix.

Covers:
- ToolRecordRepository.latest_results_by_task_ids() batch API
- AutonomyActivityProjector.project() uses batch instead of N+1
- ControlCenterViewModel._refresh_autonomy_dock_async() runs off UI thread
- UIBridgeService readiness contract preserved
- Regression: existing list_results() not broken
"""
from __future__ import annotations

import io
import json
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


def _valid_png_bytes() -> bytes:
    from PIL import Image  # type: ignore

    image = Image.new('RGB', (32, 24), color='white')
    for x in range(8, 24):
        for y in range(6, 18):
            image.putpixel((x, y), (20, 80, 160))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


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


def test_qml_exposes_external_evidence_panel() -> None:
    """Blocked external consultations must have a visible evidence panel."""
    qml = Path('src/iabv_v15/ui/qml/pages/ControlCenterPage.qml').read_text(encoding='utf-8')

    assert 'externalEvidencePanelModel' in qml
    assert 'controlCenterViewModel.externalEvidencePanel' in qml
    assert 'Evidencia externa' in qml
    assert 'externalEvidencePanelModel.phases' in qml
    assert 'externalEvidencePanelModel.metadata' in qml
    assert 'externalEvidencePanelModel.visual_evidence' in qml
    assert 'modelData.image_url' in qml


def test_visual_evidence_capture_without_permission_uses_iabv_window(tmp_path: Path) -> None:
    """External visual replay must not capture the desktop before permission."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class FakeProvider:
        def __init__(self) -> None:
            self.regions: list[str] = []

        def capture(self, region: str) -> bytes:
            self.regions.append(region)
            return _valid_png_bytes()

    class FakeWorldModel:
        def permission_snapshot(self) -> list[dict[str, Any]]:
            return []

    class DummyViewModel:
        def __init__(self) -> None:
            self.config = SimpleNamespace(workspace_root=str(tmp_path))
            self.adaptive_orchestrator = SimpleNamespace(
                context_assembler=SimpleNamespace(world_model_service=FakeWorldModel())
            )
            self._external_evidence_panel = {
                'visible': True,
                'title': 'Consulta externa no verificada',
                'status': 'blocked',
                'assistant': 'ChatGPT web asistido',
                'metadata': [],
                'actions': [],
            }
            self._last_adaptive_payload = {}
            self._active_interaction_id = 'chat-visual'
            self.chatChanged = Emitter()
            self.dataChanged = Emitter()
            self.messages: list[dict[str, str]] = []
            self.traces: list[dict[str, Any]] = []

        def _pending_observation_permission_assistant(self) -> str:
            return ''

        def _observation_permission_granted(self, assistant_kind: str) -> bool:
            return ControlCenterViewModel._observation_permission_granted(self, assistant_kind)  # type: ignore[arg-type]

        def _visual_evidence_semantic_summary(self, entry: dict[str, Any]) -> dict[str, Any]:
            return ControlCenterViewModel._visual_evidence_semantic_summary(self, entry)  # type: ignore[arg-type]

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'IABV')

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _set_external_evidence_panel(self, **kwargs: Any) -> None:
            ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _trace_external_followup(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

        def _append_message(self, role: str, speaker: str, text: str, meta: str = '', **_: Any) -> None:
            self.messages.append({'role': role, 'speaker': speaker, 'text': text, 'meta': meta})

    provider = FakeProvider()
    dummy = DummyViewModel()
    with patch('iabv_v15.infra.ui.build_ui_screenshot_provider', return_value=provider):
        entry = ControlCenterViewModel._capture_visual_evidence_snapshot(  # type: ignore[arg-type]
            dummy,
            assistant_kind='chatgpt',
            reason='test',
            announce=False,
        )

    assert provider.regions == ['main']
    assert entry['permission_granted'] is False
    assert 'UNRESOLVED:external_window_content_permission_missing' in entry['unresolved_fields']
    assert entry['semantic_summary']['state_hypothesis'] == 'iabv_window_only_external_unresolved'
    assert 'ocr_text_unresolved' in entry['semantic_summary']['labels']
    assert Path(entry['semantic_path']).exists()
    assert Path(entry['path']).exists()
    panel = dummy._external_evidence_panel
    assert panel['visual_evidence'][0]['image_url'].startswith('file:///')
    assert any(item['action'] == 'approve_observation_permission' for item in panel['actions'])
    assert dummy.traces[-1]['region'] == 'main'
    assert dummy.traces[-1]['permission_granted'] is False


def test_visual_evidence_capture_with_permission_marks_missing_target_window(tmp_path: Path) -> None:
    """Permission alone is not proof that the external assistant window was captured."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def emit(self) -> None:
            pass

    class FakeProvider:
        def __init__(self) -> None:
            self.regions: list[str] = []

        def capture(self, region: str) -> bytes:
            self.regions.append(region)
            return _valid_png_bytes()

    class FakeWorldModel:
        def permission_snapshot(self) -> list[dict[str, Any]]:
            return [{'scope': 'observe_window_content:chatgpt', 'granted': True}]

        def current_model(self) -> Any:
            return SimpleNamespace(active_windows=[])

    class DummyViewModel:
        def __init__(self) -> None:
            self.config = SimpleNamespace(workspace_root=str(tmp_path))
            self.adaptive_orchestrator = SimpleNamespace(
                context_assembler=SimpleNamespace(world_model_service=FakeWorldModel())
            )
            self._external_evidence_panel = {'assistant': 'ChatGPT web asistido', 'metadata': [], 'actions': []}
            self._last_adaptive_payload = {}
            self._active_interaction_id = 'chat-visual'
            self.chatChanged = Emitter()
            self.dataChanged = Emitter()
            self.traces: list[dict[str, Any]] = []

        def _pending_observation_permission_assistant(self) -> str:
            return ''

        def _observation_permission_granted(self, assistant_kind: str) -> bool:
            return ControlCenterViewModel._observation_permission_granted(self, assistant_kind)  # type: ignore[arg-type]

        def _visual_evidence_semantic_summary(self, entry: dict[str, Any]) -> dict[str, Any]:
            return ControlCenterViewModel._visual_evidence_semantic_summary(self, entry)  # type: ignore[arg-type]

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'IABV')

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _set_external_evidence_panel(self, **kwargs: Any) -> None:
            ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _trace_external_followup(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

        def _append_message(self, *args: Any, **kwargs: Any) -> None:
            pass

    provider = FakeProvider()
    dummy = DummyViewModel()
    with patch('iabv_v15.infra.ui.build_ui_screenshot_provider', return_value=provider):
        entry = ControlCenterViewModel._capture_visual_evidence_snapshot(  # type: ignore[arg-type]
            dummy,
            assistant_kind='chatgpt',
            reason='test',
            announce=False,
        )

    assert provider.regions == ['screen']
    assert entry['permission_granted'] is True
    assert entry['target_window_found'] is False
    assert entry['capture_scope'] == 'screen_fallback_no_target'
    assert 'UNRESOLVED:external_window_content_permission_missing' not in entry['unresolved_fields']
    assert 'UNRESOLVED:external_target_window_not_found' in entry['unresolved_fields']
    assert 'UNRESOLVED:ocr_not_enabled_on_ui_path' in entry['unresolved_fields']
    assert entry['semantic_summary']['state_hypothesis'] == 'external_target_window_not_found'
    assert entry['semantic_summary']['confidence'] > 0.0
    assert Path(entry['semantic_path']).exists()
    assert Path(entry['path']).exists()
    assert dummy._external_evidence_panel['visual_evidence'][0]['region'] == 'screen'
    assert any(item['action'] == 'open_external_assistant_chatgpt' for item in dummy._external_evidence_panel['actions'])
    assert dummy.traces[-1]['region'] == 'screen'
    assert dummy.traces[-1]['target_window_found'] is False


def test_visual_evidence_capture_with_permission_uses_target_window(tmp_path: Path) -> None:
    """When WorldModel has a target hwnd, capture that window instead of IABV/screen fallback."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def emit(self) -> None:
            pass

    class FakeProvider:
        def __init__(self) -> None:
            self.regions: list[str] = []

        def capture(self, region: str) -> bytes:
            self.regions.append(region)
            return _valid_png_bytes()

    class FakeWorldModel:
        def permission_snapshot(self) -> list[dict[str, Any]]:
            return [{'scope': 'observe_window_content:chatgpt', 'granted': True}]

        def current_model(self) -> Any:
            return SimpleNamespace(
                active_windows=[
                    SimpleNamespace(
                        title='ChatGPT - Google Chrome',
                        app_name='Google Chrome',
                        assistant_kind='chatgpt',
                        tool_id='chatgpt_web_assisted',
                        pid=123,
                        focused=False,
                        visible=True,
                        metadata={'hwnd': 4321, 'rect': [10, 20, 900, 700]},
                    )
                ]
            )

    class DummyViewModel:
        def __init__(self) -> None:
            self.config = SimpleNamespace(workspace_root=str(tmp_path))
            self.adaptive_orchestrator = SimpleNamespace(
                context_assembler=SimpleNamespace(world_model_service=FakeWorldModel())
            )
            self._external_evidence_panel = {'assistant': 'ChatGPT web asistido', 'metadata': [], 'actions': []}
            self._last_adaptive_payload = {}
            self._active_interaction_id = 'chat-visual'
            self.chatChanged = Emitter()
            self.dataChanged = Emitter()
            self.traces: list[dict[str, Any]] = []

        def _pending_observation_permission_assistant(self) -> str:
            return ''

        def _observation_permission_granted(self, assistant_kind: str) -> bool:
            return ControlCenterViewModel._observation_permission_granted(self, assistant_kind)  # type: ignore[arg-type]

        def _visual_evidence_semantic_summary(self, entry: dict[str, Any]) -> dict[str, Any]:
            return ControlCenterViewModel._visual_evidence_semantic_summary(self, entry)  # type: ignore[arg-type]

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'IABV')

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _set_external_evidence_panel(self, **kwargs: Any) -> None:
            ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _trace_external_followup(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

        def _append_message(self, *args: Any, **kwargs: Any) -> None:
            pass

    provider = FakeProvider()
    dummy = DummyViewModel()
    with patch('iabv_v15.infra.ui.build_ui_screenshot_provider', return_value=provider):
        entry = ControlCenterViewModel._capture_visual_evidence_snapshot(  # type: ignore[arg-type]
            dummy,
            assistant_kind='chatgpt',
            reason='test',
            announce=False,
        )

    assert provider.regions == ['hwnd:4321']
    assert entry['permission_granted'] is True
    assert entry['target_window_found'] is True
    assert entry['capture_scope'] == 'external_target_window'
    assert entry['target_window_title'] == 'ChatGPT - Google Chrome'
    assert 'UNRESOLVED:external_target_window_not_found' not in entry['unresolved_fields']
    assert dummy._external_evidence_panel['visual_evidence'][0]['region'] == 'hwnd:4321'
    assert dummy.traces[-1]['target_window_found'] is True
    assert dummy.traces[-1]['target_window_title'] == 'ChatGPT - Google Chrome'


def test_universal_perception_builds_light_semantic_signal_for_visual_evidence(tmp_path: Path) -> None:
    from iabv_v15.services.capture.universal_perception_service import UniversalPerceptionService

    image_path = tmp_path / 'visual.png'
    image_path.write_bytes(_valid_png_bytes())

    signal = UniversalPerceptionService().analyze_visual_evidence(
        image_path=str(image_path),
        assistant_kind='chatgpt',
        permission_granted=True,
        metadata={'target_window_found': True, 'capture_scope': 'external_target_window'},
    )
    payload = signal.model_dump(mode='json')

    assert payload['capture_available'] is True
    assert payload['source'] == 'external_evidence_panel'
    assert payload['visual_evidence_refs'] == [str(image_path)]
    assert payload['visual_snapshot']['image_width'] == 32
    assert payload['visual_snapshot']['image_height'] == 24
    assert payload['visual_snapshot']['state_hypothesis'] in {'screen_visible_without_ocr', 'screen_visible_with_text'}
    assert 'screenshot_available' in payload['visual_snapshot']['semantic_labels']
    assert 'external_target_window_found' in payload['visual_snapshot']['semantic_labels']
    assert 'UNRESOLVED:ocr_not_enabled_on_ui_path' in payload['unresolved_fields']
    assert payload['confidence'] > 0.0


def test_control_center_qml_starts_with_live_dock_compacted() -> None:
    """Control Center must not hydrate heavy autonomy models on first paint."""
    qml = Path('src/iabv_v15/ui/qml/pages/ControlCenterPage.qml').read_text(encoding='utf-8')

    assert 'property bool liveDockExpanded: false' in qml
    assert 'property bool liveDockHydrated: liveDockExpanded' in qml
    assert 'liveDockHydrated && controlCenterViewModel ? controlCenterViewModel.liveProcessSummary' in qml
    assert 'liveDockExpanded && controlCenterViewModel ? controlCenterViewModel.liveWorkItems' in qml
    assert 'liveDockExpanded && Boolean(controlCenterViewModel)' in qml


def test_control_center_qml_lazy_loads_advanced_panel() -> None:
    """visible:false must not instantiate the full advanced panel."""
    qml = Path('src/iabv_v15/ui/qml/pages/ControlCenterPage.qml').read_text(encoding='utf-8')

    assert 'sourceComponent: advancedPanelComponent' in qml
    assert 'id: advancedPanelComponent' in qml
    assert 'advancedVisible && controlCenterViewModel ? controlCenterViewModel.providerCards' in qml
    assert 'advancedVisible && controlCenterViewModel ? controlCenterViewModel.developmentPacket' in qml
    assert 'toolCount: providerCardsModel.length' in qml
    assert 'providers: providerCardsModel' in qml


def test_control_center_does_not_probe_provider_health_while_advanced_hidden() -> None:
    """Provider scans are an advanced concern and must not run on first chat paint."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._advanced_visible = False
            self._provider_refreshing = False

    dummy = DummyViewModel()

    ControlCenterViewModel._refresh_provider_health(  # type: ignore[arg-type]
        dummy,
        announce=False,
    )

    assert dummy._provider_refreshing is False


def test_control_center_deferred_provider_probe_is_guarded_by_advanced_panel() -> None:
    """The 900ms route-entry probe must not start provider scans when collapsed."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._advanced_visible = False
            self.calls = 0

        def _refresh_provider_health(self, *, announce: bool) -> None:
            self.calls += 1

    dummy = DummyViewModel()

    ControlCenterViewModel._deferred_provider_health_probe(dummy)  # type: ignore[arg-type]

    assert dummy.calls == 0


def test_control_center_chat_history_uses_virtualized_listview() -> None:
    """Chat history must not instantiate every heavy message delegate at once."""
    qml = Path('src/iabv_v15/ui/qml/pages/ControlCenterPage.qml').read_text(encoding='utf-8')

    assert 'id: chatListView' in qml
    assert 'model: chatMessagesModel' in qml
    assert 'reuseItems: true' in qml
    assert 'cacheBuffer: 480' in qml
    assert 'width: chatListView.width' in qml
    assert 'Repeater {\n                                model: chatMessagesModel' not in qml


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


def test_timer_autonomy_dock_budget_observes_active_route_stability() -> None:
    """Control dock timers must inherit the bootstrap route-stability window."""
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
            self._bootstrap_ref = SimpleNamespace(
                _active_ui_route='control',
                _last_ui_route_change_at=time.monotonic() - 25.0,
            )

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

    assert reason == 'ui_route_stabilizing:control'
    assert rss_mb == 210.0
    evidence = dummy._autonomy_dock_last_budget_decision['evidence']
    assert evidence['active_route'] == 'control'
    assert 20.0 <= evidence['ui_route_stability_age_s'] <= 30.0


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


def test_post_task_autonomy_dock_refresh_requires_deep_rest_window() -> None:
    """A completed external consultation must not immediately fan out into dock work."""
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
            self._autonomy_dock_rest_window_started_at = time.monotonic() - 180.0
            self._autonomy_dock_last_budget_decision: dict[str, Any] = {}
            self._bootstrap_ref = SimpleNamespace(
                _active_ui_route='control',
                _last_ui_route_change_at=time.monotonic() - 900.0,
            )

        def _process_rss_mb(self) -> float:
            return 400.0

        def _visible_query_wait_active(self) -> bool:
            return ControlCenterViewModel._visible_query_wait_active(self)  # type: ignore[arg-type]

        def _recent_ui_stall_ms(self) -> float:
            return 0.0

        def _autonomy_dock_budget_decision(self, **kwargs: Any) -> dict[str, Any]:
            return ControlCenterViewModel._autonomy_dock_budget_decision(self, **kwargs)  # type: ignore[arg-type]

    dummy = DummyViewModel()

    reason, rss_mb = ControlCenterViewModel._autonomy_dock_defer_reason(  # type: ignore[arg-type]
        dummy,
        source='post_task:external_consultation',
        force=False,
    )

    assert reason == 'post_task_rest_window_not_reached'
    assert rss_mb == 400.0
    assert dummy._autonomy_dock_last_budget_decision['allowed'] is False
    assert dummy._autonomy_dock_last_budget_decision['recommended_mode'] == 'wait_for_deep_idle'


def test_chat_display_text_truncates_large_auto_analysis_for_ui() -> None:
    """Large self-analysis reports stay persisted but are compact in QML."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    raw = 'x' * (ControlCenterViewModel._CHAT_INLINE_TEXT_LIMIT + 500)
    display = ControlCenterViewModel._chat_display_text(raw)

    assert len(display) < len(raw)
    assert 'historial local' in display
    assert 'mantener la UI fluida' in display


def test_chat_messages_property_returns_small_preview_without_losing_memory() -> None:
    """QML gets a bounded view while Python keeps the full in-memory history."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    long_text = 'x' * (ControlCenterViewModel._CHAT_PREVIEW_TEXT_LIMIT + 200)
    dummy = SimpleNamespace(
        _ui_state_lock=threading.RLock(),
        _chat_messages=[
            {'role': 'assistant', 'speaker': 'IABV', 'text': f'msg-{idx}-{long_text}'}
            for idx in range(20)
        ],
    )

    preview = ControlCenterViewModel.get_chat_messages_preview(dummy)  # type: ignore[arg-type]
    full = ControlCenterViewModel.get_chat_messages(dummy)  # type: ignore[arg-type]

    assert len(full) == 20
    assert len(preview) == ControlCenterViewModel._CHAT_PREVIEW_MESSAGE_LIMIT
    assert preview[0]['text'].startswith('msg-12-')
    assert preview[-1]['text'].startswith('msg-19-')
    assert all(len(item['text']) < len(long_text) + 20 for item in preview)
    assert all(item.get('textTruncated') is True for item in preview)


def test_control_center_qml_uses_preview_chat_property_name() -> None:
    """The QML chat model must bind to the bounded Property, not call methods."""
    qml = Path('src/iabv_v15/ui/qml/pages/ControlCenterPage.qml').read_text(encoding='utf-8')

    assert 'property var chatMessagesModel: controlCenterViewModel ? controlCenterViewModel.chatMessages : []' in qml
    assert 'controlCenterViewModel.get_chat_messages' not in qml


def test_release_visible_query_wait_clears_watchdog_query_pending() -> None:
    """Background follow-up must not leave the visible query flag stuck."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyWatchdog:
        def __init__(self) -> None:
            self.query_values: list[bool] = []
            self.active_values: list[str | None] = []

        def set_query_pending(self, value: bool) -> None:
            self.query_values.append(value)

        def set_active_interaction(self, value: str | None) -> None:
            self.active_values.append(value)

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
    assert dummy._ui_heartbeat_watchdog.active_values == [None]
    assert dummy._live_status == 'idle'


def test_non_final_external_outcome_releases_visible_wait_and_arms_timeout() -> None:
    """Prepared/reused external outcomes stay durable but must not keep Consultando."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._active_interaction_id = 'chat-reused'
            self.resolved: list[tuple[str, str]] = []
            self.released: list[str] = []
            self.scheduled: list[tuple[str, str, str]] = []

        def _resolve_active_interaction(self, *, outcome: str = 'resolved', provider: str = '') -> None:
            self.resolved.append((outcome, provider))

        def _release_visible_query_wait(self, *, reason: str) -> None:
            self.released.append(reason)

        def _schedule_external_followup_timeout(
            self,
            *,
            interaction_id: str,
            outcome: str,
            provider: str,
        ) -> None:
            self.scheduled.append((interaction_id, outcome, provider))

    dummy = DummyViewModel()

    ControlCenterViewModel._record_non_final_external_outcome(  # type: ignore[arg-type]
        dummy,
        outcome='reused_context',
        provider='ChatGPT web asistido',
    )

    assert dummy._interaction_has_pending_followup is True
    assert dummy._interaction_pending_followup_outcome == 'reused_context'
    assert dummy._interaction_pending_followup_provider == 'ChatGPT web asistido'
    assert dummy.resolved == [('reused_context', 'ChatGPT web asistido')]
    assert dummy.released == ['external_consultation_non_final:reused_context']
    assert dummy.scheduled == [('chat-reused', 'reused_context', 'ChatGPT web asistido')]


def test_external_followup_timeout_closes_stale_current_interaction() -> None:
    """A non-final external episode cannot remain open forever."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Emitter:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class DummyLifecycle:
        def __init__(self) -> None:
            self.resolved: list[tuple[str, str, str]] = []

        def interaction_info(self, interaction_id: str) -> dict[str, str]:
            return {'interaction_id': interaction_id, 'outcome': 'reused_context'}

        def resolve_interaction(self, interaction_id: str, *, outcome: str = 'resolved', provider: str = '') -> None:
            self.resolved.append((interaction_id, outcome, provider))

    class DummyViewModel:
        _FINAL_INTERACTION_OUTCOMES = ControlCenterViewModel._FINAL_INTERACTION_OUTCOMES

        def __init__(self) -> None:
            self._external_followup_timeout_generation = 3
            self._active_interaction_id = 'chat-reused'
            self._chat_interaction_lifecycle = DummyLifecycle()
            self._interaction_has_pending_followup = True
            self._interaction_pending_followup_outcome = 'reused_context'
            self._interaction_pending_followup_provider = 'ChatGPT web asistido'
            self._ui_heartbeat_watchdog = None
            self._live_status = 'processing'
            self.released: list[str] = []
            self.messages: list[tuple[str, str, str, str]] = []
            self.traces: list[tuple[str, dict[str, object]]] = []
            self.refresh_calls = 0
            self.chatChanged = Emitter()

        def _trace_external_followup(self, kind: str, **data: object) -> None:
            self.traces.append((kind, data))

        def _release_visible_query_wait(self, *, reason: str) -> None:
            self.released.append(reason)
            self._live_status = 'idle'

        def _append_message(self, role: str, speaker: str, text: str, meta: str, **_: object) -> None:
            self.messages.append((role, speaker, text, meta))

        def _set_live_status(self, status: str) -> None:
            self._live_status = status

        def _promote_metacognition_after_resolution(self) -> None:
            pass

        def _resolve_interaction_by_id(self, interaction_id: str, *, outcome: str = 'resolved', provider: str = '') -> None:
            ControlCenterViewModel._resolve_interaction_by_id(  # type: ignore[arg-type]
                self,
                interaction_id,
                outcome=outcome,
                provider=provider,
            )

        def _refresh_autonomy_dock_async(self) -> None:
            self.refresh_calls += 1

    dummy = DummyViewModel()

    ControlCenterViewModel._expire_external_followup_if_stale(  # type: ignore[arg-type]
        dummy,
        interaction_id='chat-reused',
        generation=3,
        outcome='reused_context',
        provider='ChatGPT web asistido',
        timeout_ms=120_000,
    )

    assert dummy.released == ['external_followup_timeout:reused_context']
    assert dummy._chat_interaction_lifecycle.resolved == [
        ('chat-reused', 'blocked', 'ChatGPT web asistido')
    ]
    assert dummy._active_interaction_id is None
    assert dummy._interaction_pending_followup_outcome == ''
    assert dummy.messages
    assert 'no recib' in dummy.messages[0][2].lower()
    assert dummy.chatChanged.count == 1
    assert dummy.refresh_calls == 1


def test_external_consultation_reuse_short_circuit_blocks_when_unverified() -> None:
    """Reuse guard without verified response must not pretend ChatGPT answered."""
    from types import SimpleNamespace

    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class FakeToolTeach:
        def __init__(self) -> None:
            self.preview_contexts: list[str] = []
            self.execute_calls = 0

        def preview_external_consultation(self, **kwargs):
            self.preview_contexts.append(str(kwargs.get('context_pack') or ''))
            return {
                'available': True,
                'tool_card': {'tool_id': 'chatgpt_web_assisted', 'title': 'ChatGPT web asistido'},
                'tool_task': {
                    'tool_id': 'chatgpt_web_assisted',
                    'metadata': {'reuse_guard_active': True},
                },
                'mode_selection': {'equivalent_pattern_exists': True},
            }

        def execute_external_consultation(self, **kwargs):
            self.execute_calls += 1
            raise AssertionError('reuse guard must return before executing')

    class FakeOrchestrator:
        def preflight_external_assistant(self, **kwargs):
            return {
                'blocked': False,
                'reason': '',
                'governance': {'approval_required': False, 'block_risky_action': False},
                'approval_checkpoints': [],
                'world_model': {},
                'world_model_summary': {},
            }

    class DummyViewModel:
        def __init__(self) -> None:
            self.tool_teach_service = FakeToolTeach()
            self.adaptive_orchestrator = FakeOrchestrator()
            self.config = SimpleNamespace(workspace_root='C:/Python/IABV_v1.5')
            self._last_user_goal = 'has una consulta a chatgpt'
            self._last_adaptive_payload = {'evidence_refs': ['x' * 500000]}
            self._latest_response_text = ''
            self._latest_response_meta = ''
            self._active_interaction_id = 'chat-reuse'
            self.updated_payload: dict[str, Any] = {}

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'asistente')

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _update_adaptive_state(self, payload: dict[str, Any]) -> None:
            self.updated_payload = dict(payload)

        def _guidance_for_unverified_external_reuse(self, **kwargs):
            return ControlCenterViewModel._guidance_for_unverified_external_reuse(self, **kwargs)  # type: ignore[arg-type]

        def _unverified_reuse_guard_external_result(self, **kwargs):
            return ControlCenterViewModel._unverified_reuse_guard_external_result(self, **kwargs)  # type: ignore[arg-type]

        def _set_external_evidence_panel(self, **kwargs):
            return ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _assistant_kind_from_tool_id(self, tool_id: str) -> str:
            return 'chatgpt' if str(tool_id).startswith('chatgpt') else ''

        def _clear_observation_permission_artifacts(self) -> None:
            pass

        def _current_site_id(self) -> str:
            return ''

        def _current_diagnostic_category(self) -> str:
            return ''

        def _current_incident_kind(self) -> str:
            return ''

        def _trace_external_consultation_phase(self, phase: str, **payload) -> None:
            pass

        def _observation_permission_granted(self, assistant_kind: str) -> bool:
            return False

        def _preview_external_consultation_light(self, **kwargs):
            return ControlCenterViewModel._preview_external_consultation_light(  # type: ignore[arg-type]
                self,
                **kwargs,
            )

        def _build_external_context_pack(self, assistant_kind: str) -> str:
            raise AssertionError('heavy context pack must not be built when reuse_guard_active is known')

        def _copy_text(self, text: str, notice: str = '') -> None:
            raise AssertionError('clipboard copy must not run for reuse short-circuit')

    dummy = DummyViewModel()

    payload = ControlCenterViewModel._execute_external_consultation_sync(  # type: ignore[arg-type]
        dummy,
        'chatgpt',
    )

    assert payload['success'] is False
    assert payload['meta'] == 'Respuesta externa no verificada: ChatGPT web asistido.'
    assert 'no tengo evidencia' in payload['message'].lower()
    assert payload['payload']['assistant_guidance']['mode'] == 'need_approval'
    assert payload['payload']['metadata']['external_consultation']['status'] == 'blocked_external'
    assert payload['payload']['metadata']['external_consultation']['reuse_guard_active'] is True
    panel = dummy._external_evidence_panel
    assert panel['visible'] is True
    assert panel['status'] == 'blocked'
    assert panel['assistant'] == 'ChatGPT web asistido'
    assert any(item['label'] == 'reuse_guard_short_circuit' for item in panel['phases'])
    assert any(item['key'] == 'response_verified' and item['value'] == 'False' for item in panel['metadata'])
    assert dummy.tool_teach_service.execute_calls == 0
    assert len(dummy.tool_teach_service.preview_contexts) == 1
    assert len(dummy.tool_teach_service.preview_contexts[0]) < 200


def test_external_consultation_reuse_guard_continues_after_observation_permission() -> None:
    """Once the user grants observation, reuse guard must not loop on the same block."""
    from types import SimpleNamespace

    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class FakeToolTeach:
        def __init__(self) -> None:
            self.preview_contexts: list[str] = []
            self.execute_calls = 0

        def preview_external_consultation(self, **kwargs):
            self.preview_contexts.append(str(kwargs.get('context_pack') or ''))
            return {
                'available': True,
                'tool_card': {
                    'tool_id': 'chatgpt_web_assisted',
                    'title': 'ChatGPT web asistido',
                    'metadata': {'response_capture_mode': 'manual_pasteback'},
                },
                'tool_task': {
                    'tool_id': 'chatgpt_web_assisted',
                    'metadata': {'reuse_guard_active': True},
                },
                'mode_selection': {'equivalent_pattern_exists': True},
                'summary': 'reuse guard present but observation permission is granted',
            }

        def execute_external_consultation(self, **kwargs):
            self.execute_calls += 1
            task = ToolTask(
                tool_id='chatgpt_web_assisted',
                title='ChatGPT',
                objective='consultar',
                requested_by_role=TaskRole.TOOL_USE,
                approval_decision=ApprovalDecision.APPROVED,
                metadata={'response_capture_mode': 'manual_pasteback'},
            )
            result = ToolResult(
                task_id=task.task_id,
                tool_id=task.tool_id,
                tool_type=ToolType.BROWSER,
                success=True,
                validation_status=ToolValidationStatus.APPROVED,
                execution_state=ExecutionState(
                    state='prepared',
                    detail='consulta preparada',
                    sandboxed=False,
                    validated=True,
                    metadata={
                        'actual_assistant_kind': 'chatgpt',
                        'response_capture_mode': 'manual_pasteback',
                        'manual_pasteback_required': True,
                    },
                ),
                output_text='Consulta externa preparada.',
            )
            return task, result, None

    class FakeOrchestrator:
        def preflight_external_assistant(self, **kwargs):
            return {
                'blocked': False,
                'reason': '',
                'governance': {'approval_required': False, 'block_risky_action': False},
                'approval_checkpoints': [],
                'world_model': {},
                'world_model_summary': {},
            }

    class DummyViewModel:
        def __init__(self) -> None:
            self.tool_teach_service = FakeToolTeach()
            self.adaptive_orchestrator = FakeOrchestrator()
            self.config = SimpleNamespace(workspace_root='C:/Python/IABV_v1.5')
            self._last_user_goal = 'has una consulta a chatgpt'
            self._last_adaptive_payload = {'metadata': {}}
            self._latest_response_text = ''
            self._latest_response_meta = ''
            self._active_interaction_id = 'chat-reuse'
            self.updated_payload: dict[str, Any] = {}
            self.copied: list[str] = []
            self.phases: list[str] = []
            self.context_built = False

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'asistente')

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _update_adaptive_state(self, payload: dict[str, Any]) -> None:
            self.updated_payload = dict(payload)

        def _guidance_for_pending_external_response(self, assistant_title: str):
            return ControlCenterViewModel._guidance_for_pending_external_response(self, assistant_title)  # type: ignore[arg-type]

        def _assistant_kind_from_tool_id(self, tool_id: str) -> str:
            return 'chatgpt' if str(tool_id).startswith('chatgpt') else ''

        def _clear_observation_permission_artifacts(self) -> None:
            pass

        def _current_site_id(self) -> str:
            return ''

        def _current_diagnostic_category(self) -> str:
            return ''

        def _current_incident_kind(self) -> str:
            return ''

        def _trace_external_consultation_phase(self, phase: str, **payload) -> None:
            self.phases.append(phase)

        def _observation_permission_granted(self, assistant_kind: str) -> bool:
            return str(assistant_kind).strip().lower() == 'chatgpt'

        def _preview_external_consultation_light(self, **kwargs):
            return ControlCenterViewModel._preview_external_consultation_light(  # type: ignore[arg-type]
                self,
                **kwargs,
            )

        def _build_external_context_pack(self, assistant_kind: str) -> str:
            self.context_built = True
            return 'contexto vivo para ChatGPT'

        def _copy_text(self, text: str, notice: str = '') -> None:
            self.copied.append(text)

        def _external_state_flags_from_payloads(self, *payloads: Any) -> list[str]:
            return ControlCenterViewModel._external_state_flags_from_payloads(self, *payloads)  # type: ignore[arg-type]

        def _external_state_notice(self, flags: list[str] | None) -> str:
            return ControlCenterViewModel._external_state_notice(self, flags)  # type: ignore[arg-type]

    dummy = DummyViewModel()

    payload = ControlCenterViewModel._execute_external_consultation_sync(  # type: ignore[arg-type]
        dummy,
        'chatgpt',
    )

    assert payload['success'] is True
    assert dummy.context_built is True
    assert dummy.tool_teach_service.execute_calls == 1
    assert len(dummy.tool_teach_service.preview_contexts) == 2
    assert dummy.copied == ['contexto vivo para ChatGPT']
    assert 'reuse_guard_bypassed_after_observation_permission' in dummy.phases
    assert 'reuse_guard_short_circuit' not in dummy.phases
    external = dummy.updated_payload['metadata']['external_consultation']
    assert external['selected_tool_id'] == 'chatgpt_web_assisted'
    assert external['status'] == 'awaiting_response'


def test_external_context_pack_limits_large_items() -> None:
    """External context must be bounded before clipboard/QML can amplify it."""
    from types import SimpleNamespace

    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    dummy = SimpleNamespace(
        _EXTERNAL_CONTEXT_ITEM_LIMIT=80,
        _EXTERNAL_CONTEXT_PACK_LIMIT=300,
    )

    compact = ControlCenterViewModel._compact_external_context_line(  # type: ignore[arg-type]
        dummy,
        'A' * 500,
    )
    limited = ControlCenterViewModel._limit_external_context_pack(  # type: ignore[arg-type]
        dummy,
        'B' * 1000,
    )

    assert len(compact) <= 80
    assert '[truncado]' in compact
    assert len(limited) <= 300
    assert 'Contexto truncado por presupuesto operativo' in limited


def test_external_consultation_diagnosis_reads_runtime_audit_reuse_guard() -> None:
    """The chat can explain what happened with ChatGPT from live audit data."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    root = _workspace('external_diag')
    try:
        logs = root / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        audit = logs / 'runtime_audit.jsonl'
        records = [
            {'kind': 'interaction_open', 'data': {'interaction_id': 'chat-x', 'message_preview': 'has una consulta a chatgpt'}},
            {'kind': 'external_consultation_phase', 'data': {'interaction_id': 'chat-x', 'assistant_kind': 'chatgpt', 'phase': 'reuse_probe_done'}},
            {'kind': 'external_consultation_phase', 'data': {'interaction_id': 'chat-x', 'assistant_kind': 'chatgpt', 'phase': 'reuse_guard_short_circuit'}},
            {'kind': 'interaction_outcome', 'data': {'interaction_id': 'chat-x', 'message_preview': 'has una consulta a chatgpt', 'outcome': 'reused_context', 'provider': 'ChatGPT web asistido'}},
            {'kind': 'interaction_open', 'data': {'interaction_id': 'chat-diag', 'message_preview': 'pero sabes que paso con chatgpt?'}},
            {'kind': 'interaction_resolved', 'data': {'interaction_id': 'chat-diag', 'message_preview': 'pero sabes que paso con chatgpt?', 'outcome': 'resolved', 'provider': 'local'}},
        ]
        audit.write_text('\n'.join(json.dumps(item) for item in records), encoding='utf-8')
        dummy = SimpleNamespace(config=SimpleNamespace(logs_dir=str(logs)))

        summary = ControlCenterViewModel._latest_external_consultation_audit_summary(dummy)  # type: ignore[arg-type]

        assert summary['status'] == 'found'
        assert summary['interaction_id'] == 'chat-x'
        assert 'reuse_guard_short_circuit' in summary['phases']
        assert summary['outcome']['outcome'] == 'reused_context'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_external_diagnosis_question_does_not_grant_observation_permission() -> None:
    """A question about ChatGPT metadata must not be parsed as approval."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def _pending_observation_permission_assistant(self) -> str:
            return 'chatgpt'

        def _normalized_command_text(self, message: str) -> str:
            return ControlCenterViewModel._normalized_command_text(self, message)  # type: ignore[arg-type]

        def _is_external_consultation_diagnosis_question(self, message: str) -> bool:
            return ControlCenterViewModel._is_external_consultation_diagnosis_question(self, message)  # type: ignore[arg-type]

        def _grant_pending_observation_permission(self, *, announce: bool = True) -> bool:
            raise AssertionError('diagnosis question must not grant observation permission')

    dummy = DummyViewModel()

    handled = ControlCenterViewModel._try_resolve_pending_observation_permission(  # type: ignore[arg-type]
        dummy,
        'pero sabes que paso ? si estas entendiendo bien los metadatos que ves de chatgpt?',
    )

    assert handled is False


def test_grant_observation_permission_captures_visual_evidence_before_retry() -> None:
    """The permission button must act: grant, capture what IABV sees, then retry."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Signal:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class FakeWorldModelService:
        def __init__(self) -> None:
            self.grants: list[dict[str, str]] = []

        def grant_observation_permission(self, **kwargs) -> None:
            self.grants.append(dict(kwargs))

    class DummyViewModel:
        def __init__(self) -> None:
            self.world_model = FakeWorldModelService()
            self.adaptive_orchestrator = SimpleNamespace(
                context_assembler=SimpleNamespace(world_model_service=self.world_model)
            )
            self.dataChanged = Signal()
            self.messages: list[tuple[str, str, str, str]] = []
            self.captures: list[dict[str, object]] = []
            self.retries: list[tuple[str, bool]] = []
            self._busy_label = ''
            self._approval_dialog_visible = True
            self._approval_dialog_title = ''
            self._approval_dialog_text = ''

        def _pending_observation_permission_assistant(self) -> str:
            return 'chatgpt'

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind)

        def _clear_observation_permission_artifacts(self) -> None:
            pass

        def _capture_visual_evidence_snapshot(self, **kwargs) -> dict[str, object]:
            self.captures.append(dict(kwargs))
            return {
                'path': 'C:/Python/IABV_v1.5/data/evolution/visual_evidence/visual_test_chatgpt.png',
                'semantic_summary': {'state_hypothesis': 'screen_visible_without_ocr'},
            }

        def _append_message(self, role: str, speaker: str, text: str, meta: str, **_: object) -> None:
            self.messages.append((role, speaker, text, meta))

        def _run_external_consultation(self, assistant_kind: str, *, announce: bool = True) -> bool:
            self.retries.append((assistant_kind, announce))
            return True

    dummy = DummyViewModel()

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as tracer:
        result = ControlCenterViewModel._grant_pending_observation_permission(  # type: ignore[arg-type]
            dummy,
            announce=True,
        )

    assert result is True
    assert dummy.world_model.grants[0]['scope'] == 'observe_window_content:chatgpt'
    assert dummy.captures == [
        {
            'assistant_kind': 'chatgpt',
            'reason': 'observation_permission_granted',
            'announce': False,
        }
    ]
    assert dummy.retries == [('chatgpt', False)]
    assert 'capture evidencia visual' in dummy.messages[0][2].lower()
    assert 'no repetir el bloqueo anterior' in dummy.messages[0][2].lower()
    assert dummy._approval_dialog_visible is False
    assert 'evidencia visual' in dummy._approval_dialog_text.lower()
    assert dummy.dataChanged.count == 1
    tracer.return_value.trace_permission.assert_called_once()


def test_external_context_question_about_browser_stays_on_audit_path() -> None:
    """Follow-up UX questions must not fall through to generic local chat."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._last_adaptive_payload = {
                'metadata': {
                    'external_consultation': {
                        'status': 'blocked_external',
                        'assistant_kind': 'chatgpt',
                    }
                }
            }
            self._external_evidence_panel = {'visible': True}

        def _normalized_command_text(self, message: str) -> str:
            return ControlCenterViewModel._normalized_command_text(self, message)  # type: ignore[arg-type]

    dummy = DummyViewModel()

    assert ControlCenterViewModel._is_external_consultation_diagnosis_question(  # type: ignore[arg-type]
        dummy,
        'pero en que navegador estas consultando?',
    ) is True
    assert ControlCenterViewModel._is_external_consultation_diagnosis_question(  # type: ignore[arg-type]
        dummy,
        'si me has entendido lo que te he dicho en el ultimo mensaje?',
    ) is True


def test_blocked_external_preflight_sets_visible_evidence_panel() -> None:
    """A preflight block must explain that no browser/window was opened."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._last_adaptive_payload: dict[str, Any] = {}
            self.updated_payload: dict[str, Any] = {}
            self._active_interaction_id = 'chat-preflight'

        def _update_adaptive_state(self, payload: dict[str, Any]) -> None:
            self.updated_payload = dict(payload)

        def _guidance_for_external_preflight_block(self, **kwargs):
            return {'mode': 'need_approval', 'actions': []}

        def _set_external_evidence_panel(self, **kwargs):
            return ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

    dummy = DummyViewModel()

    payload = ControlCenterViewModel._blocked_external_consultation_result(  # type: ignore[arg-type]
        dummy,
        assistant_kind='chatgpt',
        assistant_title='ChatGPT',
        preflight={
            'reason': 'resource pressure',
            'governance': {
                'approval_required': False,
                'block_risky_action': True,
                'external_state_flags': ['resource_pressure'],
            },
            'approval_checkpoints': [],
            'world_model_summary': {'focused_app': 'IABV'},
        },
    )

    assert payload['success'] is False
    assert dummy.updated_payload['metadata']['external_consultation_preflight']['blocked'] is True
    panel = dummy._external_evidence_panel
    assert panel['visible'] is True
    assert panel['title'] == 'Ruta externa bloqueada antes de abrir ventana'
    assert panel['interaction_id'] == 'chat-preflight'
    assert any(item['label'] == 'external_preflight_blocked' for item in panel['phases'])
    assert 'No hay navegador confirmado' in panel['user_help']


def test_security_preflight_block_opens_visible_verification_action() -> None:
    """Security verification must become a visible user-resolvable step."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._last_adaptive_payload: dict[str, Any] = {}
            self.updated_payload: dict[str, Any] = {}
            self._active_interaction_id = 'chat-security'
            self.opened: list[tuple[str, str, bool]] = []

        def _update_adaptive_state(self, payload: dict[str, Any]) -> None:
            self.updated_payload = dict(payload)

        def _guidance_for_external_preflight_block(self, **kwargs):
            return {'mode': 'need_human_verification', 'actions': []}

        def _set_external_evidence_panel(self, **kwargs):
            return ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _open_external_assistant_for_human_verification(self, assistant_kind: str, *, reason: str = 'user_action', announce: bool = True) -> bool:
            self.opened.append((assistant_kind, reason, announce))
            return True

    dummy = DummyViewModel()

    payload = ControlCenterViewModel._blocked_external_consultation_result(  # type: ignore[arg-type]
        dummy,
        assistant_kind='chatgpt',
        assistant_title='ChatGPT',
        preflight={
            'reason': 'ChatGPT web asistido quedo bloqueado por una verificacion de seguridad del sitio.',
            'governance': {
                'approval_required': False,
                'block_risky_action': True,
                'external_state_flags': ['browser_security_verification'],
            },
            'approval_checkpoints': [],
            'world_model_summary': {'focused_app': 'IABV'},
        },
    )

    assert payload['success'] is False
    assert dummy.opened == [('chatgpt', 'security_preflight_block', False)]
    panel = dummy._external_evidence_panel
    assert panel['title'] == 'Verificacion de seguridad pendiente'
    assert any(item['action'] == 'open_external_assistant_chatgpt' for item in panel['actions'])
    assert 'abrir una ventana visible' in panel['user_help'].lower()
    assert 'abriendo una ventana visible' in payload['message'].lower()


def test_security_preflight_retests_after_visible_verification() -> None:
    """After user-visible verification, stale security preflight must not trap retries forever."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class FakeController:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeToolTeach:
        def __init__(self) -> None:
            self.preview_calls = 0

        def preview_external_consultation(self, **kwargs):
            self.preview_calls += 1
            return {
                'available': False,
                'tool_card': {'tool_id': 'chatgpt_web_assisted', 'title': 'ChatGPT web asistido'},
                'tool_task': {},
            }

    class FakeOrchestrator:
        def preflight_external_assistant(self, **kwargs):
            return {
                'blocked': True,
                'reason': 'ChatGPT web asistido quedo bloqueado por una verificacion de seguridad del sitio.',
                'governance': {'external_state_flags': ['browser_security_verification']},
                'approval_checkpoints': [],
                'world_model_summary': {},
            }

    class DummyViewModel:
        def __init__(self) -> None:
            self.tool_teach_service = FakeToolTeach()
            self.adaptive_orchestrator = FakeOrchestrator()
            self.config = SimpleNamespace(workspace_root='C:/Python/IABV_v1.5')
            self._last_user_goal = 'has una consulta a chatgpt'
            self._last_adaptive_payload: dict[str, Any] = {}
            self._latest_response_text = ''
            self._latest_response_meta = ''
            self._active_interaction_id = 'chat-security'
            self._visible_external_sessions = {'chatgpt': FakeController()}
            self._external_visible_verification_opened_at = {'chatgpt': time.monotonic()}
            self.phases: list[str] = []
            self.followups: list[str] = []
            self.clear_calls = 0

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'asistente')

        def _observation_permission_granted(self, assistant_kind: str) -> bool:
            return str(assistant_kind).strip().lower() == 'chatgpt'

        def _should_retest_security_preflight_after_visible_verification(self, assistant_kind: str, preflight: dict[str, Any]) -> bool:
            return ControlCenterViewModel._should_retest_security_preflight_after_visible_verification(  # type: ignore[arg-type]
                self,
                assistant_kind,
                preflight,
            )

        def _release_visible_external_session(self, assistant_kind: str, *, reason: str = 'retry') -> None:
            return ControlCenterViewModel._release_visible_external_session(  # type: ignore[arg-type]
                self,
                assistant_kind,
                reason=reason,
            )

        def _trace_external_followup(self, kind: str, **data: Any) -> None:
            self.followups.append(kind)

        def _trace_external_consultation_phase(self, phase: str, **payload: Any) -> None:
            self.phases.append(phase)

        def _clear_observation_permission_artifacts(self) -> None:
            self.clear_calls += 1

        def _current_site_id(self) -> str:
            return ''

        def _current_diagnostic_category(self) -> str:
            return ''

        def _current_incident_kind(self) -> str:
            return ''

        def _preview_external_consultation_light(self, **kwargs):
            return ControlCenterViewModel._preview_external_consultation_light(self, **kwargs)  # type: ignore[arg-type]

    dummy = DummyViewModel()
    controller = dummy._visible_external_sessions['chatgpt']

    payload = ControlCenterViewModel._execute_external_consultation_sync(  # type: ignore[arg-type]
        dummy,
        'chatgpt',
    )

    assert payload['success'] is False
    assert dummy.tool_teach_service.preview_calls == 1
    assert dummy.clear_calls == 1
    assert controller.closed is True
    assert dummy._visible_external_sessions == {}
    assert 'external_assistant_verification_window_released' in dummy.followups
    assert 'security_preflight_retest_after_visible_verification' in dummy.phases
    assert payload['meta'] == 'Consulta externa no disponible.'


def test_open_external_assistant_for_human_verification_uses_program_profile(tmp_path: Path) -> None:
    """The visible verification button must open the program profile, not only describe it."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class Signal:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class ImmediateThread:
        def __init__(self, target, **kwargs) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    class FakePage:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def goto(self, url: str, wait_until: str = '') -> None:
            self.urls.append(url)

    class FakeController:
        instances: list['FakeController'] = []

        def __init__(self, user_data_dir: str, headless: bool) -> None:
            self.user_data_dir = user_data_dir
            self.headless = headless
            self._page = FakePage()
            FakeController.instances.append(self)

        def start(self) -> None:
            pass

        @property
        def page(self) -> FakePage:
            return self._page

        def new_page(self) -> FakePage:
            self._page = FakePage()
            return self._page

    class DummyViewModel:
        def __init__(self) -> None:
            self.config = SimpleNamespace(workspace_root=str(tmp_path))
            self._external_evidence_panel: dict[str, Any] = {}
            self._visible_external_sessions: dict[str, Any] = {}
            self._external_visible_verification_opened_at: dict[str, float] = {}
            self._active_interaction_id = 'chat-open'
            self.chatChanged = Signal()
            self.dataChanged = Signal()
            self.messages: list[str] = []
            self.traces: list[dict[str, Any]] = []

        def _external_evidence_assistant_kind(self) -> str:
            return ''

        def _assistant_display_name(self, kind: str) -> str:
            return {'chatgpt': 'ChatGPT'}.get(kind, kind or 'asistente')

        def _assistant_program_browser_profile_dir(self, assistant_kind: str) -> Path:
            return ControlCenterViewModel._assistant_program_browser_profile_dir(self, assistant_kind)  # type: ignore[arg-type]

        def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
            return {'action': action, 'label': label, 'detail': detail}

        def _set_external_evidence_panel(self, **kwargs: Any) -> None:
            return ControlCenterViewModel._set_external_evidence_panel(self, **kwargs)  # type: ignore[arg-type]

        def _append_message(self, role: str, speaker: str, text: str, meta: str = '', **kwargs: Any) -> None:
            self.messages.append(text)

        def _trace_external_followup(self, kind: str, **data: Any) -> None:
            self.traces.append({'kind': kind, **data})

    dummy = DummyViewModel()

    with patch('iabv_v15.ui.viewmodels.control_center_viewmodel.threading.Thread', ImmediateThread), \
        patch('iabv_v15.services.capture.browser_session_controller.BrowserSessionController', FakeController):
        opened = ControlCenterViewModel._open_external_assistant_for_human_verification(  # type: ignore[arg-type]
            dummy,
            'chatgpt',
            reason='test',
            announce=True,
        )

    assert opened is True
    assert 'chatgpt' in dummy._visible_external_sessions
    assert dummy._external_visible_verification_opened_at['chatgpt'] > 0
    assert FakeController.instances[0].headless is False
    assert 'chatgpt_program_session' in FakeController.instances[0].user_data_dir
    assert FakeController.instances[0].page.urls == ['https://chatgpt.com/']
    assert dummy._external_evidence_panel['status'] == 'needs_human_verification'
    assert any(item['action'] == 'consult_chatgpt' for item in dummy._external_evidence_panel['actions'])
    assert dummy.traces[-1]['mode'] == 'program_profile_visible'


def test_attachment_context_pack_reads_bounded_text_file(tmp_path: Path) -> None:
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    doc = tmp_path / 'nota.md'
    doc.write_text('linea importante\n' * 10, encoding='utf-8')

    message = ControlCenterViewModel._message_with_attachment_context(
        'analiza este documento',
        [{'name': 'nota.md', 'path': str(doc), 'size': doc.stat().st_size, 'type': 'text/markdown'}],
    )

    assert 'analiza este documento' in message
    assert '[Contexto de archivos adjuntos verificado por IABV]' in message
    assert '### nota.md (.md' in message
    assert 'linea importante' in message


def test_attachment_context_pack_marks_rich_documents_unresolved(tmp_path: Path) -> None:
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    doc = tmp_path / 'documento.pdf'
    doc.write_bytes(b'%PDF-1.4 fake')

    message = ControlCenterViewModel._message_with_attachment_context(
        'lee este pdf',
        [{'name': 'documento.pdf', 'path': str(doc), 'size': doc.stat().st_size, 'type': 'application/pdf'}],
    )

    assert 'metadata_only suffix=.pdf' in message
    assert 'UNRESOLVED:binary_or_rich_document_extraction_not_enabled' in message


def test_pending_observation_permission_keeps_episode_for_external_result() -> None:
    """Approving observation starts the external retry; sendChat must not close it as local."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class DummyViewModel:
        def __init__(self) -> None:
            self._attached_files: list[dict[str, Any]] = []
            self._working = False
            self._working_since = 0.0
            self.self_examination_service = None
            self._oses_ref = None
            self._bootstrap_ref = None
            self._chat_interaction_lifecycle = None
            self._ui_heartbeat_watchdog = None
            self._interaction_has_pending_followup = False
            self._interaction_pending_followup_outcome = ''
            self._interaction_pending_followup_provider = ''
            self.messages: list[tuple[str, str, str, str]] = []
            self.permission_handled = False
            self.live_status = ''

        def _append_message(self, role: str, author: str, text: str, meta: str, **kwargs: Any) -> None:
            self.messages.append((role, author, text, meta))

        def _routing_mode_label(self) -> str:
            return 'local'

        def _set_live_status(self, status: str) -> None:
            self.live_status = status

        def _try_handle_chat_command(self, message: str) -> bool:
            return False

        def _is_external_consultation_diagnosis_question(self, message: str) -> bool:
            return False

        def _try_resolve_pending_observation_permission(self, message: str) -> bool:
            self.permission_handled = True
            return True

        def _try_handle_lightweight_chat(self, message: str) -> bool:
            raise AssertionError('permission approval should return before lightweight chat')

        def _resolve_active_interaction(self, *, outcome: str, provider: str = '') -> None:
            raise AssertionError('approval retry must stay open for external task result')

    dummy = DummyViewModel()

    ControlCenterViewModel.sendChat(dummy, 'si')  # type: ignore[arg-type]

    assert dummy.permission_handled is True
    assert dummy.live_status == 'processing'


def test_explicit_assistant_chat_uses_light_path_before_heavy_analysis() -> None:
    """Explicit ChatGPT requests must not start packet/shortcut work on the UI path."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    class NoSubmitPool:
        def submit(self, *args, **kwargs):
            raise AssertionError('explicit assistant path must skip capability ingestion')

    class DummyViewModel:
        def __init__(self) -> None:
            self._attached_files: list[dict[str, Any]] = []
            self._working = False
            self._working_since = 0.0
            self._bg_pool = NoSubmitPool()
            self.self_examination_service = None
            self._oses_ref = None
            self._bootstrap_ref = None
            self._chat_interaction_lifecycle = None
            self._ui_heartbeat_watchdog = None
            self._last_user_goal = ''
            self._interaction_has_pending_followup = False
            self._interaction_pending_followup_outcome = ''
            self._interaction_pending_followup_provider = ''
            self.messages: list[tuple[str, str, str, str]] = []
            self.phases: list[tuple[str, dict[str, Any]]] = []
            self.consultations: list[tuple[str, bool]] = []

        def _append_message(self, role: str, author: str, text: str, meta: str, **kwargs) -> None:
            self.messages.append((role, author, text, meta))

        def _routing_mode_label(self) -> str:
            return 'local'

        def _set_live_status(self, status: str) -> None:
            self.live_status = status

        def _try_handle_chat_command(self, message: str) -> bool:
            return False

        def _try_resolve_pending_observation_permission(self, message: str) -> bool:
            return False

        def _try_handle_lightweight_chat(self, message: str) -> bool:
            return False

        def _explicit_assistant_preference(self, message: str) -> str:
            return 'chatgpt'

        def _trace_external_consultation_phase(self, phase: str, **payload: Any) -> None:
            self.phases.append((phase, payload))

        def _run_external_consultation(self, assistant_kind: str, *, announce: bool = True) -> bool:
            self.consultations.append((assistant_kind, announce))
            return True

        def _refresh_development_packet_async(self, text: str, *, force: bool = False) -> None:
            raise AssertionError('explicit assistant path must skip development packet refresh')

        def _chat_shortcut_analysis(self, message: str) -> dict[str, Any]:
            raise AssertionError('explicit assistant path must skip shortcut analysis')

        def _resolve_active_interaction(self, *, outcome: str, provider: str = '') -> None:
            raise AssertionError('explicit assistant path should remain open for follow-up')

    dummy = DummyViewModel()

    ControlCenterViewModel.sendChat(dummy, 'has una consulta a chatgpt')  # type: ignore[arg-type]

    assert dummy._last_user_goal == 'has una consulta a chatgpt'
    assert dummy._interaction_has_pending_followup is True
    assert dummy.consultations == [('chatgpt', True)]
    assert dummy.phases
    assert dummy.phases[-1][0] == 'explicit_assistant_light_path'
    assert dummy.phases[-1][1]['skipped_development_packet'] is True


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


def test_post_chat_refreshes_are_deferred_when_budget_blocks() -> None:
    """A chat response must not fan out into heavy refreshes while UI is hot."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    traces: list[tuple[str, dict[str, Any]]] = []
    autonomy_sources: list[str] = []

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError('heavy post-chat refresh should be deferred')

    dummy = SimpleNamespace(
        _background_work_budget_decision=lambda **_kwargs: {
            'allowed': False,
            'decision': 'defer',
            'reason': 'ui_route_stabilizing:control',
            'defer_seconds': 90.0,
        },
        _trace_autonomy_dock=lambda kind, **data: traces.append((kind, data)),
        _process_rss_mb=lambda: 451.0,
        _update_progress_cards=forbidden,
        _refresh_evolution_snapshot_async=forbidden,
        _refresh_agent_cards_async=forbidden,
        _refresh_development_packet_async=forbidden,
        _refresh_autonomy_dock_async=lambda *, source='timer', force=False: autonomy_sources.append(source),
    )

    ControlCenterViewModel._refresh_post_task_surfaces_after_result(dummy, 'chat')  # type: ignore[arg-type]

    assert autonomy_sources == ['post_task:chat']
    assert traces
    assert traces[-1][0] == 'control_post_task_refresh_deferred'
    assert traces[-1][1]['skipped_refreshes'] == [
        'progress_cards',
        'evolution_snapshot',
        'agent_cards',
        'development_packet',
    ]


def test_post_chat_refreshes_run_when_budget_allows() -> None:
    """Allowed post-task budget preserves the normal surface refresh path."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    calls: list[str] = []

    dummy = SimpleNamespace(
        _background_work_budget_decision=lambda **_kwargs: {
            'allowed': True,
            'decision': 'allow',
            'reason': 'budget_available',
        },
        _trace_autonomy_dock=lambda kind, **_data: calls.append(kind),
        _process_rss_mb=lambda: 400.0,
        _update_progress_cards=lambda: calls.append('progress_cards'),
        _refresh_evolution_snapshot_async=lambda: calls.append('evolution_snapshot'),
        _refresh_agent_cards_async=lambda: calls.append('agent_cards'),
        _refresh_development_packet_async=lambda: calls.append('development_packet'),
        _refresh_autonomy_dock_async=lambda *, source='timer', force=False: calls.append(f'autonomy:{source}'),
    )

    ControlCenterViewModel._refresh_post_task_surfaces_after_result(dummy, 'chat')  # type: ignore[arg-type]

    assert calls == [
        'control_post_task_refresh_started',
        'progress_cards',
        'evolution_snapshot',
        'agent_cards',
        'development_packet',
        'autonomy:post_task:chat',
    ]


def test_metacognition_promotion_defers_under_operational_budget() -> None:
    """OSES/PortableContext promotion waits for a rest window instead of spiking RAM."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    traces: list[tuple[str, dict[str, Any]]] = []
    timers: list[float] = []

    class FakeTimer:
        def __init__(self, delay: float, callback: Any) -> None:
            self.delay = delay
            self.callback = callback
            self.daemon = False

        def start(self) -> None:
            timers.append(self.delay)

    dummy = SimpleNamespace(
        _background_work_budget_decision=lambda **_kwargs: {
            'allowed': False,
            'decision': 'defer',
            'reason': 'rest_window_not_reached',
            'defer_seconds': 95.0,
        },
        _trace_autonomy_dock=lambda kind, **data: traces.append((kind, data)),
        _process_rss_mb=lambda: 1800.0,
        _metacognition_promotion_retry_scheduled=False,
        _oses_ref=SimpleNamespace(build_review=MagicMock(side_effect=AssertionError('should not build'))),
        _portable_context_ref=SimpleNamespace(build_package=MagicMock(side_effect=AssertionError('should not build'))),
    )

    with patch('iabv_v15.ui.viewmodels.control_center_viewmodel.threading.Timer', FakeTimer):
        ControlCenterViewModel._promote_metacognition_after_resolution(dummy)  # type: ignore[arg-type]

    assert timers == [95.0]
    assert dummy._metacognition_promotion_retry_scheduled is True
    assert traces[-1][0] == 'interaction_metacognition_promotion_deferred'
    dummy._oses_ref.build_review.assert_not_called()
    dummy._portable_context_ref.build_package.assert_not_called()


def test_metacognition_promotion_records_only_in_ui_process_by_default() -> None:
    """Resolved interactions are durable in audit; UI process must not rebuild OSES/PC."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    traces: list[tuple[str, dict[str, Any]]] = []
    dummy = SimpleNamespace(
        _background_work_budget_decision=lambda **_kwargs: {
            'allowed': True,
            'decision': 'allow',
            'reason': 'idle_rest_window_available',
        },
        _trace_autonomy_dock=lambda kind, **data: traces.append((kind, data)),
        _process_rss_mb=lambda: 330.0,
        _metacognition_promotion_retry_scheduled=True,
        _oses_ref=SimpleNamespace(build_review=MagicMock(side_effect=AssertionError('should not build in UI'))),
        _portable_context_ref=SimpleNamespace(build_package=MagicMock(side_effect=AssertionError('should not build in UI'))),
    )

    with patch.dict('os.environ', {'IABV_ENABLE_UI_INTERACTION_PROMOTION': ''}, clear=False):
        ControlCenterViewModel._promote_metacognition_after_resolution(dummy)  # type: ignore[arg-type]

    assert dummy._metacognition_promotion_retry_scheduled is False
    assert traces[-1][0] == 'interaction_metacognition_promotion_recorded_only'
    assert traces[-1][1]['reason'] == 'runtime_audit_durable_ui_process_promotion_disabled'
    dummy._oses_ref.build_review.assert_not_called()
    dummy._portable_context_ref.build_package.assert_not_called()
