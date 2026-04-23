"""Efficiency audit mixin — Tarea 3 findings para OSES.

Este modulo contiene las funciones de findings de eficiencia que se
integran en ``OperationalSelfExaminationService`` via monkey-patch
en bootstrap.py (o merge directo).

Nuevos findings:
- ``tool_efficiency``: benchmark por IA, compara latencia/success/score
- ``needs_custom_model``: detecta tareas donde TODAS las IAs fallan
- ``account_exhaustion``: cuando una cuenta esta a punto de agotarse
- ``external_tool_misdiagnosis``: cuando un fallo se atribuyo mal
  (ej: 403 del proxy de Devin atribuido a permisos del usuario)
- ``heuristic_perturbation``: cuando se detecto fijacion cognitiva
  y se forzó perturbacion en 1 de cada 5 requests

Contratos respetados:
- Son metodos read-only que retornan ``list[SelfExaminationFinding]``
- No disparan acciones, no deciden rutas
- Se complementan con findings existentes (no reemplazan)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any, TYPE_CHECKING

from iabv_v15.domain.models import (
    ExperimentRun,
    IssueSeverity,
    SelfExaminationFinding,
    utc_now,
)

if TYPE_CHECKING:
    from iabv_v15.services.evolution.account_ledger_service import AccountLedgerService
    from iabv_v15.services.evolution.system_backlog_service import SystemBacklogService


def tool_efficiency_findings(
    experiment_runs: list[Any],
    *,
    min_runs_per_ia: int = 3,
) -> list[SelfExaminationFinding]:
    """3.1 — Benchmark de eficiencia por IA.

    Mide: latencia promedio, tasa de exito, calidad de respuesta (score),
    costo (mensajes consumidos). Compara IAs en tareas equivalentes
    (mismo subject_key). Genera finding cuando una IA rinde significativamente
    peor que otra en la misma categoria.
    """
    findings: list[SelfExaminationFinding] = []

    # Agrupar runs por scope_key + IA
    by_scope: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
    for run in experiment_runs:
        scope = _get_scope_key(run)
        ia = _get_ia_name(run)
        if scope and ia:
            by_scope[scope][ia].append(run)

    for scope, ia_runs in by_scope.items():
        if len(ia_runs) < 2:
            continue

        ia_stats: dict[str, dict[str, float]] = {}
        for ia, runs in ia_runs.items():
            if len(runs) < min_runs_per_ia:
                continue
            successes = sum(1 for r in runs if _is_success(r))
            scores = [_get_score(r) for r in runs if _get_score(r) is not None]
            latencies = [_get_latency(r) for r in runs if _get_latency(r) is not None]

            ia_stats[ia] = {
                'success_rate': successes / len(runs) if runs else 0,
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'avg_latency': sum(latencies) / len(latencies) if latencies else 0,
                'total_runs': len(runs),
            }

        if len(ia_stats) < 2:
            continue

        # Encontrar la mejor y peor IA por score compuesto
        ranked = sorted(
            ia_stats.items(),
            key=lambda x: x[1]['success_rate'] * 0.5 + x[1]['avg_score'] * 0.5,
            reverse=True,
        )
        best_ia, best_stats = ranked[0]
        worst_ia, worst_stats = ranked[-1]

        # Solo generar finding si la diferencia es significativa
        score_diff = (
            (best_stats['success_rate'] * 0.5 + best_stats['avg_score'] * 0.5)
            - (worst_stats['success_rate'] * 0.5 + worst_stats['avg_score'] * 0.5)
        )
        if score_diff < 0.15:
            continue

        findings.append(SelfExaminationFinding(
            category='tool_efficiency',
            title=f'{worst_ia} rinde {score_diff:.0%} peor que {best_ia} en {scope}',
            summary=(
                f'En tareas de tipo {scope}, {best_ia} tiene success_rate '
                f'{best_stats["success_rate"]:.0%} y score {best_stats["avg_score"]:.2f}, '
                f'vs {worst_ia} con {worst_stats["success_rate"]:.0%} y '
                f'{worst_stats["avg_score"]:.2f}.'
            ),
            severity=IssueSeverity.MEDIUM if score_diff < 0.3 else IssueSeverity.HIGH,
            confidence=min(0.95, 0.5 + score_diff),
            recommendation=(
                f'Preferir {best_ia} para tareas {scope}. Considerar reducir '
                f'peso de {worst_ia} en AdaptiveWeightLayer.'
            ),
            metadata={
                'scope': scope,
                'best_ia': best_ia,
                'best_stats': best_stats,
                'worst_ia': worst_ia,
                'worst_stats': worst_stats,
                'all_stats': ia_stats,
                'score_difference': round(score_diff, 4),
            },
        ))

    return findings


def needs_custom_model_findings(
    experiment_runs: list[Any],
    *,
    min_runs: int = 5,
    failure_threshold: float = 0.8,
) -> list[SelfExaminationFinding]:
    """3.3 — Detecta tareas donde TODAS las IAs externas fallan.

    Si hay un patron de fallos universales, genera finding observacional
    ``needs_custom_model`` con tipo de tarea, datos de entrenamiento
    disponibles, y recomendacion. NO ejecuta entrenamiento.
    """
    findings: list[SelfExaminationFinding] = []

    # Agrupar por task_kind/scope
    by_scope: dict[str, list[Any]] = defaultdict(list)
    for run in experiment_runs:
        scope = _get_scope_key(run)
        if scope:
            by_scope[scope].append(run)

    for scope, runs in by_scope.items():
        if len(runs) < min_runs:
            continue

        # Verificar si TODAS las IAs fallan
        ia_results: dict[str, list[bool]] = defaultdict(list)
        for run in runs:
            ia = _get_ia_name(run)
            if ia:
                ia_results[ia].append(_is_success(run))

        if len(ia_results) < 2:
            continue

        all_fail = all(
            sum(results) / len(results) < (1 - failure_threshold)
            for results in ia_results.values()
            if results
        )

        if not all_fail:
            continue

        # Contar runs exitosos como posible training data
        successful_runs = [r for r in runs if _is_success(r)]

        findings.append(SelfExaminationFinding(
            category='needs_custom_model',
            title=f'Todas las IAs fallan en {scope} ({len(runs)} runs)',
            summary=(
                f'En {scope}, todas las IAs externas ({", ".join(ia_results.keys())}) '
                f'fallan consistentemente. {len(successful_runs)} runs exitosos '
                f'disponibles como datos de entrenamiento.'
            ),
            severity=IssueSeverity.MEDIUM,
            confidence=min(0.9, 0.4 + len(runs) * 0.05),
            recommendation=(
                f'Considerar fine-tune de modelo local (ollama) para tareas {scope}. '
                f'Hay {len(successful_runs)} examples exitosos disponibles. '
                f'Alternativa: buscar servicio externo especializado.'
            ),
            metadata={
                'scope': scope,
                'total_runs': len(runs),
                'successful_runs': len(successful_runs),
                'ias_tested': list(ia_results.keys()),
                'failure_rates': {
                    ia: round(1 - sum(r) / len(r), 3) if r else 1.0
                    for ia, r in ia_results.items()
                },
                'auto_executable': False,
            },
        ))

    return findings


def account_exhaustion_findings(
    account_ledger: AccountLedgerService | None,
) -> list[SelfExaminationFinding]:
    """Finding cuando una cuenta esta a punto de agotarse."""
    findings: list[SelfExaminationFinding] = []
    if account_ledger is None:
        return findings

    try:
        all_accounts = account_ledger.get_all_accounts()
    except Exception:
        return findings

    providers_seen: set[str] = set()
    for acct in all_accounts:
        if acct.provider in providers_seen:
            continue
        if acct.status == 'disabled':
            continue

        prediction = account_ledger.predict_exhaustion(acct.provider)
        if prediction.get('error') or prediction.get('unlimited'):
            continue

        remaining = prediction.get('messages_remaining', 999)
        hours_left = prediction.get('hours_until_exhaustion')
        should_rotate = prediction.get('should_rotate_soon', False)

        if should_rotate or remaining <= 10:
            providers_seen.add(acct.provider)
            severity = IssueSeverity.HIGH if remaining <= 3 else IssueSeverity.MEDIUM
            findings.append(SelfExaminationFinding(
                category='account_exhaustion',
                title=f'{acct.provider}: {remaining} mensajes restantes',
                summary=(
                    f'La cuenta activa de {acct.provider} ({acct.email}) tiene '
                    f'{remaining} mensajes restantes'
                    + (f', agotamiento estimado en {hours_left:.1f}h' if hours_left else '')
                    + '.'
                ),
                severity=severity,
                confidence=0.9,
                recommendation=(
                    f'Rotar a otra cuenta de {acct.provider} si hay disponible, '
                    f'o cambiar a proveedor local (ollama).'
                ),
                metadata={
                    'provider': acct.provider,
                    'email': acct.email,
                    'prediction': prediction,
                },
            ))

    return findings


def external_tool_misdiagnosis_findings(
    account_ledger: AccountLedgerService | None,
) -> list[SelfExaminationFinding]:
    """Detecta cuando un fallo se atribuyo incorrectamente.

    Ejemplo real: el proxy de Devin (git-manager) devuelve 403 pero
    las credenciales de GitHub son validas. El sistema aprende que el
    problema no es de permisos del usuario sino del intermediario.
    """
    findings: list[SelfExaminationFinding] = []
    if account_ledger is None:
        return findings

    try:
        faults = account_ledger.get_fault_history(hours=168)
    except Exception:
        return findings

    # Agrupar por tipo de fallo
    by_type: dict[str, list[dict]] = defaultdict(list)
    for fault in faults:
        key = f"{fault.get('provider', '')}:{fault.get('fault_type', '')}"
        by_type[key].append(fault)

    for key, fault_list in by_type.items():
        if len(fault_list) < 2:
            continue

        # Contar cuantas veces nuestras credenciales estaban OK pero
        # el servicio externo fallo
        ext_faults = [f for f in fault_list if f.get('external_service_fault')]
        our_creds_ok = [f for f in fault_list if f.get('our_credentials_ok')]

        if len(ext_faults) >= 2 and len(our_creds_ok) >= 2:
            provider, fault_type = key.split(':', 1) if ':' in key else (key, 'unknown')
            findings.append(SelfExaminationFinding(
                category='external_tool_misdiagnosis',
                title=(
                    f'Fallo recurrente en {provider}: {fault_type} '
                    f'(problema del servicio externo, no de nuestros permisos)'
                ),
                summary=(
                    f'{len(ext_faults)} fallos de {provider} donde nuestras '
                    f'credenciales eran validas pero el servicio intermediario fallo. '
                    f'NO pedir al usuario que verifique permisos en estos casos.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    f'Cuando {provider} falle con {fault_type}, intentar ruta alternativa '
                    f'(descarga directa, API alternativa) antes de notificar al usuario. '
                    f'El problema es del intermediario, no de permisos.'
                ),
                metadata={
                    'provider': provider,
                    'fault_type': fault_type,
                    'occurrences': len(fault_list),
                    'external_faults': len(ext_faults),
                    'pattern': 'credentials_ok_but_service_fails',
                },
            ))

    return findings


def heuristic_perturbation_findings(
    experiment_runs: list[Any],
    adaptive_weight_layer: Any | None = None,
) -> list[SelfExaminationFinding]:
    """3.2 — Auto-mejora de heuristicas via perturbacion.

    Si el AdaptiveWeightLayer converge a una combinacion sub-optima
    (detectada por fijacion cognitiva), sugiere perturbacion: forzar
    1 de cada 5 requests a una IA alternativa.
    """
    findings: list[SelfExaminationFinding] = []

    if not adaptive_weight_layer:
        return findings

    # Analizar runs recientes para detectar convergencia
    by_ia: dict[str, list[Any]] = defaultdict(list)
    for run in experiment_runs:
        ia = _get_ia_name(run)
        if ia:
            by_ia[ia].append(run)

    if len(by_ia) < 2:
        return findings

    total_runs = sum(len(r) for r in by_ia.values())
    if total_runs < 10:
        return findings

    # Detectar dominancia
    for ia, runs in by_ia.items():
        share = len(runs) / total_runs
        if share < 0.6:
            continue

        failures = sum(1 for r in runs if not _is_success(r))
        failure_rate = failures / len(runs) if runs else 0

        if failure_rate < 0.3:
            continue

        # IA domina >60% con >30% fallos = fijacion sub-optima
        other_ias = [k for k in by_ia if k != ia]
        findings.append(SelfExaminationFinding(
            category='heuristic_perturbation',
            title=f'{ia} domina {share:.0%} de runs con {failure_rate:.0%} fallos',
            summary=(
                f'{ia} acapara {len(runs)}/{total_runs} runs pero falla '
                f'{failure_rate:.0%} de las veces. Sugiero perturbacion: '
                f'forzar 1 de cada 5 requests a {", ".join(other_ias[:2])} '
                f'para recolectar evidencia fresca.'
            ),
            severity=IssueSeverity.MEDIUM,
            confidence=0.75,
            recommendation=(
                f'Aplicar perturbacion: redirigir 20% de requests de {ia} '
                f'a IAs alternativas ({", ".join(other_ias[:2])}). '
                f'Si la perturbacion mejora el score, ajustar pesos permanentemente.'
            ),
            metadata={
                'dominant_ia': ia,
                'dominance_share': round(share, 3),
                'failure_rate': round(failure_rate, 3),
                'total_runs': total_runs,
                'alternative_ias': other_ias,
                'perturbation_rate': 0.2,
            },
        ))

    return findings


# -----------------------------------------------------------------------
# Helpers para extraer datos de experiment runs
# -----------------------------------------------------------------------

def _get_scope_key(run: Any) -> str:
    if isinstance(run, dict):
        return str(run.get('comparison_scope_key', run.get('scope_key', run.get('subject_key', ''))))
    return str(getattr(run, 'comparison_scope_key', getattr(run, 'scope_key', getattr(run, 'subject_key', ''))))


def _get_ia_name(run: Any) -> str:
    if isinstance(run, dict):
        config = run.get('config', {})
        if isinstance(config, dict):
            return str(config.get('assistant', config.get('ia', config.get('provider', ''))))
        return str(run.get('assistant', run.get('ia', run.get('provider', ''))))
    config = getattr(run, 'config', None)
    if config and isinstance(config, dict):
        return str(config.get('assistant', config.get('ia', config.get('provider', ''))))
    return str(getattr(run, 'assistant', getattr(run, 'ia', getattr(run, 'provider', ''))))


def _is_success(run: Any) -> bool:
    if isinstance(run, dict):
        status = run.get('status', run.get('result', ''))
        return str(status).lower() in ('success', 'ok', 'passed')
    status = getattr(run, 'status', getattr(run, 'result', ''))
    if hasattr(status, 'value'):
        status = status.value
    return str(status).lower() in ('success', 'ok', 'passed')


def _get_score(run: Any) -> float | None:
    if isinstance(run, dict):
        score = run.get('quality_score', run.get('score'))
    else:
        score = getattr(run, 'quality_score', getattr(run, 'score', None))
    if score is not None:
        try:
            return float(score)
        except (ValueError, TypeError):
            return None
    return None


def _get_latency(run: Any) -> float | None:
    if isinstance(run, dict):
        val = run.get('latency_seconds', run.get('duration_seconds'))
    else:
        val = getattr(run, 'latency_seconds', getattr(run, 'duration_seconds', None))
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    return None
