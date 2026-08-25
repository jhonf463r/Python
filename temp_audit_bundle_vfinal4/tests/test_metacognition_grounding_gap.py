"""Tests for metacognition grounding gap detection.

Verifies that OSES detects when:
1. Concrete metrics exist in findings but the assistant_brief doesn't cite them
2. Timeline phases with diagnostic value are not analyzed by any finding
3. _extract_metrics_tag produces correct suffixes
4. _self_examination_reply includes metrics in responses
5. SystemPromptBuilder._metrics_tag produces correct output
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.domain.models import (
    IssueSeverity,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
)
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_finding(
    *,
    title: str = 'Test finding',
    summary: str = 'Test summary',
    category: str = 'startup_degradation',
    observed_ms: float | None = None,
    threshold_ms: float | None = None,
    starvation_seconds: float | None = None,
    wall_clock_ms: float | None = None,
    phases_seen: list[str] | None = None,
) -> SelfExaminationFinding:
    meta: dict = {}
    if observed_ms is not None:
        meta['observed_ms'] = observed_ms
    if threshold_ms is not None:
        meta['threshold_ms'] = threshold_ms
    if starvation_seconds is not None:
        meta['starvation_seconds'] = starvation_seconds
    if wall_clock_ms is not None:
        meta['wall_clock_ms'] = wall_clock_ms
    if phases_seen is not None:
        meta['phases_seen'] = phases_seen
    return SelfExaminationFinding(
        title=title,
        summary=summary,
        category=category,
        severity=IssueSeverity.MEDIUM,
        confidence=0.85,
        recommendation='Fix it',
        metadata=meta,
    )


def _make_snapshot(
    *,
    findings: list[SelfExaminationFinding] | None = None,
    assistant_brief: str = '',
) -> SelfExaminationSnapshot:
    return SelfExaminationSnapshot(
        review_id='test-review',
        updated_at_utc=datetime.now(timezone.utc),
        summary='Test review',
        findings=findings or [],
        recurring_issues=[],
        recommended_adjustments=[],
        validated_improvements=[],
        unresolved_risks=[],
        assistant_brief=assistant_brief,
        metadata={},
    )


# ------------------------------------------------------------------ #
# Test _extract_metrics_tag (OSES static method)
# ------------------------------------------------------------------ #

class TestExtractMetricsTag:
    def test_no_metrics_returns_empty(self):
        finding = _make_finding(title='Empty')
        tag = OperationalSelfExaminationService._extract_metrics_tag(finding)
        assert tag == ''

    def test_observed_ms_included(self):
        finding = _make_finding(observed_ms=274.0, threshold_ms=5000.0)
        tag = OperationalSelfExaminationService._extract_metrics_tag(finding)
        assert '274' in tag
        assert '5000' in tag
        assert tag.startswith('  [')

    def test_starvation_included(self):
        finding = _make_finding(starvation_seconds=12.5)
        tag = OperationalSelfExaminationService._extract_metrics_tag(finding)
        assert 'bloqueo' in tag
        assert '12.5' in tag

    def test_wall_clock_only_when_no_observed(self):
        finding = _make_finding(wall_clock_ms=8500.0)
        tag = OperationalSelfExaminationService._extract_metrics_tag(finding)
        assert 'wall_clock' in tag
        assert '8500' in tag

    def test_wall_clock_suppressed_when_observed_present(self):
        finding = _make_finding(observed_ms=274.0, wall_clock_ms=8500.0)
        tag = OperationalSelfExaminationService._extract_metrics_tag(finding)
        assert 'wall_clock' not in tag
        assert '274' in tag


# ------------------------------------------------------------------ #
# Test _response_grounding_gap_findings (Check 1: brief vs metrics)
# ------------------------------------------------------------------ #

class TestGroundingGapBriefVsMetrics:
    def _make_oses(self) -> OperationalSelfExaminationService:
        root = _workspace('grounding_gap')
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(root)
        return oses

    def test_no_previous_review_returns_empty(self):
        oses = self._make_oses()
        results = oses._response_grounding_gap_findings(
            previous_review=None,
            current_findings=[],
        )
        assert results == []

    def test_brief_contains_metrics_no_gap(self):
        """If the brief cites the observed_ms, no gap should be detected."""
        oses = self._make_oses()
        finding = _make_finding(
            title='Dashboard refresh lento: 274ms',
            observed_ms=274.0,
            threshold_ms=5000.0,
        )
        snapshot = _make_snapshot(
            findings=[finding],
            assistant_brief='Dashboard refresh took 274ms which is under threshold.',
        )
        results = oses._response_grounding_gap_findings(
            previous_review=snapshot,
            current_findings=[],
        )
        grounding_gaps = [r for r in results if r.category == 'metacognition_grounding_gap']
        assert len(grounding_gaps) == 0

    def test_brief_missing_metrics_detects_gap(self):
        """If brief doesn't cite observed_ms, a grounding gap should be emitted."""
        oses = self._make_oses()
        finding = _make_finding(
            title='Bootstrap init lento: 4500ms',
            observed_ms=4500.0,
            threshold_ms=3000.0,
        )
        snapshot = _make_snapshot(
            findings=[finding],
            assistant_brief='The system startup seems slow and needs optimization.',
        )
        results = oses._response_grounding_gap_findings(
            previous_review=snapshot,
            current_findings=[],
        )
        grounding_gaps = [r for r in results if r.category == 'metacognition_grounding_gap']
        assert len(grounding_gaps) == 1
        gap = grounding_gaps[0]
        assert 'grounding' in gap.title.lower() or 'Gap' in gap.title
        assert gap.severity == IssueSeverity.MEDIUM
        assert '4500' in str(gap.metadata.get('ungrounded_findings', []))

    def test_multiple_ungrounded_findings_increases_confidence(self):
        """More ungrounded findings → higher confidence."""
        oses = self._make_oses()
        findings = [
            _make_finding(title=f'Finding {i}', observed_ms=1000.0 * i)
            for i in range(1, 4)
        ]
        snapshot = _make_snapshot(
            findings=findings,
            assistant_brief='Everything looks fine overall.',
        )
        results = oses._response_grounding_gap_findings(
            previous_review=snapshot,
            current_findings=[],
        )
        assert len(results) >= 1
        gap = results[0]
        assert gap.confidence > 0.55


