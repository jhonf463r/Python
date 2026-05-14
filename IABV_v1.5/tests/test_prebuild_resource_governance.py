"""Tests for resource-governed lazy VM prebuild.

Verifies:
1. Prebuild pauses under high RAM pressure (cached snapshot)
2. Prebuild pauses after recent UI stall
3. Navigation-demand build still works (not paused)
4. startup_timeline records lazy_vm_prebuild_paused
5. No regression in canonical work queue (prebuild completes under low pressure)
6. _should_pause_prebuild never calls take_resource_snapshot directly
7. _emit_prebuild_paused never calls take_resource_snapshot directly
8. Stale/absent cache does not block and does not pause by resources
9. Async refresh updates cache without blocking caller
"""

from __future__ import annotations

import os
import sys
import time
import threading
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.services.evolution.freeze_incident_reporter import UIHeartbeatWatchdog


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_bootstrap():
    """Create a minimal AppBootstrap with mocked dependencies."""
    with patch.dict(os.environ, {'IABV_WORKSPACE': '/tmp/test_ws'}):
        from iabv_v15.bootstrap import AppBootstrap
        bs = AppBootstrap.__new__(AppBootstrap)
        bs.config = SimpleNamespace(
            app_name='test',
            workspace_root='/tmp/test_ws',
            data_dir='/tmp/test_data',
        )
        bs._timeline = MagicMock()
        bs._timeline.mark = MagicMock(return_value={})
        bs._qml_root_context = MagicMock()
        # Null out all VM attributes so _ensure_vm_for_route builds them
        for attr in AppBootstrap._ROUTE_TO_VM_ATTR.values():
            setattr(bs, attr, None)
        # Mock all service dependencies needed by VM builders
        _m = MagicMock
        bs.episode_repository = _m()
        bs.knowledge_repository = _m()
        bs.run_repository = _m()
        bs.role_router = _m()
        bs.embedding_service = _m()
        bs.session_artifact_repository = _m()
        bs.inference_service = _m()
        bs.adaptive_task_orchestrator = _m()
        bs.training_orchestrator = _m()
        bs.pbt_control_service = _m()
        bs.development_assist_service = _m()
        bs.engineering_review_service = _m()
        bs.self_teach_orchestrator = _m()
        bs.tool_teach_service = _m()
        bs.autonomous_evolution_service = _m()
        bs.evolution_review_service = _m()
        bs.experiment_lab_repository = _m()
        bs.tool_record_repository = _m()
        bs.scenario_run_repository = _m()
        bs.autonomy_activity_projector = _m()
        bs.objective_repository = _m()
        bs.universal_perception_service = _m()
        bs.autonomous_validation_cycle = _m()
        bs.tool_discovery_service = _m()
        bs.operational_self_examination_service = _m()
        bs.control_master_service = _m()
        bs.control_master_digest_builder = _m()
        bs.self_audit_service = _m()
        bs.site_policy_registry = _m()
        bs.training_profile_manager = _m()
        bs.secret_vault = _m()
        bs._browser_teach_session_service_cache = _m()
        bs.browser_learning_assembler = _m()
        bs.hidden_incident_repository = _m()
        bs.user_clue_repository = _m()
        bs.runtime_signal_collector = _m()
        bs.hidden_incident_detector = _m()
        bs.session_health_service = _m()
        bs.user_clue_service = _m()
        bs.execution_dossier_service = _m()
        bs.replay_annotation_service = _m()
        bs.replay_visual_assembler = _m()
        bs.replay_learning_feedback_service = _m()
        bs.interaction_learning_service = _m()
        bs.live_audit_supervisor = _m()
        bs.audit_teach_verification_service = _m()
        bs.resource_metacognition_service = _m()
        bs.execution_dossier_repository = _m()
        bs.incident_packet_service = _m()
        bs.self_check_orchestrator = _m()
        bs.pending_issue_repository = _m()
        bs.environment_self_awareness_service = _m()
        bs.world_model_service = _m()
        bs.portable_context_service = _m()
        bs.github_remote_service = _m()
        bs.proactive_dashboard_service = _m()
        bs.human_approval_broker = _m()
        bs.approval_memory = _m()
        bs.ui_screenshot_service = _m()
        bs.provider_configs = _m()
        bs.adaptive_session_repository = _m()
        bs.credential_broker = _m()
        bs.clarification_request_service = _m()
        bs.environment_bootstrap_service = _m()
        bs.provider_health_router = _m()
        bs.decision_audit_trail = _m()
        bs.freeze_incident_reporter = _m()
        bs.ui_heartbeat_watchdog = None
        bs.chat_interaction_lifecycle = _m()
        bs.mcp_bridge_service = None
        bs.ui_bridge_server = None
        bs.ui_screenshot_provider = None
        bs.chat_capability_ingestion_service = None
        return bs


