"""Tests for chat persistence connections to IABV's nervous system.

Covers:
- DecisionAuditTrail.CHAT_ROUTING phase + record_chat_routing() + chat_routing_summary()
- OSES._chat_observability_findings() produces correct findings
- PortableContextService._chat_stats_snapshot() includes chat data
- CCVM._record_chat_audit() wiring
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Lightweight in-memory AppDatabase stand-in
# ---------------------------------------------------------------------------

class _InMemoryDB:
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
                ON chat_messages(chat_session_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_created
                ON chat_messages(created_at_utc);
        """)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def fetch_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._conn.execute(sql, params).fetchone()


# ===========================================================================
# DecisionAuditTrail — CHAT_ROUTING
# ===========================================================================

class TestDecisionAuditTrailChatRouting:

    def _make_trail(self) -> Any:
        from iabv_v15.services.evolution.decision_audit_trail import DecisionAuditTrail
        tmp = tempfile.mkdtemp()
        return DecisionAuditTrail(data_root=tmp)

    def test_chat_routing_phase_exists(self) -> None:
        from iabv_v15.services.evolution.decision_audit_trail import DecisionPhase
        assert hasattr(DecisionPhase, 'CHAT_ROUTING')
        assert DecisionPhase.CHAT_ROUTING.value == 'chat_routing'

    def test_record_chat_routing_writes_entry(self) -> None:
        trail = self._make_trail()
        trail.record_chat_routing(
            reasoning_path='general_chat',
            user_goal='hola mundo',
        )
        entries = trail.load_recent()
        assert len(entries) == 1
        assert entries[0]['phase'] == 'chat_routing'
        assert entries[0]['metadata']['reasoning_path'] == 'general_chat'
        assert entries[0]['user_goal'] == 'hola mundo'

    def test_record_chat_routing_with_provider(self) -> None:
        trail = self._make_trail()
        trail.record_chat_routing(
            reasoning_path='orchestrator_inference',
            provider_id='groq',
            model_used='llama-3.3-70b',
            latency_ms=1200.0,
            confidence=0.85,
        )
        entries = trail.load_recent()
        assert entries[0]['provider_id'] == 'groq'
        assert entries[0]['model_used'] == 'llama-3.3-70b'
        assert entries[0]['latency_ms'] == 1200.0
        assert entries[0]['confidence'] == 0.85

    def test_record_chat_routing_failure(self) -> None:
        from iabv_v15.services.evolution.decision_audit_trail import DecisionOutcome
        trail = self._make_trail()
        trail.record_chat_routing(
            reasoning_path='chat_failure',
            outcome=DecisionOutcome.FAILED,
            error_detail='timeout connecting',
        )
        entries = trail.load_recent()
        assert entries[0]['outcome'] == 'failed'
        assert entries[0]['error_detail'] == 'timeout connecting'

    def test_chat_routing_summary_empty(self) -> None:
        trail = self._make_trail()
        summary = trail.chat_routing_summary()
        assert summary['status'] == 'no_data'
        assert summary['total_chat_decisions'] == 0

    def test_chat_routing_summary_with_data(self) -> None:
        trail = self._make_trail()
        for path in ['general_chat', 'general_chat', 'self_awareness', 'orchestrator_inference']:
            trail.record_chat_routing(reasoning_path=path, user_goal='test')
        summary = trail.chat_routing_summary()
        assert summary['status'] == 'analyzed'
        assert summary['total_chat_decisions'] == 4
        assert summary['by_path']['general_chat'] == 2
        assert summary['by_path']['self_awareness'] == 1


# ===========================================================================
# OSES — _chat_observability_findings
# ===========================================================================

class TestOSESChatObservability:

    def _make_repo(self) -> Any:
        from iabv_v15.infra.persistence.chat_message_repository import ChatMessageRepository
        db = _InMemoryDB()
        return ChatMessageRepository(db)

    def _make_oses(self, repo: Any = None) -> Any:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        tmp = tempfile.mkdtemp()
        storage = ArtifactStorage(root=tmp)
        oses = OperationalSelfExaminationService(
            workspace_root=tmp,
            storage=storage,
        )
        oses.chat_message_repository = repo
        return oses

    def test_no_repo_returns_empty(self) -> None:
        oses = self._make_oses(repo=None)
        findings = oses._chat_observability_findings()
        assert findings == []

    def test_empty_repo_returns_empty(self) -> None:
        repo = self._make_repo()
        oses = self._make_oses(repo=repo)
        findings = oses._chat_observability_findings()
        assert findings == []

    def test_detects_path_fixation(self) -> None:
        repo = self._make_repo()
        for i in range(15):
            repo.save(
                chat_session_id='s1', role='assistant', speaker='IABV',
                text=f'msg {i}', reasoning_path='general_chat',
                evidence_tag='observed',
            )
        oses = self._make_oses(repo=repo)
        findings = oses._chat_observability_findings()
        fixation = [f for f in findings if 'Fijacion' in f.title]
        assert len(fixation) == 1
        assert 'general_chat' in fixation[0].title

    def test_detects_evidence_gap(self) -> None:
        repo = self._make_repo()
        for i in range(12):
            repo.save(
                chat_session_id='s1', role='user', speaker='Tu',
                text=f'msg {i}', reasoning_path='general_chat',
                evidence_tag='',
            )
        oses = self._make_oses(repo=repo)
        findings = oses._chat_observability_findings()
        gap = [f for f in findings if 'Brecha' in f.title]
        assert len(gap) == 1

    def test_no_false_positive_on_balanced_paths(self) -> None:
        repo = self._make_repo()
        paths = ['general_chat', 'self_awareness', 'world_model', 'learning', 'evolution_status']
        for i, path in enumerate(paths * 3):
            repo.save(
                chat_session_id='s1', role='assistant', speaker='IABV',
                text=f'msg {i}', reasoning_path=path,
                evidence_tag='observed',
            )
        oses = self._make_oses(repo=repo)
        findings = oses._chat_observability_findings()
        fixation = [f for f in findings if 'Fijacion' in f.title]
        assert len(fixation) == 0


