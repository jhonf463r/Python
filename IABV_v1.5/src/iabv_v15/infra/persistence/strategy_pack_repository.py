from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import StrategyPack
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class StrategyPackRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, pack: StrategyPack) -> StrategyPack:
        relative_path = f"strategy_packs/{pack.pack_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, pack.model_dump(mode='json'))
        updated_at = str(pack.metadata.get('updated_at_utc') or '')
        if not updated_at:
            updated_at = str(pack.metadata.get('created_at_utc') or '')
        if not updated_at:
            from datetime import datetime, timezone
            updated_at = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """
            INSERT OR REPLACE INTO strategy_packs
            (pack_id, title, domain_kind, risk_level, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                pack.pack_id,
                pack.title,
                pack.domain_kind,
                pack.risk_level.value,
                saved_path,
                updated_at,
            ),
        )
        return pack

    def list_all(self) -> list[StrategyPack]:
        rows = self.db.fetchall(
            """
            SELECT pack_id, path
            FROM strategy_packs
            ORDER BY domain_kind ASC, title ASC
            """
        )
        return [self._load(row['pack_id'], row['path']) for row in rows]

    def get(self, pack_id: str) -> StrategyPack | None:
        row = self.db.fetchone(
            """
            SELECT pack_id, path
            FROM strategy_packs
            WHERE pack_id = ?
            """,
            (pack_id,),
        )
        if row is None:
            return None
        return self._load(row['pack_id'], row['path'])

    def _load(self, pack_id: str, path: str) -> StrategyPack:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f'strategy_packs/{pack_id}.json')
        return StrategyPack.model_validate(payload)
