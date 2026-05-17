"""P0.32 focused tests: Governed User Chrome Bridge / External Session Selection.

Tests cover:
- CDP availability detection
- Session selection message construction (CDP available vs not)
- User grants CDP permission ("usar mi chrome") when CDP is available
- User grants CDP permission but CDP is unavailable
- Permission denied (no recent failure context)
- CDP permission revocation
- No credential leak in any path
- OSES finding for repeated isolated_profile_blocks
- RuntimeAuditTracer bridge traces
- external_consultation does not fall to local when bridge is offered

All tests use lightweight stubs (no AppBootstrap).
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import types
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from iabv_v15.domain import models as _models


# ── Lightweight stub ────────────────────────────────────────────

def _make_stub_vm(workspace: str | Path | None = None):
    """Return a lightweight namespace with relevant methods bound."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
    from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver

    config = SimpleNamespace(
        workspace_root=str(workspace or ''),
        browser_profiles_dir='',
    )
    stub = SimpleNamespace(
        config=config,
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
        _last_external_failure_payload={},
        _last_external_failure_ts=0.0,
        _live_status='idle',
        _last_user_goal='test prompt for ChatGPT',
        _assistant_preference_resolver=AssistantPreferenceResolver(),
    )

    for attr_name in dir(ControlCenterViewModel):
        if attr_name.startswith('__'):
            continue
        val = getattr(ControlCenterViewModel, attr_name, None)
        if isinstance(val, (tuple, int, float, str, frozenset)):
            if not hasattr(stub, attr_name):
                setattr(stub, attr_name, val)

    for name in (
        '_detect_cdp_available',
        '_build_session_selection_message',
        '_try_handle_user_chrome_bridge_selection',
        '_try_handle_cdp_permission_revoke',
        '_human_external_consultation_failure',
        '_try_handle_external_failure_followup',
        '_explicit_assistant_preference',
        '_try_handle_structured_self_audit',
        '_external_state_notice',
        '_remember_external_failure',
        '_clear_external_failure_memory',
        '_humanize_task_failure',
        '_assistant_display_name',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is not None:
            stub.__dict__[name] = types.MethodType(method, stub)

    stub._append_message = MagicMock()
    stub._set_live_status = MagicMock()
    stub._clear_autonomy_activity_override = MagicMock()
    stub._copy_text = MagicMock()
    stub.dataChanged = MagicMock()
    stub.dataChanged.emit = MagicMock()

    return stub


def _security_verification_failure_payload():
    """Return a payload simulating a browser_security_verification block."""
    return {
        'success': False,
        'terminal_state': 'blocked_by_security_verification',
        'assistant_kind': 'chatgpt',
        'metadata': {
            'external_consultation': {
                'status': 'blocked_by_security_verification',
                'assistant_kind': 'chatgpt',
            },
        },
    }


# ── CDP Detection ──────────────────────────────────────────────

class TestCDPDetection:
    """Verify CDP availability detection is safe and correct."""

    def test_cdp_not_available_when_no_server(self) -> None:
        with patch.dict(os.environ, {'IABV_SHARED_CDP_URL': 'http://localhost:19999'}):
            assert not _make_stub_vm()._detect_cdp_available()

    def test_cdp_available_with_mock_server(self) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"Browser": "Chrome/120", "webSocketDebuggerUrl": "ws://..."}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_resp):
            assert _make_stub_vm()._detect_cdp_available()

    def test_cdp_detection_never_reads_page_content(self) -> None:
        """CDP probe only hits /json/version, not page content."""
        import urllib.request
        calls = []

        def tracking_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else str(req)
            calls.append(url)
            raise ConnectionRefusedError('test')

        with patch.object(urllib.request, 'urlopen', tracking_urlopen):
            _make_stub_vm()._detect_cdp_available()

        for url in calls:
            assert '/json/version' in url
            assert 'cookies' not in url.lower()
            assert 'token' not in url.lower()


