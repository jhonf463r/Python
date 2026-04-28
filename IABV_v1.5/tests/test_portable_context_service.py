import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    AutonomousValidationSnapshot,
    CodexPendingIssue,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ObservationPermissionGate,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
    ProposalValidationResult,
    SandboxExperiment,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    ToolDiscoverySignal,
    ToolDiscoveryStatus,
    ToolLiveStatus,
    ToolEvolutionDecisionLog,
    WindowObservation,
    WorldModelSnapshot,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_portable_context_service_builds_and_persists_package_from_live_state() -> None:
    root = _workspace('portable_context_live_state')
    try:
        bootstrap = AppBootstrap(str(root))
        bootstrap.objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Consolidar IABV con memoria portable',
                site_id='iabv',
                status=ObjectiveStatus.ACTIVE,
                progress=0.64,
                confidence=0.82,
            )
        )
        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='iabv:portable-context',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                score=0.91,
                confidence=0.87,
                rationale='Codex viene cerrando mejor los cambios reversibles en el repo.',
                metadata={
                    'comparison_scope_keys': ['iabv:portable-context'],
                    'adaptive_learning_summary': {
                        'reasons': ['Codex mantiene mejor precision en cambios locales reversibles.'],
                    },
                },
            )
        )
        bootstrap.experiment_lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Consolidar el contexto portable del repo',
            subject_key='iabv:portable-context',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_installed',
            success=True,
            observed_summary='Codex resolvio mejor los cambios reversibles del contexto portable.',
            precision=0.86,
            robustness=0.82,
            execution_ms=240,
            metadata={
                'assistant_kind': 'codex',
                'config_signature': 'codex-portable',
                'comparison_scope_key': 'iabv:portable-context',
            },
        )
        bootstrap.pending_issue_repository.save(
            CodexPendingIssue(
                summary='Pulir export del contexto portable en la UI.',
                probable_cause='Aun no hay accion rapida visible en todos los paneles.',
                recommended_change='Exponer copia del brief portable donde haga falta.',
            )
        )
        bootstrap.environment_self_awareness_service.current_model = lambda: EnvironmentSelfModel(  # type: ignore[assignment]
            environment_id='iabv-laptop',
            scan_status='ready',
            notifications=['Entorno listo para una nueva sesion.'],
        )
        bootstrap.world_model_service.current_model = lambda: WorldModelSnapshot(  # type: ignore[assignment]
            active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=77, focused=True)],
            focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=77, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    available=True,
                    status='abierto',
                    thread_status='hilo_correcto',
                    messages_status='disponibles',
                )
            ],
            permission_gates=[
                ObservationPermissionGate(
                    scope='observe.codex.window',
                    assistant_kind='codex',
                    title='Observar Codex',
                    detail='Necesito observar la ventana de Codex antes de reutilizarla.',
                    status='requerido',
                    required_for=['consult_codex'],
                )
            ],
            detected_blocks=['permission_required'],
            confidence=0.84,
        )
        bootstrap.autonomous_validation_cycle.current_snapshot = lambda: AutonomousValidationSnapshot(  # type: ignore[assignment]
            status='active',
            summary='Sigo validando Claude como alternativa antes de promoverla.',
            current_experiment=SandboxExperiment(
                subject_key='iabv:portable-context',
                candidate_assistant_kind='claude',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                verdict='unresolved',
            ),
        )
        bootstrap.autonomous_validation_cycle.current_decision_log = lambda refresh=False: ToolEvolutionDecisionLog(  # type: ignore[assignment]
            entries=[
                ProposalValidationResult(
                    proposal_id='proposal-1',
                    proposal_key='iabv:portable-context|validate_local_first|language_understanding|chatgpt||code_agent|codex|codex-portable',
                    domain=ExperimentDomain.CODE,
                    subject_key='iabv:portable-context',
                    proposal_kind='validate_local_first',
                    decision='promoted',
                    winner='proposed_tool',
                    reason='Codex ganó en sandbox y quedó promovido para este problema.',
                    current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                    current_assistant_kind='chatgpt',
                    candidate_route=EvaluationRoute.CODE_AGENT,
                    candidate_assistant_kind='codex',
                )
            ]
        )
        bootstrap.autonomous_validation_cycle.decision_log_summary = lambda log=None: {  # type: ignore[assignment]
            'winning_by_problem': {'iabv:portable-context': 'codex'},
            'degraded_tools': ['chatgpt'],
            'in_validation': [],
            'last_decision': {
                'subject_key': 'iabv:portable-context',
                'decision': 'promoted',
                'winner': 'proposed_tool',
                'reason': 'Codex ganó en sandbox y quedó promovido para este problema.',
            },
            'summary_by_tool': {'chatgpt': 'degradado', 'codex': 'ganando'},
            'summary_by_problem': {'iabv:portable-context': 'codex'},
            'unresolved_fields': [],
            'package_path': '',
            'markdown_path': '',
        }
        bootstrap.tool_discovery_service.current_status = lambda refresh=False, subject_key=None: ToolDiscoveryStatus(  # type: ignore[assignment]
            summary='Detecte nuevos candidatos para este problema y uno ya fue promovido.',
            signals=[
                ToolDiscoverySignal(
                    proposal_key='iabv:portable-context|validate_discovery|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|desktop_app:codex_consult_v1:external_assistant',
                    domain=ExperimentDomain.CODE,
                    scope='iabv:portable-context',
                    title='Probar Codex',
                    summary='Codex aparece disponible y vale la pena validarlo.',
                    tool_id='codex_installed',
                    tool_title='Codex instalado',
                    assistant_kind='codex',
                    route=EvaluationRoute.CODE_AGENT,
                    config_signature='desktop_app:codex_consult_v1:external_assistant',
                    status='promoted',
                    confidence=0.84,
                    compatibility_score=0.92,
                    impact_score=0.8,
                    cost_score=0.68,
                )
            ],
            metadata={
                'active_signals': [],
                'in_validation_signals': [],
                'promoted_signals': [
                    {
                        'tool_id': 'codex_installed',
                        'tool_title': 'Codex instalado',
                        'status': 'promoted',
                    }
                ],
                'discarded_signals': [],
            },
        )
        bootstrap.operational_self_examination_service.current_review = lambda **kwargs: SelfExaminationSnapshot(  # type: ignore[assignment]
            summary='La autoexaminacion confirma un bloqueo recurrente y un ajuste recomendado.',
            status='needs_attention',
            findings=[
                SelfExaminationFinding(
                    category='repeated_block',
                    title='Bloqueo recurrente: wrong_thread',
                    summary='Codex sigue cayendo en hilo incorrecto si no se preflightea.',
                    recommendation='Exigir verificacion de hilo antes de reusar Codex.',
                    confidence=0.81,
                    source_refs=['ExperimentLab', 'WorldModelSnapshot'],
                )
            ],
            recurring_issues=[{'title': 'wrong_thread', 'summary': 'Se repite en consultas comparables.'}],
            recommended_adjustments=[{'title': 'Preflight de hilo', 'recommended_change': 'Exigir verificacion de hilo antes de reusar Codex.'}],
            validated_improvements=[{'title': 'Codex por code_agent', 'summary': 'Sigue siendo la ruta mas fuerte para cambios reversibles.'}],
            unresolved_risks=['UNRESOLVED:self_examination'],
            metadata={
                'recommendation_feedback': [
                    {
                        'title': 'Preflight de hilo',
                        'status': 'false_improvement',
                        'summary': 'Sin verificar el hilo, el ajuste no produjo beneficio real.',
                        'next_step': 'No repetir este ajuste sin evidencia nueva.',
                    }
                ],
                'feedback_summary': {
                    'total_reviewed': 1,
                    'validated_improvement': 0,
                    'valid_adjustment': 0,
                    'false_improvement': 1,
                    'no_evidence': 0,
                },
            },
        )

        package = bootstrap.portable_context_service.current_package(refresh=True)

        section_ids = {section.section_id for section in package.sections}
        assert package.summary
        assert 'Codex' in package.assistant_brief or 'codex' in package.assistant_brief
        assert {'project_state', 'architecture', 'user_metacognitive_intent', 'recommended_routes', 'pending', 'hard_rules', 'self_examination', 'tool_discovery', 'tool_evolution', 'tool_evolution_decisions'} <= section_ids
        assert Path(package.package_path).exists()
        assert Path(package.markdown_path).exists()
        assert package.metadata['tool_discovery_summary']['promoted_signals'][0]['tool_id'] == 'codex_installed'
        assert package.metadata['tool_discovery_signals'][0]['status'] == 'promoted'
        assert package.metadata['tool_evolution_summary']['top_performers']
        assert package.metadata['tool_evolution_summary']['winning_by_problem']['iabv:portable-context'] == 'codex'
        assert package.metadata['tool_evolution_summary']['decided_proposal_count'] >= 1
        assert package.metadata['tool_evolution_proposals'] == []
        assert package.metadata['tool_evolution_decision_summary']['winning_by_problem']['iabv:portable-context'] == 'codex'
        assert package.metadata['tool_evolution_validated_proposals'][0]['decision'] == 'promoted'
        tool_discovery = next(section for section in package.sections if section.section_id == 'tool_discovery')
        assert tool_discovery.metadata['promoted_signal_count'] == 1
        tool_evolution = next(section for section in package.sections if section.section_id == 'tool_evolution')
        assert tool_evolution.metadata['winning_by_problem']['iabv:portable-context'] == 'codex'
        assert tool_evolution.metadata['active_proposal_count'] == 0
        assert tool_evolution.metadata['decided_proposal_count'] >= 1
        assert package.metadata['autoexamination_summary']['status'] == 'needs_attention'
        assert package.metadata['recommended_adjustments']
        assert package.metadata['recommendation_feedback'][0]['status'] == 'false_improvement'
        assert package.metadata['feedback_summary']['false_improvement'] == 1
        intent_section = next(section for section in package.sections if section.section_id == 'user_metacognitive_intent')
        assert any(item.get('label') == 'no_repetir_intencion' for item in intent_section.items)
        assert 'todas las IAs' in package.assistant_brief
        operational_blocks = next(section for section in package.sections if section.section_id == 'operational_blocks')
        assert any(
            item.get('kind') == 'permission_gate'
            and item.get('assistant_kind') == 'codex'
            and 'observar la ventana de Codex'.lower() in str(item.get('detail') or '').lower()
            for item in operational_blocks.items
        )
        assert 'UNRESOLVED' in package.assistant_brief
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_portable_context_service_infers_active_goal_from_recent_adaptive_session_when_no_objective_exists() -> None:
    """H1: sin ObjectiveNode en el repo pero con un user_goal reciente
    registrado via AdaptiveSessionRepository, el paquete portable debe
    surfacear ese intent como active_title TENTATIVO y dejar marcas
    explicitas de 'inferred_from_recent_session' en metadata para que
    consumidores puedan distinguir un objetivo confirmado de uno
    tentativo."""
    from iabv_v15.domain.models import AdaptiveSession, TaskIntent

    root = _workspace('portable_context_infer_goal')
    try:
        bootstrap = AppBootstrap(str(root))
        # Deliberadamente NO guardamos ObjectiveNode: asi simulamos el
        # estado vivo del usuario donde GoalEngine aun no materializo
        # un objetivo pero la UI si registro user_goal en una sesion.
        session = AdaptiveSession(
            user_goal='auditar todo mi programa y dejarlo probado',
            intent=TaskIntent(
                intent_key='general.assistance',
                title='Auditoria general',
            ),
        )
        bootstrap.adaptive_session_repository.save(session)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        project_state = next(section for section in package.sections if section.section_id == 'project_state')
        active_item = next(item for item in project_state.items if item.get('label') == 'Objetivo activo')
        assert 'auditar todo mi programa' in str(active_item.get('value') or '').lower()
        assert 'UNRESOLVED:active_goal_context' not in package.unresolved_fields
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_portable_context_service_keeps_unresolved_when_adaptive_session_is_stale() -> None:
    """H1: proteccion contra stale. Si la sesion mas reciente es
    anterior a la ventana de recencia, el servicio NO propaga su
    user_goal como active_title y mantiene la marca UNRESOLVED.
    Preferible admitir que no hay objetivo a inventar uno stale."""
    from datetime import datetime, timedelta, timezone

    from iabv_v15.domain.models import AdaptiveSession, TaskIntent

    root = _workspace('portable_context_stale_session')
    try:
        bootstrap = AppBootstrap(str(root))
        stale_created_at = datetime.now(timezone.utc) - timedelta(days=10)
        session = AdaptiveSession(
            user_goal='intent stale que no debe propagarse',
            intent=TaskIntent(intent_key='general.assistance', title='stale'),
            created_at_utc=stale_created_at,
            updated_at_utc=stale_created_at,
        )
        bootstrap.adaptive_session_repository.save(session)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        project_state = next(section for section in package.sections if section.section_id == 'project_state')
        active_item = next(item for item in project_state.items if item.get('label') == 'Objetivo activo')
        assert 'intent stale' not in str(active_item.get('value') or '').lower()
        assert 'sin objetivo activo confirmado' in str(active_item.get('value') or '').lower()
        assert 'UNRESOLVED:active_goal_context' in package.unresolved_fields
    finally:
        shutil.rmtree(root, ignore_errors=True)
