"""Tests for MetacognitionEvolutionMixin."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from iabv_v15.services.evolution.metacognition_evolution_mixin import (
    MetacognitionEvolutionMixin,
)


@pytest.fixture
def mixin() -> MetacognitionEvolutionMixin:
    return MetacognitionEvolutionMixin()


class TestAllFindings:
    def test_aggregates_all_sources(self, mixin: MetacognitionEvolutionMixin) -> None:
        ds_mock = MagicMock()
        ds_mock.oses_findings.return_value = [
            {'category': 'decision_simplifier', 'title': 'test1'},
        ]
        pl_mock = MagicMock()
        pl_mock.oses_findings.return_value = [
            {'category': 'platform_learning', 'title': 'test2'},
        ]
        ak_mock = MagicMock()
        ak_mock.find_missing_keys.return_value = [
            {'provider_id': 'groq', 'name': 'Groq'},
            {'provider_id': 'gemini', 'name': 'Gemini'},
        ]

        mixin.decision_simplifier = ds_mock
        mixin.platform_learning = pl_mock
        mixin.api_key_discovery = ak_mock

        findings = mixin.all_findings()
        assert len(findings) == 3
        categories = [f['category'] for f in findings]
        assert 'decision_simplifier' in categories
        assert 'platform_learning' in categories
        assert 'metacognition_evolution' in categories

    def test_handles_missing_services(self, mixin: MetacognitionEvolutionMixin) -> None:
        findings = mixin.all_findings()
        assert findings == []

    def test_handles_service_error(self, mixin: MetacognitionEvolutionMixin) -> None:
        ds_mock = MagicMock()
        ds_mock.oses_findings.side_effect = RuntimeError('oops')
        mixin.decision_simplifier = ds_mock
        findings = mixin.all_findings()
        assert findings == []


class TestReactToFindings:
    def test_react_to_actionable(self, mixin: MetacognitionEvolutionMixin) -> None:
        ac_mock = MagicMock()
        mixin.auto_correction_engine = ac_mock

        findings = [{
            'category': 'metacognition_evolution',
            'title': '2 cloud providers not configured',
            'metadata': {'actionable': True, 'missing_providers': ['groq']},
        }]
        actions = mixin.react_to_findings(findings)
        assert len(actions) >= 1
        ac_mock.auto_provision_missing_secrets.assert_called_once()

    def test_skip_non_actionable(self, mixin: MetacognitionEvolutionMixin) -> None:
        findings = [{
            'category': 'test',
            'title': 'Not actionable',
            'metadata': {},
        }]
        actions = mixin.react_to_findings(findings)
        assert actions == []

    def test_rotate_provider(self, mixin: MetacognitionEvolutionMixin) -> None:
        ak_mock = MagicMock()
        best_mock = MagicMock()
        best_mock.valid = True
        best_mock.provider_id = 'gemini'
        ak_mock.best_provider.return_value = best_mock
        mixin.api_key_discovery = ak_mock

        findings = [{
            'category': 'test',
            'title': 'Quota exhausted for groq',
            'metadata': {'actionable': True},
        }]
        actions = mixin.react_to_findings(findings)
        assert any('gemini' in a for a in actions)


class TestRunEvolutionCycle:
    def test_full_cycle(self, mixin: MetacognitionEvolutionMixin) -> None:
        ds_mock = MagicMock()
        ds_mock.oses_findings.return_value = []
        ds_mock.status_summary.return_value = {'total_resolved': 0}
        pl_mock = MagicMock()
        pl_mock.oses_findings.return_value = []
        pl_mock.status_summary.return_value = {'total_platforms': 5}
        ak_mock = MagicMock()
        ak_mock.find_missing_keys.return_value = []
        ak_mock.full_health_report.return_value = {'best_provider': None}

        mixin.decision_simplifier = ds_mock
        mixin.platform_learning = pl_mock
        mixin.api_key_discovery = ak_mock

        result = mixin.run_evolution_cycle()
        assert 'findings_count' in result
        assert 'actions_taken' in result
        assert 'provider_health' in result
