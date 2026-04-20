"""Harness operativo para auditar capacidades declaradas end-to-end.

Hoy IABV declara en ``tool_registry`` que capacidades como ``llm_local_ollama``,
``browser_capture`` o ``ui_execution`` están listas. Sin este harness no hay
forma externa de confirmar que funcionan **ahora mismo** en la máquina viva.

El harness es un **registro inyectable** (``{capability_id: runner}``) que:

* mantiene la fuente de verdad sobre qué capacidades tienen prueba real;
* no decide rutas ni suplanta al orquestador — sólo ejecuta sondas
  sintéticas ya diseñadas por el operador;
* clasifica cada capacidad con un ``CapabilityAuditPolicy`` (``requires_network``
  y ``assistant_kind``) para que el gate de governance del server MCP pueda
  bloquear rutas costosas sin tocar este módulo.

Las rutas a herramientas/servicios reales (Ollama, Playwright, UIExecutionRunner,
adapters de asistentes externos) se inyectan mediante *runner callables*. El
wiring con el container vive en ``bootstrap.py`` y en ``infra/mcp/server.py``.
Por eso este módulo NO importa nada de MCP ni forza Playwright.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


# Capacidades iniciales soportadas (tupla estable; tests parametrizan sobre ella).
DEFAULT_CAPABILITY_IDS: tuple[str, ...] = (
    "llm_local_ollama",
    "llm_external_chatgpt",
    "llm_external_claude",
    "browser_capture",
    "ui_execution",
)


@dataclass(frozen=True)
class CapabilityAuditPolicy:
    """Describe el costo/gate de auditar una capacidad.

    * ``requires_network``: si True, el MCP gate usa ``requires_network=True``
      (red offline bloquea antes de ejecutar). Ej.: ``llm_external_*``.
    * ``assistant_kind``: scope de governance (``"audit"`` en todos los casos
      actuales, pero aislado por si a futuro queremos sub-scopes).
    * ``consumes_quota``: hint humano; NO afecta el gate, sólo la UX en el
      payload devuelto para que el operador sepa que sondear esa capacidad
      puede consumir créditos externos.
    """

    requires_network: bool = False
    assistant_kind: str = "audit"
    consumes_quota: bool = False


# Políticas por defecto para las 5 capacidades iniciales.
DEFAULT_POLICIES: dict[str, CapabilityAuditPolicy] = {
    "llm_local_ollama": CapabilityAuditPolicy(requires_network=False),
    "llm_external_chatgpt": CapabilityAuditPolicy(requires_network=True, consumes_quota=True),
    "llm_external_claude": CapabilityAuditPolicy(requires_network=True, consumes_quota=True),
    "browser_capture": CapabilityAuditPolicy(requires_network=True),
    "ui_execution": CapabilityAuditPolicy(requires_network=False),
}


@dataclass
class CapabilityAuditResult:
    """Resultado estructurado de ejecutar un runner.

    Contrato estable: los runners DEBEN devolver esta forma exacta. El
    harness añade ``capability_id`` y ``latency_ms`` si el runner no lo
    hizo, y normaliza ``output_preview`` al serializar.
    """

    capability_id: str
    executed: bool
    success: bool
    latency_ms: int = 0
    output_preview: str = ""
    error: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


# Tipo esperado para un runner: recibe ``prompt_hint`` opcional para hacer la
# sonda un poquito reproducible (los tests pasan prompts sintéticos chicos).
# El harness NO fuerza este nombre a nivel lenguaje (los callables pueden ser
# ``lambda: ...``); se documenta acá.
CapabilityRunner = Callable[..., CapabilityAuditResult]


class CapabilityAuditHarness:
    """Registro de runners de auditoría de capacidades."""

    def __init__(
        self,
        runners: dict[str, CapabilityRunner] | None = None,
        policies: dict[str, CapabilityAuditPolicy] | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._runners: dict[str, CapabilityRunner] = dict(runners or {})
        self._policies: dict[str, CapabilityAuditPolicy] = dict(policies or DEFAULT_POLICIES)
        self._clock = clock

    # --- Registro ---------------------------------------------------

    def register(
        self,
        capability_id: str,
        runner: CapabilityRunner,
        *,
        policy: CapabilityAuditPolicy | None = None,
    ) -> None:
        """Registra (o reemplaza) un runner. Si se pasa policy, la asocia."""

        cid = str(capability_id or "").strip()
        if not cid:
            raise ValueError("capability_id no puede estar vacío")
        if runner is None:
            raise ValueError("runner no puede ser None")
        self._runners[cid] = runner
        if policy is not None:
            self._policies[cid] = policy

    def unregister(self, capability_id: str) -> None:
        """Elimina un runner si existe (idempotente)."""

        self._runners.pop(capability_id, None)

    # --- Introspección ----------------------------------------------

    def list_capabilities(self) -> tuple[str, ...]:
        """Capacidades con runner registrado, orden estable."""

        return tuple(sorted(self._runners.keys()))

    def policy_for(self, capability_id: str) -> CapabilityAuditPolicy:
        """Policy asociada al ``capability_id``, o default si no está mapeada."""

        return self._policies.get(capability_id, CapabilityAuditPolicy())

    def has_runner(self, capability_id: str) -> bool:
        return capability_id in self._runners

    # --- Ejecución --------------------------------------------------

    def run(
        self,
        capability_id: str,
        *,
        dry_run: bool = False,
        runner_kwargs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta un runner y devuelve el payload JSON-serializable.

        En ``dry_run=True`` NO ejecuta nada; sólo valida que el runner
        exista. Esto es la forma barata de chequear cobertura antes de
        consumir cuota externa.
        """

        cid = str(capability_id or "").strip()
        if not cid:
            return {
                "capability_id": cid,
                "executed": False,
                "success": False,
                "error": "invalid_capability_id",
                "detail": "capability_id vacío",
            }

        runner = self._runners.get(cid)
        policy = self.policy_for(cid)

        if runner is None:
            return {
                "capability_id": cid,
                "executed": False,
                "success": False,
                "error": "capability_not_registered",
                "detail": (
                    f"No hay runner para '{cid}'. Registradas: "
                    f"{', '.join(self.list_capabilities()) or '(ninguna)'}"
                ),
                "policy": _policy_payload(policy),
            }

        if dry_run:
            return {
                "capability_id": cid,
                "executed": False,
                "success": True,
                "dry_run": True,
                "latency_ms": 0,
                "output_preview": "",
                "error": None,
                "policy": _policy_payload(policy),
            }

        started = self._clock()
        try:
            raw = runner(**(runner_kwargs or {}))
        except Exception as exc:  # runner defectuoso NO debe tumbar el harness
            elapsed_ms = _elapsed_ms(self._clock, started)
            return {
                "capability_id": cid,
                "executed": True,
                "success": False,
                "latency_ms": elapsed_ms,
                "output_preview": "",
                "error": "runner_raised",
                "detail": f"{type(exc).__name__}: {exc}",
                "policy": _policy_payload(policy),
            }
        elapsed_ms = _elapsed_ms(self._clock, started)

        result = _coerce_result(cid, raw)
        # El runner puede haber medido su propia latencia; preferimos la suya
        # si es > 0, y rellenamos con la del harness si reportó 0.
        latency_ms = int(result.latency_ms) if int(result.latency_ms) > 0 else elapsed_ms

        return {
            "capability_id": result.capability_id or cid,
            "executed": bool(result.executed),
            "success": bool(result.success),
            "latency_ms": latency_ms,
            "output_preview": _clip_preview(result.output_preview),
            "error": result.error,
            "evidence": dict(result.evidence or {}),
            "policy": _policy_payload(policy),
        }


