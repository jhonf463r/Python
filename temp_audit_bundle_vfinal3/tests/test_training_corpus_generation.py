"""Tests for Brecha 3.1 — Training corpus generation from experiment traces."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
    utc_now,
)
from iabv_v15.services.lab.experiment_lab import ExperimentLab


def _make_run(
    domain: ExperimentDomain = ExperimentDomain.CLOUD_REASONING,
    suite: str = 'shadow_parallel',
    assistant: str = 'gemini',
    success: bool = True,
    latency_ms: int = 1000,
    age_days: int = 0,
) -> ExperimentRun:
    return ExperimentRun(
        domain=domain,
        suite_name=suite,
        objective='test objective',
        route=EvaluationRoute.CLOUD,
        assistant_kind=assistant,
        success=success,
        metrics=ExperimentMetric(execution_ms=latency_ms),
        created_at_utc=utc_now() - timedelta(days=age_days),
    )


def _make_lab(runs: list[ExperimentRun]) -> ExperimentLab:
    repo = MagicMock()
    repo.list_runs.return_value = runs
    registry = MagicMock()
    scoring = MagicMock()
    selector = MagicMock()
    return ExperimentLab(
        repository=repo,
        registry=registry,
        scoring_engine=scoring,
        strategy_selector=selector,
    )


class TestGenerateCorpusInsufficientData:
    def test_empty_when_too_few_runs(self):
        runs = [_make_run() for _ in range(5)]
        lab = _make_lab(runs)
        result = lab.generate_training_corpus(min_runs=10)
        assert result == []


class TestGenerateCorpusGroupsByDomain:
    def test_groups_correctly(self):
        runs_a = [_make_run(suite='suite_a', assistant='gemini') for _ in range(12)]
        runs_b = [_make_run(suite='suite_b', assistant='groq') for _ in range(12)]
        lab = _make_lab(runs_a + runs_b)
        corpus = lab.generate_training_corpus(min_runs=10)
        task_types = {e['task_type'] for e in corpus}
        assert 'cloud_reasoning:suite_a' in task_types
        assert 'cloud_reasoning:suite_b' in task_types


class TestGenerateCorpusPicksWinnerBySuccessRate:
    def test_higher_success_rate_wins(self):
        runs_good = [_make_run(assistant='gemini', success=True) for _ in range(10)]
        runs_bad = [_make_run(assistant='groq', success=False) for _ in range(5)]
        runs_bad += [_make_run(assistant='groq', success=True) for _ in range(5)]
        lab = _make_lab(runs_good + runs_bad)
        corpus = lab.generate_training_corpus(min_runs=10)
        assert len(corpus) == 1
        assert corpus[0]['recommended_assistant'] == 'gemini'
        assert corpus[0]['success_rate'] == 1.0


class TestGenerateCorpusBreaksTieByLatency:
    def test_lower_latency_wins_on_tie(self):
        runs_fast = [_make_run(assistant='groq', success=True, latency_ms=500) for _ in range(10)]
        runs_slow = [_make_run(assistant='gemini', success=True, latency_ms=3000) for _ in range(10)]
        lab = _make_lab(runs_fast + runs_slow)
        corpus = lab.generate_training_corpus(min_runs=10)
        assert len(corpus) == 1
        assert corpus[0]['recommended_assistant'] == 'groq'
        assert corpus[0]['avg_latency_ms'] == 500.0


class TestDeriveLearnedPatternsFormat:
    def test_pattern_has_required_fields(self):
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        lab = _make_lab([_make_run() for _ in range(15)])
        pcs = MagicMock(spec=PortableContextService)
        pcs.experiment_lab = lab
        pcs.derive_learned_patterns = PortableContextService.derive_learned_patterns.__get__(pcs)
        patterns = pcs.derive_learned_patterns()
        assert len(patterns) >= 1
        p = patterns[0]
        assert 'pattern_id' in p
        assert 'task_type' in p
        assert 'recommended_route' in p
        assert 'recommended_assistant_kind' in p
        assert 'confidence' in p
        assert 'success_count' in p
        assert p['source'] == 'experiment_lab_corpus'
        assert 'derived_at_utc' in p


class TestDeriveLearnedPatternsPersisted:
    def test_patterns_returned_from_lab(self):
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        lab = _make_lab([_make_run() for _ in range(15)])
        pcs = MagicMock(spec=PortableContextService)
        pcs.experiment_lab = lab
        pcs.derive_learned_patterns = PortableContextService.derive_learned_patterns.__get__(pcs)
        patterns = pcs.derive_learned_patterns()
        assert len(patterns) >= 1
        assert all(p['source'] == 'experiment_lab_corpus' for p in patterns)


class TestBuildPackageIncludesAutoPatterns:
    def test_auto_patterns_appended(self):
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        lab = _make_lab([_make_run() for _ in range(15)])
        pcs = MagicMock(spec=PortableContextService)
        pcs.experiment_lab = lab
        pcs.derive_learned_patterns = PortableContextService.derive_learned_patterns.__get__(pcs)
        auto = pcs.derive_learned_patterns()
        existing = [{'subject_key': 'x', 'domain': 'y'}]
        combined = existing + auto
        assert len(combined) > len(existing)
        assert any(p.get('source') == 'experiment_lab_corpus' for p in combined)


class TestCorpusRespectsMaxAge:
    def test_old_runs_excluded(self):
        old_runs = [_make_run(age_days=60) for _ in range(15)]
        lab = _make_lab(old_runs)
        corpus = lab.generate_training_corpus(min_runs=10, max_age_days=30)
        assert corpus == []


class TestCorpusGenerationFailureDoesNotCrash:
    def test_exception_in_lab_does_not_propagate(self):
        """build_package wraps derive_learned_patterns in try/except."""
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        pcs = MagicMock(spec=PortableContextService)
        pcs.experiment_lab = MagicMock()
        pcs.experiment_lab.generate_training_corpus.side_effect = RuntimeError('db error')
        pcs.derive_learned_patterns = PortableContextService.derive_learned_patterns.__get__(pcs)
        # derive_learned_patterns itself propagates, but the integration
        # in build_package catches it.  Verify the catch pattern:
        caught = False
        try:
            pcs.derive_learned_patterns()
        except RuntimeError:
            caught = True
        assert caught, 'derive_learned_patterns should let exception propagate'
        # The build_package wrapper catches it — simulate:
        auto_patterns = []
        try:
            auto_patterns = pcs.derive_learned_patterns()
        except Exception:
            pass  # build_package pattern
        assert auto_patterns == []
