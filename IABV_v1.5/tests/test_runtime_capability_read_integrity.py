from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from iabv_v15.domain.models import CapabilityReadiness, RuntimeAdjustment, RuntimeTuningProfile
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.runtime_tuning_repository import RuntimeTuningRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _runtime_repository(tmp_path: Path) -> tuple[AppDatabase, RuntimeTuningRepository]:
    db = AppDatabase(str(tmp_path / "runtime.sqlite"))
    repository = RuntimeTuningRepository(db, ArtifactStorage(str(tmp_path / "runtime-storage")))
    return db, repository


def _capability_repository(tmp_path: Path) -> tuple[AppDatabase, CapabilityRepository]:
    db = AppDatabase(str(tmp_path / "capability.sqlite"))
    repository = CapabilityRepository(db, ArtifactStorage(str(tmp_path / "capability-storage")))
    return db, repository


def _runtime_profile(scope_key: str) -> RuntimeTuningProfile:
    return RuntimeTuningProfile(scope_key=scope_key)


def _capability(capability_id: str, *, site_id: str | None = None) -> CapabilityReadiness:
    return CapabilityReadiness(
        capability_id=capability_id,
        title=f"Capability {capability_id}",
        site_id=site_id,
    )


def test_runtime_tuning_partial_read_preserves_valid_profiles_and_index_rows(
    tmp_path: Path,
) -> None:
    db, repository = _runtime_repository(tmp_path)
    valid = repository.save(_runtime_profile("valid-scope"))
    corrupt = repository.save(_runtime_profile("corrupt-scope"))
    row = db.fetchone(
        "SELECT path FROM runtime_tuning_profiles WHERE scope_key = ?",
        (corrupt.scope_key,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_PARTIAL
    assert report.records_seen == 2
    assert report.records_loaded == 1
    assert [item.scope_key for item in report.items] == [valid.scope_key]
    assert db.fetchone(
        "SELECT scope_key FROM runtime_tuning_profiles WHERE scope_key = ?",
        (corrupt.scope_key,),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.list_recent()
    assert len(exc_info.value.report.items) == 1


def test_capability_missing_payload_is_reported_without_pruning_index(
    tmp_path: Path,
) -> None:
    db, repository = _capability_repository(tmp_path)
    capability = repository.save(_capability("missing-capability", site_id="site-a"))
    row = db.fetchone(
        "SELECT path FROM capability_snapshots WHERE capability_key = ?",
        ("site-a__missing-capability",),
    )
    assert row is not None
    Path(row["path"]).unlink()

    report = repository.find_by_site_with_diagnostics("site-a")

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.missing_ids == ["site-a__missing-capability"]
    assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
    assert db.fetchone(
        "SELECT capability_key FROM capability_snapshots WHERE capability_key = ?",
        ("site-a__missing-capability",),
    ) is not None
    with pytest.raises(RepositoryReadError) as exc_info:
        repository.find_by_site("site-a")
    assert exc_info.value.report.missing_ids == ["site-a__missing-capability"]


def test_runtime_tuning_fetchall_failure_replaces_stale_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, repository = _runtime_repository(tmp_path)
    previous = repository.list_recent_with_diagnostics()
    assert previous.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

    def fail_fetchall(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "fetchall", fail_fetchall)
    report = repository.list_recent_with_diagnostics()

    assert report.status == RepositoryReadStatus.READ_FAILED
    assert report.collection_error_type == "OperationalError"
    assert repository.last_read_report is report
    assert report is not previous
    with pytest.raises(RepositoryReadError):
        repository.list_recent()


def test_capability_point_lookup_failure_replaces_stale_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, repository = _capability_repository(tmp_path)
    repository.list_recent_with_diagnostics()
    previous = repository.last_read_report

    def fail_fetchone(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "fetchone", fail_fetchone)
    result = repository.get_with_diagnostics("requested-capability", site_id="site-a")

    assert result.status == ArtifactReadStatus.READ_FAILED
    assert repository.last_read_report is not None
    assert repository.last_read_report.requested_artifact_id == "site-a__requested-capability"
    assert repository.last_read_report is not previous
    with pytest.raises(RepositoryReadError):
        repository.get("requested-capability", site_id="site-a")


def test_runtime_and_capability_getters_preserve_found_and_absent_semantics(
    tmp_path: Path,
) -> None:
    _, runtime_repo = _runtime_repository(tmp_path / "runtime")
    _, capability_repo = _capability_repository(tmp_path / "capability")
    profile = runtime_repo.save(_runtime_profile("global"))
    capability = capability_repo.save(_capability("capability-a", site_id="site-a"))

    runtime_result = runtime_repo.get_with_diagnostics("global")
    capability_result = capability_repo.get_with_diagnostics("capability-a", site_id="site-a")

    assert runtime_result.status == ArtifactReadStatus.FOUND
    assert capability_result.status == ArtifactReadStatus.FOUND
    assert runtime_repo.get("global") is not None
    assert capability_repo.get("capability-a", site_id="site-a") is not None
    assert runtime_repo.get("missing-scope") is None
    assert capability_repo.get("missing-capability", site_id="site-a") is None
    assert profile.scope_key == "global"
    assert capability.capability_id == "capability-a"


def test_runtime_tuning_append_adjustment_fails_closed_on_corrupt_existing_profile(
    tmp_path: Path,
) -> None:
    db, repository = _runtime_repository(tmp_path)
    profile = repository.save(_runtime_profile("global"))
    row = db.fetchone(
        "SELECT path FROM runtime_tuning_profiles WHERE scope_key = ?",
        (profile.scope_key,),
    )
    assert row is not None
    Path(row["path"]).write_text("{", encoding="utf-8")

    with pytest.raises(RepositoryReadError) as exc_info:
        repository.append_adjustment(
            RuntimeAdjustment(target_key="confidence_threshold", reason="synthetic regression")
        )

    assert exc_info.value.report.status == RepositoryReadStatus.READ_FAILED
    assert db.fetchone(
        "SELECT scope_key FROM runtime_tuning_profiles WHERE scope_key = ?",
        ("global",),
    ) is not None
