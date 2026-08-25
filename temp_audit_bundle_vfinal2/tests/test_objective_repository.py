from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import ObjectiveNode, ObjectiveNodeKind, ObjectiveStatus
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_objective_repository_persists_hierarchy_and_equivalents() -> None:
    root = _workspace('objective_repository')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'evolution'))
        repository = ObjectiveRepository(db, storage)

        objective = repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.OBJECTIVE,
                title='Mejorar login Wplay',
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.35,
                confidence=0.61,
            )
        )
        project = repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.PROJECT,
                title='Login Wplay persistente',
                parent_id=objective.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.42,
            )
        )
        task = repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.TASK,
                title='Abrir Wplay e iniciar sesion',
                parent_id=project.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.BLOCKED,
                progress=0.55,
                blocker='Bridge lag persistente',
            )
        )
        subtask = repository.save(
            ObjectiveNode(
                kind=ObjectiveNodeKind.SUBTASK,
                title='Verificar boton submit',
                parent_id=task.objective_id,
                root_id=objective.objective_id,
                site_id='wplay',
                status=ObjectiveStatus.ACTIVE,
                progress=0.2,
            )
        )

        stored_task = repository.get(task.objective_id)
        latest_task = repository.latest_active(kind=ObjectiveNodeKind.TASK, site_id='wplay')
        children = repository.list_children(task.objective_id, kind=ObjectiveNodeKind.SUBTASK)
        equivalent = repository.find_equivalent(
            kind=ObjectiveNodeKind.TASK,
            title='Abrir   Wplay   e iniciar sesion',
            parent_id=project.objective_id,
            root_id=objective.objective_id,
            site_id='wplay',
        )

        assert stored_task is not None
        assert stored_task.blocker == 'Bridge lag persistente'
        assert latest_task is not None
        assert latest_task.objective_id == task.objective_id
        assert len(children) == 1
        assert children[0].objective_id == subtask.objective_id
        assert equivalent
        assert equivalent[0].objective_id == task.objective_id
    finally:
        shutil.rmtree(root, ignore_errors=True)
