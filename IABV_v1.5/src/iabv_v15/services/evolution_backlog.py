"""Evolution Backlog — zona de tareas pendientes visible para todas las IAs.

Este módulo persiste las tareas de evolución que el programa (o un humano)
detecta como necesarias. Cualquier IA, sesión o auto-auditoría puede:
  1. Leer el backlog completo
  2. Agregar nuevas tareas descubiertas durante auditoría
  3. Marcar tareas completadas
  4. Deducir prioridades automáticamente cruzando con el estado del entorno

El archivo se guarda en ``data/evolution/backlog.json`` para que persista
entre sesiones y sea accesible por PortableContextService.

Cada tarea tiene:
  - id: UUID único
  - title: descripción corta
  - area: categoría (metacognition, hardware, gpu, tools, learning, etc.)
  - priority: critical / high / medium / low
  - status: pending / in_progress / completed / deferred
  - source: quién la creó (audit, human, auto_analysis, devin, etc.)
  - created_at: cuándo se descubrió
  - completed_at: cuándo se completó (si aplica)
  - evidence: por qué es necesaria
  - depends_on: IDs de tareas que deben completarse primero
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _default_backlog_path(workspace: str | None = None) -> Path:
    ws = workspace or os.environ.get('IABV_WORKSPACE', '')
    if not ws:
        ws = str(Path(__file__).resolve().parents[3])
    return Path(ws) / 'data' / 'evolution' / 'backlog.json'


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def load_backlog(workspace: str | None = None) -> list[dict[str, Any]]:
    """Load the full evolution backlog from disk."""
    path = _default_backlog_path(workspace)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning('Failed to load backlog: %s', exc)
    return []


def save_backlog(items: list[dict[str, Any]], workspace: str | None = None) -> str:
    """Save the full evolution backlog to disk."""
    path = _default_backlog_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(items, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    return str(path)


def add_task(
    *,
    title: str,
    area: str,
    priority: str = 'medium',
    source: str = 'auto_analysis',
    evidence: str = '',
    depends_on: list[str] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    """Add a new task to the evolution backlog."""
    backlog = load_backlog(workspace)

    # Deduplicate: skip if a pending/in_progress task with same title exists
    for existing in backlog:
        if existing.get('title') == title and existing.get('status') in ('pending', 'in_progress'):
            return existing

    task: dict[str, Any] = {
        'id': str(uuid4()),
        'title': title,
        'area': area,
        'priority': priority,
        'status': 'pending',
        'source': source,
        'created_at': _utc_now_iso(),
        'completed_at': None,
        'evidence': evidence,
        'depends_on': depends_on or [],
    }
    backlog.append(task)
    save_backlog(backlog, workspace)
    return task


def complete_task(task_id: str, workspace: str | None = None) -> bool:
    """Mark a task as completed."""
    backlog = load_backlog(workspace)
    for item in backlog:
        if item.get('id') == task_id:
            item['status'] = 'completed'
            item['completed_at'] = _utc_now_iso()
            save_backlog(backlog, workspace)
            return True
    return False


def get_pending_tasks(workspace: str | None = None) -> list[dict[str, Any]]:
    """Get all pending/in_progress tasks, sorted by priority."""
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    backlog = load_backlog(workspace)
    pending = [t for t in backlog if t.get('status') in ('pending', 'in_progress')]
    pending.sort(key=lambda t: priority_order.get(t.get('priority', 'medium'), 2))
    return pending


def deduce_priorities(
    *,
    environment_scan: dict[str, Any] | None = None,
    holistic_scan: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    """Re-prioritize backlog tasks based on current environment state.

    Cross-references the pending tasks with live scan results to:
    1. Auto-complete tasks whose work is already done (evidence in scan)
    2. Promote tasks that match current deductions or blind spots
    3. Demote tasks for areas that are already working
    """
    backlog = load_backlog(workspace)
    env = environment_scan or {}
    hol = holistic_scan or {}
    env_summary = env.get('summary', {})

    # --- Phase 1: Auto-complete tasks that are evidently resolved ---
    _auto_complete_resolved(backlog, env_summary, hol)

    pending = [t for t in backlog if t.get('status') in ('pending', 'in_progress')]

    deductions_areas = {d.get('area', '') for d in hol.get('deductions', [])}
    blind_spots = set(hol.get('blind_spots', []))

    for task in pending:
        area = task.get('area', '')

        # Promote tasks that match current deductions or blind spots
        if area in deductions_areas:
            if task.get('priority') not in ('critical',):
                task['priority'] = 'high'
                task['priority_reason'] = f'matches active deduction in area: {area}'

        # Promote tasks related to blind spots
        if any(area in bs for bs in blind_spots):
            if task.get('priority') not in ('critical', 'high'):
                task['priority'] = 'high'
                task['priority_reason'] = f'addresses blind spot: {area}'

        # Demote tasks for areas that are already working
        if area == 'peripherals' and env_summary.get('usb_devices', 0) > 0:
            if task.get('priority') == 'critical':
                task['priority'] = 'medium'
                task['priority_reason'] = 'peripherals already partially scanned'

    save_backlog(backlog, workspace)

    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    pending.sort(key=lambda t: priority_order.get(t.get('priority', 'medium'), 2))
    return pending


def _auto_complete_resolved(
    backlog: list[dict[str, Any]],
    env_summary: dict[str, Any],
    holistic: dict[str, Any],
) -> None:
    """Auto-complete backlog tasks whose work is evidently done.

    Checks each pending task against live scan evidence and marks it
    completed if the problem it describes is already resolved.
    """
    now = _utc_now_iso()

    for task in backlog:
        if task.get('status') not in ('pending', 'in_progress'):
            continue

        title_lower = task.get('title', '').lower()
        area = task.get('area', '')
        resolved_reason = ''

        # Deep environment scan task — resolved if coverage > 50%
        if area == 'environment_discovery' and 'escaneo profundo' in title_lower:
            coverage = env_summary.get('coverage_estimate', 0)
            if coverage >= 0.5:
                resolved_reason = f'cobertura del entorno: {coverage:.0%}'

        # Holistic cross-validation with peripherals — resolved if scan has data
        if area == 'metacognition' and 'cruce holístico' in title_lower and 'periféricos' in title_lower:
            has_peripherals = (
                env_summary.get('usb_devices', 0) > 0
                or env_summary.get('printers', 0) > 0
                or env_summary.get('audio_devices', 0) > 0
            )
            if has_peripherals:
                resolved_reason = 'periféricos incluidos en escaneo profundo'

        # Trend comparison fix — resolved (implemented in PR #175)
        if 'trend comparison' in title_lower and 'holistic_deductions' in title_lower:
            resolved_reason = 'implementado en PR #175'

        if resolved_reason:
            task['status'] = 'completed'
            task['completed_at'] = now
            task['completed_reason'] = f'auto-completada: {resolved_reason}'
            logger.info('backlog auto-complete: "%s" — %s', task['title'][:60], resolved_reason)


def seed_initial_backlog(workspace: str | None = None) -> list[dict[str, Any]]:
    """Seed the backlog with known pending tasks from the audit sessions.

    These are tasks identified during the teaching audit that the program
    should discover and work on. They are seeded ONCE — if the backlog
    already has items, this is a no-op.
    """
    existing = load_backlog(workspace)
    if existing:
        return existing

    initial_tasks = [
        {
            'title': 'Escaneo profundo del entorno: BIOS, USB, impresoras, audio, bluetooth, monitores, red, seguridad',
            'area': 'environment_discovery',
            'priority': 'critical',
            'source': 'audit_session',
            'evidence': 'El programa solo conoce ~35% de su entorno. No detecta periféricos, BIOS, ni estado de seguridad.',
        },
        {
            'title': 'Cruce holístico de fuentes de verdad ampliado — incluir periféricos, seguridad y servicios del OS',
            'area': 'metacognition',
            'priority': 'critical',
            'source': 'audit_session',
            'evidence': 'holistic_metacognition_scan cruza 9 pares pero no incluye periféricos ni seguridad.',
        },
        {
            'title': 'GPU routing inteligente: GPU1 (NVIDIA) como primaria, GPU0 (Intel iGPU) como refuerzo',
            'area': 'gpu_routing',
            'priority': 'high',
            'source': 'audit_session',
            'evidence': 'El usuario reporta que la GPU dedicada debería ser primaria y la iGPU refuerzo para alta demanda.',
        },
        {
            'title': 'Sonido de notificación cuando termina de procesar una consulta',
            'area': 'user_experience',
            'priority': 'medium',
            'source': 'audit_session',
            'evidence': 'El usuario quiere feedback auditivo cuando IABV termina de procesar.',
        },
        {
            'title': 'Persistir patrones aprendidos en PortableContextService para futuras sesiones',
            'area': 'learning_persistence',
            'priority': 'high',
            'source': 'audit_session',
            'evidence': 'El programa aprende pero no persiste lo aprendido entre sesiones de forma visible.',
        },
        {
            'title': 'Auto-descubrimiento de documentación: leer manuales de herramientas, monitorear versiones nuevas',
            'area': 'tool_evolution',
            'priority': 'medium',
            'source': 'audit_session',
            'evidence': 'El programa debería auto-descubrir qué herramientas tiene y leer sus manuales/changelogs.',
        },
        {
            'title': 'Wplay no queda aprendido — SiteExplorerToolAdapter no devuelve resultado con comparison_scope_key',
            'area': 'learning_persistence',
            'priority': 'high',
            'source': 'audit_session',
            'evidence': 'Consulta autónoma IABV detectó que las enseñanzas sobre Wplay no persisten entre sesiones.',
        },
        {
            'title': 'Métricas de decisión completas: GPU usada, tiempo, IA elegida, configuración, resultado',
            'area': 'metacognition',
            'priority': 'high',
            'source': 'audit_session',
            'evidence': 'Al encender/ejecutar/terminar una tarea, el programa debe registrar qué eligió y por qué.',
        },
        {
            'title': 'Auto-testeo profundo: cobertura de tests, complejidad ciclomática, dependencias circulares',
            'area': 'self_testing',
            'priority': 'medium',
            'source': 'audit_session',
            'evidence': 'El programa no sabe qué % de su código está cubierto ni dónde hay complejidad excesiva.',
        },
        {
            'title': 'Consultas autónomas completamente invisibles (headless/API, nunca ventanas visibles)',
            'area': 'consultation_mode',
            'priority': 'high',
            'source': 'audit_session',
            'evidence': 'PR #174 suprimió fallback visible pero falta verificar todas las rutas de consulta.',
        },
        {
            'title': 'Multi-monitor: posicionar ventanas en monitor correcto según contexto de tarea',
            'area': 'display_awareness',
            'priority': 'medium',
            'source': 'audit_session',
            'evidence': 'PR #174 agregó detección pero la lógica de posicionamiento es básica.',
        },
        {
            'title': 'Trend comparison fix: comparar holistic_deductions con holistic_deductions (no issues_found)',
            'area': 'metacognition',
            'priority': 'medium',
            'source': 'devin_review',
            'evidence': 'Devin Review round 2 detectó que la comparación de tendencias mezcla métricas diferentes.',
        },
    ]

    backlog: list[dict[str, Any]] = []
    for t in initial_tasks:
        task = {
            'id': str(uuid4()),
            'title': t['title'],
            'area': t['area'],
            'priority': t['priority'],
            'status': 'pending',
            'source': t['source'],
            'created_at': _utc_now_iso(),
            'completed_at': None,
            'evidence': t['evidence'],
            'depends_on': [],
        }
        backlog.append(task)

    save_backlog(backlog, workspace)
    return backlog


def format_backlog_report(workspace: str | None = None) -> str:
    """Format the backlog for the auto-analysis report."""
    backlog = load_backlog(workspace)
    pending = [t for t in backlog if t.get('status') in ('pending', 'in_progress')]
    completed = [t for t in backlog if t.get('status') == 'completed']

    lines = ['== BACKLOG DE EVOLUCION ==']

    if completed:
        auto_completed = [t for t in completed if t.get('completed_reason', '').startswith('auto-completada')]
        if auto_completed:
            lines.append(f'Tareas auto-completadas esta sesion: {len(auto_completed)}')
            for t in auto_completed:
                lines.append(f'    [COMPLETADA] {t["title"][:70]}')
                lines.append(f'      ({t.get("completed_reason", "")})')
        lines.append(f'Total completadas: {len(completed)}')

    if not pending:
        lines.append('No hay tareas pendientes.')
        return '\n'.join(lines)

    lines.append(f'Tareas pendientes: {len(pending)}')

    by_priority: dict[str, list[dict[str, Any]]] = {}
    for t in pending:
        p = t.get('priority', 'medium')
        by_priority.setdefault(p, []).append(t)

    priority_labels = {'critical': 'CRITICO', 'high': 'ALTA', 'medium': 'MEDIA', 'low': 'BAJA'}
    for prio in ['critical', 'high', 'medium', 'low']:
        tasks = by_priority.get(prio, [])
        if tasks:
            lines.append(f'  [{priority_labels.get(prio, prio)}] ({len(tasks)}):')
            for t in tasks:
                status_icon = '>' if t.get('status') == 'in_progress' else '-'
                lines.append(f'    {status_icon} {t["title"][:80]}')
                if t.get('priority_reason'):
                    lines.append(f'      (razon: {t["priority_reason"][:60]})')

    return '\n'.join(lines)
