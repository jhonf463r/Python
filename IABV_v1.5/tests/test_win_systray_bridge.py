"""Tests for WinSystrayBridge (Fix 19a).

On Linux/macOS the bridge is safe but returns ``is_available=False``.
Windows-only tests are skipped on non-Windows.
"""

from __future__ import annotations

import os
import pytest

from iabv_v15.services.platform.win_systray_bridge import (
    WinSystrayBridge,
    _find_app_icon,
    _TRAY_AVAILABLE,
)


class TestWinSystrayBridgeCrossPlatform:
    """Tests that run on any platform."""

    def test_construction(self):
        bridge = WinSystrayBridge()
        assert bridge._app_name == 'IABV v1.5'
        assert bridge._tray is None
        assert bridge.visible is False

    def test_custom_app_name(self):
        bridge = WinSystrayBridge(app_name='TestApp')
        assert bridge._app_name == 'TestApp'

    def test_snapshot_not_shown(self):
        bridge = WinSystrayBridge()
        snap = bridge.snapshot()
        assert 'available' in snap
        assert snap['visible'] is False
        assert snap['app_name'] == 'IABV v1.5'
        assert snap['has_menu'] is False

    def test_hide_when_not_shown(self):
        bridge = WinSystrayBridge()
        bridge.hide()
        assert bridge.visible is False

    def test_set_tooltip_when_not_shown(self):
        bridge = WinSystrayBridge()
        bridge.set_tooltip('test')

    def test_show_message_when_not_shown(self):
        bridge = WinSystrayBridge()
        result = bridge.show_message('title', 'body')
        assert result is False

    def test_find_app_icon_returns_string(self):
        result = _find_app_icon()
        assert isinstance(result, str)

    @pytest.mark.skipif(os.name != 'nt', reason='Non-Windows: tray not available')
    def test_is_available_non_windows(self):
        bridge = WinSystrayBridge()
        assert isinstance(bridge.is_available, bool)

    def test_is_available_reflects_platform(self):
        bridge = WinSystrayBridge()
        if os.name != 'nt':
            assert bridge.is_available is False


class TestWinSystrayBridgeWindows:
    """Tests that only run on Windows with PySide6."""

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_show_returns_bool(self):
        bridge = WinSystrayBridge()
        result = bridge.show()
        assert isinstance(result, bool)
        bridge.hide()

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_snapshot_after_show(self):
        bridge = WinSystrayBridge()
        shown = bridge.show()
        snap = bridge.snapshot()
        assert snap['visible'] is shown
        assert snap['has_menu'] is shown
        bridge.hide()
        snap = bridge.snapshot()
        assert snap['visible'] is False

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_show_message_after_show(self):
        bridge = WinSystrayBridge()
        shown = bridge.show()
        result = bridge.show_message('Test', 'Hello from test', duration_ms=1000)
        assert result is shown
        bridge.hide()

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_set_tooltip_after_show(self):
        bridge = WinSystrayBridge()
        bridge.show()
        bridge.set_tooltip('Updated tooltip')
        bridge.hide()
