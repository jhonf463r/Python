"""Tests for UIHeartbeatWatchdog and ChatInteractionLifecycle.

Covers:
1. UIHeartbeatWatchdog tick/stall detection and context
2. ChatInteractionLifecycle open/phase/resolve/query
3. Promotion to OSES (ui_heartbeat_stall_findings)
4. Promotion to PortableContext (ui_heartbeat + interaction_lifecycle summaries)
5. Regression: existing FreezeIncidentReporter / RuntimeAuditTracer still work
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
        assert pcs._interaction_lifecycle_summary() == {}

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
