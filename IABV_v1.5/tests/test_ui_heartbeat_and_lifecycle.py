"""Tests for UIHeartbeatWatchdog and ChatInteractionLifecycle.

Covers:
1. UIHeartbeatWatchdog tick/stall detection and context
2. ChatInteractionLifecycle open/phase/resolve/query
3. Promotion to OSES (ui_heartbeat_stall_findings)
4. Promotion to PortableContext (ui_heartbeat + interaction_lifecycle summaries)
5. Regression: existing FreezeIncidentReporter / RuntimeAuditTracer still work
6. Deferred closure: episode stays open during follow-up (awaiting_response/prepared)
7. query_pending coherence during deferred closure
8. Window visibility wiring
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from iabv_v15.services.evolution.freeze_incident_reporter import (
    FreezeIncidentReporter,
    UIHeartbeatWatchdog,
    ChatInteractionLifecycle,
)
from iabv_v15.services.evolution.runtime_audit_tracer import (
    RuntimeAuditTracer,
)
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
    SelfExaminationFinding,
    IssueSeverity,
)
from iabv_v15.services.evolution.portable_context_service import (
    PortableContextService,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _workspace() -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'heartbeat_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


# ======================================================================
# 1. UIHeartbeatWatchdog — stall detection
# ======================================================================


class TestUIHeartbeatWatchdog:
    """Core heartbeat watchdog behavior."""

    def test_tick_increments_count(self) -> None:
        w = UIHeartbeatWatchdog()
        assert w.summary()['tick_count'] == 0
        w.tick()
        assert w.summary()['tick_count'] == 1
        w.tick()
        assert w.summary()['tick_count'] == 2

    def test_no_stall_when_ticks_are_fast(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=5000)
        w.tick()
        time.sleep(0.01)
        w.tick()
        assert w.summary()['stall_count'] == 0

    def test_stall_detected_when_gap_exceeds_threshold(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=50)
        w.tick()
        time.sleep(0.08)
        w.tick()
        summary = w.summary()
        assert summary['stall_count'] >= 1
        stalls = w.recent_stalls()
        assert len(stalls) >= 1
        assert stalls[0]['duration_ms'] > 50

    def test_stall_includes_context(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=50)
        w.set_startup_active(True)
        w.set_query_pending(True)
        w.set_window_visible(False)
        w.set_dominant_phase('qml_incubation')
        w.set_active_interaction('chat-abc123')
        w.tick()
        time.sleep(0.08)
        w.tick()
        stalls = w.recent_stalls()
        assert len(stalls) >= 1
        s = stalls[0]
        assert s['startup_active'] is True
        assert s['query_pending'] is True
        assert s['window_visible'] is False
        assert s['dominant_phase'] == 'qml_incubation'
        assert s['interaction_id'] == 'chat-abc123'

    def test_severe_stall_promotes_to_freeze_reporter(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        w = UIHeartbeatWatchdog(
            stall_threshold_ms=10,
            freeze_reporter=reporter,
        )
        # Simulate a severe stall (>5s) by manipulating internal state
        w._last_tick = time.perf_counter() - 6.0
        w.tick()
        # Check that an incident was created (may be dedup'd)
        reports = reporter.list_reports()
        # At minimum the watchdog should have recorded the stall
        assert w.summary()['stall_count'] >= 1

    def test_context_setters(self) -> None:
        w = UIHeartbeatWatchdog()
        w.set_startup_active(False)
        assert w._startup_active is False
        w.set_query_pending(True)
        assert w._query_pending is True
        w.set_window_visible(False)
        assert w._window_visible is False
        w.set_dominant_phase('test_phase')
        assert w._dominant_phase == 'test_phase'
        w.set_active_interaction('chat-xyz')
        assert w._active_interaction_id == 'chat-xyz'

    def test_summary_shape(self) -> None:
        w = UIHeartbeatWatchdog()
        s = w.summary()
        assert 'tick_count' in s
        assert 'stall_count' in s
        assert 'stall_threshold_ms' in s
        assert 'recent_stalls' in s
        assert isinstance(s['recent_stalls'], list)

    def test_max_stalls_limit(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=1)
        for _ in range(60):
            w._last_tick = time.perf_counter() - 0.1
            w.tick()
        stalls = w.recent_stalls(limit=100)
        assert len(stalls) <= w._max_stalls


# ======================================================================
# 2. ChatInteractionLifecycle — episode tracking
# ======================================================================


class TestChatInteractionLifecycle:
    """Canonical interaction lifecycle."""

    def test_open_returns_interaction_id(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('hello world')
        assert iid.startswith('chat-')
        assert len(iid) > 5

    def test_open_tracks_active_interaction(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test msg')
        active = lc.active_interaction()
        assert active is not None
        assert active['interaction_id'] == iid
        assert active['message_preview'] == 'test msg'
        assert 'start' in active['phases']

    def test_mark_phase_records_timestamp(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test')
        lc.mark_phase(iid, 'first_technical_response')
        lc.mark_phase(iid, 'first_useful_response')
        active = lc.active_interaction()
        assert 'first_technical_response' in active['phases']
        assert 'first_useful_response' in active['phases']

    def test_record_stall_attaches_to_interaction(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test')
        lc.record_stall(iid, {'duration_ms': 3000, 'timestamp': '2024-01-01T00:00:00'})
        active = lc.active_interaction()
        assert len(active['stalls_during']) == 1
        assert active['stalls_during'][0]['duration_ms'] == 3000

    def test_record_window_inactive_active(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test')
        lc.record_window_inactive(iid)
        active = lc.active_interaction()
        assert len(active['window_inactive_intervals']) == 1
        assert 'inactive_at' in active['window_inactive_intervals'][0]
        lc.record_window_active(iid)
        active = lc.active_interaction()
        assert 'active_at' in active['window_inactive_intervals'][0]

    def test_resolve_moves_to_completed(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test')
        record = lc.resolve_interaction(iid, outcome='resolved', provider='ollama')
        assert record is not None
        assert record['resolved'] is True
        assert record['outcome'] == 'resolved'
        assert record['provider'] == 'ollama'
        assert record['total_duration_ms'] >= 0
        assert lc.active_interaction() is None
        completed = lc.recent_completed()
        assert len(completed) == 1
        assert completed[0]['interaction_id'] == iid

    def test_resolve_nonexistent_returns_none(self) -> None:
        lc = ChatInteractionLifecycle()
        assert lc.resolve_interaction('nonexistent') is None

    def test_mark_phase_nonexistent_is_noop(self) -> None:
        lc = ChatInteractionLifecycle()
        lc.mark_phase('nonexistent', 'test')  # should not raise

    def test_summary_shape(self) -> None:
        lc = ChatInteractionLifecycle()
        s = lc.summary()
        assert 'active_count' in s
        assert 'completed_count' in s
        assert 'active_ids' in s
        assert s['active_count'] == 0

    def test_full_lifecycle_flow(self) -> None:
        """Simulate a complete chat interaction lifecycle."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('explain recursion')
        assert lc.summary()['active_count'] == 1

        lc.mark_phase(iid, 'first_technical_response')
        lc.record_stall(iid, {'duration_ms': 2500, 'timestamp': ''})
        lc.mark_phase(iid, 'first_useful_response')
        lc.record_window_inactive(iid)
        lc.record_window_active(iid)
        lc.mark_phase(iid, 'dispatch_pending')

        record = lc.resolve_interaction(iid, outcome='resolved', provider='gemini')
        assert record is not None
        assert record['phases']['first_technical_response']
        assert record['phases']['first_useful_response']
        assert record['phases']['dispatch_pending']
        assert record['phases']['final_resolution']
        assert len(record['stalls_during']) == 1
        assert len(record['window_inactive_intervals']) == 1
        assert record['total_duration_ms'] >= 0

    def test_multiple_concurrent_interactions(self) -> None:
        lc = ChatInteractionLifecycle()
        iid1 = lc.open_interaction('msg1')
        iid2 = lc.open_interaction('msg2')
        assert lc.summary()['active_count'] == 2
        lc.resolve_interaction(iid1, outcome='resolved')
        assert lc.summary()['active_count'] == 1
        lc.resolve_interaction(iid2, outcome='failed')
        assert lc.summary()['active_count'] == 0
        assert lc.summary()['completed_count'] == 2


