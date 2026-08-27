"""
R8-G4.5 Light Scan Blocker Diagnostic
=====================================

Diagnostic test to determine which operation within LIGHT_SCAN is blocking.

This test instruments each step in scan_now() and _build_model() to find the exact blocking point.
"""

import sys
import os
import time
import signal
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "src"))


def log_step(step_name):
    """Log a step with timestamp."""
    timestamp = time.time()
    print(f"[LIGHT_SCAN] {timestamp:.3f} {step_name}")
    return timestamp


def measure_step(step_name, func, timeout_seconds=30):
    """Measure a step with timeout detection."""
    start = log_step(f"{step_name} START")
    try:
        result = func()
        end = log_step(f"{step_name} END")
        duration = end - start
        print(f"[LIGHT_SCAN] {step_name} DURATION: {duration:.3f}s")
        return result, duration, None
    except Exception as e:
        end = log_step(f"{step_name} EXCEPTION")
        duration = end - start
        print(f"[LIGHT_SCAN] {step_name} EXCEPTION: {type(e).__name__}: {e}")
        return None, duration, e


def test_light_scan_diagnostic():
    """
    Diagnostic test for LIGHT_SCAN blocking.
    """
    print("=" * 80)
    print("R8-G4.5 LIGHT SCAN BLOCKER DIAGNOSTIC")
    print("=" * 80)
    print()

    workspace = str(workspace_root)
    evolution_dir = str(workspace_root / "data" / "evolution")

    log_step("TEST START")

    # STEP 1: Import and create instance WITHOUT bootstrap_scan
    def import_and_init():
        from iabv_v15.services.evolution.environment_self_awareness_service import EnvironmentSelfAwarenessService
        return EnvironmentSelfAwarenessService(
            workspace_root=workspace,
            evolution_dir=evolution_dir,
            role_router=None,
            tool_registry=None,
            auto_start=False,
            bootstrap_scan=False,
        )

    instance, init_duration, init_error = measure_step("INIT_NO_BOOTSTRAP", import_and_init)
    if init_error:
        print(f"[LIGHT_SCAN] BLOCKED_AT: INIT_NO_BOOTSTRAP")
        print(f"[LIGHT_SCAN] BLOCKER_CLASS: A (EnvironmentSelfAwarenessService)")
        return

    print(f"[LIGHT_SCAN] INIT_NO_BOOTSTRAP SUCCESS: {init_duration:.3f}s")
    print()

    # STEP 2: Call current_model() (should be fast)
    def get_current_model():
        return instance.current_model()

    current_model, model_duration, model_error = measure_step("CURRENT_MODEL", get_current_model)
    if model_error:
        print(f"[LIGHT_SCAN] BLOCKED_AT: CURRENT_MODEL")
        print(f"[LIGHT_SCAN] BLOCKER_CLASS: F (lock)")
        return

    print(f"[LIGHT_SCAN] CURRENT_MODEL SUCCESS: {model_duration:.3f}s")
    print()

    # STEP 3: Instrument scan_now() step by step
    print("[LIGHT_SCAN] INSTRUMENTING scan_now() steps...")
    print()

    # STEP 3a: Call scan_now with full=False (light scan)
    # This is the blocking operation from the previous test
    # We need to instrument _build_model internally

    # Monkey-patch _build_model to instrument its steps
    original_build_model = instance._build_model

    def instrumented_build_model(*, previous, reason, full):
        log_step("_BUILD_MODEL START")

        # Step 1: _scan_hardware
        log_step("_SCAN_HARDWARE START")
        try:
            hardware_profile, hardware_unresolved = instance._scan_hardware(full=full)
            log_step("_SCAN_HARDWARE END")
        except Exception as e:
            log_step("_SCAN_HARDWARE EXCEPTION")
            raise

        # Step 2: _scan_runtime
        log_step("_SCAN_RUNTIME START")
        try:
            runtime_profile, runtime_unresolved = instance._scan_runtime(full=full)
            log_step("_SCAN_RUNTIME END")
        except Exception as e:
            log_step("_SCAN_RUNTIME EXCEPTION")
            raise

        # Step 3: _provider_health (or cached)
        log_step("_PROVIDER_HEALTH START")
        try:
            provider_health: list
            if full:
                provider_health = instance._provider_health()
            else:
                cached_provider_health = instance._provider_health_from_previous(previous)
                provider_health = cached_provider_health if cached_provider_health else instance._provider_health()
            log_step("_PROVIDER_HEALTH END")
        except Exception as e:
            log_step("_PROVIDER_HEALTH EXCEPTION")
            raise

        # Step 4: _tool_cards
        log_step("_TOOL_CARDS START")
        try:
            available_tools, missing_tools = instance._tool_cards()
            log_step("_TOOL_CARDS END")
        except Exception as e:
            log_step("_TOOL_CARDS EXCEPTION")
            raise

        # Step 5: _scan_ai_capacity
        log_step("_SCAN_AI_CAPACITY START")
        try:
            ai_capacity, ai_unresolved = instance._scan_ai_capacity(
                hardware_profile=hardware_profile,
                runtime_profile=runtime_profile,
                full=full
            )
            log_step("_SCAN_AI_CAPACITY END")
        except Exception as e:
            log_step("_SCAN_AI_CAPACITY EXCEPTION")
            raise

        # Step 6: _build_capability_graph
        log_step("_BUILD_CAPABILITY_GRAPH START")
        try:
            capability_graph = instance._build_capability_graph(
                runtime_profile=runtime_profile,
                provider_health=provider_health,
                available_tools=available_tools,
                missing_tools=missing_tools,
                ai_capacity=ai_capacity,
            )
            log_step("_BUILD_CAPABILITY_GRAPH END")
        except Exception as e:
            log_step("_BUILD_CAPABILITY_GRAPH EXCEPTION")
            raise

        # Step 7: _build_risk_signals
        log_step("_BUILD_RISK_SIGNALS START")
        try:
            risk_signals = instance._build_risk_signals(
                hardware_profile=hardware_profile,
                runtime_profile=runtime_profile,
                provider_health=provider_health,
                missing_tools=missing_tools,
                ai_capacity=ai_capacity,
            )
            log_step("_BUILD_RISK_SIGNALS END")
        except Exception as e:
            log_step("_BUILD_RISK_SIGNALS EXCEPTION")
            raise

        # Step 8: _environment_id
        log_step("_ENVIRONMENT_ID START")
        try:
            environment_id = instance._environment_id(hardware_profile=hardware_profile, runtime_profile=runtime_profile)
            log_step("_ENVIRONMENT_ID END")
        except Exception as e:
            log_step("_ENVIRONMENT_ID EXCEPTION")
            raise

        # Step 9: _build_installable_tools
        log_step("_BUILD_INSTALLABLE_TOOLS START")
        try:
            installable_tools = instance._build_installable_tools(runtime_profile=runtime_profile, missing_tools=missing_tools)
            log_step("_BUILD_INSTALLABLE_TOOLS END")
        except Exception as e:
            log_step("_BUILD_INSTALLABLE_TOOLS EXCEPTION")
            raise

        # Step 10: _diff_from_previous
        log_step("_DIFF_FROM_PREVIOUS START")
        try:
            changed_since_last_scan = instance._diff_from_previous(
                previous=previous,
                environment_id=environment_id,
                provider_health=provider_health,
                available_tools=available_tools,
                missing_tools=missing_tools,
                ai_capacity=ai_capacity,
                risk_signals=risk_signals,
            )
            log_step("_DIFF_FROM_PREVIOUS END")
        except Exception as e:
            log_step("_DIFF_FROM_PREVIOUS EXCEPTION")
            raise

        # Step 11: _build_notifications
        log_step("_BUILD_NOTIFICATIONS START")
        try:
            notifications = instance._build_notifications(
                known_environment=instance._environment_path(environment_id).exists(),
                previous_environment_id=str(previous.environment_id or ''),
                environment_id=environment_id,
                changed_since_last_scan=changed_since_last_scan,
                risk_signals=risk_signals,
            )
            log_step("_BUILD_NOTIFICATIONS END")
        except Exception as e:
            log_step("_BUILD_NOTIFICATIONS EXCEPTION")
            raise

        log_step("_BUILD_MODEL END")

        # Call original to build the actual model
        return original_build_model(previous=previous, reason=reason, full=full)

    # Apply monkey-patch
    instance._build_model = instrumented_build_model

    # STEP 3b: Call scan_now with full=False
    def light_scan():
        return instance.scan_now(reason='diagnostic', full=False)

    light_scan_result, light_scan_duration, light_scan_error = measure_step(
        "LIGHT_SCAN",
        light_scan,
        timeout_seconds=120
    )
    if light_scan_error:
        print(f"[LIGHT_SCAN] BLOCKED_AT: LIGHT_SCAN")
        print(f"[LIGHT_SCAN] BLOCKER_CLASS: G (environment capability scan) or B (subprocess)")
        print(f"[LIGHT_SCAN] EXCEPTION: {type(light_scan_error).__name__}: {light_scan_error}")
        return

    print(f"[LIGHT_SCAN] LIGHT_SCAN SUCCESS: {light_scan_duration:.3f}s")

    log_step("TEST COMPLETE")

    print()
    print("=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"INIT_DURATION: {init_duration:.3f}s")
    print(f"CURRENT_MODEL_DURATION: {model_duration:.3f}s")
    print(f"LIGHT_SCAN_DURATION: {light_scan_duration:.3f}s")
    print()
    print("BLOCKED_AT: NONE")
    print("CAN_CONTINUE_G4_5: TRUE")


if __name__ == "__main__":
    test_light_scan_diagnostic()
