from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    InteractionChannel,
    InteractionAction,
    InteractionChannel,
    InteractionEpisode,
    InteractionEvidence,
    InteractionObservation,
    InteractionPattern,
    InteractionPolicyDecision,
    InteractionResult,
    LearningSignal,
    TaskRole,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadStatus,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_tool_record_repository_round_trip() -> None:
    root = _workspace('tool_record_repository')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)

        card = ToolCard(
            tool_id='shell_command',
            title='Shell local seguro',
            tool_type=ToolType.SHELL,
            description='Wrapper local controlado.',
            adapter_key='shell',
            validation_status=ToolValidationStatus.SANDBOX_PASS,
            available=True,
            capabilities=['run_command'],
            metadata={'updated_at_utc': '2026-04-02T00:00:00+00:00'},
        )
        task = ToolTask(
            tool_id='shell_command',
            title='Inspeccionar entorno',
            objective='Ejecutar un comando local seguro.',
            requested_by_role=TaskRole.TOOL_USE,
            execution_scope='read_only',
            approval_decision=ApprovalDecision.SKIPPED,
            metadata={
                'created_at_utc': '2026-04-02T00:00:00+00:00',
                'updated_at_utc': '2026-04-02T00:00:00+00:00',
            },
        )
        result = ToolResult(
            task_id=task.task_id,
            tool_id='shell_command',
            tool_type=ToolType.SHELL,
            success=True,
            validation_status=ToolValidationStatus.APPROVED,
            execution_state=ExecutionState(state='executed', detail='Comando ejecutado.', sandboxed=False, validated=True),
            output_text='ok',
        )

        pattern = InteractionPattern(
            signature='sig-shell-read-only',
            title='Shell read only',
            channel=InteractionChannel.BACKGROUND,
            tool_id='shell_command',
            tool_type=ToolType.SHELL,
            success_count=1,
            metadata={'objective_excerpt': 'Ejecutar un comando local seguro.'},
        )
        interaction_result = InteractionResult(
            success=True,
            execution_state=ExecutionState(state='executed', detail='Comando ejecutado.', sandboxed=False, validated=True),
            summary='Comando ejecutado.',
            confidence=0.91,
            execution_ms=10,
        )
        episode = InteractionEpisode(
            objective='Ejecutar un comando local seguro.',
            mode_used=InteractionChannel.BACKGROUND,
            environment={'tool_id': 'shell_command'},
            actions=[
                InteractionAction(
                    channel=InteractionChannel.BACKGROUND,
                    operation='run_command',
                    target='Get-Location',
                )
            ],
            result=interaction_result,
            evidence=[InteractionEvidence(kind='log', label='Salida shell', ref_id='shell:stdout', confidence=0.8)],
            learning_signals=[
                LearningSignal(label='pattern:background:shell_command', channel=InteractionChannel.BACKGROUND, confidence=0.91)
            ],
            confidence=0.91,
            human_approval=False,
            policy_decision=InteractionPolicyDecision(approval_decision=ApprovalDecision.SKIPPED, confidence=0.91),
            selector_name='universal_mode_selector',
            selector_reason='Ya existe un patron exitoso en background.',
            pattern_id=pattern.pattern_id,
            reused_pattern=False,
            tool_id='shell_command',
            tool_type=ToolType.SHELL,
            task_id=task.task_id,
            result_id=result.result_id,
            metadata={'mode_selection': {'selected_mode': 'background'}},
        )
        observation = InteractionObservation(
            pattern_id=pattern.pattern_id,
            task_id=task.task_id,
            result_id=result.result_id,
            episode_id=episode.interaction_episode_id,
            success=True,
            channel=InteractionChannel.BACKGROUND,
            tool_id='shell_command',
            tool_type=ToolType.SHELL,
            summary='Comando ejecutado.',
            confidence=0.91,
            evidence_refs=['shell:stdout'],
        )

        repository.save_card(card)
        repository.save_task(task)
        repository.save_result(result)
        repository.save_interaction_pattern(pattern)
        repository.save_interaction_episode(episode)
        repository.save_interaction_observation(observation)
        log_id = repository.log_execution(
            tool_id='shell_command',
            task_id=task.task_id,
            action_type='run_command',
            state='executed',
            payload={'ok': True},
            created_at_utc='2026-04-02T00:00:00+00:00',
        )

        stored_card = repository.get_card('shell_command')
        stored_task = repository.get_task(task.task_id)
        stored_results = repository.list_results(task_id=task.task_id)
        stored_patterns = repository.list_interaction_patterns(tool_id='shell_command')
        stored_episodes = repository.list_interaction_episodes(tool_id='shell_command')
        stored_observations = repository.list_interaction_observations(tool_id='shell_command')
        stored_log = repository.list_log(task_id=task.task_id)

        assert stored_card is not None
        assert stored_card.tool_type == ToolType.SHELL
        assert stored_card.validation_status == ToolValidationStatus.SANDBOX_PASS
        assert stored_task is not None
        assert stored_task.requested_by_role == TaskRole.TOOL_USE
        assert stored_task.execution_scope == 'read_only'
        assert len(stored_results) == 1
        assert stored_results[0].validation_status == ToolValidationStatus.APPROVED
        assert stored_results[0].execution_state.state == 'executed'
        assert len(stored_patterns) == 1
        assert stored_patterns[0].channel == InteractionChannel.BACKGROUND
        assert len(stored_episodes) == 1
        assert stored_episodes[0].mode_used == InteractionChannel.BACKGROUND
        assert stored_episodes[0].result is not None
        assert stored_episodes[0].result.confidence == 0.91
        assert stored_episodes[0].selector_name == 'universal_mode_selector'
        assert stored_episodes[0].selector_reason == 'Ya existe un patron exitoso en background.'
        assert stored_episodes[0].learning_signals[0].label == 'pattern:background:shell_command'
        assert len(stored_observations) == 1
        assert stored_observations[0].pattern_id == pattern.pattern_id
        assert stored_observations[0].episode_id == episode.interaction_episode_id
        assert len(stored_log) == 1
        assert stored_log[0]['log_id'] == log_id
        assert stored_log[0]['payload']['ok'] is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _read_integrity_repository(name: str) -> tuple[Path, AppDatabase, ToolRecordRepository]:
    root = _workspace(name)
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    return root, db, ToolRecordRepository(db, storage)


