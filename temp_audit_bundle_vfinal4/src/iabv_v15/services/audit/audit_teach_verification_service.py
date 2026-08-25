from __future__ import annotations

from statistics import mean
from typing import Any

from iabv_v15.domain.models import (
    AnnotationConfidence,
    AuditIssue,
    AuditReport,
    AuditedReplayResult,
    BackgroundAuditResult,
    CrossCheckResult,
    InteractionEpisode,
    OverlayKind,
    ReplayAnnotation,
    ReplayAnnotationStatus,
    VisualAnnotation,
)
from iabv_v15.services.capture.replay_confidence_service import ReplayConfidenceService
from iabv_v15.services.capture.sensitive_field_detector import SensitiveFieldDetector


class AuditTeachVerificationService:
    COLOR_GREEN = '#22c55e'
    COLOR_BLUE = '#3b82f6'
    COLOR_YELLOW = '#f59e0b'
    COLOR_RED = '#ef4444'

    def __init__(
        self,
        *,
        replay_confidence_service: ReplayConfidenceService | None = None,
        sensitive_field_detector: SensitiveFieldDetector | None = None,
    ) -> None:
        self.replay_confidence_service = replay_confidence_service or ReplayConfidenceService()
        self.sensitive_field_detector = sensitive_field_detector or SensitiveFieldDetector()

    def verify_replay(
        self,
        *,
        episode_id: str,
        replay_steps: list[dict[str, Any]],
        annotations: list[ReplayAnnotation] | None = None,
        learning_packet: dict[str, Any] | None = None,
        interaction_episode: InteractionEpisode | None = None,
        objective: str = '',
    ) -> AuditedReplayResult:
        annotation_by_step = {
            item.step_id: item
            for item in (annotations or [])
            if item.step_id
        }
        background_results: list[BackgroundAuditResult] = []
        visual_annotations: list[VisualAnnotation] = []
        issues: list[AuditIssue] = []
        confidence_samples: list[float] = []
        steps_matching = 0
        steps_diverging = 0
        steps_uncertain = 0
        agreement_checks = 0
        agreement_hits = 0

        for step in replay_steps:
            annotation = annotation_by_step.get(str(step.get('step_id') or ''))
            background, visual, step_issues = self._audit_step(step=step, annotation=annotation)
            background_results.append(background)
            visual_annotations.append(visual)
            issues.extend(step_issues)
            confidence_samples.append(background.confidence)
            status = str(visual.metadata.get('annotation_status') or ReplayAnnotationStatus.UNCERTAIN.value)
            if status in {ReplayAnnotationStatus.KNOWN.value, ReplayAnnotationStatus.USER_CORRECTED.value}:
                steps_matching += 1
            elif status == ReplayAnnotationStatus.MISSING.value:
                steps_diverging += 1
            else:
                steps_uncertain += 1
            if background.field_type_detected != 'UNKNOWN' or self._is_inputish(step):
                agreement_checks += 1
                if status != ReplayAnnotationStatus.MISSING.value:
                    agreement_hits += 1

        total_steps = len(replay_steps)
        overall_confidence = round(mean(confidence_samples), 3) if confidence_samples else 0.0
        has_critical = any(item.severity == 'critical' for item in issues)
        audit_passed = total_steps > 0 and overall_confidence >= 0.8 and not has_critical and steps_diverging == 0
        cross_status = AnnotationConfidence.CONFIRMED if audit_passed else AnnotationConfidence.DOUBTFUL if overall_confidence >= 0.45 else AnnotationConfidence.INSUFFICIENT
        suggested_improvements = self._suggest_improvements(
            issues=issues,
            replay_steps=replay_steps,
            learning_packet=learning_packet or {},
            interaction_episode=interaction_episode,
        )
        agreement_ratio = round((agreement_hits / max(1, agreement_checks)), 3) if agreement_checks else 1.0
        algorithm_agreement_matrix = {
            'replay_confidence_service': {'sensitive_field_detector': agreement_ratio},
            'sensitive_field_detector': {'replay_confidence_service': agreement_ratio},
        }
        report = AuditReport(
            episode_id=episode_id,
            total_steps=total_steps,
            steps_matching=steps_matching,
            steps_diverging=steps_diverging,
            steps_uncertain=steps_uncertain,
            overall_confidence=overall_confidence,
            audit_passed=audit_passed,
            issues=issues,
            background_results=background_results,
            algorithm_agreement_matrix=algorithm_agreement_matrix,
            suggested_improvements=suggested_improvements,
            metadata={
                'objective': objective or (interaction_episode.objective if interaction_episode is not None else ''),
                'site_id': (learning_packet or {}).get('site_id') or (interaction_episode.site_id if interaction_episode is not None else ''),
                'interaction_episode_id': interaction_episode.interaction_episode_id if interaction_episode is not None else '',
            },
        )
        cross_check = CrossCheckResult(
            status=cross_status,
            matched=steps_diverging == 0,
            discrepancy='' if steps_diverging == 0 else 'visual_background_divergence',
            rationale=self._cross_rationale(report),
            confidence=overall_confidence,
            metadata={
                'steps_matching': steps_matching,
                'steps_diverging': steps_diverging,
                'steps_uncertain': steps_uncertain,
                'audit_passed': audit_passed,
            },
        )
        return AuditedReplayResult(
            episode_id=episode_id,
            audit_report=report,
            cross_check_result=cross_check,
            audit_annotations=visual_annotations,
            metadata={
                'mirror_mode': 'two_plane',
                'objective': report.metadata.get('objective') or '',
            },
        )

    def _audit_step(self, *, step: dict[str, Any], annotation: ReplayAnnotation | None) -> tuple[BackgroundAuditResult, VisualAnnotation, list[AuditIssue]]:
        metadata = dict(step.get('metadata_snapshot') or {})
        classification = self.replay_confidence_service.classify_event(step, annotation=annotation)
        detector_match = self.sensitive_field_detector.classify(
            selector=str(step.get('selector') or step.get('target') or ''),
            field_name=str(metadata.get('field_name') or metadata.get('name') or ''),
            input_type=str(metadata.get('input_type') or metadata.get('field_role') or metadata.get('element_role') or ''),
            autocomplete=str(metadata.get('autocomplete') or ''),
            label=' '.join(
                item for item in [
                    str(step.get('button_text') or ''),
                    str(step.get('aria_label') or ''),
                    str(step.get('placeholder') or ''),
                    str(step.get('detail') or ''),
                ]
                if item
            ),
            value=str(step.get('text') or metadata.get('masked_value') or ''),
        )
        field_type = self._field_type_detected(step=step, match=detector_match)
        status = str(classification.get('annotation_status') or ReplayAnnotationStatus.UNCERTAIN.value)
        confidence = float(classification.get('confidence_score') or 0.0)
        passed = status in {ReplayAnnotationStatus.KNOWN.value, ReplayAnnotationStatus.USER_CORRECTED.value}
        discrepancies: list[str] = []
        if status == ReplayAnnotationStatus.MISSING.value:
            discrepancies.append('visual_evidence_missing')
        if field_type == 'PASSWORD_FIELD' and not passed:
            discrepancies.append('password_field_not_confirmed')
        if self._is_inputish(step) and not bool(step.get('has_screenshot')):
            discrepancies.append('input_without_visible_capture')
        if detector_match.sensitive and status == ReplayAnnotationStatus.MISSING.value:
            discrepancies.append('sensitive_field_without_overlay')
        background = BackgroundAuditResult(
            step_id=str(step.get('step_id') or ''),
            field_type_detected=field_type,
            confidence=round(confidence, 3),
            intent_label=self._intent_label(step=step, field_type=field_type),
            algorithms_used=self._algorithms_used(step=step, detector_match=detector_match),
            passed=passed,
            discrepancies=discrepancies,
            metadata={
                'action_type': str(step.get('action_type') or ''),
                'selector': str(step.get('selector') or ''),
                'critical_object': bool(classification.get('critical_object')),
            },
        )
        visual = self._visual_annotation(step=step, classification=classification, background=background)
        issues = self._issues_for_step(step=step, background=background, classification=classification)
        return background, visual, issues

    def _field_type_detected(self, *, step: dict[str, Any], match) -> str:
        role = str(match.field_role or '').lower()
        if role == 'password':
            return 'PASSWORD_FIELD'
        if role == 'email':
            return 'EMAIL_FIELD'
        if role == 'username':
            return 'TEXT_FIELD'
        action_type = str(step.get('action_type') or '').lower()
        element_role = str(step.get('element_role') or '').lower()
        if action_type in {'input', 'change', 'focus'} or 'input' in element_role or 'text' in element_role:
            return 'TEXT_FIELD'
        return 'UNKNOWN'

    def _intent_label(self, *, step: dict[str, Any], field_type: str) -> str:
        action_type = str(step.get('action_type') or '').lower()
        if field_type == 'PASSWORD_FIELD':
            return 'enter_password'
        if field_type == 'EMAIL_FIELD':
            return 'enter_account'
        if action_type in {'click', 'submit'}:
            return 'confirm_action'
        if action_type == 'scroll':
            return 'navigate_context'
        if action_type == 'keydown':
            return 'keyboard_navigation'
        return action_type or 'observe'

    def _algorithms_used(self, *, step: dict[str, Any], detector_match) -> list[str]:
        algorithms = ['replay_confidence_service']
        if detector_match.sensitive or self._is_inputish(step):
            algorithms.append('sensitive_field_detector')
        return algorithms

    def _visual_annotation(self, *, step: dict[str, Any], classification: dict[str, Any], background: BackgroundAuditResult) -> VisualAnnotation:
        status = str(classification.get('annotation_status') or ReplayAnnotationStatus.UNCERTAIN.value)
        is_password = background.field_type_detected == 'PASSWORD_FIELD'
        if is_password and status in {ReplayAnnotationStatus.KNOWN.value, ReplayAnnotationStatus.USER_CORRECTED.value}:
            color = self.COLOR_BLUE
            icon = 'lock'
        elif status in {ReplayAnnotationStatus.KNOWN.value, ReplayAnnotationStatus.USER_CORRECTED.value}:
            color = self.COLOR_GREEN
            icon = 'ok'
        elif status == ReplayAnnotationStatus.MISSING.value:
            color = self.COLOR_RED
            icon = 'x'
        else:
            color = self.COLOR_YELLOW
            icon = 'warn'
        bounding_box = self._normalized_rect(classification.get('overlay_rect') or {})
        anchor_point = self._normalized_point(classification.get('overlay_point') or {})
        overlay_kind = OverlayKind(str(classification.get('overlay_kind') or OverlayKind.RECT.value))
        return VisualAnnotation(
            step_id=str(step.get('step_id') or ''),
            annotation_type=self._annotation_type(step=step, status=status, field_type=background.field_type_detected),
            color=color,
            icon=icon,
            label=self._annotation_label(step=step, background=background, status=status),
            tooltip=self._annotation_tooltip(step=step, background=background, classification=classification),
            confidence_bar=float(classification.get('confidence_score') or 0.0),
            target_selector=str(step.get('selector') or step.get('target') or '') or None,
            bounding_box=bounding_box if bounding_box.get('valid') else None,
            anchor_point=anchor_point if anchor_point.get('valid') else None,
            overlay_kind=overlay_kind,
            metadata={
                'annotation_status': status,
                'status_family': self._status_family(status),
                'critical_object': bool(classification.get('critical_object')),
                'field_type_detected': background.field_type_detected,
                'screenshot_path': str(step.get('screenshot_path') or ''),
                'group_key': str(step.get('group_key') or step.get('screenshot_path') or ''),
                'action_type': str(step.get('action_type') or ''),
                'confidence_score': float(classification.get('confidence_score') or 0.0),
                'display_color': color,
            },
        )

    def _issues_for_step(self, *, step: dict[str, Any], background: BackgroundAuditResult, classification: dict[str, Any]) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        status = str(classification.get('annotation_status') or ReplayAnnotationStatus.UNCERTAIN.value)
        critical = bool(classification.get('critical_object'))
        step_id = str(step.get('step_id') or '')
        if status == ReplayAnnotationStatus.MISSING.value:
            issues.append(
                AuditIssue(
                    step_id=step_id,
                    severity='critical' if critical or background.field_type_detected == 'PASSWORD_FIELD' else 'warning',
                    description='El replay no pudo confirmar visualmente este paso.',
                    algorithm_source='replay_confidence_service',
                    suggested_action='Captura otra vez el objeto o etiqueta manualmente el overlay si el paso era critico.',
                    metadata={'field_type_detected': background.field_type_detected},
                )
            )
        elif status == ReplayAnnotationStatus.UNCERTAIN.value:
            issues.append(
                AuditIssue(
                    step_id=step_id,
                    severity='warning',
                    description='La auditoria visual ve este paso, pero todavia con confianza media.',
                    algorithm_source='replay_confidence_service',
                    suggested_action='Mantener la anotacion o reforzarla con una nueva captura visible.',
                )
            )
        if 'input_without_visible_capture' in background.discrepancies:
            issues.append(
                AuditIssue(
                    step_id=step_id,
                    severity='warning',
                    description='Hubo escritura o foco sin captura visible suficiente para comprobar el elemento.',
                    algorithm_source='two_plane_cross_check',
                    suggested_action='Aumentar captura visible o confirmar el paso con una anotacion manual.',
                )
            )
        return issues

    def _annotation_type(self, *, step: dict[str, Any], status: str, field_type: str) -> str:
        if field_type != 'UNKNOWN' or self._is_inputish(step):
            return 'field_highlight'
        if status == ReplayAnnotationStatus.MISSING.value:
            return 'warning'
        return 'action_check'

    def _annotation_label(self, *, step: dict[str, Any], background: BackgroundAuditResult, status: str) -> str:
        if background.field_type_detected == 'PASSWORD_FIELD':
            return 'Campo de contrasena confirmado' if status in {ReplayAnnotationStatus.KNOWN.value, ReplayAnnotationStatus.USER_CORRECTED.value} else 'Campo de contrasena aun dudoso'
        if background.field_type_detected == 'EMAIL_FIELD':
            return 'Campo de cuenta detectado'
        if status == ReplayAnnotationStatus.MISSING.value:
            return 'Falta evidencia visual'
        label = str(step.get('text') or step.get('button_text') or step.get('aria_label') or step.get('selector') or step.get('target') or '').strip()
        return label[:96] if label else background.intent_label.replace('_', ' ')

    def _annotation_tooltip(self, *, step: dict[str, Any], background: BackgroundAuditResult, classification: dict[str, Any]) -> str:
        algorithms = ', '.join(background.algorithms_used)
        selector = str(step.get('selector') or step.get('target') or '')
        return (
            f'Intento: {background.intent_label}. '
            f'Campo: {background.field_type_detected}. '
            f'Confianza: {background.confidence:.2f}. '
            f'Algoritmos: {algorithms}. '
            f'Selector: {selector or "n/d"}.'
        )

    def _suggest_improvements(
        self,
        *,
        issues: list[AuditIssue],
        replay_steps: list[dict[str, Any]],
        learning_packet: dict[str, Any],
        interaction_episode: InteractionEpisode | None,
    ) -> list[str]:
        suggestions: list[str] = []
        if any(item.severity == 'critical' for item in issues):
            suggestions.append('Refuerza primero los overlays rojos o criticos antes de reutilizar esta ensenanza.')
        if any(item.algorithm_source == 'two_plane_cross_check' for item in issues):
            suggestions.append('Aumenta la captura visible o los checkpoints para que fondo y pantalla cuenten la misma historia.')
        if any(str(step.get('action_type') or '').lower() in {'input', 'change', 'focus'} and not step.get('has_screenshot') for step in replay_steps):
            suggestions.append('Necesitas mas evidencia visual alrededor de los campos de entrada para validar el aprendizaje.')
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        if float(visual_summary.get('visual_alignment_score', 0.0) or 0.0) < 0.5:
            suggestions.append('La alineacion visual sigue debil; conviene revisar selector, geometria y orden de pasos.')
        if interaction_episode is not None and interaction_episode.reused_pattern:
            suggestions.append('Ya existe un patron equivalente; reutilizalo antes de volver a ensenar desde cero.')
        if not suggestions:
            suggestions.append('La ensenanza quedo suficientemente coherente para seguir reutilizando la ruta actual.')
        unique: list[str] = []
        for item in suggestions:
            if item not in unique:
                unique.append(item)
        return unique[:5]

    def _cross_rationale(self, report: AuditReport) -> str:
        if report.audit_passed:
            return 'Los algoritmos del fondo y el replay visible quedaron alineados para esta sesion.'
        if report.steps_diverging > 0:
            return 'Existen pasos donde el fondo dice una cosa, pero la pantalla no lo confirma todavia.'
        return 'La auditoria encontro senales utiles, aunque la confianza global todavia no basta para dar el flujo por aprendido.'

    def _normalized_rect(self, rect: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(rect, dict) or not rect.get('valid'):
            return {'valid': False, 'x': 0.0, 'y': 0.0, 'width': 0.0, 'height': 0.0}
        return {
            'valid': True,
            'x': float(rect.get('x', 0.0) or 0.0),
            'y': float(rect.get('y', 0.0) or 0.0),
            'width': float(rect.get('width', 0.0) or 0.0),
            'height': float(rect.get('height', 0.0) or 0.0),
        }

    def _normalized_point(self, point: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(point, dict) or not point.get('valid'):
            return {'valid': False, 'x': 0.0, 'y': 0.0}
        normalized = {
            'valid': True,
            'x': float(point.get('x', 0.0) or 0.0),
            'y': float(point.get('y', 0.0) or 0.0),
        }
        if 'estimated' in point:
            normalized['estimated'] = bool(point.get('estimated'))
        return normalized

    def _status_family(self, status: str) -> str:
        if status in {ReplayAnnotationStatus.KNOWN.value, ReplayAnnotationStatus.USER_CORRECTED.value}:
            return 'green'
        if status == ReplayAnnotationStatus.MISSING.value:
            return 'red'
        return 'orange'

    def _is_inputish(self, step: dict[str, Any]) -> bool:
        action_type = str(step.get('action_type') or '').lower()
        element_role = str(step.get('element_role') or '').lower()
        return action_type in {'input', 'change', 'focus'} or 'input' in element_role or element_role in {'password', 'email', 'username', 'text_input', 'text_area'}
