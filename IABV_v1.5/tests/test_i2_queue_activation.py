from datetime import datetime, timezone
from types import SimpleNamespace

from iabv_v15.domain.models import AdaptiveSessionStatus, PendingTaskStatus, PlatformPendingTask
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator


class _Queue:
    def __init__(self, task):
        self.task = task
        self.updates = []

    def list_actionable(self):
        if self.task.status in (PendingTaskStatus.PENDING, PendingTaskStatus.READY_FOR_NEXT_SLICE):
            return [self.task]
        return []

    def upsert(self, task):
        self.task = task
        self.updates.append(task)
        return task


class _Cycle:
    def __init__(self, queue):
        self.queue = queue


def _orchestrator(task, session_status=AdaptiveSessionStatus.READY_TO_EXECUTE):
    ato = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
    ato.autonomy_cycle_service = _Cycle(_Queue(task))
    import threading
    ato._autonomous_queue_lock = threading.RLock()
    ato._autonomous_queue_inflight = set()
    captured = {}

    def handle_request(request):
        captured['request'] = request
        route = SimpleNamespace(provider_name='deving')
        result = SimpleNamespace(status='success')
        session = SimpleNamespace(session_id='session-1', status=session_status)
        return route, result, session

    ato.handle_request = handle_request
    return ato, captured


def test_queue_item_is_activated_through_canonical_handle_request():
    task = PlatformPendingTask(
        id='i2-task-1',
        title='Investigar integracion externa',
        description='Usar evidencia actual y documentar el resultado.',
        reason='integration gap',
        priority='high',
        next_action='preparar consulta externa',
        category='investigation',
        metadata={'objective_id': 'objective-1'},
    )
    ato, captured = _orchestrator(task)

    result = ato.execute_next_actionable_work_item()

    assert result is not None
    assert result['executed'] is True
    assert result['task_id'] == 'i2-task-1'
    request = captured['request']
    assert request.metadata['autonomous_queue_activation'] is True
    assert request.metadata['pending_task_id'] == 'i2-task-1'
    assert request.metadata['control_master_objective_id'] == 'objective-1'
    assert request.goal_parameters['pending_task_next_action'] == 'preparar consulta externa'
    assert ato.autonomy_cycle_service.queue.updates[-1].metadata['executive_activation']['status'] == 'accepted'


def test_queue_item_waiting_for_approval_is_not_resubmitted():
    task = PlatformPendingTask(
        id='i2-task-approval',
        title='Cambiar configuracion sensible',
        status=PendingTaskStatus.PENDING,
        metadata={
            'executive_activation': {
                'status': 'waiting_approval',
                'session_id': 'session-existing',
            }
        },
    )
    ato, captured = _orchestrator(task, AdaptiveSessionStatus.WAITING_APPROVAL)

    assert ato.execute_next_actionable_work_item() is None
    assert captured == {}
    assert ato.autonomy_cycle_service.queue.updates == []


def test_failed_queue_activation_remains_retryable():
    task = PlatformPendingTask(id='i2-task-fail', title='Revisar proveedor externo')
    ato, _ = _orchestrator(task)

    def fail(_request):
        raise RuntimeError('dispatch unavailable')

    ato.handle_request = fail
    result = ato.execute_next_actionable_work_item()

    assert result is not None
    assert result['executed'] is False
    assert result['activation_status'] == 'failed'
    assert ato.autonomy_cycle_service.queue.updates == []