# ===========================================================================
# PortableContextService — _chat_stats_snapshot
# ===========================================================================

class TestPortableContextChatStats:

    def _make_repo(self) -> Any:
        from iabv_v15.infra.persistence.chat_message_repository import ChatMessageRepository
        db = _InMemoryDB()
        return ChatMessageRepository(db)

    def _make_pcs(self, repo: Any = None) -> Any:
        from iabv_v15.services.evolution.portable_context_service import PortableContextService
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        tmp = tempfile.mkdtemp()
        storage = ArtifactStorage(root=tmp)
        pcs = PortableContextService(
            workspace_root=tmp,
            storage=storage,
        )
        pcs.chat_message_repository = repo
        return pcs

    def test_not_configured_when_no_repo(self) -> None:
        pcs = self._make_pcs(repo=None)
        stats = pcs._chat_stats_snapshot()
        assert stats['status'] == 'not_configured'

    def test_empty_when_no_messages(self) -> None:
        repo = self._make_repo()
        pcs = self._make_pcs(repo=repo)
        stats = pcs._chat_stats_snapshot()
        assert stats['status'] == 'empty'
        assert stats['total'] == 0

    def test_active_with_messages(self) -> None:
        repo = self._make_repo()
        repo.save(
            chat_session_id='s1', role='user', speaker='Tu',
            text='hola', reasoning_path='', evidence_tag='',
        )
        repo.save(
            chat_session_id='s1', role='assistant', speaker='IABV',
            text='hola mundo', reasoning_path='general_chat',
            evidence_tag='observed',
        )
        pcs = self._make_pcs(repo=repo)
        stats = pcs._chat_stats_snapshot()
        assert stats['status'] == 'active'
        assert stats['total'] == 2
        assert stats['sessions'] == 1
        assert 'general_chat' in stats['by_reasoning_path']
        assert 'observed' in stats['by_evidence_tag']


# ===========================================================================
# CCVM._record_chat_audit wiring
# ===========================================================================

class TestCCVMRecordChatAudit:

    def _make_vm(self) -> tuple:
        """Build minimal CCVM with decision_audit_trail attached."""
        from iabv_v15.infra.persistence.chat_message_repository import ChatMessageRepository
        from iabv_v15.services.evolution.decision_audit_trail import DecisionAuditTrail

        db = _InMemoryDB()
        repo = ChatMessageRepository(db)
        tmp = tempfile.mkdtemp()
        trail = DecisionAuditTrail(data_root=tmp)

        config = MagicMock()
        config.payloads_dir = tmp
        config.data_dir = tmp
        config.ollama_base_url = ''
        config.lm_studio_base_url = ''
        config.ollama_embedding_model = ''
        config.ollama_available_models = []
        config.lm_studio_available_models = []
        config.auto_route_enabled = True
        config.auto_evolution_enabled = False
        config.max_evolution_steps = 5
        config.enable_experimental_features = False

        with patch('iabv_v15.ui.viewmodels.control_center_viewmodel.ControlCenterViewModel.__init__',
                   return_value=None):
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            vm = ControlCenterViewModel.__new__(ControlCenterViewModel)

        vm.config = config
        vm._chat_message_repository = repo
        vm._chat_session_id = 'test-session'
        vm._last_reasoning_path = ''
        vm._messages = []
        vm.decision_audit_trail = trail
        return vm, trail

    def test_record_chat_audit_writes_to_trail(self) -> None:
        vm, trail = self._make_vm()
        vm._record_chat_audit(
            reasoning_path='world_model',
            user_goal='que ves?',
        )
        entries = trail.load_recent()
        assert len(entries) == 1
        assert entries[0]['phase'] == 'chat_routing'
        assert entries[0]['metadata']['reasoning_path'] == 'world_model'

    def test_record_chat_audit_no_trail_no_crash(self) -> None:
        vm, _ = self._make_vm()
        vm.decision_audit_trail = None
        vm._record_chat_audit(reasoning_path='general_chat', user_goal='hola')
        # Should not raise

    def test_record_chat_audit_failure_outcome(self) -> None:
        from iabv_v15.services.evolution.decision_audit_trail import DecisionOutcome
        vm, trail = self._make_vm()
        vm._record_chat_audit(
            reasoning_path='chat_failure',
            outcome=DecisionOutcome.FAILED,
            user_goal='fallaste',
            error_detail='connection refused',
        )
        entries = trail.load_recent()
        assert entries[0]['outcome'] == 'failed'
        assert entries[0]['error_detail'] == 'connection refused'
