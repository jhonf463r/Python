from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import AdaptiveSessionStatus, AssistantConfigurationSnapshot, CapabilityReadiness, CapabilityStatus, CapturedStep, EnvironmentRiskSignal, EnvironmentSelfModel, EvaluationRoute, ExperimentDomain, ExperimentRecommendation, HiddenIncident, InferenceRequest, InferenceResult, IssueSeverity, NetworkStatusSnapshot, ObservationPermissionGate, ProviderHealth, ProviderStatus, ReasoningMode, RoleRoute, RunRecord, RunStatus, SessionArtifact, TaskRole, ToolLiveStatus, WindowObservation, WorldModelSnapshot
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.adaptive.adaptive_planner_service import AdaptivePlannerService
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.approval_gate_service import ApprovalGateService
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService
from iabv_v15.services.providers.base import LLMProvider


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeProvider(LLMProvider):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_name=self._name, status=ProviderStatus.READY, available=True, detail='ok')

    def _result(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self._name,
            reasoning_mode=ReasoningMode.LOCAL,
            summary=f'{self._name} handled {request.user_goal}',
            inferred_task=request.user_goal,
            confidence=0.8,
            executor_model='fake-model',
        )


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _orchestrator(root: Path) -> tuple[AdaptiveTaskOrchestrator, EpisodeRepository]:
    db = AppDatabase(str(root / 'app.sqlite'))
    episodes = EpisodeRepository(str(root / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    dossiers = ExecutionDossierRepository(db, evolution_storage)
    experiment_lab = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab_service = ExperimentLab(
        repository=experiment_lab,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    incidents = HiddenIncidentRepository(db, evolution_storage)
    clues = UserClueRepository(db, evolution_storage)
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    strategy_packs = StrategyPackRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)
    site_policies = SitePolicyRegistry(str(root / 'site_policies'))
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding:0.6b',
        lightweight_model='embeddinggemma',
        state_path=str(root / 'embedding_state.json'),
    )
    sql = SqlQueryAdvisorService(str(root / 'app.sqlite'))
    analytics = AnalyticsStrategyService(episodes, knowledge, runs, artifacts)
    support = CustomerSupportService(knowledge, embedding, sql)
    devassist = DevelopmentAssistService(str(root))
    pbt = PBTControlService(str(root / 'models'))
    gaps = TeachingGapAnalyzer()
    engineering = EngineeringReviewService(
        workspace_root=str(root),
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        artifact_repository=artifacts,
        analytics_service=analytics,
        teaching_gap_analyzer=gaps,
        pbt_service=pbt,
        development_assist_service=devassist,
    )
    router = LocalRoleRouter(
        workspace_root=str(root),
        general_provider=FakeProvider('Ollama'),
        visual_provider=FakeProvider('Ollama Vision'),
        optional_provider=FakeProvider('LM Studio'),
        embedding_service=embedding,
        sql_service=sql,
        analytics_service=analytics,
        customer_support_service=support,
        engineering_review_service=engineering,
        teaching_gap_analyzer=gaps,
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        artifact_repository=artifacts,
    )
    context = TaskContextAssembler(
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        dossier_repository=dossiers,
        hidden_incident_repository=incidents,
        site_policy_registry=site_policies,
        capability_repository=capabilities,
        adaptive_session_repository=adaptive_sessions,
        artifact_repository=artifacts,
        experiment_lab_repository=experiment_lab,
    )
    orchestrator = AdaptiveTaskOrchestrator(
        role_router=router,
        adaptive_session_repository=adaptive_sessions,
        intent_service=IntentUnderstandingService(),
        context_assembler=context,
        capability_service=CapabilityReadinessService(capabilities),
        strategy_pack_registry=StrategyPackRegistry(strategy_packs),
        planner_service=AdaptivePlannerService(),
        approval_gate_service=ApprovalGateService(),
        execution_playbook_service=ExecutionPlaybookService(),
        task_outcome_recorder=TaskOutcomeRecorder(
            adaptive_session_repository=adaptive_sessions,
            capability_repository=capabilities,
            approval_checkpoint_repository=approvals,
            experiment_lab=experiment_lab_service,
            adaptive_weight_layer=adaptive_weight_layer,
        ),
        autonomy_governance_policy=AutonomyGovernancePolicy(),
    )
    return orchestrator, episodes


def _seed_wplay_teaching(episodes: EpisodeRepository, *, include_casino: bool = False) -> None:
    episode = episodes.create_episode('Wplay login', tags=['wplay'])
    steps = [
        CapturedStep(episode_id=episode.episode_id, action_type='input', metadata={'field_role': 'email', 'url': 'https://wplay.co/login'}),
        CapturedStep(episode_id=episode.episode_id, action_type='input', metadata={'field_role': 'password', 'url': 'https://wplay.co/login'}),
        CapturedStep(episode_id=episode.episode_id, action_type='keydown', metadata={'key_display': 'Enter', 'textPreview': 'iniciar sesion', 'url': 'https://wplay.co/login'}),
        CapturedStep(episode_id=episode.episode_id, action_type='click', metadata={'textPreview': 'loggedInPlayer balance', 'url': 'https://wplay.co'}),
    ]
    if include_casino:
        steps.append(CapturedStep(episode_id=episode.episode_id, action_type='click', metadata={'textPreview': 'casino en linea', 'url': 'https://wplay.co/casino'}))
    for step in steps:
        episodes.save_step(episode.episode_id, step)


def test_adaptive_orchestrator_routes_open_wplay_to_site_pack() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_wplay_core'))
    _seed_wplay_teaching(episodes)
    request = InferenceRequest(user_goal='puedes abrir la pagina de wplay ?', auto_route=True, enable_planning=True, site_hint='wplay')

    route, result, session = orchestrator.handle_request(request)

    assert route.task_role == TaskRole.TRAINING
    assert result.intent['intent_key'] == 'wplay.core'
    assert result.chosen_pack['pack_id'] == 'wplay.core'
    guidance = result.raw_output['assistant_guidance']
    assert guidance['mode'] == 'need_teaching'
    assert 'me falta una ensenanza limpia' in result.summary
    assert any(item['capability_id'] == 'wplay.session.restore' for item in result.capability_readiness)
    assert any(item['action'] == 'open_teaching_studio' for item in guidance['actions'])
    assert any(item['title'] == 'Aprobar estrategia' for item in result.approval_checkpoints)
    assert all(item['title'] != 'Aprobar fase critica' for item in result.approval_checkpoints)
    assert session.status.value == 'waiting_approval'


def test_adaptive_orchestrator_detects_wplay_login_and_avoids_generic_questions() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_login'))
    _seed_wplay_teaching(episodes)
    request = InferenceRequest(user_goal='abre Wplay e inicia sesion', auto_route=True, enable_planning=True, site_hint='wplay')

    route, result, session = orchestrator.handle_request(request)
    assert route.task_role == TaskRole.TRAINING
    assert result.intent['intent_key'] == 'wplay.login'
    assert result.chosen_pack['pack_id'] == 'wplay.login'
    assert 'me falta una ensenanza limpia' in result.summary
    assert '?Qu? intenciones tienes' not in result.summary
    assert result.raw_output['assistant_guidance']['mode'] == 'need_teaching'
    assert len(result.approval_checkpoints) >= 1
    assert 'Abrir ensenanza' in result.next_actions
    assert session.status.value == 'waiting_approval'




def test_adaptive_orchestrator_context_exposes_recent_teaching_brief() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_recent_teaching_brief'))
    _seed_wplay_teaching(episodes)
    latest = episodes.list_recent(limit=1)[0]
    artifacts = orchestrator.context_assembler.artifact_repository
    assert artifacts is not None
    artifacts.save(
        SessionArtifact(
            episode_id=latest.episode_id,
            kind='teaching_brief',
            path=f'{latest.episode_id}/brief/teaching_brief.json',
            metadata={'artifact_kind': 'teaching_brief'},
        ),
        payload={
            'lesson_title': 'Wplay login corto',
            'target_label': 'Wplay',
            'start_url': 'https://www.wplay.co/login',
            'objective': 'Abrir Wplay e iniciar sesion.',
            'expected_outcome': 'Sesion iniciada y panel principal visible.',
            'notes': 'No compartir secretos.',
        },
    )

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='abre Wplay e inicia sesion',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
        )
    )

    recent_teachings = result.raw_output['adaptive_session']['context']['recent_teachings']
    assert recent_teachings
    assert recent_teachings[0]['start_url'] == 'https://www.wplay.co/login'
    assert recent_teachings[0]['objective'] == 'Abrir Wplay e iniciar sesion.'
    assert recent_teachings[0]['expected_outcome'] == 'Sesion iniciada y panel principal visible.'


