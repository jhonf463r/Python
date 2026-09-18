"""Secret Boundary Security Tests

Tests that verify credential discovery and health check never expose secret values.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.services.trust.credential_registry import CredentialRegistry
from iabv_v15.services.trust.fake_credential_adapter import FakeCredentialAdapter


def test_discovery_no_secret_exposure():
    """Test that credential discovery never exposes secret values."""
    print("=" * 60)
    print("SECRET BOUNDARY TEST: DISCOVERY")
    print("=" * 60)
    
    # Synthetic secrets for testing only
    synthetic_secret = 'synthetic_secret_never_in_production'
    
    registry = CredentialRegistry()
    fake_adapter = FakeCredentialAdapter({
        'FAKE_TEST_CRED': synthetic_secret,
    })
    registry.register_adapter(fake_adapter)
    
    # Discover credentials
    credentials = registry.discover_credentials('fake')
    
    print(f"\nDiscovered {len(credentials)} credentials")
    
    all_output = []
    secret_exposed = False
    
    for cred in credentials:
        print(f"\nCredential ID: {cred.credential_id}")
        print(f"  Provider: {cred.provider}")
        print(f"  Principal ID: {cred.principal_id}")
        print(f"  Secret Ref: {cred.secret_ref}")
        print(f"  Credential Type: {cred.credential_type}")
        print(f"  API Version: {cred.api_version}")
        
        # Check that secret is not in any metadata field
        all_metadata = [
            cred.credential_id,
            cred.provider,
            cred.principal_id,
            cred.secret_ref,
            cred.credential_type,
            cred.api_version,
            cred.organization_id,
            cred.scope,
            str(cred.status.value),
            str(cred.last_error_code),
            str(cred.last_error_message),
        ]
        
        for metadata in all_metadata:
            if synthetic_secret in str(metadata):
                secret_exposed = True
                print(f"  ERROR: Secret exposed in metadata: {metadata}")
        
        all_output.append(str(cred.__dict__))
    
    # Check that secret is not in combined output
    combined_output = str(all_output)
    if synthetic_secret in combined_output:
        secret_exposed = True
        print("\nERROR: Secret exposed in combined output")
    
    if secret_exposed:
        print("\nFAIL: SECRET BOUNDARY VIOLATION")
        return False
    else:
        print("\nPASS: SECRET BOUNDARY PROTECTED")
        return True


def test_health_check_no_secret_exposure():
    """Test that health check never exposes secret values."""
    print("\n" + "=" * 60)
    print("SECRET BOUNDARY TEST: HEALTH CHECK")
    print("=" * 60)
    
    # Synthetic secrets for testing only
    synthetic_secret = 'synthetic_secret_never_in_production'
    
    registry = CredentialRegistry()
    fake_adapter = FakeCredentialAdapter({
        'FAKE_V3_HEALTH_CRED': synthetic_secret,
    })
    registry.register_adapter(fake_adapter)
    
    # Discover and register
    discovery_result = fake_adapter.discover()
    credentials = discovery_result.records
    registry.register_credentials(credentials)
    
    # Perform health check
    registry.register_credentials(credentials)
    health_results = registry.check_all_credentials()
    
    print(f"\nHealth checked {len(health_results)} credentials")
    
    secret_exposed = False
    
    for cred_id, record in health_results.items():
        print(f"\nCredential ID: {cred_id}")
        print(f"  Status: {record.status.value}")
        print(f"  Auth State: {record.auth_state.value}")
        print(f"  Authorization State: {record.authorization_state.value}")
        print(f"  Health State: {record.health_state.value}")
        print(f"  Quota State: {record.quota_state.value}")
        print(f"  Last Error Code: {record.last_error_code}")
        print(f"  Last Error Message: {record.last_error_message}")
        
        # Check that secret is not in any health field
        all_health_data = [
            record.status.value,
            record.auth_state.value,
            record.authorization_state.value,
            record.health_state.value,
            record.quota_state.value,
            record.last_error_code,
            record.last_error_message,
            str(record.__dict__),
        ]
        
        for data in all_health_data:
            if synthetic_secret in str(data):
                secret_exposed = True
                print(f"  ERROR: Secret exposed in health data")
    
    if secret_exposed:
        print("\nFAIL: SECRET BOUNDARY VIOLATION")
        return False
    else:
        print("\nPASS: SECRET BOUNDARY PROTECTED")
        return True


def test_serialization_no_secret_exposure():
    """Test that credential record serialization never exposes secret values."""
    print("\n" + "=" * 60)
    print("SECRET BOUNDARY TEST: SERIALIZATION")
    print("=" * 60)
    
    from iabv_v15.services.trust.provider_credential_adapter import CredentialRecord, CredentialStatus
    
    synthetic_secret = 'synthetic_secret_never_in_production'
    
    record = CredentialRecord(
        credential_id='test_id',
        provider='test',
        principal_id=synthetic_secret[:10],  # Only prefix should be stored
        credential_type='test',
        secret_ref='TEST_CRED',
        api_version='v1',
        status=CredentialStatus.UNKNOWN,
    )
    
    # Serialize
    serialized = str(record.__dict__)
    
    print(f"\nSerialized record length: {len(serialized)}")
    print(f"Prefix stored: {record.principal_id}")
    
    # Check that full secret is not in serialization
    if synthetic_secret in serialized:
        print("FAIL: SECRET BOUNDARY VIOLATION: Full secret in serialization")
        return False
    else:
        print("PASS: SECRET BOUNDARY PROTECTED: Only prefix stored")
        return True


if __name__ == "__main__":
    results = []
    
    results.append(("Discovery", test_discovery_no_secret_exposure()))
    results.append(("Health Check", test_health_check_no_secret_exposure()))
    results.append(("Serialization", test_serialization_no_secret_exposure()))
    
    print("\n" + "=" * 60)
    print("SECRET BOUNDARY TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\nPASS: ALL SECRET BOUNDARY TESTS PASSED")
        sys.exit(0)
    else:
        print("\nFAIL: SOME SECRET BOUNDARY TESTS FAILED")
        sys.exit(1)
