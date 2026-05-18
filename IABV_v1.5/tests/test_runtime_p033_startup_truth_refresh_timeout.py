"""P0.33 — startup truth refresh must not block runtime wiring."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock


def _make_bootstrap_stub():
    from iabv_v15.bootstrap import AppBootstrap

    boot = AppBootstrap.__new__(AppBootstrap)
    boot._STARTUP_TRUTH_STEP_TIMEOUT_S = 0.05
    boot._truth_refresh_active = True
    boot._metacognition_data_is_stale = MagicMock(return_value=False)
    boot._push_bootstrap_flags_to_watchdog = MagicMock()
    boot._check_startup_followup_done = MagicMock()
    boot._tracer = SimpleNamespace(trace=MagicMock())
    return boot


def test_startup_truth_refresh_times_out_stuck_portable_context():
    boot = _make_bootstrap_stub()
    boot.operational_self_examination_service = SimpleNamespace(
        build_review=MagicMock(return_value={'ok': True}),
    )
    boot.portable_context_service = SimpleNamespace(
        build_package=MagicMock(side_effect=lambda: time.sleep(2.0)),
    )

    started = time.perf_counter()
    boot._final_startup_truth_refresh()
    elapsed = time.perf_counter() - started

    assert elapsed < 0.5
    assert boot._truth_refresh_active is False
    boot._push_bootstrap_flags_to_watchdog.assert_called_once()
    boot._check_startup_followup_done.assert_called_once()
    boot._tracer.trace.assert_called_with(
        'startup_truth_refresh_step_timeout',
        step='portable_context',
        timeout_s=0.05,
    )


def test_startup_truth_refresh_clears_flag_when_oses_fails():
    boot = _make_bootstrap_stub()
    boot.operational_self_examination_service = SimpleNamespace(
        build_review=MagicMock(side_effect=RuntimeError('boom')),
    )
    boot.portable_context_service = SimpleNamespace(
        build_package=MagicMock(return_value={'ok': True}),
    )

    boot._final_startup_truth_refresh()

    assert boot._truth_refresh_active is False
    boot._push_bootstrap_flags_to_watchdog.assert_called_once()
    boot._check_startup_followup_done.assert_called_once()

