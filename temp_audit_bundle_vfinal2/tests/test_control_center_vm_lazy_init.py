"""Tests for Brecha 1.1 — ControlCenterViewModel lazy init.

Validates that:
1. __init__ does not block the event loop (< 100ms)
2. _refresh_all_data populates data correctly
3. Heavy init failure does not crash the VM
4. QML properties have valid defaults before heavy init
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest


def _make_minimal_vm():
    """Build a ControlCenterViewModel with all deps mocked.

    Patches QTimer so nothing actually fires during construction —
    we call deferred methods explicitly in each test.
    """
    from iabv_v15.ui.viewmodels.control_center_viewmodel import (
        ControlCenterViewModel,
    )

    mock_config = MagicMock()
    mock_config.default_task_role = MagicMock()
    mock_config.default_task_role.value = 'research'

    mock_role_router = MagicMock()
    mock_role_router.role_profiles = []

    mock_dev_assist = MagicMock()
    mock_dev_assist.build_repo_bridge_summary.return_value = 'repo bridge loaded'
    mock_dev_assist.build_local_stack_summary.return_value = 'local stack loaded'

    mock_pbt = MagicMock()
    mock_pbt.load_state.return_value = {'candidates': []}

    with patch(
        'iabv_v15.ui.viewmodels.control_center_viewmodel.QTimer'
    ) as MockQTimer:
        MockQTimer.singleShot = MagicMock()

        vm = ControlCenterViewModel(
            config=mock_config,
            episode_repository=MagicMock(),
            knowledge_repository=MagicMock(),
            run_repository=MagicMock(),
            artifact_repository=MagicMock(),
            inference_service=MagicMock(),
            role_router=mock_role_router,
            adaptive_orchestrator=MagicMock(),
            training_orchestrator=MagicMock(),
            pbt_service=mock_pbt,
            development_assist_service=mock_dev_assist,
            engineering_review_service=MagicMock(),
            embedding_service=MagicMock(),
        )
    return vm


class TestInitDoesNotBlockEventLoop:
    def test_init_completes_under_100ms(self):
        """__init__ must complete in < 100ms (no heavy I/O)."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )

        mock_config = MagicMock()
        mock_config.default_task_role = MagicMock()
        mock_config.default_task_role.value = 'research'
        mock_role_router = MagicMock()
        mock_role_router.role_profiles = []
        mock_dev_assist = MagicMock()
        mock_dev_assist.build_repo_bridge_summary.return_value = ''
        mock_dev_assist.build_local_stack_summary.return_value = ''

        with patch(
            'iabv_v15.ui.viewmodels.control_center_viewmodel.QTimer'
        ) as MockQTimer:
            MockQTimer.singleShot = MagicMock()

            t0 = time.monotonic()
            vm = ControlCenterViewModel(
                config=mock_config,
                episode_repository=MagicMock(),
                knowledge_repository=MagicMock(),
                run_repository=MagicMock(),
                artifact_repository=MagicMock(),
                inference_service=MagicMock(),
                role_router=mock_role_router,
                adaptive_orchestrator=MagicMock(),
                training_orchestrator=MagicMock(),
                pbt_service=MagicMock(),
                development_assist_service=mock_dev_assist,
                engineering_review_service=MagicMock(),
                embedding_service=MagicMock(),
            )
            elapsed_ms = (time.monotonic() - t0) * 1000

        assert elapsed_ms < 100, f'__init__ took {elapsed_ms:.1f}ms (limit: 100ms)'
        # build_repo_bridge_summary must NOT have been called during __init__
        mock_dev_assist.build_repo_bridge_summary.assert_not_called()
        mock_dev_assist.build_local_stack_summary.assert_not_called()


class TestInitializeHeavyPopulatesData:
    def test_deferred_refresh_loads_data(self):
        """_refresh_all_data (called by deferred path) populates repo/stack text."""
        vm = _make_minimal_vm()
        assert vm._repo_bridge_text == ''
        assert vm._local_stack_text == ''
        vm._refresh_all_data()
        assert vm._repo_bridge_text == 'repo bridge loaded'
        assert vm._local_stack_text == 'local stack loaded'


class TestInitializeHeavyFailureDoesNotCrash:
    def test_heavy_init_failure_is_caught(self):
        """If _deferred_heavy_init fails, VM survives."""
        vm = _make_minimal_vm()
        vm.mcp_bridge_service = MagicMock()
        vm.mcp_bridge_service.attach_listener.side_effect = RuntimeError('boom')
        vm._deferred_heavy_init()
        assert vm is not None


class TestQmlPropertiesHaveDefaultsBeforeHeavyInit:
    def test_defaults_are_valid_before_heavy_init(self):
        """QML-visible properties must have safe defaults before heavy init."""
        vm = _make_minimal_vm()
        assert isinstance(vm._repo_bridge_text, str)
        assert isinstance(vm._local_stack_text, str)
        assert isinstance(vm._diagnostic_text, str)
        assert isinstance(vm._strategy_text, str)
        assert isinstance(vm._recommendation_text, str)
        assert isinstance(vm._legacy_summary, str)
        assert isinstance(vm._busy_label, str)
        assert isinstance(vm._progress_cards, list)
        assert isinstance(vm._evolution_area_cards, list)
        assert isinstance(vm._agent_cards, list)
        assert isinstance(vm._chat_messages, list)
        assert isinstance(vm._provider_cards, list)
        assert isinstance(vm._evolution_overview, dict)
        assert isinstance(vm._mcp_bridge_status, dict)
