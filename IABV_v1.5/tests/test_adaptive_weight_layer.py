"""Tests for AdaptiveWeightLayer — profile generation, weight calculations, reasons."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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


# ---- GAP 2: metacognitive persistence ----


def test_metacognitive_adjustment_persists_across_instances(tmp_path: Path) -> None:
    """apply_metacognitive_adjustment writes to disk; a new instance reads it back."""
    weights_file = tmp_path / 'metacognitive_adjustments.json'
    layer1 = AdaptiveWeightLayer(persistence_path=str(weights_file))
    layer1.apply_metacognitive_adjustment(
        route='local', assistant_kind='ollama', adjustment=0.08, reason='test persist',
    )
    assert weights_file.exists(), 'weights file should be created after adjustment'
    layer2 = AdaptiveWeightLayer(persistence_path=str(weights_file))
    assert layer2.get_metacognitive_adjustment('local', 'ollama') == 0.08


def test_corrupt_file_starts_empty(tmp_path: Path) -> None:
    """A corrupt JSON file should not crash; layer starts empty and logs."""
    weights_file = tmp_path / 'metacognitive_adjustments.json'
    weights_file.write_text('NOT VALID JSON {{{', encoding='utf-8')
    layer = AdaptiveWeightLayer(persistence_path=str(weights_file))
    assert layer.get_metacognitive_adjustment('any', 'route') == 0.0


def test_get_metacognitive_adjustment_after_reload(tmp_path: Path) -> None:
    """After persisting and reloading, get_metacognitive_adjustment returns the stored value."""
    weights_file = tmp_path / 'metacognitive_adjustments.json'
    layer1 = AdaptiveWeightLayer(persistence_path=str(weights_file))
    layer1.apply_metacognitive_adjustment(
        route='cloud', assistant_kind='gemini', adjustment=-0.05, reason='overconfidence',
    )
    layer2 = AdaptiveWeightLayer(persistence_path=str(weights_file))
    assert layer2.get_metacognitive_adjustment('cloud', 'gemini') == -0.05


def test_strategy_selector_sees_adjustment_after_reload(tmp_path: Path) -> None:
    """StrategySelector reading from a reloaded AdaptiveWeightLayer sees persisted adjustments."""
    from iabv_v15.services.lab.strategy_selector import StrategySelector
    weights_file = tmp_path / 'metacognitive_adjustments.json'
    layer1 = AdaptiveWeightLayer(persistence_path=str(weights_file))
    layer1.apply_metacognitive_adjustment(
        route='local', assistant_kind='ollama', adjustment=0.12, reason='underconfidence',
    )
    layer2 = AdaptiveWeightLayer(persistence_path=str(weights_file))
    selector = StrategySelector(adaptive_weight_layer=layer2)
    assert layer2.get_metacognitive_adjustment('local', 'ollama') == 0.12


def test_no_persistence_path_falls_back_to_cwd() -> None:
    """When no persistence_path and no IABV_WORKSPACE, layer falls back to Path.cwd()."""
    import os
    old_ws = os.environ.pop('IABV_WORKSPACE', None)
    old_wr = os.environ.pop('IABV_WORKSPACE_ROOT', None)
    try:
        layer = AdaptiveWeightLayer()
        assert layer._weights_path is not None, '_weights_path must not be None even without env vars'
        layer.apply_metacognitive_adjustment(
            route='local', assistant_kind='test', adjustment=0.1, reason='fallback test',
        )
        assert layer.get_metacognitive_adjustment('local', 'test') == 0.1
    finally:
        if old_ws is not None:
            os.environ['IABV_WORKSPACE'] = old_ws
        if old_wr is not None:
            os.environ['IABV_WORKSPACE_ROOT'] = old_wr


def test_bootstrap_wires_persistence_path() -> None:
    """AppBootstrap must create AdaptiveWeightLayer with a non-None _weights_path."""
    import shutil
    from uuid import uuid4
    from iabv_v15.bootstrap import AppBootstrap

    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'awl_bootstrap_{uuid4().hex[:8]}'
    root.mkdir(parents=True, exist_ok=True)
    try:
        boot = AppBootstrap(str(root))
        assert boot.adaptive_weight_layer._weights_path is not None, \
            'bootstrap must set _weights_path'
        expected_suffix = str(Path('data') / 'evolution' / 'adaptive_weights' / 'metacognitive_adjustments.json')
        assert str(boot.adaptive_weight_layer._weights_path).endswith(expected_suffix), \
            f'path should end with {expected_suffix}'
    finally:
        shutil.rmtree(root, ignore_errors=True)
