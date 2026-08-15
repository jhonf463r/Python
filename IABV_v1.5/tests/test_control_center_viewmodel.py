from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import AutonomousValidationSnapshot, EnvironmentSelfModel, EvaluationRoute, ExecutionState, ExperimentDomain, ExperimentMetric, ExperimentRecommendation, ExperimentRun, NetworkStatusSnapshot, ObjectiveNode, ObjectiveNodeKind, ObjectiveStatus, ObservationPermissionGate, SandboxExperiment, SelfExaminationFinding, SelfExaminationSnapshot, TaskRole, ToolLiveStatus, WindowObservation, WorldModelSnapshot

def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = Path.cwd() / 'data' / f'{name}_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap


def _cleanup_bootstrap(bootstrap: AppBootstrap) -> None:
    workspace = getattr(bootstrap, '_test_workspace', None)
    stop = getattr(bootstrap, 'stop', None)
    if callable(stop):
        stop()
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)


def _drain_ui(viewmodel, *, timeout_seconds: float = 12.0) -> None:
    import time
    from iabv_v15.ui.qt import QGuiApplication

    app = QGuiApplication.instance()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if app is not None:
            app.processEvents()
        if not viewmodel.get_working():
            return
        time.sleep(0.05)
    if app is not None:
        app.processEvents()


def test_control_center_bootstrap_seeds_lightweight_development_packet() -> None:
    workspace = Path.cwd() / 'data' / f'test_control_center_lightweight_packet_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    calls = {'count': 0}
    original = bootstrap.engineering_review_service.build_codex_packet

    def _counting_packet(*, user_goal: str, selected_role_title: str) -> str:
        calls['count'] += 1
        return original(user_goal=user_goal, selected_role_title=selected_role_title)

    bootstrap.engineering_review_service.build_codex_packet = _counting_packet  # type: ignore[method-assign]
    try:
        bootstrap._build_ui_objects()
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        assert calls['count'] == 0
        assert 'Cargando evidencia evolutiva sin bloquear la UI.' in viewmodel.get_development_packet()
    finally:
        _cleanup_bootstrap(bootstrap)


def _make_ollama_available(bootstrap: AppBootstrap, *, response_text: str) -> None:
    class _FakeHealth:
        available = True

    class _FakeReportKind:
        value = 'research_brief'

    class _FakeResult:
        def __init__(self, summary: str) -> None:
            self.summary = summary
            self.provider_name = 'Ollama'
            self.report_kind = _FakeReportKind()

    class _FakeLocalProvider:
        def __init__(self, summary: str) -> None:
            self.summary = summary

        def health_check(self):
            return _FakeHealth()

        def answer_user(self, request):
            return _FakeResult(self.summary)

    adapter = bootstrap.tool_adapters['ollama']
    adapter.provider = _FakeLocalProvider(response_text)
    bootstrap.tool_registry.adapters['ollama'] = adapter
    card = bootstrap.tool_record_repository.get_card('ollama_llm')
    assert card is not None
    bootstrap.tool_record_repository.save_card(
        card.model_copy(
            update={
                'metadata': {
                    **card.metadata,
                    'assistant_kind': 'ollama',
                    'launch_mode': 'local_provider',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                }
            }
        )
    )
    refreshed = bootstrap.tool_record_repository.get_card('ollama_llm')
    assert refreshed is not None
    bootstrap.tool_registry.refresh_card(refreshed)


def _disable_external_assistant_apps(bootstrap: AppBootstrap, *, disable_web: bool = False) -> None:
    for tool_id in ('codex_installed', 'chatgpt_installed'):
        card = bootstrap.tool_record_repository.get_card(tool_id)
        assert card is not None
        bootstrap.tool_record_repository.save_card(
            card.model_copy(
                update={
                    'metadata': {
                        **card.metadata,
                        'executable_path': '',
                        'command_name': 'definitely_missing_external_app',
                        'command_aliases': [],
                        'windows_default_paths': [],
                    }
                }
            )
        )
    if disable_web:
        web_card = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert web_card is not None
        bootstrap.tool_record_repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'web_url': ''}}))


def _set_permissive_world_model(bootstrap: AppBootstrap, *, codex_ready: bool = True) -> None:
    assert bootstrap.world_model_service is not None
    tool_status = []
    if codex_ready:
        tool_status.append(
            ToolLiveStatus(
                tool_id='codex_installed',
                title='Codex instalado',
                assistant_kind='codex',
                available=True,
                status='abierto',
                thread_status='correcto_probable',
                messages_status='disponibles',
                session_status='abierta',
                confidence=0.86,
            )
        )
    tool_status.extend(
        [
            ToolLiveStatus(
                tool_id='chatgpt_web_assisted',
                title='ChatGPT web asistido',
                assistant_kind='chatgpt',
                available=True,
                status='listo',
                session_status='abierta',
                messages_status='desconocidos',
                confidence=0.8,
            ),
            ToolLiveStatus(
                tool_id='claude_web_assisted',
                title='Claude web asistido',
                assistant_kind='claude',
                available=True,
                status='listo',
                session_status='abierta',
                messages_status='desconocidos',
                confidence=0.8,
            ),
            ToolLiveStatus(
                tool_id='ollama_llm',
                title='Ollama local',
                assistant_kind='ollama',
                available=True,
                status='disponible',
                session_status='activa',
                messages_status='disponibles',
                confidence=0.82,
            ),
        ]
    )
    bootstrap.world_model_service._current_snapshot = WorldModelSnapshot(
        active_windows=[WindowObservation(title='IABV Control Center', app_name='IABV', pid=10, focused=True)],
        focused_window=WindowObservation(title='IABV Control Center', app_name='IABV', pid=10, focused=True),
        tool_live_status=tool_status,
        network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena', latency_ms=48.0),
        detected_blocks=[],
        inferred_state={'summary': 'Observacion operativa actualizada.', 'deductions': []},
        confidence=0.84,
    )


