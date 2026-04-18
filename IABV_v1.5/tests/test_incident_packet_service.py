from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    ApprovalDecision,
    DossierScope,
    ExecutionDossier,
    ExecutionState,
    HiddenIncident,
    ImprovementProposal,
    InteractionAction,
    InteractionChannel,
    InteractionEpisode,
    InteractionPattern,
    InteractionPolicyDecision,
    InteractionResult,
    IncidentQuery,
    IncidentStatus,
    IssueCandidate,
    IssueSeverity,
    RunStatus,
    ToolType,
    UserClue,
)
from iabv_v15.infra.config import load_app_config
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_incident_packet_service_builds_packet_from_hidden_incident_and_clue() -> None:
    root = _workspace('incident_packet')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    storage = ArtifactStorage(config.evolution_dir)
    dossier_repository = ExecutionDossierRepository(db, storage)
    incident_repository = HiddenIncidentRepository(db, storage)
    clue_repository = UserClueRepository(db, storage)

    incident = incident_repository.save(
        HiddenIncident(
            episode_id='episode-1',
            site_id='generic_web',
            incident_kind='navigation_stall',
            severity=IssueSeverity.HIGH,
            status=IncidentStatus.OPEN,
            summary='La pestana nueva se quedo cargando sin progreso util.',
            probable_cause='La navegacion quedo atascada al abrir una pestana nueva.',
            affected_url='https://www.google.com/search?q=mercadolibre',
        )
    )
    clue_repository.save(
        UserClue(
            text='Se congelo al abrir otra pestana.',
            episode_id='episode-1',
            linked_incident_id=incident.incident_id,
            site_id='generic_web',
        )
    )
    dossier_repository.save(
        ExecutionDossier(
            scope=DossierScope.TEACHING,
            title='Sesion con varias pestanas',
            summary='La sesion dejo un incidente de navegacion visible para Codex.',
            episode_id='episode-1',
            status=RunStatus.PARTIAL,
            severity=IssueSeverity.HIGH,
            issue_hint_text='navigation_stall',
            issue_candidates=[
                IssueCandidate(
                    title='Navegacion atascada',
                    summary='La pestana nueva no avanzo.',
                    probable_cause='La sesion multitab no reporto progreso visible.',
                    severity=IssueSeverity.HIGH,
                    issue_hint='navigation_stall',
                )
            ],
            improvement_proposals=[
                ImprovementProposal(
                    title='Revisar navegacion multitab',
                    rationale='La pestana nueva se atoro.',
                    recommended_change='Instrumentar mejor la pestana activa y el progreso visible.',
                    suggested_tests=['Abrir 3-4 pestanas', 'Buscar en la ultima pestana'],
                    tradeoffs=['Mas observabilidad puede anadir algo de ruido local.'],
                    priority_score=90,
                )
            ],
        )
    )

    service = IncidentPacketService(
        dossier_repository=dossier_repository,
        hidden_incident_repository=incident_repository,
        user_clue_repository=clue_repository,
        workspace_root=str(root),
    )

    packet = service.build_codex_packet_for_issue(IncidentQuery(incident_id=incident.incident_id, limit=5))

    assert 'navigation_stall' in packet
    assert 'Se congelo al abrir otra pestana.' in packet
    assert 'Instrumentar mejor la pestana activa y el progreso visible.' in packet


