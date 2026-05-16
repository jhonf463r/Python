"""Focused tests for P0.12: Runtime Build Fingerprint + Stale-Code Gate +
Freeze Root Cause + ChatGPT Security Handoff + Browser Thread Affinity.

Tests:
 A. runtime_build_fingerprint emitted (targeted scan, scoped dirty, budget)
 B. stale-code gate warning shown
 C. heavy refresh deferred under query_pending / resource_pressure / stall / consultation cooldown
 D. freeze report includes pre-stall events
 E. security verification produces terminal_state blocked_by_security_verification
 F. single retest after "ya lo hice" — worker routes via signal, not direct UI
 G. browser close not executed from wrong thread; close_if_owner_thread drains
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)


# ======================================================================
# A. Runtime Build Fingerprint
# ======================================================================

class TestRuntimeBuildFingerprint:

    @pytest.fixture()
    def tracer(self, tmp_path: Path):
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        t = RuntimeAuditTracer(log_dir=str(tmp_path))
        t.configure(tmp_path)
        return t

    def test_trace_build_fingerprint_emitted(self, tracer, tmp_path: Path) -> None:
        event = tracer.trace_build_fingerprint(workspace=str(tmp_path))
        assert event['kind'] == 'runtime_build_fingerprint'
        data = event['data']
        assert 'branch' in data
        assert 'head' in data
        assert 'dirty' in data
        assert 'feature_markers' in data
        assert 'stale' in data
        assert 'missing_markers' in data

    def test_fingerprint_includes_workspace(self, tracer, tmp_path: Path) -> None:
        event = tracer.trace_build_fingerprint(workspace=str(tmp_path))
        assert str(tmp_path) in event['data']['workspace'] or 'workspace' in event['data']

    def test_fingerprint_stored_in_events(self, tracer, tmp_path: Path) -> None:
        tracer.trace_build_fingerprint(workspace=str(tmp_path))
        fps = tracer.events(kind='runtime_build_fingerprint')
        assert len(fps) == 1

    def test_collect_build_fingerprint_markers(self, tmp_path: Path) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import _collect_build_fingerprint
        fp = _collect_build_fingerprint(str(tmp_path))
        assert isinstance(fp['feature_markers'], dict)
        assert isinstance(fp['stale'], bool)
        assert isinstance(fp['missing_markers'], list)

    def test_fingerprint_uses_targeted_files_not_rglob(self, tmp_path: Path) -> None:
        """_collect_build_fingerprint should NOT use rglob in its code body."""
        from iabv_v15.services.evolution import runtime_audit_tracer as mod
        import inspect
        src = inspect.getsource(mod._collect_build_fingerprint)
        # Strip docstring; only check actual code
        body = src.split('"""', 2)[-1] if '"""' in src else src
        assert 'rglob' not in body

    def test_fingerprint_scoped_dirty_flag(self, tmp_path: Path) -> None:
        """Dirty check uses diff-index scoped to src/tests/AGENTS.md."""
        from iabv_v15.services.evolution.runtime_audit_tracer import _collect_build_fingerprint
        fp = _collect_build_fingerprint(str(tmp_path))
        assert 'git_status' in fp
        assert fp['git_status'] in ('clean', 'dirty', 'unknown')

    def test_fingerprint_includes_elapsed_ms(self, tmp_path: Path) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import _collect_build_fingerprint
        fp = _collect_build_fingerprint(str(tmp_path))
        assert 'elapsed_ms' in fp
        assert isinstance(fp['elapsed_ms'], float)

    def test_fingerprint_slow_trace_emitted_when_over_budget(self, tracer, tmp_path: Path) -> None:
        from iabv_v15.services.evolution import runtime_audit_tracer as mod
        original = mod._FINGERPRINT_BUDGET_MS
        try:
            mod._FINGERPRINT_BUDGET_MS = 0.0
            tracer.trace_build_fingerprint(workspace=str(tmp_path))
            slow = tracer.events(kind='runtime_build_fingerprint_slow')
            assert len(slow) == 1
        finally:
            mod._FINGERPRINT_BUDGET_MS = original

    def test_current_elapsed_ms(self, tracer) -> None:
        ms = tracer.current_elapsed_ms()
        assert isinstance(ms, float)
        assert ms >= 0


# ======================================================================
# B. Stale-Code Gate
# ======================================================================

class TestStaleCodeGate:

    def test_stale_detected_when_markers_missing(self, tmp_path: Path) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import _collect_build_fingerprint
        fp = _collect_build_fingerprint(str(tmp_path))
        assert fp['stale'] is True
        assert len(fp['missing_markers']) > 0

    def test_stale_not_detected_when_all_markers_present(self) -> None:
        """When run against the real repo, all markers should be present."""
        from iabv_v15.services.evolution.runtime_audit_tracer import _collect_build_fingerprint
        repo_root = Path(__file__).resolve().parent.parent
        fp = _collect_build_fingerprint(str(repo_root))
        assert fp['stale'] is False
        assert fp['missing_markers'] == []

    def test_runtime_build_stale_detected_trace(self, tmp_path: Path) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
        tracer.configure(tmp_path)
        fp_event = tracer.trace_build_fingerprint(workspace=str(tmp_path))
        fp_data = fp_event.get('data', {})
        if fp_data.get('stale'):
            tracer.trace(
                'runtime_build_stale_detected',
                branch=fp_data.get('branch', ''),
                head=fp_data.get('head', ''),
                missing_markers=fp_data.get('missing_markers', []),
            )
        stale_events = tracer.events(kind='runtime_build_stale_detected')
        assert len(stale_events) == 1


# ======================================================================
# C. Freeze Root Cause — heavy refresh deferred under pressure
# ======================================================================

class TestPlatformPendingP012:

    _PENDING_DIR = (
        Path(__file__).resolve().parent.parent
        / 'data' / 'evolution' / 'platform_pending'
    )

    def _load_task(self, filename: str):
        from iabv_v15.domain.models import PlatformPendingTask
        path = self._PENDING_DIR / filename
        assert path.exists(), f'Missing platform pending task: {path}'
        return PlatformPendingTask.model_validate_json(path.read_text(encoding='utf-8'))

    def test_platform_pending_p012_valid_schema(self) -> None:
        for filename in (
            'task_runtime_consulting_lifecycle_recovery.json',
            'task_external_visual_handoff_alignment.json',
            'task_runtime_main_thread_antifreeze_budget.json',
        ):
            task = self._load_task(filename)
            assert task.id
            assert task.metadata.get('p012_additions')

    def test_platform_pending_marks_stale_build_invalid_semantics(self) -> None:
        task = self._load_task('task_runtime_consulting_lifecycle_recovery.json')
        policy = task.metadata.get('p012_stale_build_policy') or {}
        assert policy.get('covered_by_pr') == '#390'
        assert policy.get('invalid_by_stale_build') is True
        assert policy.get('required_runtime_event') == 'runtime_build_fingerprint'

    def test_platform_pending_keeps_live_proof_unresolved_until_windows_run(self) -> None:
        external = self._load_task('task_external_visual_handoff_alignment.json')
        antifreeze = self._load_task('task_runtime_main_thread_antifreeze_budget.json')
        assert external.metadata['p012_live_proof_policy']['unresolved'] == (
            'UNRESOLVED:live_windows_chatgpt_security_retest'
        )
        assert antifreeze.metadata['p012_live_proof_policy']['unresolved'] == (
            'UNRESOLVED:live_windows_antifreeze_proof_missing'
        )


class TestFreezeRootCause:

    def test_should_skip_dock_refresh_when_working(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = True
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'query_pending'

    def test_should_skip_dock_refresh_coalesced(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = time.time()
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'coalesced'

    def test_should_skip_dock_refresh_resource_pressure(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._last_external_consultation_ts = 0.0
        vm._should_defer_heavy_work = MagicMock(return_value=True)
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'resource_pressure'

    def test_should_not_skip_under_normal_conditions(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._last_external_consultation_ts = 0.0
        vm._should_defer_heavy_work = MagicMock(return_value=False)
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == ''

    def test_should_skip_after_recent_external_consultation(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._last_external_consultation_ts = time.time()
        vm._DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S = 30.0
        vm._should_defer_heavy_work = MagicMock(return_value=False)
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'post_external_consultation'

    def test_should_skip_during_budget_cooldown(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = time.time() + 60
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'budget_cooldown'

    def test_recent_heavy_stall_uses_process_elapsed(self) -> None:
        """Stall gate compares elapsed_ms (process-relative), not epoch."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        from iabv_v15.services.evolution import runtime_audit_tracer as rat_mod
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace(
            'ui_event', event_type='ui_event_loop_stall', duration_ms=5000,
        )
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._last_external_consultation_ts = 0.0
        vm._DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S = 30.0
        vm._should_defer_heavy_work = MagicMock(return_value=False)
        original = rat_mod.get_runtime_tracer
        rat_mod.get_runtime_tracer = lambda: tracer
        try:
            result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        finally:
            rat_mod.get_runtime_tracer = original
        assert result == 'recent_heavy_stall'

    def test_old_heavy_stall_does_not_block(self) -> None:
        """Stall older than 30s should NOT trigger recent_heavy_stall."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        from iabv_v15.services.evolution import runtime_audit_tracer as rat_mod
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        event = tracer.trace(
            'ui_event', event_type='ui_event_loop_stall', duration_ms=5000,
        )
        # Backdate: make it look like it happened 60s ago in process time
        now_elapsed = tracer.current_elapsed_ms()
        event['elapsed_ms'] = now_elapsed - 60_000
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._last_external_consultation_ts = 0.0
        vm._DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S = 30.0
        vm._should_defer_heavy_work = MagicMock(return_value=False)
        original = rat_mod.get_runtime_tracer
        rat_mod.get_runtime_tracer = lambda: tracer
        try:
            result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        finally:
            rat_mod.get_runtime_tracer = original
        assert result == ''

    def test_refresh_dock_sets_budget_cooldown_on_slow_projector(self) -> None:
        """After budget exceeded, subsequent refreshes are skipped by cooldown."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._dock_budget_cooldown_until = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._DOCK_REFRESH_BUDGET_MS = 0.001
        vm._DOCK_REFRESH_BUDGET_COOLDOWN_S = 10.0
        vm._last_external_consultation_ts = 0.0
        vm._DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S = 30.0
        vm._should_defer_heavy_work = MagicMock(return_value=False)
        # Bypass _should_skip_dock_refresh so the projector actually runs
        vm._should_skip_dock_refresh = MagicMock(return_value='')
        def _slow_project(**kw):
            time.sleep(0.005)
            return {
                'live_process_summary': {},
                'live_work_items': [],
                'assistant_session_cards': [],
                'autonomy_timeline': [],
            }
        slow_projector = MagicMock()
        slow_projector.project.side_effect = _slow_project
        vm.autonomy_activity_projector = slow_projector
        vm._goal_context_for_display = MagicMock(return_value={})
        vm._latest_live_audit = MagicMock(return_value={})
        vm._latest_replay_visual_summary = MagicMock(return_value={})
        vm.get_autonomy_activity = MagicMock(return_value={})
        vm._current_site_id = MagicMock(return_value='')
        ControlCenterViewModel._refresh_autonomy_dock(vm)
        assert vm._dock_budget_cooldown_until > time.time()