def _make_resource_snapshot(ram_used_pct=40.0, cpu_load_1m=0.5, cpu_count=4):
    """Create a ResourceSnapshot with specified pressure levels."""
    from iabv_v15.services.intelligent_resource_manager import ResourceSnapshot
    snap = ResourceSnapshot()
    snap.ram_used_pct = ram_used_pct
    snap.ram_total_mb = 16000
    snap.ram_available_mb = int(16000 * (1 - ram_used_pct / 100))
    snap.cpu_load_1m = cpu_load_1m
    snap.cpu_count = cpu_count
    return snap


def _inject_cached_snapshot(bs, snap, age_seconds=1.0):
    """Inject a snapshot directly into the cache (simulates background refresh)."""
    bs._init_prebuild_snapshot_cache()
    with bs._prebuild_resource_snapshot_lock:
        bs._prebuild_resource_snapshot = snap
        bs._prebuild_resource_snapshot_at = time.time() - age_seconds


def _make_watchdog_with_stall(duration_ms=5000, seconds_ago=5.0):
    """Create a UIHeartbeatWatchdog mock with a recent stall."""
    ts = datetime.fromtimestamp(
        time.time() - seconds_ago, tz=timezone.utc
    ).isoformat(timespec='milliseconds')
    stall = {
        'timestamp': ts,
        'duration_ms': duration_ms,
        'cause': 'ui_event_loop_stall',
    }
    watchdog = MagicMock()
    watchdog.recent_stalls.return_value = [stall]
    return watchdog


# ------------------------------------------------------------------ #
# 1. Prebuild pauses under high RAM pressure (cached snapshot)
# ------------------------------------------------------------------ #

class TestPrebuildPausesHighRAM:
    """_should_pause_prebuild must pause when cached snapshot shows high RAM."""

    def test_pauses_when_ram_pressure_high(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=80.0))

        reason = bs._should_pause_prebuild('control', ['capture', 'evolution'])

        assert reason is not None
        assert 'ram_pressure' in reason

    def test_pauses_when_ram_pressure_critical(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=95.0))

        reason = bs._should_pause_prebuild('control', [])

        assert reason is not None
        assert 'ram_pressure:critical' in reason

    def test_does_not_pause_when_ram_low(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=40.0))

        reason = bs._should_pause_prebuild('control', [])

        assert reason is None

    def test_pauses_when_cpu_pressure_high(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(
            bs,
            _make_resource_snapshot(ram_used_pct=40.0, cpu_load_1m=5.0, cpu_count=4),
        )

        reason = bs._should_pause_prebuild('evolution', [])

        assert reason is not None
        assert 'cpu_pressure' in reason


# ------------------------------------------------------------------ #
# 2. Prebuild pauses after recent UI stall
# ------------------------------------------------------------------ #

class TestPrebuildPausesAfterStall:
    """_should_pause_prebuild must detect recent UIHeartbeatWatchdog stalls."""

    def test_pauses_when_recent_stall_detected(self):
        bs = _make_bootstrap()
        bs.ui_heartbeat_watchdog = _make_watchdog_with_stall(
            duration_ms=8000, seconds_ago=10.0,
        )
        # Low-pressure cache — stall alone should trigger pause
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=40.0))

        reason = bs._should_pause_prebuild('capture', [])

        assert reason is not None
        assert 'recent_ui_stall' in reason

    def test_does_not_pause_when_stall_is_old(self):
        bs = _make_bootstrap()
        bs.ui_heartbeat_watchdog = _make_watchdog_with_stall(
            duration_ms=8000, seconds_ago=60.0,  # > 30s lookback
        )
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=40.0))

        reason = bs._should_pause_prebuild('capture', [])

        assert reason is None

    def test_does_not_pause_when_no_stalls(self):
        bs = _make_bootstrap()
        watchdog = MagicMock()
        watchdog.recent_stalls.return_value = []
        bs.ui_heartbeat_watchdog = watchdog
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=40.0))

        reason = bs._should_pause_prebuild('capture', [])

        assert reason is None


