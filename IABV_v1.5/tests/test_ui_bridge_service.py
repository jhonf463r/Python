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
        server.start()
        try:
            client = UIBridgeClient(port=port)
            result = client.call('send_message', text='')
            assert result.get('result', {}).get('status') == 'error'
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
        assert result['status'] in ('installing_background', 'already_installing')
        assert result['tool_id'] == 'aider_coder'
