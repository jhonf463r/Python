from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import AssistantConfigurationSnapshot, EvaluationRoute, ExperimentCandidate, ExperimentDomain
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _lab(root: Path) -> ExperimentLab:
    repository = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), ArtifactStorage(str(root / 'evolution')))
    return ExperimentLab(
        repository=repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer()),
    )


def test_experiment_lab_compares_formula_and_selects_math_route() -> None:
    root = _workspace('experiment_lab_formula')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        candidates = [
            ExperimentCandidate(
                label='math-local',
                route=EvaluationRoute.MATH_EVALUATION,
                output_text='x = 4',
                execution_ms=18,
                operational_cost=0.02,
                metadata={'reused_pattern': True},
            ),
            ExperimentCandidate(
                label='fallback-language',
                route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                output_text='tal vez x sea 5',
                execution_ms=12,
                operational_cost=0.03,
            ),
        ]
        runs, recommendation = lab.run_experiment(
            domain=ExperimentDomain.EQUATION,
            objective='Resolver una ecuacion simple',
            subject_key='math.general',
            expected={'expression': 'x = 4', 'value': '4'},
            candidates=candidates,
        )

        assert len(runs) == 2
        assert max(item.metrics.total_score for item in runs) == runs[0].metrics.total_score
        assert recommendation.recommended_route == EvaluationRoute.MATH_EVALUATION
        assert recommendation.score >= 0.7
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_experiment_lab_scores_ocr_and_object_detection() -> None:
    root = _workspace('experiment_lab_ocr')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        candidates = [
            ExperimentCandidate(
                label='vision-local',
                route=EvaluationRoute.OCR_VISION,
                output_text='Saldo disponible',
                extracted_data={'recognized_text': 'Saldo disponible', 'objects': ['boton', 'saldo']},
                execution_ms=55,
                operational_cost=0.08,
            )
        ]
        runs, recommendation = lab.run_experiment(
            domain=ExperimentDomain.OCR,
            objective='Leer texto y objetos de una captura',
            subject_key='ocr.wallet',
            expected={'text': 'Saldo disponible', 'objects': ['saldo', 'boton']},
            candidates=candidates,
        )

        assert runs[0].metrics.precision >= 0.95
        assert recommendation.recommended_route == EvaluationRoute.OCR_VISION
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_experiment_lab_suggest_route_uses_persisted_history() -> None:
    root = _workspace('experiment_lab_history')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        lab.run_experiment(
            domain=ExperimentDomain.CODE,
            objective='Explicar una funcion',
            subject_key='code.review',
            expected={'required_tokens': ['funcion', 'retorna']},
            candidates=[
                ExperimentCandidate(
                    label='code-agent',
                    route=EvaluationRoute.CODE_AGENT,
                    output_text='La funcion retorna el valor final.',
                    execution_ms=44,
                    operational_cost=0.15,
                ),
                ExperimentCandidate(
                    label='language',
                    route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                    output_text='Es algo de codigo.',
                    execution_ms=20,
                    operational_cost=0.04,
                ),
            ],
        )

        recommendation = lab.suggest_route(domain=ExperimentDomain.CODE, subject_key='code.review')

        assert recommendation is not None
        assert recommendation.recommended_route == EvaluationRoute.CODE_AGENT
        assert recommendation.confidence > 0.5
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_experiment_lab_records_observed_outcome_and_recommends_same_route() -> None:
    root = _workspace('experiment_lab_observed_outcome')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        run, recommendation = lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver un incidente tecnico guiado',
            subject_key='wplay:need_codex_fix',
            route=EvaluationRoute.LOCAL,
            candidate_label='ollama_llm',
            success=True,
            observed_summary='Ajustar sondeo y drenado sin bloquear la pagina.',
            expected_summary='abre Wplay e inicia sesion',
            precision=0.78,
            robustness=0.72,
            operational_cost=0.06,
            reuse_score=0.55,
            user_progress=0.12,
            metadata={'validation_status': 'review_needed', 'execution_lane': 'codex_packet'},
            suite_name='external_consultation',
        )

        stored_runs = lab.repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key='wplay:need_codex_fix', limit=5)
        stored_recommendation = lab.suggest_route(domain=ExperimentDomain.CODE, subject_key='wplay:need_codex_fix')

        assert stored_runs
        assert stored_runs[0].run_id == run.run_id
        assert stored_runs[0].metadata['validation_status'] == 'review_needed'
        assert recommendation.recommended_route == EvaluationRoute.LOCAL
        assert stored_recommendation is not None
        assert stored_recommendation.recommended_route == EvaluationRoute.LOCAL
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_experiment_lab_recommends_best_assistant_configuration() -> None:
    root = _workspace('experiment_lab_assistant_configuration')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Diagnosticar un incidente tecnico',
            subject_key='incident.bridge',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=True,
            observed_summary='Hipotesis general del incidente.',
            precision=0.41,
            robustness=0.44,
            execution_ms=620,
            metadata={
                'assistant_kind': 'chatgpt',
                'assistant_configuration': AssistantConfigurationSnapshot(
                    browser_mode='with_browser',
                    assistant_mode='general',
                    origin_mode='external',
                ).model_dump(mode='json'),
                'config_signature': 'without_plan|without_files|normal|short|without_tools|with_browser|general|external',
            },
        )

        run, recommendation = lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Diagnosticar un incidente tecnico',
            subject_key='incident.bridge',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_installed',
            success=True,
            observed_summary='Ajustar cola y drenado del bridge visible.',
            precision=0.88,
            robustness=0.84,
            execution_ms=210,
            metadata={
                'assistant_kind': 'codex',
                'assistant_configuration': AssistantConfigurationSnapshot(
                    planning_mode='with_plan',
                    reasoning_level='extended',
                    tools_mode='with_tools',
                    browser_mode='without_browser',
                    assistant_mode='code',
                    origin_mode='external',
                ).model_dump(mode='json'),
                'config_signature': 'with_plan|without_files|extended|short|with_tools|without_browser|code|external',
                'reused_later': True,
                'trace_id': 'trace-codex-1',
                'comparison_scope_key': 'incident-bridge',
                'source_trace_ids': ['trace-chatgpt-0'],
                'proposal_summary': 'Revisar incidente del bridge visible con contexto tecnico.',
                'outcome_summary': 'Ajustar cola y drenado del bridge visible.',
            },
        )

        assert run.assistant_kind == 'codex'
        assert run.assistant_configuration.assistant_mode == 'code'
        assert run.config_signature.endswith('|code|external')
        assert run.metadata['trace_id'] == 'trace-codex-1'
        assert run.metadata['comparison_scope_key'] == 'incident-bridge'
        assert recommendation.recommended_route == EvaluationRoute.CODE_AGENT
        assert recommendation.recommended_assistant_kind == 'codex'
        assert recommendation.recommended_config_signature == run.config_signature
        assert recommendation.metadata['ranked_configurations'][0]['assistant_kind'] == 'codex'
        assert 'incident-bridge' in recommendation.metadata['comparison_scope_keys']
        assert 'trace-codex-1' in recommendation.metadata['winning_trace_ids']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_experiment_lab_returns_fallback_when_history_has_only_failures() -> None:
    root = _workspace('experiment_lab_failure_only_history')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.LANGUAGE,
            objective='Consultar un asistente externo bloqueado',
            subject_key='language.blocked.external',
            route=EvaluationRoute.UI,
            candidate_label='chatgpt_web_assisted',
            success=False,
            observed_summary='browser_input_missing',
            precision=0.0,
            robustness=0.0,
            user_progress=0.0,
            metadata={
                'assistant_kind': 'chatgpt web asistido',
                'trace_id': 'trace-blocked-1',
                'comparison_scope_key': 'blocked-external-scope',
            },
        )

        recommendation = lab.suggest_route(domain=ExperimentDomain.LANGUAGE, subject_key='language.blocked.external')

        assert recommendation is not None
        assert recommendation.recommended_route == EvaluationRoute.FALLBACK
        assert 'Todavia no hay una corrida exitosa' in recommendation.rationale
        assert 'trace-blocked-1' in recommendation.metadata['losing_trace_ids']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_experiment_lab_adaptive_weights_penalize_blocked_and_fallback_routes() -> None:
    root = _workspace('experiment_lab_adaptive_weights')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=True,
            observed_summary='Diagnostico parcial con bloqueo de hilo.',
            precision=0.9,
            robustness=0.82,
            execution_ms=1900,
            metadata={
                'assistant_kind': 'chatgpt',
                'used_fallback': True,
                'external_state_flags': ['wrong_thread'],
                'outcome_summary': 'Ruta parcial y bloqueada.',
            },
        )

        _, recommendation = lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_installed',
            success=True,
            observed_summary='Correccion precisa del bridge sin bloqueo.',
            precision=0.83,
            robustness=0.84,
            execution_ms=240,
            metadata={
                'assistant_kind': 'codex',
                'config_signature': 'with_plan|without_files|extended|short|with_tools|without_browser|code|external',
                'outcome_summary': 'Correccion precisa del bridge.',
            },
        )

        ranked = recommendation.metadata['ranked_configurations']
        assert recommendation.recommended_route == EvaluationRoute.CODE_AGENT
        assert recommendation.recommended_assistant_kind == 'codex'
        assert ranked[0]['assistant_kind'] == 'codex'
        assert ranked[0]['weighted_score'] > ranked[1]['weighted_score']
        assert ranked[1]['blocked_rate'] > 0.0
        assert recommendation.metadata['adaptive_learning_summary']['reasons']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_list_candidate_traces_for_scope_returns_matching_traces() -> None:
    root = _workspace('lab_scope_selector')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Fix bug',
            subject_key='code:review',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_run',
            success=True,
            observed_summary='Fixed correctly.',
            precision=0.9,
            metadata={
                'assistant_kind': 'codex',
                'comparison_scope_key': 'code_review:codex_vs_claude',
            },
        )
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Fix bug',
            subject_key='code:review',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='claude_run',
            success=True,
            observed_summary='Also fixed.',
            precision=0.85,
            metadata={
                'assistant_kind': 'claude_web',
                'comparison_scope_key': 'code_review:codex_vs_claude',
            },
        )
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Other task',
            subject_key='code:other',
            route=EvaluationRoute.FALLBACK,
            candidate_label='other',
            success=False,
            observed_summary='Unrelated.',
            metadata={
                'comparison_scope_key': 'unrelated_scope',
            },
        )

        traces = lab.list_candidate_traces_for_scope('code_review:codex_vs_claude')

        assert len(traces) == 2
        kinds = sorted(t.assistant_kind for t in traces)
        assert kinds == ['claude_web', 'codex']
        for trace in traces:
            assert trace.comparison_scope_key == 'code_review:codex_vs_claude'
            assert trace.success is True
            assert trace.confidence > 0.0
            assert trace.metadata.get('from_experiment_run')
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_list_candidate_traces_for_scope_returns_empty_for_no_match() -> None:
    root = _workspace('lab_scope_no_match')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        traces = lab.list_candidate_traces_for_scope('nonexistent_scope')
        assert traces == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_list_candidate_traces_for_scope_empty_key_returns_empty() -> None:
    root = _workspace('lab_scope_empty_key')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        lab = _lab(root)
        assert lab.list_candidate_traces_for_scope('') == []
    finally:
        shutil.rmtree(root, ignore_errors=True)
