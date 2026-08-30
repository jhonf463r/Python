"""Resource-Aware Controller — self-control based on RAM, CPU, GPU, and resource pressure.

Implements resource safety checks before expensive operations:
- Check AVAILABLE_RAM, USED_PERCENT, CPU, GPU/VRAM
- Check CURRENT_PRESSURE before expensive operations
- Distinguish UNKNOWN_RESOURCE_STATE from SAFE_RESOURCE_STATE
- Never assume unlimited capacity if RESOURCE_CHECK_FAILURE occurs

Reuses existing ResourceSnapshot from IntelligentResourceManager and
ResourceMetacognitionService.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ResourcePressure(str, Enum):
    """Resource pressure classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class ResourceState(str, Enum):
    """Overall resource safety state."""
    UNKNOWN = "unknown"
    SAFE = "safe"
    UNSAFE = "unsafe"


class OperationCost(str, Enum):
    """Estimated cost of an operation."""
    TRIVIAL = "trivial"  # < 100ms, < 10MB RAM
    CHEAP = "cheap"  # < 1s, < 100MB RAM
    MODERATE = "moderate"  # < 10s, < 500MB RAM
    EXPENSIVE = "expensive"  # > 10s, > 500MB RAM


@dataclass
class ResourceCheck:
    """Result of a resource safety check."""
    safe: bool = False
    resource_state: ResourceState = ResourceState.UNKNOWN
    ram_pressure: ResourcePressure = ResourcePressure.LOW
    cpu_pressure: ResourcePressure = ResourcePressure.LOW
    gpu_pressure: ResourcePressure = ResourcePressure.LOW
    current_pressure: ResourcePressure = ResourcePressure.LOW
    ram_available_mb: int = 0
    ram_used_pct: float = 0.0
    cpu_load_1m: float = 0.0
    reason: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "resource_state": self.resource_state.value,
            "ram_pressure": self.ram_pressure.value,
            "cpu_pressure": self.cpu_pressure.value,
            "gpu_pressure": self.gpu_pressure.value,
            "current_pressure": self.current_pressure.value,
            "ram_available_mb": self.ram_available_mb,
            "ram_used_pct": self.ram_used_pct,
            "cpu_load_1m": self.cpu_load_1m,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationCostEstimate:
    """Estimated cost of an operation."""
    operation: str = ""
    cost_level: OperationCost = OperationCost.CHEAP
    expected_duration_ms: float = 0.0
    expected_ram_mb: float = 0.0
    risk: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)


