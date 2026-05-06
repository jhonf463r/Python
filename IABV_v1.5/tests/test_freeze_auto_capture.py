"""Tests for freeze auto-capture and promotion to OSES / PortableContext.

Covers:
1. Startup/post-startup freeze auto-capture via OSES → FreezeIncidentReporter
2. Chat stall / query freeze auto-capture via ControlCenterViewModel
3. Promotion of freeze incidents to PortableContext startup_health section
4. RuntimeAuditTracer.trace_freeze_incident typed helper
5. Dedup window prevents spam
"""

from __future__ import annotations

import json
import sys
import time
import threading
from datetime import datetime, timezone
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
)
from iabv_v15.services.evolution.runtime_audit_tracer import (
    RuntimeAuditTracer,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
    SelfExaminationFinding,
    IssueSeverity,
)
from iabv_v15.services.evolution.portable_context_service import (
    PortableContextService,
)


def _workspace() -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'freeze_auto_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


# ======================================================================
# 1. RuntimeAuditTracer.trace_freeze_incident
# ======================================================================


class TestTraceFreezeIncident:
    """trace_freeze_incident typed helper."""

    @pytest.fixture()
    def tracer(self) -> RuntimeAuditTracer:
        return RuntimeAuditTracer()

    def test_records_freeze_incident_event(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_freeze_incident(
            'startup_freeze',
            severity='critical',
            duration_ms=12345.6,
            dominant_phase='deferred_post_window',
            rss_mb=5210.0,
            report_path='/tmp/freeze_report.json',
        )
        assert e['kind'] == 'freeze_incident'
        assert e['data']['incident_type'] == 'startup_freeze'
        assert e['data']['severity'] == 'critical'
        assert e['data']['duration_ms'] == 12345.6
        assert e['data']['dominant_phase'] == 'deferred_post_window'
        assert e['data']['rss_mb'] == 5210.0
        assert e['data']['report_path'] == '/tmp/freeze_report.json'

    def test_chat_stall_event(self, tracer: RuntimeAuditTracer) -> None:
        e = tracer.trace_freeze_incident(
            'chat_stall',
            severity='medium',
            duration_ms=1800.5,
            dominant_phase='_chat_shortcut_analysis',
        )
        assert e['kind'] == 'freeze_incident'
        assert e['data']['incident_type'] == 'chat_stall'

    def test_events_filterable(self, tracer: RuntimeAuditTracer) -> None:
        tracer.trace('some_other_event')
        tracer.trace_freeze_incident('startup_freeze')
        tracer.trace_freeze_incident('chat_stall')
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 2


# ======================================================================
# 2. FreezeIncidentReporter auto-capture methods
# ======================================================================


class TestStartupFreezeAutoCapture:
    """capture_startup_freeze convenience method."""

    @pytest.fixture()
    def reporter(self, tmp_path: Path) -> FreezeIncidentReporter:
        return FreezeIncidentReporter(evolution_dir=str(tmp_path))

    def test_capture_creates_incident_file(self, reporter: FreezeIncidentReporter) -> None:
        findings = [
            {
                'category': 'startup_degradation',
                'title': 'Bootstrap init lento: 15000ms',
                'severity': 'IssueSeverity.HIGH',
                'metadata': {
                    'phase': 'bootstrap_init',
                    'observed_ms': 15000.0,
                    'threshold_ms': 5000.0,
                },
            },
        ]
        path = reporter.capture_startup_freeze(findings_metadata=findings)
        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['trigger'] == 'auto_startup_freeze'
        assert data['extra']['incident_type'] == 'startup_freeze'
        assert data['extra']['dominant_phase'] == 'bootstrap_init'
        assert data['extra']['dominant_phase_ms'] == 15000.0

    def test_dedup_prevents_second_capture(self, reporter: FreezeIncidentReporter) -> None:
        findings = [{'category': 'test', 'title': 'x', 'severity': 'high', 'metadata': {}}]
        path1 = reporter.capture_startup_freeze(findings_metadata=findings)
        path2 = reporter.capture_startup_freeze(findings_metadata=findings)
        assert path1 is not None
        assert path2 is None  # dedup blocked

    def test_dedup_expires(self, reporter: FreezeIncidentReporter) -> None:
        reporter._DEDUP_WINDOW_SECONDS = 0  # expire immediately
        findings = [{'category': 'test', 'title': 'x', 'severity': 'high', 'metadata': {}}]
        path1 = reporter.capture_startup_freeze(findings_metadata=findings)
        path2 = reporter.capture_startup_freeze(findings_metadata=findings)
        assert path1 is not None
        assert path2 is not None  # both captured


class TestChatStallAutoCapture:
    """capture_chat_stall convenience method."""

    @pytest.fixture()
    def reporter(self, tmp_path: Path) -> FreezeIncidentReporter:
        return FreezeIncidentReporter(evolution_dir=str(tmp_path))

    def test_capture_timeout_incident(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_chat_stall(
            duration_ms=3000.0,
            timed_out=True,
            message_summary='que hora es',
        )
        assert path is not None
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['trigger'] == 'auto_chat_stall'
        assert data['extra']['incident_type'] == 'chat_stall'
        assert data['extra']['severity'] == 'high'
        assert data['extra']['timed_out'] is True
        assert data['extra']['duration_ms'] == 3000.0

    def test_capture_slow_incident(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_chat_stall(
            duration_ms=2000.0,
            timed_out=False,
            message_summary='hola',
        )
        assert path is not None
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['extra']['severity'] == 'medium'
        assert data['extra']['timed_out'] is False

    def test_dedup_blocks_second(self, reporter: FreezeIncidentReporter) -> None:
        path1 = reporter.capture_chat_stall(duration_ms=3000, timed_out=True)
        path2 = reporter.capture_chat_stall(duration_ms=3000, timed_out=True)
        assert path1 is not None
        assert path2 is None


class TestQueryStallAutoCapture:
    """capture_query_stall convenience method — end-to-end query latency."""

    @pytest.fixture()
    def reporter(self, tmp_path: Path) -> FreezeIncidentReporter:
        return FreezeIncidentReporter(evolution_dir=str(tmp_path))

    def test_capture_orchestrator_path(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_query_stall(
            duration_ms=8000.0,
            resolved_path='orchestrator_inference',
            provider='ollama',
            route_reason='local_routing',
            success=True,
            message_summary='hola mundo',
        )
        assert path is not None
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['trigger'] == 'auto_query_stall'
        assert data['extra']['incident_type'] == 'query_stall'
        assert data['extra']['duration_ms'] == 8000.0
        assert data['extra']['resolved_path'] == 'orchestrator_inference'
        assert data['extra']['provider'] == 'ollama'
        assert data['extra']['success'] is True
        assert data['extra']['severity'] == 'medium'

    def test_capture_external_path(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_query_stall(
            duration_ms=20000.0,
            resolved_path='external_consultation',
            provider='chatgpt',
            route_reason='external_consultation',
            success=True,
            message_summary='help me with code',
        )
        assert path is not None
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['extra']['severity'] == 'high'  # >15s
        assert data['extra']['resolved_path'] == 'external_consultation'
        assert data['extra']['provider'] == 'chatgpt'

    def test_capture_failure_path(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_query_stall(
            duration_ms=6000.0,
            resolved_path='chat_failure',
            provider='',
            route_reason='No pude completar',
            success=False,
            message_summary='test',
        )
        assert path is not None
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['extra']['success'] is False
        assert '(failed)' in data['user_description']

    def test_dedup_blocks_second(self, reporter: FreezeIncidentReporter) -> None:
        path1 = reporter.capture_query_stall(
            duration_ms=8000.0, resolved_path='orchestrator_inference',
        )
        path2 = reporter.capture_query_stall(
            duration_ms=8000.0, resolved_path='orchestrator_inference',
        )
        assert path1 is not None
        assert path2 is None


class TestRecentIncidents:
    """recent_incidents summarizer for PortableContext."""

    @pytest.fixture()
    def reporter(self, tmp_path: Path) -> FreezeIncidentReporter:
        r = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        r._DEDUP_WINDOW_SECONDS = 0  # allow multiple captures
        return r

    def test_returns_structured_summaries(self, reporter: FreezeIncidentReporter) -> None:
        reporter.capture_startup_freeze(
            findings_metadata=[{
                'category': 'startup_degradation',
                'title': 'init lento',
                'severity': 'high',
                'metadata': {'phase': 'bootstrap_init', 'observed_ms': 10000},
            }],
        )
        reporter.capture_chat_stall(
            duration_ms=3000,
            timed_out=True,
            message_summary='test',
        )
        incidents = reporter.recent_incidents(limit=5)
        assert len(incidents) == 2
        types = {i['incident_type'] for i in incidents}
        assert types == {'startup_freeze', 'chat_stall'}
        for i in incidents:
            assert 'timestamp' in i
            assert 'trigger' in i


# ======================================================================
# 3. OSES auto-capture integration
# ======================================================================


class TestOsesAutoCapture:
    """_auto_capture_startup_freeze fires FreezeIncidentReporter."""

    def _make_oses(self, root: Path) -> OperationalSelfExaminationService:
        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        return OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=storage,
        )

    def test_fires_reporter_on_high_finding(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        oses._freeze_incident_reporter = reporter

        finding = SelfExaminationFinding(
            category='startup_degradation',
            title='Bootstrap init lento: 15000ms',
            summary='test',
            severity=IssueSeverity.HIGH,
            confidence=0.9,
            metadata={'phase': 'bootstrap_init', 'observed_ms': 15000.0},
        )
        oses._auto_capture_startup_freeze([finding])

        reports = reporter.list_reports()
        assert len(reports) == 1
        assert reports[0]['trigger'] == 'auto_startup_freeze'

    def test_skips_medium_findings(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        oses._freeze_incident_reporter = reporter

        finding = SelfExaminationFinding(
            category='startup_degradation',
            title='Deferred setup lento: 3000ms',
            summary='test',
            severity=IssueSeverity.MEDIUM,
            confidence=0.85,
            metadata={'phase': 'deferred_post_window', 'observed_ms': 3000.0},
        )
        oses._auto_capture_startup_freeze([finding])

        reports = reporter.list_reports()
        assert len(reports) == 0

    def test_skips_when_no_reporter(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        # No reporter wired — should not raise
        finding = SelfExaminationFinding(
            category='test', title='test', summary='test',
            severity=IssueSeverity.CRITICAL, confidence=0.9,
        )
        oses._auto_capture_startup_freeze([finding])  # should not raise


# ======================================================================
# 4. Chat stall tracing in ControlCenterViewModel
# ======================================================================


class TestViewModelChatStallTrace:
    """_trace_chat_stall fires RuntimeAuditTracer and FreezeIncidentReporter."""

    def _make_vm_stub(self) -> Any:
        """Minimal mock with just the _trace_chat_stall method bound."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        stub = MagicMock(spec=[])
        stub._freeze_incident_reporter = None
        stub._CHAT_STALL_THRESHOLD_MS = ControlCenterViewModel._CHAT_STALL_THRESHOLD_MS
        stub._trace_chat_stall = ControlCenterViewModel._trace_chat_stall.__get__(stub)
        return stub

    def test_below_threshold_does_nothing(self) -> None:
        vm = self._make_vm_stub()
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._trace_chat_stall(
                elapsed_ms=500.0,
                timed_out=False,
                message_summary='hi',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 0

    def test_above_threshold_traces_event(self) -> None:
        vm = self._make_vm_stub()
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._trace_chat_stall(
                elapsed_ms=2000.0,
                timed_out=False,
                message_summary='test message',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        assert freeze_events[0]['data']['incident_type'] == 'chat_stall'
        assert freeze_events[0]['data']['severity'] == 'medium'

    def test_timeout_traces_high_severity(self) -> None:
        vm = self._make_vm_stub()
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._trace_chat_stall(
                elapsed_ms=3000.0,
                timed_out=True,
                message_summary='test',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        assert freeze_events[0]['data']['severity'] == 'high'

    def test_fires_reporter_when_wired(self, tmp_path: Path) -> None:
        vm = self._make_vm_stub()
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        vm._freeze_incident_reporter = reporter
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._trace_chat_stall(
                elapsed_ms=3000.0,
                timed_out=True,
                message_summary='freeze test',
            )
        reports = reporter.list_reports()
        assert len(reports) == 1
        assert reports[0]['trigger'] == 'auto_chat_stall'


# ======================================================================
# 4b. End-to-end query stall tracing in ControlCenterViewModel
# ======================================================================


class TestViewModelQueryStallE2E:
    """_finalize_query_stall fires on end-to-end query latency."""

    def _make_vm_stub(self) -> Any:
        """Minimal mock with _finalize_query_stall bound."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        stub = MagicMock(spec=[])
        stub._freeze_incident_reporter = None
        stub._QUERY_STALL_THRESHOLD_MS = ControlCenterViewModel._QUERY_STALL_THRESHOLD_MS
        stub._finalize_query_stall = ControlCenterViewModel._finalize_query_stall.__get__(stub)
        stub._is_useful_response = ControlCenterViewModel._is_useful_response
        stub._query_start_pc = 0.0
        stub._query_start_message = ''
        return stub

    def test_below_threshold_does_nothing(self) -> None:
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 1.0  # 1s ago = below 5s
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
                response_text='Respuesta rapida util.',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 0

    def test_above_threshold_traces_event(self) -> None:
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 8.0  # 8s ago
        vm._query_start_message = 'hola'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local_routing',
                success=True,
                response_text='Aqui tienes la respuesta util.',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        data = freeze_events[0]['data']
        assert data['incident_type'] == 'query_stall'
        assert data['dominant_phase'] == 'orchestrator_inference'
        assert data['provider'] == 'ollama'
        assert data['success'] is True

    def test_external_consultation_path(self) -> None:
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 12.0
        vm._query_start_message = 'ayuda con codigo'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_stall(
                resolved_path='external_consultation',
                provider='chatgpt',
                route_reason='external_consultation',
                success=True,
                response_text='ChatGPT respondio con codigo funcional.',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        assert freeze_events[0]['data']['dominant_phase'] == 'external_consultation'
        assert freeze_events[0]['data']['provider'] == 'chatgpt'

    def test_failure_path_traces(self) -> None:
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 6.0
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_stall(
                resolved_path='chat_failure',
                provider='',
                route_reason='No pude completar',
                success=False,
                response_text='No pude completar la consulta local: timeout.',
            )
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        assert freeze_events[0]['data']['success'] is False

    def test_fires_reporter_when_wired(self, tmp_path: Path) -> None:
        vm = self._make_vm_stub()
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        vm._freeze_incident_reporter = reporter
        vm._query_start_pc = time.perf_counter() - 10.0
        vm._query_start_message = 'freeze test msg'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
                response_text='Respuesta completa del modelo.',
            )
        reports = reporter.list_reports()
        assert len(reports) == 1
        assert reports[0]['trigger'] == 'auto_query_stall'

    def test_resets_start_pc_after_finalize(self) -> None:
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 10.0
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='',
                route_reason='local',
                success=True,
                response_text='Resultado util y final.',
            )
        assert vm._query_start_pc == 0.0

    def test_empty_response_does_not_consume_timer(self) -> None:
        """First emission with empty/whitespace content must NOT reset timer."""
        vm = self._make_vm_stub()
        start_pc = time.perf_counter() - 8.0
        vm._query_start_pc = start_pc
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            # First call with empty/whitespace — should NOT finalize
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
                response_text='  ',
            )
        # Timer still running
        assert vm._query_start_pc == start_pc
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 0

    def test_two_phase_captures_stall_on_useful_response(self) -> None:
        """Empty first emission + useful second emission = stall captured."""
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 10.0
        vm._query_start_message = 'consulta compleja'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            # Phase 1: empty emission — timer NOT consumed
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
                response_text='  ',
            )
            assert vm._query_start_pc != 0.0  # still running
            # Phase 2: useful response — timer consumed, stall captured
            vm._finalize_query_stall(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
                response_text='Aqui tienes la respuesta util final.',
            )
        assert vm._query_start_pc == 0.0
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        assert freeze_events[0]['data']['duration_ms'] > 9000

    def test_external_blocked_empty_then_useful(self) -> None:
        """External consultation: empty first + blocked message later = captured."""
        vm = self._make_vm_stub()
        vm._query_start_pc = time.perf_counter() - 720.0  # 12 minutes
        vm._query_start_message = 'ayuda'
        reporter = FreezeIncidentReporter(evolution_dir='/tmp/test_ext_' + str(int(time.time())))
        vm._freeze_incident_reporter = reporter
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            # Phase 1: empty/placeholder emission
            vm._finalize_query_stall(
                resolved_path='external_blocked',
                provider='chatgpt',
                route_reason='external_consultation',
                success=False,
                response_text='',
            )
            assert vm._query_start_pc != 0.0  # not consumed
            # Phase 2: real blocked message
            vm._finalize_query_stall(
                resolved_path='external_blocked',
                provider='chatgpt',
                route_reason='external_consultation',
                success=False,
                response_text='No pude completar la consulta externa: acceso denegado por gobernanza.',
            )
        assert vm._query_start_pc == 0.0
        freeze_events = tracer.events(kind='freeze_incident')
        assert len(freeze_events) == 1
        assert freeze_events[0]['data']['severity'] == 'high'  # >15s
        reports = reporter.list_reports()
        assert len(reports) == 1

    def test_trivial_placeholder_does_not_consume(self) -> None:
        """Trivial placeholders like '...' or 'loading' don't consume timer."""
        vm = self._make_vm_stub()
        start_pc = time.perf_counter() - 6.0
        vm._query_start_pc = start_pc
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            for placeholder in ['...', '\u2026', '---', 'loading', 'Cargando', '  ']:
                vm._finalize_query_stall(
                    resolved_path='orchestrator_inference',
                    provider='',
                    route_reason='local',
                    success=True,
                    response_text=placeholder,
                )
        assert vm._query_start_pc == start_pc  # none consumed the timer
        assert len(tracer.events(kind='freeze_incident')) == 0


# ======================================================================
# 4c. Query visible gap — user-perceived response gap
# ======================================================================


class TestViewModelQueryVisibleGap:
    """_finalize_query_visible_gap fires on prolonged user-visible gap."""

    def _make_vm_stub(self) -> Any:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        stub = MagicMock(spec=[])
        stub._freeze_incident_reporter = None
        stub._VISIBLE_GAP_THRESHOLD_MS = ControlCenterViewModel._VISIBLE_GAP_THRESHOLD_MS
        stub._finalize_query_visible_gap = ControlCenterViewModel._finalize_query_visible_gap.__get__(stub)
        stub._reset_visible_gap_state = ControlCenterViewModel._reset_visible_gap_state.__get__(stub)
        stub.notify_window_active_changed = ControlCenterViewModel.notify_window_active_changed.__get__(stub)
        stub._query_start_pc = 0.0
        stub._visible_gap_start_pc = 0.0
        stub._query_start_message = ''
        stub._query_dispatch_pending = False
        stub._window_went_inactive = False
        stub._window_inactive_at = 0.0
        stub._window_inactive_total_ms = 0.0
        stub._query_had_early_technical = False
        return stub

    def test_below_threshold_does_nothing(self) -> None:
        """Gap below 30s threshold does not fire."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = time.perf_counter() - 10.0  # 10s < 30s
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
            )
        assert len(tracer.events(kind='freeze_incident')) == 0

    def test_above_threshold_fires_gap_incident(self) -> None:
        """Gap above 30s traces a query_visible_gap incident."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = time.perf_counter() - 45.0  # 45s
        vm._query_start_message = 'haz una consulta a chatgpt'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='external_consultation',
                provider='chatgpt',
                route_reason='external_consultation',
                success=True,
            )
        events = tracer.events(kind='freeze_incident')
        assert len(events) == 1
        data = events[0]['data']
        assert data['incident_type'] == 'query_visible_gap'
        assert data['duration_ms'] > 44000
        assert data['cause'] == 'UNRESOLVED'
        assert data['dominant_phase'] == 'external_consultation'

    def test_window_inactive_correlation(self) -> None:
        """Window going inactive during query is recorded in the gap incident."""
        vm = self._make_vm_stub()
        _start = time.perf_counter() - 1800.0  # 30 minutes
        vm._visible_gap_start_pc = _start
        vm._query_start_message = 'consulta larga'
        # Simulate window going inactive
        vm.notify_window_active_changed(False)
        assert vm._window_went_inactive is True
        assert vm._window_inactive_at > 0
        # Simulate window coming back active after 20 min
        time.sleep(0.01)  # tiny sleep for perf_counter delta
        vm.notify_window_active_changed(True)
        assert vm._window_inactive_at == 0.0
        assert vm._window_inactive_total_ms > 0
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='external_blocked',
                provider='chatgpt',
                route_reason='external_consultation',
                success=False,
            )
        events = tracer.events(kind='freeze_incident')
        assert len(events) == 1
        data = events[0]['data']
        assert data['window_went_inactive'] is True
        assert data['window_inactive_total_ms'] > 0

    def test_fires_reporter_when_wired(self, tmp_path: Path) -> None:
        """When FreezeIncidentReporter is wired, capture_query_visible_gap fires."""
        vm = self._make_vm_stub()
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        vm._freeze_incident_reporter = reporter
        vm._visible_gap_start_pc = time.perf_counter() - 60.0  # 1 min
        vm._query_start_message = 'test gap reporter'
        vm._window_went_inactive = True
        vm._window_inactive_total_ms = 55000.0
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='external_blocked',
                provider='chatgpt',
                route_reason='external_consultation',
                success=False,
                had_early_technical_response=True,
            )
        reports = reporter.list_reports()
        assert len(reports) == 1
        assert reports[0]['trigger'] == 'auto_query_visible_gap'

    def test_critical_severity_for_very_long_gap(self) -> None:
        """Gap >5 min gets critical severity."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = time.perf_counter() - 400.0  # ~6.6 min
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
            )
        events = tracer.events(kind='freeze_incident')
        assert len(events) == 1
        assert events[0]['data']['severity'] == 'critical'

    def test_notify_window_noop_without_pending_query(self) -> None:
        """notify_window_active_changed does nothing when no query pending."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = 0.0
        vm.notify_window_active_changed(False)
        assert vm._window_went_inactive is False

    def test_reset_visible_gap_state(self) -> None:
        """_reset_visible_gap_state clears all tracking attributes."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = 123.0
        vm._query_dispatch_pending = True
        vm._window_went_inactive = True
        vm._window_inactive_at = 123.0
        vm._window_inactive_total_ms = 50000.0
        vm._reset_visible_gap_state()
        assert vm._visible_gap_start_pc == 0.0
        assert vm._query_dispatch_pending is False
        assert vm._window_went_inactive is False
        assert vm._window_inactive_at == 0.0
        assert vm._window_inactive_total_ms == 0.0

    def test_had_early_technical_response_flag(self) -> None:
        """had_early_technical_response is recorded in the incident."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = time.perf_counter() - 60.0
        vm._query_start_message = 'test'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
                had_early_technical_response=True,
            )
        events = tracer.events(kind='freeze_incident')
        assert events[0]['data']['had_early_technical_response'] is True

    def test_dispatch_does_not_close_visible_gap(self) -> None:
        """Dispatch response does NOT close the visible gap timer.

        When ``_query_dispatch_pending`` is True, the timer stays alive
        so the final resolution can still detect the full gap.
        """
        vm = self._make_vm_stub()
        start_pc = time.perf_counter() - 5.0  # 5s (< 30s threshold)
        vm._visible_gap_start_pc = start_pc
        vm._query_dispatch_pending = True
        vm._query_start_message = 'haz una consulta a chatgpt'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            # Simulate chat resolution with dispatch pending — should NOT fire
            vm._finalize_query_visible_gap(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
            )
        # Below threshold AND dispatch pending — timer should survive
        assert len(tracer.events(kind='freeze_incident')) == 0
        # Timer NOT consumed — visible_gap_start_pc still alive
        assert vm._visible_gap_start_pc == start_pc

    def test_dispatch_then_late_final_fires_gap(self) -> None:
        """Dispatch early → final resolution much later → gap incident fires.

        Simulates: user sends query → dispatch "consulta aceptada" → 10 min
        of external consultation → final resolution → query_visible_gap fires.
        """
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = time.perf_counter() - 600.0  # 10 min
        vm._query_dispatch_pending = True
        vm._query_had_early_technical = True
        vm._query_start_message = 'haz una consulta a chatgpt'
        vm._window_went_inactive = True
        vm._window_inactive_total_ms = 540000.0  # 9 min inactive
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            # Final resolution arrives (external_consultation resolved)
            vm._finalize_query_visible_gap(
                resolved_path='external_consultation',
                provider='chatgpt',
                route_reason='external_consultation',
                success=True,
                had_early_technical_response=True,
            )
        events = tracer.events(kind='freeze_incident')
        assert len(events) == 1
        data = events[0]['data']
        assert data['incident_type'] == 'query_visible_gap'
        assert data['duration_ms'] > 590000
        assert data['had_early_technical_response'] is True
        assert data['window_went_inactive'] is True
        assert data['cause'] == 'UNRESOLVED'
        assert data['severity'] == 'critical'  # > 5 min

    def test_fast_final_no_dispatch_no_incident(self) -> None:
        """Fast query without dispatch → no incident, timer consumed."""
        vm = self._make_vm_stub()
        vm._visible_gap_start_pc = time.perf_counter() - 2.0  # 2s
        vm._query_dispatch_pending = False
        vm._query_start_message = 'hola'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='orchestrator_inference',
                provider='ollama',
                route_reason='local',
                success=True,
            )
        assert len(tracer.events(kind='freeze_incident')) == 0

    def test_dispatch_external_failure_fires_gap(self, tmp_path: Path) -> None:
        """Dispatch → external consultation fails → gap fires with reporter."""
        vm = self._make_vm_stub()
        reporter = FreezeIncidentReporter(evolution_dir=str(tmp_path))
        vm._freeze_incident_reporter = reporter
        vm._visible_gap_start_pc = time.perf_counter() - 120.0  # 2 min
        vm._query_dispatch_pending = True
        vm._query_had_early_technical = True
        vm._query_start_message = 'consulta a chatgpt'
        tracer = RuntimeAuditTracer()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=tracer,
        ):
            vm._finalize_query_visible_gap(
                resolved_path='external_blocked',
                provider='chatgpt',
                route_reason='external_consultation',
                success=False,
                had_early_technical_response=True,
            )
        # Tracer fired
        events = tracer.events(kind='freeze_incident')
        assert len(events) == 1
        assert events[0]['data']['severity'] == 'high'
        # Reporter captured
        reports = reporter.list_reports()
        assert len(reports) == 1
        assert reports[0]['trigger'] == 'auto_query_visible_gap'

    def test_dispatch_pending_set_by_run_external(self) -> None:
        """_run_external_consultation sets _query_dispatch_pending."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        vm = MagicMock(spec=[])
        vm._working = False
        vm._query_dispatch_pending = False
        vm._latest_response_text = ''
        vm._latest_response_meta = ''
        vm._attached_files = None
        vm._set_autonomy_activity_override = MagicMock()
        vm._append_message = MagicMock()
        vm._assistant_display_name = MagicMock(return_value='ChatGPT')
        vm._execute_external_consultation_sync = MagicMock(return_value={})
        vm.dataChanged = MagicMock()
        vm.dataChanged.emit = MagicMock()
        vm.taskResolved = MagicMock()
        vm.taskResolved.emit = MagicMock()
        # Call the method directly
        ControlCenterViewModel._run_external_consultation(vm, 'chatgpt', announce=False)
        assert vm._query_dispatch_pending is True


# ======================================================================
# 4d. OSES _query_visible_gap_findings
# ======================================================================


class TestOsesQueryVisibleGapFindings:
    """_query_visible_gap_findings promotes visible gap incidents to OSES."""

    def _make_oses(self, root: Path) -> OperationalSelfExaminationService:
        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        return OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=storage,
        )

    def test_promotes_visible_gap_incident(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        oses._freeze_incident_reporter = reporter

        reporter.capture_query_visible_gap(
            duration_ms=120000.0,
            resolved_path='external_blocked',
            provider='chatgpt',
            route_reason='external_consultation',
            success=False,
            window_went_inactive=True,
            window_inactive_total_ms=110000.0,
            message_summary='haz una consulta a chatgpt',
        )

        findings = oses._query_visible_gap_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.category == 'query_visible_gap'
        assert f.severity == IssueSeverity.HIGH
        assert f.metadata['duration_ms'] == 120000.0
        assert f.metadata['window_went_inactive'] is True
        assert f.metadata['cause'] == 'UNRESOLVED'

    def test_critical_for_very_long_gap(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        oses._freeze_incident_reporter = reporter

        reporter.capture_query_visible_gap(
            duration_ms=600000.0,  # 10 min
            resolved_path='external_blocked',
            provider='chatgpt',
            success=False,
        )

        findings = oses._query_visible_gap_findings()
        assert len(findings) == 1
        assert findings[0].severity == IssueSeverity.CRITICAL

    def test_empty_without_reporter(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        assert oses._query_visible_gap_findings() == []

    def test_ignores_non_gap_incidents(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        reporter._DEDUP_WINDOW_SECONDS = 0
        oses._freeze_incident_reporter = reporter

        reporter.capture_query_stall(
            duration_ms=9000.0,
            resolved_path='orchestrator_inference',
            provider='ollama',
            success=True,
        )
        findings = oses._query_visible_gap_findings()
        assert len(findings) == 0


# ======================================================================
# 4e. PortableContext includes query_visible_gap
# ======================================================================


class TestPortableContextVisibleGap:
    """PortableContext startup_health_section includes visible gap incidents."""

    def _make_pcs(self, root: Path) -> PortableContextService:
        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        return PortableContextService(
            workspace_root=str(root),
            storage=storage,
        )

    def test_startup_health_section_includes_visible_gap(self) -> None:
        root = _workspace()
        pcs = self._make_pcs(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        reporter._DEDUP_WINDOW_SECONDS = 0
        pcs.freeze_incident_reporter = reporter

        reporter.capture_query_visible_gap(
            duration_ms=120000.0,
            resolved_path='external_blocked',
            provider='chatgpt',
            success=False,
            window_went_inactive=True,
            window_inactive_total_ms=100000.0,
            had_early_technical_response=True,
            message_summary='haz una consulta',
        )

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        section = pcs._startup_health_section(
            status={'status': 'no_log', 'unresolved_fields': []},
            now=now,
        )
        freeze_items = [
            i for i in section.items if i.get('label') == 'freeze_incident'
        ]
        assert len(freeze_items) == 1
        item = freeze_items[0]
        assert item['incident_type'] == 'query_visible_gap'
        assert item.get('window_went_inactive') is True
        assert item.get('cause') == 'UNRESOLVED'
        assert item.get('had_early_technical_response') is True
        assert section.metadata.get('freeze_incidents')


# ======================================================================
# 4f. OSES _query_stall_findings (existing)
# ======================================================================


class TestOsesQueryStallFindings:
    """_query_stall_findings reads recent incidents and promotes to findings."""

    def _make_oses(self, root: Path) -> OperationalSelfExaminationService:
        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        return OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=storage,
        )

    def test_promotes_query_stall_incident(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        oses._freeze_incident_reporter = reporter

        reporter.capture_query_stall(
            duration_ms=9000.0,
            resolved_path='orchestrator_inference',
            provider='ollama',
            route_reason='local_routing',
            success=True,
            message_summary='hola test',
        )

        findings = oses._query_stall_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.category == 'query_stall'
        assert f.severity == IssueSeverity.MEDIUM
        assert f.metadata['duration_ms'] == 9000.0
        assert f.metadata['resolved_path'] == 'orchestrator_inference'

    def test_high_severity_for_long_stall(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        oses._freeze_incident_reporter = reporter

        reporter.capture_query_stall(
            duration_ms=20000.0,
            resolved_path='external_consultation',
            provider='chatgpt',
            success=True,
        )

        findings = oses._query_stall_findings()
        assert len(findings) == 1
        assert findings[0].severity == IssueSeverity.HIGH

    def test_empty_without_reporter(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        assert oses._query_stall_findings() == []

    def test_ignores_non_query_stall_incidents(self) -> None:
        root = _workspace()
        oses = self._make_oses(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        reporter._DEDUP_WINDOW_SECONDS = 0
        oses._freeze_incident_reporter = reporter

        reporter.capture_startup_freeze(
            findings_metadata=[{
                'category': 'startup_degradation',
                'title': 'init lento',
                'severity': 'high',
                'metadata': {'phase': 'bootstrap_init', 'observed_ms': 15000},
            }],
        )
        findings = oses._query_stall_findings()
        assert len(findings) == 0


# ======================================================================
# 5. PortableContext promotion
# ======================================================================


class TestPortableContextFreezePromotion:
    """_recent_freeze_incidents and _startup_health_section include incidents."""

    def _make_pcs(self, root: Path) -> PortableContextService:
        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        return PortableContextService(
            workspace_root=str(root),
            storage=storage,
        )

    def test_recent_freeze_incidents_empty_without_reporter(self) -> None:
        root = _workspace()
        pcs = self._make_pcs(root)
        assert pcs._recent_freeze_incidents() == []

    def test_recent_freeze_incidents_returns_data(self) -> None:
        root = _workspace()
        pcs = self._make_pcs(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        reporter._DEDUP_WINDOW_SECONDS = 0
        pcs.freeze_incident_reporter = reporter

        reporter.capture_startup_freeze(
            findings_metadata=[{
                'category': 'startup_degradation',
                'title': 'init lento',
                'severity': 'high',
                'metadata': {'phase': 'bootstrap_init', 'observed_ms': 10000},
            }],
        )
        incidents = pcs._recent_freeze_incidents()
        assert len(incidents) == 1
        assert incidents[0]['incident_type'] == 'startup_freeze'

    def test_startup_health_section_includes_freeze_items(self) -> None:
        root = _workspace()
        pcs = self._make_pcs(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        reporter._DEDUP_WINDOW_SECONDS = 0
        pcs.freeze_incident_reporter = reporter

        reporter.capture_chat_stall(
            duration_ms=3000, timed_out=True, message_summary='test',
        )

        now = datetime.now(timezone.utc)
        section = pcs._startup_health_section(
            status={'status': 'no_log', 'unresolved_fields': []},
            now=now,
        )
        freeze_items = [
            i for i in section.items if i.get('label') == 'freeze_incident'
        ]
        assert len(freeze_items) == 1
        assert freeze_items[0]['incident_type'] == 'chat_stall'
        assert section.metadata.get('freeze_incidents')

    def test_startup_health_section_includes_query_stall(self) -> None:
        root = _workspace()
        pcs = self._make_pcs(root)
        reporter = FreezeIncidentReporter(evolution_dir=str(root))
        reporter._DEDUP_WINDOW_SECONDS = 0
        pcs.freeze_incident_reporter = reporter

        reporter.capture_query_stall(
            duration_ms=9000.0,
            resolved_path='orchestrator_inference',
            provider='ollama',
            route_reason='local_routing',
            success=True,
            message_summary='hola',
        )

        now = datetime.now(timezone.utc)
        section = pcs._startup_health_section(
            status={'status': 'no_log', 'unresolved_fields': []},
            now=now,
        )
        freeze_items = [
            i for i in section.items if i.get('label') == 'freeze_incident'
        ]
        assert len(freeze_items) == 1
        assert freeze_items[0]['incident_type'] == 'query_stall'
        assert freeze_items[0].get('resolved_path') == 'orchestrator_inference'
        assert section.metadata.get('freeze_incidents')
