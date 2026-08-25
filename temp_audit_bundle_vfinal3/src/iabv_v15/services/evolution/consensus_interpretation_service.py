"""ConsensusInterpretationService: cuando F3.3 detecta un mismatch entre
lo que IABV *cree que ve* y el ground truth, consulta a N asistentes
externos la *misma* pregunta y vota cual es la interpretacion correcta.

Pedido verbatim del usuario:

    "una logica donde pide concejos o inrepretaciones del entorno con las
     diferentes herramientas para validar que lo que ve es asi y funciona
     asi"

AGENTS.md:
- No crea otro cerebro: es un agregador puro de respuestas externas.
- No fingle observacion: si ninguna IA responde, marca UNRESOLVED.
- No decide ruta: devuelve la interpretacion ganadora; quien llama
  decide que hacer (aplicar correccion, pedir aprobacion humana, etc).
- Si hay empate o confianza insuficiente, escala via
  HumanApprovalBroker (opcional) o devuelve decision=tie/UNRESOLVED.
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional


DECISION_CONSENSUS = "consensus"
DECISION_TIE = "tie"
DECISION_NO_VOTES = "no_votes"
DECISION_INSUFFICIENT_VOTES = "insufficient_votes"
DECISION_HUMAN_DEFERRED = "human_deferred"
DECISION_HUMAN_CONFIRMED = "human_confirmed"
DECISION_HUMAN_REJECTED = "human_rejected"

UNRESOLVED_NO_RESPONSE = "UNRESOLVED:no_assistant_responded"
UNRESOLVED_LOW_AGREEMENT = "UNRESOLVED:low_agreement"
UNRESOLVED_TIE = "UNRESOLVED:interpretation_tie"


InterpreterCallable = Callable[[str, str], str]
Normalizer = Callable[[str], str]


@dataclass(frozen=True)
class InterpretationVote:
    """Voto de un asistente para la pregunta planteada."""

    assistant_id: str
    raw_text: str
    interpretation: str
    confidence: float = 0.0
    error: str = ""

    @property
    def is_valid(self) -> bool:
        return not self.error and bool(self.interpretation)


@dataclass(frozen=True)
class ConsensusResult:
    """Resultado de una ronda de consulta multi-IA."""

    subject: str
    question: str
    decision: str
    winning_interpretation: str
    votes: tuple[InterpretationVote, ...]
    agreement_ratio: float
    evidence_refs: tuple[str, ...]
    unresolved: tuple[str, ...]
    generated_at_epoch: float

    @property
    def has_consensus(self) -> bool:
        return self.decision in (DECISION_CONSENSUS, DECISION_HUMAN_CONFIRMED)


def default_normalizer(text: str) -> str:
    """Normalizador conservador: trim + lowercase + colapsa espacios."""
    if not text:
        return ""
    cleaned = " ".join(str(text).strip().split())
    return cleaned.lower()


class ConsensusInterpretationService:
    """Pide una interpretacion a N asistentes y vota."""

    def __init__(
        self,
        *,
        interpreters: Mapping[str, InterpreterCallable] | None = None,
        clock: Callable[[], float] | None = None,
        min_votes: int = 2,
        agreement_threshold: float = 0.5,
        normalizer: Normalizer | None = None,
        human_approval_broker: Any | None = None,
        human_approval_timeout_s: float | None = None,
    ) -> None:
        self._interpreters: dict[str, InterpreterCallable] = dict(interpreters or {})
        self._clock = clock or time.time
        self._min_votes = max(1, int(min_votes))
        self._agreement_threshold = max(0.0, min(1.0, float(agreement_threshold)))
        self._normalizer = normalizer or default_normalizer
        self._human_broker = human_approval_broker
        self._human_timeout_s = human_approval_timeout_s

    # ---- registry -----------------------------------------------------

    def register_interpreter(self, assistant_id: str, fn: InterpreterCallable) -> None:
        if not assistant_id or fn is None:
            return
        self._interpreters[assistant_id] = fn

    def unregister_interpreter(self, assistant_id: str) -> bool:
        return self._interpreters.pop(assistant_id, None) is not None

    def registered_assistants(self) -> tuple[str, ...]:
        return tuple(self._interpreters.keys())

    # ---- main API -----------------------------------------------------

    def seek_consensus(
        self,
        *,
        subject: str,
        question: str,
        evidence_refs: Iterable[str] = (),
        assistants: Iterable[str] | None = None,
        per_call_timeout_s: Optional[float] = None,
    ) -> ConsensusResult:
        """Pregunta a los asistentes y vota el resultado.

        ``assistants`` permite restringir a un subconjunto de los registrados;
        si se omite, se usan todos.
        """
        evidence_tuple = tuple(x for x in evidence_refs if x)
        now = self._clock()

        targets = self._select_targets(assistants)
        if not targets:
            return ConsensusResult(
                subject=subject,
                question=question,
                decision=DECISION_NO_VOTES,
                winning_interpretation="",
                votes=(),
                agreement_ratio=0.0,
                evidence_refs=evidence_tuple,
                unresolved=(UNRESOLVED_NO_RESPONSE,),
                generated_at_epoch=now,
            )

        votes = tuple(
            self._collect_vote(assistant_id, question, per_call_timeout_s)
            for assistant_id in targets
        )
        valid_votes = tuple(v for v in votes if v.is_valid)

        if not valid_votes:
            return ConsensusResult(
                subject=subject,
                question=question,
                decision=DECISION_NO_VOTES,
                winning_interpretation="",
                votes=votes,
                agreement_ratio=0.0,
                evidence_refs=evidence_tuple,
                unresolved=(UNRESOLVED_NO_RESPONSE,),
                generated_at_epoch=now,
            )

        if len(valid_votes) < self._min_votes:
            winner, ratio = self._tally(valid_votes)
            return ConsensusResult(
                subject=subject,
                question=question,
                decision=DECISION_INSUFFICIENT_VOTES,
                winning_interpretation=winner,
                votes=votes,
                agreement_ratio=ratio,
                evidence_refs=evidence_tuple,
                unresolved=(UNRESOLVED_LOW_AGREEMENT,),
                generated_at_epoch=now,
            )

        winner, ratio = self._tally(valid_votes)
        if not winner:
            return self._maybe_escalate_tie(
                subject=subject,
                question=question,
                votes=votes,
                ratio=ratio,
                evidence_refs=evidence_tuple,
                now=now,
            )

        if ratio >= self._agreement_threshold:
            return ConsensusResult(
                subject=subject,
                question=question,
                decision=DECISION_CONSENSUS,
                winning_interpretation=winner,
                votes=votes,
                agreement_ratio=ratio,
                evidence_refs=evidence_tuple,
                unresolved=(),
                generated_at_epoch=now,
            )

        return self._maybe_escalate_low_agreement(
            subject=subject,
            question=question,
            winner=winner,
            votes=votes,
            ratio=ratio,
            evidence_refs=evidence_tuple,
            now=now,
        )

    # ---- internals ----------------------------------------------------

    def _select_targets(self, assistants: Iterable[str] | None) -> list[str]:
        if assistants is None:
            return list(self._interpreters.keys())
        wanted = [a for a in assistants if a in self._interpreters]
        return wanted

    def _collect_vote(
        self,
        assistant_id: str,
        question: str,
        per_call_timeout_s: float | None,
    ) -> InterpretationVote:
        fn = self._interpreters.get(assistant_id)
        if fn is None:
            return InterpretationVote(
                assistant_id=assistant_id,
                raw_text="",
                interpretation="",
                error="not_registered",
            )
        try:
            raw = fn(assistant_id, question)
        except Exception as exc:
            return InterpretationVote(
                assistant_id=assistant_id,
                raw_text="",
                interpretation="",
                error=f"interpreter_raised:{type(exc).__name__}",
            )
        if raw is None:
            return InterpretationVote(
                assistant_id=assistant_id,
                raw_text="",
                interpretation="",
                error="empty_response",
            )
        raw_text = str(raw)
        normalized = self._normalizer(raw_text)
        if not normalized:
            return InterpretationVote(
                assistant_id=assistant_id,
                raw_text=raw_text,
                interpretation="",
                error="empty_normalized",
            )
        return InterpretationVote(
            assistant_id=assistant_id,
            raw_text=raw_text,
            interpretation=normalized,
            confidence=0.0,
            error="",
        )

    def _tally(self, valid_votes: tuple[InterpretationVote, ...]) -> tuple[str, float]:
        counter = Counter(v.interpretation for v in valid_votes)
        if not counter:
            return "", 0.0
        most_common = counter.most_common()
        top_interp, top_count = most_common[0]
        if len(most_common) > 1 and most_common[1][1] == top_count:
            return "", top_count / len(valid_votes)
        return top_interp, top_count / len(valid_votes)

    def _maybe_escalate_tie(
        self,
        *,
        subject: str,
        question: str,
        votes: tuple[InterpretationVote, ...],
        ratio: float,
        evidence_refs: tuple[str, ...],
        now: float,
    ) -> ConsensusResult:
        unresolved = (UNRESOLVED_TIE,)
        decision = DECISION_TIE
        winner = ""
        if self._human_broker is not None:
            decision_from_human, interp = self._ask_human(
                subject=subject,
                question=question,
                votes=votes,
                reason="tie_between_interpretations",
            )
            if decision_from_human == DECISION_HUMAN_CONFIRMED and interp:
                return ConsensusResult(
                    subject=subject,
                    question=question,
                    decision=DECISION_HUMAN_CONFIRMED,
                    winning_interpretation=interp,
                    votes=votes,
                    agreement_ratio=ratio,
                    evidence_refs=evidence_refs,
                    unresolved=(),
                    generated_at_epoch=now,
                )
            if decision_from_human == DECISION_HUMAN_REJECTED:
                decision = DECISION_HUMAN_REJECTED
            else:
                decision = DECISION_HUMAN_DEFERRED
        return ConsensusResult(
            subject=subject,
            question=question,
            decision=decision,
            winning_interpretation=winner,
            votes=votes,
            agreement_ratio=ratio,
            evidence_refs=evidence_refs,
            unresolved=unresolved,
            generated_at_epoch=now,
        )

    def _maybe_escalate_low_agreement(
        self,
        *,
        subject: str,
        question: str,
        winner: str,
        votes: tuple[InterpretationVote, ...],
        ratio: float,
        evidence_refs: tuple[str, ...],
        now: float,
    ) -> ConsensusResult:
        unresolved = (UNRESOLVED_LOW_AGREEMENT,)
        decision = DECISION_INSUFFICIENT_VOTES
        if self._human_broker is not None:
            decision_from_human, interp = self._ask_human(
                subject=subject,
                question=question,
                votes=votes,
                reason="low_agreement_between_assistants",
                tentative_interpretation=winner,
            )
            if decision_from_human == DECISION_HUMAN_CONFIRMED and interp:
                return ConsensusResult(
                    subject=subject,
                    question=question,
                    decision=DECISION_HUMAN_CONFIRMED,
                    winning_interpretation=interp,
                    votes=votes,
                    agreement_ratio=ratio,
                    evidence_refs=evidence_refs,
                    unresolved=(),
                    generated_at_epoch=now,
                )
            if decision_from_human == DECISION_HUMAN_REJECTED:
                decision = DECISION_HUMAN_REJECTED
                winner = ""
            else:
                decision = DECISION_HUMAN_DEFERRED
        return ConsensusResult(
            subject=subject,
            question=question,
            decision=decision,
            winning_interpretation=winner,
            votes=votes,
            agreement_ratio=ratio,
            evidence_refs=evidence_refs,
            unresolved=unresolved,
            generated_at_epoch=now,
        )

    def _ask_human(
        self,
        *,
        subject: str,
        question: str,
        votes: tuple[InterpretationVote, ...],
        reason: str,
        tentative_interpretation: str = "",
    ) -> tuple[str, str]:
        broker = self._human_broker
        if broker is None:
            return (DECISION_HUMAN_DEFERRED, "")
        scope = {
            "subject": subject,
            "question": question,
            "tentative": tentative_interpretation,
            "reason_code": reason,
        }
        try:
            result = broker.request(
                kind="perception_mismatch_confirmation",
                reason=(
                    f"Consenso multi-IA no alcanzado ({reason}); se requiere "
                    f"confirmacion humana para '{subject}'."
                ),
                scope=scope,
                payload_schema=("interpretation",),
                sensitive=False,
                timeout_s=self._human_timeout_s,
            )
        except Exception:
            return (DECISION_HUMAN_DEFERRED, "")
        if result is None:
            return (DECISION_HUMAN_DEFERRED, "")
        decision_value = str(getattr(result, "decision", "")).lower()
        payload = getattr(result, "payload", None) or {}
        if decision_value == "approved":
            interp_raw = str(payload.get("interpretation") or tentative_interpretation)
            normalized = self._normalizer(interp_raw)
            if not normalized:
                return (DECISION_HUMAN_DEFERRED, "")
            return (DECISION_HUMAN_CONFIRMED, normalized)
        if decision_value == "rejected":
            return (DECISION_HUMAN_REJECTED, "")
        return (DECISION_HUMAN_DEFERRED, "")