def _read_integrity_card(tool_id: str) -> ToolCard:
    return ToolCard(
        tool_id=tool_id,
        title=f'Tool {tool_id}',
        tool_type=ToolType.SHELL,
        description='Synthetic card for read-integrity tests.',
        adapter_key='shell',
        validation_status=ToolValidationStatus.SANDBOX_PASS,
        available=True,
    )


def test_tool_record_missing_card_payload_is_reported_without_pruning_index() -> None:
    root, db, repository = _read_integrity_repository('tool_record_missing_card')
    try:
        card = repository.save_card(_read_integrity_card('missing-card'))
        row = db.fetchone(
            'SELECT tool_id, path FROM tool_cards WHERE tool_id = ?',
            (card.tool_id,),
        )
        assert row is not None
        Path(row['path']).unlink()

        report = repository.list_cards_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.records_seen == 1
        assert report.records_loaded == 0
        assert report.missing_ids == [card.tool_id]
        assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
        assert repository.last_read_report is report
        assert db.fetchone(
            'SELECT tool_id FROM tool_cards WHERE tool_id = ?',
            (card.tool_id,),
        ) is not None
        with pytest.raises(RepositoryReadError) as exc_info:
            repository.list_cards()
        assert exc_info.value.report.status == RepositoryReadStatus.READ_FAILED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_record_partial_card_report_preserves_valid_items_and_index_rows() -> None:
    root, db, repository = _read_integrity_repository('tool_record_partial_cards')
    try:
        valid = repository.save_card(_read_integrity_card('valid-card'))
        corrupt = repository.save_card(_read_integrity_card('corrupt-card'))
        row = db.fetchone(
            'SELECT path FROM tool_cards WHERE tool_id = ?',
            (corrupt.tool_id,),
        )
        assert row is not None
        Path(row['path']).write_text('{', encoding='utf-8')

        report = repository.list_cards_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_PARTIAL
        assert report.records_seen == 2
        assert report.records_loaded == 1
        assert [item.tool_id for item in report.items] == [valid.tool_id]
        corrupt_result = next(
            result for result in report.results if result.artifact_id == corrupt.tool_id
        )
        assert corrupt_result.status == ArtifactReadStatus.CORRUPT
        assert db.fetchone(
            'SELECT tool_id FROM tool_cards WHERE tool_id = ?',
            (corrupt.tool_id,),
        ) is not None
        with pytest.raises(RepositoryReadError) as exc_info:
            repository.list_cards()
        assert exc_info.value.report.status == RepositoryReadStatus.READ_PARTIAL
        assert len(exc_info.value.report.items) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_record_sqlite_fetchall_failure_replaces_stale_report(monkeypatch) -> None:
    root, db, repository = _read_integrity_repository('tool_record_fetchall_failure')
    try:
        previous = repository.list_cards_with_diagnostics()
        assert previous.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

        def fail_fetchall(*args, **kwargs):
            raise sqlite3.OperationalError('database is locked')

        monkeypatch.setattr(db, 'fetchall', fail_fetchall)
        report = repository.list_cards_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.collection_error_type == 'OperationalError'
        assert 'database is locked' in report.collection_error_message
        assert repository.last_read_report is report
        assert report is not previous
        with pytest.raises(RepositoryReadError) as exc_info:
            repository.list_cards()
        assert exc_info.value.report is repository.last_read_report
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_tool_record_task_missing_payload_is_reported_without_pruning_index() -> None:
    root, db, repository = _read_integrity_repository('tool_record_missing_task')
    try:
        task = ToolTask(
            tool_id='task-tool',
            title='Synthetic task',
            objective='Verify task artifact read integrity.',
            requested_by_role=TaskRole.TOOL_USE,
            execution_scope='read_only',
            approval_decision=ApprovalDecision.SKIPPED,
        )
        repository.save_task(task)
        row = db.fetchone(
            'SELECT task_id, path FROM tool_tasks WHERE task_id = ?',
            (task.task_id,),
        )
        assert row is not None
        Path(row['path']).unlink()

        report = repository.list_tasks_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.records_seen == 1
        assert report.records_loaded == 0
        assert report.missing_ids == [task.task_id]
        assert report.results[0].status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
        assert repository.last_read_report is report
        assert db.fetchone(
            'SELECT task_id FROM tool_tasks WHERE task_id = ?',
            (task.task_id,),
        ) is not None
        with pytest.raises(RepositoryReadError) as exc_info:
            repository.list_tasks()
        assert exc_info.value.report.status == RepositoryReadStatus.READ_FAILED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_record_log_requires_json_object_and_fails_closed() -> None:
    root, db, repository = _read_integrity_repository('tool_record_invalid_log_shape')
    try:
        log_id = repository.log_execution(
            tool_id='shell_command',
            task_id=None,
            action_type='read_only_check',
            state='executed',
            payload={'ok': True},
            created_at_utc='2026-11-05T00:00:00+00:00',
        )
        row = db.fetchone(
            'SELECT log_id, path FROM tool_execution_log WHERE log_id = ?',
            (log_id,),
        )
        assert row is not None
        Path(row['path']).write_text('[]', encoding='utf-8')

        report = repository.list_log_with_diagnostics()

        assert report.status == RepositoryReadStatus.READ_FAILED
        assert report.records_seen == 1
        assert report.results[0].status == ArtifactReadStatus.SCHEMA_UNSUPPORTED
        assert report.results[0].artifact_id == log_id
        with pytest.raises(RepositoryReadError) as exc_info:
            repository.list_log()
        assert exc_info.value.report.status == RepositoryReadStatus.READ_FAILED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_record_collection_readers_report_sqlite_errors_without_stale_reports(monkeypatch) -> None:
    root, db, repository = _read_integrity_repository('tool_record_all_collection_sqlite_errors')
    try:
        previous = repository.list_cards_with_diagnostics()
        assert previous.status == RepositoryReadStatus.NO_RECORDS_OBSERVED

        def fail_fetchall(*args, **kwargs):
            raise sqlite3.OperationalError('database is locked')

        monkeypatch.setattr(db, 'fetchall', fail_fetchall)
        readers = (
            repository.list_tasks_with_diagnostics,
            repository.list_results_with_diagnostics,
            repository.list_log_with_diagnostics,
            repository.list_interaction_patterns_with_diagnostics,
            repository.list_interaction_observations_with_diagnostics,
            repository.list_interaction_episodes_with_diagnostics,
        )
        for read_collection in readers:
            report = read_collection()
            assert report.status == RepositoryReadStatus.READ_FAILED
            assert report.collection_error_type == 'OperationalError'
            assert 'database is locked' in report.collection_error_message
            assert report.scope.startswith('SQLITE_INDEX_ROWS:')
            assert repository.last_read_report is report
            assert report is not previous
    finally:
        shutil.rmtree(root, ignore_errors=True)