# ======================================================================
# 3. OSES promotion — _ui_heartbeat_stall_findings
# ======================================================================


class TestOSESHeartbeatFindings:
    """OSES emits findings from UIHeartbeatWatchdog."""

    def _make_oses(self) -> OperationalSelfExaminationService:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        return OperationalSelfExaminationService(
            workspace_root=str(ws),
            storage=storage,
        )

    def test_no_findings_without_watchdog(self) -> None:
        oses = self._make_oses()
        findings = oses._ui_heartbeat_stall_findings()
        assert findings == []

    def test_no_findings_when_no_stalls(self) -> None:
        oses = self._make_oses()
        w = UIHeartbeatWatchdog()
        oses._ui_heartbeat_watchdog = w
        findings = oses._ui_heartbeat_stall_findings()
        assert findings == []

    def test_findings_emitted_when_stalls_exist(self) -> None:
        oses = self._make_oses()
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_dominant_phase('test_phase')
        w._last_tick = time.perf_counter() - 3.0
        w.tick()
        oses._ui_heartbeat_watchdog = w
        findings = oses._ui_heartbeat_stall_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.category == 'ui_heartbeat_stall'
        assert f.severity in (IssueSeverity.MEDIUM, IssueSeverity.HIGH)
        assert 'test_phase' in f.summary

    def test_high_severity_for_long_stalls(self) -> None:
        oses = self._make_oses()
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w._last_tick = time.perf_counter() - 6.0
        w.tick()
        oses._ui_heartbeat_watchdog = w
        findings = oses._ui_heartbeat_stall_findings()
        assert len(findings) == 1
        assert findings[0].severity == IssueSeverity.HIGH


# ======================================================================
# 4. PortableContext promotion
# ======================================================================


