from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, ApprovalDecision, RunStatus, TaskRole
from iabv_v15.services.adaptive.execution_playbook_service import OperationalExecutorResult
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_execution


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
        
        # F14: Acquire capability before execution
        # FAIL-CLOSED: Reject execution if capability acquisition fails
        try:
            capability = acquire_capability_for_execution(
                action=session.action or "EXECUTE",
                target=session.target or "tool",
                requested_scope="tool:execute",
                invocation_id=f"tool_execution_{task.task_id}",
                episode_id=None,
                session_id=session.session_id
            )
            # Extend task with authority context
            task = task.model_copy(update={
                'run_id': capability['run_id'],
                'execution_id': capability['execution_id'],
                'lease_id': capability['lease_id'],
                'action': capability['action'],
                'target': capability['target'],
            })
        except Exception as e:
            # Capability acquisition failed - reject execution (fail-closed)
            return OperationalExecutorResult(
                success=False,
                tool_result=ToolResult(
                    task_id=task.task_id,
                    tool_id=task.tool_id,
                    tool_type="unknown",
                    success=False,
                    validation_status=ToolValidationStatus.BLOCKED,
                    execution_state=ExecutionState(
                        state='capability_acquisition_failed',
                        detail=f'Capability acquisition failed: {str(e)}. Protected execution requires authority process to be running.',
                        executor_name='CapabilityLifecycle',
                        sandboxed=False,
                        destructive_blocked=True,
                    ),
                    error_message='capability_acquisition_failed',
                )
            )
        
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

