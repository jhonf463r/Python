from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import CapabilityReadiness
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class CapabilityRepository:
    """SQLite-indexed capability snapshots with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[CapabilityReadiness] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[CapabilityReadiness]
    ) -> RepositoryReadReport[CapabilityReadiness]:
        self._read_state.report = report
        return report

    def save_many(
        self, capabilities: list[CapabilityReadiness]
    ) -> list[CapabilityReadiness]:
        for capability in capabilities:
            self.save(capability)
        return capabilities

    def save(self, capability: CapabilityReadiness) -> CapabilityReadiness:
        capability_key = self._key(capability.capability_id, capability.site_id)
        relative_path = f"capabilities/{capability_key}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, capability.model_dump(mode="json")
        )
        summary = (
            capability.suggested_next_step
            or ", ".join(capability.evidence[:2])
            or capability.title
        )
        from datetime import datetime, timezone

        self.db.execute(
            """
            INSERT OR REPLACE INTO capability_snapshots
            (capability_key, capability_id, site_id, status, score, summary,
             path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capability_key,
                capability.capability_id,
                capability.site_id,
                capability.status.value,
                capability.score,
                summary,
                saved_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return capability

    def _key(self, capability_id: str, site_id: str | None) -> str:
        scope = (site_id or "global").replace("/", "_").replace("\\\\", "_")
        return f"{scope}__{capability_id}".replace(":", "_")

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[CapabilityReadiness]:
        results: list[ArtifactReadResult[CapabilityReadiness]] = []
        for row in rows:
            capability_key = str(row["capability_key"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=capability_key,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message="Repository read failed.",
                    )
                )
                continue
            paths: list[Path] = []
            if candidate.is_absolute():
                paths.append(candidate)
            paths.append(
                self.storage.root / "capabilities" / f"{capability_key}.json"
            )
            results.append(
                read_model_from_paths(paths, capability_key, CapabilityReadiness)
            )
        return self._remember_report(
            RepositoryReadReport.from_results(
                "SQLITE_INDEX_ROWS:capability_snapshots", results
            )
        )

    def list_recent_with_diagnostics(
        self, limit: int = 30
    ) -> RepositoryReadReport[CapabilityReadiness]:
        try:
            rows = self.db.fetchall(
                """
                SELECT capability_key, path
                FROM capability_snapshots
                ORDER BY updated_at_utc DESC
                LIMIT ?
                """,
                (limit,),
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:capability_snapshots", exc
                )
            )
        return self._read_rows(rows)

    def list_recent(self, limit: int = 30) -> list[CapabilityReadiness]:
        return self.list_recent_with_diagnostics(limit).require_complete()

    def find_by_site_with_diagnostics(
        self, site_id: str, limit: int = 30
    ) -> RepositoryReadReport[CapabilityReadiness]:
        normalized = site_id or ""
        try:
            rows = self.db.fetchall(
                """
                SELECT capability_key, path
                FROM capability_snapshots
                WHERE site_id = ? OR (? = '' AND site_id IS NULL)
                ORDER BY updated_at_utc DESC
                LIMIT ?
                """,
                (normalized, normalized, limit),
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:capability_snapshots", exc
                )
            )
        return self._read_rows(rows)

    def find_by_site(
        self, site_id: str, limit: int = 30
    ) -> list[CapabilityReadiness]:
        return self.find_by_site_with_diagnostics(site_id, limit).require_complete()

    def get_with_diagnostics(
        self, capability_id: str, site_id: str | None = None
    ) -> ArtifactReadResult[CapabilityReadiness]:
        capability_key = self._key(capability_id, site_id)
        scope = "SQLITE_INDEX_LOOKUP:capability_snapshots"
        try:
            row = self.db.fetchone(
                """
                SELECT capability_key, path
                FROM capability_snapshots
                WHERE capability_key = ?
                """,
                (capability_key,),
            )
        except sqlite3.Error as exc:
            self._remember_report(
                RepositoryReadReport.from_collection_error(
                    scope, exc, requested_artifact_id=capability_key
                )
            )
            return ArtifactReadResult(
                artifact_id=capability_key,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Repository read failed.",
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=capability_key,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No capability snapshot row exists for this key.",
            )
        else:
            resolved_key = str(row["capability_key"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                result = ArtifactReadResult(
                    artifact_id=resolved_key,
                    path="",
                    status=ArtifactReadStatus.READ_FAILED,
                    error_type=type(exc).__name__,
                    error_message="Repository read failed.",
                )
            else:
                paths: list[Path] = []
                if candidate.is_absolute():
                    paths.append(candidate)
                paths.append(
                    self.storage.root / "capabilities" / f"{resolved_key}.json"
                )
                result = read_model_from_paths(paths, resolved_key, CapabilityReadiness)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(
        self, capability_id: str, site_id: str | None = None
    ) -> CapabilityReadiness | None:
        result = self.get_with_diagnostics(capability_id, site_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("capability_read_report_not_recorded")
        raise RepositoryReadError(report)