def test_incident_packet_service_labels_replay_teaching_cases() -> None:
    root = _workspace('incident_packet_replay')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    storage = ArtifactStorage(config.evolution_dir)
    dossier_repository = ExecutionDossierRepository(db, storage)
    incident_repository = HiddenIncidentRepository(db, storage)
    clue_repository = UserClueRepository(db, storage)

    incident = incident_repository.save(
        HiddenIncident(
            episode_id='episode-replay',
            site_id='wplay',
            incident_kind='manual_correction_hotspot',
            severity=IssueSeverity.MEDIUM,
            status=IncidentStatus.NEEDS_FIX,
            summary='El usuario corrige manualmente varios objetos del replay.',
            probable_cause='Conviene convertir estas correcciones en reglas o anotaciones preferidas.',
        )
    )
    dossier_repository.save(
        ExecutionDossier(
            scope=DossierScope.TEACHING,
            title='Replay visual de login',
            summary='Replay visual actualizado con anotaciones y correcciones persistentes.',
            episode_id='episode-replay',
            status=RunStatus.SUCCESS,
            severity=IssueSeverity.MEDIUM,
            metrics={
                'replay_visual_summary': {
                    'green_count': 2,
                    'orange_count': 1,
                    'red_count': 0,
                    'gaps': ['campo submit no alineado'],
                    'metadata': {
                        'audit_status': 'doubtful',
                        'audit_overall_confidence': 0.61,
                        'audit_findings': [
                            'El replay no pudo confirmar visualmente este paso.',
                            'Hubo escritura o foco sin captura visible suficiente para comprobar el elemento.',
                        ],
                        'audit_rationale': 'Existen pasos donde el fondo dice una cosa, pero la pantalla no lo confirma todavia.',
                    },
                },
                'manual_correction_count': 3,
            },
        )
    )

    service = IncidentPacketService(
        dossier_repository=dossier_repository,
        hidden_incident_repository=incident_repository,
        user_clue_repository=clue_repository,
        workspace_root=str(root),
    )

    packet = service.build_codex_packet_for_issue(IncidentQuery(incident_id=incident.incident_id, limit=5))

    assert 'Paquete para Codex - Replay y ensenanza IABV v1.5' in packet
    assert 'Tipo de caso: Replay y ensenanza' in packet
    assert 'Run: no aplica (caso de replay/ensenanza)' in packet
    assert 'deteccion visual de objetos criticos sigue siendo debil' in packet
    assert 'audit_status: doubtful' in packet
    assert 'audit_overall_confidence: 0.61' in packet
    assert 'audit_hallazgo_principal: El replay no pudo confirmar visualmente este paso.' in packet
    assert 'audit_discrepancias_visuales: Hubo escritura o foco sin captura visible suficiente para comprobar el elemento.; campo submit no alineado' in packet


def test_incident_packet_service_includes_interaction_context_and_codex_task_spec() -> None:
    root = _workspace('incident_packet_interactions')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    storage = ArtifactStorage(config.evolution_dir)
    dossier_repository = ExecutionDossierRepository(db, storage)
    incident_repository = HiddenIncidentRepository(db, storage)
    clue_repository = UserClueRepository(db, storage)
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))

    pattern = tool_records.save_interaction_pattern(
        InteractionPattern(
            signature='sig-replay-wplay',
            title='Replay login Wplay',
            channel=InteractionChannel.UI,
            tool_id='playwright_browser',
            tool_type=ToolType.BROWSER,
            site_id='wplay',
            success_count=2,
            failure_count=0,
        )
    )
    episode = tool_records.save_interaction_episode(
        InteractionEpisode(
            objective='Abrir Wplay e iniciar sesion.',
            mode_used=InteractionChannel.UI,
            environment={'tool_id': 'playwright_browser'},
            actions=[InteractionAction(channel=InteractionChannel.UI, operation='click', target='#submit')],
            result=InteractionResult(success=True, execution_state=ExecutionState(state='observed', detail='ok'), summary='ok', confidence=0.84),
            confidence=0.84,
            human_approval=False,
            policy_decision=InteractionPolicyDecision(approval_decision=ApprovalDecision.SKIPPED, confidence=0.84),
            selector_name='teaching_replay_bridge',
            selector_reason='Patron equivalente ya observado.',
            pattern_id=pattern.pattern_id,
            reused_pattern=True,
            tool_id='playwright_browser',
            tool_type=ToolType.BROWSER,
            site_id='wplay',
            metadata={'source': 'teaching_session'},
        )
    )

    incident = incident_repository.save(
        HiddenIncident(
            episode_id='episode-replay-rich',
            site_id='wplay',
            incident_kind='critical_object_missing',
            severity=IssueSeverity.HIGH,
            status=IncidentStatus.NEEDS_FIX,
            summary='Falta el boton submit en el replay.',
        )
    )
    dossier_repository.save(
        ExecutionDossier(
            scope=DossierScope.TEACHING,
            title='Replay visual de Wplay',
            summary='Faltan objetos criticos en el replay.',
            episode_id='episode-replay-rich',
            status=RunStatus.PARTIAL,
            severity=IssueSeverity.HIGH,
            metrics={'replay_visual_summary': {'green_count': 1, 'orange_count': 1, 'red_count': 2}},
        )
    )

    service = IncidentPacketService(
        dossier_repository=dossier_repository,
        hidden_incident_repository=incident_repository,
        user_clue_repository=clue_repository,
        workspace_root=str(root),
        tool_record_repository=tool_records,
    )

    packet = service.build_codex_packet_for_issue(IncidentQuery(incident_id=incident.incident_id, limit=5))
    task_spec = service.build_codex_task_spec_for_issue(IncidentQuery(incident_id=incident.incident_id, limit=5))

    assert 'interaction_pattern: Replay login Wplay' in packet
    assert episode.interaction_episode_id in packet
    assert task_spec is not None
    assert task_spec.context_pack is not None
    assert episode.interaction_episode_id in task_spec.context_pack.interaction_episode_ids
    assert any('capture_studio_viewmodel.py' in item.path for item in task_spec.file_scope)



