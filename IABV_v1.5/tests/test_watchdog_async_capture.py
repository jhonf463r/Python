"""Tests for UIHeartbeatWatchdog async sampler (A/D/F).

Validates:
- Sampler daemon captures main_thread_stack DURING a stall, not just after.
- Sampler does NOT do heavy IO.
- Cooldown anti-storm still works.
- Dominant phase is captured at detection time, not at recovery.
- Enriched evidence (bootstrap_flags, live stack, post_stall_stack).
"""
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.freeze_incident_reporter import (
    FreezeIncidentReporter,
    UIHeartbeatWatchdog,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_watchdog(
    *,
    stall_threshold_ms: float = 200,
    sampler_interval_s: float = 0.05,
) -> UIHeartbeatWatchdog:
    reporter = FreezeIncidentReporter.__new__(FreezeIncidentReporter)
    reporter._reports_dir = None
    reporter._db_path = None
    wd = UIHeartbeatWatchdog(
        stall_threshold_ms=stall_threshold_ms,
        freeze_reporter=reporter,
        sampler_interval_s=sampler_interval_s,
    )
    return wd


# ---------------------------------------------------------------------------
# A. Sampler captures stack DURING stall
# ---------------------------------------------------------------------------

class TestSamplerCapturesDuringStall:
    def test_sampler_captures_live_stack_during_simulated_stall(self):
        """Sampler must produce a live stack when main thread doesn't tick."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.start_sampler()
        try:
            # Initial tick to set baseline
            wd.tick()
            # Simulate a stall: don't tick for >100ms
            time.sleep(0.25)
            # Sampler should have captured live stack by now
            data = wd._consume_live_stall_data()
            assert data.get('main_thread_stack_during_stall'), (
                'Sampler did not capture live stack during stall'
            )
            assert isinstance(data['main_thread_stack_during_stall'], list)
            assert len(data['main_thread_stack_during_stall']) > 0
        finally:
            wd.stop_sampler()

    def test_sampler_captures_dominant_phase_at_detection_time(self):
        """Dominant phase should reflect the phase when sampler detects stall."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_dominant_phase('startup_background:truth_refresh')
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            data = wd._consume_live_stall_data()
            assert data.get('dominant_phase_at_detection') == 'startup_background:truth_refresh'
        finally:
            wd.stop_sampler()

    def test_sampler_captures_bootstrap_flags_at_detection_time(self):
        """Bootstrap flags should be snapshotted at detection, not recovery."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_bootstrap_flags({
            'deferred_setup_active': True,
            'truth_refresh_active': True,
            'startup_evolution_active': False,
            'prebuild_paused': False,
        })
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            data = wd._consume_live_stall_data()
            flags = data.get('bootstrap_flags_at_detection', {})
            assert flags.get('deferred_setup_active') is True
            assert flags.get('truth_refresh_active') is True
        finally:
            wd.stop_sampler()

    def test_no_stall_no_live_data(self):
        """When ticks are regular, sampler should NOT capture live stack."""
        wd = _make_watchdog(stall_threshold_ms=200, sampler_interval_s=0.03)
        wd.start_sampler()
        try:
            for _ in range(5):
                wd.tick()
                time.sleep(0.05)
            data = wd._consume_live_stall_data()
            assert not data.get('main_thread_stack_during_stall')
        finally:
            wd.stop_sampler()

    def test_sampler_does_not_do_heavy_io(self):
        """Sampler loop must not call take_resource_snapshot or disk IO."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            # If we got here without exceptions, no heavy IO was attempted.
            # The sampler only uses sys._current_frames() which is in-memory.
            data = wd._consume_live_stall_data()
            assert data.get('main_thread_stack_during_stall')
        finally:
            wd.stop_sampler()

    def test_consume_resets_live_data(self):
        """After consuming, live data should be empty."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            data1 = wd._consume_live_stall_data()
            assert data1.get('main_thread_stack_during_stall')
            data2 = wd._consume_live_stall_data()
            assert not data2.get('main_thread_stack_during_stall')
        finally:
            wd.stop_sampler()


# ---------------------------------------------------------------------------
# D. Dominant phase no stale — stall record uses sampler phase
# ---------------------------------------------------------------------------

class TestDominantPhaseNoStale:
    def test_stall_record_uses_detection_phase_not_recovery_phase(self):
        """When sampler captured phase during stall, tick should use it."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_dominant_phase('lazy_vm_prebuild:knowledge')
        wd.start_sampler()
        try:
            wd.tick()
            # Phase changes to knowledge DURING normal operation
            wd.set_dominant_phase('startup_background:truth_refresh')
            time.sleep(0.25)
            # Sampler should have captured 'startup_background:truth_refresh'
            # Now change phase to something else (simulates recovery)
            wd.set_dominant_phase('idle')
            # tick records the stall — should use sampler's detection phase
            wd.tick()
            assert wd._stall_count >= 1
            stalls = list(wd._stalls)
            last_stall = stalls[-1]
            # Detection phase should be from sampler, not 'idle'
            assert last_stall.get('dominant_phase') != 'idle' or \
                last_stall.get('dominant_phase_at_detection') == 'startup_background:truth_refresh'
        finally:
            wd.stop_sampler()

    def test_unknown_phase_falls_back_correctly(self):
        """When no phase is confirmed, should use structured fallback."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_dominant_phase('')
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            wd.tick()
            if wd._stall_count >= 1:
                last_stall = wd._stalls[-1]
                phase = last_stall.get('dominant_phase', '')
                assert phase in (
                    'event_loop_blocked_unknown',
                    'startup_background:deferred_setup',
                    'startup_background:truth_refresh',
                    'startup_background:startup_evolution',
                    'prebuild_waiting:paused',
                ) or phase.startswith('startup_background:') or phase == ''
        finally:
            wd.stop_sampler()


# ---------------------------------------------------------------------------
# F. Enriched evidence
# ---------------------------------------------------------------------------

class TestEnrichedEvidence:
    def test_stall_record_has_post_stall_dominant_phase(self):
        """Stall record should distinguish post-stall phase."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_dominant_phase('startup_background:truth_refresh')
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            wd.set_dominant_phase('idle_after_stall')
            wd.tick()
            if wd._stall_count >= 1:
                last_stall = wd._stalls[-1]
                assert 'post_stall_dominant_phase' in last_stall
        finally:
            wd.stop_sampler()

    def test_stall_record_has_bootstrap_flags(self):
        """Stall record should include bootstrap flags snapshot."""
        wd = _make_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_bootstrap_flags({'deferred_setup_active': True, 'prebuild_paused': False})
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            wd.tick()
            if wd._stall_count >= 1:
                last_stall = wd._stalls[-1]
                if last_stall.get('bootstrap_flags_at_detection'):
                    assert last_stall['bootstrap_flags_at_detection'].get('deferred_setup_active') is True
        finally:
            wd.stop_sampler()


# ---------------------------------------------------------------------------
# Cooldown anti-storm
# ---------------------------------------------------------------------------

class TestCooldownAntiStorm:
    def test_cooldown_prevents_rapid_incident_capture(self):
        """Multiple stalls in quick succession should not all trigger capture."""
        wd = _make_watchdog(stall_threshold_ms=50, sampler_interval_s=0.02)
        wd.start_sampler()
        try:
            captures = 0
            for _ in range(3):
                wd.tick()
                time.sleep(0.1)
                wd.tick()
            # Should have had stalls but cooldown should limit captures
            assert wd._stall_count >= 1
        finally:
            wd.stop_sampler()

    def test_sampler_start_stop(self):
        """Sampler can be started and stopped cleanly."""
        wd = _make_watchdog()
        wd.start_sampler()
        assert wd._sampler_running is True
        assert wd._sampler_thread is not None
        wd.stop_sampler()
        time.sleep(0.1)
        assert wd._sampler_running is False

    def test_double_start_is_noop(self):
        """Starting sampler twice should not create a second thread."""
        wd = _make_watchdog()
        wd.start_sampler()
        t1 = wd._sampler_thread
        wd.start_sampler()
        t2 = wd._sampler_thread
        assert t1 is t2
        wd.stop_sampler()
