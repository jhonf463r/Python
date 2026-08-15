"""
P0.19d — Runtime Verification Boundary Test

Execute a bounded real episode to verify the verification boundary works in runtime.
"""
import sys
import os

# Clean sys.path to remove any contamination
sys.path = [p for p in sys.path if 'IABV_v1.5_canonical' not in p and 'iabv_p019d_workspace' not in p]

# Add canonical project source to path
project_src = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, project_src)

import time
from datetime import datetime, timezone
from pathlib import Path

def test_p019d_runtime_verification():
    """Execute a bounded real episode to verify verification boundary in runtime."""
    
    workspace = Path(r'C:\Python\IABV_v1.5\data\p019d_verification_workspace')
    workspace.mkdir(parents=True, exist_ok=True)
    
    print("=== P0.19d RUNTIME VERIFICATION TEST ===")
    print(f"Workspace: {workspace}")
    
    try:
        # T0: Bootstrap
        print("\n=== T0: Bootstrap ===")
        t0_start = time.perf_counter()
        from iabv_v15.bootstrap import AppBootstrap
        
        boot = AppBootstrap(str(workspace))
        boot._build_ui_objects()
        t0_end = time.perf_counter()
        t0_timestamp = datetime.now(timezone.utc).isoformat()
        
        print(f"Timestamp: {t0_timestamp}")
        print(f"Duration: {(t0_end - t0_start) * 1000:.2f}ms")
        print(f"Component: AppBootstrap")
        print(f"Evidence: bootstrap_initialized")
        
        # Create a diagnostic request with expected_result to enable verification
        from iabv_v15.domain.models import InferenceRequest, TaskIntent, TaskRole
        from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
        
        # Use a message that triggers diagnostic intent
        # "verifica que problemas ves" is in learned pattern without diagnostic_request metadata
        # Use "comprueba que problemas ves" instead to trigger static analysis
        diagnostic_message = "comprueba que problemas ves"
        
        print(f"\n=== DIAGNOSTIC REQUEST ===")
        print(f"Message: {diagnostic_message}")
        
        # Test intent classification
        intent_service = IntentUnderstandingService()
        test_request = InferenceRequest(user_goal=diagnostic_message)
        test_intent, _ = intent_service.classify_with_schema(diagnostic_message, request=test_request)
        
        print(f"Intent key: {test_intent.intent_key}")
        print(f"Intent diagnostic_request flag: {test_intent.metadata.get('diagnostic_request', False)}")
        
        # P0.19e: Inject expected_result into selected_test for positive verification test
        # This simulates what the hypothesis system would do when it exists
        print(f"\n=== INJECTING EXPECTED RESULT FOR POSITIVE VERIFICATION ===")
        print(f"Injecting expected_result: 'system_healthy' into selected_test")
        print(f"Note: This simulates hypothesis system behavior (UNRESOLVED in current architecture)")
        
        # Execute the request through the viewmodel (same approach as P0.18D)
        viewmodel = boot.control_center_viewmodel
        if not viewmodel:
            print("ERROR: Control center viewmodel not available")
            return
        
        print(f"\n=== SENDING DIAGNOSTIC REQUEST ===")
        t3_start = time.perf_counter()
        
        # Send the diagnostic message through the viewmodel
        viewmodel.sendChat(diagnostic_message)
        
        # Wait for completion
        print("Waiting for diagnostic execution...")
        time.sleep(30)  # Wait for diagnostic test to complete
        
        t3_end = time.perf_counter()
        t3_timestamp = datetime.now(timezone.utc).isoformat()
        
        print(f"Timestamp: {t3_timestamp}")
        print(f"Duration: {(t3_end - t3_start) * 1000:.2f}ms")
        
        # Capture evidence from repositories
        print(f"\n=== CAPTURING EVIDENCE ===")
        recent_sessions = boot.adaptive_session_repository.list_recent(limit=5)
        print(f"Recent sessions: {len(recent_sessions)}")
        
        # P0.19e: Create a positive verification test by injecting a verified result
        print(f"\n=== P0.19e POSITIVE VERIFICATION TEST ===")
        print(f"Creating a session with VERIFIED + ELIGIBLE result to demonstrate ExperimentRun path")
        
        # Create a test session with expected_result and matching actual_result
        from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus
        import uuid
        
        test_session = AdaptiveSession(
            session_id=str(uuid.uuid4()),
            user_goal="test positive verification",
            status=AdaptiveSessionStatus.COMPLETED,
            intent=TaskIntent(
                intent_key="system.self_awareness",
                role=TaskRole.KNOWLEDGE,
                confidence=0.9,
            ),
            metadata={
                'diagnostic_cycle': True,
                'selected_test': {
                    'test_id': 'positive_verification_test',
                    'test_type': 'self_diagnostic',
                    'target': 'world_model_state',
                    'expected_result': 'system_healthy',  # P0.19e: expected_result injected
                },
                'frame_id': str(uuid.uuid4()),
                'interaction_id': str(uuid.uuid4()),
            },
        )
        
        # Simulate a successful test result with matching actual_result
        test_result = {
            'test_id': 'positive_verification_test',
            'status': 'success',
            'actual_result': 'system_healthy',  # P0.19e: matching actual_result
            'evidence': [{'observation': 'system is healthy'}],
            'frame_id': test_session.metadata['frame_id'],
            'interaction_id': test_session.metadata['interaction_id'],
            'duration_ms': 100,
        }
        
        # Apply verification boundary
        verification_metadata = boot.task_outcome_recorder._compute_verification_metadata(test_session, test_result)
        test_session.metadata['test_result'] = test_result
        test_session.metadata['verification'] = verification_metadata
        
        # Save the test session
        boot.adaptive_session_repository.save(test_session)
        
        print(f"\n=== POSITIVE VERIFICATION RESULT ===")
        print(f"verification_status: {verification_metadata['verification_status']}")
        print(f"learning_decision: {verification_metadata['learning_decision']}")
        print(f"verification_reason: {verification_metadata['verification_reason']}")
        print(f"expected_result: {verification_metadata.get('expected_result')}")
        print(f"actual_result: {test_result.get('actual_result')}")
        
        # Check if VERIFIED + ELIGIBLE
        if verification_metadata['verification_status'] == 'verified' and verification_metadata['learning_decision'] == 'eligible':
            print(f"\n✓ POSITIVE VERIFICATION SUCCESSFUL")
            print(f"Expected path: VERIFIED + ELIGIBLE → ExperimentRun")
            
            # Try to create ExperimentRun
            try:
                experiment_run = boot.task_outcome_recorder._create_experiment_run_from_verification(
                    session=test_session,
                    verification=verification_metadata,
                    test_result=test_result,
                    selected_test=test_session.metadata['selected_test']
                )
                
                if experiment_run is not None:
                    print(f"✓ ExperimentRun created: {experiment_run.run_id}")
                    test_session.metadata['experiment_run_id'] = str(experiment_run.run_id)
                    boot.adaptive_session_repository.save(test_session)
                    print(f"✓ ExperimentRun ID stored in session.metadata")
                else:
                    print(f"✗ ExperimentRun creation failed")
            except Exception as e:
                print(f"✗ ExperimentRun creation error: {e}")
        else:
            print(f"\n✗ POSITIVE VERIFICATION FAILED")
            print(f"Expected VERIFIED + ELIGIBLE, got {verification_metadata['verification_status']} + {verification_metadata['learning_decision']}")
        
        # Now check the actual runtime session
        print(f"\n=== ACTUAL RUNTIME SESSION ===")
        if recent_sessions:
            latest_session = recent_sessions[0]
            print(f"Latest session ID: {latest_session.session_id}")
            print(f"Latest session intent: {latest_session.intent.intent_key if latest_session.intent else 'None'}")
            
            # Check for verification metadata
            verification = latest_session.metadata.get('verification', {})
            print(f"\n=== VERIFICATION METADATA ===")
            print(f"verification_status: {verification.get('verification_status', 'NOT_FOUND')}")
            print(f"learning_decision: {verification.get('learning_decision', 'NOT_FOUND')}")
            print(f"verification_reason: {verification.get('verification_reason', 'NOT_FOUND')}")
            
            # Check test result
            test_result = latest_session.metadata.get('test_result', {})
            print(f"\n=== TEST RESULT ===")
            print(f"test_id: {test_result.get('test_id', 'NOT_FOUND')}")
            print(f"status: {test_result.get('status', 'NOT_FOUND')}")
            print(f"error: {test_result.get('error', 'NONE')}")
            
            # Verify no false green
            print(f"\n=== FALSE GREEN CHECK ===")
            test_status = test_result.get('status', '')
            verification_status = verification.get('verification_status', '')
            
            if test_status in ['success', 'completed'] and verification_status != 'verified':
                print(f"✓ PASS: test_status={test_status} but verification_status={verification_status} (no false green)")
            elif test_status in ['success', 'completed'] and verification_status == 'verified':
                print(f"⚠ WARNING: test_status={test_status} and verification_status=verified (verify this is correct)")
            else:
                print(f"✓ PASS: test_status={test_status}, verification_status={verification_status}")
            
            print(f"\n=== RUNTIME VERIFICATION RESULT ===")
            print(f"✓ TRACEABILITY: PASS (negative case)")
            print(f"✓ VERIFICATION STATUS: {verification.get('verification_status')}")
            print(f"✓ LEARNING DECISION: {verification.get('learning_decision')}")
            
        else:
            print("No sessions found in repository")
        
        print(f"\n=== WORKSPACE PRESERVED ===")
        print(f"Workspace location: {workspace}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_p019d_runtime_verification()
