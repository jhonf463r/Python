"""Static contract tests for Entra auth; this tranche does not execute them."""
from __future__ import annotations

import asyncio
import json
import time

import pytest

pytest.importorskip("mcp")
jwt = pytest.importorskip("jwt")
httpx = pytest.importorskip("httpx")
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


@pytest.mark.parametrize(
    "resource_url",
    [
        "https://MCP.example.test/iabv",
        "https://mcp.example.test:443/iabv",
        "https://mcp.example.test:8443/iabv",
        "https://mcp.example.test",
        "https://mcp.example.test/iabv?mode=1",
        "https://mcp.example.test/iabv#fragment",
    ],
)
def test_auth_config_rejects_noncanonical_url_components(
    monkeypatch: pytest.MonkeyPatch,
    resource_url: str,
) -> None:
    _clear_auth_env(monkeypatch)
    values = {
        "IABV_ENTRA_TENANT_ID": "11111111-1111-4111-8111-111111111111",
        "IABV_ENTRA_API_CLIENT_ID": "22222222-2222-4222-8222-222222222222",
        "IABV_ENTRA_OWNER_OBJECT_ID": "33333333-3333-4333-8333-333333333333",
        "IABV_ENTRA_REQUIRED_APP_ROLE": "IABV.Owner",
        "IABV_ENTRA_ALLOWED_CLIENT_IDS": "44444444-4444-4444-8444-444444444444",
        "IABV_ENTRA_APPLICATION_ID_URI": resource_url,
        "IABV_MCP_RESOURCE_SERVER_URL": resource_url,
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(EntraConfigurationError):
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


def _signed_token(
    config: EntraAuthConfig,
    private_key: object,
    *,
    token_kid: str = "test-key",
    **claim_overrides: object,
) -> str:
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
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": token_kid})


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


def test_malformed_wrong_type_or_wrong_algorithm_token_is_denied() -> None:
    config = _config()
    verifier = _StaticKeyVerifier(config, object())
    assert asyncio.run(verifier.verify_token(None)) is None  # type: ignore[arg-type]
    assert asyncio.run(verifier.verify_token("not.a.jwt")) is None
    wrong_algorithm = jwt.encode(
        {"aud": config.api_client_id},
        "synthetic-test-key",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )
    assert asyncio.run(verifier.verify_token(wrong_algorithm)) is None




class _MockResponse:
    def __init__(self, payload: object = None, *, status_code: int = 200, json_error: Exception | None = None) -> None:
        self._payload = payload
        self.status_code = status_code
        self._json_error = json_error

    def raise_for_status(self) -> None:
        if self.status_code < 200 or self.status_code >= 300:
            raise httpx.HTTPStatusError(
                "simulated HTTP response failure",
                request=httpx.Request("GET", "https://login.microsoftonline.com/test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> object:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


def _mock_discovery_http(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[object],
) -> tuple[list[str], list[dict[str, object]]]:
    requests: list[str] = []
    client_options: list[dict[str, object]] = []

    class FakeAsyncClient:
        def __init__(self, **kwargs: object) -> None:
            client_options.append(kwargs)

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, url: str) -> object:
            requests.append(url)
            item = responses.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item

    monkeypatch.setattr(
        "iabv_v15.infra.mcp.entra_token_verifier.httpx.AsyncClient",
        FakeAsyncClient,
    )
    return requests, client_options


def _jwks_key(public_key: object, kid: str) -> dict[str, object]:
    entry = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    entry.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return entry


def _discovery(config: EntraAuthConfig, *, issuer: str | None = None, jwks_uri: str | None = None) -> _MockResponse:
    return _MockResponse({
        "issuer": issuer or config.issuer_url,
        "jwks_uri": jwks_uri or f"https://login.microsoftonline.com/{config.tenant_id}/discovery/v2.0/keys",
    })


def test_oidc_discovery_and_jwks_fetch_are_tenant_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    requests, options = _mock_discovery_http(
        monkeypatch,
        [
            _discovery(config),
            _MockResponse({"keys": [_jwks_key(private_key.public_key(), "test-key")]}),
        ],
    )
    verifier = EntraTokenVerifier(config)
    resolved = asyncio.run(verifier._get_signing_key("test-key"))
    assert resolved.public_numbers() == private_key.public_key().public_numbers()
    assert requests == [
        verifier._metadata_url,
        f"https://login.microsoftonline.com/{config.tenant_id}/discovery/v2.0/keys",
    ]
    assert options == [{"timeout": 5.0, "follow_redirects": False, "trust_env": False}]


@pytest.mark.parametrize(
    ("metadata_response", "remaining_responses", "expected_requests"),
    [
        (lambda config: _discovery(config, issuer="https://wrong.example/issuer"), [], 1),
        (lambda config: _discovery(config, jwks_uri="http://attacker.example/keys"), [], 1),
        (lambda _config: _MockResponse(status_code=302), [], 1),
        (lambda _config: httpx.ReadTimeout("simulated timeout"), [], 1),
        (lambda config: _discovery(config), [_MockResponse({"keys": []})], 2),
        (lambda config: _discovery(config), [_MockResponse(json_error=ValueError("invalid JSON"))], 2),
    ],
)
def test_oidc_discovery_and_jwks_failures_are_denied(
    monkeypatch: pytest.MonkeyPatch,
    metadata_response,
    remaining_responses: list[object],
    expected_requests: int,
) -> None:  # type: ignore[no-untyped-def]
    config = _config()
    response = metadata_response(config)
    requests, options = _mock_discovery_http(
        monkeypatch,
        [response, *remaining_responses],
    )
    verifier = EntraTokenVerifier(config)
    token = _signed_token(
        config,
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )
    assert asyncio.run(verifier.verify_token(token)) is None
    assert len(requests) == expected_requests
    assert options and options[0]["follow_redirects"] is False
    # Redirect destinations are never followed; only tenant-pinned URLs are requested.
    assert all(url.startswith("https://login.microsoftonline.com/") for url in requests)


def test_unknown_kid_forces_one_jwks_refresh_for_key_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config()
    old_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_token = _signed_token(config, new_key, token_kid="rotated-key")
    requests, _ = _mock_discovery_http(
        monkeypatch,
        [
            _discovery(config),
            _MockResponse({"keys": [_jwks_key(old_key.public_key(), "old-key")]}),
            _discovery(config),
            _MockResponse({"keys": [_jwks_key(new_key.public_key(), "rotated-key")]}),
        ],
    )
    verifier = EntraTokenVerifier(config)
    access = asyncio.run(verifier.verify_token(new_token))
    assert access is not None
    assert len(requests) == 4


def test_removed_signing_key_remains_accepted_until_cache_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config()
    old_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    old_token = _signed_token(config, old_key, token_kid="old-key")
    replacement_jwks = _MockResponse({"keys": [_jwks_key(new_key.public_key(), "new-key")]})
    requests, _ = _mock_discovery_http(
        monkeypatch,
        [
            _discovery(config),
            _MockResponse({"keys": [_jwks_key(old_key.public_key(), "old-key")]}),
            _discovery(config),
            replacement_jwks,
            _discovery(config),
            replacement_jwks,
        ],
    )
    now = [100.0]
    monkeypatch.setattr("iabv_v15.infra.mcp.entra_token_verifier.time.monotonic", lambda: now[0])
    verifier = EntraTokenVerifier(config, jwks_cache_seconds=60)
    assert asyncio.run(verifier.verify_token(old_token)) is not None
    # Key removal is not observed while the cached JWKS is fresh.
    assert asyncio.run(verifier.verify_token(old_token)) is not None
    assert len(requests) == 2

    # The configured cache floor is 60 seconds; after expiry, missing old kid
    # forces a second refresh and the token is rejected. This is not a mandate
    # revocation system and does not authorize any MCP operation.
    now[0] = 161.0
    assert asyncio.run(verifier.verify_token(old_token)) is None
    assert len(requests) == 6


def test_expired_jwks_cache_refresh_failure_does_not_reuse_removed_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    old_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    old_token = _signed_token(config, old_key, token_kid="old-key")
    requests, _ = _mock_discovery_http(
        monkeypatch,
        [
            _discovery(config),
            _MockResponse({"keys": [_jwks_key(old_key.public_key(), "old-key")]}),
            _discovery(config),
            _MockResponse(status_code=503),
        ],
    )
    now = [100.0]
    monkeypatch.setattr("iabv_v15.infra.mcp.entra_token_verifier.time.monotonic", lambda: now[0])
    verifier = EntraTokenVerifier(config, jwks_cache_seconds=60)
    assert asyncio.run(verifier.verify_token(old_token)) is not None

    now[0] = 161.0
    # A failed refresh denies authentication; the stale cached key is not a fallback.
    assert asyncio.run(verifier.verify_token(old_token)) is None
    assert len(requests) == 4
