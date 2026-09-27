"""DevinAccountRepository: Persistent storage for Devin accounts and credentials.

This repository provides SQLite-backed persistence for:
- DevinAccount records (identity metadata)
- DevinCredential records (credential metadata, not secrets)

Raw secrets remain in SecretVault (keyring).
This repository stores only metadata.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import (
    ApiVersion,
    CredentialType,
    DevinAccount,
    DevinCredential,
    IdentitySource,
    SecretReference,
    ValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DevinAccountRepository:
    """Repository for persistent Devin account and credential metadata."""

    def __init__(self, db: AppDatabase) -> None:
        self.db = db

    # ===== Account Operations =====

    def save_account(self, account: DevinAccount) -> DevinAccount:
        """Save or update a Devin account record."""
        account.updated_at_utc = datetime.now(timezone.utc)
        self.db.execute(
            """
            INSERT OR REPLACE INTO devin_accounts
            (account_id, provider, display_label, email, organization_id, organization_label,
             plan, browser_profile_id, identity_source, identity_verified,
             account_json, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account.account_id,
                account.provider,
                account.display_label,
                account.email,
                account.organization_id,
                account.organization_label,
                account.plan,
                account.browser_profile_id,
                account.identity_source.value,
                1 if account.identity_verified else 0,
                account.model_dump_json(),
                account.created_at_utc.isoformat(),
                account.updated_at_utc.isoformat(),
            ),
        )
        logger.debug('DevinAccountRepository: saved account %s', account.account_id)
        return account

    def get_account(self, account_id: str) -> DevinAccount | None:
        """Retrieve a Devin account by ID."""
        row = self.db.fetchone(
            "SELECT account_json FROM devin_accounts WHERE account_id = ?",
            (account_id,),
        )
        if row is None:
            return None
        return DevinAccount.model_validate_json(row["account_json"])

    def list_accounts(self) -> list[DevinAccount]:
        """List all Devin accounts."""
        rows = self.db.fetchall("SELECT account_json FROM devin_accounts ORDER BY updated_at_utc DESC")
        return [DevinAccount.model_validate_json(row["account_json"]) for row in rows]

    def delete_account(self, account_id: str) -> bool:
        """Delete a Devin account and all associated credentials."""
        result = self.db.execute(
            "DELETE FROM devin_accounts WHERE account_id = ?",
            (account_id,),
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info('DevinAccountRepository: deleted account %s', account_id)
        return deleted

    # ===== Credential Operations =====

    def save_credential(self, credential: DevinCredential) -> DevinCredential:
        """Save or update a Devin credential record."""
        credential.updated_at_utc = datetime.now(timezone.utc)
        self.db.execute(
            """
            INSERT OR REPLACE INTO devin_credentials
            (credential_id, account_id, secret_ref_id, fingerprint, credential_type, api_version,
             source, validation_status, last_validated_at, last_http_status, last_error_code,
             last_error_summary, capabilities_json, credential_json, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                credential.credential_id,
                credential.account_id,
                credential.secret_reference.ref_id,
                credential.fingerprint,
                credential.credential_type.value,
                credential.api_version.value,
                credential.source,
                credential.validation_status.value,
                credential.last_validated_at.isoformat() if credential.last_validated_at else None,
                credential.last_http_status,
                credential.last_error_code,
                credential.last_error_summary,
                '{}',  # capabilities_json (simplified)
                credential.model_dump_json(exclude={'capabilities'}),
                credential.created_at_utc.isoformat(),
                credential.updated_at_utc.isoformat(),
            ),
        )
        logger.debug('DevinAccountRepository: saved credential %s', credential.credential_id)
        return credential

    def get_credential(self, credential_id: str) -> DevinCredential | None:
        """Retrieve a Devin credential by ID."""
        row = self.db.fetchone(
            "SELECT credential_json FROM devin_credentials WHERE credential_id = ?",
            (credential_id,),
        )
        if row is None:
            return None
        return DevinCredential.model_validate_json(row["credential_json"])

    def list_credentials(self, account_id: str | None = None) -> list[DevinCredential]:
        """List all credentials, optionally filtered by account."""
        if account_id is None:
            rows = self.db.fetchall(
                "SELECT credential_json FROM devin_credentials ORDER BY updated_at_utc DESC"
            )
        else:
            rows = self.db.fetchall(
                "SELECT credential_json FROM devin_credentials WHERE account_id = ? ORDER BY updated_at_utc DESC",
                (account_id,),
            )
        return [DevinCredential.model_validate_json(row["credential_json"]) for row in rows]

    def delete_credential(self, credential_id: str) -> bool:
        """Delete a Devin credential."""
        result = self.db.execute(
            "DELETE FROM devin_credentials WHERE credential_id = ?",
            (credential_id,),
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info('DevinAccountRepository: deleted credential %s', credential_id)
        return deleted

    # ===== Query Operations =====

    def get_credential_by_fingerprint(self, fingerprint: str) -> DevinCredential | None:
        """Retrieve a credential by fingerprint."""
        row = self.db.fetchone(
            "SELECT credential_json FROM devin_credentials WHERE fingerprint = ?",
            (fingerprint,),
        )
        if row is None:
            return None
        return DevinCredential.model_validate_json(row["credential_json"])

    def list_credentials_by_status(self, status: ValidationStatus) -> list[DevinCredential]:
        """List credentials by validation status."""
        rows = self.db.fetchall(
            "SELECT credential_json FROM devin_credentials WHERE validation_status = ? ORDER BY updated_at_utc DESC",
            (status.value,),
        )
        return [DevinCredential.model_validate_json(row["credential_json"]) for row in rows]

    def count_accounts(self) -> int:
        """Count total accounts."""
        row = self.db.fetchone("SELECT COUNT(*) AS cnt FROM devin_accounts")
        return int(row["cnt"]) if row else 0

    def count_credentials(self, account_id: str | None = None) -> int:
        """Count total credentials, optionally filtered by account."""
        if account_id is None:
            row = self.db.fetchone("SELECT COUNT(*) AS cnt FROM devin_credentials")
        else:
            row = self.db.fetchone(
                "SELECT COUNT(*) AS cnt FROM devin_credentials WHERE account_id = ?",
                (account_id,),
            )
        return int(row["cnt"]) if row else 0
