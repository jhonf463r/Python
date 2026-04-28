"""Resource metacognition service — observe, reason, act, learn about RAM/GPU/processes.

Metacognition cycle:
1. OBSERVE: read RAM, VRAM, top processes
2. REASON: calculate liberation plan (what to close, what model fits)
3. ACT: close safe processes, load optimal Ollama model
4. LEARN: record outcome, feed findings to OSES

Architecture:
- NOT another brain.  Feeds findings into OSES via ``oses_findings()``.
- Reutilizes ``_memory_snapshot()`` from EnvironmentSelfAwarenessService.
- Reutilizes ``gpu_metacognition`` for VRAM/GPU detection.
- Records decisions in ``DecisionAuditTrail``.
- Persists liberation history in ``data/evolution/resource_metacognition/``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

MODEL_RAM_REQUIREMENTS: dict[str, float] = {
    'gemma3:1b': 1.5,
    'gemma3:4b': 3.5,
    'qwen2.5-coder:7b': 5.0,
    'llama3.1:8b': 6.0,
    'qwen2.5-coder:14b': 10.0,
    'deepseek-coder-v2:16b': 12.0,
}

NEVER_CLOSE: frozenset[str] = frozenset({
    'python', 'pythonw', 'python3', 'ollama', 'iabv',
    'svchost', 'explorer', 'csrss', 'lsass', 'winlogon',
    'wininit', 'services', 'smss', 'dwm', 'conhost',
    'system', 'registry', 'fontdrvhost', 'sihost',
})

SAFE_TO_CLOSE_DEFAULT: frozenset[str] = frozenset({
    'chrome', 'opera', 'msedge', 'firefox', 'brave',
    'spotify', 'discord', 'teams', 'slack', 'steam',
    'epicgameslauncher', 'whatsapp', 'telegram',
    'notepad', 'notepad++', 'vlc', 'acrobat',
})


@dataclass
class ProcessInfo:
    name: str
    pid: int
    ram_mb: float

    def to_dict(self) -> dict[str, Any]:
        return {'name': self.name, 'pid': self.pid, 'ram_mb': self.ram_mb}


@dataclass
class ResourceSnapshot:
    timestamp_utc: str = ''
    ram_total_gb: float = 0.0
    ram_free_gb: float = 0.0
    ram_used_gb: float = 0.0
    vram_total_gb: float = 0.0
    vram_free_gb: float = 0.0
    models_loaded: list[dict[str, Any]] = field(default_factory=list)
    top_processes: list[ProcessInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'timestamp_utc': self.timestamp_utc,
            'ram_total_gb': self.ram_total_gb,
            'ram_free_gb': self.ram_free_gb,
            'ram_used_gb': self.ram_used_gb,
            'vram_total_gb': self.vram_total_gb,
            'vram_free_gb': self.vram_free_gb,
            'models_loaded': self.models_loaded,
            'top_processes': [p.to_dict() for p in self.top_processes],
        }


@dataclass
class LiberationPlan:
    should_liberate: bool = False
    processes_to_close: list[ProcessInfo] = field(default_factory=list)
    estimated_ram_freed_gb: float = 0.0
    target_model: str = ''
    target_model_ram_gb: float = 0.0
    current_free_gb: float = 0.0
    reason: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'should_liberate': self.should_liberate,
            'processes_to_close': [p.to_dict() for p in self.processes_to_close],
            'estimated_ram_freed_gb': self.estimated_ram_freed_gb,
            'target_model': self.target_model,
            'target_model_ram_gb': self.target_model_ram_gb,
            'current_free_gb': self.current_free_gb,
            'reason': self.reason,
        }

    def summary_text(self) -> str:
        if not self.should_liberate:
            return f'No es necesario liberar RAM. {self.reason}'
        names = ', '.join(p.name for p in self.processes_to_close[:5])
        return (
            f'Plan: cerrar [{names}] libera ~{self.estimated_ram_freed_gb:.1f}GB. '
            f'Con eso puedo cargar {self.target_model} (necesita {self.target_model_ram_gb:.1f}GB).'
        )


@dataclass
class LiberationResult:
    success: bool = False
    processes_closed: list[dict[str, Any]] = field(default_factory=list)
    processes_failed: list[dict[str, Any]] = field(default_factory=list)
    ram_freed_gb: float = 0.0
    selected_model: str = ''
    model_loaded: bool = False
    error: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'success': self.success,
            'processes_closed': self.processes_closed,
            'processes_failed': self.processes_failed,
            'ram_freed_gb': self.ram_freed_gb,
            'selected_model': self.selected_model,
            'model_loaded': self.model_loaded,
            'error': self.error,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ResourceMetacognitionService:
    """Metacognition service for RAM/GPU/process resource management."""

    def __init__(
        self,
        *,
        evolution_dir: str | Path,
        environment_service: Any = None,
        experiment_lab: Any = None,
        decision_audit_trail: Any = None,
    ) -> None:
        self._evolution_dir = Path(evolution_dir)
        self._data_dir = self._evolution_dir / 'resource_metacognition'
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._history_path = self._data_dir / 'liberation_history.jsonl'
        self._learned_closeable_path = self._data_dir / 'learned_closeable.json'

        self._environment_service = environment_service
        self._experiment_lab = experiment_lab
        self._decision_audit_trail = decision_audit_trail

        self._learned_closeable: set[str] = self._load_learned_closeable()

    # ------------------------------------------------------------------
    # 1. OBSERVE
    # ------------------------------------------------------------------

    def observe_resources(self) -> ResourceSnapshot:
        """Observe current system resources: RAM, VRAM, top processes."""
        snap = ResourceSnapshot(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

        # RAM via environment service (reutilize _memory_snapshot)
        ram = self._get_ram_info()
        snap.ram_total_gb = ram.get('total_bytes', 0) / (1024 ** 3)
        snap.ram_free_gb = ram.get('free_bytes', 0) / (1024 ** 3)
        snap.ram_used_gb = ram.get('used_bytes', 0) / (1024 ** 3)

        # VRAM via gpu_metacognition
        vram = self._get_vram_info()
        snap.vram_total_gb = vram.get('vram_total_gb', 0.0)
        snap.vram_free_gb = vram.get('vram_free_gb', 0.0)
        snap.models_loaded = vram.get('models', [])

        # Top processes by RAM
        snap.top_processes = self._get_top_processes(limit=15)

        return snap

    def _get_ram_info(self) -> dict[str, Any]:
        """Get RAM info, reutilizing EnvironmentSelfAwarenessService if available."""
        if self._environment_service is not None:
            try:
                return self._environment_service._memory_snapshot()
            except Exception as exc:
                logger.debug('resource_metacognition: env service memory failed: %s', exc)

        # Fallback: cross-platform RAM detection
        if os.name == 'nt':
            return self._win32_memory_snapshot()
        return self._linux_memory_snapshot()

    @staticmethod
    def _win32_memory_snapshot() -> dict[str, Any]:
        """Read RAM via Win32 GlobalMemoryStatusEx."""
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
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {}
            used = int(status.ullTotalPhys - status.ullAvailPhys)
            return {
                'total_bytes': int(status.ullTotalPhys),
                'free_bytes': int(status.ullAvailPhys),
                'used_bytes': used,
            }
        except Exception:
            return {}

    @staticmethod
    def _linux_memory_snapshot() -> dict[str, Any]:
        """Read RAM from /proc/meminfo (Linux fallback)."""
        try:
            with open('/proc/meminfo') as f:
                lines = f.readlines()
            info: dict[str, int] = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    val = int(parts[1]) * 1024  # kB -> bytes
                    info[key] = val
            total = info.get('MemTotal', 0)
            free = info.get('MemAvailable', info.get('MemFree', 0))
            return {
                'total_bytes': total,
                'free_bytes': free,
                'used_bytes': total - free,
            }
        except Exception:
            return {}

    @staticmethod
    def _get_vram_info() -> dict[str, Any]:
        """Get VRAM info via gpu_metacognition and ollama ps."""
        result: dict[str, Any] = {'vram_total_gb': 0.0, 'vram_free_gb': 0.0, 'models': []}
        try:
            from iabv_v15.services.gpu_metacognition import detect_physical_gpus, detect_ollama_gpu_state
            gpus = detect_physical_gpus()
            nvidia = [g for g in gpus if g.get('type') == 'nvidia']
            if nvidia:
                vram_bytes = nvidia[0].get('vram_bytes', 0)
                result['vram_total_gb'] = vram_bytes / (1024 ** 3) if vram_bytes else 0.0

            ollama = detect_ollama_gpu_state()
            if ollama.get('status') == 'ok':
                result['models'] = ollama.get('models', [])
        except Exception as exc:
            logger.debug('resource_metacognition: vram info failed: %s', exc)
        return result

    @staticmethod
    def _get_top_processes(limit: int = 15) -> list[ProcessInfo]:
        """Get top RAM-consuming processes."""
        processes: list[ProcessInfo] = []
        if os.name == 'nt':
            processes = ResourceMetacognitionService._win32_top_processes(limit)
        else:
            processes = ResourceMetacognitionService._linux_top_processes(limit)
        return processes

    @staticmethod
    def _win32_top_processes(limit: int) -> list[ProcessInfo]:
        """Get top processes via tasklist on Windows."""
        try:
            result = subprocess.run(
                ['tasklist', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return []
            procs: list[ProcessInfo] = []
            for line in result.stdout.strip().splitlines():
                parts = line.strip('"').split('","')
                if len(parts) >= 5:
                    name = parts[0].lower().replace('.exe', '')
                    try:
                        pid = int(parts[1])
                    except (ValueError, IndexError):
                        continue
                    mem_str = parts[4].replace('"', '').replace(',', '').replace('.', '')
                    mem_str = re.sub(r'[^\d]', '', mem_str)
                    try:
                        ram_kb = int(mem_str)
                    except ValueError:
                        ram_kb = 0
                    procs.append(ProcessInfo(name=name, pid=pid, ram_mb=ram_kb / 1024))
            procs.sort(key=lambda p: p.ram_mb, reverse=True)
            return procs[:limit]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    @staticmethod
    def _linux_top_processes(limit: int) -> list[ProcessInfo]:
        """Get top processes via ps on Linux."""
        try:
            result = subprocess.run(
                ['ps', 'aux', '--sort=-rss'],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return []
            procs: list[ProcessInfo] = []
            for line in result.stdout.strip().splitlines()[1:limit + 1]:
                parts = line.split()
                if len(parts) >= 11:
                    try:
                        pid = int(parts[1])
                        rss_kb = int(parts[5])
                    except (ValueError, IndexError):
                        continue
                    name = parts[10].split('/')[-1].lower()
                    procs.append(ProcessInfo(name=name, pid=pid, ram_mb=rss_kb / 1024))
            return procs
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    # ------------------------------------------------------------------
    # 2. REASON
    # ------------------------------------------------------------------

    def analyze_liberation_plan(self, snapshot: ResourceSnapshot) -> LiberationPlan:
        """Analyze snapshot and produce a liberation plan."""
        plan = LiberationPlan(current_free_gb=snapshot.ram_free_gb)

        # Determine best model that could fit with current RAM
        target_model = self.select_optimal_model(snapshot.ram_free_gb)
        needed_ram = MODEL_RAM_REQUIREMENTS.get(target_model, 0.0)

        if target_model and snapshot.ram_free_gb >= needed_ram:
            plan.should_liberate = False
            plan.target_model = target_model
            plan.target_model_ram_gb = needed_ram
            plan.reason = (
                f'RAM libre ({snapshot.ram_free_gb:.1f}GB) suficiente para '
                f'{target_model} ({needed_ram:.1f}GB). No hace falta liberar.'
            )
            return plan

        # Need to liberate: find the best model we could run after liberation
        best_model, best_ram_needed = self._best_achievable_model(snapshot)
        if not best_model:
            plan.should_liberate = False
            plan.reason = 'No hay modelo alcanzable ni cerrando todos los procesos seguros.'
            return plan

        # Identify closeable processes
        closeable = self._identify_closeable_processes(snapshot.top_processes)
        ram_deficit = best_ram_needed - snapshot.ram_free_gb

        selected: list[ProcessInfo] = []
        accumulated = 0.0
        for proc in closeable:
            if accumulated >= ram_deficit:
                break
            selected.append(proc)
            accumulated += proc.ram_mb / 1024

        if accumulated < ram_deficit * 0.5:
            plan.should_liberate = False
            plan.reason = (
                f'Cerrar procesos seguros libera solo ~{accumulated:.1f}GB, '
                f'insuficiente para {best_model} ({best_ram_needed:.1f}GB).'
            )
            return plan

        plan.should_liberate = True
        plan.processes_to_close = selected
        plan.estimated_ram_freed_gb = accumulated
        plan.target_model = best_model
        plan.target_model_ram_gb = best_ram_needed
        plan.reason = (
            f'Cerrar {len(selected)} procesos libera ~{accumulated:.1f}GB. '
            f'Con eso puedo cargar {best_model} ({best_ram_needed:.1f}GB).'
        )
        return plan

    def _best_achievable_model(
        self, snapshot: ResourceSnapshot,
    ) -> tuple[str, float]:
        """Find the best model achievable after closing safe processes."""
        closeable = self._identify_closeable_processes(snapshot.top_processes)
        max_freeable = sum(p.ram_mb / 1024 for p in closeable)
        potential_free = snapshot.ram_free_gb + max_freeable

        # Sort models by RAM descending — pick the largest that fits
        sorted_models = sorted(
            MODEL_RAM_REQUIREMENTS.items(), key=lambda x: x[1], reverse=True,
        )

        # Check ExperimentLab for historical performance
        lab_preferred = self._lab_preferred_model()

        for model_name, ram_needed in sorted_models:
            if ram_needed <= potential_free:
                # If lab says a smaller model is better, prefer it
                if lab_preferred and lab_preferred != model_name:
                    lab_ram = MODEL_RAM_REQUIREMENTS.get(lab_preferred, 0.0)
                    if lab_ram <= potential_free:
                        return lab_preferred, lab_ram
                return model_name, ram_needed

        return '', 0.0

    def _identify_closeable_processes(
        self, processes: list[ProcessInfo],
    ) -> list[ProcessInfo]:
        """Identify processes safe to close, sorted by RAM descending."""
        closeable: list[ProcessInfo] = []
        all_safe = SAFE_TO_CLOSE_DEFAULT | self._learned_closeable
        for proc in processes:
            base_name = proc.name.lower().replace('.exe', '')
            if base_name in NEVER_CLOSE:
                continue
            if base_name in all_safe:
                closeable.append(proc)
        closeable.sort(key=lambda p: p.ram_mb, reverse=True)
        return closeable

    def _lab_preferred_model(self) -> str:
        """Check ExperimentLab for historically best-performing model."""
        if self._experiment_lab is None:
            return ''
        try:
            results = self._experiment_lab.recent_results(
                scope_key='ollama_model_selection', limit=10,
            )
            if not results:
                return ''
            # Count wins per model
            wins: dict[str, int] = {}
            for r in results:
                model = r.get('model', '') or r.get('metadata', {}).get('model', '')
                if model and r.get('success'):
                    wins[model] = wins.get(model, 0) + 1
            if wins:
                return max(wins, key=wins.get)  # type: ignore[arg-type]
        except Exception as exc:
            logger.debug('resource_metacognition: lab query failed: %s', exc)
        return ''

    # ------------------------------------------------------------------
    # 3. ACT
    # ------------------------------------------------------------------

    def execute_liberation(
        self,
        plan: LiberationPlan,
        mode: str = 'auto',
    ) -> LiberationResult:
        """Execute the liberation plan.

        Args:
            plan: The liberation plan to execute.
            mode: 'auto' closes without asking, 'ask' requires confirmation.
        """
        result = LiberationResult()

        if not plan.should_liberate:
            result.success = True
            result.selected_model = plan.target_model
            return result

        if mode == 'ask':
            result.error = 'mode=ask requires UI confirmation (not executed)'
            return result

        # Record decision in audit trail
        self._record_decision(
            phase='resource_liberation',
            provider_id='resource_metacognition',
            user_goal='liberar RAM para modelo Ollama',
            metadata=plan.to_dict(),
        )

        # Close processes
        ram_before = self._get_ram_info().get('free_bytes', 0) / (1024 ** 3)

        for proc in plan.processes_to_close:
            closed = self._kill_process(proc)
            entry = proc.to_dict()
            if closed:
                result.processes_closed.append(entry)
                self._mark_learned_closeable(proc.name)
            else:
                result.processes_failed.append(entry)

        # Measure freed RAM
        time.sleep(1)  # Give OS time to reclaim
        ram_after = self._get_ram_info().get('free_bytes', 0) / (1024 ** 3)
        result.ram_freed_gb = max(0.0, ram_after - ram_before)

        # Select and load optimal model
        result.selected_model = self.select_optimal_model(ram_after)
        if result.selected_model:
            result.model_loaded = self._ensure_model_loaded(result.selected_model)

        result.success = len(result.processes_closed) > 0
        return result

    @staticmethod
    def _kill_process(proc: ProcessInfo) -> bool:
        """Kill a process by PID."""
        if os.name == 'nt':
            try:
                r = subprocess.run(
                    ['taskkill', '/PID', str(proc.pid), '/F'],
                    capture_output=True, text=True, timeout=10,
                )
                return r.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        else:
            try:
                os.kill(proc.pid, 9)
                return True
            except (ProcessLookupError, PermissionError):
                return False

    @staticmethod
    def _ensure_model_loaded(model_name: str) -> bool:
        """Pull model if needed and warm it up."""
        try:
            # Check if already available
            r = subprocess.run(
                ['ollama', 'list'],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0 and model_name in r.stdout:
                logger.info('resource_metacognition: model %s already available', model_name)
                return True

            # Pull the model
            logger.info('resource_metacognition: pulling model %s', model_name)
            r = subprocess.run(
                ['ollama', 'pull', model_name],
                capture_output=True, text=True, timeout=300,
            )
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning('resource_metacognition: model load failed: %s', exc)
            return False

    def _mark_learned_closeable(self, name: str) -> None:
        """Add a process name to learned_closeable list."""
        base = name.lower().replace('.exe', '')
        if base not in SAFE_TO_CLOSE_DEFAULT and base not in NEVER_CLOSE:
            self._learned_closeable.add(base)
            self._save_learned_closeable()

    # ------------------------------------------------------------------
    # 4. LEARN
    # ------------------------------------------------------------------

    def record_outcome(self, result: LiberationResult) -> None:
        """Record liberation outcome for future learning."""
        record = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            **result.to_dict(),
        }
        try:
            with open(self._history_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as exc:
            logger.warning('resource_metacognition: history write failed: %s', exc)

    def _load_learned_closeable(self) -> set[str]:
        """Load learned_closeable from disk."""
        try:
            if self._learned_closeable_path.exists():
                data = json.loads(self._learned_closeable_path.read_text(encoding='utf-8'))
                return set(data) if isinstance(data, list) else set()
        except Exception:
            pass
        return set()

    def _save_learned_closeable(self) -> None:
        """Save learned_closeable to disk."""
        try:
            self._learned_closeable_path.write_text(
                json.dumps(sorted(self._learned_closeable), ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.debug('resource_metacognition: save learned failed: %s', exc)

    def recent_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Read recent liberation history records."""
        records: list[dict[str, Any]] = []
        try:
            if self._history_path.exists():
                lines = self._history_path.read_text(encoding='utf-8').strip().splitlines()
                for line in lines[-limit:]:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return records

    # ------------------------------------------------------------------
    # 5. AUTO-SELECTION
    # ------------------------------------------------------------------

    def select_optimal_model(self, available_ram_gb: float) -> str:
        """Select the best Ollama model that fits in available RAM.

        Prefers the largest model that fits, unless ExperimentLab says
        a smaller model historically performed better.
        """
        sorted_models = sorted(
            MODEL_RAM_REQUIREMENTS.items(), key=lambda x: x[1], reverse=True,
        )

        lab_preferred = self._lab_preferred_model()

        for model_name, ram_needed in sorted_models:
            if ram_needed <= available_ram_gb:
                if lab_preferred and lab_preferred != model_name:
                    lab_ram = MODEL_RAM_REQUIREMENTS.get(lab_preferred, 0.0)
                    if lab_ram <= available_ram_gb:
                        return lab_preferred
                return model_name

        # Fallback: smallest model
        if sorted_models:
            smallest = min(sorted_models, key=lambda x: x[1])
            if smallest[1] <= available_ram_gb:
                return smallest[0]
        return ''

    # ------------------------------------------------------------------
    # OSES findings
    # ------------------------------------------------------------------

    def oses_findings(self) -> list[dict[str, Any]]:
        """Generate findings for OperationalSelfExaminationService."""
        findings: list[dict[str, Any]] = []
        try:
            snapshot = self.observe_resources()

            if snapshot.ram_free_gb < 2.0:
                findings.append({
                    'category': 'resource_metacognition',
                    'title': f'RAM critica: {snapshot.ram_free_gb:.1f}GB libre de {snapshot.ram_total_gb:.1f}GB',
                    'summary': (
                        f'Solo {snapshot.ram_free_gb:.1f}GB de RAM disponible. '
                        f'Modelos Ollama grandes no caben. '
                        f'Se recomienda liberar RAM cerrando procesos innecesarios.'
                    ),
                    'severity': 'HIGH',
                    'confidence': 0.95,
                    'recommendation': 'Ejecutar liberacion automatica de RAM',
                    'metadata': {
                        'ram_free_gb': snapshot.ram_free_gb,
                        'ram_total_gb': snapshot.ram_total_gb,
                        'actionable': True,
                    },
                })
            elif snapshot.ram_free_gb < 3.0:
                findings.append({
                    'category': 'resource_metacognition',
                    'title': f'RAM bajo presion: {snapshot.ram_free_gb:.1f}GB libre',
                    'summary': (
                        f'{snapshot.ram_free_gb:.1f}GB de RAM disponible. '
                        f'Solo modelos pequenos caben.'
                    ),
                    'severity': 'MEDIUM',
                    'confidence': 0.9,
                    'recommendation': 'Considerar liberar RAM si se necesita un modelo mas grande',
                    'metadata': {
                        'ram_free_gb': snapshot.ram_free_gb,
                        'ram_total_gb': snapshot.ram_total_gb,
                        'actionable': False,
                    },
                })

            # Recent liberation outcomes
            history = self.recent_history(limit=3)
            if history:
                last = history[-1]
                if not last.get('success'):
                    findings.append({
                        'category': 'resource_metacognition',
                        'title': 'Ultima liberacion fallo',
                        'summary': f'Error: {last.get("error", "desconocido")}',
                        'severity': 'LOW',
                        'confidence': 0.8,
                        'recommendation': 'Revisar procesos bloqueados manualmente',
                        'metadata': {'actionable': False},
                    })

        except Exception as exc:
            logger.debug('resource_metacognition: oses_findings failed: %s', exc)

        return findings

    # ------------------------------------------------------------------
    # Chat integration helpers
    # ------------------------------------------------------------------

    def chat_observe_and_plan(self) -> str:
        """For chat: observe resources and show plan summary."""
        snapshot = self.observe_resources()
        plan = self.analyze_liberation_plan(snapshot)

        lines: list[str] = []
        lines.append(f'== Estado de Recursos ==')
        lines.append(f'RAM: {snapshot.ram_used_gb:.1f}GB usada / {snapshot.ram_total_gb:.1f}GB total ({snapshot.ram_free_gb:.1f}GB libre)')

        if snapshot.top_processes:
            lines.append('')
            lines.append('Top procesos por RAM:')
            for p in snapshot.top_processes[:8]:
                lines.append(f'  {p.name}: {p.ram_mb:.0f}MB (PID {p.pid})')

        if snapshot.models_loaded:
            lines.append('')
            lines.append('Modelos Ollama cargados:')
            for m in snapshot.models_loaded:
                lines.append(f'  {m.get("name", "?")} — GPU {m.get("gpu_percent", 0)}%')

        lines.append('')
        lines.append(f'Modelo optimo para RAM actual: {plan.target_model or "ninguno"}')
        lines.append('')
        lines.append(plan.summary_text())

        return '\n'.join(lines)

    def chat_execute_liberation(self) -> str:
        """For chat: execute full liberation cycle."""
        snapshot = self.observe_resources()
        plan = self.analyze_liberation_plan(snapshot)

        if not plan.should_liberate:
            return plan.summary_text()

        result = self.execute_liberation(plan, mode='auto')
        self.record_outcome(result)

        lines: list[str] = []
        if result.success:
            lines.append(f'Liberacion completada:')
            lines.append(f'  Procesos cerrados: {len(result.processes_closed)}')
            if result.processes_closed:
                names = ', '.join(p.get('name', '?') for p in result.processes_closed[:5])
                lines.append(f'  Cerrados: {names}')
            lines.append(f'  RAM liberada: ~{result.ram_freed_gb:.1f}GB')
            lines.append(f'  Modelo seleccionado: {result.selected_model}')
            lines.append(f'  Modelo cargado: {"si" if result.model_loaded else "no"}')
        else:
            lines.append(f'Liberacion fallo: {result.error or "sin procesos cerrados"}')

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_decision(self, **kwargs: Any) -> None:
        """Record a decision in the audit trail if available."""
        if self._decision_audit_trail is None:
            return
        try:
            self._decision_audit_trail.record(**kwargs)
        except Exception as exc:
            logger.debug('resource_metacognition: audit trail record failed: %s', exc)
