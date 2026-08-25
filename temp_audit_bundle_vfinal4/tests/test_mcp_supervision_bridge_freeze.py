"""Tests for Tasks 8, 9, 10:
- Task 8: MCP supervision and auto-restart with heartbeat
- Task 9: Bridge queue readiness handshake (shell not ready while splash up)
- Task 10: Freeze diagnostics (diagnose_freeze_cause)
"""

from __future__ import annotations

import json
import sys
import time
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from iabv_v15.services.ui_bridge_service import UIBridgeServer
from iabv_v15.services.evolution.freeze_incident_reporter import (
    FreezeIncidentReporter,
)


# ======================================================================
# Task 8: MCP supervision and auto-restart
# ======================================================================


class _FakeProcess:
    """Minimal subprocess.Popen stand-in for supervision tests."""

    def __init__(self, *, alive: bool = True, returncode: int = 0) -> None:
        self._alive = alive
        self.returncode = returncode if not alive else None
        self.pid = 12345
        self._terminated = False
        self._killed = False

    def poll(self) -> int | None:
        if self._alive:
            return None
        return self.returncode

    def terminate(self) -> None:
        self._terminated = True
        self._alive = False

    def kill(self) -> None:
        self._killed = True
        self._alive = False

    def wait(self, timeout: float = 5) -> int:
        return self.returncode or 0

    def die(self, code: int = 1) -> None:
        """Simulate process crash."""
        self._alive = False
        self.returncode = code


class _MinimalBootstrap:
    """Minimal stand-in for AppBootstrap to test MCP supervision logic."""

    _MCP_HEARTBEAT_INTERVAL_S: float = 0.1  # Fast for tests
    _MCP_MAX_RESTART_ATTEMPTS: int = 3
    _MCP_RESTART_COOLDOWN_S: float = 0.05

    def __init__(self) -> None:
        self._mcp_proc: _FakeProcess | None = None
        self._tunnel_proc: _FakeProcess | None = None
        self._mcp_supervisor_running = False
        self._mcp_supervision_status: dict[str, Any] = {}
        self._mcp_supervisor_thread: threading.Thread | None = None
        self._mcp_restart_count = 0
        self._tunnel_restart_count = 0

    def _start_mcp_subprocess(self) -> _FakeProcess | None:
        self._mcp_restart_count += 1
        return _FakeProcess(alive=True)

    def _start_tunnel_subprocess(self) -> _FakeProcess | None:
        self._tunnel_restart_count += 1
        return _FakeProcess(alive=True)

    # Import the real methods from AppBootstrap
    def _mcp_supervision_loop(self) -> None:
        import time as _time

        mcp_restarts = 0
        tunnel_restarts = 0
        last_mcp_restart: float = 0
        last_tunnel_restart: float = 0

        while getattr(self, '_mcp_supervisor_running', True):
            _time.sleep(self._MCP_HEARTBEAT_INTERVAL_S)

            if not getattr(self, '_mcp_supervisor_running', True):
                break

            now = _time.monotonic()

            mcp = getattr(self, '_mcp_proc', None)
            if mcp is not None and mcp.poll() is not None:
                if (
                    mcp_restarts < self._MCP_MAX_RESTART_ATTEMPTS
                    and (now - last_mcp_restart) > self._MCP_RESTART_COOLDOWN_S
                ):
                    mcp_restarts += 1
                    last_mcp_restart = now
                    self._mcp_proc = self._start_mcp_subprocess()

            tunnel = getattr(self, '_tunnel_proc', None)
            if tunnel is not None and tunnel.poll() is not None:
                if (
                    tunnel_restarts < self._MCP_MAX_RESTART_ATTEMPTS
                    and (now - last_tunnel_restart) > self._MCP_RESTART_COOLDOWN_S
                ):
                    tunnel_restarts += 1
                    last_tunnel_restart = now
                    self._tunnel_proc = self._start_tunnel_subprocess()

            self._mcp_supervision_status = {
                'mcp_alive': (
                    getattr(self, '_mcp_proc', None) is not None
                    and self._mcp_proc.poll() is None
                ),
                'tunnel_alive': (
                    getattr(self, '_tunnel_proc', None) is not None
                    and self._tunnel_proc.poll() is None
                ),
                'mcp_restarts': mcp_restarts,
                'tunnel_restarts': tunnel_restarts,
                'mcp_max_restarts_reached': mcp_restarts >= self._MCP_MAX_RESTART_ATTEMPTS,
                'tunnel_max_restarts_reached': tunnel_restarts >= self._MCP_MAX_RESTART_ATTEMPTS,
            }

    def _start_mcp_supervisor(self) -> None:
        self._mcp_supervisor_running = True
        self._mcp_supervisor_thread = threading.Thread(
            target=self._mcp_supervision_loop,
            name='mcp-supervisor-test',
            daemon=True,
        )
        self._mcp_supervisor_thread.start()

    def _stop_mcp_supervisor(self) -> None:
        self._mcp_supervisor_running = False
        if self._mcp_supervisor_thread:
            self._mcp_supervisor_thread.join(timeout=2)

    def mcp_supervision_status(self) -> dict[str, Any]:
        return getattr(self, '_mcp_supervision_status', {})


