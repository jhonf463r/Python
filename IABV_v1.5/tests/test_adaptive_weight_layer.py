"""Tests for AdaptiveWeightLayer — profile generation, weight calculations, reasons."""
from __future__ import annotations

from datetime import datetime, timezone

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
)
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer


def _run(
    *,
    success: bool = True,
    total_score: float = 0.8,
    execution_ms: int = 100,
    reused_later: bool = False,
    metadata: dict | None = None,
) -> ExperimentRun:
    return ExperimentRun(
        domain=ExperimentDomain.LANGUAGE,
        suite_name='test_suite',
        objective='test',
        subject_key='general',
        route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
        success=success,
        reused_later=reused_later,
        metrics=ExperimentMetric(
            total_score=total_score,
            precision=total_score,
            execution_ms=execution_ms,
        ),
        metadata=dict(metadata or {}),
        created_at_utc=datetime.now(timezone.utc),
    )


# ---- 1. Profile generation returns expected keys ----

def test_profile_contains_expected_keys() -> None:
    """_profile() must return all standard profile keys."""
    layer = AdaptiveWeightLayer()
    runs = [_run(), _run(success=False, total_score=0.3)]
    profile = layer._profile(runs)
    expected_keys = {
        'sample_count', 'success_rate', 'failure_rate', 'blocked_rate',
        'fallback_rate', 'reuse_ratio', 'average_score', 'average_latency_ms',
        'recency_score', 'trend_score', 'adaptive_weight', 'weighted_score',
        'reasons',
    }
    assert expected_keys.issubset(set(profile.keys()))


# ---- 2. Weight calculation reflects success/failure ----

def test_weight_higher_for_successful_runs() -> None:
    """Profiles with all-success runs should have higher adaptive_weight than all-failure."""
    layer = AdaptiveWeightLayer()
    success_profile = layer._profile([_run(success=True, total_score=0.9) for _ in range(5)])
    failure_profile = layer._profile([_run(success=False, total_score=0.2) for _ in range(5)])
    assert success_profile['adaptive_weight'] > failure_profile['adaptive_weight']


# ---- 3. Reasons generated for notable patterns ----

def test_reasons_generated_for_high_success() -> None:
    """Profiles with >= 66% success should include a success reason."""
    layer = AdaptiveWeightLayer()
    runs = [_run(success=True, total_score=0.9) for _ in range(4)]
    profile = layer._profile(runs)
    reasons = profile.get('reasons', [])
    assert any('exito' in str(r).lower() for r in reasons)


# ---- 4. suggest() groups and profiles correctly ----

def test_suggest_returns_profiles_per_key() -> None:
    """suggest() must return one profile per (route, assistant_kind, config_signature) key."""
    layer = AdaptiveWeightLayer()
    key1 = (EvaluationRoute.LANGUAGE_UNDERSTANDING, 'ollama', '')
    key2 = (EvaluationRoute.CLOUD, 'gemini', '')
    grouped = {
        key1: [_run(success=True, total_score=0.85)],
        key2: [_run(success=False, total_score=0.3)],
    }
    profiles = layer.suggest(grouped_runs=grouped)
    assert key1 in profiles
    assert key2 in profiles
    assert profiles[key1]['success_rate'] == 1.0
    assert profiles[key2]['success_rate'] == 0.0
