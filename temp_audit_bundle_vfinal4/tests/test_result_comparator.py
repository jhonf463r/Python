"""Pruebas focalizadas para ResultComparator.

El PR vertical sobre el diagnostico Wplay agrega una rama en
`result_comparator.compare()` que diferencia "capability runner no corrio
(sin evidencia)" vs. "captura debil" cuando categoria=NEED_TEACHING.
Esta suite cubre:
  - La rama nueva emite summary + cause estructurados.
  - Los casos clasicos (low_visual, runtime_tuning, codex_fix, ready) no
    regresan.
"""

from __future__ import annotations

from iabv_v15.domain.models import (
    AdaptiveSession,
    CapabilityReadiness,
    CapabilityStatus,
    DiagnosticCategory,
    ScenarioDefinition,
    TaskIntent,
)
from iabv_v15.services.self_teach.result_comparator import ResultComparator


def _base_scenario(scenario_id: str = "wplay.login") -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id=scenario_id,
        title="Escenario prueba",
        site_id="wplay",
        intent_keys=["wplay.login"],
        expected_signals=[
            "capability:wplay.login",
            "capability:wplay.session.restore",
        ],
    )


def _session(
    *,
    capabilities: list[CapabilityReadiness] | None = None,
    evidence_refs: list[str] | None = None,
    incidents: list[dict] | None = None,
) -> AdaptiveSession:
    session = AdaptiveSession(
        user_goal="abre Wplay e inicia sesion",
        intent=TaskIntent(intent_key="wplay.login", title="Login Wplay"),
        chosen_pack_id="wplay.login.pack",
    )
    session.capability_readiness = capabilities or []
    session.evidence_refs = list(evidence_refs or [])
    session.context.recent_incidents = list(incidents or [])
    return session


def test_compare_emits_structured_cause_when_insufficient_without_evidence() -> None:
    """Capacidades INSUFFICIENT + sin evidencia + sin visual debil =>
    summary + cause estructurados que apuntan a 'capability runner no
    registrado' en vez del placeholder historico."""
    capabilities = [
        CapabilityReadiness(
            capability_id="wplay.login",
            title="Login Wplay",
            status=CapabilityStatus.INSUFFICIENT,
            score=0.0,
            evidence=[],
        ),
        CapabilityReadiness(
            capability_id="wplay.session.restore",
            title="Restaurar sesion",
            status=CapabilityStatus.INSUFFICIENT,
            score=0.0,
            evidence=[],
        ),
    ]
    session = _session(capabilities=capabilities, evidence_refs=[])
    scenario = _base_scenario()

    category, mismatches, summary, cause, confidence = ResultComparator().compare(
        scenario, session, expected=[], observed=[]
    )

    assert category == DiagnosticCategory.NEED_TEACHING
    # Summary NO contiene el placeholder historico
    assert "Todavia falta" not in summary
    assert "ningún signal reciente" in summary or "ningun signal reciente" in summary
    # Cause estructurada apunta a capability runner + TeachingStudio + scenario
    assert "INSUFFICIENT" in cause
    assert "capability runner" in cause.lower()
    assert "wplay.login" in cause
    assert "TeachingStudio" in cause
    assert 0.75 <= confidence <= 0.9
    assert mismatches  # Capacidad debil aun genera mismatch


def test_compare_keeps_legacy_cause_when_some_evidence_is_present() -> None:
    """Si hay evidence_refs o las capacidades tienen evidence propio,
    caemos al mensaje historico (falta refinar captura, NO falta runner)."""
    capabilities = [
        CapabilityReadiness(
            capability_id="wplay.login",
            title="Login Wplay",
            status=CapabilityStatus.INSUFFICIENT,
            evidence=["snapshot-evidence-1"],
        )
    ]
    session = _session(capabilities=capabilities, evidence_refs=["run-evidence-xyz"])

    category, _mismatches, summary, cause, _confidence = ResultComparator().compare(
        _base_scenario(), session, expected=[], observed=[]
    )

    assert category == DiagnosticCategory.NEED_TEACHING
    assert summary == (
        "La app aun no tiene suficiente evidencia reciente para ejecutar esta tarea con confianza."
    )
    assert cause == (
        "Todavia faltan pasos visibles, cobertura visual o una ensenanza mas limpia del flujo."
    )


def test_compare_partial_status_keeps_legacy_cause() -> None:
    """Capacidad en PARTIAL (no INSUFFICIENT) no activa la rama nueva; el
    programa interpreta que el runner si corrio pero la captura es debil."""
    capabilities = [
        CapabilityReadiness(
            capability_id="wplay.login",
            title="Login Wplay",
            status=CapabilityStatus.PARTIAL,
            evidence=[],
        )
    ]
    session = _session(capabilities=capabilities, evidence_refs=[])

    category, _mismatches, _summary, cause, _confidence = ResultComparator().compare(
        _base_scenario(), session, expected=[], observed=[]
    )

    assert category == DiagnosticCategory.NEED_TEACHING
    assert cause == (
        "Todavia faltan pasos visibles, cobertura visual o una ensenanza mas limpia del flujo."
    )


def test_compare_low_visual_still_uses_legacy_path() -> None:
    """Si hay low_visual (metadata visual_alignment_score muy baja), sigue
    siendo need_teaching pero con el cause historico de captura
    insuficiente, no el estructurado."""
    capabilities = [
        CapabilityReadiness(
            capability_id="wplay.login",
            title="Login Wplay",
            status=CapabilityStatus.INSUFFICIENT,
            evidence=[],
            metadata={"visual_alignment_score": 0.1},
        )
    ]
    session = _session(capabilities=capabilities, evidence_refs=[])

    category, _mismatches, _summary, cause, _confidence = ResultComparator().compare(
        _base_scenario(), session, expected=[], observed=[]
    )

    assert category == DiagnosticCategory.NEED_TEACHING
    # low_visual activa el path historico porque el replay SI se intento
    # pero la cobertura visual estuvo baja.
    assert cause == (
        "Todavia faltan pasos visibles, cobertura visual o una ensenanza mas limpia del flujo."
    )


def test_compare_ready_state_returns_ready_category() -> None:
    """Sin capacidades debiles ni incidentes => ready_for_guided_live."""
    session = _session(capabilities=[], evidence_refs=[])
    category, _, _, cause, _ = ResultComparator().compare(
        _base_scenario(), session, expected=[], observed=[]
    )
    assert category == DiagnosticCategory.READY_FOR_GUIDED_LIVE
    assert "alineados" in cause