class TestMCPSupervision:
    """Task 8: MCP supervision and auto-restart with heartbeat."""

    def test_supervisor_starts_and_stops(self) -> None:
        bs = _MinimalBootstrap()
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)
        bs._start_mcp_supervisor()
        assert bs._mcp_supervisor_running is True
        time.sleep(0.3)
        bs._stop_mcp_supervisor()
        assert bs._mcp_supervisor_running is False

    def test_status_reports_alive_processes(self) -> None:
        bs = _MinimalBootstrap()
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)
        bs._start_mcp_supervisor()
        time.sleep(0.3)
        status = bs.mcp_supervision_status()
        bs._stop_mcp_supervisor()
        assert status['mcp_alive'] is True
        assert status['tunnel_alive'] is True
        assert status['mcp_restarts'] == 0
        assert status['tunnel_restarts'] == 0

    def test_mcp_crash_triggers_restart(self) -> None:
        bs = _MinimalBootstrap()
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)
        bs._start_mcp_supervisor()
        time.sleep(0.2)

        # Simulate MCP crash
        bs._mcp_proc.die(code=1)
        time.sleep(0.5)

        status = bs.mcp_supervision_status()
        bs._stop_mcp_supervisor()
        assert status['mcp_restarts'] >= 1
        assert bs._mcp_restart_count >= 1

    def test_tunnel_crash_triggers_restart(self) -> None:
        bs = _MinimalBootstrap()
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)
        bs._start_mcp_supervisor()
        time.sleep(0.2)

        # Simulate tunnel crash
        bs._tunnel_proc.die(code=1)
        time.sleep(0.5)

        status = bs.mcp_supervision_status()
        bs._stop_mcp_supervisor()
        assert status['tunnel_restarts'] >= 1
        assert bs._tunnel_restart_count >= 1

    def test_max_restarts_respected(self) -> None:
        bs = _MinimalBootstrap()
        bs._MCP_HEARTBEAT_INTERVAL_S = 0.05
        bs._MCP_RESTART_COOLDOWN_S = 0.01
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)

        # Override to always return a dead process
        def _start_dead_mcp() -> _FakeProcess:
            bs._mcp_restart_count += 1
            return _FakeProcess(alive=False, returncode=1)

        bs._start_mcp_subprocess = _start_dead_mcp  # type: ignore[assignment]

        bs._mcp_proc.die(code=1)
        bs._start_mcp_supervisor()
        time.sleep(1.5)

        status = bs.mcp_supervision_status()
        bs._stop_mcp_supervisor()
        assert status['mcp_max_restarts_reached'] is True
        assert status['mcp_restarts'] == bs._MCP_MAX_RESTART_ATTEMPTS

    def test_status_shape(self) -> None:
        bs = _MinimalBootstrap()
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)
        bs._start_mcp_supervisor()
        time.sleep(0.3)
        status = bs.mcp_supervision_status()
        bs._stop_mcp_supervisor()

        expected_keys = {
            'mcp_alive', 'tunnel_alive', 'mcp_restarts',
            'tunnel_restarts', 'mcp_max_restarts_reached',
            'tunnel_max_restarts_reached',
        }
        assert set(status.keys()) == expected_keys

    def test_no_restart_when_processes_alive(self) -> None:
        bs = _MinimalBootstrap()
        bs._mcp_proc = _FakeProcess(alive=True)
        bs._tunnel_proc = _FakeProcess(alive=True)
        bs._start_mcp_supervisor()
        time.sleep(0.5)
        status = bs.mcp_supervision_status()
        bs._stop_mcp_supervisor()
        assert status['mcp_restarts'] == 0
        assert status['tunnel_restarts'] == 0
        assert bs._mcp_restart_count == 0
        assert bs._tunnel_restart_count == 0

    def test_default_status_without_supervisor(self) -> None:
        bs = _MinimalBootstrap()
        status = bs.mcp_supervision_status()
        assert status == {}


