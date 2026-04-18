from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import BrowserProfileConfig, PersistStrategy
from iabv_v15.services.capture.browser_session_controller import (
    BrowserSessionController,
    _build_storage_seed_script,
)


class _FakeContext:
    def __init__(self) -> None:
        self.cookies: list[dict] = []
        self.init_scripts: list[str] = []
        self.pages: list[object] = []

    def add_cookies(self, cookies) -> None:
        self.cookies.extend(cookies)

    def add_init_script(self, *, script: str) -> None:
        self.init_scripts.append(script)


class _FakePage:
    def __init__(self) -> None:
        self.init_scripts: list[str] = []

    def add_init_script(self, *, script: str) -> None:
        self.init_scripts.append(script)


class _TrackedPage:
    def __init__(self, *, closed: bool = False) -> None:
        self._closed = closed

    def is_closed(self) -> bool:
        return self._closed


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_browser_session_controller_hides_automation_banner_by_default() -> None:
    controller = BrowserSessionController(user_data_dir='profile', storage_state_path='state.json', headless=True)

    assert '--enable-automation' in controller.ignore_default_args
    assert '--disable-infobars' in controller.launch_args
    assert '--start-maximized' in controller.launch_args
    assert controller.chromium_sandbox is True


def test_build_storage_seed_script_embeds_origin_local_storage() -> None:
    script = _build_storage_seed_script(
        {
            'origins': [
                {
                    'origin': 'https://example.com',
                    'localStorage': [{'name': 'token', 'value': 'abc'}],
                }
            ]
        }
    )

    assert 'https://example.com' in script
    assert 'window.localStorage.setItem' in script
    assert 'token' in script


def test_browser_session_controller_restores_storage_state_for_persistent_profile() -> None:
    root = _workspace('browser_restore_state')
    state_path = root / 'state.json'
    payload = {
        'cookies': [
            {
                'name': 'session',
                'value': 'secret-cookie',
                'domain': 'example.com',
                'path': '/',
                'expires': -1,
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax',
            }
        ],
        'origins': [
            {
                'origin': 'https://example.com',
                'localStorage': [{'name': 'token', 'value': 'abc'}],
            }
        ],
    }
    state_path.write_text(json.dumps(payload), encoding='utf-8')

    controller = BrowserSessionController(
        user_data_dir='profile',
        storage_state_path=str(state_path),
        headless=True,
    )
    fake_context = _FakeContext()
    fake_page = _FakePage()
    controller._context = fake_context
    controller._page = fake_page

    restored = controller.restore_storage_state()

    assert restored is True
    assert fake_context.cookies[0]['name'] == 'session'
    assert fake_context.init_scripts
    assert fake_page.init_scripts


def test_browser_session_controller_uses_live_context_page_when_cached_one_is_closed() -> None:
    controller = BrowserSessionController(user_data_dir='profile', storage_state_path='state.json', headless=True)
    closed_page = _TrackedPage(closed=True)
    open_page = _TrackedPage(closed=False)
    fake_context = _FakeContext()
    fake_context.pages = [closed_page, open_page]
    controller._context = fake_context
    controller._page = closed_page

    assert controller.page is open_page


def test_browser_session_controller_adopt_page_updates_active_page() -> None:
    controller = BrowserSessionController(user_data_dir='profile', storage_state_path='state.json', headless=True)
    adopted = _TrackedPage(closed=False)

    controller.adopt_page(adopted)

    assert controller.page is adopted


def test_browser_session_controller_uses_storage_state_only_without_user_data_dir() -> None:
    controller = BrowserSessionController()
    controller.configure(
        BrowserProfileConfig(
            profile_id='state_generic_web',
            site_id='generic_web',
            channel='chrome',
            user_data_dir=None,
            storage_state_path='state.json',
            persist_strategy=PersistStrategy.STORAGE_STATE_ONLY,
            headless=True,
        )
    )

    assert controller.user_data_dir is None
    assert str(controller.storage_state_path).endswith('state.json')
