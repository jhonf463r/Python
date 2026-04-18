from __future__ import annotations

from copy import deepcopy
from typing import Any


class ReplayLearningFeedbackService:
    def apply_annotations_to_learning(self, learning_packet: dict[str, Any], visual_summary: dict[str, Any]) -> dict[str, Any]:
        packet = deepcopy(learning_packet or {})
        summary = dict(visual_summary or {})
        packet['visual_summary'] = summary
        base_learning = dict(packet.get('learning_readiness') or {})
        base_login = dict(packet.get('login_learning') or {})
        critical = float(summary.get('critical_object_coverage', 0.0) or 0.0)
        visual_alignment = float(summary.get('visual_alignment_score', 0.0) or 0.0)
        login_complete = float(summary.get('login_visual_completeness', 0.0) or 0.0)
        manual = int(summary.get('manual_correction_count', 0) or 0)
        green = int(summary.get('green_count', 0) or 0)
        red = int(summary.get('red_count', 0) or 0)

        login_status = base_login.get('status', 'insufficient')
        if login_complete >= 0.75 and critical >= 0.66 and green >= 3:
            login_status = 'ready'
        elif login_complete >= 0.45 or critical >= 0.45 or manual > 0:
            login_status = 'partial' if login_status == 'insufficient' else login_status
        elif red >= 2:
            login_status = 'insufficient'

        learning_status = base_learning.get('status', 'insufficient')
        if visual_alignment >= 0.72 and critical >= 0.66 and summary.get('useful_frames', 0) >= 1:
            learning_status = 'ready'
        elif visual_alignment >= 0.4 or manual > 0:
            learning_status = 'partial' if learning_status == 'insufficient' else learning_status
        elif red >= 3:
            learning_status = 'insufficient'

        base_learning.update({
            'status': learning_status,
            'summary': self._learning_summary(learning_status, summary),
            'learning_coverage_score': summary.get('learning_coverage_score', 0.0),
            'visual_alignment_score': visual_alignment,
            'manual_correction_count': manual,
            'critical_object_coverage': critical,
        })
        base_login.update({
            'status': login_status,
            'summary': self._login_summary(login_status, summary),
            'signals': list(dict.fromkeys(list(base_login.get('signals') or []) + self._signals_from_summary(summary))),
            'missing_signals': list(dict.fromkeys(list(base_login.get('missing_signals') or []) + list(summary.get('gaps') or [])))[:8],
            'login_visual_completeness': login_complete,
        })
        packet['learning_readiness'] = base_learning
        packet['login_learning'] = base_login
        return packet

    def _signals_from_summary(self, summary: dict[str, Any]) -> list[str]:
        signals: list[str] = []
        if float(summary.get('critical_object_coverage', 0.0) or 0.0) >= 0.66:
            signals.append('objetos criticos visuales confirmados')
        if int(summary.get('manual_correction_count', 0) or 0) > 0:
            signals.append('correcciones humanas persistidas')
        if int(summary.get('green_count', 0) or 0) > 0:
            signals.append('overlays verdes confirmados')
        return signals

    def _learning_summary(self, status: str, summary: dict[str, Any]) -> str:
        if status == 'ready':
            return 'El replay visual ya quedo fuerte: la galeria, los overlays y los objetos criticos respaldan la ensenanza.'
        if status == 'partial':
            return 'La ensenanza ya tiene evidencia visual util, pero aun quedan objetos o pasos que conviene revisar.'
        return 'La ensenanza todavia no tiene suficiente coherencia visual para quedar lista como habilidad fuerte.'

    def _login_summary(self, status: str, summary: dict[str, Any]) -> str:
        if status == 'ready':
            return 'El login tiene cobertura visual suficiente en correo, contrasena y envio, con evidencia reutilizable.'
        if status == 'partial':
            return 'El login ya muestra partes importantes, pero aun quedan dudas visuales o correcciones pendientes.'
        return 'El login sigue incompleto a nivel visual; faltan objetos criticos o evidencia consistente en el replay.'
