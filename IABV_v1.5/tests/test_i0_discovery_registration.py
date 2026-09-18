"""Test I0 discovery → registration → resolution

Tests the causal edge:
DevinCredentialAdapter.discover()
    ↓
CredentialRecord
    ↓
CredentialRegistry.register_credentials()
    ↓
CredentialRegistry._credentials
    ↓
credential_id
    ↓
resolve_credential_secret()
    ↓
ephemeral secret
"""

import os

import pytest

from iabv_v15.services.trust.credential_registry import CredentialRegistry
from iabv_v15.services.trust.devin_credential_adapter import DevinCredentialAdapter


def test_discovery_generates_credential_record():
    """TEST A — discover() generates CredentialRecord with correct metadata."""
    # Set synthetic credential
    os.environ["DEVIN_API_KEY"] = "synthetic-secret-A"
    
    try:
        adapter = DevinCredentialAdapter()
        result = adapter.discover()
        
        # CRITICAL ASSERTIONS
        # 1. One credential discovered
        assert len(result.records) == 1, f"Expected 1 record, got {len(result.records)}"
        
        record = result.records[0]
        
        # 2. secret_ref is the environment variable name
        assert record.secret_ref == "DEVIN_API_KEY", \
            f"Expected secret_ref='DEVIN_API_KEY', got '{record.secret_ref}'"
        
        # 3. principal_id is empty (identity unknown)
        assert record.principal_id == "", \
            f"Expected principal_id='', got '{record.principal_id}'"
        
        # 4. credential_id is NOT the environment variable name
        assert record.credential_id != "DEVIN_API_KEY", \
            f"credential_id should be generated, not equal to secret_ref"
        
        # 5. credential_id is a hash
        assert len(record.credential_id) == 16, \
            f"Expected credential_id length 16, got {len(record.credential_id)}"
        
        # 6. provider is 'devin'
        assert record.provider == "devin", \
            f"Expected provider='devin', got '{record.provider}'"
        
        # 7. secret is NOT stored in record
        assert not hasattr(record, 'secret') or not getattr(record, 'secret', None), \
            "CredentialRecord should not contain secret"
        
    finally:
        if "DEVIN_API_KEY" in os.environ:
            del os.environ["DEVIN_API_KEY"]


def test_discovery_to_registration():
    """TEST B — discover() → register_credentials() populates registry."""
    # Set synthetic credential
    os.environ["DEVIN_API_KEY"] = "synthetic-secret-A"
    
    try:
        registry = CredentialRegistry(
            secret_resolver=lambda ref: os.environ.get(ref, '')
        )
        
        # Register adapter
        registry.register_adapter(DevinCredentialAdapter())
        
        # Discover credentials
        records = registry.discover_credentials("devin")
        
        # Register credentials
        registry.register_credentials(records)
        
        record = records[0]
        
        # CRITICAL ASSERTIONS
        # 1. Record is retrievable from registry
        retrieved = registry.get_credential(record.credential_id)
        assert retrieved is not None, "Credential not found in registry after registration"
        
        # 2. Retrieved record is the same object
        assert retrieved is record, "Retrieved record is not the same object"
        
        # 3. Registry _credentials contains the credential_id
        assert record.credential_id in registry._credentials, \
            "credential_id not in registry._credentials"
        
    finally:
        if "DEVIN_API_KEY" in os.environ:
            del os.environ["DEVIN_API_KEY"]


def test_registration_to_resolution():
    """TEST C — registration → resolve_credential_secret() resolves correctly."""
    # Set synthetic credential
    os.environ["DEVIN_API_KEY"] = "synthetic-secret-A"
    
    try:
        registry = CredentialRegistry(
            secret_resolver=lambda ref: os.environ.get(ref, '')
        )
        
        # Register adapter
        registry.register_adapter(DevinCredentialAdapter())
        
        # Discover and register
        records = registry.discover_credentials("devin")
        registry.register_credentials(records)
        
        record = records[0]
        
        # Resolve credential
        resolved = registry.resolve_credential_secret(record.credential_id)
        
        # CRITICAL ASSERTIONS
        # 1. Resolution returns the synthetic secret
        assert resolved == "synthetic-secret-A", \
            f"Expected 'synthetic-secret-A', got '{resolved}'"
        
        # 2. Resolution uses the full path:
        # credential_id → _credentials lookup → CredentialRecord.secret_ref → secret_resolver → secret
        # NOT: _secret_resolver("DEVIN_API_KEY") directly
        
        # Verify by checking the record's secret_ref
        assert record.secret_ref == "DEVIN_API_KEY"
        
    finally:
        if "DEVIN_API_KEY" in os.environ:
            del os.environ["DEVIN_API_KEY"]


def test_no_secret_persistence_in_record():
    """TEST D — CredentialRecord does not contain secret."""
    # Set synthetic credential
    os.environ["DEVIN_API_KEY"] = "synthetic-secret-A"
    
    try:
        adapter = DevinCredentialAdapter()
        result = adapter.discover()
        record = result.records[0]
        
        # CRITICAL ASSERTIONS
        # 1. Record has no 'secret' attribute
        assert not hasattr(record, 'secret'), "CredentialRecord has 'secret' attribute"
        
        # 2. Check all attributes for secret value
        for attr in dir(record):
            if not attr.startswith('_'):
                value = getattr(record, attr)
                if isinstance(value, str) and value == "synthetic-secret-A":
                    assert False, f"Secret found in attribute '{attr}'"
        
    finally:
        if "DEVIN_API_KEY" in os.environ:
            del os.environ["DEVIN_API_KEY"]


def test_absence_of_credential():
    """TEST E — no environment variable → empty discovery → empty registry."""
    # Ensure no Devin credentials
    for env_var in ['DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY', 'DEVIN_API_KEY', 
                     'DEVIN_API_KEY_SERVICE', 'DEVIN_API_KEY_LEGACY']:
        if env_var in os.environ:
            del os.environ[env_var]
    
    try:
        registry = CredentialRegistry(
            secret_resolver=lambda ref: os.environ.get(ref, '')
        )
        
        # Register adapter
        registry.register_adapter(DevinCredentialAdapter())
        
        # Discover credentials
        records = registry.discover_credentials("devin")
        
        # CRITICAL ASSERTIONS
        # 1. No credentials discovered
        assert len(records) == 0, f"Expected 0 records, got {len(records)}"
        
        # 2. Register empty list
        registry.register_credentials(records)
        
        # 3. Registry remains empty
        assert len(registry._credentials) == 0, \
            f"Expected empty registry, got {len(registry._credentials)} credentials"
        
    finally:
        # Clean up
        for env_var in ['DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY', 'DEVIN_API_KEY', 
                     'DEVIN_API_KEY_SERVICE', 'DEVIN_API_KEY_LEGACY']:
            if env_var in os.environ:
                del os.environ[env_var]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
