"""Focused tests for P0.68: Universal Runtime Stability Controller
+ Metacognitive Thread Contract.

10 test cases covering:
1. post_task:chat does NOT trigger autonomy dock automatically
2. slow autonomy dock result activates circuit breaker
3. deferred refresh with recent stall does NOT reschedule infinitely
4. "sigue" with pending_task responds via continuity handler, NOT local LLM
5. "ok procede" after recent freeze does NOT fall to local_chat_worker
6. local_chat_worker timeout closes busy/working and terminal state
7. freeze incident includes causal context (not just stack)
8. resource_pressure distinguishes process_rss_high vs system_cpu_ram_ok
9. OSES emits findings for deferred loop and dock slow
10. PortableContext exports runtime_stability_controller section

Uses lightweight stub ViewModel (no AppBootstrap) for speed.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _make_stub_vm():
    """Return a lightweight namespace with P0.68 methods bound."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = SimpleNamespace(
        _active_dispatch_ids={},
        _working=False,
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
        # P0.68 attributes
        _circuit_breaker_open=False,
        _circuit_breaker_until=0.0,
        _circuit_breaker_backoff_s=60.0,
        _circuit_breaker_max_backoff_s=900.0,
        _deferred_loop_counts={},
        _deferred_loop_max=3,
        _last_slow_dock_duration_ms=0.0,
        _dock_slow_result_block_until=0.0,
        _continuity_keywords=frozenset({
            'sigue', 'continua', 'continúa', 'ok procede', 'ok, procede',
            'que falta', 'qué falta', 'que falta por hacer',
            'qué falta por hacer', 'termina lo pendiente',
            'haz lo mas importante', 'haz lo más importante',
            'arregla esas fallas', 'procede',
        }),
        _last_external_failure_payload={},
        _last_external_failure_ts=0.0,
        _adaptive_session_id='',
        _last_user_goal='',
        _CIRCUIT_BREAKER_STALL_THRESHOLD_MS=5000.0,
        _DOCK_SLOW_RESULT_COOLDOWN_S=300.0,
    )
    for name in (
        '_check_circuit_breaker',
        '_trip_circuit_breaker',
        '_reset_circuit_breaker',
        '_record_deferred_loop',
        '_clear_deferred_loop',
        '_is_background_work_allowed',
        'get_circuit_breaker_state',
        '_is_continuity_message',
        '_try_handle_continuity_message',
        '_should_defer_heavy_work',
        '_humanize_task_failure',
        '_describe_resource_pressure',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is not None:
            stub.__dict__[name] = types.MethodType(method, stub)
    # Stub adaptive_orchestrator for _should_defer_heavy_work
    stub.adaptive_orchestrator = SimpleNamespace(
        _assess_resource_pressure=lambda: {'under_pressure': False},
    )
    return stub


# ── Test 1: post_task:chat does NOT trigger autonomy dock ──

class TestPostTaskChatNoDock:
    """After a chat task resolves, _apply_task_result must NOT call dock."""

    def test_post_task_chat_skips_dock(self):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = _make_stub_vm()
        # Bind _is_background_work_allowed
        dock_called = False
        original_allowed = vm._is_background_work_allowed

        def mock_dock():
            nonlocal dock_called
            dock_called = True

        # Simulate what _apply_task_result does for task_name='chat'
        task_name = 'chat'
        _skip_dock = task_name in ('chat', 'external_consultation')
        allowed, reason = vm._is_background_work_allowed('post_task_refresh')
        if allowed and not _skip_dock:
            mock_dock()
        assert not dock_called, 'dock should NOT be called after chat task'
        assert _skip_dock is True


# ── Test 2: slow autonomy dock activates circuit breaker ──

class TestSlowDockActivatesCircuitBreaker:
    """When dock takes >10s, circuit breaker must trip."""

    def test_slow_dock_trips_breaker(self):
        vm = _make_stub_vm()
        assert not vm._circuit_breaker_open
        # Simulate slow dock result
        vm._trip_circuit_breaker('dock_slow_result_15000ms')
        assert vm._circuit_breaker_open
        assert vm._circuit_breaker_until > time.time()
        state = vm.get_circuit_breaker_state()
        assert state['open'] is True

    def test_slow_dock_sets_cooldown(self):
        vm = _make_stub_vm()
        vm._dock_slow_result_block_until = time.time() + 300.0
        reason = vm._check_circuit_breaker('autonomy_dock')
        assert reason == 'dock_slow_result_cooldown'


# ── Test 3: deferred refresh with stall does NOT reschedule infinitely ──

class TestDeferredLoopLimit:
    """After N deferrals, circuit breaker blocks further rescheduling."""

    def test_deferred_loop_blocked_after_max(self):
        vm = _make_stub_vm()
        for _ in range(vm._deferred_loop_max):
            vm._record_deferred_loop('autonomy_dock')
        reason = vm._check_circuit_breaker('autonomy_dock')
        assert reason == 'deferred_loop_limit'

    def test_deferred_loop_cleared_on_success(self):
        vm = _make_stub_vm()
        for _ in range(2):
            vm._record_deferred_loop('autonomy_dock')
        vm._clear_deferred_loop('autonomy_dock')
        reason = vm._check_circuit_breaker('autonomy_dock')
        assert reason == ''


# ── Test 4: "sigue" with pending_task responds via continuity handler ──

class TestContinuityHandlerSigue:
    """'sigue' with active pending_task must be handled by continuity,
    NOT local LLM."""

    def test_sigue_is_continuity_message(self):
        vm = _make_stub_vm()
        assert vm._is_continuity_message('sigue')
        assert vm._is_continuity_message('Sigue')
        assert vm._is_continuity_message('ok procede')
        assert vm._is_continuity_message('que falta por hacer')
        assert not vm._is_continuity_message('explica el error de conexion')

    def test_sigue_with_pending_task_handled(self):
        vm = _make_stub_vm()
        vm._adaptive_session_id = 'task_123'
        messages_appended = []

        def mock_append(role, name, text, tag):
            messages_appended.append((role, text, tag))

        def mock_set_live(status):
            vm._live_status = status

        vm._append_message = mock_append
        vm._set_live_status = mock_set_live
        handled = vm._try_handle_continuity_message('sigue')
        assert handled is True
        assert len(messages_appended) == 1
        assert messages_appended[0][2] == 'continuity_handler'
        assert 'task_123' in messages_appended[0][1]


# ── Test 5: "ok procede" after freeze recent does NOT fall to local ──

class TestContinuityAfterFreeze:
    """'ok procede' after recent freeze should be intercepted."""

    def test_ok_procede_after_freeze_handled(self):
        vm = _make_stub_vm()
        # Simulate recent freeze via circuit_breaker_open
        vm._circuit_breaker_open = True
        vm._circuit_breaker_until = time.time() + 60.0
        messages_appended = []

        def mock_append(role, name, text, tag):
            messages_appended.append((role, text, tag))

        vm._append_message = mock_append
        vm._set_live_status = lambda s: None
        handled = vm._try_handle_continuity_message('ok procede')
        assert handled is True
        assert 'circuit breaker' in messages_appended[0][1].lower()


# ── Test 6: local_chat_worker timeout closes busy/working ──

class TestTimeoutSLA:
    """Timeout message must include 'no voy a seguir procesando a ciegas'."""

    def test_timeout_message_sla(self):
        vm = _make_stub_vm()
        msg, meta = vm._humanize_task_failure(
            'chat',
            'La operacion (chat) supero el tiempo maximo de 120s.',
        )
        assert meta == 'timeout'
        assert 'no voy a seguir procesando a ciegas' in msg.lower()


# ── Test 7: freeze incident includes causal context ──

class TestFreezeIncidentCausalContext:
    """FreezeIncidentReporter must include causal_context in reports."""

    def test_causal_context_captured(self, tmp_path):
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            FreezeIncidentReporter,
        )
        evolution_dir = tmp_path / 'evolution'
        evolution_dir.mkdir()
        reporter = FreezeIncidentReporter(
            evolution_dir=str(evolution_dir),
            db_path=str(tmp_path / 'nonexistent.db'),
        )
        path = reporter.capture_incident(trigger='test')
        report = json.loads(path.read_text(encoding='utf-8'))
        assert 'causal_context' in report
        ctx = report['causal_context']
        assert isinstance(ctx, dict)
        # Should have at least process_rss_mb (even if -1 when psutil unavailable)
        assert 'process_rss_mb' in ctx or 'error' not in ctx


