"""P0.213: Execution context for transporting PrivateInvocationEnvelope.

DESIGN_RECONSTRUCTION: This module is a new implementation reconstructed from
experimental design evidence. It is NOT recovered historical code.

Purpose: Provide thread-local storage for PrivateInvocationEnvelope,
allowing it to be transported from the execution flow to MCP tools without
modifying the public MCP contract.

Contract Requirements:
- Thread-local storage for envelope transport
- Context manager is OPTIONAL (THEORETICAL_RISK)
- Manual clear_envelope() method is sufficient for current requirements
- No complex cleanup without evidence of lifecycle problem
"""
from __future__ import annotations

import threading
from typing import Any

from iabv_v15.domain.models import PrivateInvocationEnvelope


class ExecutionContext:
    """Thread-local storage for PrivateInvocationEnvelope.

    This allows the envelope to be transported from the execution flow
    to MCP tools without modifying the public MCP contract.

    The envelope is stored in thread-local storage, so concurrent
    executions are isolated (no context bleed).

    Contract Compliance:
    - Thread-local storage for envelope transport
    - Manual clear_envelope() method for cleanup
    - Context manager is optional (THEORETICAL_RISK)
    """
    _storage = threading.local()

    @classmethod
    def set_envelope(cls, envelope: PrivateInvocationEnvelope) -> None:
        """Set the envelope for the current thread.

        Args:
            envelope: The PrivateInvocationEnvelope to store
        """
        cls._storage.envelope = envelope

    @classmethod
    def get_envelope(cls) -> PrivateInvocationEnvelope | None:
        """Get the envelope for the current thread.

        Returns:
            The PrivateInvocationEnvelope for the current thread, or None if not set
        """
        return getattr(cls._storage, 'envelope', None)

    @classmethod
    def clear_envelope(cls) -> None:
        """Clear the envelope for the current thread.

        This provides manual cleanup for the envelope context.
        """
        cls._storage.envelope = None

    @classmethod
    def has_envelope(cls) -> bool:
        """Check if an envelope is set for the current thread.

        Returns:
            True if an envelope is set, False otherwise
        """
        return hasattr(cls._storage, 'envelope') and cls._storage.envelope is not None
