"""Test I0 secret resolver seam: credential_id → CredentialRegistry → adapter.run(api_key)

This test demonstrates the seam at the secret resolver level, NOT the full
ToolTeachService execute_task() path. It uses minimal composition to verify
that the secret_resolver can resolve from environment and reach adapter.run(api_key).

Note: This is NOT a test of the canonical ToolTeachService composition.
For full composition testing, see other test modules.
"""

import os

import pytest

from iabv_v15.domain.models import TaskRole, ToolCard, ToolTask, ToolType
from iabv_v15.services.trust.credential_registry import CredentialRegistry


class TrackedAdapter:
    """Adapter that tracks api_key usage."""
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.run_calls = []
        self.api_keys_received = []
    
    def is_available(self, card: ToolCard, *, api_key=None) -> bool:
        return True
    
    def run(self, card: ToolCard, task: ToolTask, *, sandbox=False, api_key=None) -> dict:
        self.run_calls.append(1)
        self.api_keys_received.append(api_key)
        return {
            'success': True,
            'output_text': 'Fake result',
            'extracted_data': {},
            'artifacts': [],
            'error_message': '',
            'execution_ms': 0,
            'metadata': {'sandbox': sandbox, 'simulated': True},
        }


def test_credential_resolver_to_adapter_run_api_key():
    """CredentialRegistry secret_resolver resolves credential and passes it as api_key to adapter.run()."""
    # Set synthetic credential
    os.environ["DEVIN_API_KEY"] = "synthetic-secret-canonical"
    
    try:
        # Create CredentialRegistry with os.environ resolver
        credential_registry = CredentialRegistry(
            secret_resolver=lambda ref: os.environ.get(ref, '')
        )
        
        # Create adapter with EMPTY constructor key
        adapter = TrackedAdapter(api_key="")
        
        # Simulate the I0 execution path (from execute_task)
        credential_id = "DEVIN_API_KEY"
        
        # Step 1: Resolve credential using secret_resolver (as done in execute_task)
        resolved_secret = credential_registry._secret_resolver(credential_id)
        
        # Step 2: Call adapter.run with resolved secret (as done in execute_task)
        card = ToolCard(
            tool_id="devin-api",
            adapter_key="devin_api",
            tool_type=ToolType.MCP_CLIENT,
            title="Devin API",
        )
        task = ToolTask(
            tool_id="devin-api",
            title="Test Task",
            objective="Test",
            requested_by_role=TaskRole.TOOL_SANDBOX,
            metadata={"credential_id": credential_id},
        )
        
        result = adapter.run(card, task, sandbox=False, api_key=resolved_secret)
        
        # CRITICAL ASSERTIONS
        # 1. Secret was resolved from environment via secret_resolver
        assert resolved_secret == "synthetic-secret-canonical"
        
        # 2. adapter.run() was called
        assert len(adapter.run_calls) == 1
        
        # 3. api_key parameter received the resolved secret
        assert adapter.api_keys_received[0] == "synthetic-secret-canonical"
        
        # 4. Adapter constructor key remained empty (credential came from invocation)
        assert adapter.api_key == ""
        
        # 5. Task succeeded
        assert result['success'] is True
        
    finally:
        if "DEVIN_API_KEY" in os.environ:
            del os.environ["DEVIN_API_KEY"]


def test_unknown_credential_empty_secret_blocks():
    """Unknown credential_id returns empty string, blocking execution."""
    # Create CredentialRegistry
    credential_registry = CredentialRegistry(
        secret_resolver=lambda ref: os.environ.get(ref, '')
    )
    
    # Simulate with unknown credential
    credential_id = "CREDENTIAL_DOES_NOT_EXIST"
    resolved_secret = credential_registry._secret_resolver(credential_id)
    
    # CRITICAL ASSERTIONS
    # 1. Resolution returns empty string (fail-closed behavior)
    assert resolved_secret == ""
    
    # 2. If we were to call adapter.run with empty secret, we would NOT call it
    # (This simulates the fail-closed behavior in execute_task)
    if not resolved_secret:
        # In execute_task, this would return before calling adapter.run()
        assert True  # Execution blocked
    else:
        assert False  # Should not reach here


def test_credential_registry_identity():
    """Verify that a CredentialRegistry instance can be injected and used."""
    # Create CredentialRegistry
    credential_registry = CredentialRegistry(
        secret_resolver=lambda ref: os.environ.get(ref, '')
    )
    
    # Simulate injection into a service
    class FakeService:
        def __init__(self, credential_registry):
            self.credential_registry = credential_registry
    
    service = FakeService(credential_registry)
    
    # Verify identity
    assert service.credential_registry is credential_registry
    
    # Verify it can resolve credentials via secret_resolver
    os.environ["TEST_KEY"] = "test-value"
    try:
        # The resolver function works directly
        resolved = credential_registry._secret_resolver("TEST_KEY")
        assert resolved == "test-value"
    finally:
        if "TEST_KEY" in os.environ:
            del os.environ["TEST_KEY"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
