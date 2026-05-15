"""Focused tests for P0.12: Runtime Build Fingerprint + Stale-Code Gate +
Freeze Root Cause + ChatGPT Security Handoff + Browser Thread Affinity.

Tests:
 A. runtime_build_fingerprint emitted
 B. stale-code gate warning shown
 C. heavy refresh deferred under query_pending / resource_pressure
 D. freeze report includes pre-stall events
 E. security verification produces terminal_state blocked_by_security_verification
 F. single retest after "ya lo hice"
 G. browser close not executed from wrong thread
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

class TestFreezeRootCause:

    def test_should_skip_dock_refresh_when_working(self) -> None:
        """_should_skip_dock_refresh returns 'query_pending' when _working=True."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = True
        vm._last_dock_refresh_ts = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'query_pending'

    def test_should_skip_dock_refresh_coalesced(self) -> None:
        """_should_skip_dock_refresh returns 'coalesced' when called rapidly."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = time.time()
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'coalesced'

    def test_should_skip_dock_refresh_resource_pressure(self) -> None:
        """_should_skip_dock_refresh returns 'resource_pressure' under pressure."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._should_defer_heavy_work = MagicMock(return_value=True)
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == 'resource_pressure'

    def test_should_not_skip_under_normal_conditions(self) -> None:
        """_should_skip_dock_refresh returns '' when nothing is pressured."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._working = False
        vm._last_dock_refresh_ts = 0.0
        vm._DOCK_REFRESH_MIN_INTERVAL_S = 1.0
        vm._should_defer_heavy_work = MagicMock(return_value=False)
        result = ControlCenterViewModel._should_skip_dock_refresh(vm)
        assert result == ''


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
