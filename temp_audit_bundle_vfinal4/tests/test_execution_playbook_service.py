from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, ExecutionPlaybook, PlaybookStep, RunStatus, TaskIntent
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService, OperationalExecutorResult


class FakeOperationalExecutor:
    name = 'fake_browser_executor'

    def supports(self, session: AdaptiveSession) -> bool:
        return session.chosen_pack_id == 'browser.generic'

    def describe(self, session: AdaptiveSession) -> str:
        return 'Hay un adaptador operativo real disponible para esta tarea.'

    def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
        return OperationalExecutorResult(
            executed=True,
            status=RunStatus.SUCCESS,
            summary='Ejecucion real completada por el adaptador de prueba.',
            next_actions=['Verificar resultado'],
            metadata={'mode': 'executed_fake'},
        )


def _session(*, simulation_only: bool = False) -> AdaptiveSession:
    return AdaptiveSession(
        user_goal='Buscar en Google una pagina cualquiera',
        intent=TaskIntent(intent_key='browser.search.google', title='Buscar en Google'),
        chosen_pack_id='browser.generic',
        chosen_pack_title='Browser generic',
        status=AdaptiveSessionStatus.READY_TO_EXECUTE,
        playbook=ExecutionPlaybook(
            goal='Buscar en Google una pagina cualquiera',
            pack_id='browser.generic',
            summary='Pack Browser generic.',
            status=AdaptiveSessionStatus.READY_TO_EXECUTE,
            next_phase='execute',
            steps=[
                PlaybookStep(
                    phase_key='execute',
                    title='Ejecutar fase',
                    description='Intentar la fase operativa.',
                    status=RunStatus.PARTIAL,
                    executable=not simulation_only,
                    simulation_only=simulation_only,
                )
            ],
        ),
    )


def test_execution_playbook_service_reports_adapter_missing_without_claiming_success() -> None:
    service = ExecutionPlaybookService()
    session = _session()

    updated = service.execute(session)

    assert updated.status == AdaptiveSessionStatus.READY_TO_EXECUTE
    assert updated.outcome is not None
    assert updated.outcome.status == RunStatus.PARTIAL
    assert updated.outcome.metadata['mode'] == 'adapter_missing'
    assert updated.metadata['execution_state']['state'] == 'adapter_missing'
    assert updated.metadata['execution_state']['executor_available'] is False
    assert 'adaptador operativo real' in updated.outcome.summary


def test_execution_playbook_service_marks_completed_when_executor_exists() -> None:
    service = ExecutionPlaybookService(executor=FakeOperationalExecutor())
    session = _session()

    updated = service.execute(session)

    assert updated.status == AdaptiveSessionStatus.COMPLETED
    assert updated.outcome is not None
    assert updated.outcome.status == RunStatus.SUCCESS
    assert updated.outcome.metadata['mode'] == 'executed_fake'
    assert updated.metadata['execution_state']['state'] == 'executed'
    assert updated.metadata['execution_state']['executor_available'] is True
    assert updated.outcome.summary == 'Ejecucion real completada por el adaptador de prueba.'
