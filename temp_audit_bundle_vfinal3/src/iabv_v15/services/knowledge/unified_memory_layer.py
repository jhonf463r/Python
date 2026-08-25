from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import GoalContext, KnowledgeItem, RunRecord, TaskContext
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository


class UnifiedMemoryLayer:
    def __init__(self, knowledge_repository: KnowledgeRepository) -> None:
        self.knowledge_repository = knowledge_repository

    def build_snapshot(self, context: TaskContext) -> dict[str, Any]:
        capabilities = [
            {
                'capability_id': item.capability_id,
                'title': item.title,
                'status': item.status.value,
                'score': item.score,
                'site_id': item.site_id or '',
            }
            for item in context.capability_snapshot
        ]
        goal_context = self._goal_context_payload(context.goal_context)
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        return {
            'evidence': {
                'site_id': context.site_id or '',
                'site_display_name': context.site_display_name,
                'evidence_refs': list(context.evidence_summary),
                'recent_teachings': list(context.recent_teachings),
                'recent_incidents': list(context.recent_incidents),
                'recent_dossiers': list(context.recent_dossiers),
            },
            'learning': {
                'interaction_patterns': list(context.interaction_patterns),
                'knowledge_hits': list(context.knowledge_hits),
                'capabilities': capabilities,
                'experiment_insights': list(context.experiment_insights),
            },
            'operational': {
                'recent_runs': list(context.recent_runs),
                'session_readiness': dict(context.session_readiness),
                'live_audit': dict(context.live_audit),
            },
            'objectives': {
                'goal_context': goal_context,
                'objective': objective,
                'project': project,
                'task': task,
                'status': str(goal_context.get('status') or ''),
                'progress': float(goal_context.get('progress') or 0.0),
                'confidence': float(goal_context.get('confidence') or 0.0),
                'blocker': str(goal_context.get('blocker') or ''),
            },
        }

    def remember_run(self, run_record: RunRecord) -> KnowledgeItem:
        raw_output = dict(run_record.result.raw_output or {}) if isinstance(run_record.result.raw_output, dict) else {}
        decision_context = dict(raw_output.get('decision_context') or run_record.request.metadata.get('decision_context') or {})
        goal_context = self._goal_context_payload(decision_context.get('goal_context'))
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        route_kind = getattr(run_record.route, 'primary_kind', None)
        route_tag = route_kind.value if hasattr(route_kind, 'value') else 'role_route'
        tags = [
            route_tag,
            run_record.result.reasoning_mode.value,
        ]
        for extra in (
            str(run_record.request.goal_parameters.get('objective_id') or objective.get('objective_id') or '').strip(),
            str(run_record.request.goal_parameters.get('project_id') or project.get('objective_id') or '').strip(),
            str(run_record.request.goal_parameters.get('task_id') or task.get('objective_id') or '').strip(),
        ):
            if extra:
                tags.append(extra)
        item = KnowledgeItem(
            title=run_record.result.inferred_task,
            summary=run_record.result.summary,
            source_episode_id=run_record.request.metadata.get('episode_id'),
            task_label=run_record.result.inferred_task,
            confidence=run_record.result.confidence,
            tags=tags,
            payload={
                'route': run_record.route.model_dump(),
                'result': run_record.result.model_dump(),
                'decision_context': decision_context,
                'goal_parameters': dict(run_record.request.goal_parameters or {}),
                'goal_context': goal_context,
            },
        )
        return self.knowledge_repository.upsert(item)

    def _goal_context_payload(self, goal_context: GoalContext | dict[str, Any] | Any) -> dict[str, Any]:
        if isinstance(goal_context, GoalContext):
            return goal_context.model_dump(mode='json')
        if isinstance(goal_context, dict):
            return dict(goal_context)
        return {}
