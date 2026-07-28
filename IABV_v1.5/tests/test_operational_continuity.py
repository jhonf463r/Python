"""Tests for Operational Continuity Contract.

Tests the unified continuity contract for task handoff, session continuity,
and multi-agent traceability.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from iabv_v15.domain.models import (
    AccountSession,
    AgentHandoff,
    ContinuityState,
    OperationalContinuity,
)


class TestOperationalContinuity:
    """Test the OperationalContinuity model."""

    def test_create_continuity(self):
        """Test creating a basic continuity contract."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
            state=ContinuityState.IN_PROGRESS,
        )
        assert continuity.task_id != ""
        assert continuity.objective == "Test objective"
        assert continuity.current_agent == "test_agent"
        assert continuity.state == ContinuityState.IN_PROGRESS
        assert continuity.progress_percentage == 0.0
        assert len(continuity.agent_handoffs) == 0
        assert len(continuity.account_sessions) == 0
        assert continuity.created_at is not None
        assert continuity.updated_at is not None

    def test_agent_handoff(self):
        """Test recording an agent handoff."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="agent_a",
        )
        
        handoff = AgentHandoff(
            from_agent="agent_a",
            to_agent="agent_b",
            handoff_reason="quota_exhausted",
        )
        continuity.agent_handoffs.append(handoff)
        continuity.current_agent = "agent_b"
        continuity.state = ContinuityState.TRANSFERRED
        
        assert len(continuity.agent_handoffs) == 1
        assert continuity.agent_handoffs[0].from_agent == "agent_a"
        assert continuity.agent_handoffs[0].to_agent == "agent_b"
        assert continuity.current_agent == "agent_b"
        assert continuity.state == ContinuityState.TRANSFERRED

    def test_account_session(self):
        """Test recording an account session."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
        )
        
        session = AccountSession(
            email="test@example.com",
            browser="chrome",
            profile="default",
            tool="claude",
            quota_used=5,
            success=True,
        )
        continuity.account_sessions.append(session)
        continuity.current_account_session = session
        
        assert len(continuity.account_sessions) == 1
        assert continuity.account_sessions[0].email == "test@example.com"
        assert continuity.account_sessions[0].quota_used == 5
        assert continuity.current_account_session is not None
        assert continuity.current_account_session.email == "test@example.com"

    def test_progress_update(self):
        """Test updating progress."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
        )
        
        continuity.completed_steps.append("step_1")
        continuity.current_step = "step_2"
        continuity.next_step = "step_3"
        continuity.progress_percentage = 50.0
        
        assert len(continuity.completed_steps) == 1
        assert continuity.completed_steps[0] == "step_1"
        assert continuity.current_step == "step_2"
        assert continuity.next_step == "step_3"
        assert continuity.progress_percentage == 50.0

    def test_evidence_refs(self):
        """Test evidence references."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
        )
        
        continuity.evidence_refs.append("evidence_1")
        continuity.evidence_refs.append("evidence_2")
        
        assert len(continuity.evidence_refs) == 2
        assert "evidence_1" in continuity.evidence_refs

    def test_decision_audit_trail_refs(self):
        """Test decision audit trail references."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
        )
        
        continuity.decision_audit_trail_refs.append("decision_1")
        
        assert len(continuity.decision_audit_trail_refs) == 1
        assert "decision_1" in continuity.decision_audit_trail_refs

    def test_blocked_reason(self):
        """Test blocked reason field."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
            blocked_reason="Quota exhausted",
        )
        
        assert continuity.blocked_reason == "Quota exhausted"

    def test_metadata(self):
        """Test metadata field for additional context."""
        continuity = OperationalContinuity(
            task_id=str(uuid4()),
            objective="Test objective",
            current_agent="test_agent",
        )
        
        continuity.metadata["custom_field"] = "custom_value"
        continuity.metadata["priority"] = "high"
        
        assert continuity.metadata["custom_field"] == "custom_value"
        assert continuity.metadata["priority"] == "high"


class TestContinuityState:
    """Test ContinuityState enum values."""

    def test_state_values(self):
        """Test all state values are defined."""
        assert ContinuityState.NOT_STARTED == "not_started"
        assert ContinuityState.IN_PROGRESS == "in_progress"
        assert ContinuityState.PAUSED == "paused"
        assert ContinuityState.AWAITING_ACCOUNT == "awaiting_account"
        assert ContinuityState.AWAITING_APPROVAL == "awaiting_approval"
        assert ContinuityState.COMPLETED == "completed"
        assert ContinuityState.FAILED == "failed"
        assert ContinuityState.TRANSFERRED == "transferred"


class TestAgentHandoff:
    """Test AgentHandoff model."""

    def test_handoff_creation(self):
        """Test creating an agent handoff record."""
        handoff = AgentHandoff(
            from_agent="agent_a",
            to_agent="agent_b",
            handoff_reason="quota_exhausted",
        )
        
        assert handoff.from_agent == "agent_a"
        assert handoff.to_agent == "agent_b"
        assert handoff.handoff_reason == "quota_exhausted"
        assert handoff.handoff_timestamp is not None
        assert handoff.context_snapshot == {}
        assert handoff.metadata == {}

    def test_handoff_with_context(self):
        """Test handoff with context snapshot."""
        context = {"last_action": "sent_message", "state": "waiting_response"}
        handoff = AgentHandoff(
            from_agent="agent_a",
            to_agent="agent_b",
            handoff_reason="quota_exhausted",
            context_snapshot=context,
        )
        
        assert handoff.context_snapshot == context


class TestAccountSession:
    """Test AccountSession model."""

    def test_session_creation(self):
        """Test creating an account session record."""
        session = AccountSession(
            email="test@example.com",
            browser="chrome",
            profile="default",
            tool="claude",
        )
        
        assert session.email == "test@example.com"
        assert session.browser == "chrome"
        assert session.profile == "default"
        assert session.tool == "claude"
        assert session.quota_used == 0
        assert session.success is False
        assert session.session_started_at is not None
        assert session.session_ended_at is None

    def test_session_with_quota(self):
        """Test session with quota usage."""
        session = AccountSession(
            email="test@example.com",
            browser="chrome",
            profile="default",
            tool="claude",
            quota_used=10,
            success=True,
            session_ended_at=datetime.now(timezone.utc),
        )
        
        assert session.quota_used == 10
        assert session.success is True
        assert session.session_ended_at is not None

    def test_session_failure(self):
        """Test session with failure reason."""
        session = AccountSession(
            email="test@example.com",
            browser="chrome",
            profile="default",
            tool="claude",
            success=False,
            failure_reason="Authentication failed",
        )
        
        assert session.success is False
        assert session.failure_reason == "Authentication failed"
        assert session.session_ended_at is None
