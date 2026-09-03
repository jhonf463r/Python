# IABV v1.5 Resource Governance Boundary Audit
**Date:** 2026-09-02
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## Audit Scope

Inspect AdaptiveResourceOrchestrator and every production caller of:
- `should_run_task()`
- `take_resource_snapshot()`

## Synchronous Resource Probing Risk

### PowerShell/WMIC Subprocess Calls

**Location:** `intelligent_resource_manager.py` - `take_resource_snapshot()`
**Risk:** HIGH - PowerShell subprocess calls are blocking
**Evidence:** OBSERVED (from code comments in bootstrap.py line 4037)

**Code Comment Evidence (bootstrap.py line 4037):**
```python
# IMPORTANT: ARO.should_run_task() calls take_resource_snapshot() which
# can invoke blocking PowerShell subprocesses. To avoid blocking critical
# startup, only consult ARO after the system is stable (ready transition).
```

### Production Callers Analysis

#### 1. Bootstrap.py - Patch A Deferred Metacognition

**Caller:** `_bg_metacognition` (lines 1933-1963)
**Thread:** Background thread (`iabv-deferred-metacognition`)
**Path:** Deferred metacognition (non-critical startup)
**Risk:** LOW - Already in background thread, not UI thread
**Evidence:** OBSERVED

**Caller:** `_deferred_auto_install_missing_tools` (lines 2039-2064)
**Thread:** Background thread (called from `_bg_metacognition`)
**Path:** Deferred auto-install (non-critical startup)
**Risk:** LOW - Already in background thread, not UI thread
**Evidence:** OBSERVED

#### 2. Bootstrap.py - ARO Prebuild Admission

**Caller:** `_should_pause_prebuild` (lines 3963-4202)
**Thread:** Unknown (likely main thread during prebuild)
**Path:** VM prebuild (potentially critical path)
**Risk:** MEDIUM - May block critical prebuild path
**Evidence:** OBSERVED

**Code Comment Evidence (bootstrap.py line 4158):**
```python
# ``take_resource_snapshot()`` is NEVER called from the UI thread
```

This comment claims UI thread safety, but the actual threading context of `_should_pause_prebuild` needs verification.

#### 3. AdaptiveTaskOrchestrator

**Caller:** Unknown (not audited in detail)
**Thread:** Unknown
**Path:** Chat inference path
**Risk:** HIGH - If called from chat path, could block user interaction
**Evidence:** UNKNOWN

#### 4. ResourceMetacognitionService

**Caller:** Unknown (not audited in detail)
**Thread:** Unknown
**Path:** Resource observation
**Risk:** MEDIUM - May be called from various contexts
**Evidence:** UNKNOWN

## UI Thread Risk Assessment

**UI Thread:** MainWindowBridge / QML event loop
**Risk:** LOW - Code comments claim `take_resource_snapshot()` is never called from UI thread
**Evidence:** CLAIMED (not verified)

## Startup Critical Path Risk

**Critical Path:** Tool probes, UI initialization
**Risk:** LOW - ARO is explicitly delayed until after ready transition
**Evidence:** OBSERVED (from code comments)

**Code Comment Evidence (bootstrap.py line 4037):**
```python
# To avoid blocking critical startup, only consult ARO after the system is stable (ready transition).
```

## Post-Ready Critical Path Risk

**Post-Ready Path:** Chat inference, tool execution
**Risk:** HIGH - If ARO is called from chat path without proper threading
**Evidence:** UNKNOWN (needs verification)

## Summary

**SYNCHRONOUS PROBING RISK:** HIGH
**UI THREAD RISK:** LOW (claimed, not verified)
**STARTUP CRITICAL PATH RISK:** LOW (ARO delayed until ready)
**POST-READY CRITICAL PATH RISK:** HIGH (unknown threading context)

**CRITICAL FINDING:** `take_resource_snapshot()` invokes blocking PowerShell subprocesses. While ARO is delayed until after ready transition, the chat inference path may still call it synchronously, potentially blocking user interaction.

**RECOMMENDATION:** Audit AdaptiveTaskOrchestrator and all chat path callers to verify they do not call `take_resource_snapshot()` synchronously from the UI thread or critical chat path.
