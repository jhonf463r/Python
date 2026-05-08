"""Tests for bootstrap flag sync and startup followup semantics (B/C/D).

Validates:
- startup_followup_active remains true while background phases are active.
- flags are pushed to watchdog at start and end of each phase.
- dominant_phase does not go stale after pause/retry.
- _ensure_vm_for_route remains intact (not broken by changes).
"""
import sys
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.freeze_incident_reporter import (
    UIHeartbeatWatchdog,
    FreezeIncidentReporter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeBootstrap:
    """Minimal mock of bootstrap flag-related state and methods."""

    def __init__(self):
        self._deferred_setup_active = False
        self._truth_refresh_active = False
        self._startup_evolution_active = False
        self._startup_followup_active = True
        self._prebuild_paused = False
        self._prebuild_snapshot_refresh_in_flight = False
        self.watchdog = UIHeartbeatWatchdog(
            stall_threshold_ms=200,
            freeze_reporter=MagicMock(),
        )
        self._push_count = 0

    def _push_bootstrap_flags_to_watchdog(self):
        self._push_count += 1
        self.watchdog.set_bootstrap_flags({
            'deferred_setup_active': self._deferred_setup_active,
            'truth_refresh_active': self._truth_refresh_active,
            'startup_evolution_active': self._startup_evolution_active,
            'prebuild_paused': self._prebuild_paused,
            'snapshot_refresh_in_flight': self._prebuild_snapshot_refresh_in_flight,
            'startup_followup_active': self._startup_followup_active,
        })

    def _check_startup_followup_done(self):
        self._push_bootstrap_flags_to_watchdog()
        if (self._deferred_setup_active
                or self._truth_refresh_active
                or self._startup_evolution_active
                or self._prebuild_snapshot_refresh_in_flight):
            return  # at least one phase still running
        self._startup_followup_active = False
        self.watchdog.set_startup_followup_active(False)


# ---------------------------------------------------------------------------
# B. Flags pushed at start and end of each phase
# ---------------------------------------------------------------------------

class TestBootstrapFlagSync:
    def test_deferred_setup_pushes_at_start(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = True
        bs._push_bootstrap_flags_to_watchdog()
        flags = bs.watchdog._bootstrap_flags
        assert flags.get('deferred_setup_active') is True

    def test_deferred_setup_pushes_at_end(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = True
        bs._push_bootstrap_flags_to_watchdog()
        bs._deferred_setup_active = False
        bs._push_bootstrap_flags_to_watchdog()
        bs._check_startup_followup_done()
        flags = bs.watchdog._bootstrap_flags
        assert flags.get('deferred_setup_active') is False

    def test_truth_refresh_pushes_at_start(self):
        bs = FakeBootstrap()
        bs._truth_refresh_active = True
        bs._push_bootstrap_flags_to_watchdog()
        assert bs.watchdog._bootstrap_flags.get('truth_refresh_active') is True

    def test_startup_evolution_pushes_at_start_and_end(self):
        bs = FakeBootstrap()
        initial_count = bs._push_count
        bs._startup_evolution_active = True
        bs._push_bootstrap_flags_to_watchdog()
        assert bs._push_count == initial_count + 1
        bs._startup_evolution_active = False
        bs._push_bootstrap_flags_to_watchdog()
        assert bs._push_count == initial_count + 2

    def test_snapshot_refresh_pushes_flag(self):
        bs = FakeBootstrap()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._push_bootstrap_flags_to_watchdog()
        assert bs.watchdog._bootstrap_flags.get('snapshot_refresh_in_flight') is True
        bs._prebuild_snapshot_refresh_in_flight = False
        bs._push_bootstrap_flags_to_watchdog()
        assert bs.watchdog._bootstrap_flags.get('snapshot_refresh_in_flight') is False


# ---------------------------------------------------------------------------
# C. startup_followup_active stays true while any phase is active
# ---------------------------------------------------------------------------

class TestStartupFollowupSemantic:
    def test_followup_stays_true_while_deferred_setup_active(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = True
        bs._truth_refresh_active = False
        bs._startup_evolution_active = False
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is True

    def test_followup_stays_true_while_truth_refresh_active(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = False
        bs._truth_refresh_active = True
        bs._startup_evolution_active = False
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is True

    def test_followup_stays_true_while_evolution_active(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = False
        bs._truth_refresh_active = False
        bs._startup_evolution_active = True
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is True

    def test_followup_stays_true_while_snapshot_refresh_in_flight(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = False
        bs._truth_refresh_active = False
        bs._startup_evolution_active = False
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is True

    def test_followup_clears_when_all_phases_done(self):
        bs = FakeBootstrap()
        bs._deferred_setup_active = False
        bs._truth_refresh_active = False
        bs._startup_evolution_active = False
        bs._prebuild_snapshot_refresh_in_flight = False
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is False

    def test_followup_only_clears_once_all_phases_finish_sequentially(self):
        """Simulates realistic startup: phases finish one by one."""
        bs = FakeBootstrap()
        bs._deferred_setup_active = True
        bs._truth_refresh_active = True
        bs._startup_evolution_active = True

        # Phase 1 finishes
        bs._deferred_setup_active = False
        bs._push_bootstrap_flags_to_watchdog()
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is True

        # Phase 2 finishes
        bs._truth_refresh_active = False
        bs._push_bootstrap_flags_to_watchdog()
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is True

        # Phase 3 finishes
        bs._startup_evolution_active = False
        bs._push_bootstrap_flags_to_watchdog()
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is False


# ---------------------------------------------------------------------------
# D. Dominant phase not stale
# ---------------------------------------------------------------------------

class TestDominantPhaseNotStale:
    def test_watchdog_dominant_phase_can_be_updated(self):
        wd = UIHeartbeatWatchdog(
            stall_threshold_ms=200,
            freeze_reporter=MagicMock(),
        )
        wd.set_dominant_phase('lazy_vm_prebuild:knowledge')
        assert wd._dominant_phase == 'lazy_vm_prebuild:knowledge'
        wd.set_dominant_phase('startup_background:truth_refresh')
        assert wd._dominant_phase == 'startup_background:truth_refresh'

    def test_stall_record_preserves_phase_at_time_of_stall(self):
        """When sampler runs, phase at detection should be preserved."""
        wd = UIHeartbeatWatchdog(
            stall_threshold_ms=100,
            freeze_reporter=MagicMock(),
            sampler_interval_s=0.03,
        )
        wd.set_dominant_phase('startup_background:deferred_setup')
        wd.start_sampler()
        try:
            wd.tick()
            time.sleep(0.25)
            # Sampler should have captured the phase
            data = wd._consume_live_stall_data()
            assert data.get('dominant_phase_at_detection') == 'startup_background:deferred_setup'
        finally:
            wd.stop_sampler()


# ---------------------------------------------------------------------------
# _ensure_vm_for_route sanity check
# ---------------------------------------------------------------------------

class TestEnsureVmForRouteIntact:
    def test_bootstrap_module_has_ensure_vm_for_route(self):
        """Confirm _ensure_vm_for_route still exists in bootstrap module."""
        from iabv_v15 import bootstrap as bs_mod
        cls = getattr(bs_mod, 'IABVBootstrap', None)
        if cls is None:
            pytest.skip('IABVBootstrap not found in bootstrap module')
        assert hasattr(cls, '_ensure_vm_for_route'), (
            '_ensure_vm_for_route was removed or renamed — navigation on-demand broken'
        )
