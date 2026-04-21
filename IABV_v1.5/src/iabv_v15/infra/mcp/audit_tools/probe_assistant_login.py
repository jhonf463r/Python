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
- ``codex`` → ``chatgpt.com/codex``: actualmente Codex vive bajo el dominio
  de ChatGPT (hosted under OpenAI), por lo que la heurística apunta ahí;
- ``gemini`` → ``gemini.google.com``: presencia de
  ``[aria-label="Conversaciones"]`` o ``[data-test-id="conversations"]``.

Asistentes **no-web** (``devin``, ``windsurf``, ``ollama``): no exponen una
página de login navegable con Playwright — se validan por otros medios
(API token, proceso local, IDE plugin). Para estos, la tool retorna un
payload estructurado con ``logged_in=null`` y ``reason="not_applicable_web_login"``
junto con un ``check_hint`` explicando cómo validar disponibilidad real.

Detección de Cloudflare challenge:
  Varios providers (``chatgpt``, ``claude``) sirven un interstitial de
  Cloudflare cuando el cliente parece automatizado. En ese caso la página
  navegada NO es la de la app — ni login ni logueado. Retornamos
  ``logged_in=null``, ``reason="cloudflare_challenge"`` e ``indeterminate=True``
  para que el consumidor no interprete como "deslogueado".
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
    "codex": _ProviderHeuristic(web_url="https://chatgpt.com/codex", check=_codex_heuristic),
    "gemini": _ProviderHeuristic(web_url="https://gemini.google.com/", check=_gemini_heuristic),
}


# ---------------------------------------------------------------------------
# Asistentes no-web: no tienen página de login navegable. Se validan por API
# token (devin), proceso local (ollama) o IDE plugin (windsurf). Mantenemos
# el contrato de ``probe_assistant_login`` pero devolvemos una respuesta
# explícita ``not_applicable_web_login`` — nunca ``unknown_assistant_kind``,
# para que el caller distinga "kind no soportado por la tool" de "kind válido
# pero no navegable".


@dataclass(frozen=True)
class _NonWebAssistant:
    """Describe cómo validar un asistente sin UI web navegable."""

    check_hint: str
    detail: str


