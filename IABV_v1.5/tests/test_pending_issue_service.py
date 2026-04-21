"""Pruebas focalizadas para PendingIssueService.

La estrategia es evitar el `PendingIssueRepository` real (que requiere
`AppDatabase` + `ArtifactStorage`) usando un fake que sólo capture lo
persistido y devuelva la misma issue. Esto mantiene la prueba sobre el
comportamiento de `enqueue` + `_recommended_change` + `_suggested_tests`,
que es lo que este PR modifica.
"""

from __future__ import annotations

from iabv_v15.domain.models import (
    AdaptiveSession,
    CapabilityReadiness,
    CapabilityStatus,
    CodexPendingIssue,
    DiagnosticCategory,
    InferenceRequest,
    InferenceResult,
    ProbeDiagnosis,
    ProviderKind,
    ReasoningMode,
    RouteDecision,
    RunRecord,
    ScenarioDefinition,
    TaskIntent,
)
from iabv_v15.services.self_teach.pending_issue_service import (
    PendingIssueService,
    _looks_like_teaching_placeholder,
)


class _CapturingRepository:
    """Fake de `PendingIssueRepository` que sólo captura la issue guardada."""

    def __init__(self) -> None:
        self.saved: list[CodexPendingIssue] = []

    def save(self, issue: CodexPendingIssue) -> CodexPendingIssue:
        self.saved.append(issue)
        return issue


def _build_scenario(scenario_id: str = "wplay.login") -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id=scenario_id,
        title="Escenario wplay de prueba",
        summary="",
        site_id="wplay",
        intent_keys=["wplay.login"],
        expected_signals=[
            "capability:wplay.login",
            "capability:wplay.session.restore",
            "capability:wplay.navigate.casino",
        ],
    )


def _build_session() -> AdaptiveSession:
    return AdaptiveSession(
        user_goal="abre Wplay e inicia sesion",
        intent=TaskIntent(intent_key="wplay.login", title="Login Wplay"),
        chosen_pack_id="wplay.login.pack",
    )


def _build_run_record(goal: str = "abre Wplay e inicia sesion") -> RunRecord:
    request = InferenceRequest(user_goal=goal, site_hint="wplay")
    result = InferenceResult(
        request_id=request.request_id,
        provider_name="local",
        reasoning_mode=ReasoningMode.LOCAL,
        summary="stub",
        inferred_task=goal,
        confidence=0.5,
    )
    route = RouteDecision(
        primary_provider="local",
        primary_kind=ProviderKind.LOCAL,
        reason="fixture de prueba",
    )
    return RunRecord(request=request, result=result, route=route)


def _build_diagnosis(
    *,
    category: DiagnosticCategory = DiagnosticCategory.NEED_TEACHING,
    summary: str = "",
    probable_cause: str = "",
    recommended_action: str = "",
) -> ProbeDiagnosis:
    return ProbeDiagnosis(
        scenario_id="wplay.login",
        category=category,
        summary=summary,
        probable_cause=probable_cause,
        recommended_action=recommended_action,
        confidence=0.78,
    )


def test_placeholder_detector_matches_historic_strings() -> None:
    assert _looks_like_teaching_placeholder("Todavia falta una ensenanza mas clara.")
    assert _looks_like_teaching_placeholder(
        "Todavia faltan pasos visibles, cobertura visual o una ensenanza mas limpia"
    )
    assert _looks_like_teaching_placeholder(
        "Hace falta una explicacion mas clara del hueco de ensenanza."
    )
    assert _looks_like_teaching_placeholder("")
    assert _looks_like_teaching_placeholder("   ")


def test_placeholder_detector_ignores_structured_cause() -> None:
    assert not _looks_like_teaching_placeholder(
        "Capacidades en estado INSUFFICIENT sin evidencia reciente"
    )
    assert not _looks_like_teaching_placeholder(
        "El playbook llega a execute sin un ejecutor operativo real del dominio."
    )


