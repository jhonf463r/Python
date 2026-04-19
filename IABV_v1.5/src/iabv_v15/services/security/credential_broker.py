"""CredentialBroker: backend que solicita, persiste y entrega credenciales.

Expone una API sincrona simple (needs/get/request/accept) sobre SecretVault.
La capa UI se conecta via register_prompt_handler y recibe la solicitud como
un diccionario listo para emitir por la senal credentialPromptRequested del
ViewModel correspondiente. La respuesta del usuario vuelve al broker via
accept(), tras lo cual get() deja de reabrir el dialogo para el mismo dominio.

No crea otro cerebro ni toma decisiones de ruta; solo mediaciona credenciales.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional

from iabv_v15.domain.models import SecretReference
from iabv_v15.services.capture.secret_vault import SecretVault


PromptHandler = Callable[[dict], None]


@dataclass(frozen=True)
class CredentialRecord:
    """Credencial resuelta para un dominio."""

    domain: str
    username: str
    secret: str


class CredentialBroker:
    """Coordina acceso y solicitud de credenciales respaldado por SecretVault."""

    FIELD_ROLE = "password"

    def __init__(self, *, secret_vault: SecretVault) -> None:
        self._vault = secret_vault
        self._handler: Optional[PromptHandler] = None
        self._lock = threading.RLock()
        self._domain_accounts: dict[str, str] = {}
        # Fallback cache en memoria cuando keyring no esta disponible.
        self._fallback_cache: dict[str, tuple[str, str]] = {}

    # ---- public API -------------------------------------------------

    def register_prompt_handler(self, handler: PromptHandler) -> None:
        """Registra el callback que emite credentialPromptRequested en la UI."""
        with self._lock:
            self._handler = handler

    def needs(self, domain: str) -> bool:
        """True cuando todavia no hay credencial valida para el dominio."""
        return self.get(domain) is None

    def get(self, domain: str) -> CredentialRecord | None:
        """Devuelve la credencial sin repreguntar al usuario si ya existe."""
        with self._lock:
            username = self._domain_accounts.get(domain)
            fallback = self._fallback_cache.get(domain)
        if username is None:
            if fallback is not None:
                f_user, f_secret = fallback
                return CredentialRecord(domain=domain, username=f_user, secret=f_secret)
            return None
        reference = SecretReference(
            domain=domain,
            account=username,
            field_role=self.FIELD_ROLE,
            key=f"{domain}:{username}:{self.FIELD_ROLE}",
            available=self._vault.available,
        )
        secret = self._vault.resolve_reference(reference)
        if secret is not None:
            return CredentialRecord(domain=domain, username=username, secret=secret)
        if fallback is not None:
            f_user, f_secret = fallback
            return CredentialRecord(domain=domain, username=f_user, secret=f_secret)
        return None

    def request(self, domain: str, reason: str, username_hint: str | None = None) -> None:
        """Emite la solicitud hacia la UI via el handler registrado."""
        with self._lock:
            handler = self._handler
        if handler is None:
            return
        payload = {
            "domain": domain,
            "reason": reason,
            "username_hint": username_hint or "",
        }
        handler(payload)

    def accept(self, domain: str, username: str, secret: str) -> None:
        """Persiste una credencial entregada por el usuario."""
        reference = self._vault.put_secret(
            domain=domain,
            account=username,
            field_role=self.FIELD_ROLE,
            secret=secret,
        )
        with self._lock:
            self._domain_accounts[domain] = username
            if reference.available:
                self._fallback_cache.pop(domain, None)
            else:
                self._fallback_cache[domain] = (username, secret)

    def forget(self, domain: str) -> None:
        """Olvida la credencial para el dominio dado (util en tests y rotacion)."""
        with self._lock:
            self._domain_accounts.pop(domain, None)
            self._fallback_cache.pop(domain, None)
