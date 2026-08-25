from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import HiddenIncident
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class HiddenIncidentRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, incident: HiddenIncident) -> HiddenIncident:
        relative_path = f"incidents/{incident.incident_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, incident.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO hidden_incidents
            (incident_id, episode_id, run_id, site_id, incident_kind, severity, status, summary, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident.incident_id,
                incident.episode_id,
                incident.run_id,
                incident.site_id,
                incident.incident_kind,
                incident.severity.value,
                incident.status.value,
                incident.summary,
                saved_path,
                incident.created_at_utc.isoformat(),
            ),
        )
        return incident

    def list_recent(self, limit: int = 30) -> list[HiddenIncident]:
        rows = self.db.fetchall(
            """
            SELECT incident_id, path
            FROM hidden_incidents
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._load_from_path(row['incident_id'], row['path']) for row in rows]

    def find_by_episode(self, episode_id: str) -> list[HiddenIncident]:
        rows = self.db.fetchall(
            """
            SELECT incident_id, path
            FROM hidden_incidents
            WHERE episode_id = ?
            ORDER BY created_at_utc DESC
            """,
            (episode_id,),
        )
        return [self._load_from_path(row['incident_id'], row['path']) for row in rows]

    def find_by_run(self, run_id: str) -> list[HiddenIncident]:
        rows = self.db.fetchall(
            """
            SELECT incident_id, path
            FROM hidden_incidents
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            """,
            (run_id,),
        )
        return [self._load_from_path(row['incident_id'], row['path']) for row in rows]

    def find_by_kind(self, incident_kind: str, limit: int = 20) -> list[HiddenIncident]:
        probe = (incident_kind or "").strip().lower()
        if not probe:
            return []
        rows = self.db.fetchall(
            """
            SELECT incident_id, path
            FROM hidden_incidents
            WHERE lower(incident_kind) = ? OR lower(summary) LIKE ?
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (probe, f'%{probe}%', limit),
        )
        return [self._load_from_path(row['incident_id'], row['path']) for row in rows]

    def get(self, incident_id: str) -> HiddenIncident | None:
        row = self.db.fetchone(
            """
            SELECT incident_id, path
            FROM hidden_incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        )
        if row is None:
            return None
        return self._load_from_path(row['incident_id'], row['path'])

    def _load_from_path(self, incident_id: str, path: str) -> HiddenIncident:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f'incidents/{incident_id}.json')
        return HiddenIncident.model_validate(payload)
