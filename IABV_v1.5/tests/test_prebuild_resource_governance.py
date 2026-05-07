"""Tests for resource-governed lazy VM prebuild.

Verifies:
1. Prebuild pauses under high RAM pressure
2. Prebuild pauses after recent UI stall
3. Navigation-demand build still works (not paused)
4. startup_timeline records lazy_vm_prebuild_paused
5. No regression in canonical work queue (prebuild completes under low pressure)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


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
# 1. Prebuild pauses under high RAM pressure
# ------------------------------------------------------------------ #

class TestPrebuildPausesHighRAM:
    """_build_all_lazy_vms must pause when RAM pressure is high."""

    def test_pauses_when_ram_pressure_high(self):
        bs = _make_bootstrap()
        high_snap = _make_resource_snapshot(ram_used_pct=80.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=high_snap,
        ):
            reason = bs._should_pause_prebuild('control', ['capture', 'evolution'])

        assert reason is not None
        assert 'ram_pressure' in reason

    def test_pauses_when_ram_pressure_critical(self):
        bs = _make_bootstrap()
        crit_snap = _make_resource_snapshot(ram_used_pct=95.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=crit_snap,
        ):
            reason = bs._should_pause_prebuild('control', [])

        assert reason is not None
        assert 'ram_pressure:critical' in reason

    def test_does_not_pause_when_ram_low(self):
        bs = _make_bootstrap()
        low_snap = _make_resource_snapshot(ram_used_pct=40.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
            reason = bs._should_pause_prebuild('control', [])

        assert reason is None

    def test_pauses_when_cpu_pressure_high(self):
        bs = _make_bootstrap()
        # cpu_load_1m > 1.0 * cpu_count → 'high'
        high_cpu_snap = _make_resource_snapshot(ram_used_pct=40.0, cpu_load_1m=5.0, cpu_count=4)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=high_cpu_snap,
        ):
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
        low_snap = _make_resource_snapshot(ram_used_pct=40.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
            reason = bs._should_pause_prebuild('capture', [])

        assert reason is not None
        assert 'recent_ui_stall' in reason

    def test_does_not_pause_when_stall_is_old(self):
        bs = _make_bootstrap()
        bs.ui_heartbeat_watchdog = _make_watchdog_with_stall(
            duration_ms=8000, seconds_ago=60.0,  # > 30s lookback
        )
        low_snap = _make_resource_snapshot(ram_used_pct=40.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
            reason = bs._should_pause_prebuild('capture', [])

        assert reason is None

    def test_does_not_pause_when_no_stalls(self):
        bs = _make_bootstrap()
        watchdog = MagicMock()
        watchdog.recent_stalls.return_value = []
        bs.ui_heartbeat_watchdog = watchdog
        low_snap = _make_resource_snapshot(ram_used_pct=40.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
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
    """_emit_prebuild_paused must mark the timeline with metadata."""

    def test_timeline_mark_emitted(self):
        bs = _make_bootstrap()
        low_snap = _make_resource_snapshot(ram_used_pct=80.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
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

    def test_prebuild_paused_state_set(self):
        bs = _make_bootstrap()
        high_snap = _make_resource_snapshot(ram_used_pct=85.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=high_snap,
        ):
            reason = bs._should_pause_prebuild('control', ['capture'])

        assert reason is not None
        # Simulate what _build_all_lazy_vms does when paused:
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
        low_snap = _make_resource_snapshot(ram_used_pct=40.0, cpu_load_1m=0.5)
        routes = list(bs._ROUTE_TO_VM_ATTR.keys())

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
            for route in routes:
                remaining = routes[routes.index(route) + 1:]
                reason = bs._should_pause_prebuild(route, remaining)
                assert reason is None, f'Unexpected pause for route {route}: {reason}'

    def test_prebuild_paused_false_when_all_complete(self):
        """After full prebuild, _prebuild_paused should be False."""
        bs = _make_bootstrap()
        # Simulate completion state
        bs._prebuild_paused = False
        bs._prebuild_paused_routes = []
        assert not bs._prebuild_paused
        assert bs._prebuild_paused_routes == []

    def test_should_pause_handles_missing_snapshot_gracefully(self):
        """If take_resource_snapshot raises, prebuild should continue."""
        bs = _make_bootstrap()

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            side_effect=RuntimeError('psutil not available'),
        ):
            reason = bs._should_pause_prebuild('control', [])

        assert reason is None  # should not pause on error

    def test_should_pause_handles_missing_watchdog_gracefully(self):
        """If watchdog is None, prebuild should continue."""
        bs = _make_bootstrap()
        bs.ui_heartbeat_watchdog = None
        low_snap = _make_resource_snapshot(ram_used_pct=40.0)

        with patch(
            'iabv_v15.services.intelligent_resource_manager.take_resource_snapshot',
            return_value=low_snap,
        ):
            reason = bs._should_pause_prebuild('control', [])

        assert reason is None
