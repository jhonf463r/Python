"""Tests for IA-IA coordination pattern detection (Brecha 3.2).

Covers: SPECIALIZATION, FALLBACK, COMPLEMENTARY detection,
ia_trace_summary integration, StrategySelector boost, digest exposure,
and edge cases (empty runs, below threshold).
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import (
    ControlMasterDigest,
    ControlMasterState,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRecommendation,
    ExperimentRun,
    EvaluationRoute,
    PortableContextSection,
    utc_now,
)
from iabv_v15.services.evolution.control_master_digest_builder import (
    ControlMasterDigestBuilder,
    _render_coordination_patterns,
)
from iabv_v15.services.evolution.portable_context_service import (
    PortableContextService,
)
from iabv_v15.services.lab.strategy_selector import StrategySelector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(
    *,
    domain: ExperimentDomain = ExperimentDomain.CODE,
    assistant: str = 'gemini',
    success: bool = True,
    route: EvaluationRoute = EvaluationRoute.CLOUD,
    scope_key: str = '',
    age_days: int = 0,
    score: float = 0.8,
) -> ExperimentRun:
    return ExperimentRun(
        domain=domain,
        suite_name='coordination_test',
        objective='test coordination',
        route=route,
        assistant_kind=assistant,
        success=success,
        metrics=ExperimentMetric(total_score=score),
        metadata={'comparison_scope_key': scope_key} if scope_key else {},
        created_at_utc=utc_now() - timedelta(days=age_days),
    )


def _make_service() -> PortableContextService:
    storage = MagicMock()
    return PortableContextService(
        workspace_root='/tmp/test',
        storage=storage,
    )


# ---------------------------------------------------------------------------
# 1. test_specialization_detected
# ---------------------------------------------------------------------------

def test_specialization_detected():
    """IA with >70% success in a domain AND >20% above avg -> SPECIALIZATION."""
    svc = _make_service()
    runs = [
        # gemini: 8 successes in CODE -> 100% success
        *[_make_run(domain=ExperimentDomain.CODE, assistant='gemini', success=True) for _ in range(8)],
        # chatgpt: 5 failures in CODE -> 0% success
        *[_make_run(domain=ExperimentDomain.CODE, assistant='chatgpt', success=False) for _ in range(5)],
    ]
    patterns = svc._detect_coordination_patterns(runs)
    spec_patterns = [p for p in patterns if p['pattern_type'] == 'SPECIALIZATION']
    assert len(spec_patterns) >= 1
    assert spec_patterns[0]['primary_ia'] == 'gemini'
    assert spec_patterns[0]['domain'] == ExperimentDomain.CODE.value
    assert spec_patterns[0]['sample_size'] == 8
    assert spec_patterns[0]['confidence'] > 0.0


# ---------------------------------------------------------------------------
# 2. test_no_specialization_below_threshold
# ---------------------------------------------------------------------------

def test_no_specialization_below_threshold():
    """<5 runs for an assistant -> no SPECIALIZATION pattern emitted."""
    svc = _make_service()
    runs = [
        # gemini: only 3 runs (below threshold of 5)
        *[_make_run(domain=ExperimentDomain.CODE, assistant='gemini', success=True) for _ in range(3)],
        # chatgpt: only 4 runs
        *[_make_run(domain=ExperimentDomain.CODE, assistant='chatgpt', success=False) for _ in range(4)],
    ]
    patterns = svc._detect_coordination_patterns(runs)
    spec_patterns = [p for p in patterns if p['pattern_type'] == 'SPECIALIZATION']
    assert len(spec_patterns) == 0


# ---------------------------------------------------------------------------
# 3. test_fallback_detected
# ---------------------------------------------------------------------------

def test_fallback_detected():
    """IA-A fails + IA-B succeeds on same scope_key >= 3 times -> FALLBACK."""
    svc = _make_service()
    runs = []
    for i in range(4):
        scope = f'scope_{i}'
        runs.append(_make_run(assistant='chatgpt', success=False, scope_key=scope))
        runs.append(_make_run(assistant='gemini', success=True, scope_key=scope))
    patterns = svc._detect_coordination_patterns(runs)
    fallback_patterns = [p for p in patterns if p['pattern_type'] == 'FALLBACK']
    assert len(fallback_patterns) >= 1
    fb = fallback_patterns[0]
    assert fb['primary_ia'] == 'chatgpt'
    assert fb['secondary_ia'] == 'gemini'
    assert fb['sample_size'] >= 3


# ---------------------------------------------------------------------------
# 4. test_complementary_detected
# ---------------------------------------------------------------------------

def test_complementary_detected():
    """Different IAs win in different domains -> COMPLEMENTARY."""
    svc = _make_service()
    runs = [
        # gemini wins CODE (5 successes)
        *[_make_run(domain=ExperimentDomain.CODE, assistant='gemini', success=True) for _ in range(5)],
        # chatgpt wins LANGUAGE (5 successes)
        *[_make_run(domain=ExperimentDomain.LANGUAGE, assistant='chatgpt', success=True) for _ in range(5)],
        # cross-failures to ensure no single winner
        *[_make_run(domain=ExperimentDomain.CODE, assistant='chatgpt', success=False) for _ in range(3)],
        *[_make_run(domain=ExperimentDomain.LANGUAGE, assistant='gemini', success=False) for _ in range(3)],
    ]
    patterns = svc._detect_coordination_patterns(runs)
    comp_patterns = [p for p in patterns if p['pattern_type'] == 'COMPLEMENTARY']
    assert len(comp_patterns) >= 1
    cp = comp_patterns[0]
    assert 'chatgpt' in (cp['primary_ia'], cp['secondary_ia'])
    assert 'gemini' in (cp['primary_ia'], cp['secondary_ia'])


# ---------------------------------------------------------------------------
# 5. test_patterns_included_in_ia_trace_summary
# ---------------------------------------------------------------------------

def test_patterns_included_in_ia_trace_summary():
    """Portable context package metadata includes coordination_patterns."""
    svc = _make_service()
    repo_mock = MagicMock()
    runs = [
        *[_make_run(domain=ExperimentDomain.CODE, assistant='gemini', success=True) for _ in range(8)],
        *[_make_run(domain=ExperimentDomain.CODE, assistant='chatgpt', success=False) for _ in range(5)],
    ]
    repo_mock.list_runs.return_value = runs
    repo_mock.list_recommendations.return_value = []
    svc.experiment_lab_repository = repo_mock

    package = svc.build_package()
    coordination = package.metadata.get('coordination_patterns')
    assert coordination is not None
    assert isinstance(coordination, list)
    assert len(coordination) >= 1

    # Also check the section exists
    section_ids = [s.section_id for s in package.sections]
    assert 'coordination_patterns' in section_ids


# ---------------------------------------------------------------------------
# 6. test_strategy_selector_uses_specialization
# ---------------------------------------------------------------------------

def test_strategy_selector_uses_specialization():
    """StrategySelector boosts confidence when SPECIALIZATION pattern matches."""
    selector = StrategySelector()
    runs = [
        ExperimentRun(
            domain=ExperimentDomain.CODE,
            suite_name='test',
            objective='test',
            route=EvaluationRoute.CLOUD,
            assistant_kind='gemini',
            success=True,
            metrics=ExperimentMetric(total_score=0.9),
        )
        for _ in range(5)
    ]
    # Without coordination patterns
    rec_without = selector.recommend(
        domain=ExperimentDomain.CODE,
        subject_key='test',
        candidate_runs=runs,
    )
    # With matching SPECIALIZATION pattern
    patterns = [{
        'pattern_type': 'SPECIALIZATION',
        'primary_ia': 'gemini',
        'secondary_ia': None,
        'domain': 'code',
        'confidence': 0.9,
        'sample_size': 10,
        'description': 'gemini specializes in code.',
    }]
    rec_with = selector.recommend(
        domain=ExperimentDomain.CODE,
        subject_key='test',
        candidate_runs=runs,
        coordination_patterns=patterns,
    )
    assert rec_with.confidence >= rec_without.confidence
    assert 'SPECIALIZATION' in rec_with.rationale


# ---------------------------------------------------------------------------
# 7. test_empty_runs_returns_empty_patterns
# ---------------------------------------------------------------------------

def test_empty_runs_returns_empty_patterns():
    """No data -> empty list of patterns."""
    svc = _make_service()
    patterns = svc._detect_coordination_patterns([])
    assert patterns == []


# ---------------------------------------------------------------------------
# 8. test_patterns_exposed_in_digest
# ---------------------------------------------------------------------------

def test_patterns_exposed_in_digest():
    """ControlMasterDigest includes coordination_patterns_brief."""
    builder = ControlMasterDigestBuilder()
    state = ControlMasterState(current_vision='test vision')
    patterns = [
        {
            'pattern_type': 'SPECIALIZATION',
            'primary_ia': 'gemini',
            'secondary_ia': None,
            'domain': 'code',
            'confidence': 0.9,
            'sample_size': 10,
            'description': 'gemini specializes in code.',
        },
        {
            'pattern_type': 'FALLBACK',
            'primary_ia': 'chatgpt',
            'secondary_ia': 'gemini',
            'domain': 'cross-domain',
            'confidence': 0.7,
            'sample_size': 5,
            'description': 'chatgpt fails, gemini succeeds.',
        },
    ]
    digest = builder.build(state, coordination_patterns=patterns)
    assert digest.coordination_patterns_brief != ''
    assert 'gemini' in digest.coordination_patterns_brief
    assert 'specialist' in digest.coordination_patterns_brief
    assert 'fallback' in digest.coordination_patterns_brief


# ---------------------------------------------------------------------------
# Edge case: _render_coordination_patterns with None/empty
# ---------------------------------------------------------------------------

def test_render_coordination_patterns_empty():
    assert _render_coordination_patterns(None) == ''
    assert _render_coordination_patterns([]) == ''
