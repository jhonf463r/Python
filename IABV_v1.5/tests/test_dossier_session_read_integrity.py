from __future__ import annotations

import hashlib
import json
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


def test_execution_dossier_missing_payload_is_reported_without_pruning_index(
    tmp_path: Path,
) -> None:
    db, repository = _dossier_repository(tmp_path)
    dossier = repository.save(_dossier("missing-dossier"))
    row = db.fetchone(
        "SELECT path FROM execution_dossiers WHERE dossier_id = ?",
        (dossier.dossier_id,),
    )
    assert row is not None
    Path(row["path"]).unlink()

    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.missing_ids == [dossier.dossier_id]
    assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert db.fetchone(
        "SELECT dossier_id FROM execution_dossiers WHERE dossier_id = ?",
        (dossier.dossier_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_recent()
    assert exc_info.value.report.missing_ids == [dossier.dossier_id]


def test_adaptive_session_partial_read_preserves_valid_items_and_index_rows(
    tmp_path: Path,
) -> None:
    db, repository = _session_repository(tmp_path)
    valid = repository.save(_session("valid-session"))
    corrupt = repository.save(_session("partial-corrupt-session"))
    row = db.fetchone(
        "SELECT path FROM adaptive_sessions WHERE session_id = ?",
        (corrupt.session_id,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_PARTIAL
    assert report.records_seen == 2
    assert report.records_loaded == 1
    assert [item.session_id for item in report.items] == [valid.session_id]
    failed = next(result for result in report.results if result.artifact_id == corrupt.session_id)
    assert failed.status == ArtifactReadStatus.CORRUPT
    assert db.fetchone(
        "SELECT session_id FROM adaptive_sessions WHERE session_id = ?",
        (corrupt.session_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_recent()
    assert len(exc_info.value.report.items) == 1
    assert exc_info.value.report.results == report.results


def test_execution_dossier_point_lookup_found_and_confirmed_absence(
    tmp_path: Path,
) -> None:
    _, repository = _dossier_repository(tmp_path)
    dossier = repository.save(_dossier("point-dossier"))

    found = repository.get_with_diagnostics(dossier.dossier_id)

    assert found.status == ArtifactReadStatus.FOUND
    assert found.value is not None
    assert found.value.dossier_id == dossier.dossier_id
    assert repository.get(dossier.dossier_id) is not None

    missing = repository.get_with_diagnostics("absent-dossier")

    assert missing.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert missing.error_type == "IndexRowNotFound"
    assert repository.get("absent-dossier") is None
    assert repository.last_read_report is not None
    assert repository.last_read_report.results[0].error_type == "IndexRowNotFound"


def test_adaptive_session_pack_filter_and_get_keep_legacy_return_shapes(
    tmp_path: Path,
) -> None:
    _, repository = _session_repository(tmp_path)
    selected = repository.save(
        _session("selected-pack-session").model_copy(
            update={"chosen_pack_id": "pack-selected"}
        )
    )
    repository.save(_session("other-pack-session").model_copy(
        update={"chosen_pack_id": "pack-other"}
    ))

    report = repository.find_by_pack_with_diagnostics("pack-selected")

    assert report.status == RepositoryReadStatus.READ_OK
    assert [item.session_id for item in report.require_complete()] == [selected.session_id]
    loaded = repository.get(selected.session_id)
    assert loaded is not None
    assert loaded.session_id == selected.session_id
    assert repository.get("absent-session") is None


def test_execution_dossier_query_filters_preserve_expected_scope(
    tmp_path: Path,
) -> None:
    _, repository = _dossier_repository(tmp_path)
    target = repository.save(
        ExecutionDossier(
            dossier_id="query-target",
            scope=DossierScope.TEACHING,
            title="Navigation dossier",
            summary="Navigation issue summary",
            run_id="run-target",
            episode_id="episode-target",
            issue_hint_text="navigation_stall",
        )
    )
    repository.save(
        ExecutionDossier(
            dossier_id="query-other",
            scope=DossierScope.TEACHING,
            title="Other dossier",
            summary="Other issue summary",
            run_id="run-other",
            episode_id="episode-other",
            issue_hint_text="other_issue",
        )
    )

    assert [item.dossier_id for item in repository.find_by_run("run-target")] == [
        target.dossier_id
    ]
    assert [item.dossier_id for item in repository.find_by_episode("episode-target")] == [
        target.dossier_id
    ]
    issue_report = repository.find_by_issue_with_diagnostics("navigation_stall")
    assert issue_report.status == RepositoryReadStatus.READ_OK
    assert [item.dossier_id for item in issue_report.items] == [target.dossier_id]



def test_execution_dossier_reindex_plan_is_read_only_and_finds_index_and_file_differences(
    tmp_path: Path,
) -> None:
    db, repository = _dossier_repository(tmp_path)
    indexed = repository.save(_dossier("indexed-dossier"))
    orphaned = _dossier("filesystem-only-dossier")
    unindexed_path = repository.storage.save_json_atomic(
        f"dossiers/{orphaned.dossier_id}.json",
        orphaned.model_dump(mode="json"),
    )
    missing = repository.save(_dossier("index-only-dossier"))
    missing_row = db.fetchone(
        "SELECT path FROM execution_dossiers WHERE dossier_id = ?",
        (missing.dossier_id,),
    )
    assert missing_row is not None
    Path(missing_row["path"]).unlink()
    corrupt_path = Path(repository.storage.save_json_atomic(
        "dossiers/corrupt-dossier.json", {"not": "a dossier"}
    ))
    corrupt_path.write_text("{", encoding="utf-8")
    before_rows = [
        (row["dossier_id"], row["path"])
        for row in db.fetchall(
            "SELECT dossier_id, path FROM execution_dossiers ORDER BY dossier_id"
        )
    ]

    report = repository.plan_reindex_with_diagnostics()

    after_rows = [
        (row["dossier_id"], row["path"])
        for row in db.fetchall(
            "SELECT dossier_id, path FROM execution_dossiers ORDER BY dossier_id"
        )
    ]
    assert report.status.value == "REVIEW_REQUIRED"
    assert indexed.dossier_id in report.indexed_ids
    assert orphaned.dossier_id in report.unindexed_valid_ids
    orphaned_file = next(item for item in report.files if item.artifact_id == orphaned.dossier_id)
    assert orphaned_file.sha256 == hashlib.sha256(Path(unindexed_path).read_bytes()).hexdigest()
    assert orphaned_file.size_bytes == Path(unindexed_path).stat().st_size
    assert missing.dossier_id in report.indexed_without_file_ids
    assert missing.dossier_id in report.index_path_issues
    missing_path_issue = next(
        item for item in report.index_path_results
        if item.artifact_id == missing.dossier_id
    )
    assert missing_path_issue.status.value == "MISSING_PATH"
    assert "corrupt-dossier" in report.invalid_file_ids
    assert before_rows == after_rows
    assert Path(unindexed_path).exists()
    assert report.to_dict()["scope"] == "READ_ONLY_INDEX_RECONCILIATION:execution_dossiers"


def test_adaptive_session_reindex_plan_is_read_only_and_never_returns_payloads(
    tmp_path: Path,
) -> None:
    db, repository = _session_repository(tmp_path)
    indexed = repository.save(_session("indexed-session"))
    orphaned = _session("filesystem-only-session")
    path = repository.storage.save_json_atomic(
        f"adaptive_sessions/{orphaned.session_id}.json",
        orphaned.model_dump(mode="json"),
    )
    before_count = db.fetchone("SELECT COUNT(*) AS total FROM adaptive_sessions")["total"]

    report = repository.plan_reindex_with_diagnostics()

    after_count = db.fetchone("SELECT COUNT(*) AS total FROM adaptive_sessions")["total"]
    assert report.status.value == "REVIEW_REQUIRED"
    assert indexed.session_id in report.indexed_ids
    assert orphaned.session_id in report.unindexed_valid_ids
    assert before_count == after_count == 1
    assert Path(path).exists()
    assert all(not hasattr(item, "value") for item in report.files)


def test_read_only_reindex_plan_reports_database_enumeration_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, repository = _dossier_repository(tmp_path)
    repository.storage.save_json_atomic(
        "dossiers/filesystem-only.json",
        _dossier("filesystem-only").model_dump(mode="json"),
    )

    def fail_fetchall(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "fetchall", fail_fetchall)
    report = repository.plan_reindex_with_diagnostics()

    assert report.status.value == "READ_FAILED"
    assert report.collection_error_type == "OperationalError"
    assert report.unindexed_valid_ids == []


def test_read_only_reindex_plan_reports_missing_managed_directory(
    tmp_path: Path,
) -> None:
    db = AppDatabase(str(tmp_path / "adaptive.sqlite"))
    repository = AdaptiveSessionRepository(
        db, ArtifactStorage(str(tmp_path / "evolution"))
    )

    report = repository.plan_reindex_with_diagnostics()

    assert report.status.value == "DIRECTORY_ABSENT"
    assert report.directory_exists is False
    assert report.files == ()



def test_read_only_reindex_plan_flags_external_sqlite_index_path_without_opening_it(
    tmp_path: Path,
) -> None:
    db, repository = _dossier_repository(tmp_path)
    dossier = repository.save(_dossier("external-index-path"))
    outside = tmp_path.parent / f"{tmp_path.name}_outside.json"
    outside.write_text(dossier.model_dump_json(), encoding="utf-8")
    db.execute(
        "UPDATE execution_dossiers SET path = ? WHERE dossier_id = ?",
        (str(outside), dossier.dossier_id),
    )

    report = repository.plan_reindex_with_diagnostics()

    assert report.status.value == "REVIEW_REQUIRED"
    assert dossier.dossier_id in report.index_path_issues
    issue = next(
        item for item in report.index_path_results
        if item.artifact_id == dossier.dossier_id
    )
    assert issue.status.value == "INVALID_PATH"
    assert outside.read_text(encoding="utf-8") == dossier.model_dump_json()


def test_read_only_reindex_plan_distinguishes_noncanonical_safe_index_paths(
    tmp_path: Path,
) -> None:
    db, repository = _dossier_repository(tmp_path)
    dossier = repository.save(_dossier("noncanonical-index-path"))
    alternate_relative = "legacy/dossiers/noncanonical-index-path.json"
    alternate_path = Path(
        repository.storage.save_json_atomic(
            alternate_relative, dossier.model_dump(mode="json")
        )
    )
    db.execute(
        "UPDATE execution_dossiers SET path = ? WHERE dossier_id = ?",
        (str(alternate_path), dossier.dossier_id),
    )

    report = repository.plan_reindex_with_diagnostics()

    assert dossier.dossier_id in report.index_path_issues
    issue = next(
        item for item in report.index_path_results
        if item.artifact_id == dossier.dossier_id
    )
    assert issue.status.value == "SAFE_NONCANONICAL_PATH"
    assert alternate_path.exists()



def test_reindex_report_does_not_expose_payload_values_from_schema_errors(
    tmp_path: Path,
) -> None:
    db, repository = _dossier_repository(tmp_path)
    dossier = repository.save(_dossier("schema-error-canary"))
    row = db.fetchone(
        "SELECT path FROM execution_dossiers WHERE dossier_id = ?",
        (dossier.dossier_id,),
    )
    assert row is not None
    canary = "PRIVATE_PAYLOAD_CANARY"
    Path(row["path"]).write_text(
        json.dumps({"dossier_id": dossier.dossier_id, "private_value": canary}),
        encoding="utf-8",
    )

    report = repository.plan_reindex_with_diagnostics()

    assert report.status.value == "REVIEW_REQUIRED"
    serialized = repr(report.to_dict())
    assert canary not in serialized
    issue = next(
        item for item in report.index_path_results
        if item.artifact_id == dossier.dossier_id
    )
    assert issue.status.value == "SCHEMA_UNSUPPORTED"
    assert issue.error_message == "Artifact JSON does not match the supported schema."
