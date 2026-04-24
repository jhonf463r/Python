from __future__ import annotations

import os
from pathlib import Path

from iabv_v15.domain.models import AppConfig, TaskRole, ThemeConfig


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on', 'si'}


def _env_optional_flag(*names: str) -> bool | None:
    """Devuelve ``True``/``False`` si alguna env está seteada; ``None`` si ninguna.

    Usado por flags donde ``None`` significa "sin preferencia configurada, que
    el servicio decida por sí mismo" (p. ej. el ``SynapticRouter`` sigue usando
    su env propio como lectura en caliente cuando el override es ``None``).
    """
    for name in names:
        raw = os.getenv(name)
        if raw is None:
            continue
        return raw.strip().lower() in {'1', 'true', 'yes', 'on', 'si'}
    return None


def _auto_detect_best_ollama_model() -> str:
    """Detecta GPU y selecciona el mejor modelo Ollama automaticamente.

    Lee el ultimo benchmark guardado en data/gpu_benchmark_real.json.
    Si no existe, usa nvidia-smi para estimar VRAM y elegir el modelo
    mas grande que quepa. Fallback: gemma3:4b (rapido, bajo VRAM).
    """
    import subprocess

    default = 'gemma3:4b'

    # 1. Intentar leer benchmark previo
    try:
        bench_path = Path.cwd() / 'data' / 'gpu_benchmark_real.json'
        if bench_path.exists():
            import json as _json
            data = _json.loads(bench_path.read_text(encoding='utf-8'))
            bench = data if isinstance(data, list) else data.get('benchmark_results', [])
            valid = [b for b in bench if not b.get('error') and b.get('tokens_per_second', 0) > 0]
            if valid:
                best = max(valid, key=lambda b: b['tokens_per_second'])
                model = best['model']
                tps = best['tokens_per_second']
                print(f'[gpu-auto] Benchmark previo: mejor modelo = {model} ({tps} tok/s)')
                return model
    except Exception:
        pass

    # 2. Detectar VRAM via nvidia-smi
    try:
        nv = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5,
        )
        if nv.returncode == 0:
            parts = [p.strip() for p in nv.stdout.strip().split(',')]
            gpu_name = parts[0]
            vram_mb = int(parts[1])
            print(f'[gpu-auto] GPU detectada: {gpu_name} ({vram_mb} MB VRAM)')

            # Seleccion por VRAM disponible
            if vram_mb >= 10000:
                chosen = 'qwen3:8b'
            elif vram_mb >= 6000:
                chosen = 'gemma3:4b'
            elif vram_mb >= 4000:
                chosen = 'gemma3:4b'
            else:
                chosen = 'gemma3:4b'  # Modelo mas ligero
            print(f'[gpu-auto] Modelo seleccionado: {chosen} (VRAM: {vram_mb} MB)')
            return chosen
    except Exception:
        pass

    # 3. Sin GPU — usar default
    print(f'[gpu-auto] Sin GPU detectada, usando default: {default}')
    return default


def load_app_config(workspace_root: str | None = None) -> AppConfig:
    root = Path(workspace_root or Path.cwd()).resolve()
    data_dir = root / 'data'
    chrome_default = os.getenv(
        'IABV_CHROME_USER_DATA_DIR',
        str(Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data'),
    )
    default_role = os.getenv('IABV_DEFAULT_TASK_ROLE', TaskRole.TRAINING.value)
    return AppConfig(
        workspace_root=str(root),
        data_dir=str(data_dir),
        episodes_dir=str(data_dir / 'episodes'),
        screenshots_dir=str(data_dir / 'screenshots'),
        replay_annotations_dir=str(data_dir / 'replay_annotations'),
        tool_teaching_dir=str(data_dir / 'tool_teaching'),
        browser_profiles_dir=str(data_dir / 'browser_profiles'),
        browser_states_dir=str(data_dir / 'browser_states'),
        browser_artifacts_dir=str(data_dir / 'browser_artifacts'),
        site_policies_dir=str(data_dir / 'site_policies'),
        payloads_dir=str(data_dir / 'payloads'),
        models_dir=str(data_dir / 'models'),
        logs_dir=str(data_dir / 'logs'),
        evolution_dir=str(data_dir / 'evolution'),
        sqlite_path=str(data_dir / 'app.sqlite'),
        chrome_default_user_data_dir=chrome_default,
        lm_studio_base_url=os.getenv('IABV_LM_STUDIO_BASE_URL', 'http://127.0.0.1:1234/v1'),
        lm_studio_model=os.getenv('IABV_LM_STUDIO_MODEL', 'gemma3:4b'),
        ollama_base_url=os.getenv('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434/v1'),
        ollama_model=os.getenv('IABV_OLLAMA_MODEL') or _auto_detect_best_ollama_model(),
        ollama_embedding_model=os.getenv('IABV_OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b'),
        ollama_embedding_light_model=os.getenv('IABV_OLLAMA_EMBEDDING_LIGHT_MODEL', 'embeddinggemma'),
        provider_timeout_seconds=float(os.getenv('IABV_PROVIDER_TIMEOUT', '45')),
        default_task_role=TaskRole(default_role),
        autonomous_evolution_enabled=_env_flag('IABV_AUTONOMOUS_EVOLUTION', True),
        autonomous_external_launch=_env_flag('IABV_AUTONOMOUS_EXTERNAL_LAUNCH', True),
        synaptic_routing_enabled=_env_optional_flag(
            'IABV_SYNAPTIC_ROUTING_ENABLED',
            'SYNAPTIC_ROUTING',
        ),
    )


def load_theme_config() -> ThemeConfig:
    return ThemeConfig()

