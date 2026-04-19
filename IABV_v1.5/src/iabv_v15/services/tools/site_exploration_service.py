"""SiteExplorationService: crawl acotado y determinista de un sitio.

Objetivo: dado un `start_url`, visitar hasta `max_pages` paginas del
mismo dominio, extraer un snapshot liviano de cada una (titulo, headings,
links internos, formularios) y entregar un payload que
`SiteManualRepository` pueda persistir.

Alcance deliberado (PR-D v1):

- BFS con budget y filtro same-domain. El orden de descubrimiento es
  determinista: breadth-first desde `start_url`.
- No hay toma de decisiones "inteligente" de navegacion: no se
  introduce un nuevo cerebro ni un nuevo orquestador. Si se quiere
  priorizar paginas, se expone `priority_keywords` como heuristica
  simple.
- El LLM (opcional) solo se usa al final para redactar un `summary`
  del manual. La exploracion sigue siendo reproducible sin LLM.
- Reutiliza `BrowserSessionController` + `BrowserActionService` del
  stack existente (contrato de captura ya vigente).

Contratos respetados:

- No crea otro cerebro; no duplica `PerceptionSnapshot`.
- No toca governance ni ViewModels.
- Si `sync_playwright` no esta disponible, el servicio se declara no
  ejecutable (mismo patron que `PlaywrightToolAdapter.is_available`).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from iabv_v15.services.capture.browser_session_controller import (
    BrowserSessionController,
    sync_playwright,
)


@dataclass
class SitePageSnapshot:
    url: str
    title: str
    headings: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    error: str = ''


@dataclass
class SiteExplorationResult:
    hostname: str
    start_url: str
    pages: list[SitePageSnapshot]
    summary: str = ''
    success: bool = True
    error_message: str = ''
    execution_ms: int = 0

    def to_manual(self) -> dict[str, Any]:
        return {
            'hostname': self.hostname,
            'start_url': self.start_url,
            'summary': self.summary,
            'pages': [
                {
                    'url': page.url,
                    'title': page.title,
                    'headings': page.headings,
                    'internal_links': page.internal_links,
                    'forms': page.forms,
                    'error': page.error,
                }
                for page in self.pages
            ],
        }


# Firma: (pages_payload, start_url, hostname) -> str
SummaryFn = Callable[[list[dict[str, Any]], str, str], str]


class SiteExplorationService:
    """Crawl acotado sobre una misma raiz de dominio.

    El `controller_factory` permite inyectar un `BrowserSessionController`
    falso desde tests. Si no se pasa, se usa uno headless real.
    """

    _PAGE_WAIT_MS = 8000
    _DEFAULT_MAX_PAGES = 6
    _DEFAULT_MAX_LINKS_PER_PAGE = 30
    _DEFAULT_MAX_HEADINGS = 12

    def __init__(
        self,
        *,
        controller_factory: Callable[[], BrowserSessionController] | None = None,
        summary_fn: SummaryFn | None = None,
    ) -> None:
        self._controller_factory = controller_factory or (lambda: BrowserSessionController(headless=True))
        self._summary_fn = summary_fn

    def is_available(self) -> bool:
        return sync_playwright is not None

    def explore(
        self,
        *,
        start_url: str,
        max_pages: int | None = None,
        priority_keywords: list[str] | None = None,
    ) -> SiteExplorationResult:
        start = time.perf_counter()
        target_url = (start_url or '').strip()
        if not target_url:
            return SiteExplorationResult(
                hostname='',
                start_url='',
                pages=[],
                success=False,
                error_message='start_url vacio.',
            )
        hostname = (urlparse(target_url).hostname or '').lower()
        if not hostname:
            return SiteExplorationResult(
                hostname='',
                start_url=target_url,
                pages=[],
                success=False,
                error_message=f'URL sin hostname: {target_url}',
            )
        budget = max_pages if isinstance(max_pages, int) and max_pages > 0 else self._DEFAULT_MAX_PAGES
        priority = {str(k).strip().lower() for k in (priority_keywords or []) if str(k).strip()}

        controller = self._controller_factory()
        pages: list[SitePageSnapshot] = []
        error_message = ''
        try:
            controller.start()
            page = controller.page or controller.new_page()
            visited: set[str] = set()
            queue: deque[str] = deque([target_url])
            while queue and len(pages) < budget:
                next_url = queue.popleft()
                normalized = self._normalize_url(next_url)
                if not normalized or normalized in visited:
                    continue
                if (urlparse(normalized).hostname or '').lower() != hostname:
                    continue
                visited.add(normalized)
                snapshot = self._capture_page(page, normalized)
                # filtra "internal_links" para que solo incluya el mismo
                # dominio que el hostname de la raiz; los enlaces externos
                # se descartan del manual y del crawl.
                snapshot.internal_links = [
                    link for link in snapshot.internal_links
                    if (urlparse(link).hostname or '').lower() == hostname
                ]
                pages.append(snapshot)
                for link in snapshot.internal_links:
                    if link in visited:
                        continue
                    # priority_keywords reordena, no filtra: los que
                    # machean se procesan primero. Sin priority, se mantiene
                    # el orden BFS clasico (FIFO).
                    if priority and any(token in link.lower() for token in priority):
                        queue.appendleft(link)
                    else:
                        queue.append(link)
        except Exception as exc:  # noqa: BLE001 - playwright lanza varios tipos
            error_message = f'{type(exc).__name__}: {exc}'
        finally:
            try:
                controller.close()
            except Exception:
                pass

        success = bool(pages) and not error_message
        summary = ''
        if success and self._summary_fn is not None:
            try:
                summary = self._summary_fn(
                    [page.__dict__ for page in pages],
                    target_url,
                    hostname,
                )
            except Exception as exc:  # noqa: BLE001
                summary = f'(summary_fn fallo: {type(exc).__name__})'

        return SiteExplorationResult(
            hostname=hostname,
            start_url=target_url,
            pages=pages,
            summary=summary,
            success=success,
            error_message=error_message,
            execution_ms=int((time.perf_counter() - start) * 1000),
        )

    def _capture_page(self, page: Any, url: str) -> SitePageSnapshot:
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=self._PAGE_WAIT_MS)
        except TypeError:
            # Fake pages de tests pueden no aceptar kwargs.
            page.goto(url)
        except Exception as exc:  # noqa: BLE001
            return SitePageSnapshot(url=url, title='', error=f'{type(exc).__name__}: {exc}')
        try:
            title = str(getattr(page, 'title', lambda: '')() or '')
        except Exception:  # noqa: BLE001
            title = ''
        headings = self._safe_eval(page, _HEADINGS_JS, []) or []
        raw_links = self._safe_eval(page, _LINKS_JS, []) or []
        forms = self._safe_eval(page, _FORMS_JS, []) or []
        internal_links: list[str] = []
        seen: set[str] = set()
        for raw in raw_links:
            absolute = self._normalize_url(urljoin(url, str(raw)))
            if not absolute or absolute in seen:
                continue
            seen.add(absolute)
            if len(internal_links) >= self._DEFAULT_MAX_LINKS_PER_PAGE:
                break
            internal_links.append(absolute)
        return SitePageSnapshot(
            url=url,
            title=title.strip(),
            headings=[str(h).strip() for h in headings[: self._DEFAULT_MAX_HEADINGS] if str(h).strip()],
            internal_links=internal_links,
            forms=[f for f in forms if isinstance(f, dict)],
        )

    @staticmethod
    def _safe_eval(page: Any, script: str, default: Any) -> Any:
        try:
            return page.evaluate(script)
        except Exception:  # noqa: BLE001 - playwright levanta errores variados
            return default

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url:
            return ''
        cleaned = url.strip()
        if cleaned.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            return ''
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.hostname:
            return ''
        # normaliza trailing slash y drop del fragment
        path = parsed.path or '/'
        return f'{parsed.scheme}://{parsed.hostname.lower()}{path}' + (f'?{parsed.query}' if parsed.query else '')


_HEADINGS_JS = """
() => Array.from(document.querySelectorAll('h1, h2, h3'))
  .map((el) => (el.innerText || '').trim())
  .filter(Boolean)
  .slice(0, 20)
"""

_LINKS_JS = """
() => Array.from(document.querySelectorAll('a[href]'))
  .map((el) => el.getAttribute('href') || '')
  .filter((href) => !!href)
  .slice(0, 200)
"""

_FORMS_JS = """
() => Array.from(document.querySelectorAll('form')).map((form) => ({
  action: form.getAttribute('action') || '',
  method: (form.getAttribute('method') || 'get').toLowerCase(),
  inputs: Array.from(form.querySelectorAll('input, textarea, select')).map((el) => ({
    name: el.getAttribute('name') || '',
    type: (el.getAttribute('type') || el.tagName || '').toLowerCase(),
  })).filter((entry) => entry.name).slice(0, 20),
})).slice(0, 10)
"""
