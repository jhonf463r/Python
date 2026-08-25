"""Boot profile telemetry store — persists boot sessions per environment_id.

Append-only JSONL store at ``data/evolution/boot_profiles/{environment_id}.jsonl``.
Each line records one boot session: timeline events, duration, RSS peak, phase
breakdown.  Aggregation methods provide avg/median/p95 boot time, slowest
phases, and cross-environment comparison.

This is the **telemetry + persistence** layer only.  It does NOT make boot
decisions — that will be a future layer that consumes these profiles.

Design constraints:
- No new sovereign models (uses plain dicts)
- No boot-decision logic
- Crash-safe: I/O errors are swallowed (telemetry must never break boot)
- Thread-safe for concurrent reads/writes
"""
from __future__ import annotations

import json
import logging
import statistics
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BootProfileStore:
    """Persist and aggregate boot telemetry per environment_id."""

    def __init__(self, data_root: Path | str) -> None:
        self._profiles_dir = Path(data_root) / 'evolution' / 'boot_profiles'
        self._lock = threading.Lock()

    def _profile_path(self, environment_id: str) -> Path:
        safe_id = environment_id or 'unknown'
        return self._profiles_dir / f'{safe_id}.jsonl'

    def record_boot_session(
        self,
        *,
        environment_id: str,
        timeline_events: list[dict[str, Any]],
        boot_duration_ms: float | None = None,
        wiring_duration_ms: float | None = None,
        rss_peak_mb: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one boot session record for the given environment.

        Args:
            environment_id: stable fingerprint from EnvironmentSelfAwarenessService
            timeline_events: list of dicts from StartupTimeline.events()
            boot_duration_ms: full boot wall-clock up to page_loader_ready
                or splash_window_closing (auto-computed from timeline if None)
            wiring_duration_ms: time from bootstrap_init_start to
                wire_services_done — the backend-only portion of boot.
                Semantically distinct from boot_duration_ms which
                includes QML rendering and splash dismiss.
            rss_peak_mb: RSS peak during boot (auto-computed if None)
            metadata: extra context (scan_mode, deferred flags, etc.)

        Returns:
            The persisted record dict.
        """
        if boot_duration_ms is None:
            boot_duration_ms = self._compute_boot_duration(timeline_events)
        if rss_peak_mb is None:
            rss_peak_mb = self._compute_rss_peak(timeline_events)
        if wiring_duration_ms is None:
            wiring_duration_ms = self._compute_wiring_duration(timeline_events)

        phase_durations = self._compute_phase_durations(timeline_events)

        record: dict[str, Any] = {
            'environment_id': environment_id,
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'boot_duration_ms': round(boot_duration_ms, 1),
            'wiring_duration_ms': round(wiring_duration_ms, 1) if wiring_duration_ms is not None else 0.0,
            'rss_peak_mb': round(rss_peak_mb, 1),
            'phase_count': len(timeline_events),
            'phase_durations': phase_durations,
            'phases': [e.get('phase', '') for e in timeline_events],
        }
        if metadata:
            record['metadata'] = metadata

        with self._lock:
            try:
                self._profiles_dir.mkdir(parents=True, exist_ok=True)
                path = self._profile_path(environment_id)
                with path.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            except Exception as exc:
                logger.warning('boot_profile_store: write failed: %s', exc)

        logger.info(
            'boot_profile_store: recorded boot for %s — %.0fms RSS=%.1fMB phases=%d',
            environment_id, boot_duration_ms, rss_peak_mb, len(timeline_events),
        )
        return record

    def load_history(self, environment_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Load boot history for an environment, most recent last."""
        path = self._profile_path(environment_id)
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        try:
            with path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return []
        if limit and len(records) > limit:
            records = records[-limit:]
        return records

    def _session_metadata(self, environment_id: str) -> tuple[int, str]:
        """Count total sessions and extract first_seen without full parse.

        Reads the JSONL line-by-line, only parsing the first line to get
        ``timestamp_utc``.  Returns ``(total_count, first_seen_iso)``.
        """
        path = self._profile_path(environment_id)
        if not path.exists():
            return 0, ''
        count = 0
        first_seen = ''
        try:
            with path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    count += 1
                    if count == 1:
                        try:
                            first_seen = json.loads(line).get('timestamp_utc', '')
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass
        return count, first_seen

    def boot_profile_summary(self, environment_id: str) -> dict[str, Any]:
        """Aggregate boot metrics for an environment.

        Returns:
            Dict with boot_count, avg/median/p95 boot time, rss stats,
            slowest phases, first/last seen timestamps.

        ``boot_count`` and ``first_seen`` are derived from a full line
        count of the JSONL file so they stay accurate even when the
        statistical window (last 50 sessions) is smaller than the total.
        """
        total_count, first_seen = self._session_metadata(environment_id)
        if total_count == 0:
            return {
                'environment_id': environment_id,
                'boot_count': 0,
                'status': 'no_data',
            }

        history = self.load_history(environment_id, limit=50)
        if not history:
            return {
                'environment_id': environment_id,
                'boot_count': total_count,
                'status': 'no_data',
            }

        durations = [r['boot_duration_ms'] for r in history if 'boot_duration_ms' in r]
        wiring_durations = [r['wiring_duration_ms'] for r in history if r.get('wiring_duration_ms', 0) > 0]
        rss_peaks = [r['rss_peak_mb'] for r in history if 'rss_peak_mb' in r]

        phase_totals: dict[str, list[float]] = {}
        for r in history:
            for pd in (r.get('phase_durations') or []):
                phase = pd.get('phase', '')
                ms = pd.get('duration_ms', 0)
                if phase:
                    phase_totals.setdefault(phase, []).append(ms)

        slowest_phases = sorted(
            [
                {'phase': phase, 'avg_ms': round(statistics.mean(times), 1)}
                for phase, times in phase_totals.items()
                if len(times) >= 1
            ],
            key=lambda x: x['avg_ms'],
            reverse=True,
        )[:5]

        return {
            'environment_id': environment_id,
            'boot_count': total_count,
            'first_seen': first_seen,
            'last_seen': history[-1].get('timestamp_utc', ''),
            'boot_duration': {
                'avg_ms': round(statistics.mean(durations), 1) if durations else 0,
                'median_ms': round(statistics.median(durations), 1) if durations else 0,
                'p95_ms': round(_percentile(durations, 95), 1) if durations else 0,
                'min_ms': round(min(durations), 1) if durations else 0,
                'max_ms': round(max(durations), 1) if durations else 0,
            },
            'wiring_duration': {
                'avg_ms': round(statistics.mean(wiring_durations), 1) if wiring_durations else 0,
                'max_ms': round(max(wiring_durations), 1) if wiring_durations else 0,
            },
            'rss_peak': {
                'avg_mb': round(statistics.mean(rss_peaks), 1) if rss_peaks else 0,
                'max_mb': round(max(rss_peaks), 1) if rss_peaks else 0,
            },
            'slowest_phases': slowest_phases,
        }

    def all_known_profiles(self) -> list[str]:
        """List all environment_ids with boot data."""
        if not self._profiles_dir.exists():
            return []
        return sorted(
            p.stem for p in self._profiles_dir.glob('*.jsonl')
            if p.stat().st_size > 0
        )

    def compare_environments(self) -> dict[str, Any]:
        """Cross-environment boot comparison."""
        env_ids = self.all_known_profiles()
        if not env_ids:
            return {'environments': [], 'comparison': []}

        summaries = []
        for env_id in env_ids:
            summary = self.boot_profile_summary(env_id)
            if summary.get('boot_count', 0) > 0 and 'boot_duration' in summary:
                summaries.append(summary)

        comparison = sorted(
            [
                {
                    'environment_id': s['environment_id'],
                    'boot_count': s['boot_count'],
                    'avg_boot_ms': s['boot_duration']['avg_ms'],
                    'median_boot_ms': s['boot_duration']['median_ms'],
                    'avg_rss_mb': s['rss_peak']['avg_mb'],
                    'last_seen': s.get('last_seen', ''),
                }
                for s in summaries
            ],
            key=lambda x: x['avg_boot_ms'],
        )

        return {
            'environments': env_ids,
            'comparison': comparison,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_boot_duration(events: list[dict[str, Any]]) -> float:
        """Extract total boot duration from timeline events.

        Uses the last recorded milestone so that when the snapshot is
        taken at ``page_loader_ready`` or ``splash_window_closing`` the
        result reflects the full visible boot, not just wiring.
        """
        if not events:
            return 0.0
        times = [e.get('t_ms_from_start', 0) for e in events]
        return max(times) - min(times) if times else 0.0

    @staticmethod
    def _compute_wiring_duration(events: list[dict[str, Any]]) -> float:
        """Extract wiring-only duration (bootstrap_init_start → wire_services_done).

        Semantically distinct from ``boot_duration_ms``: wiring is the
        backend service construction time, before QML rendering begins.
        """
        if not events:
            return 0.0
        init_t: float | None = None
        done_t: float | None = None
        for e in events:
            phase = e.get('phase', '')
            t = e.get('t_ms_from_start', 0)
            if phase == 'bootstrap_init_start':
                init_t = t
            elif phase == 'wire_services_done':
                done_t = t
        if init_t is not None and done_t is not None:
            return done_t - init_t
        return 0.0

    @staticmethod
    def _compute_rss_peak(events: list[dict[str, Any]]) -> float:
        """Extract RSS peak from timeline events."""
        if not events:
            return 0.0
        rss_values = [e.get('rss_mb', 0) for e in events if e.get('rss_mb', 0) > 0]
        return max(rss_values) if rss_values else 0.0

    @staticmethod
    def _compute_phase_durations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compute duration of each phase transition."""
        if len(events) < 2:
            return []
        durations: list[dict[str, Any]] = []
        for i in range(1, len(events)):
            prev_t = events[i - 1].get('t_ms_from_start', 0)
            curr_t = events[i].get('t_ms_from_start', 0)
            durations.append({
                'phase': events[i].get('phase', ''),
                'duration_ms': round(curr_t - prev_t, 1),
            })
        return durations


def _percentile(data: list[float], pct: float) -> float:
    """Compute the *pct*-th percentile of *data* (simple nearest-rank)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = int(len(sorted_data) * pct / 100.0)
    k = min(k, len(sorted_data) - 1)
    return sorted_data[k]
