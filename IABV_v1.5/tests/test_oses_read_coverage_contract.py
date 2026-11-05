from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
from iabv_v15.services.evolution.portable_context_service import PortableContextService

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



def test_oses_discernment_service_requires_shared_instance(tmp_path) -> None:
    service = _service(tmp_path)

    assert service._discernment_frame_findings() == []
    assert service._source_coverage['discernment_frame_service'] == 'NOT_CONFIGURED'
    assert service._source_errors['discernment_frame_service'] == 'shared_discernment_frame_service_not_injected'


def test_oses_discernment_service_records_shared_instance_read(tmp_path) -> None:
    class SharedDiscernmentService:
        def recent_frames(self, limit=10):
            return []

    service = _service(tmp_path)
    service.discernment_frame_service = SharedDiscernmentService()

    findings = service._discernment_frame_findings()

    assert findings
    assert service._source_coverage['discernment_frame_service'] == 'READ_OK'


def test_oses_ui_bridge_records_freeze_reporter_and_missing_startup_log(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class EmptyTracer:
        def events(self, *, limit: int):
            return []

    class EmptyReporter:
        def list_reports(self, *, limit: int):
            return []

        def get_report(self, filename: str):
            raise AssertionError('no report should be requested for an empty listing')

    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: EmptyTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = EmptyReporter()

    assert service._ui_bridge_truth_findings() == []
    assert service._source_coverage['runtime_audit_tracer'] == 'READ_OK'
    assert service._source_coverage['freeze_incident_reporter'] == 'READ_OK'
    assert service._source_coverage['startup_ui_presence_log'] == 'CONFIRMED_NOT_FOUND'


def test_oses_ui_bridge_startup_presence_malformed_rows_are_partial(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class EmptyTracer:
        def events(self, *, limit: int):
            return []

    class EmptyReporter:
        def list_reports(self, *, limit: int):
            return []

        def get_report(self, filename: str):
            raise AssertionError('no report should be requested for an empty listing')

    trace_path = tmp_path / 'data' / 'logs' / 'startup_ui_presence.jsonl'
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text(
        '{"kind":"ui_bridge_port_conflict"}\n'
        '{malformed}\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: EmptyTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = EmptyReporter()

    service._ui_bridge_truth_findings()

    assert service._source_coverage['startup_ui_presence_log'] == 'READ_PARTIAL'
    assert service._source_errors['startup_ui_presence_log'] == 'malformed_jsonl_rows'


def test_oses_ui_bridge_preserves_runtime_tracer_failure(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class BrokenTracer:
        def events(self, *, limit: int):
            raise PermissionError('synthetic UI bridge tracer read failure')

    class EmptyReporter:
        def list_reports(self, *, limit: int):
            return []

        def get_report(self, filename: str):
            raise AssertionError('no report should be requested for an empty listing')

    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: BrokenTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = EmptyReporter()

    service._ui_bridge_truth_findings()

    assert service._source_coverage['runtime_audit_tracer'] == 'READ_FAILED'
    assert service._source_errors['runtime_audit_tracer'] == 'PermissionError'


def test_oses_ui_bridge_freeze_report_parse_error_is_partial(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class EmptyTracer:
        def events(self, *, limit: int):
            return []

    class BrokenReporter:
        def list_reports(self, *, limit: int):
            return [{'file': 'freeze_bad.json', 'error': 'parse_failed'}]

        def get_report(self, filename: str):
            raise AssertionError('parse-failed report must not be opened again')

    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: EmptyTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = BrokenReporter()

    service._ui_bridge_truth_findings()

    assert service._source_coverage['freeze_incident_reporter'] == 'READ_PARTIAL'
    assert service._source_errors['freeze_incident_reporter'] == 'incident_report_parse_or_shape_error'



def test_oses_ui_bridge_startup_presence_permission_failure(tmp_path, monkeypatch) -> None:
    tracer_module = import_module('iabv_v15.services.evolution.runtime_audit_tracer')

    class EmptyTracer:
        def events(self, *, limit: int):
            return []

    class EmptyReporter:
        def list_reports(self, *, limit: int):
            return []

        def get_report(self, filename: str):
            raise AssertionError('no report should be requested for an empty listing')

    trace_path = tmp_path / 'data' / 'logs' / 'startup_ui_presence.jsonl'
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text('{"kind":"event"}\\n', encoding='utf-8')
    original_open = Path.open

    def fail_target_open(self, *args, **kwargs):
        if self == trace_path:
            raise PermissionError('synthetic startup UI log access denied')
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', fail_target_open)
    monkeypatch.setattr(tracer_module, 'get_runtime_tracer', lambda: EmptyTracer())
    service = _service(tmp_path)
    service._freeze_incident_reporter = EmptyReporter()

    service._ui_bridge_truth_findings()

    assert service._source_coverage['startup_ui_presence_log'] == 'READ_FAILED'
    assert service._source_errors['startup_ui_presence_log'] == 'PermissionError'



def test_oses_cached_review_rejects_residual_errors_even_when_statuses_are_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    coverage = _complete_coverage()
    errors = {'runtime_audit_tracer': 'PermissionError'}
    snapshot = SelfExaminationSnapshot(
        source_coverage=coverage,
        source_errors=errors,
        metadata={
            'source_coverage_contract': _SOURCE_COVERAGE_CONTRACT,
            'required_source_ids': list(_REQUIRED_SOURCE_IDS),
            'source_coverage': dict(coverage),
            'source_errors': dict(errors),
        },
    )
    service._current_review = snapshot
    service._is_fresh = lambda review, *, max_age_seconds: True

    with pytest.raises(RuntimeError, match='oses_source_coverage_incomplete'):
        service.current_review_cached()


def test_oses_coverage_report_is_incomplete_when_error_map_is_nonempty(tmp_path) -> None:
    service = _service(tmp_path)
    service._source_coverage = _complete_coverage()
    service._source_errors = {'runtime_audit_tracer': 'PermissionError'}

    report = service._source_coverage_report()

    assert report['complete'] is False
    assert 'runtime_audit_tracer' in report['incomplete_source_ids']
    assert report['source_errors']['runtime_audit_tracer'] == 'PermissionError'



def _shared_birth_frame_service(tmp_path) -> DiscernmentFrameService:
    service = DiscernmentFrameService(workspace_root=str(tmp_path))
    service.build_birth_frame(
        startup_events=[
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0},
            {'phase': 'phase_world_model_done', 't_ms_from_start': 120.0},
        ],
        world_model={
            'active_windows': [],
            'network': {'connected': True, 'status': 'connected'},
        },
        environment_self_model={
            'known_environment': True,
            'scan_status': 'ready',
            'risk_signals': [],
        },
    )
    return service


def test_oses_tca_and_portable_context_read_the_same_shared_frame_history(tmp_path) -> None:
    shared = _shared_birth_frame_service(tmp_path)

    oses = _service(tmp_path, discernment_frame_service=shared)
    assert oses._discernment_frame_findings() == []
    assert oses._source_coverage['discernment_frame_service'] == 'READ_OK'

    assembler = TaskContextAssembler.__new__(TaskContextAssembler)
    assembler.discernment_frame_service = shared
    summary = assembler._discernment_frame_summary()
    assert summary['phase'] == 'birth'

    portable = PortableContextService.__new__(PortableContextService)
    portable.discernment_frame_service = shared
    section = portable._discernment_frame_section(now=datetime.now(timezone.utc))
    assert section.items[0]['phase'] == 'birth'
    assert section.unresolved_fields == []


def test_tca_and_portable_context_do_not_create_private_empty_discernment_instances() -> None:
    assembler = TaskContextAssembler.__new__(TaskContextAssembler)
    portable = PortableContextService.__new__(PortableContextService)

    assert assembler._discernment_frame_summary()['reason'] == 'shared_service_not_injected'
    section = portable._discernment_frame_section(now=datetime.now(timezone.utc))
    assert section.items[0]['reason'] == 'shared_service_not_injected'
    assert 'discernment_frame_service_not_configured' in section.unresolved_fields


def test_partial_environment_model_is_available_but_not_trusted(tmp_path) -> None:
    service = DiscernmentFrameService(workspace_root=str(tmp_path))

    frame = service.build_frame(
        phase='observe',
        trigger_source='test',
        world_model={'active_windows': [], 'network': {'connected': True}},
        environment_self_model={
            'known_environment': False,
            'scan_status': 'partial',
        },
    )

    assert 'environment_self_model' in frame.sensor_sources
    assert 'environment_self_model' in frame.untrusted_sources
    assert 'environment_self_model' not in frame.trusted_sources


def test_bootstrap_deferred_self_examination_builds_birth_frame_from_live_snapshots(tmp_path, monkeypatch) -> None:
    from iabv_v15.bootstrap import AppBootstrap

    class FakeWorldModel:
        def current_model(self):
            return SimpleNamespace(model_dump=lambda mode='json': {
                'active_windows': [{'title': 'Codex', 'app_name': 'Codex'}],
                'network_status': {'connected': True, 'status': 'connected'},
                'tool_live_status': [],
                'observation_sources': ['test_world_model'],
                'detected_blocks': [],
                'confidence': 0.8,
            })

    class FakeEnvironment:
        def current_model(self):
            return SimpleNamespace(model_dump=lambda mode='json': {
                'known_environment': True,
                'scan_status': 'ready',
                'risk_signals': [],
            })

    class FakeTimeline:
        def events(self):
            return [
                {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0},
                {'phase': 'phase_world_model_done', 't_ms_from_start': 100.0},
            ]

    class FakeFreezeReporter:
        def recent_incidents(self, limit=5):
            return []

    class FakeOSES:
        def __init__(self):
            self.source_status = []

        def _startup_health_findings(self):
            return []

        def _record_source_status(self, source, status, error=''):
            self.source_status.append((source, status, error))

    bootstrap = AppBootstrap.__new__(AppBootstrap)
    bootstrap.discernment_frame_service = DiscernmentFrameService(workspace_root=str(tmp_path))
    bootstrap.world_model_service = FakeWorldModel()
    bootstrap.environment_self_awareness_service = FakeEnvironment()
    bootstrap._timeline = FakeTimeline()
    bootstrap.freeze_incident_reporter = FakeFreezeReporter()
    bootstrap.operational_self_examination_service = FakeOSES()
    bootstrap.perception_cross_validator = None
    bootstrap.autonomy_cycle_service = None
    monkeypatch.setenv('IABV_MCP_SUBPROCESS', '0')

    bootstrap._startup_self_examination()

    frame = bootstrap.discernment_frame_service.latest_frame()
    assert frame is not None
    assert frame.phase == 'birth'
    assert frame.trigger_source == 'startup'
    assert 'startup_timeline' in frame.sensor_sources
    assert 'world_model' in frame.trusted_sources
    assert 'environment_self_model' in frame.trusted_sources



def test_component_constructors_accept_the_same_shared_discernment_service(tmp_path) -> None:
    shared = DiscernmentFrameService(workspace_root=str(tmp_path))
    marker = object()

    assembler = TaskContextAssembler(
        episode_repository=marker,
        knowledge_repository=marker,
        run_repository=marker,
        dossier_repository=marker,
        hidden_incident_repository=marker,
        site_policy_registry=marker,
        capability_repository=marker,
        adaptive_session_repository=marker,
        discernment_frame_service=shared,
    )
    portable = PortableContextService(
        workspace_root=str(tmp_path),
        storage=ArtifactStorage(str(tmp_path / 'portable')),
        discernment_frame_service=shared,
    )
    oses = _service(
        tmp_path,
        discernment_frame_service=shared,
    )

    assert assembler.discernment_frame_service is shared
    assert portable.discernment_frame_service is shared
    assert oses.discernment_frame_service is shared



def test_portable_context_unresolved_links_reads_shared_discernment_service(tmp_path) -> None:
    shared = _shared_birth_frame_service(tmp_path)
    latest = shared.latest_frame()
    assert latest is not None
    latest.unresolved_fields.append('synthetic_unresolved_sensor')

    portable = PortableContextService.__new__(PortableContextService)
    portable.discernment_frame_service = shared

    section = portable._unresolved_metacognitive_links_section(
        now=datetime.now(timezone.utc),
    )

    assert 'synthetic_unresolved_sensor' in section.unresolved_fields
    assert section.items[0]['source'] == 'discernment_frame'


def test_portable_context_unresolved_links_do_not_claim_all_clear_without_shared_service() -> None:
    portable = PortableContextService.__new__(PortableContextService)

    section = portable._unresolved_metacognitive_links_section(
        now=datetime.now(timezone.utc),
    )

    assert 'discernment_frame_service_not_configured' in section.unresolved_fields



def test_oses_metacognitive_error_ledger_is_read_without_calibration_sample(tmp_path) -> None:
    service = _service(tmp_path)

    findings = service._metacognitive_calibration_findings(
        previous_review=None,
        experiment_runs=[],
    )

    assert findings == []
    assert service._source_coverage['metacognitive_error_ledger'] == 'CONFIRMED_NOT_FOUND'


def test_oses_metacognitive_error_ledger_valid_empty_file_is_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    service.storage.save_bytes(
        'self_examination/metacognitive_ledger.jsonl',
        b'',
    )

    findings = service._metacognitive_calibration_findings(
        previous_review=None,
        experiment_runs=[],
    )

    assert findings == []
    assert service._source_coverage['metacognitive_error_ledger'] == 'READ_OK'



def test_oses_runtime_log_invalid_utf8_is_not_read_ok(tmp_path) -> None:
    service = _service(tmp_path)
    log_path = tmp_path / 'data' / 'logs' / 'iabv_v15.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(b'valid line\ninvalid: \xff\xfe\n')

    findings = service._runtime_log_findings()

    assert findings == []
    assert service._source_coverage['runtime_log'] == 'READ_FAILED'
    assert service._source_errors['runtime_log'] == 'UnicodeDecodeError'


def test_oses_runtime_log_surfaces_account_scanner_failure(tmp_path, monkeypatch) -> None:
    from importlib import import_module

    scanner = import_module('iabv_v15.services.account_resource_scanner')

    def fail_scan():
        raise PermissionError('synthetic account scan failure')

    monkeypatch.setattr(scanner, 'scan_browser_accounts', fail_scan)
    service = _service(tmp_path)
    log_path = tmp_path / 'data' / 'logs' / 'iabv_v15.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('', encoding='utf-8')

    service._runtime_log_findings()

    assert service._source_coverage['runtime_log'] == 'READ_OK'
    assert service._source_coverage['account_resource_scanner'] == 'READ_FAILED'
    assert service._source_errors['account_resource_scanner'] == 'PermissionError'



def test_validation_feedback_history_valid_jsonl_is_read_ok(tmp_path) -> None:
    import json

    service = _service(tmp_path)
    history = tmp_path / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
    history.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        'decision': 'discarded',
        'proposal_kind': 'route_substitution',
        'candidate_assistant_kind': 'claude',
        'current_assistant_kind': 'chatgpt',
    }
    history.write_text(json.dumps(entry) + '\\n', encoding='utf-8')

    service._loop_closure_findings(findings_so_far=[], experiment_runs=[])
    tried = service._load_tried_proposal_keys()

    assert 'route_substitution:chatgpt:claude' in tried
    assert service._source_coverage['validation_feedback_history'] == 'READ_OK'
    assert 'validation_feedback_history' not in service._source_errors


def test_validation_feedback_history_malformed_jsonl_is_partial(tmp_path) -> None:
    import json

    service = _service(tmp_path)
    history = tmp_path / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
    history.parent.mkdir(parents=True, exist_ok=True)
    valid = {
        'decision': 'discarded',
        'proposal_kind': 'route_substitution',
        'candidate_assistant_kind': 'claude',
        'current_assistant_kind': 'chatgpt',
    }
    history.write_text(
        json.dumps(valid) + '\\n[]\\n{malformed\\n',
        encoding='utf-8',
    )

    service._loop_closure_findings(findings_so_far=[], experiment_runs=[])
    service._load_tried_proposal_keys()

    assert service._source_coverage['validation_feedback_history'] == 'READ_PARTIAL'
    assert service._source_errors['validation_feedback_history'] == 'malformed_jsonl_rows:2'


def test_validation_feedback_history_missing_file_is_confirmed_not_found(tmp_path) -> None:
    service = _service(tmp_path)

    service._loop_closure_findings(findings_so_far=[], experiment_runs=[])
    assert service._source_coverage['validation_feedback_history'] == 'CONFIRMED_NOT_FOUND'

    assert service._load_tried_proposal_keys() == set()
    assert service._source_coverage['validation_feedback_history'] == 'CONFIRMED_NOT_FOUND'


def test_validation_feedback_history_permission_failure_is_not_not_found(tmp_path, monkeypatch) -> None:
    from pathlib import Path

    service = _service(tmp_path)
    history = tmp_path / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text('{}\\n', encoding='utf-8')
    original_read_text = Path.read_text

    def deny_history_read(path, *args, **kwargs):
        if path == history:
            raise PermissionError('synthetic feedback history permission failure')
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', deny_history_read)

    service._loop_closure_findings(findings_so_far=[], experiment_runs=[])
    assert service._source_coverage['validation_feedback_history'] == 'READ_FAILED'
    assert service._source_errors['validation_feedback_history'] == 'PermissionError'

    service._load_tried_proposal_keys()
    assert service._source_coverage['validation_feedback_history'] == 'READ_FAILED'
    assert service._source_errors['validation_feedback_history'] == 'PermissionError'
