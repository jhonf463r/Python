"""P0.21x-R51: Runtime lifecycle observability tests.

Tests for runtime_process_started, runtime_process_exit, and runtime_process_crash events.
Verifies that IABV can reliably know:
RUNTIME STARTED → RUNTIME ALIVE → RUNTIME EXITED NORMALLY or RUNTIME CRASHED
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from iabv_v15.services.evolution.runtime_audit_tracer import (
    RuntimeAuditTracer,
    get_runtime_tracer,
)


class TestRuntimeProcessStarted:
    """Tests for runtime_process_started event emission."""

    def test_trace_runtime_process_started_emits_event(self):
        """Verify trace_runtime_process_started emits correct event."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_started(
            pid=12345,
            workspace='/test/workspace',
            branch='test-branch',
            head='abc123',
        )

        assert event['kind'] == 'runtime_process_started'
        assert event['data']['pid'] == 12345
        assert event['data']['workspace'] == '/test/workspace'
        assert event['data']['branch'] == 'test-branch'
        assert event['data']['head'] == 'abc123'

    def test_trace_runtime_process_started_defaults_to_current_pid(self):
        """Verify trace_runtime_process_started defaults to current PID."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_started()

        assert event['kind'] == 'runtime_process_started'
        assert event['data']['pid'] == os.getpid()

    def test_trace_runtime_process_started_includes_timestamp(self):
        """Verify event includes timestamp and elapsed_ms."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_started()

        assert 'ts' in event
        assert 'elapsed_ms' in event
        assert event['elapsed_ms'] >= 0


class TestRuntimeProcessExit:
    """Tests for runtime_process_exit event emission."""

    def test_trace_runtime_process_exit_emits_event(self):
        """Verify trace_runtime_process_exit emits correct event."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_exit(
            exit_code=0,
            reason='normal_shutdown',
            duration_ms=12345.67,
        )

        assert event['kind'] == 'runtime_process_exit'
        assert event['data']['exit_code'] == 0
        assert event['data']['reason'] == 'normal_shutdown'
        assert event['data']['duration_ms'] == 12345.7  # rounded

    def test_trace_runtime_process_exit_with_nonzero_exit(self):
        """Verify trace_runtime_process_exit handles nonzero exit codes."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_exit(
            exit_code=1,
            reason='user_interrupt',
            duration_ms=5000.0,
        )

        assert event['kind'] == 'runtime_process_exit'
        assert event['data']['exit_code'] == 1
        assert event['data']['reason'] == 'user_interrupt'

    def test_trace_runtime_process_exit_reason_truncation(self):
        """Verify long reason strings are truncated."""
        tracer = RuntimeAuditTracer()
        long_reason = 'x' * 300
        event = tracer.trace_runtime_process_exit(reason=long_reason)

        assert len(event['data']['reason']) <= 200


