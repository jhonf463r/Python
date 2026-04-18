from __future__ import annotations

import shutil
from pathlib import Path

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    CapabilityReadiness,
    CapabilityStatus,
    CapturedStep,
    EnvironmentRiskSignal,
    EnvironmentSelfModel,
    HiddenIncident,
    IncidentStatus,
    InferenceRequest,
    IssueSeverity,
)


def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = Path.cwd() / 'data' / name
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap


def _cleanup_bootstrap(bootstrap: AppBootstrap) -> None:
    workspace = getattr(bootstrap, '_test_workspace', None)
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)


def _seed_partial_wplay_teaching(bootstrap: AppBootstrap) -> None:
    episode = bootstrap.episode_repository.create_episode('Login Wplay debil', tags=['wplay'])
    bootstrap.episode_repository.save_step(
        episode.episode_id,
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='input',
            metadata={'field_role': 'email', 'url': 'https://wplay.co/login'},
        ),
    )


def test_self_teach_escalates_weak_wplay_login_to_pending_codex() -> None:
    bootstrap = _make_bootstrap('test_self_teach_wplay_codex_workspace')
    try:
        _seed_partial_wplay_teaching(bootstrap)
        bootstrap.hidden_incident_repository.save(
            HiddenIncident(
                site_id='wplay',
                incident_kind='bridge_lag',
                severity=IssueSeverity.MEDIUM,
                status=IncidentStatus.OPEN,
                summary='Bridge atrasado durante login Wplay.',
                probable_cause='La cola visible sigue acumulando retraso.',
            )
        )

        record = bootstrap.inference_service.infer_task(
            InferenceRequest(
                user_goal='abre Wplay e inicia sesion',
                auto_route=True,
                enable_planning=True,
                site_hint='wplay',
            )
        )
        payload = bootstrap.self_teach_orchestrator.run_diagnostic(record)

        assert payload['probe_diagnosis']['category'] == 'need_codex_fix'
        assert payload['scenario_run']['scenario']['scenario_id'] == 'wplay.login'
        assert payload['pending_issue']['scenario_id'] == 'wplay.login'
        assert payload['adaptive_session']['pending_issue_id']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_self_teach_applies_runtime_tuning_for_google_navigation_stall() -> None:
    bootstrap = _make_bootstrap('test_self_teach_runtime_tuning_workspace')
    try:
        bootstrap.capability_repository.save(
            CapabilityReadiness(
                capability_id='browser.search.google',
                title='Busqueda en Google',
                status=CapabilityStatus.READY,
                score=0.92,
                site_id='google',
                evidence=['snapshot operativo estable'],
                missing_signals=[],
                suggested_next_step='Seguir con la fase de busqueda.',
            )
        )
        bootstrap.hidden_incident_repository.save(
            HiddenIncident(
                site_id='google',
                incident_kind='navigation_stall',
                severity=IssueSeverity.HIGH,
                status=IncidentStatus.OPEN,
                summary='Navegacion de Google atascada.',
                probable_cause='Se detecto una pesta?a con progreso lento.',
            )
        )

        record = bootstrap.inference_service.infer_task(
            InferenceRequest(
                user_goal='busca en Google una pagina cualquiera',
                auto_route=True,
                enable_planning=True,
                site_hint='google',
            )
        )
        payload = bootstrap.self_teach_orchestrator.run_diagnostic(record)

        assert payload['probe_diagnosis']['category'] == 'need_runtime_tuning'
        assert payload['pending_issue'] is None
        assert len(payload['runtime_adjustments']) >= 1
        assert bootstrap.hidden_incident_detector.describe_thresholds()['navigation_stall_seconds'] >= 10.0
    finally:
        _cleanup_bootstrap(bootstrap)


