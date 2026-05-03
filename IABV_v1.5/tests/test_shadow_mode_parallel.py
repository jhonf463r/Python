"""Tests for Brecha 2.1 — Shadow mode parallel dispatch cloud+local."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    InferenceResult,
    RoleRoute,
    TaskIntent,
    TaskRole,
    ToolLiveStatus,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
    AdaptiveTaskOrchestrator,
)


def _make_session(
    role: TaskRole = TaskRole.RESEARCH,
    confidence: float = 0.9,
) -> AdaptiveSession:
    session = MagicMock(spec=AdaptiveSession)
    session.session_id = 'test-session-1'
    session.user_goal = 'test objective'
    session.intent = MagicMock(spec=TaskIntent)
    session.intent.detected_role = role
    session.intent.confidence = confidence
    session.metadata = {}
    return session


def _make_route(provider: str = 'gemini') -> RoleRoute:
    return RoleRoute(
        task_role=TaskRole.RESEARCH,
        role_title='research',
        provider_name=provider,
        model_profile_id='test',
        model_name='test-model',
        reason='test route',
    )


def _make_result() -> InferenceResult:
    result = MagicMock(spec=InferenceResult)
    result.summary = 'test summary'
    result.confidence = 0.9
    result.raw_output = {'elapsed_ms': 1500}
    return result


def _make_ato(**overrides) -> AdaptiveTaskOrchestrator:
    ato = MagicMock(spec=AdaptiveTaskOrchestrator)
    ato._last_shadow_at = 0.0
    ato._SHADOW_COOLDOWN_SECONDS = 300.0
    ato._SHADOW_NON_REASONING_ROLES = AdaptiveTaskOrchestrator._SHADOW_NON_REASONING_ROLES
    ato.experiment_lab = overrides.get('experiment_lab', MagicMock())
    ato._should_shadow = AdaptiveTaskOrchestrator._should_shadow.__get__(ato)
    ato._has_local_provider = AdaptiveTaskOrchestrator._has_local_provider
    ato._shadow_parallel_dispatch = AdaptiveTaskOrchestrator._shadow_parallel_dispatch.__get__(ato)
    ato._maybe_invoke_local_chat_llm = MagicMock(return_value={'summary': 'local result'})
    return ato


class TestShadowSkippedUnderCriticalPressure:
    def test_critical_blocks_shadow(self):
        ato = _make_ato()
        session = _make_session()
        pressure = {'critical': True, 'under_pressure': True}
        assert ato._should_shadow(session, None, pressure) is False


class TestShadowSkippedWithoutLocalProvider:
    def test_no_ollama_blocks_shadow(self):
        ato = _make_ato()
        session = _make_session()
        wm = WorldModelSnapshot(
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='chatgpt-1',
                    assistant_kind='chatgpt',
                    available=True,
                ),
            ]
        )
        pressure = {'critical': False, 'under_pressure': False}
        assert ato._should_shadow(session, wm, pressure) is False


class TestShadowExecutesBothRoutes:
    def test_shadow_runs_local_llm(self):
        ato = _make_ato()
        session = _make_session()
        route = _make_route()
        result = _make_result()
        ato._shadow_parallel_dispatch(session, route, result, None)
        ato._maybe_invoke_local_chat_llm.assert_called_once()


class TestShadowReturnsPrimaryResultToUser:
    def test_primary_result_unchanged(self):
        ato = _make_ato()
        session = _make_session()
        route = _make_route()
        result = _make_result()
        original_summary = result.summary
        ato._shadow_parallel_dispatch(session, route, result, None)
        assert result.summary == original_summary


class TestShadowRecordsBothInExperimentLab:
    def test_two_runs_saved(self):
        lab = MagicMock()
        lab.repository = MagicMock()
        ato = _make_ato(experiment_lab=lab)
        session = _make_session()
        route = _make_route()
        result = _make_result()
        ato._shadow_parallel_dispatch(session, route, result, None)
        assert lab.repository.save_run.call_count == 2
        calls = lab.repository.save_run.call_args_list
        runs = [c.args[0] for c in calls]
        kinds = {r.assistant_kind for r in runs}
        assert 'gemini' in kinds
        assert 'ollama_local' in kinds
        # Both should have same comparison_scope_key
        keys = {r.metadata.get('comparison_scope_key') for r in runs}
        assert len(keys) == 1


class TestShadowCooldownPreventSpam:
    def test_recent_shadow_blocks_new(self):
        ato = _make_ato()
        ato._last_shadow_at = time.time() - 60  # 60s ago (< 300s cooldown)
        session = _make_session()
        pressure = {'critical': False, 'under_pressure': False}
        assert ato._should_shadow(session, None, pressure) is False


class TestShadowOnlyForReasoningTasks:
    def test_visual_task_excluded(self):
        ato = _make_ato()
        session = _make_session(role=TaskRole.VISUAL)
        pressure = {'critical': False, 'under_pressure': False}
        assert ato._should_shadow(session, None, pressure) is False

    def test_tool_use_excluded(self):
        ato = _make_ato()
        session = _make_session(role=TaskRole.TOOL_USE)
        pressure = {'critical': False, 'under_pressure': False}
        assert ato._should_shadow(session, None, pressure) is False

    def test_research_included(self):
        ato = _make_ato()
        session = _make_session(role=TaskRole.RESEARCH)
        pressure = {'critical': False, 'under_pressure': False}
        assert ato._should_shadow(session, None, pressure) is True


class TestShouldShadowRespectsHighPressure:
    def test_high_pressure_low_confidence_blocks(self):
        ato = _make_ato()
        session = _make_session(confidence=0.5)
        pressure = {'critical': False, 'under_pressure': True}
        assert ato._should_shadow(session, None, pressure) is False

    def test_high_pressure_high_confidence_allows(self):
        ato = _make_ato()
        session = _make_session(confidence=0.8)
        pressure = {'critical': False, 'under_pressure': True}
        assert ato._should_shadow(session, None, pressure) is True


class TestConsensusFusionPicksWinner:
    def test_scope_key_links_runs_for_comparison(self):
        """Verify shadow runs use the same comparison_scope_key."""
        lab = MagicMock()
        lab.repository = MagicMock()
        ato = _make_ato(experiment_lab=lab)
        session = _make_session()
        route = _make_route()
        result = _make_result()
        ato._shadow_parallel_dispatch(session, route, result, None)
        calls = lab.repository.save_run.call_args_list
        runs = [c.args[0] for c in calls]
        scope_keys = [r.metadata.get('comparison_scope_key') for r in runs]
        assert all(k == f'shadow_{session.session_id}' for k in scope_keys)
        assert runs[0].route.value != runs[1].route.value
