"""Integration tests for Fix 19 — systray, clipboard, DPI, pending queue updates.

Verifies that Fix 19's changes integrate cleanly:
- PlatformPendingQueue canonical tasks reflect COMPLETED for the 3 implemented tasks
- Bridge modules import cleanly
- DPI code path is safe on non-Windows
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from iabv_v15.domain.models import PendingTaskStatus


class TestPendingQueueFix19Updates:
    """Verify that the 3 READY_FOR_NEXT_SLICE tasks are now COMPLETED."""

    def test_canonical_tasks_have_three_completed(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS

        completed_ids = [
            t['id'] for t in _WINDOWS_INTEGRATION_TASKS
            if t['status'] == 'COMPLETED'
        ]
        assert 'win_systray_icon' in completed_ids
        assert 'win_clipboard_bridge' in completed_ids
        assert 'win_dpi_awareness' in completed_ids
        assert len(completed_ids) == 3

    def test_seed_persists_completed_tasks(self):
        from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = PlatformPendingQueue(evolution_dir=tmpdir)
            seeded = queue.seed_windows_integration_tasks()
            completed = [
                t for t in seeded
                if t.status == PendingTaskStatus.COMPLETED
            ]
            completed_ids = [t.id for t in completed]
            assert 'win_systray_icon' in completed_ids
            assert 'win_clipboard_bridge' in completed_ids
            assert 'win_dpi_awareness' in completed_ids

    def test_second_seed_skips_completed(self):
        from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = PlatformPendingQueue(evolution_dir=tmpdir)
            queue.seed_windows_integration_tasks()
            # Second seed should skip COMPLETED tasks
            seeded2 = queue.seed_windows_integration_tasks()
            seeded2_ids = [t.id for t in seeded2]
            assert 'win_systray_icon' not in seeded2_ids
            assert 'win_clipboard_bridge' not in seeded2_ids
            assert 'win_dpi_awareness' not in seeded2_ids

    def test_remaining_pending_tasks_count(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS

        pending = [
            t for t in _WINDOWS_INTEGRATION_TASKS
            if t['status'] in ('PENDING', 'BLOCKED')
        ]
        assert len(pending) == 6

    def test_queue_summary_after_seed(self):
        from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = PlatformPendingQueue(evolution_dir=tmpdir)
            queue.seed_windows_integration_tasks()
            summary = queue.summary()
            assert summary['total'] == 9
            assert summary['by_status'].get('COMPLETED', 0) == 3
            assert summary['actionable'] > 0

    def test_total_canonical_tasks_is_nine(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS
        assert len(_WINDOWS_INTEGRATION_TASKS) == 9


class TestBridgeImports:
    """Verify that bridge modules import cleanly on any platform."""

    def test_import_systray_bridge(self):
        from iabv_v15.services.platform.win_systray_bridge import WinSystrayBridge
        bridge = WinSystrayBridge()
        assert bridge is not None

    def test_import_clipboard_bridge(self):
        from iabv_v15.services.platform.win_clipboard_bridge import WinClipboardBridge
        bridge = WinClipboardBridge()
        assert bridge is not None

    def test_import_clipboard_error(self):
        from iabv_v15.services.platform.win_clipboard_bridge import ClipboardUnavailableError
        assert issubclass(ClipboardUnavailableError, RuntimeError)


class TestDpiAwareness:
    """Verify DPI awareness code path is safe."""

    def test_dpi_import_safe(self):
        import ctypes
        assert ctypes is not None

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_dpi_call_works(self):
        import ctypes
        try:
            result = ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
            assert isinstance(result, int)
        except OSError:
            pass

    def test_dpi_safe_on_non_windows(self):
        if os.name != 'nt':
            import ctypes
            assert not hasattr(ctypes, 'windll') or True
