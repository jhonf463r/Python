"""P0.27 tests: Governed Local Fallback + External Failure Follow-up Continuity.

Live evidence: after external_consultation was blocked by
browser_security_verification, the follow-up message 'pueddes solucionar eso'
fell to Adaptive local orchestrator (~56s) instead of being handled as
external_failure_followup.  These tests verify that:
1. Deictic follow-ups are captured by the external failure handler.
2. User-browser handoff patterns are recognised.
3. Messages without recent external failure are NOT falsely captured.
4. Explicit ChatGPT requests never return local success when external blocked.
5. RuntimeAuditTracer receives the correct traces.
6. OSES generates finding only with >=2 events.
7. Platform pending JSON validates.
"""
from __future__ import annotations

import json
import time
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


# ── helpers ──────────────────────────────────────────────────────────────

def _followup_stub() -> SimpleNamespace:
    """Minimal stub that satisfies _try_handle_external_failure_followup."""
    messages: list[tuple] = []
    stub = SimpleNamespace(
        _last_external_failure_payload={},
        _last_external_failure_ts=0.0,
        _latest_response_text='',
        _latest_response_meta='',
        _busy_label='',
        _working=True,
        _live_status='processing',
        _autonomy_activity_override={'active': True},
        _active_interaction_id='chat-test-001',
        _last_user_goal='has una consulta a chatgpt',
        _EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S=ControlCenterViewModel._EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S,
        _EXTERNAL_FAILURE_FOLLOWUP_PATTERNS=ControlCenterViewModel._EXTERNAL_FAILURE_FOLLOWUP_PATTERNS,
        _EXTERNAL_FAILURE_DEICTIC_TOKENS=ControlCenterViewModel._EXTERNAL_FAILURE_DEICTIC_TOKENS,
        _USER_BROWSER_HANDOFF_PATTERNS=ControlCenterViewModel._USER_BROWSER_HANDOFF_PATTERNS,
        _append_message=lambda *args, **kwargs: messages.append((args, kwargs)),
        _set_live_status=lambda value: setattr(stub, '_live_status', value),
        _clear_autonomy_activity_override=lambda: setattr(stub, '_autonomy_activity_override', {}),
        dataChanged=SimpleNamespace(emit=MagicMock()),
        _messages=messages,
    )
    # Bind methods needed by _try_handle_external_failure_followup
    from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver
    stub._assistant_preference_resolver = AssistantPreferenceResolver()
    for method_name in (
        '_try_handle_external_failure_followup',
        '_remember_external_failure',
        '_explicit_assistant_preference',
        '_human_external_consultation_failure',
        '_external_state_notice',
        '_clear_external_failure_memory',
        '_assistant_display_name',
        '_detect_cdp_available',
        '_build_session_selection_message',
    ):
        method = getattr(ControlCenterViewModel, method_name, None)
        if method is not None:
            stub.__dict__[method_name] = types.MethodType(method, stub)
    return stub


def _stub_with_security_failure() -> SimpleNamespace:
    """Stub pre-loaded with a browser_security_verification failure."""
    stub = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        stub,
        assistant_title='ChatGPT',
        message='No pude completar la consulta: browser_security_verification',
        meta='blocked_by_security_verification',
        outcome='blocked',
        success=False,
        assistant_kind='chatgpt',
        terminal_state='blocked_by_security_verification',
        dispatch_id='abc123def456',
    )
    return stub


def _stub_with_timeout_failure() -> SimpleNamespace:
    """Stub pre-loaded with an external timeout failure."""
    stub = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        stub,
        assistant_title='ChatGPT',
        message='ChatGPT web asistido: timeout after 60s',
        meta='timeout',
        outcome='timeout',
        success=False,
        assistant_kind='chatgpt',
        terminal_state='timeout',
        dispatch_id='timeout789abc',
    )
    return stub


# ── Test 1: deictic after security verification ─────────────────────────

def test_deictic_followup_after_security_block_uses_external_failure_path() -> None:
    """'pueddes solucionar eso' after blocked_by_security_verification
    must use external_failure_followup, NOT local chat."""
    stub = _stub_with_security_failure()

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        stub, 'pueddes solucionar eso',
    )

    assert handled is True
    assert stub._working is False
    assert stub._live_status == 'idle'
    assert 'ChatGPT' in stub._latest_response_text
    assert 'external_failure_followup' in stub._latest_response_meta
    assert stub.dataChanged.emit.called


# ── Test 2: deictic after timeout ────────────────────────────────────────

def test_deictic_followup_after_timeout_uses_external_failure_path() -> None:
    """'soluciona eso' after external timeout must use
    external_failure_followup, NOT local chat."""
    stub = _stub_with_timeout_failure()

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        stub, 'soluciona eso',
    )

    assert handled is True
    assert stub._working is False
    assert stub._live_status == 'idle'
    assert 'timeout' in stub._latest_response_text
    assert 'external_failure_followup' in stub._latest_response_meta


# ── Test 3: user browser handoff ─────────────────────────────────────────

def test_user_browser_handoff_when_user_sees_chatgpt() -> None:
    """'yo veo bien la ventana con chatgpt' must activate
    user_browser_manual_handoff, not local chat."""
    stub = _stub_with_security_failure()
    # _handle_user_browser_manual_handoff calls _copy_text — stub it.
    stub._copy_text = MagicMock()
    # Bind the class method so the stub can call it on itself.
    import types
    stub._handle_user_browser_manual_handoff = types.MethodType(
        ControlCenterViewModel._handle_user_browser_manual_handoff, stub,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        stub, 'yo veo bien la ventana con chatgpt',
    )

    assert handled is True
    assert stub._working is False
    assert stub._live_status == 'idle'
    assert 'user_browser_manual_handoff' in stub._latest_response_meta
    assert 'CDP' in stub._latest_response_text or 'comprobar' in stub._latest_response_text


