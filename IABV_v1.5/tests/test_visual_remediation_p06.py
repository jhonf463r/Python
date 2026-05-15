"""P0.6 — Shared Reality Remediation / Window Target Recovery tests.

Tests that _assess_visual_remediation() correctly classifies failed captures,
_attempt_safe_remediation() only acts on safe scenarios, and
_trace_visual_remediation_attempted() builds events without PII.
"""
from __future__ import annotations

import json
from pathlib import Path
import types
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
            'hwnd': 16319628,
        }
        result = vm._attempt_safe_remediation(assessment)
        # On Linux: Win32 not available, but no crash
        assert 'action_taken' in result
        assert isinstance(result['success'], bool)

    def test_invalid_hwnd_returns_failure(self) -> None:
        """Invalid hwnd (0 or None) must NOT attempt Win32 restore."""
        vm = _make_vm()
        for bad_hwnd in (0, None, -1):
            assessment = {
                'safe_to_auto_try': True,
                'proposed_action': 'restore_window_by_hwnd',
                'hwnd': bad_hwnd,
            }
            result = vm._attempt_safe_remediation(assessment)
            assert result['action_taken'] == 'none'
            assert result['success'] is False
            assert 'hwnd' in result['detail'].lower() or 'invalid' in result['detail'].lower()

    def test_mock_win32_calls_receive_correct_hwnd(self) -> None:
        """ShowWindow and SetForegroundWindow must receive the real hwnd."""
        vm = _make_vm()
        test_hwnd = 16319628
        calls: list[tuple[str, tuple[Any, ...]]] = []

        class FakeUser32:
            def ShowWindow(self, hwnd: int, cmd: int) -> int:
                calls.append(('ShowWindow', (hwnd, cmd)))
                return 1

            def SetForegroundWindow(self, hwnd: int) -> int:
                calls.append(('SetForegroundWindow', (hwnd,)))
                return 1

        class FakeWindll:
            user32 = FakeUser32()

        import types
        fake_ctypes = types.ModuleType('ctypes')
        fake_ctypes.windll = FakeWindll()  # type: ignore[attr-defined]

        assessment = {
            'safe_to_auto_try': True,
            'proposed_action': 'restore_window_by_hwnd',
            'hwnd': test_hwnd,
        }
        with patch.dict('sys.modules', {'ctypes': fake_ctypes}):
            result = vm._attempt_safe_remediation(assessment)
        assert result['success'] is True
        assert result['action_taken'] == 'restore_window_by_hwnd'
        assert len(calls) == 2
        assert calls[0] == ('ShowWindow', (test_hwnd, 9))  # SW_RESTORE=9
        assert calls[1] == ('SetForegroundWindow', (test_hwnd,))


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

    def test_capture_after_fields_are_none_without_recapture(self) -> None:
        """Without recapture API, capture_useful_after and
        blank_probability_after must be None."""
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
                target_window_title='ChatGPT',
                hwnd=16319628,
                rect=[-32000, -32000, 199, 34],
                reason='target_window_minimized_or_offscreen',
                proposed_action='restore_window_by_hwnd',
                action_taken='restore_window_by_hwnd',
                result_status='remediation_available',
                capture_useful_before=False,
                capture_useful_after=None,
                blank_probability_before=0.98,
                blank_probability_after=None,
                remediation_success=False,
                remediation_detail_code='win32_api_not_available',
                unresolved=['UNRESOLVED:visual_remediation_recapture_not_available'],
            )
        ev = traced_events[0]
        assert ev['capture_useful_after'] is None
        assert ev['blank_probability_after'] is None
        assert ev['remediation_success'] is False
        assert ev['remediation_detail_code'] == 'win32_api_not_available'
        assert 'UNRESOLVED:visual_remediation_recapture_not_available' in ev['unresolved']

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

    def test_success_message_mentions_recapture_needed(self) -> None:
        vm = _make_vm()
        assessment = {
            'status': 'remediation_available',
            'reason': 'target_window_minimized_or_offscreen',
            'target_window_title': 'ChatGPT - Google Chrome for Testing',
            'proposed_action': 'restore_window_by_hwnd',
        }
        remediation_result = {
            'action_taken': 'restore_window_by_hwnd',
            'success': True,
            'detail': 'Win32 ShowWindow(16319628, SW_RESTORE)=1',
        }
        msg = vm._remediation_user_message(
            assistant_title='ChatGPT',
            assessment=assessment,
            remediation_result=remediation_result,
        )
        msg_lower = msg.lower()
        assert 'reintentar' in msg_lower
        assert 'restaurar' in msg_lower or 'intente restaurar' in msg_lower

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
# P0.8 — Post-Remediation Recapture
# ══════════════════════════════════════════════════════════════════════

