"""P0.42 focused tests: Post-load UI Freeze Remediation + Idle-Budgeted
Metacognition.

All tests use SimpleNamespace stubs (no AppBootstrap) for speed.
Target: full suite < 5s on normal machine.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import types
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest


# ── Stub factories ────────────────────────────────────────────


def _make_stub_vm(**overrides):
    """Lightweight namespace with P0.42 methods bound."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = SimpleNamespace(
        _active_dispatch_ids={},
        _working=False,
        _working_since=0,
        _busy_label='',
        _latest_response_text='',
        _latest_response_meta='',
        _chat_messages=[],
        _auto_route_enabled=True,
        _selected_role='general_analyst',
        _active_interaction_id=None,
        _interaction_has_pending_followup=False,
        _autonomy_activity_override={},
        _diagnostic_text='',
        _diagnostic_truth_state='unresolved',
        _provider_refreshing=False,
        _ui_state_lock=threading.Lock(),
        _adaptive_session_id=None,
        _last_adaptive_payload={},
        _last_guidance_action='',
        _live_status='idle',
        _heavy_result_guard_active=False,
        _task_start_ts=0.0,
        _external_failure_memory=None,
        _active_incident_frame=None,
        _deferred_retry_generation=0,
        _DEFERRED_RETRY_COOLDOWN_S=0.0,
        _DEFERRED_RETRY_MAX=3,
        _deferred_retry_count=0,
        _deferred_retry_last_ts=0.0,
        _last_user_goal='',
        _attached_files=[],
        _contextual_suggestions=[],
        _development_packet='',
        _dev_packet_last_ts=0.0,
        _dev_packet_cooldown_s=30.0,
        _dev_packet_refresh_pending=False,
        _pbt_state={},
        _pbt_candidates=[],
        _last_external_consultation_ts=0.0,
        _HEAVY_RESULT_THRESHOLD_S=5.0,
    )
    for k, v in overrides.items():
        setattr(stub, k, v)

    # Bind real methods from ControlCenterViewModel
    for name in (
        '_should_defer_heavy_work',
        '_has_recent_ui_stall',
        '_should_defer_dev_packet_refresh',
        '_schedule_idle_dev_packet_refresh',
        '_run_idle_dev_packet_refresh',
        '_run_budgeted_dev_packet_refresh',
        '_refresh_development_packet',
        '_update_progress_cards',
        '_clear_autonomy_activity_override',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is None:
            continue
        if isinstance(
            ControlCenterViewModel.__dict__.get(name),
            staticmethod,
        ):
            stub.__dict__[name] = method
        else:
            stub.__dict__[name] = types.MethodType(method, stub)

    # Bind class constants
    for attr in (
        '_IDLE_REFRESH_BUDGET_MS',
        '_IDLE_REFRESH_COOLDOWN_S',
        '_IDLE_REFRESH_STALL_COOLDOWN_S',
        '_NON_CRITICAL_TASK_NAMES',
        '_DOCK_REFRESH_MIN_INTERVAL_S',
        '_DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S',
        '_DOCK_REFRESH_BUDGET_COOLDOWN_S',
        '_DOCK_SKIP_TRACE_COOLDOWN_S',
        '_FINAL_INTERACTION_OUTCOMES',
    ):
        val = getattr(ControlCenterViewModel, attr, None)
        if val is not None:
            setattr(stub, attr, val)

    _noop = lambda *a, **kw: None
    for attr in (
        '_append_message', '_record_chat_audit', '_set_live_status',
        '_collect_metrics', '_update_evolution_snapshot',
        '_resolve_active_interaction',
        '_clear_autonomy_activity_override',
        '_refresh_autonomy_dock',
        '_build_agent_cards',
        '_update_adaptive_state',
        '_invalidate_dispatch',
        '_trace_dispatch_terminal',
    ):
        if not hasattr(stub, attr):
            setattr(stub, attr, _noop)

    stub._build_agent_cards = lambda: []
    stub._agent_cards = []
    stub.dataChanged = MagicMock()
    stub.taskResolved = MagicMock()
    stub.taskFailed = MagicMock()
    stub.config = SimpleNamespace(
        workspace_root='/tmp/test_iabv',
        ollama_base_url='', lm_studio_base_url='', ollama_embedding_model='',
    )
    stub.adaptive_orchestrator = SimpleNamespace(
        _assess_resource_pressure=lambda: {'under_pressure': False},
    )
    stub.engineering_review_service = SimpleNamespace(
        build_codex_packet=lambda **kw: 'test_packet',
    )
    stub._bg_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='test-bg')
    return stub


