"""Self-Discovery Baseline — structured baseline for adaptive self-operation.

Defines the baseline structure for HOST, RUNTIME, CPU, RAM, GPU, OLLAMA, MODELS, PROVIDERS.
Reuses existing EnvironmentSelfModel, WorldModelSnapshot, ResourceSnapshot structures.

Architecture:
- LEVEL_0_STATIC: Static facts that never change (OS, architecture, paths)
- LEVEL_1_RUNTIME: Runtime state that changes (RAM, CPU, GPU, processes)
- LEVEL_2_DEEP: Deep discovery (Ollama inventory, provider capabilities, model details)

Baseline Status:
- COMPLETE: All levels populated successfully
- PARTIAL: Some levels populated, others deferred
- DEFERRED: Discovery deferred due to resource pressure or safety constraints
"""
from __future__ import annotations

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DiscoveryLevel(str, Enum):
    """Depth of self-discovery."""
    LEVEL_0_STATIC = "level_0_static"
    LEVEL_1_RUNTIME = "level_1_runtime"
    LEVEL_2_DEEP = "level_2_deep"


class BaselineStatus(str, Enum):
    """Status of baseline discovery."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    DEFERRED = "deferred"


class ResourceState(str, Enum):
    """Resource safety state."""
    UNKNOWN = "unknown"
    SAFE = "safe"
    UNSAFE = "unsafe"


@dataclass
class HostBaseline:
    """LEVEL_0_STATIC: Static host information."""
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    python_version: str = ""
    runtime_path: str = ""
    workspace_root: str = ""
    data_dir: str = ""
    source: str = "static"
    timestamp: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "architecture": self.architecture,
            "python_version": self.python_version,
            "runtime_path": self.runtime_path,
            "workspace_root": self.workspace_root,
            "data_dir": self.data_dir,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


@dataclass
class RuntimeBaseline:
    """LEVEL_1_RUNTIME: Runtime resource state."""
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    ram_used_pct: float = 0.0
    ram_pressure: str = "unknown"
    cpu_count: int = 1
    cpu_load_1m: float = 0.0
    cpu_pressure: str = "unknown"
    gpu_available: bool = False
    gpu_name: str = ""
    gpu_vram_total_mb: int = 0
    gpu_vram_free_mb: int = 0
    gpu_pressure: str = "unknown"
    current_pressure: str = "unknown"
    resource_state: ResourceState = ResourceState.UNKNOWN
    source: str = "runtime"
    timestamp: str = ""
    confidence: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "ram_total_mb": self.ram_total_mb,
            "ram_available_mb": self.ram_available_mb,
            "ram_used_pct": self.ram_used_pct,
            "ram_pressure": self.ram_pressure,
            "cpu_count": self.cpu_count,
            "cpu_load_1m": self.cpu_load_1m,
            "cpu_pressure": self.cpu_pressure,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "gpu_vram_total_mb": self.gpu_vram_total_mb,
            "gpu_vram_free_mb": self.gpu_vram_free_mb,
            "gpu_pressure": self.gpu_pressure,
            "current_pressure": self.current_pressure,
            "resource_state": self.resource_state.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


@dataclass
class OllamaBaseline:
    """LEVEL_2_DEEP: Ollama provider and model inventory."""
    ollama_available: bool = False
    ollama_version: str = ""
    ollama_endpoint: str = "http://localhost:11434"
    models_loaded: list[dict[str, Any]] = field(default_factory=list)
    models_available: list[dict[str, Any]] = field(default_factory=list)
    local_models: list[dict[str, Any]] = field(default_factory=list)
    remote_providers: list[dict[str, Any]] = field(default_factory=list)
    provider_kind: str = "local"
    source: str = "deep"
    timestamp: str = ""
    confidence: float = 0.6

    def to_dict(self) -> dict[str, Any]:
        return {
            "ollama_available": self.ollama_available,
            "ollama_version": self.ollama_version,
            "ollama_endpoint": self.ollama_endpoint,
            "models_loaded": self.models_loaded,
            "models_available": self.models_available,
            "local_models": self.local_models,
            "remote_providers": self.remote_providers,
            "provider_kind": self.provider_kind,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


@dataclass
class SelfDiscoveryBaseline:
    """Complete self-discovery baseline."""
    baseline_id: str = ""
    status: BaselineStatus = BaselineStatus.PARTIAL
    host: HostBaseline = field(default_factory=HostBaseline)
    runtime: RuntimeBaseline = field(default_factory=RuntimeBaseline)
    ollama: OllamaBaseline = field(default_factory=OllamaBaseline)
    levels_completed: list[DiscoveryLevel] = field(default_factory=list)
    levels_deferred: list[DiscoveryLevel] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "status": self.status.value,
            "host": self.host.to_dict(),
            "runtime": self.runtime.to_dict(),
            "ollama": self.ollama.to_dict(),
            "levels_completed": [l.value for l in self.levels_completed],
            "levels_deferred": [l.value for l in self.levels_deferred],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def build_host_baseline(
    workspace_root: str,
    data_dir: str,
) -> HostBaseline:
    """Build LEVEL_0_STATIC baseline (static facts)."""
    baseline = HostBaseline(
        hostname=platform.node(),
        os_name=platform.system(),
        os_version=platform.version(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        runtime_path=str(Path(__file__).resolve().parent.parent.parent),
        workspace_root=str(workspace_root),
        data_dir=str(data_dir),
        source="static",
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=1.0,
    )
    logger.info(f"Host baseline built: {baseline.hostname} ({baseline.os_name} {baseline.architecture})")
    return baseline


def build_runtime_baseline(
    resource_snapshot: dict[str, Any] | None = None,
) -> RuntimeBaseline:
    """Build LEVEL_1_RUNTIME baseline (resource state).
    
    Reuses ResourceSnapshot from IntelligentResourceManager or ResourceMetacognitionService.
    """
    baseline = RuntimeBaseline(
        source="runtime",
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=0.8,
    )
    
    if resource_snapshot:
        baseline.ram_total_mb = resource_snapshot.get("ram_total_mb", 0)
        baseline.ram_available_mb = resource_snapshot.get("ram_available_mb", 0)
        baseline.ram_used_pct = resource_snapshot.get("ram_used_pct", 0.0)
        baseline.ram_pressure = resource_snapshot.get("ram_pressure", "unknown")
        baseline.cpu_count = resource_snapshot.get("cpu_count", 1)
        baseline.cpu_load_1m = resource_snapshot.get("cpu_load_1m", 0.0)
        baseline.cpu_pressure = resource_snapshot.get("cpu_pressure", "unknown")
        
        # Determine overall resource state
        ram_ok = baseline.ram_pressure not in ("critical", "high")
        cpu_ok = baseline.cpu_pressure not in ("critical", "high")
        baseline.resource_state = ResourceState.SAFE if (ram_ok and cpu_ok) else ResourceState.UNSAFE
        
        # Determine current pressure
        if baseline.ram_pressure == "critical" or baseline.cpu_pressure == "critical":
            baseline.current_pressure = "critical"
        elif baseline.ram_pressure == "high" or baseline.cpu_pressure == "high":
            baseline.current_pressure = "high"
        elif baseline.ram_pressure == "moderate" or baseline.cpu_pressure == "moderate":
            baseline.current_pressure = "moderate"
        else:
            baseline.current_pressure = "low"
    
    logger.info(f"Runtime baseline built: RAM {baseline.ram_used_pct}% ({baseline.ram_pressure}), CPU {baseline.cpu_load_1m} ({baseline.cpu_pressure})")
    return baseline


def build_ollama_baseline(
    ollama_inventory: dict[str, Any] | None = None,
) -> OllamaBaseline:
    """Build LEVEL_2_DEEP baseline (Ollama inventory).
    
    Reuses OllamaExpertProvider inventory if available.
    """
    baseline = OllamaBaseline(
        source="deep",
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=0.6,
    )
    
    if ollama_inventory:
        baseline.ollama_available = ollama_inventory.get("available", False)
        baseline.ollama_version = ollama_inventory.get("version", "")
        baseline.ollama_endpoint = ollama_inventory.get("endpoint", "http://localhost:11434")
        baseline.models_loaded = ollama_inventory.get("models_loaded", [])
        baseline.models_available = ollama_inventory.get("models_available", [])
        baseline.local_models = ollama_inventory.get("local_models", [])
        baseline.remote_providers = ollama_inventory.get("remote_providers", [])
        baseline.provider_kind = ollama_inventory.get("provider_kind", "local")
    
    logger.info(f"Ollama baseline built: available={baseline.ollama_available}, models={len(baseline.models_available)}")
    return baseline
