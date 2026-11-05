from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    DossierScope,
    ScenarioDefinition,
    ScenarioRun,
    StrategyPack,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository


def _scenario_repository(tmp_path: Path) -> tuple[AppDatabase, ScenarioRunRepository]:
    db = AppDatabase(str(tmp_path / "scenario.sqlite"))
    repository = ScenarioRunRepository(db, ArtifactStorage(str(tmp_path / "scenario-storage")))
    return db, repository


def _strategy_repository(tmp_path: Path) -> tuple[AppDatabase, StrategyPackRepository]:
    db = AppDatabase(str(tmp_path / "strategy.sqlite"))
    repository = StrategyPackRepository(db, ArtifactStorage(str(tmp_path / "strategy-storage")))
    return db, repository


def _scenario_run(scenario_run_id: str, *, run_id: str = "run-a") -> ScenarioRun:
    return ScenarioRun(
        scenario_run_id=scenario_run_id,
        scenario=ScenarioDefinition(scenario_id="scenario-a", title="Read integrity scenario"),
        goal="Verify non-destructive scenario persistence reads.",
        run_id=run_id,
    )


def _strategy_pack(pack_id: str) -> StrategyPack:
    return StrategyPack(
        pack_id=pack_id,
        title=f"Strategy {pack_id}",
        domain_kind="read-integrity",
    )


def test_scenario_run_partial_read_preserves_valid_items_and_index_rows(
    tmp_path: Path,
) -> None:
    db, repository = _scenario_repository(tmp_path)
    valid = repository.save(_scenario_run("scenario-valid"))
    corrupt = repository.save(_scenario_run("scenario-corrupt"))
    row = db.fetchone(
        "SELECT path FROM scenario_runs WHERE scenario_run_id = ?",
        (corrupt.scenario_run_id,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_PARTIAL
    assert report.records_seen == 2
    assert report.records_loaded == 1
    assert [item.scenario_run_id for item in report.items] == [valid.scenario_run_id]
    assert db.fetchone(
        "SELECT scenario_run_id FROM scenario_runs WHERE scenario_run_id = ?",
        (corrupt.scenario_run_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_recent()
    assert len(exc_info.value.report.items) == 1


def test_strategy_pack_missing_payload_is_reported_without_pruning_index(
    tmp_path: Path,
) -> None:
    db, repository = _strategy_repository(tmp_path)
    pack = repository.save(_strategy_pack("missing-pack"))
    row = db.fetchone(
        "SELECT path FROM strategy_packs WHERE pack_id = ?",
        (pack.pack_id,),
    )
    assert row is not None
    Path(row["path"]).unlink()

    report = repository.list_all_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.missing_ids == [pack.pack_id]
    assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert db.fetchone(
        "SELECT pack_id FROM strategy_packs WHERE pack_id = ?",
        (pack.pack_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_all()
    assert exc_info.value.report.missing_ids == [pack.pack_id]


def test_scenario_run_sqlite_fetchall_failure_replaces_stale_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, repository = _scenario_repository(tmp_path)
    previous = repository.list_recent_with_diagnostics()
    assert previous.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

    def fail_fetchall(*args, **kwargs):
        raise sqlite3.OperationalError("PRIVATE_DB_ERROR_CANARY")

    monkeypatch.setattr(db, "fetchall", fail_fetchall)
    report = repository.find_by_run_with_diagnostics("run-a")

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.collection_error_type == "OperationalError"
    assert report.collection_error_message == "Repository read failed."
    assert "PRIVATE_DB_ERROR_CANARY" not in str(report.to_dict())
    assert repository.last_read_report is report
    assert report is not previous
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.find_by_run("run-a")
    assert exc_info.value.report.collection_error_type == "OperationalError"


def test_strategy_pack_point_lookup_sqlite_failure_replaces_stale_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, repository = _strategy_repository(tmp_path)
    repository.list_all_with_diagnostics()
    previous = repository.last_read_report

    def fail_fetchone(*args, **kwargs):
        raise sqlite3.OperationalError("PRIVATE_DB_ERROR_CANARY")

    monkeypatch.setattr(db, "fetchone", fail_fetchone)
    result = repository.get_with_diagnostics("requested-pack")

    assert result.status == ArtifactReadStatus.READ_FAILED
    assert result.error_message == "Repository read failed."
    assert repository.last_read_report is not None
    assert repository.last_read_report.requested_artifact_id == "requested-pack"
    assert repository.last_read_report is not previous
    with pytest.raises(RepositoryReadError):
        repository.get("requested-pack")


def test_scenario_run_point_lookup_reports_found_and_confirmed_absence(
    tmp_path: Path,
) -> None:
    _, repository = _scenario_repository(tmp_path)
    scenario = repository.save(_scenario_run("point-scenario"))

    found = repository.get_with_diagnostics(scenario.scenario_run_id)
    assert found.status == ArtifactReadStatus.FOUND
    assert found.value is not None
    assert repository.get(scenario.scenario_run_id) is not None

    missing = repository.get_with_diagnostics("absent-scenario-run")
    assert missing.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert missing.error_type == "IndexRowNotFound"
    assert repository.get("absent-scenario-run") is None


def test_strategy_pack_list_and_get_keep_legacy_success_shapes(tmp_path: Path) -> None:
    _, repository = _strategy_repository(tmp_path)
    pack = repository.save(_strategy_pack("listed-pack"))

    report = repository.list_all_with_diagnostics()
    assert report.status == RepositoryReadStatus.READ_OK
    assert [item.pack_id for item in report.require_complete()] == [pack.pack_id]

    loaded = repository.get(pack.pack_id)
    assert loaded is not None
    assert loaded.pack_id == pack.pack_id
    assert repository.get("absent-pack") is None
