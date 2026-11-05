from __future__ import annotations

import pytest

from iabv_v15.domain.models import SelfExaminationSnapshot
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
    _REQUIRED_SOURCE_IDS,
    _SOURCE_COVERAGE_CONTRACT,
)


def _service(tmp_path, **kwargs):
    return OperationalSelfExaminationService(
        workspace_root=str(tmp_path),
        storage=ArtifactStorage(str(tmp_path / "evolution")),
        **kwargs,
    )


def _complete_coverage() -> dict[str, str]:
    return {source: "READ_OK" for source in _REQUIRED_SOURCE_IDS}


def _cached_snapshot(**coverage_overrides) -> SelfExaminationSnapshot:
    coverage = _complete_coverage()
    coverage.update(coverage_overrides)
    return SelfExaminationSnapshot(
        source_coverage=coverage,
        metadata={
            "source_coverage_contract": _SOURCE_COVERAGE_CONTRACT,
            "required_source_ids": list(_REQUIRED_SOURCE_IDS),
            "source_coverage": dict(coverage),
            "source_errors": {},
        },
    )


def test_oses_recent_run_reader_records_read_failure(tmp_path) -> None:
    class BrokenRunRepository:
        def list_recent(self, limit=60):
            raise PermissionError("synthetic repository read failure")

    service = _service(tmp_path, run_repository=BrokenRunRepository())

    assert service._recent_runs() == []
    assert service._source_coverage["run_repository"] == "READ_FAILED"
    assert service._source_errors["run_repository"] == "PermissionError"


def test_oses_unconfigured_reader_is_not_reported_as_verified_empty(tmp_path) -> None:
    service = _service(tmp_path)

    assert service._recent_adaptive_sessions() == []
    assert service._source_coverage["adaptive_session_repository"] == "NOT_CONFIGURED"


def test_oses_cached_review_does_not_trigger_active_rebuild(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _cached_snapshot()
    service._current_review = snapshot
    service._is_fresh = lambda review, *, max_age_seconds: review is snapshot
    service.build_review = lambda: (_ for _ in ()).throw(
        AssertionError("cached review read must not trigger build_review")
    )

    assert service.current_review_cached() is snapshot


def test_oses_cached_review_rejects_stale_snapshot_without_rebuild(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _cached_snapshot()
    service._current_review = snapshot
    service._is_fresh = lambda review, *, max_age_seconds: False
    service.build_review = lambda: (_ for _ in ()).throw(
        AssertionError("stale cache must not trigger build_review")
    )

    with pytest.raises(RuntimeError, match="oses_cached_review_stale"):
        service.current_review_cached()


def test_oses_cached_review_rejects_incomplete_source_coverage(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _cached_snapshot(
        adaptive_session_repository="READ_FAILED",
    )
    service._current_review = snapshot
    service._is_fresh = lambda review, *, max_age_seconds: True
    service.build_review = lambda: (_ for _ in ()).throw(
        AssertionError("incomplete cache must not trigger build_review")
    )

    with pytest.raises(RuntimeError, match="oses_source_coverage_incomplete"):
        service.current_review_cached()



def test_oses_cached_review_rejects_one_source_claimed_as_complete(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = SelfExaminationSnapshot(
        source_coverage={"run_repository": "READ_OK"},
        metadata={
            "source_coverage_contract": _SOURCE_COVERAGE_CONTRACT,
            "required_source_ids": list(_REQUIRED_SOURCE_IDS),
        },
    )
    service._current_review = snapshot
    service._is_fresh = lambda review, *, max_age_seconds: True

    with pytest.raises(RuntimeError, match="oses_source_coverage_missing"):
        service.current_review_cached()


def test_oses_source_coverage_report_marks_uninstrumented_sources_explicitly(tmp_path) -> None:
    service = _service(tmp_path)
    service._source_coverage = {
        "run_repository": "READ_OK",
        "adaptive_session_repository": "READ_FAILED",
    }

    report = service._source_coverage_report()

    assert report["contract"] == _SOURCE_COVERAGE_CONTRACT
    assert set(report["required_source_ids"]) == set(_REQUIRED_SOURCE_IDS)
    assert report["source_coverage"]["run_repository"] == "READ_OK"
    assert report["source_coverage"]["adaptive_session_repository"] == "READ_FAILED"
    assert report["source_coverage"]["runtime_audit_log"] == "NOT_INSTRUMENTED"
    assert report["complete"] is False
    assert "runtime_audit_log" in report["incomplete_source_ids"]


def test_oses_source_status_does_not_erase_failure_with_later_success(tmp_path) -> None:
    service = _service(tmp_path)
    service._source_coverage = {"runtime_audit_tracer": "NOT_INSTRUMENTED"}

    service._record_source_status("runtime_audit_tracer", "READ_FAILED", "OSError")
    service._record_source_status("runtime_audit_tracer", "READ_OK")

    assert service._source_coverage["runtime_audit_tracer"] == "READ_FAILED"
    assert service._source_errors["runtime_audit_tracer"] == "OSError"