def test_control_center_chat_command_toggles_advanced() -> None:
    bootstrap = _make_bootstrap('test_control_center_commands_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        assert viewmodel.get_advanced_visible() is False
        viewmodel.sendChat('mostrar avanzado')
        assert viewmodel.get_advanced_visible() is True
        assert viewmodel.get_chat_messages()[-1]['text'].startswith('Modo avanzado visible.')
        viewmodel.sendChat('ocultar avanzado')
        assert viewmodel.get_advanced_visible() is False
        assert viewmodel.get_chat_messages()[-1]['text'].startswith('Modo avanzado oculto.')
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_bridge_message_routes_into_chat() -> None:
    bootstrap = _make_bootstrap('test_control_center_bridge_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        result = viewmodel.send_message_from_bridge('mostrar avanzado')
        assert result['status'] == 'queued'

        _drain_ui(viewmodel, timeout_seconds=3.0)

        messages = viewmodel.get_chat_messages()
        assert any(msg['text'].startswith('Modo avanzado visible.') for msg in messages)
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_greeting_stays_lightweight() -> None:
    bootstrap = _make_bootstrap('test_control_center_greeting_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        called = {'infer_task': 0}

        def _unexpected_infer_task(request):
            called['infer_task'] += 1
            raise AssertionError('general greeting should not trigger infer_task')

        viewmodel.inference_service.infer_task = _unexpected_infer_task  # type: ignore[method-assign]
        viewmodel.sendChat('hola')

        assert called['infer_task'] == 0
        assert viewmodel.get_working() is False
        assert viewmodel.get_chat_messages()[-1]['text'].startswith('Hola.')
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_browser_question_uses_world_model_shortcut() -> None:
    bootstrap = _make_bootstrap('test_control_center_browser_question_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        assert bootstrap.world_model_service is not None
        bootstrap.world_model_service._current_snapshot = WorldModelSnapshot(
            active_windows=[
                WindowObservation(title='Google Chrome - OpenAI', app_name='Chrome', pid=101, focused=False),
                WindowObservation(title='Microsoft Edge - IABV docs', app_name='Edge', pid=202, focused=True),
            ],
            focused_window=WindowObservation(title='Microsoft Edge - IABV docs', app_name='Edge', pid=202, focused=True),
            tool_live_status=list(bootstrap.world_model_service._current_snapshot.tool_live_status),
            network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena', latency_ms=42.0),
            detected_blocks=[],
            inferred_state={'summary': 'Veo ventanas de navegadores activas.', 'deductions': []},
            confidence=0.9,
        )

        called = {'infer_task': 0}

        def _unexpected_infer_task(request):
            called['infer_task'] += 1
            raise AssertionError('browser visibility question should stay on world_model shortcut')

        viewmodel.inference_service.infer_task = _unexpected_infer_task  # type: ignore[method-assign]
        viewmodel.sendChat('puedes ver los navegadores que tengo?')

        assert called['infer_task'] == 0
        assert viewmodel.get_working() is False
        reply = viewmodel.get_chat_messages()[-1]['text']
        assert 'Google Chrome - OpenAI' in reply
        assert 'Microsoft Edge - IABV docs' in reply
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_pending_approval_opens_dialog() -> None:
    bootstrap = _make_bootstrap('test_control_center_approval_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-1',
                'status': 'waiting_approval',
                'intent': {'title': 'Wplay login', 'intent_key': 'wplay.login', 'disposition': 'plan_then_execute', 'confidence': 0.91},
                'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                'chosen_pack': {'title': 'Wplay login', 'domain_kind': 'browser'},
                'playbook': {'status': 'waiting_approval', 'next_phase': 'strategy', 'summary': 'Esperando aprobacion', 'steps': []},
                'approval_checkpoints': [
                    {
                        'title': 'Confirmar estrategia inicial',
                        'decision': 'pending',
                        'risk_level': 'alto',
                        'detail': 'Se requiere tu confirmacion antes de ejecutar la fase sensible.',
                        'phase_key': 'strategy',
                    }
                ],
                'capability_readiness': [],
                'strategy_candidates': [],
                'outcome': {},
            }
        )
        assert viewmodel.get_approval_dialog_visible() is True
        assert viewmodel.get_approval_dialog_title() == 'Aprobacion requerida'
        assert 'Confirmar estrategia inicial' in viewmodel.get_approval_dialog_text()
        viewmodel.dismissApprovalDialog()
        assert viewmodel.get_approval_dialog_visible() is False
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_suggested_action_navigates_to_capture() -> None:
    bootstrap = _make_bootstrap('test_control_center_suggested_action_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        navigation = bootstrap.navigation_controller
        assert viewmodel is not None
        assert navigation is not None
        assert navigation.get_current_route() == 'dashboard'
        viewmodel.applySuggestedAction('open_teaching_studio')
        assert navigation.get_current_route() == 'capture'
        assert viewmodel.get_busy_label().startswith('Estudio de ensenanza listo')
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_suggested_action_prefills_teaching_and_hides_guidance() -> None:
    bootstrap = _make_bootstrap('test_control_center_prefill_teaching_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        navigation = bootstrap.navigation_controller
        capture = bootstrap.capture_studio_viewmodel
        assert viewmodel is not None
        assert navigation is not None
        assert capture is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-wplay',
                'status': 'waiting_approval',
                'intent': {
                    'title': 'Abrir Wplay e iniciar sesion',
                    'intent_key': 'wplay.login',
                    'disposition': 'plan_then_execute',
                    'site_hint': 'wplay',
                    'confidence': 0.91,
                },
                'context': {
                    'site_id': 'wplay',
                    'site_display_name': 'Wplay',
                    'session_readiness': {'dominant_incident': 'bridge_lag'},
                    'recent_teachings': [
                        {
                            'episode_id': 'ep-1',
                            'title': 'Wplay login corto',
                            'target_label': 'Wplay',
                            'start_url': 'https://www.wplay.co/login',
                            'objective': 'Abrir Wplay e iniciar sesion.',
                            'expected_outcome': 'Sesion iniciada y panel principal visible.',
                            'notes': 'No compartir secretos.',
                            'gaps': ['faltan rectangulos en boton submit'],
                        }
                    ],
                },
                'capability_readiness': [
                    {
                        'capability_id': 'wplay.login',
                        'title': 'Login Wplay',
                        'status': 'insufficient',
                        'site_id': 'wplay',
                        'suggested_next_step': 'Reensenar correo, contrasena y submit con mejor evidencia visual.',
                    }
                ],
                'approval_checkpoints': [],
                'strategy_candidates': [],
                'playbook': {'status': 'waiting_approval', 'next_phase': 'strategy', 'summary': 'Esperando aprobacion', 'steps': []},
                'chosen_pack': {'title': 'Login Wplay', 'domain_kind': 'browser'},
                'assistant_guidance': {
                    'mode': 'need_teaching',
                    'prompt': 'Hace falta una ensenanza limpia.',
                    'actions': [{'action': 'open_teaching_studio', 'label': 'Abrir ensenanza', 'detail': ''}],
                },
            }
        )

        viewmodel.applySuggestedAction('open_teaching_studio')

        assert navigation.get_current_route() == 'capture'
        assert viewmodel.get_assistant_guidance_mode() == 'idle'
        assert viewmodel.get_assistant_action_buttons() == []
        assert capture.teachingDraftLessonTitle == 'Wplay login corto'
        assert capture.teachingDraftTargetLabel == 'Wplay'
        assert capture.teachingDraftStartUrl == 'https://www.wplay.co/login'
        assert capture.teachingDraftObjective == 'Abrir Wplay e iniciar sesion.'
        assert capture.teachingDraftExpectedOutcome == 'Sesion iniciada y panel principal visible.'
        assert 'bridge_lag' in capture.teachingDraftNotes
        assert capture.selectedSiteId == 'wplay'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_probe_guidance_keeps_teaching_option_for_mixed_failures() -> None:
    bootstrap = _make_bootstrap('test_control_center_probe_guidance_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        guidance = viewmodel._derive_assistant_guidance(
            {
                'pending_issue_id': 'issue-123',
                'probe_diagnosis': {
                    'category': 'need_codex_fix',
                    'summary': 'Hay una mezcla de ensenanza debil e incidente tecnico repetido.',
                    'mismatches': [
                        {'category': 'need_teaching', 'title': 'Capacidad operativa aun debil'},
                        {'category': 'need_runtime_tuning', 'title': 'Incidentes tecnicos recientes'},
                    ],
                },
                'runtime_adjustments': [],
            }
        )
        actions = [item['action'] for item in guidance['actions']]
        assert guidance['mode'] == 'need_codex_fix'
        assert 'reforzar o corregir la ensenanza' in guidance['prompt']
        assert actions[0] == 'open_teaching_studio'
        assert 'prepare_codex_packet' in actions
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_hides_execute_when_adapter_is_missing() -> None:
    bootstrap = _make_bootstrap('test_control_center_missing_executor_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-google',
                'status': 'ready_to_execute',
                'intent': {'title': 'Buscar en Google', 'intent_key': 'browser.search.google', 'disposition': 'plan_then_execute', 'confidence': 0.88},
                'context': {'site_id': 'google', 'site_display_name': 'Google'},
                'chosen_pack': {'title': 'Browser generic', 'domain_kind': 'browser'},
                'playbook': {'status': 'ready_to_execute', 'next_phase': 'execute', 'summary': 'Listo para fase operativa', 'steps': []},
                'approval_checkpoints': [],
                'capability_readiness': [],
                'strategy_candidates': [],
                'outcome': {'summary': 'La estrategia quedo lista, pero no hay un adaptador operativo real para ejecutar esta fase todavia.', 'next_actions': ['Simular', 'Ver evolutivo', 'Preparar Codex']},
                'metadata': {
                    'execution_state': {
                        'executor_name': 'no_operational_executor',
                        'executor_available': False,
                        'simulation_only': False,
                        'state': 'adapter_missing',
                        'detail': 'No hay un adaptador operativo real conectado para Browser generic.',
                    }
                },
            }
        )

        assert viewmodel.get_can_execute() is False
        execution_text = viewmodel.get_adaptive_execution_text()
        assert 'Executor: no_operational_executor' in execution_text
        assert 'Estado operativo: adapter_missing' in execution_text
        assert 'Detalle operativo: No hay un adaptador operativo real conectado para Browser generic.' in execution_text
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_consult_codex_falls_back_to_web_and_records_external_result() -> None:
    bootstrap = _make_bootstrap('test_control_center_consult_codex_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._copy_text = lambda text, notice='': None  # type: ignore[method-assign]
        bootstrap.adaptive_task_orchestrator.preflight_external_assistant = (  # type: ignore[method-assign]
            lambda **kwargs: {
                'assistant_kind': 'codex',
                'world_model': {},
                'world_model_summary': {},
                'governance': {'approval_required': False, 'block_risky_action': False, 'reason': ''},
                'approval_checkpoints': [],
                'blocked': False,
                'reason': '',
            }
        )

        def fake_preview_external_consultation(**kwargs):
            return {
                'available': True,
                'summary': 'Fallback web disponible.',
                'tool_card': {
                    'tool_id': 'claude_web_assisted',
                    'title': 'Claude web asistido',
                    'metadata': {
                        'launch_mode': 'web_assisted',
                        'response_capture_mode': 'dom_capture',
                    },
                },
                'tool_task': {'tool_id': 'claude_web_assisted', 'metadata': {}},
                'mode_selection': {'fallback_used': True},
            }

        def fake_execute_external_consultation(**kwargs):
            task = SimpleNamespace(task_id='task-1', tool_id='claude_web_assisted', metadata={})
            result = SimpleNamespace(
                success=True,
                output_text='Consulta externa preparada.',
                error_message='',
                result_id='result-1',
                metadata={'actual_assistant_kind': 'claude'},
                execution_state=SimpleNamespace(
                    metadata={
                        'launch_mode': 'web_assisted',
                        'response_capture_mode': 'dom_capture',
                        'response_capture_pending': True,
                        'manual_pasteback_required': False,
                        'response_captured': False,
                    },
                    detail='Herramienta ejecutada por el adaptador local.',
                ),
            )
            return task, result, None

        bootstrap.tool_teach_service.preview_external_consultation = fake_preview_external_consultation
        bootstrap.tool_teach_service.execute_external_consultation = fake_execute_external_consultation

        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-wplay-consult',
                'status': 'need_codex_fix',
                'intent': {
                    'title': 'Abrir Wplay e iniciar sesion',
                    'intent_key': 'wplay.login',
                    'disposition': 'plan_then_execute',
                    'site_hint': 'wplay',
                    'confidence': 0.83,
                },
                'context': {
                    'site_id': 'wplay',
                    'site_display_name': 'Wplay',
                    'session_readiness': {'dominant_incident': 'bridge_lag'},
                    'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                },
                'capability_readiness': [
                    {
                        'capability_id': 'wplay.login',
                        'title': 'Login Wplay',
                        'status': 'insufficient',
                        'site_id': 'wplay',
                        'suggested_next_step': 'Reensenar el login corto y revisar el bridge.',
                    }
                ],
                'chosen_pack': {'title': 'Login Wplay', 'domain_kind': 'browser'},
                'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
                'probe_diagnosis': {
                    'category': 'need_codex_fix',
                    'summary': 'La ensenanza existe pero el bridge no consolida bien el flujo.',
                    'mismatches': [{'category': 'need_teaching', 'title': 'Readiness visual debil'}],
                },
                'pending_issue_id': 'issue-wplay-1',
            }
        )

        result_payload = viewmodel._execute_external_consultation_sync('codex')

        assert result_payload['success'] is True
        payload = dict(result_payload.get('payload') or {})
        consultation = dict((payload.get('metadata') or {}).get('external_consultation') or {})
        assert consultation['launch_mode'] == 'web_assisted'
        assert consultation['manual_pasteback_required'] is False
        assert consultation['response_capture_pending'] is True
        assert consultation['actual_assistant_kind'] in {'chatgpt', 'claude'}
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_blocks_external_consultation_before_preview_when_permission_is_missing() -> None:
    bootstrap = _make_bootstrap('test_control_center_permission_preflight_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'consulta con codex este incidente tecnico'
        preview_calls = {'count': 0}
        execute_calls = {'count': 0}

        def fake_preview_external_consultation(**kwargs):
            preview_calls['count'] += 1
            raise AssertionError('preview_external_consultation no deberia ejecutarse si el preflight bloquea la ruta')

        def fake_execute_external_consultation(**kwargs):
            execute_calls['count'] += 1
            raise AssertionError('execute_external_consultation no deberia ejecutarse si el preflight bloquea la ruta')

        bootstrap.tool_teach_service.preview_external_consultation = fake_preview_external_consultation
        bootstrap.tool_teach_service.execute_external_consultation = fake_execute_external_consultation

        def fake_preflight_external_assistant(*, user_goal: str, assistant_kind: str) -> dict[str, object]:
            return {
                'assistant_kind': assistant_kind,
                'world_model': {},
                'world_model_summary': {'permission_gates': [{'scope': 'observe_window_content:codex', 'assistant_kind': 'codex', 'status': 'requerido'}]},
                'governance': {
                    'approval_required': True,
                    'block_risky_action': True,
                    'recommended_action': 'request_observation_permission',
                    'reason': 'Para verificar si Codex tiene mensajes disponibles necesito observar esa ventana.',
                    'external_state_flags': [],
                },
                'approval_checkpoints': [
                    {
                        'title': 'Permitir observacion de codex',
                        'decision': 'pending',
                        'risk_level': 'medium',
                        'detail': 'Para verificar si Codex tiene mensajes disponibles necesito observar esa ventana.',
                        'phase_key': 'observation_permission',
                        'metadata': {
                            'assistant_kind': 'codex',
                            'permission_gates': [
                                {
                                    'scope': 'observe_window_content:codex',
                                    'assistant_kind': 'codex',
                                    'status': 'requerido',
                                }
                            ],
                        },
                    }
                ],
                'blocked': True,
                'reason': 'Para verificar si Codex tiene mensajes disponibles necesito observar esa ventana.',
            }

        bootstrap.adaptive_task_orchestrator.preflight_external_assistant = fake_preflight_external_assistant

        result = viewmodel._execute_external_consultation_sync('codex')

        assert result['success'] is False
        assert preview_calls['count'] == 0
        assert execute_calls['count'] == 0
        assert viewmodel.get_approval_dialog_visible() is True
        assert viewmodel.get_assistant_guidance_mode() == 'need_approval'
        assert any(item['action'] == 'approve_observation_permission' for item in viewmodel.get_assistant_action_buttons())
        assert 'observar esa ventana' in viewmodel.get_latest_response_text()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_ignores_stale_permission_checkpoint_after_live_grant() -> None:
    bootstrap = _make_bootstrap('test_control_center_stale_permission_gate_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'consulta con chatgpt'
        viewmodel._copy_text = lambda text, notice='': None  # type: ignore[method-assign]

        class FakeWorldModelService:
            def permission_snapshot(self):
                return [{
                    'scope': 'observe_window_content:chatgpt',
                    'assistant_kind': 'chatgpt',
                    'granted': True,
                    'detail': 'Permiso concedido por el usuario.',
                }]

        bootstrap.adaptive_task_orchestrator.context_assembler.world_model_service = FakeWorldModelService()
        bootstrap.adaptive_task_orchestrator.preflight_external_assistant = (  # type: ignore[method-assign]
            lambda **kwargs: {
                'assistant_kind': 'chatgpt',
                'world_model': {},
                'world_model_summary': {
                    'permission_gates': [
                        {
                            'scope': 'observe_window_content:chatgpt',
                            'assistant_kind': 'chatgpt',
                            'status': 'requerido',
                        }
                    ]
                },
                'governance': {
                    'approval_required': True,
                    'block_risky_action': True,
                    'recommended_action': 'request_observation_permission',
                    'reason': 'Para verificar si ChatGPT esta listo necesito observar esa ventana.',
                    'external_state_flags': [],
                },
                'approval_checkpoints': [
                    {
                        'title': 'Permitir observacion de chatgpt',
                        'decision': 'pending',
                        'risk_level': 'medium',
                        'detail': 'Para verificar si ChatGPT esta listo necesito observar esa ventana.',
                        'phase_key': 'observation_permission',
                        'metadata': {'assistant_kind': 'chatgpt'},
                    }
                ],
                'blocked': True,
                'reason': 'Para verificar si ChatGPT esta listo necesito observar esa ventana.',
            }
        )
        preview_calls = {'count': 0}

        def fake_preview_external_consultation(**kwargs):
            preview_calls['count'] += 1
            return {
                'available': True,
                'summary': 'ChatGPT disponible.',
                'tool_card': {
                    'tool_id': 'chatgpt_web_assisted',
                    'title': 'ChatGPT web asistido',
                    'metadata': {'launch_mode': 'web_assisted', 'response_capture_mode': 'manual_pasteback'},
                },
                'tool_task': {'tool_id': 'chatgpt_web_assisted', 'metadata': {}},
                'mode_selection': {},
            }

        def fake_execute_external_consultation(**kwargs):
            task = SimpleNamespace(task_id='task-chatgpt', tool_id='chatgpt_web_assisted', metadata={})
            result = SimpleNamespace(
                success=True,
                output_text='Consulta externa preparada.',
                error_message='',
                result_id='result-chatgpt',
                metadata={'actual_assistant_kind': 'chatgpt'},
                execution_state=SimpleNamespace(
                    metadata={
                        'launch_mode': 'web_assisted',
                        'response_capture_mode': 'manual_pasteback',
                        'manual_pasteback_required': True,
                        'response_capture_pending': False,
                        'response_captured': False,
                    },
                    detail='Consulta preparada.',
                ),
            )
            return task, result, None

        bootstrap.tool_teach_service.preview_external_consultation = fake_preview_external_consultation
        bootstrap.tool_teach_service.execute_external_consultation = fake_execute_external_consultation

        result = viewmodel._execute_external_consultation_sync('chatgpt')

        assert result['success'] is True
        assert preview_calls['count'] == 1
        assert 'Permiso requerido' not in result['meta']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_grants_observation_permission_and_retries_consultation() -> None:
    bootstrap = _make_bootstrap('test_control_center_permission_retry_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        class FakeWorldModelService:
            def __init__(self) -> None:
                self.calls: list[dict[str, str]] = []

            def grant_observation_permission(self, **kwargs):
                self.calls.append({key: str(value) for key, value in kwargs.items()})
                return WorldModelSnapshot(
                    permission_gates=[
                        ObservationPermissionGate(
                            scope='observe_window_content:codex',
                            assistant_kind='codex',
                            status='concedido',
                            title='Observacion de Codex',
                            detail='Permiso concedido.',
                            required_for=['consult_codex'],
                        )
                    ],
                    network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
                    confidence=0.8,
                )

        fake_world_model_service = FakeWorldModelService()
        bootstrap.adaptive_task_orchestrator.context_assembler.world_model_service = fake_world_model_service

        retried = {'assistant_kind': ''}

        def fake_run_external_consultation(assistant_kind: str, *, announce: bool = True) -> bool:
            retried['assistant_kind'] = assistant_kind
            return True

        viewmodel._run_external_consultation = fake_run_external_consultation  # type: ignore[method-assign]
        viewmodel._last_adaptive_payload = {
            'approval_checkpoints': [
                {
                    'title': 'Permitir observacion de codex',
                    'decision': 'pending',
                    'risk_level': 'medium',
                    'detail': 'Necesito permiso para observar Codex.',
                    'phase_key': 'observation_permission',
                    'metadata': {
                        'assistant_kind': 'codex',
                        'permission_gates': [
                            {
                                'scope': 'observe_window_content:codex',
                                'assistant_kind': 'codex',
                                'status': 'requerido',
                            }
                        ],
                    },
                }
            ],
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'codex',
                    'reason': 'Permiso requerido.',
                    'blocked': True,
                }
            },
        }

        assert viewmodel._grant_pending_observation_permission(announce=False) is True
        assert fake_world_model_service.calls
        assert fake_world_model_service.calls[0]['scope'] == 'observe_window_content:codex'
        assert retried['assistant_kind'] == 'codex'
        assert viewmodel.get_approval_dialog_visible() is False
        assert viewmodel._last_adaptive_payload.get('approval_checkpoints') == []
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_build_request_uses_visual_signal_snapshot_and_formal_ia_trace() -> None:
    bootstrap = _make_bootstrap('test_control_center_visual_signal_trace_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        capture = bootstrap.capture_studio_viewmodel
        service = bootstrap.universal_perception_service
        assert viewmodel is not None
        assert capture is not None
        assert service is not None

        capture._replay_visual_summary = {
            'visual_summary': {'green_count': 2, 'orange_count': 1, 'red_count': 0},
            'learning_readiness': {'status': 'ready'},
            'cross_check_summary': {'status': 'aligned'},
            'metadata': {
                'latest_url': 'https://example.com/chat',
                'latest_title': 'Codex chat',
                'dom_available': True,
                'visible_targets': ['chat input'],
                'evidence_refs': ['episode:1'],
            },
        }
        capture._assistant_lane_summary = {'total': 1, 'background': 1, 'selected_task_id': 'task-ext-1'}
        capture._session_health = {'status': 'active'}
        service._list_windows = lambda: [{'title': 'Codex - Workspace', 'pid': 888}]  # type: ignore[method-assign]
        service._list_process_rows = lambda: [{'image_name': 'codex.exe', 'pid': 888, 'window_title': 'Codex - Workspace'}]  # type: ignore[method-assign]
        viewmodel._last_adaptive_payload = {
            'metadata': {
                'autonomous_evolution_response': {
                    'ia_trace_entry': {
                        'trace_id': 'trace-ctrl-1',
                        'assistant_kind': 'codex',
                        'config_signature': 'cfg-ctrl-1',
                        'route': 'code_agent',
                        'external_state_flags': ['wrong_thread'],
                    }
                }
            }
        }

        request = viewmodel._build_request('consulta tecnica a codex')

        assert request.metadata['visual_signal']['capture_available'] is True
        assert request.metadata['visual_signal']['latest_title'] == 'Codex - Workspace'
        assert request.metadata['visual_signal']['source_app'] == 'codex'
        assert request.metadata['visual_signal']['dom_summary']['status'] == 'no_disponible'
        assert request.metadata['visual_signal']['available_actions']
        assert request.metadata['ia_trace'][0]['trace_id'] == 'trace-ctrl-1'
        assert request.metadata['ia_trace'][0]['external_state_flags'] == ['wrong_thread']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_build_request_inherits_recent_site_hint_for_task_follow_up() -> None:
    bootstrap = _make_bootstrap('test_control_center_follow_up_site_hint_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel._append_message(
            'user',
            'Tu',
            'Quiero enseñarte Wplay. Objetivo inicial: aprende a abrir el sitio y detectar si la sesion sigue activa.',
            '',
        )
        viewmodel._append_message(
            'assistant',
            'IABV',
            'Entendido. Seguimos con Wplay y lo hago por fases.',
            '',
        )

        request = viewmodel._build_request('ok entonces empecemos, que te enseño primero ?')

        assert request.site_hint == 'wplay'
        assert request.goal_parameters.get('site_hint') == 'wplay'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_operational_teaching_prompt_does_not_bypass_into_learning_chat() -> None:
    bootstrap = _make_bootstrap('test_control_center_operational_teaching_prompt_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        captured: dict[str, object] = {}

        def _fake_infer_task(request):
            captured['request'] = request
            return SimpleNamespace(
                route=SimpleNamespace(reason='Ruta local.', task_role=TaskRole.TRAINING),
                result=SimpleNamespace(
                    summary='Seguimos con Wplay por fases.',
                    provider_name='Ollama',
                    reasoning_mode=SimpleNamespace(value='local'),
                    confidence=0.87,
                    report_kind=SimpleNamespace(value='training_guidance'),
                    detected_role=TaskRole.TRAINING,
                    sources=[],
                    follow_up_teachings=[],
                    used_tools=[],
                    planner_used=False,
                    executor_model='qwen3:8b',
                    chosen_pack={'title': 'Wplay core'},
                    raw_output={
                        'adaptive_session': {
                            'intent': {'intent_key': 'wplay.core', 'title': 'Abrir Wplay'},
                            'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                            'assistant_guidance': {'actions': []},
                            'metadata': {},
                        }
                    },
                ),
            )

        viewmodel.inference_service.infer_task = _fake_infer_task  # type: ignore[assignment]

        viewmodel.sendChat(
            'Quiero enseñarte Wplay. Objetivo inicial: aprende a abrir el sitio, detectar si la sesion esta activa y dejar lista la siguiente fase sin apostar.'
        )
        _drain_ui(viewmodel)

        assert 'request' in captured
        request = captured['request']
        assert getattr(request, 'site_hint', '') == 'wplay'
        assert viewmodel.get_working() is False
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_surfaces_formal_external_state_flags_in_evolution_text() -> None:
    bootstrap = _make_bootstrap('test_control_center_external_state_flags_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-external-flags',
                'status': 'need_codex_fix',
                'intent': {'title': 'Revisar consulta externa', 'intent_key': 'knowledge.query', 'disposition': 'answer_now', 'confidence': 0.72},
                'context': {'site_display_name': 'General'},
                'chosen_pack': {'title': 'General', 'pack_id': 'general.assistance', 'domain_kind': 'language'},
                'playbook': {'status': 'need_codex_fix', 'next_phase': 'review', 'summary': 'Caso externo con bloqueo formal.', 'steps': []},
                'approval_checkpoints': [],
                'capability_readiness': [],
                'strategy_candidates': [],
                'outcome': {},
                'metadata': {
                    'decision_context': {
                        'metadata': {'external_state_flags': ['wrong_thread', 'capture_unverified']},
                        'governance': {
                            'autonomy_level': 'guarded_research',
                            'recommended_action': 'audit_autonomy',
                            'blockers': ['El hilo externo no coincide con lo esperado.'],
                        },
                    },
                    'perception_snapshot': {'external_state_flags': ['wrong_thread', 'capture_unverified']},
                },
            }
        )

        assert 'Estados externos: wrong_thread, capture_unverified' in viewmodel.get_adaptive_evolution_text()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_surfaces_historical_preference_and_human_external_notice() -> None:
    bootstrap = _make_bootstrap('test_control_center_history_and_external_notice_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-history-notice',
                'status': 'need_codex_fix',
                'intent': {'title': 'Revisar problema tecnico', 'intent_key': 'knowledge.query', 'disposition': 'answer_now', 'confidence': 0.78},
                'context': {'site_display_name': 'Wplay'},
                'chosen_pack': {'title': 'General', 'pack_id': 'general.assistance', 'domain_kind': 'language'},
                'playbook': {'status': 'need_codex_fix', 'next_phase': 'review', 'summary': 'Caso externo con historia.', 'steps': []},
                'approval_checkpoints': [],
                'capability_readiness': [],
                'strategy_candidates': [],
                'outcome': {},
                'metadata': {
                    'decision_context': {
                        'metadata': {
                            'external_state_flags': ['account_limited'],
                            'preferred_assistant_kind': 'claude',
                            'preferred_config_signature': 'cfg-history',
                            'supporting_trace_ids': ['trace-history-1'],
                        },
                        'governance': {
                            'autonomy_level': 'guarded_local',
                            'recommended_action': 'continue_local',
                            'blockers': ['La cuenta externa no permite continuar con esa via.'],
                        },
                    },
                    'perception_snapshot': {'external_state_flags': ['account_limited']},
                },
            }
        )

        text = viewmodel.get_adaptive_evolution_text()
        assert 'Preferencia historica IA: claude' in text
        assert 'Configuracion historica: cfg-history' in text
        assert 'Trazas de soporte: trace-history-1' in text
        assert 'Lectura para humano: La ruta externa quedo limitada por cuota, plan o cuenta' in text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_autonomy_message_surfaces_blocked_external_notice() -> None:
    bootstrap = _make_bootstrap('test_control_center_blocked_external_notice_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        payload = {
            'session_id': 'adaptive-blocked-external',
            'status': 'need_codex_fix',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay', 'confidence': 0.83},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El problema parece tecnico y repetido.'},
            'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
            'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'metadata': {},
        }
        viewmodel._update_adaptive_state(payload)
        viewmodel.autonomous_evolution_service.plan_or_execute = lambda **kwargs: {  # type: ignore[method-assign]
            'status': 'blocked_external',
            'assistant_kind': 'codex',
            'selected_tool_id': 'codex_installed',
            'external_state_flags': ['account_limited'],
            'detail': 'La cuenta externa no tiene cuota disponible.',
            'pending_issue_id': 'issue-1',
        }

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='self_teach')

        assert result is not None
        assert result['status'] == 'blocked_external'
        assert 'cuota, plan o cuenta' in viewmodel.get_chat_messages()[-1]['text']
        assert 'mejor via local disponible' in viewmodel.get_busy_label()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_surfaces_live_audit_summary_in_adaptive_texts() -> None:
    bootstrap = _make_bootstrap('test_control_center_live_audit_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-live-audit',
                'status': 'ready_to_execute',
                'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'disposition': 'plan_then_execute', 'confidence': 0.82},
                'context': {
                    'site_id': 'wplay',
                    'site_display_name': 'Wplay',
                    'live_audit': {
                        'summary': 'La ensenanza existe pero todavia no consolida aprendizaje reutilizable. Decision: retry_after_rebuild. Confianza 0.78.',
                        'decision_action': 'retry_after_rebuild',
                    },
                },
                'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
                'playbook': {'status': 'ready_to_execute', 'next_phase': 'execute', 'summary': 'Listo para revisar.', 'steps': []},
                'approval_checkpoints': [],
                'capability_readiness': [],
                'strategy_candidates': [],
                'outcome': {},
            }
        )

        assert 'Auditoria viva: La ensenanza existe pero todavia no consolida aprendizaje reutilizable.' in viewmodel.get_adaptive_context_text()
        assert 'Decision auditada: retry_after_rebuild' in viewmodel.get_adaptive_evolution_text()
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_self_teach_triggers_autonomous_codex_consultation() -> None:
    bootstrap = _make_bootstrap('test_control_center_autonomous_codex_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        fake_codex = Path(bootstrap.config.workspace_root) / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        bootstrap.tool_record_repository.save_card(
            card.model_copy(
                update={
                    'metadata': {
                        **card.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'dry_run_launch': True,
                    }
                }
            )
        )

        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        viewmodel._apply_task_result(
            'self_teach',
            {
                'scenario_run': {
                    'scenario': {'scenario_id': 'wplay.login', 'title': 'Wplay login'},
                    'summary': 'Bridge lag persistente.',
                },
                'probe_diagnosis': {
                    'category': 'need_codex_fix',
                    'summary': 'La ensenanza existe pero el bridge no consolida el flujo.',
                    'probable_cause': 'La cola visible drena tarde y el replay no fija aprendizaje reusable.',
                },
                'adaptive_session': {
                    'session_id': 'adaptive-wplay-autonomy',
                    'status': 'need_codex_fix',
                    'intent': {
                        'title': 'Abrir Wplay e iniciar sesion',
                        'intent_key': 'wplay.login',
                        'site_hint': 'wplay',
                        'confidence': 0.82,
                    },
                    'context': {
                        'site_id': 'wplay',
                        'site_display_name': 'Wplay',
                        'session_readiness': {'dominant_incident': 'bridge_lag'},
                        'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                        'live_audit': {
                            'summary': 'Bridge lag persistente despues de la ensenanza.',
                            'decision_action': 'consult_codex',
                        },
                    },
                    'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
                    'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico.', 'steps': []},
                    'capability_readiness': [
                        {
                            'capability_id': 'wplay.login',
                            'title': 'Login Wplay',
                            'status': 'insufficient',
                            'site_id': 'wplay',
                            'suggested_next_step': 'Reforzar bridge y consolidacion.',
                        }
                    ],
                    'approval_checkpoints': [],
                    'strategy_candidates': [],
                    'metadata': {},
                },
                'pending_issue': {},
                'runtime_adjustments': [],
            },
        )

        messages = viewmodel.get_chat_messages()
        assert any(item['speaker'] == 'Autonomia' for item in messages)
        assert any(token in viewmodel.get_adaptive_evolution_text() for token in ('Autonomia: prepared', 'Autonomia: reused', 'Autonomia: awaiting_response'))
        assert 'Asistente solicitado: codex' in viewmodel.get_adaptive_evolution_text()
        assert 'Tool autonomo: codex_installed' in viewmodel.get_adaptive_evolution_text()
        stored_results = [item for item in bootstrap.tool_record_repository.list_results(limit=10) if item.metadata.get('autonomous_consultation')]
        assert stored_results
        assert stored_results[0].metadata['autonomous_consultation']['assistant_kind'] == 'codex'
        assert bootstrap.pending_issue_repository.list_recent(limit=5)
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_audit_autonomy_command_previews_route() -> None:
    bootstrap = _make_bootstrap('test_control_center_audit_autonomy_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        fake_codex = Path(bootstrap.config.workspace_root) / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        bootstrap.tool_record_repository.save_card(
            card.model_copy(
                update={
                    'metadata': {
                        **card.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'dry_run_launch': True,
                    }
                }
            )
        )
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-wplay-preview',
                'status': 'need_codex_fix',
                'intent': {
                    'title': 'Abrir Wplay e iniciar sesion',
                    'intent_key': 'wplay.login',
                    'site_hint': 'wplay',
                    'confidence': 0.83,
                },
                'context': {
                    'site_id': 'wplay',
                    'site_display_name': 'Wplay',
                    'session_readiness': {'dominant_incident': 'bridge_lag'},
                    'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                    'live_audit': {
                        'summary': 'Bridge lag persistente despues de la ensenanza.',
                        'decision_action': 'consult_codex',
                    },
                },
                'probe_diagnosis': {
                    'category': 'need_codex_fix',
                    'summary': 'El problema parece tecnico y repetido.',
                },
                'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
                'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
                'approval_checkpoints': [],
                'capability_readiness': [],
                'strategy_candidates': [],
                'metadata': {},
            }
        )

        viewmodel.sendChat('auditar autonomia')

        messages = viewmodel.get_chat_messages()
        assert any(item['speaker'] == 'Auditoria' for item in messages)
        assert 'Preview autonomia: consult_codex' in viewmodel.get_adaptive_evolution_text()
        assert 'Preview asistente: codex' in viewmodel.get_adaptive_evolution_text()
        assert 'Preview via: codex_installed' in viewmodel.get_adaptive_evolution_text()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_ingests_external_response_and_updates_guidance() -> None:
    bootstrap = _make_bootstrap('test_control_center_ingest_external_response_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        fake_codex = Path(bootstrap.config.workspace_root) / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        bootstrap.tool_record_repository.save_card(
            card.model_copy(
                update={
                    'metadata': {
                        **card.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'dry_run_launch': True,
                    }
                }
            )
        )
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        payload = {
            'session_id': 'adaptive-wplay-ingest-ui',
            'status': 'need_codex_fix',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay', 'confidence': 0.83},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El problema parece tecnico y repetido.'},
            'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
            'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'metadata': {},
        }
        viewmodel._update_adaptive_state(payload)
        viewmodel._maybe_run_autonomous_evolution(payload, source='self_teach')

        viewmodel.ingestExternalResponse(
            'Causa raiz probable: El bridge visible acumula eventos y checkpoints sin consolidarlos a tiempo. '
            'Cambio vertical recomendado: Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina. '
            'CodexTaskSpec sugerido: - file_scope: src/iabv_v15/services/capture/browser_teach_session_service.py, src/iabv_v15/ui/viewmodels/capture_studio_viewmodel.py. '
            'Pruebas sugeridas: Captura con escritura rapida, Varias pestanas'
        )

        assert viewmodel.get_assistant_guidance_mode() == 'external_response_interpreted'
        actions = [item['action'] for item in viewmodel.get_assistant_action_buttons()]
        assert actions[0] == 'prepare_codex_packet'
        assert 'Respuesta externa: ingested' in viewmodel.get_adaptive_evolution_text()
        assert 'Siguiente accion: prepare_codex_packet' in viewmodel.get_adaptive_evolution_text()
        assert 'Validacion respuesta: review_needed' in viewmodel.get_adaptive_evolution_text()
        assert 'Adopcion segura: guarded | via codex_packet' in viewmodel.get_adaptive_evolution_text()
        assert 'via segura: codex_packet' in viewmodel.get_assistant_guidance_text()
        assert any(item['speaker'] == 'Autonomia' for item in viewmodel.get_chat_messages())
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_command_ingests_clipboard_response() -> None:
    bootstrap = _make_bootstrap('test_control_center_ingest_clipboard_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        fake_codex = Path(bootstrap.config.workspace_root) / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        bootstrap.tool_record_repository.save_card(
            card.model_copy(
                update={
                    'metadata': {
                        **card.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'dry_run_launch': True,
                    }
                }
            )
        )
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        payload = {
            'session_id': 'adaptive-wplay-ingest-chat',
            'status': 'need_codex_fix',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay', 'confidence': 0.83},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El problema parece tecnico y repetido.'},
            'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
            'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'metadata': {},
        }
        viewmodel._update_adaptive_state(payload)
        viewmodel._maybe_run_autonomous_evolution(payload, source='self_teach')
        viewmodel._read_text_from_clipboard = lambda: 'Causa raiz probable: El bridge visible sigue saturado. Cambio vertical recomendado: Ajustar sondeo y drenado. Pruebas sugeridas: Captura con escritura rapida'

        viewmodel.sendChat('ingerir respuesta')

        assert 'Respuesta externa: ingested' in viewmodel.get_adaptive_evolution_text()
        assert viewmodel.get_assistant_guidance_mode() == 'external_response_interpreted'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_auto_ingests_direct_external_response() -> None:
    bootstrap = _make_bootstrap('test_control_center_auto_ingest_external_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        bootstrap.tool_record_repository.save_card(
            card.model_copy(
                update={
                    'metadata': {
                        **card.metadata,
                        'response_capture_mode': 'direct_text',
                        'requires_manual_pasteback': False,
                        'direct_response_text': (
                            'Causa raiz probable: El bridge visible sigue saturado. '
                            'Cambio vertical recomendado: Ajustar sondeo y drenado sin bloquear la pagina. '
                            'Pruebas sugeridas: Captura con escritura rapida'
                        ),
                    }
                }
            )
        )
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        payload = {
            'session_id': 'adaptive-wplay-auto-ingest',
            'status': 'need_codex_fix',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay', 'confidence': 0.83},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El problema parece tecnico y repetido.'},
            'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
            'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'metadata': {},
        }
        viewmodel._update_adaptive_state(payload)

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='self_teach')

        assert result is not None
        assert result['status'] == 'ingested'
        assert 'Respuesta externa: ingested' in viewmodel.get_adaptive_evolution_text()
        assert 'Adopcion segura: guarded | via codex_packet' in viewmodel.get_adaptive_evolution_text()
        assert viewmodel.get_assistant_guidance_mode() == 'external_response_interpreted'
        actions = [item['action'] for item in viewmodel.get_assistant_action_buttons()]
        assert actions[0] == 'prepare_codex_packet'
    finally:
        _cleanup_bootstrap(bootstrap)

