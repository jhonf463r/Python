from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    GoalContext,
    InferenceRequest,
    InferenceResult,
    ReasoningMode,
    ProviderKind,
    RouteDecision,
    RunRecord,
    TaskContext,
    TaskRole,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.services.knowledge.unified_memory_layer import UnifiedMemoryLayer


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_unified_memory_layer_exposes_goal_context_and_persists_it() -> None:
    root = _workspace('unified_memory_layer')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        repository = KnowledgeRepository(db)
        layer = UnifiedMemoryLayer(repository)
        goal_context = GoalContext(
            objective={'objective_id': 'obj-1', 'title': 'Mejorar login Wplay'},
            project={'objective_id': 'proj-1', 'title': 'Login Wplay persistente'},
            task={'objective_id': 'task-1', 'title': 'Abrir Wplay e iniciar sesion'},
            active_node_id='task-1',
            active_title='Abrir Wplay e iniciar sesion',
            status='blocked',
            progress=0.58,
            blocker='Bridge lag persistente',
            confidence=0.64,
            trend='bloqueado',
            metadata={'site_id': 'wplay'},
        )
        context = TaskContext(
            site_id='wplay',
            site_display_name='Wplay',
            evidence_summary=['audit:bridge_lag'],
            recent_incidents=[{'incident_kind': 'bridge_lag'}],
            session_readiness={'incident_count': 1},
            live_audit={'decision_action': 'consult_codex'},
            goal_context=goal_context,
        )

        snapshot = layer.build_snapshot(context)
        assert snapshot['objectives']['status'] == 'blocked'
        assert snapshot['objectives']['task']['objective_id'] == 'task-1'
        assert snapshot['objectives']['blocker'] == 'Bridge lag persistente'

        record = RunRecord(
            request=InferenceRequest(
                user_goal='abre Wplay e inicia sesion',
                task_role=TaskRole.TRAINING,
                goal_parameters={'selected_role': 'training'},
            ),
            result=InferenceResult(
                request_id='req-1',
                provider_name='Adaptive local orchestrator',
                reasoning_mode=ReasoningMode.LOCAL,
                summary='La ruta local detecto un bloqueo de bridge.',
                inferred_task='Abrir Wplay e iniciar sesion',
                confidence=0.78,
                raw_output={'decision_context': {'goal_context': goal_context.model_dump(mode='json')}},
            ),
            route=RouteDecision(
                primary_provider='Adaptive local orchestrator',
                primary_kind=ProviderKind.LOCAL,
                reason='Ruta local de entrenamiento',
            ),
        )

        saved = layer.remember_run(record)

        assert saved.payload['goal_context']['status'] == 'blocked'
        assert saved.payload['goal_context']['project']['objective_id'] == 'proj-1'
        assert 'obj-1' in saved.tags
        assert 'proj-1' in saved.tags
        assert 'task-1' in saved.tags
    finally:
        shutil.rmtree(root, ignore_errors=True)