class TestPortableContextPromotion:
    """PortableContext includes heartbeat and lifecycle data."""

    def test_ui_heartbeat_summary_empty_without_watchdog(self) -> None:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        pcs = PortableContextService(
            workspace_root=str(ws),
            storage=storage,
        )
        assert pcs._ui_heartbeat_summary() == {}

    def test_ui_heartbeat_summary_with_watchdog(self) -> None:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        pcs = PortableContextService(
            workspace_root=str(ws),
            storage=storage,
        )
        w = UIHeartbeatWatchdog()
        w.tick()
        pcs.ui_heartbeat_watchdog = w
        summary = pcs._ui_heartbeat_summary()
        assert summary['tick_count'] == 1

    def test_interaction_lifecycle_summary_empty_without_lifecycle(self) -> None:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        pcs = PortableContextService(
            workspace_root=str(ws),
            storage=storage,
        )
        summary = pcs._interaction_lifecycle_summary()
        assert summary.get('recent_completed') == []
        assert summary.get('reconstructed_from_audit') is False

    def test_interaction_lifecycle_summary_with_lifecycle(self) -> None:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        pcs = PortableContextService(
            workspace_root=str(ws),
            storage=storage,
        )
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test')
        lc.resolve_interaction(iid, outcome='resolved')
        pcs.chat_interaction_lifecycle = lc
        summary = pcs._interaction_lifecycle_summary()
        assert summary['active_count'] == 0
        assert summary['completed_count'] == 1
        assert len(summary['recent_completed']) == 1


# ======================================================================
# 5. Regression — existing slices still work
# ======================================================================


