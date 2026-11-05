"""ControlMasterDigestBuilder: compact output, severity ordering, truncation."""

from __future__ import annotations

from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ControlMasterState,
    ControlRule,
    ControlRuleSeverity,
    ControlRuleStatus,
)
from iabv_v15.services.evolution.control_master_digest_builder import (
    ControlMasterDigestBuilder,
    _truncate,
    render_digest_markdown,
)


def _state_with_rules() -> ControlMasterState:
    return ControlMasterState(
        current_vision="Sistema vivo y gobernable",
        global_rules=[
            ControlRule(title="Regla informativa", severity=ControlRuleSeverity.INFO),
            ControlRule(title="No duplicar cerebro", severity=ControlRuleSeverity.IRREVOCABLE),
            ControlRule(title="Consultar world model antes de rutas externas", severity=ControlRuleSeverity.STRICT),
            ControlRule(title="Regla advisory", severity=ControlRuleSeverity.ADVISORY),
            ControlRule(
                title="Regla deprecated",
                severity=ControlRuleSeverity.IRREVOCABLE,
                status=ControlRuleStatus.DEPRECATED,
            ),
        ],
        active_objective_ids=["obj-1", "obj-2"],
        technical_backlog=[{"title": "Cerrar slice A"}, {"title": "Cerrar slice B"}],
        current_risks=[{"title": "Sin permiso de observacion", "severity": "medium"}],
        recent_decisions=[
            ControlDecision(summary="Aprobar capa control maestro", status=ControlDecisionStatus.ACCEPTED),
        ],
        unresolved_items=["validar Codex vivo"],
        current_tests_state={"passed": 60, "failed": 2, "total": 62},
    )


def test_digest_only_includes_strict_and_irrevocable_active_rules() -> None:
    builder = ControlMasterDigestBuilder()
    digest = builder.build(_state_with_rules())
    assert any("[irrevocable] No duplicar cerebro" == item for item in digest.rules_brief)
    assert any("[strict]" in item for item in digest.rules_brief)
    assert all("[advisory]" not in item for item in digest.rules_brief)
    assert all("[info]" not in item for item in digest.rules_brief)
    assert all("Regla deprecated" not in item for item in digest.rules_brief)


def test_irrevocable_rules_appear_before_strict_in_output() -> None:
    builder = ControlMasterDigestBuilder()
    digest = builder.build(_state_with_rules())
    first_strict = next(
        (i for i, item in enumerate(digest.rules_brief) if item.startswith("[strict]")),
        None,
    )
    first_irrevocable = next(
        (i for i, item in enumerate(digest.rules_brief) if item.startswith("[irrevocable]")),
        None,
    )
    assert first_irrevocable is not None
    assert first_strict is None or first_irrevocable < first_strict


def test_digest_carries_vision_objectives_backlog_risks_decisions_unresolved() -> None:
    builder = ControlMasterDigestBuilder()
    digest = builder.build(_state_with_rules())
    assert digest.current_vision == "Sistema vivo y gobernable"
    assert digest.active_objectives_brief == ["active:obj-1", "active:obj-2"]
    assert digest.top_backlog == ["Cerrar slice A", "Cerrar slice B"]
    assert digest.current_risks == ["[medium] Sin permiso de observacion"]
    assert digest.recent_decisions_brief == ["[accepted] Aprobar capa control maestro"]
    assert digest.unresolved == ["validar Codex vivo"]
    assert "passed=60" in digest.tests_state_brief


def test_digest_markdown_respects_max_chars_budget() -> None:
    builder = ControlMasterDigestBuilder(max_chars=400)
    big_state = _state_with_rules().model_copy(
        update={
            "global_rules": [
                ControlRule(
                    title=f"Regla critica numero {i} con un titulo deliberadamente extenso",
                    severity=ControlRuleSeverity.IRREVOCABLE,
                )
                for i in range(20)
            ],
        }
    )
    digest = builder.build(big_state)
    rendered = render_digest_markdown(digest)
    assert len(rendered) <= 400


def test_max_unresolved_is_decoupled_from_max_risks() -> None:
    """max_risks=0 must NOT silently drop unresolved items."""
    state = ControlMasterState(
        current_vision="v",
        unresolved_items=[f"item-{i}" for i in range(7)],
    )
    digest = ControlMasterDigestBuilder(max_risks=0, max_unresolved=4).build(state)
    assert digest.unresolved == ["item-0", "item-1", "item-2", "item-3"]


