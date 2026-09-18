"""Devin Credential Adapter

Provider-specific implementation for Devin API credentials.
"""

import os
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    httpx = None

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


class DevinCredentialAdapter(ProviderCredentialAdapter):
    """Devin-specific credential management."""
    
    @property
    def provider_name(self) -> str:
        return "devin"
    
    def discover(self) -> CredentialDiscoveryResult:
        """Discover Devin API credentials from environment."""
        credentials = []
        
        # Check environment variables for Devin credentials
        env_vars = [
            'DEVIN_API_KEY_IABV',
            'IABV_DEVIN_API_KEY',
            'DEVIN_API_KEY',
            'DEVIN_API_KEY_SERVICE',
            'DEVIN_API_KEY_LEGACY',
        ]
        
        for env_var in env_vars:
            key = os.environ.get(env_var, '')
            if not key:
                continue
            
            # Classify by prefix (metadata only, no secret)
            credential_type, api_version = self.classify(key)
            
            # Create credential record
            record = CredentialRecord(
                credential_id=self._generate_credential_id('devin', env_var),
                provider='devin',
                principal_id='',  # Identity unknown until provided by API response
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
        """Classify a Devin credential by its prefix."""
        if secret.startswith('cog_'):
            return "current_v3", "v3"
        elif secret.startswith('apk_user'):
            return "legacy_personal_v1_v2", "v1"
        elif secret.startswith('apk_'):
            return "legacy_service_v1", "v1"
        else:
            return "unknown", "unknown"
    
    def check_health(self, record: CredentialRecord, secret: str) -> CredentialRecord:
        """Check health of a Devin credential."""
        record.last_verified_at = datetime.now(timezone.utc).isoformat()
        
        if httpx is None:
            record.status = CredentialStatus.UNKNOWN
            record.last_error_code = "httpx_not_available"
            record.last_error_at = datetime.now(timezone.utc).isoformat()
            return record
        
        headers = {
            'Authorization': f'Bearer {secret}',
            'Content-Type': 'application/json',
        }
        
        # Check v3/self if credential is v3
        if record.api_version == 'v3':
            return self._check_v3_health(record, headers)
        
        # Check v1 compatibility for legacy credentials
        elif record.api_version == 'v1':
            return self._check_v1_health(record, headers)
        
        return record
    
    def _check_v3_health(self, record: CredentialRecord, headers: dict) -> CredentialRecord:
        """Check health of a v3 credential."""
        try:
            response = httpx.get(
                'https://api.devin.ai/v3/self',
                headers=headers,
                timeout=10.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                record.status = CredentialStatus.AVAILABLE
                record.auth_state = AuthState.AUTHENTICATED
                record.auth_state_at = datetime.now(timezone.utc).isoformat()
                record.authorization_state = AuthorizationState.AUTHORIZED
                record.authorization_state_at = datetime.now(timezone.utc).isoformat()
                record.health_state = HealthState.HEALTHY
                record.health_state_at = datetime.now(timezone.utc).isoformat()
                record.quota_state = QuotaState.AVAILABLE
                record.organization_id = data.get('organization', {}).get('id', '')
                record.last_error_code = ""
                record.last_error_at = ""
                
            elif response.status_code == 401:
                record.status = CredentialStatus.AUTH_FAILURE
                record.auth_state = AuthState.NOT_AUTHENTICATED
                record.auth_state_at = datetime.now(timezone.utc).isoformat()
                record.authorization_state = AuthorizationState.UNKNOWN
                record.health_state = HealthState.UNHEALTHY
                record.health_state_at = datetime.now(timezone.utc).isoformat()
                record.last_error_code = "401"
                record.last_error_at = datetime.now(timezone.utc).isoformat()
                
            elif response.status_code == 403:
                record.status = CredentialStatus.FORBIDDEN
                record.auth_state = AuthState.AUTHENTICATED
                record.auth_state_at = datetime.now(timezone.utc).isoformat()
                record.authorization_state = AuthorizationState.UNKNOWN
                record.health_state = HealthState.UNKNOWN
                record.health_state_at = datetime.now(timezone.utc).isoformat()
                record.last_error_code = "403"
                record.last_error_at = datetime.now(timezone.utc).isoformat()
                
            else:
                record.status = CredentialStatus.UNKNOWN
                record.auth_state = AuthState.UNKNOWN
                record.authorization_state = AuthorizationState.UNKNOWN
                record.health_state = HealthState.UNKNOWN
                record.last_error_code = str(response.status_code)
                record.last_error_at = datetime.now(timezone.utc).isoformat()
                
        except Exception as e:
            record.status = CredentialStatus.UNKNOWN
            record.auth_state = AuthState.UNKNOWN
            record.authorization_state = AuthorizationState.UNKNOWN
            record.health_state = HealthState.UNKNOWN
            record.last_error_code = type(e).__name__
            record.last_error_at = datetime.now(timezone.utc).isoformat()
        
        return record
    
    def _check_v1_health(self, record: CredentialRecord, headers: dict) -> CredentialRecord:
        """Check health of a v1 credential."""
        # No idempotent health endpoint exists for v1
        # Do not create sessions for health check
        # Health state remains UNKNOWN until legitimate observation
        record.health_state = HealthState.UNKNOWN
        record.quota_state = QuotaState.UNKNOWN
        record.last_error_code = "health_endpoint_unavailable"
        record.last_error_at = datetime.now(timezone.utc).isoformat()
        return record
    
    def parse_quota(self, response_data: dict) -> tuple[QuotaState, int, str]:
        """Parse quota information from Devin response."""
        # Devin does not provide explicit quota information in standard responses
        # We rely on error parsing in _check_v1_health to detect quota exhaustion
        return QuotaState.UNKNOWN, -1, ""
    
    def _generate_credential_id(self, provider: str, secret_ref: str) -> str:
        """Generate a unique credential ID."""
        import hashlib
        unique = f"{provider}:{secret_ref}"
        return hashlib.sha256(unique.encode()).hexdigest()[:16]