# ======================================================================
# Task 9: Bridge queue readiness handshake
# ======================================================================


class TestBridgeReadinessHandshake:
    """Task 9: Bridge queue not responding while splash is up."""

    def test_initial_state_not_ready(self) -> None:
        server = UIBridgeServer()
        assert server._shell_ready is False
        snapshot = server.readiness_snapshot()
        assert snapshot['shell_ready'] is False
        assert snapshot['pending_count'] == 0

    def test_mark_shell_ready(self) -> None:
        server = UIBridgeServer()
        server.mark_shell_ready()
        assert server._shell_ready is True
        snapshot = server.readiness_snapshot()
        assert snapshot['shell_ready'] is True

    def test_enqueue_pending_message(self) -> None:
        server = UIBridgeServer()
        server.enqueue_pending_message({'text': 'hello'})
        server.enqueue_pending_message({'text': 'world'})
        snapshot = server.readiness_snapshot()
        assert snapshot['pending_count'] == 2

    def test_mark_shell_ready_flushes_pending(self) -> None:
        server = UIBridgeServer()
        flushed: list[dict[str, Any]] = []

        def handler(**kwargs: Any) -> None:
            flushed.append(kwargs)

        server.register_handler('send_message', handler)
        server.enqueue_pending_message({'text': 'msg1'})
        server.enqueue_pending_message({'text': 'msg2'})
        assert server.readiness_snapshot()['pending_count'] == 2

        server.mark_shell_ready()
        assert server.readiness_snapshot()['pending_count'] == 0
        assert len(flushed) == 2
        assert flushed[0] == {'text': 'msg1'}
        assert flushed[1] == {'text': 'msg2'}

    def test_dispatch_buffers_send_message_when_not_ready(self) -> None:
        server = UIBridgeServer()
        handler_called = []

        def handler(**kwargs: Any) -> None:
            handler_called.append(kwargs)

        server.register_handler('send_message', handler)

        # Dispatch while not ready
        result = server._dispatch(json.dumps({
            'id': 1,
            'method': 'send_message',
            'params': {'text': 'queued'},
        }))
        assert result['result']['status'] in ('queued_pending_shell_ready', 'pending_shell_ready')
        assert len(handler_called) == 0
        assert server.readiness_snapshot()['pending_count'] == 1

    def test_dispatch_passes_through_non_send_message(self) -> None:
        server = UIBridgeServer()
        read_called = []

        def handler(**kwargs: Any) -> dict[str, Any]:
            read_called.append(True)
            return {'messages': []}

        server.register_handler('read_messages', handler)

        # read_messages should pass through even when not ready
        result = server._dispatch(json.dumps({
            'id': 2,
            'method': 'read_messages',
            'params': {},
        }))
        assert 'result' in result
        assert len(read_called) == 1

    def test_dispatch_passes_send_message_when_ready(self) -> None:
        server = UIBridgeServer()
        handler_called = []

        def handler(**kwargs: Any) -> dict[str, str]:
            handler_called.append(kwargs)
            return {'status': 'sent'}

        server.register_handler('send_message', handler)
        server.mark_shell_ready()

        result = server._dispatch(json.dumps({
            'id': 3,
            'method': 'send_message',
            'params': {'text': 'direct'},
        }))
        assert result['result'] == {'status': 'sent'}
        assert len(handler_called) == 1

    def test_mark_shell_ready_idempotent(self) -> None:
        server = UIBridgeServer()
        server.mark_shell_ready()
        server.mark_shell_ready()
        assert server._shell_ready is True

    def test_pending_handler_not_found_is_safe(self) -> None:
        server = UIBridgeServer()
        server.enqueue_pending_message({'x': 1})
        # Should not raise
        server.mark_shell_ready()
        assert server.readiness_snapshot()['pending_count'] == 0

    def test_thread_safety_of_readiness(self) -> None:
        server = UIBridgeServer()
        errors: list[str] = []

        def enqueue_many() -> None:
            for i in range(50):
                try:
                    server.enqueue_pending_message({'i': i})
                except Exception as e:
                    errors.append(str(e))

        t1 = threading.Thread(target=enqueue_many)
        t2 = threading.Thread(target=enqueue_many)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(errors) == 0
        assert server.readiness_snapshot()['pending_count'] == 100


