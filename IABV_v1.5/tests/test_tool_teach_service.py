from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import EvaluationRoute, ExecutionState, ExperimentDomain, ExperimentRecommendation, InferenceRequest, InteractionMode, ModeSelectionDecision, TaskRole, ToolAction, ToolActionType, ToolCard, ToolResult, ToolTask, ToolType, ToolValidationStatus
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter, ShellToolAdapter
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_validator import ToolValidator


class FakeToolAdapter:
    def __init__(self, tool_type: ToolType, *, available: bool = True, fail_execute: bool = False) -> None:
        self.tool_type = tool_type
        self.available = available
        self.fail_execute = fail_execute

    def is_available(self, card: ToolCard) -> bool:
        return self.available

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        if not sandbox and self.fail_execute and not task.metadata.get('rollback_origin_result_id'):
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {'action_count': len(task.actions)},
                'artifacts': [],
                'error_message': f'{card.tool_id}:failed',
                'execution_ms': 5,
                'metadata': {'sandbox': sandbox, 'tool_id': card.tool_id},
            }
        stage = 'rollback' if task.metadata.get('rollback_origin_result_id') else 'sandbox' if sandbox else 'executed'
        return {
            'success': True,
            'output_text': f'{card.tool_id}:{stage}',
            'extracted_data': {'action_count': len(task.actions)},
            'artifacts': [],
            'error_message': '',
            'execution_ms': 5,
            'metadata': {'sandbox': sandbox, 'tool_id': card.tool_id},
        }


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _service(root: Path, *, fail_shell_execute: bool = False, external_adapter: ExternalAssistantToolAdapter | None = None) -> tuple[ToolTeachService, ToolRecordRepository]:
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    repository = ToolRecordRepository(db, storage)
    adapters = {
        'playwright': FakeToolAdapter(ToolType.BROWSER),
        'shell': FakeToolAdapter(ToolType.SHELL, fail_execute=fail_shell_execute),
        'aider': FakeToolAdapter(ToolType.CODE_EDITOR),
        'external_assistant': external_adapter or ExternalAssistantToolAdapter(),
    }
    registry = ToolRegistry(repository, adapters)
    validator = ToolValidator()
    sandbox = ToolSandbox(validator)
    interaction_learning_service = InteractionLearningService(repository)
    mode_selector = InteractionModeSelector(registry, repository)
    memory = ToolMemory(repository, interaction_learning_service)
    memory = ToolMemory(repository, interaction_learning_service)
    experiment_lab_repository = ExperimentLabRepository(db, storage)
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(),
    )
    approval_policy = ToolApprovalPolicy()
    rollback_manager = ToolRollbackManager()
    service = ToolTeachService(
        registry=registry,
        memory=memory,
        sandbox=sandbox,
        validator=validator,
        approval_policy=approval_policy,
        rollback_manager=rollback_manager,
        adapters=adapters,
        workspace_root=str(root),
        interaction_learning_service=interaction_learning_service,
        mode_selector=mode_selector,
        experiment_lab=experiment_lab,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=repository, experiment_lab=experiment_lab),
    )
    return service, repository
    return service, repository


