from datetime import timedelta
import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    AutonomousValidationSnapshot,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRecommendation,
    ExperimentRun,
    SandboxExperiment,
    SelfExaminationSnapshot,
    ToolLiveStatus,
    WindowObservation,
    WorldModelSnapshot,
    utc_now,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_operational_self_examination_service_detects_repeated_blocks_and_adjustments() -> None:
    root = _workspace('operational_self_examination')
    try:
        bootstrap = AppBootstrap(str(root))
        for _ in range(3):
            bootstrap.experiment_lab.record_outcome(
                domain=ExperimentDomain.LANGUAGE,
                objective='Revisar consulta externa bloqueada',
                subject_key='general',
                route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                candidate_label='chatgpt',
                success=False,
                observed_summary='La ruta quedo bloqueada por hilo incorrecto y termino en fallback.',
                precision=0.22,
                robustness=0.25,
                execution_ms=2400,
                metadata={
                    'assistant_kind': 'chatgpt',
                    'config_signature': 'web',
                    'external_state_flags': ['wrong_thread'],
                    'blocked': True,
                    'fallback_used': True,
                },
            )
        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='general',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                score=0.89,
                confidence=0.86,
                rationale='Codex viene cerrando mejor los cambios tecnicos repetibles.',
                metadata={
                    'adaptive_learning_summary': {
                        'reasons': ['Codex mantiene mejor precision en cambios tecnicos repetibles.'],
                    }
                },
            )
        )
        bootstrap.world_model_service.current_model = lambda: WorldModelSnapshot(  # type: ignore[assignment]
            active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=41, focused=True)],
            focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=41, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    status='abierto',
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                )
            ],
            detected_blocks=['wrong_thread'],
            confidence=0.82,
        )
        bootstrap.autonomous_validation_cycle.current_snapshot = lambda: AutonomousValidationSnapshot(  # type: ignore[assignment]
            status='active',
            summary='Claude sigue en validacion, pero Codex ya mostro mejor comportamiento para el caso tecnico.',
            promoted_count=1,
            last_experiment_id='sandbox-1',
            current_experiment=SandboxExperiment(
                subject_key='general',
                candidate_assistant_kind='claude',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                verdict='unresolved',
            ),
        )

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = {item.category for item in review.findings}

        assert review.summary
        assert review.validated_improvements
        assert 'repeated_block' in categories
        assert 'inertial_route' in categories
        assert Path(review.package_path).exists()
        assert Path(review.markdown_path).exists()
        assert 'wrong_thread' in review.assistant_brief
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_operational_self_examination_service_feedback_classifies_previous_adjustments() -> None:
    root = _workspace('operational_self_examination_feedback')
    try:
        bootstrap = AppBootstrap(str(root))
        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=2),
            recommended_adjustments=[
                {
                    'title': 'Ruta debil o inercial: codex por code_agent',
                    'recommended_change': 'Exigir validacion adicional antes de reutilizar esta ruta.',
                    'category': 'inertial_route',
                    'metadata': {'assistant_kind': 'codex', 'route': 'code_agent', 'config_signature': 'patch'},
                    'feedback_key': 'inertial_route:codex:code_agent:patch',
                    'source_refs': ['ExperimentLab', 'AdaptiveWeightLayer'],
                },
                {
                    'title': 'Ruta debil o inercial: claude por language_understanding',
                    'recommended_change': 'Debilitar esta preferencia hasta confirmar mejora.',
                    'category': 'inertial_route',
                    'metadata': {'assistant_kind': 'claude', 'route': 'language_understanding', 'config_signature': 'review'},
                    'feedback_key': 'inertial_route:claude:language_understanding:review',
                    'source_refs': ['ExperimentLab', 'AdaptiveWeightLayer'],
                },
                {
                    'title': 'Ruta debil o inercial: chatgpt por language_understanding',
                    'recommended_change': 'Exigir validacion adicional antes de reutilizar esta ruta.',
                    'category': 'inertial_route',
                    'metadata': {'assistant_kind': 'chatgpt', 'route': 'language_understanding', 'config_signature': 'web'},
                    'feedback_key': 'inertial_route:chatgpt:language_understanding:web',
                    'source_refs': ['ExperimentLab', 'AdaptiveWeightLayer'],
                },
                {
                    'title': 'Pack atascado: pack_research',
                    'recommended_change': 'Revisar defaults, readiness y preguntas obligatorias del pack.',
                    'category': 'repeated_stall',
                    'metadata': {'pack_id': 'pack_research'},
                    'feedback_key': 'repeated_stall:pack_research',
                    'source_refs': ['AdaptiveSessionRepository'],
                },
            ],
        )
        bootstrap.operational_self_examination_service.storage.save_json_atomic(
            'self_examination/latest.json',
            previous_review.model_dump(mode='json'),
        )

        def save_run(*, assistant: str, route: EvaluationRoute, config_signature: str, success: bool, score: float, blocked: bool = False, fallback: bool = False) -> ExperimentRun:
            run = ExperimentRun(
                domain=ExperimentDomain.CODE if route == EvaluationRoute.CODE_AGENT else ExperimentDomain.LANGUAGE,
                suite_name='self_exam_feedback',
                objective='Retroalimentacion de ajustes',
                subject_key='general',
                route=route,
                assistant_kind=assistant,
                config_signature=config_signature,
                candidate_label=assistant,
                success=success,
                observed_summary='Corrida sintetica para evaluar retroalimentacion de autoexaminacion.',
                metrics=ExperimentMetric(
                    total_score=score,
                    execution_ms=950 if success else 2400,
                ),
                metadata={
                    'assistant_kind': assistant,
                    'config_signature': config_signature,
                    'blocked': blocked,
                    'fallback_used': fallback,
                    'external_state_flags': ['wrong_thread'] if blocked else [],
                },
            )
            return bootstrap.experiment_lab_repository.save_run(run)

        codex_runs = [
            save_run(assistant='codex', route=EvaluationRoute.CODE_AGENT, config_signature='patch', success=True, score=0.91),
            save_run(assistant='codex', route=EvaluationRoute.CODE_AGENT, config_signature='patch', success=True, score=0.9),
            save_run(assistant='codex', route=EvaluationRoute.CODE_AGENT, config_signature='patch', success=True, score=0.93),
        ]
        save_run(assistant='claude', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='review', success=True, score=0.69)
        save_run(assistant='claude', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='review', success=True, score=0.7)
        save_run(assistant='claude', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='review', success=True, score=0.71)
        save_run(assistant='chatgpt', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='web', success=False, score=0.22, blocked=True, fallback=True)
        save_run(assistant='chatgpt', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='web', success=False, score=0.2, blocked=True, fallback=True)
        save_run(assistant='chatgpt', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='web', success=False, score=0.24, blocked=True, fallback=True)

        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='general',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                recommended_config_signature='patch',
                score=0.91,
                confidence=0.88,
                rationale='Codex volvio a ser consistente despues del ajuste previo.',
                supporting_run_ids=[run.run_id for run in codex_runs],
            )
        )
        bootstrap.autonomous_validation_cycle.current_snapshot = lambda: AutonomousValidationSnapshot(status='idle')  # type: ignore[assignment]

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        feedback = list((review.metadata or {}).get('recommendation_feedback') or [])
        statuses = {item['feedback_key']: item['status'] for item in feedback}
        summary = dict((review.metadata or {}).get('feedback_summary') or {})

        assert statuses['inertial_route:codex:code_agent:patch'] == 'validated_improvement'
        assert statuses['inertial_route:claude:language_understanding:review'] == 'valid_adjustment'
        assert statuses['inertial_route:chatgpt:language_understanding:web'] == 'false_improvement'
        assert statuses['repeated_stall:pack_research'] == 'no_evidence'
        assert summary['validated_improvement'] == 1
        assert summary['valid_adjustment'] == 1
        assert summary['false_improvement'] == 1
        assert summary['no_evidence'] == 1
        assert any(item.get('repeat_policy') == 'require_new_evidence' for item in review.recommended_adjustments if item.get('last_feedback_status') == 'false_improvement')
    finally:
        shutil.rmtree(root, ignore_errors=True)
