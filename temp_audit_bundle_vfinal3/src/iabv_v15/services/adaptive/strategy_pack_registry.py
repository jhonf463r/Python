from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from iabv_v15.domain.models import CapabilityReadiness, CapabilityStatus, EvaluationRoute, IssueSeverity, StrategyAlgorithm, StrategyCandidate, StrategyPack, StrategyParameter, TaskContext, TaskIntent
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository


class StrategyPackRegistry:
    def __init__(self, repository: StrategyPackRepository):
        self.repository = repository
        self._packs = {pack.pack_id: pack for pack in self._build_default_packs()}
        self._parameter_overrides: dict[tuple[str, str], object] = {}
        self._seed_defaults()

    def resolve_pack(self, intent: TaskIntent, context: TaskContext) -> StrategyPack:
        direct_map = {
            'wplay.core': 'wplay.core',
            'wplay.login': 'wplay.login',
            'wplay.casino': 'wplay.casino',
            'browser.navigate': 'browser.generic',
            'browser.search': 'browser.generic',
            'knowledge.query': 'knowledge.query',
            'customer.support': 'customer.support',
            'analytics.strategy': 'analytics.strategy',
            'project.evolution': 'project.evolution',
            'research.local': 'browser.generic' if context.site_id else 'project.evolution',
            'general.assistance': 'knowledge.query',
            'tools.local_workflow': 'tools.local_first',
            'tools.sandbox': 'tools.sandbox',
        }
        pack_id = direct_map.get(intent.intent_key, 'browser.generic')
        pack = self._packs.get(pack_id)
        if pack is None:
            pack = self._packs['browser.generic']
        resolved = pack.model_copy(deep=True)
        self._apply_runtime_overrides(resolved)
        return resolved

    def set_parameter_default(self, pack_id: str, parameter_key: str, value: object) -> None:
        self._parameter_overrides[(pack_id, parameter_key)] = value

    def get_parameter_default(self, pack_id: str, parameter_key: str) -> object | None:
        override = self._parameter_overrides.get((pack_id, parameter_key))
        if override is not None:
            return override
        pack = self._packs.get(pack_id)
        if pack is None:
            return None
        parameter = next((item for item in pack.parameter_schema if item.key == parameter_key), None)
        return parameter.default_value if parameter is not None else None

    def runtime_overrides_snapshot(self) -> dict[str, dict[str, object]]:
        snapshot: dict[str, dict[str, object]] = {}
        for (pack_id, parameter_key), value in self._parameter_overrides.items():
            snapshot.setdefault(pack_id, {})[parameter_key] = value
        return snapshot

    def _apply_runtime_overrides(self, pack: StrategyPack) -> None:
        for parameter in pack.parameter_schema:
            override = self._parameter_overrides.get((pack.pack_id, parameter.key))
            if override is not None:
                parameter.default_value = override
                if parameter.value is None:
                    parameter.value = override

    def build_candidates(
        self,
        *,
        pack: StrategyPack,
        intent: TaskIntent,
        context: TaskContext,
        capabilities: list[CapabilityReadiness],
    ) -> list[StrategyCandidate]:
        capability_map = {item.capability_id: item for item in capabilities}
        worst_status = self._worst_status(capabilities)
        missing_requirements: list[str] = []
        for item in capabilities:
            if item.status == CapabilityStatus.INSUFFICIENT:
                missing_requirements.extend(item.missing_signals or [item.suggested_next_step])
            elif item.status == CapabilityStatus.PARTIAL:
                missing_requirements.append(item.suggested_next_step)
        missing_requirements = [item for item in missing_requirements if item]
        experiment_recommendation = self._best_experiment_recommendation(pack=pack, intent=intent, context=context)
        live_audit = dict(context.live_audit or context.metadata.get('live_audit') or {})
        candidates: list[StrategyCandidate] = []
        for algorithm in pack.available_algorithms:
            parameters = [parameter.model_copy(deep=True) for parameter in pack.parameter_schema if parameter.key in algorithm.parameter_keys or not algorithm.parameter_keys]
            for parameter in parameters:
                if parameter.value is None:
                    parameter.value = parameter.default_value
            recommendation_defaults = self._apply_experiment_defaults(parameters=parameters, pack=pack, recommendation=experiment_recommendation)
            alignment_score = self._experiment_alignment_score(pack=pack, algorithm=algorithm, recommendation=experiment_recommendation)
            rationale = self._candidate_rationale(
                pack=pack,
                algorithm=algorithm,
                intent=intent,
                capabilities=capability_map,
                experiment_recommendation=experiment_recommendation,
                alignment_score=alignment_score,
                live_audit=live_audit,
            )
            metadata = {
                'domain_kind': pack.domain_kind,
                'site_id': context.site_id or intent.site_hint or '',
                'experiment_alignment_score': round(alignment_score, 4),
            }
            if experiment_recommendation:
                metadata['experiment_recommendation'] = dict(experiment_recommendation)
            if live_audit:
                metadata['live_audit'] = dict(live_audit)
            metadata.update(recommendation_defaults)
            candidates.append(
                StrategyCandidate(
                    pack_id=pack.pack_id,
                    title=algorithm.title,
                    rationale=rationale,
                    algorithm_id=algorithm.algorithm_id,
                    parameters=parameters,
                    readiness_status=worst_status,
                    risk_level=pack.risk_level,
                    requires_approval=pack.approval_policy != 'never' or intent.sensitive or intent.monetary,
                    missing_requirements=list(dict.fromkeys(missing_requirements))[:6],
                    metadata=metadata,
                )
            )
        if candidates:
            candidates.sort(key=lambda item: float(item.metadata.get('experiment_alignment_score', 0.0) or 0.0), reverse=True)
            return candidates
        fallback_metadata = {
            'domain_kind': pack.domain_kind,
            'site_id': context.site_id or intent.site_hint or '',
            'experiment_alignment_score': 0.0,
        }
        if experiment_recommendation:
            fallback_metadata['experiment_recommendation'] = dict(experiment_recommendation)
        return [
            StrategyCandidate(
                pack_id=pack.pack_id,
                title=pack.title,
                rationale='No habia algoritmos declarados; se usa el pack base.',
                algorithm_id='default',
                parameters=[parameter.model_copy(deep=True) for parameter in pack.parameter_schema],
                readiness_status=worst_status,
                risk_level=pack.risk_level,
                requires_approval=pack.approval_policy != 'never',
                missing_requirements=list(dict.fromkeys(missing_requirements))[:6],
                metadata=fallback_metadata,
            )
        ]

    def _candidate_rationale(
        self,
        *,
        pack: StrategyPack,
        algorithm: StrategyAlgorithm,
        intent: TaskIntent,
        capabilities: dict[str, CapabilityReadiness],
        experiment_recommendation: dict[str, object] | None = None,
        alignment_score: float = 0.0,
        live_audit: dict[str, object] | None = None,
    ) -> str:
        capability_bits = []
        for capability_id in pack.required_capabilities:
            item = capabilities.get(capability_id)
            if item is not None:
                capability_bits.append(f"{item.title}: {item.status.value}")
        capability_text = ' | '.join(capability_bits) if capability_bits else 'sin capacidades declaradas'
        summary = f"{algorithm.summary} Capacidades observadas: {capability_text}."
        if experiment_recommendation:
            route = str(experiment_recommendation.get('recommended_route') or '')
            domain = str(experiment_recommendation.get('domain') or 'general')
            confidence = float(experiment_recommendation.get('confidence') or 0.0)
            if alignment_score >= 0.6:
                summary += f" Laboratorio universal sugiere {route} para {domain} y esta estrategia queda bien alineada (confianza {confidence:.2f})."
            else:
                summary += f" Laboratorio universal sugiere {route} para {domain}, pero esta estrategia solo aprovecha parcialmente esa via."
        if live_audit:
            summary += f" Auditoria viva recomienda {live_audit.get('decision_action') or 'continue_local'}"
            if live_audit.get('recommended_tool_id'):
                summary += f" con {live_audit.get('recommended_tool_id')}"
            summary += '.'
        return summary

    def _best_experiment_recommendation(self, *, pack: StrategyPack, intent: TaskIntent, context: TaskContext) -> dict[str, object] | None:
        if not context.experiment_insights:
            return None
        site_id = context.site_id or intent.site_hint or ''
        preferred_domains = self._preferred_experiment_domains(pack, intent)

        def score(item: dict[str, object]) -> tuple[float, float, float, float]:
            subject_key = str(item.get('subject_key') or '')
            domain = str(item.get('domain') or '')
            confidence = float(item.get('confidence') or 0.0)
            lab_score = float(item.get('score') or 0.0)
            site_match = 1.0 if site_id and subject_key == site_id else 0.0
            domain_match = 1.0 if domain in preferred_domains else 0.0
            return (site_match, domain_match, confidence, lab_score)

        return dict(max(context.experiment_insights, key=score))

    def _preferred_experiment_domains(self, pack: StrategyPack, intent: TaskIntent) -> set[str]:
        if pack.pack_id in {'tools.local_first', 'tools.sandbox'}:
            return {'code', 'algorithm', 'language', 'ocr', 'object_detection'}
        if pack.pack_id == 'knowledge.query':
            return {'language'}
        if pack.pack_id == 'project.evolution':
            return {'code', 'algorithm', 'language'}
        if pack.pack_id == 'analytics.strategy':
            return {'language', 'algorithm'}
        if pack.domain_kind in {'browser', 'wplay'} or intent.intent_key.startswith('browser.') or intent.intent_key.startswith('wplay.'):
            return {'ocr', 'object_detection', 'language'}
        return {'language'}

    def _apply_experiment_defaults(
        self,
        *,
        parameters: list[StrategyParameter],
        pack: StrategyPack,
        recommendation: dict[str, object] | None,
    ) -> dict[str, object]:
        if not recommendation:
            return {}
        route = str(recommendation.get('recommended_route') or '')
        metadata: dict[str, object] = {'recommended_route': route}
        if pack.pack_id not in {'tools.local_first', 'tools.sandbox'}:
            return metadata
        recommended_tool_id = self._tool_id_for_route(route)
        if recommended_tool_id:
            for parameter in parameters:
                if parameter.key == 'tool_id':
                    parameter.default_value = recommended_tool_id
                    if not parameter.value:
                        parameter.value = recommended_tool_id
            metadata['recommended_tool_id'] = recommended_tool_id
        recommended_scope = self._execution_scope_for_route(route)
        if recommended_scope and pack.pack_id == 'tools.local_first':
            for parameter in parameters:
                if parameter.key == 'execution_scope':
                    parameter.default_value = recommended_scope
                    if not parameter.value:
                        parameter.value = recommended_scope
            metadata['recommended_execution_scope'] = recommended_scope
        return metadata

    def _experiment_alignment_score(
        self,
        *,
        pack: StrategyPack,
        algorithm: StrategyAlgorithm,
        recommendation: dict[str, object] | None,
    ) -> float:
        if not recommendation:
            return 0.0
        route = str(recommendation.get('recommended_route') or '')
        if pack.pack_id in {'tools.local_first', 'tools.sandbox'}:
            return 0.92 if self._tool_id_for_route(route) else 0.18
        if pack.pack_id == 'browser.generic':
            if route in {EvaluationRoute.UI.value, EvaluationRoute.OCR_VISION.value}:
                return 0.82 if algorithm.algorithm_id == 'guided_navigation' else 0.24
            if route in {EvaluationRoute.LANGUAGE_UNDERSTANDING.value, EvaluationRoute.API.value, EvaluationRoute.BACKGROUND.value, EvaluationRoute.LOCAL.value}:
                return 0.8 if algorithm.algorithm_id == 'search_then_open' else 0.3
            return 0.15
        if pack.pack_id.startswith('wplay'):
            if route in {EvaluationRoute.UI.value, EvaluationRoute.OCR_VISION.value}:
                return 0.72 if 'guided' in algorithm.algorithm_id or 'session' in algorithm.algorithm_id else 0.46
            if route == EvaluationRoute.LANGUAGE_UNDERSTANDING.value:
                return 0.35
            return 0.2
        if pack.pack_id == 'knowledge.query':
            return 0.86 if route == EvaluationRoute.LANGUAGE_UNDERSTANDING.value else 0.24
        if pack.pack_id == 'project.evolution':
            return 0.86 if route == EvaluationRoute.CODE_AGENT.value else 0.34
        if pack.pack_id == 'analytics.strategy':
            return 0.68 if route in {EvaluationRoute.LOCAL.value, EvaluationRoute.LANGUAGE_UNDERSTANDING.value, EvaluationRoute.CODE_AGENT.value} else 0.28
        return 0.0

    def _tool_id_for_route(self, route: str) -> str:
        mapping = {
            EvaluationRoute.UI.value: 'playwright_browser',
            EvaluationRoute.OCR_VISION.value: 'playwright_browser',
            EvaluationRoute.BACKGROUND.value: 'shell_command',
            EvaluationRoute.LOCAL.value: 'shell_command',
            EvaluationRoute.API.value: 'mcp_client',
            EvaluationRoute.CODE_AGENT.value: 'aider_coder',
            EvaluationRoute.LANGUAGE_UNDERSTANDING.value: 'ollama_llm',
            EvaluationRoute.MATH_EVALUATION.value: 'ollama_llm',
        }
        return mapping.get(route, '')

    def _execution_scope_for_route(self, route: str) -> str:
        if route == EvaluationRoute.CODE_AGENT.value:
            return 'write'
        return 'read_only'

    def _worst_status(self, capabilities: list[CapabilityReadiness]) -> CapabilityStatus:
        if not capabilities:
            return CapabilityStatus.INSUFFICIENT
        order = {
            CapabilityStatus.INSUFFICIENT: 0,
            CapabilityStatus.PARTIAL: 1,
            CapabilityStatus.READY_WITH_APPROVAL: 2,
            CapabilityStatus.READY: 3,
        }
        return min(capabilities, key=lambda item: order[item.status]).status

    def _seed_defaults(self) -> None:
        for pack in self._packs.values():
            existing = self.repository.get(pack.pack_id)
            if existing is not None and self._same_pack(existing, pack):
                pack.metadata = dict(existing.metadata)
                self._packs[pack.pack_id] = pack
                continue
            now = datetime.now(timezone.utc).isoformat()
            if existing is not None:
                pack.metadata.setdefault(
                    'created_at_utc',
                    str(existing.metadata.get('created_at_utc') or existing.metadata.get('updated_at_utc') or now),
                )
            pack.metadata.setdefault('updated_at_utc', now)
            self.repository.save(pack)

    def _same_pack(self, left: StrategyPack, right: StrategyPack) -> bool:
        return self._pack_signature(left) == self._pack_signature(right)

    def _pack_signature(self, pack: StrategyPack) -> dict:
        payload = deepcopy(pack.model_dump(mode='json'))
        metadata = dict(payload.get('metadata') or {})
        metadata.pop('created_at_utc', None)
        metadata.pop('updated_at_utc', None)
        payload['metadata'] = metadata
        for parameter in payload.get('parameter_schema') or []:
            if isinstance(parameter, dict):
                parameter.pop('parameter_id', None)
        return payload

    def _build_default_packs(self) -> list[StrategyPack]:
        return [
            StrategyPack(
                pack_id='browser.generic',
                title='Navegacion web generica',
                domain_kind='browser',
                supported_intents=['browser.navigate', 'browser.search'],
                required_capabilities=['browser.generic.navigation'],
                required_context=['recent_teachings', 'recent_runs'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='guided_navigation',
                        title='Navegacion guiada',
                        summary='Propone una secuencia corta de apertura, navegacion y verificacion antes de actuar.',
                        parameter_keys=['target_site', 'target_goal'],
                        success_signals=['page_opened', 'visible_progress'],
                        fallback_signals=['need_more_teaching', 'navigation_stall'],
                    ),
                    StrategyAlgorithm(
                        algorithm_id='search_then_open',
                        title='Busqueda y apertura',
                        summary='Primero busca o ubica el sitio y luego propone la siguiente fase de interaccion.',
                        parameter_keys=['target_site', 'target_goal'],
                        success_signals=['search_result_detected'],
                        fallback_signals=['need_exact_url'],
                    ),
                ],
                parameter_schema=[
                    StrategyParameter(key='target_site', label='Sitio objetivo', description='Sitio o dominio sobre el que se trabajara.', default_value='', kind='text', editable=True),
                    StrategyParameter(key='target_goal', label='Objetivo', description='Tarea puntual de la navegacion.', default_value='', kind='text', editable=True),
                ],
                risk_level=IssueSeverity.LOW,
                approval_policy='never',
                execution_templates=['abrir sitio', 'verificar carga', 'seguir siguiente fase'],
                success_signals=['navegacion visible', 'sin incidentes dominantes'],
                fallback_signals=['captura insuficiente', 'sitio ambiguo'],
            ),
            StrategyPack(
                pack_id='wplay.core',
                title='Core Wplay',
                domain_kind='wplay',
                supported_intents=['wplay.login', 'wplay.casino'],
                required_capabilities=['wplay.login'],
                required_context=['recent_teachings', 'recent_incidents', 'session_readiness'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='site_session_guard',
                        title='Sesion Wplay con guardrails',
                        summary='Valida readiness, revisa incidentes y prepara una sesion segura por fases.',
                        parameter_keys=['login_mode'],
                    )
                ],
                parameter_schema=[
                    StrategyParameter(key='login_mode', label='Modo de sesion', description='Preferencia de restauracion o login guiado.', default_value='restore_then_guided', kind='choice', editable=True, options=['restore_then_guided', 'guided_only']),
                ],
                risk_level=IssueSeverity.HIGH,
                approval_policy='phased',
                execution_templates=['verificar sesion', 'abrir sitio', 'esperar aprobacion'],
                success_signals=['login_ready', 'session_restored'],
                fallback_signals=['session_restore_weak', 'need_reteach'],
            ),
            StrategyPack(
                pack_id='wplay.login',
                title='Login Wplay',
                domain_kind='wplay',
                supported_intents=['wplay.login'],
                required_capabilities=['wplay.login', 'wplay.session.restore'],
                required_context=['recent_teachings', 'recent_incidents', 'adaptive_sessions'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='restore_or_guided_login',
                        title='Restaurar sesion y login guiado',
                        summary='Primero intenta aprovechar la sesion conocida y, si no alcanza, prepara login guiado con aprobacion.',
                        parameter_keys=['login_mode', 'wait_seconds'],
                        success_signals=['login_ready', 'session_restored'],
                        fallback_signals=['session_restore_weak', 'login_partial'],
                    )
                ],
                parameter_schema=[
                    StrategyParameter(key='login_mode', label='Modo de login', description='Intento preferido antes de la fase guiada.', default_value='restore_then_guided', kind='choice', editable=True, options=['restore_then_guided', 'guided_only']),
                    StrategyParameter(key='wait_seconds', label='Espera maxima', description='Tiempo maximo de espera para verificar estado.', default_value=18, kind='number', editable=True),
                ],
                risk_level=IssueSeverity.HIGH,
                approval_policy='phased',
                execution_templates=['restaurar sesion', 'abrir Wplay', 'verificar autenticacion', 'pedir aprobacion si toca login guiado'],
                success_signals=['sesion autenticada', 'ruta de login lista'],
                fallback_signals=['session_restore_weak', 'need_reteach'],
            ),
            StrategyPack(
                pack_id='wplay.casino',
                title='Casino Wplay por fases',
                domain_kind='wplay',
                supported_intents=['wplay.casino'],
                required_capabilities=['wplay.login', 'wplay.navigate.casino', 'wplay.session.restore'],
                required_context=['recent_teachings', 'recent_incidents', 'adaptive_sessions'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='conservative_session_guard',
                        title='Conservadora con guardrails',
                        summary='Entra a la sesion, valida limites y propone una estrategia conservadora editable antes de cualquier accion critica.',
                        parameter_keys=['bankroll_units', 'stop_gain_pct', 'stop_loss_pct', 'table_hint'],
                    ),
                    StrategyAlgorithm(
                        algorithm_id='fibonacci_controlada',
                        title='Fibonacci controlada',
                        summary='Plantea una variante progresiva limitada, con topes claros y aprobacion humana obligatoria.',
                        parameter_keys=['bankroll_units', 'stop_gain_pct', 'stop_loss_pct', 'table_hint'],
                    ),
                ],
                parameter_schema=[
                    StrategyParameter(key='bankroll_units', label='Bankroll base', description='Unidad base para la estrategia.', default_value=100, kind='number', editable=True),
                    StrategyParameter(key='stop_gain_pct', label='Stop gain %', description='Corte de ganancia.', default_value=10, kind='number', editable=True),
                    StrategyParameter(key='stop_loss_pct', label='Stop loss %', description='Corte de perdida.', default_value=5, kind='number', editable=True),
                    StrategyParameter(key='table_hint', label='Mesa objetivo', description='Preferencia de mesa o juego.', default_value='ruleta', kind='text', editable=True),
                ],
                risk_level=IssueSeverity.CRITICAL,
                approval_policy='phased',
                execution_templates=['login', 'navegar a casino', 'configurar estrategia', 'pedir aprobacion critica', 'ejecutar fase'],
                success_signals=['casino_ready', 'strategy_approved'],
                fallback_signals=['missing_capability', 'approval_pending'],
            ),
            StrategyPack(
                pack_id='tools.local_first',
                title='Tool Teaching local-first',
                domain_kind='tools',
                supported_intents=['tools.local_workflow'],
                required_capabilities=['tools.local.registry', 'tools.local.execution'],
                required_context=['recent_runs'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='sandbox_then_execute',
                        title='Sandbox y ejecucion local',
                        summary='Selecciona una herramienta local, valida primero en sandbox y luego ejecuta con trazabilidad.',
                        parameter_keys=['tool_id', 'execution_scope'],
                        success_signals=['sandbox_pass', 'tool_executed'],
                        fallback_signals=['adapter_missing', 'sandbox_fail'],
                    )
                ],
                parameter_schema=[
                    StrategyParameter(key='tool_id', label='Herramienta', description='ToolCard preferida para esta tarea.', default_value='', kind='text', editable=True),
                    StrategyParameter(key='execution_scope', label='Scope', description='Scope operativo de la tarea.', default_value='read_only', kind='choice', editable=True, options=['read_only', 'write', 'destructive']),
                ],
                risk_level=IssueSeverity.MEDIUM,
                approval_policy='phased',
                execution_templates=['seleccionar herramienta', 'correr sandbox', 'pedir aprobacion si hace falta', 'ejecutar y registrar'],
                success_signals=['tool_ready', 'tool_executed'],
                fallback_signals=['sandbox_fail', 'need_codex_packet'],
            ),
            StrategyPack(
                pack_id='tools.sandbox',
                title='Sandbox de herramientas',
                domain_kind='tools',
                supported_intents=['tools.sandbox'],
                required_capabilities=['tools.local.registry', 'tools.local.sandbox'],
                required_context=['recent_runs'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='sandbox_probe',
                        title='Probe de sandbox',
                        summary='Prueba la herramienta local en aislamiento antes de cualquier ejecucion fuera del sandbox.',
                        parameter_keys=['tool_id'],
                        success_signals=['sandbox_pass'],
                        fallback_signals=['sandbox_fail', 'adapter_missing'],
                    )
                ],
                parameter_schema=[
                    StrategyParameter(key='tool_id', label='Herramienta', description='ToolCard a validar en sandbox.', default_value='', kind='text', editable=True),
                ],
                risk_level=IssueSeverity.LOW,
                approval_policy='never',
                execution_templates=['seleccionar herramienta', 'correr sandbox', 'registrar validacion'],
                success_signals=['sandbox_pass'],
                fallback_signals=['sandbox_fail'],
            ),
            StrategyPack(
                pack_id='knowledge.query',
                title='Consulta local con contexto',
                domain_kind='knowledge',
                supported_intents=['knowledge.query', 'general.assistance'],
                required_capabilities=['knowledge.query.local'],
                required_context=['knowledge_hits', 'recent_runs'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='context_first_answer',
                        title='Respuesta local contextual',
                        summary='Usa memoria local, ejecuciones recientes y evidencia para responder sin preguntas genericas.',
                    )
                ],
                parameter_schema=[],
                risk_level=IssueSeverity.LOW,
                approval_policy='never',
                execution_templates=['responder', 'proponer siguiente paso'],
                success_signals=['respuesta util'],
                fallback_signals=['need_context'],
            ),
            StrategyPack(
                pack_id='customer.support',
                title='Soporte al cliente local',
                domain_kind='customer',
                supported_intents=['customer.support'],
                required_capabilities=['customer.support.local'],
                required_context=['knowledge_hits', 'recent_runs'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='templated_support',
                        title='Respuesta con plantilla local',
                        summary='Cruza conocimiento y trazas recientes para responder de forma operativa.',
                    )
                ],
                parameter_schema=[],
                risk_level=IssueSeverity.LOW,
                approval_policy='never',
                execution_templates=['buscar conocimiento', 'responder'],
                success_signals=['respuesta con contexto'],
                fallback_signals=['need_more_knowledge'],
            ),
            StrategyPack(
                pack_id='analytics.strategy',
                title='Analitica y estrategia',
                domain_kind='analytics',
                supported_intents=['analytics.strategy'],
                required_capabilities=['analytics.report.local'],
                required_context=['recent_runs', 'knowledge_hits'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='metrics_first_strategy',
                        title='Metricas primero',
                        summary='Prioriza datos reales y despues propone la estrategia o experimento.',
                    )
                ],
                parameter_schema=[],
                risk_level=IssueSeverity.LOW,
                approval_policy='never',
                execution_templates=['leer metricas', 'proponer acciones'],
                success_signals=['metricas reales'],
                fallback_signals=['lack_of_data'],
            ),
            StrategyPack(
                pack_id='project.evolution',
                title='Evolucion del proyecto',
                domain_kind='project',
                supported_intents=['project.evolution'],
                required_capabilities=['project.review.local'],
                required_context=['recent_dossiers', 'recent_incidents', 'recent_runs'],
                available_algorithms=[
                    StrategyAlgorithm(
                        algorithm_id='vertical_change_recommendation',
                        title='Cambio vertical recomendado',
                        summary='Resume evidencia, causa probable, cambio vertical y pruebas sugeridas para avanzar con Codex.',
                    )
                ],
                parameter_schema=[],
                risk_level=IssueSeverity.MEDIUM,
                approval_policy='never',
                execution_templates=['leer evidencia', 'proponer mejora'],
                success_signals=['mejora priorizada'],
                fallback_signals=['need_more_evidence'],
            ),
        ]
