"""Tests for deferredSetupActive end-to-end propagation.

Verifies that ``MainWindowBridge.deferredSetupActive`` is set to True
before the background thread starts and cleared to False when the
deferred post-window setup completes.
"""
from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_global_timeline():
    from iabv_v15.infra.startup_timeline import reset_global_timeline_for_tests
    reset_global_timeline_for_tests()
    yield
    reset_global_timeline_for_tests()


def test_bridge_deferred_setup_active_default_false() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge
    bridge = MainWindowBridge('Test', '/tmp/test')
    assert bridge.get_deferred_setup_active() is False


def test_bridge_deferred_setup_active_set_and_clear() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge
    bridge = MainWindowBridge('Test', '/tmp/test')
    signals: list[bool] = []
    bridge.deferredSetupActiveChanged.connect(lambda: signals.append(bridge.get_deferred_setup_active()))

    bridge.set_deferred_setup_active(True)
    assert bridge.get_deferred_setup_active() is True
    assert len(signals) == 1
    assert signals[-1] is True

    bridge.set_deferred_setup_active(False)
    assert bridge.get_deferred_setup_active() is False
    assert len(signals) == 2
    assert signals[-1] is False


def test_bridge_deferred_setup_active_no_signal_on_same_value() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge
    bridge = MainWindowBridge('Test', '/tmp/test')
    signals: list[bool] = []
    bridge.deferredSetupActiveChanged.connect(lambda: signals.append(True))

    bridge.set_deferred_setup_active(False)
    assert len(signals) == 0, 'No signal when value unchanged'


def test_deferred_post_window_setup_sets_bridge_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge
    bridge = MainWindowBridge('Test', str(tmp_path))
    bootstrap.main_window_bridge = bridge

    assert bridge.get_deferred_setup_active() is False

    bootstrap._tool_availability_logged = False
    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._run_deferred_post_window_setup()

    assert bridge.get_deferred_setup_active() is True, (
        'Bridge must be active immediately after scheduling the deferred setup'
    )

    for t in threading.enumerate():
        if t.name == 'iabv-deferred-post-window' and t.is_alive():
            t.join(timeout=5)

    assert bridge.get_deferred_setup_active() is False, (
        'Bridge must be cleared after the deferred setup thread completes'
    )


def test_deferred_post_window_setup_without_bridge_does_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    bootstrap.main_window_bridge = None
    bootstrap._tool_availability_logged = False

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._run_deferred_post_window_setup()

    for t in threading.enumerate():
        if t.name == 'iabv-deferred-post-window' and t.is_alive():
            t.join(timeout=5)

    assert bootstrap._tool_availability_logged is True