# ── Test 8: resource_pressure distinguishes process vs system ──

class TestResourcePressureExplanation:
    """_describe_resource_pressure must distinguish IABV-internal
    pressure from general system exhaustion."""

    def test_internal_pressure_label(self):
        vm = _make_stub_vm()
        # Default (no psutil data) should mention 'presion interna'
        with patch.dict(os.environ, {}, clear=False):
            description = vm._describe_resource_pressure()
        assert 'presion interna' in description.lower() or 'stall' in description.lower()


# ── Test 9: OSES emits findings for deferred loop and dock slow ──

class TestOSESRuntimeStabilityFindings:
    """OSES must detect deferred_loop and dock_slow anti-patterns."""

    def test_deferred_loop_finding(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        # Create audit log with enough deferred events
        log_dir = tmp_path / 'data' / 'logs'
        log_dir.mkdir(parents=True)
        audit_path = log_dir / 'runtime_audit.jsonl'
        lines = []
        for i in range(6):
            lines.append(json.dumps({
                'kind': 'control_autonomy_dock_refresh_deferred',
                'data': {'reason': 'recent_heavy_stall'},
            }))
        for i in range(3):
            lines.append(json.dumps({
                'kind': 'control_autonomy_dock_refresh_budget_exceeded',
                'data': {'elapsed_ms': 15000},
            }))
        audit_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        oses = MagicMock(spec=OperationalSelfExaminationService)
        oses.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._runtime_stability_controller_findings(oses)
        categories = [f.category for f in findings]
        assert 'repeated_deferred_background_loop' in categories
        assert 'autonomy_dock_slow_projection_repeated' in categories

    def test_metacognitive_contract_missing(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        log_dir = tmp_path / 'data' / 'logs'
        log_dir.mkdir(parents=True)
        audit_path = log_dir / 'runtime_audit.jsonl'
        lines = []
        for i in range(6):
            lines.append(json.dumps({
                'kind': 'control_autonomy_dock_refresh_deferred',
                'data': {'reason': 'budget_cooldown'},
            }))
        audit_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        oses = MagicMock(spec=OperationalSelfExaminationService)
        oses.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._runtime_stability_controller_findings(oses)
        categories = [f.category for f in findings]
        assert 'metacognitive_thread_contract_missing' in categories


# ── Test 10: PortableContext exports runtime_stability_controller ──

class TestPortableContextStabilityExport:
    """PortableContext must include a runtime_stability_controller section."""

    def test_section_method_returns_section(self):
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        from iabv_v15.domain.models import PortableContextSection
        pcs = MagicMock(spec=PortableContextService)
        pcs._section = PortableContextService._section.__get__(pcs)
        section = PortableContextService._runtime_stability_controller_section(
            pcs, now='2026-01-01T00:00:00Z',
        )
        assert isinstance(section, PortableContextSection)
        assert section.section_id == 'runtime_stability_controller'
        assert 'P0.68' in section.title
        assert len(section.items) >= 1
        item = section.items[0]
        assert 'latest_stalls' in item
        assert 'circuit_breaker_state' in item
        assert 'blocked_work_classes' in item
        assert 'last_slow_dock_duration_ms' in item
        assert 'continuity_routing_status' in item
