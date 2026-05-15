"""P0.5 — Shared Reality Learning / OSES Feedback tests.

Tests that OSES detects repeated visual mismatch patterns from
shared_reality_handoff events, generates structured findings, and
PortableContext exports a compact summary without PII.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)
from iabv_v15.services.evolution.portable_context_service import (
    PortableContextService,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


# ── Helpers ──────────────────────────────────────────────────────────

def _make_handoff_event(
    *,
    assistant_kind: str = 'chatgpt',
    target_window_title: str = 'ChatGPT - Google Chrome for Testing',
    capture_useful: bool = False,
    blank_probability: float = 0.98,
    mismatch_reason: str = 'ventana minimizada, sesión aislada',
    user_claim: str = '',
    browser_label: str = 'sesión aislada',
    browser_profile: str = '',
    selected_browser_or_profile: str = '',
    seq: int = 1,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        'assistant_kind': assistant_kind,
        'target_window_title': target_window_title,
        'capture_useful': capture_useful,
        'blank_probability': blank_probability,
        'mismatch_reason': mismatch_reason,
        'user_claim': user_claim,
        'browser_label': browser_label,
        'capture_quality': {
            'blank_probability': blank_probability,
            'dynamic_range': 0,
            'unique_color_count': 1,
            'useful': capture_useful,
        },
    }
    if browser_profile:
        data['browser_profile'] = browser_profile
    if selected_browser_or_profile:
        data['selected_browser_or_profile'] = selected_browser_or_profile
    return {
        'ts': '2026-05-15T10:00:00.000Z',
        'elapsed_ms': 1000.0 * seq,
        'kind': 'shared_reality_handoff',
        'seq': seq,
        'data': data,
    }


def _make_noise_event(*, kind: str = 'service_init', seq: int = 1) -> dict[str, Any]:
    """Non-handoff event for padding logs."""
    return {
        'ts': '2026-05-15T09:00:00.000Z',
        'elapsed_ms': 100.0 * seq,
        'kind': kind,
        'seq': seq,
        'data': {'service': f'fake_service_{seq}'},
    }


def _write_audit_events(workspace: Path, events: list[dict[str, Any]]) -> None:
    log_dir = workspace / 'data' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_path = log_dir / 'runtime_audit.jsonl'
    with audit_path.open('w', encoding='utf-8') as fh:
        for event in events:
            fh.write(json.dumps(event) + '\n')


def _make_oses(workspace: Path) -> OperationalSelfExaminationService:
    storage = ArtifactStorage(root=str(workspace / 'data'))
    return OperationalSelfExaminationService(
        workspace_root=str(workspace),
        storage=storage,
    )


# ══════════════════════════════════════════════════════════════════════
# OSES pattern detection
# ══════════════════════════════════════════════════════════════════════

class TestOSESRepeatedVisualMismatch:
    """OSES detects repeated_visual_mismatch when ≥2 handoff events have
    capture_useful=false."""

    def test_two_useless_captures_produces_finding(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1),
            _make_handoff_event(seq=2, assistant_kind='gemini'),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'repeated_visual_mismatch' in cats
        f = next(f for f in findings if f.category == 'repeated_visual_mismatch')
        assert f.metadata['frequency'] == 2
        assert f.metadata['pattern'] == 'repeated_visual_mismatch'
        assert f.metadata['recommended_action'] == 'auto_restore_or_select_window'

    def test_three_events_frequency_is_three(self, tmp_path: Path) -> None:
        events = [_make_handoff_event(seq=i) for i in range(1, 4)]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        f = next(f for f in findings if f.category == 'repeated_visual_mismatch')
        assert f.metadata['frequency'] == 3


class TestOSESSingleEventNoFinding:
    """A single handoff event must NOT produce any findings — only
    repetition indicates a pattern."""

    def test_single_event_no_findings(self, tmp_path: Path) -> None:
        events = [_make_handoff_event(seq=1)]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        assert len(findings) == 0

    def test_no_events_no_findings(self, tmp_path: Path) -> None:
        _write_audit_events(tmp_path, [])
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        assert len(findings) == 0

    def test_no_audit_file_no_findings(self, tmp_path: Path) -> None:
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        assert len(findings) == 0


class TestOSESBlackCaptureRepeated:
    """OSES detects black_capture_repeated when ≥2 events have
    blank_probability ≥ 0.8."""

    def test_two_black_captures_detected(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1, blank_probability=0.95),
            _make_handoff_event(seq=2, blank_probability=0.98),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'black_capture_repeated' in cats
        f = next(f for f in findings if f.category == 'black_capture_repeated')
        assert f.metadata['frequency'] == 2

    def test_low_blank_probability_not_counted(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1, blank_probability=0.3, capture_useful=True),
            _make_handoff_event(seq=2, blank_probability=0.2, capture_useful=True),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'black_capture_repeated' not in cats


class TestOSESUserNeededToExplain:
    """OSES detects user_needed_to_explain_same_gap when ≥2 events have
    a non-empty user_claim."""

    def test_two_user_claims_detected(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1, user_claim='a mí sí me funciona'),
            _make_handoff_event(seq=2, user_claim='yo sí lo veo'),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'user_needed_to_explain_same_gap' in cats
        f = next(f for f in findings if f.category == 'user_needed_to_explain_same_gap')
        assert f.metadata['frequency'] == 2
        assert f.metadata['last_case']['user_claim'] == 'yo sí lo veo'

    def test_unknown_claim_not_counted(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1, user_claim='unknown'),
            _make_handoff_event(seq=2, user_claim='unknown'),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'user_needed_to_explain_same_gap' not in cats


class TestOSESBrowserDiffers:
    """OSES detects user_browser_differs_from_iabv_session when ≥2
    events mention isolated/controlled session."""

    def test_two_isolated_session_events_detected(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1, mismatch_reason='sesión aislada minimizada'),
            _make_handoff_event(seq=2, mismatch_reason='Chrome for Testing offscreen'),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'user_browser_differs_from_iabv_session' in cats

    def test_detected_via_browser_profile_only(self, tmp_path: Path) -> None:
        """Blocker fix: producer traces browser_profile, not browser_label.
        Detection must work with browser_profile containing 'Chrome for Testing'
        even when mismatch_reason is neutral."""
        events = [
            _make_handoff_event(
                seq=1, mismatch_reason='ventana minimizada',
                browser_label='', browser_profile='Chrome for Testing',
            ),
            _make_handoff_event(
                seq=2, mismatch_reason='ventana offscreen',
                browser_label='', browser_profile='sesión aislada de IABV',
            ),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'user_browser_differs_from_iabv_session' in cats

    def test_detected_via_selected_browser_or_profile(self, tmp_path: Path) -> None:
        """Also works with selected_browser_or_profile field."""
        events = [
            _make_handoff_event(
                seq=1, mismatch_reason='genérico', browser_label='',
                selected_browser_or_profile='Chrome for Testing (controlada)',
            ),
            _make_handoff_event(
                seq=2, mismatch_reason='genérico', browser_label='',
                selected_browser_or_profile='sesión controlada',
            ),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'user_browser_differs_from_iabv_session' in cats


class TestOSESTailReading:
    """OSES reads the 50 most recent events, not the oldest 50."""

    def test_old_events_ignored_when_more_than_50(self, tmp_path: Path) -> None:
        """55 old events with assistant_kind='old_tool' followed by 2 recent
        events with assistant_kind='recent_tool'. The finding last_case must
        reference 'recent_tool', not 'old_tool'."""
        old_events = [
            _make_handoff_event(seq=i, assistant_kind='old_tool')
            for i in range(1, 56)
        ]
        recent_events = [
            _make_handoff_event(seq=100, assistant_kind='recent_tool'),
            _make_handoff_event(seq=101, assistant_kind='recent_tool'),
        ]
        _write_audit_events(tmp_path, old_events + recent_events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        f = next(f for f in findings if f.category == 'repeated_visual_mismatch')
        # last_case must be from the recent events, not the old ones
        assert f.metadata['last_case']['assistant_kind'] == 'recent_tool'

    def test_noise_events_not_counted(self, tmp_path: Path) -> None:
        """Hundreds of non-handoff events should not affect results.
        Only the 2 handoff events at the end matter."""
        noise = [_make_noise_event(seq=i) for i in range(1, 201)]
        handoffs = [
            _make_handoff_event(seq=300, user_claim='a mí sí me funciona'),
            _make_handoff_event(seq=301, user_claim='yo sí lo veo'),
        ]
        _write_audit_events(tmp_path, noise + handoffs)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'user_needed_to_explain_same_gap' in cats
        f = next(f for f in findings if f.category == 'user_needed_to_explain_same_gap')
        assert f.metadata['last_case']['user_claim'] == 'yo sí lo veo'

    def test_large_log_smoke(self, tmp_path: Path) -> None:
        """Smoke test with a large log (500 noise + 3 handoff at end).
        Must not degrade or use stale history."""
        noise = [_make_noise_event(kind='external_query', seq=i) for i in range(1, 501)]
        handoffs = [
            _make_handoff_event(seq=600, blank_probability=0.99),
            _make_handoff_event(seq=601, blank_probability=0.95),
            _make_handoff_event(seq=602, blank_probability=0.92,
                                assistant_kind='gemini'),
        ]
        _write_audit_events(tmp_path, noise + handoffs)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        cats = [f.category for f in findings]
        assert 'black_capture_repeated' in cats
        f = next(f for f in findings if f.category == 'black_capture_repeated')
        assert f.metadata['frequency'] == 3

    def test_tail_window_does_not_count_stale_handoffs(self, tmp_path: Path) -> None:
        """Old handoffs outside the recent tail must not inflate frequency."""
        old_handoffs = [
            _make_handoff_event(seq=i, assistant_kind='old_tool')
            for i in range(1, 11)
        ]
        noise = [
            _make_noise_event(kind='external_query', seq=i)
            for i in range(20, 5120)
        ]
        recent_handoffs = [
            _make_handoff_event(seq=6000, assistant_kind='recent_tool'),
            _make_handoff_event(seq=6001, assistant_kind='recent_tool'),
        ]
        _write_audit_events(tmp_path, old_handoffs + noise + recent_handoffs)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        f = next(f for f in findings if f.category == 'repeated_visual_mismatch')
        assert f.metadata['frequency'] == 2
        assert f.metadata['last_case']['assistant_kind'] == 'recent_tool'


class TestOSESFindingMetadata:
    """Findings must include evidence, frequency, last case,
    recommended action, and priority."""

    def test_finding_has_required_metadata(self, tmp_path: Path) -> None:
        events = [
            _make_handoff_event(seq=1, user_claim='a mí sí me funciona'),
            _make_handoff_event(seq=2, user_claim='yo sí lo veo'),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._shared_reality_handoff_findings()
        for f in findings:
            assert 'pattern' in f.metadata
            assert 'frequency' in f.metadata
            assert 'recommended_action' in f.metadata
            assert 'priority' in f.metadata
            assert f.metadata['frequency'] >= 2
            assert len(f.evidence_refs) > 0
            assert len(f.source_refs) > 0


# ══════════════════════════════════════════════════════════════════════
# PortableContext — no PII, compact export
# ══════════════════════════════════════════════════════════════════════

class TestPortableContextSharedReality:
    """PortableContext _shared_reality_section exports compact summary
    without PII or sensitive file paths."""

    def test_section_with_findings(self) -> None:
        from datetime import datetime, timezone
        from iabv_v15.domain.models import utc_now
        review = {
            'findings': [
                {
                    'category': 'repeated_visual_mismatch',
                    'title': 'Captura visual inútil repetida: 3 eventos',
                    'metadata': {
                        'pattern': 'repeated_visual_mismatch',
                        'frequency': 3,
                        'last_case': {
                            'assistant_kind': 'chatgpt',
                            'target_window_title': 'ChatGPT - Google Chrome for Testing',
                        },
                        'recommended_action': 'auto_restore_or_select_window',
                        'priority': 'high',
                    },
                },
                {
                    'category': 'unrelated_finding',
                    'title': 'Some other finding',
                    'metadata': {},
                },
            ],
        }
        pcs = PortableContextService.__new__(PortableContextService)
        section = pcs._shared_reality_section(review=review, now=utc_now())
        assert section.section_id == 'shared_reality_learning'
        assert len(section.items) == 1
        item = section.items[0]
        assert item['label'] == 'repeated_visual_mismatch'
        assert item['frequency'] == 3
        assert item['last_assistant_kind'] == 'chatgpt'
        assert item['recommended_action'] == 'auto_restore_or_select_window'
        # No PII: no file paths, no hwnd, no rect in exported items
        item_str = json.dumps(item)
        assert 'C:\\' not in item_str
        assert '/home/' not in item_str
        assert '16319628' not in item_str  # hwnd

    def test_section_without_findings(self) -> None:
        from iabv_v15.domain.models import utc_now
        review = {'findings': []}
        pcs = PortableContextService.__new__(PortableContextService)
        section = pcs._shared_reality_section(review=review, now=utc_now())
        assert section.section_id == 'shared_reality_learning'
        assert len(section.items) == 0
        assert 'Sin patrones' in section.summary

    def test_section_filters_only_sr_categories(self) -> None:
        from iabv_v15.domain.models import utc_now
        review = {
            'findings': [
                {'category': 'black_capture_repeated', 'title': 'test', 'metadata': {'frequency': 2, 'last_case': {}, 'recommended_action': 'x', 'priority': 'high'}},
                {'category': 'startup_degradation', 'title': 'unrelated', 'metadata': {}},
                {'category': 'user_needed_to_explain_same_gap', 'title': 'test2', 'metadata': {'frequency': 3, 'last_case': {'assistant_kind': 'gemini'}, 'recommended_action': 'y', 'priority': 'high'}},
            ],
        }
        pcs = PortableContextService.__new__(PortableContextService)
        section = pcs._shared_reality_section(review=review, now=utc_now())
        assert len(section.items) == 2
        labels = {item['label'] for item in section.items}
        assert labels == {'black_capture_repeated', 'user_needed_to_explain_same_gap'}


# ══════════════════════════════════════════════════════════════════════
# platform_pending — no duplicates
# ══════════════════════════════════════════════════════════════════════

class TestPlatformPendingNoDuplicates:
    """platform_pending JSON files must validate and not duplicate tasks."""

    def test_external_visual_handoff_alignment_valid(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_external_visual_handoff_alignment.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'external_visual_handoff_alignment'
        assert 'p05_additions' in task.metadata

    def test_inv_phase_b_visual_metacognition_valid(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_inv_phase_b_visual_metacognition.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'inv_phase_b_visual_metacognition'
        assert 'p05_fix' in task.metadata

    def test_runtime_consulting_lifecycle_recovery_valid(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_consulting_lifecycle_recovery.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert task.id == 'runtime_consulting_lifecycle_recovery'
        assert 'p05_additions' in task.metadata

    def test_external_visual_handoff_has_p07(self) -> None:
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).resolve().parent.parent / 'data' / 'evolution' / 'platform_pending' / 'task_external_visual_handoff_alignment.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        task = PlatformPendingTask.model_validate(data)
        assert 'p07_additions' in task.metadata


# ══════════════════════════════════════════════════════════════════════
# P0.7 — Visual Remediation Learning / OSES Feedback
# ══════════════════════════════════════════════════════════════════════


def _make_remediation_event(
    *,
    assistant_kind: str = 'chatgpt',
    target_window_title: str = 'ChatGPT - Google Chrome for Testing',
    action_taken: str = 'restore_window_by_hwnd',
    capture_useful_after: bool | None = None,
    blank_probability_after: float | None = None,
    proposed_action: str = 'restore_window_by_hwnd',
    detail: str = 'Win32 ShowWindow(16319628, SW_RESTORE)=1',
    remediation_detail_code: str = '',
    remediation_success: bool | None = None,
    result_status: str = 'remediation_available',
    seq: int = 1,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        'assistant_kind': assistant_kind,
        'target_window_title': target_window_title,
        'action_taken': action_taken,
        'capture_useful_after': capture_useful_after,
        'blank_probability_after': blank_probability_after,
        'proposed_action': proposed_action,
        'detail': detail,
        'remediation_detail_code': remediation_detail_code,
        'remediation_success': remediation_success,
        'result_status': result_status,
        'hwnd_present': True,
        'capture_useful_before': False,
        'blank_probability_before': 0.98,
    }
    return {
        'ts': '2026-05-15T10:00:00.000Z',
        'elapsed_ms': 1000.0 * seq,
        'kind': 'visual_remediation_attempted',
        'seq': seq,
        'data': data,
    }


class TestOSESRepeatedRestoreWithoutRecapture:
    """OSES detects repeated_restore_without_recapture when action was taken
    but capture_useful_after is None."""

    def test_two_restores_without_recapture(self, tmp_path: Path) -> None:
        events = [
            _make_remediation_event(seq=1),
            _make_remediation_event(seq=2, assistant_kind='gemini'),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._visual_remediation_findings()
        cats = [f.category for f in findings]
        assert 'repeated_restore_without_recapture' in cats
        f = next(f for f in findings if f.category == 'repeated_restore_without_recapture')
        assert f.metadata['frequency'] == 2
        assert f.metadata['recommended_action'] == 'implement_recapture_after_restore'

    def test_single_event_no_findings(self, tmp_path: Path) -> None:
        events = [_make_remediation_event(seq=1)]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._visual_remediation_findings()
        assert len(findings) == 0


class TestOSESRepeatedWin32Unavailable:
    """OSES detects repeated_win32_restore_unavailable when detail says
    Win32 API not available."""

    def test_two_win32_unavailable(self, tmp_path: Path) -> None:
        events = [
            _make_remediation_event(
                seq=1,
                action_taken='none',
                detail='Win32 API not available (not running on Windows desktop).',
            ),
            _make_remediation_event(
                seq=2,
                action_taken='none',
                detail='Win32 API not available (not running on Windows desktop).',
            ),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._visual_remediation_findings()
        cats = [f.category for f in findings]
        assert 'repeated_win32_restore_unavailable' in cats
        f = next(f for f in findings if f.category == 'repeated_win32_restore_unavailable')
        assert f.metadata['frequency'] == 2

    def test_two_win32_unavailable_from_runtime_trace_code(self, tmp_path: Path) -> None:
        """Runtime producer stores a compact detail code, not raw detail text."""
        events = [
            _make_remediation_event(
                seq=1,
                action_taken='restore_window_by_hwnd',
                detail='',
                remediation_detail_code='win32_api_not_available',
                remediation_success=False,
            ),
            _make_remediation_event(
                seq=2,
                action_taken='restore_window_by_hwnd',
                detail='',
                remediation_detail_code='win32_api_not_available',
                remediation_success=False,
            ),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._visual_remediation_findings()
        cats = [f.category for f in findings]
        assert 'repeated_win32_restore_unavailable' in cats


class TestOSESRepeatedUserSelectionNeeded:
    """OSES detects repeated_user_selection_needed when proposed_action
    is request_user_selection."""

    def test_two_user_selections(self, tmp_path: Path) -> None:
        events = [
            _make_remediation_event(
                seq=1,
                proposed_action='request_user_selection',
                action_taken='none',
            ),
            _make_remediation_event(
                seq=2,
                proposed_action='request_user_selection',
                action_taken='none',
            ),
        ]
        _write_audit_events(tmp_path, events)
        oses = _make_oses(tmp_path)
        findings = oses._visual_remediation_findings()
        cats = [f.category for f in findings]
        assert 'repeated_user_selection_needed' in cats
        f = next(f for f in findings if f.category == 'repeated_user_selection_needed')
        assert f.metadata['frequency'] == 2


class TestOSESStaleEventsNotContaminate:
    """Log with 60 old noise events + 2 recent remediation events must
    detect only the recent ones. last_case must point to the newest."""

    def test_recent_events_not_contaminated_by_old(self, tmp_path: Path) -> None:
        old_events = [_make_noise_event(seq=i) for i in range(1, 61)]
        recent = [
            _make_remediation_event(seq=100),
            _make_remediation_event(seq=101, assistant_kind='gemini'),
        ]
        _write_audit_events(tmp_path, old_events + recent)
        oses = _make_oses(tmp_path)
        findings = oses._visual_remediation_findings()
        cats = [f.category for f in findings]
        assert 'repeated_restore_without_recapture' in cats
        f = next(f for f in findings if f.category == 'repeated_restore_without_recapture')
        assert f.metadata['last_case']['assistant_kind'] == 'gemini'


class TestPortableContextRemediationNoPII:
    """PortableContext exports remediation findings without PII."""

    def test_remediation_section_no_hwnd_no_paths(self, tmp_path: Path) -> None:
        review: dict[str, Any] = {
            'findings': [
                {
                    'category': 'repeated_restore_without_recapture',
                    'title': 'Restauración sin recaptura: 3 eventos',
                    'metadata': {
                        'pattern': 'repeated_restore_without_recapture',
                        'frequency': 3,
                        'last_case': {
                            'assistant_kind': 'chatgpt',
                            'action_taken': 'restore_window_by_hwnd',
                        },
                        'recommended_action': 'implement_recapture_after_restore',
                        'priority': 'high',
                    },
                },
                {
                    'category': 'repeated_win32_restore_unavailable',
                    'title': 'Win32 restore no disponible: 2 eventos',
                    'metadata': {
                        'pattern': 'repeated_win32_restore_unavailable',
                        'frequency': 2,
                        'recommended_action': 'environment_limitation_marker',
                        'priority': 'medium',
                    },
                },
            ],
        }
        storage = ArtifactStorage(root=str(tmp_path / 'data'))
        pcs = PortableContextService(
            workspace_root=str(tmp_path),
            storage=storage,
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        section = pcs._shared_reality_section(review=review, now=now)
        assert len(section.items) == 2
        section_str = json.dumps([item for item in section.items])
        assert 'hwnd' not in section_str.lower() or 'unknown' in section_str.lower()
        assert 'C:\\' not in section_str
        assert '/home/' not in section_str
        assert section.summary
        assert 'remediación' in section.summary.lower() or 'mismatch' in section.summary.lower()

        for item in section.items:
            assert 'label' in item
            assert 'frequency' in item
            assert 'recommended_action' in item