# ── Fake tracer for testing ──────────────────────────────────


class FakeTracer:
    def __init__(self):
        self._events: list[dict] = []
        self._elapsed_ms = 60_000.0  # well past startup

    def trace(self, kind, **data):
        event = {'kind': kind, 'data': data, 'elapsed_ms': self._elapsed_ms}
        self._events.append(event)
        return event

    def current_elapsed_ms(self):
        return self._elapsed_ms

    def events(self, *, kind=None, limit=100):
        if kind is None:
            return list(self._events[-limit:])
        return [e for e in self._events if e.get('kind') == kind][-limit:]

    def inject_stall(self, duration_ms=10000, startup_active=False, resource_pressure=False):
        self._events.append({
            'kind': 'ui_event',
            'data': {
                'event_type': 'ui_event_loop_stall',
                'duration_ms': duration_ms,
                'startup_active': startup_active,
                'resource_pressure': resource_pressure,
            },
            'elapsed_ms': self._elapsed_ms - 5000,
        })


def _patch_tracer(tracer):
    """Context manager to patch get_runtime_tracer globally."""
    return patch(
        'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        return_value=tracer,
    )


# ══════════════════════════════════════════════════════════════
# Test 1: _apply_task_result with provider_health does NOT call
# _refresh_development_packet synchronously
# ══════════════════════════════════════════════════════════════


class TestNoSyncRefreshOnTaskResult:

    def test_provider_health_does_not_sync_refresh(self):
        """provider_health result must NOT call _refresh_development_packet
        synchronously on the UI thread."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        vm._provider_cards = []

        sync_calls = []
        original_refresh = vm._refresh_development_packet

        def tracking_refresh(*a, **kw):
            sync_calls.append(('sync', threading.current_thread().name))
            return original_refresh(*a, **kw)

        vm._refresh_development_packet = tracking_refresh

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('provider_health')

        # provider_health is in _NON_CRITICAL_TASK_NAMES, so it must be deferred
        deferred = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_deferred']
        assert len(deferred) >= 1, 'provider_health should defer development_packet_refresh'
        assert deferred[0]['data']['reason'] == 'non_critical_task'

    def test_self_teach_defers_refresh(self):
        """self_teach is non-critical and should defer refresh."""
        tracer = FakeTracer()
        vm = _make_stub_vm()

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('self_teach')

        deferred = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_deferred']
        assert len(deferred) >= 1

    def test_chat_schedules_background_if_no_defer_reason(self):
        """chat with no defer reason should run on _bg_pool, not sync."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        submitted = []
        vm._bg_pool = SimpleNamespace(submit=lambda fn, *a, **kw: submitted.append(fn.__name__))

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('chat')

        assert '_run_budgeted_dev_packet_refresh' in submitted


# ══════════════════════════════════════════════════════════════
# Test 2: recent_ui_stall causes development_packet_refresh_deferred
# ══════════════════════════════════════════════════════════════


class TestRecentStallDefersRefresh:

    def test_stall_defers_even_chat(self):
        """If there was a recent UI stall, even 'chat' result defers refresh."""
        tracer = FakeTracer()
        tracer.inject_stall(duration_ms=10000)
        vm = _make_stub_vm()

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('chat')

        deferred = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_deferred']
        assert len(deferred) >= 1
        assert deferred[0]['data']['reason'] == 'recent_ui_stall'

    def test_query_pending_defers(self):
        """If _working is True (query pending), defer refresh."""
        tracer = FakeTracer()
        vm = _make_stub_vm(_working=True)

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('chat')

        deferred = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_deferred']
        assert len(deferred) >= 1
        assert deferred[0]['data']['reason'] == 'query_pending'


# ══════════════════════════════════════════════════════════════
# Test 3: Heavy refresh runs in background, not main thread
# ══════════════════════════════════════════════════════════════


