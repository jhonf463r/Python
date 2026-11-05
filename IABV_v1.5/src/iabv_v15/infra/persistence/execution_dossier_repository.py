from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import local

from iabv_v15.domain.models import ExecutionDossier
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


class ExecutionDossierRepository:
    """SQLite-indexed dossier storage with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[ExecutionDossier] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[ExecutionDossier]
    ) -> RepositoryReadReport[ExecutionDossier]:
        self._read_state.report = report
        return report


    def plan_reindex_with_diagnostics(self) -> RepositoryIndexReconciliationReport:
        """Compare dossier JSON files with SQLite IDs; read-only, never inserts or deletes."""
        scope = "READ_ONLY_INDEX_RECONCILIATION:execution_dossiers"
        indexed_ids: tuple[str, ...] = ()
        rows: list[dict[str, object]] = []
        collection_error_type = ""
        collection_error_message = ""
        try:
            rows = self.db.fetchall(
                "SELECT dossier_id, path FROM execution_dossiers ORDER BY dossier_id ASC"
            )
            indexed_ids = tuple(sorted({str(row["dossier_id"]) for row in rows}))
        except sqlite3.Error as exc:
            collection_error_type = type(exc).__name__
            collection_error_message = str(exc)[:300]

        index_path_results: list[IndexReconciliationIndexPathResult] = []
        for row in (rows if not collection_error_type else ()):
            artifact_id = str(row["dossier_id"])
            try:
                indexed_path = self.storage.resolve_managed_path(row["path"])
                canonical_path = self.storage.resolve_managed_path(
                    f"dossiers/{artifact_id}.json"
                )
            except (OSError, TypeError, ValueError) as exc:
                index_path_results.append(
                    IndexReconciliationIndexPathResult(
                        artifact_id=artifact_id,
                        status=IndexReconciliationPathStatus.INVALID_PATH,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:300],
                    )
                )
                continue

            index_result, index_digest, index_size = inspect_model_file_with_digest(
                indexed_path, artifact_id, ExecutionDossier
            )
            if index_result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND:
                path_status = IndexReconciliationPathStatus.MISSING_PATH
            elif index_result.status == ArtifactReadStatus.READ_FAILED:
                path_status = IndexReconciliationPathStatus.READ_FAILED
            elif index_result.status == ArtifactReadStatus.CORRUPT:
                path_status = IndexReconciliationPathStatus.CORRUPT
            elif index_result.status == ArtifactReadStatus.SCHEMA_UNSUPPORTED:
                path_status = IndexReconciliationPathStatus.SCHEMA_UNSUPPORTED
            elif index_result.value is None or index_result.value.dossier_id != artifact_id:
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
            directory = self.storage.resolve_managed_path("dossiers")
            expected_directory = self.storage.root / "dossiers"
            if directory != expected_directory:
                raise ValueError("Managed reconciliation directory must not be a symlink.")
            if directory.is_dir():
                directory_exists = True
                directory_root = directory.resolve(strict=True)
                entries = sorted(directory.iterdir(), key=lambda item: item.name)
                json_files = [item for item in entries if item.suffix.lower() == ".json"]
                ignored_entries = len(entries) - len(json_files)
                for candidate in json_files:
                    dossier_id = candidate.stem
                    try:
                        safe_path = self.storage.resolve_managed_path(candidate)
                        if directory_root not in safe_path.parents:
                            raise ValueError("Artifact resolves outside its expected managed subdirectory.")
                    except (OSError, TypeError, ValueError) as exc:
                        files.append(
                            IndexReconciliationFileResult(
                                artifact_id=dossier_id,
                                path=candidate.name,
                                status=ArtifactReadStatus.READ_FAILED,
                                error_type=type(exc).__name__,
                                error_message=str(exc)[:300],
                            )
                        )
                        continue
                    result, digest, size_bytes = inspect_model_file_with_digest(
                        safe_path, dossier_id, ExecutionDossier
                    )
                    status = result.status
                    error_type = result.error_type
                    error_message = result.error_message
                    if status == ArtifactReadStatus.FOUND and result.value is not None:
                        if result.value.dossier_id != dossier_id:
                            status = ArtifactReadStatus.SCHEMA_UNSUPPORTED
                            error_type = "ArtifactIdentityMismatch"
                            error_message = "Filename dossier ID does not match the JSON dossier_id."
                    files.append(
                        IndexReconciliationFileResult(
                            artifact_id=dossier_id,
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
                filesystem_error_message = "The managed dossiers path is not a directory."
        except (OSError, TypeError, ValueError) as exc:
            filesystem_error_type = type(exc).__name__
            filesystem_error_message = str(exc)[:300]

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

    def save(self, dossier: ExecutionDossier) -> ExecutionDossier:
        relative_path = f"dossiers/{dossier.dossier_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, dossier.model_dump(mode="json")
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO execution_dossiers
            (dossier_id, scope_type, run_id, episode_id, status, severity,
             issue_hint_text, summary, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dossier.dossier_id,
                dossier.scope.value,
                dossier.run_id,
                dossier.episode_id,
                dossier.status.value,
                dossier.severity.value,
                dossier.issue_hint_text,
                dossier.summary,
                saved_path,
                dossier.created_at_utc.isoformat(),
            ),
        )
        return dossier.model_copy(
            update={"metadata": {**dossier.metadata, "storage_path": saved_path}}
        )

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[ExecutionDossier]:
        results: list[ArtifactReadResult[ExecutionDossier]] = []
        for row in rows:
            dossier_id = str(row["dossier_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=dossier_id,
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
            paths.append(self.storage.root / "dossiers" / f"{dossier_id}.json")
            results.append(read_model_from_paths(paths, dossier_id, ExecutionDossier))

        return self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_ROWS:execution_dossiers", results)
        )

    def _fetchall_with_diagnostics(
        self, sql: str, parameters: tuple[object, ...]
    ) -> RepositoryReadReport[ExecutionDossier]:
        try:
            rows = self.db.fetchall(sql, parameters)
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:execution_dossiers", exc
                )
            )
        return self._read_rows(rows)

    def list_recent_with_diagnostics(
        self, limit: int = 30
    ) -> RepositoryReadReport[ExecutionDossier]:
        return self._fetchall_with_diagnostics(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_recent(self, limit: int = 30) -> list[ExecutionDossier]:
        return self.list_recent_with_diagnostics(limit).require_complete()

    def find_by_run_with_diagnostics(
        self, run_id: str
    ) -> RepositoryReadReport[ExecutionDossier]:
        return self._fetchall_with_diagnostics(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE run_id = ?
            ORDER BY created_at_utc DESC
            """,
            (run_id,),
        )

    def find_by_run(self, run_id: str) -> list[ExecutionDossier]:
        return self.find_by_run_with_diagnostics(run_id).require_complete()

    def find_by_episode_with_diagnostics(
        self, episode_id: str
    ) -> RepositoryReadReport[ExecutionDossier]:
        return self._fetchall_with_diagnostics(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE episode_id = ?
            ORDER BY created_at_utc DESC
            """,
            (episode_id,),
        )

    def find_by_episode(self, episode_id: str) -> list[ExecutionDossier]:
        return self.find_by_episode_with_diagnostics(episode_id).require_complete()

    def find_by_issue_with_diagnostics(
        self, issue_hint: str, limit: int = 20
    ) -> RepositoryReadReport[ExecutionDossier]:
        probe = (issue_hint or "").strip().lower()
        if not probe:
            return self._remember_report(
                RepositoryReadReport.from_not_executed(
                    "SQLITE_INDEX_ROWS:execution_dossiers"
                )
            )
        return self._fetchall_with_diagnostics(
            """
            SELECT dossier_id, path
            FROM execution_dossiers
            WHERE lower(issue_hint_text) LIKE ? OR lower(summary) LIKE ?
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (f"%{probe}%", f"%{probe}%", limit),
        )

    def find_by_issue(self, issue_hint: str, limit: int = 20) -> list[ExecutionDossier]:
        if not (issue_hint or "").strip():
            self.find_by_issue_with_diagnostics(issue_hint, limit)
            return []
        return self.find_by_issue_with_diagnostics(issue_hint, limit).require_complete()

    def get_with_diagnostics(
        self, dossier_id: str
    ) -> ArtifactReadResult[ExecutionDossier]:
        scope = "SQLITE_INDEX_LOOKUP:execution_dossiers"
        try:
            row = self.db.fetchone(
                """
                SELECT dossier_id, path
                FROM execution_dossiers
                WHERE dossier_id = ?
                """,
                (dossier_id,),
            )
        except sqlite3.Error as exc:
            report = RepositoryReadReport.from_collection_error(
                scope, exc, requested_artifact_id=dossier_id
            )
            self._remember_report(report)
            return ArtifactReadResult(
                artifact_id=dossier_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc)[:300],
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=dossier_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No execution-dossier row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row["dossier_id"])
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
                paths.append(self.storage.root / "dossiers" / f"{resolved_id}.json")
                result = read_model_from_paths(paths, resolved_id, ExecutionDossier)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, dossier_id: str) -> ExecutionDossier | None:
        result = self.get_with_diagnostics(dossier_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("execution_dossier_read_report_not_recorded")
        raise RepositoryReadError(report)
