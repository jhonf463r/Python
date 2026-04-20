"""Audit tool: ``probe_assistant_login(assistant_kind)``.

Comprueba si el usuario está **realmente logueado** en un asistente web
externo (ChatGPT, Claude, Codex, Gemini) abriendo la URL declarada en
``tool_registry`` con Playwright (via ``BrowserSessionController`` cuando
``use_browser_session=True``) o conectándose al Chrome del usuario vía CDP
(``use_browser_session=False``, requiere ``IABV_SHARED_CDP_URL`` o
``localhost:29229``).

Este módulo es **puro a nivel de política**: no decide rutas, no muta
estado del sistema vivo y no propaga excepciones al cliente MCP (devuelve
dicts ``{error: ...}``). El gate de governance lo aplica ``server.py``
antes de invocar esta función.

Contratos respetados (AGENTS.md):
- no fabrica observación: si Playwright no está instalado o la URL no
  responde a tiempo, devuelve ``{error: ...}`` explícito;
- no duplica ``PerceptionSnapshot``: sólo retorna evidencia puntual;
- no abre una vía encubierta de red — el caller ya validó
  ``requires_network=True`` en el gate.

Heurísticas por provider (inspiradas por el RFC
``docs/rfcs/devin-iabv-teaching-handshake.md``):

- ``chatgpt`` → ``chatgpt.com``: presencia de ``nav[aria-label*="history"]``
  o URL sin ``/auth/login``;
- ``claude`` → ``claude.ai``: URL no redirige a ``/login``; ``/chat/new``
  o ``/new`` es señal de logueado;
- ``codex`` → ``codex.openai.com``: similar a chatgpt;
- ``gemini`` → ``gemini.google.com``: presencia de
  ``[aria-label="Conversaciones"]`` o ``[data-test-id="conversations"]``.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_SHARED_CDP_URL = "http://localhost:29229"
NAVIGATION_TIMEOUT_MS = 15_000
SCREENSHOT_MAX_BYTES = 512 * 1024  # 512 KiB — evita respuestas gigantes


# ---------------------------------------------------------------------------
# Contrato de heurística


@dataclass(frozen=True)
class HeuristicResult:
    """Resultado de evaluar una heurística de logueo sobre una página."""

    logged_in: bool
    reason: str
    html_marker: str = ""


@dataclass(frozen=True)
class _ProviderHeuristic:
    """Configuración por provider: URL objetivo + evaluador."""

    web_url: str
    check: Callable[["_PageLike"], HeuristicResult]


class _PageLike(Protocol):
    """Subset de ``playwright.sync_api.Page`` que usamos.

    Tests proveen un fake compatible; no importamos playwright acá para
    no atarnos al runtime.
    """

    url: Any  # property: str
    def title(self) -> str: ...  # noqa: E704
    def query_selector(self, selector: str) -> Any | None: ...  # noqa: E704
    def goto(self, url: str, *, timeout: int = ...) -> Any: ...  # noqa: E704
    def screenshot(self, *, type: str = "png", full_page: bool = False) -> bytes: ...  # noqa: E704


# ---------------------------------------------------------------------------
# Heurísticas por provider


def _chatgpt_heuristic(page: _PageLike) -> HeuristicResult:
    final_url = str(getattr(page, "url", "") or "")
    lowered = final_url.lower()
    if "auth/login" in lowered or lowered.endswith("/login") or "/auth?" in lowered:
        return HeuristicResult(logged_in=False, reason="login_page_detected")
    nav = page.query_selector('nav[aria-label*="history" i]') or page.query_selector(
        'nav[aria-label*="chat history" i]'
    ) or page.query_selector('nav[aria-label*="historial" i]')
    if nav is not None:
        return HeuristicResult(
            logged_in=True,
            reason="nav_history_visible",
            html_marker='nav[aria-label*="history"]',
        )
    return HeuristicResult(logged_in=False, reason="no_logged_in_marker")


def _claude_heuristic(page: _PageLike) -> HeuristicResult:
    final_url = str(getattr(page, "url", "") or "")
    lowered = final_url.lower()
    path = (urlparse(lowered).path or "").rstrip("/")
    path_segments = [seg for seg in path.split("/") if seg]
    if path.endswith("/login") and "/chat/" not in path and "/chats/" not in path:
        return HeuristicResult(logged_in=False, reason="login_page_detected")
    # Match por segmento exacto (no substring): evita que `/news` o
    # `/newsletter` colisionen con la señal `/new`. Aceptamos:
    #   * `/new`, `/new/...`
    #   * `/chat`, `/chat/...`, `/chat/new/...`
    #   * `/chats`, `/chats/...`
    if path_segments and (
        path_segments[0] in {"new", "chat", "chats"}
    ):
        return HeuristicResult(
            logged_in=True,
            reason="chat_route_reached",
            html_marker=final_url,
        )
    nav = page.query_selector('[data-testid="new-chat-button"]') or page.query_selector(
        'nav[aria-label*="conversations" i]'
    )
    if nav is not None:
        return HeuristicResult(
            logged_in=True,
            reason="new_chat_button_visible",
            html_marker='[data-testid="new-chat-button"]',
        )
    return HeuristicResult(logged_in=False, reason="no_logged_in_marker")


def _codex_heuristic(page: _PageLike) -> HeuristicResult:
    final_url = str(getattr(page, "url", "") or "")
    lowered = final_url.lower()
    if "auth/login" in lowered or lowered.endswith("/login"):
        return HeuristicResult(logged_in=False, reason="login_page_detected")
    nav = page.query_selector('nav[aria-label*="history" i]') or page.query_selector(
        '[data-testid="session-list"]'
    )
    if nav is not None:
        return HeuristicResult(
            logged_in=True,
            reason="session_list_visible",
            html_marker='nav[aria-label*="history"]',
        )
    return HeuristicResult(logged_in=False, reason="no_logged_in_marker")


def _gemini_heuristic(page: _PageLike) -> HeuristicResult:
    final_url = str(getattr(page, "url", "") or "")
    lowered = final_url.lower()
    if "accounts.google.com" in lowered or "signin" in lowered or "/login" in lowered:
        return HeuristicResult(logged_in=False, reason="login_page_detected")
    conversations = page.query_selector(
        '[aria-label="Conversaciones"]'
    ) or page.query_selector(
        '[aria-label="Conversations"]'
    ) or page.query_selector(
        '[data-test-id="conversations"]'
    )
    if conversations is not None:
        return HeuristicResult(
            logged_in=True,
            reason="conversations_panel_visible",
            html_marker='[aria-label="Conversaciones"]',
        )
    return HeuristicResult(logged_in=False, reason="no_logged_in_marker")


PROVIDER_HEURISTICS: dict[str, _ProviderHeuristic] = {
    "chatgpt": _ProviderHeuristic(web_url="https://chatgpt.com/", check=_chatgpt_heuristic),
    "claude": _ProviderHeuristic(web_url="https://claude.ai/", check=_claude_heuristic),
    "codex": _ProviderHeuristic(web_url="https://codex.openai.com/", check=_codex_heuristic),
    "gemini": _ProviderHeuristic(web_url="https://gemini.google.com/", check=_gemini_heuristic),
}


def known_assistant_kinds() -> tuple[str, ...]:
    """Kinds aceptados por la tool (orden estable para docs/tests)."""

    return tuple(PROVIDER_HEURISTICS.keys())


# ---------------------------------------------------------------------------
# Playwright controller adapters


class _ControllerLike(Protocol):
    def start(self) -> None: ...  # noqa: E704
    def close(self) -> None: ...  # noqa: E704
    page: Any  # property


def _playwright_available() -> bool:
    """Determina si el runtime de playwright está disponible."""

    try:  # pragma: no cover - import path sólo ejercitado en Windows real
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return False
    return True


def _default_isolated_controller_factory() -> _ControllerLike | None:
    """Construye un ``BrowserSessionController`` aislado (``program_chat``)."""

    if not _playwright_available():
        return None
    from iabv_v15.domain.models import BrowserProfileConfig, PersistStrategy  # type: ignore
    from iabv_v15.services.capture.browser_session_controller import (
        BrowserSessionController,
    )

    profile = BrowserProfileConfig(
        profile_id="mcp_probe_assistant",
        site_id="mcp_probe_assistant",
        channel="chromium",
        persist_strategy=PersistStrategy.STORAGE_STATE_ONLY,
        user_data_dir=None,
        storage_state_path=None,
        headless=True,
    )
    controller = BrowserSessionController(profile_config=profile)
    return controller  # type: ignore[return-value]


def _default_shared_cdp_controller_factory() -> _ControllerLike | None:
    """Conecta a Chrome del usuario vía CDP (``IABV_SHARED_CDP_URL``).

    Devuelve un adapter con la misma interfaz (``start`` / ``close`` /
    ``page``). Si playwright o CDP no están disponibles, devuelve None.
    """

    if not _playwright_available():
        return None

    cdp_url = os.environ.get("IABV_SHARED_CDP_URL", DEFAULT_SHARED_CDP_URL)

    class _CDPAdapter:
        def __init__(self) -> None:
            self._pw: Any = None
            self._browser: Any = None
            self._context: Any = None
            self._page: Any = None

        def start(self) -> None:  # pragma: no cover - requiere Chrome real
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.connect_over_cdp(cdp_url)
            contexts = list(getattr(self._browser, "contexts", []) or [])
            self._context = contexts[0] if contexts else self._browser.new_context()
            pages = list(getattr(self._context, "pages", []) or [])
            self._page = pages[0] if pages else self._context.new_page()

        @property
        def page(self) -> Any:  # pragma: no cover - requiere Chrome real
            return self._page

        def close(self) -> None:  # pragma: no cover - requiere Chrome real
            try:
                if self._pw is not None:
                    self._pw.stop()
            except Exception:  # defensive — no queremos tirar en cleanup
                logger.debug("CDP adapter close failed", exc_info=True)

    return _CDPAdapter()


# ---------------------------------------------------------------------------
# Entry point público


def probe_assistant_login(
    assistant_kind: str,
    *,
    use_browser_session: bool = True,
    controller_factory: Callable[[], _ControllerLike | None] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    include_screenshot: bool = False,
    clock: Callable[[], float] = time.monotonic,
    now_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    """Comprueba si el usuario está logueado en ``assistant_kind``.

    Args:
        assistant_kind: uno de ``chatgpt``, ``claude``, ``codex``, ``gemini``.
        use_browser_session: si True (default), usa un contexto aislado
            ``program_chat`` (no reutiliza la sesión del usuario). Si False,
            se conecta a Chrome del usuario vía CDP (requiere que el Chrome
            esté corriendo con ``--remote-debugging-port`` o equivalente).
        controller_factory: override para tests. Si se provee, ignora
            ``use_browser_session`` y usa la factoría dada.
        timeout_seconds: tope duro (navegación + heurística). Al excederlo,
            devuelve ``{error: "timeout", partial_evidence: {...}}``.
        include_screenshot: si True, incluye un PNG en base64 (tope
            ``SCREENSHOT_MAX_BYTES``). Por default False para mantener
            payloads chicos.
        clock: inyectable para tests.
        now_utc: inyectable para tests (congela ``checked_at_iso``).

    Returns:
        Dict serializable con ``{assistant_kind, logged_in, evidence,
        checked_at_iso, duration_ms}`` en happy path, o ``{error, detail,
        assistant_kind, ...}`` en caso de fallo.
    """

    kind = (assistant_kind or "").strip().lower()
    if not kind:
        return {
            "error": "invalid_assistant_kind",
            "detail": "assistant_kind no puede ser vacío",
            "assistant_kind": assistant_kind,
        }
    if kind not in PROVIDER_HEURISTICS:
        return {
            "error": "unknown_assistant_kind",
            "detail": (
                f"assistant_kind={kind!r} no soportado; válidos: "
                f"{', '.join(known_assistant_kinds())}"
            ),
            "assistant_kind": kind,
        }

    heuristic = PROVIDER_HEURISTICS[kind]
    checked_at_iso = now_utc().isoformat()
    started_at = clock()

    if controller_factory is None:
        controller_factory = (
            _default_isolated_controller_factory
            if use_browser_session
            else _default_shared_cdp_controller_factory
        )

    try:
        controller = controller_factory()
    except Exception as exc:
        logger.debug("controller_factory() failed", exc_info=True)
        return {
            "error": "controller_init_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "assistant_kind": kind,
            "checked_at_iso": checked_at_iso,
        }

    if controller is None:
        return {
            "error": "playwright_unavailable",
            "detail": (
                "playwright no está instalado o no se pudo construir el "
                "BrowserSessionController. Instalá `playwright` y corré "
                "`playwright install chromium` en la máquina que hostea IABV."
            ),
            "assistant_kind": kind,
            "checked_at_iso": checked_at_iso,
        }

    partial_evidence: dict[str, Any] = {
        "url_target": heuristic.web_url,
        "mode": "isolated" if use_browser_session else "shared_cdp",
    }

    try:
        controller.start()
    except Exception as exc:
        logger.debug("controller.start() failed", exc_info=True)
        _safe_close(controller)
        return {
            "error": "controller_start_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "assistant_kind": kind,
            "checked_at_iso": checked_at_iso,
            "partial_evidence": partial_evidence,
        }

    try:
        page = _resolve_page(controller)
        if page is None:
            return {
                "error": "page_unavailable",
                "detail": "El controller no expuso una página utilizable.",
                "assistant_kind": kind,
                "checked_at_iso": checked_at_iso,
                "partial_evidence": partial_evidence,
            }

        try:
            page.goto(heuristic.web_url, timeout=int(timeout_seconds * 1000))
        except Exception as exc:  # pragma: no cover - playwright real
            logger.debug("page.goto failed", exc_info=True)
            return {
                "error": "navigation_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "assistant_kind": kind,
                "checked_at_iso": checked_at_iso,
                "partial_evidence": partial_evidence,
            }

        elapsed = clock() - started_at
        if elapsed > timeout_seconds:
            partial_evidence["url_final"] = _safe_url(page)
            return {
                "error": "timeout",
                "detail": (
                    f"Navegación a {heuristic.web_url} excedió "
                    f"timeout_seconds={timeout_seconds}; parcial disponible."
                ),
                "assistant_kind": kind,
                "checked_at_iso": checked_at_iso,
                "duration_ms": int(elapsed * 1000),
                "partial_evidence": partial_evidence,
            }

        try:
            result = heuristic.check(page)
        except Exception as exc:
            logger.debug("heuristic check failed", exc_info=True)
            partial_evidence["url_final"] = _safe_url(page)
            return {
                "error": "heuristic_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "assistant_kind": kind,
                "checked_at_iso": checked_at_iso,
                "partial_evidence": partial_evidence,
            }

        duration_ms = int((clock() - started_at) * 1000)
        evidence: dict[str, Any] = {
            "url_final": _safe_url(page),
            "url_target": heuristic.web_url,
            "page_title": _safe_title(page),
            "html_marker": result.html_marker,
            "mode": "isolated" if use_browser_session else "shared_cdp",
        }
        if include_screenshot:
            shot_b64 = _safe_screenshot(page)
            if shot_b64:
                evidence["screenshot_png_b64"] = shot_b64

        payload: dict[str, Any] = {
            "assistant_kind": kind,
            "logged_in": bool(result.logged_in),
            "reason": result.reason,
            "evidence": evidence,
            "checked_at_iso": checked_at_iso,
            "duration_ms": duration_ms,
        }
        return payload
    finally:
        _safe_close(controller)


# ---------------------------------------------------------------------------
# Helpers internos


def _resolve_page(controller: _ControllerLike) -> Any | None:
    page = getattr(controller, "page", None)
    if callable(page):  # tests fake pueden exponer ``page`` como método
        try:
            page = page()
        except Exception:
            page = None
    return page


def _safe_url(page: Any) -> str:
    try:
        value = getattr(page, "url", "")
        return str(value or "")
    except Exception:
        return ""


def _safe_title(page: Any) -> str:
    try:
        title = page.title()
        return str(title or "")
    except Exception:
        return ""


def _safe_screenshot(page: Any) -> str:
    try:
        raw = page.screenshot(type="png", full_page=False)
    except Exception:
        return ""
    if not raw:
        return ""
    if len(raw) > SCREENSHOT_MAX_BYTES:
        # Truncar bytes PNG rompe la firma IEND y produce una imagen
        # indecodable. En vez de shipear basura, dropeamos el screenshot
        # completo y dejamos que el caller note `screenshot_png_b64`
        # vacío como señal de "demasiado grande".
        logger.debug(
            "probe_assistant_login screenshot %d bytes > %d (SCREENSHOT_MAX_BYTES); dropping",
            len(raw),
            SCREENSHOT_MAX_BYTES,
        )
        return ""
    return base64.b64encode(raw).decode("ascii")


def _safe_close(controller: _ControllerLike) -> None:
    try:
        controller.close()
    except Exception:  # pragma: no cover - defensivo
        logger.debug("controller.close() failed", exc_info=True)
