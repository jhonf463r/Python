from __future__ import annotations

from types import SimpleNamespace

import pytest

from iabv_v15.domain.models import InferenceRequest, InferenceResult, ReasoningMode, RoleRoute, RunRecord, RunStatus, TaskRole
from iabv_v15.services.inference.inference_service import InferenceService


class _FakeRunRepository:
    def __init__(self) -> None:
        self.items: list[RunRecord] = []

    def record(self, run_record: RunRecord) -> RunRecord:
        self.items.append(run_record)
        return run_record


class _FakeKnowledgeService:
    def __init__(self) -> None:
        self.items: list[RunRecord] = []

    def remember_run(self, run_record: RunRecord):
        self.items.append(run_record)
        return run_record


class _FakeDossierService:
    def __init__(self) -> None:
        self.items: list[RunRecord] = []

    def build_for_run(self, run_record: RunRecord) -> None:
        self.items.append(run_record)


class _FakeAdaptiveSession:
    def __init__(self, session_id: str, *, replanned: bool = False) -> None:
        self.session_id = session_id
        self.metadata = {'replanned_automatically': replanned}
        # Typed provenance fields for compatibility with AdaptiveSession
        self.continuation_type = 'auto_replan' if replanned else 'external_request'
        self.parent_session_id = 'adaptive-session-1' if replanned else None
        self.replan_depth = 1 if replanned else 0
        self.auto_replan_child_session_id = None

    def model_dump(self, mode: str = 'json') -> dict[str, object]:
        return {
            'session_id': self.session_id,
            'metadata': dict(self.metadata),
            'continuation_type': self.continuation_type,
            'parent_session_id': self.parent_session_id,
            'replan_depth': self.replan_depth,
            'auto_replan_child_session_id': self.auto_replan_child_session_id,
        }


class _FakeAdaptiveOrchestrator:
    def __init__(self) -> None:
        self.finalized_with_run_id = ''

    def handle_request(self, request: InferenceRequest):
        route = RoleRoute(
            task_role=TaskRole.TRAINING,
            role_title='Training',
            provider_name='Adaptive local orchestrator',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='Ruta adaptativa de prueba',
        )
        result = InferenceResult(
            request_id=request.request_id,
            provider_name='Adaptive local orchestrator',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Ruta adaptativa completada.',
            inferred_task=request.user_goal,
            confidence=0.82,
            detected_role=TaskRole.TRAINING,
            executor_model='qwen3:8b',
            raw_output={},
        )
        return route, result, SimpleNamespace(session_id='adaptive-session-1')

    def finalize_with_run(self, session_id: str, run_record: RunRecord):
        self.finalized_with_run_id = run_record.run_id
        return _FakeAdaptiveSession('adaptive-session-2', replanned=True)


class _FailingRouter:
    def infer_task(self, request: InferenceRequest):
        raise RuntimeError('fallo controlado')


def test_inference_service_remembers_run_and_surfaces_replanned_session() -> None:
    run_repository = _FakeRunRepository()
    knowledge_service = _FakeKnowledgeService()
    dossier_service = _FakeDossierService()
    adaptive_orchestrator = _FakeAdaptiveOrchestrator()
    service = InferenceService(
        router=_FailingRouter(),
        run_repository=run_repository,
        execution_dossier_service=dossier_service,
        adaptive_orchestrator=adaptive_orchestrator,
        knowledge_service=knowledge_service,
    )

    saved = service.infer_task(InferenceRequest(user_goal='abre Wplay e inicia sesion', task_role=TaskRole.TRAINING))

    assert run_repository.items
    assert knowledge_service.items[0].run_id == saved.run_id
    assert dossier_service.items[0].run_id == saved.run_id
    assert adaptive_orchestrator.finalized_with_run_id == saved.run_id
    assert saved.result.raw_output['adaptive_session']['session_id'] == 'adaptive-session-2'
    assert saved.result.raw_output['adaptive_replanned'] is True


def test_inference_service_remembers_failed_runs_before_reraising() -> None:
    run_repository = _FakeRunRepository()
    knowledge_service = _FakeKnowledgeService()
    dossier_service = _FakeDossierService()
    service = InferenceService(
        router=_FailingRouter(),
        run_repository=run_repository,
        execution_dossier_service=dossier_service,
        knowledge_service=knowledge_service,
    )

    with pytest.raises(RuntimeError, match='fallo controlado'):
        service.infer_task(InferenceRequest(user_goal='rompe la ruta', task_role=TaskRole.TRAINING))

    assert run_repository.items
    assert run_repository.items[0].status == RunStatus.FAILED
    assert knowledge_service.items[0].run_id == run_repository.items[0].run_id
    assert dossier_service.items[0].run_id == run_repository.items[0].run_id
