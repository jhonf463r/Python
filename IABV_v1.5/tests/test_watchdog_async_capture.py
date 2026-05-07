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