NON_WEB_ASSISTANT_KINDS: dict[str, _NonWebAssistant] = {
    "devin": _NonWebAssistant(
        check_hint=(
            "Validá disponibilidad con `DEVIN_API_KEY` via "
            "`GET https://api.devin.ai/v1/sessions` (ver DevinApiToolAdapter)."
        ),
        detail=(
            "Devin es un agente cloud con login federado (Google/GitHub). No "
            "existe una página de login navegable con Playwright sin 2FA; la "
            "validez de la sesión se mide por API token operativo."
        ),
    ),
    "windsurf": _NonWebAssistant(
        check_hint=(
            "Validá presencia del IDE con detección de proceso "
            "(`windsurf.exe` / `Windsurf`) o presencia de la extensión "
            "instalada; no hay URL pública de login."
        ),
        detail=(
            "Windsurf es un IDE (fork de VS Code). La 'sesión logueada' vive "
            "dentro del proceso del IDE; no se audita navegando una URL."
        ),
    ),
    "ollama": _NonWebAssistant(
        check_hint=(
            "Validá el daemon local con "
            "`GET http://127.0.0.1:11434/v1/models`; si responde, Ollama está "
            "operativo (no hay concepto de 'login' en Ollama)."
        ),
        detail=(
            "Ollama es un runtime local de LLMs. No tiene cuenta, login ni "
            "dominio web; su disponibilidad se mide por HTTP 200 del daemon."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Cloudflare challenge detection
#
# Markers que aparecen cuando Cloudflare sirve un interstitial en vez del
# contenido real de la app. Si detectamos uno, retornamos ``indeterminate``
# para no falsear ``logged_in=False``.

CLOUDFLARE_CHALLENGE_TITLE_MARKERS: tuple[str, ...] = (
    "just a moment",
    "un momento",
    "please wait",
    "attention required",
    "checking your browser",
    "verifying you are human",
)

CLOUDFLARE_CHALLENGE_DOM_SELECTORS: tuple[str, ...] = (
    "#challenge-form",
    "#cf-challenge-running",
    "div#cf-wrapper",
    ".cf-turnstile",
    'iframe[src*="challenges.cloudflare.com"]',
    'iframe[title*="challenge" i]',
)


def _detect_cloudflare_challenge(page: Any) -> str | None:
    """Retorna ``marker`` si la página es un challenge de Cloudflare, si no None.

    Prioriza el title (rápido, robusto a i18n); fallback a selectores DOM
    conocidos. No propaga excepciones — cualquier fallo deja ``None``.
    """

    try:
        title = _safe_title(page)
    except Exception:
        title = ""
    lowered_title = title.lower().strip()
    for marker in CLOUDFLARE_CHALLENGE_TITLE_MARKERS:
        if marker in lowered_title:
            return f"title:{marker}"

    for selector in CLOUDFLARE_CHALLENGE_DOM_SELECTORS:
        try:
            node = page.query_selector(selector)
        except Exception:
            node = None
        if node is not None:
            return f"dom:{selector}"
    return None


# Aliases entre naming de capability profiles (PCS v1) y heurísticas de login.
# ``chatgpt_web``/``claude_web`` son los ``assistant_kind`` del
# ``AssistantCapabilityRegistry``; ``chatgpt``/``claude`` son las claves de
# heurística históricas. Los aceptamos como equivalentes para que el caller
# MCP no tenga que conocer ambas convenciones.
_ASSISTANT_KIND_ALIASES: dict[str, str] = {
    "chatgpt_web": "chatgpt",
    "claude_web": "claude",
    "codex_web": "codex",
    "gemini_web": "gemini",
    "openai_chatgpt": "chatgpt",
    "anthropic_claude": "claude",
    "google_gemini": "gemini",
    # Asistentes no-web (ver ``NON_WEB_ASSISTANT_KINDS``).
    "devin_cloud": "devin",
    "devin_api": "devin",
    "windsurf_ide": "windsurf",
    "ollama_local": "ollama",
    "llm_local_ollama": "ollama",
}


def _resolve_assistant_kind(kind: str) -> str:
    """Resuelve ``kind`` a una clave canónica de ``PROVIDER_HEURISTICS``.

    Acepta alias comunes (``chatgpt_web`` → ``chatgpt``, etc.). Si no
    encuentra match, devuelve ``kind`` sin cambios para que el validador
    upstream emita ``unknown_assistant_kind`` con la lista completa.
    """

    return _ASSISTANT_KIND_ALIASES.get(kind, kind)


def known_assistant_kinds() -> tuple[str, ...]:
    """Kinds aceptados por la tool (orden estable para docs/tests).

    Incluye los providers web (``PROVIDER_HEURISTICS``) y los asistentes
    no-web (``NON_WEB_ASSISTANT_KINDS``). Ambos son respuestas válidas;
    la forma del payload difiere pero el contrato `known kind` es el mismo.
    """

    return tuple(PROVIDER_HEURISTICS.keys()) + tuple(NON_WEB_ASSISTANT_KINDS.keys())


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

    raw_kind = (assistant_kind or "").strip().lower()
    if not raw_kind:
        return {
            "error": "invalid_assistant_kind",
            "detail": "assistant_kind no puede ser vacío",
            "assistant_kind": assistant_kind,
        }
    kind = _resolve_assistant_kind(raw_kind)
    if kind not in PROVIDER_HEURISTICS and kind not in NON_WEB_ASSISTANT_KINDS:
        valid_kinds = list(known_assistant_kinds()) + sorted(_ASSISTANT_KIND_ALIASES)
        return {
            "error": "unknown_assistant_kind",
            "detail": (
                f"assistant_kind={raw_kind!r} no soportado; válidos: "
                f"{', '.join(valid_kinds)}"
            ),
            "assistant_kind": raw_kind,
        }

    checked_at_iso = now_utc().isoformat()
    started_at = clock()

    # Asistentes no-web: devolvemos payload estructurado sin Playwright.
    if kind in NON_WEB_ASSISTANT_KINDS:
        info = NON_WEB_ASSISTANT_KINDS[kind]
        return {
            "assistant_kind": kind,
            "logged_in": None,
            "indeterminate": True,
            "reason": "not_applicable_web_login",
            "detail": info.detail,
            "check_hint": info.check_hint,
            "evidence": {
                "url_target": None,
                "mode": "non_web",
            },
            "checked_at_iso": checked_at_iso,
            "duration_ms": int((clock() - started_at) * 1000),
        }

    heuristic = PROVIDER_HEURISTICS[kind]

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

        # Detectar Cloudflare challenge ANTES de correr la heurística:
        # si la página está tapada por un interstitial, el heurístico
        # reportaría ``no_logged_in_marker`` sin base (falso negativo).
        challenge_marker = _detect_cloudflare_challenge(page)
        if challenge_marker is not None:
            duration_ms = int((clock() - started_at) * 1000)
            evidence: dict[str, Any] = {
                "url_final": _safe_url(page),
                "url_target": heuristic.web_url,
                "page_title": _safe_title(page),
                "challenge_marker": challenge_marker,
                "mode": "isolated" if use_browser_session else "shared_cdp",
            }
            if include_screenshot:
                shot_b64 = _safe_screenshot(page)
                if shot_b64:
                    evidence["screenshot_png_b64"] = shot_b64
            return {
                "assistant_kind": kind,
                "logged_in": None,
                "indeterminate": True,
                "reason": "cloudflare_challenge",
                "detail": (
                    "La navegación recibió un interstitial de Cloudflare; "
                    "no se puede determinar logueo hasta resolver el challenge."
                ),
                "evidence": evidence,
                "checked_at_iso": checked_at_iso,
                "duration_ms": duration_ms,
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
        evidence = {
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
