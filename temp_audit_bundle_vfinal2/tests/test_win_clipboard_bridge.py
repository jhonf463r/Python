"""Tests for WinClipboardBridge (Fix 19b).

On Linux/macOS the bridge is safe but ``is_available`` returns False
and read/write raise ``ClipboardUnavailableError``.
Windows-only tests are skipped on non-Windows.
"""

from __future__ import annotations

import os
import pytest

from iabv_v15.services.platform.win_clipboard_bridge import (
    WinClipboardBridge,
    ClipboardUnavailableError,
)


class TestWinClipboardBridgeCrossPlatform:
    """Tests that run on any platform."""

    def test_construction(self):
        bridge = WinClipboardBridge()
        if os.name != 'nt':
            assert bridge._user32 is None
            assert bridge._kernel32 is None

    def test_is_available_non_windows(self):
        if os.name != 'nt':
            bridge = WinClipboardBridge()
            assert bridge.is_available is False

    def test_has_text_non_windows(self):
        if os.name != 'nt':
            bridge = WinClipboardBridge()
            assert bridge.has_text() is False

    def test_get_text_raises_on_non_windows(self):
        if os.name != 'nt':
            bridge = WinClipboardBridge()
            with pytest.raises(ClipboardUnavailableError):
                bridge.get_text()

    def test_set_text_raises_on_non_windows(self):
        if os.name != 'nt':
            bridge = WinClipboardBridge()
            with pytest.raises(ClipboardUnavailableError):
                bridge.set_text('hello')

    def test_snapshot_non_windows(self):
        bridge = WinClipboardBridge()
        snap = bridge.snapshot()
        assert 'available' in snap
        assert 'has_text' in snap
        assert 'platform' in snap
        if os.name != 'nt':
            assert snap['available'] is False


class TestWinClipboardBridgeWindows:
    """Tests that only run on Windows."""

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_is_available(self):
        bridge = WinClipboardBridge()
        assert bridge.is_available is True

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_set_and_get_text_roundtrip(self):
        bridge = WinClipboardBridge()
        test_text = 'IABV clipboard test \u2014 Fix 19b'
        assert bridge.set_text(test_text) is True
        result = bridge.get_text()
        assert result == test_text

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_has_text_after_set(self):
        bridge = WinClipboardBridge()
        bridge.set_text('test')
        assert bridge.has_text() is True

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_snapshot_windows(self):
        bridge = WinClipboardBridge()
        snap = bridge.snapshot()
        assert snap['available'] is True
        assert snap['platform'] == 'windows'

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_unicode_roundtrip(self):
        bridge = WinClipboardBridge()
        test_text = 'IABV \u2014 metacognici\u00f3n \ud83e\udde0 v1.5'
        bridge.set_text(test_text)
        result = bridge.get_text()
        assert result == test_text

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_empty_clipboard(self):
        bridge = WinClipboardBridge()
        bridge.set_text('')
        result = bridge.get_text()
        assert result == ''
