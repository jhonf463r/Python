from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, ProbeDiagnosis, RunRecord, ScenarioDefinition
from iabv_v15.services.self_teach.expectation_matcher import ExpectationMatcher
from iabv_v15.services.self_teach.result_comparator import ResultComparator


class ExecutionProbeService:
    def __init__(self, *, matcher: ExpectationMatcher, comparator: ResultComparator) -> None:
        self.matcher = matcher
        self.comparator = comparator

    def analyze_result(self, *, run_record: RunRecord, session: AdaptiveSession, scenario: ScenarioDefinition) -> ProbeDiagnosis:
        expected, observed = self.matcher.compare(scenario, session)
        category, mismatches, summary, cause, confidence = self.comparator.compare(scenario, session, expected, observed)
        evidence_refs = list(dict.fromkeys(session.evidence_refs + [run_record.run_id]))[:8]
        return ProbeDiagnosis(
            scenario_id=scenario.scenario_id,
            category=category,
            summary=summary,
            probable_cause=cause,
            confidence=confidence,
            mismatches=mismatches,
            recommended_action=self._recommended_action(category),
            evidence_refs=evidence_refs,
            metadata={
                'expected_signals': expected,
                'observed_signals': observed,
                'intent_key': session.intent.intent_key,
                'pack_id': session.chosen_pack_id,
            },
        )

    def _recommended_action(self, category) -> str:
        mapping = {
            'need_teaching': 'Abrir una ensenanza corta y reforzar solo el microflujo que falta.',
            'need_runtime_tuning': 'Aplicar un ajuste runtime seguro y volver a probar el escenario.',
            'need_adapter': 'Crear o conectar el adaptador operativo del dominio antes de prometer ejecucion real.',
            'need_codex_fix': 'Escalar el caso con evidencia viva a Codex porque ya no parece resoluble solo con tuning.',
            'ready_for_guided_live': 'Pedir aprobacion y pasar a una prueba guiada en vivo.',
        }
        return mapping.get(getattr(category, 'value', str(category)), 'Revisar el diagnostico y decidir el siguiente paso.')
