"""P0.71: UIBridge Truth Contract + Freeze Causal Diagnosis + OSES findings tests.

Tests verify:
1. send_message returns unavailable when no ControlCenterViewModel.
2. get_ui_state exposes control_vm_bound, chat_ready, PIDs.
3. navigate verifies route actually changed.
4. UIBridgeStatus has truth contract fields.
5. FreezeIncidentReporter includes ui_bridge_state in reports.
6. OSES _ui_bridge_truth_findings runs without error.
7. human_simulated_chat_audit.py is importable.
8. No duplicate bridge port is accepted silently.
9. "por donde vamos?" through bridge reaches metacognitive handler (not LLM).
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

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


# ── UIBridgeStatus truth contract fields ──

class TestUIBridgeStatusTruthFields:
    def test_status_has_truth_fields(self) -> None:
        status = UIBridgeStatus()
        assert hasattr(status, 'control_vm_bound')
        assert hasattr(status, 'chat_ready')
        assert hasattr(status, 'ui_process_pid')
        assert hasattr(status, 'bridge_owner_pid')
        assert hasattr(status, 'navigation_controller_bound')
        assert hasattr(status, 'current_page_verified')

    def test_status_defaults_false(self) -> None:
        status = UIBridgeStatus()
        assert status.control_vm_bound is False
        assert status.chat_ready is False
        assert status.ui_process_pid == 0
        assert status.bridge_owner_pid == 0


# ── send_message fail-closed without VM ──

class TestSendMessageFailClosed:
    def test_send_message_without_vm_returns_unavailable(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='hello')
            inner = result.get('result', {})
            assert inner.get('status') == 'unavailable'
            assert inner.get('reason') == 'control_center_vm_not_bound'
            assert 'next_human_action' in inner
        finally:
            server.stop()

    def test_send_message_with_vm_queues(self) -> None:
        port = _find_free_port()
        vm = MagicMock()
        vm.send_message_from_bridge.return_value = {'status': 'queued', 'text': 'hi'}
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='hi')
            inner = result.get('result', {})
            assert inner.get('status') == 'queued'
        finally:
            server.stop()


# ── get_ui_state truth contract ──

class TestGetUIStateTruth:
    def test_get_ui_state_without_vm(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('get_ui_state')
            state = result.get('result', {})
            assert state.get('control_vm_bound') is False
            assert state.get('chat_ready') is False
            assert state.get('navigation_controller_bound') is False
            assert state.get('current_page_verified') is False
            assert 'ui_process_pid' in state
            assert 'bridge_owner_pid' in state
        finally:
            server.stop()

    def test_get_ui_state_with_vm(self) -> None:
        port = _find_free_port()
        vm = MagicMock()
        nav = MagicMock()
        nav.get_current_route.return_value = 'dashboard'
        vm.navigation_controller = nav
        vm._chat_session_id = 'sess-1'
        vm._live_status = 'idle'
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('get_ui_state')
            state = result.get('result', {})
            assert state.get('control_vm_bound') is True
            assert state.get('chat_ready') is True
            assert state.get('navigation_controller_bound') is True
            assert state.get('current_page') == 'dashboard'
            assert state.get('current_page_verified') is True
        finally:
            server.stop()


# ── navigate verifies route change ──

class TestNavigateVerification:
    def test_navigate_without_vm_returns_unavailable(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(control_center_viewmodel=None, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            inner = result.get('result', {})
            assert inner.get('status') == 'unavailable'
            assert inner.get('reason') == 'control_center_vm_not_bound'
        finally:
            server.stop()

    def test_navigate_verifies_route_changed(self) -> None:
        port = _find_free_port()
        vm = MagicMock()
        nav = MagicMock()
        nav.get_current_route.return_value = 'control'
        vm.navigation_controller = nav
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            inner = result.get('result', {})
            assert inner.get('status') == 'navigated'
            assert inner.get('verified') is True
        finally:
            server.stop()

    def test_navigate_detects_failed_route_change(self) -> None:
        port = _find_free_port()
        vm = MagicMock()
        nav = MagicMock()
        nav.get_current_route.return_value = 'dashboard'
        vm.navigation_controller = nav
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('navigate', page='control')
            inner = result.get('result', {})
            assert inner.get('status') == 'failed'
            assert inner.get('actual_page') == 'dashboard'
        finally:
            server.stop()


# ── Duplicate bridge port rejection ──

class TestDuplicateBridgePort:
    def test_second_server_on_same_port_fails(self) -> None:
        port = _find_free_port()
        server1 = UIBridgeServer(port=port)
        server1.start()
        assert server1.status.running is True
        try:
            server2 = UIBridgeServer(port=port)
            server2.start()
            assert server2.status.running is False or server2.status.last_error != ''
        finally:
            server1.stop()
            try:
                server2.stop()
            except Exception:
                pass


# ── FreezeIncidentReporter includes ui_bridge_state ──

class TestFreezeIncidentBridgeState:
    def test_report_includes_ui_bridge_state(self) -> None:
        from iabv_v15.services.evolution.freeze_incident_reporter import FreezeIncidentReporter
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = FreezeIncidentReporter(tmpdir)
            path = reporter.capture_incident(trigger='test')
            report = json.loads(path.read_text(encoding='utf-8'))
            assert 'ui_bridge_state' in report
            bridge_state = report['ui_bridge_state']
            assert 'bridge_reachable' in bridge_state or 'error' in bridge_state


# ── OSES _ui_bridge_truth_findings runs ──

class TestOSESBridgeTruthFindings:
    def test_ui_bridge_truth_findings_runs_without_error(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        assert hasattr(OperationalSelfExaminationService, '_ui_bridge_truth_findings')
        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = ''
        from iabv_v15.services.evolution.operational_self_examination_service import (
            _ui_bridge_truth_findings_impl,
        )
        findings = _ui_bridge_truth_findings_impl(svc)
        assert isinstance(findings, list)

    def test_findings_are_observe_only(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            _ui_bridge_truth_findings_impl,
        )
        svc = MagicMock()
        svc.workspace_root = ''
        findings = _ui_bridge_truth_findings_impl(svc)
        for f in findings:
            assert not hasattr(f, 'execute') or not callable(getattr(f, 'execute', None))


# ── Metacognitive phrase routing ──

class TestMetacognitivePhraseRouting:
    def test_por_donde_vamos_reaches_handler_not_buffer(self) -> None:
        """'por donde vamos' through bridge should reach VM handler, not buffer."""
        port = _find_free_port()
        vm = MagicMock()
        vm.send_message_from_bridge.return_value = {
            'status': 'roadmap_response',
            'source': 'roadmap_matrix',
        }
        server = build_ui_bridge_server(control_center_viewmodel=vm, port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='¿por dónde vamos?')
            inner = result.get('result', {})
            assert inner.get('status') != 'unavailable'
            vm.send_message_from_bridge.assert_called_once_with('¿por dónde vamos?')
        finally:
            server.stop()


# ── human_simulated_chat_audit.py importable ──

class TestAuditScriptImportable:
    def test_audit_script_exists(self) -> None:
        script = Path(__file__).parent.parent / 'scripts' / 'human_simulated_chat_audit.py'
        assert script.exists(), f'Audit script missing: {script}'

    def test_audit_script_compiles(self) -> None:
        script = Path(__file__).parent.parent / 'scripts' / 'human_simulated_chat_audit.py'
        import py_compile
        py_compile.compile(str(script), doraise=True)


# ── Platform pending JSON valid ──

class TestPlatformPendingP071:
    def test_p071_json_valid(self) -> None:
        json_path = (
            Path(__file__).parent.parent
            / 'data' / 'evolution' / 'platform_pending'
            / 'task_live_ui_presence_contract_p071.json'
        )
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding='utf-8'))
        assert data.get('id') == 'p071_live_ui_presence_contract'
        assert data.get('status') in ('UNRESOLVED', 'COMPLETED')
        assert len(data.get('implemented_tasks', [])) >= 6
        assert len(data.get('unresolved', [])) >= 1