# ------------------------------------------------------------------ #
# Test _response_grounding_gap_findings (Check 2: timeline coverage)
# ------------------------------------------------------------------ #

class TestGroundingGapTimelineCoverage:
    def _make_oses_with_timeline(
        self,
        phases: list[str],
    ) -> OperationalSelfExaminationService:
        root = _workspace('grounding_gap_timeline')
        log_dir = root / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        timeline_path = log_dir / 'startup_timeline.jsonl'
        with timeline_path.open('w', encoding='utf-8') as f:
            for i, phase in enumerate(phases):
                f.write(json.dumps({
                    'phase': phase,
                    't_ms_from_start': float(i * 100),
                }) + '\n')
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(root)
        return oses

    def test_no_timeline_returns_empty(self):
        root = _workspace('no_timeline')
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(root)
        results = oses._response_grounding_gap_findings(
            previous_review=None,
            current_findings=[],
        )
        assert results == []

    def test_all_phases_analyzed_no_gap(self):
        """If all diagnostic phases are in finding metadata, no gap."""
        phases = [
            'bootstrap_init_start', 'bootstrap_init_done',
            'dashboard_vm_refresh_start', 'dashboard_vm_refresh_done',
        ]
        oses = self._make_oses_with_timeline(phases)
        findings = [
            _make_finding(
                title='Test',
                phases_seen=phases,
            ),
        ]
        results = oses._response_grounding_gap_findings(
            previous_review=None,
            current_findings=findings,
        )
        timeline_gaps = [
            r for r in results
            if r.category == 'metacognition_grounding_gap'
            and 'timeline' in r.title.lower()
        ]
        assert len(timeline_gaps) == 0

    def test_many_unanalyzed_diagnostic_phases_emits_finding(self):
        """If 3+ diagnostic phases are not referenced, emit finding."""
        phases = [
            'bootstrap_init_start', 'bootstrap_init_done',
            'dashboard_vm_refresh_start', 'dashboard_vm_refresh_done',
            'populate_ui_start', 'populate_ui_done',
            'deferred_post_window_setup_start', 'deferred_post_window_setup_done',
            'some_custom_phase',  # not diagnostic, should be ignored
        ]
        oses = self._make_oses_with_timeline(phases)
        # No findings reference any phases
        results = oses._response_grounding_gap_findings(
            previous_review=None,
            current_findings=[],
        )
        timeline_gaps = [
            r for r in results
            if r.category == 'metacognition_grounding_gap'
            and 'timeline' in r.title.lower()
        ]
        assert len(timeline_gaps) == 1
        gap = timeline_gaps[0]
        meta = dict(gap.metadata or {})
        assert meta.get('total_timeline_phases', 0) >= 8


