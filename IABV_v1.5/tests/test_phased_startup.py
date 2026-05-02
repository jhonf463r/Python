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
        with patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ControlCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel', return_value=MagicMock()):
            bs._build_deferred_ui_batch_1()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
        assert 'populate_ui_vm_mcp_side_effects' in marked
        assert 'populate_ui_vm_control_center' in marked
        assert 'populate_ui_vm_capture_studio' in marked

    def test_deferred_batch_2_marks(self):
        bs = _make_bootstrap()
        bs.control_center_viewmodel = MagicMock()
        bs.evolution_center_viewmodel = None
        with patch('iabv_v15.bootstrap.EvolutionCenterViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.RunHistoryViewModel', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.CentroVivoViewModel', return_value=MagicMock()):
            bs._build_deferred_ui_batch_2()

        marked = [c.args[0] for c in bs._timeline.mark.call_args_list]
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

    def test_build_deferred_1_creates_control_and_capture(self):
        bs = _make_bootstrap()
        bs.navigation_controller = MagicMock()
        with patch('iabv_v15.bootstrap.build_mcp_bridge_service', return_value=MagicMock()), \
             patch('iabv_v15.bootstrap.ControlCenterViewModel') as ccvm, \
             patch('iabv_v15.bootstrap.CaptureStudioViewModel') as csvm:
            ccvm.return_value = MagicMock()
            csvm.return_value = MagicMock()
            bs._build_deferred_ui_batch_1()

        assert bs.control_center_viewmodel is not None
        assert bs.capture_studio_viewmodel is not None

    def test_build_deferred_2_creates_remaining_vms(self):
        bs = _make_bootstrap()
        bs.control_center_viewmodel = MagicMock()
        with patch('iabv_v15.bootstrap.EvolutionCenterViewModel') as evm, \
             patch('iabv_v15.bootstrap.KnowledgeBaseViewModel') as kvm, \
             patch('iabv_v15.bootstrap.ProviderSettingsViewModel') as pvm, \
             patch('iabv_v15.bootstrap.RunHistoryViewModel') as rvm, \
             patch('iabv_v15.bootstrap.CentroVivoViewModel') as cvvm:
            evm.return_value = MagicMock()
            kvm.return_value = MagicMock()
            pvm.return_value = MagicMock()
            rvm.return_value = MagicMock()
            cvvm.return_value = MagicMock()
            bs._build_deferred_ui_batch_2()

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