def test_adaptive_orchestrator_prefers_recent_teaching_over_stale_capability_snapshot() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_stale_capability'))
    _seed_wplay_teaching(episodes)
    orchestrator.capability_service.capability_repository.save(
        CapabilityReadiness(
            capability_id='wplay.login',
            title='Login Wplay',
            status=CapabilityStatus.READY_WITH_APPROVAL,
            score=0.94,
            site_id='wplay',
            evidence=['snapshot viejo'],
            missing_signals=[],
            suggested_next_step='snapshot viejo',
        )
    )

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='abre Wplay e inicia sesion',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
        )
    )

    login_capability = next(item for item in result.capability_readiness if item['capability_id'] == 'wplay.login')
    assert login_capability['status'] != 'ready_with_approval'
    assert result.raw_output['assistant_guidance']['mode'] == 'need_teaching'
    assert 'me falta una ensenanza limpia' in result.summary

def test_adaptive_orchestrator_builds_multiphase_casino_plan() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_casino'))
    _seed_wplay_teaching(episodes, include_casino=True)
    request = InferenceRequest(
        user_goal='abre Wplay, ve a casino en linea, juega y aplica estrategias disponibles',
        auto_route=True,
        enable_planning=True,
        site_hint='wplay',
    )

    _, result, session = orchestrator.handle_request(request)

    assert result.intent['intent_key'] == 'wplay.casino'
    assert result.chosen_pack['pack_id'] == 'wplay.casino'
    assert len(result.playbook['steps']) >= 6
    assert any(item['capability_id'] == 'wplay.navigate.casino' for item in result.capability_readiness)
    first_candidate = result.strategy_candidates[0]
    parameter_keys = {item['key'] for item in first_candidate['parameters']}
    assert {'bankroll_units', 'stop_gain_pct', 'stop_loss_pct'} <= parameter_keys
    assert any(item['title'] == 'Aprobar fase critica' for item in result.approval_checkpoints)
    assert session.playbook is not None
    assert session.playbook.next_phase == 'approval'


def test_adaptive_orchestrator_exposes_environment_self_model_in_result() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_environment_self_model'))
    _seed_wplay_teaching(episodes)

    class FakeEnvironmentService:
        def current_model(self) -> EnvironmentSelfModel:
            return EnvironmentSelfModel(
                environment_id='cyborg15-demo',
                known_environment=True,
                scan_status='ready',
                notifications=['Entorno listo para esta corrida.'],
                ai_capacity={'preferred_local_assistant_kind': 'ollama'},
            )

        def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> EnvironmentSelfModel:
            return self.current_model()

    orchestrator.context_assembler.environment_self_awareness_service = FakeEnvironmentService()

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='abre Wplay e inicia sesion',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
        )
    )

    assert result.raw_output['environment_self_model']['environment_id'] == 'cyborg15-demo'
    assert result.raw_output['decision_context']['metadata']['environment_id'] == 'cyborg15-demo'


def test_adaptive_orchestrator_exposes_world_model_in_result_and_decision_context() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_world_model'))
    _seed_wplay_teaching(episodes)

    class FakeWorldModelService:
        def current_model(self) -> WorldModelSnapshot:
            return WorldModelSnapshot(
                active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=77, focused=True)],
                focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=77, focused=True),
                tool_live_status=[
                    ToolLiveStatus(
                        tool_id='codex_installed',
                        title='Codex instalado',
                        assistant_kind='codex',
                        available=True,
                        status='abierto',
                        thread_status='otro_hilo_activo',
                        messages_status='disponibles',
                    )
                ],
                network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
                detected_blocks=['wrong_thread'],
                confidence=0.79,
            )

        def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> WorldModelSnapshot:
            return self.current_model()

    orchestrator.context_assembler.world_model_service = FakeWorldModelService()

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='abre Wplay e inicia sesion',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
        )
    )

    assert result.raw_output['world_model']['focused_window']['title'] == 'Codex - IABV'
    assert result.raw_output['world_model_summary']['detected_blocks'] == ['wrong_thread']
    assert result.raw_output['decision_context']['metadata']['world_model_summary']['codex_status']['thread_status'] == 'otro_hilo_activo'


def test_adaptive_orchestrator_exposes_portable_context_summary_in_result() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_portable_context'))
    _seed_wplay_teaching(episodes)

    class FakePortableContextService:
        def current_package(self, **kwargs):
            return {'package_id': 'portable-ctx-1', 'kwargs': kwargs}

        def package_summary(self, package):
            return {
                'package_id': 'portable-ctx-1',
                'summary': 'Contexto portable listo para una sesion nueva.',
                'assistant_brief': 'Portable context ready.',
                'package_path': 'portable_context/latest.json',
                'markdown_path': 'portable_context/latest.md',
                'self_examination_summary': {'status': 'needs_attention', 'summary': 'La ruta web viene repitiendo bloqueos.'},
            }

    orchestrator.context_assembler.portable_context_service = FakePortableContextService()

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='resume el estado del proyecto',
            auto_route=True,
            site_hint='wplay',
        )
    )

    assert result.raw_output['portable_context_summary']['package_id'] == 'portable-ctx-1'
    assert result.raw_output['decision_context']['metadata']['portable_context_summary']['summary'] == 'Contexto portable listo para una sesion nueva.'
    assert result.raw_output['portable_context_summary']['self_examination_summary']['status'] == 'needs_attention'


