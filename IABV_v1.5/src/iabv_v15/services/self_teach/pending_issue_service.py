from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, CodexPendingIssue, ProbeDiagnosis, RunRecord, RuntimeAdjustment, ScenarioDefinition
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository


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
            recommended_change=self._recommended_change(diagnosis),
            suggested_tests=self._suggested_tests(scenario, diagnosis),
            metadata={
                'pack_id': session.chosen_pack_id,
                'intent_key': session.intent.intent_key,
                'diagnostic_confidence': diagnosis.confidence,
            },
        )
        return self.repository.save(issue)

    def _recommended_change(self, diagnosis: ProbeDiagnosis) -> str:
        mapping = {
            'need_adapter': 'Conectar el adaptador operativo real del dominio antes de prometer ejecucion directa.',
            'need_codex_fix': 'Revisar la integracion entre captura, readiness, incidentes y ejecucion adaptativa.',
            'need_runtime_tuning': 'Validar si el ajuste runtime reciente basta o si toca mover logica a codigo.',
            'need_teaching': 'Separar si el fallo sigue siendo ensenanza o si ya se volvio un problema tecnico repetido.',
        }
        return mapping.get(diagnosis.category.value, 'Revisar el caso con evidencia viva.')

    def _suggested_tests(self, scenario: ScenarioDefinition, diagnosis: ProbeDiagnosis) -> list[str]:
        tests = ['Repetir el escenario en Centro de Control', 'Revisar Centro Evolutivo']
        if scenario.scenario_id == 'wplay.login':
            tests.insert(0, 'abre Wplay e inicia sesion')
        if diagnosis.category.value in {'need_runtime_tuning', 'need_codex_fix'}:
            tests.append('prueba Wplay')
        return tests
