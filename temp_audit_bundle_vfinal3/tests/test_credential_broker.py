from __future__ import annotations

import pytest

from iabv_v15.domain.models import SecretReference
from iabv_v15.services.security.credential_broker import CredentialBroker, CredentialRecord


class FakeVault:
    """SecretVault double que siempre reporta disponible y almacena en memoria."""

    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self.storage: dict[str, str] = {}

    @property
    def available(self) -> bool:
        return self._available

    def put_secret(self, domain, account, field_role, secret):  # noqa: D401
        key = f"{domain}:{account}:{field_role}"
        reference = SecretReference(
            domain=domain,
            account=account,
            field_role=field_role,
            key=key,
            available=self._available,
        )
        if not self._available:
            return reference
        self.storage[key] = secret
        return reference

    def resolve_reference(self, reference):
        if not self._available:
            return None
        return self.storage.get(reference.key)


def test_request_invokes_registered_prompt_handler() -> None:
    vault = FakeVault()
    broker = CredentialBroker(secret_vault=vault)
    received: list[dict] = []
    broker.register_prompt_handler(received.append)

    broker.request("wplay.com.co", reason="Login requerido", username_hint="user123")

    assert len(received) == 1
    payload = received[0]
    assert payload["domain"] == "wplay.com.co"
    assert payload["reason"] == "Login requerido"
    assert payload["username_hint"] == "user123"


def test_request_without_handler_is_noop() -> None:
    broker = CredentialBroker(secret_vault=FakeVault())
    # No debe lanzar aunque no haya handler registrado.
    broker.request("wplay.com.co", reason="Login", username_hint=None)


def test_accept_persists_credential_in_vault() -> None:
    vault = FakeVault()
    broker = CredentialBroker(secret_vault=vault)

    assert broker.needs("mercadolibre.com")
    broker.accept("mercadolibre.com", "faber", "s3cret!")

    record = broker.get("mercadolibre.com")
    assert isinstance(record, CredentialRecord)
    assert record.domain == "mercadolibre.com"
    assert record.username == "faber"
    assert record.secret == "s3cret!"
    assert not broker.needs("mercadolibre.com")


def test_get_does_not_repeat_prompt_handler() -> None:
    vault = FakeVault()
    broker = CredentialBroker(secret_vault=vault)
    prompts: list[dict] = []
    broker.register_prompt_handler(prompts.append)

    broker.accept("mercadolibre.com", "faber", "s3cret!")
    broker.get("mercadolibre.com")
    broker.get("mercadolibre.com")

    assert prompts == []  # get() nunca repregunta, solo request() emite prompts


def test_fallback_cache_when_vault_unavailable() -> None:
    vault = FakeVault(available=False)
    broker = CredentialBroker(secret_vault=vault)

    broker.accept("wplay.com.co", "faber", "pass")
    record = broker.get("wplay.com.co")

    assert record is not None
    assert record.secret == "pass"


def test_forget_clears_domain() -> None:
    vault = FakeVault()
    broker = CredentialBroker(secret_vault=vault)

    broker.accept("wplay.com.co", "faber", "pass")
    assert broker.get("wplay.com.co") is not None
    broker.forget("wplay.com.co")
    assert broker.get("wplay.com.co") is None
    assert broker.needs("wplay.com.co")