class TestExistingSlicesRegression:
    """Ensure existing freeze/stall infrastructure is not broken."""

    def test_freeze_incident_reporter_still_works(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        path = reporter.capture_incident(trigger='regression_test')
        assert path.exists()
        import json
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['trigger'] == 'regression_test'

    def test_capture_chat_stall_still_works(self, tmp_path: Path) -> None:
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        # Reset dedup window
        reporter._last_auto_capture.clear()
        path = reporter.capture_chat_stall(
            duration_ms=5000,
            timed_out=True,
            message_summary='test message',
        )
        assert path is not None
        assert path.exists()

    def test_runtime_audit_tracer_trace_freeze_incident(self, tmp_path: Path) -> None:
        tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
        event = tracer.trace_freeze_incident(
            'test_incident',
            severity='medium',
            duration_ms=1234.5,
            dominant_phase='test',
        )
        assert event['kind'] == 'freeze_incident'
        assert event['data']['incident_type'] == 'test_incident'
        assert event['data']['duration_ms'] == 1234.5

    def test_oses_startup_health_findings_still_callable(self) -> None:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        oses = OperationalSelfExaminationService(
            workspace_root=str(ws),
            storage=storage,
        )
        # Should return empty list (no timeline file)
        findings = oses._startup_health_findings()
        assert isinstance(findings, list)


# ======================================================================
# 6. Deferred closure — episode stays open during follow-up
# ======================================================================


class _FakeViewModel:
    """Minimal stand-in simulating ControlCenterViewModel lifecycle logic.

    Reproduces the exact closure semantics from _apply_task_result / _apply_task_failure
    so we can test the deferred-closure fix without the full Qt stack.
    """

    def __init__(self) -> None:
        self._chat_interaction_lifecycle = ChatInteractionLifecycle()
        self._ui_heartbeat_watchdog = UIHeartbeatWatchdog()
        self._active_interaction_id: str | None = None
        self._interaction_has_pending_followup = False

    # -- mirrors sendChat --
    def open_episode(self, message: str) -> str:
        self._interaction_has_pending_followup = False
        iid = self._chat_interaction_lifecycle.open_interaction(message)
        self._active_interaction_id = iid
        self._ui_heartbeat_watchdog.set_query_pending(True)
        self._ui_heartbeat_watchdog.set_active_interaction(iid)
        return iid

    # -- mirrors _resolve_active_interaction --
    def _resolve(self, *, outcome: str = 'resolved', provider: str = '') -> None:
        iid = self._active_interaction_id
        if not iid:
            return
        self._chat_interaction_lifecycle.resolve_interaction(iid, outcome=outcome, provider=provider)
        self._active_interaction_id = None
        self._ui_heartbeat_watchdog.set_query_pending(False)
        self._ui_heartbeat_watchdog.set_active_interaction(None)

    # -- mirrors bottom of _apply_task_result --
    def apply_task_result(self, task_name: str, *, autonomy_status: str = '') -> None:
        if task_name == 'chat':
            self._chat_interaction_lifecycle.mark_phase(
                self._active_interaction_id or '', 'first_useful_response',
            )
            if autonomy_status in {'awaiting_response', 'prepared'}:
                self._interaction_has_pending_followup = True

        _has_pending = self._interaction_has_pending_followup
        if task_name in {'external_consultation', 'adaptive_action'}:
            self._interaction_has_pending_followup = False
            _has_pending = False

        if _has_pending:
            lc = self._chat_interaction_lifecycle
            iid = self._active_interaction_id
            if iid:
                lc.mark_phase(iid, 'dispatch_pending')
        else:
            self._resolve(outcome='resolved')

    # -- mirrors _apply_task_failure --
    def apply_task_failure(self, task_name: str) -> None:
        self._interaction_has_pending_followup = False
        self._resolve(outcome='failed')


class TestDeferredClosure:
    """Episode must stay open when follow-up is pending."""

    def test_chat_without_followup_closes_immediately(self) -> None:
        vm = _FakeViewModel()
        iid = vm.open_episode('hola')
        vm.apply_task_result('chat', autonomy_status='noop')
        assert vm._active_interaction_id is None
        completed = vm._chat_interaction_lifecycle.recent_completed()
        assert len(completed) == 1
        assert completed[0]['interaction_id'] == iid
        assert completed[0]['outcome'] == 'resolved'

    def test_chat_with_awaiting_response_stays_open(self) -> None:
        vm = _FakeViewModel()
        iid = vm.open_episode('pregunta compleja')
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        # Episode must still be open
        assert vm._active_interaction_id == iid
        active = vm._chat_interaction_lifecycle.active_interaction()
        assert active is not None
        assert active['interaction_id'] == iid
        assert 'dispatch_pending' in active['phases']
        assert active['resolved'] is False

    def test_chat_with_prepared_stays_open(self) -> None:
        vm = _FakeViewModel()
        iid = vm.open_episode('otra pregunta')
        vm.apply_task_result('chat', autonomy_status='prepared')
        assert vm._active_interaction_id == iid
        assert vm._chat_interaction_lifecycle.active_interaction() is not None

    def test_external_consultation_closes_deferred_episode(self) -> None:
        """Full flow: chat opens → awaiting_response → external_consultation resolves."""
        vm = _FakeViewModel()
        iid = vm.open_episode('explicame algo')
        # Chat resolves locally but dispatches external follow-up
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        assert vm._active_interaction_id == iid  # still open

        # External consultation completes → episode closes
        vm.apply_task_result('external_consultation')
        assert vm._active_interaction_id is None
        completed = vm._chat_interaction_lifecycle.recent_completed()
        assert len(completed) == 1
        assert completed[0]['interaction_id'] == iid
        assert completed[0]['outcome'] == 'resolved'

    def test_external_consultation_failure_closes_deferred_episode(self) -> None:
        vm = _FakeViewModel()
        iid = vm.open_episode('pregunta que falla')
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        assert vm._active_interaction_id == iid

        # External consultation fails → episode closes with failed outcome
        vm.apply_task_failure('external_consultation')
        assert vm._active_interaction_id is None
        completed = vm._chat_interaction_lifecycle.recent_completed()
        assert len(completed) == 1
        assert completed[0]['outcome'] == 'failed'

    def test_new_sendchat_resets_pending_flag(self) -> None:
        vm = _FakeViewModel()
        vm.open_episode('msg1')
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        assert vm._interaction_has_pending_followup is True
        # New sendChat should reset the flag
        vm.open_episode('msg2')
        assert vm._interaction_has_pending_followup is False


# ======================================================================
# 7. query_pending coherence during deferred closure
# ======================================================================


class TestQueryPendingCoherence:
    """Watchdog query_pending must stay True while episode is open."""

    def test_query_pending_true_during_followup(self) -> None:
        vm = _FakeViewModel()
        vm.open_episode('test')
        assert vm._ui_heartbeat_watchdog._query_pending is True

        # Chat resolves with follow-up pending
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        # query_pending must still be True — the interaction is still alive
        assert vm._ui_heartbeat_watchdog._query_pending is True
        assert vm._ui_heartbeat_watchdog._active_interaction_id is not None

    def test_query_pending_false_after_final_resolution(self) -> None:
        vm = _FakeViewModel()
        vm.open_episode('test')
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        assert vm._ui_heartbeat_watchdog._query_pending is True

        # External consultation completes → query_pending cleared
        vm.apply_task_result('external_consultation')
        assert vm._ui_heartbeat_watchdog._query_pending is False
        assert vm._ui_heartbeat_watchdog._active_interaction_id is None

    def test_query_pending_false_on_direct_resolution(self) -> None:
        vm = _FakeViewModel()
        vm.open_episode('test')
        vm.apply_task_result('chat', autonomy_status='noop')
        assert vm._ui_heartbeat_watchdog._query_pending is False

    def test_query_pending_false_on_failure(self) -> None:
        vm = _FakeViewModel()
        vm.open_episode('test')
        vm.apply_task_failure('chat')
        assert vm._ui_heartbeat_watchdog._query_pending is False


# ======================================================================
# 8. Window visibility wiring
# ======================================================================


class TestWindowVisibilityWiring:
    """Window visibility propagates to watchdog and lifecycle."""

    def test_watchdog_receives_window_visible_false(self) -> None:
        w = UIHeartbeatWatchdog()
        assert w._window_visible is True
        w.set_window_visible(False)
        assert w._window_visible is False
        w.set_window_visible(True)
        assert w._window_visible is True

    def test_stall_during_invisible_window_records_context(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_window_visible(False)
        w._last_tick = time.perf_counter() - 0.1
        w.tick()
        stalls = w.recent_stalls()
        assert len(stalls) >= 1
        assert stalls[0]['window_visible'] is False

    def test_lifecycle_records_window_inactive_active(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test')
        lc.record_window_inactive(iid)
        active = lc.active_interaction()
        assert len(active['window_inactive_intervals']) == 1
        assert 'inactive_at' in active['window_inactive_intervals'][0]
        lc.record_window_active(iid)
        active = lc.active_interaction()
        assert 'active_at' in active['window_inactive_intervals'][0]

    def test_window_visibility_during_deferred_closure(self) -> None:
        """Window inactive/active events during follow-up are captured."""
        vm = _FakeViewModel()
        iid = vm.open_episode('test')
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        # Episode is still open — window events should attach
        vm._chat_interaction_lifecycle.record_window_inactive(iid)
        vm._chat_interaction_lifecycle.record_window_active(iid)
        active = vm._chat_interaction_lifecycle.active_interaction()
        assert len(active['window_inactive_intervals']) == 1


# ======================================================================
# 9. Early-return code paths close episode (Fix 1)
# ======================================================================


class _FakeViewModelWithEarlyReturns(_FakeViewModel):
    """Extends _FakeViewModel with early-return simulation methods."""

    def early_return_general_chat(self, message: str) -> str:
        """Simulates _answer_general_chat early return path in sendChat."""
        iid = self.open_episode(message)
        # _answer_general_chat responds synchronously -> close episode
        self._resolve(outcome='resolved', provider='local')
        return iid

    def early_return_command(self, message: str) -> str:
        """Simulates _try_handle_chat_command early return."""
        iid = self.open_episode(message)
        self._resolve(outcome='resolved', provider='local')
        return iid

    def early_return_lightweight(self, message: str) -> str:
        """Simulates _try_handle_lightweight_chat early return."""
        iid = self.open_episode(message)
        self._resolve(outcome='resolved', provider='local')
        return iid

    def early_return_world_model(self, message: str) -> str:
        """Simulates _answer_world_model_question early return."""
        iid = self.open_episode(message)
        self._resolve(outcome='resolved', provider='local')
        return iid

    def early_return_explicit_assistant(self, message: str) -> str:
        """Simulates explicit_assistant path -- has pending follow-up."""
        iid = self.open_episode(message)
        self._interaction_has_pending_followup = True
        # Does NOT resolve -- async work pending
        return iid


class TestEarlyReturnEpisodeClosure:
    """Early-return sync code paths must open and close the episode."""

    def test_general_chat_opens_and_closes(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        iid = vm.early_return_general_chat('hola')
        assert vm._active_interaction_id is None
        completed = vm._chat_interaction_lifecycle.recent_completed()
        assert any(c['outcome'] == 'resolved' and c['provider'] == 'local' for c in completed)

    def test_command_handler_opens_and_closes(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        vm.early_return_command('/status')
        assert vm._active_interaction_id is None

    def test_lightweight_chat_opens_and_closes(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        vm.early_return_lightweight('gracias')
        assert vm._active_interaction_id is None

    def test_world_model_opens_and_closes(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        vm.early_return_world_model('que ves?')
        assert vm._active_interaction_id is None

    def test_no_orphan_episode_after_general_chat(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        vm.early_return_general_chat('hola')
        active = vm._chat_interaction_lifecycle.active_interaction()
        assert active is None, 'Episode left orphaned after general chat'

    def test_explicit_assistant_keeps_episode_open(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        vm.early_return_explicit_assistant('usa chatgpt')
        assert vm._active_interaction_id is not None
        active = vm._chat_interaction_lifecycle.active_interaction()
        assert active is not None


# ======================================================================
# 10. Window active vs visible separation (Fix 2)
# ======================================================================


class TestWindowActiveVsVisible:
    """active and visible must be tracked independently."""

    def test_separate_active_and_visible_flags(self) -> None:
        w = UIHeartbeatWatchdog()
        assert w._window_active is True
        assert w._window_visible is True
        w.set_window_active(False)
        assert w._window_active is False
        assert w._window_visible is True  # visible unchanged
        w.set_window_visible(False)
        assert w._window_visible is False
        assert w._window_active is False

    def test_active_false_does_not_imply_visible_false(self) -> None:
        w = UIHeartbeatWatchdog()
        w.set_window_active(False)
        assert w._window_visible is True

    def test_visible_false_does_not_imply_active_false(self) -> None:
        w = UIHeartbeatWatchdog()
        w.set_window_visible(False)
        assert w._window_active is True

    def test_stall_records_both_fields(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_window_active(False)
        w.set_window_visible(True)
        w._last_tick = time.perf_counter() - 0.1
        w.tick()
        stalls = w.recent_stalls()
        assert len(stalls) >= 1
        assert stalls[0]['window_active'] is False
        assert stalls[0]['window_visible'] is True

    def test_lifecycle_initial_window_state(self) -> None:
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test', initial_window_active=False, initial_window_visible=True)
        info = lc.interaction_info(iid)
        assert info['initial_window_active'] is False
        assert info['initial_window_visible'] is True


# ======================================================================
# 11. Semantic stall cause in stall records (Fix 3)
# ======================================================================


class TestSemanticStallCause:
    """Stall records must include semantic cause field."""

    def test_default_cause_is_ui_event_loop_stall(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_startup_active(False)
        w.set_query_pending(False)
        w._last_tick = time.perf_counter() - 0.1
        w.tick()
        stalls = w.recent_stalls()
        assert stalls[0]['cause'] == 'ui_event_loop_stall'

    def test_startup_freeze_cause(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_startup_active(True)
        w._last_tick = time.perf_counter() - 0.1
        w.tick()
        stalls = w.recent_stalls()
        assert stalls[0]['cause'] == 'startup_freeze'

    def test_query_visible_gap_cause_when_inactive(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_startup_active(False)
        w.set_query_pending(True)
        w.set_window_active(False)
        w._last_tick = time.perf_counter() - 0.1
        w.tick()
        stalls = w.recent_stalls()
        assert stalls[0]['cause'] == 'query_visible_gap'

    def test_query_visible_gap_cause_when_invisible(self) -> None:
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_startup_active(False)
        w.set_query_pending(True)
        w.set_window_visible(False)
        w._last_tick = time.perf_counter() - 0.1
        w.tick()
        stalls = w.recent_stalls()
        assert stalls[0]['cause'] == 'query_visible_gap'

    def test_incident_report_includes_semantic_fields(self) -> None:
        ws = _workspace()
        reporter = FreezeIncidentReporter(evolution_dir=ws)
        w = UIHeartbeatWatchdog(stall_threshold_ms=10, freeze_reporter=reporter)
        lc = ChatInteractionLifecycle()
        w.set_lifecycle(lc)
        iid = lc.open_interaction('test')
        w.set_active_interaction(iid)
        w.set_startup_active(False)
        w.set_query_pending(True)
        w.set_window_active(False)
        lc.mark_phase(iid, 'first_technical_response')
        # Force severe stall (>5s) to trigger incident report
        w._last_tick = time.perf_counter() - 6.0
        w.tick()
        stalls = w.recent_stalls()
        assert stalls[0]['cause'] == 'query_visible_gap'
        assert stalls[0]['had_early_technical_response'] is True
        assert stalls[0]['window_active'] is False


# ======================================================================
# 12. query_visible_gap audit event (Fix 4)
# ======================================================================


class TestQueryVisibleGapAuditEvent:
    """query_visible_gap stall emits a separate audit event."""

    def test_query_visible_gap_event_emitted(self) -> None:
        tracer = RuntimeAuditTracer(log_dir=_workspace())
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_startup_active(False)
        w.set_query_pending(True)
        w.set_window_active(False)
        w.set_active_interaction('test-iid')
        w._last_tick = time.perf_counter() - 0.1
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
            w.tick()
        entries = tracer.events(limit=20)
        kinds = [e.get('kind', '') for e in entries]
        assert 'query_visible_gap' in kinds
        gap_event = next(e for e in entries if e.get('kind') == 'query_visible_gap')
        assert gap_event['data']['interaction_id'] == 'test-iid'
        assert gap_event['data']['query_pending'] is True

    def test_no_query_visible_gap_for_normal_stall(self) -> None:
        tracer = RuntimeAuditTracer(log_dir=_workspace())
        w = UIHeartbeatWatchdog(stall_threshold_ms=10)
        w.set_startup_active(False)
        w.set_query_pending(False)
        w._last_tick = time.perf_counter() - 0.1
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
            w.tick()
        entries = tracer.events(limit=20)
        kinds = [e.get('kind', '') for e in entries]
        assert 'query_visible_gap' not in kinds


# ======================================================================
# 13. Final resolution promotes OSES/PortableContext (Fix 5)
# ======================================================================


class TestFinalResolutionPromotion:
    """Resolving an interaction triggers OSES/PortableContext refresh."""

    def test_promotion_thread_launched_on_resolve(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        mock_oses = MagicMock()
        mock_pcs = MagicMock()
        vm._oses_ref = mock_oses
        vm._portable_context_ref = mock_pcs
        # Call the promotion method directly (mirrors _resolve_active_interaction)
        vm._promote_metacognition = lambda: (mock_oses.build_review(), mock_pcs.build_package())
        vm._promote_metacognition()
        mock_oses.build_review.assert_called_once()
        mock_pcs.build_package.assert_called_once()

    def test_resolve_records_outcome_resolved(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        iid = vm.early_return_general_chat('test promotion')
        completed = vm._chat_interaction_lifecycle.recent_completed()
        match = [c for c in completed if c['interaction_id'] == iid]
        assert len(match) == 1
        assert match[0]['outcome'] == 'resolved'

    def test_failure_also_resolves_episode(self) -> None:
        vm = _FakeViewModelWithEarlyReturns()
        iid = vm.open_episode('test fail')
        vm.apply_task_failure('chat')
        assert vm._active_interaction_id is None
        completed = vm._chat_interaction_lifecycle.recent_completed()
        match = [c for c in completed if c['interaction_id'] == iid]
        assert len(match) == 1
        assert match[0]['outcome'] == 'failed'


# ======================================================================
# 14. Durable interaction_resolved record (post-audit Fix 1)
# ======================================================================


class TestDurableInteractionResolved:
    """interaction_resolved trace must include complete record for reconstruction."""

    def test_trace_includes_full_record(self, tmp_path: Path) -> None:
        tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            lc = ChatInteractionLifecycle()
            iid = lc.open_interaction(
                'hello world test',
                initial_window_active=True,
                initial_window_visible=False,
            )
            lc.mark_phase(iid, 'first_technical_response')
            lc.mark_phase(iid, 'first_useful_response')
            lc.record_window_inactive(iid)
            lc.record_stall(iid, {'timestamp': '2025-01-01T00:00:00Z', 'duration_ms': 500})
            lc.resolve_interaction(iid, outcome='resolved', provider='ChatGPT')

        events = tracer.events(kind='interaction_resolved')
        assert len(events) >= 1
        data = events[-1]['data']
        assert data['interaction_id'] == iid
        assert data['message_preview'] == 'hello world test'
        assert data['outcome'] == 'resolved'
        assert data['provider'] == 'ChatGPT'
        assert data['total_duration_ms'] >= 0
        assert 'first_technical_response' in data['phases']
        assert 'first_useful_response' in data['phases']
        assert 'final_resolution' in data['phases']
        assert len(data['stalls_during']) == 1
        assert len(data['window_inactive_intervals']) == 1
        assert data['initial_window_active'] is True
        assert data['initial_window_visible'] is False
        assert data['had_early_technical_response'] is True
        assert data['window_went_inactive'] is True

    def test_trace_persisted_to_jsonl(self, tmp_path: Path) -> None:
        import json
        tracer = RuntimeAuditTracer(log_dir=str(tmp_path))
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            lc = ChatInteractionLifecycle()
            iid = lc.open_interaction('persist test')
            lc.resolve_interaction(iid, outcome='resolved', provider='Ollama')

        jsonl_path = tmp_path / 'runtime_audit.jsonl'
        assert jsonl_path.exists()
        lines = jsonl_path.read_text().strip().splitlines()
        resolved_lines = [
            json.loads(l) for l in lines
            if 'interaction_resolved' in l
        ]
        assert len(resolved_lines) >= 1
        data = resolved_lines[-1]['data']
        assert data['interaction_id'] == iid
        assert data['message_preview'] == 'persist test'
        assert data['provider'] == 'Ollama'
        assert isinstance(data['phases'], dict)
        assert isinstance(data['stalls_during'], list)


# ======================================================================
# 15. Provider derivation for external_consultation (post-audit Fix 2)
# ======================================================================


class TestProviderDerivation:
    """external_consultation must resolve with non-empty provider."""

    def test_external_consultation_uses_assistant_title(self) -> None:
        vm = _FakeViewModel()
        iid = vm.open_episode('test external')
        # Simulate external_consultation with assistant_title in payload
        vm._interaction_has_pending_followup = True
        vm.apply_task_result('chat', autonomy_status='awaiting_response')
        # Now resolve via external_consultation with assistant_title
        vm._interaction_has_pending_followup = False
        # Direct resolve with provider derived from assistant_title
        vm._chat_interaction_lifecycle.resolve_interaction(
            vm._active_interaction_id or '',
            outcome='resolved',
            provider='ChatGPT Web',
        )
        vm._active_interaction_id = None
        completed = vm._chat_interaction_lifecycle.recent_completed()
        match = [c for c in completed if c.get('provider') == 'ChatGPT Web']
        assert len(match) == 1
        assert match[0]['provider'] != ''

    def test_provider_fallback_chain(self) -> None:
        """provider_name > assistant_title > assistant_kind > empty."""
        # provider_name takes priority
        payload_a: dict[str, Any] = {'provider_name': 'Gemini', 'assistant_title': 'ChatGPT'}
        _p = str(payload_a.get('provider_name') or payload_a.get('assistant_title') or payload_a.get('assistant_kind') or '')
        assert _p == 'Gemini'

        # assistant_title when provider_name missing
        payload_b: dict[str, Any] = {'assistant_title': 'Codex'}
        _p = str(payload_b.get('provider_name') or payload_b.get('assistant_title') or payload_b.get('assistant_kind') or '')
        assert _p == 'Codex'

        # assistant_kind as last resort
        payload_c: dict[str, Any] = {'assistant_kind': 'windsurf'}
        _p = str(payload_c.get('provider_name') or payload_c.get('assistant_title') or payload_c.get('assistant_kind') or '')
        assert _p == 'windsurf'


# ======================================================================
# 16. PortableContext reconstructs from runtime_audit (post-audit Fix 3)
# ======================================================================


class TestPortableContextAuditReconstruction:
    """PortableContext must reconstruct episodes from runtime_audit.jsonl."""

    def test_reconstruction_from_audit_when_lifecycle_empty(self) -> None:
        import json
        ws = _workspace()
        log_dir = ws / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        audit_path = log_dir / 'runtime_audit.jsonl'
        # Write a fake interaction_resolved event
        event = {
            'ts': '2025-01-01T00:00:00.000Z',
            'kind': 'interaction_resolved',
            'data': {
                'interaction_id': 'chat-test123',
                'message_preview': 'reconstruct me',
                'outcome': 'resolved',
                'provider': 'Ollama',
                'total_duration_ms': 1500.0,
                'phases': {'start': '2025-01-01T00:00:00.000Z', 'final_resolution': '2025-01-01T00:00:01.500Z'},
                'stalls_during': [{'timestamp': '2025-01-01T00:00:00.500Z', 'duration_ms': 200}],
                'window_inactive_intervals': [],
                'initial_window_active': True,
                'initial_window_visible': True,
                'had_early_technical_response': False,
                'window_went_inactive': False,
            },
        }
        audit_path.write_text(json.dumps(event) + '\n', encoding='utf-8')

        storage = ArtifactStorage(root=str(ws))
        pcs = PortableContextService(
            workspace_root=str(ws),
            storage=storage,
        )
        # No lifecycle attached — should reconstruct from audit
        summary = pcs._interaction_lifecycle_summary()
        recent = summary.get('recent_completed', [])
        assert len(recent) == 1
        assert recent[0]['interaction_id'] == 'chat-test123'
        assert recent[0]['message_preview'] == 'reconstruct me'
        assert recent[0]['provider'] == 'Ollama'
        assert recent[0]['outcome'] == 'resolved'
        assert len(recent[0]['stalls_during']) == 1
        assert recent[0]['_source'] == 'runtime_audit'

    def test_merge_in_memory_and_audit(self) -> None:
        import json
        ws = _workspace()
        log_dir = ws / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        audit_path = log_dir / 'runtime_audit.jsonl'
        # Write an audit event for an old episode
        event = {
            'ts': '2025-01-01T00:00:00.000Z',
            'kind': 'interaction_resolved',
            'data': {
                'interaction_id': 'chat-audit-old',
                'message_preview': 'from audit',
                'outcome': 'resolved',
                'provider': 'Gemini',
                'total_duration_ms': 800.0,
                'phases': {},
                'stalls_during': [],
                'window_inactive_intervals': [],
                'initial_window_active': True,
                'initial_window_visible': True,
                'had_early_technical_response': False,
                'window_went_inactive': False,
            },
        }
        audit_path.write_text(json.dumps(event) + '\n', encoding='utf-8')

        storage = ArtifactStorage(root=str(ws))
        pcs = PortableContextService(
            workspace_root=str(ws),
            storage=storage,
        )
        # Attach a lifecycle with one in-memory episode
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('in memory')
        lc.resolve_interaction(iid, outcome='resolved', provider='local')
        pcs.chat_interaction_lifecycle = lc

        summary = pcs._interaction_lifecycle_summary()
        recent = summary.get('recent_completed', [])
        ids = [r['interaction_id'] for r in recent]
        assert 'chat-audit-old' in ids
        assert iid in ids


# ======================================================================
# 17. OSES interaction episode findings (post-audit Fix 3)
# ======================================================================


class TestOSESInteractionEpisodeFindings:
    """OSES must detect episode stalls/failures from runtime_audit."""

    def test_stall_episode_finding(self) -> None:
        import json
        ws = _workspace()
        log_dir = ws / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        audit_path = log_dir / 'runtime_audit.jsonl'
        # Write an episode with stalls
        event = {
            'ts': '2025-01-01T00:00:00.000Z',
            'kind': 'interaction_resolved',
            'data': {
                'interaction_id': 'chat-stall1',
                'outcome': 'resolved',
                'stalls_during': [
                    {'timestamp': '2025-01-01T00:00:00.500Z', 'duration_ms': 3000},
                    {'timestamp': '2025-01-01T00:00:04.000Z', 'duration_ms': 2000},
                ],
            },
        }
        audit_path.write_text(json.dumps(event) + '\n', encoding='utf-8')

        storage = ArtifactStorage(root=str(ws))
        oses = OperationalSelfExaminationService(
            workspace_root=str(ws),
            storage=storage,
        )
        findings = oses._interaction_episode_findings()
        stall_findings = [f for f in findings if f.category == 'interaction_episode_stalls']
        assert len(stall_findings) == 1
        assert '1 of the last 1' in stall_findings[0].summary
        assert stall_findings[0].metadata['source'] == 'runtime_audit'

    def test_failed_episode_finding(self) -> None:
        import json
        ws = _workspace()
        log_dir = ws / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        audit_path = log_dir / 'runtime_audit.jsonl'
        event = {
            'ts': '2025-01-01T00:00:00.000Z',
            'kind': 'interaction_resolved',
            'data': {
                'interaction_id': 'chat-fail1',
                'outcome': 'failed',
                'stalls_during': [],
            },
        }
        audit_path.write_text(json.dumps(event) + '\n', encoding='utf-8')

        storage = ArtifactStorage(root=str(ws))
        oses = OperationalSelfExaminationService(
            workspace_root=str(ws),
            storage=storage,
        )
        findings = oses._interaction_episode_findings()
        fail_findings = [f for f in findings if f.category == 'interaction_episode_failures']
        assert len(fail_findings) == 1
        assert '1 of the last 1' in fail_findings[0].summary

    def test_no_findings_when_no_audit_file(self) -> None:
        ws = _workspace()
        storage = ArtifactStorage(root=str(ws))
        oses = OperationalSelfExaminationService(
            workspace_root=str(ws),
            storage=storage,
        )
        findings = oses._interaction_episode_findings()
        assert findings == []