# ── Session Selection Message ──────────────────────────────────

class TestSessionSelectionMessage:
    """Verify the governed selection message is correct."""

    def test_message_with_cdp_available(self) -> None:
        result = _make_stub_vm()._build_session_selection_message(
            'ChatGPT', cdp_available=True,
        )
        msg = result['message']
        assert 'chatgpt_program_session/browser_profile' in msg
        assert 'usar mi chrome' in msg
        assert 'Pegar manualmente' in msg
        assert result['bridge_status'] == 'cdp_available_permission_pending'

    def test_message_without_cdp(self) -> None:
        result = _make_stub_vm()._build_session_selection_message(
            'ChatGPT', cdp_available=False,
        )
        msg = result['message']
        assert 'chatgpt_program_session/browser_profile' in msg
        assert 'usar mi chrome' not in msg
        assert '--remote-debugging-port' in msg
        assert result['bridge_status'] == 'cdp_not_available'

    def test_message_does_not_contain_credential_values(self) -> None:
        """The message may mention 'cookies' conceptually but must not leak actual values."""
        result = _make_stub_vm()._build_session_selection_message(
            'ChatGPT', cdp_available=True,
        )
        msg = result['message'].lower()
        assert 'password' not in msg
        assert 'email' not in msg
        # Must not contain any base64/hex-like credential strings
        assert '=' * 10 not in msg
        assert '0x' not in msg


# ── Bridge Selection Handler ───────────────────────────────────

class TestUserChromeBridgeSelection:
    """Verify the bridge selection handler."""

    def _make_vm_with_cdp(self, cdp_available: bool):
        vm = _make_stub_vm()
        vm._last_external_failure_payload = _security_verification_failure_payload()
        vm._last_external_failure_ts = 1000.0
        vm._detect_cdp_available = lambda: cdp_available
        return vm

    def test_grant_permission_cdp_available(self) -> None:
        vm = self._make_vm_with_cdp(cdp_available=True)
        result = vm._try_handle_user_chrome_bridge_selection('usar mi chrome')

        assert result is True
        assert os.environ.get('IABV_PREFER_CDP_SESSION') == '1'
        assert 'Permiso concedido' in vm._latest_response_text
        assert 'revocar permiso cdp' in vm._latest_response_text.lower()
        vm._append_message.assert_called()
        os.environ.pop('IABV_PREFER_CDP_SESSION', None)

    def test_grant_permission_cdp_not_available(self) -> None:
        vm = self._make_vm_with_cdp(cdp_available=False)
        result = vm._try_handle_user_chrome_bridge_selection('usar mi chrome')

        assert result is True
        assert os.environ.get('IABV_PREFER_CDP_SESSION') != '1'
        assert 'CDP no esta disponible' in vm._latest_response_text
        assert vm._working is False

    def test_permission_denied_no_recent_failure(self) -> None:
        vm = _make_stub_vm()
        vm._last_external_failure_payload = {}
        result = vm._try_handle_user_chrome_bridge_selection('usar mi chrome')
        assert result is False

    def test_unrelated_message_not_captured(self) -> None:
        vm = _make_stub_vm()
        vm._last_external_failure_payload = _security_verification_failure_payload()
        result = vm._try_handle_user_chrome_bridge_selection('hola que tal')
        assert result is False

    def test_bridge_selection_does_not_leak_credential_values(self) -> None:
        """Response may mention 'cookies' conceptually but must not leak values."""
        vm = self._make_vm_with_cdp(cdp_available=True)
        vm._try_handle_user_chrome_bridge_selection('usar mi chrome')

        response = vm._latest_response_text.lower()
        assert 'password' not in response
        assert 'email' not in response
        assert '=' * 10 not in response
        os.environ.pop('IABV_PREFER_CDP_SESSION', None)

    def test_english_pattern_works(self) -> None:
        vm = self._make_vm_with_cdp(cdp_available=True)
        result = vm._try_handle_user_chrome_bridge_selection('use my chrome')
        assert result is True
        os.environ.pop('IABV_PREFER_CDP_SESSION', None)

    def test_external_consultation_does_not_fall_to_local(self) -> None:
        """When bridge is offered, no local fallback should be triggered."""
        vm = self._make_vm_with_cdp(cdp_available=True)
        vm._try_handle_user_chrome_bridge_selection('usar mi chrome')
        response = vm._latest_response_text.lower()
        assert 'via local' not in response
        assert 'sigo con lo que ya tenemos' not in response
        os.environ.pop('IABV_PREFER_CDP_SESSION', None)


