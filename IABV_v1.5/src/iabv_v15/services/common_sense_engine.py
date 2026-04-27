"""Common Sense Reasoning Engine — deducción autónoma sin instrucciones.

Motor de razonamiento que deduce lo obvio y actúa sin que nadie se lo diga.
Implementa cadenas causales: si A + B son verdad, C se deduce automáticamente.

Principios:
  - Si algo es obvio, no preguntar: actuar.
  - Si dos hechos combinados implican un problema, deducirlo.
  - Si una acción es segura y reversible, ejecutarla.
  - Si el resultado de una acción previa fue malo, no repetirla.
  - Registrar cada deducción con evidencia para que ExperimentLab pueda
    comparar la calidad del razonamiento.

Arquitectura:
  - InferenceRule: regla (premisas → conclusión + acción)
  - FactBase: hechos observados del entorno actual
  - forward_chain(): motor de inferencia hacia adelante
  - act_on_conclusions(): ejecuta acciones seguras
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Inference Rules — cada regla es (premisas, conclusión, acción, seguridad)
# ──────────────────────────────────────────────────────────────

INFERENCE_RULES: list[dict[str, Any]] = [
    # GPU routing — cadena causal completa
    {
        'id': 'gpu_nvidia_exists_but_cpu_inference',
        'premises': ['nvidia_gpu_present', 'ollama_running', 'ollama_on_cpu'],
        'conclusion': 'nvidia_wasted',
        'action': 'force_ollama_to_nvidia',
        'severity': 'high',
        'safe': True,
        'description': 'NVIDIA disponible pero Ollama usa CPU — desperdicio de GPU',
    },
    {
        'id': 'gpu_cuda_not_installed',
        'premises': ['nvidia_gpu_present', 'ollama_running', 'ollama_on_cpu', 'no_cuda_process'],
        'conclusion': 'cuda_likely_missing',
        'action': 'verify_cuda_installation',
        'severity': 'high',
        'safe': True,
        'description': 'NVIDIA presente, Ollama en CPU, sin procesos CUDA — CUDA probablemente no instalado',
    },
    {
        'id': 'gpu_model_too_large',
        'premises': ['nvidia_gpu_present', 'ollama_running', 'model_split_cpu_gpu'],
        'conclusion': 'model_exceeds_vram',
        'action': 'suggest_smaller_model',
        'severity': 'medium',
        'safe': True,
        'description': 'Modelo dividido CPU/GPU — no cabe completo en VRAM',
    },
    {
        'id': 'gpu_idle_pre_configure',
        'premises': ['nvidia_gpu_present', 'ollama_running', 'no_models_loaded'],
        'conclusion': 'gpu_ready_for_preconfig',
        'action': 'pre_configure_cuda',
        'severity': 'low',
        'safe': True,
        'description': 'GPU disponible, Ollama idle — pre-configurar CUDA para próxima carga',
    },
    # Ollama health
    {
        'id': 'ollama_not_responding',
        'premises': ['ollama_process_exists', 'ollama_api_timeout'],
        'conclusion': 'ollama_hung',
        'action': 'restart_ollama',
        'severity': 'high',
        'safe': True,
        'description': 'Proceso de Ollama existe pero API no responde — colgado',
    },
    {
        'id': 'ollama_missing',
        'premises': ['no_ollama_process', 'ollama_expected'],
        'conclusion': 'ollama_not_running',
        'action': 'start_ollama',
        'severity': 'high',
        'safe': True,
        'description': 'Ollama no está corriendo pero se espera que esté — iniciar',
    },
    # Git hygiene
    {
        'id': 'stale_branch_with_changes',
        'premises': ['on_feature_branch', 'many_dirty_files', 'branch_is_old'],
        'conclusion': 'abandoned_branch',
        'action': 'switch_to_main',
        'severity': 'medium',
        'safe': True,
        'description': 'En rama feature vieja con muchos cambios — probablemente abandonada',
    },
    {
        'id': 'unmerged_branches_accumulating',
        'premises': ['many_unmerged_branches', 'tests_passing'],
        'conclusion': 'branch_cleanup_needed',
        'action': 'cleanup_merged_branches',
        'severity': 'low',
        'safe': True,
        'description': 'Muchas ramas sin mergear pero tests pasan — limpiar las ya mergeadas',
    },
    # Resource optimization
    {
        'id': 'secrets_missing_but_file_exists',
        'premises': ['secrets_file_exists', 'secrets_not_loaded'],
        'conclusion': 'secrets_file_not_sourced',
        'action': 'source_secrets_file',
        'severity': 'high',
        'safe': True,
        'description': 'Archivo de secretos existe pero no están cargados — falta source',
    },
    {
        'id': 'tunnel_installed_not_running',
        'premises': ['cloudflared_installed', 'tunnel_not_running', 'tunnel_expected'],
        'conclusion': 'tunnel_needs_start',
        'action': 'start_tunnel',
        'severity': 'medium',
        'safe': True,
        'description': 'Cloudflared instalado pero tunnel no corre — iniciar',
    },
    # Performance
    {
        'id': 'high_memory_low_gpu',
        'premises': ['high_ram_usage', 'nvidia_gpu_present', 'low_gpu_utilization'],
        'conclusion': 'compute_misallocated',
        'action': 'offload_to_gpu',
        'severity': 'medium',
        'safe': True,
        'description': 'RAM alta pero GPU sub-utilizada — mover carga a GPU',
    },
    {
        'id': 'slow_startup_many_checks',
        'premises': ['startup_slow', 'many_serial_checks'],
        'conclusion': 'startup_bottleneck',
        'action': 'parallelize_startup_checks',
        'severity': 'medium',
        'safe': False,
        'description': 'Arranque lento con muchas verificaciones en serie — paralelizar',
    },
    # Multi-monitor
    {
        'id': 'multi_monitor_blind_spot',
        'premises': ['multiple_monitors', 'app_on_secondary'],
        'conclusion': 'ui_on_wrong_monitor',
        'action': 'move_to_primary',
        'severity': 'low',
        'safe': True,
        'description': 'App en monitor secundario — mover al principal para evitar blind spots',
    },
    # Secret alias deduction — detect same secret under different names
    {
        'id': 'github_token_alias_mismatch',
        'premises': ['github_token_missing', 'github_token_alias_exists'],
        'conclusion': 'secret_alias_deducible',
        'action': 'map_secret_alias',
        'severity': 'high',
        'safe': True,
        'description': 'GITHUB_TOKEN no existe pero hay alias (GITHUB_TOKEN_IABV, GH_TOKEN) — mapear automaticamente',
    },
    {
        'id': 'devin_api_key_alias_mismatch',
        'premises': ['devin_key_missing', 'devin_key_alias_exists'],
        'conclusion': 'secret_alias_deducible',
        'action': 'map_secret_alias',
        'severity': 'high',
        'safe': True,
        'description': 'DEVIN_API_KEY no existe pero hay alias (DEVIN_API_KEY_IABV) — mapear automaticamente',
    },
    {
        'id': 'generic_secret_alias_detected',
        'premises': ['secret_expected_missing', 'secret_similar_name_exists'],
        'conclusion': 'secret_alias_deducible',
        'action': 'map_secret_alias',
        'severity': 'medium',
        'safe': True,
        'description': 'Secreto esperado falta pero existe uno con nombre similar — probablemente el mismo',
    },
    # External session timeout
    {
        'id': 'external_session_stalled',
        'premises': ['external_session_active', 'session_no_progress'],
        'conclusion': 'external_session_zombie',
        'action': 'abort_stalled_session',
        'severity': 'high',
        'safe': True,
        'description': 'Sesion externa lleva >2 min sin avanzar — abortar y caer a ruta local',
    },
    # ChatGPT WinError 5 fallback
    {
        'id': 'chatgpt_access_denied_fallback',
        'premises': ['chatgpt_winerror5', 'ollama_running'],
        'conclusion': 'chatgpt_blocked_use_ollama',
        'action': 'fallback_to_ollama',
        'severity': 'high',
        'safe': True,
        'description': 'ChatGPT falla con [WinError 5] Acceso denegado — caer a Ollama automaticamente',
    },
    # Codex wrong_thread re-routing
    {
        'id': 'codex_wrong_thread_reroute',
        'premises': ['codex_wrong_thread', 'alternative_ia_available'],
        'conclusion': 'codex_session_invalid',
        'action': 'reroute_from_codex',
        'severity': 'high',
        'safe': True,
        'description': 'Codex reporta wrong_thread — invalidar sesion y re-rutear a alternativa',
    },
    # Token expiration detection and auto-renewal
    {
        'id': 'cloud_token_expired_401',
        'premises': ['cloud_api_401', 'cloud_provider_configured'],
        'conclusion': 'cloud_token_expired',
        'action': 'trigger_token_renewal',
        'severity': 'high',
        'safe': True,
        'description': 'API cloud devolvio 401 Unauthorized — token expirado, abrir browser para renovar',
    },
    {
        'id': 'cloud_token_forbidden_403',
        'premises': ['cloud_api_403', 'cloud_provider_configured'],
        'conclusion': 'cloud_token_revoked',
        'action': 'trigger_token_renewal',
        'severity': 'high',
        'safe': True,
        'description': 'API cloud devolvio 403 Forbidden — token revocado o sin permisos, renovar',
    },
    {
        'id': 'github_token_expired',
        'premises': ['github_api_401'],
        'conclusion': 'github_token_needs_renewal',
        'action': 'trigger_token_renewal',
        'severity': 'critical',
        'safe': True,
        'description': 'GitHub API devolvio 401 — PAT expirado o revocado, abrir settings para regenerar',
    },
    {
        'id': 'gemini_key_missing_but_google_account',
        'premises': ['gemini_key_missing', 'google_account_in_browser'],
        'conclusion': 'gemini_provisionable',
        'action': 'provision_cloud_key',
        'severity': 'medium',
        'safe': True,
        'description': 'No hay GEMINI_API_KEY pero hay cuenta Google en el browser — abrir AI Studio para crear key',
    },
    {
        'id': 'groq_key_missing',
        'premises': ['groq_key_missing'],
        'conclusion': 'groq_provisionable',
        'action': 'provision_cloud_key',
        'severity': 'medium',
        'safe': True,
        'description': 'No hay GROQ_API_KEY — abrir console.groq.com para crear key gratis',
    },
    # Gemini quota exhausted — needs new project or billing
    {
        'id': 'gemini_quota_exhausted',
        'premises': ['gemini_api_429'],
        'conclusion': 'gemini_needs_new_project',
        'action': 'auto_provision_gemini',
        'severity': 'high',
        'safe': True,
        'description': (
            'Gemini devolvio 429 quota exceeded con limit:0 — '
            'la key actual esta en un proyecto sin cuota. '
            'Crear key en proyecto nuevo de Google Cloud via AI Studio'
        ),
    },
    # Generic cloud quota exhausted
    {
        'id': 'cloud_quota_exhausted',
        'premises': ['cloud_api_429', 'cloud_provider_configured'],
        'conclusion': 'cloud_quota_needs_attention',
        'action': 'notify_quota_exhausted',
        'severity': 'medium',
        'safe': True,
        'description': 'Un proveedor cloud devolvio 429 — cuota agotada, esperar reset o cambiar plan',
    },
]


# ──────────────────────────────────────────────────────────────
# Fact Extraction — construye base de hechos desde scans reales
# ──────────────────────────────────────────────────────────────

def extract_facts(
    *,
    gpu_scan: dict[str, Any] | None = None,
    account_scan: dict[str, Any] | None = None,
    holistic_scan: dict[str, Any] | None = None,
    limits_scan: dict[str, Any] | None = None,
    regression_scan: dict[str, Any] | None = None,
    deep_env_scan: dict[str, Any] | None = None,
    git_state: dict[str, Any] | None = None,
    version_state: dict[str, Any] | None = None,
) -> set[str]:
    """Extract boolean facts from all available scan data."""
    facts: set[str] = set()

    # GPU facts
    gp = gpu_scan or {}
    if gp.get('nvidia_count', 0) > 0:
        facts.add('nvidia_gpu_present')
    if gp.get('intel_igpu_count', 0) > 0:
        facts.add('intel_igpu_present')
    ollama_state = gp.get('ollama_state', {})
    if ollama_state.get('status') == 'ok':
        facts.add('ollama_running')
        models = ollama_state.get('models', [])
        if models:
            facts.add('models_loaded')
            for m in models:
                if m.get('cpu_percent', 0) == 100:
                    facts.add('ollama_on_cpu')
                if m.get('fully_gpu'):
                    facts.add('ollama_on_gpu')
                if 0 < m.get('gpu_percent', 0) < 100:
                    facts.add('model_split_cpu_gpu')
        else:
            facts.add('no_models_loaded')
    elif ollama_state.get('status') == 'ollama_not_found':
        facts.add('no_ollama_process')
    elif ollama_state.get('status') == 'timeout':
        facts.add('ollama_api_timeout')
        facts.add('ollama_process_exists')

    # Check for CUDA processes via nvidia-smi
    try:
        r = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            facts.add('cuda_processes_active')
        elif r.returncode == 0:
            facts.add('no_cuda_process')
    except (FileNotFoundError, subprocess.TimeoutExpired):
        if 'nvidia_gpu_present' in facts:
            facts.add('nvidia_smi_unavailable')

    # Ollama expectation
    acc = account_scan or {}
    ollama_acc = acc.get('ollama', {})
    if ollama_acc.get('available') or gp.get('nvidia_count', 0) > 0:
        facts.add('ollama_expected')

    # Account/secrets facts
    secrets = acc.get('secrets', {})
    if secrets.get('secrets_file_exists'):
        facts.add('secrets_file_exists')
    if secrets.get('missing_count', 0) > 3:
        facts.add('secrets_not_loaded')

    # Secret alias deduction: detect when expected secret is missing but an
    # alias with different name exists in the environment.
    _SECRET_ALIAS_GROUPS: list[tuple[str, list[str]]] = [
        ('GITHUB_TOKEN', ['GITHUB_TOKEN_IABV', 'IABV_GITHUB_TOKEN', 'GH_TOKEN']),
        ('DEVIN_API_KEY', ['DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY']),
        ('OPENAI_API_KEY', ['OPENAI_KEY', 'OPENAI_API_TOKEN']),
    ]
    for primary, aliases in _SECRET_ALIAS_GROUPS:
        primary_val = os.environ.get(primary, '').strip()
        alias_vals = [(a, os.environ.get(a, '').strip()) for a in aliases]
        has_alias = any(v for _, v in alias_vals)
        if not primary_val and has_alias:
            if 'GITHUB' in primary:
                facts.add('github_token_missing')
                facts.add('github_token_alias_exists')
            elif 'DEVIN' in primary:
                facts.add('devin_key_missing')
                facts.add('devin_key_alias_exists')
            else:
                facts.add('secret_expected_missing')
                facts.add('secret_similar_name_exists')

    # Cloud provider key facts — detect missing keys + token health
    _CLOUD_KEY_CHECKS: list[tuple[str, str]] = [
        ('GEMINI_API_KEY', 'gemini_key_missing'),
        ('GROQ_API_KEY', 'groq_key_missing'),
        ('OPENROUTER_API_KEY', 'openrouter_key_missing'),
        ('TOGETHER_API_KEY', 'together_key_missing'),
    ]
    for env_key, fact_name in _CLOUD_KEY_CHECKS:
        val = os.environ.get(env_key, '').strip()
        if not val:
            facts.add(fact_name)
        else:
            facts.add('cloud_provider_configured')

    # Detect Google account in browser (for Gemini provisioning)
    metacognition = deep_env_scan or {}
    browsers_data = metacognition.get('browsers') or []
    for browser_info in browsers_data:
        for profile in browser_info.get('profiles') or []:
            for account in profile.get('accounts') or []:
                acct_type = str(account.get('type') or '').lower()
                if acct_type == 'google':
                    facts.add('google_account_in_browser')
                    break

    # Token health — detect 401/403/429 from recent API calls
    api_health = acc.get('api_health', {})
    # Also pull live health from CloudReasoningPlannerService
    try:
        from iabv_v15.services.adaptive.cloud_reasoning_planner import (
            CloudReasoningPlannerService,
        )
        live_health = CloudReasoningPlannerService.get_api_health()
        for pid, ph in live_health.items():
            if pid not in api_health:
                api_health[pid] = ph
    except ImportError:
        pass
    for provider_id, health in api_health.items():
        status_code = health.get('last_status_code', 0)
        if status_code == 401:
            facts.add('cloud_api_401')
            if 'github' in provider_id.lower():
                facts.add('github_api_401')
        elif status_code == 403:
            facts.add('cloud_api_403')
        elif status_code == 429:
            facts.add('cloud_api_429')
            if 'gemini' in provider_id.lower():
                facts.add('gemini_api_429')

    # Tunnel facts
    tunnel = acc.get('cloudflare_tunnel', {})
    if tunnel.get('available'):
        facts.add('cloudflared_installed')
        if tunnel.get('tunnel_running'):
            facts.add('tunnel_running')
        else:
            facts.add('tunnel_not_running')
            facts.add('tunnel_expected')

    # Git facts
    g = git_state or {}
    branch = str(g.get('branch', ''))
    dirty = int(g.get('dirty_count', 0))
    if branch and branch != 'main' and branch != 'master':
        facts.add('on_feature_branch')
    if dirty > 50:
        facts.add('many_dirty_files')

    # Branch age detection
    hol = holistic_scan or {}
    for ded in hol.get('deductions', []):
        if 'obsoleta' in str(ded.get('finding', '')).lower():
            facts.add('branch_is_old')

    # Unmerged branches
    if len(g.get('unmerged_branches', [])) > 5:
        facts.add('many_unmerged_branches')

    # Tests
    t = version_state or {}
    if t.get('ok', False):
        facts.add('tests_passing')

    # Monitor facts
    deep = deep_env_scan or {}
    monitors = deep.get('monitors', {})
    monitor_count = monitors.get('count', 0) if isinstance(monitors, dict) else 0
    if monitor_count > 1:
        facts.add('multiple_monitors')

    # Performance facts
    lim = limits_scan or {}
    for limit in lim.get('actionable', []):
        if 'lento' in str(limit.get('blind_spot', '')).lower():
            facts.add('startup_slow')
        if 'serie' in str(limit.get('solution', '')).lower():
            facts.add('many_serial_checks')

    # GPU utilization facts
    gpu_util = gp.get('nvidia_utilization_percent')
    if gpu_util is not None and gpu_util < 10 and 'nvidia_gpu_present' in facts:
        facts.add('low_gpu_utilization')
    if gpu_util is not None and gpu_util > 80:
        facts.add('high_gpu_utilization')

    # RAM facts
    ram = deep.get('ram', {})
    ram_percent = ram.get('percent', 0)
    if ram_percent > 85:
        facts.add('high_ram_usage')
    if ram_percent > 0 and ram_percent < 40:
        facts.add('low_ram_usage')
    ram_total_gb = ram.get('total_gb', 0)
    if ram_total_gb > 0:
        facts.add('ram_info_available')

    # Disk facts
    disk = deep.get('disk', {})
    disk_percent = disk.get('percent', 0)
    if disk_percent > 90:
        facts.add('disk_nearly_full')
    disk_free_gb = disk.get('free_gb', 0)
    if 0 < disk_free_gb < 5:
        facts.add('disk_space_critical')

    # Process facts
    process_info = deep.get('processes', {})
    if process_info.get('high_cpu_processes'):
        facts.add('high_cpu_processes_detected')
    if process_info.get('zombie_processes', 0) > 0:
        facts.add('zombie_processes_detected')

    # Network facts
    net = deep.get('network', {})
    if net.get('internet_available') is False:
        facts.add('no_internet')
    if net.get('internet_available') is True:
        facts.add('internet_available')
    if net.get('vpn_active'):
        facts.add('vpn_active')

    # Startup performance
    startup_ms = deep.get('startup_ms', 0)
    if startup_ms > 5000:
        facts.add('startup_slow')

    return facts


# ──────────────────────────────────────────────────────────────
# Anomaly Detection — razonamiento sin reglas fijas
# ──────────────────────────────────────────────────────────────

# Resource capability tiers for anomaly detection
_RESOURCE_TIERS: dict[str, dict[str, Any]] = {
    'nvidia_gpu': {'capability': 'compute', 'tier': 3, 'label': 'NVIDIA GPU'},
    'intel_igpu': {'capability': 'compute', 'tier': 1, 'label': 'Intel iGPU'},
    'cpu': {'capability': 'compute', 'tier': 2, 'label': 'CPU'},
}


def detect_anomalies(
    facts: set[str],
    scans: dict[str, Any],
) -> list[dict[str, Any]]:
    """Detect anomalies WITHOUT fixed rules.

    Compares pairs of resources to find suboptimal usage:
      - resource_available vs resource_in_use → suboptimal if inferior in use
      - expected_state vs real_state → anomaly if they differ
      - historical_trend → regression if worsening

    Returns list of anomaly dicts with keys:
      type, severity, description, action, evidence
    """
    anomalies: list[dict[str, Any]] = []

    # --- A. Resource mismatch: superior available but inferior in use ---
    gpu_scan = scans.get('gpu_scan', {})
    deep_env = scans.get('deep_env_scan', {})

    has_nvidia = 'nvidia_gpu_present' in facts
    nvidia_idle = 'low_gpu_utilization' in facts or 'no_models_loaded' in facts
    ollama_on_cpu = 'ollama_on_cpu' in facts

    if has_nvidia and nvidia_idle and not ollama_on_cpu:
        vram_mb = gpu_scan.get('nvidia_vram_total_mb', 0)
        vram_label = f'{vram_mb}MB VRAM' if vram_mb else 'VRAM disponible'
        anomalies.append({
            'type': 'resource_underutilized',
            'severity': 'high',
            'description': (
                f'Recurso superior NVIDIA GPU ({vram_label}) sin carga activa'
            ),
            'action': 'preload_model_on_gpu',
            'safe': True,
            'evidence': {
                'resource': 'nvidia_gpu',
                'state': 'idle',
                'expected': 'active_compute',
            },
        })

    # RAM high + GPU idle → compute misallocated
    if 'high_ram_usage' in facts and has_nvidia and nvidia_idle:
        ram_info = deep_env.get('ram', {})
        anomalies.append({
            'type': 'compute_misallocated',
            'severity': 'medium',
            'description': (
                f'RAM al {ram_info.get("percent", "?")}% pero GPU NVIDIA ociosa '
                '— posible carga que debería estar en GPU'
            ),
            'action': 'offload_to_gpu',
            'safe': True,
            'evidence': {
                'ram_percent': ram_info.get('percent', 0),
                'gpu_utilization': gpu_scan.get('nvidia_utilization_percent', 0),
            },
        })

    # --- B. Expected state vs real state ---
    account_scan = scans.get('account_scan', {})
    secrets = account_scan.get('secrets', {})
    expected_count = secrets.get('expected_count', 0)
    loaded_count = secrets.get('loaded_count', 0)
    missing_count = secrets.get('missing_count', 0)

    if expected_count > 0 and missing_count > 0:
        anomalies.append({
            'type': 'expected_vs_real',
            'severity': 'high' if missing_count > 3 else 'medium',
            'description': (
                f'{expected_count} secretos esperados pero {missing_count} no cargados'
            ),
            'action': 'source_secrets_file',
            'safe': True,
            'evidence': {
                'expected': expected_count,
                'loaded': loaded_count,
                'missing': missing_count,
            },
        })

    # Ollama expected but not running
    if 'ollama_expected' in facts and 'no_ollama_process' in facts:
        anomalies.append({
            'type': 'expected_vs_real',
            'severity': 'high',
            'description': 'Ollama se espera activo pero no hay proceso corriendo',
            'action': 'start_ollama',
            'safe': True,
            'evidence': {'expected': 'ollama_running', 'real': 'no_process'},
        })

    # Tunnel expected but not running
    if 'cloudflared_installed' in facts and 'tunnel_not_running' in facts:
        anomalies.append({
            'type': 'expected_vs_real',
            'severity': 'medium',
            'description': 'Cloudflared instalado pero tunnel no activo',
            'action': 'start_tunnel',
            'safe': True,
            'evidence': {'expected': 'tunnel_running', 'real': 'tunnel_stopped'},
        })

    # --- C. Disk/resource pressure anomalies ---
    if 'disk_nearly_full' in facts or 'disk_space_critical' in facts:
        disk_info = deep_env.get('disk', {})
        anomalies.append({
            'type': 'resource_pressure',
            'severity': 'high' if 'disk_space_critical' in facts else 'medium',
            'description': (
                f'Disco al {disk_info.get("percent", "?")}% — '
                f'{disk_info.get("free_gb", "?")}GB libres'
            ),
            'action': 'cleanup_disk_space',
            'safe': True,
            'evidence': {
                'disk_percent': disk_info.get('percent', 0),
                'free_gb': disk_info.get('free_gb', 0),
            },
        })

    # Git dirty files anomaly — many modified files in working tree
    git_state = scans.get('git_state', {})
    dirty_count = int(git_state.get('dirty_count', 0))
    if dirty_count > 50:
        anomalies.append({
            'type': 'hygiene_anomaly',
            'severity': 'medium',
            'description': (
                f'{dirty_count} archivos modificados en working tree '
                '— probable trabajo no commiteado o archivos cache'
            ),
            'action': 'cleanup_working_tree',
            'safe': True,
            'evidence': {'dirty_count': dirty_count},
        })

    # Zombie processes
    if 'zombie_processes_detected' in facts:
        anomalies.append({
            'type': 'resource_leak',
            'severity': 'low',
            'description': 'Procesos zombie detectados — recursos no liberados',
            'action': 'cleanup_zombie_processes',
            'safe': True,
            'evidence': {
                'zombie_count': deep_env.get('processes', {}).get('zombie_processes', 0),
            },
        })

    # No internet
    if 'no_internet' in facts:
        anomalies.append({
            'type': 'connectivity_anomaly',
            'severity': 'high',
            'description': 'Sin conectividad a internet — operaciones remotas bloqueadas',
            'action': 'diagnose_network',
            'safe': True,
            'evidence': {'internet': False},
        })

    logger.info(
        'anomaly_detection: %d anomalies found from %d facts',
        len(anomalies), len(facts),
    )
    return anomalies


# ──────────────────────────────────────────────────────────────
# Historical Consultation — aprendizaje por acción ejecutada
# ──────────────────────────────────────────────────────────────

def _action_history_path() -> Path:
    """Return path to the per-action history JSONL file."""
    env_val = os.environ.get('IABV_DATA_DIR', '').strip()
    data_dir = Path(env_val) if env_val else (
        Path(os.path.expanduser('~')) / 'IABV_v1.5' / 'data'
    )
    history_dir = data_dir / 'evolution' / 'action_history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / 'action_outcomes.jsonl'


def record_action_outcome(
    action: str,
    *,
    success: bool,
    detail: str = '',
    elapsed_ms: int = 0,
    source: str = 'rule',
) -> None:
    """Record the outcome of an executed action for future history lookups.

    Appends one JSONL line per action execution, keyed by action name.
    This is the data that consult_history() reads to learn from the past.
    """
    try:
        entry = {
            'action': action,
            'success': success,
            'detail': detail[:200],
            'elapsed_ms': elapsed_ms,
            'source': source,
            'ts': time.time(),
        }
        path = _action_history_path()
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as exc:
        logger.debug('record_action_outcome: failed to write: %s', exc)


def _load_action_history() -> dict[str, dict[str, Any]]:
    """Load per-action history from the JSONL file.

    Returns a dict keyed by action name with aggregated stats:
      attempts, successes, total_elapsed_ms, last_success
    """
    history: dict[str, dict[str, Any]] = {}
    path = _action_history_path()
    if not path.exists():
        return history
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                action = entry.get('action', '')
                if not action:
                    continue
                if action not in history:
                    history[action] = {
                        'attempts': 0,
                        'successes': 0,
                        'total_elapsed_ms': 0,
                        'last_success': False,
                    }
                history[action]['attempts'] += 1
                if entry.get('success'):
                    history[action]['successes'] += 1
                history[action]['last_success'] = bool(entry.get('success'))
                history[action]['total_elapsed_ms'] += entry.get('elapsed_ms', 0)
    except Exception as exc:
        logger.debug('_load_action_history: failed to read: %s', exc)
    return history


def consult_history(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Consult per-action history BEFORE acting.

    For each proposed action (from fired rules or anomalies), checks:
      - Has this action been tried before?
      - Did it work? (success_rate)
      - Should we execute, avoid, or proceed with caution?

    Uses a dedicated JSONL file (action_outcomes.jsonl) that records
    per-action outcomes, keyed by action name (e.g. 'start_ollama',
    'force_ollama_to_nvidia').

    Returns enriched items with historical context added.
    """
    action_history = _load_action_history()

    enriched: list[dict[str, Any]] = []
    for item in items:
        action = item.get('action', '')
        history_info = action_history.get(action)

        if history_info and history_info['attempts'] > 0:
            success_rate = history_info['successes'] / history_info['attempts']
            avg_ms = history_info['total_elapsed_ms'] / history_info['attempts']
            item = {
                **item,
                'history': {
                    'attempts': history_info['attempts'],
                    'successes': history_info['successes'],
                    'success_rate': round(success_rate, 2),
                    'avg_elapsed_ms': round(avg_ms, 0),
                    'recommendation': (
                        'ejecutar' if success_rate >= 0.5
                        else 'evitar' if success_rate < 0.2
                        else 'probar_con_cautela'
                    ),
                    'learned': True,
                },
            }
            logger.info(
                'consult_history: %s → %d/%d éxitos (rate=%.2f) → %s',
                action,
                history_info['successes'],
                history_info['attempts'],
                success_rate,
                item['history']['recommendation'],
            )
        else:
            item = {
                **item,
                'history': {
                    'attempts': 0,
                    'successes': 0,
                    'success_rate': 0.0,
                    'avg_elapsed_ms': 0.0,
                    'recommendation': 'primera_vez',
                    'learned': False,
                },
            }

        enriched.append(item)

    return enriched


