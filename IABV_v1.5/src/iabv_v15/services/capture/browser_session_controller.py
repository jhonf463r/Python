from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import BrowserProfileConfig, PersistStrategy

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
except ImportError:  # pragma: no cover - optional runtime dependency
    Browser = BrowserContext = Page = Any
    sync_playwright = None


def _default_launch_args() -> list[str]:
    return [
        '--disable-blink-features=AutomationControlled',
        '--disable-infobars',
        '--start-maximized',
        '--window-position=0,0',
    ]


def _default_ignored_args() -> list[str]:
    return ['--enable-automation']


def _build_storage_seed_script(state_payload: dict[str, Any]) -> str:
    origins: list[dict[str, Any]] = []
    for item in state_payload.get('origins') or []:
        origin = item.get('origin')
        local_storage = item.get('localStorage') or []
        if origin and local_storage:
            origins.append({'origin': origin, 'localStorage': local_storage})
    serialized = json.dumps(origins, ensure_ascii=False)
    return f"""
(() => {{
  const entries = {serialized};
  const currentOrigin = window.location.origin;
  const match = entries.find((entry) => entry.origin === currentOrigin);
  if (!match || !window.localStorage) {{
    return;
  }}
  for (const item of match.localStorage || []) {{
    if (!item || typeof item.name !== \"string\") {{
      continue;
    }}
    try {{
      window.localStorage.setItem(item.name, item.value ?? \"\");
    }} catch (error) {{
    }}
  }}
}})();
"""


