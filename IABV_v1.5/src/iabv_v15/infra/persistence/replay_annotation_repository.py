from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import ReplayAnnotation
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ReplayAnnotationRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, annotation: ReplayAnnotation) -> ReplayAnnotation:
        relative_path = f"annotations/{annotation.annotation_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, annotation.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO replay_annotations
            (annotation_id, episode_id, step_id, screenshot_path, group_key, status, source, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                annotation.annotation_id,
                annotation.episode_id,
                annotation.step_id,
                annotation.screenshot_path,
                annotation.group_key,
                annotation.status.value,
                annotation.source.value,
                saved_path,
                annotation.updated_at_utc.isoformat(),
            ),
        )
        return annotation

    def list_for_episode(self, episode_id: str) -> list[ReplayAnnotation]:
        rows = self.db.fetchall(
            """
            SELECT annotation_id, path
            FROM replay_annotations
            WHERE episode_id = ?
            ORDER BY updated_at_utc DESC
            """,
            (episode_id,),
        )
        return [self._load(row['annotation_id'], row['path']) for row in rows]

    def find_by_step(self, step_id: str) -> list[ReplayAnnotation]:
        rows = self.db.fetchall(
            """
            SELECT annotation_id, path
            FROM replay_annotations
            WHERE step_id = ?
            ORDER BY updated_at_utc DESC
            """,
            (step_id,),
        )
        return [self._load(row['annotation_id'], row['path']) for row in rows]

    def get(self, annotation_id: str) -> ReplayAnnotation | None:
        row = self.db.fetchone(
            """
            SELECT annotation_id, path
            FROM replay_annotations
            WHERE annotation_id = ?
            """,
            (annotation_id,),
        )
        if row is None:
            return None
        return self._load(row['annotation_id'], row['path'])

    def delete(self, annotation_id: str) -> None:
        item = self.get(annotation_id)
        if item is not None:
            candidate = Path(self.storage.resolve(f"annotations/{annotation_id}.json"))
            if candidate.exists():
                candidate.unlink(missing_ok=True)
        self.db.execute(
            "DELETE FROM replay_annotations WHERE annotation_id = ?",
            (annotation_id,),
        )

    def _load(self, annotation_id: str, path: str) -> ReplayAnnotation:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f"annotations/{annotation_id}.json")
        return ReplayAnnotation.model_validate(payload)
