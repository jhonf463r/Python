from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from iabv_v15.domain.models import SelfExaminationSnapshot
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
    _REQUIRED_SOURCE_IDS,
    _SOURCE_COVERAGE_CONTRACT,
)
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _service(tmp_path: Path, **kwargs) -> OperationalSelfExaminationService:
    return OperationalSelfExaminationService(
        workspace_root=str(tmp_path),
        storage=ArtifactStorage(str(tmp_path / "evolution")),
        **kwargs,
    )


def _complete_snapshot(**overrides) -> SelfExaminationSnapshot:
    coverage = {source: "READ_OK" for source in _REQUIRED_SOURCE_IDS}
    coverage.update(overrides)
    errors: dict[str, str] = {}
    return SelfExaminationSnapshot(
        source_coverage=coverage,
        source_errors=errors,
        metadata={
            "source_coverage_contract": _SOURCE_COVERAGE_CONTRACT,
            "required_source_ids": list(_REQUIRED_SOURCE_IDS),
            "source_coverage": dict(coverage),
            "source_errors": dict(errors),
        },
    )


def test_oses_coverage_contract_has_unique_explicit_source_ids() -> None:
    assert _SOURCE_COVERAGE_CONTRACT == "OSES_SOURCE_COVERAGE_R1"
    assert len(_REQUIRED_SOURCE_IDS) == 31
    assert len(set(_REQUIRED_SOURCE_IDS)) == len(_REQUIRED_SOURCE_IDS)


def test_oses_coverage_report_does_not_infer_read_ok_from_uninstrumented_sources(tmp_path) -> None:
    service = _service(tmp_path)
    report = service._source_coverage_report()
    assert set(report["required_source_ids"]) == set(_REQUIRED_SOURCE_IDS)
    assert set(report["source_coverage"].values()) == {"NOT_INSTRUMENTED"}
    assert report["complete"] is False
    assert report["incomplete_source_ids"] == list(_REQUIRED_SOURCE_IDS)


