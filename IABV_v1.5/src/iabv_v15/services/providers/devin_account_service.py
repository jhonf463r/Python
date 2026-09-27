"""DevinAccountService: Registry for Devin accounts and credentials.

This service manages:
- Account registration (browser-observed identity)
- Credential registration (secure storage via SecretVault)
- Credential validation (READ-ONLY health checks)
- Account-credential association with explicit identity sources
- Persistent storage via DevinAccountRepository

This does NOT implement automatic multi-account routing.
It only provides the registry and validation foundation.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    ApiVersion,
    CredentialType,
    DevinAccount,
    DevinCredential,
    IdentitySource,
    SecretReference,
    ValidationStatus,
)
from iabv_v15.infra.persistence.devin_account_repository import DevinAccountRepository
from iabv_v15.services.capture.secret_vault import SecretVault

logger = logging.getLogger(__name__)


def compute_credential_fingerprint(secret: str) -> str:
    """Compute a non-secret fingerprint for credential identification.

    Properties:
    - Deterministic: same secret always produces same fingerprint
    - Non-reversible: fingerprint cannot be used to recover secret
    - Stable: allows tracking same credential across validations
    - Safe: can be stored in logs, evidence artifacts, and metadata
    """
    return hashlib.sha256(secret.encode('utf-8')).hexdigest()[:16]


def classify_credential_type(secret: str) -> CredentialType:
    """Classify credential type from prefix."""
    if secret.startswith('apk_user_'):
        return CredentialType.APK_USER
    elif secret.startswith('apk_'):
        return CredentialType.APK
    elif secret.startswith('cog_'):
        return CredentialType.COG
    else:
        return CredentialType.UNKNOWN


def classify_api_version(secret: str) -> ApiVersion:
    """Classify API version from prefix (inferred)."""
    if secret.startswith('apk_'):
        return ApiVersion.V1
    elif secret.startswith('cog_'):
        return ApiVersion.V3
    else:
        return ApiVersion.UNKNOWN


class DevinAccountService:
    """Registry and validation service for Devin accounts and credentials."""

    def __init__(self, *, secret_vault: SecretVault, repository: DevinAccountRepository | None = None) -> None:
        self._vault = secret_vault
        self._repository = repository
        self._accounts: dict[str, DevinAccount] = {}  # account_id -> account
        self._credentials: dict[str, DevinCredential] = {}  # credential_id -> credential
        self._account_credentials: dict[str, list[str]] = {}  # account_id -> [credential_ids]

        # Load from repository if available
        if self._repository is not None:
            self._load_from_repository()

    def _load_from_repository(self) -> None:
        """Load accounts and credentials from repository."""
        try:
            # Load accounts
            accounts = self._repository.list_accounts()
            for account in accounts:
                self._accounts[account.account_id] = account
                self._account_credentials[account.account_id] = []

            # Load credentials
            credentials = self._repository.list_credentials()
            for credential in credentials:
                self._credentials[credential.credential_id] = credential
                if credential.account_id in self._account_credentials:
                    self._account_credentials[credential.account_id].append(credential.credential_id)
                else:
                    self._account_credentials[credential.account_id] = [credential.credential_id]

            logger.info(
                'DevinAccountService: loaded %d accounts and %d credentials from repository',
                len(accounts),
                len(credentials),
            )
        except Exception as e:
            logger.error('DevinAccountService: failed to load from repository: %s', e)

    # ===== Account Registration =====

    def register_account(
        self,
        display_label: str,
        email: str | None = None,
        organization_id: str | None = None,
        organization_label: str | None = None,
        plan: str | None = None,
        browser_profile_id: str | None = None,
        identity_source: IdentitySource = IdentitySource.USER_PROVIDED,
    ) -> DevinAccount:
        """Register a Devin account with observed or user-provided identity.

        Args:
            display_label: User-provided label (e.g., "devin_personal")
            email: Masked email from browser/API
            organization_id: Org ID from API or browser
            organization_label: User-provided org label
            plan: Plan from browser (self-serve, Enterprise, etc.)
            browser_profile_id: BrowserProfileConfig.profile_id if applicable
            identity_source: Source of identity information

        Returns:
            The registered DevinAccount
        """
        account = DevinAccount(
            display_label=display_label,
            email=email,
            organization_id=organization_id,
            organization_label=organization_label,
            plan=plan,
            browser_profile_id=browser_profile_id,
            identity_source=identity_source,
            identity_verified=identity_source in (IdentitySource.USER_CONFIRMED_BROWSER, IdentitySource.PROVIDER_RETURNED),
        )
        self._accounts[account.account_id] = account
        self._account_credentials[account.account_id] = []
        logger.info('DevinAccountService: registered account %s (%s)', account.account_id, display_label)

        # Persist to repository if available
        if self._repository is not None:
            self._repository.save_account(account)

        return account

    def get_account(self, account_id: str) -> DevinAccount | None:
        """Retrieve an account by ID."""
        return self._accounts.get(account_id)

    def list_accounts(self) -> list[DevinAccount]:
        """List all registered accounts."""
        return list(self._accounts.values())

    # ===== Credential Registration =====

    def register_credential(
        self,
        account_id: str,
        secret: str,
        source: str = "legacy",
    ) -> DevinCredential:
        """Register a Devin credential with secure storage.

        Args:
            account_id: Reference to DevinAccount.account_id
            secret: Raw API key (will be stored in SecretVault)
            source: Source of credential ("legacy", "browser", "user_provided", etc.)

        Returns:
            The registered DevinCredential

        Raises:
            ValueError: If account_id does not exist
        """
        if account_id not in self._accounts:
            raise ValueError(f"Account {account_id} not found")

        # Generate credential_id first for unique key
        credential_id = str(uuid4())

        # Store secret in SecretVault with unique key per credential
        secret_reference = self._vault.put_secret(
            domain="devin",
            account=credential_id,  # Use credential_id for unique storage
            field_role="api_key",
            secret=secret,
        )

        # Compute fingerprint
        fingerprint = compute_credential_fingerprint(secret)

        # Classify credential
        credential_type = classify_credential_type(secret)
        api_version = classify_api_version(secret)

        # Create credential record
        credential = DevinCredential(
            credential_id=credential_id,
            account_id=account_id,
            secret_reference=secret_reference,
            fingerprint=fingerprint,
            credential_type=credential_type,
            api_version=api_version,
            source=source,
            validation_status=ValidationStatus.UNVERIFIED,
        )

        self._credentials[credential.credential_id] = credential
        self._account_credentials[account_id].append(credential.credential_id)

        logger.info(
            'DevinAccountService: registered credential %s for account %s (type=%s, api=%s, fingerprint=%s)',
            credential.credential_id,
            account_id,
            credential_type.value,
            api_version.value,
            fingerprint,
        )

        # Persist to repository if available
        if self._repository is not None:
            self._repository.save_credential(credential)

        return credential

    def get_credential(self, credential_id: str) -> DevinCredential | None:
        """Retrieve a credential by ID."""
        return self._credentials.get(credential_id)

    def list_credentials(self, account_id: str | None = None) -> list[DevinCredential]:
        """List all credentials, optionally filtered by account."""
        if account_id is None:
            return list(self._credentials.values())
        credential_ids = self._account_credentials.get(account_id, [])
        return [self._credentials[cid] for cid in credential_ids if cid in self._credentials]

    def get_credential_secret(self, credential_id: str) -> str | None:
        """Retrieve the raw secret for a credential from SecretVault.

        Args:
            credential_id: Credential ID

        Returns:
            Raw secret, or None if not found or unavailable
        """
        credential = self._credentials.get(credential_id)
        if credential is None:
            return None
        return self._vault.resolve_reference(credential.secret_reference)

    # ===== Credential Validation =====

    def validate_credential_read_only(
        self,
        credential_id: str,
    ) -> dict[str, Any]:
        """Perform a READ-ONLY validation of a credential.

        For v1/v2 credentials: GET /v1/sessions?limit=1
        For v3 credentials: use appropriate v3 READ-ONLY endpoint (when implemented)

        Args:
            credential_id: Credential ID to validate

        Returns:
            Validation result dict with keys:
            - valid: bool
            - http_status: int | None
            - error_code: str | None
            - error_summary: str | None
            - latency_ms: float | None
        """
        credential = self._credentials.get(credential_id)
        if credential is None:
            return {
                'valid': False,
                'http_status': None,
                'error_code': 'CREDENTIAL_NOT_FOUND',
                'error_summary': f'Credential {credential_id} not found',
                'latency_ms': None,
            }

        secret = self.get_credential_secret(credential_id)
        if secret is None:
            return {
                'valid': False,
                'http_status': None,
                'error_code': 'SECRET_UNAVAILABLE',
                'error_summary': 'Secret not available from SecretVault',
                'latency_ms': None,
            }

        # Perform READ-ONLY validation based on API version
        if credential.api_version in (ApiVersion.V1, ApiVersion.V2, ApiVersion.UNKNOWN):
            return self._validate_v1_credential(credential, secret)
        elif credential.api_version == ApiVersion.V3:
            return self._validate_v3_credential(credential, secret)
        else:
            return {
                'valid': False,
                'http_status': None,
                'error_code': 'UNSUPPORTED_API_VERSION',
                'error_summary': f'Unsupported API version: {credential.api_version.value}',
                'latency_ms': None,
            }

    def _validate_v1_credential(self, credential: DevinCredential, secret: str) -> dict[str, Any]:
        """Validate a v1/v2 credential using GET /v1/sessions?limit=1."""
        import time
        try:
            import httpx
        except ImportError:
            return {
                'valid': False,
                'http_status': None,
                'error_code': 'HTTPX_NOT_AVAILABLE',
                'error_summary': 'httpx not available',
                'latency_ms': None,
            }

        start_time = time.perf_counter()
        try:
            client = httpx.Client(timeout=10.0)
            response = client.get(
                'https://api.devin.ai/v1/sessions',
                headers={
                    'Authorization': f'Bearer {secret}',
                    'Content-Type': 'application/json',
                },
                params={'limit': '1'},
            )
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            valid = response.status_code == 200
            error_code = None if valid else f'HTTP_{response.status_code}'
            error_summary = "" if valid else f'HTTP {response.status_code}'

            # Update credential record
            credential.validation_status = ValidationStatus.READY if valid else ValidationStatus.ERROR
            credential.last_validated_at = datetime.now(timezone.utc)
            credential.last_http_status = response.status_code
            credential.last_error_code = error_code
            credential.last_error_summary = error_summary
            credential.updated_at_utc = datetime.now(timezone.utc)

            # Persist updated credential metadata
            if self._repository is not None:
                self._repository.save_credential(credential)

            return {
                'valid': valid,
                'http_status': response.status_code,
                'error_code': error_code,
                'error_summary': error_summary,
                'latency_ms': latency_ms,
            }
        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            # Update credential record
            credential.validation_status = ValidationStatus.ERROR
            credential.last_validated_at = datetime.now(timezone.utc)
            credential.last_http_status = None
            credential.last_error_code = 'VALIDATION_EXCEPTION'
            credential.last_error_summary = str(e)
            credential.updated_at_utc = datetime.now(timezone.utc)

            # Persist updated credential metadata
            if self._repository is not None:
                self._repository.save_credential(credential)

            return {
                'valid': False,
                'http_status': None,
                'error_code': 'VALIDATION_EXCEPTION',
                'error_summary': str(e),
                'latency_ms': latency_ms,
            }

    def _validate_v3_credential(self, credential: DevinCredential, secret: str) -> dict[str, Any]:
        """Validate a v3 credential using appropriate v3 READ-ONLY endpoint.

        NOT YET IMPLEMENTED - v3 migration is a separate effort.
        """
        return {
            'valid': False,
            'http_status': None,
            'error_code': 'V3_NOT_IMPLEMENTED',
            'error_summary': 'v3 validation not yet implemented',
            'latency_ms': None,
        }

    # ===== Existing Credential Migration =====

    def migrate_existing_credential(
        self,
        account_id: str,
        secret: str,
        source: str = "legacy",
    ) -> DevinCredential:
        """Migrate an existing credential (e.g., from DEVIN_API_KEY env var) into the registry.

        The credential will be registered as UNVERIFIED if account association is not proven.

        Args:
            account_id: Reference to DevinAccount.account_id
            secret: Raw API key
            source: Source of credential (typically "legacy")

        Returns:
            The registered DevinCredential
        """
        return self.register_credential(account_id, secret, source=source)