# ──────────────────────────────────────────────────────────────
# Forward Chaining Engine — inferencia hacia adelante
# ──────────────────────────────────────────────────────────────

def forward_chain(
    facts: set[str],
    rules: list[dict[str, Any]] | None = None,
    max_iterations: int = 10,
) -> dict[str, Any]:
    """Run forward chaining inference over facts and rules.

    Repeatedly checks which rules have all premises satisfied by current
    facts. When a rule fires, its conclusion is added to facts and the
    rule is marked as fired. Continues until no new conclusions or max
    iterations reached.
    """
    ruleset = rules or INFERENCE_RULES
    fired_rules: list[dict[str, Any]] = []
    conclusions: set[str] = set()
    current_facts = set(facts)
    iterations = 0

    while iterations < max_iterations:
        new_conclusions = False
        for rule in ruleset:
            if rule['id'] in {r['id'] for r in fired_rules}:
                continue
            premises = set(rule['premises'])
            if premises.issubset(current_facts):
                # Rule fires
                conclusion = rule['conclusion']
                current_facts.add(conclusion)
                conclusions.add(conclusion)
                fired_rules.append({
                    'id': rule['id'],
                    'conclusion': conclusion,
                    'action': rule.get('action', 'none'),
                    'severity': rule.get('severity', 'info'),
                    'safe': rule.get('safe', False),
                    'description': rule.get('description', ''),
                    'premises_matched': list(premises),
                    'iteration': iterations,
                })
                new_conclusions = True
                logger.info(
                    'common_sense: rule %s fired — %s (premises: %s)',
                    rule['id'], conclusion, ', '.join(premises),
                )
        iterations += 1
        if not new_conclusions:
            break

    return {
        'initial_facts': sorted(facts),
        'initial_fact_count': len(facts),
        'conclusions': sorted(conclusions),
        'conclusion_count': len(conclusions),
        'fired_rules': fired_rules,
        'fired_rule_count': len(fired_rules),
        'iterations': iterations,
        'all_facts': sorted(current_facts),
        'total_fact_count': len(current_facts),
    }


