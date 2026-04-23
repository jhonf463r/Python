from __future__ import annotations

from collections import Counter
from typing import Any

from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    DecisionContext,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    ExternalStateFlag,
    GoalContext,
    HiddenIncident,
    IATraceEntry,
    InferenceRequest,
    IntentRouteDecision,
    ObjectiveNodeKind,
    PerceptionSnapshot,
    RuntimeSignal,
    SessionHealthSnapshot,
    TaskContext,
    TaskIntent,
    VisualSignalSnapshot,
    WorldModelSnapshot,
    canonical_external_state_flag,
    canonical_external_state_flags,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.services.capture.browser_learning_assembler import BrowserLearningAssembler
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry


class TaskContextAssembler:
    def __init__(
        self,
        *,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        dossier_repository: ExecutionDossierRepository,
        hidden_incident_repository: HiddenIncidentRepository,
        site_policy_registry: SitePolicyRegistry,
        capability_repository: CapabilityRepository,
        adaptive_session_repository: AdaptiveSessionRepository,
        artifact_repository: SessionArtifactRepository | None = None,
        tool_record_repository: ToolRecordRepository | None = None,
        objective_repository: ObjectiveRepository | None = None,
        experiment_lab_repository: ExperimentLabRepository | None = None,
        live_audit_supervisor: Any | None = None,
        unified_memory_layer: Any | None = None,
        environment_self_awareness_service: Any | None = None,
        world_model_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        portable_context_service: Any | None = None,
    ) -> None:
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.dossier_repository = dossier_repository
        self.hidden_incident_repository = hidden_incident_repository
        self.site_policy_registry = site_policy_registry
        self.capability_repository = capability_repository
        self.adaptive_session_repository = adaptive_session_repository
        self.artifact_repository = artifact_repository
        self.tool_record_repository = tool_record_repository
        self.objective_repository = objective_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.live_audit_supervisor = live_audit_supervisor
        self.unified_memory_layer = unified_memory_layer
        self.environment_self_awareness_service = environment_self_awareness_service
        self.world_model_service = world_model_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.portable_context_service = portable_context_service
        self._teaching_visual_summary_builder = BrowserLearningAssembler()

    def build(self, request: InferenceRequest, intent: TaskIntent) -> TaskContext:
        return self._build_task_context(request=request, intent=intent)

    def build_perception_snapshot(
        self,
        request: InferenceRequest,
        intent: TaskIntent,
        route_decision: IntentRouteDecision | None = None,
        runtime_signals: list[RuntimeSignal] | None = None,
        session_health: SessionHealthSnapshot | None = None,
        ia_trace: list[IATraceEntry] | None = None,
        visual_signal: dict[str, Any] | None = None,
        intent_schema: Any = None,
    ) -> PerceptionSnapshot:
        task_context = self._build_task_context(request=request, intent=intent)
        goal_context = task_context.goal_context
        memory_snapshot = self._memory_snapshot(task_context)
        resolved_route_decision = route_decision or IntentRouteDecision(
            detected_role=intent.detected_role,
            planner_required=bool(request.enable_planning or intent.multi_step),
            visual_required=bool(request.requires_visual_reasoning),
            reason='Preliminary route inferred before governance.',
        )
        resolved_runtime_signals = self._runtime_signals_from_input(runtime_signals if runtime_signals is not None else request.metadata.get('runtime_signals'))
        resolved_session_health = self._session_health_from_input(session_health if session_health is not None else request.metadata.get('session_health'))
        resolved_ia_trace = self._ia_trace_from_input(
            ia_trace if ia_trace is not None else request.metadata.get('ia_trace'),
            site_id=task_context.site_id,
            user_goal=request.user_goal,
        )
        resolved_visual_signal = self._visual_signal_from_input(visual_signal if visual_signal is not None else request.metadata.get('visual_signal'))
        environment_self_model = self._environment_self_model()
        world_model = self._world_model(request=request, intent=intent)
        unresolved_fields: list[str] = []
        if not resolved_runtime_signals:
            unresolved_fields.append('UNRESOLVED:runtime_signals')
        if resolved_session_health is None:
            unresolved_fields.append('UNRESOLVED:session_health')
        if not resolved_ia_trace:
            unresolved_fields.append('UNRESOLVED:ia_trace')
        if not self._visual_signal_available(resolved_visual_signal):
            unresolved_fields.append('UNRESOLVED:visual_signal')
        if not str(environment_self_model.environment_id or '').strip():
            unresolved_fields.append('UNRESOLVED:environment_self_model')
        if self._world_model_unresolved(world_model):
            unresolved_fields.append('UNRESOLVED:world_model')
        live_audit = dict(task_context.live_audit or {})
        ia_trace_summary = self._build_ia_trace_summary(
            task_context=task_context,
            goal_context=goal_context,
            ia_trace=resolved_ia_trace,
            site_id=task_context.site_id,
            user_goal=request.user_goal,
        )
        validation_learning_summary = dict(task_context.metadata.get('validation_learning_summary') or {})
        portable_context_summary = self._portable_context_summary(
            task_context=task_context,
            environment_self_model=environment_self_model,
            world_model=world_model,
        )
        conversation_analysis = dict(intent.metadata.get('conversation_analysis') or {})
        decision_context = DecisionContext(
            user_goal=request.user_goal,
            intent=intent,
            route_decision=resolved_route_decision,
            chosen_pack_id='',
            chosen_pack_title='',
            site_id=task_context.site_id or intent.site_hint or '',
            site_display_name=task_context.site_display_name,
            evidence_refs=list(task_context.evidence_summary),
            capability_snapshot=list(task_context.capability_snapshot),
            live_audit=live_audit,
            assistant_guidance={},
            goal_context=goal_context,
            memory_snapshot=memory_snapshot,
            governance={},
            metadata={
                'decision_stage': 'pre_governance',
                'decision_source': 'task_context_assembler',
                'conversational_prompt': bool(intent.metadata.get('conversational_prompt')),
                'conversation_analysis': conversation_analysis,
                'primary_intent': str(conversation_analysis.get('primary_intent') or intent.intent_key),
                'sub_intents': list(conversation_analysis.get('sub_intents') or []),
                'ambiguity_score': float(conversation_analysis.get('ambiguity_score') or 0.0),
                'requires_clarification': bool(conversation_analysis.get('requires_clarification')),
                'compound_intent': bool(conversation_analysis.get('compound')),
                'constraints': list(conversation_analysis.get('constraints') or []),
                'ia_trace_summary': ia_trace_summary,
                'comparison_scope_key': str(ia_trace_summary.get('comparison_scope_key') or ''),
                'adaptive_learning_summary': dict(task_context.metadata.get('adaptive_learning_summary') or {}),
                'learned_patterns': list(task_context.metadata.get('learned_patterns') or []),
                'validation_learning_summary': validation_learning_summary,
                'world_model_summary': self._world_model_summary(world_model),
                'portable_context_summary': portable_context_summary,
            },
        )
        return PerceptionSnapshot(
            task_context=task_context,
            decision_context=decision_context,
            goal_context=goal_context,
            memory_snapshot=memory_snapshot,
            live_audit=live_audit,
            runtime_signals=resolved_runtime_signals,
            session_health=resolved_session_health,
            ia_trace=resolved_ia_trace,
            visual_signal=resolved_visual_signal,
            environment_self_model=environment_self_model,
            world_model=world_model,
            external_state_flags=self._external_state_flags(
                live_audit=live_audit,
                task_context=task_context,
                ia_trace=resolved_ia_trace,
                session_health=resolved_session_health,
                metadata=request.metadata,
            ),
            unresolved_fields=unresolved_fields,
            metadata={
                'site_id': task_context.site_id or '',
                'conversational_prompt': bool(intent.metadata.get('conversational_prompt')),
                'meta_assistant_prompt': bool(intent.metadata.get('meta_assistant_prompt')),
                'conversation_analysis': conversation_analysis,
                'primary_intent': str(conversation_analysis.get('primary_intent') or intent.intent_key),
                'sub_intents': list(conversation_analysis.get('sub_intents') or []),
                'ambiguity_score': float(conversation_analysis.get('ambiguity_score') or 0.0),
                'requires_clarification': bool(conversation_analysis.get('requires_clarification')),
                'compound_intent': bool(conversation_analysis.get('compound')),
                'constraints': list(conversation_analysis.get('constraints') or []),
                'ia_trace_summary': ia_trace_summary,
                'comparison_scope_key': str(ia_trace_summary.get('comparison_scope_key') or ''),
                'adaptive_learning_summary': dict(task_context.metadata.get('adaptive_learning_summary') or {}),
                'learned_patterns': list(task_context.metadata.get('learned_patterns') or []),
                'validation_learning_summary': validation_learning_summary,
                'environment_id': str(environment_self_model.environment_id or ''),
                'environment_scan_status': str(environment_self_model.scan_status or ''),
                'environment_notifications': list(environment_self_model.notifications or []),
                'world_model_summary': self._world_model_summary(world_model),
                'portable_context_summary': portable_context_summary,
            },
        )

    def _build_task_context(self, *, request: InferenceRequest, intent: TaskIntent) -> TaskContext:
        site_id = intent.site_hint or request.site_hint
        policy = self.site_policy_registry.get_policy(site_id) if site_id else None
        recent_teachings = self._recent_teachings(site_id=site_id, user_goal=request.user_goal)
        recent_runs = self._recent_runs(site_id=site_id)
        recent_dossiers = self._recent_dossiers(site_id=site_id, user_goal=request.user_goal)
        recent_incidents = self._recent_incidents(site_id=site_id)
        recent_incidents = self._recent_incidents(site_id=site_id)
        interaction_patterns = self._recent_interaction_patterns(site_id=site_id, user_goal=request.user_goal)
        goal_context = self._goal_context_snapshot(request=request, intent=intent, site_id=site_id)
        experiment_insights = self._recent_experiment_insights(site_id=site_id, user_goal=request.user_goal, goal_context=goal_context)
        adaptive_learning_summary = self._adaptive_learning_summary(experiment_insights)
        learned_patterns = self._learned_patterns(experiment_insights)
        validation_learning_summary = self._validation_learning_summary()
        live_audit = self._latest_live_audit(site_id=site_id, user_goal=request.user_goal)
        knowledge_hits = self._knowledge_hits(request=request, goal_context=goal_context)
        saved_capabilities = self.capability_repository.find_by_site(site_id or '', limit=8) if site_id else self.capability_repository.list_recent(limit=8)
        recent_sessions = self.adaptive_session_repository.list_recent(limit=8)
        matching_sessions = [
            {
                'session_id': session.session_id,
                'status': session.status.value,
                'intent_key': session.intent.intent_key,
                'pack_id': session.chosen_pack_id,
                'summary': (session.outcome.summary if session.outcome else session.intent.summary),
            }
            for session in recent_sessions
            if not site_id or session.context.site_id == site_id or session.intent.site_hint == site_id
        ][:5]
        evidence_summary = self._build_evidence_summary(
            site_display_name=policy.display_name if policy else (site_id or 'contexto general'),
            recent_teachings=recent_teachings,
            recent_runs=recent_runs,
            recent_incidents=recent_incidents,
            recent_dossiers=recent_dossiers,
            interaction_patterns=interaction_patterns,
            experiment_insights=experiment_insights,
            knowledge_hits=knowledge_hits,
        )
        if live_audit.get('summary'):
            evidence_summary.append(f"Auditoria viva: {live_audit.get('summary')}")
        incident_counter = Counter(item['incident_kind'] for item in recent_incidents if item.get('incident_kind'))
        context = TaskContext(
            site_id=site_id,
            site_display_name=policy.display_name if policy is not None else (site_id or 'General'),
            recent_teachings=recent_teachings,
            recent_runs=recent_runs,
            recent_incidents=recent_incidents,
            recent_dossiers=recent_dossiers,
            knowledge_hits=knowledge_hits,
            capability_snapshot=saved_capabilities,
            interaction_patterns=interaction_patterns,
            experiment_insights=experiment_insights,
            session_readiness={
                'site_detected': bool(site_id),
                'teaching_matches': len(recent_teachings),
                'incident_count': len(recent_incidents),
                'dominant_incident': next(iter(incident_counter.most_common(1)), ('', 0))[0],
                'adaptive_sessions': len(matching_sessions),
                'recent_sessions': matching_sessions,
                'live_audit_action': live_audit.get('decision_action', ''),
            },
            evidence_summary=evidence_summary,
            live_audit=live_audit,
            goal_context=goal_context,
            metadata={
                'policy_notes': policy.notes if policy is not None else '',
                'known_domains': list(policy.domains) if policy is not None else [],
                'live_audit': live_audit,
                'goal_context': goal_context.model_dump(mode='json'),
                'adaptive_learning_summary': adaptive_learning_summary,
                'learned_patterns': learned_patterns,
                'validation_learning_summary': validation_learning_summary,
            },
        )
        portable_context_summary = self._portable_context_summary(task_context=context)
        if portable_context_summary:
            context = context.model_copy(
                update={
                    'metadata': {
                        **context.metadata,
                        'portable_context_summary': portable_context_summary,
                    }
                }
            )
        return context

    def _memory_snapshot(self, context: TaskContext) -> dict[str, Any]:
        if self.unified_memory_layer is not None:
            try:
                return self.unified_memory_layer.build_snapshot(context)
            except Exception:
                pass
        goal_context = context.goal_context.model_dump(mode='json') if isinstance(context.goal_context, GoalContext) else dict(context.goal_context or {})
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
                'capabilities': [item.model_dump(mode='json') for item in context.capability_snapshot],
                'experiment_insights': list(context.experiment_insights),
                'adaptive_learning_summary': dict(context.metadata.get('adaptive_learning_summary') or {}),
                'learned_patterns': list(context.metadata.get('learned_patterns') or []),
                'validation_learning_summary': dict(context.metadata.get('validation_learning_summary') or {}),
            },
            'operational': {
                'recent_runs': list(context.recent_runs),
                'session_readiness': dict(context.session_readiness),
                'live_audit': dict(context.live_audit),
            },
            'objectives': {
                'goal_context': goal_context,
                'objective': dict(goal_context.get('objective') or {}),
                'project': dict(goal_context.get('project') or {}),
                'task': dict(goal_context.get('task') or {}),
                'status': str(goal_context.get('status') or ''),
                'progress': float(goal_context.get('progress') or 0.0),
                'confidence': float(goal_context.get('confidence') or 0.0),
                'blocker': str(goal_context.get('blocker') or ''),
            },
        }

    def _environment_self_model(self) -> EnvironmentSelfModel:
        if self.environment_self_awareness_service is None:
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            model = self.environment_self_awareness_service.current_model()
            self.environment_self_awareness_service.request_refresh(reason='perception_cycle', full=False)
            return model
        except Exception:
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _world_model(self, *, request: InferenceRequest | None = None, intent: TaskIntent | None = None) -> WorldModelSnapshot:
        if self.world_model_service is None:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            full = self._should_force_full_world_model(request=request, intent=intent)
            if full:
                model = self.world_model_service.request_refresh(reason='perception_cycle_full', full=True)
                if model is not None:
                    return model
                fallback = self.world_model_service.current_model()
                return fallback if fallback is not None else WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
            model = self.world_model_service.current_model()
            self.world_model_service.request_refresh(reason='perception_cycle', full=False)
            return model
        except Exception:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _world_model_unresolved(self, world_model: WorldModelSnapshot) -> bool:
        if world_model.tool_live_status or world_model.active_windows or world_model.detected_blocks:
            return False
        return float(world_model.confidence or 0.0) <= 0.05

    def _world_model_summary(self, world_model: WorldModelSnapshot) -> dict[str, Any]:
        by_assistant = {
            item.assistant_kind: item
            for item in world_model.tool_live_status
            if str(item.assistant_kind or '').strip()
        }
        return {
            'focused_window': str((world_model.focused_window.title if world_model.focused_window is not None else '') or ''),
            'network_status': str(world_model.network_status.status or ''),
            'detected_blocks': list(world_model.detected_blocks or []),
            'blocked_routes': [
                {
                    'block_type': item.block_type,
                    'target_scope': item.target_scope,
                    'assistant_kind': item.assistant_kind,
                }
                for item in (world_model.block_records or [])[:8]
            ],
            'permission_gates': [
                {
                    'scope': item.scope,
                    'assistant_kind': item.assistant_kind,
                    'status': item.status,
                }
                for item in (world_model.permission_gates or [])[:6]
            ],
            'active_window_count': len(world_model.active_windows or []),
            'confidence': float(world_model.confidence or 0.0),
            'freshness_ms': int(world_model.freshness_ms or 0),
            'codex_status': {
                'status': str((by_assistant.get('codex').status if by_assistant.get('codex') is not None else '') or ''),
                'thread_status': str((by_assistant.get('codex').thread_status if by_assistant.get('codex') is not None else '') or ''),
                'messages_status': str((by_assistant.get('codex').messages_status if by_assistant.get('codex') is not None else '') or ''),
            },
            'chatgpt_status': self._tool_world_summary(by_assistant.get('chatgpt')),
            'claude_status': self._tool_world_summary(by_assistant.get('claude')),
            'ollama_status': self._tool_world_summary(by_assistant.get('ollama')),
            'last_updated': world_model.last_updated.isoformat() if world_model.last_updated is not None else '',
        }

    def _portable_context_summary(
        self,
        *,
        task_context: TaskContext,
        environment_self_model: EnvironmentSelfModel | None = None,
        world_model: WorldModelSnapshot | None = None,
    ) -> dict[str, Any]:
        service = self.portable_context_service
        if service is None or not hasattr(service, 'current_package') or not hasattr(service, 'package_summary'):
            return {}
        try:
            package = service.current_package(
                task_context=task_context,
                environment_self_model=environment_self_model,
                world_model=world_model,
            )
            summary = service.package_summary(package)
            return dict(summary or {})
        except Exception:
            return {}

    def _tool_world_summary(self, tool: Any) -> dict[str, Any]:
        return {
            'status': str((tool.status if tool is not None else '') or ''),
            'session_status': str((tool.session_status if tool is not None else '') or ''),
            'messages_status': str((tool.messages_status if tool is not None else '') or ''),
            'permission_state': str((tool.permission_state if tool is not None else '') or ''),
            'probe_status': str((tool.probe_status if tool is not None else '') or ''),
        }

    def _should_force_full_world_model(self, *, request: InferenceRequest | None, intent: TaskIntent | None) -> bool:
        if request is None:
            return False
        params = dict(request.goal_parameters or {})
        if bool(params.get('explicit_external_consultation')) or str(params.get('consultation_scope') or '').strip().lower() == 'external_assistant':
            return True
        normalized_goal = ' '.join(str(request.user_goal or '').lower().split())
        if any(
            phrase in normalized_goal
            for phrase in (
                'que esta pasando',
                'qué está pasando',
                'que tienes abierto',
                'qué tienes abierto',
                'por que no responde',
                'por qué no responde',
                'que pasa con mi internet',
                'qué pasa con mi internet',
                'como esta mi internet',
                'cómo está mi internet',
            )
        ):
            return True
        if any(token in normalized_goal for token in ('consulta codex', 'consultar codex', 'consultar chatgpt', 'consultar claude', 'consultar ollama')):
            return True
        if intent is None:
            return False
        return bool(intent.metadata.get('meta_assistant_prompt') or intent.metadata.get('self_awareness_prompt'))

    def _runtime_signals_from_input(self, payload: Any) -> list[RuntimeSignal]:
        items: list[RuntimeSignal] = []
        for entry in payload or []:
            try:
                items.append(entry if isinstance(entry, RuntimeSignal) else RuntimeSignal.model_validate(entry))
            except Exception:
                continue
        return items

    def _session_health_from_input(self, payload: Any) -> SessionHealthSnapshot | None:
        if payload in (None, ''):
            return None
        try:
            return payload if isinstance(payload, SessionHealthSnapshot) else SessionHealthSnapshot.model_validate(payload)
        except Exception:
            return None

    def _ia_trace_from_input(self, payload: Any, *, site_id: str | None, user_goal: str) -> list[IATraceEntry]:
        items: list[IATraceEntry] = []
        for entry in payload or []:
            try:
                items.append(entry if isinstance(entry, IATraceEntry) else IATraceEntry.model_validate(entry))
            except Exception:
                continue
        if items:
            return items
        return self._recent_ia_trace(site_id=site_id, user_goal=user_goal)

    def _visual_signal_from_input(self, payload: Any) -> VisualSignalSnapshot:
        if isinstance(payload, VisualSignalSnapshot):
            return payload
        if not isinstance(payload, dict) or not payload:
            return VisualSignalSnapshot(unresolved_fields=['UNRESOLVED:visual_signal_source'])
        direct_fields = {
            'source',
            'source_app',
            'capture_available',
            'dom_available',
            'latest_url',
            'latest_title',
            'visible_targets',
            'login_detected',
            'learning_ready',
            'cross_check_status',
            'visual_evidence_refs',
            'visual_snapshot',
            'dom_summary',
            'available_actions',
            'detected_blocks',
            'confidence',
            'unresolved_fields',
            'metadata',
        }
        if any(key in payload for key in direct_fields):
            signal = VisualSignalSnapshot.model_validate(payload)
            unresolved = list(signal.unresolved_fields or [])
            if not signal.source:
                signal = signal.model_copy(update={'source': 'request_visual_signal'})
            if not self._visual_signal_available(signal) and 'UNRESOLVED:visual_signal_source' not in unresolved:
                unresolved.append('UNRESOLVED:visual_signal_source')
                signal = signal.model_copy(update={'unresolved_fields': unresolved})
            return signal
        metadata = dict(payload.get('metadata') or {})
        critical_objects = [str(item).strip() for item in (payload.get('critical_objects') or []) if str(item).strip()]
        corrected_objects = [str(item).strip() for item in (payload.get('corrected_objects') or []) if str(item).strip()]
        visible_targets: list[str] = []
        for value in [*critical_objects, *corrected_objects]:
            if value and value not in visible_targets:
                visible_targets.append(value)
        gaps = [str(item).strip() for item in (payload.get('gaps') or []) if str(item).strip()]
        evidence_refs: list[str] = []
        for item in [*(payload.get('visual_evidence_refs') or []), *(metadata.get('audit_findings') or []), *gaps]:
            value = str(item or '').strip()
            if value and value not in evidence_refs:
                evidence_refs.append(value)
        learning_status = str(
            payload.get('cross_check_status')
            or payload.get('learning_status')
            or metadata.get('learning_status')
            or metadata.get('audit_status')
            or ''
        ).strip()
        login_status = str(payload.get('login_status') or metadata.get('login_status') or '').strip().lower()
        learning_ready = bool(
            payload.get('learning_ready')
            or learning_status in {'ready', 'confirmed'}
            or float(payload.get('visual_alignment_score') or 0.0) >= 0.55
            or int(payload.get('green_count') or 0) > 0
        )
        login_detected = bool(
            payload.get('login_detected')
            or login_status in {'ready', 'partial', 'needs_refresh'}
            or float(payload.get('login_visual_completeness') or 0.0) > 0.0
            or any(token in target.lower() for target in visible_targets for token in ('login', 'email', 'correo', 'password', 'contrasena'))
        )
        capture_available = bool(
            payload
            and (
                int(payload.get('green_count') or 0) > 0
                or int(payload.get('orange_count') or 0) > 0
                or int(payload.get('red_count') or 0) > 0
                or int(payload.get('useful_frame_count') or 0) > 0
                or bool(visible_targets)
                or bool(evidence_refs)
            )
        )
        dom_available = bool(
            payload.get('dom_available')
            or metadata.get('dom_available')
            or metadata.get('dom_snapshot_count')
            or metadata.get('observed_page_count')
            or metadata.get('page_count')
        )
        unresolved_fields = list(payload.get('unresolved_fields') or [])
        if not capture_available and 'UNRESOLVED:visual_signal_source' not in unresolved_fields:
            unresolved_fields.append('UNRESOLVED:visual_signal_source')
        return VisualSignalSnapshot(
            source=str(payload.get('source') or metadata.get('source') or 'replay_visual_summary'),
            source_app=str(payload.get('source_app') or metadata.get('source_app') or metadata.get('site_id') or 'browser_page'),
            capture_available=capture_available,
            dom_available=dom_available,
            latest_url=str(payload.get('latest_url') or metadata.get('last_active_url') or ''),
            latest_title=str(payload.get('latest_title') or metadata.get('latest_title') or ''),
            visible_targets=visible_targets[:8],
            login_detected=login_detected,
            learning_ready=learning_ready,
            cross_check_status=learning_status,
            visual_evidence_refs=evidence_refs[:8],
            visual_snapshot={
                'status': 'available' if capture_available else 'no_disponible',
                'capture_mode': 'replay_visual_summary',
                'screen_capture': 'available' if capture_available else 'no_disponible',
                'green_count': int(payload.get('green_count') or 0),
                'orange_count': int(payload.get('orange_count') or 0),
                'red_count': int(payload.get('red_count') or 0),
            },
            dom_summary={
                'status': 'available' if dom_available else 'no_disponible',
                'reason': '' if dom_available else 'dom_not_exposed_in_current_capture',
                'dom_available': dom_available,
                'node_count': int(metadata.get('dom_node_count') or 0),
                'observed_page_count': int(metadata.get('observed_page_count') or metadata.get('page_count') or 0),
            },
            available_actions=[
                {'action': 'interact_visible_target', 'label': target, 'target': target, 'available': capture_available}
                for target in visible_targets[:4]
            ],
            detected_blocks=canonical_external_state_flags(list(payload.get('detected_blocks') or metadata.get('detected_blocks') or [])),
            confidence=float(payload.get('confidence') or metadata.get('confidence') or (0.45 if capture_available else 0.1)),
            unresolved_fields=unresolved_fields,
            metadata={
                'visual_alignment_score': float(payload.get('visual_alignment_score') or 0.0),
                'learning_coverage_score': float(payload.get('learning_coverage_score') or 0.0),
                'green_count': int(payload.get('green_count') or 0),
                'orange_count': int(payload.get('orange_count') or 0),
                'red_count': int(payload.get('red_count') or 0),
                'manual_correction_count': int(payload.get('manual_correction_count') or 0),
                'critical_object_coverage': float(payload.get('critical_object_coverage') or 0.0),
                'login_visual_completeness': float(payload.get('login_visual_completeness') or 0.0),
                'gaps': gaps[:8],
                'audit_status': str(metadata.get('audit_status') or ''),
            },
        )

    def _recent_ia_trace(self, *, site_id: str | None, user_goal: str) -> list[IATraceEntry]:
        if self.tool_record_repository is None:
            return []
        goal_tokens = {token for token in str(user_goal or '').lower().split() if len(token) >= 4}
        items: list[IATraceEntry] = []
        for task in self.tool_record_repository.list_tasks(limit=20):
            metadata = dict(task.metadata or {})
            assistant_kind = str(metadata.get('actual_assistant_kind') or metadata.get('assistant_kind') or metadata.get('requested_assistant_kind') or '')
            if not assistant_kind and not any(marker in str(task.tool_id or '').lower() for marker in ('codex', 'chatgpt', 'claude', 'ollama')):
                continue
            if site_id and task.site_id and task.site_id != site_id:
                continue
            objective_tokens = {token for token in str(task.objective or '').lower().split() if len(token) >= 4}
            if goal_tokens and objective_tokens and not goal_tokens.intersection(objective_tokens):
                continue
            latest_result = next(iter(self.tool_record_repository.list_results(task_id=task.task_id, limit=1)), None)
            result_metadata = dict(latest_result.metadata or {}) if latest_result is not None else {}
            stored_trace = result_metadata.get('ia_trace_entry') or metadata.get('ia_trace_entry') or (result_metadata.get('autonomous_consultation') or {}).get('ia_trace_entry') or (metadata.get('autonomous_consultation') or {}).get('ia_trace_entry')
            if stored_trace:
                try:
                    entry = IATraceEntry.model_validate(stored_trace)
                    items.append(
                        entry.model_copy(
                            update={
                                'task_id': entry.task_id or task.task_id,
                                'result_id': entry.result_id or (latest_result.result_id if latest_result is not None else ''),
                                'tool_id': entry.tool_id or str(task.tool_id or ''),
                                'comparison_scope_key': entry.comparison_scope_key
                                or self._comparison_scope_key_from_trace_metadata(
                                    task_metadata=metadata,
                                    result_metadata=result_metadata,
                                    site_id=task.site_id,
                                    user_goal=str(task.objective or user_goal),
                                ),
                            }
                        )
                    )
                    if len(items) >= 6:
                        break
                    continue
                except Exception:
                    pass
            coherence_flags = [
                str(flag)
                for flag in (
                    result_metadata.get('coherence_flags')
                    or metadata.get('coherence_flags')
                    or result_metadata.get('external_state_flags')
                    or metadata.get('external_state_flags')
                    or []
                )
                if str(flag).strip()
            ]
            detail = str(
                (latest_result.execution_state.detail if latest_result is not None and latest_result.execution_state is not None else '')
                or result_metadata.get('awaiting_reason')
                or metadata.get('awaiting_reason')
                or ''
            )
            state = str(
                (latest_result.execution_state.state if latest_result is not None and latest_result.execution_state is not None else '')
                or metadata.get('status')
                or ''
            )
            assistant_configuration = self._assistant_configuration_from_trace_payload(result_metadata, metadata)
            config_signature = str(
                result_metadata.get('config_signature')
                or metadata.get('config_signature')
                or self._config_signature(assistant_configuration)
            )
            external_state_flags = self._normalize_external_state_flags(
                [
                    state,
                    *(result_metadata.get('external_state_flags') or []),
                    *(metadata.get('external_state_flags') or []),
                    *coherence_flags,
                    result_metadata,
                    metadata,
                ]
            )
            items.append(
                IATraceEntry(
                    assistant_kind=assistant_kind or self._assistant_kind_from_tool_id(task.tool_id),
                    requested_assistant_kind=str(metadata.get('requested_assistant_kind') or metadata.get('assistant_kind') or ''),
                    actual_assistant_kind=str(metadata.get('actual_assistant_kind') or assistant_kind or self._assistant_kind_from_tool_id(task.tool_id)),
                    assistant_configuration=assistant_configuration,
                    config_signature=config_signature,
                    comparison_scope_key=self._comparison_scope_key_from_trace_metadata(
                        task_metadata=metadata,
                        result_metadata=result_metadata,
                        site_id=task.site_id,
                        user_goal=str(task.objective or user_goal),
                    ),
                    source_trace_ids=[str(item) for item in (result_metadata.get('source_trace_ids') or metadata.get('source_trace_ids') or []) if str(item).strip()],
                    route=self._route_for_trace(tool_id=task.tool_id, assistant_kind=assistant_kind or self._assistant_kind_from_tool_id(task.tool_id)),
                    tool_id=str(task.tool_id or ''),
                    task_id=task.task_id,
                    result_id=latest_result.result_id if latest_result is not None else '',
                    session_scope=str(metadata.get('session_scope') or ''),
                    thread_key=str(metadata.get('thread_key') or ''),
                    thread_title=str(metadata.get('thread_title') or ''),
                    capture_lane=str(metadata.get('capture_lane') or ''),
                    state=state,
                    detail=detail,
                    proposal_summary=self._compact_summary(result_metadata.get('proposal_summary') or metadata.get('proposal_summary') or metadata.get('context_pack') or task.objective),
                    outcome_summary=self._compact_summary(result_metadata.get('outcome_summary') or result_metadata.get('response_summary') or (latest_result.output_text if latest_result is not None else '') or detail),
                    result_label=str((latest_result.output_text if latest_result is not None else '') or detail or state)[:240],
                    success=bool(latest_result.success) if latest_result is not None else False,
                    execution_ms=int((latest_result.execution_ms if latest_result is not None else 0) or result_metadata.get('execution_ms') or metadata.get('execution_ms') or 0),
                    confidence=float(result_metadata.get('response_confidence') or result_metadata.get('confidence') or metadata.get('confidence') or 0.0),
                    evidence_refs=[
                        item
                        for item in [
                            str(result_metadata.get('pending_issue_id') or metadata.get('pending_issue_id') or ''),
                            task.task_id,
                            latest_result.result_id if latest_result is not None else '',
                            str(task.site_id or ''),
                        ]
                        if str(item).strip()
                    ],
                    reused_later=bool(result_metadata.get('reused_later', metadata.get('reuse_guard_active', False))),
                    verdict=str(result_metadata.get('validation_status') or result_metadata.get('adoption_status') or state or ''),
                    coherence_flags=coherence_flags,
                    external_state_flags=external_state_flags,
                    metadata={
                        'site_id': str(task.site_id or ''),
                        'response_capture_mode': str(metadata.get('response_capture_mode') or ''),
                        'background_capture_mode': str(metadata.get('background_capture_mode') or ''),
                    },
                )
            )
            if len(items) >= 6:
                break
        if len(items) < 6:
            for log in self.tool_record_repository.list_log(limit=20):
                payload = dict(log.get('payload') or {})
                stored_trace = payload.get('ia_trace_entry') or (payload.get('guided_improvement_cycle') or {}).get('ia_trace_entry')
                if not stored_trace:
                    continue
                try:
                    entry = IATraceEntry.model_validate(stored_trace)
                except Exception:
                    continue
                trace_site = str(entry.metadata.get('site_id') or payload.get('site_id') or '').strip()
                if site_id and trace_site and trace_site != site_id:
                    continue
                trace_goal_tokens = {token for token in str(entry.outcome_summary or entry.proposal_summary or '').lower().split() if len(token) >= 4}
                site_matched = bool(site_id and trace_site and trace_site == site_id)
                if goal_tokens and trace_goal_tokens and not goal_tokens.intersection(trace_goal_tokens) and not site_matched:
                    continue
                if any(existing.trace_id == entry.trace_id for existing in items if str(entry.trace_id).strip()):
                    continue
                items.append(entry)
                if len(items) >= 6:
                    break
        return items

    def _assistant_kind_from_tool_id(self, tool_id: str) -> str:
        tool_text = str(tool_id or '').strip().lower()
        if tool_text.startswith('codex'):
            return 'codex'
        if tool_text.startswith('chatgpt'):
            return 'chatgpt'
        if tool_text.startswith('claude'):
            return 'claude'
        if tool_text.startswith('ollama'):
            return 'ollama'
        return ''

    def _external_state_flags(
        self,
        *,
        live_audit: dict[str, Any],
        task_context: TaskContext,
        ia_trace: list[IATraceEntry],
        session_health: SessionHealthSnapshot | None,
        metadata: dict[str, Any] | None,
    ) -> list[str]:
        flags: list[str] = []
        sources: list[Any] = [live_audit.get('findings'), live_audit.get('decision_action'), task_context.session_readiness.get('live_audit_action'), metadata or {}]
        if session_health is not None:
            sources.append(session_health.health_flags)
            sources.append(session_health.metrics)
            sources.append(session_health.detail)
        for trace in ia_trace:
            sources.append(trace.external_state_flags)
            sources.append(trace.coherence_flags)
            sources.append(trace.metadata)
            sources.append(trace.state)
            sources.append(trace.detail)
            sources.append(trace.verdict)
        for source in sources:
            for value in self._iter_external_state_values(source):
                normalized = canonical_external_state_flag(value)
                if normalized and normalized not in flags:
                    flags.append(normalized)
        return flags

    def _assistant_configuration_from_trace_payload(self, result_metadata: dict[str, Any], task_metadata: dict[str, Any]) -> AssistantConfigurationSnapshot:
        for payload in (result_metadata.get('assistant_configuration'), task_metadata.get('assistant_configuration')):
            if isinstance(payload, AssistantConfigurationSnapshot):
                return payload
            if isinstance(payload, dict) and payload:
                try:
                    return AssistantConfigurationSnapshot.model_validate(payload)
                except Exception:
                    continue
        return AssistantConfigurationSnapshot()

    def _config_signature(self, configuration: AssistantConfigurationSnapshot) -> str:
        return '|'.join(
            [
                configuration.planning_mode,
                configuration.attachments_mode,
                configuration.reasoning_level,
                configuration.context_mode,
                configuration.tools_mode,
                configuration.browser_mode,
                configuration.assistant_mode,
                configuration.origin_mode,
            ]
        )

    def _compact_summary(self, text: Any, *, limit: int = 240) -> str:
        return ' '.join(str(text or '').split())[:limit]

    def _fallback_comparison_scope_key(self, *, site_id: str | None, user_goal: str) -> str:
        prefix = str(site_id or 'general').strip() or 'general'
        compact = '-'.join(
            token
            for token in (
                ''.join(character for character in raw if character.isalnum())
                for raw in str(user_goal or '').lower().split()
            )
            if token
        )[:72].strip('-')
        return f'{prefix}:{compact or "general"}'

    def _comparison_scope_key_from_trace_metadata(
        self,
        *,
        task_metadata: dict[str, Any],
        result_metadata: dict[str, Any],
        site_id: str | None,
        user_goal: str,
    ) -> str:
        payload = {**task_metadata, **result_metadata}
        objective = dict(payload.get('objective') or {})
        project = dict(payload.get('project') or {})
        task = dict(payload.get('task') or {})
        for candidate in (
            str(payload.get('comparison_scope_key') or ''),
            str(payload.get('pending_issue_id') or ''),
            str(task.get('objective_id') or ''),
            str(project.get('objective_id') or ''),
            str(objective.get('objective_id') or ''),
            str(payload.get('task_id') or ''),
            str(payload.get('project_id') or ''),
            str(payload.get('objective_id') or ''),
            str(payload.get('subject_key') or ''),
        ):
            probe = candidate.strip()
            if probe:
                return probe
        return self._fallback_comparison_scope_key(site_id=site_id, user_goal=user_goal)

    def _build_ia_trace_summary(
        self,
        *,
        task_context: TaskContext,
        goal_context: GoalContext,
        ia_trace: list[IATraceEntry],
        site_id: str | None,
        user_goal: str,
    ) -> dict[str, Any]:
        assistant_traces = [
            trace
            for trace in ia_trace
            if str(trace.assistant_kind or '').strip().lower() not in {'self_teach', 'guided_self_improvement'}
            and str(trace.metadata.get('trace_role') or '').strip().lower() != 'guided_improvement'
        ]
        comparison_scope_keys = [
            key
            for key in dict.fromkeys(
                [
                    *(trace.comparison_scope_key for trace in ia_trace if str(trace.comparison_scope_key).strip()),
                    *(item.get('subject_key') for item in task_context.experiment_insights if str(item.get('subject_key') or '').strip()),
                    *self._experiment_subject_keys(site_id=site_id, goal_context=goal_context, user_goal=user_goal),
                ]
            )
            if str(key).strip()
        ]
        best_insight = next((item for item in task_context.experiment_insights if item.get('recommended_assistant_kind') or item.get('recommended_config_signature')), {})
        best_trace = next(
            iter(
                sorted(
                    assistant_traces,
                    key=lambda item: (
                        1 if item.reused_later else 0,
                        1 if item.success else 0,
                        float(item.confidence or 0.0),
                        -int(item.execution_ms or 0),
                    ),
                    reverse=True,
                )
            ),
            None,
        )
        blocked_assistants = [
            assistant
            for assistant in dict.fromkeys(
                str(trace.actual_assistant_kind or trace.assistant_kind or '').strip().lower()
                for trace in assistant_traces
                if trace.external_state_flags
            )
            if assistant
        ]
        reusable_trace_ids = [
            trace_id
            for trace_id in dict.fromkeys(
                trace.trace_id
                for trace in ia_trace
                if str(trace.trace_id).strip() and (trace.reused_later or (trace.success and not trace.external_state_flags))
            )
            if trace_id
        ][:8]
        return {
            'comparison_scope_key': comparison_scope_keys[0] if comparison_scope_keys else self._fallback_comparison_scope_key(site_id=site_id, user_goal=user_goal),
            'comparison_scope_keys': comparison_scope_keys[:6],
            'latest_trace_ids': [trace.trace_id for trace in ia_trace if str(trace.trace_id).strip()][:6],
            'tested_assistants': [
                assistant
                for assistant in dict.fromkeys(
                    str(trace.actual_assistant_kind or trace.assistant_kind or '').strip().lower()
                    for trace in assistant_traces
                )
                if assistant
            ],
            'best_assistant_kind': str(best_insight.get('recommended_assistant_kind') or (best_trace.assistant_kind if best_trace is not None else '') or ''),
            'best_config_signature': str(best_insight.get('recommended_config_signature') or (best_trace.config_signature if best_trace is not None else '') or ''),
            'blocked_assistants': blocked_assistants,
            'reusable_trace_ids': reusable_trace_ids,
            'winning_trace_ids': list(best_insight.get('winning_trace_ids') or dict(best_insight.get('metadata') or {}).get('winning_trace_ids') or [])[:8],
            'losing_trace_ids': list(best_insight.get('losing_trace_ids') or dict(best_insight.get('metadata') or {}).get('losing_trace_ids') or [])[:8],
        }

    def _adaptive_learning_summary(self, experiment_insights: list[dict[str, Any]]) -> dict[str, Any]:
        best = next(iter(experiment_insights), None)
        if not best:
            return {}
        metadata = dict(best.get('metadata') or {})
        summary = dict(metadata.get('adaptive_learning_summary') or {})
        return {
            'subject_key': str(best.get('subject_key') or ''),
            'domain': str(best.get('domain') or ''),
            'recommended_route': str(best.get('recommended_route') or ''),
            'recommended_assistant_kind': str(best.get('recommended_assistant_kind') or ''),
            'confidence': float(best.get('confidence') or 0.0),
            'score': float(best.get('score') or 0.0),
            'reasons': list(summary.get('reasons') or []),
            'top_environment_signatures': list(summary.get('top_environment_signatures') or []),
            'top_time_buckets': list(summary.get('top_time_buckets') or []),
        }

    def _learned_patterns(self, experiment_insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for insight in experiment_insights[:3]:
            metadata = dict(insight.get('metadata') or {})
            adaptive = dict(metadata.get('adaptive_learning_summary') or {})
            items.append(
                {
                    'subject_key': str(insight.get('subject_key') or ''),
                    'domain': str(insight.get('domain') or ''),
                    'recommended_route': str(insight.get('recommended_route') or ''),
                    'recommended_assistant_kind': str(insight.get('recommended_assistant_kind') or ''),
                    'reasons': list(adaptive.get('reasons') or []),
                }
            )
        return items

    def _validation_learning_summary(self) -> dict[str, Any]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_snapshot'):
            return {}
        try:
            snapshot = service.current_snapshot()
        except Exception:
            return {}
        experiment = snapshot.current_experiment
        sync_pulse = dict((snapshot.metadata or {}).get('sync_pulse') or {})
        result: dict[str, Any] = {
            'status': str(snapshot.status or ''),
            'summary': str(snapshot.summary or ''),
            'paused_reason': str(snapshot.paused_reason or ''),
            'pending_candidates': int(snapshot.pending_candidates or 0),
            'promoted_count': int(snapshot.promoted_count or 0),
            'last_experiment_id': str(snapshot.last_experiment_id or ''),
            'subject_key': str((experiment.subject_key if experiment is not None else '') or ''),
            'candidate_route': getattr((experiment.candidate_route if experiment is not None else None), 'value', str((experiment.candidate_route if experiment is not None else '') or '')),
            'candidate_assistant_kind': str((experiment.candidate_assistant_kind if experiment is not None else '') or ''),
            'verdict': getattr((experiment.verdict if experiment is not None else None), 'value', str((experiment.verdict if experiment is not None else '') or '')),
            'promote_to_primary': bool(experiment.promote_to_primary) if experiment is not None else False,
        }
        if sync_pulse:
            result['ia_availability'] = sync_pulse.get('ia_availability') or {}
            result['top_recommendations'] = sync_pulse.get('top_recommendations') or []
            result['active_proposals'] = sync_pulse.get('active_proposals') or []
            result['coordination_status'] = str(sync_pulse.get('coordination_status') or '')
        return result

    def _route_for_trace(self, *, tool_id: str, assistant_kind: str) -> str:
        resolved_tool_id = str(tool_id or '').strip().lower()
        resolved_assistant = str(assistant_kind or '').strip().lower()
        if resolved_tool_id in {'chatgpt_web_assisted', 'claude_web_assisted'}:
            return EvaluationRoute.UI.value
        if resolved_assistant == 'codex':
            return EvaluationRoute.CODE_AGENT.value
        if resolved_assistant == 'ollama':
            return EvaluationRoute.LOCAL.value
        if resolved_assistant in {'chatgpt', 'claude'}:
            return EvaluationRoute.LANGUAGE_UNDERSTANDING.value
        return EvaluationRoute.FALLBACK.value

    def _normalize_external_state_flags(self, values: list[Any]) -> list[str]:
        flags: list[str] = []
        for value in values:
            for candidate in self._iter_external_state_values(value):
                normalized = canonical_external_state_flag(candidate)
                if normalized and normalized not in flags:
                    flags.append(normalized)
        return flags

    def _iter_external_state_values(self, source: Any) -> list[Any]:
        values: list[Any] = []
        if isinstance(source, dict):
            for key, value in source.items():
                key_text = str(key or '').strip()
                normalized_key = canonical_external_state_flag(key_text)
                if normalized_key and bool(value):
                    values.append(normalized_key)
                if key_text in {'external_state_flags', 'coherence_flags', 'health_flags'} and isinstance(value, (list, tuple, set)):
                    values.extend(list(value))
                elif key_text in {'status', 'state', 'awaiting_reason', 'auto_capture_reason', 'detail'}:
                    values.append(value)
                else:
                    values.append(value)
            if source.get('response_capture_pending'):
                values.append(ExternalStateFlag.AWAITING_RESPONSE.value)
        elif isinstance(source, (list, tuple, set)):
            values.extend(list(source))
        else:
            values.append(source)
        return values

    def _visual_signal_available(self, signal: VisualSignalSnapshot) -> bool:
        return bool(
            signal.capture_available
            or signal.dom_available
            or signal.source_app
            or signal.latest_url
            or signal.latest_title
            or signal.visible_targets
            or signal.visual_evidence_refs
            or signal.visual_snapshot
            or signal.available_actions
            or signal.detected_blocks
        )

    def _recent_teachings(self, *, site_id: str | None, user_goal: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        user_goal_lower = user_goal.lower()
        for manifest in self.episode_repository.list_recent(limit=16):
            steps = self.episode_repository.load_episode(manifest.episode_id)
            signals = self._teaching_signals(steps)
            learning_bundle = self._load_learning_bundle(manifest.episode_id)
            teaching_brief = self._load_teaching_brief(manifest.episode_id)
            visual_summary = dict(learning_bundle.get('visual_summary') or {})
            derived_visual_summary = self._derive_teaching_visual_summary(steps) if self._visual_summary_needs_refresh(visual_summary) else {}
            if self._visual_summary_score(derived_visual_summary) > self._visual_summary_score(visual_summary):
                visual_summary = {**visual_summary, **derived_visual_summary}
            if site_id and site_id != 'generic_web':
                site_match = signals['site_hits'].get(site_id, 0) > 0 or site_id in manifest.title.lower() or site_id in ' '.join(manifest.tags).lower()
                if not site_match:
                    continue
            elif not signals['site_hits'] and len(items) >= 6:
                continue
            if not site_id and user_goal_lower:
                if not any(token in user_goal_lower for token in signals['tokens'][:8]) and len(items) >= 6:
                    continue
            login_learning = dict(learning_bundle.get('login_learning') or {})
            readiness = dict(learning_bundle.get('learning_readiness') or {})
            login_status = login_learning.get('status', signals['login_status'])
            learning_status = readiness.get('status', signals['learning_status'])
            if signals['login_status'] == 'ready' and self._teaching_visual_ready(visual_summary):
                login_status = 'ready'
            elif self._status_rank(signals['login_status']) > self._status_rank(login_status):
                login_status = signals['login_status']
            if signals['learning_status'] == 'ready' and self._teaching_visual_ready(visual_summary):
                learning_status = 'ready'
            elif self._status_rank(signals['learning_status']) > self._status_rank(learning_status):
                learning_status = signals['learning_status']
            item = {
                'episode_id': manifest.episode_id,
                'title': manifest.title,
                'target_label': teaching_brief.get('target_label', ''),
                'start_url': teaching_brief.get('start_url', ''),
                'objective': teaching_brief.get('objective', ''),
                'expected_outcome': teaching_brief.get('expected_outcome', ''),
                'notes': teaching_brief.get('notes', ''),
                'updated_at_utc': manifest.updated_at_utc.isoformat(),
                'step_count': manifest.step_count,
                'relevant_steps': signals['relevant_steps'],
                'login_status': login_status,
                'learning_status': learning_status,
                'signals': list(dict.fromkeys(signals['signal_labels'] + list(login_learning.get('signals') or []))),
                'sites': dict(signals['site_hits']),
                'learning_coverage_score': max(
                    float(readiness.get('learning_coverage_score', 0.0) or 0.0),
                    float(visual_summary.get('learning_coverage_score', 0.0) or 0.0),
                ),
                'visual_alignment_score': max(
                    float(readiness.get('visual_alignment_score', 0.0) or 0.0),
                    float(visual_summary.get('visual_alignment_score', 0.0) or 0.0),
                ),
                'manual_correction_count': max(
                    int(readiness.get('manual_correction_count', 0) or 0),
                    int(visual_summary.get('manual_correction_count', 0) or 0),
                ),
                'critical_object_coverage': max(
                    float(readiness.get('critical_object_coverage', 0.0) or 0.0),
                    float(visual_summary.get('critical_object_coverage', 0.0) or 0.0),
                ),
                'login_visual_completeness': max(
                    float(login_learning.get('login_visual_completeness', 0.0) or 0.0),
                    float(visual_summary.get('login_visual_completeness', 0.0) or 0.0),
                ),
                'green_count': int(visual_summary.get('green_count', 0) or 0),
                'orange_count': int(visual_summary.get('orange_count', 0) or 0),
                'red_count': int(visual_summary.get('red_count', 0) or 0),
                'critical_objects': list(visual_summary.get('critical_objects') or []),
                'corrected_objects': list(visual_summary.get('corrected_objects') or []),
                'gaps': list(visual_summary.get('gaps') or []),
            }
            items.append(item)
            if len(items) >= 8:
                break
        return items

    def _recent_runs(self, *, site_id: str | None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for record in self.run_repository.list_recent(limit=12):
            adaptive = record.result.raw_output.get('adaptive_session') if isinstance(record.result.raw_output, dict) else None
            if site_id and adaptive:
                adaptive_site = (adaptive.get('context') or {}).get('site_id') or (adaptive.get('intent') or {}).get('site_hint')
                if adaptive_site and adaptive_site != site_id:
                    continue
            items.append(
                {
                    'run_id': record.run_id,
                    'status': record.status.value,
                    'summary': record.result.summary[:220],
                    'role': (record.result.detected_role or getattr(record.route, 'task_role', None)).value if (record.result.detected_role or getattr(record.route, 'task_role', None)) else 'training',
                    'model': record.result.executor_model or getattr(record.route, 'model_name', ''),
                    'pack_id': adaptive.get('chosen_pack_id', '') if isinstance(adaptive, dict) else '',
                }
            )
        return items[:8]

    def _recent_dossiers(self, *, site_id: str | None, user_goal: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        goal_lower = user_goal.lower()
        for dossier in self.dossier_repository.list_recent(limit=12):
            adaptive = dossier.metadata.get('adaptive_session') if isinstance(dossier.metadata, dict) else None
            if site_id and isinstance(adaptive, dict):
                adaptive_site = (adaptive.get('context') or {}).get('site_id') or (adaptive.get('intent') or {}).get('site_hint')
                if adaptive_site and adaptive_site != site_id:
                    continue
            if goal_lower and not any(term in dossier.summary.lower() for term in goal_lower.split()[:4]) and len(items) >= 5:
                continue
            items.append(
                {
                    'dossier_id': dossier.dossier_id,
                    'summary': dossier.summary[:220],
                    'severity': dossier.severity.value,
                    'status': dossier.status.value,
                    'issue_hint': dossier.issue_hint_text,
                }
            )
            if len(items) >= 6:
                break
        return items

    def _recent_incidents(self, *, site_id: str | None) -> list[dict[str, Any]]:
        incidents = self.hidden_incident_repository.list_recent(limit=18)
        if site_id:
            incidents = [item for item in incidents if item.site_id == site_id][:10]
        return [self._incident_payload(item) for item in incidents[:8]]

    def _recent_interaction_patterns(self, *, site_id: str | None, user_goal: str) -> list[dict[str, Any]]:
        if self.tool_record_repository is None:
            return []
        patterns = self.tool_record_repository.list_interaction_patterns(site_id=site_id, limit=20) if site_id else self.tool_record_repository.list_interaction_patterns(limit=20)
        goal_tokens = {token for token in user_goal.lower().split() if len(token) >= 3}
        items: list[dict[str, Any]] = []
        for pattern in patterns:
            pattern_tokens = {token for token in (pattern.title + ' ' + str(pattern.metadata.get('objective_excerpt') or '')).lower().split() if len(token) >= 3}
            if goal_tokens and not goal_tokens.intersection(pattern_tokens) and len(items) >= 4:
                continue
            items.append(
                {
                    'pattern_id': pattern.pattern_id,
                    'title': pattern.title,
                    'channel': pattern.channel.value,
                    'tool_id': pattern.tool_id,
                    'site_id': pattern.site_id or '',
                    'operation_count': len(pattern.operations),
                    'success_count': pattern.success_count,
                    'failure_count': pattern.failure_count,
                    'reusable': pattern.reusable,
                }
            )
            if len(items) >= 6:
                break
        return items

    def _recent_experiment_insights(self, *, site_id: str | None, user_goal: str, goal_context: GoalContext) -> list[dict[str, Any]]:
        if self.experiment_lab_repository is None:
            return []
        domains = self._inferred_experiment_domains(user_goal)
        subject_keys = self._experiment_subject_keys(site_id=site_id, goal_context=goal_context, user_goal=user_goal)
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for subject_key in subject_keys:
            for domain in domains:
                recommendations = self.experiment_lab_repository.list_recommendations(domain=domain.value, subject_key=subject_key, limit=3)
                for recommendation in recommendations:
                    signature = f"{recommendation.domain.value}:{recommendation.subject_key}:{recommendation.recommended_route.value}"
                    if signature in seen:
                        continue
                    seen.add(signature)
                    items.append(
                        {
                            'recommendation_id': recommendation.recommendation_id,
                            'domain': recommendation.domain.value,
                            'subject_key': recommendation.subject_key,
                            'recommended_route': recommendation.recommended_route.value,
                            'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                            'recommended_assistant_configuration': recommendation.recommended_assistant_configuration.model_dump(mode='json'),
                            'recommended_config_signature': recommendation.recommended_config_signature,
                            'score': recommendation.score,
                            'confidence': recommendation.confidence,
                            'rationale': recommendation.rationale,
                            'supporting_run_ids': list(recommendation.supporting_run_ids),
                            'winning_trace_ids': list((recommendation.metadata or {}).get('winning_trace_ids') or []),
                            'losing_trace_ids': list((recommendation.metadata or {}).get('losing_trace_ids') or []),
                            'comparison_scope_keys': list((recommendation.metadata or {}).get('comparison_scope_keys') or []),
                            'metadata': dict(recommendation.metadata or {}),
                        }
                    )
                    if len(items) >= 6:
                        return items
        return items

    def _experiment_subject_keys(self, *, site_id: str | None, goal_context: GoalContext, user_goal: str) -> list[str]:
        keys: list[str] = []
        objective = dict(goal_context.objective or {})
        project = dict(goal_context.project or {})
        task = dict(goal_context.task or {})
        for candidate in (
            self._fallback_comparison_scope_key(site_id=site_id, user_goal=user_goal),
            str(task.get('objective_id') or ''),
            str(project.get('objective_id') or ''),
            str(objective.get('objective_id') or ''),
            str(goal_context.active_node_id or ''),
            str(site_id or ''),
            'general',
        ):
            probe = candidate.strip()
            if probe and probe not in keys:
                keys.append(probe)
        return keys
    def _inferred_experiment_domains(self, user_goal: str) -> list[ExperimentDomain]:
        text = user_goal.lower()
        domains: list[ExperimentDomain] = []
        if any(token in text for token in ['ecuacion', 'equation', 'formula', 'matematic', 'simbolic', 'logica']):
            domains.extend([ExperimentDomain.EQUATION, ExperimentDomain.FORMULA, ExperimentDomain.SYMBOLIC_LOGIC])
        if any(token in text for token in ['ocr', 'texto en imagen', 'texto de imagen', 'vision', 'objeto', 'detectar objeto']):
            domains.extend([ExperimentDomain.OCR, ExperimentDomain.OBJECT_DETECTION])
        if any(token in text for token in ['lenguaje', 'resumen', 'clasifica', 'intencion', 'texto']):
            domains.append(ExperimentDomain.LANGUAGE)
        if any(token in text for token in ['codigo', 'code', 'algoritmo', 'algorithm', 'patch', 'bug']):
            domains.extend([ExperimentDomain.CODE, ExperimentDomain.ALGORITHM])
        if not domains:
            domains.append(ExperimentDomain.LANGUAGE)
        ordered: list[ExperimentDomain] = []
        for domain in domains:
            if domain not in ordered:
                ordered.append(domain)
        return ordered

    def _knowledge_hits(self, *, request: InferenceRequest, goal_context: GoalContext) -> list[dict[str, Any]]:
        terms = self._knowledge_search_terms(request=request, goal_context=goal_context)
        seen: dict[str, dict[str, Any]] = {}
        for term in terms:
            for item in self.knowledge_repository.search(term, limit=5):
                if item.knowledge_id in seen:
                    continue
                seen[item.knowledge_id] = {
                    'knowledge_id': item.knowledge_id,
                    'title': item.title,
                    'summary': item.summary,
                    'confidence': item.confidence,
                    'tags': list(item.tags),
                }
                if len(seen) >= 8:
                    return list(seen.values())
        return list(seen.values())

    def _knowledge_search_terms(self, *, request: InferenceRequest, goal_context: GoalContext) -> list[str]:
        terms: list[str] = []
        for value in (
            request.user_goal,
            str(request.goal_parameters.get('objective_title') or ''),
            str(request.goal_parameters.get('project_title') or ''),
            str(request.goal_parameters.get('task_title') or ''),
            str(request.goal_parameters.get('objective_id') or ''),
            str(request.goal_parameters.get('project_id') or ''),
            str(request.goal_parameters.get('task_id') or ''),
            str(dict(goal_context.objective).get('title') or ''),
            str(dict(goal_context.project).get('title') or ''),
            str(dict(goal_context.task).get('title') or ''),
            str(dict(goal_context.objective).get('objective_id') or ''),
            str(dict(goal_context.project).get('objective_id') or ''),
            str(dict(goal_context.task).get('objective_id') or ''),
        ):
            probe = ' '.join(str(value or '').strip().split())
            if probe and probe not in terms:
                terms.append(probe)
        return terms

    def _incident_payload(self, incident: HiddenIncident) -> dict[str, Any]:
        return {
            'incident_id': incident.incident_id,
            'incident_kind': incident.incident_kind,
            'summary': incident.summary,
            'severity': incident.severity.value,
            'status': incident.status.value,
            'site_id': incident.site_id,
            'affected_url': incident.affected_url,
        }

    def _teaching_signals(self, steps: list[Any]) -> dict[str, Any]:
        site_hits: Counter = Counter()
        signal_labels: list[str] = []
        tokens: list[str] = []
        relevant_steps = 0
        email = False
        password = False
        submit = False
        authenticated = False
        casino = False
        search_google = False
        for step in steps:
            metadata = getattr(step, 'metadata', {}) or {}
            text_chunks = [
                str(getattr(step, 'action_type', '') or ''),
                str(getattr(step, 'target', '') or ''),
                str(metadata.get('field_role') or metadata.get('element_role') or ''),
                str(metadata.get('selector') or ''),
                str(metadata.get('url') or metadata.get('frame_url') or ''),
                str(metadata.get('textPreview') or metadata.get('button_text') or ''),
            ]
            lower = ' '.join(text_chunks).lower()
            tokens.extend([token for token in lower.split() if token])
            for site in ('wplay', 'mercadolibre', 'google'):
                if site in lower:
                    site_hits[site] += 1
            action_type = str(getattr(step, 'action_type', '') or '')
            if action_type in {'click', 'input', 'change', 'submit', 'keydown', 'scroll', 'focus'}:
                relevant_steps += 1
            if any(flag in lower for flag in ['email', 'usuario', 'username']) and action_type in {'input', 'change', 'frame_fallback'}:
                email = True
            if 'password' in lower or 'contrasena' in lower or 'contrase?a' in lower:
                password = True
            if action_type == 'submit' or 'enter' in lower or 'iniciar sesion' in lower or 'login' in lower:
                submit = True
            if any(flag in lower for flag in ['loggedinplayer', 'balance', 'mi cuenta', 'cerrar sesion', 'logout']):
                authenticated = True
            if 'casino' in lower:
                casino = True
            if 'google' in lower or 'search' in lower or 'buscar' in lower:
                search_google = True
        if email:
            signal_labels.append('email o usuario detectado')
        if password:
            signal_labels.append('contrasena detectada')
        if submit:
            signal_labels.append('submit o enter detectado')
        if authenticated:
            signal_labels.append('sesion autenticada detectada')
        if casino:
            signal_labels.append('navegacion hacia casino detectada')
        if search_google:
            signal_labels.append('busqueda web detectada')
        login_score = sum(bool(flag) for flag in [email, password, submit, authenticated])
        if login_score >= 4:
            login_status = 'ready'
        elif login_score >= 2:
            login_status = 'partial'
        else:
            login_status = 'insufficient'
        if relevant_steps >= 6 or (login_status == 'ready' and relevant_steps >= 3):
            learning_status = 'ready'
        elif relevant_steps >= 2 or login_status in {'ready', 'partial'}:
            learning_status = 'partial'
        else:
            learning_status = 'insufficient'
        return {
            'site_hits': site_hits,
            'signal_labels': signal_labels,
            'tokens': tokens,
            'relevant_steps': relevant_steps,
            'login_status': login_status,
            'learning_status': learning_status,
        }

    def _latest_live_audit(self, *, site_id: str | None, user_goal: str) -> dict[str, Any]:
        if self.live_audit_supervisor is not None:
            try:
                summary = self.live_audit_supervisor.latest_summary(site_id=site_id, user_goal=user_goal)
                if summary:
                    return summary
            except Exception:
                pass
        if self.tool_record_repository is None:
            return {}
        episodes = self.tool_record_repository.list_interaction_episodes(site_id=site_id, limit=20) if site_id else self.tool_record_repository.list_interaction_episodes(limit=20)
        goal_tokens = {token for token in user_goal.lower().split() if len(token) >= 3}
        for episode in episodes:
            audit = dict(episode.metadata.get('live_audit') or {})
            if not audit:
                continue
            if goal_tokens:
                objective_tokens = {token for token in str(episode.objective or '').lower().split() if len(token) >= 3}
                if objective_tokens and not goal_tokens.intersection(objective_tokens):
                    continue
            findings = [str(item.get('kind') or '') for item in audit.get('findings') or [] if isinstance(item, dict)]
            decision = dict(audit.get('decision') or {})
            return {
                'audit_snapshot_id': str(audit.get('audit_snapshot_id') or ''),
                'summary': self._audit_summary(audit),
                'decision_action': str(decision.get('action') or ''),
                'recommended_tool_id': str(decision.get('recommended_tool_id') or ''),
                'confidence': float(audit.get('confidence') or 0.0),
                'findings': findings,
                'metrics': dict(audit.get('metrics') or {}),
                'episode_id': episode.interaction_episode_id,
            }
        return {}

    def _audit_summary(self, audit: dict[str, Any]) -> str:
        findings = [item for item in audit.get('findings') or [] if isinstance(item, dict)]
        lead = str(findings[0].get('title') or findings[0].get('kind') or '').strip() if findings else ''
        decision = str((audit.get('decision') or {}).get('action') or '').strip()
        confidence = float(audit.get('confidence') or 0.0)
        if lead and decision:
            return f'{lead} Decision: {decision}. Confianza {confidence:.2f}.'
        if lead:
            return lead
        if decision:
            return f'Decision auditada: {decision}.'
        return ''

    def _should_skip_persistent_goal_context(self, *, request: InferenceRequest, intent: TaskIntent) -> bool:
        params = dict(request.goal_parameters or {})
        has_explicit_goal = any(str(params.get(key) or '').strip() for key in ('objective_id', 'project_id', 'task_id'))
        if has_explicit_goal:
            return False
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
        return intent.intent_key in {'general.assistance', 'knowledge.query'} and intent.disposition.value in {'answer_now', 'need_info'} and conversational_prompt

    def _goal_context_snapshot(self, *, request: InferenceRequest, intent: TaskIntent, site_id: str | None) -> GoalContext:
        if self.objective_repository is None:
            return GoalContext(active_title=request.user_goal)
        if self._should_skip_persistent_goal_context(request=request, intent=intent):
            return GoalContext(
                active_title=str(request.user_goal or intent.title),
                status='pending',
                trend='conversacional',
                metadata={'source': 'transient_chat_goal', 'persistent': False, 'intent_key': intent.intent_key},
            )
        params = dict(request.goal_parameters or {})
        requested_ids = [
            str(params.get('task_id') or ''),
            str(params.get('project_id') or ''),
            str(params.get('objective_id') or ''),
        ]
        for objective_id in requested_ids:
            if not objective_id:
                continue
            node = self.objective_repository.get(objective_id)
            if node is not None:
                return self._context_from_node(node)
        site_probe = site_id or str(params.get('site_hint') or '').strip() or None
        for kind in (ObjectiveNodeKind.TASK, ObjectiveNodeKind.PROJECT, ObjectiveNodeKind.OBJECTIVE):
            node = self.objective_repository.latest_active(kind=kind, site_id=site_probe)
            if node is not None:
                return self._context_from_node(node)
        return GoalContext(
            active_title=str(params.get('objective_title') or request.user_goal or intent.title),
            status='pending',
            metadata={'source': 'no_persistent_goal'},
        )

    def _context_from_node(self, node) -> GoalContext:
        if self.objective_repository is None:
            return GoalContext(active_title=getattr(node, 'title', ''))
        objective = node
        project = None
        task = None
        if node.kind == ObjectiveNodeKind.TASK:
            task = node
            project = self.objective_repository.get(str(node.parent_id or '')) if node.parent_id else None
            objective = self.objective_repository.get(str(node.root_id or '')) or node
        elif node.kind == ObjectiveNodeKind.PROJECT:
            project = node
            objective = self.objective_repository.get(str(node.root_id or '')) or node
            children = self.objective_repository.list_children(node.objective_id, kind=ObjectiveNodeKind.TASK, limit=4)
            task = children[0] if children else None
        elif node.kind == ObjectiveNodeKind.OBJECTIVE:
            objective = node
            projects = self.objective_repository.list_children(node.objective_id, kind=ObjectiveNodeKind.PROJECT, limit=4)
            project = projects[0] if projects else None
            if project is not None:
                tasks = self.objective_repository.list_children(project.objective_id, kind=ObjectiveNodeKind.TASK, limit=4)
                task = tasks[0] if tasks else None
        active = task or project or objective
        subtasks = self.objective_repository.list_children(active.objective_id, kind=ObjectiveNodeKind.SUBTASK, limit=12) if active is not None and active.kind in {ObjectiveNodeKind.TASK, ObjectiveNodeKind.PROJECT} else []
        blocker = ''
        for candidate in (task, project, objective):
            if candidate is not None and candidate.blocker:
                blocker = candidate.blocker
                break
        progress = max(float(getattr(item, 'progress', 0.0) or 0.0) for item in (task, project, objective) if item is not None)
        confidence = max(float(getattr(item, 'confidence', 0.0) or 0.0) for item in (task, project, objective) if item is not None)
        return GoalContext(
            objective=objective.model_dump(mode='json') if objective is not None else {},
            project=project.model_dump(mode='json') if project is not None else {},
            task=task.model_dump(mode='json') if task is not None else {},
            subtasks=[item.model_dump(mode='json') for item in subtasks],
            active_node_id=str(active.objective_id if active is not None else ''),
            active_title=str(active.title if active is not None else ''),
            priority=int(getattr(active, 'priority', 50) or 50),
            status=str(getattr(active, 'status', 'pending').value if active is not None and hasattr(getattr(active, 'status', ''), 'value') else getattr(active, 'status', 'pending')),
            progress=round(progress, 4),
            blocker=blocker,
            confidence=round(confidence, 4),
            trend='bloqueado' if blocker else 'avanzando' if progress >= 0.7 else 'en curso' if progress > 0.0 else 'sin base',
            evidence_refs=list(dict.fromkeys([
                *list(getattr(objective, 'evidence_refs', []) or []),
                *list(getattr(project, 'evidence_refs', []) or []),
                *list(getattr(task, 'evidence_refs', []) or []),
            ]))[:12],
            metadata={'source': 'objective_repository'},
        )
    def _build_evidence_summary(
        self,
        *,
        site_display_name: str,
        recent_teachings: list[dict[str, Any]],
        recent_runs: list[dict[str, Any]],
        recent_incidents: list[dict[str, Any]],
        recent_dossiers: list[dict[str, Any]],
        interaction_patterns: list[dict[str, Any]],
        experiment_insights: list[dict[str, Any]],
        knowledge_hits: list[dict[str, Any]],
    ) -> list[str]:
        lines = [f'Contexto activo: {site_display_name}.']
        if recent_teachings:
            lead = recent_teachings[0]
            lines.append(
                f"Ensenanza reciente: {lead['title']} | login {lead['login_status']} | aprendizaje {lead['learning_status']} | pasos relevantes {lead['relevant_steps']} | visual {lead.get('visual_alignment_score', 0.0):.2f}."
            )
            if lead.get('manual_correction_count', 0):
                lines.append(f"Correcciones humanas persistidas: {lead['manual_correction_count']} | rojos: {lead.get('red_count', 0)}.")
        if recent_runs:
            lead_run = recent_runs[0]
            lines.append(f"Ultima corrida: {lead_run['status']} | rol {lead_run['role']} | pack {lead_run['pack_id'] or 'sin pack adaptativo'}.")
        if recent_incidents:
            lead_incident = recent_incidents[0]
            lines.append(f"Incidente reciente: {lead_incident['incident_kind']} ({lead_incident['severity']}).")
        if recent_dossiers:
            lines.append(f"Dossiers relacionados: {len(recent_dossiers)}.")
        if interaction_patterns:
            channel_counts = Counter(item.get('channel', '') for item in interaction_patterns if item.get('channel'))
            bits = [f"{channel}:{count}" for channel, count in channel_counts.items()]
            lines.append(f"Patrones universales reutilizables: {len(interaction_patterns)}" + (f" ({' | '.join(bits)})." if bits else '.'))
        if experiment_insights:
            lead = experiment_insights[0]
            lines.append(
                f"Laboratorio universal: {lead['domain']} -> {lead['recommended_route']} (score {float(lead.get('score', 0.0)):.2f}, confianza {float(lead.get('confidence', 0.0)):.2f})."
            )
        if knowledge_hits:
            lines.append(f"Conocimiento local relacionado: {len(knowledge_hits)} items.")
        return lines


    def _load_teaching_brief(self, episode_id: str) -> dict[str, Any]:
        if self.artifact_repository is None:
            return {}
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        target = next((item for item in reversed(artifacts) if item.kind == 'teaching_brief'), None)
        if target is None:
            return {}
        try:
            return self.artifact_repository.storage.load_json(target.path)
        except Exception:
            return {}

    def _load_learning_bundle(self, episode_id: str) -> dict[str, Any]:
        if self.artifact_repository is None:
            return {}
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        target = next((item for item in reversed(artifacts) if item.kind == 'learning_bundle'), None)
        if target is None:
            return {}
        try:
            return self.artifact_repository.storage.load_json(target.path)
        except Exception:
            return {}


    def _status_rank(self, value: str) -> int:
        return {'insufficient': 0, 'partial': 1, 'ready_with_approval': 2, 'ready': 3}.get(str(value or '').strip().lower(), 0)

    def _visual_summary_needs_refresh(self, summary: dict[str, Any]) -> bool:
        if not summary:
            return True
        return (
            int(summary.get('green_count', 0) or 0) == 0
            and float(summary.get('visual_alignment_score', 0.0) or 0.0) == 0.0
            and float(summary.get('critical_object_coverage', 0.0) or 0.0) == 0.0
            and float(summary.get('login_visual_completeness', 0.0) or 0.0) == 0.0
        )

    def _visual_summary_score(self, summary: dict[str, Any]) -> float:
        if not summary:
            return 0.0
        return (
            float(summary.get('visual_alignment_score', 0.0) or 0.0)
            + float(summary.get('critical_object_coverage', 0.0) or 0.0)
            + float(summary.get('login_visual_completeness', 0.0) or 0.0)
            + (int(summary.get('green_count', 0) or 0) * 0.05)
        )

    def _teaching_visual_ready(self, summary: dict[str, Any]) -> bool:
        return (
            float(summary.get('critical_object_coverage', 0.0) or 0.0) >= 0.66
            and float(summary.get('login_visual_completeness', 0.0) or 0.0) >= 0.66
            and int(summary.get('red_count', 0) or 0) == 0
        )

    def _derive_teaching_visual_summary(self, steps: list[Any]) -> dict[str, Any]:
        try:
            return dict(self._teaching_visual_summary_builder._build_visual_summary(steps))
        except Exception:
            return {}

