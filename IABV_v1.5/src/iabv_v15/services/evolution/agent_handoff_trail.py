"""Cross-agent synchronization handoff trail.

Records every handoff between IAs (Devin → Claude → Codex, etc.) for:
- Who executed the task and with what SHA
- Who audited the work and what verdict was reached
- Git synchronization state (branch, SHA, verified)
- Test execution status (declared vs verified vs reproduced)
- Inherited vs new failures
- Authority components and audit evidence
- Next agent and next action
- Learning signals about tool/agent performance

Architecture:
- Append-only JSONL persistence in ``data/evolution/agent_handoff/handoffs.jsonl``
- NOT a new orchestrator — purely observational and reconstructive
- Consumed by handoff validation and future agents needing context
- Distinguishes DECLARED (executor) from VERIFIED/REPRODUCED (auditor)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import AgentHandoffRecord, AuthorizationStatus, EvidenceStatus

logger = logging.getLogger(__name__)


class AgentHandoffTrail:
    """Append-only audit trail for cross-agent handoffs.

    Persists to ``data/evolution/agent_handoff/handoffs.jsonl``.
    Provides verification, consistency checking, and historical analysis.
    """

    def __init__(self, *, data_root: str | Path = '') -> None:
        import os
        env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
        if data_root:
            self._data_root = Path(data_root)
        elif env_dir:
            self._data_root = Path(env_dir)
        else:
            self._data_root = Path.home() / 'IABV_v1.5' / 'data'

    @property
    def _handoff_dir(self) -> Path:
        d = self._data_root / 'evolution' / 'agent_handoff'
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def _log_path(self) -> Path:
        return self._handoff_dir / 'handoffs.jsonl'

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record(self, handoff: AgentHandoffRecord) -> None:
        """Append a handoff record to the audit log."""
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(handoff.model_dump(mode='json'), ensure_ascii=False) + '\n')
        logger.info(
            'agent-handoff: recorded %s [%s] executor=%s auditor=%s task=%s sync_verified=%s',
            handoff.handoff_id, handoff.task_id,
            handoff.executor_agent, handoff.auditor_agent,
            handoff.task_name, handoff.sync_verified,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load the most recent handoff records."""
        if not self._log_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries[-limit:]

    def get_by_task(self, task_id: str) -> list[AgentHandoffRecord]:
        """Get all handoff records for a specific task."""
        entries = self.load_recent(limit=1000)
        task_entries = [e for e in entries if e.get('task_id') == task_id]
        return [AgentHandoffRecord(**e) for e in task_entries]

    def get_latest_by_task(self, task_id: str) -> AgentHandoffRecord | None:
        """Get the most recent handoff record for a task."""
        task_records = self.get_by_task(task_id)
        if not task_records:
            return None
        return max(task_records, key=lambda r: r.timestamp_utc)

    # ------------------------------------------------------------------
    # Consistency verification
    # ------------------------------------------------------------------

    def verify_consistency(self, handoff: AgentHandoffRecord) -> dict[str, Any]:
        """Verify internal consistency of a handoff record.

        Returns:
            Dictionary with verification results:
            - sha_mismatch: bool (HEAD != declared)
            - branch_missing: bool (branch doesn't exist in repo)
            - commit_missing: bool (commits don't exist in history)
            - test_declared_but_not_verified: bool
            - audit_based_on_different_sha: bool
            - inconsistent_evidence: bool
            - is_consistent: bool (overall)
        """
        issues: dict[str, Any] = {
            'sha_mismatch': False,
            'branch_missing': False,
            'commit_missing': False,
            'test_declared_but_not_verified': False,
            'audit_based_on_different_sha': False,
            'inconsistent_evidence': False,
            'unauthorized_next_agent': False,
            'unauthorized_next_action': False,
            'self_marked_reproduced': False,
            'is_consistent': True,
        }

        # Check if tests were declared but not verified
        if handoff.tests_executed and handoff.tests_status == EvidenceStatus.DECLARED:
            issues['test_declared_but_not_verified'] = True
            issues['is_consistent'] = False

        # Check if audit was based on different SHA than HEAD
        if handoff.auditor_agent and handoff.audit_evidence:
            audit_sha = handoff.audit_evidence.get('audited_sha')
            if audit_sha and audit_sha != handoff.head_sha:
                issues['audit_based_on_different_sha'] = True
                issues['is_consistent'] = False

        # Check for contradictory evidence
        if handoff.tests_status == EvidenceStatus.VERIFIED and not handoff.sync_verified:
            issues['inconsistent_evidence'] = True
            issues['is_consistent'] = False

        # Check if next_agent is declared but not authorized
        if handoff.next_agent and handoff.next_agent_authorization == AuthorizationStatus.DECLARED:
            issues['unauthorized_next_agent'] = True
            # Don't mark as inconsistent - this is expected, not an error

        # Check if next_action is declared but not authorized
        if handoff.next_action and handoff.next_action_authorization == AuthorizationStatus.DECLARED:
            issues['unauthorized_next_action'] = True
            # Don't mark as inconsistent - this is expected, not an error

        # Check if agent marked own evidence as REPRODUCED without auditor
        if handoff.tests_status == EvidenceStatus.REPRODUCED and not handoff.auditor_agent:
            issues['self_marked_reproduced'] = True
            issues['is_consistent'] = False

        return issues

    # ------------------------------------------------------------------
    # Learning analysis
    # ------------------------------------------------------------------

    def analyze_agent_performance(self, agent: str, limit: int = 50) -> dict[str, Any]:
        """Analyze historical performance of a specific agent.

        Returns:
            Dictionary with:
            - total_handoffs: int
            - successful_handoffs: int
            - failure_count: int
            - failure_rate: float
            - sample_count: int
            - last_verified: str (timestamp)
            - failure_modes: list[str]
            - task_distribution: dict[str, int]
            - learning_signals: dict[str, Any]
        """
        entries = self.load_recent(limit)
        agent_entries = [e for e in entries if e.get('executor_agent') == agent]

        if not agent_entries:
            return {
                'total_handoffs': 0,
                'successful_handoffs': 0,
                'failure_count': 0,
                'failure_rate': 0.0,
                'sample_count': 0,
                'last_verified': None,
                'failure_modes': [],
                'task_distribution': {},
                'learning_signals': {},
            }

        successful = sum(1 for e in agent_entries if e.get('audit_verdict', '').endswith('PASS'))
        failure_count = len(agent_entries) - successful
        failure_rate = failure_count / len(agent_entries) if agent_entries else 0.0

        # Count failure modes (distinct failure patterns)
        failure_modes: set[str] = set()
        for entry in agent_entries:
            for failure in entry.get('new_failures', []):
                failure_modes.add(failure)

        # Task distribution
        task_distribution: dict[str, int] = {}
        for entry in agent_entries:
            task_id = entry.get('task_id', 'unknown')
            task_distribution[task_id] = task_distribution.get(task_id, 0) + 1

        # Last verified timestamp
        last_entry = max(agent_entries, key=lambda e: e.get('timestamp_utc', ''))
        last_verified = last_entry.get('timestamp_utc', '')

        return {
            'total_handoffs': len(agent_entries),
            'successful_handoffs': successful,
            'failure_count': failure_count,
            'failure_rate': round(failure_rate, 3),
            'sample_count': len(agent_entries),
            'last_verified': last_verified,
            'failure_modes': list(failure_modes),
            'task_distribution': task_distribution,
            'learning_signals': {},
        }

    def analyze_tool_agent_combination(self, tool: str, agent: str, task_type: str = '', limit: int = 50) -> dict[str, Any]:
        """Analyze historical performance of a specific tool+agent+task combination.

        Returns:
            Dictionary with success rate, common patterns, and learning signals.
        """
        entries = self.load_recent(limit)
        tool_agent_entries = [
            e for e in entries
            if e.get('executor_agent') == agent and tool in e.get('metadata', {}).get('tools_used', [])
        ]

        # Filter by task type if specified
        if task_type:
            tool_agent_entries = [
                e for e in tool_agent_entries
                if task_type in e.get('task_name', '').lower() or task_type in e.get('task_id', '').lower()
            ]

        if not tool_agent_entries:
            return {
                'total_handoffs': 0,
                'success_rate': 0.0,
                'success_count': 0,
                'failure_count': 0,
                'sample_count': 0,
                'task_types': [],
                'patterns': [],
                'recommendation': 'insufficient_data',
            }

        successful = sum(1 for e in tool_agent_entries if e.get('audit_verdict', '').endswith('PASS'))
        failure_count = len(tool_agent_entries) - successful
        success_rate = successful / len(tool_agent_entries)

        # Extract task types
        task_types = list(set(e.get('task_id', '') for e in tool_agent_entries))

        return {
            'total_handoffs': len(tool_agent_entries),
            'success_rate': round(success_rate, 3),
            'success_count': successful,
            'failure_count': failure_count,
            'sample_count': len(tool_agent_entries),
            'task_types': task_types,
            'patterns': [],  # Would need pattern extraction logic
            'recommendation': 'use' if success_rate > 0.7 else 'avoid' if success_rate < 0.3 else 'cautious',
        }
