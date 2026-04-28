from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from iabv_v15.domain.models import RuntimeAdjustment, RuntimeTuningProfile
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage

_log = logging.getLogger(__name__)


class RuntimeTuningRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, profile: RuntimeTuningProfile) -> RuntimeTuningProfile:
        relative_path = f"runtime_tuning/{profile.scope_key}.json"
        saved_path = self.storage.save_json_atomic(relative_path, profile.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO runtime_tuning_profiles
            (profile_id, scope_key, path, updated_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (
                profile.profile_id,
                profile.scope_key,
                saved_path,
                profile.updated_at_utc.isoformat(),
            ),
        )
        return profile

    def get(self, scope_key: str = 'global') -> RuntimeTuningProfile | None:
        row = self.db.fetchone(
            """
            SELECT scope_key, path
            FROM runtime_tuning_profiles
            WHERE scope_key = ?
            ORDER BY updated_at_utc DESC
            LIMIT 1
            """,
            (scope_key,),
        )
        if row is None:
            return None
        return self._load(row['scope_key'], row['path'])

    def list_recent(self, limit: int = 10) -> list[RuntimeTuningProfile]:
        rows = self.db.fetchall(
            """
            SELECT scope_key, path
            FROM runtime_tuning_profiles
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return self._collect(rows)

    def append_adjustment(self, adjustment: RuntimeAdjustment, scope_key: str = 'global') -> RuntimeTuningProfile:
        profile = self.get(scope_key) or RuntimeTuningProfile(scope_key=scope_key)
        profile.adjustments.append(adjustment)
        profile.updated_at_utc = datetime.now(timezone.utc)
        return self.save(profile)

    def _collect(self, rows: list[dict[str, str]]) -> list[RuntimeTuningProfile]:
        results: list[RuntimeTuningProfile] = []
        orphan_ids: list[str] = []
        for row in rows:
            item = self._load(row['scope_key'], row['path'])
            if item is not None:
                results.append(item)
            else:
                orphan_ids.append(row['scope_key'])
        if orphan_ids:
            self._prune_orphans(orphan_ids)
        return results

    def _prune_orphans(self, ids: list[str]) -> None:
        if not ids:
            return
        placeholders = ','.join('?' for _ in ids)
        try:
            self.db.execute(
                f"DELETE FROM runtime_tuning_profiles WHERE scope_key IN ({placeholders})",
                tuple(ids),
            )
            _log.info("tuning_cleanup: pruned %d orphaned DB entries", len(ids))
        except Exception:
            pass

    def _load(self, scope_key: str, path: str) -> RuntimeTuningProfile | None:
        candidate = Path(path)
        try:
            if candidate.is_absolute() and candidate.exists():
                payload = json.loads(candidate.read_text(encoding='utf-8'))
            else:
                payload = self.storage.load_json(f'runtime_tuning/{scope_key}.json')
            return RuntimeTuningProfile.model_validate(payload)
        except (FileNotFoundError, json.JSONDecodeError, OSError, Exception) as exc:
            _log.warning("tuning %s: file missing or corrupt — %s", scope_key, exc)
            return None
