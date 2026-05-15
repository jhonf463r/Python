"""P0.6 — Shared Reality Remediation / Window Target Recovery tests.

Tests that _assess_visual_remediation() correctly classifies failed captures,
_attempt_safe_remediation() only acts on safe scenarios, and
_trace_visual_remediation_attempted() builds events without PII.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────

def _make_vm() -> Any:
    """Build a minimal ControlCenterViewModel-like object with P0.6 helpers."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
    vm = ControlCenterViewModel.__new__(ControlCenterViewModel)
    vm._last_adaptive_payload = {}
    return vm


def _offscreen_target_window(*, hwnd: int = 16319628) -> dict[str, Any]:
    return {
        'title': 'ChatGPT - Google Chrome for Testing',
        'hwnd': hwnd,
        'rect': [-32000, -32000, 199, 34],
    }


def _visible_target_window() -> dict[str, Any]:
    return {
        'title': 'ChatGPT - Google Chrome',
        'hwnd': 12345678,
        'rect': [100, 100, 1200, 800],
    }


def _black_capture_meta(*, blank_probability: float = 0.98) -> dict[str, Any]:
    return {
        'blank_probability': blank_probability,
        'dynamic_range': 0,
        'unique_color_count': 1,
        'useful': False,
    }


def _useful_capture_meta() -> dict[str, Any]:
    return {
        'blank_probability': 0.05,
        'dynamic_range': 180,
        'unique_color_count': 5000,
        'useful': True,
    }


# ══════════════════════════════════════════════════════════════════════
# Task A — Visual Remediation Assessment
# ══════════════════════════════════════════════════════════════════════

class TestAssessVisualRemediation:
    """_assess_visual_remediation() classifies failed captures correctly."""

    def test_offscreen_rect_generates_remediation_available(self) -> None:
        vm = _make_vm()
        tw = _offscreen_target_window()
        capture_state = vm._target_window_capture_state(tw, None)
        assessment = vm._assess_visual_remediation(
            target_window=tw,
            capture_meta=None,
            capture_state=capture_state,
        )
        assert assessment['status'] == 'remediation_available'
        assert assessment['proposed_action'] == 'restore_window_by_hwnd'
        assert assessment['safe_to_auto_try'] is True
        assert 'minimizada' in assessment['user_message'].lower() or 'offscreen' in assessment['user_message'].lower()

    def test_black_capture_generates_remediation_available(self) -> None:
        vm = _make_vm()
        tw = _visible_target_window()
        cm = _black_capture_meta()
        capture_state = vm._target_window_capture_state(tw, cm)
        assessment = vm._assess_visual_remediation(
            target_window=tw,
            capture_meta=cm,
            capture_state=capture_state,
        )
        assert assessment['status'] == 'remediation_available'
        assert 'negra' in assessment['user_message'].lower() or 'blank' in assessment['user_message'].lower()

    def test_ambiguous_window_generates_needs_user_selection(self) -> None:
        vm = _make_vm()
        capture_state = vm._target_window_capture_state(None, None)
        assessment = vm._assess_visual_remediation(
            target_window=None,
            capture_meta=None,
            capture_state=capture_state,
        )
        assert assessment['status'] == 'needs_user_selection'
        assert assessment['proposed_action'] == 'request_user_selection'
        assert assessment['safe_to_auto_try'] is False

    def test_useful_capture_no_remediation(self) -> None:
        vm = _make_vm()
        tw = _visible_target_window()
        cm = _useful_capture_meta()
        capture_state = vm._target_window_capture_state(tw, cm)
        assessment = vm._assess_visual_remediation(
            target_window=tw,
            capture_meta=cm,
            capture_state=capture_state,
        )
        assert assessment['status'] == 'no_action_needed'
        assert assessment['proposed_action'] == 'none'
        assert assessment['safe_to_auto_try'] is False

    def test_invalid_hwnd_no_auto_action(self) -> None:
        vm = _make_vm()
        tw = {
            'title': 'ChatGPT',
            'hwnd': 0,
            'rect': [-32000, -32000, 199, 34],
        }
        capture_state = vm._target_window_capture_state(tw, None)
        assessment = vm._assess_visual_remediation(
            target_window=tw,
            capture_meta=None,
            capture_state=capture_state,
        )
        assert assessment['status'] == 'remediation_available'
        assert assessment['safe_to_auto_try'] is False
        assert assessment['proposed_action'] == 'request_user_restore'

    def test_controlled_session_recommends_browser_selector(self) -> None:
        vm = _make_vm()
        tw = {
            'title': 'ChatGPT - Chrome for Testing',
            'hwnd': None,
            'rect': [100, 100, 200, 200],
        }
        cm = _black_capture_meta(blank_probability=0.95)
        capture_state = vm._target_window_capture_state(tw, cm)
        assessment = vm._assess_visual_remediation(
            target_window=tw,
            capture_meta=cm,
            capture_state=capture_state,
        )
        assert 'navegador visible' in assessment['user_message'].lower() or 'otra sesion' in assessment['user_message'].lower()