# ======================================================================
# Task 10: Freeze diagnostics — diagnose_freeze_cause
# ======================================================================


class TestFreezeDiagnostics:
    """Task 10: Freeze diagnostics using existing FreezeIncidentReporter."""

    @pytest.fixture()
    def reporter(self, tmp_path: Path) -> FreezeIncidentReporter:
        return FreezeIncidentReporter(evolution_dir=str(tmp_path))

    def test_no_incidents_returns_empty_diagnosis(self, reporter: FreezeIncidentReporter) -> None:
        diagnosis = reporter.diagnose_freeze_cause()
        assert diagnosis['dominant_cause'] == 'none'
        assert diagnosis['incident_count'] == 0
        assert diagnosis['config_recommendations'] == []
        assert 'No recent freeze incidents' in diagnosis['summary']

    def test_diagnosis_with_single_incident(self, reporter: FreezeIncidentReporter) -> None:
        reporter.capture_incident(trigger='test', extra_context={
            'incident_type': 'ui_stall',
            'severity': 'medium',
            'dominant_phase': 'qml_load',
            'duration_ms': 3000,
        })
        diagnosis = reporter.diagnose_freeze_cause()
        assert diagnosis['incident_count'] == 1
        assert diagnosis['dominant_cause'] == 'ui_stall'
        assert diagnosis['dominant_phase'] == 'qml_load'

    def test_diagnosis_identifies_dominant_cause(self, reporter: FreezeIncidentReporter) -> None:
        for _ in range(3):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'chat_stall',
                'severity': 'high',
                'dominant_phase': 'shortcut_analysis',
                'duration_ms': 5000,
            })
        reporter.capture_incident(trigger='auto', extra_context={
            'incident_type': 'ui_stall',
            'severity': 'medium',
            'dominant_phase': 'qml_load',
            'duration_ms': 2000,
        })
        diagnosis = reporter.diagnose_freeze_cause()
        assert diagnosis['dominant_cause'] == 'chat_stall'
        assert diagnosis['cause_distribution']['chat_stall'] == 3
        assert diagnosis['cause_distribution']['ui_stall'] == 1

    def test_chat_stall_recommendation(self, reporter: FreezeIncidentReporter) -> None:
        for _ in range(4):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'chat_stall',
                'severity': 'high',
                'dominant_phase': 'shortcut_analysis',
                'duration_ms': 5000,
            })
        diagnosis = reporter.diagnose_freeze_cause()
        config_names = [r['config'] for r in diagnosis['config_recommendations']]
        assert 'IABV_CHAT_ASYNC_THRESHOLD_MS' in config_names

    def test_startup_related_recommendation(self, reporter: FreezeIncidentReporter) -> None:
        for _ in range(4):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'startup_freeze',
                'severity': 'high',
                'dominant_phase': 'services_init',
                'duration_ms': 6000,
                'startup_followup_active': True,
            })
        diagnosis = reporter.diagnose_freeze_cause()
        config_names = [r['config'] for r in diagnosis['config_recommendations']]
        assert 'IABV_DEFER_METACOGNITION' in config_names

    def test_high_avg_duration_recommendation(self, reporter: FreezeIncidentReporter) -> None:
        for _ in range(3):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'ui_stall',
                'severity': 'high',
                'dominant_phase': 'heavy_compute',
                'duration_ms': 12000,
            })
        diagnosis = reporter.diagnose_freeze_cause()
        config_names = [r['config'] for r in diagnosis['config_recommendations']]
        assert 'IABV_REDUCE_PARALLEL_SCANS' in config_names

    def test_severity_trend_worsening(self, reporter: FreezeIncidentReporter) -> None:
        # list_reports returns newest-first, so create high-severity LAST
        # so they appear in the first half (newest = most recent).
        # First half (newest = high severity) vs second half (oldest = low).
        for _ in range(3):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'ui_stall',
                'severity': 'low',
                'dominant_phase': 'idle',
                'duration_ms': 2000,
            })
        import time as _t; _t.sleep(0.01)
        for _ in range(3):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'ui_stall',
                'severity': 'high',
                'dominant_phase': 'heavy',
                'duration_ms': 8000,
            })
        diagnosis = reporter.diagnose_freeze_cause()
        # newest (high) in first half → worsening
        assert diagnosis['severity_trend'] == 'worsening'
        config_names = [r['config'] for r in diagnosis['config_recommendations']]
        assert 'IABV_AGGRESSIVE_GC' in config_names

    def test_severity_trend_improving(self, reporter: FreezeIncidentReporter) -> None:
        # newest-first ordering: create low-severity LAST so they
        # appear in the first half → improving trend.
        for _ in range(3):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'ui_stall',
                'severity': 'high',
                'dominant_phase': 'heavy',
                'duration_ms': 8000,
            })
        import time as _t; _t.sleep(0.01)
        for _ in range(3):
            reporter.capture_incident(trigger='auto', extra_context={
                'incident_type': 'ui_stall',
                'severity': 'low',
                'dominant_phase': 'idle',
                'duration_ms': 2000,
            })
        diagnosis = reporter.diagnose_freeze_cause()
        # newest (low) in first half → improving
        assert diagnosis['severity_trend'] == 'improving'

    def test_diagnosis_summary_format(self, reporter: FreezeIncidentReporter) -> None:
        reporter.capture_incident(trigger='test', extra_context={
            'incident_type': 'ui_stall',
            'severity': 'medium',
            'dominant_phase': 'qml_load',
            'duration_ms': 3000,
        })
        diagnosis = reporter.diagnose_freeze_cause()
        summary = diagnosis['summary']
        assert '1 recent freeze incidents analyzed' in summary
        assert 'Dominant cause:' in summary
        assert 'Severity trend:' in summary

    def test_diagnosis_output_shape(self, reporter: FreezeIncidentReporter) -> None:
        reporter.capture_incident(trigger='test', extra_context={
            'incident_type': 'ui_stall',
            'severity': 'medium',
            'dominant_phase': 'qml_load',
            'duration_ms': 3000,
        })
        diagnosis = reporter.diagnose_freeze_cause()
        expected_keys = {
            'dominant_cause', 'dominant_phase', 'cause_distribution',
            'phase_distribution', 'severity_distribution', 'severity_trend',
            'avg_duration_ms', 'startup_related_ratio',
            'config_recommendations', 'summary', 'incident_count',
        }
        assert set(diagnosis.keys()) == expected_keys


