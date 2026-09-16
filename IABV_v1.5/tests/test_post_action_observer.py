from pathlib import Path
import os
import subprocess
import sys

from iabv_v15.domain.models import ExecutionState, ToolCard, ToolResult, ToolTask, ToolType
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.trust.post_action_observer import PostActionObserver


def test_post_action_observer_direct_import_does_not_load_windows_authority_stack() -> None:
    source_root = Path(__file__).resolve().parents[1] / 'src'
    code = '''
import builtins
import sys

blocked = {"pywintypes", "win32file", "win32pipe", "win32security"}
real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name.split(".", 1)[0] in blocked:
        raise ModuleNotFoundError(f"blocked platform dependency: {name}")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from iabv_v15.services.trust.post_action_observer import PostActionObserver
assert PostActionObserver.__name__ == "PostActionObserver"
assert not any(name.startswith("iabv_v15.services.trust.authority") for name in sys.modules)
'''
    environment = {**os.environ, 'PYTHONPATH': str(source_root)}
    result = subprocess.run(
        [sys.executable, '-c', code],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


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
