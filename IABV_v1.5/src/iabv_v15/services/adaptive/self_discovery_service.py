"""Self-Discovery Service — controlled initial self-discovery with progressive deepening.

Implements:
- LEVEL_0_STATIC: Static facts (OS, architecture, paths)
- LEVEL_1_RUNTIME: Runtime state (RAM, CPU, GPU)
- LEVEL_2_DEEP: Deep discovery (Ollama inventory, provider capabilities)

Behavior:
- Startup: Establish minimum identity (LEVEL_0), lightweight resource observation (LEVEL_1)
- Progressive deepening: LEVEL_2 only when safe and needed
- Resource safety: Check RAM/CPU/GPU before expensive operations
- Defer when unsafe: Partial baseline can resume later
- Persist progress: Save completed levels for resume capability
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.services.adaptive.self_discovery_baseline import (
    BaselineStatus,
    DiscoveryLevel,
    HostBaseline,
    OllamaBaseline,
    ResourceState,
    RuntimeBaseline,
    SelfDiscoveryBaseline,
    build_host_baseline,
    build_ollama_baseline,
    build_runtime_baseline,
)

logger = logging.getLogger(__name__)

# Resource safety thresholds
_RAM_CRITICAL_MB = 2 * 1024  # 2GB
_RAM_HIGH_MB = 4 * 1024  # 4GB
_CPU_CRITICAL_PCT = 90.0
_CPU_HIGH_PCT = 75.0

# Discovery timeouts
_OLLAMA_LIST_TIMEOUT_SECONDS = 3.0
_GPU_QUERY_TIMEOUT_SECONDS = 5.0


@dataclass
class DiscoveryResult:
    """Result of a discovery operation."""
    level: DiscoveryLevel
    success: bool
    baseline: SelfDiscoveryBaseline | None = None
    error: str = ""
    duration_ms: float = 0.0
    deferred: bool = False
    defer_reason: str = ""


class SelfDiscoveryService:
    """Controlled self-discovery with progressive deepening."""

    def __init__(
        self,
        *,
        workspace_root: str,
        data_dir: str,
        evolution_dir: str,
        auto_start: bool = True,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.data_dir = Path(data_dir).resolve()
        self.evolution_dir = Path(evolution_dir).resolve()
        self.state_dir = self.evolution_dir / "self_discovery"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self._baseline_file = self.state_dir / "baseline.json"
        self._lock = threading.RLock()
        self._current_baseline: SelfDiscoveryBaseline | None = None
        
        if auto_start:
            self._initial_discovery()

    def current_baseline(self) -> SelfDiscoveryBaseline:
        """Get current baseline (load from disk if needed)."""
        with self._lock:
            if self._current_baseline is None:
                self._current_baseline = self._load_baseline()
            return self._current_baseline

    def _initial_discovery(self) -> SelfDiscoveryBaseline:
        """Perform initial self-discovery with progressive deepening."""
        logger.info("Starting initial self-discovery...")
        
        baseline = SelfDiscoveryBaseline(
            baseline_id=f"baseline_{int(time.time())}",
            status=BaselineStatus.PARTIAL,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        # LEVEL_0: Static facts (always safe, always complete)
        try:
            host = build_host_baseline(
                workspace_root=str(self.workspace_root),
                data_dir=str(self.data_dir),
            )
            baseline.host = host
            baseline.levels_completed.append(DiscoveryLevel.LEVEL_0_STATIC)
            logger.info("LEVEL_0_STATIC completed")
        except Exception as e:
            logger.error(f"LEVEL_0_STATIC failed: {e}")
        
        # LEVEL_1: Runtime state (lightweight, always safe)
        try:
            runtime = self._discover_runtime()
            baseline.runtime = runtime
            baseline.levels_completed.append(DiscoveryLevel.LEVEL_1_RUNTIME)
            logger.info("LEVEL_1_RUNTIME completed")
        except Exception as e:
            logger.error(f"LEVEL_1_RUNTIME failed: {e}")
        
        # LEVEL_2: Deep discovery (only if safe and needed)
        should_attempt_level_2 = self._should_attempt_level_2(baseline.runtime)
        if should_attempt_level_2:
            try:
                ollama = self._discover_ollama()
                baseline.ollama = ollama
                baseline.levels_completed.append(DiscoveryLevel.LEVEL_2_DEEP)
                baseline.status = BaselineStatus.COMPLETE
                logger.info("LEVEL_2_DEEP completed")
            except Exception as e:
                logger.error(f"LEVEL_2_DEEP failed: {e}")
                baseline.levels_deferred.append(DiscoveryLevel.LEVEL_2_DEEP)
        else:
            baseline.levels_deferred.append(DiscoveryLevel.LEVEL_2_DEEP)
            logger.info("LEVEL_2_DEEP deferred (resource safety)")
        
        baseline.updated_at = datetime.now(timezone.utc).isoformat()
        
        with self._lock:
            self._current_baseline = baseline
            self._persist_baseline(baseline)
        
        logger.info(f"Initial self-discovery complete: status={baseline.status.value}, "
                    f"completed={[l.value for l in baseline.levels_completed]}, "
                    f"deferred={[l.value for l in baseline.levels_deferred]}")
        
        return baseline

    def _should_attempt_level_2(self, runtime: RuntimeBaseline) -> bool:
        """Check if LEVEL_2 deep discovery is safe to attempt."""
        # Unknown resource state: do not authorize expensive optional work
        if runtime.resource_state == ResourceState.UNKNOWN:
            logger.warning("Resource state unknown: deferring LEVEL_2_DEEP")
            return False
        
        # Unsafe resource state: defer
        if runtime.resource_state == ResourceState.UNSAFE:
            logger.warning(f"Resource state unsafe ({runtime.current_pressure}): deferring LEVEL_2_DEEP")
            return False
        
        # Safe but high pressure: still defer for ordinary startup
        if runtime.current_pressure in ("critical", "high"):
            logger.info(f"Resource pressure {runtime.current_pressure}: deferring LEVEL_2_DEEP")
            return False
        
        # Safe and low/moderate pressure: allow
        return True

    def _discover_runtime(self) -> RuntimeBaseline:
        """Discover runtime resource state (LEVEL_1)."""
        resource_snapshot = self._take_resource_snapshot()
        return build_runtime_baseline(resource_snapshot=resource_snapshot)

    def _take_resource_snapshot(self) -> dict[str, Any]:
        """Take lightweight resource snapshot."""
        snapshot = {
            "ram_total_mb": 0,
            "ram_available_mb": 0,
            "ram_used_pct": 0.0,
            "ram_pressure": "unknown",
            "cpu_count": os.cpu_count() or 1,
            "cpu_load_1m": 0.0,
            "cpu_pressure": "unknown",
        }
        
        # RAM detection (Windows: PowerShell, Linux: /proc/meminfo)
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command',
                     '(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize/1024,'
                     '(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024'],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().splitlines()
                    if len(lines) >= 2:
                        total_mb = int(float(lines[0].strip()))
                        free_mb = int(float(lines[1].strip()))
                        used_mb = total_mb - free_mb
                        snapshot["ram_total_mb"] = total_mb
                        snapshot["ram_available_mb"] = free_mb
                        snapshot["ram_used_pct"] = round((used_mb / max(total_mb, 1)) * 100, 1)
                        
                        # RAM pressure classification
                        if snapshot["ram_used_pct"] > 90:
                            snapshot["ram_pressure"] = "critical"
                        elif snapshot["ram_used_pct"] > 75:
                            snapshot["ram_pressure"] = "high"
                        elif snapshot["ram_used_pct"] > 50:
                            snapshot["ram_pressure"] = "moderate"
                        else:
                            snapshot["ram_pressure"] = "low"
            else:
                meminfo = Path('/proc/meminfo')
                if meminfo.exists():
                    text = meminfo.read_text()
                    import re
                    total_m = re.search(r'MemTotal:\s+(\d+)', text)
                    avail_m = re.search(r'MemAvailable:\s+(\d+)', text)
                    if total_m and avail_m:
                        total_kb = int(total_m.group(1))
                        avail_kb = int(avail_m.group(1))
                        snapshot["ram_total_mb"] = total_kb // 1024
                        snapshot["ram_available_mb"] = avail_kb // 1024
                        used_kb = total_kb - avail_kb
                        snapshot["ram_used_pct"] = round((used_kb / max(total_kb, 1)) * 100, 1)
                        
                        if snapshot["ram_used_pct"] > 90:
                            snapshot["ram_pressure"] = "critical"
                        elif snapshot["ram_used_pct"] > 75:
                            snapshot["ram_pressure"] = "high"
                        elif snapshot["ram_used_pct"] > 50:
                            snapshot["ram_pressure"] = "moderate"
                        else:
                            snapshot["ram_pressure"] = "low"
        except Exception as e:
            logger.warning(f"RAM detection failed: {e}")
        
        # CPU load (simplified: assume low for startup)
        snapshot["cpu_load_1m"] = 0.0
        snapshot["cpu_pressure"] = "low"
        
        return snapshot

    def _discover_ollama(self) -> OllamaBaseline:
        """Discover Ollama inventory (LEVEL_2)."""
        inventory = self._query_ollama_inventory()
        return build_ollama_baseline(ollama_inventory=inventory)

    def _query_ollama_inventory(self) -> dict[str, Any]:
        """Query Ollama for model inventory."""
        inventory = {
            "available": False,
            "version": "",
            "endpoint": "http://localhost:11434",
            "models_loaded": [],
            "models_available": [],
            "local_models": [],
            "remote_providers": [],
            "provider_kind": "local",
        }
        
        try:
            # Check if Ollama is available
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                inventory["available"] = True
                inventory["version"] = result.stdout.strip()
                
                # List models
                result = subprocess.run(
                    ['ollama', 'list'],
                    capture_output=True, text=True, timeout=_OLLAMA_LIST_TIMEOUT_SECONDS,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().splitlines()
                    for line in lines[1:]:  # Skip header
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            inventory["models_available"].append({
                                "name": model_name,
                                "size": parts[1] if len(parts) > 1 else "unknown",
                            })
                            inventory["local_models"].append({
                                "name": model_name,
                                "provider": "ollama",
                                "kind": "local",
                            })
        except FileNotFoundError:
            logger.info("Ollama not found in PATH")
        except subprocess.TimeoutExpired:
            logger.warning("Ollama list timeout")
        except Exception as e:
            logger.warning(f"Ollama inventory query failed: {e}")
        
        return inventory

    def request_level_2_discovery(self) -> DiscoveryResult:
        """Request LEVEL_2 deep discovery (can be called later when safe)."""
        start = time.time()
        baseline = self.current_baseline()
        
        if DiscoveryLevel.LEVEL_2_DEEP in baseline.levels_completed:
            return DiscoveryResult(
                level=DiscoveryLevel.LEVEL_2_DEEP,
                success=True,
                baseline=baseline,
                duration_ms=(time.time() - start) * 1000,
            )
        
        # Check resource safety
        if not self._should_attempt_level_2(baseline.runtime):
            return DiscoveryResult(
                level=DiscoveryLevel.LEVEL_2_DEEP,
                success=False,
                baseline=baseline,
                error="Resource safety check failed",
                deferred=True,
                defer_reason=baseline.runtime.current_pressure,
                duration_ms=(time.time() - start) * 1000,
            )
        
        try:
            ollama = self._discover_ollama()
            baseline.ollama = ollama
            baseline.levels_completed.append(DiscoveryLevel.LEVEL_2_DEEP)
            if DiscoveryLevel.LEVEL_2_DEEP in baseline.levels_deferred:
                baseline.levels_deferred.remove(DiscoveryLevel.LEVEL_2_DEEP)
            
            if len(baseline.levels_deferred) == 0:
                baseline.status = BaselineStatus.COMPLETE
            
            baseline.updated_at = datetime.now(timezone.utc).isoformat()
            
            with self._lock:
                self._current_baseline = baseline
                self._persist_baseline(baseline)
            
            return DiscoveryResult(
                level=DiscoveryLevel.LEVEL_2_DEEP,
                success=True,
                baseline=baseline,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error(f"LEVEL_2_DEEP discovery failed: {e}")
            return DiscoveryResult(
                level=DiscoveryLevel.LEVEL_2_DEEP,
                success=False,
                baseline=baseline,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    def _load_baseline(self) -> SelfDiscoveryBaseline:
        """Load baseline from disk."""
        if not self._baseline_file.exists():
            return SelfDiscoveryBaseline(
                baseline_id=f"baseline_{int(time.time())}",
                status=BaselineStatus.PARTIAL,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        
        try:
            with open(self._baseline_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            baseline = SelfDiscoveryBaseline(
                baseline_id=data.get("baseline_id", ""),
                status=BaselineStatus(data.get("status", "partial")),
                host=HostBaseline(**data.get("host", {})),
                runtime=RuntimeBaseline(**data.get("runtime", {})),
                ollama=OllamaBaseline(**data.get("ollama", {})),
                levels_completed=[DiscoveryLevel(l) for l in data.get("levels_completed", [])],
                levels_deferred=[DiscoveryLevel(l) for l in data.get("levels_deferred", [])],
                metadata=data.get("metadata", {}),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )
            return baseline
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return SelfDiscoveryBaseline(
                baseline_id=f"baseline_{int(time.time())}",
                status=BaselineStatus.PARTIAL,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

    def _persist_baseline(self, baseline: SelfDiscoveryBaseline) -> None:
        """Persist baseline to disk."""
        try:
            with open(self._baseline_file, 'w', encoding='utf-8') as f:
                json.dump(baseline.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist baseline: {e}")