def test_self_teach_guided_cycle_registers_repeated_error_learning() -> None:
    bootstrap = _make_bootstrap('test_self_teach_guided_cycle_workspace')
    try:
        _seed_partial_wplay_teaching(bootstrap)
        bootstrap.hidden_incident_repository.save(
            HiddenIncident(
                site_id='wplay',
                incident_kind='bridge_lag',
                severity=IssueSeverity.MEDIUM,
                status=IncidentStatus.OPEN,
                summary='Bridge atrasado durante login Wplay.',
                probable_cause='La cola visible sigue acumulando retraso.',
            )
        )

        first_record = bootstrap.inference_service.infer_task(
            InferenceRequest(
                user_goal='abre Wplay e inicia sesion',
                auto_route=True,
                enable_planning=True,
                site_hint='wplay',
            )
        )
        bootstrap.self_teach_orchestrator.run_guided_cycle(first_record)

        second_record = bootstrap.inference_service.infer_task(
            InferenceRequest(
                user_goal='abre Wplay e inicia sesion',
                auto_route=True,
                enable_planning=True,
                site_hint='wplay',
            )
        )
        payload = bootstrap.self_teach_orchestrator.run_guided_cycle(second_record)

        cycle = payload['guided_improvement_cycle']
        findings = {item['kind'] for item in cycle['detected_blockages']}

        assert 'repeated_error' in findings
        assert 'route_stuck' in findings
        assert cycle['trace_id']
        assert cycle['lab_run_id']
        assert payload['learning_registered']['subject_key'].startswith('guided_improvement:')
        logs = bootstrap.tool_record_repository.list_log(tool_id='self_teach_orchestrator', limit=5)
        assert any(entry.get('action_type') == 'guided_self_improvement' for entry in logs)
    finally:
        _cleanup_bootstrap(bootstrap)


def test_self_teach_guided_cycle_detects_hardware_pressure_without_breaking_cycle() -> None:
    bootstrap = _make_bootstrap('test_self_teach_hardware_pressure_workspace')
    try:
        _seed_partial_wplay_teaching(bootstrap)

        def fake_current_model() -> EnvironmentSelfModel:
            return EnvironmentSelfModel(
                environment_id='env-risky',
                scan_status='ready',
                risk_signals=[
                    EnvironmentRiskSignal(
                        kind='memory_pressure_critical',
                        severity=IssueSeverity.CRITICAL,
                        summary='La RAM libre cayo a nivel critico.',
                    )
                ],
            )

        bootstrap.environment_self_awareness_service.current_model = fake_current_model  # type: ignore[method-assign]
        bootstrap.environment_self_awareness_service.request_refresh = lambda **_: fake_current_model()  # type: ignore[method-assign]

        record = bootstrap.inference_service.infer_task(
            InferenceRequest(
                user_goal='abre Wplay e inicia sesion',
                auto_route=True,
                enable_planning=True,
                site_hint='wplay',
            )
        )
        payload = bootstrap.self_teach_orchestrator.run_guided_cycle(record)

        cycle = payload['guided_improvement_cycle']
        findings = {item['kind'] for item in cycle['detected_blockages']}
        proposals = {item['action_key'] for item in cycle['proposed_corrections']}

        assert 'hardware_pressure' in findings
        assert 'protect_hardware_before_heavy_retry' in proposals
        assert cycle['requires_user_decision'] is True
        assert 'Detecte riesgo de hardware' in ' '.join(cycle['notifications'])
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_command_routes_to_self_teach() -> None:
    bootstrap = _make_bootstrap('test_control_center_self_teach_command_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        captured: list[str] = []

        def fake_run_self_teach(text: str) -> None:
            captured.append(text)

        viewmodel.runSelfTeach = fake_run_self_teach  # type: ignore[method-assign]
        viewmodel.sendChat('prueba Wplay')

        assert captured == ['prueba Wplay']
        assert any(item.get('role') == 'user' and item.get('text') == 'prueba Wplay' for item in viewmodel.get_chat_messages())
    finally:
        _cleanup_bootstrap(bootstrap)
