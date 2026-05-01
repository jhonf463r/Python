"""Tests for worker continuity handoff slice.

Covers:
- quota_exhausted -> handoff_required true
- session_stalled -> handoff_required true
- task_packet preserves continuation metadata
- backward compatibility: no continuity when no blocking condition
- TaskOutcomeRecorder stamps worker_continuity on session
- OSES detects repeated handoff patterns
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    DecisionContext,
    ExternalStateFlag,
    GoalContext,
    InferenceRequest,
    InferenceResult,
    IntentRouteDecision,
    PerceptionSnapshot,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    SelfExaminationFinding,
    TaskContext,
    TaskIntent,
    TaskRole,
    ToolLiveStatus,
    WorkerContinuityReason,
    WorldModelSnapshot,
    build_worker_continuity,
    canonical_external_state_flags,
)


# ─── Helpers ──────────────────────────────────────────────────


def _make_session(
    *,
    status: AdaptiveSessionStatus = AdaptiveSessionStatus.COMPLETED,
    metadata: dict[str, Any] | None = None,
) -> AdaptiveSession:
    return AdaptiveSession(
        user_goal='test goal',
        intent=TaskIntent(
            intent_key='general.assistance',
            detected_role=TaskRole.TRAINING,
        ),
        status=status,
        metadata=metadata or {},
    )


def _make_role_route() -> RoleRoute:
    return RoleRoute(
        task_role=TaskRole.TRAINING,
        role_title='Training',
        provider_name='Ollama',
        model_profile_id='test',
        model_name='test',
        reason='test',
    )


def _make_run_record(
    *,
    health_flags: list[str] | None = None,
    diagnostic_flags: list[str] | None = None,
) -> RunRecord:
    return RunRecord(
        request=InferenceRequest(user_goal='test goal'),
        result=InferenceResult(
            request_id='r1',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='done',
            inferred_task='test',
            confidence=0.9,
            health_flags=health_flags or [],
            diagnostic_flags=diagnostic_flags or [],
        ),
        route=_make_role_route(),
        status=RunStatus.SUCCESS,
    )


def _minimal_decision_context(**overrides: Any) -> DecisionContext:
    defaults: dict[str, Any] = {
        'user_goal': 'test goal',
        'intent': TaskIntent(title='test', intent_key='general.test'),
        'route_decision': IntentRouteDecision(detected_role=TaskRole.TRAINING, reason='test'),
        'governance': {},
        'metadata': {},
    }
    defaults.update(overrides)
    return DecisionContext(**defaults)


def _minimal_perception(**overrides: Any) -> PerceptionSnapshot:
    defaults: dict[str, Any] = {
        'task_context': TaskContext(),
        'decision_context': _minimal_decision_context(),
        'goal_context': GoalContext(),
        'unresolved_fields': [],
        'metadata': {},
    }
    defaults.update(overrides)
    return PerceptionSnapshot(**defaults)


# ─── build_worker_continuity unit tests ───────────────────────


class TestBuildWorkerContinuity:
    def test_quota_exhausted_triggers_handoff(self):
        result = build_worker_continuity(
            session_metadata={
                'task_packet': {'objective': 'deploy feature X'},
                'worker_gate': {'top_worker': {'assistant_kind': 'codex'}},
            },
            external_state_flags=['account_limited'],
            worker_usable=False,
            session_status='executing',
        )
        assert result['handoff_required'] is True
        assert result['worker_status'] == 'blocked'
        assert result['continuation_reason'] == WorkerContinuityReason.QUOTA_EXHAUSTED.value
        assert result['continuation_packet']['objective'] == 'deploy feature X'

    def test_session_stalled_triggers_handoff(self):
        result = build_worker_continuity(
            session_metadata={
                'task_packet': {'objective': 'fix bug'},
                'worker_gate': {'usable': False},
            },
            external_state_flags=[],
            worker_usable=False,
            session_status='executing',
        )
        assert result['handoff_required'] is True
        assert result['continuation_reason'] == WorkerContinuityReason.SESSION_STALLED.value
        assert result['worker_status'] == 'blocked'

    def test_manual_blocked_triggers_handoff(self):
        result = build_worker_continuity(
            session_metadata={'task_packet': {'objective': 'risky op'}},
            external_state_flags=[],
            worker_usable=True,
            session_status='executing',
            governance={'block_risky_action': True},
        )
        assert result['handoff_required'] is True
        assert result['continuation_reason'] == WorkerContinuityReason.MANUAL_BLOCKED.value

    def test_auth_expired_triggers_handoff(self):
        result = build_worker_continuity(
            session_metadata={'task_packet': {'objective': 'query API'}},
            external_state_flags=['session_expired'],
            worker_usable=False,
            session_status='executing',
        )
        assert result['handoff_required'] is True
        assert result['continuation_reason'] == WorkerContinuityReason.AUTH_EXPIRED.value

    def test_no_blocking_condition_no_handoff(self):
        result = build_worker_continuity(
            session_metadata={
                'task_packet': {'objective': 'normal task'},
                'worker_gate': {'usable': True, 'top_worker': {'assistant_kind': 'codex'}},
            },
            external_state_flags=[],
            worker_usable=True,
            session_status='executing',
        )
        assert result['handoff_required'] is False
        assert result['worker_status'] == 'active'
        assert result['continuation_reason'] == ''
        assert result['continuation_packet'] == {}
        assert result['preferred_next_worker'] == 'codex'

    def test_continuation_packet_includes_changed_files_and_tests(self):
        result = build_worker_continuity(
            session_metadata={
                'task_packet': {
                    'objective': 'refactor module',
                    'unresolved': ['missing_type_stub'],
                },
                'changed_files': ['src/foo.py', 'src/bar.py'],
                'tests_run': ['test_foo.py'],
                'completed_step_summary': 'Refactored 3 functions',
            },
            external_state_flags=['account_limited'],
            worker_usable=False,
            session_status='executing',
        )
        assert result['handoff_required'] is True
        pkt = result['continuation_packet']
        assert pkt['objective'] == 'refactor module'
        assert pkt['changed_files'] == ['src/foo.py', 'src/bar.py']
        assert pkt['tests_run'] == ['test_foo.py']
        assert pkt['completed_step_summary'] == 'Refactored 3 functions'
        assert pkt['unresolved'] == ['missing_type_stub']


# ─── TaskOutcomeRecorder stamps worker_continuity ─────────────


class TestRecorderStampsContinuity:
    def test_recorder_stamps_worker_continuity_on_session(self):
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        session = _make_session(
            status=AdaptiveSessionStatus.FAILED,
            metadata={
                'task_packet': {'objective': 'blocked task'},
                'worker_gate': {'usable': False},
            },
        )
        run = _make_run_record(health_flags=['account_limited'])

        result = TaskOutcomeRecorder._stamp_worker_continuity(
            session=session,
            run_record=run,
        )
        wc = result.metadata.get('worker_continuity')
        assert wc is not None
        assert wc['handoff_required'] is True
        assert wc['continuation_reason'] == 'quota_exhausted'

    def test_recorder_no_handoff_when_healthy(self):
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        session = _make_session(
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={
                'task_packet': {'objective': 'normal task'},
                'worker_gate': {'usable': True},
            },
        )
        run = _make_run_record()

        result = TaskOutcomeRecorder._stamp_worker_continuity(
            session=session,
            run_record=run,
        )
        wc = result.metadata.get('worker_continuity')
        assert wc is not None
        assert wc['handoff_required'] is False
        assert wc['worker_status'] == 'active'

    def test_recorder_stamps_without_run_record(self):
        from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

        session = _make_session(
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={
                'task_packet': {'objective': 'stuck task'},
                'worker_gate': {'usable': False},
                'external_state_flags': ['account_limited'],
            },
        )
        result = TaskOutcomeRecorder._stamp_worker_continuity(
            session=session,
            run_record=None,
        )
        wc = result.metadata.get('worker_continuity')
        assert wc is not None
        assert wc['handoff_required'] is True


# ─── _build_task_packet includes worker_continuity ────────────


class TestBuildTaskPacketContinuity:
    def test_task_packet_includes_worker_continuity(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )

        session = _make_session(
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={
                'worker_gate': {
                    'usable': False,
                    'top_worker': {'assistant_kind': 'chatgpt'},
                    'available_count': 0,
                },
            },
        )
        dc = _minimal_decision_context(
            governance={
                'assistant_kind': 'chatgpt',
                'approval_required': False,
                'should_consult': True,
                'block_risky_action': False,
            },
            metadata={
                'external_state_flags': ['account_limited'],
            },
        )
        perception = _minimal_perception(
            unresolved_fields=['missing_api_key'],
            metadata={},
        )
        packet = AdaptiveTaskOrchestrator._build_task_packet(
            session=session,
            decision_context=dc,
            perception=perception,
        )
        assert 'worker_continuity' in packet
        wc = packet['worker_continuity']
        assert wc['handoff_required'] is True
        assert wc['continuation_reason'] == 'quota_exhausted'
        assert wc['worker_status'] == 'blocked'

    def test_task_packet_no_continuity_when_healthy(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )

        session = _make_session(
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={
                'worker_gate': {
                    'usable': True,
                    'top_worker': {'assistant_kind': 'codex'},
                    'available_count': 3,
                },
            },
        )
        dc = _minimal_decision_context(
            governance={
                'assistant_kind': 'codex',
                'approval_required': False,
                'should_consult': False,
                'block_risky_action': False,
            },
            metadata={},
        )
        packet = AdaptiveTaskOrchestrator._build_task_packet(
            session=session,
            decision_context=dc,
            perception=None,
        )
        assert 'worker_continuity' in packet
        wc = packet['worker_continuity']
        assert wc['handoff_required'] is False
        assert wc['worker_status'] == 'active'


# ─── OSES _worker_continuity_findings ─────────────────────────


class TestOSESWorkerContinuityFindings:
    def _make_oses(self):
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        import tempfile
        tmp = tempfile.mkdtemp()
        return OperationalSelfExaminationService(
            workspace_root=tmp,
            storage=ArtifactStorage(tmp),
        )

    def test_detects_repeated_handoff_pattern(self):
        oses = self._make_oses()
        sessions = [
            SimpleNamespace(
                session_id=f'sid-{i}',
                metadata={
                    'worker_continuity': {
                        'handoff_required': True,
                        'continuation_reason': 'quota_exhausted',
                    },
                },
            )
            for i in range(3)
        ]
        findings = oses._worker_continuity_findings(adaptive_sessions=sessions)
        assert len(findings) >= 1
        pattern_finding = [f for f in findings if f.category == 'worker_continuity_pattern']
        assert len(pattern_finding) == 1
        assert pattern_finding[0].metadata['handoff_count'] == 3

    def test_detects_repeated_reason(self):
        oses = self._make_oses()
        sessions = [
            SimpleNamespace(
                session_id=f'sid-{i}',
                metadata={
                    'worker_continuity': {
                        'handoff_required': True,
                        'continuation_reason': 'session_stalled',
                    },
                },
            )
            for i in range(2)
        ]
        findings = oses._worker_continuity_findings(adaptive_sessions=sessions)
        reason_findings = [f for f in findings if f.category == 'worker_continuity_reason']
        assert len(reason_findings) == 1
        assert reason_findings[0].metadata['reason'] == 'session_stalled'
        assert reason_findings[0].metadata['count'] == 2

    def test_no_findings_when_no_handoffs(self):
        oses = self._make_oses()
        sessions = [
            SimpleNamespace(
                session_id='sid-1',
                metadata={
                    'worker_continuity': {
                        'handoff_required': False,
                        'continuation_reason': '',
                    },
                },
            ),
            SimpleNamespace(session_id='sid-2', metadata={}),
        ]
        findings = oses._worker_continuity_findings(adaptive_sessions=sessions)
        assert len(findings) == 0

    def test_no_findings_single_handoff(self):
        oses = self._make_oses()
        sessions = [
            SimpleNamespace(
                session_id='sid-1',
                metadata={
                    'worker_continuity': {
                        'handoff_required': True,
                        'continuation_reason': 'quota_exhausted',
                    },
                },
            ),
        ]
        findings = oses._worker_continuity_findings(adaptive_sessions=sessions)
        pattern_findings = [f for f in findings if f.category == 'worker_continuity_pattern']
        assert len(pattern_findings) == 0


# ─── Backward compatibility ──────────────────────────────────


class TestBackwardCompatibility:
    def test_build_worker_continuity_empty_metadata(self):
        result = build_worker_continuity(
            session_metadata={},
            external_state_flags=[],
            worker_usable=True,
            session_status='completed',
        )
        assert result['handoff_required'] is False
        assert result['worker_status'] == 'active'
        assert result['continuation_reason'] == ''
        assert result['continuation_packet'] == {}

    def test_build_worker_continuity_none_flags(self):
        result = build_worker_continuity(
            session_metadata={},
            external_state_flags=None,
            worker_usable=True,
            session_status='completed',
        )
        assert result['handoff_required'] is False


# ─── Preflight continuity with real signals ──────────────────


class TestPreflightContinuitySignals:
    """Verify that preflight_external_assistant derives external_state_flags
    from world_model.tool_live_status instead of hardcoding []."""

    def test_preflight_account_limited_triggers_handoff(self, monkeypatch):
        from test_task_packet import _build_orchestrator, _workspace
        root = _workspace('wc_preflight_quota')
        orch = _build_orchestrator(root)
        wm = WorldModelSnapshot(
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='chatgpt-1',
                    assistant_kind='chatgpt',
                    available=False,
                    status='no_disponible',
                    external_state_flags=['account_limited'],
                ),
            ],
        )
        monkeypatch.setattr(orch, '_world_model', lambda: wm)
        if hasattr(orch.context_assembler, 'world_model_service'):
            monkeypatch.setattr(orch.context_assembler, 'world_model_service', None)
        result = orch.preflight_external_assistant(
            user_goal='Check quota',
            assistant_kind='chatgpt',
        )
        wc = result['task_packet']['worker_continuity']
        assert wc['handoff_required'] is True
        assert wc['continuation_reason'] == 'quota_exhausted'

    def test_preflight_session_expired_triggers_auth_expired(self, monkeypatch):
        from test_task_packet import _build_orchestrator, _workspace
        root = _workspace('wc_preflight_auth')
        orch = _build_orchestrator(root)
        wm = WorldModelSnapshot(
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='chatgpt-1',
                    assistant_kind='chatgpt',
                    available=False,
                    status='no_disponible',
                    external_state_flags=['session_expired'],
                ),
            ],
        )
        monkeypatch.setattr(orch, '_world_model', lambda: wm)
        if hasattr(orch.context_assembler, 'world_model_service'):
            monkeypatch.setattr(orch.context_assembler, 'world_model_service', None)
        result = orch.preflight_external_assistant(
            user_goal='Check auth',
            assistant_kind='chatgpt',
        )
        wc = result['task_packet']['worker_continuity']
        assert wc['handoff_required'] is True
        assert wc['continuation_reason'] == 'auth_expired'


# ─── preferred_next_worker uses canonical worker shape ───────


class TestPreferredNextWorkerShape:
    def test_preferred_next_worker_tool_email(self):
        result = build_worker_continuity(
            session_metadata={
                'worker_gate': {
                    'usable': True,
                    'top_worker': {'tool': 'chatgpt', 'email': 'user@test.com'},
                },
            },
            external_state_flags=[],
            worker_usable=True,
            session_status='completed',
        )
        assert result['handoff_required'] is False
        assert result['preferred_next_worker'] == 'chatgpt:user@test.com'

    def test_preferred_next_worker_tool_only(self):
        result = build_worker_continuity(
            session_metadata={
                'worker_gate': {
                    'usable': True,
                    'top_worker': {'tool': 'copilot'},
                },
            },
            external_state_flags=[],
            worker_usable=True,
            session_status='completed',
        )
        assert result['preferred_next_worker'] == 'copilot'

    def test_preferred_next_worker_browser_profile(self):
        result = build_worker_continuity(
            session_metadata={
                'worker_gate': {
                    'usable': True,
                    'top_worker': {'browser': 'chrome', 'profile': 'work'},
                },
            },
            external_state_flags=[],
            worker_usable=True,
            session_status='completed',
        )
        assert result['preferred_next_worker'] == 'chrome:work'

    def test_preferred_next_worker_assistant_kind_fallback(self):
        result = build_worker_continuity(
            session_metadata={
                'worker_gate': {
                    'usable': True,
                    'top_worker': {'assistant_kind': 'codex'},
                },
            },
            external_state_flags=[],
            worker_usable=True,
            session_status='completed',
        )
        assert result['preferred_next_worker'] == 'codex'

    def test_backward_compat_empty_top_worker(self):
        result = build_worker_continuity(
            session_metadata={
                'worker_gate': {'usable': True, 'top_worker': {}},
            },
            external_state_flags=[],
            worker_usable=True,
            session_status='completed',
        )
        assert result['preferred_next_worker'] == ''