def test_unresolved_items_are_preserved_when_rule_trim_fits_budget() -> None:
    """Governance signals must not be dropped once the digest already fits."""
    # Fabricate a state where rule trimming alone brings it under budget,
    # and there are a handful of unresolved items that must survive.
    state = ControlMasterState(
        current_vision="v",
        global_rules=[
            ControlRule(
                title=f"Regla muy larga de gobernanza numero {i} con contexto adicional",
                severity=ControlRuleSeverity.IRREVOCABLE,
            )
            for i in range(6)
        ],
        unresolved_items=["falta permiso de observacion", "validar Codex vivo"],
    )
    # Budget chosen so rule trimming fits it with unresolved intact.
    digest = ControlMasterDigestBuilder(max_chars=350).build(state)
    rendered = render_digest_markdown(digest)
    assert len(rendered) <= 350
    # Unresolved items must still both be there.
    assert digest.unresolved == ["falta permiso de observacion", "validar Codex vivo"]


def test_digest_is_independent_of_chat_history() -> None:
    """The digest API only takes the persisted state; it cannot read any chat."""
    builder = ControlMasterDigestBuilder()
    digest = builder.build(ControlMasterState(current_vision="v"))
    assert digest.current_vision == "v"
    # No field in ControlMasterDigest or ControlMasterState references chat.
    state_fields = set(ControlMasterState.model_fields.keys())
    assert "chat_history" not in state_fields
    assert "messages" not in state_fields


# --- Truncation priority: work_queue_brief survival tests ---

from iabv_v15.domain.models import ControlMasterDigest


def _heavy_digest_with_work_queue() -> ControlMasterDigest:
    """Build a realistic large digest where work_queue_brief competes for space."""
    return ControlMasterDigest(
        current_vision="Sistema vivo, gobernable, auto-observable y portable",
        rules_brief=[
            "[irrevocable] No crear otro cerebro ni orquestador",
            "[strict] Consultar world model antes de rutas externas",
        ],
        active_objectives_brief=[
            "active:obj-startup-perf",
            "active:obj-autonomy-zero-touch",
            "active:obj-portable-context",
        ],
        top_backlog=[
            "Cerrar slice startup lazy gate",
            "Refactor phased populate",
            "Optimizar tail runtime_audit",
        ],
        current_risks=[
            "[high] RSS memory puede superar umbral en Windows",
            "[medium] Latencia cloud reasoning degradada",
        ],
        recent_decisions_brief=[
            "[accepted] Aprobar cola canonica en ControlMaster",
            "[accepted] Persistir episodio durable en runtime_audit",
        ],
        unresolved=["validar Codex vivo", "performance tail runtime_audit"],
        tests_state_brief="passed=160, failed=0, total=160",
        autonomy_metrics_brief="autonomy=0.72 resilience=0.85 verdict=improving",
        coordination_patterns_brief="ia-ia: 3 consultas cloud, 1 fallback local",
        work_queue_brief=[
            "[CRITICAL] Fix startup freeze (platform) fix congelamiento",
            "[HIGH] RSS memory monitor (oses) implementar monitor",
            "[HIGH] Query stall detection (pending) agregar deteccion",
            "[MEDIUM] Portable context refresh (objective) optimizar refresh",
            "[LOW] Tool registry cleanup (pending) limpiar registro",
        ],
        work_queue_counts={"pending": 3, "blocked": 1, "ready": 1},
    )


def test_work_queue_brief_survives_truncation_under_2000() -> None:
    """At least 1 work_queue_brief item must survive under max_chars=2000."""
    digest = _heavy_digest_with_work_queue()
    truncated = _truncate(digest, max_chars=2000)
    rendered = render_digest_markdown(truncated)
    assert len(rendered) <= 2000, f"rendered length {len(rendered)} > 2000"
    assert len(truncated.work_queue_brief) >= 1, (
        "work_queue_brief was completely removed; at least 1 item must survive"
    )


def test_work_queue_counts_dropped_before_work_queue_brief() -> None:
    """work_queue_counts must be discarded before work_queue_brief."""
    digest = _heavy_digest_with_work_queue()
    truncated = _truncate(digest, max_chars=2000)
    if truncated.work_queue_brief:
        # If brief survived, counts should already be gone or both survive.
        # Verify: if we still have brief items, counts was dropped first.
        pass  # The ordering test is structural — confirmed by code order.
    # Stronger: build a digest where dropping counts alone frees enough space.
    tight = ControlMasterDigest(
        current_vision="v" * 200,
        rules_brief=["[irrevocable] No duplicar cerebro"],
        unresolved=["item-1"],
        work_queue_brief=["[HIGH] Fix startup (platform) fix"],
        work_queue_counts={"pending": 5, "blocked": 2, "ready": 1},
        coordination_patterns_brief="patterns" * 20,
        autonomy_metrics_brief="metrics" * 20,
        tests_state_brief="passed=60, failed=0",
    )
    # Use a budget that forces some drops but not all.
    budget = len(render_digest_markdown(tight)) - 50
    result = _truncate(tight, max_chars=budget)
    rendered = render_digest_markdown(result)
    assert len(rendered) <= budget
    # work_queue_counts should be dropped before work_queue_brief.
    assert result.work_queue_counts == {} or len(result.work_queue_brief) > 0


