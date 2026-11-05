from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
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



def test_oses_environment_model_reader_uses_configured_service(tmp_path) -> None:
    environment = SimpleNamespace(risk_signals=[])
    world_model = SimpleNamespace(
        current_model=lambda: SimpleNamespace(environment=None),
        environment_self_awareness_service=SimpleNamespace(
            current_model=lambda: environment,
        ),
    )
    service = _service(tmp_path, world_model_service=world_model)

    assert service._environment_model() is environment
    assert service._source_coverage['environment_self_awareness_service'] == 'READ_OK'


def test_oses_low_load_reads_environment_self_awareness_service(tmp_path) -> None:
    environment = SimpleNamespace(
        risk_signals=[SimpleNamespace(severity='HIGH')],
    )
    world_model_service = SimpleNamespace(
        current_model=lambda: SimpleNamespace(environment=None),
        environment_self_awareness_service=SimpleNamespace(
            current_model=lambda: environment,
        ),
    )
    service = _service(tmp_path, world_model_service=world_model_service)

    assert service._is_low_load(SimpleNamespace(block_records=[])) is False
    assert service._source_coverage['environment_self_awareness_service'] == 'READ_OK'


def test_oses_environment_model_failure_is_not_reported_as_clean(tmp_path) -> None:
    class BrokenEnvironmentService:
        def current_model(self):
            raise PermissionError('synthetic environment read failure')

    class BrokenWorldModel:
        def current_model(self):
            raise RuntimeError('snapshot unavailable')

        environment_self_awareness_service = BrokenEnvironmentService()

    service = _service(tmp_path, world_model_service=BrokenWorldModel())

    assert service._environment_model() is None
    assert service._source_coverage['environment_self_awareness_service'] == 'READ_FAILED'
    assert service._source_errors['environment_self_awareness_service'] == 'PermissionError'


def test_oses_runtime_tracer_records_success_only_after_all_reads(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class EmptyTracer:
        def events(self, *, kind: str, limit: int):
            return []

        def recent_dispatch_lifecycles(self, *, limit: int):
            return []

    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: EmptyTracer())
    service = _service(tmp_path)

    assert service._resource_quiescence_web_skill_findings() == []
    assert service._source_coverage['runtime_audit_tracer'] == 'READ_OK'


def test_oses_runtime_tracer_read_failure_is_preserved(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class BrokenTracer:
        def events(self, *, kind: str, limit: int):
            raise PermissionError('synthetic tracer read failure')

        def recent_dispatch_lifecycles(self, *, limit: int):
            return []

    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: BrokenTracer())
    service = _service(tmp_path)

    assert service._resource_quiescence_web_skill_findings() == []
    assert service._source_coverage['runtime_audit_tracer'] == 'READ_FAILED'
    assert service._source_errors['runtime_audit_tracer'] == 'PermissionError'


def test_oses_account_scanner_records_complete_quota_and_secret_reads(tmp_path, monkeypatch) -> None:
    scanner = import_module('iabv_v15.services.account_resource_scanner')
    monkeypatch.setattr(
        scanner,
        'get_all_quota_status',
        lambda: {'exhausted_count': 0, 'available_count': 0, 'exhausted_keys': []},
    )
    monkeypatch.setattr(scanner, 'scan_configured_secrets', lambda: {'missing': []})
    service = _service(tmp_path)

    assert service._account_resource_health_findings() == []
    assert service._source_coverage['account_resource_scanner'] == 'READ_OK'


def test_oses_account_scanner_failure_is_not_erased_by_later_success(tmp_path, monkeypatch) -> None:
    scanner = import_module('iabv_v15.services.account_resource_scanner')

    def fail_quota_read():
        raise PermissionError('synthetic quota read failure')

    monkeypatch.setattr(scanner, 'get_all_quota_status', fail_quota_read)
    monkeypatch.setattr(scanner, 'scan_configured_secrets', lambda: {'missing': []})
    service = _service(tmp_path)

    assert service._account_resource_health_findings() == []
    assert service._source_coverage['account_resource_scanner'] == 'READ_FAILED'
    assert service._source_errors['account_resource_scanner'] == 'PermissionError'



def test_oses_runtime_audit_log_integrity_is_verified(tmp_path) -> None:
    audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text(
        '{"kind":"dispatch_started","data":{"task_name":"chat"}}\n'
        '{"kind":"dispatch_terminal","data":{"terminal_state":"completed"}}\n',
        encoding='utf-8',
    )
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage['runtime_audit_log'] == 'READ_OK'
    assert 'runtime_audit_log' not in service._source_errors


def test_oses_runtime_audit_log_malformed_rows_are_partial_not_clean(tmp_path) -> None:
    audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text(
        '{"kind":"valid_event"}\n'
        '[]\n'
        '{malformed}\n',
        encoding='utf-8',
    )
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage['runtime_audit_log'] == 'READ_PARTIAL'
    assert service._source_errors['runtime_audit_log'] == 'malformed_jsonl_rows:2'


def test_oses_runtime_audit_log_missing_file_is_not_verified_empty(tmp_path) -> None:
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage['runtime_audit_log'] == 'CONFIRMED_NOT_FOUND'


def test_oses_runtime_audit_log_permission_failure_is_reported(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text('{"kind":"event"}\n', encoding='utf-8')
    original_open = Path.open

    def fail_target_open(self, *args, **kwargs):
        if self == audit_path:
            raise PermissionError('synthetic audit log access denied')
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', fail_target_open)
    service = _service(tmp_path)

    service._inspect_runtime_audit_log()

    assert service._source_coverage['runtime_audit_log'] == 'READ_FAILED'
    assert service._source_errors['runtime_audit_log'] == 'PermissionError'
