from __future__ import annotations

import shutil
from pathlib import Path

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import ExecutionState, ExperimentDomain, EvaluationRoute, TaskRole, ToolResult, ToolTask, ToolType, ToolValidationStatus
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter



def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = Path.cwd() / 'data' / name
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap



def _cleanup_bootstrap(bootstrap: AppBootstrap) -> None:
    workspace = getattr(bootstrap, '_test_workspace', None)
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)



def _make_codex_available(bootstrap: AppBootstrap) -> None:
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



def _make_chatgpt_available(bootstrap: AppBootstrap) -> None:
    fake_chatgpt = Path(bootstrap.config.workspace_root) / 'fake_chatgpt.exe'
    fake_chatgpt.write_text('stub', encoding='utf-8')
    card = bootstrap.tool_record_repository.get_card('chatgpt_installed')
    assert card is not None
    bootstrap.tool_record_repository.save_card(
        card.model_copy(
            update={
                'metadata': {
                    **card.metadata,
                    'executable_path': str(fake_chatgpt),
                    'command_name': '',
                    'command_aliases': [],
                    'windows_default_paths': [],
                    'dry_run_launch': True,
                }
            }
        )
    )


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


def test_autonomous_evolution_service_prepares_codex_consultation_for_bridge_lag() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_codex_workspace')
    try:
        _make_codex_available(bootstrap)
        payload = {
            'session_id': 'adaptive-wplay-autonomy',
            'intent': {
                'title': 'Abrir Wplay e iniciar sesion',
                'intent_key': 'wplay.login',
                'site_hint': 'wplay',
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
                'summary': 'La ensenanza existe pero el bridge no consolida bien el flujo.',
                'probable_cause': 'La cola visible drena tarde y deja pobre consolidacion semantica.',
            },
            'metadata': {},
        }

        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert result['status'] == 'awaiting_response'
        assert result['requested_assistant_kind'] == 'codex'
        assert result['selected_tool_id'] == 'codex_installed'
        assert result['manual_pasteback_required'] is False
        assert result['response_capture_pending'] is True
        assert result['pending_issue_id']
        issue = bootstrap.pending_issue_repository.get(result['pending_issue_id'])
        assert issue is not None
        assert issue.metadata['autonomous_evolution'] is True
        stored_results = [item for item in bootstrap.tool_record_repository.list_results(limit=10) if item.metadata.get('autonomous_consultation')]
        assert stored_results
        assert stored_results[0].metadata['autonomous_consultation']['decision_source'] == 'self_teach'
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_skips_external_consultation_for_retry_after_rebuild() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_noop_workspace')
    try:
        payload = {
            'session_id': 'adaptive-wplay-rebuild',
            'intent': {
                'title': 'Abrir Wplay e iniciar sesion',
                'intent_key': 'wplay.login',
                'site_hint': 'wplay',
            },
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'live_audit': {
                    'summary': 'La ensenanza existe pero conviene reconstruir aprendizaje antes de escalar.',
                    'decision_action': 'retry_after_rebuild',
                },
            },
            'probe_diagnosis': {
                'category': 'need_runtime_tuning',
                'summary': 'Primero conviene reintentar despues del rebuild.',
            },
            'metadata': {},
        }

        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert result['status'] == 'noop'
        assert result['recommended_action'] == 'retry_after_rebuild'
        assert bootstrap.pending_issue_repository.list_recent(limit=5) == []
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_preview_prefers_codex_for_bridge_lag() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_preview_workspace')
    try:
        _make_codex_available(bootstrap)
        payload = {
            'session_id': 'adaptive-wplay-preview',
            'intent': {
                'title': 'Abrir Wplay e iniciar sesion',
                'intent_key': 'wplay.login',
                'site_hint': 'wplay',
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
            'metadata': {},
        }

        preview = bootstrap.autonomous_evolution_service.preview_plan(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='manual_audit',
        )

        assert preview['status'] == 'preview'
        assert preview['should_consult'] is True
        assert preview['requested_assistant_kind'] == 'codex'
        assert preview['selected_tool_id'] == 'codex_installed'
        assert preview['available'] is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_autonomous_evolution_service_ingests_codex_response_and_updates_issue() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_ingest_codex_workspace')
    try:
        _make_codex_available(bootstrap)
        payload = {
            'session_id': 'adaptive-wplay-ingest',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {
                'category': 'need_codex_fix',
                'summary': 'La ensenanza existe pero el bridge no consolida bien el flujo.',
                'probable_cause': 'La cola visible drena tarde y deja pobre consolidacion semantica.',
            },
            'metadata': {},
        }
        prepared = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )
        payload['metadata'] = {'autonomous_evolution': dict(prepared)}
        bridge = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            response_text=(
                'Causa raiz probable: El bridge visible acumula eventos y checkpoints sin consolidarlos a tiempo.\n'
                'Cambio vertical recomendado: Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina.\n'
                'CodexTaskSpec sugerido:\n'
                '- file_scope: src/iabv_v15/services/capture/browser_teach_session_service.py, src/iabv_v15/ui/viewmodels/capture_studio_viewmodel.py\n'
                'Pruebas sugeridas: Captura con escritura rapida, Varias pestanas'
            ),
            source='clipboard',
        )

        assert bridge['status'] == 'ingested'
        assert bridge['next_action'] == 'prepare_codex_packet'
        assert bridge['response_validation']['status'] == 'review_needed'
        assert bridge['response_validation']['sandbox_required'] is True
        assert bridge['adoption_plan']['execution_lane'] == 'codex_packet'
        assert bridge['adoption_plan']['requires_human_approval'] is True
        issue = bootstrap.pending_issue_repository.get(bridge['pending_issue_id'])
        assert issue is not None
        assert 'Ajustar sondeo' in issue.recommended_change
        assert issue.metadata['external_consult_response']['adoption_plan']['execution_lane'] == 'codex_packet'
        results = bootstrap.tool_record_repository.list_results(task_id=prepared['task_id'], limit=5)
        assert results
        assert results[0].metadata['autonomous_consultation']['response_next_action'] == 'prepare_codex_packet'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_autonomous_evolution_service_ingests_chatgpt_response_as_teaching_gap() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_ingest_chatgpt_workspace')
    try:
        _make_chatgpt_available(bootstrap)
        payload = {
            'session_id': 'adaptive-wplay-chatgpt',
            'intent': {'title': 'Explica por que Wplay no queda aprendido', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'live_audit': {'summary': 'Hace falta una explicacion mas clara del hueco de ensenanza.', 'decision_action': 'consult_chatgpt'},
            },
            'probe_diagnosis': {'category': 'need_teaching', 'summary': 'Todavia falta una ensenanza mas clara.'},
            'metadata': {},
        }
        prepared = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='explica por que Wplay no queda aprendido',
            source='chat',
        )
        payload['metadata'] = {'autonomous_evolution': dict(prepared)}
        bridge = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='explica por que Wplay no queda aprendido',
            response_text='Causa raiz probable: La ensenanza todavia no describe con claridad el boton submit ni el momento exacto del login. Cambio vertical recomendado: Reensenar el flujo con capturas visibles mas limpias y menos ruido.',
            source='clipboard',
        )

        assert bridge['status'] == 'ingested'
        assert bridge['assistant_kind'] == 'chatgpt'
        assert bridge['next_action'] == 'open_teaching_studio'
        assert bridge['response_validation']['status'] == 'approved'
        assert bridge['adoption_plan']['execution_lane'] == 'teaching_replay'
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_marks_insufficient_response_for_reaudit() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_insufficient_response_workspace')
    try:
        _make_codex_available(bootstrap)
        payload = {
            'session_id': 'adaptive-wplay-insufficient',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Hace falta una respuesta tecnica mas concreta.'},
            'metadata': {},
        }
        prepared = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )
        payload['metadata'] = {'autonomous_evolution': dict(prepared)}

        bridge = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            response_text='No se, revisa eso.',
            source='clipboard',
        )

        assert bridge['status'] == 'captured'
        assert bridge['next_action'] == 'audit_autonomy'
        assert bridge['response_validation']['status'] == 'insufficient'
        assert bridge['adoption_plan']['execution_lane'] == 'audit_again'
        runs = bootstrap.experiment_lab_repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key='wplay:need_codex_fix', limit=5)
        assert runs
        assert runs[0].metadata['validation_status'] == 'insufficient'
        assert runs[0].metrics.total_score < 0.3
    finally:
        _cleanup_bootstrap(bootstrap)


