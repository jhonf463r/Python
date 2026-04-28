from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import AdaptiveSession
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class AdaptiveSessionRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, session: AdaptiveSession) -> AdaptiveSession:
        relative_path = f"adaptive_sessions/{session.session_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, session.model_dump(mode='json'))
        summary = ''
        if session.outcome is not None and session.outcome.summary:
            summary = session.outcome.summary
        elif session.playbook is not None and session.playbook.summary:
            summary = session.playbook.summary
        else:
            summary = session.intent.summary or session.user_goal
        site_id = session.context.site_id or session.intent.site_hint
        self.db.execute(
            """
            INSERT OR REPLACE INTO adaptive_sessions
            (session_id, run_id, status, intent_key, pack_id, site_id, summary, path, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.run_id,
                session.status.value,
                session.intent.intent_key,
                session.chosen_pack_id,
                site_id,
                summary,
                saved_path,
                session.created_at_utc.isoformat(),
                session.updated_at_utc.isoformat(),
            ),
        )
        return session

    def list_recent(self, limit: int = 20) -> list[AdaptiveSession]:
        rows = self.db.fetchall(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [s for row in rows if (s := self._load(row['session_id'], row['path'])) is not None]

    def get(self, session_id: str) -> AdaptiveSession | None:
        row = self.db.fetchone(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        )
        if row is None:
            return None
        return self._load(row['session_id'], row['path'])

    def find_by_run(self, run_id: str) -> list[AdaptiveSession]:
        rows = self.db.fetchall(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            WHERE run_id = ?
            ORDER BY updated_at_utc DESC
            """,
            (run_id,),
        )
        return [s for row in rows if (s := self._load(row['session_id'], row['path'])) is not None]

    def find_by_pack(self, pack_id: str, limit: int = 20) -> list[AdaptiveSession]:
        rows = self.db.fetchall(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            WHERE pack_id = ?
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (pack_id, limit),
        )
        return [s for row in rows if (s := self._load(row['session_id'], row['path'])) is not None]

    def _load(self, session_id: str, path: str) -> AdaptiveSession | None:
        try:
            candidate = Path(path)
            if candidate.is_absolute() and candidate.exists():
                payload = json.loads(candidate.read_text(encoding='utf-8'))
            else:
                payload = self.storage.load_json(f'adaptive_sessions/{session_id}.json')
            return AdaptiveSession.model_validate(payload)
        except (FileNotFoundError, OSError):
            return None
