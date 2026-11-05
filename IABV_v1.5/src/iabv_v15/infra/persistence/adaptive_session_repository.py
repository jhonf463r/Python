from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import local

from iabv_v15.domain.models import AdaptiveSession
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    inspect_model_file_with_digest,
    read_model_from_paths,
    IndexReconciliationFileResult,
    IndexReconciliationIndexPathResult,
    IndexReconciliationPathStatus,
    RepositoryIndexReconciliationReport,
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


    def plan_reindex_with_diagnostics(self) -> RepositoryIndexReconciliationReport:
        """Compare adaptive-session JSON files with SQLite IDs; strictly read-only."""
        scope = "READ_ONLY_INDEX_RECONCILIATION:adaptive_sessions"
        indexed_ids: tuple[str, ...] = ()
        rows: list[dict[str, object]] = []
        collection_error_type = ""
        collection_error_message = ""
        try:
            rows = self.db.fetchall(
                "SELECT session_id, path FROM adaptive_sessions ORDER BY session_id ASC"
            )
            indexed_ids = tuple(sorted({str(row["session_id"]) for row in rows}))
        except sqlite3.Error as exc:
            collection_error_type = type(exc).__name__
            collection_error_message = "SQLite index enumeration failed."

        index_path_results: list[IndexReconciliationIndexPathResult] = []
        for row in (rows if not collection_error_type else ()):
            artifact_id = str(row["session_id"])
            try:
                indexed_path = self.storage.resolve_managed_path(row["path"])
                canonical_path = self.storage.resolve_managed_path(
                    f"adaptive_sessions/{artifact_id}.json"
                )
            except (OSError, TypeError, ValueError) as exc:
                index_path_results.append(
                    IndexReconciliationIndexPathResult(
                        artifact_id=artifact_id,
                        status=IndexReconciliationPathStatus.INVALID_PATH,
                        error_type=type(exc).__name__,
                        error_message="Indexed artifact path is not a valid managed path.",
                    )
                )
                continue

            index_result, index_digest, index_size = inspect_model_file_with_digest(
                indexed_path, artifact_id, AdaptiveSession
            )
            if index_result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND:
                path_status = IndexReconciliationPathStatus.MISSING_PATH
            elif index_result.status == ArtifactReadStatus.READ_FAILED:
                path_status = IndexReconciliationPathStatus.READ_FAILED
            elif index_result.status == ArtifactReadStatus.CORRUPT:
                path_status = IndexReconciliationPathStatus.CORRUPT
            elif index_result.status == ArtifactReadStatus.SCHEMA_UNSUPPORTED:
                path_status = IndexReconciliationPathStatus.SCHEMA_UNSUPPORTED
            elif index_result.value is None or index_result.value.session_id != artifact_id:
                path_status = IndexReconciliationPathStatus.IDENTITY_MISMATCH
            elif indexed_path == canonical_path:
                path_status = IndexReconciliationPathStatus.SAFE_CANONICAL_PATH
            else:
                path_status = IndexReconciliationPathStatus.SAFE_NONCANONICAL_PATH

            index_path_results.append(
                IndexReconciliationIndexPathResult(
                    artifact_id=artifact_id,
                    status=path_status,
                    error_type=index_result.error_type,
                    error_message=index_result.error_message,
                    sha256=index_digest,
                    size_bytes=index_size,
                )
            )

        files: list[IndexReconciliationFileResult] = []
        directory_exists = False
        filesystem_error_type = ""
        filesystem_error_message = ""
        ignored_entries = 0
        try:
            directory = self.storage.resolve_managed_path("adaptive_sessions")
            expected_directory = self.storage.root / "adaptive_sessions"
            if directory != expected_directory:
                raise ValueError("Managed reconciliation directory must not be a symlink.")
            if directory.is_dir():
                directory_exists = True
                directory_root = directory.resolve(strict=True)
                entries = sorted(directory.iterdir(), key=lambda item: item.name)
                json_files = [item for item in entries if item.suffix.lower() == ".json"]
                ignored_entries = len(entries) - len(json_files)
                for candidate in json_files:
                    session_id = candidate.stem
                    try:
                        safe_path = self.storage.resolve_managed_path(candidate)
                        if directory_root not in safe_path.parents:
                            raise ValueError("Artifact resolves outside its expected managed subdirectory.")
                    except (OSError, TypeError, ValueError) as exc:
                        files.append(
                            IndexReconciliationFileResult(
                                artifact_id=session_id,
                                path=candidate.name,
                                status=ArtifactReadStatus.READ_FAILED,
                                error_type=type(exc).__name__,
                                error_message="Indexed artifact path is not a valid managed path.",
                            )
                        )
                        continue
                    result, digest, size_bytes = inspect_model_file_with_digest(
                        safe_path, session_id, AdaptiveSession
                    )
                    status = result.status
                    error_type = result.error_type
                    error_message = result.error_message
                    if status == ArtifactReadStatus.FOUND and result.value is not None:
                        if result.value.session_id != session_id:
                            status = ArtifactReadStatus.SCHEMA_UNSUPPORTED
                            error_type = "ArtifactIdentityMismatch"
                            error_message = "Filename session ID does not match the JSON session_id."
                    files.append(
                        IndexReconciliationFileResult(
                            artifact_id=session_id,
                            path=candidate.name,
                            status=status,
                            error_type=error_type,
                            error_message=error_message,
                            sha256=digest,
                            size_bytes=size_bytes,
                        )
                    )
            elif directory.exists():
                filesystem_error_type = "NotADirectoryError"
                filesystem_error_message = "The managed adaptive_sessions path is not a directory."
        except (OSError, TypeError, ValueError) as exc:
            filesystem_error_type = type(exc).__name__
            filesystem_error_message = "Managed artifact directory could not be enumerated."

        return RepositoryIndexReconciliationReport(
            scope=scope,
            indexed_ids=indexed_ids,
            files=tuple(files),
            index_path_results=tuple(index_path_results),
            directory_exists=directory_exists,
            observed_at_utc=datetime.now(timezone.utc).isoformat(),
            collection_error_type=collection_error_type,
            collection_error_message=collection_error_message,
            filesystem_error_type=filesystem_error_type,
            filesystem_error_message=filesystem_error_message,
            ignored_entries=ignored_entries,
        )

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
                        error_message="Indexed artifact path is not a valid managed path.",
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
                error_message="Indexed artifact path is not a valid managed path.",
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
                    error_message="Indexed artifact path is not a valid managed path.",
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