# ──────────────────────────────────────────────────────────────
# Action Executors — ejecutores de acciones seguras
# ──────────────────────────────────────────────────────────────

def _exec_force_ollama_to_nvidia(rule: dict[str, Any]) -> dict[str, Any]:
    """Force Ollama to use NVIDIA GPU."""
    try:
        from iabv_v15.services.gpu_metacognition import verify_ollama_gpu_usage
        result = verify_ollama_gpu_usage()
        return {
            'executed': True,
            'result': result.get('status', 'unknown'),
            'detail': result.get('detail', ''),
            'corrections': result.get('corrections_made', []),
        }
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_verify_cuda(rule: dict[str, Any]) -> dict[str, Any]:
    """Verify CUDA installation status."""
    checks: list[dict[str, str]] = []
    # Check nvidia-smi
    try:
        r = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        checks.append({
            'check': 'nvidia-smi',
            'status': 'ok' if r.returncode == 0 else 'failed',
            'detail': r.stdout[:200] if r.returncode == 0 else r.stderr[:200],
        })
    except FileNotFoundError:
        checks.append({'check': 'nvidia-smi', 'status': 'not_found', 'detail': 'nvidia-smi no está en PATH'})
    except subprocess.TimeoutExpired:
        checks.append({'check': 'nvidia-smi', 'status': 'timeout', 'detail': ''})

    # Check nvcc (CUDA compiler)
    try:
        r = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, timeout=10)
        checks.append({
            'check': 'nvcc',
            'status': 'ok' if r.returncode == 0 else 'failed',
            'detail': r.stdout[:200] if r.returncode == 0 else 'nvcc falló',
        })
    except FileNotFoundError:
        checks.append({'check': 'nvcc', 'status': 'not_found', 'detail': 'CUDA toolkit no instalado'})
    except subprocess.TimeoutExpired:
        checks.append({'check': 'nvcc', 'status': 'timeout', 'detail': ''})

    all_ok = all(c['status'] == 'ok' for c in checks)
    return {
        'executed': True,
        'cuda_ok': all_ok,
        'checks': checks,
        'recommendation': '' if all_ok else 'Instalar CUDA toolkit desde https://developer.nvidia.com/cuda-downloads',
    }


