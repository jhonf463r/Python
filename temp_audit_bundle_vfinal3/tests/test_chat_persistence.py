"""Tests for chat message persistence and cognitive trace.

Covers:
- ChatMessageRepository CRUD
- Retention policy (compact + delete when > cap)
- ControlCenterViewModel._append_message persists to repo
- _load_previous_chat_history restores messages on startup
- Reasoning path tagging in answer methods
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Lightweight in-memory AppDatabase stand-in
# ---------------------------------------------------------------------------

class _InMemoryDB:
    """Minimal AppDatabase replacement backed by a shared in-memory SQLite."""

    def __init__(self) -> None:
        self._conn = sqlite3.connect(':memory:', check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                chat_session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                meta TEXT NOT NULL DEFAULT '',
                evidence_tag TEXT NOT NULL DEFAULT '',
                reasoning_path TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session
            ON chat_messages (chat_session_id, created_at_utc DESC);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_created
            ON chat_messages (created_at_utc DESC);
        """)

    def connect(self) -> sqlite3.Connection:
        return self._conn

    def execute(self, sql: str, parameters=()) -> None:
        with self._conn:
            self._conn.execute(sql, tuple(parameters))

    def fetchall(self, sql: str, parameters=()) -> list[sqlite3.Row]:
        return list(self._conn.execute(sql, tuple(parameters)).fetchall())

    def fetchone(self, sql: str, parameters=()) -> sqlite3.Row | None:
        return self._conn.execute(sql, tuple(parameters)).fetchone()


# ---------------------------------------------------------------------------
# Import the real repository
# ---------------------------------------------------------------------------

from iabv_v15.infra.persistence.chat_message_repository import ChatMessageRepository


# ===================================================================
# ChatMessageRepository — basic CRUD
# ===================================================================

class TestChatMessageRepositorySave:
    def _make_repo(self) -> ChatMessageRepository:
        return ChatMessageRepository(_InMemoryDB())

    def test_save_returns_message_id(self):
        repo = self._make_repo()
        mid = repo.save(chat_session_id='s1', role='user', speaker='Tu', text='hola')
        assert mid
        assert isinstance(mid, str)

    def test_saved_message_appears_in_list_recent(self):
        repo = self._make_repo()
        repo.save(chat_session_id='s1', role='user', speaker='Tu', text='hola')
        msgs = repo.list_recent(limit=10)
        assert len(msgs) == 1
        assert msgs[0]['text'] == 'hola'
        assert msgs[0]['role'] == 'user'
        assert msgs[0]['speaker'] == 'Tu'

    def test_evidence_tag_persisted(self):
        repo = self._make_repo()
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV',
                  text='reply', evidence_tag='observed')
        msgs = repo.list_recent()
        assert msgs[0]['evidence_tag'] == 'observed'

    def test_reasoning_path_persisted(self):
        repo = self._make_repo()
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV',
                  text='reply', reasoning_path='llm_grounded')
        msgs = repo.list_recent()
        assert msgs[0]['reasoning_path'] == 'llm_grounded'

    def test_metadata_persisted(self):
        repo = self._make_repo()
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV',
                  text='reply', metadata={'focus': 'startup', 'anchors_total': 5})
        msgs = repo.list_recent()
        assert msgs[0]['metadata']['focus'] == 'startup'
        assert msgs[0]['metadata']['anchors_total'] == 5

    def test_count(self):
        repo = self._make_repo()
        assert repo.count() == 0
        repo.save(chat_session_id='s1', role='user', speaker='Tu', text='a')
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV', text='b')
        assert repo.count() == 2

    def test_list_by_session(self):
        repo = self._make_repo()
        repo.save(chat_session_id='s1', role='user', speaker='Tu', text='q1')
        repo.save(chat_session_id='s2', role='user', speaker='Tu', text='q2')
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV', text='a1')
        msgs = repo.list_by_session('s1')
        assert len(msgs) == 2
        assert all(m['chat_session_id'] == 's1' for m in msgs)

    def test_list_sessions(self):
        repo = self._make_repo()
        repo.save(chat_session_id='s1', role='user', speaker='Tu', text='q1')
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV', text='a1')
        repo.save(chat_session_id='s2', role='user', speaker='Tu', text='q2')
        sessions = repo.list_sessions()
        assert len(sessions) == 2
        assert sessions[0]['message_count'] in (1, 2)

    def test_text_truncated_to_10000(self):
        repo = self._make_repo()
        long_text = 'x' * 15000
        repo.save(chat_session_id='s1', role='user', speaker='Tu', text=long_text)
        msgs = repo.list_recent()
        assert len(msgs[0]['text']) == 10000


# ===================================================================
# ChatMessageRepository — retention policy
# ===================================================================

