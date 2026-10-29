"""Tenant-pinned Microsoft Entra access-token verification for the MCP resource server.

This module intentionally implements authentication only. A valid access token and
Owner app role do not establish IABV G1/G2/G3 or authorize governed repository reads.
All configuration is external and incomplete configuration fails closed.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import time
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit
from typing import Any

import httpx
import jwt
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings

logger = logging.getLogger(__name__)

_ENV_NAMES = (
    "IABV_ENTRA_TENANT_ID",
    "IABV_ENTRA_API_CLIENT_ID",
    "IABV_ENTRA_OWNER_OBJECT_ID",
    "IABV_ENTRA_REQUIRED_APP_ROLE",
    "IABV_ENTRA_ALLOWED_CLIENT_IDS",
    "IABV_ENTRA_APPLICATION_ID_URI",
    "IABV_MCP_RESOURCE_SERVER_URL",
)


class EntraConfigurationError(ValueError):
    """Required Entra configuration is absent, malformed, or inconsistent."""


@dataclass(frozen=True)
class EntraAuthConfig:
    tenant_id: str
    api_client_id: str
    owner_object_id: str
    required_app_role: str
    allowed_client_ids: frozenset[str]
    application_id_uri: str
    resource_server_url: str

    @property
    def issuer_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"


def _required_guid(env_name: str, value: str) -> str:
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise EntraConfigurationError(f"{env_name} must contain a GUID.") from exc


def _validate_https_resource_url(value: str, env_name: str) -> str:
    value = value.strip()
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise EntraConfigurationError(f"{env_name} contains an invalid port.") from exc
    if port is not None:
        raise EntraConfigurationError(
            f"{env_name} must omit an explicit port to preserve exact URL identity."
        )
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.hostname.lower() in {"localhost", "localhost.localdomain"}
        or parsed.hostname.lower().endswith(".localhost")
        or parsed.hostname.lower().endswith(".local")
    ):
        raise EntraConfigurationError(
            f"{env_name} must be the approved canonical HTTPS resource URL "
            "without credentials, query, or fragment."
        )
    canonical_url = f"https://{parsed.hostname or ''}{parsed.path or '/'}"
    if value != canonical_url:
        raise EntraConfigurationError(
            f"{env_name} must use a canonical URL spelling with exact host and path components."
        )
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise EntraConfigurationError(f"{env_name} must use the approved DNS host, not an IP literal.")
    return value


def load_entra_auth_config_from_environment() -> EntraAuthConfig | None:
    """Load complete explicit configuration; return None only when wholly absent.

    A partially populated environment is a configuration error, never permission to
    fall back to an unauthenticated HTTP server.
    """
    values = {name: (os.environ.get(name) or "").strip() for name in _ENV_NAMES}
    if not any(values.values()):
        return None
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise EntraConfigurationError("Incomplete Entra/MCP configuration; missing: " + ", ".join(missing))

    tenant_id = _required_guid("IABV_ENTRA_TENANT_ID", values["IABV_ENTRA_TENANT_ID"])
    api_client_id = _required_guid("IABV_ENTRA_API_CLIENT_ID", values["IABV_ENTRA_API_CLIENT_ID"])
    owner_object_id = _required_guid("IABV_ENTRA_OWNER_OBJECT_ID", values["IABV_ENTRA_OWNER_OBJECT_ID"])
    role = values["IABV_ENTRA_REQUIRED_APP_ROLE"]
    if not role or len(role) > 128 or any(ch.isspace() for ch in role):
        raise EntraConfigurationError("IABV_ENTRA_REQUIRED_APP_ROLE must be a non-empty app-role value.")

    allowed_clients = frozenset(
        _required_guid("IABV_ENTRA_ALLOWED_CLIENT_IDS", item.strip())
        for item in values["IABV_ENTRA_ALLOWED_CLIENT_IDS"].split(",")
        if item.strip()
    )
    if not allowed_clients:
        raise EntraConfigurationError("IABV_ENTRA_ALLOWED_CLIENT_IDS must contain at least one client GUID.")
    if api_client_id in allowed_clients:
        raise EntraConfigurationError("The API application ID must not also be an allowed OAuth client ID.")

    app_id_uri = _validate_https_resource_url(
        values["IABV_ENTRA_APPLICATION_ID_URI"], "IABV_ENTRA_APPLICATION_ID_URI"
    )
    resource_url = _validate_https_resource_url(
        values["IABV_MCP_RESOURCE_SERVER_URL"], "IABV_MCP_RESOURCE_SERVER_URL"
    )
    # The OAuth resource/Application ID URI is a URL identity. The token's v2 aud
    # claim is validated separately against api_client_id below.
    if app_id_uri != resource_url:
        raise EntraConfigurationError(
            "IABV_ENTRA_APPLICATION_ID_URI must exactly equal IABV_MCP_RESOURCE_SERVER_URL."
        )

    return EntraAuthConfig(
        tenant_id=tenant_id,
        api_client_id=api_client_id,
        owner_object_id=owner_object_id,
        required_app_role=role,
        allowed_client_ids=allowed_clients,
        application_id_uri=app_id_uri,
        resource_server_url=resource_url,
    )


class EntraTokenVerifier:
    """Validate an Entra v2 access token for this exact API and configured Owner.

    Discovery and JWKS URLs are tenant-pinned. Redirects and arbitrary token-provided
    issuers/key URLs are not followed. Roles are exposed to MCP as the SDK's scope
    collection solely so AuthSettings.required_scopes can enforce the configured app
    role. This verifier is not a substitute for the independent G1/G2/G3 gates.
    """

    def __init__(self, config: EntraAuthConfig, *, jwks_cache_seconds: int = 3600) -> None:
        if not isinstance(config, EntraAuthConfig):
            raise TypeError("EntraTokenVerifier requires the immutable EntraAuthConfig snapshot.")
        self._config = config
        self._issuer_url = config.issuer_url
        self._metadata_url = (
            f"https://login.microsoftonline.com/{config.tenant_id}/v2.0/.well-known/openid-configuration"
        )
        self._jwks_cache_seconds = max(60, min(int(jwks_cache_seconds), 24 * 60 * 60))
        self._jwks_by_kid: dict[str, dict[str, Any]] = {}
        self._jwks_expires_at = 0.0
        self._jwks_lock = asyncio.Lock()

    _IMMUTABLE_AUTH_FIELDS = frozenset(
        {"_config", "_issuer_url", "_metadata_url", "_jwks_cache_seconds"}
    )

    def __setattr__(self, name: str, value: Any) -> None:
        if name in EntraTokenVerifier._IMMUTABLE_AUTH_FIELDS and hasattr(self, name):
            raise AttributeError(f"{name} is immutable after verifier construction.")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if name in EntraTokenVerifier._IMMUTABLE_AUTH_FIELDS:
            raise AttributeError(f"{name} is immutable after verifier construction.")
        object.__delattr__(self, name)

    @property
    def config(self) -> EntraAuthConfig:
        """Read-only reference to the frozen configuration accepted by this verifier."""
        return self._config

    async def _load_jwks(self) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        if self._jwks_by_kid and now < self._jwks_expires_at:
            return self._jwks_by_kid

        async with self._jwks_lock:
            now = time.monotonic()
            if self._jwks_by_kid and now < self._jwks_expires_at:
                return self._jwks_by_kid

            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False, trust_env=False) as client:
                metadata_response = await client.get(self._metadata_url)
                metadata_response.raise_for_status()
                metadata = metadata_response.json()
                if metadata.get("issuer") != self._issuer_url:
                    raise jwt.InvalidIssuerError("Tenant discovery issuer mismatch.")

                jwks_url = metadata.get("jwks_uri")
                parsed_jwks = urlsplit(jwks_url or "")
                if (
                    parsed_jwks.scheme != "https"
                    or parsed_jwks.hostname != "login.microsoftonline.com"
                    or parsed_jwks.username is not None
                    or parsed_jwks.password is not None
                    or parsed_jwks.query
                    or parsed_jwks.fragment
                ):
                    raise jwt.InvalidTokenError("Unexpected Entra JWKS endpoint.")

                jwks_response = await client.get(jwks_url)
                jwks_response.raise_for_status()
                jwks = jwks_response.json()

            entries = jwks.get("keys")
            if not isinstance(entries, list):
                raise jwt.InvalidTokenError("Invalid JWKS document.")
            by_kid: dict[str, dict[str, Any]] = {}
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                kid = entry.get("kid")
                if (
                    isinstance(kid, str)
                    and entry.get("kty") == "RSA"
                    and entry.get("use", "sig") == "sig"
                    and entry.get("alg", "RS256") == "RS256"
                ):
                    by_kid[kid] = entry
            if not by_kid:
                raise jwt.InvalidTokenError("No usable signing keys in Entra JWKS.")

            self._jwks_by_kid = by_kid
            self._jwks_expires_at = time.monotonic() + self._jwks_cache_seconds
            return by_kid

    async def _get_signing_key(self, kid: str) -> Any:
        keys = await self._load_jwks()
        key_data = keys.get(kid)
        if key_data is None:
            # Force one refresh to support legitimate Entra signing-key rotation.
            self._jwks_expires_at = 0.0
            keys = await self._load_jwks()
            key_data = keys.get(kid)
        if key_data is None:
            raise jwt.InvalidTokenError("Unknown signing key identifier.")
        return jwt.PyJWK.from_dict(key_data, algorithm="RS256").key

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return SDK access info only for a valid, role-bearing Owner token."""
        try:
            if not isinstance(token, str) or not token:
                return None
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                return None

            signing_key = await self._get_signing_key(header["kid"])
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.config.api_client_id,
                issuer=self._issuer_url,
                options={
                    "require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid", "ver"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
                leeway=0,
            )

            # Do not accept a list audience or a token for a different Entra API.
            if claims.get("aud") != self.config.api_client_id:
                return None
            if claims.get("iss") != self._issuer_url or claims.get("tid") != self.config.tenant_id:
                return None
            if claims.get("ver") != "2.0" or claims.get("oid") != self.config.owner_object_id:
                return None

            # ID tokens are not API bearer tokens. Reject their common token-only markers;
            # the tenant, audience and app-role checks below remain mandatory as well.
            if claims.get("nonce") is not None or claims.get("at_hash") is not None:
                return None
            # This verifier accepts v2 tokens only; azp is the expected client-id claim.
            client_id = claims.get("azp")
            if not isinstance(client_id, str):
                return None
            try:
                client_id = str(uuid.UUID(client_id))
            except ValueError:
                return None
            if client_id not in self.config.allowed_client_ids:
                return None

            roles = claims.get("roles")
            if not isinstance(roles, list) or self.config.required_app_role not in roles:
                return None
            exp = claims.get("exp")
            if not isinstance(exp, (int, float)):
                return None

            # SDK resource comparison is intentionally disabled in AuthSettings
            # because Entra v2 aud is the API client GUID, not the resource URL.
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=[self.config.required_app_role],
                expires_at=int(exp),
                resource=self.config.api_client_id,
                subject=self.config.owner_object_id,
                claims={
                    "iss": self._issuer_url,
                    "tid": self.config.tenant_id,
                    "oid": self.config.owner_object_id,
                    "aud": self.config.api_client_id,
                    "ver": "2.0",
                },
            )
        except Exception:
            # Never log tokens, headers, raw claims, or exception text from untrusted tokens.
            logger.warning("Entra access-token verification denied.")
            return None


def build_entra_auth_from_environment() -> tuple[EntraTokenVerifier, AuthSettings] | None:
    """Create SDK auth wiring; missing config is distinguishable from partial config."""
    config = load_entra_auth_config_from_environment()
    if config is None:
        return None

    verifier = EntraTokenVerifier(config)
    auth_settings = AuthSettings(
        issuer_url=config.issuer_url,
        resource_server_url=config.resource_server_url,
        required_scopes=[config.required_app_role],
        validate_token_resource=False,
    )
    return verifier, auth_settings
