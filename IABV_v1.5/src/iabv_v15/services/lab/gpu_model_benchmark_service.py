"""GPU Model Benchmark Service — auto-descubre y compara modelos locales.

El sistema ejecuta un benchmark estandarizado contra todos los modelos
Ollama instalados, mide tokens/segundo, calidad de respuesta y latencia,
y registra los resultados en el ExperimentLab.  El resultado es una
recomendacion basada en evidencia de cual modelo rinde mejor en el
hardware actual (GPU, VRAM, RAM).

No crea otro cerebro: usa ExperimentLab existente para persistir y
StrategySelector para recomendar.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from typing import Any

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentCandidate,
    ExperimentDomain,
    ExperimentRecommendation,
    ExperimentRun,
)
from iabv_v15.services.lab.experiment_lab import ExperimentLab

logger = logging.getLogger(__name__)

_BENCHMARK_PROMPTS: list[dict[str, str]] = [
    {
        'prompt': 'Explica en 3 oraciones que es la neuroplasticidad.',
        'expected': 'neuroplasticidad capacidad cerebro cambiar adaptarse',
        'category': 'knowledge',
    },
    {
        'prompt': 'Escribe una funcion Python que calcule el factorial de un numero usando recursion.',
        'expected': 'def factorial recursion return base case',
        'category': 'code',
    },
    {
        'prompt': 'Resume en una oracion: "El aprendizaje automatico permite que las maquinas aprendan patrones de datos sin ser programadas explicitamente."',
        'expected': 'aprendizaje automatico maquinas patrones datos',
        'category': 'summarization',
    },
]

_OLLAMA_API_BASE = 'http://127.0.0.1:11434'
_GENERATE_TIMEOUT_SECONDS = 120
_LIST_TIMEOUT_SECONDS = 10


class GpuModelBenchmarkService:
    """Benchmarks all locally installed Ollama models and ranks them."""

    def __init__(
        self,
        *,
        experiment_lab: ExperimentLab,
        ollama_api_base: str = _OLLAMA_API_BASE,
    ) -> None:
        self.experiment_lab = experiment_lab
        self.ollama_api_base = ollama_api_base.rstrip('/')

    def discover_models(self) -> list[dict[str, Any]]:
        """Return list of installed Ollama models with metadata."""
        ollama_bin = shutil.which('ollama') or ''
        if not ollama_bin:
            return []
        try:
            result = subprocess.run(
                [ollama_bin, 'list'],
                capture_output=True, text=True, timeout=_LIST_TIMEOUT_SECONDS,
                encoding='utf-8', errors='ignore', check=False,
            )
        except Exception:
            return []
        if result.returncode != 0:
            return []
        models: list[dict[str, Any]] = []
        for line in result.stdout.splitlines()[1:]:
            parts = [p for p in line.split() if p]
            if not parts:
                continue
            name = parts[0]
            size = parts[2] if len(parts) > 2 else ''
            models.append({'name': name, 'size': size})
        return models

    def benchmark_model(
        self,
        model_name: str,
        *,
        prompts: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Run benchmark prompts against a single model and return metrics."""
        prompts = prompts or _BENCHMARK_PROMPTS
        results: list[dict[str, Any]] = []

        for prompt_spec in prompts:
            prompt = prompt_spec['prompt']
            expected_keywords = prompt_spec.get('expected', '')
            category = prompt_spec.get('category', 'general')

            start = time.perf_counter()
            output_text, token_count, eval_duration_ns = self._ollama_generate(
                model_name, prompt,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            tokens_per_second = 0.0
            if eval_duration_ns and eval_duration_ns > 0 and token_count > 0:
                tokens_per_second = token_count / (eval_duration_ns / 1e9)

            keyword_hits = sum(
                1 for kw in expected_keywords.split()
                if kw.strip() and kw.strip().lower() in output_text.lower()
            )
            total_keywords = max(len(expected_keywords.split()), 1)
            quality_score = keyword_hits / total_keywords

            results.append({
                'category': category,
                'prompt': prompt[:120],
                'output_text': output_text[:500],
                'tokens_per_second': round(tokens_per_second, 2),
                'token_count': token_count,
                'elapsed_ms': elapsed_ms,
                'quality_score': round(quality_score, 4),
            })

        avg_tps = sum(r['tokens_per_second'] for r in results) / max(len(results), 1)
        avg_quality = sum(r['quality_score'] for r in results) / max(len(results), 1)
        avg_latency = sum(r['elapsed_ms'] for r in results) / max(len(results), 1)

        return {
            'model_name': model_name,
            'avg_tokens_per_second': round(avg_tps, 2),
            'avg_quality_score': round(avg_quality, 4),
            'avg_latency_ms': int(avg_latency),
            'prompt_count': len(results),
            'details': results,
        }

    def run_full_benchmark(
        self,
        *,
        models: list[str] | None = None,
    ) -> dict[str, Any]:
        """Benchmark all (or specified) models and register via ExperimentLab.

        Returns a summary with ranked results and the ExperimentLab
        recommendation.
        """
        if models is None:
            discovered = self.discover_models()
            models = [m['name'] for m in discovered]

        if not models:
            return {
                'status': 'no_models',
                'message': 'No se encontraron modelos Ollama instalados.',
                'ranked': [],
                'recommendation': None,
            }

        benchmark_results: list[dict[str, Any]] = []
        candidates: list[ExperimentCandidate] = []

        for model_name in models:
            logger.info('gpu_model_benchmark: benchmarking %s', model_name)
            try:
                result = self.benchmark_model(model_name)
            except Exception as exc:
                logger.warning('gpu_model_benchmark: %s failed: %s', model_name, exc)
                continue
            benchmark_results.append(result)

            tps = result['avg_tokens_per_second']
            quality = result['avg_quality_score']
            composite_score = quality * 0.5 + min(tps / 100.0, 1.0) * 0.3 + min(1.0, 5000.0 / max(result['avg_latency_ms'], 1)) * 0.2

            candidates.append(ExperimentCandidate(
                label=model_name,
                route=EvaluationRoute.LOCAL,
                assistant_kind=model_name.split(':')[0],
                output_text=result['details'][0]['output_text'] if result['details'] else '',
                execution_ms=result['avg_latency_ms'],
                operational_cost=0.0,
                extracted_data={
                    'text': result['details'][0]['output_text'][:240] if result['details'] else '',
                },
                metadata={
                    'tokens_per_second': tps,
                    'quality_score': quality,
                    'composite_score': round(composite_score, 4),
                    'assistant_kind': model_name.split(':')[0],
                    'benchmark_type': 'gpu_model_benchmark',
                },
            ))

        if not candidates:
            return {
                'status': 'all_failed',
                'message': 'Todos los modelos fallaron durante el benchmark.',
                'ranked': [],
                'recommendation': None,
            }

        runs, recommendation = self.experiment_lab.run_experiment(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='Determinar el modelo Ollama con mejor rendimiento (tok/s + calidad) en el hardware actual',
            subject_key='gpu_model_selection',
            expected={'text': 'respuesta coherente y completa'},
            candidates=candidates,
        )

        ranked = sorted(
            benchmark_results,
            key=lambda r: (
                r['avg_quality_score'] * 0.5
                + min(r['avg_tokens_per_second'] / 100.0, 1.0) * 0.3
                + min(1.0, 5000.0 / max(r['avg_latency_ms'], 1)) * 0.2
            ),
            reverse=True,
        )

        best = ranked[0] if ranked else None
        summary = self._build_summary(ranked, recommendation)

        return {
            'status': 'completed',
            'message': summary,
            'best_model': best['model_name'] if best else None,
            'best_tokens_per_second': best['avg_tokens_per_second'] if best else 0,
            'best_quality_score': best['avg_quality_score'] if best else 0,
            'ranked': [
                {
                    'model': r['model_name'],
                    'tokens_per_second': r['avg_tokens_per_second'],
                    'quality_score': r['avg_quality_score'],
                    'latency_ms': r['avg_latency_ms'],
                }
                for r in ranked
            ],
            'experiment_runs': len(runs),
            'recommendation': {
                'recommended_route': recommendation.recommended_route.value,
                'rationale': recommendation.rationale,
                'recommended_assistant_kind': recommendation.recommended_assistant_kind,
            } if recommendation else None,
        }

    def _ollama_generate(
        self,
        model: str,
        prompt: str,
    ) -> tuple[str, int, int]:
        """Call Ollama generate API and return (text, token_count, eval_duration_ns)."""
        import urllib.request

        payload = json.dumps({
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {'num_predict': 256},
        }).encode('utf-8')

        url = f'{self.ollama_api_base}/api/generate'
        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=_GENERATE_TIMEOUT_SECONDS) as resp:
                body = json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            logger.warning('ollama_generate failed for %s: %s', model, exc)
            return '', 0, 0

        text = str(body.get('response') or '')
        eval_count = int(body.get('eval_count') or 0)
        eval_duration = int(body.get('eval_duration') or 0)
        return text, eval_count, eval_duration

    def _build_summary(
        self,
        ranked: list[dict[str, Any]],
        recommendation: ExperimentRecommendation | None,
    ) -> str:
        if not ranked:
            return 'No hay resultados de benchmark.'
        lines = ['Resultados del benchmark GPU de modelos locales:\n']
        for i, r in enumerate(ranked, 1):
            medal = {1: '(mejor)', 2: '', 3: ''}.get(i, '')
            lines.append(
                f'  {i}. {r["model_name"]} — '
                f'{r["avg_tokens_per_second"]:.1f} tok/s, '
                f'calidad {r["avg_quality_score"]:.0%}, '
                f'latencia {r["avg_latency_ms"]}ms '
                f'{medal}'
            )
        if recommendation:
            lines.append(
                f'\nRecomendacion del ExperimentLab: '
                f'{recommendation.recommended_assistant_kind or recommendation.recommended_route.value}'
            )
            lines.append(f'Justificacion: {recommendation.rationale}')
        return '\n'.join(lines)