def test_autonomous_evolution_service_marks_structured_quota_block_as_blocked_external() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_quota_block_workspace')
    try:
        payload = {
            'session_id': 'adaptive-wplay-quota-block',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El problema parece tecnico y repetido.'},
            'metadata': {},
        }

        def _fake_execute_external_consultation(**kwargs):
            task = ToolTask(
                tool_id='codex_installed',
                title='Consulta externa Codex',
                objective='abre Wplay e inicia sesion',
                requested_by_role=TaskRole.TOOL_USE,
                actions=[],
                metadata={
                    'assistant_kind': 'codex',
                    'actual_assistant_kind': 'codex',
                    'assistant_configuration': {},
                    'config_signature': 'cfg-codex',
                    'context_pack': 'consulta tecnica',
                },
            )
            result = ToolResult(
                task_id=task.task_id,
                tool_id='codex_installed',
                tool_type=ToolType.LLM_WEB_UI,
                success=True,
                validation_status=ToolValidationStatus.SANDBOX_PASS,
                execution_state=ExecutionState(
                    state='executed',
                    detail='La cuenta externa no tiene cuota disponible.',
                    metadata={
                        'assistant_kind': 'codex',
                        'launch_mode': 'desktop',
                        'response_capture_mode': 'browser_dom',
                        'launched': True,
                        'credits_exhausted': True,
                        'quota_status': 'exhausted',
                        'account_status': 'limited',
                    },
                ),
                output_text='La cuenta externa no tiene cuota disponible.',
                metadata={'assistant_kind': 'codex'},
            )
            return task, result, {'summary': 'Preview Codex'}

        bootstrap.tool_teach_service.execute_external_consultation = _fake_execute_external_consultation  # type: ignore[method-assign]

        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert result['status'] == 'blocked_external'
        assert 'account_limited' in result['external_state_flags']
        assert 'cuota disponible' in result['detail']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_autonomous_evolution_service_marks_browser_dom_unavailable_as_capture_unverified() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_browser_dom_unavailable_workspace')
    try:
        payload = {
            'session_id': 'adaptive-browser-dom-unavailable',
            'intent': {'title': 'Validar sesion web externa', 'intent_key': 'knowledge.query', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag', 'live_audit_action': 'consult_chatgpt'},
            },
            'metadata': {
                'decision_context': {
                    'governance': {'should_consult': True, 'assistant_kind': 'chatgpt', 'recommended_action': 'consult_chatgpt'},
                },
            },
        }
        task = ToolTask(
            tool_id='chatgpt_web_assisted',
            title='Consultar ChatGPT',
            objective='Validar sesion web externa',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={
                'assistant_kind': 'chatgpt',
                'requested_assistant_kind': 'chatgpt',
                'actual_assistant_kind': 'chatgpt',
                'response_capture_mode': 'dom_capture',
                'selected_tool_id': 'chatgpt_web_assisted',
            },
        )
        result = ToolResult(
            task_id=task.task_id,
            tool_id='chatgpt_web_assisted',
            tool_type=ToolType.LLM_WEB_UI,
            success=False,
            output_text='',
            error_message='browser_dom_unavailable',
            execution_state=ExecutionState(
                state='failed',
                detail='browser_dom_unavailable',
                metadata={
                    'assistant_kind': 'chatgpt',
                    'response_capture_mode': 'dom_capture',
                    'auto_capture_reason': 'browser_dom_unavailable',
                    'launched': False,
                    'response_captured': False,
                },
            ),
            metadata={'error_message': 'browser_dom_unavailable'},
        )

        consultation = {
            'assistant_kind': 'chatgpt',
            'requested_assistant_kind': 'chatgpt',
            'actual_assistant_kind': 'chatgpt',
            'selected_tool_id': 'chatgpt_web_assisted',
            'task_id': task.task_id,
            'result_id': result.result_id,
            'response_capture_mode': 'dom_capture',
        }

        flags = bootstrap.autonomous_evolution_service._consultation_external_state_flags(
            task=task,
            result=result,
            requested_assistant_kind='chatgpt',
            coherence_flags=[],
        )
        consultation['external_state_flags'] = flags

        assert 'capture_unverified' in flags
    finally:
        _cleanup_bootstrap(bootstrap)


