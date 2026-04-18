from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSessionStatus,
    CapabilityReadiness,
    EnvironmentSelfModel,
    ExternalStateFlag,
    GoalContext,
    IssueSeverity,
    WorldModelSnapshot,
    canonical_external_state_flags,
)


class AutonomyGovernancePolicy:
    """Central policy for deciding when the system should act, consult, retry or replan."""

    _TECHNICAL_INCIDENTS = {
        'bridge_lag',
        'navigation_stall',
        'session_restore_weak',
        'visual_alignment_weak',
        'critical_object_missing',
    }

    def evaluate(
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
        environment_self_model: EnvironmentSelfModel | dict[str, Any] | None = None,
        world_model: WorldModelSnapshot | dict[str, Any] | None = None,
        ambiguity_score: float = 0.0,
        requires_clarification: bool = False,
        sub_intents: list[str] | None = None,
    ) -> dict[str, Any]:
        goal = self._normalize_goal_context(goal_context)
        environment = self._normalize_environment_self_model(environment_self_model)
        world = self._normalize_world_model(world_model)
        progress = float(goal.get('progress') or 0.0)
        blocker = str(goal.get('blocker') or '').strip()
        goal_status = str(goal.get('status') or '').strip().lower()
        goal_confidence = float(goal.get('confidence') or 0.0)
        external_states = canonical_external_state_flags(external_state_flags)
        historical_assistant = str(preferred_assistant_kind or '').strip().lower()
        blocked_assistant_set = {
            str(item or '').strip().lower()
            for item in (blocked_assistants or [])
            if str(item or '').strip()
        }
        if historical_assistant in blocked_assistant_set:
            historical_assistant = ''

        # ETAPA 2: Ambiguity and clarification check
        if requires_clarification or ambiguity_score > 0.75:
            sub_intents_list = sub_intents or []
            reason = 'Ambigüedad conversacional detectada. El mensaje tiene múltiples intenciones o no es suficientemente claro.'
            if requires_clarification and sub_intents_list:
                reason = f'Detecté varias intenciones: {", ".join(sub_intents_list[:3])}. Necesito que aclares cuál quieres que atienda primero.'
            elif ambiguity_score > 0.75:
                reason = f'Ambigüedad alta (score: {ambiguity_score:.2f}). Por favor, aclara tu petición antes de proceder.'
            return self._snapshot(
                autonomy_level='clarification_needed',
                recommended_action='solicitar_clarificacion',
                reason=reason,
                confidence=0.0,
                should_consult=True,
                blockers=[reason],
                diagnostic_category='conversation_ambiguity',
            )

        guidance_mode = str(assistant_guidance.get('mode') or '').strip().lower()
        live_action = str(session_readiness.get('live_audit_action') or live_audit.get('decision_action') or '').strip().lower()
        summary = str(live_audit.get('summary') or assistant_guidance.get('prompt') or '').strip()
        dominant_incident = str(session_readiness.get('dominant_incident') or '').strip()
        weak_capabilities = [item for item in capability_snapshot if item.status.value in {'insufficient', 'partial'}]

        blockers: list[str] = []
        if blocker:
            blockers.append(blocker)
        if weak_capabilities:
            blockers.append(str(weak_capabilities[0].suggested_next_step or weak_capabilities[0].title or 'Hay capacidades debiles en la ruta actual.'))
        if approval_pending:
            blockers.append('La siguiente fase requiere aprobacion humana antes de continuar.')

        normalized_goal = ' '.join(str(user_goal or '').lower().split())
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
        meta_assistant_prompt = (
            any(token in normalized_goal for token in ('codex', 'chatgpt', 'claude', 'ollama', 'ia', 'ias'))
            and any(token in normalized_goal for token in ('sabes', 'puedes', 'puedo', 'internamente', 'automatic', 'automatica', 'automático', 'respondieron'))
        )
        conversational_intent = (
            intent_key in {'general.assistance', 'knowledge.query'}
            and intent_disposition in {'answer_now', 'need_info'}
            and (conversational_prompt or meta_assistant_prompt)
        )
        explicit_assistant = self._explicit_assistant_request(normalized_goal)
        technical_pressure = guidance_mode in {'need_codex_fix', 'need_adapter'} or live_action == 'consult_codex' or (dominant_incident in self._TECHNICAL_INCIDENTS and bool(weak_capabilities))
        teaching_pressure = guidance_mode == 'need_teaching'
        failed_or_blocked = session_status in {
            AdaptiveSessionStatus.FAILED.value,
            AdaptiveSessionStatus.ABORTED.value,
            AdaptiveSessionStatus.NEED_INFO.value,
        }
        ready_but_guarded = session_status in {
            AdaptiveSessionStatus.READY_TO_EXECUTE.value,
            AdaptiveSessionStatus.EXECUTING.value,
        }
        progress_conflict = progress >= 0.8 and failed_or_blocked

        confidence = max(
            min(goal_confidence, 1.0),
            min(float(live_audit.get('confidence') or 0.0), 1.0),
            0.45 if ready_but_guarded else 0.35,
        )

        environment_guard = self._environment_guard(
            environment=environment,
            confidence=confidence,
            blockers=blockers,
            diagnostic_category=guidance_mode,
            external_state_flags=external_states,
        )
        if environment_guard is not None:
            return environment_guard

        world_model_guard = self._world_model_guard(
            world_model=world,
            confidence=confidence,
            blockers=blockers,
            diagnostic_category=guidance_mode,
            external_state_flags=external_states,
            explicit_assistant=explicit_assistant,
            historical_assistant=historical_assistant,
            technical_pressure=technical_pressure,
        )
        if world_model_guard is not None:
            return world_model_guard

        if approval_pending or session_status == AdaptiveSessionStatus.WAITING_APPROVAL.value:
            return self._snapshot(
                autonomy_level='human_gate',
                recommended_action='stop_and_wait_user',
                reason='La estrategia necesita aprobacion humana antes de seguir.',
                confidence=max(confidence, 0.82),
                approval_required=True,
                block_risky_action=True,
                require_sandbox=False,
                blockers=blockers,
                diagnostic_category=guidance_mode,
                external_state_flags=external_states,
            )

        if ExternalStateFlag.ACCOUNT_LIMITED.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason='La ruta externa quedo limitada por cuenta o cuota. IABV debe avisarlo con claridad y seguir con la mejor via local disponible mientras se resuelve el acceso.',
                confidence=max(confidence, 0.86),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[*blockers, 'La cuenta o cuota del asistente externo no permite continuar con esta ruta.'],
                diagnostic_category=guidance_mode or 'account_limited',
                external_state_flags=external_states,
            )

        if ExternalStateFlag.SESSION_EXPIRED.value in external_states or ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason='La sesion externa no quedo lista para seguir. IABV debe informar el bloqueo y continuar por la mejor via local mientras la sesion se recupera.',
                confidence=max(confidence, 0.84),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[*blockers, 'La sesion del asistente externo no quedo lista para continuar.'],
                diagnostic_category=guidance_mode or 'session_recovery',
                external_state_flags=external_states,
            )

        if ExternalStateFlag.WRONG_THREAD.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action='audit_autonomy',
                reason='La consulta externa parece estar asociada al hilo incorrecto y no debe darse por valida.',
                confidence=max(confidence, 0.81),
                research_needed=True,
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, 'La verificacion del hilo externo no coincide con lo esperado.'],
                diagnostic_category=guidance_mode or 'wrong_thread',
                external_state_flags=external_states,
            )

        if ExternalStateFlag.CAPTURE_UNVERIFIED.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='audit_autonomy',
                reason='La respuesta externa no quedo verificada con suficiente evidencia de captura.',
                confidence=max(confidence, 0.73),
                should_retry=True,
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, 'La captura de la respuesta externa sigue sin verificacion suficiente.'],
                diagnostic_category=guidance_mode or 'capture_unverified',
                external_state_flags=external_states,
            )

        if conversational_intent:
            return self._snapshot(
                autonomy_level='autonomous_local',
                recommended_action='continue_local',
                reason='La consulta actual es conversacional y debe resolverse localmente sin escalar incidentes tecnicos previos.',
                confidence=max(confidence, 0.72),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[],
                diagnostic_category=guidance_mode,
                external_state_flags=external_states,
            )

        if explicit_assistant:
            explicit_action = self._consult_action_for_assistant(explicit_assistant)
            return self._snapshot(
                autonomy_level='guarded_research' if explicit_assistant != 'ollama' else 'autonomous_local',
                recommended_action=explicit_action,
                reason=f'El usuario pidio una consulta externa dirigida a {explicit_assistant}; esa preferencia debe respetarse antes de reciclar incidentes o rutas previas.',
                confidence=max(confidence, 0.78),
                should_consult=True,
                research_needed=explicit_assistant != 'ollama',
                assistant_kind=explicit_assistant,
                approval_required=False,
                block_risky_action=False,
                require_sandbox=explicit_assistant == 'codex',
                blockers=blockers,
                diagnostic_category='explicit_external_consultation',
                external_state_flags=external_states,
            )

        if technical_pressure:
            consult_assistant = historical_assistant or 'codex'
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action=self._consult_action_for_assistant(consult_assistant),
                reason=(
                    f"{summary or 'La evidencia tecnica actual justifica una consulta externa verificable.'} "
                    f"El historico reciente favorece {consult_assistant}."
                ).strip() if historical_assistant else (summary or 'La evidencia tecnica actual justifica una consulta externa verificable.'),
                confidence=max(confidence, 0.74),
                should_consult=True,
                research_needed=consult_assistant != 'ollama',
                assistant_kind=consult_assistant,
                approval_required=False,
                block_risky_action=False,
                require_sandbox=consult_assistant == 'codex',
                blockers=blockers,
                diagnostic_category=guidance_mode or 'need_codex_fix',
                external_state_flags=external_states,
            )

        if teaching_pressure and ('explica' in user_goal.lower() or live_action == 'consult_chatgpt'):
            consult_assistant = historical_assistant or 'chatgpt'
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action=self._consult_action_for_assistant(consult_assistant),
                reason=(
                    f"{summary or 'Conviene contrastar el siguiente microajuste con una explicacion externa antes de reensenar.'} "
                    f"El historico reciente favorece {consult_assistant}."
                ).strip() if historical_assistant else (summary or 'Conviene contrastar el siguiente microajuste con una explicacion externa antes de reensenar.'),
                confidence=max(confidence, 0.68),
                should_consult=True,
                research_needed=consult_assistant != 'ollama',
                assistant_kind=consult_assistant,
                approval_required=False,
                block_risky_action=False,
                require_sandbox=consult_assistant == 'codex',
                blockers=blockers,
                diagnostic_category='need_teaching',
                external_state_flags=external_states,
            )

        if failed_or_blocked or progress_conflict or goal_status == 'blocked' or live_action in {'retry_after_rebuild', 'rebuild_learning'}:
            replan_reason = summary or 'La estrategia actual no consolido el objetivo y conviene replanificar sin perder contexto.'
            if progress_conflict:
                replan_reason = 'El objetivo figura muy avanzado, pero la ultima ejecucion no valido ese progreso. Conviene replanificar y verificar evidencia.'
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='replan_strategy',
                reason=replan_reason,
                confidence=max(confidence, 0.72),
                should_replan=True,
                should_retry=live_action == 'retry_after_rebuild',
                approval_required=False,
                block_risky_action=bool(blocker),
                require_sandbox=True,
                blockers=blockers,
                diagnostic_category=guidance_mode or 'replan',
                external_state_flags=external_states,
            )

        if ready_but_guarded:
            return self._snapshot(
                autonomy_level='guarded_execution',
                recommended_action=live_action or 'continue_local',
                reason=summary or 'La ruta local es suficiente, pero las acciones operativas deben seguir dentro del sandbox o guiadas.',
                confidence=max(confidence, 0.66),
                should_retry=live_action == 'retry_after_rebuild',
                approval_required=False,
                block_risky_action=False,
                require_sandbox=True,
                blockers=blockers,
                diagnostic_category=guidance_mode,
                external_state_flags=external_states,
            )

        return self._snapshot(
            autonomy_level='autonomous_local',
            recommended_action=live_action or 'continue_local',
            reason=summary or 'La evidencia local actual es suficiente para seguir sin escalar.',
            confidence=max(confidence, 0.6),
            should_retry=live_action == 'retry_after_rebuild',
            approval_required=False,
            block_risky_action=False,
            require_sandbox=False,
            blockers=blockers,
            diagnostic_category=guidance_mode,
            external_state_flags=external_states,
        )

    def _explicit_assistant_request(self, normalized_goal: str) -> str:
        if not normalized_goal:
            return ''
        if (
            any(token in normalized_goal for token in ('codex', 'chatgpt', 'claude', 'ollama'))
            and any(token in normalized_goal for token in ('sabes', 'puedes', 'puedo', 'internamente', 'automatic', 'automatica', 'autom?tico', 'respondieron'))
        ):
            return ''
        consult_verbs = (
            'consulta',
            'consulta externa',
            'consultar',
            'usa ',
            'utiliza ',
            'revisa con',
            'valida con',
            'pregunta a',
            'apoyate en',
            'ap?yate en',
            'razona con',
            'piensa con',
            'escala a',
            'escalalo a',
            'escalalo con',
        )
        if not any(token in normalized_goal for token in consult_verbs):
            return ''
        for assistant in ('chatgpt', 'claude', 'codex', 'ollama'):
            if assistant in normalized_goal:
                return assistant
        return ''

    def _consult_action_for_assistant(self, assistant_kind: str) -> str:
        assistant = str(assistant_kind or '').strip().lower()
        return {
            'codex': 'consult_codex',
            'chatgpt': 'consult_chatgpt',
            'claude': 'consult_claude',
            'ollama': 'consult_ollama',
        }.get(assistant, 'consult_chatgpt')

    def _snapshot(
        self,
        *,
        autonomy_level: str,
        recommended_action: str,
        reason: str,
        confidence: float,
        should_consult: bool = False,
        should_retry: bool = False,
        should_replan: bool = False,
        research_needed: bool = False,
        assistant_kind: str = '',
        approval_required: bool = False,
        block_risky_action: bool = False,
        require_sandbox: bool = False,
        blockers: list[str] | None = None,
        diagnostic_category: str = '',
        external_state_flags: list[str] | None = None,
        blocked_routes: list[str] | None = None,
        permission_gates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            'autonomy_level': autonomy_level,
            'should_consult': should_consult,
            'should_retry': should_retry,
            'should_replan': should_replan,
            'research_needed': research_needed,
            'assistant_kind': assistant_kind,
            'recommended_action': recommended_action,
            'reason': reason,
            'confidence': round(max(0.0, min(confidence, 0.99)), 4),
            'approval_required': approval_required,
            'block_risky_action': block_risky_action,
            'require_sandbox': require_sandbox,
            'blockers': [item for item in (blockers or []) if str(item).strip()][:4],
            'diagnostic_category': diagnostic_category,
            'decision_source': 'autonomy_governance_policy',
            'external_state_flags': list(external_state_flags or []),
            'blocked_routes': [item for item in (blocked_routes or []) if str(item).strip()][:6],
            'permission_gates': list(permission_gates or [])[:6],
        }

    def _environment_guard(
        self,
        *,
        environment: EnvironmentSelfModel,
        confidence: float,
        blockers: list[str],
        diagnostic_category: str,
        external_state_flags: list[str],
    ) -> dict[str, Any] | None:
        if environment is None:
            return None
        severe_risks = [
            risk for risk in environment.risk_signals
            if risk.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL}
        ]
        if not severe_risks:
            return None
        critical_kinds = {str(risk.kind or '') for risk in severe_risks}
        if not critical_kinds.intersection({'ram_critical', 'ram_pressure', 'gpu_temperature_critical', 'gpu_temperature_warning', 'cpu_pressure', 'throttling_detected'}):
            return None
        preferred_local_assistant = str(environment.ai_capacity.get('preferred_local_assistant_kind') or '').strip().lower()
        risk_notes = [risk.summary for risk in severe_risks][:3]
        return self._snapshot(
            autonomy_level='protective_local',
            recommended_action='continue_local',
            reason='El entorno actual esta bajo presion y la gobernanza debe degradar con gracia antes de lanzar trabajo mas pesado.',
            confidence=max(confidence, 0.8),
            should_consult=False,
            research_needed=False,
            assistant_kind=preferred_local_assistant if preferred_local_assistant == 'ollama' else '',
            approval_required=False,
            block_risky_action=True,
            require_sandbox=False,
            blockers=[*blockers, *risk_notes],
            diagnostic_category=diagnostic_category or 'environment_guard',
            external_state_flags=external_state_flags,
        )

    def _normalize_goal_context(self, goal_context: GoalContext | dict[str, Any] | None) -> dict[str, Any]:
        if goal_context is None:
            return {}
        if isinstance(goal_context, GoalContext):
            return goal_context.model_dump(mode='json')
        return dict(goal_context or {})

    def _normalize_environment_self_model(self, environment_self_model: EnvironmentSelfModel | dict[str, Any] | None) -> EnvironmentSelfModel:
        if isinstance(environment_self_model, EnvironmentSelfModel):
            return environment_self_model
        if isinstance(environment_self_model, dict) and environment_self_model:
            try:
                return EnvironmentSelfModel.model_validate(environment_self_model)
            except Exception:
                return EnvironmentSelfModel(scan_status='degraded')
        return EnvironmentSelfModel(scan_status='unavailable')

    def _normalize_world_model(self, world_model: WorldModelSnapshot | dict[str, Any] | None) -> WorldModelSnapshot:
        if isinstance(world_model, WorldModelSnapshot):
            return world_model
        if isinstance(world_model, dict) and world_model:
            try:
                return WorldModelSnapshot.model_validate(world_model)
            except Exception:
                return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _world_model_guard(
        self,
        *,
        world_model: WorldModelSnapshot,
        confidence: float,
        blockers: list[str],
        diagnostic_category: str,
        external_state_flags: list[str],
        explicit_assistant: str,
        historical_assistant: str,
        technical_pressure: bool,
    ) -> dict[str, Any] | None:
        if world_model is None:
            return None
        meaningful_signal = bool(
            world_model.tool_live_status
            or world_model.active_windows
            or world_model.detected_blocks
            or world_model.focused_window is not None
            or str(world_model.network_status.status or '').strip() not in {'', 'desconocido'}
        )
        if not meaningful_signal:
            return None

        assistant_hint = explicit_assistant or historical_assistant or ('codex' if technical_pressure else '')
        statuses = {
            str(item.assistant_kind or '').strip().lower(): item
            for item in (world_model.tool_live_status or [])
            if str(item.assistant_kind or '').strip()
        }
        permission_gates = [
            item for item in (world_model.permission_gates or [])
            if not assistant_hint or item.assistant_kind == assistant_hint
        ]
        if permission_gates:
            required_gate = next((item for item in permission_gates if item.status == 'requerido'), None)
            if required_gate is not None:
                required_routes = [str(item).strip() for item in (required_gate.required_for or []) if str(item).strip()]
                route_hint = required_routes[0] if required_routes else f'consult_{assistant_hint}' if assistant_hint else 'consult_external'
                return self._snapshot(
                    autonomy_level='guarded_research',
                    recommended_action='request_observation_permission',
                    reason=str(required_gate.detail or 'Necesito permiso explicito para observar el contenido visible antes de seguir con esta ruta.'),
                    confidence=max(confidence, 0.85),
                    approval_required=True,
                    block_risky_action=True,
                    require_sandbox=False,
                    blockers=[*blockers, str(required_gate.detail or 'Falta permiso para verificar la herramienta externa antes de usarla.')],
                    diagnostic_category=diagnostic_category or 'observation_permission_required',
                    external_state_flags=external_state_flags,
                    blocked_routes=[route_hint],
                    permission_gates=[item.model_dump(mode='json') for item in permission_gates],
                )

        block_records = [
            item for item in (world_model.block_records or [])
            if not assistant_hint
            or item.assistant_kind == assistant_hint
            or item.target_scope in {f'consult_{assistant_hint}', 'consult_external'}
        ]
        explicit_record = next(
            (
                item for item in block_records
                if item.block_type in {'wrong_thread', 'account_limited', 'browser_security_verification', 'assistant_unavailable', 'network_blocked'}
            ),
            None,
        )
        if explicit_record is not None:
            category = explicit_record.block_type
            reason_map = {
                'wrong_thread': f'{explicit_record.title or assistant_hint or "La herramienta"} esta abierto, pero el hilo activo no coincide con el workspace esperado.',
                'account_limited': f'{explicit_record.title or assistant_hint or "La herramienta"} muestra senales recientes de cuota, credito o mensajes agotados.',
                'browser_security_verification': f'{explicit_record.title or assistant_hint or "La herramienta"} quedo bloqueado por una verificacion de seguridad del sitio.',
                'assistant_unavailable': f'No pude confirmar que {explicit_record.title or assistant_hint or "la herramienta"} este disponible antes de usarla.',
                'network_blocked': 'La red no esta lista para sostener una consulta externa confiable en este momento.',
            }
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local' if category != 'wrong_thread' else 'audit_autonomy',
                reason=reason_map.get(category, explicit_record.reason or explicit_record.detail or 'La ruta externa no es viable en este momento.'),
                confidence=max(confidence, float(explicit_record.confidence or 0.0), 0.82),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, str(explicit_record.detail or explicit_record.reason or 'Hay un bloqueo operativo activo.')],
                diagnostic_category=diagnostic_category or category,
                external_state_flags=canonical_external_state_flags([*external_state_flags, category]),
                blocked_routes=[str(explicit_record.target_scope or '')],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )
        network = world_model.network_status
        if assistant_hint and assistant_hint != 'ollama' and network.status in {'desconectado', 'bloqueado'}:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason='La red no esta lista para sostener una consulta externa confiable en este momento.',
                confidence=max(confidence, 0.83),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, str(network.detail or 'La red no quedo disponible para esta via externa.')],
                diagnostic_category=diagnostic_category or 'network_blocked',
                external_state_flags=external_state_flags,
                blocked_routes=[f'consult_{assistant_hint}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        targeted = statuses.get(assistant_hint) if assistant_hint else None
        if targeted is None:
            return None

        targeted_blocks = canonical_external_state_flags(
            list(targeted.external_state_flags or []) + list(targeted.detected_blocks or [])
        )
        target_title = str(targeted.title or assistant_hint or 'la herramienta externa').strip()
        target_detail = str(targeted.detail or '').strip()

        if targeted.thread_status in {'otro_hilo_activo', 'sin_hilo_iabv'}:
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action='audit_autonomy',
                reason=f'{target_title} esta abierto, pero el hilo activo no coincide con el workspace esperado.',
                confidence=max(confidence, 0.84),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'El hilo activo no coincide con el workspace de IABV.'],
                diagnostic_category=diagnostic_category or 'wrong_thread',
                external_state_flags=canonical_external_state_flags([*external_state_flags, ExternalStateFlag.WRONG_THREAD.value]),
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        if targeted.messages_status == 'agotados_o_limitados' or ExternalStateFlag.ACCOUNT_LIMITED.value in targeted_blocks:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason=f'{target_title} muestra senales recientes de limite de cuenta, cuota o mensajes agotados.',
                confidence=max(confidence, 0.86),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'La cuenta o los mensajes de esta via externa no estan disponibles ahora mismo.'],
                diagnostic_category=diagnostic_category or 'account_limited',
                external_state_flags=canonical_external_state_flags([*external_state_flags, ExternalStateFlag.ACCOUNT_LIMITED.value]),
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        if 'browser_security_verification' in targeted_blocks:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason=f'{target_title} quedo bloqueado por una verificacion de seguridad del sitio y no conviene insistir como si fuera un selector roto.',
                confidence=max(confidence, 0.84),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'El sitio activo una verificacion de seguridad antes de abrir el chat.'],
                diagnostic_category=diagnostic_category or 'browser_security_verification',
                external_state_flags=canonical_external_state_flags([*external_state_flags, ExternalStateFlag.CAPTURE_UNVERIFIED.value]),
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        if targeted.status == 'no_disponible' and explicit_assistant:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason=f'No pude confirmar que {target_title} este disponible en este entorno antes de usarlo.',
                confidence=max(confidence, 0.76),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'La herramienta pedida no quedo confirmada como disponible.'],
                diagnostic_category=diagnostic_category or 'assistant_unavailable',
                external_state_flags=external_state_flags,
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        return None



