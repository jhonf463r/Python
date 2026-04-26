from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
        self.decision_audit_trail: Any | None = None
        self._current_package: PortableContextPackage | None = None

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
        tool_discovery = self._tool_discovery_snapshot()
        tool_evolution = self._tool_evolution_snapshot()
        tool_evolution_decisions = self._tool_evolution_decision_snapshot()
        self_examination = self._self_examination_snapshot()
        cloud_reasoning_status = self._cloud_reasoning_snapshot()
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
            self._tool_discovery_section(status=tool_discovery, now=now),
            self._tool_evolution_section(status=tool_evolution, now=now),
            self._tool_evolution_decisions_section(snapshot=tool_evolution_decisions, now=now),
            self._self_examination_section(review=self_examination, now=now),
            self._cloud_reasoning_section(status=cloud_reasoning_status, now=now),
            self._recommended_routes_section(recommendations=recommendations, now=now),
            self._operational_blocks_section(world=world, recommendations=recommendations, now=now),
            self._validated_decisions_section(
                recommendations=recommendations,
                validation=validation,
                now=now,
            ),
            self._decision_history_section(decision_history=decision_history, now=now),
            self._pending_section(pending_items=pending_items, backlog_items=backlog_items, now=now),
            self._unresolved_section(unresolved=unresolved, now=now),
            self._hard_rules_section(now=now),
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
        items = pending_items[:4] + backlog_items[:4]
        summary = f'{len(pending_items)} pending issues y {len(backlog_items)} mejoras priorizadas.'
        if not items:
            summary = 'No tengo pendientes priorizados confirmados por evidencia persistida.'
        return self._section(
            section_id='pending',
            title='Pendientes priorizados',
            summary=summary,
            items=items,
            source_kind='persistent_backlog',
            source_refs=['pending_issue_repository', 'evolution_review_service'],
            confidence=0.8 if items else 0.0,
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:pending_backlog'],
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
                elif section.section_id in {'learning', 'tool_discovery', 'tool_evolution', 'tool_evolution_decisions', 'self_examination', 'recommended_routes', 'validated_decisions', 'decision_history', 'user_metacognitive_intent'}:
                    label = str(item.get('label') or item.get('decision') or item.get('subject_key') or item.get('assistant_kind') or 'n/d')
                    detail = str(item.get('value') or item.get('route') or item.get('summary') or item.get('recommendation') or item.get('why') or item.get('detail') or '').strip()
                    assistant = str(item.get('assistant_kind') or '').strip()
                    suffix = f' | {assistant}' if assistant and assistant.lower() not in label.lower() else ''
                    lines.append(f'- {label}{suffix}: {detail}')
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