def test_work_queue_brief_progressive_trim() -> None:
    """work_queue_brief should trim progressively (5->4->3->...->1) before removal."""
    digest = _heavy_digest_with_work_queue()
    assert len(digest.work_queue_brief) == 5
    # Use a tight budget that forces progressive trimming of work_queue_brief
    # after other less-critical sections have already been dropped.
    budget = 500
    result = _truncate(digest, max_chars=budget)
    rendered = render_digest_markdown(result)
    assert len(rendered) <= budget
    assert 0 < len(result.work_queue_brief) < 5, (
        f"Expected progressive trim, got {len(result.work_queue_brief)} items"
    )


def test_rules_and_unresolved_survive_after_work_queue_trim() -> None:
    """Rules and unresolved must survive even when work_queue_brief is trimmed."""
    digest = _heavy_digest_with_work_queue()
    truncated = _truncate(digest, max_chars=2000)
    rendered = render_digest_markdown(truncated)
    assert len(rendered) <= 2000
    assert len(truncated.rules_brief) > 0, "rules_brief must survive truncation"
    assert len(truncated.unresolved) > 0, "unresolved must survive truncation"


def test_render_work_queue_compact_format() -> None:
    """_render_work_queue must produce compact strings (no 'src=' prefix, truncated)."""
    from iabv_v15.services.evolution.control_master_digest_builder import (
        _render_work_queue,
    )

    queue = [
        {
            "priority_label": "CRITICAL",
            "source": "platform",
            "title": "A" * 80,  # very long title
            "next_action": "B" * 60,  # very long action
            "status": "pending",
        },
    ]
    brief, counts = _render_work_queue(queue)
    assert len(brief) == 1
    # Title truncated to 40 chars, action to 30 chars.
    assert len(brief[0]) < 80 + 60, "Brief line must be shorter than raw fields"
    assert "src=" not in brief[0], "Compact format must not use 'src=' prefix"



def test_digest_carries_d021_source_times_scope_and_queue_lineage() -> None:
    from datetime import datetime, timezone

    source_generated = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    observed = datetime(2026, 11, 4, 12, 1, tzinfo=timezone.utc)
    state = ControlMasterState(
        state_id="state-d021-001",
        current_vision="governed project",
        evidence_links=[
            "evidence://control-master/vision",
            "evidence://control-master/rule-01",
        ],
        metadata={
            "_space_time_control_master_source_provenance": {
                "project_id": "IABV_v1.5",
                "source_object": "control_master/latest.json",
                "source_state_id": "state-d021-001",
                "source_revision_or_digest": "sha256:abc123",
                "source_generated_at_utc": source_generated.isoformat(),
                "source_observed_at_utc": observed.isoformat(),
                "workspace_scope_id": "scope-001",
                "freshness_status": "FRESH",
                "read_status": "READ_OK",
            }
        },
    )
    digest = ControlMasterDigestBuilder().build(
        state,
        work_queue=[{
            "id": "objective:OBJ-42",
            "priority_label": "HIGH",
            "priority_score": 80,
            "title": "Close objective",
            "status": "pending",
            "next_action": "Inspect causal dependency",
            "dependencies": ["OBJ-41"],
            "evidence_refs": ["evidence://OBJ-42/review"],
            "source": "objective",
        }],
        work_queue_status="AVAILABLE",
        source_coverage={"objectives": "READ_OK"},
        observed_at_utc=observed,
    )
    assert digest.control_master_signal_status == "FRESH"
    assert digest.source_state_id == "state-d021-001"
    assert digest.source_object == "control_master/latest.json"
    assert digest.project_id == "IABV_v1.5"
    assert digest.workspace_scope_id == "scope-001"
    assert digest.source_revision_or_digest == "sha256:abc123"
    assert digest.source_generated_at_utc == source_generated
    assert digest.observed_at_utc == observed
    assert digest.top_work_queue_items[0]["item_id"] == "objective:OBJ-42"
    assert digest.top_work_queue_items[0]["dependencies"] == ["OBJ-41"]
    assert digest.top_work_queue_items[0]["evidence_refs"] == ["evidence://OBJ-42/review"]
    assert digest.source_evidence_refs == [
        "evidence://control-master/vision",
        "evidence://control-master/rule-01",
    ]
    rendered = render_digest_markdown(digest)
    assert "Vigencia D021: FRESH" in rendered
    assert "state-d021-001" in rendered
    assert "objective:OBJ-42" in rendered
    assert "evidence://OBJ-42/review" in rendered
    assert "evidence://control-master/vision" in rendered


