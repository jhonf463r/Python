from pathlib import Path

from iabv_v15.domain.models import ExecutionState, ToolCard, ToolResult, ToolTask, ToolType
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.trust.post_action_observer import PostActionObserver


def test_post_action_observer_records_actor_report_without_claiming_observation(tmp_path: Path) -> None:
    repository = ToolRecordRepository(AppDatabase(str(tmp_path / 'app.sqlite')), ArtifactStorage(str(tmp_path / 'artifacts')))
    task = ToolTask(tool_id='shell_command', title='actor report', objective='record declared result')
    card = ToolCard(tool_id='shell_command', title='Shell', tool_type=ToolType.SHELL, adapter_key='shell')
    result = ToolResult(task_id=task.task_id, tool_id=card.tool_id, tool_type=ToolType.SHELL, success=True, execution_state=ExecutionState(state='executed'))

    observed = PostActionObserver(ToolMemory(repository)).observe(result=result, task=task, card=card)

    assert observed is result
    event = repository.list_log(tool_id=card.tool_id, task_id=task.task_id, limit=1)[0]
    assert event['payload']['actor_reported_success'] is True
    assert event['payload']['observation_status'] == 'not_independently_observed'
    assert event['payload']['verification_status'] == 'not_verified'
