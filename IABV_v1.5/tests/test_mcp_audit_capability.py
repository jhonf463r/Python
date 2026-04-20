"""Tests de la tool MCP ``audit_capability`` a nivel de módulo.

Verifica:

* invalid_capability_id
* harness_unavailable (ni harness ni factory)
* harness_init_failed (factory raisea)
* delegación correcta al harness (dry_run, happy path)
* ``checked_at_iso`` se añade siempre.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from iabv_v15.infra.mcp.audit_tools.audit_capability import (
    audit_capability,
    known_capability_ids,
    policy_for_capability,
)
from iabv_v15.services.evolution.capability_audit_harness import (
    CapabilityAuditHarness,
    CapabilityAuditResult,
)


def _fixed_now() -> datetime:
    return datetime(2026, 4, 20, 1, 23, 45, tzinfo=timezone.utc)


def test_known_capability_ids_is_stable() -> None:
    ids = known_capability_ids()
    assert ids == (
        "llm_local_ollama",
        "llm_external_chatgpt",
        "llm_external_claude",
        "browser_capture",
        "ui_execution",
    )


def test_policy_for_capability_returns_public_policy() -> None:
    policy = policy_for_capability("llm_external_chatgpt")
    assert policy.requires_network is True
    assert policy.consumes_quota is True


def test_policy_for_capability_unknown_returns_default() -> None:
    policy = policy_for_capability("nope")
    assert policy.requires_network is False
    assert policy.assistant_kind == "audit"


def test_audit_capability_invalid_id() -> None:
    payload = audit_capability("   ", now_utc=_fixed_now)
    assert payload["error"] == "invalid_capability_id"
    assert payload["checked_at_iso"].startswith("2026-04-20")


def test_audit_capability_harness_unavailable() -> None:
    payload = audit_capability(
        "llm_local_ollama",
        harness=None,
        harness_factory=None,
        now_utc=_fixed_now,
    )
    assert payload["error"] == "harness_unavailable"
    assert payload["capability_id"] == "llm_local_ollama"


def test_audit_capability_harness_init_failed() -> None:
    def _bad() -> Any:
        raise RuntimeError("wiring roto")

    payload = audit_capability(
        "llm_local_ollama",
        harness_factory=_bad,
        now_utc=_fixed_now,
    )
    assert payload["error"] == "harness_init_failed"
    assert "wiring roto" in payload["detail"]


def test_audit_capability_delegates_to_harness_happy_path() -> None:
    h = CapabilityAuditHarness()
    h.register(
        "llm_local_ollama",
        lambda **_: CapabilityAuditResult(
            capability_id="llm_local_ollama",
            executed=True,
            success=True,
            output_preview="OK",
            latency_ms=33,
        ),
    )
    payload = audit_capability("llm_local_ollama", harness=h, now_utc=_fixed_now)
    assert payload["executed"] is True
    assert payload["success"] is True
    assert payload["output_preview"] == "OK"
    assert payload["latency_ms"] == 33
    assert payload["checked_at_iso"].startswith("2026-04-20")
    # Policy se propaga.
    assert payload["policy"]["requires_network"] is False


def test_audit_capability_dry_run_does_not_execute() -> None:
    calls: list[int] = []

    def _runner(**_: Any) -> CapabilityAuditResult:
        calls.append(1)
        return CapabilityAuditResult(
            capability_id="llm_local_ollama",
            executed=True,
            success=True,
        )

    h = CapabilityAuditHarness()
    h.register("llm_local_ollama", _runner)
    payload = audit_capability(
        "llm_local_ollama",
        dry_run=True,
        harness=h,
        now_utc=_fixed_now,
    )
    assert calls == []
    assert payload["dry_run"] is True
    assert payload["executed"] is False
    assert payload["success"] is True


def test_audit_capability_unknown_capability_propagates_error() -> None:
    h = CapabilityAuditHarness()
    payload = audit_capability("nope", harness=h, now_utc=_fixed_now)
    assert payload["error"] == "capability_not_registered"
    assert "checked_at_iso" in payload


def test_audit_capability_uses_factory_when_harness_none() -> None:
    h = CapabilityAuditHarness()
    h.register(
        "llm_local_ollama",
        lambda **_: CapabilityAuditResult(
            capability_id="llm_local_ollama",
            executed=True,
            success=True,
        ),
    )
    payload = audit_capability(
        "llm_local_ollama",
        harness=None,
        harness_factory=lambda: h,
        now_utc=_fixed_now,
    )
    assert payload["success"] is True
