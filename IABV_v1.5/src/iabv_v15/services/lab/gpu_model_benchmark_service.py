"""GPU Model Benchmark Service — auto-descubre y compara modelos locales.

El sistema ejecuta un benchmark estandarizado contra todos los modelos
Ollama instalados, mide tokens/segundo, calidad de respuesta y latencia,
y registra los resultados en el ExperimentLab.  El resultado es una
recomendacion basada en evidencia de cual modelo rinde mejor en el
hardware actual (GPU, VRAM, RAM).

Fuente de verdad: nvidia-smi.  Durante cada prompt se muestrea la GPU
con ``nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,
memory.total,temperature.gpu`` para saber si la inferencia realmente
esta corriendo en la GPU discreta (GPU1 en Task Manager) y no en la
integrada (GPU0).  Si hay discrepancia, se registra como hallazgo
metacognitivo para que el sistema aprenda a detectar su entorno de
forma precisa cuando se mueva a otro laptop.

No crea otro cerebro: usa ExperimentLab existente para persistir y
StrategySelector para recomendar.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
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
        'prompt': (
            'Explica en detalle que es la neuroplasticidad, como funciona '
            'el aprendizaje en el cerebro humano, que tipos de sinapsis '
            'existen y como se forman nuevas conexiones neuronales. '
            'Escribe al menos 6 oraciones completas y detalladas.'
        ),
        'expected': 'neuroplasticidad capacidad cerebro cambiar adaptarse sinapsis conexiones neuronales aprendizaje',
        'category': 'knowledge',
    },
    {
        'prompt': (
            'Escribe una funcion Python completa que implemente el algoritmo '
            'quicksort con documentacion, type hints, y un ejemplo de uso. '
            'Incluye el manejo de listas vacias y un solo elemento. '
            'Explica la complejidad temporal del algoritmo.'
        ),
        'expected': 'def quicksort pivot partition recursion return list base case O(n log n)',
        'category': 'code',
    },
    {
        'prompt': (
            'Resume en 3 oraciones el siguiente texto: '
            '"El aprendizaje automatico es una rama de la inteligencia '
            'artificial que permite a las maquinas aprender patrones de '
            'datos sin ser programadas explicitamente. Usa algoritmos que '
            'mejoran con la experiencia, incluyendo redes neuronales, '
            'arboles de decision, y metodos de ensamble. Las aplicaciones '
            'van desde reconocimiento de imagenes hasta procesamiento de '
            'lenguaje natural y conduccion autonoma."'
        ),
        'expected': 'aprendizaje automatico inteligencia artificial maquinas patrones datos algoritmos redes neuronales',
        'category': 'summarization',
    },
]

_OLLAMA_API_BASE = 'http://127.0.0.1:11434'
_GENERATE_TIMEOUT_SECONDS = 180
_LIST_TIMEOUT_SECONDS = 10
_NUM_PREDICT = 512
_GPU_SAMPLE_INTERVAL_SECONDS = 0.5


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

    # ------------------------------------------------------------------
    # nvidia-smi monitoring
    # ------------------------------------------------------------------

    def query_all_gpus(self) -> list[dict[str, Any]]:
        """Query nvidia-smi for ALL GPUs and return structured data per GPU."""
        nvidia = shutil.which('nvidia-smi')
        if not nvidia:
            return []
        try:
            result = subprocess.run(
                [
                    nvidia,
                    '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu',
                    '--format=csv,noheader,nounits',
                ],
                capture_output=True, text=True, timeout=5,
                encoding='utf-8', errors='ignore', check=False,
            )
        except Exception:
            return []
        if result.returncode != 0:
            return []
        gpus: list[dict[str, Any]] = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 6:
                continue
            try:
                gpus.append({
                    'index': int(parts[0]),
                    'name': parts[1],
                    'utilization_pct': float(parts[2]),
                    'memory_used_mb': int(float(parts[3])),
                    'memory_total_mb': int(float(parts[4])),
                    'temperature_c': float(parts[5]),
                })
            except (ValueError, IndexError):
                continue
        return gpus

    def query_gpu_processes(self) -> list[dict[str, Any]]:
        """Query nvidia-smi for processes using NVIDIA GPU compute."""
        nvidia = shutil.which('nvidia-smi')
        if not nvidia:
            return []
        try:
            result = subprocess.run(
                [nvidia, '--query-compute-apps=pid,name,used_memory',
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5,
                encoding='utf-8', errors='ignore', check=False,
            )
        except Exception:
            return []
        if result.returncode != 0:
            return []
        procs: list[dict[str, Any]] = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                procs.append({
                    'pid': parts[0],
                    'process_name': parts[1],
                    'vram_used_mb': parts[2],
                })
        return procs

    def query_ollama_ps(self) -> list[dict[str, Any]]:
        """Query ``ollama ps`` to check what models are loaded and where."""
        ollama = shutil.which('ollama') or ''
        if not ollama:
            return []
        try:
            result = subprocess.run(
                [ollama, 'ps'],
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
            if len(parts) >= 4:
                models.append({
                    'name': parts[0],
                    'id': parts[1] if len(parts) > 1 else '',
                    'size': parts[2] if len(parts) > 2 else '',
                    'processor': parts[3] if len(parts) > 3 else 'unknown',
                })
        return models

    def _collect_truth_sources(self) -> dict[str, Any]:
        """Collect data from all available truth sources about GPU state."""
        return {
            'nvidia_smi_gpus': self.query_all_gpus(),
            'nvidia_smi_processes': self.query_gpu_processes(),
            'ollama_ps': self.query_ollama_ps(),
        }

    def _cross_reference_sources(
        self,
        *,
        ollama_report: dict[str, Any],
        gpu_samples: list[list[dict[str, Any]]],
        truth_before: dict[str, Any],
        truth_after: dict[str, Any],
    ) -> dict[str, Any]:
        """Cross-reference multiple truth sources to detect discrepancies.

        Compares what Ollama claims (tok/s, eval_count) against:
        - nvidia-smi GPU utilization during inference
        - nvidia-smi compute process list
        - ollama ps (GPU vs CPU loading)
        """
        gpu_analysis = self._analyze_gpu_usage(gpu_samples)
        findings: list[dict[str, str]] = []

        ollama_tps = ollama_report.get('tokens_per_second', 0)
        gpu_used = gpu_analysis.get('gpu_actually_used', False)

        # Finding 1: Ollama claims good tok/s but GPU shows no activity
        if ollama_tps > 10 and not gpu_used:
            findings.append({
                'type': 'discrepancy',
                'severity': 'HIGH',
                'source_a': 'ollama_api',
                'source_b': 'nvidia_smi',
                'detail': (
                    f'Ollama reporta {ollama_tps:.1f} tok/s pero nvidia-smi '
                    f'muestra <5% utilizacion GPU. Inferencia probablemente '
                    f'ejecutandose en CPU, no en GPU NVIDIA.'
                ),
            })

        # Finding 2: ollama ps says model is on CPU
        ollama_ps_after = truth_after.get('ollama_ps', [])
        for m in ollama_ps_after:
            proc = str(m.get('processor', '')).lower()
            if 'cpu' in proc or proc == '0%':
                findings.append({
                    'type': 'discrepancy',
                    'severity': 'HIGH',
                    'source_a': 'ollama_ps',
                    'source_b': 'expected_gpu',
                    'detail': (
                        f'ollama ps muestra modelo {m.get("name", "?")} '
                        f'cargado en processor={proc}. Deberia estar en GPU.'
                    ),
                })
            elif 'gpu' in proc or '%' in proc:
                gpu_pct = proc.replace('gpu', '').replace('%', '').strip()
                findings.append({
                    'type': 'confirmation',
                    'severity': 'INFO',
                    'source_a': 'ollama_ps',
                    'source_b': 'nvidia_smi',
                    'detail': (
                        f'ollama ps confirma modelo {m.get("name", "?")} '
                        f'en GPU (processor={proc}).'
                    ),
                })

        # Finding 3: nvidia-smi processes — is ollama actually using GPU compute?
        procs_after = truth_after.get('nvidia_smi_processes', [])
        ollama_on_gpu = any(
            'ollama' in str(p.get('process_name', '')).lower()
            for p in procs_after
        )
        if procs_after and not ollama_on_gpu:
            findings.append({
                'type': 'discrepancy',
                'severity': 'MEDIUM',
                'source_a': 'nvidia_smi_processes',
                'source_b': 'expected_ollama',
                'detail': (
                    'nvidia-smi --query-compute-apps no muestra ningun '
                    'proceso de Ollama usando GPU compute.'
                ),
            })
        elif ollama_on_gpu:
            findings.append({
                'type': 'confirmation',
                'severity': 'INFO',
                'source_a': 'nvidia_smi_processes',
                'source_b': 'ollama',
                'detail': 'Proceso ollama encontrado en GPU compute apps.',
            })

        # Finding 4: VRAM usage change
        gpus_before = truth_before.get('nvidia_smi_gpus', [])
        gpus_after = truth_after.get('nvidia_smi_gpus', [])
        for ga in gpus_after:
            idx = ga['index']
            gb = next((g for g in gpus_before if g['index'] == idx), None)
            if gb:
                vram_delta = ga['memory_used_mb'] - gb['memory_used_mb']
                if vram_delta > 100:
                    findings.append({
                        'type': 'confirmation',
                        'severity': 'INFO',
                        'source_a': 'nvidia_smi_vram',
                        'source_b': 'before_after_delta',
                        'detail': (
                            f'GPU{idx} ({ga["name"]}): VRAM aumento '
                            f'{vram_delta}MB durante inferencia '
                            f'({gb["memory_used_mb"]}MB -> {ga["memory_used_mb"]}MB).'
                        ),
                    })

        # Overall calibration verdict
        confirmations = sum(1 for f in findings if f['type'] == 'confirmation')
        discrepancies = sum(1 for f in findings if f['type'] == 'discrepancy')
        high_discrepancies = sum(
            1 for f in findings
            if f['type'] == 'discrepancy' and f['severity'] == 'HIGH'
        )

        calibrated = discrepancies == 0 or (confirmations > discrepancies)

        return {
            'calibrated': calibrated,
            'confirmations': confirmations,
            'discrepancies': discrepancies,
            'high_severity_discrepancies': high_discrepancies,
            'findings': findings,
            'gpu_analysis': gpu_analysis,
            'verdict': (
                'CALIBRADO: todas las fuentes coinciden'
                if calibrated and discrepancies == 0
                else f'PARCIALMENTE CALIBRADO: {confirmations} confirmaciones vs {discrepancies} discrepancias'
                if calibrated
                else f'NO CALIBRADO: {high_discrepancies} discrepancias graves detectadas — '
                     f'el sistema puede estar confiando en datos incorrectos'
            ),
        }

    def _sample_gpu_during(
        self,
        target_fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, list[list[dict[str, Any]]]]:
        """Run *target_fn* while sampling nvidia-smi in a background thread.

        Returns ``(fn_result, gpu_samples)`` where *gpu_samples* is a list
        of snapshots, each snapshot being a list of per-GPU dicts.
        """
        samples: list[list[dict[str, Any]]] = []
        stop_event = threading.Event()

        def _sampler() -> None:
            while not stop_event.is_set():
                snap = self.query_all_gpus()
                if snap:
                    samples.append(snap)
                stop_event.wait(_GPU_SAMPLE_INTERVAL_SECONDS)

        sampler_thread = threading.Thread(target=_sampler, daemon=True)
        sampler_thread.start()
        try:
            result = target_fn(*args, **kwargs)
        finally:
            stop_event.set()
            sampler_thread.join(timeout=2)
        return result, samples

    def _analyze_gpu_usage(
        self,
        samples: list[list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Analyze sampled GPU data to determine which GPU was active."""
        if not samples:
            return {
                'nvidia_smi_available': False,
                'active_gpu_index': None,
                'gpu_actually_used': False,
                'discrepancy': 'nvidia-smi no disponible o no devolvio datos',
            }

        gpu_peak: dict[int, float] = {}
        gpu_peak_mem: dict[int, int] = {}
        gpu_names: dict[int, str] = {}
        gpu_avg_util: dict[int, list[float]] = {}

        for snapshot in samples:
            for gpu in snapshot:
                idx = gpu['index']
                gpu_names[idx] = gpu['name']
                util = gpu['utilization_pct']
                mem = gpu['memory_used_mb']
                gpu_peak[idx] = max(gpu_peak.get(idx, 0), util)
                gpu_peak_mem[idx] = max(gpu_peak_mem.get(idx, 0), mem)
                if idx not in gpu_avg_util:
                    gpu_avg_util[idx] = []
                gpu_avg_util[idx].append(util)

        active_idx = max(gpu_peak, key=lambda i: gpu_peak[i]) if gpu_peak else None
        avg_utils = {
            idx: sum(vals) / len(vals) for idx, vals in gpu_avg_util.items()
        }

        gpu_used = active_idx is not None and gpu_peak.get(active_idx, 0) > 5.0

        return {
            'nvidia_smi_available': True,
            'active_gpu_index': active_idx,
            'active_gpu_name': gpu_names.get(active_idx, 'unknown') if active_idx is not None else None,
            'gpu_actually_used': gpu_used,
            'samples_count': len(samples),
            'per_gpu': {
                idx: {
                    'name': gpu_names[idx],
                    'peak_utilization_pct': round(gpu_peak[idx], 1),
                    'avg_utilization_pct': round(avg_utils.get(idx, 0), 1),
                    'peak_memory_used_mb': gpu_peak_mem.get(idx, 0),
                }
                for idx in sorted(gpu_names)
            },
            'discrepancy': None if gpu_used else 'GPU utilization < 5% durante inferencia — posible ejecucion en CPU',
        }

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
        """Run benchmark prompts against a single model and return metrics.

        GPU utilization is sampled via nvidia-smi during each prompt to
        provide ground-truth data about which GPU is really active.
        """
        prompts = prompts or _BENCHMARK_PROMPTS
        results: list[dict[str, Any]] = []
        all_gpu_samples: list[list[dict[str, Any]]] = []

        truth_before = self._collect_truth_sources()

        for prompt_spec in prompts:
            prompt = prompt_spec['prompt']
            expected_keywords = prompt_spec.get('expected', '')
            category = prompt_spec.get('category', 'general')

            start = time.perf_counter()
            (output_text, token_count, eval_duration_ns), gpu_samples = (
                self._sample_gpu_during(
                    self._ollama_generate, model_name, prompt,
                )
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            all_gpu_samples.extend(gpu_samples)

            tokens_per_second = 0.0
            if eval_duration_ns and eval_duration_ns > 0 and token_count > 0:
                tokens_per_second = token_count / (eval_duration_ns / 1e9)

            keyword_hits = sum(
                1 for kw in expected_keywords.split()
                if kw.strip() and kw.strip().lower() in output_text.lower()
            )
            total_keywords = max(len(expected_keywords.split()), 1)
            quality_score = keyword_hits / total_keywords

            prompt_gpu_analysis = self._analyze_gpu_usage(gpu_samples)

            results.append({
                'category': category,
                'prompt': prompt[:120],
                'output_text': output_text[:500],
                'tokens_per_second': round(tokens_per_second, 2),
                'token_count': token_count,
                'elapsed_ms': elapsed_ms,
                'quality_score': round(quality_score, 4),
                'gpu_during_inference': prompt_gpu_analysis,
            })

        avg_tps = sum(r['tokens_per_second'] for r in results) / max(len(results), 1)
        avg_quality = sum(r['quality_score'] for r in results) / max(len(results), 1)
        avg_latency = sum(r['elapsed_ms'] for r in results) / max(len(results), 1)

        truth_after = self._collect_truth_sources()

        cross_ref = self._cross_reference_sources(
            ollama_report={'tokens_per_second': avg_tps, 'model': model_name},
            gpu_samples=all_gpu_samples,
            truth_before=truth_before,
            truth_after=truth_after,
        )

        return {
            'model_name': model_name,
            'avg_tokens_per_second': round(avg_tps, 2),
            'avg_quality_score': round(avg_quality, 4),
            'avg_latency_ms': int(avg_latency),
            'prompt_count': len(results),
            'details': results,
            'gpu_ground_truth': {
                'truth_sources_before': truth_before,
                'truth_sources_after': truth_after,
                'during_inference': cross_ref.get('gpu_analysis', {}),
                'cross_reference': cross_ref,
            },
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

        gpu_findings: list[dict[str, str]] = []
        for r in benchmark_results:
            cross_ref = r.get('gpu_ground_truth', {}).get('cross_reference', {})
            for finding in cross_ref.get('findings', []):
                gpu_findings.append({
                    'model': r['model_name'],
                    'finding': finding.get('detail', ''),
                    'severity': finding.get('severity', 'INFO'),
                    'type': finding.get('type', 'unknown'),
                    'sources': f'{finding.get("source_a", "?")} vs {finding.get("source_b", "?")}',
                })

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
                    'calibration_verdict': r.get('gpu_ground_truth', {}).get('cross_reference', {}).get('verdict', 'unknown'),
                    'gpu_ground_truth': r.get('gpu_ground_truth', {}).get('during_inference', {}),
                }
                for r in ranked
            ],
            'gpu_findings': gpu_findings,
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
            'options': {'num_predict': _NUM_PREDICT},
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
