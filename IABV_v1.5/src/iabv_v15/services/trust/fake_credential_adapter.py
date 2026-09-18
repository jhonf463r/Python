"""Fake Credential Adapter for Testing

Test-only provider adapter for validating provider-neutral architecture.
"""

from datetime import datetime, timezone

from iabv_v15.services.trust.provider_credential_adapter import (
    AuthState,
    AuthorizationState,
    CredentialDiscoveryResult,
    CredentialRecord,
    CredentialStatus,
    EpistemicState,
    HealthState,
    ProviderCredentialAdapter,
    ProvisioningState,
    QuotaState,
)


class FakeCredentialAdapter(ProviderCredentialAdapter):
    """Fake provider adapter for testing."""
    
    def __init__(self, fake_credentials: dict[str, str] | None = None):
        """Initialize with fake credentials for testing.
        
        Args:
            fake_credentials: Dict of env_var -> secret for testing
        """
        self._fake_credentials = fake_credentials or {}
    
    @property
    def provider_name(self) -> str:
        return "fake"
    
    def discover(self) -> CredentialDiscoveryResult:
        """Discover fake credentials from test configuration."""
        credentials = []
        
        for env_var, secret in self._fake_credentials.items():
            credential_type, api_version = self.classify(secret)
            
            record = CredentialRecord(
                credential_id=self._generate_credential_id('fake', env_var),
                provider='fake',
                principal_id=secret[:10],
                credential_type=credential_type,
                secret_ref=env_var,
                api_version=api_version,
                status=CredentialStatus.UNKNOWN,
                provisioning_state=ProvisioningState.DISCOVERABLE,
                provisioning_state_at=datetime.now(timezone.utc).isoformat(),
                source_state=EpistemicState.OBSERVED,
                source_state_at=datetime.now(timezone.utc).isoformat(),
            )
            
            credentials.append(record)
        
        return CredentialDiscoveryResult(records=credentials)
    
    def classify(self, secret: str) -> tuple[str, str]:
        """Classify a fake credential by its prefix."""
        if secret.startswith('fake_v3_'):
            return "fake_v3", "v3"
        elif secret.startswith('fake_v1_'):
            return "fake_v1", "v1"
        else:
            return "unknown", "unknown"
    
    def check_health(self, record: CredentialRecord, secret: str) -> CredentialRecord:
        """Check health of a fake credential (simulated)."""
        record.last_verified_at = datetime.now(timezone.utc).isoformat()
        
        # Simulate health check based on secret prefix
        if secret.startswith('fake_v3_exhausted'):
            record.status = CredentialStatus.QUOTA_EXHAUSTED
            record.auth_state = AuthState.AUTHENTICATED
            record.auth_state_at = datetime.now(timezone.utc).isoformat()
            record.authorization_state = AuthorizationState.PARTIALLY_AUTHORIZED
            record.authorization_state_at = datetime.now(timezone.utc).isoformat()
            record.health_state = HealthState.HEALTHY
            record.health_state_at = datetime.now(timezone.utc).isoformat()
            record.quota_state = QuotaState.EXHAUSTED
            record.quota_reset_at = "UNKNOWN"
            record.last_error_code = "quota_exhausted"
            record.last_error_at = datetime.now(timezone.utc).isoformat()
        elif secret.startswith('fake_v3_auth_fail'):
            record.status = CredentialStatus.AUTH_FAILURE
            record.auth_state = AuthState.NOT_AUTHENTICATED
            record.auth_state_at = datetime.now(timezone.utc).isoformat()
            record.authorization_state = AuthorizationState.UNKNOWN
            record.health_state = HealthState.UNHEALTHY
            record.health_state_at = datetime.now(timezone.utc).isoformat()
            record.last_error_code = "401"
            record.last_error_at = datetime.now(timezone.utc).isoformat()
        elif secret.startswith('fake_v3_'):
            record.status = CredentialStatus.AVAILABLE
            record.auth_state = AuthState.AUTHENTICATED
            record.auth_state_at = datetime.now(timezone.utc).isoformat()
            record.authorization_state = AuthorizationState.AUTHORIZED
            record.authorization_state_at = datetime.now(timezone.utc).isoformat()
            record.health_state = HealthState.HEALTHY
            record.health_state_at = datetime.now(timezone.utc).isoformat()
            record.quota_state = QuotaState.AVAILABLE
            record.last_error_code = ""
            record.last_error_at = ""
        elif secret.startswith('fake_v1_'):
            record.status = CredentialStatus.AVAILABLE
            record.auth_state = AuthState.AUTHENTICATED
            record.auth_state_at = datetime.now(timezone.utc).isoformat()
            record.authorization_state = AuthorizationState.AUTHORIZED
            record.authorization_state_at = datetime.now(timezone.utc).isoformat()
            record.health_state = HealthState.HEALTHY
            record.health_state_at = datetime.now(timezone.utc).isoformat()
            record.quota_state = QuotaState.AVAILABLE
            record.last_error_code = ""
            record.last_error_at = ""
        else:
            record.status = CredentialStatus.UNKNOWN
            record.auth_state = AuthState.UNKNOWN
            record.authorization_state = AuthorizationState.UNKNOWN
            record.health_state = HealthState.UNKNOWN
            record.last_error_code = "unknown_type"
            record.last_error_at = datetime.now(timezone.utc).isoformat()
        
        return record
    
    def parse_quota(self, response_data: dict) -> tuple[QuotaState, int, str]:
        """Parse quota information from fake response."""
        return QuotaState.UNKNOWN, -1, ""
    
    def _generate_credential_id(self, provider: str, secret_ref: str) -> str:
        """Generate a unique credential ID."""
        import hashlib
        unique = f"{provider}:{secret_ref}"
        return hashlib.sha256(unique.encode()).hexdigest()[:16]
