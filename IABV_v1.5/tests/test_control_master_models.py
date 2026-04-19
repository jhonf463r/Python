"""Dominio: validar defaults, enums y serializacion de los modelos de control maestro."""

from __future__ import annotations

import json

from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ControlMasterDigest,
    ControlMasterState,
    ControlRule,
    ControlRuleSeverity,
    ControlRuleStatus,
)


def test_control_rule_defaults_and_ids_are_deterministic_shape() -> None:
    rule = ControlRule(title="No hacer refactor masivo")
    assert rule.severity == ControlRuleSeverity.ADVISORY
    assert rule.status == ControlRuleStatus.ACTIVE
    assert rule.rule_id
    # created_at and updated_at come from separate utc_now() calls but should
    # still sit on the same wall-clock second when no time passed in between.
    assert abs((rule.updated_at_utc - rule.created_at_utc).total_seconds()) < 0.5


def test_control_decision_defaults() -> None:
    decision = ControlDecision(summary="Agregar capa control maestro")
    assert decision.status == ControlDecisionStatus.PROPOSED
    assert decision.decision_id
    assert decision.affected_modules == []
    assert decision.timestamp is not None


def test_control_master_state_is_empty_by_default() -> None:
    state = ControlMasterState()
    assert state.version == "control_master.v1"
    assert state.current_vision == ""
    assert state.active_objective_ids == []
    assert state.global_rules == []
    assert state.recent_decisions == []


def test_control_master_digest_roundtrip_json() -> None:
    digest = ControlMasterDigest(
        current_vision="vision",
        rules_brief=["[irrevocable] No duplicar cerebro"],
    )
    raw = digest.model_dump_json()
    parsed = ControlMasterDigest.model_validate(json.loads(raw))
    assert parsed.version == "control_master_digest.v1"
    assert parsed.current_vision == "vision"
    assert parsed.rules_brief == ["[irrevocable] No duplicar cerebro"]


def test_control_rule_severity_order_weighting() -> None:
    severities = [
        ControlRuleSeverity.INFO,
        ControlRuleSeverity.ADVISORY,
        ControlRuleSeverity.STRICT,
        ControlRuleSeverity.IRREVOCABLE,
    ]
    assert [s.value for s in severities] == ["info", "advisory", "strict", "irrevocable"]