def test_autonomy_governance_policy_degrades_under_environment_pressure() -> None:
    policy = AutonomyGovernancePolicy()

    governance = policy.evaluate(
        user_goal='consulta con codex este incidente tecnico',
        session_status=AdaptiveSessionStatus.PLANNED.value,
        session_readiness={},
        live_audit={},
        assistant_guidance={'mode': 'need_codex_fix'},
        capability_snapshot=[],
        approval_pending=False,
        environment_self_model=EnvironmentSelfModel(
            environment_id='cyborg15-demo',
            scan_status='ready',
            ai_capacity={'preferred_local_assistant_kind': 'ollama'},
            risk_signals=[
                EnvironmentRiskSignal(
                    kind='ram_critical',
                    severity=IssueSeverity.CRITICAL,
                    summary='La RAM libre esta en zona critica.',
                )
            ],
        ),
    )

    assert governance['recommended_action'] == 'continue_local'
    assert governance['block_risky_action'] is True
    assert governance['autonomy_level'] == 'protective_local'
    assert 'RAM libre' in ' '.join(governance['blockers'])


def test_autonomy_governance_policy_blocks_codex_when_world_model_reports_wrong_thread() -> None:
    policy = AutonomyGovernancePolicy()

    governance = policy.evaluate(
        user_goal='revisa con codex este incidente tecnico',
        session_status=AdaptiveSessionStatus.PLANNED.value,
        session_readiness={},
        live_audit={},
        assistant_guidance={'mode': 'need_codex_fix'},
        capability_snapshot=[],
        approval_pending=False,
        world_model=WorldModelSnapshot(
            focused_window=WindowObservation(title='Codex - personal', app_name='Codex', pid=45, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    available=True,
                    status='abierto',
                    detail='Codex esta abierto, pero el hilo activo mas reciente parece distinto al del workspace actual.',
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                )
            ],
            network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
            confidence=0.82,
        ),
    )

    assert governance['recommended_action'] == 'audit_autonomy'
    assert governance['block_risky_action'] is True
    assert governance['autonomy_level'] == 'guarded_research'
    assert 'workspace' in ' '.join(governance['blockers']).lower()


def test_adaptive_orchestrator_preflight_requires_observation_permission_for_codex() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_preflight_permission'))
    _seed_wplay_teaching(episodes)

    class FakeWorldModelService:
        def current_model(self) -> WorldModelSnapshot:
            return self.request_refresh(reason='manual', full=False)

        def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> WorldModelSnapshot:
            return WorldModelSnapshot(
                active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=91, focused=True)],
                focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=91, focused=True),
                tool_live_status=[
                    ToolLiveStatus(
                        tool_id='codex_installed',
                        title='Codex instalado',
                        assistant_kind='codex',
                        available=True,
                        status='abierto',
                        detail='Para verificar si Codex esta listo de verdad necesito observar el contenido visible de esa ventana.',
                        thread_status='correcto_probable',
                        session_status='abierta',
                        messages_status='desconocidos',
                        permission_state='requerido',
                        probe_status='permiso_requerido',
                    )
                ],
                network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
                permission_gates=[
                    ObservationPermissionGate(
                        scope='observe_window_content:codex',
                        assistant_kind='codex',
                        status='requerido',
                        title='Observacion de Codex',
                        detail='Para verificar si Codex tiene mensajes disponibles necesito observar esa ventana.',
                        required_for=['consult_codex'],
                    )
                ],
                detected_blocks=['permission_required:observe_window_content:codex'],
                confidence=0.83,
            )

    orchestrator.context_assembler.world_model_service = FakeWorldModelService()

    preflight = orchestrator.preflight_external_assistant(
        user_goal='consulta con codex este incidente tecnico',
        assistant_kind='codex',
    )

    assert preflight['blocked'] is True
    assert preflight['governance']['approval_required'] is True
    assert preflight['governance']['recommended_action'] == 'request_observation_permission'
    assert preflight['approval_checkpoints']
    assert preflight['approval_checkpoints'][0]['phase_key'] == 'observation_permission'


def test_adaptive_orchestrator_preflight_does_not_reask_granted_observation_permission() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_preflight_permission_granted'))
    _seed_wplay_teaching(episodes)

    class FakeWorldModelService:
        def current_model(self) -> WorldModelSnapshot:
            return self.request_refresh(reason='manual', full=False)

        def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> WorldModelSnapshot:
            return WorldModelSnapshot(
                active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=91, focused=True)],
                focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=91, focused=True),
                tool_live_status=[
                    ToolLiveStatus(
                        tool_id='codex_installed',
                        title='Codex instalado',
                        assistant_kind='codex',
                        available=True,
                        status='abierto',
                        detail='Permiso concedido.',
                        thread_status='correcto_probable',
                        session_status='abierta',
                        messages_status='desconocidos',
                        permission_state='concedido',
                        probe_status='permiso_concedido_esperando_probe',
                    )
                ],
                network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
                permission_gates=[
                    ObservationPermissionGate(
                        scope='observe_window_content:codex',
                        assistant_kind='codex',
                        status='concedido',
                        title='Observacion de Codex',
                        detail='Permiso concedido por el usuario.',
                        required_for=['consult_codex'],
                        granted=True,
                    )
                ],
                confidence=0.83,
            )

    orchestrator.context_assembler.world_model_service = FakeWorldModelService()

    preflight = orchestrator.preflight_external_assistant(
        user_goal='consulta con codex este incidente tecnico',
        assistant_kind='codex',
    )

    assert preflight['governance']['recommended_action'] != 'request_observation_permission'
    assert preflight['governance']['approval_required'] is False
    assert preflight['approval_checkpoints'] == []


def test_adaptive_orchestrator_approval_action_advances_session() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_approval'))
    _seed_wplay_teaching(episodes)
    _, _, session = orchestrator.handle_request(InferenceRequest(user_goal='abre Wplay e inicia sesion', auto_route=True, enable_planning=True, site_hint='wplay'))

    updated = orchestrator.approve_strategy(session.session_id)

    assert updated is not None
    assert any(item.decision.value == 'approved' for item in updated.approval_checkpoints)
    assert updated.status.value in {'waiting_approval', 'ready_to_execute'}


