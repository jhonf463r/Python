from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import AdaptiveSession
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class AdaptiveSessionRepository:
    """SQLite-indexed adaptive-session storage with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[AdaptiveSession] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[AdaptiveSession]
    ) -> RepositoryReadReport[AdaptiveSession]:
        self._read_state.report = report
        return report

    def save(self, session: AdaptiveSession) -> AdaptiveSession:
        relative_path = f"adaptive_sessions/{session.session_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, session.model_dump(mode="json")
        )
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
            (session_id, run_id, status, intent_key, pack_id, site_id, summary,
             path, created_at_utc, updated_at_utc)
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

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[AdaptiveSession]:
        results: list[ArtifactReadResult[AdaptiveSession]] = []
        for row in rows:
            session_id = str(row["session_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=session_id,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:300],
                    )
                )
                continue

            paths: list[Path] = []
            if candidate.is_absolute():
                paths.append(candidate)
            paths.append(self.storage.root / "adaptive_sessions" / f"{session_id}.json")
            results.append(read_model_from_paths(paths, session_id, AdaptiveSession))

        return self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_ROWS:adaptive_sessions", results)
        )

    def _fetchall_with_diagnostics(
        self, sql: str, parameters: tuple[object, ...]
    ) -> RepositoryReadReport[AdaptiveSession]:
        try:
            rows = self.db.fetchall(sql, parameters)
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:adaptive_sessions", exc
                )
            )
        return self._read_rows(rows)

    def list_recent_with_diagnostics(
        self, limit: int = 20
    ) -> RepositoryReadReport[AdaptiveSession]:
        return self._fetchall_with_diagnostics(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_recent(self, limit: int = 20) -> list[AdaptiveSession]:
        return self.list_recent_with_diagnostics(limit).require_complete()

    def find_by_run_with_diagnostics(
        self, run_id: str
    ) -> RepositoryReadReport[AdaptiveSession]:
        return self._fetchall_with_diagnostics(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            WHERE run_id = ?
            ORDER BY updated_at_utc DESC
            """,
            (run_id,),
        )

    def find_by_run(self, run_id: str) -> list[AdaptiveSession]:
        return self.find_by_run_with_diagnostics(run_id).require_complete()

    def find_by_pack_with_diagnostics(
        self, pack_id: str, limit: int = 20
    ) -> RepositoryReadReport[AdaptiveSession]:
        return self._fetchall_with_diagnostics(
            """
            SELECT session_id, path
            FROM adaptive_sessions
            WHERE pack_id = ?
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (pack_id, limit),
        )

    def find_by_pack(self, pack_id: str, limit: int = 20) -> list[AdaptiveSession]:
        return self.find_by_pack_with_diagnostics(pack_id, limit).require_complete()

    def get_with_diagnostics(
        self, session_id: str
    ) -> ArtifactReadResult[AdaptiveSession]:
        scope = "SQLITE_INDEX_LOOKUP:adaptive_sessions"
        try:
            row = self.db.fetchone(
                """
                SELECT session_id, path
                FROM adaptive_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            )
        except sqlite3.Error as exc:
            report = RepositoryReadReport.from_collection_error(
                scope, exc, requested_artifact_id=session_id
            )
            self._remember_report(report)
            return ArtifactReadResult(
                artifact_id=session_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc)[:300],
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=session_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No adaptive-session row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row["session_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                result = ArtifactReadResult(
                    artifact_id=resolved_id,
                    path="",
                    status=ArtifactReadStatus.READ_FAILED,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:300],
                )
            else:
                paths: list[Path] = []
                if candidate.is_absolute():
                    paths.append(candidate)
                paths.append(
                    self.storage.root / "adaptive_sessions" / f"{resolved_id}.json"
                )
                result = read_model_from_paths(paths, resolved_id, AdaptiveSession)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, session_id: str) -> AdaptiveSession | None:
        result = self.get_with_diagnostics(session_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("adaptive_session_read_report_not_recorded")
        raise RepositoryReadError(report)
