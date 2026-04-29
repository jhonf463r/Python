from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import SessionArtifact
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class SessionArtifactRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, artifact: SessionArtifact, payload: Any | None = None) -> SessionArtifact:
        final_artifact = artifact
        if payload is not None:
            artifact_path = Path(artifact.path)
            if artifact_path.is_absolute():
                raise ValueError("Artifact payload paths must be relative to ArtifactStorage.")
            if isinstance(payload, (bytes, bytearray)):
                saved_path = self.storage.save_bytes(artifact.path, bytes(payload))
            else:
                saved_path = self.storage.save_json_atomic(artifact.path, payload)
            final_artifact = artifact.model_copy(update={"path": saved_path})

        metadata_json = json.dumps(final_artifact.metadata, ensure_ascii=False)
        self.db.execute(
            """
            INSERT OR REPLACE INTO session_artifacts
            (artifact_id, episode_id, kind, path, metadata_json, created_at_utc, redacted)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                final_artifact.artifact_id,
                final_artifact.episode_id,
                final_artifact.kind,
                final_artifact.path,
                metadata_json,
                final_artifact.created_at_utc.isoformat(),
                1 if bool(final_artifact.metadata.get("redacted")) else 0,
            ),
        )
        return final_artifact

    def list_for_episode(self, episode_id: str) -> list[SessionArtifact]:
        rows = self.db.fetchall(
            """
            SELECT artifact_id, episode_id, kind, path, metadata_json, created_at_utc
            FROM session_artifacts
            WHERE episode_id = ?
            ORDER BY created_at_utc ASC
            """,
            (episode_id,),
        )
        return [self._row_to_model(row) for row in rows]

    def count(self) -> int:
        row = self.db.fetchone("SELECT COUNT(*) AS cnt FROM session_artifacts")
        return int(row["cnt"]) if row else 0

    def list_recent(self, limit: int = 50) -> list[SessionArtifact]:
        rows = self.db.fetchall(
            """
            SELECT artifact_id, episode_id, kind, path, metadata_json, created_at_utc
            FROM session_artifacts
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row) -> SessionArtifact:
        payload = {
            "artifact_id": row["artifact_id"],
            "episode_id": row["episode_id"],
            "kind": row["kind"],
            "path": row["path"],
            "metadata": json.loads(row["metadata_json"]),
            "created_at_utc": row["created_at_utc"],
        }
        return SessionArtifact.model_validate(payload)
