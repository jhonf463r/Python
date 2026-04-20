"""`ConsensusFusionService` (PCS v1 — Pieza 5).

Fusiona una lista de `IATraceEntry` del mismo ``comparison_scope_key``
en un único ganador descriptivo, aplicando una de tres estrategias:

* ``weighted_vote`` — mayoría por ``result_label`` ponderada por
  ``confidence``.
* ``highest_confidence`` — el trace con mayor ``confidence``.
* ``first_success`` — el primer trace con ``success=True`` (orden de
  entrada, i.e. el más temprano cronológicamente si el caller ordenó).

Contratos que respeta:
  * **No muta** los traces de entrada (se consumen como read-only).
  * Devuelve siempre un `ConsensusResult` bien tipado; ante lista
    vacía, kwargs inválidos o estrategia desconocida, marca
    ``unresolved_fields`` con la razón en vez de lanzar.
  * No decide rutas operativas; el consumidor decide qué hacer con el
    ganador. No toca red, filesystem ni estado vivo.
  * No usa ``getattr``/``setattr`` para esquivar tipado: lee atributos
    definidos en el contrato `IATraceEntry`.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from iabv_v15.domain.models import ConsensusResult, IATraceEntry
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer

# Estrategias soportadas. Cualquier otro valor degrada a fail-observable.
_STRATEGY_WEIGHTED_VOTE = "weighted_vote"
_STRATEGY_HIGHEST_CONFIDENCE = "highest_confidence"
_STRATEGY_FIRST_SUCCESS = "first_success"
_SUPPORTED_STRATEGIES = frozenset(
    {
        _STRATEGY_WEIGHTED_VOTE,
        _STRATEGY_HIGHEST_CONFIDENCE,
        _STRATEGY_FIRST_SUCCESS,
    }
)


class ConsensusFusionService:
    """Servicio descriptivo de consenso.

    El ``AdaptiveWeightLayer`` se recibe por constructor para dejar
    wireada la dependencia aunque hoy no se utilice en la fórmula; una
    próxima iteración puede ponderar votos por el historial adaptativo
    del asistente. Mantenerlo en el constructor evita un refactor
    posterior de los consumidores.
    """

    def __init__(self, *, adaptive_weight_layer: AdaptiveWeightLayer) -> None:
        self._weight_layer = adaptive_weight_layer

    def fuse(
        self,
        *,
        candidate_traces: list[IATraceEntry],
        strategy: str = _STRATEGY_WEIGHTED_VOTE,
    ) -> ConsensusResult:
        strategy_clean = (strategy or "").strip().lower() or _STRATEGY_WEIGHTED_VOTE

        if not candidate_traces:
            return ConsensusResult(
                strategy_used=strategy_clean,
                reasoning="No candidate traces provided.",
                unresolved_fields=["no_candidates"],
                metadata={"strategy_requested": strategy_clean},
            )

        if strategy_clean not in _SUPPORTED_STRATEGIES:
            return ConsensusResult(
                comparison_scope_key=str(
                    candidate_traces[0].comparison_scope_key or ""
                ),
                strategy_used=strategy_clean,
                reasoning=(
                    f"Unknown strategy '{strategy_clean}'. "
                    f"Supported: {sorted(_SUPPORTED_STRATEGIES)}."
                ),
                considered_trace_ids=[str(t.trace_id) for t in candidate_traces],
                unresolved_fields=["unknown_strategy"],
                metadata={"strategy_requested": strategy_clean},
            )

        scope_key = str(candidate_traces[0].comparison_scope_key or "")
        considered = [str(t.trace_id) for t in candidate_traces]

        if strategy_clean == _STRATEGY_WEIGHTED_VOTE:
            return self._weighted_vote(
                candidate_traces=candidate_traces,
                scope_key=scope_key,
                considered=considered,
            )
        if strategy_clean == _STRATEGY_HIGHEST_CONFIDENCE:
            return self._highest_confidence(
                candidate_traces=candidate_traces,
                scope_key=scope_key,
                considered=considered,
            )
        # first_success
        return self._first_success(
            candidate_traces=candidate_traces,
            scope_key=scope_key,
            considered=considered,
        )

    # ------------------------------------------------------------------
    # Estrategias

    def _weighted_vote(
        self,
        *,
        candidate_traces: list[IATraceEntry],
        scope_key: str,
        considered: list[str],
    ) -> ConsensusResult:
        totals: dict[str, float] = defaultdict(float)
        best_per_label: dict[str, IATraceEntry] = {}
        for trace in candidate_traces:
            label = str(trace.result_label or "").strip().lower() or "unlabeled"
            confidence = max(0.0, float(trace.confidence or 0.0))
            totals[label] += confidence
            incumbent = best_per_label.get(label)
            if incumbent is None or float(trace.confidence or 0.0) > float(
                incumbent.confidence or 0.0
            ):
                best_per_label[label] = trace

        if not totals:
            return ConsensusResult(
                comparison_scope_key=scope_key,
                strategy_used=_STRATEGY_WEIGHTED_VOTE,
                reasoning="Weighted vote found no usable labels.",
                considered_trace_ids=considered,
                unresolved_fields=["no_usable_labels"],
                metadata={"strategy_requested": _STRATEGY_WEIGHTED_VOTE},
            )

        # Ganador: mayor peso total. Desempate por label alfabético.
        winning_label, winning_weight = max(
            totals.items(), key=lambda item: (item[1], -ord(item[0][0]) if item[0] else 0)
        )
        winner = best_per_label[winning_label]
        total_weight = sum(totals.values()) or 1.0
        consensus_confidence = round(winning_weight / total_weight, 4)
        reasoning = (
            f"weighted_vote winner label='{winning_label}' with "
            f"summed_confidence={winning_weight:.4f} over total="
            f"{total_weight:.4f}. Representative trace="
            f"{winner.trace_id} (assistant_kind='{winner.assistant_kind}')."
        )
        return ConsensusResult(
            comparison_scope_key=scope_key,
            winning_trace_id=str(winner.trace_id),
            winning_assistant_kind=str(winner.assistant_kind or ""),
            winning_label=winning_label,
            strategy_used=_STRATEGY_WEIGHTED_VOTE,
            confidence=consensus_confidence,
            reasoning=reasoning,
            considered_trace_ids=considered,
            unresolved_fields=[],
            metadata={
                "strategy_requested": _STRATEGY_WEIGHTED_VOTE,
                "label_weights": _serialize_totals(totals),
                "total_weight": round(float(total_weight), 4),
            },
        )

    def _highest_confidence(
        self,
        *,
        candidate_traces: list[IATraceEntry],
        scope_key: str,
        considered: list[str],
    ) -> ConsensusResult:
        winner = max(
            candidate_traces, key=lambda t: float(t.confidence or 0.0)
        )
        reasoning = (
            f"highest_confidence winner trace_id={winner.trace_id} "
            f"(confidence={float(winner.confidence or 0.0):.4f}, "
            f"assistant_kind='{winner.assistant_kind}')."
        )
        return ConsensusResult(
            comparison_scope_key=scope_key,
            winning_trace_id=str(winner.trace_id),
            winning_assistant_kind=str(winner.assistant_kind or ""),
            winning_label=str(winner.result_label or ""),
            strategy_used=_STRATEGY_HIGHEST_CONFIDENCE,
            confidence=round(float(winner.confidence or 0.0), 4),
            reasoning=reasoning,
            considered_trace_ids=considered,
            unresolved_fields=[],
            metadata={"strategy_requested": _STRATEGY_HIGHEST_CONFIDENCE},
        )

    def _first_success(
        self,
        *,
        candidate_traces: list[IATraceEntry],
        scope_key: str,
        considered: list[str],
    ) -> ConsensusResult:
        winner: IATraceEntry | None = None
        for trace in candidate_traces:
            if bool(trace.success):
                winner = trace
                break

        if winner is None:
            return ConsensusResult(
                comparison_scope_key=scope_key,
                strategy_used=_STRATEGY_FIRST_SUCCESS,
                reasoning="first_success found no trace with success=True.",
                considered_trace_ids=considered,
                unresolved_fields=["no_success"],
                metadata={"strategy_requested": _STRATEGY_FIRST_SUCCESS},
            )

        reasoning = (
            f"first_success winner trace_id={winner.trace_id} "
            f"(assistant_kind='{winner.assistant_kind}', "
            f"label='{winner.result_label}')."
        )
        return ConsensusResult(
            comparison_scope_key=scope_key,
            winning_trace_id=str(winner.trace_id),
            winning_assistant_kind=str(winner.assistant_kind or ""),
            winning_label=str(winner.result_label or ""),
            strategy_used=_STRATEGY_FIRST_SUCCESS,
            confidence=round(float(winner.confidence or 0.0), 4),
            reasoning=reasoning,
            considered_trace_ids=considered,
            unresolved_fields=[],
            metadata={"strategy_requested": _STRATEGY_FIRST_SUCCESS},
        )


def _serialize_totals(totals: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"label": label, "weight": round(float(weight), 4)}
        for label, weight in sorted(totals.items(), key=lambda item: -item[1])
    ]