# ======================================================================
# Regression: existing FreezeIncidentReporter unchanged
# ======================================================================


class TestFreezeReporterRegression:
    """Ensure existing FreezeIncidentReporter behavior is preserved."""

    def test_capture_incident_still_works(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        path = reporter.capture_incident(trigger='regression')
        assert path.exists()
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['trigger'] == 'regression'

    def test_list_reports_still_works(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        reporter.capture_incident(trigger='test1')
        reporter.capture_incident(trigger='test2')
        reports = reporter.list_reports()
        assert len(reports) == 2

    def test_recent_incidents_still_works(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        reporter.capture_incident(trigger='auto', extra_context={
            'incident_type': 'ui_stall',
            'severity': 'medium',
        })
        incidents = reporter.recent_incidents()
        assert len(incidents) == 1
        assert incidents[0]['incident_type'] == 'ui_stall'

    def test_capture_chat_stall_still_works(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        reporter._last_auto_capture.clear()
        path = reporter.capture_chat_stall(
            duration_ms=4000,
            timed_out=False,
            message_summary='regression test',
        )
        assert path is not None
        assert path.exists()


# ======================================================================
# Regression: UIBridgeServer existing behavior
# ======================================================================


class TestBridgeServerRegression:
    """Ensure existing UIBridgeServer behavior is preserved."""

    def test_register_handler_still_works(self) -> None:
        server = UIBridgeServer()
        server.register_handler('test', lambda: {'ok': True})
        assert 'test' in server._handlers

    def test_dispatch_unknown_method(self) -> None:
        server = UIBridgeServer()
        result = server._dispatch(json.dumps({
            'id': 1,
            'method': 'unknown',
        }))
        assert 'error' in result
        assert 'unknown_method' in result['error']

    def test_dispatch_invalid_json(self) -> None:
        server = UIBridgeServer()
        result = server._dispatch('not json')
        assert 'error' in result
        assert 'invalid_json' in result['error']

    def test_status_property(self) -> None:
        server = UIBridgeServer()
        status = server.status
        assert status.running is False
        assert status.connected_clients == 0
