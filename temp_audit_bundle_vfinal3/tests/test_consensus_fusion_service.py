"""Tests del `ConsensusFusionService` (PCS v1 — Pieza 5)."""

from __future__ import annotations

from iabv_v15.domain.models import ConsensusResult, IATraceEntry
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.consensus_fusion_service import (
    ConsensusFusionService,
)


def _trace(
    *,
    trace_id: str = "t",
    assistant_kind: str = "codex",
    result_label: str = "ok",
    confidence: float = 0.5,
    success: bool = True,
    scope: str = "scope-x",
) -> IATraceEntry:
    return IATraceEntry(
        trace_id=trace_id,
        assistant_kind=assistant_kind,
        result_label=result_label,
        confidence=confidence,
        success=success,
        comparison_scope_key=scope,
    )


def _service() -> ConsensusFusionService:
    return ConsensusFusionService(adaptive_weight_layer=AdaptiveWeightLayer())


def test_weighted_vote_wins_by_summed_confidence() -> None:
    traces = [
        _trace(trace_id="t1", assistant_kind="codex", result_label="pass", confidence=0.4),
        _trace(trace_id="t2", assistant_kind="claude_web", result_label="pass", confidence=0.3),
        _trace(trace_id="t3", assistant_kind="chatgpt_web", result_label="fail", confidence=0.9),
    ]
    result = _service().fuse(candidate_traces=traces, strategy="weighted_vote")

    # pass = 0.4 + 0.3 = 0.7; fail = 0.9 → fail gana por peso total.
    assert result.winning_label == "fail"
    assert result.winning_trace_id == "t3"
    assert result.winning_assistant_kind == "chatgpt_web"
    assert result.strategy_used == "weighted_vote"
    assert result.confidence > 0.0
    assert result.considered_trace_ids == ["t1", "t2", "t3"]
    assert result.comparison_scope_key == "scope-x"
    # El metadata guarda los pesos por label para trazabilidad.
    weights = {row["label"]: row["weight"] for row in result.metadata["label_weights"]}
    assert weights == {"pass": 0.7, "fail": 0.9}


def test_weighted_vote_picks_representative_trace_by_max_confidence() -> None:
    traces = [
        _trace(trace_id="low", assistant_kind="a", result_label="green", confidence=0.2),
        _trace(trace_id="high", assistant_kind="b", result_label="green", confidence=0.8),
    ]
    result = _service().fuse(candidate_traces=traces, strategy="weighted_vote")
    assert result.winning_label == "green"
    assert result.winning_trace_id == "high"
    assert result.winning_assistant_kind == "b"


def test_highest_confidence_picks_top_trace() -> None:
    traces = [
        _trace(trace_id="t1", assistant_kind="codex", confidence=0.3),
        _trace(trace_id="t2", assistant_kind="claude_web", confidence=0.9),
        _trace(trace_id="t3", assistant_kind="devin", confidence=0.6),
    ]
    result = _service().fuse(candidate_traces=traces, strategy="highest_confidence")

    assert result.winning_trace_id == "t2"
    assert result.winning_assistant_kind == "claude_web"
    assert result.confidence == 0.9
    assert result.strategy_used == "highest_confidence"


def test_first_success_returns_first_true_success() -> None:
    traces = [
        _trace(trace_id="t1", success=False),
        _trace(trace_id="t2", success=False),
        _trace(trace_id="t3", success=True, assistant_kind="claude_web"),
        _trace(trace_id="t4", success=True, assistant_kind="codex"),
    ]
    result = _service().fuse(candidate_traces=traces, strategy="first_success")

    assert result.winning_trace_id == "t3"
    assert result.winning_assistant_kind == "claude_web"
    assert result.strategy_used == "first_success"


def test_first_success_without_any_success_is_fail_observable() -> None:
    traces = [_trace(trace_id="t1", success=False), _trace(trace_id="t2", success=False)]
    result = _service().fuse(candidate_traces=traces, strategy="first_success")

    assert result.winning_trace_id == ""
    assert "no_success" in result.unresolved_fields
    assert result.strategy_used == "first_success"
    assert result.comparison_scope_key == "scope-x"


def test_empty_candidates_returns_no_candidates() -> None:
    result = _service().fuse(candidate_traces=[], strategy="weighted_vote")

    assert result.winning_trace_id == ""
    assert "no_candidates" in result.unresolved_fields
    assert result.strategy_used == "weighted_vote"
    assert result.comparison_scope_key == ""


def test_unknown_strategy_degrades_with_unresolved_field() -> None:
    traces = [_trace(trace_id="t1")]
    result = _service().fuse(candidate_traces=traces, strategy="random_choice")

    assert "unknown_strategy" in result.unresolved_fields
    assert result.strategy_used == "random_choice"
    assert result.winning_trace_id == ""
    assert result.considered_trace_ids == ["t1"]


def test_fuse_does_not_mutate_input_traces() -> None:
    traces = [
        _trace(trace_id="t1", assistant_kind="codex", confidence=0.1, result_label="pass"),
        _trace(trace_id="t2", assistant_kind="devin", confidence=0.9, result_label="pass"),
    ]
    before = [t.model_dump() for t in traces]
    _service().fuse(candidate_traces=traces, strategy="weighted_vote")
    after = [t.model_dump() for t in traces]
    assert before == after


def test_consensus_result_round_trip_serialisation() -> None:
    traces = [
        _trace(trace_id="t1", assistant_kind="codex", confidence=0.7, result_label="pass"),
        _trace(trace_id="t2", assistant_kind="devin", confidence=0.4, result_label="pass"),
    ]
    result = _service().fuse(candidate_traces=traces, strategy="weighted_vote")
    dumped = result.model_dump(mode="json")
    hydrated = ConsensusResult.model_validate(dumped)

    assert hydrated == result
    assert hydrated.winning_label == "pass"
    assert hydrated.strategy_used == "weighted_vote"
