"""Intelligent Resource Manager — adaptive resource orchestration.

Monitors RAM/CPU, detects user activity, and prioritizes tasks
so the program responds fast when the user is interacting and
defers heavy work (training, merges, deep analysis) to idle periods.

Key capabilities:
  - Real-time resource snapshot (RAM, CPU, heavy processes)
  - User activity detection (typing = interactive → max responsiveness)
  - Task priority queue with auto-throttling
  - Self-diagnosis of freezes and resource contention
  - Configuration learning: records what works vs. what causes freezes
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RESOURCE SNAPSHOT
# ---------------------------------------------------------------------------

@dataclass
class ResourceSnapshot:
    """Point-in-time snapshot of system resources."""
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    ram_used_pct: float = 0.0
    cpu_load_1m: float = 0.0
    cpu_count: int = 1
    heavy_processes: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def ram_pressure(self) -> str:
        if self.ram_used_pct > 90:
            return 'critical'
        if self.ram_used_pct > 75:
            return 'high'
        if self.ram_used_pct > 50:
            return 'moderate'
        return 'low'

    @property
    def cpu_pressure(self) -> str:
        load_per_core = self.cpu_load_1m / max(self.cpu_count, 1)
        if load_per_core > 2.0:
            return 'critical'
        if load_per_core > 1.0:
            return 'high'
        if load_per_core > 0.5:
            return 'moderate'
        return 'low'


def _win32_ram_ctypes() -> tuple[int, int, float]:
    """Read RAM via Win32 GlobalMemoryStatusEx (instant, no subprocess).

    Returns (total_mb, available_mb, used_pct).  Falls back to (0, 0, 0.0)
    on non-Windows or on error.
    """
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[union-attr]
            return 0, 0, 0.0
        total_mb = int(status.ullTotalPhys) // (1024 * 1024)
        avail_mb = int(status.ullAvailPhys) // (1024 * 1024)
        used_pct = round(float(status.dwMemoryLoad), 1)
        return total_mb, avail_mb, used_pct
    except Exception:
        return 0, 0, 0.0


def _win32_cpu_pct() -> float:
    """Read CPU load percentage via Win32 GetSystemTimes (two-sample delta).

    Returns a pseudo-load value comparable to Unix load: pct/100 * cores.
    Falls back to 0.0 on error.
    """
    try:
        import ctypes

        class FILETIME(ctypes.Structure):
            _fields_ = [('lo', ctypes.c_ulong), ('hi', ctypes.c_ulong)]

        def _ft_val(ft: 'FILETIME') -> int:
            return ft.hi << 32 | ft.lo

        kernel32 = ctypes.windll.kernel32  # type: ignore[union-attr]
        idle1, kern1, user1 = FILETIME(), FILETIME(), FILETIME()
        kernel32.GetSystemTimes(
            ctypes.byref(idle1), ctypes.byref(kern1), ctypes.byref(user1),
        )
        time.sleep(0.25)
        idle2, kern2, user2 = FILETIME(), FILETIME(), FILETIME()
        kernel32.GetSystemTimes(
            ctypes.byref(idle2), ctypes.byref(kern2), ctypes.byref(user2),
        )
        idle_d = _ft_val(idle2) - _ft_val(idle1)
        total_d = (_ft_val(kern2) + _ft_val(user2)) - (_ft_val(kern1) + _ft_val(user1))
        if total_d <= 0:
            return 0.0
        busy_pct = (1 - idle_d / total_d) * 100
        cores = os.cpu_count() or 1
        return round(busy_pct / 100 * cores, 2)
    except Exception:
        return 0.0


def take_resource_snapshot() -> ResourceSnapshot:
    """Capture current system resource state (cross-platform).

    On Windows uses ctypes for instant kernel32 calls (no subprocess,
    no locale issues, no WMI timeout).  On Linux reads /proc directly.
    """
    snap = ResourceSnapshot()
    snap.cpu_count = os.cpu_count() or 1

    # --- RAM ---
    try:
        meminfo = Path('/proc/meminfo')
        if meminfo.exists():
            text = meminfo.read_text()
            import re
            total_m = re.search(r'MemTotal:\s+(\d+)', text)
            avail_m = re.search(r'MemAvailable:\s+(\d+)', text)
            if total_m and avail_m:
                total_kb = int(total_m.group(1))
                avail_kb = int(avail_m.group(1))
                snap.ram_total_mb = total_kb // 1024
                snap.ram_available_mb = avail_kb // 1024
                snap.ram_used_pct = round((1 - avail_kb / max(total_kb, 1)) * 100, 1)
        elif os.name == 'nt':
            total_mb, avail_mb, used_pct = _win32_ram_ctypes()
            if total_mb > 0:
                snap.ram_total_mb = total_mb
                snap.ram_available_mb = avail_mb
                snap.ram_used_pct = used_pct
    except Exception as exc:
        logger.debug('RAM snapshot failed: %s', exc)

    # --- CPU load ---
    try:
        loadavg = Path('/proc/loadavg')
        if loadavg.exists():
            snap.cpu_load_1m = float(loadavg.read_text().split()[0])
        elif os.name == 'nt':
            snap.cpu_load_1m = _win32_cpu_pct()
    except Exception as exc:
        logger.debug('CPU snapshot failed: %s', exc)

    # Heavy processes (top memory consumers)
    try:
        if Path('/proc').exists():
            r = subprocess.run(
                ['ps', 'aux', '--sort=-rss'],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines()[1:6]:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        snap.heavy_processes.append({
                            'pid': parts[1],
                            'cpu_pct': float(parts[2]),
                            'mem_pct': float(parts[3]),
                            'rss_mb': int(parts[5]) // 1024,
                            'command': parts[10][:60],
                        })
        else:
            r = subprocess.run(
                ['powershell', '-Command',
                 'Get-Process | Sort-Object -Property WorkingSet -Descending '
                 '| Select-Object -First 5 -Property Name,Id,CPU,'
                 '@{N="MemMB";E={[math]::Round($_.WorkingSet/1MB)}} '
                 '| ConvertTo-Json'],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0 and r.stdout.strip():
                procs = json.loads(r.stdout)
                if isinstance(procs, dict):
                    procs = [procs]
                for p in procs[:5]:
                    snap.heavy_processes.append({
                        'pid': str(p.get('Id', '')),
                        'mem_mb': p.get('MemMB', 0),
                        'command': str(p.get('Name', ''))[:60],
                    })
    except Exception as exc:
        logger.debug('process snapshot failed: %s', exc)

    return snap


# ---------------------------------------------------------------------------
# USER ACTIVITY DETECTION
# ---------------------------------------------------------------------------

class UserActivityState(Enum):
    ACTIVE = 'active'       # user typing/clicking — max responsiveness
    IDLE_SHORT = 'idle_short'  # 30s-5min no activity — can do light background
    IDLE_LONG = 'idle_long'   # >5min — run heavy tasks
    ABSENT = 'absent'        # >15min — full background mode


@dataclass
class UserActivityTracker:
    """Tracks when the user last interacted to decide task scheduling."""
    _last_interaction: float = field(default_factory=time.time)
    _last_typing: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_interaction(self) -> None:
        with self._lock:
            self._last_interaction = time.time()

    def record_typing(self) -> None:
        with self._lock:
            now = time.time()
            self._last_typing = now
            self._last_interaction = now

    @property
    def state(self) -> UserActivityState:
        with self._lock:
            elapsed = time.time() - self._last_interaction
        if elapsed < 30:
            return UserActivityState.ACTIVE
        if elapsed < 300:
            return UserActivityState.IDLE_SHORT
        if elapsed < 900:
            return UserActivityState.IDLE_LONG
        return UserActivityState.ABSENT

    @property
    def seconds_since_last_interaction(self) -> float:
        with self._lock:
            return time.time() - self._last_interaction

    @property
    def is_typing(self) -> bool:
        with self._lock:
            return (time.time() - self._last_typing) < 5.0


# ---------------------------------------------------------------------------
# TASK PRIORITY QUEUE
# ---------------------------------------------------------------------------

class TaskPriority(Enum):
    CRITICAL = 0   # respond to user NOW
    HIGH = 1       # respond to user within seconds
    MEDIUM = 2     # analysis, learning — can defer 30s
    LOW = 3        # training, merges, deep analysis — defer to idle
    BACKGROUND = 4 # cleanup, cache warming — only when absent


@dataclass
class InternalTask:
    """A background task the program might run."""
    name: str
    priority: TaskPriority
    category: str  # 'response', 'analysis', 'training', 'merge', 'cleanup'
    estimated_ram_mb: int = 0
    estimated_duration_s: float = 0
    deferred: bool = False
    defer_reason: str = ''
    last_run: float = 0


class AdaptiveResourceOrchestrator:
    """Decides which internal tasks to run based on resources and user state.

    When the user is active (typing), the orchestrator:
      - Pauses LOW/BACKGROUND tasks
      - Limits MEDIUM tasks to lightweight operations
      - Gives full CPU/RAM to CRITICAL/HIGH (responding to user)

    When the user is idle/absent:
      - Resumes deferred tasks in priority order
      - Runs heavy operations (training, merges, deep analysis)
      - Monitors resource consumption to avoid freezes
    """

    def __init__(self, config_path: str | None = None) -> None:
        self._user_tracker = UserActivityTracker()
        self._task_queue: list[InternalTask] = []
        self._config_path = Path(config_path or '')
        self._lock = threading.Lock()
        self._learned_configs: dict[str, Any] = {}
        self._freeze_history: list[dict[str, Any]] = []
        self._bg_monitor = BackgroundResourceMonitor(interval_s=15.0)
        self._load_learned_configs()

    def start_monitoring(self) -> None:
        """Start background resource monitoring daemon."""
        self._bg_monitor.start()

    def stop_monitoring(self) -> None:
        """Stop background resource monitoring."""
        self._bg_monitor.stop()

    def record_user_typing(self) -> None:
        self._user_tracker.record_typing()

    def record_user_interaction(self) -> None:
        self._user_tracker.record_interaction()

    @property
    def user_state(self) -> UserActivityState:
        return self._user_tracker.state

    def should_run_task(self, task: InternalTask) -> tuple[bool, str]:
        """Decide if a task should run now or be deferred.

        Returns (should_run, reason).
        """
        user = self._user_tracker.state
        snap = take_resource_snapshot()

        # CRITICAL always runs
        if task.priority == TaskPriority.CRITICAL:
            return True, 'critical task — always runs'

        # If user is actively typing, only CRITICAL and HIGH run
        if self._user_tracker.is_typing:
            if task.priority.value > TaskPriority.HIGH.value:
                return False, 'usuario escribiendo — diferida para no afectar respuesta'

        # RAM pressure check
        if snap.ram_pressure == 'critical' and task.estimated_ram_mb > 100:
            self._record_resource_event('ram_pressure_defer', {
                'task': task.name, 'ram_used_pct': snap.ram_used_pct,
                'ram_available_mb': snap.ram_available_mb,
            })
            return False, f'RAM critica ({snap.ram_used_pct}%) — tarea pesada diferida'

        if snap.ram_pressure == 'high' and task.priority.value >= TaskPriority.LOW.value:
            return False, f'RAM alta ({snap.ram_used_pct}%) — tareas bajas diferidas'

        # CPU pressure
        if snap.cpu_pressure in ('critical', 'high') and task.priority.value >= TaskPriority.MEDIUM.value:
            return False, f'CPU sobrecargada — tareas medias/bajas diferidas'

        # User state vs task priority
        if user == UserActivityState.ACTIVE:
            if task.priority.value >= TaskPriority.LOW.value:
                return False, 'usuario activo — tareas de baja prioridad diferidas'

        if user == UserActivityState.IDLE_SHORT:
            if task.priority == TaskPriority.BACKGROUND:
                return False, 'inactividad corta — solo tareas de fondo para inactividad larga'

        # All checks passed
        return True, 'recursos disponibles y prioridad compatible'

    def get_scheduling_report(self) -> dict[str, Any]:
        """Generate a report of current task scheduling state for the auto-analysis."""
        snap = take_resource_snapshot()
        user = self._user_tracker.state

        deferred = [t for t in self._task_queue if t.deferred]
        runnable = [t for t in self._task_queue if not t.deferred]

        return {
            'resources': {
                'ram_total_mb': snap.ram_total_mb,
                'ram_available_mb': snap.ram_available_mb,
                'ram_used_pct': snap.ram_used_pct,
                'ram_pressure': snap.ram_pressure,
                'cpu_load': snap.cpu_load_1m,
                'cpu_count': snap.cpu_count,
                'cpu_pressure': snap.cpu_pressure,
                'heavy_processes': snap.heavy_processes[:3],
            },
            'user_state': user.value,
            'seconds_since_interaction': round(
                self._user_tracker.seconds_since_last_interaction, 1,
            ),
            'task_queue': {
                'total': len(self._task_queue),
                'deferred': len(deferred),
                'runnable': len(runnable),
                'deferred_tasks': [
                    {'name': t.name, 'reason': t.defer_reason}
                    for t in deferred[:5]
                ],
            },
            'freeze_history_count': len(self._freeze_history),
            'learned_configs': len(self._learned_configs),
            'monitoring': self._bg_monitor.get_history_summary(),
            'bottleneck_diagnoses': self._bg_monitor.get_bottleneck_diagnosis(),
        }

    def diagnose_freeze(self, duration_s: float) -> dict[str, Any]:
        """Self-diagnose a detected freeze/hang and record it for learning."""
        snap = take_resource_snapshot()
        diagnosis: dict[str, Any] = {
            'timestamp': time.time(),
            'freeze_duration_s': duration_s,
            'ram_at_freeze': snap.ram_used_pct,
            'cpu_at_freeze': snap.cpu_load_1m,
            'heavy_processes': snap.heavy_processes[:3],
            'probable_cause': 'unknown',
            'recommendation': '',
        }

        if snap.ram_pressure == 'critical':
            diagnosis['probable_cause'] = 'ram_exhaustion'
            diagnosis['recommendation'] = (
                'Reducir tareas paralelas y diferir entrenamiento/merges. '
                f'Solo {snap.ram_available_mb}MB libres de {snap.ram_total_mb}MB'
            )
        elif snap.cpu_pressure in ('critical', 'high'):
            diagnosis['probable_cause'] = 'cpu_saturation'
            diagnosis['recommendation'] = (
                f'CPU load {snap.cpu_load_1m:.1f} con {snap.cpu_count} cores. '
                'Reducir concurrencia de inferencia'
            )
        elif snap.heavy_processes:
            top = snap.heavy_processes[0]
            diagnosis['probable_cause'] = 'heavy_process'
            diagnosis['recommendation'] = (
                f'Proceso pesado: {top.get("command", "?")} '
                f'usando {top.get("mem_pct", top.get("mem_mb", "?"))} memoria'
            )
        else:
            diagnosis['probable_cause'] = 'ui_thread_block'
            diagnosis['recommendation'] = (
                'Posible bloqueo del hilo principal (QML). '
                'Verificar llamadas sincronas en hilo UI'
            )

        self._freeze_history.append(diagnosis)
        self._learn_from_freeze(diagnosis)

        return diagnosis

    def _record_resource_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Record a resource event for learning."""
        entry = {
            'type': event_type,
            'timestamp': time.time(),
            **data,
        }
        self._freeze_history.append(entry)
        if len(self._freeze_history) > 100:
            self._freeze_history = self._freeze_history[-50:]

    def _learn_from_freeze(self, diagnosis: dict[str, Any]) -> None:
        """Update learned configurations based on freeze diagnosis."""
        cause = diagnosis.get('probable_cause', '')
        if cause == 'ram_exhaustion':
            self._learned_configs['max_parallel_inference'] = max(
                1,
                self._learned_configs.get('max_parallel_inference', 3) - 1,
            )
            self._learned_configs['defer_training_when_ram_above'] = 70
        elif cause == 'cpu_saturation':
            self._learned_configs['max_parallel_tasks'] = max(
                1,
                self._learned_configs.get('max_parallel_tasks', 4) - 1,
            )
        self._save_learned_configs()

    def _load_learned_configs(self) -> None:
        """Load previously learned resource configurations."""
        cfg_file = self._config_path / 'resource_configs.json' if self._config_path else None
        if not cfg_file:
            return
        try:
            if cfg_file.exists():
                self._learned_configs = json.loads(cfg_file.read_text(encoding='utf-8'))
                logger.info('loaded %d learned resource configs', len(self._learned_configs))
        except Exception as exc:
            logger.debug('failed to load resource configs: %s', exc)

    def _save_learned_configs(self) -> None:
        """Persist learned configurations for future sessions."""
        cfg_file = self._config_path / 'resource_configs.json' if self._config_path else None
        if not cfg_file:
            return
        try:
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text(
                json.dumps(self._learned_configs, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.debug('failed to save resource configs: %s', exc)

    @property
    def learned_max_parallel_inference(self) -> int:
        return self._learned_configs.get('max_parallel_inference', 3)

    @property
    def learned_max_parallel_tasks(self) -> int:
        return self._learned_configs.get('max_parallel_tasks', 4)

    @property
    def defer_training_threshold(self) -> int:
        return self._learned_configs.get('defer_training_when_ram_above', 80)


# ---------------------------------------------------------------------------
# BACKGROUND RESOURCE MONITOR — lightweight daemon thread
# ---------------------------------------------------------------------------

class BackgroundResourceMonitor:
    """Lightweight daemon that periodically snapshots system resources.

    Runs as a background thread so the main program never blocks.
    Snapshots are stored in a ring buffer (last N entries). When the
    program is free (user idle, no urgent tasks), the holistic scan
    can inspect the history to detect:
      - Sustained high RAM pressure (trending toward OOM)
      - CPU spikes correlated with specific operations
      - Gradual memory leaks
      - Bottlenecks that caused UI freezes
    """

    def __init__(
        self,
        interval_s: float = 15.0,
        max_history: int = 60,
    ) -> None:
        self._interval = interval_s
        self._max_history = max_history
        self._history: list[ResourceSnapshot] = []
        self._anomalies: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._prev_ram_pct: float = 0.0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name='resource-monitor',
        )
        self._thread.start()
        logger.info('BackgroundResourceMonitor started (interval=%ss)', self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                snap = take_resource_snapshot()
                with self._lock:
                    self._history.append(snap)
                    if len(self._history) > self._max_history:
                        self._history = self._history[-self._max_history:]
                    self._detect_anomalies(snap)
            except Exception as exc:
                logger.debug('resource monitor tick failed: %s', exc)
            self._stop_event.wait(self._interval)

    def _detect_anomalies(self, snap: ResourceSnapshot) -> None:
        """Detect sudden spikes or dangerous trends."""
        # Sudden RAM spike (>15% increase in one interval)
        if self._prev_ram_pct > 0:
            delta = snap.ram_used_pct - self._prev_ram_pct
            if delta > 15:
                self._anomalies.append({
                    'type': 'ram_spike',
                    'timestamp': snap.timestamp,
                    'from_pct': self._prev_ram_pct,
                    'to_pct': snap.ram_used_pct,
                    'delta': round(delta, 1),
                })
        self._prev_ram_pct = snap.ram_used_pct

        # Critical threshold breach
        if snap.ram_pressure == 'critical':
            self._anomalies.append({
                'type': 'ram_critical',
                'timestamp': snap.timestamp,
                'ram_used_pct': snap.ram_used_pct,
                'ram_available_mb': snap.ram_available_mb,
            })

        # Trim anomaly history
        if len(self._anomalies) > 50:
            self._anomalies = self._anomalies[-25:]

    def get_history_summary(self) -> dict[str, Any]:
        """Summarize resource history for inspection when program is free."""
        with self._lock:
            if not self._history:
                return {'status': 'no_data', 'samples': 0}

            ram_pcts = [s.ram_used_pct for s in self._history]
            cpu_loads = [s.cpu_load_1m for s in self._history]

            return {
                'status': 'ok',
                'samples': len(self._history),
                'interval_s': self._interval,
                'ram': {
                    'current_pct': ram_pcts[-1],
                    'avg_pct': round(sum(ram_pcts) / len(ram_pcts), 1),
                    'max_pct': round(max(ram_pcts), 1),
                    'min_pct': round(min(ram_pcts), 1),
                    'trend': 'rising' if len(ram_pcts) > 3 and ram_pcts[-1] > ram_pcts[-3] + 5 else
                             'falling' if len(ram_pcts) > 3 and ram_pcts[-1] < ram_pcts[-3] - 5 else
                             'stable',
                },
                'cpu': {
                    'current_load': round(cpu_loads[-1], 2),
                    'avg_load': round(sum(cpu_loads) / len(cpu_loads), 2),
                    'max_load': round(max(cpu_loads), 2),
                },
                'anomalies': len(self._anomalies),
                'recent_anomalies': self._anomalies[-3:] if self._anomalies else [],
            }

    def get_bottleneck_diagnosis(self) -> list[dict[str, str]]:
        """Inspect collected history and diagnose bottlenecks.

        Called when the program is free (user idle) to analyze
        accumulated data without blocking the user.
        """
        with self._lock:
            history = list(self._history)
            anomalies = list(self._anomalies)

        if not history:
            return []

        diagnoses: list[dict[str, str]] = []

        # Check for sustained high RAM
        high_ram_samples = sum(1 for s in history if s.ram_used_pct > 80)
        if high_ram_samples > len(history) * 0.7:
            diagnoses.append({
                'severity': 'warning',
                'area': 'resource_bottleneck',
                'finding': (
                    f'RAM sostenidamente alta: >{80}% en {high_ram_samples}'
                    f'/{len(history)} muestras — posible memory leak o '
                    'demasiados procesos simultaneos'
                ),
                'action': 'investigate_memory_leak',
            })

        # Check for memory trend (leak detection)
        if len(history) >= 10:
            first_5_avg = sum(s.ram_used_pct for s in history[:5]) / 5
            last_5_avg = sum(s.ram_used_pct for s in history[-5:]) / 5
            if last_5_avg > first_5_avg + 10:
                diagnoses.append({
                    'severity': 'warning',
                    'area': 'resource_bottleneck',
                    'finding': (
                        f'Tendencia de RAM creciente: {first_5_avg:.0f}% → '
                        f'{last_5_avg:.0f}% — posible fuga de memoria'
                    ),
                    'action': 'check_memory_leaks',
                })

        # Check for repeated anomalies
        ram_spikes = [a for a in anomalies if a.get('type') == 'ram_spike']
        if len(ram_spikes) >= 3:
            diagnoses.append({
                'severity': 'warning',
                'area': 'resource_bottleneck',
                'finding': (
                    f'{len(ram_spikes)} picos de RAM detectados — '
                    'procesos internos causan oscilaciones de memoria'
                ),
                'action': 'review_batch_operations',
            })

        return diagnoses


# ---------------------------------------------------------------------------
# REPORT FORMATTING
# ---------------------------------------------------------------------------

def format_resource_report(report: dict[str, Any]) -> str:
    """Format the resource management data for the auto-analysis output."""
    lines: list[str] = []
    res = report.get('resources', {})

    lines.append('== RECURSOS DEL SISTEMA ==')
    lines.append(
        f'  RAM: {res.get("ram_used_pct", 0)}% usado '
        f'({res.get("ram_available_mb", 0)}MB libres de '
        f'{res.get("ram_total_mb", 0)}MB) '
        f'— presion: {res.get("ram_pressure", "?")}'
    )
    lines.append(
        f'  CPU: load {res.get("cpu_load", 0):.1f} '
        f'({res.get("cpu_count", 1)} cores) '
        f'— presion: {res.get("cpu_pressure", "?")}'
    )

    procs = res.get('heavy_processes', [])
    if procs:
        lines.append(f'  Procesos pesados: {len(procs)}')
        for p in procs[:3]:
            mem_info = p.get('mem_pct', p.get('mem_mb', '?'))
            if isinstance(mem_info, float):
                mem_str = f'{mem_info:.1f}%'
            else:
                mem_str = f'{mem_info}MB'
            lines.append(
                f'    - {p.get("command", "?")} '
                f'(PID {p.get("pid", "?")}, mem: {mem_str})'
            )

    lines.append('')
    lines.append('== ADMINISTRACION INTELIGENTE ==')
    lines.append(f'  Estado del usuario: {report.get("user_state", "?")}')
    lines.append(
        f'  Ultima interaccion: hace '
        f'{report.get("seconds_since_interaction", 0):.0f}s'
    )

    tq = report.get('task_queue', {})
    lines.append(
        f'  Cola de tareas: {tq.get("total", 0)} total, '
        f'{tq.get("runnable", 0)} ejecutables, '
        f'{tq.get("deferred", 0)} diferidas'
    )

    deferred = tq.get('deferred_tasks', [])
    if deferred:
        lines.append('  Tareas diferidas:')
        for t in deferred:
            lines.append(f'    - {t["name"]}: {t["reason"]}')

    freeze_count = report.get('freeze_history_count', 0)
    if freeze_count > 0:
        lines.append(f'  Congelamientos registrados: {freeze_count}')

    learned = report.get('learned_configs', 0)
    if learned > 0:
        lines.append(f'  Configuraciones aprendidas: {learned}')

    # Background monitoring history
    mon = report.get('monitoring', {})
    if mon.get('status') == 'ok' and mon.get('samples', 0) > 0:
        ram_mon = mon.get('ram', {})
        cpu_mon = mon.get('cpu', {})
        lines.append(f'  Monitoreo en fondo: {mon["samples"]} muestras (cada {mon.get("interval_s", 15)}s)')
        lines.append(
            f'    RAM: actual {ram_mon.get("current_pct", 0)}%, '
            f'promedio {ram_mon.get("avg_pct", 0)}%, '
            f'max {ram_mon.get("max_pct", 0)}%, '
            f'tendencia: {ram_mon.get("trend", "?")}'
        )
        lines.append(
            f'    CPU: actual {cpu_mon.get("current_load", 0):.1f}, '
            f'promedio {cpu_mon.get("avg_load", 0):.1f}, '
            f'max {cpu_mon.get("max_load", 0):.1f}'
        )
        anomaly_count = mon.get('anomalies', 0)
        if anomaly_count > 0:
            lines.append(f'    Anomalias detectadas: {anomaly_count}')
            for a in mon.get('recent_anomalies', [])[:3]:
                a_type = a.get('type', '?')
                if a_type == 'ram_spike':
                    lines.append(
                        f'      - Pico de RAM: {a.get("from_pct", 0):.0f}% → '
                        f'{a.get("to_pct", 0):.0f}% (+{a.get("delta", 0)}%)'
                    )
                elif a_type == 'ram_critical':
                    lines.append(
                        f'      - RAM critica: {a.get("ram_used_pct", 0):.0f}% '
                        f'({a.get("ram_available_mb", 0)}MB libres)'
                    )

    # Bottleneck diagnoses
    bottlenecks = report.get('bottleneck_diagnoses', [])
    if bottlenecks:
        lines.append('  Diagnostico de cuellos de botella:')
        for b in bottlenecks:
            icon = {'critical': 'CRITICO', 'warning': 'ALERTA', 'info': 'INFO'}.get(
                b.get('severity', 'info'), '?',
            )
            lines.append(f'    [{icon}] {b.get("finding", "?")}')
            if b.get('action') and b['action'] != 'none':
                lines.append(f'      Accion: {b["action"]}')

    return '\n'.join(lines)
