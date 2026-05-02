"""Tests for PlatformPendingQueue and related models (Fix 18b/18d)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    PendingTaskStatus,
    PlatformPendingTask,
    PlatformResumeHint,
)
from iabv_v15.services.evolution.platform_pending_queue import (
    PlatformPendingQueue,
    _WINDOWS_INTEGRATION_TASKS,
)


@pytest.fixture
def queue(tmp_path: Path) -> PlatformPendingQueue:
    return PlatformPendingQueue(evolution_dir=str(tmp_path / 'evolution'))


class TestPlatformPendingTaskModel:
    def test_defaults(self):
        task = PlatformPendingTask(title='Test task')
        assert task.title == 'Test task'
        assert task.status == PendingTaskStatus.PENDING
        assert task.priority == 'medium'
        assert task.id  # auto-generated UUID

    def test_all_statuses(self):
        for status in PendingTaskStatus:
            task = PlatformPendingTask(title='x', status=status)
            assert task.status == status

    def test_serialization_roundtrip(self):
        task = PlatformPendingTask(
            title='Test',
            description='desc',
            reason='reason',
            dependency_missing='lib_x',
            priority='high',
            next_action='pip install lib_x',
            status=PendingTaskStatus.BLOCKED,
            category='windows_native',
            resume_hint='check lib_x availability',
        )
        data = json.loads(task.model_dump_json())
        recovered = PlatformPendingTask.model_validate(data)
        assert recovered.title == task.title
        assert recovered.status == PendingTaskStatus.BLOCKED
        assert recovered.dependency_missing == 'lib_x'


class TestPlatformResumeHintModel:
    def test_defaults(self):
        hint = PlatformResumeHint(task_id='abc')
        assert hint.task_id == 'abc'
        assert hint.handoff_required is False
        assert hint.remaining_steps == []

    def test_with_data(self):
        hint = PlatformResumeHint(
            task_id='win_toast',
            checkpoint_phase='dependency_check',
            last_successful_step='verified_windows_10_plus',
            remaining_steps=['install_winotify', 'implement_bridge', 'test'],
            handoff_required=True,
            context_snapshot={'win_version': '10.0.19045'},
        )
        assert hint.handoff_required is True
        assert len(hint.remaining_steps) == 3
        assert hint.context_snapshot['win_version'] == '10.0.19045'


class TestPlatformPendingQueue:
    def test_upsert_and_get(self, queue: PlatformPendingQueue):
        task = PlatformPendingTask(id='test_1', title='Test task')
        result = queue.upsert(task)
        assert result.id == 'test_1'

        retrieved = queue.get('test_1')
        assert retrieved is not None
        assert retrieved.title == 'Test task'

    def test_get_nonexistent(self, queue: PlatformPendingQueue):
        assert queue.get('nonexistent') is None

    def test_list_all_sorted_by_priority(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='low', title='Low', priority='low'))
        queue.upsert(PlatformPendingTask(id='crit', title='Critical', priority='critical'))
        queue.upsert(PlatformPendingTask(id='med', title='Medium', priority='medium'))
        queue.upsert(PlatformPendingTask(id='high', title='High', priority='high'))

        tasks = queue.list_all()
        priorities = [t.priority for t in tasks]
        assert priorities == ['critical', 'high', 'medium', 'low']

    def test_list_actionable(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='p', title='Pending', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='b', title='Blocked', status=PendingTaskStatus.BLOCKED))
        queue.upsert(PlatformPendingTask(id='r', title='Ready', status=PendingTaskStatus.READY_FOR_NEXT_SLICE))
        queue.upsert(PlatformPendingTask(id='c', title='Complete', status=PendingTaskStatus.COMPLETED))

        actionable = queue.list_actionable()
        ids = {t.id for t in actionable}
        assert 'p' in ids
        assert 'r' in ids
        assert 'b' not in ids
        assert 'c' not in ids

    def test_list_blocked(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='p', title='Pending', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='b', title='Blocked', status=PendingTaskStatus.BLOCKED))

        blocked = queue.list_blocked()
        assert len(blocked) == 1
        assert blocked[0].id == 'b'

    def test_mark_status(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='t1', title='Task'))
        result = queue.mark_status('t1', PendingTaskStatus.COMPLETED)
        assert result is not None
        assert result.status == PendingTaskStatus.COMPLETED

        retrieved = queue.get('t1')
        assert retrieved is not None
        assert retrieved.status == PendingTaskStatus.COMPLETED

    def test_mark_status_nonexistent(self, queue: PlatformPendingQueue):
        assert queue.mark_status('nope', PendingTaskStatus.COMPLETED) is None

    def test_summary(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='p1', title='A', status=PendingTaskStatus.PENDING, priority='high'))
        queue.upsert(PlatformPendingTask(id='p2', title='B', status=PendingTaskStatus.BLOCKED, priority='high'))
        queue.upsert(PlatformPendingTask(id='p3', title='C', status=PendingTaskStatus.PENDING, priority='low'))

        s = queue.summary()
        assert s['total'] == 3
        assert s['by_status']['PENDING'] == 2
        assert s['by_status']['BLOCKED'] == 1
        assert s['by_priority']['high'] == 2
        assert s['actionable'] == 2
        assert s['blocked'] == 1

    def test_to_portable_items(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(
            id='t1', title='Task 1', description='desc',
            reason='reason', priority='high',
            next_action='do something', category='test',
        ))
        items = queue.to_portable_items()
        assert len(items) == 1
        item = items[0]
        assert item['id'] == 't1'
        assert item['title'] == 'Task 1'
        assert item['status'] == 'PENDING'
        assert item['next_action'] == 'do something'

    def test_seed_windows_integration_tasks(self, queue: PlatformPendingQueue):
        seeded = queue.seed_windows_integration_tasks()
        assert len(seeded) == len(_WINDOWS_INTEGRATION_TASKS)

        all_tasks = queue.list_all()
        assert len(all_tasks) == len(_WINDOWS_INTEGRATION_TASKS)

        ids = {t.id for t in all_tasks}
        for task_dict in _WINDOWS_INTEGRATION_TASKS:
            assert task_dict['id'] in ids

    def test_seed_idempotent(self, queue: PlatformPendingQueue):
        queue.seed_windows_integration_tasks()
        queue.seed_windows_integration_tasks()
        assert len(queue.list_all()) == len(_WINDOWS_INTEGRATION_TASKS)

    def test_seed_preserves_completed(self, queue: PlatformPendingQueue):
        queue.seed_windows_integration_tasks()
        first_id = _WINDOWS_INTEGRATION_TASKS[0]['id']
        queue.mark_status(first_id, PendingTaskStatus.COMPLETED)
        queue.seed_windows_integration_tasks()
        task = queue.get(first_id)
        assert task is not None
        assert task.status == PendingTaskStatus.COMPLETED


class TestResumeHints:
    def test_save_and_get(self, queue: PlatformPendingQueue):
        hint = PlatformResumeHint(
            task_id='win_toast',
            checkpoint_phase='install',
            last_successful_step='pip_install',
            remaining_steps=['implement', 'test'],
            handoff_required=True,
        )
        queue.save_resume_hint(hint)

        retrieved = queue.get_resume_hint('win_toast')
        assert retrieved is not None
        assert retrieved.task_id == 'win_toast'
        assert retrieved.handoff_required is True
        assert retrieved.remaining_steps == ['implement', 'test']

    def test_get_nonexistent(self, queue: PlatformPendingQueue):
        assert queue.get_resume_hint('nope') is None

    def test_list_resume_hints(self, queue: PlatformPendingQueue):
        queue.save_resume_hint(PlatformResumeHint(task_id='a'))
        queue.save_resume_hint(PlatformResumeHint(task_id='b'))
        hints = queue.list_resume_hints()
        assert len(hints) == 2