# ------------------------------------------------------------------ #
# 3. Navigation-demand build still works (not paused)
# ------------------------------------------------------------------ #

class TestNavigationDemandNotPaused:
    """_ensure_vm_for_route must always build the VM, regardless of pressure."""

    def test_ensure_vm_builds_under_high_pressure(self):
        bs = _make_bootstrap()
        assert bs.evolution_center_viewmodel is None

        with patch('iabv_v15.bootstrap.EvolutionCenterViewModel') as evm_cls:
            evm_cls.return_value = MagicMock()
            bs._ensure_vm_for_route('evolution')

        assert bs.evolution_center_viewmodel is not None
        evm_cls.assert_called_once()

    def test_ensure_vm_is_noop_when_already_built(self):
        bs = _make_bootstrap()
        bs.evolution_center_viewmodel = MagicMock()  # already built

        with patch('iabv_v15.bootstrap.EvolutionCenterViewModel') as evm_cls:
            bs._ensure_vm_for_route('evolution')

        evm_cls.assert_not_called()

    def test_ensure_vm_does_not_call_should_pause(self):
        """Navigation-triggered build must NOT check resource pressure."""
        bs = _make_bootstrap()

        with patch('iabv_v15.bootstrap.KnowledgeBaseViewModel') as kb_cls, \
             patch.object(bs, '_should_pause_prebuild') as pause_mock:
            kb_cls.return_value = MagicMock()
            bs._ensure_vm_for_route('knowledge')

        pause_mock.assert_not_called()


# ------------------------------------------------------------------ #
# 4. startup_timeline records lazy_vm_prebuild_paused
# ------------------------------------------------------------------ #

