"""Startup birth-audit helpers.

This module reads the pre-Python startup audit emitted by
``scripts/start_iabv.ps1``.  It is intentionally a lightweight helper, not a
new orchestrator: PowerShell writes the black-box events, bootstrap hands them
to ``RuntimeAuditTracer``, and OSES/PortableContext consume the same JSONL.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STARTUP_AUDIT_FILENAME = 'startup_audit.jsonl'
RUNTIME_AUDIT_FILENAME = 'runtime_audit.jsonl'


def _logs_dir(workspace_root: str | Path) -> Path:
    root = Path(workspace_root)
    return root / 'data' / 'logs'


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_jsonl(path: str | Path, *, limit: int = 500) -> list[dict[str, Any]]:
    """Read parseable JSONL objects from ``path`` tail-first bounded by limit."""
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with target.open('r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        return []
    if limit > 0:
        return rows[-limit:]
    return rows


def read_startup_audit_events(
    workspace_root: str | Path,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    return read_jsonl(_logs_dir(workspace_root) / STARTUP_AUDIT_FILENAME, limit=limit)


def read_runtime_audit_events(
    workspace_root: str | Path,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    return read_jsonl(_logs_dir(workspace_root) / RUNTIME_AUDIT_FILENAME, limit=limit)


def _last_attempt(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    last_start_idx = 0
    for idx in range(len(events) - 1, -1, -1):
        if str(events[idx].get('event') or '') == 'startup_attempt':
            last_start_idx = idx
            break
    attempt_events = events[last_start_idx:]
    attempt_id = str(attempt_events[0].get('attempt_id') or '')
    if attempt_id:
        filtered = [e for e in events if str(e.get('attempt_id') or '') == attempt_id]
        if filtered:
            return filtered
    return attempt_events


def latest_startup_audit_event(workspace_root: str | Path) -> dict[str, Any] | None:
    """Return the newest pre-Python event for bootstrap handoff."""
    events = read_startup_audit_events(workspace_root, limit=200)
    return events[-1] if events else None


def startup_audit_snapshot(workspace_root: str | Path) -> dict[str, Any]:
    """Summarise launcher -> PowerShell -> Python handoff evidence.

    The result is compact by design so it can be embedded in PortableContext
    and OSES findings without copying large logs.
    """
    logs = _logs_dir(workspace_root)
    startup_path = logs / STARTUP_AUDIT_FILENAME
    runtime_path = logs / RUNTIME_AUDIT_FILENAME
    if not startup_path.exists():
        return {
            'status': 'no_log',
            'source': str(startup_path),
            'unresolved_fields': ['UNRESOLVED:startup_audit_missing'],
        }

    events = read_startup_audit_events(workspace_root, limit=500)
    if not events:
        return {
            'status': 'no_data',
            'source': str(startup_path),
            'unresolved_fields': ['UNRESOLVED:startup_audit_empty'],
        }

    attempt_events = _last_attempt(events)
    kinds = [str(e.get('event') or '') for e in attempt_events]
    last = attempt_events[-1] if attempt_events else events[-1]
    attempt_id = str(last.get('attempt_id') or '')
    first_ts = _parse_ts(attempt_events[0].get('timestamp_utc')) if attempt_events else None

    runtime_events = read_runtime_audit_events(workspace_root, limit=500)
    runtime_after: list[dict[str, Any]] = []
    if first_ts is not None:
        for event in runtime_events:
            event_ts = _parse_ts(event.get('ts'))
            if event_ts is None or event_ts >= first_ts:
                runtime_after.append(event)
    else:
        runtime_after = runtime_events

    runtime_kinds = [str(e.get('kind') or '') for e in runtime_after]
    handoff_received = 'startup_handoff_received' in runtime_kinds
    runtime_fingerprint = 'runtime_build_fingerprint' in runtime_kinds
    stale_lock_count = sum(1 for e in events if str(e.get('event') or '') == 'stale_lock_removed')
    hidden_process_count = sum(1 for e in events if str(e.get('event') or '') == 'existing_process_detected')
    script_error_count = sum(1 for e in events if str(e.get('event') or '') == 'startup_script_error')

    unresolved: list[str] = []
    recent_blockers: list[dict[str, Any]] = []
    if 'startup_attempt' in kinds and not runtime_fingerprint:
        unresolved.append('UNRESOLVED:startup_attempt_without_runtime_fingerprint')
        recent_blockers.append({'phase': 'startup_attempt_without_runtime_fingerprint'})
    if 'python_launch_failed' in kinds:
        unresolved.append('UNRESOLVED:python_launch_failed')
        recent_blockers.append({'phase': 'python_launch_failed'})
    if 'suspected_hung_start' in kinds:
        unresolved.append('UNRESOLVED:suspected_hung_start')
        recent_blockers.append({'phase': 'suspected_hung_start'})
    if hidden_process_count:
        recent_blockers.append({
            'phase': 'hidden_start_processes_seen',
            'count': hidden_process_count,
        })

    status = 'analyzed'
    if unresolved:
        status = 'needs_attention'
    elif handoff_received and runtime_fingerprint:
        status = 'handoff_complete'

    return {
        'status': status,
        'source': str(startup_path),
        'runtime_source': str(runtime_path),
        'attempt_id': attempt_id,
        'last_event': str(last.get('event') or ''),
        'last_timestamp_utc': str(last.get('timestamp_utc') or ''),
        'events_seen': kinds,
        'event_count': len(attempt_events),
        'python_launch_attempted': 'python_launch_attempt' in kinds,
        'python_launch_spawned': 'python_launch_spawned' in kinds or 'python_launch_success' in kinds,
        'bootstrap_handoff_received': handoff_received,
        'runtime_fingerprint_received': runtime_fingerprint,
        'stale_lock_count': stale_lock_count,
        'hidden_process_count': hidden_process_count,
        'startup_script_error_count': script_error_count,
        'recent_blockers': recent_blockers,
        'unresolved_fields': unresolved,
    }
