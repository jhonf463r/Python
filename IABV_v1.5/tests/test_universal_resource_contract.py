"""Tests for Universal External Resource Contract.

Tests the universal representation of heterogeneous external resources:
- Browser accounts (ChatGPT, Claude, etc.)
- API credentials (Devin, GitHub, OpenAI, etc.)
- Local endpoints (Ollama, etc.)

Key properties:
- Credential opacity (secrets never exposed)
- Multiple credentials for same provider
- Different availability states
- Routing compatibility with existing worker gate
- Browser account compatibility
- Devin representation without provider-specific assumptions
- No automatic quota inference
"""

from datetime import datetime, timezone
import pytest

from iabv_v15.domain.models import (
    UniversalResource,
    UniversalResourceSnapshot,
    ResourceKind,
    AuthenticationState,
    AccountStatus,
    QuotaScope,
    utc_now,
)


class TestUniversalResourceConstruction:
    """Test that browser accounts and API credentials can both be represented."""

    def test_browser_account_representation(self):
        """Test that a browser account can be represented as UniversalResource."""
        resource = UniversalResource(
            resource_id="chatgpt_user1_chrome",
            provider="chatgpt",
            tool_id="chatgpt_web",
            resource_kind=ResourceKind.BROWSER_ACCOUNT,
            credential_ref="chatgpt:user1@example.com:session",
            principal_id="user1@example.com",
            principal_kind="email",
            organization_id=None,
            identity_source="browser_session",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.USER,
            quota_remaining=10,
            quota_limit=40,
            routing_eligible=True,
            score=0.9,
            # Compatibility fields
            email="user1@example.com",
            browser="chrome",
            profile="Default",
            has_session=True,
            session_verified_at=utc_now(),
        )

        assert resource.resource_id == "chatgpt_user1_chrome"
        assert resource.provider == "chatgpt"
        assert resource.resource_kind == ResourceKind.BROWSER_ACCOUNT
        assert resource.credential_ref == "chatgpt:user1@example.com:session"
        assert resource.authentication_state == AuthenticationState.AUTHENTICATED
        assert resource.routing_eligible is True
        assert resource.email == "user1@example.com"
        assert resource.browser == "chrome"

    def test_api_credential_representation(self):
        """Test that an API credential can be represented as UniversalResource."""
        resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            principal_id=None,  # Unknown for Devin
            principal_kind=None,
            organization_id=None,  # Unknown for Devin
            identity_source=None,
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.ORGANIZATION,  # Use value constructor
            quota_remaining=0,  # Not available via API
            quota_limit=0,
            routing_eligible=True,
            score=1.0,
            # Compatibility fields (empty for API credentials)
            email="",
            browser="",
            profile="",
            has_session=False,
            session_verified_at=None,
        )

        assert resource.resource_id == "devin_credential_0"
        assert resource.provider == "devin"
        assert resource.resource_kind == ResourceKind.API_CREDENTIAL
        assert resource.credential_ref == "devin:credential_0:DEVIN_API_KEY"
        assert resource.authentication_state == AuthenticationState.AUTHENTICATED
        assert resource.quota_scope == QuotaScope.ORGANIZATION
        assert resource.routing_eligible is True
        assert resource.email == ""  # Empty for API credentials


class TestCredentialOpacity:
    """Test that secret values never appear in resource/routing/trace output."""

    def test_credential_ref_is_opaque(self):
        """Test that credential_ref is an opaque reference, not a secret value."""
        resource = UniversalResource(
            resource_id="test_resource",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="test:credential_0:TEST_API_KEY",  # Opaque reference
        )

        # The credential_ref should be a reference string, not the actual secret
        assert resource.credential_ref == "test:credential_0:TEST_API_KEY"
        # There should be no field containing the actual secret value
        assert not hasattr(resource, 'secret')
        assert not hasattr(resource, 'api_key')
        assert not hasattr(resource, 'token')

    def test_serialization_excludes_secrets(self):
        """Test that serialization does not expose secret values."""
        resource = UniversalResource(
            resource_id="test_resource",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="test:credential_0:TEST_API_KEY",
        )

        data = resource.model_dump(mode='json')

        # Check that credential_ref is present (it's opaque)
        assert 'credential_ref' in data
        assert data['credential_ref'] == "test:credential_0:TEST_API_KEY"

        # Check that no secret fields exist
        assert 'secret' not in data
        assert 'api_key' not in data
        assert 'token' not in data
        assert 'password' not in data