class BrowserSessionController:
    """Playwright controller for Browser Teach Mode."""

    def __init__(
        self,
        profile_config: BrowserProfileConfig | None = None,
        user_data_dir: str | None = None,
        storage_state_path: str | None = None,
        headless: bool = False,
        channel: str | None = None,
        launch_args: list[str] | None = None,
        ignore_default_args: list[str] | bool | None = None,
    ) -> None:
        self.profile_config = profile_config
        self.user_data_dir = Path(user_data_dir) if user_data_dir else None
        self.storage_state_path = Path(storage_state_path) if storage_state_path else None
        self.headless = headless
        self.channel = channel
        self.launch_args = launch_args or _default_launch_args()
        self.ignore_default_args = ignore_default_args if ignore_default_args is not None else _default_ignored_args()
        self.chromium_sandbox = True
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._owner_thread_id: int | None = None
        self._close_requested: bool = False
        self._close_unresolved_reported: bool = False
        if profile_config is not None:
            self.configure(profile_config)

    def configure(self, profile_config: BrowserProfileConfig) -> None:
        self.profile_config = profile_config
        if profile_config.persist_strategy == PersistStrategy.STORAGE_STATE_ONLY:
            self.user_data_dir = None
        else:
            self.user_data_dir = Path(profile_config.user_data_dir) if profile_config.user_data_dir else None
        self.storage_state_path = Path(profile_config.storage_state_path) if profile_config.storage_state_path else None
        self.headless = profile_config.headless
        self.channel = profile_config.channel
        self.launch_args = profile_config.launch_args or _default_launch_args()
        self.ignore_default_args = _default_ignored_args()
        self.chromium_sandbox = True

    @property
    def context(self) -> BrowserContext | None:
        if self.close_if_owner_thread():
            return None
        return self._context

    @property
    def page(self) -> Page | None:
        if self.close_if_owner_thread():
            return None
        if self._page is not None:
            try:
                if not self._page.is_closed():
                    return self._page
            except Exception:
                return self._page
            self._page = None
        if self._context is not None and getattr(self._context, 'pages', None):
            pages = []
            for page in self._context.pages:
                try:
                    if page.is_closed():
                        continue
                except Exception:
                    pass
                pages.append(page)
            if pages:
                self._page = pages[-1]
        return self._page

    def start(self, profile_config: BrowserProfileConfig | None = None) -> None:
        if profile_config is not None:
            self.configure(profile_config)
        if sync_playwright is None:
            raise RuntimeError('Playwright is not installed.')
        self.close_if_owner_thread()
        if self._pw is not None:
            return
        self._pw = sync_playwright().start()
        self._owner_thread_id = threading.current_thread().ident
        self._close_unresolved_reported = False

        if self.user_data_dir is not None:
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                channel=self.channel,
                args=self.launch_args,
                ignore_default_args=self.ignore_default_args,
                chromium_sandbox=self.chromium_sandbox,
                no_viewport=True,
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._configure_page(self._page)
            self.restore_storage_state()
            self.maximize_window()
            logger.info('Started persistent browser context: %s', self.user_data_dir)
            return

        self._browser = self._pw.chromium.launch(
            headless=self.headless,
            channel=self.channel,
            args=self.launch_args,
            ignore_default_args=self.ignore_default_args,
            chromium_sandbox=self.chromium_sandbox,
        )
        if self.storage_state_path and self.storage_state_path.exists():
            self._context = self._browser.new_context(storage_state=str(self.storage_state_path), no_viewport=True)
        else:
            self._context = self._browser.new_context(no_viewport=True)
        self._page = self._context.new_page()
        self._configure_page(self._page)
        self.maximize_window()
        logger.info('Started browser session. storage_state=%s', self.storage_state_path)

    def new_page(self) -> Page:
        if self._context is None:
            raise RuntimeError('Browser session not started.')
        self._page = self._context.new_page()
        self._configure_page(self._page)
        self.maximize_window()
        return self._page

    def adopt_page(self, page: Page | None) -> Page | None:
        self._page = page
        if page is not None:
            self._configure_page(page)
            self.maximize_window()
        return self._page

    def _configure_page(self, page: Page | None) -> None:
        if page is None:
            return
        try:
            page.set_default_timeout(15000)
        except Exception:
            pass
        try:
            page.set_default_navigation_timeout(15000)
        except Exception:
            pass

    def maximize_window(self) -> None:
        if self._context is None or self.page is None or self.headless:
            return
        try:
            session = self._context.new_cdp_session(self.page)
            window_info = session.send('Browser.getWindowForTarget')
            session.send(
                'Browser.setWindowBounds',
                {
                    'windowId': window_info.get('windowId'),
                    'bounds': {'windowState': 'maximized'},
                },
            )
        except Exception as exc:
            logger.debug('Could not maximize browser window: %s', exc)

    def save_storage_state(self, path: str) -> str:
        if self._context is None:
            raise RuntimeError('No active browser context.')
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=str(target))
        return str(target)

    def restore_storage_state(self) -> bool:
        if self._context is None or self.storage_state_path is None or not self.storage_state_path.exists():
            return False
        try:
            payload = json.loads(self.storage_state_path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.warning('Could not read storage state from %s: %s', self.storage_state_path, exc)
            return False

        restored_any = False
        cookies = payload.get('cookies') or []
        if cookies:
            try:
                self._context.add_cookies(cookies)
                restored_any = True
            except Exception as exc:
                logger.debug('Could not restore cookies from storage state: %s', exc)

        storage_script = _build_storage_seed_script(payload)
        if storage_script.strip():
            try:
                self._context.add_init_script(script=storage_script)
                restored_any = True
            except Exception as exc:
                logger.debug('Could not add storage restore init script to context: %s', exc)
            if self.page is not None:
                try:
                    self.page.add_init_script(script=storage_script)
                except Exception as exc:
                    logger.debug('Could not add storage restore init script to page: %s', exc)
        return restored_any

    def close(self) -> None:
        current_tid = threading.current_thread().ident
        owner_tid = self._owner_thread_id
        if owner_tid is not None and current_tid != owner_tid:
            self._close_requested = True
            self._close_unresolved_reported = False
            logger.warning(
                'browser_session_close called from thread %s but owned by %s — deferring',
                current_tid, owner_tid,
            )
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'browser_session_close_deferred',
                    caller_thread=current_tid,
                    owner_thread=owner_tid,
                )
            except Exception:
                pass
            return
        self._do_close(current_tid)

    def close_if_owner_thread(self) -> bool:
        """Drain a deferred close if called from the owner thread.

        Returns True if the session was closed, False otherwise.
        """
        if not getattr(self, '_close_requested', False):
            return False
        current_tid = threading.current_thread().ident
        owner_tid = self._owner_thread_id
        if owner_tid is not None and current_tid != owner_tid:
            active_thread_ids = {
                thread.ident for thread in threading.enumerate()
                if thread.ident is not None
            }
            if owner_tid not in active_thread_ids and not self._close_unresolved_reported:
                self._close_unresolved_reported = True
                logger.warning(
                    'browser_session_close unresolved: owner thread %s is no longer active',
                    owner_tid,
                )
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace(
                        'browser_session_close_unresolved',
                        caller_thread=current_tid,
                        owner_thread=owner_tid,
                        reason='owner_thread_unavailable',
                    )
                except Exception:
                    pass
            return False
        self._do_close(current_tid)
        return True

    def _do_close(self, caller_tid: int | None) -> None:
        """Perform the actual Playwright teardown on the owner thread."""
        self._close_requested = False
        self._close_unresolved_reported = False
        try:
            self._page = None
            if self._context is not None:
                self._context.close()
                self._context = None
            if self._browser is not None:
                self._browser.close()
                self._browser = None
            if self._pw is not None:
                self._pw.stop()
                self._pw = None
            self._owner_thread_id = None
        except Exception as exc:
            logger.warning('Error closing browser session: %s', exc)
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'browser_session_close_unresolved',
                    error=str(exc),
                    caller_thread=caller_tid,
                    reason='exception_during_close',
                )
            except Exception:
                pass
