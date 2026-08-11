from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, ApprovalDecision, RunStatus, TaskOutcome


@dataclass(slots=True)
class OperationalExecutorResult:
    executed: bool
    status: RunStatus
    summary: str
    next_actions: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


class OperationalExecutor(Protocol):
    name: str

    def supports(self, session: AdaptiveSession) -> bool:
        ...

    def describe(self, session: AdaptiveSession) -> str:
        ...

    def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
        ...


class NullOperationalExecutor:
    name = 'no_operational_executor'

    def supports(self, session: AdaptiveSession) -> bool:
        return False

    def describe(self, session: AdaptiveSession) -> str:
        pack = session.chosen_pack_title or session.chosen_pack_id or 'esta tarea'
        return (
            f'No hay un adaptador operativo real conectado para {pack}. '
            'La app puede planificar, simular y diagnosticar, pero todavia no ejecutar ese dominio por si sola.'
        )

    def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
        return OperationalExecutorResult(
            executed=False,
            status=RunStatus.PARTIAL,
            summary=self.describe(session),
            next_actions=['Simular', 'Ver evolutivo', 'Preparar Codex'],
            metadata={'mode': 'adapter_missing'},
        )


class ExecutionPlaybookService:
    def __init__(
        self, 
        executor: OperationalExecutor | None = None,
        knowledge_executor: OperationalExecutor | None = None,
    ) -> None:
        self.tool_executor = executor or NullOperationalExecutor()
        self.knowledge_executor = knowledge_executor or NullOperationalExecutor()
        # Default to tool executor for backward compatibility
        self.executor = self.tool_executor

    def annotate_execution_capability(self, session: AdaptiveSession) -> AdaptiveSession:
        execute_step = self._execute_step(session)
        simulation_only = bool(execute_step.simulation_only) if execute_step is not None else False
        
        # Select appropriate executor based on pack_id
        if session.chosen_pack_id == 'knowledge.query':
            executor = self.knowledge_executor
        else:
            executor = self.tool_executor
        
        executor_available = bool(execute_step is not None and not simulation_only and executor.supports(session))
        state = 'not_applicable'
        if execute_step is not None:
            if simulation_only:
                state = 'simulation_only'
            elif executor_available:
                state = 'ready'
            else:
                state = 'adapter_missing'
        detail = self._describe_execution_capability(session, execute_step, executor_available, simulation_only)
        execution_state = {
            'state': state,
            'executor_name': getattr(executor, 'name', 'unknown'),
            'executor_available': executor_available,
            'simulation_only': simulation_only,
            'detail': detail,
            'execute_step_present': bool(execute_step is not None),
        }
        session.metadata['execution_state'] = execution_state
        if execute_step is not None:
            execute_step.metadata['execution_state'] = execution_state
            execute_step.detail = detail
        return session

    def approve_strategy(self, session: AdaptiveSession) -> AdaptiveSession:
        return self._approve_matching(session, phase_key='strategy')

    def approve_next_phase(self, session: AdaptiveSession) -> AdaptiveSession:
        pending = next((item for item in session.approval_checkpoints if item.decision == ApprovalDecision.PENDING), None)
        if pending is None:
            return session
        pending.decision = ApprovalDecision.APPROVED
        pending.decided_at_utc = datetime.now(timezone.utc)
        return self._refresh_status(session)

    def simulate(self, session: AdaptiveSession) -> AdaptiveSession:
        session = self.annotate_execution_capability(session)
        execution_state = self._execution_state(session)
        if session.playbook is not None:
            session.playbook.status = AdaptiveSessionStatus.READY_TO_EXECUTE
            session.playbook.next_phase = 'approval' if self._has_pending_approval(session) else 'execute'
            execute_step = self._execute_step(session)
            if execute_step is not None:
                execute_step.detail = str(execution_state.get('detail') or 'Simulacion completada.')
                execute_step.metadata['last_action'] = 'simulate'
        self._update_execution_state(
            session,
            state='simulated',
            detail='Simulacion completada. ' + str(execution_state.get('detail') or ''),
            last_action='simulate',
        )
        session.status = AdaptiveSessionStatus.WAITING_APPROVAL if self._has_pending_approval(session) else AdaptiveSessionStatus.READY_TO_EXECUTE
        session.outcome = TaskOutcome(
            status=RunStatus.PARTIAL,
            summary='Simulacion completada. La estrategia ya quedo aterrizada con contexto, pack y evidencias.',
            next_actions=self._ready_next_actions(session),
            metadata={'mode': 'simulate'},
        )
        session.updated_at_utc = datetime.now(timezone.utc)
        return session

    def execute(self, session: AdaptiveSession) -> AdaptiveSession:
        session = self.annotate_execution_capability(session)
        pending = self._has_pending_approval(session)
        if pending:
            self._update_execution_state(
                session,
                state='approval_blocked',
                detail='La ejecucion sigue bloqueada hasta completar los checkpoints pendientes.',
                last_action='execute',
            )
            session.status = AdaptiveSessionStatus.WAITING_APPROVAL
            session.outcome = TaskOutcome(
                status=RunStatus.PARTIAL,
                summary='La fase operativa sigue bloqueada porque todavia hay checkpoints pendientes.',
                next_actions=['Aprobar estrategia o la fase critica antes de ejecutar.'],
                metadata={'mode': 'execute_blocked'},
            )
            session.updated_at_utc = datetime.now(timezone.utc)
            return session

        execute_step = self._execute_step(session)
        execution_state = self._execution_state(session)
        
        # Select appropriate executor based on pack_id
        if session.chosen_pack_id == 'knowledge.query':
            executor = self.knowledge_executor
        else:
            executor = self.tool_executor
        
        if execute_step is None:
            self._update_execution_state(
                session,
                state='not_applicable',
                detail='No hay una fase execute declarada para esta sesion.',
                last_action='execute',
            )
            session.status = AdaptiveSessionStatus.READY_TO_EXECUTE
            session.outcome = TaskOutcome(
                status=RunStatus.PARTIAL,
                summary='La sesion no declaro una fase ejecutable; solo queda lista para revision o siguiente ajuste.',
                next_actions=['Simular', 'Ver evolutivo'],
                metadata={'mode': 'execute_not_applicable'},
            )
        elif bool(execution_state.get('simulation_only')):
            self._update_execution_state(
                session,
                state='simulation_only',
                detail='Esta fase sigue restringida a simulacion o preparacion por su nivel de riesgo.',
                last_action='execute',
            )
            session.status = AdaptiveSessionStatus.READY_TO_EXECUTE
            session.outcome = TaskOutcome(
                status=RunStatus.PARTIAL,
                summary='La estrategia quedo aprobada, pero esta fase sigue en modo guiado o simulado por politica de riesgo.',
                next_actions=['Simular', 'Aprobar fase siguiente', 'Ver evolutivo'],
                metadata={'mode': 'execute_simulation_only'},
            )
        elif not bool(execution_state.get('executor_available')):
            result = OperationalExecutorResult(
                executed=False,
                status=RunStatus.PARTIAL,
                summary=executor.describe(session),
                next_actions=['Simular', 'Ver evolutivo', 'Preparar Codex'],
                metadata={'mode': 'adapter_missing'},
            )
            self._update_execution_state(
                session,
                state='adapter_missing',
                detail=result.summary,
                last_action='execute',
            )
            session.status = AdaptiveSessionStatus.READY_TO_EXECUTE
            session.outcome = TaskOutcome(
                status=result.status,
                summary='La estrategia quedo lista, pero no hay un adaptador operativo real para ejecutar esta fase todavia.',
                next_actions=result.next_actions or ['Simular', 'Preparar Codex'],
                metadata={'mode': 'execute_waiting_adapter', **result.metadata},
            )
        else:
            self._update_execution_state(
                session,
                state='executing',
                detail='La fase operativa fue enviada al adaptador del dominio.',
                last_action='execute',
            )
            result = executor.execute(session)
            self._update_execution_state(
                session,
                state='executed' if result.status == RunStatus.SUCCESS else 'failed',
                detail=result.summary,
                last_action='execute',
            )
            session.status = (
                AdaptiveSessionStatus.COMPLETED
                if result.status == RunStatus.SUCCESS
                else AdaptiveSessionStatus.FAILED
                if result.status == RunStatus.FAILED
                else AdaptiveSessionStatus.READY_TO_EXECUTE
            )
            session.outcome = TaskOutcome(
                status=result.status,
                summary=result.summary,
                next_actions=result.next_actions,
                metadata={'mode': 'execute_executed', **result.metadata},
            )
        if session.playbook is not None:
            session.playbook.status = session.status
            session.playbook.next_phase = 'none' if session.status == AdaptiveSessionStatus.COMPLETED else 'execute'
        session.updated_at_utc = datetime.now(timezone.utc)
        return session

    def abort(self, session: AdaptiveSession) -> AdaptiveSession:
        self._update_execution_state(
            session,
            state='aborted',
            detail='La fase operativa fue abortada por el usuario.',
            last_action='abort',
        )
        session.status = AdaptiveSessionStatus.ABORTED
        session.outcome = TaskOutcome(
            status=RunStatus.CANCELLED,
            summary='La sesion adaptativa fue abortada por el usuario.',
            next_actions=['Puedes reenfocar la estrategia o abrir una nueva sesion.'],
            metadata={'mode': 'abort'},
        )
        if session.playbook is not None:
            session.playbook.status = AdaptiveSessionStatus.ABORTED
            session.playbook.next_phase = 'none'
        session.updated_at_utc = datetime.now(timezone.utc)
        return session

    def _approve_matching(self, session: AdaptiveSession, phase_key: str) -> AdaptiveSession:
        target = next((item for item in session.approval_checkpoints if item.phase_key == phase_key and item.decision == ApprovalDecision.PENDING), None)
        if target is None:
            return self.approve_next_phase(session)
        target.decision = ApprovalDecision.APPROVED
        target.decided_at_utc = datetime.now(timezone.utc)
        return self._refresh_status(session)

    def _refresh_status(self, session: AdaptiveSession) -> AdaptiveSession:
        session = self.annotate_execution_capability(session)
        session.status = AdaptiveSessionStatus.WAITING_APPROVAL if self._has_pending_approval(session) else AdaptiveSessionStatus.READY_TO_EXECUTE
        if session.playbook is not None:
            session.playbook.status = session.status
            session.playbook.next_phase = 'approval' if self._has_pending_approval(session) else 'execute'
        session.outcome = TaskOutcome(
            status=RunStatus.PARTIAL,
            summary='Aprobacion registrada. La estrategia sigue avanzando por fases.',
            next_actions=self._ready_next_actions(session) if not self._has_pending_approval(session) else ['Aprobar fase siguiente'],
            metadata={'mode': 'approval'},
        )
        session.updated_at_utc = datetime.now(timezone.utc)
        return session

    def _has_pending_approval(self, session: AdaptiveSession) -> bool:
        return any(item.decision == ApprovalDecision.PENDING for item in session.approval_checkpoints)

    def _execute_step(self, session: AdaptiveSession):
        if session.playbook is None:
            return None
        return next((item for item in session.playbook.steps if item.phase_key == 'execute'), None)

    def _execution_state(self, session: AdaptiveSession) -> dict[str, object]:
        state = session.metadata.get('execution_state')
        return dict(state) if isinstance(state, dict) else {}

    def _ready_next_actions(self, session: AdaptiveSession) -> list[str]:
        execution_state = self._execution_state(session)
        if bool(execution_state.get('simulation_only')):
            return ['Simular', 'Ver evolutivo']
        if bool(execution_state.get('executor_available')):
            return ['Simular', 'Ejecutar ahora']
        return ['Simular', 'Ver evolutivo', 'Preparar Codex']

    def _describe_execution_capability(self, session: AdaptiveSession, execute_step, executor_available: bool, simulation_only: bool) -> str:
        if execute_step is None:
            return 'La sesion no declaro una fase execute todavia.'
        if simulation_only:
            return 'La fase execute queda intencionalmente en simulacion o guiado porque el pack es sensible o de alto riesgo.'
        if executor_available:
            return f'Hay un adaptador operativo disponible ({getattr(self.executor, "name", "executor")}) para intentar la fase real.'
        return self.executor.describe(session)

    def _update_execution_state(self, session: AdaptiveSession, *, state: str, detail: str, last_action: str) -> None:
        execution_state = self._execution_state(session)
        execution_state.update(
            {
                'state': state,
                'detail': detail,
                'last_action': last_action,
                'updated_at_utc': datetime.now(timezone.utc).isoformat(),
            }
        )
        session.metadata['execution_state'] = execution_state
        execute_step = self._execute_step(session)
        if execute_step is not None:
            execute_step.metadata['execution_state'] = execution_state
            execute_step.detail = detail