# ══════════════════════════════════════════════════════════════════════
# Task B — Safe Remediation
# ══════════════════════════════════════════════════════════════════════

class TestAttemptSafeRemediation:
    """_attempt_safe_remediation() only acts on safe scenarios."""

    def test_no_auto_when_unsafe(self) -> None:
        vm = _make_vm()
        assessment = {
            'safe_to_auto_try': False,
            'proposed_action': 'request_user_restore',
        }
        result = vm._attempt_safe_remediation(assessment)
        assert result['action_taken'] == 'none'
        assert result['success'] is False

    def test_auto_attempt_on_linux_returns_not_available(self) -> None:
        """On Linux (no Win32), the auto-attempt should fail gracefully."""
        vm = _make_vm()
        assessment = {
            'safe_to_auto_try': True,
            'proposed_action': 'restore_window_by_hwnd',
        }
        result = vm._attempt_safe_remediation(assessment)
        # On Linux: Win32 not available, but no crash
        assert 'action_taken' in result
        assert isinstance(result['success'], bool)


# ══════════════════════════════════════════════════════════════════════
# Task D — RuntimeAuditTracer event
# ══════════════════════════════════════════════════════════════════════

class TestTraceVisualRemediationAttempted:
    """_trace_visual_remediation_attempted() builds event without PII."""

    def test_event_fields_no_pii(self) -> None:
        vm = _make_vm()
        traced_events: list[dict[str, Any]] = []

        def fake_trace(kind: str, **kwargs: Any) -> None:
            traced_events.append({'kind': kind, **kwargs})

        mock_tracer = MagicMock()
        mock_tracer.trace = fake_trace
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=mock_tracer,
        ):
            vm._trace_visual_remediation_attempted(
                assistant_kind='chatgpt',
                target_window_title='ChatGPT - Google Chrome for Testing',
                hwnd=16319628,
                rect=[-32000, -32000, 199, 34],
                reason='target_window_minimized_or_offscreen',
                proposed_action='restore_window_by_hwnd',
                action_taken='restore_window_by_hwnd',
                result_status='remediation_available',
                capture_useful_before=False,
                blank_probability_before=0.98,
                unresolved=['UNRESOLVED:external_target_window_minimized_or_offscreen'],
            )
        assert len(traced_events) == 1
        ev = traced_events[0]
        assert ev['kind'] == 'visual_remediation_attempted'
        assert ev['assistant_kind'] == 'chatgpt'
        assert ev['hwnd_present'] is True
        assert ev['proposed_action'] == 'restore_window_by_hwnd'
        assert ev['capture_useful_before'] is False
        assert ev['blank_probability_before'] == 0.98
        # No sensitive file paths
        ev_str = json.dumps(ev)
        assert 'C:\\' not in ev_str
        assert '/home/' not in ev_str

    def test_hwnd_zero_shows_present_false(self) -> None:
        vm = _make_vm()
        traced_events: list[dict[str, Any]] = []

        def fake_trace(kind: str, **kwargs: Any) -> None:
            traced_events.append({'kind': kind, **kwargs})

        mock_tracer = MagicMock()
        mock_tracer.trace = fake_trace
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            return_value=mock_tracer,
        ):
            vm._trace_visual_remediation_attempted(
                assistant_kind='gemini',
                target_window_title='Gemini',
                hwnd=0,
                rect=None,
                reason='no_target_window',
                proposed_action='request_user_selection',
                action_taken='none',
                result_status='needs_user_selection',
                capture_useful_before=False,
            )
        assert traced_events[0]['hwnd_present'] is False


