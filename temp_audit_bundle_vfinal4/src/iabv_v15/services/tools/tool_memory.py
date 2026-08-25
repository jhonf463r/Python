from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import ToolCard, ToolResult, ToolTask, ToolValidationStatus
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService


class ToolMemory:
    def __init__(self, repository: ToolRecordRepository, interaction_learning_service: InteractionLearningService | None = None):
        self.repository = repository
        self.interaction_learning_service = interaction_learning_service

    def remember_task(self, task: ToolTask) -> ToolTask:
        task.metadata.setdefault('updated_at_utc', datetime.now(timezone.utc).isoformat())
        task.metadata.setdefault('created_at_utc', task.metadata['updated_at_utc'])
        return self.repository.save_task(task)

    def audit_event(self, *, tool_id: str, task_id: str | None, action_type: str, state: str, payload: dict[str, Any]) -> str:
        return self.repository.log_execution(
            tool_id=tool_id,
            task_id=task_id,
            action_type=action_type,
            state=state,
            payload=payload,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def remember_result(self, card: ToolCard, task: ToolTask, result: ToolResult) -> ToolResult:
        goal_metadata = self._goal_metadata(task.metadata)
        if goal_metadata:
            result = result.model_copy(update={'metadata': {**result.metadata, **goal_metadata}})
        self.repository.save_result(result)
        updated_card = card.model_copy(
            update={
                'success_count': card.success_count + (1 if result.success else 0),
                'failure_count': card.failure_count + (0 if result.success else 1),
                'last_result_id': result.result_id,
                'last_validated_at_utc': result.created_at_utc,
                'validation_status': result.validation_status,
                'metadata': {
                    **card.metadata,
                    'updated_at_utc': result.created_at_utc.isoformat(),
                },
            }
        )
        self.repository.save_card(updated_card)
        self.repository.log_execution(
            tool_id=task.tool_id,
            task_id=task.task_id,
            action_type='task_result',
            state=result.execution_state.state,
            payload=result.model_dump(mode='json'),
            created_at_utc=result.created_at_utc.isoformat(),
        )
        if self.interaction_learning_service is not None:
            pattern = self.interaction_learning_service.learn_from_execution(card=updated_card, task=task, result=result)
            result = result.model_copy(
                update={
                    'metadata': {
                        **result.metadata,
                        'interaction_pattern_id': pattern.pattern_id,
                        'interaction_channel': pattern.channel.value,
                        'interaction_episode_id': str(pattern.metadata.get('last_interaction_episode_id') or ''),
                        'mode_selection': dict(task.metadata.get('mode_selection') or {}),
                        'selected_mode': str(task.metadata.get('selected_mode') or ''),
                        'selector_reason': str(task.metadata.get('selector_reason') or ''),
                        'reuse_guard_active': bool(task.metadata.get('reuse_guard_active')),
                    }
                }
            )
            self.repository.save_result(result)
        return result

    def mark_card_blocked(self, card: ToolCard, reason: str) -> ToolCard:
        updated = card.model_copy(
            update={
                'validation_status': ToolValidationStatus.BLOCKED,
                'available': False,
                'metadata': {**card.metadata, 'blocked_reason': reason, 'updated_at_utc': datetime.now(timezone.utc).isoformat()},
            }
        )
        return self.repository.save_card(updated)

    def _goal_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        goal_parameters = dict(metadata.get('goal_parameters') or {}) if isinstance(metadata, dict) else {}
        goal_context = dict(metadata.get('goal_context') or {}) if isinstance(metadata, dict) else {}
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        return {
            'objective_id': str(goal_parameters.get('objective_id') or objective.get('objective_id') or ''),
            'project_id': str(goal_parameters.get('project_id') or project.get('objective_id') or ''),
            'task_goal_id': str(goal_parameters.get('task_id') or task.get('objective_id') or ''),
            'goal_progress': float(goal_parameters.get('goal_progress') or goal_context.get('progress') or 0.0),
            'goal_status': str(goal_parameters.get('goal_status') or goal_context.get('status') or ''),
        }

    def history_for_tool(self, tool_id: str, limit: int = 10) -> dict[str, Any]:
        results = [item.model_dump(mode='json') for item in self.repository.list_results(tool_id=tool_id, limit=limit)]
        log = self.repository.list_log(tool_id=tool_id, limit=limit)
        return {'results': results, 'log': log}