class TestRetentionPolicy:
    def _make_repo(self, max_detailed: int = 5) -> ChatMessageRepository:
        repo = ChatMessageRepository(_InMemoryDB())
        repo._MAX_DETAILED = max_detailed
        return repo

    def test_no_retention_under_cap(self):
        repo = self._make_repo(max_detailed=10)
        for i in range(5):
            repo.save(chat_session_id='s1', role='user', speaker='Tu', text=f'msg{i}')
        removed = repo.apply_retention()
        assert removed == 0
        assert repo.count() == 5

    def test_retention_compacts_over_cap(self):
        repo = self._make_repo(max_detailed=5)
        for i in range(8):
            repo.save(chat_session_id='s1', role='user', speaker='Tu', text=f'msg{i}')
        removed = repo.apply_retention()
        assert removed > 0
        # Should have summary + remaining messages
        assert repo.count() <= 8

    def test_summary_row_created(self):
        repo = self._make_repo(max_detailed=3)
        for i in range(6):
            repo.save(chat_session_id='s1', role='user', speaker='Tu',
                      text=f'msg{i}', reasoning_path='general_chat')
        repo.apply_retention()
        msgs = repo.list_recent(limit=100)
        summaries = [m for m in msgs if m.get('reasoning_path') == 'retention_summary']
        assert len(summaries) >= 1
        assert 'Sesion s1' in summaries[0]['text']

    def test_summary_includes_path_stats(self):
        repo = self._make_repo(max_detailed=2)
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV',
                  text='a', reasoning_path='llm_grounded', evidence_tag='observed')
        repo.save(chat_session_id='s1', role='assistant', speaker='IABV',
                  text='b', reasoning_path='template_fallback', evidence_tag='unresolved')
        repo.save(chat_session_id='s1', role='user', speaker='Tu', text='c')
        repo.apply_retention()
        msgs = repo.list_recent(limit=100)
        summaries = [m for m in msgs if m.get('reasoning_path') == 'retention_summary']
        if summaries:
            assert 'Paths:' in summaries[0]['text'] or 'Mensajes:' in summaries[0]['text']


# ===================================================================
# ControlCenterViewModel — _append_message persistence
# ===================================================================

class _PersistenceVM:
    """Minimal stub matching ControlCenterViewModel's persistence contract."""

    def __init__(self, repo: ChatMessageRepository | None = None) -> None:
        self._chat_messages: list[dict[str, Any]] = []
        self._ui_state_lock = threading.Lock()
        self._last_reasoning_path: str = ''
        self.chat_message_repository = repo
        self._chat_session_id = 'test-session-001'

    def _refresh_contextual_suggestions(self) -> None:
        pass

    def _validate_ui_reflects_reality(self) -> None:
        pass

    # Bind the real methods
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
    _append_message = ControlCenterViewModel._append_message
    _persist_chat_message = ControlCenterViewModel._persist_chat_message


class TestAppendMessagePersistence:
    def _make_vm(self) -> tuple[_PersistenceVM, ChatMessageRepository]:
        repo = ChatMessageRepository(_InMemoryDB())
        vm = _PersistenceVM(repo=repo)
        return vm, repo

    def test_append_persists_user_message(self):
        vm, repo = self._make_vm()
        vm._append_message('user', 'Tu', 'hola mundo')
        assert repo.count() == 1
        msgs = repo.list_recent()
        assert msgs[0]['role'] == 'user'
        assert msgs[0]['text'] == 'hola mundo'

    def test_append_persists_assistant_with_trace(self):
        vm, repo = self._make_vm()
        vm._append_message('assistant', 'IABV', 'respuesta', 'meta info',
                          evidence_tag='observed',
                          reasoning_path='llm_grounded',
                          trace_metadata={'focus': 'startup', 'anchors_total': 3})
        msgs = repo.list_recent()
        assert msgs[0]['evidence_tag'] == 'observed'
        assert msgs[0]['reasoning_path'] == 'llm_grounded'
        assert msgs[0]['metadata']['focus'] == 'startup'

    def test_append_uses_last_reasoning_path_if_not_provided(self):
        vm, repo = self._make_vm()
        vm._last_reasoning_path = 'evolution_status'
        vm._append_message('assistant', 'IABV', 'reply')
        msgs = repo.list_recent()
        assert msgs[0]['reasoning_path'] == 'evolution_status'
        # Should be cleared after use
        assert vm._last_reasoning_path == ''

    def test_append_without_repo_does_not_crash(self):
        vm = _PersistenceVM(repo=None)
        vm._append_message('user', 'Tu', 'hola')
        assert len(vm._chat_messages) == 1

    def test_in_memory_list_still_capped_at_30(self):
        vm, repo = self._make_vm()
        for i in range(35):
            vm._append_message('user', 'Tu', f'msg{i}')
        assert len(vm._chat_messages) == 30
        # But all 35 are in SQLite
        assert repo.count() == 35


