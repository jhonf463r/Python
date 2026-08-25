from __future__ import annotations

from iabv_v15.domain.models import ExecutionState, ToolCard, ToolResult, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import ToolAdapter
from iabv_v15.services.tools.tool_validator import ToolValidator


class ToolSandbox:
    def __init__(self, validator: ToolValidator):
        self.validator = validator

    def run(self, *, card: ToolCard, task: ToolTask, adapter: ToolAdapter) -> ToolResult:
        payload = adapter.run(card, task, sandbox=True)
        result = ToolResult(
            task_id=task.task_id,
            tool_id=card.tool_id,
            tool_type=card.tool_type,
            success=bool(payload.get('success')),
            execution_state=ExecutionState(
                state='sandboxed',
                detail='Sandbox local de herramienta ejecutado.',
                executor_name=card.adapter_key,
                sandboxed=True,
                destructive_blocked=bool((payload.get('metadata') or {}).get('blocked')),
                approval_decision=task.approval_decision,
                metadata=payload.get('metadata') or {},
            ),
            output_text=str(payload.get('output_text') or ''),
            extracted_data=dict(payload.get('extracted_data') or {}),
            artifacts=list(payload.get('artifacts') or []),
            error_message=str(payload.get('error_message') or ''),
            execution_ms=int(payload.get('execution_ms') or 0),
            metadata={'sandbox': True},
        )
        return self.validator.validate(card=card, task=task, result=result, sandbox=True)
