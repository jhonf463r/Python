"""Tool MCP ``audit_capability``: sonda una capacidad declarada y reporta.

El trabajo pesado vive en
:class:`iabv_v15.services.evolution.capability_audit_harness.CapabilityAuditHarness`.
Este módulo sólo:

1. Resuelve/construye el harness desde el container si no fue pasado.
2. Valida ``capability_id`` y ``dry_run``.
3. Normaliza el payload de salida.

El gate de governance (``assistant_kind='audit'`` + ``requires_network`` dinámico
según la capacidad) vive en ``server.py`` — no acá — para mantener este módulo
puro/testeable sin FastMCP.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from iabv_v15.services.evolution.capability_audit_harness import (
    CapabilityAuditHarness,
    CapabilityAuditResult,
    DEFAULT_CAPABILITY_IDS,
    DEFAULT_POLICIES,
    CapabilityAuditPolicy,
)


# Factoría que produce un harness a partir del container. Se inyecta desde
# ``server.py``; tests pueden pasar factorías sintéticas sin instanciar
# AppBootstrap.
HarnessFactory = Callable[[], CapabilityAuditHarness | None]


def known_capability_ids() -> tuple[str, ...]:
    """Lista estable de capacidades soportadas por defecto."""

    return tuple(DEFAULT_CAPABILITY_IDS)


def policy_for_capability(capability_id: str) -> CapabilityAuditPolicy:
    """Policy pública para que ``server.py`` decida el gate antes de ejecutar."""

    return DEFAULT_POLICIES.get(capability_id, CapabilityAuditPolicy())


def audit_capability(
    capability_id: str,
    *,
    dry_run: bool = False,
    harness: CapabilityAuditHarness | None = None,
    harness_factory: HarnessFactory | None = None,
    runner_kwargs: dict[str, Any] | None = None,
    now_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    """Ejecuta el runner asociado a ``capability_id`` y devuelve el resultado.

    Args:
        capability_id: identificador declarado en ``DEFAULT_CAPABILITY_IDS``
            (o cualquier otro que haya sido registrado vía
            ``CapabilityAuditHarness.register``).
        dry_run: si True, no ejecuta el runner — sólo valida que esté
            registrado. Útil para que el Devin remoto revise cobertura sin
            consumir cuota externa.
        harness: harness explícito (útil para tests).
        harness_factory: si ``harness`` es None, se llama esta factoría para
            construirlo. Si ambos son None, devuelve
            ``{error: "harness_unavailable"}``.
        runner_kwargs: kwargs extra para pasarle al runner registrado.

    Returns:
        Dict JSON-serializable. En happy path:
            ``{capability_id, executed, success, latency_ms, output_preview,
               error, evidence, policy, checked_at_iso}``.
        En error:
            ``{capability_id, error, detail, ...}``.
    """

    cid = str(capability_id or "").strip()
    if not cid:
        return {
            "capability_id": "",
            "executed": False,
            "success": False,
            "error": "invalid_capability_id",
            "detail": "capability_id vacío",
            "checked_at_iso": _iso(now_utc()),
        }

    resolved_harness = harness
    if resolved_harness is None and harness_factory is not None:
        try:
            resolved_harness = harness_factory()
        except Exception as exc:
            return {
                "capability_id": cid,
                "executed": False,
                "success": False,
                "error": "harness_init_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "checked_at_iso": _iso(now_utc()),
            }

    if resolved_harness is None:
        return {
            "capability_id": cid,
            "executed": False,
            "success": False,
            "error": "harness_unavailable",
            "detail": (
                "No se pudo resolver CapabilityAuditHarness desde el container. "
                "Revisa bootstrap.py: el wiring puede haber degradado."
            ),
            "checked_at_iso": _iso(now_utc()),
        }

    payload = resolved_harness.run(
        cid,
        dry_run=bool(dry_run),
        runner_kwargs=dict(runner_kwargs or {}),
    )
    payload.setdefault("checked_at_iso", _iso(now_utc()))
    return payload


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Builtin runner factories
#
# Cada factoría recibe lo mínimo necesario para construir un ``runner``
# que cumple el contrato ``() -> CapabilityAuditResult`` (o dict equivalente).
# NO se ejecutan acá; sólo devuelven el callable, permitiendo que el
# wiring decida qué subset conectar en runtime.


@dataclass
class _ProviderHealthLike:
    """Protocolo mínimo para un health_check de Ollama."""

    available: bool
    reason: str = ""


class _LLMProviderLike:
    """Protocolo mínimo que espera el runner de llm_local_ollama."""

    def health_check(self) -> _ProviderHealthLike: ...  # pragma: no cover
    def answer_user(self, request: Any) -> Any: ...  # pragma: no cover


def build_llm_local_ollama_runner(
    provider: _LLMProviderLike | None,
    *,
    inference_service: Any | None = None,
    prompt: str = "Hola, responde con OK.",
    clock: Callable[[], float] = time.monotonic,
) -> Callable[..., CapabilityAuditResult]:
    """Runner para ``llm_local_ollama``.

    Verifica ``provider.health_check().available`` y luego ejecuta un prompt
    sintético chico. Ante cualquier falla, devuelve un
    ``CapabilityAuditResult`` con ``success=False`` y ``error`` humano.
    """

    def _run(**_kwargs: Any) -> CapabilityAuditResult:
        if provider is None:
            return CapabilityAuditResult(
                capability_id="llm_local_ollama",
                executed=False,
                success=False,
                error="provider_unavailable",
                evidence={"reason": "no LLMProvider inyectado"},
            )
        started = clock()
        try:
            health = provider.health_check()
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id="llm_local_ollama",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="health_check_raised",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        if not bool(getattr(health, "available", False)):
            return CapabilityAuditResult(
                capability_id="llm_local_ollama",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="provider_unhealthy",
                evidence={"reason": str(getattr(health, "reason", "") or "desconocido")},
            )

        # El provider real (OpenAICompatLocalProvider) accede a `.value` en
        # varios campos del request (`task_role`, `complexity`, `ambiguity`,
        # `allowed_tools`). Un `SimpleNamespace` con strings sueltos rompe
        # con `AttributeError: 'str' object has no attribute 'value'`. Usamos
        # el contrato real `InferenceRequest` con defaults seguros.
        from iabv_v15.domain.models import InferenceRequest

        request = InferenceRequest(
            user_goal="capability_audit",
            prompt=prompt,
            offline_only=True,
            metadata={"scope": "capability_audit", "assistant_kind": "ollama"},
        )
        try:
            # Route through canonical InferenceService to enforce reflection routing and resource governance
            if inference_service is not None:
                record = inference_service.infer_task(request)
                result = record.result
            else:
                # Fail-closed: InferenceService unavailable, return failure without provider call
                return CapabilityAuditResult(
                    capability_id="llm_local_ollama",
                    executed=False,
                    success=False,
                    latency_ms=int(max(0.0, clock() - started) * 1000),
                    error="inference_service_unavailable",
                    evidence={"reason": "InferenceService is None - fail-closed to prevent provider bypass"},
                )
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id="llm_local_ollama",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="answer_raised",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        elapsed_ms = int(max(0.0, clock() - started) * 1000)
        summary = str(getattr(result, "summary", "") or "")
        return CapabilityAuditResult(
            capability_id="llm_local_ollama",
            executed=True,
            success=bool(summary.strip()),
            latency_ms=elapsed_ms,
            output_preview=summary,
            error=None if summary.strip() else "empty_response",
            evidence={
                "provider_name": str(getattr(result, "provider_name", "") or ""),
            },
        )

    return _run


def build_llm_external_runner(
    assistant_kind: str,
    *,
    probe_login: Callable[[str], dict[str, Any]],
    send_prompt: Callable[[str], dict[str, Any]] | None = None,
    prompt: str = "Hola, responde con OK.",
    clock: Callable[[], float] = time.monotonic,
) -> Callable[..., CapabilityAuditResult]:
    """Runner para ``llm_external_{chatgpt,claude,...}``.

    Usa ``probe_login`` (típicamente ``probe_assistant_login`` del F3.1) para
    confirmar sesión activa. Si ``send_prompt`` está disponible, ejecuta un
    prompt sintético corto; si no, se limita a reportar el estado del login.
    """

    def _run(**_kwargs: Any) -> CapabilityAuditResult:
        started = clock()
        try:
            login_payload = probe_login(assistant_kind)
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id=f"llm_external_{assistant_kind}",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="probe_login_raised",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        if isinstance(login_payload, dict) and login_payload.get("governance_blocked"):
            return CapabilityAuditResult(
                capability_id=f"llm_external_{assistant_kind}",
                executed=False,
                success=False,
                error="governance_blocked",
                evidence={"upstream": login_payload},
            )
        logged_in = bool(isinstance(login_payload, dict) and login_payload.get("logged_in"))
        if not logged_in:
            return CapabilityAuditResult(
                capability_id=f"llm_external_{assistant_kind}",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="not_logged_in",
                evidence={
                    "login_reason": str(login_payload.get("reason") or "unknown")
                    if isinstance(login_payload, dict)
                    else "probe_returned_non_dict",
                    "login_error": str(login_payload.get("error") or "")
                    if isinstance(login_payload, dict)
                    else "",
                },
            )

        if send_prompt is None:
            # Sin adapter para enviar prompt; pero login ok ya es señal válida.
            return CapabilityAuditResult(
                capability_id=f"llm_external_{assistant_kind}",
                executed=True,
                success=True,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                output_preview="login_ok",
                evidence={"login_only": True},
            )

        try:
            send_payload = send_prompt(prompt)
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id=f"llm_external_{assistant_kind}",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="send_prompt_raised",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        elapsed_ms = int(max(0.0, clock() - started) * 1000)
        success = bool(isinstance(send_payload, dict) and send_payload.get("success"))
        preview = str(
            (send_payload.get("output_text") if isinstance(send_payload, dict) else "")
            or ""
        )
        return CapabilityAuditResult(
            capability_id=f"llm_external_{assistant_kind}",
            executed=True,
            success=success,
            latency_ms=elapsed_ms,
            output_preview=preview,
            error=None if success else "send_prompt_failed",
            evidence={"raw": send_payload if isinstance(send_payload, dict) else None},
        )

    return _run


class _BrowserControllerLike:
    """Protocolo mínimo del BrowserSessionController para el runner."""

    def start(self) -> None: ...  # pragma: no cover
    def close(self) -> None: ...  # pragma: no cover
    @property
    def page(self) -> Any | None: ...  # pragma: no cover


def build_browser_capture_runner(
    controller_factory: Callable[[], _BrowserControllerLike | None],
    *,
    url: str = "https://example.com/",
    expected_substring: str = "Example Domain",
    clock: Callable[[], float] = time.monotonic,
) -> Callable[..., CapabilityAuditResult]:
    """Runner para ``browser_capture``.

    Abre ``url``, captura ``document.title`` y busca ``expected_substring``
    en el ``content()``. Cierra el controller siempre, aun ante error.
    """

    def _run(**_kwargs: Any) -> CapabilityAuditResult:
        started = clock()
        try:
            controller = controller_factory()
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id="browser_capture",
                executed=False,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="controller_init_failed",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        if controller is None:
            return CapabilityAuditResult(
                capability_id="browser_capture",
                executed=False,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="playwright_unavailable",
                evidence={"reason": "controller_factory returned None"},
            )
        try:
            try:
                controller.start()
            except Exception as exc:
                return CapabilityAuditResult(
                    capability_id="browser_capture",
                    executed=True,
                    success=False,
                    latency_ms=int(max(0.0, clock() - started) * 1000),
                    error="controller_start_failed",
                    evidence={"exception": f"{type(exc).__name__}: {exc}"},
                )
            page = getattr(controller, "page", None)
            if page is None:
                return CapabilityAuditResult(
                    capability_id="browser_capture",
                    executed=True,
                    success=False,
                    latency_ms=int(max(0.0, clock() - started) * 1000),
                    error="page_unavailable",
                )
            try:
                page.goto(url, timeout=10000)
            except Exception as exc:
                return CapabilityAuditResult(
                    capability_id="browser_capture",
                    executed=True,
                    success=False,
                    latency_ms=int(max(0.0, clock() - started) * 1000),
                    error="goto_failed",
                    evidence={"exception": f"{type(exc).__name__}: {exc}"},
                )
            title = ""
            body_text = ""
            try:
                title = str(page.title() or "")
            except Exception:
                title = ""
            try:
                body_text = str(page.content() or "")
            except Exception:
                body_text = ""
            elapsed_ms = int(max(0.0, clock() - started) * 1000)
            matched = expected_substring in body_text
            return CapabilityAuditResult(
                capability_id="browser_capture",
                executed=True,
                success=bool(matched),
                latency_ms=elapsed_ms,
                output_preview=title,
                error=None if matched else "expected_substring_missing",
                evidence={
                    "url": url,
                    "expected_substring": expected_substring,
                    "title": title,
                    "body_length": len(body_text),
                },
            )
        finally:
            try:
                controller.close()
            except Exception:
                pass

    return _run


def build_ui_execution_runner(
    executor: Callable[..., Any] | None,
    *,
    clock: Callable[[], float] = time.monotonic,
) -> Callable[..., CapabilityAuditResult]:
    """Runner para ``ui_execution``.

    Ejecuta un ``ToolAction`` idempotente (el executor real debe ser
    inofensivo — ej. ``mouse_move`` a coordenada conocida). Si el executor
    no existe, reporta ``ui_execution_unavailable``.
    """

    def _run(**kwargs: Any) -> CapabilityAuditResult:
        if executor is None:
            return CapabilityAuditResult(
                capability_id="ui_execution",
                executed=False,
                success=False,
                error="ui_execution_unavailable",
                evidence={"reason": "UIExecutionRunner no inyectado"},
            )
        started = clock()
        try:
            result = executor(**kwargs)
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id="ui_execution",
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="executor_raised",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        elapsed_ms = int(max(0.0, clock() - started) * 1000)
        success = bool(
            isinstance(result, dict)
            and (result.get("success") or result.get("executed"))
        )
        preview = str(
            (result.get("output_text") if isinstance(result, dict) else "") or ""
        )
        return CapabilityAuditResult(
            capability_id="ui_execution",
            executed=True,
            success=success,
            latency_ms=elapsed_ms,
            output_preview=preview,
            error=None if success else "executor_not_ok",
            evidence={"raw": result if isinstance(result, dict) else repr(result)[:200]},
        )

    return _run


def build_domain_capability_runner(
    capability_id: str,
    *,
    site_id: str | None = None,
    readiness_provider: Callable[[str, str | None], Any | None],
    clock: Callable[[], float] = time.monotonic,
) -> Callable[..., CapabilityAuditResult]:
    """Runner para capacidades de dominio (``wplay.*``, ``browser.search.google``,
    ``browser.generic.navigation``).

    A diferencia de los runners de infraestructura (Ollama, ChatGPT, browser_capture,
    ui_execution) que ejecutan una sonda sintética, las capacidades de dominio se
    miden por **evidencia aprendida**: el runner consulta a ``readiness_provider``
    y reporta el ``CapabilityStatus`` del último snapshot persistido por
    ``CapabilityReadinessService``.

    Contrato del ``readiness_provider``:

    * Recibe ``(capability_id, site_id)``.
    * Devuelve el objeto ``CapabilityReadiness`` más reciente o ``None`` si nunca
      se capturó evidencia para esa capacidad.
    * No debe lanzar; si lanza, el runner lo captura y reporta
      ``error="readiness_provider_raised"``.

    Semántica del resultado:

    * ``None`` o status ``INSUFFICIENT`` → ``error="capability_pack_not_captured"``
      con pista explícita: falta TeachingStudio capture y registro en el
      ``capability_runner_registry`` para emitir ``UniversalPerceptionSignal``.
    * ``PARTIAL`` → ``error="capability_status_partial"`` + evidencia de qué
      señales faltan.
    * ``READY`` / ``READY_WITH_APPROVAL`` → ``success=True`` con preview del título
      y score actual.

    Este runner es el complemento físico del diagnóstico estructurado de
    ``PendingIssueService`` y ``ResultComparator``: cuando ambos apunten al
    mismo ``capability_id`` el operador sabe exactamente qué pieza instalar
    (capture + runner) para desbloquear el escenario.
    """

    def _run(**_kwargs: Any) -> CapabilityAuditResult:
        started = clock()
        try:
            readiness = readiness_provider(capability_id, site_id)
        except Exception as exc:
            return CapabilityAuditResult(
                capability_id=capability_id,
                executed=True,
                success=False,
                latency_ms=int(max(0.0, clock() - started) * 1000),
                error="readiness_provider_raised",
                evidence={"exception": f"{type(exc).__name__}: {exc}"},
            )
        elapsed_ms = int(max(0.0, clock() - started) * 1000)

        if readiness is None:
            return CapabilityAuditResult(
                capability_id=capability_id,
                executed=True,
                success=False,
                latency_ms=elapsed_ms,
                error="capability_pack_not_captured",
                output_preview="",
                evidence={
                    "site_id": site_id or "",
                    "requires": (
                        f"TeachingStudio capture + runner registrado para "
                        f"'{capability_id}'; sin evidencia previa el pack "
                        "sensible no puede emitir UniversalPerceptionSignal."
                    ),
                },
            )

        status_value = str(getattr(getattr(readiness, "status", None), "value", "") or "")
        title = str(getattr(readiness, "title", "") or capability_id)
        score = float(getattr(readiness, "score", 0.0) or 0.0)
        evidence_items = list(getattr(readiness, "evidence", []) or [])
        missing_signals = list(getattr(readiness, "missing_signals", []) or [])
        suggested = str(getattr(readiness, "suggested_next_step", "") or "")
        last_episode = str(getattr(readiness, "last_episode_id", "") or "")

        base_evidence: dict[str, Any] = {
            "site_id": site_id or getattr(readiness, "site_id", "") or "",
            "status": status_value,
            "score": score,
            "evidence_preview": evidence_items[:4],
            "missing_signals": missing_signals[:4],
            "suggested_next_step": suggested,
            "last_episode_id": last_episode,
        }

        if status_value in {"ready", "ready_with_approval"}:
            return CapabilityAuditResult(
                capability_id=capability_id,
                executed=True,
                success=True,
                latency_ms=elapsed_ms,
                output_preview=title,
                evidence=base_evidence,
            )
        if status_value == "partial":
            return CapabilityAuditResult(
                capability_id=capability_id,
                executed=True,
                success=False,
                latency_ms=elapsed_ms,
                output_preview=title,
                error="capability_status_partial",
                evidence=base_evidence,
            )
        # INSUFFICIENT o valor desconocido: tratamos como pack no capturado.
        return CapabilityAuditResult(
            capability_id=capability_id,
            executed=True,
            success=False,
            latency_ms=elapsed_ms,
            output_preview=title,
            error="capability_pack_not_captured",
            evidence=base_evidence,
        )

    return _run


__all__ = [
    "audit_capability",
    "build_browser_capture_runner",
    "build_domain_capability_runner",
    "build_llm_external_runner",
    "build_llm_local_ollama_runner",
    "build_ui_execution_runner",
    "known_capability_ids",
    "policy_for_capability",
]