def test_autonomous_evolution_service_auto_ingests_direct_response_from_external_tool() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_direct_auto_ingest_workspace')
    try:
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
        payload = {
            'session_id': 'adaptive-wplay-direct-auto-ingest',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El caso necesita una respuesta tecnica accionable.'},
            'metadata': {},
        }

        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert result['status'] == 'ingested'
        assert result['auto_response_ingested'] is True
        assert result['manual_pasteback_required'] is False
        assert result['next_action'] == 'prepare_codex_packet'
        assert result['response_validation']['status'] == 'review_needed'
        assert result['adoption_plan']['execution_lane'] == 'codex_packet'
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_can_fall_back_to_local_ollama_when_external_apps_are_unavailable() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_local_fallback_workspace')
    try:
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
        payload = {
            'session_id': 'adaptive-wplay-local-fallback',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El caso necesita una respuesta tecnica accionable.'},
            'metadata': {},
        }

        preview = bootstrap.autonomous_evolution_service.preview_plan(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )
        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert preview['selected_tool_id'] == 'ollama_llm'
        assert preview['actual_assistant_kind'] == 'ollama'
        assert result['status'] == 'ingested'
        assert result['selected_tool_id'] == 'ollama_llm'
        assert result['assistant_kind'] == 'ollama'
        assert result['auto_response_ingested'] is True
        assert result['manual_pasteback_required'] is False
        assert result['next_action'] == 'prepare_codex_packet'
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_reuses_successful_local_consultation_for_same_scope() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_reuses_local_scope_workspace')
    try:
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
        payload = {
            'session_id': 'adaptive-wplay-local-learning',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El caso necesita una respuesta tecnica accionable.'},
            'metadata': {},
        }

        first = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        _make_codex_available(bootstrap)
        preview = bootstrap.autonomous_evolution_service.preview_plan(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )
        recommendation = bootstrap.experiment_lab_repository.latest_recommendation(
            domain=ExperimentDomain.CODE.value,
            subject_key='wplay:need_codex_fix',
        )

        assert first['status'] == 'ingested'
        assert first['experiment_feedback']['route'] == EvaluationRoute.LOCAL.value
        assert first['experiment_feedback']['subject_key'] == 'wplay:need_codex_fix'
        assert recommendation is not None
        assert recommendation.recommended_route == EvaluationRoute.LOCAL
        assert preview['selected_tool_id'] == 'ollama_llm'
        assert preview['actual_assistant_kind'] == 'ollama'
    finally:
        _cleanup_bootstrap(bootstrap)





