from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import ReplayAnnotation, ReplayAnnotationSource, ReplayAnnotationStatus
from iabv_v15.infra.config import load_app_config
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.replay_annotation_repository import ReplayAnnotationRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.capture.replay_annotation_service import ReplayAnnotationService
from iabv_v15.services.capture.replay_confidence_service import ReplayConfidenceService
from iabv_v15.services.capture.replay_visual_assembler import ReplayVisualAssembler


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_replay_annotation_service_persists_updates_and_clears() -> None:
    root = _workspace('replay_annotation_service')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    repo = ReplayAnnotationRepository(db, ArtifactStorage(config.replay_annotations_dir))
    service = ReplayAnnotationService(repo)

    saved = service.save_user_annotation(
        episode_id='ep-1',
        screenshot_path='C:/tmp/capture.png',
        group_key='frame-1',
        step_id='step-1',
        overlay_rect={'valid': True, 'x': 0.1, 'y': 0.2, 'width': 0.3, 'height': 0.2},
        overlay_label='Boton login',
    )

    items = service.list_for_episode('ep-1')
    assert len(items) == 1
    assert items[0].overlay_label == 'Boton login'

    updated = service.update_status(saved.annotation_id, ReplayAnnotationStatus.KNOWN.value)
    assert updated is not None
    assert updated.status == ReplayAnnotationStatus.KNOWN

    relabeled = service.update_label(saved.annotation_id, 'Boton ingresar')
    assert relabeled is not None
    assert relabeled.overlay_label == 'Boton ingresar'

    service.clear(saved.annotation_id)
    assert service.list_for_episode('ep-1') == []


def test_replay_visual_assembler_builds_gallery_with_multiple_overlays_and_colors() -> None:
    assembler = ReplayVisualAssembler(ReplayConfidenceService())
    screenshot_path = 'C:/tmp/login_capture.png'
    replay_steps = [
        {
            'step_id': 'step-email',
            'step_index': 1,
            'episode_id': 'ep-1',
            'action_type': 'input',
            'element_role': 'email',
            'button_text': '',
            'aria_label': '',
            'placeholder': 'correo',
            'text': 'f***@mail.com',
            'target': '#email',
            'selector': '#email',
            'detail': 'Correo digitado',
            'capture_source': 'captured',
            'has_screenshot': True,
            'screenshot_path': screenshot_path,
            'screenshot_url': screenshot_path,
            'screenshot_name': 'login_capture.png',
            'overlay_rect': {'valid': True, 'x': 0.1, 'y': 0.2, 'width': 0.3, 'height': 0.08},
            'metadata_snapshot': {},
            'learning_relevant': True,
            'critical_object': True,
        },
        {
            'step_id': 'step-submit',
            'step_index': 2,
            'episode_id': 'ep-1',
            'action_type': 'click',
            'element_role': 'button',
            'button_text': 'Ingresar',
            'aria_label': '',
            'placeholder': '',
            'text': 'Ingresar',
            'target': '#submit',
            'selector': '#submit',
            'detail': 'Click en ingresar',
            'capture_source': 'captured',
            'has_screenshot': True,
            'screenshot_path': screenshot_path,
            'screenshot_url': screenshot_path,
            'screenshot_name': 'login_capture.png',
            'overlay_rect': {'valid': True, 'x': 0.12, 'y': 0.42, 'width': 0.18, 'height': 0.08},
            'metadata_snapshot': {},
            'learning_relevant': True,
            'critical_object': True,
        },
        {
            'step_id': 'step-frame',
            'step_index': 3,
            'episode_id': 'ep-1',
            'action_type': 'frame_fallback',
            'element_role': 'frame',
            'button_text': '',
            'aria_label': '',
            'placeholder': '',
            'text': 'LoginAndGetTempToken',
            'target': 'frame:login',
            'selector': 'frame:login',
            'detail': 'Fallback de frame',
            'capture_source': 'frame_fallback_structured',
            'has_screenshot': False,
            'screenshot_path': '',
            'screenshot_url': '',
            'screenshot_name': '',
            'overlay_rect': {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0},
            'metadata_snapshot': {},
            'learning_relevant': True,
            'critical_object': False,
        },
    ]
    annotations = [
        ReplayAnnotation(
            episode_id='ep-1',
            step_id='step-submit',
            screenshot_path=screenshot_path,
            group_key=screenshot_path,
            status=ReplayAnnotationStatus.USER_CORRECTED,
            source=ReplayAnnotationSource.USER,
            overlay_label='Boton ingresar corregido',
            overlay_rect={'valid': True, 'x': 0.12, 'y': 0.42, 'width': 0.18, 'height': 0.08},
        )
    ]

    gallery = assembler.build_gallery(episode_id='ep-1', replay_steps=replay_steps, annotations=annotations)

    assert len(gallery['frames']) == 1
    assert gallery['frames'][0]['overlay_count'] >= 2
    assert gallery['summary']['green_count'] >= 1
    assert gallery['summary']['manual_correction_count'] >= 1
    assert gallery['timeline_steps'][1]['annotation_status'] == 'user_corrected'


def test_replay_visual_assembler_creates_fallback_marker_for_uncertain_overlay_without_rect() -> None:
    assembler = ReplayVisualAssembler(ReplayConfidenceService())
    screenshot_path = 'C:/tmp/checkpoint.png'
    replay_steps = [
        {
            'step_id': 'step-checkpoint',
            'step_index': 1,
            'episode_id': 'ep-2',
            'action_type': 'visual_checkpoint',
            'element_role': '',
            'button_text': '',
            'aria_label': '',
            'placeholder': '',
            'text': '',
            'target': '',
            'selector': '',
            'detail': 'Checkpoint visual capturado por intervalo.',
            'capture_source': 'captured',
            'has_screenshot': True,
            'screenshot_path': screenshot_path,
            'screenshot_url': screenshot_path,
            'screenshot_name': 'checkpoint.png',
            'overlay_rect': {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0},
            'overlay_point': {'valid': False, 'x': 0, 'y': 0},
            'metadata_snapshot': {},
            'learning_relevant': True,
            'critical_object': False,
        },
    ]

    gallery = assembler.build_gallery(episode_id='ep-2', replay_steps=replay_steps, annotations=[])

    overlay = gallery['frames'][0]['overlays'][0]
    assert overlay['overlay_point']['valid'] is True
    assert overlay['geometry_estimated'] is True
    assert overlay['status_family'] == 'orange'
    assert overlay['overlay_label'] == 'checkpoint visual'
