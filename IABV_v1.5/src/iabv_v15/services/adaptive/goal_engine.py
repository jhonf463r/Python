from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    GoalContext,
    InferenceRequest,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
)
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository


class GoalEngine:
    def __init__(self, repository: ObjectiveRepository) -> None:
        self.repository = repository

    def _should_keep_persistent_goal_context(self, *, request: InferenceRequest, session: AdaptiveSession) -> bool:
        params = dict(request.goal_parameters or {})
        has_explicit_goal = any(str(params.get(key) or '').strip() for key in ('objective_id', 'project_id', 'task_id'))
        if has_explicit_goal:
            return True
        normalized_goal = ' '.join(str(request.user_goal or '').lower().split())
        conversational_prompt = (
            any(phrase in normalized_goal for phrase in (
                'que sabes hacer',
                'qué sabes hacer',
                'que puedes hacer',
                'qué puedes hacer',
                'en que puedes ayudar',
                'en qué puedes ayudar',
                'quien eres',
                'quién eres',
                'como funcionas',
                'cómo funcionas',
            ))
            or (len(normalized_goal.split()) <= 4 and any(normalized_goal.startswith(prefix) for prefix in ('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches')))
        )
        return not (
            session.intent.intent_key in {'general.assistance', 'knowledge.query'}
            and session.intent.disposition.value in {'answer_now', 'need_info'}
            and conversational_prompt
        )

    def attach_session_goal_context(self, *, request: InferenceRequest, session: AdaptiveSession) -> GoalContext:
        if not self._should_keep_persistent_goal_context(request=request, session=session):
            context = GoalContext(
                active_title=str(request.user_goal or session.intent.title),
                status=ObjectiveStatus.PENDING.value,
                trend='conversacional',
                metadata={
                    'source': 'transient_chat_goal',
                    'persistent': False,
                    'intent_key': session.intent.intent_key,
                    'site_id': session.context.site_id or session.intent.site_hint or request.site_hint or '',
                },
            )
            session.context.goal_context = context
            session.context.metadata['goal_context'] = context.model_dump(mode='json')
            merged_goal_parameters = {**dict(request.goal_parameters or {}), **self.build_goal_parameters(context)}
            session.metadata['goal_parameters'] = merged_goal_parameters
            session.metadata['goal_context'] = context.model_dump(mode='json')
            session.context.metadata['goal_parameters'] = merged_goal_parameters
            return context
        site_id = session.context.site_id or session.intent.site_hint or request.site_hint
        objective = self._resolve_objective(
            kind=ObjectiveNodeKind.OBJECTIVE,
            explicit_id=str(request.goal_parameters.get('objective_id') or ''),
            title=str(request.goal_parameters.get('objective_title') or request.user_goal or session.intent.title),
            site_id=site_id,
            parent_id=None,
            root_id=None,
            priority=int(request.goal_parameters.get('objective_priority') or request.goal_parameters.get('priority') or 50),
            summary=session.intent.summary,
            metadata={
                'user_goal': request.user_goal,
                'intent_key': session.intent.intent_key,
                'domain_hint': session.intent.domain_hint,
            },
        )
        project_title = str(
            request.goal_parameters.get('project_title')
            or request.goal_parameters.get('project')
            or session.intent.title
            or request.user_goal
        )
        project = self._resolve_objective(
            kind=ObjectiveNodeKind.PROJECT,
            explicit_id=str(request.goal_parameters.get('project_id') or ''),
            title=project_title,
            site_id=site_id,
            parent_id=objective.objective_id,
            root_id=objective.objective_id,
            priority=int(request.goal_parameters.get('project_priority') or request.goal_parameters.get('priority') or objective.priority),
            summary=session.intent.summary,
            metadata={
                'user_goal': request.user_goal,
                'intent_key': session.intent.intent_key,
                'site_display_name': session.context.site_display_name,
            },
        )
        task_title = str(request.goal_parameters.get('task_title') or session.intent.title or request.user_goal)
        task = self._resolve_objective(
            kind=ObjectiveNodeKind.TASK,
            explicit_id=str(request.goal_parameters.get('task_id') or ''),
            title=task_title,
            site_id=site_id,
            parent_id=project.objective_id,
            root_id=objective.objective_id,
            priority=int(request.goal_parameters.get('task_priority') or request.goal_parameters.get('priority') or project.priority),
            summary=session.intent.summary,
            metadata={
                'user_goal': request.user_goal,
                'intent_key': session.intent.intent_key,
                'pack_id': session.chosen_pack_id,
                'pack_title': session.chosen_pack_title,
            },
        )
        context = self._synchronize_context(objective=objective, project=project, task=task, session=session)
        session.context.goal_context = context
        session.context.metadata['goal_context'] = context.model_dump(mode='json')
        merged_goal_parameters = {**dict(request.goal_parameters or {}), **self.build_goal_parameters(context)}
        session.metadata['goal_parameters'] = merged_goal_parameters
        session.metadata['goal_context'] = context.model_dump(mode='json')
        session.context.metadata['goal_parameters'] = merged_goal_parameters
        return context

    def sync_session(self, session: AdaptiveSession) -> GoalContext | None:
        context_payload = session.metadata.get('goal_context') or session.context.metadata.get('goal_context')
        context = GoalContext.model_validate(context_payload) if isinstance(context_payload, dict) and context_payload else session.context.goal_context
        if not context.objective and not context.task and not context.project:
            return None
        objective = self.repository.get(str(context.objective.get('objective_id') or '')) if context.objective else None
        project = self.repository.get(str(context.project.get('objective_id') or '')) if context.project else None
        task = self.repository.get(str(context.task.get('objective_id') or '')) if context.task else None
        if objective is None or project is None or task is None:
            return None
        refreshed = self._synchronize_context(objective=objective, project=project, task=task, session=session)
        session.context.goal_context = refreshed
        session.context.metadata['goal_context'] = refreshed.model_dump(mode='json')
        session.metadata['goal_context'] = refreshed.model_dump(mode='json')
        session.metadata['goal_parameters'] = {**dict(session.metadata.get('goal_parameters') or {}), **self.build_goal_parameters(refreshed)}
        return refreshed

    def build_goal_parameters(self, context: GoalContext) -> dict[str, Any]:
        objective = dict(context.objective or {})
        project = dict(context.project or {})
        task = dict(context.task or {})
        return {
            'objective_id': str(objective.get('objective_id') or ''),
            'objective_title': str(objective.get('title') or context.active_title or ''),
            'project_id': str(project.get('objective_id') or ''),
            'project_title': str(project.get('title') or ''),
            'task_id': str(task.get('objective_id') or ''),
            'task_title': str(task.get('title') or ''),
            'goal_status': str(context.status or ''),
            'goal_progress': float(context.progress or 0.0),
            'goal_confidence': float(context.confidence or 0.0),
            'goal_blocker': str(context.blocker or ''),
        }

    def _resolve_objective(
        self,
        *,
        kind: ObjectiveNodeKind,
        explicit_id: str,
        title: str,
        site_id: str | None,
        parent_id: str | None,
        root_id: str | None,
        priority: int,
        summary: str,
        metadata: dict[str, Any],
    ) -> ObjectiveNode:
        existing = self.repository.get(explicit_id) if explicit_id else None
        if existing is None:
            matches = self.repository.find_equivalent(
                kind=kind,
                title=title,
                parent_id=parent_id,
                root_id=root_id,
                site_id=site_id,
                limit=3,
            )
            existing = matches[0] if matches else None
        if existing is None:
            existing = ObjectiveNode(
                kind=kind,
                title=title.strip() or kind.value.title(),
                summary=summary,
                parent_id=parent_id,
                root_id=root_id or '',
                site_id=site_id,
                priority=priority,
                status=ObjectiveStatus.ACTIVE,
                progress=0.05 if kind == ObjectiveNodeKind.OBJECTIVE else 0.0,
                confidence=0.0,
                metadata=dict(metadata),
            )
            if not existing.root_id:
                existing = existing.model_copy(update={'root_id': existing.objective_id if parent_id is None else (root_id or '')})
            return self.repository.save(existing)
        updated = existing.model_copy(
            update={
                'title': title.strip() or existing.title,
                'summary': summary or existing.summary,
                'site_id': site_id or existing.site_id,
                'priority': priority if priority is not None else existing.priority,
                'parent_id': parent_id if parent_id is not None else existing.parent_id,
                'root_id': existing.root_id or root_id or (existing.objective_id if existing.parent_id is None else ''),
                'status': existing.status if existing.status != ObjectiveStatus.COMPLETED else ObjectiveStatus.COMPLETED,
                'metadata': {**dict(existing.metadata or {}), **metadata},
                'updated_at_utc': datetime.now(timezone.utc),
            }
        )
        return self.repository.save(updated)

    def _synchronize_context(self, *, objective: ObjectiveNode, project: ObjectiveNode, task: ObjectiveNode, session: AdaptiveSession) -> GoalContext:
        task_node = self._apply_session_progress(task, session=session, level='task')
        subtask_nodes = self._sync_subtasks(task_node=task_node, objective_id=objective.objective_id, session=session)
        project_progress = self._rollup_progress(subtask_nodes or [task_node])
        project_node = self.repository.save(
            project.model_copy(
                update={
                    'status': self._rollup_status([task_node] + subtask_nodes) if subtask_nodes else task_node.status,
                    'progress': project_progress,
                    'blocker': task_node.blocker,
                    'confidence': max(float(project.confidence or 0.0), float(task_node.confidence or 0.0)),
                    'evidence_refs': self._merge_refs(project.evidence_refs, task_node.evidence_refs),
                    'updated_at_utc': datetime.now(timezone.utc),
                }
            )
        )
        objective_progress = self._rollup_progress([project_node, task_node])
        objective_node = self.repository.save(
            objective.model_copy(
                update={
                    'status': self._rollup_status([project_node, task_node] + subtask_nodes),
                    'progress': objective_progress,
                    'blocker': task_node.blocker,
                    'confidence': max(float(objective.confidence or 0.0), float(project_node.confidence or 0.0), float(task_node.confidence or 0.0)),
                    'evidence_refs': self._merge_refs(objective.evidence_refs, project_node.evidence_refs, task_node.evidence_refs),
                    'updated_at_utc': datetime.now(timezone.utc),
                }
            )
        )
        active_title = task_node.title or project_node.title or objective_node.title
        progress = max(float(task_node.progress or 0.0), float(project_node.progress or 0.0), float(objective_node.progress or 0.0))
        confidence = max(float(task_node.confidence or 0.0), float(project_node.confidence or 0.0), float(objective_node.confidence or 0.0), float(session.intent.confidence or 0.0))
        status = task_node.status.value if task_node.status != ObjectiveStatus.PENDING else project_node.status.value
        blocker = task_node.blocker or project_node.blocker or objective_node.blocker
        if status == ObjectiveStatus.COMPLETED.value:
            trend = 'completado'
        elif blocker:
            trend = 'bloqueado'
        elif progress >= 0.7:
            trend = 'avanzando'
        elif progress > 0.0:
            trend = 'en curso'
        else:
            trend = 'iniciado'
        return GoalContext(
            objective=objective_node.model_dump(mode='json'),
            project=project_node.model_dump(mode='json'),
            task=task_node.model_dump(mode='json'),
            subtasks=[item.model_dump(mode='json') for item in subtask_nodes],
            active_node_id=task_node.objective_id,
            active_title=active_title,
            priority=task_node.priority,
            status=status,
            progress=round(progress, 4),
            blocker=blocker,
            confidence=round(confidence, 4),
            trend=trend,
            evidence_refs=self._merge_refs(objective_node.evidence_refs, project_node.evidence_refs, task_node.evidence_refs),
            metadata={
                'session_id': session.session_id,
                'intent_key': session.intent.intent_key,
                'pack_id': session.chosen_pack_id,
                'site_id': session.context.site_id or session.intent.site_hint or '',
            },
        )

    def _apply_session_progress(self, node: ObjectiveNode, *, session: AdaptiveSession, level: str) -> ObjectiveNode:
        status, progress, blocker = self._progress_from_session(session)
        live_audit = dict(session.context.live_audit or {})
        confidence = max(
            float(node.confidence or 0.0),
            float(session.intent.confidence or 0.0),
            float(live_audit.get('confidence') or 0.0),
        )
        evidence = self._merge_refs(node.evidence_refs, session.evidence_refs)
        if session.pending_issue_id:
            evidence.append(f'pending:{session.pending_issue_id}')
        if session.run_id:
            evidence.append(f'run:{session.run_id}')
        updated = node.model_copy(
            update={
                'status': status,
                'progress': progress,
                'blocker': blocker,
                'confidence': round(min(0.99, confidence), 4),
                'summary': session.outcome.summary if session.outcome is not None and session.outcome.summary else (session.intent.summary or node.summary),
                'evidence_refs': evidence[:12],
                'metadata': {
                    **dict(node.metadata or {}),
                    'level': level,
                    'session_id': session.session_id,
                    'intent_key': session.intent.intent_key,
                    'pack_id': session.chosen_pack_id,
                    'status': session.status.value,
                },
                'updated_at_utc': datetime.now(timezone.utc),
            }
        )
        return self.repository.save(updated)

    def _sync_subtasks(self, *, task_node: ObjectiveNode, objective_id: str, session: AdaptiveSession) -> list[ObjectiveNode]:
        if session.playbook is None or not session.playbook.steps:
            return self.repository.list_children(task_node.objective_id, kind=ObjectiveNodeKind.SUBTASK, limit=20)
        step_nodes: list[ObjectiveNode] = []
        next_phase = str(session.playbook.next_phase or '').strip().lower()
        for index, step in enumerate(session.playbook.steps):
            existing_matches = self.repository.find_equivalent(
                kind=ObjectiveNodeKind.SUBTASK,
                title=step.title,
                parent_id=task_node.objective_id,
                root_id=objective_id,
                site_id=task_node.site_id,
                limit=2,
            )
            existing = existing_matches[0] if existing_matches else None
            if session.status == AdaptiveSessionStatus.COMPLETED:
                step_status = ObjectiveStatus.COMPLETED
                step_progress = 1.0
            elif next_phase and str(step.phase_key or '').strip().lower() == next_phase:
                step_status = ObjectiveStatus.ACTIVE
                step_progress = 0.6
            elif index == 0 and session.status in {AdaptiveSessionStatus.ACTIVE if hasattr(AdaptiveSessionStatus, 'ACTIVE') else AdaptiveSessionStatus.PLANNED}:  # pragma: no cover
                step_status = ObjectiveStatus.ACTIVE
                step_progress = 0.4
            elif session.status in {AdaptiveSessionStatus.EXECUTING, AdaptiveSessionStatus.READY_TO_EXECUTE, AdaptiveSessionStatus.WAITING_APPROVAL} and index == 0:
                step_status = ObjectiveStatus.ACTIVE
                step_progress = 0.45
            elif session.status in {AdaptiveSessionStatus.FAILED, AdaptiveSessionStatus.ABORTED, AdaptiveSessionStatus.NEED_INFO}:
                step_status = ObjectiveStatus.BLOCKED if index == 0 else ObjectiveStatus.PENDING
                step_progress = 0.2 if index == 0 else 0.0
            else:
                step_status = ObjectiveStatus.PENDING
                step_progress = 0.0
            payload = ObjectiveNode(
                objective_id=existing.objective_id if existing is not None else ObjectiveNode(title=step.title).objective_id,
                kind=ObjectiveNodeKind.SUBTASK,
                title=step.title,
                summary=step.detail or step.description,
                parent_id=task_node.objective_id,
                root_id=objective_id,
                site_id=task_node.site_id,
                priority=task_node.priority + index + 1,
                status=step_status if existing is None or existing.status != ObjectiveStatus.COMPLETED else existing.status,
                progress=1.0 if existing is not None and existing.status == ObjectiveStatus.COMPLETED else step_progress,
                blocker=task_node.blocker if step_status == ObjectiveStatus.BLOCKED else '',
                confidence=float(task_node.confidence or 0.0),
                evidence_refs=self._merge_refs(list(existing.evidence_refs) if existing is not None else [], task_node.evidence_refs),
                tags=list(dict.fromkeys((list(existing.tags) if existing is not None else []) + [str(step.phase_key or '').strip()])),
                metadata={
                    **(dict(existing.metadata or {}) if existing is not None else {}),
                    'phase_key': step.phase_key,
                    'requires_approval': bool(step.requires_approval),
                    'executable': bool(step.executable),
                    'simulation_only': bool(step.simulation_only),
                    'pack_id': step.pack_id or session.chosen_pack_id,
                },
                created_at_utc=existing.created_at_utc if existing is not None else datetime.now(timezone.utc),
                updated_at_utc=datetime.now(timezone.utc),
            )
            step_nodes.append(self.repository.save(payload))
        return step_nodes

    def _progress_from_session(self, session: AdaptiveSession) -> tuple[ObjectiveStatus, float, str]:
        weak_capabilities = [item for item in session.capability_readiness if item.status.value in {'insufficient', 'partial'}]
        if session.status == AdaptiveSessionStatus.COMPLETED:
            return ObjectiveStatus.COMPLETED, 1.0, ''
        if session.status == AdaptiveSessionStatus.FAILED:
            blocker = session.outcome.summary if session.outcome is not None and session.outcome.summary else 'La ejecucion fallo y requiere correccion.'
            return ObjectiveStatus.BLOCKED, 0.25, blocker
        if session.status == AdaptiveSessionStatus.ABORTED:
            return ObjectiveStatus.PAUSED, 0.2, 'La sesion fue abortada antes de completar el objetivo.'
        if session.status == AdaptiveSessionStatus.NEED_INFO:
            return ObjectiveStatus.BLOCKED, 0.15, ', '.join(session.intent.missing_requirements[:2]) or 'Falta informacion para continuar.'
        if session.status == AdaptiveSessionStatus.WAITING_APPROVAL:
            return ObjectiveStatus.BLOCKED, 0.4, 'Esperando aprobacion humana para continuar con la siguiente fase.'
        if session.status == AdaptiveSessionStatus.EXECUTING:
            return ObjectiveStatus.ACTIVE, 0.72, ''
        if session.status == AdaptiveSessionStatus.READY_TO_EXECUTE:
            return ObjectiveStatus.ACTIVE, 0.58, weak_capabilities[0].suggested_next_step if weak_capabilities else ''
        if weak_capabilities:
            return ObjectiveStatus.BLOCKED, 0.32, weak_capabilities[0].suggested_next_step or weak_capabilities[0].title
        return ObjectiveStatus.ACTIVE, 0.22, ''

    def _rollup_progress(self, nodes: list[ObjectiveNode]) -> float:
        if not nodes:
            return 0.0
        return round(sum(float(item.progress or 0.0) for item in nodes) / max(len(nodes), 1), 4)

    def _rollup_status(self, nodes: list[ObjectiveNode]) -> ObjectiveStatus:
        filtered = [item for item in nodes if item is not None]
        if not filtered:
            return ObjectiveStatus.PENDING
        statuses = {item.status for item in filtered}
        if all(status == ObjectiveStatus.COMPLETED for status in statuses):
            return ObjectiveStatus.COMPLETED
        if ObjectiveStatus.BLOCKED in statuses:
            return ObjectiveStatus.BLOCKED
        if ObjectiveStatus.ACTIVE in statuses:
            return ObjectiveStatus.ACTIVE
        if ObjectiveStatus.PAUSED in statuses:
            return ObjectiveStatus.PAUSED
        return ObjectiveStatus.PENDING

    def _merge_refs(self, *groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                text = str(item or '').strip()
                if text and text not in merged:
                    merged.append(text)
        return merged[:16]
