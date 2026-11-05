from __future__ import annotations

from pathlib import Path
from threading import local

from iabv_v15.domain.models import CodexPendingIssue
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class PendingIssueRepository:
    """SQLite-indexed JSON repository with explicit per-artifact read outcomes."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[CodexPendingIssue] | None:
        """Diagnostics for the most recent read on this thread."""
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[CodexPendingIssue]
    ) -> RepositoryReadReport[CodexPendingIssue]:
        self._read_state.report = report
        return report

    def _remember_collection_error(
        self,
        scope: str,
        error: Exception,
        *,
        requested_artifact_id: str = "",
    ) -> RepositoryReadReport[CodexPendingIssue]:
        return self._remember_report(
            RepositoryReadReport.from_collection_error(
                scope,
                error,
                requested_artifact_id=requested_artifact_id,
            )
        )

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

    def list_recent_with_diagnostics(self, limit: int = 20) -> RepositoryReadReport[CodexPendingIssue]:
        return self._fetchall_with_diagnostics(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_recent(self, limit: int = 20) -> list[CodexPendingIssue]:
        return self.list_recent_with_diagnostics(limit).require_complete()

    def get_with_diagnostics(self, issue_id: str) -> ArtifactReadResult[CodexPendingIssue]:
        try:
            row = self.db.fetchone(
                """
                SELECT issue_id, path
                FROM codex_pending_issues
                WHERE issue_id = ?
                """,
                (issue_id,),
            )
        except Exception as exc:
            self._remember_collection_error(
                "SQLITE_INDEX_LOOKUP",
                exc,
                requested_artifact_id=issue_id,
            )
            return ArtifactReadResult(
                artifact_id=issue_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc)[:300],
            )
        if row is None:
            result = ArtifactReadResult(
                artifact_id=issue_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No pending-issue row exists in the SQLite index.",
            )
        else:
            result = self._load_result(row['issue_id'], row['path'])
        self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_LOOKUP", [result])
        )
        return result

    def get(self, issue_id: str) -> CodexPendingIssue | None:
        result = self.get_with_diagnostics(issue_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND and result.error_type == "IndexRowNotFound":
            return None
        report = self.last_read_report
        assert report is not None
        raise RepositoryReadError(report)

    def find_by_run_with_diagnostics(self, run_id: str) -> RepositoryReadReport[CodexPendingIssue]:
        return self._fetchall_with_diagnostics(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            """,
            (run_id,),
        )

    def find_by_run(self, run_id: str) -> list[CodexPendingIssue]:
        return self.find_by_run_with_diagnostics(run_id).require_complete()

    def find_by_scenario_id_with_diagnostics(
        self, scenario_id: str
    ) -> RepositoryReadReport[CodexPendingIssue]:
        return self._fetchall_with_diagnostics(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            WHERE scenario_id = ?
            ORDER BY created_at_utc DESC
            """,
            (scenario_id,),
        )

    def find_by_scenario_id(self, scenario_id: str) -> list[CodexPendingIssue]:
        return self.find_by_scenario_id_with_diagnostics(scenario_id).require_complete()

    def find_by_session_with_diagnostics(
        self, session_id: str
    ) -> RepositoryReadReport[CodexPendingIssue]:
        return self._fetchall_with_diagnostics(
            """
            SELECT issue_id, path
            FROM codex_pending_issues
            WHERE session_id = ?
            ORDER BY created_at_utc DESC
            """,
            (session_id,),
        )

    def find_by_session(self, session_id: str) -> list[CodexPendingIssue]:
        return self.find_by_session_with_diagnostics(session_id).require_complete()

    def _fetchall_with_diagnostics(
        self,
        sql: str,
        parameters: tuple[object, ...],
    ) -> RepositoryReadReport[CodexPendingIssue]:
        try:
            rows = self.db.fetchall(sql, parameters)
        except Exception as exc:
            return self._remember_collection_error("SQLITE_INDEX_ROWS", exc)
        return self._read_rows(rows)

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[CodexPendingIssue]:
        results = [
            self._load_result(row['issue_id'], row['path'])
            for row in rows
        ]
        return self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_ROWS", results)
        )

    def _load_result(self, issue_id: str, path: str) -> ArtifactReadResult[CodexPendingIssue]:
        candidate = Path(path)
        paths: list[Path] = []
        if candidate.is_absolute():
            paths.append(candidate)
        paths.append(self.storage.root / f"pending_issues/{issue_id}.json")
        return read_model_from_paths(paths, issue_id, CodexPendingIssue)
