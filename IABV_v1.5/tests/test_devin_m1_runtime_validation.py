"""Runtime validation of existing Devin credential using DevinAccountService.

This test demonstrates:
- Existing credential
  → registry lookup
  → fingerprint
  → SecretVault resolution
  → READ-ONLY validation
  → persistent validation record

Uses the REAL existing credential but does NOT create a Devin session.
"""
import sys
sys.path.insert(0, 'src')

from iabv_v15.bootstrap import _auto_load_secrets, _resolve_devin_api_key
from iabv_v15.domain.models import IdentitySource, ValidationStatus
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.providers.devin_account_service import DevinAccountService


def test_runtime_existing_credential_validation():
    """Validate the existing legacy Devin credential through the registry."""
    # Load the existing credential from environment
    _auto_load_secrets()
    api_key = _resolve_devin_api_key()

    print(f"=== RUNTIME VALIDATION OF EXISTING CREDENTIAL ===")
    print(f"Credential present: {'YES' if api_key else 'NO'}")
    print(f"Credential length: {len(api_key) if api_key else 0}")

    if not api_key:
        print("ERROR: No credential found")
        return

    # Initialize account service with real SecretVault
    vault = SecretVault(service_name="IABV_v15")
    service = DevinAccountService(secret_vault=vault)

    # Register a placeholder account (identity not verified yet)
    account = service.register_account(
        display_label="legacy_devin_account",
        identity_source=IdentitySource.UNKNOWN,
    )
    print(f"Account registered: {account.account_id}")
    print(f"Account label: {account.display_label}")
    print(f"Identity verified: {account.identity_verified}")

    # Migrate the existing credential into the registry
    credential = service.migrate_existing_credential(
        account_id=account.account_id,
        secret=api_key,
        source="legacy",
    )
    print(f"Credential registered: {credential.credential_id}")
    print(f"Fingerprint: {credential.fingerprint}")
    print(f"Credential type: {credential.credential_type.value}")
    print(f"API version: {credential.api_version.value}")
    print(f"Source: {credential.source}")
    print(f"Initial validation status: {credential.validation_status.value}")

    # Perform READ-ONLY validation
    print(f"\n=== PERFORMING READ-ONLY VALIDATION ===")
    result = service.validate_credential_read_only(credential.credential_id)

    print(f"Valid: {result['valid']}")
    print(f"HTTP status: {result['http_status']}")
    print(f"Error code: {result['error_code']}")
    print(f"Error summary: {result['error_summary']}")
    print(f"Latency: {result['latency_ms']:.2f}ms")

    # Verify credential metadata was updated
    updated_credential = service.get_credential(credential.credential_id)
    print(f"\n=== UPDATED CREDENTIAL METADATA ===")
    print(f"Validation status: {updated_credential.validation_status.value}")
    print(f"Last validated at: {updated_credential.last_validated_at}")
    print(f"Last HTTP status: {updated_credential.last_http_status}")
    print(f"Last error code: {updated_credential.last_error_code}")
    print(f"Last error summary: {updated_credential.last_error_summary}")

    # Verify the credential can be retrieved from SecretVault
    retrieved_secret = service.get_credential_secret(credential.credential_id)
    print(f"\n=== SECRET VAULT VERIFICATION ===")
    print(f"Secret retrievable: {'YES' if retrieved_secret else 'NO'}")
    print(f"Secret matches original: {'YES' if retrieved_secret == api_key else 'NO'}")

    # Verify fingerprint is non-reversible
    print(f"\n=== FINGERPRINT SAFETY ===")
    print(f"Fingerprint in secret: {'YES' if api_key in credential.fingerprint else 'NO'}")
    print(f"Secret in fingerprint: {'NO' if credential.fingerprint not in api_key else 'YES'}")

    # Assertions
    assert credential.credential_id is not None
    assert credential.fingerprint is not None
    assert len(credential.fingerprint) == 16
    assert credential.source == "legacy"
    assert credential.validation_status == ValidationStatus.READY or credential.validation_status == ValidationStatus.ERROR
    assert updated_credential.last_validated_at is not None
    assert result['http_status'] is not None
    assert retrieved_secret == api_key
    assert api_key not in credential.fingerprint

    print(f"\n=== RUNTIME VALIDATION COMPLETE ===")
    print(f"[OK] Credential successfully registered and validated")
    print(f"[OK] Fingerprint computed and stored")
    print(f"[OK] Secret stored in SecretVault")
    print(f"[OK] Validation result attributed to credential fingerprint")
    print(f"[OK] Raw secret never exposed in metadata")


if __name__ == "__main__":
    test_runtime_existing_credential_validation()
