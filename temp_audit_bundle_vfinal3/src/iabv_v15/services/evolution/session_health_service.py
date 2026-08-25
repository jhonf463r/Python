from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import HiddenIncident, IncidentStatus, SessionHealthSnapshot


class SessionHealthService:
    def snapshot_for_teaching_session(
        self,
        *,
        episode_id: str | None,
        site_id: str,
        runtime_snapshot: dict[str, Any],
        incidents: list[HiddenIncident],
    ) -> SessionHealthSnapshot:
        snapshot = runtime_snapshot or {}
        active_incidents = [item for item in incidents if item.status in {IncidentStatus.OPEN, IncidentStatus.OBSERVED, IncidentStatus.NEEDS_FIX}]
        label = 'Sin incidencias'
        detail = 'La captura no reporta bloqueos visibles.'
        flags: list[str] = []
        if active_incidents:
            lead = active_incidents[0]
            mapping = {
                'navigation_stall': 'Navegacion atascada',
                'capture_starvation': 'Revisar captura',
                'bridge_lag': 'Bridge atrasado',
                'tab_attach_gap': 'Pestana pendiente',
                'finalize_slow': 'Finalizacion lenta',
                'replay_incomplete': 'Replay parcial',
                'session_restore_weak': 'Sesion fragil',
            }
            label = mapping.get(lead.incident_kind, 'Incidencia detectada')
            detail = lead.summary
            flags = [item.incident_kind for item in active_incidents]
        return SessionHealthSnapshot(
            episode_id=episode_id,
            site_id=site_id,
            health_label=label,
            health_flags=flags,
            status=str(snapshot.get('status', 'idle') or 'idle'),
            visible_step_count=int(snapshot.get('visible_step_count', 0) or 0),
            screenshot_count=int(snapshot.get('screenshot_count', 0) or 0),
            api_seen_count=int(snapshot.get('api_seen_count', 0) or 0),
            api_saved_count=int(snapshot.get('api_saved_count', 0) or 0),
            api_dropped_count=int(snapshot.get('api_dropped_count', 0) or 0),
            page_count=int(snapshot.get('page_count', 0) or 0),
            observed_page_count=int(snapshot.get('observed_page_count', 0) or 0),
            queue_depth=int(snapshot.get('queue_depth', 0) or 0),
            frames_detected=int(snapshot.get('frames_detected', 0) or 0),
            heartbeat_count=int(snapshot.get('heartbeat_count', 0) or 0),
            last_active_url=str(snapshot.get('last_active_url', '') or ''),
            recent_urls=list(snapshot.get('recent_urls', []))[:3],
            detail=detail,
            metrics={
                'seconds_since_last_visible_progress': float(snapshot.get('seconds_since_last_visible_progress', 0.0) or 0.0),
                'active_navigation_stall_seconds': float(snapshot.get('active_navigation_stall_seconds', 0.0) or 0.0),
                'poll_without_progress_count': int(snapshot.get('poll_without_progress_count', 0) or 0),
            },
        )
