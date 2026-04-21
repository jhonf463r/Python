"""HumanApprovalBroker: servicio generico para solicitar validacion humana.

Extiende el patron ya probado por `EnvironmentBootstrapService` (prompt +
futures thread-safe) y `CredentialBroker` (sensitive data no viaja por logs)
a cualquier decision que no pueda resolverse sin presencia humana real:

    - login detectado como ausente en un asistente externo
    - rotacion / entrega de credencial delicada
    - autorizacion puntual de un POST externo con efecto de escritura
    - confirmacion de ground truth cuando la percepcion es ambigua
    - accion destructiva explicita (rm / drop / delete)

No es otro cerebro ni orquestador. No duplica `PerceptionSnapshot` ni
`EnvironmentSelfModel`. Solo media entre un consumer interno que detecta la
necesidad y la UI/usuario que resuelve.

La UI se suscribe via `register_prompt_handler` y recibe un dict describiendo
la solicitud (sin payload sensible). El usuario responde en la UI llamando
`approve(request_id, payload=...)` o `reject(request_id)`. El consumer que
inicio la solicitud obtiene un `ApprovalResult` via la API bloqueante
`request(...)`.

Scope y ApprovalMemory
----------------------
Cada solicitud lleva un `scope` (dict[str, str]) que describe por atributos
la decision (ej. `{"kind": "merge_pr", "repo": "jhonf463r/Python",
"label": "documentation_only"}`). ApprovalMemory (PR siguiente) decidira si
una solicitud con el mismo scope debe auto-aprobarse a partir de politicas
aprendidas previamente. Este modulo solo expone los hooks
(`set_pre_approver`, `register_post_resolve_handler`) para que ApprovalMemory
se enchufe sin que el broker la conozca.
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Protocol


PromptHandler = Callable[[dict], None]
PreApprover = Callable[["ApprovalRequest"], Optional["ApprovalResult"]]
PostResolveHandler = Callable[["ApprovalRequest", "ApprovalResult"], None]


class _UIScreenshotCapturer(Protocol):
    """Minimo contrato que el broker necesita para capturar evidencia visual.

    Coincide con `UIScreenshotService.capture` pero se define como Protocol
    para no introducir dependencia dura (el servicio de captura vive en
    `services.capture` y no debe importarse aqui para evitar ciclos).
    """

    def capture(
        self,
        *,
        source: str,
        scope: Mapping[str, str] | None = None,
        session_id: str | None = None,
    ) -> object: ...


# Reason codes estables. No inventar mas; ampliarlos si un caso real lo exige.
KIND_LOGIN_REQUIRED = "login_required"
KIND_CREDENTIAL_REQUEST = "credential_request"
KIND_EXTERNAL_CALL_AUTHORIZATION = "external_call_authorization"
KIND_PERCEPTION_MISMATCH = "perception_mismatch_confirmation"
KIND_DESTRUCTIVE_ACTION = "destructive_action"
KIND_MERGE_PR = "merge_pr"
KIND_GENERIC = "generic"

KNOWN_KINDS = frozenset(
    {
        KIND_LOGIN_REQUIRED,
        KIND_CREDENTIAL_REQUEST,
        KIND_EXTERNAL_CALL_AUTHORIZATION,
        KIND_PERCEPTION_MISMATCH,
        KIND_DESTRUCTIVE_ACTION,
        KIND_MERGE_PR,
        KIND_GENERIC,
    }
)


@dataclass(frozen=True)
class ApprovalRequest:
    """Solicitud de validacion humana pendiente de resolver."""

    request_id: str
    kind: str
    reason: str
    scope: Mapping[str, str]
    payload_schema: tuple[str, ...] = ()
    sensitive: bool = False
    requested_at_epoch: float = 0.0


@dataclass(frozen=True)
class ApprovalResult:
    """Resultado final de una solicitud. Thread-safe / inmutable."""

    request_id: str
    approved: bool
    rejected: bool = False
    timed_out: bool = False
    cancelled: bool = False
    auto_resolved: bool = False
    payload_keys: tuple[str, ...] = ()
    payload: Optional[Mapping[str, str]] = None

    def is_resolved(self) -> bool:
        return self.approved or self.rejected or self.timed_out or self.cancelled


@dataclass
class _PendingEntry:
    request: ApprovalRequest
    future: Future


class HumanApprovalBroker:
    """Mediador thread-safe de aprobaciones humanas genericas."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._prompt_handler: Optional[PromptHandler] = None
        self._pre_approver: Optional[PreApprover] = None
        self._post_handlers: list[PostResolveHandler] = []
        self._lock = threading.RLock()
        self._pending: dict[str, _PendingEntry] = {}
        self._clock = clock or time.time
        self._ui_screenshot_capturer: Optional[_UIScreenshotCapturer] = None

    # ---- wiring ------------------------------------------------------

    def register_prompt_handler(self, handler: PromptHandler) -> None:
        """Registra el callback que emite `humanApprovalRequested` en la UI."""
        with self._lock:
            self._prompt_handler = handler

    def set_pre_approver(self, pre_approver: Optional[PreApprover]) -> None:
        """Permite que ApprovalMemory resuelva solicitudes sin preguntar al humano.

        Si devuelve un `ApprovalResult`, se usa directamente y no se emite
        prompt. Si devuelve `None`, la solicitud pasa al flujo normal.
        """
        with self._lock:
            self._pre_approver = pre_approver

    def set_ui_screenshot_capturer(
        self, capturer: Optional[_UIScreenshotCapturer]
    ) -> None:
        """Registra un servicio que guarde evidencia visual del prompt.

        AGENTS.md: no es otro cerebro ni decisor; solo deja un PNG en
        `data/evolution/ui_snapshots/` cada vez que IABV pide algo al humano,
        para que la revision posterior pueda reconstruir que estaba en pantalla
        en ese momento. Opcional; el broker sigue funcionando sin el.
        """
        with self._lock:
            self._ui_screenshot_capturer = capturer

    def register_post_resolve_handler(self, handler: PostResolveHandler) -> None:
        """Observador invocado cuando una solicitud se resuelve (cualquier via).

        Uso tipico: ApprovalMemory persiste el resultado para futuras coincidencias.
        """
        with self._lock:
            self._post_handlers.append(handler)

    # ---- public API --------------------------------------------------

    def request(
        self,
        *,
        kind: str,
        reason: str,
        scope: Optional[Mapping[str, str]] = None,
        payload_schema: tuple[str, ...] = (),
        sensitive: bool = False,
        timeout_s: Optional[float] = None,
    ) -> ApprovalResult:
        """Solicita aprobacion humana y bloquea hasta resolucion o timeout.

        Parametros:
            kind: uno de `KIND_*` o string libre (ver `KNOWN_KINDS`).
            reason: texto humano que la UI mostrara al usuario. No debe contener
                secretos.
            scope: atributos que describen la decision para `ApprovalMemory`.
                Valores deben ser string; no serializa payload sensible.
            payload_schema: nombres de campos que la UI debe recolectar
                (ej. `("token",)` para credencial).
            sensitive: si True, el broker no persiste el payload en memoria ni
                lo expone en `pending_requests()`. El valor solo viaja por el
                `Future` hacia el consumer original.
            timeout_s: None = espera indefinida. Si se agota, devuelve
                `timed_out=True` y la UI debe descartar el prompt.
        """
        if not kind:
            raise ValueError("approval request requires non-empty kind")
        scope_map: Mapping[str, str] = dict(scope or {})

        request = ApprovalRequest(
            request_id=uuid.uuid4().hex,
            kind=kind,
            reason=reason or "",
            scope=scope_map,
            payload_schema=tuple(payload_schema),
            sensitive=bool(sensitive),
            requested_at_epoch=self._clock(),
        )

        # 1) Pre-approver (ApprovalMemory) puede resolver sin prompt.
        with self._lock:
            pre = self._pre_approver
        if pre is not None:
            pre_result = pre(request)
            if pre_result is not None:
                self._dispatch_post_resolve(request, pre_result)
                return pre_result

        # 2) Registrar future y emitir prompt.
        future: Future = Future()
        with self._lock:
            self._pending[request.request_id] = _PendingEntry(request=request, future=future)
            handler = self._prompt_handler

        prompt_payload = self._build_prompt_payload(request)
        self._capture_ui_snapshot(request)
        if handler is None:
            # Sin UI conectada no hay forma de pedir aprobacion: resolvemos
            # como timed_out inmediato para que el consumer no quede bloqueado.
            self._finalise_without_handler(request)
            return ApprovalResult(
                request_id=request.request_id,
                approved=False,
                timed_out=True,
            )

        try:
            handler(prompt_payload)
        except Exception:
            # Si la UI falla al emitir, no dejamos el Future huerfano.
            with self._lock:
                self._pending.pop(request.request_id, None)
            raise

        try:
            result: ApprovalResult = future.result(timeout=timeout_s)
        except FutureTimeoutError:
            with self._lock:
                entry = self._pending.pop(request.request_id, None)
            if entry is not None and not entry.future.done():
                entry.future.cancel()
            result = ApprovalResult(
                request_id=request.request_id,
                approved=False,
                timed_out=True,
            )

        self._dispatch_post_resolve(request, result)
        return result

    def approve(
        self,
        request_id: str,
        payload: Optional[Mapping[str, str]] = None,
    ) -> bool:
        """La UI llama esto cuando el usuario aprueba la solicitud."""
        with self._lock:
            entry = self._pending.pop(request_id, None)
        if entry is None or entry.future.done():
            return False
        result = self._build_result(
            entry.request,
            approved=True,
            payload=payload,
        )
        entry.future.set_result(result)
        return True

    def reject(self, request_id: str) -> bool:
        """La UI llama esto cuando el usuario rechaza la solicitud."""
        with self._lock:
            entry = self._pending.pop(request_id, None)
        if entry is None or entry.future.done():
            return False
        result = ApprovalResult(
            request_id=request_id,
            approved=False,
            rejected=True,
        )
        entry.future.set_result(result)
        return True

    def cancel(self, request_id: str) -> bool:
        """Cancelacion programatica (ej. el caller ya no necesita la aprobacion)."""
        with self._lock:
            entry = self._pending.pop(request_id, None)
        if entry is None or entry.future.done():
            return False
        result = ApprovalResult(
            request_id=request_id,
            approved=False,
            cancelled=True,
        )
        entry.future.set_result(result)
        return True

    def pending_requests(self) -> list[dict]:
        """Describe las solicitudes pendientes sin exponer payload sensible.

        `ProactiveDashboardService` lo usa para mostrar en EvolutionCenter
        "que necesita IABV del humano ahora mismo".
        """
        with self._lock:
            entries = list(self._pending.values())
        return [self._build_prompt_payload(entry.request) for entry in entries]

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    # ---- internals ---------------------------------------------------

    @staticmethod
    def _build_prompt_payload(request: ApprovalRequest) -> dict:
        """Payload seguro para la UI. No incluye valores sensibles."""
        return {
            "id": request.request_id,
            "kind": request.kind,
            "reason": request.reason,
            "scope": dict(request.scope),
            "payload_schema": list(request.payload_schema),
            "sensitive": request.sensitive,
            "requested_at_epoch": request.requested_at_epoch,
        }

    @staticmethod
    def _build_result(
        request: ApprovalRequest,
        *,
        approved: bool,
        payload: Optional[Mapping[str, str]],
    ) -> ApprovalResult:
        normalised_payload: Optional[Mapping[str, str]]
        payload_keys: tuple[str, ...]
        if payload is None:
            normalised_payload = None
            payload_keys = ()
        else:
            normalised_payload = dict(payload)
            payload_keys = tuple(sorted(normalised_payload.keys()))
        return ApprovalResult(
            request_id=request.request_id,
            approved=approved,
            payload=normalised_payload,
            payload_keys=payload_keys,
        )

    def _capture_ui_snapshot(self, request: ApprovalRequest) -> None:
        """Best-effort: nunca interrumpe el flujo de aprobacion.

        Se dispara solo despues del pre_approver: si ApprovalMemory ya
        resolvio la solicitud automaticamente no hay UI que fotografiar
        (no hubo presencia humana). Si el capturer falla, solo se loggea.
        """
        with self._lock:
            capturer = self._ui_screenshot_capturer
        if capturer is None:
            return
        try:
            scope = {
                "trigger": "human_approval_request",
                "request_id": request.request_id,
                "approval_kind": request.kind,
                "sensitive": "1" if request.sensitive else "0",
            }
            for key, value in request.scope.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                if key in scope:
                    continue
                scope[f"req.{key}"] = value
            capturer.capture(source="approval_broker", scope=scope)
        except Exception:
            # Evidencia visual es "nice to have"; nunca debe tumbar al consumer.
            import logging
            logging.getLogger(__name__).exception(
                "ui_screenshot capturer failed for approval request %s",
                request.request_id,
            )

    def _finalise_without_handler(self, request: ApprovalRequest) -> None:
        with self._lock:
            entry = self._pending.pop(request.request_id, None)
        if entry is not None and not entry.future.done():
            entry.future.cancel()

    def _dispatch_post_resolve(
        self,
        request: ApprovalRequest,
        result: ApprovalResult,
    ) -> None:
        with self._lock:
            handlers = list(self._post_handlers)
        for handler in handlers:
            try:
                handler(request, result)
            except Exception:
                # Un observador roto no debe interrumpir al consumer original.
                continue
