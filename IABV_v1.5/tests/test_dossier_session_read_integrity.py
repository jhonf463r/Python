from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    DossierScope,
    ExecutionDossier,
    TaskIntent,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _dossier_repository(tmp_path: Path) -> tuple[AppDatabase, ExecutionDossierRepository]:
    db = AppDatabase(str(tmp_path / "dossier.sqlite"))
    repository = ExecutionDossierRepository(db, ArtifactStorage(str(tmp_path / "dossiers")))
    return db, repository


def _session_repository(tmp_path: Path) -> tuple[AppDatabase, AdaptiveSessionRepository]:
    db = AppDatabase(str(tmp_path / "session.sqlite"))
    repository = AdaptiveSessionRepository(db, ArtifactStorage(str(tmp_path / "sessions")))
    return db, repository


def _dossier(dossier_id: str, *, run_id: str = "run-1") -> ExecutionDossier:
    return ExecutionDossier(
        dossier_id=dossier_id,
        scope=DossierScope.TEACHING,
        title=f"Dossier {dossier_id}",
        summary="Synthetic dossier used by isolated read-integrity tests.",
        run_id=run_id,
    )


def _session(session_id: str, *, run_id: str = "run-1") -> AdaptiveSession:
    return AdaptiveSession(
        session_id=session_id,
        user_goal="Synthetic adaptive-session read-integrity probe",
        intent=TaskIntent(intent_key="general.assistance"),
        run_id=run_id,
        chosen_pack_id="pack-read-integrity",
    )


