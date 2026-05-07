from __future__ import annotations

import os
import shutil
import time
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


def _drain_evolution_vm(predicate, *, timeout_seconds: float = 30.0) -> None:
    app = evolution_center_vm.QGuiApplication.instance()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if app is not None:
            app.processEvents()
        if predicate():
            return
        time.sleep(0.05)
    if app is not None:
        app.processEvents()


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
        assert any(keyword in status for keyword in ('Estado: waiting_approval', 'Estado: adapter_missing'))
        assert any(keyword in status for keyword in (
            'Respuesta: captura automatica por clipboard con fallback manual si no aparece texto util',
            'Auditoria viva:',
            'tool_adapter_missing',
        ))

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
        _drain_evolution_vm(
            lambda: (
                'Auditoria base completada.' in vm.get_latest_tool_status()
                or 'Error en auditoria' in vm.get_latest_tool_status()
            )
        )
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
        assert all(c is False for c in calls)
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
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = Path.cwd() / 'data' / f'test_ec_credential_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
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
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = Path.cwd() / 'data' / f'test_ec_clarification_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
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
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = Path.cwd() / 'data' / f'test_ec_dependency_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
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
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = Path.cwd() / 'data' / f'test_ec_activity_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
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
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = Path.cwd() / 'data' / f'test_ec_health_signal_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
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



