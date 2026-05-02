"""Auto-Correction Engine — ejecuta correcciones autónomas basadas en deducciones.

Toma las deducciones del holistic_metacognition_scan y los reportes de
los scanners (accounts, regression, limits, GPU) y ejecuta las acciones
correctivas que sean seguras y automáticas.

Principio: si la corrección es reversible y no requiere aprobación
humana, se ejecuta. Si requiere intervención del usuario, se genera
una solicitud clara con exactamente qué necesita.

Acciones que puede auto-corregir:
  - GPU: configurar CUDA_VISIBLE_DEVICES, liberar VRAM
  - Git: cambiar a main si está en rama obsoleta
  - Tools: reportar herramientas faltantes con comandos de instalación
  - Secrets: reportar secretos faltantes con instrucciones
  - Backlog: crear tareas automátticas para gaps detectados

Acciones que requieren usuario:
  - Instalar software con admin
  - Proveer API keys / tokens
  - Aprobar cambios arquitectónicos
  - Verificar hardware externo
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Correction Registry — maps action names to correction functions
# ──────────────────────────────────────────────────────────────

def _correct_gpu_primary(deduction: dict[str, str],
                         context: dict[str, Any]) -> dict[str, Any]:
    """Ensure NVIDIA GPU is set as primary for CUDA compute."""
    try:
        from iabv_v15.services.gpu_metacognition import (
            startup_gpu_health_check,
        )
        result = startup_gpu_health_check()
        strategy = result.get('dual_gpu_strategy', {})
        if strategy.get('recommended'):
            return {
                'action': 'switch_primary_to_nvidia',
                'status': 'corrected',
                'detail': f'GPU primaria configurada: {strategy.get("primary_compute", "?")}',
                'cuda_devices': os.environ.get('CUDA_VISIBLE_DEVICES', 'default'),
            }
        return {
            'action': 'switch_primary_to_nvidia',
            'status': 'no_action_needed',
            'detail': 'GPU ya está correctamente configurada',
        }
    except Exception as exc:
        return {
            'action': 'switch_primary_to_nvidia',
            'status': 'failed',
            'detail': str(exc),
        }


def _correct_verify_gpu_drivers(deduction: dict[str, str],
                                context: dict[str, Any]) -> dict[str, Any]:
    """Verify GPU drivers and report status."""
    checks: list[str] = []
    nvidia_ok = False

    try:
        r = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
             '--format=csv,noheader'],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            checks.append(f'nvidia-smi OK: {r.stdout.strip()}')
            nvidia_ok = True
        else:
            checks.append('nvidia-smi: no NVIDIA GPU detected or drivers not installed')
    except FileNotFoundError:
        checks.append('nvidia-smi: command not found — NVIDIA drivers not installed')
    except Exception as exc:
        checks.append(f'nvidia-smi: error — {exc}')

    if not nvidia_ok and os.name == 'nt':
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '(Get-CimInstance Win32_VideoController).Name'],
                capture_output=True, text=True, timeout=10,
            )
            if r.stdout.strip():
                gpu_names = r.stdout.strip().splitlines()
                checks.append(f'PowerShell VideoControllers: {", ".join(gpu_names)}')
                if any('nvidia' in g.lower() for g in gpu_names):
                    checks.append('NVIDIA GPU detectada por PowerShell pero nvidia-smi falla — drivers incompletos')
        except Exception:
            pass

    return {
        'action': 'verify_gpu_drivers',
        'status': 'verified' if nvidia_ok else 'needs_user',
        'checks': checks,
        'user_action': None if nvidia_ok else (
            'Instalar NVIDIA drivers desde https://www.nvidia.com/drivers/ '
            'o ejecutar: winget install Nvidia.GeForceExperience'
        ),
    }


def _correct_verify_igpu(deduction: dict[str, str],
                         context: dict[str, Any]) -> dict[str, Any]:
    """Verify Intel iGPU status on dual-GPU laptop."""
    if os.name != 'nt':
        return {
            'action': 'verify_igpu_drivers',
            'status': 'skip',
            'detail': 'iGPU verification only applies to Windows laptops',
        }
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_VideoController | "
             "Where-Object {$_.Name -match 'Intel'} | "
             "Select-Object Name, Status, DriverVersion | "
             "ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10,
        )
        if r.stdout.strip() and r.stdout.strip() != 'null':
            import json
            data = json.loads(r.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            return {
                'action': 'verify_igpu_drivers',
                'status': 'found',
                'igpus': data,
                'detail': f'Intel iGPU encontrada: {data[0].get("Name", "?")}',
            }
        return {
            'action': 'verify_igpu_drivers',
            'status': 'not_found',
            'detail': 'Intel iGPU no detectada por Windows — puede estar deshabilitada en BIOS',
            'user_action': 'Verificar en BIOS que la iGPU Intel está habilitada (MSI: Advanced > Integrated Graphics > Enabled)',
        }
    except Exception as exc:
        return {
            'action': 'verify_igpu_drivers',
            'status': 'error',
            'detail': str(exc),
        }


def _correct_free_gpu_vram(deduction: dict[str, str],
                           context: dict[str, Any]) -> dict[str, Any]:
    """Free GPU VRAM by unloading split models from Ollama."""
    try:
        from iabv_v15.services.gpu_metacognition import auto_free_gpu_for_model
        result = auto_free_gpu_for_model()
        return {
            'action': 'free_gpu_vram',
            'status': 'corrected' if result.get('count', 0) > 0 else 'no_action_needed',
            'freed_models': result.get('freed', []),
            'detail': f'Liberados {result.get("count", 0)} modelos de GPU',
        }
    except Exception as exc:
        return {'action': 'free_gpu_vram', 'status': 'failed', 'detail': str(exc)}


def _generate_tool_install_plan(deduction: dict[str, str],
                                context: dict[str, Any]) -> dict[str, Any]:
    """Generate installation commands for missing tools."""
    limits = context.get('limits_scan', {})
    actionable = limits.get('actionable', [])

    install_commands: list[dict[str, str]] = []
    for lim in actionable:
        solution = lim.get('solution', '')
        if not solution:
            continue
        install_commands.append({
            'blind_spot': lim.get('blind_spot', ''),
            'command': solution,
            'severity': lim.get('severity', 'medium'),
            'category': lim.get('category', ''),
        })

    return {
        'action': 'install_or_update_tools',
        'status': 'needs_user' if install_commands else 'no_action_needed',
        'install_plan': install_commands,
        'count': len(install_commands),
        'user_action': (
            'Ejecutar los comandos de instalación listados. '
            'Algunos requieren permisos de administrador.'
        ) if install_commands else None,
    }


# Known secret providers: name pattern → (url, description, auto_openable)
_SECRET_PROVIDERS: dict[str, tuple[str, str, bool]] = {
    'GITHUB': (
        'https://github.com/settings/tokens/new?scopes=repo&description=IABV',
        'GitHub PAT (scope: repo)', True,
    ),
    'DEVIN': (
        'https://app.devin.ai/settings/api-keys',
        'Devin API Key', True,
    ),
    'OPENAI': (
        'https://platform.openai.com/api-keys',
        'OpenAI API Key', True,
    ),
    'ANTHROPIC': (
        'https://console.anthropic.com/settings/keys',
        'Anthropic API Key', True,
    ),
    'GROQ': (
        'https://console.groq.com/keys',
        'Groq API Key (Llama 3.3 70B, gratis)', True,
    ),
    'GEMINI': (
        'https://aistudio.google.com/apikey',
        'Google Gemini API Key (AI Studio, gratis)', True,
    ),
    'CLOUDFLARE': (
        'https://dash.cloudflare.com/',
        'Cloudflare Zero Trust > Tunnels', True,
    ),
}


def _resolve_secret_provider(name: str) -> tuple[str, str, bool]:
    """Return (url, description, auto_openable) for a secret name."""
    for pattern, provider in _SECRET_PROVIDERS.items():
        if pattern in name:
            return provider
    return ('', f'Configurar $env:{name}', False)


def auto_provision_missing_secrets(
    context: dict[str, Any],
    *,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Auto-detect missing secrets and open browser for provisioning.

    Instead of just reporting "you need to add X to ~/.iabv_secrets.ps1",
    this function:
      1. Detects which secrets are missing
      2. Opens the browser to the correct URL for each provider
      3. Returns structured info so the UI can prompt the user inline

    The user only needs to click "Authorize" or copy-paste the token
    into the UI dialog — no manual PowerShell editing required.
    """
    account_scan = context.get('account_scan', {})
    secrets = account_scan.get('secrets', {})
    missing = secrets.get('missing', [])

    if not missing:
        return {
            'action': 'provision_secrets',
            'status': 'no_action_needed',
            'detail': 'Todos los secretos están configurados',
        }

    provisions: list[dict[str, Any]] = []
    opened_urls: list[str] = []
    auto_provisioned: list[str] = []

    # Try autonomous provisioning first when Playwright is available.
    _AUTONOMOUS_PROVIDERS: dict[str, str] = {
        'GEMINI_API_KEY': 'gemini',
        'GROQ_API_KEY': 'groq',
    }

    for name in missing:
        url, description, can_open = _resolve_secret_provider(name)
        provision: dict[str, Any] = {
            'name': name,
            'description': description,
            'url': url,
            'auto_openable': can_open,
            'opened': False,
            'autonomous': False,
        }

        # Attempt autonomous provisioning for known cloud providers.
        # Tries full Playwright flow first; falls back to browser+dialog.
        autonomous_provider = _AUTONOMOUS_PROVIDERS.get(name)
        if autonomous_provider and open_browser:
            try:
                from iabv_v15.services.cloud_key_autonomous_provisioner import (
                    CloudKeyAutonomousProvisioner,
                )
                provisioner = CloudKeyAutonomousProvisioner()
                if CloudKeyAutonomousProvisioner.is_available():
                    prov_result = provisioner.provision_key(autonomous_provider)
                else:
                    prov_result = provisioner.provision_key_fallback(autonomous_provider)
                provision['autonomous'] = True
                provision['autonomous_result'] = {
                    'success': prov_result.success,
                    'needs_user_auth': prov_result.needs_user_auth,
                    'user_action': prov_result.user_action,
                    'steps': len(prov_result.steps_completed),
                    'mode': 'playwright' if CloudKeyAutonomousProvisioner.is_available() else 'fallback',
                }
                if prov_result.success:
                    auto_provisioned.append(name)
                    provision['opened'] = True
                    provisions.append(provision)
                    logger.info('auto_provision: autonomous success for %s', name)
                    continue
                if prov_result.needs_user_auth:
                    provision['opened'] = True
                    provision['user_action'] = prov_result.user_action
                    provisions.append(provision)
                    continue
            except Exception as exc:
                logger.debug('auto_provision: autonomous failed for %s: %s', name, exc)

        if open_browser and can_open and url:
            try:
                import webbrowser
                webbrowser.open(url)
                provision['opened'] = True
                opened_urls.append(url)
                logger.info('auto_provision: opened browser for %s → %s', name, url)
            except Exception as exc:
                logger.debug('auto_provision: could not open browser for %s: %s', name, exc)

        provisions.append(provision)

    if auto_provisioned and not opened_urls:
        return {
            'action': 'provision_secrets',
            'status': 'auto_provisioned',
            'provisions': provisions,
            'count': len(provisions),
            'auto_provisioned': auto_provisioned,
            'user_action': (
                f'IABV provisiono automaticamente: {", ".join(auto_provisioned)}. '
                f'No se requiere accion manual.'
            ),
        }

    return {
        'action': 'provision_secrets',
        'status': 'needs_user',
        'provisions': provisions,
        'count': len(provisions),
        'opened_count': len(opened_urls),
        'auto_provisioned': auto_provisioned,
        'user_action': (
            'Se abrieron las páginas para crear los tokens. '
            'Pega cada token en el diálogo de IABV cuando lo tengas.'
            if opened_urls else
            'Abre los links indicados y pega los tokens en IABV.'
        ),
    }


