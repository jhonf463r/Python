"""Tests for RuntimeAuditTracer — continuous self-audit from boot to shutdown."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from iabv_v15.services.evolution.runtime_audit_tracer import (
    RuntimeAuditTracer,
    get_runtime_tracer,
)


class TestRuntimeAuditTracer:
    """Core event tracing."""

    @pytest.fixture()
    def tracer(self, tmp_path: Path) -> RuntimeAuditTracer:
        t = RuntimeAuditTracer(log_dir=str(tmp_path))
        t.configure(tmp_path)
        return t

    def test_trace_creates_event(self, tracer: RuntimeAuditTracer) -> None:
        event = tracer.trace('test_event', key='value')
        assert event['kind'] == 'test_event'
        assert event['data']['key'] == 'value'
        assert 'ts' in event
        assert 'elapsed_ms' in event
        assert event['seq'] == 1

    def test_events_in_memory(self, tracer: RuntimeAuditTracer) -> None:
        tracer.trace('a')
        tracer.trace('b')
        tracer.trace('c')
        events = tracer.events()
        assert len(events) == 3
        assert [e['kind'] for e in events] == ['a', 'b', 'c']

    def test_events_filter_by_kind(self, tracer: RuntimeAuditTracer) -> None:
        tracer.trace('alpha')
        tracer.trace('beta')
        tracer.trace('alpha')
        assert len(tracer.events(kind='alpha')) == 2
        assert len(tracer.events(kind='beta')) == 1

    def test_events_limit(self, tracer: RuntimeAuditTracer) -> None:
        for i in range(10):
            tracer.trace('evt')
        assert len(tracer.events(limit=3)) == 3

    def test_jsonl_file_written(self, tracer: RuntimeAuditTracer, tmp_path: Path) -> None:
        tracer.trace('hello')
        log_file = tmp_path / 'runtime_audit.jsonl'
        assert log_file.exists()
        lines = log_file.read_text(encoding='utf-8').strip().split('\n')
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data['kind'] == 'hello'

    def test_summary(self, tracer: RuntimeAuditTracer) -> None:
        tracer.trace('a')
        tracer.trace('b')
        tracer.trace_error('ctx', 'TypeError', 'bad')
        s = tracer.summary()
        assert s['total_events'] == 3
        assert s['in_memory'] == 3
        assert s['errors'] == 1
        assert s['kinds']['error'] == 1
        assert s['enabled'] is True


class TestTypedTraceHelpers:
    """Typed convenience methods."""

    @pytest.fixture()
    def tracer(self) -> RuntimeAuditTracer:
        return RuntimeAuditTracer()

    def test_trace_service_init(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_service_init('db', 123.4, dependencies=['config'])
        assert e['kind'] == 'service_init'
        assert e['data']['service'] == 'db'
        assert e['data']['duration_ms'] == 123.4
        assert e['data']['dependencies'] == ['config']

    def test_trace_service_init_error(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_service_init('db', 50.0, status='error', error='locked')
        assert e['data']['status'] == 'error'
        assert e['data']['error'] == 'locked'

    def test_trace_decision(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_decision(
            'route_selection', 'synaptic_router',
            inputs={'goal': 'translate'}, result='ollama', confidence=0.85,
        )
        assert e['kind'] == 'decision'
        assert e['data']['algorithm'] == 'synaptic_router'
        assert e['data']['confidence'] == 0.85

    def test_trace_external_query(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_external_query(
            'chatgpt', 'completion',
            status='timeout', duration_ms=5000.0,
            error='read timeout',
        )
        assert e['kind'] == 'external_query'
        assert e['data']['target'] == 'chatgpt'
        assert e['data']['status'] == 'timeout'

    def test_trace_permission(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_permission(
            'cloud_reasoning', 'check',
            granted=False, reason='no api key',
        )
        assert e['kind'] == 'permission'
        assert e['data']['granted'] is False

    def test_trace_resource_snapshot(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_resource_snapshot(
            ram_used_pct=75.3, cpu_load=0.45, thread_count=12,
        )
        assert e['kind'] == 'resource_snapshot'
        assert e['data']['ram_used_pct'] == 75.3

    def test_trace_error(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_error('bootstrap', 'ImportError', 'no module named x')
        assert e['kind'] == 'error'
        assert e['data']['error_type'] == 'ImportError'

    def test_trace_ui_event(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_ui_event('page_load', component='EvolutionCenter')
        assert e['kind'] == 'ui_event'
        assert e['data']['component'] == 'EvolutionCenter'


class TestBootReport:
    """Export a structured boot report for AI analysis."""

    @pytest.fixture()
    def tracer(self) -> RuntimeAuditTracer:
        t = RuntimeAuditTracer()
        t.trace_service_init('db', 50.0)
        t.trace_service_init('tool_registry', 200.0)
        t.trace_service_init('world_model', 800.0)
        t.trace_service_init('broken_svc', 10.0, status='error', error='import fail')
        t.trace_external_query('ollama', 'ping', status='ok', duration_ms=100.0)
        t.trace_external_query('chatgpt', 'completion', status='timeout', duration_ms=5000.0, error='timeout')
        t.trace_permission('cloud_reasoning', 'check', granted=False, reason='no key')
        t.trace_error('startup', 'OSError', 'locked')
        return t

    def test_boot_report_structure(self, tracer: RuntimeAuditTracer) -> None:
        report = tracer.export_boot_report()
        assert report['services_initialized'] == 4
        assert len(report['services_failed']) == 1
        assert report['services_failed'][0]['service'] == 'broken_svc'
        assert len(report['services_slow']) == 1  # world_model > 500ms
        assert report['external_queries_attempted'] == 2
        assert len(report['external_queries_failed']) == 1
        assert report['permissions_checked'] == 1
        assert len(report['permissions_denied']) == 1
        assert len(report['errors_during_boot']) == 1

    def test_empty_boot_report(self) -> None:
        t = RuntimeAuditTracer()
        report = t.export_boot_report()
        assert report['services_initialized'] == 0
        assert report['services_failed'] == []


class TestGlobalSingleton:
    def test_get_runtime_tracer_returns_same(self) -> None:
        a = get_runtime_tracer()
        b = get_runtime_tracer()
        assert a is b

    def test_tracer_is_instance(self) -> None:
        assert isinstance(get_runtime_tracer(), RuntimeAuditTracer)


class TestInMemoryLimit:
    def test_max_in_memory_capped(self) -> None:
        t = RuntimeAuditTracer()
        t._max_in_memory = 10
        for i in range(25):
            t.trace('evt', i=i)
        assert len(t.events(limit=100)) == 10

    def test_disabled_tracer_still_keeps_memory(self) -> None:
        import os
        old = os.environ.get('IABV_RUNTIME_TRACE')
        os.environ['IABV_RUNTIME_TRACE'] = '0'
        try:
            t = RuntimeAuditTracer()
            t.trace('test')
            assert len(t.events()) == 1
            assert t._enabled is False
        finally:
            if old is not None:
                os.environ['IABV_RUNTIME_TRACE'] = old
            else:
                os.environ.pop('IABV_RUNTIME_TRACE', None)



def test_trace_returns_file_fsync_ack(tmp_path: Path) -> None:
    import hashlib

    tracer = RuntimeAuditTracer(log_dir=tmp_path)
    event = tracer.trace('durable_event', value='verified')
    acknowledgement = event['durability_ack']

    log_file = tmp_path / 'runtime_audit.jsonl'
    raw_line = log_file.read_bytes()
    disk_event = json.loads(raw_line.decode('utf-8').strip())

    assert acknowledgement['status'] == 'FILE_FSYNCED'
    assert acknowledgement['path'] == 'runtime_audit.jsonl'
    assert acknowledgement['seq'] == event['seq'] == 1
    assert acknowledgement['byte_start'] == 0
    assert acknowledgement['byte_end'] == len(raw_line)
    assert acknowledgement['line_sha256'] == hashlib.sha256(raw_line).hexdigest()
    assert raw_line.endswith(b'\n')
    assert disk_event['kind'] == 'durable_event'
    assert 'durability_ack' not in disk_event
    assert tracer.events()[-1]['durability_ack'] == acknowledgement


def test_trace_fsync_failure_returns_write_failed_ack(tmp_path: Path, monkeypatch) -> None:
    import iabv_v15.services.evolution.runtime_audit_tracer as tracer_module

    def fail_fsync(_fd: int) -> None:
        raise OSError('synthetic fsync failure')

    monkeypatch.setattr(tracer_module.os, 'fsync', fail_fsync)
    tracer = RuntimeAuditTracer(log_dir=tmp_path)

    event = tracer.trace('not_durable_event')
    acknowledgement = event['durability_ack']

    assert acknowledgement['status'] == 'WRITE_FAILED'
    assert acknowledgement['error_type'] == 'OSError'
    assert len(tracer.events()) == 1


def test_trace_without_log_directory_is_memory_only() -> None:
    tracer = RuntimeAuditTracer()

    event = tracer.trace('memory_only_event')

    assert event['durability_ack']['status'] == 'MEMORY_ONLY'
    assert len(tracer.events()) == 1


def test_disabled_trace_returns_disabled_ack(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv('IABV_RUNTIME_TRACE', '0')
    tracer = RuntimeAuditTracer(log_dir=tmp_path)

    event = tracer.trace('disabled_event')

    assert event['durability_ack']['status'] == 'DISABLED'
    assert len(tracer.events()) == 1
    assert not (tmp_path / 'runtime_audit.jsonl').exists()


def test_interaction_resolution_exposes_file_fsync_durability_ack(tmp_path, monkeypatch) -> None:
    from iabv_v15.services.evolution import runtime_audit_tracer
    from iabv_v15.services.evolution.freeze_incident_reporter import ChatInteractionLifecycle

    tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
    tracer.configure(tmp_path)
    monkeypatch.setattr(runtime_audit_tracer, 'get_runtime_tracer', lambda: tracer)
    lifecycle = ChatInteractionLifecycle()
    interaction_id = lifecycle.open_interaction('durability ack test')

    record = lifecycle.resolve_interaction(interaction_id, outcome='resolved', provider='test')

    assert record is not None
    acknowledgement = record['runtime_audit_durability']
    assert acknowledgement['status'] == 'FILE_FSYNCED'
    assert acknowledgement['seq'] == 2
    assert len(acknowledgement['line_sha256']) == 64
    retained = lifecycle.interaction_info(interaction_id)
    assert retained is not None
    assert retained['runtime_audit_durability'] == acknowledgement


def test_interaction_resolution_exposes_fsync_failure_ack(tmp_path, monkeypatch) -> None:
    from iabv_v15.services.evolution import runtime_audit_tracer
    from iabv_v15.services.evolution.freeze_incident_reporter import ChatInteractionLifecycle

    def fail_fsync(_fd: int) -> None:
        raise OSError('synthetic fsync failure')

    monkeypatch.setattr(runtime_audit_tracer.os, 'fsync', fail_fsync)
    tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
    tracer.configure(tmp_path)
    monkeypatch.setattr(runtime_audit_tracer, 'get_runtime_tracer', lambda: tracer)
    lifecycle = ChatInteractionLifecycle()
    interaction_id = lifecycle.open_interaction('durability failure test')

    record = lifecycle.resolve_interaction(interaction_id, outcome='failed', provider='test')

    assert record is not None
    assert record['runtime_audit_durability'] == {
        'status': 'WRITE_FAILED',
        'error_type': 'OSError',
    }
    retained = lifecycle.interaction_info(interaction_id)
    assert retained is not None
    assert retained['runtime_audit_durability']['status'] == 'WRITE_FAILED'


@pytest.mark.parametrize("fail_fsync", [False, True])
def test_audit_consumers_distinguish_receipt_from_recovered_row(
    tmp_path, monkeypatch, fail_fsync,
) -> None:
    from iabv_v15.domain.models import utc_now
    from iabv_v15.infra.persistence.storage import ArtifactStorage
    from iabv_v15.services.evolution import runtime_audit_tracer
    from iabv_v15.services.evolution.control_master_service import ControlMasterService
    from iabv_v15.services.evolution.freeze_incident_reporter import ChatInteractionLifecycle
    from iabv_v15.services.evolution.portable_context_service import PortableContextService

    logs = tmp_path / "data" / "logs"
    tracer = RuntimeAuditTracer(log_dir=str(logs))
    tracer.configure(logs)
    monkeypatch.setattr(runtime_audit_tracer, "get_runtime_tracer", lambda: tracer)
    lifecycle = ChatInteractionLifecycle()
    interaction_id = lifecycle.open_interaction("synthetic interaction")

    def fail(_fd):
        raise OSError("synthetic fsync failure")

    with monkeypatch.context() as m:
        if fail_fsync:
            m.setattr(runtime_audit_tracer.os, "fsync", fail)
        lifecycle.resolve_interaction(interaction_id, outcome="failed", provider="test")

    for active_lifecycle in (lifecycle, None):
        control = ControlMasterService(
            repository=None,
            workspace_root=str(tmp_path),
            chat_interaction_lifecycle=active_lifecycle,
        )
        portable = PortableContextService(
            workspace_root=str(tmp_path),
            storage=ArtifactStorage(str(tmp_path / "artifacts")),
        )
        portable.chat_interaction_lifecycle = active_lifecycle
        if active_lifecycle is None:
            expected = "ACK_UNAVAILABLE"
        else:
            expected = "WRITE_FAILED" if fail_fsync else "FILE_FSYNCED"

        item = control._project_runtime_audit_items(set())[0]
        episode = portable._interaction_lifecycle_section(now=utc_now()).items[0]
        assert item["id"] == f"audit:{interaction_id}"
        assert episode["interaction_id"] == interaction_id
        assert item["runtime_audit_durability"]["status"] == expected
        assert episode["runtime_audit_durability_status"] == expected
        assert item["runtime_audit_durability"]["accepted"] == (expected == "FILE_FSYNCED")
        assert episode["runtime_audit_durability_accepted"] == (expected == "FILE_FSYNCED")
