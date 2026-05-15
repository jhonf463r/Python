"""Focused tests for P0.3 visual evidence offscreen / black capture slice.

Task A: _window_rect_is_captureable classifies offscreen/minimized windows.
Task B: black/low-info capture produces visual_unresolved, not visual_captured.
Task C: user message contains guidance about minimized/offscreen/black capture.
Task D: runtime audit traces invalid visual evidence.
Task E: platform_pending JSONs validate with PlatformPendingTask.
Task F: action suggestions allow restore/retry.

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
    )
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
        combined = {**execution_state_metadata, **result_metadata}
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
        # No target_window but capture_meta_from_exec picks up the flat keys
        # _capture_is_low_information returns True for blank_probability >= 0.90
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
