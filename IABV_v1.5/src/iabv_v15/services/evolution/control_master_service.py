"""ControlMasterService: single source of truth for governance state.

Composes (does not duplicate) existing pieces:

- Objectives live in ``ObjectiveRepository``; the service only tracks
  their ids and projects their status into ``ControlMasterState``.
- Backlog items are projected from ``PendingIssueRepository``.
- Current risks are projected from ``OperationalSelfExaminationService``.
- Rules and decisions are the only first-class governance artifacts that
  this service persists via ``ControlMasterRepository``.

The service is deliberately small: each mutation is explicit (no magic
auto-updates), and every projection is rebuilt on read so the state
never drifts from live repositories.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ControlMasterState,
    ControlRule,
    ControlRuleSeverity,
    ControlRuleStatus,
    ObjectiveNode,
    ObjectiveStatus,
    utc_now,
)
from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository


_DISCARDED_TAG = "discarded"
_UNRESOLVED_TAG = "unresolved"


class ControlMasterService:
    """Governance-layer service built on top of existing evolution infra."""

    def __init__(
        self,
        *,
        repository: ControlMasterRepository,
        objective_repository: Any | None = None,
        pending_issue_repository: Any | None = None,
        self_examination_service: Any | None = None,
        experiment_lab_repository: Any | None = None,
        account_resource_scanner: Any | None = None,
        platform_pending_queue: Any | None = None,
        workspace_root: str | None = None,
        recent_decisions_limit: int = 10,
    ) -> None:
        self.repository = repository
        self.objective_repository = objective_repository
        self.pending_issue_repository = pending_issue_repository
        self.self_examination_service = self_examination_service
        self.experiment_lab_repository = experiment_lab_repository
        self.account_resource_scanner = account_resource_scanner
        self.platform_pending_queue = platform_pending_queue
        self.workspace_root = workspace_root
        self.recent_decisions_limit = recent_decisions_limit

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def current_state(self, *, refresh: bool = False) -> ControlMasterState:
        base = self.repository.load_latest_state() if not refresh else None
        if base is None:
            base = ControlMasterState()
        rules = self.repository.list_rules()
        decisions = sorted(
            self.repository.list_decisions(),
            key=lambda d: d.timestamp,
            reverse=True,
        )[: self.recent_decisions_limit]
        objective_buckets = self._project_objective_buckets()
        backlog = self._project_backlog()
        risks = self._project_risks()
        account_inventory = self._project_account_inventory()
        unresolved = list(dict.fromkeys([
            *base.unresolved_items,
            *self._project_unresolved(),
            *account_inventory.get('unresolved_items', []),
        ]))
        metadata = dict(base.metadata)
        metadata['account_inventory'] = account_inventory
        state = base.model_copy(
            update={
                "global_rules": rules,
                "recent_decisions": decisions,
                "active_objective_ids": objective_buckets["active"],
                "completed_objective_ids": objective_buckets["completed"],
                "paused_objective_ids": objective_buckets["paused"],
                "discarded_objective_ids": objective_buckets["discarded"],
                "technical_backlog": backlog,
                "current_risks": risks,
                "unresolved_items": unresolved,
                "metadata": metadata,
                "last_updated": utc_now(),
            }
        )
        return state

    def save_state(self, state: ControlMasterState) -> ControlMasterState:
        return self.repository.save_state(state)

    def get_rule(self, rule_id: str) -> ControlRule | None:
        return self.repository.get_rule(rule_id)

    def get_decision(self, decision_id: str) -> ControlDecision | None:
        return self.repository.get_decision(decision_id)

    # ------------------------------------------------------------------
    # Write API (explicit)
    # ------------------------------------------------------------------

    def set_vision(self, vision: str, *, evidence: list[str] | None = None) -> ControlMasterState:
        state = self.current_state()
        new_evidence = list(dict.fromkeys([*state.evidence_links, *(evidence or [])]))
        updated = state.model_copy(
            update={
                "current_vision": vision,
                "evidence_links": new_evidence,
                "last_updated": utc_now(),
            }
        )
        return self.save_state(updated)

    def upsert_rule(self, rule: ControlRule) -> ControlRule:
        existing = self.repository.get_rule(rule.rule_id)
        if existing is not None:
            rule = rule.model_copy(
                update={
                    "created_at_utc": existing.created_at_utc,
                    "updated_at_utc": utc_now(),
                }
            )
        return self.repository.upsert_rule(rule)

    def record_decision(self, decision: ControlDecision) -> ControlDecision:
        return self.repository.record_decision(decision)

    def mark_objective(
        self,
        objective_id: str,
        status: str,
        *,
        note: str = "",
    ) -> ObjectiveNode | None:
        if self.objective_repository is None:
            return None
        node = self.objective_repository.get(objective_id)
        if node is None:
            return None
        updates: dict[str, Any] = {"updated_at_utc": utc_now()}
        normalized = status.lower()
        if normalized == "discarded":
            # ObjectiveStatus has no DISCARDED; tag it instead to preserve
            # backwards compatibility with existing objective JSONs.
            tags = list(dict.fromkeys([*node.tags, _DISCARDED_TAG]))
            updates["tags"] = tags
            updates["status"] = ObjectiveStatus.PAUSED
        else:
            try:
                updates["status"] = ObjectiveStatus(normalized)
            except ValueError:
                return None
        if note:
            metadata = dict(node.metadata)
            notes = list(metadata.get("control_master_notes", []))
            notes.append({"note": note, "at": updates["updated_at_utc"].isoformat()})
            metadata["control_master_notes"] = notes
            updates["metadata"] = metadata
        updated = node.model_copy(update=updates)
        saved = self.objective_repository.save(updated)
        if saved.status == ObjectiveStatus.COMPLETED and saved.parent_id:
            self._auto_close_ancestors_if_children_done(saved.parent_id, {saved.objective_id})
        return saved

    def _auto_close_ancestors_if_children_done(
        self,
        parent_id: str,
        visited: set[str],
    ) -> None:
        """Close ancestor objectives whose direct children are all completed.

        Walks up via ``parent_id``. Only auto-closes if:
        - the repository exposes ``list_children`` (legacy repos are no-ops);
        - the parent is currently ACTIVE (terminal/blocked/paused ancestors
          are left alone — the user made that decision explicitly);
        - every direct child is ``COMPLETED`` (blocked/paused/pending/
          discarded children mean the parent is not fully done).

        Ancestors discarded via the ``discarded`` tag are skipped: their
        PAUSED status reflects a user decision and must not be overridden.

        The ``visited`` set is threaded through direct recursion (not
        re-entry via ``mark_objective``) so cycles in ``parent_id`` never
        cause unbounded recursion even if the ACTIVE-only guard is ever
        weakened.
        """

        if self.objective_repository is None:
            return
        if parent_id in visited:
            return
        visited.add(parent_id)
        list_children = getattr(self.objective_repository, "list_children", None)
        if list_children is None:
            return
        parent = self.objective_repository.get(parent_id)
        if parent is None or parent.status != ObjectiveStatus.ACTIVE:
            return
        try:
            # Explicit large limit: the default list_children limit (40)
            # is a display cap in ObjectiveRepository, but here we need
            # to see *every* child — missing any uncompleted sibling would
            # incorrectly auto-close the parent.
            children = list_children(parent_id, limit=10_000)
        except TypeError:
            # Legacy embedders whose list_children does not accept limit.
            try:
                children = list_children(parent_id)
            except Exception:
                return
        except Exception:
            return
        if not children:
            return
        if any(child.status != ObjectiveStatus.COMPLETED for child in children):
            return
        # All children are completed → close the parent in place with an
        # audit note and recurse directly (keeping the same ``visited``
        # set) so cycle protection survives the whole chain.
        now = utc_now()
        note = f"auto-closed: all {len(children)} children completed"
        metadata = dict(parent.metadata)
        notes = list(metadata.get("control_master_notes", []))
        notes.append({"note": note, "at": now.isoformat()})
        metadata["control_master_notes"] = notes
        closed = parent.model_copy(
            update={
                "status": ObjectiveStatus.COMPLETED,
                "metadata": metadata,
                "updated_at_utc": now,
            }
        )
        self.objective_repository.save(closed)
        if closed.parent_id:
            self._auto_close_ancestors_if_children_done(closed.parent_id, visited)

    def mark_unresolved(self, item: str, *, evidence: list[str] | None = None) -> ControlMasterState:
        item_clean = item.strip()
        if not item_clean:
            return self.current_state()
        state = self.current_state()
        unresolved = list(dict.fromkeys([*state.unresolved_items, item_clean]))
        new_evidence = list(dict.fromkeys([*state.evidence_links, *(evidence or [])]))
        updated = state.model_copy(
            update={
                "unresolved_items": unresolved,
                "evidence_links": new_evidence,
                "last_updated": utc_now(),
            }
        )
        return self.save_state(updated)

    def record_tests_state(self, summary: dict[str, Any]) -> ControlMasterState:
        state = self.current_state()
        updated = state.model_copy(
            update={
                "current_tests_state": dict(summary),
                "last_updated": utc_now(),
            }
        )
        return self.save_state(updated)

    # ------------------------------------------------------------------
    # Canonical work queue projection
    # ------------------------------------------------------------------

    def current_work_queue(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Project a unified, prioritised work queue from all live sources.

        Combines objectives, platform pending tasks, pending issues,
        OSES findings (HIGH/CRITICAL), and failed/stalled interaction
        episodes from ``runtime_audit.jsonl``.  Each item carries a
        deterministic ``priority_score`` with ``score_breakdown``.

        COMPLETED items are excluded.  Projection is idempotent.
        """
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        # 1. Objectives (active, pending, blocked)
        items.extend(self._project_objective_queue_items(seen_ids))

        # 2. Platform pending tasks (non-COMPLETED)
        items.extend(self._project_platform_pending_items(seen_ids))

        # 3. Pending issues
        items.extend(self._project_pending_issue_items(seen_ids))

        # 4. OSES findings (HIGH/CRITICAL only)
        items.extend(self._project_oses_finding_items(seen_ids))

        # 5. Failed/stalled interaction episodes from runtime_audit
        items.extend(self._project_runtime_audit_items(seen_ids))

        # 6. Tests state
        state = self.current_state()
        ts = state.current_tests_state
        if ts and ts.get('failed', 0) > 0:
            tid = 'tests:failing'
            if tid not in seen_ids:
                seen_ids.add(tid)
                items.append(self._make_item(
                    item_id=tid,
                    title=f"Tests failing: {ts.get('failed')} of {ts.get('total', '?')}",
                    status='needs_fix',
                    source='tests_state',
                    evidence_refs=[],
                    next_action='Fix failing tests before merging',
                    score_components={'test_failure': 70, 'base': 10},
                ))

        # Score and sort
        for item in items:
            components = item.get('score_breakdown', {})
            item['priority_score'] = sum(components.values())
            item['priority_label'] = _score_to_label(item['priority_score'])
        items.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        return items[:limit]

    def _make_item(
        self,
        *,
        item_id: str,
        title: str,
        status: str,
        source: str,
        evidence_refs: list[str],
        next_action: str,
        score_components: dict[str, int],
        acceptance_tests: list[str] | None = None,
        dependencies: str = '',
        parallelizable: bool = True,
        updated_at: str = '',
        reason: str = '',
    ) -> dict[str, Any]:
        return {
            'id': item_id,
            'title': title,
            'status': status,
            'priority_score': 0,
            'priority_label': '',
            'source': source,
            'evidence_refs': evidence_refs,
            'next_action': next_action,
            'acceptance_tests': list(acceptance_tests or []),
            'dependencies': dependencies,
            'parallelizable': parallelizable,
            'updated_at': updated_at or utc_now().isoformat(),
            'reason': reason,
            'score_breakdown': dict(score_components),
        }

    def _project_objective_queue_items(
        self, seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        if self.objective_repository is None:
            return []
        items: list[dict[str, Any]] = []
        for status_val in (ObjectiveStatus.ACTIVE, ObjectiveStatus.PENDING, ObjectiveStatus.BLOCKED):
            try:
                nodes = self.objective_repository.list_recent(status=status_val, limit=20)
            except Exception:
                continue
            for node in nodes:
                oid = f'objective:{node.objective_id}'
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)
                score: dict[str, int] = {'base': 20}
                if node.priority >= 80:
                    score['high_priority'] = 30
                elif node.priority >= 60:
                    score['medium_priority'] = 15
                if status_val == ObjectiveStatus.BLOCKED:
                    score['blocked'] = 20
                items.append(self._make_item(
                    item_id=oid,
                    title=node.title,
                    status=status_val.value,
                    source='objective_repository',
                    evidence_refs=list(node.evidence_refs or []),
                    next_action=node.blocker if node.blocker else 'Continue work',
                    score_components=score,
                    dependencies=node.blocker,
                    parallelizable=not bool(node.blocker),
                    updated_at=node.updated_at_utc.isoformat(),
                    reason=node.summary,
                ))
        return items

    def _project_platform_pending_items(
        self, seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        queue = self.platform_pending_queue
        if queue is None:
            return []
        items: list[dict[str, Any]] = []
        try:
            from iabv_v15.domain.models import PendingTaskStatus as _PTS
            all_tasks = queue.list_all() if hasattr(queue, 'list_all') else []
        except Exception:
            return []
        for task in all_tasks:
            if task.status == _PTS.COMPLETED:
                continue
            tid = f'platform:{task.id}'
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            score: dict[str, int] = {'base': 15}
            prio_map = {'critical': 50, 'high': 30, 'medium': 15, 'low': 5}
            score['priority'] = prio_map.get(task.priority, 10)
            if task.status == _PTS.BLOCKED:
                score['blocked'] = 15
            items.append(self._make_item(
                item_id=tid,
                title=task.title,
                status=task.status.value,
                source='platform_pending_queue',
                evidence_refs=[],
                next_action=task.next_action or task.resume_hint or 'Investigate',
                score_components=score,
                dependencies=task.dependency_missing,
                parallelizable=task.status != _PTS.BLOCKED,
                updated_at=task.updated_at.isoformat(),
                reason=task.reason or task.description,
            ))
        return items

    def _project_pending_issue_items(
        self, seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        if self.pending_issue_repository is None:
            return []
        items: list[dict[str, Any]] = []
        candidates: list[Any] = []
        for method_name in ('list_recent', 'list_open', 'list_pending', 'list_all'):
            method = getattr(self.pending_issue_repository, method_name, None)
            if method is None:
                continue
            try:
                candidates = list(method())
                break
            except Exception:
                continue
        for issue in candidates[:15]:
            iid = f'issue:{getattr(issue, "issue_id", "") or id(issue)}'
            if iid in seen_ids:
                continue
            seen_ids.add(iid)
            score: dict[str, int] = {'base': 25}
            summary = getattr(issue, 'summary', '') or ''
            lower_summary = summary.lower()
            if any(k in lower_summary for k in ('startup', 'freeze', 'crash', 'stall')):
                score['user_impact'] = 40
            if any(k in lower_summary for k in ('memory', 'rss', 'oom')):
                score['memory_critical'] = 35
            items.append(self._make_item(
                item_id=iid,
                title=summary[:120] or 'Pending issue',
                status=getattr(issue, 'status', 'needs_fix'),
                source='pending_issue_repository',
                evidence_refs=list(getattr(issue, 'evidence_refs', []) or []),
                next_action=getattr(issue, 'recommended_change', '') or 'Investigate',
                score_components=score,
                updated_at=getattr(issue, 'created_at_utc', utc_now()).isoformat()
                if hasattr(getattr(issue, 'created_at_utc', None), 'isoformat')
                else '',
                reason=getattr(issue, 'probable_cause', '') or '',
            ))
        return items

    def _project_oses_finding_items(
        self, seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        if self.self_examination_service is None:
            return []
        snapshot = None
        for method_name in ('current_snapshot', 'latest_snapshot', 'current', 'latest'):
            method = getattr(self.self_examination_service, method_name, None)
            if method is None:
                continue
            try:
                snapshot = method()
                break
            except Exception:
                continue
        if snapshot is None:
            return []
        findings = getattr(snapshot, 'findings', None) or []
        items: list[dict[str, Any]] = []
        for finding in findings:
            sev = getattr(finding, 'severity', None)
            if sev is None:
                continue
            sev_val = sev.value if hasattr(sev, 'value') else str(sev)
            if sev_val not in ('high', 'critical'):
                continue
            fid = f'oses:{getattr(finding, "finding_id", "") or getattr(finding, "category", "")}'
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            score: dict[str, int] = {'base': 30}
            if sev_val == 'critical':
                score['critical_severity'] = 50
            elif sev_val == 'high':
                score['high_severity'] = 30
            title_lower = (getattr(finding, 'title', '') or '').lower()
            if any(k in title_lower for k in ('startup', 'freeze', 'stall', 'event_loop')):
                score['startup_impact'] = 25
            if any(k in title_lower for k in ('memory', 'rss', 'oom')):
                score['memory_impact'] = 25
            items.append(self._make_item(
                item_id=fid,
                title=getattr(finding, 'title', '') or 'OSES finding',
                status=getattr(finding, 'status', 'observed'),
                source='oses_finding',
                evidence_refs=list(getattr(finding, 'evidence_refs', []) or []),
                next_action=getattr(finding, 'recommendation', '') or 'Investigate',
                score_components=score,
                reason=getattr(finding, 'summary', '') or '',
            ))
        return items

    def _project_runtime_audit_items(
        self, seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        """Project failed/stalled interaction episodes from runtime_audit.jsonl.

        Resolved-sane episodes are NOT projected (no false positives).
        """
        if not self.workspace_root:
            return []
        import json as _json
        audit_path = Path(str(self.workspace_root)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        items: list[dict[str, Any]] = []
        try:
            lines = audit_path.read_text(encoding='utf-8', errors='replace').splitlines()
            count = 0
            for line in reversed(lines):
                if count >= 10:
                    break
                if not line.strip():
                    continue
                try:
                    event = _json.loads(line)
                except Exception:
                    continue
                if event.get('kind') != 'interaction_resolved':
                    continue
                count += 1
                data = dict(event.get('data') or {})
                outcome = data.get('outcome', '')
                stalls = list(data.get('stalls_during') or [])
                # Only project failed or stalled episodes
                if outcome == 'resolved' and not stalls:
                    continue
                iid_raw = data.get('interaction_id', '')
                aid = f'audit:{iid_raw}'
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)
                score: dict[str, int] = {'base': 20}
                if outcome in ('failed', 'abandoned'):
                    score['failed_interaction'] = 35
                if stalls:
                    score['ui_stalls'] = min(len(stalls) * 15, 45)
                items.append(self._make_item(
                    item_id=aid,
                    title=(
                        f'Interaction {outcome}: '
                        f'"{data.get("message_preview", "")[:50]}" '
                        f'provider={data.get("provider", "?")}'
                    ),
                    status=outcome,
                    source='runtime_audit',
                    evidence_refs=[f'data/logs/runtime_audit.jsonl#{iid_raw}'],
                    next_action='Investigate interaction failure/stall pattern',
                    score_components=score,
                    reason=(
                        f'duration={data.get("total_duration_ms", 0)}ms '
                        f'stalls={len(stalls)} '
                        f'window_inactive={data.get("window_went_inactive", False)}'
                    ),
                ))
        except Exception:
            pass
        return items

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def seed_from_agents_md(self, path: Path) -> int:
        """Parse AGENTS.md and create/refresh structured rules.

        Idempotent: every rule id is deterministically derived from its
        title, so re-running the seed updates in place instead of
        creating duplicates.
        """

        if not path.exists():
            return 0
        text = path.read_text(encoding="utf-8")
        created = 0
        for title, description, severity in _parse_agents_rules(text):
            rule_id = _deterministic_rule_id(title)
            rule = ControlRule(
                rule_id=rule_id,
                title=title,
                description=description,
                severity=severity,
                status=ControlRuleStatus.ACTIVE,
                source_refs=[f"AGENTS.md#{_heading_anchor(title)}"],
            )
            self.upsert_rule(rule)
            created += 1
        return created

    # ------------------------------------------------------------------
    # Projections (derived, never persisted twice)
    # ------------------------------------------------------------------

    def _project_objective_buckets(self) -> dict[str, list[str]]:
        buckets = {
            "active": [],
            "completed": [],
            "paused": [],
            "discarded": [],
        }
        if self.objective_repository is None:
            return buckets
        try:
            active = self.objective_repository.list_recent(
                status=ObjectiveStatus.ACTIVE, limit=50
            )
            completed = self.objective_repository.list_recent(
                status=ObjectiveStatus.COMPLETED, limit=50
            )
            paused = self.objective_repository.list_recent(
                status=ObjectiveStatus.PAUSED, limit=50
            )
        except Exception:
            return buckets
        for node in active:
            buckets["active"].append(node.objective_id)
        for node in completed:
            buckets["completed"].append(node.objective_id)
        for node in paused:
            if _DISCARDED_TAG in (node.tags or []):
                buckets["discarded"].append(node.objective_id)
            else:
                buckets["paused"].append(node.objective_id)
        return buckets

    def _project_backlog(self) -> list[dict[str, Any]]:
        if self.pending_issue_repository is None:
            return []
        candidates: list[Any] = []
        for method_name in ("list_recent", "list_open", "list_pending", "list_all"):
            method = getattr(self.pending_issue_repository, method_name, None)
            if method is None:
                continue
            try:
                candidates = list(method())
                break
            except Exception:
                continue
        backlog: list[dict[str, Any]] = []
        for item in candidates[:20]:
            if hasattr(item, "model_dump"):
                backlog.append(item.model_dump(mode="json"))
            elif isinstance(item, dict):
                backlog.append(item)
            else:
                backlog.append({"raw": str(item)})
        return backlog

    def _project_risks(self) -> list[dict[str, Any]]:
        if self.self_examination_service is None:
            return []
        snapshot = None
        for method_name in ("current_snapshot", "latest_snapshot", "current", "latest"):
            method = getattr(self.self_examination_service, method_name, None)
            if method is None:
                continue
            try:
                snapshot = method()
                break
            except Exception:
                continue
        if snapshot is None:
            return []
        findings = getattr(snapshot, "findings", None) or []
        risks: list[dict[str, Any]] = []
        for finding in findings[:10]:
            if hasattr(finding, "model_dump"):
                risks.append(finding.model_dump(mode="json"))
        return risks

    def _project_account_inventory(self) -> dict[str, Any]:
        """Project account inventory into governance metadata.

        Returns a compact summary dict so that Control Master knows:
        how many accounts are active, exhausted, at risk, and which
        account is the recommended next one.  Failures are swallowed —
        governance never crashes because the scanner is unavailable.
        """
        scanner = self.account_resource_scanner
        if scanner is None:
            return {
                'status': 'scanner_not_connected',
                'unresolved_items': [
                    'UNRESOLVED:account_inventory_scanner_not_connected',
                ],
            }
        try:
            if callable(scanner):
                snapshot = scanner()
            else:
                snapshot = scanner
        except Exception:
            return {
                'status': 'scanner_error',
                'unresolved_items': [
                    'UNRESOLVED:account_inventory_scanner_error',
                ],
            }

        if hasattr(snapshot, 'model_dump'):
            data = snapshot.model_dump(mode='json')
        elif isinstance(snapshot, dict):
            data = snapshot
        else:
            return {
                'status': 'scanner_unknown_format',
                'unresolved_items': [
                    'UNRESOLVED:account_inventory_unknown_format',
                ],
            }

        # Build compact summary for governance
        queue = data.get('continuity_queue', [])
        next_recommended = queue[0] if queue else None

        return {
            'status': 'ok',
            'active_count': data.get('active_count', 0),
            'exhausted_count': data.get('exhausted_count', 0),
            'expired_count': data.get('expired_count', 0),
            'unresolved_count': data.get('unresolved_count', 0),
            'total_remaining_messages': data.get('total_remaining_messages', 0),
            'tools_available': data.get('tools_available', []),
            'continuity_queue_size': len(queue),
            'next_recommended': {
                'email': next_recommended.get('email', ''),
                'tool': next_recommended.get('tool', ''),
                'score': next_recommended.get('score', 0.0),
                'quota_remaining': next_recommended.get('quota_remaining', 0),
            } if next_recommended else None,
            'scanned_at': data.get('scanned_at', ''),
            'unresolved_items': data.get('unresolved_items', []),
        }

    def _project_unresolved(self) -> list[str]:
        if self.self_examination_service is None:
            return []
        for method_name in ("current_snapshot", "latest_snapshot", "current", "latest"):
            method = getattr(self.self_examination_service, method_name, None)
            if method is None:
                continue
            try:
                snapshot = method()
            except Exception:
                continue
            unresolved = getattr(snapshot, "unresolved_risks", None) or []
            return [str(item) for item in unresolved]
        return []


# ----------------------------------------------------------------------
# Scoring helpers
# ----------------------------------------------------------------------


def _score_to_label(score: int) -> str:
    if score >= 80:
        return 'critical'
    if score >= 50:
        return 'high'
    if score >= 30:
        return 'medium'
    return 'low'


# ----------------------------------------------------------------------
# AGENTS.md parsing helpers
# ----------------------------------------------------------------------


_IRREVOCABLE_HEADINGS = {
    "Contratos Que No Debes Romper",
}
_STRICT_HEADINGS = {
    "Capas Cerradas Que Debes Respetar",
    "Politica Operativa Actual",
    "Regla De Observacion Real",
}


def _parse_agents_rules(text: str) -> list[tuple[str, str, ControlRuleSeverity]]:
    """Extract governance rules from AGENTS.md headings.

    Returns tuples ``(title, description, severity)`` for each bullet
    point found under well-known governance headings.
    """

    rules: list[tuple[str, str, ControlRuleSeverity]] = []
    for heading, severity in _iter_heading_sections(text):
        if heading in _IRREVOCABLE_HEADINGS:
            rule_severity = ControlRuleSeverity.IRREVOCABLE
        elif heading in _STRICT_HEADINGS:
            rule_severity = ControlRuleSeverity.STRICT
        else:
            continue
        bullets = _extract_bullets(severity)
        for title, description in bullets:
            rules.append((title, description, rule_severity))
    return rules


def _iter_heading_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        sections.append((heading, body))
    return sections


def _extract_bullets(body: str) -> list[tuple[str, str]]:
    bullets: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            if current_title is not None:
                bullets.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped[2:].strip()
            current_lines = []
        elif stripped and current_title is not None:
            current_lines.append(stripped)
        elif not stripped and current_title is not None:
            bullets.append((current_title, "\n".join(current_lines).strip()))
            current_title = None
            current_lines = []
    if current_title is not None:
        bullets.append((current_title, "\n".join(current_lines).strip()))
    # Drop empty titles (defensive, should not happen)
    return [item for item in bullets if item[0]]


def _deterministic_rule_id(title: str) -> str:
    digest = hashlib.sha256(title.strip().lower().encode("utf-8")).hexdigest()[:12]
    return f"rule-{digest}"


def _heading_anchor(title: str) -> str:
    slug = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    slug = re.sub(r"\s+", "-", slug).strip("-")
    return slug or "rule"
