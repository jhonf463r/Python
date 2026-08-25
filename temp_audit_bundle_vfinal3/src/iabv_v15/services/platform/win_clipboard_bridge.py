"""Windows Clipboard bridge via ctypes (Fix 19b).

Provides low-level clipboard read/write using the Win32 API directly
through ``ctypes``.  This bridge is complementary to the Qt clipboard
used by the UI — it allows non-UI services (background workers,
autonomous tasks) to interact with the system clipboard without
requiring a ``QGuiApplication`` instance.

The bridge is safe to construct on non-Windows platforms — all methods
return safe defaults or raise ``ClipboardUnavailableError``.

Capabilities:
- ``get_text()``  — read CF_UNICODETEXT from clipboard
- ``set_text(text)`` — write CF_UNICODETEXT to clipboard
- ``has_text()``  — check if clipboard contains text
- ``is_available`` — whether Win32 clipboard API is accessible
"""

from __future__ import annotations

import ctypes
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


class ClipboardUnavailableError(RuntimeError):
    """Raised when clipboard operations are attempted on non-Windows."""


class WinClipboardBridge:
    """Win32 clipboard read/write via ctypes."""

    def __init__(self) -> None:
        self._user32: Any = None
        self._kernel32: Any = None
        if os.name == 'nt':
            try:
                self._user32 = ctypes.windll.user32  # type: ignore[attr-defined]
                self._kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            except Exception:
                logger.warning('clipboard_bridge: failed to load user32/kernel32')

    @property
    def is_available(self) -> bool:
        if self._user32 is None:
            return False
        try:
            if self._user32.OpenClipboard(0):
                self._user32.CloseClipboard()
                return True
        except Exception:
            pass
        return False

    def get_text(self) -> str:
        """Read Unicode text from the clipboard.

        Returns empty string if clipboard is empty or contains no text.
        Raises ``ClipboardUnavailableError`` on non-Windows.
        """
        if self._user32 is None:
            raise ClipboardUnavailableError('Win32 clipboard not available')

        if not self._user32.OpenClipboard(0):
            logger.debug('clipboard_bridge.get_text: OpenClipboard failed')
            return ''
        try:
            handle = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ''
            self._kernel32.GlobalLock.restype = ctypes.c_void_p
            ptr = self._kernel32.GlobalLock(handle)
            if not ptr:
                return ''
            try:
                return ctypes.wstring_at(ptr)
            finally:
                self._kernel32.GlobalUnlock(handle)
        except Exception:
            logger.exception('clipboard_bridge.get_text: error reading clipboard')
            return ''
        finally:
            self._user32.CloseClipboard()

    def set_text(self, text: str) -> bool:
        """Write Unicode text to the clipboard.  Returns True on success."""
        if self._user32 is None:
            raise ClipboardUnavailableError('Win32 clipboard not available')

        if not self._user32.OpenClipboard(0):
            logger.debug('clipboard_bridge.set_text: OpenClipboard failed')
            return False
        try:
            self._user32.EmptyClipboard()
            encoded = text.encode('utf-16-le') + b'\x00\x00'
            h_mem = self._kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
            if not h_mem:
                return False
            self._kernel32.GlobalLock.restype = ctypes.c_void_p
            ptr = self._kernel32.GlobalLock(h_mem)
            if not ptr:
                self._kernel32.GlobalFree(h_mem)
                return False
            ctypes.memmove(ptr, encoded, len(encoded))
            self._kernel32.GlobalUnlock(h_mem)
            result = self._user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            return bool(result)
        except Exception:
            logger.exception('clipboard_bridge.set_text: error writing clipboard')
            return False
        finally:
            self._user32.CloseClipboard()

    def has_text(self) -> bool:
        """Check if clipboard currently contains Unicode text."""
        if self._user32 is None:
            return False
        try:
            return bool(self._user32.IsClipboardFormatAvailable(CF_UNICODETEXT))
        except Exception:
            return False

    def snapshot(self) -> dict[str, Any]:
        """Return a machine-readable snapshot of the bridge state."""
        return {
            'available': self.is_available,
            'has_text': self.has_text(),
            'platform': 'windows' if os.name == 'nt' else os.name,
        }
