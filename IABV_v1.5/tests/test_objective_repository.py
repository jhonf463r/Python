from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import ObjectiveNode, ObjectiveNodeKind, ObjectiveStatus
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
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



def _objective_repository(root: Path) -> tuple[AppDatabase, ObjectiveRepository]:
    db = AppDatabase(str(root / "app.sqlite"))
    storage = ArtifactStorage(str(root / "evolution"))
    return db, ObjectiveRepository(db, storage)


def _seed_objective(repository: ObjectiveRepository) -> ObjectiveNode:
    return repository.save(
        ObjectiveNode(
            kind=ObjectiveNodeKind.OBJECTIVE,
            title="Read integrity probe",
            status=ObjectiveStatus.ACTIVE,
        )
    )


def test_missing_objective_payload_is_reported_and_index_row_is_preserved() -> None:
    root = _workspace("objective_missing_payload")
    try:
        db, repository = _objective_repository(root)
        node = _seed_objective(repository)
        row = db.fetchone(
            "SELECT objective_id, path FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        )
        assert row is not None
        Path(row["path"]).unlink()

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.records_seen == 1
        assert report.records_loaded == 0
        assert report.missing_ids == [node.objective_id]
        assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
        preserved = db.fetchone(
            "SELECT objective_id FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        )
        assert preserved is not None
        with pytest.raises(RepositoryReadError):
            repository.list_recent()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_corrupt_objective_payload_is_reported_without_pruning_index() -> None:
    root = _workspace("objective_corrupt_payload")
    try:
        db, repository = _objective_repository(root)
        node = _seed_objective(repository)
        row = db.fetchone(
            "SELECT path FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        )
        assert row is not None
        Path(row["path"]).write_text("{", encoding="utf-8")

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.results[0].status == ArtifactReadStatus.CORRUPT
        assert report.failed_ids == [node.objective_id]
        assert db.fetchone(
            "SELECT objective_id FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        ) is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_unsupported_objective_schema_is_reported_without_pruning_index() -> None:
    root = _workspace("objective_unsupported_schema")
    try:
        db, repository = _objective_repository(root)
        node = _seed_objective(repository)
        row = db.fetchone(
            "SELECT path FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        )
        assert row is not None
        Path(row["path"]).write_text("{}", encoding="utf-8")

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.results[0].status == ArtifactReadStatus.SCHEMA_UNSUPPORTED
        assert db.fetchone(
            "SELECT objective_id FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        ) is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_objective_io_failure_is_not_classified_as_missing_or_pruned(monkeypatch) -> None:
    root = _workspace("objective_io_failure")
    try:
        db, repository = _objective_repository(root)
        node = _seed_objective(repository)
        row = db.fetchone(
            "SELECT path FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        )
        assert row is not None
        artifact_path = Path(row["path"])
        original_read_text = Path.read_text

        def fail_target_read(self, *args, **kwargs):
            if self == artifact_path:
                raise PermissionError("simulated denied read")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fail_target_read)
        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.results[0].status == ArtifactReadStatus.READ_FAILED
        assert report.results[0].error_type == "PermissionError"
        assert db.fetchone(
            "SELECT objective_id FROM objective_nodes WHERE objective_id = ?",
            (node.objective_id,),
        ) is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_objective_fetchone_sqlite_failure_preserves_current_report(monkeypatch) -> None:
    root = _workspace("objective_fetchone_sqlite_failure")
    try:
        db, repository = _objective_repository(root)

        def fail_fetchone(*args, **kwargs):
            raise sqlite3.OperationalError("PRIVATE_DB_ERROR_CANARY")

        monkeypatch.setattr(db, "fetchone", fail_fetchone)
        result = repository.get_with_diagnostics("objective-requested")

        assert result.status == ArtifactReadStatus.READ_FAILED
        assert result.error_type == "OperationalError"
        report = repository.last_read_report
        assert report is not None
        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.requested_artifact_id == "objective-requested"
        assert report.collection_error_type == "OperationalError"

        with pytest.raises(RepositoryReadError) as exc_info:
            repository.get("objective-requested")
        assert exc_info.value.report.requested_artifact_id == "objective-requested"
        assert repository.last_read_report is exc_info.value.report
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_objective_fetchall_sqlite_failure_replaces_stale_report(monkeypatch) -> None:
    root = _workspace("objective_fetchall_sqlite_failure")
    try:
        db, repository = _objective_repository(root)
        previous = repository.list_recent_with_diagnostics()
        assert previous.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

        def fail_fetchall(*args, **kwargs):
            raise sqlite3.OperationalError("PRIVATE_DB_ERROR_CANARY")

        monkeypatch.setattr(db, "fetchall", fail_fetchall)
        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.collection_error_type == "OperationalError"
        assert report.collection_error_message == "Repository read failed."
        assert "PRIVATE_DB_ERROR_CANARY" not in str(report.to_dict())
        assert repository.last_read_report is report
        assert report is not previous

        with pytest.raises(RepositoryReadError) as exc_info:
            repository.list_recent()
        assert exc_info.value.report.status == RepositoryReadStatus.READ_FAILED
        assert repository.last_read_report is exc_info.value.report
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_query_not_executed_is_fail_closed_generically_but_empty_title_is_legacy_noop(monkeypatch) -> None:
    root = _workspace("objective_query_not_executed")
    try:
        db, repository = _objective_repository(root)

        def forbidden_fetchall(*args, **kwargs):
            raise AssertionError("empty-title probe must not execute SQL")

        monkeypatch.setattr(db, "fetchall", forbidden_fetchall)
        matches, report = repository.find_equivalent_with_diagnostics(
            kind=ObjectiveNodeKind.OBJECTIVE,
            title="   ",
        )

        assert matches == []
        assert report.status == RepositoryReadStatus.QUERY_NOT_EXECUTED
        assert report.query_not_executed is True
        assert report.to_dict()["query_not_executed"] is True
        with pytest.raises(RepositoryReadError) as exc_info:
            report.require_complete()
        assert exc_info.value.report is report

        assert repository.find_equivalent(
            kind=ObjectiveNodeKind.OBJECTIVE,
            title="   ",
        ) == []
        assert repository.last_read_report is not None
        assert repository.last_read_report.status == RepositoryReadStatus.QUERY_NOT_EXECUTED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_partial_objective_report_preserves_valid_items_inside_error() -> None:
    root = _workspace("objective_partial_report_items")
    try:
        db, repository = _objective_repository(root)
        valid_a = _seed_objective(repository)
        valid_b = _seed_objective(repository)
        corrupt = _seed_objective(repository)
        row = db.fetchone(
            "SELECT path FROM objective_nodes WHERE objective_id = ?",
            (corrupt.objective_id,),
        )
        assert row is not None
        Path(row["path"]).write_text("{", encoding="utf-8")

        report = repository.list_recent_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_PARTIAL
        assert report.records_seen == 3
        assert report.records_loaded == 2
        assert len(report.items) == 2
        with pytest.raises(RepositoryReadError) as exc_info:
            report.require_complete()
        assert len(exc_info.value.report.items) == 2
        assert len(exc_info.value.report.results) == 3
        assert {node.objective_id for node in exc_info.value.report.items} == {
            valid_a.objective_id, valid_b.objective_id
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)
