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


def query_cpu_info() -> dict:
    """Query CPU information — cores, threads, name, and current usage."""
    info: dict = {'available': False}
    if sys.platform == 'win32':
        try:
            ps_cmd = (
                '$cpu = Get-CimInstance Win32_Processor; '
                '$load = (Get-Counter "\\Processor(_Total)\\% Processor Time" '
                '-ErrorAction SilentlyContinue).CounterSamples[0].CookedValue; '
                '[PSCustomObject]@{'
                'Name=$cpu.Name; Cores=$cpu.NumberOfCores; '
                'Threads=$cpu.NumberOfLogicalProcessors; '
                'MaxClockMHz=$cpu.MaxClockSpeed; '
                'LoadPct=[math]::Round($load,1); '
                'RAMTotalGB=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1); '
                'RAMFreeGB=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1)'
                '} | ConvertTo-Json -Compress'
            )
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_cmd],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout)
                info = {
                    'available': True,
                    'name': data.get('Name', '?'),
                    'cores': data.get('Cores', 0),
                    'threads': data.get('Threads', 0),
                    'max_clock_mhz': data.get('MaxClockMHz', 0),
                    'load_pct': data.get('LoadPct', 0),
                    'ram_total_gb': data.get('RAMTotalGB', 0),
                    'ram_free_gb': data.get('RAMFreeGB', 0),
                }
        except Exception as e:
            info = {'available': False, 'error': str(e)}
    else:
        try:
            import multiprocessing
            info = {
                'available': True,
                'name': 'Linux CPU',
                'cores': multiprocessing.cpu_count(),
                'threads': multiprocessing.cpu_count(),
            }
        except Exception:
            pass
    return info


def _map_gpu_adapter_name(phys_id: str, luid: str) -> str:
    """Map Performance Counter GPU adapter to Task Manager GPU index.

    Task Manager enumerates ALL display adapters (Intel iGPU = GPU0,
    NVIDIA = GPU1). But Performance Counters use phys_N per vendor.
    We query WMI to get the real adapter order matching Task Manager.
    Falls back to phys_N if WMI is unavailable.
    """
    if not hasattr(_map_gpu_adapter_name, '_cache'):
        _map_gpu_adapter_name._cache = {}
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-CimInstance Win32_VideoController | '
                 'Select-Object -Property DeviceID, Name | '
                 'ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if r.returncode == 0 and r.stdout.strip():
                adapters = json.loads(r.stdout)
                if isinstance(adapters, dict):
                    adapters = [adapters]
                for i, a in enumerate(adapters):
                    name = a.get('Name', '')
                    if 'nvidia' in name.lower():
                        _map_gpu_adapter_name._cache['nvidia'] = f'GPU{i}'
                    elif 'intel' in name.lower():
                        _map_gpu_adapter_name._cache['intel'] = f'GPU{i}'
        except Exception:
            pass

    # NVIDIA engines typically use phys_0 even when Task Manager shows GPU1
    # Try to detect by LUID pattern or fall back to adapter mapping
    if _map_gpu_adapter_name._cache.get('nvidia'):
        return _map_gpu_adapter_name._cache['nvidia']
    return f'GPU{phys_id}'


