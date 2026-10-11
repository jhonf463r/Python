"""Tests focalizados para HumanApprovalBroker."""
from __future__ import annotations

import threading
import time

import pytest

from iabv_v15.services.security.human_approval_broker import (
    ApprovalRequest,
    ApprovalResult,
    HumanApprovalBroker,
    KIND_CREDENTIAL_REQUEST,
    KIND_EXTERNAL_CALL_AUTHORIZATION,
    KIND_LOGIN_REQUIRED,
    KIND_MERGE_PR,
    KIND_PERCEPTION_MISMATCH,
)
from iabv_v15.services.security.system_principal_provider import SystemPrincipal


class _StaticPrincipalProvider:
    def __init__(self, principal: SystemPrincipal | None) -> None:
        self.principal = principal

    def get_principal(self) -> SystemPrincipal | None:
        return self.principal


def _start_approve_later(
    broker: HumanApprovalBroker,
    payload: dict | None = None,
    delay: float = 0.02,
    captured: dict | None = None,
) -> threading.Thread:
    """Helper: aprueba el ultimo request pendiente despues de `delay`."""

    def worker() -> None:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            pending = broker.pending_requests()
            if pending:
                request_id = pending[-1]["id"]
                if captured is not None:
                    captured["prompt"] = pending[-1]
                time.sleep(delay)
                broker.approve(request_id, payload=payload)
                return
            time.sleep(0.005)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def _start_reject_later(broker: HumanApprovalBroker, delay: float = 0.02) -> threading.Thread:
    def worker() -> None:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            pending = broker.pending_requests()
            if pending:
                time.sleep(delay)
                broker.reject(pending[-1]["id"])
                return
            time.sleep(0.005)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def test_request_blocks_until_approved_and_returns_payload():
    broker = HumanApprovalBroker()
    prompts: list[dict] = []
    broker.register_prompt_handler(lambda payload: prompts.append(payload))

    worker = _start_approve_later(broker, payload={"token": "gh_pat_xxx"})

    result = broker.request(
        kind=KIND_CREDENTIAL_REQUEST,
        reason="GitHub push needs elevated token",
        scope={"repo": "jhonf463r/Python"},
        payload_schema=("token",),
        sensitive=True,
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.approved is True
    assert result.rejected is False
    assert result.timed_out is False
    assert result.payload == {"token": "gh_pat_xxx"}
    assert result.payload_keys == ("token",)
    # Prompt enviado a UI no lleva payload sensible.
    assert len(prompts) == 1
    assert "token" not in prompts[0]
    assert prompts[0]["sensitive"] is True
    assert prompts[0]["kind"] == KIND_CREDENTIAL_REQUEST
    assert prompts[0]["scope"] == {"repo": "jhonf463r/Python"}


def test_request_returns_rejected_when_user_rejects():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    worker = _start_reject_later(broker)

    result = broker.request(
        kind=KIND_LOGIN_REQUIRED,
        reason="Claude desktop signed out",
        scope={"assistant": "claude"},
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.approved is False
    assert result.rejected is True
    assert result.timed_out is False
    assert result.payload is None


def test_request_times_out_when_no_response():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)

    result = broker.request(
        kind=KIND_LOGIN_REQUIRED,
        reason="Nobody home",
        scope={"assistant": "chatgpt"},
        timeout_s=0.05,
    )

    assert result.approved is False
    assert result.timed_out is True
    # Tras timeout, no queda residuo en el mapa interno.
    assert broker.pending_count() == 0
    assert broker.pending_requests() == []


def test_external_approval_requires_active_dialog_and_broker_derived_principal():
    principal = SystemPrincipal(sid='S-1-5-21-1000-2000-3000-1001', session_id=4)
    broker = HumanApprovalBroker(principal_provider=_StaticPrincipalProvider(principal))
    pre_approver_calls: list[str] = []
    caller_forgery: list[bool] = []
    cross_dialog: list[bool] = []
    request_ids: list[str] = []

    def auto_approve(request: ApprovalRequest) -> ApprovalResult:
        pre_approver_calls.append(request.request_id)
        return ApprovalResult(request_id=request.request_id, approved=True, auto_resolved=True)

    def active_control_center_dialog(prompt: dict) -> None:
        request_id = str(prompt['id'])
        request_ids.append(request_id)
        caller_forgery.append(broker.approve(request_id, payload={'approved_by': principal.sid}))
        cross_dialog.append(broker.approve_external_from_control_center(
            request_id, active_dialog_request_id='another-request'
        ))
        assert broker.pending_count() == 1
        assert broker.approve_external_from_control_center(
            request_id, active_dialog_request_id=request_id
        ) is True

    broker.set_pre_approver(auto_approve)
    broker.register_prompt_handler(active_control_center_dialog)
    result = broker.request(
        kind=KIND_EXTERNAL_CALL_AUTHORIZATION,
        reason='Authorize one task',
        scope={'task_id': 'task-1'},
        timeout_s=0.2,
    )

    assert pre_approver_calls == []
    assert caller_forgery == [False]
    assert cross_dialog == [False]
    assert result.approved is True
    assert result.payload is None
    assert result.approval_source == 'control_center_dialog'
    assert result.request_id == result.dialog_request_id == request_ids[0]
    assert result.approver_principal == principal
    assert result.approved_at_epoch is not None
    assert broker.approve_external_from_control_center(
        request_ids[0], active_dialog_request_id=request_ids[0]
    ) is False


def test_external_approval_fails_closed_without_principal_and_on_rejection_or_timeout():
    missing = HumanApprovalBroker(principal_provider=_StaticPrincipalProvider(None))
    missing.register_prompt_handler(lambda prompt: missing.approve_external_from_control_center(
        prompt['id'], active_dialog_request_id=prompt['id']
    ))
    missing_result = missing.request(
        kind=KIND_EXTERNAL_CALL_AUTHORIZATION,
        reason='Missing system identity',
        timeout_s=0.2,
    )
    assert missing_result.approved is False
    assert missing_result.rejected is True
    assert missing_result.principal_unavailable is True
    assert missing_result.approver_principal is None

    rejected = HumanApprovalBroker(principal_provider=_StaticPrincipalProvider(None))
    rejected.register_prompt_handler(lambda prompt: rejected.reject(prompt['id']))
    rejected_result = rejected.request(
        kind=KIND_EXTERNAL_CALL_AUTHORIZATION,
        reason='User closed/rejected dialog',
        timeout_s=0.2,
    )
    assert rejected_result.rejected is True
    assert rejected_result.approved is False

    cancelled = HumanApprovalBroker(principal_provider=_StaticPrincipalProvider(None))
    cancelled.register_prompt_handler(lambda _prompt: None)
    cancelled_results: list[ApprovalResult] = []
    cancel_thread = threading.Thread(target=lambda: cancelled_results.append(cancelled.request(
        kind=KIND_EXTERNAL_CALL_AUTHORIZATION,
        reason='Programmatic cancellation',
        timeout_s=1.0,
    )), daemon=True)
    cancel_thread.start()
    deadline = time.monotonic() + 2.0
    while not cancelled.pending_requests() and time.monotonic() < deadline:
        time.sleep(0.001)
    pending_id = cancelled.pending_requests()[0]['id']
    assert cancelled.cancel(pending_id) is True
    cancel_thread.join(timeout=1.0)
    assert cancelled.pending_count() == 0
    assert cancelled_results[0].cancelled is True

    timed_out = HumanApprovalBroker(principal_provider=_StaticPrincipalProvider(None))
    timed_out.register_prompt_handler(lambda prompt: None)
    timeout_result = timed_out.request(
        kind=KIND_EXTERNAL_CALL_AUTHORIZATION,
        reason='No human response',
        timeout_s=0.01,
    )
    assert timeout_result.timed_out is True
    assert timeout_result.approved is False


def test_pre_approver_bypasses_prompt():
    broker = HumanApprovalBroker()
    prompts: list[dict] = []
    broker.register_prompt_handler(lambda payload: prompts.append(payload))

    def auto_approve(request: ApprovalRequest) -> ApprovalResult | None:
        if request.scope.get("label") == "documentation_only":
            return ApprovalResult(
                request_id=request.request_id,
                approved=True,
                auto_resolved=True,
            )
        return None

    broker.set_pre_approver(auto_approve)

    result = broker.request(
        kind=KIND_MERGE_PR,
        reason="Merge docs PR",
        scope={"repo": "jhonf463r/Python", "label": "documentation_only"},
        timeout_s=1.0,
    )

    assert result.approved is True
    assert result.auto_resolved is True
    assert prompts == []  # nunca llego a la UI.


def test_pre_approver_returning_none_falls_through_to_prompt():
    broker = HumanApprovalBroker()
    prompts: list[dict] = []
    broker.register_prompt_handler(lambda payload: prompts.append(payload))
    broker.set_pre_approver(lambda request: None)

    worker = _start_approve_later(broker)
    result = broker.request(
        kind=KIND_MERGE_PR,
        reason="Merge risky PR",
        scope={"repo": "jhonf463r/Python", "label": "src_change"},
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.approved is True
    assert result.auto_resolved is False
    assert len(prompts) == 1


def test_post_resolve_handlers_receive_request_and_result():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    observed: list[tuple[ApprovalRequest, ApprovalResult]] = []
    broker.register_post_resolve_handler(lambda req, res: observed.append((req, res)))

    worker = _start_approve_later(broker)
    result = broker.request(
        kind=KIND_PERCEPTION_MISMATCH,
        reason="Ambiguous chatgpt window state",
        scope={"assistant": "chatgpt"},
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.approved is True
    assert len(observed) == 1
    req, res = observed[0]
    assert req.kind == KIND_PERCEPTION_MISMATCH
    assert res.approved is True


def test_post_resolve_handler_fired_on_auto_resolve_too():
    broker = HumanApprovalBroker()
    observed: list[ApprovalResult] = []
    broker.register_post_resolve_handler(lambda req, res: observed.append(res))

    def auto_approve(request: ApprovalRequest) -> ApprovalResult | None:
        return ApprovalResult(
            request_id=request.request_id,
            approved=True,
            auto_resolved=True,
        )

    broker.set_pre_approver(auto_approve)

    result = broker.request(
        kind=KIND_MERGE_PR,
        reason="Auto-approve test",
        scope={"repo": "jhonf463r/Python"},
        timeout_s=1.0,
    )

    assert result.approved is True
    assert len(observed) == 1
    assert observed[0].auto_resolved is True


def test_pending_requests_hides_sensitive_payload():
    broker = HumanApprovalBroker()
    captured: dict = {}
    broker.register_prompt_handler(lambda payload: captured.update(payload))
    worker = _start_approve_later(
        broker,
        payload={"token": "super_secret"},
    )

    # Antes del approve el token no existe en prompt ni en pending dump.
    result = broker.request(
        kind=KIND_CREDENTIAL_REQUEST,
        reason="test",
        scope={"provider": "github"},
        payload_schema=("token",),
        sensitive=True,
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert "token" not in captured
    assert captured.get("sensitive") is True
    assert result.payload == {"token": "super_secret"}


def test_request_without_prompt_handler_times_out_immediately():
    broker = HumanApprovalBroker()
    result = broker.request(
        kind=KIND_LOGIN_REQUIRED,
        reason="no UI",
        scope={},
        timeout_s=1.0,
    )
    assert result.timed_out is True
    assert result.approved is False
    assert broker.pending_count() == 0


def test_cancel_resolves_pending_request():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)

    cancelled_ids: list[str] = []

    def cancel_later() -> None:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            pending = broker.pending_requests()
            if pending:
                rid = pending[-1]["id"]
                broker.cancel(rid)
                cancelled_ids.append(rid)
                return
            time.sleep(0.005)

    t = threading.Thread(target=cancel_later, daemon=True)
    t.start()

    result = broker.request(
        kind=KIND_EXTERNAL_CALL_AUTHORIZATION,
        reason="unused",
        scope={},
        timeout_s=2.0,
    ) if False else None
    # ^ evitamos variable inaccesible; rehacemos explicitamente:
    result = broker.request(
        kind="external_call_authorization",
        reason="caller cancelled",
        scope={},
        timeout_s=2.0,
    )
    t.join(timeout=2.0)

    assert result.cancelled is True
    assert result.approved is False
    assert result.rejected is False
    assert result.timed_out is False
    assert cancelled_ids  # confirmamos que cancel() se ejecuto via pending_requests
    assert result.request_id == cancelled_ids[-1]


def test_empty_kind_raises():
    broker = HumanApprovalBroker()
    with pytest.raises(ValueError):
        broker.request(kind="", reason="oops", scope={})


def test_approve_reject_unknown_id_returns_false():
    broker = HumanApprovalBroker()
    assert broker.approve("does-not-exist") is False
    assert broker.reject("does-not-exist") is False
    assert broker.cancel("does-not-exist") is False


def test_broken_post_resolve_handler_does_not_break_request():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    broker.register_post_resolve_handler(lambda req, res: (_ for _ in ()).throw(RuntimeError("boom")))
    ok_observed: list[ApprovalResult] = []
    broker.register_post_resolve_handler(lambda req, res: ok_observed.append(res))

    worker = _start_approve_later(broker)
    result = broker.request(
        kind=KIND_LOGIN_REQUIRED,
        reason="test",
        scope={"assistant": "chatgpt"},
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.approved is True
    # Observador bueno igual recibio el resultado pese al otro handler roto.
    assert len(ok_observed) == 1


# ---- F1.2: UI screenshot capturer --------------------------------------


class _FakeCapturer:
    """Capturer in-memory para los tests de wiring (no toca disco).

    Registra cada llamada a `capture` asi el test puede verificar scope y
    source sin requerir un UIScreenshotService completo.
    """

    def __init__(self, raise_exc: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self._raise_exc = raise_exc

    def capture(
        self,
        *,
        source: str,
        scope=None,
        session_id: str | None = None,
    ) -> object:
        self.calls.append(
            {
                "source": source,
                "scope": dict(scope or {}),
                "session_id": session_id,
            }
        )
        if self._raise_exc is not None:
            raise self._raise_exc
        return object()


def test_capturer_is_called_when_human_prompt_is_emitted():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    capturer = _FakeCapturer()
    broker.set_ui_screenshot_capturer(capturer)

    worker = _start_approve_later(broker, payload={"token": "gh_pat"})
    broker.request(
        kind=KIND_CREDENTIAL_REQUEST,
        reason="need token",
        scope={"repo": "jhonf463r/Python"},
        payload_schema=("token",),
        sensitive=True,
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert len(capturer.calls) == 1
    call = capturer.calls[0]
    assert call["source"] == "approval_broker"
    scope = call["scope"]
    assert scope["trigger"] == "human_approval_request"
    assert scope["approval_kind"] == KIND_CREDENTIAL_REQUEST
    assert scope["sensitive"] == "1"
    assert "request_id" in scope
    # El scope del request se proyecta con prefijo req.*
    assert scope["req.repo"] == "jhonf463r/Python"


def test_capturer_not_called_when_pre_approver_auto_resolves():
    """ApprovalMemory auto-resolve no requiere presencia humana -> no captura."""
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    capturer = _FakeCapturer()
    broker.set_ui_screenshot_capturer(capturer)

    def pre(req: ApprovalRequest) -> ApprovalResult:
        return ApprovalResult(
            request_id=req.request_id,
            approved=True,
            auto_resolved=True,
        )

    broker.set_pre_approver(pre)

    result = broker.request(
        kind=KIND_MERGE_PR,
        reason="pre-approved by memory",
        scope={"repo": "jhonf463r/Python"},
        timeout_s=1.0,
    )

    assert result.approved is True
    assert result.auto_resolved is True
    assert capturer.calls == []


def test_capturer_exception_does_not_break_approval_flow():
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    capturer = _FakeCapturer(raise_exc=RuntimeError("provider blew up"))
    broker.set_ui_screenshot_capturer(capturer)

    worker = _start_approve_later(broker)
    result = broker.request(
        kind=KIND_LOGIN_REQUIRED,
        reason="need login",
        scope={"assistant": "chatgpt"},
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.approved is True
    # Se intento capturar aunque haya explotado.
    assert len(capturer.calls) == 1


def test_capturer_unset_is_safe():
    """Sin capturer registrado el broker sigue emitiendo prompts normales."""
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda payload: None)
    # set a capturer and then clear it:
    broker.set_ui_screenshot_capturer(_FakeCapturer())
    broker.set_ui_screenshot_capturer(None)

    worker = _start_reject_later(broker)
    result = broker.request(
        kind=KIND_PERCEPTION_MISMATCH,
        reason="ambiguous",
        scope={"window": "chrome"},
        timeout_s=2.0,
    )
    worker.join(timeout=2.0)

    assert result.rejected is True
