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

import logging
import os
import subprocess
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


def _generate_secret_request(deduction: dict[str, str],
                             context: dict[str, Any]) -> dict[str, Any]:
    """Generate request for missing secrets/credentials."""
    account_scan = context.get('account_scan', {})
    secrets = account_scan.get('secrets', {})
    missing = secrets.get('missing', [])

    if not missing:
        return {
            'action': 'request_secrets',
            'status': 'no_action_needed',
            'detail': 'Todos los secretos están configurados',
        }

    instructions: list[dict[str, str]] = []
    for name in missing:
        instr: dict[str, str] = {'name': name, 'how_to_get': ''}
        if 'GITHUB' in name:
            instr['how_to_get'] = 'https://github.com/settings/tokens/new — scope: repo'
        elif 'DEVIN' in name:
            instr['how_to_get'] = 'https://app.devin.ai/settings — API Keys section'
        elif 'OPENAI' in name:
            instr['how_to_get'] = 'https://platform.openai.com/api-keys'
        elif 'ANTHROPIC' in name:
            instr['how_to_get'] = 'https://console.anthropic.com/settings/keys'
        elif 'CLOUDFLARE' in name:
            instr['how_to_get'] = 'https://dash.cloudflare.com/ — Zero Trust > Tunnels'
        else:
            instr['how_to_get'] = f'Configurar en ~/.iabv_secrets.ps1: $env:{name}="valor"'
        instructions.append(instr)

    return {
        'action': 'request_secrets',
        'status': 'needs_user',
        'missing_secrets': instructions,
        'count': len(instructions),
        'user_action': (
            'Agregar los secretos faltantes a ~/.iabv_secrets.ps1 '
            'o configurarlos como variables de entorno'
        ),
    }


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

    # Run common sense reasoning engine — causal inference over all facts
    common_sense_result: dict[str, Any] = {}
    try:
        from iabv_v15.services.common_sense_engine import run_common_sense_reasoning
        common_sense_result = run_common_sense_reasoning(
            gpu_scan=gpu_scan,
            account_scan=account_scan,
            holistic_scan=holistic_scan,
            limits_scan=limits_scan,
            regression_scan=regression_scan,
        )
        # Merge common sense corrections into our corrections
        for cs_action in common_sense_result.get('actions_executed', []):
            cs_result = cs_action.get('result', {})
            if cs_result.get('executed'):
                corrections_applied.append({
                    'action': cs_action.get('action', 'common_sense'),
                    'status': 'corrected',
                    'detail': f'[Sentido Común] {cs_action.get("description", "")} — {cs_result.get("detail", "")}',
                })
        for cs_need in common_sense_result.get('actions_needs_user', []):
            user_requests.append({
                'action': cs_need.get('action', 'common_sense'),
                'status': 'needs_user',
                'detail': cs_need.get('description', ''),
                'user_action': 'Requiere aprobación del usuario',
            })
    except Exception as exc:
        logger.debug('common_sense_reasoning failed: %s', exc)

    return {
        'corrections_applied': corrections_applied,
        'corrections_count': len(corrections_applied),
        'user_requests': user_requests,
        'user_requests_count': len(user_requests),
        'tool_deduction': tool_deduction,
        'backlog_tasks_created': backlog_tasks_created,
        'backlog_tasks_count': len(backlog_tasks_created),
        'common_sense': common_sense_result,
    }


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
