"""
R8-G4.5 Light Scan Stack Capture
==================================

Diagnostic test to capture the Python stack while LIGHT_SCAN is blocked.
Uses faulthandler to dump traceback after a timeout.
"""

import sys
import os
import time
import faulthandler
import signal
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "src"))


def log_step(step_name):
    """Log a step with timestamp."""
    timestamp = time.time()
    print(f"[STACK_CAPTURE] {timestamp:.3f} {step_name}")
    return timestamp


def test_light_scan_stack_capture():
    """
    Diagnostic test to capture Python stack while LIGHT_SCAN is blocked.
    """
    print("=" * 80)
    print("R8-G4.5 LIGHT SCAN STACK CAPTURE")
    print("=" * 80)
    print()

    workspace = str(workspace_root)
    evolution_dir = str(workspace_root / "data" / "evolution")

    log_step("TEST START")
    print(f"PID: {os.getpid()}")
    print()

    # Configure faulthandler to dump traceback after 15 seconds
    # This will capture the stack if LIGHT_SCAN blocks
    faulthandler.enable(file=sys.stderr, all_threads=True)
    log_step("FAULTHANDLER_ENABLED")

    # Schedule a traceback dump after 15 seconds
    # This will show where the process is stuck
    faulthandler.dump_traceback_later(timeout=15, repeat=False, file=sys.stderr)
    log_step("TRACEBACK_DUMP_SCHEDULED_15s")

    try:
        # Import and create instance WITHOUT bootstrap_scan
        log_step("IMPORT_START")
        from iabv_v15.services.evolution.environment_self_awareness_service import EnvironmentSelfAwarenessService
        log_step("IMPORT_END")

        log_step("INIT_NO_BOOTSTRAP_START")
        instance = EnvironmentSelfAwarenessService(
            workspace_root=workspace,
            evolution_dir=evolution_dir,
            role_router=None,
            tool_registry=None,
            auto_start=False,
            bootstrap_scan=False,
        )
        log_step("INIT_NO_BOOTSTRAP_END")

        # Call current_model() (should be fast)
        log_step("CURRENT_MODEL_START")
        current_model = instance.current_model()
        log_step("CURRENT_MODEL_END")

        # Call scan_now with full=False (light scan) - this is where it blocks
        log_step("LIGHT_SCAN_START")
        light_scan_result = instance.scan_now(reason='diagnostic', full=False)
        log_step("LIGHT_SCAN_END")

        # If we reach here, LIGHT_SCAN completed
        log_step("LIGHT_SCAN_COMPLETED")

        # Cancel the scheduled traceback dump
        faulthandler.cancel_dump_traceback_later()
        log_step("TRACEBACK_DUMP_CANCELLED")

        print()
        print("=" * 80)
        print("LIGHT_SCAN COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("LIGHT_SCAN_COMPLETED = TRUE")
        print("LIGHT_SCAN_TIMEOUT = FALSE")
        print("BLOCKED_AT_FILE = NONE")
        print("BLOCKED_AT_LINE = NONE")
        print("BLOCKED_AT_FUNCTION = NONE")
        print()
        print("ROOT_CAUSE_CLASS = NONE (NO BLOCKER)")
        print("CONFIDENCE = HIGH")
        print()
        print("NEXT_STEP = CONTINUE_TO_G4_5_RUNTIME")

    except Exception as e:
        # Cancel the scheduled traceback dump
        faulthandler.cancel_dump_traceback_later()
        log_step("TRACEBACK_DUMP_CANCELLED")

        log_step("EXCEPTION")
        print()
        print("=" * 80)
        print("LIGHT_SCAN EXCEPTION")
        print("=" * 80)
        print()
        print(f"EXCEPTION_TYPE: {type(e).__name__}")
        print(f"EXCEPTION_MESSAGE: {e}")
        print()
        print("LIGHT_SCAN_COMPLETED = FALSE")
        print("LIGHT_SCAN_TIMEOUT = FALSE")
        print("BLOCKED_AT_FILE = EXCEPTION")
        print("BLOCKED_AT_FUNCTION = EXCEPTION")
        print()
        print("ROOT_CAUSE_CLASS = EXCEPTION")
        print("CONFIDENCE = HIGH")
        print()
        print("NEXT_STEP = REVIEW_EXCEPTION")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_light_scan_stack_capture()
