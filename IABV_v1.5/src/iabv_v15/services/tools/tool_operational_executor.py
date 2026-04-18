from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, ApprovalDecision, RunStatus, TaskRole, ToolType
from iabv_v15.services.adaptive.execution_playbook_service import OperationalExecutorResult
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


_LOCAL_CHAT_PACK_IDS = frozenset({'knowledge.query', 'general.assistance'})
_LOCAL_CHAT_INTENT_KEYS = frozenset({'knowledge.query', 'general.assistance'})
_LOCAL_CHAT_ROLES = frozenset({TaskRole.KNOWLEDGE, TaskRole.ANALYTICS, TaskRole.RESEARCH})


class ToolOperationalExecutor:
    name = 'tool_local_first_executor'

    def __init__(self, tool_teach_service: ToolTeachService) -> None:
        self.tool_teach_service = tool_teach_service

    def _is_tool_flow(self, session: AdaptiveSession) -> bool:
        return session.intent.detected_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} or session.chosen_pack_id.startswith('tools.')

    def _is_local_chat_flow(self, session: AdaptiveSession) -> bool:
        pack_id = session.chosen_pack_id or ''
        intent_key = session.intent.intent_key or ''
        if pack_id in _LOCAL_CHAT_PACK_IDS:
            return True
        if intent_key in _LOCAL_CHAT_INTENT_KEYS:
            return True
        if session.intent.detected_role in _LOCAL_CHAT_ROLES and not pack_id:
            return True
        return False

    def supports(self, session: AdaptiveSession) -> bool:
        tool_flow = self._is_tool_flow(session)
        local_chat_flow = self._is_local_chat_flow(session)
        if not (tool_flow or local_chat_flow):
            return False
        preview_task = self.tool_teach_service.build_task_for_session(session)
        card = self.tool_teach_service.registry.pick_card_for_task(preview_task)
        if card is None:
            return False
        adapter = self.tool_teach_service.adapters.get(card.adapter_key)
        if not (adapter and adapter.is_available(card)):
            return False
        if tool_flow:
            return True
        return card.tool_type == ToolType.LLM_LOCAL

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

