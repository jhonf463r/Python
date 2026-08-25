from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    CapturedStep,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    InferenceRequest,
    KnowledgeItem,
    NetworkStatusSnapshot,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
    RuntimeSignal,
    SessionArtifact,
    SessionHealthSnapshot,
    TaskIntent,
    TaskRole,
    ToolLiveStatus,
    WindowObservation,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_task_context_assembler_recovers_knowledge_from_persistent_goal_context() -> None:
    root = _workspace('task_context_goal_knowledge')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        knowledge_repository = KnowledgeRepository(db)
        objective_repository = ObjectiveRepository(db, evolution_storage)
        knowledge_repository.upsert(
            KnowledgeItem(
                title='Wplay login estable',
                summary='Mejorar login Wplay con replay estable y submit consistente.',
                tags=['wplay', 'login'],
                confidence=0.84,
            )
        )
        objective = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Mejorar login Wplay',
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.41,
            )
        )
        project = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.PROJECT,
                title='Login Wplay persistente',
                parent_id=objective.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.46,
            )
        )
        task = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.TASK,
                title='Abrir Wplay e iniciar sesion',
                parent_id=project.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.BLOCKED,
                progress=0.58,
                blocker='Bridge lag persistente',
            )
        )

        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=knowledge_repository,
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            objective_repository=objective_repository,
        )
        request = InferenceRequest(
            user_goal='necesito ayuda con este flujo',
            site_hint='wplay',
            goal_parameters={
                'objective_id': objective.objective_id,
                'project_id': project.objective_id,
                'task_id': task.objective_id,
            },
        )
        intent = TaskIntent(
            intent_key='wplay.login',
            title='Abrir Wplay e iniciar sesion',
            detected_role=TaskRole.TRAINING,
            site_hint='wplay',
            summary='Resolver el login de Wplay.',
        )

        context = assembler.build(request, intent)

        assert context.goal_context.objective['objective_id'] == objective.objective_id
        assert context.goal_context.task['objective_id'] == task.objective_id
        assert context.knowledge_hits
        assert context.knowledge_hits[0]['title'] == 'Wplay login estable'
    finally:
        shutil.rmtree(root, ignore_errors=True)

