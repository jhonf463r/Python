"""Tests focalizados para los helpers `_devin_create_session` y
`_devin_send_message` del wiring de bootstrap.

No corre `AppComposition` completo (requiere Qt + DB). Solo valida el
contrato de las funciones helper: graceful degradation cuando el adapter
no existe, cuando falta API key, y comportamiento feliz con una fake
respuesta HTTP (monkeypatch de `httpx.post`).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from iabv_v15 import bootstrap


class _FakeAdapter:
    """Adapter minimal compatible con `_devin_create_session` / `_devin_send_message`."""

    BASE_URL = "https://api.devin.ai/v1"

    def __init__(self, api_key: str = "cog_test"):
        self.api_key = api_key
        self._sessions_url = f"{self.BASE_URL}/sessions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


def _fake_response(status_code: int, body: dict | None = None, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        status_code=status_code,
        json=lambda: body or {},
        text=text,
    )


def test_create_session_returns_empty_when_adapter_is_none() -> None:
    assert bootstrap._devin_create_session(None, "hola") == ""


def test_create_session_returns_empty_when_api_key_missing() -> None:
    adapter = _FakeAdapter(api_key="")
    assert bootstrap._devin_create_session(adapter, "hola") == ""


def test_create_session_returns_session_id_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()
    calls: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _fake_response(201, {"session_id": "sess-123"})

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    sid = bootstrap._devin_create_session(adapter, "hola mundo")
    assert sid == "sess-123"
    assert calls[0]["url"] == "https://api.devin.ai/v1/sessions"
    assert calls[0]["json"] == {"prompt": "hola mundo"}
    assert calls[0]["headers"]["Authorization"] == "Bearer cog_test"


def test_create_session_fallback_to_id_field(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()

    def fake_post(url, headers=None, json=None, timeout=None):
        return _fake_response(200, {"id": "alt-456"})

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    assert bootstrap._devin_create_session(adapter, "x") == "alt-456"


def test_create_session_returns_empty_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()

    def fake_post(url, headers=None, json=None, timeout=None):
        return _fake_response(500, {}, text="boom")

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    assert bootstrap._devin_create_session(adapter, "x") == ""


def test_create_session_returns_empty_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()

    def fake_post(*_a, **_kw):
        raise RuntimeError("net down")

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    assert bootstrap._devin_create_session(adapter, "x") == ""


def test_send_message_returns_false_when_adapter_is_none() -> None:
    assert bootstrap._devin_send_message(None, "sess-1", "hi") is False


def test_send_message_returns_false_when_session_id_empty() -> None:
    adapter = _FakeAdapter()
    assert bootstrap._devin_send_message(adapter, "", "hi") is False


def test_send_message_returns_false_when_api_key_missing() -> None:
    adapter = _FakeAdapter(api_key="")
    assert bootstrap._devin_send_message(adapter, "sess-1", "hi") is False


def test_send_message_returns_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()
    calls: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        return _fake_response(200, {"ok": True})

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    ok = bootstrap._devin_send_message(adapter, "sess-xyz", "hola")
    assert ok is True
    assert calls[0]["url"] == "https://api.devin.ai/v1/session/sess-xyz/message"
    assert calls[0]["json"] == {"message": "hola"}


def test_send_message_returns_false_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()

    def fake_post(*_a, **_kw):
        return _fake_response(403, {}, text="nope")

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    assert bootstrap._devin_send_message(adapter, "sess-1", "x") is False


def test_send_message_returns_false_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _FakeAdapter()

    def fake_post(*_a, **_kw):
        raise RuntimeError("timeout")

    import httpx as _httpx

    monkeypatch.setattr(_httpx, "post", fake_post)
    assert bootstrap._devin_send_message(adapter, "sess-1", "x") is False