# ── CDP Permission Revoke ──────────────────────────────────────

class TestCDPPermissionRevoke:
    """Verify CDP permission revocation."""

    def test_revoke_clears_env_var(self) -> None:
        os.environ['IABV_PREFER_CDP_SESSION'] = '1'
        vm = _make_stub_vm()

        result = vm._try_handle_cdp_permission_revoke('revocar permiso cdp')

        assert result is True
        assert 'IABV_PREFER_CDP_SESSION' not in os.environ
        assert 'revocado' in vm._latest_response_text.lower()

    def test_unrelated_message_not_captured(self) -> None:
        vm = _make_stub_vm()
        result = vm._try_handle_cdp_permission_revoke('hola que tal')
        assert result is False


# ── External Consultation Failure Handoff ──────────────────────

class TestExternalConsultationFailureHandoff:
    """Verify the security_verification branch offers session selection."""

    def _make_vm_with_cdp(self, cdp_available: bool):
        vm = _make_stub_vm()
        vm._detect_cdp_available = lambda: cdp_available
        return vm

    def test_security_verification_offers_session_selection(self) -> None:
        vm = self._make_vm_with_cdp(cdp_available=False)
        msg, meta, busy = vm._human_external_consultation_failure(
            'ChatGPT', 'browser_security_verification detected',
        )
        assert 'chatgpt_program_session/browser_profile' in msg
        assert 'Opciones disponibles' in msg
        assert 'blocked_by_security_verification' in meta

    def test_security_verification_with_cdp_offers_bridge(self) -> None:
        vm = self._make_vm_with_cdp(cdp_available=True)
        msg, meta, busy = vm._human_external_consultation_failure(
            'ChatGPT', 'browser_security_verification',
        )
        assert 'usar mi chrome' in msg
        assert 'CDP' in msg

    def test_security_verification_does_not_fall_to_local(self) -> None:
        vm = self._make_vm_with_cdp(cdp_available=False)
        msg, meta, busy = vm._human_external_consultation_failure(
            'ChatGPT', 'browser_security_verification',
        )
        assert 'no necesariamente tu Chrome normal' in msg
        assert meta == 'ChatGPT: blocked_by_security_verification'


# ── OSES Finding ───────────────────────────────────────────────

