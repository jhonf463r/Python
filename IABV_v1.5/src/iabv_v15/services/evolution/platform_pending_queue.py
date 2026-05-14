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


# ------------------------------------------------------------------
# Canonical category constants used across bootstrap.py,
# autonomy_cycle_service.py, and the queue itself.
# ------------------------------------------------------------------
CATEGORY_MISSING_TOOL = 'missing_tool'
CATEGORY_PERMISSION_REQUIRED = 'permission_required'
CATEGORY_OSES_FINDING = 'oses_finding'
CATEGORY_CAPABILITY_DISCOVERY = 'capability_discovery'
CATEGORY_WINDOWS_NATIVE = 'windows_native'
CATEGORY_INVESTIGATION = 'investigation'


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

    # Alias for consistent external naming (the prompt and MCP tools
    # refer to ``list_tasks``).
    list_tasks = list_all

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
        """Return a list of dicts suitable for PortableContext pending section.

        Only includes tasks with actionable statuses (PENDING,
        READY_FOR_NEXT_SLICE, BLOCKED).  COMPLETED tasks are excluded
        because they are not pending work.
        """
        actionable_statuses = {
            PendingTaskStatus.PENDING,
            PendingTaskStatus.READY_FOR_NEXT_SLICE,
            PendingTaskStatus.BLOCKED,
        }
        items: list[dict[str, Any]] = []
        for t in self.list_all():
            if t.status not in actionable_statuses:
                continue
            if len(items) >= limit:
                break
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
    # Capability discovery → queue (Fix 18e)
    # ------------------------------------------------------------------

    def seed_from_capability_graph(
        self,
        capabilities: list[Any],
    ) -> list[PlatformPendingTask]:
        """Create pending tasks for missing environment capabilities.

        Accepts a list of ``EnvironmentCapability`` objects (or dicts with
        compatible fields).  Already-completed tasks are not overwritten.
        """
        seeded: list[PlatformPendingTask] = []
        for cap in capabilities:
            cap_id = getattr(cap, 'capability_id', '') or (cap.get('capability_id', '') if isinstance(cap, dict) else '')
            available = getattr(cap, 'available', True) if not isinstance(cap, dict) else cap.get('available', True)
            if not cap_id or available:
                continue
            task_id = f'cap_{cap_id}'
            existing = self.get(task_id)
            if existing is not None and existing.status == PendingTaskStatus.COMPLETED:
                continue
            title = getattr(cap, 'title', cap_id) if not isinstance(cap, dict) else cap.get('title', cap_id)
            summary = getattr(cap, 'summary', '') if not isinstance(cap, dict) else cap.get('summary', '')
            status_str = getattr(cap, 'status', 'missing') if not isinstance(cap, dict) else cap.get('status', 'missing')
            dep = ''
            meta = getattr(cap, 'metadata', {}) if not isinstance(cap, dict) else cap.get('metadata', {})
            if isinstance(meta, dict):
                dep = meta.get('missing', '') or meta.get('dependency', '')
            task = PlatformPendingTask(
                id=task_id,
                title=f'Capacidad faltante: {title}',
                description=summary or f'{cap_id} no disponible en el entorno',
                reason=f'capability status: {status_str}',
                dependency_missing=str(dep),
                priority='medium',
                next_action=f'Verificar e instalar dependencia para {cap_id}',
                status=(
                    PendingTaskStatus.BLOCKED if dep
                    else PendingTaskStatus.PENDING
                ),
                category=CATEGORY_CAPABILITY_DISCOVERY,
            )
            if existing is not None:
                task = task.model_copy(update={
                    'status': existing.status,
                    'updated_at': utc_now(),
                })
            seeded.append(self.upsert(task))
        return seeded

    # ------------------------------------------------------------------
    # Metacognition roadmap — investigation phases
    # ------------------------------------------------------------------

    _METACOGNITION_PHASES: list[dict[str, Any]] = [
        {
            'id': 'inv_phase_a_antifreeze',
            'title': 'Fase A: Regulación inteligente anti-freeze',
            'description': (
                'El programa monitorea su propio consumo (CPU, RAM, hilos, '
                'SQLite locks) y se auto-regula — si detecta que va a '
                'saturarse, pausa o reduce procesos antes de congelarse. '
                'Extiende AutonomyGovernancePolicy, _assess_resource_pressure '
                'y BackgroundResourceMonitor.'
            ),
            'reason': 'El usuario reporta congelamientos; el programa debe prevenirlos proactivamente.',
            'dependency_missing': '',
            'priority': 'high',
            'next_action': (
                'Aplicar evaluate_operational_budget() a cada trabajo auxiliar '
                'pesado antes de ejecutarlo; pausar o degradar tareas cuando '
                'hay usuario esperando, stalls recientes o presion >= HIGH.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
        {
            'id': 'inv_phase_a2_budgeted_idle_self_tests',
            'title': 'Fase A2: Auto-tests periodicos con presupuesto operativo',
            'description': (
                'Ejecutar reexamenes, pruebas de coherencia, limpieza de '
                'contexto y verificaciones de ramas solo durante ventanas de '
                'descanso: usuario no esperando, RSS estable, sin stalls '
                'recientes y confianza suficiente.'
            ),
            'reason': (
                'El sistema ya detecta problemas, pero necesita decidir '
                'cuando puede testearse a si mismo sin saturar la UI ni '
                'romper la conversacion visible.'
            ),
            'dependency_missing': 'inv_phase_a_antifreeze',
            'priority': 'high',
            'next_action': (
                'Conectar AutonomousValidationCycleService y OSES al nuevo '
                'evaluate_operational_budget(work_class=idle_self_test); '
                'registrar resultados en ExperimentLab/OSES/ControlMaster.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
        {
            'id': 'inv_phase_a3_budget_experiment_feedback',
            'title': 'Fase A3: Evaluar presupuesto operativo con ExperimentLab',
            'description': (
                'Cada decision del presupuesto operativo queda registrada como '
                'ExperimentRun comparable para que OSES y PortableContext puedan '
                'aprender de defer/allow/ask_user sin depender de impresiones.'
            ),
            'reason': (
                'El sistema necesita evidencia historica testeable antes de '
                'cambiar sus propios umbrales de RAM, stalls o ventana de descanso.'
            ),
            'dependency_missing': 'inv_phase_a2_budgeted_idle_self_tests',
            'priority': 'high',
            'next_action': (
                'Registrar outcomes de evaluate_operational_budget en ExperimentLab '
                'y exportarlos en OSES/PortableContext.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
        {
            'id': 'inv_phase_a4_budget_threshold_calibration',
            'title': 'Fase A4: Calibrar umbrales del presupuesto operativo por evidencia',
            'description': (
                'OSES lee los ExperimentRun del presupuesto operativo y decide si '
                'hay muestra suficiente para conservar, ajustar o aplazar cambios '
                'de umbral sin improvisar.'
            ),
            'reason': (
                'La autonomia debe testear sus propias constantes antes de aplicar '
                'cambios: idle_rest_window, stall_ms y umbrales de RSS.'
            ),
            'dependency_missing': 'inv_phase_a3_budget_experiment_feedback',
            'priority': 'high',
            'next_action': (
                'Agregar resumen de calibracion a OSES/PortableContext y emitir '
                'finding solo cuando la muestra sea suficiente.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
        {
            'id': 'inv_phase_a5_runtime_budget_threshold_application',
            'title': 'Fase A5: Aplicacion gobernada de umbrales runtime',
            'description': (
                'Convertir recomendaciones de calibracion en ajustes runtime '
                'reversibles usando RuntimeTuningRepository, con evidencia antes '
                'y despues y sin tocar politica sensible a ciegas.'
            ),
            'reason': (
                'A4 puede recomendar; A5 debe aplicar solo cambios seguros, '
                'versionados y reversibles cuando haya evidencia suficiente.'
            ),
            'dependency_missing': 'inv_phase_a4_budget_threshold_calibration',
            'priority': 'medium',
            'next_action': (
                'Definir gate para promover recommended_thresholds a RuntimeTuning '
                'solo si OSES reporta muestra suficiente y no hay stalls recientes.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
        {
            'id': 'inv_phase_b_visual_metacognition',
            'title': 'Fase B: Percepción visual del UI propio (metacognición visual)',
            'description': (
                'El programa "ve" su propia interfaz — sabe qué widgets '
                'están visibles, su estado, y mapea cada componente visual '
                'a su código fuente. Autoconciencia visual integrada, no '
                'grabación externa.'
            ),
            'reason': 'Necesario para auditoría automática y replay guiado.',
            'dependency_missing': 'inv_phase_a2_budgeted_idle_self_tests',
            'priority': 'medium',
            'next_action': (
                'Diseñar QML introspection layer que exponga el árbol '
                'de widgets activo a WorldModelSnapshot.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
        {
            'id': 'inv_phase_c_guided_replay',
            'title': 'Fase C: Replay guiado con UI Highlighting (tutorial interactivo)',
            'description': (
                'Cuando IABV necesita enseñar al usuario una tarea que no '
                'puede hacer solo, muestra un replay guiado con highlighting '
                'visual — resalta botones, campos, pasos a seguir, como un '
                'tutorial interactivo dentro de la misma ventana.'
            ),
            'reason': 'Mejorar comunicación máquina-humano mediante guía visual.',
            'dependency_missing': 'inv_phase_b_visual_metacognition',
            'priority': 'low',
            'next_action': (
                'Diseñar overlay QML que reciba secuencia de pasos y '
                'resalte widgets con animación y texto explicativo.'
            ),
            'status': 'PENDING',
            'category': CATEGORY_INVESTIGATION,
        },
    ]

    def seed_metacognition_investigation_phases(self) -> list[PlatformPendingTask]:
        """Register the metacognition roadmap phases as pending tasks.

        Idempotent: completed tasks are not overwritten.
        """
        seeded: list[PlatformPendingTask] = []
        for task_dict in self._METACOGNITION_PHASES:
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
            'Bridge de notificaciones con fallback: winotify (Action '
            'Center) si instalado, QSystemTrayIcon balloon si hay '
            'systray activo, noop si no hay backend. Implementado '
            'en Fix 21 via WinToastBridge.'
        ),
        'reason': 'Implementado en Fix 21',
        'dependency_missing': '',
        'priority': 'high',
        'next_action': '',
        'status': 'COMPLETED',
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
