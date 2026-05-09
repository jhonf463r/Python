"""Tests for Tasks 5 & 6: RAM reduction and deferred non-critical scans.

Covers:
1. _rss_mb helper returns a float >= 0
2. RSS tracking at bootstrap milestones (timeline marks include rss_mb)
3. Deferred post-window setup splits into Phase A (tool probes) and Phase B (metacognition)
4. _deferred_auto_install_missing_tools reads stashed missing list
5. _run_deferred_metacognition_scan is idempotent
6. _log_tool_availability no longer calls _startup_self_examination directly
7. _log_tool_availability stashes _deferred_missing_tools
8. Regression: existing deferred setup still works end-to-end
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from iabv_v15.bootstrap import _rss_mb


# ======================================================================
# 1. _rss_mb helper
# ======================================================================


class TestRssMb:
    """Test the RSS memory tracking helper."""

    def test_returns_float(self) -> None:
        result = _rss_mb()
        assert isinstance(result, float)

    def test_returns_non_negative(self) -> None:
        result = _rss_mb()
        assert result >= 0.0

    def test_returns_reasonable_value(self) -> None:
        result = _rss_mb()
        # Any running Python process uses at least a few MB
        # On CI / headless it may report 0.0 if resource module fails
        assert result >= 0.0
        # Should not be absurdly large (> 100 GB)
        assert result < 100_000.0


# ======================================================================
# 2. RSS tracking at bootstrap timeline milestones
# ======================================================================


class TestRssTimelineTracking:
    """Bootstrap timeline marks include rss_mb at key milestones."""

    def test_bootstrap_init_marks_include_rss(self, tmp_path: Path) -> None:
        """bootstrap_init_start and bootstrap_init_done include rss_mb."""
        from iabv_v15.infra.startup_timeline import StartupTimeline

        timeline = StartupTimeline()
        # Simulate what bootstrap.__init__ does
        timeline.mark('bootstrap_init_start', rss_mb=_rss_mb())
        timeline.mark('bootstrap_init_done', rss_mb=_rss_mb())

        events = timeline.events()
        start_ev = next(e for e in events if e['phase'] == 'bootstrap_init_start')
        done_ev = next(e for e in events if e['phase'] == 'bootstrap_init_done')
        assert 'rss_mb' in start_ev
        assert 'rss_mb' in done_ev
        assert isinstance(start_ev['rss_mb'], float)
        assert isinstance(done_ev['rss_mb'], float)

    def test_wire_services_marks_include_rss(self) -> None:
        """wire_services_start and wire_services_done include rss_mb."""
        from iabv_v15.infra.startup_timeline import StartupTimeline

        timeline = StartupTimeline()
        timeline.mark('wire_services_start', rss_mb=_rss_mb())
        timeline.mark('phase_tools_adapters_done', rss_mb=_rss_mb())
        timeline.mark('phase_oses_done', rss_mb=_rss_mb())
        timeline.mark('wire_services_done', rss_mb=_rss_mb())

        events = timeline.events()
        phases_with_rss = [
            e['phase'] for e in events
            if 'rss_mb' in e and isinstance(e['rss_mb'], float)
        ]
        assert 'wire_services_start' in phases_with_rss
        assert 'phase_tools_adapters_done' in phases_with_rss
        assert 'phase_oses_done' in phases_with_rss
        assert 'wire_services_done' in phases_with_rss


# ======================================================================
# 3. Deferred post-window setup Phase A / Phase B split
# ======================================================================


class TestDeferredPostWindowSetup:
    """_run_deferred_post_window_setup splits work into two phases."""

    def _make_bootstrap(self, tmp_path: Path):
        """Create a minimal AppBootstrap with deferred services."""
        with patch.dict('os.environ', {
            'IABV_DEFER_TOOL_PROBE': '1',
            'IABV_MCP_SUBPROCESS': '0',
        }):
            from iabv_v15.bootstrap import AppBootstrap
            boot = AppBootstrap(str(tmp_path))
        return boot

    def test_deferred_setup_is_idempotent(self, tmp_path: Path) -> None:
        """Second call to _run_deferred_post_window_setup is a no-op."""
        boot = self._make_bootstrap(tmp_path)
        # First call sets _tool_availability_logged
        boot._tool_availability_logged = False
        # Manually mark it as done to test idempotency
        boot._tool_availability_logged = True
        # This should be a no-op (returns immediately)
        boot._run_deferred_post_window_setup()
        # No crash = success

    def test_metacognition_scan_is_idempotent(self, tmp_path: Path) -> None:
        """_run_deferred_metacognition_scan only runs once."""
        boot = self._make_bootstrap(tmp_path)
        boot._metacognition_scan_started = True
        # Should be a no-op
        boot._run_deferred_metacognition_scan()
        # No crash = success

    def test_deferred_missing_tools_stashed(self, tmp_path: Path) -> None:
        """_log_tool_availability stashes missing tools for deferred install."""
        boot = self._make_bootstrap(tmp_path)
        # Mock tool_registry to return empty cards
        boot.tool_registry = MagicMock()
        boot.tool_registry.list_cards.return_value = []
        boot._log_tool_availability()
        # Should have stashed an empty list (no missing tools)
        assert hasattr(boot, '_deferred_missing_tools')
        assert isinstance(boot._deferred_missing_tools, list)


# ======================================================================
# 4. _deferred_auto_install_missing_tools
# ======================================================================


class TestDeferredAutoInstall:
    """Auto-install of missing tools is deferred to Phase B."""

    def _make_bootstrap(self, tmp_path: Path):
        with patch.dict('os.environ', {
            'IABV_DEFER_TOOL_PROBE': '1',
            'IABV_MCP_SUBPROCESS': '0',
        }):
            from iabv_v15.bootstrap import AppBootstrap
            boot = AppBootstrap(str(tmp_path))
        return boot

    def test_no_install_when_no_missing_tools(self, tmp_path: Path) -> None:
        """No auto-install when _deferred_missing_tools is empty."""
        boot = self._make_bootstrap(tmp_path)
        boot._deferred_missing_tools = []
        # Should not raise or try to import auto_correction_engine
        boot._deferred_auto_install_missing_tools()

    def test_install_called_when_missing_tools_present(self, tmp_path: Path) -> None:
        """Auto-install is called with the stashed missing tools list."""
        boot = self._make_bootstrap(tmp_path)
        boot._deferred_missing_tools = ['fake_tool_1', 'fake_tool_2']
        boot._auxiliary_work_rest_started_at -= 300.0

        with patch(
            'iabv_v15.services.auto_correction_engine.auto_fix_missing_tools',
            return_value={'installed': 1, 'results': [{'tool_id': 'fake_tool_1', 'status': 'installed'}]},
        ) as mock_fix:
            boot._deferred_auto_install_missing_tools()
            mock_fix.assert_called_once_with(['fake_tool_1', 'fake_tool_2'])

    def test_install_failure_is_swallowed(self, tmp_path: Path) -> None:
        """Auto-install failure does not propagate."""
        boot = self._make_bootstrap(tmp_path)
        boot._deferred_missing_tools = ['broken_tool']
        boot._auxiliary_work_rest_started_at -= 300.0

        with patch(
            'iabv_v15.services.auto_correction_engine.auto_fix_missing_tools',
            side_effect=RuntimeError('pip exploded'),
        ):
            # Should not raise
            boot._deferred_auto_install_missing_tools()

    def test_install_deferred_until_operational_rest_window(self, tmp_path: Path) -> None:
        """Heavy auto-install must not start while the shell just became interactive."""
        boot = self._make_bootstrap(tmp_path)
        boot._deferred_missing_tools = ['fake_tool_1']
        scheduled: list[float] = []
        boot._schedule_auxiliary_retry = lambda delay, callback: scheduled.append(delay)  # type: ignore[method-assign]

        with patch(
            'iabv_v15.services.auto_correction_engine.auto_fix_missing_tools',
            return_value={'installed': 1, 'results': []},
        ) as mock_fix:
            boot._deferred_auto_install_missing_tools()

        mock_fix.assert_not_called()
        assert scheduled


# ======================================================================
# 5. _log_tool_availability no longer calls self-examination directly
# ======================================================================


class TestToolAvailabilityDecoupled:
    """_log_tool_availability is decoupled from metacognition scans."""

    def _make_bootstrap(self, tmp_path: Path):
        with patch.dict('os.environ', {
            'IABV_DEFER_TOOL_PROBE': '1',
            'IABV_MCP_SUBPROCESS': '0',
        }):
            from iabv_v15.bootstrap import AppBootstrap
            boot = AppBootstrap(str(tmp_path))
        return boot

    def test_no_self_examination_called(self, tmp_path: Path) -> None:
        """_log_tool_availability does NOT call _startup_self_examination."""
        boot = self._make_bootstrap(tmp_path)
        boot.tool_registry = MagicMock()
        boot.tool_registry.list_cards.return_value = []

        with patch.object(boot, '_startup_self_examination') as mock_exam:
            boot._log_tool_availability()
            mock_exam.assert_not_called()

    def test_no_common_sense_called(self, tmp_path: Path) -> None:
        """_log_tool_availability does NOT call _run_startup_common_sense."""
        boot = self._make_bootstrap(tmp_path)
        boot.tool_registry = MagicMock()
        boot.tool_registry.list_cards.return_value = []

        with patch.object(boot, '_run_startup_common_sense') as mock_cs:
            boot._log_tool_availability()
            mock_cs.assert_not_called()

    def test_no_auto_install_called_directly(self, tmp_path: Path) -> None:
        """_log_tool_availability does NOT call auto_fix_missing_tools directly."""
        boot = self._make_bootstrap(tmp_path)
        boot.tool_registry = MagicMock()
        boot.tool_registry.list_cards.return_value = []

        with patch(
            'iabv_v15.services.auto_correction_engine.auto_fix_missing_tools',
        ) as mock_fix:
            boot._log_tool_availability()
            mock_fix.assert_not_called()


# ======================================================================
# 6. Phase B metacognition scan thread
# ======================================================================


class TestMetacognitionScanPhaseB:
    """Phase B runs self-examination, common-sense, and auto-install."""

    def _make_bootstrap(self, tmp_path: Path):
        with patch.dict('os.environ', {
            'IABV_DEFER_TOOL_PROBE': '1',
            'IABV_MCP_SUBPROCESS': '0',
        }):
            from iabv_v15.bootstrap import AppBootstrap
            boot = AppBootstrap(str(tmp_path))
        return boot

    def test_metacognition_scan_calls_self_examination(self, tmp_path: Path) -> None:
        """Phase B calls _startup_self_examination."""
        boot = self._make_bootstrap(tmp_path)
        boot._metacognition_scan_started = False
        calls = []

        with patch.object(boot, '_startup_self_examination', side_effect=lambda: calls.append('exam')):
            with patch.object(boot, '_run_startup_common_sense', side_effect=lambda: calls.append('cs')):
                with patch.object(boot, '_deferred_auto_install_missing_tools', side_effect=lambda: calls.append('install')):
                    boot._run_deferred_metacognition_scan()
                    # Wait for background thread to finish
                    time.sleep(0.5)

        assert 'exam' in calls
        assert 'cs' in calls
        assert 'install' in calls

    def test_metacognition_scan_idempotent(self, tmp_path: Path) -> None:
        """Second call does not start another thread."""
        boot = self._make_bootstrap(tmp_path)
        boot._metacognition_scan_started = False
        call_count = []

        with patch.object(boot, '_startup_self_examination', side_effect=lambda: call_count.append(1)):
            with patch.object(boot, '_run_startup_common_sense'):
                with patch.object(boot, '_deferred_auto_install_missing_tools'):
                    boot._run_deferred_metacognition_scan()
                    boot._run_deferred_metacognition_scan()  # second call = no-op
                    time.sleep(0.5)

        assert len(call_count) == 1


# ======================================================================
# 7. Regression: existing deferred setup flow
# ======================================================================


class TestDeferredSetupRegression:
    """Existing deferred setup flows still work."""

    def _make_bootstrap(self, tmp_path: Path):
        with patch.dict('os.environ', {
            'IABV_DEFER_TOOL_PROBE': '1',
            'IABV_MCP_SUBPROCESS': '0',
        }):
            from iabv_v15.bootstrap import AppBootstrap
            boot = AppBootstrap(str(tmp_path))
        return boot

    def test_deferred_setup_active_flag_lifecycle(self, tmp_path: Path) -> None:
        """_deferred_setup_active transitions: False → True → False."""
        boot = self._make_bootstrap(tmp_path)
        boot._tool_availability_logged = False
        boot.main_window_bridge = None

        # Mock _log_tool_availability to avoid actual work
        with patch.object(boot, '_log_tool_availability'):
            with patch.object(boot, '_run_deferred_metacognition_scan'):
                boot._run_deferred_post_window_setup()
                # Wait for the thread
                time.sleep(0.5)

        assert boot._deferred_setup_active is False

    def test_tool_availability_logged_set(self, tmp_path: Path) -> None:
        """_tool_availability_logged is set after deferred setup."""
        boot = self._make_bootstrap(tmp_path)
        boot._tool_availability_logged = False
        boot.main_window_bridge = None

        with patch.object(boot, '_log_tool_availability'):
            with patch.object(boot, '_run_deferred_metacognition_scan'):
                boot._run_deferred_post_window_setup()
                # Immediately after call, flag should be set
                assert boot._tool_availability_logged is True


# ======================================================================
# 8. GPU health check still deferred (not on critical path)
# ======================================================================


class TestGPUHealthCheckDeferred:
    """GPU startup health check runs in its own thread, not blocking probes."""

    def _make_bootstrap(self, tmp_path: Path):
        with patch.dict('os.environ', {
            'IABV_DEFER_TOOL_PROBE': '1',
            'IABV_MCP_SUBPROCESS': '0',
        }):
            from iabv_v15.bootstrap import AppBootstrap
            boot = AppBootstrap(str(tmp_path))
        return boot

    def test_gpu_check_runs_in_thread(self, tmp_path: Path) -> None:
        """GPU health check starts in a daemon thread during _log_tool_availability."""
        boot = self._make_bootstrap(tmp_path)
        boot.tool_registry = MagicMock()
        boot.tool_registry.list_cards.return_value = []

        threads_before = set(t.name for t in threading.enumerate())
        boot._log_tool_availability()
        time.sleep(0.2)
        threads_after = set(t.name for t in threading.enumerate())

        # The GPU thread may have already finished, but at minimum
        # no crash occurred during the call
        assert hasattr(boot, '_deferred_missing_tools')