def test_autonomous_evolution_service_classifies_claude_routes_consistently() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_claude_routes_workspace')
    try:
        service = bootstrap.autonomous_evolution_service
        assert service._consultation_evaluation_route(
            assistant_kind='claude',
            consultation={'selected_tool_id': 'claude_web_assisted'},
        ) == EvaluationRoute.UI
        assert service._consultation_evaluation_route(
            assistant_kind='claude',
            consultation={'selected_tool_id': 'claude_installed'},
        ) == EvaluationRoute.LANGUAGE_UNDERSTANDING
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_rejects_unverified_clipboard_captured_codex_response() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_clipboard_capture_workspace')
    try:
        class _Runner:
            def __init__(self, workspace_root: str) -> None:
                self.workspace_root = workspace_root

            def capture_response_from_app(self, **kwargs) -> dict[str, object]:
                return {
                    'launched': True,
                    'focused_title': 'Codex',
                    'response_captured': True,
                    'captured_text': (
                        'Causa raiz probable: El bridge visible acumula eventos y checkpoints sin consolidarlos a tiempo. '
                        'Cambio vertical recomendado: Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina. '
                        'Pruebas sugeridas: Captura con escritura rapida'
                    ),
                    'error_message': '',
                }

        adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
        bootstrap.tool_adapters['external_assistant'] = adapter
        bootstrap.tool_registry.adapters['external_assistant'] = adapter
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
                        'response_capture_mode': 'clipboard_capture',
                        'requires_manual_pasteback': False,
                    }
                }
            )
        )
        refreshed = bootstrap.tool_record_repository.get_card('codex_installed')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)

        payload = {
            'session_id': 'adaptive-wplay-clipboard-capture',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El caso necesita una respuesta tecnica accionable.'},
            'metadata': {},
        }

        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert result['status'] == 'failed'
        assert result.get('auto_response_ingested') in {False, None}
        assert result['assistant_kind'] == 'codex'
        assert result['manual_pasteback_required'] is False
        assert result.get('response_validation') in ({}, None)
        assert result.get('adoption_plan') in ({}, None)
        assert 'capture_unverified' in result['external_state_flags']
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_service_auto_ingests_codex_rollout_capture() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_rollout_capture_workspace')
    try:
        class _Runner:
            def __init__(self, workspace_root: str) -> None:
                self.workspace_root = workspace_root

            def capture_response_from_app(self, **kwargs) -> dict[str, object]:
                return {
                    'launched': True,
                    'focused_title': 'Codex',
                    'response_captured': True,
                    'capture_source': 'session_rollout',
                    'thread_verified': True,
                    'used_fallback_capture': False,
                    'captured_text': (
                        'Causa raiz probable: El bridge visible acumula eventos y checkpoints sin consolidarlos a tiempo. '
                        'Cambio vertical recomendado: Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina. '
                        'Pruebas sugeridas: Captura con escritura rapida'
                    ),
                    'error_message': '',
                }

        adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
        bootstrap.tool_adapters['external_assistant'] = adapter
        bootstrap.tool_registry.adapters['external_assistant'] = adapter
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
                        'response_capture_mode': 'clipboard_capture',
                        'background_capture_mode': 'codex_rollout',
                        'requires_manual_pasteback': False,
                    }
                }
            )
        )
        refreshed = bootstrap.tool_record_repository.get_card('codex_installed')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)

        payload = {
            'session_id': 'adaptive-wplay-rollout-capture',
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'site_display_name': 'Wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'El caso necesita una respuesta tecnica accionable.'},
            'metadata': {},
        }

        result = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='abre Wplay e inicia sesion',
            source='self_teach',
        )

        assert result['status'] == 'ingested'
        assert result['auto_response_ingested'] is True
        assert result['auto_response_capture_mode'] == 'session_rollout'
        assert result['assistant_kind'] == 'codex'
        assert result['manual_pasteback_required'] is False
    finally:
        _cleanup_bootstrap(bootstrap)