def test_tool_teach_service_preserves_tool_sandbox_route_and_executes_read_only() -> None:
    root = _workspace('tool_teach_service_read_only')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        request = InferenceRequest(
            user_goal='Valida esta herramienta shell en sandbox',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )

        route, result = service.handle(request)
        task = service.build_task_from_request(request)
        execution = service.execute_task(task, approved=False)
        stored_results = repository.list_results(task_id=task.task_id, limit=10)

        assert route.task_role == TaskRole.TOOL_SANDBOX
        assert result.detected_role == TaskRole.TOOL_SANDBOX
        assert result.raw_output['tool_preview']['available'] is True
        assert execution.success is True
        assert execution.execution_state.state == 'executed'
        assert execution.validation_status.value == 'approved'
        assert execution.metadata['interaction_pattern_id']
        assert execution.metadata['interaction_episode_id']
        assert execution.metadata['live_audit']['decision']['action'] == 'continue_local'
        stored_episodes = repository.list_interaction_episodes(limit=10)
        matching_episode = next(item for item in stored_episodes if item.task_id == task.task_id)
        assert matching_episode.metadata['live_audit']['decision']['action'] == 'continue_local'
        assert len(stored_results) == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_requires_approval_for_code_editing() -> None:
    root = _workspace('tool_teach_service_write')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        request = InferenceRequest(
            user_goal='Edita codigo con aider para ajustar el router',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={'tool_id': 'aider_coder', 'execution_scope': 'write'},
        )

        task = service.build_task_from_request(request)
        waiting = service.execute_task(task, approved=False)
        executed = service.execute_task(task, approved=True)
        history = repository.list_results(task_id=task.task_id, limit=10)

        assert waiting.success is True
        assert waiting.execution_state.state == 'waiting_approval'
        assert waiting.execution_state.approval_decision.value == 'pending'
        assert waiting.metadata['live_audit']['decision']['action'] == 'stop_and_wait_user'
        assert executed.success is True
        assert executed.execution_state.state == 'executed'
        assert executed.execution_state.approval_decision.value == 'approved'
        assert len(history) == 3
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_attempts_basic_rollback_on_failed_write() -> None:
    root = _workspace('tool_teach_service_rollback')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root, fail_shell_execute=True)
        request = InferenceRequest(
            user_goal='Ejecuta un comando local con rollback',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'tool_id': 'shell_command',
                'execution_scope': 'write',
                'command': 'echo write',
                'rollback_command': 'echo rollback',
            },
        )

        task = service.build_task_from_request(request)
        result = service.execute_task(task, approved=True)
        history = repository.list_results(task_id=task.task_id, limit=10)

        assert result.success is False
        assert result.execution_state.state == 'failed'
        assert result.rollback_state is not None
        assert result.rollback_state.state == 'rolled_back'
        assert 'Rollback ejecutado correctamente' in result.rollback_state.detail
        assert len(history) == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_tool_teach_service_preview_surfaces_reusable_interaction_patterns() -> None:
    root = _workspace('tool_teach_service_patterns')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, _ = _service(root)
        request = InferenceRequest(
            user_goal='Abre una pagina local con playwright y toma una captura',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'tool_id': 'playwright_browser',
                'execution_scope': 'read_only',
                'url': 'https://example.com/demo',
            },
        )

        task = service.build_task_from_request(request)
        service.execute_task(task, approved=True)
        preview = service.preview_request(request)
        rebuilt_task = service.build_task_from_request(request)

        assert preview['available'] is True
        assert len(preview['interaction_patterns']) == 1
        assert preview['interaction_patterns'][0]['channel'] == 'ui'
        assert preview['mode_selection']['selected_mode'] == 'ui'
        assert preview['mode_selection']['equivalent_pattern_exists'] is True
        assert preview['mode_selection']['already_resolved'] is True
        assert rebuilt_task.metadata['reuse_guard_active'] is True
        assert rebuilt_task.metadata['reused_actions_from_pattern'] is True
        assert rebuilt_task.actions[0].metadata['reused_from_pattern'] is True
        assert 'patron' in preview['summary'].lower()
        assert 'reensenar' in preview['summary'].lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_logs_adapter_missing_as_audit_event() -> None:
    root = _workspace('tool_teach_service_adapter_missing')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        service.adapters.pop('shell', None)
        task = ToolTask(
            tool_id='shell_command',
            title='Shell sin adaptador',
            objective='Ejecutar shell sin adaptador disponible.',
            requested_by_role=TaskRole.TOOL_USE,
            execution_scope='read_only',
        )

        result = service.execute_task(task, approved=False)
        log = repository.list_log(task_id=task.task_id, limit=10)

        assert result.success is False
        assert result.execution_state.state == 'adapter_missing'
        assert any(item['state'] == 'adapter_missing' and item['action_type'] == 'preflight' for item in log)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_blocks_destructive_shell_commands_and_keeps_audit_trail() -> None:
    root = _workspace('tool_teach_service_destructive_block')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        real_shell = ShellToolAdapter()
        service.adapters['shell'] = real_shell
        service.registry.adapters['shell'] = real_shell
        task = ToolTask(
            tool_id='shell_command',
            title='Bloqueo destructivo',
            objective='Ejecuta un comando destructivo local',
            requested_by_role=TaskRole.TOOL_USE,
            actions=[
                ToolAction(
                    action_type=ToolActionType.RUN_COMMAND,
                    label='Bloqueado',
                    value='Remove-Item -LiteralPath C:\\Temp\\algo.txt -Force',
                )
            ],
            execution_scope='destructive',
        )
        result = service.execute_task(task, approved=True)
        history = repository.list_results(task_id=task.task_id, limit=10)
        log = repository.list_log(task_id=task.task_id, limit=10)

        assert result.success is False
        assert result.validation_status.value == 'blocked'
        assert result.execution_state.state == 'blocked'
        assert result.execution_state.destructive_blocked is True
        assert result.rollback_state is None
        assert len(history) == 1
        assert any(item['state'] == 'blocked' and item['action_type'] == 'task_result' for item in log)
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_tool_teach_service_external_consultation_prefers_codex_for_bridge_lag() -> None:
    root = _workspace('tool_teach_service_external_codex')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        fake_codex = root / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'dry_run_launch': True,
                    }
                }
            )
        )

        preview = service.preview_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            launch_dry_run=True,
        )
        task, result, _ = service.execute_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            approved=True,
            launch_dry_run=True,
        )

        assert preview['tool_card']['tool_id'] == 'codex_installed'
        assert preview['mode_selection']['selected_tool_id'] == 'codex_installed'
        assert task.metadata['consultation_scope'] == 'external_assistant'
        assert task.metadata['assistant_kind'] == 'codex'
        assert result.success is True
        assert result.execution_state.state == 'awaiting_response'
        assert result.validation_status.value == 'unvalidated'
        assert result.execution_state.metadata['assistant_kind'] == 'codex'
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert result.execution_state.metadata['response_capture_pending'] is True
        assert result.metadata['interaction_episode_id']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_consultation_supports_direct_text_capture() -> None:
    root = _workspace('tool_teach_service_external_direct_capture')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
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

        preview = service.preview_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            launch_dry_run=True,
        )
        _, result, _ = service.execute_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            approved=True,
            launch_dry_run=True,
        )

        assert preview['available'] is True
        assert 'pegado manual' not in preview['summary'].lower()
        assert result.success is True
        assert result.output_text.startswith('Causa raiz probable:')
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert result.execution_state.metadata['response_captured'] is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_consultation_falls_back_to_web_when_desktop_is_missing() -> None:
    root = _workspace('tool_teach_service_external_web_fallback')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        for tool_id in ('codex_installed', 'chatgpt_installed'):
            card = repository.get_card(tool_id)
            assert card is not None
            repository.save_card(
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
        for tool_id in ('chatgpt_web_assisted', 'claude_web_assisted'):
            web_card = repository.get_card(tool_id)
            assert web_card is not None
            repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'dry_run_launch': True}}))

        preview = service.preview_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            launch_dry_run=True,
        )
        task, result, _ = service.execute_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            approved=True,
            launch_dry_run=True,
        )

        assert preview['tool_card']['tool_id'] in {'chatgpt_web_assisted', 'claude_web_assisted'}
        assert preview['mode_selection']['selected_tool_id'] in {'chatgpt_web_assisted', 'claude_web_assisted'}
        assert preview['mode_selection']['fallback_used'] is True
        assert task.tool_id in {'chatgpt_web_assisted', 'claude_web_assisted'}
        assert result.success is True
        assert result.execution_state.state == 'awaiting_response'
        assert result.validation_status.value == 'unvalidated'
        assert result.execution_state.metadata['launch_mode'] == 'web_assisted'
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert result.execution_state.metadata['response_capture_pending'] is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_sandbox_honors_explicit_requested_tool_id() -> None:
    root = _workspace('tool_teach_service_explicit_sandbox_tool')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        fake_codex = root / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'dry_run_launch': True,
                    }
                }
            )
        )
        request = InferenceRequest(
            user_goal='Validar en sandbox la herramienta Codex instalado',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={'tool_id': 'codex_installed', 'execution_scope': 'read_only'},
        )

        task = service.build_task_from_request(request)
        result = service.execute_task(task, approved=False)

        assert task.tool_id == 'codex_installed'
        assert task.metadata['requested_tool_id'] == 'codex_installed'
        assert task.metadata['mode_selection']['selected_tool_id'] == 'codex_installed'
        assert result.tool_id == 'codex_installed'
        assert result.execution_state.executor_name == 'external_assistant'
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_tool_teach_service_external_consultation_can_fall_back_to_local_ollama_when_enabled() -> None:
    root = _workspace('tool_teach_service_external_local_fallback')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)

        class LocalAutomaticConsultationAdapter:
            tool_type = ToolType.LLM_LOCAL

            def is_available(self, card: ToolCard) -> bool:
                return True

            def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
                return {
                    'success': True,
                    'output_text': (
                        'Causa raiz probable: El bridge visible sigue saturado. '
                        'Cambio vertical recomendado: Ajustar sondeo y drenado sin bloquear la pagina. '
                        'file_scope: src/iabv_v15/services/capture/browser_teach_session_service.py '
                        'Pruebas sugeridas: Captura con escritura rapida'
                    ),
                    'extracted_data': {'provider': 'Ollama'},
                    'artifacts': [],
                    'error_message': '',
                    'execution_ms': 5,
                    'metadata': {
                        'sandbox': sandbox,
                        'assistant_kind': 'ollama',
                        'launch_mode': 'local_provider',
                        'response_capture_mode': 'tool_result',
                        'manual_pasteback_required': False,
                        'response_captured': True,
                    },
                }

        adapter = LocalAutomaticConsultationAdapter()
        service.adapters['ollama'] = adapter
        service.registry.adapters['ollama'] = adapter
        ollama = repository.get_card('ollama_llm')
        assert ollama is not None
        repository.save_card(
            ollama.model_copy(
                update={
                    'metadata': {
                        **ollama.metadata,
                        'assistant_kind': 'ollama',
                        'launch_mode': 'local_provider',
                        'response_capture_mode': 'tool_result',
                        'requires_manual_pasteback': False,
                    }
                }
            )
        )
        service.registry.refresh_card(repository.get_card('ollama_llm'))
        for tool_id in ('codex_installed', 'chatgpt_installed'):
            card = repository.get_card(tool_id)
            assert card is not None
            repository.save_card(
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
        web_card = repository.get_card('chatgpt_web_assisted')
        assert web_card is not None
        repository.save_card(web_card.model_copy(update={'metadata': {**web_card.metadata, 'web_url': ''}}))

        preview = service.preview_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            launch_dry_run=True,
            allow_local_automatic_consultation=True,
        )
        task, result, _ = service.execute_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            approved=True,
            launch_dry_run=True,
            allow_local_automatic_consultation=True,
        )

        assert preview['tool_card']['tool_id'] == 'ollama_llm'
        assert preview['tool_card']['metadata']['assistant_kind'] == 'ollama'
        assert task.tool_id == 'ollama_llm'
        assert result.tool_id == 'ollama_llm'
        assert result.success is True
        assert result.execution_state.metadata['assistant_kind'] == 'ollama'
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert 'captura automatica' in preview['summary'].lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)