class TestMultipleCredentials:
    """Test that at least two credentials for the same provider can coexist."""

    def test_multiple_devin_credentials(self):
        """Test that multiple Devin credentials can be represented distinctly."""
        credential_a = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            routing_eligible=True,
            score=1.0,
        )

        credential_b = UniversalResource(
            resource_id="devin_credential_1",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_1:IABV_DEVIN_API_KEY",
            authentication_state=AuthenticationState.QUOTA_EXHAUSTED,
            availability_state=AccountStatus.EXHAUSTED,
            routing_eligible=False,
            score=0.0,
        )

        # Credentials are distinct by resource_id and credential_ref
        assert credential_a.resource_id != credential_b.resource_id
        assert credential_a.credential_ref != credential_b.credential_ref
        assert credential_a.authentication_state != credential_b.authentication_state
        assert credential_a.routing_eligible != credential_b.routing_eligible

    def test_multiple_credentials_in_snapshot(self):
        """Test that a snapshot can contain multiple credentials for the same provider."""
        snapshot = UniversalResourceSnapshot(
            entries=[
                UniversalResource(
                    resource_id="devin_credential_0",
                    provider="devin",
                    tool_id="devin_api",
                    resource_kind=ResourceKind.API_CREDENTIAL,
                    credential_ref="devin:credential_0:DEVIN_API_KEY",
                    authentication_state=AuthenticationState.AUTHENTICATED,
                    availability_state=AccountStatus.ACTIVE,
                    routing_eligible=True,
                    score=1.0,
                ),
                UniversalResource(
                    resource_id="devin_credential_1",
                    provider="devin",
                    tool_id="devin_api",
                    resource_kind=ResourceKind.API_CREDENTIAL,
                    credential_ref="devin:credential_1:IABV_DEVIN_API_KEY",
                    authentication_state=AuthenticationState.QUOTA_EXHAUSTED,
                    availability_state=AccountStatus.EXHAUSTED,
                    routing_eligible=False,
                    score=0.0,
                ),
            ],
            active_count=1,
            exhausted_count=1,
            tools_available=["devin_api"],
        )

        assert len(snapshot.entries) == 2
        assert snapshot.active_count == 1
        assert snapshot.exhausted_count == 1
        assert all(e.provider == "devin" for e in snapshot.entries)


class TestDifferentAvailabilityStates:
    """Test different availability states for resources."""

    def test_authenticated_available(self):
        """Test authenticated + available state."""
        resource = UniversalResource(
            resource_id="test",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            routing_eligible=True,
            score=1.0,
        )

        assert resource.authentication_state == AuthenticationState.AUTHENTICATED
        assert resource.availability_state == AccountStatus.ACTIVE
        assert resource.routing_eligible is True

    def test_authenticated_quota_exhausted(self):
        """Test authenticated + quota_exhausted state."""
        resource = UniversalResource(
            resource_id="test",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            authentication_state=AuthenticationState.QUOTA_EXHAUSTED,
            availability_state=AccountStatus.EXHAUSTED,
            block_reason="out_of_quota",
            routing_eligible=False,
            score=0.0,
        )

        assert resource.authentication_state == AuthenticationState.QUOTA_EXHAUSTED
        assert resource.availability_state == AccountStatus.EXHAUSTED
        assert resource.block_reason == "out_of_quota"
        assert resource.routing_eligible is False

    def test_auth_failure(self):
        """Test auth_failure state."""
        resource = UniversalResource(
            resource_id="test",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            authentication_state=AuthenticationState.AUTH_FAILURE,
            availability_state=AccountStatus.EXHAUSTED,
            block_reason="auth_failure",
            routing_eligible=False,
            score=0.0,
        )

        assert resource.authentication_state == AuthenticationState.AUTH_FAILURE
        assert resource.availability_state == AccountStatus.EXHAUSTED
        assert resource.block_reason == "auth_failure"
        assert resource.routing_eligible is False

    def test_unknown_state(self):
        """Test unknown state."""
        resource = UniversalResource(
            resource_id="test",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            authentication_state=AuthenticationState.UNKNOWN,
            availability_state=AccountStatus.UNRESOLVED,
            routing_eligible=False,
            score=0.0,
        )

        assert resource.authentication_state == AuthenticationState.UNKNOWN
        assert resource.availability_state == AccountStatus.UNRESOLVED
        assert resource.routing_eligible is False


