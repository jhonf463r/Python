"""P0.24 focused tests: Build-State Sovereignty + Live Runtime Contract.

Tests cover:
1. Feature markers for P0.22 and P0.23 are present in _REQUIRED_FEATURE_MARKERS.
2. _collect_build_fingerprint detects stale builds when markers are missing.
3. trace_stale_build_detected records the correct event kind.
4. trace_live_proof_started records expected terminals.
5. trace_live_proof_result records terminal state and validity.
6. validate_live_proof_terminal accepts/rejects terminal states per contract.
7. Bootstrap stores _build_fingerprint_data and _build_stale.
8. Platform pending P0.24 JSON validates.

All tests use stubs (no AppBootstrap/Qt) for speed.
Target: full suite < 3s on normal machine.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


# ── 1. Feature markers include P0.22 and P0.23 ──


class TestFeatureMarkersIncludeP022P023:

    def test_has_p022_marker(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _REQUIRED_FEATURE_MARKERS,
        )
        assert 'has_p022_consultation_state' in _REQUIRED_FEATURE_MARKERS
        assert _REQUIRED_FEATURE_MARKERS['has_p022_consultation_state'] == '_should_defer_heavy_work'

    def test_has_p023_marker(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _REQUIRED_FEATURE_MARKERS,
        )
        assert 'has_p023_external_intent_security' in _REQUIRED_FEATURE_MARKERS
        assert _REQUIRED_FEATURE_MARKERS['has_p023_external_intent_security'] == '_ASSISTANT_ALIASES'

    def test_marker_files_includes_assistant_preference_resolver(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import _MARKER_FILES
        assert 'services/adaptive/assistant_preference_resolver.py' in _MARKER_FILES

    def test_original_markers_still_present(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _REQUIRED_FEATURE_MARKERS,
        )
        assert 'has_post_remediation_recapture' in _REQUIRED_FEATURE_MARKERS
        assert 'has_post_recapture_response_retry' in _REQUIRED_FEATURE_MARKERS
        assert 'has_shared_reality_handoff' in _REQUIRED_FEATURE_MARKERS
        assert 'has_dispatch_lifecycle_tracing' in _REQUIRED_FEATURE_MARKERS


# ── 2. _collect_build_fingerprint stale detection ──


class TestCollectBuildFingerprintStaleDetection:

    def test_fingerprint_returns_stale_when_markers_missing(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _collect_build_fingerprint,
        )
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'src' / 'iabv_v15'
            src.mkdir(parents=True)
            # Create empty marker files so file reads succeed but markers not found
            for sub in (
                'ui/viewmodels',
                'services/evolution',
                'services/capture',
                'services/adaptive',
            ):
                (src / sub).mkdir(parents=True, exist_ok=True)
            (src / 'ui/viewmodels/control_center_viewmodel.py').write_text('')
            (src / 'services/evolution/runtime_audit_tracer.py').write_text('')
            (src / 'services/evolution/freeze_incident_reporter.py').write_text('')
            (src / 'services/capture/browser_session_controller.py').write_text('')
            (src / 'services/adaptive/assistant_preference_resolver.py').write_text('')

            fp = _collect_build_fingerprint(td)
            assert fp['stale'] is True
            assert len(fp['missing_markers']) > 0
            assert 'has_p022_consultation_state' in fp['missing_markers']
            assert 'has_p023_external_intent_security' in fp['missing_markers']

    def test_fingerprint_not_stale_when_all_markers_present(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _collect_build_fingerprint,
            _REQUIRED_FEATURE_MARKERS,
        )
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'src' / 'iabv_v15'
            src.mkdir(parents=True)
            for sub in (
                'ui/viewmodels',
                'services/evolution',
                'services/capture',
                'services/adaptive',
            ):
                (src / sub).mkdir(parents=True, exist_ok=True)
            # Write all marker strings into the viewmodel file
            all_markers = '\n'.join(_REQUIRED_FEATURE_MARKERS.values())
            (src / 'ui/viewmodels/control_center_viewmodel.py').write_text(all_markers)
            (src / 'services/evolution/runtime_audit_tracer.py').write_text(all_markers)
            (src / 'services/evolution/freeze_incident_reporter.py').write_text(all_markers)
            (src / 'services/capture/browser_session_controller.py').write_text(all_markers)
            (src / 'services/adaptive/assistant_preference_resolver.py').write_text(all_markers)

            fp = _collect_build_fingerprint(td)
            assert fp['stale'] is False
            assert fp['missing_markers'] == []

    def test_fingerprint_has_elapsed_ms(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _collect_build_fingerprint,
        )
        fp = _collect_build_fingerprint('.')
        assert 'elapsed_ms' in fp
        assert isinstance(fp['elapsed_ms'], float)


# ── 3. trace_stale_build_detected ──


class TestTraceStaleBuiltDetected:

    def test_trace_stale_build_detected_event_kind(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_stale_build_detected(
            head='abc123',
            branch='main',
            missing_markers=['has_p022_consultation_state'],
        )
        assert event['kind'] == 'stale_build_detected'
        assert event['data']['head'] == 'abc123'
        assert event['data']['branch'] == 'main'
        assert 'has_p022_consultation_state' in event['data']['missing_markers']

    def test_trace_stale_build_detected_defaults(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_stale_build_detected()
        assert event['kind'] == 'stale_build_detected'
        assert event['data']['head'] == ''
        assert event['data']['missing_markers'] == []


# ── 4. trace_live_proof_started ──


class TestTraceLiveProofStarted:

    def test_records_input_message(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_live_proof_started(
            input_message='consulta nueva a ChatGPT: responde solo S si entiendes',
        )
        assert event['kind'] == 'live_proof_started'
        assert 'consulta nueva' in event['data']['input_message']

    def test_records_expected_terminals(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_live_proof_started()
        assert event['kind'] == 'live_proof_started'
        terminals = event['data']['expected_terminals']
        assert 'response_captured' in terminals
        assert 'blocked_by_security_verification' in terminals
        assert 'blocked_by_resource_pressure' in terminals

    def test_custom_expected_terminals(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_live_proof_started(
            expected_terminals=['response_captured'],
        )
        assert event['data']['expected_terminals'] == ['response_captured']


# ── 5. trace_live_proof_result ──


class TestTraceLiveProofResult:

    def test_records_valid_result(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_live_proof_result(
            terminal_state='response_captured',
            valid=True,
            detail='got S',
            dispatch_id='abc123',
        )
        assert event['kind'] == 'live_proof_result'
        assert event['data']['terminal_state'] == 'response_captured'
        assert event['data']['valid'] is True
        assert event['data']['dispatch_id'] == 'abc123'

    def test_records_invalid_result(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        tracer = RuntimeAuditTracer()
        event = tracer.trace_live_proof_result(
            terminal_state='local_chat',
            valid=False,
            detail='misrouted to local',
        )
        assert event['data']['valid'] is False
        assert event['data']['terminal_state'] == 'local_chat'


# ── 6. validate_live_proof_terminal ──


class TestValidateLiveProofTerminal:

    def test_response_captured_is_valid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('response_captured', dispatch_id='d1')
        assert result['valid'] is True
        assert result['dispatch_id'] == 'd1'

    def test_blocked_by_security_verification_is_valid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('blocked_by_security_verification')
        assert result['valid'] is True

    def test_blocked_by_resource_pressure_is_valid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('blocked_by_resource_pressure')
        assert result['valid'] is True

    def test_local_chat_is_invalid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('local_chat')
        assert result['valid'] is False
        assert 'external_consultation' in result['reason']

    def test_operational_status_is_invalid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('operational_status')
        assert result['valid'] is False

    def test_empty_terminal_is_invalid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('')
        assert result['valid'] is False
        assert 'empty' in result['reason']

    def test_nonetype_get_error_detected(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal(
            'failed_with_actionable_reason',
            error_message="'NoneType' object has no attribute 'get'",
        )
        assert result['valid'] is False
        assert 'NoneType' in result['reason']

    def test_unknown_terminal_is_invalid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('some_new_state')
        assert result['valid'] is False
        assert 'unknown' in result['reason']

    def test_dispatch_id_echoed_back(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import validate_live_proof_terminal
        result = validate_live_proof_terminal('response_captured', dispatch_id='xyz789')
        assert result['dispatch_id'] == 'xyz789'


# ── 7. Bootstrap stores fingerprint data ──


class TestBootstrapStoresFingerprintData:

    def test_bootstrap_has_build_stale_attribute(self) -> None:
        from iabv_v15.bootstrap import AppBootstrap
        assert hasattr(AppBootstrap, '__init__')
        # Verify the attribute is set in __init__ by reading the source
        import inspect
        source = inspect.getsource(AppBootstrap.__init__)
        assert '_build_stale' in source
        assert '_build_fingerprint_data' in source

    def test_bootstrap_calls_trace_stale_build_detected(self) -> None:
        import inspect
        from iabv_v15.bootstrap import AppBootstrap
        source = inspect.getsource(AppBootstrap.__init__)
        assert 'trace_stale_build_detected' in source


# ── 8. Live proof terminal constants ──


class TestLiveProofTerminalConstants:

    def test_valid_terminals_contains_expected(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _LIVE_PROOF_VALID_TERMINALS,
        )
        assert 'response_captured' in _LIVE_PROOF_VALID_TERMINALS
        assert 'blocked_by_security_verification' in _LIVE_PROOF_VALID_TERMINALS
        assert 'blocked_by_resource_pressure' in _LIVE_PROOF_VALID_TERMINALS

    def test_invalid_terminals_contains_expected(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _LIVE_PROOF_INVALID_TERMINALS,
        )
        assert 'local_chat' in _LIVE_PROOF_INVALID_TERMINALS
        assert 'operational_status' in _LIVE_PROOF_INVALID_TERMINALS

    def test_no_overlap_between_valid_and_invalid(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            _LIVE_PROOF_VALID_TERMINALS,
            _LIVE_PROOF_INVALID_TERMINALS,
        )
        overlap = _LIVE_PROOF_VALID_TERMINALS & _LIVE_PROOF_INVALID_TERMINALS
        assert overlap == frozenset()


# ── 9. P0.23 trace_event fix (was trace_event, now trace) ──


class TestP023TraceEventFix:

    def test_control_center_viewmodel_uses_trace_not_trace_event(self) -> None:
        import inspect
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        source = inspect.getsource(ControlCenterViewModel._set_live_status)
        assert 'trace_event(' not in source
        assert '.trace(' in source

    def test_apply_task_result_uses_trace_not_trace_event(self) -> None:
        import inspect
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        source = inspect.getsource(ControlCenterViewModel._apply_task_result)
        assert 'trace_event(' not in source


# ── 10. Platform pending P0.24 valid JSON ──


class TestPlatformPendingP024ValidJson:

    def test_p024_json_validates(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        p = Path(__file__).resolve().parent.parent / (
            'data/evolution/platform_pending/'
            'task_runtime_build_state_sovereignty_live_contract_p024.json'
        )
        assert p.exists(), f'P0.24 platform pending file not found: {p}'
        raw = p.read_text(encoding='utf-8')
        task = PlatformPendingTask.model_validate_json(raw)
        assert task.id
        assert task.title

    def test_p024_has_verification_status(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        p = Path(__file__).resolve().parent.parent / (
            'data/evolution/platform_pending/'
            'task_runtime_build_state_sovereignty_live_contract_p024.json'
        )
        raw = p.read_text(encoding='utf-8')
        task = PlatformPendingTask.model_validate_json(raw)
        assert task.metadata.get('verification_status') == 'CODE_FIX_PENDING_LIVE_PROOF'

    def test_p024_has_build_sovereignty_evidence(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        p = Path(__file__).resolve().parent.parent / (
            'data/evolution/platform_pending/'
            'task_runtime_build_state_sovereignty_live_contract_p024.json'
        )
        raw = p.read_text(encoding='utf-8')
        task = PlatformPendingTask.model_validate_json(raw)
        evidence = task.metadata.get('evidence', [])
        assert len(evidence) > 0

    def test_p024_references_stale_build(self) -> None:
        p = Path(__file__).resolve().parent.parent / (
            'data/evolution/platform_pending/'
            'task_runtime_build_state_sovereignty_live_contract_p024.json'
        )
        raw = p.read_text(encoding='utf-8')
        data = json.loads(raw)
        desc = data.get('description', '') + data.get('reason', '')
        assert 'stale' in desc.lower() or '901fa7629' in desc
