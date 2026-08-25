"""Tests for Brecha 1.2 — Startup pageLoader freeze optimization.

Since PySide6/QML runtime is not available in CI, these tests verify
the structural properties of the QML files that guarantee the optimization:
- DashboardPage loads first (synchronous, fast)
- Secondary pages are deferred (asynchronous, lazy)
- page_loader_ready fires at the right time
- Splash closes after main page ready
- Startup timeline phases are recorded
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml'
MAIN_QML = QML_DIR / 'Main.qml'
PAGES_DIR = QML_DIR / 'pages'


@pytest.fixture
def main_qml_content() -> str:
    return MAIN_QML.read_text(encoding='utf-8')


class TestMainPageLoadsFirst:
    """DashboardPage is the active page at startup and loads synchronously."""

    def test_default_route_is_dashboard(self, main_qml_content: str):
        # routeSource default (fallback) returns DashboardPage
        assert 'return Qt.resolvedUrl("pages/DashboardPage.qml")' in main_qml_content

    def test_initial_page_loaded_flag_starts_false(self, main_qml_content: str):
        # initialPageLoaded starts false → asynchronous: false for first load
        assert 'property bool initialPageLoaded: false' in main_qml_content

    def test_pageloader_sync_on_first_load(self, main_qml_content: str):
        # asynchronous is bound to parent.initialPageLoaded (false initially)
        assert 'asynchronous: parent.initialPageLoaded' in main_qml_content


class TestSecondaryPagesDeferred:
    """Heavy pages are preloaded asynchronously AFTER initial page ready."""

    def test_preloaders_exist_for_heavy_pages(self, main_qml_content: str):
        assert 'controlPreloader' in main_qml_content
        assert 'evolutionPreloader' in main_qml_content
        assert 'capturePreloader' in main_qml_content

    def test_preloaders_are_async(self, main_qml_content: str):
        # Each preloader must have asynchronous: true
        preloader_blocks = re.findall(
            r'(Loader\s*\{[^}]*?id:\s*(?:control|evolution|capture)Preloader[^}]*?\})',
            main_qml_content,
            re.DOTALL,
        )
        assert len(preloader_blocks) >= 3
        for block in preloader_blocks:
            assert 'asynchronous: true' in block

    def test_preloaders_start_inactive(self, main_qml_content: str):
        # All preloaders must start with active: false
        preloader_blocks = re.findall(
            r'(Loader\s*\{[^}]*?id:\s*(?:control|evolution|capture)Preloader[^}]*?\})',
            main_qml_content,
            re.DOTALL,
        )
        assert len(preloader_blocks) >= 3
        for block in preloader_blocks:
            assert 'active: false' in block

    def test_preload_triggered_after_page_ready(self, main_qml_content: str):
        # secondaryPreloadKickoff starts after page_loader_ready
        assert 'secondaryPreloadKickoff.start()' in main_qml_content


class TestPageLoaderReadyEmittedBeforeTimeout:
    """page_loader_ready fires as soon as DashboardPage is ready (<5s target)."""

    def test_page_loader_ready_signal_on_ready_status(self, main_qml_content: str):
        # signal_page_loader_ready() called when status === Loader.Ready
        pattern = r'if\s*\(status\s*===\s*Loader\.Ready.*?signal_page_loader_ready'
        assert re.search(pattern, main_qml_content, re.DOTALL)

    def test_dashboard_page_is_lightweight(self):
        """DashboardPage must be < 300 lines to load fast."""
        dashboard = PAGES_DIR / 'DashboardPage.qml'
        lines = dashboard.read_text(encoding='utf-8').splitlines()
        assert len(lines) < 300, f'DashboardPage has {len(lines)} lines (should be < 300)'


class TestAsynchronousLoaderFlag:
    """After initial load, pageLoader switches to asynchronous mode."""

    def test_async_after_initial_page(self, main_qml_content: str):
        # asynchronous bound to initialPageLoaded which becomes true after first Ready
        assert 'parent.initialPageLoaded = true' in main_qml_content
        assert 'asynchronous: parent.initialPageLoaded' in main_qml_content

    def test_secondary_pages_are_heavy(self):
        """Verify that deferred pages are indeed heavy (>500 lines)."""
        heavy_pages = ['EvolutionCenterPage.qml', 'CaptureStudioPage.qml', 'ControlCenterPage.qml']
        for page_name in heavy_pages:
            page = PAGES_DIR / page_name
            lines = page.read_text(encoding='utf-8').splitlines()
            assert len(lines) > 500, f'{page_name} has {len(lines)} lines (expected > 500)'


class TestSplashClosesAfterMainPageReady:
    """Bootstrap closes splash after page_loader_ready (the first visible page)."""

    def test_bootstrap_handles_page_loader_ready(self):
        bootstrap = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'bootstrap.py'
        content = bootstrap.read_text(encoding='utf-8')
        # _handle_page_loader_ready exists and sets _shell_loader_ready_handled
        assert '_handle_page_loader_ready' in content
        assert '_fire_splash_ready_and_raise_main' in content

    def test_page_loader_ready_prevents_fallback(self):
        """page_loader_ready sets _shell_loader_ready_handled=True, preventing fallback."""
        bootstrap = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'bootstrap.py'
        content = bootstrap.read_text(encoding='utf-8')
        # In _handle_page_loader_ready: sets _shell_loader_ready_handled
        assert '_page_loader_ready_received = True' in content
        assert '_shell_loader_ready_handled = True' in content


class TestStartupTimelinePhasesRecorded:
    """Bootstrap records all phases in the startup timeline."""

    def test_timeline_marks_exist(self):
        bootstrap = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'bootstrap.py'
        content = bootstrap.read_text(encoding='utf-8')
        required_marks = [
            'page_loader_ready',
            'shell_loader_ready',
            'main_qml_completed',
        ]
        for mark in required_marks:
            assert f"'{mark}'" in content or f'"{mark}"' in content, \
                f'Timeline mark {mark!r} not found in bootstrap.py'

    def test_main_window_bridge_emits_all_signals(self):
        bridge = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'ui' / 'controllers' / 'main_window_bridge.py'
        content = bridge.read_text(encoding='utf-8')
        signals = ['shellLoaderReady', 'pageLoaderReady', 'mainQmlCompleted']
        for signal in signals:
            assert signal in content, f'Signal {signal!r} not found in MainWindowBridge'
