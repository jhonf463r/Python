"""Static contract tests for Entra auth; this tranche does not execute them."""
from __future__ import annotations

import asyncio
import time

import pytest

pytest.importorskip("mcp")
jwt = pytest.importorskip("jwt")
pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric import rsa

from iabv_v15.infra.mcp.entra_token_verifier import (
    EntraAuthConfig,
    EntraConfigurationError,
    EntraTokenVerifier,
    build_entra_auth_from_environment,
    load_entra_auth_config_from_environment,
)


ENV_NAMES = (
    "IABV_ENTRA_TENANT_ID",
    "IABV_ENTRA_API_CLIENT_ID",
    "IABV_ENTRA_OWNER_OBJECT_ID",
    "IABV_ENTRA_REQUIRED_APP_ROLE",
    "IABV_ENTRA_ALLOWED_CLIENT_IDS",
    "IABV_ENTRA_APPLICATION_ID_URI",
    "IABV_MCP_RESOURCE_SERVER_URL",
)


def _clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _config() -> EntraAuthConfig:
    return EntraAuthConfig(
        tenant_id="11111111-1111-4111-8111-111111111111",
        api_client_id="22222222-2222-4222-8222-222222222222",
        owner_object_id="33333333-3333-4333-8333-333333333333",
        required_app_role="IABV.Owner",
        allowed_client_ids=frozenset({"44444444-4444-4444-8444-444444444444"}),
        application_id_uri="https://mcp.example.test/iabv",
        resource_server_url="https://mcp.example.test/iabv",
    )


def test_auth_config_is_absent_only_when_all_variables_are_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)
    assert load_entra_auth_config_from_environment() is None
    monkeypatch.setenv("IABV_ENTRA_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    with pytest.raises(EntraConfigurationError, match="Incomplete"):
        load_entra_auth_config_from_environment()


def test_auth_config_requires_exact_resource_and_application_id_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)
    values = {
        "IABV_ENTRA_TENANT_ID": "11111111-1111-4111-8111-111111111111",
        "IABV_ENTRA_API_CLIENT_ID": "22222222-2222-4222-8222-222222222222",
        "IABV_ENTRA_OWNER_OBJECT_ID": "33333333-3333-4333-8333-333333333333",
        "IABV_ENTRA_REQUIRED_APP_ROLE": "IABV.Owner",
        "IABV_ENTRA_ALLOWED_CLIENT_IDS": "44444444-4444-4444-8444-444444444444",
        "IABV_ENTRA_APPLICATION_ID_URI": "https://mcp.example.test/iabv",
        "IABV_MCP_RESOURCE_SERVER_URL": "https://mcp.example.test/iabv/",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(EntraConfigurationError, match="exactly equal"):
        load_entra_auth_config_from_environment()


def test_sdk_auth_settings_keep_resource_url_separate_from_aud_guid(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_env(monkeypatch)
    values = {
        "IABV_ENTRA_TENANT_ID": "11111111-1111-4111-8111-111111111111",
        "IABV_ENTRA_API_CLIENT_ID": "22222222-2222-4222-8222-222222222222",
        "IABV_ENTRA_OWNER_OBJECT_ID": "33333333-3333-4333-8333-333333333333",
        "IABV_ENTRA_REQUIRED_APP_ROLE": "IABV.Owner",
        "IABV_ENTRA_ALLOWED_CLIENT_IDS": "44444444-4444-4444-8444-444444444444",
        "IABV_ENTRA_APPLICATION_ID_URI": "https://mcp.example.test/iabv",
        "IABV_MCP_RESOURCE_SERVER_URL": "https://mcp.example.test/iabv",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    verifier, settings = build_entra_auth_from_environment()
    assert isinstance(verifier, EntraTokenVerifier)
    assert str(settings.resource_server_url).rstrip("/") == "https://mcp.example.test/iabv"
    assert settings.validate_token_resource is False
    assert settings.required_scopes == ["IABV.Owner"]


class _StaticKeyVerifier(EntraTokenVerifier):
    def __init__(self, config: EntraAuthConfig, key: object) -> None:
        super().__init__(config)
        self._test_key = key

    async def _get_signing_key(self, kid: str) -> object:
        if kid != "test-key":
            raise jwt.InvalidTokenError("unexpected key")
        return self._test_key


def _signed_token(config: EntraAuthConfig, private_key: object, **claim_overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": config.issuer_url,
        "aud": config.api_client_id,
        "tid": config.tenant_id,
        "oid": config.owner_object_id,
        "ver": "2.0",
        "azp": next(iter(config.allowed_client_ids)),
        "roles": [config.required_app_role],
        "iat": now - 1,
        "nbf": now - 1,
        "exp": now + 300,
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def test_valid_tenant_pinned_owner_token_is_accepted_without_network() -> None:
    config = _config()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = _StaticKeyVerifier(config, private_key.public_key())
    token = _signed_token(config, private_key)
    access = asyncio.run(verifier.verify_token(token))
    assert access is not None
    assert access.client_id in config.allowed_client_ids
    assert access.resource == config.api_client_id
    assert access.scopes == [config.required_app_role]
    assert (access.claims or {}).get("aud") == config.api_client_id


@pytest.mark.parametrize('overrides', [
    {"aud": "55555555-5555-4555-8555-555555555555"},
    {"tid": "66666666-6666-4666-8666-666666666666"},
    {"oid": "77777777-7777-4777-8777-777777777777"},
    {"azp": "88888888-8888-4888-8888-888888888888"},
    {"roles": ["IABV.Reader"]},
    {"ver": "1.0"},
    {"nonce": "id-token-nonce"},
    {"at_hash": "id-token-hash"},
    {"nbf": int(time.time()) + 600},
    {"exp": int(time.time()) - 600},
])
def test_wrong_audience_tenant_owner_client_role_or_version_is_denied(overrides: dict[str, object]) -> None:
    config = _config()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = _StaticKeyVerifier(config, private_key.public_key())
    token = _signed_token(config, private_key, **overrides)
    assert asyncio.run(verifier.verify_token(token)) is None


def test_malformed_or_wrong_algorithm_token_is_denied() -> None:
    config = _config()
    verifier = _StaticKeyVerifier(config, object())
    assert asyncio.run(verifier.verify_token("not.a.jwt")) is None
    wrong_algorithm = jwt.encode(
        {"aud": config.api_client_id},
        "synthetic-test-key",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )
    assert asyncio.run(verifier.verify_token(wrong_algorithm)) is None

