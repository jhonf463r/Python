"""Runtime Audit Tracer — continuous self-audit from boot to shutdown.

Records every significant event in the program's lifecycle so that
any AI (Windsurf, Devin, IABV itself) can read the trace and
understand *exactly* what happened, when, and why:

- **Boot trace**: every service init with duration and dependencies
- **Decision trace**: every orchestrator/router decision with algorithm,
  inputs, and outputs
- **External query trace**: every attempt to contact an external service
  (ChatGPT, Ollama, Devin API, GitHub) with success/failure/timeout
- **Permission trace**: every permission check, grant, deny, or missing
  dialog
- **Resource trace**: resource snapshots at configurable intervals
- **Error trace**: every exception with full context

The trace is written as JSONL (one JSON object per line) to
``data/logs/runtime_audit.jsonl``.  Each line has:

    {
        "ts": "2024-01-15T10:30:45.123Z",
        "elapsed_ms": 12345.6,
        "kind": "service_init",
        "data": { ... }
    }

The tracer is designed to be ultra-lightweight:
- One ``json.dumps`` + one file append per event
- Thread-safe via lock
- Crash-safe: I/O errors are swallowed
- Can be disabled via ``IABV_RUNTIME_TRACE=0``

Usage
~~~~~
The global tracer is accessed via ``get_runtime_tracer()``.
Bootstrap calls ``trace_service_init()``, orchestrator calls
``trace_decision()``, adapters call ``trace_external_query()``, etc.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Feature markers expected from P0 slices #381-#389
# ------------------------------------------------------------------
_REQUIRED_FEATURE_MARKERS: dict[str, str] = {
    'has_post_remediation_recapture': '_attempt_post_remediation_recapture',
    'has_post_recapture_response_retry': '_attempt_post_recapture_response_retry',
    'has_shared_reality_handoff': 'shared_reality_handoff',
    'has_dispatch_lifecycle_tracing': 'trace_dispatch_started',
}


def _git_cmd(args: list[str], cwd: str | Path) -> str:
    """Run a git command and return stripped stdout, or '' on failure."""
    try:
        r = subprocess.run(
            ['git'] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


_MARKER_FILES: tuple[str, ...] = (
    'ui/viewmodels/control_center_viewmodel.py',
    'services/evolution/runtime_audit_tracer.py',
    'services/evolution/freeze_incident_reporter.py',
    'services/capture/browser_session_controller.py',
)

_FINGERPRINT_BUDGET_MS: float = 250.0


def _collect_build_fingerprint(workspace: str | Path = '.') -> dict[str, Any]:
    """Collect git and feature-marker info for the running build.

    Uses targeted file reads (not rglob) and scoped dirty check
    (src/, tests/, AGENTS.md only) to stay under 250ms budget.
    """
    t0 = time.perf_counter()
    ws = Path(workspace).resolve()
    src_dir = ws / 'src' / 'iabv_v15'
    if not src_dir.is_dir():
        src_dir = ws

    branch = _git_cmd(['rev-parse', '--abbrev-ref', 'HEAD'], ws)
    head = _git_cmd(['rev-parse', 'HEAD'], ws)
    dirty_output = _git_cmd(
        ['diff-index', '--name-only', 'HEAD', '--', 'src/', 'tests/', 'AGENTS.md'],
        ws,
    )
    if dirty_output:
        dirty = True
        git_status = 'dirty'
    elif dirty_output == '' and head:
        dirty = False
        git_status = 'clean'
    else:
        dirty = False
        git_status = 'unknown'
    origin_main = _git_cmd(['rev-parse', 'origin/main'], ws)

    markers: dict[str, bool] = {}
    for marker_name, search_string in _REQUIRED_FEATURE_MARKERS.items():
        found = False
        for rel_path in _MARKER_FILES:
            try:
                target = src_dir / rel_path
                if target.is_file():
                    content = target.read_text(encoding='utf-8', errors='ignore')
                    if search_string in content:
                        found = True
                        break
            except Exception:
                continue
        markers[marker_name] = found

    elapsed_ms = (time.perf_counter() - t0) * 1000
    result: dict[str, Any] = {
        'branch': branch,
        'head': head,
        'dirty': dirty,
        'git_status': git_status,
        'origin_main_head': origin_main,
        'workspace': str(ws),
        'feature_markers': markers,
        'stale': not all(markers.values()),
        'missing_markers': [k for k, v in markers.items() if not v],
        'elapsed_ms': round(elapsed_ms, 1),
    }
    if elapsed_ms > _FINGERPRINT_BUDGET_MS:
        result['budget_exceeded'] = True
    return result


class RuntimeAuditTracer:
    """Continuous JSONL tracer for the full program lifecycle."""

    def __init__(self, log_dir: str | Path | None = None) -> None:
        self._log_dir = Path(log_dir) if log_dir else None
        self._t0 = time.perf_counter()
        self._lock = threading.Lock()
        self._event_count = 0
        self._enabled = os.environ.get('IABV_RUNTIME_TRACE', '1') != '0'
        self._in_memory: list[dict[str, Any]] = []
        self._max_in_memory = 500

    def configure(self, log_dir: str | Path) -> None:
        """Set or update the log directory (called once bootstrap knows it)."""
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Core trace method
    # ------------------------------------------------------------------

    def trace(self, kind: str, **data: Any) -> dict[str, Any]:
        """Record one trace event. Returns the event dict."""
        now_pc = time.perf_counter()
        event: dict[str, Any] = {
            'ts': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            'elapsed_ms': round((now_pc - self._t0) * 1000.0, 1),
            'kind': kind,
        }
        if data:
            event['data'] = data
        with self._lock:
            self._event_count += 1
            event['seq'] = self._event_count
            self._in_memory.append(event)
            if len(self._in_memory) > self._max_in_memory:
                self._in_memory = self._in_memory[-self._max_in_memory:]
            if self._enabled and self._log_dir is not None:
                self._append(event)
        return event

    # ------------------------------------------------------------------
    # Typed trace helpers
    # ------------------------------------------------------------------

    def trace_service_init(
        self,
        service_name: str,
        duration_ms: float,
        *,
        status: str = 'ok',
        error: str = '',
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record a service initialization event."""
        return self.trace(
            'service_init',
            service=service_name,
            duration_ms=round(duration_ms, 1),
            status=status,
            error=error,
            dependencies=dependencies or [],
        )

    def trace_decision(
        self,
        decision_point: str,
        algorithm: str,
        inputs: dict[str, Any] | None = None,
        result: str = '',
        confidence: float | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Record an orchestrator/router decision."""
        return self.trace(
            'decision',
            decision_point=decision_point,
            algorithm=algorithm,
            inputs=inputs or {},
            result=result,
            confidence=confidence,
            **extra,
        )

    def trace_external_query(
        self,
        target: str,
        operation: str,
        *,
        status: str = 'ok',
        duration_ms: float = 0.0,
        error: str = '',
        response_summary: str = '',
    ) -> dict[str, Any]:
        """Record an external service query (ChatGPT, Ollama, Devin, etc.)."""
        return self.trace(
            'external_query',
            target=target,
            operation=operation,
            status=status,
            duration_ms=round(duration_ms, 1),
            error=error,
            response_summary=response_summary,
        )

    def trace_permission(
        self,
        permission_id: str,
        action: str,
        *,
        granted: bool | None = None,
        reason: str = '',
        dialog_shown: bool = False,
    ) -> dict[str, Any]:
        """Record a permission check/grant/deny."""
        return self.trace(
            'permission',
            permission_id=permission_id,
            action=action,
            granted=granted,
            reason=reason,
            dialog_shown=dialog_shown,
        )

    def trace_resource_snapshot(
        self,
        *,
        ram_used_pct: float = 0.0,
        cpu_load: float = 0.0,
        thread_count: int = 0,
        **extra: Any,
    ) -> dict[str, Any]:
        """Record a periodic resource snapshot."""
        return self.trace(
            'resource_snapshot',
            ram_used_pct=round(ram_used_pct, 1),
            cpu_load=round(cpu_load, 2),
            thread_count=thread_count,
            **extra,
        )

    def trace_error(
        self,
        context: str,
        error_type: str,
        message: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Record an exception or error."""
        return self.trace(
            'error',
            context=context,
            error_type=error_type,
            message=message,
            **extra,
        )

    def trace_dispatch_started(
        self,
        *,
        task_name: str,
        dispatch_id: str = '',
        interaction_id: str = '',
        provider: str = '',
        source: str = '',
        user_goal_excerpt: str = '',
        visible_busy_label: str = '',
    ) -> dict[str, Any]:
        """Record a dispatch being started (worker spawned).

        Paired with ``trace_dispatch_terminal`` to reconstruct full
        lifecycle: started → terminal state.
        """
        return self.trace(
            'dispatch_started',
            task_name=task_name,
            dispatch_id=dispatch_id[:12] if dispatch_id else '',
            interaction_id=interaction_id,
            provider=provider,
            source=source,
            user_goal_excerpt=user_goal_excerpt[:120] if user_goal_excerpt else '',
            visible_busy_label=visible_busy_label[:120] if visible_busy_label else '',
        )

    def trace_dispatch_terminal(
        self,
        *,
        task_name: str,
        dispatch_id: str = '',
        terminal_state: str,
        interaction_id: str = '',
        provider: str = '',
        reason: str = '',
        user_visible_message_present: bool = False,
    ) -> dict[str, Any]:
        """Record a dispatch reaching a terminal state.

        Covers: timeout watchdog, stale worker discard, external tool blocked,
        security_verification / permission / quota blocks, and normal success/failure.
        """
        return self.trace(
            'dispatch_terminal',
            task_name=task_name,
            dispatch_id=dispatch_id[:12] if dispatch_id else '',
            terminal_state=terminal_state,
            interaction_id=interaction_id,
            provider=provider,
            reason=reason[:200] if reason else '',
            user_visible_message_present=user_visible_message_present,
        )

    def trace_ui_event(
        self,
        event_type: str,
        component: str = '',
        **extra: Any,
    ) -> dict[str, Any]:
        """Record a UI event (page load, button click, freeze detected)."""
        return self.trace(
            'ui_event',
            event_type=event_type,
            component=component,
            **extra,
        )

    def trace_freeze_incident(
        self,
        incident_type: str,
        *,
        severity: str = 'high',
        duration_ms: float = 0.0,
        dominant_phase: str = '',
        rss_mb: float = 0.0,
        report_path: str = '',
        **extra: Any,
    ) -> dict[str, Any]:
        """Record a freeze/stall incident detected by auto-capture."""
        return self.trace(
            'freeze_incident',
            incident_type=incident_type,
            severity=severity,
            duration_ms=round(duration_ms, 1),
            dominant_phase=dominant_phase,
            rss_mb=round(rss_mb, 1),
            report_path=report_path,
            **extra,
        )

    def trace_build_fingerprint(self, workspace: str | Path = '') -> dict[str, Any]:
        """Record a runtime_build_fingerprint event at startup.

        Collects git branch, HEAD commit, dirty flag, origin/main HEAD,
        and probes for feature markers introduced in recent P0 slices.
        """
        fp = _collect_build_fingerprint(workspace or '.')
        event = self.trace('runtime_build_fingerprint', **fp)
        if fp.get('budget_exceeded'):
            self.trace(
                'runtime_build_fingerprint_slow',
                elapsed_ms=fp.get('elapsed_ms', 0),
                budget_ms=_FINGERPRINT_BUDGET_MS,
            )
        return event

    def current_elapsed_ms(self) -> float:
        """Return milliseconds since tracer boot (process-relative)."""
        return round((time.perf_counter() - self._t0) * 1000.0, 1)

    # ------------------------------------------------------------------
    # Query / export
    # ------------------------------------------------------------------

    def events(self, *, kind: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent in-memory events, optionally filtered by kind."""
        with self._lock:
            source = list(self._in_memory)
        if kind:
            source = [e for e in source if e.get('kind') == kind]
        return source[-limit:]

    def recent_dispatch_lifecycles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Reconstruct recent dispatch lifecycles by correlating started/terminal events.

        Returns a list of dicts sorted newest-first with keys:
        ``task_name``, ``dispatch_id``, ``started_at``, ``terminal_at``,
        ``duration_ms``, ``terminal_state``, ``provider``,
        ``user_visible_message_present``, ``unresolved``,
        ``orphan_terminal``.

        Priority order:
        1. Lifecycles with ``dispatch_id`` (correlated *and* unresolved),
           sorted by ``started_at`` descending — newest first regardless
           of whether they have a terminal event.
        2. Orphan terminals (terminal without matching started), sorted
           by ``terminal_at`` descending.

        An entry is ``unresolved=True`` when a ``dispatch_started`` event
        has no matching ``dispatch_terminal`` event.
        An entry is ``orphan_terminal=True`` when a ``dispatch_terminal``
        event has no matching ``dispatch_started`` event.
        """
        started_events = self.events(kind='dispatch_started', limit=500)
        terminal_events = self.events(kind='dispatch_terminal', limit=500)

        terminal_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for ev in terminal_events:
            d = ev.get('data', {})
            key = (d.get('task_name', ''), d.get('dispatch_id', ''))
            terminal_by_key[key] = ev

        dispatched: list[dict[str, Any]] = []
        for sev in started_events:
            sd = sev.get('data', {})
            task_name = sd.get('task_name', '')
            dispatch_id = sd.get('dispatch_id', '')
            key = (task_name, dispatch_id)
            tev = terminal_by_key.pop(key, None)
            started_ms = sev.get('elapsed_ms', 0.0)
            entry: dict[str, Any] = {
                'task_name': task_name,
                'dispatch_id': dispatch_id,
                'started_at': sev.get('ts', ''),
                'terminal_at': '',
                'duration_ms': 0.0,
                'terminal_state': '',
                'provider': sd.get('provider', ''),
                'user_visible_message_present': False,
                'unresolved': True,
                'orphan_terminal': False,
            }
            if tev is not None:
                td = tev.get('data', {})
                terminal_ms = tev.get('elapsed_ms', 0.0)
                entry['terminal_at'] = tev.get('ts', '')
                entry['duration_ms'] = round(terminal_ms - started_ms, 1)
                entry['terminal_state'] = td.get('terminal_state', '')
                entry['provider'] = td.get('provider', '') or entry['provider']
                entry['user_visible_message_present'] = td.get('user_visible_message_present', False)
                entry['unresolved'] = False
            dispatched.append(entry)

        orphans: list[dict[str, Any]] = []
        for key, tev in terminal_by_key.items():
            td = tev.get('data', {})
            orphans.append({
                'task_name': td.get('task_name', ''),
                'dispatch_id': td.get('dispatch_id', ''),
                'started_at': '',
                'terminal_at': tev.get('ts', ''),
                'duration_ms': 0.0,
                'terminal_state': td.get('terminal_state', ''),
                'provider': td.get('provider', ''),
                'user_visible_message_present': td.get('user_visible_message_present', False),
                'unresolved': False,
                'orphan_terminal': True,
            })

        dispatched.sort(key=lambda e: e.get('started_at', ''), reverse=True)
        orphans.sort(key=lambda e: e.get('terminal_at', ''), reverse=True)

        result = dispatched + orphans
        return result[:limit]

    def summary(self) -> dict[str, Any]:
        """Quick summary of trace state for diagnostics."""
        with self._lock:
            events = list(self._in_memory)
        kinds: dict[str, int] = {}
        errors = 0
        for e in events:
            k = e.get('kind', 'unknown')
            kinds[k] = kinds.get(k, 0) + 1
            if k == 'error':
                errors += 1
        return {
            'total_events': self._event_count,
            'in_memory': len(events),
            'enabled': self._enabled,
            'log_dir': str(self._log_dir) if self._log_dir else None,
            'kinds': kinds,
            'errors': errors,
            'uptime_ms': round((time.perf_counter() - self._t0) * 1000.0, 1),
        }

    def export_boot_report(self) -> dict[str, Any]:
        """Export a structured report of the boot sequence for AI analysis.

        Groups service_init events by timing and highlights bottlenecks,
        failed services, and disconnected dependencies.
        """
        inits = self.events(kind='service_init', limit=500)
        errors = self.events(kind='error', limit=100)
        ext_queries = self.events(kind='external_query', limit=100)
        permissions = self.events(kind='permission', limit=100)

        total_boot_ms = max(
            (e.get('elapsed_ms', 0) for e in inits),
            default=0,
        )

        failed_services = [
            e['data'] for e in inits
            if e.get('data', {}).get('status') != 'ok'
        ]
        slow_services = sorted(
            [e['data'] for e in inits if e.get('data', {}).get('duration_ms', 0) > 500],
            key=lambda d: d.get('duration_ms', 0),
            reverse=True,
        )
        failed_queries = [
            e['data'] for e in ext_queries
            if e.get('data', {}).get('status') not in ('ok', 'success')
        ]
        denied_permissions = [
            e['data'] for e in permissions
            if e.get('data', {}).get('granted') is False
        ]

        return {
            'total_boot_ms': round(total_boot_ms, 1),
            'services_initialized': len(inits),
            'services_failed': failed_services,
            'services_slow': slow_services[:10],
            'external_queries_attempted': len(ext_queries),
            'external_queries_failed': failed_queries,
            'permissions_checked': len(permissions),
            'permissions_denied': denied_permissions,
            'errors_during_boot': [
                {
                    'context': e.get('data', {}).get('context', ''),
                    'error_type': e.get('data', {}).get('error_type', ''),
                    'message': e.get('data', {}).get('message', ''),
                }
                for e in errors
            ],
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append(self, event: dict[str, Any]) -> None:
        if self._log_dir is None:
            return
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            target = self._log_dir / 'runtime_audit.jsonl'
            with target.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(event, ensure_ascii=False, default=str) + '\n')
        except Exception as exc:
            logger.warning('RuntimeAuditTracer._append failed (log_dir=%s): %s', self._log_dir, exc)


# ======================================================================
# Global singleton
# ======================================================================

_GLOBAL: RuntimeAuditTracer | None = None
_GLOBAL_LOCK = threading.Lock()


def get_runtime_tracer() -> RuntimeAuditTracer:
    """Return the process-global RuntimeAuditTracer, creating on first use."""
    global _GLOBAL
    with _GLOBAL_LOCK:
        if _GLOBAL is None:
            _GLOBAL = RuntimeAuditTracer()
        return _GLOBAL


def configure_runtime_tracer(log_dir: str | Path) -> RuntimeAuditTracer:
    """Configure the global tracer with a log directory."""
    tracer = get_runtime_tracer()
    tracer.configure(log_dir)
    return tracer
