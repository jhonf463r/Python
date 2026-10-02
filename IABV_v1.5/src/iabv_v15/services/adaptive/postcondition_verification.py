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
        causal_correlation: Any | None = None,
    ) -> PostconditionVerification:
        observed = self.observer.observe(expectation, execution_id=execution_id)
        prefix = evidence_prefix or f"postcondition-execution:{execution_id}"
        refs = [
            f"{prefix}:baseline",
            f"{prefix}:observation",
        ]
        refs.extend(
            ref for ref in (baseline.evidence_ref, observed.evidence_ref)
            if ref and ref not in refs
        )
        correlated_refs = self._correlation_evidence_refs(
            expectation=expectation,
            observed=observed,
            causal_correlation=causal_correlation,
        )
        if baseline.source in {"observer_error", "observer_unavailable"}:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "No se obtuvo un baseline independiente válido antes de la acción."
        elif baseline.satisfied or self._contains_expected_correlation(baseline, expectation):
            verdict, attribution = "not_verified", "not_attributable"
            reason = "La expectativa ya se cumplía en el baseline; no se demuestra una transición nueva."
        elif observed.observed_at_utc <= baseline.observed_at_utc:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "La observación posterior no es más reciente que el baseline."
        elif not observed.satisfied:
            verdict, attribution = "not_verified", "not_attributable"
            reason = "La observación posterior no encontró el estado esperado."
        elif len(observed.matches) > 1:
            verdict, attribution = "ambiguous", "ambiguous_due_to_competing_causes"
            reason = "Se observaron múltiples entidades que satisfacen la expectativa y no hay vínculo causal."
        elif observed.caused_by_execution_id == execution_id:
            verdict, attribution = "verified", "directly_attributable"
            reason = "La fuente independiente vinculó el estado observado con esta ejecución."
        elif correlated_refs:
            verdict, attribution = "verified", "directly_attributable"
            reason = "La única coincidencia observada contiene el correlador declarado por una acción de la tarea ejecutada."
        else:
            verdict, attribution = "observation_only", "temporally_associated"
            reason = "El estado apareció después de la acción, pero la fuente no lo atribuye a esta ejecución."
        refs.extend(ref for ref in correlated_refs if ref not in refs)
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

    @staticmethod
    def _correlation_evidence_refs(
        *,
        expectation: PostconditionExpectation,
        observed: PostconditionObservation,
        causal_correlation: Any | None,
    ) -> list[str]:
        """Return a task/action provenance ref only for a unique exact match.

        The algorithm is field- and capability-neutral: observers expose
        their independently observed match fields, while the executed task
        supplies action identities carrying the same declared correlation ID.
        """
        if not isinstance(causal_correlation, dict):
            return []
        correlation_id = str(expectation.correlation_id or '').strip()
        correlation_field = str(expectation.correlation_field or '').strip()
        if not correlation_id or not correlation_field:
            return []
        if str(causal_correlation.get('correlation_id') or '').strip() != correlation_id:
            return []
        if str(causal_correlation.get('correlation_field') or '').strip() != correlation_field:
            return []
        task_id = str(causal_correlation.get('task_id') or '').strip()
        action_ids = causal_correlation.get('action_ids')
        if not task_id or not isinstance(action_ids, list) or not action_ids:
            return []
        if len(observed.matches) != 1:
            return []
        match = observed.matches[0]
        if not isinstance(match, dict) or str(match.get(correlation_field) or '').strip() != correlation_id:
            return []
        action_ref = ','.join(str(item).strip() for item in action_ids if str(item).strip())
        if not action_ref:
            return []
        return [f'causal-correlation:{task_id}:{action_ref}:{correlation_field}:{correlation_id}']

    @staticmethod
    def _contains_expected_correlation(
        observation: PostconditionObservation,
        expectation: PostconditionExpectation,
    ) -> bool:
        correlation_id = str(expectation.correlation_id or '').strip()
        correlation_field = str(expectation.correlation_field or '').strip()
        return bool(
            correlation_id
            and correlation_field
            and any(
                isinstance(match, dict)
                and str(match.get(correlation_field) or '').strip() == correlation_id
                for match in observation.matches
            )
        )
