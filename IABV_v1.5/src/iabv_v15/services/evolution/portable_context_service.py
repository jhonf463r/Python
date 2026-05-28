from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    ObjectiveNodeKind,
    PortableContextPackage,
    PortableContextSection,
    TaskContext,
    WorldModelSnapshot,
    utc_now,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class PortableContextService:
    # Ventana de recencia para el fallback de intencion de usuario (H1).
    # Si la sesion adaptativa mas reciente supera esta antiguedad, el
    # user_goal no se propaga como active_title tentativo; se prefiere
    # dejar UNRESOLVED:active_goal_context antes que afirmar un objetivo
    # stale.
    _USER_GOAL_FALLBACK_FRESHNESS_HOURS = 72
    _USER_GOAL_FALLBACK_MIN_LENGTH = 3

    def __init__(
        self,
        *,
        workspace_root: str,
        storage: ArtifactStorage,
        objective_repository: Any | None = None,
        experiment_lab_repository: Any | None = None,
        pending_issue_repository: Any | None = None,
        evolution_review_service: Any | None = None,
        environment_self_awareness_service: Any | None = None,
        world_model_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        self_examination_service: Any | None = None,
        tool_discovery_service: Any | None = None,
        tool_evolution_monitor: Any | None = None,
        task_context_assembler: Any | None = None,
        adaptive_task_orchestrator: Any | None = None,
        adaptive_session_repository: Any | None = None,
        platform_pending_queue: Any | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.storage = storage
        self.objective_repository = objective_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.pending_issue_repository = pending_issue_repository
        self.evolution_review_service = evolution_review_service
        self.environment_self_awareness_service = environment_self_awareness_service
        self.world_model_service = world_model_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.self_examination_service = self_examination_service
        self.tool_discovery_service = tool_discovery_service
        self.tool_evolution_monitor = tool_evolution_monitor
        self.task_context_assembler = task_context_assembler
        self.adaptive_task_orchestrator = adaptive_task_orchestrator
        self.adaptive_session_repository = adaptive_session_repository
        self.platform_pending_queue = platform_pending_queue
        self.control_master_service: Any | None = None
        self.decision_audit_trail: Any | None = None
        self.code_audit_trail: Any | None = None
        self.boot_profile_store: Any | None = None
        self.freeze_incident_reporter: Any | None = None
        self.experiment_lab: Any | None = None
        self.chat_message_repository: Any | None = None
        self._current_package: PortableContextPackage | None = None
        self._account_resource_cache: dict[str, Any] | None = None
        self._account_resource_cached_at: float = 0.0
        self._ACCOUNT_RESOURCE_TTL: float = 60.0

    def current_package(
        self,
        *,
        refresh: bool = False,
        max_age_seconds: int = 300,
        task_context: TaskContext | None = None,
        environment_self_model: EnvironmentSelfModel | None = None,
        world_model: WorldModelSnapshot | None = None,
    ) -> PortableContextPackage:
        cached = self._current_package
        if cached is None:
            cached = self._load_latest_package()
            self._current_package = cached
        if not refresh and cached is not None and self._is_fresh(cached, max_age_seconds=max_age_seconds):
            if not self._goal_shifted(cached, task_context=task_context):
                return cached
        package = self.build_package(
            task_context=task_context,
            environment_self_model=environment_self_model,
            world_model=world_model,
        )
        self._current_package = package
        return package

    def build_package(
        self,
        *,
        task_context: TaskContext | None = None,
        environment_self_model: EnvironmentSelfModel | None = None,
        world_model: WorldModelSnapshot | None = None,
    ) -> PortableContextPackage:
        now = utc_now()
        goal_context = self._goal_context(task_context=task_context)
        environment = environment_self_model or self._environment_self_model()
        world = world_model or self._world_model()
        validation = self._validation_snapshot()
        project_health = self._project_health_snapshot()
        recommendations = self._recommendation_items(task_context=task_context)
        adaptive_learning = self._adaptive_learning_summary(task_context=task_context, recommendations=recommendations)
        learned_patterns = self._learned_patterns(task_context=task_context, recommendations=recommendations)
        try:
            auto_patterns = self.derive_learned_patterns()
            if auto_patterns:
                learned_patterns = list(learned_patterns) + auto_patterns
        except Exception:
            logging.getLogger(__name__).warning('Could not derive auto learned patterns', exc_info=True)
        coordination_patterns = self._build_coordination_patterns()
        tool_discovery = self._tool_discovery_snapshot()
        tool_evolution = self._tool_evolution_snapshot()
        tool_evolution_decisions = self._tool_evolution_decision_snapshot()
        self_examination = self._self_examination_snapshot()
        cloud_reasoning_status = self._cloud_reasoning_snapshot()
        code_audit_status = self._code_audit_snapshot()
        startup_health = self._startup_health_snapshot()
        account_resource = self._account_resource_snapshot()
        boot_profile = self._boot_profile_snapshot()
        evidence_basis = self._evidence_basis_snapshot(
            environment=environment,
            world=world,
            task_context=task_context,
        )
        task_packet_summary = self._task_packet_summary_snapshot()
        pending_items = self._pending_items()
        backlog_items = self._backlog_items()
        decision_history = self._decision_history(recommendations=recommendations)
        unresolved = self._unresolved_fields(
            environment=environment,
            world=world,
            validation=validation,
            recommendations=recommendations,
            goal_context=goal_context,
        )
        unresolved = list(dict.fromkeys([*unresolved, *list(self_examination.get('unresolved_risks') or [])]))
        sections = [
            self._project_state_section(
                goal_context=goal_context,
                project_health=project_health,
                validation=validation,
                world=world,
                now=now,
            ),
            self._architecture_section(now=now),
            self._user_metacognitive_intent_section(now=now),
            self._implemented_capabilities_section(
                recommendations=recommendations,
                validation=validation,
                world=world,
                now=now,
            ),
            self._learning_section(
                adaptive_learning=adaptive_learning,
                learned_patterns=learned_patterns,
                recommendations=recommendations,
                now=now,
            ),
            self._coordination_patterns_section(
                coordination_patterns=coordination_patterns,
                now=now,
            ),
            self._tool_discovery_section(status=tool_discovery, now=now),
            self._tool_evolution_section(status=tool_evolution, now=now),
            self._tool_evolution_decisions_section(snapshot=tool_evolution_decisions, now=now),
            self._self_examination_section(review=self_examination, now=now),
            self._code_audit_section(status=code_audit_status, now=now),
            self._cloud_reasoning_section(status=cloud_reasoning_status, now=now),
            self._startup_health_section(status=startup_health, now=now),
            self._interaction_lifecycle_section(now=now),
            self._account_resource_section(status=account_resource, now=now),
            self._account_inventory_continuity_section(now=now),
            self._tool_coordination_section(now=now),
            self._boot_profile_section(status=boot_profile, now=now),
            self._evidence_basis_section(evidence=evidence_basis, now=now),
            self._test_evidence_section(now=now),
            self._task_packet_summary_section(snapshot=task_packet_summary, now=now),
            self._recommended_routes_section(recommendations=recommendations, now=now),
            self._operational_blocks_section(world=world, recommendations=recommendations, now=now),
            self._validated_decisions_section(
                recommendations=recommendations,
                validation=validation,
                now=now,
            ),
            self._decision_history_section(decision_history=decision_history, now=now),
            self._pending_section(pending_items=pending_items, backlog_items=backlog_items, now=now),
            self._canonical_work_queue_section(now=now),
            self._shared_reality_section(review=self_examination, now=now),
            self._user_chrome_bridge_section(now=now),
            self._active_incident_frame_section(now=now),
            self._web_skill_status_section(now=now),
            self._devin_repair_status_section(now=now),
            self._capability_readiness_section(now=now),
            self._next_time_policy_section(now=now),
            self._discernment_frame_section(now=now),
            self._metacognitive_roadmap_matrix_section(now=now),
            self._unresolved_metacognitive_links_section(now=now),
            self._unresolved_section(unresolved=unresolved, now=now),
            self._hard_rules_section(now=now),
            self._user_identity_section(now=now),
            self._long_term_goals_section(now=now),
        ]
        package = PortableContextPackage(
            created_at_utc=now,
            updated_at_utc=now,
            summary=self._package_summary(
                goal_context=goal_context,
                recommendations=recommendations,
                world=world,
                pending_items=pending_items,
                unresolved=unresolved,
                self_examination=self_examination,
            ),
            sections=sections,
            unresolved_fields=unresolved,
            metadata={
                'workspace_root': self.workspace_root,
                'site_id': str(goal_context.get('site_id') or ''),
                'active_objective_id': str(goal_context.get('active_objective_id') or ''),
                'refresh_policy': 'refresh_if_stale_or_goal_shift',
                'source_count': sum(len(section.source_refs) for section in sections),
                'tool_discovery_summary': dict(tool_discovery.get('summary_payload') or {}),
                'tool_discovery_signals': list(tool_discovery.get('signals') or []),
                'tool_evolution_summary': dict(tool_evolution.get('summary_payload') or {}),
                'tool_evolution_proposals': list(tool_evolution.get('proposals') or []),
                'tool_evolution_degraded_subjects': list(tool_evolution.get('degraded_subjects') or []),
                'tool_evolution_decision_summary': dict(tool_evolution_decisions.get('summary_payload') or {}),
                'tool_evolution_validated_proposals': list(tool_evolution_decisions.get('entries') or []),
                'cloud_reasoning_status': dict(cloud_reasoning_status),
                'startup_health': dict(startup_health),
                'account_resource': dict(account_resource),
                'boot_profile': dict(boot_profile),
                'evidence_basis': dict(evidence_basis),
                'task_packet_summary': dict(task_packet_summary),
                'coordination_patterns': coordination_patterns,
                'chat_stats': self._chat_stats_snapshot(),
                'autoexamination_summary': dict(self_examination.get('summary_payload') or {}),
                'recurring_issues': list(self_examination.get('recurring_issues') or []),
                'recommended_adjustments': list(self_examination.get('recommended_adjustments') or []),
                    'validated_improvements': list(self_examination.get('validated_improvements') or []),
                    'recommendation_feedback': list(self_examination.get('recommendation_feedback') or []),
                    'feedback_summary': dict(self_examination.get('feedback_summary') or {}),
                    'unresolved_risks': list(self_examination.get('unresolved_risks') or []),
                },
            )
        package = package.model_copy(
            update={
                'assistant_brief': self._render_assistant_brief(package),
                'package_path': str(self.storage.resolve('portable_context/latest.json')),
                'markdown_path': str(self.storage.resolve('portable_context/latest.md')),
            }
        )
        archive_json_rel = f'portable_context/history/{package.package_id}.json'
        archive_md_rel = f'portable_context/history/{package.package_id}.md'
        latest_json_rel = 'portable_context/latest.json'
        latest_md_rel = 'portable_context/latest.md'
        payload = package.model_dump(mode='json')
        self.storage.save_json_atomic(archive_json_rel, payload)
        self.storage.save_bytes(archive_md_rel, package.assistant_brief.encode('utf-8'))
        self.storage.save_json_atomic(latest_json_rel, payload)
        self.storage.save_bytes(latest_md_rel, package.assistant_brief.encode('utf-8'))
        package.metadata.update(
            {
                'archive_json_path': str(self.storage.resolve(archive_json_rel)),
                'archive_markdown_path': str(self.storage.resolve(archive_md_rel)),
            }
        )
        self.storage.save_json_atomic(latest_json_rel, package.model_dump(mode='json'))
        return package

    def package_summary(self, package: PortableContextPackage | None = None) -> dict[str, Any]:
        resolved = package or self.current_package()
        sections = {section.section_id: section for section in resolved.sections}
        recommended = sections.get('recommended_routes')
        blocks = sections.get('operational_blocks')
        pending = sections.get('pending')
        validated = sections.get('validated_decisions')
        self_examination = sections.get('self_examination')
        return {
            'package_id': resolved.package_id,
            'package_version': resolved.package_version,
            'summary': resolved.summary,
            'assistant_brief': resolved.assistant_brief,
            'package_path': resolved.package_path,
            'markdown_path': resolved.markdown_path,
            'updated_at_utc': resolved.updated_at_utc.isoformat(),
            'recommended_routes': list((recommended.items if recommended is not None else [])[:4]),
            'active_blocks': list((blocks.items if blocks is not None else [])[:6]),
            'validated_decisions': list((validated.items if validated is not None else [])[:4]),
            'pending_items': list((pending.items if pending is not None else [])[:6]),
            'tool_discovery_summary': dict((resolved.metadata or {}).get('tool_discovery_summary') or {}),
            'tool_discovery_signals': list((resolved.metadata or {}).get('tool_discovery_signals') or [])[:6],
            'tool_evolution_summary': dict((resolved.metadata or {}).get('tool_evolution_summary') or {}),
            'tool_evolution_proposals': list((resolved.metadata or {}).get('tool_evolution_proposals') or [])[:4],
            'tool_evolution_decision_summary': dict((resolved.metadata or {}).get('tool_evolution_decision_summary') or {}),
            'tool_evolution_validated_proposals': list((resolved.metadata or {}).get('tool_evolution_validated_proposals') or [])[:4],
            'self_examination_summary': dict((resolved.metadata or {}).get('autoexamination_summary') or {}),
            'recurring_issues': list((self_examination.metadata if self_examination is not None else {}).get('recurring_issues') or [])[:4],
            'recommended_adjustments': list((resolved.metadata or {}).get('recommended_adjustments') or [])[:4],
            'validated_improvements': list((resolved.metadata or {}).get('validated_improvements') or [])[:4],
            'recommendation_feedback': list((resolved.metadata or {}).get('recommendation_feedback') or [])[:4],
            'feedback_summary': dict((resolved.metadata or {}).get('feedback_summary') or {}),
            'unresolved_risks': list((resolved.metadata or {}).get('unresolved_risks') or [])[:6],
            'unresolved_fields': list(resolved.unresolved_fields or []),
        }

    def flush_startup_health(self) -> bool:
        """Patch ``startup_health`` into ``portable_context/latest.json`` in-place.

        In short runs the full ``build_package()`` may never execute before
        the process exits, leaving ``latest.json`` without the new
        ``startup_health`` fields collected during this boot.  This method
        reads the persisted package, replaces only the ``startup_health``
        section and its metadata entry, and writes back — without
        rebuilding every other section (which would be expensive and
        could overwrite fresher data from a concurrent MCP call).

        Returns ``True`` if the flush wrote data, ``False`` if skipped
        (no existing package, no storage, or error).
        """
        try:
            if not self.storage.exists('portable_context/latest.json'):
                return False
            payload = self.storage.load_json('portable_context/latest.json')
        except Exception:
            logging.getLogger(__name__).debug(
                'flush_startup_health: cannot load latest.json', exc_info=True,
            )
            return False

        startup_health = self._startup_health_snapshot()
        if startup_health.get('status') in ('no_log', 'no_data', 'error', None):
            return False

        try:
            sections = payload.get('sections') or []
            replaced = False
            for section in sections:
                if section.get('section_id') == 'startup_health':
                    section['items'] = [startup_health]
                    section['metadata'] = section.get('metadata') or {}
                    section['metadata']['flushed_at_boot'] = True
                    replaced = True
                    break
            if not replaced:
                return False

            metadata = payload.get('metadata') or {}
            metadata['startup_health'] = dict(startup_health)
            payload['metadata'] = metadata
            payload['updated_at_utc'] = utc_now().isoformat()

            self.storage.save_json_atomic('portable_context/latest.json', payload)
            logging.getLogger(__name__).info(
                'flush_startup_health: patched latest.json (status=%s)',
                startup_health.get('status'),
            )
            return True
        except Exception:
            logging.getLogger(__name__).debug(
                'flush_startup_health: write failed', exc_info=True,
            )
            return False

    def _load_latest_package(self) -> PortableContextPackage | None:
        try:
            if not self.storage.exists('portable_context/latest.json'):
                return None
            payload = self.storage.load_json('portable_context/latest.json')
            return PortableContextPackage.model_validate(payload)
        except Exception:
            return None

    def _is_fresh(self, package: PortableContextPackage, *, max_age_seconds: int) -> bool:
        try:
            age_seconds = (utc_now() - package.updated_at_utc).total_seconds()
        except Exception:
            return False
        return age_seconds <= max_age_seconds

    def _goal_shifted(self, package: PortableContextPackage, *, task_context: TaskContext | None) -> bool:
        if task_context is None:
            return False
        goal_context = task_context.goal_context
        cached_site = str((package.metadata or {}).get('site_id') or '').strip()
        cached_objective = str((package.metadata or {}).get('active_objective_id') or '').strip()
        target_site = str(task_context.site_id or '').strip()
        target_objective = str(goal_context.active_node_id or '').strip()
        return cached_site != target_site or cached_objective != target_objective

    def _goal_context(self, *, task_context: TaskContext | None) -> dict[str, Any]:
        if task_context is not None:
            goal = task_context.goal_context
            return {
                'site_id': str(task_context.site_id or ''),
                'active_title': str(goal.active_title or ''),
                'active_objective_id': str(goal.active_node_id or ''),
                'objective_id': str((dict(goal.objective or {}).get('objective_id') or '') or ''),
                'progress': float(goal.progress or 0.0),
                'confidence': float(goal.confidence or 0.0),
                'blocker': str(goal.blocker or ''),
                'objective': dict(goal.objective or {}),
                'project': dict(goal.project or {}),
                'task': dict(goal.task or {}),
            }
        objective = self._latest_objective(kind=ObjectiveNodeKind.OBJECTIVE)
        project = self._latest_objective(kind=ObjectiveNodeKind.PROJECT)
        task = self._latest_objective(kind=ObjectiveNodeKind.TASK)
        active_title = str((getattr(task, 'title', '') or getattr(project, 'title', '') or getattr(objective, 'title', '') or '')).strip()
        active_objective_id = str((getattr(task, 'objective_id', '') or getattr(project, 'objective_id', '') or getattr(objective, 'objective_id', '') or ''))
        site_id = str((getattr(task, 'site_id', '') or getattr(project, 'site_id', '') or getattr(objective, 'site_id', '') or ''))
        fallback_metadata: dict[str, Any] = {}
        if not active_title:
            inferred = self._recent_user_goal_fallback()
            if inferred is not None:
                active_title = inferred['active_title']
                site_id = site_id or inferred.get('site_id') or ''
                fallback_metadata = {
                    'source': 'inferred_from_recent_session',
                    'session_id': inferred.get('session_id') or '',
                    'inferred_from_session_created_at_utc': inferred.get('created_at_utc') or '',
                    'inferred': True,
                    'status': 'tentative',
                }
        return {
            'site_id': site_id,
            'active_title': active_title,
            'active_objective_id': active_objective_id,
            'objective_id': str(getattr(objective, 'objective_id', '') or ''),
            'progress': float(getattr(task, 'progress', 0.0) or getattr(project, 'progress', 0.0) or getattr(objective, 'progress', 0.0) or 0.0),
            'confidence': float(getattr(task, 'confidence', 0.0) or getattr(project, 'confidence', 0.0) or getattr(objective, 'confidence', 0.0) or 0.0),
            'blocker': '',
            'objective': objective.model_dump(mode='json') if objective is not None else {},
            'project': project.model_dump(mode='json') if project is not None else {},
            'task': task.model_dump(mode='json') if task is not None else {},
            'metadata': fallback_metadata,
        }

    def _recent_user_goal_fallback(self) -> dict[str, Any] | None:
        """H1: si no hay objetivo activo declarado en objective_repository,
        recupera el user_goal mas reciente de AdaptiveSessionRepository
        y lo propaga como active_title TENTATIVO.

        Motivacion: la UI ya registra cada intent del usuario en
        AdaptiveSession.user_goal, pero esa senal no llegaba al
        PortableContextPackage cuando el GoalEngine aun no habia
        materializado un ObjectiveNode. Como resultado, el paquete
        portable mostraba 'sin objetivo activo confirmado' aun cuando el
        usuario habia expresado una intencion segundos antes, dejando al
        orquestador y a los asistentes externos sin contexto.

        Proteccion contra stale: si la sesion mas reciente fue creada
        hace mas de ``_USER_GOAL_FALLBACK_FRESHNESS_HOURS`` horas o su
        user_goal es trivialmente corto, NO se propaga y se mantiene la
        marca UNRESOLVED:active_goal_context. Preferible admitir que no
        hay objetivo a inventar uno stale.

        La propagacion deja marcas explicitas en
        ``goal_context['metadata']`` para que todo consumidor (UI,
        cognitive_frame_translator, strategy_selector) pueda distinguir
        un objetivo confirmado de uno inferido.
        """
        repository = self.adaptive_session_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return None
        try:
            recent_sessions = repository.list_recent(limit=1)
        except Exception:
            return None
        if not recent_sessions:
            return None
        session = recent_sessions[0]
        user_goal = str(getattr(session, 'user_goal', '') or '').strip()
        if len(user_goal) < self._USER_GOAL_FALLBACK_MIN_LENGTH:
            return None
        created_at = getattr(session, 'created_at_utc', None)
        if isinstance(created_at, datetime):
            reference = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self._USER_GOAL_FALLBACK_FRESHNESS_HOURS)
            if reference < cutoff:
                return None
            created_at_str = reference.isoformat()
        else:
            created_at_str = ''
        site_id = str(getattr(getattr(session, 'context', None), 'site_id', '') or '')
        return {
            'active_title': user_goal,
            'session_id': str(getattr(session, 'session_id', '') or ''),
            'created_at_utc': created_at_str,
            'site_id': site_id,
        }

    def _latest_objective(self, *, kind: ObjectiveNodeKind) -> Any | None:
        repository = self.objective_repository
        if repository is None or not hasattr(repository, 'latest_active'):
            return None
        try:
            return repository.latest_active(kind=kind)
        except Exception:
            return None

    def _environment_self_model(self) -> EnvironmentSelfModel:
        service = self.environment_self_awareness_service
        if service is None or not hasattr(service, 'current_model'):
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            return service.current_model()
        except Exception:
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _world_model(self) -> WorldModelSnapshot:
        service = self.world_model_service
        if service is None or not hasattr(service, 'current_model'):
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            model = service.current_model()
            return model if model is not None else WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        except Exception:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _validation_snapshot(self) -> dict[str, Any]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_snapshot'):
            return {}
        try:
            snapshot = service.current_snapshot()
            return snapshot.model_dump(mode='json')
        except Exception:
            return {}

    def _project_health_snapshot(self) -> dict[str, Any]:
        service = self.evolution_review_service
        if service is None or not hasattr(service, 'build_project_health'):
            return {}
        try:
            snapshot = service.build_project_health()
            return snapshot.model_dump(mode='json')
        except Exception:
            return {}

    def _self_examination_snapshot(self) -> dict[str, Any]:
        service = self.self_examination_service
        if service is None or not hasattr(service, 'current_review'):
            return {
                'summary': '',
                'summary_payload': {},
                'findings': [],
                'recurring_issues': [],
                'recommended_adjustments': [],
                'validated_improvements': [],
                'recommendation_feedback': [],
                'feedback_summary': {},
                'unresolved_risks': ['UNRESOLVED:self_examination'],
            }
        try:
            review = service.current_review(refresh=True)
            if hasattr(service, 'review_summary'):
                summary_payload = dict(service.review_summary(review) or {})
            else:
                summary_payload = {}
            return {
                'summary': str(getattr(review, 'summary', '') or ''),
                'summary_payload': summary_payload,
                'findings': [item.model_dump(mode='json') for item in list(getattr(review, 'findings', []) or [])[:6]],
                'recurring_issues': list(getattr(review, 'recurring_issues', []) or [])[:6],
                'recommended_adjustments': list(getattr(review, 'recommended_adjustments', []) or [])[:6],
                'validated_improvements': list(getattr(review, 'validated_improvements', []) or [])[:4],
                'recommendation_feedback': list(dict(getattr(review, 'metadata', {}) or {}).get('recommendation_feedback') or [])[:6],
                'feedback_summary': dict(dict(getattr(review, 'metadata', {}) or {}).get('feedback_summary') or {}),
                'unresolved_risks': list(getattr(review, 'unresolved_risks', []) or [])[:8],
            }
        except Exception:
            return {
                'summary': '',
                'summary_payload': {},
                'findings': [],
                'recurring_issues': [],
                'recommended_adjustments': [],
                'validated_improvements': [],
                'recommendation_feedback': [],
                'feedback_summary': {},
                'unresolved_risks': ['UNRESOLVED:self_examination'],
            }

    def _startup_health_snapshot(self) -> dict[str, Any]:
        """Read ``data/logs/startup_timeline.jsonl`` and summarise the last boot.

        The instrumentation in :mod:`iabv_v15.infra.startup_timeline` appends one
        JSON line per milestone (``bootstrap_init_start``, ``main_window_shown``,
        ``deferred_post_window_setup_done`` ...) with ``t_ms_from_start`` and
        ``rss_mb``.  This snapshot picks the last contiguous boot run (events
        whose ``t_ms_from_start`` is monotonically increasing) and exposes the
        derived intervals so PortableContext consumers and OSES findings can
        reason about startup degradation without re-parsing the file.

        Sin servicio nuevo, sin memoria paralela: leemos el JSONL existente.

        Returns a dict with:
            - ``status``: ``no_log`` / ``no_data`` / ``analyzed`` / ``error``
            - ``init_ms``: ``bootstrap_init_done - bootstrap_init_start``
            - ``run_to_window_ms``: ``main_window_shown - run_start``
            - ``deferred_ms``: ``deferred_post_window_setup_done -
              deferred_post_window_setup_start`` (post-window cost)
            - ``last_started_at_utc``: ISO timestamp of the latest jsonl mtime
            - ``recent_blockers``: list of phases that exceed thresholds
            - ``rss_mb_max``: peak RSS recorded across the run
            - ``unresolved_fields``: tags emitted when evidence is missing
        """
        log_path = Path(self.workspace_root) / 'data' / 'logs' / 'startup_timeline.jsonl'
        if not log_path.exists():
            return {
                'status': 'no_log',
                'unresolved_fields': ['UNRESOLVED:startup_timeline_missing'],
            }
        try:
            stat = log_path.stat()
            last_mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            last_mtime_utc = ''
        events: list[dict[str, Any]] = []
        try:
            with log_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return {
                'status': 'error',
                'unresolved_fields': ['UNRESOLVED:startup_timeline_unreadable'],
            }
        if not events:
            return {
                'status': 'no_data',
                'last_started_at_utc': last_mtime_utc,
                'unresolved_fields': ['UNRESOLVED:startup_timeline_empty'],
            }
        # Pick the last contiguous run: walk back from the tail while
        # ``t_ms_from_start`` keeps decreasing or staying flat.  A non-monotonic
        # jump signals a fresh process attached to the same file.
        last_run: list[dict[str, Any]] = [events[-1]]
        for evt in reversed(events[:-1]):
            try:
                if float(evt.get('t_ms_from_start') or 0.0) <= float(last_run[0].get('t_ms_from_start') or 0.0):
                    last_run.insert(0, evt)
                else:
                    break
            except (TypeError, ValueError):
                break
        phase_to_ms: dict[str, float] = {}
        phase_to_process_ms: dict[str, float] = {}
        rss_max = 0.0
        for evt in last_run:
            phase = str(evt.get('phase') or '')
            if not phase:
                continue
            try:
                phase_to_ms[phase] = float(evt.get('t_ms_from_start') or 0.0)
            except (TypeError, ValueError):
                continue
            if 't_ms_from_process' in evt:
                try:
                    phase_to_process_ms[phase] = float(evt['t_ms_from_process'])
                except (TypeError, ValueError):
                    pass
            try:
                rss_max = max(rss_max, float(evt.get('rss_mb') or 0.0))
            except (TypeError, ValueError):
                continue

        def _delta(a: str, b: str) -> float | None:
            if a in phase_to_ms and b in phase_to_ms:
                return round(phase_to_ms[b] - phase_to_ms[a], 1)
            return None

        init_ms = _delta('bootstrap_init_start', 'bootstrap_init_done')
        run_to_window_ms = _delta('run_start', 'main_window_shown')
        if run_to_window_ms is None:
            run_to_window_ms = _delta('bootstrap_init_done', 'main_window_shown')
        deferred_ms = _delta('deferred_post_window_setup_start', 'deferred_post_window_setup_done')

        unresolved: list[str] = []
        if init_ms is None:
            unresolved.append('UNRESOLVED:startup_init_window_missing')
        if run_to_window_ms is None:
            unresolved.append('UNRESOLVED:startup_main_window_missing')
        recent_blockers: list[dict[str, Any]] = []
        if init_ms is not None and init_ms > 4000.0:
            recent_blockers.append({'phase': 'bootstrap_init', 'ms': init_ms})
        if run_to_window_ms is not None and run_to_window_ms > 8000.0:
            recent_blockers.append({'phase': 'run_to_main_window', 'ms': run_to_window_ms})
        if deferred_ms is not None and deferred_ms > 5000.0:
            recent_blockers.append({'phase': 'deferred_post_window', 'ms': deferred_ms})

        # False-ready detection: readiness proof is hierarchical.
        # ``page_loader_ready`` proves the real internal page exists and is
        # stronger than ``shell_loader_ready``.  With phased construction,
        # ``populate_ui_done`` arrives much later (Phase 3 VMs are deferred),
        # so splash closing before populate_ui_done is EXPECTED — not a bug.
        false_ready = False
        false_ready_reason: list[str] = []
        splash_ms = phase_to_ms.get('splash_set_ready')
        populate_done_ms = phase_to_ms.get('populate_ui_done')
        page_ready_ms = phase_to_ms.get('page_loader_ready')
        shell_ready_ms = phase_to_ms.get('shell_loader_ready')
        shell_ready_fallback_ms = phase_to_ms.get('shell_loader_ready_fallback')
        readiness_proof_ms = page_ready_ms if page_ready_ms is not None else shell_ready_ms
        readiness_proof_phase = (
            'page_loader_ready'
            if page_ready_ms is not None
            else 'shell_loader_ready'
            if shell_ready_ms is not None
            else ''
        )
        if splash_ms is not None and readiness_proof_ms is not None and splash_ms < readiness_proof_ms:
            false_ready = True
            false_ready_reason.append(f'splash_set_ready_before_{readiness_proof_phase}')
        if splash_ms is not None and readiness_proof_ms is None and shell_ready_fallback_ms is None:
            false_ready = True
            false_ready_reason.append('splash_set_ready_without_readiness_proof')
        if shell_ready_fallback_ms is not None and readiness_proof_ms is None:
            false_ready = True
            false_ready_reason.append('shell_loader_ready_fallback_used')
        if false_ready:
            recent_blockers.append({
                'phase': 'startup_false_ready',
                'reasons': false_ready_reason,
                'readiness_proof_phase': readiness_proof_phase,
            })

        # Process-start metrics: use t_ms_from_process when available,
        # otherwise fall back to t_ms_from_start.
        process_to_shell_loader_ready_ms: float | None = None
        process_to_page_loader_ready_ms: float | None = None
        process_to_splash_window_closing_ms: float | None = None
        fallback_used = shell_ready_fallback_ms is not None

        if 'shell_loader_ready' in phase_to_process_ms:
            process_to_shell_loader_ready_ms = round(
                phase_to_process_ms['shell_loader_ready'], 1,
            )
        elif shell_ready_ms is not None:
            process_to_shell_loader_ready_ms = round(shell_ready_ms, 1)
        elif shell_ready_fallback_ms is not None:
            process_to_shell_loader_ready_ms = round(shell_ready_fallback_ms, 1)

        if 'page_loader_ready' in phase_to_process_ms:
            process_to_page_loader_ready_ms = round(
                phase_to_process_ms['page_loader_ready'], 1,
            )
        elif 'page_loader_ready' in phase_to_ms:
            process_to_page_loader_ready_ms = round(
                phase_to_ms['page_loader_ready'], 1,
            )

        if 'splash_window_closing' in phase_to_process_ms:
            process_to_splash_window_closing_ms = round(
                phase_to_process_ms['splash_window_closing'], 1,
            )
        elif 'splash_window_closing' in phase_to_ms:
            process_to_splash_window_closing_ms = round(
                phase_to_ms['splash_window_closing'], 1,
            )

        return {
            'status': 'analyzed',
            'init_ms': init_ms,
            'run_to_window_ms': run_to_window_ms,
            'deferred_ms': deferred_ms,
            'process_to_shell_loader_ready_ms': process_to_shell_loader_ready_ms,
            'process_to_page_loader_ready_ms': process_to_page_loader_ready_ms,
            'process_to_splash_window_closing_ms': process_to_splash_window_closing_ms,
            'fallback_used': fallback_used,
            'rss_mb_max': round(rss_max, 1) if rss_max else None,
            'last_started_at_utc': last_mtime_utc,
            'phases_seen': list(phase_to_ms.keys()),
            'event_count': len(last_run),
            'recent_blockers': recent_blockers,
            'false_ready_detected': false_ready,
            'false_ready_reasons': false_ready_reason,
            'unresolved_fields': unresolved,
        }

    def _account_resource_snapshot(self) -> dict[str, Any]:
        """Return a cached summary of account health, quotas and workers.

        This is **observability only** — it never triggers browser/cookie
        scans on its own.  The data comes from ``get_all_quota_status`` and
        ``scan_configured_secrets`` which read lightweight JSON/env state.

        ``estimate_available_workers()`` is the expensive call (it copies
        browser SQLite cookies).  Instead of calling it inside every
        ``build_package()``, we cache the result with a 60 s TTL so that
        repeated refreshes reuse the same data.

        If the cache is warm the method returns instantly with zero I/O.
        """
        now = time.monotonic()
        if (
            self._account_resource_cache is not None
            and (now - self._account_resource_cached_at) < self._ACCOUNT_RESOURCE_TTL
        ):
            return self._account_resource_cache

        result = self._account_resource_scan()
        self._account_resource_cache = result
        self._account_resource_cached_at = now
        return result

    def _account_resource_scan(self) -> dict[str, Any]:
        """Execute the actual scanner calls (quota + secrets + workers).

        Separated from ``_account_resource_snapshot`` so the TTL cache
        logic stays clean.  Failures are swallowed — the portable context
        build never crashes because of a scanner issue.
        """
        try:
            from iabv_v15.services.account_resource_scanner import (
                get_all_quota_status,
                estimate_available_workers,
                scan_configured_secrets,
            )
        except Exception:
            return {'status': 'scanner_unavailable'}

        quotas: dict[str, Any] = {}
        try:
            quotas = get_all_quota_status()
        except Exception:
            quotas = {'error': 'quota_read_failed'}

        workers: dict[str, Any] = {}
        try:
            workers = estimate_available_workers()
        except Exception:
            workers = {'error': 'worker_read_failed'}

        secrets: dict[str, Any] = {}
        try:
            secrets = scan_configured_secrets()
        except Exception:
            secrets = {'error': 'secrets_read_failed'}

        failures: list[str] = []
        if 'error' in quotas:
            failures.append('quota_read_failed')
        if 'error' in workers:
            failures.append('worker_read_failed')
        if 'error' in secrets:
            failures.append('secrets_read_failed')

        exhausted = [
            {'tool': s['tool'], 'email': s['email'], 'resets_at': s.get('resets_at', '')}
            for s in quotas.get('statuses', []) if s.get('exhausted')
        ]
        available_workers = [
            {
                'tool': w['tool'],
                'email': w['email'],
                'remaining': w['remaining_messages'],
                'limit': w['limit'],
            }
            for w in workers.get('workers', [])[:15]
        ]

        status = 'partial_failure' if failures else 'ok'
        return {
            'status': status,
            'read_failures': failures,
            'quota_total_tracked': quotas.get('total_tracked', 0),
            'quota_exhausted_count': quotas.get('exhausted_count', 0),
            'quota_available_count': quotas.get('available_count', 0),
            'exhausted_accounts': exhausted[:10],
            'worker_available_count': workers.get('available_count', 0),
            'worker_exhausted_count': workers.get('exhausted_count', 0),
            'worker_total_remaining_messages': workers.get('total_remaining_messages', 0),
            'workers_by_tool': list(workers.get('tools_available', [])),
            'available_workers': available_workers,
            'secrets_configured': secrets.get('configured_count', 0),
            'secrets_missing': list(secrets.get('missing', []))[:5],
        }

    def _account_resource_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        """Export account/quota/worker health to portable context.

        Ensures the next session knows: which accounts have messages left,
        which are exhausted, what tools have active workers, and what
        secrets are missing — without re-scanning everything.
        """
        items: list[dict[str, Any]] = []
        st = str(status.get('status') or 'scanner_unavailable')

        if st in ('ok', 'partial_failure'):
            for w in status.get('available_workers', [])[:8]:
                items.append({
                    'label': f"{w['tool']}: {w['email']}",
                    'remaining': w['remaining'],
                    'limit': w['limit'],
                    'status': 'available',
                })
            for e in status.get('exhausted_accounts', [])[:5]:
                items.append({
                    'label': f"{e['tool']}: {e['email']}",
                    'status': 'exhausted',
                    'resets_at': e.get('resets_at', ''),
                })
            for m in status.get('secrets_missing', [])[:3]:
                items.append({
                    'label': f'Secreto faltante: {m}',
                    'status': 'missing',
                })

        avail = status.get('worker_available_count', 0)
        exhausted = status.get('quota_exhausted_count', 0)
        remaining = status.get('worker_total_remaining_messages', 0)
        tools = status.get('workers_by_tool', [])
        missing_secrets = status.get('secrets_missing', [])

        read_failures = status.get('read_failures', [])

        if st == 'scanner_unavailable':
            summary = 'AccountResourceScanner no disponible. Cuotas y workers desconocidos.'
        elif st == 'partial_failure':
            failed = ', '.join(read_failures) if read_failures else 'lectura parcial'
            parts = [f'Lectura parcial ({failed})']
            if avail > 0:
                parts.append(f'{avail} workers disponibles')
            if exhausted > 0:
                parts.append(f'{exhausted} cuentas agotadas')
            summary = ' | '.join(parts)
        elif avail == 0 and exhausted == 0:
            summary = 'Sin cuentas rastreadas. El rastreo comienza al enviar mensajes.'
        else:
            parts = [f'{avail} workers disponibles']
            if remaining > 0:
                parts.append(f'{remaining} mensajes restantes')
            if exhausted > 0:
                parts.append(f'{exhausted} cuentas agotadas')
            if tools:
                parts.append(f'tools: {", ".join(tools)}')
            if missing_secrets:
                parts.append(f'{len(missing_secrets)} secretos faltantes')
            summary = ' | '.join(parts)

        return self._section(
            section_id='account_resource_health',
            title='Salud de cuentas, cuotas y workers',
            summary=summary,
            items=items,
            source_kind='account_resource_scanner',
            source_refs=['account_resource_scanner', 'quota_tracker.json'],
            confidence=0.85 if st == 'ok' else (0.5 if st == 'partial_failure' else 0.0),
            last_updated=now,
            metadata={
                'status': st,
                'worker_available_count': avail,
                'quota_exhausted_count': exhausted,
                'total_remaining_messages': remaining,
                'tools_available': tools,
                'secrets_configured': status.get('secrets_configured', 0),
                'secrets_missing': missing_secrets,
            },
        )

    # ------------------------------------------------------------------
    # Account inventory continuity — formal snapshot for next session
    # ------------------------------------------------------------------

    def _account_inventory_continuity_section(self, *, now) -> PortableContextSection:
        """Export formal account inventory for session continuity.

        Ensures the next session inherits: which accounts exist, their
        quota status, the continuity queue (ranked next-best accounts),
        and any UNRESOLVED items.  This section complements the lighter
        ``account_resource_health`` section with the full typed snapshot.
        """
        items: list[dict[str, Any]] = []
        unresolved_fields: list[str] = []

        try:
            from iabv_v15.services.account_resource_scanner import (
                build_inventory_snapshot,
            )
            snapshot = build_inventory_snapshot()

            # Active accounts
            for entry in snapshot.continuity_queue[:6]:
                items.append({
                    'label': f"{entry.tool}: {entry.email}",
                    'score': entry.score,
                    'quota_remaining': entry.quota_remaining,
                    'quota_limit': entry.quota_limit,
                    'status': entry.status.value,
                    'browser': entry.browser,
                })

            # Exhausted accounts
            for entry in snapshot.entries:
                if entry.exhausted and len(items) < 10:
                    resets = ''
                    if entry.quota_resets_at:
                        resets = entry.quota_resets_at.isoformat()
                    items.append({
                        'label': f"{entry.tool}: {entry.email}",
                        'status': 'exhausted',
                        'resets_at': resets,
                    })

            unresolved_fields = list(snapshot.unresolved_items)

            # Summary
            parts: list[str] = []
            if snapshot.active_count:
                parts.append(f'{snapshot.active_count} cuentas activas')
            if snapshot.exhausted_count:
                parts.append(f'{snapshot.exhausted_count} agotadas')
            parts.append(f'{snapshot.total_remaining_messages} mensajes disponibles')
            if snapshot.continuity_queue:
                top = snapshot.continuity_queue[0]
                parts.append(
                    f'siguiente recomendada: {top.email} ({top.tool}, '
                    f'score={top.score:.2f})'
                )
            if snapshot.unresolved_count:
                parts.append(f'{snapshot.unresolved_count} UNRESOLVED')
            summary = ' | '.join(parts)
            confidence = 0.85

        except Exception:
            summary = 'AccountInventorySnapshot no disponible. Continuidad de cuentas desconocida.'
            confidence = 0.0
            unresolved_fields = [
                'UNRESOLVED:account_inventory_snapshot_unavailable',
            ]

        return self._section(
            section_id='account_inventory_continuity',
            title='Inventario de cuentas y cola de continuidad',
            summary=summary,
            items=items,
            source_kind='account_resource_scanner',
            source_refs=['account_resource_scanner', 'build_inventory_snapshot'],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=unresolved_fields,
            metadata={
                'section_purpose': 'continuity_for_next_session',
                'requires_human_approval': True,
            },
        )

    # ------------------------------------------------------------------
    # Tool coordination — limit-aware selection summary
    # ------------------------------------------------------------------

    def _tool_coordination_section(self, *, now) -> PortableContextSection:
        """Export tool coordination summary for session continuity.

        Surfaces: which tool was selected, why, fallback history,
        quota states, and task affinities so the next session inherits
        the coordination context.
        """
        items: list[dict[str, Any]] = []
        summary = 'Sin datos de coordinacion de herramientas.'
        confidence = 0.3
        unresolved_fields: list[str] = []

        try:
            sessions = list((self.adaptive_session_repository.list_recent(limit=5) if self.adaptive_session_repository else []) or [])
            for session in sessions[:3]:
                meta = dict(session.metadata or {})
                tp = meta.get('task_packet') or {}
                tss = tp.get('tool_selection_summary') or {}
                selected = tss.get('selected_tool', '')
                reason = str(tss.get('reason') or '')
                if not selected and not reason:
                    continue
                label = f"seleccion:{selected}" if selected else f"decision:{reason}"
                items.append({
                    'label': label,
                    'value': f"razon={reason} fallback={tss.get('fallback_used', False)} quota_confirmed={tss.get('quota_confirmed', False)}",
                    'detail': f"alternativas_descartadas={len(tss.get('alternatives_discarded', []))}",
                })
            if items:
                summary = f'{len(items)} selecciones recientes de herramienta registradas con trazabilidad.'
                confidence = 0.7
            else:
                unresolved_fields.append('UNRESOLVED:no_recent_tool_selections')
        except Exception:
            unresolved_fields.append('UNRESOLVED:tool_coordination_read_error')

        return self._section(
            section_id='tool_coordination',
            title='Coordinacion limit-aware de herramientas',
            summary=summary,
            items=items,
            source_kind='adaptive_task_orchestrator',
            source_refs=['tool_selection_summary', 'worker_gate'],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=unresolved_fields,
        )

    # ------------------------------------------------------------------
    # Boot profile — read-only summary of BootProfileStore telemetry
    # ------------------------------------------------------------------

    def _boot_profile_snapshot(self) -> dict[str, Any]:
        """Return an aggregated boot profile for the current environment.

        Delegates to ``BootProfileStore.boot_profile_summary()`` using the
        ``environment_id`` from ``EnvironmentSelfAwarenessService``.  Pure
        observability — no decisions, no mutations.
        """
        store = self.boot_profile_store
        if store is None:
            return {'status': 'no_store'}

        env_svc = self.environment_self_awareness_service
        environment_id = ''
        if env_svc is not None and hasattr(env_svc, 'current_model'):
            try:
                model = env_svc.current_model()
                environment_id = getattr(model, 'environment_id', '') or ''
            except Exception:
                pass
        if not environment_id:
            return {'status': 'no_environment_id'}

        try:
            summary = store.boot_profile_summary(environment_id)
        except Exception:
            return {'status': 'read_error', 'environment_id': environment_id}

        summary.setdefault('status', 'no_data' if summary.get('boot_count', 0) == 0 else 'ok')
        return summary

    def _boot_profile_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        """Export boot profile telemetry as a portable context section.

        Shows environment_id, boot_count, timing stats (avg/median/p95),
        RSS peak, wiring duration, and slowest phases so that new sessions
        can see historical boot health without re-reading JSONL files.
        """
        st = str(status.get('status') or 'no_store')
        items: list[dict[str, Any]] = []
        unresolved: list[str] = []

        if st == 'ok':
            env_id = status.get('environment_id', '')
            boot_count = status.get('boot_count', 0)
            dur = status.get('boot_duration', {})
            wiring = status.get('wiring_duration', {})
            rss = status.get('rss_peak', {})

            items.append({
                'label': 'environment_id',
                'value': env_id,
            })
            items.append({
                'label': 'boot_count',
                'value': boot_count,
            })
            items.append({
                'label': 'boot_duration',
                'avg_ms': dur.get('avg_ms', 0),
                'median_ms': dur.get('median_ms', 0),
                'p95_ms': dur.get('p95_ms', 0),
            })
            items.append({
                'label': 'wiring_duration',
                'avg_ms': wiring.get('avg_ms', 0),
                'max_ms': wiring.get('max_ms', 0),
            })
            items.append({
                'label': 'rss_peak',
                'avg_mb': rss.get('avg_mb', 0),
                'max_mb': rss.get('max_mb', 0),
            })

            for sp in status.get('slowest_phases', [])[:5]:
                items.append({
                    'label': 'slowest_phase',
                    'phase': sp.get('phase', ''),
                    'avg_ms': sp.get('avg_ms', 0),
                })

            first_seen = status.get('first_seen', '')
            last_seen = status.get('last_seen', '')
            if first_seen:
                items.append({'label': 'first_seen', 'value': first_seen})
            if last_seen:
                items.append({'label': 'last_seen', 'value': last_seen})

            avg_ms = dur.get('avg_ms', 0)
            p95_ms = dur.get('p95_ms', 0)
            wiring_avg = wiring.get('avg_ms', 0)
            rss_max = rss.get('max_mb', 0)
            summary = (
                f'Boot profile ({env_id}): {boot_count} boots, '
                f'avg {avg_ms:.0f}ms, p95 {p95_ms:.0f}ms, '
                f'wiring avg {wiring_avg:.0f}ms, '
                f'RSS pico {rss_max:.0f}MB.'
            )
        elif st == 'no_data':
            env_id = status.get('environment_id', '')
            summary = f'Boot profile ({env_id}): sin datos de arranque todavia.'
            unresolved.append('UNRESOLVED:boot_profile_no_data')
        elif st == 'no_store':
            summary = 'BootProfileStore no disponible.'
            unresolved.append('UNRESOLVED:boot_profile_store_missing')
        elif st == 'no_environment_id':
            summary = 'environment_id no disponible para consultar boot profile.'
            unresolved.append('UNRESOLVED:boot_profile_no_environment_id')
        elif st == 'read_error':
            summary = 'Error al leer boot profile.'
            unresolved.append('UNRESOLVED:boot_profile_read_error')
        else:
            summary = f'Boot profile status: {st}'

        confidence = 0.85 if st == 'ok' else 0.0
        return self._section(
            section_id='boot_profile',
            title='Perfil de arranque (boot telemetry)',
            summary=summary,
            items=items,
            source_kind='boot_profile_store',
            source_refs=[
                'data/evolution/boot_profiles/',
                'iabv_v15.services.evolution.boot_profile_store',
            ],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=unresolved,
            metadata={
                'status': st,
                'environment_id': status.get('environment_id', ''),
                'boot_count': status.get('boot_count', 0),
                'boot_duration': status.get('boot_duration'),
                'wiring_duration': status.get('wiring_duration'),
                'rss_peak': status.get('rss_peak'),
                'slowest_phases': status.get('slowest_phases', []),
                'first_seen': status.get('first_seen', ''),
                'last_seen': status.get('last_seen', ''),
            },
        )

    def _evidence_basis_snapshot(
        self,
        *,
        environment: EnvironmentSelfModel,
        world: WorldModelSnapshot,
        task_context: TaskContext | None = None,
    ) -> dict[str, Any]:
        """Classify the current evidence basis for the portable package.

        Reuses ``TaskContextAssembler._classify_evidence_basis`` when
        available; otherwise falls back to a local classification using the
        same criteria (world model resolved, environment has id, persisted
        learning present).
        """
        has_world_model = bool(
            world.tool_live_status
            or world.active_windows
            or world.detected_blocks
            or float(world.confidence or 0.0) > 0.05
        )
        has_environment = bool(str(environment.environment_id or '').strip())
        has_persisted_learning = bool(
            task_context is not None
            and (
                task_context.metadata.get('adaptive_learning_summary')
                or task_context.metadata.get('learned_patterns')
            )
        )
        has_ia_trace = bool(
            task_context is not None
            and task_context.metadata.get('ia_trace')
        )
        unresolved_fields = list(world.unresolved_fields or []) + list(environment.unresolved_fields or [])

        assembler = self.task_context_assembler
        if assembler is not None and hasattr(assembler, '_classify_evidence_basis'):
            return assembler._classify_evidence_basis(
                has_world_model=has_world_model,
                has_environment=has_environment,
                has_persisted_learning=has_persisted_learning,
                has_ia_trace=has_ia_trace,
                unresolved_fields=unresolved_fields,
            )
        live: list[str] = []
        persisted: list[str] = []
        if has_world_model:
            live.append('world_model')
        if has_environment:
            live.append('environment_self_model')
        if has_persisted_learning:
            persisted.append('adaptive_learning')
        if has_ia_trace:
            persisted.append('ia_trace')
        if live:
            state = 'observed'
        elif persisted:
            state = 'inferred'
        else:
            state = 'unresolved'
        return {
            'state': state,
            'live_sources': live,
            'persisted_sources': persisted,
            'unresolved': list(unresolved_fields),
        }

    def _evidence_basis_section(
        self,
        *,
        evidence: dict[str, Any],
        now,
    ) -> PortableContextSection:
        """Export evidence basis classification as a portable context section."""
        state = str(evidence.get('state') or 'unresolved')
        live = list(evidence.get('live_sources') or [])
        persisted = list(evidence.get('persisted_sources') or [])
        unresolved = list(evidence.get('unresolved') or [])

        items: list[dict[str, Any]] = [
            {'label': 'state', 'value': state},
        ]
        if live:
            items.append({'label': 'live_sources', 'value': ', '.join(live)})
        if persisted:
            items.append({'label': 'persisted_sources', 'value': ', '.join(persisted)})
        if unresolved:
            items.append({'label': 'unresolved_fields', 'value': ', '.join(unresolved)})

        if state == 'observed':
            summary = f'Evidencia observada en vivo ({", ".join(live)}). Fuentes persistidas: {", ".join(persisted) or "ninguna"}.'
        elif state == 'inferred':
            summary = f'Evidencia inferida de persistencia ({", ".join(persisted)}). Sin fuentes vivas confirmadas.'
        else:
            summary = 'Sin evidencia confirmada. Todas las fuentes están sin resolver.'

        section_unresolved: list[str] = []
        if state == 'unresolved':
            section_unresolved.append('UNRESOLVED:evidence_basis_no_sources')

        confidence = 0.9 if state == 'observed' else (0.6 if state == 'inferred' else 0.0)
        return self._section(
            section_id='evidence_basis',
            title='Base evidencial del contexto',
            summary=summary,
            items=items,
            source_kind='task_context_assembler',
            source_refs=[
                'iabv_v15.services.adaptive.task_context_assembler',
                'WorldModelSnapshot',
                'EnvironmentSelfModel',
            ],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=section_unresolved,
            metadata=dict(evidence),
        )

    # ------------------------------------------------------------------
    # P0.29 — Test evidence compact section
    # ------------------------------------------------------------------

    def _test_evidence_section(self, *, now) -> PortableContextSection:
        """Export compact test evidence summary without logs or PII."""
        evidence = self._load_test_evidence()
        if evidence is None:
            return self._section(
                section_id='test_evidence',
                title='Evidencia de tests',
                summary='Sin evidencia de tests reciente.',
                items=[{'label': 'status', 'value': 'no_recent_evidence'}],
                source_kind='audit_tools',
                source_refs=['iabv_v15.infra.mcp.audit_tools'],
                confidence=0.0,
                last_updated=now,
                unresolved_fields=['UNRESOLVED:no_test_evidence'],
            )
        passed = int(evidence.get('passed') or 0)
        failed = int(evidence.get('failed') or 0)
        errors = int(evidence.get('errors') or 0)
        suite = str(evidence.get('suite') or '')
        ts = str(evidence.get('timestamp') or '')
        total = passed + failed + errors
        health = 'green' if failed == 0 and errors == 0 else 'red'
        summary = f'{passed}/{total} passed'
        if failed:
            summary += f', {failed} failed'
        if errors:
            summary += f', {errors} errors'
        if suite:
            summary += f' [{suite}]'
        items: list[dict[str, Any]] = [
            {'label': 'health', 'value': health},
            {'label': 'passed', 'value': passed},
            {'label': 'failed', 'value': failed},
            {'label': 'errors', 'value': errors},
            {'label': 'timestamp', 'value': ts},
        ]
        if suite:
            items.append({'label': 'suite', 'value': suite})
        return self._section(
            section_id='test_evidence',
            title='Evidencia de tests',
            summary=summary,
            items=items,
            source_kind='audit_tools',
            source_refs=['iabv_v15.infra.mcp.audit_tools'],
            confidence=0.9 if health == 'green' else 0.5,
            last_updated=now,
        )

    def _load_test_evidence(self) -> dict[str, Any] | None:
        """Load latest TestEvidence from workspace root — best-effort."""
        try:
            from iabv_v15.infra.mcp.audit_tools import load_latest_test_evidence
            return load_latest_test_evidence(self.workspace_root)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Task-packet summary — metacognitive digest of recent task_packet
    # fields persisted by TaskOutcomeRecorder into ExperimentRun.metadata.
    # ------------------------------------------------------------------

    _TASK_PACKET_MIN_RUNS = 3

    @staticmethod
    def _worker_label(sw: Any) -> str:
        """Extract a human-readable label from a selected_worker dict.

        Recognises the real shape produced by worker_health_gate /
        _build_task_packet (tool, email, browser, profile) and falls back
        to assistant_kind / name if present.
        """
        if not isinstance(sw, dict) or not sw:
            return ''
        tool = str(sw.get('tool') or '').strip()
        email = str(sw.get('email') or '').strip()
        if tool and email:
            return f'{tool}:{email}'
        if tool:
            return tool
        browser = str(sw.get('browser') or '').strip()
        profile = str(sw.get('profile') or '').strip()
        if browser and profile:
            return f'{browser}:{profile}'
        if browser:
            return browser
        name = str(sw.get('name') or sw.get('assistant_kind') or '').strip()
        return name

    def _task_packet_summary_snapshot(self) -> dict[str, Any]:
        repo = self.experiment_lab_repository
        if repo is None or not hasattr(repo, 'list_runs'):
            return {'status': 'no_repository', 'run_count': 0}
        try:
            runs = list(repo.list_runs(limit=60))
        except Exception:
            return {'status': 'read_error', 'run_count': 0}
        if not runs:
            return {'status': 'no_data', 'run_count': 0}

        evidence_states: Counter[str] = Counter()
        approval_count = 0
        gate_ran_unusable = 0
        no_worker_count = 0
        unresolved_all: Counter[str] = Counter()
        worker_labels: Counter[str] = Counter()
        total = 0

        wt_budget_exhausted = 0
        wt_handoff_count = 0
        wt_human_intervention = 0
        wt_worker_kinds: Counter[str] = Counter()
        wt_total = 0

        for run in runs:
            meta = run.metadata or {}
            eb = meta.get('evidence_basis')
            if not isinstance(eb, dict):
                continue
            total += 1
            state = str(eb.get('state') or 'unresolved').lower()
            evidence_states[state] += 1

            gf = meta.get('governance_flags') or {}
            if isinstance(gf, dict) and gf.get('approval_required'):
                approval_count += 1

            should_consult = bool(gf.get('should_consult')) if isinstance(gf, dict) else False

            sw = meta.get('selected_worker')
            wlabel = self._worker_label(sw)
            if wlabel:
                worker_labels[wlabel] += 1
            elif should_consult:
                no_worker_count += 1

            rwc = meta.get('ranked_worker_count')
            if should_consult and isinstance(rwc, int) and rwc == 0:
                gate_ran_unusable += 1

            tu = meta.get('task_unresolved')
            if isinstance(tu, list):
                for field in tu:
                    if isinstance(field, str) and field.strip():
                        unresolved_all[field.strip()] += 1

            wt = meta.get('worker_telemetry')
            if isinstance(wt, dict) and wt.get('worker_kind'):
                wt_total += 1
                wt_worker_kinds[str(wt['worker_kind'])] += 1
                bs = str(wt.get('budget_state') or '').lower()
                if bs in {'exhausted', 'quota_exceeded', 'timeout'}:
                    wt_budget_exhausted += 1
                if wt.get('handoff_required'):
                    wt_handoff_count += 1
                if wt.get('human_intervention_required'):
                    wt_human_intervention += 1

        if total < self._TASK_PACKET_MIN_RUNS:
            return {'status': 'insufficient_data', 'run_count': total}

        top_unresolved = unresolved_all.most_common(5)
        top_workers = worker_labels.most_common(5)

        result: dict[str, Any] = {
            'status': 'ok',
            'run_count': total,
            'evidence_state_distribution': dict(evidence_states),
            'approval_required_count': approval_count,
            'approval_required_rate': round(approval_count / total, 3) if total else 0.0,
            'gate_ran_unusable_count': gate_ran_unusable,
            'no_worker_count': no_worker_count,
            'unresolved_hotspots': [
                {'field': f, 'count': c} for f, c in top_unresolved
            ],
            'worker_tendencies': [
                {'worker': w, 'count': c, 'rate': round(c / total, 3)}
                for w, c in top_workers
            ],
        }
        if wt_total > 0:
            # Collect scientific proxy aggregates
            cr_vals: list[float] = []
            ep_vals: list[float] = []
            idp_vals: list[int] = []
            scores_for_stability: list[float] = []
            for run in runs:
                wt2 = (run.metadata or {}).get('worker_telemetry')
                if not isinstance(wt2, dict):
                    continue
                if isinstance(wt2.get('compression_ratio'), (int, float)):
                    cr_vals.append(float(wt2['compression_ratio']))
                if isinstance(wt2.get('entropy_proxy'), (int, float)):
                    ep_vals.append(float(wt2['entropy_proxy']))
                if isinstance(wt2.get('inference_depth_proxy'), int):
                    idp_vals.append(wt2['inference_depth_proxy'])
                if hasattr(run, 'total_score') and isinstance(run.total_score, (int, float)):
                    scores_for_stability.append(float(run.total_score))

            wt_summary: dict[str, Any] = {
                'runs_with_telemetry': wt_total,
                'budget_exhausted_count': wt_budget_exhausted,
                'handoff_required_count': wt_handoff_count,
                'human_intervention_count': wt_human_intervention,
                'worker_kind_distribution': [
                    {'kind': k, 'count': c, 'rate': round(c / wt_total, 3)}
                    for k, c in wt_worker_kinds.most_common(5)
                ],
            }
            if cr_vals:
                wt_summary['avg_compression_ratio'] = round(sum(cr_vals) / len(cr_vals), 4)
            if ep_vals:
                wt_summary['avg_entropy_proxy'] = round(sum(ep_vals) / len(ep_vals), 4)
            if idp_vals:
                wt_summary['avg_inference_depth'] = round(sum(idp_vals) / len(idp_vals), 2)
            if len(scores_for_stability) >= 2:
                try:
                    from iabv_v15.services.lab.scientific_proxy_engine import (
                        stability_score_from_runs,
                        nonlinearity_indicator,
                    )
                    wt_summary['stability_score'] = stability_score_from_runs(scores_for_stability)
                    wt_summary['nonlinearity_indicator'] = nonlinearity_indicator(scores_for_stability)
                except Exception:
                    pass

            # Metacognitive calibration summary
            cal_errors: list[float] = []
            fp_count = 0
            fn_count = 0
            for run in runs:
                mc = (run.metadata or {}).get('metacognitive_evaluation')
                if not isinstance(mc, dict):
                    continue
                ce = mc.get('calibration_error')
                if isinstance(ce, (int, float)):
                    cal_errors.append(float(ce))
                if mc.get('false_positive'):
                    fp_count += 1
                if mc.get('false_negative'):
                    fn_count += 1
            if cal_errors:
                wt_summary['metacognitive_calibration'] = {
                    'avg_calibration_error': round(sum(cal_errors) / len(cal_errors), 4),
                    'max_calibration_error': round(max(cal_errors), 4),
                    'false_positive_count': fp_count,
                    'false_negative_count': fn_count,
                    'evaluations_count': len(cal_errors),
                }

            result['worker_telemetry_summary'] = wt_summary
        return result

    def _task_packet_summary_section(
        self,
        *,
        snapshot: dict[str, Any],
        now: datetime,
    ) -> PortableContextSection:
        st = snapshot.get('status', 'no_data')
        total = snapshot.get('run_count', 0)
        items: list[dict[str, Any]] = []
        unresolved: list[str] = []

        if st == 'ok':
            dist = snapshot.get('evidence_state_distribution', {})
            items.append({
                'label': 'evidence_state_distribution',
                'value': ', '.join(f'{k}: {v}' for k, v in dist.items()),
            })
            items.append({
                'label': 'approval_required',
                'value': f"{snapshot.get('approval_required_count', 0)}/{total} ({snapshot.get('approval_required_rate', 0):.1%})",
            })
            items.append({
                'label': 'gate_unusable_or_no_worker',
                'value': f"gate_unusable={snapshot.get('gate_ran_unusable_count', 0)}, no_worker={snapshot.get('no_worker_count', 0)}",
            })
            hotspots = snapshot.get('unresolved_hotspots', [])
            if hotspots:
                items.append({
                    'label': 'unresolved_hotspots',
                    'value': ', '.join(f"{h['field']}({h['count']})" for h in hotspots[:5]),
                })
            workers = snapshot.get('worker_tendencies', [])
            if workers:
                items.append({
                    'label': 'worker_tendencies',
                    'value': ', '.join(
                        f"{w['worker']}: {w['count']} ({w['rate']:.0%})" for w in workers[:5]
                    ),
                })

            obs = dist.get('observed', 0)
            inf = dist.get('inferred', 0)
            unres = dist.get('unresolved', 0)
            if total > 0 and obs >= inf and obs >= unres:
                summary = f'Task-packet digest de {total} runs: evidencia predominantemente observed ({obs}/{total}).'
            elif total > 0 and unres > obs:
                summary = f'Task-packet digest de {total} runs: ratio alto de unresolved ({unres}/{total}).'
            else:
                summary = f'Task-packet digest de {total} runs: evidencia mixta (obs={obs}, inf={inf}, unres={unres}).'
            confidence = 0.85
        elif st == 'insufficient_data':
            summary = f'Task-packet: solo {total} runs, insuficiente para resumir patrones.'
            unresolved.append('UNRESOLVED:task_packet_insufficient_data')
            confidence = 0.0
        elif st == 'no_data':
            summary = 'Task-packet: sin datos de runs recientes.'
            unresolved.append('UNRESOLVED:task_packet_no_data')
            confidence = 0.0
        elif st == 'no_repository':
            summary = 'Task-packet: repositorio de experimentos no disponible.'
            unresolved.append('UNRESOLVED:task_packet_no_repository')
            confidence = 0.0
        else:
            summary = f'Task-packet: status {st}.'
            unresolved.append(f'UNRESOLVED:task_packet_{st}')
            confidence = 0.0

        return self._section(
            section_id='task_packet_summary',
            title='Task-packet pattern summary',
            summary=summary,
            items=items,
            source_kind='experiment_lab_repository',
            source_refs=[
                'ExperimentLab',
                'TaskOutcomeRecorder',
            ],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=unresolved,
            metadata=snapshot,
        )

    def _cloud_reasoning_snapshot(self) -> dict[str, Any]:
        audit = getattr(self, 'decision_audit_trail', None)
        if audit is None:
            return {
                'status': 'not_configured',
                'health_score': 0.0,
                'overall_trend': 'unknown',
                'total_decisions': 0,
                'trends': [],
                'recommendations': [],
            }
        try:
            return audit.self_examination_summary()
        except Exception:
            return {
                'status': 'error',
                'health_score': 0.0,
                'overall_trend': 'unknown',
                'total_decisions': 0,
                'trends': [],
                'recommendations': [],
            }

    def _chat_stats_snapshot(self) -> dict[str, Any]:
        """Snapshot of chat persistence stats for the portable context."""
        repo = self.chat_message_repository
        if repo is None:
            return {'status': 'not_configured', 'total': 0}
        try:
            total = repo.count()
            if total == 0:
                return {'status': 'empty', 'total': 0}
            recent = repo.list_recent(limit=100)
            sessions = repo.list_sessions()
            path_counts: dict[str, int] = {}
            evidence_counts: dict[str, int] = {}
            for msg in recent:
                p = msg.get('reasoning_path', '') or 'untagged'
                path_counts[p] = path_counts.get(p, 0) + 1
                e = msg.get('evidence_tag', '') or 'untagged'
                evidence_counts[e] = evidence_counts.get(e, 0) + 1
            audit = getattr(self, 'decision_audit_trail', None)
            routing_summary = {}
            if audit is not None and hasattr(audit, 'chat_routing_summary'):
                try:
                    routing_summary = audit.chat_routing_summary()
                except Exception:
                    pass
            return {
                'status': 'active',
                'total': total,
                'sessions': len(sessions),
                'recent_sample': len(recent),
                'by_reasoning_path': path_counts,
                'by_evidence_tag': evidence_counts,
                'routing_decisions': routing_summary,
            }
        except Exception:
            return {'status': 'error', 'total': 0}

    def _tool_discovery_snapshot(self) -> dict[str, Any]:
        service = self.tool_discovery_service
        if service is None or not hasattr(service, 'current_status'):
            return {
                'summary': '',
                'summary_payload': {},
                'signals': [],
                'unresolved_fields': ['UNRESOLVED:tool_discovery'],
            }
        try:
            status = service.current_status(refresh=True)
            summary_payload = dict(service.status_summary(status) or {}) if hasattr(service, 'status_summary') else {}
            return {
                'summary': str(getattr(status, 'summary', '') or ''),
                'summary_payload': summary_payload,
                'signals': [item.model_dump(mode='json') for item in list(getattr(status, 'signals', []) or [])[:8]],
                'unresolved_fields': list(getattr(status, 'unresolved_fields', []) or []),
            }
        except Exception:
            return {
                'summary': '',
                'summary_payload': {},
                'signals': [],
                'unresolved_fields': ['UNRESOLVED:tool_discovery'],
            }

    def _tool_evolution_snapshot(self) -> dict[str, Any]:
        service = self.tool_evolution_monitor
        if service is None or not hasattr(service, 'current_status'):
            return {
                'summary': '',
                'summary_payload': {},
                'performance': [],
                'proposals': [],
                'degraded_subjects': [],
                'unresolved_fields': ['UNRESOLVED:tool_evolution'],
            }
        try:
            status = service.current_status(refresh=True)
            if hasattr(service, 'status_summary'):
                summary_payload = dict(service.status_summary(status) or {})
            else:
                summary_payload = {}
            return {
                'summary': str(getattr(status, 'summary', '') or ''),
                'summary_payload': summary_payload,
                'performance': [item.model_dump(mode='json') for item in list(getattr(status, 'performance', []) or [])[:6]],
                'proposals': [item.model_dump(mode='json') for item in list(getattr(status, 'proposals', []) or [])[:6]],
                'degraded_subjects': list(getattr(status, 'degraded_subjects', []) or [])[:8],
                'unresolved_fields': list(getattr(status, 'unresolved_fields', []) or []),
            }
        except Exception:
            return {
                'summary': '',
                'summary_payload': {},
                'performance': [],
                'proposals': [],
                'degraded_subjects': [],
                'unresolved_fields': ['UNRESOLVED:tool_evolution'],
            }

    def _tool_evolution_decision_snapshot(self) -> dict[str, Any]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_decision_log'):
            return {
                'summary': '',
                'summary_payload': {},
                'entries': [],
                'unresolved_fields': ['UNRESOLVED:tool_evolution_decisions'],
            }
        try:
            log = service.current_decision_log()
            summary_payload = dict(service.decision_log_summary(log) or {}) if hasattr(service, 'decision_log_summary') else {}
            return {
                'summary': str(summary_payload.get('last_decision', {}).get('reason') or ''),
                'summary_payload': summary_payload,
                'entries': [item.model_dump(mode='json') for item in list(getattr(log, 'entries', []) or [])[-6:]],
                'unresolved_fields': list(getattr(log, 'unresolved_fields', []) or []),
            }
        except Exception:
            return {
                'summary': '',
                'summary_payload': {},
                'entries': [],
                'unresolved_fields': ['UNRESOLVED:tool_evolution_decisions'],
            }

    def _recommendation_items(self, *, task_context: TaskContext | None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if task_context is not None:
            for insight in task_context.experiment_insights[:6]:
                items.append(
                    {
                        'subject_key': str(insight.get('subject_key') or ''),
                        'domain': str(insight.get('domain') or ''),
                        'recommended_route': str(insight.get('recommended_route') or ''),
                        'recommended_assistant_kind': str(insight.get('recommended_assistant_kind') or ''),
                        'recommended_config_signature': str(insight.get('recommended_config_signature') or ''),
                        'score': float(insight.get('score') or 0.0),
                        'confidence': float(insight.get('confidence') or 0.0),
                        'rationale': str(insight.get('rationale') or ''),
                        'supporting_run_ids': list(insight.get('supporting_run_ids') or []),
                        'comparison_scope_keys': list(insight.get('comparison_scope_keys') or []),
                        'metadata': dict(insight.get('metadata') or {}),
                        'created_at_utc': str(insight.get('created_at_utc') or ''),
                    }
                )
        if items:
            return items[:6]
        repository = self.experiment_lab_repository
        if repository is None:
            return []
        try:
            for recommendation in repository.list_recommendations(limit=6):
                metadata = dict(recommendation.metadata or {})
                items.append(
                    {
                        'subject_key': recommendation.subject_key,
                        'domain': recommendation.domain.value,
                        'recommended_route': recommendation.recommended_route.value,
                        'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                        'recommended_config_signature': recommendation.recommended_config_signature,
                        'score': float(recommendation.score or 0.0),
                        'confidence': float(recommendation.confidence or 0.0),
                        'rationale': str(recommendation.rationale or ''),
                        'supporting_run_ids': list(recommendation.supporting_run_ids or []),
                        'comparison_scope_keys': list(metadata.get('comparison_scope_keys') or []),
                        'metadata': metadata,
                        'created_at_utc': recommendation.created_at_utc.isoformat(),
                    }
                )
        except Exception:
            return items
        return items[:6]

    def _adaptive_learning_summary(self, *, task_context: TaskContext | None, recommendations: list[dict[str, Any]]) -> dict[str, Any]:
        if task_context is not None:
            summary = dict(task_context.metadata.get('adaptive_learning_summary') or {})
            if summary:
                return summary
        best = next(iter(recommendations), None)
        if not best:
            return {}
        metadata = dict(best.get('metadata') or {})
        adaptive = dict(metadata.get('adaptive_learning_summary') or {})
        return {
            'subject_key': str(best.get('subject_key') or ''),
            'domain': str(best.get('domain') or ''),
            'recommended_route': str(best.get('recommended_route') or ''),
            'recommended_assistant_kind': str(best.get('recommended_assistant_kind') or ''),
            'confidence': float(best.get('confidence') or 0.0),
            'score': float(best.get('score') or 0.0),
            'reasons': list(adaptive.get('reasons') or []),
            'top_environment_signatures': list(adaptive.get('top_environment_signatures') or []),
            'top_time_buckets': list(adaptive.get('top_time_buckets') or []),
        }

    def _learned_patterns(self, *, task_context: TaskContext | None, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if task_context is not None:
            patterns = list(task_context.metadata.get('learned_patterns') or [])
            if patterns:
                return patterns[:3]
        items: list[dict[str, Any]] = []
        for recommendation in recommendations[:3]:
            adaptive = dict(dict(recommendation.get('metadata') or {}).get('adaptive_learning_summary') or {})
            items.append(
                {
                    'subject_key': str(recommendation.get('subject_key') or ''),
                    'domain': str(recommendation.get('domain') or ''),
                    'recommended_route': str(recommendation.get('recommended_route') or ''),
                    'recommended_assistant_kind': str(recommendation.get('recommended_assistant_kind') or ''),
                    'reasons': list(adaptive.get('reasons') or []),
                }
            )
        return items

    # ------------------------------------------------------------------
    # Auto-derived learned patterns from ExperimentLab (Brecha 3.1)
    # ------------------------------------------------------------------

    def derive_learned_patterns(self) -> list[dict[str, Any]]:
        """Convert training corpus into learned_patterns for portable context.

        Calls ``ExperimentLab.generate_training_corpus()`` and formats each
        example as a learned_pattern compatible with ``StrategySelector``.
        """
        lab = self.experiment_lab
        if lab is None or not hasattr(lab, 'generate_training_corpus'):
            return []
        corpus = lab.generate_training_corpus()
        patterns: list[dict[str, Any]] = []
        for example in corpus:
            patterns.append({
                'pattern_id': f"auto_{example['task_type']}_{example['recommended_assistant']}",
                'task_type': example['task_type'],
                'recommended_route': example['recommended_route'],
                'recommended_assistant_kind': example['recommended_assistant'],
                'confidence': example['confidence'],
                'success_count': example['sample_size'],
                'source': 'experiment_lab_corpus',
                'derived_at_utc': utc_now().isoformat(),
            })
        return patterns

    def _build_coordination_patterns(self) -> list[dict[str, Any]]:
        """Fetch experiment runs and detect coordination patterns."""
        repo = self.experiment_lab_repository
        if repo is None or not hasattr(repo, 'list_runs'):
            return []
        try:
            runs = list(repo.list_runs(limit=60))
        except Exception:
            return []
        return self._detect_coordination_patterns(runs)

    def _coordination_patterns_section(
        self,
        *,
        coordination_patterns: list[dict[str, Any]],
        now: Any,
    ) -> PortableContextSection:
        items = [dict(p) for p in coordination_patterns[:8]]
        if items:
            summary = f'{len(items)} coordination pattern(s) detected across IAs.'
        else:
            summary = 'No IA-IA coordination patterns detected yet.'
        return self._section(
            section_id='coordination_patterns',
            title='Patrones de coordinacion IA-IA',
            summary=summary,
            items=items,
            source_kind='persistent_learning',
            source_refs=['ExperimentLab', 'ia_trace_summary'],
            confidence=0.75 if items else 0.0,
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:coordination_patterns'],
        )

    # ------------------------------------------------------------------
    # IA-IA coordination pattern detection (Brecha 3.2)
    # ------------------------------------------------------------------

    def _detect_coordination_patterns(
        self,
        experiment_runs: list[Any],
        task_outcomes: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect recurring coordination patterns between IAs.

        Patterns detected:
        1. SPECIALIZATION: IA X consistently better for domain Y
        2. COMPLEMENTARY: IA X good at generation, IA Y good at validation
        3. SEQUENCE: Pattern "local-first then cloud-validate" works better
        4. FALLBACK: IA X fails -> IA Y succeeds (reliable fallback chain)

        Returns list of patterns, each:
        {
            'pattern_type': 'SPECIALIZATION' | 'COMPLEMENTARY' | 'SEQUENCE' | 'FALLBACK',
            'primary_ia': str,
            'secondary_ia': str | None,
            'domain': str,
            'confidence': float,
            'sample_size': int,
            'description': str,
        }
        """
        if not experiment_runs:
            return []
        patterns: list[dict[str, Any]] = []
        patterns.extend(self._detect_specialization_patterns(experiment_runs))
        patterns.extend(self._detect_fallback_patterns(experiment_runs))
        patterns.extend(self._detect_complementary_patterns(experiment_runs))
        patterns.extend(self._detect_sequence_patterns(experiment_runs))
        return patterns

    def _detect_specialization_patterns(
        self,
        runs: list[Any],
    ) -> list[dict[str, Any]]:
        """SPECIALIZATION: IA with >70% success in a domain AND >20% above average."""
        from collections import defaultdict

        domain_assistant_runs: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
        for run in runs:
            domain = str(run.domain.value if hasattr(run.domain, 'value') else run.domain or '').strip()
            assistant = str(run.assistant_kind or '').strip().lower()
            if not domain or not assistant:
                continue
            domain_assistant_runs[domain][assistant].append(bool(run.success))

        patterns: list[dict[str, Any]] = []
        for domain, assistants in domain_assistant_runs.items():
            all_results = [s for results in assistants.values() for s in results]
            if not all_results:
                continue
            avg_success = sum(all_results) / len(all_results)
            for assistant, results in assistants.items():
                if len(results) < 5:
                    continue
                success_rate = sum(results) / len(results)
                if success_rate > 0.7 and success_rate > avg_success + 0.2:
                    patterns.append({
                        'pattern_type': 'SPECIALIZATION',
                        'primary_ia': assistant,
                        'secondary_ia': None,
                        'domain': domain,
                        'confidence': round(min(1.0, 0.5 + len(results) * 0.05), 4),
                        'sample_size': len(results),
                        'description': (
                            f'{assistant} specializes in {domain}: '
                            f'{success_rate:.0%} success ({len(results)} runs) '
                            f'vs {avg_success:.0%} average.'
                        ),
                    })
        return patterns

    def _detect_fallback_patterns(
        self,
        runs: list[Any],
    ) -> list[dict[str, Any]]:
        """FALLBACK: IA-A fails + IA-B succeeds on same comparison_scope_key >= 3 times."""
        from collections import defaultdict

        scope_runs: dict[str, list[Any]] = defaultdict(list)
        for run in runs:
            scope_key = str((run.metadata or {}).get('comparison_scope_key') or '').strip()
            if not scope_key:
                scope_key = str(run.comparison_scope_key if hasattr(run, 'comparison_scope_key') else '').strip()
            if scope_key:
                scope_runs[scope_key].append(run)

        fallback_counter: dict[tuple[str, str], int] = defaultdict(int)
        for scope_key, scope_group in scope_runs.items():
            failed = [r for r in scope_group if not r.success]
            succeeded = [r for r in scope_group if r.success]
            for f in failed:
                f_kind = str(f.assistant_kind or '').strip().lower()
                if not f_kind:
                    continue
                for s in succeeded:
                    s_kind = str(s.assistant_kind or '').strip().lower()
                    if not s_kind or s_kind == f_kind:
                        continue
                    fallback_counter[(f_kind, s_kind)] += 1

        patterns: list[dict[str, Any]] = []
        for (failed_ia, success_ia), count in fallback_counter.items():
            if count >= 3:
                patterns.append({
                    'pattern_type': 'FALLBACK',
                    'primary_ia': failed_ia,
                    'secondary_ia': success_ia,
                    'domain': 'cross-domain',
                    'confidence': round(min(1.0, 0.4 + count * 0.1), 4),
                    'sample_size': count,
                    'description': (
                        f'When {failed_ia} fails, {success_ia} succeeds '
                        f'({count} occurrences). Reliable fallback chain.'
                    ),
                })
        return patterns

    def _detect_complementary_patterns(
        self,
        runs: list[Any],
    ) -> list[dict[str, Any]]:
        """COMPLEMENTARY: Different IAs win in different domains."""
        from collections import defaultdict

        domain_winners: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for run in runs:
            if not run.success:
                continue
            domain = str(run.domain.value if hasattr(run.domain, 'value') else run.domain or '').strip()
            assistant = str(run.assistant_kind or '').strip().lower()
            if not domain or not assistant:
                continue
            domain_winners[domain][assistant] += 1

        best_per_domain: dict[str, tuple[str, int]] = {}
        for domain, assistants in domain_winners.items():
            if not assistants:
                continue
            best = max(assistants.items(), key=lambda item: item[1])
            if best[1] >= 3:
                best_per_domain[domain] = best

        unique_winners = {ia for ia, _ in best_per_domain.values()}
        if len(unique_winners) < 2:
            return []

        patterns: list[dict[str, Any]] = []
        winner_list = sorted(unique_winners)
        for i, ia_a in enumerate(winner_list):
            for ia_b in winner_list[i + 1:]:
                domains_a = [d for d, (w, _) in best_per_domain.items() if w == ia_a]
                domains_b = [d for d, (w, _) in best_per_domain.items() if w == ia_b]
                if not domains_a or not domains_b:
                    continue
                total_samples = sum(
                    c for d, (w, c) in best_per_domain.items()
                    if w in (ia_a, ia_b)
                )
                patterns.append({
                    'pattern_type': 'COMPLEMENTARY',
                    'primary_ia': ia_a,
                    'secondary_ia': ia_b,
                    'domain': f'{",".join(sorted(domains_a))} vs {",".join(sorted(domains_b))}',
                    'confidence': round(min(1.0, 0.5 + total_samples * 0.02), 4),
                    'sample_size': total_samples,
                    'description': (
                        f'{ia_a} excels at {",".join(sorted(domains_a))}; '
                        f'{ia_b} excels at {",".join(sorted(domains_b))}. '
                        f'Complementary strengths.'
                    ),
                })
        return patterns

    def _detect_sequence_patterns(
        self,
        runs: list[Any],
    ) -> list[dict[str, Any]]:
        """SEQUENCE: 'local-first then cloud-validate' vs 'cloud direct'."""
        from collections import defaultdict

        scope_runs: dict[str, list[Any]] = defaultdict(list)
        for run in runs:
            scope_key = str((run.metadata or {}).get('comparison_scope_key') or '').strip()
            if not scope_key:
                scope_key = str(run.comparison_scope_key if hasattr(run, 'comparison_scope_key') else '').strip()
            if scope_key:
                scope_runs[scope_key].append(run)

        local_first_wins = 0
        cloud_direct_wins = 0
        total_sequences = 0
        for scope_key, scope_group in scope_runs.items():
            if len(scope_group) < 2:
                continue
            sorted_runs = sorted(scope_group, key=lambda r: r.created_at_utc)
            first_route = str(sorted_runs[0].route.value if hasattr(sorted_runs[0].route, 'value') else sorted_runs[0].route or '').lower()
            has_local_first = first_route in ('local', 'background', 'ui')
            has_cloud_validation = any(
                str(r.route.value if hasattr(r.route, 'value') else r.route or '').lower() in ('cloud', 'api')
                for r in sorted_runs[1:]
            )
            if has_local_first and has_cloud_validation:
                total_sequences += 1
                if any(r.success for r in sorted_runs):
                    local_first_wins += 1
            elif first_route in ('cloud', 'api') and len(scope_group) == 1:
                total_sequences += 1
                if sorted_runs[0].success:
                    cloud_direct_wins += 1

        if total_sequences < 5:
            return []

        patterns: list[dict[str, Any]] = []
        if local_first_wins > cloud_direct_wins and local_first_wins >= 3:
            patterns.append({
                'pattern_type': 'SEQUENCE',
                'primary_ia': 'local',
                'secondary_ia': 'cloud',
                'domain': 'cross-domain',
                'confidence': round(min(1.0, 0.4 + local_first_wins * 0.08), 4),
                'sample_size': total_sequences,
                'description': (
                    f'"local-first then cloud-validate" wins '
                    f'{local_first_wins}/{total_sequences} sequences '
                    f'vs cloud-direct {cloud_direct_wins}/{total_sequences}.'
                ),
            })
        elif cloud_direct_wins > local_first_wins and cloud_direct_wins >= 3:
            patterns.append({
                'pattern_type': 'SEQUENCE',
                'primary_ia': 'cloud',
                'secondary_ia': 'local',
                'domain': 'cross-domain',
                'confidence': round(min(1.0, 0.4 + cloud_direct_wins * 0.08), 4),
                'sample_size': total_sequences,
                'description': (
                    f'"cloud-direct" wins '
                    f'{cloud_direct_wins}/{total_sequences} sequences '
                    f'vs local-first {local_first_wins}/{total_sequences}.'
                ),
            })
        return patterns

    def _pending_items(self) -> list[dict[str, Any]]:
        repository = self.pending_issue_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        items: list[dict[str, Any]] = []
        try:
            for issue in repository.list_recent(limit=6):
                items.append(
                    {
                        'issue_id': str(getattr(issue, 'issue_id', '') or ''),
                        'summary': str(getattr(issue, 'summary', '') or ''),
                        'category': str(getattr(getattr(issue, 'category', None), 'value', getattr(issue, 'category', '')) or ''),
                        'status': str(getattr(getattr(issue, 'status', None), 'value', getattr(issue, 'status', '')) or ''),
                        'probable_cause': str(getattr(issue, 'probable_cause', '') or ''),
                        'recommended_change': str(getattr(issue, 'recommended_change', '') or ''),
                        'updated_at_utc': str(getattr(issue, 'created_at_utc', '') or ''),
                    }
                )
        except Exception:
            return []
        return items

    def _backlog_items(self) -> list[dict[str, Any]]:
        service = self.evolution_review_service
        if service is None or not hasattr(service, 'build_improvement_backlog'):
            return []
        items: list[dict[str, Any]] = []
        try:
            for proposal in service.build_improvement_backlog(limit=6):
                items.append(
                    {
                        'title': str(getattr(proposal, 'title', '') or ''),
                        'rationale': str(getattr(proposal, 'rationale', '') or ''),
                        'recommended_change': str(getattr(proposal, 'recommended_change', '') or ''),
                        'priority_score': int(getattr(proposal, 'priority_score', 0) or 0),
                        'suggested_tests': list(getattr(proposal, 'suggested_tests', []) or []),
                    }
                )
        except Exception:
            return []
        return items

    def _decision_history(self, *, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for recommendation in recommendations[:5]:
            adaptive = dict(dict(recommendation.get('metadata') or {}).get('adaptive_learning_summary') or {})
            reasons = [str(item).strip() for item in (adaptive.get('reasons') or []) if str(item).strip()]
            history.append(
                {
                    'subject_key': str(recommendation.get('subject_key') or ''),
                    'assistant_kind': str(recommendation.get('recommended_assistant_kind') or ''),
                    'route': str(recommendation.get('recommended_route') or ''),
                    'why': reasons[0] if reasons else str(recommendation.get('rationale') or ''),
                    'comparison_scope_keys': list(recommendation.get('comparison_scope_keys') or []),
                    'created_at_utc': str(recommendation.get('created_at_utc') or ''),
                }
            )
        return history

    def _unresolved_fields(
        self,
        *,
        environment: EnvironmentSelfModel,
        world: WorldModelSnapshot,
        validation: dict[str, Any],
        recommendations: list[dict[str, Any]],
        goal_context: dict[str, Any],
    ) -> list[str]:
        unresolved: list[str] = []
        for item in list(environment.unresolved_fields or []) + list(world.unresolved_fields or []):
            text = str(item).strip()
            if text and text not in unresolved:
                unresolved.append(text)
        for item in list(validation.get('unresolved_fields') or []):
            text = str(item).strip()
            if text and text not in unresolved:
                unresolved.append(text)
        if not recommendations:
            unresolved.append('UNRESOLVED:recommendation_history')
        if not str(goal_context.get('active_title') or '').strip():
            unresolved.append('UNRESOLVED:active_goal_context')
        return unresolved

    def _project_state_section(
        self,
        *,
        goal_context: dict[str, Any],
        project_health: dict[str, Any],
        validation: dict[str, Any],
        world: WorldModelSnapshot,
        now,
    ) -> PortableContextSection:
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        items = [
            {'label': 'Objetivo activo', 'value': str(objective.get('title') or goal_context.get('active_title') or 'sin objetivo activo confirmado')},
            {'label': 'Proyecto activo', 'value': str(project.get('title') or 'sin proyecto activo confirmado')},
            {'label': 'Tarea activa', 'value': str(task.get('title') or 'sin tarea activa confirmada')},
            {'label': 'Pulso evolutivo', 'value': str(project_health.get('summary') or 'sin resumen evolutivo confirmado')},
            {'label': 'World model', 'value': str(dict(world.inferred_state or {}).get('summary') or 'sin resumen world model')},
            {'label': 'Validacion autonoma', 'value': str(validation.get('summary') or 'sin validacion autonoma fuerte')},
        ]
        summary = str(objective.get('title') or goal_context.get('active_title') or 'Sin objetivo activo confirmado')
        summary += f" | World model: {str(world.network_status.status or 'n/d')}"
        if str(validation.get('status') or '').strip():
            summary += f" | Validacion: {str(validation.get('status') or '').strip()}"
        return self._section(
            section_id='project_state',
            title='Estado actual del proyecto',
            summary=summary,
            items=items,
            source_kind='aggregated_live_state',
            source_refs=['objective_repository', 'evolution_review_service', 'world_model_service', 'autonomous_validation_cycle'],
            confidence=max(float(world.confidence or 0.0), 0.62),
            last_updated=world.last_updated or now,
        )

    def _architecture_section(self, *, now) -> PortableContextSection:
        components = [
            ('PerceptionSnapshot', 'wired', 'Entrada unificada antes de decidir.'),
            ('TaskContextAssembler', 'wired' if self.task_context_assembler is not None else 'unresolved', 'Arma contexto, memoria, aprendizaje y world model.'),
            ('AdaptiveTaskOrchestrator', 'wired' if self.adaptive_task_orchestrator is not None else 'unresolved', 'Decide ruta, governance y resultado final.'),
            ('EnvironmentSelfModel', 'wired' if self.environment_self_awareness_service is not None else 'unresolved', 'Describe hardware, runtime y riesgo operativo.'),
            ('WorldModelSnapshot', 'wired' if self.world_model_service is not None else 'unresolved', 'Panorama operativo vivo de herramientas, red y ventanas.'),
            ('ExperimentLab', 'wired' if self.experiment_lab_repository is not None else 'unresolved', 'Memoria persistida de resultados y recomendaciones.'),
            ('AdaptiveWeightLayer', 'wired', 'Ajusta preferencia futura segun evidencia real.'),
            ('ToolEvolutionMonitor', 'wired' if self.tool_evolution_monitor is not None else 'unresolved', 'Monitorea desempeno por herramienta y problema, y propone cambios con evidencia.'),
            ('AutonomousValidationCycle', 'wired' if self.autonomous_validation_cycle is not None else 'unresolved', 'Valida candidatos en sandbox antes de promoverlos.'),
            ('PortableContextPackage', 'wired', 'Exporta contexto comprimido reusable para nuevas sesiones.'),
        ]
        items = [{'component': component, 'status': status, 'detail': detail} for component, status, detail in components]
        unresolved = [f'UNRESOLVED:{item["component"]}' for item in items if item['status'] != 'wired']
        return self._section(
            section_id='architecture',
            title='Arquitectura central vigente',
            summary='La arquitectura sigue siendo una sola: perception -> orchestrator -> governance -> ejecucion -> aprendizaje.',
            items=items,
            source_kind='project_contract',
            source_refs=['AGENTS.md', 'bootstrap wiring'],
            confidence=1.0,
            last_updated=now,
            unresolved_fields=unresolved,
        )

    def _user_metacognitive_intent_section(self, *, now) -> PortableContextSection:
        items = [
            {
                'label': 'centro_metacognitivo_local',
                'detail': 'IABV debe ser el centro local-first que observa laptop, nube, herramientas, sesiones y resultados sin crear otro cerebro.',
            },
            {
                'label': 'ias_como_organos_externos',
                'detail': 'Devin, Codex, ChatGPT, Claude y otros asistentes deben aportar evidencia, trazas y rendimiento al ExperimentLab.',
            },
            {
                'label': 'no_repetir_intencion',
                'detail': 'Las ideas recurrentes del usuario se condensan en contexto portable para que cada sesion arranque con la misma direccion.',
            },
            {
                'label': 'evolucion_gobernada',
                'detail': 'Toda incubacion cognitiva, algoritmo mutable o ajuste de prompts pasa por sandbox, consenso y validacion antes de promoverse.',
            },
            {
                'label': 'percepcion_segura_de_cuentas',
                'detail': 'El sistema puede detectar presencia/sesion y recomendar rutas, pero no extrae contrasenas, cookies ni tokens; pide permiso cuando corresponda.',
            },
        ]
        return self._section(
            section_id='user_metacognitive_intent',
            title='Intencion persistente del usuario',
            summary='Direccion estable: todas las IAs deben alimentar la metacognicion de IABV para mejorar coherencia, memoria operativa y autonomia gobernada.',
            items=items,
            source_kind='user_intent',
            source_refs=['chat:metacognicion_extendida', 'AGENTS.md', 'portable_context'],
            confidence=0.9,
            last_updated=now,
        )

    def _implemented_capabilities_section(
        self,
        *,
        recommendations: list[dict[str, Any]],
        validation: dict[str, Any],
        world: WorldModelSnapshot,
        now,
    ) -> PortableContextSection:
        items = [
            {'capability': 'P1 World Model operativo', 'status': 'active' if world.tool_live_status or world.detected_blocks or world.active_windows else 'partial', 'detail': 'Observa estado de herramientas, red, foco, procesos y bloqueos antes de actuar.'},
            {'capability': 'P2 Neuroplasticidad operativa', 'status': 'active' if recommendations else 'partial', 'detail': 'Aprende resultados reales y ajusta preferencia futura de rutas e IAs.'},
            {'capability': 'Monitor de evolucion de herramientas', 'status': 'active' if self.tool_evolution_monitor is not None else 'unresolved', 'detail': 'Resume desempeno por problema, detecta degradacion y genera propuestas para sandbox.'},
            {'capability': 'SandboxExperiment', 'status': 'active' if self.autonomous_validation_cycle is not None else 'unresolved', 'detail': 'Valida candidatos antes de promoverlos como decision estable.'},
            {'capability': 'P3 Contexto portable', 'status': 'active', 'detail': 'Condensa arquitectura, aprendizaje, bloqueos y pendientes en JSON + Markdown reutilizable.'},
            {'capability': 'Preguntas humanas de aprendizaje', 'status': 'active', 'detail': 'Responde desde ExperimentLab y validacion sin disparar autonomia operativa.'},
            {'capability': 'Preflight de asistentes externos', 'status': 'active', 'detail': 'Consulta world model y governance antes de abrir o pegar en otra herramienta.'},
        ]
        summary = 'Capas cerradas: P1 y nucleo de P2. P3 ya deja paquete portable util para sesiones nuevas.'
        if str(validation.get('summary') or '').strip():
            summary += f" Validacion actual: {str(validation.get('summary') or '').strip()}"
        return self._section(
            section_id='implemented_capabilities',
            title='Piezas ya implementadas',
            summary=summary,
            items=items,
            source_kind='project_contract',
            source_refs=['bootstrap wiring', 'world_model_service', 'experiment_lab_repository', 'autonomous_validation_cycle'],
            confidence=0.95,
            last_updated=now,
        )

    def _learning_section(
        self,
        *,
        adaptive_learning: dict[str, Any],
        learned_patterns: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
        now,
    ) -> PortableContextSection:
        items: list[dict[str, Any]] = []
        if adaptive_learning:
            items.append(
                {
                    'label': 'Preferencia actual',
                    'assistant_kind': str(adaptive_learning.get('recommended_assistant_kind') or ''),
                    'route': str(adaptive_learning.get('recommended_route') or ''),
                    'reasons': list(adaptive_learning.get('reasons') or []),
                    'confidence': float(adaptive_learning.get('confidence') or 0.0),
                    'score': float(adaptive_learning.get('score') or 0.0),
                }
            )
        for pattern in learned_patterns[:3]:
            items.append(
                {
                    'label': 'Patron aprendido',
                    'subject_key': str(pattern.get('subject_key') or ''),
                    'assistant_kind': str(pattern.get('recommended_assistant_kind') or ''),
                    'route': str(pattern.get('recommended_route') or ''),
                    'reasons': list(pattern.get('reasons') or []),
                }
            )
        summary = 'Aun no hay aprendizaje consolidado.'
        if adaptive_learning:
            preferred = str(adaptive_learning.get('recommended_assistant_kind') or adaptive_learning.get('recommended_route') or 'sin preferencia fuerte')
            summary = f'Aprendizaje acumulado: {preferred} viene saliendo mejor en historial comparable.'
        elif recommendations:
            summary = 'Hay recomendaciones persistidas, pero sin una preferencia fuerte totalmente consolidada.'
        return self._section(
            section_id='learning',
            title='Aprendizaje acumulado util',
            summary=summary,
            items=items,
            source_kind='persistent_learning',
            source_refs=['ExperimentLab', 'AdaptiveWeightLayer', 'TaskOutcomeRecorder'],
            confidence=float(adaptive_learning.get('confidence') or 0.58),
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:learning_summary'],
        )

    def _tool_discovery_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        signals = [dict(item) for item in (status.get('signals') or []) if isinstance(item, dict)]
        summary_payload = dict(status.get('summary_payload') or {})
        items: list[dict[str, Any]] = []
        for item in signals[:4]:
            items.append(
                {
                    'label': str(item.get('tool_title') or item.get('assistant_kind') or item.get('tool_id') or 'candidato'),
                    'assistant_kind': str(item.get('assistant_kind') or ''),
                    'detail': (
                        f"scope={str(item.get('scope') or '')} | estado={str(item.get('status') or '')} | "
                        f"confianza={float(item.get('confidence') or 0.0):.2f} | {str(item.get('summary') or '').strip()}"
                    ),
                }
            )
        summary = str(status.get('summary') or 'Sin descubrimiento de herramientas confirmado.')
        return self._section(
            section_id='tool_discovery',
            title='Descubrimiento de herramientas',
            summary=summary,
            items=items,
            source_kind='tool_discovery',
            source_refs=['ToolRegistry', 'WorldModelSnapshot', 'ExperimentLab', 'AutonomousValidationCycleService'],
            confidence=0.78 if items else 0.35,
            last_updated=now,
            unresolved_fields=list(status.get('unresolved_fields') or []),
            metadata={
                'active_signal_count': len(list(summary_payload.get('active_signals') or [])),
                'in_validation_signal_count': len(list(summary_payload.get('in_validation_signals') or [])),
                'promoted_signal_count': len(list(summary_payload.get('promoted_signals') or [])),
                'discarded_signal_count': len(list(summary_payload.get('discarded_signals') or [])),
            },
        )

    def _tool_evolution_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        performance = [dict(item) for item in (status.get('performance') or []) if isinstance(item, dict)]
        proposals = [dict(item) for item in (status.get('proposals') or []) if isinstance(item, dict)]
        summary_payload = dict(status.get('summary_payload') or {})
        items: list[dict[str, Any]] = []
        for item in performance[:3]:
            items.append(
                {
                    'label': str(item.get('subject_key') or 'general'),
                    'assistant_kind': str(item.get('assistant_kind') or ''),
                    'detail': (
                        f"route={str(item.get('route') or '')} | score={float(item.get('weighted_score') or 0.0):.2f} | "
                        f"exito={float(item.get('success_rate') or 0.0):.0%} | bloqueos={float(item.get('blocked_rate') or 0.0):.0%}"
                    ),
                }
            )
        for item in proposals[:3]:
            items.append(
                {
                    'label': str(item.get('title') or item.get('subject_key') or 'propuesta'),
                    'assistant_kind': str(item.get('candidate_assistant_kind') or ''),
                    'detail': str(item.get('summary') or ''),
                }
            )
        summary = str(status.get('summary') or 'Sin monitor de evolucion confirmado.')
        return self._section(
            section_id='tool_evolution',
            title='Evolucion de herramientas',
            summary=summary,
            items=items,
            source_kind='experiment_lab_monitor',
            source_refs=['ExperimentLab', 'AdaptiveWeightLayer', 'AutonomousValidationCycle'],
            confidence=0.83 if items else 0.35,
            last_updated=now,
            unresolved_fields=list(status.get('unresolved_fields') or []),
            metadata={
                'degraded_subjects': list(status.get('degraded_subjects') or []),
                'proposal_count': len(proposals),
                'active_proposal_count': int(summary_payload.get('active_proposal_count') or len(proposals)),
                'decided_proposal_count': int(summary_payload.get('decided_proposal_count') or 0),
                'winning_by_problem': dict(summary_payload.get('winning_by_problem') or {}),
                'in_validation': list(summary_payload.get('in_validation') or []),
                'discarded_proposals': list(summary_payload.get('discarded_proposals') or [])[:4],
                'recent_decisions': list(summary_payload.get('recent_decisions') or [])[:4],
            },
        )

    def _tool_evolution_decisions_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        entries = [dict(item) for item in (snapshot.get('entries') or []) if isinstance(item, dict)]
        items: list[dict[str, Any]] = []
        for item in entries[-4:]:
            items.append(
                {
                    'label': str(item.get('subject_key') or item.get('proposal_key') or 'decision'),
                    'assistant_kind': str(item.get('candidate_assistant_kind') or ''),
                    'detail': (
                        f"decision={str(item.get('decision') or '')} | ganador={str(item.get('winner') or '')} | "
                        f"{str(item.get('reason') or '').strip()}"
                    ),
                }
            )
        summary_payload = dict(snapshot.get('summary_payload') or {})
        last_decision = dict(summary_payload.get('last_decision') or {})
        summary = str(last_decision.get('reason') or 'Sin decisiones evolutivas registradas todavia.')
        return self._section(
            section_id='tool_evolution_decisions',
            title='Decisiones evolutivas',
            summary=summary,
            items=items,
            source_kind='autonomous_validation_cycle',
            source_refs=['AutonomousValidationCycleService', 'SandboxExperimentService', 'ExperimentLab'],
            confidence=0.84 if items else 0.35,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata={
                'winning_by_problem': dict(summary_payload.get('winning_by_problem') or {}),
                'degraded_tools': list(summary_payload.get('degraded_tools') or []),
                'in_validation': list(summary_payload.get('in_validation') or []),
            },
        )

    def _self_examination_section(self, *, review: dict[str, Any], now) -> PortableContextSection:
        items: list[dict[str, Any]] = []
        for finding in list(review.get('findings') or [])[:4]:
            items.append(
                {
                    'label': str(finding.get('title') or finding.get('category') or 'Hallazgo'),
                    'summary': str(finding.get('summary') or '').strip(),
                    'recommendation': str(finding.get('recommendation') or '').strip(),
                    'severity': str(finding.get('severity') or ''),
                    'confidence': float(finding.get('confidence') or 0.0),
                    'source_refs': list(finding.get('source_refs') or []),
                }
            )
        for adjustment in list(review.get('recommended_adjustments') or [])[:2]:
            items.append(
                {
                    'label': str(adjustment.get('title') or 'Ajuste recomendado'),
                    'summary': str(adjustment.get('recommended_change') or '').strip(),
                    'severity': str(adjustment.get('severity') or ''),
                    'confidence': float(adjustment.get('confidence') or 0.0),
                    'source_refs': list(adjustment.get('source_refs') or []),
                }
            )
        for feedback in list(review.get('recommendation_feedback') or [])[:2]:
            items.append(
                {
                    'label': f"{str(feedback.get('title') or 'Ajuste previo')} [{str(feedback.get('status') or 'sin estado')}]",
                    'summary': str(feedback.get('summary') or '').strip(),
                    'recommendation': str(feedback.get('next_step') or '').strip(),
                    'confidence': float(feedback.get('confidence') or 0.0),
                    'source_refs': list(feedback.get('source_refs') or []),
                }
            )
        summary = str(review.get('summary') or '').strip() or 'Todavia no hay una autoexaminacion fuerte exportada.'
        return self._section(
            section_id='self_examination',
            title='Autoexaminacion operativa',
            summary=summary,
            items=items,
            source_kind='derived_review',
            source_refs=['OperationalSelfExaminationService', 'ExperimentLab', 'WorldModelSnapshot'],
            confidence=max((float(item.get('confidence') or 0.0) for item in items), default=0.0),
            last_updated=now,
            unresolved_fields=list(review.get('unresolved_risks') or []),
            metadata={
                'recurring_issues': list(review.get('recurring_issues') or []),
                'validated_improvements': list(review.get('validated_improvements') or []),
                'recommendation_feedback': list(review.get('recommendation_feedback') or []),
                'feedback_summary': dict(review.get('feedback_summary') or {}),
            },
        )

    def _code_audit_snapshot(self) -> dict[str, Any]:
        """Build code audit summary from CodeAuditTrail."""
        trail = getattr(self, 'code_audit_trail', None)
        if trail is None:
            return {'status': 'not_configured'}
        try:
            return trail.summary_for_portable_context()
        except Exception:
            return {'status': 'error'}

    def _code_audit_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        """Export code audit trail to portable context.

        Ensures new sessions know what was audited, by whom, what bugs
        were found, what patterns recur, and what needs cross-verification
        on a different environment (Linux vs Windows).
        """
        items: list[dict[str, Any]] = []
        coverage = status.get('coverage') or {}
        for r in list(status.get('recent_rounds') or [])[:5]:
            items.append({
                'label': f"Ronda {r.get('round_number', '?')} ({r.get('auditor', '?')})",
                'environment': r.get('environment', ''),
                'modules': r.get('modules', [])[:4],
                'bugs_found': r.get('bugs_found', 0),
                'loc_audited': r.get('loc_audited', 0),
                'pr_url': r.get('pr_url', ''),
            })
        for pattern in list(status.get('recurring_patterns') or [])[:3]:
            items.append({
                'label': f"Patron: {pattern.get('pattern_tag', '')}",
                'occurrences': pattern.get('occurrences', 0),
                'affected_modules': pattern.get('affected_modules', []),
                'all_fixed': pattern.get('all_fixed', True),
            })
        for cv in list(status.get('pending_cross_verifications') or [])[:3]:
            items.append({
                'label': f"Cross-verificacion pendiente: {cv.get('title', '')}",
                'module_path': cv.get('module_path', ''),
                'needs_windows': cv.get('needs_windows', False),
                'needs_linux': cv.get('needs_linux', False),
            })
        total_rounds = coverage.get('total_rounds', 0)
        total_bugs = coverage.get('total_bugs_fixed', 0)
        total_loc = coverage.get('total_loc_audited', 0)
        pending_cv = coverage.get('pending_cross_verifications', 0)
        if total_rounds == 0:
            summary = 'Sin auditorias registradas. Usar register_audit_finding via MCP para registrar hallazgos.'
        else:
            summary = (
                f'{total_rounds} rondas, {total_loc} LOC auditadas, '
                f'{total_bugs} bugs fixeados, {pending_cv} verificaciones cruzadas pendientes.'
            )
        return self._section(
            section_id='code_audit_trail',
            title='Historial de auditorias de codigo',
            summary=summary,
            items=items,
            source_kind='code_audit',
            source_refs=['CodeAuditTrail'],
            confidence=0.90 if total_rounds > 0 else 0.0,
            last_updated=now,
            metadata={
                'total_rounds': total_rounds,
                'total_bugs_fixed': total_bugs,
                'total_loc_audited': total_loc,
                'auditors': coverage.get('auditors', []),
                'environments_used': coverage.get('environments_used', []),
                'pending_cross_verifications': pending_cv,
            },
        )

    def _cloud_reasoning_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        """Export cloud reasoning decision audit to portable context.

        This ensures the next session (of any AI agent) has the full picture
        of which cloud providers are working, which are degrading, and what
        the system recommends — BEFORE it starts planning or modifying code.
        """
        items: list[dict[str, Any]] = []
        for trend in list(status.get('trends') or [])[:5]:
            if not isinstance(trend, dict):
                continue
            items.append({
                'provider_id': trend.get('provider_id', ''),
                'success_rate': trend.get('success_rate', 0.0),
                'total_decisions': trend.get('total_decisions', 0),
                'avg_latency_ms': trend.get('avg_latency_ms', 0.0),
                'trend_direction': trend.get('trend_direction', 'unknown'),
                'rate_limited_count': trend.get('rate_limited_count', 0),
            })
        for rec in list(status.get('recommendations') or [])[:3]:
            items.append({
                'label': 'Recomendacion',
                'summary': str(rec),
            })
        health = status.get('health_score', 0.0)
        total = status.get('total_decisions', 0)
        overall = status.get('overall_trend', 'unknown')
        st = status.get('status', 'not_configured')
        if st == 'no_data':
            summary = 'Sin decisiones registradas. Ejecutar "soluciona X" para iniciar el trail de auditoria.'
        elif st == 'analyzed':
            summary = (
                f'Cloud reasoning: {total} decisiones, exito {health:.0%}, '
                f'tendencia: {overall}.'
            )
        else:
            summary = f'Cloud reasoning status: {st}'
        best = status.get('best_provider') or {}
        return self._section(
            section_id='cloud_reasoning',
            title='Estado de Cloud Reasoning',
            summary=summary,
            items=items,
            source_kind='decision_audit',
            source_refs=['DecisionAuditTrail', 'ApiKeyDiscoveryService'],
            confidence=0.85 if st == 'analyzed' else 0.0,
            last_updated=now,
            metadata={
                'health_score': health,
                'overall_trend': overall,
                'total_decisions': total,
                'best_provider': best.get('provider_id', ''),
            },
        )

    def _recent_freeze_incidents(self) -> list[dict[str, Any]]:
        """Return recent freeze incidents for inclusion in startup_health."""
        reporter = self.freeze_incident_reporter
        if reporter is None or not hasattr(reporter, 'recent_incidents'):
            return []
        try:
            return reporter.recent_incidents(limit=3)
        except Exception:
            return []

    def _ui_heartbeat_summary(self) -> dict[str, Any]:
        """Return UI heartbeat watchdog summary for PortableContext."""
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        if watchdog is None or not hasattr(watchdog, 'summary'):
            return {}
        try:
            return watchdog.summary()
        except Exception:
            return {}

    def _interaction_lifecycle_summary(self) -> dict[str, Any]:
        """Return chat interaction lifecycle summary for PortableContext.

        Merges in-memory lifecycle data with durable records from
        ``runtime_audit.jsonl`` so that episodes survive process death.
        """
        lifecycle = getattr(self, 'chat_interaction_lifecycle', None)
        in_memory_recent: list[dict[str, Any]] = []
        summary: dict[str, Any] = {}
        if lifecycle is not None and hasattr(lifecycle, 'summary'):
            try:
                summary = lifecycle.summary()
                in_memory_recent = lifecycle.recent_completed(limit=3)
            except Exception:
                pass

        # Reconstruct from runtime_audit.jsonl if in-memory is empty/missing
        audit_recent = self._interaction_episodes_from_audit(limit=3)
        # Merge: prefer in-memory for IDs we already have, append audit-only
        seen_ids = {r.get('interaction_id') for r in in_memory_recent}
        for ar in audit_recent:
            if ar.get('interaction_id') not in seen_ids:
                in_memory_recent.append(ar)
                seen_ids.add(ar.get('interaction_id'))
        # Keep only most recent 3
        in_memory_recent = in_memory_recent[-3:]
        summary['recent_completed'] = in_memory_recent
        # reconstructed_from_audit = true if ANY episode came from audit
        summary['reconstructed_from_audit'] = any(
            ep.get('_source') == 'runtime_audit' for ep in in_memory_recent
        )
        return summary

    def _interaction_lifecycle_section(self, *, now) -> PortableContextSection:
        """Build a renderable section for recent interaction episodes.

        Merges in-memory lifecycle with durable ``runtime_audit.jsonl``
        records so that episodes survive process death and appear in
        ``latest.md`` (not only in ``latest.json`` metadata).
        """
        lifecycle_data = self._interaction_lifecycle_summary()
        recent = list(lifecycle_data.get('recent_completed') or [])
        reconstructed = bool(lifecycle_data.get('reconstructed_from_audit'))
        items: list[dict[str, Any]] = []
        for ep in recent:
            stall_count = len(ep.get('stalls_during') or [])
            outcome = ep.get('outcome', '')
            is_resolved = ep.get('resolved', outcome == 'resolved')
            is_final = ep.get('is_final', outcome not in ('prepared', 'awaiting_external_response', 'reused_context'))
            items.append({
                'interaction_id': ep.get('interaction_id', ''),
                'message_preview': ep.get('message_preview', ''),
                'outcome': outcome,
                'resolved': is_resolved,
                'is_final': is_final,
                'provider': ep.get('provider', ''),
                'total_duration_ms': ep.get('total_duration_ms', 0),
                'stall_count': stall_count,
                'had_early_technical_response': ep.get('had_early_technical_response', False),
                'window_went_inactive': ep.get('window_went_inactive', False),
                'source': ep.get('_source', 'in_memory'),
            })
        if not items:
            summary_text = 'Sin episodios de interaccion recientes.'
        else:
            sources = set(i.get('source', '') for i in items)
            source_note = ' (reconstruido desde runtime_audit)' if 'runtime_audit' in sources else ''
            summary_text = (
                f'{len(items)} episodio(s) reciente(s){source_note}.'
            )
        return self._section(
            section_id='interaction_lifecycle',
            title='Ciclo de vida de interacciones recientes',
            summary=summary_text,
            items=items,
            source_kind='runtime_audit_jsonl+in_memory',
            source_refs=['data/logs/runtime_audit.jsonl', 'ChatInteractionLifecycle'],
            confidence=0.9 if items else 0.0,
            last_updated=now,
            unresolved_fields=[],
            metadata=lifecycle_data,
        )

    def _interaction_episodes_from_audit(
        self, *, limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Read recent ``interaction_resolved`` events from runtime_audit.jsonl.

        Deduplicates by ``interaction_id``: if both ``interaction_outcome``
        (prepared/reused) and ``interaction_resolved`` (final) exist for the
        same id, only the most recent event is kept.  Since the file is read
        in reverse chronological order, the first occurrence per id wins.
        """
        import json as _json
        audit_path = Path(self.workspace_root) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        seen_ids: set[str] = set()
        episodes: list[dict[str, Any]] = []
        try:
            lines = audit_path.read_text(encoding='utf-8', errors='replace').splitlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    event = _json.loads(line)
                except Exception:
                    continue
                if event.get('kind') not in ('interaction_resolved', 'interaction_outcome'):
                    continue
                data = dict(event.get('data') or {})
                iid = data.get('interaction_id', '')
                if iid and iid in seen_ids:
                    continue  # already have a more recent event for this id
                if iid:
                    seen_ids.add(iid)
                is_final = data.get('is_final', event.get('kind') == 'interaction_resolved')
                ep_outcome = data.get('outcome', '')
                episodes.append({
                    'interaction_id': iid,
                    'message_preview': data.get('message_preview', ''),
                    'outcome': ep_outcome,
                    'provider': data.get('provider', ''),
                    'total_duration_ms': data.get('total_duration_ms', 0),
                    'phases': dict(data.get('phases') or {}),
                    'stalls_during': list(data.get('stalls_during') or []),
                    'window_inactive_intervals': list(
                        data.get('window_inactive_intervals') or [],
                    ),
                    'initial_window_active': data.get('initial_window_active', True),
                    'initial_window_visible': data.get('initial_window_visible', True),
                    'had_early_technical_response': data.get(
                        'had_early_technical_response', False,
                    ),
                    'window_went_inactive': data.get('window_went_inactive', False),
                    'resolved': ep_outcome == 'resolved',
                    'is_final': is_final,
                    '_source': 'runtime_audit',
                })
                if len(episodes) >= limit:
                    break
        except Exception:
            pass
        episodes.reverse()
        return episodes

    def _startup_health_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        """Export the latest startup timeline summary as a portable section.

        Reads the snapshot built by :meth:`_startup_health_snapshot` and emits
        a single section with the three core intervals (init / run-to-window /
        deferred) plus any phase that crossed a degradation threshold.  This is
        the cable that ensures ``data/logs/startup_timeline.jsonl`` stops being
        a loose log: any new session opening the package sees the boot health
        without re-parsing the JSONL.
        """
        st = str(status.get('status') or 'no_log')
        unresolved = list(status.get('unresolved_fields') or [])
        items: list[dict[str, Any]] = []
        if st == 'analyzed':
            items.append({
                'phase': 'bootstrap_init',
                'ms': status.get('init_ms'),
                'note': 'bootstrap_init_done - bootstrap_init_start',
            })
            items.append({
                'phase': 'run_to_main_window',
                'ms': status.get('run_to_window_ms'),
                'note': 'run_start (or bootstrap_init_done) - main_window_shown',
            })
            items.append({
                'phase': 'deferred_post_window',
                'ms': status.get('deferred_ms'),
                'note': 'deferred_post_window_setup_done - start',
            })
            for blk in list(status.get('recent_blockers') or [])[:4]:
                items.append({
                    'label': 'startup_blocker',
                    'phase': blk.get('phase'),
                    'ms': blk.get('ms'),
                })
        freeze_incidents = self._recent_freeze_incidents()
        for fi in freeze_incidents:
            items.append({
                'label': 'freeze_incident',
                'incident_type': fi.get('incident_type', ''),
                'trigger': fi.get('trigger', ''),
                'severity': fi.get('severity', ''),
                'dominant_phase': fi.get('dominant_phase', ''),
                'duration_ms': fi.get('duration_ms', 0),
                'timestamp': fi.get('timestamp', ''),
                'file': fi.get('file', ''),
            })
        if st == 'analyzed':
            init = status.get('init_ms')
            window = status.get('run_to_window_ms')
            rss = status.get('rss_mb_max')
            init_str = f'{init:.0f}ms' if isinstance(init, (int, float)) else 'n/d'
            window_str = f'{window:.0f}ms' if isinstance(window, (int, float)) else 'n/d'
            rss_str = f', RSS pico {rss:.0f}MB' if isinstance(rss, (int, float)) and rss > 0 else ''
            incidents_str = f' Freeze incidents recientes: {len(freeze_incidents)}.' if freeze_incidents else ''
            summary = (
                f'Startup ultimo: init {init_str}, run->window {window_str}{rss_str}. '
                f'Eventos {status.get("event_count", 0)}.{incidents_str}'
            )
        elif st == 'no_log':
            summary = 'Sin data/logs/startup_timeline.jsonl. Lanzar la UI con IABV_STARTUP_TIMELINE=1 para registrar arranque.'
        elif st == 'no_data':
            summary = 'Archivo startup_timeline.jsonl vacio: no hay arranques registrados todavia.'
        elif st == 'error':
            summary = 'startup_timeline.jsonl ilegible. Revisar permisos del workspace.'
        else:
            summary = f'Startup status: {st}'
        confidence = 0.85 if st == 'analyzed' and not unresolved else 0.0
        return self._section(
            section_id='startup_health',
            title='Salud del arranque (startup_timeline)',
            summary=summary,
            items=items,
            source_kind='startup_timeline_jsonl',
            source_refs=['data/logs/startup_timeline.jsonl', 'iabv_v15.infra.startup_timeline'],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=unresolved,
            metadata={
                'status': st,
                'init_ms': status.get('init_ms'),
                'run_to_window_ms': status.get('run_to_window_ms'),
                'deferred_ms': status.get('deferred_ms'),
                'rss_mb_max': status.get('rss_mb_max'),
                'last_started_at_utc': status.get('last_started_at_utc', ''),
                'phases_seen': list(status.get('phases_seen') or []),
                'recent_blockers': list(status.get('recent_blockers') or []),
                'freeze_incidents': freeze_incidents,
                'ui_heartbeat': self._ui_heartbeat_summary(),
                'interaction_lifecycle': self._interaction_lifecycle_summary(),
            },
        )

    def _recommended_routes_section(self, *, recommendations: list[dict[str, Any]], now) -> PortableContextSection:
        items = [
            {
                'subject_key': str(item.get('subject_key') or ''),
                'assistant_kind': str(item.get('recommended_assistant_kind') or ''),
                'route': str(item.get('recommended_route') or ''),
                'confidence': float(item.get('confidence') or 0.0),
                'score': float(item.get('score') or 0.0),
                'reasons': list(dict(item.get('metadata') or {}).get('adaptive_learning_summary', {}).get('reasons') or []),
                'comparison_scope_keys': list(item.get('comparison_scope_keys') or []),
            }
            for item in recommendations[:4]
        ]
        summary = 'No hay rutas recomendadas con evidencia suficiente.'
        if items:
            top = items[0]
            summary = f"Ruta lider actual: {top.get('assistant_kind') or 'n/d'} por {top.get('route') or 'n/d'} para {top.get('subject_key') or 'general'}."
        return self._section(
            section_id='recommended_routes',
            title='Herramientas y rutas recomendadas',
            summary=summary,
            items=items,
            source_kind='persistent_learning',
            source_refs=['ExperimentLab', 'StrategySelector', 'comparison_scope_key'],
            confidence=float(items[0].get('confidence') or 0.0) if items else 0.0,
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:recommended_routes'],
        )

    def _operational_blocks_section(self, *, world: WorldModelSnapshot, recommendations: list[dict[str, Any]], now) -> PortableContextSection:
        items: list[dict[str, Any]] = []
        for block in (world.block_records or [])[:8]:
            items.append({'kind': str(block.block_type or ''), 'target_scope': str(block.target_scope or ''), 'assistant_kind': str(block.assistant_kind or ''), 'detail': str(block.detail or '')})
        for gate in (world.permission_gates or [])[:6]:
            items.append(
                {
                    'kind': 'permission_gate',
                    'target_scope': str(gate.scope or ''),
                    'assistant_kind': str(gate.assistant_kind or ''),
                    'detail': str(gate.detail or ''),
                }
            )
        for tool in (world.tool_live_status or [])[:8]:
            if str(tool.status or '').strip() in {'bloqueado', 'limitado', 'no_disponible', 'sesion_expirada'} or str(tool.messages_status or '').strip() == 'agotados_o_limitados' or str(tool.permission_state or '').strip() == 'requerido':
                items.append({'kind': 'tool_status', 'target_scope': str(tool.tool_id or ''), 'assistant_kind': str(tool.assistant_kind or ''), 'detail': str(tool.detail or tool.status or '')})
        blocked_assistants = list(dict((recommendations[0].get('metadata') or {}).get('ia_trace_summary') or {}).get('blocked_assistants') or []) if recommendations else []
        for assistant in blocked_assistants[:3]:
            items.append({'kind': 'blocked_assistant_history', 'target_scope': 'historical_trace', 'assistant_kind': str(assistant), 'detail': 'Asistente con bloqueos recientes en trazas reutilizadas.'})
        summary = f'{len(items)} bloqueos o limitaciones activas.'
        if not items:
            summary = 'No veo bloqueos operativos fuertes persistidos en este momento.'
        return self._section(
            section_id='operational_blocks',
            title='Bloqueos, limites y rutas inviables',
            summary=summary,
            items=items,
            source_kind='live_operational_state',
            source_refs=['WorldModelSnapshot'],
            confidence=max(float(world.confidence or 0.0), 0.55),
            last_updated=world.last_updated or now,
        )

    def _validated_decisions_section(self, *, recommendations: list[dict[str, Any]], validation: dict[str, Any], now) -> PortableContextSection:
        items: list[dict[str, Any]] = []
        if str(validation.get('summary') or '').strip():
            items.append(
                {
                    'decision': 'validation_cycle',
                    'summary': str(validation.get('summary') or ''),
                    'status': str(validation.get('status') or ''),
                    'promoted_count': int(validation.get('promoted_count') or 0),
                    'candidate_assistant_kind': str(validation.get('candidate_assistant_kind') or ''),
                    'candidate_route': str(validation.get('candidate_route') or ''),
                    'verdict': str(validation.get('verdict') or ''),
                }
            )
        for recommendation in recommendations[:3]:
            confidence = float(recommendation.get('confidence') or 0.0)
            score = float(recommendation.get('score') or 0.0)
            if confidence < 0.7 and score < 0.7:
                continue
            items.append(
                {
                    'decision': 'recommended_route',
                    'subject_key': str(recommendation.get('subject_key') or ''),
                    'assistant_kind': str(recommendation.get('recommended_assistant_kind') or ''),
                    'route': str(recommendation.get('recommended_route') or ''),
                    'confidence': confidence,
                    'score': score,
                    'supporting_run_ids': list(recommendation.get('supporting_run_ids') or []),
                }
            )
        summary = 'No hay decisiones validadas con suficiente evidencia.'
        if items:
            summary = f'{len(items)} decisiones ya tienen validacion o confianza suficiente para reutilizarse.'
        return self._section(
            section_id='validated_decisions',
            title='Decisiones ya validadas',
            summary=summary,
            items=items,
            source_kind='persistent_learning',
            source_refs=['ExperimentLab', 'AutonomousValidationCycle'],
            confidence=0.82 if items else 0.0,
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:validated_decisions'],
        )

    def _decision_history_section(self, *, decision_history: list[dict[str, Any]], now) -> PortableContextSection:
        summary = 'No hay historial condensado de decisiones relevantes.'
        if decision_history:
            summary = f'{len(decision_history)} decisiones recientes quedaron condensadas para retomar el hilo rapido.'
        return self._section(
            section_id='decision_history',
            title='Historial condensado de decisiones',
            summary=summary,
            items=decision_history,
            source_kind='persistent_learning',
            source_refs=['ExperimentLab', 'ia_trace_summary'],
            confidence=0.74 if decision_history else 0.0,
            last_updated=now,
            unresolved_fields=[] if decision_history else ['UNRESOLVED:decision_history'],
        )

    def _pending_section(self, *, pending_items: list[dict[str, Any]], backlog_items: list[dict[str, Any]], now) -> PortableContextSection:
        platform_items = self._platform_pending_items()
        items = pending_items[:4] + backlog_items[:4] + platform_items[:4]
        platform_summary = ''
        if platform_items:
            platform_summary = f' {len(platform_items)} tareas de plataforma pendientes.'
        summary = f'{len(pending_items)} pending issues y {len(backlog_items)} mejoras priorizadas.{platform_summary}'
        if not items:
            summary = 'No tengo pendientes priorizados confirmados por evidencia persistida.'
        return self._section(
            section_id='pending',
            title='Pendientes priorizados',
            summary=summary,
            items=items,
            source_kind='persistent_backlog',
            source_refs=['pending_issue_repository', 'evolution_review_service', 'platform_pending_queue'],
            confidence=0.8 if items else 0.0,
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:pending_backlog'],
        )

    def _platform_pending_items(self) -> list[dict[str, Any]]:
        """Read structured pending items from PlatformPendingQueue."""
        queue = self.platform_pending_queue
        if queue is None or not hasattr(queue, 'to_portable_items'):
            return []
        try:
            return queue.to_portable_items(limit=6)
        except Exception:
            return []

    def _canonical_work_queue_section(self, *, now) -> PortableContextSection:
        """Project top-5 canonical work queue items from ControlMasterService."""
        cms = self.control_master_service
        if cms is None or not hasattr(cms, 'current_work_queue'):
            return self._section(
                section_id='canonical_work_queue',
                title='Cola canónica de trabajo',
                summary='ControlMasterService no conectado.',
                items=[],
                source_kind='control_master',
                source_refs=['ControlMasterService'],
                confidence=0.0,
                last_updated=now,
                unresolved_fields=['UNRESOLVED:canonical_work_queue_not_connected'],
            )
        try:
            queue = cms.current_work_queue(limit=5)
        except Exception:
            queue = []
        items: list[dict[str, Any]] = []
        for wq_item in queue:
            items.append({
                'id': wq_item.get('id', ''),
                'title': wq_item.get('title', ''),
                'status': wq_item.get('status', ''),
                'priority_score': wq_item.get('priority_score', 0),
                'priority_label': wq_item.get('priority_label', ''),
                'source': wq_item.get('source', ''),
                'next_action': wq_item.get('next_action', ''),
                'evidence_refs': wq_item.get('evidence_refs', []),
            })
        summary = f'{len(queue)} items prioritarios en cola canónica de trabajo.'
        if not items:
            summary = 'Cola canónica vacía o sin fuentes conectadas.'
        return self._section(
            section_id='canonical_work_queue',
            title='Cola canónica de trabajo',
            summary=summary,
            items=items,
            source_kind='control_master',
            source_refs=['ControlMasterService', 'ObjectiveRepository', 'PlatformPendingQueue', 'PendingIssueRepository', 'OSES', 'runtime_audit'],
            confidence=0.9 if items else 0.0,
            last_updated=now,
        )

    def _unresolved_section(self, *, unresolved: list[str], now) -> PortableContextSection:
        items = [{'field': item} for item in unresolved]
        summary = 'Todo lo no confirmado queda marcado como UNRESOLVED.'
        if unresolved:
            summary = f'{len(unresolved)} campos siguen sin evidencia suficiente y no deben asumirse.'
        return self._section(
            section_id='unresolved',
            title='UNRESOLVED',
            summary=summary,
            items=items,
            source_kind='honest_runtime_limits',
            source_refs=['WorldModelSnapshot', 'EnvironmentSelfModel', 'AutonomousValidationCycle'],
            confidence=1.0,
            last_updated=now,
            unresolved_fields=unresolved,
        )

    def _hard_rules_section(self, *, now) -> PortableContextSection:
        rules = [
            'No crear otro cerebro ni otro orquestador.',
            'No duplicar PerceptionSnapshot ni crear una memoria paralela.',
            'No romper governance ni saltarse bloqueos del world model.',
            'Cambios minimos, reversibles y verificables.',
            'Si algo no puede confirmarse con evidencia, marcar UNRESOLVED.',
            'Los ViewModels observan y explican; no inventan decisiones de ruta.',
            'Antes de usar una herramienta externa, consultar estado y bloqueos reales.',
            'El aprendizaje acumulado debe respetarse, pero sin dogma: cambiar de ruta solo con evidencia.',
        ]
        return self._section(
            section_id='hard_rules',
            title='Reglas duras que no deben romperse',
            summary='Este paquete portable no reemplaza la arquitectura: solo la condensa y la hace reutilizable.',
            items=[{'rule': item} for item in rules],
            source_kind='project_contract',
            source_refs=['AGENTS.md'],
            confidence=1.0,
            last_updated=now,
        )

    # ------------------------------------------------------------------
    # User Identity & Long-term Goals
    # ------------------------------------------------------------------

    _IDENTITY_FILE = 'portable_context/user_identity.json'
    _GOALS_FILE = 'portable_context/long_term_goals.json'

    def _user_identity_section(self, *, now) -> PortableContextSection:
        """Persistent user identity: preferences, habits, and environment profile."""
        identity = self._load_identity()
        items: list[dict[str, Any]] = []
        if identity.get('preferred_language'):
            items.append({'label': 'preferred_language', 'value': identity['preferred_language']})
        if identity.get('preferred_ia'):
            items.append({'label': 'preferred_ia', 'value': identity['preferred_ia']})
        if identity.get('environment_os'):
            items.append({'label': 'environment_os', 'value': identity['environment_os']})
        for pref_key, pref_val in (identity.get('custom_preferences') or {}).items():
            items.append({'label': pref_key, 'value': str(pref_val)})
        if not items:
            items.append({'label': 'status', 'value': 'No identity profile persisted yet'})
        return self._section(
            section_id='user_identity',
            title='Identidad persistente del usuario',
            summary='Preferencias, hábitos y perfil del entorno que persisten entre sesiones.',
            items=items,
            source_kind='user_identity',
            source_refs=[self._IDENTITY_FILE],
            confidence=0.9 if len(items) > 1 else 0.3,
            last_updated=now,
        )

    def _long_term_goals_section(self, *, now) -> PortableContextSection:
        """Long-term objectives that persist across sessions."""
        goals = self._load_goals()
        items: list[dict[str, Any]] = []
        for goal in goals:
            items.append({
                'title': str(goal.get('title') or ''),
                'status': str(goal.get('status') or 'active'),
                'priority': str(goal.get('priority') or 'medium'),
                'created_at': str(goal.get('created_at') or ''),
            })
        if not items:
            items.append({'title': 'No long-term goals defined', 'status': 'empty', 'priority': '', 'created_at': ''})
        return self._section(
            section_id='long_term_goals',
            title='Objetivos a largo plazo',
            summary='Metas persistentes del usuario que sobreviven entre sesiones.',
            items=items,
            source_kind='user_goals',
            source_refs=[self._GOALS_FILE],
            confidence=0.9 if len(items) > 1 else 0.3,
            last_updated=now,
        )

    def _load_identity(self) -> dict[str, Any]:
        """Load user identity from persisted JSON."""
        try:
            import json
            path = self.storage.resolve(self._IDENTITY_FILE)
            if path.is_file():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {}

    def _load_goals(self) -> list[dict[str, Any]]:
        """Load long-term goals from persisted JSON."""
        try:
            import json
            path = self.storage.resolve(self._GOALS_FILE)
            if path.is_file():
                data = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def save_identity(self, identity: dict[str, Any]) -> None:
        """Persist user identity profile."""
        import json
        path = self.storage.resolve(self._IDENTITY_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(identity, indent=2, ensure_ascii=False), encoding='utf-8')

    def save_goals(self, goals: list[dict[str, Any]]) -> None:
        """Persist long-term goals."""
        import json
        path = self.storage.resolve(self._GOALS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding='utf-8')

    def add_goal(self, title: str, *, priority: str = 'medium') -> dict[str, Any]:
        """Add a new long-term goal and persist."""
        from datetime import datetime, timezone
        goals = self._load_goals()
        goal = {
            'title': title,
            'status': 'active',
            'priority': priority,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        goals.append(goal)
        self.save_goals(goals)
        return goal

    def _package_summary(
        self,
        *,
        goal_context: dict[str, Any],
        recommendations: list[dict[str, Any]],
        world: WorldModelSnapshot,
        pending_items: list[dict[str, Any]],
        unresolved: list[str],
        self_examination: dict[str, Any] | None = None,
    ) -> str:
        objective = str(dict(goal_context.get('objective') or {}).get('title') or goal_context.get('active_title') or 'sin objetivo activo confirmado')
        route_summary = 'sin preferencia de ruta consolidada'
        if recommendations:
            best = recommendations[0]
            route_summary = f"{str(best.get('recommended_assistant_kind') or 'n/d')} por {str(best.get('recommended_route') or 'n/d')}"
        review_count = len(list((self_examination or {}).get('recommended_adjustments') or []))
        return (
            f"Objetivo actual: {objective} | mejor ruta conocida: {route_summary} | "
            f"bloqueos activos: {len(world.detected_blocks or [])} | pendientes: {len(pending_items)} | "
            f"ajustes sugeridos: {review_count} | unresolved: {len(unresolved)}"
        )

    def _render_assistant_brief(self, package: PortableContextPackage) -> str:
        lines = [
            '# IABV v1.5 - Portable Context Package',
            '',
            f'Generado: {package.updated_at_utc.isoformat()}',
            f'Resumen: {package.summary}',
            '',
            'Usa este contexto como arranque rapido para una sesion nueva. Si algo aparece como UNRESOLVED, no lo des por confirmado.',
            '',
        ]
        for section in package.sections:
            lines.append(f'## {section.title}')
            lines.append(section.summary or 'Sin resumen.')
            for item in section.items[:6]:
                if section.section_id == 'architecture':
                    lines.append(f"- {str(item.get('component') or 'n/d')}: {str(item.get('status') or 'n/d')} | {str(item.get('detail') or '').strip()}")
                elif section.section_id == 'implemented_capabilities':
                    lines.append(f"- {str(item.get('capability') or 'n/d')}: {str(item.get('status') or 'n/d')} | {str(item.get('detail') or '').strip()}")
                elif section.section_id in {'learning', 'tool_discovery', 'tool_evolution', 'tool_evolution_decisions', 'self_examination', 'recommended_routes', 'validated_decisions', 'decision_history', 'user_metacognitive_intent', 'task_packet_summary'}:
                    label = str(item.get('label') or item.get('decision') or item.get('subject_key') or item.get('assistant_kind') or 'n/d')
                    detail = str(item.get('value') or item.get('route') or item.get('summary') or item.get('recommendation') or item.get('why') or item.get('detail') or '').strip()
                    assistant = str(item.get('assistant_kind') or '').strip()
                    suffix = f' | {assistant}' if assistant and assistant.lower() not in label.lower() else ''
                    lines.append(f'- {label}{suffix}: {detail}')
                elif section.section_id == 'interaction_lifecycle':
                    iid = str(item.get('interaction_id') or 'n/d')
                    preview = str(item.get('message_preview') or '')[:60]
                    outcome = str(item.get('outcome') or 'n/d')
                    resolved = item.get('resolved', outcome == 'resolved')
                    is_final = item.get('is_final', outcome not in ('prepared', 'awaiting_external_response', 'reused_context'))
                    provider = str(item.get('provider') or 'n/d')
                    dur = item.get('total_duration_ms', 0)
                    stalls = item.get('stall_count', 0)
                    early = item.get('had_early_technical_response', False)
                    inactive = item.get('window_went_inactive', False)
                    src = str(item.get('source') or 'n/d')
                    lines.append(
                        f'- [{iid}] "{preview}" | outcome={outcome} resolved={str(resolved).lower()} '
                        f'is_final={str(is_final).lower()} '
                        f'provider={provider} duration={dur}ms stalls={stalls} '
                        f'early_technical={early} window_inactive={inactive} source={src}'
                    )
                elif section.section_id == 'canonical_work_queue':
                    wid = str(item.get('id') or 'n/d')
                    wtitle = str(item.get('title') or 'n/d')[:80]
                    wscore = item.get('priority_score', 0)
                    wlabel = str(item.get('priority_label') or 'n/d')
                    wsrc = str(item.get('source') or 'n/d')
                    wnext = str(item.get('next_action') or 'n/d')[:60]
                    lines.append(f'- [{wlabel}|{wscore}] {wid}: {wtitle} (src={wsrc}) → {wnext}')
                elif section.section_id in {'operational_blocks', 'pending', 'unresolved'}:
                    label = str(item.get('kind') or item.get('issue_id') or item.get('title') or item.get('field') or 'n/d')
                    detail = str(item.get('detail') or item.get('summary') or item.get('recommended_change') or item.get('rationale') or '').strip()
                    lines.append(f'- {label}: {detail}')
                elif section.section_id == 'hard_rules':
                    lines.append(f"- {str(item.get('rule') or '').strip()}")
                else:
                    label = str(item.get('label') or item.get('component') or item.get('title') or 'n/d')
                    detail = str(item.get('value') or item.get('detail') or item.get('summary') or '').strip()
                    lines.append(f'- {label}: {detail}')
            lines.append(f"Fuente: {section.source_kind} | refs: {', '.join(section.source_refs) or 'n/d'} | actualizado: {section.last_updated.isoformat()}")
            if section.unresolved_fields:
                lines.append(f"UNRESOLVED: {', '.join(section.unresolved_fields)}")
            lines.append('')
        return '\n'.join(lines).strip()

    # ── P0.5: Shared Reality compact summary ───────────────────────
    def _shared_reality_section(
        self,
        *,
        review: dict[str, Any],
        now,
    ) -> PortableContextSection:
        """Export compact summary of shared reality + visual remediation findings.

        Includes P0.5 handoff patterns and P0.7 remediation patterns.
        Strips PII and full file paths — keeps only pattern, frequency,
        last assistant_kind, and recommended_action.
        """
        sr_categories = {
            # P0.5 handoff patterns
            'repeated_visual_mismatch',
            'user_browser_differs_from_iabv_session',
            'black_capture_repeated',
            'user_needed_to_explain_same_gap',
            # P0.7 remediation patterns
            'repeated_restore_without_recapture',
            'repeated_win32_restore_unavailable',
            'repeated_user_selection_needed',
            'repeated_restore_attempted',
        }
        items: list[dict[str, Any]] = []
        for finding in list(review.get('findings') or []):
            cat = str(finding.get('category') or '')
            if cat not in sr_categories:
                continue
            meta = dict(finding.get('metadata') or {})
            last_case = dict(meta.get('last_case') or {})
            items.append({
                'label': cat,
                'summary': str(finding.get('title') or '')[:120],
                'frequency': meta.get('frequency', 0),
                'last_assistant_kind': last_case.get('assistant_kind', 'unknown'),
                'recommended_action': meta.get('recommended_action', ''),
                'priority': meta.get('priority', 'medium'),
            })
        summary = (
            f'{len(items)} patrones de mismatch/remediación visual detectados'
            if items else
            'Sin patrones de mismatch visual ni remediación repetida'
        )
        return self._section(
            section_id='shared_reality_learning',
            title='Shared Reality Learning',
            summary=summary,
            items=items,
            source_kind='oses_shared_reality',
            source_refs=['OperationalSelfExaminationService', 'runtime_audit'],
            confidence=0.85 if items else 0.3,
            last_updated=now,
        )

    def _user_chrome_bridge_section(
        self,
        *,
        now,
    ) -> PortableContextSection:
        """P0.32: Export compact summary of user Chrome bridge state (no PII)."""
        import os
        cdp_active = os.environ.get('IABV_PREFER_CDP_SESSION') == '1'
        items: list[dict[str, Any]] = []
        bridge_events = 0
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            for ev in tracer.events(limit=200):
                kind = ev.get('kind', '')
                if kind.startswith('user_browser_bridge_'):
                    bridge_events += 1
        except Exception:
            pass
        items.append({
            'cdp_session_active': cdp_active,
            'bridge_events_total': bridge_events,
            'session_mode': 'user_chrome_cdp' if cdp_active else 'isolated_profile',
        })
        summary = (
            f'CDP bridge activo: {"si" if cdp_active else "no"}. '
            f'{bridge_events} eventos de bridge registrados.'
        )
        return self._section(
            section_id='user_chrome_bridge',
            title='User Chrome Bridge (P0.32)',
            summary=summary,
            items=items,
            source_kind='runtime_audit',
            source_refs=['RuntimeAuditTracer', 'IABV_PREFER_CDP_SESSION'],
            confidence=0.9 if bridge_events > 0 else 0.5,
            last_updated=now,
        )

    def _active_incident_frame_section(
        self,
        *,
        now,
    ) -> PortableContextSection:
        """P0.37: Export compact summary of active incident state (no PII)."""
        items: list[dict[str, Any]] = []
        incident_events = 0
        last_incident_state = 'none'
        unresolved_handoff = False
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            for ev in tracer.events(limit=200):
                kind = ev.get('kind', '')
                if kind == 'active_incident_frame_created':
                    incident_events += 1
                    last_incident_state = ev.get('data', {}).get('block_type', 'unknown')
                elif kind == 'incident_followup_resolved_or_unresolved':
                    resolution = ev.get('data', {}).get('resolution', '')
                    if resolution != 'resolved':
                        unresolved_handoff = True
        except Exception:
            pass
        items.append({
            'last_incident_state': last_incident_state,
            'unresolved_external_handoff': unresolved_handoff,
            'incident_frame_count': incident_events,
            'user_assistance_loop_status': 'active' if incident_events > 0 and not unresolved_handoff else 'idle',
        })
        summary = (
            f'Ultimo incidente: {last_incident_state}. '
            f'{incident_events} frames creados. '
            f'Handoff sin resolver: {"si" if unresolved_handoff else "no"}.'
        )
        return self._section(
            section_id='active_incident_frame',
            title='Active Incident Frame (P0.37)',
            summary=summary,
            items=items,
            source_kind='runtime_audit',
            source_refs=['RuntimeAuditTracer', 'ActiveIncidentFrame'],
            confidence=0.9 if incident_events > 0 else 0.5,
            last_updated=now,
        )

    # ------------------------------------------------------------------
    # P0.38: Web skill status + Devin repair status sections
    # ------------------------------------------------------------------

    def _web_skill_status_section(self, *, now) -> PortableContextSection:
        """Export compact web skill profile status. No PII/cookies/tokens."""
        items: list[dict[str, Any]] = []
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            scan_events = tracer.events(kind='assistant_web_skill_scan', limit=5)
            for ev in scan_events:
                data = ev.get('data', {})
                items.append({
                    'assistant_kind': data.get('assistant_kind', ''),
                    'auth_status': data.get('auth_status', 'unknown'),
                    'session_mode': data.get('session_mode', 'unknown'),
                    'cdp_available': data.get('cdp_available', False),
                    'window_found': data.get('window_found', False),
                    'phase': data.get('phase', ''),
                    'last_block': data.get('detail', ''),
                })
            quiescence_events = tracer.events(kind='external_consultation_quiescence', limit=5)
            for ev in quiescence_events:
                data = ev.get('data', {})
                items.append({
                    'type': 'quiescence_decision',
                    'decision': data.get('decision', ''),
                    'pressure_level': data.get('pressure_level', ''),
                    'assistant_kind': data.get('assistant_kind', ''),
                    'reason': str(data.get('reason', ''))[:100],
                })
        except Exception:
            pass
        summary = (
            f'{len(items)} eventos de web skill/quiescence registrados'
            if items else
            'Sin eventos de web skill registrados'
        )
        return self._section(
            section_id='web_skill_status',
            title='Web Skill Status (P0.38)',
            summary=summary,
            items=items,
            source_kind='runtime_audit_web_skill',
            source_refs=['RuntimeAuditTracer'],
            confidence=0.8 if items else 0.3,
            last_updated=now,
        )

    def _devin_repair_status_section(self, *, now) -> PortableContextSection:
        """Export compact Devin repair worker status. No PII/credentials."""
        items: list[dict[str, Any]] = []
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            devin_events = tracer.events(kind='devin_repair_worker', limit=10)
            for ev in devin_events:
                data = ev.get('data', {})
                items.append({
                    'phase': data.get('phase', ''),
                    'available': data.get('available', False),
                    'session_id': str(data.get('session_id', ''))[:12],
                    'detail': str(data.get('detail', ''))[:100],
                })
        except Exception:
            pass
        summary = (
            f'{len(items)} eventos de Devin repair worker registrados'
            if items else
            'Sin eventos de Devin repair worker'
        )
        return self._section(
            section_id='devin_repair_status',
            title='Devin Repair Worker Status (P0.38)',
            summary=summary,
            items=items,
            source_kind='runtime_audit_devin_repair',
            source_refs=['RuntimeAuditTracer'],
            confidence=0.8 if items else 0.3,
            last_updated=now,
        )

    def _capability_readiness_section(self, *, now) -> PortableContextSection:
        """P0.39: Export latest capability readiness per assistant. No PII."""
        items: list[dict[str, Any]] = []
        seen_assistants: set[str] = set()
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            readiness_events = tracer.events(kind='external_readiness_assessed', limit=20)
            for ev in reversed(readiness_events):
                data = ev.get('data', {})
                ak = data.get('assistant_kind', '')
                if ak in seen_assistants:
                    continue
                seen_assistants.add(ak)
                items.append({
                    'assistant_kind': ak,
                    'action_possible': data.get('action_possible', False),
                    'confidence': data.get('confidence', 0.0),
                    'blocking_reason': str(data.get('blocking_reason', ''))[:80],
                    'session_selected': data.get('session_selected', ''),
                    'security_block': data.get('security_block', 'none'),
                    'capture_mode': data.get('capture_mode', ''),
                })
        except Exception:
            pass
        has_ready = any(i.get('action_possible') for i in items)
        summary = (
            f'{len(items)} herramientas evaluadas; '
            + ('al menos 1 lista' if has_ready else 'ninguna lista actualmente')
        )
        unresolved: list[str] = []
        if not items:
            unresolved.append('no_readiness_data')
        elif not has_ready:
            unresolved.append('no_tool_action_possible')
        return self._section(
            section_id='capability_readiness',
            title='External Tool Capability Readiness (P0.39)',
            summary=summary,
            items=items,
            source_kind='runtime_audit_readiness',
            source_refs=['RuntimeAuditTracer', '_assess_external_readiness'],
            confidence=0.8 if items else 0.3,
            last_updated=now,
            unresolved_fields=unresolved if unresolved else None,
        )

    def _next_time_policy_section(self, *, now) -> PortableContextSection:
        """P0.40 Task E: Export learned next-time policies from runtime audit.

        Scans for 'incident_human_assistance_requested' events and builds
        compact policies without PII.
        """
        policies: list[dict[str, Any]] = []
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            events = tracer.events(kind='incident_human_assistance_requested', limit=20)
            seen: set[str] = set()
            for ev in reversed(events):
                data = ev.get('data', {})
                policy_key = data.get('policy', '')
                if policy_key and policy_key not in seen:
                    seen.add(policy_key)
                    policies.append({
                        'policy': policy_key,
                        'trigger': data.get('block_type', ''),
                        'action': data.get('user_action', ''),
                    })
        except Exception:
            pass
        summary = f'{len(policies)} next-time policies recorded'
        if not policies:
            policies.append({
                'policy': 'when_security_verification_show_window_first',
                'trigger': 'security_verification',
                'action': 'focus/open problem window before generic explanation',
                'source': 'default_from_P0.40',
            })
            summary = '1 default policy (no runtime events yet)'
        return self._section(
            section_id='next_time_policies',
            title='Next-Time Policies (P0.40)',
            summary=summary,
            items=policies,
            source_kind='runtime_audit_learning',
            source_refs=['RuntimeAuditTracer', '_record_show_window_learning'],
            confidence=0.7 if policies else 0.3,
            last_updated=now,
        )

    def _discernment_frame_section(self, *, now) -> PortableContextSection:
        """P0.69: export latest discernment frame as compact section."""
        items: list[dict[str, Any]] = []
        unresolved: list[str] = []
        try:
            from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
            svc = DiscernmentFrameService()
            export = svc.compact_export()
            if export.get('status') == 'no_frame':
                items.append({'status': 'no_frame_yet'})
                unresolved.append('no_discernment_frame_generated')
            else:
                items.append(export)
        except Exception:
            items.append({'status': 'service_unavailable'})
            unresolved.append('discernment_frame_service_unavailable')
        phase = items[0].get('phase', 'unknown') if items else 'unknown'
        grounding = items[0].get('grounding_status', 'unknown') if items else 'unknown'
        conf = items[0].get('confidence', 0.0) if items else 0.0
        summary = f'phase={phase}, grounding={grounding}, confidence={conf}'
        return self._section(
            section_id='discernment_frame',
            title='Metacognitive Discernment Frame (P0.69)',
            summary=summary,
            items=items,
            source_kind='discernment_frame_service',
            source_refs=['DiscernmentFrameService'],
            confidence=float(conf) if isinstance(conf, (int, float)) else 0.0,
            last_updated=now,
            unresolved_fields=unresolved,
        )

    def _metacognitive_roadmap_matrix_section(self, *, now) -> PortableContextSection:
        """P0.70: export metacognitive autonomy roadmap matrix."""
        items: list[dict[str, Any]] = []
        unresolved: list[str] = []
        try:
            import json as _json
            from pathlib import Path as _Path
            candidates = [
                _Path(self.workspace_root) / 'data' / 'evolution' / 'platform_pending' / 'task_metacognitive_autonomy_roadmap_matrix_p070.json',
            ]
            for p in candidates:
                if p.exists():
                    raw = _json.loads(p.read_text(encoding='utf-8'))
                    phases = raw.get('phases', [])
                    compact_phases = []
                    for ph in phases:
                        compact_phases.append({
                            'phase': ph.get('phase', ''),
                            'status': ph.get('status', 'unresolved'),
                            'missing_links_count': len(ph.get('missing_links', [])),
                            'risk_if_unfixed': ph.get('risk_if_unfixed', ''),
                        })
                    items.append({
                        'task_id': raw.get('task_id', ''),
                        'status': raw.get('status', ''),
                        'phases': compact_phases,
                    })
                    for ph in phases:
                        for ml in ph.get('missing_links', []):
                            unresolved.append(f'{ph["phase"]}:{ml}')
                    break
            if not items:
                items.append({'status': 'roadmap_file_not_found'})
                unresolved.append('metacognitive_roadmap_matrix_not_found')
        except Exception:
            items.append({'status': 'error_reading_roadmap'})
            unresolved.append('metacognitive_roadmap_matrix_read_error')

        completed = sum(1 for i in items[0].get('phases', []) if i.get('status') == 'completed') if items and 'phases' in items[0] else 0
        total = len(items[0].get('phases', [])) if items and 'phases' in items[0] else 0
        summary = f'{completed}/{total} phases completed' if total else 'no roadmap'
        return self._section(
            section_id='metacognitive_roadmap_matrix',
            title='Metacognitive Autonomy Roadmap Matrix (P0.70)',
            summary=summary,
            items=items,
            source_kind='platform_pending',
            source_refs=['task_metacognitive_autonomy_roadmap_matrix_p070.json'],
            confidence=0.8 if total else 0.0,
            last_updated=now,
            unresolved_fields=unresolved,
        )

    def _unresolved_metacognitive_links_section(self, *, now) -> PortableContextSection:
        """P0.70: collect unresolved metacognitive links across frame + roadmap."""
        items: list[dict[str, Any]] = []
        unresolved: list[str] = []
        try:
            from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
            svc = DiscernmentFrameService()
            frame = svc.latest_frame()
            if frame and frame.unresolved_fields:
                items.append({
                    'source': 'discernment_frame',
                    'unresolved': frame.unresolved_fields[:10],
                })
                unresolved.extend(frame.unresolved_fields[:10])
        except Exception:
            pass
        try:
            import json as _json
            from pathlib import Path as _Path
            p = _Path(self.workspace_root) / 'data' / 'evolution' / 'platform_pending' / 'task_metacognitive_autonomy_roadmap_matrix_p070.json'
            if p.exists():
                raw = _json.loads(p.read_text(encoding='utf-8'))
                roadmap_unresolved = raw.get('unresolved', [])
                if roadmap_unresolved:
                    items.append({
                        'source': 'roadmap_matrix',
                        'unresolved': roadmap_unresolved[:10],
                    })
                    unresolved.extend(roadmap_unresolved[:10])
        except Exception:
            pass
        if not items:
            items.append({'status': 'no_unresolved_links'})
        summary = f'{len(unresolved)} unresolved metacognitive links' if unresolved else 'all clear'
        return self._section(
            section_id='unresolved_metacognitive_links',
            title='Unresolved Metacognitive Links (P0.70)',
            summary=summary,
            items=items,
            source_kind='aggregated',
            source_refs=['DiscernmentFrameService', 'roadmap_matrix'],
            confidence=0.7 if not unresolved else 0.4,
            last_updated=now,
            unresolved_fields=unresolved,
        )

    def _section(
        self,
        *,
        section_id: str,
        title: str,
        summary: str,
        items: list[dict[str, Any]],
        source_kind: str,
        source_refs: list[str],
        confidence: float,
        last_updated,
        unresolved_fields: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PortableContextSection:
        return PortableContextSection(
            section_id=section_id,
            title=title,
            summary=summary,
            items=items,
            source_kind=source_kind,
            source_refs=source_refs,
            confidence=confidence,
            last_updated=last_updated,
            unresolved_fields=list(unresolved_fields or []),
            metadata=dict(metadata or {}),
        )
