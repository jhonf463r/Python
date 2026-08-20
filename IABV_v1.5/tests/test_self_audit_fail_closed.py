"""Tests for SelfAudit Fail-Closed (PHASE 8).

These tests verify that SelfAuditService rejects invalid identity
with fail-closed behavior (no fallback to None).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from iabv_v15.domain.models import SelfAuditSnapshot
from iabv_v15.services.evolution.self_audit_service import SelfAuditService


class TestSelfAuditFailClosed:
    """Tests for SelfAudit fail-closed behavior."""
    
    def test_accept_valid_canonical_identity(self):
        """Test that valid canonical identity is accepted."""
        # Create mock services
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Valid canonical identity
        canonical_identity = {
            'execution_id': 'test-exec-id',
            'run_id': 'test-run-id',
            'invocation_id': 'test-invocation-id',
            'runtime_generation': 0,
            'signature': '0' * 64,  # Valid signature length
        }
        
        # Should not raise
        snapshot = self_audit_service.run(
            reason="test",
            canonical_identity=canonical_identity,
        )
        
        # Snapshot should include canonical_identity
        assert snapshot.canonical_identity == canonical_identity
    
    def test_reject_invalid_canonical_identity_not_dict(self):
        """Test that non-dict canonical_identity is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (not a dict)
        canonical_identity = "invalid"
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="canonical_identity must be a dict"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_reject_missing_execution_id(self):
        """Test that missing execution_id is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (missing execution_id)
        canonical_identity = {
            'run_id': 'test-run-id',
            'invocation_id': 'test-invocation-id',
            'runtime_generation': 0,
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Missing required field"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_reject_missing_run_id(self):
        """Test that missing run_id is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (missing run_id)
        canonical_identity = {
            'execution_id': 'test-exec-id',
            'invocation_id': 'test-invocation-id',
            'runtime_generation': 0,
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Missing required field"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_reject_missing_invocation_id(self):
        """Test that missing invocation_id is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (missing invocation_id)
        canonical_identity = {
            'execution_id': 'test-exec-id',
            'run_id': 'test-run-id',
            'runtime_generation': 0,
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Missing required field"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_reject_missing_runtime_generation(self):
        """Test that missing runtime_generation is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (missing runtime_generation)
        canonical_identity = {
            'execution_id': 'test-exec-id',
            'run_id': 'test-run-id',
            'invocation_id': 'test-invocation-id',
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Missing required field"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_reject_invalid_signature_length(self):
        """Test that invalid signature length is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (wrong signature length)
        canonical_identity = {
            'execution_id': 'test-exec-id',
            'run_id': 'test-run-id',
            'invocation_id': 'test-invocation-id',
            'runtime_generation': 0,
            'signature': '0' * 10,  # Wrong length
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid signature"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_reject_invalid_signature_type(self):
        """Test that invalid signature type is rejected."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity (wrong signature type)
        canonical_identity = {
            'execution_id': 'test-exec-id',
            'run_id': 'test-run-id',
            'invocation_id': 'test-invocation-id',
            'runtime_generation': 0,
            'signature': 123,  # Not a string
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid signature"):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_accept_none_canonical_identity(self):
        """Test that None canonical_identity is accepted (backward compatibility)."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # None canonical_identity (backward compatibility)
        snapshot = self_audit_service.run(reason="test", canonical_identity=None)
        
        # Snapshot should have None canonical_identity
        assert snapshot.canonical_identity is None
    
    def test_no_canonical_identity_default(self):
        """Test that no canonical_identity defaults to None."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # No canonical_identity parameter
        snapshot = self_audit_service.run(reason="test")
        
        # Snapshot should have None canonical_identity
        assert snapshot.canonical_identity is None


class TestSelfAuditFailClosedSecurity:
    """Security tests for SelfAudit fail-closed behavior."""
    
    def test_no_fallback_to_none_on_invalid(self):
        """Test that invalid identity does not fallback to None."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity
        canonical_identity = "invalid"
        
        # Should raise, not fallback to None
        with pytest.raises(ValueError):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
    
    def test_no_warning_on_invalid(self):
        """Test that invalid identity raises error, not warning."""
        tool_registry = type('MockToolRegistry', (), {
            'list_cards': lambda: [],
            'refresh_card': lambda x: x,
        })()
        
        self_audit_service = SelfAuditService(
            tool_registry=tool_registry,
            environment_self_model_provider=lambda: None,
            world_model_service=None,
            operational_self_examination_service=None,
            portable_context_service=None,
            workspace_root=".",
        )
        
        # Invalid canonical identity
        canonical_identity = "invalid"
        
        # Should raise ValueError, not log warning
        with pytest.raises(ValueError):
            self_audit_service.run(
                reason="test",
                canonical_identity=canonical_identity,
            )