def test_adaptive_orchestrator_reports_missing_executor_for_ready_google_flow() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_google_missing_executor'))
    orchestrator.capability_service.capability_repository.save(
        CapabilityReadiness(
            capability_id='browser.search.google',
            title='Busqueda en Google',
            status=CapabilityStatus.READY,
            score=0.92,
            site_id='google',
            evidence=['snapshot operativo estable'],
            missing_signals=[],
            suggested_next_step='Continuar con la fase operativa.',
        )
    )

    _, result, session = orchestrator.handle_request(
        InferenceRequest(
            user_goal='busca en Google una pagina cualquiera',
            auto_route=True,
            enable_planning=True,
            site_hint='google',
        )
    )

    guidance = result.raw_output['assistant_guidance']
    assert guidance['mode'] == 'need_adapter'
    assert session.metadata['execution_state']['state'] == 'adapter_missing'
    assert session.metadata['execution_state']['executor_available'] is False

    updated = orchestrator.execute_now(session.session_id)

    assert updated is not None
    assert updated.status.value == 'ready_to_execute'
    assert updated.outcome is not None
    assert updated.outcome.metadata['mode'] == 'adapter_missing'
    assert updated.metadata['execution_state']['state'] == 'adapter_missing'


def test_control_center_ui_includes_adaptive_operating_panels() -> None:
    qml = (REPO_ROOT / 'src' / 'iabv_v15' / 'ui' / 'qml' / 'pages' / 'ControlCenterPage.qml').read_text(encoding='utf-8')
    assert 'Intento' in qml
    assert 'Contexto' in qml
    assert 'Estrategia' in qml
    assert 'Aprobaciones' in qml
    assert 'Ejecucion' in qml
    assert 'Evidencia' in qml
    assert 'Evolutivo' in qml
    assert 'Aprobar estrategia' in qml
    assert 'Aprobar fase siguiente' in qml
    assert 'Simular' in qml
    assert 'Ejecutar ahora' in qml


def test_adaptive_orchestrator_teaching_gap_keeps_teaching_action_even_with_incidents() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_wplay_mixed_guidance'))
    episode = episodes.create_episode('Wplay frame only', tags=['wplay'])
    episodes.save_step(
        episode.episode_id,
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='frame_fallback',
            target='frame:gettemporaryauthenticationtoken',
            metadata={
                'capture_channel': 'visible',
                'capture_source': 'frame_fallback',
                'frame_request_type': 'GetTemporaryAuthenticationToken',
                'field_role': 'token',
                'url': 'https://www.wplay.co/casino-en-vivo',
            },
        ),
    )
    for _ in range(3):
        orchestrator.context_assembler.hidden_incident_repository.save(
            HiddenIncident(
                site_id='wplay',
                incident_kind='bridge_lag',
                summary='Bridge atrasado durante captura de Wplay.',
            )
        )

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='abre Wplay e inicia sesion',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
        )
    )

    guidance = result.raw_output['assistant_guidance']
    actions = {item['action'] for item in guidance['actions']}
    assert guidance['mode'] == 'need_teaching'
    assert 'problema tecnico' in guidance['prompt']
    assert 'open_teaching_studio' in actions
    assert 'prepare_codex_packet' in actions


def test_adaptive_orchestrator_context_exposes_experiment_lab_recommendation() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_experiment_lab'))
    assert orchestrator.context_assembler.experiment_lab_repository is not None
    orchestrator.context_assembler.experiment_lab_repository.save_recommendation(
        ExperimentRecommendation(
            domain=ExperimentDomain.LANGUAGE,
            subject_key='general',
            recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            score=0.82,
            confidence=0.88,
            rationale='La comprension de lenguaje local resuelve mejor este tipo de consultas.',
        )
    )

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='analiza tecnicamente este flujo y propon la mejor estrategia',
            auto_route=True,
            enable_planning=True,
        )
    )

    context = result.raw_output['adaptive_session']['context']
    assert context['experiment_insights']
    assert context['experiment_insights'][0]['recommended_route'] == 'language_understanding'
    assert 'Laboratorio universal' in '\n'.join(context['evidence_summary'])
    assert 'Laboratorio sugiere language_understanding' in result.playbook['summary']

def test_adaptive_orchestrator_emits_decision_context_and_memory_snapshot() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_decision_context'))
    _seed_wplay_teaching(episodes)
    request = InferenceRequest(
        user_goal='abre Wplay e inicia sesion',
        auto_route=True,
        enable_planning=True,
        site_hint='wplay',
    )

    preview = orchestrator.build_decision_context_preview(request)
    _, result, session = orchestrator.handle_request(request)

    decision_context = result.raw_output['decision_context']
    perception_snapshot = result.raw_output['perception_snapshot']
    assert preview.metadata['decision_stage'] == 'pre_governance'
    assert decision_context['intent']['intent_key'] == 'wplay.login'
    assert decision_context['route_decision']['detected_role'] == TaskRole.TRAINING.value
    assert decision_context['governance']['recommended_action']
    assert decision_context['memory_snapshot']['evidence']['recent_teachings']
    assert decision_context['memory_snapshot']['learning']['capabilities']
    assert session.metadata['decision_context']['route_decision']['detected_role'] == TaskRole.TRAINING.value
    assert perception_snapshot['decision_context']['metadata']['decision_stage'] == 'post_governance'
    assert perception_snapshot['memory_snapshot']['evidence']['recent_teachings']
    assert session.metadata['perception_snapshot']['decision_context']['route_decision']['detected_role'] == TaskRole.TRAINING.value
    assert 'ia_trace_summary' in decision_context['metadata']
    assert decision_context['metadata']['comparison_scope_key']
    assert result.raw_output['ia_trace_summary']['comparison_scope_key'] == decision_context['metadata']['comparison_scope_key']


def test_adaptive_orchestrator_propagates_control_master_objective_id() -> None:
    """Opt-in Control Master link survives from request into session.

    Downstream closers (``TaskOutcomeRecorder`` → ``ControlMasterService``)
    read ``session.metadata["control_master_objective_id"]`` when a
    session hits a terminal status to auto-close the linked objective.
    For that loop to engage from a real user request, the orchestrator
    has to carry the request-level hint into the session metadata.
    Absent key must stay absent so legacy callers see no behaviour change.
    """

    orchestrator, _ = _orchestrator(_workspace('adaptive_cm_objective_propagation'))

    _, _, session_with = orchestrator.handle_request(
        InferenceRequest(
            user_goal='analiza este caso tecnico',
            auto_route=True,
            enable_planning=True,
            metadata={'control_master_objective_id': 'obj-super-sync-cli-export'},
        )
    )
    assert session_with.metadata.get('control_master_objective_id') == 'obj-super-sync-cli-export'

    _, _, session_without = orchestrator.handle_request(
        InferenceRequest(user_goal='analiza este caso tecnico', auto_route=True, enable_planning=True)
    )
    assert 'control_master_objective_id' not in session_without.metadata


def test_adaptive_orchestrator_governance_falls_back_local_on_session_expired() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_session_expired'))

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='analiza este caso tecnico',
            auto_route=True,
            enable_planning=True,
            metadata={'external_state_flags': ['session_expired']},
        )
    )

    decision_context = result.raw_output['decision_context']
    assert 'session_expired' in decision_context['metadata']['external_state_flags']
    assert decision_context['governance']['recommended_action'] == 'continue_local'
    assert decision_context['governance']['autonomy_level'] == 'guarded_local'


