"""Provider Credential Adapter Interface

Defines the contract for provider-specific credential discovery and health checking.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CredentialStatus(Enum):
    """Status of a credential."""
    AVAILABLE = "available"
    AUTH_FAILURE = "auth_failure"
    FORBIDDEN = "forbidden"
    QUOTA_EXHAUSTED = "quota_exhausted"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DISABLED = "disabled"
    LEGACY = "legacy"
    UNKNOWN = "unknown"


class QuotaState(Enum):
    """Quota state for a credential."""
    AVAILABLE = "available"
    EXHAUSTED = "exhausted"
    UNKNOWN = "unknown"


class EpistemicState(Enum):
    """Epistemic state of knowledge about a credential property."""
    FACT = "fact"
    OBSERVED = "observed"
    INFERENCE = "inference"
    UNKNOWN = "unknown"
    NEGATIVE_KNOWLEDGE = "negative_knowledge"


class ProvisioningState(Enum):
    """Provisioning state of a credential."""
    EXTERNAL_EXISTS = "external_exists"
    PROVISIONED = "provisioned"
    DISCOVERABLE = "discoverable"
    RESOLVABLE = "resolvable"
    UNKNOWN = "unknown"


class AuthState(Enum):
    """Authentication state of a credential."""
    AUTHENTICATED = "authenticated"
    NOT_AUTHENTICATED = "not_authenticated"
    UNKNOWN = "unknown"


class AuthorizationState(Enum):
    """Authorization state of a credential."""
    AUTHORIZED = "authorized"
    PARTIALLY_AUTHORIZED = "partially_authorized"
    NOT_AUTHORIZED = "not_authorized"
    UNKNOWN = "unknown"


class HealthState(Enum):
    """Health state of a credential."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CredentialRecord:
    """Secure record of a credential without storing the secret value."""
    
    credential_id: str
    provider: str
    principal_id: str
    credential_type: str
    secret_ref: str  # Reference to where the secret is stored (e.g., env var name)
    api_version: str
    organization_id: str = ""
    scope: str = ""
    capabilities: list[str] = None
    status: CredentialStatus = CredentialStatus.UNKNOWN
    enabled: bool = True
    created_at: str = None
    last_verified_at: str = ""
    expires_at: str = ""
    
    # Provisioning state
    provisioning_state: ProvisioningState = ProvisioningState.UNKNOWN
    provisioning_state_at: str = ""
    
    # Authentication state
    auth_state: AuthState = AuthState.UNKNOWN
    auth_state_at: str = ""
    
    # Authorization state
    authorization_state: AuthorizationState = AuthorizationState.UNKNOWN
    authorization_state_at: str = ""
    
    # Health state
    health_state: HealthState = HealthState.UNKNOWN
    health_state_at: str = ""
    
    # Quota tracking
    quota_state: QuotaState = QuotaState.UNKNOWN
    quota_remaining: int = -1
    quota_limit: int = -1
    quota_reset_at: str = ""
    
    # Rate limiting
    rate_limit_remaining: int = -1
    rate_limit_reset_at: str = ""
    
    # Error tracking
    last_error_code: str = ""
    last_error_at: str = ""
    last_error_message: str = ""
    
    # Source tracking
    source_state: EpistemicState = EpistemicState.UNKNOWN
    source_state_at: str = ""
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CredentialDiscoveryResult:
    """Result of credential discovery."""
    records: list[CredentialRecord]


class ProviderCredentialAdapter(ABC):
    """Interface for provider-specific credential management."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'devin', 'openai', 'anthropic')."""
        pass
    
    @abstractmethod
    def discover(self) -> CredentialDiscoveryResult:
        """Discover credentials for this provider from environment/config.
        
        Returns metadata records without storing secrets.
        """
        pass
    
    @abstractmethod
    def classify(self, secret: str) -> tuple[str, str]:
        """Classify a credential by its prefix/value.
        
        Returns:
            (credential_type, api_version)
        """
        pass
    
    @abstractmethod
    def check_health(self, record: CredentialRecord, secret: str) -> CredentialRecord:
        """Check health of a credential without exposing the secret.
        
        Updates the record with:
        - status (AVAILABLE, AUTH_FAILURE, QUOTA_EXHAUSTED, etc.)
        - quota_state
        - quota_remaining
        - quota_reset_at
        - last_error_code
        - last_error_at
        - last_error_message
        """
        pass
    
    @abstractmethod
    def parse_quota(self, response_data: dict[str, Any]) -> tuple[QuotaState, int, str]:
        """Parse quota information from provider response.
        
        Returns:
            (quota_state, quota_remaining, quota_reset_at)
        """
        pass
