"""Tests for AutonomyCycleService — the unified autonomy substrate.

Covers:
1. Bridge: OSES findings → pending queue (replaces inline OSES bridge)
2. Resume hints: save checkpoint on ABORTED/FAILED sessions
3. Capability discovery → pending tasks (delegation)
4. Startup summary: actionable context for new sessions
5. Integration: OSES and TaskOutcomeRecorder delegation
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.domain.models import (
    AdaptiveSessionStatus,
    EnvironmentCapability,
    PendingTaskStatus,
    PlatformPendingTask,
    PlatformResumeHint,
)
from iabv_v15.services.evolution.autonomy_cycle_service import AutonomyCycleService
from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue


@pytest.fixture
def evolution_dir(tmp_path: Path) -> str:
    d = tmp_path / 'data' / 'evolution'
    d.mkdir(parents=True)
    return str(d)


@pytest.fixture
def queue(evolution_dir: str) -> PlatformPendingQueue:
    return PlatformPendingQueue(evolution_dir=evolution_dir)


@pytest.fixture
def service(queue: PlatformPendingQueue) -> AutonomyCycleService:
    return AutonomyCycleService(queue=queue)


# ------------------------------------------------------------------
# Fake finding for bridge tests
# ------------------------------------------------------------------

class _FakeSeverity:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeFinding:
    def __init__(
        self,
        category: str,
        severity: str,
        title: str = 'test finding',
        summary: str = '',
        recommendation: str = '',
        confidence: float = 0.8,
    ) -> None:
        self.category = category
        self.severity = _FakeSeverity(severity)
        self.title = title
        self.summary = summary
        self.recommendation = recommendation
        self.confidence = confidence


# ------------------------------------------------------------------
# Fake session for resume hint tests
# ------------------------------------------------------------------

_STATUS_MAP = {
    'ABORTED': AdaptiveSessionStatus.ABORTED,
    'FAILED': AdaptiveSessionStatus.FAILED,
    'COMPLETED': AdaptiveSessionStatus.COMPLETED,
}


class _FakeSession:
    def __init__(
        self,
        session_id: str = 'sess-001',
        status_value: str = 'ABORTED',
        user_goal: str = 'test goal',
        metadata: dict | None = None,
        playbook: Any = None,
    ) -> None:
        self.session_id = session_id
        self.status = _STATUS_MAP.get(status_value, AdaptiveSessionStatus.ABORTED)
        self.user_goal = user_goal
        self.metadata = metadata or {}
        self.playbook = playbook


class _FakeResult:
    def __init__(self, summary: str = 'step done') -> None:
        self.summary = summary


class _FakeRunRecord:
    def __init__(self, summary: str = 'last step done') -> None:
        self.result = _FakeResult(summary)
        self.error_summary = ''


# ------------------------------------------------------------------
# 1. Bridge tests
# ------------------------------------------------------------------

class TestBridgeFindings:
    def test_high_finding_creates_pending_task(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        findings = [_FakeFinding('startup_populate_ui_freeze', 'CRITICAL')]
        count = service.bridge_findings(findings)
        assert count == 1
        task = queue.get('oses_startup_populate_ui_freeze')
        assert task is not None
        assert task.priority == 'critical'
        assert task.category == 'oses_finding'

    def test_low_severity_skipped(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        findings = [_FakeFinding('startup_populate_ui_freeze', 'MEDIUM')]
        count = service.bridge_findings(findings)
        assert count == 0
        assert queue.get('oses_startup_populate_ui_freeze') is None

    def test_unknown_category_skipped(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        findings = [_FakeFinding('unknown_category', 'CRITICAL')]
        count = service.bridge_findings(findings)
        assert count == 0

    def test_completed_task_not_overwritten(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(
            id='oses_startup_degradation',
            title='done',
            status=PendingTaskStatus.COMPLETED,
        ))
        findings = [_FakeFinding('startup_degradation', 'HIGH')]
        count = service.bridge_findings(findings)
        assert count == 0
        task = queue.get('oses_startup_degradation')
        assert task is not None
        assert task.status == PendingTaskStatus.COMPLETED

    def test_bridge_idempotent(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        findings = [_FakeFinding('cloud_reasoning_degradation', 'HIGH')]
        service.bridge_findings(findings)
        service.bridge_findings(findings)
        tasks = [t for t in queue.list_all() if t.id == 'oses_cloud_reasoning_degradation']
        assert len(tasks) == 1


# ------------------------------------------------------------------
# 2. Resume hint tests
# ------------------------------------------------------------------

class TestResumeHints:
    def test_aborted_session_saves_hint(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        session = _FakeSession(status_value='ABORTED')
        hint = service.save_resume_hint(session)
        assert hint is not None
        assert hint.task_id == 'sess-001'
        assert hint.handoff_required is False
        retrieved = queue.get_resume_hint('sess-001')
        assert retrieved is not None

    def test_failed_session_saves_hint_with_handoff(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        session = _FakeSession(status_value='FAILED')
        hint = service.save_resume_hint(session)
        assert hint is not None
        assert hint.handoff_required is True

    def test_completed_session_no_hint(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        session = _FakeSession(status_value='COMPLETED')
        hint = service.save_resume_hint(session)
        assert hint is None

    def test_run_record_captures_last_step(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        session = _FakeSession(status_value='ABORTED')
        rr = _FakeRunRecord(summary='installed dependency X')
        hint = service.save_resume_hint(session, run_record=rr)
        assert hint is not None
        assert hint.last_successful_step == 'installed dependency X'


# ------------------------------------------------------------------
# 3. Capability discovery tests
# ------------------------------------------------------------------

class TestCapabilityDiscovery:
    def test_missing_capability_becomes_task(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        caps = [EnvironmentCapability(
            capability_id='platform.toast',
            title='Toast',
            available=False,
            status='missing',
            metadata={'missing': 'winotify'},
        )]
        seeded = service.seed_capabilities(caps)
        assert len(seeded) == 1
        assert seeded[0].status == PendingTaskStatus.BLOCKED

    def test_available_capability_skipped(self, service: AutonomyCycleService):
        caps = [EnvironmentCapability(
            capability_id='platform.clipboard',
            title='Clipboard',
            available=True,
            status='confirmed',
        )]
        seeded = service.seed_capabilities(caps)
        assert seeded == []


# ------------------------------------------------------------------
# 4. Startup summary tests
# ------------------------------------------------------------------

class TestStartupSummary:
    def test_empty_queue_summary(self, service: AutonomyCycleService):
        summary = service.startup_summary()
        assert summary['actionable_tasks'] == []
        assert summary['blocked_tasks'] == []
        assert summary['resume_hints'] == []
        assert summary['queue_summary']['total'] == 0

    def test_summary_includes_actionable_and_blocked(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(
            id='t1', title='Task 1',
            status=PendingTaskStatus.PENDING, priority='high',
            next_action='do it',
        ))
        queue.upsert(PlatformPendingTask(
            id='t2', title='Task 2',
            status=PendingTaskStatus.BLOCKED, priority='medium',
            dependency_missing='winotify',
        ))
        queue.upsert(PlatformPendingTask(
            id='t3', title='Task 3',
            status=PendingTaskStatus.COMPLETED, priority='low',
        ))
        summary = service.startup_summary()
        assert len(summary['actionable_tasks']) == 1
        assert summary['actionable_tasks'][0]['id'] == 't1'
        assert len(summary['blocked_tasks']) == 1
        assert summary['blocked_tasks'][0]['id'] == 't2'
        assert summary['queue_summary']['total'] == 3

    def test_summary_includes_resume_hints(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        queue.save_resume_hint(PlatformResumeHint(
            task_id='sess-x',
            checkpoint_phase='ABORTED',
            last_successful_step='step 3',
            remaining_steps=['step 4', 'step 5'],
            handoff_required=False,
        ))
        summary = service.startup_summary()
        assert len(summary['resume_hints']) == 1
        assert summary['resume_hints'][0]['task_id'] == 'sess-x'
        assert summary['resume_hints'][0]['remaining'] == ['step 4', 'step 5']


# ------------------------------------------------------------------
# 5. Integration: end-to-end cycle
# ------------------------------------------------------------------

class TestEndToEndCycle:
    def test_full_cycle_perceive_to_resume(self, service: AutonomyCycleService, queue: PlatformPendingQueue):
        """Simulates the complete autonomy cycle:
        1. OSES produces a finding → bridge creates task
        2. Session attempts the task → fails → resume hint saved
        3. New session reads startup_summary → sees both task + hint
        """
        # Step 1: OSES finding
        findings = [_FakeFinding(
            'startup_degradation', 'HIGH',
            title='Boot too slow',
            summary='Bootstrap init takes 12s',
        )]
        service.bridge_findings(findings)

        # Step 2: Session works on it, then aborts
        session = _FakeSession(
            session_id='sess-fix-boot',
            status_value='ABORTED',
            user_goal='Fix startup degradation',
            metadata={'intent_key': 'optimize_startup'},
        )
        rr = _FakeRunRecord(summary='Moved phase 2 to lazy')
        service.save_resume_hint(session, run_record=rr)

        # Step 3: Next session reads summary
        summary = service.startup_summary()
        assert len(summary['actionable_tasks']) == 1
        assert summary['actionable_tasks'][0]['id'] == 'oses_startup_degradation'
        assert len(summary['resume_hints']) == 1
        assert summary['resume_hints'][0]['task_id'] == 'sess-fix-boot'
        assert summary['resume_hints'][0]['last_step'] == 'Moved phase 2 to lazy'
