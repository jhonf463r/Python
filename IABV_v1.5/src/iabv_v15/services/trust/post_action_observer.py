"""Post-action evidence boundary for the ToolTeach runtime.

This component records what the actor declared after execution.  It does not
promote that report into an independently observed or verified outcome; G3
performs its own filesystem observation and expected-versus-observed check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from iabv_v15.domain.models import ToolCard, ToolResult, ToolTask

if TYPE_CHECKING:
    from iabv_v15.services.tools.tool_memory import ToolMemory


class PostActionObserver:
    """Record a declared actor result without conflating it with world state."""

    def __init__(self, memory: ToolMemory) -> None:
        self.memory = memory

    def observe(self, *, result: ToolResult, task: ToolTask, card: ToolCard) -> ToolResult:
        self.memory.audit_event(
            tool_id=card.tool_id,
            task_id=task.task_id,
            action_type='post_action_actor_report',
            state='actor_reported_success' if result.success else 'actor_reported_failure',
            payload={
                'actor_reported_success': result.success,
                'result_id': result.result_id,
                'execution_state': result.execution_state.state,
                'observation_status': 'not_independently_observed',
                'verification_status': 'not_verified',
            },
        )
        return result