def test_tool_teach_service_external_consultation_prefers_goal_scoped_lab_recommendation() -> None:
    root = _workspace('tool_teach_service_external_goal_scope')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, _ = _service(root)
        assert service.experiment_lab is not None
        service.experiment_lab.repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.LANGUAGE,
                subject_key='general:chatgpt',
                recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                score=0.62,
                confidence=0.66,
                rationale='El fallback general aun prefiere ChatGPT desktop.',
            )
        )
        service.experiment_lab.repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.LANGUAGE,
                subject_key='task-123:chatgpt',
                recommended_route=EvaluationRoute.LOCAL,
                score=0.91,
                confidence=0.88,
                rationale='Para esta tarea ya conviene consulta local automatica por el objetivo activo.',
            )
        )

        preview = service.preview_external_consultation(
            user_goal='resume el estado del objetivo activo',
            assistant_preference='chatgpt',
            context_pack='Objetivo activo: validar progreso longitudinal.',
            allow_local_automatic_consultation=True,
            goal_parameters={'task_id': 'task-123', 'objective_id': 'objective-1'},
        )

        assert preview['tool_task']['metadata']['lab_recommendation']['subject_key'] == 'task-123:chatgpt'
        assert preview['tool_task']['metadata']['requested_tool_id'] == 'ollama_llm'
    finally:
        shutil.rmtree(root, ignore_errors=True)