def test_adaptive_orchestrator_prefers_historical_assistant_when_history_is_clear() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_historical_assistant'))
    repository = orchestrator.context_assembler.experiment_lab_repository
    assert repository is not None
    repository.save_recommendation(
        ExperimentRecommendation(
            domain=ExperimentDomain.CODE,
            subject_key='wplay',
            recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            recommended_assistant_kind='claude',
            recommended_assistant_configuration=AssistantConfigurationSnapshot(
                reasoning_level='extended',
                assistant_mode='general',
                origin_mode='external',
            ),
            recommended_config_signature='hist-claude-cfg',
            score=0.91,
            confidence=0.87,
            rationale='Claude resolvio mejor este incidente tecnico repetido.',
            metadata={
                'winning_trace_ids': ['trace-win-1'],
                'comparison_scope_keys': ['wplay:bridge-lag'],
            },
        )
    )

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='revisa este problema de codigo en Wplay con el mismo bridge lag',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
            metadata={
                'site_id': 'wplay',
                'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
                'session_readiness': {'dominant_incident': 'bridge_lag'},
                'recent_incidents': [{'incident_kind': 'bridge_lag'}],
            },
        )
    )

    decision_context = result.raw_output['decision_context']
    assert decision_context['governance']['should_consult'] is True
    assert decision_context['governance']['assistant_kind'] == 'claude'
    assert decision_context['metadata']['preferred_assistant_kind'] == 'claude'
    assert decision_context['metadata']['preferred_config_signature'] == 'hist-claude-cfg'
    assert decision_context['metadata']['supporting_trace_ids'] == ['trace-win-1']


def test_adaptive_orchestrator_governance_marks_capture_unverified_for_retry() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_capture_unverified'))

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='necesito revisar una respuesta externa',
            auto_route=True,
            enable_planning=True,
            metadata={'external_state_flags': ['capture_unverified']},
        )
    )

    decision_context = result.raw_output['decision_context']
    assert 'capture_unverified' in decision_context['metadata']['external_state_flags']
    assert decision_context['governance']['recommended_action'] == 'audit_autonomy'
    assert decision_context['governance']['should_retry'] is True


def test_adaptive_orchestrator_finalize_failed_run_auto_replans_when_governance_allows() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_auto_replan'))

    _, _, session = orchestrator.handle_request(
        InferenceRequest(
            user_goal='resume tecnicamente una tabla hash',
            auto_route=True,
            enable_planning=True,
        )
    )

    session = session.model_copy(
        deep=True,
        update={
            'status': AdaptiveSessionStatus.READY_TO_EXECUTE,
            'approval_checkpoints': [],
            'capability_readiness': [],
        },
    )
    if session.playbook is not None:
        session.playbook = session.playbook.model_copy(
            update={
                'status': AdaptiveSessionStatus.READY_TO_EXECUTE,
                'simulation_only': False,
            }
        )
    session.metadata['execution_state'] = {
        'executor_name': 'local_test_executor',
        'executor_available': True,
        'simulation_only': False,
        'state': 'ready',
        'detail': 'Ejecutor local disponible para replanificacion.',
    }
    orchestrator.task_outcome_recorder.record(session)

    run_record = RunRecord(
        request=InferenceRequest(
            user_goal='resume tecnicamente una tabla hash',
            auto_route=True,
            enable_planning=True,
        ),
        result=InferenceResult(
            request_id='req-run-failed',
            provider_name='Ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='La corrida fallo por timeout controlado.',
            inferred_task='resume tecnicamente una tabla hash',
            confidence=0.31,
            detected_role=TaskRole.KNOWLEDGE,
            executor_model='fake-model',
        ),
        route=RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title='Knowledge',
            provider_name='Ollama',
            model_profile_id='general-qwen',
            model_name='qwen3:8b',
            reason='test finalize with run',
        ),
        status=RunStatus.FAILED,
        error_summary='timeout controlado',
    )

    replanned = orchestrator.finalize_with_run(session.session_id, run_record)

    assert replanned is not None
    assert replanned.session_id != session.session_id
    assert replanned.metadata['replanned_automatically'] is True
    assert replanned.metadata['replan_triggered_by_run_id'] == run_record.run_id
    original = orchestrator.get_session(session.session_id)
    assert original is not None
    assert original.metadata['auto_replanned'] is True
    assert original.metadata['auto_replanned_session_id'] == replanned.session_id


def test_adaptive_orchestrator_finalize_with_run_records_learning_and_reuses_it() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_learning_loop'))

    request = InferenceRequest(
        user_goal='revisa este problema de codigo en Wplay con el mismo bridge lag',
        auto_route=True,
        enable_planning=True,
        site_hint='wplay',
        metadata={
            'site_id': 'wplay',
            'live_audit': {'summary': 'Bridge lag persistente despues de la ensenanza.', 'decision_action': 'consult_codex'},
            'session_readiness': {'dominant_incident': 'bridge_lag'},
            'recent_incidents': [{'incident_kind': 'bridge_lag'}],
        },
    )

    _, _, session = orchestrator.handle_request(request)

    run_record = RunRecord(
        request=request,
        result=InferenceResult(
            request_id='req-learning-1',
            provider_name='Claude',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='Claude detecto la causa raiz del bridge lag y propuso una correccion estable.',
            inferred_task=request.user_goal,
            confidence=0.92,
            detected_role=TaskRole.KNOWLEDGE,
            executor_model='claude-sonnet',
        ),
        route=RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title='Knowledge',
            provider_name='Claude',
            model_profile_id='claude-profile',
            model_name='claude-sonnet',
            reason='test adaptive learning loop',
        ),
        status=RunStatus.SUCCESS,
    )

    saved = orchestrator.finalize_with_run(session.session_id, run_record)

    assert saved is not None
    assert saved.metadata['adaptive_learning']['records']
    repository = orchestrator.context_assembler.experiment_lab_repository
    assert repository is not None
    recommendations = repository.list_recommendations(domain=ExperimentDomain.CODE.value, subject_key='wplay', limit=3)
    assert recommendations
    assert any(item.recommended_assistant_kind == 'claude' for item in recommendations)

    _, result, _ = orchestrator.handle_request(request)

    decision_context = result.raw_output['decision_context']
    assert decision_context['metadata']['preferred_assistant_kind'] == 'claude'
    assert decision_context['metadata']['adaptive_learning_summary']['recommended_assistant_kind'] == 'claude'
    assert decision_context['metadata']['learned_patterns']



def test_autonomy_governance_policy_keeps_general_chat_local_even_with_technical_pressure() -> None:
    policy = AutonomyGovernancePolicy()

    snapshot = policy.evaluate(
        user_goal='hola que sabes hacer ?',
        session_status='failed',
        session_readiness={'dominant_incident': 'bridge_lag', 'live_audit_action': 'consult_codex'},
        live_audit={'summary': 'Incidente tecnico previo.', 'decision_action': 'consult_codex', 'confidence': 0.8},
        assistant_guidance={'mode': 'need_codex_fix', 'prompt': 'Incidente tecnico previo.'},
        capability_snapshot=[
            CapabilityReadiness(
                capability_id='wplay.login',
                title='Login Wplay',
                status=CapabilityStatus.INSUFFICIENT,
                suggested_next_step='Revisar bridge.',
            )
        ],
        approval_pending=False,
        intent_key='general.assistance',
        intent_disposition='answer_now',
    )

    assert snapshot['should_consult'] is False
    assert snapshot['recommended_action'] == 'continue_local'
    assert snapshot['autonomy_level'] == 'autonomous_local'


