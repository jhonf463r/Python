from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    AmbiguityLevel,
    ComplexityLevel,
    InferenceRequest,
    InferenceResult,
    KnowledgeItem,
    ProviderKind,
    ReasoningMode,
    RouteDecision,
    RunRecord,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.snapshot_version_manager import SnapshotVersionManager
from iabv_v15.services.training.payload_archive_service import PayloadArchiveService
from iabv_v15.services.training.training_orchestrator import TrainingOrchestrator


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_training_payload_prepare_and_archive() -> None:
    root = _workspace('training')
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)

    manifest = episodes.create_episode('Payload Episode')
    request = InferenceRequest(
        user_goal='Review payload generation',
        screenshots=['one.png', 'two.png'],
        complexity=ComplexityLevel.DEEP,
        ambiguity=AmbiguityLevel.MEDIUM,
    )
    result = InferenceResult(
        request_id=request.request_id,
        provider_name='LM Studio',
        reasoning_mode=ReasoningMode.LOCAL,
        summary='Payload summary',
        inferred_task='Review payload generation',
        confidence=0.81,
    )
    route = RouteDecision(
        primary_provider='LM Studio',
        primary_kind=ProviderKind.LOCAL,
        fallback_provider='Ollama',
        reason='simple',
    )
    runs.record(RunRecord(request=request, result=result, route=route))
    knowledge.upsert(KnowledgeItem(title='Payload knowledge', summary='Useful memory', source_episode_id=manifest.episode_id))

    manager = SnapshotVersionManager(str(root / 'payloads'))
    archive = PayloadArchiveService(str(root / 'payloads'), manager)
    orchestrator = TrainingOrchestrator(str(root), episodes, knowledge, runs, archive)

    payload, saved_path = orchestrator.prepare_and_archive()
    assert payload.version == 2
    assert len(payload.episodes) == 1
    assert Path(saved_path).exists()

    snapshot = manager.load_snapshot('training_payload_v2.json')
    compatibility, _details = manager.check_compatibility(snapshot, {'version': 2, 'fields': ['episodes']})
    assert compatibility in {'adaptable', 'compatible'}