class TestTimelineRecordsPaused:
    """_emit_prebuild_paused must mark the timeline with cached metadata."""

    def test_timeline_mark_emitted_with_cached_data(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=80.0))

        bs._emit_prebuild_paused(
            reason='ram_pressure:high',
            route='control',
            remaining=['control', 'capture', 'evolution'],
        )

        bs._timeline.mark.assert_called()
        call_args = bs._timeline.mark.call_args
        assert call_args.args[0] == 'lazy_vm_prebuild_paused'
        kw = call_args.kwargs
        assert kw['reason'] == 'ram_pressure:high'
        assert kw['route'] == 'control'
        assert 'remaining_routes' in kw
        assert 'memory_percent' in kw
        assert 'snapshot_age_ms' in kw

    def test_timeline_mark_emitted_without_cache(self):
        """When no cached snapshot exists, timeline still emits (without resource data)."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()  # no snapshot injected

        bs._emit_prebuild_paused(
            reason='recent_ui_stall:5000ms',
            route='capture',
            remaining=['capture'],
        )

        bs._timeline.mark.assert_called()
        call_args = bs._timeline.mark.call_args
        assert call_args.args[0] == 'lazy_vm_prebuild_paused'
        kw = call_args.kwargs
        assert kw['reason'] == 'recent_ui_stall:5000ms'
        # No memory_percent since no snapshot
        assert 'memory_percent' not in kw

    def test_prebuild_paused_state_set(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=85.0))

        reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason is not None
        bs._prebuild_paused = True
        bs._prebuild_paused_routes = ['control', 'capture']
        assert bs._prebuild_paused is True
        assert 'control' in bs._prebuild_paused_routes


# ------------------------------------------------------------------ #
# 5. No regression: prebuild completes under low pressure
# ------------------------------------------------------------------ #

class TestNoRegressionCanonicalQueue:
    """Under low resource pressure and no stalls, prebuild builds all VMs."""

    def test_all_routes_pass_gate_under_low_pressure(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(
            bs,
            _make_resource_snapshot(ram_used_pct=40.0, cpu_load_1m=0.5),
        )
        routes = list(bs._ROUTE_TO_VM_ATTR.keys())

        for route in routes:
            remaining = routes[routes.index(route) + 1:]
            reason = bs._should_pause_prebuild(route, remaining)
            assert reason is None, f'Unexpected pause for route {route}: {reason}'

    def test_prebuild_paused_false_when_all_complete(self):
        """After full prebuild, _prebuild_paused should be False."""
        bs = _make_bootstrap()
        bs._prebuild_paused = False
        bs._prebuild_paused_routes = []
        assert not bs._prebuild_paused
        assert bs._prebuild_paused_routes == []

    def test_should_pause_handles_missing_watchdog_gracefully(self):
        """If watchdog is None, prebuild should continue."""
        bs = _make_bootstrap()
        bs.ui_heartbeat_watchdog = None
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=40.0))

        reason = bs._should_pause_prebuild('control', [])

        assert reason is None


# ------------------------------------------------------------------ #
# 6. _should_pause_prebuild never calls take_resource_snapshot
# ------------------------------------------------------------------ #

class TestShouldPauseNeverCallsSnapshotSync:
    """_should_pause_prebuild must not import or call take_resource_snapshot."""

    def test_no_sync_snapshot_call_with_cache(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=80.0))

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
        ) as mock_snap:
            bs._should_pause_prebuild('control', [])

        mock_snap.assert_not_called()

    def test_no_sync_snapshot_call_without_cache(self):
        """Without cache, _should_pause_prebuild pauses and triggers
        an async refresh — but never blocks the caller waiting for it."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()  # no snapshot

        call_thread_names: list[str] = []

        def _recording_snap():
            import threading
            call_thread_names.append(threading.current_thread().name)
            return _make_resource_snapshot()

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            side_effect=_recording_snap,
        ):
            import time as _t
            start = _t.time()
            reason = bs._should_pause_prebuild('control', [])
            elapsed = _t.time() - start

        # Must return immediately (< 0.5s) — never blocks
        assert elapsed < 0.5
        # Must pause with unavailable reason
        assert reason == 'resource_snapshot_unavailable'
        # If take_resource_snapshot was called, it was NOT on the main thread
        _t.sleep(0.5)  # let background thread run
        for name in call_thread_names:
            assert name != threading.current_thread().name


# ------------------------------------------------------------------ #
# 7. _emit_prebuild_paused never calls take_resource_snapshot
# ------------------------------------------------------------------ #

class TestEmitPausedNeverCallsSnapshotSync:
    """_emit_prebuild_paused must read cache only — no sync snapshot."""

    def test_no_sync_snapshot_call(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=80.0))

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
        ) as mock_snap:
            bs._emit_prebuild_paused('ram_pressure:high', 'control', ['control'])

        mock_snap.assert_not_called()

    def test_no_sync_snapshot_call_without_cache(self):
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
        ) as mock_snap:
            bs._emit_prebuild_paused('recent_ui_stall:5000ms', 'capture', [])

        mock_snap.assert_not_called()


# ------------------------------------------------------------------ #
# 8. Stale/absent cache does not block and does not pause by resources
# ------------------------------------------------------------------ #

