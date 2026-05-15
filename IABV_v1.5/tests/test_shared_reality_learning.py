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
    seq: int = 1,
) -> dict[str, Any]:
    return {
        'ts': '2026-05-15T10:00:00.000Z',
        'elapsed_ms': 1000.0 * seq,
        'kind': 'shared_reality_handoff',
        'seq': seq,
        'data': {
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
        },
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
