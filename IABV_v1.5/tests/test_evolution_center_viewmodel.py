from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("PySide6")

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.ui.viewmodels import evolution_center_viewmodel as evolution_center_vm
from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    BackgroundProcessSnapshot,
    DossierScope,
    EvaluationRoute,
    ExecutionDossier,
    ExperimentDomain,
    HiddenIncident,
    IncidentStatus,
    IssueSeverity,
    NetworkStatusSnapshot,
    RunStatus,
    ToolLiveStatus,
    WindowObservation,
    WorldModelSnapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dossier(dossier_id: str, *, minutes: int, episode_id: str) -> ExecutionDossier:
    created = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return ExecutionDossier(
        dossier_id=dossier_id,
        created_at_utc=created,
        scope=DossierScope.TEACHING,
        title=f'Dossier {dossier_id}',
        summary='resumen',
        episode_id=episode_id,
        status=RunStatus.SUCCESS,
        severity=IssueSeverity.LOW,
    )


def _incident(incident_id: str, *, minutes: int, episode_id: str) -> HiddenIncident:
    created = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return HiddenIncident(
        incident_id=incident_id,
        created_at_utc=created,
        updated_at_utc=created,
        episode_id=episode_id,
        site_id='wplay',
        incident_kind='bridge_lag',
        severity=IssueSeverity.MEDIUM,
        status=IncidentStatus.OPEN,
        summary=f'Incidente {incident_id}',
    )