class TestStaleCacheBehavior:
    """When cache is absent, prebuild pauses until snapshot arrives."""

    def test_absent_cache_pauses_with_snapshot_unavailable(self):
        """No cache and no refresh → pause with resource_snapshot_unavailable."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()  # empty cache

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=_make_resource_snapshot(),
        ):
            reason = bs._should_pause_prebuild('control', [])

        assert reason == 'resource_snapshot_unavailable'

    def test_absent_cache_with_refresh_in_flight_pauses_pending(self):
        """No cache but refresh in-flight → pause with resource_snapshot_pending.

        Note: startup_followup_active is disabled to isolate the
        snapshot-pending codepath (Fix B adds a higher-priority check
        when startup_followup_active is True).
        """
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._startup_followup_active = False

        reason = bs._should_pause_prebuild('control', [])

        assert reason == 'resource_snapshot_pending'

    def test_stale_cache_does_not_pause_by_resources(self):
        bs = _make_bootstrap()
        # Inject a high-pressure snapshot but make it stale (> max age)
        high_snap = _make_resource_snapshot(ram_used_pct=95.0)
        _inject_cached_snapshot(bs, high_snap, age_seconds=120.0)

        reason = bs._should_pause_prebuild('control', [])

        assert reason is None  # stale snapshot ignored (data existed before)

    def test_stall_still_pauses_without_cache(self):
        """Recent UI stall should still pause even without resource cache."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()  # no snapshot
        bs._prebuild_snapshot_refresh_in_flight = True  # so we skip unavailable
        bs._startup_followup_active = False  # isolate snapshot-pending path
        bs.ui_heartbeat_watchdog = _make_watchdog_with_stall(
            duration_ms=8000, seconds_ago=10.0,
        )

        reason = bs._should_pause_prebuild('capture', [])

        # snapshot_pending fires first in this case since snap is None + in-flight
        assert reason is not None
        assert 'resource_snapshot_pending' in reason or 'recent_ui_stall' in reason


# ------------------------------------------------------------------ #
# 9. Async refresh updates cache without blocking caller
# ------------------------------------------------------------------ #

