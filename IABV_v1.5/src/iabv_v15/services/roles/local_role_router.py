from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Any, Callable

from iabv_v15.domain.models import (
    AmbiguityLevel,
    ComplexityLevel,
    DecisionContext,
    InferenceRequest,
    InferenceResult,
    IntentRouteDecision,
    ModelProfile,
    ProviderHealth,
    ReasoningMode,
    ReportKind,
    RoleProfile,
    RoleRoute,
    TaskIntent,
    TaskRole,
    ToolCapability,
)
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer


class LocalRoleRouter:
    def __init__(
        self,
        *,
        workspace_root: str,
        general_provider: LLMProvider,
        visual_provider: LLMProvider,
        optional_provider: LLMProvider | None,
        embedding_service: EmbeddingIndexService,
        sql_service: SqlQueryAdvisorService,
        analytics_service: AnalyticsStrategyService,
        customer_support_service: CustomerSupportService,
        engineering_review_service: EngineeringReviewService,
        teaching_gap_analyzer: TeachingGapAnalyzer,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        artifact_repository: SessionArtifactRepository,
        tool_teach_service: Any | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.general_provider = general_provider
        self.visual_provider = visual_provider
        self.optional_provider = optional_provider
        self.embedding_service = embedding_service
        self.sql_service = sql_service
        self.analytics_service = analytics_service
        self.customer_support_service = customer_support_service
        self.engineering_review_service = engineering_review_service
        self.teaching_gap_analyzer = teaching_gap_analyzer
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.artifact_repository = artifact_repository
        self.tool_teach_service = tool_teach_service
        self._health_snapshot_lock = threading.RLock()
        self._health_snapshot_cache: list[ProviderHealth] = []
        self._health_snapshot_checked_at = 0.0
        self._model_profiles = self._build_model_profiles()
        self._role_profiles = self._build_role_profiles()

    @property
    def role_profiles(self) -> list[RoleProfile]:
        return self._role_profiles

    @property
    def model_profiles(self) -> list[ModelProfile]:
        return self._model_profiles

    def health_snapshot(self, *, refresh: bool = False, max_age_seconds: float = 30.0) -> list[ProviderHealth]:
        ttl = max(float(max_age_seconds), 0.0)
        if not refresh and ttl > 0.0:
            with self._health_snapshot_lock:
                if self._health_snapshot_cache and (time.monotonic() - self._health_snapshot_checked_at) <= ttl:
                    return [item.model_copy(deep=True) for item in self._health_snapshot_cache]
        snapshot = [
            self.general_provider.health_check(),
            self.visual_provider.health_check(),
        ]
        if self.optional_provider is not None:
            snapshot.append(self.optional_provider.health_check())
        snapshot.append(self.embedding_service.health_check())
        with self._health_snapshot_lock:
            self._health_snapshot_cache = [item.model_copy(deep=True) for item in snapshot]
            self._health_snapshot_checked_at = time.monotonic()
        return snapshot

    def infer_task(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        decision_context = self._decision_context_from_request(request)
        decision = decision_context.route_decision if decision_context is not None else self._decide_route(request)
        dispatch_request = request.model_copy(
            update={
                'task_role': decision.detected_role,
                'allowed_tools': self._merge_tools(request.allowed_tools, decision.tool_chain),
                'requires_visual_reasoning': request.requires_visual_reasoning or decision.visual_required,
            }
        )
        planner_summary = ''
        planner_used = False
        if dispatch_request.enable_planning and decision.planner_required and decision.detected_role != TaskRole.VISUAL:
            planner_summary = self._run_planner(dispatch_request, decision)
            planner_used = bool(planner_summary)
            if planner_summary:
                dispatch_request = dispatch_request.model_copy(
                    update={'prompt': self._append_context(dispatch_request.prompt, f'Plan previo:\n{planner_summary}')}
                )

        route, result = self._dispatch_by_role(dispatch_request)
        route.task_role = decision.detected_role
        route.role_title = self._role_title(decision.detected_role)
        route.reason = f"{decision.reason} {route.reason}".strip()
        result.detected_role = decision.detected_role
        result.planner_used = planner_used
        result.executor_model = route.model_name or result.executor_model
        result.raw_output['intent_route_decision'] = decision.model_dump(mode='json')
        if planner_summary:
            result.raw_output['planner_summary'] = planner_summary
        return route, result

    def build_decision_from_intent(self, *, request: InferenceRequest, intent: TaskIntent) -> IntentRouteDecision:
        if request.role_hint is not None and not request.auto_route:
            detected_role = request.role_hint
            reason = f'Rol manual conservado en DecisionContext: {self._role_title(detected_role)}.'
        else:
            detected_role = intent.detected_role
            reason = f'Rol resuelto desde intent {intent.intent_key}: {self._role_title(detected_role)}.'
        return IntentRouteDecision(
            detected_role=detected_role,
            planner_required=self._planner_required(request, detected_role),
            visual_required=request.requires_visual_reasoning or detected_role == TaskRole.VISUAL,
            tool_chain=list(self._role_tools(detected_role)),
            reason=reason,
        )

    def route_from_decision(self, decision: IntentRouteDecision, *, provider_name: str = 'Adaptive local orchestrator') -> RoleRoute:
        role_profile = next((item for item in self.role_profiles if item.role == decision.detected_role), self.role_profiles[0])
        model_profile = next((item for item in self.model_profiles if item.profile_id == role_profile.preferred_model_profile_id), self.model_profiles[0])
        return RoleRoute(
            task_role=decision.detected_role,
            role_title=role_profile.title,
            provider_name=provider_name,
            model_profile_id=model_profile.profile_id,
            model_name=model_profile.model_name,
            tool_chain=list(dict.fromkeys(list(role_profile.default_tools) + list(decision.tool_chain))),
            reason=str(decision.reason or ''),
        )

    def _decision_context_from_request(self, request: InferenceRequest) -> DecisionContext | None:
        payload = request.metadata.get('decision_context') if isinstance(request.metadata, dict) else None
        if not isinstance(payload, dict):
            return None
        try:
            return DecisionContext.model_validate(payload)
        except Exception:
            return None

    def analyze_ui(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        visual_request = request.model_copy(update={'task_role': TaskRole.VISUAL, 'requires_visual_reasoning': True})
        route, result = self._route_visual(visual_request)
        result.detected_role = TaskRole.VISUAL
        result.executor_model = route.model_name
        return route, result

    def summarize_session(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        training_request = request.model_copy(update={'task_role': TaskRole.TRAINING})
        route, result = self._route_training(training_request)
        result.detected_role = TaskRole.TRAINING
        result.executor_model = route.model_name
        return route, result

    def _dispatch_by_role(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        dispatch: dict[TaskRole, Callable[[InferenceRequest], tuple[RoleRoute, InferenceResult]]] = {
            TaskRole.TRAINING: self._route_training,
            TaskRole.KNOWLEDGE: self._route_knowledge,
            TaskRole.ANALYTICS: self._route_analytics,
            TaskRole.CUSTOMER_SUPPORT: self._route_customer_support,
            TaskRole.PROJECT_EVOLUTION: self._route_project_evolution,
            TaskRole.RESEARCH: self._route_research,
            TaskRole.VISUAL: self._route_visual,
            TaskRole.TOOL_USE: self._route_tooling,
            TaskRole.TOOL_SANDBOX: self._route_tooling,
        }
        handler = dispatch.get(request.task_role, self._route_training)
        return handler(request)

    def _decide_route(self, request: InferenceRequest) -> IntentRouteDecision:
        has_visual_evidence = bool(request.screenshots or request.steps or request.requires_visual_reasoning)
        if request.role_hint is not None and not request.auto_route:
            return IntentRouteDecision(
                detected_role=request.role_hint,
                planner_required=self._planner_required(request, request.role_hint),
                visual_required=request.role_hint == TaskRole.VISUAL,
                tool_chain=list(self._role_tools(request.role_hint)),
                reason=f'Rol forzado manualmente: {self._role_title(request.role_hint)}.',
            )
        if not request.auto_route:
            return IntentRouteDecision(
                detected_role=request.task_role,
                planner_required=self._planner_required(request, request.task_role),
                visual_required=request.task_role == TaskRole.VISUAL,
                tool_chain=list(self._role_tools(request.task_role)),
                reason=f'Rol manual conservado: {self._role_title(request.task_role)}.',
            )

        detected_role = self._detect_role(request.user_goal, has_visual_evidence)
        return IntentRouteDecision(
            detected_role=detected_role,
            planner_required=self._planner_required(request, detected_role),
            visual_required=has_visual_evidence and detected_role == TaskRole.VISUAL,
            tool_chain=list(self._role_tools(detected_role)),
            reason=f'Rol detectado automaticamente: {self._role_title(detected_role)}.',
        )

    def _detect_role(self, user_goal: str, has_visual_evidence: bool) -> TaskRole:
        text = user_goal.lower()
        if has_visual_evidence and self._contains_any(text, ['captura', 'pantalla', 'interfaz', 'ui', 'imagen', 'visual', 'dom']):
            return TaskRole.VISUAL
        if self._contains_any(text, ['tool', 'herramienta', 'playwright', 'ollama', 'aider', 'mcp', 'powershell', 'sandbox']):
            return TaskRole.TOOL_SANDBOX if self._contains_any(text, ['sandbox', 'probar tool', 'probar herramienta']) else TaskRole.TOOL_USE
        if self._contains_any(text, ['cliente', 'whatsapp', 'soporte', 'atencion', 'respuesta al cliente', 'pedido', 'producto', 'formas de pago', 'horario', 'venta']):
            return TaskRole.CUSTOMER_SUPPORT
        if self._contains_any(text, ['marketing', 'estadistica', 'estadisticas', 'metricas', 'conversion', 'embudo', 'campana', 'campaÃ±a', 'roi', 'analitica']):
            return TaskRole.ANALYTICS
        if self._contains_any(text, ['proyecto', 'codigo', 'cÃ³digo', 'bug', 'error', 'fallo', 'refactor', 'arquitectura', 'mejora', 'centro de control', 'ui pc']):
            return TaskRole.PROJECT_EVOLUTION
        if self._contains_any(text, ['investiga', 'investigar', 'benchmark', 'comparar', 'compara', 'analiza a fondo', 'estrategia', 'tendencia', 'research']):
            return TaskRole.RESEARCH
        if self._contains_any(text, ['base de conocimiento', 'documentacion', 'documentaciÃ³n', 'memoria', 'consulta', 'buscar', 'que sabes', 'quÃ© sabes', 'conocimiento']):
            return TaskRole.KNOWLEDGE
        if self._contains_any(text, ['ensenar', 'enseÃ±ar', 'entrenamiento', 'aprender', 'capturar', 'automatizar', 'siguiente ensenanza', 'siguiente enseÃ±anza']):
            return TaskRole.TRAINING
        return TaskRole.TRAINING

    def _planner_required(self, request: InferenceRequest, role: TaskRole) -> bool:
        if not request.enable_planning or role == TaskRole.VISUAL:
            return False
        text = request.user_goal.lower()
        words = [token for token in text.replace('\n', ' ').split(' ') if token]
        if request.deep_reasoning or request.complexity == ComplexityLevel.DEEP or request.ambiguity == AmbiguityLevel.HIGH:
            return True
        if len(words) >= 24:
            return True
        return self._contains_any(
            text,
            ['plan', 'pasos', 'estrategia', 'compara', 'comparar', 'primero', 'luego', 'despues', 'despuÃ©s', 'analiza a fondo'],
        )

    def _run_planner(self, request: InferenceRequest, decision: IntentRouteDecision) -> str:
        planner_prompt = (
            'Actua como planificador local de IABV. Resume la intencion, detecta restricciones y propone un plan corto de ejecucion.\n'
            f'Rol previsto: {self._role_title(decision.detected_role)}\n'
            f'Objetivo: {request.user_goal}'
        )
        planner_request = request.model_copy(
            update={
                'prompt': planner_prompt,
                'task_role': TaskRole.RESEARCH,
                'complexity': ComplexityLevel.MEDIUM,
                'ambiguity': AmbiguityLevel.MEDIUM,
            }
        )
        try:
            planner_result = self.general_provider.infer_task(planner_request)
            return planner_result.summary.strip()
        except Exception:
            return ''

    def _route_training(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        episodes = self.episode_repository.list_recent(limit=80)
        artifacts = self.artifact_repository.list_recent(limit=200)
        runs = self.run_repository.list_recent(limit=120)
        gap_report = self.teaching_gap_analyzer.analyze(
            episodes=episodes,
            artifacts=artifacts,
            runs=runs,
            knowledge_count=self.knowledge_repository.count(),
        )
        prompt = (
            'Rol: entrenamiento y mejora de ensenanzas. '
            f"Objetivo: {request.user_goal}\n"
            f"Resumen de huecos: {gap_report['summary']}\n"
            f"Siguientes ensenanzas sugeridas: {', '.join(gap_report['follow_up_teachings'])}."
            f"{self._context_suffix(request)}"
        )
        route, result = self._run_general(
            request,
            prompt=prompt,
            reason='Entrenamiento local con observaciones, memoria y priorizacion de ensenanzas.',
            tool_chain=[ToolCapability.BROWSER_OBSERVATION, ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.PBT_TUNING],
            report_kind=ReportKind.TRAINING_GUIDANCE,
            sources=['browser:observation_bundle', 'tabla:episodes', 'tabla:run_records'],
        )
        result.follow_up_teachings = list(gap_report['follow_up_teachings'])
        result.raw_output['teaching_gaps'] = gap_report
        return route, result

    def _route_knowledge(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        hits = self.knowledge_repository.search(request.user_goal, limit=10)
        documents = [
            {'title': item.title, 'summary': item.summary, 'body': str(item.payload), 'source': f'knowledge:{item.title}'}
            for item in hits
        ]
        semantic_hits = self.embedding_service.search(request.user_goal, documents, limit=5)
        self.embedding_service.refresh_metadata(
            knowledge_count=self.knowledge_repository.count(),
            artifact_count=self.artifact_repository.count(),
            last_query=request.user_goal,
        )
        prompt = (
            'Rol: base de conocimiento y consulta local. '
            f"Objetivo: {request.user_goal}\n"
            f"Hallazgos semanticos: {semantic_hits}."
            f"{self._context_suffix(request)}"
        )
        route, result = self._run_general(
            request,
            prompt=prompt,
            reason='Consulta de conocimiento local con apoyo de embeddings y memoria confirmada.',
            tool_chain=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS],
            report_kind=ReportKind.KNOWLEDGE_BRIEF,
            sources=[str(item.get('source')) for item in semantic_hits],
        )
        result.raw_output['knowledge_hits'] = semantic_hits
        return route, result

    def _route_analytics(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        report = self.analytics_service.build_report()
        prompt = (
            'Rol: marketing y analisis estadistico local. '
            f"Objetivo: {request.user_goal}\n"
            f"Metricas reales: {report['metrics']}\n"
            f"Acciones recomendadas: {report['recommended_actions']}"
            f"{self._context_suffix(request)}"
        )
        route, result = self._run_general(
            request,
            prompt=prompt,
            reason='Analisis local sobre metricas calculadas directamente desde SQLite y artefactos del proyecto.',
            tool_chain=[ToolCapability.ANALYTICS, ToolCapability.SQL_READ_ONLY],
            report_kind=ReportKind.ANALYTICS_REPORT,
            sources=list(report['sources']),
        )
        result.raw_output['analytics'] = report
        return route, result

    def _route_customer_support(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        context = self.customer_support_service.build_context(request.user_goal)
        prompt = (
            'Rol: atencion al cliente con consulta local. '
            f"Objetivo: {request.user_goal}\n"
            f"Contexto de conocimiento: {context['knowledge_hits']}\n"
            f"Contexto SQL: {context['sql_context']}\n"
            f"Plantilla: {context['response_template']}"
            f"{self._context_suffix(request)}"
        )
        route, result = self._run_general(
            request.model_copy(update={'read_only_sql': True}),
            prompt=prompt,
            reason='Respuesta local apoyada en conocimiento interno y consultas SQL seguras de solo lectura.',
            tool_chain=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS, ToolCapability.SQL_READ_ONLY, ToolCapability.CUSTOMER_TEMPLATE],
            report_kind=ReportKind.CUSTOMER_RESPONSE,
            sources=list(dict.fromkeys(context['sources'])),
        )
        result.raw_output['customer_support'] = context
        return route, result

    def _route_project_evolution(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        packet = self.engineering_review_service.build_codex_packet(
            user_goal=request.user_goal,
            selected_role_title=self._role_title(TaskRole.PROJECT_EVOLUTION),
        )
        prompt = (
            'Rol: evolucion del proyecto. '
            f"Objetivo: {request.user_goal}\n"
            'A partir del paquete generado, resume el problema, la mejora prioritaria y el siguiente cambio vertical recomendable.\n'
            f'Paquete:\n{packet}'
            f"{self._context_suffix(request)}"
        )
        route, result = self._run_general(
            request,
            prompt=prompt,
            reason='Revision local del proyecto con paquete estructurado para Codex y diagnostico accionable.',
            tool_chain=[ToolCapability.CODEX_PACKET, ToolCapability.ANALYTICS, ToolCapability.PBT_TUNING],
            report_kind=ReportKind.ENGINEERING_REVIEW,
            sources=['repo:AGENTS.md', 'repo:docs/ARCHITECTURE.md', 'tabla:run_records'],
        )
        result.raw_output['codex_packet'] = packet
        return route, result

    def _route_research(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        docs = self._read_local_docs()
        prompt = (
            'Rol: investigacion local. '
            f"Objetivo: {request.user_goal}\n"
            f"Contexto local relevante: {docs}"
            f"{self._context_suffix(request)}"
        )
        route, result = self._run_general(
            request,
            prompt=prompt,
            reason='Investigacion local sobre documentacion, conocimiento y artefactos del propio proyecto.',
            tool_chain=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS],
            report_kind=ReportKind.RESEARCH_BRIEF,
            sources=['repo:AGENTS.md', 'repo:docs/ARCHITECTURE.md'],
        )
        result.raw_output['research_docs'] = docs
        return route, result

    def _route_visual(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        profile = self._model_profile('visual-gemma')
        fallback_name = self.optional_provider.name if self.optional_provider is not None else self.general_provider.name
        route = RoleRoute(
            task_role=TaskRole.VISUAL,
            role_title=self._role_title(TaskRole.VISUAL),
            provider_name=self.visual_provider.name,
            model_profile_id=profile.profile_id,
            model_name=profile.model_name,
            tool_chain=[ToolCapability.VISUAL_REVIEW, ToolCapability.BROWSER_OBSERVATION],
            reason='Revision visual local sobre capturas, DOM y artefactos del navegador.',
            fallback_provider_name=fallback_name,
        )
        visual_request = request.model_copy(
            update={
                'prompt': self._append_context(
                    request.prompt,
                    f'Rol visual. Objetivo: {request.user_goal}',
                ),
                'requires_visual_reasoning': True,
            }
        )
        fallback_errors: list[str] = []
        try:
            result = self.visual_provider.analyze_ui(visual_request)
        except Exception as exc:
            fallback_errors.append(f'{self.visual_provider.name}: {exc}')
            result, fallback_name, fallback_errors = self._visual_fallback(visual_request, fallback_errors)
            result.reasoning_mode = ReasoningMode.DEGRADED
            result.confidence_reduced = True
            result.used_fallback = True
            result.provider_name = fallback_name
            route.used_fallback = True
            route.fallback_provider_name = fallback_name
            route.reason = f'{route.reason} Fallback visual -> {fallback_name}.'
            self._attach_fallback_trace(
                result,
                channel='visual',
                primary_provider=self.visual_provider.name,
                fallback_provider=fallback_name,
                errors=fallback_errors,
            )
        result.used_tools = [ToolCapability.VISUAL_REVIEW, ToolCapability.BROWSER_OBSERVATION]
        result.sources = ['browser:screenshots', 'browser:dom_snapshot']
        result.report_kind = ReportKind.VISUAL_ANALYSIS
        result.executor_model = profile.model_name if not route.used_fallback else self._model_profile('visual-gemma').model_name
        return route, result

    def _visual_fallback(self, request: InferenceRequest, errors: list[str]) -> tuple[InferenceResult, str, list[str]]:
        if self.optional_provider is not None:
            try:
                return self.optional_provider.analyze_ui(request), self.optional_provider.name, errors
            except Exception as exc:
                errors.append(f'{self.optional_provider.name}: {exc}')
        try:
            return self.general_provider.analyze_ui(request), self.general_provider.name, errors
        except Exception as exc:
            errors.append(f'{self.general_provider.name}: {exc}')
            raise RuntimeError('No pude completar el fallback visual local.') from exc

    def _route_tooling(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        if self.tool_teach_service is not None:
            return self.tool_teach_service.handle(request)
        profile = self._model_profile('general-qwen')
        route = RoleRoute(
            task_role=request.task_role,
            role_title=self._role_title(request.task_role),
            provider_name='Tool local-first runtime',
            model_profile_id=profile.profile_id,
            model_name=profile.model_name,
            tool_chain=[ToolCapability.TOOL_EXECUTION, ToolCapability.TOOL_SANDBOX, ToolCapability.LOCAL_LLM],
            reason='Tool Teaching aun no esta inicializado en el bootstrap.',
        )
        result = InferenceResult(
            request_id=request.request_id,
            provider_name='Tool local-first runtime',
            reasoning_mode=ReasoningMode.DEGRADED,
            summary='La ruta de Tool Teaching existe, pero todavia no esta inicializada en esta sesion.',
            inferred_task=request.user_goal,
            confidence=0.25,
            used_tools=list(route.tool_chain),
            report_kind=ReportKind.TOOL_EXECUTION,
            detected_role=request.task_role,
            executor_model=profile.model_name,
            error_summary='tool_teach_service_unavailable',
            diagnostic_flags=['tool_teach_service_unavailable'],
        )
        return route, result
    def _run_general(
        self,
        request: InferenceRequest,
        *,
        prompt: str,
        reason: str,
        tool_chain: list[ToolCapability],
        report_kind: ReportKind,
        sources: list[str],
    ) -> tuple[RoleRoute, InferenceResult]:
        profile = self._model_profile('general-qwen')
        route = RoleRoute(
            task_role=request.task_role,
            role_title=self._role_title(request.task_role),
            provider_name=self.general_provider.name,
            model_profile_id=profile.profile_id,
            model_name=profile.model_name,
            tool_chain=tool_chain,
            reason=reason,
            fallback_provider_name=self.visual_provider.name,
        )
        enriched_request = request.model_copy(update={'prompt': prompt})
        try:
            result = self.general_provider.answer_user(enriched_request)
        except Exception as exc:
            fallback_errors = [f'{self.general_provider.name}: {exc}']
            result = self.visual_provider.answer_user(enriched_request)
            result.reasoning_mode = ReasoningMode.DEGRADED
            result.confidence_reduced = True
            result.used_fallback = True
            result.provider_name = self.visual_provider.name
            route.used_fallback = True
            route.reason = f'{route.reason} Fallback general -> {self.visual_provider.name}.'
            self._attach_fallback_trace(
                result,
                channel='general',
                primary_provider=self.general_provider.name,
                fallback_provider=self.visual_provider.name,
                errors=fallback_errors,
            )
        result.used_tools = tool_chain
        result.sources = sources
        result.report_kind = report_kind
        result.executor_model = profile.model_name if not route.used_fallback else self._model_profile('visual-gemma').model_name
        return route, result

    def _attach_fallback_trace(
        self,
        result: InferenceResult,
        *,
        channel: str,
        primary_provider: str,
        fallback_provider: str,
        errors: list[str],
    ) -> None:
        result.raw_output['fallback_trace'] = {
            'channel': channel,
            'primary_provider': primary_provider,
            'fallback_provider': fallback_provider,
            'errors': list(errors),
        }

    def _append_context(self, prompt: str, extra: str) -> str:
        prompt = (prompt or '').strip()
        extra = (extra or '').strip()
        if not prompt:
            return extra
        if not extra:
            return prompt
        return f'{prompt}\n\n{extra}'

    def _context_suffix(self, request: InferenceRequest) -> str:
        prompt = (request.prompt or '').strip()
        if not prompt:
            return ''
        return f'\nContexto adicional: {prompt}'

    def _merge_tools(self, request_tools: list[ToolCapability], route_tools: list[ToolCapability]) -> list[ToolCapability]:
        merged: list[ToolCapability] = []
        for tool in list(request_tools) + list(route_tools):
            if tool not in merged:
                merged.append(tool)
        return merged

    def _role_tools(self, role: TaskRole) -> list[ToolCapability]:
        profile = next((item for item in self._role_profiles if item.role == role), None)
        return list(profile.default_tools) if profile else []

    def _read_local_docs(self) -> dict[str, str]:
        docs: dict[str, str] = {}
        for relative in ('AGENTS.md', 'docs/ARCHITECTURE.md'):
            path = self.workspace_root / relative
            if path.exists():
                docs[relative] = path.read_text(encoding='utf-8', errors='ignore')[:3000]
        return docs

    def _role_title(self, role: TaskRole) -> str:
        return next((profile.title for profile in self._role_profiles if profile.role == role), role.value)

    def _model_profile(self, profile_id: str) -> ModelProfile:
        return next(profile for profile in self._model_profiles if profile.profile_id == profile_id)

    def _contains_any(self, text: str, patterns: list[str]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _build_model_profiles(self) -> list[ModelProfile]:
        return [
            ModelProfile(
                profile_id='general-qwen',
                label='Generalista local',
                backend='Ollama',
                model_name='qwen3:8b',
                summary='Razonamiento principal para entrenamiento, analitica, soporte y evolucion del proyecto.',
                quantization='Q4_K_M',
            ),
            ModelProfile(
                profile_id='visual-gemma',
                label='Vision local',
                backend='Ollama',
                model_name='gemma3:4b',
                summary='Analisis visual y multimodal sobre capturas, paginas y UI usando el runtime local principal.',
                supports_vision=True,
                quantization='Q4_K_M',
            ),
            ModelProfile(
                profile_id='embedding-qwen',
                label='Embeddings locales',
                backend='Ollama',
                model_name='qwen3-embedding:0.6b',
                summary='Recuperacion semantica de conocimiento, sesiones, esquemas y documentacion.',
                supports_embeddings=True,
                quantization='Q4',
            ),
        ]

    def _build_role_profiles(self) -> list[RoleProfile]:
        return [
            RoleProfile(role=TaskRole.TRAINING, title='Entrenamiento', summary='Aprender tareas, detectar huecos y sugerir que ensenar despues.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.BROWSER_OBSERVATION, ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.PBT_TUNING]),
            RoleProfile(role=TaskRole.KNOWLEDGE, title='Base de conocimiento', summary='Consultar memoria, sesiones y documentacion local.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS]),
            RoleProfile(role=TaskRole.ANALYTICS, title='Marketing y estadisticas', summary='Medir progreso y proponer estrategias con metricas reales.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.ANALYTICS, ToolCapability.SQL_READ_ONLY]),
            RoleProfile(role=TaskRole.CUSTOMER_SUPPORT, title='Atencion al cliente', summary='Responder con apoyo de conocimiento y datos locales.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS, ToolCapability.SQL_READ_ONLY]),
            RoleProfile(role=TaskRole.PROJECT_EVOLUTION, title='Evolucion del proyecto', summary='Detectar fallos, preparar paquete Codex y proponer la siguiente mejora.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.CODEX_PACKET, ToolCapability.ANALYTICS]),
            RoleProfile(role=TaskRole.RESEARCH, title='Investigacion', summary='Sintetizar lo que ya sabe el proyecto y lo que falta por explorar.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS]),
            RoleProfile(role=TaskRole.VISUAL, title='Vision y revision web', summary='Mirar pantallas, capturas y artefactos del navegador.', preferred_model_profile_id='visual-gemma', default_tools=[ToolCapability.VISUAL_REVIEW, ToolCapability.BROWSER_OBSERVATION]),
            RoleProfile(role=TaskRole.TOOL_USE, title='Tool Teaching', summary='Seleccionar y ejecutar herramientas locales primero con sandbox y trazabilidad.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.TOOL_EXECUTION, ToolCapability.TOOL_SANDBOX, ToolCapability.LOCAL_LLM]),
            RoleProfile(role=TaskRole.TOOL_SANDBOX, title='Tool Sandbox', summary='Probar herramientas locales en aislamiento antes de ejecutar fuera del sandbox.', preferred_model_profile_id='general-qwen', default_tools=[ToolCapability.TOOL_SANDBOX, ToolCapability.TOOL_EXECUTION]),
        ]