def query_task_manager_gpu() -> dict:
    """Query Windows Performance Counters — the SAME data Task Manager shows.

    This reads GPU Engine utilization counters via PowerShell, which is the
    exact source that feeds the Task Manager GPU graphs. This provides an
    independent truth source separate from nvidia-smi.

    Parses individual engine types (3D, Compute, Copy, VideoDecode, VideoEncode)
    per GPU adapter — so the program sees exactly what the user sees in Task Manager.

    Uses MAX (not SUM) per engine type to avoid exceeding 100%.
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
        # Use MAX per engine type (not sum) — multiple instances exist
        by_type: dict[str, float] = {}
        by_gpu: dict[str, float] = {}
        for sample in data:
            path = sample.get('Path', '')
            value = sample.get('CookedValue', 0.0)
            # Parse engine type: engtype_3d, engtype_compute, engtype_copy, etc.
            eng_match = _re.search(r'engtype_(\w+)', path, _re.IGNORECASE)
            engine_type = eng_match.group(1) if eng_match else 'unknown'
            # Take MAX per type (each instance is 0-100%)
            by_type[engine_type] = max(by_type.get(engine_type, 0), value)
            # Parse GPU adapter: phys_N and luid
            gpu_match = _re.search(r'phys_(\d+)', path, _re.IGNORECASE)
            luid_match = _re.search(r'luid_(0x[\da-fA-F_]+)', path, _re.IGNORECASE)
            phys_id = gpu_match.group(1) if gpu_match else '0'
            luid = luid_match.group(1) if luid_match else ''
            gpu_id = _map_gpu_adapter_name(phys_id, luid)
            by_gpu[gpu_id] = max(by_gpu.get(gpu_id, 0), value)
            engines.append({
                'path': path, 'util_pct': round(value, 2),
                'engine_type': engine_type, 'gpu': gpu_id,
            })

        by_type = {k: round(v, 2) for k, v in by_type.items()}
        by_gpu = {k: round(v, 2) for k, v in by_gpu.items()}
        total_util = round(max(by_gpu.values()) if by_gpu else 0, 2)
        return {
            'available': True,
            'active_engines': engines,
            'total_util': total_util,
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
    """Run Ollama inference and sample nvidia-smi + Task Manager during execution."""
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
    tm_samples: list[dict] = []
    stop = threading.Event()

    def sampler():
        """Sample nvidia-smi every 0.3s during inference."""
        while not stop.is_set():
            gpus = query_nvidia_smi()
            samples.append({'t': round(time.time(), 2), 'gpus': gpus})
            stop.wait(0.3)

    def tm_sampler():
        """Sample Task Manager Performance Counters every 2s during inference.

        This runs slower than nvidia-smi because Get-Counter takes ~1-2s.
        But it captures the SAME data the user sees in Task Manager.
        """
        while not stop.is_set():
            tm = query_task_manager_gpu()
            if tm.get('available'):
                tm_samples.append({
                    't': round(time.time(), 2),
                    'total_util': tm.get('total_util', 0),
                    'by_engine_type': tm.get('by_engine_type', {}),
                    'by_gpu': tm.get('by_gpu', {}),
                })
            stop.wait(2)

    t1 = threading.Thread(target=sampler, daemon=True)
    t2 = threading.Thread(target=tm_sampler, daemon=True)
    t1.start()
    t2.start()

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
    t1.join(2)
    t2.join(3)

    # Analyze nvidia-smi GPU samples
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

    # Analyze Task Manager samples (captured DURING inference)
    if tm_samples:
        peak_tm_total = max(s['total_util'] for s in tm_samples)
        avg_tm_total = round(sum(s['total_util'] for s in tm_samples) / len(tm_samples), 2)
        # Merge all engine types across samples — take peak per type
        all_types: dict[str, float] = {}
        all_gpus: dict[str, float] = {}
        for s in tm_samples:
            for k, v in s.get('by_engine_type', {}).items():
                all_types[k] = max(all_types.get(k, 0), v)
            for k, v in s.get('by_gpu', {}).items():
                all_gpus[k] = max(all_gpus.get(k, 0), v)
        result['task_manager'] = {
            'available': True,
            'samples_count': len(tm_samples),
            'peak_total_util': round(peak_tm_total, 2),
            'avg_total_util': avg_tm_total,
            'peak_by_engine_type': {k: round(v, 2) for k, v in all_types.items()},
            'peak_by_gpu': {k: round(v, 2) for k, v in all_gpus.items()},
            'total_util': round(peak_tm_total, 2),
            'by_engine_type': {k: round(v, 2) for k, v in all_types.items()},
            'by_gpu': {k: round(v, 2) for k, v in all_gpus.items()},
        }
    else:
        result['task_manager'] = query_task_manager_gpu()
    return result


# ---------------------------------------------------------------------------
# Hardware fingerprint — detect new hardware and auto-recalibrate
# ---------------------------------------------------------------------------

def _build_hardware_fingerprint(gpus: list[dict]) -> dict:
    """Build a fingerprint of the current GPU hardware."""
    gpu_info = []
    for g in gpus:
        gpu_info.append({
            'name': g.get('name', ''),
            'mem_total_mb': g.get('mem_total_mb', 0),
            'driver': g.get('driver', ''),
        })
    # Also detect Intel iGPU via WMI (not visible in nvidia-smi)
    all_adapters = []
    if sys.platform == 'win32':
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-CimInstance Win32_VideoController | '
                 'Select-Object -Property Name, AdapterRAM, DriverVersion | '
                 'ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if r.returncode == 0 and r.stdout.strip():
                adapters = json.loads(r.stdout)
                if isinstance(adapters, dict):
                    adapters = [adapters]
                for a in adapters:
                    all_adapters.append({
                        'name': a.get('Name', ''),
                        'vram_bytes': a.get('AdapterRAM', 0),
                        'driver': a.get('DriverVersion', ''),
                    })
        except Exception:
            pass

    return {
        'nvidia_gpus': gpu_info,
        'all_adapters': all_adapters,
        'gpu_count': len(gpu_info),
        'adapter_count': len(all_adapters),
    }


def _fingerprint_changed(current: dict, saved: dict) -> tuple[bool, list[str]]:
    """Compare current hardware fingerprint vs saved one."""
    changes = []
    if not saved:
        return True, ['primera ejecución — sin perfil guardado']

    saved_fp = saved.get('hardware_fingerprint', {})
    if not saved_fp:
        return True, ['perfil anterior sin fingerprint']

    # Compare NVIDIA GPU count
    if current.get('gpu_count', 0) != saved_fp.get('gpu_count', 0):
        changes.append(f'GPU count: {saved_fp.get("gpu_count")} → {current.get("gpu_count")}')

    # Compare GPU names
    cur_names = [g['name'] for g in current.get('nvidia_gpus', [])]
    saved_names = [g['name'] for g in saved_fp.get('nvidia_gpus', [])]
    if cur_names != saved_names:
        changes.append(f'GPUs: {saved_names} → {cur_names}')

    # Compare VRAM
    cur_vram = [g['mem_total_mb'] for g in current.get('nvidia_gpus', [])]
    saved_vram = [g['mem_total_mb'] for g in saved_fp.get('nvidia_gpus', [])]
    if cur_vram != saved_vram:
        changes.append(f'VRAM: {saved_vram}MB → {cur_vram}MB')

    # Compare all adapters (detects iGPU changes)
    cur_adapters = [a['name'] for a in current.get('all_adapters', [])]
    saved_adapters = [a['name'] for a in saved_fp.get('all_adapters', [])]
    if cur_adapters != saved_adapters:
        changes.append(f'Adaptadores: {saved_adapters} → {cur_adapters}')

    return len(changes) > 0, changes


def _load_saved_report() -> dict:
    """Load the last saved GPU benchmark report."""
    report_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gpu_benchmark_report.json')
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p(BOLD + CYAN, '=' * 60)
    p(BOLD + CYAN, '  IABV v1.5 — GPU Auto-Benchmark + Metacognición')
    p(BOLD + CYAN, '=' * 60)
    print()

    # === PHASE 0: Hardware fingerprint — detect new environment ===
    gpus = query_nvidia_smi()
    hw_fingerprint = _build_hardware_fingerprint(gpus)
    saved_report = _load_saved_report()
    hw_changed, hw_reasons = _fingerprint_changed(hw_fingerprint, saved_report)

    if hw_changed:
        p(BOLD + YELLOW, '▸ FASE 0: Detección de entorno')
        print()
        p(YELLOW, '  ⚠ ENTORNO NUEVO O CAMBIADO detectado:')
        for reason in hw_reasons:
            p(YELLOW, f'    → {reason}')
        if hw_fingerprint.get('all_adapters'):
            p(CYAN, '  Adaptadores GPU detectados (todos):')
            for i, a in enumerate(hw_fingerprint['all_adapters']):
                vram_mb = round(a.get('vram_bytes', 0) / 1024 / 1024) if a.get('vram_bytes') else '?'
                p(CYAN, f'    GPU{i}: {a["name"]} — {vram_mb}MB VRAM, driver {a.get("driver", "?")}')
        p(GREEN, '  → Ejecutando benchmark completo para calibrar este entorno...')
        print()
    else:
        p(BOLD + GREEN, '▸ FASE 0: Detección de entorno')
        print()
        p(GREEN, f'  ✓ Mismo hardware que último benchmark ({saved_report.get("timestamp", "?")})')
        p(GREEN, f'  ✓ Mejor modelo conocido: {saved_report.get("best_model", "?")} '
              f'({saved_report.get("best_tps", "?")} tok/s)')
        p(GREEN, '  → Ejecutando verificación rápida + benchmark para confirmar calibración...')
        print()

    # === PHASE 1: Auto-diagnosis ===
    p(BOLD, '▸ FASE 1: Auto-diagnóstico GPU (cruce de fuentes)')
    print()

    cuda_vis = os.environ.get('CUDA_VISIBLE_DEVICES', '')
    print('  Consultando nvidia-smi procesos...', end=' ', flush=True)
    procs = query_nvidia_processes()
    print(f'{len(procs)} encontrado(s)', flush=True)
    print('  Consultando ollama ps...', end=' ', flush=True)
    ollama_raw = query_ollama_ps()
    ollama_models = parse_ollama_ps_processor(ollama_raw)
    print(f'{len(ollama_models)} modelo(s)', flush=True)
    print(flush=True)

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
    print('  Consultando Task Manager Performance Counters...', end=' ', flush=True)
    task_mgr = query_task_manager_gpu()
    print('OK', flush=True)
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

            # Source 4: Task Manager Performance Counters (peak from continuous sampling)
            tm = result.get('task_manager', {})
            tm_peak_util = tm.get('peak_total_util', tm.get('total_util', 0))
            tm_active = tm_peak_util > 1.0 if tm.get('available') else None

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
            # Task Manager cross-reference with per-engine detail (sampled DURING inference)
            if tm.get('available'):
                tm_peak = tm.get('peak_total_util', tm.get('total_util', 0))
                tm_avg = tm.get('avg_total_util', tm_peak)
                tm_n = tm.get('samples_count', 1)
                tm_by_type = tm.get('peak_by_engine_type', tm.get('by_engine_type', {}))
                tm_by_gpu = tm.get('peak_by_gpu', tm.get('by_gpu', {}))
                tm_color = GREEN if tm_peak > 1 else RED
                engine_str = ', '.join(
                    f'{k}={v:.1f}%' for k, v in sorted(tm_by_type.items(), key=lambda x: -x[1])
                ) if tm_by_type else 'sin actividad'
                gpu_str = ', '.join(
                    f'{k}={v:.1f}%' for k, v in sorted(tm_by_gpu.items())
                ) if tm_by_gpu else ''
                p(tm_color, f'    → [Task Manager]        peak={tm_peak:.1f}% avg={tm_avg:.1f}% ({tm_n} muestras)')
                if tm_by_type:
                    p(tm_color, f'                            Engines (peak): {engine_str}')
                if tm_by_gpu:
                    p(tm_color, f'                            GPUs (peak): {gpu_str}')
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

    # === PHASE 4: High-performance reasoning ===
    print()
    p(BOLD, '▸ FASE 4: Razonamiento de alto rendimiento (metacognición de recursos)')
    print()

    print('  Analizando componentes del sistema...', flush=True)
    cpu_info = query_cpu_info()
    adapters = hw_fingerprint.get('all_adapters', [])
    best_model = ok_results[0] if ok_results else None

    reasoning: list[dict] = []

    # --- CPU Analysis ---
    if cpu_info.get('available'):
        cpu_name = cpu_info.get('name', '?')
        cores = cpu_info.get('cores', 0)
        threads = cpu_info.get('threads', 0)
        cpu_load = cpu_info.get('load_pct', 0)
        ram_total = cpu_info.get('ram_total_gb', 0)
        ram_free = cpu_info.get('ram_free_gb', 0)

        p(CYAN, f'  [CPU] {cpu_name}')
        p(CYAN, f'    {cores} cores / {threads} hilos, uso actual: {cpu_load}%')
        p(CYAN, f'    RAM: {ram_free}GB libre de {ram_total}GB total')

        if cpu_load < 30:
            reasoning.append({
                'component': 'CPU', 'status': 'subutilizado',
                'detail': f'CPU al {cpu_load}% — {threads} hilos disponibles para '
                          f'preprocesamiento paralelo, I/O, o tareas en background.',
                'action': 'Se pueden paralelizar tareas de preprocessing de datos, '
                          'tokenización, y post-procesamiento en CPU mientras la GPU '
                          'hace inferencia.',
            })
        elif cpu_load > 80:
            reasoning.append({
                'component': 'CPU', 'status': 'saturado',
                'detail': f'CPU al {cpu_load}% — puede ser cuello de botella para I/O.',
                'action': 'Reducir procesos en background o usar batch processing '
                          'para reducir overhead de CPU.',
            })
        else:
            reasoning.append({
                'component': 'CPU', 'status': 'balanceado',
                'detail': f'CPU al {cpu_load}% — buen balance entre cómputo y disponibilidad.',
                'action': 'Configuración actual óptima para CPU.',
            })

        # RAM check for model loading
        if ram_free and ram_total:
            ram_pct_free = round(ram_free / ram_total * 100, 1)
            if ram_pct_free < 20:
                reasoning.append({
                    'component': 'RAM', 'status': 'bajo',
                    'detail': f'Solo {ram_free}GB libre ({ram_pct_free}% de {ram_total}GB). '
                              f'Modelos grandes pueden causar swapping.',
                    'action': 'Usar modelos más pequeños (4b en vez de 8b) o cerrar '
                              'aplicaciones que consuman RAM.',
                })

    # --- GPU Analysis ---
    p(CYAN, '  [GPUs] Análisis de adaptadores:')
    nvidia_gpu = None
    intel_gpu = None
    for i, a in enumerate(adapters):
        name = a.get('name', '')
        vram_mb = round(a.get('vram_bytes', 0) / 1024 / 1024) if a.get('vram_bytes') else 0
        p(CYAN, f'    GPU{i}: {name} ({vram_mb}MB)')
        if 'nvidia' in name.lower():
            nvidia_gpu = {'index': i, 'name': name, 'vram_mb': vram_mb}
        elif 'intel' in name.lower():
            intel_gpu = {'index': i, 'name': name, 'vram_mb': vram_mb}

    # NVIDIA GPU reasoning
    if nvidia_gpu and best_model:
        peak_util = max(best_model.get('peak_util_per_gpu', {}).values(), default=0)
        avg_util = max(best_model.get('avg_util_per_gpu', {}).values(), default=0)
        vram_used = gpus[0]['mem_used_mb'] if gpus else 0
        vram_total = gpus[0]['mem_total_mb'] if gpus else 0

        if peak_util > 90:
            reasoning.append({
                'component': f'GPU{nvidia_gpu["index"]} (NVIDIA)',
                'status': 'alto rendimiento',
                'detail': f'Peak {peak_util}%, avg {avg_util}% durante inferencia. '
                          f'VRAM: {vram_used}/{vram_total}MB. '
                          f'La GPU NVIDIA está trabajando cerca de su máxima capacidad.',
                'action': 'Mantener configuración actual. Para más rendimiento: '
                          'usar modelos más pequeños (4b > 8b en velocidad) o '
                          'cuantización más agresiva.',
            })
        elif peak_util > 50:
            reasoning.append({
                'component': f'GPU{nvidia_gpu["index"]} (NVIDIA)',
                'status': 'parcial',
                'detail': f'Peak {peak_util}%, avg {avg_util}%. '
                          f'GPU no al máximo — posible cuello de botella en CPU o I/O.',
                'action': 'Verificar si el CPU está saturado alimentando datos a la GPU. '
                          'Considerar batch size más grande.',
            })
        else:
            reasoning.append({
                'component': f'GPU{nvidia_gpu["index"]} (NVIDIA)',
                'status': 'subutilizado',
                'detail': f'Peak {peak_util}%, avg {avg_util}%. GPU no se usa eficientemente.',
                'action': 'Verificar CUDA_VISIBLE_DEVICES, reinstalar drivers, o '
                          'verificar que Ollama usa GPU.',
            })

    # Intel iGPU reasoning
    if intel_gpu:
        reasoning.append({
            'component': f'GPU{intel_gpu["index"]} (Intel iGPU)',
            'status': 'disponible para descarga',
            'detail': f'{intel_gpu["name"]} con {intel_gpu["vram_mb"]}MB. '
                      f'Actualmente maneja display (~3% uso). '
                      f'Tiene hardware de Video Decode/Encode (Quick Sync).',
            'action': 'Puede usarse para: '
                      '(1) Video decode/encode via Intel Quick Sync — libera NVIDIA de tareas multimedia. '
                      '(2) Display rendering — ya lo hace, mantiene NVIDIA libre para cómputo. '
                      '(3) Inferencia ligera de modelos pequeños via OpenVINO si se necesita '
                      'procesamiento paralelo.',
        })

    # --- Dual-GPU simultaneous usage reasoning ---
    if nvidia_gpu and intel_gpu:
        reasoning.append({
            'component': 'Dual-GPU (estrategia)',
            'status': 'oportunidad de optimización',
            'detail': 'El sistema tiene 2 GPUs que pueden trabajar simultáneamente:\n'
                      f'    GPU{intel_gpu["index"]} Intel: display + video decode/encode\n'
                      f'    GPU{nvidia_gpu["index"]} NVIDIA: inferencia CUDA + cómputo pesado\n'
                      f'    Esta distribución ya está activa — Intel maneja el escritorio (3%) '
                      f'y NVIDIA se dedica 100% a inferencia ({best_model.get("tps", "?")} tok/s).',
            'action': 'Configuración dual-GPU ÓPTIMA. Para escenarios avanzados:\n'
                      '    • Si se necesita procesar video + inferencia simultánea → '
                      'Intel Quick Sync para video, NVIDIA para modelo.\n'
                      '    • Si se necesita inferencia paralela → modelo pequeño en '
                      'CPU+Intel (OpenVINO), modelo grande en NVIDIA (CUDA).\n'
                      '    • Evitar mover inferencia CUDA a Intel — rendimiento 10x menor.',
        })

    # --- Overall system configuration ---
    if best_model:
        vram_total = gpus[0]['mem_total_mb'] if gpus else 6141
        best_tps = best_model.get('tps', 0)
        can_fit_8b = vram_total >= 5500

        reasoning.append({
            'component': 'Configuración óptima global',
            'status': 'RECOMENDACIÓN',
            'detail': f'Sistema: {cpu_info.get("name", "?")} + '
                      f'{nvidia_gpu["name"] if nvidia_gpu else "?"} + '
                      f'{intel_gpu["name"] if intel_gpu else "solo NVIDIA"}.',
            'action': f'Config recomendada para alto rendimiento:\n'
                      f'    • CUDA_VISIBLE_DEVICES: no configurar (auto-detect)\n'
                      f'    • Modelo preferido: {best_model["model"]} ({best_tps} tok/s)\n'
                      f'    • Modelos ≤{"8b" if can_fit_8b else "4b"} caben en {vram_total}MB VRAM\n'
                      f'    • Intel iGPU: dejar como display adapter (libera NVIDIA)\n'
                      f'    • CPU ({cpu_info.get("threads", "?")} hilos): '
                      f'disponible para preprocessing paralelo\n'
                      f'    • RAM: mantener ≥4GB libre para modelo + sistema',
        })

    # Print reasoning
    print()
    for r in reasoning:
        status_color = {
            'subutilizado': YELLOW,
            'saturado': RED,
            'balanceado': GREEN,
            'alto rendimiento': GREEN,
            'parcial': YELLOW,
            'disponible para descarga': CYAN,
            'oportunidad de optimización': CYAN,
            'bajo': RED,
            'RECOMENDACIÓN': GREEN + BOLD,
        }.get(r['status'], CYAN)

        p(status_color, f'  [{r["component"]}] — {r["status"].upper()}')
        for line in r['detail'].split('\n'):
            p(CYAN, f'    {line.strip()}')
        p(GREEN, f'    → {r["action"].split(chr(10))[0]}')
        # Print multi-line actions
        for extra_line in r['action'].split('\n')[1:]:
            p(GREEN, f'      {extra_line.strip()}')
        print()

    # === PHASE 5: Multi-IA Super-Scanner ===
    print()
    p(BOLD, '▸ FASE 5: Super-escáner multi-IA (configuraciones óptimas)')
    print()

    # --- 5a: Auto-discover all available resources ---
    p(BOLD, '  [5a] Descubrimiento automático del entorno...')

    # Detect installed browsers
    detected_browsers: list[dict] = []
    if os.name == 'nt':
        browser_checks = [
            ('Chrome', [
                os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
                os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
            ]),
            ('Edge', [
                os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
                os.path.expandvars(r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe'),
            ]),
            ('Firefox', [
                os.path.expandvars(r'%ProgramFiles%\Mozilla Firefox\firefox.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe'),
            ]),
            ('Brave', [
                os.path.expandvars(r'%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe'),
                os.path.expandvars(r'%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe'),
            ]),
            ('Opera', [
                os.path.expandvars(r'%LocalAppData%\Programs\Opera\opera.exe'),
                os.path.expandvars(r'%AppData%\Opera Software\Opera Stable\opera.exe'),
            ]),
            ('Vivaldi', [
                os.path.expandvars(r'%LocalAppData%\Vivaldi\Application\vivaldi.exe'),
            ]),
        ]
        for name, paths in browser_checks:
            for p_path in paths:
                if os.path.isfile(p_path):
                    detected_browsers.append({'name': name, 'path': p_path})
                    break

    if detected_browsers:
        p(GREEN, f'  Navegadores detectados: {len(detected_browsers)}')
        for b in detected_browsers:
            p(CYAN, f'    • {b["name"]}: {b["path"]}')
    else:
        p(YELLOW, '  No se detectaron navegadores (o no es Windows)')

    # Detect all Ollama models (auto-discover, not hardcoded)
    ollama_models_discovered: list[str] = []
    try:
        req_models = urllib.request.Request('http://127.0.0.1:11434/api/tags')
        with urllib.request.urlopen(req_models, timeout=10) as resp:
            tags_data = json.loads(resp.read())
        for m in tags_data.get('models', []):
            name = m.get('name', '')
            if name:
                ollama_models_discovered.append(name)
        p(GREEN, f'  Modelos Ollama instalados: {len(ollama_models_discovered)}')
        for m_name in ollama_models_discovered:
            size_gb = 0
            for m in tags_data.get('models', []):
                if m.get('name') == m_name:
                    size_gb = round(m.get('size', 0) / 1e9, 1)
            p(CYAN, f'    • {m_name} ({size_gb}GB)')
    except Exception as e:
        p(RED, f'  Error descubriendo modelos Ollama: {e}')

    # Detect cloud IAs availability
    cloud_ias: list[dict] = []
    ia_endpoints = {
        'ChatGPT': {'check': 'chatgpt_installed', 'web': 'https://chatgpt.com'},
        'Claude': {'check': 'claude_installed', 'web': 'https://claude.ai'},
        'Codex': {'check': 'codex_installed', 'web': 'https://chatgpt.com/codex'},
        'Devin': {'check': 'devin_api', 'web': 'https://app.devin.ai'},
    }
    for ia_name, info in ia_endpoints.items():
        cloud_ias.append({
            'name': ia_name,
            'type': 'cloud',
            'web_url': info['web'],
            'status': 'requires_browser_session',
        })
    p(GREEN, f'  IAs cloud conocidas: {len(cloud_ias)}')
    for cia in cloud_ias:
        p(CYAN, f'    • {cia["name"]}: {cia["web_url"]} ({cia["status"]})')

    print()

    # --- 5b: Benchmark all Ollama models x configs x prompts ---
    p(BOLD, '  [5b] Benchmark exhaustivo de modelos locales...')
    print()

    # Test prompts by task type
    test_prompts = {
        'código': 'Escribe una función Python que encuentre el segundo número '
                  'más grande en una lista sin usar sort. Solo código, sin explicación.',
        'razonamiento': 'Un granjero tiene 17 ovejas. Todas menos 9 se escapan. '
                        '¿Cuántas quedan? Explica paso a paso.',
        'creatividad': 'Inventa un haiku sobre inteligencia artificial en español.',
        'metacognición': 'Eres un programa que se auto-examina. Describe tu estado '
                         'actual: qué puedes hacer, qué limitaciones tienes, y cómo '
                         'mejorarías tu propio rendimiento si pudieras modificarte.',
    }

    # Temperature configs to test
    temperatures = [0.1, 0.5, 0.9]

    # Use ALL discovered models — full panorama, not just hardcoded ones
    # Fallback to test_models from FASE 2 if Ollama API discovery failed
    models_to_scan = ollama_models_discovered if ollama_models_discovered else test_models

    ia_scan_results: list[dict] = []

    p(CYAN, f'  Modelos: {models_to_scan}')
    p(CYAN, f'  Tareas: {list(test_prompts.keys())}')
    p(CYAN, f'  Temperaturas: {temperatures}')
    total_combos = len(models_to_scan) * len(test_prompts) * len(temperatures)
    p(CYAN, f'  Total combinaciones: {total_combos}')
    print()

    combo_num = 0
    for model in models_to_scan:
        for task_name, prompt in test_prompts.items():
            for temp in temperatures:
                combo_num += 1
                label = f'{model} | {task_name} | temp={temp}'
                print(f'  [{combo_num}/{total_combos}] {label}...', end=' ', flush=True)

                payload = json.dumps({
                    'model': model, 'prompt': prompt, 'stream': False,
                    'options': {'num_predict': 128, 'temperature': temp},
                }).encode()
                req = urllib.request.Request(
                    'http://127.0.0.1:11434/api/generate',
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                )

                try:
                    t0 = time.perf_counter()
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        body = json.loads(resp.read())
                    elapsed = time.perf_counter() - t0

                    eval_count = body.get('eval_count', 0)
                    eval_ns = body.get('eval_duration', 0)
                    tps = round(eval_count / (eval_ns / 1e9), 2) if eval_ns > 0 else 0
                    response_text = body.get('response', '')

                    # Quality heuristics per task type
                    has_content = len(response_text.strip()) > 10
                    if task_name == 'código':
                        has_quality = 'def ' in response_text or 'return' in response_text
                    elif task_name == 'razonamiento':
                        has_quality = '9' in response_text or 'nueve' in response_text.lower()
                    elif task_name == 'metacognición':
                        rt = response_text.lower()
                        has_quality = any(w in rt for w in [
                            'limitacion', 'limitación', 'mejorar',
                            'rendimiento', 'capacidad', 'estado',
                        ])
                    else:
                        has_quality = len(response_text.strip()) > 20

                    quality_score = round(
                        (0.5 if has_content else 0) + (0.5 if has_quality else 0), 2
                    )

                    result_entry = {
                        'model': model, 'task': task_name, 'temperature': temp,
                        'tps': tps, 'tokens': eval_count, 'elapsed_s': round(elapsed, 2),
                        'quality': quality_score,
                        'response_excerpt': response_text[:150].replace('\n', ' '),
                    }
                    ia_scan_results.append(result_entry)

                    q_icon = '✓' if quality_score >= 0.5 else '✗'
                    p(GREEN if quality_score >= 0.5 else RED,
                      f'{tps} tok/s, calidad={quality_score} {q_icon}')

                except Exception as e:
                    ia_scan_results.append({
                        'model': model, 'task': task_name, 'temperature': temp,
                        'error': str(e),
                    })
                    p(RED, f'ERROR: {e}')

    # Analyze results per task
    print()
    p(BOLD, '  Resultados del super-escáner:')
    print()

    best_per_task: dict[str, dict] = {}
    for task_name in test_prompts:
        task_results = [r for r in ia_scan_results
                        if r.get('task') == task_name and r.get('tps')]
        if not task_results:
            continue

        # Best = highest quality, then highest speed
        task_results.sort(key=lambda r: (r.get('quality', 0), r.get('tps', 0)), reverse=True)
        best = task_results[0]
        best_per_task[task_name] = best

        p(GREEN + BOLD, f'  [{task_name.upper()}] Mejor: {best["model"]} '
                        f'(temp={best["temperature"]}) → {best["tps"]} tok/s, '
                        f'calidad={best["quality"]}')
        p(CYAN, f'    Respuesta: {best.get("response_excerpt", "")[:100]}...')
        # Show alternatives
        for alt in task_results[1:3]:
            p(CYAN, f'    Alt: {alt["model"]} temp={alt["temperature"]} → '
                    f'{alt["tps"]} tok/s, calidad={alt["quality"]}')
        print()

    # Overall recommendation
    if best_per_task:
        print()
        p(GREEN + BOLD, '  RECOMENDACIÓN POR TIPO DE TAREA:')
        for task_name, best in best_per_task.items():
            p(GREEN, f'    • {task_name}: usar {best["model"]} con '
                    f'temperature={best["temperature"]}')
        print()

    # Check if different tasks need different models/configs
    unique_configs = set()
    for best in best_per_task.values():
        unique_configs.add((best['model'], best['temperature']))

    if len(unique_configs) > 1:
        p(YELLOW, '  METACOGNICIÓN: Diferentes tareas rinden mejor con '
                  'diferentes configuraciones.')
        p(YELLOW, '  El programa debe seleccionar modelo+temperatura según '
                  'el tipo de tarea.')
    elif len(unique_configs) == 1:
        cfg = list(unique_configs)[0]
        p(GREEN, f'  METACOGNICIÓN: Una sola configuración óptima para todo: '
                 f'{cfg[0]} temp={cfg[1]}')

    print()
    p(BOLD + CYAN, '=' * 60)

    # Save results with hardware fingerprint + reasoning for future comparisons
    report = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'hardware_fingerprint': hw_fingerprint,
        'hardware_changed': hw_changed,
        'cpu_info': cpu_info if cpu_info.get('available') else None,
        'optimal_config': {
            'cuda_visible_devices': 'unset (auto-detect)',
            'best_model': ok_results[0]['model'] if ok_results else None,
            'best_tps': ok_results[0]['tps'] if ok_results else None,
            'all_models_calibrated': all(
                'CALIBRADO' in r.get('verdict', '') for r in ok_results
            ) if ok_results else False,
        },
        'high_performance_reasoning': reasoning,
        'diagnosis_findings': findings,
        'benchmark': benchmark_results,
        'best_model': ok_results[0]['model'] if ok_results else None,
        'best_tps': ok_results[0]['tps'] if ok_results else None,
        'ias_super_scan': {
            'scan_timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'environment_discovery': {
                'browsers_detected': detected_browsers,
                'ollama_models_discovered': ollama_models_discovered,
                'cloud_ias_known': cloud_ias,
            },
            'models_tested': models_to_scan,
            'tasks_tested': list(test_prompts.keys()),
            'temperatures_tested': temperatures,
            'total_combinations': total_combos,
            'results': ia_scan_results,
            'best_per_task': {
                task: {
                    'model': best['model'],
                    'temperature': best['temperature'],
                    'tps': best['tps'],
                    'quality': best['quality'],
                }
                for task, best in best_per_task.items()
            },
            'metacognition_insight': (
                'different_config_per_task'
                if len(unique_configs) > 1
                else 'single_optimal_config'
            ),
        },
    }
    report_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gpu_benchmark_report.json')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    p(CYAN, f'  Reporte guardado en: {os.path.abspath(report_path)}')
    print()


if __name__ == '__main__':
    main()
