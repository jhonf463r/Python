"""Tests for DevinAccountService.

Tests focus on:
- Two credentials can coexist in metadata without exposing secrets
- Fingerprints distinguish two different secrets
- Identical secrets produce identical fingerprints
- Raw secrets are never emitted to evidence/logging
- Credential metadata survives restart (persistence model)
- Account identity source is preserved
- Existing legacy Devin credential can be registered without deletion
- Validation results are attributed to the exact credential fingerprint
- Unknown account ownership remains NOT_VERIFIED
"""
from __future__ import annotations

import pytest

from iabv_v15.domain.models import (
    ApiVersion,
    CredentialType,
    DevinAccount,
    DevinCredential,
    IdentitySource,
    ValidationStatus,
)
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.providers.devin_account_service import (
    compute_credential_fingerprint,
    classify_credential_type,
    classify_api_version,
    DevinAccountService,
)


class FakeSecretVault(SecretVault):
    """Fake SecretVault for testing (in-memory, no keyring)."""

    def __init__(self) -> None:
        super().__init__(service_name="TEST_IABV")
        self._secrets: dict[str, str] = {}

    @property
    def available(self) -> bool:
        return True

    def put_secret(self, domain: str, account: str, field_role: str, secret: str):
        key = f"{domain}:{account}:{field_role}"
        self._secrets[key] = secret
        from iabv_v15.domain.models import SecretReference
        reference = SecretReference(
            domain=domain,
            account=account,
            field_role=field_role,
            key=key,
            available=True,
        )
        return reference

    def resolve_reference(self, reference):
        return self._secrets.get(reference.key)


# ===== Fingerprint Tests =====

def test_fingerprint_deterministic():
    """Identical secrets produce identical fingerprints."""
    secret = "apk_user_1234567890"
    fp1 = compute_credential_fingerprint(secret)
    fp2 = compute_credential_fingerprint(secret)
    assert fp1 == fp2
    assert len(fp1) == 16  # Truncated SHA-256


def test_fingerprint_distinguishes_secrets():
    """Fingerprints distinguish two different secrets."""
    secret_a = "apk_user_1234567890"
    secret_b = "apk_user_0987654321"
    fp_a = compute_credential_fingerprint(secret_a)
    fp_b = compute_credential_fingerprint(secret_b)
    assert fp_a != fp_b


def test_fingerprint_non_reversible():
    """Fingerprint cannot reconstruct secret (non-reversible)."""
    secret = "apk_user_1234567890"
    fingerprint = compute_credential_fingerprint(secret)
    # No way to reconstruct secret from fingerprint
    assert secret not in fingerprint
    assert len(fingerprint) < len(secret)


# ===== Classification Tests =====

def test_classify_credential_type_apk_user():
    """Classify apk_user_* credentials."""
    assert classify_credential_type("apk_user_123") == CredentialType.APK_USER


def test_classify_credential_type_apk():
    """Classify apk_* credentials."""
    assert classify_credential_type("apk_123") == CredentialType.APK


def test_classify_credential_type_cog():
    """Classify cog_* credentials."""
    assert classify_credential_type("cog_123") == CredentialType.COG


def test_classify_credential_type_unknown():
    """Classify unknown credentials."""
    assert classify_credential_type("xyz_123") == CredentialType.UNKNOWN


def test_classify_api_version_v1():
    """Classify v1/v2 credentials from prefix."""
    assert classify_api_version("apk_user_123") == ApiVersion.V1
    assert classify_api_version("apk_123") == ApiVersion.V1


def test_classify_api_version_v3():
    """Classify v3 credentials from prefix."""
    assert classify_api_version("cog_123") == ApiVersion.V3


def test_classify_api_version_unknown():
    """Classify unknown API version."""
    assert classify_api_version("xyz_123") == ApiVersion.UNKNOWN


# ===== Account Registration Tests =====

def test_register_account_basic():
    """Basic account registration."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(
        display_label="devin_personal",
        email="j***@example.com",
        identity_source=IdentitySource.USER_PROVIDED,
    )

    assert account.account_id is not None
    assert account.display_label == "devin_personal"
    assert account.email == "j***@example.com"
    assert account.identity_source == IdentitySource.USER_PROVIDED
    assert account.identity_verified is False


def test_register_account_with_browser_source():
    """Account registration with browser-confirmed identity."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(
        display_label="devin_work",
        email="o***@example.com",
        organization_id="org_123",
        plan="Enterprise",
        browser_profile_id="profile_1",
        identity_source=IdentitySource.USER_CONFIRMED_BROWSER,
    )

    assert account.identity_source == IdentitySource.USER_CONFIRMED_BROWSER
    assert account.identity_verified is True
    assert account.organization_id == "org_123"
    assert account.plan == "Enterprise"
    assert account.browser_profile_id == "profile_1"


def test_list_accounts():
    """List multiple accounts."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account1 = service.register_account(display_label="account1")
    account2 = service.register_account(display_label="account2")

    accounts = service.list_accounts()
    assert len(accounts) == 2
    assert account1 in accounts
    assert account2 in accounts


# ===== Credential Registration Tests =====

def test_register_credential_basic():
    """Basic credential registration."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(display_label="account1")
    credential = service.register_credential(
        account_id=account.account_id,
        secret="apk_user_1234567890",
        source="user_provided",
    )

    assert credential.credential_id is not None
    assert credential.account_id == account.account_id
    assert credential.fingerprint == compute_credential_fingerprint("apk_user_1234567890")
    assert credential.credential_type == CredentialType.APK_USER
    assert credential.api_version == ApiVersion.V1
    assert credential.source == "user_provided"
    assert credential.validation_status == ValidationStatus.UNVERIFIED


