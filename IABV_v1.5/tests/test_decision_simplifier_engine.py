"""Tests for DecisionSimplifierEngine."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from iabv_v15.services.evolution.decision_simplifier_engine import (
    DecisionSimplifierEngine,
    ObstacleComplexity,
    ActionStep,
)


@pytest.fixture
def engine(tmp_path: Path) -> DecisionSimplifierEngine:
    return DecisionSimplifierEngine(data_root=str(tmp_path))


class TestClassifyObstacle:
    def test_quota_exhausted(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('Error 429: rate limit exceeded')
        assert profile.category == 'quota_exhausted'
        assert profile.complexity in (ObstacleComplexity.TRIVIAL, ObstacleComplexity.SIMPLE)

    def test_api_key_missing(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('GROQ_API_KEY not set in environment')
        assert profile.category == 'api_key_missing'

    def test_login_required(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('401 Unauthorized - please sign in')
        assert profile.category == 'login_required'

    def test_timeout(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('Connection timed out after 30s')
        assert profile.category == 'timeout'

    def test_dependency_missing(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('ModuleNotFoundError: No module named aider')
        assert profile.category == 'dependency_missing'

    def test_network_issue(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('ConnectionError: DNS resolution failed')
        assert profile.category == 'network_issue'

    def test_unknown_obstacle(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('Something completely unexpected happened')
        assert profile.category == 'unknown'
        assert profile.complexity == ObstacleComplexity.COMPLEX

    def test_confidence_increases_with_history(self, tmp_path: Path) -> None:
        engine = DecisionSimplifierEngine(data_root=str(tmp_path))
        # Seed history with successful quota resolutions
        history_dir = tmp_path / 'evolution' / 'decision_simplifier'
        history_dir.mkdir(parents=True, exist_ok=True)
        with open(history_dir / 'solution_history.jsonl', 'w') as f:
            for _ in range(5):
                f.write(json.dumps({'category': 'quota_exhausted', 'success': True}) + '\n')
        engine._load_history()
        profile = engine.classify_obstacle('429 rate limit')
        assert profile.similar_past_count == 5
        assert profile.past_success_rate == 1.0
        assert profile.complexity == ObstacleComplexity.TRIVIAL


class TestCheckReadiness:
    def test_ready_with_resources(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('Connection timed out')
        profile.permissions_granted = True
        readiness = engine.check_readiness(profile)
        assert readiness.ready is True
        assert readiness.confidence >= 0.5

    def test_blocked_without_permission(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('quota exceeded')
        profile.permissions_granted = False
        readiness = engine.check_readiness(profile)
        assert readiness.ready is False
        assert 'permission' in readiness.missing


class TestSuggestAction:
    def test_plan_for_quota(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('429 rate limit')
        readiness = engine.check_readiness(profile)
        if readiness.ready:
            plan = engine.suggest_action(profile, readiness)
            assert plan is not None
            assert len(plan.steps) >= 1
            assert plan.steps[0].action == 'rotate_provider'

    def test_no_plan_when_not_ready(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('something weird')
        profile.permissions_granted = False
        readiness = engine.check_readiness(profile)
        plan = engine.suggest_action(profile, readiness)
        assert plan is None


class TestExecutePlan:
    def test_execute_with_executor(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('429 rate limit')
        readiness = engine.check_readiness(profile)
        plan = engine.suggest_action(profile, readiness)
        if plan:
            result = engine.execute_plan(plan, profile, executor=lambda s: True)
            assert result.success is True
            assert result.steps_completed == len(plan.steps)

    def test_execute_failure(self, engine: DecisionSimplifierEngine) -> None:
        profile = engine.classify_obstacle('429 rate limit')
        readiness = engine.check_readiness(profile)
        plan = engine.suggest_action(profile, readiness)
        if plan:
            result = engine.execute_plan(plan, profile, executor=lambda s: False)
            assert result.success is False


class TestResolveIfReady:
    def test_resolve_trivial(self, engine: DecisionSimplifierEngine) -> None:
        result = engine.resolve_if_ready(
            'timeout connecting to API',
            executor=lambda s: True,
        )
        # timeout is TRIVIAL — should resolve
        assert result is not None
        assert result.success is True

    def test_escalate_complex(self, engine: DecisionSimplifierEngine) -> None:
        result = engine.resolve_if_ready('completely novel alien error from Mars')
        assert result is None  # Should escalate to deep reasoning


class TestHistoryPersistence:
    def test_persisted(self, engine: DecisionSimplifierEngine) -> None:
        engine.resolve_if_ready('timeout error', executor=lambda s: True)
        path = engine._history_path()
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[0])
        assert entry['category'] == 'timeout'


class TestOsesFindings:
    def test_no_findings_empty_history(self, engine: DecisionSimplifierEngine) -> None:
        findings = engine.oses_findings()
        assert findings == []

    def test_high_failure_rate_finding(self, tmp_path: Path) -> None:
        engine = DecisionSimplifierEngine(data_root=str(tmp_path))
        history_dir = tmp_path / 'evolution' / 'decision_simplifier'
        history_dir.mkdir(parents=True, exist_ok=True)
        with open(history_dir / 'solution_history.jsonl', 'w') as f:
            for i in range(10):
                f.write(json.dumps({
                    'category': 'network_issue',
                    'success': i < 2,  # 80% failure rate
                }) + '\n')
        engine._load_history()
        findings = engine.oses_findings()
        assert len(findings) >= 1
        assert 'failure rate' in findings[0]['title'].lower()


class TestStatusSummary:
    def test_summary(self, engine: DecisionSimplifierEngine) -> None:
        summary = engine.status_summary()
        assert 'total_resolved' in summary
        assert 'known_patterns' in summary
        assert 'quota_exhausted' in summary['known_patterns']
