from __future__ import annotations

from pathlib import Path

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import InferenceRequest, TaskIntent
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.evolution.environment_self_awareness_service import (
    EnvironmentSelfAwarenessService,
)
from iabv_v15.services.evolution.world_model_service import WorldModelService


def test_effect_bounded_bootstrap_keeps_real_composition_without_observer_scans(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv('IABV_DATA_DIR', str(tmp_path / 'data'))
    # The effect-bounded contract overrides an explicit request for the
    # deferred tool probe, both during wiring and post-window setup.
    monkeypatch.setenv('IABV_DEFER_TOOL_PROBE', '0')

    scan_calls: list[str] = []

    def reject_environment_scan(self, **kwargs):
        scan_calls.append('environment')
        raise AssertionError('bounded bootstrap must not call environment scan_now')

    def reject_world_scan(self, **kwargs):
        scan_calls.append('world_model')
        raise AssertionError('bounded bootstrap must not call world-model scan_now')

    def reject_tool_probe(self):
        raise AssertionError('bounded bootstrap must not run tool availability probes')

    # Exercise production defaults for auto_start rather than relying on
    # PYTEST_CURRENT_TEST to suppress the observer threads.
    monkeypatch.setattr(EnvironmentSelfAwarenessService, '_in_test_mode', lambda self: False)
    monkeypatch.setattr(WorldModelService, '_in_test_mode', lambda self: False)
    monkeypatch.setattr(EnvironmentSelfAwarenessService, 'scan_now', reject_environment_scan)
    monkeypatch.setattr(WorldModelService, 'scan_now', reject_world_scan)
    monkeypatch.setattr(AppBootstrap, '_log_tool_availability', reject_tool_probe)

    bootstrap = AppBootstrap(str(tmp_path / 'workspace'), effect_bounded=True)

    assert bootstrap.inference_service is not None
    assert bootstrap.adaptive_task_orchestrator is not None
    assert bootstrap.role_router is not None
    assert isinstance(bootstrap.task_context_assembler, TaskContextAssembler)
    assert isinstance(bootstrap.environment_self_awareness_service, EnvironmentSelfAwarenessService)
    assert isinstance(bootstrap.world_model_service, WorldModelService)
    assert bootstrap.task_context_assembler.environment_self_awareness_service is bootstrap.environment_self_awareness_service
    assert bootstrap.task_context_assembler.world_model_service is bootstrap.world_model_service

    environment = bootstrap.environment_self_awareness_service
    world_model = bootstrap.world_model_service
    assert environment._auto_start is False
    assert world_model._auto_start is False
    assert environment._thread is None
    assert world_model._thread is None
    assert environment.refresh_enabled is False
    assert world_model.refresh_enabled is False
    assert scan_calls == []
    bootstrap._run_deferred_post_window_setup()
    assert scan_calls == []

    environment_model = environment.current_model()
    world_snapshot = world_model.current_model()
    assert environment_model is not None
    assert world_snapshot is not None

    # These are the actual perception helpers called by TaskContextAssembler;
    # the external-consultation parameters exercise its full-refresh branch.
    request = InferenceRequest(
        user_goal='Consultar externamente a Devin sobre el estado técnico.',
        goal_parameters={
            'explicit_external_consultation': True,
            'consultation_scope': 'external_assistant',
        },
    )
    intent = TaskIntent(intent_key='research.external_consultation')
    assert bootstrap.task_context_assembler._environment_self_model() is not None
    assert bootstrap.task_context_assembler._world_model(request=request, intent=intent) is not None

    assert environment.request_refresh(reason='test', full=True) is not None
    assert world_model.request_refresh(reason='test', full=True) is not None
    assert scan_calls == []
    assert environment.current_model() is not None
    assert world_model.current_model() is not None


def test_default_bootstrap_keeps_observer_refresh_behavior(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv('IABV_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('IABV_DEFER_TOOL_PROBE', '1')

    scan_calls: list[str] = []

    def observe_environment_scan(self, **kwargs):
        scan_calls.append('environment')
        return self.current_model()

    def observe_world_scan(self, **kwargs):
        scan_calls.append('world_model')
        return self.current_model()

    # Retain bootstrap_scan and refresh behavior while intercepting the scan
    # boundary so this compatibility test performs no network/provider probes.
    monkeypatch.setattr(EnvironmentSelfAwarenessService, 'scan_now', observe_environment_scan)
    monkeypatch.setattr(WorldModelService, 'scan_now', observe_world_scan)
    bootstrap = AppBootstrap(str(tmp_path / 'workspace'))

    assert bootstrap.environment_self_awareness_service.refresh_enabled is True
    assert bootstrap.world_model_service.refresh_enabled is True
    assert 'environment' in scan_calls
    assert 'world_model' in scan_calls