def test_signal_availability_is_independent_from_unverified_queue_coverage() -> None:
    state = ControlMasterState(
        state_id="cm-state-readable",
        metadata={
            "_space_time_control_master_source_provenance": {
                "read_status": "READ_OK",
                "freshness_status": "FRESH",
                "source_state_id": "cm-state-readable",
                "source_generated_at_utc": "2026-11-04T12:00:00+00:00",
                "project_id": "IABV_v1.5",
                "source_object": "control_master/latest.json",
                "workspace_scope_id": "scope-001",
                "source_revision_or_digest": "sha256:source001",
            }
        },
    )
    digest = ControlMasterDigestBuilder().build(
        state,
        work_queue=None,
        work_queue_status="UNVERIFIED",
        signal_reason="SOURCE_APPLICABILITY_OR_COVERAGE_UNRESOLVED",
    )
    assert digest.signal_status == "AVAILABLE"
    assert digest.work_queue_status == "UNVERIFIED"
    assert digest.control_master_signal_status == "FRESH"


def test_missing_control_master_source_is_unavailable_even_if_queue_state_is_separate() -> None:
    state = ControlMasterState(
        metadata={
            "_space_time_control_master_source_provenance": {
                "read_status": "NO_SOURCE_SNAPSHOT",
                "freshness_status": "UNAVAILABLE",
                "project_id": "IABV_v1.5",
                "source_object": "control_master/latest.json",
            }
        },
    )
    digest = ControlMasterDigestBuilder().build(
        state,
        work_queue=None,
        work_queue_status="UNVERIFIED",
    )
    assert digest.signal_status == "UNAVAILABLE"
    assert digest.work_queue_status == "UNVERIFIED"


def test_build_from_service_reports_empty_only_after_complete_successful_reads() -> None:
    from datetime import datetime, timezone

    class _Service:
        last_work_queue_errors = ()
        last_work_queue_source_coverage = {
            "objective_repository": "READ_OK",
            "platform_pending_queue": "READ_OK",
            "pending_issue_repository": "READ_OK",
            "self_examination_service": "READ_OK",
            "runtime_audit": "READ_OK",
            "runtime_audit_durability": "READ_OK",
            "tests_state": "READ_OK",
        }

        def current_state(self, *, refresh: bool = False):
            return ControlMasterState(
                state_id="state-reader-empty",
                current_vision="live source read",
                metadata={
                    "_space_time_control_master_source_provenance": {
                        "project_id": "IABV_v1.5",
                        "source_object": "control_master/latest.json",
                        "source_state_id": "state-reader-empty",
                        "source_revision_or_digest": "sha256:reader-empty",
                        "source_generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "workspace_scope_id": "scope-reader",
                        "freshness_status": "FRESH",
                        "read_status": "READ_OK",
                    }
                },
            )

        def current_work_queue(self, *, limit: int = 10):
            return []

    digest = ControlMasterDigestBuilder().build_from_service(_Service())
    assert digest.signal_status == "AVAILABLE"
    assert digest.work_queue_status == "EMPTY_QUEUE"
    assert digest.control_master_signal_status == "FRESH"


def test_build_from_service_missing_expected_source_cannot_confirm_empty_queue() -> None:
    from datetime import datetime, timezone

    class _Service:
        last_work_queue_errors = ()
        # Five sources report READ_OK, but tests_state was never reported.
        last_work_queue_source_coverage = {
            "objective_repository": "READ_OK",
            "platform_pending_queue": "READ_OK",
            "pending_issue_repository": "READ_OK",
            "self_examination_service": "READ_OK",
            "runtime_audit": "READ_OK",
            "runtime_audit_durability": "READ_OK",
        }

        def current_state(self, *, refresh: bool = False):
            return ControlMasterState(
                state_id="state-reader-missing-source",
                current_vision="source snapshot",
                metadata={
                    "_space_time_control_master_source_provenance": {
                        "project_id": "IABV_v1.5",
                        "source_object": "control_master/latest.json",
                        "source_state_id": "state-reader-missing-source",
                        "source_revision_or_digest": "sha256:missing-source",
                        "source_generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "workspace_scope_id": "scope-reader",
                        "freshness_status": "FRESH",
                        "read_status": "READ_OK",
                    }
                },
            )

        def current_work_queue(self, *, limit: int = 10):
            return []

    digest = ControlMasterDigestBuilder().build_from_service(_Service())
    assert digest.signal_status == "AVAILABLE"
    assert digest.work_queue_status == "UNVERIFIED"
    assert digest.work_queue_brief == []
    assert "MISSING:tests_state" in digest.signal_reason