def test_autonomous_evolution_context_pack_includes_query_id_marker() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_query_marker_workspace')
    try:
        payload = {
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {'site_id': 'wplay', 'live_audit': {'summary': 'Bridge lag persistente.'}},
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Hace falta contexto tecnico accionable.'},
            'metadata': {},
        }
        query = bootstrap.autonomous_evolution_service._build_incident_query(payload=payload, pending_issue_id='issue-123')
        context_pack = bootstrap.autonomous_evolution_service._build_context_pack(
            assistant_kind='codex',
            payload=payload,
            user_goal='abre Wplay e inicia sesion',
            pending_issue_id='issue-123',
            query=query,
        )

        assert 'Pending issue: issue-123' in context_pack
        assert 'IABV_QUERY_ID: issue-123' in context_pack
    finally:
        _cleanup_bootstrap(bootstrap)


def test_context_pack_injects_bridge_metrics_for_wplay_bridge_lag() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_bridge_metrics_workspace')
    try:
        payload = {
            'intent': {'title': 'Abrir Wplay e iniciar sesion', 'intent_key': 'wplay.login', 'site_hint': 'wplay'},
            'context': {
                'site_id': 'wplay',
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [
                    {
                        'incident_kind': 'bridge_lag',
                        'summary': 'La captura visible acumula retraso en el bridge.',
                        'probable_cause': 'La cola de eventos crecio o hubo ciclos sin progreso visible.',
                        'detail': 'Cola: 92 | ciclos sin progreso: 5',
                        'affected_url': 'https://www.wplay.co/casino',
                        'recent_urls': [
                            'https://www.wplay.co/login',
                            'https://www.wplay.co/',
                            'https://www.wplay.co/casino',
                        ],
                        'metadata': {'queue_depth': 92, 'poll_without_progress_count': 5},
                    }
                ],
                'live_audit': {'summary': 'Bridge lag persistente.'},
            },
            'probe_diagnosis': {'category': 'need_teaching', 'summary': 'Hace falta una ensenanza mas clara del hueco.'},
            'metadata': {},
        }
        query = bootstrap.autonomous_evolution_service._build_incident_query(
            payload=payload, pending_issue_id='issue-bridge-1'
        )
        context_pack = bootstrap.autonomous_evolution_service._build_context_pack(
            assistant_kind='chatgpt',
            payload=payload,
            user_goal='explica por que Wplay no queda aprendido',
            pending_issue_id='issue-bridge-1',
            query=query,
        )

        # Antes del fix, ninguno de estos valores llegaba al prompt externo:
        assert 'Metricas del incidente:' in context_pack
        assert 'queue_depth=92' in context_pack
        assert 'poll_without_progress_count=5' in context_pack
        assert 'URL afectada: https://www.wplay.co/casino' in context_pack
        assert 'URLs recientes:' in context_pack
        assert 'https://www.wplay.co/login' in context_pack
        assert 'Detalle del incidente: Cola: 92 | ciclos sin progreso: 5' in context_pack
        assert 'Causa probable registrada:' in context_pack
        # La linea de cierre del resumen sigue presente despues de las metricas:
        assert 'Si identificas que este caso ya requiere parche tecnico' in context_pack
    finally:
        _cleanup_bootstrap(bootstrap)


