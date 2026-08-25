from __future__ import annotations

from iabv_v15.domain.models import ApprovalDecision, ToolCard, ToolTask


class ToolApprovalPolicy:
    def evaluate(self, *, card: ToolCard, task: ToolTask) -> ToolTask:
        destructive = any(action.destructive for action in task.actions)
        requires = card.requires_human_approval or card.supports_write or task.execution_scope in {'write', 'destructive'} or destructive
        decision = task.approval_decision
        if not requires and decision == ApprovalDecision.PENDING:
            decision = ApprovalDecision.SKIPPED
        return task.model_copy(
            update={
                'approval_decision': decision,
                'metadata': {
                    **task.metadata,
                    'approval_required': requires,
                    'destructive': destructive,
                },
            }
        )
