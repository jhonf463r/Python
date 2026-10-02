from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from iabv_v15.domain.models import (
    PostconditionExpectation,
    PostconditionObservation,
    PostconditionVerification,
)


class PostconditionObserver(Protocol):
    def observe(self, expectation: PostconditionExpectation, *, execution_id: str) -> PostconditionObservation:
        """Read the target state independently from the operational executor."""


class WorldModelWindowObserver:
    """Targeted, local window read using WorldModelService's OS enumerator.

    This deliberately avoids ``scan_now``: that full composition also probes
    network/tool availability and is not needed to verify a window predicate.
    """

    source = "world_model.windows.local_os_enumerator"

    def __init__(self, world_model_service: Any) -> None:
        self.world_model_service = world_model_service

    def observe(self, expectation: PostconditionExpectation, *, execution_id: str) -> PostconditionObservation:
        if expectation.kind != "window_present":
            return PostconditionObservation(source=self.source, evidence_ref=f"postcondition-observation:{uuid4()}")
        rows = self.world_model_service._list_windows()
        needle = expectation.title.strip().casefold()
        matches = [
            {"title": str(row.get("title") or ""), "pid": int(row.get("pid") or 0)}
            for row in rows
            if needle and needle == str(row.get("title") or "").strip().casefold()
        ]
        return PostconditionObservation(
            source=self.source,
            observed_at_utc=datetime.now(timezone.utc),
            satisfied=bool(matches),
            matches=matches,
            evidence_ref=f"postcondition-observation:{uuid4()}",
        )


class PostconditionVerificationService:
    def __init__(self, observer: PostconditionObserver) -> None:
        self.observer = observer

    def capture_baseline(self, expectation: PostconditionExpectation, *, execution_id: str) -> PostconditionObservation:
        return self.observer.observe(expectation, execution_id=execution_id)

    def verify(
        self,
        *,
        execution_id: str,
        expectation: PostconditionExpectation,
        baseline: PostconditionObservation,
        evidence_prefix: str = "",
    ) -> PostconditionVerification:
        observed = self.observer.observe(expectation, execution_id=execution_id)
        prefix = evidence_prefix or f"postcondition-execution:{execution_id}"
        refs = [
            f"{prefix}:baseline",
            f"{prefix}:observation",
        ]
        if baseline.source in {"observer_error", "observer_unavailable"}:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "No se obtuvo un baseline independiente válido antes de la acción."
        elif baseline.satisfied:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "La expectativa ya se cumplía en el baseline; no se demuestra una transición nueva."
        elif observed.observed_at_utc <= baseline.observed_at_utc:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "La observación posterior no es más reciente que el baseline."
        elif not observed.satisfied:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "La observación posterior no encontró el estado esperado."
        elif observed.caused_by_execution_id == execution_id:
            verdict, attribution = "verified", "directly_attributable"
            reason = "La fuente independiente vinculó el estado observado con esta ejecución."
        elif len(observed.matches) > 1:
            verdict, attribution = "ambiguous", "ambiguous_due_to_competing_causes"
            reason = "Se observaron múltiples entidades que satisfacen la expectativa y no hay vínculo causal."
        else:
            verdict, attribution = "observation_only", "temporally_associated"
            reason = "El estado apareció después de la acción, pero la fuente no lo atribuye a esta ejecución."
        return PostconditionVerification(
            execution_id=execution_id,
            expectation=expectation,
            baseline=baseline,
            observation=observed,
            verdict=verdict,
            attribution=attribution,
            reason=reason,
            evidence_refs=refs,
        )