def test_context_pack_omits_incident_evidence_when_no_recent_incidents() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_no_incident_evidence_workspace')
    try:
        payload = {
            'intent': {'title': 'Consulta general', 'intent_key': 'research.external_consultation'},
            'context': {'site_id': '', 'recent_incidents': []},
            'probe_diagnosis': {'category': 'need_teaching', 'summary': 'Sin evidencia adicional.'},
            'metadata': {},
        }
        query = bootstrap.autonomous_evolution_service._build_incident_query(
            payload=payload, pending_issue_id='issue-empty'
        )
        context_pack = bootstrap.autonomous_evolution_service._build_context_pack(
            assistant_kind='chatgpt',
            payload=payload,
            user_goal='explicar caso generico',
            pending_issue_id='issue-empty',
            query=query,
        )

        # Sin incidentes -> no se inventan lineas de metricas ni urls
        assert 'Metricas del incidente:' not in context_pack
        assert 'URL afectada:' not in context_pack
        assert 'URLs recientes:' not in context_pack
        # Y el fallback de 'sin evidencia adicional' sigue funcionando
        assert 'sin evidencia adicional' in context_pack
    finally:
        _cleanup_bootstrap(bootstrap)


def test_autonomous_evolution_service_respects_explicit_chatgpt_family_under_technical_pressure() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_explicit_chatgpt_family_workspace')
    try:
        _disable_external_assistant_apps(bootstrap)
        web_card = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert web_card is not None
        bootstrap.tool_record_repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'dry_run_launch': True}}))
        refreshed = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)
        _make_codex_available(bootstrap)

        payload = {
            'session_id': 'adaptive-explicit-chatgpt-family',
            'intent': {
                'title': 'Consulta externa dirigida a ChatGPT',
                'intent_key': 'research.external_consultation',
                'site_hint': 'wplay',
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
                'summary': 'La evidencia tecnica existe, pero el usuario pidio otra IA.',
            },
            'metadata': {},
        }

        preview = bootstrap.autonomous_evolution_service.preview_plan(
            adaptive_payload=payload,
            user_goal='Necesito una consulta externa con ChatGPT para revisar el objetivo activo.',
            source='chat',
            decision_context={
                'governance': {
                    'should_consult': True,
                    'assistant_kind': 'chatgpt',
                    'recommended_action': 'consult_chatgpt',
                    'reason': 'El usuario pidio ChatGPT de forma explicita.',
                    'diagnostic_category': 'explicit_external_consultation',
                }
            },
        )

        assert preview['requested_assistant_kind'] == 'chatgpt'
        assert preview['selected_tool_id'] == 'chatgpt_web_assisted'
        assert 'Asistente elegido: chatgpt' in preview['context_pack_excerpt']
        assert 'IABV Codex' not in preview['context_pack_excerpt']
    finally:
        _cleanup_bootstrap(bootstrap)


class _FakeClarificationService:
    """Doble minimo del ClarificationRequestService para tests de PR-C.

    No toca threading; registra la pregunta recibida y devuelve la respuesta
    canned configurada en el constructor. Si `raise_exc` esta seteado, lo
    lanza en ask() para simular timeout/cancelacion.
    """

    def __init__(self, *, answer: str | None = None, raise_exc: Exception | None = None) -> None:
        self._answer = answer
        self._raise_exc = raise_exc
        self.asked: list[dict[str, object]] = []

    def ask(self, *, question: str, options=None, context=None, timeout_s=None):
        self.asked.append(
            {
                'question': question,
                'options': list(options or []),
                'context': context or '',
                'timeout_s': timeout_s,
            }
        )
        if self._raise_exc is not None:
            raise self._raise_exc
        return str(self._answer or '')


def _permission_required_decision_context(*, assistant_kind: str = 'chatgpt') -> dict[str, object]:
    return {
        'governance': {
            'should_consult': False,
            'assistant_kind': assistant_kind,
            'recommended_action': 'request_observation_permission',
            'reason': 'Necesito permiso explicito para observar la ventana visible.',
            'diagnostic_category': 'observation_permission_required',
        },
        'metadata': {},
    }


