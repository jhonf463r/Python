from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from importlib import import_module
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
    assert service._source_coverage["test_evidence_file"] == "READ_PARTIAL"
    assert service._source_errors["test_evidence_file"] == (
        "fresh_commit_bound_evidence_not_verified"
    )


def test_cached_oses_review_rejects_typed_metadata_coverage_disagreement(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    metadata_coverage = dict(snapshot.metadata["source_coverage"])
    metadata_coverage["run_repository"] = "READ_FAILED"
    snapshot.metadata = {**snapshot.metadata, "source_coverage": metadata_coverage}
    service._current_review = snapshot

    with pytest.raises(RuntimeError, match="oses_source_coverage_representation_mismatch"):
        service.current_review_cached()


def test_cached_oses_review_rejects_metadata_completion_claim_that_disagrees(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    snapshot.metadata = {**snapshot.metadata, "source_coverage_complete": False}
    service._current_review = snapshot

    with pytest.raises(RuntimeError, match="oses_source_coverage_completion_unverified"):
        service.current_review_cached()


def test_cached_oses_review_rejects_future_dated_snapshot(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot().model_copy(
        update={"updated_at_utc": datetime.now(timezone.utc) + timedelta(seconds=60)}
    )
    service._current_review = snapshot

    with pytest.raises(RuntimeError, match="oses_cached_review_stale"):
        service.current_review_cached()


def test_cached_oses_miss_does_not_create_self_examination_directory(tmp_path) -> None:
    service = _service(tmp_path)
    cache_dir = Path(service.storage.root) / "self_examination"
    assert not cache_dir.exists()

    with pytest.raises(RuntimeError, match="oses_cached_review_unavailable"):
        service.current_review_cached()

    assert not cache_dir.exists()


def test_oses_persistence_materializes_all_required_source_ids_even_if_some_were_not_instrumented(tmp_path) -> None:
    service = _service(tmp_path)
    snapshot = _complete_snapshot()
    service._source_coverage = {"run_repository": "READ_OK"}
    service._source_errors = {}

    persisted = service._persist_review(snapshot)
    latest = service.storage.load_json("self_examination/latest.json")
    assert set(latest["source_coverage"]) == set(_REQUIRED_SOURCE_IDS)
    assert latest["source_coverage"]["adaptive_session_repository"] == "NOT_INSTRUMENTED"
    assert latest["metadata"]["source_coverage_complete"] is False
    assert "adaptive_session_repository" in latest["metadata"]["source_coverage_incomplete_ids"]
    assert persisted.source_coverage == latest["source_coverage"]


def test_oses_coverage_report_marks_unexpected_reader_ids_incomplete(tmp_path) -> None:
    service = _service(tmp_path)
    service._source_coverage["unregistered_reader"] = "READ_OK"

    report = service._source_coverage_report()

    assert report["complete"] is False
    assert report["unexpected_source_ids"] == ["unregistered_reader"]


def test_oses_accepts_fresh_commit_bound_test_evidence(tmp_path, monkeypatch) -> None:
    from iabv_v15.infra.mcp import audit_tools

    service = _service(tmp_path)
    evidence_path = tmp_path / "data" / "evolution" / "test_evidence" / "latest.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": 10,
        "failed": 0,
        "errors": 0,
        "commit_sha": "a" * 40,
        "branch": "test-branch",
        "worktree_clean": True,
        "provenance_status": "COMMIT_BOUND_CLEAN",
        "worktree_status_sha256": "b" * 64,
        "metadata": {
            "provenance_before": {
            "commit_sha": "a" * 40,
            "branch": "test-branch",
            "worktree_clean": True,
            "provenance_status": "COMMIT_BOUND_CLEAN",
            "worktree_status_sha256": "b" * 64,
        },
            "provenance_after": {
            "commit_sha": "a" * 40,
            "branch": "test-branch",
            "worktree_clean": True,
            "provenance_status": "COMMIT_BOUND_CLEAN",
            "worktree_status_sha256": "b" * 64,
        },
        },
    }
    evidence["payload_sha256"] = audit_tools._test_evidence_payload_sha256(evidence)
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    monkeypatch.setattr(
        audit_tools,
        "_collect_test_git_provenance",
        lambda _root: {
            "commit_sha": "a" * 40,
            "branch": "test-branch",
            "worktree_clean": True,
            "provenance_status": "COMMIT_BOUND_CLEAN",
            "worktree_status_sha256": "b" * 64,
        },
    )

    service._metacognitive_starvation_findings()

    assert service._source_coverage["test_evidence_file"] == "READ_OK"
    assert service._source_errors.get("test_evidence_file", "") == ""


def test_oses_account_scanner_partial_coverage_cannot_be_promoted_to_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_account_resource_coverage(
        {
            "source_coverage": {
                "browser_accounts": "READ_PARTIAL",
                "quota_tracker": "READ_OK",
            },
            "source_errors": {"browser_accounts": "profile_read_failed"},
        }
    )
    assert service._source_coverage["account_resource_scanner"] == "READ_PARTIAL"
    assert "error_sources=browser_accounts" in service._source_errors["account_resource_scanner"]


def test_oses_account_scanner_missing_coverage_is_unverified(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_account_resource_coverage({"accounts": [], "count": 0})
    assert service._source_coverage["account_resource_scanner"] == "READ_UNVERIFIED"


def test_oses_account_scanner_partial_state_survives_later_success(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_account_resource_coverage(
        {"source_coverage": {"browser_sessions": "READ_PARTIAL"}, "source_errors": {}}
    )
    service._record_account_resource_coverage(
        {"source_coverage": {"quota_tracker": "READ_OK"}, "source_errors": {}}
    )
    assert service._source_coverage["account_resource_scanner"] == "READ_PARTIAL"


def test_oses_account_scanner_residual_errors_prevent_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_account_resource_coverage(
        {
            "source_coverage": {
                "browser_accounts": "READ_OK",
                "quota_tracker": "READ_OK",
            },
            "source_errors": {"browser_accounts": "profile_discovery_warning"},
        }
    )
    assert service._source_coverage["account_resource_scanner"] == "READ_PARTIAL"
    assert "error_sources=browser_accounts" in service._source_errors["account_resource_scanner"]



def test_oses_account_scanner_malformed_source_errors_are_unverified(tmp_path) -> None:
    service = _service(tmp_path)
    service._record_account_resource_coverage(
        {
            "source_coverage": {"browser_accounts": "READ_OK"},
            "source_errors": ["invalid-shape"],
        }
    )
    assert service._source_coverage["account_resource_scanner"] == "READ_UNVERIFIED"
    assert service._source_errors["account_resource_scanner"] == "scanner_source_errors_invalid"



def test_oses_recent_run_reader_records_read_failure(tmp_path) -> None:
    class BrokenRunRepository:
        def list_recent(self, limit=60):
            raise PermissionError("synthetic repository read failure")

    service = _service(tmp_path, run_repository=BrokenRunRepository())

    assert service._recent_runs() == []
    assert service._source_coverage["run_repository"] == "READ_FAILED"
    assert service._source_errors["run_repository"] == "PermissionError"


def test_oses_unconfigured_adaptive_session_reader_is_not_verified_empty(tmp_path) -> None:
    service = _service(tmp_path)

    assert service._recent_adaptive_sessions() == []
    assert service._source_coverage["adaptive_session_repository"] == "NOT_CONFIGURED"


def test_oses_environment_reader_uses_configured_service(tmp_path) -> None:
    environment = SimpleNamespace(risk_signals=[])
    world_model = SimpleNamespace(
        current_model=lambda: SimpleNamespace(environment=None),
        environment_self_awareness_service=SimpleNamespace(current_model=lambda: environment),
    )
    service = _service(tmp_path, world_model_service=world_model)

    assert service._environment_model() is environment
    assert service._source_coverage["environment_self_awareness_service"] == "READ_OK"


def test_oses_environment_reader_failure_is_not_reported_as_clean(tmp_path) -> None:
    class BrokenEnvironmentService:
        def current_model(self):
            raise PermissionError("synthetic environment read failure")

    class BrokenWorldModel:
        def current_model(self):
            raise RuntimeError("snapshot unavailable")

        environment_self_awareness_service = BrokenEnvironmentService()

    service = _service(tmp_path, world_model_service=BrokenWorldModel())

    assert service._environment_model() is None
    assert service._source_coverage["environment_self_awareness_service"] == "READ_FAILED"
    assert service._source_errors["environment_self_awareness_service"] == "PermissionError"


def test_oses_runtime_audit_log_valid_jsonl_is_read_ok(tmp_path) -> None:
    audit_path = tmp_path / "data" / "logs" / "runtime_audit.jsonl"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text(
        '{"kind":"dispatch_started","data":{"task_name":"chat"}}\n'
        '{"kind":"dispatch_terminal","data":{"terminal_state":"completed"}}\n',
        encoding="utf-8",
    )
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage["runtime_audit_log"] == "READ_OK"
    assert "runtime_audit_log" not in service._source_errors


def test_oses_runtime_audit_log_malformed_rows_are_partial(tmp_path) -> None:
    audit_path = tmp_path / "data" / "logs" / "runtime_audit.jsonl"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text('{"kind":"valid"}\n[]\n{malformed}\n', encoding="utf-8")
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage["runtime_audit_log"] == "READ_PARTIAL"
    assert service._source_errors["runtime_audit_log"] == "malformed_jsonl_rows:2"


def test_oses_runtime_audit_log_absence_is_confirmed_not_verified_empty(tmp_path) -> None:
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage["runtime_audit_log"] == "CONFIRMED_NOT_FOUND"


def test_oses_runtime_audit_log_permission_failure_is_read_failed(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / "data" / "logs" / "runtime_audit.jsonl"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text('{"kind":"event"}\n', encoding="utf-8")
    original_open = Path.open

    def deny_audit_open(target, *args, **kwargs):
        if target == audit_path:
            raise PermissionError("synthetic audit log access denied")
        return original_open(target, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_audit_open)
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage["runtime_audit_log"] == "READ_FAILED"
    assert service._source_errors["runtime_audit_log"] == "PermissionError"


def test_oses_runtime_tracer_failure_is_preserved(tmp_path, monkeypatch) -> None:
    tracer_module = import_module("iabv_v15.services.evolution.runtime_audit_tracer")

    class BrokenTracer:
        def events(self, *, kind: str, limit: int):
            raise PermissionError("synthetic tracer read failure")

        def recent_dispatch_lifecycles(self, *, limit: int):
            return []

    monkeypatch.setattr(tracer_module, "get_runtime_tracer", lambda: BrokenTracer())
    service = _service(tmp_path)

    assert service._resource_quiescence_web_skill_findings() == []
    assert service._source_coverage["runtime_audit_tracer"] == "READ_FAILED"
    assert service._source_errors["runtime_audit_tracer"] == "PermissionError"


def test_oses_metacognitive_ledger_valid_empty_file_is_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    service.storage.save_bytes("self_examination/metacognitive_ledger.jsonl", b"")

    assert service._load_metacognitive_ledger() == []
    assert service._source_coverage["metacognitive_error_ledger"] == "READ_OK"


def test_oses_metacognitive_ledger_malformed_rows_are_partial(tmp_path) -> None:
    service = _service(tmp_path)
    service.storage.save_bytes(
        "self_examination/metacognitive_ledger.jsonl",
        b'{"valid":true}\n[]\n{malformed}\n',
    )

    assert service._load_metacognitive_ledger() == [{"valid": True}]
    assert service._source_coverage["metacognitive_error_ledger"] == "READ_PARTIAL"
    assert service._source_errors["metacognitive_error_ledger"] == "malformed_jsonl_rows:2"


def test_oses_metacognitive_ledger_invalid_utf8_is_read_failed(tmp_path) -> None:
    service = _service(tmp_path)
    service.storage.save_bytes("self_examination/metacognitive_ledger.jsonl", b'{"valid":true}\n\xff')

    assert service._load_metacognitive_ledger() == []
    assert service._source_coverage["metacognitive_error_ledger"] == "READ_FAILED"
    assert service._source_errors["metacognitive_error_ledger"] == "UnicodeDecodeError"


def test_validation_feedback_history_valid_jsonl_is_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    history = tmp_path / "data" / "evolution" / "validation_feedback" / "history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(
        json.dumps({
            "decision": "discarded",
            "proposal_kind": "route_substitution",
            "candidate_assistant_kind": "claude",
            "current_assistant_kind": "chatgpt",
        }) + "\n",
        encoding="utf-8",
    )

    tried = service._load_tried_proposal_keys()

    assert "route_substitution:chatgpt:claude" in tried
    assert service._source_coverage["validation_feedback_history"] == "READ_OK"


def test_validation_feedback_history_malformed_jsonl_is_partial(tmp_path) -> None:
    service = _service(tmp_path)
    history = tmp_path / "data" / "evolution" / "validation_feedback" / "history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    valid = {
        "decision": "discarded",
        "proposal_kind": "route_substitution",
        "candidate_assistant_kind": "claude",
        "current_assistant_kind": "chatgpt",
    }
    history.write_text(json.dumps(valid) + "\n[]\n{malformed\n", encoding="utf-8")

    service._load_tried_proposal_keys()

    assert service._source_coverage["validation_feedback_history"] == "READ_PARTIAL"
    assert service._source_errors["validation_feedback_history"] == "malformed_jsonl_rows:2"


def test_validation_feedback_history_absence_is_confirmed_not_found(tmp_path) -> None:
    service = _service(tmp_path)

    assert service._load_tried_proposal_keys() == set()
    assert service._source_coverage["validation_feedback_history"] == "CONFIRMED_NOT_FOUND"


def test_validation_feedback_history_permission_failure_is_read_failed(monkeypatch, tmp_path) -> None:
    history = tmp_path / "data" / "evolution" / "validation_feedback" / "history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text("{}\n", encoding="utf-8")
    original_read_text = Path.read_text

    def deny_history_read(target, *args, **kwargs):
        if target == history:
            raise PermissionError("synthetic feedback history permission failure")
        return original_read_text(target, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_history_read)
    service = _service(tmp_path)

    assert service._load_tried_proposal_keys() == set()
    assert service._source_coverage["validation_feedback_history"] == "READ_FAILED"
    assert service._source_errors["validation_feedback_history"] == "PermissionError"


def test_oses_runtime_log_invalid_utf8_is_not_read_ok(tmp_path) -> None:
    log_path = tmp_path / "data" / "logs" / "iabv_v15.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(b"valid line\ninvalid: \xff\xfe\n")
    service = _service(tmp_path)

    assert service._runtime_log_findings() == []
    assert service._source_coverage["runtime_log"] == "READ_FAILED"
    assert service._source_errors["runtime_log"] == "UnicodeDecodeError"



def test_oses_ui_bridge_startup_presence_malformed_rows_are_partial(tmp_path, monkeypatch) -> None:
    tracer_module = import_module("iabv_v15.services.evolution.runtime_audit_tracer")

    class EmptyTracer:
        def events(self, *, limit: int):
            return []

    class EmptyReporter:
        def list_reports(self, *, limit: int):
            return []

    trace = tmp_path / "data" / "logs" / "startup_ui_presence.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_text('{"kind":"ui_bridge_port_conflict"}\n{malformed}\n', encoding="utf-8")
    monkeypatch.setattr(tracer_module, "get_runtime_tracer", lambda: EmptyTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = EmptyReporter()

    service._ui_bridge_truth_findings()

    assert service._source_coverage["startup_ui_presence_log"] == "READ_PARTIAL"
    assert service._source_errors["startup_ui_presence_log"] == "malformed_jsonl_rows"


def test_oses_ui_bridge_freeze_report_shape_error_is_partial(tmp_path, monkeypatch) -> None:
    tracer_module = import_module("iabv15.services.evolution.runtime_audit_tracer")

    class EmptyTracer:
        def events(self, *, limit: int):
            return []

    class BrokenReporter:
        def list_reports(self, *, limit: int):
            return [{"file": "freeze_bad.json", "error": "parse_failed"}]

        def get_report(self, filename: str):
            raise AssertionError("parse-failed report must not be opened again")

    monkeypatch.setattr(tracer_module, "get_runtime_tracer", lambda: EmptyTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = BrokenReporter()

    service._ui_bridge_truth_findings()

    assert service._source_coverage["freeze_incident_reporter"] == "READ_PARTIAL"
    assert service._source_errors["freeze_incident_reporter"] == "incident_report_parse_or_shape_error"


def test_oses_ui_bridge_runtime_tracer_failure_is_preserved(tmp_path, monkeypatch) -> None:
    tracer_module = import_module("iabv15.services.evolution.runtime_audit_tracer")

    class BrokenTracer:
        def events(self, *, limit: int):
            raise PermissionError("synthetic UI bridge tracer failure")

    monkeypatch.setattr(tracer_module, "get_runtime_tracer", lambda: BrokenTracer())
    service = _service(tmp_path)

    service._ui_bridge_truth_findings()

    assert service._source_coverage["runtime_audit_tracer"] == "READ_FAILED"
    assert service._source_errors["runtime_audit_tracer"] == "PermissionError"


def test_oses_test_evidence_without_commit_provenance_is_partial(tmp_path) -> None:
    path = tmp_path / "data" / "evolution" / "test_evidence" / "latest.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": 10,
            "failed": 0,
            "errors": 0,
        }),
        encoding="utf-8",
    )
    service = _service(tmp_path)

    service._metacognitive_starvation_findings()

    assert service._source_coverage["test_evidence_file"] == "READ_PARTIAL"
    assert service._source_errors["test_evidence_file"] == "fresh_commit_bound_evidence_not_verified"


def test_oses_test_evidence_permission_failure_is_not_absence(tmp_path, monkeypatch) -> None:
    path = tmp_path / "data" / "evolution" / "test_evidence" / "latest.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    original_read_bytes = Path.read_bytes

    def deny_evidence_read(target, *args, **kwargs):
        if target == path:
            raise PermissionError("synthetic TestEvidence read denial")
        return original_read_bytes(target, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", deny_evidence_read)
    service = _service(tmp_path)

    service._metacognitive_starvation_findings()

    assert service._source_coverage["test_evidence_file"] == "READ_FAILED"
    assert service._source_errors["test_evidence_file"] == "PermissionError"


def test_oses_test_evidence_missing_file_is_confirmed_not_found(tmp_path) -> None:
    service = _service(tmp_path)

    service._metacognitive_starvation_findings()

    assert service._source_coverage["test_evidence_file"] == "CONFIRMED_NOT_FOUND"


def test_oses_adaptive_threshold_failure_survives_later_success(tmp_path, monkeypatch) -> None:
    service = _service(tmp_path, experiment_lab_repository=object())
    attempts = 0

    def fail_once_then_succeed():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            service._record_source_status("experiment_lab_threshold", "READ_FAILED", "OperationalError")
            return None
        service._record_source_status("experiment_lab_threshold", "READ_OK")
        return 4

    monkeypatch.setattr(service, "_compute_current_adaptive_nc", fail_once_then_succeed)

    assert service._adaptive_threshold_shift_findings() == []
    assert attempts == 1
    assert service._source_coverage["experiment_lab_threshold"] == "READ_FAILED"

    assert service._compute_current_adaptive_nc() == 4
    assert service._source_coverage["experiment_lab_threshold"] == "READ_FAILED"
    assert service._source_errors["experiment_lab_threshold"] == "OperationalError"

    report = service._source_coverage_report()
    assert report["complete"] is False
    assert "experiment_lab_threshold" in report["incomplete_source_ids"]



def test_oses_low_load_reads_environment_self_awareness_service(tmp_path) -> None:
    environment = SimpleNamespace(risk_signals=[SimpleNamespace(severity="HIGH")])
    world_model = SimpleNamespace(
        current_model=lambda: SimpleNamespace(environment=None),
        environment_self_awareness_service=SimpleNamespace(current_model=lambda: environment),
    )
    service = _service(tmp_path, world_model_service=world_model)

    assert service._is_low_load(SimpleNamespace(block_records=[])) is False
    assert service._source_coverage["environment_self_awareness_service"] == "READ_OK"


def test_oses_runtime_tracer_records_read_ok_only_after_all_reads(tmp_path, monkeypatch) -> None:
    tracer_module = import_module("iabv_v15.services.evolution.runtime_audit_tracer")

    class EmptyTracer:
        def events(self, *, kind: str, limit: int):
            return []

        def recent_dispatch_lifecycles(self, *, limit: int):
            return []

    monkeypatch.setattr(tracer_module, "get_runtime_tracer", lambda: EmptyTracer())
    service = _service(tmp_path)

    assert service._resource_quiescence_web_skill_findings() == []
    assert service._source_coverage["runtime_audit_tracer"] == "READ_OK"
    assert "runtime_audit_tracer" not in service._source_errors
