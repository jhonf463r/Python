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
                'dominant_phase': extra.get('dominant_phase', ''),
                'dominant_phase_at_detection': extra.get('dominant_phase_at_detection', ''),
                'duration_ms': extra.get('duration_ms') or extra.get('dominant_phase_ms', 0),
                'timed_out': extra.get('timed_out'),
                'finding_titles': extra.get('finding_titles', []),
                'has_live_stack': bool(extra.get('main_thread_stack_during_stall')),
                'startup_followup_active': extra.get('startup_followup_active'),
                'bootstrap_flags': extra.get('bootstrap_flags', {}),
            })
        return result

    # ------------------------------------------------------------------
    # Task 10: Freeze diagnostics — analyze WHY freezes happen and
    # recommend configuration adjustments for future sessions.
    # ------------------------------------------------------------------

    def diagnose_freeze_cause(self, *, limit: int = 10) -> dict[str, Any]:
        """Analyze recent freeze incidents and produce a diagnosis.

        Returns a structured diagnosis with:
        - dominant_cause: most frequent freeze cause
        - cause_distribution: count per cause type
        - severity_trend: whether freezes are getting worse
        - config_recommendations: actionable adjustments
        - summary: human-readable explanation

        Uses existing incident reports — does NOT create new services.
        """
        incidents = self.recent_incidents(limit=limit)
        if not incidents:
            return {
                'dominant_cause': 'none',
                'cause_distribution': {},
                'severity_trend': 'stable',
                'config_recommendations': [],
                'summary': 'No recent freeze incidents to analyze.',
                'incident_count': 0,
            }

        cause_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        phase_counts: dict[str, int] = {}
        total_duration_ms: float = 0.0
        startup_related = 0

        for inc in incidents:
            cause = inc.get('incident_type', 'unknown')
            cause_counts[cause] = cause_counts.get(cause, 0) + 1
            sev = inc.get('severity', 'unknown')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            phase = inc.get('dominant_phase') or inc.get('dominant_phase_at_detection') or 'unknown'
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            total_duration_ms += inc.get('duration_ms', 0)
            if inc.get('startup_followup_active'):
                startup_related += 1

        dominant_cause = max(cause_counts, key=cause_counts.get)  # type: ignore[arg-type]
        dominant_phase = max(phase_counts, key=phase_counts.get)  # type: ignore[arg-type]

        # Severity trend: compare recent half vs older half.
        # Incidents arrive newest-first from recent_incidents().
        half = len(incidents) // 2
        if half > 0:
            recent_half_critical = sum(
                1 for i in incidents[:half]
                if i.get('severity') in ('critical', 'high')
            )
            older_half_critical = sum(
                1 for i in incidents[half:]
                if i.get('severity') in ('critical', 'high')
            )
            if recent_half_critical > older_half_critical:
                severity_trend = 'worsening'
            elif recent_half_critical < older_half_critical:
                severity_trend = 'improving'
            else:
                severity_trend = 'stable'
        else:
            severity_trend = 'insufficient_data'

        recommendations: list[dict[str, str]] = []

        if startup_related > len(incidents) * 0.5:
            recommendations.append({
                'config': 'IABV_DEFER_METACOGNITION',
                'value': '1',
                'reason': f'{startup_related}/{len(incidents)} freezes are startup-related; '
                          'defer metacognition scans to reduce boot pressure.',
            })

        if dominant_phase.startswith('startup_background:'):
            recommendations.append({
                'config': 'IABV_STARTUP_EVOLUTION_DELAY_S',
                'value': '30',
                'reason': f'Dominant freeze phase is {dominant_phase}; '
                          'increase evolution delay to let UI stabilize first.',
            })

        avg_duration = total_duration_ms / len(incidents) if incidents else 0
        if avg_duration > 8000:
            recommendations.append({
                'config': 'IABV_REDUCE_PARALLEL_SCANS',
                'value': '1',
                'reason': f'Average freeze duration is {avg_duration:.0f}ms; '
                          'reduce parallel background scans to lower contention.',
            })

        if cause_counts.get('chat_stall', 0) > 2:
            recommendations.append({
                'config': 'IABV_CHAT_ASYNC_THRESHOLD_MS',
                'value': '1500',
                'reason': f'{cause_counts["chat_stall"]} chat stall incidents; '
                          'lower async threshold to offload processing sooner.',
            })

        if severity_trend == 'worsening':
            recommendations.append({
                'config': 'IABV_AGGRESSIVE_GC',
                'value': '1',
                'reason': 'Freeze severity is worsening over time; '
                          'enable aggressive GC between phases.',
            })

        summary_parts = [
            f'{len(incidents)} recent freeze incidents analyzed.',
            f'Dominant cause: {dominant_cause} ({cause_counts[dominant_cause]}x).',
            f'Dominant phase: {dominant_phase}.',
            f'Severity trend: {severity_trend}.',
        ]
        if recommendations:
            summary_parts.append(
                f'{len(recommendations)} configuration adjustment(s) recommended.'
            )

        return {
            'dominant_cause': dominant_cause,
            'dominant_phase': dominant_phase,
            'cause_distribution': cause_counts,
            'phase_distribution': phase_counts,
            'severity_distribution': severity_counts,
            'severity_trend': severity_trend,
            'avg_duration_ms': round(avg_duration, 1),
            'startup_related_ratio': round(startup_related / len(incidents), 2) if incidents else 0,
            'config_recommendations': recommendations,
            'summary': ' '.join(summary_parts),
            'incident_count': len(incidents),
        }

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


