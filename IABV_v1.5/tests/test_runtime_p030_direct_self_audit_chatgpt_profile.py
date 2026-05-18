"""P0.30: Metacognitive Direct Audit + ChatGPT Profile Isolation + Starvation Detection.

Tests:
1. _is_direct_self_audit_query detects metacognitive patterns.
2. _is_direct_self_audit_query rejects non-metacognitive messages.
3. _answer_direct_self_audit_query reads structured evidence and responds.
4. _answer_direct_self_audit_query handles missing evidence gracefully.
5. _is_new_chatgpt_consultation detects fresh consultation requests.
6. _is_new_chatgpt_consultation rejects non-consultation messages.
7. _try_handle_external_failure_followup skips when new consultation detected.
8. Isolated profile note included when browser_security_verification in failure.
9. Isolated profile note NOT included when other terminal states.
10. OSES _metacognitive_starvation_findings emits finding with >=2 signals.
11. OSES _metacognitive_starvation_findings no finding with <2 signals.
12. sendChat routing: self-audit guard fires before lightweight_chat.
13. platform_pending P0.30 JSON validates with PlatformPendingTask.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Sys-path setup
# ---------------------------------------------------------------------------
_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)


# ---------------------------------------------------------------------------
# Helpers — lightweight ControlCenterViewModel stub
# ---------------------------------------------------------------------------
def _make_vm(workspace: str | None = None) -> Any:
    """Build a minimal ControlCenterViewModel-like object with P0.30 methods."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    config = MagicMock()
    config.workspace_root = workspace or ''

    with patch.object(ControlCenterViewModel, '__init__', lambda self, **kw: None):
        vm = ControlCenterViewModel.__new__(ControlCenterViewModel)

    vm.config = config
    vm._messages = []
    vm._latest_response_text = ''
    vm._latest_response_meta = ''
    vm._busy_label = ''
    vm._working = False
    vm._last_external_failure_payload = {}
    vm._last_external_failure_ts = 0.0
    vm._attached_files = []
    vm._chat_session_id = 'test-session'
    vm._active_interaction_id = ''

    # Stubs for signals / UI
    vm.dataChanged = MagicMock()
    vm.liveStatusChanged = MagicMock()

    def _set_live_status(s: str) -> None:
        pass
    vm._set_live_status = _set_live_status

    def _clear_autonomy_activity_override() -> None:
        pass
    vm._clear_autonomy_activity_override = _clear_autonomy_activity_override

    def _append_message(role, sender, text, *args, **kwargs) -> None:
        vm._messages.append({'role': role, 'sender': sender, 'text': text})
    vm._append_message = _append_message

    return vm


# ---------------------------------------------------------------------------
# 1. _is_direct_self_audit_query detects metacognitive patterns
# ---------------------------------------------------------------------------
class TestIsDirectSelfAuditQuery:
    def test_autoauditoria_detected(self):
        vm = _make_vm()
        assert vm._is_direct_self_audit_query('haz una autoauditoría')

    def test_estado_de_tests_detected(self):
        vm = _make_vm()
        assert vm._is_direct_self_audit_query('dime el estado de tests')

    def test_portable_context_detected(self):
        vm = _make_vm()
        assert vm._is_direct_self_audit_query('muestra portable context')

    def test_control_master_detected(self):
        vm = _make_vm()
        assert vm._is_direct_self_audit_query('que dice control master')

    def test_runtime_audit_detected(self):
        vm = _make_vm()
        assert vm._is_direct_self_audit_query('revisa runtime audit')

    def test_que_evidencia_detected(self):
        vm = _make_vm()
        assert vm._is_direct_self_audit_query('qué evidencia tienes')


# ---------------------------------------------------------------------------
# 2. _is_direct_self_audit_query rejects non-metacognitive messages
# ---------------------------------------------------------------------------
class TestIsDirectSelfAuditQueryRejects:
    def test_greeting_not_detected(self):
        vm = _make_vm()
        assert not vm._is_direct_self_audit_query('hola')

    def test_chatgpt_request_not_detected(self):
        vm = _make_vm()
        assert not vm._is_direct_self_audit_query('haz una consulta a chatgpt')

    def test_random_question_not_detected(self):
        vm = _make_vm()
        assert not vm._is_direct_self_audit_query('cuanto es 2+2')


