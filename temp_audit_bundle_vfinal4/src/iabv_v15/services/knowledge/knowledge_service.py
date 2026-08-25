from __future__ import annotations

from iabv_v15.domain.models import KnowledgeItem, RunRecord
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.services.knowledge.unified_memory_layer import UnifiedMemoryLayer


class KnowledgeService:
    def __init__(self, repository: KnowledgeRepository, unified_memory_layer: UnifiedMemoryLayer | None = None):
        self.repository = repository
        self.unified_memory_layer = unified_memory_layer

    def remember_run(self, run_record: RunRecord) -> KnowledgeItem:
        if self.unified_memory_layer is not None:
            return self.unified_memory_layer.remember_run(run_record)
        item = KnowledgeItem(
            title=run_record.result.inferred_task,
            summary=run_record.result.summary,
            source_episode_id=run_record.request.metadata.get("episode_id"),
            task_label=run_record.result.inferred_task,
            confidence=run_record.result.confidence,
            tags=[
                run_record.route.primary_kind.value,
                run_record.result.reasoning_mode.value,
            ],
            payload={
                "route": run_record.route.model_dump(),
                "result": run_record.result.model_dump(),
            },
        )
        return self.repository.upsert(item)

    def search(self, term: str = "") -> list[KnowledgeItem]:
        return self.repository.search(term)
