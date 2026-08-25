from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import CapturedStep, InferenceRequest, InferenceResult, ReasoningMode, RoleRoute, RunRecord, RunStatus, SessionArtifact, TaskRole, ToolCapability
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_analytics_strategy_service_uses_real_metrics() -> None:
    root = _workspace('analytics')
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))

    manifest = episodes.create_episode('Sesion 1')
    episodes.save_step(manifest.episode_id, CapturedStep(episode_id=manifest.episode_id, action_type='click', target='#start'))
    artifacts.save(SessionArtifact(episode_id=manifest.episode_id, kind='dom_snapshot', path=f'{manifest.episode_id}/dom.json', metadata={'capture_channel': 'background'}), payload={'ok': True})
    request = InferenceRequest(user_goal='Analiza progreso', task_role=TaskRole.ANALYTICS)
    result = InferenceResult(request_id=request.request_id, provider_name='Ollama', reasoning_mode=ReasoningMode.LOCAL, summary='ok', inferred_task='Analiza progreso', confidence=0.75)
    route = RoleRoute(task_role=TaskRole.ANALYTICS, role_title='Marketing y estadisticas', provider_name='Ollama', model_profile_id='general-qwen', model_name='qwen3:8b', tool_chain=[ToolCapability.ANALYTICS], reason='metricas reales')
    runs.record(RunRecord(request=request, result=result, route=route, status=RunStatus.PARTIAL))

    service = AnalyticsStrategyService(episodes, knowledge, runs, artifacts)
    report = service.build_report()

    assert report['metrics']['episodes'] == 1
    assert report['metrics']['artifacts'] == 1
    assert report['metrics']['partial_runs'] == 1
    assert 'tabla:run_records' in report['sources']


def test_teaching_gap_analyzer_prioritizes_reteaching_failed_tasks() -> None:
    analyzer = TeachingGapAnalyzer()
    request = InferenceRequest(user_goal='Responder mensajes', task_role=TaskRole.CUSTOMER_SUPPORT)
    result = InferenceResult(request_id=request.request_id, provider_name='Ollama', reasoning_mode=ReasoningMode.LOCAL, summary='ok', inferred_task='Responder mensajes', confidence=0.55)
    route = RoleRoute(task_role=TaskRole.CUSTOMER_SUPPORT, role_title='Atencion al cliente', provider_name='Ollama', model_profile_id='general-qwen', model_name='qwen3:8b', tool_chain=[ToolCapability.KNOWLEDGE_SEARCH], reason='soporte local')
    runs = [
        RunRecord(request=request, result=result, route=route, status=RunStatus.PARTIAL),
        RunRecord(request=request, result=result, route=route, status=RunStatus.FAILED),
    ]
    artifacts = [SessionArtifact(episode_id='e1', kind='dom_snapshot', path='e1/dom.json', metadata={'capture_channel': 'background'})]

    report = analyzer.analyze(episodes=[], artifacts=artifacts, runs=runs, knowledge_count=0)

    assert report['follow_up_teachings']
    assert any('Responder mensajes' in item or 'flujo base' in item.lower() for item in report['follow_up_teachings'])
