from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import CodexPendingIssue
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class PendingIssueRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, issue: CodexPendingIssue) -> CodexPendingIssue:
        relative_path = f"pending_issues/{issue.issue_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, issue.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO codex_pending_issues
            (issue_id, run_id, episode_id, session_id, scenario_id, category, status, summary, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue.issue_id,
                issue.run_id,
                issue.episode_id,
                issue.session_id,
                issue.scenario_id,
                issue.category.value,
                issue.status.value,
                issue.summary,
                saved_path,
                issue.created_at_utc.isoformat(),
            ),
        )
        return issue

    def list_recent(self, limit: int = 20) -> list[CodexPendingIssue]:
        rows = self.db.fetchall(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        items: list[CodexPendingIssue] = []
        for row in rows:
            loaded = self._load_optional(row['issue_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def get(self, issue_id: str) -> CodexPendingIssue | None:
        row = self.db.fetchone(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            WHERE issue_id = ?
            """,
            (issue_id,),
        )
        if row is None:
            return None
        return self._load_optional(row['issue_id'], row['path'])

    def find_by_run(self, run_id: str) -> list[CodexPendingIssue]:
        rows = self.db.fetchall(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            """,
            (run_id,),
        )
        items: list[CodexPendingIssue] = []
        for row in rows:
            loaded = self._load_optional(row['issue_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def find_by_session(self, session_id: str) -> list[CodexPendingIssue]:
        rows = self.db.fetchall(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            WHERE session_id = ?
            ORDER BY created_at_utc DESC
            """,
            (session_id,),
        )
        items: list[CodexPendingIssue] = []
        for row in rows:
            loaded = self._load_optional(row['issue_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def _load(self, issue_id: str, path: str) -> CodexPendingIssue:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f'pending_issues/{issue_id}.json')
        return CodexPendingIssue.model_validate(payload)

    def _load_optional(self, issue_id: str, path: str) -> CodexPendingIssue | None:
        try:
            return self._load(issue_id, path)
        except FileNotFoundError:
            return None
