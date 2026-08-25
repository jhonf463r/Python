from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    CapturedStep,
    ExecutionState,
    InteractionChannel,
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


def _result(task: ToolTask, tool_type: ToolType, *, success: bool = True) -> ToolResult:
    return ToolResult(
        task_id=task.task_id,
        tool_id=task.tool_id,
        tool_type=tool_type,
        success=success,
        validation_status=ToolValidationStatus.APPROVED if success else ToolValidationStatus.SANDBOX_FAIL,
        execution_state=ExecutionState(state='executed' if success else 'failed', detail='ok' if success else 'failed'),
        output_text='ok' if success else '',
        error_message='' if success else 'failed',
    )


def test_interaction_learning_service_normalizes_ui_background_and_api() -> None:
    root = _workspace('interaction_learning_service')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = _repository(root)
        service = InteractionLearningService(repository)

        browser_card = ToolCard(tool_id='playwright_browser', title='Playwright', tool_type=ToolType.BROWSER, adapter_key='playwright')
        browser_task = ToolTask(
            tool_id='playwright_browser',
            title='Abrir pagina',
            objective='Abrir una pagina y extraer un titulo',
            site_id='demo',
            actions=[
                ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir', target='https://example.com/app?token=secret'),
                ToolAction(action_type=ToolActionType.EXTRACT_TEXT, label='Titulo', target='#title'),
            ],
        )
        browser_pattern = service.learn_from_execution(card=browser_card, task=browser_task, result=_result(browser_task, ToolType.BROWSER))

        shell_card = ToolCard(tool_id='shell_command', title='Shell', tool_type=ToolType.SHELL, adapter_key='shell')
        shell_task = ToolTask(
            tool_id='shell_command',
            title='Listar',
            objective='Listar archivos locales',
            actions=[ToolAction(action_type=ToolActionType.RUN_COMMAND, label='Dir', value='Get-ChildItem -Force')],
        )
        shell_pattern = service.learn_from_execution(card=shell_card, task=shell_task, result=_result(shell_task, ToolType.SHELL))

        api_card = ToolCard(tool_id='mcp_client', title='MCP', tool_type=ToolType.MCP_CLIENT, adapter_key='mcp')
        api_task = ToolTask(
            tool_id='mcp_client',
            title='Consultar MCP',
            objective='Consultar un servicio local por API',
            actions=[ToolAction(action_type=ToolActionType.MCP_CALL, label='Call', value='health')],
        )
        api_pattern = service.learn_from_execution(card=api_card, task=api_task, result=_result(api_task, ToolType.MCP_CLIENT))

        assert browser_pattern.channel == InteractionChannel.UI
        assert browser_pattern.operations[0].target == 'https://example.com/app'
        assert shell_pattern.channel == InteractionChannel.BACKGROUND
        assert shell_pattern.operations[0].value_hint == 'Get-ChildItem'
        assert api_pattern.channel == InteractionChannel.API
        assert api_pattern.operations[0].value_hint == '<mcp_call>'

        stored_patterns = repository.list_interaction_patterns(limit=10)
        assert len(stored_patterns) == 3
        stored_observations = repository.list_interaction_observations(limit=10)
        assert len(stored_observations) == 3
        stored_episodes = repository.list_interaction_episodes(limit=10)
        assert len(stored_episodes) == 3
        assert all(item.result is not None for item in stored_episodes)
        assert {item.mode_used for item in stored_episodes} == {InteractionChannel.UI, InteractionChannel.BACKGROUND, InteractionChannel.API}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_interaction_learning_service_matches_reusable_patterns() -> None:
    root = _workspace('interaction_learning_match')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = _repository(root)
        service = InteractionLearningService(repository)
        card = ToolCard(tool_id='playwright_browser', title='Playwright', tool_type=ToolType.BROWSER, adapter_key='playwright')
        task = ToolTask(
            tool_id='playwright_browser',
            title='Abrir pagina demo',
            objective='Abrir una pagina demo y sacar una captura',
            site_id='demo',
            actions=[
                ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir', target='https://example.com/demo'),
                ToolAction(action_type=ToolActionType.SCREENSHOT, label='Captura', parameters={'path': str(root / 'shot.png')}),
            ],
        )
        service.learn_from_execution(card=card, task=task, result=_result(task, ToolType.BROWSER))

        matched = service.match_patterns(card=card, task=task, limit=3)
        summaries = service.summarize_patterns(site_id='demo', user_goal='captura demo', limit=3)
        episodes = repository.list_interaction_episodes(tool_id='playwright_browser', limit=5)

        assert len(matched) == 1
        assert matched[0].tool_id == 'playwright_browser'
        assert len(summaries) == 1
        assert summaries[0]['channel'] == 'ui'
        assert len(episodes) == 1
        assert episodes[0].reused_pattern is False
        assert episodes[0].result is not None
        assert episodes[0].result.success is True
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_codex_contracts_serialize_cleanly() -> None:
    from iabv_v15.domain.models import (
        CodexAcceptanceCriteria,
        CodexConstraints,
        CodexContextPack,
        CodexFileScope,
        CodexRunResult,
        CodexTaskSpec,
        CodexTestPlan,
        RunStatus,
    )

    spec = CodexTaskSpec(
        title='Ajustar flujo universal',
        goal='Conectar aprendizaje universal al planner.',
        file_scope=[CodexFileScope(path='src/iabv_v15/services/adaptive/task_context_assembler.py', writable=True)],
        constraints=CodexConstraints(read_only_paths=['src/iabv_v15/domain/models.py'], forbidden_operations=['git reset --hard']),
        acceptance_criteria=[CodexAcceptanceCriteria(description='La suite debe seguir verde.')],
        test_plan=CodexTestPlan(title='Suite minima', commands=['pytest tests/test_interaction_learning_service.py -q'], expected_outcomes=['verde']),
        context_pack=CodexContextPack(summary='Usar episodios de interaccion recientes.', interaction_episode_ids=['ep-1']),
    )
    result = CodexRunResult(status=RunStatus.SUCCESS, summary='Cambio validado.', changed_files=['src/iabv_v15/services/tools/interaction_learning_service.py'])

    payload = spec.model_dump(mode='json')
    restored = CodexTaskSpec.model_validate(payload)

    assert restored.title == spec.title
    assert restored.file_scope[0].writable is True
    assert result.status == RunStatus.SUCCESS