def test_evolution_center_bootstrap_reuses_cached_portable_context() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_cached_portable_context')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)

    class _FakePackage:
        def model_dump(self, *, mode: str = 'json') -> dict[str, object]:
            return {
                'assistant_brief': 'Contexto portable cacheado.',
                'package_path': str(workspace / 'portable.json'),
                'metadata': {},
            }

    try:
        bootstrap = AppBootstrap(str(workspace))
        calls: list[bool] = []

        def _current_package(*, refresh: bool = False, **_: object) -> _FakePackage:
            calls.append(refresh)
            return _FakePackage()

        bootstrap.portable_context_service.current_package = _current_package  # type: ignore[method-assign]
        bootstrap._build_ui_objects()

        assert calls
        assert calls[0] is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_auto_follows_latest_records_until_user_pins_selection() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_follow_latest')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        old_dossier = _dossier('old-dossier', minutes=0, episode_id='ep-old')
        old_incident = _incident('old-incident', minutes=0, episode_id='ep-old')
        bootstrap.execution_dossier_repository.save(old_dossier)
        bootstrap.hidden_incident_repository.save(old_incident)
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        assert vm.get_selected_dossier()['dossier_id'] == 'old-dossier'
        assert vm.get_selected_incident()['incident_id'] == 'old-incident'

        new_dossier = _dossier('new-dossier', minutes=5, episode_id='ep-new')
        new_incident = _incident('new-incident', minutes=5, episode_id='ep-new')
        bootstrap.execution_dossier_repository.save(new_dossier)
        bootstrap.hidden_incident_repository.save(new_incident)
        vm.refresh()

        assert vm.get_selected_dossier()['dossier_id'] == 'new-dossier'
        assert vm.get_selected_incident()['incident_id'] == 'new-incident'
        assert 'new-incident' in vm.get_latest_packet()

        vm.selectIncident('old-incident')
        pinned_incident = vm.get_selected_incident()['incident_id']
        newest_incident = _incident('newest-incident', minutes=10, episode_id='ep-brand-new')
        bootstrap.hidden_incident_repository.save(newest_incident)
        vm.refresh()

        assert vm.get_selected_incident()['incident_id'] == pinned_incident
        assert 'old-incident' in vm.get_latest_packet()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_selecting_dossier_clears_incident_packet_context() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_packet_context')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        dossier = _dossier('dossier-1', minutes=0, episode_id='episode-1')
        incident = _incident('incident-1', minutes=0, episode_id='episode-incident')
        bootstrap.execution_dossier_repository.save(dossier)
        bootstrap.hidden_incident_repository.save(incident)
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        vm.selectIncident('incident-1')
        assert vm.get_selected_incident()['incident_id'] == 'incident-1'

        vm.selectDossier('dossier-1')

        assert vm.get_selected_incident() == {}
        assert vm.get_selected_dossier()['dossier_id'] == 'dossier-1'
        assert 'episode-1' in vm.get_latest_packet()
        assert 'incident-1' not in vm.get_latest_packet()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_sandbox_status_is_copyable(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_copy_tool_status')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    copied = {'text': ''}

    class FakeClipboard:
        def setText(self, text: str) -> None:
            copied['text'] = text

    monkeypatch.setattr(evolution_center_vm.QGuiApplication, 'clipboard', staticmethod(lambda: FakeClipboard()))
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        vm.sandboxToolCard('codex_installed')
        status = vm.get_latest_tool_status()

        assert 'Herramienta: Codex instalado (codex_installed)' in status
        assert 'Estado: waiting_approval' in status
        assert 'Respuesta: captura automatica por clipboard con fallback manual si no aparece texto util' in status
        assert 'Auditoria viva: stop_and_wait_user' in status

        vm.copyLatestToolStatus()

        assert 'copiado al portapapeles' in vm.get_clipboard_notice().lower()
        assert copied['text'] == status
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_base_tool_audit_collects_multiple_statuses() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_audit_base_tools')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        vm.auditBaseTools()
        status = vm.get_latest_tool_status()

        assert 'Auditoria base completada.' in status
        assert 'Herramienta: Ollama local (ollama_llm)' in status
        assert 'Herramienta: Playwright browser (playwright_browser)' in status
        assert 'Herramienta: Desktop human runner (desktop_human_runner)' in status
        assert 'Herramienta: Codex instalado (codex_installed)' in status
        assert 'Herramienta: ChatGPT instalado (chatgpt_installed)' in status
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_exposes_and_copies_portable_context(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_portable_context')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    copied = {'text': ''}

    class FakeClipboard:
        def setText(self, text: str) -> None:
            copied['text'] = text

    monkeypatch.setattr(evolution_center_vm.QGuiApplication, 'clipboard', staticmethod(lambda: FakeClipboard()))
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        portable = vm.get_portable_context()

        assert portable
        assert portable.get('assistant_brief')
        assert portable.get('package_path')

        vm.copyPortableContext()

        assert 'copiado al portapapeles' in vm.get_clipboard_notice().lower()
        assert copied['text'] == vm.get_portable_context_brief()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_exposes_tool_evolution_panel_from_portable_context() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_tool_evolution_panel')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)

    class _FakePackage:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def model_dump(self, *, mode: str = 'json') -> dict[str, object]:
            return dict(self._payload)

    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None
        service = bootstrap.portable_context_service
        assert service is not None

        service.current_package = lambda refresh=True: _FakePackage(  # type: ignore[assignment]
            {
                'assistant_brief': 'Estado portable listo.',
                'package_path': str(workspace / 'portable.json'),
                'metadata': {
                    'tool_evolution_summary': {
                        'winning_by_problem': {'language_understanding': 'chatgpt'},
                        'in_validation': ['validate_discovery:ollama:language_understanding'],
                        'recent_decisions': [{'decision': 'deferred', 'reason': 'Sandbox parcial.'}],
                        'discarded_proposals': [{'status': 'discarded', 'assistant_kind': 'claude'}],
                    },
                    'tool_discovery_summary': {
                        'active_signals': [{'tool_title': 'Ollama local', 'assistant_kind': 'ollama'}],
                    },
                },
            }
        )

        vm.refresh()
        panel = vm.get_tool_evolution_panel()

        assert panel
        assert panel.get('winning_by_problem', {}).get('language_understanding') == 'chatgpt'
        assert panel.get('in_validation') == ['validate_discovery:ollama:language_understanding']
        assert panel.get('discoveries_recent', [])[0].get('assistant_kind') == 'ollama'
        assert panel.get('latest_decisions', [])[0].get('decision') == 'deferred'
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_exposes_and_copies_self_examination(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_self_examination')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    copied = {'text': ''}

    class FakeClipboard:
        def setText(self, text: str) -> None:
            copied['text'] = text

    monkeypatch.setattr(evolution_center_vm.QGuiApplication, 'clipboard', staticmethod(lambda: FakeClipboard()))
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        self_examination = vm.get_self_examination()

        assert self_examination
        assert self_examination.get('assistant_brief')
        assert self_examination.get('package_path')

        vm.copySelfExamination()

        assert 'copiada al portapapeles' in vm.get_clipboard_notice().lower()
        assert copied['text'] == vm.get_self_examination_brief()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_refresh_reuses_cached_self_examination_after_portable_context_refresh() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_self_exam_refresh_reuse')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None
        service = bootstrap.operational_self_examination_service
        assert service is not None

        original = service.current_review
        calls: list[bool] = []

        def tracked_current_review(*, refresh: bool = False, max_age_seconds: int = 300):
            calls.append(bool(refresh))
            return original(refresh=refresh, max_age_seconds=max_age_seconds)

        service.current_review = tracked_current_review  # type: ignore[assignment]

        vm.refresh()

        assert calls
        assert calls.count(True) == 1
        assert calls[-1] is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_surfaces_ia_comparison_recommendations() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_ia_comparisons')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap.experiment_lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Diagnosticar incidente del bridge',
            subject_key='incident.bridge',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_installed',
            success=True,
            observed_summary='Ajustar cola y drenado del bridge visible.',
            precision=0.88,
            robustness=0.83,
            execution_ms=210,
            metadata={
                'assistant_kind': 'codex',
                'assistant_configuration': AssistantConfigurationSnapshot(
                    planning_mode='with_plan',
                    reasoning_level='extended',
                    tools_mode='with_tools',
                    assistant_mode='code',
                    origin_mode='external',
                ).model_dump(mode='json'),
                'config_signature': 'with_plan|without_files|extended|short|with_tools|without_browser|code|external',
                'trace_id': 'trace-codex-1',
                'comparison_scope_key': 'incident-bridge',
            },
        )
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        comparisons = vm.get_ia_comparisons()

        assert comparisons
        assert comparisons[0]['recommended_assistant_kind'] == 'codex'
        assert 'incident-bridge' in comparisons[0]['comparison_scope_keys']
        assert 'trace-codex-1' in comparisons[0]['winning_trace_ids']
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_exposes_environment_self_model() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_environment_self_model')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        environment = vm.get_environment_self_model()

        assert environment
        assert environment.get('environment_id')
        assert environment.get('scan_status') in {'ready', 'partial'}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_exposes_world_model() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_world_model')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        assert bootstrap.world_model_service is not None
        bootstrap.world_model_service._current_snapshot = WorldModelSnapshot(
            active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=51, focused=True)],
            focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=51, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    status='abierto',
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                )
            ],
            network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
            background_processes=[BackgroundProcessSnapshot(process_name='OneDrive', pid=99, state='memory_heavy')],
            detected_blocks=['wrong_thread'],
            confidence=0.81,
        )
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        vm.refresh()
        world_model = vm.get_world_model()

        assert world_model
        assert world_model['focused_window']['title'] == 'Codex - IABV'
        assert world_model['network_status']['status'] == 'conectado'
        assert world_model['tool_live_status'][0]['thread_status'] == 'otro_hilo_activo'
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# Tests para señales evolutivas UI (Task B)

