from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import local

from iabv_v15.domain.models import RuntimeAdjustment, RuntimeTuningProfile
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class RuntimeTuningRepository:
    """SQLite-indexed runtime-tuning profiles with non-destructive reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[RuntimeTuningProfile] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[RuntimeTuningProfile]
    ) -> RepositoryReadReport[RuntimeTuningProfile]:
        self._read_state.report = report
        return report

    def save(self, profile: RuntimeTuningProfile) -> RuntimeTuningProfile:
        relative_path = f"runtime_tuning/{profile.scope_key}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, profile.model_dump(mode="json")
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO runtime_tuning_profiles
            (profile_id, scope_key, path, updated_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (
                profile.profile_id,
                profile.scope_key,
                saved_path,
                profile.updated_at_utc.isoformat(),
            ),
        )
        return profile

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[RuntimeTuningProfile]:
        results: list[ArtifactReadResult[RuntimeTuningProfile]] = []
        for row in rows:
            scope_key = str(row["scope_key"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=scope_key,
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
            paths.append(self.storage.root / "runtime_tuning" / f"{scope_key}.json")
            results.append(read_model_from_paths(paths, scope_key, RuntimeTuningProfile))
        return self._remember_report(
            RepositoryReadReport.from_results(
                "SQLITE_INDEX_ROWS:runtime_tuning_profiles", results
            )
        )

    def list_recent_with_diagnostics(
        self, limit: int = 10
    ) -> RepositoryReadReport[RuntimeTuningProfile]:
        try:
            rows = self.db.fetchall(
                """
                SELECT scope_key, path
                FROM runtime_tuning_profiles
                ORDER BY updated_at_utc DESC
                LIMIT ?
                """,
                (limit,),
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:runtime_tuning_profiles", exc
                )
            )
        return self._read_rows(rows)

    def list_recent(self, limit: int = 10) -> list[RuntimeTuningProfile]:
        return self.list_recent_with_diagnostics(limit).require_complete()

    def get_with_diagnostics(
        self, scope_key: str = "global"
    ) -> ArtifactReadResult[RuntimeTuningProfile]:
        scope = "SQLITE_INDEX_LOOKUP:runtime_tuning_profiles"
        try:
            row = self.db.fetchone(
                """
                SELECT scope_key, path
                FROM runtime_tuning_profiles
                WHERE scope_key = ?
                ORDER BY updated_at_utc DESC
                LIMIT 1
                """,
                (scope_key,),
            )
        except sqlite3.Error as exc:
            self._remember_report(
                RepositoryReadReport.from_collection_error(
                    scope, exc, requested_artifact_id=scope_key
                )
            )
            return ArtifactReadResult(
                artifact_id=scope_key,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Repository read failed.",
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=scope_key,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No runtime-tuning profile row exists for this scope.",
            )
        else:
            resolved_key = str(row["scope_key"])
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
                    self.storage.root / "runtime_tuning" / f"{resolved_key}.json"
                )
                result = read_model_from_paths(paths, resolved_key, RuntimeTuningProfile)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, scope_key: str = "global") -> RuntimeTuningProfile | None:
        result = self.get_with_diagnostics(scope_key)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("runtime_tuning_read_report_not_recorded")
        raise RepositoryReadError(report)

    def append_adjustment(
        self, adjustment: RuntimeAdjustment, scope_key: str = "global"
    ) -> RuntimeTuningProfile:
        profile = self.get(scope_key)
        if profile is None:
            profile = RuntimeTuningProfile(scope_key=scope_key)
        profile.adjustments.append(adjustment)
        profile.updated_at_utc = datetime.now(timezone.utc)
        return self.save(profile)
