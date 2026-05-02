from __future__ import annotations

import json
import logging
from pathlib import Path

from iabv_v15.domain.models import CapabilityReadiness
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage

_log = logging.getLogger(__name__)


class CapabilityRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save_many(self, capabilities: list[CapabilityReadiness]) -> list[CapabilityReadiness]:
        for capability in capabilities:
            self.save(capability)
        return capabilities

    def save(self, capability: CapabilityReadiness) -> CapabilityReadiness:
        capability_key = self._key(capability.capability_id, capability.site_id)
        relative_path = f"capabilities/{capability_key}.json"
        saved_path = self.storage.save_json_atomic(relative_path, capability.model_dump(mode='json'))
        summary = capability.suggested_next_step or ', '.join(capability.evidence[:2]) or capability.title
        from datetime import datetime, timezone
        self.db.execute(
            """
            INSERT OR REPLACE INTO capability_snapshots
            (capability_key, capability_id, site_id, status, score, summary, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capability_key,
                capability.capability_id,
                capability.site_id,
                capability.status.value,
                capability.score,
                summary,
                saved_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return capability

    def list_recent(self, limit: int = 30) -> list[CapabilityReadiness]:
        rows = self.db.fetchall(
            """
            SELECT capability_key, path
            FROM capability_snapshots
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return self._collect(rows)

    def find_by_site(self, site_id: str, limit: int = 30) -> list[CapabilityReadiness]:
        rows = self.db.fetchall(
            """
            SELECT capability_key, path
            FROM capability_snapshots
            WHERE site_id = ? OR (? = '' AND site_id IS NULL)
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (site_id or '', site_id or '', limit),
        )
        return self._collect(rows)

    def get(self, capability_id: str, site_id: str | None = None) -> CapabilityReadiness | None:
        capability_key = self._key(capability_id, site_id)
        row = self.db.fetchone(
            """
            SELECT capability_key, path
            FROM capability_snapshots
            WHERE capability_key = ?
            """,
            (capability_key,),
        )
        if row is None:
            return None
        return self._load(row['capability_key'], row['path'])

    def _key(self, capability_id: str, site_id: str | None) -> str:
        scope = (site_id or 'global').replace('/', '_').replace('\\', '_')
        return f'{scope}__{capability_id}'.replace(':', '_')

    def _collect(self, rows: list[dict[str, str]]) -> list[CapabilityReadiness]:
        results: list[CapabilityReadiness] = []
        orphan_ids: list[str] = []
        for row in rows:
            item = self._load(row['capability_key'], row['path'])
            if item is not None:
                results.append(item)
            else:
                orphan_ids.append(row['capability_key'])
        if orphan_ids:
            self._prune_orphans(orphan_ids)
        return results

    def _prune_orphans(self, ids: list[str]) -> None:
        if not ids:
            return
        placeholders = ','.join('?' for _ in ids)
        try:
            self.db.execute(
                f"DELETE FROM capability_snapshots WHERE capability_key IN ({placeholders})",
                tuple(ids),
            )
            _log.info("capability_cleanup: pruned %d orphaned DB entries", len(ids))
        except Exception:
            pass

    def _load(self, capability_key: str, path: str) -> CapabilityReadiness | None:
        candidate = Path(path)
        try:
            if candidate.is_absolute() and candidate.exists():
                payload = json.loads(candidate.read_text(encoding='utf-8'))
            else:
                payload = self.storage.load_json(f'capabilities/{capability_key}.json')
            return CapabilityReadiness.model_validate(payload)
        except (FileNotFoundError, json.JSONDecodeError, OSError, Exception) as exc:
            _log.debug("capability %s: file missing or corrupt — %s", capability_key, exc)
            return None
