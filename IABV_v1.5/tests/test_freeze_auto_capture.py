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
            )
        assert vm._query_start_pc == 0.0


# ======================================================================
# 4c. OSES _query_stall_findings
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
