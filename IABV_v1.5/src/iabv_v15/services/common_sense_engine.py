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

import logging
import os
import subprocess
import time
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

    return facts


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
    'start_tunnel': _exec_noop,
    'offload_to_gpu': _exec_noop,
    'parallelize_startup_checks': _exec_noop,
    'move_to_primary': _exec_noop,
}


def act_on_conclusions(
    chain_result: dict[str, Any],
    *,
    execute_safe: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute actions for fired rules. Only executes safe actions by default.

    Args:
        chain_result: Output from forward_chain()
        execute_safe: If True, auto-execute safe actions
        dry_run: If True, report what would be done without executing
    """
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    needs_user: list[dict[str, Any]] = []

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
            })
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

def _register_with_experiment_lab(result: dict[str, Any]) -> None:
    """Register reasoning results with ExperimentLab for strategy comparison.

    This allows ExperimentLab to track how well the common sense engine
    performs over time, comparing different rule sets and inference
    strategies. The experiment domain is INFERENCE_BENCHMARK.
    """
    try:
        from iabv_v15.services.lab.experiment_lab import ExperimentLab
        from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
        from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
        from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
        from iabv_v15.services.lab.strategy_selector import StrategySelector
        from iabv_v15.domain.models import ExperimentDomain, EvaluationRoute

        repo = ExperimentLabRepository()
        lab = ExperimentLab(
            repository=repo,
            registry=AlgorithmBenchmarkRegistry(),
            scoring_engine=DecisionScoringEngine(),
            strategy_selector=StrategySelector(),
        )

        # Calculate reasoning quality metrics
        fact_count = result.get('fact_count', 0)
        conclusion_count = result.get('conclusion_count', 0)
        executed_count = result.get('actions_executed_count', 0)
        elapsed_ms = result.get('elapsed_ms', 0)

        # Precision: ratio of executed actions that succeeded
        executed = result.get('actions_executed', [])
        success_count = sum(1 for a in executed if a.get('result', {}).get('executed'))
        precision = success_count / max(executed_count, 1) if executed_count > 0 else (
            1.0 if conclusion_count == 0 else 0.5
        )

        # Robustness: ability to derive conclusions from facts
        robustness = min(conclusion_count / max(fact_count * 0.3, 1), 1.0) if fact_count > 0 else 0.0

        lab.record_outcome(
            domain=ExperimentDomain.INFERENCE_BENCHMARK,
            objective='common_sense_reasoning_quality',
            subject_key='common_sense_engine_v1',
            route=EvaluationRoute.LOCAL,
            candidate_label='forward_chain_v1',
            success=executed_count > 0 or conclusion_count == 0,
            observed_summary=(
                f'{fact_count} hechos → {conclusion_count} conclusiones → '
                f'{executed_count} acciones en {elapsed_ms}ms'
            ),
            precision=precision,
            robustness=robustness,
            execution_ms=elapsed_ms,
            metadata={
                'fact_count': fact_count,
                'conclusion_count': conclusion_count,
                'fired_rule_count': result.get('fired_rule_count', 0),
                'actions_executed_count': executed_count,
                'actions_needs_user_count': result.get('actions_needs_user_count', 0),
                'inference_iterations': result.get('inference_iterations', 0),
                'comparison_scope_key': 'metacognition_reasoning',
                'assistant_kind': 'common_sense_engine',
            },
        )
        logger.debug('common_sense: registered with ExperimentLab (precision=%.2f, robustness=%.2f)',
                      precision, robustness)
    except Exception as exc:
        logger.debug('common_sense: ExperimentLab registration failed: %s', exc)


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
    """Full common sense reasoning pipeline: observe → infer → act.

    1. Extract facts from all scans
    2. Run forward chaining to derive conclusions
    3. Execute safe actions based on conclusions
    4. Return complete reasoning trace for ExperimentLab
    """
    start = time.monotonic()

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

    chain = forward_chain(facts)

    actions = act_on_conclusions(chain, execute_safe=execute, dry_run=dry_run)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    result = {
        'facts': chain['initial_facts'],
        'fact_count': chain['initial_fact_count'],
        'conclusions': chain['conclusions'],
        'conclusion_count': chain['conclusion_count'],
        'fired_rules': chain['fired_rules'],
        'fired_rule_count': chain['fired_rule_count'],
        'inference_iterations': chain['iterations'],
        'actions_executed': actions['executed'],
        'actions_executed_count': actions['executed_count'],
        'actions_skipped': actions['skipped'],
        'actions_needs_user': actions['needs_user'],
        'actions_needs_user_count': actions['needs_user_count'],
        'elapsed_ms': elapsed_ms,
    }

    # Register with ExperimentLab for strategy comparison
    _register_with_experiment_lab(result)

    return result


# ──────────────────────────────────────────────────────────────
# Format Report
# ──────────────────────────────────────────────────────────────

def format_common_sense_report(result: dict[str, Any]) -> str:
    """Format common sense reasoning results for auto-analysis."""
    lines: list[str] = ['== RAZONAMIENTO AUTONOMO (SENTIDO COMUN) ==']
    lines.append(f'  Hechos observados: {result.get("fact_count", 0)}')
    lines.append(f'  Reglas activadas: {result.get("fired_rule_count", 0)}')
    lines.append(f'  Conclusiones deducidas: {result.get("conclusion_count", 0)}')

    # Show fired rules with causal chain
    for rule in result.get('fired_rules', []):
        severity = rule.get('severity', 'info').upper()
        lines.append(f'  [{severity}] {rule.get("description", rule["id"])}')
        lines.append(f'    Premisas: {", ".join(rule.get("premises_matched", []))}')
        lines.append(f'    → Conclusión: {rule.get("conclusion", "?")}')

    # Actions executed
    executed = result.get('actions_executed', [])
    if executed:
        lines.append(f'  Acciones ejecutadas: {len(executed)}')
        for a in executed:
            status = a.get('result', {})
            if status.get('executed'):
                lines.append(f'    [EJECUTADO] {a.get("description", a["action"])} ({a.get("elapsed_ms", 0)}ms)')
                detail = status.get('detail', '')
                if detail:
                    lines.append(f'      → {detail}')
            else:
                lines.append(f'    [FALLÓ] {a.get("description", a["action"])}')
                lines.append(f'      → {status.get("error", status.get("detail", "?"))}')
    else:
        lines.append('  Acciones ejecutadas: ninguna necesaria')

    # Needs user
    needs_user = result.get('actions_needs_user', [])
    if needs_user:
        lines.append(f'  Requiere usuario: {len(needs_user)}')
        for n in needs_user:
            lines.append(f'    [NECESITA APROBACION] {n.get("description", n["action"])}')

    lines.append(f'  Tiempo de razonamiento: {result.get("elapsed_ms", 0)}ms')

    return '\n'.join(lines)
