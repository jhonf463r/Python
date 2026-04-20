"""Tests del ``CapabilityAuditHarness`` y los runner factories builtin.

Cubre:

* registro/introspección del harness;
* policies por defecto para las 5 capacidades iniciales;
* ``run()`` happy path, ``dry_run``, capability_not_registered,
  runner_raised, runner_returned_invalid_type;
* normalización de latencia (runner reporta vs harness mide);
* truncado de ``output_preview``;
* cada runner factory builtin (``llm_local_ollama``, ``llm_external_*``,
  ``browser_capture``, ``ui_execution``) ante los dos casos típicos
  (success / failure por causa esperada).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from iabv_v15.infra.mcp.audit_tools.audit_capability import (
    build_browser_capture_runner,
    build_llm_external_runner,
    build_llm_local_ollama_runner,
    build_ui_execution_runner,
)
from iabv_v15.services.evolution.capability_audit_harness import (
    CapabilityAuditHarness,
    CapabilityAuditPolicy,
    CapabilityAuditResult,
    DEFAULT_CAPABILITY_IDS,
    DEFAULT_POLICIES,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers


def _ok_runner(**_: Any) -> CapabilityAuditResult:
    return CapabilityAuditResult(
        capability_id="cap_x",
        executed=True,
        success=True,
        output_preview="all good",
    )


def _fail_runner(**_: Any) -> CapabilityAuditResult:
    return CapabilityAuditResult(
        capability_id="cap_x",
        executed=True,
        success=False,
        error="boom",
    )


# ---------------------------------------------------------------------------
# Registro / introspección


def test_default_capability_ids_stable() -> None:
    assert DEFAULT_CAPABILITY_IDS == (
        "llm_local_ollama",
        "llm_external_chatgpt",
        "llm_external_claude",
        "browser_capture",
        "ui_execution",
    )


def test_default_policies_flag_external_as_network() -> None:
    assert DEFAULT_POLICIES["llm_local_ollama"].requires_network is False
    assert DEFAULT_POLICIES["llm_external_chatgpt"].requires_network is True
    assert DEFAULT_POLICIES["llm_external_claude"].requires_network is True
    assert DEFAULT_POLICIES["browser_capture"].requires_network is True
    assert DEFAULT_POLICIES["ui_execution"].requires_network is False
    # external consume cuota; los locales no
    assert DEFAULT_POLICIES["llm_external_chatgpt"].consumes_quota is True
    assert DEFAULT_POLICIES["llm_local_ollama"].consumes_quota is False


def test_harness_register_and_list() -> None:
    h = CapabilityAuditHarness()
    assert h.list_capabilities() == ()
    h.register("cap_x", _ok_runner)
    h.register("cap_y", _fail_runner)
    assert h.list_capabilities() == ("cap_x", "cap_y")
    assert h.has_runner("cap_x")
    assert not h.has_runner("cap_z")


def test_harness_register_rejects_invalid_inputs() -> None:
    h = CapabilityAuditHarness()
    with pytest.raises(ValueError):
        h.register("", _ok_runner)
    with pytest.raises(ValueError):
        h.register("cap_x", None)  # type: ignore[arg-type]


def test_harness_policy_for_returns_default_when_unknown() -> None:
    h = CapabilityAuditHarness()
    policy = h.policy_for("brand_new_cap")
    assert policy.requires_network is False
    assert policy.assistant_kind == "audit"


def test_harness_register_can_override_policy() -> None:
    h = CapabilityAuditHarness()
    h.register(
        "cap_x",
        _ok_runner,
        policy=CapabilityAuditPolicy(requires_network=True, consumes_quota=True),
    )
    policy = h.policy_for("cap_x")
    assert policy.requires_network is True
    assert policy.consumes_quota is True


def test_harness_unregister_is_idempotent() -> None:
    h = CapabilityAuditHarness()
    h.register("cap_x", _ok_runner)
    h.unregister("cap_x")
    h.unregister("cap_x")  # no debe raisear
    assert not h.has_runner("cap_x")


# ---------------------------------------------------------------------------
# run() / dry_run


def test_run_invalid_capability_id() -> None:
    h = CapabilityAuditHarness()
    payload = h.run("   ")
    assert payload["executed"] is False
    assert payload["success"] is False
    assert payload["error"] == "invalid_capability_id"


def test_run_unknown_capability_returns_not_registered() -> None:
    h = CapabilityAuditHarness()
    h.register("cap_a", _ok_runner)
    payload = h.run("cap_missing")
    assert payload["executed"] is False
    assert payload["success"] is False
    assert payload["error"] == "capability_not_registered"
    # Policy siempre presente aun en error para que el caller sepa el gate.
    assert "policy" in payload
    assert payload["policy"]["assistant_kind"] == "audit"


def test_run_dry_run_does_not_execute_runner() -> None:
    calls: list[int] = []

    def _spy(**_: Any) -> CapabilityAuditResult:
        calls.append(1)
        return _ok_runner()

    h = CapabilityAuditHarness()
    h.register("cap_x", _spy)
    payload = h.run("cap_x", dry_run=True)
    assert calls == []
    assert payload["executed"] is False
    assert payload["success"] is True
    assert payload["dry_run"] is True
    assert payload["error"] is None


def test_run_happy_path_sets_latency_from_clock_when_runner_reports_zero() -> None:
    ticks = iter([100.0, 100.250])  # 250 ms
    h = CapabilityAuditHarness(clock=lambda: next(ticks))
    h.register("cap_x", _ok_runner)  # runner devuelve latency_ms=0

    payload = h.run("cap_x")
    assert payload["executed"] is True
    assert payload["success"] is True
    assert payload["latency_ms"] == 250
    assert payload["output_preview"] == "all good"


def test_run_prefers_runner_latency_when_runner_reports_non_zero() -> None:
    def _runner(**_: Any) -> CapabilityAuditResult:
        return CapabilityAuditResult(
            capability_id="cap_x",
            executed=True,
            success=True,
            latency_ms=42,
        )

    ticks = iter([0.0, 1.0])
    h = CapabilityAuditHarness(clock=lambda: next(ticks))
    h.register("cap_x", _runner)
    payload = h.run("cap_x")
    assert payload["latency_ms"] == 42  # usa la del runner, no 1000ms del clock


def test_run_catches_runner_exception() -> None:
    def _raising(**_: Any) -> CapabilityAuditResult:
        raise RuntimeError("explota")

    h = CapabilityAuditHarness()
    h.register("cap_x", _raising)
    payload = h.run("cap_x")
    assert payload["executed"] is True
    assert payload["success"] is False
    assert payload["error"] == "runner_raised"
    assert "RuntimeError" in payload["detail"]


def test_run_handles_runner_returning_invalid_type() -> None:
    def _bad(**_: Any) -> Any:
        return "no es CapabilityAuditResult"

    h = CapabilityAuditHarness()
    h.register("cap_x", _bad)
    payload = h.run("cap_x")
    assert payload["executed"] is True
    assert payload["success"] is False
    assert payload["error"] == "runner_returned_invalid_type"


def test_run_coerces_dict_result() -> None:
    def _dict_runner(**_: Any) -> Any:
        return {
            "capability_id": "cap_x",
            "executed": True,
            "success": True,
            "latency_ms": 17,
            "output_preview": "done",
            "error": None,
            "evidence": {"k": "v"},
        }

    h = CapabilityAuditHarness()
    h.register("cap_x", _dict_runner)
    payload = h.run("cap_x")
    assert payload["latency_ms"] == 17
    assert payload["evidence"] == {"k": "v"}


def test_run_clips_long_output_preview() -> None:
    long = "x" * 2000

    def _runner(**_: Any) -> CapabilityAuditResult:
        return CapabilityAuditResult(
            capability_id="cap_x",
            executed=True,
            success=True,
            output_preview=long,
        )

    h = CapabilityAuditHarness()
    h.register("cap_x", _runner)
    payload = h.run("cap_x")
    assert len(payload["output_preview"]) < len(long)
    assert payload["output_preview"].endswith("… (truncated)")


# ---------------------------------------------------------------------------
# Runner: llm_local_ollama


class _FakeHealth:
    def __init__(self, *, available: bool, reason: str = "") -> None:
        self.available = available
        self.reason = reason


class _FakeResult:
    def __init__(self, summary: str, provider_name: str = "ollama") -> None:
        self.summary = summary
        self.provider_name = provider_name
        self.report_kind = SimpleNamespace(value="standard")


class _FakeProvider:
    def __init__(self, *, health: _FakeHealth, summary: str | None = "OK",
                 raise_on_health: Exception | None = None,
                 raise_on_answer: Exception | None = None) -> None:
        self._health = health
        self._summary = summary
        self._raise_on_health = raise_on_health
        self._raise_on_answer = raise_on_answer
        self.calls: list[Any] = []

    def health_check(self) -> _FakeHealth:
        if self._raise_on_health is not None:
            raise self._raise_on_health
        return self._health

    def answer_user(self, request: Any) -> _FakeResult:
        self.calls.append(request)
        if self._raise_on_answer is not None:
            raise self._raise_on_answer
        return _FakeResult(summary=str(self._summary or ""))


def test_llm_local_ollama_runner_happy_path() -> None:
    provider = _FakeProvider(health=_FakeHealth(available=True), summary="OK")
    runner = build_llm_local_ollama_runner(provider)
    result = runner()
    assert result.capability_id == "llm_local_ollama"
    assert result.executed is True
    assert result.success is True
    assert result.output_preview == "OK"
    assert provider.calls, "debe haber invocado answer_user"


def test_llm_local_ollama_runner_reports_unhealthy() -> None:
    provider = _FakeProvider(
        health=_FakeHealth(available=False, reason="ollama_not_running"),
    )
    runner = build_llm_local_ollama_runner(provider)
    result = runner()
    assert result.executed is True
    assert result.success is False
    assert result.error == "provider_unhealthy"
    assert result.evidence["reason"] == "ollama_not_running"


def test_llm_local_ollama_runner_catches_health_exception() -> None:
    provider = _FakeProvider(
        health=_FakeHealth(available=True),
        raise_on_health=RuntimeError("no connection"),
    )
    runner = build_llm_local_ollama_runner(provider)
    result = runner()
    assert result.success is False
    assert result.error == "health_check_raised"


def test_llm_local_ollama_runner_catches_answer_exception() -> None:
    provider = _FakeProvider(
        health=_FakeHealth(available=True),
        raise_on_answer=TimeoutError("llm slow"),
    )
    runner = build_llm_local_ollama_runner(provider)
    result = runner()
    assert result.success is False
    assert result.error == "answer_raised"


def test_llm_local_ollama_runner_rejects_when_no_provider() -> None:
    runner = build_llm_local_ollama_runner(None)
    result = runner()
    assert result.executed is False
    assert result.success is False
    assert result.error == "provider_unavailable"


def test_llm_local_ollama_runner_reports_empty_response() -> None:
    provider = _FakeProvider(health=_FakeHealth(available=True), summary="  ")
    runner = build_llm_local_ollama_runner(provider)
    result = runner()
    assert result.success is False
    assert result.error == "empty_response"


# ---------------------------------------------------------------------------
# Runner: llm_external_*


def test_llm_external_runner_reports_not_logged_in() -> None:
    runner = build_llm_external_runner(
        "chatgpt",
        probe_login=lambda kind: {"logged_in": False, "reason": "login_page_detected"},
    )
    result = runner()
    assert result.capability_id == "llm_external_chatgpt"
    assert result.success is False
    assert result.error == "not_logged_in"
    assert result.evidence["login_reason"] == "login_page_detected"


def test_llm_external_runner_surfaces_governance_block() -> None:
    runner = build_llm_external_runner(
        "claude",
        probe_login=lambda kind: {"governance_blocked": True, "reason": "network_unavailable"},
    )
    result = runner()
    assert result.executed is False
    assert result.error == "governance_blocked"
    assert result.evidence["upstream"]["governance_blocked"] is True


def test_llm_external_runner_success_when_logged_in_and_no_send_prompt() -> None:
    runner = build_llm_external_runner(
        "chatgpt",
        probe_login=lambda kind: {"logged_in": True},
    )
    result = runner()
    assert result.success is True
    assert result.output_preview == "login_ok"
    assert result.evidence["login_only"] is True


def test_llm_external_runner_invokes_send_prompt_when_logged_in() -> None:
    calls: list[str] = []

    def _send(prompt: str) -> dict[str, Any]:
        calls.append(prompt)
        return {"success": True, "output_text": "Hola!"}

    runner = build_llm_external_runner(
        "chatgpt",
        probe_login=lambda kind: {"logged_in": True},
        send_prompt=_send,
    )
    result = runner()
    assert calls, "debe haber llamado send_prompt"
    assert result.success is True
    assert result.output_preview == "Hola!"


def test_llm_external_runner_catches_probe_exception() -> None:
    def _raise(_: str) -> Any:
        raise RuntimeError("bad mcp")

    runner = build_llm_external_runner("chatgpt", probe_login=_raise)
    result = runner()
    assert result.executed is True
    assert result.error == "probe_login_raised"


def test_llm_external_runner_catches_send_prompt_exception() -> None:
    def _raise(_: str) -> Any:
        raise TimeoutError("timeout")

    runner = build_llm_external_runner(
        "chatgpt",
        probe_login=lambda kind: {"logged_in": True},
        send_prompt=_raise,
    )
    result = runner()
    assert result.success is False
    assert result.error == "send_prompt_raised"


# ---------------------------------------------------------------------------
# Runner: browser_capture


class _FakePage:
    def __init__(self, *, title: str, content: str,
                 raise_on_goto: Exception | None = None) -> None:
        self._title = title
        self._content = content
        self._raise_on_goto = raise_on_goto
        self.goto_calls: list[tuple[str, int]] = []

    def goto(self, url: str, timeout: int = 10000) -> None:
        if self._raise_on_goto is not None:
            raise self._raise_on_goto
        self.goto_calls.append((url, timeout))

    def title(self) -> str:
        return self._title

    def content(self) -> str:
        return self._content


class _FakeBrowserController:
    def __init__(self, page: _FakePage | None,
                 *, raise_on_start: Exception | None = None) -> None:
        self._page = page
        self._raise_on_start = raise_on_start
        self.started = False
        self.closed = False

    def start(self) -> None:
        if self._raise_on_start is not None:
            raise self._raise_on_start
        self.started = True

    def close(self) -> None:
        self.closed = True

    @property
    def page(self) -> _FakePage | None:
        return self._page


def test_browser_capture_runner_happy_path() -> None:
    page = _FakePage(title="Example Domain", content="<html>Example Domain</html>")
    ctrl = _FakeBrowserController(page)
    runner = build_browser_capture_runner(lambda: ctrl)
    result = runner()
    assert result.capability_id == "browser_capture"
    assert result.success is True
    assert result.output_preview == "Example Domain"
    assert ctrl.started is True
    assert ctrl.closed is True
    assert page.goto_calls


def test_browser_capture_runner_reports_missing_substring() -> None:
    page = _FakePage(title="Other", content="<html>no match here</html>")
    ctrl = _FakeBrowserController(page)
    runner = build_browser_capture_runner(lambda: ctrl)
    result = runner()
    assert result.success is False
    assert result.error == "expected_substring_missing"
    assert ctrl.closed is True


def test_browser_capture_runner_handles_playwright_unavailable() -> None:
    runner = build_browser_capture_runner(lambda: None)
    result = runner()
    assert result.executed is False
    assert result.error == "playwright_unavailable"


def test_browser_capture_runner_handles_controller_init_failure() -> None:
    def _factory() -> Any:
        raise RuntimeError("no playwright")

    runner = build_browser_capture_runner(_factory)
    result = runner()
    assert result.executed is False
    assert result.error == "controller_init_failed"


def test_browser_capture_runner_handles_controller_start_failure_and_closes() -> None:
    ctrl = _FakeBrowserController(
        _FakePage(title="t", content="body"),
        raise_on_start=RuntimeError("no chrome"),
    )
    runner = build_browser_capture_runner(lambda: ctrl)
    result = runner()
    assert result.success is False
    assert result.error == "controller_start_failed"
    assert ctrl.closed is True  # close SIEMPRE, aun ante fallo


def test_browser_capture_runner_handles_goto_failure_and_closes() -> None:
    page = _FakePage(title="", content="", raise_on_goto=TimeoutError("slow"))
    ctrl = _FakeBrowserController(page)
    runner = build_browser_capture_runner(lambda: ctrl)
    result = runner()
    assert result.error == "goto_failed"
    assert ctrl.closed is True


def test_browser_capture_runner_handles_page_unavailable() -> None:
    ctrl = _FakeBrowserController(page=None)
    runner = build_browser_capture_runner(lambda: ctrl)
    result = runner()
    assert result.error == "page_unavailable"
    assert ctrl.closed is True


# ---------------------------------------------------------------------------
# Runner: ui_execution


def test_ui_execution_runner_reports_unavailable_when_no_executor() -> None:
    runner = build_ui_execution_runner(None)
    result = runner()
    assert result.executed is False
    assert result.error == "ui_execution_unavailable"


def test_ui_execution_runner_happy_path() -> None:
    runner = build_ui_execution_runner(lambda **_: {"success": True, "output_text": "moved"})
    result = runner()
    assert result.success is True
    assert result.output_preview == "moved"


def test_ui_execution_runner_reports_failure_when_executor_returns_non_ok() -> None:
    runner = build_ui_execution_runner(lambda **_: {"success": False})
    result = runner()
    assert result.success is False
    assert result.error == "executor_not_ok"


def test_ui_execution_runner_catches_executor_exception() -> None:
    def _raise(**_: Any) -> Any:
        raise RuntimeError("crash")

    runner = build_ui_execution_runner(_raise)
    result = runner()
    assert result.executed is True
    assert result.error == "executor_raised"
