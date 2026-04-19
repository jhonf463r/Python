from __future__ import annotations

import threading

import pytest

from iabv_v15.services.ux.clarification_request_service import (
    ClarificationCancelledError,
    ClarificationRequestService,
    ClarificationTimeoutError,
)


def test_ask_future_resolves_with_user_response() -> None:
    service = ClarificationRequestService()
    captured: list[dict] = []

    def handler(payload: dict) -> None:
        captured.append(payload)
        # Simula respuesta del usuario desde otro hilo.
        threading.Thread(
            target=lambda: service.resolve(payload["id"], "opcion_a"),
            daemon=True,
        ).start()

    service.register_prompt_handler(handler)

    answer = service.ask(
        question="Que ruta prefieres?",
        options=["opcion_a", "opcion_b"],
        context="Evaluacion adaptativa",
        timeout_s=2.0,
    )

    assert answer == "opcion_a"
    assert captured[0]["question"] == "Que ruta prefieres?"
    assert captured[0]["options"] == ["opcion_a", "opcion_b"]
    assert captured[0]["context"] == "Evaluacion adaptativa"
    assert isinstance(captured[0]["id"], str) and captured[0]["id"]


def test_ask_raises_timeout_when_no_response() -> None:
    service = ClarificationRequestService()
    service.register_prompt_handler(lambda payload: None)

    with pytest.raises(ClarificationTimeoutError):
        service.ask(question="?", timeout_s=0.05)

    assert service.pending_ids() == []


def test_cancel_propagates_error_to_caller() -> None:
    service = ClarificationRequestService()
    received: list[dict] = []

    def handler(payload: dict) -> None:
        received.append(payload)
        threading.Timer(0.02, lambda: service.cancel(payload["id"], reason="aborted")).start()

    service.register_prompt_handler(handler)

    with pytest.raises(ClarificationCancelledError):
        service.ask(question="?", timeout_s=2.0)


def test_resolve_unknown_request_returns_false() -> None:
    service = ClarificationRequestService()
    assert service.resolve("does-not-exist", "anything") is False
