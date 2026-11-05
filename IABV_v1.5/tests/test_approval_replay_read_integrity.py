from __future__ import annotations

from pathlib import Path

import pytest

from iabv_v15.domain.models import ApprovalCheckpoint, ReplayAnnotation
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.replay_annotation_repository import ReplayAnnotationRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _approval_repository(tmp_path: Path) -> tuple[AppDatabase, ApprovalCheckpointRepository]:
    db = AppDatabase(str(tmp_path / "approval.sqlite"))
    repository = ApprovalCheckpointRepository(db, ArtifactStorage(str(tmp_path / "approval-storage")))
    return db, repository


def _replay_repository(tmp_path: Path) -> tuple[AppDatabase, ReplayAnnotationRepository]:
    db = AppDatabase(str(tmp_path / "replay.sqlite"))
    repository = ReplayAnnotationRepository(db, ArtifactStorage(str(tmp_path / "replay-storage")))
    return db, repository


def _checkpoint(checkpoint_id: str, session_id: str = "session-a") -> ApprovalCheckpoint:
    return ApprovalCheckpoint(
        checkpoint_id=checkpoint_id,
        session_id=session_id,
        title=f"Approval {checkpoint_id}",
        detail="Synthetic approval checkpoint for read-integrity regression.",
    )


def _annotation(annotation_id: str, episode_id: str = "episode-a") -> ReplayAnnotation:
    return ReplayAnnotation(
        annotation_id=annotation_id,
        episode_id=episode_id,
        step_id="step-a",
        screenshot_path="screen.png",
        group_key="group-a",
    )


def test_approval_checkpoint_partial_read_preserves_valid_items_and_index_rows(
    tmp_path: Path,
) -> None:
    db, repository = _approval_repository(tmp_path)
    valid = repository.save(_checkpoint("valid-checkpoint"))
    corrupt = repository.save(_checkpoint("corrupt-checkpoint"))
    row = db.fetchone(
        "SELECT path FROM approval_checkpoints WHERE checkpoint_id = ?",
        (corrupt.checkpoint_id,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    report = repository.list_for_session_with_diagnostics("session-a")

    assert report.status == RepositoryReadStatus.READ_PARTIAL
    assert report.records_seen == 2
    assert report.records_loaded == 1
    assert [item.checkpoint_id for item in report.items] == [valid.checkpoint_id]
    assert db.fetchone(
        "SELECT checkpoint_id FROM approval_checkpoints WHERE checkpoint_id = ?",
        (corrupt.checkpoint_id,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_for_session("session-a")
    assert len(exc_info.value.report.items) == 1


def test_approval_checkpoint_point_lookup_reports_found_and_confirmed_absence(
    tmp_path: Path,
) -> None:
    _, repository = _approval_repository(tmp_path)
    checkpoint = repository.save(_checkpoint("point-checkpoint"))

    found = repository.get_with_diagnostics(checkpoint.checkpoint_id)
    assert found.status == ArtifactReadStatus.FOUND
    assert found.value is not None
    assert repository.get(checkpoint.checkpoint_id) is not None

    missing = repository.get_with_diagnostics("absent-checkpoint")
    assert missing.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert missing.error_type == "IndexRowNotFound"
    assert repository.get("absent-checkpoint") is None


def test_replay_annotation_missing_payload_is_reported_without_pruning_index(
    tmp_path: Path,
) -> None:
    db, repository = _replay_repository(tmp_path)
    annotation = repository.save(_annotation("missing-annotation"))
    row = db.fetchone(
        "SELECT path FROM replay_annotations WHERE annotation_id = ?",
        (annotation.annotation_id,),
    )
    assert row is not None
    Path(row["path"]).unlink()

    report = repository.list_for_episode_with_diagnostics("episode-a")

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.missing_ids == [annotation.annotation_id]
    assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert db.fetchone(
        "SELECT annotation_id FROM replay_annotations WHERE annotation_id = ?",
        (annotation.annotation_id,),
    ) is not None
    with pytest.raises(RepositoryReadError):
        repository.list_for_episode("episode-a")


def test_replay_annotation_corrupt_read_does_not_authorize_explicit_delete(
    tmp_path: Path,
) -> None:
    db, repository = _replay_repository(tmp_path)
    annotation = repository.save(_annotation("corrupt-annotation"))
    row = db.fetchone(
        "SELECT path FROM replay_annotations WHERE annotation_id = ?",
        (annotation.annotation_id,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    with pytest.raises(RepositoryReadError) as exc_info:
        repository.delete(annotation.annotation_id)

    assert exc_info.value.report.results[0].status == ArtifactReadStatus.CORRUPT
    assert db.fetchone(
        "SELECT annotation_id FROM replay_annotations WHERE annotation_id = ?",
        (annotation.annotation_id,),
    ) is not None
    assert Path(row["path"]).exists()


def test_replay_annotation_explicit_delete_removes_only_a_confirmed_read(
    tmp_path: Path,
) -> None:
    db, repository = _replay_repository(tmp_path)
    annotation = repository.save(_annotation("valid-delete-annotation"))
    row = db.fetchone(
        "SELECT path FROM replay_annotations WHERE annotation_id = ?",
        (annotation.annotation_id,),
    )
    assert row is not None
    artifact_path = Path(row["path"])
    assert artifact_path.exists()

    repository.delete(annotation.annotation_id)

    assert not artifact_path.exists()
    assert db.fetchone(
        "SELECT annotation_id FROM replay_annotations WHERE annotation_id = ?",
        (annotation.annotation_id,),
    ) is None


def test_approval_and_replay_sqlite_collection_failures_replace_stale_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    approval_db, approval_repo = _approval_repository(tmp_path / "approval")
    replay_db, replay_repo = _replay_repository(tmp_path / "replay")
    previous_approval = approval_repo.list_for_session_with_diagnostics("session-a")
    previous_replay = replay_repo.list_for_episode_with_diagnostics("episode-a")
    assert previous_approval.status == RepositoryReadStatus.NO_RECORDS_OBSERVED
    assert previous_replay.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

    def fail_fetchall(*args, **kwargs):
        raise __import__("sqlite3").OperationalError("database is locked")

    monkeypatch.setattr(approval_db, "fetchall", fail_fetchall)
    monkeypatch.setattr(replay_db, "fetchall", fail_fetchall)
    approval_report = approval_repo.list_for_session_with_diagnostics("session-a")
    replay_report = replay_repo.find_by_step_with_diagnostics("step-a")

    assert approval_report.status == RepositoryReadStatus.READ_FAILED
    assert replay_report.status == RepositoryReadStatus.READ_FAILED
    assert approval_repo.last_read_report is approval_report
    assert replay_repo.last_read_report is replay_report
    assert approval_report is not previous_approval
    assert replay_report is not previous_replay
