from __future__ import annotations

from iabv_v15.domain.models import ApprovalDecision, ExecutionState, ToolCard, ToolResult, ToolTask, ToolValidationStatus


class ToolValidator:
    def validate(self, *, card: ToolCard, task: ToolTask, result: ToolResult, sandbox: bool) -> ToolResult:
        validation_status = result.validation_status
        state = result.execution_state.state or ('sandboxed' if sandbox else 'executed')
        execution_metadata = dict(result.execution_state.metadata or {})
        awaiting_response = bool(
            (
                execution_metadata.get('manual_pasteback_required')
                and not execution_metadata.get('response_captured')
                and str(execution_metadata.get('response_capture_mode') or '').strip().lower() == 'manual_pasteback'
            )
            or execution_metadata.get('response_capture_pending')
        )
        if result.execution_state.destructive_blocked:
            validation_status = ToolValidationStatus.BLOCKED
            state = 'blocked'
        elif awaiting_response:
            validation_status = ToolValidationStatus.UNVALIDATED
            state = 'awaiting_response'
        elif sandbox and result.success:
            validation_status = ToolValidationStatus.SANDBOX_PASS
            state = 'sandbox_pass'
        elif sandbox and not result.success:
            validation_status = ToolValidationStatus.SANDBOX_FAIL
            state = 'sandbox_fail'
        elif result.success and task.approval_decision == ApprovalDecision.APPROVED:
            validation_status = ToolValidationStatus.APPROVED
            state = 'executed'
        elif result.success and task.execution_scope == 'read_only':
            validation_status = ToolValidationStatus.APPROVED
            state = 'executed'
        elif result.success:
            validation_status = ToolValidationStatus.SANDBOX_PASS
        updated_state = result.execution_state.model_copy(
            update={
                'state': state,
                'validated': result.success,
                'approval_decision': task.approval_decision,
                'sandboxed': sandbox,
            }
        )
        return result.model_copy(
            update={
                'validation_status': validation_status,
                'execution_state': updated_state,
            }
        )

