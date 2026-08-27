"""R10 — Forensic Capture for StructuredNeed → Decision.

Captures raw runtime evidence for the decision mechanism.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from iabv_v15.domain.models import (
    StructuredNeed,
    NeedStatus,
)
from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.control_master_service import ControlMasterService
from iabv_v15.services.evolution.structured_need_repository import StructuredNeedRepository


def main() -> None:
    """Capture forensic evidence for R10 decision mechanism."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evolution_dir = Path(tmpdir)
        need_repo = StructuredNeedRepository(evolution_dir)
        storage = ArtifactStorage(tmpdir)
        control_repo = ControlMasterRepository(storage)

        # BEFORE STATE: Capture initial state
        print("=== R10_FORENSIC_BEFORE_STATE ===")
        needs_before = need_repo.list_all()
        print(f"NEED_COUNT_BEFORE: {len(needs_before)}")
        for need in needs_before:
            print(f"  NEED_ID: {need.need_id}")
            print(f"  STATUS: {need.status.value}")
            print(f"  PRIORITY: {need.priority}")
        print("=== END BEFORE_STATE ===")

        # Create test needs
        critical_need = StructuredNeed(
            need_id="need_forensic_critical",
            source_finding_id="finding_forensic_123",
            category="windows_capability_missing",
            capability_gap="Falta: Capacidad crítica forense",
            current_state="",
            desired_state="Dependencia: crítica forense",
            knowledge_required="windows_capability_missing",
            reason="Prueba forense crítica",
            evidence=[],
            priority="critical",
            status=NeedStatus.PENDING,
        )

        medium_need = StructuredNeed(
            need_id="need_forensic_medium",
            source_finding_id="finding_forensic_456",
            category="windows_capability_missing",
            capability_gap="Falta: Capacidad media forense",
            current_state="",
            desired_state="Dependencia: media forense",
            knowledge_required="windows_capability_missing",
            reason="Prueba forense media",
            evidence=[],
            priority="medium",
            status=NeedStatus.PENDING,
        )

        need_repo.upsert(critical_need)
        need_repo.upsert(medium_need)

        # AFTER STATE: Capture state after needs created
        print("=== R10_FORENSIC_AFTER_STATE ===")
        needs_after = need_repo.list_all()
        print(f"NEED_COUNT_AFTER: {len(needs_after)}")
        for need in needs_after:
            print(f"  NEED_ID: {need.need_id}")
            print(f"  STATUS: {need.status.value}")
            print(f"  PRIORITY: {need.priority}")
            print(f"  SOURCE_FINDING_ID: {need.source_finding_id}")
        print("=== END AFTER_STATE ===")

        # DECISION RUNTIME: Capture decision output
        print("=== R10_FORENSIC_DECISION_RUNTIME ===")
        service = ControlMasterService(
            repository=control_repo,
            structured_need_repository=need_repo,
        )

        queue = service.current_work_queue(limit=10)
        need_items = [item for item in queue if item['source'] == 'structured_need_repository']

        print(f"QUEUE_SIZE: {len(queue)}")
        print(f"NEED_ITEMS_COUNT: {len(need_items)}")

        for item in need_items:
            print(f"  ITEM_ID: {item['id']}")
            print(f"  TITLE: {item['title']}")
            print(f"  STATUS: {item['status']}")
            print(f"  PRIORITY_SCORE: {item['priority_score']}")
            print(f"  PRIORITY_LABEL: {item['priority_label']}")
            print(f"  SOURCE: {item['source']}")
            print(f"  EVIDENCE_REFS: {item['evidence_refs']}")
            print(f"  NEXT_ACTION: {item['next_action']}")
            print(f"  REASON: {item['reason']}")
            print(f"  SCORE_BREAKDOWN: {item['score_breakdown']}")
        print("=== END DECISION_RUNTIME ===")

        # PROVENANCE CHECK: Verify traceability
        print("=== R10_FORENSIC_PROVENANCE ===")
        critical_item = next((item for item in need_items if item['id'] == 'need:need_forensic_critical'), None)
        medium_item = next((item for item in need_items if item['id'] == 'need:need_forensic_medium'), None)

        if critical_item:
            print(f"CRITICAL_NEED_FOUND: True")
            print(f"CRITICAL_NEED_ID: {critical_item['id']}")
            print(f"CRITICAL_EVIDENCE_REFS: {critical_item['evidence_refs']}")
            print(f"CRITICAL_SOURCE_FINDING_PRESERVED: {critical_item['evidence_refs'] == ['finding_forensic_123']}")
        else:
            print("CRITICAL_NEED_FOUND: False")

        if medium_item:
            print(f"MEDIUM_NEED_FOUND: True")
            print(f"MEDIUM_NEED_ID: {medium_item['id']}")
            print(f"MEDIUM_EVIDENCE_REFS: {medium_item['evidence_refs']}")
            print(f"MEDIUM_SOURCE_FINDING_PRESERVED: {medium_item['evidence_refs'] == ['finding_forensic_456']}")
        else:
            print("MEDIUM_NEED_FOUND: False")

        # DETERMINISM CHECK: Verify critical has higher score
        if critical_item and medium_item:
            print(f"CRITICAL_HIGHER_THAN_MEDIUM: {critical_item['priority_score'] > medium_item['priority_score']}")
        print("=== END PROVENANCE ===")


if __name__ == "__main__":
    main()
