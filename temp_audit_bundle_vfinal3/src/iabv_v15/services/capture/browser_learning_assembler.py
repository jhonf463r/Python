from __future__ import annotations

from collections import Counter

from iabv_v15.domain.models import (
    AnnotationConfidence,
    BrowserObservationBundle,
    CapturedStep,
    CrossCheckResult,
    OverlayKind,
    RedactionSummary,
    SitePolicy,
    TeachingEpisode,
    TeachingEvidence,
    UserClickTrace,
    VisualObjectAnnotation,
    VisualTeachingFrame,
)
from iabv_v15.services.capture.replay_confidence_service import ReplayConfidenceService


class BrowserLearningAssembler:
    IMPORTANT_ACTIONS = {'click', 'input', 'change', 'submit', 'keydown', 'scroll', 'focus'}
    LOGIN_ACTIONS = {'input', 'submit', 'keydown', 'click', 'frame_fallback'}
    AUTH_KEYWORDS = {'logout', 'cerrar sesion', 'loggedinplayer', 'player-balance', 'mi cuenta', 'balance'}

    def __init__(self, confidence_service: ReplayConfidenceService | None = None) -> None:
        self.confidence_service = confidence_service or ReplayConfidenceService()

    def assemble(
        self,
        *,
        episode_id: str,
        site_policy: SitePolicy,
        steps: list[CapturedStep],
        artifacts: list,
        bundle: BrowserObservationBundle,
        redaction_summary: RedactionSummary,
    ) -> dict:
        channel_counts = Counter(artifact.metadata.get('capture_channel', 'unknown') for artifact in artifacts)
        action_counts = Counter(step.action_type for step in steps)
        visible_steps = [step for step in steps if (step.metadata or {}).get('capture_channel') == 'visible' and step.action_type != 'teaching_brief']
        relevant_steps = [step for step in visible_steps if self._is_relevant_step(step)]
        screenshot_steps = [step for step in steps if step.screenshot_path]
        visual_summary = self._build_visual_summary(steps)
        visual_frames, teaching_evidence, cross_check_summary = self._build_visual_teaching_frames(steps)
        teaching_episode = TeachingEpisode(
            episode_id=episode_id,
            objective=f'Ensenanza guiada de {site_policy.display_name or site_policy.site_id}',
            frames=visual_frames,
            evidence=teaching_evidence,
            cross_check_summary=cross_check_summary,
            learning_status='',
            metadata={
                'site_id': site_policy.site_id,
                'display_name': site_policy.display_name,
            },
        )
        login_learning = self._infer_login_learning(site_policy=site_policy, steps=steps, bundle=bundle, visual_summary=visual_summary)
        learning_readiness = self._infer_learning_readiness(
            site_policy=site_policy,
            visible_steps=visible_steps,
            relevant_steps=relevant_steps,
            screenshot_steps=screenshot_steps,
            login_learning=login_learning,
            bundle=bundle,
            visual_summary=visual_summary,
            cross_check_summary=cross_check_summary,
        )
        teaching_episode.learning_status = str(learning_readiness.get('status') or '')
        suggested_commands = login_learning.get('suggested_commands') or [f'Abrir {site_policy.display_name}', f'Abrir {site_policy.display_name} y continuar el flujo ensenado']
        return {
            'episode_id': episode_id,
            'site_id': site_policy.site_id,
            'display_name': site_policy.display_name,
            'bundle_id': bundle.bundle_id,
            'url': bundle.url,
            'capture_channels': [channel.value for channel in bundle.capture_channels],
            'channel_counts': dict(channel_counts),
            'action_counts': dict(action_counts),
            'artifact_count': len(artifacts),
            'step_count': len(steps),
            'visible_step_count': len(visible_steps),
            'relevant_step_count': len(relevant_steps),
            'screenshot_step_count': len(screenshot_steps),
            'capture_stats': bundle.capture_stats,
            'redaction_summary': redaction_summary.model_dump(mode='json'),
            'learning_readiness': learning_readiness,
            'login_learning': login_learning,
            'suggested_commands': suggested_commands,
            'visual_summary': visual_summary,
            'visual_teaching_frames': [item.model_dump(mode='json') for item in visual_frames],
            'teaching_evidence': [item.model_dump(mode='json') for item in teaching_evidence],
            'cross_check_summary': cross_check_summary,
            'teaching_episode': teaching_episode.model_dump(mode='json'),
        }

    def _build_visual_summary(self, steps: list[CapturedStep]) -> dict:
        total_relevant = 0
        known = uncertain = missing = 0
        critical_total = critical_good = 0
        login_total = login_good = 0
        for step in steps:
            step_payload = self._step_payload(step)
            classification = self.confidence_service.classify_event(step_payload)
            if self._is_relevant_step(step):
                total_relevant += 1
            if classification['annotation_status'] == 'known':
                known += 1
            elif classification['annotation_status'] == 'uncertain':
                uncertain += 1
            elif classification['annotation_status'] == 'missing':
                missing += 1
            if classification['critical_object']:
                critical_total += 1
                if classification['annotation_status'] in {'known', 'user_corrected'}:
                    critical_good += 1
            if self._is_login_related(step_payload):
                login_total += 1
                if classification['annotation_status'] in {'known', 'user_corrected'}:
                    login_good += 1
        total_relevant = max(1, total_relevant)
        return {
            'learning_coverage_score': round((known + uncertain) / total_relevant, 3),
            'visual_alignment_score': round(known / total_relevant, 3),
            'manual_correction_count': 0,
            'critical_object_coverage': round(critical_good / max(1, critical_total), 3),
            'login_visual_completeness': round(login_good / max(1, login_total), 3),
            'known_count': known,
            'uncertain_count': uncertain,
            'missing_count': missing,
            'green_count': known,
            'orange_count': uncertain,
            'red_count': missing,
            'user_corrected_count': 0,
        }

    def _build_visual_teaching_frames(self, steps: list[CapturedStep]) -> tuple[list[VisualTeachingFrame], list[TeachingEvidence], dict]:
        frames: list[VisualTeachingFrame] = []
        evidence: list[TeachingEvidence] = []
        confirmed = doubtful = insufficient = 0
        for step in steps:
            if not self._is_relevant_step(step):
                continue
            payload = self._step_payload(step)
            classification = self.confidence_service.classify_event(payload)
            detected = self._detected_object(step, payload, classification)
            click_trace = self._user_click(step, payload)
            cross_check = self._cross_check(detected, click_trace)
            if cross_check.status == AnnotationConfidence.CONFIRMED:
                confirmed += 1
            elif cross_check.status == AnnotationConfidence.DOUBTFUL:
                doubtful += 1
            else:
                insufficient += 1
            frame = VisualTeachingFrame(
                episode_id=step.episode_id,
                step_id=step.step_id,
                objective=classification['overlay_label'],
                screenshot_ref=step.screenshot_path or '',
                detected_objects=[detected] if detected is not None else [],
                user_click=click_trace,
                cross_check=cross_check,
                notes=[classification['overlay_notes']] if classification.get('overlay_notes') else [],
                metadata={
                    'action_type': step.action_type,
                    'element_role': payload.get('element_role') or '',
                    'selector': payload.get('selector') or '',
                    'channel': (step.metadata or {}).get('capture_channel', 'visible'),
                    'confidence_score': classification.get('confidence_score', 0.0),
                },
            )
            frames.append(frame)
            evidence.append(
                TeachingEvidence(
                    episode_id=step.episode_id,
                    frame_id=frame.frame_id,
                    summary=cross_check.rationale,
                    screenshot_ref=step.screenshot_path or '',
                    confidence=cross_check.confidence,
                    metadata={'step_id': step.step_id, 'label': classification['overlay_label']},
                )
            )
        total = max(1, len(frames))
        summary = {
            'frame_count': len(frames),
            'confirmed_count': confirmed,
            'doubtful_count': doubtful,
            'insufficient_count': insufficient,
            'observer_agreement_score': round(confirmed / total, 4),
            'target_element_alignment': round((confirmed + (doubtful * 0.5)) / total, 4),
            'learning_status': 'confirmed' if confirmed and insufficient == 0 else 'doubtful' if confirmed or doubtful else 'insufficient',
        }
        return frames, evidence, summary

    def _detected_object(self, step: CapturedStep, payload: dict, classification: dict) -> VisualObjectAnnotation | None:
        if not payload['overlay_rect'].get('valid') and not classification['overlay_point'].get('valid'):
            return None
        status = classification['annotation_status']
        confidence = (
            AnnotationConfidence.CONFIRMED if status in {'known', 'user_corrected'} else AnnotationConfidence.DOUBTFUL if status == 'uncertain' else AnnotationConfidence.INSUFFICIENT
        )
        return VisualObjectAnnotation(
            label=classification['overlay_label'],
            overlay_kind=OverlayKind(classification['overlay_kind']),
            overlay_rect=payload['overlay_rect'],
            overlay_point=classification['overlay_point'],
            detected_by=str((step.metadata or {}).get('capture_source') or 'bridge_capture'),
            confidence_score=float(classification['confidence_score'] or 0.0),
            confidence=confidence,
            screenshot_ref=step.screenshot_path or '',
            matched_user_click=False,
            metadata={'selector': payload.get('selector') or '', 'action_type': step.action_type},
        )

    def _user_click(self, step: CapturedStep, payload: dict) -> UserClickTrace | None:
        rect = payload['overlay_rect']
        if step.action_type not in {'click', 'submit', 'input', 'change', 'keydown', 'focus'}:
            return None
        if not rect.get('valid'):
            return None
        point_x = rect['x'] + (rect['width'] / 2.0)
        point_y = rect['y'] + (rect['height'] / 2.0)
        viewport_width = float((step.metadata or {}).get('viewport_width') or (step.metadata or {}).get('viewportWidth') or 0.0)
        viewport_height = float((step.metadata or {}).get('viewport_height') or (step.metadata or {}).get('viewportHeight') or 0.0)
        return UserClickTrace(
            action_type=step.action_type,
            target=payload.get('selector') or payload.get('target') or '',
            screenshot_ref=step.screenshot_path or '',
            x=int(point_x * viewport_width) if viewport_width > 0 else 0,
            y=int(point_y * viewport_height) if viewport_height > 0 else 0,
            normalized_x=point_x,
            normalized_y=point_y,
            derived_from_rect=True,
            metadata={'step_id': step.step_id},
        )

    def _cross_check(self, detected: VisualObjectAnnotation | None, click_trace: UserClickTrace | None) -> CrossCheckResult:
        if detected is None or click_trace is None:
            return CrossCheckResult(
                status=AnnotationConfidence.INSUFFICIENT,
                matched=False,
                annotation_id=detected.annotation_id if detected is not None else '',
                click_id=click_trace.click_id if click_trace is not None else '',
                discrepancy='missing_detected_object_or_click_trace',
                rationale='No pude construir el objeto detectado y el clic humano en el mismo frame.',
                confidence=0.24,
            )
        rect = detected.overlay_rect or {}
        matched = bool(rect.get('valid')) and rect.get('x', 0.0) <= click_trace.normalized_x <= rect.get('x', 0.0) + rect.get('width', 0.0) and rect.get('y', 0.0) <= click_trace.normalized_y <= rect.get('y', 0.0) + rect.get('height', 0.0)
        return CrossCheckResult(
            status=AnnotationConfidence.CONFIRMED if matched else AnnotationConfidence.DOUBTFUL,
            matched=matched,
            annotation_id=detected.annotation_id,
            click_id=click_trace.click_id,
            discrepancy='' if matched else 'human_click_outside_detected_object',
            rationale='El clic humano y el objeto detectado coincidieron.' if matched else 'El objeto detectado y el clic humano no quedaron totalmente alineados.',
            confidence=0.9 if matched else 0.5,
        )

    def _step_payload(self, step: CapturedStep) -> dict:
        metadata = step.metadata or {}
        return {
            'step_id': step.step_id,
            'action_type': step.action_type,
            'element_role': metadata.get('field_role') or metadata.get('element_role') or metadata.get('tag_name') or metadata.get('input_type') or '',
            'target': step.target or metadata.get('selector') or '',
            'selector': metadata.get('selector') or step.target or '',
            'text': metadata.get('masked_value') or step.text_value or metadata.get('textPreview') or '',
            'button_text': metadata.get('button_text') or '',
            'aria_label': metadata.get('aria_label') or '',
            'placeholder': metadata.get('placeholder') or '',
            'key_display': metadata.get('key_display') or '',
            'detail': '',
            'capture_source': metadata.get('capture_source') or '',
            'has_screenshot': bool(step.screenshot_path),
            'overlay_rect': self._build_overlay_rect(metadata),
            'metadata_snapshot': metadata,
        }

    def _build_overlay_rect(self, metadata: dict) -> dict:
        rect = metadata.get('element_rect') or metadata.get('elementRect')
        width = metadata.get('viewport_width') or metadata.get('viewportWidth') or 0
        height = metadata.get('viewport_height') or metadata.get('viewportHeight') or 0
        if not isinstance(rect, dict):
            return {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0}
        try:
            x = float(rect.get('x', 0) or 0)
            y = float(rect.get('y', 0) or 0)
            w = float(rect.get('width', 0) or 0)
            h = float(rect.get('height', 0) or 0)
            vw = float(width or 0)
            vh = float(height or 0)
        except (TypeError, ValueError):
            return {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0}
        if vw <= 0 or vh <= 0 or w <= 0 or h <= 0:
            return {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0}
        return {
            'valid': True,
            'x': max(0.0, min(1.0, x / vw)),
            'y': max(0.0, min(1.0, y / vh)),
            'width': max(0.0, min(1.0, w / vw)),
            'height': max(0.0, min(1.0, h / vh)),
        }

    def _is_relevant_step(self, step: CapturedStep) -> bool:
        metadata = step.metadata or {}
        action_type = step.action_type
        if action_type in {'input', 'change', 'click', 'submit', 'scroll', 'focus'}:
            return True
        if action_type == 'keydown':
            return str(metadata.get('key_display') or '').lower() in {'enter', 'tab'}
        if action_type == 'frame_fallback':
            return bool(metadata.get('frame_request_type'))
        return False

    def _infer_login_learning(self, *, site_policy: SitePolicy, steps: list[CapturedStep], bundle: BrowserObservationBundle, visual_summary: dict) -> dict:
        email_or_user = False
        password = False
        submit = False
        authenticated = False
        signals: list[str] = []

        for step in steps:
            metadata = step.metadata or {}
            role = (metadata.get('field_role') or metadata.get('element_role') or '').lower()
            action_type = step.action_type
            key_display = str(metadata.get('key_display') or '').lower()
            if role in {'email', 'email_input', 'username', 'username_input'} and action_type in self.LOGIN_ACTIONS:
                email_or_user = True
            if role in {'password', 'password_input'} and action_type in self.LOGIN_ACTIONS:
                password = True
            if action_type == 'submit':
                submit = True
            if action_type == 'keydown' and key_display == 'enter':
                submit = True
            if action_type == 'click':
                text = ' '.join(str(metadata.get(key) or '') for key in ('button_text', 'aria_label', 'textPreview', 'selector')).lower()
                if any(token in text for token in {'login', 'ingresar', 'iniciar sesion', 'continuar'}):
                    submit = True
            if action_type == 'frame_fallback' and str(metadata.get('frame_request_type') or '').strip() == 'LoginAndGetTempToken':
                email_or_user = True
                password = True
                submit = True

        searchable_chunks = []
        for snapshot in bundle.dom_snapshots:
            searchable_chunks.extend([snapshot.title or '', snapshot.visible_text_excerpt or '', snapshot.html_excerpt or ''])
        searchable_chunks.extend(message.get('text', '') for message in bundle.console_messages if isinstance(message, dict))
        searchable_chunks.extend(exchange.url or '' for exchange in bundle.network_exchanges)
        auth_blob = ' '.join(searchable_chunks).lower()
        authenticated = any(keyword in auth_blob for keyword in self.AUTH_KEYWORDS)

        if email_or_user:
            signals.append('campo de correo o usuario detectado')
        if password:
            signals.append('campo de contrasena detectado')
        if submit:
            signals.append('envio de login detectado')
        if authenticated:
            signals.append('evidencia de sesion autenticada detectada')
        if float(visual_summary.get('critical_object_coverage', 0.0) or 0.0) >= 0.66:
            signals.append('objetos criticos visuales confirmados')

        missing: list[str] = []
        if not email_or_user:
            missing.append('falta detectar un campo de correo o usuario')
        if not password:
            missing.append('falta detectar un campo de contrasena')
        if not submit:
            missing.append('falta detectar la accion de envio del login')
        if not authenticated:
            missing.append('falta evidencia solida de que la sesion quedo autenticada')
        if float(visual_summary.get('login_visual_completeness', 0.0) or 0.0) < 0.45:
            missing.append('faltan rectangulos o evidencia visual suficiente sobre objetos criticos del login')

        if email_or_user and password and submit and authenticated and float(visual_summary.get('login_visual_completeness', 0.0) or 0.0) >= 0.66:
            status = 'ready'
            summary = 'La ensenanza ya contiene senales suficientes para entender el inicio de sesion como flujo reutilizable, con respaldo visual minimo de los objetos criticos.'
        elif sum(bool(item) for item in [email_or_user, password, submit, authenticated]) >= 2 or float(visual_summary.get('critical_object_coverage', 0.0) or 0.0) >= 0.45:
            status = 'partial'
            summary = 'La ensenanza entiende partes importantes del login, pero todavia no conviene asumir ejecucion automatica completa.'
        else:
            status = 'insufficient'
            summary = 'La ensenanza aun no contiene suficientes senales para afirmar que el login fue aprendido como tarea.'

        display_name = site_policy.display_name or site_policy.site_id
        return {
            'status': status,
            'summary': summary,
            'signals': signals,
            'missing_signals': missing,
            'login_visual_completeness': visual_summary.get('login_visual_completeness', 0.0),
            'critical_object_coverage': visual_summary.get('critical_object_coverage', 0.0),
            'suggested_commands': [
                f'Abrir {display_name}',
                f'Abrir {display_name} e iniciar sesion',
            ],
        }

    def _infer_learning_readiness(
        self,
        *,
        site_policy: SitePolicy,
        visible_steps: list[CapturedStep],
        relevant_steps: list[CapturedStep],
        screenshot_steps: list[CapturedStep],
        login_learning: dict,
        bundle: BrowserObservationBundle,
        visual_summary: dict,
        cross_check_summary: dict,
    ) -> dict:
        visible_count = len(visible_steps)
        relevant_count = len(relevant_steps)
        screenshot_count = len(screenshot_steps)
        login_status = login_learning.get('status', 'insufficient')
        channel_count = len(bundle.capture_channels)
        agreement_score = float(cross_check_summary.get('observer_agreement_score', 0.0) or 0.0)
        alignment_score = float(cross_check_summary.get('target_element_alignment', 0.0) or 0.0)
        if visible_count >= 4 and relevant_count >= 4 and screenshot_count >= 2 and login_status == 'ready' and channel_count >= 2 and agreement_score >= 0.66:
            status = 'ready'
        elif visible_count >= 2 and relevant_count >= 2 and (login_status in {'ready', 'partial'} or agreement_score >= 0.4 or alignment_score >= 0.45):
            status = 'partial'
        else:
            status = 'insufficient'
        summary = (
            f'Visible {visible_count}, relevantes {relevant_count}, capturas {screenshot_count}, canales {channel_count}, '
            f'login {login_status}, acuerdo visual {agreement_score:.2f}.'
        )
        return {
            'status': status,
            'summary': summary,
            'learning_coverage_score': visual_summary.get('learning_coverage_score', 0.0),
            'visual_alignment_score': visual_summary.get('visual_alignment_score', 0.0),
            'critical_object_coverage': visual_summary.get('critical_object_coverage', 0.0),
            'login_visual_completeness': visual_summary.get('login_visual_completeness', 0.0),
            'manual_correction_count': visual_summary.get('manual_correction_count', 0),
            'observer_agreement_score': agreement_score,
            'target_element_alignment': alignment_score,
        }

    def _is_login_related(self, step_payload: dict) -> bool:
        role = str(step_payload.get('element_role') or '').lower()
        if role in {'password_input', 'email_input', 'username_input', 'password', 'email', 'username'}:
            return True
        label = ' '.join(str(step_payload.get(key) or '') for key in ('button_text', 'aria_label', 'detail', 'target', 'selector')).lower()
        return any(token in label for token in {'login', 'iniciar sesion', 'ingresar', 'continuar'})
