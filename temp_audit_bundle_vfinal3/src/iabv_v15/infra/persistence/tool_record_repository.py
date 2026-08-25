from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import InteractionEpisode, InteractionObservation, InteractionPattern, ToolCard, ToolResult, ToolTask
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ToolRecordRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

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

    def list_cards(self) -> list[ToolCard]:
        rows = self.db.fetchall(
            """
            SELECT tool_id, path
            FROM tool_cards
            ORDER BY updated_at_utc DESC, title ASC
            """
        )
        cards: list[ToolCard] = []
        for row in rows:
            card = self._load_card_safe(row['tool_id'], row['path'])
            if card is not None:
                cards.append(card)
        return cards

    def get_card(self, tool_id: str) -> ToolCard | None:
        row = self.db.fetchone(
            """
            SELECT tool_id, path
            FROM tool_cards
            WHERE tool_id = ?
            """,
            (tool_id,),
        )
        if row is None:
            return None
        return self._load_card_safe(row['tool_id'], row['path'])

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

    def list_tasks(self, limit: int = 20) -> list[ToolTask]:
        rows = self.db.fetchall(
            """
            SELECT task_id, path
            FROM tool_tasks
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        items: list[ToolTask] = []
        for row in rows:
            loaded = self._load_task_safe(row['task_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def get_task(self, task_id: str) -> ToolTask | None:
        row = self.db.fetchone(
            """
            SELECT task_id, path
            FROM tool_tasks
            WHERE task_id = ?
            """,
            (task_id,),
        )
        if row is None:
            return None
        return self._load_task_safe(row['task_id'], row['path'])

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

    def list_results(self, *, tool_id: str | None = None, task_id: str | None = None, limit: int = 20) -> list[ToolResult]:
        sql = "SELECT result_id, path FROM tool_results"
        parameters: list[object] = []
        clauses: list[str] = []
        if tool_id:
            clauses.append('tool_id = ?')
            parameters.append(tool_id)
        if task_id:
            clauses.append('task_id = ?')
            parameters.append(task_id)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY created_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        items: list[ToolResult] = []
        for row in rows:
            loaded = self._load_result_safe(row['result_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

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

    def list_log(self, *, tool_id: str | None = None, task_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        sql = 'SELECT log_id, path FROM tool_execution_log'
        parameters: list[object] = []
        clauses: list[str] = []
        if tool_id:
            clauses.append('tool_id = ?')
            parameters.append(tool_id)
        if task_id:
            clauses.append('task_id = ?')
            parameters.append(task_id)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY created_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        items: list[dict[str, Any]] = []
        for row in rows:
            loaded = self._load_log_safe(row['log_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items


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

    def get_interaction_pattern_by_signature(self, signature: str) -> InteractionPattern | None:
        row = self.db.fetchone(
            """
            SELECT pattern_id, path
            FROM interaction_patterns
            WHERE signature = ?
            """,
            (signature,),
        )
        if row is None:
            return None
        return self._load_interaction_pattern_safe(row['pattern_id'], row['path'])

    def get_interaction_pattern(self, pattern_id: str) -> InteractionPattern | None:
        row = self.db.fetchone(
            """
            SELECT pattern_id, path
            FROM interaction_patterns
            WHERE pattern_id = ?
            """,
            (pattern_id,),
        )
        if row is None:
            return None
        return self._load_interaction_pattern_safe(row['pattern_id'], row['path'])

    def list_interaction_patterns(
        self,
        *,
        channel: str | None = None,
        tool_id: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[InteractionPattern]:
        sql = 'SELECT pattern_id, path FROM interaction_patterns'
        parameters: list[object] = []
        clauses: list[str] = []
        if channel:
            clauses.append('channel = ?')
            parameters.append(channel)
        if tool_id:
            clauses.append('tool_id = ?')
            parameters.append(tool_id)
        if site_id:
            clauses.append('site_id = ?')
            parameters.append(site_id)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY updated_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        items: list[InteractionPattern] = []
        for row in rows:
            loaded = self._load_interaction_pattern_safe(row['pattern_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

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

    def list_interaction_observations(
        self,
        *,
        pattern_id: str | None = None,
        tool_id: str | None = None,
        limit: int = 20,
    ) -> list[InteractionObservation]:
        sql = 'SELECT observation_id, path FROM interaction_observations'
        parameters: list[object] = []
        clauses: list[str] = []
        if pattern_id:
            clauses.append('pattern_id = ?')
            parameters.append(pattern_id)
        if tool_id:
            clauses.append('tool_id = ?')
            parameters.append(tool_id)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY created_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        items: list[InteractionObservation] = []
        for row in rows:
            loaded = self._load_interaction_observation_safe(row['observation_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

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

    def list_interaction_episodes(
        self,
        *,
        tool_id: str | None = None,
        mode_used: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[InteractionEpisode]:
        sql = 'SELECT interaction_episode_id, path FROM interaction_episodes'
        parameters: list[object] = []
        clauses: list[str] = []
        if tool_id:
            clauses.append('tool_id = ?')
            parameters.append(tool_id)
        if mode_used:
            clauses.append('mode_used = ?')
            parameters.append(mode_used)
        if site_id:
            clauses.append('site_id = ?')
            parameters.append(site_id)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY updated_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        items: list[InteractionEpisode] = []
        for row in rows:
            loaded = self._load_interaction_episode_safe(row['interaction_episode_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def get_interaction_episode(self, interaction_episode_id: str) -> InteractionEpisode | None:
        row = self.db.fetchone(
            """
            SELECT interaction_episode_id, path
            FROM interaction_episodes
            WHERE interaction_episode_id = ?
            """,
            (interaction_episode_id,),
        )
        if row is None:
            return None
        return self._load_interaction_episode(row['interaction_episode_id'], row['path'])

    def _load_card(self, tool_id: str, path: str) -> ToolCard:
        return ToolCard.model_validate(self._load_json(f'cards/{tool_id}.json', path))

    def _load_card_safe(self, tool_id: str, path: str) -> ToolCard | None:
        try:
            return self._load_card(tool_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM tool_cards WHERE tool_id = ?', (tool_id,))
            return None

    def _load_task(self, task_id: str, path: str) -> ToolTask:
        return ToolTask.model_validate(self._load_json(f'tasks/{task_id}.json', path))

    def _load_task_safe(self, task_id: str, path: str) -> ToolTask | None:
        try:
            return self._load_task(task_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM tool_tasks WHERE task_id = ?', (task_id,))
            return None

    def _load_result(self, result_id: str, path: str) -> ToolResult:
        return ToolResult.model_validate(self._load_json(f'results/{result_id}.json', path))

    def _load_result_safe(self, result_id: str, path: str) -> ToolResult | None:
        try:
            return self._load_result(result_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM tool_results WHERE result_id = ?', (result_id,))
            return None

    def _load_interaction_pattern(self, pattern_id: str, path: str) -> InteractionPattern:
        return InteractionPattern.model_validate(self._load_json(f'interaction_patterns/{pattern_id}.json', path))

    def _load_interaction_pattern_safe(self, pattern_id: str, path: str) -> InteractionPattern | None:
        try:
            return self._load_interaction_pattern(pattern_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM interaction_patterns WHERE pattern_id = ?', (pattern_id,))
            return None

    def _load_interaction_observation(self, observation_id: str, path: str) -> InteractionObservation:
        return InteractionObservation.model_validate(self._load_json(f'interaction_observations/{observation_id}.json', path))

    def _load_interaction_observation_safe(self, observation_id: str, path: str) -> InteractionObservation | None:
        try:
            return self._load_interaction_observation(observation_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM interaction_observations WHERE observation_id = ?', (observation_id,))
            return None

    def _load_interaction_episode(self, interaction_episode_id: str, path: str) -> InteractionEpisode:
        return InteractionEpisode.model_validate(self._load_json(f'interaction_episodes/{interaction_episode_id}.json', path))

    def _load_interaction_episode_safe(self, interaction_episode_id: str, path: str) -> InteractionEpisode | None:
        try:
            return self._load_interaction_episode(interaction_episode_id, path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM interaction_episodes WHERE interaction_episode_id = ?', (interaction_episode_id,))
            return None

    def _load_json(self, relative_path: str, path: str) -> dict[str, Any]:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            return json.loads(candidate.read_text(encoding='utf-8'))
        return self.storage.load_json(relative_path)

    def _load_log_safe(self, log_id: str, path: str) -> dict[str, Any] | None:
        try:
            return self._load_json(f'log/{log_id}.json', path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.db.execute('DELETE FROM tool_execution_log WHERE log_id = ?', (log_id,))
            return None