# ======================================================================
# UIHeartbeatWatchdog — lightweight main-thread heartbeat detector
# ======================================================================

class UIHeartbeatWatchdog:
    """Lightweight heartbeat monitor for the Qt/UI main thread.

    NOT a new service: it lives inside the freeze_incident_reporter module
    and is wired from bootstrap into the existing QTimer mechanism.

    How it works:
    - ``tick()`` is called periodically from a QTimer on the main thread
      (e.g. every 500 ms).
    - A background thread checks if ticks are arriving on time.
    - When the gap between ticks exceeds ``stall_threshold_ms``, a
      ``ui_event_loop_stall`` event is emitted via RuntimeAuditTracer
      and optionally captured via FreezeIncidentReporter.

    Context captured per stall:
    - startup_active: whether the app is still booting
    - query_pending: whether a chat query is being processed
    - window_visible: whether the main window is active/visible
    - duration_ms: how long the stall lasted
    - dominant_phase: best guess at what was blocking
    """

    DEFAULT_TICK_INTERVAL_MS = 500
    DEFAULT_STALL_THRESHOLD_MS = 2000
    DEFAULT_SAMPLER_INTERVAL_S: float = 0.5

    # Cooldown between incident captures of the same cause type (seconds).
    _INCIDENT_CAPTURE_COOLDOWN_S: float = 30.0

    def __init__(
        self,
        *,
        stall_threshold_ms: float = DEFAULT_STALL_THRESHOLD_MS,
        freeze_reporter: FreezeIncidentReporter | None = None,
        sampler_interval_s: float = DEFAULT_SAMPLER_INTERVAL_S,
    ) -> None:
        self._stall_threshold_ms = stall_threshold_ms
        self._freeze_reporter = freeze_reporter
        self._lock = threading.Lock()
        self._last_tick: float = time.perf_counter()
        self._tick_count: int = 0
        self._stall_count: int = 0
        self._stalls: list[dict[str, Any]] = []
        self._max_stalls = 50
        # Context flags — set externally by bootstrap / viewmodel
        self._startup_active: bool = True
        self._startup_followup_active: bool = False
        self._query_pending: bool = False
        self._window_visible: bool = True
        self._window_active: bool = True
        self._dominant_phase: str = ''
        self._active_interaction_id: str | None = None
        # Bootstrap active-flags snapshot for incident enrichment
        self._bootstrap_flags: dict[str, bool] = {}
        # Anti-storm guard for async incident capture
        self._capture_in_flight: bool = False
        self._capture_last_by_cause: dict[str, float] = {}
        # --- Async sampler state (captures DURING stall) ---
        self._sampler_interval_s = sampler_interval_s
        self._sampler_running: bool = False
        self._sampler_thread: threading.Thread | None = None
        # Stack captured by the sampler DURING a stall window.
        self._live_stall_stack: list[str] = []
        self._live_stall_dominant_phase: str = ''
        self._live_stall_bootstrap_flags: dict[str, bool] = {}
        self._live_stall_timestamp: str = ''

    # --- Async sampler (daemon thread external to event loop) ---

    def start_sampler(self) -> None:
        """Start the background sampler daemon thread.

        The sampler observes ``_last_tick`` every ~500ms.  When the gap
        exceeds ``_stall_threshold_ms`` it captures
        ``sys._current_frames()[main_thread_id]`` **during** the stall.
        No heavy IO is performed from the sampler.
        """
        if self._sampler_running:
            return
        self._sampler_running = True
        self._sampler_thread = threading.Thread(
            target=self._sampler_loop,
            name='watchdog-sampler',
            daemon=True,
        )
        self._sampler_thread.start()

    def stop_sampler(self) -> None:
        self._sampler_running = False

    def _sampler_loop(self) -> None:
        """Lightweight sampler loop running on a daemon thread.

        Reads ``_last_tick`` (cheap) and when a gap exceeds threshold,
        captures the main-thread stack via ``sys._current_frames()``.
        Does NOT do any IO / take_resource_snapshot / disk writes.
        """
        main_tid = threading.main_thread().ident
        while self._sampler_running:
            time.sleep(self._sampler_interval_s)
            if not self._sampler_running:
                break
            now = time.perf_counter()
            with self._lock:
                gap_ms = (now - self._last_tick) * 1000.0
            if gap_ms > self._stall_threshold_ms:
                # Capture live stack DURING the stall
                stack_lines: list[str] = []
                try:
                    frames = sys._current_frames()
                    if main_tid is not None and main_tid in frames:
                        import traceback as _tb
                        stack_lines = _tb.format_stack(frames[main_tid])[-12:]
                except Exception:
                    pass
                # Snapshot phase/flags at detection time (not recovery time)
                with self._lock:
                    self._live_stall_stack = stack_lines
                    self._live_stall_dominant_phase = self._dominant_phase
                    self._live_stall_bootstrap_flags = dict(self._bootstrap_flags)
                    self._live_stall_timestamp = (
                        datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                    )

    def _consume_live_stall_data(self) -> dict[str, Any]:
        """Consume the live stall data captured by the sampler."""
        with self._lock:
            data: dict[str, Any] = {}
            if self._live_stall_stack:
                data['main_thread_stack_during_stall'] = list(self._live_stall_stack)
                data['dominant_phase_at_detection'] = self._live_stall_dominant_phase
                data['bootstrap_flags_at_detection'] = dict(self._live_stall_bootstrap_flags)
                data['sampler_capture_timestamp'] = self._live_stall_timestamp
            # Reset after consumption
            self._live_stall_stack = []
            self._live_stall_dominant_phase = ''
            self._live_stall_bootstrap_flags = {}
            self._live_stall_timestamp = ''
            return data

    def tick(self) -> None:
        """Called from the main thread (QTimer). Records heartbeat."""
        now = time.perf_counter()
        with self._lock:
            gap_ms = (now - self._last_tick) * 1000.0
            self._last_tick = now
            self._tick_count += 1

        if gap_ms > self._stall_threshold_ms:
            self._record_stall(gap_ms)

    def _record_stall(self, duration_ms: float) -> None:
        # Consume live stall data captured by sampler DURING the stall.
        live_data = self._consume_live_stall_data()
        # Use dominant_phase from detection time if available;
        # fall back to current phase (which may be stale).
        dominant_phase_at_detection = live_data.get('dominant_phase_at_detection', '')
        effective_dominant_phase = dominant_phase_at_detection or self._dominant_phase
        if not effective_dominant_phase:
            if self._startup_active or self._startup_followup_active:
                # Derive from bootstrap flags
                for flag_name in ('deferred_setup_active', 'truth_refresh_active',
                                  'startup_evolution_active'):
                    if self._bootstrap_flags.get(flag_name):
                        effective_dominant_phase = f'startup_background:{flag_name.replace("_active", "")}'
                        break
                if not effective_dominant_phase:
                    if self._bootstrap_flags.get('prebuild_paused'):
                        effective_dominant_phase = 'prebuild_waiting:paused'
                    else:
                        effective_dominant_phase = 'event_loop_blocked_unknown'
            else:
                effective_dominant_phase = 'event_loop_blocked_unknown'

        stall_record: dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            'duration_ms': round(duration_ms, 1),
            'startup_active': self._startup_active,
            'startup_followup_active': self._startup_followup_active,
            'query_pending': self._query_pending,
            'window_visible': self._window_visible,
            'window_active': self._window_active,
            'dominant_phase': effective_dominant_phase,
            'interaction_id': self._active_interaction_id,
        }
        # Include live stall data from sampler
        if live_data.get('main_thread_stack_during_stall'):
            stall_record['main_thread_stack_during_stall'] = live_data['main_thread_stack_during_stall']
            stall_record['dominant_phase_at_detection'] = dominant_phase_at_detection
            stall_record['bootstrap_flags_at_detection'] = live_data.get('bootstrap_flags_at_detection', {})
            stall_record['sampler_capture_timestamp'] = live_data.get('sampler_capture_timestamp', '')
        # Post-stall stack (captured here, after event loop resumed)
        stall_record['post_stall_dominant_phase'] = self._dominant_phase
        # Derive semantic cause from context
        cause = 'ui_event_loop_stall'
        if self._startup_active or self._startup_followup_active:
            cause = 'startup_freeze'
        elif self._query_pending and (not self._window_active or not self._window_visible):
            cause = 'query_visible_gap'
        stall_record['cause'] = cause
        # Enrich from active interaction lifecycle if available
        stall_record.update(self._lifecycle_context_for_stall())
        with self._lock:
            self._stall_count += 1
            self._stalls.append(stall_record)
            if len(self._stalls) > self._max_stalls:
                self._stalls = self._stalls[-self._max_stalls:]

        # Emit to RuntimeAuditTracer
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import (
                get_runtime_tracer,
            )
            tracer = get_runtime_tracer()
            audit_data: dict[str, Any] = {
                'duration_ms': round(duration_ms, 1),
                'startup_active': self._startup_active,
                'startup_followup_active': self._startup_followup_active,
                'query_pending': self._query_pending,
                'window_visible': self._window_visible,
                'window_active': self._window_active,
                'dominant_phase': effective_dominant_phase,
                'interaction_id': self._active_interaction_id,
                'cause': cause,
                'bootstrap_flags': dict(self._bootstrap_flags),
            }
            if live_data.get('main_thread_stack_during_stall'):
                audit_data['has_live_stack'] = True
                audit_data['dominant_phase_at_detection'] = dominant_phase_at_detection
            tracer.trace('ui_event_loop_stall', **audit_data)
            # Emit separate query_visible_gap event when applicable
            if cause == 'query_visible_gap':
                tracer.trace(
                    'query_visible_gap',
                    duration_ms=round(duration_ms, 1),
                    interaction_id=self._active_interaction_id,
                    window_visible=self._window_visible,
                    window_active=self._window_active,
                    query_pending=self._query_pending,
                )
        except Exception:
            pass

        # Promote to FreezeIncidentReporter for severe stalls (>5s).
        # Runs in a daemon thread to avoid blocking the UI thread —
        # capture_incident() calls take_resource_snapshot() which takes
        # 15-18s on Windows (PowerShell/CIM subprocess).
        if duration_ms > 5000 and self._freeze_reporter is not None:
            self._capture_incident_async(
                duration_ms=duration_ms,
                stall_record=stall_record,
                cause=cause,
            )

        logger.warning(
            'ui_heartbeat_stall: %.0fms (startup=%s query=%s phase=%s)',
            duration_ms, self._startup_active, self._query_pending,
            self._dominant_phase,
        )

    def _capture_incident_async(
        self,
        *,
        duration_ms: float,
        stall_record: dict[str, Any],
        cause: str,
    ) -> None:
        """Launch incident capture in a background thread.

        Anti-storm guards:
        - At most one capture in-flight at a time.
        - Cooldown per cause type (``_INCIDENT_CAPTURE_COOLDOWN_S``).
        """
        # Guard 1: one in-flight max
        if self._capture_in_flight:
            return
        # Guard 2: cooldown per cause
        now = time.time()
        last = self._capture_last_by_cause.get(cause, 0.0)
        if now - last < self._INCIDENT_CAPTURE_COOLDOWN_S:
            return

        self._capture_in_flight = True
        self._capture_last_by_cause[cause] = now

        reporter = self._freeze_reporter
        phase = self._dominant_phase

        bootstrap_flags = dict(self._bootstrap_flags)
        followup_active = self._startup_followup_active

        # Capture post-stall main-thread stack (event loop has resumed).
        # sys._current_frames() is cheap (~0ms) and safe from any thread.
        post_stall_stack: list[str] = []
        try:
            frames = sys._current_frames()
            main_tid = threading.main_thread().ident
            if main_tid is not None and main_tid in frames:
                import traceback
                post_stall_stack = traceback.format_stack(frames[main_tid])[-8:]
        except Exception:
            pass

        def _worker() -> None:
            try:
                extra: dict[str, Any] = {
                    'incident_type': 'ui_event_loop_stall',
                    'severity': 'critical' if duration_ms > 10000 else 'high',
                    'startup_followup_active': followup_active,
                    'bootstrap_flags': bootstrap_flags,
                    **stall_record,
                }
                if post_stall_stack:
                    extra['post_stall_stack'] = post_stall_stack
                reporter.capture_incident(
                    trigger='auto_ui_heartbeat_stall',
                    user_description=(
                        f'UI event loop stall: {duration_ms:.0f}ms '
                        f'(phase={phase})'
                    ),
                    extra_context=extra,
                )
            except Exception:
                pass
            finally:
                self._capture_in_flight = False

        t = threading.Thread(target=_worker, daemon=True,
                             name='watchdog-incident-capture')
        t.start()

    # --- Context setters (called by bootstrap / viewmodel) ---

    def set_startup_active(self, active: bool) -> None:
        self._startup_active = active

    def set_startup_followup_active(self, active: bool) -> None:
        self._startup_followup_active = active

    def set_bootstrap_flags(self, flags: dict[str, bool]) -> None:
        """Snapshot of active bootstrap phases for incident enrichment."""
        self._bootstrap_flags = dict(flags)

    def set_query_pending(self, pending: bool) -> None:
        self._query_pending = pending

    def set_window_visible(self, visible: bool) -> None:
        self._window_visible = visible

    def set_window_active(self, active: bool) -> None:
        self._window_active = active

    def set_dominant_phase(self, phase: str) -> None:
        self._dominant_phase = phase

    def set_active_interaction(self, interaction_id: str | None) -> None:
        self._active_interaction_id = interaction_id

    # --- Query / export ---

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                'tick_count': self._tick_count,
                'stall_count': self._stall_count,
                'stall_threshold_ms': self._stall_threshold_ms,
                'recent_stalls': list(self._stalls[-5:]),
            }

    def recent_stalls(self, *, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._stalls[-limit:])

    def _lifecycle_context_for_stall(self) -> dict[str, Any]:
        """Pull enrichment fields from the active interaction lifecycle."""
        extra: dict[str, Any] = {}
        lc = getattr(self, '_lifecycle', None)
        if lc is None or self._active_interaction_id is None:
            return extra
        try:
            info = lc.interaction_info(self._active_interaction_id)
            if info is None:
                return extra
            extra['had_early_technical_response'] = 'first_technical_response' in (info.get('phases') or {})
            extra['window_went_inactive'] = len(info.get('window_inactive_intervals') or []) > 0
        except Exception:
            pass
        return extra

    def set_lifecycle(self, lifecycle: 'ChatInteractionLifecycle | None') -> None:
        """Wire the lifecycle reference for stall enrichment."""
        self._lifecycle = lifecycle


