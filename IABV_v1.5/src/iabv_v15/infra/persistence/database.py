from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Iterable

logger = logging.getLogger(__name__)

# Default busy timeout in milliseconds.  Gives concurrent processes
# (UI + MCP) time to release the write lock instead of failing
# immediately with ``database is locked``.
_BUSY_TIMEOUT_MS = int(os.environ.get('IABV_SQLITE_BUSY_TIMEOUT_MS', '5000'))


class AppDatabase:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.sqlite_path))
        connection.row_factory = sqlite3.Row
        connection.execute(f'PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}')
        return connection

    def _initialize(self) -> None:
        with self.connect() as conn:
            # WAL mode allows concurrent readers+writer, essential for
            # UI + MCP coexistence.  Disabled in tests via env var to
            # avoid WAL/SHM file cleanup races with shutil.rmtree.
            if os.environ.get('IABV_SQLITE_WAL', '1') == '1':
                try:
                    conn.execute('PRAGMA journal_mode=WAL')
                except Exception:
                    pass
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    step_count INTEGER NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS knowledge_items (
                    knowledge_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    tags_text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_records (
                    run_id TEXT PRIMARY KEY,
                    request_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    route_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    duration_ms INTEGER,
                    error_summary TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS session_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    episode_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    redacted INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS execution_dossiers (
                    dossier_id TEXT PRIMARY KEY,
                    scope_type TEXT NOT NULL,
                    run_id TEXT,
                    episode_id TEXT,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    issue_hint_text TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hidden_incidents (
                    incident_id TEXT PRIMARY KEY,
                    episode_id TEXT,
                    run_id TEXT,
                    site_id TEXT NOT NULL,
                    incident_kind TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_clues (
                    clue_id TEXT PRIMARY KEY,
                    episode_id TEXT,
                    run_id TEXT,
                    linked_incident_id TEXT,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS adaptive_sessions (
                    session_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    status TEXT NOT NULL,
                    intent_key TEXT NOT NULL,
                    pack_id TEXT NOT NULL,
                    site_id TEXT,
                    summary TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS strategy_packs (
                    pack_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    domain_kind TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS capability_snapshots (
                    capability_key TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL,
                    site_id TEXT,
                    status TEXT NOT NULL,
                    score REAL NOT NULL,
                    summary TEXT NOT NULL,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS approval_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    playbook_id TEXT,
                    decision TEXT NOT NULL,
                    phase_key TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS replay_annotations (
                    annotation_id TEXT PRIMARY KEY,
                    episode_id TEXT NOT NULL,
                    step_id TEXT,
                    screenshot_path TEXT NOT NULL,
                    group_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenario_runs (
                    scenario_run_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    session_id TEXT,
                    scenario_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runtime_tuning_profiles (
                    profile_id TEXT PRIMARY KEY,
                    scope_key TEXT NOT NULL,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS codex_pending_issues (
                    issue_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    episode_id TEXT,
                    session_id TEXT,
                    scenario_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_cards (
                    tool_id TEXT PRIMARY KEY,
                    tool_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    adapter_key TEXT NOT NULL,
                    local_first INTEGER NOT NULL DEFAULT 1,
                    available INTEGER NOT NULL DEFAULT 1,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_tasks (
                    task_id TEXT PRIMARY KEY,
                    tool_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by_role TEXT NOT NULL,
                    execution_scope TEXT NOT NULL,
                    approval_decision TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_results (
                    result_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    tool_type TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    validation_status TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_execution_log (
                    log_id TEXT PRIMARY KEY,
                    tool_id TEXT NOT NULL,
                    task_id TEXT,
                    state TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interaction_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    signature TEXT NOT NULL UNIQUE,
                    channel TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    tool_type TEXT NOT NULL,
                    site_id TEXT,
                    reusable INTEGER NOT NULL DEFAULT 1,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interaction_observations (
                    observation_id TEXT PRIMARY KEY,
                    pattern_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    result_id TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    site_id TEXT,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interaction_episodes (
                    interaction_episode_id TEXT PRIMARY KEY,
                    tool_id TEXT NOT NULL,
                    tool_type TEXT NOT NULL,
                    mode_used TEXT NOT NULL,
                    task_id TEXT,
                    result_id TEXT,
                    site_id TEXT,
                    pattern_id TEXT,
                    reused_pattern INTEGER NOT NULL DEFAULT 0,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interaction_actions (
                    action_id TEXT PRIMARY KEY,
                    interaction_episode_id TEXT NOT NULL,
                    mode_used TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    target TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interaction_results (
                    interaction_result_id TEXT PRIMARY KEY,
                    interaction_episode_id TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS objective_nodes (
                    objective_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    parent_id TEXT,
                    root_id TEXT NOT NULL,
                    site_id TEXT,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    progress REAL NOT NULL,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS experiment_runs (
                    run_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    suite_name TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    route TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    score REAL NOT NULL,
                    path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS experiment_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    recommended_route TEXT NOT NULL,
                    score REAL NOT NULL,
                    path TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    chat_session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    meta TEXT NOT NULL DEFAULT '',
                    evidence_tag TEXT NOT NULL DEFAULT '',
                    reasoning_path TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at_utc TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_episodes_updated
                ON episodes (updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_knowledge_items_updated
                ON knowledge_items (updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_run_records_created
                ON run_records (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_session_artifacts_episode
                ON session_artifacts (episode_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_execution_dossiers_created
                ON execution_dossiers (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_execution_dossiers_run
                ON execution_dossiers (run_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_execution_dossiers_episode
                ON execution_dossiers (episode_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_execution_dossiers_issue_hint
                ON execution_dossiers (issue_hint_text, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_hidden_incidents_created
                ON hidden_incidents (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_hidden_incidents_episode
                ON hidden_incidents (episode_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_hidden_incidents_run
                ON hidden_incidents (run_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_hidden_incidents_kind_status
                ON hidden_incidents (incident_kind, status, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_user_clues_created
                ON user_clues (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_user_clues_episode
                ON user_clues (episode_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_user_clues_run
                ON user_clues (run_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_user_clues_incident
                ON user_clues (linked_incident_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_adaptive_sessions_created
                ON adaptive_sessions (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_adaptive_sessions_run
                ON adaptive_sessions (run_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_adaptive_sessions_pack
                ON adaptive_sessions (pack_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_strategy_packs_domain
                ON strategy_packs (domain_kind, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_capability_snapshots_site
                ON capability_snapshots (site_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_capability_snapshots_status
                ON capability_snapshots (status, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_approval_checkpoints_session
                ON approval_checkpoints (session_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_replay_annotations_episode
                ON replay_annotations (episode_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_replay_annotations_step
                ON replay_annotations (step_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_replay_annotations_status
                ON replay_annotations (status, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_scenario_runs_created
                ON scenario_runs (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_scenario_runs_run
                ON scenario_runs (run_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_scenario_runs_session
                ON scenario_runs (session_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_runtime_tuning_scope
                ON runtime_tuning_profiles (scope_key, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_codex_pending_created
                ON codex_pending_issues (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_codex_pending_run
                ON codex_pending_issues (run_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_codex_pending_session
                ON codex_pending_issues (session_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_cards_type
                ON tool_cards (tool_type, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_cards_status
                ON tool_cards (validation_status, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_tasks_tool
                ON tool_tasks (tool_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_tasks_status
                ON tool_tasks (status, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_results_task
                ON tool_results (task_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_results_tool
                ON tool_results (tool_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_log_tool
                ON tool_execution_log (tool_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_tool_log_task
                ON tool_execution_log (task_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_patterns_channel
                ON interaction_patterns (channel, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_patterns_tool
                ON interaction_patterns (tool_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_patterns_site
                ON interaction_patterns (site_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_observations_pattern
                ON interaction_observations (pattern_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_observations_tool
                ON interaction_observations (tool_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_episodes_tool
                ON interaction_episodes (tool_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_episodes_mode
                ON interaction_episodes (mode_used, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_episodes_site
                ON interaction_episodes (site_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_actions_episode
                ON interaction_actions (interaction_episode_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_interaction_results_episode
                ON interaction_results (interaction_episode_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_objective_nodes_root
                ON objective_nodes (root_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_objective_nodes_parent
                ON objective_nodes (parent_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_objective_nodes_kind_status
                ON objective_nodes (kind, status, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_objective_nodes_site
                ON objective_nodes (site_id, updated_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_experiment_runs_subject
                ON experiment_runs (subject_key, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_experiment_runs_domain_route
                ON experiment_runs (domain, route, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_experiment_recommendations_subject
                ON experiment_recommendations (subject_key, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_chat_messages_session
                ON chat_messages (chat_session_id, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_chat_messages_created
                ON chat_messages (created_at_utc DESC);

                CREATE TABLE IF NOT EXISTS integrity_claims (
                    claim_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    invariant TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS verification_events (
                    event_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    checked_at_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verification_evidence TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_integrity_claims_subject
                ON integrity_claims (subject, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_integrity_claims_invariant
                ON integrity_claims (invariant, created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_integrity_claims_created
                ON integrity_claims (created_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_verification_events_claim
                ON verification_events (claim_id, checked_at_utc DESC);

                CREATE INDEX IF NOT EXISTS idx_verification_events_checked
                ON verification_events (checked_at_utc DESC);
                """
            )
            self._ensure_column(conn, 'run_records', 'duration_ms', 'INTEGER')
            self._ensure_column(conn, 'run_records', 'error_summary', "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, 'experiment_runs', 'metadata_json', "TEXT NOT NULL DEFAULT '{}'")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        existing = {row['name'] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column in existing:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def execute(self, sql: str, parameters: Iterable[object] = ()) -> None:
        self._exec_with_retry(lambda conn: conn.execute(sql, tuple(parameters)))

    def fetchall(self, sql: str, parameters: Iterable[object] = ()) -> list[sqlite3.Row]:
        return self._query_with_retry(
            lambda conn: list(conn.execute(sql, tuple(parameters)).fetchall()),
        )

    def fetchone(self, sql: str, parameters: Iterable[object] = ()) -> sqlite3.Row | None:
        return self._query_with_retry(
            lambda conn: conn.execute(sql, tuple(parameters)).fetchone(),
        )

    def _exec_with_retry(
        self,
        fn,
        *,
        max_retries: int = 3,
        backoff_base: float = 0.25,
    ) -> None:
        """Execute *fn(conn)* with retry on ``database is locked``."""
        self._query_with_retry(fn, max_retries=max_retries, backoff_base=backoff_base)

    def _query_with_retry(
        self,
        fn,
        *,
        max_retries: int = 3,
        backoff_base: float = 0.25,
    ):
        """Execute *fn(conn)* with retry on ``database is locked``.

        Returns whatever *fn* returns.  Used by both write (execute) and
        read (fetchall/fetchone) paths so that concurrent UI + MCP
        startup doesn't fail reads either.
        """
        for attempt in range(max_retries + 1):
            try:
                with self.connect() as conn:
                    return fn(conn)
            except sqlite3.OperationalError as exc:
                if 'database is locked' not in str(exc) or attempt >= max_retries:
                    raise
                wait = backoff_base * (2 ** attempt)
                logger.warning(
                    'database_locked_retry: attempt=%d/%d wait=%.2fs sql_preview=%s',
                    attempt + 1, max_retries, wait, str(fn)[:80],
                )
                time.sleep(wait)
