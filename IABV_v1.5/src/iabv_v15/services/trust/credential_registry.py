"""Credential Registry for IABV

Provider-neutral credential lifecycle management.
Discovers, classifies, and checks health of credentials without storing secrets.
Delegates provider-specific logic to ProviderCredentialAdapter implementations.
"""

from datetime import datetime, timezone
from typing import Callable

from iabv_v15.services.trust.provider_credential_adapter import (
    CredentialRecord,
    CredentialStatus,
    ProviderCredentialAdapter,
    QuotaState,
)


class CredentialRegistry:
    """Provider-neutral registry for external agent credentials.
    
    Manages credential lifecycle without storing secrets.
    Delegates provider-specific logic to ProviderCredentialAdapter implementations.
    """
    
    def __init__(self, secret_resolver: Callable[[str], str] | None = None):
        self._credentials: dict[str, CredentialRecord] = {}
        self._adapters: dict[str, ProviderCredentialAdapter] = {}
        self._secret_resolver = secret_resolver if secret_resolver is not None else lambda ref: ''
    
    def register_adapter(self, adapter: ProviderCredentialAdapter) -> None:
        """Register a provider credential adapter."""
        self._adapters[adapter.provider_name] = adapter
    
    def discover_credentials(self, provider: str | None = None) -> list[CredentialRecord]:
        """Discover credentials for a specific provider or all registered providers.
        
        Args:
            provider: If specified, only discover credentials for this provider.
                    If None, discover credentials for all registered providers.
        
        Returns:
            List of credential records without storing secrets.
        """
        credentials = []
        
        if provider:
            adapter = self._adapters.get(provider)
            if adapter:
                result = adapter.discover()
                credentials.extend(result.records)
        else:
            for adapter in self._adapters.values():
                result = adapter.discover()
                credentials.extend(result.records)
        
        return credentials
    
    def check_credential_health(self, record: CredentialRecord) -> CredentialRecord:
        """Check health of a credential without exposing the secret.
        
        Delegates to the appropriate provider adapter.
        """
        # Get secret from secure reference via resolver
        secret = self._secret_resolver(record.secret_ref)
        if not secret:
            record.status = CredentialStatus.UNKNOWN
            record.last_error_code = "secret_not_found"
            record.last_error_at = datetime.now(timezone.utc).isoformat()
            return record
        
        # Delegate to provider adapter
        adapter = self._adapters.get(record.provider)
        if adapter:
            return adapter.check_health(record, secret)
        else:
            record.status = CredentialStatus.UNKNOWN
            record.last_error_code = "adapter_not_found"
            record.last_error_at = datetime.now(timezone.utc).isoformat()
            return record
    
    def register_credentials(self, credentials: list[CredentialRecord]) -> None:
        """Register credentials in the registry."""
        for record in credentials:
            self._credentials[record.credential_id] = record
    
    def get_available_credentials(self, provider: str | None = None) -> list[CredentialRecord]:
        """Get available credentials for a provider or all providers.
        
        Args:
            provider: If specified, only return credentials for this provider.
                    If None, return available credentials for all providers.
        
        Returns:
            List of credentials that are AVAILABLE and enabled.
        """
        if provider:
            return [
                c for c in self._credentials.values()
                if c.provider == provider and c.status == CredentialStatus.AVAILABLE and c.enabled
            ]
        else:
            return [
                c for c in self._credentials.values()
                if c.status == CredentialStatus.AVAILABLE and c.enabled
            ]
    
    def get_credential_candidates(
        self,
        provider: str | None = None,
        credential_type: str | None = None,
        api_version: str | None = None,
    ) -> list[CredentialRecord]:
        """Get credential candidates based on filters.
        
        Args:
            provider: Filter by provider (optional)
            credential_type: Filter by credential type (optional)
            api_version: Filter by API version (optional)
        
        Returns:
            List of credential records matching the filters.
        """
        candidates = list(self._credentials.values())
        
        if provider:
            candidates = [c for c in candidates if c.provider == provider]
        if credential_type:
            candidates = [c for c in candidates if c.credential_type == credential_type]
        if api_version:
            candidates = [c for c in candidates if c.api_version == api_version]
        
        return candidates
    
    def get_credential(self, credential_id: str) -> CredentialRecord | None:
        """Get a credential by ID."""
        return self._credentials.get(credential_id)
    
    def resolve_credential_secret(self, credential_id: str) -> str:
        """Resolve the secret for a credential by ID for a single invocation.
        
        This is a temporary resolution for execution. The secret is not stored
        and must be used immediately, then discarded.
        
        Args:
            credential_id: The credential ID to resolve
        
        Returns:
            The secret value, or empty string if not found
        
        Security:
            The secret is returned transiently for immediate use in adapter.run().
            The caller must not persist it, log it, or include it in telemetry.
        """
        record = self._credentials.get(credential_id)
        if not record:
            return ''
        
        return self._secret_resolver(record.secret_ref)
    
    def check_all_credentials(self) -> dict[str, CredentialRecord]:
        """Check health of all registered credentials."""
        results = {}
        for credential_id, record in self._credentials.items():
            results[credential_id] = self.check_credential_health(record)
        return results