# ======================================================================
# ChatInteractionLifecycle — canonical interaction episode tracker
# ======================================================================

class ChatInteractionLifecycle:
    """Tracks the full lifecycle of a user chat interaction.

    NOT a new service: it lives in the same module and is used by
    ControlCenterViewModel to open/close interaction episodes.

    Each ``sendChat`` opens an episode with a unique interaction_id.
    The lifecycle correlates:
    - start (user sends message)
    - first_technical_response (system begins processing)
    - first_useful_response (system shows meaningful content)
    - dispatch_pending (external consultation started)
    - external_followup_pending (waiting for external result)
    - final_resolution (task resolved or failed)
    - window_inactive/active intervals
    - UI heartbeat stalls during the interaction
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._interactions: dict[str, dict[str, Any]] = {}
        self._completed: list[dict[str, Any]] = []
        self._max_completed = 30

    def open_interaction(
        self,
        message_preview: str = '',
        *,
        initial_window_active: bool = True,
        initial_window_visible: bool = True,
    ) -> str:
        """Open a new interaction episode. Returns the interaction_id."""
        from uuid import uuid4
        interaction_id = f'chat-{uuid4().hex[:12]}'
        now = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        record: dict[str, Any] = {
            'interaction_id': interaction_id,
            'started_at_utc': now_utc,
            'message_preview': message_preview[:120],
            '_t0': now,
            'phases': {
                'start': now_utc,
            },
            'stalls_during': [],
            'window_inactive_intervals': [],
            'initial_window_active': initial_window_active,
            'initial_window_visible': initial_window_visible,
            'resolved': False,
        }
        with self._lock:
            self._interactions[interaction_id] = record
        # Trace
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import (
                get_runtime_tracer,
            )
            get_runtime_tracer().trace(
                'interaction_open',
                interaction_id=interaction_id,
                message_preview=message_preview[:120],
            )
        except Exception:
            pass
        return interaction_id

    def mark_phase(self, interaction_id: str, phase: str) -> None:
        """Mark a lifecycle phase for the given interaction."""
        now_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        with self._lock:
            record = self._interactions.get(interaction_id)
            if record is None:
                return
            record['phases'][phase] = now_utc

    def record_stall(self, interaction_id: str, stall: dict[str, Any]) -> None:
        """Attach a UI heartbeat stall to the active interaction."""
        with self._lock:
            record = self._interactions.get(interaction_id)
            if record is None:
                return
            record['stalls_during'].append({
                'timestamp': stall.get('timestamp', ''),
                'duration_ms': stall.get('duration_ms', 0),
            })

    def record_window_inactive(self, interaction_id: str) -> None:
        now_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        with self._lock:
            record = self._interactions.get(interaction_id)
            if record is None:
                return
            record['window_inactive_intervals'].append({
                'inactive_at': now_utc,
            })

    def record_window_active(self, interaction_id: str) -> None:
        now_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        with self._lock:
            record = self._interactions.get(interaction_id)
            if record is None:
                return
            intervals = record['window_inactive_intervals']
            if intervals and 'active_at' not in intervals[-1]:
                intervals[-1]['active_at'] = now_utc

    # Semantic outcomes that do NOT count as final resolution.
    _NON_FINAL_OUTCOMES: frozenset[str] = frozenset({
        'prepared', 'awaiting_external_response', 'reused_context',
    })

    def resolve_interaction(
        self,
        interaction_id: str,
        *,
        outcome: str = 'resolved',
        provider: str = '',
    ) -> dict[str, Any] | None:
        """Close an interaction episode and move it to completed list.

        ``is_final`` and ``resolved`` are separate:
        - ``is_final=True``: ``resolved``, ``failed``, ``blocked`` — the
          episode is closed and moved to completed.
        - ``resolved=True``: only ``outcome == 'resolved'`` — the
          episode reached successful resolution.
        - ``blocked`` and ``failed`` are ``is_final=True, resolved=False``.
        - ``prepared``, ``awaiting_external_response``, ``reused_context``
          stay open (``is_final=False``).
        """
        is_final = outcome not in self._NON_FINAL_OUTCOMES
        now = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        with self._lock:
            record = self._interactions.pop(interaction_id, None)
            if record is None:
                return None
            phase_key = 'final_resolution' if is_final else f'outcome_{outcome}'
            record['phases'][phase_key] = now_utc
            record['resolved'] = outcome == 'resolved'
            record['outcome'] = outcome
            record['provider'] = provider
            if is_final:
                record['total_duration_ms'] = round(
                    (now - record.pop('_t0', now)) * 1000.0, 1,
                )
                self._completed.append(record)
                if len(self._completed) > self._max_completed:
                    self._completed = self._completed[-self._max_completed:]
            else:
                # Non-final: keep in active interactions for re-resolution.
                record['elapsed_ms_so_far'] = round(
                    (now - record.get('_t0', now)) * 1000.0, 1,
                )
                self._interactions[interaction_id] = record
        # Trace — persist the record for durable reconstruction.
        trace_kind = 'interaction_resolved' if is_final else 'interaction_outcome'
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import (
                get_runtime_tracer,
            )
            get_runtime_tracer().trace(
                trace_kind,
                interaction_id=interaction_id,
                message_preview=record.get('message_preview', ''),
                outcome=outcome,
                provider=provider,
                total_duration_ms=record.get('total_duration_ms', 0),
                phases=dict(record.get('phases') or {}),
                stalls_during=list(record.get('stalls_during') or []),
                stall_count=len(record.get('stalls_during', [])),
                window_inactive_intervals=list(
                    record.get('window_inactive_intervals') or [],
                ),
                initial_window_active=record.get('initial_window_active', True),
                initial_window_visible=record.get('initial_window_visible', True),
                had_early_technical_response='first_technical_response' in (
                    record.get('phases') or {}
                ),
                window_went_inactive=bool(
                    record.get('window_inactive_intervals'),
                ),
                is_final=is_final,
            )
        except Exception:
            pass
        return record

    # --- Query ---

    def interaction_info(self, interaction_id: str) -> dict[str, Any] | None:
        """Return a snapshot of an interaction (active or completed)."""
        with self._lock:
            record = self._interactions.get(interaction_id)
            if record is not None:
                return dict(record)
            for c in reversed(self._completed):
                if c.get('interaction_id') == interaction_id:
                    return dict(c)
        return None

    def active_interaction(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._interactions:
                return None
            # Return the most recent
            return dict(list(self._interactions.values())[-1])

    def recent_completed(self, *, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._completed[-limit:])

    def summary(self) -> dict[str, Any]:
        with self._lock:
            active_count = len(self._interactions)
            completed_count = len(self._completed)
            active_ids = list(self._interactions.keys())
        return {
            'active_count': active_count,
            'completed_count': completed_count,
            'active_ids': active_ids,
        }