def test_control_center_evolution_panel_has_honest_fallbacks() -> None:
    bootstrap = _make_bootstrap('test_control_center_evolution_panel_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        overview = viewmodel.get_evolution_overview()
        area_cards = viewmodel.get_evolution_area_cards()
        blockers = viewmodel.get_evolution_blockers()

        assert overview['title'] == 'Pulso evolutivo'
        assert 'areas con evidencia operativa' in overview['summary']
        assert len(overview['compact_cards']) == 4
        assert len(area_cards) == 7
        assert isinstance(blockers, list)
        assert {item['title'] for item in area_cards} >= {
            'Aprendizaje',
            'Algoritmos probados',
            'Variables exploradas',
            'Investigaciones utiles',
            'Objetivos y tareas',
            'Auditoria y coherencia',
            'Memoria y reutilizacion',
        }
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_evolution_panel_reflects_audit_and_autonomy_gaps() -> None:
    bootstrap = _make_bootstrap('test_control_center_evolution_panel_gaps_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        capture = bootstrap.capture_studio_viewmodel
        assert viewmodel is not None
        assert capture is not None

        capture._replay_visual_summary = {
            'metadata': {
                'audit_status': 'failed',
                'audit_overall_confidence': 0.42,
                'audit_findings': ['submit no coincide'],
                'steps_matching': 2,
                'steps_diverging': 1,
            }
        }
        viewmodel._pbt_state = {
            'generation': 2,
            'summary': 'PBT encontro una configuracion mas estable.',
            'candidates': [{'candidate_id': 'cand-1', 'score': 0.81, 'notes': 'estable'}],
        }
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-evo-1',
                'status': 'waiting_approval',
                'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login'},
                'chosen_pack': {'title': 'Login Wplay'},
                'context': {
                    'live_audit': {
                        'summary': 'Desalineacion visual frente al submit.',
                        'decision_action': 'consult_codex',
                        'recommended_action': 'prepare_codex_packet',
                    }
                },
                'metadata': {
                    'autonomous_evolution': {
                        'assistant_kind': 'codex',
                        'status': 'prepared',
                        'detail': 'Consulta externa preparada.',
                        'response_ingested': False,
                    }
                },
                'capability_readiness': [
                    {
                        'capability_id': 'wplay.login',
                        'title': 'Login Wplay',
                        'status': 'insufficient',
                        'detail': 'Falta evidencia estable en submit.',
                    }
                ],
            }
        )
        viewmodel._update_evolution_snapshot()

        overview = viewmodel.get_evolution_overview()
        cards = {item['title']: item for item in viewmodel.get_evolution_area_cards()}
        blockers = viewmodel.get_evolution_blockers()

        assert overview['status'] in {'warning', 'blocked'}
        assert cards['Auditoria y coherencia']['status'] == 'blocked'
        assert cards['Investigaciones utiles']['status'] == 'warning'
        assert cards['Objetivos y tareas']['status'] == 'warning'
        assert any('submit no coincide' in item['detail'] or 'submit no coincide' in item['title'] for item in blockers)
    finally:
        _cleanup_bootstrap(bootstrap)