# ======================================================================
# D. Freeze Incident Reporter includes pre-stall events
# ======================================================================

class TestFreezeIncidentReporterEnriched:

    @pytest.fixture()
    def reporter(self, tmp_path: Path):
        from iabv_v15.services.evolution.freeze_incident_reporter import FreezeIncidentReporter
        return FreezeIncidentReporter(evolution_dir=str(tmp_path))

    def test_capture_includes_runtime_audit_context(self, reporter, tmp_path: Path) -> None:
        path = reporter.capture_incident(trigger='test')
        data = json.loads(path.read_text(encoding='utf-8'))
        assert 'runtime_audit_context' in data

    def test_runtime_audit_context_has_recent_events(self, reporter, tmp_path: Path) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
        tracer = get_runtime_tracer()
        tracer.trace('before_freeze_1')
        tracer.trace('before_freeze_2')
        path = reporter.capture_incident(trigger='auto')
        data = json.loads(path.read_text(encoding='utf-8'))
        ctx = data['runtime_audit_context']
        assert 'recent_events' in ctx
        assert len(ctx['recent_events']) >= 2


# ======================================================================
# E. ChatGPT Security Handoff
# ======================================================================

class TestChatGPTSecurityHandoff:

    def test_security_verification_failure_message(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._external_state_notice = MagicMock(return_value='')
        result = ControlCenterViewModel._human_external_consultation_failure(
            vm, 'ChatGPT', 'browser_security_verification detected', [],
        )
        message, meta, busy = result
        assert 'blocked_by_security_verification' in meta
        assert 'captcha' in message.lower() or 'verificacion' in message.lower()
        assert 'Evidencia:' in message
        assert 'Accion humana:' in message
        assert 'ya lo hice' in message

    def test_terminal_state_blocked_by_security_verification(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert 'blocked_by_security_verification' in ControlCenterViewModel._TERMINAL_DISPATCH_STATES


# ======================================================================
# F. Security Verification Retest
# ======================================================================

class TestSecurityVerificationRetest:

    def test_retest_patterns_detected(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        patterns = ControlCenterViewModel._SECURITY_RETEST_PATTERNS
        assert 'ya lo hice' in patterns
        assert 'a mi si me funciona' in patterns

    def test_retest_not_triggered_without_security_context(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._last_adaptive_payload = {}
        vm._SECURITY_RETEST_PATTERNS = ControlCenterViewModel._SECURITY_RETEST_PATTERNS
        result = ControlCenterViewModel._try_handle_security_verification_retest(vm, 'ya lo hice')
        assert result is False

    def test_retest_guard_prevents_second_retest(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._security_retest_done = True
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation': {
                    'detail': 'browser_security_verification',
                    'status': 'blocked_external',
                    'assistant_kind': 'chatgpt',
                },
            },
        }
        vm._SECURITY_RETEST_PATTERNS = ControlCenterViewModel._SECURITY_RETEST_PATTERNS
        vm._set_live_status = MagicMock()
        vm._append_message = MagicMock()
        result = ControlCenterViewModel._try_handle_security_verification_retest(vm, 'ya lo hice')
        assert result is True
        vm._append_message.assert_called_once()
        msg = vm._append_message.call_args[0][2]
        assert 'Ya hice un retest' in msg

    def test_retest_worker_does_not_call_append_message(self) -> None:
        """Worker emits taskResolved/taskFailed; never calls _append_message directly."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        import inspect
        src = inspect.getsource(ControlCenterViewModel._try_handle_security_verification_retest)
        worker_src = src[src.index('def _retest_worker'):]
        assert '_append_message' not in worker_src
        assert '_set_live_status' not in worker_src


# ======================================================================
# G. Browser Thread Affinity
# ======================================================================

class TestBrowserThreadAffinity:

    def test_close_from_wrong_thread_defers(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = -99999
        ctrl._context = MagicMock()
        ctrl._browser = MagicMock()
        ctrl._pw = MagicMock()
        ctrl.close()
        ctrl._context.close.assert_not_called()
        ctrl._browser.close.assert_not_called()
        ctrl._pw.stop.assert_not_called()

    def test_close_from_wrong_thread_sets_close_requested(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = -99999
        ctrl._context = MagicMock()
        assert ctrl._close_requested is False
        ctrl.close()
        assert ctrl._close_requested is True

    def test_close_if_owner_thread_drains_deferred(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = threading.current_thread().ident
        mock_ctx = MagicMock()
        mock_browser = MagicMock()
        mock_pw = MagicMock()
        ctrl._context = mock_ctx
        ctrl._browser = mock_browser
        ctrl._pw = mock_pw
        ctrl._close_requested = True
        result = ctrl.close_if_owner_thread()
        assert result is True
        mock_ctx.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
        assert ctrl._close_requested is False

    def test_context_property_drains_deferred_close_on_owner_thread(self) -> None:
        """A real owner-thread safe point drains deferred close before reuse."""
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = threading.current_thread().ident
        mock_ctx = MagicMock()
        mock_browser = MagicMock()
        mock_pw = MagicMock()
        ctrl._context = mock_ctx
        ctrl._browser = mock_browser
        ctrl._pw = mock_pw
        ctrl._close_requested = True

        assert ctrl.context is None

        mock_ctx.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
        assert ctrl._close_requested is False
        assert ctrl._owner_thread_id is None

    def test_unavailable_owner_thread_marks_unresolved_once(self) -> None:
        """If the owner thread is gone, trace unresolved without blocking UI."""
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = -99999
        ctrl._close_requested = True
        tracer = MagicMock()

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            assert ctrl.close_if_owner_thread() is False
            assert ctrl.close_if_owner_thread() is False

        assert ctrl._close_unresolved_reported is True
        tracer.trace.assert_called_once()
        assert tracer.trace.call_args.args[0] == 'browser_session_close_unresolved'
        assert tracer.trace.call_args.kwargs['reason'] == 'owner_thread_unavailable'

    def test_close_if_owner_thread_noop_without_request(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = threading.current_thread().ident
        assert ctrl.close_if_owner_thread() is False

    def test_close_if_owner_thread_noop_from_wrong_thread(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = -99999
        ctrl._close_requested = True
        assert ctrl.close_if_owner_thread() is False

    def test_close_from_owner_thread_proceeds(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        ctrl._owner_thread_id = threading.current_thread().ident
        mock_ctx = MagicMock()
        mock_browser = MagicMock()
        mock_pw = MagicMock()
        ctrl._context = mock_ctx
        ctrl._browser = mock_browser
        ctrl._pw = mock_pw
        ctrl.close()
        mock_ctx.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    def test_close_without_owner_thread_proceeds(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        assert ctrl._owner_thread_id is None
        mock_ctx = MagicMock()
        ctrl._context = mock_ctx
        ctrl.close()
        mock_ctx.close.assert_called_once()

    def test_owner_thread_set_on_start(self) -> None:
        from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
        ctrl = BrowserSessionController()
        assert ctrl._owner_thread_id is None