class TestRoutingCompatibility:
    """Test that the existing worker gate can consume the universal representation."""

    def test_universal_resource_has_routing_fields(self):
        """Test that UniversalResource has the fields needed for routing."""
        resource = UniversalResource(
            resource_id="test",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            routing_eligible=True,
            score=0.9,
            block_signals=["rate_limited"],
        )

        # These fields are analogous to AccountInventoryEntry fields
        assert hasattr(resource, 'routing_eligible')
        assert hasattr(resource, 'score')
        assert hasattr(resource, 'block_signals')
        assert hasattr(resource, 'availability_state')

    def test_continuity_queue_contract(self):
        """Test that continuity_queue uses the same contract as AccountInventorySnapshot."""
        snapshot = UniversalResourceSnapshot(
            entries=[
                UniversalResource(
                    resource_id="test",
                    provider="test",
                    tool_id="test_api",
                    resource_kind=ResourceKind.API_CREDENTIAL,
                    routing_eligible=True,
                    score=0.9,
                )
            ],
            continuity_queue=[
                UniversalResource(
                    resource_id="test",
                    provider="test",
                    tool_id="test_api",
                    resource_kind=ResourceKind.API_CREDENTIAL,
                    routing_eligible=True,
                    score=0.9,
                )
            ],
            active_count=1,
            exhausted_count=0,
            tools_available=["test_api"],
        )

        # These fields match the AccountInventorySnapshot contract
        assert hasattr(snapshot, 'continuity_queue')
        assert hasattr(snapshot, 'active_count')
        assert hasattr(snapshot, 'exhausted_count')
        assert hasattr(snapshot, 'tools_available')
        assert len(snapshot.continuity_queue) == 1
        assert snapshot.active_count == 1


class TestBrowserCompatibility:
    """Test that existing browser account behaviour remains unchanged."""

    def test_browser_account_preserves_compatibility_fields(self):
        """Test that browser accounts preserve compatibility with AccountInventoryEntry."""
        resource = UniversalResource(
            resource_id="chatgpt_user1",
            provider="chatgpt",
            tool_id="chatgpt_web",
            resource_kind=ResourceKind.BROWSER_ACCOUNT,
            email="user1@example.com",
            browser="chrome",
            profile="Default",
            has_session=True,
            session_verified_at=utc_now(),
            quota_remaining=10,
            quota_limit=40,
            exhausted=False,
            status=AccountStatus.ACTIVE,
            score=0.9,
        )

        # All AccountInventoryEntry fields are present in UniversalResource
        assert resource.email == "user1@example.com"
        assert resource.browser == "chrome"
        assert resource.profile == "Default"
        assert resource.has_session is True
        assert resource.session_verified_at is not None
        assert resource.quota_remaining == 10
        assert resource.quota_limit == 40
        assert resource.exhausted is False
        assert resource.status == AccountStatus.ACTIVE
        assert resource.score == 0.9


class TestDevinRepresentation:
    """Test that Devin credentials are represented without provider-specific account architecture."""

    def test_devin_without_email(self):
        """Test that Devin API credential does not require email."""
        resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            # No email required
            email="",
            principal_id=None,
            organization_id=None,
        )

        assert resource.resource_kind == ResourceKind.API_CREDENTIAL
        assert resource.email == ""
        assert resource.principal_id is None
        assert resource.organization_id is None

    def test_devin_without_browser(self):
        """Test that Devin API credential does not require browser/profile."""
        resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            # No browser/profile required
            browser="",
            profile="",
            has_session=False,
        )

        assert resource.browser == ""
        assert resource.profile == ""
        assert resource.has_session is False

    def test_devin_quota_scope_organization(self):
        """Test that Devin quota scope is declared as ORGANIZATION."""
        resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            quota_scope=QuotaScope.ORGANIZATION,  # Use value constructor
        )

        assert resource.quota_scope == QuotaScope.ORGANIZATION
        assert resource.quota_scope.value == "organization"


class TestNoQuotaInference:
    """Test that two Devin credentials are not automatically treated as two independent quotas."""

    def test_two_credentials_same_organization_scope(self):
        """Test that two credentials share the same ORGANIZATION quota scope."""
        credential_a = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            quota_scope=QuotaScope.ORGANIZATION,  # Use value constructor
        )

        credential_b = UniversalResource(
            resource_id="devin_credential_1",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_1:IABV_DEVIN_API_KEY",
            quota_scope=QuotaScope.ORGANIZATION,  # Use value constructor
        )

        # Both declare ORGANIZATION scope, not CREDENTIAL scope
        assert credential_a.quota_scope == QuotaScope.ORGANIZATION
        assert credential_b.quota_scope == QuotaScope.ORGANIZATION

        # They do NOT automatically get independent quotas
        assert credential_a.quota_remaining == 0
        assert credential_b.quota_remaining == 0
        assert credential_a.quota_limit == 0
        assert credential_b.quota_limit == 0

    def test_quota_scope_must_be_explicit(self):
        """Test that quota_scope defaults to UNKNOWN, not inferred."""
        resource = UniversalResource(
            resource_id="test",
            provider="test",
            tool_id="test_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
        )

        # quota_scope defaults to UNKNOWN, not automatically inferred
        assert resource.quota_scope == QuotaScope.UNKNOWN
