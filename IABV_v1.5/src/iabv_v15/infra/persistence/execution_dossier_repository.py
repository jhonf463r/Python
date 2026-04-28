from __future__ import annotations

import json
import logging
from pathlib import Path

from iabv_v15.domain.models import ExecutionDossier
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage

logger = logging.getLogger(__name__)


class ExecutionDossierRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, dossier: ExecutionDossier) -> ExecutionDossier:
        relative_path = f"dossiers/{dossier.dossier_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, dossier.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO execution_dossiers
            (dossier_id, scope_type, run_id, episode_id, status, severity, issue_hint_text, summary, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dossier.dossier_id,
                dossier.scope.value,
                dossier.run_id,
                dossier.episode_id,
                dossier.status.value,
                dossier.severity.value,
                dossier.issue_hint_text,
                dossier.summary,
                saved_path,
                dossier.created_at_utc.isoformat(),
            ),
        )
        return dossier.model_copy(update={'metadata': {**dossier.metadata, 'storage_path': saved_path}})

    def list_recent(self, limit: int = 30) -> list[ExecutionDossier]:
        rows = self.db.fetchall(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [d for row in rows if (d := self._load_from_path(row['dossier_id'], row['path'])) is not None]

    def find_by_run(self, run_id: str) -> list[ExecutionDossier]:
        rows = self.db.fetchall(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            """,
            (run_id,),
        )
        return [d for row in rows if (d := self._load_from_path(row['dossier_id'], row['path'])) is not None]

    def find_by_episode(self, episode_id: str) -> list[ExecutionDossier]:
        rows = self.db.fetchall(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE episode_id = ?
            ORDER BY created_at_utc DESC
            """,
            (episode_id,),
        )
        return [d for row in rows if (d := self._load_from_path(row['dossier_id'], row['path'])) is not None]

    def find_by_issue(self, issue_hint: str, limit: int = 20) -> list[ExecutionDossier]:
        probe = (issue_hint or '').strip().lower()
        if not probe:
            return []
        rows = self.db.fetchall(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE lower(issue_hint_text) LIKE ? OR lower(summary) LIKE ?
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (f'%{probe}%', f'%{probe}%', limit),
        )
        return [d for row in rows if (d := self._load_from_path(row['dossier_id'], row['path'])) is not None]

    def get(self, dossier_id: str) -> ExecutionDossier | None:
        row = self.db.fetchone(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE dossier_id = ?
            """,
            (dossier_id,),
        )
        if row is None:
            return None
        return self._load_from_path(row['dossier_id'], row['path'])

    def _load_from_path(self, dossier_id: str, path: str) -> ExecutionDossier | None:
        try:
            candidate = Path(path)
            if candidate.is_absolute() and candidate.exists():
                payload = json.loads(candidate.read_text(encoding='utf-8'))
            else:
                relative = f'dossiers/{dossier_id}.json'
                payload = self.storage.load_json(relative)
            return ExecutionDossier.model_validate(payload)
        except (FileNotFoundError, OSError):
            return None