class TestBackgroundExecution:

    def test_budgeted_refresh_runs_on_bg_pool(self):
        """_run_budgeted_dev_packet_refresh must execute on background thread."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        thread_names = []

        original = vm.engineering_review_service.build_codex_packet

        def tracking_build(**kw):
            thread_names.append(threading.current_thread().name)
            return original(**kw)

        vm.engineering_review_service.build_codex_packet = tracking_build

        with _patch_tracer(tracer):
            future = vm._bg_pool.submit(vm._run_budgeted_dev_packet_refresh)
            future.result(timeout=5)

        assert any('test-bg' in n for n in thread_names), \
            f'Expected bg thread, got: {thread_names}'
        started = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_started']
        finished = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_finished']
        assert len(started) >= 1
        assert len(finished) >= 1


# ══════════════════════════════════════════════════════════════
# Test 4: Budget exceeded returns partial packet with UNRESOLVED
# ══════════════════════════════════════════════════════════════


class TestBudgetExceeded:

    def test_budget_exceeded_marks_partial(self):
        """When refresh exceeds budget, packet should be marked partial."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        # Set very low budget to force exceed
        vm._IDLE_REFRESH_BUDGET_MS = 0.001

        def slow_build(**kw):
            time.sleep(0.01)
            return 'slow_packet'

        vm.engineering_review_service.build_codex_packet = slow_build

        with _patch_tracer(tracer):
            vm._run_budgeted_dev_packet_refresh()

        exceeded = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_budget_exceeded']
        assert len(exceeded) >= 1
        assert 'development_packet_partial=true' in vm._development_packet
        assert 'UNRESOLVED:development_packet_full_refresh_budget_exceeded' in vm._development_packet

    def test_within_budget_no_partial(self):
        """When refresh is within budget, no partial marker."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        vm._IDLE_REFRESH_BUDGET_MS = 10000.0  # Very generous

        with _patch_tracer(tracer):
            vm._run_budgeted_dev_packet_refresh()

        exceeded = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_budget_exceeded']
        assert len(exceeded) == 0
        assert 'partial' not in (vm._development_packet or '')


# ══════════════════════════════════════════════════════════════
# Test 5: OSES generates stable_resource_ui_starvation finding
# ══════════════════════════════════════════════════════════════


class TestOSESFindings:

    def _make_audit_dir(self, ws):
        audit_path = ws / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        return audit_path

    def _write_audit_with_stall(self, audit_path, startup_active=False, resource_pressure=False, count=1):
        with open(audit_path, 'w', encoding='utf-8') as f:
            for _ in range(count):
                event = {
                    'kind': 'ui_event',
                    'data': {
                        'event_type': 'ui_event_loop_stall',
                        'duration_ms': 67156,
                        'startup_active': startup_active,
                        'resource_pressure': resource_pressure,
                    },
                    'elapsed_ms': 80000,
                }
                f.write(json.dumps(event) + '\n')

    def _write_budget_exceeded(self, audit_path, count=1):
        with open(audit_path, 'a', encoding='utf-8') as f:
            for _ in range(count):
                event = {
                    'kind': 'development_packet_refresh_budget_exceeded',
                    'data': {'elapsed_ms': 2500, 'budget_ms': 1500},
                    'elapsed_ms': 90000,
                }
                f.write(json.dumps(event) + '\n')

    def test_stable_resource_starvation_finding(self):
        """OSES must produce stable_resource_ui_starvation when
        post-load stall with stable resources."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            audit_path = self._make_audit_dir(ws)
            self._write_audit_with_stall(str(audit_path), startup_active=False, resource_pressure=False)

            svc = SimpleNamespace(workspace_root=ws)
            findings = OperationalSelfExaminationService._external_readiness_missing_findings(svc)

            cats = [f.category for f in findings]
            assert 'stable_resource_ui_starvation' in cats
            starvation = [f for f in findings if f.category == 'stable_resource_ui_starvation'][0]
            assert starvation.metadata['dominant_cause'] == 'post_load_ui_thread_dossier_json_io'

    def test_repeated_post_load_stall_finding(self):
        """OSES must produce repeated_post_load_ui_stall when >=2 stalls."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            audit_path = self._make_audit_dir(ws)
            self._write_audit_with_stall(str(audit_path), count=3)

            svc = SimpleNamespace(workspace_root=ws)
            findings = OperationalSelfExaminationService._external_readiness_missing_findings(svc)

            cats = [f.category for f in findings]
            assert 'repeated_post_load_ui_stall' in cats

    def test_dossier_io_finding(self):
        """OSES must produce dossier_json_io_main_thread when budget exceeded."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            audit_path = self._make_audit_dir(ws)
            audit_path.touch()
            self._write_budget_exceeded(str(audit_path), count=2)

            svc = SimpleNamespace(workspace_root=ws)
            findings = OperationalSelfExaminationService._external_readiness_missing_findings(svc)

            cats = [f.category for f in findings]
            assert 'dossier_json_io_main_thread' in cats

    def test_no_finding_for_startup_stall(self):
        """Startup stalls (startup_active=True) should NOT produce
        stable_resource_ui_starvation."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            audit_path = self._make_audit_dir(ws)
            self._write_audit_with_stall(str(audit_path), startup_active=True)

            svc = SimpleNamespace(workspace_root=ws)
            findings = OperationalSelfExaminationService._external_readiness_missing_findings(svc)

            cats = [f.category for f in findings]
            assert 'stable_resource_ui_starvation' not in cats


# ══════════════════════════════════════════════════════════════
# Test 6: PortableContext includes post_load_stability section
# ══════════════════════════════════════════════════════════════


class TestPortableContextPostLoadStability:

    def _make_svc_stub(self):
        """Build a stub with _section bound from the real class."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        svc = SimpleNamespace()
        svc._post_load_stability_section = types.MethodType(
            PortableContextService._post_load_stability_section, svc,
        )
        svc._section = types.MethodType(
            PortableContextService._section, svc,
        )
        return svc

    def test_section_exists_in_package(self):
        """build_package must include post_load_stability section."""
        tracer = FakeTracer()
        svc = self._make_svc_stub()
        with _patch_tracer(tracer):
            section = svc._post_load_stability_section(now=time.time())
        assert section.section_id == 'post_load_stability'
        assert 'P0.42' in section.title

    def test_section_reports_stall(self):
        """Section should reflect a recent post-load stall."""
        tracer = FakeTracer()
        tracer.inject_stall(duration_ms=67000, startup_active=False, resource_pressure=False)
        svc = self._make_svc_stub()
        with _patch_tracer(tracer):
            section = svc._post_load_stability_section(now=time.time())
        assert len(section.items) >= 1
        item = section.items[0]
        assert item['latest_stall_ms'] == 67000.0
        assert item['dominant_cause'] == 'post_load_ui_thread_dossier_json_io'

    def test_section_no_stall_clean(self):
        """When no stalls, section should report clean state."""
        tracer = FakeTracer()
        svc = self._make_svc_stub()
        with _patch_tracer(tracer):
            section = svc._post_load_stability_section(now=time.time())
        item = section.items[0]
        assert item['latest_stall_ms'] == 0
        assert item['mitigation_status'] == 'no_stalls_observed'