def test_evolution_center_emits_credential_prompt_requested() -> None:
    """Verifica que el ViewModel emite credentialPromptRequested."""
    workspace = Path.cwd() / 'data' / f'test_ec_credential_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    try:
        viewmodel = bootstrap.evolution_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_credential_requested(payload):
            received['payload'] = payload

        viewmodel.credentialPromptRequested.connect(on_credential_requested)
        test_payload = {'domain': 'api.example.com', 'reason': 'API key required', 'username_hint': 'api_user'}
        viewmodel.credentialPromptRequested.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['domain'] == 'api.example.com'
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_emits_clarification_requested() -> None:
    """Verifica que el ViewModel emite clarificationRequested."""
    workspace = Path.cwd() / 'data' / f'test_ec_clarification_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    try:
        viewmodel = bootstrap.evolution_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_clarification_requested(payload):
            received['payload'] = payload

        viewmodel.clarificationRequested.connect(on_clarification_requested)
        test_payload = {'id': '456', 'question': 'Select severity?', 'options': ['Low', 'Medium', 'High'], 'context': 'Incident review'}
        viewmodel.clarificationRequested.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['question'] == 'Select severity?'
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_emits_missing_dependency_requested() -> None:
    """Verifica que el ViewModel emite missingDependencyRequested."""
    workspace = Path.cwd() / 'data' / f'test_ec_dependency_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    try:
        viewmodel = bootstrap.evolution_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_dependency_requested(payload):
            received['payload'] = payload

        viewmodel.missingDependencyRequested.connect(on_dependency_requested)
        test_payload = {'package_name': 'pytest-asyncio', 'manager': 'pip', 'reason': 'Required for async tests'}
        viewmodel.missingDependencyRequested.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['package_name'] == 'pytest-asyncio'
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_emits_background_activity_changed() -> None:
    """Verifica que el ViewModel emite backgroundActivityChanged."""
    workspace = Path.cwd() / 'data' / f'test_ec_activity_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    try:
        viewmodel = bootstrap.evolution_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_activity_changed(payload):
            received['payload'] = payload

        viewmodel.backgroundActivityChanged.connect(on_activity_changed)
        test_payload = {'text': 'Analyzing dossiers...', 'progress': 75, 'status': 'running', 'details': ['Step 2 of 3']}
        viewmodel.backgroundActivityChanged.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['progress'] == 75
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_emits_provider_health_changed() -> None:
    """Verifica que el ViewModel emite providerHealthChanged."""
    workspace = Path.cwd() / 'data' / f'test_ec_health_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    try:
        viewmodel = bootstrap.evolution_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_health_changed(payload):
            received['payload'] = payload

        viewmodel.providerHealthChanged.connect(on_health_changed)
        test_payload = [{'name': 'Codex', 'status': 'ready', 'latency': 50}, {'name': 'Ollama', 'status': 'degraded', 'latency': 500}]
        viewmodel.providerHealthChanged.emit(test_payload)

        assert received['payload'] is not None
        assert len(received['payload']) == 2
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