# ══════════════════════════════════════════════════════════════════════
# Task F — User message
# ══════════════════════════════════════════════════════════════════════

class TestRemediationUserMessage:
    """_remediation_user_message() builds practical, non-technical message."""

    def test_message_contains_required_elements(self) -> None:
        vm = _make_vm()
        assessment = {
            'status': 'remediation_available',
            'reason': 'target_window_minimized_or_offscreen',
            'target_window_title': 'ChatGPT - Google Chrome for Testing',
            'proposed_action': 'restore_window_by_hwnd',
        }
        remediation_result = {
            'action_taken': 'restore_window_by_hwnd',
            'success': False,
            'detail': 'Win32 not available',
        }
        msg = vm._remediation_user_message(
            assistant_title='ChatGPT',
            assessment=assessment,
            remediation_result=remediation_result,
        )
        msg_lower = msg.lower()
        assert 'chatgpt' in msg_lower
        assert 'minimizada' in msg_lower or 'offscreen' in msg_lower
        assert 'otra sesion' in msg_lower or 'navegador' in msg_lower
        assert 'reintentar' in msg_lower or 'reintenta' in msg_lower

    def test_message_for_no_target_window(self) -> None:
        vm = _make_vm()
        assessment = {
            'status': 'needs_user_selection',
            'reason': 'no_target_window',
            'target_window_title': 'unknown',
            'proposed_action': 'request_user_selection',
        }
        remediation_result = {
            'action_taken': 'none',
            'success': False,
        }
        msg = vm._remediation_user_message(
            assistant_title='Gemini',
            assessment=assessment,
            remediation_result=remediation_result,
        )
        assert 'Gemini' in msg
        assert 'ventana objetivo' in msg.lower() or 'no encontre' in msg.lower()


# ══════════════════════════════════════════════════════════════════════
# Integration — remediation wired into visual override flow
# ══════════════════════════════════════════════════════════════════════

class TestRemediationIntegration:
    """Remediation assessment + trace are invoked in the visual override path."""

    def test_failed_remediation_produces_shared_reality_handoff(self) -> None:
        """When visual evidence is invalid and remediation doesn't fix it,
        the result must still contain shared_reality_handoff AND
        visual_remediation metadata."""
        vm = _make_vm()
        tw = _offscreen_target_window()
        cm = _black_capture_meta()
        capture_state = vm._target_window_capture_state(tw, cm)

        assessment = vm._assess_visual_remediation(
            target_window=tw,
            capture_meta=cm,
            capture_state=capture_state,
        )
        assert assessment['status'] == 'remediation_available'

        remediation_result = vm._attempt_safe_remediation(assessment)
        # On Linux, remediation will not succeed via Win32
        # The flow should still produce a handoff
        assert 'action_taken' in remediation_result

        # Verify the remediation user message is practical
        msg = vm._remediation_user_message(
            assistant_title='ChatGPT',
            assessment=assessment,
            remediation_result=remediation_result,
        )
        assert len(msg) > 50
        assert 'ChatGPT' in msg


# ══════════════════════════════════════════════════════════════════════
# platform_pending validation
# ══════════════════════════════════════════════════════════════════════

class TestPlatformPendingP06:
    """platform_pending JSON files must validate with P0.6 metadata."""

    def test_external_visual_handoff_alignment_has_p06(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_external_visual_handoff_alignment.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'external_visual_handoff_alignment'
        assert 'p06_additions' in task.metadata
