from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.infra import startup_timeline as timeline_mod
from iabv_v15.infra.startup_timeline import StartupTimeline


class _Tracer:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def trace(self, kind: str, **data):
        self.events.append((kind, data))
        return {'kind': kind, 'data': data}


class _Timeline:
    def __init__(self) -> None:
        self.marks: list[tuple[str, dict]] = []

    def mark(self, phase: str, **extra):
        self.marks.append((phase, extra))
        return {'phase': phase, 'extra': extra}


class _Watchdog:
    def __init__(self) -> None:
        self.active_calls: list[bool] = []

    def set_window_active(self, value: bool) -> None:
        self.active_calls.append(value)


def _bootstrap_stub() -> AppBootstrap:
    bs = AppBootstrap.__new__(AppBootstrap)
    bs._timeline = _Timeline()
    bs._tracer = _Tracer()
    bs._window_lifecycle_recent = []
    bs._window_lifecycle_last = {}
    bs._window_lifecycle_storm_until = 0.0
    bs._window_lifecycle_last_guard_trace = 0.0
    bs._own_window_offscreen_last_trace = 0.0
    bs._main_win = None
    bs.ui_heartbeat_watchdog = _Watchdog()
    bs.control_center_viewmodel = None
    return bs


def test_duplicate_active_changed_is_coalesced_but_watchdog_updates() -> None:
    bs = _bootstrap_stub()

    bs._on_window_lifecycle('activeChanged', active=True)
    bs._on_window_lifecycle('activeChanged', active=True)

    assert [m[0] for m in bs._timeline.marks] == ['window_activeChanged']
    assert bs.ui_heartbeat_watchdog.active_calls == [True, True]
    assert any(
        kind == 'window_lifecycle_storm_guarded'
        and data['reason'] == 'duplicate_coalesced'
        for kind, data in bs._tracer.events
    )


def test_window_lifecycle_storm_guard_drops_timeline_marks() -> None:
    bs = _bootstrap_stub()

    for _ in range(AppBootstrap._WINDOW_LIFECYCLE_STORM_LIMIT + 1):
        bs._on_window_lifecycle('closing')

    assert len(bs._timeline.marks) == AppBootstrap._WINDOW_LIFECYCLE_STORM_LIMIT
    assert any(
        kind == 'window_lifecycle_storm_guarded'
        and data['reason'] == 'storm_guarded'
        for kind, data in bs._tracer.events
    )


def test_own_window_offscreen_is_traced_from_window_rect() -> None:
    bs = _bootstrap_stub()
    bs._main_win = SimpleNamespace(
        winId=lambda: 123,
        isVisible=lambda: True,
        x=lambda: -32000,
        y=lambda: -32000,
        width=lambda: 1543,
        height=lambda: 1022,
    )

    bs._on_window_lifecycle('visibleChanged', visible=True)

    assert bs._timeline.marks[0][1]['rect']['left'] == -32000
    assert any(kind == 'own_window_offscreen' for kind, _data in bs._tracer.events)


def test_startup_timeline_rate_limits_window_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    info = MagicMock()
    monkeypatch.setattr(timeline_mod.logger, 'info', info)
    tl = StartupTimeline()

    tl.mark('window_activeChanged', active=True)
    tl.mark('window_activeChanged', active=False)
    tl.mark('non_window_phase')

    assert info.call_count == 2
    assert info.call_args_list[-1].args[0].startswith('startup_timeline %s')
    assert info.call_args_list[-1].args[1] == 'non_window_phase'


def test_slow_timeline_mark_emits_runtime_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = _Tracer()
    monkeypatch.setattr(
        'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        lambda: tracer,
    )
    tl = StartupTimeline()

    def slow_append(_event):
        import time
        time.sleep(0.11)

    monkeypatch.setattr(tl, '_append_jsonl', slow_append)
    tl.log_dir = timeline_mod.Path('.')
    tl.mark('slow_phase')

    assert any(kind == 'timeline_mark_slow' for kind, _data in tracer.events)


def test_auto_provision_prepares_secret_link_without_visible_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from iabv_v15.services import auto_correction_engine as ace

    opened: list[str] = []
    monkeypatch.delenv('IABV_ALLOW_VISIBLE_SECRET_BROWSER', raising=False)
    monkeypatch.setattr('webbrowser.open', lambda url: opened.append(url) or True)

    result = ace.auto_provision_missing_secrets({
        'account_scan': {'secrets': {'missing': ['GITHUB_TOKEN']}},
    })

    assert opened == []
    assert result['opened_count'] == 0
    assert result['provisions'][0]['visible_browser_suppressed'] is True
    assert 'no abrio Chrome' in result['user_action']


def test_auto_provision_visible_browser_requires_user_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from iabv_v15.services import auto_correction_engine as ace

    opened: list[str] = []
    monkeypatch.delenv('IABV_ALLOW_VISIBLE_SECRET_BROWSER', raising=False)
    monkeypatch.setattr('webbrowser.open', lambda url: opened.append(url) or True)

    result = ace.auto_provision_missing_secrets({
        'user_initiated': True,
        'account_scan': {'secrets': {'missing': ['GITHUB_TOKEN']}},
    })

    assert opened and 'github.com/settings/tokens' in opened[0]
    assert result['opened_count'] == 1


def test_common_sense_cloud_key_provision_does_not_open_browser_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from iabv_v15.services.common_sense_engine import _exec_provision_cloud_key

    opened: list[str] = []
    monkeypatch.delenv('IABV_ALLOW_VISIBLE_SECRET_BROWSER', raising=False)
    monkeypatch.setattr('webbrowser.open', lambda url: opened.append(url) or True)

    result = _exec_provision_cloud_key({'id': 'groq_key_missing'})

    assert opened == []
    assert result['browser_opened'] is False
    assert 'no abrio Chrome' in result['user_action']
