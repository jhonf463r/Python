"""P0.30 focused tests: structured self-audit guard, ChatGPT new-vs-followup,
isolated profile explanation, and OSES metacognitive starvation.

All tests use lightweight stubs (no AppBootstrap) unless explicitly noted.
"""
from __future__ import annotations

import json
import shutil
import threading
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
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
        _external_consultation_browser_override={},
        _live_status='idle',
        _last_user_goal='',
        _assistant_preference_resolver=AssistantPreferenceResolver(),
    )

    # Copy class-level constants that instance methods reference via self.
    # These are tuples, ints, floats etc defined on the class body.
    for attr_name in dir(ControlCenterViewModel):
        if attr_name.startswith('__'):
            continue  # skip dunder
        val = getattr(ControlCenterViewModel, attr_name, None)
        if isinstance(val, (tuple, int, float, str, frozenset)):
            if not hasattr(stub, attr_name):
                setattr(stub, attr_name, val)

    # Bind required methods
    for name in (
        '_try_handle_structured_self_audit',
        '_try_handle_external_failure_followup',
        '_explicit_assistant_preference',
        '_human_external_consultation_failure',
        '_external_state_notice',
        '_remember_external_failure',
        '_clear_external_failure_memory',
        '_external_failure_followup_can_recover_from_audit',
        '_recover_external_failure_from_runtime_audit',
        '_external_failure_indicates_security_verification',
        '_security_help_requests_visible_window',
        '_security_followup_disputes_visible_verification',
        '_security_followup_requests_user_browser',
        '_security_verification_assistant_kind',
        '_remember_user_browser_external_override',
        '_humanize_task_failure',
        '_assistant_display_name',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is not None:
            stub.__dict__[name] = types.MethodType(method, stub)

    # Stubs for side-effect methods
    stub._append_message = MagicMock()
    stub._set_live_status = MagicMock()
    stub._clear_autonomy_activity_override = MagicMock()
    stub._open_security_verification_window = MagicMock(return_value={
        'opened': True,
        'mode': 'visible_isolated_profile',
        'assistant_kind': 'chatgpt',
        'url': 'https://chatgpt.com/',
    })
    stub.dataChanged = MagicMock()
    stub.dataChanged.emit = MagicMock()

    return stub


# ── Task B: Structured self-audit guard ─────────────────────────

class TestStructuredSelfAuditGuard:
    """Verify that self-audit queries are answered from artifacts, not Ollama."""

    def setup_method(self) -> None:
        self.workspace = Path(f'/tmp/test_p030_selfaudit_{uuid4().hex[:8]}')
        self.workspace.mkdir(parents=True, exist_ok=True)
        # Create minimal artifact files
        evo = self.workspace / 'data' / 'evolution'
        (evo / 'test_evidence').mkdir(parents=True, exist_ok=True)
        (evo / 'self_examination').mkdir(parents=True, exist_ok=True)
        (evo / 'portable_context').mkdir(parents=True, exist_ok=True)
        (evo / 'control_master').mkdir(parents=True, exist_ok=True)

        te = {'passed': 42, 'failed': 1, 'total': 43, 'timestamp': datetime.now(timezone.utc).isoformat()}
        (evo / 'test_evidence' / 'latest.json').write_text(json.dumps(te), encoding='utf-8')

        se = {'status': 'healthy', 'summary': 'All systems operational', 'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'findings': [{'category': 'test'}]}
        (evo / 'self_examination' / 'latest.json').write_text(json.dumps(se), encoding='utf-8')

        pc = {'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'sections': [{'section_id': 'cloud_reasoning'}, {'section_id': 'test_evidence'}]}
        (evo / 'portable_context' / 'latest.json').write_text(json.dumps(pc), encoding='utf-8')

        cm = {'current_tests_state': {'passed': 42, 'failed': 1, 'total': 43}}
        (evo / 'control_master' / 'latest.json').write_text(json.dumps(cm), encoding='utf-8')

        self.vm = _make_stub_vm(workspace=self.workspace)

    def teardown_method(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_autoauditoria_answered_from_artifacts(self) -> None:
        result = self.vm._try_handle_structured_self_audit(
            'haz una autoauditoría y dime el estado de tests, self audit y portable context'
        )
        assert result is True
        assert 'passed=42' in self.vm._latest_response_text
        assert 'SelfAudit' in self.vm._latest_response_text
        assert 'PortableContext' in self.vm._latest_response_text
        assert 'ControlMaster' in self.vm._latest_response_text
        assert self.vm._working is False

    def test_estado_de_tests_answered(self) -> None:
        result = self.vm._try_handle_structured_self_audit('estado de tests')
        assert result is True
        assert 'passed=42' in self.vm._latest_response_text

    def test_control_master_answered(self) -> None:
        result = self.vm._try_handle_structured_self_audit('control master')
        assert result is True
        assert 'ControlMaster' in self.vm._latest_response_text

    def test_portable_context_answered(self) -> None:
        result = self.vm._try_handle_structured_self_audit('portable context')
        assert result is True
        assert 'PortableContext' in self.vm._latest_response_text

    def test_non_audit_message_not_captured(self) -> None:
        result = self.vm._try_handle_structured_self_audit('haz una consulta a chatgpt')
        assert result is False

    def test_no_ollama_invoked(self) -> None:
        """The guard must NOT call any LLM/Ollama method."""
        result = self.vm._try_handle_structured_self_audit('autoauditoria')
        assert result is True
        assert 'structured_self_audit' in self.vm._latest_response_meta
        # No LLM methods should exist on our stub — if they did and were
        # called, the test would fail with AttributeError
        assert not hasattr(self.vm, 'inference_service')

    def test_missing_evidence_reported(self) -> None:
        """When test_evidence is missing, the guard reports UNRESOLVED."""
        (self.workspace / 'data' / 'evolution' / 'test_evidence' / 'latest.json').unlink()
        result = self.vm._try_handle_structured_self_audit('autoauditoria')
        assert result is True
        assert 'UNRESOLVED' in self.vm._latest_response_text
        assert 'test_evidence' in self.vm._latest_response_text

    def test_responds_under_5_seconds(self) -> None:
        """The guard must respond in <5s (target: <1s for disk reads)."""
        t0 = time.perf_counter()
        self.vm._try_handle_structured_self_audit('autoauditoria')
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f'Self-audit took {elapsed:.1f}s, must be <5s'


class TestStructuredSelfAuditNoArtifacts:
    """When no artifacts exist, the guard still answers without crashing."""

    def setup_method(self) -> None:
        self.workspace = Path(f'/tmp/test_p030_noart_{uuid4().hex[:8]}')
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.vm = _make_stub_vm(workspace=self.workspace)

    def teardown_method(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_answers_with_all_missing(self) -> None:
        result = self.vm._try_handle_structured_self_audit('autoauditoria')
        assert result is True
        assert 'UNRESOLVED' in self.vm._latest_response_text


# ── Task D: New consultation vs follow-up ───────────────────────

class TestNewConsultationVsFollowup:
    """Verify that explicit new consultation intent is NOT captured as follow-up."""

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()
        # Simulate a recent external failure
        self.vm._remember_external_failure(
            assistant_title='ChatGPT',
            message='Verificacion de seguridad pendiente',
            meta='ChatGPT: blocked_by_security_verification',
            outcome='failed',
            assistant_kind='chatgpt',
            terminal_state='blocked_by_security_verification',
        )

    def test_deictic_followup_captured(self) -> None:
        """'pueddes solucionar eso' after failure -> follow-up."""
        result = self.vm._try_handle_external_failure_followup('pueddes solucionar eso')
        assert result is True

    def test_new_consultation_not_captured(self) -> None:
        """'haz una consulta a ChatGPT: responde solo S' after failure -> NOT follow-up."""
        result = self.vm._try_handle_external_failure_followup(
            'haz una consulta a ChatGPT: responde solo S si entiendes'
        )
        assert result is False

    def test_shared_reality_dispute_captured(self) -> None:
        """'no veo la verificación' -> follow-up (not new consultation)."""
        # This pattern matches 'por que' and 'no pudo' type patterns
        result = self.vm._try_handle_external_failure_followup('por que no pudo consultar')
        assert result is True

    def test_no_recent_failure_no_capture(self) -> None:
        """Without recent failure, nothing is captured."""
        self.vm._clear_external_failure_memory()
        result = self.vm._try_handle_external_failure_followup('soluciona eso')
        assert result is False

    def test_consulta_nueva_explicit_not_captured(self) -> None:
        """'consulta chatgpt ahora' should route as new external, not follow-up."""
        result = self.vm._try_handle_external_failure_followup('consulta chatgpt ahora')
        assert result is False


# ── Task E: Isolated profile explanation ────────────────────────

class TestIsolatedProfileExplanation:
    """Verify that security_verification handoff mentions isolated profile."""

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_browser_security_mentions_isolated_profile(self) -> None:
        msg, meta, busy = self.vm._human_external_consultation_failure(
            'ChatGPT', 'browser_security_verification detected'
        )
        assert 'perfil controlado por IABV' in msg
        assert 'chatgpt_program_session/browser_profile' in msg
        assert 'Chrome normal' in msg
        assert 'ya lo hice' in msg
        assert 'blocked_by_security_verification' in meta

    def test_non_security_does_not_mention_profile(self) -> None:
        msg, meta, busy = self.vm._human_external_consultation_failure(
            'ChatGPT', 'timeout: request took too long'
        )
        assert 'perfil controlado' not in msg
        assert 'timeout' in meta


# ── Task F: OSES metacognitive starvation ───────────────────────

class TestOSESMetacognitiveStarvation:
    """Verify OSES detects metacognitive starvation."""

    def setup_method(self) -> None:
        self.workspace = Path(f'/tmp/test_p030_oses_starv_{uuid4().hex[:8]}')
        self.workspace.mkdir(parents=True, exist_ok=True)

    def teardown_method(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _write_audit_lines(self, lines: list[dict]) -> None:
        audit_dir = self.workspace / 'data' / 'logs'
        audit_dir.mkdir(parents=True, exist_ok=True)
        with (audit_dir / 'runtime_audit.jsonl').open('w', encoding='utf-8') as f:
            for entry in lines:
                f.write(json.dumps(entry) + '\n')

    def test_starvation_detected_with_many_skips(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
        # Write 6 pressure-skip events
        events = [
            {'kind': 'control_autonomy_dock_refresh_skipped_due_to_pressure', 'data': {}}
            for _ in range(6)
        ]
        self._write_audit_lines(events)

        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.workspace_root = str(self.workspace)
        findings = svc._metacognitive_starvation_findings()
        assert len(findings) >= 1
        assert findings[0].category == 'metacognitive_maintenance_starved'

    def test_no_starvation_with_few_skips(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
        events = [
            {'kind': 'control_autonomy_dock_refresh_skipped_due_to_pressure', 'data': {}}
        ]
        self._write_audit_lines(events)
        # Also write fresh test evidence so the threshold is higher
        te_dir = self.workspace / 'data' / 'evolution' / 'test_evidence'
        te_dir.mkdir(parents=True, exist_ok=True)
        te = {'passed': 10, 'failed': 0, 'total': 10, 'timestamp': datetime.now(timezone.utc).isoformat()}
        (te_dir / 'latest.json').write_text(json.dumps(te), encoding='utf-8')

        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.workspace_root = str(self.workspace)
        findings = svc._metacognitive_starvation_findings()
        assert len(findings) == 0

    def test_starvation_with_missing_test_evidence_and_some_skips(self) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
        # 2 skips + no test evidence = starved
        events = [
            {'kind': 'resource_pressure', 'data': {}},
            {'kind': 'resource_pressure', 'data': {}},
        ]
        self._write_audit_lines(events)

        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.workspace_root = str(self.workspace)
        findings = svc._metacognitive_starvation_findings()
        assert len(findings) >= 1


# ── Task G: RuntimeAuditTracer trace kinds ──────────────────────

class TestRuntimeAuditTracerP030:
    """Verify new trace kinds are recorded correctly."""

    def setup_method(self) -> None:
        self.workspace = Path(f'/tmp/test_p030_tracer_{uuid4().hex[:8]}')
        self.workspace.mkdir(parents=True, exist_ok=True)

    def teardown_method(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_structured_self_audit_traced(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        log_dir = self.workspace / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        tracer = RuntimeAuditTracer(log_dir=str(log_dir))
        event = tracer.trace(
            'structured_self_audit_answered',
            artifacts_found=4,
            missing=[],
        )
        assert event['kind'] == 'structured_self_audit_answered'
        assert event['data']['artifacts_found'] == 4

    def test_new_request_forced_traced(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        log_dir = self.workspace / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        tracer = RuntimeAuditTracer(log_dir=str(log_dir))
        event = tracer.trace(
            'external_consultation_new_request_forced',
            previous_failure_assistant='ChatGPT',
            new_target='chatgpt',
        )
        assert event['kind'] == 'external_consultation_new_request_forced'
        assert event['data']['new_target'] == 'chatgpt'

    def test_profile_context_traced(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        log_dir = self.workspace / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        tracer = RuntimeAuditTracer(log_dir=str(log_dir))
        event = tracer.trace(
            'assistant_profile_context_reported',
            profile_label='chatgpt_program_session/browser_profile',
            block_type='browser_security_verification',
        )
        assert event['kind'] == 'assistant_profile_context_reported'
        assert 'browser_profile' in event['data']['profile_label']


# ── Task H: Platform pending validation ─────────────────────────

class TestPlatformPendingP030:
    """Validate the P0.30 platform pending task JSON."""

    def test_task_json_is_valid(self) -> None:
        task_path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_metacognitive_direct_audit_and_chatgpt_profile_p030.json'
        assert task_path.exists(), f'Missing: {task_path}'
        data = json.loads(task_path.read_text(encoding='utf-8'))
        assert data['id'] == 'runtime_metacognitive_direct_audit_and_chatgpt_profile_p030'
        assert data['status'] == 'READY_FOR_NEXT_SLICE'
        assert 'tasks_implemented' in data['metadata']
        assert len(data['metadata']['tasks_implemented']) >= 4

    def test_validates_with_platform_pending_task_model(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        task_path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_metacognitive_direct_audit_and_chatgpt_profile_p030.json'
        raw = task_path.read_text(encoding='utf-8')
        task = PlatformPendingTask.model_validate_json(raw)
        assert task.id == 'runtime_metacognitive_direct_audit_and_chatgpt_profile_p030'
        assert task.category == 'runtime_observability'