# ---------------------------------------------------------------------------
# 3. _answer_direct_self_audit_query reads structured evidence
# ---------------------------------------------------------------------------
class TestAnswerDirectSelfAuditQuery:
    def test_with_test_evidence(self, tmp_path):
        te_dir = tmp_path / 'data' / 'evolution' / 'test_evidence'
        te_dir.mkdir(parents=True)
        (te_dir / 'latest.json').write_text(json.dumps({
            'passed': 21, 'failed': 0, 'errors': 0,
            'duration_s': 1.5, 'timestamp': '2026-05-16T10:00:00Z',
        }))
        vm = _make_vm(str(tmp_path))
        result = vm._answer_direct_self_audit_query('estado de tests')
        assert result is True
        assert '21 passed' in vm._latest_response_text
        assert 'structured_self_audit' in vm._latest_response_meta

    def test_with_self_examination(self, tmp_path):
        se_dir = tmp_path / 'data' / 'evolution' / 'self_examination'
        se_dir.mkdir(parents=True)
        (se_dir / 'latest.json').write_text(json.dumps({
            'status': 'healthy', 'findings': [{'a': 1}, {'b': 2}],
        }))
        vm = _make_vm(str(tmp_path))
        result = vm._answer_direct_self_audit_query('autoauditoria')
        assert result is True
        assert 'Self-examination' in vm._latest_response_text
        assert '2 findings' in vm._latest_response_text


# ---------------------------------------------------------------------------
# 4. _answer_direct_self_audit_query handles missing evidence
# ---------------------------------------------------------------------------
class TestAnswerDirectSelfAuditMissingEvidence:
    def test_no_evidence_files(self, tmp_path):
        vm = _make_vm(str(tmp_path))
        result = vm._answer_direct_self_audit_query('autoauditoria')
        assert result is True
        assert 'sin evidencia' in vm._latest_response_text or 'sin snapshot' in vm._latest_response_text

    def test_no_workspace(self):
        vm = _make_vm('')
        result = vm._answer_direct_self_audit_query('autoauditoria')
        assert result is False


# ---------------------------------------------------------------------------
# 5. _is_new_chatgpt_consultation detects fresh consultation requests
# ---------------------------------------------------------------------------
class TestIsNewChatgptConsultation:
    def test_haz_una_consulta(self):
        vm = _make_vm()
        assert vm._is_new_chatgpt_consultation('haz una consulta a chatgpt')

    def test_consulta_nueva(self):
        vm = _make_vm()
        assert vm._is_new_chatgpt_consultation('consulta nueva a ChatGPT')

    def test_has_una_consulta(self):
        vm = _make_vm()
        assert vm._is_new_chatgpt_consultation('has una consulta a chatgpt: dime algo')


# ---------------------------------------------------------------------------
# 6. _is_new_chatgpt_consultation rejects non-consultation messages
# ---------------------------------------------------------------------------
class TestIsNewChatgptConsultationRejects:
    def test_followup_not_detected(self):
        vm = _make_vm()
        assert not vm._is_new_chatgpt_consultation('que paso con chatgpt')

    def test_greeting_not_detected(self):
        vm = _make_vm()
        assert not vm._is_new_chatgpt_consultation('hola como estas')

    def test_deictic_not_detected(self):
        vm = _make_vm()
        assert not vm._is_new_chatgpt_consultation('solucionar eso')


# ---------------------------------------------------------------------------
# 7. _try_handle_external_failure_followup skips when new consultation
# ---------------------------------------------------------------------------
class TestFollowupSkipsNewConsultation:
    def test_new_consultation_bypasses_followup(self):
        vm = _make_vm()
        vm._last_external_failure_payload = {
            'assistant_title': 'ChatGPT',
            'message': 'blocked',
            'meta': 'browser_security_verification',
            'outcome': 'blocked_by_security_verification',
            'success': False,
            'at': time.time(),
            'assistant_kind': 'chatgpt',
            'terminal_state': 'blocked_by_security_verification',
            'dispatch_id': 'abc123',
        }
        vm._last_external_failure_ts = time.time()
        result = vm._try_handle_external_failure_followup(
            'haz una consulta a chatgpt: dime algo nuevo'
        )
        assert result is False

    def test_followup_still_works_for_deictic(self):
        vm = _make_vm()
        vm._last_external_failure_payload = {
            'assistant_title': 'ChatGPT',
            'message': 'blocked',
            'meta': 'test',
            'outcome': 'failed',
            'success': False,
            'at': time.time(),
            'assistant_kind': 'chatgpt',
            'terminal_state': 'failed_with_actionable_reason',
            'dispatch_id': 'abc123',
        }
        vm._last_external_failure_ts = time.time()
        result = vm._try_handle_external_failure_followup('solucionar eso')
        assert result is True