# ---------------------------------------------------------------------------
# Helpers


def _coerce_result(capability_id: str, raw: Any) -> CapabilityAuditResult:
    """Acepta dict o CapabilityAuditResult; normaliza a dataclass."""

    if isinstance(raw, CapabilityAuditResult):
        return raw
    if isinstance(raw, dict):
        return CapabilityAuditResult(
            capability_id=str(raw.get("capability_id") or capability_id),
            executed=bool(raw.get("executed", True)),
            success=bool(raw.get("success", False)),
            latency_ms=int(raw.get("latency_ms") or 0),
            output_preview=str(raw.get("output_preview") or ""),
            error=(str(raw["error"]) if raw.get("error") else None),
            evidence=dict(raw.get("evidence") or {}),
        )
    # Runner devolvió None / valor inválido → marcamos error.
    return CapabilityAuditResult(
        capability_id=capability_id,
        executed=True,
        success=False,
        error="runner_returned_invalid_type",
        evidence={"raw_repr": repr(raw)[:200]},
    )


def _elapsed_ms(clock: Callable[[], float], started: float) -> int:
    elapsed = max(0.0, clock() - started)
    return int(elapsed * 1000)


def _clip_preview(text: str, *, limit: int = 512) -> str:
    raw = str(text or "")
    if len(raw) <= limit:
        return raw
    return raw[:limit] + "… (truncated)"


def _policy_payload(policy: CapabilityAuditPolicy) -> dict[str, Any]:
    return {
        "requires_network": bool(policy.requires_network),
        "assistant_kind": str(policy.assistant_kind),
        "consumes_quota": bool(policy.consumes_quota),
    }


__all__ = [
    "CapabilityAuditHarness",
    "CapabilityAuditPolicy",
    "CapabilityAuditResult",
    "CapabilityRunner",
    "DEFAULT_CAPABILITY_IDS",
    "DEFAULT_POLICIES",
]