def test_plan_or_execute_requests_observation_permission_and_returns_noop_when_user_denies() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_permission_denied_workspace')
    try:
        service = bootstrap.autonomous_evolution_service
        fake = _FakeClarificationService(answer='No autorizo')
        service.clarification_request_service = fake

        result = service.plan_or_execute(
            adaptive_payload={'session_id': 'adaptive-perm-1', 'metadata': {}},
            user_goal='revisa este problema tecnico',
            source='self_teach',
            decision_context=_permission_required_decision_context(),
        )

        assert result['status'] == 'noop'
        assert result['recommended_action'] == 'request_observation_permission'
        assert 'no aprobo' in result['reason'].lower() or 'denegada' in result['reason'].lower() or 'chatgpt' in result['reason'].lower()
        # Se le pregunto al usuario exactamente una vez, via clarification service.
        assert len(fake.asked) == 1
        assert 'chatgpt' in str(fake.asked[0]['question']).lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_plan_or_execute_returns_noop_when_user_permission_times_out() -> None:
    bootstrap = _make_bootstrap('test_autonomous_evolution_permission_timeout_workspace')
    try:
        from iabv_v15.services.ux.clarification_request_service import ClarificationTimeoutError

        service = bootstrap.autonomous_evolution_service
        fake = _FakeClarificationService(raise_exc=ClarificationTimeoutError('timeout'))
        service.clarification_request_service = fake

        result = service.plan_or_execute(
            adaptive_payload={'session_id': 'adaptive-perm-2', 'metadata': {}},
            user_goal='revisa otro problema',
            source='self_teach',
            decision_context=_permission_required_decision_context(),
        )

        assert result['status'] == 'noop'
        # El gate sigue cerrado despues de un timeout.
        assert result['recommended_action'] == 'request_observation_permission'
        assert len(fake.asked) == 1
    finally:
        _cleanup_bootstrap(bootstrap)


def test_plan_or_execute_without_clarification_service_keeps_legacy_noop_for_observation_gate() -> None:
    """Cuando el servicio no esta cableado (tests legacy o bootstrap parcial),
    el flujo se comporta igual que antes: devuelve noop con el action del gate,
    sin intentar preguntar."""
    bootstrap = _make_bootstrap('test_autonomous_evolution_permission_no_service_workspace')
    try:
        service = bootstrap.autonomous_evolution_service
        service.clarification_request_service = None

        result = service.plan_or_execute(
            adaptive_payload={'session_id': 'adaptive-perm-3', 'metadata': {}},
            user_goal='revisa otro problema mas',
            source='self_teach',
            decision_context=_permission_required_decision_context(),
        )

        assert result['status'] == 'noop'
        assert result['recommended_action'] == 'request_observation_permission'
    finally:
        _cleanup_bootstrap(bootstrap)


def test_request_observation_permission_helper_flags_approval_from_affirmative_answer() -> None:
    """Cubrimos el helper directamente: respuestas afirmativas se interpretan
    como aprobacion, sin importar mayusculas o espacios."""
    bootstrap = _make_bootstrap('test_autonomous_evolution_permission_helper_workspace')
    try:
        service = bootstrap.autonomous_evolution_service
        assessment = {
            'should_consult': False,
            'assistant_kind': 'chatgpt',
            'action': 'request_observation_permission',
            'reason': 'Necesito permiso.',
            'diagnostic_category': 'observation_permission_required',
        }
        payload = {'session_id': 'adaptive-perm-4', 'metadata': {}}

        for answer in ('Si', ' si ', 'Autorizo', 'Apruebo', 'OK', 'yes'):
            service.clarification_request_service = _FakeClarificationService(answer=answer)
            outcome = service._request_observation_permission(
                assessment=assessment, payload=payload, user_goal='alguna consulta',
            )
            assert outcome['attempted'] is True, f'Answer {answer!r} should count as attempt'
            assert outcome['approved'] is True, f'Answer {answer!r} should count as approval'

        for answer in ('No', 'no autorizo', 'cancelar', ''):
            service.clarification_request_service = _FakeClarificationService(answer=answer)
            outcome = service._request_observation_permission(
                assessment=assessment, payload=payload, user_goal='alguna consulta',
            )
            assert outcome['attempted'] is True
            assert outcome['approved'] is False, f'Answer {answer!r} should NOT count as approval'

        # Regresion para Devin Review #15: la puntuacion en el primer token
        # no debe bypasear el chequeo de negacion. "No, autorizo" tiene
        # 'no,' como primer token; sin strip, el frozenset no lo reconoce
        # y se interpretaba como aprobacion. Tambien validamos que un
        # sufijo de puntuacion no rompa el match del set de aprobaciones.
        for denied_answer in ('No, autorizo', 'No. Autorizo nada', 'no! autorizo', 'Cancelar.'):
            service.clarification_request_service = _FakeClarificationService(answer=denied_answer)
            outcome = service._request_observation_permission(
                assessment=assessment, payload=payload, user_goal='consulta con puntuacion',
            )
            assert outcome['approved'] is False, (
                f'Answer {denied_answer!r} should NOT count as approval: '
                'punctuation must not bypass denial prefix.'
            )

        for approved_answer in ('Autorizo.', 'Apruebo!', 'Si,', '¿Si?', 'Ok,'):
            service.clarification_request_service = _FakeClarificationService(answer=approved_answer)
            outcome = service._request_observation_permission(
                assessment=assessment, payload=payload, user_goal='consulta con puntuacion',
            )
            assert outcome['approved'] is True, (
                f'Answer {approved_answer!r} should count as approval even with trailing punctuation.'
            )

        # Sin servicio no se llega a consultar.
        service.clarification_request_service = None
        outcome = service._request_observation_permission(
            assessment=assessment, payload=payload, user_goal='alguna consulta',
        )
        assert outcome == {'attempted': False, 'approved': False, 'detail': '', 'raw_response': ''}
    finally:
        _cleanup_bootstrap(bootstrap)