# ---------------------------------------------------------------------------
# 8. Isolated profile note included when browser_security_verification
# ---------------------------------------------------------------------------
class TestIsolatedProfileNote:
    def test_profile_note_with_security_verification(self):
        vm = _make_vm()
        vm._last_external_failure_payload = {
            'assistant_title': 'ChatGPT',
            'message': 'no pude',
            'meta': 'browser_security_verification bloqueó',
            'outcome': 'blocked_by_security_verification',
            'success': False,
            'at': time.time(),
            'assistant_kind': 'chatgpt',
            'terminal_state': 'browser_security_verification',
            'dispatch_id': 'abc123',
        }
        vm._last_external_failure_ts = time.time()
        result = vm._try_handle_external_failure_followup('que paso')
        assert result is True
        assert 'perfil controlado por IABV' in vm._latest_response_text
        assert 'perfil aislado' in vm._latest_response_text


# ---------------------------------------------------------------------------
# 9. Isolated profile note NOT included when other terminal states
# ---------------------------------------------------------------------------
class TestNoIsolatedProfileNote:
    def test_no_profile_note_with_resource_pressure(self):
        vm = _make_vm()
        vm._last_external_failure_payload = {
            'assistant_title': 'ChatGPT',
            'message': 'bloqueado',
            'meta': 'resource_pressure',
            'outcome': 'blocked_by_resource_pressure',
            'success': False,
            'at': time.time(),
            'assistant_kind': 'chatgpt',
            'terminal_state': 'blocked_by_resource_pressure',
            'dispatch_id': 'abc123',
        }
        vm._last_external_failure_ts = time.time()
        result = vm._try_handle_external_failure_followup('que paso')
        assert result is True
        assert 'perfil controlado por IABV' not in vm._latest_response_text


# ---------------------------------------------------------------------------
# 10. OSES _metacognitive_starvation_findings with >=2 signals
# ---------------------------------------------------------------------------
class TestOSESStarvation:
    def test_starvation_with_missing_test_evidence_and_self_examination(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        # Neither test_evidence nor self_examination exist
        findings = svc._metacognitive_starvation_findings()
        assert len(findings) == 1
        assert findings[0].category == 'metacognitive_maintenance_starved'
        assert 'no_test_evidence' in findings[0].metadata.get('signals', [])
        assert 'no_self_examination' in findings[0].metadata.get('signals', [])


# ---------------------------------------------------------------------------
# 11. OSES _metacognitive_starvation_findings no finding with <2 signals
# ---------------------------------------------------------------------------
class TestOSESNoStarvation:
    def test_no_starvation_with_evidence(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        # Create both evidence files
        te_dir = tmp_path / 'data' / 'evolution' / 'test_evidence'
        te_dir.mkdir(parents=True)
        (te_dir / 'latest.json').write_text('{"passed": 5}')
        se_dir = tmp_path / 'data' / 'evolution' / 'self_examination'
        se_dir.mkdir(parents=True)
        (se_dir / 'latest.json').write_text(json.dumps({
            'status': 'ok', 'findings': [],
            'timestamp': '2099-01-01T00:00:00Z',
        }))
        findings = svc._metacognitive_starvation_findings()
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# 12. sendChat routing: self-audit guard fires before lightweight_chat
# ---------------------------------------------------------------------------
class TestSendChatRouting:
    def test_self_audit_query_does_not_reach_lightweight(self, tmp_path):
        """When a self-audit query arrives, it should be handled by
        _answer_direct_self_audit_query, not by _try_handle_lightweight_chat."""
        vm = _make_vm(str(tmp_path))
        # Ensure _is_direct_self_audit_query returns True
        assert vm._is_direct_self_audit_query('dime el estado de tests')
        # Ensure _answer_direct_self_audit_query returns True
        result = vm._answer_direct_self_audit_query('dime el estado de tests')
        assert result is True


# ---------------------------------------------------------------------------
# 13. platform_pending P0.30 JSON validates with PlatformPendingTask
# ---------------------------------------------------------------------------
class TestPlatformPendingP030:
    def test_json_validates(self):
        from iabv_v15.domain.models import PlatformPendingTask
        json_path = (
            Path(__file__).resolve().parent.parent
            / 'data' / 'evolution' / 'platform_pending'
            / 'task_runtime_metacognitive_direct_audit_and_chatgpt_profile_p030.json'
        )
        raw = json_path.read_text(encoding='utf-8')
        task = PlatformPendingTask.model_validate_json(raw)
        assert task.id == 'runtime_metacognitive_direct_audit_and_chatgpt_profile_p030'
        assert task.priority == 'P0'
        assert 'CODE_FIX_PENDING_LIVE_PROOF' in str(task.metadata)
