from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, CodexPendingIssue, ProbeDiagnosis, RunRecord, RuntimeAdjustment, ScenarioDefinition
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository


# Cadena canonica del placeholder historico que suele colarse cuando el
# comparator no encuentra datos suficientes. Se usa para detectarla y
# reemplazarla por un recommended_change estructurado.
_TEACHING_PLACEHOLDER_MARKERS = (
    "todavia falta una ensenanza mas clara",
    "todavia faltan pasos visibles",
    "hace falta una explicacion mas clara",
)


def _looks_like_teaching_placeholder(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in _TEACHING_PLACEHOLDER_MARKERS)


class PendingIssueService:
    def __init__(self, repository: PendingIssueRepository) -> None:
        self.repository = repository

    def enqueue(
        self,
        *,
        scenario: ScenarioDefinition,
        run_record: RunRecord,
        session: AdaptiveSession,
        diagnosis: ProbeDiagnosis,
        runtime_adjustments: list[RuntimeAdjustment],
    ) -> CodexPendingIssue:
        lead_episode = next((item.last_episode_id for item in session.capability_readiness if item.last_episode_id), None)
        issue = CodexPendingIssue(
            scenario_id=scenario.scenario_id,
            goal=run_record.request.user_goal,
            category=diagnosis.category,
            summary=diagnosis.summary,
            probable_cause=diagnosis.probable_cause,
            unresolved_reason=diagnosis.recommended_action,
            run_id=run_record.run_id,
            episode_id=lead_episode,
            session_id=session.session_id,
            evidence_refs=list(diagnosis.evidence_refs[:8]),
            runtime_adjustments=list(runtime_adjustments),
            recommended_change=self._recommended_change(scenario, diagnosis),
            suggested_tests=self._suggested_tests(scenario, diagnosis),
            metadata={
                'pack_id': session.chosen_pack_id,
                'intent_key': session.intent.intent_key,
                'diagnostic_confidence': diagnosis.confidence,
            },
        )
        return self.repository.save(issue)

    def _recommended_change(
        self, scenario: ScenarioDefinition, diagnosis: ProbeDiagnosis
    ) -> str:
        mapping = {
            'need_adapter': 'Conectar el adaptador operativo real del dominio antes de prometer ejecucion directa.',
            'need_codex_fix': 'Revisar la integracion entre captura, readiness, incidentes y ejecucion adaptativa.',
            'need_runtime_tuning': 'Validar si el ajuste runtime reciente basta o si toca mover logica a codigo.',
            'need_teaching': 'Separar si el fallo sigue siendo ensenanza o si ya se volvio un problema tecnico repetido.',
        }
        default = mapping.get(diagnosis.category.value, 'Revisar el caso con evidencia viva.')

        # Cuando el diagnostico es need_teaching y el probable_cause/summary
        # trae el placeholder historico, el recommended_change generico no
        # ayuda al caller. Emitimos un mensaje estructurado que apunte al
        # capability runner + TeachingStudio + scenario concreto.
        if diagnosis.category.value == 'need_teaching' and (
            _looks_like_teaching_placeholder(diagnosis.probable_cause)
            or _looks_like_teaching_placeholder(diagnosis.summary)
        ):
            scenario_id = scenario.scenario_id or 'desconocido'
            expected_caps = list(scenario.expected_signals or [])[:3]
            caps_hint = (
                f" ({', '.join(expected_caps)})" if expected_caps else ""
            )
            return (
                f"Registrar el capability runner de '{scenario_id}'{caps_hint} "
                "en el capability_runner_registry y capturar el microflujo en "
                "TeachingStudio; sin runner + captura previos el pack sensible "
                "no puede emitir UniversalPerceptionSignal y el diagnostico se "
                "queda en NEED_TEACHING permanente."
            )
        return default

    def _suggested_tests(self, scenario: ScenarioDefinition, diagnosis: ProbeDiagnosis) -> list[str]:
        tests = ['Repetir el escenario en Centro de Control', 'Revisar Centro Evolutivo']
        scenario_id = scenario.scenario_id or ''
        if scenario_id == 'wplay.login':
            tests.insert(0, 'abre Wplay e inicia sesion')
        if diagnosis.category.value == 'need_teaching' and scenario_id.startswith('wplay.'):
            tests.insert(
                0,
                f"Verificar que el capability runner de '{scenario_id}' este "
                "registrado en capability_runner_registry",
            )
        if diagnosis.category.value in {'need_runtime_tuning', 'need_codex_fix'}:
            tests.append('prueba Wplay')
        return tests
