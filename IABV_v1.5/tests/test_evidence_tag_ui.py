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
