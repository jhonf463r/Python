"""Tests focalizados para ConsensusInterpretationService."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iabv_v15.services.evolution.consensus_interpretation_service import (
    ConsensusInterpretationService,
    ConsensusResult,
    DECISION_CONSENSUS,
    DECISION_HUMAN_CONFIRMED,
    DECISION_HUMAN_DEFERRED,
    DECISION_HUMAN_REJECTED,
    DECISION_INSUFFICIENT_VOTES,
    DECISION_NO_VOTES,
    DECISION_TIE,
    InterpretationVote,
    UNRESOLVED_LOW_AGREEMENT,
    UNRESOLVED_NO_RESPONSE,
    UNRESOLVED_TIE,
    default_normalizer,
)


# ---- fakes -------------------------------------------------------------


@dataclass
class FakeApprovalResult:
    decision: str = "pending"
    payload: dict | None = None


class FakeBroker:
    def __init__(self, *, result: FakeApprovalResult | None = None, raise_exc: Exception | None = None):
        self._result = result
        self._raise = raise_exc
        self.requests: list[dict] = []

    def request(self, **kwargs):
        self.requests.append(kwargs)
        if self._raise:
            raise self._raise
        return self._result


def make_service(
    interpreters: dict,
    *,
    min_votes: int = 2,
    agreement_threshold: float = 0.5,
    broker: Any = None,
) -> ConsensusInterpretationService:
    return ConsensusInterpretationService(
        interpreters=interpreters,
        min_votes=min_votes,
        agreement_threshold=agreement_threshold,
        human_approval_broker=broker,
        clock=lambda: 100.0,
    )


# ---- core voting -------------------------------------------------------


def test_default_normalizer_trims_lowercases_and_collapses_whitespace():
    assert default_normalizer("   Hello    World  \n") == "hello world"
    assert default_normalizer("") == ""
    assert default_normalizer(None) == ""  # type: ignore[arg-type]


def test_no_interpreters_returns_no_votes():
    svc = make_service({})
    res = svc.seek_consensus(subject="window-X", question="what do you see?")
    assert res.decision == DECISION_NO_VOTES
    assert res.votes == ()
    assert UNRESOLVED_NO_RESPONSE in res.unresolved
    assert res.agreement_ratio == 0.0
    assert res.winning_interpretation == ""


def test_all_interpreters_raise_returns_no_votes():
    def boom(aid, q):
        raise RuntimeError("down")

    svc = make_service({"codex": boom, "claude": boom})
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_NO_VOTES
    assert UNRESOLVED_NO_RESPONSE in res.unresolved
    assert len(res.votes) == 2
    assert all(v.error.startswith("interpreter_raised") for v in res.votes)


def test_consensus_all_agree():
    interpreters = {
        "codex": lambda aid, q: "ChatGPT window is visible",
        "claude": lambda aid, q: "chatgpt window is visible",
        "chatgpt": lambda aid, q: "ChatGPT Window is visible",
    }
    svc = make_service(interpreters)
    res = svc.seek_consensus(subject="w", question="q")
    assert res.decision == DECISION_CONSENSUS
    assert res.winning_interpretation == "chatgpt window is visible"
    assert res.agreement_ratio == 1.0
    assert len(res.votes) == 3
    assert all(v.is_valid for v in res.votes)
    assert res.unresolved == ()


def test_consensus_majority_over_threshold():
    interpreters = {
        "codex": lambda aid, q: "sesion activa",
        "claude": lambda aid, q: "sesion activa",
        "chatgpt": lambda aid, q: "no sesion",
    }
    svc = make_service(interpreters, agreement_threshold=0.5)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_CONSENSUS
    assert res.winning_interpretation == "sesion activa"
    assert round(res.agreement_ratio, 2) == 0.67


def test_tie_without_broker_returns_tie():
    interpreters = {
        "codex": lambda aid, q: "option A",
        "claude": lambda aid, q: "option B",
    }
    svc = make_service(interpreters, agreement_threshold=0.5)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_TIE
    assert res.winning_interpretation == ""
    assert UNRESOLVED_TIE in res.unresolved


def test_insufficient_votes_when_below_min_votes():
    # min_votes=2 but only one interpreter responds
    interpreters = {
        "codex": lambda aid, q: "the answer",
        "claude": lambda aid, q: None,  # empty response
    }
    svc = make_service(interpreters, min_votes=2)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_INSUFFICIENT_VOTES
    assert UNRESOLVED_LOW_AGREEMENT in res.unresolved


def test_low_agreement_below_threshold_without_broker():
    interpreters = {
        "codex": lambda aid, q: "A",
        "claude": lambda aid, q: "A",
        "chatgpt": lambda aid, q: "B",
        "devin": lambda aid, q: "C",
        "ollama": lambda aid, q: "D",
    }
    svc = make_service(interpreters, agreement_threshold=0.9)
    res = svc.seek_consensus(subject="x", question="q")
    # A wins with 2/5=0.4, no tie, but below threshold 0.9 -> low_agreement
    assert res.decision == DECISION_INSUFFICIENT_VOTES
    assert UNRESOLVED_LOW_AGREEMENT in res.unresolved
    assert res.winning_interpretation == "a"
    assert round(res.agreement_ratio, 2) == 0.4


def test_filtered_assistants_parameter():
    interpreters = {
        "codex": lambda aid, q: "codex_answer",
        "claude": lambda aid, q: "claude_answer",
        "chatgpt": lambda aid, q: "chatgpt_answer",
    }
    svc = make_service(interpreters, min_votes=2)
    res = svc.seek_consensus(subject="x", question="q", assistants=["codex", "claude"])
    assert {v.assistant_id for v in res.votes} == {"codex", "claude"}


def test_unknown_assistant_in_filter_is_ignored():
    interpreters = {"codex": lambda aid, q: "a", "claude": lambda aid, q: "a"}
    svc = make_service(interpreters)
    res = svc.seek_consensus(
        subject="x",
        question="q",
        assistants=["codex", "claude", "nonexistent"],
    )
    assert {v.assistant_id for v in res.votes} == {"codex", "claude"}


def test_empty_response_counts_as_error_not_vote():
    interpreters = {
        "codex": lambda aid, q: "   ",   # normalizes to empty
        "claude": lambda aid, q: "real answer",
        "chatgpt": lambda aid, q: "real answer",
    }
    svc = make_service(interpreters)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_CONSENSUS
    assert res.winning_interpretation == "real answer"
    # codex vote exists but invalid
    codex_vote = next(v for v in res.votes if v.assistant_id == "codex")
    assert codex_vote.is_valid is False
    assert codex_vote.error == "empty_normalized"


# ---- broker escalation ------------------------------------------------


def test_tie_escalates_to_broker_and_confirms_with_interpretation():
    interpreters = {
        "codex": lambda aid, q: "A",
        "claude": lambda aid, q: "B",
    }
    broker = FakeBroker(result=FakeApprovalResult(decision="approved", payload={"interpretation": "Actual B"}))
    svc = make_service(interpreters, broker=broker, agreement_threshold=0.5)
    res = svc.seek_consensus(subject="win-x", question="qq")
    assert res.decision == DECISION_HUMAN_CONFIRMED
    assert res.winning_interpretation == "actual b"
    assert res.unresolved == ()
    assert broker.requests and broker.requests[0]["kind"] == "perception_mismatch_confirmation"


def test_tie_escalates_to_broker_and_rejects():
    interpreters = {
        "codex": lambda aid, q: "A",
        "claude": lambda aid, q: "B",
    }
    broker = FakeBroker(result=FakeApprovalResult(decision="rejected"))
    svc = make_service(interpreters, broker=broker)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_HUMAN_REJECTED
    assert res.winning_interpretation == ""
    assert UNRESOLVED_TIE in res.unresolved


def test_tie_escalates_to_broker_pending_is_deferred():
    interpreters = {
        "codex": lambda aid, q: "A",
        "claude": lambda aid, q: "B",
    }
    broker = FakeBroker(result=FakeApprovalResult(decision="pending"))
    svc = make_service(interpreters, broker=broker)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_HUMAN_DEFERRED
    assert UNRESOLVED_TIE in res.unresolved


def test_broker_raising_degrades_to_deferred():
    interpreters = {"codex": lambda aid, q: "A", "claude": lambda aid, q: "B"}
    broker = FakeBroker(raise_exc=RuntimeError("broker down"))
    svc = make_service(interpreters, broker=broker)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_HUMAN_DEFERRED


def test_low_agreement_with_broker_confirmation_uses_tentative_interpretation():
    interpreters = {
        "codex": lambda aid, q: "A",
        "claude": lambda aid, q: "B",
        "chatgpt": lambda aid, q: "A",
        "devin": lambda aid, q: "C",
    }
    broker = FakeBroker(result=FakeApprovalResult(decision="approved", payload={}))
    # Very high threshold so even 2/4 majority triggers low_agreement
    svc = make_service(interpreters, broker=broker, agreement_threshold=0.9)
    res = svc.seek_consensus(subject="x", question="q")
    # Tentative A wins (2/4) and broker confirms without payload override
    assert res.decision == DECISION_HUMAN_CONFIRMED
    assert res.winning_interpretation == "a"


def test_low_agreement_broker_rejection_clears_winner():
    interpreters = {
        "codex": lambda aid, q: "A",
        "claude": lambda aid, q: "B",
        "chatgpt": lambda aid, q: "A",
        "devin": lambda aid, q: "C",
    }
    broker = FakeBroker(result=FakeApprovalResult(decision="rejected"))
    svc = make_service(interpreters, broker=broker, agreement_threshold=0.9)
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_HUMAN_REJECTED
    assert res.winning_interpretation == ""


# ---- registry helpers -------------------------------------------------


def test_register_and_unregister_interpreter():
    svc = make_service({})
    assert svc.registered_assistants() == ()
    svc.register_interpreter("codex", lambda aid, q: "hello")
    assert "codex" in svc.registered_assistants()
    assert svc.unregister_interpreter("codex") is True
    assert svc.unregister_interpreter("codex") is False


def test_register_ignores_empty_id_or_none_callable():
    svc = make_service({})
    svc.register_interpreter("", lambda aid, q: "x")
    svc.register_interpreter("codex", None)  # type: ignore[arg-type]
    assert svc.registered_assistants() == ()


def test_custom_normalizer_respected():
    def upper_norm(x: str) -> str:
        return (x or "").strip().upper()

    svc = ConsensusInterpretationService(
        interpreters={
            "codex": lambda aid, q: "yes",
            "claude": lambda aid, q: "YES",
            "chatgpt": lambda aid, q: "no",
        },
        normalizer=upper_norm,
        clock=lambda: 0.0,
    )
    res = svc.seek_consensus(subject="x", question="q")
    assert res.decision == DECISION_CONSENSUS
    assert res.winning_interpretation == "YES"


def test_evidence_refs_propagate():
    svc = make_service({"codex": lambda aid, q: "a", "claude": lambda aid, q: "a"})
    res = svc.seek_consensus(
        subject="x",
        question="q",
        evidence_refs=["data/evolution/world_model/a.json", "data/evolution/world_model/b.json"],
    )
    assert res.evidence_refs == (
        "data/evolution/world_model/a.json",
        "data/evolution/world_model/b.json",
    )


def test_question_is_passed_to_interpreters():
    seen: list[tuple[str, str]] = []

    def capture(aid, q):
        seen.append((aid, q))
        return "ok"

    svc = make_service({"codex": capture, "claude": capture})
    svc.seek_consensus(subject="x", question="is the window visible?")
    assert seen == [("codex", "is the window visible?"), ("claude", "is the window visible?")]


def test_consensus_result_has_consensus_property():
    r1 = ConsensusResult(
        subject="x",
        question="q",
        decision=DECISION_CONSENSUS,
        winning_interpretation="a",
        votes=(),
        agreement_ratio=1.0,
        evidence_refs=(),
        unresolved=(),
        generated_at_epoch=0.0,
    )
    r2 = ConsensusResult(
        subject="x",
        question="q",
        decision=DECISION_HUMAN_CONFIRMED,
        winning_interpretation="a",
        votes=(),
        agreement_ratio=0.5,
        evidence_refs=(),
        unresolved=(),
        generated_at_epoch=0.0,
    )
    r3 = ConsensusResult(
        subject="x",
        question="q",
        decision=DECISION_TIE,
        winning_interpretation="",
        votes=(),
        agreement_ratio=0.5,
        evidence_refs=(),
        unresolved=(UNRESOLVED_TIE,),
        generated_at_epoch=0.0,
    )
    assert r1.has_consensus is True
    assert r2.has_consensus is True
    assert r3.has_consensus is False
