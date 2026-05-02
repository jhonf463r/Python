"""Tests for Fix 20 — Startup Acceleration.

Verifies:
- Early splash close logic
- processEvents yield helper
- CommonSense rule for splash_early_close
- QML loading indicator presence in Main.qml
- Updated PlatformPendingQueue with 4 COMPLETED tasks
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.services.common_sense_engine import INFERENCE_RULES
from iabv_v15.services.auto_correction_engine import _ACTION_HANDLERS


class TestFix20CommonSense:
    """Verify the new CommonSense rule for early splash close."""

    def test_splash_closed_before_shell_ready_rule_exists(self):
        rule_ids = [r['id'] for r in INFERENCE_RULES]
        assert 'splash_closed_before_shell_ready' in rule_ids

    def test_rule_premises(self):
        rule = next(r for r in INFERENCE_RULES if r['id'] == 'splash_closed_before_shell_ready')
        assert 'splash_early_close_used' in rule['premises']

    def test_rule_action_has_handler(self):
        rule = next(r for r in INFERENCE_RULES if r['id'] == 'splash_closed_before_shell_ready')
        assert rule['action'] in _ACTION_HANDLERS

    def test_log_incubation_time_handler_exists(self):
        assert 'log_incubation_time' in _ACTION_HANDLERS


class TestFix20QMLLoadingIndicator:
    """Verify the QML loading indicator exists in Main.qml."""

    def test_main_qml_has_loading_indicator(self):
        qml_path = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'Main.qml'
        content = qml_path.read_text(encoding='utf-8')
        assert 'Cargando IABV...' in content
        assert 'BusyIndicator' in content

    def test_loading_indicator_visibility_binding(self):
        qml_path = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'Main.qml'
        content = qml_path.read_text(encoding='utf-8')
        assert 'mainShellLoader.status !== Loader.Ready' in content


class TestFix20YieldHelper:
    """Verify the _yield_to_event_loop static method exists."""

    def test_yield_method_exists(self):
        from iabv_v15.bootstrap import AppBootstrap
        assert hasattr(AppBootstrap, '_yield_to_event_loop')
        assert callable(AppBootstrap._yield_to_event_loop)

    def test_yield_safe_without_qt(self):
        """_yield_to_event_loop should not crash without QGuiApplication."""
        from iabv_v15.bootstrap import AppBootstrap
        # Should be a no-op when no app instance exists
        AppBootstrap._yield_to_event_loop()


class TestFix20PlatformPendingQueueUpdated:
    """Verify Fix 21 toast task is marked COMPLETED in the canonical list."""

    def test_toast_task_completed(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS
        task = next(t for t in _WINDOWS_INTEGRATION_TASKS if t['id'] == 'win_toast_notifications')
        assert task['status'] == 'COMPLETED'

    def test_four_tasks_completed_total(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS
        completed = [t for t in _WINDOWS_INTEGRATION_TASKS if t['status'] == 'COMPLETED']
        assert len(completed) == 4  # systray, clipboard, dpi, toast

    def test_remaining_pending_count(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS
        non_completed = [t for t in _WINDOWS_INTEGRATION_TASKS if t['status'] != 'COMPLETED']
        assert len(non_completed) == 5  # 5 remaining (autostart, power, session, scheduler, watcher)

    def test_total_tasks_unchanged(self):
        from iabv_v15.services.evolution.platform_pending_queue import _WINDOWS_INTEGRATION_TASKS
        assert len(_WINDOWS_INTEGRATION_TASKS) == 9


class TestFix20Integration:
    """Integration checks for Fix 20 + Fix 21 together."""

    def test_toast_bridge_importable(self):
        from iabv_v15.services.platform.win_toast_bridge import WinToastBridge
        bridge = WinToastBridge()
        assert bridge is not None

    def test_all_platform_bridges_importable(self):
        from iabv_v15.services.platform.win_systray_bridge import WinSystrayBridge
        from iabv_v15.services.platform.win_clipboard_bridge import WinClipboardBridge
        from iabv_v15.services.platform.win_toast_bridge import WinToastBridge
        assert WinSystrayBridge is not None
        assert WinClipboardBridge is not None
        assert WinToastBridge is not None

    def test_bootstrap_has_early_splash_close_code(self):
        """Verify bootstrap.py contains the early splash close logic."""
        bootstrap_path = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'bootstrap.py'
        content = bootstrap_path.read_text(encoding='utf-8')
        assert 'splash_early_close' in content
        assert 'populate_ui_early_close' in content

    def test_bootstrap_has_yield_calls(self):
        """Verify bootstrap.py contains processEvents yield calls."""
        bootstrap_path = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'bootstrap.py'
        content = bootstrap_path.read_text(encoding='utf-8')
        assert '_yield_to_event_loop' in content
        assert content.count('_yield_to_event_loop()') >= 5