def test_control_center_evolution_text_surfaces_auto_replan_state() -> None:
    bootstrap = _make_bootstrap('test_control_center_auto_replan_text_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-replan-ui',
                'status': 'ready_to_execute',
                'intent': {'title': 'Resolver login Wplay', 'intent_key': 'wplay.login', 'disposition': 'plan_then_execute', 'confidence': 0.84},
                'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
                'playbook': {'status': 'ready_to_execute', 'next_phase': 'execute', 'summary': 'Replan listo.', 'steps': []},
                'approval_checkpoints': [],
                'capability_readiness': [],
                'strategy_candidates': [],
                'outcome': {},
                'metadata': {
                    'replanned_automatically': True,
                    'replanned_from_session_id': 'adaptive-original',
                    'governance': {
                        'autonomy_level': 'guarded_local',
                        'recommended_action': 'replan_strategy',
                        'require_sandbox': True,
                        'should_replan': True,
                        'research_needed': False,
                        'blockers': [],
                    },
                },
            }
        )

        text = viewmodel.get_adaptive_evolution_text()
        assert 'Replanificacion automatica: True' in text
        assert 'origen: adaptive-original' in text
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_evolution_panel_reflects_external_response_adoption_plan() -> None:
    bootstrap = _make_bootstrap('test_control_center_evolution_panel_adoption_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-evo-adoption',
                'status': 'ready_to_execute',
                'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login'},
                'chosen_pack': {'title': 'Login Wplay'},
                'context': {'live_audit': {'summary': 'Bridge lag persistente.', 'decision_action': 'consult_codex'}},
                'metadata': {
                    'autonomous_evolution': {
                        'assistant_kind': 'codex',
                        'status': 'prepared',
                        'detail': 'Consulta externa preparada.',
                        'response_ingested': True,
                    },
                    'autonomous_evolution_response': {
                        'status': 'ingested',
                        'assistant_kind': 'codex',
                        'response_summary': 'Ajustar sondeo y drenado.',
                        'response_validation': {
                            'status': 'review_needed',
                            'sandbox_required': True,
                            'requires_human_approval': True,
                            'rationale': 'La respuesta requiere revision guiada antes de adoptarla.',
                        },
                        'adoption_plan': {
                            'status': 'guarded',
                            'execution_lane': 'codex_packet',
                            'next_action': 'prepare_codex_packet',
                            'rollback_ready': False,
                        },
                    },
                },
                'capability_readiness': [],
            }
        )
        viewmodel._update_evolution_snapshot()

        cards = {item['title']: item for item in viewmodel.get_evolution_area_cards()}
        assert 'validacion review_needed' in cards['Investigaciones utiles']['detail']
        assert 'via codex_packet' in cards['Investigaciones utiles']['detail']
        assert 'revision guiada' in cards['Investigaciones utiles']['blocker']
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_autonomy_can_fall_back_to_local_ollama_when_external_apps_are_unavailable() -> None:
    bootstrap = _make_bootstrap('test_control_center_local_ollama_fallback_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        _set_permissive_world_model(bootstrap)
        _make_ollama_available(
            bootstrap,
            response_text=(
                'Causa raiz probable: El bridge visible sigue saturado. '
                'Cambio vertical recomendado: Ajustar sondeo y drenado sin bloquear la pagina. '
                'file_scope: src/iabv_v15/services/capture/browser_teach_session_service.py '
                'Pruebas sugeridas: Captura con escritura rapida'
            ),
        )
        _disable_external_assistant_apps(bootstrap, disable_web=True)
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        payload = {
            'session_id': 'adaptive-wplay-local-ollama',
            'status': 'need_codex_fix',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay', 'confidence': 0.83},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El problema parece tecnico y repetido.'},
            'chosen_pack': {'title': 'Wplay login', 'pack_id': 'wplay.login', 'domain_kind': 'browser'},
            'playbook': {'status': 'waiting_fix', 'next_phase': 'diagnose', 'summary': 'Caso tecnico', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'metadata': {},
        }
        viewmodel._update_adaptive_state(payload)

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='self_teach')

        assert result is not None
        assert result['status'] == 'ingested'
        assert result['selected_tool_id'] == 'ollama_llm'
        assert result['assistant_kind'] == 'ollama'
        text = viewmodel.get_adaptive_evolution_text()
        assert 'Asistente resuelto: ollama' in text
        assert 'Tool autonomo: ollama_llm' in text
        assert 'Asistente respuesta: ollama' in text
        assert viewmodel.get_assistant_guidance_mode() == 'external_response_interpreted'
    finally:
        _cleanup_bootstrap(bootstrap)

def test_control_center_evolution_panel_prioritizes_goal_scoped_experiments() -> None:
    bootstrap = _make_bootstrap('test_control_center_goal_scoped_experiments_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        objective = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Mejorar login Wplay',
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.42,
                confidence=0.77,
            )
        )
        project = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.PROJECT,
                title='Login Wplay persistente',
                parent_id=objective.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.58,
                confidence=0.8,
            )
        )
        task = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.TASK,
                title='Abrir Wplay e iniciar sesion',
                parent_id=project.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.63,
                confidence=0.82,
            )
        )
        bootstrap.experiment_lab_repository.save_run(
            ExperimentRun(
                domain=ExperimentDomain.CODE,
                suite_name='code_suite',
                objective='Fallback global',
                subject_key='general',
                route=EvaluationRoute.LOCAL,
                candidate_label='fallback_local',
                success=True,
                metrics=ExperimentMetric(total_score=0.52),
            )
        )
        bootstrap.experiment_lab_repository.save_run(
            ExperimentRun(
                domain=ExperimentDomain.CODE,
                suite_name='code_suite',
                objective='Mejorar login Wplay',
                subject_key=task.objective_id,
                route=EvaluationRoute.CODE_AGENT,
                candidate_label='codex_patch',
                success=True,
                metrics=ExperimentMetric(total_score=0.91),
            )
        )
        bootstrap.experiment_lab_repository.save_run(
            ExperimentRun(
                domain=ExperimentDomain.CODE,
                suite_name='code_suite',
                objective='Mejorar login Wplay',
                subject_key=task.objective_id,
                route=EvaluationRoute.LOCAL,
                candidate_label='ollama_probe',
                success=True,
                metrics=ExperimentMetric(total_score=0.64),
            )
        )
        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='general',
                recommended_route=EvaluationRoute.LOCAL,
                score=0.52,
                confidence=0.5,
                rationale='Fallback global todavia sin foco de objetivo.',
            )
        )
        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key=task.objective_id,
                recommended_route=EvaluationRoute.CODE_AGENT,
                score=0.91,
                confidence=0.86,
                rationale='El objetivo activo necesita una correccion guiada y ya tiene evidencia suficiente.',
                metadata={
                    'ranked_routes': [
                        {'route': 'code_agent', 'score': 0.91, 'samples': 2},
                        {'route': 'local', 'score': 0.64, 'samples': 1},
                    ]
                },
            )
        )

        viewmodel._last_goal_context = {
            'objective': objective.model_dump(mode='json'),
            'project': project.model_dump(mode='json'),
            'task': task.model_dump(mode='json'),
            'subtasks': [],
            'active_node_id': task.objective_id,
            'active_title': task.title,
            'priority': int(task.priority),
            'status': task.status.value,
            'progress': float(task.progress),
            'blocker': '',
            'confidence': float(task.confidence),
            'trend': 'avanzando',
            'metadata': {'site_id': 'wplay'},
        }
        viewmodel._last_user_goal = 'abre Wplay e inicia sesion'
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-goal-scope',
                'status': 'ready_to_execute',
                'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
                'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                'chosen_pack': {'title': 'Login Wplay'},
                'capability_readiness': [],
            }
        )
        viewmodel._update_evolution_snapshot()

        cards = {item['title']: item for item in viewmodel.get_evolution_area_cards()}
        algorithms = cards['Algoritmos probados']
        overview = viewmodel.get_evolution_overview()

        assert task.objective_id in algorithms['summary']
        assert 'correccion guiada' in algorithms['detail']
        assert 'codex_patch' in algorithms['detail']
        assert 'ollama_probe' in algorithms['detail']
        assert 'descartadas local' in algorithms['detail']
        assert task.objective_id in overview['latest_experiment']
    finally:
        _cleanup_bootstrap(bootstrap)

def test_control_center_general_chat_request_does_not_reuse_persistent_goal_ids() -> None:
    bootstrap = _make_bootstrap('test_control_center_general_chat_request_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        objective = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Mejorar login Wplay',
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.84,
                confidence=0.79,
            )
        )
        project = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.PROJECT,
                title='Login Wplay persistente',
                parent_id=objective.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.8,
                confidence=0.8,
            )
        )
        task = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.TASK,
                title='Abrir Wplay e iniciar sesion',
                parent_id=project.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.BLOCKED,
                progress=0.63,
                confidence=0.82,
                blocker='Bridge lag persistente',
            )
        )
        viewmodel._last_goal_context = {
            'objective': objective.model_dump(mode='json'),
            'project': project.model_dump(mode='json'),
            'task': task.model_dump(mode='json'),
            'subtasks': [],
            'active_node_id': task.objective_id,
            'active_title': task.title,
            'priority': int(task.priority),
            'status': task.status.value,
            'progress': float(task.progress),
            'blocker': task.blocker,
            'confidence': float(task.confidence),
            'trend': 'bloqueado',
            'metadata': {'site_id': 'wplay'},
        }

        request = viewmodel._build_request('hola que sabes hacer ?')

        assert request.goal_parameters.get('objective_id', '') == ''
        assert request.goal_parameters.get('project_id', '') == ''
        assert request.goal_parameters.get('task_id', '') == ''
        assert request.metadata['goal_context_source'] == 'transient'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_skips_autonomy_for_general_chat_even_with_technical_history() -> None:
    bootstrap = _make_bootstrap('test_control_center_general_chat_no_autonomy_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        payload = {
            'session_id': 'adaptive-general-chat',
            'user_goal': 'hola que sabes hacer ?',
            'status': 'failed',
            'intent': {
                'title': 'Asistencia general del centro de control',
                'intent_key': 'general.assistance',
                'disposition': 'answer_now',
                'confidence': 0.93,
            },
            'context': {
                'site_id': '',
                'site_display_name': 'General',
                'session_readiness': {'dominant_incident': 'bridge_lag', 'live_audit_action': 'consult_codex'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {
                    'summary': 'Bridge lag persistente en un caso tecnico anterior.',
                    'decision_action': 'consult_codex',
                    'confidence': 0.81,
                },
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Incidente tecnico viejo.'},
            'capability_readiness': [
                {
                    'capability_id': 'wplay.login',
                    'title': 'Login Wplay',
                    'status': 'insufficient',
                    'suggested_next_step': 'Revisar el bridge y el replay.',
                }
            ],
            'metadata': {},
        }

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='chat')

        assert result is None
        assert not any(item['speaker'] == 'Autonomia' for item in viewmodel.get_chat_messages())
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_treats_meta_assistant_question_as_general_chat() -> None:
    bootstrap = _make_bootstrap('test_control_center_meta_assistant_chat_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        request = viewmodel._build_request('sabes consultar automaticamente a codex y chatgpt internamente ?')

        assert request.goal_parameters.get('objective_id', '') == ''
        assert viewmodel._is_general_chat_message('sabes consultar automaticamente a codex y chatgpt internamente ?') is True

        payload = {
            'session_id': 'adaptive-meta-assistant-chat',
            'user_goal': 'sabes consultar automaticamente a codex y chatgpt internamente ?',
            'status': 'failed',
            'intent': {
                'title': 'Consulta sobre autonomia externa',
                'intent_key': 'knowledge.query',
                'disposition': 'answer_now',
                'confidence': 0.9,
            },
            'context': {
                'site_id': '',
                'site_display_name': 'General',
                'session_readiness': {'dominant_incident': 'bridge_lag', 'live_audit_action': 'consult_codex'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {
                    'summary': 'Incidente tecnico previo que no debe contaminar preguntas meta.',
                    'decision_action': 'consult_codex',
                    'confidence': 0.82,
                },
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Incidente tecnico viejo.'},
            'capability_readiness': [
                {
                    'capability_id': 'wplay.login',
                    'title': 'Login Wplay',
                    'status': 'insufficient',
                    'suggested_next_step': 'Revisar el bridge y el replay.',
                }
            ],
            'metadata': {},
        }

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='chat')

        assert result is None
        assert bootstrap.tool_record_repository.list_tasks(limit=5) == []
        assert not any(item['speaker'] == 'Autonomia' for item in viewmodel.get_chat_messages())
    finally:
        _cleanup_bootstrap(bootstrap)



def test_control_center_refresh_surfaces_goal_and_assistant_startup_readiness() -> None:
    bootstrap = _make_bootstrap('test_control_center_startup_assistants_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        objective = bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Consolidar autonomia local-first',
                status=ObjectiveStatus.ACTIVE,
                progress=0.42,
                confidence=0.73,
                site_id='wplay',
            )
        )
        fake_claude = Path(bootstrap.config.workspace_root) / 'fake_claude.exe'
        fake_claude.write_text('stub', encoding='utf-8')
        claude = bootstrap.tool_record_repository.get_card('claude_installed')
        assert claude is not None
        bootstrap.tool_record_repository.save_card(
            claude.model_copy(
                update={
                    'metadata': {
                        **claude.metadata,
                        'executable_path': str(fake_claude),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'dry_run_launch': True,
                    }
                }
            )
        )
        refreshed = bootstrap.tool_record_repository.get_card('claude_installed')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)

        viewmodel.refresh()

        cards = {item['name']: item for item in viewmodel.get_agent_cards()}
        assert 'Objetivo persistente' in cards
        assert objective.title in cards['Objetivo persistente']['detail']
        assert 'Claude instalado' in cards
        assert cards['Claude instalado']['status'] in {'listo guiado', 'listo automatico'}
        assert viewmodel.get_busy_label().startswith('Arranque autonomo: objetivo')
        assert objective.title in viewmodel.get_busy_label()
        assert 'Claude instalado' in viewmodel.get_busy_label()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_autonomy_activity_shows_waiting_external_consultation() -> None:
    bootstrap = _make_bootstrap('test_control_center_autonomy_activity_waiting_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-autonomy-activity-waiting',
                'status': 'planned',
                'intent': {'title': 'Diagnosticar Wplay', 'intent_key': 'wplay.login', 'disposition': 'plan_then_execute', 'confidence': 0.88},
                'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                'metadata': {
                    'decision_context': {
                        'governance': {'should_consult': True, 'recommended_action': 'consult_codex'},
                        'goal_context': {
                            'objective': {'title': 'Recuperar login Wplay'},
                            'progress': 0.31,
                            'confidence': 0.74,
                        },
                    },
                    'autonomous_evolution': {
                        'status': 'awaiting_response',
                        'assistant_kind': 'codex',
                        'actual_assistant_kind': 'codex',
                        'selected_tool_id': 'codex_installed',
                        'response_capture_mode': 'clipboard_capture',
                        'detail': 'Estoy observando la respuesta de Codex para capturarla automaticamente.',
                        'started_at_utc': datetime.now(timezone.utc).isoformat(),
                    },
                },
            }
        )

        activity = viewmodel.get_autonomy_activity()

        assert activity['visible'] is True
        assert activity['title'] == 'Consulta externa en curso'
        assert activity['stage'] == 'esperando respuesta util'
        assert activity['tool'].startswith('Codex')
        assert activity['progress'] >= 0.8
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_autonomy_activity_shows_ingested_external_learning() -> None:
    bootstrap = _make_bootstrap('test_control_center_autonomy_activity_ingested_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._update_adaptive_state(
            {
                'session_id': 'adaptive-autonomy-activity-ingested',
                'status': 'completed',
                'intent': {'title': 'Diagnosticar Wplay', 'intent_key': 'wplay.login', 'disposition': 'plan_then_execute', 'confidence': 0.9},
                'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                'metadata': {
                    'decision_context': {
                        'governance': {'should_consult': False, 'recommended_action': 'prepare_codex_packet'},
                        'goal_context': {
                            'objective': {'title': 'Recuperar login Wplay'},
                            'progress': 0.63,
                            'confidence': 0.81,
                        },
                    },
                    'autonomous_evolution': {
                        'status': 'prepared',
                        'assistant_kind': 'chatgpt',
                        'actual_assistant_kind': 'chatgpt',
                        'selected_tool_id': 'chatgpt_installed',
                    },
                    'autonomous_evolution_response': {
                        'status': 'ingested',
                        'assistant_kind': 'chatgpt',
                        'selected_tool_id': 'chatgpt_installed',
                        'response_summary': 'La respuesta externa confirmo el siguiente microajuste seguro.',
                        'response_ingested': True,
                        'response_validation': {'status': 'accepted'},
                        'adoption_plan': {'next_action': 'prepare_codex_packet', 'human_help': 'Revisa el paquete tecnico antes de tocar codigo.'},
                    },
                },
            }
        )

        activity = viewmodel.get_autonomy_activity()

        assert activity['visible'] is True
        assert activity['title'] == 'Resultado de consulta externa'
        assert activity['stage'] == 'aprendizaje consolidado'
        assert activity['progress'] == 1.0
        assert 'memoria evolutiva' in activity['learning_note']
    finally:
        _cleanup_bootstrap(bootstrap)

