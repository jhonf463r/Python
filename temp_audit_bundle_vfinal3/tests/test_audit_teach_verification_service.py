from __future__ import annotations

from iabv_v15.domain.models import (
    AnnotationConfidence,
    OverlayKind,
    ReplayAnnotation,
    ReplayAnnotationSource,
    ReplayAnnotationStatus,
)
from iabv_v15.services.audit.audit_teach_verification_service import AuditTeachVerificationService
from iabv_v15.services.capture.replay_visual_assembler import ReplayVisualAssembler


def _step(
    *,
    step_id: str,
    action_type: str = 'input',
    element_role: str = 'password_input',
    selector: str = '#password',
    text: str = '',
    has_screenshot: bool = True,
    overlay_rect: dict | None = None,
    metadata_snapshot: dict | None = None,
) -> dict:
    return {
        'step_id': step_id,
        'action_type': action_type,
        'element_role': element_role,
        'selector': selector,
        'target': selector,
        'text': text,
        'detail': '',
        'button_text': '',
        'aria_label': '',
        'placeholder': '',
        'has_screenshot': has_screenshot,
        'overlay_rect': overlay_rect or {'valid': False, 'x': 0.0, 'y': 0.0, 'width': 0.0, 'height': 0.0},
        'overlay_point': {'valid': False, 'x': 0.0, 'y': 0.0},
        'metadata_snapshot': metadata_snapshot or {'input_type': 'password', 'field_role': element_role},
        'screenshot_path': 'C:/tmp/demo.png' if has_screenshot else '',
        'group_key': 'C:/tmp/demo.png' if has_screenshot else f'no_screenshot::{step_id}',
        'learning_relevant': True,
        'learning_priority': 100,
        'learning_reason': 'test',
    }


def test_audit_teach_verification_service_confirms_password_field_with_visual_evidence() -> None:
    service = AuditTeachVerificationService()
    replay_steps = [
        _step(
            step_id='step-1',
            has_screenshot=True,
            overlay_rect={'valid': True, 'x': 0.15, 'y': 0.20, 'width': 0.30, 'height': 0.12},
        )
    ]

    result = service.verify_replay(episode_id='episode-1', replay_steps=replay_steps)

    assert result.audit_report is not None
    assert result.audit_report.steps_matching == 1
    assert result.audit_report.audit_passed is True
    assert result.audit_report.background_results[0].field_type_detected == 'PASSWORD_FIELD'
    assert result.audit_annotations[0].color == service.COLOR_BLUE
    assert result.audit_annotations[0].icon == 'lock'
    assert result.cross_check_result is not None
    assert result.cross_check_result.status == AnnotationConfidence.CONFIRMED


def test_audit_teach_verification_service_marks_missing_visual_confirmation_as_critical() -> None:
    service = AuditTeachVerificationService()
    replay_steps = [
        _step(
            step_id='step-2',
            has_screenshot=False,
            overlay_rect={'valid': False, 'x': 0.0, 'y': 0.0, 'width': 0.0, 'height': 0.0},
        )
    ]

    result = service.verify_replay(episode_id='episode-2', replay_steps=replay_steps)

    assert result.audit_report is not None
    assert result.audit_report.steps_diverging == 1
    assert any(issue.severity == 'critical' for issue in result.audit_report.issues)
    assert result.cross_check_result is not None
    assert result.cross_check_result.status == AnnotationConfidence.INSUFFICIENT
    assert 'visual_background_divergence' == result.cross_check_result.discrepancy


def test_replay_visual_assembler_merges_audit_annotations_into_gallery() -> None:
    service = AuditTeachVerificationService()
    assembler = ReplayVisualAssembler()
    replay_steps = [
        _step(
            step_id='step-3',
            action_type='click',
            element_role='button',
            selector='#login-submit',
            has_screenshot=True,
            overlay_rect={'valid': True, 'x': 0.40, 'y': 0.55, 'width': 0.18, 'height': 0.10},
            metadata_snapshot={'button_text': 'Ingresar'},
        )
    ]
    annotations = [
        ReplayAnnotation(
            episode_id='episode-3',
            step_id='step-3',
            screenshot_path='C:/tmp/demo.png',
            group_key='C:/tmp/demo.png',
            status=ReplayAnnotationStatus.USER_CORRECTED,
            source=ReplayAnnotationSource.USER,
            overlay_kind=OverlayKind.RECT,
            confidence_score=0.92,
            overlay_rect={'valid': True, 'x': 0.40, 'y': 0.55, 'width': 0.18, 'height': 0.10},
            overlay_label='Ingresar',
        )
    ]

    audit_result = service.verify_replay(
        episode_id='episode-3',
        replay_steps=replay_steps,
        annotations=annotations,
    )
    assembled = assembler.assemble_with_audit(
        episode_id='episode-3',
        replay_steps=replay_steps,
        annotations=annotations,
        audit_annotations=audit_result.audit_annotations,
        audit_report=audit_result.audit_report,
        cross_check_result=audit_result.cross_check_result,
    )

    assert assembled.frames
    assert assembled.frames[0]['audit_overlay_count'] >= 1
    assert assembled.timeline_steps[0]['audit_label']
    assert assembled.summary is not None
    assert assembled.summary.metadata['audit_issue_count'] == len(audit_result.audit_report.issues)
    assert assembled.summary.metadata['audit_passed'] is True