def test_adaptive_orchestrator_upgrades_real_wplay_login_when_visual_evidence_is_strong() -> None:
    orchestrator, episodes = _orchestrator(_workspace('adaptive_wplay_visual_ready'))
    episode = episodes.create_episode('Wplay login visual fuerte', tags=['wplay'])
    steps = [
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='frame_fallback',
            target='frame:loginandgettemptoken',
            screenshot_path='C:/tmp/wplay_login_frame.png',
            metadata={
                'capture_channel': 'visible',
                'capture_source': 'frame_fallback',
                'frame_request_type': 'LoginAndGetTempToken',
                'field_role': 'email',
                'selector': 'frame:loginandgettemptoken',
                'frame_url': 'https://login.example/#{"requestType":"LoginAndGetTempToken"}',
                'textPreview': 'Login detectado en frame embebido.',
            },
        ),
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='input',
            target='#login-username',
            metadata={
                'capture_channel': 'visible',
                'capture_source': 'frame_fallback_structured',
                'field_role': 'email_input',
                'selector': '#login-username',
            },
        ),
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='input',
            target='#login-password',
            metadata={
                'capture_channel': 'visible',
                'capture_source': 'frame_fallback_structured',
                'field_role': 'password_input',
                'selector': '#login-password',
            },
        ),
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='keydown',
            target='#login-password',
            metadata={
                'capture_channel': 'visible',
                'capture_source': 'frame_fallback_structured',
                'field_role': 'password_input',
                'selector': '#login-password',
                'key_display': 'Enter',
            },
        ),
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='submit',
            target='#login-form',
            screenshot_path='C:/tmp/wplay_submit_frame.png',
            metadata={
                'capture_channel': 'visible',
                'capture_source': 'frame_fallback_structured',
                'selector': '#login-form',
                'button_text': 'Iniciar sesion',
                'textPreview': 'loggedInPlayer balance',
            },
        ),
    ]
    for step in steps:
        episodes.save_step(episode.episode_id, step)
    artifacts = orchestrator.context_assembler.artifact_repository
    assert artifacts is not None
    artifacts.save(
        SessionArtifact(
            episode_id=episode.episode_id,
            kind='learning_bundle',
            path=f'{episode.episode_id}/summary/learning_bundle.json',
            metadata={'artifact_kind': 'learning_bundle', 'site_id': 'wplay'},
        ),
        payload={
            'login_learning': {'status': 'partial', 'login_visual_completeness': 0.0},
            'learning_readiness': {'status': 'partial', 'visual_alignment_score': 0.0, 'critical_object_coverage': 0.0},
            'visual_summary': {
                'green_count': 0,
                'orange_count': 5,
                'red_count': 0,
                'visual_alignment_score': 0.0,
                'critical_object_coverage': 0.0,
                'login_visual_completeness': 0.0,
            },
        },
    )

    _, result, _ = orchestrator.handle_request(
        InferenceRequest(
            user_goal='abre Wplay e inicia sesion',
            auto_route=True,
            enable_planning=True,
            site_hint='wplay',
        )
    )

    login_capability = next(item for item in result.capability_readiness if item['capability_id'] == 'wplay.login')
    restore_capability = next(item for item in result.capability_readiness if item['capability_id'] == 'wplay.session.restore')
    assert login_capability['status'] == 'ready_with_approval'
    assert restore_capability['status'] == 'ready_with_approval'
    assert result.raw_output['assistant_guidance']['mode'] != 'need_teaching'


def test_prepare_retry_marks_reingest_flag_for_session_expired_consultation() -> None:
    """Cuando la consulta expiro (hilo abierto con respuesta lista), el reintento
    debe pedir reingesta del DOM en vez de relanzar la pagina desde cero."""
    orchestrator, _ = _orchestrator(_workspace('retry_reingest_session_expired'))

    payload = {'metadata': {'pending_issue_id': 'issue-42'}}
    existing = {'task_id': 'task-abc', 'result_id': 'result-xyz'}

    new_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload=payload,
        existing_consultation=existing,
        retry_count=0,
        previous_status='session_expired',
    )

    retry_meta = new_payload['metadata']['consultation_retry']
    assert retry_meta['previous_status'] == 'session_expired'
    assert retry_meta['reingest_only'] is True
    assert new_payload['metadata']['reingest_existing_response'] is True
    # El reintento debe empezar desde 1, no reescribir el original.
    assert retry_meta['retry_count'] == 1
    # No debe arrastrar pending_issue_id viejo.
    assert 'pending_issue_id' not in new_payload['metadata']


def test_prepare_retry_skips_reingest_flag_for_failed_or_blocked_consultation() -> None:
    """En fallos o bloqueos el reintento debe hacer el flujo completo
    (relanzar + pegar prompt + submit), no solo releer el DOM."""
    orchestrator, _ = _orchestrator(_workspace('retry_reingest_failed'))

    payload = {'metadata': {}}
    existing = {'task_id': 'task-1', 'result_id': 'result-1'}

    failed_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload=payload,
        existing_consultation=existing,
        retry_count=1,
        previous_status='failed',
    )
    blocked_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload=payload,
        existing_consultation=existing,
        retry_count=0,
        previous_status='blocked',
    )

    for retry_payload in (failed_payload, blocked_payload):
        retry_meta = retry_payload['metadata']['consultation_retry']
        assert retry_meta['reingest_only'] is False
        assert retry_payload['metadata'].get('reingest_existing_response') is None


def test_prepare_retry_is_idempotent_and_does_not_mutate_input_payload() -> None:
    """El helper debe devolver un payload nuevo sin alterar el original."""
    orchestrator, _ = _orchestrator(_workspace('retry_reingest_idempotent'))

    original_metadata = {'autonomous_evolution': {'old': True}, 'pending_issue_id': 'x'}
    payload = {'metadata': dict(original_metadata)}

    new_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload=payload,
        existing_consultation={'task_id': 't', 'result_id': 'r'},
        retry_count=0,
        previous_status='session_expired',
    )

    # El payload original no se toca.
    assert payload['metadata'] == original_metadata
    # El nuevo payload si limpia flags anteriores.
    assert 'autonomous_evolution' not in new_payload['metadata']
    assert 'pending_issue_id' not in new_payload['metadata']
    assert new_payload['metadata']['reingest_existing_response'] is True


