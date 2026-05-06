"""Freeze Incident Reporter — structured auto-audit for UI freezes.

When the program detects (or the user reports) a freeze or hang, this
service captures a comprehensive snapshot of everything that was happening
at that moment:

- System resources (RAM, CPU, heavy processes)
- Active threads and what they were doing
- SQLite lock state
- Startup timeline events (if still in boot)
- OSES findings and risk signals
- Background resource monitor history and anomalies
- Pending queue state (what the program was trying to do)
- User activity state (typing, idle, absent)

The report is written as a single structured JSON file to
``data/evolution/incident_reports/freeze_YYYYMMDD_HHMMSS.json``
so that any AI (Windsurf, Devin, IABV itself) can read it and
provide a precise diagnosis.

The reporter is lightweight by design: it reads existing state
rather than collecting new data.  Heavy analysis (deep memory
profiling, thread dumps) is deferred to the ``audit_mode`` flag.

Usage
~~~~~
Constructed once in ``bootstrap.py`` and called:

- **Automatically** when ``BackgroundResourceMonitor`` detects a
  critical anomaly or when ``_assess_resource_pressure`` returns
  CRITICAL.
- **Manually** via the MCP ``autonomy_report_freeze`` tool when the
  user says "se congeló".
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def _thread_snapshot() -> list[dict[str, Any]]:
    """Capture a snapshot of all active threads."""
    threads: list[dict[str, Any]] = []
    for t in threading.enumerate():
        threads.append({
            'name': t.name,
            'daemon': t.daemon,
            'alive': t.is_alive(),
            'ident': t.ident,
        })
    return threads


def _sqlite_lock_probe(db_path: str | None) -> dict[str, Any]:
    """Quick non-blocking probe of SQLite lock state."""
    if not db_path or not Path(db_path).exists():
        return {'status': 'no_db', 'path': db_path or ''}
    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=0.5)
        conn.execute('PRAGMA journal_mode')
        mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
        busy = conn.execute('PRAGMA busy_timeout').fetchone()[0]
        conn.close()
        return {
            'status': 'ok',
            'path': db_path,
            'journal_mode': mode,
            'busy_timeout': busy,
        }
    except sqlite3.OperationalError as exc:
        return {
            'status': 'locked' if 'locked' in str(exc) else 'error',
            'path': db_path,
            'error': str(exc),
        }
    except Exception as exc:
        return {'status': 'error', 'path': db_path, 'error': str(exc)}


class FreezeIncidentReporter:
    """Captures comprehensive freeze/incident reports for AI-readable audit.

    Each report is a self-contained JSON file with all the context an AI
    needs to diagnose what happened and why.
    """

    _DEDUP_WINDOW_SECONDS = 300  # min seconds between auto-captures of same type

    def __init__(
        self,
        evolution_dir: str | Path,
        *,
        db_path: str | None = None,
    ) -> None:
        self._report_dir = Path(evolution_dir).resolve() / 'incident_reports'
        self._report_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._last_auto_capture: dict[str, float] = {}

    def capture_incident(
        self,
        *,
        trigger: str = 'auto',
        user_description: str = '',
        resource_orchestrator: Any | None = None,
        startup_timeline: Any | None = None,
        environment_self_model: Any | None = None,
        pending_queue: Any | None = None,
        oses: Any | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> Path:
        """Capture a full incident snapshot and write it to disk.

        Parameters
        ----------
        trigger
            How the report was triggered: ``'auto'`` (detected by monitor),
            ``'user'`` (user reported via MCP/UI), ``'startup'`` (detected
            during boot).
        user_description
            Free-text description from the user (e.g. "se congeló al abrir
            el panel de evolución").
        resource_orchestrator
            ``AdaptiveResourceOrchestrator`` instance (optional).
        startup_timeline
            ``StartupTimeline`` instance (optional).
        environment_self_model
            ``EnvironmentSelfModel`` instance (optional).
        pending_queue
            ``PlatformPendingQueue`` instance (optional).
        oses
            ``OperationalSelfExaminationService`` instance (optional).
        extra_context
            Arbitrary extra data to include in the report.

        Returns
        -------
        Path
            The path to the written report file.
        """
        ts = datetime.now(timezone.utc)
        report: dict[str, Any] = {
            'report_version': '1.0',
            'timestamp': ts.isoformat(timespec='milliseconds'),
            'trigger': trigger,
            'user_description': user_description,
        }

        # 1. System resources
        report['resources'] = self._capture_resources(resource_orchestrator)

        # 2. Active threads
        report['threads'] = _thread_snapshot()

        # 3. SQLite state
        report['sqlite'] = _sqlite_lock_probe(self._db_path)

        # 4. Startup timeline (if available)
        report['startup_timeline'] = self._capture_timeline(startup_timeline)

        # 5. Resource monitor history + anomalies
        report['monitor_history'] = self._capture_monitor_history(
            resource_orchestrator,
        )

        # 6. Environment risk signals
        report['environment'] = self._capture_environment(
            environment_self_model,
        )

        # 7. Pending queue state
        report['pending_queue'] = self._capture_pending_queue(pending_queue)

        # 8. OSES findings (last review)
        report['oses_findings'] = self._capture_oses(oses)

        # 9. Process info
        report['process'] = {
            'pid': os.getpid(),
            'python_version': sys.version,
            'platform': sys.platform,
            'cwd': os.getcwd(),
        }

        # 10. Extra context
        if extra_context:
            report['extra'] = extra_context

        # Write report — include microseconds to avoid collisions.
        filename = f'freeze_{ts.strftime("%Y%m%d_%H%M%S_%f")}.json'
        path = self._report_dir / filename
        try:
            path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8',
            )
            logger.info(
                'freeze_incident_report: written to %s (%d bytes)',
                path, path.stat().st_size,
            )
        except Exception as exc:
            logger.warning('freeze_incident_report: write failed: %s', exc)

        return path

    def list_reports(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Return metadata of recent incident reports for quick inspection."""
        reports: list[dict[str, Any]] = []
        paths = sorted(
            self._report_dir.glob('freeze_*.json'),
            reverse=True,
        )
        for p in paths[:limit]:
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                reports.append({
                    'file': p.name,
                    'timestamp': data.get('timestamp', ''),
                    'trigger': data.get('trigger', ''),
                    'user_description': data.get('user_description', ''),
                    'resources_summary': {
                        'ram_pct': data.get('resources', {}).get(
                            'ram_used_pct', -1,
                        ),
                        'cpu_load': data.get('resources', {}).get(
                            'cpu_load', -1,
                        ),
                    },
                    'sqlite_status': data.get('sqlite', {}).get('status', ''),
                    'thread_count': len(data.get('threads', [])),
                })
            except Exception:
                reports.append({'file': p.name, 'error': 'parse_failed'})
        return reports

    def get_report(self, filename: str) -> dict[str, Any] | None:
        """Load a full incident report by filename."""
        path = self._report_dir / filename
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Auto-capture convenience methods
    # ------------------------------------------------------------------

    def _should_auto_capture(self, incident_type: str) -> bool:
        """Dedup guard: skip if same type was captured within the window."""
        now = time.time()
        last = self._last_auto_capture.get(incident_type, 0.0)
        if now - last < self._DEDUP_WINDOW_SECONDS:
            return False
        self._last_auto_capture[incident_type] = now
        return True

    def capture_startup_freeze(
        self,
        *,
        findings_metadata: list[dict[str, Any]],
        startup_timeline: Any | None = None,
        resource_orchestrator: Any | None = None,
        oses: Any | None = None,
    ) -> Path | None:
        """Auto-capture a startup/post-startup freeze from OSES findings.

        Called by OSES when ``_startup_health_findings()`` yields HIGH+
        severity findings.  Generates a structured incident referencing
        the dominant phase, RSS, and timeline context.
        """
        if not self._should_auto_capture('startup_freeze'):
            return None
        dominant = findings_metadata[0] if findings_metadata else {}
        extra: dict[str, Any] = {
            'incident_type': 'startup_freeze',
            'severity': str(dominant.get('severity', 'high')),
            'dominant_phase': str(dominant.get('metadata', {}).get('phase', '')),
            'dominant_phase_ms': dominant.get('metadata', {}).get('observed_ms')
                or dominant.get('metadata', {}).get('sync_blocking_ms', 0),
            'threshold_ms': dominant.get('metadata', {}).get('threshold_ms', 0),
            'findings_count': len(findings_metadata),
            'finding_titles': [f.get('title', '') for f in findings_metadata[:4]],
            'finding_categories': [f.get('category', '') for f in findings_metadata[:4]],
        }
        return self.capture_incident(
            trigger='auto_startup_freeze',
            user_description=(
                f'Auto-detected startup freeze: {dominant.get("title", "unknown")}'
            ),
            startup_timeline=startup_timeline,
            resource_orchestrator=resource_orchestrator,
            oses=oses,
            extra_context=extra,
        )

    def capture_chat_stall(
        self,
        *,
        duration_ms: float,
        timed_out: bool,
        message_summary: str = '',
        extra_context: dict[str, Any] | None = None,
    ) -> Path | None:
        """Auto-capture a chat/query stall from sendChat UI thread block.

        Called by ControlCenterViewModel when ``_sa_done.wait(timeout=3)``
        takes perceptibly long or times out.
        """
        if not self._should_auto_capture('chat_stall'):
            return None
        extra: dict[str, Any] = {
            'incident_type': 'chat_stall',
            'severity': 'high' if timed_out else 'medium',
            'duration_ms': round(duration_ms, 1),
            'timed_out': timed_out,
            'message_summary': message_summary[:200],
            **(extra_context or {}),
        }
        return self.capture_incident(
            trigger='auto_chat_stall',
            user_description=(
                f'Chat UI stall: {"timed out" if timed_out else "slow"} '
                f'({duration_ms:.0f}ms) during shortcut analysis'
            ),
            extra_context=extra,
        )

    def capture_query_stall(
        self,
        *,
        duration_ms: float,
        resolved_path: str = '',
        provider: str = '',
        route_reason: str = '',
        success: bool = True,
        message_summary: str = '',
        extra_context: dict[str, Any] | None = None,
    ) -> Path | None:
        """Auto-capture an end-to-end query stall (sendChat start → resolution).

        Fires when the wall-clock time from ``sendChat`` entry to the first
        visible assistant response (taskResolved / taskFailed / shortcut)
        exceeds the perceptible threshold.  Covers all execution paths:
        orchestrator_inference, external_consultation, chat_routing, fallback.
        """
        if not self._should_auto_capture('query_stall'):
            return None
        severity = 'high' if duration_ms > 15000 else 'medium'
        extra: dict[str, Any] = {
            'incident_type': 'query_stall',
            'severity': severity,
            'duration_ms': round(duration_ms, 1),
            'resolved_path': resolved_path,
            'provider': provider,
            'route_reason': route_reason,
            'success': success,
            'message_summary': message_summary[:200],
            **(extra_context or {}),
        }
        return self.capture_incident(
            trigger='auto_query_stall',
            user_description=(
                f'Query stall: {duration_ms:.0f}ms via {resolved_path}'
                f'{" (failed)" if not success else ""}'
            ),
            extra_context=extra,
        )

    def recent_incidents(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return recent incident summaries for PortableContext inclusion."""
        reports = self.list_reports(limit=limit)
        result: list[dict[str, Any]] = []
        for meta in reports:
            if meta.get('error'):
                continue
            full = self.get_report(meta.get('file', ''))
            if full is None:
                continue
            extra = full.get('extra', {})
            result.append({
                'file': meta.get('file', ''),
                'timestamp': full.get('timestamp', ''),
                'trigger': full.get('trigger', ''),
                'incident_type': extra.get('incident_type', full.get('trigger', '')),
                'severity': extra.get('severity', ''),
                'dominant_phase': extra.get('dominant_phase') or extra.get('resolved_path', ''),
                'duration_ms': extra.get('duration_ms') or extra.get('dominant_phase_ms', 0),
                'timed_out': extra.get('timed_out'),
                'finding_titles': extra.get('finding_titles', []),
                'resolved_path': extra.get('resolved_path', ''),
                'provider': extra.get('provider', ''),
                'success': extra.get('success'),
                'extra': dict(extra),
            })
        return result

    # ------------------------------------------------------------------
    # Private capture helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _capture_resources(
        orchestrator: Any | None,
    ) -> dict[str, Any]:
        """Capture resource state from the orchestrator or raw snapshot."""
        if orchestrator is not None and hasattr(orchestrator, 'get_scheduling_report'):
            try:
                report = orchestrator.get_scheduling_report()
                return report.get('resources', {})
            except Exception:
                pass
        # Fallback: direct snapshot
        try:
            from iabv_v15.services.intelligent_resource_manager import (
                take_resource_snapshot,
            )
            snap = take_resource_snapshot()
            return {
                'ram_total_mb': snap.ram_total_mb,
                'ram_available_mb': snap.ram_available_mb,
                'ram_used_pct': snap.ram_used_pct,
                'cpu_load': snap.cpu_load_1m,
                'cpu_count': snap.cpu_count,
                'heavy_processes': snap.heavy_processes[:5],
            }
        except Exception as exc:
            return {'error': str(exc)}

    @staticmethod
    def _capture_timeline(
        timeline: Any | None,
    ) -> list[dict[str, Any]]:
        if timeline is None:
            return []
        try:
            return timeline.events()[-20:]
        except Exception:
            return []

    @staticmethod
    def _capture_monitor_history(
        orchestrator: Any | None,
    ) -> dict[str, Any]:
        if orchestrator is None:
            return {}
        try:
            bg = getattr(orchestrator, '_bg_monitor', None)
            if bg is None:
                return {}
            summary = bg.get_history_summary()
            diagnoses = bg.get_bottleneck_diagnosis()
            return {
                'summary': summary,
                'bottleneck_diagnoses': diagnoses,
            }
        except Exception:
            return {}

    @staticmethod
    def _capture_environment(
        env_model: Any | None,
    ) -> dict[str, Any]:
        if env_model is None:
            return {}
        try:
            risk_signals = getattr(env_model, 'risk_signals', [])
            return {
                'scan_status': getattr(env_model, 'scan_status', ''),
                'risk_signals': [
                    {
                        'kind': getattr(s, 'kind', ''),
                        'severity': str(getattr(s, 'severity', '')),
                        'summary': getattr(s, 'summary', ''),
                        'metric_value': getattr(s, 'metric_value', None),
                    }
                    for s in (risk_signals or [])[:10]
                ],
            }
        except Exception:
            return {}

    @staticmethod
    def _capture_pending_queue(
        queue: Any | None,
    ) -> dict[str, Any]:
        if queue is None:
            return {}
        try:
            summary = queue.summary()
            actionable = queue.list_actionable()
            return {
                'summary': summary,
                'actionable_tasks': [
                    {
                        'id': t.id,
                        'title': t.title,
                        'priority': t.priority,
                        'category': t.category,
                    }
                    for t in actionable[:8]
                ],
            }
        except Exception:
            return {}

    @staticmethod
    def _capture_oses(
        oses: Any | None,
    ) -> list[dict[str, Any]]:
        if oses is None:
            return []
        try:
            if hasattr(oses, '_startup_health_findings'):
                findings = oses._startup_health_findings()
                return [
                    {
                        'category': getattr(f, 'category', ''),
                        'severity': str(getattr(f, 'severity', '')),
                        'title': getattr(f, 'title', ''),
                        'recommendation': getattr(f, 'recommendation', ''),
                    }
                    for f in (findings or [])[:10]
                ]
        except Exception:
            pass
        return []
