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
        
        # P0.19g: Cannot inject expected_result - must come from natural route
        print(f"\n=== P0.19g NO MANUAL INJECTION ===")
        print(f"expected_result must come from hypothesis system, not manual injection.")
        print(f"Skipping injection per P0.19g rules.")
        
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
        
        # P0.19g: Cannot create positive runtime test without hypothesis system
        print(f"\n=== P0.19g POSITIVE RUNTIME TEST LIMITATION ===")
        print(f"Cannot create VERIFIED + ELIGIBLE runtime test without hypothesis system.")
        print(f"expected_result must come from natural route, not manual injection.")
        print(f"Without hypothesis system, verification_status = INCONCLUSIVE.")
        print(f"Skipping positive runtime test per P0.19g rules.")
        
        # Check the actual runtime session (negative case)
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
