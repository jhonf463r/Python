"""Tests for async incident capture in UIHeartbeatWatchdog.

Verifies:
1. _record_stall returns quickly even when capture_incident is slow
2. capture_incident executes in background thread
3. Cooldown prevents multiple captures for repeated stalls
4. RuntimeAuditTracer trace still emits synchronously (lightweight)
5. In-flight guard prevents concurrent captures
"""

from __future__ import annotations

import os
import sys
import time
import threading
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# The runtime_audit_tracer module must be imported so patch targets exist.
import iabv_v15.services.evolution.runtime_audit_tracer as _rat_mod  # noqa: F401

_TRACER_PATCH = 'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer'


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_watchdog(freeze_reporter=None):
    """Create a UIHeartbeatWatchdog with a mocked or provided reporter."""
    from iabv_v15.services.evolution.freeze_incident_reporter import (
        UIHeartbeatWatchdog,
    )
    reporter = freeze_reporter or MagicMock()
    wd = UIHeartbeatWatchdog(
        stall_threshold_ms=2000,
        freeze_reporter=reporter,
    )
    return wd, reporter


# ------------------------------------------------------------------ #
# 1. _record_stall returns quickly
# ------------------------------------------------------------------ #

class TestRecordStallReturnsFast:
    """_record_stall must return in < 1s even if capture_incident is slow."""

    def test_returns_fast_with_slow_capture(self):
        slow_reporter = MagicMock()

        def slow_capture(**kwargs):
            time.sleep(5)

        slow_reporter.capture_incident.side_effect = slow_capture
        wd, _ = _make_watchdog(freeze_reporter=slow_reporter)

        with patch(_TRACER_PATCH, return_value=MagicMock()):
            start = time.time()
            wd._record_stall(8000.0)  # > 5000ms threshold
            elapsed = time.time() - start

        # Must return immediately — capture runs in background
        assert elapsed < 1.0

    def test_returns_fast_with_no_reporter(self):
        wd, _ = _make_watchdog(freeze_reporter=None)
        wd._freeze_reporter = None

        with patch(_TRACER_PATCH, return_value=MagicMock()):
            start = time.time()
            wd._record_stall(8000.0)
            elapsed = time.time() - start

        assert elapsed < 0.5


# ------------------------------------------------------------------ #
# 2. capture_incident executes in background
# ------------------------------------------------------------------ #

class TestCaptureInBackground:
    """capture_incident must actually run (just in a background thread)."""

    def test_capture_called_in_background(self):
        reporter = MagicMock()
        captured = threading.Event()

        def on_capture(**kwargs):
            captured.set()

        reporter.capture_incident.side_effect = on_capture
        wd, _ = _make_watchdog(freeze_reporter=reporter)

        with patch(
            _TRACER_PATCH, return_value=MagicMock(),
        ):
            wd._record_stall(8000.0)

        # Wait for background thread to complete
        assert captured.wait(timeout=5.0), 'capture_incident was not called'
        reporter.capture_incident.assert_called_once()

    def test_capture_not_called_for_short_stall(self):
        """Stalls < 5000ms should NOT trigger incident capture."""
        reporter = MagicMock()
        wd, _ = _make_watchdog(freeze_reporter=reporter)

        with patch(_TRACER_PATCH, return_value=MagicMock()):
            wd._record_stall(3000.0)  # < 5000ms threshold
            time.sleep(0.5)

        reporter.capture_incident.assert_not_called()


# ------------------------------------------------------------------ #
# 3. Cooldown prevents repeated captures
# ------------------------------------------------------------------ #

class TestCooldown:
    """Repeated stalls within cooldown period must not produce multiple captures."""

    def test_cooldown_blocks_second_capture(self):
        reporter = MagicMock()
        call_count = 0
        call_count_lock = threading.Lock()

        def count_capture(**kwargs):
            nonlocal call_count
            with call_count_lock:
                call_count += 1

        reporter.capture_incident.side_effect = count_capture
        wd, _ = _make_watchdog(freeze_reporter=reporter)

        with patch(_TRACER_PATCH, return_value=MagicMock()):
            wd._record_stall(8000.0)  # First capture
            time.sleep(0.5)  # Let first capture complete
            wd._record_stall(8000.0)  # Second within cooldown — blocked
            time.sleep(0.5)

        with call_count_lock:
            assert call_count == 1

    def test_cooldown_allows_after_expiry(self):
        reporter = MagicMock()
        wd, _ = _make_watchdog(freeze_reporter=reporter)
        # Set cooldown to very short for testing
        wd._INCIDENT_CAPTURE_COOLDOWN_S = 0.1

        with patch(_TRACER_PATCH, return_value=MagicMock()):
            wd._record_stall(8000.0)
            time.sleep(0.5)  # Wait for first + cooldown expiry
            wd._record_stall(8000.0)
            time.sleep(0.5)

        assert reporter.capture_incident.call_count == 2


# ------------------------------------------------------------------ #
# 4. RuntimeAuditTracer trace still emits synchronously
# ------------------------------------------------------------------ #

