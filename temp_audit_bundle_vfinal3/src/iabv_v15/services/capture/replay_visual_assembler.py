from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import AuditReport, AuditedReplayResult, CrossCheckResult, ReplayAnnotation, ReplayVisualSummary, VisualAnnotation
from iabv_v15.services.capture.replay_confidence_service import ReplayConfidenceService


class ReplayVisualAssembler:
    def __init__(self, confidence_service: ReplayConfidenceService | None = None):
        self.confidence_service = confidence_service or ReplayConfidenceService()

    def build_gallery(self, *, episode_id: str, replay_steps: list[dict[str, Any]], annotations: list[ReplayAnnotation]) -> dict[str, Any]:
        by_step = {item.step_id: item for item in annotations if item.step_id}
        extra_by_frame: dict[str, list[ReplayAnnotation]] = {}
        for annotation in annotations:
            if annotation.step_id:
                continue
            key = annotation.screenshot_path or annotation.group_key or 'no_frame'
            extra_by_frame.setdefault(key, []).append(annotation)

        frames: OrderedDict[str, dict[str, Any]] = OrderedDict()
        timeline_steps: list[dict[str, Any]] = []
        critical_total = 0
        critical_good = 0
        login_good = 0
        login_total = 0
        known = uncertain = missing = user_corrected = manual_corrections = 0
        corrected_objects: list[str] = []
        critical_objects: list[str] = []
        gaps: list[str] = []

        for index, original in enumerate(replay_steps):
            step = dict(original)
            annotation = by_step.get(step.get('step_id') or '')
            classification = self.confidence_service.classify_event(step, annotation=annotation)
            step.update(classification)
            step['annotation_id'] = annotation.annotation_id if annotation is not None else ''
            step['group_key'] = self._group_key(step)
            frame_key = step['group_key']
            step['frame_index'] = -1
            if step.get('has_screenshot'):
                frame = frames.setdefault(frame_key, self._new_frame(step, frame_key))
                frame['step_ids'].append(step.get('step_id') or f'idx:{index}')
                frame['overlays'].append(self._overlay_from_step(step))
            if classification['critical_object']:
                critical_total += 1
                critical_objects.append(classification['overlay_label'])
                if classification['annotation_status'] in {'known', 'user_corrected'}:
                    critical_good += 1
            if self._login_related(step):
                login_total += 1
                if classification['annotation_status'] in {'known', 'user_corrected'}:
                    login_good += 1
            status = classification['annotation_status']
            if status == 'known':
                known += 1
            elif status == 'uncertain':
                uncertain += 1
            elif status == 'missing':
                missing += 1
                if classification['critical_object']:
                    gaps.append(f"Objeto critico sin evidencia visual: {classification['overlay_label']}")
            elif status == 'user_corrected':
                user_corrected += 1
                corrected_objects.append(classification['overlay_label'])
            if classification['annotation_source'] == 'user':
                manual_corrections += 1
            timeline_steps.append(step)

        for key, items in extra_by_frame.items():
            frame = frames.setdefault(key, self._new_annotation_frame(episode_id=episode_id, group_key=key, sample=items[0]))
            for annotation in items:
                classified = self.confidence_service.classify_event(
                    {
                        'step_id': '',
                        'action_type': 'manual_annotation',
                        'element_role': '',
                        'has_screenshot': True,
                        'overlay_rect': annotation.overlay_rect,
                        'screenshot_path': annotation.screenshot_path,
                        'screenshot_url': self._to_screenshot_url(annotation.screenshot_path),
                        'screenshot_name': self._screenshot_name(annotation.screenshot_path),
                        'target': '',
                        'selector': '',
                        'text': '',
                        'detail': '',
                        'metadata_snapshot': {},
                    },
                    annotation=annotation,
                )
                overlay_rect = self._normalize_rect(classified['overlay_rect'])
                overlay_point = self._ensure_overlay_point(
                    point=classified['overlay_point'],
                    rect=overlay_rect,
                    seed=f"{annotation.annotation_id}:{annotation.overlay_label or ''}",
                )
                frame['overlays'].append(
                    {
                        'annotation_id': annotation.annotation_id,
                        'step_id': annotation.step_id or '',
                        'step_index': -1,
                        'overlay_kind': classified['overlay_kind'],
                        'overlay_rect': overlay_rect,
                        'overlay_point': overlay_point,
                        'overlay_label': classified['overlay_label'],
                        'overlay_notes': classified['overlay_notes'],
                        'annotation_status': classified['annotation_status'],
                        'status_family': self._status_family(classified['annotation_status']),
                        'geometry_estimated': bool(overlay_point.get('estimated')) and not overlay_rect.get('valid'),
                        'annotation_source': classified['annotation_source'],
                        'confidence_score': classified['confidence_score'],
                        'display_color': classified['display_color'],
                        'active': False,
                        'critical_object': False,
                        'action_type': 'manual_annotation',
                    }
                )
                manual_corrections += 1
                user_corrected += 1
                corrected_objects.append(annotation.overlay_label or 'objeto corregido')

        frame_list = list(frames.values())
        frame_index_by_group: dict[str, int] = {}
        for frame_index, frame in enumerate(frame_list):
            frame['frame_index'] = frame_index
            frame_index_by_group[frame['group_key']] = frame_index
        for step in timeline_steps:
            step['frame_index'] = frame_index_by_group.get(step.get('group_key') or '', -1)

        useful_frames = sum(1 for frame in frame_list if any(item.get('annotation_status') in {'known', 'user_corrected', 'uncertain'} for item in frame['overlays']))
        contextual_frames = max(0, len(frame_list) - useful_frames)
        total_relevant = max(1, sum(1 for step in timeline_steps if step.get('learning_relevant') or step.get('critical_object')))
        green_count = known + user_corrected
        orange_count = uncertain
        red_count = missing
        summary = ReplayVisualSummary(
            episode_id=episode_id,
            total_frames=len(frame_list),
            useful_frames=useful_frames,
            contextual_frames=contextual_frames,
            total_overlays=sum(len(frame['overlays']) for frame in frame_list),
            known_count=known,
            uncertain_count=uncertain,
            missing_count=missing,
            user_corrected_count=user_corrected,
            green_count=green_count,
            orange_count=orange_count,
            red_count=red_count,
            manual_correction_count=manual_corrections,
            learning_coverage_score=round((green_count + orange_count) / total_relevant, 3),
            visual_alignment_score=round(green_count / total_relevant, 3),
            critical_object_coverage=round((critical_good / max(1, critical_total)), 3),
            login_visual_completeness=round((login_good / max(1, login_total)), 3),
            critical_objects=list(dict.fromkeys(item for item in critical_objects if item)),
            corrected_objects=list(dict.fromkeys(item for item in corrected_objects if item)),
            gaps=list(dict.fromkeys(gaps))[:8],
            metadata={
                'timeline_step_count': len(timeline_steps),
            },
        )
        for frame in frame_list:
            frame['overlay_count'] = len(frame['overlays'])
            frame['annotation_count'] = sum(1 for item in frame['overlays'] if item.get('annotation_source') == 'user')
            frame['status_counts'] = {
                'green': sum(1 for item in frame['overlays'] if item.get('annotation_status') in {'known', 'user_corrected'}),
                'orange': sum(1 for item in frame['overlays'] if item.get('annotation_status') == 'uncertain'),
                'red': sum(1 for item in frame['overlays'] if item.get('annotation_status') == 'missing'),
            }
        return {
            'timeline_steps': timeline_steps,
            'frames': frame_list,
            'summary': summary.model_dump(mode='json'),
        }

    def assemble_with_audit(
        self,
        *,
        episode_id: str,
        replay_steps: list[dict[str, Any]],
        annotations: list[ReplayAnnotation],
        audit_annotations: list[VisualAnnotation],
        audit_report: AuditReport | None = None,
        cross_check_result: CrossCheckResult | None = None,
    ) -> AuditedReplayResult:
        gallery = self.build_gallery(episode_id=episode_id, replay_steps=replay_steps, annotations=annotations)
        timeline_steps = [dict(item) for item in gallery.get('timeline_steps', [])]
        frames: list[dict[str, Any]] = []
        frames_by_step: dict[str, list[dict[str, Any]]] = {}
        frames_by_group: dict[str, dict[str, Any]] = {}
        for original in gallery.get('frames', []):
            frame = {
                **dict(original),
                'step_ids': list(original.get('step_ids', [])),
                'overlays': [dict(item) for item in original.get('overlays', [])],
                'status_counts': dict(original.get('status_counts', {'green': 0, 'orange': 0, 'red': 0})),
            }
            frames.append(frame)
            frames_by_group[frame.get('group_key') or frame.get('frame_id') or ''] = frame
            for step_id in frame.get('step_ids', []):
                frames_by_step.setdefault(step_id, []).append(frame)

        annotations_by_step: dict[str, list[VisualAnnotation]] = {}
        for annotation in audit_annotations:
            annotations_by_step.setdefault(annotation.step_id, []).append(annotation)

        for step in timeline_steps:
            step_annotations = annotations_by_step.get(str(step.get('step_id') or ''), [])
            if not step_annotations:
                continue
            payload = [item.model_dump(mode='json') for item in step_annotations]
            step['audit_annotations'] = payload
            primary = step_annotations[0]
            step['audit_status'] = str(primary.metadata.get('annotation_status') or 'uncertain')
            step['audit_color'] = primary.color
            step['audit_icon'] = primary.icon
            step['audit_label'] = primary.label

        for annotation in audit_annotations:
            overlay = self._audit_overlay_from_annotation(annotation)
            target_frames = frames_by_step.get(annotation.step_id, [])
            if not target_frames:
                group_key = str(annotation.metadata.get('group_key') or annotation.metadata.get('screenshot_path') or f'audit::{annotation.annotation_id}')
                frame = frames_by_group.get(group_key)
                if frame is None:
                    frame = {
                        'frame_id': group_key,
                        'episode_id': episode_id,
                        'group_key': group_key,
                        'frame_index': len(frames),
                        'screenshot_path': str(annotation.metadata.get('screenshot_path') or ''),
                        'screenshot_name': self._screenshot_name(str(annotation.metadata.get('screenshot_path') or '')),
                        'screenshot_url': self._to_screenshot_url(str(annotation.metadata.get('screenshot_path') or '')),
                        'step_ids': [annotation.step_id] if annotation.step_id else [],
                        'overlays': [],
                        'overlay_count': 0,
                        'annotation_count': 0,
                        'status_counts': {'green': 0, 'orange': 0, 'red': 0},
                    }
                    frames.append(frame)
                    frames_by_group[group_key] = frame
                    if annotation.step_id:
                        frames_by_step.setdefault(annotation.step_id, []).append(frame)
                target_frames = [frame]
            for frame in target_frames:
                frame['overlays'].append(dict(overlay))

        for frame_index, frame in enumerate(frames):
            frame['frame_index'] = frame_index
            frame['overlay_count'] = len(frame.get('overlays', []))
            frame['annotation_count'] = sum(1 for item in frame.get('overlays', []) if item.get('annotation_source') in {'user', 'audit'})
            frame['audit_overlay_count'] = sum(1 for item in frame.get('overlays', []) if item.get('annotation_source') == 'audit')
            frame['status_counts'] = {
                'green': sum(1 for item in frame.get('overlays', []) if item.get('annotation_status') in {'known', 'user_corrected'}),
                'orange': sum(1 for item in frame.get('overlays', []) if item.get('annotation_status') == 'uncertain'),
                'red': sum(1 for item in frame.get('overlays', []) if item.get('annotation_status') == 'missing'),
            }

        summary_payload = dict(gallery.get('summary') or {})
        if summary_payload:
            summary = ReplayVisualSummary.model_validate(summary_payload)
        else:
            summary = ReplayVisualSummary(episode_id=episode_id)
        summary_metadata = dict(summary.metadata or {})
        if audit_report is not None:
            summary_metadata.update(
                {
                    'audit_overall_confidence': audit_report.overall_confidence,
                    'audit_passed': audit_report.audit_passed,
                    'audit_issue_count': len(audit_report.issues),
                    'audit_suggested_improvements': list(audit_report.suggested_improvements),
                    'audit_findings': [item.description for item in audit_report.issues[:6]],
                }
            )
        if cross_check_result is not None:
            summary_metadata['audit_status'] = cross_check_result.status.value
            summary_metadata['audit_rationale'] = cross_check_result.rationale
        summary = summary.model_copy(
            update={
                'total_overlays': sum(len(frame.get('overlays', [])) for frame in frames),
                'metadata': summary_metadata,
            }
        )
        return AuditedReplayResult(
            episode_id=episode_id,
            timeline_steps=timeline_steps,
            frames=frames,
            summary=summary,
            audit_report=audit_report,
            cross_check_result=cross_check_result,
            audit_annotations=audit_annotations,
            metadata={'augmented_with_audit': True},
        )

    def _audit_overlay_from_annotation(self, annotation: VisualAnnotation) -> dict[str, Any]:
        overlay_rect = self._normalize_rect(annotation.bounding_box or {})
        overlay_point = self._ensure_overlay_point(
            point=annotation.anchor_point or {},
            rect=overlay_rect,
            seed=f"audit:{annotation.annotation_id}:{annotation.label}",
        )
        status = str(annotation.metadata.get('annotation_status') or 'uncertain')
        return {
            'annotation_id': annotation.annotation_id,
            'step_id': annotation.step_id,
            'step_index': -1,
            'overlay_kind': annotation.overlay_kind.value,
            'overlay_rect': overlay_rect,
            'overlay_point': overlay_point,
            'overlay_label': annotation.label,
            'overlay_notes': annotation.tooltip,
            'annotation_status': status,
            'status_family': self._status_family(status),
            'geometry_estimated': bool(overlay_point.get('estimated')) and not overlay_rect.get('valid'),
            'annotation_source': 'audit',
            'confidence_score': annotation.confidence_bar,
            'display_color': annotation.color,
            'active': False,
            'critical_object': bool(annotation.metadata.get('critical_object')),
            'action_type': str(annotation.metadata.get('action_type') or annotation.annotation_type),
        }
    def _group_key(self, step: dict[str, Any]) -> str:
        if step.get('screenshot_path'):
            return str(step['screenshot_path'])
        if step.get('screenshot_url'):
            return str(step['screenshot_url'])
        if step.get('linked_screenshot_id'):
            return str(step['linked_screenshot_id'])
        return f"no_screenshot::{step.get('step_id') or step.get('step_index')}"

    def _new_frame(self, step: dict[str, Any], group_key: str) -> dict[str, Any]:
        return {
            'frame_id': group_key,
            'episode_id': step.get('episode_id') or '',
            'group_key': group_key,
            'frame_index': -1,
            'screenshot_path': step.get('screenshot_path') or '',
            'screenshot_name': step.get('screenshot_name') or self._screenshot_name(step.get('screenshot_path') or ''),
            'screenshot_url': step.get('screenshot_url') or self._to_screenshot_url(step.get('screenshot_path') or ''),
            'step_ids': [],
            'overlays': [],
            'overlay_count': 0,
            'annotation_count': 0,
            'status_counts': {'green': 0, 'orange': 0, 'red': 0},
        }

    def _new_annotation_frame(self, *, episode_id: str, group_key: str, sample: ReplayAnnotation) -> dict[str, Any]:
        return {
            'frame_id': group_key or sample.annotation_id,
            'episode_id': episode_id,
            'group_key': group_key or sample.annotation_id,
            'frame_index': -1,
            'screenshot_path': sample.screenshot_path,
            'screenshot_name': self._screenshot_name(sample.screenshot_path),
            'screenshot_url': self._to_screenshot_url(sample.screenshot_path),
            'step_ids': [],
            'overlays': [],
            'overlay_count': 0,
            'annotation_count': 0,
            'status_counts': {'green': 0, 'orange': 0, 'red': 0},
        }

    def _overlay_from_step(self, step: dict[str, Any]) -> dict[str, Any]:
        overlay_rect = self._normalize_rect(step.get('overlay_rect') or {})
        overlay_point = self._ensure_overlay_point(
            point=step.get('overlay_point') or {},
            rect=overlay_rect,
            seed=f"{step.get('step_id') or ''}:{step.get('step_index', -1)}:{step.get('overlay_label') or step.get('text') or ''}",
        )
        status = step.get('annotation_status') or 'uncertain'
        return {
            'annotation_id': step.get('annotation_id') or '',
            'step_id': step.get('step_id') or '',
            'step_index': step.get('step_index', -1),
            'overlay_kind': step.get('overlay_kind') or 'rect',
            'overlay_rect': overlay_rect,
            'overlay_point': overlay_point,
            'overlay_label': step.get('overlay_label') or step.get('text') or step.get('selector') or '',
            'overlay_notes': step.get('overlay_notes') or '',
            'annotation_status': status,
            'status_family': self._status_family(status),
            'geometry_estimated': bool(overlay_point.get('estimated')) and not overlay_rect.get('valid'),
            'annotation_source': step.get('annotation_source') or 'captured',
            'confidence_score': step.get('confidence_score') or 0.0,
            'display_color': step.get('display_color') or '#f0a65b',
            'active': False,
            'critical_object': bool(step.get('critical_object')),
            'action_type': step.get('action_type') or '',
        }

    def _ensure_overlay_point(self, *, point: dict[str, Any], rect: dict[str, Any], seed: str) -> dict[str, Any]:
        normalized_point = self._normalize_point(point)
        if normalized_point.get('valid'):
            return normalized_point
        if rect.get('valid'):
            return {
                'valid': True,
                'x': min(1.0, max(0.0, rect['x'] + (rect['width'] / 2.0))),
                'y': min(1.0, max(0.0, rect['y'] + (rect['height'] / 2.0))),
                'estimated': False,
            }
        anchors = [
            (0.18, 0.18),
            (0.82, 0.18),
            (0.18, 0.82),
            (0.82, 0.82),
            (0.5, 0.22),
            (0.5, 0.78),
            (0.28, 0.5),
            (0.72, 0.5),
        ]
        index = abs(hash(seed or 'overlay')) % len(anchors)
        x, y = anchors[index]
        return {'valid': True, 'x': x, 'y': y, 'estimated': True}

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
        normalized = {
            'valid': True,
            'x': float(point.get('x', 0.0) or 0.0),
            'y': float(point.get('y', 0.0) or 0.0),
        }
        if 'estimated' in point:
            normalized['estimated'] = bool(point.get('estimated'))
        return normalized

    def _status_family(self, status: str) -> str:
        if status in {'known', 'user_corrected'}:
            return 'green'
        if status == 'missing':
            return 'red'
        return 'orange'

    def _login_related(self, step: dict[str, Any]) -> bool:
        role = str(step.get('element_role') or '').lower()
        label_blob = ' '.join(str(step.get(key) or '') for key in ('button_text', 'aria_label', 'detail', 'target', 'selector')).lower()
        if role in {'password_input', 'email_input', 'username_input', 'password', 'email', 'username'}:
            return True
        if any(token in label_blob for token in {'login', 'iniciar sesion', 'ingresar', 'continuar'}):
            return True
        return False

    def _to_screenshot_url(self, screenshot_path: str) -> str:
        if not screenshot_path:
            return ''
        try:
            candidate = Path(screenshot_path)
            if candidate.exists():
                return candidate.resolve().as_uri()
        except Exception:
            return screenshot_path
        return screenshot_path

    def _screenshot_name(self, screenshot_path: str) -> str:
        if not screenshot_path:
            return ''
        try:
            return Path(screenshot_path).name
        except Exception:
            return screenshot_path.replace('\\', '/').split('/')[-1]

