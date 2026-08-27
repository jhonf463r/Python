"""
R8-G4.4 Runtime Integration Test
================================

This test executes the REAL OperationalSelfExaminationService.build_review()
against the current environment to observe REAL OSES findings and their
transformation to StructuredNeed objects.

This is a RUNTIME_INTEGRATION test, not a unit test.
It does NOT inject synthetic SelfExaminationFinding objects.
It does NOT call NeedFormulationService directly.
It exercises the real path: OSES → build_review() → findings → needs
"""

import sys
import os
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "src"))

from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
from iabv_v15.infra.persistence.storage import ArtifactStorage


def test_real_build_review():
    """
    Execute real build_review() against current environment.
    This test observes the natural state without seeding any input.
    """
    print("=" * 80)
    print("R8-G4.4 RUNTIME INTEGRATION TEST")
    print("=" * 80)
    print()

    workspace = str(workspace_root)
    print(f"WORKSPACE_ROOT: {workspace}")
    print()

    # Initialize storage (required dependency)
    storage = ArtifactStorage(root=workspace)
    print(f"STORAGE_INITIALIZED: {storage is not None}")
    print()

    # Initialize OperationalSelfExaminationService with minimal dependencies
    # This will use whatever is available in the current environment
    print("INITIALIZING OperationalSelfExaminationService...")
    print()

    try:
        oses = OperationalSelfExaminationService(
            workspace_root=workspace,
            storage=storage,
            # Other dependencies are optional (None)
            run_repository=None,
            adaptive_session_repository=None,
            experiment_lab_repository=None,
            scenario_run_repository=None,
            evolution_review_service=None,
            world_model_service=None,
            autonomous_validation_cycle=None,
            adaptive_weight_layer=None,
            token_rotation_ledger=None,
        )
        print("OSES_INITIALIZED: TRUE")
        print()

        # Check if need formulation services initialized
        print(f"NEED_FORMULATION_SERVICE: {oses.need_formulation_service is not None}")
        print(f"STRUCTURED_NEED_REPOSITORY: {oses.structured_need_repository is not None}")
        print()

    except Exception as e:
        print(f"OSES_INITIALIZED: FALSE")
        print(f"ERROR: {type(e).__name__}: {e}")
        print()
        print("ZERO_FINDINGS_REASON: OSES_INITIALIZATION_FAILED")
        return

    # Execute build_review()
    print("EXECUTING build_review()...")
    print("BUILD_REVIEW_START")
    print()

    try:
        review = oses.build_review()
        print("BUILD_REVIEW_END")
        print()

        # Capture findings
        findings = review.findings if review else []
        total_findings = len(findings)

        print(f"TOTAL_FINDINGS: {total_findings}")
        print()

        if total_findings == 0:
            print("ZERO_FINDINGS_REASON: NO_FINDINGS_PRODUCED")
            print()
            return

        # Classify findings
        capability_findings = []
        operational_findings = []

        for finding in findings:
            print(f"FINDING_ID: {finding.finding_id}")
            print(f"  CATEGORY: {finding.category}")
            print(f"  TITLE: {finding.title}")
            print(f"  SUMMARY: {finding.summary}")
            print(f"  SEVERITY: {finding.severity}")
            print(f"  CONFIDENCE: {finding.confidence}")
            print()

            # Check if capability-shaped (using G4.2 classification)
            from iabv_v15.services.evolution.need_formulation_service import NeedFormulationService
            nfs = NeedFormulationService()
            if nfs._is_capability_shaped(finding):
                capability_findings.append(finding)
            else:
                operational_findings.append(finding)

        print(f"CAPABILITY_FINDINGS: {len(capability_findings)}")
        print(f"OPERATIONAL_FINDINGS: {len(operational_findings)}")
        print()

        # Check for structured needs
        if oses.structured_need_repository is not None:
            needs = oses.structured_need_repository.list_all()
            print(f"STRUCTURED_NEEDS: {len(needs)}")
            print()

            for need in needs:
                print(f"NEED_ID: {need.need_id}")
                print(f"  SOURCE_FINDING_ID: {need.source_finding_id}")
                print(f"  CATEGORY: {need.category}")
                print(f"  CAPABILITY_GAP: {need.capability_gap}")
                print(f"  CURRENT_STATE: {need.current_state}")
                print(f"  DESIRED_STATE: {need.desired_state}")
                print(f"  KNOWLEDGE_REQUIRED: {need.knowledge_required}")
                print(f"  REASON: {need.reason}")
                print(f"  EVIDENCE: {need.evidence}")
                print(f"  PRIORITY: {need.priority}")
                print(f"  STATUS: {need.status}")
                print()

    except Exception as e:
        print(f"BUILD_REVIEW_FAILED: TRUE")
        print(f"ERROR: {type(e).__name__}: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("ZERO_FINDINGS_REASON: BUILD_REVIEW_EXCEPTION")
        return

    print("=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    test_real_build_review()
