from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import ScenarioRun
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ScenarioRunRepository:
    """SQLite-indexed scenario-run storage with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[ScenarioRun] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[ScenarioRun]
    ) -> RepositoryReadReport[ScenarioRun]:
        self._read_state.report = report
        return report

    def save(self, scenario_run: ScenarioRun) -> ScenarioRun:
        relative_path = f"scenario_runs/{scenario_run.scenario_run_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, scenario_run.model_dump(mode="json")
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO scenario_runs
            (scenario_run_id, run_id, session_id, scenario_id, mode, status,
             summary, path, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_run.scenario_run_id,
                scenario_run.run_id,
                scenario_run.session_id,
                scenario_run.scenario.scenario_id,
                scenario_run.mode.value,
                scenario_run.status.value,
                scenario_run.summary,
                saved_path,
                scenario_run.created_at_utc.isoformat(),
                scenario_run.updated_at_utc.isoformat(),
            ),
        )
        return scenario_run

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[ScenarioRun]:
        results: list[ArtifactReadResult[ScenarioRun]] = []
        for row in rows:
            scenario_run_id = str(row["scenario_run_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=scenario_run_id,
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
                self.storage.root / "scenario_runs" / f"{scenario_run_id}.json"
            )
            results.append(read_model_from_paths(paths, scenario_run_id, ScenarioRun))

        return self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_ROWS:scenario_runs", results)
        )

    def _fetchall_with_diagnostics(
        self, sql: str, parameters: tuple[object, ...]
    ) -> RepositoryReadReport[ScenarioRun]:
        try:
            rows = self.db.fetchall(sql, parameters)
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:scenario_runs", exc
                )
            )
        return self._read_rows(rows)

    def list_recent_with_diagnostics(
        self, limit: int = 20
    ) -> RepositoryReadReport[ScenarioRun]:
        return self._fetchall_with_diagnostics(
            """
            SELECT scenario_run_id, path
            FROM scenario_runs
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_recent(self, limit: int = 20) -> list[ScenarioRun]:
        return self.list_recent_with_diagnostics(limit).require_complete()

    def find_by_run_with_diagnostics(
        self, run_id: str
    ) -> RepositoryReadReport[ScenarioRun]:
        return self._fetchall_with_diagnostics(
            """
            SELECT scenario_run_id, path
            FROM scenario_runs
            WHERE run_id = ?
            ORDER BY updated_at_utc DESC
            """,
            (run_id,),
        )

    def find_by_run(self, run_id: str) -> list[ScenarioRun]:
        return self.find_by_run_with_diagnostics(run_id).require_complete()

    def get_with_diagnostics(
        self, scenario_run_id: str
    ) -> ArtifactReadResult[ScenarioRun]:
        scope = "SQLITE_INDEX_LOOKUP:scenario_runs"
        try:
            row = self.db.fetchone(
                """
                SELECT scenario_run_id, path
                FROM scenario_runs
                WHERE scenario_run_id = ?
                """,
                (scenario_run_id,),
            )
        except sqlite3.Error as exc:
            self._remember_report(
                RepositoryReadReport.from_collection_error(
                    scope, exc, requested_artifact_id=scenario_run_id
                )
            )
            return ArtifactReadResult(
                artifact_id=scenario_run_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Repository read failed.",
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=scenario_run_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No scenario-run row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row["scenario_run_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                result = ArtifactReadResult(
                    artifact_id=resolved_id,
                    path="",
                    status=ArtifactReadStatus.READ_FAILED,
                    error_type=type(exc).__name__,
                    error_message="Repository read failed.",
                )
            else:
                paths: list[Path] = []
                if candidate.is_absolute():
                    paths.append(candidate)
                paths.append(self.storage.root / "scenario_runs" / f"{resolved_id}.json")
                result = read_model_from_paths(paths, resolved_id, ScenarioRun)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, scenario_run_id: str) -> ScenarioRun | None:
        result = self.get_with_diagnostics(scenario_run_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("scenario_run_read_report_not_recorded")
        raise RepositoryReadError(report)