class TestRuntimeProcessCrash:
    """Tests for runtime_process_crash event emission."""

    def test_trace_runtime_process_crash_emits_event(self):
        """Verify trace_runtime_process_crash emits correct event."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_crash(
            error_type='ValueError',
            error_message='test error',
            traceback_summary='line 1\nline 2\nline 3',
        )

        assert event['kind'] == 'runtime_process_crash'
        assert event['data']['error_type'] == 'ValueError'
        assert event['data']['error_message'] == 'test error'
        assert event['data']['traceback_summary'] == 'line 1\nline 2\nline 3'

    def test_trace_runtime_process_crash_message_truncation(self):
        """Verify long error messages are truncated."""
        tracer = RuntimeAuditTracer()
        long_message = 'x' * 600
        event = tracer.trace_runtime_process_crash(error_message=long_message)

        assert len(event['data']['error_message']) <= 500

    def test_trace_runtime_process_crash_traceback_truncation(self):
        """Verify long tracebacks are truncated."""
        tracer = RuntimeAuditTracer()
        long_traceback = 'x' * 1200
        event = tracer.trace_runtime_process_crash(traceback_summary=long_traceback)

        assert len(event['data']['traceback_summary']) <= 1000


class TestLifecycleEventIntegration:
    """Integration tests for lifecycle events."""

    def test_lifecycle_events_have_sequence_numbers(self):
        """Verify lifecycle events have incrementing sequence numbers."""
        tracer = RuntimeAuditTracer()
        start_event = tracer.trace_runtime_process_started()
        exit_event = tracer.trace_runtime_process_exit()

        assert start_event['seq'] == 1
        assert exit_event['seq'] == 2

    def test_lifecycle_events_can_be_filtered_by_kind(self):
        """Verify lifecycle events can be filtered from in-memory events."""
        tracer = RuntimeAuditTracer()
        tracer.trace_runtime_process_started()
        tracer.trace_service_init('test_service', 100.0)
        tracer.trace_runtime_process_exit()

        started_events = tracer.events(kind='runtime_process_started')
        exit_events = tracer.events(kind='runtime_process_exit')

        assert len(started_events) == 1
        assert len(exit_events) == 1

    def test_global_tracer_singleton(self):
        """Verify get_runtime_tracer returns singleton."""
        tracer1 = get_runtime_tracer()
        tracer2 = get_runtime_tracer()

        assert tracer1 is tracer2


class TestNegativeCases:
    """Tests for negative cases and edge conditions."""

    def test_normal_exit_not_mislabeled_as_crash(self):
        """Verify normal exit is not emitted as crash."""
        tracer = RuntimeAuditTracer()
        tracer.trace_runtime_process_exit(exit_code=0, reason='normal_shutdown')

        crash_events = tracer.events(kind='runtime_process_crash')
        exit_events = tracer.events(kind='runtime_process_exit')

        assert len(crash_events) == 0
        assert len(exit_events) == 1
        assert exit_events[0]['data']['exit_code'] == 0

    def test_crash_not_emitted_on_normal_path(self):
        """Verify crash event is not emitted on normal shutdown."""
        tracer = RuntimeAuditTracer()
        tracer.trace_runtime_process_exit()

        crash_events = tracer.events(kind='runtime_process_crash')
        assert len(crash_events) == 0

    def test_disappearance_without_proof_not_classified(self):
        """Verify disappearance without explicit exit/crash is not classified.

        The tracer does NOT infer termination from disappearance.
        Only explicit runtime_process_exit or runtime_process_crash events
        are authoritative.
        """
        tracer = RuntimeAuditTracer()
        tracer.trace_runtime_process_started()

        # Simulate process disappearance without explicit event
        # The tracer should NOT auto-generate an exit/crash event
        all_events = tracer.events()
        exit_events = tracer.events(kind='runtime_process_exit')
        crash_events = tracer.events(kind='runtime_process_crash')

        assert len(exit_events) == 0
        assert len(crash_events) == 0
        assert len(all_events) == 1  # Only started event


class TestExistingBehaviorPreserved:
    """Tests that existing RuntimeAuditTracer behavior remains intact."""

    def test_existing_trace_methods_still_work(self):
        """Verify existing trace methods are not affected."""
        tracer = RuntimeAuditTracer()

        # Test existing methods still work
        tracer.trace_service_init('test', 100.0)
        tracer.trace_decision('test_point', 'test_algo')
        tracer.trace_external_query('test_target', 'test_op')
        tracer.trace_permission('test_perm', 'test_action')
        tracer.trace_resource_snapshot(ram_used_pct=50.0)
        tracer.trace_error('test_context', 'TypeError', 'test message')

        events = tracer.events()
        assert len(events) == 6
        assert events[0]['kind'] == 'service_init'
        assert events[1]['kind'] == 'decision'
        assert events[2]['kind'] == 'external_query'
        assert events[3]['kind'] == 'permission'
        assert events[4]['kind'] == 'resource_snapshot'
        assert events[5]['kind'] == 'error'

    def test_trace_core_method_still_works(self):
        """Verify core trace method is not affected."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace('custom_kind', custom_field='custom_value')

        assert event['kind'] == 'custom_kind'
        assert event['data']['custom_field'] == 'custom_value'

    def test_events_query_still_works(self):
        """Verify events query methods are not affected."""
        tracer = RuntimeAuditTracer()
        tracer.trace_runtime_process_started()
        tracer.trace_service_init('test', 100.0)
        tracer.trace_runtime_process_exit()

        all_events = tracer.events()
        assert len(all_events) == 3

        started_events = tracer.events(kind='runtime_process_started')
        assert len(started_events) == 1

        recent_events = tracer.events(limit=2)
        assert len(recent_events) == 2

    def test_summary_still_works(self):
        """Verify summary method is not affected."""
        tracer = RuntimeAuditTracer()
        tracer.trace_runtime_process_started()
        tracer.trace_error('test', 'Error', 'message')

        summary = tracer.summary()
        assert 'total_events' in summary
        assert summary['total_events'] == 2
        assert summary['errors'] == 1


class TestMainPyIntegration:
    """Tests for main.py lifecycle event emission."""

    def test_main_py_imports_runtime_tracer(self):
        """Verify main.py can import and use RuntimeAuditTracer."""
        # Verify the import path works
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
        tracer = get_runtime_tracer()
        assert tracer is not None
        assert isinstance(tracer, RuntimeAuditTracer)

    def test_main_py_started_event_structure(self):
        """Verify runtime_process_started event has correct structure."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_started(
            pid=os.getpid(),
            workspace=str(Path.cwd()),
        )

        # Verify the event structure matches what main.py would emit
        assert event['kind'] == 'runtime_process_started'
        assert 'pid' in event['data']
        assert 'workspace' in event['data']
        assert 'ts' in event
        assert 'elapsed_ms' in event
        assert 'seq' in event

    def test_main_py_crash_event_structure(self):
        """Verify runtime_process_crash event has correct structure."""
        tracer = RuntimeAuditTracer()
        event = tracer.trace_runtime_process_crash(
            error_type='ValueError',
            error_message='test error',
            traceback_summary='test traceback',
        )

        # Verify the event structure matches what main.py would emit
        assert event['kind'] == 'runtime_process_crash'
        assert 'error_type' in event['data']
        assert 'error_message' in event['data']
        assert 'traceback_summary' in event['data']
        assert 'ts' in event
        assert 'elapsed_ms' in event