def test_execution_dossier_partial_read_preserves_valid_items_and_all_index_rows(
    tmp_path: Path,
) -> None:
    db, repository = _dossier_repository(tmp_path)
    valid = repository.save(_dossier("valid-dossier"))
    corrupt = repository.save(_dossier("corrupt-dossier"))
    row = db.fetchone(
        "SELECT path FROM execution_dossiers WHERE dossier_id = ?",
        (corrupt.dossier_id,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_PARTIAL
    assert report.records_seen == 2
    assert report.records_loaded == 1
    assert [item.dossier_id for item in report.items] == [valid.dossier_id]
    failed = next(result for result in report.results if result.artifact_id == corrupt.dossier_id)
    assert failed.status == ArtifactReadStatus.CORRUPT
    assert db.fetchone(
        "SELECT dossier_id FROM execution_dossiers WHERE dossier_id = ?",
        (corrupt.dossier_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_recent()
    assert len(exc_info.value.report.items) == 1
    assert exc_info.value.report.results == report.results


def test_adaptive_session_missing_payload_is_reported_without_pruning_index(
    tmp_path: Path,
) -> None:
    db, repository = _session_repository(tmp_path)
    session = repository.save(_session("missing-session"))
    row = db.fetchone(
        "SELECT path FROM adaptive_sessions WHERE session_id = ?",
        (session.session_id,),
    )
    assert row is not None
    Path(row["path"]).unlink()

    report = repository.find_by_run_with_diagnostics("run-1")

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.records_seen == 1
    assert report.records_loaded == 0
    assert report.missing_ids == [session.session_id]
    assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert db.fetchone(
        "SELECT session_id FROM adaptive_sessions WHERE session_id = ?",
        (session.session_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.find_by_run("run-1")
    assert exc_info.value.report.missing_ids == [session.session_id]


def test_execution_dossier_permission_failure_is_not_reported_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, repository = _dossier_repository(tmp_path)
    dossier = repository.save(_dossier("permission-dossier"))
    row = db.fetchone(
        "SELECT path FROM execution_dossiers WHERE dossier_id = ?",
        (dossier.dossier_id,),
    )
    assert row is not None
    target = Path(row["path"])
    original_read_text = Path.read_text

    def fail_target(self: Path, *args, **kwargs):
        if self == target:
            raise PermissionError("simulated denied dossier read")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_target)
    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.results[0].status == ArtifactReadStatus.READ_FAILED
    assert report.results[0].error_type == "PermissionError"
    assert db.fetchone(
        "SELECT dossier_id FROM execution_dossiers WHERE dossier_id = ?",
        (dossier.dossier_id,),
    ) is not None


def test_adaptive_session_corrupt_payload_is_not_pruned_and_point_read_fails_closed(
    tmp_path: Path,
) -> None:
    db, repository = _session_repository(tmp_path)
    session = repository.save(_session("corrupt-session"))
    row = db.fetchone(
        "SELECT path FROM adaptive_sessions WHERE session_id = ?",
        (session.session_id,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    result = repository.get_with_diagnostics(session.session_id)

    assert result.status == ArtifactReadStatus.CORRUPT
    assert repository.last_read_report is not None
    assert repository.last_read_report.status == RepositoryReadStatus.READ_FAILED
    assert db.fetchone(
        "SELECT session_id FROM adaptive_sessions WHERE session_id = ?",
        (session.session_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.get(session.session_id)
    assert exc_info.value.report.results[0].status == ArtifactReadStatus.CORRUPT


def test_dossier_and_adaptive_point_lookup_sqlite_errors_replace_stale_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dossier_db, dossier_repo = _dossier_repository(tmp_path / "dossier")
    session_db, session_repo = _session_repository(tmp_path / "session")
    assert dossier_repo.list_recent_with_diagnostics().status == RepositoryReadStatus.NO_RECORDS_OBSERVED
    assert session_repo.list_recent_with_diagnostics().status == RepositoryReadStatus.NO_RECORDS_OBSERVED

    def fail_fetchone(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(dossier_db, "fetchone", fail_fetchone)
    monkeypatch.setattr(session_db, "fetchone", fail_fetchone)

    dossier_result = dossier_repo.get_with_diagnostics("requested-dossier")
    session_result = session_repo.get_with_diagnostics("requested-session")

    assert dossier_result.status == ArtifactReadStatus.READ_FAILED
    assert session_result.status == ArtifactReadStatus.READ_FAILED
    assert dossier_repo.last_read_report is not None
    assert session_repo.last_read_report is not None
    assert dossier_repo.last_read_report.requested_artifact_id == "requested-dossier"
    assert session_repo.last_read_report.requested_artifact_id == "requested-session"
    assert dossier_repo.last_read_report.collection_error_type == "OperationalError"
    assert session_repo.last_read_report.collection_error_type == "OperationalError"
    with pytest.raises(RepositoryReadError):
        dossier_repo.get("requested-dossier")
    with pytest.raises(RepositoryReadError):
        session_repo.get("requested-session")


def test_dossier_and_adaptive_collection_sqlite_errors_replace_stale_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dossier_db, dossier_repo = _dossier_repository(tmp_path / "dossier")
    session_db, session_repo = _session_repository(tmp_path / "session")
    previous_dossier = dossier_repo.list_recent_with_diagnostics()
    previous_session = session_repo.list_recent_with_diagnostics()
    assert previous_dossier.status == RepositoryReadStatus.NO_RECORDS_OBSERVED
    assert previous_session.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

    def fail_fetchall(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(dossier_db, "fetchall", fail_fetchall)
    monkeypatch.setattr(session_db, "fetchall", fail_fetchall)

    dossier_report = dossier_repo.list_recent_with_diagnostics()
    session_report = session_repo.list_recent_with_diagnostics()

    assert dossier_report.status == RepositoryReadStatus.READ_FAILED
    assert session_report.status == RepositoryReadStatus.READ_FAILED
    assert dossier_report.collection_error_type == "OperationalError"
    assert session_report.collection_error_type == "OperationalError"
    assert dossier_repo.last_read_report is dossier_report
    assert session_repo.last_read_report is session_report
    assert dossier_report is not previous_dossier
    assert session_report is not previous_session


def test_empty_dossier_issue_query_is_explicitly_not_executed_and_legacy_noop_is_preserved(
    tmp_path: Path,
) -> None:
    _, repository = _dossier_repository(tmp_path)

    report = repository.find_by_issue_with_diagnostics("   ")

    assert report.status == RepositoryReadStatus.QUERY_NOT_EXECUTED
    assert repository.last_read_report is report
    assert repository.find_by_issue("") == []
    assert repository.last_read_report is not None
    assert repository.last_read_report.status == RepositoryReadStatus.QUERY_NOT_EXECUTED
