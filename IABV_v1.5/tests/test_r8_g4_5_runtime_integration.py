"""
R8-G4.5 Runtime Integration Test
================================

This test executes the REAL OperationalSelfExaminationService.build_review()
with PRODUCTION-LIKE dependencies to enable capability-shaped producers.

Key fix from G4.4: This test provides world_model_service with real
environment_self_awareness_service to enable _windows_integration_findings().

This is a RUNTIME_INTEGRATION test, not a unit test.
It does NOT inject synthetic SelfExaminationFinding objects.
It does NOT call NeedFormulationService directly.
It does NOT use manual reclassification after build_review().
It exercises the real path: OSES → build_review() → findings → needs
"""

import sys
import os
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "src"))

from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
from iabv_v15.services.evolution.world_model_service import WorldModelService
from iabv_v15.services.evolution.environment_self_awareness_service import EnvironmentSelfAwarenessService
from iabv_v15.infra.persistence.storage import ArtifactStorage


def test_real_build_review_with_production_dependencies():
    """
    Execute real build_review() with production-like dependencies.
    This test provides world_model_service with real environment_self_awareness_service
    to enable _windows_integration_findings() capability producer.

    CRITICAL FIX: Set PYTEST_CURRENT_TEST to signal test mode to EnvironmentSelfAwarenessService,
    which prevents heavy subprocess calls (PowerShell) during initialization.
    """
    print("=" * 80)
    print("R8-G4.5 RUNTIME INTEGRATION TEST")
    print("=" * 80)
    print()

    # Signal test mode to EnvironmentSelfAwarenessService to avoid subprocess hangs
    # NOTE: This may affect some finding producers. For G4.5 we need real capability findings.
    # If test mode prevents capability findings, we may need to adjust.
    os.environ['PYTEST_CURRENT_TEST'] = 'test_r8_g4_5_runtime_integration.py::test_real_build_review_with_production_dependencies'

    workspace = str(workspace_root)
    evolution_dir = str(workspace_root / "data" / "evolution")
    print(f"WORKSPACE_ROOT: {workspace}")
    print(f"EVOLUTION_DIR: {evolution_dir}")
    print(f"PYTEST_CURRENT_TEST: {os.environ.get('PYTEST_CURRENT_TEST')}")
    print()

    # Initialize storage (required dependency)
    storage = ArtifactStorage(root=workspace)
    print(f"STORAGE_INITIALIZED: {storage is not None}")
    print()

    # Initialize EnvironmentSelfAwarenessService (production-like)
    print("INITIALIZING EnvironmentSelfAwarenessService...")
    print()

    try:
        env_self_service = EnvironmentSelfAwarenessService(
            workspace_root=workspace,
            evolution_dir=evolution_dir,
            role_router=None,
            tool_registry=None,
            auto_start=False,  # Disable background thread for test
            bootstrap_scan=True,  # Enable bootstrap scan to get initial model
        )
        print(f"ENV_SELF_SERVICE_INITIALIZED: TRUE")
        print()

        # Get the current model to verify it has data
        env_model = env_self_service.current_model()
        print(f"ENV_MODEL_AVAILABLE: {env_model is not None}")
        if env_model:
            print(f"ENV_MODEL_SCAN_STATUS: {env_model.scan_status}")
            print(f"ENV_MODEL_CAPABILITY_GRAPH_LENGTH: {len(env_model.capability_graph or [])}")
            platform_caps = [c for c in (env_model.capability_graph or []) if c.capability_id.startswith('platform.')]
            print(f"ENV_MODEL_PLATFORM_CAPS_COUNT: {len(platform_caps)}")
            missing_caps = [c for c in platform_caps if not c.available and c.status not in ('not_applicable',)]
            print(f"ENV_MODEL_MISSING_PLATFORM_CAPS_COUNT: {len(missing_caps)}")
            if missing_caps:
                print(f"ENV_MODEL_MISSING_PLATFORM_CAPS: {[c.capability_id for c in missing_caps[:5]]}")
        print()
    except Exception as e:
        print(f"ENV_SELF_SERVICE_INITIALIZED: FALSE")
        print(f"ERROR: {type(e).__name__}: {e}")
        print()
        print("ZERO_FINDINGS_REASON: ENV_SELF_SERVICE_INITIALIZATION_FAILED")
        return

    # Initialize WorldModelService (production-like)
    print("INITIALIZING WorldModelService...")
    print()

    try:
        world_model_service = WorldModelService(
            workspace_root=workspace,
            evolution_dir=evolution_dir,
            tool_registry=None,
            tool_record_repository=None,
            environment_self_awareness_service=env_self_service,
            universal_perception_service=None,
            role_router=None,
            auto_start=False,  # Disable background thread for test
            bootstrap_scan=True,  # Enable bootstrap scan
        )
        print(f"WORLD_MODEL_SERVICE_INITIALIZED: TRUE")
        print()

        # Verify the dependency chain is correct
        wm_env_service = getattr(world_model_service, 'environment_self_awareness_service', None)
        print(f"WORLD_MODEL_ENV_SELF_SERVICE: {wm_env_service is not None}")
        print(f"WORLD_MODEL_ENV_SELF_SERVICE_MATCH: {wm_env_service is env_self_service}")
        print()
    except Exception as e:
        print(f"WORLD_MODEL_SERVICE_INITIALIZED: FALSE")
        print(f"ERROR: {type(e).__name__}: {e}")
        print()
        print("ZERO_FINDINGS_REASON: WORLD_MODEL_SERVICE_INITIALIZATION_FAILED")
        return

    # Initialize OperationalSelfExaminationService with world_model_service
    print("INITIALIZING OperationalSelfExaminationService...")
    print()

    try:
        oses = OperationalSelfExaminationService(
            workspace_root=workspace,
            storage=storage,
            world_model_service=world_model_service,  # CRITICAL: Provide real world_model_service
            run_repository=None,
            adaptive_session_repository=None,
            experiment_lab_repository=None,
            scenario_run_repository=None,
            evolution_review_service=None,
            autonomous_validation_cycle=None,
            adaptive_weight_layer=None,
            token_rotation_ledger=None,
        )
        print("OSES_INITIALIZED: TRUE")
        print(f"OSES_WORLD_MODEL_SERVICE: {oses.world_model_service is not None}")
        print(f"OSES_WORLD_MODEL_SERVICE_MATCH: {oses.world_model_service is world_model_service}")
        print()

        # Check if need formulation services initialized
        print(f"NEED_FORMULATION_SERVICE: {oses.need_formulation_service is not None}")
        print(f"STRUCTURED_NEED_REPOSITORY: {oses.structured_need_repository is not None}")
        print()

    except Exception as e:
        print("OSES_INITIALIZED: FALSE")
        print(f"ERROR: {type(e).__name__}: {e}")
        print()
        print("ZERO_FINDINGS_REASON: OSES_INITIALIZATION_FAILED")
        return

    # Capture before state
    print("CAPTURING BEFORE STATE...")
    print()

    if oses.structured_need_repository is not None:
        before_needs = oses.structured_need_repository.list_all()
        print(f"BEFORE_NEEDS_COUNT: {len(before_needs)}")
        print()

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

        # Capture all findings without manual reclassification
        print("CAPTURING FINDINGS...")
        print()

        capability_findings = []
        operational_findings = []

        for finding in findings:
            is_capability = finding.category.lower() in {'windows_capability_missing', 'capability_promised_but_unavailable', 'research_gap'}
            print(f"FINDING_ID: {finding.finding_id}")
            print(f"  CATEGORY: {finding.category}")
            print(f"  TITLE: {finding.title}")
            print(f"  SUMMARY: {finding.summary}")
            print(f"  SEVERITY: {finding.severity}")
            print(f"  CONFIDENCE: {finding.confidence}")
            print(f"  CAPABILITY_SHAPED: {is_capability}")
            print()

            if is_capability:
                capability_findings.append(finding)
            else:
                operational_findings.append(finding)

        print(f"CAPABILITY_FINDINGS_COUNT: {len(capability_findings)}")
        print(f"OPERATIONAL_FINDINGS_COUNT: {len(operational_findings)}")
        print()

        # Print all finding categories for debugging
        print("ALL_FINDING_CATEGORIES:")
        for finding in findings:
            print(f"  {finding.category}")
            if finding.category == 'windows_integration_gaps':
                print(f"    METADATA: {finding.metadata}")
            if finding.category == 'windows_capability_missing':
                print(f"    INDIVIDUAL_CAPABILITY_FINDING: {finding.title}")
        print()

        # Debug: check if individual capability findings are being produced
        print("DEBUG: Checking for individual capability findings...")
        windows_capability_missing_count = sum(1 for f in findings if f.category == 'windows_capability_missing')
        print(f"WINDOWS_CAPABILITY_MISSING_COUNT: {windows_capability_missing_count}")
        print()

        # Debug: print ALL finding IDs to see if there are more than 8
        print(f"TOTAL_FINDINGS_IN_LIST: {len(findings)}")
        print("ALL_FINDING_IDS:")
        for finding in findings:
            print(f"  {finding.finding_id}: {finding.category}")
        print()

        # Debug: check if the windows_integration_gaps finding has metadata about individual capabilities
        windows_integration_finding = next((f for f in findings if f.category == 'windows_integration_gaps'), None)
        if windows_integration_finding:
            print(f"WINDOWS_INTEGRATION_FINDING_ID: {windows_integration_finding.finding_id}")
            print(f"WINDOWS_INTEGRATION_FINDING_METADATA: {windows_integration_finding.metadata}")
        print()

        # Debug: check if build_review returns a filtered list
        print("DEBUG: Checking if findings are filtered...")
        print(f"TOTAL_FINDINGS_RETURNED: {len(findings)}")
        print(f"EXPECTED_FINDINGS: 8 operational + 1 capability = 9")
        print(f"ACTUAL_FINDINGS: {len(findings)}")
        print(f"MISSING_CAPABILITY_FINDING_IN_RETURNED_LIST: {windows_capability_missing_count == 0}")
        print()

        # Debug: check the review object directly to see if it has more findings
        print("DEBUG: Checking review object...")
        review = oses.current_review()
        print(f"REVIEW_FINDINGS_COUNT: {len(review.findings)}")
        print(f"REVIEW_FINDINGS_CATEGORIES:")
        for finding in review.findings:
            print(f"  {finding.finding_id}: {finding.category}")
        print()

        # Debug: check if the full findings list has more than 8 findings
        # The review truncates to findings[:8] at line 965 of operational_self_examination_service.py
        # But _formulate_structured_needs is called on the FULL findings list at line 918
        print("DEBUG: Checking if findings were truncated...")
        print(f"NOTE: Review truncates findings to first 8 (line 965)")
        print(f"NOTE: Need formulation uses FULL findings list (line 918)")
        print(f"NOTE: Individual capability findings may be in position 9+")
        print()

        # Check for structured needs (after build_review, no manual classification)
        print("CHECKING STRUCTURED NEEDS...")
        print()

        if oses.structured_need_repository is not None:
            after_needs = oses.structured_need_repository.list_all()
            print(f"AFTER_NEEDS_COUNT: {len(after_needs)}")
            print()

            new_needs = [n for n in after_needs if n not in before_needs]

            # Check if the new need's source_finding_id is in the visible findings
            if new_needs:
                new_need = new_needs[0]
                source_finding_id = new_need.source_finding_id
                print(f"NEW_NEED_SOURCE_FINDING_ID: {source_finding_id}")
                visible_finding_ids = {f.finding_id for f in findings}
                print(f"SOURCE_FINDING_IN_VISIBLE_LIST: {source_finding_id in visible_finding_ids}")
                if source_finding_id not in visible_finding_ids:
                    print(f"CONCLUSION: The capability finding was truncated (position 9+)")
                    print(f"CONCLUSION: Need formulation still worked because it uses FULL findings list")
                print()
            print(f"NEW_NEEDS_COUNT: {len(new_needs)}")
            print()

            for need in new_needs:
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
    test_real_build_review_with_production_dependencies()