def test_incident_packet_service_targets_teaching_capture_bridge_cases() -> None:
    root = _workspace('incident_packet_teaching_bridge')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    storage = ArtifactStorage(config.evolution_dir)
    dossier_repository = ExecutionDossierRepository(db, storage)
    incident_repository = HiddenIncidentRepository(db, storage)
    clue_repository = UserClueRepository(db, storage)

    incident = incident_repository.save(
        HiddenIncident(
            episode_id='episode-teach-bridge',
            site_id='wplay',
            incident_kind='bridge_lag',
            severity=IssueSeverity.HIGH,
            status=IncidentStatus.OPEN,
            summary='La captura visible acumula retraso en el bridge.',
            affected_url='https://www.wplay.co/casino-en-vivo',
        )
    )
    dossier_repository.save(
        ExecutionDossier(
            scope=DossierScope.TEACHING,
            title='Ensenanza de Wplay',
            summary='Pasos: 13 | artefactos: 124 | visible: 12 | capturas: 9 | API guardada: 120 | replay: complete',
            episode_id='episode-teach-bridge',
            status=RunStatus.PARTIAL,
            severity=IssueSeverity.HIGH,
            metrics={'visible_step_count': 12, 'artifact_count': 124, 'api_artifact_count': 120, 'replay_quality': 'complete'},
            improvement_proposals=[
                ImprovementProposal(
                    title='Convertir demostracion en conocimiento reusable',
                    rationale='La ensenanza dejo suficiente evidencia para revision.',
                    recommended_change='Validar el replay y confirmar si la sesion debe pasar a tarea o conocimiento confirmado.',
                    suggested_tests=['Replay guiado', 'Payload de entrenamiento'],
                    priority_score=52,
                ),
                ImprovementProposal(
                    title='Reducir atraso del bridge',
                    rationale='La captura visible acumula retraso en el bridge.',
                    recommended_change='Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina.',
                    suggested_tests=['Captura con escritura rapida', 'Varias pestanas'],
                    priority_score=82,
                ),
            ],
        )
    )

    service = IncidentPacketService(
        dossier_repository=dossier_repository,
        hidden_incident_repository=incident_repository,
        user_clue_repository=clue_repository,
        workspace_root=str(root),
    )

    packet = service.build_codex_packet_for_issue(IncidentQuery(incident_id=incident.incident_id, limit=5))
    task_spec = service.build_codex_task_spec_for_issue(IncidentQuery(incident_id=incident.incident_id, limit=5))

    assert 'Paquete para Codex - Ensenanza guiada IABV v1.5' in packet
    assert 'bridge visible acumulo eventos y checkpoints' in packet
    assert 'Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina.' in packet
    assert 'auditoria_2_planos: sin auditoria de dos planos disponible' in packet
    assert task_spec is not None
    assert task_spec.goal == 'Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina.'
    assert any('browser_teach_session_service.py' in item.path for item in task_spec.file_scope)
    assert any('capture_studio_viewmodel.py' in item.path for item in task_spec.file_scope)
    assert any('interaction_learning_service.py' in item.path for item in task_spec.file_scope)




