from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from iabv_v15.domain.models import CodexPendingIssue
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _repository(root: Path) -> tuple[AppDatabase, PendingIssueRepository]:
    db = AppDatabase(str(root / "app.sqlite"))
    storage = ArtifactStorage(str(root / "evolution"))
    return db, PendingIssueRepository(db, storage)


def _seed_issue(repository: PendingIssueRepository) -> CodexPendingIssue:
    return repository.save(
        CodexPendingIssue(
            summary="Pending issue read-integrity probe",
            run_id="run-read-integrity",
            scenario_id="scenario-read-integrity",
        )
    )


def _indexed_path(db: AppDatabase, issue_id: str) -> Path:
    row = db.fetchone(
        "SELECT path FROM codex_pending_issues WHERE issue_id = ?",
        (issue_id,),
    )
    assert row is not None
    return Path(row["path"])


def _index_row_exists(db: AppDatabase, issue_id: str) -> bool:
    return db.fetchone(
        "SELECT issue_id FROM codex_pending_issues WHERE issue_id = ?",
        (issue_id,),
    ) is not None


def test_pending_issue_roundtrip_reports_all_indexed_rows_read() -> None:
    with tempfile.TemporaryDirectory(prefix="pending_issue_repo_") as directory:
        root = Path(directory)
        db, repository = _repository(root)
        issue = _seed_issue(repository)

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_OK
        assert report.scope == "SQLITE_INDEX_ROWS"
        assert report.records_seen == 1
        assert report.records_loaded == 1
        assert report.items[0].issue_id == issue.issue_id


def test_missing_pending_issue_payload_is_reported_and_index_row_is_preserved() -> None:
    with tempfile.TemporaryDirectory(prefix="pending_issue_missing_") as directory:
        root = Path(directory)
        db, repository = _repository(root)
        issue = _seed_issue(repository)
        _indexed_path(db, issue.issue_id).unlink()

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.missing_ids == [issue.issue_id]
        assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
        assert _index_row_exists(db, issue.issue_id)
        with pytest.raises(RepositoryReadError):
            repository.list_recent()


def test_corrupt_pending_issue_payload_is_reported_without_index_prune() -> None:
    with tempfile.TemporaryDirectory(prefix="pending_issue_corrupt_") as directory:
        root = Path(directory)
        db, repository = _repository(root)
        issue = _seed_issue(repository)
        _indexed_path(db, issue.issue_id).write_text("{", encoding="utf-8")

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.results[0].status == ArtifactReadStatus.CORRUPT
        assert report.failed_ids == [issue.issue_id]
        assert _index_row_exists(db, issue.issue_id)


def test_pending_issue_permission_failure_is_not_treated_as_missing(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(prefix="pending_issue_io_") as directory:
        root = Path(directory)
        db, repository = _repository(root)
        issue = _seed_issue(repository)
        artifact_path = _indexed_path(db, issue.issue_id)
        original_read_text = Path.read_text

        def fail_target_read(self, *args, **kwargs):
            if self == artifact_path:
                raise PermissionError("simulated denied read")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fail_target_read)
        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.results[0].status == ArtifactReadStatus.READ_FAILED
        assert report.results[0].error_type == "PermissionError"
        assert _index_row_exists(db, issue.issue_id)
