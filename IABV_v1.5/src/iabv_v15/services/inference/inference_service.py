from __future__ import annotations

import time

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    ApprovalCheckpoint,
    AssistantConfigurationSnapshot,
    CapabilityReadiness,
    ClarificationItem,
    DecisionContext,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRun,
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
    SessionContinuationType,
    SynapticRoutingDecision,
    TaskContext,
    TaskIntent,
    TaskOutcome,
    TaskRole,
    VisualSignalSnapshot,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.evolution.execution_dossier_service import ExecutionDossierService
from iabv_v15.services.knowledge.knowledge_service import KnowledgeService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


class InferenceService:
    def __init__(
        self,
        router: LocalRoleRouter,
        run_repository: RunRepository,
        execution_dossier_service: ExecutionDossierService | None = None,
        adaptive_orchestrator: AdaptiveTaskOrchestrator | None = None,
        knowledge_service: KnowledgeService | None = None,
    ):
        self.router = router
        self.run_repository = run_repository
        self.execution_dossier_service = execution_dossier_service
        self.adaptive_orchestrator = adaptive_orchestrator
        self.knowledge_service = knowledge_service

    def infer_task(self, request: InferenceRequest) -> RunRecord:
        return self._execute('infer_task', request)

    def analyze_ui(self, request: InferenceRequest) -> RunRecord:
        return self._execute('analyze_ui', request)

    def summarize_session(self, request: InferenceRequest) -> RunRecord:
        return self._execute('summarize_session', request)

    def _execute(self, method_name: str, request: InferenceRequest) -> RunRecord:
        started = time.perf_counter()
        adaptive_session = None
        try:
            if method_name == 'infer_task' and self.adaptive_orchestrator is not None:
                route, result, adaptive_session = self.adaptive_orchestrator.handle_request(request)
            else:
                router_method = getattr(self.router, method_name)
                route, result = router_method(request)
            status = RunStatus.PARTIAL if result.used_fallback else RunStatus.SUCCESS
            run_record = RunRecord(
                request=request,
                result=result,
                route=route,
                status=status,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_summary=result.error_summary or '',
            )
            saved = self.run_repository.record(run_record)
            if adaptive_session is not None and self.adaptive_orchestrator is not None:
                finalized_session = self.adaptive_orchestrator.finalize_with_run(adaptive_session.session_id, saved)
                if finalized_session is not None and isinstance(saved.result.raw_output, dict):
                    saved.result.raw_output['adaptive_session'] = finalized_session.model_dump(mode='json')
                    # Canonical source: use typed continuation_type instead of legacy metadata
                    saved.result.raw_output['adaptive_replanned'] = bool(finalized_session.continuation_type == SessionContinuationType.AUTO_REPLAN)
            if self.knowledge_service is not None:
                self.knowledge_service.remember_run(saved)
            if self.execution_dossier_service is not None:
                self.execution_dossier_service.build_for_run(saved)
            return saved
        except Exception as exc:
            failed_route = RoleRoute(
                task_role=request.role_hint or request.task_role,
                role_title=(request.role_hint or request.task_role).value,
                provider_name='Adaptive local orchestrator' if self.adaptive_orchestrator is not None and method_name == 'infer_task' else 'Ollama',
                model_profile_id='general-qwen',
                model_name='qwen3:8b',
                reason=f'Fallo durante {method_name} antes de completar el routing.',
            )
            failed_result = InferenceResult(
                request_id=request.request_id,
                provider_name='Adaptive local orchestrator' if self.adaptive_orchestrator is not None and method_name == 'infer_task' else 'Ollama',
                reasoning_mode=ReasoningMode.DEGRADED,
                summary='',
                inferred_task=request.user_goal,
                confidence=0.0,
                detected_role=request.role_hint or request.task_role,
                executor_model='qwen3:8b',
                error_summary=str(exc),
                diagnostic_flags=['exception_during_inference'],
            )
            failed_record = RunRecord(
                request=request,
                result=failed_result,
                route=failed_route,
                status=RunStatus.FAILED,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_summary=str(exc),
            )
            saved = self.run_repository.record(failed_record)
            if self.knowledge_service is not None:
                self.knowledge_service.remember_run(saved)
            if self.execution_dossier_service is not None:
                self.execution_dossier_service.build_for_run(saved)
            raise
