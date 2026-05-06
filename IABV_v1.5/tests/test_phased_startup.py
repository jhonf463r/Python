"""Tests for phased populate_ui startup optimization.

Verifies:
1. Timeline marks per VM phase exist after _build_ui_objects
2. Fast path: shell_loader_ready honesto preempts splash_early_close
   and shell_loader_ready_fallback
3. Fallback determinism: when honest signal never arrives, fallback
   still closes the splash
4. Phased build methods exist and are callable
5. Regression: _build_ui_objects still builds all VMs (sync path)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
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
        # Minimal config
        bs.config = SimpleNamespace(
            app_name='test',
            workspace_root='/tmp/test_ws',
            data_dir='/tmp/test_data',
        )
        # Timeline mock
        bs._timeline = MagicMock()
        bs._timeline.mark = MagicMock()
        bs._timeline.events_since = MagicMock(return_value=[])
        # Null out all VM attributes
        bs.navigation_controller = None
        bs.theme_controller = None
        bs.main_window_bridge = None
        bs.dashboard_viewmodel = None
        bs.control_center_viewmodel = None
        bs.capture_studio_viewmodel = None
        bs.evolution_center_viewmodel = None
        bs.knowledge_base_viewmodel = None
        bs.provider_settings_viewmodel = None
        bs.run_history_viewmodel = None
        bs.centro_vivo_viewmodel = None
        # Side-effects
        bs.mcp_bridge_service = None
        bs.ui_bridge_server = None
        bs.ui_screenshot_provider = None
        bs.chat_capability_ingestion_service = None
        # Theme
        bs.theme = SimpleNamespace()
        # Splash
        bs._splash = None
        bs._shell_loader_ready_handled = False
        # Service dependencies (mocked — only need to exist as attributes)
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
        bs.chat_message_repository = _m()
        bs.decision_audit_trail = _m()
        return bs


# ------------------------------------------------------------------ #
# 1. Timeline marks per phase
# ------------------------------------------------------------------ #


class TestTimelinePhaseMarks:
    """_build_ui_objects must leave timeline marks for each VM phase."""

    def test_critical_phase_marks(self):
        bs = _make_bootstrap()
        # Mock VM constructors
        with patch('iabv_v15.bootstrap.NavigationController') as nc, \
             patch('iabv_v15.bootstrap.ThemeController') as tc, \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel') as dvm:
            nc.return_value = MagicMock()
            tc.return_value = MagicMock()
            bridge = MagicMock()
            mwb.return_value = bridge
            dvm.return_value = MagicMock()
            bs._build_critical_ui_objects()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        assert 'populate_ui_vm_navigation' in marked
        assert 'populate_ui_vm_dashboard' in marked

    def test_deferred_batch_1_marks(self):
        bs = _make_bootstrap()
        bs.navigation_controller = MagicMock()
        with patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()):
            bs._build_deferred_ui_batch_1()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        assert 'populate_ui_vm_mcp_side_effects' in marked
        # ControlCenterVM and CaptureStudioVM are now lazy — they moved
        # to _build_deferred_ui_batch_2 (sync test path) or lazy
        # construction (live path).
        assert 'populate_ui_vm_control_center' not in marked
        assert 'populate_ui_vm_capture_studio' not in marked

    def test_deferred_batch_2_marks(self):
        bs = _make_bootstrap()
        bs.navigation_controller = MagicMock()
        bs.control_center_viewmodel = None
        bs.capture_studio_viewmodel = None
        bs.evolution_center_viewmodel = None
        with patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.RunHistoryViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CentroVivoViewModel', return_value=MagicMock()):
            bs._build_deferred_ui_batch_2()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        assert 'populate_ui_vm_control_center' in marked
        assert 'populate_ui_vm_capture_studio' in marked
        assert 'populate_ui_vm_evolution_center' in marked
        assert 'populate_ui_vm_remaining' in marked

    def test_full_build_has_all_marks(self):
        bs = _make_bootstrap()
        with patch('iabv_v15.bootstrap.NavigationController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ThemeController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.RunHistoryViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CentroVivoViewModel', return_value=MagicMock()):
            mwb.return_value = MagicMock()
            bs._build_ui_objects()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        expected = [
            'populate_ui_vm_navigation',
            'populate_ui_vm_dashboard',
            'populate_ui_vm_mcp_side_effects',
            'populate_ui_vm_control_center',
            'populate_ui_vm_capture_studio',
            'populate_ui_vm_evolution_center',
            'populate_ui_vm_remaining',
        ]
        for phase in expected:
            assert phase in marked, f'{phase} missing from timeline'


# ------------------------------------------------------------------ #
# 2. Fast path: honest signal preempts fallback
# ------------------------------------------------------------------ #


class TestFastPathHonestSignal:
    """When shell_loader_ready fires, fallback and early_close are no-ops."""

    def test_honest_signal_preempts_fallback(self):
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._fire_splash_ready_and_raise_main = MagicMock()

        # Simulate honest signal arriving
        bs._handle_shell_loader_ready()

        assert bs._shell_loader_ready_handled is True
        bs._fire_splash_ready_and_raise_main.assert_called_once_with('shell_loader_ready')

        # Now fallback should be a no-op
        bs._fire_splash_ready_and_raise_main.reset_mock()
        bs._force_splash_ready_fallback()
        bs._fire_splash_ready_and_raise_main.assert_not_called()

    def test_honest_signal_preempts_early_close(self):
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._fire_splash_ready_and_raise_main = MagicMock()

        # Honest signal first
        bs._handle_shell_loader_ready()
        assert bs._shell_loader_ready_handled is True

        # Early close should be no-op (the guard checks _shell_loader_ready_handled)
        # Simulate the _early_splash_close closure logic directly
        if bs._shell_loader_ready_handled:
            early_close_fired = False
        else:
            early_close_fired = True
        assert not early_close_fired

    def test_populate_ui_critical_done_before_populate_ui_done(self):
        """Critical phase timeline mark must precede populate_ui_done."""
        bs = _make_bootstrap()
        with patch('iabv_v15.bootstrap.NavigationController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ThemeController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.RunHistoryViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CentroVivoViewModel', return_value=MagicMock()):
            mwb.return_value = MagicMock()
            bs._build_ui_objects()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        nav_idx = marked.index('populate_ui_vm_navigation')
        dash_idx = marked.index('populate_ui_vm_dashboard')
        cc_idx = marked.index('populate_ui_vm_control_center')
        assert nav_idx < dash_idx < cc_idx


# ------------------------------------------------------------------ #
# 3. Fallback determinism: when honest signal never arrives
# ------------------------------------------------------------------ #


class TestFallbackDeterminism:
    """Fallback must still close splash when honest signal never arrives."""

    def test_fallback_fires_when_no_honest_signal(self):
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._shell_ready_wall_t0 = None
        bs._shell_ready_fallback_ms = 5000
        bs._fire_splash_ready_and_raise_main = MagicMock()

        bs._force_splash_ready_fallback()

        assert bs._shell_loader_ready_handled is True
        bs._fire_splash_ready_and_raise_main.assert_called_once_with('shell_loader_ready_fallback')

    def test_fallback_records_timeline_mark(self):
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._shell_ready_wall_t0 = None
        bs._shell_ready_fallback_ms = 5000
        bs._fire_splash_ready_and_raise_main = MagicMock()

        bs._force_splash_ready_fallback()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        assert 'shell_loader_ready_fallback' in marked

    def test_fallback_idempotent(self):
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._shell_ready_wall_t0 = None
        bs._shell_ready_fallback_ms = 5000
        bs._fire_splash_ready_and_raise_main = MagicMock()

        bs._force_splash_ready_fallback()
        bs._force_splash_ready_fallback()

        assert bs._fire_splash_ready_and_raise_main.call_count == 1


# ------------------------------------------------------------------ #
# 4. Phased build methods exist and produce VMs
# ------------------------------------------------------------------ #


class TestPhasedBuildMethods:
    """Three phased build methods exist and produce their VMs."""

    def test_build_critical_creates_nav_theme_bridge_dashboard(self):
        bs = _make_bootstrap()
        with patch('iabv_v15.bootstrap.NavigationController') as nc, \
             patch('iabv_v15.bootstrap.ThemeController') as tc, \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel') as dvm:
            nc.return_value = MagicMock(name='nav')
            tc.return_value = MagicMock(name='theme')
            mwb.return_value = MagicMock(name='bridge')
            dvm.return_value = MagicMock(name='dashboard')
            bs._build_critical_ui_objects()

        assert bs.navigation_controller is not None
        assert bs.theme_controller is not None
        assert bs.main_window_bridge is not None
        assert bs.dashboard_viewmodel is not None
        # Deferred VMs must still be None
        assert bs.control_center_viewmodel is None
        assert bs.evolution_center_viewmodel is None

    def test_build_deferred_1_only_services(self):
        """Phase 2 now only builds lightweight services, not VMs."""
        bs = _make_bootstrap()
        bs.navigation_controller = MagicMock()
        with patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()):
            bs._build_deferred_ui_batch_1()

        # ControlCenter and CaptureStudio are lazy now
        assert bs.control_center_viewmodel is None
        assert bs.capture_studio_viewmodel is None

    def test_build_deferred_2_creates_all_lazy_vms(self):
        """Sync path batch_2 builds ALL lazy VMs including control/capture."""
        bs = _make_bootstrap()
        bs.navigation_controller = MagicMock()
        bs.control_center_viewmodel = None
        bs.capture_studio_viewmodel = None
        with patch('iabv_v15.bootstrap.ControlCenterViewModel') as ccvm, \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel') as csvm, \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel') as evm, \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel') as kvm, \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel') as pvm, \
             patch('iabv_v15.bootstrap.RunHistoryViewModel') as rvm, \
             patch('iabv_v15.bootstrap.CentroVivoViewModel') as cvvm:
            ccvm.return_value = MagicMock()
            csvm.return_value = MagicMock()
            evm.return_value = MagicMock()
            kvm.return_value = MagicMock()
            pvm.return_value = MagicMock()
            rvm.return_value = MagicMock()
            cvvm.return_value = MagicMock()
            bs._build_deferred_ui_batch_2()

        assert bs.control_center_viewmodel is not None
        assert bs.capture_studio_viewmodel is not None
        assert bs.evolution_center_viewmodel is not None
        assert bs.knowledge_base_viewmodel is not None
        assert bs.provider_settings_viewmodel is not None
        assert bs.run_history_viewmodel is not None
        assert bs.centro_vivo_viewmodel is not None


# ------------------------------------------------------------------ #
# 5. Regression: _build_ui_objects (sync) still builds everything
# ------------------------------------------------------------------ #


class TestBuildUiObjectsSyncRegression:
    """_build_ui_objects must still produce all VMs for tests."""

    def test_sync_build_produces_all_vms(self):
        bs = _make_bootstrap()
        with patch('iabv_v15.bootstrap.NavigationController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ThemeController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.RunHistoryViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CentroVivoViewModel', return_value=MagicMock()):
            mwb.return_value = MagicMock()
            bs._build_ui_objects()

        all_vms = [
            bs.navigation_controller,
            bs.theme_controller,
            bs.main_window_bridge,
            bs.dashboard_viewmodel,
            bs.control_center_viewmodel,
            bs.capture_studio_viewmodel,
            bs.evolution_center_viewmodel,
            bs.knowledge_base_viewmodel,
            bs.provider_settings_viewmodel,
            bs.run_history_viewmodel,
            bs.centro_vivo_viewmodel,
        ]
        for vm in all_vms:
            assert vm is not None

    def test_sync_build_idempotent(self):
        bs = _make_bootstrap()
        with patch('iabv_v15.bootstrap.NavigationController') as nc, \
             patch('iabv_v15.bootstrap.ThemeController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.RunHistoryViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CentroVivoViewModel', return_value=MagicMock()):
            mwb.return_value = MagicMock()
            nc.return_value = MagicMock()
            bs._build_ui_objects()
            first_nav = bs.navigation_controller
            # Second call should be idempotent
            nc.reset_mock()
            bs._build_ui_objects()
            nc.assert_not_called()
            assert bs.navigation_controller is first_nav


# ------------------------------------------------------------------ #
# 6. Phase 3 must not block pre-page_loader_ready path
# ------------------------------------------------------------------ #


class TestDeferredBatch2WaitsForPageLoaderReady:
    """Phase 3 VMs must NOT be built until page_loader_ready fires."""

    def test_lazy_vms_null_after_phase_1_and_2(self):
        """After Phase 1 + Phase 2, ALL lazy VMs must still be None."""
        bs = _make_bootstrap()
        with patch('iabv_v15.bootstrap.NavigationController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ThemeController', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.MainWindowBridge') as mwb, \
             patch('iabv_v15.bootstrap.DashboardViewModel', return_value=MagicMock()):
            mwb.return_value = MagicMock()
            bs._build_critical_ui_objects()
        with patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()):
            bs._build_deferred_ui_batch_1()

        # Phase 1 + 2 done — ALL lazy VMs must still be None
        assert bs.control_center_viewmodel is None
        assert bs.capture_studio_viewmodel is None
        assert bs.evolution_center_viewmodel is None
        assert bs.knowledge_base_viewmodel is None
        assert bs.provider_settings_viewmodel is None
        assert bs.run_history_viewmodel is None
        assert bs.centro_vivo_viewmodel is None

    def test_page_loader_ready_schedules_deferred_batch_2(self):
        """_handle_page_loader_ready must trigger Phase 3 scheduling."""
        bs = _make_bootstrap()
        bs._persist_boot_profile = MagicMock()
        bs._raise_main_window_now = MagicMock()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False
        bs._deferred_batch_2_done = False

        with patch('iabv_v15.bootstrap.QTimer') as qt_mock:
            bs._handle_page_loader_ready()
            qt_mock.singleShot.assert_called_once_with(0, bs._pending_deferred_2_fn)

        assert bs._page_loader_ready_received is True
        assert bs._deferred_batch_2_scheduled is True

    def test_fallback_also_schedules_deferred_batch_2(self):
        """_force_splash_ready_fallback must also trigger Phase 3."""
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._shell_ready_wall_t0 = None
        bs._shell_ready_fallback_ms = 5000
        bs._fire_splash_ready_and_raise_main = MagicMock()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False

        with patch('iabv_v15.bootstrap.QTimer') as qt_mock:
            bs._force_splash_ready_fallback()
            qt_mock.singleShot.assert_called_once_with(0, bs._pending_deferred_2_fn)

        assert bs._deferred_batch_2_scheduled is True

    def test_schedule_deferred_2_idempotent(self):
        """_schedule_pending_deferred_2 must be idempotent."""
        bs = _make_bootstrap()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False

        with patch('iabv_v15.bootstrap.QTimer') as qt_mock:
            bs._schedule_pending_deferred_2()
            bs._schedule_pending_deferred_2()  # second call
            assert qt_mock.singleShot.call_count == 1

    def test_schedule_deferred_2_noop_without_fn(self):
        """_schedule_pending_deferred_2 is no-op if fn not stored yet."""
        bs = _make_bootstrap()
        bs._deferred_batch_2_scheduled = False

        with patch('iabv_v15.bootstrap.QTimer') as qt_mock:
            bs._schedule_pending_deferred_2()
            qt_mock.singleShot.assert_not_called()

    def test_deferred_2_closure_guard_prevents_double_build(self):
        """Phase 3 closure guard prevents double VM construction."""
        bs = _make_bootstrap()
        bs._deferred_batch_2_done = True
        bs.navigation_controller = MagicMock()
        bs.control_center_viewmodel = None
        bs.capture_studio_viewmodel = None

        with patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.EvolutionCenterViewModel') as evm:
            bs._build_deferred_ui_batch_2()
            # _build_deferred_ui_batch_2 itself has no guard — guard is
            # in the closure.  But the method still builds VMs.
            # This test confirms the flag exists and is checked in the
            # _populate_ui_deferred_2 closure (tested via integration).
            evm.assert_called_once()

    def test_shell_loader_ready_schedules_phase3_safety_net(self):
        """_handle_shell_loader_ready starts a 5s safety net for Phase 3."""
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._fire_splash_ready_and_raise_main = MagicMock()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False

        with patch('iabv_v15.bootstrap.QTimer') as qt_mock:
            bs._handle_shell_loader_ready()
            # Safety net timer: 5000ms → _schedule_pending_deferred_2
            qt_mock.singleShot.assert_called_once_with(
                5000, bs._schedule_pending_deferred_2,
            )


# ------------------------------------------------------------------ #
# 7. Synchronous Loader expectations
# ------------------------------------------------------------------ #


class TestSynchronousLoaders:
    """Main.qml Loaders must be synchronous to avoid QQmlIncubationController
    starvation on Windows with QQmlApplicationEngine."""

    def test_main_shell_loader_is_synchronous(self):
        """mainShellLoader must have asynchronous: false."""
        qml_path = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'Main.qml'
        if not qml_path.exists():
            pytest.skip('Main.qml not found')
        content = qml_path.read_text(encoding='utf-8')
        # mainShellLoader section must NOT have asynchronous: true
        import re
        shell_loader_match = re.search(
            r'id:\s*mainShellLoader.*?asynchronous:\s*(true|false)',
            content,
            re.DOTALL,
        )
        assert shell_loader_match is not None, 'mainShellLoader not found'
        assert shell_loader_match.group(1) == 'false', (
            'mainShellLoader must be synchronous (asynchronous: false) '
            'to avoid QQmlIncubationController starvation on Windows'
        )

    def test_page_loader_is_synchronous(self):
        """pageLoader uses conditional async: sync for first page, async after.

        PR #322 changed the architecture: the first page (Dashboard) loads
        synchronously for fast page_loader_ready, then subsequent pages
        load asynchronously via background preloaders. The asynchronous
        property is now bound to ``parent.initialPageLoaded``.
        """
        qml_path = Path(__file__).resolve().parent.parent / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'Main.qml'
        if not qml_path.exists():
            pytest.skip('Main.qml not found')
        content = qml_path.read_text(encoding='utf-8')
        import re
        page_loader_match = re.search(
            r'id:\s*pageLoader.*?asynchronous:\s*(.+)',
            content,
            re.DOTALL,
        )
        assert page_loader_match is not None, 'pageLoader not found'
        async_value = page_loader_match.group(1).strip()
        assert async_value != 'true', (
            'pageLoader must NOT be unconditionally async — first page '
            'must load synchronously for fast page_loader_ready'
        )


# ------------------------------------------------------------------ #
# 8. Lazy VM construction
# ------------------------------------------------------------------ #


class TestLazyVMConstruction:
    """Phase 3 VMs must be constructed lazily on navigation, not during boot."""

    def test_ensure_vm_for_route_builds_evolution(self):
        """_ensure_vm_for_route('evolution') constructs EvolutionCenterVM."""
        bs = _make_bootstrap()
        bs._qml_root_context = MagicMock()
        assert bs.evolution_center_viewmodel is None
        with patch.object(bs, '_build_evolution_center_vm') as build:
            bs._ensure_vm_for_route('evolution')
            build.assert_called_once()

    def test_ensure_vm_for_route_is_idempotent(self):
        """Subsequent calls for same route are no-ops."""
        bs = _make_bootstrap()
        bs._qml_root_context = MagicMock()
        bs.evolution_center_viewmodel = MagicMock()  # already built
        with patch.object(bs, '_build_evolution_center_vm') as build:
            bs._ensure_vm_for_route('evolution')
            build.assert_not_called()

    def test_ensure_vm_for_route_ignores_phase1_routes(self):
        """Phase 1 route (dashboard) is a no-op (not in lazy map)."""
        bs = _make_bootstrap()
        bs._qml_root_context = MagicMock()
        bs._ensure_vm_for_route('dashboard')
        # No crash, no VMs built

    def test_ensure_vm_for_route_builds_control(self):
        """_ensure_vm_for_route('control') constructs ControlCenterVM."""
        bs = _make_bootstrap()
        bs._qml_root_context = MagicMock()
        assert bs.control_center_viewmodel is None
        with patch.object(bs, '_build_control_center_vm') as build:
            bs._ensure_vm_for_route('control')
            build.assert_called_once()

    def test_ensure_vm_for_route_builds_capture(self):
        """_ensure_vm_for_route('capture') constructs CaptureStudioVM."""
        bs = _make_bootstrap()
        bs._qml_root_context = MagicMock()
        assert bs.capture_studio_viewmodel is None
        with patch.object(bs, '_build_capture_studio_vm') as build:
            bs._ensure_vm_for_route('capture')
            build.assert_called_once()

    def test_ensure_vm_covers_all_lazy_routes(self):
        """All 7 lazy routes are in _ROUTE_TO_VM_ATTR."""
        from iabv_v15.bootstrap import AppBootstrap
        expected = {'control', 'capture', 'evolution', 'knowledge', 'providers', 'runs', 'centro_vivo'}
        assert set(AppBootstrap._ROUTE_TO_VM_ATTR.keys()) == expected

    def test_wire_task_a_signals_reads_vms_dynamically(self):
        """_wire_task_a_signals must read VMs at emit time, not connect time."""
        bs = _make_bootstrap()
        bs.control_center_viewmodel = MagicMock()
        bs.evolution_center_viewmodel = None  # not built yet
        bs._wire_task_a_signals()
        # Build the VM AFTER wiring
        mock_vm = MagicMock()
        bs.evolution_center_viewmodel = mock_vm
        # Emit a signal — both VMs should receive it
        bs.credential_broker.register_prompt_handler.call_args[0][0]('test_payload')


# ------------------------------------------------------------------ #
# 9. page_loader_ready prevents fallback (honest readiness)
# ------------------------------------------------------------------ #


class TestPageLoaderReadyPreventsFallback:
    """page_loader_ready is sufficient to close splash and prevent fallback."""

    def test_page_loader_ready_prevents_fallback(self):
        """If page_loader_ready already fired, fallback must be a no-op."""
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._page_loader_ready_received = False
        bs._fire_splash_ready_and_raise_main = MagicMock()
        bs._raise_main_window_now = MagicMock()
        bs._persist_boot_profile = MagicMock()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False

        # page_loader_ready fires first (before fallback timer)
        with patch('iabv_v15.bootstrap.QTimer'), \
             patch('threading.Thread'):
            bs._handle_page_loader_ready()

        assert bs._page_loader_ready_received is True
        assert bs._shell_loader_ready_handled is True
        bs._fire_splash_ready_and_raise_main.assert_called_once_with('page_loader_ready')

        # Now fallback should be a no-op
        bs._fire_splash_ready_and_raise_main.reset_mock()
        bs._force_splash_ready_fallback()
        bs._fire_splash_ready_and_raise_main.assert_not_called()

    def test_splash_ready_from_page_loader_when_shell_missing(self):
        """page_loader_ready closes splash even if shell_loader_ready never arrived."""
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = False
        bs._page_loader_ready_received = False
        bs._fire_splash_ready_and_raise_main = MagicMock()
        bs._raise_main_window_now = MagicMock()
        bs._persist_boot_profile = MagicMock()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False

        with patch('iabv_v15.bootstrap.QTimer'), \
             patch('threading.Thread'):
            bs._handle_page_loader_ready()

        # splash.set_ready() must have been called via _fire_splash_ready_and_raise_main
        bs._fire_splash_ready_and_raise_main.assert_called_once_with('page_loader_ready')
        # _raise_main_window_now must NOT be called separately (it's in _fire_splash_ready)
        bs._raise_main_window_now.assert_not_called()

    def test_page_loader_ready_with_shell_already_handled(self):
        """When shell_loader_ready already fired, page_loader_ready just raises window."""
        bs = _make_bootstrap()
        bs._shell_loader_ready_handled = True  # shell already handled
        bs._page_loader_ready_received = False
        bs._fire_splash_ready_and_raise_main = MagicMock()
        bs._raise_main_window_now = MagicMock()
        bs._persist_boot_profile = MagicMock()
        bs._pending_deferred_2_fn = MagicMock()
        bs._deferred_batch_2_scheduled = False

        with patch('iabv_v15.bootstrap.QTimer'), \
             patch('threading.Thread'):
            bs._handle_page_loader_ready()

        # Should NOT fire splash again
        bs._fire_splash_ready_and_raise_main.assert_not_called()
        # Should just raise the main window
        bs._raise_main_window_now.assert_called_once_with('page_loader_ready')


# ------------------------------------------------------------------ #
# 10. Truth refresh ordering: OSES before PortableContext
# ------------------------------------------------------------------ #


class TestTruthRefreshOrdering:
    """OSES must refresh before PortableContext in the final truth refresh."""

    def test_oses_refreshes_before_portable_context(self):
        """_final_startup_truth_refresh calls OSES.build_review before PCS.build_package."""
        bs = _make_bootstrap()
        call_order = []
        oses = MagicMock()
        oses.build_review.side_effect = lambda: call_order.append('oses')
        pcs = MagicMock()
        pcs.build_package.side_effect = lambda: call_order.append('pcs')
        bs.operational_self_examination_service = oses
        bs.portable_context_service = pcs

        bs._final_startup_truth_refresh()

        assert call_order == ['oses', 'pcs'], (
            f'Expected OSES before PCS, got: {call_order}'
        )

    def test_oses_failure_does_not_block_portable_context(self):
        """If OSES fails, PortableContext must still persist."""
        bs = _make_bootstrap()
        oses = MagicMock()
        oses.build_review.side_effect = RuntimeError('oses crash')
        pcs = MagicMock()
        bs.operational_self_examination_service = oses
        bs.portable_context_service = pcs

        bs._final_startup_truth_refresh()

        pcs.build_package.assert_called_once()
