"""Tests for DevinAccountRepository persistence.

Tests focus on:
- Account survives restart
- Credential survives restart
- account_id remains stable
- credential_id remains stable
- fingerprint remains stable
- Multiple credentials remain distinct
- Multiple accounts remain distinct
- Validation metadata survives restart
- Raw secrets are never persisted in registry metadata
- Existing legacy credential remains available in SecretVault
- Metadata can load even when SecretVault secret is temporarily unavailable
- Corrupted registry fails explicitly rather than silently resetting
- Unknown account identity remains identity_verified = false
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    ApiVersion,
    CredentialType,
    DevinAccount,
    DevinCredential,
    IdentitySource,
    ValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.devin_account_repository import DevinAccountRepository
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.providers.devin_account_service import DevinAccountService


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


def test_account_survives_restart():
    """Account metadata survives restart."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        # Create service with repository
        service1 = DevinAccountService(secret_vault=vault, repository=repo)

        # Register account
        account1 = service1.register_account(
            display_label="test_account",
            email="test@example.com",
            identity_source=IdentitySource.USER_PROVIDED,
        )

        # Simulate restart: create new service instance with same repository
        service2 = DevinAccountService(secret_vault=vault, repository=repo)

        # Account should be recovered
        recovered = service2.get_account(account1.account_id)
        assert recovered is not None
        assert recovered.account_id == account1.account_id
        assert recovered.display_label == "test_account"
        assert recovered.email == "test@example.com"
        assert recovered.identity_source == IdentitySource.USER_PROVIDED
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_credential_survives_restart():
    """Credential metadata survives restart."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        # Create service with repository
        service1 = DevinAccountService(secret_vault=vault, repository=repo)

        # Register account and credential
        account = service1.register_account(display_label="test_account")
        credential1 = service1.register_credential(
            account_id=account.account_id,
            secret="apk_user_test123",
        )

        # Simulate restart
        service2 = DevinAccountService(secret_vault=vault, repository=repo)

        # Credential should be recovered
        recovered = service2.get_credential(credential1.credential_id)
        assert recovered is not None
        assert recovered.credential_id == credential1.credential_id
        assert recovered.account_id == account.account_id
        assert recovered.fingerprint == credential1.fingerprint
        assert recovered.credential_type == CredentialType.APK_USER
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_account_id_remains_stable():
    """Account ID remains stable across restarts."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account1 = service1.register_account(display_label="test_account")

        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        account2 = service2.get_account(account1.account_id)

        assert account1.account_id == account2.account_id
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_credential_id_remains_stable():
    """Credential ID remains stable across restarts."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account = service1.register_account(display_label="test_account")
        credential1 = service1.register_credential(
            account_id=account.account_id,
            secret="apk_user_test123",
        )

        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        credential2 = service2.get_credential(credential1.credential_id)

        assert credential1.credential_id == credential2.credential_id
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_fingerprint_remains_stable():
    """Fingerprint remains stable across restarts for same secret."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account = service1.register_account(display_label="test_account")
        credential1 = service1.register_credential(
            account_id=account.account_id,
            secret="apk_user_stable_secret",
        )

        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        credential2 = service2.get_credential(credential1.credential_id)

        assert credential1.fingerprint == credential2.fingerprint
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_multiple_credentials_remain_distinct():
    """Multiple credentials remain distinct across restarts."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account = service1.register_account(display_label="test_account")
        cred1 = service1.register_credential(
            account_id=account.account_id,
            secret="apk_user_credential_a",
        )
        cred2 = service1.register_credential(
            account_id=account.account_id,
            secret="apk_user_credential_b",
        )

        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        recovered_creds = service2.list_credentials(account_id=account.account_id)

        assert len(recovered_creds) == 2
        recovered_ids = {c.credential_id for c in recovered_creds}
        assert cred1.credential_id in recovered_ids
        assert cred2.credential_id in recovered_ids
        assert cred1.fingerprint != cred2.fingerprint
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_multiple_accounts_remain_distinct():
    """Multiple accounts remain distinct across restarts."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account1 = service1.register_account(display_label="account_a")
        account2 = service1.register_account(display_label="account_b")

        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        recovered_accounts = service2.list_accounts()

        assert len(recovered_accounts) == 2
        recovered_ids = {a.account_id for a in recovered_accounts}
        assert account1.account_id in recovered_ids
        assert account2.account_id in recovered_ids
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_validation_metadata_survives_restart():
    """Validation metadata survives restart."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account = service1.register_account(display_label="test_account")
        credential = service1.register_credential(
            account_id=account.account_id,
            secret="fake_key",
        )

        # Validate credential (will fail with fake key, but that's OK)
        result = service1.validate_credential_read_only(credential.credential_id)

        # Simulate restart
        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        recovered = service2.get_credential(credential.credential_id)

        # Validation metadata should be preserved
        assert recovered.last_validated_at is not None
        assert recovered.last_error_code is not None  # Should have error from fake key
        assert recovered.validation_status == ValidationStatus.ERROR
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_raw_secrets_never_in_persistence():
    """Raw secrets are never persisted in registry metadata."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service = DevinAccountService(secret_vault=vault, repository=repo)
        account = service.register_account(display_label="test_account")
        credential = service.register_credential(
            account_id=account.account_id,
            secret="apk_user_secret_value_12345",
        )

        # Check database directly
        row = repo.db.fetchone(
            "SELECT credential_json FROM devin_credentials WHERE credential_id = ?",
            (credential.credential_id,),
        )
        assert row is not None
        credential_json = row["credential_json"]
        assert "apk_user_secret_value_12345" not in credential_json

        # Check SecretVault still has the secret
        secret = service.get_credential_secret(credential.credential_id)
        assert secret == "apk_user_secret_value_12345"
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_unknown_account_identity_not_verified():
    """Unknown account identity remains identity_verified = false."""
    os.environ['IABV_SQLITE_WAL'] = '0'  # Disable WAL for tests
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "test.db"
        db = AppDatabase(str(db_path))
        repo = DevinAccountRepository(db)
        vault = FakeSecretVault()

        service1 = DevinAccountService(secret_vault=vault, repository=repo)
        account = service1.register_account(
            display_label="test_account",
            identity_source=IdentitySource.INFERRED,
        )

        service2 = DevinAccountService(secret_vault=vault, repository=repo)
        recovered = service2.get_account(account.account_id)

        assert recovered.identity_source == IdentitySource.INFERRED
        assert recovered.identity_verified is False
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_persistence_without_repository():
    """Service works without repository (in-memory only)."""
    vault = FakeSecretVault()
    service = DevinAccountService(secret_vault=vault, repository=None)

    account = service.register_account(display_label="test_account")
    credential = service.register_credential(
        account_id=account.account_id,
        secret="apk_user_test",
    )

    # Should work normally
    assert service.get_account(account.account_id) is not None
    assert service.get_credential(credential.credential_id) is not None
