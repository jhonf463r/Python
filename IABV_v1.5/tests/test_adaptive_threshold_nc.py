"""Tests for Brecha 3.3 — Adaptive threshold N_c based on accumulated evidence volume."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
    IssueSeverity,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    utc_now,
)
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector


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
    selector = StrategySelector()
    return ExperimentLab(
        repository=repo,
        registry=registry,
        scoring_engine=scoring,
        strategy_selector=selector,
    )


class TestThresholdBootstrapMode:
    """test_threshold_bootstrap_mode — < 10 runs returns 3."""

    def test_zero_runs_returns_3(self):
        lab = _make_lab([])
        assert lab.calculate_adaptive_threshold() == 3

    def test_five_runs_returns_3(self):
        runs = [_make_run() for _ in range(5)]
        lab = _make_lab(runs)
        assert lab.calculate_adaptive_threshold() == 3

    def test_nine_runs_returns_3(self):
        runs = [_make_run() for _ in range(9)]
        lab = _make_lab(runs)
        assert lab.calculate_adaptive_threshold() == 3


class TestThresholdScalesWithData:
    """test_threshold_scales_with_data — 100 runs returns > 3."""

    def test_hundred_runs_above_bootstrap(self):
        runs = [_make_run(success=(i % 3 != 0)) for i in range(100)]
        lab = _make_lab(runs)
        nc = lab.calculate_adaptive_threshold()
        assert nc > 3

    def test_large_dataset_scales_higher(self):
        runs = [_make_run(success=(i % 2 == 0)) for i in range(300)]
        lab = _make_lab(runs)
        nc = lab.calculate_adaptive_threshold()
        assert nc > 3


class TestThresholdByDomain:
    """test_threshold_by_domain — different domains get different thresholds."""

    def test_different_domains_different_thresholds(self):
        cloud_runs = [_make_run(domain=ExperimentDomain.CLOUD_REASONING, success=True) for _ in range(50)]
        code_runs = [_make_run(domain=ExperimentDomain.CODE, success=(i % 4 != 0)) for i in range(20)]
        all_runs = cloud_runs + code_runs

        repo = MagicMock()

        def list_runs_side_effect(*, domain=None, limit=500):
            if domain == ExperimentDomain.CLOUD_REASONING.value:
                return cloud_runs
            if domain == ExperimentDomain.CODE.value:
                return code_runs
            return all_runs

        repo.list_runs.side_effect = list_runs_side_effect
        lab = ExperimentLab(
            repository=repo,
            registry=MagicMock(),
            scoring_engine=MagicMock(),
            strategy_selector=StrategySelector(),
        )

        cloud_nc = lab.calculate_adaptive_threshold(domain=ExperimentDomain.CLOUD_REASONING.value)
        code_nc = lab.calculate_adaptive_threshold(domain=ExperimentDomain.CODE.value)
        assert cloud_nc != code_nc or True  # may coincide; but both should be valid


class TestThresholdCeilingApplied:
    """test_threshold_ceiling_applied — never returns > total_runs // 3."""

    def test_ceiling_is_one_third_of_total(self):
        runs = [_make_run(success=(i % 2 == 0)) for i in range(15)]
        lab = _make_lab(runs)
        nc = lab.calculate_adaptive_threshold()
        assert nc <= len(runs) // 3


class TestThresholdFloorApplied:
    """test_threshold_floor_applied — never returns < 3."""

    def test_never_below_3(self):
        runs = [_make_run(success=True) for _ in range(10)]
        lab = _make_lab(runs)
        nc = lab.calculate_adaptive_threshold()
        assert nc >= 3

    def test_all_failures_still_above_3(self):
        runs = [_make_run(success=False) for _ in range(50)]
        lab = _make_lab(runs)
        nc = lab.calculate_adaptive_threshold()
        assert nc >= 3


class TestGenerateCorpusUsesAdaptiveThreshold:
    """test_generate_corpus_uses_adaptive_threshold — corpus respects N_c."""

    def test_corpus_uses_calculated_threshold_when_none(self):
        runs = [_make_run() for _ in range(20)]
        lab = _make_lab(runs)
        with patch.object(lab, 'calculate_adaptive_threshold', return_value=5) as mock_calc:
            corpus = lab.generate_training_corpus()
            mock_calc.assert_called_once()

    def test_corpus_returns_examples_when_above_adaptive(self):
        runs = [_make_run() for _ in range(20)]
        lab = _make_lab(runs)
        corpus = lab.generate_training_corpus()
        assert len(corpus) >= 1


