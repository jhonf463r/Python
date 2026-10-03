from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, ApprovalDecision, RunStatus, TaskRole
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
        causal_correlation = self._causal_correlation_manifest(task=task, session=session)
        approved = not any(item.decision == ApprovalDecision.PENDING for item in session.approval_checkpoints)
        result = self.tool_teach_service.execute_task(task, approved=approved)
        trace = dict(result.metadata.get('ia_trace_entry') or {})
        card = self.tool_teach_service.registry.get_card(result.tool_id)
        execute_step = next(
            (step for step in (session.playbook.steps if session.playbook is not None else []) if step.phase_key == 'execute'),
            None,
        )
        metadata = {
            'mode': result.execution_state.state,
            'tool_id': result.tool_id,
            'tool_label': card.title if card is not None else result.tool_id,
            'tool_type': result.tool_type.value,
            'adapter_key': result.execution_state.executor_name,
            'tool_task_id': result.task_id,
            'tool_result_id': result.result_id,
            'required_capability_id': str(execute_step.capability_id or '') if execute_step is not None else '',
            'required_action_types': [action.action_type.value for action in task.actions],
            'tool_capabilities': list(card.capabilities) if card is not None else [],
            'assistant_kind': str(trace.get('actual_assistant_kind') or result.metadata.get('assistant_kind') or ''),
            'assistant_configuration': dict(trace.get('assistant_configuration') or result.metadata.get('assistant_configuration') or {}),
            'config_signature': str(trace.get('config_signature') or result.metadata.get('config_signature') or ''),
            'route': str(trace.get('route') or ''),
            'comparison_scope_key': str(trace.get('comparison_scope_key') or task.metadata.get('comparison_scope_key') or ''),
            'validation_status': result.validation_status.value,
            'rollback_state': result.rollback_state.state if result.rollback_state is not None else '',
            'rollback_detail': result.rollback_state.detail if result.rollback_state is not None else '',
        }
        if causal_correlation is not None:
            metadata['causal_correlation'] = causal_correlation
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

    @staticmethod
    def _causal_correlation_manifest(*, task, session: AdaptiveSession) -> dict[str, object] | None:
        """Bind a declared observable marker to the actual task action IDs.

        This records the pre-execution task contract only. The independent
        postcondition observer must still observe the same marker before the
        verifier can attribute the effect.
        """
        playbook = session.playbook
        if playbook is None:
            return None
        execute_step = next((step for step in playbook.steps if step.phase_key == 'execute'), None)
        expectation = execute_step.postcondition if execute_step is not None else None
        if expectation is None:
            return None
        correlation_id = str(expectation.correlation_id or '').strip()
        correlation_field = str(expectation.correlation_field or '').strip()
        if not correlation_id or not correlation_field:
            return None
        action_ids = [
            str(action.action_id)
            for action in task.actions
            if str(action.correlation_id or '').strip() == correlation_id
        ]
        if not action_ids:
            return None
        return {
            'task_id': str(task.task_id),
            'action_ids': action_ids,
            'correlation_id': correlation_id,
            'correlation_field': correlation_field,
        }