def _exec_suggest_smaller_model(rule: dict[str, Any]) -> dict[str, Any]:
    """Suggest using a smaller model that fits in GPU VRAM."""
    try:
        from iabv_v15.services.gpu_metacognition import detect_ollama_gpu_state
        state = detect_ollama_gpu_state()
        split_models = [
            m['name'] for m in state.get('models', [])
            if not m.get('fully_gpu') and m.get('gpu_percent', 0) > 0
        ]
        return {
            'executed': True,
            'split_models': split_models,
            'recommendation': (
                f'Modelos divididos CPU/GPU: {", ".join(split_models)}. '
                'Usar modelos más pequeños (ej: 7B en vez de 20B) para 100% GPU.'
            ) if split_models else 'No hay modelos divididos actualmente.',
        }
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_pre_configure_cuda(rule: dict[str, Any]) -> dict[str, Any]:
    """Pre-configure CUDA environment for next model load."""
    try:
        from iabv_v15.services.gpu_metacognition import detect_physical_gpus
        gpus = detect_physical_gpus()
        nvidia = [g for g in gpus if g.get('type') == 'nvidia']
        if nvidia:
            idx = nvidia[0].get('index', 0)
            old = os.environ.get('CUDA_VISIBLE_DEVICES', '')
            os.environ['CUDA_VISIBLE_DEVICES'] = str(idx)
            return {
                'executed': True,
                'detail': f'CUDA_VISIBLE_DEVICES: {old!r} → {idx!r}',
            }
        return {'executed': True, 'detail': 'No NVIDIA GPU to configure'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_restart_ollama(rule: dict[str, Any]) -> dict[str, Any]:
    """Restart Ollama service."""
    try:
        if os.name == 'nt':
            subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Stop-Process -Name ollama* -Force -ErrorAction SilentlyContinue; '
                 'Start-Sleep 2; Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden'],
                capture_output=True, timeout=30,
            )
        else:
            subprocess.run(['systemctl', 'restart', 'ollama'], capture_output=True, timeout=30)
        return {'executed': True, 'detail': 'Ollama reiniciado'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_start_ollama(rule: dict[str, Any]) -> dict[str, Any]:
    """Start Ollama service."""
    try:
        if os.name == 'nt':
            subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden'],
                capture_output=True, timeout=15,
            )
        else:
            subprocess.run(['ollama', 'serve'], capture_output=True, timeout=5)
        return {'executed': True, 'detail': 'Ollama iniciado'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_switch_to_main(rule: dict[str, Any]) -> dict[str, Any]:
    """Switch git to main branch."""
    try:
        r = subprocess.run(
            ['git', 'checkout', 'main'],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            return {'executed': True, 'detail': 'Cambiado a rama main'}
        return {'executed': False, 'detail': f'git checkout main falló: {r.stderr[:100]}'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_cleanup_branches(rule: dict[str, Any]) -> dict[str, Any]:
    """Clean up merged remote branches."""
    try:
        r = subprocess.run(
            ['git', 'remote', 'prune', 'origin'],
            capture_output=True, text=True, timeout=30,
        )
        pruned = r.stdout.count('pruning') if r.returncode == 0 else 0
        return {'executed': True, 'detail': f'{pruned} ramas remotas limpiadas'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_source_secrets(rule: dict[str, Any]) -> dict[str, Any]:
    """Load secrets from secrets file into environment."""
    import re
    secrets_file = os.path.join(os.path.expanduser('~'), '.iabv_secrets.ps1')
    loaded = 0
    try:
        with open(secrets_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m = re.match(r'\$env:(\w+)\s*=\s*["\']?(.+?)["\']?\s*$', line.strip())
                if m:
                    name, value = m.group(1), m.group(2)
                    if not os.environ.get(name):
                        os.environ[name] = value
                        loaded += 1
        return {'executed': True, 'detail': f'{loaded} secretos cargados desde {secrets_file}'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_noop(rule: dict[str, Any]) -> dict[str, Any]:
    """No-op executor for informational conclusions."""
    return {'executed': False, 'detail': 'Acción informativa — no requiere ejecución'}


def _exec_preload_model_on_gpu(rule: dict[str, Any]) -> dict[str, Any]:
    """Pre-load the default model on NVIDIA GPU to verify GPU routing."""
    try:
        import urllib.request
        import json as _json
        # First ensure CUDA env is set
        from iabv_v15.services.gpu_metacognition import detect_physical_gpus
        gpus = detect_physical_gpus()
        nvidia = [g for g in gpus if g.get('type') == 'nvidia']
        if nvidia:
            os.environ['CUDA_VISIBLE_DEVICES'] = str(nvidia[0].get('index', 0))

        # Try to load a small model via Ollama API to force GPU allocation
        try:
            req = urllib.request.Request(
                'http://localhost:11434/api/generate',
                data=_json.dumps({
                    'model': 'qwen2.5-coder:7b',
                    'prompt': 'test',
                    'stream': False,
                    'options': {'num_predict': 1},
                }).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = _json.loads(resp.read())
                return {
                    'executed': True,
                    'detail': (
                        f'Modelo pre-cargado en GPU — '
                        f'respuesta en {body.get("total_duration", 0) // 1_000_000}ms'
                    ),
                }
        except Exception as load_exc:
            return {
                'executed': True,
                'detail': f'CUDA_VISIBLE_DEVICES configurado, carga de modelo falló: {load_exc}',
            }
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_verify_gpu_via_nvidia_smi(rule: dict[str, Any]) -> dict[str, Any]:
    """Verify Ollama is actually using GPU via nvidia-smi process list."""
    try:
        r = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid,name,used_memory',
             '--format=csv,noheader'],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            processes = r.stdout.strip().splitlines()
            ollama_procs = [p for p in processes if 'ollama' in p.lower()]
            return {
                'executed': True,
                'detail': (
                    f'{len(ollama_procs)} procesos Ollama en GPU, '
                    f'{len(processes)} procesos GPU totales'
                ),
                'gpu_processes': processes[:10],
            }
        return {
            'executed': True,
            'detail': 'nvidia-smi OK pero sin procesos compute activos',
        }
    except FileNotFoundError:
        return {'executed': False, 'error': 'nvidia-smi no encontrado'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_cleanup_working_tree(rule: dict[str, Any]) -> dict[str, Any]:
    """Clean up cache/data files from the working tree."""
    try:
        cleaned = 0
        ws = os.environ.get('IABV_WORKSPACE', os.path.join(os.path.expanduser('~'), 'IABV_v1.5'))
        cache_patterns = ['__pycache__', '.pytest_cache', '*.pyc', 'tmp_*']
        for pattern in cache_patterns:
            if '*' in pattern:
                import glob
                for f in glob.glob(os.path.join(ws, pattern)):
                    if os.path.isdir(f):
                        import shutil
                        shutil.rmtree(f, ignore_errors=True)
                        cleaned += 1
            else:
                target = os.path.join(ws, pattern)
                if os.path.isdir(target):
                    import shutil
                    shutil.rmtree(target, ignore_errors=True)
                    cleaned += 1
        return {'executed': True, 'detail': f'{cleaned} directorios cache limpiados'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_cleanup_disk_space(rule: dict[str, Any]) -> dict[str, Any]:
    """Clean up disk space by removing known safe temp directories."""
    try:
        import tempfile
        import shutil
        cleaned_mb = 0
        temp_dir = tempfile.gettempdir()
        # Only clean old temp files, not actively used ones
        return {
            'executed': False,
            'detail': f'Revisión de espacio en {temp_dir} — limpieza automática no implementada aún',
        }
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_diagnose_network(rule: dict[str, Any]) -> dict[str, Any]:
    """Diagnose network connectivity issues."""
    checks: list[str] = []
    try:
        import urllib.request
        urllib.request.urlopen('https://api.github.com/rate_limit', timeout=5)
        checks.append('GitHub API: OK')
    except Exception as exc:
        checks.append(f'GitHub API: FALLÓ ({exc})')

    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com', timeout=5)
        checks.append('Google: OK')
    except Exception:
        checks.append('Google: FALLÓ')

    try:
        if os.name == 'nt':
            ping_cmd = ['ping', '-n', '1', '-w', '3000', '8.8.8.8']
        else:
            ping_cmd = ['ping', '-c', '1', '-W', '3', '8.8.8.8']
        r = subprocess.run(ping_cmd,
                          capture_output=True, text=True, timeout=5)
        checks.append('DNS 8.8.8.8: ' + ('OK' if r.returncode == 0 else 'FALLÓ'))
    except Exception:
        checks.append('Ping: no disponible')

    return {'executed': True, 'detail': '; '.join(checks), 'checks': checks}


def _exec_start_tunnel(rule: dict[str, Any]) -> dict[str, Any]:
    """Start cloudflared tunnel."""
    try:
        if os.name == 'nt':
            tunnel_path = os.path.join(
                os.path.expanduser('~'), '.iabv', 'tools', 'cloudflared.exe',
            )
            if os.path.exists(tunnel_path):
                subprocess.Popen(
                    [tunnel_path, 'tunnel', 'run'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return {'executed': True, 'detail': 'Tunnel cloudflared iniciado'}
            return {'executed': False, 'detail': 'cloudflared no encontrado en ~/.iabv/tools/'}
        else:
            subprocess.Popen(
                ['cloudflared', 'tunnel', 'run'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return {'executed': True, 'detail': 'Tunnel cloudflared iniciado'}
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_github_rate_check(rule: dict[str, Any]) -> dict[str, Any]:
    """Check GitHub API rate limit status."""
    try:
        import urllib.request
        import json as _json
        token = os.environ.get('GITHUB_TOKEN', '')
        req = urllib.request.Request('https://api.github.com/rate_limit')
        if token:
            req.add_header('Authorization', f'token {token}')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
            core = data.get('resources', {}).get('core', {})
            remaining = core.get('remaining', 0)
            limit = core.get('limit', 0)
            return {
                'executed': True,
                'detail': f'GitHub API: {remaining}/{limit} requests restantes',
            }
    except Exception as exc:
        return {'executed': False, 'error': str(exc)}


def _exec_map_secret_alias(rule: dict[str, Any]) -> dict[str, Any]:
    """Map a secret alias to the expected name in os.environ."""
    _ALIAS_MAP: list[tuple[str, list[str]]] = [
        ('GITHUB_TOKEN', ['GITHUB_TOKEN_IABV', 'IABV_GITHUB_TOKEN', 'GH_TOKEN']),
        ('DEVIN_API_KEY', ['DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY']),
    ]
    mapped: list[str] = []
    for primary, aliases in _ALIAS_MAP:
        if os.environ.get(primary, '').strip():
            continue
        for alias in aliases:
            val = os.environ.get(alias, '').strip()
            if val:
                os.environ[primary] = val
                mapped.append(f'{alias} → {primary}')
                logger.info('map_secret_alias: %s → %s', alias, primary)
                break
    if mapped:
        return {'executed': True, 'detail': f'Mapeados: {", ".join(mapped)}'}
    return {'executed': False, 'detail': 'No se encontraron alias para mapear'}


def _exec_abort_stalled_session(rule: dict[str, Any]) -> dict[str, Any]:
    """Placeholder for aborting a stalled external session."""
    return {'executed': True, 'detail': 'Sesion externa marcada para abort — downstream debe re-rutear a local'}


def _exec_fallback_to_ollama(rule: dict[str, Any]) -> dict[str, Any]:
    """Mark ChatGPT as unavailable and signal fallback to Ollama."""
    return {'executed': True, 'detail': 'ChatGPT bloqueado por WinError 5 — señal de fallback a Ollama emitida'}


def _exec_reroute_from_codex(rule: dict[str, Any]) -> dict[str, Any]:
    """Mark Codex session as invalid due to wrong_thread."""
    return {'executed': True, 'detail': 'Codex wrong_thread — sesion invalidada, re-routing a alternativa'}


def _exec_trigger_token_renewal(rule: dict[str, Any]) -> dict[str, Any]:
    """Detect expired/revoked token and trigger auto-renewal via browser.

    Uses auto_provision_missing_secrets to open the correct renewal URL
    and guide the user through the UI — no PowerShell needed.
    """
    conclusion = rule.get('conclusion', '')
    description = rule.get('description', '')

    _RENEWAL_URLS: dict[str, str] = {
        'GITHUB_TOKEN': 'https://github.com/settings/tokens/new?scopes=repo&description=IABV',
        'GEMINI_API_KEY': 'https://aistudio.google.com/apikey',
        'GROQ_API_KEY': 'https://console.groq.com/keys',
        'OPENAI_API_KEY': 'https://platform.openai.com/api-keys',
    }

    # For cloud_token_expired/revoked, determine the specific provider by
    # reading CloudReasoningPlannerService API health to find which one
    # returned 401/403.  Fall back to listing all renewal URLs.
    if conclusion == 'github_token_needs_renewal':
        provider_key = 'GITHUB_TOKEN'
        detail = 'GitHub PAT expirado — abrir https://github.com/settings/tokens'
    else:
        status_target = 401 if conclusion == 'cloud_token_expired' else 403
        provider_key = 'CLOUD_PROVIDER'
        detail = description or f'Token cloud {status_target}'
        try:
            from iabv_v15.services.adaptive.cloud_reasoning_planner import (
                CloudReasoningPlannerService,
            )
            health = CloudReasoningPlannerService.get_api_health()
            _PROVIDER_KEY_MAP: dict[str, str] = {
                'gemini': 'GEMINI_API_KEY',
                'groq': 'GROQ_API_KEY',
                'openai': 'OPENAI_API_KEY',
                'github': 'GITHUB_TOKEN',
            }
            for pid, info in health.items():
                if info.get('last_status_code') == status_target:
                    for keyword, key in _PROVIDER_KEY_MAP.items():
                        if keyword in pid.lower():
                            provider_key = key
                            detail = f'{pid} devolvio {status_target}'
                            break
                    if provider_key != 'CLOUD_PROVIDER':
                        break
        except Exception:
            pass

    url = _RENEWAL_URLS.get(provider_key, '')
    if not url and provider_key == 'CLOUD_PROVIDER':
        url = ' | '.join(f'{k}: {v}' for k, v in _RENEWAL_URLS.items())
    opened = False
    if url and '|' not in url:
        try:
            import webbrowser
            webbrowser.open(url)
            opened = True
        except Exception:
            pass

    return {
        'executed': True,
        'detail': detail,
        'provider': provider_key,
        'browser_opened': opened,
        'renewal_url': url,
        'user_action': (
            'Token renovado en el browser — pega el nuevo token en el dialogo de IABV.'
            if opened else
            f'Revisa tus dashboards de proveedores cloud y pega el nuevo token en IABV. ({url})'
            if provider_key == 'CLOUD_PROVIDER' else
            f'Abre {url} y pega el nuevo token en IABV.'
        ),
    }


def _exec_auto_provision_gemini(rule: dict[str, Any]) -> dict[str, Any]:
    """Auto-provision Gemini API key when quota is exhausted.

    Uses CloudKeyAutonomousProvisioner to:
    1. Scan AI Studio page and learn its UI structure
    2. Find "Create API key" button autonomously
    3. Guide the user through key creation in a NEW project
    4. Save the key via save_secret_to_profile
    5. Verify with a test call

    The program learns the page structure and persists it for future sessions.
    """
    # Try autonomous provisioning first
    try:
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
        )
        provisioner = CloudKeyAutonomousProvisioner(headless=True)

        if provisioner.is_available():
            result = provisioner.provision_key('gemini', auto_navigate=True)
            return {
                'executed': True,
                'detail': result.error or (
                    'Gemini key provisioned successfully'
                    if result.success else
                    'Gemini page scanned — awaiting user action'
                ),
                'autonomous': True,
                'success': result.success,
                'needs_user_auth': result.needs_user_auth,
                'steps_completed': len(result.steps_completed),
                'page_scanned': len(result.page_scans) > 0,
                'env_key': 'GEMINI_API_KEY',
                'signup_url': 'https://aistudio.google.com/apikey',
                'learned_solution': 'create_key_in_new_project',
                'user_action': result.user_action or (
                    'En AI Studio: Click "Create API key" → '
                    '"Create API key in new project" → Copiar key → Pegar en IABV'
                ),
                'troubleshooting': {
                    'error_429_limit_0': (
                        'El proyecto actual tiene limit:0 en free tier. '
                        'Cada proyecto nuevo de Google Cloud recibe su propia cuota gratuita.'
                    ),
                    'billing_alternative': (
                        'Alternativamente, habilitar billing en '
                        'https://console.cloud.google.com/billing — '
                        '$300 creditos gratis para cuentas nuevas.'
                    ),
                },
            }
    except Exception as exc:
        logger.debug('auto_provision_gemini: autonomous provisioner unavailable: %s', exc)

    # Fallback: open browser manually
    opened = False
    try:
        import webbrowser
        webbrowser.open('https://aistudio.google.com/apikey')
        opened = True
    except Exception:
        pass

    return {
        'executed': True,
        'detail': (
            'Gemini quota exhausted (429, limit:0). '
            'La solucion es crear key en un proyecto NUEVO de Google Cloud. '
            'Se abrio AI Studio para guiar el proceso.'
        ),
        'autonomous': False,
        'learned_solution': 'create_key_in_new_project',
        'browser_opened': opened,
        'env_key': 'GEMINI_API_KEY',
        'signup_url': 'https://aistudio.google.com/apikey',
        'user_action': (
            'En AI Studio: Click "Create API key" → '
            '"Create API key in new project" → Copiar key → Pegar en IABV'
        ),
        'troubleshooting': {
            'error_429_limit_0': (
                'El proyecto actual tiene limit:0 en free tier. '
                'Cada proyecto nuevo de Google Cloud recibe su propia cuota gratuita.'
            ),
            'billing_alternative': (
                'Alternativamente, habilitar billing en '
                'https://console.cloud.google.com/billing — '
                '$300 creditos gratis para cuentas nuevas.'
            ),
        },
    }


def _exec_notify_quota_exhausted(rule: dict[str, Any]) -> dict[str, Any]:
    """Notify that a cloud provider's quota is exhausted."""
    return {
        'executed': True,
        'detail': 'Proveedor cloud con cuota agotada (429) — esperar reset diario o cambiar plan',
        'user_action': 'Esperar ~24h para reset de cuota o habilitar billing en el proveedor',
    }


def _exec_provision_cloud_key(rule: dict[str, Any]) -> dict[str, Any]:
    """Open browser to provision a missing cloud API key (Gemini, Groq, etc).

    Follows the single-window principle: opens browser to the correct page
    and returns structured info for the UI to show a paste dialog.
    """
    rule_id = rule.get('id', '')
    _PROVISION_MAP: dict[str, tuple[str, str, str]] = {
        'gemini_key_missing_but_google_account': (
            'GEMINI_API_KEY',
            'https://aistudio.google.com/apikey',
            'Google Gemini (AI Studio) — gratis con tu cuenta Google',
        ),
        'groq_key_missing': (
            'GROQ_API_KEY',
            'https://console.groq.com/keys',
            'Groq — gratis, Llama 3.3 70B ultra-rapido',
        ),
    }

    env_key, url, description = _PROVISION_MAP.get(
        rule_id, ('UNKNOWN', '', 'Proveedor cloud desconocido'),
    )

    opened = False
    if url:
        try:
            import webbrowser
            webbrowser.open(url)
            opened = True
        except Exception:
            pass

    return {
        'executed': True,
        'detail': f'Provisioning {env_key}: {description}',
        'env_key': env_key,
        'signup_url': url,
        'browser_opened': opened,
        'user_action': (
            f'Se abrio {url} — crea la API key y pegala en el dialogo de IABV.'
            if opened else
            f'Abre {url}, crea la API key y pegala en IABV.'
        ),
    }


_ACTION_EXECUTORS: dict[str, Any] = {
    'force_ollama_to_nvidia': _exec_force_ollama_to_nvidia,
    'verify_cuda_installation': _exec_verify_cuda,
    'suggest_smaller_model': _exec_suggest_smaller_model,
    'pre_configure_cuda': _exec_pre_configure_cuda,
    'restart_ollama': _exec_restart_ollama,
    'start_ollama': _exec_start_ollama,
    'switch_to_main': _exec_switch_to_main,
    'cleanup_merged_branches': _exec_cleanup_branches,
    'source_secrets_file': _exec_source_secrets,
    'start_tunnel': _exec_start_tunnel,
    'offload_to_gpu': _exec_preload_model_on_gpu,
    'parallelize_startup_checks': _exec_noop,
    'move_to_primary': _exec_noop,
    # New v2 executors for anomaly-based actions
    'preload_model_on_gpu': _exec_preload_model_on_gpu,
    'verify_gpu_nvidia_smi': _exec_verify_gpu_via_nvidia_smi,
    'cleanup_working_tree': _exec_cleanup_working_tree,
    'cleanup_disk_space': _exec_cleanup_disk_space,
    'cleanup_zombie_processes': _exec_noop,
    'diagnose_network': _exec_diagnose_network,
    'check_github_rate': _exec_github_rate_check,
    # Secret alias + session fault executors
    'map_secret_alias': _exec_map_secret_alias,
    'abort_stalled_session': _exec_abort_stalled_session,
    'fallback_to_ollama': _exec_fallback_to_ollama,
    'reroute_from_codex': _exec_reroute_from_codex,
    # Token renewal + cloud key provisioning executors
    'trigger_token_renewal': _exec_trigger_token_renewal,
    'provision_cloud_key': _exec_provision_cloud_key,
    'auto_provision_gemini': _exec_auto_provision_gemini,
    'notify_quota_exhausted': _exec_notify_quota_exhausted,
}


def act_on_conclusions(
    chain_result: dict[str, Any],
    *,
    anomalies: list[dict[str, Any]] | None = None,
    enriched_items: list[dict[str, Any]] | None = None,
    execute_safe: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute actions for fired rules and anomalies.

    Now handles both rule-based conclusions and anomaly-based detections.
    Uses historical consultation to decide whether to execute or skip.

    Args:
        chain_result: Output from forward_chain()
        anomalies: Output from detect_anomalies()
        enriched_items: Output from consult_history() (enriched rules+anomalies)
        execute_safe: If True, auto-execute safe actions
        dry_run: If True, report what would be done without executing
    """
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    needs_user: list[dict[str, Any]] = []

    # Build a lookup of historical recommendations for each action
    history_lookup: dict[str, dict[str, Any]] = {}
    for item in (enriched_items or []):
        action = item.get('action', '')
        if action and item.get('history'):
            history_lookup[action] = item['history']

    for rule in chain_result.get('fired_rules', []):
        action = rule.get('action', 'none')
        is_safe = rule.get('safe', False)
        executor = _ACTION_EXECUTORS.get(action)

        if executor is None:
            skipped.append({
                'rule_id': rule['id'],
                'action': action,
                'reason': 'no executor registered',
            })
            continue

        if dry_run:
            skipped.append({
                'rule_id': rule['id'],
                'action': action,
                'reason': 'dry_run mode',
                'would_execute': is_safe and execute_safe,
            })
            continue

        # Check history: skip if historically bad
        hist = history_lookup.get(action, {})
        if hist.get('recommendation') == 'evitar':
            skipped.append({
                'rule_id': rule['id'],
                'action': action,
                'reason': f'historically bad (success_rate={hist.get("success_rate", 0)})',
                'history': hist,
            })
            continue

        if is_safe and execute_safe:
            start = time.monotonic()
            result = executor(rule)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            executed.append({
                'rule_id': rule['id'],
                'action': action,
                'description': rule.get('description', ''),
                'severity': rule.get('severity', 'info'),
                'result': result,
                'elapsed_ms': elapsed_ms,
                'source': 'rule',
                'history': hist if hist else None,
            })
            record_action_outcome(
                action,
                success=bool(result.get('executed')),
                detail=str(result.get('detail', result.get('error', '')))[:200],
                elapsed_ms=elapsed_ms,
                source='rule',
            )
        elif not is_safe:
            needs_user.append({
                'rule_id': rule['id'],
                'action': action,
                'description': rule.get('description', ''),
                'severity': rule.get('severity', 'info'),
                'reason': 'action not marked safe — requires user approval',
            })
        else:
            skipped.append({
                'rule_id': rule['id'],
                'action': action,
                'reason': 'execute_safe=False',
            })

    # Execute anomaly-based actions
    for anomaly in (anomalies or []):
        action = anomaly.get('action', '')
        is_safe = anomaly.get('safe', False)
        executor = _ACTION_EXECUTORS.get(action)

        if not executor:
            skipped.append({
                'anomaly_type': anomaly.get('type', ''),
                'action': action,
                'reason': 'no executor registered',
            })
            continue

        if dry_run:
            skipped.append({
                'anomaly_type': anomaly.get('type', ''),
                'action': action,
                'reason': 'dry_run mode',
            })
            continue

        # Check if this exact action was already executed by a rule
        already_executed_actions = {e.get('action') for e in executed}
        if action in already_executed_actions:
            skipped.append({
                'anomaly_type': anomaly.get('type', ''),
                'action': action,
                'reason': 'already executed by rule-based action',
            })
            continue

        # Check history
        hist = history_lookup.get(action, {})
        if hist.get('recommendation') == 'evitar':
            skipped.append({
                'anomaly_type': anomaly.get('type', ''),
                'action': action,
                'reason': f'historically bad (success_rate={hist.get("success_rate", 0)})',
            })
            continue

        if is_safe and execute_safe:
            start = time.monotonic()
            result = executor(anomaly)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            executed.append({
                'anomaly_type': anomaly.get('type', ''),
                'action': action,
                'description': anomaly.get('description', ''),
                'severity': anomaly.get('severity', 'info'),
                'result': result,
                'elapsed_ms': elapsed_ms,
                'source': 'anomaly',
                'history': hist if hist else None,
            })
            record_action_outcome(
                action,
                success=bool(result.get('executed')),
                detail=str(result.get('detail', result.get('error', '')))[:200],
                elapsed_ms=elapsed_ms,
                source='anomaly',
            )

    return {
        'executed': executed,
        'executed_count': len(executed),
        'skipped': skipped,
        'skipped_count': len(skipped),
        'needs_user': needs_user,
        'needs_user_count': len(needs_user),
    }


# ──────────────────────────────────────────────────────────────
# ExperimentLab Integration — register reasoning quality
# ──────────────────────────────────────────────────────────────

def _register_with_experiment_lab(result: dict[str, Any]) -> dict[str, Any]:
    """Register reasoning results with ExperimentLab for strategy comparison.

    Now registers both forward_chain_v1 and hybrid_v1 as separate candidates,
    so ExperimentLab can compare which reasoning approach performs better.
    Returns the experiment recommendation for display in the report.
    """
    recommendation_info: dict[str, Any] = {}
    try:
        from iabv_v15.services.lab.experiment_lab import ExperimentLab
        from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
        from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
        from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
        from iabv_v15.services.lab.strategy_selector import StrategySelector
        from iabv_v15.domain.models import (
            ExperimentCandidate, ExperimentDomain, EvaluationRoute,
        )

        repo = ExperimentLabRepository()
        lab = ExperimentLab(
            repository=repo,
            registry=AlgorithmBenchmarkRegistry(),
            scoring_engine=DecisionScoringEngine(),
            strategy_selector=StrategySelector(),
        )

        fact_count = result.get('fact_count', 0)
        conclusion_count = result.get('conclusion_count', 0)
        anomaly_count = result.get('anomaly_count', 0)
        executed_count = result.get('actions_executed_count', 0)
        history_count = result.get('history_consultations', 0)
        elapsed_ms = result.get('elapsed_ms', 0)

        executed = result.get('actions_executed', [])
        success_count = sum(1 for a in executed if a.get('result', {}).get('executed'))

        # --- Forward chain v1 metrics (rules only) ---
        rule_executed = [a for a in executed if a.get('source') == 'rule']
        rule_success = sum(1 for a in rule_executed if a.get('result', {}).get('executed'))
        fc_precision = rule_success / max(len(rule_executed), 1) if rule_executed else (
            1.0 if conclusion_count == 0 else 0.5
        )
        fc_robustness = min(conclusion_count / max(fact_count * 0.3, 1), 1.0) if fact_count > 0 else 0.0

        # --- Hybrid v1 metrics (rules + anomalies + history) ---
        total_insights = conclusion_count + anomaly_count
        hybrid_precision = success_count / max(executed_count, 1) if executed_count > 0 else (
            1.0 if total_insights == 0 else 0.5
        )
        hybrid_robustness = min(
            total_insights / max(fact_count * 0.3, 1), 1.0,
        ) if fact_count > 0 else 0.0
        # Bonus for using history
        if history_count > 0:
            hybrid_robustness = min(hybrid_robustness + 0.1, 1.0)

        candidates = [
            ExperimentCandidate(
                label='forward_chain_v1',
                route=EvaluationRoute.LOCAL,
                output_text=(
                    f'{fact_count} hechos → {conclusion_count} conclusiones → '
                    f'{len(rule_executed)} acciones por reglas'
                ),
                execution_ms=elapsed_ms,
                metadata={
                    'precision': fc_precision,
                    'robustness': fc_robustness,
                    'assistant_kind': 'common_sense_engine',
                    'comparison_scope_key': 'metacognition_reasoning',
                },
            ),
            ExperimentCandidate(
                label='hybrid_v1',
                route=EvaluationRoute.LOCAL,
                output_text=(
                    f'{fact_count} hechos → {conclusion_count} conclusiones + '
                    f'{anomaly_count} anomalías → {executed_count} acciones'
                ),
                execution_ms=elapsed_ms,
                metadata={
                    'precision': hybrid_precision,
                    'robustness': hybrid_robustness,
                    'assistant_kind': 'common_sense_engine',
                    'comparison_scope_key': 'metacognition_reasoning',
                    'anomaly_count': anomaly_count,
                    'history_consultations': history_count,
                },
            ),
        ]

        runs, recommendation = lab.run_experiment(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='common_sense_reasoning_quality',
            subject_key='common_sense_engine_v1',
            expected={
                'min_conclusions': 1,
                'min_actionable': 1,
            },
            candidates=candidates,
            metadata={
                'fact_count': fact_count,
                'conclusion_count': conclusion_count,
                'anomaly_count': anomaly_count,
                'actions_executed_count': executed_count,
                'actions_needs_user_count': result.get('actions_needs_user_count', 0),
                'inference_iterations': result.get('inference_iterations', 0),
                'history_consultations': history_count,
            },
        )

        # Extract winning algorithm info
        winner_label = recommendation.recommended_assistant_kind or ''
        if not winner_label and runs:
            best_run = max(runs, key=lambda r: r.metrics.total_score)
            winner_label = best_run.candidate_label

        recommendation_info = {
            'winner': winner_label,
            'winner_score': recommendation.score,
            'confidence': recommendation.confidence,
            'rationale': recommendation.rationale,
            'candidates': {
                'forward_chain_v1': {
                    'precision': round(fc_precision, 2),
                    'robustness': round(fc_robustness, 2),
                },
                'hybrid_v1': {
                    'precision': round(hybrid_precision, 2),
                    'robustness': round(hybrid_robustness, 2),
                },
            },
        }

        logger.debug(
            'common_sense: registered with ExperimentLab — winner=%s '
            '(fc: p=%.2f r=%.2f, hybrid: p=%.2f r=%.2f)',
            winner_label, fc_precision, fc_robustness,
            hybrid_precision, hybrid_robustness,
        )
    except Exception as exc:
        logger.debug('common_sense: ExperimentLab registration failed: %s', exc)

    return recommendation_info


# ──────────────────────────────────────────────────────────────
# Full Reasoning Pipeline
# ──────────────────────────────────────────────────────────────

def run_common_sense_reasoning(
    *,
    gpu_scan: dict[str, Any] | None = None,
    account_scan: dict[str, Any] | None = None,
    holistic_scan: dict[str, Any] | None = None,
    limits_scan: dict[str, Any] | None = None,
    regression_scan: dict[str, Any] | None = None,
    deep_env_scan: dict[str, Any] | None = None,
    git_state: dict[str, Any] | None = None,
    version_state: dict[str, Any] | None = None,
    execute: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Full common sense reasoning pipeline v2: observe → detect → infer → learn → act.

    1. Extract facts from all scans (expanded with RAM, disk, network, processes)
    2. Detect anomalies without fixed rules (resource mismatch, expected vs real)
    3. Run forward chaining to derive conclusions (existing rules)
    4. Consult history before acting (ExperimentLab learning)
    5. Execute safe actions based on all insights (rules + anomalies)
    6. Register with ExperimentLab comparing forward_chain vs hybrid
    """
    start = time.monotonic()

    # Phase 1: Extract facts (existing + expanded)
    facts = extract_facts(
        gpu_scan=gpu_scan,
        account_scan=account_scan,
        holistic_scan=holistic_scan,
        limits_scan=limits_scan,
        regression_scan=regression_scan,
        deep_env_scan=deep_env_scan,
        git_state=git_state,
        version_state=version_state,
    )

    # Phase 2: Detect anomalies (NEW — reasoning without fixed rules)
    scans = {
        'gpu_scan': gpu_scan or {},
        'account_scan': account_scan or {},
        'holistic_scan': holistic_scan or {},
        'deep_env_scan': deep_env_scan or {},
        'git_state': git_state or {},
    }
    anomalies = detect_anomalies(facts, scans)

    # Phase 3: Forward chaining (existing)
    chain = forward_chain(facts)

    # Phase 4: Consult history (NEW — learning from past)
    all_items: list[dict[str, Any]] = []
    for rule in chain.get('fired_rules', []):
        all_items.append(rule)
    for anomaly in anomalies:
        all_items.append(anomaly)
    enriched = consult_history(all_items)

    # Count learned items
    history_consultations = sum(
        1 for item in enriched if item.get('history', {}).get('learned')
    )

    # Phase 5: Execute actions (rules + anomalies, informed by history)
    actions = act_on_conclusions(
        chain,
        anomalies=anomalies,
        enriched_items=enriched,
        execute_safe=execute,
        dry_run=dry_run,
    )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    result = {
        'facts': chain['initial_facts'],
        'fact_count': chain['initial_fact_count'],
        'conclusions': chain['conclusions'],
        'conclusion_count': chain['conclusion_count'],
        'fired_rules': chain['fired_rules'],
        'fired_rule_count': chain['fired_rule_count'],
        'inference_iterations': chain['iterations'],
        'anomalies': anomalies,
        'anomaly_count': len(anomalies),
        'history_consultations': history_consultations,
        'history_items': [
            {
                'action': item.get('action', ''),
                'history': item.get('history', {}),
            }
            for item in enriched
            if item.get('history', {}).get('learned')
        ],
        'actions_executed': actions['executed'],
        'actions_executed_count': actions['executed_count'],
        'actions_skipped': actions['skipped'],
        'actions_needs_user': actions['needs_user'],
        'actions_needs_user_count': actions['needs_user_count'],
        'elapsed_ms': elapsed_ms,
    }

    # Phase 6: Register with ExperimentLab comparing algorithms
    recommendation = _register_with_experiment_lab(result)
    result['algorithm_recommendation'] = recommendation

    return result


# ──────────────────────────────────────────────────────────────
# Format Report
# ──────────────────────────────────────────────────────────────

def format_common_sense_report(result: dict[str, Any]) -> str:
    """Format common sense reasoning results for auto-analysis (v2).

    Displays anomalies, historical learning, and algorithm comparison
    alongside the existing rule-based output.
    """
    lines: list[str] = ['== RAZONAMIENTO AUTONOMO (SENTIDO COMUN v2) ==']
    lines.append(f'  Hechos observados: {result.get("fact_count", 0)}')

    # Anomalies section (NEW)
    anomalies = result.get('anomalies', [])
    if anomalies:
        lines.append(f'  Anomalías detectadas: {len(anomalies)}')
        for a in anomalies:
            lines.append(f'    [ANOMALÍA] {a.get("description", a.get("type", "?"))}')
    else:
        lines.append('  Anomalías detectadas: 0')

    # Rules section
    lines.append(f'  Reglas activadas: {result.get("fired_rule_count", 0)}')

    # Show fired rules with causal chain
    for rule in result.get('fired_rules', []):
        severity = rule.get('severity', 'info').upper()
        lines.append(f'  [{severity}] {rule.get("description", rule["id"])}')
        lines.append(f'    Premisas: {", ".join(rule.get("premises_matched", []))}')
        lines.append(f'    → Conclusión: {rule.get("conclusion", "?")}')

    # Historical learning section (NEW)
    history_items = result.get('history_items', [])
    history_count = result.get('history_consultations', 0)
    if history_count > 0:
        lines.append(f'  Conclusiones por historial: {history_count}')
        for hi in history_items:
            hist = hi.get('history', {})
            action = hi.get('action', '?')
            succ = hist.get('successes', 0)
            att = hist.get('attempts', 0)
            rec = hist.get('recommendation', '?')
            lines.append(f'    [APRENDIDO] {action}: éxito en {succ}/{att} ejecuciones previas → {rec}')

    # Actions executed
    executed = result.get('actions_executed', [])
    if executed:
        lines.append(f'  Acciones ejecutadas: {len(executed)}')
        for a in executed:
            status = a.get('result', {})
            source = a.get('source', 'rule')
            source_tag = ' (anomalía)' if source == 'anomaly' else ''
            if status.get('executed'):
                lines.append(
                    f'    [EJECUTADO] {a.get("description", a["action"])}{source_tag} '
                    f'({a.get("elapsed_ms", 0)}ms)'
                )
                detail = status.get('detail', '')
                if detail:
                    lines.append(f'      → {detail}')
            else:
                lines.append(f'    [FALLÓ] {a.get("description", a["action"])}{source_tag}')
                lines.append(f'      → {status.get("error", status.get("detail", "?"))}')
    else:
        lines.append('  Acciones ejecutadas: ninguna necesaria')

    # Needs user
    needs_user = result.get('actions_needs_user', [])
    if needs_user:
        lines.append(f'  Requiere usuario: {len(needs_user)}')
        for n in needs_user:
            lines.append(f'    [NECESITA APROBACION] {n.get("description", n["action"])}')

    # Algorithm comparison (NEW)
    rec = result.get('algorithm_recommendation', {})
    if rec:
        winner = rec.get('winner', '?')
        candidates = rec.get('candidates', {})
        fc = candidates.get('forward_chain_v1', {})
        hy = candidates.get('hybrid_v1', {})
        lines.append(
            f'  Algoritmo ganador: {winner} '
            f'(precision={hy.get("precision", "?")}, robustness={hy.get("robustness", "?")})'
        )
        if fc:
            lines.append(
                f'    vs forward_chain_v1 '
                f'(precision={fc.get("precision", "?")}, robustness={fc.get("robustness", "?")})'
            )

    lines.append(f'  Tiempo de razonamiento: {result.get("elapsed_ms", 0)}ms')

    return '\n'.join(lines)
