"""Tests for AdaptiveModelSelector and adaptive provider selection in CloudReasoningPlannerService."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AdaptiveModelSelector unit tests
# ---------------------------------------------------------------------------

class TestAdaptiveModelSelector:
    """Tests for the AdaptiveModelSelector service."""

    def _make_selector(self, tmp_path: Path | None = None):
        from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector
        data_dir = tmp_path or Path(tempfile.mkdtemp())
        return AdaptiveModelSelector(data_dir=data_dir)

    def test_select_best_provider_no_history(self, tmp_path):
        sel = self._make_selector(tmp_path)
        result = sel.select_best_provider(task_type='general')
        assert 'provider_id' in result
        assert 'fallback_chain' in result
        assert 'scores' in result
        assert isinstance(result['fallback_chain'], list)

    def test_select_best_provider_returns_ollama_when_no_keys(self, tmp_path):
        sel = self._make_selector(tmp_path)
        # Clear all cloud API keys
        env_patch = {
            'GEMINI_API_KEY': '',
            'GROQ_API_KEY': '',
            'OPENROUTER_API_KEY': '',
            'TOGETHER_API_KEY': '',
        }
        with patch.dict(os.environ, env_patch, clear=False):
            result = sel.select_best_provider()
            assert result['provider_id'] == 'ollama_local'

    def test_record_result_creates_log(self, tmp_path):
        sel = self._make_selector(tmp_path)
        sel.record_result(
            provider_id='groq',
            task_type='planning',
            latency_ms=150.0,
            success=True,
            model_used='llama-3.3-70b',
        )
        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        assert log_file.exists()
        entries = [json.loads(l) for l in log_file.read_text().strip().split('\n')]
        assert len(entries) == 1
        assert entries[0]['provider_id'] == 'groq'
        assert entries[0]['latency_ms'] == 150.0

    def test_record_quota_exhaustion_triggers_cooldown(self, tmp_path):
        sel = self._make_selector(tmp_path)
        sel.record_result(
            provider_id='gemini',
            task_type='planning',
            latency_ms=500.0,
            success=False,
            error='quota exceeded',
            status_code=429,
        )
        assert 'gemini' in sel._quota_cooldowns

    def test_detect_degradation_slow_provider(self, tmp_path):
        sel = self._make_selector(tmp_path)
        # Write entries with high latency
        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        for i in range(5):
            entry = {
                'provider_id': 'ollama_local',
                'latency_ms': 20000.0,  # very slow
                'success': True,
                'task_type': 'general',
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')

        findings = sel.detect_degradation()
        slow_findings = [f for f in findings if f['type'] == 'very_slow']
        assert len(slow_findings) == 1
        assert slow_findings[0]['provider_id'] == 'ollama_local'

    def test_detect_degradation_high_failure_rate(self, tmp_path):
        sel = self._make_selector(tmp_path)
        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        for i in range(5):
            entry = {
                'provider_id': 'groq',
                'latency_ms': 100.0,
                'success': i == 0,  # only first succeeds
                'error': '' if i == 0 else 'connection error',
                'task_type': 'general',
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')

        findings = sel.detect_degradation()
        fail_findings = [f for f in findings if f['type'] == 'high_failure_rate']
        assert len(fail_findings) == 1
        assert fail_findings[0]['provider_id'] == 'groq'

    def test_detect_degradation_quota_exhausted(self, tmp_path):
        sel = self._make_selector(tmp_path)
        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            'provider_id': 'gemini',
            'latency_ms': 200.0,
            'success': False,
            'error': 'quota exceeded',
            'quota_exhausted': True,
            'task_type': 'general',
        }
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        findings = sel.detect_degradation()
        quota_findings = [f for f in findings if f['type'] == 'quota_exhausted']
        assert len(quota_findings) == 1

    def test_recommend_local_model_coding(self, tmp_path):
        sel = self._make_selector(tmp_path)
        result = sel.recommend_local_model(
            task_type='coding',
            available_models=['qwen2.5-coder:7b', 'gemma3:4b', 'embeddinggemma:latest'],
        )
        assert result['recommended'] == 'qwen2.5-coder:7b'
        assert 'code_specialized' in result['reason']

    def test_recommend_local_model_excludes_embeddings(self, tmp_path):
        sel = self._make_selector(tmp_path)
        result = sel.recommend_local_model(
            task_type='general',
            available_models=['embeddinggemma:latest', 'gemma3:4b'],
        )
        assert result['recommended'] == 'gemma3:4b'

    def test_performance_summary_no_data(self, tmp_path):
        sel = self._make_selector(tmp_path)
        summary = sel.performance_summary()
        assert summary['status'] == 'no_data'

    def test_performance_summary_with_data(self, tmp_path):
        sel = self._make_selector(tmp_path)
        sel.record_result(provider_id='groq', latency_ms=100.0, success=True)
        sel.record_result(provider_id='groq', latency_ms=120.0, success=True)
        sel.record_result(provider_id='ollama_local', latency_ms=5000.0, success=True)
        summary = sel.performance_summary()
        assert summary['status'] == 'ok'
        assert summary['total_decisions'] == 3

    def test_cloud_provider_scored_higher_with_key(self, tmp_path):
        sel = self._make_selector(tmp_path)
        with patch.dict(os.environ, {'GROQ_API_KEY': 'gsk_test123'}, clear=False):
            result = sel.select_best_provider()
            scores = {s['provider_id']: s['total_score'] for s in result['scores']}
            # Groq (with key) should score higher than ollama_local
            assert scores.get('groq', 0) > scores.get('ollama_local', 0)


# ---------------------------------------------------------------------------
# CloudReasoningPlannerService adaptive chain tests
# ---------------------------------------------------------------------------

class TestAdaptiveCloudPlanner:
    """Tests for adaptive provider selection in CloudReasoningPlannerService."""

    def test_extract_json_strips_think_tags(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
        data = {
            'choices': [{
                'message': {
                    'content': '<think>internal reasoning</think>{"steps": [{"title": "test"}]}'
                }
            }]
        }
        result = CloudReasoningPlannerService._extract_json(data, 'test')
        assert result is not None
        assert result['_cloud_source'] == 'test'
        assert 'steps' in result

    def test_extract_json_returns_none_for_invalid(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
        data = {'choices': [{'message': {'content': 'no json here'}}]}
        result = CloudReasoningPlannerService._extract_json(data, 'test')
        assert result is None

    def test_try_provider_returns_none_for_missing_key(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}, clear=False):
            result = CloudReasoningPlannerService._try_provider(
                'gemini', [{'role': 'user', 'content': 'test'}],
            )
            assert result is None

    def test_selector_wiring_respects_chain(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
        from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector

        selector = MagicMock(spec=AdaptiveModelSelector)
        selector.select_best_provider.return_value = {
            'provider_id': 'ollama_local',
            'fallback_chain': ['ollama_local'],
            'reason': 'test',
        }

        original = CloudReasoningPlannerService._model_selector
        try:
            CloudReasoningPlannerService._model_selector = selector
            # Call with no keys set (all cloud providers should fail)
            with patch.dict(os.environ, {
                'GEMINI_API_KEY': '', 'GROQ_API_KEY': '',
                'OPENROUTER_API_KEY': '', 'TOGETHER_API_KEY': '',
            }):
                # The chain is ['ollama_local'] which will also fail (no server)
                # but we verify the selector was consulted
                CloudReasoningPlannerService._query_cloud_for_plan(
                    'test context', 'test prompt',
                )
                selector.select_best_provider.assert_called_once_with(task_type='planning')
        finally:
            CloudReasoningPlannerService._model_selector = original


# ---------------------------------------------------------------------------
# OSES model degradation findings tests
# ---------------------------------------------------------------------------

class TestOSESModelFindings:
    """Tests for OSES _runtime_performance_findings with model degradation."""

    def _make_oses(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        oses = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService,
        )
        oses.world_model_service = None
        oses.adaptive_model_selector = None
        return oses

    def test_model_slow_triggers_finding(self, tmp_path):
        oses = self._make_oses()
        from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector
        sel = AdaptiveModelSelector(data_dir=tmp_path)

        # Write slow entries
        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            with open(log_file, 'a') as f:
                f.write(json.dumps({
                    'provider_id': 'ollama_local',
                    'latency_ms': 20000.0,
                    'success': True,
                }) + '\n')

        oses.adaptive_model_selector = sel
        with patch.object(oses, '_read_process_rss_mb', return_value=100.0):
            findings = oses._runtime_performance_findings()
        slow = [f for f in findings if f.title == 'model_too_slow']
        assert len(slow) == 1
        assert 'ollama_local' in slow[0].summary

    def test_provider_failing_triggers_finding(self, tmp_path):
        oses = self._make_oses()
        from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector
        sel = AdaptiveModelSelector(data_dir=tmp_path)

        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        for i in range(5):
            with open(log_file, 'a') as f:
                f.write(json.dumps({
                    'provider_id': 'groq',
                    'latency_ms': 100.0,
                    'success': i == 0,
                    'error': '' if i == 0 else 'fail',
                }) + '\n')

        oses.adaptive_model_selector = sel
        with patch.object(oses, '_read_process_rss_mb', return_value=100.0):
            findings = oses._runtime_performance_findings()
        failing = [f for f in findings if f.title == 'provider_failing']
        assert len(failing) == 1

    def test_quota_exhausted_triggers_finding(self, tmp_path):
        oses = self._make_oses()
        from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector
        sel = AdaptiveModelSelector(data_dir=tmp_path)

        log_file = tmp_path / 'evolution' / 'model_selection' / 'performance.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(json.dumps({
                'provider_id': 'gemini',
                'latency_ms': 200.0,
                'success': False,
                'quota_exhausted': True,
            }) + '\n')

        oses.adaptive_model_selector = sel
        with patch.object(oses, '_read_process_rss_mb', return_value=100.0):
            findings = oses._runtime_performance_findings()
        quota = [f for f in findings if f.title == 'provider_quota_exhausted']
        assert len(quota) == 1

    def test_no_findings_without_selector(self):
        oses = self._make_oses()
        with patch.object(oses, '_read_process_rss_mb', return_value=100.0):
            findings = oses._runtime_performance_findings()
        model_findings = [f for f in findings if f.title in (
            'model_too_slow', 'provider_failing', 'provider_quota_exhausted',
        )]
        assert len(model_findings) == 0
