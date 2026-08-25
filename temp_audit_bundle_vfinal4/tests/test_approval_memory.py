"""Tests focalizados para ApprovalMemory."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from iabv_v15.services.security.approval_memory import (
    ApprovalMemory,
    ApprovalPolicy,
    DECISION_APPROVED,
    DECISION_REJECTED,
)
from iabv_v15.services.security.human_approval_broker import (
    ApprovalRequest,
    HumanApprovalBroker,
    KIND_CREDENTIAL_REQUEST,
    KIND_LOGIN_REQUIRED,
    KIND_MERGE_PR,
)


def _req(
    *,
    kind: str = KIND_MERGE_PR,
    scope: dict | None = None,
    payload_schema: tuple[str, ...] = (),
    reason: str = "test",
) -> ApprovalRequest:
    return ApprovalRequest(
        request_id="req-" + kind,
        kind=kind,
        reason=reason,
        scope=dict(scope or {}),
        payload_schema=payload_schema,
        sensitive=False,
        requested_at_epoch=0.0,
    )


def test_remember_persists_and_survives_reload(tmp_path: Path):
    path = tmp_path / "policies.json"
    mem = ApprovalMemory(storage_path=path, clock=lambda: 1000.0)

    pid = mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python", "label": "docs"},
        kinds=[KIND_MERGE_PR],
        note="approve docs merges for this repo",
    )

    assert pid
    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert len(raw["policies"]) == 1

    # Otra instancia debe leerla tal cual.
    mem2 = ApprovalMemory(storage_path=path, clock=lambda: 2000.0)
    policies = mem2.list_policies()
    assert len(policies) == 1
    assert policies[0].decision == DECISION_APPROVED
    assert policies[0].scope_pattern == {"repo": "jhonf463r/Python", "label": "docs"}
    assert policies[0].kinds == frozenset({KIND_MERGE_PR})


def test_pre_approver_auto_approves_matching_request(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 10.0)
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python", "label": "docs"},
        kinds=[KIND_MERGE_PR],
    )

    request = _req(
        kind=KIND_MERGE_PR,
        scope={"repo": "jhonf463r/Python", "label": "docs", "pr_number": "42"},
    )
    result = mem.pre_approver(request)

    assert result is not None
    assert result.approved is True
    assert result.auto_resolved is True


def test_pre_approver_auto_rejects_matching_request(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 10.0)
    mem.remember(
        decision=DECISION_REJECTED,
        scope_pattern={"kind": "destructive", "target": "/etc"},
    )

    request = _req(
        kind="destructive_action",
        scope={"kind": "destructive", "target": "/etc", "cmd": "rm -rf"},
    )
    result = mem.pre_approver(request)

    assert result is not None
    assert result.approved is False
    assert result.rejected is True
    assert result.auto_resolved is True


def test_pre_approver_returns_none_when_no_match(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 10.0)
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python"},
    )
    request = _req(scope={"repo": "otro/repo"})
    assert mem.pre_approver(request) is None


def test_pre_approver_refuses_when_payload_schema_required(tmp_path: Path):
    """Si la solicitud necesita un secret/valor, memoria NUNCA auto-resuelve."""
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 10.0)
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"provider": "github"},
    )
    request = _req(
        kind=KIND_CREDENTIAL_REQUEST,
        scope={"provider": "github"},
        payload_schema=("token",),
    )
    assert mem.pre_approver(request) is None


def test_pre_approver_prefers_most_specific_policy(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 10.0)
    # Politica general: aprueba cualquier merge_pr del repo.
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python"},
        kinds=[KIND_MERGE_PR],
    )
    # Politica especifica: rechaza merges con label=risky.
    mem.remember(
        decision=DECISION_REJECTED,
        scope_pattern={"repo": "jhonf463r/Python", "label": "risky"},
        kinds=[KIND_MERGE_PR],
    )
    request = _req(
        kind=KIND_MERGE_PR,
        scope={"repo": "jhonf463r/Python", "label": "risky"},
    )
    result = mem.pre_approver(request)
    assert result is not None
    assert result.rejected is True


def test_kind_filter_is_honored(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 10.0)
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python"},
        kinds=[KIND_MERGE_PR],  # solo merge_pr
    )
    # kind distinto: no matchea.
    request = _req(kind=KIND_LOGIN_REQUIRED, scope={"repo": "jhonf463r/Python"})
    assert mem.pre_approver(request) is None
    # kind coincide: matchea.
    request2 = _req(kind=KIND_MERGE_PR, scope={"repo": "jhonf463r/Python"})
    assert mem.pre_approver(request2) is not None


def test_ttl_expires_policy(tmp_path: Path):
    now_holder = {"t": 100.0}
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: now_holder["t"])
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python"},
        ttl_s=60.0,
    )
    request = _req(scope={"repo": "jhonf463r/Python"})

    # Dentro de TTL -> matchea.
    now_holder["t"] = 150.0
    assert mem.pre_approver(request) is not None

    # Fuera de TTL -> no matchea.
    now_holder["t"] = 200.0
    assert mem.pre_approver(request) is None


def test_clear_expired_removes_them(tmp_path: Path):
    now_holder = {"t": 0.0}
    mem = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: now_holder["t"])
    mem.remember(decision=DECISION_APPROVED, scope_pattern={"a": "1"}, ttl_s=10.0)
    mem.remember(decision=DECISION_APPROVED, scope_pattern={"a": "2"})  # sin TTL
    now_holder["t"] = 100.0

    removed = mem.clear_expired()
    assert removed == 1
    policies = mem.list_policies()
    assert len(policies) == 1
    assert policies[0].scope_pattern == {"a": "2"}


def test_forget_removes_policy(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json")
    pid = mem.remember(decision=DECISION_APPROVED, scope_pattern={"x": "y"})
    assert mem.forget(pid) is True
    assert mem.list_policies() == []
    # idempotent.
    assert mem.forget(pid) is False


def test_remember_rejects_invalid_decision(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "p.json")
    with pytest.raises(ValueError):
        mem.remember(decision="maybe", scope_pattern={})


def test_usage_count_increments_on_auto_resolve(tmp_path: Path):
    path = tmp_path / "p.json"
    mem = ApprovalMemory(storage_path=path)
    pid = mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python"},
    )
    request = _req(scope={"repo": "jhonf463r/Python"})

    mem.pre_approver(request)
    mem.pre_approver(request)
    mem.pre_approver(request)

    policies = mem.list_policies()
    assert len(policies) == 1
    assert policies[0].policy_id == pid
    assert policies[0].usage_count == 3
    # Persistencia tambien refleja el contador.
    reloaded = ApprovalMemory(storage_path=path)
    assert reloaded.list_policies()[0].usage_count == 3


def test_integration_with_human_approval_broker(tmp_path: Path):
    """Memory conectada al broker resuelve sin preguntar a la UI."""
    mem = ApprovalMemory(storage_path=tmp_path / "p.json")
    mem.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python", "label": "docs"},
        kinds=[KIND_MERGE_PR],
    )

    broker = HumanApprovalBroker()
    prompts: list[dict] = []
    broker.register_prompt_handler(lambda payload: prompts.append(payload))
    broker.set_pre_approver(mem.pre_approver)

    result = broker.request(
        kind=KIND_MERGE_PR,
        reason="merge the docs fix",
        scope={"repo": "jhonf463r/Python", "label": "docs", "pr_number": "42"},
        timeout_s=1.0,
    )

    assert result.approved is True
    assert result.auto_resolved is True
    assert prompts == []  # nunca se emite prompt a la UI


def test_malformed_storage_file_does_not_crash(tmp_path: Path):
    path = tmp_path / "p.json"
    path.write_text("{not valid json", encoding="utf-8")
    # No debe explotar: deja la memoria vacia.
    mem = ApprovalMemory(storage_path=path)
    assert mem.list_policies() == []


def test_missing_storage_file_is_tolerated(tmp_path: Path):
    mem = ApprovalMemory(storage_path=tmp_path / "does_not_exist.json")
    assert mem.list_policies() == []
    # Primera escritura crea archivo y padre si hace falta.
    mem.remember(decision=DECISION_APPROVED, scope_pattern={"a": "b"})
    assert (tmp_path / "does_not_exist.json").exists()


def test_policy_json_roundtrip():
    policy = ApprovalPolicy(
        policy_id="abc",
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "r", "label": "l"},
        kinds=frozenset({"merge_pr", "login_required"}),
        ttl_s=3600.0,
        created_at_epoch=12345.0,
        note="hello",
        usage_count=5,
    )
    rebuilt = ApprovalPolicy.from_json(policy.to_json())
    assert rebuilt == policy
