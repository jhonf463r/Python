"""Tests for runtime trace correlation and self-observability.

Covers the 6 mandatory test categories:
1. Local interaction without tool gate persists canonical reason
2. PortableContext tool_coordination shows items even without selected_tool
3. External selection persists tool/fallback/quota
4. Startup/runtime degradation findings include trace refs
5. Execution dossier metadata correlates with adaptive_session
6. Regression: existing tests still pass
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    DecisionContext,
    EnvironmentSelfModel,
    IntentDisposition,
    IntentRouteDecision,
    IssueSeverity,
    PerceptionSnapshot,
    SelfExaminationFinding,
    TaskContext,
    TaskIntent,
    TaskRole,
    WorldModelSnapshot,
)

# --- Helpers for building test fixtures --------------------------------


def _mock_session(
    *,
    session_id: str = 'sess-001',
    intent_key: str = 'knowledge.query',
    pack_id: str = 'knowledge.query',
    pack_title: str = 'Consulta local con contexto',
    disposition: str = 'answer_now',
    metadata: dict[str, Any] | None = None,
) -> AdaptiveSession:
    intent = TaskIntent(
        intent_key=intent_key,
        summary='test',
        title='Base de conocimiento',
        detected_role=TaskRole.KNOWLEDGE,
        disposition=IntentDisposition(disposition),
    )
    session = AdaptiveSession(
        session_id=session_id,
        user_goal='test goal',
        intent=intent,
        context=TaskContext(),
        chosen_pack_id=pack_id,
        chosen_pack_title=pack_title,
        metadata=metadata or {},
        status=AdaptiveSessionStatus.COMPLETED,
    )
    return session


def _mock_decision_context(*, governance: dict | None = None) -> DecisionContext:
    intent = TaskIntent(
        intent_key='knowledge.query',
        summary='test',
        title='Base de conocimiento',
        detected_role=TaskRole.KNOWLEDGE,
    )
    return DecisionContext(
        user_goal='test goal',
        intent=intent,
        route_decision=IntentRouteDecision(
            detected_role=TaskRole.KNOWLEDGE,
            reason='test route',
        ),
        governance=governance or {},
        metadata={},
    )


def _mock_perception() -> PerceptionSnapshot:
    p = MagicMock(spec=PerceptionSnapshot)
    p.metadata = {}
    p.unresolved_fields = []
    return p


# --- Category 1: Local interaction without tool gate -------------------

class TestLocalInteractionGateNotRan:
    """Verify that interactions where the tool gate does NOT run persist
    structured canonical reasons."""

    def test_gate_not_ran_reason_external_not_requested(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={},
            gate_ran=False,
            governance={'should_consult': False},
            session_metadata={},
        )
        assert result['reason'] == 'external_route_not_requested'
        assert result['gate_ran'] is False
        assert result['selected_tool'] == ''
        assert result['routed_locally'] is True

    def test_gate_not_ran_reason_blocked_by_world_model(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={},
            gate_ran=False,
            governance={'should_consult': True, 'block_risky_action': True},
            session_metadata={},
        )
        assert result['reason'] == 'blocked_by_world_model'
        assert result['gate_ran'] is False
        assert result['requested_external_consultation'] is True
        assert result['routed_locally'] is True

    def test_gate_not_ran_reason_approval_required(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={},
            gate_ran=False,
            governance={'should_consult': True, 'approval_required': True},
            session_metadata={},
        )
        assert result['reason'] == 'approval_required_not_granted'

    def test_gate_not_ran_fallback_reason(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={},
            gate_ran=False,
            governance={'should_consult': True},
            session_metadata={},
        )
        assert result['reason'] == 'gate_not_ran'
        assert result['fallback_used'] is False
        assert result['quota_confirmed'] is False

    def test_gate_ran_no_worker(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={'usable': False, 'available_count': 0},
            gate_ran=True,
            governance={'should_consult': True},
            session_metadata={},
        )
        assert result['reason'] == 'no_worker'
        assert result['gate_ran'] is True

    def test_gate_ran_unusable(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={'usable': False, 'available_count': 2},
            gate_ran=True,
            governance={'should_consult': True},
            session_metadata={},
        )
        assert result['reason'] == 'gate_unusable'


class TestTaskPacketRouteReason:
    """Verify that _build_task_packet includes route_reason and chosen_pack_id."""

    def test_task_packet_includes_route_fields(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )
        session = _mock_session()
        dc = _mock_decision_context()
        perception = _mock_perception()
        tp = AdaptiveTaskOrchestrator._build_task_packet(
            session=session,
            decision_context=dc,
            perception=perception,
        )
        assert tp['chosen_pack_id'] == 'knowledge.query'
        assert tp['disposition'] == 'answer_now'
        assert 'knowledge.query' in tp['route_reason']
        assert 'Consulta local con contexto' in tp['route_reason']
        assert tp['intent_key'] == 'knowledge.query'

    def test_task_packet_tool_selection_has_gate_ran(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )
        session = _mock_session()
        dc = _mock_decision_context()
        perception = _mock_perception()
        tp = AdaptiveTaskOrchestrator._build_task_packet(
            session=session,
            decision_context=dc,
            perception=perception,
        )
        tss = tp['tool_selection_summary']
        assert 'gate_ran' in tss
        assert 'reason' in tss
        assert 'requested_external_consultation' in tss
        assert 'routed_locally' in tss


# --- Category 2: PortableContext shows items without selected_tool -----

class TestPortableContextToolCoordination:
    """Verify that tool_coordination section shows items even when
    no external tool was selected (gate_not_ran / continue_local)."""

    def _build_service_with_sessions(self, sessions):
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        mock_repo = MagicMock()
        mock_repo.list_recent.return_value = sessions
        svc = PortableContextService(
            workspace_root='/tmp/test',
            storage=MagicMock(),
            adaptive_session_repository=mock_repo,
        )
        return svc

    def test_local_flow_appears_in_tool_coordination(self):
        session = _mock_session(metadata={
            'task_packet': {
                'route_reason': 'knowledge.query -> consulta local',
                'chosen_pack_id': 'knowledge.query',
                'tool_selection_summary': {
                    'selected_tool': '',
                    'reason': 'external_route_not_requested',
                    'gate_ran': False,
                },
            },
        })
        svc = self._build_service_with_sessions([session])
        now = datetime.now(timezone.utc)
        section = svc._tool_coordination_section(now=now)
        assert len(section.items) == 1
        item = section.items[0]
        assert 'local:knowledge.query' in item['label']
        assert 'external_route_not_requested' in item['value']
        assert 'UNRESOLVED:no_recent_tool_selections' not in section.unresolved_fields

    def test_external_flow_appears_in_tool_coordination(self):
        session = _mock_session(metadata={
            'task_packet': {
                'route_reason': 'external consultation',
                'chosen_pack_id': 'external.consult',
                'tool_selection_summary': {
                    'selected_tool': 'chatgpt',
                    'reason': 'source=auto_ranked',
                    'gate_ran': True,
                    'fallback_used': False,
                    'quota_confirmed': True,
                    'alternatives_discarded': [],
                },
            },
        })
        svc = self._build_service_with_sessions([session])
        now = datetime.now(timezone.utc)
        section = svc._tool_coordination_section(now=now)
        assert len(section.items) == 1
        assert 'seleccion:chatgpt' in section.items[0]['label']

    def test_empty_sessions_still_unresolved(self):
        svc = self._build_service_with_sessions([])
        now = datetime.now(timezone.utc)
        section = svc._tool_coordination_section(now=now)
        assert 'UNRESOLVED:no_recent_tool_selections' in section.unresolved_fields

    def test_mixed_sessions_both_appear(self):
        s1 = _mock_session(session_id='s1', metadata={
            'task_packet': {
                'route_reason': 'local route',
                'chosen_pack_id': 'knowledge.query',
                'tool_selection_summary': {
                    'selected_tool': '',
                    'reason': 'gate_not_ran',
                    'gate_ran': False,
                },
            },
        })
        s2 = _mock_session(session_id='s2', metadata={
            'task_packet': {
                'route_reason': 'external consult',
                'chosen_pack_id': 'external.consult',
                'tool_selection_summary': {
                    'selected_tool': 'devin',
                    'reason': 'source=auto_ranked',
                    'gate_ran': True,
                    'fallback_used': False,
                    'quota_confirmed': True,
                    'alternatives_discarded': [],
                },
            },
        })
        svc = self._build_service_with_sessions([s1, s2])
        now = datetime.now(timezone.utc)
        section = svc._tool_coordination_section(now=now)
        assert len(section.items) == 2
        labels = [i['label'] for i in section.items]
        assert any('local:' in l for l in labels)
        assert any('seleccion:devin' in l for l in labels)


# --- Category 3: External selection persists tool/fallback/quota -------

class TestExternalSelectionPersistence:
    """Verify that sessions with external tool selection persist
    selected_tool, fallback_used, and quota_confirmed."""

    def test_external_tool_selection_fields(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={
                'usable': True,
                'top_worker': {'tool': 'chatgpt', 'email': 'user@test.com', 'remaining': 50},
                'available_count': 3,
                'ranked_workers': [
                    {'tool': 'chatgpt', 'email': 'user@test.com'},
                    {'tool': 'devin', 'email': 'dev@test.com'},
                ],
                'account_selection_source': 'auto_ranked',
            },
            gate_ran=True,
            governance={'assistant_kind': 'chatgpt', 'should_consult': True},
            session_metadata={},
        )
        assert result['selected_tool'] == 'chatgpt'
        assert result['reason'] == 'source=auto_ranked'
        assert result['fallback_used'] is False
        assert result['quota_confirmed'] is True
        assert result['gate_ran'] is True
        assert len(result['alternatives_discarded']) == 1

    def test_external_with_fallback(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={
                'usable': True,
                'top_worker': {'tool': 'devin', 'email': 'dev@test.com'},
                'available_count': 1,
                'ranked_workers': [{'tool': 'devin', 'email': 'dev@test.com'}],
                'account_selection_source': 'auto_ranked',
                'fallback_used': True,
                'recommended_account': {'tool': 'chatgpt'},
            },
            gate_ran=True,
            governance={'assistant_kind': 'devin', 'should_consult': True},
            session_metadata={},
        )
        assert result['fallback_used'] is True
        assert result['fallback_origin'] == 'chatgpt'


# --- Category 4: Startup degradation findings include trace refs -------

class TestStartupFindingsTraceRefs:
    """Verify that OSES startup/runtime degradation findings include
    metadata.trace_refs with enough info to locate the trace."""

    def _make_timeline(self, events: list[dict]) -> str:
        return '\n'.join(json.dumps(e) for e in events)

    def test_startup_degradation_has_trace_refs(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        logs_dir = tmp_path / 'data' / 'logs'
        logs_dir.mkdir(parents=True)
        events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 100.0},
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 6000.0, 'rss_mb': 200.0},
            {'phase': 'run_start', 't_ms_from_start': 6500.0, 'rss_mb': 210.0},
            {'phase': 'main_window_shown', 't_ms_from_start': 18000.0, 'rss_mb': 400.0},
        ]
        timeline_path = logs_dir / 'startup_timeline.jsonl'
        timeline_path.write_text(self._make_timeline(events), encoding='utf-8')

        svc = OperationalSelfExaminationService(
            workspace_root=str(tmp_path),
            storage=MagicMock(),
        )
        findings = svc._startup_health_findings()
        assert len(findings) >= 1
        for f in findings:
            assert 'trace_refs' in f.metadata
            refs = f.metadata['trace_refs']
            assert refs['startup_timeline_path'] == 'data/logs/startup_timeline.jsonl'
            assert refs['rss_peak_mb'] == 400.0
            assert refs['slowest_phase'] == 'main_window_shown'
            assert refs['phases_count'] >= 3

    def test_memory_spike_finding_has_trace_refs(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        logs_dir = tmp_path / 'data' / 'logs'
        logs_dir.mkdir(parents=True)
        events = [
            {'phase': 'run_start', 't_ms_from_start': 0.0, 'rss_mb': 100.0},
            {'phase': 'populate_ui_start', 't_ms_from_start': 1000.0, 'rss_mb': 150.0},
            {'phase': 'populate_ui_done', 't_ms_from_start': 2000.0, 'rss_mb': 500.0},
            {'phase': 'main_window_shown', 't_ms_from_start': 3000.0, 'rss_mb': 510.0},
        ]
        timeline_path = logs_dir / 'startup_timeline.jsonl'
        timeline_path.write_text(self._make_timeline(events), encoding='utf-8')

        svc = OperationalSelfExaminationService(
            workspace_root=str(tmp_path),
            storage=MagicMock(),
        )
        findings = svc._startup_health_findings()
        memory_findings = [f for f in findings if f.category == 'startup_memory_spike']
        assert len(memory_findings) >= 1
        refs = memory_findings[0].metadata['trace_refs']
        assert 'rss_peak_mb' in refs
        assert refs['rss_peak_mb'] >= 500.0

    def test_trace_refs_include_session_link(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        logs_dir = tmp_path / 'data' / 'logs'
        logs_dir.mkdir(parents=True)
        events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0},
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 6000.0},
        ]
        timeline_path = logs_dir / 'startup_timeline.jsonl'
        timeline_path.write_text(self._make_timeline(events), encoding='utf-8')

        mock_repo = MagicMock()
        mock_session = _mock_session(session_id='sess-linked')
        mock_repo.list_recent.return_value = [mock_session]

        svc = OperationalSelfExaminationService(
            workspace_root=str(tmp_path),
            storage=MagicMock(),
            adaptive_session_repository=mock_repo,
        )
        findings = svc._startup_health_findings()
        assert len(findings) >= 1
        refs = findings[0].metadata['trace_refs']
        assert refs['latest_session_id'] == 'sess-linked'
        assert refs['latest_session_intent'] == 'knowledge.query'


# --- Category 5: Execution dossier metadata correlates with session ----

class TestDossierSessionCorrelation:
    """Verify that execution dossier metadata includes correlated session
    data and route information from task_packet."""

    def test_dossier_metadata_from_run_basic(self):
        from iabv_v15.services.evolution.execution_dossier_service import (
            ExecutionDossierService,
        )
        run_result = MagicMock()
        run_result.report_kind.value = 'standard'
        run_result.reasoning_mode.value = 'local'
        run_result.intent = {'intent_key': 'knowledge.query'}
        run_result.chosen_pack = {'pack_id': 'knowledge.query'}
        run_route = MagicMock()
        run_route.reason = 'test route'
        run_record = MagicMock()
        run_record.result = run_result
        run_record.route = run_route

        meta = ExecutionDossierService._dossier_metadata_from_run(
            run_record,
            adaptive_payload=None,
        )
        assert meta['report_kind'] == 'standard'
        assert meta['reasoning_mode'] == 'local'
        assert meta['intent_key'] == 'knowledge.query'
        assert meta['route_reason'] == 'test route'

    def test_dossier_metadata_correlates_session_id(self):
        from iabv_v15.services.evolution.execution_dossier_service import (
            ExecutionDossierService,
        )
        run_result = MagicMock()
        run_result.report_kind.value = 'standard'
        run_result.reasoning_mode.value = 'local'
        run_result.intent = {}
        run_result.chosen_pack = {}
        run_record = MagicMock()
        run_record.result = run_result
        run_record.route = MagicMock()

        adaptive_payload = {
            'session_id': 'sess-correlated-123',
            'metadata': {
                'task_packet': {
                    'route_reason': 'from task_packet',
                    'intent_key': 'knowledge.query',
                    'chosen_pack_id': 'knowledge.query',
                    'tool_selection_summary': {
                        'gate_ran': False,
                        'reason': 'external_route_not_requested',
                        'selected_tool': '',
                    },
                },
            },
        }
        meta = ExecutionDossierService._dossier_metadata_from_run(
            run_record,
            adaptive_payload=adaptive_payload,
        )
        assert meta['correlated_session_id'] == 'sess-correlated-123'
        assert meta['route_reason'] == 'from task_packet'
        assert meta['gate_ran'] is False
        assert meta['tool_selection_reason'] == 'external_route_not_requested'
        assert meta['selected_tool'] == ''

    def test_dossier_metadata_prefers_task_packet_route_reason(self):
        from iabv_v15.services.evolution.execution_dossier_service import (
            ExecutionDossierService,
        )
        run_result = MagicMock()
        run_result.report_kind.value = 'standard'
        run_result.reasoning_mode.value = 'local'
        run_result.intent = {}
        run_result.chosen_pack = {}
        run_route = MagicMock()
        run_route.reason = 'fallback route reason'
        run_record = MagicMock()
        run_record.result = run_result
        run_record.route = run_route

        adaptive_payload = {
            'metadata': {
                'task_packet': {
                    'route_reason': 'Rol resuelto desde intent knowledge.query',
                },
            },
        }
        meta = ExecutionDossierService._dossier_metadata_from_run(
            run_record,
            adaptive_payload=adaptive_payload,
        )
        assert meta['route_reason'] == 'Rol resuelto desde intent knowledge.query'


# --- Category 6: RunHistory viewmodel shows route_reason ---------------

class TestRunHistoryRouteFields:
    """Verify that RunHistoryViewModel exposes route_reason and related
    trace fields in the run payload."""

    def test_run_payload_includes_route_reason(self):
        from iabv_v15.ui.viewmodels.run_history_viewmodel import RunHistoryViewModel

        mock_run = MagicMock()
        mock_run.run_id = 'run-001'
        mock_run.duration_ms = 100
        mock_run.model_dump.return_value = {
            'run_id': 'run-001',
            'status': 'success',
            'duration_ms': 100,
            'result': {
                'detected_role': 'knowledge',
                'planner_used': False,
                'executor_model': 'ollama',
                'reasoning_mode': 'local',
                'inferred_task': 'test',
                'summary': 'ok',
            },
            'route': {'task_role': 'knowledge', 'model_name': 'ollama'},
        }

        mock_repo = MagicMock()
        mock_repo.list_recent.return_value = [mock_run]

        mock_session = _mock_session(metadata={
            'task_packet': {
                'route_reason': 'Rol resuelto desde intent knowledge.query',
                'chosen_pack_id': 'knowledge.query',
                'evidence_basis': {'state': 'observed'},
                'worker_gate_summary': {'ran': False, 'usable': False, 'available_count': 0},
                'governance_flags': {'approval_required': False},
                'unresolved': [],
                'tool_selection_summary': {
                    'selected_tool': '',
                    'reason': 'external_route_not_requested',
                    'gate_ran': False,
                    'fallback_used': False,
                    'quota_confirmed': False,
                    'requested_external_consultation': False,
                    'routed_locally': True,
                },
            },
        })
        mock_session_repo = MagicMock()
        mock_session_repo.find_by_run.return_value = [mock_session]

        with patch.object(RunHistoryViewModel, '__init__', lambda self, *a, **kw: None):
            vm = RunHistoryViewModel.__new__(RunHistoryViewModel)
            vm.repository = mock_repo
            vm.dossier_repository = None
            vm.session_repository = mock_session_repo
            vm._runs = []
            vm._selected_run = {}
            vm._selected_dossier = {}
            vm.dataChanged = MagicMock()
            vm.refresh()

        assert len(vm._runs) == 1
        run = vm._runs[0]
        assert run['route_reason'] == 'Rol resuelto desde intent knowledge.query'
        assert run['chosen_pack_id'] == 'knowledge.query'
        assert run['tool_selection_reason'] == 'external_route_not_requested'
        assert run['gate_ran'] is False
        assert run['routed_locally'] is True
        assert run['requested_external'] is False


# --- Backward compatibility -------------------------------------------

class TestBackwardCompatibility:
    """Verify backward compatibility of _build_tool_selection_summary."""

    def test_old_gate_ran_true_still_works(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={
                'usable': True,
                'top_worker': {'tool': 'ollama', 'email': ''},
                'account_selection_source': 'auto_ranked',
            },
            gate_ran=True,
            governance={'assistant_kind': 'ollama'},
            session_metadata={},
        )
        assert result['selected_tool'] == 'ollama'
        assert result['reason'] == 'source=auto_ranked'
        assert result['gate_ran'] is True
        assert 'requested_external_consultation' in result
        assert 'routed_locally' in result

    def test_pre_dispatch_blocked_fallback_still_detected(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            _build_tool_selection_summary,
        )
        result = _build_tool_selection_summary(
            worker_gate={
                'usable': True,
                'top_worker': {'tool': 'chatgpt'},
                'account_selection_source': 'auto_ranked',
            },
            gate_ran=True,
            governance={'assistant_kind': 'chatgpt'},
            session_metadata={'pre_dispatch_blocked': {'fallback_attempted': True}},
        )
        assert result['fallback_used'] is True
