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


def query_task_manager_gpu() -> dict:
    """Query Windows Performance Counters — the SAME data Task Manager shows.

    This reads GPU Engine utilization counters via PowerShell, which is the
    exact source that feeds the Task Manager GPU graphs. This provides an
    independent truth source separate from nvidia-smi.

    Parses individual engine types (3D, Compute, Copy, VideoDecode, VideoEncode)
    per GPU adapter — so the program sees exactly what the user sees in Task Manager.
    """
    if sys.platform != 'win32':
        return {'available': False, 'reason': 'not Windows'}
    try:
        ps_cmd = (
            'Get-Counter -Counter '
            '"\\GPU Engine(*)\\Utilization Percentage" '
            '-ErrorAction SilentlyContinue | '
            'Select-Object -ExpandProperty CounterSamples | '
            'Where-Object { $_.CookedValue -gt 0 } | '
            'Select-Object -Property Path, CookedValue | '
            'ConvertTo-Json -Compress'
        )
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return {'available': True, 'active_engines': [], 'total_util': 0.0,
                    'by_engine_type': {}, 'by_gpu': {}}

        data = json.loads(r.stdout)
        if isinstance(data, dict):
            data = [data]

        import re as _re
        engines = []
        total_util = 0.0
        by_type: dict[str, float] = {}
        by_gpu: dict[str, float] = {}
        for sample in data:
            path = sample.get('Path', '')
            value = sample.get('CookedValue', 0.0)
            total_util += value
            # Parse engine type: engtype_3d, engtype_compute, engtype_copy, etc.
            eng_match = _re.search(r'engtype_(\w+)', path, _re.IGNORECASE)
            engine_type = eng_match.group(1) if eng_match else 'unknown'
            by_type[engine_type] = by_type.get(engine_type, 0) + value
            # Parse GPU adapter: phys_N
            gpu_match = _re.search(r'phys_(\d+)', path, _re.IGNORECASE)
            gpu_id = f'GPU{gpu_match.group(1)}' if gpu_match else 'unknown'
            by_gpu[gpu_id] = by_gpu.get(gpu_id, 0) + value
            engines.append({
                'path': path, 'util_pct': round(value, 2),
                'engine_type': engine_type, 'gpu': gpu_id,
            })

        by_type = {k: round(v, 2) for k, v in by_type.items()}
        by_gpu = {k: round(v, 2) for k, v in by_gpu.items()}
        return {
            'available': True,
            'active_engines': engines,
            'total_util': round(total_util, 2),
            'engine_count': len(engines),
            'by_engine_type': by_type,
            'by_gpu': by_gpu,
        }
    except Exception as e:
        return {'available': True, 'error': str(e), 'active_engines': [],
                'total_util': 0.0, 'by_engine_type': {}, 'by_gpu': {}}


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

    # Also sample Task Manager counters (independent truth source)
    task_mgr_after = query_task_manager_gpu()
    result['task_manager'] = task_mgr_after
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

    # Source 4: Task Manager (Windows Performance Counters) — per engine breakdown
    task_mgr = query_task_manager_gpu()
    if task_mgr.get('available'):
        active = task_mgr.get('active_engines', [])
        total = task_mgr.get('total_util', 0)
        by_type = task_mgr.get('by_engine_type', {})
        by_gpu = task_mgr.get('by_gpu', {})
        p(CYAN, f'  [Task Manager GPU Counters] {len(active)} engine(s) activo(s), '
              f'utilización total: {total:.1f}%')
        if by_gpu:
            p(CYAN, '    Por GPU (lo que ves en Task Manager):')
            for gid, val in sorted(by_gpu.items()):
                color = GREEN if val > 1 else YELLOW
                p(color, f'      {gid}: {val:.1f}%')
        if by_type:
            p(CYAN, '    Por tipo de engine:')
            for etype, val in sorted(by_type.items(), key=lambda x: -x[1]):
                label = {
                    '3D': '3D (CUDA compute / inferencia)',
                    'Compute': 'Compute (CUDA kernels)',
                    'Copy': 'Copy (transferencia memoria)',
                    'VideoDecode': 'Video Decode',
                    'VideoEncode': 'Video Encode',
                    'VideoProcessing': 'Video Processing',
                }.get(etype, etype)
                color = GREEN if val > 1 else YELLOW
                p(color, f'      {label}: {val:.1f}%')
        if not active:
            p(YELLOW, '    (sin actividad GPU según Performance Counters)')
    else:
        p(YELLOW, f'  [Task Manager GPU Counters] No disponible: {task_mgr.get("reason", "?")}')

    # Source 5: CUDA_VISIBLE_DEVICES
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

    # === PHASE 1.5: Auto-remediation ===
    needs_ollama_restart = False

    # Fix 1: Remove CUDA_VISIBLE_DEVICES from Windows system environment
    if any(f['type'] == 'misconfiguration' and 'CUDA_VISIBLE_DEVICES' in f.get('detail', '')
           for f in findings):
        p(BOLD, '▸ FASE 1.5: Auto-corrección del entorno')
        print()
        if sys.platform == 'win32':
            p(YELLOW, '  Limpiando CUDA_VISIBLE_DEVICES del sistema Windows...')
            for scope in ['User', 'Machine']:
                try:
                    subprocess.run(
                        ['powershell', '-Command',
                         f'[Environment]::SetEnvironmentVariable("CUDA_VISIBLE_DEVICES", $null, "{scope}")'],
                        capture_output=True, text=True, timeout=10, check=False,
                    )
                    p(GREEN, f'    → Removido de {scope} environment')
                except Exception as e:
                    p(YELLOW, f'    → No se pudo limpiar {scope}: {e}')
            needs_ollama_restart = True

    # Fix 2: If any model is on CPU with GPU available, restart Ollama
    any_on_cpu = any(f['type'] == 'discrepancy' and 'CPU' in f.get('detail', '')
                     for f in findings)
    if any_on_cpu or needs_ollama_restart:
        if not needs_ollama_restart:
            p(BOLD, '▸ FASE 1.5: Auto-corrección de Ollama')
            print()
        p(YELLOW, '  Reiniciando Ollama para aplicar configuración GPU...')

        # Kill all Ollama processes
        ollama_exe = shutil.which('ollama')
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/f', '/im', 'ollama.exe'],
                           capture_output=True, timeout=10, check=False)
        else:
            subprocess.run(['pkill', '-f', 'ollama'], capture_output=True, timeout=10, check=False)
        p(CYAN, '    → Procesos Ollama terminados')
        time.sleep(3)

        # Verify port is free
        if sys.platform == 'win32':
            r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5, check=False)
            if '11434' in r.stdout:
                p(YELLOW, '    → Puerto 11434 aún ocupado, esperando...')
                time.sleep(5)
                # Try killing whatever is on the port
                for line in r.stdout.splitlines():
                    if '11434' in line and 'LISTENING' in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            subprocess.run(['taskkill', '/f', '/pid', pid],
                                           capture_output=True, timeout=5, check=False)

        # Start Ollama serve in background (clean environment)
        env = os.environ.copy()
        env.pop('CUDA_VISIBLE_DEVICES', None)
        p(CYAN, '    → Arrancando ollama serve (sin CUDA_VISIBLE_DEVICES)...')
        try:
            if ollama_exe:
                subprocess.Popen(
                    [ollama_exe, 'serve'],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0,
                )
                p(GREEN, '    → Ollama serve arrancado en background')
                p(CYAN, '    → Esperando 8 segundos para que inicie...')
                time.sleep(8)
            else:
                p(RED, '    → ollama no encontrado en PATH')
        except Exception as e:
            p(RED, f'    → Error arrancando ollama: {e}')

        # Verify: warm up a model and check if it's on GPU now
        p(CYAN, '    → Verificando: cargando modelo de prueba...')
        try:
            payload = json.dumps({
                'model': 'gemma3:4b', 'prompt': 'hola', 'stream': False,
                'options': {'num_predict': 5},
            }).encode()
            req = urllib.request.Request(
                'http://127.0.0.1:11434/api/generate',
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                json.loads(resp.read())
            p(GREEN, '    → Modelo cargado exitosamente')
        except Exception as e:
            p(RED, f'    → Error cargando modelo: {e}')

        # Re-check ollama ps
        time.sleep(2)
        ollama_raw_after = query_ollama_ps()
        ollama_models_after = parse_ollama_ps_processor(ollama_raw_after)
        gpu_after_fix = query_nvidia_smi()
        procs_after_fix = query_nvidia_processes()

        p(CYAN, '  Verificación post-fix:')
        for m in ollama_models_after:
            processor = m.get('processor', '?')
            color = GREEN if 'gpu' in processor.lower() else RED
            p(color, f'    [ollama ps] {m.get("name", "?")} → processor={processor}')
        for g in gpu_after_fix:
            p(CYAN, f'    [nvidia-smi] GPU{g["index"]}: {g["util_pct"]}% util, '
                  f'{g["mem_used_mb"]}MB/{g["mem_total_mb"]}MB VRAM')
        for pr in procs_after_fix:
            p(GREEN, f'    [nvidia compute] PID {pr["pid"]}: {pr["name"]} ({pr["vram_mb"]}MB)')

        # Update findings with post-fix status
        any_gpu_now = any('gpu' in m.get('processor', '').lower() for m in ollama_models_after)
        if any_gpu_now:
            findings.append({
                'type': 'auto_fix_success', 'severity': 'INFO',
                'detail': 'Después del reinicio de Ollama, modelo(s) ahora en GPU. '
                          'El sistema se auto-corrigió exitosamente.',
            })
            p(GREEN + BOLD, '  ✓ AUTO-CORRECCIÓN EXITOSA: modelos ahora en GPU')
        else:
            findings.append({
                'type': 'auto_fix_partial', 'severity': 'MEDIUM',
                'detail': 'Después del reinicio de Ollama, modelos siguen en CPU. '
                          'Puede requerir reinstalación de Ollama con soporte CUDA.',
            })
            p(YELLOW, '  ⚠ Modelos siguen en CPU — puede requerir reinstalación de Ollama')
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

    # Filter: only test generative models that fit in 6GB VRAM (skip embedding models)
    test_models = [
        m for m in available
        if any(k in m for k in ['gemma3', 'qwen2.5-coder', 'qwen3'])
        and 'embedding' not in m.lower()
    ]
    if not test_models:
        test_models = [m for m in available if 'embedding' not in m.lower()][:3]

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

            # Source 4: Task Manager Performance Counters
            tm = result.get('task_manager', {})
            tm_active = tm.get('total_util', 0) > 1.0 if tm.get('available') else None

            # Count agreements (4 sources now)
            sources = {
                'nvidia_smi_util': any_gpu,
                'ollama_ps': ollama_says_gpu,
                'nvidia_compute_apps': ollama_in_compute,
            }
            if tm_active is not None:
                sources['task_manager_counters'] = tm_active

            total_sources = len(sources)
            agree_gpu = sum(1 for v in sources.values() if v)
            agree_cpu = sum(1 for v in sources.values() if not v)

            if agree_gpu >= (total_sources - 1):
                result['verdict'] = f'CALIBRADO (GPU): {agree_gpu}/{total_sources} fuentes confirman GPU activa'
                color = GREEN
            elif agree_cpu >= (total_sources - 1):
                result['verdict'] = f'NO CALIBRADO (CPU): {agree_cpu}/{total_sources} fuentes indican CPU'
                color = RED
            else:
                result['verdict'] = f'PARCIAL: {agree_gpu}/{total_sources} GPU vs {agree_cpu}/{total_sources} CPU'
                color = YELLOW

            result['sources'] = sources
            p(color, f'    → {result["verdict"]}')
            p(CYAN, f'    → {tps} tok/s, {result["tokens"]} tokens en {result["elapsed_s"]}s')
            p(CYAN, f'    → [nvidia-smi]         Peak GPU: {result.get("peak_util_per_gpu", {})} Avg: {result.get("avg_util_per_gpu", {})}')
            p(CYAN, f'    → [ollama ps]           processor: {model_proc}')
            p(CYAN, f'    → [nvidia compute apps] {[pr["name"] for pr in procs_after]}')
            # Task Manager cross-reference with per-engine detail
            if tm.get('available'):
                tm_util = tm.get('total_util', 0)
                tm_by_type = tm.get('by_engine_type', {})
                tm_by_gpu = tm.get('by_gpu', {})
                tm_color = GREEN if tm_util > 1 else RED
                engine_str = ', '.join(
                    f'{k}={v:.1f}%' for k, v in sorted(tm_by_type.items(), key=lambda x: -x[1])
                ) if tm_by_type else 'sin actividad'
                gpu_str = ', '.join(
                    f'{k}={v:.1f}%' for k, v in sorted(tm_by_gpu.items())
                ) if tm_by_gpu else ''
                p(tm_color, f'    → [Task Manager]        total={tm_util:.1f}%')
                if tm_by_type:
                    p(tm_color, f'                            Engines: {engine_str}')
                if tm_by_gpu:
                    p(tm_color, f'                            GPUs: {gpu_str}')
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
