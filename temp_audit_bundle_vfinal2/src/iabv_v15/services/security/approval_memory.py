"""ApprovalMemory: aprende politicas explicitas de aprobacion humana.

Se enchufa a `HumanApprovalBroker` via `set_pre_approver` y
`register_post_resolve_handler` sin que el broker la conozca directamente.

Reglas clave (AGENTS.md + intencion del usuario):
    - Solo aprende por orden explicita (`remember(...)`). Nunca auto-aprende
      porque el humano haya aprobado una vez: aprobar manual no implica
      "quiero que lo hagas automatico desde ahora".
    - Solo aplica a decisiones puras si/no. Si el `ApprovalRequest` incluye
      `payload_schema` no vacio (ej. recolectar un token) NO se auto-resuelve
      porque la memoria no tiene el valor delicado y no debe inventarlo.
    - Respeta TTL por politica. Las politicas expiradas no matchean y se
      barren en la proxima llamada.
    - Persiste en disco (`data/evolution/approval_policies/policies.json`)
      de forma atomica. No mantiene una memoria paralela: espeja
      exactamente la decision registrada por el usuario.
    - Matching es "subset exacto": el `scope_pattern` de la politica debe
      ser un subconjunto de `request.scope` con valores iguales. Entre
      varias politicas que apliquen gana la mas especifica (mas claves).
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional

from iabv_v15.services.security.human_approval_broker import (
    ApprovalRequest,
    ApprovalResult,
)


DECISION_APPROVED = "approved"
DECISION_REJECTED = "rejected"
VALID_DECISIONS = frozenset({DECISION_APPROVED, DECISION_REJECTED})


@dataclass(frozen=True)
class ApprovalPolicy:
    """Regla aprendida que puede auto-resolver futuras solicitudes."""

    policy_id: str
    decision: str
    scope_pattern: Mapping[str, str]
    kinds: Optional[frozenset[str]]
    ttl_s: Optional[float]
    created_at_epoch: float
    note: str = ""
    usage_count: int = 0

    def is_expired(self, now: float) -> bool:
        if self.ttl_s is None:
            return False
        return (now - self.created_at_epoch) > self.ttl_s

    def matches(self, request: ApprovalRequest) -> bool:
        if self.kinds is not None and request.kind not in self.kinds:
            return False
        for key, expected in self.scope_pattern.items():
            if request.scope.get(key) != expected:
                return False
        return True

    def specificity(self) -> int:
        return len(self.scope_pattern) + (0 if self.kinds is None else 1)

    def to_json(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "decision": self.decision,
            "scope_pattern": dict(self.scope_pattern),
            "kinds": None if self.kinds is None else sorted(self.kinds),
            "ttl_s": self.ttl_s,
            "created_at_epoch": self.created_at_epoch,
            "note": self.note,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_json(cls, payload: dict) -> "ApprovalPolicy":
        kinds = payload.get("kinds")
        return cls(
            policy_id=str(payload["policy_id"]),
            decision=str(payload["decision"]),
            scope_pattern=dict(payload.get("scope_pattern") or {}),
            kinds=None if kinds is None else frozenset(kinds),
            ttl_s=payload.get("ttl_s"),
            created_at_epoch=float(payload.get("created_at_epoch") or 0.0),
            note=str(payload.get("note") or ""),
            usage_count=int(payload.get("usage_count") or 0),
        )


class ApprovalMemory:
    """Memoria persistida de politicas de aprobacion explicitas."""

    def __init__(
        self,
        *,
        storage_path: Path,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._storage_path = storage_path
        self._clock = clock or time.time
        self._lock = threading.RLock()
        self._policies: dict[str, ApprovalPolicy] = {}
        self._load_from_disk()

    # ---- API publica ------------------------------------------------

    def remember(
        self,
        *,
        decision: str,
        scope_pattern: Mapping[str, str],
        kinds: Optional[Iterable[str]] = None,
        ttl_s: Optional[float] = None,
        note: str = "",
    ) -> str:
        """Registra una politica explicita y la persiste.

        Devuelve el `policy_id`.
        """
        if decision not in VALID_DECISIONS:
            raise ValueError(f"invalid decision: {decision!r}")
        policy = ApprovalPolicy(
            policy_id=uuid.uuid4().hex,
            decision=decision,
            scope_pattern=dict(scope_pattern or {}),
            kinds=None if kinds is None else frozenset(kinds),
            ttl_s=ttl_s,
            created_at_epoch=self._clock(),
            note=note,
        )
        with self._lock:
            self._policies[policy.policy_id] = policy
            self._save_to_disk_locked()
        return policy.policy_id

    def forget(self, policy_id: str) -> bool:
        """Revoca una politica. Devuelve True si existia."""
        with self._lock:
            removed = self._policies.pop(policy_id, None) is not None
            if removed:
                self._save_to_disk_locked()
        return removed

    def clear_expired(self) -> int:
        """Barre politicas expiradas. Devuelve cantidad removida."""
        now = self._clock()
        with self._lock:
            expired = [pid for pid, policy in self._policies.items() if policy.is_expired(now)]
            for pid in expired:
                self._policies.pop(pid, None)
            if expired:
                self._save_to_disk_locked()
        return len(expired)

    def list_policies(self) -> list[ApprovalPolicy]:
        """Devuelve las politicas vigentes (no incluye expiradas)."""
        now = self._clock()
        with self._lock:
            return [p for p in self._policies.values() if not p.is_expired(now)]

    def find_best_match(self, request: ApprovalRequest) -> Optional[ApprovalPolicy]:
        """Devuelve la politica mas especifica que aplique, o None."""
        now = self._clock()
        with self._lock:
            candidates = [
                p
                for p in self._policies.values()
                if not p.is_expired(now) and p.matches(request)
            ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.specificity(), reverse=True)
        return candidates[0]

    # ---- hooks para HumanApprovalBroker -----------------------------

    def pre_approver(self, request: ApprovalRequest) -> Optional[ApprovalResult]:
        """Pasarle este metodo a `HumanApprovalBroker.set_pre_approver(...)`.

        Reglas:
            - si la solicitud trae `payload_schema` no vacio, memoria NO
              resuelve (no tiene el valor).
            - si no hay politica aplicable, devuelve None.
            - si hay politica, aplica su `decision` y marca `auto_resolved=True`.
        """
        if request.payload_schema:
            return None
        policy = self.find_best_match(request)
        if policy is None:
            return None
        with self._lock:
            stored = self._policies.get(policy.policy_id)
            if stored is None:
                return None
            updated = ApprovalPolicy(
                policy_id=stored.policy_id,
                decision=stored.decision,
                scope_pattern=stored.scope_pattern,
                kinds=stored.kinds,
                ttl_s=stored.ttl_s,
                created_at_epoch=stored.created_at_epoch,
                note=stored.note,
                usage_count=stored.usage_count + 1,
            )
            self._policies[policy.policy_id] = updated
            self._save_to_disk_locked()
        if policy.decision == DECISION_APPROVED:
            return ApprovalResult(
                request_id=request.request_id,
                approved=True,
                auto_resolved=True,
            )
        return ApprovalResult(
            request_id=request.request_id,
            approved=False,
            rejected=True,
            auto_resolved=True,
        )

    def post_resolve_handler(
        self,
        request: ApprovalRequest,
        result: ApprovalResult,
    ) -> None:
        """Pasarle este metodo a `HumanApprovalBroker.register_post_resolve_handler(...)`.

        Actualmente solo se usa como hook de observacion para futuras
        extensiones (auditoria, metricas). No aprende implicitamente: para
        aprender, usar `remember(...)` explicitamente desde la UI.
        """
        return None

    # ---- persistencia -----------------------------------------------

    def _load_from_disk(self) -> None:
        try:
            raw = self._storage_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        except OSError:
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        entries = payload.get("policies") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                policy = ApprovalPolicy.from_json(entry)
            except (KeyError, TypeError, ValueError):
                continue
            self._policies[policy.policy_id] = policy

    def _save_to_disk_locked(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "policies": [p.to_json() for p in self._policies.values()],
        }
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".policies-",
            suffix=".json.tmp",
            dir=str(self._storage_path.parent),
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            from iabv_v15.infra.persistence.storage import _replace_with_retry
            _replace_with_retry(tmp_path, self._storage_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
