"""P0.32 — Governed User Chrome Bridge / External Session Selection.

Focused tests for:
- CDP availability probe (_detect_cdp_available)
- User Chrome bridge selection with explicit permission
- CDP permission revoke
- Session selection message building
- No PII leak in bridge events
- OSES finding: isolated_profile_blocks_user_logged_in_browser
- external_consultation does not fall back to local silently
- RuntimeAuditTracer bridge event tracing
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracer():
    """Fresh RuntimeAuditTracer for each test."""
    from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
    return RuntimeAuditTracer(log_dir=None)


@pytest.fixture()
def viewmodel_cls():
    """Import ControlCenterViewModel class without constructing it."""
    from iabv_v15.ui.viewmodels import control_center_viewmodel as mod
    return mod.ControlCenterViewModel


# ---------------------------------------------------------------------------
# 1. CDP probe — available
# ---------------------------------------------------------------------------

class TestCDPProbeAvailable:
    """User has Chrome running with --remote-debugging-port=9222."""

    def test_cdp_available_returns_true(self, viewmodel_cls):
        version_json = json.dumps({
            'Browser': 'Chrome/125.0.6422.60',
            'Protocol-Version': '1.3',
        }).encode()

        class FakeResp:
            def read(self):
                return version_json
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch('urllib.request.urlopen', return_value=FakeResp()):
            result = viewmodel_cls._detect_cdp_available(cdp_url='http://localhost:9222')

        assert result['available'] is True
        assert 'Chrome/125' in result['browser_version']
        assert result['error'] == ''


# ---------------------------------------------------------------------------
# 2. CDP probe — not available
# ---------------------------------------------------------------------------

class TestCDPProbeUnavailable:
    """Chrome not running with debugging port."""

    def test_cdp_unavailable_returns_false(self, viewmodel_cls):
        import urllib.error
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('Connection refused')):
            result = viewmodel_cls._detect_cdp_available(cdp_url='http://localhost:9222')

        assert result['available'] is False
        assert 'connection_failed' in result['error']
        assert result['browser_version'] == ''


# ---------------------------------------------------------------------------
# 3. Permission denied — user does not type bridge patterns
# ---------------------------------------------------------------------------

class TestPermissionDenied:
    """Messages that don't match bridge patterns should not activate CDP."""

    def test_non_matching_message_returns_false(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        vm._CHROME_BRIDGE_PATTERNS = viewmodel_cls._CHROME_BRIDGE_PATTERNS
        result = viewmodel_cls._try_handle_user_chrome_bridge_selection(vm, 'hola como estas')
        assert result is False

    def test_revoke_non_matching_returns_false(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        vm._CDP_REVOKE_PATTERNS = viewmodel_cls._CDP_REVOKE_PATTERNS
        result = viewmodel_cls._try_handle_cdp_permission_revoke(vm, 'quiero ver el estado')
        assert result is False


# ---------------------------------------------------------------------------
# 4. CDP unavailable — manual selection required
# ---------------------------------------------------------------------------

class TestManualSelectionRequired:
    """When user types 'usar mi chrome' but CDP is not available (P0.72).

    P0.72: must NOT instruct the user to run a terminal command. Instead it
    offers a governed Chrome window IABV opens itself (UNA SOLA VENTANA).
    """

    def test_cdp_unavailable_offers_governed_launch_no_command(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        vm._CHROME_BRIDGE_PATTERNS = viewmodel_cls._CHROME_BRIDGE_PATTERNS
        vm._verify_chrome_bridge_capability = MagicMock(return_value=True)
        vm._format_human_assist_message = viewmodel_cls._format_human_assist_message
        vm._GOVERNED_LAUNCH_OFFER = viewmodel_cls._GOVERNED_LAUNCH_OFFER
        vm._detect_cdp_available = MagicMock(return_value={
            'available': False,
            'cdp_url': 'http://localhost:9222',
            'browser_version': '',
            'error': 'connection_failed: Connection refused',
        })
        vm.dataChanged = MagicMock()

        result = viewmodel_cls._try_handle_user_chrome_bridge_selection(vm, 'usar mi chrome')

        assert result is True
        # UNA SOLA VENTANA: never a terminal command in the user response.
        assert '--remote-debugging-port' not in vm._latest_response_text
        assert 'chrome.exe' not in vm._latest_response_text.lower()
        # Offers a governed window instead.
        assert 'gobernada' in vm._latest_response_text.lower()
        assert 'IABV_PREFER_CDP_SESSION' not in os.environ or os.environ.get('IABV_PREFER_CDP_SESSION') != '1'


# ---------------------------------------------------------------------------
# 5. No PII leak in bridge events
# ---------------------------------------------------------------------------

class TestNoPIILeak:
    """Bridge events must not contain cookies, emails, tokens, or credentials."""

    def test_tracer_bridge_event_no_pii(self, tracer):
        ev = tracer.trace_user_browser_bridge(
            'permission_requested',
            assistant_kind='chatgpt',
            reason='user_requested_chrome_bridge',
        )
        data = ev.get('data', {})
        serialized = json.dumps(data)
        pii_markers = ['@', 'password', 'token', 'cookie', 'Bearer', 'session_id']
        for marker in pii_markers:
            assert marker not in serialized, f'PII marker {marker!r} found in event data'

    def test_session_selection_message_no_pii(self, viewmodel_cls):
        cdp_probe = {
            'available': True,
            'browser_version': 'Chrome/125.0',
            'error': '',
        }
        vm = MagicMock(spec=viewmodel_cls)
        msg = viewmodel_cls._build_session_selection_message(vm, 'ChatGPT', cdp_probe)
        # "cookies" and "tokens" appear as disclaimers ("No leere cookies ni tokens"),
        # NOT as actual credential values. Check for actual PII patterns instead.
        pii_markers = ['@gmail', 'password=', 'token=', 'Bearer ', 'session_id=']
        for marker in pii_markers:
            assert marker not in msg, f'PII marker {marker!r} found in session selection message'


# ---------------------------------------------------------------------------
# 6. External consultation does not fall back to local silently
# ---------------------------------------------------------------------------

class TestExternalConsultationNoSilentFallback:
    """When security verification blocks, message must mention the block explicitly."""

    def test_security_verification_mentions_isolated_profile(self, viewmodel_cls):
        cdp_probe = {
            'available': False,
            'cdp_url': 'http://localhost:9222',
            'browser_version': '',
            'error': 'connection_failed',
        }
        vm = MagicMock(spec=viewmodel_cls)
        msg = viewmodel_cls._build_session_selection_message(
            vm, 'ChatGPT', cdp_probe,
        )
        assert 'perfil aislado' in msg.lower()
        assert 'chatgpt_program_session' in msg


# ---------------------------------------------------------------------------
# 7. OSES finding: isolated_profile_blocks_user_logged_in_browser
# ---------------------------------------------------------------------------

class TestOSESIsolatedProfileFinding:
    """OSES should detect repeated isolated profile blocks >= 2."""

    def test_finding_generated_when_blocks_ge_2(self, tmp_path):
        audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit_path.parent.mkdir(parents=True)
        lines = []
        for i in range(3):
            lines.append(json.dumps({
                'kind': 'assistant_profile_context_reported',
                'data': {
                    'block_type': 'browser_security_verification',
                    'assistant_title': 'ChatGPT',
                },
            }))
        audit_path.write_text('\n'.join(lines), encoding='utf-8')

        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._isolated_profile_block_findings(svc)
        assert len(findings) == 1
        assert findings[0].category == 'isolated_profile_blocks_user_logged_in_browser'
        assert findings[0].metadata['block_count'] == 3

    def test_no_finding_when_blocks_lt_2(self, tmp_path):
        audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit_path.parent.mkdir(parents=True)
        audit_path.write_text(json.dumps({
            'kind': 'assistant_profile_context_reported',
            'data': {'block_type': 'browser_security_verification'},
        }), encoding='utf-8')

        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._isolated_profile_block_findings(svc)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# 8. RuntimeAuditTracer bridge event tracing
# ---------------------------------------------------------------------------

class TestTracerBridgeEvents:
    """Verify that trace_user_browser_bridge emits correctly typed events."""

    def test_permission_requested_event(self, tracer):
        ev = tracer.trace_user_browser_bridge(
            'permission_requested',
            assistant_kind='chatgpt',
            reason='user_requested_chrome_bridge',
        )
        assert ev['kind'] == 'user_browser_bridge_permission_requested'
        assert ev['data']['assistant_kind'] == 'chatgpt'

    def test_session_selected_event(self, tracer):
        ev = tracer.trace_user_browser_bridge(
            'session_selected',
            assistant_kind='chatgpt',
            cdp_available=True,
            session_selected='user_chrome_cdp',
            reason='user_explicit_permission',
        )
        assert ev['kind'] == 'user_browser_bridge_session_selected'
        assert ev['data']['session_selected'] == 'user_chrome_cdp'
        assert ev['data']['cdp_available'] is True

    def test_bridge_result_cdp_unavailable(self, tracer):
        ev = tracer.trace_user_browser_bridge(
            'bridge_result',
            assistant_kind='chatgpt',
            cdp_available=False,
            session_selected='none',
            reason='cdp_unavailable',
        )
        assert ev['kind'] == 'user_browser_bridge_bridge_result'
        assert ev['data']['cdp_available'] is False

    def test_permission_denied_event(self, tracer):
        ev = tracer.trace_user_browser_bridge(
            'permission_denied',
            assistant_kind='chatgpt',
            session_selected='isolated_profile',
            reason='user_revoked_cdp_permission',
        )
        assert ev['kind'] == 'user_browser_bridge_permission_denied'
        assert ev['data']['session_selected'] == 'isolated_profile'


# ---------------------------------------------------------------------------
# 9. Session selection message with CDP available
# ---------------------------------------------------------------------------

class TestSessionSelectionMessageCDPAvailable:
    """When CDP is available, message should offer 3 options including user Chrome."""

    def test_message_includes_user_chrome_option(self, viewmodel_cls):
        cdp_probe = {
            'available': True,
            'browser_version': 'Chrome/125.0',
            'error': '',
        }
        vm = MagicMock(spec=viewmodel_cls)
        msg = viewmodel_cls._build_session_selection_message(vm, 'ChatGPT', cdp_probe)
        assert 'usar mi chrome' in msg.lower()
        assert 'Chrome/125.0' in msg
        assert 'Pegado manual' in msg


# ---------------------------------------------------------------------------
# 10. Platform pending validates
# ---------------------------------------------------------------------------

class TestPlatformPendingP032:
    """P0.32 platform_pending JSON must validate with PlatformPendingTask."""

    def test_p032_json_validates(self):
        from iabv_v15.domain.models import PlatformPendingTask
        p = Path(__file__).resolve().parent.parent / 'IABV_v1.5' / 'data' / 'evolution' / 'platform_pending'
        found = False
        for candidate in [
            p / 'task_runtime_governed_user_chrome_bridge_p032.json',
            Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_governed_user_chrome_bridge_p032.json',
        ]:
            if candidate.exists():
                raw = candidate.read_text(encoding='utf-8')
                PlatformPendingTask.model_validate_json(raw)
                found = True
                break
        if not found:
            # Try relative to workspace
            ws = Path(os.environ.get('IABV_WORKSPACE', ''))
            if ws.is_dir():
                pp = ws / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_governed_user_chrome_bridge_p032.json'
                if pp.exists():
                    raw = pp.read_text(encoding='utf-8')
                    PlatformPendingTask.model_validate_json(raw)
                    found = True
            if not found:
                pytest.skip('P0.32 platform_pending file not found in expected locations')
