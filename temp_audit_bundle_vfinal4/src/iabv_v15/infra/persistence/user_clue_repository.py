from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import UserClue
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class UserClueRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, clue: UserClue) -> UserClue:
        relative_path = f"clues/{clue.clue_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, clue.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO user_clues
            (clue_id, episode_id, run_id, linked_incident_id, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                clue.clue_id,
                clue.episode_id,
                clue.run_id,
                clue.linked_incident_id,
                saved_path,
                clue.created_at_utc.isoformat(),
            ),
        )
        return clue

    def list_recent(self, limit: int = 30) -> list[UserClue]:
        rows = self.db.fetchall(
            """
            SELECT clue_id, path
            FROM user_clues
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._load_from_path(row['clue_id'], row['path']) for row in rows]

    def find_by_episode(self, episode_id: str) -> list[UserClue]:
        rows = self.db.fetchall(
            """
            SELECT clue_id, path
            FROM user_clues
            WHERE episode_id = ?
            ORDER BY created_at_utc DESC
            """,
            (episode_id,),
        )
        return [self._load_from_path(row['clue_id'], row['path']) for row in rows]

    def find_by_run(self, run_id: str) -> list[UserClue]:
        rows = self.db.fetchall(
            """
            SELECT clue_id, path
            FROM user_clues
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            """,
            (run_id,),
        )
        return [self._load_from_path(row['clue_id'], row['path']) for row in rows]

    def find_by_incident(self, incident_id: str) -> list[UserClue]:
        rows = self.db.fetchall(
            """
            SELECT clue_id, path
            FROM user_clues
            WHERE linked_incident_id = ?
            ORDER BY created_at_utc DESC
            """,
            (incident_id,),
        )
        return [self._load_from_path(row['clue_id'], row['path']) for row in rows]

    def _load_from_path(self, clue_id: str, path: str) -> UserClue:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f'clues/{clue_id}.json')
        return UserClue.model_validate(payload)
