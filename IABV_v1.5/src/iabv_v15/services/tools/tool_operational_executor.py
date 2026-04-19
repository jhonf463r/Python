from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import AdaptiveSession, ApprovalDecision, RunStatus, TaskRole, ToolTask
from iabv_v15.services.adaptive.execution_playbook_service import OperationalExecutorResult
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


class ToolOperationalExecutor:
    name = 'tool_local_first_executor'

    def __init__(self, tool_teach_service: ToolTeachService) -> None:
        self.tool_teach_service = tool_teach_service

    def supports(self, session: AdaptiveSession) -> bool:
        if not (session.intent.detected_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} or session.chosen_pack_id.startswith('tools.')):
            return False
        preview_task = self.tool_teach_service.build_task_for_session(session)
        card = self.tool_teach_service.registry.pick_card_for_task(preview_task)
        if card is None:
            return False
        adapter = self.tool_teach_service.adapters.get(card.adapter_key)
        return bool(adapter and adapter.is_available(card))

    def describe(self, session: AdaptiveSession) -> str:
        if not self.supports(session):
            pack = session.chosen_pack_title or session.chosen_pack_id or 'esta tarea'
            return f'No hay un executor de herramientas aplicable para {pack}; sigue faltando un adaptador operativo del dominio.'
        preview_task = self.tool_teach_service.build_task_for_session(session)
        card = self.tool_teach_service.registry.pick_card_for_task(preview_task)
        if card is None:
            return 'No hay una herramienta local registrada para esta tarea todavia.'
        approval_required = card.requires_human_approval or card.supports_write or preview_task.execution_scope in {'write', 'destructive'}
        if approval_required and any(item.decision == ApprovalDecision.PENDING for item in session.approval_checkpoints):
            return f'{card.title} esta listo para sandbox, pero necesita aprobacion humana antes de ejecutar fuera del sandbox.'
        return f'{card.title} esta listo para ejecutar la tarea en local-first, pasando primero por sandbox y validacion.'

    def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
        if not self.supports(session):
            return OperationalExecutorResult(executed=False, status=RunStatus.PARTIAL, summary=self.describe(session), next_actions=['Simular', 'Preparar Codex'], metadata={'mode': 'adapter_missing'})
        task = self.tool_teach_service.build_task_for_session(session)
        approved = not any(item.decision == ApprovalDecision.PENDING for item in session.approval_checkpoints)
        result = self.tool_teach_service.execute_task(task, approved=approved)
        metadata = {
            'mode': result.execution_state.state,
            'tool_id': result.tool_id,
            'validation_status': result.validation_status.value,
            'tool_result_id': result.result_id,
            'rollback_state': result.rollback_state.state if result.rollback_state is not None else '',
            'rollback_detail': result.rollback_state.detail if result.rollback_state is not None else '',
        }
        next_actions = ['Ver evolutivo']
        if result.execution_state.state == 'waiting_approval':
            next_actions = ['Aprobar estrategia', 'Aprobar fase siguiente']
        elif result.success:
            next_actions = ['Ver evidencia relacionada', 'Revisar resultado']
        elif result.rollback_state is not None and result.rollback_state.state == 'rolled_back':
            next_actions = ['Revisar rollback', 'Ver evolutivo']
        elif result.execution_state.state == 'adapter_missing':
            next_actions = ['Preparar Codex', 'Ver evolutivo']
        return OperationalExecutorResult(
            executed=result.success and result.execution_state.state == 'executed',
            status=RunStatus.SUCCESS if result.success and result.execution_state.state == 'executed' else RunStatus.PARTIAL if result.execution_state.state in {'waiting_approval', 'sandbox_pass'} else RunStatus.FAILED,
            summary=result.output_text or result.execution_state.detail or result.error_message or 'Herramienta local ejecutada.',
            next_actions=next_actions,
            metadata=metadata,
        )

    def execute_tool_call(
        self,
        tool_call: Any,
        *,
        session: AdaptiveSession | None = None,
    ) -> OperationalExecutorResult:
        """Execute an explicit ``ToolCall`` emitted by an LLM.

        Unlike :meth:`execute`, which infers the task from the
        ``AdaptiveSession`` context, this method honours the tool identity and
        arguments the LLM requested. It builds a ``ToolTask`` from
        ``tool_call.name`` and ``tool_call.args`` and routes it through
        ``ToolTeachService.execute_task`` so the correct adapter is selected.
        """
        tool_id = str(getattr(tool_call, 'name', '') or '').strip()
        raw_args = getattr(tool_call, 'args', None) or {}
        args = dict(raw_args) if isinstance(raw_args, dict) else {}
        if not tool_id:
            return OperationalExecutorResult(
                executed=False,
                status=RunStatus.FAILED,
                summary='tool_call sin nombre de herramienta.',
                next_actions=['Ver evolutivo'],
                metadata={'mode': 'invalid_tool_call'},
            )

        objective_parts = [
            str(value) for value in args.values()
            if isinstance(value, (str, int, float))
        ]
        objective = ' '.join(objective_parts) if objective_parts else tool_id

        pack_id = getattr(session, 'chosen_pack_id', '') or ''
        site_id = getattr(session, 'site_id', None)
        session_id = getattr(session, 'session_id', None)
        task = ToolTask(
            tool_id=tool_id,
            title=f'tool_call:{tool_id}',
            objective=objective,
            pack_id=pack_id,
            site_id=site_id,
            session_id=session_id,
            metadata={'tool_call_args': args, 'source': 'llm_tool_call'},
        )

        approved = True
        if session is not None:
            approved = not any(
                item.decision == ApprovalDecision.PENDING
                for item in session.approval_checkpoints
            )

        result = self.tool_teach_service.execute_task(task, approved=approved)
        execution_state = getattr(result.execution_state, 'state', '') or ''
        metadata = {
            'mode': execution_state,
            'tool_id': result.tool_id,
            'tool_call_args': args,
            'validation_status': result.validation_status.value,
            'tool_result_id': result.result_id,
            'rollback_state': result.rollback_state.state if result.rollback_state is not None else '',
            'rollback_detail': result.rollback_state.detail if result.rollback_state is not None else '',
        }
        next_actions = ['Ver evolutivo']
        if execution_state == 'waiting_approval':
            next_actions = ['Aprobar estrategia', 'Aprobar fase siguiente']
        elif result.success:
            next_actions = ['Ver evidencia relacionada', 'Revisar resultado']
        elif result.rollback_state is not None and result.rollback_state.state == 'rolled_back':
            next_actions = ['Revisar rollback', 'Ver evolutivo']
        elif execution_state == 'adapter_missing':
            next_actions = ['Preparar Codex', 'Ver evolutivo']

        if result.success and execution_state == 'executed':
            status = RunStatus.SUCCESS
        elif execution_state in {'waiting_approval', 'sandbox_pass'}:
            status = RunStatus.PARTIAL
        else:
            status = RunStatus.FAILED

        return OperationalExecutorResult(
            executed=result.success and execution_state == 'executed',
            status=status,
            summary=result.output_text or getattr(result.execution_state, 'detail', '') or result.error_message or f'Herramienta {tool_id} ejecutada.',
            next_actions=next_actions,
            metadata=metadata,
        )

