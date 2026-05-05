from __future__ import annotations

import ctypes
import hashlib
import importlib.metadata as importlib_metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import tomllib
from typing import Any

from iabv_v15.domain.models import (
    EnvironmentCapability,
    EnvironmentRiskSignal,
    EnvironmentSelfModel,
    IssueSeverity,
    ProviderHealth,
    utc_now,
)


class EnvironmentSelfAwarenessService:
    """Background observer that keeps a lightweight self-model of the current environment."""

    _CPU_WARNING_PCT = 85.0
    _RAM_WARNING_BYTES = 3 * 1024**3
    _RAM_CRITICAL_BYTES = 2 * 1024**3
    _DISK_WARNING_BYTES = 20 * 1024**3
    _DISK_CRITICAL_BYTES = 10 * 1024**3
    _GPU_TEMP_WARNING_C = 80.0
    _GPU_TEMP_CRITICAL_C = 85.0
    _DEFAULT_SCAN_INTERVAL = 90.0
    _DEFAULT_FULL_SCAN_INTERVAL = 480.0
    _POWERSHELL_TIMEOUT_SECONDS = 1.0
    _TYPEPERF_TIMEOUT_SECONDS = 1.5
    _GPU_QUERY_TIMEOUT_SECONDS = 1.5
    _OLLAMA_LIST_TIMEOUT_SECONDS = 2.0

    def __init__(
        self,
        *,
        workspace_root: str,
        evolution_dir: str,
        role_router: Any | None = None,
        tool_registry: Any | None = None,
        auto_start: bool | None = None,
        bootstrap_scan: bool = True,
        scan_interval_seconds: float = _DEFAULT_SCAN_INTERVAL,
        full_scan_interval_seconds: float = _DEFAULT_FULL_SCAN_INTERVAL,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.project_root = self._resolve_project_root(self.workspace_root)
        self.state_dir = Path(evolution_dir).resolve() / 'environment_self_model'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.role_router = role_router
        self.tool_registry = tool_registry
        self.scan_interval_seconds = max(float(scan_interval_seconds), 15.0)
        self.full_scan_interval_seconds = max(float(full_scan_interval_seconds), self.scan_interval_seconds)
        self._auto_start = (not self._in_test_mode()) if auto_start is None else bool(auto_start)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._refresh_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending_refresh_reason = 'scheduled_light'
        self._pending_full_refresh = False
        self._last_scan_monotonic = 0.0
        self._last_full_scan_monotonic = 0.0
        self._current_model = self._load_latest_model() or EnvironmentSelfModel(scan_status='bootstrapping')
        if bootstrap_scan:
            # Fix 15: always do a *light* scan during bootstrap.  A full scan
            # calls PowerShell/nvidia-smi/ollama-list/typeperf — each with
            # subprocess timeouts that add 15-25s on Windows.  The first full
            # scan will run when the background thread triggers it (after
            # full_scan_interval_seconds) or on the next manual request_refresh.
            self.scan_now(reason='startup', full=False)
            # Schedule the first full scan to run as soon as the background
            # thread starts, rather than waiting for full_scan_interval_seconds.
            self._pending_full_refresh = True
        if self._auto_start:
            self.start()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name='iabv-environment-self-awareness', daemon=True)
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 1.0) -> None:
        self._stop_event.set()
        self._refresh_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(timeout_seconds, 0.1))

    def current_model(self) -> EnvironmentSelfModel:
        with self._lock:
            return self._current_model.model_copy(deep=True)

    def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> EnvironmentSelfModel:
        with self._lock:
            if full:
                self._pending_full_refresh = True
            self._pending_refresh_reason = str(reason or 'manual')
            too_soon = (time.monotonic() - self._last_scan_monotonic) < 10.0
            if too_soon and not full and self._thread is not None and self._thread.is_alive():
                return self._current_model.model_copy(deep=True)
        if self._thread is not None and self._thread.is_alive():
            self._refresh_event.set()
            return self.current_model()
        return self.scan_now(reason=reason, full=full)

    def scan_now(self, *, reason: str = 'manual', full: bool = False) -> EnvironmentSelfModel:
        previous = self.current_model()
        model = self._build_model(previous=previous, reason=reason, full=full)
        with self._lock:
            self._current_model = model
            now_monotonic = time.monotonic()
            self._last_scan_monotonic = now_monotonic
            if full:
                self._last_full_scan_monotonic = now_monotonic
        self._persist_model(model)
        return model.model_copy(deep=True)

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            triggered = self._refresh_event.wait(self.scan_interval_seconds)
            if self._stop_event.is_set():
                break
            if triggered:
                self._refresh_event.clear()
            with self._lock:
                full = self._pending_full_refresh or (
                    (time.monotonic() - self._last_full_scan_monotonic) >= self.full_scan_interval_seconds
                )
                reason = self._pending_refresh_reason if triggered else ('scheduled_full' if full else 'scheduled_light')
                self._pending_full_refresh = False
                self._pending_refresh_reason = 'scheduled_light'
            try:
                self.scan_now(reason=reason, full=full)
            except Exception:
                with self._lock:
                    self._current_model = self._current_model.model_copy(
                        update={
                            'scan_status': 'degraded',
                            'notifications': list(dict.fromkeys(list(self._current_model.notifications) + ['No pude refrescar el entorno en segundo plano.'])),
                        }
                    )

    def _build_model(self, *, previous: EnvironmentSelfModel, reason: str, full: bool) -> EnvironmentSelfModel:
        hardware_profile, hardware_unresolved = self._scan_hardware(full=full)
        runtime_profile, runtime_unresolved = self._scan_runtime(full=full)
        provider_health: list[ProviderHealth]
        if full:
            provider_health = self._provider_health()
        else:
            cached_provider_health = self._provider_health_from_previous(previous)
            provider_health = cached_provider_health if cached_provider_health else self._provider_health()
        available_tools, missing_tools = self._tool_cards()
        ai_capacity, ai_unresolved = self._scan_ai_capacity(hardware_profile=hardware_profile, runtime_profile=runtime_profile, full=full)
        capability_graph = self._build_capability_graph(
            runtime_profile=runtime_profile,
            provider_health=provider_health,
            available_tools=available_tools,
            missing_tools=missing_tools,
            ai_capacity=ai_capacity,
        )
        risk_signals = self._build_risk_signals(
            hardware_profile=hardware_profile,
            runtime_profile=runtime_profile,
            provider_health=provider_health,
            missing_tools=missing_tools,
            ai_capacity=ai_capacity,
        )
        environment_id = self._environment_id(hardware_profile=hardware_profile, runtime_profile=runtime_profile)
        previous_environment_id = str(previous.environment_id or '')
        known_environment = self._environment_path(environment_id).exists()
        installable_tools = self._build_installable_tools(runtime_profile=runtime_profile, missing_tools=missing_tools)
        changed_since_last_scan = self._diff_from_previous(
            previous=previous,
            environment_id=environment_id,
            provider_health=provider_health,
            available_tools=available_tools,
            missing_tools=missing_tools,
            ai_capacity=ai_capacity,
            risk_signals=risk_signals,
        )
        notifications = self._build_notifications(
            known_environment=known_environment,
            previous_environment_id=previous_environment_id,
            environment_id=environment_id,
            changed_since_last_scan=changed_since_last_scan,
            risk_signals=risk_signals,
        )
        unresolved_fields = list(dict.fromkeys([*hardware_unresolved, *runtime_unresolved, *ai_unresolved]))
        metadata = {
            'scan_reason': str(reason or 'manual'),
            'scan_mode': 'full' if full else 'light',
            'project_root': str(self.project_root),
            'workspace_root': str(self.workspace_root),
            'provider_health': [item.model_dump(mode='json') for item in provider_health],
            'previous_environment_id': previous_environment_id,
            'known_environment_path': str(self._environment_path(environment_id)),
            'latest_model_path': str(self._latest_model_path()),
        }
        if previous_environment_id and previous_environment_id != environment_id:
            metadata['environment_transition'] = {'from': previous_environment_id, 'to': environment_id}
        return EnvironmentSelfModel(
            environment_id=environment_id,
            known_environment=known_environment,
            scan_status='ready' if not unresolved_fields else 'partial',
            hardware_profile=hardware_profile,
            runtime_profile=runtime_profile,
            capability_graph=capability_graph,
            available_tools=available_tools,
            missing_tools=missing_tools,
            installable_tools=installable_tools,
            ai_capacity=ai_capacity,
            risk_signals=risk_signals,
            notifications=notifications,
            last_scan=utc_now(),
            changed_since_last_scan=changed_since_last_scan,
            unresolved_fields=unresolved_fields,
            metadata=metadata,
        )

    def _provider_health_from_previous(self, previous: EnvironmentSelfModel) -> list[ProviderHealth]:
        payload = previous.metadata.get('provider_health') if isinstance(previous.metadata, dict) else None
        if not isinstance(payload, list):
            return []
        recovered: list[ProviderHealth] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                recovered.append(ProviderHealth.model_validate(item))
            except Exception:
                continue
        return recovered

    def _scan_hardware(self, *, full: bool) -> tuple[dict[str, Any], list[str]]:
        unresolved: list[str] = []
        memory = self._memory_snapshot()
        disk = self._disk_snapshot()
        cpu_info = self._cpu_snapshot(full=full)
        gpu_info = self._gpu_snapshot(full=full)
        battery_info = self._battery_snapshot(full=full)
        hardware = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'machine': platform.machine(),
            'processor_name': cpu_info.get('name') or platform.processor(),
            'physical_cores': cpu_info.get('physical_cores'),
            'logical_cores': cpu_info.get('logical_cores') or os.cpu_count() or 0,
            'current_clock_mhz': cpu_info.get('current_clock_mhz'),
            'max_clock_mhz': cpu_info.get('max_clock_mhz'),
            'cpu_usage_percent': cpu_info.get('cpu_usage_percent'),
            'cpu_temperature_c': cpu_info.get('cpu_temperature_c'),
            'memory_total_bytes': memory.get('total_bytes'),
            'memory_free_bytes': memory.get('free_bytes'),
            'memory_used_bytes': memory.get('used_bytes'),
            'memory_usage_ratio': memory.get('usage_ratio'),
            'disk_total_bytes': disk.get('total_bytes'),
            'disk_free_bytes': disk.get('free_bytes'),
            'disk_usage_ratio': disk.get('usage_ratio'),
            'gpu_name': gpu_info.get('name'),
            'gpu_driver': gpu_info.get('driver'),
            'gpu_memory_total_mb': gpu_info.get('memory_total_mb'),
            'gpu_memory_free_mb': gpu_info.get('memory_free_mb'),
            'gpu_temperature_c': gpu_info.get('temperature_c'),
            'gpu_utilization_pct': gpu_info.get('utilization_pct'),
            'battery_percent': battery_info.get('percent'),
            'battery_status': battery_info.get('status'),
            'throttling_detected': self._detect_throttling(cpu_info=cpu_info, gpu_info=gpu_info),
        }
        sensors_not_available: list[dict[str, str]] = []
        is_windows = os.name == 'nt'
        # cpu_temperature: no hay una fuente confiable y universal para leer la
        # temperatura de CPU desde Python estandar. Si viene None, no es "falla
        # del sensor" sino que el host no lo expone por esta via.
        if hardware.get('cpu_temperature_c') is None:
            sensors_not_available.append(
                {'sensor': 'cpu_temperature', 'reason': 'sensor_not_exposed_on_this_host'}
            )
        # gpu_temperature si ya reportamos gpu_name: hay GPU NVIDIA pero la
        # query fallo -> sigue siendo UNRESOLVED real.
        if hardware.get('gpu_name') and hardware.get('gpu_temperature_c') is None:
            unresolved.append('UNRESOLVED:gpu_temperature')
        # battery: hardware opcional (desktops no tienen bateria). Si la query
        # no devuelve nada, lo tratamos como "no expuesto" en vez de UNRESOLVED.
        if hardware.get('battery_percent') is None:
            sensors_not_available.append(
                {'sensor': 'battery_status', 'reason': 'sensor_not_exposed_on_this_host'}
            )
        # cpu_frequency: Win32_Processor puede exponer CurrentClockSpeed/
        # MaxClockSpeed en Windows, pero no siempre lo hace (depende del
        # driver y la configuración del host).  Tratamos la ausencia como
        # sensor no expuesto en cualquier plataforma.
        if hardware.get('current_clock_mhz') is None or hardware.get('max_clock_mhz') is None:
            sensors_not_available.append(
                {'sensor': 'cpu_frequency', 'reason': 'sensor_not_exposed_on_this_host'}
            )
        if sensors_not_available:
            hardware['sensors_not_available'] = sensors_not_available
        return hardware, unresolved

    def _scan_runtime(self, *, full: bool) -> tuple[dict[str, Any], list[str]]:
        unresolved: list[str] = []
        packages = self._installed_packages(full=full)
        dependency_status = self._project_dependency_status(packages=packages)
        runtime = {
            'python_executable': sys.executable,
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'conda_prefix': os.getenv('CONDA_PREFIX', ''),
            'virtual_env': os.getenv('VIRTUAL_ENV', ''),
            'workspace_root': str(self.workspace_root),
            'project_root': str(self.project_root),
            'workspace_writeable': self._workspace_writeable(),
            'workspace_exists': self.workspace_root.exists(),
            'repo_paths': {
                'src': str(self.project_root / 'src'),
                'tests': str(self.project_root / 'tests'),
                'venv': str(self.workspace_root / '.venv'),
                'vendor_deps': str(self.workspace_root / '.vendor_deps'),
            },
            'package_count': len(packages),
            'packages_present': sorted(
                package for package in ('pytest', 'PySide6', 'httpx', 'Pillow', 'playwright', 'keyring', 'pydantic') if package.lower() in packages
            ),
            'missing_project_dependencies': dependency_status['missing'],
            'project_dependencies_checked': dependency_status['checked'],
        }
        if dependency_status['source'] == 'unresolved':
            unresolved.append('UNRESOLVED:project_dependencies')
        return runtime, unresolved

    def _provider_health(self) -> list[ProviderHealth]:
        if self.role_router is None or not hasattr(self.role_router, 'health_snapshot'):
            return []
        try:
            return list(self.role_router.health_snapshot())
        except Exception:
            return []

    def _tool_cards(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        available: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        if self.tool_registry is None:
            return available, missing
        try:
            cards = [self.tool_registry.refresh_card(card, max_age_seconds=120.0) for card in self.tool_registry.list_cards()]
        except Exception:
            return available, missing
        for card in cards:
            payload = {
                'tool_id': card.tool_id,
                'title': card.title,
                'tool_type': card.tool_type.value if hasattr(card.tool_type, 'value') else str(card.tool_type),
                'available': bool(card.available),
                'assistant_kind': str(card.metadata.get('assistant_kind') or ''),
                'launch_mode': str(card.metadata.get('launch_mode') or ''),
                'supports_write': bool(card.supports_write),
                'supports_sandbox': bool(card.supports_sandbox),
            }
            if card.available:
                available.append(payload)
            else:
                missing.append(payload)
        return available, missing

    def _scan_ai_capacity(
        self,
        *,
        hardware_profile: dict[str, Any],
        runtime_profile: dict[str, Any],
        full: bool,
    ) -> tuple[dict[str, Any], list[str]]:
        unresolved: list[str] = []
        vram_mb = int(hardware_profile.get('gpu_memory_total_mb') or 0)
        ram_total = int(hardware_profile.get('memory_total_bytes') or 0)
        ram_free = int(hardware_profile.get('memory_free_bytes') or 0)
        has_gpu = bool(vram_mb)
        if vram_mb >= 6000 and ram_total >= 15 * 1024**3:
            safe_models = ['embedding <= 1B', '4B safe', '8B with caution']
            max_recommended = '8B q4/q5'
        elif ram_total >= 12 * 1024**3:
            safe_models = ['embedding <= 1B', '4B safe']
            max_recommended = '4B q4/q5'
        else:
            safe_models = ['embedding <= 1B', '3B-4B only']
            max_recommended = '4B q4 low-context'
        ollama = self._ollama_inventory(full=full)
        if not ollama['available']:
            unresolved.append('UNRESOLVED:ollama_inventory')
        ai_capacity = {
            'preferred_local_assistant_kind': 'ollama',
            'execution_mode': 'gpu_mixed' if has_gpu else 'cpu_only',
            'gpu_available': has_gpu,
            'gpu_memory_total_mb': vram_mb,
            'safe_models': safe_models,
            'max_recommended_model': max_recommended,
            'local_runtime': ollama,
            'memory_headroom_gb': round(ram_free / (1024**3), 2) if ram_free else 0.0,
            'avoid_heavy_models': ram_free < self._RAM_WARNING_BYTES or vram_mb < 6000,
        }
        return ai_capacity, unresolved

    def _build_capability_graph(
        self,
        *,
        runtime_profile: dict[str, Any],
        provider_health: list[ProviderHealth],
        available_tools: list[dict[str, Any]],
        missing_tools: list[dict[str, Any]],
        ai_capacity: dict[str, Any],
    ) -> list[EnvironmentCapability]:
        capabilities: list[EnvironmentCapability] = [
            EnvironmentCapability(
                capability_id='runtime.python',
                title='Python activo',
                available=bool(runtime_profile.get('python_executable')),
                status='ready' if runtime_profile.get('python_executable') else 'missing',
                summary=str(runtime_profile.get('python_version') or ''),
                evidence_refs=[str(runtime_profile.get('python_executable') or '')],
            ),
            EnvironmentCapability(
                capability_id='runtime.workspace_write',
                title='Workspace editable',
                available=bool(runtime_profile.get('workspace_writeable')),
                status='ready' if runtime_profile.get('workspace_writeable') else 'blocked',
                summary='Permisos de escritura sobre el workspace actual.',
            ),
            EnvironmentCapability(
                capability_id='ai.local_models',
                title='IA local utilizable',
                available=bool(ai_capacity.get('local_runtime', {}).get('available') or ai_capacity.get('safe_models')),
                status='ready' if ai_capacity.get('safe_models') else 'missing',
                summary=str(ai_capacity.get('max_recommended_model') or ''),
            ),
        ]
        for health in provider_health:
            capabilities.append(
                EnvironmentCapability(
                    capability_id=f'provider.{health.provider_name.lower().replace(" ", "_")}',
                    title=f'Proveedor {health.provider_name}',
                    available=bool(health.available),
                    status=health.status.value,
                    summary=health.detail,
                    evidence_refs=[health.provider_name],
                )
            )
        for tool in available_tools[:12]:
            capabilities.append(
                EnvironmentCapability(
                    capability_id=f'tool.{tool["tool_id"]}',
                    title=tool['title'],
                    available=True,
                    status='ready',
                    summary=f"{tool.get('tool_type') or 'tool'} via {tool.get('launch_mode') or 'n/d'}",
                    evidence_refs=[tool['tool_id']],
                )
            )
        for tool in missing_tools[:6]:
            capabilities.append(
                EnvironmentCapability(
                    capability_id=f'tool.{tool["tool_id"]}',
                    title=tool['title'],
                    available=False,
                    status='missing',
                    summary='La herramienta sigue registrada, pero no esta lista en este entorno.',
                    evidence_refs=[tool['tool_id']],
                )
            )
        capabilities.extend(self._windows_platform_capabilities())
        return capabilities

    # ------------------------------------------------------------------
    # Windows-native capability discovery (Fix 18a)
    # ------------------------------------------------------------------

    def _windows_platform_capabilities(self) -> list[EnvironmentCapability]:
        """Detect Windows-native capabilities and return them as graph entries.

        Runs lightweight probes that do NOT shell out to PowerShell — each
        check is pure-Python or ctypes-based so it adds < 1ms to the scan.
        Capabilities that cannot be confirmed are marked ``missing`` so
        OSES and PortableContext can register them as structured pendientes.
        """
        if os.name != 'nt':
            return [
                EnvironmentCapability(
                    capability_id='platform.windows',
                    title='Windows nativo',
                    available=False,
                    status='not_applicable',
                    summary='El entorno actual no es Windows.',
                ),
            ]

        caps: list[EnvironmentCapability] = []

        # 1. OS version + edition
        win_ver = self._windows_version_detail()
        caps.append(EnvironmentCapability(
            capability_id='platform.windows',
            title='Windows nativo',
            available=True,
            status='ready',
            summary=win_ver.get('edition', platform.platform()),
            evidence_refs=[win_ver.get('version', '')],
            metadata=win_ver,
        ))

        # 2. User paths (AppData, Documents, etc.)
        user_paths = self._windows_user_paths()
        caps.append(EnvironmentCapability(
            capability_id='platform.windows_user_paths',
            title='Rutas de usuario Windows',
            available=bool(user_paths.get('appdata_local')),
            status='ready' if user_paths.get('appdata_local') else 'missing',
            summary=f"LOCALAPPDATA={user_paths.get('appdata_local', 'N/A')}",
            metadata=user_paths,
        ))

        # 3. PowerShell availability
        ps = shutil.which('powershell') or shutil.which('pwsh')
        caps.append(EnvironmentCapability(
            capability_id='platform.windows_shell',
            title='PowerShell disponible',
            available=bool(ps),
            status='ready' if ps else 'missing',
            summary=str(ps or 'No encontrado'),
            evidence_refs=[str(ps)] if ps else [],
        ))

        # 4. Clipboard access
        clip_ok = self._windows_clipboard_available()
        caps.append(EnvironmentCapability(
            capability_id='platform.clipboard',
            title='Clipboard Win32',
            available=clip_ok,
            status='ready' if clip_ok else 'missing',
            summary='OpenClipboard/CloseClipboard via user32' if clip_ok else 'No se pudo verificar clipboard',
        ))

        # 5. Window enumeration (user32)
        user32_ok = self._windows_user32_available()
        caps.append(EnvironmentCapability(
            capability_id='platform.window_enumeration',
            title='Enumeracion de ventanas Win32',
            available=user32_ok,
            status='ready' if user32_ok else 'missing',
            summary='user32.EnumWindows disponible' if user32_ok else 'user32 no cargado',
        ))

        # 6. Notification support (Windows 10+ toast)
        notif = self._windows_notification_support()
        caps.append(EnvironmentCapability(
            capability_id='platform.notifications',
            title='Notificaciones Windows',
            available=notif['available'],
            status=notif['status'],
            summary=notif['summary'],
            metadata=notif.get('metadata', {}),
        ))

        # 7. Autostart capability (shell:startup folder exists)
        autostart = self._windows_autostart_capability()
        caps.append(EnvironmentCapability(
            capability_id='platform.autostart',
            title='Autostart al login',
            available=autostart['available'],
            status=autostart['status'],
            summary=autostart['summary'],
            evidence_refs=autostart.get('evidence_refs', []),
        ))

        # 8. Process management (CREATE_NO_WINDOW, subprocess)
        caps.append(EnvironmentCapability(
            capability_id='platform.process_management',
            title='Gestion de procesos Win32',
            available=True,
            status='ready',
            summary='subprocess + CREATE_NO_WINDOW disponible',
        ))

        return caps

    def _windows_version_detail(self) -> dict[str, Any]:
        """Detect detailed Windows version, build number, and edition."""
        info: dict[str, Any] = {
            'version': platform.version(),
            'release': platform.release(),
            'machine': platform.machine(),
        }
        try:
            ver = sys.getwindowsversion()  # type: ignore[attr-defined]
            info['major'] = ver.major
            info['minor'] = ver.minor
            info['build'] = ver.build
            info['service_pack'] = ver.service_pack
            info['platform_version'] = f'{ver.major}.{ver.minor}.{ver.build}'
        except Exception:
            pass
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:
                edition = winreg.QueryValueEx(key, 'ProductName')[0]
                info['edition'] = str(edition)
                try:
                    display_version = winreg.QueryValueEx(key, 'DisplayVersion')[0]
                    info['display_version'] = str(display_version)
                except Exception:
                    pass
        except Exception:
            info['edition'] = platform.platform()
        return info

    def _windows_user_paths(self) -> dict[str, str]:
        """Detect standard Windows user paths."""
        paths: dict[str, str] = {}
        env_map = {
            'userprofile': 'USERPROFILE',
            'appdata_roaming': 'APPDATA',
            'appdata_local': 'LOCALAPPDATA',
            'temp': 'TEMP',
            'home_drive': 'HOMEDRIVE',
            'home_path': 'HOMEPATH',
            'program_data': 'ProgramData',
        }
        for key, env_var in env_map.items():
            val = os.environ.get(env_var, '')
            if val:
                paths[key] = val
        documents = Path.home() / 'Documents'
        if documents.is_dir():
            paths['documents'] = str(documents)
        downloads = Path.home() / 'Downloads'
        if downloads.is_dir():
            paths['downloads'] = str(downloads)
        return paths

    def _windows_clipboard_available(self) -> bool:
        """Check if Win32 clipboard API is accessible."""
        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            if user32.OpenClipboard(0):
                user32.CloseClipboard()
                return True
        except Exception:
            pass
        return False

    def _windows_user32_available(self) -> bool:
        """Check if user32 is loadable for window enumeration."""
        try:
            u32 = ctypes.windll.user32  # type: ignore[attr-defined]
            return bool(u32.GetDesktopWindow())
        except Exception:
            return False

    def _windows_notification_support(self) -> dict[str, Any]:
        """Check for Windows 10+ toast notification support."""
        result: dict[str, Any] = {'available': False, 'status': 'missing', 'summary': '', 'metadata': {}}
        try:
            ver = sys.getwindowsversion()  # type: ignore[attr-defined]
            is_win10_plus = ver.major >= 10
        except Exception:
            is_win10_plus = False
        if not is_win10_plus:
            result['summary'] = 'Requiere Windows 10+'
            return result
        try:
            from importlib.util import find_spec
            has_winrt = find_spec('winrt') is not None or find_spec('winsdk') is not None
            has_plyer = find_spec('plyer') is not None
            has_winotify = find_spec('winotify') is not None
        except Exception:
            has_winrt = has_plyer = has_winotify = False
        if has_winrt or has_plyer or has_winotify:
            lib = 'winrt' if has_winrt else ('plyer' if has_plyer else 'winotify')
            result.update(available=True, status='ready', summary=f'Toast via {lib}')
            result['metadata'] = {'library': lib, 'winrt': has_winrt, 'plyer': has_plyer, 'winotify': has_winotify}
        else:
            result['summary'] = 'Windows 10+ pero sin libreria de toast (winrt/plyer/winotify)'
            result['status'] = 'missing_dependency'
            result['metadata'] = {'windows_10_plus': True, 'missing': 'winrt, plyer, o winotify'}
        return result

    def _windows_autostart_capability(self) -> dict[str, Any]:
        """Check if the shell:startup folder is accessible."""
        result: dict[str, Any] = {'available': False, 'status': 'missing', 'summary': '', 'evidence_refs': []}
        startup_folder = Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
        if startup_folder.is_dir():
            result['available'] = True
            result['status'] = 'ready'
            result['summary'] = f'shell:startup accesible en {startup_folder}'
            result['evidence_refs'] = [str(startup_folder)]
        else:
            result['summary'] = 'shell:startup no encontrado o no accesible'
        return result

    def _build_risk_signals(
        self,
        *,
        hardware_profile: dict[str, Any],
        runtime_profile: dict[str, Any],
        provider_health: list[ProviderHealth],
        missing_tools: list[dict[str, Any]],
        ai_capacity: dict[str, Any],
    ) -> list[EnvironmentRiskSignal]:
        risks: list[EnvironmentRiskSignal] = []
        memory_free = int(hardware_profile.get('memory_free_bytes') or 0)
        disk_free = int(hardware_profile.get('disk_free_bytes') or 0)
        cpu_usage = float(hardware_profile.get('cpu_usage_percent') or 0.0)
        gpu_temp = hardware_profile.get('gpu_temperature_c')
        if memory_free and memory_free <= self._RAM_CRITICAL_BYTES:
            risks.append(EnvironmentRiskSignal(kind='ram_critical', severity=IssueSeverity.CRITICAL, summary='La RAM libre cayo a una zona critica; evita lanzar tareas pesadas.', metric_value=round(memory_free / (1024**3), 2), threshold=round(self._RAM_CRITICAL_BYTES / (1024**3), 2)))
        elif memory_free and memory_free <= self._RAM_WARNING_BYTES:
            risks.append(EnvironmentRiskSignal(kind='ram_pressure', severity=IssueSeverity.HIGH, summary='La RAM libre esta baja para rutas pesadas o varios modelos locales a la vez.', metric_value=round(memory_free / (1024**3), 2), threshold=round(self._RAM_WARNING_BYTES / (1024**3), 2)))
        if disk_free and disk_free <= self._DISK_CRITICAL_BYTES:
            risks.append(EnvironmentRiskSignal(kind='disk_critical', severity=IssueSeverity.CRITICAL, summary='El disco libre esta en una zona critica para capturas, modelos o artefactos.', metric_value=round(disk_free / (1024**3), 2), threshold=round(self._DISK_CRITICAL_BYTES / (1024**3), 2)))
        elif disk_free and disk_free <= self._DISK_WARNING_BYTES:
            risks.append(EnvironmentRiskSignal(kind='disk_pressure', severity=IssueSeverity.MEDIUM, summary='El disco libre esta justo; conviene evitar cargas o descargas grandes.', metric_value=round(disk_free / (1024**3), 2), threshold=round(self._DISK_WARNING_BYTES / (1024**3), 2)))
        if cpu_usage >= self._CPU_WARNING_PCT:
            risks.append(EnvironmentRiskSignal(kind='cpu_pressure', severity=IssueSeverity.HIGH, summary='La CPU esta con carga sostenida alta; conviene evitar rutas pesadas mientras se estabiliza.', metric_value=round(cpu_usage, 2), threshold=self._CPU_WARNING_PCT))
        if isinstance(gpu_temp, (int, float)) and gpu_temp >= self._GPU_TEMP_CRITICAL_C:
            risks.append(EnvironmentRiskSignal(kind='gpu_temperature_critical', severity=IssueSeverity.CRITICAL, summary='La GPU supero el umbral termico seguro para sesiones largas.', metric_value=gpu_temp, threshold=self._GPU_TEMP_CRITICAL_C))
        elif isinstance(gpu_temp, (int, float)) and gpu_temp >= self._GPU_TEMP_WARNING_C:
            risks.append(EnvironmentRiskSignal(kind='gpu_temperature_warning', severity=IssueSeverity.HIGH, summary='La GPU esta caliente; conviene bajar la carga antes de abrir mas trabajo visual o modelos.', metric_value=gpu_temp, threshold=self._GPU_TEMP_WARNING_C))
        if bool(hardware_profile.get('throttling_detected')):
            risks.append(EnvironmentRiskSignal(kind='throttling_detected', severity=IssueSeverity.HIGH, summary='El reloj actual sugiere throttling bajo carga; evita tareas pesadas hasta que baje la presion.'))
        if runtime_profile.get('missing_project_dependencies'):
            risks.append(EnvironmentRiskSignal(kind='runtime_dependencies_missing', severity=IssueSeverity.MEDIUM, summary='Faltan dependencias del proyecto en el interprete activo.', metric_value=len(runtime_profile.get('missing_project_dependencies') or []), metadata={'packages': list(runtime_profile.get('missing_project_dependencies') or [])}))
        for health in provider_health:
            if not health.available:
                risks.append(EnvironmentRiskSignal(kind=f'provider_unavailable:{health.provider_name.lower()}', severity=IssueSeverity.MEDIUM, summary=f'El proveedor {health.provider_name} no esta disponible en este entorno.', metadata={'provider': health.provider_name, 'detail': health.detail}))
        for tool in missing_tools[:4]:
            risks.append(EnvironmentRiskSignal(kind=f'tool_missing:{tool["tool_id"]}', severity=IssueSeverity.LOW, summary=f'La herramienta {tool["title"]} no esta lista en este entorno.', metadata={'tool_id': tool['tool_id']}))
        if bool(ai_capacity.get('avoid_heavy_models')):
            risks.append(EnvironmentRiskSignal(kind='heavy_local_models_discouraged', severity=IssueSeverity.MEDIUM, summary='El entorno actual no esta en condiciones ideales para modelos locales pesados.', metadata={'max_recommended_model': ai_capacity.get('max_recommended_model')}))
        return risks

    def _build_installable_tools(self, *, runtime_profile: dict[str, Any], missing_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        installable: list[dict[str, Any]] = []
        for package in runtime_profile.get('missing_project_dependencies') or []:
            installable.append({'kind': 'python_dependency', 'name': package, 'safe_to_install': package in {'httpx', 'playwright', 'keyring', 'Pillow'}, 'summary': f'Paquete faltante en el interprete activo: {package}.'})
        for tool in missing_tools:
            installable.append({'kind': 'tool_runtime', 'name': tool['tool_id'], 'safe_to_install': False, 'summary': f"La herramienta {tool['title']} sigue registrada pero no esta disponible en esta laptop o interprete."})
        return installable[:12]

    def _build_notifications(
        self,
        *,
        known_environment: bool,
        previous_environment_id: str,
        environment_id: str,
        changed_since_last_scan: list[str],
        risk_signals: list[EnvironmentRiskSignal],
    ) -> list[str]:
        notifications: list[str] = []
        if not known_environment:
            notifications.append('Entorno nuevo detectado: el cerebro corrio un escaneo base antes de decidir.')
        if previous_environment_id and previous_environment_id != environment_id:
            notifications.append('Cambio de laptop o runtime detectado; se ajustaron capacidades segun el nuevo entorno.')
        for risk in risk_signals:
            if risk.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL}:
                notifications.append(risk.summary)
        if changed_since_last_scan:
            notifications.append(f'Cambios relevantes desde el ultimo escaneo: {", ".join(changed_since_last_scan[:4])}.')
        return notifications[:6]

    def _diff_from_previous(
        self,
        *,
        previous: EnvironmentSelfModel,
        environment_id: str,
        provider_health: list[ProviderHealth],
        available_tools: list[dict[str, Any]],
        missing_tools: list[dict[str, Any]],
        ai_capacity: dict[str, Any],
        risk_signals: list[EnvironmentRiskSignal],
    ) -> list[str]:
        if not previous.environment_id:
            return []
        changes: list[str] = []
        if previous.environment_id != environment_id:
            changes.append('environment_id')
        previous_available = {item.get('tool_id') for item in previous.available_tools}
        current_available = {item.get('tool_id') for item in available_tools}
        for tool_id in sorted(current_available - previous_available):
            changes.append(f'tool_available:{tool_id}')
        for tool_id in sorted(previous_available - current_available):
            changes.append(f'tool_missing:{tool_id}')
        previous_missing = {item.get('tool_id') for item in previous.missing_tools}
        current_missing = {item.get('tool_id') for item in missing_tools}
        for tool_id in sorted(current_missing - previous_missing):
            changes.append(f'tool_now_missing:{tool_id}')
        previous_provider = {str(item.get('provider_name') or ''): str(item.get('status') or '') for item in (previous.metadata.get('provider_health') or []) if isinstance(item, dict)}
        for item in provider_health:
            current_status = item.status.value
            if previous_provider.get(item.provider_name) != current_status:
                changes.append(f'provider:{item.provider_name}->{current_status}')
        previous_model = str(previous.ai_capacity.get('max_recommended_model') or '')
        current_model = str(ai_capacity.get('max_recommended_model') or '')
        if previous_model and current_model and previous_model != current_model:
            changes.append(f'ai_capacity:{current_model}')
        previous_risks = {f'{risk.kind}:{risk.severity.value}' for risk in previous.risk_signals}
        current_risks = {f'{risk.kind}:{risk.severity.value}' for risk in risk_signals}
        for risk in sorted(current_risks - previous_risks):
            changes.append(f'risk:{risk}')
        return changes[:12]

    def _resolve_project_root(self, workspace_root: Path) -> Path:
        if (workspace_root / 'pyproject.toml').exists():
            return workspace_root
        return Path(__file__).resolve().parents[4]

    def _latest_model_path(self) -> Path:
        return self.state_dir / 'latest.json'

    def _environment_path(self, environment_id: str) -> Path:
        return self.state_dir / f'{environment_id or "unknown"}.json'

    def _load_latest_model(self) -> EnvironmentSelfModel | None:
        path = self._latest_model_path()
        if not path.exists():
            return None
        try:
            return EnvironmentSelfModel.model_validate_json(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def _persist_model(self, model: EnvironmentSelfModel) -> None:
        payload = json.dumps(model.model_dump(mode='json'), ensure_ascii=True, indent=2)
        self._latest_model_path().write_text(payload, encoding='utf-8')
        self._environment_path(model.environment_id).write_text(payload, encoding='utf-8')

    def _environment_id(self, *, hardware_profile: dict[str, Any], runtime_profile: dict[str, Any]) -> str:
        material = {
            'hostname': hardware_profile.get('hostname'),
            'machine': hardware_profile.get('machine'),
            'processor_name': hardware_profile.get('processor_name'),
            'memory_total_bytes': hardware_profile.get('memory_total_bytes'),
            'gpu_name': hardware_profile.get('gpu_name'),
            'python_executable': runtime_profile.get('python_executable'),
        }
        digest = hashlib.sha1(json.dumps(material, sort_keys=True, ensure_ascii=True).encode('utf-8')).hexdigest()[:12]
        prefix = re.sub(r'[^a-z0-9]+', '-', str(hardware_profile.get('hostname') or 'env').lower()).strip('-')[:18]
        return f'{prefix or "env"}-{digest}'

    def _workspace_writeable(self) -> bool:
        try:
            probe = self.workspace_root / '.environment_self_model_probe'
            probe.write_text('ok', encoding='utf-8')
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def _installed_packages(self, *, full: bool) -> set[str]:
        try:
            if self._in_test_mode() and not full:
                names = set()
                for package in ('pytest', 'pydantic', 'PySide6'):
                    try:
                        importlib_metadata.version(package)
                        names.add(package.lower())
                    except importlib_metadata.PackageNotFoundError:
                        continue
                return names
            return {dist.metadata.get('Name', '').lower() for dist in importlib_metadata.distributions() if dist.metadata.get('Name')}
        except Exception:
            return set()

    def _project_dependency_status(self, *, packages: set[str]) -> dict[str, Any]:
        path = self.project_root / 'pyproject.toml'
        if not path.exists():
            return {'checked': [], 'missing': [], 'source': 'unresolved'}
        try:
            payload = tomllib.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return {'checked': [], 'missing': [], 'source': 'unresolved'}
        dependencies = list(payload.get('project', {}).get('dependencies') or [])
        checked: list[str] = []
        missing: list[str] = []
        import_aliases = {'pillow': 'PIL'}
        for raw in dependencies:
            name = self._normalize_dependency_name(raw)
            if not name:
                continue
            checked.append(name)
            normalized = name.lower()
            installed = normalized in packages
            if not installed and normalized in import_aliases:
                try:
                    __import__(import_aliases[normalized])
                    installed = True
                except Exception:
                    installed = False
            if not installed:
                missing.append(name)
        return {'checked': checked, 'missing': missing, 'source': 'pyproject'}

    def _normalize_dependency_name(self, raw: str) -> str:
        text = str(raw or '').strip()
        if not text:
            return ''
        match = re.match(r'([A-Za-z0-9_.-]+)', text)
        return match.group(1) if match else ''

    def _memory_snapshot(self) -> dict[str, Any]:
        if os.name != 'nt':
            return {}

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
            'usage_ratio': round((used / int(status.ullTotalPhys)), 4) if status.ullTotalPhys else 0.0,
        }

    def _disk_snapshot(self) -> dict[str, Any]:
        usage = shutil.disk_usage(self.workspace_root.anchor or self.workspace_root)
        used = usage.total - usage.free
        return {
            'total_bytes': int(usage.total),
            'free_bytes': int(usage.free),
            'used_bytes': int(used),
            'usage_ratio': round(used / usage.total, 4) if usage.total else 0.0,
        }

    def _cpu_snapshot(self, *, full: bool) -> dict[str, Any]:
        snapshot: dict[str, Any] = {'logical_cores': os.cpu_count() or 0}
        if self._in_test_mode() and not full:
            snapshot['name'] = platform.processor() or ''
            return snapshot
        processor_json = self._powershell_json(
            "Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors,CurrentClockSpeed,MaxClockSpeed | ConvertTo-Json -Compress"
        )
        if isinstance(processor_json, dict):
            snapshot.update(
                {
                    'name': processor_json.get('Name'),
                    'physical_cores': processor_json.get('NumberOfCores'),
                    'logical_cores': processor_json.get('NumberOfLogicalProcessors') or snapshot.get('logical_cores'),
                    'current_clock_mhz': processor_json.get('CurrentClockSpeed'),
                    'max_clock_mhz': processor_json.get('MaxClockSpeed'),
                }
            )
        cpu_usage = self._cpu_usage_percent()
        if cpu_usage is not None:
            snapshot['cpu_usage_percent'] = cpu_usage
        return snapshot

    def _gpu_snapshot(self, *, full: bool) -> dict[str, Any]:
        if self._in_test_mode() and not full:
            return {}
        nvidia = shutil.which('nvidia-smi')
        if not nvidia:
            return {}
        result = self._run_command(
            [
                nvidia,
                '--query-gpu=name,driver_version,temperature.gpu,memory.total,memory.used,utilization.gpu',
                '--format=csv,noheader,nounits',
            ],
            timeout_seconds=self._GPU_QUERY_TIMEOUT_SECONDS,
        )
        if not result or result.get('returncode') != 0:
            return {}
        lines = str(result.get('stdout') or '').strip().splitlines()
        if not lines:
            return {}
        parts = [item.strip() for item in lines[0].split(',')]
        if len(parts) < 6:
            return {}
        try:
            memory_total = int(float(parts[3]))
            memory_used = int(float(parts[4]))
            utilization = float(parts[5])
            temperature = float(parts[2])
        except ValueError:
            return {'name': parts[0], 'driver': parts[1]}
        return {
            'name': parts[0],
            'driver': parts[1],
            'temperature_c': temperature,
            'memory_total_mb': memory_total,
            'memory_used_mb': memory_used,
            'memory_free_mb': max(memory_total - memory_used, 0),
            'utilization_pct': utilization,
        }

    def _battery_snapshot(self, *, full: bool) -> dict[str, Any]:
        if os.name != 'nt' or (self._in_test_mode() and not full):
            return {}
        payload = self._powershell_json(
            "Get-CimInstance Win32_Battery | Select-Object -First 1 EstimatedChargeRemaining,BatteryStatus | ConvertTo-Json -Compress"
        )
        if not isinstance(payload, dict):
            return {}
        return {'percent': payload.get('EstimatedChargeRemaining'), 'status': payload.get('BatteryStatus')}

    def _cpu_usage_percent(self) -> float | None:
        if os.name != 'nt':
            return None
        result = self._run_command(
            ['typeperf', r'\Processor(_Total)\% Processor Time', '-sc', '1'],
            timeout_seconds=self._TYPEPERF_TIMEOUT_SECONDS,
        )
        if not result or result.get('returncode') != 0:
            return None
        match = re.search(r'"([0-9]+(?:\.[0-9]+)?)"\s*$', str(result.get('stdout') or '').replace(',', '.').strip(), re.MULTILINE)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    def _detect_throttling(self, *, cpu_info: dict[str, Any], gpu_info: dict[str, Any]) -> bool:
        current_clock = float(cpu_info.get('current_clock_mhz') or 0.0)
        max_clock = float(cpu_info.get('max_clock_mhz') or 0.0)
        cpu_usage = float(cpu_info.get('cpu_usage_percent') or 0.0)
        if current_clock and max_clock and cpu_usage >= 70.0 and current_clock < (max_clock * 0.65):
            return True
        gpu_util = float(gpu_info.get('utilization_pct') or 0.0)
        gpu_temp = float(gpu_info.get('temperature_c') or 0.0)
        return bool(gpu_util >= 85.0 and gpu_temp >= self._GPU_TEMP_WARNING_C)

    def _ollama_inventory(self, *, full: bool) -> dict[str, Any]:
        if self._in_test_mode() and not full:
            return {'available': False, 'models': [], 'detail': 'test-mode-skip'}
        candidates = [
            shutil.which('ollama') or '',
            str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Ollama' / 'ollama.exe'),
        ]
        ollama = next((candidate for candidate in candidates if self._path_exists(candidate)), '')
        if not ollama:
            return {'available': False, 'models': [], 'detail': 'ollama_not_found'}
        result = self._run_command([ollama, 'list'], timeout_seconds=self._OLLAMA_LIST_TIMEOUT_SECONDS)
        if not result or result.get('returncode') != 0:
            return {'available': False, 'models': [], 'detail': 'ollama_list_failed'}
        models: list[dict[str, str]] = []
        for line in str(result.get('stdout') or '').splitlines()[1:]:
            parts = [item for item in re.split(r'\s{2,}', line.strip()) if item]
            if not parts:
                continue
            models.append({'name': parts[0], 'size': parts[2] if len(parts) > 2 else ''})
        return {'available': True, 'path': ollama, 'models': models[:12], 'detail': 'ready' if models else 'installed_without_models'}

    def _powershell_json(self, command: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        shell = shutil.which('powershell') or shutil.which('pwsh')
        if not shell:
            return None
        result = self._run_command([shell, '-Command', command], timeout_seconds=self._POWERSHELL_TIMEOUT_SECONDS)
        if not result or result.get('returncode') != 0:
            return None
        stdout = str(result.get('stdout') or '').strip()
        if not stdout:
            return None
        try:
            return json.loads(stdout)
        except Exception:
            return None

    def _run_command(self, command: list[str], *, timeout_seconds: float) -> dict[str, Any] | None:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=timeout_seconds,
                check=False,
            )
        except Exception:
            return None
        return {'returncode': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr}

    def _path_exists(self, value: str) -> bool:
        if not str(value or '').strip():
            return False
        try:
            return Path(value).exists()
        except Exception:
            return False

    def _in_test_mode(self) -> bool:
        return bool(os.getenv('PYTEST_CURRENT_TEST'))