def test_evolution_center_exposes_proactive_dashboard_from_service() -> None:
    """Gap #107 wiring: si bootstrap setea `proactive_dashboard_service` en el
    VM, `refresh()` debe poblar `proactiveDashboard` con la snapshot
    serializada a dict y `proactiveDashboardBrief` con el resumen humano.
    """
    import threading
    import time as _time

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_proactive_dashboard')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    request_thread: threading.Thread | None = None
    broker = None
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None
        assert vm.proactive_dashboard_service is not None, (
            'bootstrap debe wirear el servicio en el VM (regresion del PR #107)'
        )

        broker = bootstrap.human_approval_broker
        # Handler no resolvente: el request quedara "pending" hasta que
        # cancelemos manualmente al final del test.
        broker.register_prompt_handler(lambda _payload: None)

        def _fire_request() -> None:
            try:
                broker.request(
                    kind='login_required',
                    reason='wplay requiere login humano',
                    scope={'assistant': 'wplay', 'domain': 'wplay.com'},
                    timeout_s=5.0,
                )
            except Exception:
                pass

        request_thread = threading.Thread(target=_fire_request, daemon=True)
        request_thread.start()

        # Esperamos que el broker registre el pending.
        for _ in range(200):
            if broker.pending_count() >= 1:
                break
            _time.sleep(0.01)
        assert broker.pending_count() == 1, 'broker no registro el pending en tiempo razonable'

        vm.refresh()

        dashboard = vm.get_proactive_dashboard()
        assert isinstance(dashboard, dict)
        assert dashboard['pending_attention_count'] == 1
        assert dashboard['entries'], 'debe haber al menos un entry serializado'
        approval_entries = [e for e in dashboard['entries'] if e['kind'] == 'approval_request']
        assert approval_entries, 'debe haber un approval_request entre los entries'
        entry = approval_entries[0]
        assert entry['severity'] == 'critical', 'login_required mapea a severity=critical'
        assert 'wplay' in entry['title'].lower()
        assert entry['scope']['assistant'] == 'wplay'

        brief = vm.get_proactive_dashboard_brief()
        assert '1 pendiente' in brief

        proactive_prop = vm.proactiveDashboard
        assert proactive_prop['pending_attention_count'] == 1
    finally:
        # cleanup: cancelamos la request para liberar el thread, sino queda
        # bloqueado hasta timeout_s (5s) y deja leak entre tests.
        if broker is not None:
            for pending in list(broker.pending_requests()):
                broker.cancel(pending['id'])
        if request_thread is not None:
            request_thread.join(timeout=2.0)
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_proactive_dashboard_empty_when_service_not_wired() -> None:
    """Si el servicio no esta seteado, `proactiveDashboard` debe ser `{}`
    y no levantar excepcion. Respeta AGENTS.md: el VM no inventa datos.
    """
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_no_dashboard_service')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None
        # Simulamos entorno sin wiring: el VM debe aguantar sin romper.
        vm.proactive_dashboard_service = None
        vm.refresh()
        assert vm.get_proactive_dashboard() == {}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_exposes_recent_ui_screenshots_from_service() -> None:
    """F1.1: cuando `UIScreenshotService` esta wired, el VM debe exponer
    los records recientes serializados como dicts.
    """
    from iabv_v15.services.capture.ui_screenshot_service import (
        NoopUIScreenshotProvider,
        UIScreenshotService,
    )

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_ui_screenshots')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None

        storage = workspace / 'ui_snapshots'
        service = UIScreenshotService(
            storage_dir=storage,
            provider=NoopUIScreenshotProvider(),
        )
        service.capture(source='vm_wiring_test', scope={'surface': 'evolution_center'})
        vm.ui_screenshot_service = service
        vm.refresh()

        records = vm.get_recent_ui_screenshots()
        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0]['source'] == 'vm_wiring_test'
        assert records[0]['scope'] == {'surface': 'evolution_center'}
        assert records[0]['success'] is True
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_recent_ui_screenshots_empty_when_service_not_wired() -> None:
    """F1.1: sin wiring, `recentUiScreenshots` debe ser `[]` y no romper."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_no_ui_screenshot_service')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None
        vm.ui_screenshot_service = None
        vm.refresh()
        assert vm.get_recent_ui_screenshots() == []
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_publish_branch_as_pr_delegates_to_service() -> None:
    """F2.2: el slot dispara el servicio en un thread y expone el resultado."""
    import threading as _threading
    from dataclasses import dataclass, field
    from typing import Any as _Any, Mapping as _Mapping

    @dataclass(frozen=True)
    class _FakePublishResult:
        success: bool = True
        branch: str = ''
        base: str = 'main'
        pr_number: int | None = None
        pr_url: str = ''
        http_status: int | None = 201
        pushed: bool = True
        blocked_by_policy: bool = False
        required_approval: bool = False
        approval_granted: bool = False
        error: str = ''
        evidence_path: str = ''
        extra: _Mapping[str, _Any] = field(default_factory=dict)

    class _FakeGitHubRemoteService:
        def __init__(self) -> None:
            self.calls: list[dict[str, _Any]] = []
            self._done = _threading.Event()

        def publish_branch_as_pr(self, **kwargs: _Any) -> _FakePublishResult:
            self.calls.append(kwargs)
            try:
                return _FakePublishResult(
                    success=True,
                    branch=kwargs.get('branch', ''),
                    base=kwargs.get('base', 'main'),
                    pr_number=42,
                    pr_url='https://github.com/jhonf463r/Python/pull/42',
                    pushed=True,
                )
            finally:
                self._done.set()

        def wait(self, timeout: float = 5.0) -> bool:
            return self._done.wait(timeout)

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_publish_pr')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        assert vm is not None
        fake = _FakeGitHubRemoteService()
        vm.github_remote_service = fake

        vm.publishBranchAsPR(
            'iabv-auto/test-f2-2',
            'Test F2.2 PR',
            'body here',
            'main',
            25,
            False,
        )
        assert fake.wait(timeout=5.0), 'publish_branch_as_pr no fue invocado'

        # Esperar a que el worker emita taskResolved y _apply_result corra.
        # Qt Slots invocados desde un thread no-Qt se despachan via QueuedConnection;
        # en modo offscreen el loop no corre, asi que invocamos _apply_result a mano
        # con el payload serializado para validar el flujo de estado del VM.
        assert len(fake.calls) == 1
        call = fake.calls[0]
        assert call['branch'] == 'iabv-auto/test-f2-2'
        assert call['title'] == 'Test F2.2 PR'
        assert call['body'] == 'body here'
        assert call['base'] == 'main'
        assert call['diff_lines'] == 25
        assert call['draft'] is False

        payload = vm._serialize_publish_result(
            type(
                '_R',
                (),
                dict(
                    success=True,
                    branch='iabv-auto/test-f2-2',
                    base='main',
                    pr_number=42,
                    pr_url='https://github.com/jhonf463r/Python/pull/42',
                    http_status=201,
                    pushed=True,
                    blocked_by_policy=False,
                    required_approval=False,
                    approval_granted=False,
                    error='',
                    evidence_path='',
                ),
            )(),
        )
        vm._apply_result('publish_pr', payload)
        assert vm.get_publish_pr_result()['pr_number'] == 42
        assert 'PR #42' in vm.get_publish_pr_status()
        assert vm.get_working() is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_publish_branch_as_pr_requires_branch_and_title() -> None:
    """F2.2: sin rama o titulo validos, el slot no invoca el servicio."""
    import threading as _threading
    from typing import Any as _Any

    class _SpyService:
        def __init__(self) -> None:
            self.calls = 0

        def publish_branch_as_pr(self, **kwargs: _Any) -> None:
            self.calls += 1

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_publish_pr_validation')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        spy = _SpyService()
        vm.github_remote_service = spy

        vm.publishBranchAsPR('', 'titulo', 'body', 'main', 0, False)
        assert 'Falta el nombre de la rama' in vm.get_publish_pr_status()

        vm.publishBranchAsPR('iabv-auto/x', '  ', 'body', 'main', 0, False)
        assert 'Falta el titulo' in vm.get_publish_pr_status()
        assert spy.calls == 0

        vm.github_remote_service = None
        vm.publishBranchAsPR('iabv-auto/x', 'titulo', 'body', 'main', 0, False)
        assert 'GitHubRemoteService' in vm.get_publish_pr_status()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_evolution_center_publish_pr_status_formatter() -> None:
    """F2.2: formateador de status cubre los caminos success / blocked / approval / error."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_evolution_center_publish_pr_format')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()
        vm = bootstrap.evolution_center_viewmodel
        fmt = vm._format_publish_pr_status

        ok = fmt({'success': True, 'branch': 'iabv-auto/ok', 'pr_number': 7, 'pr_url': 'https://github.com/x/y/pull/7'})
        assert 'PR #7' in ok
        assert 'iabv-auto/ok' in ok

        blocked = fmt({'success': False, 'blocked_by_policy': True, 'branch': 'devin/x', 'error': 'requires human approval'})
        assert 'Policy bloqueo' in blocked

        awaiting = fmt({'success': False, 'required_approval': True, 'approval_granted': False, 'branch': 'devin/x'})
        assert 'aprobacion humana' in awaiting

        err = fmt({'success': False, 'branch': 'iabv-auto/x', 'error': 'push failed'})
        assert 'push failed' in err
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
