"""Tests for anti-freeze frame budget + visual metacognition enhancements.

Anti-freeze:
- _begin_frame / _frame_budget_remaining_ms / _should_skip_remaining_heavy_work
- OSES _frame_budget_overrun_findings detects repeated overruns

Visual metacognition:
- _capture_is_partial_occlusion detects occluded target
- _capture_is_wrong_window detects title mismatch
- _capture_resolution_too_low detects small captures
- _target_window_capture_state integrates all detections
- OSES _visual_metacognition_findings detects repeated patterns
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------
# Anti-freeze frame budget tests
# ---------------------------------------------------------------

class TestFrameBudgetAccounting:
    """Per-frame UI-thread budget accounting."""

    def _make_vm(self) -> Any:
        """Create a minimal ControlCenterViewModel-like object with budget methods."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        # Use __new__ to avoid full init
        vm = object.__new__(ControlCenterViewModel)
        return vm

    def test_begin_frame_returns_monotonic(self) -> None:
        vm = self._make_vm()
        t0 = vm._begin_frame()
        assert t0 > 0
        t1 = vm._begin_frame()
        assert t1 >= t0

    def test_frame_budget_remaining_positive_initially(self) -> None:
        vm = self._make_vm()
        # Patch _should_defer_heavy_work to return False (no pressure)
        vm._should_defer_heavy_work = lambda: False
        t0 = vm._begin_frame()
        remaining = vm._frame_budget_remaining_ms(t0)
        assert remaining > 0
        assert remaining <= 50.0

    def test_frame_budget_reduced_under_pressure(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: True
        t0 = vm._begin_frame()
        remaining = vm._frame_budget_remaining_ms(t0)
        assert remaining <= 25.0

    def test_should_skip_returns_false_within_budget(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: False
        t0 = vm._begin_frame()
        assert vm._should_skip_remaining_heavy_work(t0) is False

    def test_should_skip_returns_true_after_budget_exhausted(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: False
        # Simulate a frame that started 100ms ago (budget = 50ms)
        t0 = time.monotonic() - 0.100
        assert vm._should_skip_remaining_heavy_work(t0) is True

    def test_frame_budget_constants_exist(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert ControlCenterViewModel._FRAME_BUDGET_MS == 50.0
        assert ControlCenterViewModel._FRAME_BUDGET_PRESSURE_MS == 25.0


# ---------------------------------------------------------------
# Visual metacognition detection tests
# ---------------------------------------------------------------

class TestPartialOcclusionDetection:
    """_capture_is_partial_occlusion detects occluded targets."""

    def _call(self, capture_meta, target_window=None):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        return ControlCenterViewModel._capture_is_partial_occlusion(
            capture_meta, target_window,
        )

    def test_high_occlusion_pct(self) -> None:
        assert self._call({'occluded_pct': 45.0}) is True

    def test_low_occlusion_pct(self) -> None:
        assert self._call({'occluded_pct': 10.0}) is False

    def test_foreground_hwnd_mismatch(self) -> None:
        assert self._call(
            {'foreground_hwnd': 999},
            {'hwnd': 123},
        ) is True

    def test_foreground_hwnd_match(self) -> None:
        assert self._call(
            {'foreground_hwnd': 123},
            {'hwnd': 123},
        ) is False

    def test_none_inputs(self) -> None:
        assert self._call(None) is False
        assert self._call({}) is False


class TestWrongWindowDetection:
    """_capture_is_wrong_window detects title mismatch."""

    def _call(self, capture_meta, target_window=None):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        return ControlCenterViewModel._capture_is_wrong_window(
            capture_meta, target_window,
        )

    def test_different_titles(self) -> None:
        assert self._call(
            {'captured_title': 'Notepad'},
            {'title': 'ChatGPT - Google Chrome'},
        ) is True

    def test_matching_titles(self) -> None:
        assert self._call(
            {'captured_title': 'ChatGPT - Google Chrome'},
            {'title': 'ChatGPT - Google Chrome'},
        ) is False

    def test_substring_match_ok(self) -> None:
        assert self._call(
            {'captured_title': 'ChatGPT - Google Chrome'},
            {'title': 'ChatGPT'},
        ) is False

    def test_empty_titles(self) -> None:
        assert self._call({'captured_title': ''}, {'title': 'ChatGPT'}) is False
        assert self._call({'captured_title': 'Notepad'}, {'title': ''}) is False

    def test_none_inputs(self) -> None:
        assert self._call(None) is False
        assert self._call({}, None) is False


class TestResolutionTooLow:
    """_capture_resolution_too_low detects small captures."""

    def _call(self, capture_meta, **kw):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        return ControlCenterViewModel._capture_resolution_too_low(
            capture_meta, **kw,
        )

    def test_small_capture(self) -> None:
        assert self._call({'capture_width': 100, 'capture_height': 80}) is True

    def test_adequate_capture(self) -> None:
        assert self._call({'capture_width': 1920, 'capture_height': 1080}) is False

    def test_width_too_small(self) -> None:
        assert self._call({'capture_width': 50, 'capture_height': 300}) is True

    def test_height_too_small(self) -> None:
        assert self._call({'capture_width': 400, 'capture_height': 100}) is True

    def test_custom_minimum(self) -> None:
        assert self._call(
            {'capture_width': 300, 'capture_height': 200},
            min_width=400, min_height=300,
        ) is True

    def test_alternate_keys(self) -> None:
        assert self._call({'width': 50, 'height': 50}) is True

    def test_none_inputs(self) -> None:
        assert self._call(None) is False
        assert self._call({}) is False


class TestTargetWindowCaptureStateIntegration:
    """_target_window_capture_state integrates all visual detections."""

    def _make_vm(self) -> Any:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = object.__new__(ControlCenterViewModel)
        return vm

    def test_partial_occlusion_detected(self) -> None:
        vm = self._make_vm()
        result = vm._target_window_capture_state(
            target_window={'rect': [100, 100, 800, 600], 'title': 'ChatGPT', 'hwnd': 123},
            capture_meta={'foreground_hwnd': 999},
        )
        assert 'UNRESOLVED:visual_capture_partial_occlusion' in result['unresolved']
        assert result['low_information'] is True

    def test_wrong_window_detected(self) -> None:
        vm = self._make_vm()
        result = vm._target_window_capture_state(
            target_window={'rect': [100, 100, 800, 600], 'title': 'ChatGPT', 'hwnd': 123},
            capture_meta={'captured_title': 'Notepad', 'foreground_hwnd': 123},
        )
        assert 'UNRESOLVED:visual_capture_wrong_window' in result['unresolved']
        assert result['captureable'] is False

    def test_resolution_too_low_detected(self) -> None:
        vm = self._make_vm()
        result = vm._target_window_capture_state(
            target_window={'rect': [100, 100, 500, 400], 'title': 'Tool', 'hwnd': 123},
            capture_meta={'capture_width': 50, 'capture_height': 20, 'foreground_hwnd': 123},
        )
        assert 'UNRESOLVED:visual_capture_resolution_too_low' in result['unresolved']

    def test_clean_capture_no_issues(self) -> None:
        vm = self._make_vm()
        result = vm._target_window_capture_state(
            target_window={'rect': [100, 100, 1000, 800], 'title': 'ChatGPT', 'hwnd': 123},
            capture_meta={
                'foreground_hwnd': 123,
                'captured_title': 'ChatGPT - Google Chrome',
                'capture_width': 900, 'capture_height': 700,
            },
        )
        assert result['captureable'] is True
        assert result['low_information'] is False
        assert result['unresolved'] == []


# ---------------------------------------------------------------
# OSES findings tests
# ---------------------------------------------------------------

class TestOSESFrameBudgetFindings:
    """OSES _frame_budget_overrun_findings detects repeated overruns."""

    def _write_events(self, tmp: str, events: list[dict]) -> None:
        logs = Path(tmp) / 'data' / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / 'runtime_audit.jsonl').open('w') as fh:
            for e in events:
                fh.write(json.dumps(e) + '\n')

    def _make_oses(self, workspace: str) -> Any:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        svc.workspace_root = workspace
        return svc

    def test_no_finding_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_events(tmp, [
                {'kind': 'ui_frame_budget_overrun', 'data': {'elapsed_ms': 80}},
                {'kind': 'ui_frame_budget_overrun', 'data': {'elapsed_ms': 90}},
            ])
            svc = self._make_oses(tmp)
            findings = svc._frame_budget_overrun_findings()
            assert len(findings) == 0

    def test_finding_at_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_events(tmp, [
                {'kind': 'ui_frame_budget_overrun', 'data': {'elapsed_ms': 80}},
                {'kind': 'ui_frame_budget_overrun', 'data': {'elapsed_ms': 90}},
                {'kind': 'ui_frame_budget_overrun', 'data': {'elapsed_ms': 100}},
            ])
            svc = self._make_oses(tmp)
            findings = svc._frame_budget_overrun_findings()
            assert len(findings) == 1
            assert findings[0].category == 'repeated_frame_budget_overrun'

    def test_no_crash_without_workspace(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        assert svc._frame_budget_overrun_findings() == []


class TestOSESVisualMetacognitionFindings:
    """OSES _visual_metacognition_findings detects repeated patterns."""

    def _write_events(self, tmp: str, events: list[dict]) -> None:
        logs = Path(tmp) / 'data' / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / 'runtime_audit.jsonl').open('w') as fh:
            for e in events:
                fh.write(json.dumps(e) + '\n')

    def _make_oses(self, workspace: str) -> Any:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        svc.workspace_root = workspace
        return svc

    def test_partial_occlusion_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_events(tmp, [
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_partial_occlusion'],
                }},
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_partial_occlusion'],
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._visual_metacognition_findings()
            cats = [f.category for f in findings]
            assert 'repeated_partial_occlusion' in cats

    def test_wrong_window_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_events(tmp, [
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_wrong_window'],
                }},
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_wrong_window'],
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._visual_metacognition_findings()
            cats = [f.category for f in findings]
            assert 'repeated_wrong_window_captured' in cats

    def test_resolution_too_low_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_events(tmp, [
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_resolution_too_low'],
                }},
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_resolution_too_low'],
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._visual_metacognition_findings()
            cats = [f.category for f in findings]
            assert 'repeated_resolution_too_low' in cats

    def test_single_event_no_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_events(tmp, [
                {'kind': 'visual_evidence_snapshot', 'data': {
                    'unresolved': ['UNRESOLVED:visual_capture_wrong_window'],
                }},
            ])
            svc = self._make_oses(tmp)
            findings = svc._visual_metacognition_findings()
            assert len(findings) == 0

    def test_no_crash_without_workspace(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        assert svc._visual_metacognition_findings() == []


# ---------------------------------------------------------------
# Central reasoning budget gate tests
# ---------------------------------------------------------------

class TestReasoningBudgetGate:
    """_should_defer_reasoning prevents back-to-back heavy inference."""

    def _make_vm(self) -> Any:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm = object.__new__(ControlCenterViewModel)
        vm._messages = []
        vm._live_status = 'idle'
        return vm

    def test_no_defer_without_pressure(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: False
        vm._last_heavy_inference_end_ts = time.time()
        vm._last_heavy_inference_elapsed_s = 20.0
        assert vm._should_defer_reasoning('hola') is False

    def test_no_defer_without_recent_heavy(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: True
        # No previous heavy inference recorded
        assert vm._should_defer_reasoning('hola') is False

    def test_no_defer_when_cooldown_expired(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: True
        vm._last_heavy_inference_end_ts = time.time() - 60.0
        vm._last_heavy_inference_elapsed_s = 20.0
        assert vm._should_defer_reasoning('hola') is False

    def test_no_defer_when_last_was_fast(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: True
        vm._last_heavy_inference_end_ts = time.time()
        vm._last_heavy_inference_elapsed_s = 3.0
        assert vm._should_defer_reasoning('hola') is False

    def test_defer_when_all_conditions_met(self) -> None:
        vm = self._make_vm()
        vm._should_defer_heavy_work = lambda: True
        vm._last_heavy_inference_end_ts = time.time() - 5.0
        vm._last_heavy_inference_elapsed_s = 20.0
        # Stub _append_message and _set_live_status
        messages: list[tuple[str, ...]] = []
        vm._append_message = lambda *a, **kw: messages.append(a)
        vm._set_live_status = lambda s: None
        result = vm._should_defer_reasoning('hola')
        assert result is True
        assert len(messages) == 1
        assert 'recuperandome' in messages[0][2]

    def test_record_heavy_inference_timing(self) -> None:
        vm = self._make_vm()
        before = time.time()
        vm._record_heavy_inference_timing(15.0)
        assert vm._last_heavy_inference_elapsed_s == 15.0
        assert vm._last_heavy_inference_end_ts >= before

    def test_reasoning_constants_exist(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert ControlCenterViewModel._REASONING_COOLDOWN_S == 30.0
        assert ControlCenterViewModel._REASONING_SLOW_THRESHOLD_S == 10.0


# ---------------------------------------------------------------
# Deep visual capture comparison tests
# ---------------------------------------------------------------

class TestCaptureComparison:
    """_compare_capture_similarity compares before/after capture metadata."""

    def _compare(self, before: dict | None, after: dict | None) -> dict:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        return ControlCenterViewModel._compare_capture_similarity(before, after)

    def test_identical_captures_high_similarity(self) -> None:
        meta = {'blank_probability': 0.1, 'dynamic_range': 200, 'unique_color_count': 5000}
        result = self._compare(meta, dict(meta))
        assert result['similarity_score'] > 0.99
        assert result['changed'] is False

    def test_black_to_content_is_changed(self) -> None:
        before = {'blank_probability': 0.98, 'dynamic_range': 0, 'unique_color_count': 1}
        after = {'blank_probability': 0.05, 'dynamic_range': 220, 'unique_color_count': 8000}
        result = self._compare(before, after)
        assert result['changed'] is True
        assert result['similarity_score'] < 0.5

    def test_none_before_returns_no_data(self) -> None:
        after = {'blank_probability': 0.1, 'dynamic_range': 200, 'unique_color_count': 5000}
        result = self._compare(None, after)
        assert result['changed'] is False
        assert result['detail'] == 'insufficient data for comparison'

    def test_none_after_returns_no_data(self) -> None:
        before = {'blank_probability': 0.1, 'dynamic_range': 200, 'unique_color_count': 5000}
        result = self._compare(before, None)
        assert result['changed'] is False

    def test_partial_metrics_still_work(self) -> None:
        before = {'blank_probability': 0.9}
        after = {'blank_probability': 0.1}
        result = self._compare(before, after)
        assert result['changed'] is True
        assert 'blank_probability_delta' in result['metrics']

    def test_similar_but_different_below_threshold(self) -> None:
        before = {'blank_probability': 0.10, 'dynamic_range': 200, 'unique_color_count': 5000}
        after = {'blank_probability': 0.12, 'dynamic_range': 195, 'unique_color_count': 4800}
        result = self._compare(before, after)
        assert result['changed'] is False
        assert result['similarity_score'] > 0.85


# ---------------------------------------------------------------
# OSES reasoning budget findings tests
# ---------------------------------------------------------------

class TestOSESReasoningBudgetFindings:
    """_reasoning_budget_findings detects deferrals and follow-up freezes."""

    def _make_oses(self, workspace: str) -> Any:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        svc.workspace_root = workspace
        return svc

    def _write_audit(self, tmp: str, events: list[dict]) -> None:
        logs = Path(tmp) / 'data' / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / 'runtime_audit.jsonl').open('w') as f:
            for ev in events:
                f.write(json.dumps(ev) + '\n')

    def test_deferral_below_threshold_no_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit(tmp, [
                {'kind': 'reasoning_budget_deferred'},
                {'kind': 'reasoning_budget_deferred'},
            ])
            svc = self._make_oses(tmp)
            findings = svc._reasoning_budget_findings()
            assert len(findings) == 0

    def test_deferral_at_threshold_produces_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit(tmp, [
                {'kind': 'reasoning_budget_deferred'},
                {'kind': 'reasoning_budget_deferred'},
                {'kind': 'reasoning_budget_deferred'},
            ])
            svc = self._make_oses(tmp)
            findings = svc._reasoning_budget_findings()
            cats = [f.category for f in findings]
            assert 'repeated_reasoning_budget_deferral' in cats

    def test_followup_freeze_pattern_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit(tmp, [
                {'kind': 'post_result_ui_update_coalesced'},
                {'kind': 'ui_event_loop_stall'},
                {'kind': 'post_result_ui_update_coalesced'},
                {'kind': 'ui_event_loop_stall'},
            ])
            svc = self._make_oses(tmp)
            findings = svc._reasoning_budget_findings()
            cats = [f.category for f in findings]
            assert 'followup_after_failure_freeze' in cats

    def test_heavy_without_stall_no_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_audit(tmp, [
                {'kind': 'post_result_ui_update_coalesced'},
                {'kind': 'some_other_event'},
                {'kind': 'post_result_ui_update_coalesced'},
                {'kind': 'some_other_event'},
            ])
            svc = self._make_oses(tmp)
            findings = svc._reasoning_budget_findings()
            cats = [f.category for f in findings]
            assert 'followup_after_failure_freeze' not in cats

    def test_no_crash_without_workspace(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        assert svc._reasoning_budget_findings() == []
