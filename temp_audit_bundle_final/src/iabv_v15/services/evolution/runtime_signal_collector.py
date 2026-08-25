from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import IssueSeverity, RuntimeSignal


class RuntimeSignalCollector:
    def capture_tick(self, *, episode_id: str | None, site_id: str, runtime_snapshot: dict[str, Any]) -> list[RuntimeSignal]:
        snapshot = runtime_snapshot or {}
        signals: list[RuntimeSignal] = []
        active_url = snapshot.get('last_active_url', '')
        if snapshot.get('page_count', 0) > 1:
            signals.append(
                RuntimeSignal(
                    episode_id=episode_id,
                    site_id=site_id,
                    signal_kind='multi_tab_runtime',
                    summary=f"Sesi?n con {int(snapshot.get('page_count', 0) or 0)} pesta?as detectadas.",
                    severity=IssueSeverity.LOW,
                    metadata={
                        'active_url': active_url,
                        'recent_urls': list(snapshot.get('recent_urls', []))[:3],
                    },
                )
            )
        if float(snapshot.get('seconds_since_last_visible_progress', 0.0) or 0.0) >= 4.0:
            signals.append(
                RuntimeSignal(
                    episode_id=episode_id,
                    site_id=site_id,
                    signal_kind='visible_progress_idle',
                    summary='Hay heartbeat activo, pero el progreso visible esta lento.',
                    severity=IssueSeverity.LOW,
                    metadata={
                        'seconds_since_last_visible_progress': snapshot.get('seconds_since_last_visible_progress', 0.0),
                        'active_url': active_url,
                    },
                )
            )
        if int(snapshot.get('queue_depth', 0) or 0) >= 40:
            signals.append(
                RuntimeSignal(
                    episode_id=episode_id,
                    site_id=site_id,
                    signal_kind='bridge_backlog',
                    summary='La cola de eventos visibles esta creciendo.',
                    severity=IssueSeverity.MEDIUM,
                    metadata={
                        'queue_depth': snapshot.get('queue_depth', 0),
                        'poll_without_progress_count': snapshot.get('poll_without_progress_count', 0),
                    },
                )
            )
        if float(snapshot.get('max_unobserved_tab_age', 0.0) or 0.0) >= 1.0:
            signals.append(
                RuntimeSignal(
                    episode_id=episode_id,
                    site_id=site_id,
                    signal_kind='tab_pending_attach',
                    summary='Hay pesta?as nuevas esperando observacion completa.',
                    severity=IssueSeverity.LOW,
                    metadata={
                        'max_unobserved_tab_age': snapshot.get('max_unobserved_tab_age', 0.0),
                        'page_count': snapshot.get('page_count', 0),
                        'observed_page_count': snapshot.get('observed_page_count', 0),
                    },
                )
            )
        return signals
