"""Regression Cycle Detector — detección de ciclos hacer-deshacer.

Detecta cuando el programa (o un agente) está deshaciendo trabajo
previamente implementado, creando un ciclo infinito de hacer y deshacer.

Funciona analizando:
  1. Git history: commits recientes que revierten cambios anteriores
  2. File churn: archivos que se modifican repetidamente sin progreso neto
  3. Backlog oscillation: tareas que se completan y reaparecen
  4. Function resurrection: funciones eliminadas que reaparecen

El programa debe tener percepción de si está borrando código que ya
implementó antes — un detector de regresión que compare cada cambio
contra el historial y alerte si está deshaciendo trabajo previo.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _run_git(args: list[str], workspace: str, timeout: int = 15) -> str:
    """Run a git command and return stdout."""
    try:
        r = subprocess.run(
            ['git', '-C', workspace] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


# ──────────────────────────────────────────────────────────────
# 1. Revert Detection — commits that undo previous commits
# ──────────────────────────────────────────────────────────────

def detect_reverts(workspace: str, lookback: int = 30) -> list[dict[str, Any]]:
    """Find commits in recent history that revert earlier commits."""
    log = _run_git(
        ['log', f'--max-count={lookback}', '--format=%H|||%s|||%an|||%ai'],
        workspace,
    )
    if not log:
        return []

    commits: list[dict[str, str]] = []
    for line in log.splitlines():
        parts = line.split('|||')
        if len(parts) >= 4:
            commits.append({
                'hash': parts[0][:12],
                'subject': parts[1],
                'author': parts[2],
                'date': parts[3],
            })

    reverts: list[dict[str, Any]] = []
    revert_patterns = [
        re.compile(r'[Rr]evert\s+"?(.+?)"?$'),
        re.compile(r'[Uu]ndo\s+(.+)'),
        re.compile(r'[Rr]ollback\s+(.+)'),
    ]

    for c in commits:
        for pattern in revert_patterns:
            m = pattern.search(c['subject'])
            if m:
                reverted_subject = m.group(1).strip('"').strip()
                # Find the original commit being reverted
                original = next(
                    (o for o in commits if reverted_subject in o['subject'] and o['hash'] != c['hash']),
                    None,
                )
                reverts.append({
                    'revert_commit': c['hash'],
                    'revert_subject': c['subject'],
                    'original_subject': reverted_subject,
                    'original_commit': original['hash'] if original else 'unknown',
                    'author': c['author'],
                    'date': c['date'],
                })
                break

    return reverts


# ──────────────────────────────────────────────────────────────
# 2. File Churn Detection — files modified repeatedly
# ──────────────────────────────────────────────────────────────

def detect_file_churn(workspace: str, lookback: int = 30,
                      threshold: int = 4) -> list[dict[str, Any]]:
    """Find files that are modified excessively in recent commits."""
    log = _run_git(
        ['log', f'--max-count={lookback}', '--name-only', '--format=COMMIT:%H'],
        workspace,
    )
    if not log:
        return []

    file_counts: Counter[str] = Counter()
    current_commit = ''
    for line in log.splitlines():
        if line.startswith('COMMIT:'):
            current_commit = line[7:19]
        elif line.strip():
            file_counts[line.strip()] += 1

    churned: list[dict[str, Any]] = []
    for filepath, count in file_counts.most_common(20):
        if count >= threshold:
            # Check net change — if file keeps getting modified but the
            # diff is small, it might be a churn cycle
            diff_stat = _run_git(
                ['log', f'--max-count={lookback}', '--numstat', '--', filepath],
                workspace,
            )
            total_added = 0
            total_removed = 0
            for dline in diff_stat.splitlines():
                parts = dline.split('\t')
                if len(parts) >= 2 and parts[0].isdigit():
                    total_added += int(parts[0])
                    total_removed += int(parts[1])

            net_change = total_added - total_removed
            churn_ratio = (total_added + total_removed) / max(abs(net_change), 1)

            churned.append({
                'file': filepath,
                'modifications': count,
                'total_added': total_added,
                'total_removed': total_removed,
                'net_change': net_change,
                'churn_ratio': round(churn_ratio, 1),
                'is_cyclic': churn_ratio > 5 and count >= threshold,
            })

    return churned


# ──────────────────────────────────────────────────────────────
# 3. Backlog Oscillation — tasks that complete and reappear
# ──────────────────────────────────────────────────────────────

def detect_backlog_oscillation(workspace: str) -> list[dict[str, Any]]:
    """Detect tasks that were completed but reappeared as pending."""
    backlog_path = Path(workspace) / 'data' / 'evolution' / 'backlog.json'
    if not backlog_path.exists():
        return []

    try:
        backlog = json.loads(backlog_path.read_text(encoding='utf-8'))
    except Exception:
        return []

    # Group by title — if the same title appears both completed and pending,
    # it's oscillating
    title_groups: dict[str, list[dict[str, Any]]] = {}
    for task in backlog:
        title = task.get('title', '')
        title_groups.setdefault(title, []).append(task)

    oscillations: list[dict[str, Any]] = []
    for title, tasks in title_groups.items():
        statuses = [t.get('status') for t in tasks]
        if 'completed' in statuses and ('pending' in statuses or 'in_progress' in statuses):
            oscillations.append({
                'title': title[:80],
                'occurrences': len(tasks),
                'statuses': statuses,
                'last_completed': next(
                    (t.get('completed_at') for t in reversed(tasks) if t.get('status') == 'completed'),
                    None,
                ),
            })

    return oscillations


# ──────────────────────────────────────────────────────────────
# 4. Function Resurrection — deleted code that reappears
# ──────────────────────────────────────────────────────────────

def detect_function_resurrection(workspace: str, lookback: int = 20) -> list[dict[str, Any]]:
    """Detect functions that were deleted in one commit and re-added later."""
    log = _run_git(
        ['log', f'--max-count={lookback}', '--format=COMMIT:%H:%s', '-p',
         '--', '*.py'],
        workspace, timeout=30,
    )
    if not log:
        return []

    # Track function additions and deletions per commit
    func_pattern = re.compile(r'^[+-]def\s+(\w+)\s*\(')
    deleted_funcs: dict[str, str] = {}  # func_name -> commit that deleted it
    resurrected: list[dict[str, Any]] = []
    current_commit = ''
    current_subject = ''

    for line in log.splitlines():
        if line.startswith('COMMIT:'):
            parts = line.split(':', 2)
            current_commit = parts[1][:12] if len(parts) > 1 else ''
            current_subject = parts[2] if len(parts) > 2 else ''
            continue

        m = func_pattern.match(line)
        if not m:
            continue

        func_name = m.group(1)
        if line.startswith('-def'):
            deleted_funcs[func_name] = current_commit
        elif line.startswith('+def') and func_name in deleted_funcs:
            resurrected.append({
                'function': func_name,
                'deleted_in': deleted_funcs[func_name],
                'resurrected_in': current_commit,
                'resurrected_subject': current_subject,
            })

    return resurrected


# ──────────────────────────────────────────────────────────────
# Full Regression Cycle Report
# ──────────────────────────────────────────────────────────────

def regression_cycle_scan(workspace: str | None = None) -> dict[str, Any]:
    """Full regression cycle detection scan."""
    ws = workspace or os.environ.get('IABV_WORKSPACE', '')
    if not ws:
        ws = str(Path(__file__).resolve().parents[3])

    reverts = detect_reverts(ws)
    churn = detect_file_churn(ws)
    oscillations = detect_backlog_oscillation(ws)
    resurrections = detect_function_resurrection(ws)

    cyclic_files = [f for f in churn if f.get('is_cyclic')]

    severity = 'ok'
    if reverts or cyclic_files or oscillations:
        severity = 'warning'
    if len(reverts) > 3 or len(cyclic_files) > 5:
        severity = 'critical'

    alerts: list[str] = []
    if reverts:
        alerts.append(f'{len(reverts)} commits de revert detectados — posible ciclo hacer-deshacer')
    if cyclic_files:
        alerts.append(f'{len(cyclic_files)} archivos con churn cíclico (modificados repetidamente sin progreso neto)')
    if oscillations:
        alerts.append(f'{len(oscillations)} tareas del backlog oscilando (completadas y reaparecidas)')
    if resurrections:
        alerts.append(f'{len(resurrections)} funciones resucitadas (eliminadas y re-creadas)')

    return {
        'reverts': reverts,
        'file_churn': churn,
        'cyclic_files': cyclic_files,
        'backlog_oscillations': oscillations,
        'function_resurrections': resurrections,
        'severity': severity,
        'alerts': alerts,
        'summary': {
            'revert_count': len(reverts),
            'churn_files': len(churn),
            'cyclic_files': len(cyclic_files),
            'oscillation_count': len(oscillations),
            'resurrection_count': len(resurrections),
            'total_issues': len(reverts) + len(cyclic_files) + len(oscillations) + len(resurrections),
        },
    }


def format_regression_report(scan: dict[str, Any]) -> str:
    """Format regression cycle scan for the auto-analysis report."""
    lines: list[str] = ['== DETECTOR DE CICLOS Y REGRESIONES ==']
    summary = scan.get('summary', {})

    if summary.get('total_issues', 0) == 0:
        lines.append('  Sin ciclos ni regresiones detectadas — progreso estable.')
        return '\n'.join(lines)

    severity = scan.get('severity', 'ok')
    icon = {'critical': 'CRITICO', 'warning': 'ALERTA', 'ok': 'OK'}.get(severity, '?')
    lines.append(f'  Estado: [{icon}]')

    # Reverts
    reverts = scan.get('reverts', [])
    if reverts:
        lines.append(f'  Reverts: {len(reverts)}')
        for r in reverts[:3]:
            lines.append(f'    - {r["revert_commit"]}: {r["revert_subject"][:60]}')

    # Cyclic files
    cyclic = scan.get('cyclic_files', [])
    if cyclic:
        lines.append(f'  Archivos cíclicos: {len(cyclic)}')
        for f in cyclic[:3]:
            lines.append(
                f'    - {f["file"]}: {f["modifications"]}x modificado, '
                f'ratio={f["churn_ratio"]}, neto={f["net_change"]:+d} líneas'
            )

    # Oscillations
    osc = scan.get('backlog_oscillations', [])
    if osc:
        lines.append(f'  Tareas oscilantes: {len(osc)}')
        for o in osc[:3]:
            lines.append(f'    - "{o["title"]}" ({o["occurrences"]}x)')

    # Resurrections
    res = scan.get('function_resurrections', [])
    if res:
        lines.append(f'  Funciones resucitadas: {len(res)}')
        for r in res[:3]:
            lines.append(f'    - {r["function"]}() eliminada en {r["deleted_in"]}, re-creada en {r["resurrected_in"]}')

    # Alerts
    for a in scan.get('alerts', []):
        lines.append(f'  ! {a}')

    return '\n'.join(lines)