def test_tool_teach_service_external_consultation_supports_claude_preference() -> None:
    root = _workspace('tool_teach_service_external_claude')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        fake_claude = root / 'fake_claude.exe'
        fake_claude.write_text('stub', encoding='utf-8')
        claude = repository.get_card('claude_installed')
        assert claude is not None
        repository.save_card(
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
        refreshed = repository.get_card('claude_installed')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        preview = service.preview_external_consultation(
            user_goal='explica el bloqueo del objetivo activo',
            assistant_preference='claude',
            context_pack='Objetivo activo: consolidar autonomia local-first.',
            site_id='wplay',
            diagnostic_category='need_teaching',
            incident_kind='',
            launch_dry_run=True,
        )
        task, result, _ = service.execute_external_consultation(
            user_goal='explica el bloqueo del objetivo activo',
            assistant_preference='claude',
            context_pack='Objetivo activo: consolidar autonomia local-first.',
            site_id='wplay',
            diagnostic_category='need_teaching',
            incident_kind='',
            approved=True,
            launch_dry_run=True,
        )

        assert preview['tool_card']['tool_id'] == 'claude_web_assisted'
        assert preview['mode_selection']['selected_tool_id'] == 'claude_web_assisted'
        assert task.metadata['assistant_kind'] == 'claude'
        assert result.success is True
        assert result.execution_state.state == 'awaiting_response'
        assert result.execution_state.metadata['assistant_kind'] == 'claude'
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert result.execution_state.metadata['response_capture_pending'] is True
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_tool_teach_service_claude_preference_stays_in_claude_family_when_desktop_is_missing() -> None:
    root = _workspace('tool_teach_service_claude_family_fallback')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        claude = repository.get_card('claude_installed')
        assert claude is not None
        repository.save_card(
            claude.model_copy(
                update={
                    'metadata': {
                        **claude.metadata,
                        'executable_path': '',
                        'command_name': 'definitely_missing_external_app',
                        'command_aliases': [],
                        'windows_default_paths': [],
                    }
                }
            )
        )
        claude_web = repository.get_card('claude_web_assisted')
        assert claude_web is not None
        repository.save_card(claude_web.model_copy(update={'metadata': {**claude_web.metadata, 'dry_run_launch': True}}))

        preview = service.preview_external_consultation(
            user_goal='explica el bloqueo del objetivo activo',
            assistant_preference='claude',
            context_pack='Objetivo activo: consolidar autonomia local-first.',
            site_id='wplay',
            diagnostic_category='need_teaching',
            incident_kind='',
            launch_dry_run=True,
        )

        assert preview['tool_card']['tool_id'] == 'claude_web_assisted'
        assert preview['mode_selection']['selected_tool_id'] == 'claude_web_assisted'
        assert preview['tool_task']['metadata']['goal_parameters']['allowed_tool_ids'] == ['claude_installed', 'claude_web_assisted']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_consultation_rejects_unverified_codex_clipboard_capture() -> None:
    root = _workspace('tool_teach_service_external_clipboard_capture')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
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
                        'Causa raiz probable: El bridge visible sigue saturado. '
                        'Cambio vertical recomendado: Ajustar sondeo y drenado sin bloquear la pagina.'
                    ),
                    'error_message': '',
                }

        service, repository = _service(
            root,
            external_adapter=ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root)),
        )
        fake_codex = root / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
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
        refreshed = repository.get_card('codex_installed')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        _, result, preview = service.execute_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            approved=True,
            launch_dry_run=False,
        )

        assert 'capturar la respuesta automaticamente' in preview['summary'].lower()
        assert result.success is False
        assert result.execution_state.state == 'failed'
        assert result.validation_status.value == 'unvalidated'
        assert result.execution_state.metadata['response_capture_mode'] == 'clipboard_capture'
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert result.execution_state.metadata['response_captured'] is False
        assert result.execution_state.metadata['capture_unverified'] is True
        assert 'capture_unverified' in result.metadata['external_state_flags']
        assert result.output_text == ''
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_rejects_unverified_codex_rollout_capture_as_wrong_thread() -> None:
    root = _workspace('tool_teach_service_external_unverified_rollout')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        class _Runner:
            def __init__(self, workspace_root: str) -> None:
                self.workspace_root = workspace_root

            def capture_response_from_app(self, **kwargs) -> dict[str, object]:
                return {
                    'launched': True,
                    'focused_title': 'Codex',
                    'response_captured': True,
                    'captured_text': 'Texto ajeno capturado desde un rollout no verificado.',
                    'capture_source': 'session_rollout',
                    'thread_verified': False,
                    'used_fallback_capture': True,
                    'rollout_path': str(Path(self.workspace_root) / 'fallback-rollout.jsonl'),
                    'error_message': '',
                }

        service, repository = _service(
            root,
            external_adapter=ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root)),
        )
        fake_codex = root / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
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
        refreshed = repository.get_card('codex_installed')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        _, result, _ = service.execute_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            approved=True,
            launch_dry_run=False,
        )

        assert result.success is False
        assert result.error_message == 'wrong_thread'
        assert result.execution_state.state == 'failed'
        assert result.execution_state.metadata['thread_mismatch'] is True
        assert result.execution_state.metadata['capture_unverified'] is True
        assert 'wrong_thread' in result.metadata['external_state_flags']
        assert 'capture_unverified' in result.metadata['external_state_flags']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_consultation_prefers_desktop_codex_over_learned_web_pattern() -> None:
    root = _workspace('tool_teach_service_external_prefers_desktop_over_web_pattern')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        web_card = repository.get_card('chatgpt_web_assisted')
        assert web_card is not None
        web_task = ToolTask(
            tool_id='chatgpt_web_assisted',
            title='Consulta web previa',
            objective='Consultar Codex sobre bridge lag en Wplay',
            requested_by_role=TaskRole.TOOL_USE,
            site_id='wplay',
            actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Prompt web', value='Explica el bridge lag de Wplay')],
            metadata={
                'consultation_scope': 'external_assistant',
                'assistant_kind': 'chatgpt',
                'response_capture_mode': 'manual_pasteback',
                'requires_manual_pasteback': True,
            },
        )
        service.execute_task(web_task, approved=True)

        fake_codex = root / 'fake_codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'response_capture_mode': 'clipboard_capture',
                        'requires_manual_pasteback': False,
                        'dry_run_launch': False,
                    }
                }
            )
        )
        refreshed = repository.get_card('codex_installed')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        preview = service.preview_external_consultation(
            user_goal='abre Wplay e inicia sesion',
            assistant_preference='codex',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            launch_dry_run=False,
        )

        assert preview['tool_card']['tool_id'] == 'codex_installed'
        assert preview['mode_selection']['selected_tool_id'] == 'codex_installed'
        assert preview['mode_selection']['metadata']['selection_policy'] == 'preferred_external_tool'
    finally:
        shutil.rmtree(root, ignore_errors=True)