# ---------------------------------------------------------------------------
# PR-B — Pre-captura forzada en _prepare_retry_for_expired_consultation
# ---------------------------------------------------------------------------
# Cuando la consulta expiro y la sesion aislada aun tiene una respuesta
# visible, ``_prepare_retry_for_expired_consultation`` debe intentar una
# captura inmediata (dom_capture / clipboard_capture) ANTES de relanzar el
# pipeline completo de ``plan_or_execute``.


class _StubEvolutionServiceForReingest:
    """Stub minimo de AutonomousEvolutionService para tests de pre-captura."""

    def __init__(self, *, captured_text: str = '', should_fail: bool = False) -> None:
        self.captured_text = captured_text
        self.should_fail = should_fail
        self.reingest_calls: list[dict] = []
        self.ingest_calls: list[dict] = []

    def reingest_existing_session(
        self, *, existing_consultation, adaptive_payload, user_goal, source,
    ):
        self.reingest_calls.append({
            'existing_consultation': existing_consultation,
            'user_goal': user_goal,
            'source': source,
        })
        if self.should_fail:
            raise RuntimeError('capture_failed')
        if not self.captured_text:
            return {'pre_capture_ingested': False, 'reason': 'no_response_text'}
        return {
            'pre_capture_ingested': True,
            'detail': self.captured_text,
            'outcome_summary': f'Respuesta capturada: {self.captured_text[:80]}',
            'status': 'ingested',
            'pre_capture_task_id': 'task-pre',
            'pre_capture_result_id': 'result-pre',
            'pre_capture_source': 'browser_dom_reingest',
        }

    def ingest_consult_response(self, *, adaptive_payload, user_goal, response_text, source):
        self.ingest_calls.append({
            'user_goal': user_goal,
            'response_text': response_text,
            'source': source,
        })
        return {
            'status': 'ingested',
            'detail': response_text,
            'assistant_kind': 'chatgpt',
            'pending_issue_id': 'issue-reingest',
        }


def test_prepare_retry_forces_pre_capture_for_session_expired() -> None:
    """Cuando previous_status es session_expired y se pasa user_goal, el
    metodo debe llamar a reingest_existing_session y, si captura texto,
    marcar capture_completed_before_retry=True."""
    orchestrator, _ = _orchestrator(_workspace('retry_pre_capture_ok'))
    stub = _StubEvolutionServiceForReingest(captured_text='Respuesta del DOM abierto.')
    orchestrator.autonomous_evolution_service = stub

    existing = {
        'task_id': 'task-old', 'result_id': 'result-old',
        'selected_tool_id': 'chatgpt_web_assisted',
        'assistant_kind': 'chatgpt',
        'response_capture_mode': 'dom_capture',
    }
    payload = {'metadata': {'pending_issue_id': 'issue-42'}}

    new_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload=payload,
        existing_consultation=existing,
        retry_count=0,
        previous_status='session_expired',
        user_goal='resolver error en login',
        source='test',
    )

    assert len(stub.reingest_calls) == 1
    assert stub.reingest_calls[0]['user_goal'] == 'resolver error en login'
    assert new_payload['metadata']['capture_completed_before_retry'] is True
    pre_result = new_payload['metadata'].get('pre_capture_result') or {}
    assert pre_result.get('pre_capture_ingested') is True
    assert pre_result.get('detail') == 'Respuesta del DOM abierto.'
    assert new_payload['metadata']['reingest_existing_response'] is True


def test_prepare_retry_falls_through_when_pre_capture_returns_nothing() -> None:
    """Si reingest_existing_session no obtiene texto, no se marca
    capture_completed_before_retry y el flujo normal de plan_or_execute sigue."""
    orchestrator, _ = _orchestrator(_workspace('retry_pre_capture_empty'))
    stub = _StubEvolutionServiceForReingest(captured_text='')
    orchestrator.autonomous_evolution_service = stub

    existing = {
        'task_id': 'task-1', 'result_id': 'result-1',
        'selected_tool_id': 'chatgpt_web_assisted',
        'assistant_kind': 'chatgpt',
    }

    new_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload={'metadata': {}},
        existing_consultation=existing,
        retry_count=0,
        previous_status='session_expired',
        user_goal='diagnosticar lentitud',
        source='test',
    )

    assert len(stub.reingest_calls) == 1
    assert new_payload['metadata'].get('capture_completed_before_retry') is not True
    assert new_payload['metadata']['reingest_existing_response'] is True


def test_prepare_retry_survives_pre_capture_exception() -> None:
    """Si reingest_existing_session lanza excepcion, el metodo no debe
    propagarla: simplemente omite la pre-captura y sigue con el retry normal."""
    orchestrator, _ = _orchestrator(_workspace('retry_pre_capture_exc'))
    stub = _StubEvolutionServiceForReingest(should_fail=True)
    orchestrator.autonomous_evolution_service = stub

    existing = {
        'task_id': 'task-x', 'result_id': 'result-x',
        'selected_tool_id': 'chatgpt_web_assisted',
        'assistant_kind': 'chatgpt',
    }

    new_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload={'metadata': {}},
        existing_consultation=existing,
        retry_count=1,
        previous_status='session_expired',
        user_goal='fix crash',
        source='test',
    )

    assert len(stub.reingest_calls) == 1
    assert new_payload['metadata'].get('capture_completed_before_retry') is not True
    assert new_payload['metadata']['reingest_existing_response'] is True


def test_prepare_retry_no_pre_capture_for_failed_or_blocked() -> None:
    """Para failed/blocked, NO se debe intentar pre-captura: el flujo debe
    ser el completo (launch + paste + submit)."""
    orchestrator, _ = _orchestrator(_workspace('retry_no_pre_capture'))
    stub = _StubEvolutionServiceForReingest(captured_text='Should not be called')
    orchestrator.autonomous_evolution_service = stub

    existing = {
        'task_id': 'task-f', 'result_id': 'result-f',
        'selected_tool_id': 'chatgpt_web_assisted',
        'assistant_kind': 'chatgpt',
    }

    for status in ('failed', 'blocked'):
        new_payload = orchestrator._prepare_retry_for_expired_consultation(
            payload={'metadata': {}},
            existing_consultation=existing,
            retry_count=0,
            previous_status=status,
            user_goal='fix something',
            source='test',
        )
        assert new_payload['metadata'].get('capture_completed_before_retry') is not True
        assert new_payload['metadata'].get('reingest_existing_response') is None

    assert len(stub.reingest_calls) == 0


def test_prepare_retry_no_pre_capture_without_user_goal() -> None:
    """Sin user_goal (llamada legacy sin keyword args), la pre-captura no
    se intenta y el comportamiento es identico al original."""
    orchestrator, _ = _orchestrator(_workspace('retry_no_goal'))
    stub = _StubEvolutionServiceForReingest(captured_text='ignored')
    orchestrator.autonomous_evolution_service = stub

    new_payload = orchestrator._prepare_retry_for_expired_consultation(
        payload={'metadata': {}},
        existing_consultation={'task_id': 't', 'result_id': 'r'},
        retry_count=0,
        previous_status='session_expired',
    )

    assert len(stub.reingest_calls) == 0
    assert new_payload['metadata'].get('capture_completed_before_retry') is not True
    assert new_payload['metadata']['reingest_existing_response'] is True