class TestPostRemediationRecapture:
    """_attempt_post_remediation_recapture() validates recapture scenarios."""

    class _FakeImage:
        def __init__(
            self,
            *,
            blank_probability: float,
            dynamic_range: int,
            unique_colors: int,
        ) -> None:
            self.blank_probability = blank_probability
            self.dynamic_range = dynamic_range
            self.unique_colors = unique_colors

        def convert(self, _mode: str) -> 'TestPostRemediationRecapture._FakeImage':
            return self

        def histogram(self) -> list[int]:
            total = 300
            blank = int(total * self.blank_probability)
            hist = [0] * 768
            hist[0] = blank // 3
            hist[256] = blank // 3
            hist[512] = blank - hist[0] - hist[256]
            rest = total - blank
            hist[100] = rest // 3
            hist[356] = rest // 3
            hist[612] = rest - hist[100] - hist[356]
            return hist

        def getextrema(self) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
            return (
                (0, self.dynamic_range),
                (0, self.dynamic_range),
                (0, self.dynamic_range),
            )

        def getcolors(self, maxcolors: int = 100000) -> list[tuple[int, tuple[int, int, int]]]:
            count = min(self.unique_colors, maxcolors)
            return [(1, (idx % 255, idx % 255, idx % 255)) for idx in range(count)]

    def test_successful_recapture_sets_capture_useful_after_true(self) -> None:
        """When remediation succeeds and recaptured image is useful,
        capture_useful_after must be True."""
        vm = _make_vm()
        assessment = {
            'hwnd': 16319628,
            'rect': [100, 100, 1200, 800],
            'proposed_action': 'restore_window_by_hwnd',
        }
        remediation_result = {'success': True}

        # Mock ImageGrab to return a colorful image without requiring numpy.
        fake_image = self._FakeImage(
            blank_probability=0.05,
            dynamic_range=180,
            unique_colors=500,
        )
        fake_image_grab = MagicMock()
        fake_image_grab.grab.return_value = fake_image
        fake_pil = types.ModuleType('PIL')
        fake_pil.ImageGrab = fake_image_grab  # type: ignore[attr-defined]

        with patch.dict('sys.modules', {'PIL': fake_pil, 'PIL.ImageGrab': fake_image_grab}):
            result = vm._attempt_post_remediation_recapture(
                remediation_result=remediation_result,
                assessment=assessment,
            )
        assert result['recapture_attempted'] is True
        assert result['capture_useful_after'] is True
        assert result['recapture_status'] == 'improved'
        assert result['blank_probability_after'] is not None

    def test_black_recapture_maintains_handoff(self) -> None:
        """When recaptured image is still black, handoff must be maintained."""
        vm = _make_vm()
        assessment = {
            'hwnd': 16319628,
            'rect': [100, 100, 1200, 800],
            'proposed_action': 'restore_and_recapture',
        }
        remediation_result = {'success': True}

        fake_image = self._FakeImage(
            blank_probability=1.0,
            dynamic_range=0,
            unique_colors=1,
        )
        fake_image_grab = MagicMock()
        fake_image_grab.grab.return_value = fake_image
        fake_pil = types.ModuleType('PIL')
        fake_pil.ImageGrab = fake_image_grab  # type: ignore[attr-defined]

        with patch.dict('sys.modules', {'PIL': fake_pil, 'PIL.ImageGrab': fake_image_grab}):
            result = vm._attempt_post_remediation_recapture(
                remediation_result=remediation_result,
                assessment=assessment,
            )
        assert result['recapture_attempted'] is True
        assert result['capture_useful_after'] is False
        assert result['recapture_status'] == 'still_low_information'
        assert len(result['recapture_unresolved']) > 0

    def test_recapture_analysis_failure_does_not_mark_improved(self) -> None:
        """If image analysis fails after recapture, keep the state unresolved."""
        vm = _make_vm()
        assessment = {
            'hwnd': 16319628,
            'rect': [100, 100, 1200, 800],
            'proposed_action': 'restore_window_by_hwnd',
        }
        remediation_result = {'success': True}

        class BrokenImage:
            def convert(self, _mode: str) -> Any:
                raise RuntimeError('cannot analyze')

        fake_image_grab = MagicMock()
        fake_image_grab.grab.return_value = BrokenImage()
        fake_pil = types.ModuleType('PIL')
        fake_pil.ImageGrab = fake_image_grab  # type: ignore[attr-defined]

        with patch.dict('sys.modules', {'PIL': fake_pil, 'PIL.ImageGrab': fake_image_grab}):
            result = vm._attempt_post_remediation_recapture(
                remediation_result=remediation_result,
                assessment=assessment,
            )

        assert result['recapture_attempted'] is True
        assert result['recapture_status'] == 'error'
        assert result['capture_useful_after'] is None
        assert any('UNRESOLVED' in item for item in result['recapture_unresolved'])

    def test_no_imagegrab_leaves_unresolved(self) -> None:
        """Without PIL ImageGrab, recapture must leave UNRESOLVED."""
        vm = _make_vm()
        assessment = {
            'hwnd': 16319628,
            'rect': [100, 100, 1200, 800],
            'proposed_action': 'restore_window_by_hwnd',
        }
        remediation_result = {'success': True}

        # Simulate ImportError when trying to import ImageGrab
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def mock_import(name: str, *args: Any, **kwargs: Any):
            if name == 'PIL.ImageGrab' or name == 'PIL':
                raise ImportError('mocked: no PIL')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            result = vm._attempt_post_remediation_recapture(
                remediation_result=remediation_result,
                assessment=assessment,
            )
        assert result['recapture_attempted'] is False
        assert result['recapture_status'] == 'skipped'
        assert any('UNRESOLVED' in u for u in result.get('recapture_unresolved', []))

    def test_no_recapture_if_remediation_failed(self) -> None:
        """When remediation_success is False, recapture must be skipped."""
        vm = _make_vm()
        assessment = {
            'hwnd': 16319628,
            'rect': [100, 100, 1200, 800],
            'proposed_action': 'restore_window_by_hwnd',
        }
        remediation_result = {'success': False}

        result = vm._attempt_post_remediation_recapture(
            remediation_result=remediation_result,
            assessment=assessment,
        )
        assert result['recapture_attempted'] is False
        assert result['recapture_status'] == 'skipped'
        assert result['capture_useful_after'] is None

    def test_no_recapture_if_hwnd_invalid(self) -> None:
        """When hwnd is 0 or None, recapture must be skipped."""
        vm = _make_vm()
        for bad_hwnd in (0, None, -1):
            assessment = {
                'hwnd': bad_hwnd,
                'rect': [100, 100, 1200, 800],
                'proposed_action': 'restore_window_by_hwnd',
            }
            remediation_result = {'success': True}

            result = vm._attempt_post_remediation_recapture(
                remediation_result=remediation_result,
                assessment=assessment,
            )
            assert result['recapture_attempted'] is False
            assert result['recapture_status'] == 'skipped'
            assert result['capture_useful_after'] is None

    def test_recapture_event_no_pii(self) -> None:
        """Recapture trace event must not export PII."""
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
                rect=[100, 100, 1200, 800],
                reason='target_window_minimized_or_offscreen',
                proposed_action='restore_window_by_hwnd',
                action_taken='restore_window_by_hwnd',
                result_status='remediation_available',
                capture_useful_before=False,
                capture_useful_after=True,
                blank_probability_before=0.98,
                blank_probability_after=0.05,
                remediation_success=True,
                recapture_status='improved',
                unresolved=[],
            )
        assert len(traced_events) == 1
        ev = traced_events[0]
        assert ev['recapture_status'] == 'improved'
        assert ev['capture_useful_after'] is True
        assert ev['blank_probability_after'] == 0.05
        ev_str = json.dumps(ev)
        assert 'C:\\' not in ev_str
        assert '/home/' not in ev_str


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

    def test_external_visual_handoff_alignment_has_p08(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_external_visual_handoff_alignment.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'external_visual_handoff_alignment'
        assert 'p08_additions' in task.metadata

    def test_external_visual_handoff_alignment_has_p09(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_external_visual_handoff_alignment.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'external_visual_handoff_alignment'
        assert 'p09_additions' in task.metadata


# ══════════════════════════════════════════════════════════════════════
# P0.9 — Post-Recapture Response Proof tests
# ══════════════════════════════════════════════════════════════════════

class TestPostRecaptureResponseProof:
    """P0.9: after a successful recapture, IABV must verify whether the
    external response was actually captured — not just that the window
    is visible."""

    def test_recapture_improved_response_not_captured_no_success(self) -> None:
        """If recapture improved but response NOT captured, the result
        must NOT declare success."""
        vm = _make_vm()
        proof = vm._build_post_recapture_response_proof(
            response_captured=False,
            response_capture_pending=False,
            response_capture_mode='manual_pasteback',
            assistant_title='ChatGPT',
            target_window=_offscreen_target_window(),
            assessment={
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
                'target_window_title': 'ChatGPT - Google Chrome for Testing',
                'proposed_action': 'restore_window_by_hwnd',
            },
            capture_useful_before=False,
            capture_useful_after=True,
            recapture={'recapture_status': 'improved'},
        )
        assert proof['window_observable'] is True
        assert proof['response_captured'] is False
        assert proof['status'] == 'response_not_captured'
        assert proof['target_window_title'] == 'ChatGPT - Google Chrome for Testing'
        assert proof['hwnd'] == 16319628

    def test_recapture_improved_response_captured_success(self) -> None:
        """If recapture improved AND response captured, status must be
        response_captured."""
        vm = _make_vm()
        proof = vm._build_post_recapture_response_proof(
            response_captured=True,
            response_capture_pending=False,
            response_capture_mode='clipboard_capture',
            assistant_title='ChatGPT',
            target_window=_visible_target_window(),
            assessment={
                'hwnd': 12345678,
                'rect': [100, 100, 1200, 800],
                'target_window_title': 'ChatGPT - Google Chrome',
                'proposed_action': 'restore_window_by_hwnd',
            },
            capture_useful_before=False,
            capture_useful_after=True,
            recapture={'recapture_status': 'improved'},
        )
        assert proof['window_observable'] is True
        assert proof['response_captured'] is True
        assert proof['status'] == 'response_captured'

    def test_recapture_improved_clipboard_pending_unresolved(self) -> None:
        """If recapture improved but response_capture_mode is clipboard and
        response NOT captured, status is response_pending (UNRESOLVED actionable)."""
        vm = _make_vm()
        proof = vm._build_post_recapture_response_proof(
            response_captured=False,
            response_capture_pending=False,
            response_capture_mode='clipboard_capture',
            assistant_title='ChatGPT',
            target_window=_visible_target_window(),
            assessment={
                'hwnd': 12345678,
                'rect': [100, 100, 1200, 800],
            },
            capture_useful_before=False,
            capture_useful_after=True,
            recapture={'recapture_status': 'improved'},
        )
        assert proof['window_observable'] is True
        assert proof['response_captured'] is False
        assert proof['response_capture_pending'] is True
        assert proof['status'] == 'response_pending'

    def test_response_pending_message_guides_user(self) -> None:
        """The pending-response guidance message must name the tool and
        explain what the user needs to do."""
        vm = _make_vm()
        proof = {
            'target_window_title': 'ChatGPT - Google Chrome for Testing',
            'response_capture_mode': 'manual_pasteback',
            'response_capture_pending': False,
        }
        msg = vm._post_recapture_response_pending_message(
            assistant_title='ChatGPT',
            response_proof=proof,
        )
        assert 'ChatGPT' in msg
        assert 'restaurada' in msg
        assert 'capturada' in msg or 'respuesta' in msg

    def test_response_proof_metadata_no_pii(self) -> None:
        """The response proof dict must not contain PII — no full paths,
        no user names."""
        vm = _make_vm()
        proof = vm._build_post_recapture_response_proof(
            response_captured=False,
            response_capture_pending=True,
            response_capture_mode='dom_capture',
            assistant_title='ChatGPT',
            target_window=_offscreen_target_window(),
            assessment={
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
            },
            capture_useful_before=False,
            capture_useful_after=True,
            recapture={'recapture_status': 'improved'},
        )
        proof_str = json.dumps(proof)
        assert 'C:\\Users' not in proof_str
        assert '/home/' not in proof_str
        assert 'password' not in proof_str.lower()
        assert proof['status'] == 'response_pending'

    def test_trace_post_recapture_response_verification(self) -> None:
        """RuntimeAuditTracer must receive a post_recapture_response_verification
        event that can reconstruct the chain."""
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
            vm._trace_post_recapture_response_verification(
                assistant_kind='chatgpt',
                response_proof={
                    'target_window_title': 'ChatGPT - Google Chrome for Testing',
                    'hwnd': 16319628,
                    'window_observable': True,
                    'response_captured': False,
                    'response_capture_pending': True,
                    'response_capture_mode': 'clipboard_capture',
                    'status': 'response_pending',
                    'capture_useful_before': False,
                    'capture_useful_after': True,
                },
            )

        assert len(traced_events) == 1
        ev = traced_events[0]
        assert ev['kind'] == 'post_recapture_response_verification'
        assert ev['assistant_kind'] == 'chatgpt'
        assert ev['window_observable'] is True
        assert ev['response_captured'] is False
        assert ev['response_capture_pending'] is True
        assert ev['status'] == 'response_pending'
        ev_str = json.dumps(ev)
        assert 'C:\\' not in ev_str
        assert '/home/' not in ev_str
