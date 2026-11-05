from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import ReplayAnnotation
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ReplayAnnotationRepository:
    """SQLite-indexed replay annotations with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[ReplayAnnotation] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[ReplayAnnotation]
    ) -> RepositoryReadReport[ReplayAnnotation]:
        self._read_state.report = report
        return report

    def save(self, annotation: ReplayAnnotation) -> ReplayAnnotation:
        relative_path = f"annotations/{annotation.annotation_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, annotation.model_dump(mode="json")
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO replay_annotations
            (annotation_id, episode_id, step_id, screenshot_path, group_key,
             status, source, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                annotation.annotation_id,
                annotation.episode_id,
                annotation.step_id,
                annotation.screenshot_path,
                annotation.group_key,
                annotation.status.value,
                annotation.source.value,
                saved_path,
                annotation.updated_at_utc.isoformat(),
            ),
        )
        return annotation

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[ReplayAnnotation]:
        results: list[ArtifactReadResult[ReplayAnnotation]] = []
        for row in rows:
            annotation_id = str(row["annotation_id"])
            try:
                candidate = self.storage.resolve_managed_path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=annotation_id,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:300],
                    )
                )
                continue
            try:
                fallback = self.storage.resolve_managed_path(
                    f"annotations/{annotation_id}.json"
                )
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=annotation_id,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:300],
                    )
                )
                continue
            results.append(
                read_model_from_paths([candidate, fallback], annotation_id, ReplayAnnotation)
            )
        return self._remember_report(
            RepositoryReadReport.from_results(
                "SQLITE_INDEX_ROWS:replay_annotations", results
            )
        )

    def list_for_episode_with_diagnostics(
        self, episode_id: str
    ) -> RepositoryReadReport[ReplayAnnotation]:
        try:
            rows = self.db.fetchall(
                """
                SELECT annotation_id, path
                FROM replay_annotations
                WHERE episode_id = ?
                ORDER BY updated_at_utc DESC
                """,
                (episode_id,),
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:replay_annotations", exc
                )
            )
        return self._read_rows(rows)

    def list_for_episode(self, episode_id: str) -> list[ReplayAnnotation]:
        return self.list_for_episode_with_diagnostics(episode_id).require_complete()

    def find_by_step_with_diagnostics(
        self, step_id: str
    ) -> RepositoryReadReport[ReplayAnnotation]:
        try:
            rows = self.db.fetchall(
                """
                SELECT annotation_id, path
                FROM replay_annotations
                WHERE step_id = ?
                ORDER BY updated_at_utc DESC
                """,
                (step_id,),
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:replay_annotations", exc
                )
            )
        return self._read_rows(rows)

    def find_by_step(self, step_id: str) -> list[ReplayAnnotation]:
        return self.find_by_step_with_diagnostics(step_id).require_complete()

    def get_with_diagnostics(
        self, annotation_id: str
    ) -> ArtifactReadResult[ReplayAnnotation]:
        scope = "SQLITE_INDEX_LOOKUP:replay_annotations"
        try:
            row = self.db.fetchone(
                """
                SELECT annotation_id, path
                FROM replay_annotations
                WHERE annotation_id = ?
                """,
                (annotation_id,),
            )
        except sqlite3.Error as exc:
            self._remember_report(
                RepositoryReadReport.from_collection_error(
                    scope, exc, requested_artifact_id=annotation_id
                )
            )
            return ArtifactReadResult(
                artifact_id=annotation_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc)[:300],
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=annotation_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No replay-annotation row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row["annotation_id"])
            try:
                candidate = self.storage.resolve_managed_path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                result = ArtifactReadResult(
                    artifact_id=resolved_id,
                    path="",
                    status=ArtifactReadStatus.READ_FAILED,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:300],
                )
            else:
                try:
                    fallback = self.storage.resolve_managed_path(
                        f"annotations/{resolved_id}.json"
                    )
                except (TypeError, ValueError, OSError) as exc:
                    result = ArtifactReadResult(
                        artifact_id=resolved_id,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:300],
                    )
                else:
                    result = read_model_from_paths(
                        [candidate, fallback], resolved_id, ReplayAnnotation
                    )

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, annotation_id: str) -> ReplayAnnotation | None:
        result = self.get_with_diagnostics(annotation_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("replay_annotation_read_report_not_recorded")
        raise RepositoryReadError(report)

    def delete(self, annotation_id: str) -> None:
        """Explicitly delete only after the indexed artifact has been read successfully."""
        result = self.get_with_diagnostics(annotation_id)
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return
        if result.status != ArtifactReadStatus.FOUND or result.value is None:
            report = self.last_read_report
            if report is None:
                raise RuntimeError("replay_annotation_read_report_not_recorded")
            raise RepositoryReadError(report)

        # Delete the exact artifact path that was successfully read. Any file
        # deletion error stops before the SQLite index row is removed.
        Path(result.path).unlink(missing_ok=True)
        self.db.execute(
            "DELETE FROM replay_annotations WHERE annotation_id = ?",
            (annotation_id,),
        )