# ---------------------------------------------------------------------------
# H6 — SynapticRouter integration in AdaptiveTaskOrchestrator
# ---------------------------------------------------------------------------
# Los tests siguientes verifican que el ranking inter-IA del ``SynapticRouter``
# (PCS v1) sea visible en ``DecisionContext.metadata.synaptic_route`` cuando el
# intent es external-worthy, y que NO se inyecte en flujos local-first. La ruta
# operativa sigue siendo de ``LocalRoleRouter`` — la inyección es puramente
# descriptiva.


from iabv_v15.domain.models import SynapticRoutingDecision, TaskIntent
from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
    _synaptic_task_kind_from_intent,
)


class _StubSynapticRouter:
    """Router sintético que registra las task_kinds consultadas."""

    def __init__(self, *, routing_enabled: bool = True, selected_kind: str = 'codex') -> None:
        self.routing_enabled = routing_enabled
        self.selected_kind = selected_kind
        self.calls: list[str] = []

    def decide(self, *, task_kind: str, candidate_assistant_kinds: list[str] | None = None) -> SynapticRoutingDecision:
        self.calls.append(task_kind)
        return SynapticRoutingDecision(
            selected_assistant_kind=self.selected_kind if self.routing_enabled else '',
            alternatives=[{'assistant_kind': 'devin', 'score': 0.42}],
            fit_score=0.6 if self.routing_enabled else 0.0,
            weight_score=0.1,
            availability_score=0.3,
            total_score=0.55 if self.routing_enabled else 0.0,
            routing_enabled=self.routing_enabled,
            reason='stub' if self.routing_enabled else 'SYNAPTIC_ROUTING feature flag off',
            unresolved_fields=['adaptive_history_empty'],
            metadata={'task_kind': task_kind},
        )


def test_synaptic_task_kind_mapping_for_code_generation_intent() -> None:
    intent = TaskIntent(
        intent_key='project.evolution',
        detected_role=TaskRole.PROJECT_EVOLUTION,
        metadata={'code_generation_prompt': True},
    )
    assert _synaptic_task_kind_from_intent(intent) == 'code_generation'


def test_synaptic_task_kind_mapping_defaults_project_to_code_review() -> None:
    intent = TaskIntent(
        intent_key='project.evolution',
        detected_role=TaskRole.PROJECT_EVOLUTION,
        metadata={},
    )
    assert _synaptic_task_kind_from_intent(intent) == 'code_review'


def test_synaptic_task_kind_mapping_for_external_research() -> None:
    intent = TaskIntent(
        intent_key='research.external_consultation',
        detected_role=TaskRole.RESEARCH,
    )
    assert _synaptic_task_kind_from_intent(intent) == 'long_context_synthesis'


def test_synaptic_task_kind_mapping_is_empty_for_local_chat() -> None:
    # general.assistance y knowledge.query son local-first: el router NO se
    # consulta y el orquestador debe saltar la inyección.
    for intent_key, role in (
        ('general.assistance', TaskRole.KNOWLEDGE),
        ('knowledge.query', TaskRole.KNOWLEDGE),
    ):
        intent = TaskIntent(intent_key=intent_key, detected_role=role)
        assert _synaptic_task_kind_from_intent(intent) == ''


def test_synaptic_task_kind_mapping_for_browser_search() -> None:
    intent = TaskIntent(
        intent_key='browser.search',
        detected_role=TaskRole.KNOWLEDGE,
    )
    assert _synaptic_task_kind_from_intent(intent) == 'retrieval_augmented'


def test_synaptic_task_kind_mapping_for_browser_navigate() -> None:
    intent = TaskIntent(
        intent_key='browser.navigate',
        detected_role=TaskRole.KNOWLEDGE,
    )
    assert _synaptic_task_kind_from_intent(intent) == 'web_browsing'


def test_orchestrator_injects_synaptic_route_for_code_generation_goal() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_h6_code_gen'))
    stub = _StubSynapticRouter(routing_enabled=True, selected_kind='codex')
    orchestrator.synaptic_router = stub

    request = InferenceRequest(
        user_goal='genera un parche pequeño con tests unitarios para el router',
        auto_route=True,
    )
    decision = orchestrator.build_decision_context_preview(request)

    assert stub.calls, 'SynapticRouter debió ser consultado para un goal de código'
    assert stub.calls[0] == 'code_generation'
    assert 'synaptic_route' in decision.metadata
    payload = decision.metadata['synaptic_route']
    assert payload['routing_enabled'] is True
    assert payload['selected_assistant_kind'] == 'codex'
    assert payload['metadata']['task_kind'] == 'code_generation'
    # La ruta operativa interna NO la reemplaza el router sináptico.
    assert decision.route_decision.detected_role == TaskRole.PROJECT_EVOLUTION


def test_orchestrator_skips_synaptic_route_for_conversational_goal() -> None:
    orchestrator, _ = _orchestrator(_workspace('adaptive_h6_conversational'))
    stub = _StubSynapticRouter()
    orchestrator.synaptic_router = stub

    request = InferenceRequest(user_goal='hola, como estas?', auto_route=True)
    decision = orchestrator.build_decision_context_preview(request)

    assert stub.calls == [], 'No debe consultarse SynapticRouter en flujos local-first'
    assert 'synaptic_route' not in decision.metadata


def test_orchestrator_without_synaptic_router_keeps_metadata_clean() -> None:
    # Backward compat: cuando ``synaptic_router=None`` (bootstrap legacy o
    # sandbox sin PCS v1), ``DecisionContext.metadata`` no debe contener la
    # clave ``synaptic_route``.
    orchestrator, _ = _orchestrator(_workspace('adaptive_h6_no_router'))
    assert orchestrator.synaptic_router is None

    request = InferenceRequest(
        user_goal='genera un parche pequeño con tests unitarios',
        auto_route=True,
    )
    decision = orchestrator.build_decision_context_preview(request)

    assert 'synaptic_route' not in decision.metadata


def test_orchestrator_propagates_routing_disabled_flag() -> None:
    # Cuando SYNAPTIC_ROUTING=off, el router devuelve ``routing_enabled=False``
    # y el orquestador debe inyectar igual el payload observable (fail-observable)
    # para que UI/MCP vean el motivo.
    orchestrator, _ = _orchestrator(_workspace('adaptive_h6_flag_off'))
    stub = _StubSynapticRouter(routing_enabled=False)
    orchestrator.synaptic_router = stub

    request = InferenceRequest(
        user_goal='genera un parche con tests',
        auto_route=True,
    )
    decision = orchestrator.build_decision_context_preview(request)

    assert stub.calls == ['code_generation']
    payload = decision.metadata.get('synaptic_route')
    assert payload is not None
    assert payload['routing_enabled'] is False
    assert 'feature flag off' in payload['reason'].lower()
