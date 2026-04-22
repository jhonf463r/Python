from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from iabv_v15.services.chat.capability_ingestion import (
    ChatCapabilityIngestionService,
    _sanitize_session_id,
)


def _fixed_clock() -> datetime:
    return datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)


def _make_service(tmp_path: Path) -> ChatCapabilityIngestionService:
    return ChatCapabilityIngestionService(data_root=tmp_path, clock=_fixed_clock)


class TestDetect:
    def test_detects_gpu_when_user_claims_ownership(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        detections = service.detect('tengo una GPU RTX 4060 y quiero probar modelos')
        kinds = [item.kind for item in detections]
        assert 'hardware_gpu' in kinds

    def test_ignores_gpu_without_possession_marker(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        # Sin "tengo", "uso", "instale" etc. no hay afirmacion de capacidad.
        detections = service.detect('la GPU es una buena idea en general')
        assert detections == []

    def test_detects_local_model_mention(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        detections = service.detect('instale qwen3 y llama3 en mi laptop')
        kinds = [item.kind for item in detections]
        assert kinds.count('local_model') >= 1

    def test_detects_external_account_with_ownership(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        detections = service.detect('tengo cuenta de Claude y Codex')
        kinds = [item.kind for item in detections]
        assert 'external_account' in kinds

    def test_dedupes_multiple_matches_of_same_kind(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        detections = service.detect('tengo gpu y la gpu esta activa, la GPU se ve bien')
        # Solo una entrada por (kind, matched_text normalizado).
        gpu_count = sum(1 for item in detections if item.kind == 'hardware_gpu')
        assert gpu_count == 1

    def test_empty_message_returns_no_detections(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        assert service.detect('') == []
        assert service.detect('   ') == []


class TestRecord:
    def test_record_writes_jsonl_entry_per_detection(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        detections = service.detect('tengo gpu rtx 4060 y uso qwen3 local')
        entries = service.record(detections, session_id='sess-1', raw_message='tengo gpu rtx 4060 y uso qwen3 local')
        assert len(entries) == len(detections) >= 2
        target = tmp_path / 'chat_research_backlog' / 'sess-1.jsonl'
        assert target.exists()
        lines = [json.loads(line) for line in target.read_text(encoding='utf-8').splitlines() if line.strip()]
        assert len(lines) == len(detections)
        assert all(item['status'] == 'open' for item in lines)
        assert all(item['session_id'] == 'sess-1' for item in lines)

    def test_record_appends_across_calls(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        service.ingest('tengo gpu', session_id='sess-x')
        service.ingest('tengo docker instalado', session_id='sess-x')
        target = tmp_path / 'chat_research_backlog' / 'sess-x.jsonl'
        lines = [line for line in target.read_text(encoding='utf-8').splitlines() if line.strip()]
        assert len(lines) == 2

    def test_record_is_noop_without_detections(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        result = service.record([], session_id='sess-y', raw_message='algo neutro')
        assert result == []
        assert not (tmp_path / 'chat_research_backlog').exists()


class TestSanitizeSessionId:
    def test_replaces_path_separators(self) -> None:
        assert _sanitize_session_id('../../evil') == 'evil'

    def test_keeps_alnum_dash_underscore(self) -> None:
        assert _sanitize_session_id('sess-2026_04_21') == 'sess-2026_04_21'

    def test_empty_becomes_default(self) -> None:
        assert _sanitize_session_id('') == 'default'
        assert _sanitize_session_id('///') == 'default'


class TestListEntries:
    def test_returns_most_recent_first(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        service.ingest('tengo gpu', session_id='sess-a')
        entries = service.list_entries()
        assert entries
        assert entries[0].session_id == 'sess-a'

    def test_filter_by_session_id(self, tmp_path: Path) -> None:
        service = _make_service(tmp_path)
        service.ingest('tengo gpu', session_id='sess-a')
        service.ingest('tengo docker', session_id='sess-b')
        filtered = service.list_entries(session_id='sess-a')
        assert all(entry.session_id == 'sess-a' for entry in filtered)
        assert len(filtered) == 1