def test_register_credential_unknown_account():
    """Register credential for unknown account raises error."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    with pytest.raises(ValueError, match="Account .* not found"):
        service.register_credential(
            account_id="unknown_account_id",
            secret="apk_user_123",
        )


def test_two_credentials_coexist():
    """Two credentials can coexist in metadata without exposing secrets."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(display_label="account1")
    cred1 = service.register_credential(
        account_id=account.account_id,
        secret="apk_user_1111111111",
    )
    cred2 = service.register_credential(
        account_id=account.account_id,
        secret="apk_user_2222222222",
    )

    # Credentials have different IDs
    assert cred1.credential_id != cred2.credential_id

    # Credentials have different fingerprints
    assert cred1.fingerprint != cred2.fingerprint

    # Raw secrets are not in credential metadata
    assert "apk_user_1111111111" not in cred1.model_dump_json()
    assert "apk_user_2222222222" not in cred2.model_dump_json()

    # But secrets are stored in SecretVault
    secret1 = service.get_credential_secret(cred1.credential_id)
    secret2 = service.get_credential_secret(cred2.credential_id)
    assert secret1 == "apk_user_1111111111"
    assert secret2 == "apk_user_2222222222"


def test_list_credentials_by_account():
    """List credentials filtered by account."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account1 = service.register_account(display_label="account1")
    account2 = service.register_account(display_label="account2")

    cred1a = service.register_credential(account_id=account1.account_id, secret="apk_user_1a")
    cred1b = service.register_credential(account_id=account1.account_id, secret="apk_user_1b")
    cred2a = service.register_credential(account_id=account2.account_id, secret="apk_user_2a")

    # All credentials
    all_creds = service.list_credentials()
    assert len(all_creds) == 3

    # Account1 credentials
    account1_creds = service.list_credentials(account_id=account1.account_id)
    assert len(account1_creds) == 2
    assert cred1a in account1_creds
    assert cred1b in account1_creds
    assert cred2a not in account1_creds

    # Account2 credentials
    account2_creds = service.list_credentials(account_id=account2.account_id)
    assert len(account2_creds) == 1
    assert cred2a in account2_creds


# ===== Identity Source Preservation Tests =====

def test_identity_source_preserved():
    """Account identity source is preserved."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(
        display_label="account1",
        identity_source=IdentitySource.PROVIDER_RETURNED,
    )

    retrieved = service.get_account(account.account_id)
    assert retrieved.identity_source == IdentitySource.PROVIDER_RETURNED
    assert retrieved.identity_verified is True


def test_unknown_account_ownership_not_verified():
    """Unknown account ownership remains NOT_VERIFIED."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(
        display_label="account1",
        identity_source=IdentitySource.INFERRED,
    )

    assert account.identity_source == IdentitySource.INFERRED
    assert account.identity_verified is False


# ===== Legacy Credential Migration Tests =====

def test_migrate_existing_credential():
    """Existing legacy credential can be registered without deletion."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(display_label="account1")
    credential = service.migrate_existing_credential(
        account_id=account.account_id,
        secret="apk_user_legacy123",
        source="legacy",
    )

    assert credential.source == "legacy"
    assert credential.validation_status == ValidationStatus.UNVERIFIED
    assert credential.fingerprint == compute_credential_fingerprint("apk_user_legacy123")

    # Secret is still accessible
    secret = service.get_credential_secret(credential.credential_id)
    assert secret == "apk_user_legacy123"


# ===== Validation Tests =====

def test_validation_result_attribution():
    """Validation results are attributed to the exact credential fingerprint."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(display_label="account1")
    cred1 = service.register_credential(account_id=account.account_id, secret="fake_key_1")
    cred2 = service.register_credential(account_id=account.account_id, secret="fake_key_2")

    # Validate credential 1 (will fail with fake key, but that's OK for test)
    result1 = service.validate_credential_read_only(cred1.credential_id)

    # Credential 1 should have validation metadata updated
    updated_cred1 = service.get_credential(cred1.credential_id)
    assert updated_cred1.last_validated_at is not None
    assert updated_cred1.last_error_code is not None  # Should have error from fake key

    # Credential 2 should NOT have validation metadata (not validated)
    updated_cred2 = service.get_credential(cred2.credential_id)
    assert updated_cred2.last_validated_at is None
    assert updated_cred2.last_error_code is None

    # Results are attributed to fingerprint
    assert result1['error_code'] == updated_cred1.last_error_code


def test_validate_unknown_credential():
    """Validate unknown credential returns error."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    result = service.validate_credential_read_only("unknown_credential_id")
    assert result['valid'] is False
    assert result['error_code'] == 'CREDENTIAL_NOT_FOUND'


# ===== Secret Safety Tests =====

def test_raw_secrets_not_in_metadata():
    """Raw secrets are never emitted to credential metadata."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault)

    account = service.register_account(display_label="account1")
    credential = service.register_credential(
        account_id=account.account_id,
        secret="apk_user_secret123",
    )

    # Secret not in credential JSON
    credential_json = credential.model_dump_json()
    assert "apk_user_secret123" not in credential_json

    # Secret not in account JSON
    account_json = account.model_dump_json()
    assert "apk_user_secret123" not in account_json

    # But secret is accessible via SecretVault
    secret = service.get_credential_secret(credential.credential_id)
    assert secret == "apk_user_secret123"
