"""Resource Guard — Preventive control for IABV's own expensive work.

Minimal guard that checks resource pressure BEFORE expensive operations:
- Deep scans (PowerShell, WMI, subprocess)
- Model discovery/preload
- Maintenance actions
- Optional observations

Uses existing ResourceSnapshot from intelligent_resource_manager.
Does NOT create a new governor — reuses existing infrastructure.

Behavior:
- LOW: normal optional work allowed
- MODERATE: reduce optional work
- HIGH: suppress expensive optional work
- CRITICAL: ONLY essential request work, suppress deep scans/maintenance/preload
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResourcePressure(Enum):
    """Resource pressure levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ResourceDecision:
    """Decision result for resource-aware action."""
    allowed: bool
    pressure: ResourcePressure
    reason: str
    ram_used_pct: float = 0.0
    ram_available_mb: int = 0


class ResourceGuard:
    """Preventive guard for IABV's own expensive work.

    Checks resource pressure BEFORE starting expensive operations.
    Reuses existing ResourceSnapshot from intelligent_resource_manager.
    """

    def __init__(self) -> None:
        self._snapshot_cache: dict[str, Any] = {}
        self._cache_ttl_seconds = 5.0
        self._last_check_time = 0.0

    def check_action_allowed(
        self,
        *,
        action: str,
        estimated_ram_mb: int = 0,
        goal_required: bool = False,
        essential: bool = False,
    ) -> ResourceDecision:
        """Check if an action is allowed given current resource pressure.

        Args:
            action: Description of the action (for logging)
            estimated_ram_mb: Estimated RAM consumption in MB
            goal_required: Whether the action is required by current goal
            essential: Whether the action is essential for safety

        Returns:
            ResourceDecision with allowed status and reason
        """
        import time

        # Use cached snapshot if recent (avoid repeated expensive checks)
        now = time.time()
        if now - self._last_check_time < self._cache_ttl_seconds and self._snapshot_cache:
            snap = self._snapshot_cache
        else:
            try:
                from iabv_v15.services.intelligent_resource_manager import take_resource_snapshot
                snap = take_resource_snapshot()
                self._snapshot_cache = snap
                self._last_check_time = now
            except Exception as exc:
                logger.warning("Resource snapshot failed, allowing action: %s", exc)
                # If snapshot fails, allow action (fail-safe)
                return ResourceDecision(
                    allowed=True,
                    pressure=ResourcePressure.LOW,
                    reason="snapshot_failed",
                )

        pressure = self._classify_pressure(snap.ram_used_pct)

        # Essential actions always allowed
        if essential:
            return ResourceDecision(
                allowed=True,
                pressure=pressure,
                reason="essential_action",
                ram_used_pct=snap.ram_used_pct,
                ram_available_mb=snap.ram_available_mb,
            )

        # Goal-required actions have higher priority
        if goal_required:
            if pressure == ResourcePressure.CRITICAL:
                # Even goal-required actions need to check RAM availability
                if snap.ram_available_mb < estimated_ram_mb:
                    return ResourceDecision(
                        allowed=False,
                        pressure=pressure,
                        reason=f"insufficient_ram_for_goal_required ({snap.ram_available_mb}MB < {estimated_ram_mb}MB)",
                        ram_used_pct=snap.ram_used_pct,
                        ram_available_mb=snap.ram_available_mb,
                    )
            return ResourceDecision(
                allowed=True,
                pressure=pressure,
                reason="goal_required",
                ram_used_pct=snap.ram_used_pct,
                ram_available_mb=snap.ram_available_mb,
            )

        # Optional work based on pressure level
        if pressure == ResourcePressure.CRITICAL:
            return ResourceDecision(
                allowed=False,
                pressure=pressure,
                reason="critical_pressure_optional_work_suppressed",
                ram_used_pct=snap.ram_used_pct,
                ram_available_mb=snap.ram_available_mb,
            )

        if pressure == ResourcePressure.HIGH:
            # Suppress expensive optional work under HIGH pressure
            if estimated_ram_mb > 100:
                return ResourceDecision(
                    allowed=False,
                    pressure=pressure,
                    reason=f"high_pressure_expensive_optional_suppressed ({estimated_ram_mb}MB > 100MB)",
                    ram_used_pct=snap.ram_used_pct,
                    ram_available_mb=snap.ram_available_mb,
                )
            # Allow lightweight optional work
            return ResourceDecision(
                allowed=True,
                pressure=pressure,
                reason="high_pressure_lightweight_optional_allowed",
                ram_used_pct=snap.ram_used_pct,
                ram_available_mb=snap.ram_available_mb,
            )

        if pressure == ResourcePressure.MODERATE:
            # Reduce optional work under MODERATE pressure
            if estimated_ram_mb > 500:
                return ResourceDecision(
                    allowed=False,
                    pressure=pressure,
                    reason=f"moderate_pressure_heavy_optional_suppressed ({estimated_ram_mb}MB > 500MB)",
                    ram_used_pct=snap.ram_used_pct,
                    ram_available_mb=snap.ram_available_mb,
                )
            return ResourceDecision(
                allowed=True,
                pressure=pressure,
                reason="moderate_pressure_optional_allowed",
                ram_used_pct=snap.ram_used_pct,
                ram_available_mb=snap.ram_available_mb,
            )

        # LOW pressure: normal optional work allowed
        return ResourceDecision(
            allowed=True,
            pressure=pressure,
            reason="low_pressure_normal_work_allowed",
            ram_used_pct=snap.ram_used_pct,
            ram_available_mb=snap.ram_available_mb,
        )

    def _classify_pressure(self, ram_used_pct: float) -> ResourcePressure:
        """Classify resource pressure from RAM usage percentage."""
        if ram_used_pct >= 90:
            return ResourcePressure.CRITICAL
        if ram_used_pct >= 75:
            return ResourcePressure.HIGH
        if ram_used_pct >= 50:
            return ResourcePressure.MODERATE
        return ResourcePressure.LOW

    def get_current_pressure(self) -> ResourcePressure:
        """Get current resource pressure without decision logic."""
        try:
            from iabv_v15.services.intelligent_resource_manager import take_resource_snapshot
            snap = take_resource_snapshot()
            return self._classify_pressure(snap.ram_used_pct)
        except Exception as exc:
            logger.warning("Resource snapshot failed for pressure check: %s", exc)
            return ResourcePressure.LOW  # Fail-safe


# Global instance for use across services
_global_guard: ResourceGuard | None = None


def get_resource_guard() -> ResourceGuard:
    """Get the global resource guard instance."""
    global _global_guard
    if _global_guard is None:
        _global_guard = ResourceGuard()
    return _global_guard
