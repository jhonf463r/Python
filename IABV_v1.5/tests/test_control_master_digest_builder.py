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
