from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    AutonomousValidationSnapshot,
    EnvironmentSelfModel,
    ObjectiveNodeKind,
    PortableContextPackage,
    PortableContextSection,
    TaskContext,
    WorldModelSnapshot,
    utc_now,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage
try:
    from iabv_v15.services.adaptive.autonomy_governance_policy import (
        summarize_operational_budget_calibration,
    )
except ImportError:
    def summarize_operational_budget_calibration(*args, **kwargs) -> dict[str, Any]:
        return {
            'status': 'unavailable',
            'reason': 'autonomy_governance_operational_budget_helpers_missing',
            'sample_count': 0,
            'confidence': 0.0,
        }


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
        operational_budget_learning = self._operational_budget_learning_snapshot()
        code_audit_status = self._code_audit_snapshot()
        startup_health = self._startup_health_snapshot()
        birth_stability = self._birth_stability_snapshot()
        account_resource = self._account_resource_snapshot()
        tool_autonomy_status = self._tool_autonomy_status_snapshot(account_resource=account_resource)
        boot_profile = self._boot_profile_snapshot()
        audit_control_master = self._audit_control_master_snapshot()
        learning_history = self._learning_history_snapshot()
        evidence_basis = self._evidence_basis_snapshot(
            environment=environment,
            world=world,
            task_context=task_context,
        )
        task_packet_summary = self._task_packet_summary_snapshot()
        visual_target_binding = self._visual_target_binding_snapshot()
        formal_semantic_reasoning = self._formal_semantic_reasoning_snapshot()
        concept_weight_evidence = self._concept_weight_evidence_snapshot()
        algorithm_fitness = self._algorithm_fitness_snapshot()
        runtime_organ_matrix = self._runtime_organ_matrix_snapshot()
        runtime_learning_closure = self._runtime_learning_closure_snapshot()
        worker_timeout = self._worker_timeout_snapshot()
        pending_items = self._pending_items()
        platform_pending_items = self._platform_pending_items()
        module_progress = self._module_progress_snapshot()
        backlog_items = self._backlog_items()
        genesis_readiness = self._genesis_readiness_snapshot(
            startup_health=startup_health,
            birth_stability=birth_stability,
            evidence_basis=evidence_basis,
            visual_target_binding=visual_target_binding,
            runtime_learning_closure=runtime_learning_closure,
            self_examination=self_examination,
            validation=validation,
            pending_items=[*pending_items, *platform_pending_items],
        )
        universal_evolution_scorecard = self._universal_evolution_scorecard_snapshot(account_resource=account_resource)
        decision_history = self._decision_history(recommendations=recommendations)
        unresolved = self._unresolved_fields(
            environment=environment,
            world=world,
            validation=validation,
            recommendations=recommendations,
            goal_context=goal_context,
        )
        unresolved = list(dict.fromkeys([*unresolved, *list(self_examination.get('unresolved_risks') or [])]))
        
        # Extract operational continuity from task context if available
        operational_continuity = {}
        if task_context and hasattr(task_context, 'metadata'):
            operational_continuity = dict(task_context.metadata.get('operational_continuity') or {})
        
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
            self._operational_budget_learning_section(
                snapshot=operational_budget_learning,
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
            self._runtime_stability_section(now=now),  # P0.130
            self._code_audit_section(status=code_audit_status, now=now),
            self._cloud_reasoning_section(status=cloud_reasoning_status, now=now),
            self._startup_health_section(status=startup_health, now=now),
            self._birth_stability_section(status=birth_stability, now=now),
            self._interaction_lifecycle_section(now=now),
            self._worker_timeout_section(snapshot=worker_timeout, now=now),
        ]
        
        # Build account inventory continuity section first to reuse its snapshot
        # Pass account_resource to reuse raw pool/quota data and avoid duplicate scans
        inventory_section, inventory_snapshot = self._account_inventory_continuity_section(
            now=now,
            account_resource=account_resource,
        )
        sections.append(inventory_section)
        
        # Reuse the inventory snapshot for account resource section to avoid duplicate scanning
        sections.append(
            self._account_resource_section(
                status=account_resource,
                inventory_snapshot=inventory_snapshot,
                now=now,
            )
        )
        
        sections.extend([
            self._audit_control_master_section(snapshot=audit_control_master, now=now),
            self._learning_history_section(snapshot=learning_history, now=now),
            self._tool_coordination_section(now=now),
            self._tool_autonomy_status_section(snapshot=tool_autonomy_status, now=now),
            self._boot_profile_section(status=boot_profile, now=now),
            self._evidence_basis_section(evidence=evidence_basis, now=now),
            self._task_packet_summary_section(snapshot=task_packet_summary, now=now),
            self._visual_target_binding_section(snapshot=visual_target_binding, now=now),
            self._formal_semantic_reasoning_section(snapshot=formal_semantic_reasoning, now=now),
            self._concept_weight_evidence_section(snapshot=concept_weight_evidence, now=now),
            self._algorithm_fitness_section(snapshot=algorithm_fitness, now=now),
            self._runtime_organ_matrix_section(snapshot=runtime_organ_matrix, now=now),
            self._artifact_lifecycle_section(now=now),  # P0.134/P0.136
            self._runtime_learning_closure_section(snapshot=runtime_learning_closure, now=now),
            self._universal_evolution_scorecard_section(snapshot=universal_evolution_scorecard, now=now),
            self._genesis_readiness_section(snapshot=genesis_readiness, now=now),
            self._recommended_routes_section(recommendations=recommendations, now=now),
            self._operational_blocks_section(world=world, recommendations=recommendations, now=now),
            self._validated_decisions_section(
                recommendations=recommendations,
                validation=validation,
                now=now,
            ),
            self._decision_history_section(decision_history=decision_history, now=now),
            self._module_progress_section(snapshot=module_progress, now=now),
            self._pending_section(pending_items=pending_items, backlog_items=backlog_items, now=now),
            self._canonical_work_queue_section(now=now),
            self._unresolved_section(unresolved=unresolved, now=now),
            self._hard_rules_section(now=now),
            self._user_identity_section(now=now),
            self._long_term_goals_section(now=now),
        ])
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
                'operational_budget_learning': operational_budget_learning,
                'tool_discovery_signals': list(tool_discovery.get('signals') or []),
                'tool_evolution_summary': dict(tool_evolution.get('summary_payload') or {}),
                'tool_evolution_proposals': list(tool_evolution.get('proposals') or []),
                'tool_evolution_degraded_subjects': list(tool_evolution.get('degraded_subjects') or []),
                'tool_evolution_decision_summary': dict(tool_evolution_decisions.get('summary_payload') or {}),
                'tool_evolution_validated_proposals': list(tool_evolution_decisions.get('entries') or []),
                'cloud_reasoning_status': dict(cloud_reasoning_status),
                'startup_health': dict(startup_health),
                'birth_stability': dict(birth_stability),
                'account_resource': dict(account_resource),
                'boot_profile': dict(boot_profile),
                'evidence_basis': dict(evidence_basis),
                'task_packet_summary': dict(task_packet_summary),
                'visual_target_binding': dict(visual_target_binding),
                'formal_semantic_reasoning': dict(formal_semantic_reasoning),
                'concept_weight_evidence': dict(concept_weight_evidence),
                'runtime_learning_closure': dict(runtime_learning_closure),
                'worker_timeout_summary': dict(worker_timeout),
                'genesis_readiness': dict(genesis_readiness),
                'module_progress': dict(module_progress),
                'coordination_patterns': coordination_patterns,
                'chat_stats': self._chat_stats_snapshot(),
                'autoexamination_summary': dict(self_examination.get('summary_payload') or {}),
                'recurring_issues': list(self_examination.get('recurring_issues') or []),
                'recommended_adjustments': list(self_examination.get('recommended_adjustments') or []),
                    'validated_improvements': list(self_examination.get('validated_improvements') or []),
                    'recommendation_feedback': list(self_examination.get('recommendation_feedback') or []),
                    'feedback_summary': dict(self_examination.get('feedback_summary') or {}),
                    'unresolved_risks': list(self_examination.get('unresolved_risks') or []),
                'operational_continuity': operational_continuity,
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
            persisted = self._load_persisted_environment_self_model()
            if persisted is not None:
                return persisted
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            return service.current_model()
        except Exception:
            persisted = self._load_persisted_environment_self_model()
            if persisted is not None:
                return persisted
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _world_model(self) -> WorldModelSnapshot:
        service = self.world_model_service
        if service is None or not hasattr(service, 'current_model'):
            persisted = self._load_persisted_world_model()
            if persisted is not None:
                return persisted
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            model = service.current_model()
            return model if model is not None else WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        except Exception:
            persisted = self._load_persisted_world_model()
            if persisted is not None:
                return persisted
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _load_persisted_environment_self_model(self) -> EnvironmentSelfModel | None:
        path = Path(self.workspace_root) / 'data' / 'evolution' / 'environment_self_model' / 'latest.json'
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding='utf-8', errors='replace'))
            if not isinstance(payload, dict):
                return None
            metadata = dict(payload.get('metadata') or {})
            metadata['portable_context_source'] = 'persisted_environment_self_model_latest'
            payload['metadata'] = metadata
            return EnvironmentSelfModel.model_validate(payload)
        except Exception:
            return None

    def _load_persisted_world_model(self) -> WorldModelSnapshot | None:
        path = Path(self.workspace_root) / 'data' / 'evolution' / 'world_model' / 'latest.json'
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding='utf-8', errors='replace'))
            if not isinstance(payload, dict):
                return None
            metadata = dict(payload.get('metadata') or {})
            metadata['portable_context_source'] = 'persisted_world_model_latest'
            payload['metadata'] = metadata
            return WorldModelSnapshot.model_validate(payload)
        except Exception:
            return None

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

        # False-ready detection: ``splash_set_ready`` honesto debe llegar
        # *despues* de ``shell_loader_ready``.  With phased construction,
        # ``populate_ui_done`` arrives much later (Phase 3 VMs are deferred)
        # so splash closing before populate_ui_done is EXPECTED — not a bug.
        # The check is: did the splash close before the shell was actually
        # ready?  Or did the fallback fire instead of the honest signal?
        false_ready = False
        false_ready_reason: list[str] = []
        splash_ms = phase_to_ms.get('splash_set_ready')
        populate_done_ms = phase_to_ms.get('populate_ui_done')
        shell_ready_ms = phase_to_ms.get('shell_loader_ready')
        shell_ready_fallback_ms = phase_to_ms.get('shell_loader_ready_fallback')
        if splash_ms is not None and shell_ready_ms is not None:
            if splash_ms < shell_ready_ms:
                false_ready = True
                false_ready_reason.append('splash_set_ready_before_shell_loader_ready')
        if splash_ms is not None and shell_ready_ms is None and shell_ready_fallback_ms is None:
            false_ready = True
            false_ready_reason.append('splash_set_ready_without_shell_loader_ready')
        if shell_ready_fallback_ms is not None:
            false_ready = True
            false_ready_reason.append('shell_loader_ready_fallback_used')
        if false_ready:
            recent_blockers.append({
                'phase': 'startup_false_ready',
                'reasons': false_ready_reason,
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

    def _birth_stability_snapshot(self) -> dict[str, Any]:
        """Summarize whether IABV learned from its own startup/freezes.

        This is the portable counterpart to OSES runtime-birth findings. It
        reads only durable artifacts so a new IA/session can see if the
        organism observed its birth, whether duplicate launches were handled,
        and whether stable-resource freezes still point to main-thread blind
        spots.
        """
        reports = self._birth_recent_freeze_reports(limit=5)
        stable = [
            r for r in reports
            if self._birth_freeze_resources_are_stable(r)
            and str(r.get('trigger') or '') == 'auto_ui_heartbeat_stall'
        ]
        cause_counts = Counter(self._birth_classify_freeze_cause(r) for r in stable)
        worst_ms = max((self._birth_freeze_duration_ms(r) for r in stable), default=0.0)
        duplicate_summary = self._birth_startup_duplicate_summary()
        metacognition_skipped = self._birth_metacognition_was_skipped()
        unresolved: list[str] = []
        if stable and metacognition_skipped:
            unresolved.append('UNRESOLVED:idle_budgeted_startup_metacognition_policy')
        if not reports:
            unresolved.append('UNRESOLVED:freeze_reports_missing')
        status = 'analyzed' if reports or duplicate_summary.get('status') == 'analyzed' else 'no_data'
        dominant_cause = ''
        if cause_counts:
            dominant_cause = cause_counts.most_common(1)[0][0]
        return {
            'status': status,
            'stable_resource_freeze_count': len(stable),
            'worst_freeze_ms': worst_ms,
            'dominant_cause': dominant_cause,
            'cause_counts': dict(cause_counts),
            'startup_duplicate_summary': duplicate_summary,
            'startup_metacognition_skipped': metacognition_skipped,
            'recent_freeze_reports': [
                {
                    'file': r.get('_file', ''),
                    'trigger': r.get('trigger', ''),
                    'duration_ms': self._birth_freeze_duration_ms(r),
                    'resources_stable': self._birth_freeze_resources_are_stable(r),
                    'cause': self._birth_classify_freeze_cause(r),
                }
                for r in reports[:3]
            ],
            'unresolved_fields': unresolved,
        }

    def _birth_recent_freeze_reports(self, *, limit: int = 5) -> list[dict[str, Any]]:
        reports_dir = Path(self.workspace_root) / 'data' / 'evolution' / 'incident_reports'
        if not reports_dir.exists() or not reports_dir.is_dir():
            return []
        try:
            paths = sorted(
                reports_dir.glob('freeze_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:limit]
        except OSError:
            return []
        reports: list[dict[str, Any]] = []
        root = Path(self.workspace_root)
        for path in paths:
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            payload['_file'] = path.name
            try:
                payload['_relative_path'] = str(path.relative_to(root))
            except ValueError:
                payload['_relative_path'] = str(path)
            reports.append(payload)
        return reports

    @staticmethod
    def _birth_freeze_duration_ms(report: dict[str, Any]) -> float:
        for source in (
            report.get('duration_ms'),
            (report.get('extra') or {}).get('duration_ms'),
            (report.get('metadata') or {}).get('duration_ms'),
        ):
            try:
                value = float(source)
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass
        match = re.search(r'(\d+(?:\.\d+)?)\s*ms', str(report.get('user_description') or ''))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _birth_freeze_resources_are_stable(report: dict[str, Any]) -> bool:
        resources = dict(report.get('resources') or {})
        try:
            cpu = float(resources.get('cpu_load') or resources.get('cpu_percent') or 0.0)
        except (TypeError, ValueError):
            cpu = 0.0
        try:
            ram_available = float(resources.get('ram_available_mb') or 0.0)
        except (TypeError, ValueError):
            ram_available = 0.0
        try:
            ram_used_pct = float(resources.get('ram_used_pct') or 0.0)
        except (TypeError, ValueError):
            ram_used_pct = 0.0
        return cpu < 45.0 and (ram_available >= 1024.0 or ram_used_pct < 85.0)

    @staticmethod
    def _birth_classify_freeze_cause(report: dict[str, Any]) -> str:
        parts: list[str] = []
        for container in (report, dict(report.get('extra') or {})):
            for key in ('main_thread_stack_during_stall', 'main_thread_stack', 'stack'):
                value = container.get(key)
                if isinstance(value, list):
                    parts.extend(str(item) for item in value)
                elif value:
                    parts.append(str(value))
        recent = json.dumps(
            ((report.get('runtime_audit_context') or {}).get('recent_events') or []),
            ensure_ascii=False,
        )
        text = f'{" ".join(parts)} {recent}'.lower()
        if 'execution_dossier_repository' in text or 'json.loads' in text:
            return 'main_thread_dossier_json_io'
        if 'autonomy_activity_projector' in text or 'tool_record_repository' in text:
            return 'main_thread_autonomy_dock_db_projection'
        if 'datachanged.emit' in text or '_apply_task_result' in text:
            return 'qml_datachanged_emit_refresh'
        if 'control_autonomy_dock_refresh' in text:
            return 'autonomy_dock_refresh_churn'
        if 'browser_security_verification' in text or 'external_consultation' in text:
            return 'external_consultation_handoff_ui_churn'
        if 'app.exec' in text:
            return 'qt_event_loop_starvation_observed'
        return 'unknown_main_thread_stall'

    def _birth_metacognition_was_skipped(self) -> bool:
        timeline = Path(self.workspace_root) / 'data' / 'logs' / 'startup_timeline.jsonl'
        if not timeline.exists():
            return False
        try:
            lines = timeline.read_text(encoding='utf-8', errors='replace').splitlines()[-120:]
        except OSError:
            return False
        return any(
            'deferred_metacognition_skipped' in line
            or 'startup_metacognition_disabled_for_interactivity' in line
            for line in lines
        )

    def _birth_startup_duplicate_summary(self) -> dict[str, Any]:
        audit = Path(self.workspace_root) / 'data' / 'logs' / 'startup_audit.jsonl'
        if not audit.exists():
            return {'status': 'no_startup_audit'}
        try:
            lines = audit.read_text(encoding='utf-8', errors='replace').splitlines()[-80:]
        except OSError:
            return {'status': 'unreadable'}
        blocked = 0
        focused = 0
        reasons: Counter[str] = Counter()
        for line in lines:
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get('event') != 'startup_duplicate_blocked':
                continue
            data = dict(event.get('data') or {})
            blocked += 1
            reason = str(data.get('reason') or 'unknown')
            reasons[reason] += 1
            if data.get('focus_success') is True:
                focused += 1
        return {
            'status': 'analyzed',
            'blocked_count': blocked,
            'focus_success_count': focused,
            'reasons': dict(reasons),
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
        
        Returns a dict with the processed status and also includes the raw
        pool and all_quota data for reuse by build_inventory_snapshot().
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
            # Pass all_quota to avoid duplicate call to get_all_quota_status()
            workers = estimate_available_workers(all_quota=quotas if 'error' not in quotas else None)
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
        result = {
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
        
        # Include raw data for reuse by build_inventory_snapshot()
        # Each source is preserved independently to handle partial failures
        if 'error' not in workers:
            result['_raw_pool'] = workers
        if 'error' not in quotas:
            result['_raw_quota'] = quotas
        
        return result

    def _account_resource_section(self, *, status: dict[str, Any] | None, inventory_snapshot: Any | None, now) -> PortableContextSection:
        """Export account/quota/worker health to portable context.

        Ensures the next session knows: which accounts have messages left,
        which are exhausted, what tools have active workers, and what
        secrets are missing — without re-scanning everything.

        If inventory_snapshot is provided, reuses its data to avoid
        duplicate scanning of the same underlying sources.
        """
        items: list[dict[str, Any]] = []
        
        # Reuse data from inventory snapshot if available to avoid duplicate scanning
        if inventory_snapshot is not None:
            st = 'ok'
            # Extract data from the typed snapshot
            for entry in inventory_snapshot.continuity_queue[:8]:
                items.append({
                    'label': f"{entry.tool}: {entry.email}",
                    'remaining': entry.quota_remaining,
                    'limit': entry.quota_limit,
                    'status': 'available',
                })
            for entry in inventory_snapshot.entries[:5]:
                if entry.exhausted:
                    resets = entry.quota_resets_at.isoformat() if entry.quota_resets_at else ''
                    items.append({
                        'label': f"{entry.tool}: {entry.email}",
                        'status': 'exhausted',
                        'resets_at': resets,
                    })
            
            avail = inventory_snapshot.active_count
            exhausted = inventory_snapshot.exhausted_count
            remaining = inventory_snapshot.total_remaining_messages
            # Preserve tools_available and secrets_missing from status if available
            tools = status.get('workers_by_tool', []) if status else []
            missing_secrets = status.get('secrets_missing', []) if status else []
            read_failures = []
        elif status is not None:
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
        else:
            st = 'scanner_unavailable'
            avail = 0
            exhausted = 0
            remaining = 0
            tools = []
            missing_secrets = []
            read_failures = []

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

    def _account_inventory_continuity_section(self, *, now, account_resource: dict[str, Any] | None = None) -> tuple[PortableContextSection, Any]:
        """Export formal account inventory for session continuity.

        Ensures the next session inherits: which accounts exist, their
        quota status, the continuity queue (ranked next-best accounts),
        and any UNRESOLVED items.  This section complements the lighter
        ``account_resource_health`` section with the full typed snapshot.
        
        Returns a tuple of (section, snapshot) so the snapshot can be
        reused by _account_resource_section to avoid duplicate scanning.
        
        If account_resource is provided and contains raw pool/quota data,
        those are reused to avoid duplicate calls to estimate_available_workers()
        and get_all_quota_status().
        """
        items: list[dict[str, Any]] = []
        unresolved_fields: list[str] = []
        snapshot = None

        try:
            from iabv_v15.services.account_resource_scanner import (
                build_inventory_snapshot,
            )
            
            # Reuse raw data from account_resource if available to avoid duplicate scans
            pool = account_resource.get('_raw_pool') if account_resource else None
            all_quota = account_resource.get('_raw_quota') if account_resource else None
            
            snapshot = build_inventory_snapshot(pool=pool, all_quota=all_quota)

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

        section = self._section(
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
        
        return section, snapshot

    # ------------------------------------------------------------------
    # Audit control master — agent session gate snapshot
    # ------------------------------------------------------------------

    def _audit_control_master_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        """Export agent session gate snapshot as audit control master section.

        P0.136B: PortableContext exporta snapshot de agent_session_gate/latest.json
        como sección audit_control_master para que OSES pueda detectar riesgos
        (stale tasks, duplicate findings, agent delivery without gate) sin
        escanear filesystem pesado.
        """
        st = str(snapshot.get('status') or 'no_snapshot')
        items: list[dict[str, Any]] = []
        unresolved_fields: list[str] = list(snapshot.get('unresolved_fields') or [])

        if st == 'ok':
            agent = str(snapshot.get('agent') or 'unknown')
            generated_at = str(snapshot.get('generated_at') or '')
            active_count = snapshot.get('active_objectives_count', 0)
            stale_count = snapshot.get('stale_or_partial_count', 0)
            duplicate_count = snapshot.get('duplicate_risks_count', 0)
            human_review = snapshot.get('human_review_required', False)

            items.append({'label': 'agent', 'value': agent})
            items.append({'label': 'generated_at', 'value': generated_at})
            items.append({'label': 'active_objectives_count', 'value': active_count})
            items.append({'label': 'stale_or_partial_count', 'value': stale_count})
            items.append({'label': 'duplicate_risks_count', 'value': duplicate_count})
            items.append({'label': 'human_review_required', 'value': human_review})

            # Raw snapshot preview
            raw = snapshot.get('raw_snapshot', {})
            if raw:
                for key in ['active_objectives', 'stale_or_partial', 'duplicate_risks']:
                    values = list(raw.get(key) or [])
                    if values:
                        items.append({
                            'label': f'{key}_preview',
                            'value': f'{len(values)} items',
                            'detail': str(values[0]) if values else '',
                        })

            summary = (
                f'Agent session gate ({agent}): {active_count} objetivos activos, '
                f'{stale_count} stale/partial, {duplicate_count} duplicate risks, '
                f'human_review={human_review}.'
            )
            confidence = 0.85
        elif st == 'no_snapshot':
            summary = 'Agent session gate snapshot no disponible. PortableContext marca UNRESOLVED.'
            confidence = 0.0
            unresolved_fields.append('UNRESOLVED:agent_session_gate_snapshot_missing')
        elif st == 'read_error':
            summary = 'Error al leer agent session gate snapshot.'
            confidence = 0.0
            unresolved_fields.append('UNRESOLVED:agent_session_gate_read_error')
        else:
            summary = f'Agent session gate status: {st}'
            confidence = 0.0

        return self._section(
            section_id='audit_control_master',
            title='Control maestro de auditoría (agent session gate)',
            summary=summary,
            items=items,
            source_kind='agent_session_gate',
            source_refs=['scripts/devin_session_gate.py', 'data/evolution/agent_session_gate/latest.json'],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(unresolved_fields)),
            metadata={
                'status': st,
                'agent': snapshot.get('agent', ''),
                'generated_at': snapshot.get('generated_at', ''),
                'active_objectives_count': snapshot.get('active_objectives_count', 0),
                'stale_or_partial_count': snapshot.get('stale_or_partial_count', 0),
                'duplicate_risks_count': snapshot.get('duplicate_risks_count', 0),
                'human_review_required': snapshot.get('human_review_required', False),
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
        readiness: dict[str, Any] = {}

        try:
            discovery = self.tool_discovery_service
            if discovery is not None and hasattr(discovery, 'external_coordination_readiness'):
                readiness = dict(discovery.external_coordination_readiness() or {})
                for family, payload in list(dict(readiness.get('families') or {}).items())[:6]:
                    if not isinstance(payload, dict):
                        continue
                    items.append({
                        'label': f"familia:{family}",
                        'value': (
                            f"readiness={payload.get('readiness', '')} "
                            f"tool={payload.get('best_tool_id', '')} lane={payload.get('capture_lane', '')}"
                        ),
                        'detail': str(payload.get('next_human_action') or payload.get('recommended_use') or ''),
                    })
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
                readiness_status = str(readiness.get('status') or '').strip()
                if readiness_status:
                    summary = f'{len(items)} senales de coordinacion; readiness={readiness_status}.'
                else:
                    summary = f'{len(items)} selecciones recientes de herramienta registradas con trazabilidad.'
                confidence = 0.78
            else:
                unresolved_fields.append('UNRESOLVED:no_recent_tool_selections')
            unresolved_fields.extend(list(readiness.get('unresolved_fields') or []))
        except Exception:
            unresolved_fields.append('UNRESOLVED:tool_coordination_read_error')

        return self._section(
            section_id='tool_coordination',
            title='Coordinacion limit-aware de herramientas',
            summary=summary,
            items=items,
            source_kind='adaptive_task_orchestrator',
            source_refs=['tool_selection_summary', 'worker_gate', 'ToolDiscoveryService.external_coordination_readiness'],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(unresolved_fields)),
            metadata={
                'external_coordination_readiness': readiness,
            },
        )

    def _tool_autonomy_status_snapshot(self, *, account_resource: dict[str, Any] | None = None) -> dict[str, Any]:
        """Strict live-readiness contract for external tools.

        This complements the broader coordination section.  It is intentionally
        read-only and fail-closed: missing evidence becomes UNRESOLVED instead
        of an optimistic capability claim.
        
        Args:
            account_resource: Optional account resource snapshot containing raw data
                (_raw_pool, _raw_quota) to reuse for inventory snapshot construction.
        """
        discovery = self.tool_discovery_service
        if discovery is None or not hasattr(discovery, 'tool_autonomy_status'):
            return {
                'status': 'unavailable',
                'tools': [],
                'unresolved_fields': ['UNRESOLVED:tool_autonomy_status_service_missing'],
            }
        account_inventory = None
        # Skip build_inventory_snapshot when account_resource is provided to avoid duplicate calls
        # The data will be extracted from account_resource directly
        if account_resource is None:
            try:
                from iabv_v15.services.account_resource_scanner import build_inventory_snapshot
                account_inventory = build_inventory_snapshot()
            except Exception:
                account_inventory = None

        devin_status: dict[str, Any] | None = None
        try:
            from iabv_v15.services.evolution.devin_runtime_concierge import devin_runtime_status
            registry = getattr(discovery, 'tool_registry', None)
            adapters = getattr(registry, 'adapters', {}) if registry is not None else {}
            adapter = adapters.get('devin_api') if isinstance(adapters, dict) else None
            devin_status = devin_runtime_status(adapter=adapter, probe=False)
        except Exception:
            devin_status = {
                'ready': False,
                'unresolved_fields': ['UNRESOLVED:devin_runtime_status_read_error'],
            }
        try:
            return dict(discovery.tool_autonomy_status(
                account_inventory=account_inventory,
                devin_status=devin_status,
            ) or {})
        except Exception as exc:
            return {
                'status': 'read_error',
                'tools': [],
                'unresolved_fields': ['UNRESOLVED:tool_autonomy_status_read_error'],
                'error': f'{type(exc).__name__}: {exc}'[:200],
            }

    def _tool_autonomy_status_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        tools = list(snapshot.get('tools') or [])
        usable = [item for item in tools if isinstance(item, dict) and item.get('can_use_now')]
        blocked = [item for item in tools if isinstance(item, dict) and not item.get('can_use_now')]
        items: list[dict[str, Any]] = []
        for item in tools[:8]:
            if not isinstance(item, dict):
                continue
            items.append({
                'label': f"{item.get('assistant_kind', '')}:{item.get('tool_id', '')}",
                'value': (
                    f"can_use_now={bool(item.get('can_use_now'))} "
                    f"live_verified={bool(item.get('live_verified'))} "
                    f"readiness={item.get('readiness', '')}"
                ),
                'detail': str(item.get('last_failure_reason') or item.get('next_human_action') or item.get('next_machine_action') or ''),
            })
        summary = str(snapshot.get('summary') or '')
        if not summary:
            summary = f'{len(usable)} herramientas usables, {len(blocked)} no verificadas o bloqueadas.'
        return self._section(
            section_id='tool_autonomy_status',
            title='Estado vivo de herramientas externas',
            summary=summary,
            items=items,
            source_kind='tool_discovery',
            source_refs=list(snapshot.get('source_refs') or [
                'ToolRegistry',
                'WorldModelSnapshot',
                'AccountInventorySnapshot',
                'DevinRuntimeConcierge',
            ]),
            confidence=0.82 if tools else 0.2,
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(list(snapshot.get('unresolved_fields') or []))),
            metadata={
                'status': snapshot.get('status', ''),
                'usable_tool_ids': list(snapshot.get('usable_tool_ids') or []),
                'human_actions': list(snapshot.get('human_actions') or [])[:6],
                'machine_actions': list(snapshot.get('machine_actions') or [])[:6],
                'policy': snapshot.get('policy', 'do_not_report_tool_success_without_live_verification'),
            },
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

    def _audit_control_master_snapshot(self) -> dict[str, Any]:
        """Read agent session gate snapshot as compact audit control master.

        P0.136B: PortableContext exporta snapshot de agent_session_gate/latest.json
        como sección audit_control_master para que OSES pueda detectar riesgos
        (stale tasks, duplicate findings, agent delivery without gate) sin
        escanear filesystem pesado.

        Returns a dict with:
            - ``status``: ``no_snapshot`` / ``read_error`` / ``ok``
            - ``agent``: agent name from snapshot
            - ``generated_at``: ISO timestamp when snapshot was generated
            - ``active_objectives_count``: number of active objectives
            - ``stale_or_partial_count``: number of stale/partial tasks
            - ``duplicate_risks_count``: number of duplicate risks
            - ``human_review_required``: boolean from snapshot
            - ``unresolved_fields``: list of UNRESOLVED tags
        """
        gate_path = Path(self.workspace_root) / 'data' / 'evolution' / 'agent_session_gate' / 'latest.json'
        if not gate_path.exists():
            return {
                'status': 'no_snapshot',
                'unresolved_fields': ['UNRESOLVED:agent_session_gate_snapshot_missing'],
            }
        try:
            import json
            snapshot = json.loads(gate_path.read_text(encoding='utf-8', errors='ignore'))
        except Exception as exc:
            return {
                'status': 'read_error',
                'unresolved_fields': ['UNRESOLVED:agent_session_gate_read_error'],
                'error': str(exc)[:200],
            }

        active_objectives = list(snapshot.get('active_objectives') or [])
        stale_or_partial = list(snapshot.get('stale_or_partial_tasks') or [])
        duplicate_risks = list(snapshot.get('duplicate_risks') or [])
        unresolved = list(snapshot.get('unresolved') or [])

        return {
            'status': 'ok',
            'agent': str(snapshot.get('agent') or 'unknown'),
            'generated_at': str(snapshot.get('generated_at') or ''),
            'active_objectives_count': len(active_objectives),
            'stale_or_partial_count': len(stale_or_partial),
            'duplicate_risks_count': len(duplicate_risks),
            'human_review_required': bool(snapshot.get('human_review_required')),
            'unresolved_fields': unresolved,
            'raw_snapshot': {
                'active_objectives': active_objectives[:5],
                'stale_or_partial': stale_or_partial[:5],
                'duplicate_risks': duplicate_risks[:5],
            },
        }

    def _learning_history_snapshot(self) -> dict[str, Any]:
        """Read gate POST and OSES findings to build learning history.

        P0.136B: PortableContext captura validación cruzada entre teoría previa
        (gate PRE) y realidad posterior (gate POST + OSES findings) para que
        la siguiente sesión parta de experiencia acumulativa.

        Returns a dict with:
            - ``status``: ``no_history`` / ``read_error`` / ``ok``
            - ``recent_theory_validations``: list of recent gate theory validations
            - ``repeated_patterns``: patterns detected across sessions
            - ``learning_signals``: signals for future sessions
            - ``unresolved_fields``: list of UNRESOLVED tags
        """
        post_path = Path(self.workspace_root) / 'data' / 'evolution' / 'agent_session_gate' / 'latest_post.json'
        oses_path = Path(self.workspace_root) / 'data' / 'evolution' / 'self_examination' / 'latest.json'

        if not post_path.exists() and not oses_path.exists():
            return {
                'status': 'no_history',
                'unresolved_fields': ['UNRESOLVED:learning_history_no_data'],
            }

        try:
            recent_theory_validations: list[dict[str, Any]] = []
            
            # Leer historial acumulado bajo history/ no solo latest.json
            history_dir = Path(self.workspace_root) / 'data' / 'evolution' / 'agent_session_gate' / 'history'
            if history_dir.exists():
                for json_file in sorted(history_dir.glob('*.json'))[-10:]:  # Últimos 10 archivos de historial
                    data = safe_read_json(json_file)
                    if '_read_error' not in data:
                        if data.get('mode') == 'post':
                            theory_validation = data.get('theory_validation', {})
                            if theory_validation.get('pre_available'):
                                recent_theory_validations.append({
                                    'session_time': data.get('generated_at', ''),
                                    'agent': data.get('agent', ''),
                                    'pre_theory': theory_validation.get('pre_theory', {}),
                                    'post_reality': theory_validation.get('post_reality', {}),
                                    'divergences': theory_validation.get('divergences', []),
                                    'verdict': data.get('verdict', ''),
                                })
            
            # Leer latest_post.json si no hay suficiente historial
            if len(recent_theory_validations) < 5 and post_path.exists():
                post = safe_read_json(post_path)
                if '_read_error' not in post:
                    theory_validation = post.get('theory_validation', {})
                    if theory_validation.get('pre_available'):
                        recent_theory_validations.append({
                            'session_time': post.get('generated_at', ''),
                            'agent': post.get('agent', ''),
                            'pre_theory': theory_validation.get('pre_theory', {}),
                            'post_reality': theory_validation.get('post_reality', {}),
                            'divergences': theory_validation.get('divergences', []),
                            'verdict': post.get('verdict', ''),
                        })

            repeated_patterns: list[dict[str, Any]] = []
            if oses_path.exists():
                oses = safe_read_json(oses_path)
                if '_read_error' not in oses:
                    findings = list(oses.get('findings', []))
                    # Detectar patrones repetidos
                    from collections import Counter
                    categories = [f.get('category', '') for f in findings if f.get('category')]
                    category_counts = Counter(categories)
                    for category, count in category_counts.most_common(5):
                        if count >= 2:
                            repeated_patterns.append({
                                'pattern': category,
                                'occurrence_count': count,
                                'severity': 'recurring',
                            })

            learning_signals: list[str] = []
            # Usar slices seguros que no fallen si hay menos datos
            validation_slice = recent_theory_validations[-3:] if len(recent_theory_validations) >= 3 else recent_theory_validations
            if recent_theory_validations:
                for validation in validation_slice:
                    divergences = validation.get('divergences', [])
                    if divergences:
                        learning_signals.append(f"Theory divergence detected: {divergences[0][:100]}")
                    if validation.get('verdict') == 'ready':
                        learning_signals.append(f"Session completed successfully at {validation.get('session_time', '')}")

            if repeated_patterns:
                pattern_slice = repeated_patterns[:3] if len(repeated_patterns) >= 3 else repeated_patterns
                for pattern in pattern_slice:
                    learning_signals.append(f"Recurring pattern: {pattern['pattern']} ({pattern['occurrence_count']} occurrences)")

            # Validar que hay datos suficientes
            if len(recent_theory_validations) == 0 and len(repeated_patterns) == 0:
                return {
                    'status': 'insufficient_data',
                    'unresolved_fields': ['UNRESOLVED:learning_history_insufficient_data'],
                    'recent_theory_validations': [],
                    'repeated_patterns': [],
                    'learning_signals': ['Insufficient data for learning history analysis'],
                }

            return {
                'status': 'ok',
                'recent_theory_validations': recent_theory_validations[-5:] if len(recent_theory_validations) >= 5 else recent_theory_validations,
                'repeated_patterns': repeated_patterns,
                'learning_signals': learning_signals[-10:] if len(learning_signals) >= 10 else learning_signals,
                'unresolved_fields': [],
            }
        except Exception as exc:
            return {
                'status': 'read_error',
                'unresolved_fields': ['UNRESOLVED:learning_history_read_error'],
                'error': str(exc)[:200],
            }

    def _learning_history_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        """Export learning history as portable context section.

        P0.136B: PortableContext exporta historial de aprendizaje para que
        la siguiente sesión pueda responder "esto ya pasó antes" o "esta
        teoría local falló en este contexto".
        """
        st = str(snapshot.get('status') or 'no_history')
        items: list[dict[str, Any]] = []
        unresolved_fields: list[str] = list(snapshot.get('unresolved_fields') or [])

        if st == 'ok':
            recent_validations = list(snapshot.get('recent_theory_validations', []))
            repeated_patterns = list(snapshot.get('repeated_patterns', []))
            learning_signals = list(snapshot.get('learning_signals', []))

            for validation in recent_validations[:3]:
                session_time = str(validation.get('session_time', '') or '')[:19]
                verdict = str(validation.get('verdict', '') or '')
                divergences = list(validation.get('divergences', []))
                items.append({
                    'label': f'Session {session_time}',
                    'value': f'verdict={verdict}, divergences={len(divergences)}',
                    'detail': str(divergences[0][:80]) if divergences else 'No divergences',
                })

            for pattern in repeated_patterns[:3]:
                pattern_name = str(pattern.get('pattern', ''))
                count = pattern.get('occurrence_count', 0)
                items.append({
                    'label': f'Recurring pattern: {pattern_name}',
                    'value': f'{count} occurrences',
                    'detail': f'severity={pattern.get("severity", "")}',
                })

            for signal in learning_signals[:5]:
                items.append({
                    'label': 'Learning signal',
                    'value': signal[:100],
                })

            validation_count = len(recent_validations)
            pattern_count = len(repeated_patterns)
            signal_count = len(learning_signals)
            summary = (
                f'Learning history: {validation_count} validaciones recientes, '
                f'{pattern_count} patrones recurrentes, {signal_count} señales de aprendizaje.'
            )
            confidence = 0.85
        elif st == 'no_history':
            summary = 'Learning history no disponible aún. PortableContext marcará UNRESOLVOLED.'
            confidence = 0.0
            unresolved_fields.append('UNRESOLVED:learning_history_no_data')
        elif st == 'read_error':
            summary = 'Error al leer learning history.'
            confidence = 0.0
            unresolved_fields.append('UNRESOLVED:learning_history_read_error')
        else:
            summary = f'Learning history status: {st}'
            confidence = 0.0

        return self._section(
            section_id='learning_history',
            title='Historial de aprendizaje (teoría vs realidad)',
            summary=summary,
            items=items,
            source_kind='agent_session_gate_cross_oses',
            source_refs=[
                'scripts/devin_session_gate.py',
                'data/evolution/agent_session_gate/latest_post.json',
                'data/evolution/self_examination/latest.json',
            ],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(unresolved_fields)),
            metadata={
                'status': st,
                'recent_validation_count': snapshot.get('recent_theory_validations_count', 0),
                'repeated_pattern_count': snapshot.get('repeated_pattern_count', 0),
                'learning_signal_count': snapshot.get('learning_signal_count', 0),
            },
        )

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
        world_source = str((world.metadata or {}).get('portable_context_source') or '')
        environment_source = str((environment.metadata or {}).get('portable_context_source') or '')
        if has_world_model:
            if world_source.startswith('persisted_'):
                persisted.append('world_model_latest')
            else:
                live.append('world_model')
        if has_environment:
            if environment_source.startswith('persisted_'):
                persisted.append('environment_self_model_latest')
            else:
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

    def _operational_budget_learning_snapshot(self) -> dict[str, Any]:
        repo = self.experiment_lab_repository
        if repo is None or not hasattr(repo, 'list_runs'):
            return {'status': 'not_configured', 'total_runs': 0, 'items': []}
        try:
            runs = list(repo.list_runs(domain='algorithm', limit=80))
        except Exception:
            return {'status': 'error', 'total_runs': 0, 'items': []}
        budget_runs = [
            run for run in runs
            if str(getattr(run, 'suite_name', '') or '') == 'operational_budget'
            or str(dict(getattr(run, 'metadata', {}) or {}).get('suite_name') or '') == 'operational_budget'
        ]
        by_decision: dict[str, int] = {}
        by_reason: dict[str, int] = {}
        by_work_class: dict[str, int] = {}
        items: list[dict[str, Any]] = []
        for run in budget_runs[:8]:
            metadata = dict(getattr(run, 'metadata', {}) or {})
            decision = str(metadata.get('budget_decision') or '')
            reason = str(metadata.get('budget_reason') or '')
            work_class = str(metadata.get('work_class') or '')
            by_decision[decision or 'unknown'] = by_decision.get(decision or 'unknown', 0) + 1
            by_reason[reason or 'unknown'] = by_reason.get(reason or 'unknown', 0) + 1
            by_work_class[work_class or 'unknown'] = by_work_class.get(work_class or 'unknown', 0) + 1
            items.append({
                'run_id': getattr(run, 'run_id', ''),
                'decision': decision,
                'reason': reason,
                'work_class': work_class,
                'source': str(metadata.get('source') or ''),
                'score': float(getattr(getattr(run, 'metrics', None), 'total_score', 0.0) or 0.0),
                'observed_summary': str(getattr(run, 'observed_summary', '') or ''),
                'created_at_utc': getattr(run, 'created_at_utc', utc_now()).isoformat(),
            })
        return {
            'status': 'active' if budget_runs else 'empty',
            'total_runs': len(budget_runs),
            'by_decision': by_decision,
            'by_reason': by_reason,
            'by_work_class': by_work_class,
            'items': items,
            'calibration': summarize_operational_budget_calibration(budget_runs),
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
            try:
                status = service.current_status(refresh=False, max_age_seconds=900)
            except TypeError:
                status = service.current_status(refresh=False)
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
        for directive in self._recent_operational_directives_from_backlog(limit=6):
            label = str(directive.get('label') or '').strip()
            hint = str(directive.get('research_hint') or '').strip()
            matched = str(directive.get('matched_text') or '').strip()
            if not label:
                continue
            detail = hint or 'Directiva operativa pendiente de validar por los ciclos existentes.'
            if matched:
                detail = f'{detail} Evidencia de chat: "{matched}".'
            items.append(
                {
                    'label': str(directive.get('kind') or 'operational_directive'),
                    'detail': detail,
                    'source': 'chat_research_backlog',
                    'detected_at_utc': str(directive.get('detected_at_utc') or ''),
                }
            )
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

    def _recent_operational_directives_from_backlog(self, *, limit: int = 6) -> list[dict[str, Any]]:
        backlog_dir = Path(self.workspace_root) / 'data' / 'chat_research_backlog'
        if not backlog_dir.exists() or not backlog_dir.is_dir():
            return []
        collected: list[dict[str, Any]] = []
        try:
            files = sorted(backlog_dir.glob('*.jsonl'))
        except OSError:
            return []
        for path in files:
            try:
                with path.open('r', encoding='utf-8') as handle:
                    for line in handle:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        try:
                            payload = json.loads(stripped)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(payload, dict):
                            continue
                        kind = str(payload.get('kind') or '').strip()
                        if not kind.startswith('operational_'):
                            continue
                        if str(payload.get('status') or 'open').lower() not in {'open', 'in_progress'}:
                            continue
                        collected.append(payload)
            except OSError:
                continue
        collected.sort(key=lambda item: str(item.get('detected_at_utc') or ''), reverse=True)
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in collected:
            kind = str(item.get('kind') or '').strip()
            if not kind or kind in seen:
                continue
            seen.add(kind)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

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

    def _operational_budget_learning_section(
        self,
        *,
        snapshot: dict[str, Any],
        now,
    ) -> PortableContextSection:
        items: list[dict[str, Any]] = []
        for item in list(snapshot.get('items') or [])[:6]:
            items.append({
                'label': f"{item.get('work_class') or 'unknown'}:{item.get('decision') or 'unknown'}",
                'detail': (
                    f"reason={item.get('reason') or 'unknown'} | "
                    f"source={item.get('source') or 'unknown'} | "
                    f"score={float(item.get('score') or 0.0):.2f}"
                ),
                'observed_summary': str(item.get('observed_summary') or ''),
            })
        calibration = dict(snapshot.get('calibration') or {})
        if calibration:
            items.append({
                'label': f"calibration:{calibration.get('status') or 'unknown'}",
                'detail': (
                    f"samples={int(calibration.get('sample_count') or 0)}/"
                    f"{int(calibration.get('minimum_sample') or 0)} | "
                    f"recommendation={calibration.get('recommendation') or 'n/d'}"
                ),
                'observed_summary': 'Calibracion derivada desde ExperimentLab; no aplica umbrales sin ruta gobernada.',
            })
        total = int(snapshot.get('total_runs') or 0)
        summary = (
            f'{total} decisiones de presupuesto operativo registradas en ExperimentLab.'
            if total else
            'Sin decisiones de presupuesto operativo persistidas aun.'
        )
        if calibration:
            summary += f" Calibracion: {calibration.get('status') or 'unknown'}."
        return self._section(
            section_id='operational_budget_learning',
            title='Aprendizaje del presupuesto operativo',
            summary=summary,
            items=items,
            source_kind='persistent_learning',
            source_refs=['AutonomyGovernancePolicy', 'ExperimentLab', 'OSES'],
            confidence=0.84 if items else 0.2,
            last_updated=now,
            unresolved_fields=[] if items else ['UNRESOLVED:operational_budget_learning'],
            metadata=snapshot,
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
                'external_coordination_readiness': dict(summary_payload.get('external_coordination_readiness') or {}),
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

    def _runtime_stability_section(self, *, now) -> PortableContextSection:
        """P0.130: Export runtime stability nervous system section."""
        try:
            from iabv_v15.services.evolution.runtime_organ_state import (
                build_runtime_stability_dossier,
                load_runtime_organ_snapshot,
            )

            dossier = build_runtime_stability_dossier(self.workspace_root)
            organs_snapshot = load_runtime_organ_snapshot(self.workspace_root)

            # Build compact items
            items: list[dict[str, Any]] = []

            # Total stalls summary
            if dossier.get("total_stalls", 0) > 0:
                items.append({
                    'label': 'Total stalls',
                    'summary': f'{dossier["total_stalls"]} stalls, max {dossier["max_stall_ms"]:.0f}ms',
                    'severity': 'HIGH' if dossier["total_stalls"] >= 5 else 'MEDIUM',
                    'confidence': 0.85,
                    'source_refs': ['runtime_audit.jsonl', 'build_runtime_stability_dossier'],
                })

            # Suspected organs
            if dossier.get("suspected_organs"):
                items.append({
                    'label': 'Órganos sospechosos',
                    'summary': ', '.join(set(dossier["suspected_organs"])),
                    'severity': 'HIGH',
                    'confidence': 0.75,
                    'source_refs': ['runtime_organs/latest.json', 'build_runtime_stability_dossier'],
                })

            # Active heavy organs
            if dossier.get("active_heavy_organs"):
                items.append({
                    'label': 'Órganos heavy activos',
                    'summary': ', '.join(dossier["active_heavy_organs"]),
                    'severity': 'MEDIUM',
                    'confidence': 0.80,
                    'source_refs': ['runtime_organs/latest.json'],
                })

            # Degraded organs
            degraded = [o.get("organ_id") for o in organs_snapshot.get("organs", []) if o.get("mode") in {"throttled", "on_demand", "disabled"}]
            if degraded:
                items.append({
                    'label': 'Órganos degradados',
                    'summary': ', '.join(degraded),
                    'severity': 'LOW',
                    'confidence': 0.90,
                    'source_refs': ['runtime_organs/latest.json'],
                })

            summary = (
                f'Sistema de estabilidad runtime: {dossier["total_stalls"]} stalls, '
                f'{len(dossier.get("suspected_organs", []))} órganos sospechosos, '
                f'{len(dossier.get("active_heavy_organs", []))} heavy activos.'
            )

            return self._section(
                section_id='runtime_stability_nervous_system',
                title='Sistema de Estabilidad Runtime',
                summary=summary,
                items=items[:5],  # Top 5 items
                source_kind='derived_dossier',
                source_refs=['runtime_audit.jsonl', 'runtime_organs/latest.json', 'build_runtime_stability_dossier'],
                confidence=0.80,
                last_updated=now,
                unresolved_fields=dossier.get("unresolved_fields", []),
                metadata={
                    'total_stalls': dossier.get("total_stalls"),
                    'max_stall_ms': dossier.get("max_stall_ms"),
                    'suspected_organs': dossier.get("suspected_organs", []),
                    'active_heavy_organs': dossier.get("active_heavy_organs", []),
                    'next_recommendation': dossier.get("next_recommendation", ""),
                },
            )
        except Exception as exc:
            logger.debug(f"PortableContext runtime stability section failed: {exc}")
            return self._section(
                section_id='runtime_stability_nervous_system',
                title='Sistema de Estabilidad Runtime',
                summary='UNRESOLVED: runtime_stability_nervous_system',
                items=[],
                source_kind='derived_dossier',
                source_refs=['runtime_audit.jsonl', 'runtime_organs/latest.json'],
                confidence=0.0,
                last_updated=now,
                unresolved_fields=['UNRESOLVED:runtime_stability_nervous_system'],
                metadata={},
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

    def _worker_timeout_snapshot(self, *, limit: int = 80) -> dict[str, Any]:
        """Summarize recent worker timeout/progress events from runtime_audit."""
        audit_path = Path(self.workspace_root) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return {
                'status': 'no_runtime_audit',
                'recent_worker_timeouts': [],
                'event_counts': {},
                'unresolved_fields': ['UNRESOLVED:worker_timeout_audit_missing'],
            }
        events: list[dict[str, Any]] = []
        try:
            for line in audit_path.read_text(encoding='utf-8', errors='replace').splitlines()[-limit:]:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if str(event.get('kind') or '').startswith('worker_'):
                    events.append(event)
        except OSError as exc:
            return {
                'status': 'error',
                'reason': str(exc),
                'recent_worker_timeouts': [],
                'event_counts': {},
                'unresolved_fields': ['UNRESOLVED:worker_timeout_audit_read_failed'],
            }
        counts: dict[str, int] = {}
        recent_terminal: list[dict[str, Any]] = []
        recovery_attempted = False
        recovery_result = ''
        unresolved_fields: list[str] = []
        for event in events:
            kind = str(event.get('kind') or '')
            counts[kind] = counts.get(kind, 0) + 1
            data = dict(event.get('data') or {})
            if kind == 'worker_recovery_attempted':
                recovery_attempted = True
            if kind == 'worker_recovery_result':
                recovery_result = str(data.get('result') or recovery_result)
            if kind == 'worker_timeout_terminal':
                recent_terminal.append({
                    'task_name': data.get('task_name', ''),
                    'dispatch_id': str(data.get('dispatch_id') or '')[:12],
                    'interaction_id': str(data.get('interaction_id') or '')[:12],
                    'terminal_state': data.get('terminal_state', ''),
                    'waiting_on': data.get('waiting_on', ''),
                    'elapsed_s': data.get('elapsed_s', 0),
                })
        if counts.get('worker_no_progress_detected', 0):
            unresolved_fields.append('UNRESOLVED:worker_no_progress_detected')
        if any(item.get('terminal_state') == 'blocked_no_progress' for item in recent_terminal):
            unresolved_fields.append('UNRESOLVED:external_consultation_blocked_no_progress')
        if counts.get('worker_recovery_result', 0) and recovery_result == 'failed':
            unresolved_fields.append('UNRESOLVED:worker_timeout_recovery_failed')
        status = 'observed' if events else 'no_worker_timeout_events'
        return {
            'status': status,
            'event_counts': counts,
            'recent_worker_timeouts': recent_terminal[-5:],
            'last_timeout_task': (recent_terminal[-1].get('task_name') if recent_terminal else ''),
            'last_timeout_phase': (recent_terminal[-1].get('waiting_on') if recent_terminal else ''),
            'recovery_attempted': recovery_attempted,
            'recovery_result': recovery_result,
            'unresolved_fields': unresolved_fields,
        }

    def _worker_timeout_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        recent = list(snapshot.get('recent_worker_timeouts') or [])
        counts = dict(snapshot.get('event_counts') or {})
        if recent:
            summary = f'{len(recent)} timeout(s) terminales recientes; eventos={counts}.'
        elif counts:
            summary = f'Eventos de progreso/timeout observados sin terminal reciente; eventos={counts}.'
        else:
            summary = 'Sin eventos recientes de timeout de worker.'
        return self._section(
            section_id='worker_timeout_summary',
            title='Resumen de timeouts y recuperacion de workers',
            summary=summary,
            items=recent,
            source_kind='runtime_audit_jsonl',
            source_refs=['data/logs/runtime_audit.jsonl'],
            confidence=0.86 if counts else 0.0,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata=snapshot,
        )

    def _visual_target_binding_snapshot(self, *, limit: int = 30) -> dict[str, Any]:
        audit_path = Path(self.workspace_root) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return {
                'status': 'no_runtime_audit',
                'recent_binding_statuses': {},
                'recent_concepts': [],
                'unresolved_fields': ['UNRESOLVED:visual_target_binding_audit_missing'],
            }
        events: list[dict[str, Any]] = []
        try:
            lines = audit_path.read_text(encoding='utf-8', errors='replace').splitlines()[-400:]
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                kind = str(event.get('kind') or '')
                if kind in {
                    'visual_target_binding_result',
                    'visual_concept_read_result',
                    'visual_capability_calibration_result',
                    'human_visual_help_requested',
                    'visual_self_capture_prevented',
                    'external_consultation_audit_visual_context_reported',
                }:
                    events.append(event)
                if len(events) >= limit:
                    break
        except OSError:
            return {
                'status': 'unreadable',
                'recent_binding_statuses': {},
                'recent_concepts': [],
                'unresolved_fields': ['UNRESOLVED:visual_target_binding_audit_unreadable'],
            }
        events.reverse()
        statuses: Counter[str] = Counter()
        concepts: list[str] = []
        latest_binding: dict[str, Any] = {}
        latest_calibration: dict[str, Any] = {}
        latest_help: dict[str, Any] = {}
        latest_metavision: dict[str, Any] = {}
        latest_web_surface: dict[str, Any] = {}
        latest_alignment_handoff: dict[str, Any] = {}
        unresolved: list[str] = []
        for event in events:
            kind = str(event.get('kind') or '')
            data = dict(event.get('data') or {})
            if kind == 'visual_target_binding_result':
                status = str(data.get('binding_status') or data.get('status') or '').strip()
                if status:
                    statuses[status] += 1
                latest_binding = {
                    'assistant_kind': str(data.get('assistant_kind') or data.get('requested_assistant_kind') or '')[:40],
                    'binding_status': status,
                    'confidence': data.get('confidence', 0.0),
                    'candidate_count': len(data.get('candidate_windows') or []),
                    'selected_title': str((data.get('selected_window') or {}).get('title') or '')[:120]
                    if isinstance(data.get('selected_window'), dict)
                    else '',
                    'next_human_action': str(data.get('next_human_action') or '')[:180],
                }
            elif kind == 'visual_concept_read_result':
                for label in list(data.get('labels') or [])[:8]:
                    if str(label):
                        concepts.append(str(label)[:80])
                for label in list(data.get('metavision_concepts') or [])[:8]:
                    if str(label):
                        concepts.append(str(label)[:80])
                if data.get('metavision_status') or data.get('metavision_concepts') or data.get('metavision_affordances'):
                    latest_metavision = {
                        'status': str(data.get('metavision_status') or '')[:60],
                        'confidence': data.get('metavision_confidence', 0.0),
                        'concepts': [str(item)[:80] for item in list(data.get('metavision_concepts') or [])[:8] if str(item)],
                        'affordances': [str(item)[:80] for item in list(data.get('metavision_affordances') or [])[:8] if str(item)],
                        'missing_sources': [str(item)[:60] for item in list(data.get('metavision_missing_sources') or [])[:8] if str(item)],
                        'next_action': str(data.get('metavision_next_action') or '')[:180],
                    }
                if data.get('web_surface_status') or data.get('web_surface_readiness') or data.get('web_surface_controls'):
                    latest_web_surface = {
                        'status': str(data.get('web_surface_status') or '')[:60],
                        'readiness': str(data.get('web_surface_readiness') or '')[:80],
                        'concepts': [str(item)[:80] for item in list(data.get('web_surface_concepts') or [])[:8] if str(item)],
                        'controls': [str(item)[:80] for item in list(data.get('web_surface_controls') or [])[:8] if str(item)],
                        'next_action': str(data.get('web_surface_next_action') or '')[:180],
                    }
                for field in list(data.get('unresolved_fields') or [])[:6]:
                    if str(field):
                        unresolved.append(str(field)[:120])
            elif kind == 'visual_capability_calibration_result':
                latest_calibration = {
                    'assistant_kind': str(data.get('assistant_kind') or '')[:40],
                    'status': str(data.get('status') or '')[:60],
                    'target_binding_status': str(data.get('target_binding_status') or '')[:60],
                    'window_count': int(data.get('window_count') or 0),
                    'selected_window_title': str(data.get('selected_window_title') or '')[:120],
                    'semantic_reader_available': bool(data.get('semantic_reader_available')),
                    'ocr_status': str(data.get('ocr_status') or '')[:60],
                    'capability_score': data.get('capability_score', 0.0),
                }
                for field in list(data.get('unresolved_fields') or [])[:6]:
                    if str(field):
                        unresolved.append(str(field)[:120])
            elif kind == 'human_visual_help_requested':
                latest_help = {
                    'assistant_kind': str(data.get('assistant_kind') or '')[:40],
                    'binding_status': str(data.get('binding_status') or '')[:40],
                    'next_human_action': str(data.get('next_human_action') or '')[:180],
                }
            elif kind == 'external_consultation_audit_visual_context_reported':
                latest_alignment_handoff = {
                    'interaction_id': str(data.get('interaction_id') or '')[:80],
                    'provider': str(data.get('provider') or '')[:80],
                    'final': str(data.get('final') or '')[:60],
                    'calibration_status': str(data.get('calibration_status') or '')[:60],
                    'binding_status': str(data.get('binding_status') or '')[:60],
                    'unresolved_fields': [str(item)[:120] for item in list(data.get('unresolved_fields') or [])[:6] if str(item)],
                }
        return {
            'status': 'analyzed' if events else 'no_visual_events',
            'recent_binding_statuses': dict(statuses),
            'latest_binding': latest_binding,
            'latest_calibration': latest_calibration,
            'latest_help_request': latest_help,
            'latest_metavision': latest_metavision,
            'latest_web_surface': latest_web_surface,
            'latest_alignment_handoff': latest_alignment_handoff,
            'recent_concepts': list(dict.fromkeys(concepts))[:12],
            'unresolved_fields': list(dict.fromkeys(unresolved))[:12],
            'events_analyzed': len(events),
        }

    def _visual_target_binding_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        status = str(snapshot.get('status') or 'unknown')
        latest = dict(snapshot.get('latest_binding') or {})
        items: list[dict[str, Any]] = []
        if latest:
            items.append({
                'label': 'latest_binding',
                'assistant_kind': latest.get('assistant_kind', ''),
                'binding_status': latest.get('binding_status', ''),
                'confidence': latest.get('confidence', 0.0),
                'candidate_count': latest.get('candidate_count', 0),
                'selected_title': latest.get('selected_title', ''),
                'next_human_action': latest.get('next_human_action', ''),
            })
        calibration = dict(snapshot.get('latest_calibration') or {})
        if calibration:
            items.append({
                'label': 'latest_visual_calibration',
                'assistant_kind': calibration.get('assistant_kind', ''),
                'status': calibration.get('status', ''),
                'target_binding_status': calibration.get('target_binding_status', ''),
                'window_count': calibration.get('window_count', 0),
                'semantic_reader_available': calibration.get('semantic_reader_available', False),
                'ocr_status': calibration.get('ocr_status', ''),
                'capability_score': calibration.get('capability_score', 0.0),
            })
        for label in list(snapshot.get('recent_concepts') or [])[:8]:
            items.append({'label': 'visual_concept', 'value': str(label)})
        metavision = dict(snapshot.get('latest_metavision') or {})
        if metavision:
            items.append({
                'label': 'latest_metavision',
                'status': metavision.get('status', ''),
                'confidence': metavision.get('confidence', 0.0),
                'concepts': list(metavision.get('concepts') or [])[:6],
                'affordances': list(metavision.get('affordances') or [])[:6],
                'missing_sources': list(metavision.get('missing_sources') or [])[:6],
                'next_action': metavision.get('next_action', ''),
            })
        web_surface = dict(snapshot.get('latest_web_surface') or {})
        if web_surface:
            items.append({
                'label': 'latest_web_surface',
                'status': web_surface.get('status', ''),
                'readiness': web_surface.get('readiness', ''),
                'concepts': list(web_surface.get('concepts') or [])[:6],
                'controls': list(web_surface.get('controls') or [])[:6],
                'next_action': web_surface.get('next_action', ''),
            })
        alignment = dict(snapshot.get('latest_alignment_handoff') or {})
        if alignment:
            items.append({
                'label': 'latest_human_machine_alignment_handoff',
                'provider': alignment.get('provider', ''),
                'final': alignment.get('final', ''),
                'calibration_status': alignment.get('calibration_status', ''),
                'binding_status': alignment.get('binding_status', ''),
                'unresolved_fields': list(alignment.get('unresolved_fields') or [])[:6],
            })
        if status == 'analyzed':
            summary = (
                'Visual target binding activo: '
                f'estados recientes={snapshot.get("recent_binding_statuses", {})}.'
            )
        elif status == 'no_visual_events':
            summary = 'Sin eventos recientes de binding visual.'
        else:
            summary = 'Binding visual sin evidencia durable reciente.'
        return self._section(
            section_id='visual_target_binding',
            title='Binding visual y conceptos universales',
            summary=summary,
            items=items,
            source_kind='runtime_audit_jsonl',
            source_refs=['data/logs/runtime_audit.jsonl', 'UniversalPerceptionService', 'WorldModelService'],
            confidence=0.85 if status == 'analyzed' else 0.0,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata=snapshot,
        )

    def _formal_semantic_reasoning_snapshot(self) -> dict[str, Any]:
        try:
            from iabv_v15.services.evolution.formal_semantic_reasoning_probe import (
                FormalSemanticReasoningProbe,
                load_runtime_audit_events,
            )
        except Exception:
            return {
                'status': 'unavailable',
                'score': 0.0,
                'metrics': {},
                'findings': [],
                'unresolved_fields': ['UNRESOLVED:formal_semantic_reasoning_probe_import'],
            }

        events = load_runtime_audit_events(self.workspace_root, limit=900)
        decisions: list[dict[str, Any]] = []
        audit = getattr(self, 'decision_audit_trail', None)
        if audit is not None and hasattr(audit, 'load_recent'):
            try:
                decisions = list(audit.load_recent(180) or [])
            except Exception:
                decisions = []
        probe = FormalSemanticReasoningProbe()
        result = probe.evaluate(events=events, decisions=decisions)
        benchmark = probe.benchmark_candidates(events=events, decisions=decisions)
        return {
            **result,
            'benchmark': benchmark,
        }

    def _formal_semantic_reasoning_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        metrics = dict(snapshot.get('metrics') or {})
        findings = list(snapshot.get('findings') or [])
        items = [
            {'label': 'score', 'value': snapshot.get('score', 0.0)},
            {'label': 'external_blocks', 'value': metrics.get('external_block_count', 0)},
            {'label': 'deictic_followups', 'value': metrics.get('deictic_followup_count', 0)},
            {'label': 'local_misroutes', 'value': metrics.get('local_misroute_after_external_block', 0)},
            {'label': 'visual_binding_failures', 'value': metrics.get('visual_binding_failure_count', 0)},
        ]
        benchmark = dict(snapshot.get('benchmark') or {})
        winner = dict(benchmark.get('winner') or {})
        if winner:
            items.append({
                'label': 'symbolic_logic_winner',
                'value': str(winner.get('candidate_id') or ''),
                'score': float(winner.get('score') or 0.0),
                'robustness': float(winner.get('robustness') or 0.0),
            })
        for finding in findings[:4]:
            if isinstance(finding, dict):
                items.append({
                    'label': 'formal_semantic_gap',
                    'kind': str(finding.get('kind') or ''),
                    'count': finding.get('count', ''),
                    'detail': str(finding.get('user_reference_text') or '')[:160],
                })
        status = str(snapshot.get('status') or 'unknown')
        if status == 'pass':
            summary = 'Probe formal-semantico sin gaps recientes de referencia, verdad y grounding.'
        elif status == 'needs_attention':
            summary = (
                'Probe formal-semantico detecto gaps: '
                f"score={float(snapshot.get('score') or 0.0):.2f}, "
                f"{len(findings)} hallazgo(s)."
            )
        elif status == 'no_data':
            summary = 'Sin evidencia suficiente para medir razonamiento formal-semantico.'
        else:
            summary = f'Probe formal-semantico en estado {status}.'
        return self._section(
            section_id='formal_semantic_reasoning',
            title='Razonamiento formal, referencia y grounding',
            summary=summary,
            items=items,
            source_kind='runtime_audit_and_decision_audit',
            source_refs=['data/logs/runtime_audit.jsonl', 'DecisionAuditTrail', 'ExperimentLab'],
            confidence=0.82 if status in {'pass', 'needs_attention'} else 0.0,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata=snapshot,
        )

    def _concept_weight_evidence_snapshot(self, *, limit: int = 40) -> dict[str, Any]:
        path = Path(self.workspace_root) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not path.exists():
            return {
                'status': 'no_runtime_audit',
                'events_analyzed': 0,
                'latest': {},
                'concept_counts': {},
                'unresolved_fields': ['UNRESOLVED:concept_weight_runtime_audit_missing'],
            }
        events: list[dict[str, Any]] = []
        try:
            for line in reversed(path.read_text(encoding='utf-8', errors='replace').splitlines()[-500:]):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if str(event.get('kind') or '') == 'visual_concept_read_result':
                    events.append(dict(event.get('data') or {}))
                if len(events) >= limit:
                    break
        except OSError:
            return {
                'status': 'unreadable',
                'events_analyzed': 0,
                'latest': {},
                'concept_counts': {},
                'unresolved_fields': ['UNRESOLVED:concept_weight_runtime_audit_unreadable'],
            }
        events.reverse()
        concept_counts: Counter[str] = Counter()
        contradiction_count = 0
        missing_evidence = 0
        latest: dict[str, Any] = {}
        for data in events:
            concepts = [str(item) for item in list(data.get('concept_weight_concepts') or []) if str(item)]
            if not concepts and not data.get('concept_weight_status'):
                missing_evidence += 1
            for concept in concepts:
                concept_counts[concept] += 1
            contradiction_count += int(data.get('concept_weight_contradiction_count') or 0)
            if data.get('concept_weight_status') or concepts:
                latest = {
                    'status': str(data.get('concept_weight_status') or ''),
                    'confidence': float(data.get('concept_weight_confidence') or 0.0),
                    'concepts': concepts[:8],
                    'sources': list(data.get('concept_weight_sources') or [])[:8],
                    'missing_sources': list(data.get('concept_weight_missing_sources') or [])[:8],
                    'contradiction_count': int(data.get('concept_weight_contradiction_count') or 0),
                    'next_action': str(data.get('concept_weight_next_action') or '')[:220],
                }
        status = 'analyzed' if events else 'no_concept_events'
        unresolved: list[str] = []
        if events and missing_evidence:
            unresolved.append('UNRESOLVED:concept_weight_evidence_missing_in_some_visual_events')
        if contradiction_count:
            unresolved.append('UNRESOLVED:concept_weight_contradictions_present')
        return {
            'status': status,
            'events_analyzed': len(events),
            'latest': latest,
            'concept_counts': dict(concept_counts.most_common(12)),
            'contradiction_count': contradiction_count,
            'missing_evidence_count': missing_evidence,
            'unresolved_fields': unresolved,
        }

    def _concept_weight_evidence_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        latest = dict(snapshot.get('latest') or {})
        items: list[dict[str, Any]] = []
        if latest:
            items.append({
                'label': 'latest_concept_weight_evidence',
                'status': latest.get('status', ''),
                'confidence': latest.get('confidence', 0.0),
                'concepts': list(latest.get('concepts') or [])[:8],
                'sources': list(latest.get('sources') or [])[:8],
                'missing_sources': list(latest.get('missing_sources') or [])[:8],
                'contradiction_count': latest.get('contradiction_count', 0),
                'next_action': latest.get('next_action', ''),
            })
        for concept, count in list(dict(snapshot.get('concept_counts') or {}).items())[:8]:
            items.append({'label': 'concept_activation', 'concept': concept, 'count': count})
        status = str(snapshot.get('status') or 'unknown')
        if status == 'analyzed':
            summary = (
                f"ConceptWeightEvidence analizo {snapshot.get('events_analyzed', 0)} evento(s); "
                f"contradicciones={snapshot.get('contradiction_count', 0)}."
            )
        elif status == 'no_concept_events':
            summary = 'Sin eventos recientes con evidencia de pesos conceptuales.'
        else:
            summary = 'Evidencia de pesos conceptuales no disponible.'
        return self._section(
            section_id='concept_weight_evidence',
            title='Activacion conceptual comun',
            summary=summary,
            items=items,
            source_kind='runtime_audit_jsonl',
            source_refs=['data/logs/runtime_audit.jsonl', 'concept_weight_evidence', 'UniversalPerceptionService'],
            confidence=0.82 if status == 'analyzed' else 0.0,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata=snapshot,
        )

    def _algorithm_fitness_snapshot(self) -> dict[str, Any]:
        """Build compact algorithm fitness inventory from source.

        This is read-only and intentionally compact.  It makes the algorithm
        governance contract visible to the next session without turning
        PortableContext into a new analyzer or route decider.
        """
        try:
            from iabv_v15.services.evolution.algorithm_fitness_contract import (
                build_algorithm_observation_matrix,
            )
            matrix = build_algorithm_observation_matrix(
                workspace_root=self.workspace_root,
                src_dir=str(Path(self.workspace_root) / 'src'),
            )
        except Exception as exc:
            return {
                'status': 'error',
                'error': str(exc)[:200],
                'unresolved_fields': ['UNRESOLVED:algorithm_fitness_snapshot_failed'],
            }

        if matrix.get('error'):
            return {
                'status': 'unavailable',
                'error': matrix.get('error'),
                'unresolved_fields': ['UNRESOLVED:algorithm_fitness_source_missing'],
            }

        algorithms = list(matrix.get('algorithms') or [])
        high_complexity = sorted(
            algorithms,
            key=lambda item: int(item.get('complexity') or 0),
            reverse=True,
        )[:8]
        unknown = [
            item for item in algorithms
            if item.get('capability_area') == 'unknown'
        ][:8]
        without_public_calls = [
            item for item in algorithms
            if not item.get('runtime_call_sites')
        ][:8]
        unresolved: list[str] = []
        if unknown:
            unresolved.append('UNRESOLVED:algorithm_capability_unknown')
        if without_public_calls:
            unresolved.append('UNRESOLVED:algorithm_runtime_call_sites_missing')

        return {
            'status': 'observed',
            'total_algorithms': matrix.get('total_algorithms', 0),
            'by_capability_area': matrix.get('by_capability_area', {}),
            'high_complexity': [
                {
                    'algorithm_id': item.get('algorithm_id'),
                    'module_path': item.get('module_path'),
                    'capability_area': item.get('capability_area'),
                    'complexity': item.get('complexity'),
                }
                for item in high_complexity
            ],
            'unknown_capability': [
                {
                    'algorithm_id': item.get('algorithm_id'),
                    'module_path': item.get('module_path'),
                }
                for item in unknown
            ],
            'without_public_call_sites': [
                {
                    'algorithm_id': item.get('algorithm_id'),
                    'module_path': item.get('module_path'),
                }
                for item in without_public_calls
            ],
            'unresolved_fields': unresolved,
        }

    def _algorithm_fitness_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        status = str(snapshot.get('status') or 'unknown')
        total = int(snapshot.get('total_algorithms', 0) or 0)
        by_area = snapshot.get('by_capability_area') or {}
        if status == 'observed':
            summary = (
                f'{total} algoritmos/modulos observados; '
                f'{len(by_area)} areas de capacidad; '
                f'{len(snapshot.get("high_complexity") or [])} candidatos de alta complejidad.'
            )
        else:
            summary = f'Algorithm fitness no disponible: {snapshot.get("error", status)}'
        return self._section(
            section_id='algorithm_fitness',
            title='Fitness de algoritmos y organos',
            summary=summary,
            items=[
                {'label': 'capability_area_counts', 'value': by_area},
                {'label': 'high_complexity', 'items': snapshot.get('high_complexity') or []},
                {'label': 'unknown_capability', 'items': snapshot.get('unknown_capability') or []},
                {'label': 'without_public_call_sites', 'items': snapshot.get('without_public_call_sites') or []},
            ],
            source_kind='source_inventory',
            source_refs=[
                'algorithm_fitness_contract.build_algorithm_observation_matrix',
                'src/iabv_v15',
            ],
            confidence=0.72 if status == 'observed' else 0.25,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata={'status': status, 'total_algorithms': total},
        )

    def _runtime_organ_matrix_snapshot(self) -> dict[str, Any]:
        try:
            from iabv_v15.services.evolution.runtime_organ_state import load_runtime_organ_snapshot
            return load_runtime_organ_snapshot(self.workspace_root)
        except Exception as exc:
            return {'status': 'unavailable', 'organ_count': 0, 'organs': [], 'error': str(exc)}

    def _runtime_organ_matrix_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        organs = list(snapshot.get('organs') or [])
        try:
            from iabv_v15.services.evolution.algorithm_fitness_contract import (
                evaluate_runtime_organ_fitness,
            )
            fitness = evaluate_runtime_organ_fitness(runtime_organ_snapshot=snapshot)
        except Exception as exc:
            fitness = {'status': 'unavailable', 'error': str(exc), 'organ_scores': []}
        heavy_active = [
            item for item in organs
            if item.get('cost_class') == 'heavy' and item.get('mode') == 'active'
        ]
        throttled = [item for item in organs if item.get('mode') == 'throttled']
        items = [
            {
                'label': str(item.get('organ_id') or 'unknown'),
                'mode': str(item.get('mode') or ''),
                'cost_class': str(item.get('cost_class') or ''),
                'can_run_now': bool(item.get('can_run_now')),
                'detail': str(item.get('human_visible_reason') or '')[:240],
                'blocked_reason': str(item.get('last_blocked_reason') or '')[:160],
            }
            for item in organs[:12]
        ]
        return self._section(
            section_id='runtime_organ_matrix',
            title='Matriz de organos runtime',
            summary=(
                f"{len(organs)} organos observados; "
                f"{len(heavy_active)} pesados activos; {len(throttled)} throttled/on-demand."
            ),
            items=items,
            source_kind='runtime',
            source_refs=['data/evolution/runtime_organs/latest.json'],
            confidence=0.8 if organs else 0.25,
            last_updated=now,
            unresolved_fields=[] if organs else ['UNRESOLVED:runtime_organ_matrix_missing'],
            metadata={
                'status': snapshot.get('status', 'unknown'),
                'active_heavy_count': len(heavy_active),
                'throttled_count': len(throttled),
                'average_fitness_score': fitness.get('average_fitness_score', 0.0),
                'degraded_count': fitness.get('degraded_count', 0),
            },
        )

    def _artifact_lifecycle_snapshot(self) -> dict[str, Any]:
        """P0.134/P0.136: Read artifact lifecycle inventory from latest.json."""
        try:
            inventory_path = Path(self.workspace_root) / 'data' / 'evolution' / 'artifact_lifecycle' / 'latest.json'
            if not inventory_path.exists():
                return {
                    'status': 'missing',
                    'error': 'artifact_lifecycle_inventory_not_found',
                    'unresolved_fields': ['UNRESOLVED:artifact_lifecycle_inventory_missing'],
                }
            
            with open(inventory_path, 'r', encoding='utf-8') as f:
                inventory = json.load(f)
            
            return {
                'status': 'observed',
                'scanned_at': inventory.get('scanned_at'),
                'total_size_mb': inventory.get('total_scanned_size_bytes', 0) / 1024 / 1024,
                'total_files': inventory.get('total_file_count', 0),
                'reclaimable_mb': inventory.get('reclaimable_bytes_estimate', 0) / 1024 / 1024,
                'keep_count': inventory.get('keep_count', 0),
                'quarantine_count': inventory.get('quarantine_candidates_count', 0),
                'delete_approval_count': inventory.get('delete_requires_approval_count', 0),
                'unknown_count': inventory.get('unknown_count', 0),
                'duplicate_groups': inventory.get('duplicate_groups', [])[:5],
                'top_heavy_folders': inventory.get('top_heavy_folders', [])[:5],
                'unresolved_fields': inventory.get('unresolved_fields', []),
            }
        except Exception as exc:
            return {
                'status': 'error',
                'error': str(exc)[:200],
                'unresolved_fields': ['UNRESOLVED:artifact_lifecycle_read_failed'],
            }


    def _runtime_learning_closure_snapshot(self, *, limit: int = 80) -> dict[str, Any]:
        """Convert recent runtime observations into learning candidates.

        This does not validate or apply changes.  It only prevents visual and
        communication failures from remaining as loose logs when OSES or
        ExperimentLab are not available in the current process.
        """
        audit_path = Path(self.workspace_root) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return {
                'status': 'no_runtime_audit',
                'events_analyzed': 0,
                'pattern_counts': {},
                'repeated_patterns': [],
                'learning_candidates': [],
                'next_learning_action': 'Ejecutar una interaccion viva para producir runtime_audit antes de inferir aprendizaje.',
                'unresolved_fields': ['UNRESOLVED:runtime_audit_learning_source'],
            }
        try:
            lines = audit_path.read_text(encoding='utf-8', errors='replace').splitlines()[-800:]
        except OSError:
            return {
                'status': 'unreadable',
                'events_analyzed': 0,
                'pattern_counts': {},
                'repeated_patterns': [],
                'learning_candidates': [],
                'next_learning_action': 'Reparar lectura de runtime_audit antes de inferir aprendizaje.',
                'unresolved_fields': ['UNRESOLVED:runtime_audit_learning_unreadable'],
            }

        events: list[dict[str, Any]] = []
        interesting_kinds = {
            'visual_target_binding_result',
            'visual_concept_read_result',
            'visual_capability_calibration_result',
            'human_visual_help_requested',
            'visual_self_capture_prevented',
            'interaction_resolved',
            'interaction_outcome',
            'dispatch_terminal',
            'external_consultation_audit_visual_context_reported',
        }

        def is_stability_event(kind: str) -> bool:
            normalized = kind.lower().strip()
            stability_kinds = {
                'ui_event_loop_stall',
                'runtime_freeze_incident',
                'freeze_incident',
                'post_load_ui_stall',
                'recent_ui_stall',
                'startup_heavy_work_deferred',
                'post_load_dev_packet_refresh_budget_exceeded',
            }
            return (
                normalized in stability_kinds
                or normalized.endswith('_stall')
                or normalized.endswith('_freeze')
                or normalized.startswith('freeze_')
            )

        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            kind = str(event.get('kind') or '')
            if kind in interesting_kinds or is_stability_event(kind):
                events.append(event)
            if len(events) >= limit:
                break
        events.reverse()

        pattern_counts: Counter[str] = Counter()
        candidates: list[dict[str, Any]] = []
        successful_groundings = 0
        communication_success = 0
        latest_event_kind = ''
        unresolved: list[str] = []

        def add_candidate(kind: str, reason: str, event_kind: str, details: dict[str, Any] | None = None) -> None:
            pattern_counts[kind] += 1
            if len(candidates) >= 10:
                return
            candidates.append({
                'candidate_kind': kind,
                'reason': reason[:180],
                'source_event': event_kind,
                'details': details or {},
                'recommended_sink': 'OSES + ExperimentLab + AdaptiveWeightLayer',
            })

        for event in events:
            kind = str(event.get('kind') or '')
            latest_event_kind = kind or latest_event_kind
            data = dict(event.get('data') or {})
            if kind == 'visual_target_binding_result':
                status = str(data.get('binding_status') or data.get('status') or '').strip()
                if status == 'bound':
                    successful_groundings += 1
                elif status in {'missing', 'ambiguous', 'wrong_surface', 'self_capture'}:
                    add_candidate(
                        'visual_target_binding_gap',
                        f'Binding visual termino en {status}; no debe capturar superficie equivocada.',
                        kind,
                        {
                            'binding_status': status,
                            'assistant_kind': str(data.get('assistant_kind') or data.get('requested_assistant_kind') or '')[:40],
                            'candidate_count': len(data.get('candidate_windows') or []),
                        },
                    )
            elif kind == 'visual_concept_read_result':
                fields = [str(item)[:120] for item in list(data.get('unresolved_fields') or [])[:6] if str(item)]
                missing_sources = [str(item)[:80] for item in list(data.get('metavision_missing_sources') or [])[:6] if str(item)]
                web_readiness = str(data.get('web_surface_readiness') or '')
                if web_readiness in {'target_missing', 'semantic_reader_missing', 'blocked_by_security_verification', 'authentication_required'}:
                    add_candidate(
                        'web_surface_interpretation_gap',
                        f'Web surface readiness={web_readiness}; requiere accion guiada antes de actuar.',
                        kind,
                        {
                            'readiness': web_readiness[:80],
                            'controls': [str(item)[:80] for item in list(data.get('web_surface_controls') or [])[:6] if str(item)],
                            'concepts': [str(item)[:80] for item in list(data.get('web_surface_concepts') or [])[:6] if str(item)],
                        },
                    )
                if fields or missing_sources:
                    add_candidate(
                        'visual_semantic_reader_gap',
                        'La lectura conceptual visual tuvo fuentes faltantes o unresolved_fields.',
                        kind,
                        {
                            'unresolved_fields': fields,
                            'missing_sources': missing_sources,
                            'labels': [str(item)[:80] for item in list(data.get('labels') or [])[:6] if str(item)],
                        },
                    )
                    unresolved.extend(fields)
            elif kind == 'visual_capability_calibration_result':
                status = str(data.get('status') or '')
                if status not in {'ready', 'pass', 'ok'}:
                    add_candidate(
                        'visual_calibration_gap',
                        f'Calibracion visual en estado {status or "unknown"}.',
                        kind,
                        {
                            'target_binding_status': str(data.get('target_binding_status') or '')[:60],
                            'ocr_status': str(data.get('ocr_status') or '')[:60],
                            'capability_score': data.get('capability_score', 0.0),
                        },
                    )
            elif kind == 'human_visual_help_requested':
                add_candidate(
                    'human_visual_help_needed',
                    'El sistema pidio ayuda humana para resolver una referencia visual.',
                    kind,
                    {
                        'assistant_kind': str(data.get('assistant_kind') or '')[:40],
                        'binding_status': str(data.get('binding_status') or '')[:60],
                    },
                )
            elif kind == 'visual_self_capture_prevented':
                add_candidate(
                    'visual_self_capture_prevented',
                    'Se evito capturar IABV/Codex como si fuera la herramienta objetivo.',
                    kind,
                    {},
                )
            elif kind in {'interaction_resolved', 'interaction_outcome'}:
                outcome = str(data.get('outcome') or '')
                if outcome == 'resolved' or bool(data.get('resolved')):
                    communication_success += 1
                elif outcome in {'failed', 'blocked', 'timeout'}:
                    add_candidate(
                        'communication_terminal_gap',
                        f'Interaccion termino en {outcome}; requiere clasificacion causal y estrategia distinta.',
                        kind,
                        {
                            'provider': str(data.get('provider') or '')[:60],
                            'message_preview': str(data.get('message_preview') or '')[:120],
                        },
                    )
            elif kind == 'dispatch_terminal':
                terminal = str(data.get('terminal_state') or data.get('state') or '')
                if terminal and terminal not in {'success', 'response_captured', 'resolved'}:
                    add_candidate(
                        'external_dispatch_terminal_gap',
                        f'Dispatch externo termino en {terminal}.',
                        kind,
                        {
                            'task_name': str(data.get('task_name') or '')[:80],
                            'terminal_state': terminal[:80],
                        },
                    )
            elif kind == 'external_consultation_audit_visual_context_reported':
                unresolved_fields = [str(item)[:120] for item in list(data.get('unresolved_fields') or [])[:6] if str(item)]
                if unresolved_fields:
                    add_candidate(
                        'external_visual_context_gap',
                        'La consulta externa reporto contexto visual sin resolver.',
                        kind,
                        {'unresolved_fields': unresolved_fields},
                    )
                    unresolved.extend(unresolved_fields)
            elif is_stability_event(kind):
                add_candidate(
                    'runtime_stability_gap',
                    f'Evento de estabilidad detectado: {kind}.',
                    kind,
                    {'duration_ms': data.get('duration_ms') or data.get('elapsed_ms')},
                )

        repeated = [
            {
                'pattern': name,
                'count': count,
                'priority': (
                    'critical' if name in {'runtime_stability_gap', 'visual_target_binding_gap'} and count >= 2 else 'high'
                ),
            }
            for name, count in pattern_counts.most_common()
            if count >= 2
        ]
        if repeated:
            status = 'learning_signal_repeated'
            next_action = 'Convertir el patron repetido de mayor prioridad en hallazgo OSES y prueba antes/despues.'
        elif candidates:
            status = 'learning_signal_detected'
            next_action = 'Esperar otra muestra comparable o ejecutar una prueba focalizada antes de ajustar pesos.'
        elif events:
            status = 'observed_no_learning_gap'
            next_action = 'Mantener observacion; no hay patron negativo suficiente para adaptar.'
        else:
            status = 'no_learning_events'
            next_action = 'Generar eventos de runtime con una interaccion viva antes de evaluar aprendizaje.'
            unresolved.append('UNRESOLVED:runtime_learning_events')

        return {
            'status': status,
            'events_analyzed': len(events),
            'pattern_counts': dict(pattern_counts),
            'repeated_patterns': repeated[:8],
            'learning_candidates': candidates[:8],
            'successful_groundings': successful_groundings,
            'communication_success': communication_success,
            'latest_event_kind': latest_event_kind,
            'next_learning_action': next_action,
            'unresolved_fields': list(dict.fromkeys(unresolved))[:12],
        }

    def _runtime_learning_closure_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        status = str(snapshot.get('status') or 'unknown')
        items: list[dict[str, Any]] = []
        for item in list(snapshot.get('repeated_patterns') or [])[:6]:
            items.append({
                'label': 'repeated_pattern',
                'pattern': item.get('pattern', ''),
                'count': item.get('count', 0),
                'priority': item.get('priority', ''),
            })
        for candidate in list(snapshot.get('learning_candidates') or [])[:6]:
            items.append({
                'label': 'learning_candidate',
                'candidate_kind': candidate.get('candidate_kind', ''),
                'reason': candidate.get('reason', ''),
                'source_event': candidate.get('source_event', ''),
                'recommended_sink': candidate.get('recommended_sink', ''),
            })
        if status == 'learning_signal_repeated':
            summary = 'RuntimeAudit contiene patrones repetidos listos para OSES/ExperimentLab.'
            confidence = 0.78
        elif status == 'learning_signal_detected':
            summary = 'RuntimeAudit contiene señales de aprendizaje, pero falta repeticion comparable.'
            confidence = 0.55
        elif status == 'observed_no_learning_gap':
            summary = 'RuntimeAudit fue observado sin gap de aprendizaje claro.'
            confidence = 0.62
        elif status == 'no_learning_events':
            summary = 'Sin eventos recientes para cerrar aprendizaje desde runtime.'
            confidence = 0.0
        else:
            summary = 'Cierre de aprendizaje runtime sin evidencia legible.'
            confidence = 0.0
        return self._section(
            section_id='runtime_learning_closure',
            title='Cierre de aprendizaje desde runtime',
            summary=summary,
            items=items,
            source_kind='runtime_audit_jsonl',
            source_refs=['data/logs/runtime_audit.jsonl', 'OperationalSelfExaminationService', 'ExperimentLab', 'AdaptiveWeightLayer'],
            confidence=confidence,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata=snapshot,
        )

    def _genesis_phase(
        self,
        *,
        phase: str,
        status: str,
        score: float,
        evidence_refs: list[str],
        summary: str,
        next_test: str,
        unresolved_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            'phase': phase,
            'status': status,
            'score': round(max(0.0, min(float(score), 1.0)), 3),
            'summary': summary[:260],
            'evidence_refs': evidence_refs[:6],
            'next_test': next_test[:260],
            'unresolved_fields': list(dict.fromkeys(unresolved_fields or []))[:8],
        }

    def _genesis_readiness_snapshot(
        self,
        *,
        startup_health: dict[str, Any],
        birth_stability: dict[str, Any],
        evidence_basis: dict[str, Any],
        visual_target_binding: dict[str, Any],
        runtime_learning_closure: dict[str, Any] | None = None,
        self_examination: dict[str, Any],
        validation: AutonomousValidationSnapshot | None,
        pending_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Summarize the root metacognitive loop as a portable test matrix.

        This is intentionally not a new brain.  It only folds already-existing
        evidence into the cycle described by the Genesis Kernel proposal:
        birth -> observe -> ground -> communicate -> act -> learn -> reorganize.
        The output is compact enough for other devices/sessions to compare
        readiness without re-parsing every low-level log.
        """
        phases: list[dict[str, Any]] = []

        startup_status = str(startup_health.get('status') or 'unknown')
        startup_unresolved = list(startup_health.get('unresolved_fields') or [])
        startup_blockers = list(startup_health.get('recent_blockers') or [])
        if startup_status == 'analyzed' and not startup_blockers and not startup_unresolved:
            phases.append(self._genesis_phase(
                phase='birth',
                status='pass',
                score=1.0,
                evidence_refs=['data/logs/startup_timeline.jsonl'],
                summary='El arranque tiene timeline analizado y no muestra blockers recientes.',
                next_test='Repetir arranque en otro dispositivo y comparar run_to_window_ms, RSS pico y phases_seen.',
            ))
        elif startup_status == 'analyzed':
            phases.append(self._genesis_phase(
                phase='birth',
                status='warn',
                score=0.58,
                evidence_refs=['data/logs/startup_timeline.jsonl'],
                summary='El arranque es observable, pero hay blockers o campos sin resolver.',
                next_test='Aislar el blocker de startup dominante antes de ejecutar metacognicion profunda.',
                unresolved_fields=startup_unresolved,
            ))
        else:
            phases.append(self._genesis_phase(
                phase='birth',
                status='unresolved',
                score=0.0,
                evidence_refs=['data/logs/startup_timeline.jsonl'],
                summary='No hay evidencia suficiente del nacimiento del proceso.',
                next_test='Ejecutar IABV con startup_timeline activo y confirmar BirthEvent/timeline persistido.',
                unresolved_fields=startup_unresolved or ['UNRESOLVED:startup_timeline'],
            ))

        stable_freezes = int(birth_stability.get('stable_resource_freeze_count') or 0)
        worst_freeze = float(birth_stability.get('worst_freeze_ms') or 0.0)
        birth_unresolved = list(birth_stability.get('unresolved_fields') or [])
        if str(birth_stability.get('status') or '') == 'analyzed' and stable_freezes == 0:
            phases.append(self._genesis_phase(
                phase='stabilize',
                status='pass',
                score=1.0,
                evidence_refs=['data/evolution/incident_reports/freeze_*.json', 'data/logs/runtime_audit.jsonl'],
                summary='No hay congelamientos recientes con recursos estables en la evidencia analizada.',
                next_test='Mantener watchdog activo y validar que nuevas consultas no produzcan ui_event_loop_stall.',
            ))
        elif stable_freezes:
            phases.append(self._genesis_phase(
                phase='stabilize',
                status='fail',
                score=0.25,
                evidence_refs=['data/evolution/incident_reports/freeze_*.json', 'data/logs/runtime_audit.jsonl'],
                summary=f'{stable_freezes} freeze(s) con recursos estables; peor stall {worst_freeze:.0f}ms.',
                next_test='Mover o presupuestar el trabajo pesado que aparece en el stack dominante y repetir prueba viva.',
                unresolved_fields=birth_unresolved,
            ))
        else:
            phases.append(self._genesis_phase(
                phase='stabilize',
                status='unresolved',
                score=0.0,
                evidence_refs=['data/evolution/incident_reports/freeze_*.json'],
                summary='No hay suficiente evidencia de estabilidad post-arranque.',
                next_test='Esperar 90s tras abrir IABV y verificar que no se emite freeze report.',
                unresolved_fields=birth_unresolved or ['UNRESOLVED:birth_stability'],
            ))

        evidence_state = str(evidence_basis.get('state') or 'unresolved')
        live_sources = list(evidence_basis.get('live_sources') or [])
        persisted_sources = list(evidence_basis.get('persisted_sources') or [])
        evidence_unresolved = list(evidence_basis.get('unresolved') or [])
        if evidence_state == 'observed':
            phases.append(self._genesis_phase(
                phase='observe',
                status='pass' if not evidence_unresolved else 'warn',
                score=0.9 if not evidence_unresolved else 0.62,
                evidence_refs=['WorldModelSnapshot', 'EnvironmentSelfModel', 'TaskContextAssembler'],
                summary=f'Fuentes vivas disponibles: {", ".join(live_sources) or "n/d"}.',
                next_test='Cruzar WorldModel y EnvironmentSelfModel contra lo visible en pantalla en una prueba viva.',
                unresolved_fields=evidence_unresolved,
            ))
        elif evidence_state == 'inferred':
            phases.append(self._genesis_phase(
                phase='observe',
                status='warn',
                score=0.45,
                evidence_refs=['TaskContextAssembler', 'PortableContextService'],
                summary=f'Solo hay fuentes persistidas/inferidas: {", ".join(persisted_sources) or "n/d"}.',
                next_test='Tomar snapshot vivo del dispositivo antes de decidir una accion externa.',
                unresolved_fields=evidence_unresolved,
            ))
        else:
            phases.append(self._genesis_phase(
                phase='observe',
                status='unresolved',
                score=0.0,
                evidence_refs=['WorldModelSnapshot', 'EnvironmentSelfModel'],
                summary='El sistema no tiene base evidencial viva suficiente para saber en que entorno esta.',
                next_test='Conectar WorldModel/EnvironmentSelfModel al paquete antes de juzgar capacidad universal.',
                unresolved_fields=evidence_unresolved or ['UNRESOLVED:evidence_basis'],
            ))

        visual_status = str(visual_target_binding.get('status') or 'unknown')
        binding_statuses = dict(visual_target_binding.get('recent_binding_statuses') or {})
        visual_unresolved = list(visual_target_binding.get('unresolved_fields') or [])
        latest_metavision = dict(visual_target_binding.get('latest_metavision') or {})
        has_semantic_visual = bool(binding_statuses or latest_metavision or visual_target_binding.get('latest_calibration'))
        bad_bindings = sum(int(binding_statuses.get(key) or 0) for key in ('missing', 'wrong_surface', 'self_capture'))
        if visual_status == 'analyzed' and bad_bindings == 0:
            phases.append(self._genesis_phase(
                phase='ground',
                status='pass',
                score=0.88,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'UniversalPerceptionService', 'WorldModelService'],
                summary='Hay eventos visuales recientes y no predominan missing/self_capture/wrong_surface.',
                next_test='Pedir "esa ventana" con dos candidatos visibles y confirmar binding_status bound/ambiguous correcto.',
                unresolved_fields=visual_unresolved,
            ))
        elif has_semantic_visual:
            phases.append(self._genesis_phase(
                phase='ground',
                status='warn' if bad_bindings else 'pass',
                score=0.5 if bad_bindings else 0.78,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'UniversalPerceptionService'],
                summary=f'Binding visual con estados recientes={binding_statuses}; requiere calibracion viva si hay target_missing.',
                next_test='Ejecutar calibracion visual con ChatGPT visible y verificar que no capture IABV/Codex como objetivo.',
                unresolved_fields=visual_unresolved,
            ))
        else:
            phases.append(self._genesis_phase(
                phase='ground',
                status='unresolved',
                score=0.0,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'UniversalPerceptionService'],
                summary='No hay eventos recientes de binding visual/metavision para probar referencias como "esa ventana".',
                next_test='Generar visual_target_binding_result antes de capturar pantalla completa.',
                unresolved_fields=visual_unresolved or ['UNRESOLVED:visual_grounding'],
            ))

        lifecycle = self._interaction_lifecycle_summary()
        recent_interactions = list(lifecycle.get('recent_completed') or [])
        resolved_count = sum(1 for item in recent_interactions if item.get('resolved') or item.get('outcome') == 'resolved')
        failed_count = sum(1 for item in recent_interactions if item.get('outcome') == 'failed')
        blocked_count = sum(1 for item in recent_interactions if item.get('outcome') == 'blocked')
        if recent_interactions and failed_count == 0:
            phases.append(self._genesis_phase(
                phase='communicate',
                status='pass' if blocked_count == 0 else 'warn',
                score=0.82 if blocked_count == 0 else 0.62,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'ChatInteractionLifecycle'],
                summary=f'{len(recent_interactions)} interaccion(es) recientes reconstruidas; resueltas={resolved_count}, bloqueadas={blocked_count}.',
                next_test='Hacer pregunta metacognitiva y confirmar respuesta <5s con evidencia, diagnostico y siguiente accion.',
            ))
        elif recent_interactions:
            phases.append(self._genesis_phase(
                phase='communicate',
                status='fail',
                score=0.28,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'ChatInteractionLifecycle'],
                summary=f'Interacciones recientes incluyen fallos: failed={failed_count}, blocked={blocked_count}.',
                next_test='Clasificar si el fallo fue ruta local indebida, falta de ventana, permiso o congelamiento.',
                unresolved_fields=['UNRESOLVED:communication_reliability'],
            ))
        else:
            phases.append(self._genesis_phase(
                phase='communicate',
                status='unresolved',
                score=0.0,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'ChatInteractionLifecycle'],
                summary='No hay interacciones recientes reconstruibles.',
                next_test='Enviar una pregunta de estado y verificar interaction_open -> interaction_resolved.',
                unresolved_fields=['UNRESOLVED:interaction_lifecycle'],
            ))

        findings = list(self_examination.get('findings') or [])
        feedback = list(self_examination.get('recommendation_feedback') or [])
        validated = list(self_examination.get('validated_improvements') or [])
        learning_closure = dict(runtime_learning_closure or {})
        closure_status = str(learning_closure.get('status') or '')
        closure_repeated = list(learning_closure.get('repeated_patterns') or [])
        closure_candidates = list(learning_closure.get('learning_candidates') or [])
        if validated:
            phases.append(self._genesis_phase(
                phase='learn',
                status='pass',
                score=0.9,
                evidence_refs=['OperationalSelfExaminationService', 'ExperimentLab'],
                summary=f'{len(validated)} mejora(s) validadas con evidencia.',
                next_test='Repetir un caso fallido y comprobar que el sistema cambia de estrategia.',
            ))
        elif findings:
            phases.append(self._genesis_phase(
                phase='learn',
                status='warn',
                score=0.48,
                evidence_refs=['OperationalSelfExaminationService', 'runtime_audit', 'ExperimentLab'],
                summary=f'{len(findings)} hallazgo(s) activos, pero sin mejoras validadas todavia.',
                next_test='Cerrar un hallazgo con prueba antes/despues y registrar feedback de recomendacion.',
                unresolved_fields=list(self_examination.get('unresolved_risks') or [])[:6],
            ))
        elif closure_repeated or closure_status == 'learning_signal_repeated':
            phases.append(self._genesis_phase(
                phase='learn',
                status='warn',
                score=0.44,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'OperationalSelfExaminationService', 'ExperimentLab'],
                summary=(
                    f'RuntimeAudit detecto {len(closure_repeated)} patron(es) repetidos; '
                    'falta validar la adaptacion.'
                ),
                next_test=str(learning_closure.get('next_learning_action') or 'Cerrar patron repetido con OSES y prueba antes/despues.'),
                unresolved_fields=list(learning_closure.get('unresolved_fields') or ['UNRESOLVED:learning_outcome_not_validated'])[:6],
            ))
        elif closure_candidates:
            phases.append(self._genesis_phase(
                phase='learn',
                status='warn',
                score=0.36,
                evidence_refs=['data/logs/runtime_audit.jsonl', 'OperationalSelfExaminationService'],
                summary=f'RuntimeAudit tiene {len(closure_candidates)} candidato(s) de aprendizaje sin repeticion suficiente.',
                next_test=str(learning_closure.get('next_learning_action') or 'Recolectar otra muestra comparable antes de ajustar pesos.'),
                unresolved_fields=list(learning_closure.get('unresolved_fields') or ['UNRESOLVED:learning_candidate_needs_second_sample'])[:6],
            ))
        else:
            phases.append(self._genesis_phase(
                phase='learn',
                status='unresolved',
                score=0.0,
                evidence_refs=['OperationalSelfExaminationService'],
                summary='No hay autoexaminacion fuerte disponible para aprendizaje.',
                next_test='Generar OSES current_review y comprobar que sus hallazgos aparecen en portable_context.',
                unresolved_fields=['UNRESOLVED:self_examination'],
            ))

        validation_status = str(getattr(validation, 'status', '') or '')
        validation_unresolved = list(getattr(validation, 'unresolved_fields', []) or [])
        validation_metadata = dict(getattr(validation, 'metadata', {}) or {})
        promoted_count = int(validation_metadata.get('promoted_count') or 0)
        if promoted_count > 0:
            phases.append(self._genesis_phase(
                phase='reorganize',
                status='pass',
                score=0.86,
                evidence_refs=['AutonomousValidationCycleService', 'SandboxExperimentService'],
                summary=f'Hay {promoted_count} promocion(es) validadas por el ciclo autonomo.',
                next_test='Verificar que cada promocion tenga rollback o evidencia de sandbox.',
            ))
        elif validation_status and validation_status != 'bootstrapping':
            phases.append(self._genesis_phase(
                phase='reorganize',
                status='warn',
                score=0.42,
                evidence_refs=['AutonomousValidationCycleService', 'SandboxExperimentService'],
                summary=f'Ciclo de validacion presente en estado {validation_status}, pero sin promocion validada.',
                next_test='Correr un candidato pequeno en sandbox y exigir veredicto antes de tocar runtime.',
                unresolved_fields=validation_unresolved,
            ))
        else:
            phases.append(self._genesis_phase(
                phase='reorganize',
                status='unresolved',
                score=0.0,
                evidence_refs=['AutonomousValidationCycleService', 'SandboxExperimentService'],
                summary='La reorganizacion gobernada no tiene ciclo activo/promociones observables.',
                next_test='Conectar evidencia del ciclo de validacion o mantener automodificacion bloqueada.',
                unresolved_fields=validation_unresolved or ['UNRESOLVED:autonomous_validation_cycle'],
            ))

        relevant_pending = [
            item for item in pending_items
            if any(token in str(item.get('id') or item.get('title') or '').lower()
                   for token in ('genesis', 'birth', 'metavision', 'visual', 'communication', 'universal', 'device'))
        ][:8]
        if relevant_pending:
            phases.append(self._genesis_phase(
                phase='portability',
                status='warn',
                score=0.58,
                evidence_refs=['data/evolution/platform_pending/*.json'],
                summary=f'{len(relevant_pending)} pendiente(s) relevantes guian pruebas para otros dispositivos.',
                next_test='Convertir cada pendiente critico en test de contrato reproducible por dispositivo.',
                unresolved_fields=[
                    str(item.get('dependency_missing') or item.get('id') or '')[:120]
                    for item in relevant_pending
                    if item.get('dependency_missing') or item.get('id')
                ],
            ))
        else:
            phases.append(self._genesis_phase(
                phase='portability',
                status='unresolved',
                score=0.0,
                evidence_refs=['data/evolution/platform_pending/*.json'],
                summary='No hay backlog portable visible para replicar el aprendizaje en otros dispositivos.',
                next_test='Registrar matriz de pruebas por dispositivo: arranque, ventana, comunicacion, vision y aprendizaje.',
                unresolved_fields=['UNRESOLVED:portable_device_test_matrix'],
            ))

        scores = [float(item.get('score') or 0.0) for item in phases]
        overall_score = round(sum(scores) / len(scores), 3) if scores else 0.0
        weakest = min(phases, key=lambda item: float(item.get('score') or 0.0)) if phases else {}
        status_counts = Counter(str(item.get('status') or '') for item in phases)
        if status_counts.get('fail', 0) > 0 or overall_score < 0.45:
            readiness_status = 'blocked'
        elif status_counts.get('unresolved', 0) > 0 or overall_score < 0.75:
            readiness_status = 'needs_evidence'
        else:
            readiness_status = 'ready_for_cross_device_trials'
        return {
            'status': readiness_status,
            'overall_score': overall_score,
            'phase_count': len(phases),
            'status_counts': dict(status_counts),
            'weakest_phase': weakest.get('phase', ''),
            'weakest_next_test': weakest.get('next_test', ''),
            'phases': phases,
            'priority_equation': (
                'communication + observability + uncertainty_reduction + learning_value + '
                'portability - resource_cost - user_friction - risk'
            ),
            'source_contract': 'Nucleo Genesis Metacognitivo: birth->observe->ground->communicate->act->learn->reorganize',
        }

    def _genesis_readiness_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        phases = list(snapshot.get('phases') or [])
        weakest = str(snapshot.get('weakest_phase') or 'n/d')
        score = float(snapshot.get('overall_score') or 0.0)
        status = str(snapshot.get('status') or 'unknown')
        if status == 'ready_for_cross_device_trials':
            summary = f'Nucleo Genesis listo para pruebas entre dispositivos (score={score:.2f}).'
        elif status == 'blocked':
            summary = f'Nucleo Genesis bloqueado por fase {weakest} (score={score:.2f}).'
        else:
            summary = f'Nucleo Genesis requiere mas evidencia; fase mas debil: {weakest} (score={score:.2f}).'
        unresolved: list[str] = []
        for phase in phases:
            unresolved.extend(str(item) for item in list(phase.get('unresolved_fields') or []) if str(item))
        return self._section(
            section_id='genesis_readiness',
            title='Nucleo Genesis metacognitivo',
            summary=summary,
            items=phases,
            source_kind='aggregated_runtime_contract',
            source_refs=[
                'data/logs/startup_timeline.jsonl',
                'data/logs/runtime_audit.jsonl',
                'data/evolution/incident_reports/freeze_*.json',
                'WorldModelSnapshot',
                'EnvironmentSelfModel',
                'OperationalSelfExaminationService',
                'AutonomousValidationCycleService',
            ],
            confidence=score,
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(unresolved))[:12],
            metadata=snapshot,
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

    def _birth_stability_section(self, *, status: dict[str, Any], now) -> PortableContextSection:
        st = str(status.get('status') or 'no_data')
        stable_count = int(status.get('stable_resource_freeze_count') or 0)
        worst_ms = float(status.get('worst_freeze_ms') or 0.0)
        dominant = str(status.get('dominant_cause') or '')
        duplicate_summary = dict(status.get('startup_duplicate_summary') or {})
        metacog_skipped = bool(status.get('startup_metacognition_skipped'))
        unresolved = list(status.get('unresolved_fields') or [])
        items: list[dict[str, Any]] = [
            {
                'label': 'stable_resource_freezes',
                'count': stable_count,
                'worst_ms': worst_ms,
                'dominant_cause': dominant,
            },
            {
                'label': 'startup_duplicates',
                'blocked_count': duplicate_summary.get('blocked_count', 0),
                'focus_success_count': duplicate_summary.get('focus_success_count', 0),
                'reasons': duplicate_summary.get('reasons', {}),
            },
            {
                'label': 'deferred_metacognition',
                'startup_metacognition_skipped': metacog_skipped,
            },
        ]
        items.extend(list(status.get('recent_freeze_reports') or [])[:3])
        if stable_count and dominant:
            summary = (
                f'{stable_count} freeze(s) con recursos estables; causa dominante '
                f'{dominant}; peor stall {worst_ms:.0f}ms.'
            )
        elif st == 'analyzed':
            summary = 'Nacimiento auditado sin freeze estable reciente.'
        else:
            summary = 'Sin evidencia suficiente de nacimiento/congelamiento para analizar.'
        if metacog_skipped and stable_count:
            summary += ' Falta ejecutar aprendizaje metacognitivo diferido post-idle.'
        return self._section(
            section_id='birth_stability',
            title='Estabilidad del nacimiento consciente',
            summary=summary,
            items=items,
            source_kind='startup_and_freeze_artifacts',
            source_refs=[
                'data/logs/startup_audit.jsonl',
                'data/logs/startup_timeline.jsonl',
                'data/evolution/incident_reports/freeze_*.json',
            ],
            confidence=0.86 if st == 'analyzed' else 0.0,
            last_updated=now,
            unresolved_fields=unresolved,
            metadata=dict(status),
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

    def _module_progress_snapshot(self) -> dict[str, Any]:
        """Summarize platform_pending as organ/module progress.

        This is a read-only control map for the evolutionary roadmap. It does
        not decide execution; it tells the next session which organs are
        incomplete, how complex they look, and what should be handled first.
        """

        pending_dir = Path(self.workspace_root) / 'data' / 'evolution' / 'platform_pending'
        if not pending_dir.exists():
            return {
                'status': 'unavailable',
                'total_tasks': 0,
                'overall_progress_percent': 0.0,
                'modules': [],
                'top_open_tasks': [],
                'unresolved_fields': ['UNRESOLVED:platform_pending_dir'],
            }

        tasks: list[dict[str, Any]] = []
        for path in sorted(pending_dir.glob('*.json')):
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            tasks.append({
                'id': str(payload.get('id') or path.stem),
                'title': str(payload.get('title') or path.stem),
                'status': str(payload.get('status') or 'PENDING'),
                'priority': str(payload.get('priority') or 'medium').lower(),
                'category': str(payload.get('category') or 'uncategorized'),
                'next_action': str(payload.get('next_action') or ''),
            })

        if not tasks:
            return {
                'status': 'empty',
                'total_tasks': 0,
                'overall_progress_percent': 0.0,
                'modules': [],
                'top_open_tasks': [],
                'unresolved_fields': ['UNRESOLVED:platform_pending_tasks'],
            }

        completed_count = sum(1 for task in tasks if task['status'] == 'COMPLETED')
        priority_weight = {'critical': 5.0, 'high': 3.0, 'medium': 2.0, 'low': 1.0}
        by_category: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            by_category.setdefault(task['category'], []).append(task)

        modules: list[dict[str, Any]] = []
        for category, items in sorted(by_category.items()):
            completed = sum(1 for item in items if item['status'] == 'COMPLETED')
            open_items = [item for item in items if item['status'] != 'COMPLETED']
            complexity_score = round(
                sum(priority_weight.get(item['priority'], 1.5) for item in open_items),
                2,
            )
            critical_open = sum(1 for item in open_items if item['priority'] == 'critical')
            progress_percent = round((completed / max(len(items), 1)) * 100.0, 1)
            next_focus = sorted(
                open_items,
                key=lambda item: (
                    -priority_weight.get(item['priority'], 1.5),
                    item['status'],
                    item['id'],
                ),
            )[:3]
            modules.append({
                'category': category,
                'total': len(items),
                'completed': completed,
                'open': len(open_items),
                'critical_open': critical_open,
                'progress_percent': progress_percent,
                'missing_percent': round(100.0 - progress_percent, 1),
                'complexity_score': complexity_score,
                'next_focus': [
                    {
                        'id': item['id'][:120],
                        'status': item['status'],
                        'priority': item['priority'],
                        'next_action': item['next_action'][:220],
                    }
                    for item in next_focus
                ],
            })

        top_open = sorted(
            [task for task in tasks if task['status'] != 'COMPLETED'],
            key=lambda item: (
                -priority_weight.get(item['priority'], 1.5),
                item['status'],
                item['category'],
                item['id'],
            ),
        )[:8]

        return {
            'status': 'tracked',
            'total_tasks': len(tasks),
            'completed_tasks': completed_count,
            'open_tasks': len(tasks) - completed_count,
            'overall_progress_percent': round((completed_count / max(len(tasks), 1)) * 100.0, 1),
            'modules': sorted(
                modules,
                key=lambda item: (
                    -int(item.get('critical_open') or 0),
                    -float(item.get('complexity_score') or 0.0),
                    str(item.get('category') or ''),
                ),
            )[:16],
            'top_open_tasks': [
                {
                    'id': item['id'][:120],
                    'category': item['category'][:100],
                    'status': item['status'],
                    'priority': item['priority'],
                    'next_action': item['next_action'][:220],
                }
                for item in top_open
            ],
            'unresolved_fields': [],
        }

    def _module_progress_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        modules = list(snapshot.get('modules') or [])
        top_open = list(snapshot.get('top_open_tasks') or [])
        progress = float(snapshot.get('overall_progress_percent') or 0.0)
        summary = (
            f"Progreso global {progress:.1f}%: "
            f"{int(snapshot.get('completed_tasks') or 0)} completadas, "
            f"{int(snapshot.get('open_tasks') or 0)} abiertas."
        )
        items = [
            {
                'label': str(item.get('category') or ''),
                'value': (
                    f"{float(item.get('progress_percent') or 0.0):.1f}% listo | "
                    f"faltante {float(item.get('missing_percent') or 0.0):.1f}% | "
                    f"complejidad {float(item.get('complexity_score') or 0.0):.1f} | "
                    f"criticos abiertos {int(item.get('critical_open') or 0)}"
                ),
                'next_focus': list(item.get('next_focus') or [])[:3],
            }
            for item in modules[:10]
        ]
        if top_open:
            items.append({
                'label': 'top_open_tasks',
                'value': 'Primeras tareas abiertas por criticidad y complejidad.',
                'items': top_open[:6],
            })
        return self._section(
            section_id='module_progress',
            title='Progreso por organo/modulo',
            summary=summary if modules else 'No hay matriz de progreso disponible.',
            items=items,
            source_kind='platform_pending_progress',
            source_refs=['data/evolution/platform_pending/*.json'],
            confidence=0.86 if modules else 0.0,
            last_updated=now,
            unresolved_fields=list(snapshot.get('unresolved_fields') or []),
            metadata=snapshot,
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
        """Read structured pending items from PlatformPendingQueue (canonical contract)."""
        queue = self.platform_pending_queue
        if queue is not None and hasattr(queue, 'to_portable_items'):
            try:
                return queue.to_portable_items(limit=6)
            except Exception:
                pass
        # Fallback: instantiate queue directly and use canonical contract
        try:
            from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue
            fallback_queue = PlatformPendingQueue(self.workspace_root / 'data' / 'evolution')
            return fallback_queue.to_portable_items(limit=6)
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

    def _universal_evolution_scorecard_snapshot(self, *, account_resource: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build universal evolution scorecard comparing current vs previous state.

        This is read-only and uses the UniversalEvolutionScorecard module to
        determine if the system improved, regressed, or stayed stuck after changes.
        """
        try:
            from iabv_v15.services.evolution.universal_evolution_scorecard import (
                build_universal_evolution_scorecard,
                normalize_evolution_metrics,
            )
        except Exception:
            return {
                'status': 'unavailable',
                'error': 'universal_evolution_scorecard_module_missing',
                'unresolved_fields': ['UNRESOLVED:scorecard_module_not_available'],
            }

        # Load previous scorecard from storage
        previous = None
        try:
            prev_path = Path(self.workspace_root) / 'data' / 'evolution' / 'universal_evolution' / 'previous_scorecard.json'
            if prev_path.exists():
                previous = json.loads(prev_path.read_text(encoding='utf-8'))
        except Exception:
            pass

        # Build current metrics from existing snapshots
        current_metrics: dict[str, Any] = {}

        # Extract from algorithm fitness
        algorithm_fitness = self._algorithm_fitness_snapshot()
        if algorithm_fitness.get('status') != 'error':
            current_metrics['algorithm_count'] = len(algorithm_fitness.get('algorithms', []))
            current_metrics['unknown_capability_count'] = len([
                a for a in algorithm_fitness.get('algorithms', [])
                if a.get('capability_area') == 'unknown'
            ])

        # Extract from tool autonomy status
        tool_autonomy = self._tool_autonomy_status_snapshot(account_resource=account_resource)
        if tool_autonomy.get('status') != 'error':
            tools = tool_autonomy.get('tools', [])
            current_metrics['tools'] = {
                'total': len(tools),
                'live_verified': sum(1 for t in tools if t.get('live_verified')),
                'response_capture_verified': sum(1 for t in tools if t.get('response_capture_verified')),
            }

        # Extract from runtime organ state
        runtime_organ = self._runtime_organ_matrix_snapshot()
        if runtime_organ.get('status') != 'unavailable':
            organs = runtime_organ.get('organs', [])
            current_metrics['runtime'] = {
                'organ_count': len(organs),
                'heavy_active': sum(1 for o in organs if o.get('cost_class') == 'heavy' and o.get('mode') == 'active'),
            }

        # Normalize metrics
        current = normalize_evolution_metrics(current_metrics)

        # Build scorecard
        scorecard = build_universal_evolution_scorecard(
            previous=previous,
            current=current,
            repeated_unresolved=self._load_repeated_unresolved(),
            cycle_markers=self._load_cycle_markers(),
        )

        # Save current as previous for next comparison
        try:
            scorecard_path = Path(self.workspace_root) / 'data' / 'evolution' / 'universal_evolution' / 'previous_scorecard.json'
            scorecard_path.parent.mkdir(parents=True, exist_ok=True)
            scorecard_path.write_text(json.dumps(current, default=str, indent=2), encoding='utf-8')
        except Exception:
            pass

        return scorecard

    def _load_repeated_unresolved(self) -> list[str]:
        """Load unresolved fields that have persisted across multiple sessions."""
        try:
            path = Path(self.workspace_root) / 'data' / 'evolution' / 'portable_context' / 'latest.json'
            if not path.exists():
                return []
            payload = json.loads(path.read_text(encoding='utf-8'))
            unresolved = list(payload.get('unresolved_fields', []))
            # Filter for UNRESOLVED that are likely persistent
            persistent = [u for u in unresolved if 'UNRESOLVED:' in u and 'pending' not in u.lower()]
            return persistent[:20]
        except Exception:
            return []

    def _load_cycle_markers(self) -> list[str]:
        """Load markers that indicate the system is stuck in a cycle."""
        try:
            path = Path(self.workspace_root) / 'data' / 'evolution' / 'operational_self_examination' / 'latest.json'
            if not path.exists():
                return []
            payload = json.loads(path.read_text(encoding='utf-8'))
            findings = list(payload.get('findings', []))
            # Look for repeated patterns
            categories = [f.get('category', '') for f in findings]
            from collections import Counter
            counts = Counter(categories)
            repeated = [cat for cat, count in counts.items() if count >= 3]
            return repeated[:10]
        except Exception:
            return []

    def _universal_evolution_scorecard_section(self, *, snapshot: dict[str, Any], now) -> PortableContextSection:
        """Build universal evolution scorecard section for PortableContext.

        This section answers the metacognitive question: did the system improve,
        regress, or stay stuck after changes?
        """
        verdict = str(snapshot.get('verdict') or 'UNRESOLVED')
        summary = str(snapshot.get('summary') or 'Scorecard no disponible')
        items: list[dict[str, Any]] = []

        # Add verdict item
        items.append({
            'label': 'Veredicto de evolución',
            'value': verdict,
            'detail': summary[:200],
        })

        # Add metric changes
        metric_changes = list(snapshot.get('metric_changes') or [])
        for change in metric_changes[:8]:
            items.append({
                'label': str(change.get('metric') or 'n/d'),
                'value': str(change.get('direction') or 'n/d'),
                'detail': f"{change.get('previous', 0):.3f} → {change.get('current', 0):.3f}",
            })

        # Add repeated unresolved if present
        repeated = list(snapshot.get('repeated_unresolved') or [])
        if repeated:
            items.append({
                'label': 'UNRESOLVED recurrentes',
                'value': str(len(repeated)),
                'detail': ', '.join(repeated[:4]),
            })

        # Add cycle markers if present
        cycles = list(snapshot.get('cycle_markers') or [])
        if cycles:
            items.append({
                'label': 'Marcadores de ciclo',
                'value': str(len(cycles)),
                'detail': ', '.join(cycles[:4]),
            })

        unresolved = list(snapshot.get('unresolved_fields') or [])
        if verdict == 'UNRESOLVED':
            unresolved.append('UNRESOLVED:scorecard_verdict_unknown')

        return self._section(
            section_id='universal_evolution_scorecard',
            title='Universal Evolution Scorecard',
            summary=f'{verdict}: {summary}',
            items=items,
            source_kind='metacognitive_comparison',
            source_refs=['UniversalEvolutionScorecard', 'PortableContext'],
            confidence=float(snapshot.get('confidence') or 0.0),
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(unresolved)),
            metadata={
                'verdict': verdict,
                'epsilon': snapshot.get('epsilon', 0.015),
                'metric_count': len(metric_changes),
            },
        )

    def _artifact_lifecycle_section(self, *, now) -> PortableContextSection:
        """Artifact lifecycle storage governance summary (P0.134/P0.136).
        
        Reads the artifact lifecycle inventory from data/evolution/artifact_lifecycle/latest.json
        and exposes storage hygiene metrics, reclaimable space, and quarantine candidates.
        """
        path = Path(self.workspace_root) / 'data' / 'evolution' / 'artifact_lifecycle' / 'latest.json'
        if not path.exists():
            return self._section(
                section_id='artifact_lifecycle',
                title='Gobernanza de ciclo de vida de artifacts',
                summary='Inventario de artifact lifecycle no ejecutado aún.',
                items=[],
                source_kind='storage_governance',
                source_refs=['ArtifactLifecycleService'],
                confidence=0.0,
                last_updated=now,
                unresolved_fields=['UNRESOLVED:artifact_lifecycle_inventory_missing'],
            )
        
        try:
            inventory = json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.debug(f'PortableContext: failed to read artifact lifecycle inventory: {exc}')
            return self._section(
                section_id='artifact_lifecycle',
                title='Gobernanza de ciclo de vida de artifacts',
                summary='Error al leer inventario de artifact lifecycle.',
                items=[],
                source_kind='storage_governance',
                source_refs=['ArtifactLifecycleService'],
                confidence=0.0,
                last_updated=now,
                unresolved_fields=['UNRESOLVED:artifact_lifecycle_inventory_error'],
            )
        
        # Build items from inventory
        items: list[dict[str, Any]] = []
        
        # Summary metrics
        total_size = inventory.get('total_scanned_size_bytes', 0)
        total_files = inventory.get('total_file_count', 0)
        reclaimable = inventory.get('reclaimable_bytes_estimate', 0)
        keep_count = inventory.get('keep_count', 0)
        quarantine_count = inventory.get('quarantine_candidates_count', 0)
        delete_approval_count = inventory.get('delete_requires_approval_count', 0)
        unknown_count = inventory.get('unknown_count', 0)
        
        items.append({
            'label': 'Total escaneado',
            'value': f'{total_size / (1024*1024):.1f}MB en {total_files} archivos',
        })
        
        items.append({
            'label': 'Espacio recuperable',
            'value': f'{reclaimable / (1024*1024):.1f}MB ({reclaimable / max(total_size, 1):.1%})',
        })
        
        items.append({
            'label': 'Archivos a mantener',
            'value': str(keep_count),
        })
        
        items.append({
            'label': 'Candidatos a quarantine',
            'value': str(quarantine_count),
        })
        
        items.append({
            'label': 'Requieren aprobación',
            'value': str(delete_approval_count),
        })
        
        if unknown_count > 0:
            items.append({
                'label': 'Sin clasificar',
                'value': str(unknown_count),
            })
        
        # Top heavy folders
        for folder in inventory.get('top_heavy_folders', [])[:3]:
            items.append({
                'label': f'Carpeta pesada: {folder.get("path", "n/d")[:60]}',
                'value': f'{folder.get("size_bytes", 0) / (1024*1024):.1f}MB',
            })
        
        # Top heavy files
        for file in inventory.get('top_heavy_files', [])[:3]:
            items.append({
                'label': f'Archivo pesado: {file.get("path", "n/d")[:60]}',
                'value': f'{file.get("size_bytes", 0) / (1024*1024):.1f}MB',
            })
        
        # Duplicate groups
        duplicate_groups = inventory.get('duplicate_groups', [])
        if duplicate_groups:
            items.append({
                'label': 'Grupos de duplicados',
                'value': str(len(duplicate_groups)),
            })
        
        # Build summary
        summary_parts = [
            f'{total_files} archivos escaneados ({total_size / (1024*1024):.1f}MB)',
            f'{reclaimable / (1024*1024):.1f}MB recuperables',
            f'{quarantine_count} candidatos a quarantine',
        ]
        if delete_approval_count > 0:
            summary_parts.append(f'{delete_approval_count} requieren aprobación')
        
        # Unresolved fields
        unresolved = list(inventory.get('unresolved_fields', []))
        if unknown_count > 0:
            unresolved.append(f'unknown_artifacts:{unknown_count}')
        if delete_approval_count > 0:
            unresolved.append(f'delete_requires_approval:{delete_approval_count}')
        
        return self._section(
            section_id='artifact_lifecycle',
            title='Gobernanza de ciclo de vida de artifacts',
            summary=', '.join(summary_parts),
            items=items,
            source_kind='storage_governance',
            source_refs=['ArtifactLifecycleService', 'data/evolution/artifact_lifecycle/latest.json'],
            confidence=0.85 if total_files > 0 else 0.0,
            last_updated=now,
            unresolved_fields=list(dict.fromkeys(unresolved)),
            metadata={
                'total_size_bytes': total_size,
                'total_file_count': total_files,
                'reclaimable_bytes_estimate': reclaimable,
                'keep_count': keep_count,
                'quarantine_candidates_count': quarantine_count,
                'delete_requires_approval_count': delete_approval_count,
                'unknown_count': unknown_count,
                'duplicate_group_count': len(duplicate_groups),
            },
        )
