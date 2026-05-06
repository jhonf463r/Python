"""Unified autonomy cycle — percibir → consolidar → decidir → reanudar.

Consolidates the autonomy-related logic that was previously scattered
across ``OperationalSelfExaminationService`` (OSES bridge),
``TaskOutcomeRecorder`` (resume hints), ``PlatformPendingQueue``
(capability seeding), and ``bootstrap.py`` (wiring).

Responsibilities
~~~~~~~~~~~~~~~~
1. **Bridge OSES findings → PlatformPendingQueue** (was in OSES).
2. **Save resume hints on interrupted sessions** (was in TaskOutcomeRecorder).
3. **Seed pending tasks from capability graph** (was wired ad-hoc in bootstrap).
4. **Resume-aware startup**: surface actionable tasks and resume hints for
   the orchestrator or UI to pick up.
5. **Provide a unified summary** of what the system can do, what it cannot,
   and what the next action should be.

Usage
~~~~~
Constructed once in ``bootstrap.py`` and injected into services that need
autonomy awareness.  The cycle itself does NOT make autonomous decisions —
that stays with ``AdaptiveTaskOrchestrator``.  This service is the *state
substrate* that feeds decisions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    PendingTaskStatus,
    PlatformPendingTask,
    PlatformResumeHint,
    RunRecord,
    utc_now,
)
from iabv_v15.services.evolution.platform_pending_queue import (
    CATEGORY_OSES_FINDING,
    CATEGORY_PERMISSION_REQUIRED,
    PlatformPendingQueue,
)

logger = logging.getLogger(__name__)


# Categories from OSES findings that should become pending tasks.
_FINDING_TO_PENDING_CATEGORIES: dict[str, str] = {
    'startup_populate_ui_freeze': (
        'Reducir tiempo de populate_ui en el hilo principal.'
    ),
    'startup_degradation': (
        'Investigar degradacion de arranque por umbrales excedidos.'
    ),
    'startup_memory_spike': (
        'Investigar spike de memoria RSS durante arranque.'
    ),
    'recurring_failure': (
        'Investigar fallo recurrente sin correccion.'
    ),
    'cloud_reasoning_degradation': (
        'Revisar proveedores cloud con tasa de exito baja.'
    ),
    'windows_integration_gaps': (
        'Completar integracion Windows detectada como faltante.'
    ),
    'temporal_regression': (
        'Investigar regresion de latencia detectada por anomalia temporal.'
    ),
}


class AutonomyCycleService:
    """Central autonomy substrate: queue + bridge + resume + discovery.

    This is the single module responsible for the autonomy cycle:

    * OSES produces signals → ``bridge_findings()`` structures them
    * Interrupted sessions → ``save_resume_hint()`` captures checkpoints
    * Environment capabilities → ``seed_capabilities()`` creates tasks
    * New sessions → ``startup_summary()`` provides actionable context

    The flow is:
    percibir → consolidar → decidir → ejecutar → verificar → reanudar
    """

    def __init__(self, queue: PlatformPendingQueue) -> None:
        self._queue = queue

    @property
    def queue(self) -> PlatformPendingQueue:
        return self._queue

    # ------------------------------------------------------------------
    # 1. Bridge: OSES findings → pending queue
    # ------------------------------------------------------------------

    def bridge_findings(
        self,
        findings: list[Any],
    ) -> int:
        """Convert HIGH/CRITICAL OSES findings into pending tasks.

        Returns the number of tasks created or updated.
        """
        count = 0
        for finding in findings:
            category = getattr(finding, 'category', '')
            if category not in _FINDING_TO_PENDING_CATEGORIES:
                continue
            severity = getattr(finding, 'severity', None)
            severity_val = getattr(severity, 'value', str(severity))
            if severity_val not in ('HIGH', 'CRITICAL'):
                continue
            task_id = f'oses_{category}'
            next_action = _FINDING_TO_PENDING_CATEGORIES[category]
            try:
                existing = self._queue.get(task_id)
                if existing is not None and existing.status == PendingTaskStatus.COMPLETED:
                    continue
                priority = 'critical' if severity_val == 'CRITICAL' else 'high'
                task = PlatformPendingTask(
                    id=task_id,
                    title=getattr(finding, 'title', category),
                    description=getattr(finding, 'summary', '') or '',
                    reason=f'OSES finding: {category}',
                    priority=priority,
                    next_action=next_action,
                    status=PendingTaskStatus.PENDING,
                    category=CATEGORY_OSES_FINDING,
                    resume_hint=getattr(finding, 'recommendation', '') or '',
                    metadata={
                        'source': 'autonomy_cycle',
                        'severity': severity_val,
                        'confidence': getattr(finding, 'confidence', 0.0),
                    },
                )
                self._queue.upsert(task)
                count += 1
            except Exception:
                logger.debug('autonomy_cycle: bridge failed for %s', category)
        return count

    # ------------------------------------------------------------------
    # 2. Resume hints: save checkpoint on interrupted sessions
    # ------------------------------------------------------------------

    def save_resume_hint(
        self,
        session: AdaptiveSession,
        *,
        run_record: RunRecord | None = None,
    ) -> PlatformResumeHint | None:
        """Save a resume hint when a session ends ABORTED or FAILED.

        Returns the saved hint, or None if the session status doesn't
        warrant a checkpoint.
        """
        if session.status not in (
            AdaptiveSessionStatus.ABORTED,
            AdaptiveSessionStatus.FAILED,
        ):
            return None
        try:
            metadata = dict(session.metadata or {})
            last_step = ''
            remaining: list[str] = []
            if run_record is not None:
                last_step = (
                    run_record.result.summary
                    or run_record.error_summary
                    or 'unknown'
                )[:200]
            playbook_goal = ''
            if session.playbook is not None:
                playbook_goal = str(session.playbook.goal or '')[:200]

            context_snapshot: dict[str, Any] = {
                'user_goal': (session.user_goal or '')[:300],
                'playbook_goal': playbook_goal,
                'status': session.status.value,
                'intent_key': metadata.get('intent_key', ''),
            }
            if session.playbook is not None and hasattr(session.playbook, 'steps'):
                steps = session.playbook.steps or []
                remaining = [str(s) for s in steps if isinstance(s, str)][:8]

            hint = PlatformResumeHint(
                task_id=session.session_id,
                checkpoint_phase=session.status.value,
                last_successful_step=last_step,
                remaining_steps=remaining,
                handoff_required=session.status == AdaptiveSessionStatus.FAILED,
                context_snapshot=context_snapshot,
            )
            self._queue.save_resume_hint(hint)
            return hint
        except Exception:
            logger.debug('autonomy_cycle: save_resume_hint failed', exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 3. Capability discovery → pending tasks
    # ------------------------------------------------------------------

    def seed_capabilities(
        self,
        capabilities: list[Any],
    ) -> list[PlatformPendingTask]:
        """Convert missing environment capabilities into pending tasks.

        Delegates to ``PlatformPendingQueue.seed_from_capability_graph``.
        """
        return self._queue.seed_from_capability_graph(capabilities)

    # ------------------------------------------------------------------
    # 3b. Permission gates → BLOCKED tasks
    # ------------------------------------------------------------------

    def seed_permission_gaps(
        self,
        permission_gates: list[Any],
    ) -> int:
        """Convert ungranted permission gates into BLOCKED pending tasks.

        Reads ``ObservationPermissionGate`` objects from the WorldModel
        and creates a BLOCKED task for each permission that hasn't been
        granted yet.  Granted permissions mark the corresponding task
        as COMPLETED.  Returns the number of tasks created or updated.
        """
        count = 0
        for gate in permission_gates:
            scope = getattr(gate, 'scope', '') or ''
            granted = getattr(gate, 'granted', False)
            if not scope:
                continue
            task_id = f'perm_{scope}'
            existing = self._queue.get(task_id)
            if granted:
                if existing is not None and existing.status != PendingTaskStatus.COMPLETED:
                    self._queue.mark_status(task_id, PendingTaskStatus.COMPLETED)
                    count += 1
                continue
            if existing is not None and existing.status == PendingTaskStatus.COMPLETED:
                continue
            title = getattr(gate, 'title', scope) or scope
            detail = getattr(gate, 'detail', '') or ''
            required_for = getattr(gate, 'required_for', []) or []
            task = PlatformPendingTask(
                id=task_id,
                title=f'Permiso faltante: {title}',
                description=detail or f'Permiso {scope} no concedido.',
                reason='permission_gate not granted',
                dependency_missing=f'user approval for {scope}',
                priority='high' if required_for else 'medium',
                next_action=f'Solicitar permiso de {scope} al usuario',
                status=PendingTaskStatus.BLOCKED,
                category=CATEGORY_PERMISSION_REQUIRED,
                metadata={'required_for': required_for},
            )
            self._queue.upsert(task)
            count += 1
        return count

    # ------------------------------------------------------------------
    # 4. Startup summary: actionable context for the next session
    # ------------------------------------------------------------------

    def startup_summary(self) -> dict[str, Any]:
        """Build a summary of actionable work for session start.

        Returns a dict with:
        - ``actionable_tasks``: tasks that can be worked on now
        - ``blocked_tasks``: tasks waiting on a dependency
        - ``resume_hints``: checkpoints from interrupted sessions
        - ``queue_summary``: aggregate stats
        """
        actionable = self._queue.list_actionable()
        blocked = [
            t for t in self._queue.list_all()
            if t.status == PendingTaskStatus.BLOCKED
        ]
        hints = self._queue.list_resume_hints()
        summary = self._queue.summary()

        return {
            'actionable_tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'priority': t.priority,
                    'next_action': t.next_action,
                    'category': t.category,
                }
                for t in actionable
            ],
            'blocked_tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'dependency_missing': t.dependency_missing,
                }
                for t in blocked
            ],
            'resume_hints': [
                {
                    'task_id': h.task_id,
                    'checkpoint_phase': h.checkpoint_phase,
                    'last_step': h.last_successful_step,
                    'remaining': h.remaining_steps,
                    'handoff_required': h.handoff_required,
                }
                for h in hints
            ],
            'queue_summary': summary,
        }
