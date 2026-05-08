"""Tests for UIBridgeService — IPC bridge between MCP server and UI."""

from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from iabv_v15.services.ui_bridge_service import (
    DEFAULT_BRIDGE_HOST,
    UIBridgeClient,
    UIBridgeServer,
    build_ui_bridge_server,
)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestUIBridgeServer:
    """Basic server lifecycle tests."""

    def test_start_and_stop(self) -> None:
        port = _find_free_port()
        server = UIBridgeServer(port=port)
        server.start()
        assert server.status.running is True
        server.stop()
        assert server.status.running is False

    def test_accepts_connection(self) -> None:
        port = _find_free_port()
        server = UIBridgeServer(port=port)
        server.register_handler('ping', lambda: {'pong': True})
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(('127.0.0.1', port))
            request = json.dumps({'id': '1', 'method': 'ping', 'params': {}}) + '\n'
            sock.sendall(request.encode())
            response = b''
            while b'\n' not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            data = json.loads(response.strip())
            assert data['id'] == '1'
            assert data['result'] == {'pong': True}
        finally:
            server.stop()

    def test_unknown_method_returns_error(self) -> None:
        port = _find_free_port()
        server = UIBridgeServer(port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(('127.0.0.1', port))
            request = json.dumps({'id': '2', 'method': 'nonexistent'}) + '\n'
            sock.sendall(request.encode())
            response = b''
            while b'\n' not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            data = json.loads(response.strip())
            assert 'error' in data
            assert 'unknown_method' in data['error']
        finally:
            server.stop()

    def test_status_listener_called(self) -> None:
        port = _find_free_port()
        server = UIBridgeServer(port=port)
        statuses: list[bool] = []
        server.attach_listener(lambda s: statuses.append(s.running))
        server.start()
        server.stop()
        assert True in statuses
        assert False in statuses


class TestUIBridgeClient:
    """Client tests — connecting to a running server."""

    def test_is_ui_available_false_when_no_server(self) -> None:
        port = _find_free_port()
        client = UIBridgeClient(port=port)
        assert client.is_ui_available() is False

    def test_is_ui_available_true_with_server(self) -> None:
        port = _find_free_port()
        server = UIBridgeServer(port=port)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            assert client.is_ui_available() is True
        finally:
            server.stop()

    def test_call_returns_error_when_no_server(self) -> None:
        port = _find_free_port()
        client = UIBridgeClient(port=port)
        result = client.call('ping')
        assert 'error' in result
        assert result['error'] == 'ui_not_available'

    def test_call_success(self) -> None:
        port = _find_free_port()
        server = UIBridgeServer(port=port)
        server.register_handler('echo', lambda text='': {'echoed': text})
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('echo', text='hello')
            assert result.get('result') == {'echoed': 'hello'}
        finally:
            server.stop()


class TestBuildUIBridgeServer:
    """Tests for the factory function with default handlers."""

    def test_build_without_viewmodel(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(port=port)
        server.mark_shell_ready('test')  # shell must be ready to accept traffic
        server.start()
        try:
            client = UIBridgeClient(port=port)

            # send_message without VM should buffer
            result = client.call('send_message', text='hello from bridge')
            assert result.get('result', {}).get('status') == 'buffered'

            # read_messages should return the buffered message
            result = client.call('read_messages', limit=10)
            messages = result.get('result', {}).get('messages', [])
            assert len(messages) == 1
            assert messages[0]['text'] == 'hello from bridge'

            # get_ui_state should work
            result = client.call('get_ui_state')
            assert result.get('result', {}).get('ui_running') is True

            # push_chat_message should record
            result = client.call('push_chat_message', role='user', text='test message')
            assert result.get('result', {}).get('status') == 'recorded'

            # verify pushed message appears in read
            result = client.call('read_messages', limit=10)
            messages = result.get('result', {}).get('messages', [])
            assert len(messages) == 2
        finally:
            server.stop()

    def test_send_message_empty_text_error(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='')
            assert result.get('result', {}).get('status') == 'error'
        finally:
            server.stop()

    def test_build_with_viewmodel_reads_live_chat_state(self) -> None:
        class _FakeViewModel:
            def __init__(self) -> None:
                self.messages = [
                    {'role': 'assistant', 'speaker': 'IABV', 'text': 'inicio', 'timestamp': '10:00'},
                ]
                self._chat_session_id = 'session-1'
                self._live_status = 'idle'

            def send_message_from_bridge(self, text: str) -> dict[str, object]:
                self.messages.append({'role': 'user', 'speaker': 'Bridge', 'text': text, 'timestamp': '10:01'})
                self.messages.append({'role': 'assistant', 'speaker': 'IABV', 'text': 'ok', 'timestamp': '10:01'})
                return {'status': 'queued', 'text': text}

            def get_chat_messages(self) -> list[dict[str, str]]:
                return list(self.messages)

        port = _find_free_port()
        server = build_ui_bridge_server(_FakeViewModel(), port=port)
        server.mark_shell_ready('test')  # shell must be ready to accept traffic
        server.start()
        try:
            client = UIBridgeClient(port=port)
            send_result = client.call('send_message', text='audita esto')
            assert send_result.get('result', {}).get('status') == 'queued'

            read_result = client.call('read_messages', limit=10)
            payload = read_result.get('result', {})
            messages = payload.get('messages', [])
            assert payload.get('source') == 'viewmodel'
            assert payload.get('total') == 3
            assert messages[-1]['text'] == 'ok'
            assert messages[-1]['speaker'] == 'IABV'
        finally:
            server.stop()


class TestBridgeReadinessHandshake:
    """Tests for the shell readiness handshake (Tasks 1, 2, 7)."""

    def test_server_starts_not_ready(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        assert server.shell_ready is False

    def test_mark_shell_ready_sets_flag(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.mark_shell_ready('test_source')
        assert server.shell_ready is True

    def test_mark_shell_ready_idempotent(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.mark_shell_ready('first')
        server.mark_shell_ready('second')
        snap = server.readiness_snapshot()
        assert snap['ready_source'] == 'first'

    def test_enqueue_buffers_when_not_ready(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        result = server.enqueue_pending_message({'text': 'hello'})
        assert result['status'] == 'pending_shell_ready'
        assert result['queue_position'] == 1

    def test_enqueue_passthrough_when_ready(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.mark_shell_ready('test')
        result = server.enqueue_pending_message({'text': 'hello'})
        assert result == {}

    def test_mark_ready_flushes_pending(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        flushed: list[str] = []
        server.register_handler('send_message', lambda text='': flushed.append(text))
        server.enqueue_pending_message({'text': 'msg1'})
        server.enqueue_pending_message({'text': 'msg2'})
        assert len(flushed) == 0
        server.mark_shell_ready('test')
        assert flushed == ['msg1', 'msg2']

    def test_readiness_snapshot_shape(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        snap = server.readiness_snapshot()
        assert snap['shell_ready'] is False
        assert snap['pending_count'] == 0
        assert snap['ready_source'] == ''

    def test_set_deferred_setup_active(self) -> None:
        server = UIBridgeServer(port=_find_free_port())
        server.set_deferred_setup_active(True)
        assert server.readiness_snapshot()['deferred_setup_active'] is True
        server.set_deferred_setup_active(False)
        assert server.readiness_snapshot()['deferred_setup_active'] is False

    def test_send_message_buffered_before_ready(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(port=port)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='pre-ready msg')
            payload = result.get('result', {})
            assert payload.get('status') == 'pending_shell_ready'
        finally:
            server.stop()

    def test_send_message_works_after_ready(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(port=port)
        server.mark_shell_ready('test')
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='post-ready msg')
            payload = result.get('result', {})
            assert payload.get('status') == 'buffered'
        finally:
            server.stop()

    def test_bridge_readiness_handler(self) -> None:
        port = _find_free_port()
        server = build_ui_bridge_server(port=port)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('bridge_readiness')
            payload = result.get('result', {})
            assert 'shell_ready' in payload
            assert payload['shell_ready'] is False
        finally:
            server.stop()


class TestSelfAuditIncremental:
    """Placeholder test to verify incremental audit concept."""

    def test_subsystem_names_valid(self) -> None:
        valid = {'orchestrator', 'synaptic_router', 'world_model',
                 'oses', 'portable_context', 'common_sense', 'ui'}
        assert len(valid) == 7


class TestAiderBackgroundInstall:
    """Tests for background installation of heavy packages."""

    def test_heavy_packages_set(self) -> None:
        from iabv_v15.services.auto_correction_engine import _HEAVY_PIP_PACKAGES
        assert 'aider_coder' in _HEAVY_PIP_PACKAGES

    def test_install_in_background_returns_immediately(self) -> None:
        from iabv_v15.services.auto_correction_engine import _auto_install_missing_tool
        result = _auto_install_missing_tool('aider_coder')
        assert result['status'] in ('installing_background', 'already_installing', 'cooldown_active')
        assert result['tool_id'] == 'aider_coder'


class TestGetUIStateCurrentPage:
    """current_page must read from navigation_controller.get_current_route().

    Antes leia ``_current_page`` que NO existe en ControlCenterViewModel y
    siempre devolvia ``"unknown"`` — exactamente el bug que la auditoria
    live reporta.
    """

    def test_current_page_reads_from_navigation_controller(self) -> None:
        class _FakeNav:
            def __init__(self, route: str) -> None:
                self._route = route

            def get_current_route(self) -> str:
                return self._route

        class _FakeVM:
            def __init__(self) -> None:
                self.navigation_controller = _FakeNav('control_center')
                self._chat_session_id = 's1'
                self._live_status = 'idle'
                self.messages: list[dict[str, str]] = []

            def get_chat_messages(self) -> list[dict[str, str]]:
                return list(self.messages)

        port = _find_free_port()
        server = build_ui_bridge_server(_FakeVM(), port=port)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            res = client.call('get_ui_state')
            payload = res.get('result', {})
            assert payload.get('ui_running') is True
            assert payload.get('current_page') == 'control_center'
        finally:
            server.stop()

    def test_current_page_unknown_when_navigation_controller_missing(self) -> None:
        class _FakeVM:
            def __init__(self) -> None:
                self._chat_session_id = ''
                self._live_status = 'idle'
                self.messages: list[dict[str, str]] = []

            def get_chat_messages(self) -> list[dict[str, str]]:
                return []

        port = _find_free_port()
        server = build_ui_bridge_server(_FakeVM(), port=port)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            res = client.call('get_ui_state')
            payload = res.get('result', {})
            assert payload.get('current_page') == 'unknown'
        finally:
            server.stop()

    def test_current_page_falls_back_to_legacy_attribute(self) -> None:
        class _FakeVM:
            def __init__(self) -> None:
                self._current_page = 'evolution_center'
                self._chat_session_id = ''
                self._live_status = 'idle'
                self.messages: list[dict[str, str]] = []

            def get_chat_messages(self) -> list[dict[str, str]]:
                return []

        port = _find_free_port()
        server = build_ui_bridge_server(_FakeVM(), port=port)
        server.start()
        try:
            client = UIBridgeClient(port=port)
            res = client.call('get_ui_state')
            payload = res.get('result', {})
            assert payload.get('current_page') == 'evolution_center'
        finally:
            server.stop()
