"""Focused tests for P0.3 + P0.4 visual evidence and shared reality slices.

P0.3:
Task A: _window_rect_is_captureable classifies offscreen/minimized windows.
Task B: black/low-info capture produces visual_unresolved, not visual_captured.
Task C: user message contains guidance about minimized/offscreen/black capture.
Task D: runtime audit traces invalid visual evidence.
Task E: platform_pending JSONs validate with PlatformPendingTask.
Task F: action suggestions allow restore/retry.

P0.4:
Task A: _build_shared_reality_handoff creates causal handoff package.
Task B: _detect_user_mismatch_claim identifies user 'it works for me' signals.
Task C: shared reality message includes causal comparison.
Task D: evidence path exposure.
Task E: runtime audit shared_reality_handoff event.

Performance: pure-helper tests use a lightweight stub (no AppBootstrap).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from iabv_v15.domain.models import PlatformPendingTask


# ── Lightweight stub (mirrors test_runtime_p0_antifreeze.py pattern) ──

def _make_stub_vm():
    import types
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = SimpleNamespace(
        _active_dispatch_ids={},
        _working=False,
        _busy_label='',
        _latest_response_text='',
        _latest_response_meta='',
        _chat_messages=[],
        _auto_route_enabled=True,
        _selected_role='general_analyst',
        _active_interaction_id=None,
        _interaction_has_pending_followup=False,
        _autonomy_activity_override={},
        _diagnostic_text='',
        _diagnostic_truth_state='unresolved',
        _provider_refreshing=False,
        _ui_state_lock=threading.Lock(),
        _last_adaptive_payload={},
        _live_status='idle',
    )

    # Stub methods needed by _try_handle_shared_reality_followup
    def _set_live_status(status: str) -> None:
        stub._live_status = status

    def _append_message(role: str, speaker: str, text: str, meta: str = '',
                        **kwargs: Any) -> None:
        stub._chat_messages.append({
            'role': role, 'speaker': speaker, 'text': text, 'meta': meta,
        })

    stub._set_live_status = _set_live_status
    stub._append_message = _append_message
    # Bind methods from ControlCenterViewModel to the stub.
    # For static methods, we need to access them from __dict__ to get the
    # staticmethod descriptor, then extract __func__.
    static_names = set()
    for name in (
        '_window_rect_is_captureable',
        '_capture_is_low_information',
        '_target_window_capture_state',
        '_validate_visual_evidence_result',
        '_visual_handoff_message',
        '_trace_visual_evidence_invalid',
        # P0.4 methods
        '_build_shared_reality_handoff',
        '_detect_user_mismatch_claim',
        '_build_causal_explanation',
        '_shared_reality_user_message',
        '_attach_evidence_to_handoff',
        '_trace_shared_reality_handoff',
        '_try_handle_shared_reality_followup',
    ):
        raw = ControlCenterViewModel.__dict__.get(name)
        if isinstance(raw, staticmethod):
            stub.__dict__[name] = raw.__func__
            static_names.add(name)
        else:
            method = getattr(ControlCenterViewModel, name, None)
            if method is not None:
                stub.__dict__[name] = types.MethodType(method, stub)
    return stub


# ── Test 1: offscreen rect classified as not captureable ──

class TestWindowRectIsCaptureable:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_offscreen_minimized_rect(self) -> None:
        """rect=[-32000, -32000, 199, 34] must be NOT captureable."""
        assert self.vm._window_rect_is_captureable([-32000, -32000, 199, 34]) is False

    def test_offscreen_left_only(self) -> None:
        assert self.vm._window_rect_is_captureable([-31000, 100, 800, 600]) is False

    def test_offscreen_top_only(self) -> None:
        assert self.vm._window_rect_is_captureable([100, -31000, 800, 600]) is False

    def test_none_rect(self) -> None:
        assert self.vm._window_rect_is_captureable(None) is False

    def test_empty_rect(self) -> None:
        assert self.vm._window_rect_is_captureable([]) is False

    def test_too_small_rect(self) -> None:
        assert self.vm._window_rect_is_captureable([100, 100, 120, 110]) is False

    def test_normal_rect_is_captureable(self) -> None:
        assert self.vm._window_rect_is_captureable([100, 100, 1200, 800]) is True

    def test_borderline_valid_rect(self) -> None:
        assert self.vm._window_rect_is_captureable([0, 0, 200, 200]) is True


# ── Test 2: black capture produces visual_unresolved ──

class TestCaptureIsLowInformation:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_high_blank_probability(self) -> None:
        assert self.vm._capture_is_low_information({'blank_probability': 0.98}) is True

    def test_zero_dynamic_range(self) -> None:
        assert self.vm._capture_is_low_information({'dynamic_range': 0}) is True

    def test_single_color(self) -> None:
        assert self.vm._capture_is_low_information({'unique_color_count': 1}) is True

    def test_useful_false(self) -> None:
        assert self.vm._capture_is_low_information({'useful': False}) is True

    def test_normal_capture(self) -> None:
        assert self.vm._capture_is_low_information({
            'blank_probability': 0.1,
            'dynamic_range': 200,
            'unique_color_count': 500,
            'useful': True,
        }) is False

    def test_none_meta(self) -> None:
        assert self.vm._capture_is_low_information(None) is False


# ── Test 3: target_window_capture_state with offscreen window ──

class TestTargetWindowCaptureState:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_offscreen_window_produces_unresolved(self) -> None:
        target = {
            'title': 'ChatGPT - Google Chrome for Testing',
            'hwnd': 16319628,
            'rect': [-32000, -32000, 199, 34],
        }
        state = self.vm._target_window_capture_state(target)
        assert state['captureable'] is False
        assert state['reason'] == 'target_window_minimized_or_offscreen'
        assert 'UNRESOLVED:external_target_window_minimized_or_offscreen' in state['unresolved']
        assert 'UNRESOLVED:visual_capture_low_information' in state['unresolved']

    def test_black_capture_produces_low_information(self) -> None:
        target = {
            'title': 'ChatGPT',
            'hwnd': 12345,
            'rect': [100, 100, 1200, 800],
        }
        capture_meta = {
            'blank_probability': 0.98,
            'dynamic_range': 0,
            'unique_color_count': 1,
        }
        state = self.vm._target_window_capture_state(target, capture_meta)
        assert state['low_information'] is True
        assert 'UNRESOLVED:visual_capture_low_information' in state['unresolved']

    def test_no_target_window(self) -> None:
        state = self.vm._target_window_capture_state(None)
        assert state['captureable'] is False
        assert state['reason'] == 'no_target_window'

    def test_valid_window_and_capture(self) -> None:
        target = {
            'title': 'ChatGPT',
            'hwnd': 12345,
            'rect': [100, 100, 1200, 800],
        }
        capture_meta = {
            'blank_probability': 0.05,
            'dynamic_range': 200,
            'unique_color_count': 5000,
            'useful': True,
        }
        state = self.vm._target_window_capture_state(target, capture_meta)
        assert state['captureable'] is True
        assert state['low_information'] is False
        assert state['unresolved'] == []


# ── Test 4: user message contains guidance about offscreen/black capture ──

class TestUserMessageContent:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_offscreen_message_mentions_minimized(self) -> None:
        target = {
            'title': 'ChatGPT - Google Chrome for Testing',
            'hwnd': 16319628,
            'rect': [-32000, -32000, 199, 34],
        }
        state = self.vm._target_window_capture_state(target)
        msg = state['user_message']
        assert 'minimizada' in msg or 'fuera de pantalla' in msg
        assert 'negra' in msg or 'captura' in msg
        assert 'Restaura' in msg or 'reintenta' in msg

    def test_black_capture_message_mentions_information(self) -> None:
        target = {
            'title': 'ChatGPT',
            'hwnd': 12345,
            'rect': [100, 100, 1200, 800],
        }
        capture_meta = {'blank_probability': 0.98, 'dynamic_range': 0, 'unique_color_count': 1}
        state = self.vm._target_window_capture_state(target, capture_meta)
        msg = state['user_message']
        assert 'informacion' in msg.lower() or 'negra' in msg.lower() or 'vacia' in msg.lower()


# ── Test 5: suggested actions allow restore/retry ──

class TestSuggestedActions:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_offscreen_suggests_restore_and_retry(self) -> None:
        target = {
            'title': 'ChatGPT',
            'hwnd': 12345,
            'rect': [-32000, -32000, 199, 34],
        }
        state = self.vm._target_window_capture_state(target)
        actions = state['suggested_actions']
        assert 'restore_target_window' in actions
        assert 'retry_capture' in actions

    def test_low_info_suggests_restore_and_retry(self) -> None:
        target = {
            'title': 'ChatGPT',
            'hwnd': 12345,
            'rect': [100, 100, 1200, 800],
        }
        capture_meta = {'blank_probability': 0.99}
        state = self.vm._target_window_capture_state(target, capture_meta)
        actions = state['suggested_actions']
        assert 'restore_target_window' in actions
        assert 'retry_capture' in actions


# ── Test 6: runtime audit traces invalid evidence ──

class TestRuntimeAuditTrace:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_trace_visual_evidence_invalid_does_not_raise(self) -> None:
        """Tracing should be resilient — never raise even if tracer unavailable."""
        self.vm._trace_visual_evidence_invalid(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window={
                'title': 'ChatGPT - Google Chrome for Testing',
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
            },
            capture_meta={
                'blank_probability': 0.98,
                'dynamic_range': 0,
                'unique_color_count': 1,
                'useful': False,
            },
            reason='target_window_minimized_or_offscreen',
            suggested_actions=['restore_target_window', 'retry_capture'],
        )


# ── Test 7: platform_pending JSON validates with PlatformPendingTask ──

class TestPlatformPendingValidation:
    def test_external_visual_handoff_alignment_json(self) -> None:
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_external_visual_handoff_alignment.json'
        raw = path.read_text(encoding='utf-8')
        data = json.loads(raw)
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'external_visual_handoff_alignment'
        assert task.status.value in {'PENDING', 'READY_FOR_NEXT_SLICE', 'COMPLETED', 'BLOCKED', 'UNRESOLVED'}

    def test_runtime_consulting_lifecycle_recovery_json(self) -> None:
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_consulting_lifecycle_recovery.json'
        raw = path.read_text(encoding='utf-8')
        data = json.loads(raw)
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'runtime_consulting_lifecycle_recovery'

    def test_inv_phase_b_visual_metacognition_json(self) -> None:
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_inv_phase_b_visual_metacognition.json'
        raw = path.read_text(encoding='utf-8')
        data = json.loads(raw)
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'inv_phase_b_visual_metacognition'


# ── Test: visual handoff message content ──

class TestVisualHandoffMessage:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_handoff_message_offscreen(self) -> None:
        target = {
            'title': 'ChatGPT - Google Chrome for Testing',
            'hwnd': 16319628,
            'rect': [-32000, -32000, 199, 34],
        }
        capture_state = self.vm._target_window_capture_state(target)
        msg = self.vm._visual_handoff_message(
            assistant_title='ChatGPT',
            target_window=target,
            capture_state=capture_state,
        )
        assert 'ChatGPT' in msg
        assert 'minimizada' in msg or 'fuera de pantalla' in msg
        assert 'negra' in msg or 'sin informacion' in msg
        assert 'hwnd=' in msg
        assert 'rect=' in msg
        assert 'restaurar' in msg.lower() or 'reintenta' in msg.lower()

    def test_handoff_message_no_target(self) -> None:
        capture_state = self.vm._target_window_capture_state(None)
        msg = self.vm._visual_handoff_message(
            assistant_title='ChatGPT',
            target_window=None,
            capture_state=capture_state,
        )
        assert 'ChatGPT' in msg
        assert 'no se encontro' in msg.lower() or 'no encontr' in msg.lower()


# ── Test: validate_visual_evidence_result integration ──

class TestValidateVisualEvidenceResult:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_offscreen_window_returns_override(self) -> None:
        result_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT - Google Chrome for Testing',
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
            },
        }
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=result_metadata,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None
        assert override['visual_unresolved'] is True
        assert consultation_metadata['status'] == 'visual_unresolved'
        assert 'UNRESOLVED:external_target_window_minimized_or_offscreen' in consultation_metadata.get('unresolved', [])

    def test_black_capture_returns_override(self) -> None:
        result_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT',
                'hwnd': 12345,
                'rect': [100, 100, 1200, 800],
            },
            'visual_evidence_snapshot': {
                'blank_probability': 0.98,
                'dynamic_range': 0,
                'unique_color_count': 1,
                'useful': False,
            },
        }
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=result_metadata,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None
        assert override['visual_unresolved'] is True
        assert consultation_metadata['status'] == 'visual_unresolved'
        assert 'UNRESOLVED:visual_capture_low_information' in consultation_metadata.get('unresolved', [])

    def test_valid_evidence_returns_none(self) -> None:
        result_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT',
                'hwnd': 12345,
                'rect': [100, 100, 1200, 800],
            },
            'visual_evidence_snapshot': {
                'blank_probability': 0.05,
                'dynamic_range': 200,
                'unique_color_count': 5000,
                'useful': True,
            },
        }
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=result_metadata,
            consultation_metadata=consultation_metadata,
        )
        assert override is None
        assert consultation_metadata['status'] == 'prepared'

    def test_no_target_no_capture_returns_none(self) -> None:
        """When neither target_window nor capture_meta is present, skip validation."""
        result_metadata: dict[str, Any] = {}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=result_metadata,
            consultation_metadata=consultation_metadata,
        )
        assert override is None


# ── Test: real wiring — evidence only in execution_state.metadata ──

class TestExecutionStateMetadataWiring:
    """Reproduce the live flow: target_window and capture metrics live in
    execution_state.metadata, NOT in result.metadata. The combined dict
    that _execute_external_consultation_sync builds must surface them.
    """

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_offscreen_in_execution_state_metadata_produces_visual_unresolved(self) -> None:
        """Simulates the live case: target_window + blank metrics in
        execution_state.metadata only, result.metadata is empty."""
        execution_state_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT - Google Chrome for Testing',
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
            },
            'blank_probability': 0.98,
            'dynamic_range': 0,
            'unique_color_count': 1,
            'useful': False,
            'capture_scope': 'external_target_window_bbox',
        }
        result_metadata: dict[str, Any] = {}
        # Build combined dict as _execute_external_consultation_sync does:
        # execution_state.metadata prevails on conflict
        combined = {**result_metadata, **execution_state_metadata}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=combined,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None
        assert override['visual_unresolved'] is True
        assert override['reason'] == 'target_window_minimized_or_offscreen'
        assert consultation_metadata['status'] == 'visual_unresolved'
        assert 'UNRESOLVED:external_target_window_minimized_or_offscreen' in consultation_metadata.get('unresolved', [])
        assert 'UNRESOLVED:visual_capture_low_information' in consultation_metadata.get('unresolved', [])

    def test_black_metrics_in_execution_state_no_target_window(self) -> None:
        """Blank probability and low-info metrics in execution_state only,
        no target_window anywhere — should still detect via flat keys."""
        execution_state_metadata: dict[str, Any] = {
            'blank_probability': 0.95,
            'dynamic_range': 0,
            'unique_color_count': 2,
            'useful': False,
        }
        combined = {**execution_state_metadata}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=combined,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None
        assert consultation_metadata['status'] == 'visual_unresolved'

    def test_valid_capture_in_execution_state_returns_none(self) -> None:
        """Valid evidence in execution_state.metadata should pass through."""
        execution_state_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT',
                'hwnd': 12345,
                'rect': [100, 100, 1200, 800],
            },
            'blank_probability': 0.05,
            'dynamic_range': 200,
            'unique_color_count': 5000,
            'useful': True,
        }
        combined = {**execution_state_metadata}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=combined,
            consultation_metadata=consultation_metadata,
        )
        assert override is None
        assert consultation_metadata['status'] == 'prepared'

    def test_execution_state_prevails_on_conflict(self) -> None:
        """When both result.metadata and execution_state.metadata have
        the same key, execution_state.metadata must win (live capture data)."""
        result_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT',
                'hwnd': 12345,
                'rect': [100, 100, 1200, 800],
            },
            'blank_probability': 0.05,
            'useful': True,
        }
        execution_state_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT - Google Chrome for Testing',
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
            },
            'blank_probability': 0.98,
            'dynamic_range': 0,
            'unique_color_count': 1,
            'useful': False,
        }
        # execution_state.metadata prevails: same merge order as production
        combined = {**result_metadata, **execution_state_metadata}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=combined,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None, (
            'execution_state.metadata has offscreen rect and blank capture — must override'
        )
        assert override['visual_unresolved'] is True
        assert override['reason'] == 'target_window_minimized_or_offscreen'
        assert consultation_metadata['status'] == 'visual_unresolved'

    def test_offscreen_user_message_contains_required_keywords(self) -> None:
        """User message from offscreen override must contain keywords about
        minimized/offscreen window, black capture, and retry."""
        execution_state_metadata: dict[str, Any] = {
            'target_window': {
                'title': 'ChatGPT - Google Chrome for Testing',
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
            },
            'blank_probability': 0.98,
            'dynamic_range': 0,
            'unique_color_count': 1,
            'useful': False,
        }
        combined = {**execution_state_metadata}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=combined,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None
        msg = override['user_message'].lower()
        assert any(kw in msg for kw in ('minimizada', 'fuera de pantalla', 'offscreen')), (
            f'Message must mention minimized/offscreen window, got: {msg}'
        )
        assert any(kw in msg for kw in ('negra', 'black', 'baja información', 'low information')), (
            f'Message must mention black/low-info capture, got: {msg}'
        )
        assert any(kw in msg for kw in ('restaura', 'reintenta', 'retry', 'restore')), (
            f'Message must guide user to restore/retry, got: {msg}'
        )


# ══════════════════════════════════════════════════════════════════════
# P0.4 — Shared Reality / Causal Handoff tests
# ══════════════════════════════════════════════════════════════════════

# -- Helpers for P0.4 tests --

_LIVE_TARGET_WINDOW: dict[str, Any] = {
    'title': 'ChatGPT - Google Chrome for Testing',
    'hwnd': 16319628,
    'rect': [-32000, -32000, 199, 34],
}

_LIVE_CAPTURE_META: dict[str, Any] = {
    'blank_probability': 0.98,
    'dynamic_range': 0,
    'unique_color_count': 1,
    'useful': False,
    'capture_scope': 'external_target_window_bbox',
}


def _offscreen_capture_state(vm: Any) -> dict[str, Any]:
    """Get capture_state for the live offscreen case."""
    return vm._target_window_capture_state(_LIVE_TARGET_WINDOW, _LIVE_CAPTURE_META)


# ── Test G.1: user says "a mí sí me funciona" + offscreen + black capture ──

class TestSharedRealityMismatch:
    """User says 'it works for me', IABV has offscreen window + black capture.
    The message must explain the difference between browsers/sessions."""

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_user_mismatch_with_offscreen_produces_causal_explanation(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
            user_claim='a mí sí me funciona',
        )
        msg = self.vm._shared_reality_user_message(
            handoff=handoff,
            user_claim='a mí sí me funciona',
        )
        msg_lower = msg.lower()
        assert 'chatgpt' in msg_lower
        assert any(kw in msg_lower for kw in ('chrome for testing', 'sesión aislada', 'sesión controlada'))
        assert any(kw in msg_lower for kw in ('minimizada', 'fuera de pantalla', 'offscreen'))
        assert any(kw in msg_lower for kw in ('negra', 'baja información'))
        assert 'a mí sí me funciona' in msg_lower

    def test_mismatch_claim_detected(self) -> None:
        assert self.vm._detect_user_mismatch_claim('a mí sí me funciona') == 'a mí sí me funciona'
        assert self.vm._detect_user_mismatch_claim('yo sí lo veo bien') == 'yo sí lo veo'
        assert self.vm._detect_user_mismatch_claim('en mi navegador sí abre') == 'en mi navegador sí'
        assert self.vm._detect_user_mismatch_claim('por qué a mí sí y a él no') == 'por qué a mí sí'
        assert self.vm._detect_user_mismatch_claim('a mí me funciona bien') == 'a mí me funciona'

    def test_no_mismatch_on_unrelated_text(self) -> None:
        assert self.vm._detect_user_mismatch_claim('hola') == ''
        assert self.vm._detect_user_mismatch_claim('consulta chatgpt') == ''
        assert self.vm._detect_user_mismatch_claim('') == ''


# ── Test G.2: message includes required fields ──

class TestSharedRealityMessageContent:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_message_includes_tool_browser_rect_black_capture_actions(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
        )
        msg = self.vm._shared_reality_user_message(handoff=handoff)
        msg_lower = msg.lower()
        # Tool name
        assert 'chatgpt' in msg_lower
        # Browser/session info
        assert any(kw in msg_lower for kw in ('chrome for testing', 'sesión aislada', 'sesión controlada'))
        # rect/hwnd
        assert '16319628' in msg or 'hwnd' in msg_lower
        assert '-32000' in msg
        # Black capture
        assert any(kw in msg_lower for kw in ('negra', 'baja información', 'blank_probability'))
        # Actions
        assert any(kw in msg_lower for kw in ('restaurar', 'reintentar', 'seleccionar', 'autorizar'))


# ── Test G.3: missing evidence → unknown/UNRESOLVED, not invented ──

class TestSharedRealityMissingEvidence:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_no_target_window_marks_unknown(self) -> None:
        capture_state = self.vm._target_window_capture_state(None, None)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=None,
            capture_meta=None,
            capture_state=capture_state,
        )
        assert handoff['target_window_title'] == 'unknown'
        assert handoff['selected_browser_or_profile'] == 'unknown'
        assert any('UNRESOLVED' in t for t in handoff['unresolved'])
        assert handoff['evidence_path'] == 'no_disponible'

    def test_partial_evidence_fills_what_it_can(self) -> None:
        partial_window: dict[str, Any] = {'title': 'ChatGPT', 'hwnd': 999}
        capture_state = self.vm._target_window_capture_state(partial_window, None)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=partial_window,
            capture_meta=None,
            capture_state=capture_state,
        )
        assert handoff['target_window_title'] == 'ChatGPT'
        assert handoff['hwnd'] == 999
        assert handoff['rect'] is None


# ── Test G.4: runtime audit receives shared_reality_handoff ──

class TestSharedRealityAuditTrace:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_trace_does_not_raise(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
            user_claim='a mí sí me funciona',
        )
        # Should not raise even without a live RuntimeAuditTracer
        self.vm._trace_shared_reality_handoff(handoff)

    def test_handoff_has_required_audit_fields(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
            user_claim='a mí sí me funciona',
        )
        # Verify all fields needed by _trace_shared_reality_handoff
        assert 'requested_tool' in handoff
        assert 'user_claim' in handoff
        assert 'target_window_title' in handoff
        assert 'selected_browser_or_profile' in handoff
        assert 'hwnd' in handoff
        assert 'rect' in handoff
        assert 'capture_scope' in handoff
        assert 'capture_useful' in handoff
        assert 'mismatch_reason' in handoff
        assert 'causal_explanation' in handoff
        assert 'user_action_needed' in handoff
        assert 'unresolved' in handoff
        assert handoff['user_claim'] == 'a mí sí me funciona'
        assert handoff['capture_useful'] is False


# ── Test G.5: no false success when capture_useful=false ──

class TestNoFalseSuccessOnSharedReality:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_visual_override_still_prevents_success(self) -> None:
        """Even with shared reality handoff, the flow must NOT report success
        when capture is black/useless."""
        combined = {**_LIVE_CAPTURE_META, 'target_window': _LIVE_TARGET_WINDOW}
        consultation_metadata: dict[str, Any] = {
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
        }
        override = self.vm._validate_visual_evidence_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            result_metadata=combined,
            consultation_metadata=consultation_metadata,
        )
        assert override is not None
        assert override['visual_unresolved'] is True
        assert consultation_metadata['status'] == 'visual_unresolved'
        assert consultation_metadata['status'] != 'prepared'
        assert consultation_metadata['status'] != 'visual_captured'


# ── Test G.6: causal explanation structure ──

class TestCausalExplanation:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_causal_explanation_has_tu_vista_vs_iabv(self) -> None:
        explanation = self.vm._build_causal_explanation(
            assistant_title='ChatGPT',
            browser_label='Chrome for Testing (sesión aislada de IABV)',
            target_title='ChatGPT - Google Chrome for Testing',
            reason='target_window_minimized_or_offscreen',
            rect=[-32000, -32000, 199, 34],
            blank_prob=0.98,
        )
        expl_lower = explanation.lower()
        assert 'tu vista' in expl_lower
        assert 'vista de iabv' in expl_lower
        assert 'chrome for testing' in expl_lower
        assert 'minimizada' in expl_lower or 'fuera de pantalla' in expl_lower
        assert 'negra' in expl_lower or 'sin información' in expl_lower
        assert 'no puedo confirmar' in expl_lower
        assert 'restaures' in expl_lower or 'autorices' in expl_lower

    def test_causal_explanation_no_target_window(self) -> None:
        explanation = self.vm._build_causal_explanation(
            assistant_title='ChatGPT',
            browser_label='unknown',
            target_title='',
            reason='no_target_window',
        )
        assert 'no encontré' in explanation.lower() or 'no encontre' in explanation.lower()


# ── Test G.7: evidence path exposure ──

class TestEvidencePathExposure:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_evidence_path_attached_from_metadata(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
        )
        result_metadata = {'screenshot_path': 'C:\\captures\\black_capture.png'}
        updated = self.vm._attach_evidence_to_handoff(handoff, result_metadata)
        assert updated['evidence_path'] == 'C:\\captures\\black_capture.png'
        assert updated['evidence_metadata']['useful'] is False
        assert updated['evidence_metadata']['reason'] == 'low_information_pixels'
        assert updated['evidence_metadata']['description'] == 'Esto fue lo que capturé'

    def test_no_evidence_path_stays_no_disponible(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
        )
        result_metadata: dict[str, Any] = {}
        updated = self.vm._attach_evidence_to_handoff(handoff, result_metadata)
        assert updated['evidence_path'] == 'no_disponible'
        assert 'evidence_metadata' not in updated


# ── Test G.8: handoff package has all required fields ──

class TestHandoffPackageFields:
    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_all_required_fields_present(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
            user_claim='a mí sí me funciona',
            evidence_path='C:\\captures\\test.png',
        )
        required_fields = [
            'user_claim', 'requested_tool', 'selected_tool',
            'selected_browser_or_profile', 'target_window_title',
            'hwnd', 'rect', 'capture_scope', 'capture_useful',
            'capture_quality', 'mismatch_reason', 'causal_explanation',
            'user_action_needed', 'fallback_available', 'unresolved',
            'evidence_path',
        ]
        for field in required_fields:
            assert field in handoff, f'Missing required field: {field}'
        assert handoff['user_claim'] == 'a mí sí me funciona'
        assert handoff['requested_tool'] == 'chatgpt'
        assert handoff['capture_useful'] is False
        assert handoff['fallback_available'] is True
        assert 'authorize_visible_browser' in handoff['user_action_needed']
        cq = handoff['capture_quality']
        assert cq['blank_probability'] == 0.98
        assert cq['dynamic_range'] == 0
        assert cq['unique_color_count'] == 1

    def test_chrome_for_testing_detected_as_isolated_session(self) -> None:
        capture_state = _offscreen_capture_state(self.vm)
        handoff = self.vm._build_shared_reality_handoff(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            target_window=_LIVE_TARGET_WINDOW,
            capture_meta=_LIVE_CAPTURE_META,
            capture_state=capture_state,
        )
        assert 'Chrome for Testing' in handoff['selected_browser_or_profile']
        assert 'aislada' in handoff['selected_browser_or_profile']


# ══════════════════════════════════════════════════════════════════════
# P0.4 — Wired followup flow tests
# ══════════════════════════════════════════════════════════════════════

def _build_payload_with_handoff() -> dict[str, Any]:
    """Build a _last_adaptive_payload containing a shared_reality_handoff."""
    return {
        'metadata': {
            'shared_reality_handoff': {
                'user_claim': 'unknown',
                'requested_tool': 'chatgpt',
                'selected_tool': 'chatgpt',
                'selected_browser_or_profile': 'Chrome for Testing (sesión aislada de IABV)',
                'target_window_title': 'ChatGPT - Google Chrome for Testing',
                'hwnd': 16319628,
                'rect': [-32000, -32000, 199, 34],
                'capture_scope': 'external_target_window_bbox',
                'capture_useful': False,
                'capture_quality': {
                    'blank_probability': 0.98,
                    'dynamic_range': 0,
                    'unique_color_count': 1,
                    'useful': False,
                },
                'mismatch_reason': (
                    'La ventana que IABV usa está minimizada o fuera de pantalla. '
                    'Tú probablemente ves tu navegador/sesión normal, pero IABV '
                    'usa una sesión aislada que no está visible.'
                ),
                'causal_explanation': 'Tu vista vs Vista de IABV ...',
                'user_action_needed': [
                    'restore_target_window',
                    'select_visible_window',
                    'retry_capture',
                    'authorize_visible_browser',
                ],
                'fallback_available': True,
                'unresolved': [
                    'UNRESOLVED:external_target_window_minimized_or_offscreen',
                    'UNRESOLVED:visual_capture_low_information',
                    'UNRESOLVED:shared_reality_mismatch_pending_live_proof',
                ],
                'evidence_path': 'no_disponible',
            },
        },
    }


class TestSharedRealityFollowupWiring:
    """Tests for _try_handle_shared_reality_followup — the wired flow
    that connects user chat messages to the shared reality handoff."""

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_with_handoff_and_mismatch_claim_responds_causally(self) -> None:
        """User says 'a mí sí me funciona' after a visual failure that
        produced a shared_reality_handoff → IABV responds with causal
        explanation including Tu vista / Vista de IABV."""
        self.vm._last_adaptive_payload = _build_payload_with_handoff()
        result = self.vm._try_handle_shared_reality_followup('a mí sí me funciona')
        assert result is True
        assert len(self.vm._chat_messages) == 1
        msg = self.vm._chat_messages[0]
        assert msg['role'] == 'assistant'
        assert msg['speaker'] == 'IABV'
        assert msg['meta'] == 'shared_reality_followup'
        text_lower = msg['text'].lower()
        assert 'chatgpt' in text_lower
        assert any(kw in text_lower for kw in ('chrome for testing', 'sesión aislada'))
        assert any(kw in text_lower for kw in ('minimizada', 'fuera de pantalla'))
        assert any(kw in text_lower for kw in ('negra', 'baja información'))
        assert any(kw in text_lower for kw in ('restaurar', 'reintentar', 'autorizar'))
        assert 'a mí sí me funciona' in text_lower

    def test_without_handoff_returns_false(self) -> None:
        """No shared_reality_handoff in payload → returns False without
        intercepting, allowing normal chat flow to continue."""
        self.vm._last_adaptive_payload = {}
        result = self.vm._try_handle_shared_reality_followup('a mí sí me funciona')
        assert result is False
        assert len(self.vm._chat_messages) == 0

    def test_unrelated_message_with_handoff_returns_false(self) -> None:
        """Handoff exists but user message doesn't match any mismatch
        pattern → returns False."""
        self.vm._last_adaptive_payload = _build_payload_with_handoff()
        result = self.vm._try_handle_shared_reality_followup('hola, qué tal')
        assert result is False
        assert len(self.vm._chat_messages) == 0

    def test_updates_user_claim_in_handoff(self) -> None:
        """The handler must update user_claim in the handoff with the
        actual user phrase that triggered the followup."""
        self.vm._last_adaptive_payload = _build_payload_with_handoff()
        self.vm._try_handle_shared_reality_followup('yo sí lo veo bien')
        assert len(self.vm._chat_messages) == 1
        text_lower = self.vm._chat_messages[0]['text'].lower()
        assert 'yo sí lo veo' in text_lower

    def test_multiple_patterns_work(self) -> None:
        """Various mismatch patterns should all trigger the followup."""
        patterns = [
            'en mi navegador sí abre',
            'por qué a mí sí y a él no',
            'a mí me funciona bien',
            'funciona en mi computador',
        ]
        for pattern in patterns:
            vm = _make_stub_vm()
            vm._last_adaptive_payload = _build_payload_with_handoff()
            result = vm._try_handle_shared_reality_followup(pattern)
            assert result is True, f'Pattern "{pattern}" should trigger followup'
            assert len(vm._chat_messages) == 1, f'Pattern "{pattern}" should produce a message'

    def test_sets_live_status_to_idle(self) -> None:
        """After responding, the live status must be set to idle."""
        self.vm._last_adaptive_payload = _build_payload_with_handoff()
        self.vm._try_handle_shared_reality_followup('a mí sí me funciona')
        assert self.vm._live_status == 'idle'

    def test_updates_latest_response_and_busy_label(self) -> None:
        """Handler must update _latest_response_text, _latest_response_meta,
        and clear _busy_label."""
        self.vm._last_adaptive_payload = _build_payload_with_handoff()
        self.vm._try_handle_shared_reality_followup('a mí sí me funciona')
        assert self.vm._latest_response_text != ''
        assert 'chatgpt' in self.vm._latest_response_text.lower()
        assert 'shared_reality_followup' in self.vm._latest_response_meta
        assert self.vm._busy_label == ''

    def test_preserves_original_handoff_evidence(self) -> None:
        """The handoff copy used for the response must preserve all original
        evidence fields (rect, hwnd, capture_quality, etc.)."""
        self.vm._last_adaptive_payload = _build_payload_with_handoff()
        self.vm._try_handle_shared_reality_followup('a mí sí me funciona')
        msg_text = self.vm._chat_messages[0]['text']
        assert '16319628' in msg_text or 'hwnd' in msg_text.lower()
        assert '-32000' in msg_text