def test_task_context_assembler_prioritizes_goal_scoped_experiment_insights() -> None:
    root = _workspace('task_context_goal_experiments')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        objective_repository = ObjectiveRepository(db, evolution_storage)
        experiment_lab_repository = ExperimentLabRepository(db, evolution_storage)

        objective = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Mejorar login Wplay',
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.4,
            )
        )
        project = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.PROJECT,
                title='Login Wplay persistente',
                parent_id=objective.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.5,
            )
        )
        task = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.TASK,
                title='Abrir Wplay e iniciar sesion',
                parent_id=project.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.6,
            )
        )
        experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.LANGUAGE,
                subject_key='general',
                recommended_route=EvaluationRoute.UI,
                score=0.55,
                confidence=0.5,
                rationale='Fallback general sin foco de objetivo.',
            )
        )
        experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.LANGUAGE,
                subject_key=task.objective_id,
                recommended_route=EvaluationRoute.CODE_AGENT,
                score=0.93,
                confidence=0.89,
                rationale='El objetivo activo ya favorece una correccion de codigo guiada.',
            )
        )

        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            objective_repository=objective_repository,
            experiment_lab_repository=experiment_lab_repository,
        )
        request = InferenceRequest(
            user_goal='necesito decidir la mejor via para este objetivo',
            site_hint='wplay',
            goal_parameters={
                'objective_id': objective.objective_id,
                'project_id': project.objective_id,
                'task_id': task.objective_id,
            },
        )
        intent = TaskIntent(
            intent_key='wplay.login',
            title='Abrir Wplay e iniciar sesion',
            detected_role=TaskRole.TRAINING,
            site_hint='wplay',
            summary='Resolver el login de Wplay.',
        )

        context = assembler.build(request, intent)

        assert context.experiment_insights
        assert context.experiment_insights[0]['subject_key'] == task.objective_id
        assert 'objetivo activo' in context.experiment_insights[0]['rationale']
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_task_context_assembler_keeps_general_chat_transient_even_with_active_objectives() -> None:
    root = _workspace('task_context_general_chat_transient')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        objective_repository = ObjectiveRepository(db, evolution_storage)

        objective = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Mejorar login Wplay',
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.7,
            )
        )
        project = objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.PROJECT,
                title='Login Wplay persistente',
                parent_id=objective.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.72,
            )
        )
        objective_repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.TASK,
                title='Abrir Wplay e iniciar sesion',
                parent_id=project.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.BLOCKED,
                progress=0.63,
                blocker='Bridge lag persistente',
            )
        )

        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            objective_repository=objective_repository,
        )
        request = InferenceRequest(user_goal='hola que sabes hacer ?')
        intent = TaskIntent(
            intent_key='general.assistance',
            title='Asistencia general del centro de control',
            detected_role=TaskRole.KNOWLEDGE,
            summary='Responder de forma util y corta sobre capacidades operativas del sistema.',
        )

        context = assembler.build(request, intent)

        assert context.goal_context.objective == {}
        assert context.goal_context.project == {}
        assert context.goal_context.task == {}
        assert context.goal_context.metadata['source'] == 'transient_chat_goal'
        assert context.goal_context.metadata['persistent'] is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_recovers_strong_visual_login_from_stale_bundle() -> None:
    root = _workspace('task_context_stale_visual_bundle')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        artifact_storage = ArtifactStorage(str(root / 'artifacts'))
        episodes = EpisodeRepository(str(root / 'episodes'), db)
        artifacts = SessionArtifactRepository(db, artifact_storage)
        episode = episodes.create_episode('Wplay login fuerte', tags=['wplay'])
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
                    'textPreview': 'correo o usuario',
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
                    'textPreview': 'contrasena',
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

        assembler = TaskContextAssembler(
            episode_repository=episodes,
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            artifact_repository=artifacts,
        )
        request = InferenceRequest(user_goal='abre Wplay e inicia sesion', site_hint='wplay')
        intent = TaskIntent(
            intent_key='wplay.login',
            title='Abrir Wplay e iniciar sesion',
            detected_role=TaskRole.TRAINING,
            site_hint='wplay',
            summary='Resolver el login de Wplay.',
        )

        context = assembler.build(request, intent)

        assert context.recent_teachings
        lead = context.recent_teachings[0]
        assert lead['login_status'] == 'ready'
        assert lead['learning_status'] == 'ready'
        assert lead['green_count'] >= 4
        assert lead['critical_object_coverage'] >= 0.8
        assert lead['login_visual_completeness'] >= 0.8
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_prioritizes_comparison_scope_over_general_recommendation() -> None:
    root = _workspace('task_context_comparison_scope_insights')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        experiment_lab_repository = ExperimentLabRepository(db, evolution_storage)

        experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='general',
                recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                recommended_assistant_kind='chatgpt',
                score=0.58,
                confidence=0.51,
                rationale='Fallback general.',
            )
        )
        experiment_lab_repository.save_recommendation(
                ExperimentRecommendation(
                    domain=ExperimentDomain.CODE,
                    subject_key='wplay:revisa-bridge-lag-tecnico-de-codigo',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                recommended_config_signature='scope-codex-cfg',
                score=0.91,
                confidence=0.88,
                rationale='El comparison scope de bridge lag ya favorece codex.',
                metadata={'adaptive_learning_summary': {'reasons': ['historial de exito 100%']}},
            )
        )

        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            experiment_lab_repository=experiment_lab_repository,
        )
        request = InferenceRequest(
            user_goal='revisa bridge lag tecnico de codigo',
            site_hint='wplay',
        )
        intent = TaskIntent(
            intent_key='project.evolution',
            title='Revision tecnica',
            detected_role=TaskRole.PROJECT_EVOLUTION,
            site_hint='wplay',
            summary='Revisar incidente repetido.',
        )

        context = assembler.build(request, intent)

        assert context.experiment_insights
        assert context.experiment_insights[0]['subject_key'] == 'wplay:revisa-bridge-lag-tecnico-de-codigo'
        assert context.metadata['adaptive_learning_summary']['recommended_assistant_kind'] == 'codex'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_includes_world_model_and_summary() -> None:
    root = _workspace('task_context_world_model')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))

        class FakeEnvironmentService:
            def current_model(self) -> EnvironmentSelfModel:
                return EnvironmentSelfModel(environment_id='env-demo', scan_status='ready')

            def request_refresh(self, **kwargs):
                return None

        class FakeWorldModelService:
            def current_model(self) -> WorldModelSnapshot:
                return WorldModelSnapshot(
                    active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=12, focused=True)],
                    focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=12, focused=True),
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
                    network_status=NetworkStatusSnapshot(connected=True, status='conectado', quality='buena'),
                    detected_blocks=['wrong_thread'],
                    confidence=0.81,
                )

            def request_refresh(self, **kwargs):
                return None

        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            environment_self_awareness_service=FakeEnvironmentService(),
            world_model_service=FakeWorldModelService(),
        )
        request = InferenceRequest(user_goal='que esta pasando con codex?', site_hint='wplay')
        intent = TaskIntent(
            intent_key='general.assistance',
            title='Consulta operativa',
            detected_role=TaskRole.KNOWLEDGE,
            site_hint='wplay',
            summary='Pregunta operativa.',
        )

        snapshot = assembler.build_perception_snapshot(request, intent)

        assert snapshot.world_model.focused_window is not None
        assert snapshot.world_model.focused_window.title == 'Codex - IABV'
        assert snapshot.metadata['world_model_summary']['network_status'] == 'conectado'
        assert snapshot.metadata['world_model_summary']['codex_status']['thread_status'] == 'otro_hilo_activo'
        assert snapshot.decision_context.metadata['world_model_summary']['detected_blocks'] == ['wrong_thread']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_includes_portable_context_summary() -> None:
    root = _workspace('task_context_portable_context')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))

        class FakePortableContextService:
            def current_package(self, **kwargs):
                return {'package_id': 'portable-1', 'kwargs': kwargs}

            def package_summary(self, package):
                return {
                    'package_id': 'portable-1',
                    'summary': 'Contexto portable listo.',
                    'markdown_path': str(root / 'evolution' / 'portable_context' / 'latest.md'),
                    'package_path': str(root / 'evolution' / 'portable_context' / 'latest.json'),
                    'self_examination_summary': {'status': 'watch', 'summary': 'Hay un patron repetido que vigilar.'},
                }

        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            portable_context_service=FakePortableContextService(),
        )
        request = InferenceRequest(user_goal='retoma el estado del proyecto', site_hint='iabv')
        intent = TaskIntent(
            intent_key='general.assistance',
            title='Retomar proyecto',
            detected_role=TaskRole.KNOWLEDGE,
            site_hint='iabv',
            summary='Contexto portable.',
        )

        context = assembler.build(request, intent)
        snapshot = assembler.build_perception_snapshot(request, intent)

        assert context.metadata['portable_context_summary']['package_id'] == 'portable-1'
        assert snapshot.metadata['portable_context_summary']['package_id'] == 'portable-1'
        assert snapshot.decision_context.metadata['portable_context_summary']['summary'] == 'Contexto portable listo.'
        assert snapshot.metadata['portable_context_summary']['self_examination_summary']['status'] == 'watch'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_includes_environment_self_model_in_perception_snapshot() -> None:
    root = _workspace('task_context_environment_self_model')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))

        class FakeEnvironmentService:
            def __init__(self) -> None:
                self.refresh_requested = False

            def current_model(self) -> EnvironmentSelfModel:
                return EnvironmentSelfModel(
                    environment_id='cyborg15-demo',
                    known_environment=True,
                    scan_status='ready',
                    notifications=['Entorno listo.'],
                    runtime_profile={'python_executable': 'python'},
                )

            def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> EnvironmentSelfModel:
                self.refresh_requested = True
                return self.current_model()

        env_service = FakeEnvironmentService()
        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            environment_self_awareness_service=env_service,
        )
        request = InferenceRequest(user_goal='abre wplay e inicia sesion', site_hint='wplay')
        intent = TaskIntent(
            intent_key='wplay.login',
            title='Abrir Wplay e iniciar sesion',
            detected_role=TaskRole.TRAINING,
            site_hint='wplay',
            summary='Resolver el login de Wplay.',
        )

        perception = assembler.build_perception_snapshot(request, intent)

        assert perception.environment_self_model.environment_id == 'cyborg15-demo'
        assert perception.metadata['environment_id'] == 'cyborg15-demo'
        assert 'UNRESOLVED:environment_self_model' not in perception.unresolved_fields
        assert env_service.refresh_requested is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_builds_perception_snapshot_with_runtime_and_unresolved_channels() -> None:
    root = _workspace('task_context_perception_snapshot')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
        )
        request = InferenceRequest(
            user_goal='hola que sabes hacer ?',
            metadata={
                'runtime_signals': [
                    RuntimeSignal(signal_kind='bridge_lag', summary='Bridge atrasado en captura visible.').model_dump(mode='json')
                ],
                'session_health': SessionHealthSnapshot(
                    site_id='general',
                    health_label='Sesion estable',
                    status='active',
                ).model_dump(mode='json'),
            },
        )
        intent = TaskIntent(
            intent_key='general.assistance',
            title='Asistencia general',
            detected_role=TaskRole.KNOWLEDGE,
            summary='Responder sobre el sistema.',
            metadata={'conversational_prompt': True},
        )

        perception = assembler.build_perception_snapshot(request, intent)

        assert perception.decision_context.intent.intent_key == 'general.assistance'
        assert perception.decision_context.metadata['decision_stage'] == 'pre_governance'
        assert perception.memory_snapshot['evidence']['site_display_name'] == 'General'
        assert perception.runtime_signals[0].signal_kind == 'bridge_lag'
        assert perception.session_health is not None
        assert 'UNRESOLVED:ia_trace' in perception.unresolved_fields
        assert 'UNRESOLVED:visual_signal' in perception.unresolved_fields
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_normalizes_visual_signal_and_ia_trace() -> None:
    root = _workspace('task_context_visual_signal_trace')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
        )
        request = InferenceRequest(
            user_goal='necesito validar una consulta externa',
            metadata={
                'visual_signal': {
                    'source': 'capture_studio',
                    'source_app': 'codex',
                    'capture_available': True,
                    'dom_available': True,
                    'latest_url': 'https://example.com/chat',
                    'latest_title': 'Codex chat',
                    'visible_targets': ['chat input', 'send'],
                    'learning_ready': True,
                    'cross_check_status': 'aligned',
                    'visual_evidence_refs': ['episode:visual-1'],
                    'visual_snapshot': {'status': 'available', 'screen_capture': 'available'},
                    'dom_summary': {'status': 'available', 'node_count': 14},
                    'available_actions': [{'action': 'interact_visible_target', 'label': 'chat input', 'target': 'chat input', 'available': True}],
                    'detected_blocks': ['wrong_thread'],
                    'confidence': 0.82,
                },
                'ia_trace': [
                    {
                        'trace_id': 'trace-1',
                        'assistant_kind': 'codex',
                        'assistant_configuration': {'planning_mode': 'with_plan'},
                        'config_signature': 'cfg-1',
                        'comparison_scope_key': 'incident-bridge-1',
                        'source_trace_ids': ['trace-seed-0'],
                        'proposal_summary': 'Contrastar el incidente del bridge visible.',
                        'outcome_summary': 'Respuesta pendiente de captura.',
                        'route': 'code_agent',
                        'result_label': 'awaiting_response',
                        'success': False,
                        'execution_ms': 1200,
                        'confidence': 0.64,
                        'evidence_refs': ['task:external-1'],
                        'reused_later': False,
                        'verdict': 'awaiting_response',
                        'external_state_flags': ['wrong_thread'],
                    }
                ],
                'external_state_flags': ['capture_unverified'],
            },
        )
        intent = TaskIntent(
            intent_key='general.assistance',
            title='Asistencia general',
            detected_role=TaskRole.KNOWLEDGE,
            summary='Responder sobre el sistema.',
            metadata={'conversational_prompt': False},
        )

        perception = assembler.build_perception_snapshot(request, intent)

        assert perception.visual_signal.capture_available is True
        assert perception.visual_signal.source_app == 'codex'
        assert perception.visual_signal.latest_title == 'Codex chat'
        assert perception.visual_signal.available_actions[0]['action'] == 'interact_visible_target'
        assert perception.visual_signal.detected_blocks == ['wrong_thread']
        assert perception.ia_trace[0].trace_id == 'trace-1'
        assert perception.ia_trace[0].assistant_configuration.planning_mode == 'with_plan'
        assert perception.ia_trace[0].comparison_scope_key == 'incident-bridge-1'
        assert perception.ia_trace[0].source_trace_ids == ['trace-seed-0']
        assert 'wrong_thread' in perception.external_state_flags
        assert 'capture_unverified' in perception.external_state_flags
        assert 'UNRESOLVED:visual_signal' not in perception.unresolved_fields
        assert 'UNRESOLVED:ia_trace' not in perception.unresolved_fields
        assert perception.metadata['ia_trace_summary']['comparison_scope_key'] == 'incident-bridge-1'
        assert perception.metadata['ia_trace_summary']['tested_assistants'] == ['codex']
        assert perception.decision_context.metadata['ia_trace_summary']['latest_trace_ids'] == ['trace-1']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_recovers_guided_self_improvement_trace_without_polluting_assistant_preference() -> None:
    root = _workspace('task_context_guided_self_improvement_trace')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        tool_storage = ArtifactStorage(str(root / 'tool_teaching'))
        tool_record_repository = ToolRecordRepository(db, tool_storage)
        tool_record_repository.log_execution(
            tool_id='self_teach_orchestrator',
            task_id='run-guided-1',
            action_type='guided_self_improvement',
            state='needs_user',
            payload={
                'ia_trace_entry': {
                    'trace_id': 'guided-trace-1',
                    'assistant_kind': 'self_teach',
                    'requested_assistant_kind': 'self_teach',
                    'actual_assistant_kind': 'self_teach',
                    'comparison_scope_key': 'guided_improvement:wplay:wplay.login',
                    'route': 'guided_self_improvement',
                    'proposal_summary': 'Registrar el bloqueo y no repetir el mismo error.',
                    'outcome_summary': 'El sistema detecto route_stuck y dejo aprendizaje reutilizable.',
                    'result_label': 'needs_user',
                    'success': False,
                    'metadata': {'trace_role': 'guided_improvement', 'site_id': 'wplay'},
                }
            },
            created_at_utc='2026-04-13T12:00:00+00:00',
        )
        assembler = TaskContextAssembler(
            episode_repository=EpisodeRepository(str(root / 'episodes'), db),
            knowledge_repository=KnowledgeRepository(db),
            run_repository=RunRepository(db),
            dossier_repository=ExecutionDossierRepository(db, evolution_storage),
            hidden_incident_repository=HiddenIncidentRepository(db, evolution_storage),
            site_policy_registry=SitePolicyRegistry(str(root / 'site_policies')),
            capability_repository=CapabilityRepository(db, evolution_storage),
            adaptive_session_repository=AdaptiveSessionRepository(db, evolution_storage),
            tool_record_repository=tool_record_repository,
        )
        request = InferenceRequest(user_goal='abre Wplay e inicia sesion', site_hint='wplay')
        intent = TaskIntent(
            intent_key='wplay.login',
            title='Abrir Wplay e iniciar sesion',
            detected_role=TaskRole.TRAINING,
            site_hint='wplay',
            summary='Resolver el login de Wplay.',
        )

        perception = assembler.build_perception_snapshot(request, intent)

        assert perception.ia_trace[0].trace_id == 'guided-trace-1'
        assert perception.metadata['ia_trace_summary']['latest_trace_ids'] == ['guided-trace-1']
        assert perception.metadata['ia_trace_summary']['tested_assistants'] == []
        assert perception.metadata['ia_trace_summary']['best_assistant_kind'] == ''
    finally:
        shutil.rmtree(root, ignore_errors=True)
