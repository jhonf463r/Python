"""Persistence for chat messages with cognitive trace.

Each message exchanged between user and assistant is persisted to SQLite
so the full conversation history survives restarts.  The ``reasoning_path``
column records *how* the system generated each response (e.g.
``llm_grounded``, ``llm_supplemented``, ``template_fallback``), enabling
post-hoc analysis of cognitive performance.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from iabv_v15.infra.persistence.database import AppDatabase

_log = logging.getLogger(__name__)


class ChatMessageRepository:
    """Thin persistence layer — mirrors the in-memory ``_chat_messages`` list."""

    def __init__(self, db: AppDatabase) -> None:
        self.db = db

    def save(
        self,
        *,
        chat_session_id: str,
        role: str,
        speaker: str,
        text: str,
        meta: str = '',
        evidence_tag: str = '',
        reasoning_path: str = '',
        metadata: dict[str, Any] | None = None,
    ) -> str:
        message_id = f'{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")}-{uuid.uuid4().hex[:8]}'
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        try:
            self.db.execute(
                """
                INSERT INTO chat_messages
                (message_id, chat_session_id, role, speaker, text, meta,
                 evidence_tag, reasoning_path, metadata_json, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    chat_session_id,
                    role,
                    speaker,
                    text[:10000],
                    meta[:2000],
                    evidence_tag,
                    reasoning_path,
                    metadata_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception as exc:
            _log.debug('chat_message_save_failed: %s', exc)
        return message_id

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT message_id, chat_session_id, role, speaker, text, meta,
                   evidence_tag, reasoning_path, metadata_json, created_at_utc
            FROM chat_messages
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_dict(r) for r in reversed(rows)]

    def list_by_session(self, chat_session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT message_id, chat_session_id, role, speaker, text, meta,
                   evidence_tag, reasoning_path, metadata_json, created_at_utc
            FROM chat_messages
            WHERE chat_session_id = ?
            ORDER BY created_at_utc ASC
            LIMIT ?
            """,
            (chat_session_id, limit),
        )
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        row = self.db.fetchone('SELECT COUNT(*) AS cnt FROM chat_messages')
        return int(row['cnt']) if row else 0

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT chat_session_id,
                   MIN(created_at_utc) AS started_at,
                   MAX(created_at_utc) AS last_at,
                   COUNT(*) AS message_count
            FROM chat_messages
            GROUP BY chat_session_id
            ORDER BY MAX(created_at_utc) DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Retention policy
    # ------------------------------------------------------------------
    _MAX_DETAILED = 1000
    _SUMMARY_ROLE = 'system'
    _SUMMARY_SPEAKER = 'retention'

    def apply_retention(self) -> int:
        """Compact old sessions when total messages exceed the cap.

        The oldest sessions (beyond ``_MAX_DETAILED``) are compressed into
        a single summary row per session, then the detail rows are deleted.
        Returns the number of detail rows removed.
        """
        total = self.count()
        if total <= self._MAX_DETAILED:
            return 0
        overflow = total - self._MAX_DETAILED
        oldest_rows = self.db.fetchall(
            """
            SELECT message_id, chat_session_id, role, speaker, text,
                   evidence_tag, reasoning_path, created_at_utc
            FROM chat_messages
            ORDER BY created_at_utc ASC
            LIMIT ?
            """,
            (overflow,),
        )
        if not oldest_rows:
            return 0
        sessions_to_compact: dict[str, list[dict[str, Any]]] = {}
        ids_to_delete: list[str] = []
        for row in oldest_rows:
            sid = row['chat_session_id']
            sessions_to_compact.setdefault(sid, []).append(dict(row))
            ids_to_delete.append(row['message_id'])

        removed = 0
        for sid, messages in sessions_to_compact.items():
            summary = self._build_session_summary(sid, messages)
            existing = self.db.fetchone(
                "SELECT message_id FROM chat_messages "
                "WHERE chat_session_id = ? AND speaker = ? LIMIT 1",
                (sid, self._SUMMARY_SPEAKER),
            )
            if not existing:
                self.save(
                    chat_session_id=sid,
                    role=self._SUMMARY_ROLE,
                    speaker=self._SUMMARY_SPEAKER,
                    text=summary,
                    reasoning_path='retention_summary',
                )
            batch_size = 200
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i:i + batch_size]
                placeholders = ','.join('?' for _ in batch)
                try:
                    self.db.execute(
                        f"DELETE FROM chat_messages WHERE message_id IN ({placeholders})"
                        f" AND speaker != ?",
                        (*batch, self._SUMMARY_SPEAKER),
                    )
                    removed += len(batch)
                except Exception as exc:
                    _log.debug('retention_delete_failed: %s', exc)
        return removed

    @staticmethod
    def _build_session_summary(session_id: str, messages: list[dict[str, Any]]) -> str:
        user_msgs = [m for m in messages if m.get('role') == 'user']
        assistant_msgs = [m for m in messages if m.get('role') == 'assistant']
        paths: dict[str, int] = {}
        tags: dict[str, int] = {}
        for m in assistant_msgs:
            p = m.get('reasoning_path', '') or ''
            if p:
                paths[p] = paths.get(p, 0) + 1
            t = m.get('evidence_tag', '') or ''
            if t:
                tags[t] = tags.get(t, 0) + 1
        topics = [m.get('text', '')[:80] for m in user_msgs[:5]]
        started = messages[0].get('created_at_utc', '?') if messages else '?'
        ended = messages[-1].get('created_at_utc', '?') if messages else '?'
        parts = [
            f'Sesion {session_id} | {started} -> {ended}',
            f'Mensajes: {len(user_msgs)} usuario, {len(assistant_msgs)} asistente',
        ]
        if paths:
            parts.append(f'Paths: {", ".join(f"{k}={v}" for k, v in paths.items())}')
        if tags:
            parts.append(f'Tags: {", ".join(f"{k}={v}" for k, v in tags.items())}')
        if topics:
            parts.append(f'Temas: {" | ".join(topics)}')
        return '\n'.join(parts)

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        result: dict[str, Any] = {
            'message_id': row['message_id'],
            'chat_session_id': row['chat_session_id'],
            'role': row['role'],
            'speaker': row['speaker'],
            'text': row['text'],
            'meta': row['meta'],
            'created_at_utc': row['created_at_utc'],
        }
        evidence_tag = row['evidence_tag']
        if evidence_tag:
            result['evidence_tag'] = evidence_tag
        reasoning_path = row['reasoning_path']
        if reasoning_path:
            result['reasoning_path'] = reasoning_path
        try:
            md = json.loads(row['metadata_json'])
            if md:
                result['metadata'] = md
        except (json.JSONDecodeError, TypeError):
            pass
        return result