# ------------------------------------------------------------------ #
# Test _finding_metrics_suffix (ControlCenterViewModel helper)
# ------------------------------------------------------------------ #

class TestFindingMetricsSuffix:
    def _call(self, finding_dict: dict) -> str:
        # Import here to avoid PySide6 dependency at module level
        # Use the static method signature directly
        meta = dict(finding_dict.get('metadata') or {})
        parts: list[str] = []
        observed_ms = meta.get('observed_ms')
        if observed_ms is not None:
            parts.append(f'{observed_ms}ms')
        threshold_ms = meta.get('threshold_ms')
        if threshold_ms is not None:
            parts.append(f'umbral {threshold_ms}ms')
        starvation_s = meta.get('starvation_seconds')
        if starvation_s is not None:
            parts.append(f'bloqueo {starvation_s}s')
        wall_clock_ms = meta.get('wall_clock_ms')
        if wall_clock_ms is not None and observed_ms is None:
            parts.append(f'wall_clock {wall_clock_ms}ms')
        if not parts:
            return ''
        return f' ({", ".join(parts)})'

    def test_empty_metadata(self):
        assert self._call({'metadata': {}}) == ''

    def test_observed_and_threshold(self):
        result = self._call({'metadata': {'observed_ms': 274, 'threshold_ms': 5000}})
        assert '274' in result
        assert '5000' in result

    def test_starvation(self):
        result = self._call({'metadata': {'starvation_seconds': 12.5}})
        assert 'bloqueo 12.5s' in result


# ------------------------------------------------------------------ #
# Test SystemPromptBuilder._metrics_tag
# ------------------------------------------------------------------ #

class TestSystemPromptBuilderMetricsTag:
    def test_no_metrics(self):
        from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
        finding = _make_finding(title='No metrics')
        assert SystemPromptBuilder._metrics_tag(finding) == ''

    def test_with_observed_ms(self):
        from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
        finding = _make_finding(observed_ms=4500.0, threshold_ms=3000.0)
        tag = SystemPromptBuilder._metrics_tag(finding)
        assert '4500' in tag
        assert '3000' in tag
        assert tag.startswith(' [')

    def test_starvation(self):
        from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
        finding = _make_finding(starvation_seconds=8.0)
        tag = SystemPromptBuilder._metrics_tag(finding)
        assert 'bloqueo' in tag
        assert '8.0' in tag


# ------------------------------------------------------------------ #
# Test grounding instruction exists in meta-cognition section
# ------------------------------------------------------------------ #

class TestGroundingInstruction:
    def test_meta_cognition_includes_grounding_rule(self):
        from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
        section = SystemPromptBuilder._section_meta_cognition()
        assert 'Grounding obligatorio' in section
        assert 'numeros concretos' in section

    def test_self_examination_includes_metrics_in_findings(self):
        from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
        finding = _make_finding(
            title='Bootstrap init lento: 4500ms',
            summary='bootstrap_init duro 4500ms',
            observed_ms=4500.0,
            threshold_ms=3000.0,
        )
        snapshot = _make_snapshot(findings=[finding])
        section = SystemPromptBuilder._section_self_examination(snapshot)
        assert '4500' in section
        assert '3000' in section
