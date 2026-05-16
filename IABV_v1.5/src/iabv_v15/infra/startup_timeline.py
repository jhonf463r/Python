"""Startup timeline instrumentation for IABV v1.5.

Records timestamped milestones of the boot sequence so we can pinpoint
exactly which stage retains the GUI thread when the splash freezes.

Each milestone is appended as one JSON line to
``data/logs/startup_timeline.jsonl``.  Format:

    {
        "phase": "bootstrap_init_done",
        "t_ms_from_start": 2173.4,
        "rss_mb": 122.7,
        "extra": {...}
    }

The first call defines ``t0``; subsequent calls compute ``t_ms_from_start``
as monotonic milliseconds from that anchor.

Designed to be cheap (one JSON.dumps + one append) and crash-free: any
I/O error is swallowed because instrumentation must never break boot.

The user can opt out via ``IABV_STARTUP_TIMELINE=0`` (default ``1``).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Set by __main__.py to the perf_counter() captured at process entry,
# BEFORE any heavy imports.  When available, marks include
# ``t_ms_from_process`` — the real wall time from Python process start.
_PROCESS_T0: float | None = None
_MARK_SLOW_BUDGET_MS = 100.0
_WINDOW_LOG_COOLDOWN_S = 2.0


def _get_rss_mb() -> float:
    """Return current process RSS in MiB. ``-1.0`` if unavailable."""
    try:
        import psutil  # type: ignore[import-not-found]
        return float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        try:
            import resource
            kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On Linux ru_maxrss is in KiB; on macOS it's in bytes.
            if kb < 10 * 1024 * 1024:  # heuristic: treat as KiB on Linux
                return kb / 1024.0
            return kb / (1024.0 * 1024.0)
        except Exception:
            return -1.0


@dataclass
class StartupTimeline:
    """Cheap, crash-safe phase recorder.

    Keeps the in-memory event list AND optionally streams every entry to
    ``data/logs/startup_timeline.jsonl``.  The same instance is shared
    across :mod:`iabv_v15.bootstrap` and :mod:`iabv_v15.main` via the
    process-global ``get_global_timeline()`` helper.
    """

    log_dir: Path | None = None
    _t0: float = field(default_factory=time.perf_counter)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _events: list[dict[str, Any]] = field(default_factory=list)
    _enabled: bool = True
    _last_log_by_phase: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Always instantiate the timeline; only the JSONL sink is gated
        # by the env var so unit tests can inspect events without writing.
        if os.environ.get('IABV_STARTUP_TIMELINE', '1') == '0':
            self._enabled = False

    @property
    def t0(self) -> float:
        return self._t0

    def reset(self) -> None:
        """Reset the anchor and clear events (used by tests)."""
        with self._lock:
            self._t0 = time.perf_counter()
            self._events.clear()

    def mark(self, phase: str, **extra: Any) -> dict[str, Any]:
        """Record one milestone. Returns the appended event dict."""
        mark_t0 = time.perf_counter()
        now = time.perf_counter()
        elapsed_ms = (now - self._t0) * 1000.0
        event: dict[str, Any] = {
            'phase': phase,
            't_ms_from_start': round(elapsed_ms, 1),
            'rss_mb': round(_get_rss_mb(), 1),
        }
        process_t0 = _PROCESS_T0
        if process_t0 is not None:
            event['t_ms_from_process'] = round((now - process_t0) * 1000.0, 1)
        if extra:
            event['extra'] = extra
        with self._lock:
            self._events.append(event)
            if self._enabled and self.log_dir is not None:
                self._append_jsonl(event)
        mark_elapsed_ms = (time.perf_counter() - mark_t0) * 1000.0
        if mark_elapsed_ms > _MARK_SLOW_BUDGET_MS:
            event['mark_duration_ms'] = round(mark_elapsed_ms, 1)
            self._trace_slow_mark(phase, mark_elapsed_ms)
        try:
            if self._should_log_phase(phase):
                logger.info(
                    'startup_timeline %s @ %.1fms RSS=%.1fMB%s',
                    phase, elapsed_ms, event['rss_mb'],
                    f' {extra}' if extra else '',
                )
        except Exception:
            pass
        return event

    def events(self) -> list[dict[str, Any]]:
        """Snapshot copy of recorded events."""
        with self._lock:
            return list(self._events)

    def _append_jsonl(self, event: dict[str, Any]) -> None:
        if self.log_dir is None:
            return
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            target = self.log_dir / 'startup_timeline.jsonl'
            with target.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception:
            # Instrumentation must never break boot.
            pass

    def _should_log_phase(self, phase: str) -> bool:
        """Rate-limit logger.info for high-frequency window lifecycle marks."""
        if not phase.startswith('window_'):
            return True
        now = time.perf_counter()
        last = self._last_log_by_phase.get(phase, 0.0)
        if now - last < _WINDOW_LOG_COOLDOWN_S:
            return False
        self._last_log_by_phase[phase] = now
        return True

    @staticmethod
    def _trace_slow_mark(phase: str, duration_ms: float) -> None:
        """Emit slow timeline instrumentation without making timeline depend on it."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(
                'timeline_mark_slow',
                phase=phase,
                duration_ms=round(duration_ms, 1),
                budget_ms=_MARK_SLOW_BUDGET_MS,
            )
        except Exception:
            pass


_GLOBAL: StartupTimeline | None = None
_GLOBAL_LOCK = threading.Lock()


def get_global_timeline() -> StartupTimeline:
    """Return the process-global timeline instance, creating on first use."""
    global _GLOBAL
    with _GLOBAL_LOCK:
        if _GLOBAL is None:
            _GLOBAL = StartupTimeline()
        return _GLOBAL


def configure_global_timeline(log_dir: Path) -> StartupTimeline:
    """Attach a JSONL sink to the global timeline (idempotent)."""
    timeline = get_global_timeline()
    if timeline.log_dir is None:
        with timeline._lock:
            timeline.log_dir = log_dir
            if timeline._enabled:
                for event in timeline._events:
                    timeline._append_jsonl(event)
    return timeline


def reset_global_timeline_for_tests() -> StartupTimeline:
    """Reset the global timeline to a fresh anchor (tests only)."""
    global _GLOBAL
    with _GLOBAL_LOCK:
        _GLOBAL = StartupTimeline()
        return _GLOBAL


__all__ = [
    'StartupTimeline',
    'get_global_timeline',
    'configure_global_timeline',
    'reset_global_timeline_for_tests',
]
