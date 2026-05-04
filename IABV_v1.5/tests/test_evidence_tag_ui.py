"""Focused tests for the evidence tag contract in chat messages.

Covers:
- _classify_evidence_tag returns correct tag for each combination
- _append_message stores evidenceTag when valid, omits when empty/invalid
- answer methods pass the correct evidence tag
- no evidenceTag on user messages or untagged assistant messages
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


# ─── _classify_evidence_tag ──────────────────────────────────


class TestClassifyEvidenceTag:
    def test_observed_when_live_observation(self) -> None:
        assert ControlCenterViewModel._classify_evidence_tag(
            has_live_observation=True,
        ) == 'observed'

    def test_observed_takes_priority_over_inferred(self) -> None:
        assert ControlCenterViewModel._classify_evidence_tag(
            has_live_observation=True,
            has_persisted_evidence=True,
        ) == 'observed'

    def test_inferred_when_persisted_evidence(self) -> None:
        assert ControlCenterViewModel._classify_evidence_tag(
            has_persisted_evidence=True,
        ) == 'inferred'

    def test_unresolved_when_no_evidence(self) -> None:
        assert ControlCenterViewModel._classify_evidence_tag() == 'unresolved'

    def test_unresolved_when_both_false(self) -> None:
        assert ControlCenterViewModel._classify_evidence_tag(
            has_live_observation=False,
            has_persisted_evidence=False,
        ) == 'unresolved'


# ─── _append_message evidence tag ────────────────────────────


class _MinimalVM:
    """Minimal stand-in to test _append_message without full bootstrap."""

    def __init__(self) -> None:
        self._chat_messages: list[dict[str, Any]] = []
        self._ui_state_lock = __import__('threading').Lock()
        self._contextual_suggestions: list[dict[str, Any]] = []
        self._live_status = 'idle'
        self._working = False
        self._attached_files: list[dict[str, Any]] = []

    def _refresh_contextual_suggestions(self) -> None:
        pass

    def _validate_ui_reflects_reality(self) -> dict[str, Any]:
        return {'valid': True, 'findings': []}


def _build_minimal_vm() -> _MinimalVM:
    return _MinimalVM()


class TestAppendMessageEvidenceTag:
    def test_observed_tag_stored(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'hello', 'meta', evidence_tag='observed',  # type: ignore[arg-type]
        )
        assert vm._chat_messages[-1]['evidenceTag'] == 'observed'

    def test_inferred_tag_stored(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'hello', 'meta', evidence_tag='inferred',  # type: ignore[arg-type]
        )
        assert vm._chat_messages[-1]['evidenceTag'] == 'inferred'

    def test_unresolved_tag_stored(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'hello', 'meta', evidence_tag='unresolved',  # type: ignore[arg-type]
        )
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'

    def test_empty_tag_not_stored(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'hello', 'meta', evidence_tag='',  # type: ignore[arg-type]
        )
        assert 'evidenceTag' not in vm._chat_messages[-1]

    def test_invalid_tag_not_stored(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'hello', 'meta', evidence_tag='guessed',  # type: ignore[arg-type]
        )
        assert 'evidenceTag' not in vm._chat_messages[-1]

    def test_no_tag_param_means_no_key(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'hello', 'meta',  # type: ignore[arg-type]
        )
        assert 'evidenceTag' not in vm._chat_messages[-1]

    def test_user_messages_unaffected(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'user', 'Tu', 'hello', '',  # type: ignore[arg-type]
        )
        assert 'evidenceTag' not in vm._chat_messages[-1]
        assert vm._chat_messages[-1]['role'] == 'user'

    def test_existing_fields_preserved(self) -> None:
        vm = _build_minimal_vm()
        ControlCenterViewModel._append_message(
            vm, 'assistant', 'IABV', 'text', 'meta',  # type: ignore[arg-type]
            reasoning='thought process',
            evidence_tag='observed',
        )
        msg = vm._chat_messages[-1]
        assert msg['reasoning'] == 'thought process'
        assert msg['evidenceTag'] == 'observed'
        assert msg['role'] == 'assistant'
        assert msg['text'] == 'text'
        assert msg['meta'] == 'meta'


# ─── Evidence tag values are consistent ──────────────────────


class TestEvidenceTagValues:
    """Verify that the valid tag values are exactly three."""

    def test_only_three_valid_tags(self) -> None:
        valid = {'observed', 'inferred', 'unresolved'}
        for tag in valid:
            vm = _build_minimal_vm()
            ControlCenterViewModel._append_message(
                vm, 'assistant', 'IABV', 'x', '', evidence_tag=tag,  # type: ignore[arg-type]
            )
            assert vm._chat_messages[-1]['evidenceTag'] == tag

    def test_classify_returns_only_valid_tags(self) -> None:
        valid = {'observed', 'inferred', 'unresolved'}
        combos = [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ]
        for live, persisted in combos:
            tag = ControlCenterViewModel._classify_evidence_tag(
                has_live_observation=live,
                has_persisted_evidence=persisted,
            )
            assert tag in valid, f'Unexpected tag {tag!r} for live={live}, persisted={persisted}'


# ─── Dynamic evidence tag for evolution / learning ───────────


class _AnswerMethodVM(_MinimalVM):
    """Extends _MinimalVM with stubs required by _answer_evolution/learning/self_examination."""

    def __init__(self) -> None:
        super().__init__()
        self._last_user_goal: str = ''
        self._latest_response_text: str = ''
        self._latest_response_meta: str = ''
        self._busy_label: str = ''
        self._last_adaptive_payload: dict[str, Any] = {}
        self._validation_status: dict[str, Any] = {}
        self._discovery_status: dict[str, Any] = {}
        self._learning_snapshot: dict[str, Any] = {}
        self._examination_snapshot: dict[str, Any] = {}

    # stubs called by the answer methods
    def _clear_autonomy_activity_override(self) -> None:
        pass

    def _update_adaptive_state(self, payload: Any) -> None:
        pass

    def _evolution_status_conversation_payload(self, *, message: str) -> dict[str, Any]:
        return {}

    def _learning_conversation_payload(self, *, message: str) -> dict[str, Any]:
        return {}

    def _current_validation_status(self) -> dict[str, Any]:
        return self._validation_status

    def _current_tool_discovery_status(self) -> dict[str, Any]:
        return self._discovery_status

    def _learning_evidence_snapshot(self) -> dict[str, Any]:
        return self._learning_snapshot

    def _current_self_examination_snapshot(self) -> dict[str, Any]:
        return self._examination_snapshot

    def _self_examination_conversation_payload(self, *, message: str) -> dict[str, Any]:
        return {}

    _classify_evidence_tag = staticmethod(ControlCenterViewModel._classify_evidence_tag)
    _finding_metrics_suffix = staticmethod(ControlCenterViewModel._finding_metrics_suffix)
    _startup_timeline_summary = staticmethod(ControlCenterViewModel._startup_timeline_summary)
    _append_message = ControlCenterViewModel._append_message
    _general_chat_reply = ControlCenterViewModel._general_chat_reply

    class dataChanged:  # noqa: N801
        @staticmethod
        def emit() -> None:
            pass


def _build_answer_vm() -> _AnswerMethodVM:
    return _AnswerMethodVM()


class TestEvolutionBranchTag:
    """Tag comes from the exact branch that produced the reply, not global snapshot."""

    def test_evolution_reply_unresolved_branch(self) -> None:
        vm = _build_answer_vm()
        vm._evolution_status_reply = lambda msg: (  # type: ignore[attr-defined]
            'Todavia no tengo evidencia suficiente.', 'Evidencia evolutiva insuficiente.', 'unresolved',
        )
        ControlCenterViewModel._answer_evolution_status_question(vm, 'que esta evolucionando?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'

    def test_evolution_reply_inferred_branch(self) -> None:
        vm = _build_answer_vm()
        vm._evolution_status_reply = lambda msg: (  # type: ignore[attr-defined]
            'Va ganando tool_x para scope_a.', 'Estado evolutivo real.', 'inferred',
        )
        ControlCenterViewModel._answer_evolution_status_question(vm, 'que esta evolucionando?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'inferred'

    def test_focus_validation_no_active_despite_old_winners_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._validation_status = {'winning_by_problem': {'scope_a': 'tool_x'}}
        vm._discovery_status = {}
        vm._evolution_status_focus = lambda msg: 'validation'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._evolution_status_reply(vm, 'que estas validando?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_focus_winners_with_data_is_inferred(self) -> None:
        vm = _build_answer_vm()
        vm._validation_status = {'winning_by_problem': {'scope_a': 'tool_x'}}
        vm._discovery_status = {}
        vm._evolution_status_focus = lambda msg: 'winners'  # type: ignore[attr-defined]
        vm._human_join = lambda items, limit=3: ', '.join(items[:limit])  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._evolution_status_reply(vm, 'que va ganando?')  # type: ignore[arg-type]
        assert tag == 'inferred'

    def test_focus_discarded_no_data_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._validation_status = {'winning_by_problem': {'scope_a': 'tool_x'}}
        vm._discovery_status = {}
        vm._evolution_status_focus = lambda msg: 'discarded'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._evolution_status_reply(vm, 'que descartaste?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_focus_discovery_no_signals_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._validation_status = {'winning_by_problem': {'scope_a': 'tool_x'}}
        vm._discovery_status = {}
        vm._evolution_status_focus = lambda msg: 'discovery'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._evolution_status_reply(vm, 'que descubriste?')  # type: ignore[arg-type]
        assert tag == 'unresolved'


class TestLearningBranchTag:
    """Tag comes from the exact branch that produced the reply, not global snapshot."""

    def test_learning_reply_unresolved_branch(self) -> None:
        vm = _build_answer_vm()
        vm._learning_reply = lambda msg: (  # type: ignore[attr-defined]
            'Todavia no tengo evidencia suficiente.', 'Evidencia insuficiente.', 'unresolved',
        )
        ControlCenterViewModel._answer_learning_question(vm, 'que aprendiste?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'

    def test_learning_reply_inferred_branch(self) -> None:
        vm = _build_answer_vm()
        vm._learning_reply = lambda msg: (  # type: ignore[attr-defined]
            'La ultima corrida fue test.', 'Historial sin ganador claro.', 'inferred',
        )
        ControlCenterViewModel._answer_learning_question(vm, 'que aprendiste?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'inferred'

    def test_focus_current_validation_no_experiment_despite_patterns_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._learning_snapshot = {
            'experiment_runs': [{'candidate_label': 'test'}],
            'recommendations': [],
            'latest_recommendation': None,
            'adaptive_learning': {},
            'learned_patterns': [{'recommended_assistant_kind': 'ollama'}],
            'validation': {},
            'validation_summary': '',
            'current_experiment': {},
        }
        vm._learning_focus = lambda msg: 'current_validation'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._learning_reply(vm, 'que estas validando?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_focus_route_change_no_recommendation_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._learning_snapshot = {
            'experiment_runs': [{'candidate_label': 'test'}],
            'recommendations': [],
            'latest_recommendation': None,
            'adaptive_learning': {},
            'learned_patterns': [],
            'validation': {},
            'validation_summary': '',
            'current_experiment': {},
        }
        vm._learning_focus = lambda msg: 'route_change'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._learning_reply(vm, 'cambiaste de ruta?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_focus_tools_with_recommendations_is_inferred(self) -> None:
        rec = MagicMock()
        rec.metadata = {'ranked_configurations': [{'assistant_kind': 'ollama'}, {'assistant_kind': 'codex'}]}
        vm = _build_answer_vm()
        vm._learning_snapshot = {
            'experiment_runs': [],
            'recommendations': [rec],
            'latest_recommendation': rec,
            'adaptive_learning': {},
            'learned_patterns': [],
            'validation': {},
            'validation_summary': '',
            'current_experiment': {},
        }
        vm._learning_focus = lambda msg: 'tools'  # type: ignore[attr-defined]
        vm._human_join = lambda items, limit=3: ', '.join(items[:limit])  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._learning_reply(vm, 'que herramienta va mejor?')  # type: ignore[arg-type]
        assert tag == 'inferred'


class TestSelfExaminationBranchTag:
    """Tag comes from the exact branch that produced the reply, not global snapshot."""

    def test_self_examination_reply_unresolved_branch(self) -> None:
        vm = _build_answer_vm()
        vm._self_examination_reply = lambda msg: (  # type: ignore[attr-defined]
            'Todavia no tengo evidencia suficiente.', 'Evidencia insuficiente.', 'unresolved',
        )
        ControlCenterViewModel._answer_self_examination_question(vm, 'que esta fallando?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'

    def test_self_examination_reply_inferred_branch(self) -> None:
        vm = _build_answer_vm()
        vm._self_examination_reply = lambda msg: (  # type: ignore[attr-defined]
            'Lo mas delicado ahora es X.', 'Revision operativa con evidencia.', 'inferred',
        )
        ControlCenterViewModel._answer_self_examination_question(vm, 'que esta fallando?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'inferred'

    def test_focus_failures_no_recurring_despite_findings_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._examination_snapshot = {
            'top_findings': [{'title': 'some finding', 'summary': 'detail'}],
            'recurring_issues': [],
            'recommended_adjustments': [],
            'validated_improvements': [],
            'unresolved_risks': [],
        }
        vm._self_examination_focus = lambda msg: 'failures'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._self_examination_reply(vm, 'que falla?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_focus_adjustments_no_adjustments_despite_findings_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._examination_snapshot = {
            'top_findings': [{'title': 'some finding'}],
            'recurring_issues': [{'title': 'recurring'}],
            'recommended_adjustments': [],
            'validated_improvements': [],
            'unresolved_risks': [],
        }
        vm._self_examination_focus = lambda msg: 'adjustments'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._self_examination_reply(vm, 'que ajustes?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_focus_repetition_with_findings_is_inferred(self) -> None:
        vm = _build_answer_vm()
        vm._examination_snapshot = {
            'top_findings': [{'title': 'patron repetido', 'summary': 'se repite'}],
            'recurring_issues': [],
            'recommended_adjustments': [],
            'validated_improvements': [],
            'unresolved_risks': [],
        }
        vm._self_examination_focus = lambda msg: 'repetition'  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._self_examination_reply(vm, 'que repites?')  # type: ignore[arg-type]
        assert tag == 'inferred'


# ─── General chat evidence tag propagation ───────────────────


class _GeneralChatVM(_AnswerMethodVM):
    """Extends _AnswerMethodVM with stubs for _general_chat_reply / _answer_general_chat."""

    def __init__(self) -> None:
        super().__init__()
        self._working: bool = False

    def _normalized_command_text(self, message: str) -> str:
        return message.strip().lower()

    def _is_self_awareness_question(self, message: str) -> bool:
        return False

    def _is_world_model_question(self, message: str) -> bool:
        return False

    def _is_self_examination_question(self, message: str) -> bool:
        return False

    def _is_learning_question(self, message: str) -> bool:
        return False

    def _is_general_chat_message(self, message: str) -> bool:
        return True

    def _seems_task_like_message(self, message: str) -> bool:
        return False

    def _general_conversation_payload(self, *, message: str) -> dict[str, Any]:
        return {}

    def _set_live_status(self, status: str) -> None:
        pass


def _build_general_chat_vm() -> _GeneralChatVM:
    return _GeneralChatVM()


class TestGeneralChatEvidenceTag:
    """Tag propagates correctly when _general_chat_reply delegates to specialized replies."""

    def test_general_delegates_to_self_awareness_is_observed(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_self_awareness_question = lambda msg: True  # type: ignore[assignment]
        vm._self_awareness_reply = lambda msg: ('Veo 5 ventanas abiertas.', 'Estado del entorno.')  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'que ventanas ves?')  # type: ignore[arg-type]
        assert tag == 'observed'
        assert 'ventanas' in reply.lower()

    def test_general_delegates_to_world_model_is_observed(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_world_model_question = lambda msg: True  # type: ignore[assignment]
        vm._world_model_reply = lambda msg: ('Red estable, CPU al 40%.', 'World model.')  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'como esta el sistema?')  # type: ignore[arg-type]
        assert tag == 'observed'

    def test_general_delegates_to_learning_with_evidence_is_inferred(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_learning_question = lambda msg: True  # type: ignore[assignment]
        vm._learning_reply = lambda msg: ('Ollama rinde mejor que Claude.', 'Aprendizaje.', 'inferred')  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'que aprendiste?')  # type: ignore[arg-type]
        assert tag == 'inferred'

    def test_general_delegates_to_learning_without_evidence_is_unresolved(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_learning_question = lambda msg: True  # type: ignore[assignment]
        vm._learning_reply = lambda msg: ('No tengo evidencia suficiente.', 'Sin evidencia.', 'unresolved')  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'que aprendiste?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_general_delegates_to_self_examination_with_evidence_is_inferred(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_self_examination_question = lambda msg: True  # type: ignore[assignment]
        vm._self_examination_reply = lambda msg: ('Detecto patron repetido X.', 'Patron detectado.', 'inferred')  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'que falla?')  # type: ignore[arg-type]
        assert tag == 'inferred'

    def test_general_delegates_to_self_examination_without_evidence_is_unresolved(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_self_examination_question = lambda msg: True  # type: ignore[assignment]
        vm._self_examination_reply = lambda msg: ('No tengo evidencia.', 'Sin evidencia.', 'unresolved')  # type: ignore[attr-defined]
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'que falla?')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_small_talk_greeting_is_unresolved(self) -> None:
        vm = _build_general_chat_vm()
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'hola')  # type: ignore[arg-type]
        assert tag == 'unresolved'
        assert 'ayudarte' in reply.lower()

    def test_generic_message_is_unresolved(self) -> None:
        vm = _build_general_chat_vm()
        reply, meta, tag = ControlCenterViewModel._general_chat_reply(vm, 'dimelo todo')  # type: ignore[arg-type]
        assert tag == 'unresolved'

    def test_answer_general_chat_preserves_tag_from_delegation(self) -> None:
        vm = _build_general_chat_vm()
        vm._is_self_awareness_question = lambda msg: True  # type: ignore[assignment]
        vm._self_awareness_reply = lambda msg: ('Hay 3 procesos activos.', 'Estado vivo.')  # type: ignore[attr-defined]
        ControlCenterViewModel._answer_general_chat(vm, 'que procesos hay?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'observed'

    def test_answer_general_chat_small_talk_no_false_observed(self) -> None:
        vm = _build_general_chat_vm()
        ControlCenterViewModel._answer_general_chat(vm, 'hola que tal')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'
