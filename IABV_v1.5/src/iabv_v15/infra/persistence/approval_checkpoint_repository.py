from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import ApprovalCheckpoint
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ApprovalCheckpointRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save_many(self, checkpoints: list[ApprovalCheckpoint]) -> list[ApprovalCheckpoint]:
        for checkpoint in checkpoints:
            self.save(checkpoint)
        return checkpoints

    def save(self, checkpoint: ApprovalCheckpoint) -> ApprovalCheckpoint:
        relative_path = f"approvals/{checkpoint.checkpoint_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, checkpoint.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO approval_checkpoints
            (checkpoint_id, session_id, playbook_id, decision, phase_key, risk_level, title, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                checkpoint.checkpoint_id,
                checkpoint.session_id,
                checkpoint.playbook_id,
                checkpoint.decision.value,
                checkpoint.phase_key,
                checkpoint.risk_level.value,
                checkpoint.title,
                saved_path,
                checkpoint.created_at_utc.isoformat(),
            ),
        )
        return checkpoint

    def list_for_session(self, session_id: str) -> list[ApprovalCheckpoint]:
        rows = self.db.fetchall(
            """
            SELECT checkpoint_id, path
            FROM approval_checkpoints
            WHERE session_id = ?
            ORDER BY created_at_utc ASC
            """,
            (session_id,),
        )
        return [self._load(row['checkpoint_id'], row['path']) for row in rows]

    def get(self, checkpoint_id: str) -> ApprovalCheckpoint | None:
        row = self.db.fetchone(
            """
            SELECT checkpoint_id, path
            FROM approval_checkpoints
            WHERE checkpoint_id = ?
            """,
            (checkpoint_id,),
        )
        if row is None:
            return None
        return self._load(row['checkpoint_id'], row['path'])

    def _load(self, checkpoint_id: str, path: str) -> ApprovalCheckpoint:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f'approvals/{checkpoint_id}.json')
        return ApprovalCheckpoint.model_validate(payload)
