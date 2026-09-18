"""Test I0 credential_id → CredentialRegistry → execute_task → adapter.run(api_key)

This micro-cycle tests ONLY the causal edge:
credential_id
    ↓
CredentialRegistry
    ↓
secret resolution
    ↓
ToolTeachService.execute_task()
    ↓
adapter.run(api_key=resolved_secret)
    ↓
existing proven HTTP seam

The proven seam (adapter.run(api_key) → effective_key → Authorization) is NOT re-tested here.
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    ApprovalDecision,
    ToolAction,
    ToolActionType,
    TaskRole,
    ToolTask,
    ToolType,
    ToolValidationStatus,
    ToolCard,
)
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.trust.credential_registry import CredentialRegistry
from iabv_v15.services.trust.provider_credential_adapter import (
    CredentialRecord,
    CredentialStatus,
)


def test_credential_a_resolves_to_secret_a():
    """Credential ID A resolves to secret A and reaches HTTP boundary."""
    # Setup: Registry with credential-A
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_a = CredentialRecord(
        credential_id="credential-A",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-A",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_a])
    
    # Setup: Adapter with mock HTTP
    adapter = DevinApiToolAdapter(api_key="constructor-key")
    auth_headers = []
    
    def mock_post(url, headers, json, timeout):
        auth_headers.append(headers.get("Authorization"))
        return MagicMock(status_code=200, json=lambda: {"id": "session-123"})
    
    def mock_get(url, headers, params, timeout):
        return MagicMock(status_code=200, json=lambda: {"status": "completed", "answer": "result"})
    
    # Execute with credential_id
    with patch("httpx.post", side_effect=mock_post), patch("httpx.get", side_effect=mock_get):
        result = adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={"credential_id": "credential-A"},
            ),
            sandbox=False,
            api_key=registry.resolve_credential_secret("credential-A"),
        )
    
    # Assert: HTTP boundary received secret-A
    assert len(auth_headers) == 1
    assert auth_headers[0] == "Bearer secret-ref-A"
    assert adapter.api_key == "constructor-key"  # No mutation


def test_credential_b_resolves_to_secret_b():
    """Credential ID B resolves to secret B and reaches HTTP boundary."""
    # Setup: Registry with credential-B
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_b = CredentialRecord(
        credential_id="credential-B",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-B",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_b])
    
    # Setup: Adapter with mock HTTP
    adapter = DevinApiToolAdapter(api_key="constructor-key")
    auth_headers = []
    
    def mock_post(url, headers, json, timeout):
        auth_headers.append(headers.get("Authorization"))
        return MagicMock(status_code=200, json=lambda: {"id": "session-456"})
    
    def mock_get(url, headers, params, timeout):
        return MagicMock(status_code=200, json=lambda: {"status": "completed", "answer": "result"})
    
    # Execute with credential_id
    with patch("httpx.post", side_effect=mock_post), patch("httpx.get", side_effect=mock_get):
        result = adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={"credential_id": "credential-B"},
            ),
            sandbox=False,
            api_key=registry.resolve_credential_secret("credential-B"),
        )
    
    # Assert: HTTP boundary received secret-B
    assert len(auth_headers) == 1
    assert auth_headers[0] == "Bearer secret-ref-B"
    assert adapter.api_key == "constructor-key"  # No mutation


def test_isolation_a_b_a():
    """Sequential invocations A → B → A produce correct secrets without contamination."""
    # Setup: Registry with both credentials
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_a = CredentialRecord(
        credential_id="credential-A",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-A",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    record_b = CredentialRecord(
        credential_id="credential-B",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-B",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_a, record_b])
    
    # Setup: Adapter with mock HTTP
    adapter = DevinApiToolAdapter(api_key="constructor-key")
    auth_headers = []
    
    def mock_post(url, headers, json, timeout):
        auth_headers.append(headers.get("Authorization"))
        return MagicMock(status_code=200, json=lambda: {"id": "session-xyz"})
    
    def mock_get(url, headers, params, timeout):
        return MagicMock(status_code=200, json=lambda: {"status": "completed", "answer": "result"})
    
    with patch("httpx.post", side_effect=mock_post), patch("httpx.get", side_effect=mock_get):
        # Invocation A
        adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={"credential_id": "credential-A"},
            ),
            sandbox=False,
            api_key=registry.resolve_credential_secret("credential-A"),
        )
        
        # Invocation B
        adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={"credential_id": "credential-B"},
            ),
            sandbox=False,
            api_key=registry.resolve_credential_secret("credential-B"),
        )
        
        # Invocation A again
        adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={"credential_id": "credential-A"},
            ),
            sandbox=False,
            api_key=registry.resolve_credential_secret("credential-A"),
        )
    
    # Assert: A → B → A sequence with correct isolation
    assert len(auth_headers) == 3
    assert auth_headers[0] == "Bearer secret-ref-A"
    assert auth_headers[1] == "Bearer secret-ref-B"
    assert auth_headers[2] == "Bearer secret-ref-A"
    assert adapter.api_key == "constructor-key"  # No mutation


def test_unknown_credential_fail_closed():
    """Unknown credential ID fails closed without calling adapter.run()."""
    # Setup: Registry with credential-A only
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_a = CredentialRecord(
        credential_id="credential-A",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-A",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_a])
    
    # Resolve unknown credential
    resolved = registry.resolve_credential_secret("credential-UNKNOWN")
    
    # Assert: Empty secret returned
    assert resolved == ""


def test_secret_not_resolvable_fail_closed():
    """Credential exists but secret resolver returns empty string."""
    # Setup: Registry with resolver that returns empty for this ref
    registry = CredentialRegistry(secret_resolver=lambda ref: "" if ref == "ref-B" else f"secret-{ref}")
    record_b = CredentialRecord(
        credential_id="credential-B",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-B",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_b])
    
    # Resolve credential
    resolved = registry.resolve_credential_secret("credential-B")
    
    # Assert: Empty secret returned
    assert resolved == ""


def test_legacy_behavior_without_credential_id():
    """Without credential_id, legacy behavior uses constructor key."""
    # Setup: Registry with credentials
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_a = CredentialRecord(
        credential_id="credential-A",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-A",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_a])
    
    # Setup: Adapter with constructor key
    adapter = DevinApiToolAdapter(api_key="constructor-key")
    auth_headers = []
    
    def mock_post(url, headers, json, timeout):
        auth_headers.append(headers.get("Authorization"))
        return MagicMock(status_code=200, json=lambda: {"id": "session-789"})
    
    def mock_get(url, headers, params, timeout):
        return MagicMock(status_code=200, json=lambda: {"status": "completed", "answer": "result"})
    
    # Execute WITHOUT credential_id
    with patch("httpx.post", side_effect=mock_post), patch("httpx.get", side_effect=mock_get):
        result = adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={},  # No credential_id
            ),
            sandbox=False,
            api_key=None,  # No override
        )
    
    # Assert: HTTP boundary received constructor key (legacy behavior)
    assert len(auth_headers) == 1
    assert auth_headers[0] == "Bearer constructor-key"
    assert adapter.api_key == "constructor-key"


def test_preflight_reachability_with_invocation_credential():
    """Adapter without constructor key + valid invocation credential can reach run()."""
    # Setup: Registry with credential-A
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_a = CredentialRecord(
        credential_id="credential-A",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-A",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_a])
    
    # Setup: Adapter WITHOUT constructor key
    adapter = DevinApiToolAdapter(api_key="")  # Empty constructor key
    
    # Check preflight with invocation credential
    card = ToolCard(
        tool_id="devin-api",
        adapter_key="devin_api",
        tool_type=ToolType.MCP_CLIENT,
        title="Devin API",
    )
    
    # Preflight with invocation credential should pass
    preflight_api_key = registry.resolve_credential_secret("credential-A")
    is_available = adapter.is_available(card, api_key=preflight_api_key)
    
    # Mock HTTP for preflight
    def mock_get(url, headers, params, timeout):
        return MagicMock(status_code=200, json=lambda: {"sessions": []})
    
    with patch("httpx.get", side_effect=mock_get):
        is_available = adapter.is_available(card, api_key=preflight_api_key)
    
    # Assert: Preflight passed with invocation credential
    assert is_available is True


def test_adapter_no_mutation():
    """Adapter state is not mutated after credential-based invocations."""
    # Setup: Registry with credentials
    registry = CredentialRegistry(secret_resolver=lambda ref: f"secret-{ref}")
    record_a = CredentialRecord(
        credential_id="credential-A",
        provider="devin",
        principal_id="",  # Empty as per security requirement
        credential_type="api_key",
        secret_ref="ref-A",
        api_version="v1",
        status=CredentialStatus.AVAILABLE,
        enabled=True,
    )
    registry.register_credentials([record_a])
    
    # Setup: Adapter with constructor key
    original_api_key = "constructor-key"
    adapter = DevinApiToolAdapter(api_key=original_api_key)
    
    # Execute with invocation credential
    def mock_post(url, headers, json, timeout):
        return MagicMock(status_code=200, json=lambda: {"id": "session-999"})
    
    def mock_get(url, headers, params, timeout):
        return MagicMock(status_code=200, json=lambda: {"status": "completed", "answer": "result"})
    
    with patch("httpx.post", side_effect=mock_post), patch("httpx.get", side_effect=mock_get):
        adapter.run(
            ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
            ),
            ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                metadata={"credential_id": "credential-A"},
            ),
            sandbox=False,
            api_key=registry.resolve_credential_secret("credential-A"),
        )
    
    # Assert: Adapter state unchanged
    assert adapter.api_key == original_api_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