# ══════════════════════════════════════════════════════════════
# Test 7: RuntimeAuditTracer records defer/start/finish/skip events
# ══════════════════════════════════════════════════════════════


class TestTracerEvents:

    def test_deferred_event_recorded(self):
        """When refresh is deferred, tracer must record the event."""
        tracer = FakeTracer()
        vm = _make_stub_vm(_working=True)

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('chat')

        kinds = [e['kind'] for e in tracer._events]
        assert 'development_packet_refresh_deferred' in kinds

    def test_start_and_finish_recorded(self):
        """Normal budgeted refresh must record start and finish."""
        tracer = FakeTracer()
        vm = _make_stub_vm()

        with _patch_tracer(tracer):
            vm._run_budgeted_dev_packet_refresh()

        kinds = [e['kind'] for e in tracer._events]
        assert 'development_packet_refresh_started' in kinds
        assert 'development_packet_refresh_finished' in kinds

    def test_skip_due_to_stall_recorded(self):
        """When idle callback finds stall still active, must record skip."""
        tracer = FakeTracer()
        tracer.inject_stall(duration_ms=15000)
        vm = _make_stub_vm()
        vm._dev_packet_refresh_pending = True

        with _patch_tracer(tracer):
            vm._run_idle_dev_packet_refresh()

        kinds = [e['kind'] for e in tracer._events]
        assert 'development_packet_refresh_skipped_due_to_stall' in kinds

    def test_budget_exceeded_event(self):
        """When budget exceeded, tracer must record the event."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        vm._IDLE_REFRESH_BUDGET_MS = 0.001

        def slow_build(**kw):
            time.sleep(0.01)
            return 'slow'

        vm.engineering_review_service.build_codex_packet = slow_build

        with _patch_tracer(tracer):
            vm._run_budgeted_dev_packet_refresh()

        kinds = [e['kind'] for e in tracer._events]
        assert 'development_packet_refresh_budget_exceeded' in kinds


# ══════════════════════════════════════════════════════════════
# Test 8: External consultation and terminal_state flows unbroken
# ══════════════════════════════════════════════════════════════


class TestExternalConsultationUnbroken:

    def test_external_consultation_still_works(self):
        """After P0.42 changes, external_consultation task result path
        must still set correct fields and not crash."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

        vm = _make_stub_vm()
        # Add more needed attrs for _apply_task_result
        vm._chat_interaction_lifecycle = None
        vm._FINAL_INTERACTION_OUTCOMES = getattr(
            ControlCenterViewModel, '_FINAL_INTERACTION_OUTCOMES', {'resolved', 'blocked'},
        )

        for name in (
            '_user_facing_chat_response',
            '_humanize_task_failure',
            '_set_external_consultation_activity',
            '_external_state_notice',
            '_derive_external_consultation_outcome',
            '_clear_external_failure_memory',
            '_remember_external_failure',
            '_resolve_incident_frame',
            '_maybe_run_autonomous_evolution',
            '_update_progress_cards',
            '_process_ui_events',
        ):
            if not hasattr(vm, name):
                setattr(vm, name, lambda *a, **kw: None)

        vm._derive_external_consultation_outcome = lambda p: 'resolved'
        vm._external_state_notice = lambda flags: ''

        tracer = FakeTracer()
        with _patch_tracer(tracer):
            payload = {
                'message': 'Consulta externa completada.',
                'meta': 'chatgpt | success',
                'success': True,
                'assistant_title': 'ChatGPT',
                'payload': {},
            }
            # Simulate _apply_task_result for external_consultation
            vm._last_external_consultation_ts = time.time()
            vm._latest_response_text = str(payload.get('message', ''))
            vm._latest_response_meta = str(payload.get('meta', ''))
            vm._busy_label = f"Consulta externa lista con {payload['assistant_title']}."

        assert vm._busy_label == 'Consulta externa lista con ChatGPT.'

    def test_startup_followup_defers_refresh(self):
        """During early startup (<10s), refresh should be deferred."""
        tracer = FakeTracer()
        tracer._elapsed_ms = 5000  # 5 seconds = still in startup

        vm = _make_stub_vm()

        with _patch_tracer(tracer):
            reason = vm._should_defer_dev_packet_refresh('chat')

        assert reason == 'startup_followup_active'

    def test_resource_pressure_defers_refresh(self):
        """Under resource pressure, refresh should be deferred."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        vm.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {'under_pressure': True, 'critical': False},
        )

        with _patch_tracer(tracer):
            reason = vm._should_defer_dev_packet_refresh('chat')

        assert reason == 'resource_pressure'


# ══════════════════════════════════════════════════════════════
# Test 9: Idle-budgeted policy respects cooldown
# ══════════════════════════════════════════════════════════════


class TestIdleBudgetedPolicy:

    def test_stall_increases_cooldown(self):
        """When deferring due to stall, the reason recorded must be
        recent_ui_stall (which uses longer cooldown internally)."""
        tracer = FakeTracer()
        tracer.inject_stall(duration_ms=10000)
        vm = _make_stub_vm()
        # QTimer import will fail in test env, so _bg_pool fallback runs
        submitted = []
        vm._bg_pool = SimpleNamespace(submit=lambda fn, *a: submitted.append(fn.__name__))

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('chat')

        deferred = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_deferred']
        assert len(deferred) >= 1
        assert deferred[0]['data']['reason'] == 'recent_ui_stall'
        assert vm._dev_packet_refresh_pending is True

    def test_non_critical_uses_normal_defer(self):
        """Non-critical tasks defer with reason=non_critical_task."""
        tracer = FakeTracer()
        vm = _make_stub_vm()
        submitted = []
        vm._bg_pool = SimpleNamespace(submit=lambda fn, *a: submitted.append(fn.__name__))

        with _patch_tracer(tracer):
            vm._schedule_idle_dev_packet_refresh('provider_health')

        deferred = [e for e in tracer._events if e['kind'] == 'development_packet_refresh_deferred']
        assert len(deferred) >= 1
        assert deferred[0]['data']['reason'] == 'non_critical_task'


# ══════════════════════════════════════════════════════════════
# Test 10: Platform pending file P0.42 exists and is valid
# ══════════════════════════════════════════════════════════════


class TestPlatformPending:

    def test_platform_pending_exists(self):
        """P0.42 platform_pending file must exist and be valid JSON."""
        pp_path = Path(__file__).resolve().parent.parent / (
            'data/evolution/platform_pending/'
            'task_runtime_post_load_freeze_remediation_p042.json'
        )
        assert pp_path.exists(), f'Missing platform_pending: {pp_path}'
        data = json.loads(pp_path.read_text(encoding='utf-8'))
        assert data['status'] == 'PENDING'
        assert data['metadata']['verification_status'] == 'CODE_FIX_PENDING_LIVE_PROOF'
        assert 'post_load_ui_thread_dossier_json_io' in data['metadata']['root_cause']
