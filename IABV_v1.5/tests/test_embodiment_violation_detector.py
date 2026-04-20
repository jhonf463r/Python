"""Tests de ``EmbodimentViolationDetector`` (PCS v1, PR E)."""

from __future__ import annotations

import pytest

from iabv_v15.domain.models import (
    EmbodimentViolationKind,
    EmbodimentViolationRecord,
    IssueSeverity,
)
from iabv_v15.services.evolution.embodiment_violation_detector import (
    EmbodimentViolationDetector,
)


def test_record_and_detect_reports_violation_when_sensor_tool_not_used() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-A',
        question_text='¿qué ventanas están abiertas ahora en la pantalla?',
        tool_ids_used=['web_search'],
        assistant_kind='chatgpt',
        trace_id='trace-1',
    )

    violations = detector.detect(session_id='sess-A')

    assert len(violations) == 1
    record = violations[0]
    assert isinstance(record, EmbodimentViolationRecord)
    assert record.session_id == 'sess-A'
    assert record.assistant_kind == 'chatgpt'
    assert record.trace_id == 'trace-1'
    assert record.expected_tool_id in {'world_model_snapshot', 'list_open_windows'}
    assert record.violation_kind == EmbodimentViolationKind.SENSOR_BYPASS
    assert record.severity == IssueSeverity.LOW
    assert 'web_search' in record.tool_ids_used
    assert record.matched_sensor, 'debe quedar registrada la keyword que disparó el match'
    assert any(ref.startswith('embodiment_manifest:') for ref in record.evidence_refs)


def test_detect_no_violation_when_expected_tool_was_used() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-B',
        question_text='¿estado de ventanas y foco del escritorio?',
        tool_ids_used=['world_model_snapshot'],
    )
    detector.record_interaction(
        session_id='sess-B',
        question_text='¿tests pasan en la suite actual?',
        tool_ids_used=['run_pytest', 'read_repo_file'],
    )

    assert detector.detect(session_id='sess-B') == []


def test_detect_no_violation_when_question_does_not_match_any_sensor() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-C',
        question_text='¿cuál es la capital de Francia?',
        tool_ids_used=['web_search'],
    )

    assert detector.detect(session_id='sess-C') == []


def test_multiple_sessions_are_isolated() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-A',
        question_text='¿bloqueo o falla del sistema?',
        tool_ids_used=['web_search'],
    )
    detector.record_interaction(
        session_id='sess-B',
        question_text='¿login de asistente externo?',
        tool_ids_used=['probe_assistant_login'],
    )

    violations_a = detector.detect(session_id='sess-A')
    violations_b = detector.detect(session_id='sess-B')

    assert len(violations_a) == 1
    assert violations_a[0].session_id == 'sess-A'
    assert violations_a[0].expected_tool_id == 'self_examination_current'
    assert violations_b == []

    unknown = detector.detect(session_id='sess-nonexistent')
    assert unknown == []


def test_buffer_respects_maxlen_and_drops_oldest_entries() -> None:
    detector = EmbodimentViolationDetector(maxlen=3)
    for index in range(5):
        detector.record_interaction(
            session_id='sess-buffer',
            question_text=f'¿ventana {index} en pantalla?',
            tool_ids_used=[],
        )

    violations = detector.detect(session_id='sess-buffer')
    assert len(violations) == detector.maxlen == 3
    texts = {record.question_text for record in violations}
    # Las 3 más recientes (index 2, 3, 4) deben seguir; las viejas se cayeron.
    assert texts == {
        '¿ventana 2 en pantalla?',
        '¿ventana 3 en pantalla?',
        '¿ventana 4 en pantalla?',
    }


def test_snapshot_global_returns_all_sessions() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-A',
        question_text='¿ventanas abiertas ahora?',
        tool_ids_used=[],
    )
    detector.record_interaction(
        session_id='sess-B',
        question_text='¿tests de pytest corren?',
        tool_ids_used=['web_search'],
    )
    detector.record_interaction(
        session_id='sess-C',
        question_text='¿qué hora es en Tokio?',
        tool_ids_used=[],
    )

    all_violations = detector.snapshot()
    sessions_with_violations = {record.session_id for record in all_violations}
    assert sessions_with_violations == {'sess-A', 'sess-B'}
    assert detector.snapshot(session_id='sess-A')[0].session_id == 'sess-A'


def test_violation_record_roundtrip_pydantic_serialization() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-R',
        question_text='¿leer archivo pyproject.toml?',
        tool_ids_used=['web_search'],
        assistant_kind='claude',
        trace_id='trace-round',
    )
    [record] = detector.detect(session_id='sess-R')

    payload = record.model_dump(mode='json')
    assert payload['session_id'] == 'sess-R'
    assert payload['violation_kind'] == EmbodimentViolationKind.SENSOR_BYPASS.value
    assert payload['severity'] == IssueSeverity.LOW.value
    assert payload['expected_tool_id'] == 'read_repo_file'

    restored = EmbodimentViolationRecord.model_validate(payload)
    assert restored.session_id == record.session_id
    assert restored.expected_tool_id == record.expected_tool_id
    assert restored.violation_kind == record.violation_kind
    assert restored.severity == record.severity
    assert restored.tool_ids_used == record.tool_ids_used
    assert restored.metadata == record.metadata


def test_maxlen_must_be_positive() -> None:
    with pytest.raises(ValueError):
        EmbodimentViolationDetector(maxlen=0)
    with pytest.raises(ValueError):
        EmbodimentViolationDetector(maxlen=-1)


def test_clear_resets_buffer() -> None:
    detector = EmbodimentViolationDetector()
    detector.record_interaction(
        session_id='sess-X',
        question_text='¿ventanas abiertas?',
        tool_ids_used=[],
    )
    assert len(detector.detect(session_id='sess-X')) == 1
    detector.clear(session_id='sess-X')
    assert detector.detect(session_id='sess-X') == []
    # clear global no rompe cuando ya está vacío.
    detector.clear()
    assert detector.snapshot() == []
