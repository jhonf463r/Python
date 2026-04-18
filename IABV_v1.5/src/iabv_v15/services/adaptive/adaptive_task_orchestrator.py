from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    ApprovalCheckpoint,
    CapabilityReadiness,
    ClarificationItem,
    DecisionContext,
    EnvironmentSelfModel,
    GoalContext,
    InferenceRequest,
    InferenceResult,
    IssueSeverity,
    IntentSchema,
    PerceptionSnapshot,
    ReasoningMode,
    ReportKind,
    RoleRoute,
    RunRecord,
    RunStatus,
    TaskContext,
    TaskIntent,
    TaskOutcome,
    TaskRole,
    VisualSignalSnapshot,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.services.adaptive.adaptive_planner_service import AdaptivePlannerService
from iabv_v15.services.adaptive.approval_gate_service import ApprovalGateService
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService
from iabv_v15.services.adaptive.goal_engine import GoalEngine
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


class AdaptiveTaskOrchestrator:
    def __init__(
        self,
        *,
        role_router: LocalRoleRouter,
        adaptive_session_repository: AdaptiveSessionRepository,
        intent_service: IntentUnderstandingService,
        context_assembler: TaskContextAssembler,
        capability_service: CapabilityReadinessService,
        strategy_pack_registry: StrategyPackRegistry,
        planner_service: AdaptivePlannerService,
        approval_gate_service: ApprovalGateService,
        execution_playbook_service: ExecutionPlaybookService,
        task_outcome_recorder: TaskOutcomeRecorder,
        autonomous_evolution_service: Any | None = None,
        unified_memory_layer: Any | None = None,
        goal_engine: GoalEngine | None = None,
        autonomy_governance_policy: AutonomyGovernancePolicy | None = None,
    ) -> None:
        self.role_router = role_router
        self.adaptive_session_repository = adaptive_session_repository
        self.intent_service = intent_service
        self.context_assembler = context_assembler
        self.capability_service = capability_service
        self.strategy_pack_registry = strategy_pack_registry
        self.planner_service = planner_service
        self.approval_gate_service = approval_gate_service
        self.execution_playbook_service = execution_playbook_service
        self.task_outcome_recorder = task_outcome_recorder
        self.autonomous_evolution_service = autonomous_evolution_service
        self.unified_memory_layer = unified_memory_layer
        self.goal_engine = goal_engine
        self.autonomy_governance_policy = autonomy_governance_policy

    def build_decision_context_preview(self, request: InferenceRequest) -> DecisionContext:
        # Usar clasificación con schema para mejor comprensión semántica
        intent, intent_schema = self.intent_service.classify_with_schema(
            request.user_goal,
            request.goal_parameters,
            conversation_history=request.metadata.get('conversation_history'),
        )
        route_decision = self.role_router.build_decision_from_intent(request=request, intent=intent)
        perception = self.context_assembler.build_perception_snapshot(
            request, intent, route_decision=route_decision, intent_schema=intent_schema
        )
        return perception.decision_context

    def handle_request(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult, AdaptiveSession]:
        # ETAPA 2: Clasificación semántica mejorada con IntentSchema
        intent, intent_schema = self.intent_service.classify_with_schema(
            request.user_goal,
            request.goal_parameters,
            conversation_history=request.metadata.get('conversation_history'),
        )
        hypotheses = intent.hypotheses
        route_decision = self.role_router.build_decision_from_intent(request=request, intent=intent)
        perception = self.context_assembler.build_perception_snapshot(
            request, intent, route_decision=route_decision, intent_schema=intent_schema
        )
        context = perception.task_context

        # Extraer análisis conversacional del schema (más preciso que keywords)
        ambiguity_score = intent_schema.ambiguity_score if intent_schema else 0.0
        requires_clarification = intent_schema.requires_clarification if intent_schema else False
        sub_intents = intent_schema.sub_intents if intent_schema else []
        risk_level = intent_schema.risk_level if intent_schema else 'low'

        capabilities = self.capability_service.evaluate(intent, context)
        context.capability_snapshot = capabilities
        perception.task_context.capability_snapshot = capabilities
        pack = self.strategy_pack_registry.resolve_pack(intent, context)
        strategy_candidates = self.strategy_pack_registry.build_candidates(
            pack=pack,
            intent=intent,
            context=context,
            capabilities=capabilities,
        )
        playbook = self.planner_service.build_playbook(
            intent=intent,
            context=context,
            pack=pack,
            capabilities=capabilities,
            strategy_candidates=strategy_candidates,
        )
        approvals = self.approval_gate_service.evaluate(intent=intent, pack=pack, strategy_candidates=strategy_candidates)
        session_status = self._derive_session_status(intent=intent, playbook=playbook, approvals=approvals)
        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=intent,
            hypotheses=hypotheses,
            context=context,
            chosen_pack_id=pack.pack_id,
            chosen_pack_title=pack.title,
            status=session_status,
            capability_readiness=capabilities,
            strategy_candidates=strategy_candidates,
            playbook=playbook.model_copy(update={'status': session_status}),
            approval_checkpoints=[],
            outcome=None,
            evidence_refs=list(context.evidence_summary),
            metadata={
                'approval_mode': request.approval_mode,
                'execution_scope': request.execution_scope,
                'goal_parameters': dict(request.goal_parameters),
                'perception_snapshot': perception.model_dump(mode='json'),
                'etapa2_conversation_analysis': {
                    'ambiguity_score': ambiguity_score,
                    'requires_clarification': requires_clarification,
                    'sub_intents': sub_intents,
                    'risk_level': risk_level,
                    'compound_intent': len(sub_intents) > 1 if sub_intents else False,
                    'semantic_source': intent_schema.semantic_source if intent_schema else 'keywords',
                    'intent_confidence': intent_schema.confidence if intent_schema else 0.0,
                },
            },
        )
        session.playbook.metadata['site_id'] = context.site_id or intent.site_hint or ''
        for checkpoint in approvals:
            checkpoint.session_id = session.session_id
            checkpoint.playbook_id = session.playbook.playbook_id if session.playbook is not None else None
        session.approval_checkpoints = approvals
        session = self.execution_playbook_service.annotate_execution_capability(session)
        if self.goal_engine is not None:
            self.goal_engine.attach_session_goal_context(request=request, session=session)
            perception.goal_context = session.context.goal_context
            perception.task_context.goal_context = session.context.goal_context
        session.outcome = self._initial_outcome(session=session, pack=pack)
        session = self._refresh_session_metadata(session, request=request, pack=pack, perception_snapshot=perception)
        decision_context = DecisionContext.model_validate(
            session.metadata.get('decision_context') or session.context.metadata.get('decision_context') or {}
        )
        saved_session = self.task_outcome_recorder.record(session)
        route = self._build_route(saved_session, decision_context)
        result = self._build_result(request=request, session=saved_session, pack=pack, route=route)
        return route, result, saved_session

    def govern_adaptive_payload(self, adaptive_payload: dict[str, Any], *, user_goal: str, source: str) -> dict[str, Any]:
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        existing = dict(metadata.get('autonomous_evolution') or {})
        decision_context = self._decision_context_from_payload(payload=payload, user_goal=user_goal)
        metadata['decision_context'] = decision_context.model_dump(mode='json')
        payload['metadata'] = metadata
        if self.autonomous_evolution_service is None:
            return payload
        # Verificar si hay una consulta expirada o fallida que necesite reintento
        existing_status = existing.get('status')
        external_state_flags = list(existing.get('external_state_flags') or [])
        retry_count = int(existing.get('retry_count') or 0)
        max_retries = 3
        # Determinar si necesita reintento:
        # 1. awaiting_response con SESSION_EXPIRED (26% - browser_input_missing)
        # 2. failed/blocked sin retry_exhausted (32%)
        needs_retry = (
            existing_status == 'awaiting_response' and 'session_expired' in external_state_flags
        ) or (
            existing_status in {'failed', 'blocked'} and not existing.get('retry_exhausted')
        )
        if needs_retry:
            if retry_count >= max_retries:
                # Máximo de reintentos alcanzado, marcar como fallido permanentemente
                existing['status'] = 'failed'
                existing['retry_exhausted'] = True
                existing['reason'] = f'Consulta fallida después de {max_retries} reintentos.'
                metadata['autonomous_evolution'] = dict(existing)
                payload['metadata'] = metadata
                payload['assistant_guidance'] = f'La consulta externa no pudo completarse después de {max_retries} intentos. Recomiendo continuar localmente.'
                return payload
            # Limpiar estado para reintento
            previous_status = existing_status if existing_status in {'failed', 'blocked'} else 'session_expired'
            payload = self._prepare_retry_for_expired_consultation(payload, existing, retry_count, previous_status)
            decision_context = self._decision_context_from_payload(payload=payload, user_goal=user_goal)
        elif existing_status in {'prepared', 'reused'} or existing.get('retry_exhausted'):
            # Estados finales o agotados reintentos, no reintentar
            return payload
        result = self.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal=user_goal,
            source=source,
            decision_context=decision_context,
        )
        # Incrementar contador de reintentos si es un reintento
        if needs_retry:
            result['retry_count'] = retry_count + 1
            result['is_retry'] = True
        metadata['autonomous_evolution'] = dict(result)
        if self._has_external_response(result):
            metadata['autonomous_evolution_response'] = dict(result)
            payload['assistant_guidance'] = self._guidance_for_external_response(result)
        payload['metadata'] = metadata
        if result.get('pending_issue_id'):
            payload['pending_issue_id'] = result.get('pending_issue_id')
        if result.get('status') in {'prepared', 'reused', 'awaiting_response'} and not self._has_external_response(result):
            payload['assistant_guidance'] = self._guidance_for_pending_external_response(result)
        return payload

    def _prepare_retry_for_expired_consultation(
        self,
        payload: dict[str, Any],
        existing_consultation: dict[str, Any],
        retry_count: int,
        previous_status: str = 'session_expired',
    ) -> dict[str, Any]:
        """Limpia el estado de una consulta expirada o fallida para permitir reintento."""
        new_payload = dict(payload)
        metadata = dict(new_payload.get('metadata') or {})
        # Limpiar flags de estado anterior
        metadata.pop('autonomous_evolution', None)
        metadata.pop('autonomous_evolution_response', None)
        metadata.pop('pending_issue_id', None)
        # Limpiar también execution_state relacionado si existe
        if 'execution_state' in metadata:
            metadata.pop('execution_state', None)
        # Agregar metadata de reintento
        reason = (
            'Consulta externa fallida, reintentando.'
            if previous_status in {'failed', 'blocked'}
            else 'Consulta externa expirada, reintentando captura.'
        )
        metadata['consultation_retry'] = {
            'previous_task_id': str(existing_consultation.get('task_id') or ''),
            'previous_result_id': str(existing_consultation.get('result_id') or ''),
            'retry_count': retry_count + 1,
            'previous_status': previous_status,
            'retry_reason': reason,
        }
        new_payload['metadata'] = metadata
        return new_payload

    def preview_autonomy(self, adaptive_payload: dict[str, Any], *, user_goal: str, source: str) -> dict[str, Any]:
        payload = dict(adaptive_payload or {})
        decision_context = self._decision_context_from_payload(payload=payload, user_goal=user_goal)
        if self.autonomous_evolution_service is None:
            governance = dict(decision_context.governance)
            return {
                'status': 'preview',
                'should_consult': bool(governance.get('should_consult')),
                'assistant_kind': str(governance.get('assistant_kind') or ''),
                'requested_assistant_kind': str(governance.get('assistant_kind') or ''),
                'actual_assistant_kind': str(governance.get('assistant_kind') or ''),
                'decision_source': source,
                'recommended_action': str(governance.get('recommended_action') or 'continue_local'),
                'reason': str(governance.get('reason') or 'No hay pipeline de autonomia configurado.'),
                'site_id': decision_context.site_id,
                'incident_kind': str((decision_context.live_audit or {}).get('incident_kind') or ''),
                'available': False,
                'fallback_used': False,
                'selected_tool_id': '',
                'launch_mode': '',
                'preview_summary': '',
                'context_pack_excerpt': '',
            }
        return self.autonomous_evolution_service.preview_plan(
            adaptive_payload=payload,
            user_goal=user_goal,
            source=source,
            decision_context=decision_context,
        )

    def ingest_external_response(
        self,
        adaptive_payload: dict[str, Any],
        *,
        user_goal: str,
        response_text: str,
        source: str,
    ) -> dict[str, Any]:
        if self.autonomous_evolution_service is None:
            return {
                'status': 'missing_context',
                'assistant_kind': '',
                'next_action': 'stop_and_wait_user',
                'detail': 'La autonomia externa no esta disponible en esta sesion.',
            }
        payload = dict(adaptive_payload or {})
        decision_context = self._decision_context_from_payload(payload=payload, user_goal=user_goal)
        metadata = dict(payload.get('metadata') or {})
        metadata['decision_context'] = decision_context.model_dump(mode='json')
        payload['metadata'] = metadata
        return self.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal=user_goal,
            response_text=response_text,
            source=source,
        )

    def finalize_with_run(self, session_id: str, run_record: RunRecord) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        session = session.model_copy(deep=True)
        session.run_id = run_record.run_id
        session.updated_at_utc = datetime.now(timezone.utc)
        session.metadata['linked_run_status'] = run_record.status.value
        session.metadata['linked_run_id'] = run_record.run_id
        session.metadata['linked_run_summary'] = run_record.result.summary
        session.metadata['linked_run_error'] = run_record.error_summary or run_record.result.error_summary
        session = self._apply_run_feedback(session, run_record)
        session = self._refresh_session_metadata(session)
        saved_session = self.task_outcome_recorder.record(session, run_record=run_record)
        if self._should_auto_replan(saved_session):
            replanned = self.replan_session(saved_session.session_id)
            if replanned is not None:
                saved_session.metadata['auto_replanned_session_id'] = replanned.session_id
                saved_session.metadata['auto_replanned'] = True
                saved_session.updated_at_utc = datetime.now(timezone.utc)
                self.task_outcome_recorder.record(saved_session)
                replanned.metadata['replanned_automatically'] = True
                replanned.metadata['replan_triggered_by_run_id'] = run_record.run_id
                replanned = self.task_outcome_recorder.record(replanned)
                return replanned
        return saved_session

    def _apply_run_feedback(self, session: AdaptiveSession, run_record: RunRecord) -> AdaptiveSession:
        linked_status = run_record.status
        summary = str(run_record.result.summary or '')
        error_summary = str(run_record.error_summary or run_record.result.error_summary or '').strip()
        next_actions = list(run_record.result.next_actions or [])
        if linked_status == RunStatus.SUCCESS:
            session.status = AdaptiveSessionStatus.COMPLETED
            summary = summary or 'La corrida ligada al playbook termino correctamente.'
        elif linked_status == RunStatus.FAILED:
            session.status = AdaptiveSessionStatus.FAILED
            summary = error_summary or summary or 'La corrida ligada al playbook fallo.'
            if not next_actions:
                next_actions = ['Replanificar', 'Revisar evidencia reciente']
        elif linked_status == RunStatus.CANCELLED:
            session.status = AdaptiveSessionStatus.ABORTED
            summary = error_summary or summary or 'La corrida ligada al playbook fue cancelada.'
        else:
            if session.status == AdaptiveSessionStatus.EXECUTING and error_summary:
                session.status = AdaptiveSessionStatus.FAILED
            summary = summary or error_summary or (session.outcome.summary if session.outcome is not None else '') or 'La corrida ligada al playbook termino de forma parcial.'
            if run_record.result.used_fallback or error_summary:
                session.metadata['linked_run_partial'] = True
                if not next_actions:
                    next_actions = ['Revisar resultado parcial', 'Replanificar']
        previous_metadata = dict(session.outcome.metadata or {}) if session.outcome is not None else {}
        session.outcome = TaskOutcome(
            status=linked_status,
            summary=summary,
            next_actions=next_actions,
            evidence_refs=list(session.evidence_refs),
            metadata={
                **previous_metadata,
                'source': 'linked_run',
                'run_id': run_record.run_id,
                'run_status': linked_status.value,
                'run_error_summary': error_summary,
            },
        )
        if session.playbook is not None:
            session.playbook = session.playbook.model_copy(update={'status': self._session_status_from_value(session.status.value)})
        return session

    def _should_auto_replan(self, session: AdaptiveSession) -> bool:
        governance = dict(session.metadata.get('governance') or {})
        if not governance or not bool(governance.get('should_replan')):
            return False
        if bool(governance.get('should_consult')) or bool(governance.get('approval_required')) or bool(governance.get('block_risky_action')):
            return False
        if session.metadata.get('auto_replanned_session_id') or session.metadata.get('replanned_automatically'):
            return False
        if session.metadata.get('replanned_from_session_id'):
            return False
        return int(session.metadata.get('replan_count') or 0) < 2

    def get_session(self, session_id: str) -> AdaptiveSession | None:
        return self.adaptive_session_repository.get(session_id)

    def latest_session(self) -> AdaptiveSession | None:
        items = self.adaptive_session_repository.list_recent(limit=1)
        return items[0] if items else None

    def approve_strategy(self, session_id: str) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        session = self.execution_playbook_service.approve_strategy(session)
        session = self._refresh_session_metadata(session)
        return self.task_outcome_recorder.record(session)

    def approve_next_phase(self, session_id: str) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        session = self.execution_playbook_service.approve_next_phase(session)
        session = self._refresh_session_metadata(session)
        return self.task_outcome_recorder.record(session)

    def simulate(self, session_id: str) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        session = self.execution_playbook_service.simulate(session)
        session = self._refresh_session_metadata(session)
        return self.task_outcome_recorder.record(session)

    def execute_now(self, session_id: str) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        session = self.execution_playbook_service.execute(session)
        session = self._refresh_session_metadata(session)
        return self.task_outcome_recorder.record(session)

    def abort(self, session_id: str) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        session = self.execution_playbook_service.abort(session)
        session = self._refresh_session_metadata(session)
        return self.task_outcome_recorder.record(session)

    def replan_session(self, session_id: str) -> AdaptiveSession | None:
        session = self.adaptive_session_repository.get(session_id)
        if session is None:
            return None
        request = self._request_from_session(session)
        request = request.model_copy(
            update={
                'metadata': {
                    **dict(request.metadata or {}),
                    'replanned_from_session_id': session.session_id,
                    'replan_reason': str((session.metadata.get('governance') or {}).get('reason') or (session.outcome.summary if session.outcome is not None else '') or ''),
                }
            }
        )
        _, _, replanned = self.handle_request(request)
        replanned.metadata['replanned_from_session_id'] = session.session_id
        replanned.metadata['replan_count'] = int(session.metadata.get('replan_count') or 0) + 1
        return self.task_outcome_recorder.record(replanned)

    def _refresh_session_metadata(
        self,
        session: AdaptiveSession,
        *,
        request: InferenceRequest | None = None,
        pack: Any | None = None,
        perception_snapshot: PerceptionSnapshot | None = None,
    ) -> AdaptiveSession:
        self._sync_goal_context(session)
        refresh_request = request or self._request_from_session(session)
        pack_ref = pack or self._pack_stub(session)
        assistant_guidance = self._build_assistant_guidance(session, pack_ref)
        decision_context = self._build_decision_context(
            request=refresh_request,
            session=session,
            pack=pack_ref,
            assistant_guidance=assistant_guidance,
            perception_snapshot=perception_snapshot,
        )
        resolved_perception = self._refresh_perception_snapshot(
            perception_snapshot=perception_snapshot,
            session=session,
            decision_context=decision_context,
            assistant_guidance=assistant_guidance,
        )
        session.context.metadata['decision_context'] = decision_context.model_dump(mode='json')
        session.context.metadata['goal_context'] = session.context.goal_context.model_dump(mode='json')
        session.context.metadata['perception_snapshot'] = resolved_perception.model_dump(mode='json')
        session.metadata.update(
            {
                'decision_context': decision_context.model_dump(mode='json'),
                'assistant_guidance': dict(decision_context.assistant_guidance or {}),
                'governance': dict(decision_context.governance),
                'goal_context': session.context.goal_context.model_dump(mode='json'),
                'goal_parameters': {**dict(session.metadata.get('goal_parameters') or {}), **self._goal_parameters(session.context.goal_context)},
                'perception_snapshot': resolved_perception.model_dump(mode='json'),
            }
        )
        return session

    def _refresh_perception_snapshot(
        self,
        *,
        perception_snapshot: PerceptionSnapshot | None,
        session: AdaptiveSession,
        decision_context: DecisionContext,
        assistant_guidance: dict[str, Any],
    ) -> PerceptionSnapshot:
        refreshed_memory_snapshot = (
            self.unified_memory_layer.build_snapshot(session.context)
            if self.unified_memory_layer is not None
            else self._memory_snapshot_from_context(session.context)
        )
        environment_self_model = (
            perception_snapshot.environment_self_model
            if perception_snapshot is not None
            else self._environment_self_model()
        )
        world_model = (
            perception_snapshot.world_model
            if perception_snapshot is not None
            else self._world_model()
        )
        if perception_snapshot is None:
            return PerceptionSnapshot(
                task_context=session.context,
                decision_context=decision_context,
                goal_context=session.context.goal_context,
                memory_snapshot=refreshed_memory_snapshot,
                live_audit=dict(session.context.live_audit or {}),
                runtime_signals=[],
                session_health=None,
                ia_trace=[],
                visual_signal=VisualSignalSnapshot(unresolved_fields=['UNRESOLVED:visual_signal_source']),
                environment_self_model=environment_self_model,
                world_model=world_model,
                external_state_flags=[],
                unresolved_fields=[
                    'UNRESOLVED:runtime_signals',
                    'UNRESOLVED:session_health',
                    'UNRESOLVED:ia_trace',
                    'UNRESOLVED:visual_signal',
                    *(['UNRESOLVED:environment_self_model'] if not str(environment_self_model.environment_id or '').strip() else []),
                    *(['UNRESOLVED:world_model'] if self._world_model_unresolved(world_model) else []),
                ],
                metadata={'decision_source': 'adaptive_task_orchestrator_fallback'},
            )
        unresolved_fields = [
            field
            for field in perception_snapshot.unresolved_fields
            if field not in {'UNRESOLVED:runtime_signals', 'UNRESOLVED:session_health', 'UNRESOLVED:ia_trace', 'UNRESOLVED:visual_signal', 'UNRESOLVED:world_model'}
            or (
                field == 'UNRESOLVED:runtime_signals' and not perception_snapshot.runtime_signals
            )
            or (
                field == 'UNRESOLVED:session_health' and perception_snapshot.session_health is None
            )
            or (
                field == 'UNRESOLVED:ia_trace' and not perception_snapshot.ia_trace
            )
            or (
                field == 'UNRESOLVED:visual_signal'
                and not (
                    perception_snapshot.visual_signal.capture_available
                    or perception_snapshot.visual_signal.dom_available
                    or perception_snapshot.visual_signal.visible_targets
                    or perception_snapshot.visual_signal.visual_evidence_refs
                )
            )
            or (
                field == 'UNRESOLVED:world_model'
                and self._world_model_unresolved(world_model)
            )
        ]
        return perception_snapshot.model_copy(
            update={
                'task_context': session.context,
                'decision_context': decision_context,
                'goal_context': session.context.goal_context,
                'memory_snapshot': refreshed_memory_snapshot,
                'live_audit': dict(session.context.live_audit or perception_snapshot.live_audit or {}),
                'environment_self_model': environment_self_model,
                'world_model': world_model,
                'metadata': {
                    **dict(perception_snapshot.metadata or {}),
                    'decision_stage': 'post_governance',
                    'assistant_guidance_mode': str(assistant_guidance.get('mode') or ''),
                    'environment_id': str(environment_self_model.environment_id or ''),
                    'world_model_summary': self._world_model_summary(world_model),
                },
                'unresolved_fields': unresolved_fields,
            }
        )

    def _pack_stub(self, session: AdaptiveSession) -> Any:
        return SimpleNamespace(pack_id=session.chosen_pack_id, title=session.chosen_pack_title)

    def _sync_goal_context(self, session: AdaptiveSession) -> GoalContext:
        if self.goal_engine is not None:
            context = self.goal_engine.sync_session(session)
            if context is not None:
                return context
        return session.context.goal_context

    def _goal_parameters(self, goal_context: GoalContext | None) -> dict[str, Any]:
        if goal_context is None:
            return {}
        if self.goal_engine is not None:
            return self.goal_engine.build_goal_parameters(goal_context)
        payload = goal_context.model_dump(mode='json') if isinstance(goal_context, GoalContext) else dict(goal_context or {})
        objective = dict(payload.get('objective') or {})
        project = dict(payload.get('project') or {})
        task = dict(payload.get('task') or {})
        return {
            'objective_id': str(objective.get('objective_id') or ''),
            'objective_title': str(objective.get('title') or payload.get('active_title') or ''),
            'project_id': str(project.get('objective_id') or ''),
            'project_title': str(project.get('title') or ''),
            'task_id': str(task.get('objective_id') or ''),
            'task_title': str(task.get('title') or ''),
            'goal_status': str(payload.get('status') or ''),
            'goal_progress': float(payload.get('progress') or 0.0),
            'goal_confidence': float(payload.get('confidence') or 0.0),
            'goal_blocker': str(payload.get('blocker') or ''),
        }

    def _request_from_session(self, session: AdaptiveSession) -> InferenceRequest:
        goal_parameters = {**dict(session.metadata.get('goal_parameters') or {}), **self._goal_parameters(session.context.goal_context)}
        return InferenceRequest(
            user_goal=session.user_goal,
            prompt=session.user_goal,
            task_role=session.intent.detected_role,
            role_hint=session.intent.detected_role,
            auto_route=False,
            site_hint=session.context.site_id or session.intent.site_hint,
            approval_mode=str(session.metadata.get('approval_mode') or 'phased'),
            execution_scope=str(session.metadata.get('execution_scope') or 'operational'),
            goal_parameters=goal_parameters,
            metadata={
                'decision_source': 'adaptive_session_refresh',
                'session_id': session.session_id,
            },
        )

    def _session_status_from_value(self, value: str) -> AdaptiveSessionStatus:
        try:
            return AdaptiveSessionStatus(str(value or AdaptiveSessionStatus.PLANNED.value))
        except ValueError:
            return AdaptiveSessionStatus.PLANNED

    def _enrich_assistant_guidance(
        self,
        *,
        session: AdaptiveSession,
        assistant_guidance: dict[str, Any],
        governance: dict[str, Any],
    ) -> dict[str, Any]:
        guidance = dict(assistant_guidance or {})
        actions = [dict(item) for item in (guidance.get('actions') or []) if isinstance(item, dict)]
        recommended_action = str(governance.get('recommended_action') or '').strip()
        if recommended_action == 'replan_strategy' and not any(item.get('action') == 'replan_strategy' for item in actions):
            actions.insert(0, self._guidance_action('replan_strategy', 'Replanificar', 'Reconstruir la estrategia usando el mismo objetivo, evidencia y aprendizaje.'))
        if bool(governance.get('should_consult')):
            assistant_kind = str(governance.get('assistant_kind') or '').strip().lower()
            if assistant_kind == 'codex':
                consult_action = 'consult_codex'
                consult_label = 'Consultar Codex'
                consult_detail = 'Contrastar el siguiente cambio tecnico con evidencia verificable.'
            elif assistant_kind == 'claude':
                consult_action = 'consult_claude'
                consult_label = 'Consultar Claude'
                consult_detail = 'Contrastar la explicacion o la estrategia con una sesion dedicada de Claude.'
            elif assistant_kind == 'ollama':
                consult_action = 'consult_ollama'
                consult_label = 'Consultar Ollama'
                consult_detail = 'Resolver la consulta con la via local automatica antes de escalar a otra IA.'
            else:
                consult_action = 'consult_chatgpt'
                consult_label = 'Consultar ChatGPT'
                consult_detail = 'Contrastar la explicacion o el siguiente microajuste con apoyo externo.'
            if not any(item.get('action') == consult_action for item in actions):
                actions.insert(0, self._guidance_action(consult_action, consult_label, consult_detail))
        if bool(governance.get('should_replan')) and not any(item.get('action') == 'open_evolution_center' for item in actions):
            actions.append(self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Revisar el progreso, los bloqueos y la evidencia antes de repetir la ruta.'))
        if bool(governance.get('research_needed')) and not any(item.get('action') == 'audit_autonomy' for item in actions):
            actions.append(self._guidance_action('audit_autonomy', 'Auditar autonomia', 'Comprobar si la investigacion externa sigue siendo la mejor via.'))
        guidance['actions'] = actions[:4]
        guidance['governance'] = dict(governance)
        return guidance

    def _derive_session_status(self, *, intent, playbook, approvals: list[ApprovalCheckpoint]) -> AdaptiveSessionStatus:
        if intent.disposition.value == 'need_info':
            return AdaptiveSessionStatus.NEED_INFO
        if approvals:
            return AdaptiveSessionStatus.WAITING_APPROVAL
        return playbook.status

    def _initial_outcome(self, *, session: AdaptiveSession, pack) -> TaskOutcome:
        if session.intent.disposition.value == 'need_info':
            return TaskOutcome(
                status=session.playbook.steps[0].status if session.playbook and session.playbook.steps else None,
                summary='Falta un dato puntual antes de seguir con una estrategia util.',
                next_actions=session.intent.missing_requirements[:3],
                metadata={'mode': 'need_info'},
            )
        readiness_lines = [f"{item.title}: {item.status.value}" for item in session.capability_readiness[:4]]
        execution_state = self._execution_state(session)
        if session.approval_checkpoints:
            next_actions = ['Aprobar estrategia']
            if len(session.approval_checkpoints) > 1:
                next_actions.append('Aprobar fase siguiente')
        else:
            next_actions = ['Simular']
            if bool(execution_state.get('executor_available')) and not bool(execution_state.get('simulation_only')):
                next_actions.append('Ejecutar ahora')
            else:
                next_actions.append('Preparar Codex')
        summary = f"{pack.title}. Readiness: {' | '.join(readiness_lines) or 'sin capacidades declaradas'}."
        detail = str(execution_state.get('detail') or '')
        if detail:
            summary += f' Ejecucion: {detail}'
        return TaskOutcome(
            status=session.playbook.steps[0].status if session.playbook and session.playbook.steps else None,
            summary=summary,
            next_actions=next_actions,
            metadata={'mode': 'initial'},
        )

    def _build_route(self, session: AdaptiveSession, decision_context: DecisionContext) -> RoleRoute:
        route = self.role_router.route_from_decision(
            decision_context.route_decision,
            provider_name='Adaptive local orchestrator',
        )
        route.reason = f"{route.reason} Pack: {session.chosen_pack_title or session.chosen_pack_id} ({session.intent.disposition.value}).".strip()
        return route

    def _build_result(self, *, request: InferenceRequest, session: AdaptiveSession, pack, route: RoleRoute) -> InferenceResult:
        clarifications = []
        if session.intent.disposition.value == 'need_info':
            for missing in session.intent.missing_requirements[:2]:
                clarifications.append(ClarificationItem(prompt=missing, blocking=True))
        decision_context_payload = dict(session.metadata.get('decision_context') or {})
        perception_snapshot_payload = dict(session.metadata.get('perception_snapshot') or session.context.metadata.get('perception_snapshot') or {})
        assistant_guidance = dict(session.metadata.get('assistant_guidance') or decision_context_payload.get('assistant_guidance') or self._build_assistant_guidance(session, pack))
        summary = str(assistant_guidance.get('prompt') or self._render_summary(session))
        role_profile = next((item for item in self.role_router.role_profiles if item.role == session.intent.detected_role), self.role_router.role_profiles[0])
        report_kind = self._report_kind_for_role(session.intent.detected_role)
        guidance_checks = {
            'need_teaching': ['Abrir ensenanza', 'Consultar ChatGPT', 'Revisar capacidad aprendida'],
            'need_approval': ['Revisar aprobaciones', 'Confirmar siguiente fase'],
            'need_evolution_review': ['Revisar incidentes recientes', 'Abrir Centro Evolutivo'],
            'need_adapter': ['Consultar Codex', 'Simular fase siguiente', 'Abrir Centro Evolutivo'],
            'need_codex_fix': ['Consultar Codex', 'Preparar paquete para Codex', 'Revisar incidentes recurrentes'],
            'ready_execute': ['Simular fase siguiente', 'Verificar resultado esperado'],
            'need_info': ['Responder el dato faltante'],
        }
        return InferenceResult(
            request_id=request.request_id,
            provider_name='Adaptive local orchestrator',
            reasoning_mode=ReasoningMode.LOCAL,
            summary=summary,
            inferred_task=session.intent.title,
            confidence=session.intent.confidence,
            clarifications=clarifications,
            used_tools=list(dict.fromkeys(list(role_profile.default_tools) + list(route.tool_chain))),
            sources=session.evidence_refs[:6],
            follow_up_teachings=[item.suggested_next_step for item in session.capability_readiness if item.status.value in {'insufficient', 'partial'}][:4],
            report_kind=report_kind,
            detected_role=session.intent.detected_role,
            planner_used=session.intent.disposition.value == 'plan_then_execute',
            executor_model=route.model_name,
            improvement_hints=[item.suggested_next_step for item in session.capability_readiness if item.suggested_next_step][:4],
            recommended_next_checks=guidance_checks.get(str(assistant_guidance.get('mode') or ''), ['Revisar siguiente fase']),
            intent=session.intent.model_dump(mode='json'),
            chosen_pack=pack.model_dump(mode='json'),
            strategy_candidates=[item.model_dump(mode='json') for item in session.strategy_candidates],
            playbook=session.playbook.model_dump(mode='json') if session.playbook is not None else None,
            approval_checkpoints=[item.model_dump(mode='json') for item in session.approval_checkpoints],
            capability_readiness=[item.model_dump(mode='json') for item in session.capability_readiness],
            next_actions=[str(item.get('label')) for item in assistant_guidance.get('actions', []) if item.get('label')] or list(session.outcome.next_actions if session.outcome is not None else []),
            raw_output={
                'adaptive_session_id': session.session_id,
                'adaptive_session': session.model_dump(mode='json'),
                'session_readiness': session.context.session_readiness,
                'session_health': perception_snapshot_payload.get('session_health'),
                'assistant_guidance': assistant_guidance,
                'decision_context': decision_context_payload,
                'perception_snapshot': perception_snapshot_payload,
                'runtime_signals': list(perception_snapshot_payload.get('runtime_signals') or []),
                'ia_trace': list(perception_snapshot_payload.get('ia_trace') or []),
                'ia_trace_summary': dict(perception_snapshot_payload.get('metadata', {}).get('ia_trace_summary') or decision_context_payload.get('metadata', {}).get('ia_trace_summary') or {}),
                'visual_signal': dict(perception_snapshot_payload.get('visual_signal') or {}),
                'environment_self_model': dict(perception_snapshot_payload.get('environment_self_model') or {}),
                'world_model': dict(perception_snapshot_payload.get('world_model') or {}),
                'world_model_summary': dict(perception_snapshot_payload.get('metadata', {}).get('world_model_summary') or decision_context_payload.get('metadata', {}).get('world_model_summary') or {}),
                'portable_context_summary': dict(perception_snapshot_payload.get('metadata', {}).get('portable_context_summary') or decision_context_payload.get('metadata', {}).get('portable_context_summary') or {}),
                'external_state_flags': list(perception_snapshot_payload.get('external_state_flags') or decision_context_payload.get('metadata', {}).get('external_state_flags') or []),
            },
        )

    def _build_decision_context(
        self,
        *,
        request: InferenceRequest,
        session: AdaptiveSession,
        pack,
        assistant_guidance: dict[str, Any],
        perception_snapshot: PerceptionSnapshot | None = None,
    ) -> DecisionContext:
        route_decision = (
            perception_snapshot.decision_context.route_decision
            if perception_snapshot is not None
            else self.role_router.build_decision_from_intent(request=request, intent=session.intent)
        )
        live_audit = dict(perception_snapshot.live_audit or {}) if perception_snapshot is not None else dict(session.context.live_audit or {})
        goal_context = perception_snapshot.goal_context if perception_snapshot is not None else session.context.goal_context
        external_state_flags = list(perception_snapshot.external_state_flags or []) if perception_snapshot is not None else []
        ia_trace_summary = dict((perception_snapshot.metadata or {}).get('ia_trace_summary') or {}) if perception_snapshot is not None else {}
        environment_self_model = perception_snapshot.environment_self_model if perception_snapshot is not None else self._environment_self_model()
        world_model = perception_snapshot.world_model if perception_snapshot is not None else self._world_model()
        historical_preferred_assistant_kind = str(
            ia_trace_summary.get('best_assistant_kind')
            or next((item.get('recommended_assistant_kind') for item in session.context.experiment_insights if item.get('recommended_assistant_kind')), '')
            or ''
        ).strip().lower()
        historical_preferred_config_signature = str(
            ia_trace_summary.get('best_config_signature')
            or next((item.get('recommended_config_signature') for item in session.context.experiment_insights if item.get('recommended_config_signature')), '')
            or ''
        ).strip()
        supporting_trace_ids = [
            str(item)
            for item in (
                ia_trace_summary.get('reusable_trace_ids')
                or ia_trace_summary.get('winning_trace_ids')
                or ia_trace_summary.get('latest_trace_ids')
                or []
            )
            if str(item).strip()
        ][:8]
        memory_snapshot = (
            self.unified_memory_layer.build_snapshot(session.context)
            if self.unified_memory_layer is not None
            else self._memory_snapshot_from_context(session.context)
        )
        if not memory_snapshot and perception_snapshot is not None:
            memory_snapshot = perception_snapshot.memory_snapshot
        governance = self._build_governance(
            user_goal=request.user_goal,
            session_status=session.status.value,
            session_readiness=session.context.session_readiness,
            live_audit=live_audit,
            assistant_guidance=assistant_guidance,
            capability_snapshot=session.capability_readiness,
            approval_pending=bool(session.approval_checkpoints),
            goal_context=goal_context,
            intent_key=session.intent.intent_key,
            intent_disposition=session.intent.disposition.value,
            external_state_flags=external_state_flags,
            preferred_assistant_kind=historical_preferred_assistant_kind,
            preferred_config_signature=historical_preferred_config_signature,
            supporting_trace_ids=supporting_trace_ids,
            blocked_assistants=list(ia_trace_summary.get('blocked_assistants') or []),
            environment_self_model=environment_self_model,
            world_model=world_model,
        )
        guided_assistant = self._enrich_assistant_guidance(
            session=session,
            assistant_guidance=assistant_guidance,
            governance=governance,
        )
        preferred_assistant_kind = str(
            governance.get('assistant_kind')
            or historical_preferred_assistant_kind
            or ''
        ).strip().lower()
        preferred_config_signature = str(
            historical_preferred_config_signature
            or ''
        ).strip()
        portable_context_summary = (
            dict((perception_snapshot.metadata or {}).get('portable_context_summary') or {})
            if perception_snapshot is not None
            else dict(session.context.metadata.get('portable_context_summary') or {})
        )
        return DecisionContext(
            user_goal=request.user_goal,
            intent=session.intent,
            route_decision=route_decision,
            chosen_pack_id=pack.pack_id,
            chosen_pack_title=pack.title,
            site_id=session.context.site_id or session.intent.site_hint or '',
            site_display_name=session.context.site_display_name,
            evidence_refs=list(session.evidence_refs),
            capability_snapshot=list(session.capability_readiness),
            live_audit=live_audit,
            assistant_guidance=guided_assistant,
            goal_context=goal_context,
            memory_snapshot=memory_snapshot,
            governance=governance,
            metadata={
                'session_id': session.session_id,
                'intent_key': session.intent.intent_key,
                'decision_source': 'adaptive_task_orchestrator',
                'decision_stage': 'post_governance',
                'conversational_prompt': bool(session.intent.metadata.get('conversational_prompt')),
                'external_state_flags': external_state_flags,
                'ia_trace_summary': ia_trace_summary,
                'comparison_scope_key': str(ia_trace_summary.get('comparison_scope_key') or ''),
                'preferred_assistant_kind': preferred_assistant_kind,
                'preferred_config_signature': preferred_config_signature,
                'supporting_trace_ids': supporting_trace_ids,
                'adaptive_learning_summary': dict(session.context.metadata.get('adaptive_learning_summary') or {}),
                'learned_patterns': list(session.context.metadata.get('learned_patterns') or []),
                'validation_learning_summary': dict(session.context.metadata.get('validation_learning_summary') or {}),
                'environment_id': str(environment_self_model.environment_id or ''),
                'environment_scan_status': str(environment_self_model.scan_status or ''),
                'environment_notifications': list(environment_self_model.notifications or []),
                'environment_risk_signals': [item.model_dump(mode='json') for item in environment_self_model.risk_signals],
                'world_model_summary': self._world_model_summary(world_model),
                'portable_context_summary': portable_context_summary,
            },
        )

    def _decision_context_from_payload(self, *, payload: dict[str, Any], user_goal: str) -> DecisionContext:
        metadata = dict(payload.get('metadata') or {})
        existing = metadata.get('decision_context')
        if isinstance(existing, dict):
            try:
                return DecisionContext.model_validate(existing)
            except Exception:
                pass
        perception_payload = metadata.get('perception_snapshot')
        if isinstance(perception_payload, dict):
            try:
                perception = PerceptionSnapshot.model_validate(perception_payload)
                return perception.decision_context
            except Exception:
                pass
        intent = TaskIntent.model_validate(payload.get('intent') or {})
        context = TaskContext.model_validate(payload.get('context') or {})
        capability_snapshot = [
            CapabilityReadiness.model_validate(item)
            for item in (payload.get('capability_readiness') or [])
            if isinstance(item, dict)
        ]
        context.capability_snapshot = capability_snapshot
        request = InferenceRequest(
            user_goal=user_goal,
            task_role=intent.detected_role,
            auto_route=False,
            site_hint=context.site_id or intent.site_hint,
            role_hint=intent.detected_role,
        )
        assistant_guidance = dict(payload.get('assistant_guidance') or metadata.get('assistant_guidance') or {})
        pack = dict(payload.get('chosen_pack') or payload.get('pack') or {})
        perception_metadata = dict(dict(metadata.get('perception_snapshot') or {}).get('metadata') or {})
        ia_trace_summary = dict(perception_metadata.get('ia_trace_summary') or metadata.get('ia_trace_summary') or {})
        historical_preferred_assistant_kind = str(
            ia_trace_summary.get('best_assistant_kind')
            or ''
        ).strip().lower()
        historical_preferred_config_signature = str(ia_trace_summary.get('best_config_signature') or '').strip()
        supporting_trace_ids = [str(item) for item in (ia_trace_summary.get('reusable_trace_ids') or ia_trace_summary.get('latest_trace_ids') or []) if str(item).strip()][:8]
        world_model_payload = dict((dict(metadata.get('perception_snapshot') or {}).get('world_model') or metadata.get('world_model') or {}))
        try:
            world_model = WorldModelSnapshot.model_validate(world_model_payload) if world_model_payload else self._world_model()
        except Exception:
            world_model = self._world_model()
        governance = self._build_governance(
            user_goal=user_goal,
            session_status=str(payload.get('status') or ''),
            session_readiness=context.session_readiness,
            live_audit=context.live_audit,
            assistant_guidance=assistant_guidance,
            capability_snapshot=capability_snapshot,
            approval_pending=bool(payload.get('approval_checkpoints') or []),
            goal_context=context.goal_context,
            intent_key=intent.intent_key,
            intent_disposition=intent.disposition.value,
            external_state_flags=list((dict(metadata.get('perception_snapshot') or {}).get('external_state_flags') or metadata.get('external_state_flags') or [])),
            preferred_assistant_kind=historical_preferred_assistant_kind,
            preferred_config_signature=historical_preferred_config_signature,
            supporting_trace_ids=supporting_trace_ids,
            blocked_assistants=list(ia_trace_summary.get('blocked_assistants') or []),
            world_model=world_model,
        )
        guided_assistant = self._enrich_assistant_guidance(
            session=AdaptiveSession(
                user_goal=user_goal,
                intent=intent,
                context=context,
                chosen_pack_id=str(pack.get('pack_id') or payload.get('chosen_pack_id') or ''),
                chosen_pack_title=str(pack.get('title') or payload.get('chosen_pack_title') or ''),
                status=self._session_status_from_value(str(payload.get('status') or AdaptiveSessionStatus.PLANNED.value)),
                capability_readiness=capability_snapshot,
            ),
            assistant_guidance=assistant_guidance,
            governance=governance,
        )
        preferred_assistant_kind = str(
            governance.get('assistant_kind')
            or historical_preferred_assistant_kind
            or ''
        ).strip().lower()
        preferred_config_signature = str(historical_preferred_config_signature or '').strip()
        portable_context_summary = dict(
            dict(metadata.get('decision_context') or {}).get('metadata', {}).get('portable_context_summary')
            or dict(metadata.get('perception_snapshot') or {}).get('metadata', {}).get('portable_context_summary')
            or context.metadata.get('portable_context_summary')
            or {}
        )
        return DecisionContext(
            user_goal=user_goal,
            intent=intent,
            route_decision=self.role_router.build_decision_from_intent(request=request, intent=intent),
            chosen_pack_id=str(pack.get('pack_id') or payload.get('chosen_pack_id') or ''),
            chosen_pack_title=str(pack.get('title') or payload.get('chosen_pack_title') or ''),
            site_id=context.site_id or intent.site_hint or '',
            site_display_name=context.site_display_name,
            evidence_refs=list(payload.get('evidence_refs') or context.evidence_summary or []),
            capability_snapshot=capability_snapshot,
            live_audit=dict(context.live_audit or {}),
            assistant_guidance=guided_assistant,
            goal_context=context.goal_context,
            memory_snapshot=self._memory_snapshot_from_context(context),
            governance=governance,
            metadata={
                'session_id': str(payload.get('session_id') or ''),
                'intent_key': intent.intent_key,
                'decision_source': 'adaptive_payload',
                'decision_stage': 'payload_reconstruction',
                'conversational_prompt': bool(intent.metadata.get('conversational_prompt')),
                'external_state_flags': list((dict(metadata.get('perception_snapshot') or {}).get('external_state_flags') or metadata.get('external_state_flags') or [])),
                'ia_trace_summary': ia_trace_summary,
                'comparison_scope_key': str(ia_trace_summary.get('comparison_scope_key') or ''),
                'preferred_assistant_kind': preferred_assistant_kind,
                'preferred_config_signature': preferred_config_signature,
                'supporting_trace_ids': supporting_trace_ids,
                'adaptive_learning_summary': dict(context.metadata.get('adaptive_learning_summary') or {}),
                'learned_patterns': list(context.metadata.get('learned_patterns') or []),
                'validation_learning_summary': dict(context.metadata.get('validation_learning_summary') or {}),
                'world_model_summary': self._world_model_summary(world_model),
                'portable_context_summary': portable_context_summary,
            },
        )

    def _memory_snapshot_from_context(self, context: TaskContext) -> dict[str, Any]:
        if self.unified_memory_layer is not None:
            return self.unified_memory_layer.build_snapshot(context)
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
        service = getattr(self.context_assembler, 'environment_self_awareness_service', None)
        if service is None:
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            return service.current_model()
        except Exception:
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _world_model(self) -> WorldModelSnapshot:
        service = getattr(self.context_assembler, 'world_model_service', None)
        if service is None:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            return service.current_model()
        except Exception:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _world_model_unresolved(self, world_model: WorldModelSnapshot | None) -> bool:
        if world_model is None:
            return True
        if world_model.tool_live_status or world_model.active_windows or world_model.detected_blocks:
            return False
        return float(world_model.confidence or 0.0) <= 0.05

    def _world_model_summary(self, world_model: WorldModelSnapshot | None) -> dict[str, Any]:
        model = world_model if isinstance(world_model, WorldModelSnapshot) else WorldModelSnapshot()
        by_assistant = {
            item.assistant_kind: item
            for item in model.tool_live_status
            if str(item.assistant_kind or '').strip()
        }
        return {
            'focused_window': str((model.focused_window.title if model.focused_window is not None else '') or ''),
            'network_status': str(model.network_status.status or ''),
            'detected_blocks': list(model.detected_blocks or []),
            'blocked_routes': [
                {
                    'block_type': item.block_type,
                    'target_scope': item.target_scope,
                    'assistant_kind': item.assistant_kind,
                }
                for item in (model.block_records or [])[:8]
            ],
            'permission_gates': [
                {
                    'scope': item.scope,
                    'assistant_kind': item.assistant_kind,
                    'status': item.status,
                }
                for item in (model.permission_gates or [])[:6]
            ],
            'active_window_count': len(model.active_windows or []),
            'confidence': float(model.confidence or 0.0),
            'freshness_ms': int(model.freshness_ms or 0),
            'codex_status': {
                'status': str((by_assistant.get('codex').status if by_assistant.get('codex') is not None else '') or ''),
                'thread_status': str((by_assistant.get('codex').thread_status if by_assistant.get('codex') is not None else '') or ''),
                'messages_status': str((by_assistant.get('codex').messages_status if by_assistant.get('codex') is not None else '') or ''),
            },
            'chatgpt_status': self._tool_world_summary(by_assistant.get('chatgpt')),
            'claude_status': self._tool_world_summary(by_assistant.get('claude')),
            'ollama_status': self._tool_world_summary(by_assistant.get('ollama')),
            'last_updated': model.last_updated.isoformat() if model.last_updated is not None else '',
        }

    def _tool_world_summary(self, tool: Any) -> dict[str, Any]:
        return {
            'status': str((tool.status if tool is not None else '') or ''),
            'session_status': str((tool.session_status if tool is not None else '') or ''),
            'messages_status': str((tool.messages_status if tool is not None else '') or ''),
            'permission_state': str((tool.permission_state if tool is not None else '') or ''),
            'probe_status': str((tool.probe_status if tool is not None else '') or ''),
        }

    def preflight_external_assistant(self, *, user_goal: str, assistant_kind: str) -> dict[str, Any]:
        normalized_assistant = str(assistant_kind or '').strip().lower()
        world_model_service = getattr(self.context_assembler, 'world_model_service', None)
        world_model = (
            world_model_service.request_refresh(reason=f'preflight_external:{normalized_assistant or "external"}', full=True)
            if world_model_service is not None
            else self._world_model()
        )
        environment_self_model = self._environment_self_model()
        governance = self._build_governance(
            user_goal=user_goal,
            session_status=AdaptiveSessionStatus.READY_TO_EXECUTE.value,
            session_readiness={'live_audit_action': f'consult_{normalized_assistant}'},
            live_audit={'decision_action': f'consult_{normalized_assistant}', 'summary': 'Preflight antes de consulta externa.'},
            assistant_guidance={'mode': 'manual_external_consultation'},
            capability_snapshot=[],
            approval_pending=False,
            goal_context=None,
            intent_key='general.assistance',
            intent_disposition='answer_now',
            external_state_flags=[],
            preferred_assistant_kind=normalized_assistant,
            environment_self_model=environment_self_model,
            world_model=world_model,
        )
        permission_gates = [
            item for item in (world_model.permission_gates or [])
            if item.assistant_kind == normalized_assistant and item.status == 'requerido'
        ]
        approval_checkpoints: list[ApprovalCheckpoint] = []
        if governance.get('approval_required') or permission_gates:
            prompt = (
                permission_gates[0].detail
                if permission_gates
                else str(governance.get('reason') or 'Necesito aprobacion antes de seguir con la consulta externa.')
            )
            approval_checkpoints.append(
                ApprovalCheckpoint(
                    title=f'Permitir observacion de {normalized_assistant or "ventana externa"}',
                    detail=prompt,
                    phase_key='observation_permission',
                    reason='La ruta externa necesita observacion viva antes de continuar.',
                    risk_level=IssueSeverity.MEDIUM,
                    metadata={
                        'assistant_kind': normalized_assistant,
                        'permission_gates': [item.model_dump(mode='json') for item in permission_gates],
                    },
                )
            )
        return {
            'assistant_kind': normalized_assistant,
            'world_model': world_model.model_dump(mode='json'),
            'world_model_summary': self._world_model_summary(world_model),
            'governance': governance,
            'approval_checkpoints': [item.model_dump(mode='json') for item in approval_checkpoints],
            'blocked': bool(governance.get('block_risky_action') or governance.get('approval_required')),
            'reason': str(governance.get('reason') or ''),
        }

    def _build_governance(
        self,
        *,
        user_goal: str,
        session_status: str,
        session_readiness: dict[str, Any],
        live_audit: dict[str, Any],
        assistant_guidance: dict[str, Any],
        capability_snapshot: list[CapabilityReadiness],
        approval_pending: bool,
        goal_context: GoalContext | dict[str, Any] | None = None,
        intent_key: str = '',
        intent_disposition: str = '',
        external_state_flags: list[str] | None = None,
        preferred_assistant_kind: str = '',
        preferred_config_signature: str = '',
        supporting_trace_ids: list[str] | None = None,
        blocked_assistants: list[str] | None = None,
        environment_self_model: EnvironmentSelfModel | None = None,
        world_model: WorldModelSnapshot | None = None,
    ) -> dict[str, Any]:
        if self.autonomy_governance_policy is not None:
            return self.autonomy_governance_policy.evaluate(
                user_goal=user_goal,
                session_status=session_status,
                session_readiness=session_readiness,
                live_audit=live_audit,
                assistant_guidance=assistant_guidance,
                capability_snapshot=capability_snapshot,
                approval_pending=approval_pending,
                goal_context=goal_context,
                intent_key=intent_key,
                intent_disposition=intent_disposition,
                external_state_flags=external_state_flags,
                preferred_assistant_kind=preferred_assistant_kind,
                preferred_config_signature=preferred_config_signature,
                supporting_trace_ids=supporting_trace_ids,
                blocked_assistants=blocked_assistants,
                environment_self_model=environment_self_model,
                world_model=world_model,
            )
        guidance_mode = str(assistant_guidance.get('mode') or '').strip().lower()
        live_action = str(session_readiness.get('live_audit_action') or live_audit.get('decision_action') or '').strip().lower()
        summary = str(live_audit.get('summary') or assistant_guidance.get('prompt') or '').strip()
        if approval_pending or session_status == AdaptiveSessionStatus.WAITING_APPROVAL.value:
            return {
                'autonomy_level': 'human_gate',
                'should_consult': False,
                'assistant_kind': '',
                'recommended_action': 'stop_and_wait_user',
                'reason': 'La estrategia necesita aprobacion humana antes de seguir.',
                'confidence': 0.82,
                'approval_required': True,
                'block_risky_action': True,
                'require_sandbox': False,
                'should_replan': False,
                'should_retry': False,
                'research_needed': False,
                'blockers': ['La siguiente fase requiere aprobacion humana.'],
                'diagnostic_category': guidance_mode,
                'decision_source': 'adaptive_task_orchestrator',
                'external_state_flags': list(external_state_flags or []),
            }
        return {
            'autonomy_level': 'autonomous_local',
            'should_consult': False,
            'assistant_kind': '',
            'recommended_action': live_action or 'continue_local',
            'reason': summary or 'La via local actual sigue siendo suficiente con la evidencia disponible.',
            'confidence': 0.6,
            'approval_required': False,
            'block_risky_action': False,
            'require_sandbox': False,
            'should_replan': False,
            'should_retry': False,
            'research_needed': False,
            'blockers': [],
            'diagnostic_category': guidance_mode,
            'decision_source': 'adaptive_task_orchestrator',
            'external_state_flags': list(external_state_flags or []),
        }

    def _has_external_response(self, result: dict[str, Any]) -> bool:
        return bool(
            result.get('response_validation')
            or result.get('adoption_plan')
            or result.get('response_ingested_at_utc')
            or result.get('response_source')
        )

    def _guidance_for_external_response(self, result: dict[str, Any]) -> dict[str, Any]:
        next_action = str(result.get('next_action') or 'open_evolution_center')
        validation = dict(result.get('response_validation') or {})
        adoption = dict(result.get('adoption_plan') or {})
        return {
            'mode': 'external_response_interpreted',
            'title': 'Respuesta externa interpretada',
            'prompt': (
                f"{str(result.get('detail') or result.get('response_summary') or 'La respuesta externa ya quedo integrada.')} "
                f"Validacion: {validation.get('status') or 'n/d'} | via segura: {adoption.get('execution_lane') or 'n/d'} | "
                f"sandbox: {bool(validation.get('sandbox_required'))}."
            ).strip(),
            'actions': [
                self._guidance_action(next_action, 'Seguir con la respuesta', 'Aplicar la siguiente accion segura sugerida por la respuesta externa.'),
                self._guidance_action('audit_autonomy', 'Auditar autonomia', 'Revisar si la ruta y la validacion siguen bien calibradas.'),
            ],
        }

    def _guidance_for_pending_external_response(self, result: dict[str, Any]) -> dict[str, Any]:
        assistant_kind = str(result.get('assistant_kind') or '')
        assistant_title = 'Codex' if assistant_kind == 'codex' else 'ChatGPT' if assistant_kind == 'chatgpt' else 'la asistencia externa'
        return {
            'mode': 'waiting_external_response',
            'title': f'Esperando respuesta de {assistant_title}',
            'prompt': f'La consulta externa ya quedo preparada con {assistant_title}. Cuando recibas la respuesta, puedes ingerirla para seguir con el mismo caso.',
            'actions': [
                self._guidance_action('ingest_external_response', 'Ingerir respuesta', 'Pegar o leer la respuesta externa para convertirla en siguiente accion.'),
                self._guidance_action('audit_autonomy', 'Auditar autonomia', 'Revisar la ruta elegida antes de escalar de nuevo.'),
            ],
        }

    def _guidance_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
        return {'action': action, 'label': label, 'detail': detail}

    def _build_assistant_guidance(self, session: AdaptiveSession, pack) -> dict[str, object]:
        site_name = session.context.site_display_name or session.context.site_id or session.intent.site_hint or 'el flujo actual'
        approvals = [item for item in session.approval_checkpoints if item.decision.value == 'pending']
        session_readiness = session.context.session_readiness or {}
        execution_state = self._execution_state(session)
        incident_count = int(session_readiness.get('incident_count', len(session.context.recent_incidents)) or 0)
        dominant_incident = session_readiness.get('dominant_incident') or (session.context.recent_incidents[0].get('incident_kind', '') if session.context.recent_incidents else '')
        weak_capabilities = [item for item in session.capability_readiness if item.status.value in {'insufficient', 'partial'}]
        low_visual = any(
            (
                float(item.metadata.get('visual_alignment_score', 0.0) or 0.0) < 0.45
                or float(item.metadata.get('critical_object_coverage', item.metadata.get('login_visual_completeness', 0.0)) or 0.0) < 0.4
            )
            for item in weak_capabilities
        )
        no_teaching = not bool(session.context.recent_teachings)
        lead_teaching = session.context.recent_teachings[0] if session.context.recent_teachings else {}
        strong_teaching_ready = bool(lead_teaching) and (
            str(lead_teaching.get('login_status') or '') == 'ready'
            and str(lead_teaching.get('learning_status') or '') == 'ready'
            and float(lead_teaching.get('critical_object_coverage', 0.0) or 0.0) >= 0.66
            and float(lead_teaching.get('login_visual_completeness', 0.0) or 0.0) >= 0.66
            and int(lead_teaching.get('red_count', 0) or 0) == 0
        )
        repeated_technical = (not strong_teaching_ready) and incident_count >= 3 and dominant_incident in {
            'bridge_lag',
            'navigation_stall',
            'session_restore_weak',
            'visual_alignment_weak',
            'critical_object_missing',
        }
        is_tool_flow = session.intent.detected_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} or session.chosen_pack_id.startswith('tools.')
        teaching_gap = bool(weak_capabilities) and (no_teaching or low_visual) and not is_tool_flow

        if session.intent.disposition.value == 'need_info':
            question = session.intent.missing_requirements[0] if session.intent.missing_requirements else 'Necesito un dato puntual adicional.'
            return {
                'mode': 'need_info',
                'title': 'Falta un dato puntual',
                'prompt': f'Antes de seguir necesito esto: {question}.',
                'actions': [
                    self._guidance_action('open_teaching_studio', 'Abrir ensenanza', 'Si prefieres mostrar el flujo en vez de explicarlo.'),
                ],
            }
        if teaching_gap:
            prompt = (
                f'Puedo ayudarte con {site_name}, pero todavia me falta una ensenanza limpia o evidencia visual suficiente para hacerlo con confianza. '
                'Si quieres, abro Estudio de ensenanza para capturar ese flujo corto ahora.'
            )
            if dominant_incident:
                prompt += f' Tambien veo incidentes recientes como {dominant_incident}.'
            if repeated_technical:
                prompt += ' Ademas, no parece ser solo una falta de ensenanza: tambien hay un problema tecnico que conviene revisar o escalar.'
            actions = [
                self._guidance_action('open_teaching_studio', 'Abrir ensenanza', 'Capturar el flujo que falta o corregir el replay.'),
                self._guidance_action('consult_chatgpt', 'Consultar ChatGPT', 'Pedir ayuda para explicar el hueco de ensenanza o el siguiente microajuste.'),
            ]
            if repeated_technical:
                actions.append(self._guidance_action('prepare_codex_packet', 'Preparar Codex', 'Armar el caso tecnico verificable.'))
                actions.append(self._guidance_action('consult_codex', 'Consultar Codex', 'Escalar el problema tecnico con el contexto actual.'))
            if incident_count:
                actions.append(self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Revisar incidentes y evidencia reciente.'))
            return {
                'mode': 'need_teaching',
                'title': 'Hace falta ensenanza',
                'prompt': prompt,
                'actions': actions[:4],
            }
        if is_tool_flow and not bool(execution_state.get('executor_available')):
            return {
                'mode': 'need_adapter',
                'title': 'Falta herramienta local disponible',
                'prompt': 'La ruta Tool Teaching ya esta activa, pero no hay una ToolCard disponible o validada para esta tarea. Puedes revisar las herramientas conocidas, correr sandbox o preparar el caso tecnico.',
                'actions': [
                    self._guidance_action('consult_codex', 'Consultar Codex', 'Abrir la via externa mas tecnica para revisar el adaptador faltante.'),
                    self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Revisar ToolCards, validacion y trazas recientes.'),
                    self._guidance_action('prepare_codex_packet', 'Preparar Codex', 'Escalar el caso si falta adaptador o wrapper.'),
                ],
            }
        if repeated_technical and not no_teaching:
            return {
                'mode': 'need_codex_fix',
                'title': 'Parece un problema interno',
                'prompt': (
                    f'Puedo ayudarte con {site_name}, pero lo que veo ahora parece mas un problema interno del sistema que falta de instruccion. '
                    f'Tengo incidentes repetidos como {dominant_incident or "los recientes"}. Si quieres, te llevo al Centro Evolutivo y preparo el caso para Codex.'
                ),
                'actions': [
                    self._guidance_action('consult_codex', 'Consultar Codex', 'Abrir Codex con el contexto tecnico actual.'),
                    self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Inspeccionar incidentes, dossiers y backlog.'),
                    self._guidance_action('prepare_codex_packet', 'Preparar Codex', 'Armar el paquete tecnico verificable.'),
                    self._guidance_action('review_stack', 'Revisar stack', 'Actualizar el estado local antes de escalar.'),
                ],
            }
        if incident_count and not strong_teaching_ready:
            return {
                'mode': 'need_evolution_review',
                'title': 'Conviene revisar la evidencia',
                'prompt': (
                    f'Tengo contexto para {site_name}, pero antes de insistir conviene revisar la evidencia reciente. '
                    f'Hay incidentes como {dominant_incident or "los recientes"}. Puedo llevarte directo al Centro Evolutivo o preparar el caso para Codex.'
                ),
                'actions': [
                    self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Revisar incidentes, dossiers y backlog.'),
                    self._guidance_action('prepare_codex_packet', 'Preparar Codex', 'Armar el paquete tecnico verificable.'),
                ],
            }
        if approvals:
            actions = []
            if any(item.phase_key == 'strategy' for item in approvals):
                actions.append(self._guidance_action('approve_strategy', 'Aprobar estrategia', 'Confirmar la estrategia antes de seguir.'))
            if approvals:
                actions.append(self._guidance_action('approve_next_phase', approvals[-1].title or 'Aprobar fase siguiente', approvals[-1].detail or ''))
            return {
                'mode': 'need_approval',
                'title': 'Aprobacion requerida',
                'prompt': f'Ya tengo la estrategia lista para {site_name}. Solo me falta tu aprobacion para pasar a la siguiente fase.',
                'actions': actions[:2],
            }
        if not bool(execution_state.get('executor_available')) and not bool(execution_state.get('simulation_only')):
            return {
                'mode': 'need_adapter',
                'title': 'Falta adaptador operativo',
                'prompt': (
                    f'Ya tengo estrategia y contexto para {site_name}, pero todavia no hay un adaptador operativo real que ejecute esta fase. '
                    f'{execution_state.get("detail") or "Puedo seguir simulando o dejar el caso listo para Evolutivo y Codex."}'
                ),
                'actions': [
                    self._guidance_action('simulate', 'Simular', 'Revisar la fase disponible antes de conectarla a un ejecutor real.'),
                    self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Seguir la evidencia y el backlog tecnico.'),
                    self._guidance_action('prepare_codex_packet', 'Preparar Codex', 'Armar el caso tecnico verificable.'),
                ],
            }
        if bool(execution_state.get('simulation_only')):
            return {
                'mode': 'ready_execute',
                'title': 'Listo para guiado o simulacion',
                'prompt': f'Ya tengo suficiente contexto para seguir con {site_name}, pero esta fase se mantiene en simulacion o guiado por su nivel de riesgo.',
                'actions': [
                    self._guidance_action('simulate', 'Simular', 'Ver la siguiente fase antes de pedir otra aprobacion.'),
                    self._guidance_action('open_evolution_center', 'Ver evolutivo', 'Revisar evidencia y estado del flujo.'),
                ],
            }
        return {
            'mode': 'ready_execute',
            'title': 'Listo para avanzar',
            'prompt': f'Ya tengo suficiente contexto para seguir con {site_name}. Puedes simular o ejecutar la siguiente fase cuando quieras.',
            'actions': [
                self._guidance_action('simulate', 'Simular', 'Ver la siguiente fase antes de ejecutar.'),
                self._guidance_action('execute_now', 'Ejecutar ahora', 'Pasar a la fase operativa disponible.'),
            ],
        }

    def _render_summary(self, session: AdaptiveSession) -> str:
        if session.intent.disposition.value == 'need_info':
            question = session.intent.missing_requirements[0] if session.intent.missing_requirements else 'Necesito un dato puntual adicional.'
            return f'Necesito un dato concreto para seguir: {question}.'
        candidate = session.strategy_candidates[0] if session.strategy_candidates else None
        readiness_lines = [f"{item.title}: {item.status.value}" for item in session.capability_readiness[:4]]
        approvals = len([item for item in session.approval_checkpoints if item.decision.value == 'pending'])
        execution_state = self._execution_state(session)
        parts = [
            f"Entendi la tarea como {session.intent.title}.",
            f"Pack elegido: {session.chosen_pack_title or session.chosen_pack_id}.",
        ]
        if candidate is not None:
            parts.append(f"Estrategia propuesta: {candidate.title}.")
        if readiness_lines:
            parts.append('Capacidades: ' + ' | '.join(readiness_lines) + '.')
        if approvals:
            parts.append(f'Tengo {approvals} checkpoint(s) de aprobacion antes de la fase critica.')
        elif session.playbook is not None:
            parts.append(f'Siguiente fase: {session.playbook.next_phase or "ejecucion"}.')
        if execution_state:
            parts.append(f"Ejecucion operativa: {execution_state.get('detail', 'sin detalle')}.")
        if session.context.evidence_summary:
            parts.append('Evidencia usada: ' + ' '.join(session.context.evidence_summary[:2]))
        if session.outcome is not None and session.outcome.next_actions:
            parts.append('Proximo paso sugerido: ' + '; '.join(session.outcome.next_actions[:3]) + '.')
        return ' '.join(parts)

    def _execution_state(self, session: AdaptiveSession) -> dict[str, object]:
        state = session.metadata.get('execution_state')
        return dict(state) if isinstance(state, dict) else {}

    def _report_kind_for_role(self, role: TaskRole) -> ReportKind:
        mapping = {
            TaskRole.TRAINING: ReportKind.TRAINING_GUIDANCE,
            TaskRole.KNOWLEDGE: ReportKind.KNOWLEDGE_BRIEF,
            TaskRole.ANALYTICS: ReportKind.ANALYTICS_REPORT,
            TaskRole.CUSTOMER_SUPPORT: ReportKind.CUSTOMER_RESPONSE,
            TaskRole.PROJECT_EVOLUTION: ReportKind.ENGINEERING_REVIEW,
            TaskRole.RESEARCH: ReportKind.RESEARCH_BRIEF,
            TaskRole.VISUAL: ReportKind.VISUAL_ANALYSIS,
        }
        return mapping.get(role, ReportKind.CHAT)