def test_tool_teach_service_external_consultation_tracks_dedicated_session_metadata() -> None:
    root = _workspace('tool_teach_service_external_session_metadata')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        chatgpt_desktop = repository.get_card('chatgpt_installed')
        assert chatgpt_desktop is not None
        repository.save_card(
            chatgpt_desktop.model_copy(
                update={
                    'metadata': {
                        **chatgpt_desktop.metadata,
                        'executable_path': '',
                        'command_name': 'definitely_missing_external_app',
                        'command_aliases': [],
                        'windows_default_paths': [],
                    }
                }
            )
        )
        chatgpt_web = repository.get_card('chatgpt_web_assisted')
        assert chatgpt_web is not None
        repository.save_card(chatgpt_web.model_copy(update={'metadata': {**chatgpt_web.metadata, 'dry_run_launch': True}}))
        refreshed = repository.get_card('chatgpt_web_assisted')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        preview = service.preview_external_consultation(
            user_goal='resume el estado del objetivo activo',
            assistant_preference='chatgpt',
            context_pack='Objetivo activo: validar progreso longitudinal.',
            site_id='wplay',
            goal_parameters={'objective_id': 'objective-1', 'project_id': 'project-1', 'task_id': 'task-1'},
            launch_dry_run=True,
        )
        task, result, _ = service.execute_external_consultation(
            user_goal='resume el estado del objetivo activo',
            assistant_preference='chatgpt',
            context_pack='Objetivo activo: validar progreso longitudinal.',
            site_id='wplay',
            goal_parameters={'objective_id': 'objective-1', 'project_id': 'project-1', 'task_id': 'task-1'},
            approved=True,
            launch_dry_run=True,
        )

        assert preview['tool_card']['tool_id'] == 'chatgpt_web_assisted'
        assert task.metadata['session_scope'] == 'program_chat'
        assert task.metadata['capture_lane'] == 'background'
        assert task.metadata['lane_priority'] == ['background', 'app', 'manual']
        assert task.metadata['thread_key'].startswith('iabv::chatgpt::')
        assert task.metadata['thread_title'].startswith('IABV ChatGPT')
        assert task.metadata['session_profile_dir'].endswith('browser_profile')
        assert Path(task.metadata['session_profile_dir']).exists()
        assert 'IABV_THREAD_KEY:' in str(task.metadata['context_pack'])
        assert result.execution_state.state == 'awaiting_response'
        assert result.execution_state.metadata['manual_pasteback_required'] is False
        assert result.execution_state.metadata['session_scope'] == 'program_chat'
        assert result.execution_state.metadata['thread_key'] == task.metadata['thread_key']
        assert result.execution_state.metadata['capture_lane'] == 'background'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_explicit_chatgpt_preference_stays_in_chatgpt_family_under_technical_pressure() -> None:
    root = _workspace('tool_teach_service_explicit_chatgpt_family')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        _ = repository.get_card('codex_installed')
        chatgpt_web = repository.get_card('chatgpt_web_assisted')
        assert chatgpt_web is not None
        repository.save_card(chatgpt_web.model_copy(update={'metadata': {**chatgpt_web.metadata, 'dry_run_launch': True}}))
        refreshed = repository.get_card('chatgpt_web_assisted')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        preview = service.preview_external_consultation(
            user_goal='Necesito una consulta externa con ChatGPT para revisar el objetivo activo.',
            assistant_preference='chatgpt',
            context_pack='Diagnostico: bridge_lag en Wplay.',
            site_id='wplay',
            diagnostic_category='need_codex_fix',
            incident_kind='bridge_lag',
            launch_dry_run=True,
        )

        assert preview['tool_card']['tool_id'] == 'chatgpt_web_assisted'
        assert preview['tool_task']['metadata']['assistant_kind'] == 'chatgpt'
        assert preview['tool_task']['metadata']['thread_key'].startswith('iabv::chatgpt::')
        assert preview['tool_task']['metadata']['thread_title'].startswith('IABV ChatGPT')
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_explicit_codex_request_overrides_cross_family_selector() -> None:
    root = _workspace('tool_teach_service_explicit_codex_override')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, repository = _service(root)
        fake_codex = root / 'codex.exe'
        fake_codex.write_text('stub', encoding='utf-8')
        codex = repository.get_card('codex_installed')
        assert codex is not None
        repository.save_card(
            codex.model_copy(
                update={
                    'metadata': {
                        **codex.metadata,
                        'executable_path': str(fake_codex),
                        'command_name': '',
                        'command_aliases': [],
                        'windows_default_paths': [],
                        'response_capture_mode': 'clipboard_capture',
                        'requires_manual_pasteback': False,
                        'dry_run_launch': True,
                    }
                }
            )
        )
        refreshed = repository.get_card('codex_installed')
        assert refreshed is not None
        service.registry.refresh_card(refreshed)

        class _WrongSelector:
            def select(self, *, request, draft_task, suggested_tool_id, allowed_tool_ids=None):
                return ModeSelectionDecision(
                    selected_mode=InteractionMode.UI,
                    selected_tool_id='chatgpt_web_assisted',
                    selected_tool_type=ToolType.LLM_WEB_UI,
                    available=True,
                    adapter_exists=True,
                    reason='selector_cross_family',
                )

        service.mode_selector = _WrongSelector()
        request = InferenceRequest(
            user_goal='Necesito una consulta tecnica con Codex para revisar un problema del sistema.',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'tool_id': 'codex_installed',
                'assistant_preference': 'codex',
                'assistant_kind': 'codex',
                'consultation_scope': 'external_assistant',
                'execution_scope': 'read_only',
                'title': 'Consulta tecnica con Codex',
                'expected_outcome': 'Diagnostico tecnico devuelto por Codex.',
            },
        )

        task = service.build_task_from_request(request)

        assert task.tool_id == 'codex_installed'
        assert task.metadata['requested_assistant_kind'] == 'codex'
        assert task.metadata['actual_assistant_kind'] == 'codex'
        assert task.metadata['mode_selection']['selected_tool_id'] == 'codex_installed'
        assert task.metadata['mode_selection']['metadata']['selection_policy'] == 'explicit_assistant_override'
        assert task.metadata['comparison_scope_key']
        assert isinstance(task.metadata['source_trace_ids'], list)
        assert 'Codex' in task.metadata['proposal_summary']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_trace_marks_browser_dom_unavailable_as_capture_unverified() -> None:
    root = _workspace('tool_teach_service_browser_dom_unavailable')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, _ = _service(root)
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

        trace = service._build_ia_trace_entry(task=task, result=result, assistant_kind='chatgpt')

        assert 'capture_unverified' in trace.external_state_flags
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_trace_marks_access_denied_auto_capture_as_capture_unverified() -> None:
    root = _workspace('tool_teach_service_access_denied_capture_unverified')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, _ = _service(root)
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
            },
        )
        result = ToolResult(
            task_id=task.task_id,
            tool_id='chatgpt_web_assisted',
            tool_type=ToolType.LLM_WEB_UI,
            success=False,
            output_text='',
            error_message='[WinError 5] Acceso denegado',
            execution_state=ExecutionState(
                state='failed',
                detail='[WinError 5] Acceso denegado',
                metadata={
                    'assistant_kind': 'chatgpt',
                    'response_capture_mode': 'dom_capture',
                    'auto_capture_attempted': True,
                    'auto_capture_reason': '[WinError 5] Acceso denegado',
                    'launched': False,
                    'response_captured': False,
                },
            ),
            metadata={'error_message': '[WinError 5] Acceso denegado'},
        )

        trace = service._build_ia_trace_entry(task=task, result=result, assistant_kind='chatgpt')

        assert 'capture_unverified' in trace.external_state_flags
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_external_trace_marks_codex_state_missing_as_missing_thread_tracking() -> None:
    root = _workspace('tool_teach_service_codex_state_missing')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        service, _ = _service(root)
        task = ToolTask(
            tool_id='codex_installed',
            title='Consultar Codex',
            objective='Resolver bridge lag',
            requested_by_role=TaskRole.TOOL_USE,
            metadata={'assistant_kind': 'codex'},
        )
        result = ToolResult(
            task_id=task.task_id,
            tool_id='codex_installed',
            tool_type=ToolType.CUSTOM,
            success=False,
            validation_status=ToolValidationStatus.UNVALIDATED,
            execution_state=ExecutionState(
                state='failed',
                detail='codex_state_missing',
                executor_name='external_assistant',
                metadata={
                    'assistant_kind': 'codex',
                    'auto_capture_reason': 'codex_state_missing',
                    'missing_thread_tracking': True,
                    'capture_unverified': True,
                    'response_capture_mode': 'clipboard_capture',
                    'launched': True,
                    'response_captured': False,
                },
            ),
            error_message='codex_state_missing',
        )

        trace = service._build_ia_trace_entry(task=task, result=result, assistant_kind='codex')

        assert 'missing_thread_tracking' in trace.external_state_flags
        assert 'capture_unverified' in trace.external_state_flags
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_teach_service_preview_summary_surfaces_blocked_assistant_preference() -> None:
    card = ToolCard(
        tool_id='chatgpt_web_assisted',
        title='ChatGPT Web',
        tool_type=ToolType.LLM_WEB_UI,
        adapter_key='external_assistant',
        metadata={'assistant_kind': 'chatgpt'},
    )
    task = ToolTask(
        tool_id='chatgpt_web_assisted',
        title='Consulta externa',
        objective='revisa con codex porfa',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[],
        metadata={
            'consultation_scope': 'external_assistant',
            'assistant_kind': 'chatgpt',
        },
    )
    mode_selection = {
        'selected_mode': 'ui',
        'selected_tool_id': 'chatgpt_web_assisted',
        'fallback_used': True,
        'assistant_preference_blocked': True,
        'requested_assistant_preference': 'codex',
        'preferred_tool_id': 'codex_installed',
        'preference_unavailable_reason': (
            "La preferencia explicita del usuario no pudo respetarse porque "
            "ningun miembro de la familia 'codex' esta disponible en este momento."
        ),
        'selection_policy': 'explicit_assistant_preference_unavailable',
    }

    summary = ToolTeachService._preview_summary(
        None, card, task, None, mode_selection
    )

    assert 'preferencia explicita' in summary.lower()
    assert 'codex' in summary.lower()
    assert 'ningun miembro de la familia' in summary.lower()
    assert 'fallback' not in summary.lower()


def test_tool_teach_service_preview_summary_without_block_preserves_generic_fallback_line() -> None:
    card = ToolCard(
        tool_id='chatgpt_web_assisted',
        title='ChatGPT Web',
        tool_type=ToolType.LLM_WEB_UI,
        adapter_key='external_assistant',
        metadata={'assistant_kind': 'chatgpt'},
    )
    task = ToolTask(
        tool_id='chatgpt_web_assisted',
        title='Consulta externa',
        objective='consulta',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[],
        metadata={
            'consultation_scope': 'external_assistant',
            'assistant_kind': 'chatgpt',
        },
    )
    mode_selection = {
        'selected_mode': 'ui',
        'selected_tool_id': 'chatgpt_web_assisted',
        'fallback_used': True,
    }

    summary = ToolTeachService._preview_summary(
        None, card, task, None, mode_selection
    )

    assert 'fallback' in summary.lower()
    assert 'preferencia explicita' not in summary.lower()