class TestOSESIsolatedProfileBlockFinding:
    """Verify OSES detects repeated isolated_profile_blocks pattern."""

    def setup_method(self) -> None:
        self.workspace = Path(f'/tmp/test_p032_oses_{uuid4().hex[:8]}')
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / 'data' / 'logs').mkdir(parents=True, exist_ok=True)

    def teardown_method(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _write_audit_events(self, events: list[dict]) -> None:
        audit_path = self.workspace / 'data' / 'logs' / 'runtime_audit.jsonl'
        with audit_path.open('w', encoding='utf-8') as f:
            for evt in events:
                f.write(json.dumps(evt) + '\n')

    def _make_oses_stub(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        stub = SimpleNamespace(workspace_root=str(self.workspace))
        stub._isolated_profile_block_findings = types.MethodType(
            OperationalSelfExaminationService._isolated_profile_block_findings, stub,
        )
        return stub

    def test_no_finding_with_zero_blocks(self) -> None:
        self._write_audit_events([])
        oses = self._make_oses_stub()
        findings = oses._isolated_profile_block_findings()
        assert len(findings) == 0

    def test_no_finding_with_single_block(self) -> None:
        self._write_audit_events([
            {'kind': 'assistant_profile_context_reported', 'data': {}},
        ])
        oses = self._make_oses_stub()
        findings = oses._isolated_profile_block_findings()
        assert len(findings) == 0

    def test_finding_with_repeated_blocks(self) -> None:
        self._write_audit_events([
            {'kind': 'assistant_profile_context_reported', 'data': {}},
            {'kind': 'assistant_profile_context_reported', 'data': {}},
            {'kind': 'assistant_profile_context_reported', 'data': {}},
        ])
        oses = self._make_oses_stub()
        findings = oses._isolated_profile_block_findings()
        assert len(findings) == 1
        assert findings[0].category == 'isolated_profile_blocks_user_logged_in_browser'
        assert findings[0].metadata['profile_block_count'] == 3

    def test_finding_counts_denied_bridges(self) -> None:
        self._write_audit_events([
            {'kind': 'assistant_profile_context_reported', 'data': {}},
            {'kind': 'assistant_profile_context_reported', 'data': {}},
            {'kind': 'user_browser_bridge_result', 'data': {'permission_granted': False}},
        ])
        oses = self._make_oses_stub()
        findings = oses._isolated_profile_block_findings()
        assert len(findings) == 1
        assert findings[0].metadata['bridge_denied_count'] == 1


# ── RuntimeAuditTracer Bridge Traces ───────────────────────────

class TestRuntimeAuditTracerBridgeTraces:
    """Verify new trace_user_browser_bridge method."""

    def setup_method(self) -> None:
        self.workspace = Path(f'/tmp/test_p032_tracer_{uuid4().hex[:8]}')
        log_dir = self.workspace / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        self.tracer = RuntimeAuditTracer(log_dir=str(log_dir))

    def teardown_method(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_permission_requested_event(self) -> None:
        evt = self.tracer.trace_user_browser_bridge(
            'permission_requested',
            assistant_kind='chatgpt',
            cdp_available=True,
            block_type='browser_security_verification',
        )
        assert evt['kind'] == 'user_browser_bridge_permission_requested'
        assert evt['data']['assistant_kind'] == 'chatgpt'
        assert evt['data']['cdp_available'] is True

    def test_result_event(self) -> None:
        evt = self.tracer.trace_user_browser_bridge(
            'result',
            assistant_kind='chatgpt',
            session_type='user_chrome_normal',
            cdp_available=True,
            permission_granted=True,
            selected_session='user_chrome_cdp',
        )
        assert evt['kind'] == 'user_browser_bridge_result'
        assert evt['data']['permission_granted'] is True
        assert evt['data']['selected_session'] == 'user_chrome_cdp'

    def test_session_selected_event(self) -> None:
        evt = self.tracer.trace_user_browser_bridge(
            'session_selected',
            assistant_kind='chatgpt',
            selected_session='isolated_profile',
        )
        assert evt['kind'] == 'user_browser_bridge_session_selected'
        assert evt['data']['selected_session'] == 'isolated_profile'


# ── Platform Pending Validation ────────────────────────────────

class TestPlatformPendingP032:
    """Validate platform_pending JSON conforms to PlatformPendingTask model."""

    def test_task_json_validates(self) -> None:
        task_path = Path(__file__).resolve().parent.parent / (
            'data/evolution/platform_pending/task_governed_user_chrome_bridge_p032.json'
        )
        assert task_path.exists(), f'Missing: {task_path}'
        raw = task_path.read_text(encoding='utf-8')
        task = _models.PlatformPendingTask.model_validate_json(raw)
        assert task.id == 'governed_user_chrome_bridge_p032'
        assert task.status == _models.PendingTaskStatus.READY_FOR_NEXT_SLICE
        assert task.metadata.get('covered_by_pr') == 'pending'
