from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    InferenceRequest,
    InteractionChannel,
    InteractionEpisode,
    InteractionResult,
    TaskIntent,
    TaskRole,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor


REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_episode_with_audit(*, objective: str, decision_action: str, episode_id: str = '') -> InteractionEpisode:
    return InteractionEpisode(
        interaction_episode_id=episode_id or str(uuid4()),
        objective=objective,
        mode_used=InteractionChannel.UI,
        confidence=0.5,
        tool_id='playwright_browser',
        tool_type=ToolType.BROWSER,
        site_id='wplay',
        metadata={
            'live_audit': {
                'audit_snapshot_id': f'audit-{uuid4().hex[:6]}',
                'confidence': 0.75,
                'findings': [{'kind': 'bridge_lag', 'title': 'Bridge lag'}],
                'decision': {'action': decision_action, 'recommended_tool_id': 'codex_installed'},
            }
        },
    )


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_live_audit_supervisor_marks_bridge_lag_and_persists_teaching_snapshot() -> None:
    root = _workspace('live_audit_supervisor_teaching')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = ToolRecordRepository(AppDatabase(str(root / 'app.sqlite')), ArtifactStorage(str(root / 'tool_teaching')))
        supervisor = LiveAuditSupervisor(tool_record_repository=repository)
        episode = InteractionEpisode(
            objective='Abrir Wplay e iniciar sesion.',
            mode_used=InteractionChannel.UI,
            environment={'tool_id': 'playwright_browser', 'site_id': 'wplay'},
            captured_metadata={'capture_stats': {'queue_depth': 8, 'heartbeat_count': 14}},
            confidence=0.22,
            tool_id='playwright_browser',
            tool_type=ToolType.BROWSER,
            site_id='wplay',
            metadata={'source': 'teaching_session'},
            result=InteractionResult(
                success=False,
                execution_state=ExecutionState(
                    state='observed',
                    detail='Bundle debil.',
                    approval_decision=ApprovalDecision.SKIPPED,
                ),
                summary='Ensenanza debil para login.',
                confidence=0.22,
                metadata={'source': 'teaching_session'},
            ),
        )
        learning_packet = {
            'bundle_id': 'bundle-live-audit',
            'capture_stats': {
                'step_count': 9,
                'relevant_step_count': 6,
                'visible_step_count': 2,
                'screenshot_count': 1,
                'queue_depth': 8,
                'api_dropped_count': 4,
                'heartbeat_count': 14,
            },
            'learning_readiness': {'status': 'insufficient'},
            'login_learning': {'status': 'insufficient', 'login_visual_completeness': 0.0},
            'visual_summary': {
                'visual_alignment_score': 0.0,
                'critical_object_coverage': 0.0,
                'login_visual_completeness': 0.0,
                'critical_objects': ['login_form'],
            },
            'interaction_confidence': 0.22,
        }

        updated_episode, updated_packet, snapshot = supervisor.audit_teaching_session(
            site_id='wplay',
            display_name='Wplay',
            learning_packet=learning_packet,
            interaction_episode=episode,
            incidents=[{'incident_kind': 'bridge_lag', 'severity': 'medium'}],
        )

        assert updated_episode is not None
        assert snapshot is not None
        assert snapshot.decision.action == 'consult_codex'
        assert {item.kind for item in snapshot.findings} >= {'bridge_lag', 'learning_not_consolidated'}
        stored = repository.get_interaction_episode(updated_episode.interaction_episode_id)
        assert stored is not None
        assert stored.metadata['live_audit']['decision']['action'] == 'consult_codex'
        assert updated_packet['metadata']['audit_decision'] == 'consult_codex'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_context_assembler_exposes_latest_live_audit_summary() -> None:
    workspace = _workspace('task_context_live_audit')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        bootstrap = AppBootstrap(str(workspace))
        episode = InteractionEpisode(
            objective='Abrir Wplay e iniciar sesion.',
            mode_used=InteractionChannel.UI,
            confidence=0.38,
            tool_id='playwright_browser',
            tool_type=ToolType.BROWSER,
            site_id='wplay',
            metadata={
                'live_audit': {
                    'audit_snapshot_id': 'audit-1',
                    'confidence': 0.78,
                    'findings': [{'kind': 'learning_not_consolidated', 'title': 'Aprendizaje aun debil'}],
                    'decision': {'action': 'retry_after_rebuild', 'recommended_tool_id': 'playwright_browser'},
                }
            },
        )
        bootstrap.tool_record_repository.save_interaction_episode(episode)

        context = bootstrap.task_context_assembler.build(
            InferenceRequest(user_goal='abre Wplay e inicia sesion', task_role=TaskRole.TRAINING, site_hint='wplay'),
            TaskIntent(title='Abrir Wplay e iniciar sesion', intent_key='wplay.login', detected_role=TaskRole.TRAINING, site_hint='wplay'),
        )

        assert context.live_audit['decision_action'] == 'retry_after_rebuild'
        assert context.metadata['live_audit']['recommended_tool_id'] == 'playwright_browser'
        assert any('Auditoria viva:' in item for item in context.evidence_summary)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_live_audit_supervisor_marks_external_capture_block_as_blocked_not_successful_evidence() -> None:
    root = _workspace('live_audit_supervisor_external_block')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = ToolRecordRepository(AppDatabase(str(root / 'app.sqlite')), ArtifactStorage(str(root / 'tool_teaching')))
        supervisor = LiveAuditSupervisor(tool_record_repository=repository)
        card = ToolCard(
            tool_id='chatgpt_web_assisted',
            title='ChatGPT web asistido',
            tool_type=ToolType.LLM_WEB_UI,
            adapter_key='external_assistant',
        )
        task = ToolTask(
            tool_id='chatgpt_web_assisted',
            title='Consultar ChatGPT',
            objective='Consultar por que no despega Playwright',
            requested_by_role=TaskRole.TOOL_USE,
        )
        result = ToolResult(
            task_id=task.task_id,
            tool_id='chatgpt_web_assisted',
            tool_type=ToolType.LLM_WEB_UI,
            success=False,
            error_message='[WinError 5] Acceso denegado',
            execution_state=ExecutionState(
                state='failed',
                detail='[WinError 5] Acceso denegado',
                metadata={'external_state_flags': ['capture_unverified']},
            ),
            metadata={'external_state_flags': ['capture_unverified']},
        )

        updated = supervisor.audit_tool_result(card=card, task=task, result=result)
        live_audit = dict(updated.metadata.get('live_audit') or {})

        assert live_audit['decision']['action'] == 'continue_local'
        assert 'bloqueada o sin captura verificable' in live_audit['decision']['rationale']
        assert 'external_route_blocked' in [item['kind'] for item in live_audit['findings']]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_latest_summary_filters_by_user_goal() -> None:
    """R15-1: latest_summary must skip episodes whose objective doesn't match
    user_goal when goal_tokens <= 4.  Before the fix, ``pass`` was used instead
    of ``continue``, making the goal filter dead code."""
    root = _workspace('live_audit_goal_filter')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = ToolRecordRepository(
            AppDatabase(str(root / 'app.sqlite')),
            ArtifactStorage(str(root / 'tool_teaching')),
        )
        supervisor = LiveAuditSupervisor(tool_record_repository=repository)

        unrelated = _make_episode_with_audit(
            objective='Configurar proxy de red',
            decision_action='continue_local',
        )
        matching = _make_episode_with_audit(
            objective='Abrir Wplay e iniciar sesion',
            decision_action='consult_codex',
        )
        repository.save_interaction_episode(unrelated)
        repository.save_interaction_episode(matching)

        result = supervisor.latest_summary(user_goal='iniciar sesion Wplay')

        assert result, 'Expected a non-empty summary for a matching episode'
        assert result['decision_action'] == 'consult_codex', (
            f"Expected 'consult_codex' from the matching episode, got '{result['decision_action']}' "
            '(goal filter may be dead — pass vs continue)'
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)
