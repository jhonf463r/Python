"""Persistent queue for platform integration pending tasks (Fix 18b).

Stores ``PlatformPendingTask`` objects as individual JSON files under
``data/evolution/platform_pending/``.  The queue is designed to be read
by PortableContext, OSES, and any agent that resumes work — providing
a structured view of what capabilities are missing, what is blocked,
and what the next action should be for each item.

The queue also supports ``PlatformResumeHint`` objects for checkpoint
and auto-resume semantics (Fix 18d).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    PendingTaskStatus,
    PlatformPendingTask,
    PlatformResumeHint,
    utc_now,
)


class PlatformPendingQueue:
    """Persistent FIFO queue for platform-level pending tasks."""

    def __init__(self, evolution_dir: str | Path) -> None:
        self._dir = Path(evolution_dir).resolve() / 'platform_pending'
        self._dir.mkdir(parents=True, exist_ok=True)
        self._resume_dir = self._dir / 'resume_hints'
        self._resume_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Pending tasks
    # ------------------------------------------------------------------

    def upsert(self, task: PlatformPendingTask) -> PlatformPendingTask:
        """Insert or update a pending task.  Returns the persisted copy."""
        task = task.model_copy(update={'updated_at': utc_now()})
        path = self._task_path(task.id)
        path.write_text(
            task.model_dump_json(indent=2),
            encoding='utf-8',
        )
        return task

    def get(self, task_id: str) -> PlatformPendingTask | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        try:
            return PlatformPendingTask.model_validate_json(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def list_all(self) -> list[PlatformPendingTask]:
        """Return all pending tasks sorted by priority (critical > high > medium > low)."""
        tasks: list[PlatformPendingTask] = []
        for path in sorted(self._dir.glob('task_*.json')):
            try:
                tasks.append(PlatformPendingTask.model_validate_json(path.read_text(encoding='utf-8')))
            except Exception:
                continue
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        tasks.sort(key=lambda t: priority_order.get(t.priority, 99))
        return tasks

    def list_actionable(self) -> list[PlatformPendingTask]:
        """Return tasks that are PENDING or READY_FOR_NEXT_SLICE."""
        return [
            t for t in self.list_all()
            if t.status in (PendingTaskStatus.PENDING, PendingTaskStatus.READY_FOR_NEXT_SLICE)
        ]

    def list_blocked(self) -> list[PlatformPendingTask]:
        return [t for t in self.list_all() if t.status == PendingTaskStatus.BLOCKED]

    def mark_status(self, task_id: str, status: PendingTaskStatus) -> PlatformPendingTask | None:
        task = self.get(task_id)
        if task is None:
            return None
        task = task.model_copy(update={'status': status, 'updated_at': utc_now()})
        return self.upsert(task)

    def summary(self) -> dict[str, Any]:
        """Return a machine-readable summary of the queue state."""
        tasks = self.list_all()
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            by_priority[t.priority] = by_priority.get(t.priority, 0) + 1
        return {
            'total': len(tasks),
            'by_status': by_status,
            'by_priority': by_priority,
            'actionable': len(self.list_actionable()),
            'blocked': len(self.list_blocked()),
        }

    def to_portable_items(self, *, limit: int = 8) -> list[dict[str, Any]]:
        """Return a list of dicts suitable for PortableContext pending section."""
        items: list[dict[str, Any]] = []
        for t in self.list_all()[:limit]:
            items.append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'reason': t.reason,
                'dependency_missing': t.dependency_missing,
                'priority': t.priority,
                'next_action': t.next_action,
                'status': t.status.value,
                'category': t.category,
                'resume_hint': t.resume_hint,
            })
        return items

    # ------------------------------------------------------------------
    # Resume hints (Fix 18d)
    # ------------------------------------------------------------------

    def save_resume_hint(self, hint: PlatformResumeHint) -> PlatformResumeHint:
        """Persist a resume hint for a task."""
        path = self._resume_dir / f'hint_{hint.task_id}.json'
        path.write_text(hint.model_dump_json(indent=2), encoding='utf-8')
        return hint

    def get_resume_hint(self, task_id: str) -> PlatformResumeHint | None:
        path = self._resume_dir / f'hint_{task_id}.json'
        if not path.exists():
            return None
        try:
            return PlatformResumeHint.model_validate_json(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def list_resume_hints(self) -> list[PlatformResumeHint]:
        hints: list[PlatformResumeHint] = []
        for path in sorted(self._resume_dir.glob('hint_*.json')):
            try:
                hints.append(PlatformResumeHint.model_validate_json(path.read_text(encoding='utf-8')))
            except Exception:
                continue
        return hints

    # ------------------------------------------------------------------
    # Seed: populate queue with known Windows integration gaps
    # ------------------------------------------------------------------

    def seed_windows_integration_tasks(self) -> list[PlatformPendingTask]:
        """Register the canonical set of Windows integration pending tasks.

        Called once (idempotent) to populate the queue with the known gaps
        identified during the Windows platform audit.  Each task has a
        stable ``id`` so re-running this method does not create duplicates.
        """
        tasks = _WINDOWS_INTEGRATION_TASKS
        seeded: list[PlatformPendingTask] = []
        for task_dict in tasks:
            task_id = task_dict['id']
            existing = self.get(task_id)
            if existing is not None and existing.status == PendingTaskStatus.COMPLETED:
                continue
            task = PlatformPendingTask(**task_dict)
            if existing is not None:
                task = task.model_copy(update={
                    'status': existing.status,
                    'updated_at': utc_now(),
                })
            seeded.append(self.upsert(task))
        return seeded

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _task_path(self, task_id: str) -> Path:
        safe_id = task_id.replace('/', '_').replace('\\', '_')
        return self._dir / f'task_{safe_id}.json'


# ======================================================================
# Canonical Windows integration pending tasks
# ======================================================================

_WINDOWS_INTEGRATION_TASKS: list[dict[str, Any]] = [
    {
        'id': 'win_toast_notifications',
        'title': 'Notificaciones toast nativas',
        'description': (
            'Implementar envio de notificaciones toast de Windows 10+ '
            'para alertas criticas del sistema (starvation, degradacion, '
            'tareas completadas).'
        ),
        'reason': 'No hay libreria de toast instalada (winrt/plyer/winotify)',
        'dependency_missing': 'winotify o plyer (pip install winotify)',
        'priority': 'high',
        'next_action': 'pip install winotify && implementar NotificationBridge',
        'status': 'PENDING',
        'category': 'windows_native',
    },
    {
        'id': 'win_autostart_shortcut',
        'title': 'Autostart de IABV al login de Windows',
        'description': (
            'Crear shortcut en shell:startup para que IABV arranque '
            'automaticamente cuando el usuario inicia sesion.'
        ),
        'reason': 'La carpeta shell:startup existe pero no hay shortcut de IABV',
        'dependency_missing': 'Logica de creacion de .lnk (pywin32 o COM)',
        'priority': 'medium',
        'next_action': 'Implementar creacion de shortcut .lnk via COM/winshell',
        'status': 'PENDING',
        'category': 'windows_native',
    },
    {
        'id': 'win_systray_icon',
        'title': 'Icono en system tray',
        'description': (
            'Icono de IABV en el system tray de Windows con menu '
            'contextual (Mostrar / Salir). Implementado en Fix 19a '
            'via WinSystrayBridge + QSystemTrayIcon.'
        ),
        'reason': 'Implementado en Fix 19a',
        'dependency_missing': '',
        'priority': 'high',
        'next_action': '',
        'status': 'COMPLETED',
        'category': 'windows_native',
    },
    {
        'id': 'win_clipboard_bridge',
        'title': 'Clipboard bridge bidireccional',
        'description': (
            'Bridge nativo de clipboard Win32 via ctypes con '
            'get_text/set_text/has_text. Implementado en Fix 19b '
            'via WinClipboardBridge.'
        ),
        'reason': 'Implementado en Fix 19b',
        'dependency_missing': '',
        'priority': 'medium',
        'next_action': '',
        'status': 'COMPLETED',
        'category': 'windows_native',
    },
    {
        'id': 'win_power_awareness',
        'title': 'Deteccion de plan de energia y estado de pantalla',
        'description': (
            'Detectar si la pantalla esta apagada, el equipo en modo '
            'sleep, o el plan de energia es de ahorro. Ajustar scans y '
            'workers en consecuencia.'
        ),
        'reason': 'No hay deteccion de power plan ni screen lock',
        'dependency_missing': 'powercfg o WMI query',
        'priority': 'low',
        'next_action': 'Agregar _power_plan_snapshot() en EnvironmentSelfAwarenessService',
        'status': 'PENDING',
        'category': 'windows_native',
    },
    {
        'id': 'win_session_change_monitor',
        'title': 'Monitor de cambios de sesion Windows (lock/unlock)',
        'description': (
            'Detectar cuando el usuario bloquea/desbloquea la sesion, '
            'cierra sesion, o cambia de usuario. Pausar scans durante '
            'lock y reanudar al unlock.'
        ),
        'reason': 'No hay WTSRegisterSessionNotification ni hook',
        'dependency_missing': 'WTS API via ctypes o pywin32',
        'priority': 'medium',
        'next_action': 'Implementar via ctypes wtsapi32.WTSRegisterSessionNotification',
        'status': 'BLOCKED',
        'category': 'windows_native',
    },
    {
        'id': 'win_task_scheduler',
        'title': 'Integracion con Task Scheduler de Windows',
        'description': (
            'Crear y gestionar tareas programadas en Task Scheduler para '
            'maintenance, backups de data/, y health checks periodicos.'
        ),
        'reason': 'No hay integracion con Task Scheduler',
        'dependency_missing': 'schtasks.exe o COM API',
        'priority': 'low',
        'next_action': 'Evaluar si schtasks.exe cubre el caso o si se necesita COM',
        'status': 'PENDING',
        'category': 'windows_native',
    },
    {
        'id': 'win_filesystem_watcher',
        'title': 'Watcher de filesystem nativo (ReadDirectoryChangesW)',
        'description': (
            'Detectar cambios en archivos del workspace en tiempo real '
            'usando la API nativa de Windows en lugar de polling.'
        ),
        'reason': 'El hot-reload actual usa polling de mtimes',
        'dependency_missing': 'ReadDirectoryChangesW via ctypes o watchdog',
        'priority': 'low',
        'next_action': 'Evaluar watchdog vs ctypes directo; riesgo de dependencia pesada',
        'status': 'PENDING',
        'category': 'windows_native',
    },
    {
        'id': 'win_dpi_awareness',
        'title': 'DPI awareness para pantallas HiDPI',
        'description': (
            'SetProcessDpiAwareness(2) llamado en bootstrap antes '
            'de QGuiApplication. Implementado en Fix 19c.'
        ),
        'reason': 'Implementado en Fix 19c',
        'dependency_missing': '',
        'priority': 'medium',
        'next_action': '',
        'status': 'COMPLETED',
        'category': 'windows_native',
    },
]
