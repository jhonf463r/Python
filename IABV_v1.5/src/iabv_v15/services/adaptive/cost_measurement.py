"""Cost Measurement — measure IABV's own work for adaptive learning.

Tracks ACTION, START, END, DURATION, RAM_BEFORE/AFTER, CPU_BEFORE/AFTER,
GPU_BEFORE/AFTER, RESULT, ERROR for each operation.

This data feeds into:
- Experience storage (ToolMemory/ExperimentLab)
- Adaptive operating protocol (OLD_RULE, OBSERVATION, ACTUAL_RESULT, NEW_RULE, CONFIDENCE)
- Resource-aware controller (historical cost patterns)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ResourceMeasurement:
    """Point-in-time resource measurement."""
    ram_available_mb: int = 0
    ram_used_pct: float = 0.0
    cpu_load_1m: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ram_available_mb": self.ram_available_mb,
            "ram_used_pct": self.ram_used_pct,
            "cpu_load_1m": self.cpu_load_1m,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationCostRecord:
    """Record of an operation's cost."""
    action: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    ram_before: ResourceMeasurement = field(default_factory=ResourceMeasurement)
    ram_after: ResourceMeasurement = field(default_factory=ResourceMeasurement)
    cpu_before: ResourceMeasurement = field(default_factory=ResourceMeasurement)
    cpu_after: ResourceMeasurement = field(default_factory=ResourceMeasurement)
    gpu_before: dict[str, Any] = field(default_factory=dict)
    gpu_after: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "ram_before": self.ram_before.to_dict(),
            "ram_after": self.ram_after.to_dict(),
            "cpu_before": self.cpu_before.to_dict(),
            "cpu_after": self.cpu_after.to_dict(),
            "gpu_before": self.gpu_before,
            "gpu_after": self.gpu_after,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class CostMeasurementService:
    """Measure cost of IABV's own operations."""

    def __init__(self, *, evolution_dir: str) -> None:
        self.evolution_dir = Path(evolution_dir).resolve()
        self.state_dir = self.evolution_dir / "cost_measurement"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.state_dir / "cost_log.jsonl"
        self._lock = threading.RLock()

    def measure_operation(
        self,
        action: str,
        operation_func,
        *args,
        **kwargs,
    ) -> tuple[Any, OperationCostRecord]:
        """Measure the cost of an operation.
        
        Returns (result, cost_record).
        """
        record = OperationCostRecord(action=action)
        
        # Measure before state
        record.ram_before = self._measure_resources()
        record.cpu_before = record.ram_before  # CPU measured together
        record.gpu_before = self._measure_gpu()
        record.start_time = datetime.now(timezone.utc).isoformat()
        
        start_ms = time.time() * 1000
        
        try:
            result = operation_func(*args, **kwargs)
            record.result = "success"
        except Exception as e:
            result = None
            record.result = "error"
            record.error = str(e)
            logger.error(f"Operation {action} failed: {e}")
        
        end_ms = time.time() * 1000
        record.duration_ms = end_ms - start_ms
        record.end_time = datetime.now(timezone.utc).isoformat()
        
        # Measure after state
        record.ram_after = self._measure_resources()
        record.cpu_after = record.ram_after
        record.gpu_after = self._measure_gpu()
        
        # Persist record
        self._persist_record(record)
        
        return result, record

    def _measure_resources(self) -> ResourceMeasurement:
        """Measure current RAM and CPU."""
        measurement = ResourceMeasurement(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
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
                        measurement.ram_available_mb = free_mb
                        measurement.ram_used_pct = round(((total_mb - free_mb) / max(total_mb, 1)) * 100, 1)
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
                        measurement.ram_available_mb = avail_kb // 1024
                        measurement.ram_used_pct = round(((total_kb - avail_kb) / max(total_kb, 1)) * 100, 1)
        except Exception as e:
            logger.warning(f"Resource measurement failed: {e}")
        
        # CPU load (simplified)
        measurement.cpu_load_1m = 0.0
        
        return measurement

    def _measure_gpu(self) -> dict[str, Any]:
        """Measure GPU state (placeholder for future GPU detection)."""
        return {
            "available": False,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "utilization_pct": 0.0,
        }

    def _persist_record(self, record: OperationCostRecord) -> None:
        """Persist cost record to log file."""
        with self._lock:
            try:
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record.to_dict(), default=str) + '\n')
            except Exception as e:
                logger.error(f"Failed to persist cost record: {e}")

    def get_recent_costs(self, action: str | None = None, limit: int = 100) -> list[OperationCostRecord]:
        """Get recent cost records, optionally filtered by action."""
        records = []
        
        if not self._log_file.exists():
            return records
        
        with self._lock:
            try:
                with open(self._log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if action is None or data.get("action") == action:
                                record = OperationCostRecord(
                                    action=data.get("action", ""),
                                    start_time=data.get("start_time", ""),
                                    end_time=data.get("end_time", ""),
                                    duration_ms=data.get("duration_ms", 0.0),
                                    ram_before=ResourceMeasurement(**data.get("ram_before", {})),
                                    ram_after=ResourceMeasurement(**data.get("ram_after", {})),
                                    cpu_before=ResourceMeasurement(**data.get("cpu_before", {})),
                                    cpu_after=ResourceMeasurement(**data.get("cpu_after", {})),
                                    gpu_before=data.get("gpu_before", {}),
                                    gpu_after=data.get("gpu_after", {}),
                                    result=data.get("result", ""),
                                    error=data.get("error", ""),
                                    metadata=data.get("metadata", {}),
                                )
                                records.append(record)
                                if len(records) >= limit:
                                    break
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse cost record: {e}")
            except Exception as e:
                logger.error(f"Failed to read cost log: {e}")
        
        # Sort by start time descending
        records.sort(key=lambda r: r.start_time, reverse=True)
        return records

    def get_average_cost(self, action: str) -> dict[str, Any]:
        """Get average cost statistics for an action."""
        records = self.get_recent_costs(action=action, limit=1000)
        
        if not records:
            return {
                "action": action,
                "count": 0,
                "avg_duration_ms": 0.0,
                "avg_ram_delta_mb": 0.0,
                "success_rate": 0.0,
            }
        
        total_duration = sum(r.duration_ms for r in records)
        avg_duration = total_duration / len(records)
        
        # Calculate average RAM delta
        ram_deltas = []
        for r in records:
            delta = r.ram_before.ram_available_mb - r.ram_after.ram_available_mb
            ram_deltas.append(delta)
        avg_ram_delta = sum(ram_deltas) / len(ram_deltas) if ram_deltas else 0.0
        
        # Success rate
        success_count = sum(1 for r in records if r.result == "success")
        success_rate = success_count / len(records)
        
        return {
            "action": action,
            "count": len(records),
            "avg_duration_ms": avg_duration,
            "avg_ram_delta_mb": avg_ram_delta,
            "success_rate": success_rate,
        }
