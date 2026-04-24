"""GPU Auto-Benchmark — Auto-diagnóstico, corrección y benchmark con cruce de fuentes.

Ejecutar directamente:
    cd C:\\Python\\IABV_v1.5
    $env:PYTHONPATH='src'
    python scripts/gpu_auto_benchmark.py

Este script:
1. Auto-diagnostica la configuración GPU (CUDA_VISIBLE_DEVICES, nvidia-smi, ollama ps)
2. Si encuentra errores, intenta corregirlos automáticamente
3. Ejecuta un benchmark contra modelos Ollama con monitoreo GPU en tiempo real
4. Cruza TODAS las fuentes de verdad durante la inferencia
5. Genera un reporte con hallazgos metacognitivos
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

# ---------------------------------------------------------------------------
# Colores para output
# ---------------------------------------------------------------------------
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'


def p(color: str, msg: str) -> None:
    print(f'{color}{msg}{RESET}', flush=True)


# ---------------------------------------------------------------------------
# Fuentes de verdad
# ---------------------------------------------------------------------------

def query_nvidia_smi() -> list[dict]:
    nvidia = shutil.which('nvidia-smi')
    if not nvidia:
        return []
    try:
        r = subprocess.run(
            [nvidia, '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    gpus = []
    for line in r.stdout.strip().splitlines():
        parts = [x.strip() for x in line.split(',')]
        if len(parts) >= 6:
            gpus.append({
                'index': int(parts[0]), 'name': parts[1],
                'util_pct': float(parts[2]),
                'mem_used_mb': int(float(parts[3])),
                'mem_total_mb': int(float(parts[4])),
                'temp_c': float(parts[5]),
            })
    return gpus


def query_nvidia_processes() -> list[dict]:
    nvidia = shutil.which('nvidia-smi')
    if not nvidia:
        return []
    try:
        r = subprocess.run(
            [nvidia, '--query-compute-apps=pid,process_name,used_memory',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    procs = []
    for line in r.stdout.strip().splitlines():
        parts = [x.strip() for x in line.split(',')]
        if len(parts) >= 3:
            procs.append({'pid': parts[0], 'name': parts[1], 'vram_mb': parts[2]})
    return procs


def query_ollama_ps() -> str:
    ollama = shutil.which('ollama')
    if not ollama:
        return 'ollama not found'
    try:
        r = subprocess.run([ollama, 'ps'], capture_output=True, text=True, timeout=10, check=False)
        return r.stdout.strip()
    except Exception as e:
        return f'error: {e}'


def parse_ollama_ps_processor(ps_output: str) -> list[dict]:
    """Parse ollama ps using column-position parsing (handles multi-word fields)."""
    lines = ps_output.splitlines()
    if not lines:
        return []
    header = lines[0]
    col_names = ['NAME', 'ID', 'SIZE', 'PROCESSOR', 'CONTEXT', 'UNTIL']
    col_starts = []
    for cn in col_names:
        pos = header.find(cn)
        col_starts.append(pos if pos >= 0 else -1)
    models = []
    for line in lines[1:]:
        if not line.strip():
            continue
        vals = {}
        for i, cn in enumerate(col_names):
            start = col_starts[i]
            if start < 0:
                continue
            end = col_starts[i + 1] if i + 1 < len(col_starts) and col_starts[i + 1] >= 0 else len(line)
            vals[cn.lower()] = line[start:end].strip()
        if vals.get('name'):
            models.append(vals)
    return models


def run_inference(model: str, prompt: str, num_predict: int = 256) -> dict:
    """Run Ollama inference and sample nvidia-smi during execution."""
    payload = json.dumps({
        'model': model, 'prompt': prompt, 'stream': False,
        'options': {'num_predict': num_predict},
    }).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/generate',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )

    samples: list[dict] = []
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            gpus = query_nvidia_smi()
            samples.append({
                't': round(time.time(), 2),
                'gpus': gpus,
            })
            stop.wait(0.3)

    t = threading.Thread(target=sampler, daemon=True)
    t.start()

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        elapsed = time.perf_counter() - start
        eval_count = body.get('eval_count', 0)
        eval_ns = body.get('eval_duration', 0)
        tps = round(eval_count / (eval_ns / 1e9), 2) if eval_ns > 0 else 0
        result = {'ok': True, 'tokens': eval_count, 'tps': tps, 'elapsed_s': round(elapsed, 2)}
    except Exception as ex:
        result = {'ok': False, 'error': str(ex)}

    stop.set()
    t.join(2)

    # Analyze GPU samples
    peak_utils = {}
    avg_utils = {}
    for s in samples:
        for g in s['gpus']:
            idx = g['index']
            peak_utils[idx] = max(peak_utils.get(idx, 0), g['util_pct'])
            if idx not in avg_utils:
                avg_utils[idx] = []
            avg_utils[idx].append(g['util_pct'])

    for idx in avg_utils:
        avg_utils[idx] = round(sum(avg_utils[idx]) / len(avg_utils[idx]), 1)

    result['gpu_samples_count'] = len(samples)
    result['peak_util_per_gpu'] = peak_utils
    result['avg_util_per_gpu'] = avg_utils
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p(BOLD + CYAN, '=' * 60)
    p(BOLD + CYAN, '  IABV v1.5 — GPU Auto-Benchmark + Metacognición')
    p(BOLD + CYAN, '=' * 60)
    print()

    # === PHASE 1: Auto-diagnosis ===
    p(BOLD, '▸ FASE 1: Auto-diagnóstico GPU (cruce de fuentes)')
    print()

    cuda_vis = os.environ.get('CUDA_VISIBLE_DEVICES', '')
    gpus = query_nvidia_smi()
    procs = query_nvidia_processes()
    ollama_raw = query_ollama_ps()
    ollama_models = parse_ollama_ps_processor(ollama_raw)

    findings = []

    # Source 1: nvidia-smi GPUs
    p(CYAN, f'  [nvidia-smi GPUs] {len(gpus)} GPU(s) detectada(s):')
    for g in gpus:
        p(CYAN, f'    GPU{g["index"]}: {g["name"]} — {g["util_pct"]}% util, '
              f'{g["mem_used_mb"]}MB/{g["mem_total_mb"]}MB VRAM, {g["temp_c"]}°C')

    # Source 2: nvidia-smi processes
    p(CYAN, f'  [nvidia-smi procs] {len(procs)} proceso(s) usando GPU:')
    for pr in procs:
        p(CYAN, f'    PID {pr["pid"]}: {pr["name"]} ({pr["vram_mb"]}MB)')
    if not procs:
        p(YELLOW, '    (ningún proceso usando GPU compute)')

    # Source 3: ollama ps
    p(CYAN, f'  [ollama ps] Modelos cargados:')
    for m in ollama_models:
        processor = m.get('processor', '?')
        color = GREEN if 'gpu' in processor.lower() else RED
        p(color, f'    {m.get("name", "?")} → processor={processor}, size={m.get("size", "?")}')
    if not ollama_models:
        p(YELLOW, '    (ningún modelo cargado)')

    # Source 4: CUDA_VISIBLE_DEVICES
    p(CYAN, f'  [CUDA_VISIBLE_DEVICES] = "{cuda_vis or "(no set)"}"')
    nvidia_indices = {g['index'] for g in gpus}
    if cuda_vis:
        try:
            requested = [int(x.strip()) for x in cuda_vis.split(',') if x.strip()]
            invalid = [i for i in requested if i not in nvidia_indices]
            if invalid:
                findings.append({
                    'type': 'misconfiguration', 'severity': 'HIGH',
                    'detail': f'CUDA_VISIBLE_DEVICES={cuda_vis} apunta a GPU(s) '
                              f'{invalid} que NO existen (reales: {sorted(nvidia_indices)}). '
                              f'Task Manager GPU1=NVIDIA pero CUDA GPU0=NVIDIA.',
                    'action': 'AUTO-FIX: limpiando CUDA_VISIBLE_DEVICES',
                })
                os.environ.pop('CUDA_VISIBLE_DEVICES', None)
                p(RED, f'    ⚠ HALLAZGO: índices {invalid} no existen en nvidia-smi!')
                p(GREEN, f'    → AUTO-FIX: removido CUDA_VISIBLE_DEVICES del environment')
        except ValueError:
            pass
    else:
        p(GREEN, '    OK — sin override, auto-detect activo')

    # Source 5: Cross-reference — ollama ps dice CPU pero hay GPU disponible?
    for m in ollama_models:
        proc = m.get('processor', '').lower()
        if 'cpu' in proc and gpus:
            gpu_free = max(g['mem_total_mb'] - g['mem_used_mb'] for g in gpus)
            findings.append({
                'type': 'discrepancy', 'severity': 'HIGH',
                'detail': f'Modelo {m.get("name")} cargado en CPU pero hay '
                          f'{gpu_free}MB VRAM libre. Ollama no está usando la GPU.',
            })
            p(RED, f'    ⚠ HALLAZGO: {m.get("name")} en CPU con {gpu_free}MB VRAM libre!')

    print()
    if findings:
        p(RED + BOLD, f'  DIAGNÓSTICO: {len(findings)} problema(s) encontrado(s)')
        for f in findings:
            p(RED, f'    [{f["severity"]}] {f["detail"]}')
    else:
        p(GREEN + BOLD, '  DIAGNÓSTICO: GPU configurada correctamente')
    print()

    # === PHASE 2: Benchmark ===
    p(BOLD, '▸ FASE 2: Benchmark con monitoreo GPU en tiempo real')
    p(BOLD, '  (Observa Task Manager → GPU1 mientras corre)')
    print()

    prompt = (
        'Explica en detalle qué es la neuroplasticidad cerebral, '
        'cómo el cerebro forma nuevas conexiones sinápticas durante el aprendizaje, '
        'y cómo la repetición fortalece las redes neuronales. '
        'Incluye ejemplos concretos de cómo esto aplica en la vida real.'
    )

    # Get available models
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=10) as resp:
            tags = json.loads(resp.read())
        available = [m['name'] for m in tags.get('models', [])]
    except Exception:
        available = ['gemma3:4b']

    # Filter: only test models that fit in 6GB VRAM
    test_models = [m for m in available if any(k in m for k in ['gemma3', 'qwen2.5-coder', 'qwen3'])]
    if not test_models:
        test_models = available[:3]

    p(CYAN, f'  Modelos a probar: {test_models}')
    print()

    gpu_before = query_nvidia_smi()
    benchmark_results = []

    for model in test_models:
        p(YELLOW, f'  ▸ Probando {model}...')

        # Before
        ps_before = query_ollama_ps()

        # Run inference with GPU sampling
        result = run_inference(model, prompt, num_predict=256)
        result['model'] = model

        # After
        ps_after = query_ollama_ps()
        gpu_after_model = query_nvidia_smi()
        procs_after = query_nvidia_processes()

        # Parse ollama ps processor
        models_after = parse_ollama_ps_processor(ps_after)
        model_proc = 'unknown'
        for ma in models_after:
            if model.split(':')[0] in ma.get('name', ''):
                model_proc = ma.get('processor', '?')
                break

        result['ollama_processor'] = model_proc
        result['gpu_processes_after'] = procs_after

        # Cross-reference verdict
        if result.get('ok'):
            tps = result['tps']
            any_gpu = any(v > 5 for v in result.get('peak_util_per_gpu', {}).values())
            ollama_says_gpu = 'gpu' in model_proc.lower()
            ollama_in_compute = any('ollama' in p.get('name', '').lower() for p in procs_after)

            # Count agreements
            sources = {
                'nvidia_smi_util': any_gpu,
                'ollama_ps': ollama_says_gpu,
                'nvidia_compute_apps': ollama_in_compute,
            }
            agree_gpu = sum(1 for v in sources.values() if v)
            agree_cpu = sum(1 for v in sources.values() if not v)

            if agree_gpu >= 2:
                result['verdict'] = f'CALIBRADO (GPU): {agree_gpu}/3 fuentes confirman GPU activa'
                color = GREEN
            elif agree_cpu >= 2:
                result['verdict'] = f'NO CALIBRADO (CPU): {agree_cpu}/3 fuentes indican CPU'
                color = RED
            else:
                result['verdict'] = 'PARCIAL: fuentes no concuerdan'
                color = YELLOW

            result['sources'] = sources
            p(color, f'    → {result["verdict"]}')
            p(CYAN, f'    → {tps} tok/s, {result["tokens"]} tokens en {result["elapsed_s"]}s')
            p(CYAN, f'    → Peak GPU util: {result.get("peak_util_per_gpu", {})}')
            p(CYAN, f'    → Avg GPU util: {result.get("avg_util_per_gpu", {})}')
            p(CYAN, f'    → ollama ps processor: {model_proc}')
            p(CYAN, f'    → nvidia compute apps: {[p["name"] for p in procs_after]}')
        else:
            p(RED, f'    → ERROR: {result.get("error", "?")}')

        benchmark_results.append(result)
        print()

    # === PHASE 3: Final report ===
    p(BOLD, '▸ FASE 3: Reporte final')
    print()

    # Ranking by tok/s
    ok_results = [r for r in benchmark_results if r.get('ok')]
    ok_results.sort(key=lambda r: r.get('tps', 0), reverse=True)

    if ok_results:
        p(GREEN + BOLD, '  Ranking por velocidad (tok/s):')
        for i, r in enumerate(ok_results, 1):
            p(GREEN, f'    {i}. {r["model"]}: {r["tps"]} tok/s — {r["verdict"]}')
        print()
        best = ok_results[0]
        p(GREEN + BOLD, f'  Mejor modelo: {best["model"]} ({best["tps"]} tok/s)')
    else:
        p(RED, '  No se completó ningún benchmark exitosamente')

    # Summary of findings
    print()
    p(BOLD, '  Hallazgos metacognitivos:')
    if findings:
        for f in findings:
            p(RED, f'    [{f["severity"]}] {f["detail"]}')
    else:
        p(GREEN, '    Ninguna discrepancia encontrada — fuentes de verdad alineadas')

    print()
    p(BOLD + CYAN, '=' * 60)

    # Save results
    report = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'diagnosis_findings': findings,
        'benchmark': benchmark_results,
        'best_model': ok_results[0]['model'] if ok_results else None,
        'best_tps': ok_results[0]['tps'] if ok_results else None,
    }
    report_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gpu_benchmark_report.json')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    p(CYAN, f'  Reporte guardado en: {os.path.abspath(report_path)}')
    print()


if __name__ == '__main__':
    main()