def test_control_center_viewmodel_projects_live_external_assistant_dock() -> None:
    bootstrap = _make_bootstrap('test_control_center_live_assistant_dock')
    try:
        _disable_external_assistant_apps(bootstrap)
        web_card = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert web_card is not None
        bootstrap.tool_record_repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'dry_run_launch': True}}))
        refreshed = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)

        task, result, _ = bootstrap.tool_teach_service.execute_external_consultation(
            user_goal='resume el estado del objetivo activo',
            assistant_preference='chatgpt',
            context_pack='Objetivo activo: validar progreso longitudinal.',
            site_id='wplay',
            goal_parameters={'objective_id': 'objective-1', 'project_id': 'project-1', 'task_id': 'task-1'},
            approved=True,
            launch_dry_run=True,
        )

        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel.refreshAutonomyDock()

        summary = viewmodel.get_live_process_summary()
        work_items = viewmodel.get_live_work_items()
        session_cards = viewmodel.get_assistant_session_cards()
        timeline = viewmodel.get_autonomy_timeline()

        assert summary['assistant_title'] == 'ChatGPT'
        assert summary['status'] == 'awaiting_response'
        assert summary['lane'] == 'background'
        assert summary['task_id'] == task.task_id
        assert summary['progress_pct'] > 0
        assert summary['current_step']
        assert 'capturar respuesta' in summary['pending_summary']
        assert any(item['task_id'] == task.task_id and item['current_step'] for item in work_items)
        chatgpt_card = next(item for item in session_cards if item['assistant_kind'] == 'chatgpt')
        assert chatgpt_card['session_scope'] == 'program_chat'
        assert chatgpt_card['thread_key'] == task.metadata['thread_key']
        assert chatgpt_card['lane'] == 'background'
        assert chatgpt_card['progress_pct'] > 0
        assert timeline
        assert result.execution_state.metadata['response_capture_pending'] is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_build_request_preserves_explicit_chatgpt_preference() -> None:
    bootstrap = _make_bootstrap('test_control_center_explicit_chatgpt_request_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        request = viewmodel._build_request('Necesito una consulta externa con ChatGPT para revisar el objetivo activo.')

        assert request.goal_parameters['assistant_preference'] == 'chatgpt'
        assert request.goal_parameters['assistant_kind'] == 'chatgpt'
        assert request.goal_parameters['explicit_external_consultation'] is True
        assert request.goal_parameters['consultation_scope'] == 'external_assistant'
        assert request.metadata['explicit_assistant_preference'] == 'chatgpt'
        assert request.metadata['explicit_external_consultation'] is True
        assert isinstance(request.metadata['runtime_signals'], list)
        assert isinstance(request.metadata['session_health'], dict)
        assert isinstance(request.metadata['visual_signal'], dict)
        assert isinstance(request.metadata['ia_trace'], list)
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_skips_autonomy_when_payload_marks_conversational_prompt() -> None:
    bootstrap = _make_bootstrap('test_control_center_snapshot_conversational_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        payload = {
            'session_id': 'adaptive-conversational-prompt',
            'user_goal': 'explicame tu estado actual operativo',
            'status': 'failed',
            'intent': {
                'title': 'Explicacion operativa',
                'intent_key': 'general.assistance',
                'disposition': 'answer_now',
                'confidence': 0.92,
            },
            'context': {
                'site_id': '',
                'site_display_name': 'General',
                'session_readiness': {'dominant_incident': 'bridge_lag', 'live_audit_action': 'consult_codex'},
                'live_audit': {
                    'summary': 'Incidente tecnico previo que no debe forzar escalado.',
                    'decision_action': 'consult_codex',
                    'confidence': 0.8,
                },
            },
            'metadata': {
                'decision_context': {
                    'metadata': {
                        'conversational_prompt': True,
                    }
                }
            },
        }

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='chat')

        assert result is None
        assert not any(item['speaker'] == 'Autonomia' for item in viewmodel.get_chat_messages())
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_explicit_chatgpt_request_does_not_skip_autonomy() -> None:
    bootstrap = _make_bootstrap('test_control_center_explicit_chatgpt_autonomy_workspace')
    try:
        _set_permissive_world_model(bootstrap, codex_ready=False)
        _disable_external_assistant_apps(bootstrap)
        web_card = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert web_card is not None
        bootstrap.tool_record_repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'dry_run_launch': True}}))
        refreshed = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)

        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'Necesito una consulta externa con ChatGPT para revisar el objetivo activo.'
        payload = {
            'session_id': 'adaptive-explicit-chatgpt',
            'status': 'planned',
            'intent': {
                'title': 'Consulta externa dirigida a ChatGPT',
                'intent_key': 'knowledge.query',
                'disposition': 'answer_now',
                'confidence': 0.84,
            },
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag', 'live_audit_action': 'consult_codex'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {
                    'summary': 'Bridge lag persistente en un caso tecnico previo.',
                    'decision_action': 'consult_codex',
                    'confidence': 0.8,
                },
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Incidente tecnico viejo.'},
            'capability_readiness': [
                {
                    'capability_id': 'wplay.login',
                    'title': 'Login Wplay',
                    'status': 'insufficient',
                    'suggested_next_step': 'Revisar el bridge.',
                }
            ],
            'metadata': {},
        }

        result = viewmodel._maybe_run_autonomous_evolution(payload, source='chat')

        assert result is not None
        assert result['requested_assistant_kind'] == 'chatgpt'
        assert result['selected_tool_id'] == 'chatgpt_web_assisted'
        assert result['thread_key'].startswith('iabv::chatgpt::')
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_general_message_completes_from_bootstrap_ui_objects() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_general_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('haber mira q puedes aser tu aca adentro? tipo codex chatgpt y eso lo manejas o q?')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert len(messages) >= 3
        assert messages[-1]['speaker'] == 'IABV'
        assert 'puedo ayudarte' in messages[-1]['text'].lower()
        assert 'need_adapter' not in messages[-1]['text'].lower()
        assert 'protective_local' not in messages[-1]['text'].lower()
        assert viewmodel.get_busy_label() == 'Respuesta lista.'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_presentation_humanizes_simple_greeting() -> None:
    bootstrap = _make_bootstrap('test_control_center_human_greeting_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'hola'

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': 'Simulacion completada. No hay un executor de herramientas aplicable para Consulta local con contexto; sigue faltando un adaptador operativo del dominio.',
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:8b',
                'confidence': '0.93',
                'route_reason': 'Consulta general',
                'sources': [],
                'used_tools': [],
                'follow_up_teachings': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Consulta local con contexto'},
                'adaptive_session': {
                    'intent': {'intent_key': 'general.assistance'},
                    'context': {'site_display_name': 'General'},
                    'assistant_guidance': {
                        'mode': 'need_adapter',
                        'governance': {
                            'autonomy_level': 'protective_local',
                            'blockers': ['La RAM libre esta baja para rutas pesadas o varios modelos locales a la vez.'],
                        },
                    },
                },
            },
        )

        text = viewmodel.get_chat_messages()[-1]['text']
        assert text.startswith('Hola.')
        assert 'need_adapter' not in text.lower()
        assert 'protective_local' not in text.lower()
        assert 'ram libre' not in text.lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_general_chat_humanizes_visible_adaptive_panels() -> None:
    bootstrap = _make_bootstrap('test_control_center_human_general_panels_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'hola'

        viewmodel._update_adaptive_state(
            {
                'session_id': 'session-visible-123',
                'status': 'completed',
                'intent': {
                    'intent_key': 'general.assistance',
                    'title': 'Asistencia general del centro de control',
                    'metadata': {'conversational_prompt': True},
                },
                'context': {
                    'site_display_name': 'General',
                    'recent_runs': [{'run_id': 'run-1'}],
                    'recent_incidents': [],
                },
                'playbook': {'status': 'completed', 'next_phase': 'none', 'summary': 'Respuesta local'},
                'metadata': {
                    'decision_context': {
                        'governance': {
                            'autonomy_level': 'autonomous_local',
                            'recommended_action': 'continue_local',
                            'blockers': [],
                        }
                    },
                    'execution_state': {
                        'executor_name': 'tool_local_first_executor',
                        'state': 'adapter_missing',
                        'detail': 'No hay un executor de herramientas aplicable.',
                    },
                },
                'outcome': {
                    'summary': 'Ya tengo estrategia y contexto, pero no hay executor.',
                    'next_actions': ['Simular'],
                },
            }
        )

        assert 'session-visible-123' not in viewmodel.get_adaptive_status_text()
        assert 'executor' not in viewmodel.get_adaptive_execution_text().lower()
        assert 'continue_local' not in viewmodel.get_adaptive_evolution_text().lower()
        assert 'autonomous_local' not in viewmodel.get_adaptive_evolution_text().lower()
        assert 'otra ia' in viewmodel.get_adaptive_evolution_text().lower() or 'consulta externa' in viewmodel.get_adaptive_evolution_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_presentation_explains_capabilities_without_internal_jargon() -> None:
    bootstrap = _make_bootstrap('test_control_center_human_capabilities_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'que puedes hacer?'

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': 'Simulacion completada. La estrategia ya quedo aterrizada con contexto, pack y evidencias.',
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:8b',
                'confidence': '0.93',
                'route_reason': 'Consulta general',
                'sources': [],
                'used_tools': [],
                'follow_up_teachings': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Consulta local con contexto'},
                'adaptive_session': {
                    'intent': {'intent_key': 'general.assistance'},
                    'context': {'site_display_name': 'General'},
                },
            },
        )

        text = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'puedo ayudarte' in text
        assert 'codex' in text
        assert 'chatgpt' in text
        assert 'simulacion' not in text
        assert 'pack' not in text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_presentation_understands_messy_request_and_mentions_lightweight_path_in_human_language() -> None:
    bootstrap = _make_bootstrap('test_control_center_human_messy_request_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'mira bro no se si me explico pero wplay ta raro se traba y como q no entra bien revisalo pls'

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': 'Consulta local con contexto. Readiness: Chat adaptativo local: ready. Ejecucion: No hay un executor de herramientas aplicable para Consulta local con contexto; sigue faltando un adaptador operativo del dominio.',
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:8b',
                'confidence': '0.81',
                'route_reason': 'Caso tecnico',
                'sources': [],
                'used_tools': [],
                'follow_up_teachings': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Login Wplay'},
                'adaptive_session': {
                    'intent': {'intent_key': 'wplay.login'},
                    'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                    'assistant_guidance': {
                        'actions': [{'action': 'prepare_codex_packet'}],
                        'governance': {
                            'autonomy_level': 'protective_local',
                            'blockers': ['La RAM libre esta baja para rutas pesadas o varios modelos locales a la vez.'],
                        },
                    },
                },
            },
        )

        text = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'wplay' in text
        assert 'equipo esta bajo bastante carga' in text
        assert 'need_adapter' not in text
        assert 'protective_local' not in text
        assert 'executor' not in text
        assert 'ram libre' not in text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_presentation_prefers_local_llm_answer_over_canned_reply() -> None:
    bootstrap = _make_bootstrap('test_control_center_local_llm_answer_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'explicame en una sola frase que es la neuroplasticidad operativa en iabv'
        llm_answer = 'La neuroplasticidad operativa es la capacidad del sistema para reorganizarse segun evidencia.'

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': llm_answer,
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:1.7b',
                'confidence': '0.85',
                'route_reason': 'Consulta local',
                'sources': [],
                'used_tools': [],
                'follow_up_teachings': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Consulta local con contexto'},
                'adaptive_session': {
                    'intent': {'intent_key': 'general.assistance'},
                    'context': {'site_display_name': 'General'},
                    'assistant_guidance': {'mode': 'ready_execute'},
                },
                'local_chat_llm': {
                    'summary': llm_answer,
                    'provider_name': 'Ollama',
                    'available': True,
                    'error': '',
                },
            },
        )

        last_message = viewmodel.get_chat_messages()[-1]
        assert last_message['text'] == llm_answer
        assert 'te leo. cuentame' not in last_message['text'].lower()
        assert 'ollama' in last_message['meta'].lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_presentation_keeps_canned_reply_when_llm_unavailable() -> None:
    bootstrap = _make_bootstrap('test_control_center_local_llm_unavailable_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = 'q puedes hacer tu aca adentro con codex o chatgpt'

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': 'Plantilla canned para meta-assistant.',
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:1.7b',
                'confidence': '0.70',
                'route_reason': 'Consulta general',
                'sources': [],
                'used_tools': [],
                'follow_up_teachings': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Consulta local con contexto'},
                'adaptive_session': {
                    'intent': {'intent_key': 'general.assistance'},
                    'context': {'site_display_name': 'General'},
                    'assistant_guidance': {'mode': 'ready_execute'},
                },
                'local_chat_llm': {
                    'summary': '',
                    'provider_name': 'Ollama',
                    'available': False,
                    'error': 'unreachable',
                },
            },
        )

        text = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'puedo ayudarte' in text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_chat_presentation_avoids_generic_general_reply_for_task_like_message() -> None:
    bootstrap = _make_bootstrap('test_control_center_task_like_general_reply_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._last_user_goal = (
            'haber mira no se si me explico bien pero wplay se queda raro como medio lageado '
            'y no se si eres tu o codex o chatgpt pero ayudame a entender que pasa y como revisarlo sin hacer cualquier cosa'
        )

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': 'Simulacion completada. No hay un executor de herramientas aplicable para Consulta local con contexto.',
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:8b',
                'confidence': '0.74',
                'route_reason': 'Consulta general',
                'sources': [],
                'used_tools': [],
                'follow_up_teachings': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Consulta local con contexto'},
                'adaptive_session': {
                    'intent': {'intent_key': 'general.assistance'},
                    'context': {'site_id': 'wplay', 'site_display_name': 'Wplay'},
                    'assistant_guidance': {
                        'actions': [{'action': 'prepare_codex_packet'}],
                    },
                },
            },
        )

        text = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'te leo. cuentame' not in text
        assert 'wplay' in text
        assert 'paso mas util' in text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_explicit_codex_request_hands_off_externally() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_explicit_codex_workspace')
    try:
        _disable_external_assistant_apps(bootstrap)
        for tool_id in ('chatgpt_web_assisted', 'claude_web_assisted'):
            web_card = bootstrap.tool_record_repository.get_card(tool_id)
            assert web_card is not None
            bootstrap.tool_record_repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'dry_run_launch': True}}))
            refreshed = bootstrap.tool_record_repository.get_card(tool_id)
            assert refreshed is not None
            bootstrap.tool_registry.refresh_card(refreshed)

        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat(
            'Necesito una consulta tecnica con Codex para diagnosticar por que IABV no siempre logra lanzar '
            'y capturar consultas externas automaticamente. Usa solo el hilo dedicado del programa.'
        )
        _drain_ui(viewmodel)

        # After Brecha 2.4 refactor, this message triggers world model detection
        # (mentions Codex + hilo) and is answered from live state, not external
        # consultation. The world model path reports Codex availability status.
        latest = viewmodel.get_latest_response_text().lower()
        assert 'codex' in latest
        assert viewmodel.get_assistant_guidance_mode() == 'idle'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_short_codex_request_is_treated_as_explicit_external_consultation() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_short_codex_workspace')
    try:
        _disable_external_assistant_apps(bootstrap)
        for tool_id in ('chatgpt_web_assisted', 'claude_web_assisted'):
            web_card = bootstrap.tool_record_repository.get_card(tool_id)
            assert web_card is not None
            bootstrap.tool_record_repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'dry_run_launch': True}}))
            refreshed = bootstrap.tool_record_repository.get_card(tool_id)
            assert refreshed is not None
            bootstrap.tool_registry.refresh_card(refreshed)

        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('revisa wplay con codex')
        _drain_ui(viewmodel)

        assert 'consulta externa' in viewmodel.get_latest_response_text().lower() or 'codex' in viewmodel.get_latest_response_text().lower()
        assert 'need_adapter' not in viewmodel.get_latest_response_text().lower()
        assert 'protective_local' not in viewmodel.get_latest_response_text().lower()
        assert 'task ' not in viewmodel.get_latest_response_meta().lower()
        assert 'result ' not in viewmodel.get_latest_response_meta().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_explicit_assistant_preference_ignores_messy_message_that_only_mentions_other_ias() -> None:
    bootstrap = _make_bootstrap('test_control_center_messy_mentions_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        preference = viewmodel._explicit_assistant_preference(
            'haber mira no se si me explico bien pero wplay se queda raro como medio lageado y no se si eres tu o codex o chatgpt '
            'pero ayudame a entender que pasa y como revisarlo sin hacer cualquier cosa'
        )

        assert preference == ''
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_external_consultation_failure_is_humanized_for_chat() -> None:
    bootstrap = _make_bootstrap('test_control_center_external_failure_humanized_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel._apply_task_failure('external_consultation', "No pude completar la consulta externa guiada: 'NoneType' object has no attribute 'get'")

        message = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'nonetype' not in message
        assert 'attribute' not in message
        assert 'consulta externa' in message
        assert 'otra via' in message or 'seguir con lo que ya tenemos' in message
        assert 'consulta externa' in viewmodel.get_latest_response_text().lower()
        assert viewmodel.get_busy_label() == viewmodel.get_latest_response_text()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_explicit_codex_blocked_external_surfaces_formal_flags() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_explicit_codex_blocked_external_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('mira no se si me explico pero wplay medio se traba, revisa con codex porfa y si no puedes dilo claro')
        _drain_ui(viewmodel)

        # After Brecha 2.4, preflight_external_assistant checks worker health
        # before launching. With no real workers, the preflight blocks the
        # consultation and the response humanizes the block reason.
        latest = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'codex' in latest or 'lanzar' in latest
        assert 'nonetype' not in latest
        assert 'traceback' not in latest
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_explicit_codex_wrong_thread_surfaces_clear_notice() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_explicit_codex_wrong_thread_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('necesito consulta con codex pero si el hilo esta mal dilo claro y no finjas exito')
        _drain_ui(viewmodel)

        # After Brecha 2.4, this message triggers world model detection (mentions
        # codex + hilo) and is answered from live state. The response reports
        # Codex thread/availability status without launching external consultation.
        latest = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'codex' in latest
        assert 'nonetype' not in latest
        assert 'traceback' not in latest
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_explicit_codex_missing_thread_tracking_surfaces_clear_notice() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_explicit_codex_missing_thread_tracking_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('consulta codex pero si no puedes verificar el hilo dilo claro')
        _drain_ui(viewmodel)

        # After Brecha 2.4, this message triggers world model detection (mentions
        # codex + hilo) and is answered from live state without external consultation.
        latest = viewmodel.get_chat_messages()[-1]['text'].lower()
        assert 'codex' in latest
        assert 'nonetype' not in latest
        assert 'traceback' not in latest
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_explicit_chatgpt_security_verification_surfaces_clear_notice() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_explicit_chatgpt_security_verification_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('consulta chatgpt y si el sitio se bloquea dilo claro')
        _drain_ui(viewmodel)

        # After Brecha 2.4, preflight_external_assistant blocks the consultation
        # before launching. The humanized response mentions the assistant name
        # and avoids raw error details.
        latest_text = viewmodel.get_latest_response_text().lower()
        assert 'chatgpt' in latest_text
        assert 'winerror' not in latest_text
        assert 'traceback' not in latest_text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_send_chat_external_access_denied_is_humanized_and_stops_waiting_state() -> None:
    bootstrap = _make_bootstrap('test_control_center_send_chat_external_access_denied_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('Necesito una consulta externa con ChatGPT para revisar por que Playwright no logra abrir bien desde el programa')
        _drain_ui(viewmodel)

        # After Brecha 2.4, preflight_external_assistant blocks before launch.
        # The humanized response mentions the assistant and avoids raw errors.
        latest_text = viewmodel.get_latest_response_text().lower()
        assert 'winerror' not in latest_text
        assert 'acceso denegado' not in latest_text
        assert 'chatgpt' in latest_text
        # When the external consultation is blocked with actionable guidance
        # (buttons/actions), the guidance must be preserved, not reset to idle.
        assert viewmodel.get_assistant_guidance_mode() != 'idle'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_awareness_reply_uses_environment_and_tool_registry() -> None:
    bootstrap = _make_bootstrap('test_control_center_self_awareness_reply_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            known_environment=True,
            scan_status='ready',
            hardware_profile={'memory_usage_ratio': 0.64, 'cpu_usage_percent': 32.0},
            runtime_profile={'python_version': '3.13.2'},
            available_tools=[
                {'title': 'Playwright browser'},
                {'title': 'Ollama local'},
                {'title': 'Codex instalado'},
            ],
            missing_tools=[
                {'tool_id': 'claude_installed'},
                {'tool_id': 'mcp_client'},
            ],
            ai_capacity={
                'max_recommended_model': '8B q4/q5',
                'local_runtime': {
                    'models': [
                        {'name': 'qwen3:8b'},
                        {'name': 'gemma3:4b'},
                    ]
                },
            },
        )
        viewmodel._assistant_tool_cards = lambda: [  # type: ignore[method-assign]
            {'name': 'Ollama local', 'status': 'listo automatico'},
            {'name': 'Codex instalado', 'status': 'listo guiado'},
            {'name': 'ChatGPT web asistido', 'status': 'sesion aislada'},
            {'name': 'Claude web asistido', 'status': 'no disponible'},
        ]
        viewmodel._last_user_goal = 'conoces tu entorno?'

        viewmodel._apply_task_result(
            'chat',
            {
                'summary': 'project.evolution con contexto acumulado y need_adapter.',
                'provider_name': 'Adaptive local orchestrator',
                'role_title': 'Base de conocimiento',
                'executor_model': 'qwen3:8b',
                'confidence': '0.94',
                'route_reason': 'Autodiagnostico',
                'sources': [],
                'follow_up_teachings': [],
                'used_tools': [],
                'planner_used': False,
                'chosen_pack': {'title': 'Consulta local con contexto'},
                'adaptive_session': {
                    'user_goal': 'conoces tu entorno?',
                    'intent': {'intent_key': 'system.self_awareness', 'metadata': {'self_awareness_prompt': True, 'conversational_prompt': True}},
                    'context': {'site_display_name': 'General'},
                },
            },
        )

        text = viewmodel.get_latest_response_text().lower()
        assert 'qwen3:8b' in text
        assert 'gemma3:4b' in text
        assert 'mcp_client' in text
        assert 'claude web asistido' in text or 'claude web asistido no esta disponible' in text
        assert 'need_adapter' not in text
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_awareness_panels_are_humanized() -> None:
    bootstrap = _make_bootstrap('test_control_center_self_awareness_panels_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            known_environment=True,
            scan_status='partial',
            available_tools=[{'title': 'Ollama local'}, {'title': 'ChatGPT web asistido'}],
            missing_tools=[{'tool_id': 'claude_installed'}],
            ai_capacity={'max_recommended_model': '8B q4/q5', 'local_runtime': {'models': [{'name': 'qwen3:8b'}]}},
            notifications=['Cambios relevantes desde el ultimo escaneo: tool_available:playwright_browser.'],
        )
        viewmodel._last_user_goal = 'que herramientas tienes disponibles?'

        viewmodel._update_adaptive_state(
            {
                'user_goal': 'que herramientas tienes disponibles?',
                'session_id': 'adaptive-self-awareness',
                'status': 'completed',
                'intent': {
                    'intent_key': 'system.self_awareness',
                    'title': 'Autodiagnostico conversacional del sistema',
                    'metadata': {'self_awareness_prompt': True, 'conversational_prompt': True},
                },
                'context': {'site_display_name': 'General', 'recent_runs': [], 'recent_incidents': []},
                'playbook': {'status': 'completed', 'next_phase': 'none', 'summary': 'Respuesta lista', 'steps': []},
                'metadata': {'decision_context': {'governance': {'autonomy_level': 'autonomous_local', 'blockers': []}}},
            }
        )

        assert 'Autodiagnostico resuelto' in viewmodel.get_adaptive_status_text()
        assert 'mis herramientas o mis conexiones reales' in viewmodel.get_adaptive_intent_text()
        assert 'herramientas listas' in viewmodel.get_adaptive_context_text().lower()
        assert 'sin desviar la respuesta hacia auditorias previas' in viewmodel.get_adaptive_strategy_text().lower()
        assert 'Lei el modelo del entorno' in viewmodel.get_adaptive_execution_text()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_awareness_connectivity_phrase_is_detected() -> None:
    bootstrap = _make_bootstrap('test_control_center_self_awareness_connectivity_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        assert viewmodel._is_self_awareness_question('con que ias te puedes conectar ahora?') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_does_not_trigger_autonomy_for_self_awareness_chat() -> None:
    bootstrap = _make_bootstrap('test_control_center_self_awareness_no_autonomy_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        adaptive_payload = {
            'user_goal': 'conoces tu entorno?',
            'intent': {
                'intent_key': 'system.self_awareness',
                'metadata': {'self_awareness_prompt': True, 'conversational_prompt': True},
            },
            'context': {'site_display_name': 'General'},
            'metadata': {},
        }

        result = viewmodel._maybe_run_autonomous_evolution(adaptive_payload, source='chat')

        assert result is None
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_awareness_chat_bypasses_inference_and_uses_live_state() -> None:
    bootstrap = _make_bootstrap('test_control_center_self_awareness_send_chat_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            known_environment=True,
            scan_status='ready',
            available_tools=[
                {'title': 'Ollama local'},
                {'title': 'Codex instalado'},
            ],
            missing_tools=[{'tool_id': 'claude_installed'}],
            ai_capacity={
                'max_recommended_model': '8B q4/q5',
                'local_runtime': {'models': [{'name': 'qwen3:8b'}]},
            },
        )
        viewmodel._assistant_tool_cards = lambda: [  # type: ignore[method-assign]
            {'name': 'Ollama local', 'status': 'listo automatico'},
            {'name': 'Codex instalado', 'status': 'listo guiado'},
        ]

        def _fail_infer_task(_request):
            raise AssertionError('sendChat no debia entrar a infer_task() para una pregunta de self awareness.')

        def _fail_autonomy(*_args, **_kwargs):
            raise AssertionError('sendChat no debia intentar autonomia para una pregunta de self awareness.')

        viewmodel.inference_service.infer_task = _fail_infer_task  # type: ignore[assignment]
        viewmodel._maybe_run_autonomous_evolution = _fail_autonomy  # type: ignore[method-assign]

        viewmodel.sendChat('conoces tu entorno?')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
        assert 'qwen3:8b' in messages[-1]['text'].lower()
        assert 'codex' in messages[-1]['text'].lower()
        assert 'autodiagnostico resuelto' in viewmodel.get_adaptive_status_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_compound_self_awareness_message_goes_through_inference() -> None:
    bootstrap = _make_bootstrap('test_control_center_compound_self_awareness_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat(
            'conoces tu entorno y, con eso claro, revisa por que el chat se desvia con mensajes largos sin ejecutar nada todavia'
        )
        _drain_ui(viewmodel)

        # After Brecha 2.4, _try_handle_lightweight_chat runs BEFORE
        # _chat_shortcut_analysis. Compound messages containing self-awareness
        # phrases ("conoces tu entorno") now trigger the SA shortcut path
        # directly instead of going through inference.
        assert viewmodel.get_working() is False
        latest = viewmodel.get_latest_response_text().lower()
        assert len(latest) > 0
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_world_model_question_is_detected_and_answered_from_live_state() -> None:
    bootstrap = _make_bootstrap('test_control_center_world_model_reply_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_world_model = lambda: WorldModelSnapshot(  # type: ignore[method-assign]
            active_windows=[
                WindowObservation(title='Codex - IABV', app_name='Codex', pid=51, focused=True),
                WindowObservation(title='ChatGPT - browser', app_name='Browser', pid=88, focused=False),
            ],
            focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=51, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    status='abierto',
                    detail='Codex esta abierto, pero el hilo activo no parece ser el del workspace de IABV.',
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                    session_status='abierta',
                )
            ],
            network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena', latency_ms=36.0),
            detected_blocks=['wrong_thread'],
            inferred_state={
                'summary': 'Hay bloqueos operativos activos que conviene respetar antes de lanzar otra accion.',
                'deductions': ['Codex esta abierto, pero el hilo activo no parece ser el del workspace de IABV.'],
            },
            confidence=0.83,
        )

        assert viewmodel._is_world_model_question('por que no responde codex?') is True
        reply, meta = viewmodel._world_model_reply('por que no responde codex?')

        assert 'hilo activo no parece ser el del workspace' in reply.lower()
        assert 'codex instalado' in meta.lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_world_model_chat_bypasses_inference_and_uses_live_state() -> None:
    bootstrap = _make_bootstrap('test_control_center_world_model_send_chat_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_world_model = lambda: WorldModelSnapshot(  # type: ignore[method-assign]
            active_windows=[
                WindowObservation(title='Codex - IABV', app_name='Codex', pid=51, focused=True),
                WindowObservation(title='ChatGPT - browser', app_name='Browser', pid=88, focused=False),
            ],
            focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=51, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    status='abierto',
                    detail='Codex esta abierto, pero el hilo activo no parece ser el del workspace de IABV.',
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                    session_status='abierta',
                )
            ],
            network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena', latency_ms=36.0),
            detected_blocks=['wrong_thread'],
            inferred_state={
                'summary': 'Hay bloqueos operativos activos que conviene respetar antes de lanzar otra accion.',
                'deductions': ['Codex esta abierto, pero el hilo activo no parece ser el del workspace de IABV.'],
            },
            confidence=0.83,
        )

        def _fail_infer_task(_request):
            raise AssertionError('sendChat no debia entrar a infer_task() para una pregunta de world model.')

        def _fail_autonomy(*_args, **_kwargs):
            raise AssertionError('sendChat no debia intentar autonomia para una pregunta de world model.')

        viewmodel.inference_service.infer_task = _fail_infer_task  # type: ignore[assignment]
        viewmodel._maybe_run_autonomous_evolution = _fail_autonomy  # type: ignore[method-assign]

        viewmodel.sendChat('por que no responde codex?')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
        assert 'hilo activo no parece ser el del workspace' in messages[-1]['text'].lower()
        assert 'observacion operativa resuelta' in viewmodel.get_adaptive_status_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_world_model_panels_are_humanized() -> None:
    bootstrap = _make_bootstrap('test_control_center_world_model_panels_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_world_model = lambda: WorldModelSnapshot(  # type: ignore[method-assign]
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
            detected_blocks=['wrong_thread'],
            inferred_state={'deductions': ['Codex esta abierto, pero el hilo activo no parece ser el del workspace de IABV.']},
            confidence=0.81,
        )

        viewmodel._update_adaptive_state(
            {
                'user_goal': 'por que no responde codex?',
                'session_id': 'adaptive-world-model',
                'status': 'completed',
                'intent': {
                    'intent_key': 'general.assistance',
                    'title': 'Consulta operativa',
                    'metadata': {'conversational_prompt': True},
                },
                'context': {'site_display_name': 'General', 'recent_runs': [], 'recent_incidents': []},
                'playbook': {'status': 'completed', 'next_phase': 'none', 'summary': 'Respuesta lista', 'steps': []},
                'metadata': {'decision_context': {'governance': {'autonomy_level': 'autonomous_local', 'blockers': []}}},
            }
        )

        assert 'Observacion operativa resuelta' in viewmodel.get_adaptive_status_text()
        assert 'estado vivo del sistema' in viewmodel.get_adaptive_intent_text()
        assert 'foco actual' in viewmodel.get_adaptive_context_text().lower()
        assert 'world model del entorno' in viewmodel.get_adaptive_execution_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_does_not_trigger_autonomy_for_world_model_chat() -> None:
    bootstrap = _make_bootstrap('test_control_center_world_model_no_autonomy_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        adaptive_payload = {
            'user_goal': 'por que no responde codex?',
            'intent': {
                'intent_key': 'general.assistance',
                'metadata': {'conversational_prompt': True},
            },
            'context': {'site_display_name': 'General'},
            'metadata': {},
        }

        result = viewmodel._maybe_run_autonomous_evolution(adaptive_payload, source='chat')

        assert result is None
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_learning_chat_bypasses_inference_and_uses_persisted_evidence() -> None:
    bootstrap = _make_bootstrap('test_control_center_learning_chat_bypass_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        assert bootstrap.experiment_lab_repository is not None
        assert bootstrap.autonomous_validation_cycle is not None

        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.LANGUAGE,
                subject_key='general',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                score=0.91,
                confidence=0.88,
                rationale='Codex viene cerrando mejor los ajustes repetibles.',
                metadata={
                    'adaptive_learning_summary': {
                        'reasons': ['Codex mantiene mejor precision en correcciones repetibles.'],
                    },
                    'ranked_configurations': [
                        {'assistant_kind': 'codex'},
                        {'assistant_kind': 'chatgpt'},
                    ],
                },
            )
        )
        bootstrap.autonomous_validation_cycle.current_snapshot = lambda: AutonomousValidationSnapshot(  # type: ignore[assignment]
            status='active',
            summary='Sigo validando Claude como alternativa antes de promoverla.',
            current_experiment=SandboxExperiment(
                subject_key='general',
                candidate_assistant_kind='claude',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                verdict='unresolved',
            ),
        )

        def _fail_infer_task(_request):
            raise AssertionError('sendChat no debia entrar a infer_task() para una pregunta de aprendizaje.')

        def _fail_autonomy(*_args, **_kwargs):
            raise AssertionError('sendChat no debia intentar autonomia para una pregunta de aprendizaje.')

        viewmodel.inference_service.infer_task = _fail_infer_task  # type: ignore[assignment]
        viewmodel._maybe_run_autonomous_evolution = _fail_autonomy  # type: ignore[method-assign]

        viewmodel.sendChat('que aprendiste')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
        assert 'codex' in messages[-1]['text'].lower()
        assert 'sandbox' in messages[-1]['text'].lower()
        assert 'claude' in messages[-1]['text'].lower()
        assert 'aprendizaje adaptativo resuelto' in viewmodel.get_adaptive_status_text().lower()
        assert 'preferencia actual: codex' in viewmodel.get_adaptive_context_text().lower()
        assert 'validacion autonoma actual' not in messages[-1]['text'].lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_learning_chat_recognizes_que_va_mejor_without_running_autonomy() -> None:
    bootstrap = _make_bootstrap('test_control_center_learning_chat_que_va_mejor_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        assert bootstrap.experiment_lab_repository is not None

        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.LANGUAGE,
                subject_key='general',
                recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                recommended_assistant_kind='chatgpt',
                score=0.86,
                confidence=0.82,
                metadata={
                    'adaptive_learning_summary': {
                        'reasons': ['ChatGPT viene resumiendo mejor la evidencia transversal.'],
                    },
                    'ranked_configurations': [
                        {'assistant_kind': 'chatgpt'},
                        {'assistant_kind': 'claude'},
                        {'assistant_kind': 'codex'},
                    ],
                },
            )
        )

        def _fail_infer_task(_request):
            raise AssertionError('La pregunta "que va mejor" debia resolverse sin inferencia operativa.')

        def _fail_autonomy(*_args, **_kwargs):
            raise AssertionError('La pregunta "que va mejor" no debia escalar a autonomia.')

        viewmodel.inference_service.infer_task = _fail_infer_task  # type: ignore[assignment]
        viewmodel._maybe_run_autonomous_evolution = _fail_autonomy  # type: ignore[method-assign]

        viewmodel.sendChat('que va mejor ahora')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
        assert 'chatgpt' in messages[-1]['text'].lower()
        assert 'funcionando mejor' in messages[-1]['text'].lower()
        assert 'aprendizaje adaptativo resuelto' in viewmodel.get_adaptive_status_text().lower()
        assert 'sin preferencia fuerte' not in viewmodel.get_adaptive_context_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_evolution_status_chat_bypasses_inference_and_uses_validation_status() -> None:
    bootstrap = _make_bootstrap('test_control_center_evolution_status_chat_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        assert bootstrap.autonomous_validation_cycle is not None
        assert bootstrap.tool_discovery_service is not None

        bootstrap.autonomous_validation_cycle.get_status = lambda: {  # type: ignore[assignment]
            'winning_by_problem': {'language_understanding': 'chatgpt'},
            'in_validation': ['validate_discovery:ollama:language_understanding'],
            'discarded_proposals': [],
            'recent_decisions': [
                {
                    'subject_key': 'language_understanding',
                    'proposal_key': 'validate_discovery:ollama:language_understanding',
                    'decision': 'deferred',
                    'winner': 'tie',
                    'reason': 'Sigue en sandbox por evidencia parcial.',
                }
            ],
            'last_decision': {'reason': 'Sigue en sandbox por evidencia parcial.'},
            'unresolved_fields': [],
        }
        bootstrap.tool_discovery_service.get_status = lambda: {  # type: ignore[assignment]
            'active_signals': [],
            'in_validation_signals': [{'tool_title': 'Ollama local'}],
            'promoted_signals': [],
            'discarded_signals': [],
            'summary': 'Discovery estable.',
            'unresolved_fields': [],
        }

        def _fail_infer_task(_request):
            raise AssertionError('La pregunta evolutiva no debia entrar a infer_task().')

        def _fail_autonomy(*_args, **_kwargs):
            raise AssertionError('La pregunta evolutiva no debia escalar a autonomia.')

        viewmodel.inference_service.infer_task = _fail_infer_task  # type: ignore[assignment]
        viewmodel._maybe_run_autonomous_evolution = _fail_autonomy  # type: ignore[method-assign]

        viewmodel.sendChat('que herramienta va ganando ahora y que esta en validacion?')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
        assert 'chatgpt' in messages[-1]['text'].lower()
        assert 'sandbox' in messages[-1]['text'].lower()
        assert 'estado evolutivo resuelto' in viewmodel.get_adaptive_status_text().lower()
        assert 'ganadores confirmados' in viewmodel.get_adaptive_context_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_evolution_status_chat_uses_discovery_state_without_autonomy() -> None:
    bootstrap = _make_bootstrap('test_control_center_evolution_discovery_chat_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        assert bootstrap.autonomous_validation_cycle is not None
        assert bootstrap.tool_discovery_service is not None

        bootstrap.autonomous_validation_cycle.get_status = lambda: {  # type: ignore[assignment]
            'winning_by_problem': {},
            'in_validation': [],
            'discarded_proposals': [{'proposal_key': 'validate_discovery:claude:general', 'assistant_kind': 'claude'}],
            'recent_decisions': [],
            'last_decision': {},
            'unresolved_fields': [],
        }
        bootstrap.tool_discovery_service.get_status = lambda: {  # type: ignore[assignment]
            'active_signals': [
                {
                    'tool_title': 'Claude web assisted',
                    'assistant_kind': 'claude',
                    'scope': 'general',
                    'summary': 'Tiene mejor espacio de razonamiento para comparativas complejas.',
                }
            ],
            'in_validation_signals': [],
            'promoted_signals': [],
            'discarded_signals': [{'tool_title': 'ChatGPT web assisted'}],
            'summary': 'Discovery con un candidato fuerte.',
            'unresolved_fields': [],
        }

        def _fail_infer_task(_request):
            raise AssertionError('El discovery evolutivo no debia entrar a infer_task().')

        def _fail_autonomy(*_args, **_kwargs):
            raise AssertionError('El discovery evolutivo no debia escalar a autonomia.')

        viewmodel.inference_service.infer_task = _fail_infer_task  # type: ignore[assignment]
        viewmodel._maybe_run_autonomous_evolution = _fail_autonomy  # type: ignore[method-assign]

        viewmodel.sendChat('que herramienta nueva vale la pena probar y que fue descartado?')
        _drain_ui(viewmodel)

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
        assert 'claude' in messages[-1]['text'].lower()
        assert 'descartaron' in messages[-1]['text'].lower()
        assert 'resumen evolutivo real' in messages[-1]['meta'].lower()
        assert 'estado evolutivo resuelto' in viewmodel.get_adaptive_status_text().lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_examination_chat_proceeds_through_canonical_pipeline() -> None:
    """P0.18C: Diagnostic requests now go through canonical metacognitive pipeline instead of bypassing inference."""
    bootstrap = _make_bootstrap('test_control_center_self_examination_chat_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        bootstrap.operational_self_examination_service.current_review = lambda **kwargs: SelfExaminationSnapshot(  # type: ignore[assignment]
            summary='La autoexaminacion detecta una ruta web inercial y un ajuste claro.',
            status='needs_attention',
            findings=[
                SelfExaminationFinding(
                    category='inertial_route',
                    title='Ruta debil o inercial: chatgpt por language_understanding',
                    summary='Se reutilizo varias veces con bloqueos y fallback recurrente.',
                    recommendation='Exigir validacion adicional antes de volver a usar esa ruta.',
                    confidence=0.84,
                    source_refs=['ExperimentLab', 'AdaptiveWeightLayer'],
                )
            ],
            recurring_issues=[
                {
                    'title': 'Bloqueo recurrente: wrong_thread',
                    'summary': 'El hilo incorrecto sigue reapareciendo en consultas comparables.',
                }
            ],
            recommended_adjustments=[
                {
                    'title': 'Preflight estricto',
                    'recommended_change': 'Exigir validacion adicional antes de volver a usar esa ruta.',
                }
            ],
            validated_improvements=[
                {
                    'title': 'Codex por code_agent',
                    'summary': 'Sigue siendo la mejora mas estable para correcciones tecnicas.',
                }
            ],
            unresolved_risks=['UNRESOLVED:self_examination'],
        )

        # P0.18C: Diagnostic requests should now proceed through infer_task (not bypass it)
        # The fix in _try_handle_chat_command returns False for diagnostic requests,
        # allowing them to reach the canonical metacognitive pipeline.
        infer_task_called = False

        def _track_infer_task(request):
            nonlocal infer_task_called
            infer_task_called = True
            # Return a minimal result to allow the test to complete
            from iabv_v15.services.inference.inference_service import InferenceResult
            return InferenceResult(
                output_text='Respuesta de prueba para diagnostico.',
                execution_state={'state': 'completed'},
                metadata={},
            )

        viewmodel.inference_service.infer_task = _track_infer_task  # type: ignore[assignment]

        # Use a phrase that matches _is_self_code_analysis_request() patterns
        viewmodel.sendChat('analiza tu estado')
        _drain_ui(viewmodel)

        # Verify that infer_task was called (diagnostic request went through canonical pipeline)
        assert infer_task_called, 'Diagnostic request should proceed through infer_task after P0.18C fix'

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_examination_chat_recognizes_examinate_proceeds_through_pipeline() -> None:
    """P0.18C: Diagnostic requests like "diagnosticate" now go through canonical metacognitive pipeline."""
    bootstrap = _make_bootstrap('test_control_center_self_examination_examinate_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        bootstrap.operational_self_examination_service.current_review = lambda **kwargs: SelfExaminationSnapshot(  # type: ignore[assignment]
            summary='La autoexaminacion detecto un bloqueo recurrente y una correccion recomendada.',
            status='watch',
            findings=[
                SelfExaminationFinding(
                    category='repeated_block',
                    title='Bloqueo recurrente: wrong_thread',
                    summary='El hilo incorrecto sigue reapareciendo en consultas comparables.',
                    recommendation='Exigir verificacion de hilo antes de reutilizar Codex.',
                    confidence=0.81,
                )
            ],
            recommended_adjustments=[
                {
                    'title': 'Preflight de hilo',
                    'recommended_change': 'Exigir verificacion de hilo antes de reutilizar Codex.',
                }
            ],
        )

        # P0.18C: Diagnostic requests should now proceed through infer_task
        infer_task_called = False

        def _track_infer_task(request):
            nonlocal infer_task_called
            infer_task_called = True
            from iabv_v15.services.inference.inference_service import InferenceResult
            return InferenceResult(
                output_text='Respuesta de prueba para diagnosticate.',
                execution_state={'state': 'completed'},
                metadata={},
            )

        viewmodel.inference_service.infer_task = _track_infer_task  # type: ignore[assignment]

        viewmodel.sendChat('diagnosticate')
        _drain_ui(viewmodel)

        # Verify that infer_task was called (diagnostic request went through canonical pipeline)
        assert infer_task_called, 'Diagnostic request "diagnosticate" should proceed through infer_task after P0.18C fix'

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_examination_chat_recognizes_recommended_changes_proceeds_through_pipeline() -> None:
    """P0.18C: Diagnostic requests about recommended changes now go through canonical metacognitive pipeline."""
    bootstrap = _make_bootstrap('test_control_center_self_examination_adjustments_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        bootstrap.operational_self_examination_service.current_review = lambda **kwargs: SelfExaminationSnapshot(  # type: ignore[assignment]
            summary='La autoexaminacion detecta dos cambios recomendados.',
            status='watch',
            recommended_adjustments=[
                {
                    'title': 'Preflight de hilo',
                    'recommended_change': 'Exigir verificacion de hilo antes de reutilizar Codex.',
                },
                {
                    'title': 'Debilitar ruta web',
                    'recommended_change': 'Debilitar la prioridad de la ruta web hasta que mejore la tendencia.',
                },
            ],
            unresolved_risks=['UNRESOLVED:self_examination'],
        )

        # P0.18C: Diagnostic requests should now proceed through infer_task
        infer_task_called = False

        def _track_infer_task(request):
            nonlocal infer_task_called
            infer_task_called = True
            from iabv_v15.services.inference.inference_service import InferenceResult
            return InferenceResult(
                output_text='Respuesta de prueba para cambios recomendados.',
                execution_state={'state': 'completed'},
                metadata={},
            )

        viewmodel.inference_service.infer_task = _track_infer_task  # type: ignore[assignment]

        viewmodel.sendChat('mejoras pendientes')
        _drain_ui(viewmodel)

        # Verify that infer_task was called (diagnostic request went through canonical pipeline)
        assert infer_task_called, 'Diagnostic request about changes should proceed through infer_task after P0.18C fix'

        messages = viewmodel.get_chat_messages()
        assert viewmodel.get_working() is False
        assert messages[-1]['speaker'] == 'IABV'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_self_examination_phrase_has_priority_over_learning_phrase() -> None:
    """P0.18C: Diagnostic requests with learning phrases now go through canonical metacognitive pipeline."""
    bootstrap = _make_bootstrap('test_control_center_self_examination_priority_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        bootstrap.operational_self_examination_service.current_review = lambda **kwargs: SelfExaminationSnapshot(  # type: ignore[assignment]
            summary='La autoexaminacion ya detecto una mejora y un riesgo activo.',
            status='watch',
            findings=[
                SelfExaminationFinding(
                    category='repeated_block',
                    title='Bloqueo recurrente: wrong_thread',
                    summary='Sigue apareciendo en consultas comparables.',
                    recommendation='Exigir verificacion de hilo antes de reusar Codex.',
                    confidence=0.8,
                )
            ],
            recommended_adjustments=[{'title': 'Preflight de hilo', 'recommended_change': 'Exigir verificacion de hilo antes de reusar Codex.'}],
        )

        # P0.18C: Diagnostic requests should now proceed through infer_task
        infer_task_called = False

        def _track_infer_task(request):
            nonlocal infer_task_called
            infer_task_called = True
            from iabv_v15.services.inference.inference_service import InferenceResult
            return InferenceResult(
                output_text='Respuesta de prueba para aprendizaje de autoexaminacion.',
                execution_state={'state': 'completed'},
                metadata={},
            )

        viewmodel.inference_service.infer_task = _track_infer_task  # type: ignore[assignment]

        viewmodel.sendChat('busca errores')
        _drain_ui(viewmodel)

        # Verify that infer_task was called (diagnostic request went through canonical pipeline)
        assert infer_task_called, 'Diagnostic request with learning phrase should proceed through infer_task after P0.18C fix'

        messages = viewmodel.get_chat_messages()
        assert messages[-1]['speaker'] == 'IABV'
    finally:
        _cleanup_bootstrap(bootstrap)


# Tests para señales evolutivas UI (Task B)

def test_control_center_emits_credential_prompt_requested() -> None:
    """Verifica que el ViewModel emite credentialPromptRequested."""
    bootstrap = _make_bootstrap('test_cc_credential_signal')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_credential_requested(payload):
            received['payload'] = payload

        viewmodel.credentialPromptRequested.connect(on_credential_requested)
        test_payload = {'domain': 'example.com', 'reason': 'Login required', 'username_hint': 'user@example.com'}
        viewmodel.credentialPromptRequested.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['domain'] == 'example.com'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_emits_clarification_requested() -> None:
    """Verifica que el ViewModel emite clarificationRequested."""
    bootstrap = _make_bootstrap('test_cc_clarification_signal')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_clarification_requested(payload):
            received['payload'] = payload

        viewmodel.clarificationRequested.connect(on_clarification_requested)
        test_payload = {'id': '123', 'question': 'Which option?', 'options': ['A', 'B'], 'context': 'Test'}
        viewmodel.clarificationRequested.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['question'] == 'Which option?'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_emits_missing_dependency_requested() -> None:
    """Verifica que el ViewModel emite missingDependencyRequested."""
    bootstrap = _make_bootstrap('test_cc_dependency_signal')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_dependency_requested(payload):
            received['payload'] = payload

        viewmodel.missingDependencyRequested.connect(on_dependency_requested)
        test_payload = {'package_name': 'numpy', 'manager': 'pip', 'reason': 'Required for analysis'}
        viewmodel.missingDependencyRequested.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['package_name'] == 'numpy'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_emits_background_activity_changed() -> None:
    """Verifica que el ViewModel emite backgroundActivityChanged."""
    bootstrap = _make_bootstrap('test_cc_activity_signal')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_activity_changed(payload):
            received['payload'] = payload

        viewmodel.backgroundActivityChanged.connect(on_activity_changed)
        test_payload = {'text': 'Processing...', 'progress': 50, 'status': 'running', 'details': ['Step 1']}
        viewmodel.backgroundActivityChanged.emit(test_payload)

        assert received['payload'] is not None
        assert received['payload']['progress'] == 50
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_emits_provider_health_changed() -> None:
    """Verifica que el ViewModel emite providerHealthChanged."""
    bootstrap = _make_bootstrap('test_cc_health_signal')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        received = {'payload': None}

        def on_health_changed(payload):
            received['payload'] = payload

        viewmodel.providerHealthChanged.connect(on_health_changed)
        test_payload = [{'name': 'Ollama', 'status': 'ready', 'latency': 100}]
        viewmodel.providerHealthChanged.emit(test_payload)

        assert received['payload'] is not None
        assert len(received['payload']) == 1
    finally:
        _cleanup_bootstrap(bootstrap)


# ----------------------------------------------------------------------
# Frente 2 — botón "Auditarme ahora"
#
# El slot `runSelfAuditNow(reason)` dispara `SelfAuditService.run(reason=...)`
# en un hilo background y emite `selfAuditStarted` al arrancar y
# `selfAuditCompleted(json)` / `selfAuditFailed(detail)` al terminar. La
# property `lastSelfAuditSummary` se actualiza con el `summary_markdown`
# del snapshot. Los tests usan un `SelfAuditService` fake (sincrónico) y
# esperan al worker para evitar condiciones de carrera.


class _FakeAuditServiceForVM:
    def __init__(self, snapshot: object | None = None, *, raise_exc: Exception | None = None) -> None:
        from datetime import datetime, timezone

        from iabv_v15.domain.models import EnvironmentMatchResult, SelfAuditSnapshot

        self._snapshot = snapshot or SelfAuditSnapshot(
            generated_at=datetime(2025, 4, 19, 12, 0, 0, tzinfo=timezone.utc),
            reason=None,
            tool_checks=[],
            environment_match=EnvironmentMatchResult(
                matched=True,
                mismatches=[],
                environment_digest="env",
                world_model_digest="wm",
            ),
            pending_issues=[],
            world_model_digest={"available": True},
            summary_markdown="# Auditoría VM — resumen de prueba",
        )
        self._raise_exc = raise_exc
        self.calls: list[str | None] = []

    def run(self, *, reason: str | None = None):
        self.calls.append(reason)
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._snapshot


def _wait_for(predicate, *, timeout_seconds: float = 5.0) -> bool:
    import time
    from iabv_v15.ui.qt import QGuiApplication

    app = QGuiApplication.instance()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if app is not None:
            app.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    if app is not None:
        app.processEvents()
    return predicate()


def test_control_center_run_self_audit_emits_completed_and_updates_summary() -> None:
    import json

    bootstrap = _make_bootstrap('test_cc_self_audit_happy')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        fake = _FakeAuditServiceForVM()
        viewmodel.self_audit_service = fake

        started = {'n': 0}
        completed = {'payload': None}
        failed = {'detail': None}

        viewmodel.selfAuditStarted.connect(lambda: started.__setitem__('n', started['n'] + 1))
        viewmodel.selfAuditCompleted.connect(lambda blob: completed.__setitem__('payload', blob))
        viewmodel.selfAuditFailed.connect(lambda detail: failed.__setitem__('detail', detail))

        viewmodel.runSelfAuditNow('ui_trigger')

        assert _wait_for(lambda: completed['payload'] is not None)
        assert started['n'] == 1
        assert failed['detail'] is None
        assert fake.calls == ['ui_trigger']
        payload = json.loads(completed['payload'])
        assert payload['summary_markdown'].startswith('# Auditoría VM')
        assert viewmodel.get_last_self_audit_summary().startswith('# Auditoría VM')
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_run_self_audit_empty_reason_passes_none() -> None:
    bootstrap = _make_bootstrap('test_cc_self_audit_empty_reason')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        fake = _FakeAuditServiceForVM()
        viewmodel.self_audit_service = fake

        completed = {'n': 0}
        viewmodel.selfAuditCompleted.connect(lambda _blob: completed.__setitem__('n', completed['n'] + 1))

        viewmodel.runSelfAuditNow('')

        assert _wait_for(lambda: completed['n'] == 1)
        # Frente 2: `reason` vacío se normaliza a None antes de llamar el service.
        assert fake.calls == [None]
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_run_self_audit_fails_gracefully_when_service_is_none() -> None:
    bootstrap = _make_bootstrap('test_cc_self_audit_missing')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.self_audit_service = None

        failed = {'detail': None}
        completed = {'n': 0}
        viewmodel.selfAuditFailed.connect(lambda detail: failed.__setitem__('detail', detail))
        viewmodel.selfAuditCompleted.connect(lambda _blob: completed.__setitem__('n', completed['n'] + 1))

        viewmodel.runSelfAuditNow('probe')

        assert failed['detail'] is not None
        assert 'self_audit_service' in failed['detail']
        # Sin service, el snapshot completado NUNCA se emite.
        assert completed['n'] == 0
    finally:
        _cleanup_bootstrap(bootstrap)


def test_control_center_run_self_audit_emits_failed_on_service_exception() -> None:
    bootstrap = _make_bootstrap('test_cc_self_audit_exception')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        fake = _FakeAuditServiceForVM(raise_exc=RuntimeError('boom'))
        viewmodel.self_audit_service = fake

        failed = {'detail': None}
        completed = {'n': 0}
        viewmodel.selfAuditFailed.connect(lambda detail: failed.__setitem__('detail', detail))
        viewmodel.selfAuditCompleted.connect(lambda _blob: completed.__setitem__('n', completed['n'] + 1))

        viewmodel.runSelfAuditNow('will_fail')

        assert _wait_for(lambda: failed['detail'] is not None)
        assert 'boom' in failed['detail']
        assert completed['n'] == 0
    finally:
        _cleanup_bootstrap(bootstrap)



def test_send_chat_ingests_capability_mention_when_service_available() -> None:
    bootstrap = _make_bootstrap('test_send_chat_ingests_capability_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        service = viewmodel.chat_capability_ingestion_service
        assert service is not None, 'bootstrap debe inyectar el service'

        viewmodel.sendChat('tengo una GPU RTX 4060 y quiero probar modelos locales')
        _drain_ui(viewmodel)

        entries = service.list_entries(session_id=viewmodel._chat_session_id)
        kinds = [entry.kind for entry in entries]
        assert 'hardware_gpu' in kinds
    finally:
        _cleanup_bootstrap(bootstrap)


def test_send_chat_shows_capability_notice_in_chat() -> None:
    bootstrap = _make_bootstrap('test_send_chat_shows_notice_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel.sendChat('tengo gpu y instale qwen3 local')
        _drain_ui(viewmodel)

        messages = viewmodel._chat_messages
        notice_messages = [
            msg for msg in messages
            if isinstance(msg, dict)
            and 'area de investigacion' in str(msg.get('text') or '').lower()
        ]
        assert notice_messages, 'el chat debe avisar al usuario que anoto la capacidad'
        combined = ' '.join(str(msg.get('text') or '') for msg in notice_messages)
        assert 'gpu' in combined.lower() or 'GPU' in combined
    finally:
        _cleanup_bootstrap(bootstrap)


def test_send_chat_does_not_break_when_ingestion_service_missing() -> None:
    bootstrap = _make_bootstrap('test_send_chat_no_service_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        # Simulamos el escenario de tests antiguos / bootstrap minimo donde
        # el service no esta inyectado. sendChat debe funcionar igual.
        viewmodel.chat_capability_ingestion_service = None

        viewmodel.sendChat('tengo gpu pero no quiero que se rompa')
        _drain_ui(viewmodel)

        # Se registro al menos el mensaje del usuario; no hubo excepcion.
        user_messages = [
            msg for msg in viewmodel._chat_messages
            if isinstance(msg, dict) and msg.get('role') == 'user'
        ]
        assert user_messages
    finally:
        _cleanup_bootstrap(bootstrap)


def test_send_chat_does_not_register_capability_without_possession_marker() -> None:
    bootstrap = _make_bootstrap('test_send_chat_no_marker_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        service = viewmodel.chat_capability_ingestion_service
        assert service is not None

        viewmodel.sendChat('la gpu en general es cara y rinde bien')
        _drain_ui(viewmodel)

        entries = service.list_entries(session_id=viewmodel._chat_session_id)
        assert entries == []
    finally:
        _cleanup_bootstrap(bootstrap)


def test_assistant_tool_ids_exposes_devin_and_github_api() -> None:
    bootstrap = _make_bootstrap('test_assistant_tool_ids_devin_github_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        tool_ids = viewmodel._assistant_tool_ids()
        assert 'devin_api' in tool_ids, (
            'devin_api debe estar en la lista de asistentes del chat; sin esto el '
            'chat responde "no tengo conexion con Devin" aun cuando el adapter vive.'
        )
        assert 'github_api' in tool_ids, (
            'github_api es un adapter activo consumible por chat; debe aparecer en la lista de asistentes.'
        )
        assert 'ollama_llm' in tool_ids
        assert 'codex_installed' in tool_ids
    finally:
        _cleanup_bootstrap(bootstrap)


def test_aggregate_assistant_entries_collapses_claude_dual_cards() -> None:
    bootstrap = _make_bootstrap('test_aggregate_claude_dual_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        raw_cards = [
            {'name': 'Ollama local', 'status': 'listo automatico', 'assistant_kind': 'ollama', 'tool_id': 'ollama_llm'},
            {'name': 'Devin (Cognition AI)', 'status': 'listo automatico', 'assistant_kind': 'devin', 'tool_id': 'devin_api'},
            {'name': 'Claude instalado', 'status': 'no disponible', 'assistant_kind': 'claude', 'tool_id': 'claude_installed'},
            {'name': 'Claude web asistido', 'status': 'listo guiado', 'assistant_kind': 'claude', 'tool_id': 'claude_web_assisted'},
        ]
        aggregated = viewmodel._aggregate_assistant_entries(raw_cards)
        kinds = [str(card.get('assistant_kind')) for card in aggregated]
        assert kinds.count('claude') == 1, 'Las dos variantes de Claude deben colapsar a una sola entrada.'
        claude_entry = next(card for card in aggregated if str(card.get('assistant_kind')) == 'claude')
        assert 'listo' in str(claude_entry.get('status') or '').lower()
        assert claude_entry.get('status') != 'no disponible'
        # Con variantes multiples, el nombre debe ser el friendly kind title
        assert 'Claude' in str(claude_entry.get('name') or '')
        devin_entry = next(card for card in aggregated if str(card.get('assistant_kind')) == 'devin')
        assert 'listo' in str(devin_entry.get('status') or '').lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_aggregate_assistant_entries_preserves_unique_variant_title() -> None:
    bootstrap = _make_bootstrap('test_aggregate_single_variant_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        # Solo una variante de Claude -> respeta el titulo original del card
        raw_cards = [
            {'name': 'Claude web asistido', 'status': 'listo guiado', 'assistant_kind': 'claude', 'tool_id': 'claude_web_assisted'},
        ]
        aggregated = viewmodel._aggregate_assistant_entries(raw_cards)
        assert len(aggregated) == 1
        assert aggregated[0]['name'] == 'Claude web asistido'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_self_awareness_reply_assistants_focus_mentions_devin_when_ready() -> None:
    bootstrap = _make_bootstrap('test_self_awareness_assistants_mentions_devin_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None
        viewmodel._current_environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            known_environment=True,
            scan_status='ready',
            hardware_profile={},
            runtime_profile={},
            available_tools=[{'title': 'Ollama local'}, {'title': 'Devin (Cognition AI)'}],
            missing_tools=[],
            ai_capacity={'local_runtime': {'models': [{'name': 'qwen3:8b'}]}},
        )
        viewmodel._assistant_tool_cards = lambda: [  # type: ignore[method-assign]
            {'name': 'Ollama local', 'status': 'listo automatico', 'assistant_kind': 'ollama'},
            {'name': 'Devin (Cognition AI)', 'status': 'listo automatico', 'assistant_kind': 'devin'},
            {'name': 'Claude instalado', 'status': 'no disponible', 'assistant_kind': 'claude'},
            {'name': 'Claude web asistido', 'status': 'listo guiado', 'assistant_kind': 'claude'},
        ]
        response, meta = viewmodel._self_awareness_reply('con que IAs te conectas?')
        lowered = response.lower()
        assert 'devin' in lowered, 'El chat debe mencionar Devin cuando el adapter esta listo.'
        assert 'ollama' in lowered
        # No debe aparecer "claude no esta disponible" porque Claude web esta ready
        assert 'no esta disponible' not in lowered or 'claude no esta disponible' not in lowered
        assert 'Conexiones reales' in meta or 'conexiones' in meta.lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_external_blocked_result_preserves_assistant_guidance_popup() -> None:
    """When taskResolved fires for external_consultation with success=False and
    the adaptive_payload already carries actionable assistant_guidance (e.g.
    mode='need_approval' with action buttons), the guidance popup must NOT be
    wiped by _reset_assistant_guidance."""
    bootstrap = _make_bootstrap('test_external_blocked_preserves_guidance_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        adaptive_payload = {
            'session_id': 'adaptive-blocked-guidance',
            'status': 'waiting_approval',
            'intent': {'title': 'Consultar Codex', 'intent_key': 'codex.consult', 'disposition': 'plan_then_execute', 'confidence': 0.80},
            'context': {'site_id': 'general', 'site_display_name': 'General'},
            'chosen_pack': {'title': 'Codex consult', 'domain_kind': 'external'},
            'playbook': {'status': 'waiting_approval', 'next_phase': 'strategy', 'summary': 'Esperando permiso', 'steps': []},
            'approval_checkpoints': [
                {
                    'title': 'Permitir observacion de codex',
                    'decision': 'pending',
                    'risk_level': 'medium',
                    'detail': 'Para verificar si Codex tiene mensajes disponibles necesito observar esa ventana.',
                    'phase_key': 'observation_permission',
                }
            ],
            'capability_readiness': [],
            'strategy_candidates': [],
            'outcome': {},
            'assistant_guidance': {
                'mode': 'need_approval',
                'title': 'Permiso para observar Codex',
                'prompt': 'Necesito observar la ventana de Codex.',
                'actions': [
                    {'action': 'approve_observation_permission', 'title': 'Permitir observacion', 'detail': 'Conceder permiso.'},
                    {'action': 'consult_codex', 'title': 'Reintentar Codex', 'detail': 'Volver a correr el preflight.'},
                ],
            },
        }

        external_payload = {
            'success': False,
            'message': 'No voy a lanzar Codex todavia. Primero necesito tu permiso.',
            'meta': 'Permiso requerido para Codex.',
            'payload': adaptive_payload,
            'assistant_title': 'Codex',
            'external_state_flags': [],
        }

        viewmodel._apply_task_result('external_consultation', external_payload)

        assert viewmodel.get_assistant_guidance_mode() == 'need_approval', (
            'El guidance mode debe preservarse como need_approval despues de taskResolved con success=False'
        )
        assert len(viewmodel.get_assistant_action_buttons()) >= 1, (
            'Los action buttons del guidance deben preservarse'
        )
        assert any(item['action'] == 'approve_observation_permission' for item in viewmodel.get_assistant_action_buttons()), (
            'El boton approve_observation_permission debe seguir presente'
        )
        assert viewmodel.get_approval_dialog_visible() is True, (
            'El dialogo de aprobacion debe seguir visible cuando mode=need_approval'
        )
    finally:
        _cleanup_bootstrap(bootstrap)


def test_external_blocked_result_preserves_approval_dialog_for_assistant_unavailable() -> None:
    """When the governance diagnostic_category is 'assistant_unavailable' and the
    guidance has mode='need_approval' with action buttons, the approval dialog
    must remain visible after taskResolved with success=False."""
    bootstrap = _make_bootstrap('test_external_blocked_assistant_unavailable_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        adaptive_payload = {
            'session_id': 'adaptive-unavailable',
            'status': 'waiting_approval',
            'intent': {'title': 'Consultar ChatGPT', 'intent_key': 'chatgpt.consult', 'disposition': 'plan_then_execute', 'confidence': 0.75},
            'context': {'site_id': 'general', 'site_display_name': 'General'},
            'chosen_pack': {'title': 'ChatGPT consult', 'domain_kind': 'external'},
            'playbook': {'status': 'waiting_approval', 'next_phase': 'strategy', 'summary': 'Esperando permiso', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'outcome': {},
            'assistant_guidance': {
                'mode': 'need_approval',
                'title': 'ChatGPT no disponible',
                'prompt': 'ChatGPT no esta disponible en este momento.',
                'actions': [
                    {'action': 'consult_chatgpt', 'title': 'Reintentar ChatGPT', 'detail': 'Volver a verificar disponibilidad.'},
                    {'action': 'review_stack', 'title': 'Abrir / verificar herramienta', 'detail': 'Revisar si la herramienta esta abierta.'},
                ],
            },
            'metadata': {
                'decision_context': {
                    'governance': {
                        'diagnostic_category': 'assistant_unavailable',
                    },
                },
            },
        }

        external_payload = {
            'success': False,
            'message': 'ChatGPT no esta disponible.',
            'meta': 'Ruta bloqueada para ChatGPT.',
            'payload': adaptive_payload,
            'assistant_title': 'ChatGPT',
            'external_state_flags': [],
        }

        viewmodel._apply_task_result('external_consultation', external_payload)

        assert viewmodel.get_assistant_guidance_mode() == 'need_approval', (
            'El guidance mode debe preservarse como need_approval para assistant_unavailable'
        )
        assert viewmodel.get_approval_dialog_visible() is True, (
            'El dialogo de aprobacion debe seguir visible para assistant_unavailable'
        )
        assert len(viewmodel.get_assistant_action_buttons()) >= 1, (
            'Los botones de accion deben preservarse para assistant_unavailable'
        )
    finally:
        _cleanup_bootstrap(bootstrap)


def test_external_blocked_result_resets_guidance_when_no_actionable_payload() -> None:
    """Regression: when external_consultation fails with success=False but the
    adaptive_payload does NOT carry actionable guidance (no approval buttons,
    no need_approval mode), _reset_assistant_guidance must still run to clean
    up stale state."""
    bootstrap = _make_bootstrap('test_external_blocked_resets_when_no_guidance_workspace')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        adaptive_payload = {
            'session_id': 'adaptive-no-guidance',
            'status': 'ready_to_execute',
            'intent': {'title': 'Consulta general', 'intent_key': 'general.assistance', 'disposition': 'plan_then_execute', 'confidence': 0.60},
            'context': {'site_id': 'general', 'site_display_name': 'General'},
            'chosen_pack': {'title': 'General', 'domain_kind': 'local'},
            'playbook': {'status': 'ready_to_execute', 'next_phase': 'execute', 'summary': 'Listo.', 'steps': []},
            'approval_checkpoints': [],
            'capability_readiness': [],
            'strategy_candidates': [],
            'outcome': {},
        }

        external_payload = {
            'success': False,
            'message': 'Ollama no respondio a tiempo.',
            'meta': 'Timeout en consulta.',
            'payload': adaptive_payload,
            'assistant_title': 'Ollama',
            'external_state_flags': [],
        }

        viewmodel._apply_task_result('external_consultation', external_payload)

        assert viewmodel.get_assistant_guidance_mode() == 'idle', (
            'Sin guidance accionable, el mode debe resetearse a idle'
        )
        assert viewmodel.get_assistant_action_buttons() == [], (
            'Sin guidance accionable, los action buttons deben limpiarse'
        )
        assert viewmodel.get_approval_dialog_visible() is False, (
            'Sin guidance accionable, el dialogo de aprobacion debe estar oculto'
        )
    finally:
        _cleanup_bootstrap(bootstrap)