def test_oses_source_status_does_not_erase_failure_with_later_success(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_source_status("run_repository", "READ_FAILED", "PermissionError")
    service._record_source_status("run_repository", "READ_OK")
    assert service._source_coverage["run_repository"] == "READ_FAILED"
    assert service._source_errors["run_repository"] == "PermissionError"


def test_oses_source_status_allows_initial_not_instrumented_state_to_be_replaced(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_source_status("run_repository", "NOT_INSTRUMENTED")
    service._record_source_status("run_repository", "READ_OK")
    assert service._source_coverage["run_repository"] == "READ_OK"
    assert "run_repository" not in service._source_errors


def test_cached_oses_review_returns_fresh_complete_snapshot_without_rebuild(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    service._current_review = snapshot
    service.build_review = lambda: (_ for _ in ()).throw(
        AssertionError("cached reader must not rebuild or persist a review")
    )
    assert service.current_review_cached() is snapshot


def test_cached_oses_review_loads_persisted_snapshot_without_rebuilding(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    service.storage.save_json_atomic(
        "self_examination/latest.json", snapshot.model_dump(mode="json")
    )
    service._current_review = None
    service.build_review = lambda: (_ for _ in ()).throw(
        AssertionError("cache read must not call build_review")
    )
    loaded = service.current_review_cached()
    assert loaded.review_id == snapshot.review_id
    assert loaded.source_coverage == snapshot.source_coverage


def test_cached_oses_review_rejects_stale_snapshot_without_rebuilding(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot().model_copy(
        update={"updated_at_utc": datetime.now(timezone.utc) - timedelta(seconds=301)}
    )
    service._current_review = snapshot
    service.build_review = lambda: (_ for _ in ()).throw(
        AssertionError("stale cache must not trigger a rebuild")
    )
    with pytest.raises(RuntimeError, match="oses_cached_review_stale"):
        service.current_review_cached()


@pytest.mark.parametrize(
    "metadata_change,coverage_change,error",
    [
        ({"source_coverage_contract": "OTHER"}, None, "oses_source_coverage_contract_unverified"),
        ({"required_source_ids": []}, None, "oses_source_coverage_contract_mismatch"),
        (None, {"run_repository": "READ_PARTIAL"}, "oses_source_coverage_incomplete"),
        (None, {"not_a_required_source": "READ_OK"}, "oses_source_coverage_missing"),
    ],
)
def test_cached_oses_review_rejects_contract_or_coverage_mismatch(
    tmp_path, metadata_change, coverage_change, error
) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot(**(coverage_change or {}))
    if metadata_change:
        snapshot.metadata = {**snapshot.metadata, **metadata_change}
    service._current_review = snapshot
    with pytest.raises(RuntimeError, match=error):
        service.current_review_cached()


def test_cached_oses_review_rejects_residual_source_errors_even_when_statuses_are_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    snapshot.source_errors = {"run_repository": "PermissionError"}
    snapshot.metadata = {**snapshot.metadata, "source_errors": dict(snapshot.source_errors)}
    service._current_review = snapshot
    with pytest.raises(RuntimeError, match="oses_source_coverage_incomplete"):
        service.current_review_cached()


def test_legacy_snapshot_deserializes_but_remains_unverified(tmp_path) -> None:
    service = _service(tmp_path)
    legacy = SelfExaminationSnapshot.model_validate({"summary": "historical snapshot"})
    service._current_review = legacy
    assert legacy.source_coverage == {}
    assert legacy.source_errors == {}
    with pytest.raises(RuntimeError, match="oses_source_coverage_contract_unverified"):
        service.current_review_cached()


def test_oses_persists_typed_coverage_in_latest_and_immutable_archive(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    service._source_coverage = dict(snapshot.source_coverage)
    service._source_errors = {}
    persisted = service._persist_review(snapshot)
    latest = service.storage.load_json("self_examination/latest.json")
    archive = service.storage.load_json(
        f"self_examination/history/{persisted.review_id}.json"
    )
    for payload in (latest, archive):
        assert payload["source_coverage"] == snapshot.source_coverage
        assert payload["source_errors"] == {}
        assert payload["metadata"]["source_coverage_contract"] == _SOURCE_COVERAGE_CONTRACT
        assert payload["metadata"]["required_source_ids"] == list(_REQUIRED_SOURCE_IDS)


def test_oses_discernment_reader_uses_the_injected_shared_instance(tmp_path) -> None:
    class SharedFrames:
        def __init__(self):
            self.calls = 0

        def recent_frames(self, limit=10):
            self.calls += 1
            return []

    shared = SharedFrames()
    service = _service(tmp_path, discernment_frame_service=shared)
    service._discernment_frame_findings()
    assert service.discernment_frame_service is shared
    assert shared.calls == 1
    assert service._source_coverage["discernment_frame_service"] == "READ_OK"


def test_oses_discernment_reader_does_not_create_a_private_instance_when_unwired(tmp_path) -> None:
    service = _service(tmp_path)
    service._discernment_frame_findings()
    assert service._source_coverage["discernment_frame_service"] == "NOT_CONFIGURED"
    assert service._source_errors["discernment_frame_service"] == (
        "shared_discernment_frame_service_not_injected"
    )


def test_task_context_assembler_uses_the_injected_shared_discernment_service() -> None:
    shared = SimpleNamespace(discernment_frame_summary=lambda: {"status": "shared"})
    assembler = TaskContextAssembler(
        episode_repository=None,
        knowledge_repository=None,
        run_repository=None,
        dossier_repository=None,
        hidden_incident_repository=None,
        site_policy_registry=None,
        capability_repository=None,
        adaptive_session_repository=None,
        discernment_frame_service=shared,
    )
    assert assembler.discernment_frame_service is shared
    assert assembler._discernment_frame_summary() == {"status": "shared"}


def test_portable_context_uses_the_injected_shared_discernment_service(tmp_path) -> None:
    class SharedFrames:
        def __init__(self):
            self.calls = 0

        def compact_export(self):
            self.calls += 1
            return {"status": "no_frame"}

        def latest_frame(self):
            return None

    shared = SharedFrames()
    service = PortableContextService(
        workspace_root=str(tmp_path),
        storage=ArtifactStorage(str(tmp_path / "portable")),
        discernment_frame_service=shared,
    )
    section = service._discernment_frame_section(now=datetime.now(timezone.utc))
    assert service.discernment_frame_service is shared
    assert shared.calls == 1
    assert "no_discernment_frame_generated" in section.unresolved_fields


def test_existing_test_evidence_without_r24_commit_provenance_stays_unverified(tmp_path) -> None:
    service = _service(tmp_path)
    evidence_path = tmp_path / "data" / "evolution" / "test_evidence" / "latest.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "passed": 10,
                "failed": 0,
                "errors": 0,
            }
        ),
        encoding="utf-8",
    )
    service._metacognitive_starvation_findings()
    assert service._source_coverage["test_evidence_file"] == "READ_UNVERIFIED"
    assert service._source_errors["test_evidence_file"] == (
        "R24_commit_bound_provenance_and_freshness_not_integrated"
    )
