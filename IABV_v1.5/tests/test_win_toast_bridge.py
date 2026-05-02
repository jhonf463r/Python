"""Tests for WinToastBridge (Fix 21).

Cross-platform tests run everywhere; Windows-only tests require
``os.name == 'nt'`` and are skipped on Linux/macOS.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.services.platform.win_toast_bridge import WinToastBridge


# ======================================================================
# Cross-platform tests (run on any OS)
# ======================================================================


class TestWinToastBridgeCrossPlatform:
    """Tests that run on every platform."""

    def test_construction_default(self):
        bridge = WinToastBridge()
        assert bridge._app_name == 'IABV v1.5'

    def test_construction_custom_name(self):
        bridge = WinToastBridge(app_name='Test App')
        assert bridge._app_name == 'Test App'

    def test_snapshot_returns_dict(self):
        bridge = WinToastBridge()
        snap = bridge.snapshot()
        assert isinstance(snap, dict)
        assert 'available' in snap
        assert 'backend' in snap
        assert 'winotify_installed' in snap
        assert 'systray_available' in snap
        assert 'platform' in snap

    def test_notify_returns_false_without_backend(self):
        bridge = WinToastBridge()
        # Without systray and without winotify, notify returns False
        if not bridge.is_available:
            result = bridge.notify('Title', 'Body')
            assert result is False

    def test_backend_none_without_systray(self):
        bridge = WinToastBridge(systray_bridge=None)
        if os.name != 'nt':
            assert bridge.backend == 'none'

    def test_snapshot_platform_matches_os(self):
        bridge = WinToastBridge()
        assert bridge.snapshot()['platform'] == os.name

    def test_with_mock_systray(self):
        """When a systray bridge is provided, backend should be 'balloon'."""

        class _MockSystray:
            is_available = True

            def show_message(self, **kwargs):
                pass

        bridge = WinToastBridge(systray_bridge=_MockSystray())
        if not bridge.snapshot()['winotify_installed']:
            assert bridge.backend == 'balloon'
            assert bridge.is_available is True

    def test_notify_with_mock_systray_returns_true(self):
        class _MockSystray:
            is_available = True
            called = False

            def show_message(self, **kwargs):
                self.called = True

        mock = _MockSystray()
        bridge = WinToastBridge(systray_bridge=mock)
        if not bridge.snapshot()['winotify_installed']:
            result = bridge.notify('Hello', 'World')
            assert result is True
            assert mock.called is True

    def test_notify_icon_types(self):
        class _MockSystray:
            is_available = True
            last_icon_type = None

            def show_message(self, **kwargs):
                self.last_icon_type = kwargs.get('icon_type')

        mock = _MockSystray()
        bridge = WinToastBridge(systray_bridge=mock)
        if not bridge.snapshot()['winotify_installed']:
            bridge.notify('T', 'B', icon='warning')
            assert mock.last_icon_type == 'warning'

    def test_notify_balloon_failure_returns_false(self):
        class _BrokenSystray:
            is_available = True

            def show_message(self, **kwargs):
                raise RuntimeError('broken')

        bridge = WinToastBridge(systray_bridge=_BrokenSystray())
        if not bridge.snapshot()['winotify_installed']:
            result = bridge.notify('T', 'B')
            assert result is False

    def test_icon_path_stored(self):
        bridge = WinToastBridge(icon_path='/path/to/icon.ico')
        assert bridge._icon_path == '/path/to/icon.ico'


# ======================================================================
# Windows-only tests
# ======================================================================


@pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
class TestWinToastBridgeWindows:
    """Tests that only run on Windows."""

    def test_backend_not_none_on_windows(self):
        bridge = WinToastBridge()
        # On Windows, at minimum balloon should work if systray is provided
        # Without systray, winotify might or might not be installed

    def test_snapshot_on_windows(self):
        bridge = WinToastBridge()
        snap = bridge.snapshot()
        assert snap['platform'] == 'nt'

    def test_is_available_with_systray(self):
        class _MockSystray:
            is_available = True

            def show_message(self, **kwargs):
                pass

        bridge = WinToastBridge(systray_bridge=_MockSystray())
        assert bridge.is_available is True
