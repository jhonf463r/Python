from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import OverlayKind, ReplayAnnotation, ReplayAnnotationSource, ReplayAnnotationStatus


class ReplayConfidenceService:
    COLOR_BY_STATUS = {
        ReplayAnnotationStatus.KNOWN.value: '#56d98e',
        ReplayAnnotationStatus.UNCERTAIN.value: '#f0a65b',
        ReplayAnnotationStatus.MISSING.value: '#ff6b6b',
        ReplayAnnotationStatus.USER_CORRECTED.value: '#56d98e',
    }

    def classify_event(self, step: dict[str, Any], annotation: ReplayAnnotation | None = None) -> dict[str, Any]:
        metadata = dict(step.get('metadata_snapshot') or {})
        action_type = str(step.get('action_type') or '').lower()
        element_role = str(step.get('element_role') or metadata.get('field_role') or metadata.get('element_role') or '').lower()
        has_screenshot = bool(step.get('has_screenshot'))
        has_rect = bool((step.get('overlay_rect') or {}).get('valid'))
        overlay_kind = self._overlay_kind(action_type, element_role, has_rect)
        overlay_point = self._overlay_point(step.get('overlay_rect') or {}, overlay_kind)
        overlay_label = self._overlay_label(step, element_role)
        critical = self._is_critical_object(action_type, element_role, step)

        if annotation is not None:
            status = annotation.status.value
            confidence = float(annotation.confidence_score or 0.9)
            source = annotation.source.value
            overlay_kind = annotation.overlay_kind.value
            overlay_rect = self._normalize_rect(annotation.overlay_rect)
            overlay_point = self._normalize_point(annotation.overlay_point)
            overlay_label = self._clean_label(annotation.overlay_label) or overlay_label
            overlay_notes = annotation.overlay_notes or ''
        else:
            status, confidence = self._baseline_status(action_type, element_role, has_screenshot, has_rect, step)
            source = self._baseline_source(action_type, step)
            overlay_rect = self._normalize_rect(step.get('overlay_rect') or {})
            overlay_notes = ''

        return {
            'annotation_status': status,
            'confidence_score': round(confidence, 3),
            'annotation_source': source,
            'overlay_kind': overlay_kind,
            'overlay_rect': overlay_rect,
            'overlay_point': overlay_point,
            'overlay_label': overlay_label,
            'overlay_notes': overlay_notes,
            'critical_object': critical,
            'display_color': self.COLOR_BY_STATUS.get(status, '#f0a65b'),
        }

    def _baseline_status(self, action_type: str, element_role: str, has_screenshot: bool, has_rect: bool, step: dict[str, Any]) -> tuple[str, float]:
        capture_source = str(step.get('capture_source') or '').lower()
        frame_request_type = str((step.get('metadata_snapshot') or {}).get('frame_request_type') or '').strip()
        login_related = self._is_login_related(action_type, element_role, step)
        if capture_source == 'frame_fallback_structured' and login_related:
            return ReplayAnnotationStatus.KNOWN.value, 0.91 if has_screenshot else 0.84
        if action_type == 'frame_fallback' and frame_request_type == 'LoginAndGetTempToken' and login_related:
            return ReplayAnnotationStatus.KNOWN.value, 0.88 if has_screenshot else 0.72
        if action_type in {'frame_fallback', 'visible_recovery'}:
            return ReplayAnnotationStatus.UNCERTAIN.value, 0.48
        if action_type == 'scroll':
            return (ReplayAnnotationStatus.KNOWN.value, 0.72) if has_screenshot else (ReplayAnnotationStatus.UNCERTAIN.value, 0.45)
        if login_related and has_screenshot and not has_rect:
            return ReplayAnnotationStatus.KNOWN.value, 0.86
        if element_role in {'password_input', 'email_input', 'username_input', 'password', 'email', 'username'} and has_screenshot and has_rect:
            return ReplayAnnotationStatus.KNOWN.value, 0.95
        if action_type in {'click', 'submit', 'focus'} and has_screenshot and has_rect:
            return ReplayAnnotationStatus.KNOWN.value, 0.9
        if action_type == 'keydown' and str(step.get('key_display') or '').lower() in {'enter', 'tab'} and has_screenshot:
            return ReplayAnnotationStatus.KNOWN.value, 0.82
        if has_screenshot and has_rect:
            return ReplayAnnotationStatus.KNOWN.value, 0.78
        if has_screenshot or capture_source in {'frame_fallback_structured', 'artifact_recovery'}:
            return ReplayAnnotationStatus.UNCERTAIN.value, 0.52
        if self._is_critical_object(action_type, element_role, step):
            return ReplayAnnotationStatus.MISSING.value, 0.22
        return ReplayAnnotationStatus.UNCERTAIN.value, 0.34

    def _baseline_source(self, action_type: str, step: dict[str, Any]) -> str:
        capture_source = str(step.get('capture_source') or '').lower()
        if capture_source.startswith('frame_fallback') or action_type == 'frame_fallback':
            return ReplayAnnotationSource.RECOVERED.value
        if capture_source in {'artifact_recovery', 'inferred'}:
            return ReplayAnnotationSource.INFERRED.value
        if capture_source:
            return ReplayAnnotationSource.CAPTURED.value
        return ReplayAnnotationSource.INFERRED.value

    def _overlay_kind(self, action_type: str, element_role: str, has_rect: bool) -> str:
        if action_type == 'scroll':
            return OverlayKind.SCROLL_BAND.value
        if action_type == 'click':
            return OverlayKind.CLICK_POINT.value if has_rect else OverlayKind.RECT.value
        if action_type in {'input', 'change'} and element_role in {'password_input', 'email_input', 'username_input', 'password', 'email', 'username', 'text_input'}:
            return OverlayKind.TEXT_SPAN.value if has_rect else OverlayKind.RECT.value
        return OverlayKind.RECT.value

    def _overlay_point(self, overlay_rect: dict[str, Any], overlay_kind: str) -> dict[str, float]:
        normalized = self._normalize_rect(overlay_rect)
        if overlay_kind != OverlayKind.CLICK_POINT.value or not normalized.get('valid'):
            return {'valid': False, 'x': 0.0, 'y': 0.0}
        return {
            'valid': True,
            'x': min(1.0, max(0.0, normalized['x'] + (normalized['width'] / 2.0))),
            'y': min(1.0, max(0.0, normalized['y'] + (normalized['height'] / 2.0))),
        }

    def _overlay_label(self, step: dict[str, Any], element_role: str) -> str:
        action_type = str(step.get('action_type') or '').lower()
        for key in ('button_text', 'aria_label', 'placeholder', 'text', 'target', 'selector'):
            value = self._clean_label(step.get(key) or '')
            if value:
                return value[:80]
        if element_role in {'password_input', 'password'}:
            return 'campo contrasena'
        if element_role in {'email_input', 'email'}:
            return 'campo correo'
        if element_role in {'username_input', 'username'}:
            return 'campo usuario'
        if action_type in {'input', 'change'} and element_role in {'text_input', 'text_area'}:
            return 'campo de texto'
        if action_type == 'keydown':
            key_display = str(step.get('key_display') or '').strip()
            return f'tecla {key_display}'.strip() if key_display else 'tecla'
        if action_type == 'submit':
            return 'submit'
        if action_type == 'click':
            return 'clic'
        if action_type == 'scroll':
            return 'scroll'
        if action_type == 'visual_checkpoint':
            return 'checkpoint visual'
        if action_type == 'teaching_brief':
            return 'brief de ensenanza'
        return element_role or action_type or 'objeto'

    def _clean_label(self, value: Any) -> str:
        text = str(value or '').strip()
        if text.lower() in {'sin texto', 'sin selector', 'n/d', 'none'}:
            return ''
        return text

    def _is_critical_object(self, action_type: str, element_role: str, step: dict[str, Any]) -> bool:
        label = ' '.join(str(step.get(key) or '') for key in ('button_text', 'aria_label', 'detail', 'target', 'selector')).lower()
        if element_role in {'password_input', 'email_input', 'username_input', 'password', 'email', 'username'}:
            return True
        if action_type in {'click', 'submit', 'keydown'} and any(token in label for token in {'login', 'iniciar sesion', 'ingresar', 'continuar', 'casino', 'buscar'}):
            return True
        return False


    def _is_login_related(self, action_type: str, element_role: str, step: dict[str, Any]) -> bool:
        if element_role in {'password_input', 'email_input', 'username_input', 'password', 'email', 'username'}:
            return True
        metadata = dict(step.get('metadata_snapshot') or {})
        label = ' '.join(
            str(value or '')
            for value in (
                step.get('button_text'),
                step.get('aria_label'),
                step.get('placeholder'),
                step.get('detail'),
                step.get('target'),
                step.get('selector'),
                metadata.get('frame_request_type'),
                metadata.get('frame_url'),
                metadata.get('textPreview'),
            )
        ).lower()
        if action_type in {'click', 'submit', 'keydown', 'input', 'change', 'focus', 'frame_fallback'} and any(
            token in label for token in {'login', 'iniciar sesion', 'ingresar', 'continuar', 'username', 'password', 'correo'}
        ):
            return True
        return False

    def _normalize_rect(self, rect: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(rect, dict) or not rect.get('valid'):
            return {'valid': False, 'x': 0.0, 'y': 0.0, 'width': 0.0, 'height': 0.0}
        return {
            'valid': True,
            'x': float(rect.get('x', 0.0) or 0.0),
            'y': float(rect.get('y', 0.0) or 0.0),
            'width': float(rect.get('width', 0.0) or 0.0),
            'height': float(rect.get('height', 0.0) or 0.0),
        }

    def _normalize_point(self, point: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(point, dict) or not point.get('valid'):
            return {'valid': False, 'x': 0.0, 'y': 0.0}
        return {
            'valid': True,
            'x': float(point.get('x', 0.0) or 0.0),
            'y': float(point.get('y', 0.0) or 0.0),
        }
