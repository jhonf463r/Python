from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import ExecutionDossier
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
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
