from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import ApprovalCheckpoint
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ApprovalCheckpointRepository:
    """SQLite-indexed approval checkpoints with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[ApprovalCheckpoint] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[ApprovalCheckpoint]
    ) -> RepositoryReadReport[ApprovalCheckpoint]:
        self._read_state.report = report
        return report

    def save_many(
        self, checkpoints: list[ApprovalCheckpoint]
    ) -> list[ApprovalCheckpoint]:
        for checkpoint in checkpoints:
            self.save(checkpoint)
        return checkpoints

    def save(self, checkpoint: ApprovalCheckpoint) -> ApprovalCheckpoint:
        relative_path = f"approvals/{checkpoint.checkpoint_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, checkpoint.model_dump(mode="json")
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO approval_checkpoints
            (checkpoint_id, session_id, playbook_id, decision, phase_key,
             risk_level, title, path, created_at_utc)
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

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[ApprovalCheckpoint]:
        results: list[ArtifactReadResult[ApprovalCheckpoint]] = []
        for row in rows:
            checkpoint_id = str(row["checkpoint_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=checkpoint_id,
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
            paths.append(self.storage.root / "approvals" / f"{checkpoint_id}.json")
            results.append(
                read_model_from_paths(paths, checkpoint_id, ApprovalCheckpoint)
            )
        return self._remember_report(
            RepositoryReadReport.from_results(
                "SQLITE_INDEX_ROWS:approval_checkpoints", results
            )
        )

    def list_for_session_with_diagnostics(
        self, session_id: str
    ) -> RepositoryReadReport[ApprovalCheckpoint]:
        try:
            rows = self.db.fetchall(
                """
                SELECT checkpoint_id, path
                FROM approval_checkpoints
                WHERE session_id = ?
                ORDER BY created_at_utc ASC
                """,
                (session_id,),
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:approval_checkpoints", exc
                )
            )
        return self._read_rows(rows)

    def list_for_session(self, session_id: str) -> list[ApprovalCheckpoint]:
        return self.list_for_session_with_diagnostics(session_id).require_complete()

    def get_with_diagnostics(
        self, checkpoint_id: str
    ) -> ArtifactReadResult[ApprovalCheckpoint]:
        scope = "SQLITE_INDEX_LOOKUP:approval_checkpoints"
        try:
            row = self.db.fetchone(
                """
                SELECT checkpoint_id, path
                FROM approval_checkpoints
                WHERE checkpoint_id = ?
                """,
                (checkpoint_id,),
            )
        except sqlite3.Error as exc:
            self._remember_report(
                RepositoryReadReport.from_collection_error(
                    scope, exc, requested_artifact_id=checkpoint_id
                )
            )
            return ArtifactReadResult(
                artifact_id=checkpoint_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc)[:300],
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=checkpoint_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No approval-checkpoint row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row["checkpoint_id"])
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
                paths.append(self.storage.root / "approvals" / f"{resolved_id}.json")
                result = read_model_from_paths(paths, resolved_id, ApprovalCheckpoint)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, checkpoint_id: str) -> ApprovalCheckpoint | None:
        result = self.get_with_diagnostics(checkpoint_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("approval_checkpoint_read_report_not_recorded")
        raise RepositoryReadError(report)
