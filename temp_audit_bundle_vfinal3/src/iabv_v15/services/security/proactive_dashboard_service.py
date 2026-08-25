"""ProactiveDashboardService: calcula `que necesita IABV del humano ahora`.

Al arrancar IABV, en lugar de esperar a que el usuario pregunte, esta capa
resume en una sola foto:

    - solicitudes de aprobacion humanas abiertas (`HumanApprovalBroker`)
    - politicas aprendidas que resuelven decisiones automaticamente
      (`ApprovalMemory`), con su contador de uso (transparencia: el usuario
      ve que cosas se estan auto-aprobando y puede revocarlas)

Produce un `DashboardSnapshot` puramente de datos. La UI (EvolutionCenter)
lo consume en un PR siguiente sin que este servicio conozca el ViewModel.

Reglas AGENTS.md relevantes:
    - no es otro cerebro ni orquestador; solo agrega y resume
    - no duplica `PerceptionSnapshot`, `EnvironmentSelfModel` o
      `WorldModelSnapshot`
    - no inyecta decisiones de ruta; su output es descriptivo
    - respeta que el ViewModel no es decisor: solo expone datos
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional

from iabv_v15.services.security.approval_memory import (
    ApprovalMemory,
    ApprovalPolicy,
    DECISION_APPROVED,
    DECISION_REJECTED,
)
from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker


SEVERITY_INFO = "info"
SEVERITY_ATTENTION = "attention"
SEVERITY_CRITICAL = "critical"

SEVERITY_ORDER = {
    SEVERITY_CRITICAL: 0,
    SEVERITY_ATTENTION: 1,
    SEVERITY_INFO: 2,
}

ENTRY_KIND_APPROVAL_REQUEST = "approval_request"
ENTRY_KIND_LEARNED_POLICY = "learned_policy"


# Heuristic: algunos kinds son `critical` (bloquean el flujo si no se atienden)
# y otros son `attention` (tarea pendiente pero no bloqueante inmediato).
_CRITICAL_REQUEST_KINDS = frozenset(
    {
        "login_required",
        "credential_request",
        "perception_mismatch_confirmation",
        "destructive_action",
    }
)


@dataclass(frozen=True)
class DashboardEntry:
    """Un item que el humano debe ver al arrancar IABV."""

    entry_id: str
    kind: str
    title: str
    detail: str
    severity: str
    scope: Mapping[str, str]
    actionable: bool
    created_at_epoch: float


@dataclass(frozen=True)
class DashboardSnapshot:
    """Foto generada por el servicio; sin estado mutable."""

    generated_at_epoch: float
    entries: tuple[DashboardEntry, ...] = ()
    pending_attention_count: int = 0
    learned_policies_count: int = 0

    def has_attention_items(self) -> bool:
        return self.pending_attention_count > 0


class ProactiveDashboardService:
    """Agrega pendings del broker + politicas aprendidas en una sola snapshot."""

    def __init__(
        self,
        *,
        broker: HumanApprovalBroker,
        memory: ApprovalMemory,
        clock: Callable[[], float] | None = None,
        include_learned_policies: bool = True,
    ) -> None:
        self._broker = broker
        self._memory = memory
        self._clock = clock or time.time
        self._include_policies = bool(include_learned_policies)

    # ---- API publica -------------------------------------------------

    def snapshot(self) -> DashboardSnapshot:
        """Devuelve la foto actual. Thread-safe: delega a broker y memory."""
        now = self._clock()
        entries: list[DashboardEntry] = []

        for pending in self._broker.pending_requests():
            entries.append(self._entry_from_pending(pending))

        pending_attention_count = len(entries)

        if self._include_policies:
            for policy in self._memory.list_policies():
                entries.append(self._entry_from_policy(policy))

        entries.sort(
            key=lambda e: (
                SEVERITY_ORDER.get(e.severity, 99),
                -e.created_at_epoch,
            )
        )

        return DashboardSnapshot(
            generated_at_epoch=now,
            entries=tuple(entries),
            pending_attention_count=pending_attention_count,
            learned_policies_count=len(self._memory.list_policies()),
        )

    def pending_attention_count(self) -> int:
        return self._broker.pending_count()

    # ---- internals ---------------------------------------------------

    def _entry_from_pending(self, pending: dict) -> DashboardEntry:
        kind = str(pending.get("kind") or "")
        scope = dict(pending.get("scope") or {})
        severity = (
            SEVERITY_CRITICAL
            if kind in _CRITICAL_REQUEST_KINDS
            else SEVERITY_ATTENTION
        )
        title = self._title_for_request(kind, scope)
        detail = str(pending.get("reason") or "")
        return DashboardEntry(
            entry_id=str(pending.get("id") or ""),
            kind=ENTRY_KIND_APPROVAL_REQUEST,
            title=title,
            detail=detail,
            severity=severity,
            scope=scope,
            actionable=True,
            created_at_epoch=float(pending.get("requested_at_epoch") or 0.0),
        )

    def _entry_from_policy(self, policy: ApprovalPolicy) -> DashboardEntry:
        action_word = (
            "auto-aprueba"
            if policy.decision == DECISION_APPROVED
            else "auto-rechaza"
            if policy.decision == DECISION_REJECTED
            else policy.decision
        )
        scope_desc = ", ".join(f"{k}={v}" for k, v in sorted(policy.scope_pattern.items()))
        kinds_desc = (
            "cualquier tipo"
            if policy.kinds is None
            else ", ".join(sorted(policy.kinds))
        )
        title = f"Politica aprendida: {action_word} {kinds_desc}"
        detail_parts = [f"scope: {scope_desc or '(sin filtro)'}", f"usos: {policy.usage_count}"]
        if policy.note:
            detail_parts.append(f"nota: {policy.note}")
        if policy.ttl_s is not None:
            detail_parts.append(f"ttl_s: {policy.ttl_s}")
        return DashboardEntry(
            entry_id=policy.policy_id,
            kind=ENTRY_KIND_LEARNED_POLICY,
            title=title,
            detail=" | ".join(detail_parts),
            severity=SEVERITY_INFO,
            scope=dict(policy.scope_pattern),
            actionable=False,
            created_at_epoch=policy.created_at_epoch,
        )

    @staticmethod
    def _title_for_request(kind: str, scope: Mapping[str, str]) -> str:
        """Armamos un titulo humano corto segun kind + scope."""
        if kind == "login_required":
            who = scope.get("assistant") or scope.get("provider") or "asistente"
            return f"Login requerido en {who}"
        if kind == "credential_request":
            provider = scope.get("provider") or scope.get("domain") or "proveedor"
            return f"Credencial requerida para {provider}"
        if kind == "perception_mismatch_confirmation":
            subject = scope.get("subject") or scope.get("assistant") or "observacion"
            return f"Confirmar ground truth: {subject}"
        if kind == "destructive_action":
            target = scope.get("target") or "objetivo"
            return f"Autorizar accion destructiva sobre {target}"
        if kind == "external_call_authorization":
            provider = scope.get("provider") or scope.get("url") or "endpoint externo"
            return f"Autorizar llamada externa a {provider}"
        if kind == "merge_pr":
            repo = scope.get("repo") or "repo"
            pr = scope.get("pr_number") or scope.get("pr") or "PR"
            return f"Aprobar merge de {repo}#{pr}"
        if kind:
            return f"Aprobacion requerida: {kind}"
        return "Aprobacion requerida"
