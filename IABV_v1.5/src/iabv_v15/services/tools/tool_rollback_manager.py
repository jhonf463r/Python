from __future__ import annotations

from iabv_v15.domain.models import ApprovalDecision, ExecutionState, ToolCard, ToolResult, ToolTask, ToolTaskStatus


class ToolRollbackManager:
    def attempt(self, *, card: ToolCard, task: ToolTask, result: ToolResult, adapter) -> ExecutionState:
        rollback_actions = list(task.rollback_actions)
        if not rollback_actions:
            return ExecutionState(
                state='rollback_unavailable',
                detail='La herramienta no define rollback_actions para esta tarea.',
                executor_name=card.adapter_key,
                sandboxed=False,
                validated=False,
                approval_decision=task.approval_decision,
            )
        rollback_task = task.model_copy(
            update={
                'status': ToolTaskStatus.ROLLED_BACK,
                'actions': rollback_actions,
                'rollback_actions': [],
                'execution_scope': 'read_only',
                'approval_decision': ApprovalDecision.APPROVED,
                'metadata': {
                    **task.metadata,
                    'rollback_origin_result_id': result.result_id,
                },
            }
        )
        try:
            payload = adapter.run(card, rollback_task, sandbox=False)
        except Exception as exc:
            return ExecutionState(
                state='rollback_failed',
                detail=f'Rollback lanzo una excepcion: {exc}',
                executor_name=card.adapter_key,
                sandboxed=False,
                validated=False,
                approval_decision=task.approval_decision,
                metadata={'rollback_exception': str(exc)},
            )
        success = bool(payload.get('success'))
        return ExecutionState(
            state='rolled_back' if success else 'rollback_failed',
            detail='Rollback ejecutado correctamente.' if success else str(payload.get('error_message') or 'El rollback no pudo completarse.'),
            executor_name=card.adapter_key,
            sandboxed=False,
            validated=success,
            approval_decision=task.approval_decision,
            metadata={
                'rollback_output_text': str(payload.get('output_text') or ''),
                'rollback_artifacts': list(payload.get('artifacts') or []),
                'rollback_metadata': dict(payload.get('metadata') or {}),
            },
        )
