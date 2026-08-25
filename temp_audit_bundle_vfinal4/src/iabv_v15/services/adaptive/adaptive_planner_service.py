from __future__ import annotations

from collections import Counter
from typing import Any

from iabv_v15.domain.models import AdaptiveSessionStatus, CapabilityReadiness, CapabilityStatus, ExecutionPlaybook, PlaybookStep, RunStatus, StrategyCandidate, StrategyPack, TaskContext, TaskIntent


class AdaptivePlannerService:
    def build_playbook(
        self,
        *,
        intent: TaskIntent,
        context: TaskContext,
        pack: StrategyPack,
        capabilities: list[CapabilityReadiness],
        strategy_candidates: list[StrategyCandidate],
    ) -> ExecutionPlaybook:
        requires_approval = pack.approval_policy != 'never' or intent.sensitive or intent.monetary
        simulation_only = intent.sensitive or intent.monetary or pack.risk_level.value in {'high', 'critical'}
        candidate = strategy_candidates[0] if strategy_candidates else None
        weakest = next((item for item in capabilities if item.status in {CapabilityStatus.INSUFFICIENT, CapabilityStatus.PARTIAL}), None)
        recommendation = self._experiment_recommendation(candidate=candidate, context=context)
        live_audit = dict(context.live_audit or context.metadata.get('live_audit') or {})
        preferred_route = str((candidate.metadata if candidate is not None else {}).get('recommended_route') or recommendation.get('recommended_route') or '')
        reusable_patterns = self._matching_patterns(context=context, preferred_route=preferred_route)
        matching_pattern_ids = [str(item.get('pattern_id') or '') for item in reusable_patterns if item.get('pattern_id')]
        route_detail = self._route_detail(candidate=candidate, recommendation=recommendation)
        pattern_detail = self._pattern_detail(reusable_patterns)
        recommended_tool_id = str((candidate.metadata if candidate is not None else {}).get('recommended_tool_id') or '')
        recommended_scope = str((candidate.metadata if candidate is not None else {}).get('recommended_execution_scope') or '')
        alignment_score = float((candidate.metadata if candidate is not None else {}).get('experiment_alignment_score', 0.0) or 0.0)

        steps = [
            PlaybookStep(
                phase_key='understand_goal',
                title='Entender objetivo',
                description=f'Objetivo interpretado: {intent.title}.',
                status=RunStatus.SUCCESS,
                detail='La intencion ya fue clasificada y contextualizada.',
                metadata={
                    'site_id': context.site_id or intent.site_hint or '',
                    'intent_key': intent.intent_key,
                },
            ),
            PlaybookStep(
                phase_key='select_pack',
                title='Seleccionar pack',
                description=f'Se usa {pack.title}.',
                status=RunStatus.SUCCESS,
                detail=f'Pack elegido: {pack.pack_id}.',
                pack_id=pack.pack_id,
                metadata={
                    'domain_kind': pack.domain_kind,
                    'risk_level': pack.risk_level.value,
                },
            ),
            PlaybookStep(
                phase_key='validate_capabilities',
                title='Validar capacidades',
                description='Se revisa si las ensenanzas y la evidencia soportan la tarea.',
                status=RunStatus.SUCCESS if weakest is None else RunStatus.PARTIAL,
                detail='Todo listo.' if weakest is None else weakest.suggested_next_step,
                metadata={
                    'weakest_capability_id': weakest.capability_id if weakest is not None else '',
                    'interaction_pattern_count': len(context.interaction_patterns),
                    'experiment_insight_count': len(context.experiment_insights),
                },
            ),
            PlaybookStep(
                phase_key='propose_strategy',
                title='Proponer estrategia',
                description=(candidate.rationale if candidate is not None else 'Sin candidato explicito; se aplica la estrategia base del pack.'),
                status=RunStatus.SUCCESS,
                detail=self._compose_detail(
                    base_detail=(candidate.title if candidate is not None else pack.title),
                    route_detail=route_detail,
                    pattern_detail=pattern_detail,
                ),
                metadata={
                    'preferred_route': preferred_route,
                    'recommended_tool_id': recommended_tool_id,
                    'recommended_execution_scope': recommended_scope,
                    'experiment_alignment_score': alignment_score,
                    'matching_pattern_ids': matching_pattern_ids,
                    'matching_pattern_count': len(matching_pattern_ids),
                    'live_audit_action': str(live_audit.get('decision_action') or ''),
                },
            ),
        ]
        if requires_approval:
            steps.append(
                PlaybookStep(
                    phase_key='approval',
                    title='Checkpoint de aprobacion',
                    description='Se requiere aprobacion explicita antes de la fase sensible o monetaria.',
                    status=RunStatus.PARTIAL,
                    requires_approval=True,
                    detail='Pendiente de aprobacion.',
                    metadata={
                        'preferred_route': preferred_route,
                        'recommended_tool_id': recommended_tool_id,
                    },
                )
            )
        execute_detail = self._execute_detail(
            simulation_only=simulation_only,
            preferred_route=preferred_route,
            recommended_tool_id=recommended_tool_id,
            recommended_scope=recommended_scope,
            pattern_detail=pattern_detail,
        )
        steps.append(
            PlaybookStep(
                phase_key='execute',
                title='Ejecutar fase',
                description='Ejecutar o dejar preparada la siguiente fase operativa.',
                status=RunStatus.PARTIAL,
                requires_approval=requires_approval,
                executable=not simulation_only,
                simulation_only=simulation_only,
                detail=execute_detail,
                pack_id=pack.pack_id,
                capability_id=weakest.capability_id if weakest is not None else (capabilities[0].capability_id if capabilities else None),
                metadata={
                    'preferred_route': preferred_route,
                    'recommended_tool_id': recommended_tool_id,
                    'recommended_execution_scope': recommended_scope,
                    'matching_pattern_ids': matching_pattern_ids,
                    'matching_pattern_count': len(matching_pattern_ids),
                },
            )
        )
        # P2: multi-IA parallel steps when compound intent detected
        multi_ia_steps = self._multi_ia_parallel_steps(
            intent=intent,
            context=context,
            preferred_route=preferred_route,
            recommended_tool_id=recommended_tool_id,
        )
        steps.extend(multi_ia_steps)

        steps.extend(
            [
                PlaybookStep(
                    phase_key='verify',
                    title='Verificar resultado',
                    description='Confirmar senales de exito, incidentes y evidencia.',
                    status=RunStatus.PARTIAL,
                    detail=self._verify_detail(preferred_route=preferred_route, reusable_patterns=reusable_patterns),
                    metadata={
                        'preferred_route': preferred_route,
                        'matching_pattern_ids': matching_pattern_ids,
                    },
                ),
                PlaybookStep(
                    phase_key='record_outcome',
                    title='Registrar outcome',
                    description='Persistir resultado, evidencia y siguiente accion.',
                    status=RunStatus.PARTIAL,
                    detail=self._record_detail(preferred_route=preferred_route, reusable_patterns=reusable_patterns),
                    metadata={
                        'preferred_route': preferred_route,
                        'matching_pattern_ids': matching_pattern_ids,
                        'experiment_recommendation': recommendation,
                    },
                ),
            ]
        )
        if intent.disposition.value == 'answer_now' and not requires_approval:
            status = AdaptiveSessionStatus.COMPLETED
            next_phase = 'none'
        elif intent.disposition.value == 'need_info':
            status = AdaptiveSessionStatus.NEED_INFO
            next_phase = 'need_info'
        elif requires_approval:
            status = AdaptiveSessionStatus.WAITING_APPROVAL
            next_phase = 'approval'
        else:
            status = AdaptiveSessionStatus.READY_TO_EXECUTE
            next_phase = 'execute'
        summary = self._build_summary(
            intent=intent,
            pack=pack,
            candidate=candidate,
            weakest=weakest,
            context=context,
            reusable_patterns=reusable_patterns,
            recommendation=recommendation,
            preferred_route=preferred_route,
            live_audit=live_audit,
        )
        return ExecutionPlaybook(
            goal=intent.title,
            pack_id=pack.pack_id,
            summary=summary,
            status=status,
            steps=steps,
            next_phase=next_phase,
            requires_approval=requires_approval,
            simulation_only=simulation_only,
            metadata={
                'site_id': context.site_id or intent.site_hint or '',
                'pack_title': pack.title,
                'chosen_algorithm': candidate.algorithm_id if candidate is not None else '',
                'experiment_recommendation': recommendation,
                'preferred_route': preferred_route,
                'recommended_tool_id': recommended_tool_id,
                'recommended_execution_scope': recommended_scope,
                'interaction_pattern_count': len(context.interaction_patterns),
                'matching_pattern_count': len(matching_pattern_ids),
                'matching_pattern_ids': matching_pattern_ids,
                'live_audit': live_audit,
            },
        )

    def _build_summary(
        self,
        *,
        intent: TaskIntent,
        pack: StrategyPack,
        candidate: StrategyCandidate | None,
        weakest: CapabilityReadiness | None,
        context: TaskContext,
        reusable_patterns: list[dict[str, Any]],
        recommendation: dict[str, Any],
        preferred_route: str,
        live_audit: dict[str, Any],
    ) -> str:
        parts = [f'Pack {pack.title}.']
        if candidate is not None:
            parts.append(f'Estrategia propuesta: {candidate.title}.')
        if weakest is not None:
            parts.append(f'Capacidad debil: {weakest.title} en estado {weakest.status.value}.')
        if context.recent_incidents:
            lead = context.recent_incidents[0]
            parts.append(f"Incidente a vigilar: {lead['incident_kind']}.")
        if recommendation:
            route = recommendation.get('recommended_route') or preferred_route or 'fallback'
            parts.append(
                f"Laboratorio sugiere {route} para {recommendation.get('domain', 'general')} con score {float(recommendation.get('score', 0.0)):.2f}."
            )
        if reusable_patterns:
            channel_counts = Counter(str(item.get('channel') or '') for item in reusable_patterns if item.get('channel'))
            bits = ', '.join(f'{channel}:{count}' for channel, count in channel_counts.items())
            parts.append(
                f'Patrones reutilizables detectados: {len(reusable_patterns)}' + (f' ({bits}).' if bits else '.')
            )
        if live_audit:
            parts.append(
                f"Auditoria viva: {live_audit.get('summary') or 'sin resumen'}"
            )
        if intent.monetary:
            parts.append('Accion monetaria detectada: se obliga aprobacion explicita.')
        return ' '.join(parts)

    def _experiment_recommendation(self, *, candidate: StrategyCandidate | None, context: TaskContext) -> dict[str, Any]:
        if candidate is not None:
            metadata = candidate.metadata or {}
            recommendation = metadata.get('experiment_recommendation')
            if isinstance(recommendation, dict) and recommendation:
                return recommendation
        return context.experiment_insights[0] if context.experiment_insights else {}

    def _matching_patterns(self, *, context: TaskContext, preferred_route: str) -> list[dict[str, Any]]:
        patterns = list(context.interaction_patterns or [])
        if not patterns:
            return []
        desired_channels = self._channels_for_route(preferred_route)
        items: list[tuple[float, dict[str, Any]]] = []
        for pattern in patterns:
            score = float(pattern.get('success_count', 0) or 0) - float(pattern.get('failure_count', 0) or 0) * 0.5
            if context.site_id and pattern.get('site_id') == context.site_id:
                score += 2.0
            channel = str(pattern.get('channel') or '')
            if channel and channel in desired_channels:
                score += 1.5
            if pattern.get('reusable'):
                score += 0.5
            if score > 0:
                items.append((score, pattern))
        items.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in items[:4]]

    def _channels_for_route(self, preferred_route: str) -> set[str]:
        mapping = {
            'ui': {'ui'},
            'ocr_vision': {'ui'},
            'background': {'background'},
            'local': {'background'},
            'code_agent': {'background'},
            'math_evaluation': {'background'},
            'language_understanding': {'background'},
            'api': {'api'},
            'fallback': {'ui', 'background', 'api'},
        }
        return mapping.get(preferred_route or 'fallback', {'ui', 'background', 'api'})

    def _route_detail(self, *, candidate: StrategyCandidate | None, recommendation: dict[str, Any]) -> str:
        route = str((candidate.metadata if candidate is not None else {}).get('recommended_route') or recommendation.get('recommended_route') or '')
        if not route:
            return ''
        score = float((candidate.metadata if candidate is not None else {}).get('experiment_alignment_score', recommendation.get('score', 0.0)) or 0.0)
        return f'Ruta sugerida: {route} (score {score:.2f}).'

    def _pattern_detail(self, reusable_patterns: list[dict[str, Any]]) -> str:
        if not reusable_patterns:
            return ''
        lead = reusable_patterns[0]
        return (
            f"Patron reutilizable lider: {lead.get('title') or 'sin titulo'}"
            f" | canal {lead.get('channel') or 'n/d'}"
            f" | exitos {int(lead.get('success_count', 0) or 0)}."
        )

    def _compose_detail(self, *, base_detail: str, route_detail: str, pattern_detail: str) -> str:
        parts = [base_detail]
        if route_detail:
            parts.append(route_detail)
        if pattern_detail:
            parts.append(pattern_detail)
        return ' '.join(parts)

    def _execute_detail(
        self,
        *,
        simulation_only: bool,
        preferred_route: str,
        recommended_tool_id: str,
        recommended_scope: str,
        pattern_detail: str,
    ) -> str:
        parts: list[str] = []
        if preferred_route:
            parts.append(f'Ruta operativa preferida: {preferred_route}.')
        if recommended_tool_id:
            parts.append(f'Herramienta sugerida: {recommended_tool_id}.')
        if recommended_scope:
            parts.append(f'Alcance sugerido: {recommended_scope}.')
        if pattern_detail:
            parts.append(pattern_detail)
        if simulation_only:
            parts.append('La fase operativa se deja en simulacion o preparada hasta que exista aprobacion y adaptador confiable.')
        else:
            parts.append('La fase queda preparada para ejecucion por fases.')
        return ' '.join(parts).strip()

    def _verify_detail(self, *, preferred_route: str, reusable_patterns: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        if preferred_route:
            parts.append(f'Verificar que la ruta {preferred_route} deje senales observables consistentes.')
        if reusable_patterns:
            parts.append(f'Comparar contra {len(reusable_patterns)} patrones universales ya aprendidos antes de marcar exito.')
        else:
            parts.append('Se ejecuta despues de la fase operativa.')
        return ' '.join(parts)

    def _record_detail(self, *, preferred_route: str, reusable_patterns: list[dict[str, Any]]) -> str:
        parts = ['La sesion adaptativa deja traza reutilizable para evolutivo y Codex.']
        if preferred_route:
            parts.append(f'Registrar el resultado bajo la via {preferred_route}.')
        if reusable_patterns:
            parts.append('Actualizar el episodio o patron universal relacionado si la ejecucion confirma el flujo.')
        return ' '.join(parts)

    # ------------------------------------------------------------------
    # P2: Playbook multi-IA con sub-intents
    # ------------------------------------------------------------------

    _SUB_INTENT_TO_IA: dict[str, str] = {
        'project.evolution': 'codex',
        'code.review': 'codex',
        'code.generation': 'codex',
        'knowledge.query': 'chatgpt',
        'general.assistance': 'chatgpt',
        'system.self_awareness': 'ollama',
        'research.investigation': 'chatgpt',
        'tool.execution': 'ollama',
    }

    def _multi_ia_parallel_steps(
        self,
        *,
        intent: TaskIntent,
        context: TaskContext,
        preferred_route: str,
        recommended_tool_id: str,
    ) -> list[PlaybookStep]:
        """Generate parallel playbook steps when compound intent is detected.

        When ``IntentUnderstandingService`` detects multiple sub-intents
        (``sub_intents`` in the schema analysis), decompose the execute
        phase into parallel steps where different IAs handle different
        aspects based on their strengths.

        Only emits steps when there are 2+ sub-intents and the experiment
        insights suggest different IAs for different aspects.  Falls back
        to an empty list (no change to playbook) when decomposition is
        not warranted.
        """
        sub_intents = list(context.metadata.get('sub_intents') or [])
        if len(sub_intents) < 2:
            return []

        composite = None
        for insight in (context.experiment_insights or []):
            comp = (insight.get('metadata') or {}).get('composite_recommendation') if isinstance(insight, dict) else None
            if isinstance(comp, dict) and comp.get('primary') and comp.get('secondary'):
                composite = comp
                break

        steps: list[PlaybookStep] = []
        assigned_ias: list[str] = []

        for idx, sub_intent in enumerate(sub_intents[:3]):
            sub_key = str(sub_intent).strip().lower()
            if composite is not None and idx == 0:
                ia = str(composite['primary'].get('assistant_kind') or 'primary')
            elif composite is not None and idx == 1:
                ia = str(composite['secondary'].get('assistant_kind') or 'secondary')
            else:
                ia = self._SUB_INTENT_TO_IA.get(sub_key, '')
            if not ia:
                ia = 'auto'
            assigned_ias.append(ia)
            steps.append(
                PlaybookStep(
                    phase_key=f'parallel_ia_{idx}',
                    title=f'Sub-tarea {idx + 1}: {sub_key} → {ia}',
                    description=f'Aspecto "{sub_key}" asignado a {ia} para ejecucion paralela.',
                    status=RunStatus.PARTIAL,
                    detail=f'IA asignada: {ia} | Sub-intent: {sub_key} | Ruta preferida: {preferred_route}',
                    metadata={
                        'sub_intent': sub_key,
                        'assigned_ia': ia,
                        'parallel_group': 'multi_ia_decomposition',
                        'preferred_route': preferred_route,
                        'recommended_tool_id': recommended_tool_id,
                    },
                )
            )

        if steps:
            consolidation_detail = (
                f'Consolidar resultados de {len(steps)} sub-tareas paralelas '
                f'({", ".join(assigned_ias)}). Verificar coherencia y combinar.'
            )
            steps.append(
                PlaybookStep(
                    phase_key='consolidate_multi_ia',
                    title='Consolidar resultados multi-IA',
                    description=consolidation_detail,
                    status=RunStatus.PARTIAL,
                    detail=consolidation_detail,
                    metadata={
                        'parallel_group': 'multi_ia_decomposition',
                        'ia_count': len(assigned_ias),
                        'assigned_ias': assigned_ias,
                    },
                )
            )
        return steps
