"""Tests for StrategySelector — recommendation, fallback, trace_id and CSK handling."""
from __future__ import annotations

from datetime import datetime, timezone

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
)
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.lab.strategy_selector import StrategySelector


def _run(
    *,
    route: EvaluationRoute = EvaluationRoute.LANGUAGE_UNDERSTANDING,
    success: bool = True,
    total_score: float = 0.8,
    trace_id: str = '',
    comparison_scope_key: str = '',
    assistant_kind: str = '',
    config_signature: str = '',
) -> ExperimentRun:
    return ExperimentRun(
        domain=ExperimentDomain.LANGUAGE,
        suite_name='test_suite',
        objective='test',
        subject_key='general',
        comparison_scope_key=comparison_scope_key,
        route=route,
        assistant_kind=assistant_kind,
        config_signature=config_signature,
        success=success,
        metrics=ExperimentMetric(total_score=total_score, precision=total_score),
        metadata={'trace_id': trace_id, 'comparison_scope_key': comparison_scope_key},
        created_at_utc=datetime.now(timezone.utc),
    )


# ---- 1. Fallback when no data ----

def test_fallback_without_data() -> None:
    """recommend() returns FALLBACK when no runs are provided."""
    selector = StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer())
    rec = selector.recommend(
        domain=ExperimentDomain.LANGUAGE,
        subject_key='general',
        candidate_runs=[],
    )
    assert rec.recommended_route == EvaluationRoute.FALLBACK
    assert rec.rationale


# ---- 2. Prioritizes successful route over failed ----

def test_prioritizes_successful_route_over_failed() -> None:
    """recommend() picks the route with successful runs over one with only failures."""
    selector = StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer())
    runs = [
        _run(route=EvaluationRoute.LOCAL, success=False, total_score=0.3),
        _run(route=EvaluationRoute.LOCAL, success=False, total_score=0.25),
        _run(route=EvaluationRoute.LANGUAGE_UNDERSTANDING, success=True, total_score=0.85),
    ]
    rec = selector.recommend(
        domain=ExperimentDomain.LANGUAGE,
        subject_key='general',
        candidate_runs=runs,
    )
    assert rec.recommended_route == EvaluationRoute.LANGUAGE_UNDERSTANDING


# ---- 3. Handles empty CSK without crash ----

def test_handles_empty_csk_without_crash() -> None:
    """recommend() should work fine when all runs have empty comparison_scope_key."""
    selector = StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer())
    runs = [
        _run(comparison_scope_key='', success=True, total_score=0.7),
        _run(comparison_scope_key='', success=True, total_score=0.75),
    ]
    rec = selector.recommend(
        domain=ExperimentDomain.LANGUAGE,
        subject_key='general',
        candidate_runs=runs,
    )
    assert rec.recommended_route is not None
    assert rec.score > 0


# ---- 4. Respects adaptive_weight_layer ----

def test_respects_adaptive_weight_layer() -> None:
    """recommend() uses AdaptiveWeightLayer profiles to influence scoring."""
    selector = StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer())
    runs = [
        _run(route=EvaluationRoute.LANGUAGE_UNDERSTANDING, success=True, total_score=0.80, assistant_kind='ollama'),
        _run(route=EvaluationRoute.CLOUD, success=True, total_score=0.78, assistant_kind='gemini'),
    ]
    rec = selector.recommend(
        domain=ExperimentDomain.LANGUAGE,
        subject_key='general',
        candidate_runs=runs,
    )
    assert rec.metadata.get('ranked_configurations')
    configs = rec.metadata['ranked_configurations']
    assert len(configs) >= 1
    assert all('adaptive_weight' in c for c in configs)


# ---- 5. winning/losing trace_ids populated when trace_id present ----

def test_trace_ids_populated_in_recommendation() -> None:
    """winning_trace_ids and losing_trace_ids should be populated when runs have trace_id."""
    selector = StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer())
    runs = [
        _run(route=EvaluationRoute.LANGUAGE_UNDERSTANDING, success=True, total_score=0.9, trace_id='abc12345'),
        _run(route=EvaluationRoute.LOCAL, success=True, total_score=0.5, trace_id='def67890'),
    ]
    rec = selector.recommend(
        domain=ExperimentDomain.LANGUAGE,
        subject_key='general',
        candidate_runs=runs,
    )
    winning = rec.metadata.get('winning_trace_ids', [])
    losing = rec.metadata.get('losing_trace_ids', [])
    assert 'abc12345' in winning
    assert 'def67890' in losing
