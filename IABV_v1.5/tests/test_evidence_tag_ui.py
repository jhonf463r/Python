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
    """Extends _MinimalVM with stubs required by _answer_evolution/learning."""

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

    _classify_evidence_tag = staticmethod(ControlCenterViewModel._classify_evidence_tag)
    _append_message = ControlCenterViewModel._append_message

    class dataChanged:  # noqa: N801
        @staticmethod
        def emit() -> None:
            pass


def _build_answer_vm() -> _AnswerMethodVM:
    return _AnswerMethodVM()


class TestEvolutionDynamicTag:
    def test_evolution_without_evidence_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._validation_status = {}
        vm._discovery_status = {}
        vm._evolution_status_reply = lambda msg: (  # type: ignore[attr-defined]
            'Todavia no tengo evidencia suficiente.', 'Evidencia evolutiva insuficiente.',
        )
        ControlCenterViewModel._answer_evolution_status_question(vm, 'que esta evolucionando?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'

    def test_evolution_with_evidence_is_inferred(self) -> None:
        vm = _build_answer_vm()
        vm._validation_status = {'winning_by_problem': {'scope_a': 'tool_x'}}
        vm._discovery_status = {}
        vm._evolution_status_reply = lambda msg: (  # type: ignore[attr-defined]
            'Va ganando tool_x para scope_a.', 'Estado evolutivo real.',
        )
        ControlCenterViewModel._answer_evolution_status_question(vm, 'que esta evolucionando?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'inferred'


class TestLearningDynamicTag:
    def test_learning_without_evidence_is_unresolved(self) -> None:
        vm = _build_answer_vm()
        vm._learning_snapshot = {}
        vm._learning_reply = lambda msg: (  # type: ignore[attr-defined]
            'Todavia no tengo evidencia suficiente.', 'Evidencia insuficiente.',
        )
        ControlCenterViewModel._answer_learning_question(vm, 'que aprendiste?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'unresolved'

    def test_learning_with_evidence_is_inferred(self) -> None:
        vm = _build_answer_vm()
        vm._learning_snapshot = {
            'experiment_runs': [{'candidate_label': 'test'}],
            'recommendations': [],
            'latest_recommendation': None,
            'adaptive_learning': {},
            'learned_patterns': [],
            'validation': {},
        }
        vm._learning_reply = lambda msg: (  # type: ignore[attr-defined]
            'La ultima corrida fue test.', 'Historial sin ganador claro.',
        )
        ControlCenterViewModel._answer_learning_question(vm, 'que aprendiste?')  # type: ignore[arg-type]
        assert vm._chat_messages[-1]['evidenceTag'] == 'inferred'