def save_secret_to_profile(name: str, value: str) -> dict[str, Any]:
    """Save a secret to ~/.iabv_secrets.ps1 and set it in the environment.

    Called from the UI when the user provides a token. This eliminates
    the need to manually edit PowerShell files.
    """
    import os
    import re

    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        return {
            'status': 'error',
            'name': name,
            'detail': f'Invalid secret name: {name!r} — must be a valid env var name',
        }

    secrets_path = os.path.join(os.path.expanduser('~'), '.iabv_secrets.ps1')
    safe_value = value.replace('\r', '').replace('\n', '').replace("'", "''")  # strip newlines + PS escape
    line_to_add = f"$env:{name} = '{safe_value}'"

    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            pattern = re.compile(
                rf'^\s*\$env:{re.escape(name)}\s*=.*$',
                re.MULTILINE,
            )
            if pattern.search(content):
                content = pattern.sub(lambda _: line_to_add, content)
            else:
                content = content.rstrip() + '\n' + line_to_add + '\n'
        else:
            content = (
                '# iabv_secrets.ps1 — auto-generated by IABV\n'
                '# Do NOT commit this file.\n\n'
                + line_to_add + '\n'
            )

        with open(secrets_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Only set env var after successful file persistence
        os.environ[name] = value

        logger.info('save_secret: %s saved to %s', name, secrets_path)
        return {
            'status': 'saved',
            'name': name,
            'path': secrets_path,
            'detail': f'{name} guardado y activado',
        }
    except Exception as exc:
        logger.warning('save_secret: failed to write %s: %s', name, exc)
        return {
            'status': 'error',
            'name': name,
            'detail': str(exc),
        }


def _generate_secret_request(deduction: dict[str, str],
                             context: dict[str, Any]) -> dict[str, Any]:
    """Generate request for missing secrets/credentials.

    Delegates to auto_provision_missing_secrets for browser-based
    provisioning. Falls back to manual instructions if browser is
    not available.
    """
    return auto_provision_missing_secrets(context, open_browser=False)


def _add_backlog_task_for_gap(deduction: dict[str, str],
                              context: dict[str, Any]) -> dict[str, Any]:
    """Add a backlog task for a detected gap that cannot be auto-corrected."""
    try:
        from iabv_v15.services.evolution_backlog import add_task
        ws = context.get('workspace', '')
        task = add_task(
            title=f'Auto-detectado: {deduction.get("finding", "gap desconocido")[:80]}',
            area=deduction.get('area', 'unknown'),
            priority=deduction.get('severity', 'medium'),
            source='auto_correction_engine',
            evidence=deduction.get('finding', ''),
            workspace=ws,
        )
        return {
            'action': 'add_backlog_task',
            'status': 'created',
            'task_id': task.get('id', ''),
            'title': task.get('title', ''),
        }
    except Exception as exc:
        return {'action': 'add_backlog_task', 'status': 'failed', 'detail': str(exc)}


def _noop(deduction: dict[str, str],
          context: dict[str, Any]) -> dict[str, Any]:
    """No action needed — deduction is informational."""
    return {
        'action': deduction.get('action', 'none'),
        'status': 'informational',
        'detail': deduction.get('finding', ''),
    }


# Map action strings to correction functions
_ACTION_HANDLERS: dict[str, Any] = {
    'auto_switch_to_main': _noop,  # Already handled inline in viewmodel
    'switch_primary_to_nvidia': _correct_gpu_primary,
    'verify_gpu_drivers': _correct_verify_gpu_drivers,
    'verify_igpu_drivers': _correct_verify_igpu,
    'free_gpu_vram': _correct_free_gpu_vram,
    'install_or_update_tools': _generate_tool_install_plan,
    'force_headless_mode': _noop,  # Already handled by consultation mode
    'use_per_test_timeout': _noop,  # Informational
    'ensure_primary_monitor': _noop,  # Informational
    'ask_user': _noop,
    'cleanup_branches_then_retest': _noop,  # Already handled inline
    'none': _noop,
    'investigate_regression': _noop,
    'notify_user': _noop,
    'review_reverts': _noop,  # Informational — user reviews
    'review_file_churn': _noop,  # Informational
    'investigate_oscillation': _noop,  # Informational
    # OSES self-audit auto-correction actions
    'degrade_provider_priority': _noop,  # logged — weight layer handles next cycle
    'block_failing_route': _noop,  # logged — governance blocks next attempt
    'flag_slow_provider': _noop,  # logged — temporal awareness persists flag
    'reclassify_intent': _noop,  # logged — intent learner adjusts patterns
    'trigger_diagnostic_scan': _noop,  # logged — triggers deep scan next cycle
    # Auto-install actions
    'auto_install_dependency': _noop,  # handled by _auto_install_missing_tool
    # Runtime performance auto-corrections
    'reduce_scan_interval': _noop,  # logged — WorldModelService adjusts next cycle
    'increase_network_cache_ttl': _noop,  # logged — probe cache extended
    'consolidate_polling_threads': _noop,  # logged — requires code change
    'lazy_load_services': _noop,  # logged — requires code change
    # Adaptive model selection auto-corrections
    'switch_provider': _noop,  # logged — AdaptiveModelSelector handles
    'rotate_api_key': _noop,  # logged — next call uses new provider
    'cooldown_provider': _noop,  # logged — provider in quota cooldown
    'recommend_local_model': _noop,  # logged — suggest better Ollama model
    # Startup metacognition auto-corrections
    'defer_heavy_viewmodel_init': _noop,  # logged — DashboardViewModel defers refresh
    'investigate_viewmodel_blocking': _noop,  # logged — trigger profiling of VM init
    'reduce_background_thread_load': _noop,  # logged — stagger GIL-heavy tasks
    'profile_memory_allocations': _noop,  # logged — trigger RSS profiler
    'defer_heavy_service_scans': _noop,  # logged — light bootstrap scan
    'parallelize_startup_checks': _noop,  # logged — restructure serial checks
    # QML layer auto-corrections
    'force_shell_ready_fallback': _noop,  # logged — fallback already fires
    'reduce_qml_incubation_load': _noop,  # logged — requires QML refactor
}


def execute_corrections(
    *,
    deductions: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute corrections from a list of deductions (used by OSES self-audit).

    Simpler interface than ``execute_auto_corrections`` — takes raw
    deductions and runs them through the action handler registry.
    """
    ctx = context or {}
    applied: list[dict[str, Any]] = []
    for deduction in deductions:
        action = deduction.get('action', 'none')
        handler = _ACTION_HANDLERS.get(action, _noop)
        try:
            result = handler(deduction, ctx)
            result['source'] = deduction.get('source', 'unknown')
            applied.append(result)
            logger.info(
                'oses_correction: %s -> %s (%s)',
                deduction.get('conclusion', '?'), action,
                result.get('status', '?'),
            )
        except Exception as exc:
            logger.debug('oses_correction failed: %s -- %s', action, exc)
    return {
        'applied': applied,
        'applied_count': len(applied),
    }


# Heavy pip packages that should be installed in background (non-blocking).
# aider-chat is ~200MB+ and can fail on low-RAM machines; installing it
# synchronously during bootstrap freezes the UI and may OOM.
_HEAVY_PIP_PACKAGES: set[str] = {'aider_coder'}
_HEAVY_INSTALL_COOLDOWN_SECONDS = 12 * 60 * 60  # 12h between attempts

# Track background installs so we don't double-launch.
_background_install_threads: dict[str, threading.Thread] = {}
_background_install_lock = threading.Lock()


def _preferred_python_executable() -> str:
    python_exe = sys.executable
    if os.name == 'nt' and python_exe.lower().endswith('pythonw.exe'):
        python_candidate = Path(python_exe).with_name('python.exe')
        if python_candidate.is_file():
            return str(python_candidate)
    return python_exe


def _hidden_subprocess_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if os.name == 'nt':
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
        startupinfo.wShowWindow = 0
        kwargs['creationflags'] = creationflags
        kwargs['startupinfo'] = startupinfo
    return kwargs


def _auto_install_cooldown_path() -> Path:
    workspace_root = Path(os.environ.get('IABV_WORKSPACE_ROOT') or Path.cwd())
    return workspace_root / 'data' / 'evolution' / 'auto_install_cooldowns.json'


def _load_auto_install_cooldowns() -> dict[str, dict[str, Any]]:
    path = _auto_install_cooldown_path()
    if not path.is_file():
        return {}
    try:
        return dict(json.loads(path.read_text(encoding='utf-8')))
    except Exception:
        return {}


def _save_auto_install_cooldowns(data: dict[str, dict[str, Any]]) -> None:
    path = _auto_install_cooldown_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding='utf-8')


def _is_heavy_install_cooldown_active(tool_id: str) -> bool:
    data = _load_auto_install_cooldowns()
    record = dict(data.get(tool_id) or {})
    last_attempt_epoch = float(record.get('last_attempt_epoch') or 0.0)
    if last_attempt_epoch <= 0:
        return False
    return (time.time() - last_attempt_epoch) < _HEAVY_INSTALL_COOLDOWN_SECONDS


def _mark_heavy_install_attempt(tool_id: str, *, status: str) -> None:
    data = _load_auto_install_cooldowns()
    data[tool_id] = {
        'last_attempt_epoch': time.time(),
        'status': status,
    }
    _save_auto_install_cooldowns(data)


def _auto_install_missing_tool(tool_id: str) -> dict[str, Any]:
    """Attempt to auto-install a missing tool/dependency.

    Supports pip packages and known system tools. Returns a result
    dict with status='installed' on success.

    Heavy packages (aider-chat) are installed in a background thread
    and return status='installing_background' immediately.
    """
    _PIP_PACKAGES: dict[str, str] = {
        'aider_coder': 'aider-chat',
        'mcp_client': 'mcp',
    }
    pip_pkg = _PIP_PACKAGES.get(tool_id)
    if pip_pkg:
        # Heavy packages: install in background thread to avoid
        # blocking bootstrap / freezing the UI.
        if tool_id in _HEAVY_PIP_PACKAGES:
            return _install_in_background(tool_id, pip_pkg)
        try:
            result = subprocess.run(
                [_preferred_python_executable(), '-m', 'pip', 'install', pip_pkg, '-q'],
                capture_output=True, text=True, timeout=120,
                stdin=subprocess.DEVNULL,
                **_hidden_subprocess_kwargs(),
            )
            if result.returncode == 0:
                logger.info('auto_install: %s installed via pip (%s)', tool_id, pip_pkg)
                return {
                    'action': 'auto_install_dependency',
                    'status': 'installed',
                    'tool_id': tool_id,
                    'package': pip_pkg,
                    'method': 'pip',
                }
            return {
                'action': 'auto_install_dependency',
                'status': 'failed',
                'tool_id': tool_id,
                'detail': result.stderr[:200],
            }
        except Exception as exc:
            return {
                'action': 'auto_install_dependency',
                'status': 'failed',
                'tool_id': tool_id,
                'detail': str(exc),
            }
    return {
        'action': 'auto_install_dependency',
        'status': 'unknown_tool',
        'tool_id': tool_id,
    }


def _install_in_background(tool_id: str, pip_pkg: str) -> dict[str, Any]:
    """Launch a pip install in a daemon thread. Non-blocking."""

    if _is_heavy_install_cooldown_active(tool_id):
        return {
            'action': 'auto_install_dependency',
            'status': 'cooldown_active',
            'tool_id': tool_id,
            'package': pip_pkg,
            'detail': f'recent {tool_id} auto-install attempt is still in cooldown',
        }

    def _worker() -> None:
        try:
            log_path = _auto_install_cooldown_path().parent.parent / 'logs' / f'auto_install_{tool_id}.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open('ab') as log_handle:
                result = subprocess.run(
                    [_preferred_python_executable(), '-m', 'pip', 'install', pip_pkg, '-q'],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    timeout=600,
                    **_hidden_subprocess_kwargs(),
                )
            if result.returncode == 0:
                _mark_heavy_install_attempt(tool_id, status='installed')
                logger.info('auto_install_bg: %s installed via pip (%s)', tool_id, pip_pkg)
            else:
                _mark_heavy_install_attempt(tool_id, status='failed')
                logger.warning(
                    'auto_install_bg: %s failed with code %s', tool_id, result.returncode,
                )
        except Exception as exc:
            _mark_heavy_install_attempt(tool_id, status='exception')
            logger.warning('auto_install_bg: %s exception -- %s', tool_id, exc)

    with _background_install_lock:
        existing = _background_install_threads.get(tool_id)
        if existing is not None and existing.is_alive():
            return {
                'action': 'auto_install_dependency',
                'status': 'already_installing',
                'tool_id': tool_id,
                'package': pip_pkg,
            }
        t = threading.Thread(target=_worker, name=f'bg-install-{tool_id}', daemon=True)
        _background_install_threads[tool_id] = t

    _mark_heavy_install_attempt(tool_id, status='queued')
    t.start()
    logger.info('auto_install_bg: %s queued for background install (%s)', tool_id, pip_pkg)
    return {
        'action': 'auto_install_dependency',
        'status': 'installing_background',
        'tool_id': tool_id,
        'package': pip_pkg,
        'detail': f'{pip_pkg} is heavy (~200MB); installing in background thread',
    }


def auto_fix_missing_tools(missing_tools: list[str]) -> dict[str, Any]:
    """Auto-install all missing tools that can be resolved via pip.

    Called by bootstrap or OSES when tool_missing is detected.
    Returns summary of installations.
    """
    results: list[dict[str, Any]] = []
    for tool_id in missing_tools:
        result = _auto_install_missing_tool(tool_id)
        results.append(result)
    installed = [r for r in results if r.get('status') == 'installed']
    return {
        'total': len(missing_tools),
        'installed': len(installed),
        'results': results,
    }


# ──────────────────────────────────────────────────────────────
# Runtime Log Auto-Correction — reacts to _runtime_log_findings
# ──────────────────────────────────────────────────────────────

def _correct_runtime_noise_disagreement(
    finding: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """When multi_source_disagreement is noisy, bump the cache TTL."""
    count = finding.get('occurrences', 0)
    if count <= 5:
        return {'action': 'bump_disagreement_ttl', 'status': 'no_action_needed',
                'detail': f'{count} occurrences — within threshold'}
    try:
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        old_ttl = ToolAdapter._MULTI_SOURCE_CACHE_TTL
        new_ttl = min(old_ttl * 2, 600.0)
        if new_ttl > old_ttl:
            ToolAdapter._MULTI_SOURCE_CACHE_TTL = new_ttl
            ToolAdapter.persist_ttl()
            logger.info(
                'auto-correction: bumped multi_source_cache TTL %s→%s '
                'due to %d disagreement logs', old_ttl, new_ttl, count,
            )
            return {'action': 'bump_disagreement_ttl', 'status': 'corrected',
                    'detail': f'TTL {old_ttl}→{new_ttl}s (triggered by {count} occurrences)'}
        return {'action': 'bump_disagreement_ttl', 'status': 'no_action_needed',
                'detail': f'TTL already at max ({old_ttl}s)'}
    except Exception as exc:
        return {'action': 'bump_disagreement_ttl', 'status': 'failed', 'detail': str(exc)}


def _correct_ghost_session(
    finding: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """Clean up marker files from ghost sessions."""
    workspace = context.get('workspace', '')
    if not workspace:
        return {'action': 'cleanup_ghost_markers', 'status': 'no_action_needed',
                'detail': 'No workspace provided'}
    marker_dir = Path(workspace) / 'data' / 'logs'
    cleaned = 0
    try:
        import time as _time
        for marker in marker_dir.glob('.disagreement_*.marker'):
            age = _time.time() - marker.stat().st_mtime
            if age > 300:
                marker.unlink(missing_ok=True)
                cleaned += 1
    except OSError:
        pass
    detail = f'Cleaned {cleaned} stale markers' if cleaned else 'No stale markers found'
    return {'action': 'cleanup_ghost_markers',
            'status': 'corrected' if cleaned else 'no_action_needed',
            'detail': detail}


def _correct_http_noise(
    finding: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """Re-apply httpx/httpcore suppression if noise is detected in logs.

    The primary suppression happens at startup via
    ``suppress_noisy_http_loggers()`` in ``infra/logging.py``.
    This handler acts as a safety net: if something resets the log
    levels at runtime, the auto-correction loop will re-suppress.
    """
    count = finding.get('occurrences', 0)
    if count <= 20:
        return {'action': 'suppress_httpx', 'status': 'no_action_needed',
                'detail': f'{count} HTTP lines — within threshold'}
    try:
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        import logging as _logging
        httpx_logger = _logging.getLogger('httpx')
        already_suppressed = httpx_logger.level >= _logging.WARNING
        suppress_noisy_http_loggers()
        if already_suppressed:
            return {'action': 'suppress_httpx', 'status': 'no_action_needed',
                    'detail': 'httpx already at WARNING or higher (noise is from before suppression)'}
        logger.info(
            'auto-correction: re-suppressed httpx/httpcore to WARNING '
            'due to %d HTTP log lines (levels were reset at runtime)',
            count,
        )
        return {'action': 'suppress_httpx', 'status': 'corrected',
                'detail': f'httpx→WARNING re-applied (triggered by {count} HTTP lines in log tail)'}
    except Exception as exc:
        return {'action': 'suppress_httpx', 'status': 'failed', 'detail': str(exc)}


def _correct_cloudflare_blocked(
    finding: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """When Cloudflare blocks isolated sessions, recommend using the user's browser via CDP."""
    count = finding.get('occurrences', 0)
    if count < 1:
        return {'action': 'prefer_cdp_session', 'status': 'no_action_needed',
                'detail': 'no cloudflare blocks detected'}
    # Scan user's browser accounts to enrich the recommendation
    try:
        from iabv_v15.services.account_resource_scanner import scan_browser_accounts
        browser_info = scan_browser_accounts()
        acct_count = browser_info.get('count', 0)
    except Exception:
        acct_count = 0
    detail = (
        f'Cloudflare bloqueo {count} sesion(es) aislada(s). '
        f'El usuario tiene {acct_count} cuenta(s) en sus navegadores. '
        f'Preferir CDP (use_browser_session=False) para reusar las cookies '
        f'y sesiones activas del usuario en vez de sesiones aisladas limpias.'
    )
    logger.info(
        'auto-correction: cloudflare_blocked — %d bloqueo(s) detectado(s), '
        '%d cuenta(s) de navegador disponibles. '
        'Recomendacion: usar CDP del Chrome del usuario.',
        count, acct_count,
    )
    return {'action': 'prefer_cdp_session', 'status': 'corrected', 'detail': detail}


def _correct_wrong_thread(
    finding: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """When wrong_thread is detected, log a recommendation to create a dedicated thread."""
    count = finding.get('occurrences', 0)
    if count < 1:
        return {'action': 'fix_thread_routing', 'status': 'no_action_needed',
                'detail': 'no wrong_thread events'}
    logger.info(
        'auto-correction: wrong_thread — %d captura(s) en hilo incorrecto. '
        'Recomendacion: crear hilo dedicado o validar thread_key antes de capturar.',
        count,
    )
    return {
        'action': 'fix_thread_routing', 'status': 'corrected',
        'detail': f'{count} captura(s) en hilo incorrecto. Crear hilo dedicado.',
    }


def _correct_adapter_missing(
    finding: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """When adapter_missing is detected, log available alternatives."""
    count = finding.get('occurrences', 0)
    if count < 1:
        return {'action': 'resolve_adapter', 'status': 'no_action_needed',
                'detail': 'no adapter_missing events'}
    logger.info(
        'auto-correction: adapter_missing — %d fase(s) sin adaptador operativo. '
        'Recomendacion: verificar ToolRegistry para ejecutores locales disponibles '
        'o escalar a Codex/Devin para integracion.',
        count,
    )
    return {
        'action': 'resolve_adapter', 'status': 'corrected',
        'detail': f'{count} fase(s) sin adaptador. Verificar ToolRegistry o escalar.',
    }


# Maps runtime log anomaly categories to correction functions.
_RUNTIME_LOG_HANDLERS: dict[str, Any] = {
    'runtime_noise': _correct_runtime_noise_disagreement,
    'ghost_session': _correct_ghost_session,
    'http_noise': _correct_http_noise,
    'cloudflare_blocked': _correct_cloudflare_blocked,
    'wrong_thread': _correct_wrong_thread,
    'session_verification_failed': _correct_cloudflare_blocked,
    'adapter_missing': _correct_adapter_missing,
    'external_consultation_failure': _noop,
    'tool_availability': _noop,
}


def apply_runtime_log_corrections(
    findings: list[dict[str, Any]],
    *,
    workspace: str = '',
) -> dict[str, Any]:
    """Apply auto-corrections based on runtime log findings.

    Called by OperationalSelfExaminationService after _runtime_log_findings()
    produces findings. This closes the loop: the program detects its own
    anomalies in the log and corrects them automatically.

    Returns a summary of corrections applied and informational items.
    """
    context = {'workspace': workspace}
    corrections: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for finding in findings:
        category = finding.get('category', '')
        handler = _RUNTIME_LOG_HANDLERS.get(category)
        if handler is None:
            skipped.append({'category': category, 'reason': 'no_handler'})
            continue
        result = handler(finding, context)
        status = result.get('status', '')
        if status == 'corrected':
            corrections.append(result)
            logger.info('runtime auto-correction: %s — %s',
                        result.get('action', '?'), result.get('detail', ''))
        elif status != 'no_action_needed':
            skipped.append({'category': category, 'status': status,
                            'detail': result.get('detail', '')})

    return {
        'corrections_applied': corrections,
        'corrections_count': len(corrections),
        'skipped': skipped,
        'skipped_count': len(skipped),
    }


# ──────────────────────────────────────────────────────────────
# Tool Deduction — what tools/resources are missing and how to get them
# ──────────────────────────────────────────────────────────────

def deduce_missing_tools(
    *,
    account_scan: dict[str, Any] | None = None,
    limits_scan: dict[str, Any] | None = None,
    gpu_scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deduce what tools, APIs, and resources IABV needs but doesn't have.

    Returns a structured plan of what's missing and how to get it,
    organized by urgency and who needs to act (program vs user).
    """
    auto_fixable: list[dict[str, str]] = []
    needs_user: list[dict[str, str]] = []
    informational: list[dict[str, str]] = []

    # From limits scan — software and hardware gaps
    lim = limits_scan or {}
    for limit in lim.get('actionable', []):
        category = limit.get('category', '')
        solution = limit.get('solution', '')
        severity = limit.get('severity', 'medium')

        if category == 'software' and 'pip install' in solution:
            auto_fixable.append({
                'what': limit.get('blind_spot', ''),
                'command': solution,
                'type': 'python_package',
                'severity': severity,
            })
        elif category == 'software':
            needs_user.append({
                'what': limit.get('blind_spot', ''),
                'how': solution,
                'type': 'external_tool',
                'severity': severity,
            })
        elif category == 'hardware':
            needs_user.append({
                'what': limit.get('blind_spot', ''),
                'how': solution,
                'type': 'hardware_driver',
                'severity': severity,
            })
        elif category == 'knowledge':
            auto_fixable.append({
                'what': limit.get('blind_spot', ''),
                'command': solution,
                'type': 'knowledge_gap',
                'severity': severity,
            })
        else:
            informational.append({
                'what': limit.get('blind_spot', ''),
                'detail': solution,
                'severity': severity,
            })

    # From account scan — missing APIs and secrets
    acc = account_scan or {}
    secrets = acc.get('secrets', {})
    for name in secrets.get('missing', []):
        # Determine how important this secret is
        importance = 'high' if name in ('GITHUB_TOKEN_IABV', 'DEVIN_API_KEY_IABV') else 'medium'
        url = ''
        if 'GITHUB' in name:
            url = 'https://github.com/settings/tokens/new'
        elif 'DEVIN' in name:
            url = 'https://app.devin.ai/settings'
        elif 'OPENAI' in name:
            url = 'https://platform.openai.com/api-keys'
        elif 'ANTHROPIC' in name:
            url = 'https://console.anthropic.com/settings/keys'

        needs_user.append({
            'what': f'Secret {name} no configurado',
            'how': f'Generar en {url}' if url else f'Configurar: $env:{name}="valor"',
            'type': 'api_credential',
            'severity': importance,
        })

    # GPU-specific deductions
    gp = gpu_scan or {}
    if gp.get('nvidia_count', 0) == 0 and os.name == 'nt':
        needs_user.append({
            'what': 'NVIDIA GPU no detectada (drivers)',
            'how': 'Instalar desde https://www.nvidia.com/drivers/ o: winget install Nvidia.GeForceExperience',
            'type': 'hardware_driver',
            'severity': 'high',
        })
    for issue in gp.get('issues', []):
        if '100% CPU' in issue:
            auto_fixable.append({
                'what': 'Modelo de Ollama corriendo en CPU cuando hay GPU',
                'command': 'Verificar CUDA: ollama run --verbose',
                'type': 'gpu_config',
                'severity': 'high',
            })

    return {
        'auto_fixable': auto_fixable,
        'needs_user': needs_user,
        'informational': informational,
        'auto_fixable_count': len(auto_fixable),
        'needs_user_count': len(needs_user),
        'total_gaps': len(auto_fixable) + len(needs_user) + len(informational),
    }


# ──────────────────────────────────────────────────────────────
# Main Auto-Correction Entry Point
# ──────────────────────────────────────────────────────────────

def execute_auto_corrections(
    *,
    holistic_scan: dict[str, Any] | None = None,
    account_scan: dict[str, Any] | None = None,
    limits_scan: dict[str, Any] | None = None,
    gpu_scan: dict[str, Any] | None = None,
    regression_scan: dict[str, Any] | None = None,
    deep_env_scan: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    """Execute all safe auto-corrections and generate user requests for the rest.

    Returns:
      - corrections_applied: list of corrections that were executed automatically
      - user_requests: list of things that need user intervention
      - tool_deduction: what tools/resources are missing
      - backlog_tasks_created: tasks added to backlog for unresolved gaps
    """
    context = {
        'account_scan': account_scan or {},
        'limits_scan': limits_scan or {},
        'gpu_scan': gpu_scan or {},
        'regression_scan': regression_scan or {},
        'deep_env_scan': deep_env_scan or {},
        'workspace': workspace or '',
    }

    corrections_applied: list[dict[str, Any]] = []
    user_requests: list[dict[str, Any]] = []
    backlog_tasks_created: list[dict[str, Any]] = []

    # Process holistic deductions
    hol = holistic_scan or {}
    for deduction in hol.get('deductions', []):
        action = deduction.get('action', 'none')
        handler = _ACTION_HANDLERS.get(action)

        if handler is None:
            # Unknown action — add to backlog
            result = _add_backlog_task_for_gap(deduction, context)
            backlog_tasks_created.append(result)
            continue

        result = handler(deduction, context)
        status = result.get('status', '')

        if status == 'corrected':
            corrections_applied.append(result)
            logger.info('auto-correction applied: %s — %s',
                        action, result.get('detail', ''))
        elif status == 'needs_user':
            user_requests.append(result)
        elif status == 'failed':
            logger.warning('auto-correction failed: %s — %s',
                           action, result.get('detail', ''))
            backlog_task = _add_backlog_task_for_gap(deduction, context)
            backlog_tasks_created.append(backlog_task)

    # GPU routing verification — ensure Ollama is on NVIDIA, not Intel/CPU
    try:
        from iabv_v15.services.gpu_metacognition import verify_ollama_gpu_usage
        gpu_routing = verify_ollama_gpu_usage()
        gpu_status = gpu_routing.get('status', '')
        if gpu_status in ('suboptimal', 'uncertain'):
            # Auto-corrected — Ollama was on wrong GPU
            for corr in gpu_routing.get('corrections_made', []):
                corrections_applied.append({
                    'action': corr.get('action', 'gpu_routing'),
                    'status': 'corrected',
                    'detail': corr.get('detail', ''),
                })
            logger.info('gpu_routing auto-corrected: %s', gpu_routing.get('detail', ''))
        elif gpu_status == 'optimal':
            corrections_applied.append({
                'action': 'gpu_routing_verified',
                'status': 'corrected',
                'detail': gpu_routing.get('detail', 'Ollama en NVIDIA — óptimo'),
            })
        elif gpu_status == 'idle':
            for corr in gpu_routing.get('corrections_made', []):
                corrections_applied.append({
                    'action': corr.get('action', 'gpu_pre_config'),
                    'status': 'corrected',
                    'detail': corr.get('detail', ''),
                })
    except Exception as exc:
        logger.debug('gpu_routing check failed: %s', exc)

    # Generate missing secrets request if there are missing secrets
    secrets_result = _generate_secret_request({}, context)
    if secrets_result.get('status') == 'needs_user':
        user_requests.append(secrets_result)

    # Deduce missing tools
    tool_deduction = deduce_missing_tools(
        account_scan=account_scan,
        limits_scan=limits_scan,
        gpu_scan=gpu_scan,
    )

    # Auto-fix Python packages if possible
    for fix in tool_deduction.get('auto_fixable', []):
        if fix.get('type') == 'python_package':
            cmd = fix.get('command', '')
            if cmd.startswith('pip install'):
                try:
                    r = subprocess.run(
                        cmd.split(),
                        capture_output=True, text=True, timeout=60,
                    )
                    if r.returncode == 0:
                        corrections_applied.append({
                            'action': 'auto_install_package',
                            'status': 'corrected',
                            'detail': f'Instalado: {cmd}',
                        })
                    else:
                        user_requests.append({
                            'action': 'install_package',
                            'status': 'needs_user',
                            'detail': f'Falló: {cmd} — {r.stderr[:100]}',
                            'user_action': f'Ejecutar manualmente: {cmd}',
                        })
                except Exception as exc:
                    logger.debug('auto_install failed: %s', exc)

    # Add user-needed tools from deduction
    for need in tool_deduction.get('needs_user', []):
        user_requests.append({
            'action': 'install_tool',
            'status': 'needs_user',
            'what': need.get('what', ''),
            'user_action': need.get('how', ''),
            'severity': need.get('severity', 'medium'),
        })

    # NOTE: common sense reasoning is NOT called here to avoid double
    # execution of side-effecting actions (subprocess.Popen, HTTP requests).
    # The viewmodel (control_center_viewmodel.py §4.9) calls
    # run_common_sense_reasoning() separately with richer context
    # (git_state, version_state, deep_env_scan) and formats its own report.

    return {
        'corrections_applied': corrections_applied,
        'corrections_count': len(corrections_applied),
        'user_requests': user_requests,
        'user_requests_count': len(user_requests),
        'tool_deduction': tool_deduction,
        'backlog_tasks_created': backlog_tasks_created,
        'backlog_tasks_count': len(backlog_tasks_created),
    }


# ──────────────────────────────────────────────────────────────
# Deductive Reasoning Engine — general-purpose reasoning via Ollama
#
# Instead of hardcoded if/then rules for each problem, this engine:
# 1. Collects all findings + available context (tools, accounts, APIs)
# 2. Asks Ollama to reason about the root cause and propose corrections
# 3. Parses the structured response and executes safe corrections
#
# The program learns to fix NEW problems without us programming each case.
# ──────────────────────────────────────────────────────────────

_DEDUCTIVE_SYSTEM_PROMPT = """\
Eres el motor de razonamiento interno de IABV v1.5, un programa local-first
que controla herramientas en el laptop del usuario. Tu trabajo es analizar
problemas operativos detectados y deducir la mejor correccion usando los
recursos disponibles.

REGLAS:
- Responde SOLO en JSON valido, sin markdown ni explicaciones fuera del JSON.
- Cada correccion debe ser una de las ACCIONES PERMITIDAS.
- Si no hay correccion segura, responde con acciones vacias.
- Nunca inventes recursos que no estan en el contexto.
- Prioriza reusar lo que ya existe (cuentas del navegador, APIs, herramientas).

ACCIONES PERMITIDAS:
- "switch_to_cdp": Cambiar de sesion aislada a CDP del navegador del usuario.
  Parametros: {"reason": "...", "target_tool": "chatgpt|claude|codex"}
- "create_dedicated_thread": Crear un hilo dedicado para el asistente.
  Parametros: {"reason": "...", "assistant_kind": "..."}
- "suppress_logger": Suprimir un logger ruidoso.
  Parametros: {"logger_name": "...", "level": "WARNING"}
- "bump_cache_ttl": Aumentar TTL de cache para reducir re-escaneos.
  Parametros: {"cache_name": "...", "new_ttl": 300}
- "recommend_adapter": Recomendar un adaptador o executor para una fase.
  Parametros: {"phase": "...", "available_tools": [...], "recommendation": "..."}
- "flag_for_user": Marcar algo que necesita intervencion humana.
  Parametros: {"what": "...", "why": "...", "suggested_action": "..."}
- "rotate_account": Rotar a otra cuenta cuando la actual esta agotada.
  Parametros: {"tool": "chatgpt|claude|codex", "exhausted_email": "...", "reason": "..."}
- "no_action": No hay correccion segura disponible.
  Parametros: {"reason": "..."}

CUOTAS:
- Si una cuenta aparece como AGOTADA, NO la uses para consultas nuevas.
- Si hay otra cuenta disponible para el mismo tool, recomienda rotarla.
- Si TODAS las cuentas de un tool estan agotadas, usa flag_for_user.

POOL DE ASISTENTES:
- Cada cuenta con sesion activa es un "asistente" disponible.
- Al distribuir tareas, prioriza cuentas con mas mensajes restantes.
- Si hay multiples cuentas con sesion en el mismo tool, se pueden
  usar en paralelo para acelerar tareas complejas.
- Si una cuenta se agota, rotar automaticamente a la siguiente disponible.
- El pool se actualiza en tiempo real; consulta estimate_available_workers().

FORMATO DE RESPUESTA:
{
  "reasoning": "explicacion corta de tu analisis",
  "corrections": [
    {"action": "nombre_accion", "params": {...}, "confidence": 0.0-1.0}
  ]
}
"""


def _build_deductive_context(
    findings: list[dict[str, Any]],
    *,
    workspace: str = '',
) -> str:
    """Build a context string for the deductive reasoning engine."""
    parts: list[str] = []

    # Findings
    parts.append('== PROBLEMAS DETECTADOS ==')
    for f in findings:
        parts.append(
            f"- [{f.get('category', '?')}] ocurrencias={f.get('occurrences', 0)} "
            f"titulo={f.get('title', '')} resumen={f.get('summary', '')}"
        )

    # Available tools
    parts.append('\n== HERRAMIENTAS DISPONIBLES ==')
    try:
        from iabv_v15.services.tools.tool_registry import ToolRegistry
        registry = ToolRegistry(workspace_root=workspace or '.')
        cards = registry.list_cards()
        for card in cards[:20]:
            parts.append(f"- {card.tool_id}: available={card.available}")
    except Exception:
        parts.append('- (no se pudo leer ToolRegistry)')

    # Browser accounts
    parts.append('\n== CUENTAS DE NAVEGADOR DEL USUARIO ==')
    try:
        from iabv_v15.services.account_resource_scanner import scan_browser_accounts
        browser = scan_browser_accounts()
        if browser.get('count', 0) > 0:
            for acc in browser.get('accounts', [])[:10]:
                parts.append(
                    f"- {acc.get('browser', '?')}: {acc.get('email', '?')} "
                    f"(perfil: {acc.get('profile', '?')})"
                )
        else:
            parts.append('- Ninguna cuenta detectada')
    except Exception:
        parts.append('- (scanner no disponible)')

    # Active browser sessions (cookies per tool domain)
    parts.append('\n== SESIONES ACTIVAS EN NAVEGADOR (cookies) ==')
    try:
        from iabv_v15.services.account_resource_scanner import scan_browser_sessions
        sess = scan_browser_sessions()
        if sess.get('session_count', 0) > 0:
            for tool, tool_sessions in sess.get('by_tool', {}).items():
                for s in tool_sessions:
                    parts.append(
                        f"- {s.get('tool', '?').upper()} en {s.get('browser', '?')} "
                        f"{s.get('profile', '?')}: {s.get('cookie_count', 0)} cookies "
                        f"({s.get('domain', '?')})"
                    )
        else:
            parts.append('- Ninguna sesion activa detectada')
    except Exception:
        parts.append('- (scanner de sesiones no disponible)')

    # API status
    parts.append('\n== ESTADO DE APIs ==')
    try:
        from iabv_v15.services.account_resource_scanner import (
            scan_ollama_api,
            scan_devin_api,
            scan_github_api,
        )
        ollama = scan_ollama_api()
        parts.append(f"- Ollama: {'disponible' if ollama.get('available') else 'no disponible'}")
        if ollama.get('available'):
            models = ollama.get('models', [])
            parts.append(f"  Modelos: {', '.join(m.get('name', '?') for m in models[:5])}")
        devin = scan_devin_api()
        parts.append(f"- Devin API: {'disponible' if devin.get('available') else 'no disponible'}")
        github = scan_github_api()
        parts.append(f"- GitHub API: {'disponible' if github.get('available') else 'no disponible'}")
    except Exception:
        parts.append('- (no se pudo leer estado de APIs)')

    # Quota status per account+tool
    parts.append('\n== CUOTAS POR CUENTA ==')
    try:
        from iabv_v15.services.account_resource_scanner import get_all_quota_status
        qs = get_all_quota_status()
        if qs['total_tracked'] == 0:
            parts.append('- Sin cuentas rastreadas todavia.')
        else:
            for s in qs['statuses']:
                status_tag = 'AGOTADA' if s['exhausted'] else 'OK'
                parts.append(
                    f"- [{status_tag}] {s['tool']}:{s['email']} — "
                    f"{s['used_in_window']}/{s['limit']} msgs "
                    f"(ventana {s['window_hours']}h)"
                )
                if s['exhausted'] and s.get('resets_at'):
                    parts.append(f"  Se reactiva: {s['resets_at']}")
            parts.append(
                f"Resumen: {qs['available_count']} disponibles, "
                f"{qs['exhausted_count']} agotadas"
            )
    except Exception:
        parts.append('- (no se pudo leer estado de cuotas)')

    # Worker pool: accounts with active sessions + remaining messages
    parts.append('\n== POOL DE ASISTENTES ==')
    try:
        from iabv_v15.services.account_resource_scanner import estimate_available_workers
        pool = estimate_available_workers()
        if pool['available_count'] == 0 and pool['exhausted_count'] == 0:
            parts.append('- Sin asistentes con sesion activa detectados.')
        else:
            for w in pool.get('workers', []):
                parts.append(
                    f"- [DISPONIBLE] {w['tool']}:{w['email']} — "
                    f"{w['remaining_messages']}/{w['limit']} msgs"
                )
            for w in pool.get('exhausted', []):
                reset = f" (reactiva: {w['resets_at']})" if w.get('resets_at') else ''
                parts.append(
                    f"- [AGOTADO] {w['tool']}:{w['email']}{reset}"
                )
            parts.append(
                f"Total: {pool['available_count']} disponibles, "
                f"{pool['exhausted_count']} agotados, "
                f"{pool['total_remaining_messages']} msgs restantes"
            )
    except Exception:
        parts.append('- (no se pudo leer pool de asistentes)')

    return '\n'.join(parts)


def _query_ollama_for_deduction(context: str) -> dict[str, Any] | None:
    """Ask Ollama to reason about findings and propose corrections."""
    return _query_ollama_for_reasoning(context, _DEDUCTIVE_SYSTEM_PROMPT)


# Executors for deduced corrections — these actually carry out the actions.

def _execute_switch_to_cdp(params: dict[str, Any]) -> dict[str, Any]:
    """Set environment flag to prefer CDP over isolated sessions."""
    target = params.get('target_tool', 'all')
    os.environ['IABV_PREFER_CDP_SESSION'] = '1'
    logger.info(
        'deductive-correction: switched to CDP mode for %s — '
        'will reuse user browser sessions instead of isolated contexts',
        target,
    )
    return {
        'action': 'switch_to_cdp',
        'status': 'corrected',
        'detail': f'CDP mode activated for {target}. '
                  f'IABV_PREFER_CDP_SESSION=1 set in environment.',
    }


def _execute_suppress_logger(params: dict[str, Any]) -> dict[str, Any]:
    """Suppress a noisy logger."""
    import logging as _logging
    logger_name = params.get('logger_name', '')
    level_name = params.get('level', 'WARNING')
    level = getattr(_logging, level_name.upper(), _logging.WARNING)
    if logger_name:
        _logging.getLogger(logger_name).setLevel(level)
        logger.info('deductive-correction: suppressed %s to %s', logger_name, level_name)
        return {
            'action': 'suppress_logger',
            'status': 'corrected',
            'detail': f'{logger_name} → {level_name}',
        }
    return {'action': 'suppress_logger', 'status': 'no_action_needed', 'detail': 'no logger name'}


def _execute_bump_cache_ttl(params: dict[str, Any]) -> dict[str, Any]:
    """Bump a cache TTL to reduce re-scanning noise."""
    cache_name = params.get('cache_name', 'multi_source_cache')
    new_ttl = params.get('new_ttl', 300)
    try:
        from iabv_v15.services.tools.tool_adapters import ExternalAssistantWebToolAdapter
        if hasattr(ExternalAssistantWebToolAdapter, '_multi_source_cache_ttl'):
            old_ttl = ExternalAssistantWebToolAdapter._multi_source_cache_ttl
            ExternalAssistantWebToolAdapter._multi_source_cache_ttl = float(new_ttl)
            logger.info(
                'deductive-correction: bumped %s TTL %s → %s',
                cache_name, old_ttl, new_ttl,
            )
            return {
                'action': 'bump_cache_ttl',
                'status': 'corrected',
                'detail': f'{cache_name} TTL {old_ttl}→{new_ttl}s',
            }
    except Exception as exc:
        return {'action': 'bump_cache_ttl', 'status': 'failed', 'detail': str(exc)}
    return {'action': 'bump_cache_ttl', 'status': 'no_action_needed', 'detail': 'target not found'}


def _execute_recommend_adapter(params: dict[str, Any]) -> dict[str, Any]:
    """Log a recommendation for a missing adapter (informational)."""
    recommendation = params.get('recommendation', '')
    phase = params.get('phase', '?')
    logger.info(
        'deductive-correction: adapter recommendation for phase %s — %s',
        phase, recommendation,
    )
    return {
        'action': 'recommend_adapter',
        'status': 'corrected',
        'detail': f'Phase {phase}: {recommendation}',
    }


def _execute_flag_for_user(params: dict[str, Any]) -> dict[str, Any]:
    """Flag something that needs human intervention."""
    what = params.get('what', '?')
    why = params.get('why', '')
    logger.info('deductive-correction: flagged for user — %s: %s', what, why)
    return {
        'action': 'flag_for_user',
        'status': 'needs_user',
        'detail': f'{what}: {why}',
        'user_action': params.get('suggested_action', ''),
    }


def _execute_rotate_account(params: dict[str, Any]) -> dict[str, Any]:
    tool = params.get('tool', '?')
    exhausted = params.get('exhausted_email', '?')
    reason = params.get('reason', '')
    try:
        from iabv_v15.services.account_resource_scanner import best_account_for_tool
        alt = best_account_for_tool(tool)
        if alt:
            logger.info(
                'deductive-correction: rotating %s from %s to %s — %s',
                tool, exhausted, alt['email'], reason,
            )
            return {
                'action': 'rotate_account',
                'status': 'corrected',
                'detail': f'{tool}: rotated from {exhausted} to {alt["email"]} ({alt["remaining"]} msgs left)',
            }
        logger.warning('deductive-correction: all accounts exhausted for %s', tool)
        return {
            'action': 'rotate_account',
            'status': 'needs_user',
            'detail': f'{tool}: all accounts exhausted, no alternative available',
        }
    except Exception as exc:
        return {'action': 'rotate_account', 'status': 'error', 'detail': str(exc)}


_DEDUCTIVE_EXECUTORS: dict[str, Any] = {
    'switch_to_cdp': _execute_switch_to_cdp,
    'create_dedicated_thread': lambda p: {
        'action': 'create_dedicated_thread', 'status': 'corrected',
        'detail': f"Thread recommendation for {p.get('assistant_kind', '?')}: {p.get('reason', '')}",
    },
    'suppress_logger': _execute_suppress_logger,
    'bump_cache_ttl': _execute_bump_cache_ttl,
    'recommend_adapter': _execute_recommend_adapter,
    'flag_for_user': _execute_flag_for_user,
    'rotate_account': _execute_rotate_account,
    'no_action': lambda p: {
        'action': 'no_action', 'status': 'no_action_needed',
        'detail': p.get('reason', 'no safe correction available'),
    },
}


def apply_deductive_corrections(
    findings: list[dict[str, Any]],
    *,
    workspace: str = '',
) -> dict[str, Any]:
    """Use Ollama to reason about findings and execute deduced corrections.

    This is the general-purpose reasoning engine. Instead of matching
    each problem to a hardcoded handler, it:
    1. Builds context from findings + available tools/accounts/APIs
    2. Asks Ollama to analyze and propose corrections
    3. Executes the proposed corrections via safe executors

    Falls back to the pattern-based handlers if Ollama is unavailable.
    """
    # Build context for the LLM
    context = _build_deductive_context(findings, workspace=workspace)

    # Query Ollama
    deduction = _query_ollama_for_deduction(context)

    corrections: list[dict[str, Any]] = []
    reasoning = ''

    if deduction is not None:
        reasoning = deduction.get('reasoning', '')
        if reasoning:
            logger.info('deductive-reasoning: %s', reasoning[:200])

        for correction in deduction.get('corrections', []):
            action = correction.get('action', '')
            params = correction.get('params', {})
            confidence = correction.get('confidence', 0.0)

            # Only execute corrections with confidence >= 0.6
            if confidence < 0.6:
                logger.debug(
                    'deductive-reasoning: skipped %s (confidence=%.2f < 0.6)',
                    action, confidence,
                )
                continue

            executor = _DEDUCTIVE_EXECUTORS.get(action)
            if executor is not None:
                try:
                    result = executor(params)
                    result['confidence'] = confidence
                    result['reasoning'] = reasoning
                    corrections.append(result)
                except Exception as exc:
                    logger.debug('deductive executor %s failed: %s', action, exc)
            else:
                logger.debug('deductive-reasoning: unknown action %s', action)

    return {
        'deductive_reasoning': reasoning,
        'corrections_applied': corrections,
        'corrections_count': len(corrections),
        'ollama_available': deduction is not None,
    }


# ──────────────────────────────────────────────────────────────
# Intelligent Tool Verification — deep audit of real access to each tool
#
# When the program detects a multi_source_disagreement (e.g. codex:
# filesystem=yes, process=no, window=no), it now goes DEEPER:
# - Checks session state files (sqlite, rollouts)
# - Scans browser accounts for web-based alternatives
# - Queries CLI availability
# - Asks Ollama to reason about the best configuration
#
# The program does this ITSELF — no human programming for each tool.
# ──────────────────────────────────────────────────────────────

_TOOL_VERIFICATION_PROMPT = """\
Eres el verificador inteligente de herramientas de IABV v1.5.
Recibes un informe detallado del estado real de una herramienta
(archivos, procesos, sesiones, rutas, cuentas del navegador) y
debes deducir:
1. Si la herramienta realmente esta disponible y en que modo.
2. Cual es la MEJOR configuracion para usarla dado el estado actual.
3. Que acciones tomar para mejorar el acceso.

REGLAS:
- Responde SOLO en JSON valido.
- Basa tus conclusiones SOLO en la evidencia provista, no inventes.
- Si hay sesiones activas en el navegador del usuario, prefiere CDP.
- Si el ejecutable existe pero no esta corriendo, puede lanzarse.
- Si hay datos de sesion (sqlite, rollouts), la herramienta fue usada.

FORMATO DE RESPUESTA:
{
  "tool_id": "nombre",
  "truly_available": true/false,
  "best_mode": "desktop_app|codex_rollout|web_assisted|cdp_shared|cli",
  "reasoning": "explicacion corta",
  "configuration": {
    "launch_mode": "...",
    "response_capture_mode": "...",
    "use_browser_session": true/false,
    "additional_params": {}
  },
  "actions": [
    {"action": "nombre_accion", "params": {...}, "confidence": 0.0-1.0}
  ]
}
"""


def _deep_tool_probe(tool_id: str, *, workspace: str = '') -> dict[str, Any]:
    """Gather deep diagnostic info about a tool's real state.

    Goes beyond the 3-source check (filesystem/process/window) to inspect:
    - Session state files and their age
    - Rollout directories and recent sessions
    - CLI availability and version
    - Browser accounts with active sessions for web alternatives
    - Environment variables that affect the tool
    """
    import glob as _glob
    import time as _time

    info: dict[str, Any] = {
        'tool_id': tool_id,
        'timestamp': _time.time(),
    }

    # Determine assistant_kind from tool_id
    assistant_kind = tool_id.replace('_installed', '').replace('_web_assisted', '')
    info['assistant_kind'] = assistant_kind

    # 1. ToolRegistry card info
    try:
        from iabv_v15.services.tools.tool_registry import ToolRegistry
        registry = ToolRegistry(workspace_root=workspace or '.')
        card = registry.get_card(tool_id)
        if card:
            info['card'] = {
                'title': card.title,
                'adapter_key': card.adapter_key,
                'launch_mode': card.metadata.get('launch_mode', ''),
                'response_capture_mode': card.metadata.get('response_capture_mode', ''),
                'background_capture_mode': card.metadata.get('background_capture_mode', ''),
                'web_url': card.metadata.get('web_url', ''),
                'command_name': card.metadata.get('command_name', ''),
                'command_aliases': card.metadata.get('command_aliases', []),
                'windows_default_paths': card.metadata.get('windows_default_paths', []),
                'session_state_path': card.metadata.get('session_state_path', ''),
                'session_rollouts_root': card.metadata.get('session_rollouts_root', ''),
                'window_title_hints': card.metadata.get('window_title_hints', []),
            }
    except Exception:
        info['card'] = None

    # 2. Filesystem check — resolve all possible executable paths
    resolved_paths: list[dict[str, Any]] = []
    try:
        import shutil as _shutil
        cmd_name = (info.get('card') or {}).get('command_name', assistant_kind)
        which_result = _shutil.which(cmd_name)
        if which_result:
            resolved_paths.append({'source': 'which', 'path': which_result, 'exists': True})

        for alias in (info.get('card') or {}).get('command_aliases', []):
            alias_result = _shutil.which(alias)
            if alias_result:
                resolved_paths.append({'source': f'which({alias})', 'path': alias_result, 'exists': True})

        for pattern in (info.get('card') or {}).get('windows_default_paths', []):
            expanded = pattern
            for token, env_var in [
                ('{localappdata}', 'LOCALAPPDATA'),
                ('{programfiles}', 'ProgramFiles'),
                ('{userprofile}', 'USERPROFILE'),
            ]:
                expanded = expanded.replace(token, os.environ.get(env_var, ''))
            expanded = expanded.replace('\\', os.sep)
            matches = _glob.glob(expanded) if ('*' in expanded or '?' in expanded) else []
            if matches:
                for m in matches:
                    resolved_paths.append({'source': 'glob', 'path': m, 'exists': os.path.exists(m)})
            elif os.path.exists(expanded):
                resolved_paths.append({'source': 'direct', 'path': expanded, 'exists': True})
            else:
                resolved_paths.append({'source': 'direct', 'path': expanded, 'exists': False})
    except Exception:
        pass
    info['filesystem'] = {'paths_found': resolved_paths, 'any_exists': any(p['exists'] for p in resolved_paths)}

    # 3. Process check
    try:
        import psutil
        keywords = [assistant_kind]
        keywords.extend((info.get('card') or {}).get('command_aliases', []))
        running_procs: list[dict[str, str]] = []
        for proc in psutil.process_iter(['name', 'exe', 'pid']):
            try:
                name = str(proc.info.get('name') or '').lower()
                exe = str(proc.info.get('exe') or '').lower()
                for kw in keywords:
                    if kw.lower() in name or kw.lower() in exe:
                        running_procs.append({
                            'pid': str(proc.info.get('pid', '')),
                            'name': name,
                            'exe': exe,
                        })
                        break
            except Exception:
                continue
        info['process'] = {'running': running_procs, 'is_running': bool(running_procs)}
    except Exception:
        info['process'] = {'running': [], 'is_running': False}

    # 4. Session state — check sqlite DB and rollout directories
    session_info: dict[str, Any] = {}
    state_path = (info.get('card') or {}).get('session_state_path', '')
    if state_path:
        expanded_state = state_path
        for token, env_var in [('{userprofile}', 'USERPROFILE')]:
            expanded_state = expanded_state.replace(token, os.environ.get(env_var, ''))
        expanded_state = expanded_state.replace('\\', os.sep)
        session_info['state_path'] = expanded_state
        session_info['state_exists'] = os.path.exists(expanded_state)
        if session_info['state_exists']:
            try:
                stat = os.stat(expanded_state)
                session_info['state_size_bytes'] = stat.st_size
                session_info['state_modified_ago_seconds'] = round(_time.time() - stat.st_mtime)
            except Exception:
                pass

    rollouts_root = (info.get('card') or {}).get('session_rollouts_root', '')
    if rollouts_root:
        expanded_rollouts = rollouts_root
        for token, env_var in [('{userprofile}', 'USERPROFILE')]:
            expanded_rollouts = expanded_rollouts.replace(token, os.environ.get(env_var, ''))
        expanded_rollouts = expanded_rollouts.replace('\\', os.sep)
        session_info['rollouts_root'] = expanded_rollouts
        session_info['rollouts_exists'] = os.path.isdir(expanded_rollouts)
        if session_info['rollouts_exists']:
            try:
                rollout_dirs = sorted(Path(expanded_rollouts).iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                session_info['rollout_count'] = len(rollout_dirs)
                if rollout_dirs:
                    newest = rollout_dirs[0]
                    session_info['newest_rollout'] = str(newest.name)
                    session_info['newest_rollout_age_seconds'] = round(_time.time() - newest.stat().st_mtime)
            except Exception:
                pass
    info['session'] = session_info

    # 5. Window titles (only on Windows)
    info['window'] = {'detected': False}
    if os.name == 'nt':
        try:
            import ctypes
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            titles: list[str] = []

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)  # type: ignore[misc]
            def _enum_cb(hwnd: Any, _: Any) -> bool:
                if user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(hwnd, buf, 512)
                    t = buf.value.strip()
                    if t:
                        titles.append(t)
                return True
            user32.EnumWindows(_enum_cb, 0)

            hints = (info.get('card') or {}).get('window_title_hints', [assistant_kind.title()])
            matching = [t for t in titles if any(h.lower() in t.lower() for h in hints)]
            info['window'] = {
                'detected': bool(matching),
                'matching_windows': matching[:5],
                'total_visible': len(titles),
            }
        except Exception:
            pass

    # 6. Browser accounts (for web-based alternatives)
    try:
        from iabv_v15.services.account_resource_scanner import scan_browser_accounts
        browser = scan_browser_accounts()
        info['browser_accounts'] = {
            'count': browser.get('count', 0),
            'accounts': [
                {'email': a.get('email', '?'), 'browser': a.get('browser', '?')}
                for a in browser.get('accounts', [])[:10]
            ],
        }
    except Exception:
        info['browser_accounts'] = {'count': 0, 'accounts': []}

    # 7. Web alternative check
    web_tool_id = f'{assistant_kind}_web_assisted'
    web_url = ''
    try:
        from iabv_v15.services.tools.tool_registry import ToolRegistry
        registry = ToolRegistry(workspace_root=workspace or '.')
        web_card = registry.get_card(web_tool_id)
        if web_card:
            web_url = web_card.metadata.get('web_url', '')
    except Exception:
        pass
    info['web_alternative'] = {
        'tool_id': web_tool_id,
        'web_url': web_url,
        'available': bool(web_url),
    }

    # 8. Environment flags
    info['env_flags'] = {
        'IABV_PREFER_CDP_SESSION': os.environ.get('IABV_PREFER_CDP_SESSION', ''),
        'CODEX_HOME': os.environ.get('CODEX_HOME', ''),
    }

    return info


def verify_tool_access_deductive(
    tool_id: str,
    *,
    workspace: str = '',
) -> dict[str, Any]:
    """Perform an intelligent, deep verification of real access to a tool.

    This function:
    1. Gathers deep diagnostic info (filesystem, process, sessions, browser)
    2. Sends ALL evidence to Ollama for reasoning
    3. Returns Ollama's assessment of best configuration

    The program calls this ITSELF when it detects disagreements — no human
    needs to program the verification logic for each tool.
    """
    probe = _deep_tool_probe(tool_id, workspace=workspace)

    # Build a readable summary for Ollama
    parts: list[str] = [f'== VERIFICACION PROFUNDA: {tool_id} ==']
    parts.append(f"assistant_kind: {probe.get('assistant_kind', '?')}")

    # Card
    card = probe.get('card') or {}
    parts.append(f"\nToolCard: launch_mode={card.get('launch_mode', '?')}, "
                 f"capture={card.get('response_capture_mode', '?')}, "
                 f"background={card.get('background_capture_mode', '?')}")
    if card.get('web_url'):
        parts.append(f"  web_url: {card['web_url']}")

    # Filesystem
    fs = probe.get('filesystem', {})
    parts.append(f"\nFilesystem: any_exists={fs.get('any_exists', False)}")
    for p in fs.get('paths_found', []):
        parts.append(f"  [{p['source']}] {p['path']} exists={p['exists']}")

    # Process
    proc = probe.get('process', {})
    parts.append(f"\nProcess: is_running={proc.get('is_running', False)}")
    for p in proc.get('running', []):
        parts.append(f"  PID={p['pid']} name={p['name']}")

    # Session
    sess = probe.get('session', {})
    if sess.get('state_exists'):
        parts.append(f"\nSession DB: {sess['state_path']} "
                     f"(size={sess.get('state_size_bytes', '?')}B, "
                     f"modified {sess.get('state_modified_ago_seconds', '?')}s ago)")
    else:
        parts.append(f"\nSession DB: {sess.get('state_path', 'none')} — no existe")
    if sess.get('rollouts_exists'):
        parts.append(f"Rollouts: {sess.get('rollout_count', 0)} sesiones, "
                     f"mas reciente: {sess.get('newest_rollout', '?')} "
                     f"({sess.get('newest_rollout_age_seconds', '?')}s ago)")

    # Window
    win = probe.get('window', {})
    parts.append(f"\nWindow: detected={win.get('detected', False)}")
    for w in win.get('matching_windows', []):
        parts.append(f"  '{w}'")

    # Browser accounts
    ba = probe.get('browser_accounts', {})
    parts.append(f"\nBrowser accounts: {ba.get('count', 0)}")
    for a in ba.get('accounts', []):
        parts.append(f"  {a.get('browser', '?')}: {a.get('email', '?')}")

    # Web alternative
    web = probe.get('web_alternative', {})
    parts.append(f"\nWeb alternative: {web.get('tool_id', '?')} "
                 f"available={web.get('available', False)} url={web.get('web_url', '')}")

    # Env flags
    env = probe.get('env_flags', {})
    parts.append(f"\nEnvironment: CDP_PREFER={env.get('IABV_PREFER_CDP_SESSION', 'unset')}")

    context = '\n'.join(parts)

    # Query Ollama
    deduction = _query_ollama_for_reasoning(context, _TOOL_VERIFICATION_PROMPT)

    result: dict[str, Any] = {
        'tool_id': tool_id,
        'probe': probe,
        'ollama_available': deduction is not None,
    }

    if deduction:
        result['truly_available'] = deduction.get('truly_available', False)
        result['best_mode'] = deduction.get('best_mode', 'unknown')
        result['reasoning'] = deduction.get('reasoning', '')
        result['configuration'] = deduction.get('configuration', {})
        result['actions'] = deduction.get('actions', [])

        logger.info(
            'tool-verification[%s]: truly_available=%s, best_mode=%s — %s',
            tool_id,
            result['truly_available'],
            result['best_mode'],
            result.get('reasoning', '')[:200],
        )

        # Execute any deduced actions
        for action_item in deduction.get('actions', []):
            action = action_item.get('action', '')
            params = action_item.get('params', {})
            confidence = action_item.get('confidence', 0.0)
            if confidence >= 0.6:
                executor = _DEDUCTIVE_EXECUTORS.get(action)
                if executor:
                    try:
                        exec_result = executor(params)
                        result.setdefault('corrections_applied', []).append(exec_result)
                    except Exception as exc:
                        logger.debug('tool-verification executor %s failed: %s', action, exc)
    else:
        result['truly_available'] = probe.get('filesystem', {}).get('any_exists', False)
        result['best_mode'] = 'unknown'
        result['reasoning'] = 'Ollama no disponible — usando resultado de filesystem'

    return result


def _record_cloud_api_health(provider_id: str, status_code: int) -> None:
    """Record HTTP status from cloud API calls for token health tracking.

    Feeds into CommonSenseEngine to detect expired/revoked tokens.
    Delegates to CloudReasoningPlannerService._record_api_health.
    """
    try:
        from iabv_v15.services.adaptive.cloud_reasoning_planner import (
            CloudReasoningPlannerService,
        )
        CloudReasoningPlannerService._record_api_health(provider_id, status_code)
    except ImportError:
        pass


def _query_cloud_reasoning(context: str, system_prompt: str) -> dict[str, Any] | None:
    """Fix 60: try cloud reasoning models (Gemini, Groq) before falling back
    to local Ollama.  The best available model is used for metacognition,
    planning and deductive reasoning.  Results are saved so the local model
    can learn from better answers over time."""
    import json as _json
    import re as _re

    try:
        import httpx
    except ImportError:
        return None

    messages_openai = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': context},
    ]

    # --- Gemini (Google AI Studio, OpenAI-compat endpoint) ---
    gemini_key = os.environ.get('GEMINI_API_KEY', '')
    if gemini_key:
        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.post(
                    'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                    json={
                        'model': 'gemini-2.0-flash',
                        'messages': messages_openai,
                        'temperature': 0.2,
                    },
                    headers={
                        'Authorization': f'Bearer {gemini_key}',
                        'Content-Type': 'application/json',
                    },
                )
                _record_cloud_api_health('gemini', resp.status_code)
                resp.raise_for_status()
                data = resp.json()
            raw = data['choices'][0]['message']['content'].strip()
            raw = _re.sub(r'<think>.*?</think>', '', raw, flags=_re.DOTALL).strip()
            match = _re.search(r'\{[\s\S]*\}', raw)
            if match:
                result = _json.loads(match.group())
                result['_cloud_source'] = 'gemini'
                logger.info('cloud-reasoning: Gemini responded successfully')
                _save_cloud_reasoning_example(context, result)
                return result
        except Exception as exc:
            logger.debug('gemini reasoning failed: %s', exc)

    # --- Groq (OpenAI-compat endpoint, Llama 3.3 70B) ---
    groq_key = os.environ.get('GROQ_API_KEY', '')
    if groq_key:
        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    json={
                        'model': 'llama-3.3-70b-versatile',
                        'messages': messages_openai,
                        'temperature': 0.2,
                    },
                    headers={
                        'Authorization': f'Bearer {groq_key}',
                        'Content-Type': 'application/json',
                    },
                )
                _record_cloud_api_health('groq', resp.status_code)
                resp.raise_for_status()
                data = resp.json()
            raw = data['choices'][0]['message']['content'].strip()
            raw = _re.sub(r'<think>.*?</think>', '', raw, flags=_re.DOTALL).strip()
            match = _re.search(r'\{[\s\S]*\}', raw)
            if match:
                result = _json.loads(match.group())
                result['_cloud_source'] = 'groq'
                logger.info('cloud-reasoning: Groq responded successfully')
                _save_cloud_reasoning_example(context, result)
                return result
        except Exception as exc:
            logger.debug('groq reasoning failed: %s', exc)

    return None


def _save_cloud_reasoning_example(context: str, result: dict[str, Any]) -> None:
    """Persist cloud reasoning examples so the local model can learn."""
    import json as _json
    try:
        data_dir = Path(os.environ.get('IABV_DATA_DIR', '')) / 'evolution' / 'cloud_reasoning'
        if not data_dir.exists():
            data_dir = Path.home() / 'IABV_v1.5' / 'data' / 'evolution' / 'cloud_reasoning'
        data_dir.mkdir(parents=True, exist_ok=True)
        log_path = data_dir / 'reasoning_examples.jsonl'
        from datetime import datetime, timezone
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context_hash': hash(context[:200]),
            'source': result.get('_cloud_source', 'cloud'),
            'reasoning': result.get('reasoning', ''),
            'corrections_count': len(result.get('corrections', [])),
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass


def _query_ollama_for_reasoning(context: str, system_prompt: str) -> dict[str, Any] | None:
    """Reasoning query with cloud-first, local-fallback strategy.

    Fix 60: tries Gemini / Groq cloud models first (better reasoning),
    then falls back to local Ollama.  Cloud results are saved so the
    local model can learn from higher-quality answers over time."""
    # Try cloud models first
    cloud_result = _query_cloud_reasoning(context, system_prompt)
    if cloud_result is not None:
        return cloud_result

    # Fallback to local Ollama
    import json as _json

    base_url = os.environ.get('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434/v1')
    model = os.environ.get('IABV_OLLAMA_MODEL', 'qwen3:8b')

    try:
        import httpx
    except ImportError:
        return None

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': context},
    ]
    payload = {
        'model': model,
        'messages': messages,
        'stream': False,
        'temperature': 0.2,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f'{base_url}/chat/completions', json=payload)
            resp.raise_for_status()
            data = resp.json()
        raw_text = data['choices'][0]['message']['content'].strip()

        import re
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            return _json.loads(json_match.group())
        return None
    except Exception as exc:
        logger.debug('ollama reasoning query failed: %s', exc)
        return None


def format_auto_correction_report(result: dict[str, Any]) -> str:
    """Format auto-correction results for the auto-analysis report."""
    lines: list[str] = ['== AUTO-CORRECCION Y DEDUCCION DE HERRAMIENTAS ==']

    # Corrections applied
    corrections = result.get('corrections_applied', [])
    if corrections:
        lines.append(f'  Correcciones automáticas aplicadas: {len(corrections)}')
        for c in corrections:
            lines.append(f'    [CORREGIDO] {c.get("detail", c.get("action", "?"))}')
    else:
        lines.append('  Correcciones automáticas: ninguna necesaria')

    # User requests
    user_reqs = result.get('user_requests', [])
    if user_reqs:
        lines.append(f'  Requiere acción del usuario: {len(user_reqs)}')
        for req in user_reqs[:8]:
            what = req.get('what', req.get('detail', req.get('action', '?')))
            action = req.get('user_action', '')
            lines.append(f'    [NECESITA USUARIO] {what}')
            if action:
                lines.append(f'      → {action}')
    else:
        lines.append('  No se requiere acción del usuario')

    # Tool deduction summary
    td = result.get('tool_deduction', {})
    auto_count = td.get('auto_fixable_count', 0)
    user_count = td.get('needs_user_count', 0)
    if auto_count + user_count > 0:
        lines.append(f'  Herramientas faltantes: {auto_count} auto-instalables, {user_count} requieren usuario')
    else:
        lines.append('  Herramientas: todas las necesarias están disponibles')

    # Backlog tasks created
    bt_count = result.get('backlog_tasks_count', 0)
    if bt_count > 0:
        lines.append(f'  Tareas creadas en backlog: {bt_count}')

    return '\n'.join(lines)
