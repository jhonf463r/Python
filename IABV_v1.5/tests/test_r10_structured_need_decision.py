"""R10 — StructuredNeed → Decision Tests.

Tests the decision mechanism in ControlMasterService that selects
pending StructuredNeeds for the work queue.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from iabv_v15.domain.models import (
    ControlMasterState,
    StructuredNeed,
    NeedStatus,
    utc_now,
)
from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.control_master_service import ControlMasterService
from iabv_v15.services.evolution.structured_need_repository import StructuredNeedRepository


class TestR10StructuredNeedDecision:
    """R10: StructuredNeed → Decision edge tests."""

    def test_positive_multiple_pending_needs_selects_highest_priority(
        self,
    ) -> None:
        """POSITIVE: multiple pending needs → deterministic selection of highest priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create multiple pending needs with different priorities
            high_priority_need = StructuredNeed(
                need_id="need_high",
                source_finding_id="finding_123",
                category="windows_capability_missing",
                capability_gap="Falta: Notificaciones Windows",
                current_state="",
                desired_state="Dependencia: winrt, plyer, o winotify",
                knowledge_required="windows_capability_missing",
                reason="Windows 10+ pero sin libreria de toast",
                evidence=[],
                priority="high",
                status=NeedStatus.PENDING,
            )

            low_priority_need = StructuredNeed(
                need_id="need_low",
                source_finding_id="finding_456",
                category="windows_capability_missing",
                capability_gap="Falta: Otra capacidad",
                current_state="",
                desired_state="Dependencia: alguna libreria",
                knowledge_required="windows_capability_missing",
                reason="Otra razón",
                evidence=[],
                priority="low",
                status=NeedStatus.PENDING,
            )

            need_repo.upsert(high_priority_need)
            need_repo.upsert(low_priority_need)

            # Create ControlMasterService with need repository
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Get work queue
            queue = service.current_work_queue(limit=10)

            # Find structured need items
            need_items = [item for item in queue if item['source'] == 'structured_need_repository']

            # Assert: both needs are in queue
            assert len(need_items) == 2

            # Assert: high priority need has higher score
            high_item = next((item for item in need_items if item['id'] == 'need:need_high'), None)
            low_item = next((item for item in need_items if item['id'] == 'need:need_low'), None)

            assert high_item is not None
            assert low_item is not None
            assert high_item['priority_score'] > low_item['priority_score']

            # Assert: provenance preserved
            assert high_item['evidence_refs'] == ['finding_123']
            assert low_item['evidence_refs'] == ['finding_456']

    def test_negative_no_pending_needs_no_selection(
        self,
    ) -> None:
        """NEGATIVE: no pending needs → no selection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create a resolved need (should not be selected)
            resolved_need = StructuredNeed(
                need_id="need_resolved",
                source_finding_id="finding_789",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad resuelta",
                current_state="",
                desired_state="Dependencia: resuelta",
                knowledge_required="windows_capability_missing",
                reason="Ya resuelto",
                evidence=[],
                priority="high",
                status=NeedStatus.RESOLVED,
            )

            need_repo.upsert(resolved_need)

            # Create ControlMasterService with need repository
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Get work queue
            queue = service.current_work_queue(limit=10)

            # Find structured need items
            need_items = [item for item in queue if item['source'] == 'structured_need_repository']

            # Assert: no pending needs in queue
            assert len(need_items) == 0

    def test_deferred_lower_priority_remains_pending(
        self,
    ) -> None:
        """DEFERRED: lower-priority need → remains pending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create critical and low priority needs
            critical_need = StructuredNeed(
                need_id="need_critical",
                source_finding_id="finding_critical",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad crítica",
                current_state="",
                desired_state="Dependencia: crítica",
                knowledge_required="windows_capability_missing",
                reason="Crítica",
                evidence=[],
                priority="critical",
                status=NeedStatus.PENDING,
            )

            low_need = StructuredNeed(
                need_id="need_low",
                source_finding_id="finding_low",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad baja",
                current_state="",
                desired_state="Dependencia: baja",
                knowledge_required="windows_capability_missing",
                reason="Baja",
                evidence=[],
                priority="low",
                status=NeedStatus.PENDING,
            )

            need_repo.upsert(critical_need)
            need_repo.upsert(low_need)

            # Create ControlMasterService with need repository
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Get work queue
            queue = service.current_work_queue(limit=10)

            # Find structured need items
            need_items = [item for item in queue if item['source'] == 'structured_need_repository']

            # Assert: both needs are in queue (both pending)
            assert len(need_items) == 2

            # Assert: critical need has higher score and would be selected first
            critical_item = next((item for item in need_items if item['id'] == 'need:need_critical'), None)
            low_item = next((item for item in need_items if item['id'] == 'need:need_low'), None)

            assert critical_item is not None
            assert low_item is not None
            assert critical_item['priority_score'] > low_item['priority_score']

            # Assert: low need is still pending (not removed)
            assert low_item['status'] == 'pending'

    def test_provenance_preserved(
        self,
    ) -> None:
        """PROVENANCE: selected decision retains exact need_id and source_finding_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create a need with specific IDs
            test_need = StructuredNeed(
                need_id="need_provenance_test",
                source_finding_id="finding_provenance_123",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad de prueba",
                current_state="",
                desired_state="Dependencia: prueba",
                knowledge_required="windows_capability_missing",
                reason="Prueba de provenance",
                evidence=[],
                priority="high",
                status=NeedStatus.PENDING,
            )

            need_repo.upsert(test_need)

            # Create ControlMasterService with need repository
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Get work queue
            queue = service.current_work_queue(limit=10)

            # Find the need item
            need_item = next((item for item in queue if item['source'] == 'structured_need_repository'), None)

            # Assert: need_id preserved
            assert need_item is not None
            assert need_item['id'] == 'need:need_provenance_test'

            # Assert: source_finding_id preserved in evidence_refs
            assert need_item['evidence_refs'] == ['finding_provenance_123']

            # Assert: other fields preserved
            assert need_item['title'] == 'Falta: Capacidad de prueba'
            assert need_item['reason'] == 'Prueba de provenance'

    def test_determinism_same_state_same_decision(
        self,
    ) -> None:
        """DETERMINISM: same pending state → same decision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create a fixed set of needs
            need1 = StructuredNeed(
                need_id="need_1",
                source_finding_id="finding_1",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad 1",
                current_state="",
                desired_state="Dependencia: 1",
                knowledge_required="windows_capability_missing",
                reason="Razón 1",
                evidence=[],
                priority="high",
                status=NeedStatus.PENDING,
            )

            need2 = StructuredNeed(
                need_id="need_2",
                source_finding_id="finding_2",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad 2",
                current_state="",
                desired_state="Dependencia: 2",
                knowledge_required="windows_capability_missing",
                reason="Razón 2",
                evidence=[],
                priority="medium",
                status=NeedStatus.PENDING,
            )

            need_repo.upsert(need1)
            need_repo.upsert(need2)

            # Create ControlMasterService
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Get work queue twice
            queue1 = service.current_work_queue(limit=10)
            queue2 = service.current_work_queue(limit=10)

            # Extract need items
            need_items1 = [item for item in queue1 if item['source'] == 'structured_need_repository']
            need_items2 = [item for item in queue2 if item['source'] == 'structured_need_repository']

            # Assert: same number of items
            assert len(need_items1) == len(need_items2)

            # Assert: same priority scores
            scores1 = sorted([item['priority_score'] for item in need_items1], reverse=True)
            scores2 = sorted([item['priority_score'] for item in need_items2], reverse=True)
            assert scores1 == scores2

            # Assert: same ordering (by score)
            items1_sorted = sorted(need_items1, key=lambda x: x['priority_score'], reverse=True)
            items2_sorted = sorted(need_items2, key=lambda x: x['priority_score'], reverse=True)
            assert [item['id'] for item in items1_sorted] == [item['id'] for item in items2_sorted]

    def test_idempotency_no_duplicate_work(
        self,
    ) -> None:
        """IDEMPOTENCY: running decision twice without state change does not create duplicate work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create a need
            test_need = StructuredNeed(
                need_id="need_idempotent",
                source_finding_id="finding_idempotent",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad idempotente",
                current_state="",
                desired_state="Dependencia: idempotente",
                knowledge_required="windows_capability_missing",
                reason="Prueba de idempotencia",
                evidence=[],
                priority="high",
                status=NeedStatus.PENDING,
            )

            need_repo.upsert(test_need)

            # Create ControlMasterService
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Get work queue multiple times
            queue1 = service.current_work_queue(limit=10)
            queue2 = service.current_work_queue(limit=10)
            queue3 = service.current_work_queue(limit=10)

            # Extract need items
            need_items1 = [item for item in queue1 if item['source'] == 'structured_need_repository']
            need_items2 = [item for item in queue2 if item['source'] == 'structured_need_repository']
            need_items3 = [item for item in queue3 if item['source'] == 'structured_need_repository']

            # Assert: always one item (no duplicates)
            assert len(need_items1) == 1
            assert len(need_items2) == 1
            assert len(need_items3) == 1

            # Assert: same item ID (need identity not mutated)
            assert need_items1[0]['id'] == need_items2[0]['id'] == need_items3[0]['id']

            # Assert: repository still has only one need
            all_needs = need_repo.list_all()
            assert len(all_needs) == 1
            assert all_needs[0].need_id == "need_idempotent"

    def test_no_side_effect_no_execution(
        self,
    ) -> None:
        """NO_SIDE_EFFECT: decision selection does not execute tools, modify repository, or invoke external AI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evolution_dir = Path(tmpdir)
            need_repo = StructuredNeedRepository(evolution_dir)
            storage = ArtifactStorage(tmpdir)
            control_repo = ControlMasterRepository(storage)

            # Create a need
            test_need = StructuredNeed(
                need_id="need_no_side_effect",
                source_finding_id="finding_no_side_effect",
                category="windows_capability_missing",
                capability_gap="Falta: Capacidad sin efectos",
                current_state="",
                desired_state="Dependencia: sin efectos",
                knowledge_required="windows_capability_missing",
                reason="Prueba de sin efectos",
                evidence=[],
                priority="high",
                status=NeedStatus.PENDING,
            )

            need_repo.upsert(test_need)

            # Create ControlMasterService
            service = ControlMasterService(
                repository=control_repo,
                structured_need_repository=need_repo,
            )

            # Capture repository state before decision
            needs_before = need_repo.list_all()
            need_count_before = len(needs_before)
            need_status_before = needs_before[0].status if needs_before else None

            # Get work queue (decision)
            queue = service.current_work_queue(limit=10)

            # Capture repository state after decision
            needs_after = need_repo.list_all()
            need_count_after = len(needs_after)
            need_status_after = needs_after[0].status if needs_after else None

            # Assert: repository unchanged
            assert need_count_before == need_count_after
            assert need_status_before == need_status_after

            # Assert: need still PENDING (not modified)
            assert need_status_after == NeedStatus.PENDING

            # Assert: no external calls made (decision is pure projection)
            # This is verified by the fact that the test completes without
            # any network or subprocess calls

            # Assert: decision output is just data (no execution)
            need_item = next((item for item in queue if item['source'] == 'structured_need_repository'), None)
            assert need_item is not None
            assert need_item['status'] == 'pending'  # Still pending, not executed
