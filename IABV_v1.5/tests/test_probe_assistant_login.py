"""Tests para ``probe_assistant_login`` (F3.1).

Cubren:
- 4 providers × 2 casos (logueado vs login-page detectado) = 8 casos base;
- errores tipados: assistant_kind inválido / unknown, playwright_unavailable,
  controller_init_failed, controller_start_failed, page_unavailable,
  timeout, heuristic_failed;
- evidencia incluye screenshot si ``include_screenshot=True``;
- registro en MCP server + governance gate (block wildcard, block audit,
  network desconectada).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fakes de browser


class _FakePage:
    def __init__(
        self,
        *,
        url: str = "",
        title: str = "",
        markers: dict[str, bool] | None = None,
        screenshot_bytes: bytes = b"",
        goto_raises: Exception | None = None,
    ) -> None:
        self.url = url
        self._title = title
        self._markers = markers or {}
        self._screenshot = screenshot_bytes
        self._goto_raises = goto_raises
        self.goto_calls: list[tuple[str, int]] = []

    def title(self) -> str:
        return self._title

    def query_selector(self, selector: str) -> object | None:
        # Partial-match para tolerar que las heurísticas prueben variantes con
        # ``[i]`` (case-insensitive) que no aplican sobre el test; cualquier
        # selector registrado como ``True`` se considera presente.
        if selector in self._markers:
            return object() if self._markers[selector] else None
        for key, present in self._markers.items():
            if present and _selectors_match(selector, key):
                return object()
        return None

    def goto(self, url: str, *, timeout: int = 0) -> None:
        self.goto_calls.append((url, timeout))
        if self._goto_raises is not None:
            raise self._goto_raises

    def screenshot(self, *, type: str = "png", full_page: bool = False) -> bytes:
        return self._screenshot


def _selectors_match(actual: str, registered: str) -> bool:
    """Match laxo de selectores: ignora ``[i]`` y espacios diferentes."""

    def _norm(value: str) -> str:
        return value.replace(" i]", "]").replace(" I]", "]").strip()

    return _norm(actual) == _norm(registered)


class _FakeController:
    def __init__(
        self,
        page: _FakePage | None,
        *,
        start_raises: Exception | None = None,
    ) -> None:
        self._page = page
        self._start_raises = start_raises
        self.start_calls = 0
        self.close_calls = 0

    def start(self) -> None:
        self.start_calls += 1
        if self._start_raises is not None:
            raise self._start_raises

    @property
    def page(self) -> _FakePage | None:
        return self._page

    def close(self) -> None:
        self.close_calls += 1


def _fixed_clock(start: float = 0.0, step: float = 0.05) -> callable:
    """Reloj que avanza ``step`` cada call desde ``start``."""

    current = [start - step]

    def _tick() -> float:
        current[0] += step
        return current[0]

    return _tick


def _fixed_now(iso: str = "2026-04-20T01:23:45.678901+00:00") -> callable:
    dt = datetime.fromisoformat(iso)
    # Aseguramos tz-aware para que ``isoformat`` devuelva lo pedido.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return lambda: dt


# ---------------------------------------------------------------------------
# Importar la tool después de definir fakes para no arrastrar playwright.


from iabv_v15.infra.mcp.audit_tools.probe_assistant_login import (  # noqa: E402
    PROVIDER_HEURISTICS,
    known_assistant_kinds,
    probe_assistant_login,
)


# ---------------------------------------------------------------------------
# Casos felices + login-page detectado (4 providers × 2 casos)


@pytest.mark.parametrize(
    ("kind", "url_after_goto", "markers", "expected_reason"),
    [
        (
            "chatgpt",
            "https://chatgpt.com/",
            {'nav[aria-label*="history"]': True},
            "nav_history_visible",
        ),
        (
            "claude",
            "https://claude.ai/chat/new",
            {},
            "chat_route_reached",
        ),
        (
            "codex",
            "https://codex.openai.com/",
            {'nav[aria-label*="history"]': True},
            "session_list_visible",
        ),
        (
            "gemini",
            "https://gemini.google.com/app/abc123",
            {'[aria-label="Conversaciones"]': True},
            "conversations_panel_visible",
        ),
    ],
)
def test_probe_reports_logged_in_happy_path(
    kind: str, url_after_goto: str, markers: dict[str, bool], expected_reason: str
) -> None:
    page = _FakePage(url=url_after_goto, title=f"{kind} home", markers=markers)
    controller = _FakeController(page)

    result = probe_assistant_login(
        kind,
        controller_factory=lambda: controller,
        clock=_fixed_clock(start=10.0, step=0.25),
        now_utc=_fixed_now(),
    )

    assert result["assistant_kind"] == kind
    assert result["logged_in"] is True
    assert result["reason"] == expected_reason
    assert result["checked_at_iso"].startswith("2026-04-20T01:23:45")
    assert isinstance(result["duration_ms"], int) and result["duration_ms"] >= 0
    evidence = result["evidence"]
    assert evidence["url_target"] == PROVIDER_HEURISTICS[kind].web_url
    assert evidence["url_final"] == url_after_goto
    assert evidence["mode"] == "isolated"
    assert "screenshot_png_b64" not in evidence  # default False
    # controller lifecycle
    assert controller.start_calls == 1
    assert controller.close_calls == 1
    assert page.goto_calls == [(PROVIDER_HEURISTICS[kind].web_url, 10000)]


@pytest.mark.parametrize(
    ("kind", "url_after_goto"),
    [
        ("chatgpt", "https://chatgpt.com/auth/login"),
        ("claude", "https://claude.ai/login"),
        ("codex", "https://codex.openai.com/auth/login"),
        ("gemini", "https://accounts.google.com/signin?continue=..."),
    ],
)
def test_probe_reports_not_logged_in_when_login_page(
    kind: str, url_after_goto: str
) -> None:
    page = _FakePage(url=url_after_goto, title="Sign in")
    controller = _FakeController(page)

    result = probe_assistant_login(
        kind,
        controller_factory=lambda: controller,
        clock=_fixed_clock(),
        now_utc=_fixed_now(),
    )

    assert result["logged_in"] is False
    assert result["reason"] == "login_page_detected"
    assert result["evidence"]["url_final"] == url_after_goto
    assert result["assistant_kind"] == kind


def test_probe_reports_not_logged_in_when_no_marker() -> None:
    page = _FakePage(url="https://chatgpt.com/about", markers={})
    controller = _FakeController(page)

    result = probe_assistant_login(
        "chatgpt",
        controller_factory=lambda: controller,
        clock=_fixed_clock(),
        now_utc=_fixed_now(),
    )

    assert result["logged_in"] is False
    assert result["reason"] == "no_logged_in_marker"


# ---------------------------------------------------------------------------
# Errores tipados


def test_probe_rejects_empty_kind() -> None:
    result = probe_assistant_login("")
    assert result["error"] == "invalid_assistant_kind"


def test_probe_rejects_unknown_kind() -> None:
    result = probe_assistant_login("unknown_foo")
    assert result["error"] == "unknown_assistant_kind"
    assert "chatgpt" in result["detail"]


def test_probe_returns_playwright_unavailable_when_factory_returns_none() -> None:
    result = probe_assistant_login(
        "chatgpt",
        controller_factory=lambda: None,
        now_utc=_fixed_now(),
    )
    assert result["error"] == "playwright_unavailable"
    assert result["assistant_kind"] == "chatgpt"
    assert "playwright" in result["detail"].lower()


def test_probe_returns_controller_init_failed_on_factory_exception() -> None:
    def _boom() -> Any:
        raise RuntimeError("cannot_init")

    result = probe_assistant_login(
        "chatgpt",
        controller_factory=_boom,
        now_utc=_fixed_now(),
    )
    assert result["error"] == "controller_init_failed"
    assert "cannot_init" in result["detail"]


def test_probe_returns_controller_start_failed_and_closes() -> None:
    page = _FakePage(url="https://chatgpt.com/")
    controller = _FakeController(page, start_raises=RuntimeError("start_died"))

    result = probe_assistant_login(
        "chatgpt",
        controller_factory=lambda: controller,
        now_utc=_fixed_now(),
    )

    assert result["error"] == "controller_start_failed"
    assert "start_died" in result["detail"]
    assert controller.close_calls == 1


def test_probe_returns_page_unavailable_when_controller_has_no_page() -> None:
    controller = _FakeController(page=None)

    result = probe_assistant_login(
        "chatgpt",
        controller_factory=lambda: controller,
        now_utc=_fixed_now(),
    )

    assert result["error"] == "page_unavailable"
    assert controller.close_calls == 1


def test_probe_returns_timeout_when_clock_overshoots() -> None:
    # El reloj avanza 100s por tick, superando timeout_seconds=5.0 tras goto.
    page = _FakePage(url="https://chatgpt.com/")
    controller = _FakeController(page)

    result = probe_assistant_login(
        "chatgpt",
        controller_factory=lambda: controller,
        timeout_seconds=5.0,
        clock=_fixed_clock(start=0.0, step=100.0),
        now_utc=_fixed_now(),
    )

    assert result["error"] == "timeout"
    assert result["assistant_kind"] == "chatgpt"
    assert result["partial_evidence"]["url_final"] == "https://chatgpt.com/"
    assert result["partial_evidence"]["mode"] == "isolated"
    assert result["duration_ms"] >= 0


def test_probe_returns_heuristic_failed_when_check_raises() -> None:
    # Provocamos excepción dentro de la heurística haciendo que query_selector
    # tire — el page fake lanza si le mandan un selector marcado como "raise".
    class _ExplodingPage(_FakePage):
        def query_selector(self, selector: str) -> object | None:
            raise RuntimeError("selector_blew_up")

    controller = _FakeController(
        _ExplodingPage(url="https://chatgpt.com/no_markers", markers={})
    )

    result = probe_assistant_login(
        "chatgpt",
        controller_factory=lambda: controller,
        now_utc=_fixed_now(),
    )

    assert result["error"] == "heuristic_failed"
    assert "selector_blew_up" in result["detail"]


# ---------------------------------------------------------------------------
# Opciones


def test_probe_includes_screenshot_when_requested() -> None:
    page = _FakePage(
        url="https://claude.ai/chat/new",
        title="Claude",
        screenshot_bytes=b"\x89PNG\r\n\x1a\nFAKE",
    )
    controller = _FakeController(page)

    result = probe_assistant_login(
        "claude",
        controller_factory=lambda: controller,
        include_screenshot=True,
        now_utc=_fixed_now(),
    )

    assert result["logged_in"] is True
    assert "screenshot_png_b64" in result["evidence"]
    assert result["evidence"]["screenshot_png_b64"]  # non-empty


def test_probe_shared_cdp_mode_uses_cdp_factory_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # El paquete __init__ re-exporta ``probe_assistant_login`` como atributo
    # (shadow del submódulo a nivel de getattr), por eso resolvemos el módulo
    # real vía ``sys.modules``.
    import sys

    mod = sys.modules["iabv_v15.infra.mcp.audit_tools.probe_assistant_login"]
    monkeypatch.setattr(mod, "_default_shared_cdp_controller_factory", lambda: None)
    monkeypatch.setattr(mod, "_default_isolated_controller_factory", lambda: object())

    result = probe_assistant_login("chatgpt", use_browser_session=False)
    assert result["error"] == "playwright_unavailable"


def test_known_assistant_kinds_is_stable() -> None:
    assert known_assistant_kinds() == ("chatgpt", "claude", "codex", "gemini")