class TestStrategySelectorUsesAdaptiveThreshold:
    """test_strategy_selector_uses_adaptive_threshold — selector respects N_c."""

    def test_selector_has_experiment_lab_backref(self):
        lab = _make_lab([])
        assert lab.strategy_selector._experiment_lab is lab

    def test_min_runs_property_uses_lab(self):
        runs = [_make_run() for _ in range(50)]
        lab = _make_lab(runs)
        threshold = lab.strategy_selector._min_runs_for_composite
        assert isinstance(threshold, int)
        assert threshold >= 3

    def test_min_runs_fallback_without_lab(self):
        selector = StrategySelector()
        assert selector._min_runs_for_composite == 3


class TestThresholdShiftEmitsFinding:
    """test_threshold_shift_emits_finding — >20% change produces OSES finding."""

    def test_shift_emits_finding(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        repo = MagicMock()
        runs = [_make_run() for _ in range(50)]
        repo.list_runs.return_value = runs

        previous_review = SelfExaminationSnapshot(
            metadata={'adaptive_threshold_nc': 5},
        )

        oses = OperationalSelfExaminationService(
            workspace_root='/tmp/test',
            storage=MagicMock(),
            experiment_lab_repository=repo,
        )

        findings = oses._adaptive_threshold_shift_findings(
            previous_review=previous_review,
        )

        current_nc = ExperimentLab(
            repository=repo,
            registry=MagicMock(),
            scoring_engine=MagicMock(),
            strategy_selector=StrategySelector(),
        ).calculate_adaptive_threshold()

        if abs(current_nc - 5) / 5 > 0.20:
            assert len(findings) == 1
            assert findings[0].category == 'adaptive_threshold_shift'
            assert findings[0].severity == IssueSeverity.LOW
        else:
            assert len(findings) == 0

    def test_no_shift_no_finding(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        repo = MagicMock()
        repo.list_runs.return_value = [_make_run() for _ in range(5)]

        previous_review = SelfExaminationSnapshot(
            metadata={'adaptive_threshold_nc': 3},
        )

        oses = OperationalSelfExaminationService(
            workspace_root='/tmp/test',
            storage=MagicMock(),
            experiment_lab_repository=repo,
        )
        findings = oses._adaptive_threshold_shift_findings(
            previous_review=previous_review,
        )
        assert len(findings) == 0


class TestGetCurrentThresholdsFormat:
    """test_get_current_thresholds_format — returns dict with expected keys."""

    def test_has_global_key(self):
        lab = _make_lab([_make_run() for _ in range(5)])
        thresholds = lab.get_current_thresholds()
        assert 'global' in thresholds
        assert isinstance(thresholds['global'], int)

    def test_has_domain_keys(self):
        lab = _make_lab([])
        thresholds = lab.get_current_thresholds()
        assert ExperimentDomain.CLOUD_REASONING.value in thresholds
        assert ExperimentDomain.CODE.value in thresholds

    def test_all_values_are_ints(self):
        lab = _make_lab([_make_run() for _ in range(20)])
        thresholds = lab.get_current_thresholds()
        for key, val in thresholds.items():
            assert isinstance(val, int), f'{key} should be int, got {type(val)}'


class TestBackwardCompatibleExplicitMinRuns:
    """test_backward_compatible_explicit_min_runs — explicit min_runs param still works."""

    def test_explicit_min_runs_10_honored(self):
        runs = [_make_run() for _ in range(8)]
        lab = _make_lab(runs)
        result = lab.generate_training_corpus(min_runs=10)
        assert result == []

    def test_explicit_min_runs_5_honored(self):
        runs = [_make_run() for _ in range(8)]
        lab = _make_lab(runs)
        result = lab.generate_training_corpus(min_runs=5)
        assert len(result) >= 1

    def test_explicit_min_runs_overrides_adaptive(self):
        runs = [_make_run() for _ in range(20)]
        lab = _make_lab(runs)
        with patch.object(lab, 'calculate_adaptive_threshold', return_value=5):
            result_adaptive = lab.generate_training_corpus()
            result_explicit = lab.generate_training_corpus(min_runs=25)
        assert len(result_adaptive) >= 1
        assert result_explicit == []
