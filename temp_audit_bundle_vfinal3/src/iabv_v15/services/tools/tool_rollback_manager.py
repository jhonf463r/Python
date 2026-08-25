from __future__ import annotations

from iabv_v15.domain.models import ApprovalDecision, ExecutionState, ToolCard, ToolResult, ToolTask, ToolTaskStatus
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest


class ToolRollbackManager:
    def __init__(self, capability_action_bridge: CapabilityActionBridge | None = None) -> None:
        self.capability_action_bridge = capability_action_bridge
    
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
        
        # F16: Default-deny authorization for protected rollback execution
        # All rollback execution requires authority authorization
        # Rollback uses the same capability as the original execution
        if self.capability_action_bridge is None:
            # Authority unavailable - reject rollback (fail-closed)
            return ExecutionState(
                state='rollback_failed',
                detail='Authority system is not available. Protected rollback requires authority process to be running.',
                executor_name='CapabilityActionBridge',
                sandboxed=False,
                validated=False,
                approval_decision=task.approval_decision,
                metadata={'authority_unavailable': True},
            )
        
        # Require capability for rollback execution (default-deny)
        if task.lease_id is None or task.action is None or task.target is None:
            # Missing capability fields - reject rollback (fail-closed)
            return ExecutionState(
                state='rollback_failed',
                detail='Protected rollback requires capability (lease_id, action, target). Task missing authority fields.',
                executor_name='CapabilityActionBridge',
                sandboxed=False,
                validated=False,
                approval_decision=task.approval_decision,
                metadata={
                    'authorization_required': True,
                    'lease_id': task.lease_id,
                    'action': task.action,
                    'target': task.target,
                },
            )
        
        # Authorize rollback action with capability
        auth_result = self.capability_action_bridge.authorize_action(
            ActionRequest(
                lease_id=task.lease_id,
                execution_id=task.execution_id,
                action=task.action,
                target=task.target,
            )
        )
        if not auth_result.authorized:
            # Authorization failed - reject rollback
            return ExecutionState(
                state='rollback_failed',
                detail=f'Rollback authorization failed: {auth_result.error or "Unknown error"}',
                executor_name='CapabilityActionBridge',
                sandboxed=False,
                validated=False,
                approval_decision=task.approval_decision,
                metadata={'authorization_error': auth_result.error},
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
