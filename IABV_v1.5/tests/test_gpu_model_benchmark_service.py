"""Tests for GpuModelBenchmarkService — GPU model auto-benchmark."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentCandidate,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRecommendation,
    ExperimentRun,
)
from iabv_v15.services.lab.gpu_model_benchmark_service import (
    GpuModelBenchmarkService,
    _BENCHMARK_PROMPTS,
)
from iabv_v15.services.lab.suites import InferenceBenchmarkSuite


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_lab() -> MagicMock:
    lab = MagicMock()
    recommendation = ExperimentRecommendation(
        domain=ExperimentDomain.INFERENCE_BENCHMARK,
        subject_key='gpu_model_selection',
        recommended_route=EvaluationRoute.LOCAL,
        recommended_assistant_kind='gemma3',
        rationale='gemma3:4b tiene el mejor balance tok/s + calidad.',
    )
    lab.run_experiment.return_value = (
        [MagicMock(spec=ExperimentRun)],
        recommendation,
    )
    return lab


def _fake_ollama_response(text: str = 'La neuroplasticidad es la capacidad del cerebro.', eval_count: int = 42, eval_duration: int = 1_000_000_000) -> bytes:
    return json.dumps({
        'response': text,
        'eval_count': eval_count,
        'eval_duration': eval_duration,
    }).encode('utf-8')


# ---------------------------------------------------------------------------
# Tests: discover_models
# ---------------------------------------------------------------------------

class TestDiscoverModels:
    def test_discover_models_parses_ollama_list(self):
        fake_output = (
            'NAME                    ID              SIZE      MODIFIED\n'
            'gemma3:4b               abc123          3.3 GB    2 hours ago\n'
            'qwen3:8b                def456          5.1 GB    3 hours ago\n'
        )
        with patch('shutil.which', return_value='/usr/bin/ollama'), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=fake_output)
            svc = GpuModelBenchmarkService(experiment_lab=_fake_lab())
            models = svc.discover_models()
        assert len(models) == 2
        assert models[0]['name'] == 'gemma3:4b'
        assert models[1]['name'] == 'qwen3:8b'

    def test_discover_models_returns_empty_when_ollama_missing(self):
        with patch('shutil.which', return_value=None):
            svc = GpuModelBenchmarkService(experiment_lab=_fake_lab())
            assert svc.discover_models() == []

    def test_discover_models_returns_empty_on_failure(self):
        with patch('shutil.which', return_value='/usr/bin/ollama'), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='')
            svc = GpuModelBenchmarkService(experiment_lab=_fake_lab())
            assert svc.discover_models() == []


# ---------------------------------------------------------------------------
# Tests: benchmark_model
# ---------------------------------------------------------------------------

class TestBenchmarkModel:
    def test_benchmark_model_measures_tps_and_quality(self):
        svc = GpuModelBenchmarkService(experiment_lab=_fake_lab())
        with patch.object(svc, '_ollama_generate') as mock_gen:
            mock_gen.return_value = (
                'La neuroplasticidad es la capacidad del cerebro para cambiar y adaptarse.',
                42,
                1_000_000_000,
            )
            result = svc.benchmark_model('gemma3:4b')
        assert result['model_name'] == 'gemma3:4b'
        assert result['avg_tokens_per_second'] == 42.0
        assert result['avg_quality_score'] > 0.0
        assert result['prompt_count'] == len(_BENCHMARK_PROMPTS)
        assert len(result['details']) == len(_BENCHMARK_PROMPTS)

    def test_benchmark_model_handles_zero_duration(self):
        svc = GpuModelBenchmarkService(experiment_lab=_fake_lab())
        with patch.object(svc, '_ollama_generate') as mock_gen:
            mock_gen.return_value = ('respuesta', 0, 0)
            result = svc.benchmark_model('test:latest')
        assert result['avg_tokens_per_second'] == 0.0


# ---------------------------------------------------------------------------
# Tests: run_full_benchmark
# ---------------------------------------------------------------------------

class TestRunFullBenchmark:
    def test_run_full_benchmark_ranks_models(self):
        lab = _fake_lab()
        svc = GpuModelBenchmarkService(experiment_lab=lab)
        call_count = {'n': 0}
        def mock_generate(model, prompt):
            call_count['n'] += 1
            if 'gemma' in model:
                return ('neuroplasticidad capacidad cerebro cambiar adaptarse', 50, 1_000_000_000)
            return ('respuesta generica', 20, 1_000_000_000)

        with patch.object(svc, '_ollama_generate', side_effect=mock_generate), \
             patch.object(svc, 'discover_models', return_value=[
                 {'name': 'gemma3:4b', 'size': '3.3 GB'},
                 {'name': 'qwen3:8b', 'size': '5.1 GB'},
             ]):
            result = svc.run_full_benchmark()

        assert result['status'] == 'completed'
        assert result['best_model'] == 'gemma3:4b'
        assert len(result['ranked']) == 2
        assert result['ranked'][0]['model'] == 'gemma3:4b'
        assert result['recommendation'] is not None
        lab.run_experiment.assert_called_once()

    def test_run_full_benchmark_no_models(self):
        svc = GpuModelBenchmarkService(experiment_lab=_fake_lab())
        with patch.object(svc, 'discover_models', return_value=[]):
            result = svc.run_full_benchmark()
        assert result['status'] == 'no_models'

    def test_run_full_benchmark_with_explicit_models(self):
        lab = _fake_lab()
        svc = GpuModelBenchmarkService(experiment_lab=lab)
        with patch.object(svc, '_ollama_generate', return_value=('respuesta', 30, 1_000_000_000)):
            result = svc.run_full_benchmark(models=['phi4:latest'])
        assert result['status'] == 'completed'
        assert result['best_model'] == 'phi4:latest'


# ---------------------------------------------------------------------------
# Tests: InferenceBenchmarkSuite
# ---------------------------------------------------------------------------

class TestInferenceBenchmarkSuite:
    def test_suite_scores_with_tps_and_quality(self):
        suite = InferenceBenchmarkSuite()
        candidate = ExperimentCandidate(
            label='test-model',
            route=EvaluationRoute.LOCAL,
            output_text='la neuroplasticidad es la capacidad del cerebro',
            metadata={'tokens_per_second': 50.0},
        )
        result = suite.evaluate(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='benchmark test',
            expected={'text': 'neuroplasticidad capacidad cerebro'},
            candidate=candidate,
        )
        assert result['suite_name'] == 'inference_benchmark_suite'
        assert result['precision'] > 0.0
        assert result['success'] is True
        assert result['metadata']['tokens_per_second'] == 50.0

    def test_suite_fails_with_zero_tps(self):
        suite = InferenceBenchmarkSuite()
        candidate = ExperimentCandidate(
            label='broken-model',
            route=EvaluationRoute.LOCAL,
            output_text='',
            metadata={'tokens_per_second': 0.0},
        )
        result = suite.evaluate(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='benchmark test',
            expected={'text': 'algo'},
            candidate=candidate,
        )
        assert result['success'] is False

    def test_suite_high_tps_boosts_precision(self):
        suite = InferenceBenchmarkSuite()
        slow = ExperimentCandidate(
            label='slow',
            route=EvaluationRoute.LOCAL,
            output_text='respuesta generica',
            metadata={'tokens_per_second': 10.0},
        )
        fast = ExperimentCandidate(
            label='fast',
            route=EvaluationRoute.LOCAL,
            output_text='respuesta generica',
            metadata={'tokens_per_second': 80.0},
        )
        result_slow = suite.evaluate(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='test',
            expected={'text': 'respuesta generica'},
            candidate=slow,
        )
        result_fast = suite.evaluate(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='test',
            expected={'text': 'respuesta generica'},
            candidate=fast,
        )
        assert result_fast['precision'] > result_slow['precision']