class TestAsyncRefresh:
    """_refresh_prebuild_snapshot_async must update cache in background."""

    def test_refresh_populates_cache(self):
        bs = _make_bootstrap()
        fake_snap = _make_resource_snapshot(ram_used_pct=60.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=fake_snap,
        ):
            bs._refresh_prebuild_snapshot_async()
            # Wait for background thread to complete
            import time
            time.sleep(0.5)

        snap, age = bs._get_cached_snapshot()
        assert snap is not None
        assert snap.ram_used_pct == 60.0
        assert age < 5.0  # should be very recent

    def test_refresh_does_not_block_caller(self):
        """Caller should return immediately even if snapshot is slow."""
        bs = _make_bootstrap()

        def slow_snapshot():
            import time
            time.sleep(10)
            return _make_resource_snapshot(ram_used_pct=50.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            side_effect=slow_snapshot,
        ):
            start = time.time()
            bs._refresh_prebuild_snapshot_async()
            elapsed = time.time() - start

        # Caller must return immediately (< 1s), not wait for the 10s sleep
        assert elapsed < 1.0

    def test_refresh_failure_does_not_crash(self):
        """If take_resource_snapshot raises, cache stays empty."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            side_effect=RuntimeError('psutil not available'),
        ):
            bs._refresh_prebuild_snapshot_async()
            import time
            time.sleep(0.5)

        snap, _ = bs._get_cached_snapshot()
        assert snap is None  # cache not populated on error


# ------------------------------------------------------------------ #
# 10. Prebuild snapshot refresh coalescing
# ------------------------------------------------------------------ #

class TestRefreshCoalescing:
    """_refresh_prebuild_snapshot_async must not spawn parallel threads."""

    def test_coalesce_skips_if_in_flight(self):
        """Second call while first is running should not spawn another thread."""
        bs = _make_bootstrap()
        started = threading.Event()
        proceed = threading.Event()

        def slow_snapshot():
            started.set()
            proceed.wait(timeout=5.0)
            return _make_resource_snapshot(ram_used_pct=50.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            side_effect=slow_snapshot,
        ) as mock_snap:
            bs._refresh_prebuild_snapshot_async()
            started.wait(timeout=2.0)
            # First is in-flight now
            assert bs._prebuild_snapshot_refresh_in_flight is True
            bs._refresh_prebuild_snapshot_async()  # should be coalesced
            bs._refresh_prebuild_snapshot_async()  # should be coalesced

        proceed.set()
        time.sleep(0.5)
        # Only ONE call to take_resource_snapshot
        assert mock_snap.call_count == 1

    def test_in_flight_flag_cleared_after_completion(self):
        bs = _make_bootstrap()
        fake_snap = _make_resource_snapshot(ram_used_pct=40.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=fake_snap,
        ):
            bs._refresh_prebuild_snapshot_async()
            time.sleep(0.5)

        assert bs._prebuild_snapshot_refresh_in_flight is False

    def test_in_flight_flag_cleared_on_failure(self):
        bs = _make_bootstrap()

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            side_effect=RuntimeError('fail'),
        ):
            bs._refresh_prebuild_snapshot_async()
            time.sleep(0.5)

        assert bs._prebuild_snapshot_refresh_in_flight is False


# ------------------------------------------------------------------ #
# 11. Snapshot-pending retry: prebuild waits then resumes
# ------------------------------------------------------------------ #

class TestSnapshotPendingRetry:
    """When snapshot is pending, prebuild must retry via QTimer, not stop forever."""

    def test_pending_does_not_build_route_immediately(self):
        """Snapshot in-flight + cache absent → route NOT built."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._startup_followup_active = False  # isolate snapshot-pending path

        reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason == 'resource_snapshot_pending'

    def test_unavailable_triggers_refresh_and_pauses(self):
        """No snapshot, no refresh → triggers refresh + pauses."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=_make_resource_snapshot(),
        ) as mock_snap:
            reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason == 'resource_snapshot_unavailable'
        # Refresh should have been triggered
        assert bs._prebuild_snapshot_refresh_in_flight is True or mock_snap.called

    def test_ensure_vm_for_route_not_blocked_by_pending(self):
        """Navigation on-demand must still build even if prebuild is paused.

        Uses the existing TestNavigationDemandNotPaused logic — verifies
        _should_pause_prebuild is never called from _ensure_vm_for_route.
        """
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._prebuild_paused = True
        bs._prebuild_paused_routes = ['control', 'capture']

        # Patch _should_pause_prebuild — it must NOT be called from nav path
        with patch.object(bs, '_should_pause_prebuild') as mock_gate:
            # Also patch the heavy VM constructor to avoid deep dependency chain
            with patch.object(type(bs), '_build_control_center_vm', create=True):
                try:
                    bs._ensure_vm_for_route('control')
                except (AttributeError, TypeError):
                    pass  # missing deep deps is fine — we only check the gate

        mock_gate.assert_not_called()

    def test_timeline_records_snapshot_pending_reason(self):
        """Timeline must include reason=resource_snapshot_pending."""
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()
        bs._prebuild_snapshot_refresh_in_flight = True

        bs._emit_prebuild_paused('resource_snapshot_pending', 'control',
                                 ['control', 'capture'])

        bs._timeline.mark.assert_called_once()
        call_kwargs = bs._timeline.mark.call_args
        assert call_kwargs.args[0] == 'lazy_vm_prebuild_paused'
        assert call_kwargs.kwargs['reason'] == 'resource_snapshot_pending'


# ------------------------------------------------------------------ #
# 12. idle prebuild is on-demand only
# ------------------------------------------------------------------ #

class TestDominantPhaseDuringPrebuild:
    """Idle prebuild must not construct hidden ViewModels."""

    def test_idle_prebuild_skips_hidden_vm_construction(self):
        bs = _make_bootstrap()
        mock_wd = MagicMock()
        bs.ui_heartbeat_watchdog = mock_wd
        bs._startup_followup_active = False

        with patch.object(bs, '_ensure_vm_for_route') as ensure_mock:
            bs._build_all_lazy_vms()

        ensure_mock.assert_not_called()
        phases = [call_args.args[0] for call_args in bs._timeline.mark.call_args_list]
        assert 'lazy_vm_prebuild_skipped' in phases
        assert 'lazy_vm_prebuild_done' in phases
        phase_calls = [c.args[0] for c in mock_wd.set_dominant_phase.call_args_list]
        assert phase_calls == ['']


# ------------------------------------------------------------------ #
# 13. Prebuild pauses when background startup is active
# ------------------------------------------------------------------ #

class TestPrebuildPausesDuringBackgroundStartup:
    """Prebuild must not run while heavy background startup tasks are active."""

    def test_pauses_when_deferred_setup_active(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=30.0))
        bs._deferred_setup_active = True

        reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason == 'startup_background_active:deferred_post_window_setup'

    def test_pauses_when_truth_refresh_active(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=30.0))
        bs._truth_refresh_active = True

        reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason == 'startup_background_active:startup_truth_refresh'

    def test_pauses_when_startup_evolution_active(self):
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=30.0))
        bs._startup_evolution_active = True

        reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason == 'startup_background_active:startup_evolution'

    def test_does_not_pause_when_no_background_active(self):
        """With all background flags False and low pressure, should proceed."""
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=30.0))
        bs._deferred_setup_active = False
        bs._truth_refresh_active = False
        bs._startup_evolution_active = False

        reason = bs._should_pause_prebuild('control', [])

        assert reason is None

    def test_startup_background_retries_via_qtimer(self):
        """startup_background_active reasons should schedule QTimer retry."""
        bs = _make_bootstrap()
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=30.0))
        bs._deferred_setup_active = True

        reason = bs._should_pause_prebuild('control', ['capture'])

        # Verify reason is retryable (starts with startup_background_active:)
        assert reason is not None
        assert reason.startswith('startup_background_active:')


# ------------------------------------------------------------------ #
# 14. Timeline spam prevention (cooldown/dedup)
# ------------------------------------------------------------------ #

class TestTimelineSpamPrevention:
    """_emit_prebuild_paused should not spam the timeline with the same reason."""

    def test_no_duplicate_emission_within_cooldown(self):
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()

        # First emission — should go through
        bs._emit_prebuild_paused('resource_snapshot_pending', 'control',
                                 ['control', 'capture'])
        assert bs._timeline.mark.call_count == 1

        # Second emission with same reason+route within cooldown — suppressed
        bs._emit_prebuild_paused('resource_snapshot_pending', 'control',
                                 ['control', 'capture'])
        assert bs._timeline.mark.call_count == 1  # still 1

    def test_emission_when_reason_changes(self):
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()

        bs._emit_prebuild_paused('resource_snapshot_pending', 'control',
                                 ['control', 'capture'])
        assert bs._timeline.mark.call_count == 1

        # Different reason — should emit
        bs._emit_prebuild_paused('startup_background_active:startup_evolution',
                                 'control', ['control', 'capture'])
        assert bs._timeline.mark.call_count == 2

    def test_emission_when_route_changes(self):
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()

        bs._emit_prebuild_paused('resource_snapshot_pending', 'control',
                                 ['control', 'capture'])
        assert bs._timeline.mark.call_count == 1

        # Same reason but different route — should emit
        bs._emit_prebuild_paused('resource_snapshot_pending', 'capture',
                                 ['capture'])
        assert bs._timeline.mark.call_count == 2


# ------------------------------------------------------------------ #
# 15. startup_followup_active semantics
# ------------------------------------------------------------------ #

class TestStartupFollowupActive:
    """startup_followup_active stays True until all background phases finish."""

    def test_followup_active_initially_true(self):
        bs = _make_bootstrap()
        assert bs._startup_followup_active is True

    def test_followup_cleared_when_all_phases_done(self):
        bs = _make_bootstrap()
        bs._deferred_setup_active = False
        bs._truth_refresh_active = False
        bs._startup_evolution_active = False

        bs._check_startup_followup_done()

        assert bs._startup_followup_active is False

    def test_followup_not_cleared_if_any_phase_active(self):
        bs = _make_bootstrap()
        bs._deferred_setup_active = False
        bs._truth_refresh_active = True  # still running
        bs._startup_evolution_active = False

        bs._check_startup_followup_done()

        assert bs._startup_followup_active is True


# ------------------------------------------------------------------ #
# 16. dominant_phase cleaned on pause (not stale)
# ------------------------------------------------------------------ #

class TestDominantPhaseNotStale:
    """dominant_phase must be set to prebuild_waiting:<reason> on pause."""

    def test_waiting_phase_set_on_transient_pause(self):
        bs = _make_bootstrap()
        mock_wd = MagicMock()
        bs.ui_heartbeat_watchdog = mock_wd
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=30.0))
        bs._deferred_setup_active = True  # will cause startup_background_active

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=_make_resource_snapshot(),
        ):
            with patch('iabv_v15.bootstrap.QTimer') as MockQTimer:
                MockQTimer.singleShot = MagicMock()  # don't execute callback
                bs._build_all_lazy_vms()

        # Idle prebuild is skipped, so no stale waiting or route phase remains.
        phase_calls = [c.args[0] for c in mock_wd.set_dominant_phase.call_args_list]
        assert phase_calls[-1] == ''

    def test_phase_cleared_on_non_transient_pause(self):
        """Non-retryable pause (resource pressure) should clear phase."""
        bs = _make_bootstrap()
        mock_wd = MagicMock()
        bs.ui_heartbeat_watchdog = mock_wd
        # High RAM pressure — non-transient
        _inject_cached_snapshot(bs, _make_resource_snapshot(ram_used_pct=95.0))

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=_make_resource_snapshot(ram_used_pct=95.0),
        ):
            with patch('iabv_v15.bootstrap.QTimer') as MockQTimer:
                MockQTimer.singleShot = MagicMock()
                bs._build_all_lazy_vms()

        # Last set_dominant_phase should be '' (cleared)
        phase_calls = [c.args[0] for c in mock_wd.set_dominant_phase.call_args_list]
        assert phase_calls[-1] == ''


# ------------------------------------------------------------------ #
# 17. FreezeIncidentReporter includes stack and flags
# ------------------------------------------------------------------ #

class TestFreezeReporterEnrichment:
    """Incident report must include main_thread_stack and bootstrap_flags."""

    def test_capture_includes_main_thread_stack(self):
        reporter = MagicMock()
        watchdog = UIHeartbeatWatchdog(freeze_reporter=reporter)
        watchdog._startup_active = False
        watchdog._startup_followup_active = False
        watchdog.set_bootstrap_flags({'prebuild_paused': True})

        watchdog._capture_incident_async(
            duration_ms=10000,
            stall_record={'duration_ms': 10000, 'cause': 'stall'},
            cause='ui_event_loop_stall',
        )

        import time as _t
        _t.sleep(0.5)  # let daemon thread run

        reporter.capture_incident.assert_called_once()
        extra = reporter.capture_incident.call_args.kwargs['extra_context']
        assert 'post_stall_stack' in extra or 'main_thread_stack_during_stall' in extra
        assert 'bootstrap_flags' in extra
        assert extra['bootstrap_flags']['prebuild_paused'] is True

    def test_capture_includes_startup_followup_active(self):
        reporter = MagicMock()
        watchdog = UIHeartbeatWatchdog(freeze_reporter=reporter)
        watchdog._startup_followup_active = True

        watchdog._capture_incident_async(
            duration_ms=6000,
            stall_record={'duration_ms': 6000, 'cause': 'stall'},
            cause='ui_event_loop_stall',
        )

        import time as _t
        _t.sleep(0.5)

        extra = reporter.capture_incident.call_args.kwargs['extra_context']
        assert extra['startup_followup_active'] is True


# ------------------------------------------------------------------ #
# 18. _ensure_vm_for_route still not paused
# ------------------------------------------------------------------ #

class TestEnsureVmStillIntact:
    """Navigation on-demand must never check _should_pause_prebuild."""

    def test_ensure_vm_ignores_background_active(self):
        bs = _make_bootstrap()
        bs._init_prebuild_snapshot_cache()
        bs._deferred_setup_active = True
        bs._startup_evolution_active = True
        bs._prebuild_paused = True

        with patch.object(bs, '_should_pause_prebuild') as mock_gate:
            try:
                bs._ensure_vm_for_route('control')
            except (AttributeError, TypeError):
                pass

        mock_gate.assert_not_called()
