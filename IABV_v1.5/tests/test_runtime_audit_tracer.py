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


def test_governed_browser_trace_persists_only_safe_launch_reference(tmp_path: Path) -> None:
    tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
    tracer.configure(tmp_path)
    desktop_target = r'C:\\Users\\Owner\\AppData\\Local\\Programs\\Codex\\Codex.exe'
    web_target = 'https://chatgpt.com/share/private-path?token=private-web-token'

    desktop_event = tracer.trace_governed_browser_session(
        'started',
        assistant_kind='codex',
        launch_target=desktop_target,
    )
    web_event = tracer.trace_governed_browser_session(
        'result',
        assistant_kind='chatgpt',
        launch_target=web_target,
    )

    assert desktop_event['data']['launch_target_ref'] == 'desktop:codex'
    assert web_event['data']['launch_target_ref'] == 'web:chatgpt'
    assert 'launch_target' not in desktop_event['data']
    assert 'launch_target' not in web_event['data']
    persisted = (tmp_path / 'runtime_audit.jsonl').read_text(encoding='utf-8')
    assert desktop_target not in persisted
    assert web_target not in persisted
    assert 'private-web-token' not in persisted



def test_governed_browser_trace_minimizes_endpoint_profile_reason_and_extra(tmp_path: Path) -> None:
    tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
    tracer.configure(tmp_path)
    raw_endpoint = 'http://operator:private-pass@localhost:9223/devtools/browser/private-id?token=private-cdp-token'
    raw_profile = r'C:\Users\Owner\chatgpt_program_session\browser_profile'
    raw_reason = r'failed at C:\Users\Owner\private-state.json alice@example.com Bearer private-bearer'

    governed = tracer.trace_governed_browser_session(
        'started',
        assistant_kind='ChatGPT',
        cdp_url=raw_endpoint,
        profile_label=raw_profile,
        launch_target='https://chatgpt.com/private?token=private-web-token',
        reason=raw_reason,
        extra_profile_path=raw_profile,
        extra_secret='private-extra-secret',
    )
    data = governed['data']
    assert data['assistant_kind'] == 'chatgpt'
    assert data['cdp_endpoint_ref'] == 'http://localhost:9223'
    assert data['profile_ref'] == 'chatgpt_profile'
    assert data['launch_target_ref'] == 'web:chatgpt'
    assert data['reason_code'] == 'other'
    assert data['extra_fields_omitted'] is True
    assert 'cdp_url' not in data
    assert 'profile_label' not in data
    assert 'extra_profile_path' not in data
    assert 'extra_secret' not in data

    unbound = tracer.trace_security_window_unbound(
        incident_id='inc-p072-1',
        assistant_kind='chatgpt',
        profile_label=raw_profile,
        reason=raw_reason,
    )
    assert unbound['data']['profile_ref'] == 'chatgpt_profile'
    assert unbound['data']['reason_code'] == 'other'
    assert 'profile_label' not in unbound['data']

    fallback = tracer.trace_visible_fallback(
        'blocked_no_target',
        assistant_kind='chatgpt',
        reason=raw_reason,
        target_available=False,
        diagnostic_path=raw_profile,
    )
    assert fallback['data']['reason_code'] == 'other'
    assert fallback['data']['extra_fields_omitted'] is True
    assert 'diagnostic_path' not in fallback['data']

    persisted = (tmp_path / 'runtime_audit.jsonl').read_text(encoding='utf-8')
    for private_value in (
        raw_endpoint,
        raw_profile,
        raw_reason,
        'private-pass',
        'private-cdp-token',
        'private-web-token',
        'private-bearer',
        'private-extra-secret',
        'alice@example.com',
    ):
        assert private_value not in persisted
    assert RuntimeAuditTracer._safe_cdp_endpoint_ref('http://10.0.0.7:9223/private') == 'remote_cdp_endpoint'



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



def test_trace_memory_only_ack_is_not_accepted(tmp_path: Path) -> None:
    from iabv_v15.services.evolution.runtime_audit_tracer import validate_durability_ack

    tracer = RuntimeAuditTracer()
    event = tracer.trace("memory_only_event")
    acknowledgement = event["durability_ack"]
    assert acknowledgement["status"] == "MEMORY_ONLY"
    assert validate_durability_ack(
        acknowledgement, expected_seq=event["seq"]
    )["accepted"] is False


def test_trace_ack_validator_rejects_malformed_receipts() -> None:
    from iabv_v15.services.evolution.runtime_audit_tracer import validate_durability_ack

    valid = {
        "status": "FILE_FSYNCED",
        "path": "runtime_audit.jsonl",
        "seq": 4,
        "byte_start": 10,
        "byte_end": 100,
        "line_sha256": "a" * 64,
    }
    assert validate_durability_ack(valid, expected_seq=4)["accepted"] is True
    assert validate_durability_ack(
        valid, expected_seq=4, expected_line_sha256="a" * 64,
        expected_byte_start=10, expected_byte_end=100,
    )["verification"] == "TRACER_RECEIPT_MATCHED_TO_READ_ROW"
    assert validate_durability_ack(
        valid, expected_seq=4, expected_line_sha256="b" * 64,
        expected_byte_start=10, expected_byte_end=100,
    )["status"] == "ACK_INVALID"
    assert validate_durability_ack(
        valid, expected_seq=4, expected_line_sha256="a" * 64,
        expected_byte_start=9, expected_byte_end=100,
    )["status"] == "ACK_INVALID"
    assert validate_durability_ack(valid, expected_seq=5)["status"] == "ACK_INVALID"
    assert validate_durability_ack(valid, expected_seq=True)["status"] == "ACK_INVALID"
    assert validate_durability_ack(valid, expected_seq="4")["status"] == "ACK_INVALID"
    assert validate_durability_ack({**valid, "line_sha256": "bad"})["status"] == "ACK_INVALID"
    assert validate_durability_ack({**valid, "path": "../runtime_audit.jsonl"})["status"] == "ACK_INVALID"


def test_trace_write_failure_returns_explicit_non_durable_ack(tmp_path: Path, monkeypatch) -> None:
    from pathlib import Path as _Path

    tracer = RuntimeAuditTracer(log_dir=tmp_path)
    original_open = _Path.open

    def fail_log_write(self, *args, **kwargs):
        if self.name == "runtime_audit.jsonl":
            raise PermissionError("synthetic denied write")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(_Path, "open", fail_log_write)
    event = tracer.trace("write_failure_event")
    assert event["durability_ack"]["status"] == "WRITE_FAILED"
    assert tracer.events()[-1]["kind"] == "write_failure_event"