# ── Test 4: no false capture without recent failure ──────────────────────

def test_no_false_capture_without_recent_external_failure() -> None:
    """Message without a recent external failure must NOT be captured."""
    stub = _followup_stub()  # no failure recorded

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        stub, 'pueddes solucionar eso',
    )

    assert handled is False
    assert stub._messages == []
    assert stub._live_status == 'processing'  # unchanged


# ── Test 5: explicit ChatGPT request never returns local success ─────────

def test_explicit_chatgpt_request_blocked_never_local_success() -> None:
    """When external is blocked, the failure payload stored via
    _remember_external_failure must have success=False and blocked outcome.
    An explicit ChatGPT request that is blocked must never pretend it
    succeeded locally."""
    stub = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        stub,
        assistant_title='ChatGPT',
        message='Ruta bloqueada para ChatGPT.',
        meta='blocked_by_security_verification',
        outcome='blocked',
        success=False,
        assistant_kind='chatgpt',
        terminal_state='blocked_by_security_verification',
        dispatch_id='block789',
    )

    payload = stub._last_external_failure_payload
    assert payload.get('success') is False
    assert payload.get('outcome') == 'blocked'
    assert payload.get('assistant_kind') == 'chatgpt'
    assert payload.get('terminal_state') == 'blocked_by_security_verification'
    # The deictic follow-up must be handled, NOT fall to local.
    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        stub, 'puedes solucionar eso',
    )
    assert handled is True
    # Response must NOT claim ChatGPT was consulted successfully.
    assert 'fallo' in stub._latest_response_text.lower() or 'bloque' in stub._latest_response_text.lower() or 'blocked' in stub._latest_response_meta.lower()


# ── Test 6: RuntimeAuditTracer receives suppression trace ────────────────

def test_tracer_receives_local_fallback_suppressed_trace() -> None:
    """RuntimeAuditTracer must receive
    local_fallback_suppressed_for_external_failure when a deictic followup
    is handled."""
    stub = _stub_with_security_failure()
    trace_calls: list[tuple] = []

    mock_tracer = SimpleNamespace(
        trace=lambda kind, **kw: trace_calls.append((kind, kw)),
    )

    with patch(
        'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        return_value=mock_tracer,
    ):
        handled = ControlCenterViewModel._try_handle_external_failure_followup(
            stub, 'arregla eso',
        )

    assert handled is True
    kinds = [c[0] for c in trace_calls]
    assert 'local_fallback_suppressed_for_external_failure' in kinds

    suppressed = next(c for c in trace_calls if c[0] == 'local_fallback_suppressed_for_external_failure')
    data = suppressed[1]
    assert data.get('previous_assistant_kind') == 'chatgpt'
    assert data.get('previous_terminal_state') == 'blocked_by_security_verification'
    assert 'arregla eso' in data.get('user_message_excerpt', '')
    assert data.get('dispatch_id') == 'abc123def456'


# ── Test 7: OSES generates finding only with >=2 events ──────────────────

def test_oses_finding_only_with_two_or_more_misroute_events() -> None:
    """OSES _external_failure_followup_misrouted_findings must generate a
    finding ONLY when there are >=2 misroute events (external blocked →
    local chat)."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )
    from iabv_v15.domain.models import SelfExaminationFinding

    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        logs_dir = Path(tmpdir) / 'data' / 'logs'
        logs_dir.mkdir(parents=True)
        audit_path = logs_dir / 'runtime_audit.jsonl'

        # Write 1 pair → should NOT generate finding
        events_one = [
            {'kind': 'dispatch_terminal', 'data': {
                'task_name': 'external_consultation',
                'terminal_state': 'blocked_by_security_verification',
                'dispatch_id': 'ext001',
            }},
            {'kind': 'dispatch_started', 'data': {
                'task_name': 'chat',
                'dispatch_id': 'local001',
            }},
        ]
        audit_path.write_text('\n'.join(json.dumps(e) for e in events_one))

        svc = SimpleNamespace(workspace_root=tmpdir)
        findings_one = OperationalSelfExaminationService._external_failure_followup_misrouted_findings(svc)
        assert len(findings_one) == 0

        # Write 2 pairs → should generate finding
        events_two = events_one + [
            {'kind': 'dispatch_terminal', 'data': {
                'task_name': 'external_consultation',
                'terminal_state': 'blocked_by_resource_pressure',
                'dispatch_id': 'ext002',
            }},
            {'kind': 'dispatch_started', 'data': {
                'task_name': 'chat',
                'dispatch_id': 'local002',
            }},
        ]
        audit_path.write_text('\n'.join(json.dumps(e) for e in events_two))

        findings_two = OperationalSelfExaminationService._external_failure_followup_misrouted_findings(svc)
        assert len(findings_two) == 1
        finding = findings_two[0]
        assert finding.category == 'external_failure_followup_misrouted_to_local'
        assert finding.metadata['count'] == 2


# ── Test 8: platform pending JSON validates ──────────────────────────────

def test_platform_pending_p027_json_validates() -> None:
    """Platform pending JSON must validate with PlatformPendingTask."""
    from iabv_v15.domain.models import PlatformPendingTask

    json_path = (
        Path(__file__).resolve().parent.parent
        / 'data' / 'evolution' / 'platform_pending'
        / 'task_runtime_external_failure_followup_governance_p027.json'
    )
    assert json_path.exists(), f'Missing {json_path}'
    raw = json_path.read_text(encoding='utf-8')
    task = PlatformPendingTask.model_validate_json(raw)
    assert task.id == 'runtime_external_failure_followup_governance_p027'
    assert task.status == 'PENDING'
    assert 'P0.27' in task.title
