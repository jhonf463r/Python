from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    ExecutionState,
    InferenceRequest,
    TaskRole,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_registry import ToolRegistry


class DummyAdapter:
    def __init__(self, tool_type: ToolType, *, available: bool = True) -> None:
        self.tool_type = tool_type
        self.available = available

    def is_available(self, card: ToolCard) -> bool:
        return self.available

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, object]:
        return {
            'success': True,
            'output_text': 'ok',
            'extracted_data': {},
            'artifacts': [],
            'error_message': '',
            'execution_ms': 5,
            'metadata': {'sandbox': sandbox},
        }


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _repository(root: Path) -> ToolRecordRepository:
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    return ToolRecordRepository(db, storage)


def _selector(root: Path, *, all_available: bool = True) -> tuple[InteractionModeSelector, ToolRegistry, ToolRecordRepository, InteractionLearningService]:
    repository = _repository(root)
    adapters = {
        'playwright': DummyAdapter(ToolType.BROWSER, available=all_available),
        'shell': DummyAdapter(ToolType.SHELL, available=all_available),
        'aider': DummyAdapter(ToolType.CODE_EDITOR, available=all_available),
        'mcp': DummyAdapter(ToolType.MCP_CLIENT, available=all_available),
        'ollama': DummyAdapter(ToolType.LLM_LOCAL, available=all_available),
        'external_assistant': DummyAdapter(ToolType.CUSTOM, available=all_available),
    }
    registry = ToolRegistry(repository, adapters)
    learning = InteractionLearningService(repository)
    selector = InteractionModeSelector(registry, repository)
    return selector, registry, repository, learning


def _result(task: ToolTask, tool_type: ToolType) -> ToolResult:
    return ToolResult(
        task_id=task.task_id,
        tool_id=task.tool_id,
        tool_type=tool_type,
        success=True,
        validation_status=ToolValidationStatus.APPROVED,
        execution_state=ExecutionState(state='executed', detail='ok'),
        output_text='ok',
    )


def _failed_result(task: ToolTask, tool_type: ToolType, *, detail: str = '[WinError 5] Acceso denegado') -> ToolResult:
    return ToolResult(
        task_id=task.task_id,
        tool_id=task.tool_id,
        tool_type=tool_type,
        success=False,
        validation_status=ToolValidationStatus.UNVALIDATED,
        execution_state=ExecutionState(state='failed', detail=detail),
        error_message=detail,
        output_text='',
    )


