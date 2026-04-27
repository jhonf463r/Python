"""Test _try_cloud_quick_reply — cloud-first fallback for general chat."""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest

from iabv_v15.bootstrap import AppBootstrap


def _make_ccvm():
    """Create a ControlCenterViewModel via bootstrap."""
    workspace = Path.cwd() / 'data' / f'test_cloud_quick_reply_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace
    return bootstrap.control_center_viewmodel, bootstrap


class TestTryCloudQuickReply:

    def test_returns_none_when_no_keys(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            with patch.dict('os.environ', {}, clear=True):
                result = ccvm._try_cloud_quick_reply('hola como estas')
            assert result is None
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_returns_cloud_response_when_key_available(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Hola, estoy bien, gracias.'}}],
            }
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response

            with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key-123'}):
                with patch('httpx.Client', return_value=mock_client):
                    result = ccvm._try_cloud_quick_reply('que hora es?')
            assert result is not None
            assert len(result) > 10
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_falls_through_on_error(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = Exception('connection refused')

            with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
                with patch('httpx.Client', return_value=mock_client):
                    result = ccvm._try_cloud_quick_reply('hola')
            assert result is None
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_tries_next_provider_on_failure(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            call_count = {'n': 0}

            class FakeClient:
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    return False
                def post(self, url, **kw):
                    call_count['n'] += 1
                    if call_count['n'] == 1:
                        raise Exception('groq down')
                    resp = MagicMock()
                    resp.status_code = 200
                    resp.json.return_value = {
                        'choices': [{'message': {'content': 'Respuesta de gemini test provider fallback'}}],
                    }
                    return resp

            with patch.dict('os.environ', {'GROQ_API_KEY': 'k1', 'GEMINI_API_KEY': 'k2'}):
                with patch('httpx.Client', return_value=FakeClient()):
                    result = ccvm._try_cloud_quick_reply('test')
            assert result is not None
            assert len(result) > 10
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)
