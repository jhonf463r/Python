from __future__ import annotations

from datetime import datetime, timezone
import json

from iabv_v15.domain.models import KnowledgeItem
from iabv_v15.infra.persistence.database import AppDatabase


class KnowledgeRepository:
    def __init__(self, db: AppDatabase):
        self.db = db

    def upsert(self, item: KnowledgeItem) -> KnowledgeItem:
        item.updated_at_utc = datetime.now(timezone.utc)
        self.db.execute(
            """
            INSERT OR REPLACE INTO knowledge_items
            (knowledge_id, title, summary, tags_text, confidence, payload_json, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.knowledge_id,
                item.title,
                item.summary,
                ",".join(item.tags),
                item.confidence,
                item.model_dump_json(),
                item.updated_at_utc.isoformat(),
            ),
        )
        return item

    def search(self, term: str = "", limit: int = 50) -> list[KnowledgeItem]:
        query = f"%{term.lower()}%"
        rows = self.db.fetchall(
            """
            SELECT payload_json
            FROM knowledge_items
            WHERE lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(tags_text) LIKE ?
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (query, query, query, limit),
        )
        return [KnowledgeItem.model_validate_json(row["payload_json"]) for row in rows]

    def list_recent(self, limit: int = 20) -> list[KnowledgeItem]:
        rows = self.db.fetchall(
            "SELECT payload_json FROM knowledge_items ORDER BY updated_at_utc DESC LIMIT ?",
            (limit,),
        )
        return [KnowledgeItem.model_validate_json(row["payload_json"]) for row in rows]
