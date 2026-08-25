"""Tests for the canonical work queue projection in ControlMasterService.

Covers:
1. Unification: objectives + platform pending + pending issues combined without duplicates
2. Scoring: startup/memory/query stall items rank above low-priority items
3. Reconciliation: COMPLETED platform tasks do not reappear
4. Idempotence: repeated projection produces identical results
5. Digest rendering: top next actions appear in ControlMasterDigest
6. PortableContext rendering: canonical work queue section in latest.md
7. Runtime audit: failed/stalled episodes create items with evidence_refs
8. Runtime audit: resolved-sane episodes do NOT create false positives
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import (
    ControlMasterState,
    IssueSeverity,
    ObjectiveNode,
    ObjectiveStatus,
    PendingTaskStatus,
    PlatformPendingTask,
    SelfExaminationFinding,
    utc_now,
)
from iabv_v15.services.evolution.control_master_digest_builder import (
    ControlMasterDigestBuilder,
    render_digest_markdown,
)
from iabv_v15.services.evolution.control_master_service import ControlMasterService


def _workspace() -> Path:
    root = Path("/tmp") / f"iabv_wq_{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    (root / "data" / "logs").mkdir(parents=True, exist_ok=True)
    return root


def _fake_repo():
    """Minimal ControlMasterRepository fake."""
    repo = MagicMock()
    repo.load_latest_state.return_value = ControlMasterState()
    repo.list_rules.return_value = []
    repo.list_decisions.return_value = []
    repo.save_state.side_effect = lambda s: s
    return repo


def _fake_objective_repo(nodes: list[ObjectiveNode] | None = None):
    """Fake ObjectiveRepository that returns given nodes for any status."""
    repo = MagicMock()
    repo.list_recent.return_value = nodes or []
    return repo


def _fake_pending_issue_repo(issues: list[Any] | None = None):
    repo = MagicMock()
    repo.list_recent.return_value = issues or []
    return repo


def _fake_platform_pending_queue(tasks: list[PlatformPendingTask] | None = None):
    queue = MagicMock()
    queue.list_all.return_value = tasks or []
    return queue


def _fake_self_examination_service(findings: list[SelfExaminationFinding] | None = None):
    svc = MagicMock()
    snapshot = MagicMock()
    snapshot.findings = findings or []
    svc.current_review.return_value = snapshot
    return svc


def _write_audit(workspace: Path, events: list[dict[str, Any]]) -> None:
    path = workspace / "data" / "logs" / "runtime_audit.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


class TestWorkQueueUnification:
    """work queue combina objectives + platform pending + pending issues sin duplicar."""

    def test_unifies_all_sources(self) -> None:
        ws = _workspace()
        try:
            obj_node = ObjectiveNode(
                objective_id="obj-1", title="Fix startup", status=ObjectiveStatus.ACTIVE
            )
            task = PlatformPendingTask(
                id="plat-1", title="Enable systray", status=PendingTaskStatus.PENDING
            )
            issue = MagicMock()
            issue.issue_id = "iss-1"
            issue.summary = "Query freeze"
            issue.status = "needs_fix"
            issue.evidence_refs = []
            issue.recommended_change = "Fix query"
            issue.probable_cause = ""
            issue.created_at_utc = utc_now()

            svc = ControlMasterService(
                repository=_fake_repo(),
                objective_repository=_fake_objective_repo([obj_node]),
                pending_issue_repository=_fake_pending_issue_repo([issue]),
                platform_pending_queue=_fake_platform_pending_queue([task]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            ids = [item['id'] for item in queue]
            assert 'objective:obj-1' in ids
            assert 'platform:plat-1' in ids
            assert 'issue:iss-1' in ids
            # No duplicates
            assert len(ids) == len(set(ids))
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_no_duplicates_on_repeated_sources(self) -> None:
        ws = _workspace()
        try:
            obj_node = ObjectiveNode(
                objective_id="obj-dup", title="Test dup", status=ObjectiveStatus.ACTIVE
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                objective_repository=_fake_objective_repo([obj_node]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            obj_ids = [i['id'] for i in queue if i['id'] == 'objective:obj-dup']
            assert len(obj_ids) == 1
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestScoringDeterministic:
    """Score ordena startup/memory/query stall por encima de tareas low."""

    def test_startup_freeze_ranks_above_low_priority(self) -> None:
        ws = _workspace()
        try:
            issue_startup = MagicMock()
            issue_startup.issue_id = "iss-startup"
            issue_startup.summary = "Startup freeze in populate_ui"
            issue_startup.status = "needs_fix"
            issue_startup.evidence_refs = []
            issue_startup.recommended_change = "Fix startup"
            issue_startup.probable_cause = ""
            issue_startup.created_at_utc = utc_now()

            obj_low = ObjectiveNode(
                objective_id="obj-low", title="Improve docs", status=ObjectiveStatus.ACTIVE,
                priority=20,
            )

            svc = ControlMasterService(
                repository=_fake_repo(),
                objective_repository=_fake_objective_repo([obj_low]),
                pending_issue_repository=_fake_pending_issue_repo([issue_startup]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            startup_item = next(i for i in queue if 'startup' in i['title'].lower())
            low_item = next(i for i in queue if i['id'] == 'objective:obj-low')
            assert startup_item['priority_score'] > low_item['priority_score']
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_memory_critical_scores_high(self) -> None:
        ws = _workspace()
        try:
            issue = MagicMock()
            issue.issue_id = "iss-mem"
            issue.summary = "Memory RSS critical OOM risk"
            issue.status = "needs_fix"
            issue.evidence_refs = []
            issue.recommended_change = "Reduce memory"
            issue.probable_cause = ""
            issue.created_at_utc = utc_now()

            svc = ControlMasterService(
                repository=_fake_repo(),
                pending_issue_repository=_fake_pending_issue_repo([issue]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            mem_item = next(i for i in queue if 'memory' in i['title'].lower())
            assert mem_item['priority_score'] >= 60
            assert mem_item['priority_label'] in ('high', 'critical')
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_score_breakdown_present(self) -> None:
        ws = _workspace()
        try:
            obj = ObjectiveNode(
                objective_id="obj-brk", title="Test breakdown", status=ObjectiveStatus.ACTIVE,
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                objective_repository=_fake_objective_repo([obj]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            item = next(i for i in queue if i['id'] == 'objective:obj-brk')
            assert 'score_breakdown' in item
            assert isinstance(item['score_breakdown'], dict)
            assert sum(item['score_breakdown'].values()) == item['priority_score']
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestCompletedReconciliation:
    """completed platform tasks no reaparecen."""

    def test_completed_platform_task_excluded(self) -> None:
        ws = _workspace()
        try:
            completed = PlatformPendingTask(
                id="plat-done", title="Already done", status=PendingTaskStatus.COMPLETED
            )
            pending = PlatformPendingTask(
                id="plat-open", title="Still open", status=PendingTaskStatus.PENDING
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                platform_pending_queue=_fake_platform_pending_queue([completed, pending]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            ids = [i['id'] for i in queue]
            assert 'platform:plat-done' not in ids
            assert 'platform:plat-open' in ids
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestProjectionIdempotence:
    """repeated projection is idempotent."""

    def test_two_projections_identical(self) -> None:
        ws = _workspace()
        try:
            obj = ObjectiveNode(
                objective_id="obj-idem", title="Idempotence test", status=ObjectiveStatus.ACTIVE,
            )
            task = PlatformPendingTask(
                id="plat-idem", title="Platform test", status=PendingTaskStatus.PENDING,
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                objective_repository=_fake_objective_repo([obj]),
                platform_pending_queue=_fake_platform_pending_queue([task]),
                workspace_root=str(ws),
            )
            q1 = svc.current_work_queue()
            q2 = svc.current_work_queue()
            assert len(q1) == len(q2)
            for a, b in zip(q1, q2):
                assert a['id'] == b['id']
                assert a['priority_score'] == b['priority_score']
                assert a['source'] == b['source']
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestDigestRendersWorkQueue:
    """digest renderiza top next actions."""

    def test_digest_includes_work_queue(self) -> None:
        state = ControlMasterState()
        work_queue = [
            {
                'id': 'objective:obj-1',
                'title': 'Fix startup freeze',
                'status': 'active',
                'priority_score': 80,
                'priority_label': 'critical',
                'source': 'objective_repository',
                'next_action': 'Investigate populate_ui',
                'evidence_refs': [],
            },
        ]
        builder = ControlMasterDigestBuilder(max_chars=4000)
        digest = builder.build(state, work_queue=work_queue)
        assert len(digest.work_queue_brief) == 1
        assert 'Fix startup freeze' in digest.work_queue_brief[0]
        md = render_digest_markdown(digest)
        assert 'Cola de trabajo' in md
        assert 'Fix startup freeze' in md

    def test_digest_work_queue_counts(self) -> None:
        state = ControlMasterState()
        work_queue = [
            {'id': 'a', 'status': 'active', 'title': 'A', 'priority_label': 'high', 'source': 's', 'next_action': 'x', 'priority_score': 50},
            {'id': 'b', 'status': 'active', 'title': 'B', 'priority_label': 'high', 'source': 's', 'next_action': 'x', 'priority_score': 40},
            {'id': 'c', 'status': 'blocked', 'title': 'C', 'priority_label': 'low', 'source': 's', 'next_action': 'x', 'priority_score': 20},
        ]
        builder = ControlMasterDigestBuilder(max_chars=4000)
        digest = builder.build(state, work_queue=work_queue)
        assert digest.work_queue_counts.get('active') == 2
        assert digest.work_queue_counts.get('blocked') == 1
        md = render_digest_markdown(digest)
        assert 'Work queue counts' in md


class TestPortableContextCanonicalQueue:
    """portable context muestra la cola canónica."""

    def test_section_renders_in_latest_md(self) -> None:
        from iabv_v15.services.evolution.portable_context_service import PortableContextService
        from iabv_v15.infra.persistence.storage import ArtifactStorage

        ws = _workspace()
        try:
            storage = ArtifactStorage(root=str(ws / "data"))
            pcs = PortableContextService(workspace_root=str(ws), storage=storage)
            # Wire a mock ControlMasterService
            cms = MagicMock()
            cms.current_work_queue.return_value = [
                {
                    'id': 'objective:obj-vis',
                    'title': 'Visible in latest.md',
                    'status': 'active',
                    'priority_score': 70,
                    'priority_label': 'high',
                    'source': 'objective_repository',
                    'next_action': 'Investigate',
                    'evidence_refs': ['ref1'],
                },
            ]
            pcs.control_master_service = cms
            package = pcs.build_package()
            # Find the canonical work queue section
            wq_section = next(
                (s for s in package.sections if s.section_id == 'canonical_work_queue'),
                None,
            )
            assert wq_section is not None
            assert len(wq_section.items) == 1
            assert wq_section.items[0]['title'] == 'Visible in latest.md'
            # Verify it renders in the assistant_brief / markdown
            assert 'Cola canónica de trabajo' in package.assistant_brief
            assert 'Visible in latest.md' in package.assistant_brief
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestRuntimeAuditFailedCreatesItem:
    """runtime_audit failed/stalled crea item con evidence_refs."""

    def test_failed_episode_creates_work_item(self) -> None:
        ws = _workspace()
        try:
            _write_audit(ws, [
                {
                    "kind": "interaction_resolved",
                    "data": {
                        "interaction_id": "chat-fail-1",
                        "message_preview": "Test query that failed",
                        "outcome": "failed",
                        "provider": "Gemini",
                        "total_duration_ms": 5000,
                        "stalls_during": [],
                        "window_went_inactive": False,
                    },
                },
            ])
            svc = ControlMasterService(
                repository=_fake_repo(),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            audit_items = [i for i in queue if i['source'] == 'runtime_audit']
            assert len(audit_items) == 1
            assert audit_items[0]['id'] == 'audit:chat-fail-1'
            assert 'runtime_audit.jsonl' in audit_items[0]['evidence_refs'][0]
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_stalled_episode_creates_work_item(self) -> None:
        ws = _workspace()
        try:
            _write_audit(ws, [
                {
                    "kind": "interaction_resolved",
                    "data": {
                        "interaction_id": "chat-stall-1",
                        "message_preview": "Query with stall",
                        "outcome": "resolved",
                        "provider": "Groq",
                        "total_duration_ms": 15000,
                        "stalls_during": [{"type": "query_visible_gap", "duration_ms": 8000}],
                        "window_went_inactive": False,
                    },
                },
            ])
            svc = ControlMasterService(
                repository=_fake_repo(),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            audit_items = [i for i in queue if i['source'] == 'runtime_audit']
            assert len(audit_items) == 1
            assert 'stall' in audit_items[0]['reason'].lower() or 'stalls=1' in audit_items[0]['reason']
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestRuntimeAuditResolvedNoFalsePositive:
    """runtime_audit resolved sano no crea falso positivo."""

    def test_resolved_clean_not_projected(self) -> None:
        ws = _workspace()
        try:
            _write_audit(ws, [
                {
                    "kind": "interaction_resolved",
                    "data": {
                        "interaction_id": "chat-ok-1",
                        "message_preview": "Healthy interaction",
                        "outcome": "resolved",
                        "provider": "Gemini",
                        "total_duration_ms": 1500,
                        "stalls_during": [],
                        "window_went_inactive": False,
                    },
                },
            ])
            svc = ControlMasterService(
                repository=_fake_repo(),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            audit_items = [i for i in queue if i['source'] == 'runtime_audit']
            assert len(audit_items) == 0
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestOSESFindingsProjected:
    """OSES HIGH/CRITICAL findings appear in work queue."""

    def test_high_oses_finding_in_queue(self) -> None:
        ws = _workspace()
        try:
            finding = SelfExaminationFinding(
                finding_id="f-startup",
                title="startup_false_ready",
                severity=IssueSeverity.HIGH,
                recommendation="Fix phased populate_ui",
                summary="Shell loader ready never arrived honestly",
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                self_examination_service=_fake_self_examination_service([finding]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            oses_items = [i for i in queue if i['source'] == 'oses_finding']
            assert len(oses_items) == 1
            assert oses_items[0]['title'] == 'startup_false_ready'
            assert oses_items[0]['priority_score'] >= 50
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_medium_oses_finding_excluded(self) -> None:
        ws = _workspace()
        try:
            finding = SelfExaminationFinding(
                finding_id="f-med",
                title="minor thing",
                severity=IssueSeverity.MEDIUM,
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                self_examination_service=_fake_self_examination_service([finding]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            oses_items = [i for i in queue if i['source'] == 'oses_finding']
            assert len(oses_items) == 0
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestWorkQueueItemSchema:
    """Each work queue item has all required fields."""

    def test_item_has_all_required_fields(self) -> None:
        ws = _workspace()
        try:
            obj = ObjectiveNode(
                objective_id="obj-schema", title="Schema test", status=ObjectiveStatus.ACTIVE,
            )
            svc = ControlMasterService(
                repository=_fake_repo(),
                objective_repository=_fake_objective_repo([obj]),
                workspace_root=str(ws),
            )
            queue = svc.current_work_queue()
            assert len(queue) >= 1
            item = queue[0]
            required_keys = {
                'id', 'title', 'status', 'priority_score', 'priority_label',
                'source', 'evidence_refs', 'next_action', 'acceptance_tests',
                'dependencies', 'parallelizable', 'updated_at', 'reason',
                'score_breakdown',
            }
            assert required_keys.issubset(set(item.keys()))
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestBootstrapWiring:
    """Verify bootstrap wires platform_pending_queue, workspace_root into CMS
    and control_master_service into PortableContextService."""

    def test_bootstrap_wires_platform_pending_queue(self) -> None:
        """Simulates bootstrap wiring: CMS receives platform_pending_queue."""
        ws = _workspace()
        try:
            queue = _fake_platform_pending_queue([
                PlatformPendingTask(id="bp-1", title="Bootstrap task", status=PendingTaskStatus.PENDING),
            ])
            svc = ControlMasterService(
                repository=_fake_repo(),
                platform_pending_queue=queue,
                workspace_root=str(ws),
            )
            assert svc.platform_pending_queue is queue
            assert svc.workspace_root == str(ws)
            items = svc.current_work_queue()
            assert any(i['id'] == 'platform:bp-1' for i in items)
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_portable_context_with_control_master_service(self) -> None:
        """PCS with CMS wired produces canonical_work_queue section without UNRESOLVED."""
        from iabv_v15.services.evolution.portable_context_service import PortableContextService
        from iabv_v15.infra.persistence.storage import ArtifactStorage

        ws = _workspace()
        try:
            storage = ArtifactStorage(root=str(ws / "data"))
            pcs = PortableContextService(workspace_root=str(ws), storage=storage)
            cms = MagicMock()
            cms.current_work_queue.return_value = [
                {
                    'id': 'objective:bp-test',
                    'title': 'Wired correctly',
                    'status': 'active',
                    'priority_score': 55,
                    'priority_label': 'high',
                    'source': 'objective_repository',
                    'next_action': 'Verify',
                    'evidence_refs': [],
                },
            ]
            pcs.control_master_service = cms
            package = pcs.build_package()
            wq_section = next(
                (s for s in package.sections if s.section_id == 'canonical_work_queue'),
                None,
            )
            assert wq_section is not None
            assert len(wq_section.items) == 1
            # Should NOT have UNRESOLVED when CMS is connected
            assert 'UNRESOLVED:canonical_work_queue_not_connected' not in wq_section.unresolved_fields
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestOSESCurrentReview:
    """ControlMasterService reads OSES via current_review() per AGENTS.md."""

    def test_oses_reads_via_current_review(self) -> None:
        ws = _workspace()
        try:
            finding = SelfExaminationFinding(
                finding_id="f-review",
                title="populate_ui_blocked",
                severity=IssueSeverity.HIGH,
                recommendation="Fix phased populate_ui",
                summary="populate_ui blocked main thread",
            )
            # Mock service that only exposes current_review(), not current_snapshot
            svc_mock = MagicMock(spec=[])
            snapshot = MagicMock()
            snapshot.findings = [finding]
            svc_mock.current_review = MagicMock(return_value=snapshot)

            cms = ControlMasterService(
                repository=_fake_repo(),
                self_examination_service=svc_mock,
                workspace_root=str(ws),
            )
            queue = cms.current_work_queue()
            oses_items = [i for i in queue if i['source'] == 'oses_finding']
            assert len(oses_items) == 1
            assert oses_items[0]['title'] == 'populate_ui_blocked'
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_oses_severity_string_uppercase(self) -> None:
        """Severity as string 'HIGH' or 'CRITICAL' is handled."""
        ws = _workspace()
        try:
            finding = MagicMock()
            finding.finding_id = "f-str"
            finding.title = "string_severity_test"
            finding.severity = "HIGH"  # string, not enum
            finding.status = "observed"
            finding.evidence_refs = []
            finding.recommendation = "Investigate"
            finding.summary = "Test string severity"

            svc_mock = MagicMock(spec=[])
            snapshot = MagicMock()
            snapshot.findings = [finding]
            svc_mock.current_review = MagicMock(return_value=snapshot)

            cms = ControlMasterService(
                repository=_fake_repo(),
                self_examination_service=svc_mock,
                workspace_root=str(ws),
            )
            queue = cms.current_work_queue()
            oses_items = [i for i in queue if i['source'] == 'oses_finding']
            assert len(oses_items) == 1
        finally:
            shutil.rmtree(ws, ignore_errors=True)


class TestDigestWorkQueueInOrchestrator:
    """AdaptiveTaskOrchestrator digest includes work_queue_brief when queue available."""

    def test_digest_has_work_queue_when_service_provides_queue(self) -> None:
        state = ControlMasterState()
        work_queue = [
            {
                'id': 'objective:orch-1',
                'title': 'Orchestrator sees this',
                'status': 'active',
                'priority_score': 65,
                'priority_label': 'high',
                'source': 'objective_repository',
                'next_action': 'Execute',
                'evidence_refs': [],
            },
        ]
        builder = ControlMasterDigestBuilder(max_chars=4000)
        digest = builder.build(state, work_queue=work_queue)
        assert len(digest.work_queue_brief) >= 1
        assert 'Orchestrator sees this' in digest.work_queue_brief[0]
        md = render_digest_markdown(digest)
        assert 'Orchestrator sees this' in md
