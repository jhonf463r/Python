from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import local
from typing import Any, Callable, Sequence, TypeVar
from uuid import uuid4

from iabv_v15.domain.models import InteractionEpisode, InteractionObservation, InteractionPattern, ToolCard, ToolResult, ToolTask
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_json_mapping_from_paths,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage

TRecord = TypeVar('TRecord')


class ToolRecordRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[Any] | None:
        """Per-thread diagnostics for the most recent collection read."""
        return getattr(self._read_state, "report", None)

    def _remember_report(self, report: RepositoryReadReport[Any]) -> RepositoryReadReport[Any]:
        self._read_state.report = report
        return report

    def _read_indexed_collection(
        self,
        *,
        table: str,
        id_column: str,
        relative_directory: str,
        sql: str,
        parameters: Sequence[object],
        reader: Callable[[Sequence[Path], str], ArtifactReadResult[TRecord]],
    ) -> RepositoryReadReport[TRecord]:
        """Read one bounded SQLite collection and retain every row outcome."""
        scope = f"SQLITE_INDEX_ROWS:{table}"
        try:
            rows = self.db.fetchall(sql, tuple(parameters))
        except Exception as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error(scope, exc)
            )

        results: list[ArtifactReadResult[TRecord]] = []
        for row in rows:
            artifact_id = str(row[id_column])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=artifact_id,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message="Indexed artifact path is invalid.",
                    )
                )
                continue

            paths: list[Path] = []
            if candidate.is_absolute():
                paths.append(candidate)
            paths.append(
                self.storage.root / relative_directory / f"{artifact_id}.json"
            )
            results.append(reader(paths, artifact_id))

        return self._remember_report(
            RepositoryReadReport.from_results(scope, results)
        )

    def _read_indexed_item(
        self,
        *,
        table: str,
        id_column: str,
        artifact_id: str,
        sql: str,
        parameters: Sequence[object],
        relative_directory: str,
        reader: Callable[[Sequence[Path], str], ArtifactReadResult[TRecord]],
    ) -> ArtifactReadResult[TRecord]:
        """Read one SQLite-indexed artifact and replace the current diagnostic report."""
        scope = f"SQLITE_INDEX_LOOKUP:{table}"
        try:
            row = self.db.fetchone(sql, tuple(parameters))
        except sqlite3.Error as exc:
            report = RepositoryReadReport.from_collection_error(
                scope,
                exc,
                requested_artifact_id=artifact_id,
            )
            self._remember_report(report)
            return ArtifactReadResult(
                artifact_id=artifact_id,
                path="",
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Repository point lookup failed.",
            )

        if row is None:
            result = ArtifactReadResult(
                artifact_id=artifact_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message=f"No {table} row exists in the SQLite index.",
            )
        else:
            resolved_id = str(row[id_column])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                result = ArtifactReadResult(
                    artifact_id=resolved_id,
                    path="",
                    status=ArtifactReadStatus.READ_FAILED,
                    error_type=type(exc).__name__,
                    error_message="Indexed artifact path is invalid.",
                )
            else:
                paths: list[Path] = []
                if candidate.is_absolute():
                    paths.append(candidate)
                paths.append(
                    self.storage.root / relative_directory / f"{resolved_id}.json"
                )
                result = reader(paths, resolved_id)

        self._remember_report(RepositoryReadReport.from_results(scope, [result]))
        return result

    def _legacy_item_value(
        self,
        result: ArtifactReadResult[TRecord],
    ) -> TRecord | None:
        """Preserve legacy None-on-absent behavior; fail closed on unreadable records."""
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        if report is None:
            raise RuntimeError("indexed_item_read_report_not_recorded")
        raise RepositoryReadError(report)

    def save_card(self, card: ToolCard) -> ToolCard:
        relative_path = f"cards/{card.tool_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, card.model_dump(mode='json'))
        updated_at = str(card.last_validated_at_utc.isoformat() if card.last_validated_at_utc is not None else card.metadata.get('updated_at_utc') or '')
        if not updated_at:
            from datetime import datetime, timezone

            updated_at = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """
            INSERT OR REPLACE INTO tool_cards
            (tool_id, tool_type, title, validation_status, adapter_key, local_first, available, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card.tool_id,
                card.tool_type.value,
                card.title,
                card.validation_status.value,
                card.adapter_key,
                int(card.local_first),
                int(card.available),
                saved_path,
                updated_at,
            ),
        )
        return card

    def list_cards_with_diagnostics(self) -> RepositoryReadReport[ToolCard]:
        """Read the SQLite-indexed cards without pruning unreadable index rows."""
        try:
            rows = self.db.fetchall(
                """
                SELECT tool_id, path
                FROM tool_cards
                ORDER BY updated_at_utc DESC, title ASC
                """
            )
        except Exception as exc:
            return self._remember_report(
                RepositoryReadReport.from_collection_error("SQLITE_INDEX_ROWS", exc)
            )

        results: list[ArtifactReadResult[ToolCard]] = []
        for row in rows:
            tool_id = str(row["tool_id"])
            try:
                candidate = Path(row["path"])
            except (TypeError, ValueError, OSError) as exc:
                results.append(
                    ArtifactReadResult(
                        artifact_id=tool_id,
                        path="",
                        status=ArtifactReadStatus.READ_FAILED,
                        error_type=type(exc).__name__,
                        error_message="Indexed artifact path is invalid.",
                    )
                )
                continue
            paths: list[Path] = []
            if candidate.is_absolute():
                paths.append(candidate)
            paths.append(self.storage.root / f"cards/{tool_id}.json")
            results.append(read_model_from_paths(paths, tool_id, ToolCard))
        return self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_ROWS", results)
        )

    def list_cards(self) -> list[ToolCard]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_cards_with_diagnostics().require_complete()

    def get_card_with_diagnostics(self, tool_id: str) -> ArtifactReadResult[ToolCard]:
        return self._read_indexed_item(
            table="tool_cards",
            id_column="tool_id",
            artifact_id=tool_id,
            sql="SELECT tool_id, path FROM tool_cards WHERE tool_id = ?",
            parameters=(tool_id,),
            relative_directory="cards",
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, ToolCard
            ),
        )

    def get_card(self, tool_id: str) -> ToolCard | None:
        return self._legacy_item_value(self.get_card_with_diagnostics(tool_id))

    def save_task(self, task: ToolTask) -> ToolTask:
        relative_path = f"tasks/{task.task_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, task.model_dump(mode='json'))
        created_at = str(task.metadata.get('created_at_utc') or task.metadata.get('updated_at_utc') or '')
        updated_at = str(task.metadata.get('updated_at_utc') or created_at or '')
        if not created_at or not updated_at:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()
            created_at = created_at or now
            updated_at = updated_at or now
        self.db.execute(
            """
            INSERT OR REPLACE INTO tool_tasks
            (task_id, tool_id, status, requested_by_role, execution_scope, approval_decision, path, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                task.tool_id,
                task.status.value,
                task.requested_by_role.value,
                task.execution_scope,
                task.approval_decision.value,
                saved_path,
                created_at,
                updated_at,
            ),
        )
        return task

    def list_tasks_with_diagnostics(self, limit: int = 20) -> RepositoryReadReport[ToolTask]:
        return self._read_indexed_collection(
            table="tool_tasks",
            id_column="task_id",
            relative_directory="tasks",
            sql="""
                SELECT task_id, path
                FROM tool_tasks
                ORDER BY updated_at_utc DESC
                LIMIT ?
            """,
            parameters=(limit,),
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, ToolTask
            ),
        )

    def list_tasks(self, limit: int = 20) -> list[ToolTask]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_tasks_with_diagnostics(limit).require_complete()

    def get_task_with_diagnostics(self, task_id: str) -> ArtifactReadResult[ToolTask]:
        return self._read_indexed_item(
            table="tool_tasks",
            id_column="task_id",
            artifact_id=task_id,
            sql="SELECT task_id, path FROM tool_tasks WHERE task_id = ?",
            parameters=(task_id,),
            relative_directory="tasks",
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, ToolTask
            ),
        )

    def get_task(self, task_id: str) -> ToolTask | None:
        return self._legacy_item_value(self.get_task_with_diagnostics(task_id))

    def save_result(self, result: ToolResult) -> ToolResult:
        relative_path = f"results/{result.result_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, result.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO tool_results
            (result_id, task_id, tool_id, tool_type, success, validation_status, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.result_id,
                result.task_id,
                result.tool_id,
                result.tool_type.value,
                int(result.success),
                result.validation_status.value,
                saved_path,
                result.created_at_utc.isoformat(),
            ),
        )
        return result

    def list_results_with_diagnostics(
        self, *, tool_id: str | None = None, task_id: str | None = None, limit: int = 20
    ) -> RepositoryReadReport[ToolResult]:
        sql = "SELECT result_id, path FROM tool_results"
        parameters: list[object] = []
        clauses: list[str] = []
        if tool_id:
            clauses.append("tool_id = ?")
            parameters.append(tool_id)
        if task_id:
            clauses.append("task_id = ?")
            parameters.append(task_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at_utc DESC LIMIT ?"
        parameters.append(limit)
        return self._read_indexed_collection(
            table="tool_results",
            id_column="result_id",
            relative_directory="results",
            sql=sql,
            parameters=parameters,
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, ToolResult
            ),
        )

    def list_results(
        self, *, tool_id: str | None = None, task_id: str | None = None, limit: int = 20
    ) -> list[ToolResult]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_results_with_diagnostics(
            tool_id=tool_id, task_id=task_id, limit=limit
        ).require_complete()

    def log_execution(self, *, tool_id: str, task_id: str | None, action_type: str, state: str, payload: dict[str, Any], created_at_utc: str) -> str:
        log_id = str(uuid4())
        relative_path = f"log/{log_id}.json"
        saved_path = self.storage.save_json_atomic(
            relative_path,
            {
                'log_id': log_id,
                'tool_id': tool_id,
                'task_id': task_id,
                'action_type': action_type,
                'state': state,
                'created_at_utc': created_at_utc,
                'payload': payload,
            },
        )
        self.db.execute(
            """
            INSERT INTO tool_execution_log
            (log_id, tool_id, task_id, state, action_type, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (log_id, tool_id, task_id, state, action_type, saved_path, created_at_utc),
        )
        return log_id

    def list_log_with_diagnostics(
        self, *, tool_id: str | None = None, task_id: str | None = None, limit: int = 50
    ) -> RepositoryReadReport[dict[str, Any]]:
        sql = "SELECT log_id, path FROM tool_execution_log"
        parameters: list[object] = []
        clauses: list[str] = []
        if tool_id:
            clauses.append("tool_id = ?")
            parameters.append(tool_id)
        if task_id:
            clauses.append("task_id = ?")
            parameters.append(task_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at_utc DESC LIMIT ?"
        parameters.append(limit)
        return self._read_indexed_collection(
            table="tool_execution_log",
            id_column="log_id",
            relative_directory="log",
            sql=sql,
            parameters=parameters,
            reader=read_json_mapping_from_paths,
        )

    def list_log(
        self, *, tool_id: str | None = None, task_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_log_with_diagnostics(
            tool_id=tool_id, task_id=task_id, limit=limit
        ).require_complete()

    def save_interaction_pattern(self, pattern: InteractionPattern) -> InteractionPattern:
        relative_path = f"interaction_patterns/{pattern.pattern_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, pattern.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO interaction_patterns
            (pattern_id, signature, channel, tool_id, tool_type, site_id, reusable, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern.pattern_id,
                pattern.signature,
                pattern.channel.value,
                pattern.tool_id,
                pattern.tool_type.value,
                pattern.site_id,
                int(pattern.reusable),
                saved_path,
                pattern.updated_at_utc.isoformat(),
            ),
        )
        return pattern

    def get_interaction_pattern_by_signature_with_diagnostics(
        self, signature: str
    ) -> ArtifactReadResult[InteractionPattern]:
        return self._read_indexed_item(
            table="interaction_patterns",
            id_column="pattern_id",
            artifact_id=signature,
            sql="SELECT pattern_id, path FROM interaction_patterns WHERE signature = ?",
            parameters=(signature,),
            relative_directory="interaction_patterns",
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, InteractionPattern
            ),
        )

    def get_interaction_pattern_by_signature(
        self, signature: str
    ) -> InteractionPattern | None:
        return self._legacy_item_value(
            self.get_interaction_pattern_by_signature_with_diagnostics(signature)
        )

    def get_interaction_pattern_with_diagnostics(
        self, pattern_id: str
    ) -> ArtifactReadResult[InteractionPattern]:
        return self._read_indexed_item(
            table="interaction_patterns",
            id_column="pattern_id",
            artifact_id=pattern_id,
            sql="SELECT pattern_id, path FROM interaction_patterns WHERE pattern_id = ?",
            parameters=(pattern_id,),
            relative_directory="interaction_patterns",
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, InteractionPattern
            ),
        )

    def get_interaction_pattern(self, pattern_id: str) -> InteractionPattern | None:
        return self._legacy_item_value(
            self.get_interaction_pattern_with_diagnostics(pattern_id)
        )

    def list_interaction_patterns_with_diagnostics(
        self,
        *,
        channel: str | None = None,
        tool_id: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> RepositoryReadReport[InteractionPattern]:
        sql = "SELECT pattern_id, path FROM interaction_patterns"
        parameters: list[object] = []
        clauses: list[str] = []
        if channel:
            clauses.append("channel = ?")
            parameters.append(channel)
        if tool_id:
            clauses.append("tool_id = ?")
            parameters.append(tool_id)
        if site_id:
            clauses.append("site_id = ?")
            parameters.append(site_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at_utc DESC LIMIT ?"
        parameters.append(limit)
        return self._read_indexed_collection(
            table="interaction_patterns",
            id_column="pattern_id",
            relative_directory="interaction_patterns",
            sql=sql,
            parameters=parameters,
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, InteractionPattern
            ),
        )

    def list_interaction_patterns(
        self,
        *,
        channel: str | None = None,
        tool_id: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[InteractionPattern]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_interaction_patterns_with_diagnostics(
            channel=channel, tool_id=tool_id, site_id=site_id, limit=limit
        ).require_complete()

    def save_interaction_observation(self, observation: InteractionObservation) -> InteractionObservation:
        relative_path = f"interaction_observations/{observation.observation_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, observation.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO interaction_observations
            (observation_id, pattern_id, task_id, result_id, success, channel, tool_id, site_id, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.observation_id,
                observation.pattern_id,
                observation.task_id,
                observation.result_id,
                int(observation.success),
                observation.channel.value,
                observation.tool_id,
                observation.site_id,
                saved_path,
                observation.created_at_utc.isoformat(),
            ),
        )
        return observation

    def list_interaction_observations_with_diagnostics(
        self,
        *,
        pattern_id: str | None = None,
        tool_id: str | None = None,
        limit: int = 20,
    ) -> RepositoryReadReport[InteractionObservation]:
        sql = "SELECT observation_id, path FROM interaction_observations"
        parameters: list[object] = []
        clauses: list[str] = []
        if pattern_id:
            clauses.append("pattern_id = ?")
            parameters.append(pattern_id)
        if tool_id:
            clauses.append("tool_id = ?")
            parameters.append(tool_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at_utc DESC LIMIT ?"
        parameters.append(limit)
        return self._read_indexed_collection(
            table="interaction_observations",
            id_column="observation_id",
            relative_directory="interaction_observations",
            sql=sql,
            parameters=parameters,
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, InteractionObservation
            ),
        )

    def list_interaction_observations(
        self,
        *,
        pattern_id: str | None = None,
        tool_id: str | None = None,
        limit: int = 20,
    ) -> list[InteractionObservation]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_interaction_observations_with_diagnostics(
            pattern_id=pattern_id, tool_id=tool_id, limit=limit
        ).require_complete()

    def save_interaction_episode(self, episode: InteractionEpisode) -> InteractionEpisode:
        episode_relative_path = f"interaction_episodes/{episode.interaction_episode_id}.json"
        episode_saved_path = self.storage.save_json_atomic(episode_relative_path, episode.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO interaction_episodes
            (interaction_episode_id, tool_id, tool_type, mode_used, task_id, result_id, site_id, pattern_id, reused_pattern, path, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode.interaction_episode_id,
                episode.tool_id,
                episode.tool_type.value,
                episode.mode_used.value,
                episode.task_id,
                episode.result_id,
                episode.site_id,
                episode.pattern_id,
                int(episode.reused_pattern),
                episode_saved_path,
                episode.created_at_utc.isoformat(),
                episode.updated_at_utc.isoformat(),
            ),
        )
        for action in episode.actions:
            action_relative_path = f"interaction_actions/{action.action_id}.json"
            action_saved_path = self.storage.save_json_atomic(action_relative_path, action.model_dump(mode='json'))
            created_at = (action.started_at_utc or episode.created_at_utc).isoformat()
            self.db.execute(
                """
                INSERT OR REPLACE INTO interaction_actions
                (action_id, interaction_episode_id, mode_used, operation, target, path, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.action_id,
                    episode.interaction_episode_id,
                    action.channel.value,
                    action.operation,
                    action.target,
                    action_saved_path,
                    created_at,
                ),
            )
        if episode.result is not None:
            result_relative_path = f"interaction_results/{episode.result.interaction_result_id}.json"
            result_saved_path = self.storage.save_json_atomic(result_relative_path, episode.result.model_dump(mode='json'))
            self.db.execute(
                """
                INSERT OR REPLACE INTO interaction_results
                (interaction_result_id, interaction_episode_id, success, confidence, path, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.result.interaction_result_id,
                    episode.interaction_episode_id,
                    int(episode.result.success),
                    float(episode.result.confidence),
                    result_saved_path,
                    episode.updated_at_utc.isoformat(),
                ),
            )
        return episode

    def list_interaction_episodes_with_diagnostics(
        self,
        *,
        tool_id: str | None = None,
        mode_used: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> RepositoryReadReport[InteractionEpisode]:
        sql = "SELECT interaction_episode_id, path FROM interaction_episodes"
        parameters: list[object] = []
        clauses: list[str] = []
        if tool_id:
            clauses.append("tool_id = ?")
            parameters.append(tool_id)
        if mode_used:
            clauses.append("mode_used = ?")
            parameters.append(mode_used)
        if site_id:
            clauses.append("site_id = ?")
            parameters.append(site_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at_utc DESC LIMIT ?"
        parameters.append(limit)
        return self._read_indexed_collection(
            table="interaction_episodes",
            id_column="interaction_episode_id",
            relative_directory="interaction_episodes",
            sql=sql,
            parameters=parameters,
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, InteractionEpisode
            ),
        )

    def list_interaction_episodes(
        self,
        *,
        tool_id: str | None = None,
        mode_used: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[InteractionEpisode]:
        """Legacy list API; fail closed and retain the diagnostic report."""
        return self.list_interaction_episodes_with_diagnostics(
            tool_id=tool_id, mode_used=mode_used, site_id=site_id, limit=limit
        ).require_complete()

    def get_interaction_episode_with_diagnostics(
        self, interaction_episode_id: str
    ) -> ArtifactReadResult[InteractionEpisode]:
        return self._read_indexed_item(
            table="interaction_episodes",
            id_column="interaction_episode_id",
            artifact_id=interaction_episode_id,
            sql=(
                "SELECT interaction_episode_id, path "
                "FROM interaction_episodes WHERE interaction_episode_id = ?"
            ),
            parameters=(interaction_episode_id,),
            relative_directory="interaction_episodes",
            reader=lambda paths, artifact_id: read_model_from_paths(
                paths, artifact_id, InteractionEpisode
            ),
        )

    def get_interaction_episode(
        self, interaction_episode_id: str
    ) -> InteractionEpisode | None:
        return self._legacy_item_value(
            self.get_interaction_episode_with_diagnostics(interaction_episode_id)
        )

    def _load_card(self, tool_id: str, path: str) -> ToolCard:
        return ToolCard.model_validate(self._load_json(f'cards/{tool_id}.json', path))

    def _load_card_safe(self, tool_id: str, path: str) -> ToolCard | None:
        try:
            return self._load_card(tool_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise

    def _load_task(self, task_id: str, path: str) -> ToolTask:
        return ToolTask.model_validate(self._load_json(f'tasks/{task_id}.json', path))

    def _load_task_safe(self, task_id: str, path: str) -> ToolTask | None:
        try:
            return self._load_task(task_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise

    def _load_result(self, result_id: str, path: str) -> ToolResult:
        return ToolResult.model_validate(self._load_json(f'results/{result_id}.json', path))

    def _load_result_safe(self, result_id: str, path: str) -> ToolResult | None:
        try:
            return self._load_result(result_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise

    def _load_interaction_pattern(self, pattern_id: str, path: str) -> InteractionPattern:
        return InteractionPattern.model_validate(self._load_json(f'interaction_patterns/{pattern_id}.json', path))

    def _load_interaction_pattern_safe(self, pattern_id: str, path: str) -> InteractionPattern | None:
        try:
            return self._load_interaction_pattern(pattern_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise

    def _load_interaction_observation(self, observation_id: str, path: str) -> InteractionObservation:
        return InteractionObservation.model_validate(self._load_json(f'interaction_observations/{observation_id}.json', path))

    def _load_interaction_observation_safe(self, observation_id: str, path: str) -> InteractionObservation | None:
        try:
            return self._load_interaction_observation(observation_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise

    def _load_interaction_episode(self, interaction_episode_id: str, path: str) -> InteractionEpisode:
        return InteractionEpisode.model_validate(self._load_json(f'interaction_episodes/{interaction_episode_id}.json', path))

    def _load_interaction_episode_safe(self, interaction_episode_id: str, path: str) -> InteractionEpisode | None:
        try:
            return self._load_interaction_episode(interaction_episode_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise

    def _load_json(self, relative_path: str, path: str) -> dict[str, Any]:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            return json.loads(candidate.read_text(encoding='utf-8'))
        return self.storage.load_json(relative_path)

    def _load_log_safe(self, log_id: str, path: str) -> dict[str, Any] | None:
        try:
            return self._load_json(f'log/{log_id}.json', path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            raise
