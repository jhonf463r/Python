"""P0.71: Live UI Presence Contract + UIBridge Truthfulness tests.

Covers:
- UIBridge send_message fails-closed if no ControlCenterViewModel bound
- UIBridge navigate verifies route changed
- get_ui_state exposes control_vm_bound / chat_ready
- Port conflict detection prevents duplicate UIBridgeServer
- FreezeIncidentReporter captures bridge/control VM state
- OSES _ui_bridge_truth_findings detects 4 patterns
- mark_control_vm_bound signals chat_ready correctly
- duplicate bridge port is rejected or marked conflict
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from iabv_v15.services.ui_bridge_service import (
    UIBridgeClient,
    UIBridgeServer,
    UIBridgeStatus,
    build_ui_bridge_server,
)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------
# Fake VMs for testing
# ---------------------------------------------------------------

class _FakeNavController:
    def __init__(self, route: str = 'dashboard') -> None:
        self._route = route

    def get_current_route(self) -> str:
        return self._route

    def navigate_to(self, page: str) -> None:
        self._route = page


class _FakeViewModel:
    def __init__(self, nav_route: str = 'dashboard') -> None:
        self.navigation_controller = _FakeNavController(nav_route)
        self._chat_session_id = 'test-session'
        self._live_status = 'idle'
        self.messages: list[dict[str, str]] = []
        self.sent: list[str] = []

    def send_message_from_bridge(self, text: str) -> dict[str, object]:
        self.sent.append(text)
        return {'status': 'queued', 'text': text}

    def get_chat_messages(self) -> list[dict[str, str]]:
        return list(self.messages)


# ---------------------------------------------------------------
# Task C: UIBridge Truth Contract
# ---------------------------------------------------------------

class TestUIBridgeSendMessageFailClosed:
    """send_message must return status=unavailable when no VM is bound."""

    def test_send_message_fails_if_no_controlcentervm(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='¿por dónde vamos?')
            payload = result.get('result', {})
            assert payload.get('status') == 'unavailable'
            assert payload.get('reason') == 'control_center_vm_not_bound'
        finally:
            server.stop()

    def test_send_message_succeeds_with_vm(self) -> None:
        vm = _FakeViewModel()
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='hello')
            payload = result.get('result', {})
            assert payload.get('status') == 'queued'
            assert 'hello' in vm.sent
        finally:
            server.stop()


class TestUIBridgeNavigateVerifiesRoute:
    """navigate must verify route actually changed."""

    def test_navigate_verifies_route_changed(self) -> None:
        vm = _FakeViewModel(nav_route='dashboard')
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            payload = result.get('result', {})
            assert payload.get('status') == 'navigated'
            assert payload.get('verified') is True
        finally:
            server.stop()

    def test_navigate_fails_when_route_unchanged(self) -> None:
        """If navigation_controller doesn't change route, return failed."""
        class _StuckNav:
            def get_current_route(self) -> str:
                return 'dashboard'
            def navigate_to(self, page: str) -> None:
                pass  # does not change route

        class _StuckVM:
            def __init__(self) -> None:
                self.navigation_controller = _StuckNav()
                self._chat_session_id = ''
                self._live_status = 'idle'
            def get_chat_messages(self) -> list[dict[str, str]]:
                return []

        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=_StuckVM(), port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            payload = result.get('result', {})
            assert payload.get('status') == 'failed'
        finally:
            server.stop()

    def test_navigate_unavailable_without_vm(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            payload = result.get('result', {})
            assert payload.get('status') == 'unavailable'
            assert payload.get('reason') == 'control_center_vm_not_bound'
        finally:
            server.stop()


class TestGetUIStateExposesP071Fields:
    """get_ui_state must expose control_vm_bound / chat_ready / pids."""

    def test_get_ui_state_exposes_control_vm_bound_chat_ready(self) -> None:
        vm = _FakeViewModel()
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        # Re-signal VM bound after shell is ready (mirrors real bootstrap order)
        server.mark_control_vm_bound(True)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('get_ui_state')
            payload = result.get('result', {})
            assert payload.get('control_vm_bound') is True
            assert payload.get('chat_ready') is True
            assert payload.get('ui_process_pid', 0) > 0
            assert payload.get('bridge_owner_pid', 0) > 0
            assert payload.get('navigation_controller_bound') is True
            assert payload.get('current_page_verified') is True
        finally:
            server.stop()

    def test_get_ui_state_no_vm_shows_unbound(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('get_ui_state')
            payload = result.get('result', {})
            assert payload.get('control_vm_bound') is False
            assert payload.get('chat_ready') is False
        finally:
            server.stop()


# ---------------------------------------------------------------
# Task B: Port conflict / duplicate bridge
# ---------------------------------------------------------------

class TestDuplicateBridgePortRejected:
    """Starting a second server on the same port must be rejected."""

    def test_duplicate_bridge_port_rejected_or_marked_conflict(self) -> None:
        port = _find_free_port()
        server1 = UIBridgeServer(port=port)
        server1.start()
        assert server1.status.running is True
        try:
            server2 = UIBridgeServer(port=port)
            server2.start()
            # server2 must NOT be running due to port conflict
            assert server2.status.running is False
            assert server2.status.last_error != ''
        finally:
            server1.stop()


class TestMarkControlVMBound:
    """mark_control_vm_bound must update chat_ready based on shell readiness."""

    def test_mark_bound_without_shell_ready(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.mark_control_vm_bound(True)
        assert server.status.control_vm_bound is True
        assert server.status.chat_ready is False  # shell not ready yet

    def test_mark_bound_with_shell_ready(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.mark_shell_ready('test')
        server.mark_control_vm_bound(True)
        assert server.status.control_vm_bound is True
        assert server.status.chat_ready is True

    def test_unbind_clears_chat_ready(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.mark_shell_ready('test')
        server.mark_control_vm_bound(True)
        assert server.status.chat_ready is True
        server.mark_control_vm_bound(False)
        assert server.status.chat_ready is False


# ---------------------------------------------------------------
# Task E: FreezeIncidentReporter captures bridge state
# ---------------------------------------------------------------

class TestFreezeReportIncludesBridgeState:
    """_capture_ui_bridge_state must capture bridge/VM info."""

    def test_capture_ui_bridge_state_returns_dict(self) -> None:
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            FreezeIncidentReporter,
        )
        state = FreezeIncidentReporter._capture_ui_bridge_state()
        assert isinstance(state, dict)
        assert 'available' in state
        assert 'unresolved_fields' in state

    def test_capture_bridge_unavailable_marks_unresolved(self) -> None:
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            FreezeIncidentReporter,
        )
        # No bridge server running → should mark unavailable
        state = FreezeIncidentReporter._capture_ui_bridge_state()
        assert state['available'] is False
        assert 'ui_bridge_not_reachable' in state['unresolved_fields']


# ---------------------------------------------------------------
# Task E: OSES _ui_bridge_truth_findings
# ---------------------------------------------------------------

class TestOSESUIBridgeTruthFindings:
    """OSES findings for bridge truthfulness patterns."""

    def _write_audit_events(self, tmp_dir: str, events: list[dict]) -> None:
        logs_dir = Path(tmp_dir) / 'data' / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        with (logs_dir / 'runtime_audit.jsonl').open('w') as fh:
            for ev in events:
                fh.write(json.dumps(ev) + '\n')

    def _make_oses(self, workspace: str) -> object:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        svc.workspace_root = workspace
        return svc

    def test_bridge_claimed_ready_but_no_vm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit_events(tmp, [
                {'kind': 'ui_bridge_send_unavailable', 'data': {
                    'reason': 'control_center_vm_not_bound',
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._ui_bridge_truth_findings()
            cats = [f.category for f in findings]
            assert 'bridge_claimed_ready_but_no_vm' in cats

    def test_local_chat_slow_after_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit_events(tmp, [
                {'kind': 'dispatch_terminal', 'data': {
                    'provider': 'local',
                    'duration_ms': 112650,
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._ui_bridge_truth_findings()
            cats = [f.category for f in findings]
            assert 'local_chat_slow_after_continuity' in cats

    def test_ui_stall_without_causal_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit_events(tmp, [
                {'kind': 'freeze_incident', 'data': {
                    'cause': 'event_loop_blocked_unknown',
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._ui_bridge_truth_findings()
            cats = [f.category for f in findings]
            assert 'ui_stall_without_causal_phase' in cats

    def test_duplicate_ui_bridge_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit_events(tmp, [
                {'kind': 'ui_bridge_trace', 'data': {
                    'event': 'ui_bridge_port_conflict',
                    'owner_pid': 12345,
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._ui_bridge_truth_findings()
            cats = [f.category for f in findings]
            assert 'duplicate_ui_bridge_owner' in cats

    def test_no_findings_on_clean_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit_events(tmp, [
                {'kind': 'dispatch_terminal', 'data': {
                    'provider': 'local', 'duration_ms': 200,
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._ui_bridge_truth_findings()
            assert len(findings) == 0

    def test_no_crash_without_audit_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            svc = self._make_oses(tmp)
            findings = svc._ui_bridge_truth_findings()
            assert findings == []

    def test_no_crash_without_workspace(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        findings = svc._ui_bridge_truth_findings()
        assert findings == []


# ---------------------------------------------------------------
# Task D: Human-Simulated Chat Audit (code-level simulation)
# ---------------------------------------------------------------

class TestHumanSimulatedChatAudit:
    """Simulate human chat flow through the UIBridge.

    Verifies: bridge→VM message delivery, navigation works,
    no hang, no stall >5s, chat_ready=true after bootstrap.
    Live Windows proof remains UNRESOLVED.
    """

    def test_bridge_delivers_messages_to_vm(self) -> None:
        """Simulate: user sends 3 messages through bridge → VM receives all."""
        vm = _FakeViewModel()
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.mark_control_vm_bound(True)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            phrases = [
                '¿por dónde vamos?',
                '¿me entiendes y qué evidencia tienes?',
                'sigue',
            ]
            for phrase in phrases:
                t0 = time.time()
                result = client.call('send_message', text=phrase)
                elapsed = time.time() - t0
                payload = result.get('result', {})
                assert payload.get('status') == 'queued', (
                    f'Expected queued for "{phrase}", got {payload}'
                )
                assert elapsed < 5.0, f'Stall >5s for "{phrase}": {elapsed:.1f}s'
            assert vm.sent == phrases
        finally:
            server.stop()

    def test_bridge_navigate_to_control_then_verify(self) -> None:
        """Simulate: navigate to 'control' and verify route changed."""
        vm = _FakeViewModel(nav_route='dashboard')
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            payload = result.get('result', {})
            assert payload.get('verified') is True
        finally:
            server.stop()

    def test_bridge_chat_ready_after_bootstrap(self) -> None:
        """After full bootstrap (VM bound + shell ready), chat_ready=true."""
        vm = _FakeViewModel()
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.mark_control_vm_bound(True)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('get_ui_state')
            payload = result.get('result', {})
            assert payload.get('chat_ready') is True
            assert payload.get('control_vm_bound') is True
        finally:
            server.stop()

    def test_no_message_buffered_without_vm(self) -> None:
        """Without VM, messages must NOT be silently buffered."""
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='sigue')
            payload = result.get('result', {})
            assert payload.get('status') == 'unavailable'
            assert 'control_center_vm_not_bound' in payload.get('reason', '')
        finally:
            server.stop()
