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
        ollama_model=os.getenv('IABV_OLLAMA_MODEL', 'gemma3:4b'),  # Benchmark: 57.4 tok/s en RTX 4050 (vs qwen3:8b ~25 tok/s)
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