def test_enqueue_emits_structured_recommended_change_when_diagnosis_is_placeholder() -> None:
    """Si el diagnosis arrastra el placeholder 'Todavia falta…', el
    recommended_change generico 'Separar si el fallo sigue siendo…' se
    reemplaza por uno estructurado que apunta a capability runner +
    TeachingStudio + scenario concreto."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    scenario = _build_scenario("wplay.login")
    diagnosis = _build_diagnosis(
        summary="La app aun no tiene suficiente evidencia reciente.",
        probable_cause="Todavia faltan pasos visibles, cobertura visual o una ensenanza mas limpia del flujo.",
        recommended_action="Abrir una ensenanza corta.",
    )

    issue = service.enqueue(
        scenario=scenario,
        run_record=_build_run_record(),
        session=_build_session(),
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert "capability_runner_registry" in issue.recommended_change
    assert "TeachingStudio" in issue.recommended_change
    assert "wplay.login" in issue.recommended_change
    # Debe listar al menos una capability concreta esperada del escenario
    assert "capability:wplay.login" in issue.recommended_change
    # No debe dejar el mensaje generico
    assert issue.recommended_change != (
        "Separar si el fallo sigue siendo ensenanza o si ya se volvio un problema tecnico repetido."
    )


def test_enqueue_keeps_generic_recommended_change_for_non_placeholder_teaching() -> None:
    """Si la ProbeDiagnosis trae un probable_cause especifico (NO placeholder),
    el recommended_change usa el mensaje generico de need_teaching. No
    queremos sobreescribir diagnostico valido."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    diagnosis = _build_diagnosis(
        summary="La evidencia visual sigue debil.",
        probable_cause="El replay visual aun no muestra bien correo/contrasena/submit.",
    )

    issue = service.enqueue(
        scenario=_build_scenario("wplay.login"),
        run_record=_build_run_record(),
        session=_build_session(),
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert issue.recommended_change == (
        "Separar si el fallo sigue siendo ensenanza o si ya se volvio un problema tecnico repetido."
    )


def test_enqueue_recommended_change_uses_mapping_for_non_teaching_categories() -> None:
    """Para need_adapter/need_codex_fix/need_runtime_tuning el mensaje mapeado
    sigue siendo la fuente de verdad (no hay reescritura)."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]

    cases = {
        DiagnosticCategory.NEED_ADAPTER: "Conectar el adaptador operativo real del dominio antes de prometer ejecucion directa.",
        DiagnosticCategory.NEED_CODEX_FIX: "Revisar la integracion entre captura, readiness, incidentes y ejecucion adaptativa.",
        DiagnosticCategory.NEED_RUNTIME_TUNING: "Validar si el ajuste runtime reciente basta o si toca mover logica a codigo.",
    }
    for category, expected in cases.items():
        diagnosis = _build_diagnosis(
            category=category,
            probable_cause="Todavia falta una ensenanza mas clara.",  # placeholder, pero categoria != need_teaching
        )
        issue = service.enqueue(
            scenario=_build_scenario("wplay.login"),
            run_record=_build_run_record(),
            session=_build_session(),
            diagnosis=diagnosis,
            runtime_adjustments=[],
        )
        assert issue.recommended_change == expected, category


def test_enqueue_suggested_tests_inject_runner_verification_for_wplay_teaching() -> None:
    """Para need_teaching en escenarios wplay.*, el primer test sugerido
    debe apuntar a verificar el capability_runner_registry (no solo 'abre
    Wplay')."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    diagnosis = _build_diagnosis(probable_cause="Todavia falta una ensenanza mas clara.")

    issue = service.enqueue(
        scenario=_build_scenario("wplay.login"),
        run_record=_build_run_record(),
        session=_build_session(),
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert any(
        "capability_runner_registry" in test for test in issue.suggested_tests
    ), issue.suggested_tests
    # Mantiene tambien los legacy 'abre Wplay' + 'Revisar Centro Evolutivo'
    assert any("abre Wplay e inicia sesion" in t for t in issue.suggested_tests)
    assert any("Revisar Centro Evolutivo" in t for t in issue.suggested_tests)


def test_enqueue_suggested_tests_preserve_prueba_wplay_for_codex_fix() -> None:
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    diagnosis = _build_diagnosis(category=DiagnosticCategory.NEED_CODEX_FIX)

    issue = service.enqueue(
        scenario=_build_scenario("wplay.login"),
        run_record=_build_run_record(),
        session=_build_session(),
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert "prueba Wplay" in issue.suggested_tests


def test_enqueue_suggested_tests_do_not_inject_runner_hint_for_non_wplay() -> None:
    """La sugerencia de capability_runner_registry es especifica de wplay.*,
    no debe colarse para escenarios ajenos al dominio."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    scenario = ScenarioDefinition(
        scenario_id="google.search",
        title="Busqueda generica en Google",
        site_id="google",
        intent_keys=["browser.search.google"],
    )
    diagnosis = _build_diagnosis(probable_cause="Todavia falta una ensenanza mas clara.")

    issue = service.enqueue(
        scenario=scenario,
        run_record=_build_run_record("busca en Google"),
        session=_build_session(),
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert not any(
        "capability_runner_registry" in test for test in issue.suggested_tests
    )


def test_enqueue_structured_message_handles_scenario_without_expected_signals() -> None:
    """Si el escenario no trae expected_signals, el mensaje estructurado
    debe seguir siendo generable (sin lanzar errores) y no debe emitir un
    parentesis vacio."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    scenario = ScenarioDefinition(
        scenario_id="wplay.login",
        title="login wplay minimal",
        site_id="wplay",
        expected_signals=[],
    )
    diagnosis = _build_diagnosis(probable_cause="Todavia falta una ensenanza mas clara.")

    issue = service.enqueue(
        scenario=scenario,
        run_record=_build_run_record(),
        session=_build_session(),
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert "()" not in issue.recommended_change
    assert "wplay.login" in issue.recommended_change


def test_enqueue_propagates_probable_cause_summary_and_evidence() -> None:
    """Contract check: `enqueue` no debe mutar ni perder probable_cause,
    summary, evidence_refs provenientes del diagnosis (solo cambiamos
    recommended_change + suggested_tests)."""
    service = PendingIssueService(_CapturingRepository())  # type: ignore[arg-type]
    session = _build_session()
    session.capability_readiness = [
        CapabilityReadiness(
            capability_id="wplay.login",
            title="Login wplay",
            status=CapabilityStatus.INSUFFICIENT,
            last_episode_id="ep-1",
        )
    ]
    diagnosis = _build_diagnosis(
        summary="La app aun no tiene suficiente evidencia reciente.",
        probable_cause="Capacidades en estado INSUFFICIENT sin evidencia reciente",
        recommended_action="Abrir TeachingStudio.",
    )
    diagnosis.evidence_refs = ["evidence-1", "evidence-2"]

    issue = service.enqueue(
        scenario=_build_scenario("wplay.login"),
        run_record=_build_run_record(),
        session=session,
        diagnosis=diagnosis,
        runtime_adjustments=[],
    )

    assert issue.summary == "La app aun no tiene suficiente evidencia reciente."
    assert (
        issue.probable_cause
        == "Capacidades en estado INSUFFICIENT sin evidencia reciente"
    )
    assert issue.unresolved_reason == "Abrir TeachingStudio."
    assert issue.evidence_refs == ["evidence-1", "evidence-2"]
    assert issue.episode_id == "ep-1"
