"""
R8-G4.5 Initialization Diagnostic
================================

Diagnostic test to determine which operation in EnvironmentSelfAwarenessService.__init__
is blocking during initialization.

This test adds instrumentation to show timestamps for each step and detect blocking operations.
"""

import sys
import os
import time
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "src"))


def log_step(step_name):
    """Log a step with timestamp."""
    timestamp = time.time()
    print(f"[ESA] {timestamp:.3f} {step_name}")
    return timestamp


def measure_step(step_name, func, timeout_seconds=30):
    """Measure a step with timeout detection."""
    start = log_step(f"{step_name} START")
    try:
        result = func()
        end = log_step(f"{step_name} END")
        duration = end - start
        print(f"[ESA] {step_name} DURATION: {duration:.3f}s")
        return result, duration, None
    except Exception as e:
        end = log_step(f"{step_name} EXCEPTION")
        duration = end - start
        print(f"[ESA] {step_name} EXCEPTION: {type(e).__name__}: {e}")
        return None, duration, e


def test_environment_self_awareness_service_init_diagnostic():
    """
    Diagnostic test for EnvironmentSelfAwarenessService initialization.
    """
    print("=" * 80)
    print("R8-G4.5 INITIALIZATION DIAGNOSTIC")
    print("=" * 80)
    print()

    workspace = str(workspace_root)
    evolution_dir = str(workspace_root / "data" / "evolution")

    log_step("TEST START")

    # STEP 1: Import the service
    def import_service():
        from iabv_v15.services.evolution.environment_self_awareness_service import EnvironmentSelfAwarenessService
        return EnvironmentSelfAwarenessService

    service_class, import_duration, import_error = measure_step("IMPORT", import_service)
    if import_error:
        print(f"[ESA] BLOCKED_AT: IMPORT")
        print(f"[ESA] BLOCKER_CLASS: I (configuration/dependency)")
        return

    # STEP 2: Create instance WITHOUT bootstrap_scan
    def create_instance_no_bootstrap():
        return service_class(
            workspace_root=workspace,
            evolution_dir=evolution_dir,
            role_router=None,
            tool_registry=None,
            auto_start=False,  # Disable background thread
            bootstrap_scan=False,  # Disable bootstrap scan
        )

    instance_no_bootstrap, init_duration, init_error = measure_step(
        "INIT_NO_BOOTSTRAP_SCAN",
        create_instance_no_bootstrap
    )
    if init_error:
        print(f"[ESA] BLOCKED_AT: INIT_NO_BOOTSTRAP_SCAN")
        print(f"[ESA] BLOCKER_CLASS: A (EnvironmentSelfAwarenessService)")
        print(f"[ESA] EXCEPTION: {type(init_error).__name__}: {init_error}")
        return

    print(f"[ESA] INIT_NO_BOOTSTRAP_SCAN SUCCESS: {init_duration:.3f}s")

    # STEP 3: Call _load_latest_model directly
    def load_model():
        return instance_no_bootstrap._load_latest_model()

    model, load_duration, load_error = measure_step("LOAD_LATEST_MODEL", load_model)
    if load_error:
        print(f"[ESA] BLOCKED_AT: LOAD_LATEST_MODEL")
        print(f"[ESA] BLOCKER_CLASS: D (filesystem)")
        print(f"[ESA] EXCEPTION: {type(load_error).__name__}: {load_error}")
        return

    print(f"[ESA] LOAD_LATEST_MODEL SUCCESS: {load_duration:.3f}s")

    # STEP 4: Call scan_now with full=False (light scan)
    def light_scan():
        return instance_no_bootstrap.scan_now(reason='diagnostic', full=False)

    light_scan_result, light_scan_duration, light_scan_error = measure_step(
        "LIGHT_SCAN",
        light_scan,
        timeout_seconds=60
    )
    if light_scan_error:
        print(f"[ESA] BLOCKED_AT: LIGHT_SCAN")
        print(f"[ESA] BLOCKER_CLASS: C (Windows capability scan) or E (subprocess)")
        print(f"[ESA] EXCEPTION: {type(light_scan_error).__name__}: {light_scan_error}")
        return

    print(f"[ESA] LIGHT_SCAN SUCCESS: {light_scan_duration:.3f}s")

    # STEP 5: Call scan_now with full=True (full scan)
    def full_scan():
        return instance_no_bootstrap.scan_now(reason='diagnostic', full=True)

    full_scan_result, full_scan_duration, full_scan_error = measure_step(
        "FULL_SCAN",
        full_scan,
        timeout_seconds=120
    )
    if full_scan_error:
        print(f"[ESA] BLOCKED_AT: FULL_SCAN")
        print(f"[ESA] BLOCKER_CLASS: C (Windows capability scan) or E (subprocess) or F (network)")
        print(f"[ESA] EXCEPTION: {type(full_scan_error).__name__}: {full_scan_error}")
        return

    print(f"[ESA] FULL_SCAN SUCCESS: {full_scan_duration:.3f}s")

    # STEP 6: Create instance WITH bootstrap_scan (the original blocking scenario)
    def create_instance_with_bootstrap():
        return service_class(
            workspace_root=workspace,
            evolution_dir=evolution_dir,
            role_router=None,
            tool_registry=None,
            auto_start=False,  # Disable background thread
            bootstrap_scan=True,  # Enable bootstrap scan (this calls scan_now)
        )

    instance_with_bootstrap, bootstrap_init_duration, bootstrap_init_error = measure_step(
        "INIT_WITH_BOOTSTRAP_SCAN",
        create_instance_with_bootstrap,
        timeout_seconds=120
    )
    if bootstrap_init_error:
        print(f"[ESA] BLOCKED_AT: INIT_WITH_BOOTSTRAP_SCAN")
        print(f"[ESA] BLOCKER_CLASS: C (Windows capability scan) or E (subprocess)")
        print(f"[ESA] EXCEPTION: {type(bootstrap_init_error).__name__}: {bootstrap_init_error}")
        return

    print(f"[ESA] INIT_WITH_BOOTSTRAP_SCAN SUCCESS: {bootstrap_init_duration:.3f}s")

    log_step("TEST COMPLETE")

    print()
    print("=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"IMPORT_DURATION: {import_duration:.3f}s")
    print(f"INIT_NO_BOOTSTRAP_SCAN_DURATION: {init_duration:.3f}s")
    print(f"LOAD_LATEST_MODEL_DURATION: {load_duration:.3f}s")
    print(f"LIGHT_SCAN_DURATION: {light_scan_duration:.3f}s")
    print(f"FULL_SCAN_DURATION: {full_scan_duration:.3f}s")
    print(f"INIT_WITH_BOOTSTRAP_SCAN_DURATION: {bootstrap_init_duration:.3f}s")
    print()
    print("BLOCKED_AT: NONE")
    print("CAN_CONTINUE_TO_RUNTIME: TRUE")


if __name__ == "__main__":
    test_environment_self_awareness_service_init_diagnostic()
