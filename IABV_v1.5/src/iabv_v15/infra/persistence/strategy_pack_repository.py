from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local

from iabv_v15.domain.models import StrategyPack
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class StrategyPackRepository:
    """SQLite-indexed strategy-pack storage with non-destructive diagnostic reads."""

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[StrategyPack] | None:
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[StrategyPack]
    ) -> RepositoryReadReport[StrategyPack]:
        self._read_state.report = report
        return report

    def save(self, pack: StrategyPack) -> StrategyPack:
        relative_path = f"strategy_packs/{pack.pack_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path, pack.model_dump(mode="json")
        )
        updated_at = str(pack.metadata.get("updated_at_utc") or "")
        if not updated_at:
            updated_at = str(pack.metadata.get("created_at_utc") or "")
        if not updated_at:
            from datetime import datetime, timezone

            updated_at = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """
            INSERT OR REPLACE INTO strategy_packs
            (pack_id, title, domain_kind, risk_level, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                pack.pack_id,
                pack.title,
                pack.domain_kind,
                pack.risk_level.value,
                saved_path,
                updated_at,
            ),
        )
        return pack

    def _read_rows(
        self, rows: list[dict[str, str]]
    ) -> RepositoryReadReport[StrategyPack]:
        results: list[ArtifactReadResult[StrategyPack]] = []
        for row in rows:
            pack_id = str(row["pack_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=pack_id,
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
            paths.append(self.storage.root / "strategy_packs" / f"{pack_id}.json")
            results.append(read_model_from_paths(paths, pack_id, StrategyPack))

        return self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_ROWS:strategy_packs", results)
        )

    def _fetchall_with_diagnostics(self) -> RepositoryReadReport[StrategyPack]:
        try:
            rows = self.db.fetchall(
                """
                SELECT pack_id, path
                FROM strategy_packs
                ORDER BY domain_kind ASC, title ASC
                """
            )
        except sqlite3.Error as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(
                    "SQLITE_INDEX_ROWS:strategy_packs", exc
                )
            )
        return self._read_rows(rows)

    def list_all_with_diagnostics(self) -> RepositoryReadReport[StrategyPack]:
        return self._fetchall_with_diagnostics()

    def list_all(self) -> list[StrategyPack]:
        return self.list_all_with_diagnostics().require_complete()

    def get_with_diagnostics(self, pack_id: str) -> ArtifactReadResult[StrategyPack]:
        scope = "SQLITE_INDEX_LOOKUP:strategy_packs"
        try:
            row = self.db.fetchone(
                """
                SELECT pack_id, path
                FROM strategy_packs
                WHERE pack_id = ?
                """,
                (pack_id,),
            )
        except sqlite3.Error as exc:
            self._remember_report(
                RepositoryReadReport.from_collection_error(
                    scope, exc, requested_artifact_id=pack_id
                )
            )
            return ArtifactReadResult(
                artifact_id=pack_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Repository read failed.",
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=pack_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No strategy-pack row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row["pack_id"])
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
                paths.append(self.storage.root / "strategy_packs" / f"{resolved_id}.json")
                result = read_model_from_paths(paths, resolved_id, StrategyPack)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def get(self, pack_id: str) -> StrategyPack | None:
        result = self.get_with_diagnostics(pack_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("strategy_pack_read_report_not_recorded")
        raise RepositoryReadError(report)
