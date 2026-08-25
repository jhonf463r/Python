from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import OverlayKind, ReplayAnnotation, ReplayAnnotationSource, ReplayAnnotationStatus
from iabv_v15.infra.persistence.replay_annotation_repository import ReplayAnnotationRepository


class ReplayAnnotationService:
    def __init__(self, repository: ReplayAnnotationRepository):
        self.repository = repository

    def list_for_episode(self, episode_id: str) -> list[ReplayAnnotation]:
        return self.repository.list_for_episode(episode_id)

    def save_user_annotation(
        self,
        *,
        episode_id: str,
        screenshot_path: str,
        group_key: str,
        step_id: str | None = None,
        linked_screenshot_id: str = '',
        overlay_kind: str = OverlayKind.RECT.value,
        status: str = ReplayAnnotationStatus.USER_CORRECTED.value,
        confidence_score: float = 0.95,
        overlay_rect: dict[str, float] | None = None,
        overlay_point: dict[str, float] | None = None,
        overlay_label: str = '',
        overlay_notes: str = '',
        metadata: dict[str, Any] | None = None,
    ) -> ReplayAnnotation:
        existing = self._find_target(episode_id=episode_id, step_id=step_id, screenshot_path=screenshot_path)
        now = datetime.now(timezone.utc)
        payload = dict(metadata or {})
        if existing is not None:
            annotation = existing.model_copy(update={
                'updated_at_utc': now,
                'screenshot_path': screenshot_path,
                'group_key': group_key or existing.group_key,
                'linked_screenshot_id': linked_screenshot_id or existing.linked_screenshot_id,
                'overlay_kind': OverlayKind(overlay_kind),
                'status': ReplayAnnotationStatus(status),
                'source': ReplayAnnotationSource.USER,
                'confidence_score': confidence_score,
                'overlay_rect': overlay_rect or existing.overlay_rect,
                'overlay_point': overlay_point or existing.overlay_point,
                'overlay_label': overlay_label or existing.overlay_label,
                'overlay_notes': overlay_notes or existing.overlay_notes,
                'metadata': {**existing.metadata, **payload},
            })
        else:
            annotation = ReplayAnnotation(
                episode_id=episode_id,
                step_id=step_id,
                screenshot_path=screenshot_path,
                group_key=group_key,
                linked_screenshot_id=linked_screenshot_id,
                overlay_kind=OverlayKind(overlay_kind),
                status=ReplayAnnotationStatus(status),
                source=ReplayAnnotationSource.USER,
                confidence_score=confidence_score,
                overlay_rect=overlay_rect or {},
                overlay_point=overlay_point or {},
                overlay_label=overlay_label,
                overlay_notes=overlay_notes,
                metadata=payload,
            )
        return self.repository.save(annotation)

    def update_status(self, annotation_id: str, status: str) -> ReplayAnnotation | None:
        annotation = self.repository.get(annotation_id)
        if annotation is None:
            return None
        updated = annotation.model_copy(update={
            'status': ReplayAnnotationStatus(status),
            'source': ReplayAnnotationSource.USER,
            'updated_at_utc': datetime.now(timezone.utc),
        })
        return self.repository.save(updated)

    def update_label(self, annotation_id: str, label: str) -> ReplayAnnotation | None:
        annotation = self.repository.get(annotation_id)
        if annotation is None:
            return None
        updated = annotation.model_copy(update={
            'overlay_label': label.strip(),
            'source': ReplayAnnotationSource.USER,
            'updated_at_utc': datetime.now(timezone.utc),
        })
        return self.repository.save(updated)

    def clear(self, annotation_id: str) -> None:
        self.repository.delete(annotation_id)

    def _find_target(self, *, episode_id: str, step_id: str | None, screenshot_path: str) -> ReplayAnnotation | None:
        candidates = self.repository.list_for_episode(episode_id)
        if step_id:
            for item in candidates:
                if item.step_id == step_id:
                    return item
        normalized = (screenshot_path or '').strip().lower()
        if normalized:
            for item in candidates:
                if (item.screenshot_path or '').strip().lower() == normalized and not step_id:
                    return item
        return None