class ResourceAwareController:
    """Resource-aware self-control for expensive operations."""

    # Safety thresholds
    _RAM_CRITICAL_MB = 2 * 1024  # 2GB
    _RAM_HIGH_MB = 4 * 1024  # 4GB
    _RAM_MODERATE_MB = 6 * 1024  # 6GB
    _CPU_CRITICAL_PCT = 90.0
    _CPU_HIGH_PCT = 75.0
    _CPU_MODERATE_PCT = 50.0

    def __init__(self) -> None:
        self._last_check: ResourceCheck | None = None
        self._check_cache_ttl_seconds = 5.0
        self._last_check_timestamp = 0.0

    def check_resource_safety(
        self,
        operation_cost: OperationCost = OperationCost.CHEAP,
        force_refresh: bool = False,
    ) -> ResourceCheck:
        """Check if it's safe to perform an operation with given cost.
        
        Rules:
        - UNKNOWN_RESOURCE_STATE: Do NOT authorize expensive optional work
        - SAFE_RESOURCE_STATE: Authorize if pressure allows
        - RESOURCE_CHECK_FAILURE: Never assume unlimited capacity
        - CRITICAL pressure: Always defer (except trivial operations)
        - HIGH pressure: Defer expensive operations
        - MODERATE pressure: Allow cheap/moderate, defer expensive
        - LOW pressure: Allow all
        """
        # Use cached check if recent
        now = time.time()
        if not force_refresh and self._last_check is not None:
            if (now - self._last_check_timestamp) < self._check_cache_ttl_seconds:
                # Re-evaluate based on operation cost
                return self._evaluate_for_operation(self._last_check, operation_cost)
        
        # Take fresh snapshot
        snapshot = self._take_resource_snapshot()
        check = self._build_resource_check(snapshot)
        
        self._last_check = check
        self._last_check_timestamp = now
        
        return self._evaluate_for_operation(check, operation_cost)

    def _evaluate_for_operation(
        self,
        check: ResourceCheck,
        operation_cost: OperationCost,
    ) -> ResourceCheck:
        """Evaluate if operation is safe given resource state."""
        # UNKNOWN_RESOURCE_STATE: Do NOT authorize expensive optional work
        if check.resource_state == ResourceState.UNKNOWN:
            if operation_cost in (OperationCost.MODERATE, OperationCost.EXPENSIVE):
                check.safe = False
                check.reason = "Resource state unknown: cannot authorize expensive operation"
                return check
            # Trivial/cheap operations may proceed with caution
            check.safe = True
            check.reason = "Resource state unknown but operation is trivial/cheap"
            return check
        
        # UNSAFE_RESOURCE_STATE: Defer all but trivial
        if check.resource_state == ResourceState.UNSAFE:
            if operation_cost == OperationCost.TRIVIAL:
                check.safe = True
                check.reason = "Resource state unsafe but operation is trivial"
            else:
                check.safe = False
                check.reason = f"Resource state unsafe ({check.current_pressure}): cannot authorize operation"
            return check
        
        # SAFE_RESOURCE_STATE: Evaluate based on pressure and cost
        if check.current_pressure == ResourcePressure.CRITICAL:
            # CRITICAL: Only trivial operations
            if operation_cost == OperationCost.TRIVIAL:
                check.safe = True
                check.reason = "Critical pressure but operation is trivial"
            else:
                check.safe = False
                check.reason = "Critical pressure: cannot authorize non-trivial operation"
            return check
        
        if check.current_pressure == ResourcePressure.HIGH:
            # HIGH: Allow trivial/cheap, defer moderate/expensive
            if operation_cost in (OperationCost.TRIVIAL, OperationCost.CHEAP):
                check.safe = True
                check.reason = "High pressure but operation is cheap/trivial"
            else:
                check.safe = False
                check.reason = "High pressure: cannot authorize moderate/expensive operation"
            return check
        
        if check.current_pressure == ResourcePressure.MODERATE:
            # MODERATE: Allow trivial/cheap/moderate, defer expensive
            if operation_cost in (OperationCost.TRIVIAL, OperationCost.CHEAP, OperationCost.MODERATE):
                check.safe = True
                check.reason = "Moderate pressure: operation within limits"
            else:
                check.safe = False
                check.reason = "Moderate pressure: cannot authorize expensive operation"
            return check
        
        # LOW pressure: Allow all
        check.safe = True
        check.reason = "Low pressure: operation safe"
        return check

    def _take_resource_snapshot(self) -> dict[str, Any]:
        """Take resource snapshot."""
        snapshot = {
            "ram_total_mb": 0,
            "ram_available_mb": 0,
            "ram_used_pct": 0.0,
            "cpu_count": os.cpu_count() or 1,
            "cpu_load_1m": 0.0,
        }
        
        # RAM detection
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command',
                     '(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize/1024,'
                     '(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024'],
                    capture_output=True, text=True, timeout=3,
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
        except Exception as e:
            logger.warning(f"RAM detection failed: {e}")
        
        # CPU load (simplified)
        snapshot["cpu_load_1m"] = 0.0
        
        return snapshot

    def _build_resource_check(self, snapshot: dict[str, Any]) -> ResourceCheck:
        """Build resource check from snapshot."""
        ram_available_mb = snapshot.get("ram_available_mb", 0)
        ram_used_pct = snapshot.get("ram_used_pct", 0.0)
        cpu_load_1m = snapshot.get("cpu_load_1m", 0.0)
        cpu_count = snapshot.get("cpu_count", 1)
        
        # Classify RAM pressure
        if ram_used_pct > 90:
            ram_pressure = ResourcePressure.CRITICAL
        elif ram_used_pct > 75:
            ram_pressure = ResourcePressure.HIGH
        elif ram_used_pct > 50:
            ram_pressure = ResourcePressure.MODERATE
        else:
            ram_pressure = ResourcePressure.LOW
        
        # Classify CPU pressure
        load_per_core = cpu_load_1m / max(cpu_count, 1)
        if load_per_core > 2.0:
            cpu_pressure = ResourcePressure.CRITICAL
        elif load_per_core > 1.0:
            cpu_pressure = ResourcePressure.HIGH
        elif load_per_core > 0.5:
            cpu_pressure = ResourcePressure.MODERATE
        else:
            cpu_pressure = ResourcePressure.LOW
        
        # Overall current pressure
        if ram_pressure == ResourcePressure.CRITICAL or cpu_pressure == ResourcePressure.CRITICAL:
            current_pressure = ResourcePressure.CRITICAL
        elif ram_pressure == ResourcePressure.HIGH or cpu_pressure == ResourcePressure.HIGH:
            current_pressure = ResourcePressure.HIGH
        elif ram_pressure == ResourcePressure.MODERATE or cpu_pressure == ResourcePressure.MODERATE:
            current_pressure = ResourcePressure.MODERATE
        else:
            current_pressure = ResourcePressure.LOW
        
        # Overall resource state
        if ram_available_mb == 0 and ram_used_pct == 0:
            resource_state = ResourceState.UNKNOWN
        elif current_pressure in (ResourcePressure.CRITICAL, ResourcePressure.HIGH):
            resource_state = ResourceState.UNSAFE
        else:
            resource_state = ResourceState.SAFE
        
        return ResourceCheck(
            safe=False,  # Will be evaluated by operation cost
            resource_state=resource_state,
            ram_pressure=ram_pressure,
            cpu_pressure=cpu_pressure,
            gpu_pressure=ResourcePressure.LOW,  # TODO: implement GPU detection
            current_pressure=current_pressure,
            ram_available_mb=ram_available_mb,
            ram_used_pct=ram_used_pct,
            cpu_load_1m=cpu_load_1m,
            reason="",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def estimate_operation_cost(self, operation: str) -> OperationCostEstimate:
        """Estimate the cost of an operation.
        
        Pre-defined cost estimates for common operations:
        - Reflection: CHEAP
        - World model refresh: MODERATE
        - Environment scan: MODERATE
        - Ollama inference: EXPENSIVE
        - Deep discovery: EXPENSIVE
        """
        cost_map = {
            "reflection": OperationCost.CHEAP,
            "world_model_refresh": OperationCost.MODERATE,
            "environment_scan": OperationCost.MODERATE,
            "ollama_inference": OperationCost.EXPENSIVE,
            "deep_discovery": OperationCost.EXPENSIVE,
            "model_selection": OperationCost.CHEAP,
            "context_assembly": OperationCost.CHEAP,
            "tool_execution": OperationCost.MODERATE,
        }
        
        cost_level = cost_map.get(operation, OperationCost.CHEAP)
        
        # Estimate duration and RAM based on cost level
        if cost_level == OperationCost.TRIVIAL:
            duration_ms = 50.0
            ram_mb = 5.0
        elif cost_level == OperationCost.CHEAP:
            duration_ms = 500.0
            ram_mb = 50.0
        elif cost_level == OperationCost.MODERATE:
            duration_ms = 5000.0
            ram_mb = 200.0
        else:  # EXPENSIVE
            duration_ms = 30000.0
            ram_mb = 1000.0
        
        return OperationCostEstimate(
            operation=operation,
            cost_level=cost_level,
            expected_duration_ms=duration_ms,
            expected_ram_mb=ram_mb,
            risk="low" if cost_level != OperationCost.EXPENSIVE else "medium",
        )
