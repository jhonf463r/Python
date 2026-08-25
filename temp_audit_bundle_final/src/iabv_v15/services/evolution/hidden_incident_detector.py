from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import HiddenIncident, IncidentStatus, IssueSeverity, RuntimeSignal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HiddenIncidentDetector:
    def __init__(self) -> None:
        self._thresholds = {
            'navigation_stall_seconds': 8.0,
            'capture_starvation_seconds': 6.0,
            'queue_depth_threshold': 80,
            'poll_without_progress_threshold': 4,
            'tab_attach_gap_seconds': 2.0,
            'finalize_slow_ms': 10000.0,
        }

    def configure(self, overrides: dict[str, float | int]) -> None:
        for key, value in dict(overrides or {}).items():
            if key in self._thresholds:
                self._thresholds[key] = value

    def describe_thresholds(self) -> dict[str, float | int]:
        return dict(self._thresholds)

    def detect_from_snapshot(
        self,
        *,
        episode_id: str | None,
        site_id: str,
        runtime_snapshot: dict[str, Any],
        signals: list[RuntimeSignal],
        existing_incidents: list[HiddenIncident],
    ) -> list[HiddenIncident]:
        snapshot = runtime_snapshot or {}
        incidents: list[HiddenIncident] = []
        active_url = str(snapshot.get('last_active_url', '') or '')
        recent_urls = list(snapshot.get('recent_urls', []))[:3]
        signal_ids = [signal.signal_id for signal in signals]
        evidence_ids = list(snapshot.get('recent_evidence_ids', []))[:8]

        def add(kind: str, summary: str, severity: IssueSeverity, probable_cause: str, detail: str, metadata: dict[str, Any]) -> None:
            if self._incident_exists(kind, active_url, existing_incidents):
                return
            incidents.append(
                HiddenIncident(
                    episode_id=episode_id,
                    site_id=site_id,
                    incident_kind=kind,
                    severity=severity,
                    status=IncidentStatus.OPEN,
                    summary=summary,
                    probable_cause=probable_cause,
                    detail=detail,
                    affected_url=active_url,
                    recent_urls=recent_urls,
                    evidence_ids=evidence_ids,
                    signal_ids=signal_ids,
                    metadata=metadata,
                )
            )

        if float(snapshot.get('active_navigation_stall_seconds', 0.0) or 0.0) >= float(self._thresholds['navigation_stall_seconds']):
            add(
                'navigation_stall',
                'Se detecto una navegacion atascada en la pestana activa.',
                IssueSeverity.HIGH,
                'La pestana nueva no mostro progreso util durante varios segundos.',
                f"URL activa: {active_url or 'sin url'} | demora: {snapshot.get('active_navigation_stall_seconds', 0.0):.1f}s",
                {'active_navigation_stall_seconds': snapshot.get('active_navigation_stall_seconds', 0.0)},
            )
        if (int(snapshot.get('heartbeat_count', 0) or 0) > 0 and int(snapshot.get('visible_step_count', 0) or 0) == 0 and int(snapshot.get('screenshot_count', 0) or 0) == 0 and float(snapshot.get('seconds_since_session_start', 0.0) or 0.0) >= float(self._thresholds['capture_starvation_seconds'])):
            add(
                'capture_starvation',
                'La sesion esta viva pero no esta dejando evidencia visible suficiente.',
                IssueSeverity.HIGH,
                'Hay heartbeat, pero no aparecen pasos visibles ni capturas.',
                f"Heartbeat: {snapshot.get('heartbeat_count', 0)} | cola: {snapshot.get('queue_depth', 0)}",
                {'heartbeat_count': snapshot.get('heartbeat_count', 0), 'queue_depth': snapshot.get('queue_depth', 0)},
            )
        if int(snapshot.get('queue_depth', 0) or 0) >= int(self._thresholds['queue_depth_threshold']) or int(snapshot.get('poll_without_progress_count', 0) or 0) >= int(self._thresholds['poll_without_progress_threshold']):
            add(
                'bridge_lag',
                'La captura visible acumula retraso en el bridge.',
                IssueSeverity.MEDIUM,
                'La cola de eventos crecio o hubo varios ciclos sin progreso visible.',
                f"Cola: {snapshot.get('queue_depth', 0)} | ciclos sin progreso: {snapshot.get('poll_without_progress_count', 0)}",
                {'queue_depth': snapshot.get('queue_depth', 0), 'poll_without_progress_count': snapshot.get('poll_without_progress_count', 0)},
            )
        if float(snapshot.get('max_unobserved_tab_age', 0.0) or 0.0) >= float(self._thresholds['tab_attach_gap_seconds']):
            add(
                'tab_attach_gap',
                'Se detecto una pestana nueva sin observacion completa.',
                IssueSeverity.MEDIUM,
                'La pestana nueva existe, pero aun no tiene bridge o seguimiento completo.',
                f"Pesta?as: {snapshot.get('page_count', 0)} | observadas: {snapshot.get('observed_page_count', 0)}",
                {'max_unobserved_tab_age': snapshot.get('max_unobserved_tab_age', 0.0)},
            )
        if float(snapshot.get('finalize_duration_ms', 0.0) or 0.0) > float(self._thresholds['finalize_slow_ms']):
            add(
                'finalize_slow',
                'Detener y recopilar tardo mas de lo esperado.',
                IssueSeverity.MEDIUM,
                'La finalizacion consumio demasiado tiempo y puede sentirse como congelamiento.',
                f"Duracion de cierre: {snapshot.get('finalize_duration_ms', 0.0):.0f} ms",
                {'finalize_duration_ms': snapshot.get('finalize_duration_ms', 0.0)},
            )
        if snapshot.get('replay_quality') == 'insufficient':
            add(
                'replay_incomplete',
                'El replay quedo insuficiente para validar la ense?anza.',
                IssueSeverity.HIGH,
                'Hay brief o artefactos, pero no suficiente evidencia visible reutilizable.',
                f"Visible: {snapshot.get('visible_step_count', 0)} | capturas: {snapshot.get('screenshot_count', 0)}",
                {'replay_quality': snapshot.get('replay_quality', 'insufficient')},
            )
        if bool(snapshot.get('storage_state_available')) and bool(snapshot.get('manual_login_required_repeated')):
            add(
                'session_restore_weak',
                'La restauracion de sesion por sitio sigue pidiendo login.',
                IssueSeverity.MEDIUM,
                'El storage state existe, pero la pagina insiste en autenticacion manual.',
                'Conviene revisar cookies, politica del sitio o el momento de guardado del estado.',
                {'storage_state_available': True},
            )
        return incidents

    def _incident_exists(self, incident_kind: str, affected_url: str, existing_incidents: list[HiddenIncident]) -> bool:
        for incident in existing_incidents:
            if incident.incident_kind != incident_kind:
                continue
            if incident.status in {IncidentStatus.RECOVERED, IncidentStatus.RESOLVED_BY_RELEASE}:
                continue
            if affected_url and incident.affected_url and incident.affected_url != affected_url:
                continue
            return True
        return False
