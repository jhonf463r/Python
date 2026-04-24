#!/usr/bin/env python3
"""
IABV GPU Benchmark Real — Tests REAL para cada modelo en la RTX 4050.
Verifica GPU con nvidia-smi DURANTE la inferencia.
Ejecutar: python scripts/gpu_benchmark_real.py
"""
import json
import subprocess
import time
import threading
import httpx

OLLAMA = 'http://127.0.0.1:11434'
PROMPT_SIMPLE = 'Responde en una linea: cual es la capital de Colombia?'
PROMPT_COMPLEX = (
    'Eres un experto en Python. Escribe una funcion que calcule '
    'los numeros primos hasta N usando la Criba de Eratostenes. '
    'Incluye type hints y docstring.'
)
RESULTS: list[dict] = []


def gpu_snapshot() -> dict:
    """Captura estado GPU con nvidia-smi."""
    try:
        r = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            parts = [p.strip() for p in r.stdout.strip().split(',')]
            return {
                'name': parts[0],
                'vram_total_mb': int(parts[1]),
                'vram_used_mb': int(parts[2]),
                'vram_free_mb': int(parts[3]),
                'gpu_util_pct': int(parts[4]),
                'temp_c': int(parts[5]),
            }
    except Exception as e:
        return {'error': str(e)}
    return {'error': 'nvidia-smi failed'}


def gpu_monitor_during(duration: float) -> list[dict]:
    """Monitorea GPU cada 0.5s durante duration segundos."""
    snapshots = []
    stop = threading.Event()

    def _loop():
        while not stop.is_set():
            snapshots.append({**gpu_snapshot(), 'ts': time.time()})
            stop.wait(0.5)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    stop.wait(duration)
    stop.set()
    t.join(timeout=2)
    return snapshots


def unload_all():
    """Descarga todos los modelos de Ollama para tener baseline limpio."""
    try:
        with httpx.Client(timeout=10) as c:
            ps = c.get(f'{OLLAMA}/api/ps').json().get('models', [])
            for m in ps:
                name = m.get('name', '')
                if name:
                    c.post(f'{OLLAMA}/api/generate',
                           json={'model': name, 'keep_alive': 0},
                           timeout=10)
        time.sleep(2)
    except Exception:
        pass


def benchmark_model(model_name: str, prompt: str, label: str) -> dict:
    """Benchmark real: descarga modelos, carga uno, mide GPU durante inferencia."""
    print(f'\n{"="*60}')
    print(f'  TEST: {model_name} ({label})')
    print(f'{"="*60}')

    # 1. Descargar modelos previos
    print('  [1] Descargando modelos previos...')
    unload_all()

    # 2. GPU baseline (sin modelo)
    baseline = gpu_snapshot()
    print(f'  [2] GPU baseline: VRAM={baseline.get("vram_used_mb",0)} MB, Util={baseline.get("gpu_util_pct",0)}%')

    # 3. Ejecutar inferencia + monitorear GPU
    print(f'  [3] Ejecutando inferencia...')
    gpu_samples: list[dict] = []
    stop_monitor = threading.Event()

    def monitor():
        while not stop_monitor.is_set():
            gpu_samples.append({**gpu_snapshot(), 'ts': round(time.time(), 2)})
            stop_monitor.wait(0.3)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    error = None
    response_text = ''
    eval_count = 0
    eval_duration = 0
    total_duration = 0
    tps = 0.0
    elapsed = 0.0

    try:
        with httpx.Client(timeout=180) as c:
            start = time.time()
            r = c.post(f'{OLLAMA}/api/generate',
                       json={'model': model_name, 'prompt': prompt, 'stream': False},
                       timeout=180)
            elapsed = round(time.time() - start, 2)

            if r.status_code == 200:
                data = r.json()
                response_text = data.get('response', '')
                eval_count = data.get('eval_count', 0)
                eval_duration = data.get('eval_duration', 0)
                total_duration = data.get('total_duration', 0)
                load_duration = data.get('load_duration', 0)
                prompt_eval = data.get('prompt_eval_duration', 0)

                tps = round(eval_count / (eval_duration / 1e9), 1) if eval_duration else 0
            else:
                error = f'HTTP {r.status_code}: {r.text[:200]}'
    except Exception as e:
        error = str(e)[:200]
        elapsed = round(time.time() - start, 2)

    stop_monitor.set()
    monitor_thread.join(timeout=2)

    # 4. GPU durante inferencia
    if gpu_samples:
        max_vram = max(s.get('vram_used_mb', 0) for s in gpu_samples)
        max_util = max(s.get('gpu_util_pct', 0) for s in gpu_samples)
        avg_util = round(sum(s.get('gpu_util_pct', 0) for s in gpu_samples) / len(gpu_samples), 1)
        max_temp = max(s.get('temp_c', 0) for s in gpu_samples)
    else:
        max_vram = max_util = avg_util = max_temp = 0

    # 5. Verificar si modelo esta en GPU
    using_gpu = False
    vram_model = 0
    try:
        with httpx.Client(timeout=10) as c:
            ps = c.get(f'{OLLAMA}/api/ps').json().get('models', [])
            for m in ps:
                if m.get('name', '').startswith(model_name.split(':')[0]):
                    vram_model = round(m.get('size_vram', 0) / 1e9, 2)
                    using_gpu = m.get('size_vram', 0) > 0
    except Exception:
        pass

    # 6. GPU final
    final = gpu_snapshot()

    result = {
        'model': model_name,
        'label': label,
        'tokens_per_second': tps,
        'eval_count': eval_count,
        'eval_duration_ms': round(eval_duration / 1e6, 1) if eval_duration else 0,
        'total_time_seconds': elapsed,
        'load_time_ms': round(load_duration / 1e6, 1) if 'load_duration' in dir() and load_duration else 0,
        'response_preview': response_text[:200],
        'error': error,
        'gpu_baseline_vram_mb': baseline.get('vram_used_mb', 0),
        'gpu_max_vram_mb': max_vram,
        'gpu_vram_model_gb': vram_model,
        'gpu_max_util_pct': max_util,
        'gpu_avg_util_pct': avg_util,
        'gpu_max_temp_c': max_temp,
        'gpu_using_gpu': using_gpu,
        'gpu_samples_count': len(gpu_samples),
    }

    # Print results
    if error:
        print(f'  [ERROR] {error}')
    else:
        print(f'  [4] Resultado:')
        print(f'      Velocidad:     {tps} tok/s ({eval_count} tokens en {result["eval_duration_ms"]}ms)')
        print(f'      Tiempo total:  {elapsed}s')
        print(f'      GPU en uso:    {"SI" if using_gpu else "NO"} (VRAM modelo: {vram_model} GB)')
        print(f'      VRAM peak:     {max_vram} MB (baseline: {baseline.get("vram_used_mb",0)} MB)')
        print(f'      GPU util peak: {max_util}% (promedio: {avg_util}%)')
        print(f'      Temperatura:   {max_temp} C')
        print(f'      Respuesta:     {response_text[:100]}...')

    RESULTS.append(result)
    return result


