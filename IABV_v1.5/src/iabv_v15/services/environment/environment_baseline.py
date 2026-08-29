"""Environment Baseline Service - initial baseline with timestamp and freshness.

Establishes a baseline of the environment at startup:
- Hardware, software, GPU, RAM/CPU, network
- Services, Ollama, models, MCP/tools, Git/GitHub
- Accounts/capabilities, runtime, permissions

Maintains observation freshness (FRESH/STALE/UNKNOWN) and observation levels (LEVEL_0/1/2).

Startup: full baseline establishment
Background: incremental refresh
Request-time: targeted refresh only for stale/unknown state
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observation Freshness
# ---------------------------------------------------------------------------

class ObservationFreshness(Enum):
    """Freshness of an observation."""
    FRESH = "fresh"  # Recently observed, within TTL
    STALE = "stale"  # Observed but beyond TTL
    UNKNOWN = "unknown"  # Never observed or observation failed


# ---------------------------------------------------------------------------
# Observation Levels
# ---------------------------------------------------------------------------

class ObservationLevel(Enum):
    """Depth of observation required."""
    LEVEL_0_STATIC = "level_0_static"  # Configuration, versions, known paths
    LEVEL_1_LIGHT_RUNTIME = "level_1_light_runtime"  # RAM, CPU, GPU utilization, process state, Ollama health
    LEVEL_2_DEEP_DISCOVERY = "level_2_deep_discovery"  # WMI/PowerShell hardware/service/window/network/account discovery


# ---------------------------------------------------------------------------
# Baseline State
# ---------------------------------------------------------------------------

@dataclass
class ObservationRecord:
    """A single observation with freshness tracking."""
    key: str
    value: Any
    level: ObservationLevel
    timestamp_utc: str
    ttl_seconds: float = 60.0  # Default TTL for freshness

    @property
    def age_seconds(self) -> float:
        """Age of this observation in seconds."""
        try:
            ts = datetime.fromisoformat(self.timestamp_utc)
            return (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            return float('inf')

    @property
    def freshness(self) -> ObservationFreshness:
        """Current freshness of this observation."""
        if self.age_seconds > self.ttl_seconds:
            return ObservationFreshness.STALE
        return ObservationFreshness.FRESH


@dataclass
class EnvironmentBaseline:
    """Complete baseline of the environment at startup."""
    baseline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    host_id: str = ""
    runtime_id: str = ""
    
    # Hardware
    hardware: dict[str, Any] = field(default_factory=dict)
    
    # Software
    software: dict[str, Any] = field(default_factory=dict)
    
    # GPU
    gpu: dict[str, Any] = field(default_factory=dict)
    
    # RAM/CPU
    ram_cpu: dict[str, Any] = field(default_factory=dict)
    
    # Network
    network: dict[str, Any] = field(default_factory=dict)
    
    # Services
    services: dict[str, Any] = field(default_factory=dict)
    
    # Ollama
    ollama: dict[str, Any] = field(default_factory=dict)
    
    # Models
    models: dict[str, Any] = field(default_factory=dict)
    
    # Tools/MCP
    tools: dict[str, Any] = field(default_factory=dict)
    
    # Git/GitHub
    git: dict[str, Any] = field(default_factory=dict)
    
    # GitHub
    github: dict[str, Any] = field(default_factory=dict)
    
    # Permissions
    permissions: dict[str, Any] = field(default_factory=dict)
    
    # Known limitations
    known_limitations: list[str] = field(default_factory=list)
    
    # Individual observations with freshness tracking
    observations: dict[str, ObservationRecord] = field(default_factory=dict)

    def get_observation(self, key: str) -> tuple[Any, ObservationFreshness]:
        """Get an observation and its freshness."""
        record = self.observations.get(key)
        if record is None:
            return None, ObservationFreshness.UNKNOWN
        return record.value, record.freshness

    def set_observation(
        self,
        key: str,
        value: Any,
        level: ObservationLevel,
        ttl_seconds: float = 60.0,
    ) -> None:
        """Set an observation with current timestamp."""
        self.observations[key] = ObservationRecord(
            key=key,
            value=value,
            level=level,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ttl_seconds=ttl_seconds,
        )

    def is_fresh(self, key: str) -> bool:
        """Check if an observation is fresh."""
        _, freshness = self.get_observation(key)
        return freshness == ObservationFreshness.FRESH

    def is_stale(self, key: str) -> bool:
        """Check if an observation is stale."""
        _, freshness = self.get_observation(key)
        return freshness == ObservationFreshness.STALE

    def is_unknown(self, key: str) -> bool:
        """Check if an observation is unknown."""
        _, freshness = self.get_observation(key)
        return freshness == ObservationFreshness.UNKNOWN

    def age_seconds(self, key: str) -> float:
        """Get age of an observation in seconds."""
        record = self.observations.get(key)
        if record is None:
            return float('inf')
        return record.age_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert baseline to dictionary for persistence."""
        return {
            'baseline_id': self.baseline_id,
            'timestamp_utc': self.timestamp_utc,
            'host_id': self.host_id,
            'runtime_id': self.runtime_id,
            'hardware': self.hardware,
            'software': self.software,
            'gpu': self.gpu,
            'ram_cpu': self.ram_cpu,
            'network': self.network,
            'services': self.services,
            'ollama': self.ollama,
            'models': self.models,
            'tools': self.tools,
            'git': self.git,
            'github': self.github,
            'permissions': self.permissions,
            'known_limitations': self.known_limitations,
            'observations': {
                k: {
                    'value': v.value,
                    'level': v.level.value,
                    'timestamp_utc': v.timestamp_utc,
                    'ttl_seconds': v.ttl_seconds,
                }
                for k, v in self.observations.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'EnvironmentBaseline':
        """Create baseline from dictionary."""
        baseline = cls(
            baseline_id=data.get('baseline_id', ''),
            timestamp_utc=data.get('timestamp_utc', ''),
            host_id=data.get('host_id', ''),
            runtime_id=data.get('runtime_id', ''),
            hardware=data.get('hardware', {}),
            software=data.get('software', {}),
            gpu=data.get('gpu', {}),
            ram_cpu=data.get('ram_cpu', {}),
            network=data.get('network', {}),
            services=data.get('services', {}),
            ollama=data.get('ollama', {}),
            models=data.get('models', {}),
            tools=data.get('tools', {}),
            git=data.get('git', {}),
            github=data.get('github', {}),
            permissions=data.get('permissions', {}),
            known_limitations=data.get('known_limitations', []),
        )
        # Restore observations
        for key, obs_data in data.get('observations', {}).items():
            baseline.observations[key] = ObservationRecord(
                key=key,
                value=obs_data['value'],
                level=ObservationLevel(obs_data['level']),
                timestamp_utc=obs_data['timestamp_utc'],
                ttl_seconds=obs_data['ttl_seconds'],
            )
        return baseline


# ---------------------------------------------------------------------------
# Environment Baseline Service
# ---------------------------------------------------------------------------

class EnvironmentBaselineService:
    """Manages environment baseline with freshness tracking.

    Startup: establishes full baseline
    Background: maintains LEVEL_1 observations frequently, LEVEL_2 periodically
    Request-time: targeted refresh for stale/unknown state only
    """

    # TTL for different observation levels
    LEVEL_0_TTL_SECONDS = 300.0  # 5 minutes - static config
    LEVEL_1_TTL_SECONDS = 30.0   # 30 seconds - runtime state
    LEVEL_2_TTL_SECONDS = 180.0  # 3 minutes - deep discovery

    def __init__(
        self,
        *,
        workspace_root: str,
        evolution_dir: str,
        auto_start: bool | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.state_dir = Path(evolution_dir).resolve() / 'environment_baseline'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._auto_start = (not self._in_test_mode()) if auto_start is None else bool(auto_start)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._baseline: EnvironmentBaseline | None = None
        self._baseline_path = self.state_dir / 'latest_baseline.json'

        # Initialize host and runtime IDs
        self._host_id = self._get_host_id()
        self._runtime_id = uuid.uuid4().hex

        if self._auto_start:
            self.start()

    def _in_test_mode(self) -> bool:
        """Check if running in test mode."""
        return os.environ.get('IABV_TEST_MODE', '').lower() in ('1', 'true')

    def _get_host_id(self) -> str:
        """Get a stable host identifier."""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"

    def start(self) -> None:
        """Start the baseline service."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name='iabv-environment-baseline',
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 1.0) -> None:
        """Stop the baseline service."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(timeout_seconds, 0.1))

    def establish_baseline(self) -> EnvironmentBaseline:
        """Establish the initial baseline at startup.

        This performs a comprehensive discovery of the environment:
        - LEVEL_0: static configuration
        - LEVEL_1: runtime state
        - LEVEL_2: deep discovery
        """
        with self._lock:
            baseline = EnvironmentBaseline(
                host_id=self._host_id,
                runtime_id=self._runtime_id,
            )
            self._baseline = baseline

        # Perform observations at different levels
        self._observe_level_0_static(baseline)
        self._observe_level_1_light_runtime(baseline)
        self._observe_level_2_deep_discovery(baseline)

        # Persist baseline
        self._persist_baseline(baseline)

        return baseline

    def get_baseline(self) -> EnvironmentBaseline:
        """Get the current baseline."""
        with self._lock:
            if self._baseline is None:
                # Try to load from disk
                self._baseline = self._load_baseline()
                if self._baseline is None:
                    # Create empty baseline
                    self._baseline = EnvironmentBaseline(
                        host_id=self._host_id,
                        runtime_id=self._runtime_id,
                    )
            return self._baseline

    def refresh_observation(
        self,
        key: str,
        level: ObservationLevel | None = None,
        force: bool = False,
    ) -> tuple[Any, ObservationFreshness]:
        """Refresh a specific observation if stale or unknown.

        Args:
            key: Observation key to refresh
            level: Observation level (if not specified, uses existing level)
            force: Force refresh even if fresh

        Returns:
            (value, freshness) after refresh
        """
        baseline = self.get_baseline()
        
        # Check if refresh is needed
        if not force and baseline.is_fresh(key):
            return baseline.get_observation(key)

        # Determine level
        if level is None:
            record = baseline.observations.get(key)
            if record is None:
                level = ObservationLevel.LEVEL_1_LIGHT_RUNTIME  # Default
            else:
                level = record.level

        # Perform targeted refresh based on level
        if level == ObservationLevel.LEVEL_0_STATIC:
            self._observe_level_0_static(baseline, target_key=key)
        elif level == ObservationLevel.LEVEL_1_LIGHT_RUNTIME:
            self._observe_level_1_light_runtime(baseline, target_key=key)
        elif level == ObservationLevel.LEVEL_2_DEEP_DISCOVERY:
            self._observe_level_2_deep_discovery(baseline, target_key=key)
        
        # Update the baseline reference
        with self._lock:
            self._baseline = baseline

        return baseline.get_observation(key)

    def _observe_level_0_static(
        self,
        baseline: EnvironmentBaseline,
        target_key: str | None = None,
    ) -> None:
        """Observe static configuration (LEVEL_0)."""
        # Python version
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        baseline.set_observation(
            'python_version',
            python_version,
            ObservationLevel.LEVEL_0_STATIC,
            self.LEVEL_0_TTL_SECONDS,
        )
        baseline.software['python_version'] = python_version

        # Platform
        platform = sys.platform
        baseline.set_observation(
            'platform',
            platform,
            ObservationLevel.LEVEL_0_STATIC,
            self.LEVEL_0_TTL_SECONDS,
        )
        baseline.software['platform'] = platform

        # Workspace root
        baseline.set_observation(
            'workspace_root',
            str(self.workspace_root),
            ObservationLevel.LEVEL_0_STATIC,
            self.LEVEL_0_TTL_SECONDS,
        )

    def _observe_level_1_light_runtime(
        self,
        baseline: EnvironmentBaseline,
        target_key: str | None = None,
    ) -> None:
        """Observe light runtime state (LEVEL_1)."""
        # RAM/CPU using existing resource snapshot
        try:
            from iabv_v15.services.intelligent_resource_manager import take_resource_snapshot
            snap = take_resource_snapshot()
            
            baseline.set_observation(
                'ram_available_mb',
                snap.ram_available_mb,
                ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
                self.LEVEL_1_TTL_SECONDS,
            )
            baseline.set_observation(
                'ram_used_pct',
                snap.ram_used_pct,
                ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
                self.LEVEL_1_TTL_SECONDS,
            )
            baseline.set_observation(
                'cpu_load',
                snap.cpu_load_1m,
                ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
                self.LEVEL_1_TTL_SECONDS,
            )
            
            baseline.ram_cpu['available_mb'] = snap.ram_available_mb
            baseline.ram_cpu['used_pct'] = snap.ram_used_pct
            baseline.ram_cpu['cpu_load'] = snap.cpu_load_1m
        except Exception as exc:
            logger.warning("LEVEL_1 observation failed: %s", exc)

    def _observe_level_2_deep_discovery(
        self,
        baseline: EnvironmentBaseline,
        target_key: str | None = None,
    ) -> None:
        """Observe deep discovery (LEVEL_2) - resource-guarded."""
        # Check resource pressure before deep discovery
        try:
            from iabv_v15.services.resource_guard import get_resource_guard
            guard = get_resource_guard()
            decision = guard.check_action_allowed(
                action="level_2_deep_discovery",
                estimated_ram_mb=200,
                goal_required=False,
                essential=False,
            )
            if not decision.allowed:
                logger.info("LEVEL_2 deep discovery skipped: %s", decision.reason)
                baseline.known_limitations.append(f"LEVEL_2 discovery skipped: {decision.reason}")
                return
        except Exception:
            # If guard fails, proceed (fail-safe)
            pass

        # Deep environment scan
        try:
            from iabv_v15.services.deep_environment_scanner import scan_bios_firmware
            bios = scan_bios_firmware()
            baseline.set_observation(
                'bios_firmware',
                bios,
                ObservationLevel.LEVEL_2_DEEP_DISCOVERY,
                self.LEVEL_2_TTL_SECONDS,
            )
            baseline.hardware['bios'] = bios
        except Exception as exc:
            logger.warning("LEVEL_2 bios scan failed: %s", exc)

    def _monitor_loop(self) -> None:
        """Background loop for maintaining observations."""
        while not self._stop_event.is_set():
            try:
                baseline = self.get_baseline()
                
                # Refresh LEVEL_1 observations frequently
                self._observe_level_1_light_runtime(baseline)
                
                # Persist periodically
                self._persist_baseline(baseline)
            except Exception as exc:
                logger.warning("baseline monitor loop error: %s", exc)
            
            # Wait for next cycle (LEVEL_1 refresh interval)
            self._stop_event.wait(self.LEVEL_1_TTL_SECONDS)

    def _persist_baseline(self, baseline: EnvironmentBaseline) -> None:
        """Persist baseline to disk."""
        try:
            self._baseline_path.write_text(
                json.dumps(baseline.to_dict(), indent=2),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.warning("Failed to persist baseline: %s", exc)

    def _load_baseline(self) -> EnvironmentBaseline | None:
        """Load baseline from disk."""
        try:
            if self._baseline_path.exists():
                data = json.loads(self._baseline_path.read_text(encoding='utf-8'))
                return EnvironmentBaseline.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to load baseline: %s", exc)
        return None


# Global instance
_global_baseline_service: EnvironmentBaselineService | None = None


def get_environment_baseline_service() -> EnvironmentBaselineService:
    """Get the global environment baseline service instance."""
    global _global_baseline_service
    if _global_baseline_service is None:
        raise RuntimeError("EnvironmentBaselineService not initialized")
    return _global_baseline_service
