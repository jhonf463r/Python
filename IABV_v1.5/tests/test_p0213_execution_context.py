"""P0.213 Tests for ExecutionContext.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for thread-local execution context for envelope transport.
"""
import pytest
from iabv_v15.domain.execution_context import ExecutionContext
from iabv_v15.domain.models import PrivateInvocationEnvelope, CanonicalExecutionIdentity


class TestExecutionContext:
    """Test ExecutionContext thread-local storage."""

    def test_set_and_get_envelope(self):
        """Test A: set and get envelope."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        envelope = PrivateInvocationEnvelope(identity=identity)
        
        ExecutionContext.set_envelope(envelope)
        retrieved = ExecutionContext.get_envelope()
        
        assert retrieved is not None
        if retrieved:
            assert retrieved.get_invocation_id() == envelope.get_invocation_id()

    def test_get_envelope_when_not_set(self):
        """Test B: get envelope when not set returns None."""
        ExecutionContext.clear_envelope()
        retrieved = ExecutionContext.get_envelope()
        
        assert retrieved is None

    def test_clear_envelope(self):
        """Test C: clear envelope."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        envelope = PrivateInvocationEnvelope(identity=identity)
        
        ExecutionContext.set_envelope(envelope)
        assert ExecutionContext.get_envelope() is not None
        
        ExecutionContext.clear_envelope()
        assert ExecutionContext.get_envelope() is None

    def test_has_envelope(self):
        """Test D: has_envelope returns correct status."""
        ExecutionContext.clear_envelope()
        assert ExecutionContext.has_envelope() is False
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        envelope = PrivateInvocationEnvelope(identity=identity)
        
        ExecutionContext.set_envelope(envelope)
        assert ExecutionContext.has_envelope() is True
        
        ExecutionContext.clear_envelope()
        assert ExecutionContext.has_envelope() is False

    def test_thread_isolation(self):
        """Test E: thread isolation - different threads have different contexts."""
        import threading
        results = {}
        
        def thread1():
            identity = CanonicalExecutionIdentity(
                run_id="thread1_run_id",
                episode_id="thread1_episode_id",
                session_id="thread1_session_id"
            )
            envelope = PrivateInvocationEnvelope(identity=identity)
            ExecutionContext.set_envelope(envelope)
            results['thread1'] = ExecutionContext.get_envelope().get_invocation_id()
        
        def thread2():
            identity = CanonicalExecutionIdentity(
                run_id="thread2_run_id",
                episode_id="thread2_episode_id",
                session_id="thread2_session_id"
            )
            envelope = PrivateInvocationEnvelope(identity=identity)
            ExecutionContext.set_envelope(envelope)
            results['thread2'] = ExecutionContext.get_envelope().get_invocation_id()
        
        t1 = threading.Thread(target=thread1)
        t2 = threading.Thread(target=thread2)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        assert results['thread1'] != results['thread2']
