"""Tests focalizados para ProactiveDashboardService."""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from iabv_v15.services.security.approval_memory import (
    ApprovalMemory,
    DECISION_APPROVED,
    DECISION_REJECTED,
)
from iabv_v15.services.security.human_approval_broker import (
    HumanApprovalBroker,
    KIND_CREDENTIAL_REQUEST,
    KIND_LOGIN_REQUIRED,
    KIND_MERGE_PR,
    KIND_PERCEPTION_MISMATCH,
)
from iabv_v15.services.security.proactive_dashboard_service import (
    DashboardEntry,
    DashboardSnapshot,
    ENTRY_KIND_APPROVAL_REQUEST,
    ENTRY_KIND_LEARNED_POLICY,
    ProactiveDashboardService,
    SEVERITY_ATTENTION,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
)


def _raise_pending_request(
    broker: HumanApprovalBroker,
    *,
    kind: str,
    scope: dict,
    reason: str = "test",
    payload_schema: tuple[str, ...] = (),
    sensitive: bool = False,
) -> threading.Thread:
    """Dispara un request en otro hilo para dejarlo pendiente (no se aprueba)."""

    def worker() -> None:
        broker.request(
            kind=kind,
            reason=reason,
            scope=scope,
            payload_schema=payload_schema,
            sensitive=sensitive,
            timeout_s=10.0,
        )

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def _wait_for_pending(broker: HumanApprovalBroker, expected: int, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if broker.pending_count() >= expected:
            return
        time.sleep(0.005)
    raise AssertionError(f"expected {expected} pending, got {broker.pending_count()}")


def test_snapshot_empty_when_nothing_pending(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    svc = ProactiveDashboardService(broker=broker, memory=memory, clock=lambda: 100.0)

    snap = svc.snapshot()
    assert snap.generated_at_epoch == 100.0
    assert snap.entries == ()
    assert snap.pending_attention_count == 0
    assert snap.learned_policies_count == 0
    assert snap.has_attention_items() is False


def test_snapshot_includes_approval_request_as_critical(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    svc = ProactiveDashboardService(broker=broker, memory=memory, clock=lambda: 1.0)

    t = _raise_pending_request(
        broker,
        kind=KIND_LOGIN_REQUIRED,
        scope={"assistant": "chatgpt"},
        reason="ChatGPT desktop is signed out",
    )
    _wait_for_pending(broker, 1)

    snap = svc.snapshot()
    try:
        assert snap.pending_attention_count == 1
        assert snap.has_attention_items() is True
        assert len(snap.entries) == 1
        entry = snap.entries[0]
        assert entry.kind == ENTRY_KIND_APPROVAL_REQUEST
        assert entry.severity == SEVERITY_CRITICAL
        assert entry.actionable is True
        assert entry.title.startswith("Login requerido en chatgpt")
        assert entry.detail == "ChatGPT desktop is signed out"
        assert entry.scope == {"assistant": "chatgpt"}
    finally:
        # cancelar el pending para que el hilo termine
        for p in broker.pending_requests():
            broker.cancel(p["id"])
        t.join(timeout=2.0)


def test_snapshot_marks_merge_pr_as_attention_not_critical(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    svc = ProactiveDashboardService(broker=broker, memory=memory)

    t = _raise_pending_request(
        broker,
        kind=KIND_MERGE_PR,
        scope={"repo": "jhonf463r/Python", "pr_number": "42"},
        reason="merge docs PR",
    )
    _wait_for_pending(broker, 1)

    snap = svc.snapshot()
    try:
        entry = snap.entries[0]
        assert entry.severity == SEVERITY_ATTENTION
        assert "Aprobar merge de jhonf463r/Python#42" in entry.title
    finally:
        for p in broker.pending_requests():
            broker.cancel(p["id"])
        t.join(timeout=2.0)


def test_snapshot_sorts_critical_before_attention_before_info(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 50.0)

    # politica aprendida (info)
    memory.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python", "label": "docs"},
        kinds=[KIND_MERGE_PR],
    )
    svc = ProactiveDashboardService(broker=broker, memory=memory, clock=lambda: 100.0)

    # attention (merge_pr)
    t1 = _raise_pending_request(
        broker,
        kind=KIND_MERGE_PR,
        scope={"repo": "jhonf463r/Python", "pr_number": "42"},
    )
    # critical (perception mismatch)
    t2 = _raise_pending_request(
        broker,
        kind=KIND_PERCEPTION_MISMATCH,
        scope={"subject": "chatgpt window state"},
    )
    _wait_for_pending(broker, 2)

    try:
        snap = svc.snapshot()
        # critical first, attention second, info last
        assert len(snap.entries) == 3
        severities = [e.severity for e in snap.entries]
        assert severities == [SEVERITY_CRITICAL, SEVERITY_ATTENTION, SEVERITY_INFO]
        assert snap.pending_attention_count == 2
        assert snap.learned_policies_count == 1
    finally:
        for p in broker.pending_requests():
            broker.cancel(p["id"])
        t1.join(timeout=2.0)
        t2.join(timeout=2.0)


def test_snapshot_hides_sensitive_payload_but_shows_reason(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    svc = ProactiveDashboardService(broker=broker, memory=memory)

    t = _raise_pending_request(
        broker,
        kind=KIND_CREDENTIAL_REQUEST,
        scope={"provider": "github"},
        reason="rotate PAT",
        payload_schema=("token",),
        sensitive=True,
    )
    _wait_for_pending(broker, 1)

    snap = svc.snapshot()
    try:
        entry = snap.entries[0]
        assert entry.detail == "rotate PAT"
        assert entry.severity == SEVERITY_CRITICAL
        # No se filtra el schema sensible como dato del entry (la UI solo
        # muestra titulo y detail). Ademas scope solo tiene 'provider'.
        assert "token" not in entry.detail
        assert "token" not in entry.title
        assert entry.scope == {"provider": "github"}
    finally:
        for p in broker.pending_requests():
            broker.cancel(p["id"])
        t.join(timeout=2.0)


def test_snapshot_includes_learned_policies_as_info(tmp_path: Path):
    broker = HumanApprovalBroker()
    memory = ApprovalMemory(storage_path=tmp_path / "p.json", clock=lambda: 0.0)
    memory.remember(
        decision=DECISION_APPROVED,
        scope_pattern={"repo": "jhonf463r/Python", "label": "docs"},
        kinds=[KIND_MERGE_PR],
        note="approve docs merges",
    )
    memory.remember(
        decision=DECISION_REJECTED,
        scope_pattern={"kind": "destructive", "target": "/etc"},
    )
    svc = ProactiveDashboardService(broker=broker, memory=memory)

    snap = svc.snapshot()
    assert snap.pending_attention_count == 0
    assert snap.learned_policies_count == 2
    info_entries = [e for e in snap.entries if e.kind == ENTRY_KIND_LEARNED_POLICY]
    assert len(info_entries) == 2
    # Todos son info y no actionable desde el dashboard (se revocan aparte).
    for entry in info_entries:
        assert entry.severity == SEVERITY_INFO
        assert entry.actionable is False
        assert entry.kind == ENTRY_KIND_LEARNED_POLICY


def test_can_disable_learned_policies_display(tmp_path: Path):
    broker = HumanApprovalBroker()
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    memory.remember(decision=DECISION_APPROVED, scope_pattern={"x": "1"})
    svc = ProactiveDashboardService(
        broker=broker,
        memory=memory,
        include_learned_policies=False,
    )

    snap = svc.snapshot()
    assert snap.entries == ()
    # El conteo oficial sigue reflejando lo que hay, solo se ocultan los
    # entries en la lista renderizable.
    assert snap.learned_policies_count == 1


def test_title_heuristics_cover_known_kinds(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    svc = ProactiveDashboardService(broker=broker, memory=memory)

    cases = [
        (KIND_LOGIN_REQUIRED, {"assistant": "claude"}, "Login requerido en claude"),
        (KIND_CREDENTIAL_REQUEST, {"provider": "github"}, "Credencial requerida para github"),
        (KIND_PERCEPTION_MISMATCH, {"subject": "window state"}, "Confirmar ground truth: window state"),
        ("destructive_action", {"target": "/data"}, "Autorizar accion destructiva sobre /data"),
        ("external_call_authorization", {"provider": "openai"}, "Autorizar llamada externa a openai"),
        (KIND_MERGE_PR, {"repo": "foo/bar", "pr_number": "7"}, "Aprobar merge de foo/bar#7"),
    ]
    for kind, scope, expected_title in cases:
        t = _raise_pending_request(broker, kind=kind, scope=scope)
        _wait_for_pending(broker, 1)
        try:
            snap = svc.snapshot()
            assert snap.entries[0].title.startswith(expected_title), (kind, snap.entries[0].title)
        finally:
            for p in broker.pending_requests():
                broker.cancel(p["id"])
            t.join(timeout=2.0)


def test_dataclass_defaults_are_sane():
    snap = DashboardSnapshot(generated_at_epoch=0.0)
    assert snap.entries == ()
    assert snap.pending_attention_count == 0
    assert snap.learned_policies_count == 0
    assert snap.has_attention_items() is False

    entry = DashboardEntry(
        entry_id="x",
        kind=ENTRY_KIND_APPROVAL_REQUEST,
        title="t",
        detail="d",
        severity=SEVERITY_INFO,
        scope={"a": "b"},
        actionable=False,
        created_at_epoch=0.0,
    )
    assert entry.entry_id == "x"
    assert entry.scope == {"a": "b"}


def test_pending_attention_count_shortcut(tmp_path: Path):
    broker = HumanApprovalBroker()
    broker.register_prompt_handler(lambda _: None)
    memory = ApprovalMemory(storage_path=tmp_path / "p.json")
    svc = ProactiveDashboardService(broker=broker, memory=memory)

    assert svc.pending_attention_count() == 0
    t = _raise_pending_request(broker, kind=KIND_LOGIN_REQUIRED, scope={"assistant": "chatgpt"})
    _wait_for_pending(broker, 1)
    try:
        assert svc.pending_attention_count() == 1
    finally:
        for p in broker.pending_requests():
            broker.cancel(p["id"])
        t.join(timeout=2.0)