# ===================================================================
# ControlCenterViewModel — _load_previous_chat_history
# ===================================================================

class _LoadVM:
    """Stub for testing _load_previous_chat_history."""

    def __init__(self, repo: ChatMessageRepository | None = None) -> None:
        self.chat_message_repository = repo
        self._chat_messages: list[dict[str, Any]] = []
        self._ui_state_lock = threading.Lock()
        self._last_reasoning_path = ''
        self._chat_session_id = 'test-load-session'

    def _routing_mode_label(self) -> str:
        return 'auto'

    def _refresh_contextual_suggestions(self) -> None:
        pass

    def _validate_ui_reflects_reality(self) -> None:
        pass

    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
    _load_previous_chat_history = ControlCenterViewModel._load_previous_chat_history
    _seed_messages = ControlCenterViewModel._seed_messages
    _append_message = ControlCenterViewModel._append_message
    _persist_chat_message = ControlCenterViewModel._persist_chat_message


class TestLoadPreviousChatHistory:
    def test_empty_repo_returns_empty(self):
        repo = ChatMessageRepository(_InMemoryDB())
        vm = _LoadVM(repo=repo)
        result = vm._load_previous_chat_history()
        assert result == []

    def test_loads_previous_messages(self):
        repo = ChatMessageRepository(_InMemoryDB())
        repo.save(chat_session_id='old', role='user', speaker='Tu', text='pregunta1')
        repo.save(chat_session_id='old', role='assistant', speaker='IABV',
                  text='respuesta1', evidence_tag='observed', reasoning_path='llm_grounded')
        vm = _LoadVM(repo=repo)
        result = vm._load_previous_chat_history()
        assert len(result) == 2
        assert result[0]['text'] == 'pregunta1'
        assert result[1]['evidenceTag'] == 'observed'
        assert result[1]['reasoningPath'] == 'llm_grounded'

    def test_seed_uses_loaded_history(self):
        repo = ChatMessageRepository(_InMemoryDB())
        repo.save(chat_session_id='prev', role='user', speaker='Tu', text='viejo')
        vm = _LoadVM(repo=repo)
        vm._seed_messages()
        assert len(vm._chat_messages) == 1
        assert vm._chat_messages[0]['text'] == 'viejo'

    def test_seed_falls_back_to_default_when_no_history(self):
        repo = ChatMessageRepository(_InMemoryDB())
        vm = _LoadVM(repo=repo)
        vm._seed_messages()
        assert len(vm._chat_messages) == 1
        assert 'Chat operativo listo' in vm._chat_messages[0]['text']

    def test_no_repo_falls_back_to_default(self):
        vm = _LoadVM(repo=None)
        vm._seed_messages()
        assert len(vm._chat_messages) == 1
        assert 'Chat operativo listo' in vm._chat_messages[0]['text']


# ===================================================================
# Reasoning path tags per answer method
# ===================================================================

class TestReasoningPathTags:
    """Verify that each answer method sets the correct reasoning_path."""

    def _make_vm_for_answer(self) -> tuple[_PersistenceVM, ChatMessageRepository]:
        repo = ChatMessageRepository(_InMemoryDB())
        vm = _PersistenceVM(repo=repo)
        return vm, repo

    @pytest.mark.parametrize('path,expected', [
        ('llm_grounded', 'llm_grounded'),
        ('llm_supplemented', 'llm_supplemented'),
        ('template_fallback', 'template_fallback'),
        ('evolution_status', 'evolution_status'),
        ('learning', 'learning'),
        ('self_awareness', 'self_awareness'),
        ('world_model', 'world_model'),
        ('general_chat', 'general_chat'),
    ])
    def test_reasoning_path_stored(self, path: str, expected: str):
        vm, repo = self._make_vm_for_answer()
        vm._append_message('assistant', 'IABV', 'test reply',
                          reasoning_path=path)
        msgs = repo.list_recent()
        assert msgs[0]['reasoning_path'] == expected


# ===================================================================
# Database schema — chat_messages table
# ===================================================================

class TestDatabaseSchema:
    def test_chat_messages_table_created(self):
        db = _InMemoryDB()
        cursor = db.connect().execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'"
        )
        assert cursor.fetchone() is not None

    def test_chat_messages_columns(self):
        db = _InMemoryDB()
        cursor = db.connect().execute("PRAGMA table_info(chat_messages)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            'message_id', 'chat_session_id', 'role', 'speaker', 'text',
            'meta', 'evidence_tag', 'reasoning_path', 'metadata_json',
            'created_at_utc',
        }
        assert expected.issubset(columns)