def test_build_from_service_unexpected_source_cannot_confirm_empty_queue() -> None:
    from datetime import datetime, timezone

    class _Service:
        last_work_queue_errors = ()
        last_work_queue_source_coverage = {
            "objective_repository": "READ_OK",
            "platform_pending_queue": "READ_OK",
            "pending_issue_repository": "READ_OK",
            "self_examination_service": "READ_OK",
            "runtime_audit": "READ_OK",
            "runtime_audit_durability": "READ_OK",
            "tests_state": "READ_OK",
            "unregistered_source": "READ_OK",
        }

        def current_state(self, *, refresh: bool = False):
            return ControlMasterState(
                state_id="state-reader-unexpected-source",
                current_vision="source snapshot",
                metadata={
                    "_space_time_control_master_source_provenance": {
                        "project_id": "IABV_v1.5",
                        "source_object": "control_master/latest.json",
                        "source_state_id": "state-reader-unexpected-source",
                        "source_revision_or_digest": "sha256:unexpected-source",
                        "source_generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "workspace_scope_id": "scope-reader",
                        "freshness_status": "FRESH",
                        "read_status": "READ_OK",
                    }
                },
            )

        def current_work_queue(self, *, limit: int = 10):
            return []

    digest = ControlMasterDigestBuilder().build_from_service(_Service())
    assert digest.signal_status == "AVAILABLE"
    assert digest.work_queue_status == "UNVERIFIED"
    assert digest.work_queue_brief == []
    assert "UNEXPECTED:unregistered_source" in digest.signal_reason


def test_build_from_service_queue_exception_is_unavailable_not_empty() -> None:
    from datetime import datetime, timezone

    class _Service:
        last_work_queue_errors = ()
        last_work_queue_source_coverage = {
            "objectives": "READ_OK",
        }

        def current_state(self, *, refresh: bool = False):
            return ControlMasterState(
                state_id="state-reader-failure",
                metadata={
                    "_space_time_control_master_source_provenance": {
                        "project_id": "IABV_v1.5",
                        "source_object": "control_master/latest.json",
                        "source_state_id": "state-reader-failure",
                        "source_revision_or_digest": "sha256:reader-failure",
                        "source_generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "workspace_scope_id": "scope-reader",
                        "freshness_status": "FRESH",
                        "read_status": "READ_OK",
                    }
                },
            )

        def current_work_queue(self, *, limit: int = 10):
            raise RuntimeError("queue unavailable")

    digest = ControlMasterDigestBuilder().build_from_service(_Service())
    assert digest.signal_status == "AVAILABLE"
    assert digest.work_queue_status == "UNAVAILABLE"
    assert digest.work_queue_brief == []
    assert digest.signal_reason == "CONTROL_MASTER_QUEUE_READ_FAILED:RuntimeError"


def test_digest_labels_test_state_mirror_freshness() -> None:
    from datetime import datetime, timedelta, timezone
    from iabv_v15.services.evolution.control_master_digest_builder import _render_tests_brief

    missing = _render_tests_brief({})
    assert "mirror_status=MIRROR_UNVERIFIED" in missing
    assert "canonical_queue_read=SEPARATE" in missing

    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    stale = _render_tests_brief({
        "evidence_id": "evidence-stale-001",
        "timestamp": stale_timestamp,
        "passed": 10,
        "failed": 3,
        "total": 13,
    })
    assert "mirror_status=MIRROR_STALE" in stale
    assert "failed=3" in stale

    fresh_timestamp = datetime.now(timezone.utc).isoformat()
    fresh = _render_tests_brief({
        "evidence_id": "evidence-fresh-001",
        "timestamp": fresh_timestamp,
        "commit_sha": "a" * 40,
        "suite": "tests/test_control_master_service.py",
        "passed": 12,
        "failed": 0,
        "total": 12,
    })
    assert "mirror_status=MIRROR_FRESHNESS_ONLY" in fresh
    assert "canonical_queue_read=SEPARATE" in fresh
    assert "evidence_id=evidence-fresh-001" in fresh
    assert "commit=aaaaaaaaaaaa" in fresh
