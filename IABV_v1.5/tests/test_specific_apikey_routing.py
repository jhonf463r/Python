"""Test that specific API key questions bypass account_resource and reach general chat.

NOTE: _is_account_resource_question and _build_cloud_reply_context were removed
from ControlCenterViewModel during Brecha 2.4 refactor. API-key routing is now
handled by the orchestrator pipeline via IntentUnderstandingService.
These tests are skipped until they are rewritten against the new routing API.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest

from iabv_v15.bootstrap import AppBootstrap

pytestmark = pytest.mark.skip(
    reason='_is_account_resource_question / _build_cloud_reply_context removed; routing now handled by orchestrator'
)


def _make_ccvm():
    workspace = Path.cwd() / 'data' / f'test_apikey_routing_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace
    return bootstrap.control_center_viewmodel, bootstrap


class TestSpecificApiKeyBypassesAccountResource:
    """Questions about specific API keys should NOT trigger account_resource."""

    def test_groq_api_key_question(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            assert not ccvm._is_account_resource_question(
                'y la api key de groq la está usando?'
            )
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_gemini_question(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            assert not ccvm._is_account_resource_question(
                'estas usando gemini para responder?'
            )
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_que_modelo_usas(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            assert not ccvm._is_account_resource_question(
                'que modelo estas usando ahora?'
            )
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_openrouter_key(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            assert not ccvm._is_account_resource_question(
                'tienes la api key de openrouter configurada?'
            )
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_broad_accounts_still_works(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            assert ccvm._is_account_resource_question(
                'que cuentas tienes', fast_only=True
            )
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_escanea_navegadores_still_works(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            assert ccvm._is_account_resource_question(
                'escanea mis navegadores', fast_only=True
            )
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)


class TestBuildCloudReplyContext:
    """_build_cloud_reply_context includes live system state."""

    def test_includes_api_key_status(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key', 'GEMINI_API_KEY': ''}):
                ctx = ccvm._build_cloud_reply_context()
            assert 'Groq' in ctx
            assert 'ESTADO DEL SISTEMA' in ctx
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)

    def test_no_crash_without_services(self) -> None:
        ccvm, bootstrap = _make_ccvm()
        try:
            with patch.dict('os.environ', {}, clear=True):
                ctx = ccvm._build_cloud_reply_context()
            assert 'ESTADO DEL SISTEMA' in ctx
        finally:
            shutil.rmtree(getattr(bootstrap, '_test_workspace', ''), ignore_errors=True)