def test_interaction_learning_service_learns_from_teaching_session_and_reuses_episode_id() -> None:
    root = _workspace('interaction_learning_teaching')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = _repository(root)
        service = InteractionLearningService(repository)
        steps = [
            CapturedStep(episode_id='teach-1', action_type='input', target='#email', metadata={'field_role': 'email', 'capture_channel': 'visible'}),
            CapturedStep(episode_id='teach-1', action_type='input', target='#password', metadata={'field_role': 'password', 'capture_channel': 'visible'}),
            CapturedStep(episode_id='teach-1', action_type='submit', target='#submit', screenshot_path=str(root / 'shot.png'), metadata={'element_role': 'button', 'capture_channel': 'visible'}),
        ]
        packet = {
            'bundle_id': 'bundle-1',
            'learning_readiness': {'status': 'partial', 'summary': 'La ensenanza ya aporta senales utiles.'},
            'login_learning': {'status': 'partial', 'summary': 'El login ya muestra partes importantes.'},
            'visual_summary': {
                'visual_alignment_score': 0.6,
                'critical_object_coverage': 0.67,
                'login_visual_completeness': 0.7,
                'manual_correction_count': 1,
                'green_count': 3,
                'orange_count': 1,
                'red_count': 0,
            },
        }

        episode = service.learn_from_teaching_session(
            episode_id='teach-1',
            site_id='wplay',
            display_name='Wplay',
            objective='Abrir Wplay e iniciar sesion.',
            expected_outcome='Sesion abierta.',
            notes='Corregir el submit si hace falta.',
            steps=steps,
            learning_packet=packet,
        )
        assert episode is not None
        assert episode.mode_used == InteractionChannel.UI
        assert episode.pattern_id
        assert episode.selector_name == 'teaching_replay_bridge'
        assert any(item.label.startswith('teaching:') for item in episode.learning_signals)

        updated = service.learn_from_teaching_session(
            episode_id='teach-1',
            site_id='wplay',
            display_name='Wplay',
            objective='Abrir Wplay e iniciar sesion.',
            expected_outcome='Sesion abierta.',
            notes='Replay corregido.',
            steps=steps,
            learning_packet={**packet, 'visual_summary': {**packet['visual_summary'], 'manual_correction_count': 2}},
            previous_episode_id=episode.interaction_episode_id,
        )

        stored_episodes = repository.list_interaction_episodes(site_id='wplay', limit=10)
        stored_patterns = repository.list_interaction_patterns(site_id='wplay', limit=10)
        assert updated is not None
        assert updated.interaction_episode_id == episode.interaction_episode_id
        assert len(stored_episodes) == 1
        assert len(stored_patterns) == 1
        assert stored_patterns[0].tool_id == 'playwright_browser'
        assert stored_episodes[0].metadata['notes'] == 'Replay corregido.'
    finally:
        shutil.rmtree(root, ignore_errors=True)
