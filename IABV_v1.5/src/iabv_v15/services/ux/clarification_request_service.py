"""ClarificationRequestService: bloquea al backend hasta que el usuario aclare.

La capa UI recibe la pregunta via clarificationRequested (dict con id, pregunta,
opciones y contexto) y responde llamando resolve(id, answer). El servicio
gestiona timeouts y cancelaciones.
"""
from __future__ import annotations

import threading
import uuid
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from typing import Callable, Optional


PromptHandler = Callable[[dict], None]


class ClarificationTimeoutError(TimeoutError):
    """Se alcanza el timeout_s sin respuesta del usuario."""


class ClarificationCancelledError(RuntimeError):
    """La solicitud fue cancelada antes de resolverse."""


class ClarificationRequestService:
    def __init__(self) -> None:
        self._handler: Optional[PromptHandler] = None
        self._lock = threading.RLock()
        self._pending: dict[str, Future[str]] = {}

    # ---- public API -------------------------------------------------

    def register_prompt_handler(self, handler: PromptHandler) -> None:
        with self._lock:
            self._handler = handler

    def ask(
        self,
        question: str,
        options: list[str] | None = None,
        context: str | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """Emite clarificationRequested y bloquea hasta obtener respuesta."""
        request_id = uuid.uuid4().hex
        future: Future[str] = Future()
        with self._lock:
            self._pending[request_id] = future
            handler = self._handler
        payload = {
            "id": request_id,
            "question": question,
            "options": list(options or []),
            "context": context or "",
        }
        if handler is None:
            with self._lock:
                self._pending.pop(request_id, None)
            raise ClarificationTimeoutError(
                f"Clarification {request_id} dropped: no handler registered"
            )
        handler(payload)
        try:
            if timeout_s is None:
                return future.result()
            return future.result(timeout=timeout_s)
        except FutureTimeoutError as exc:
            with self._lock:
                self._pending.pop(request_id, None)
            if not future.done():
                future.cancel()
            raise ClarificationTimeoutError(
                f"Clarification {request_id} expired after {timeout_s}s"
            ) from exc
        finally:
            with self._lock:
                self._pending.pop(request_id, None)

    def resolve(self, request_id: str, response: str) -> bool:
        """Llamada por la UI cuando el usuario contesta. True si se resolvio."""
        with self._lock:
            future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(response)
        return True

    def cancel(self, request_id: str, reason: str = "cancelled") -> bool:
        with self._lock:
            future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_exception(ClarificationCancelledError(reason))
        return True

    def pending_ids(self) -> list[str]:
        with self._lock:
            return list(self._pending.keys())