def test_selector_prefers_ui_when_resolved_pattern_exists() -> None:
    root = _workspace('interaction_mode_selector_ui')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        selector, registry, _repository, learning = _selector(root)
        card = registry.get_card('playwright_browser')
        assert card is not None
        task = ToolTask(
            tool_id='playwright_browser',
            title='Abrir demo',
            objective='Abre una pagina demo y toma una captura',
            site_id='demo',
            actions=[
                ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir', target='https://example.com/demo'),
                ToolAction(action_type=ToolActionType.SCREENSHOT, label='Captura', parameters={'path': str(root / 'shot.png')}),
            ],
        )
        learning.learn_from_execution(card=card, task=task, result=_result(task, ToolType.BROWSER))

        request = InferenceRequest(
            user_goal='Abre una pagina demo y toma una captura',
            task_role=TaskRole.TOOL_USE,
            site_hint='demo',
        )
        selection = selector.select(request=request, draft_task=task, suggested_tool_id='playwright_browser')

        assert selection.selected_mode.value == 'ui'
        assert selection.selected_tool_id == 'playwright_browser'
        assert selection.adapter_exists is True
        assert selection.available is True
        assert selection.equivalent_pattern_exists is True
        assert selection.already_resolved is True
        assert bool(selection.reusable_pattern_id)
        assert bool(selection.reusable_episode_id)
        assert selection.fallback_used is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_selector_detects_background_duplicate_and_implemented_improvement() -> None:
    root = _workspace('interaction_mode_selector_background')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        selector, registry, _repository, learning = _selector(root)
        card = registry.get_card('shell_command')
        assert card is not None
        task = ToolTask(
            tool_id='shell_command',
            title='Inspeccionar shell',
            objective='Ejecuta un comando local para listar archivos',
            actions=[ToolAction(action_type=ToolActionType.RUN_COMMAND, label='Listar', value='Get-ChildItem -Force')],
        )
        learning.learn_from_execution(card=card, task=task, result=_result(task, ToolType.SHELL))

        request = InferenceRequest(
            user_goal='Mejora el comando shell para listar archivos',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={'execution_scope': 'read_only'},
        )
        selection = selector.select(request=request, draft_task=task, suggested_tool_id='shell_command')

        assert selection.selected_mode.value == 'background'
        assert selection.selected_tool_id == 'shell_command'
        assert selection.equivalent_pattern_exists is True
        assert selection.already_resolved is True
        assert selection.improvement_already_implemented is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_selector_uses_fallback_when_no_adapter_is_available() -> None:
    root = _workspace('interaction_mode_selector_fallback')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        selector, registry, _repository, _learning = _selector(root, all_available=False)
        draft_task = ToolTask(
            tool_id='mcp_client',
            title='Consulta API',
            objective='Consulta una API local por MCP',
        )
        request = InferenceRequest(
            user_goal='Consulta una API local por MCP',
            task_role=TaskRole.TOOL_USE,
        )
        selection = selector.select(request=request, draft_task=draft_task, suggested_tool_id='mcp_client')

        assert selection.selected_tool_id == 'mcp_client'
        assert selection.available is False
        assert selection.fallback_used is True
        assert selection.selected_mode.value == 'fallback'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_selector_prefers_requested_external_desktop_tool_over_learned_web_pattern() -> None:
    root = _workspace('interaction_mode_selector_external_preferred')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        selector, registry, _repository, learning = _selector(root)
        web_card = registry.get_card('chatgpt_web_assisted')
        codex_card = registry.get_card('codex_installed')
        assert web_card is not None
        assert codex_card is not None
        web_task = ToolTask(
            tool_id='chatgpt_web_assisted',
            title='Consulta web previa',
            objective='Consultar Codex sobre bridge lag en Wplay',
            site_id='wplay',
            actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Prompt web', value='Explica el bridge lag de Wplay')],
        )
        learning.learn_from_execution(card=web_card, task=web_task, result=_result(web_task, ToolType.LLM_WEB_UI))

        request = InferenceRequest(
            user_goal='Consultar Codex sobre bridge lag en Wplay',
            task_role=TaskRole.TOOL_USE,
            site_hint='wplay',
            goal_parameters={
                'consultation_scope': 'external_assistant',
                'tool_id': 'codex_installed',
                'assistant_kind': 'codex',
                'allowed_tool_ids': ['codex_installed', 'chatgpt_web_assisted'],
            },
        )
        draft_task = ToolTask(
            tool_id='codex_installed',
            title='Consulta Codex',
            objective='Consultar Codex sobre bridge lag en Wplay',
            site_id='wplay',
        )

        selection = selector.select(
            request=request,
            draft_task=draft_task,
            suggested_tool_id='codex_installed',
            allowed_tool_ids=['codex_installed', 'chatgpt_web_assisted'],
        )

        assert selection.selected_tool_id == 'codex_installed'
        assert selection.adapter_exists is True
        assert selection.available is True
        assert selection.metadata['selection_policy'] == 'preferred_external_tool'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_selector_does_not_reuse_failure_only_pattern() -> None:
    root = _workspace('interaction_mode_selector_failure_pattern')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        selector, registry, _repository, learning = _selector(root)
        card = registry.get_card('playwright_browser')
        assert card is not None
        task = ToolTask(
            tool_id='playwright_browser',
            title='Abrir demo',
            objective='Abre una pagina demo y toma una captura',
            site_id='demo',
            actions=[ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir', target='https://example.com/demo')],
        )
        learning.learn_from_execution(card=card, task=task, result=_failed_result(task, ToolType.BROWSER))

        request = InferenceRequest(
            user_goal='Abre una pagina demo y toma una captura',
            task_role=TaskRole.TOOL_USE,
            site_hint='demo',
        )
        selection = selector.select(request=request, draft_task=task, suggested_tool_id='playwright_browser')

        assert selection.equivalent_pattern_exists is False
        assert selection.already_resolved is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_selector_avoids_repeatedly_blocked_external_tool_when_same_family_alternative_exists() -> None:
    root = _workspace('interaction_mode_selector_repeated_blocked_external')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        selector, registry, _repository, learning = _selector(root)
        blocked_card = registry.get_card('chatgpt_web_assisted')
        fallback_card = registry.get_card('chatgpt_installed')
        assert blocked_card is not None
        assert fallback_card is not None
        blocked_task = ToolTask(
            tool_id='chatgpt_web_assisted',
            title='Consulta ChatGPT',
            objective='Consultar ChatGPT sobre Playwright bloqueado',
            actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Prompt web', value='Revisar bloqueo de Playwright')],
        )
        learning.learn_from_execution(card=blocked_card, task=blocked_task, result=_failed_result(blocked_task, ToolType.LLM_WEB_UI))
        learning.learn_from_execution(card=blocked_card, task=blocked_task, result=_failed_result(blocked_task, ToolType.LLM_WEB_UI))

        request = InferenceRequest(
            user_goal='Consultar ChatGPT sobre Playwright bloqueado',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'consultation_scope': 'external_assistant',
                'tool_id': 'chatgpt_web_assisted',
                'assistant_kind': 'chatgpt',
                'allowed_tool_ids': ['chatgpt_web_assisted', 'chatgpt_installed'],
            },
        )
        draft_task = ToolTask(
            tool_id='chatgpt_web_assisted',
            title='Consulta ChatGPT',
            objective='Consultar ChatGPT sobre Playwright bloqueado',
        )

        selection = selector.select(
            request=request,
            draft_task=draft_task,
            suggested_tool_id='chatgpt_web_assisted',
            allowed_tool_ids=['chatgpt_web_assisted', 'chatgpt_installed'],
        )

        assert selection.selected_tool_id == 'chatgpt_installed'
        assert selection.selected_tool_id != 'chatgpt_web_assisted'
    finally:
        shutil.rmtree(root, ignore_errors=True)
