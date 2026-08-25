from __future__ import annotations

from iabv_v15.domain.models import SecretReference

try:  # pragma: no cover - depends on runtime backend
    import keyring
except ImportError:  # pragma: no cover - optional runtime dependency
    keyring = None


class SecretVault:
    def __init__(self, service_name: str = "IABV_v15") -> None:
        self.service_name = service_name

    @property
    def available(self) -> bool:
        return keyring is not None

    def put_secret(self, domain: str, account: str, field_role: str, secret: str) -> SecretReference:
        key = f"{domain}:{account}:{field_role}"
        reference = SecretReference(
            domain=domain,
            account=account,
            field_role=field_role,
            key=key,
            available=self.available,
        )
        if not self.available:
            return reference.model_copy(update={"available": False})
        try:
            keyring.set_password(self.service_name, key, secret)
            return reference
        except Exception:
            return reference.model_copy(update={"available": False})

    def resolve_reference(self, reference: SecretReference) -> str | None:
        if not self.available:
            return None
        try:
            return keyring.get_password(self.service_name, reference.key)
        except Exception:
            return None
