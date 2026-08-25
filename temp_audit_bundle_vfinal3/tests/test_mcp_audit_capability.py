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

from iabv_v15.domain.models import CapabilityReadiness, CapabilityStatus
from iabv_v15.infra.mcp.audit_tools.audit_capability import (
    audit_capability,
    build_domain_capability_runner,
    known_capability_ids,
    policy_for_capability,
)
from iabv_v15.services.evolution.capability_audit_harness import (
    CapabilityAuditHarness,
    CapabilityAuditResult,
    DOMAIN_CAPABILITY_IDS,
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


# ---------------------------------------------------------------------------
# build_domain_capability_runner — PR #3 (registra wplay.* + browser.*)


def test_domain_capability_ids_stable() -> None:
    assert DOMAIN_CAPABILITY_IDS == (
        "wplay.login",
        "wplay.session.restore",
        "wplay.navigate.casino",
        "browser.search.google",
        "browser.generic.navigation",
    )


def test_domain_capability_policies_dont_require_network() -> None:
    for cid in DOMAIN_CAPABILITY_IDS:
        policy = policy_for_capability(cid)
        assert policy.requires_network is False, cid
        assert policy.consumes_quota is False, cid


def test_domain_runner_emits_pack_not_captured_when_readiness_missing() -> None:
    runner = build_domain_capability_runner(
        "wplay.login",
        site_id="wplay",
        readiness_provider=lambda _cid, _site: None,
    )
    result = runner()
    assert result.capability_id == "wplay.login"
    assert result.executed is True
    assert result.success is False
    assert result.error == "capability_pack_not_captured"
    assert result.evidence["site_id"] == "wplay"
    assert "TeachingStudio" in result.evidence["requires"]
    assert "wplay.login" in result.evidence["requires"]


def test_domain_runner_reports_success_when_readiness_ready() -> None:
    readiness = CapabilityReadiness(
        capability_id="wplay.login",
        title="Login de Wplay preparado",
        status=CapabilityStatus.READY,
        score=0.91,
        site_id="wplay",
        evidence=["login_status=ready", "critical_object_coverage=0.8"],
    )
    runner = build_domain_capability_runner(
        "wplay.login",
        site_id="wplay",
        readiness_provider=lambda _cid, _site: readiness,
    )
    result = runner()
    assert result.success is True
    assert result.error is None
    assert result.output_preview == "Login de Wplay preparado"
    assert result.evidence["status"] == "ready"
    assert result.evidence["score"] == 0.91
    assert result.evidence["site_id"] == "wplay"


def test_domain_runner_reports_ready_with_approval_as_success() -> None:
    readiness = CapabilityReadiness(
        capability_id="wplay.navigate.casino",
        title="Casino preparado con aprobacion",
        status=CapabilityStatus.READY_WITH_APPROVAL,
        score=0.7,
        site_id="wplay",
    )
    runner = build_domain_capability_runner(
        "wplay.navigate.casino",
        site_id="wplay",
        readiness_provider=lambda _cid, _site: readiness,
    )
    result = runner()
    assert result.success is True
    assert result.evidence["status"] == "ready_with_approval"


def test_domain_runner_reports_partial_status() -> None:
    readiness = CapabilityReadiness(
        capability_id="wplay.session.restore",
        title="Restore parcial",
        status=CapabilityStatus.PARTIAL,
        score=0.4,
        site_id="wplay",
        missing_signals=["critical_object_coverage", "red_count_zero"],
        suggested_next_step="Recapturar login con critical_object_coverage>=0.66",
    )
    runner = build_domain_capability_runner(
        "wplay.session.restore",
        site_id="wplay",
        readiness_provider=lambda _cid, _site: readiness,
    )
    result = runner()
    assert result.success is False
    assert result.error == "capability_status_partial"
    assert result.evidence["status"] == "partial"
    assert "critical_object_coverage" in result.evidence["missing_signals"]
    assert result.evidence["suggested_next_step"].startswith("Recapturar login")


def test_domain_runner_reports_insufficient_as_pack_not_captured() -> None:
    readiness = CapabilityReadiness(
        capability_id="wplay.login",
        title="Insuficiente",
        status=CapabilityStatus.INSUFFICIENT,
        score=0.0,
        site_id="wplay",
    )
    runner = build_domain_capability_runner(
        "wplay.login",
        site_id="wplay",
        readiness_provider=lambda _cid, _site: readiness,
    )
    result = runner()
    assert result.success is False
    assert result.error == "capability_pack_not_captured"
    assert result.evidence["status"] == "insufficient"


def test_domain_runner_captures_readiness_provider_exception() -> None:
    def _boom(_cid: str, _site: Any) -> Any:
        raise RuntimeError("repo offline")

    runner = build_domain_capability_runner(
        "wplay.login",
        site_id="wplay",
        readiness_provider=_boom,
    )
    result = runner()
    assert result.success is False
    assert result.error == "readiness_provider_raised"
    assert "repo offline" in result.evidence["exception"]


def test_domain_runner_works_through_harness_and_audit_tool() -> None:
    readiness = CapabilityReadiness(
        capability_id="browser.search.google",
        title="Busqueda en Google",
        status=CapabilityStatus.READY,
        score=0.8,
        site_id="google",
    )
    h = CapabilityAuditHarness()
    h.register(
        "browser.search.google",
        build_domain_capability_runner(
            "browser.search.google",
            site_id="google",
            readiness_provider=lambda _cid, _site: readiness,
        ),
    )
    payload = audit_capability(
        "browser.search.google",
        harness=h,
        now_utc=_fixed_now,
    )
    assert payload["executed"] is True
    assert payload["success"] is True
    assert payload["output_preview"] == "Busqueda en Google"
    assert payload["evidence"]["status"] == "ready"
    # La policy default registrada no pide red.
    assert payload["policy"]["requires_network"] is False
    assert payload["checked_at_iso"].startswith("2026-04-20")