def test_ensure_pending_issue_drops_live_audit_summary_from_text_fallbacks() -> None:
    """Regression H3: LiveAudit summary must not leak into CodexPendingIssue fields.

    When `probe_diagnosis` is empty and the caller-provided `reason` is actually
    a LiveAudit summary (shape "{lead} Decision: {action}. Confianza 0.NN.")
    the backlog used to record that same string as summary, probable_cause and
    recommended_change at once, producing three identical non-actionable lines.
    The fix sanitizes `reason` before using it as text fallback so summary
    lands on the generic placeholder and the other fields stay empty.
    """
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_h3_workspace')
    try:
        service = bootstrap.autonomous_evolution_service
        payload = {
            'session_id': 'adaptive-h3',
            'probe_diagnosis': {},
            'context': {'live_audit': {'audit_snapshot_id': 'snap-h3'}},
            'metadata': {},
        }
        issue = service._ensure_pending_issue(
            payload=payload,
            user_goal='sesion de prueba h3',
            assistant_kind='codex',
            source='self_teach',
            reason='Sin hallazgos. Decision: continue_local. Confianza 0.66.',
        )
        assert issue is not None
        # The live-audit-shaped reason must NOT leak into any Codex text field.
        assert 'Confianza 0.66' not in issue.summary
        assert 'Confianza 0.66' not in issue.probable_cause
        assert 'Confianza 0.66' not in issue.recommended_change
        assert 'Confianza 0.66' not in issue.unresolved_reason
        # Summary falls back to the generic placeholder so Codex sees a clear
        # "no diagnostico" marker instead of an operational audit line.
        assert issue.summary == 'Consulta evolutiva autonoma requerida.'
        # Fields that had no real diagnosis must stay empty instead of
        # duplicating the summary, so the three-identical-lines pattern is
        # gone.
        assert issue.probable_cause == ''
        assert issue.recommended_change == ''
        assert issue.unresolved_reason == ''
        # Live audit context is still preserved via evidence_refs so Codex can
        # pull the full snapshot when triaging the backlog.
        assert 'snap-h3' in issue.evidence_refs
    finally:
        _cleanup_bootstrap(bootstrap)



def test_ensure_pending_issue_preserves_real_diagnosis_and_reason() -> None:
    """H3 guard does not regress non-live-audit reasons.

    A `reason` that is a legitimate technical description must still flow into
    the text fallbacks when the diagnosis omits individual fields. Only the
    LiveAudit summary shape is stripped.
    """
    bootstrap = _make_bootstrap('test_autonomous_evolution_service_h3_positive_workspace')
    try:
        service = bootstrap.autonomous_evolution_service
        payload = {
            'session_id': 'adaptive-h3-positive',
            'probe_diagnosis': {
                'category': 'need_codex_fix',
                'summary': 'El bridge deja la cola visible a medias.',
            },
            'metadata': {},
        }
        issue = service._ensure_pending_issue(
            payload=payload,
            user_goal='sesion de prueba h3 positive',
            assistant_kind='codex',
            source='self_teach',
            reason='El render queda congelado al reabrir la pestana.',
        )
        assert issue is not None
        assert issue.summary == 'El bridge deja la cola visible a medias.'
        # probable_cause is taken from the caller-provided reason because it
        # does not match the LiveAudit pattern.
        assert issue.probable_cause == 'El render queda congelado al reabrir la pestana.'
        assert issue.recommended_change == 'El render queda congelado al reabrir la pestana.'
    finally:
        _cleanup_bootstrap(bootstrap)