class TestRuntimeAuditSync:
    """runtime_audit trace must still emit during _record_stall (lightweight)."""

    def test_tracer_called_sync(self):
        wd, _ = _make_watchdog()
        mock_tracer = MagicMock()

        with patch(_TRACER_PATCH, return_value=mock_tracer):
            wd._record_stall(3000.0)

        mock_tracer.trace.assert_called()
        call_args = mock_tracer.trace.call_args
        assert call_args.args[0] == 'ui_event_loop_stall'


# ------------------------------------------------------------------ #
# 5. In-flight guard prevents concurrent captures
# ------------------------------------------------------------------ #

class TestInFlightGuard:
    """Only one capture thread should run at a time."""

    def test_in_flight_blocks_concurrent(self):
        reporter = MagicMock()
        started = threading.Event()
        proceed = threading.Event()

        def blocking_capture(**kwargs):
            started.set()
            proceed.wait(timeout=5.0)

        reporter.capture_incident.side_effect = blocking_capture
        wd, _ = _make_watchdog(freeze_reporter=reporter)

        with patch(_TRACER_PATCH, return_value=MagicMock()):
            # First stall starts capture
            wd._capture_incident_async(
                duration_ms=8000.0,
                stall_record={'timestamp': datetime.now(timezone.utc).isoformat()},
                cause='test_cause_1',
            )
            started.wait(timeout=2.0)

            # While first is in-flight, second should be blocked
            assert wd._capture_in_flight is True
            wd._capture_incident_async(
                duration_ms=9000.0,
                stall_record={'timestamp': datetime.now(timezone.utc).isoformat()},
                cause='test_cause_2',  # different cause, but in-flight blocks
            )

        # Only the first capture should have been called
        proceed.set()
        time.sleep(0.5)
        assert reporter.capture_incident.call_count == 1


# ------------------------------------------------------------------ #
# PR #360 — Sampler coverage (added on top of historical tests)
# ------------------------------------------------------------------ #

def _make_sampler_watchdog(
    *,
    stall_threshold_ms: float = 200,
    sampler_interval_s: float = 0.05,
):
    from iabv_v15.services.evolution.freeze_incident_reporter import (
        FreezeIncidentReporter,
        UIHeartbeatWatchdog,
    )
    reporter = FreezeIncidentReporter.__new__(FreezeIncidentReporter)
    reporter._reports_dir = None
    reporter._db_path = None
    wd = UIHeartbeatWatchdog(
        stall_threshold_ms=stall_threshold_ms,
        freeze_reporter=reporter,
        sampler_interval_s=sampler_interval_s,
    )
    return wd


class TestSamplerCapturesDuringStall:
    def test_sampler_captures_live_stack_during_simulated_stall(self):
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            data = wd._consume_live_stall_data()
            assert data.get('main_thread_stack_during_stall'), (
                'Sampler did not capture live stack during stall'
            )
            assert isinstance(data['main_thread_stack_during_stall'], list)
            assert len(data['main_thread_stack_during_stall']) > 0
        finally:
            wd.stop_sampler()

    def test_sampler_captures_dominant_phase_at_detection_time(self):
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
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
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
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
        wd = _make_sampler_watchdog(stall_threshold_ms=200, sampler_interval_s=0.03)
        wd.start_sampler()
        try:
            for _ in range(5):
                wd.tick()
                time.sleep(0.05)
            data = wd._consume_live_stall_data()
            assert not data.get('main_thread_stack_during_stall')
        finally:
            wd.stop_sampler()

    def test_consume_resets_live_data(self):
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
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


class TestSamplerDominantPhaseNoStale:
    def test_stall_record_uses_detection_phase_not_recovery_phase(self):
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
        wd.set_dominant_phase('lazy_vm_prebuild:knowledge')
        wd.start_sampler()
        try:
            wd.tick()
            wd.set_dominant_phase('startup_background:truth_refresh')
            time.sleep(0.25)
            wd.set_dominant_phase('idle')
            wd.tick()
            assert wd._stall_count >= 1
            stalls = list(wd._stalls)
            last_stall = stalls[-1]
            assert last_stall.get('dominant_phase') != 'idle' or \
                last_stall.get('dominant_phase_at_detection') == 'startup_background:truth_refresh'
        finally:
            wd.stop_sampler()


class TestSamplerEnrichedEvidence:
    def test_stall_record_has_post_stall_dominant_phase(self):
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
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
        wd = _make_sampler_watchdog(stall_threshold_ms=100, sampler_interval_s=0.03)
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


class TestSamplerStartStop:
    def test_sampler_start_stop(self):
        wd = _make_sampler_watchdog()
        wd.start_sampler()
        assert wd._sampler_running is True
        assert wd._sampler_thread is not None
        wd.stop_sampler()
        time.sleep(0.1)
        assert wd._sampler_running is False

    def test_double_start_is_noop(self):
        wd = _make_sampler_watchdog()
        wd.start_sampler()
        t1 = wd._sampler_thread
        wd.start_sampler()
        t2 = wd._sampler_thread
        assert t1 is t2
        wd.stop_sampler()