def main():
    print('=' * 60)
    print('  IABV GPU BENCHMARK REAL')
    print('  RTX 4050 Laptop — Verificacion con nvidia-smi')
    print('=' * 60)

    # List models
    try:
        with httpx.Client(timeout=10) as c:
            tags = c.get(f'{OLLAMA}/api/tags').json().get('models', [])
            chat_models = []
            for m in tags:
                name = m.get('name', '')
                family = m.get('details', {}).get('family', '')
                size_gb = round(m.get('size', 0) / 1e9, 2)
                param = m.get('details', {}).get('parameter_size', '')
                # Skip embedding models
                if 'embedding' in name.lower() or 'embed' in name.lower():
                    print(f'  [skip] {name} (embedding model)')
                    continue
                chat_models.append((name, size_gb, param, family))
                print(f'  [chat] {name} ({size_gb} GB, {param}, {family})')
    except Exception as e:
        print(f'ERROR listing models: {e}')
        return

    # Sort by size ascending
    chat_models.sort(key=lambda x: x[1])

    # Benchmark each
    for name, size_gb, param, family in chat_models:
        benchmark_model(name, PROMPT_SIMPLE, f'simple ({size_gb}GB, {param})')

    # Also test best model with complex prompt
    if RESULTS:
        best = max([r for r in RESULTS if not r.get('error')], key=lambda r: r['tokens_per_second'], default=None)
        if best:
            benchmark_model(best['model'], PROMPT_COMPLEX, 'complejo (codigo)')

    # Final summary
    print('\n' + '=' * 60)
    print('  RESUMEN FINAL — BENCHMARK REAL GPU')
    print('=' * 60)
    valid = [r for r in RESULTS if not r.get('error')]
    valid.sort(key=lambda r: r['tokens_per_second'], reverse=True)

    print(f'\n{"#":>3} {"Modelo":25} {"tok/s":>8} {"GPU?":>5} {"VRAM":>8} {"Util%":>6} {"Temp":>5} {"Label":20}')
    print('-' * 85)
    for i, r in enumerate(valid, 1):
        gpu_flag = 'SI' if r['gpu_using_gpu'] else 'NO'
        print(f'{i:>3} {r["model"]:25} {r["tokens_per_second"]:>8.1f} {gpu_flag:>5} {r["gpu_vram_model_gb"]:>7.2f}G {r["gpu_max_util_pct"]:>5}% {r["gpu_max_temp_c"]:>4}C {r["label"]:20}')

    # Save results
    output_path = 'data/gpu_benchmark_real.json'
    import os
    os.makedirs('data', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)
    print(f'\nResultados guardados en: {output_path}')

    if valid:
        best = valid[0]
        print(f'\n*** MEJOR MODELO REAL: {best["model"]} — {best["tokens_per_second"]} tok/s, GPU: {"SI" if best["gpu_using_gpu"] else "NO"} ***')


if __name__ == '__main__':
    main()
