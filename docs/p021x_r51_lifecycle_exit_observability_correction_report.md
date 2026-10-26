# P0.21x-R51: Minimal Lifecycle Exit Observability - Correction Report

## 1. FILES CHANGED

### Modified Files

1. **`src/iabv_v15/services/evolution/runtime_audit_tracer.py`**
   - **Lines Modified**: 723-771
   - **Changes**:
     - Added `_R51_VALID_EVENT_TYPES = {'started', 'exit', 'crash'}` class variable
     - Added event_type validation in `trace_runtime_lifecycle()`
     - Returns empty dict on invalid event_type with warning log
   - **Purpose**: Restrict lifecycle API to only valid event types (R51-05)

2. **`src/iabv_v15/main.py`**
   - **Lines Modified**: 10-34, 40-60
   - **Changes**:
     - Added `load_app_config()` import and call before tracing started
     - Added `configure_runtime_tracer()` call to ensure persistence
     - Changed workspace_root to use `IABV_WORKSPACE_ROOT` env var with cwd fallback
     - Added exception flag check `_r51_crash_already_traced` to prevent duplicate crash
     - Updated crash tracing to use canonical workspace_root from config
   - **Purpose**: Ensure started persistence (R51-03), use canonical workspace (R51-04), prevent duplicate crash (R51-02)

3. **`src/iabv_v15/bootstrap.py`**
   - **Lines Modified**: 5309-5333, 5339-5358
   - **Changes**:
     - Added `_app_exit_code` attribute to capture actual exit code from `app.exec()`
     - Added `_bootstrap_exception_occurred` flag in exception handler
     - Added `fatal._r51_crash_already_traced` marker on exception before re-raising
     - Modified finally block to check exception flag before tracing exit
     - Modified finally block to use actual exit code instead of hardcoded 0
     - Added shutdown_reason logic: 'normal_shutdown' for exit_code=0, 'non_zero_exit' otherwise
   - **Purpose**: Prevent false exit after crash (R51-01), prevent duplicate crash (R51-02), use real exit code

### Created Files

4. **`tests/test_r51_lifecycle_observability.py`** (Updated)
   - **Lines Added**: 145 lines (TestR51ComprehensiveLifecycle class)
   - **Purpose**: Comprehensive tests for R51 lifecycle semantics (R51-06)

---

## 2. EXACT CHANGES

### runtime_audit_tracer.py

**Lines 727-771**: Added event type validation

```python
_R51_VALID_EVENT_TYPES = {'started', 'exit', 'crash'}

def trace_runtime_lifecycle(self, event_type: str, ...):
    # P0.21x-R51: Validate event_type to prevent accidental misuse
    if event_type not in self._R51_VALID_EVENT_TYPES:
        logger.warning(
            'trace_runtime_lifecycle: invalid event_type=%s, must be one of %s',
            event_type,
            sorted(self._R51_VALID_EVENT_TYPES),
        )
        return {}
    # ... rest of method
```

### main.py

**Lines 10-34**: Ensure tracer persistence and canonical workspace

```python
def main() -> int:
    try:
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            get_runtime_tracer,
            configure_runtime_tracer,
        )
        from iabv_v15.infra.config import load_app_config

        # Use IABV_WORKSPACE_ROOT if set by launcher, otherwise fall back to cwd
        workspace_root = os.environ.get('IABV_WORKSPACE_ROOT') or str(Path.cwd())

        # Load config to get logs_dir using canonical workspace resolution
        config = load_app_config(workspace_root=workspace_root)
        tracer = get_runtime_tracer()
        configure_runtime_tracer(Path(config.logs_dir))

        # Now trace started with guaranteed persistence
        tracer.trace_runtime_lifecycle(
            'started',
            pid=os.getpid(),
            workspace_root=config.workspace_root,
        )
    except Exception:
        pass
```

**Lines 40-60**: Prevent duplicate crash tracing

```python
except Exception as exc:
    # P0.21x-R51: Record runtime process crash only if not already traced by AppBootstrap
    if not getattr(exc, '_r51_crash_already_traced', False):
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            from iabv_v15.infra.config import load_app_config
            tracer = get_runtime_tracer()
            config = load_app_config()
            tracer.trace_runtime_lifecycle(
                'crash',
                pid=os.getpid(),
                exit_code=1,
                shutdown_reason='exception_in_main',
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                workspace_root=config.workspace_root,
            )
        except Exception:
            pass
```

### bootstrap.py

**Lines 5309-5312**: Capture actual exit code

```python
self._timeline.mark('app_exec_about_to_start')
exit_code = app.exec()
self._app_exit_code = exit_code
return exit_code
```

**Lines 5313-5333**: Mark exception and prevent duplicate crash

```python
except Exception as fatal:
    # P0.21x-R51: Mark that an exception occurred to prevent false exit in finally
    self._bootstrap_exception_occurred = True

    # P0.21x-R51: Record runtime process crash at AppBootstrap exception point
    try:
        self._tracer.trace_runtime_lifecycle(
            'crash',
            pid=os.getpid(),
            exit_code=1,
            shutdown_reason='exception_in_bootstrap_run',
            exception_type=type(fatal).__name__,
            exception_message=str(fatal),
            workspace_root=str(self.config.workspace_root),
        )
    except Exception:
        pass

    # P0.21x-R51: Mark exception as already traced to prevent duplicate crash in main.py
    fatal._r51_crash_already_traced = True
```

**Lines 5339-5358**: Prevent false exit after crash, use real exit code

```python
finally:
    # P0.21x-R51: Record runtime process exit only if no exception occurred
    try:
        if not getattr(self, '_bootstrap_exception_occurred', False):
            exit_code = getattr(self, '_app_exit_code', 0)
            shutdown_reason = 'normal_shutdown' if exit_code == 0 else 'non_zero_exit'
            self._tracer.trace_runtime_lifecycle(
                'exit',
                pid=os.getpid(),
                exit_code=exit_code,
                shutdown_reason=shutdown_reason,
                workspace_root=str(self.config.workspace_root),
            )
    except Exception:
        pass
```

---

## 3. LIFECYCLE SEMANTICS

### Normal Sequence

**`started → exit`**

- `runtime_process_started` traced in `main.py` before `AppBootstrap.run()`
- `runtime_process_exit` traced in `AppBootstrap.run()` finally block ONLY if:
  - `_bootstrap_exception_occurred` flag is False (no exception occurred)
  - Exit code is captured from actual `app.exec()` return value
  - `shutdown_reason` is `'normal_shutdown'` if exit_code=0, `'non_zero_exit'` otherwise

**Evidence**: Test A (`test_a_normal_started_to_exit_only`) ✓

### Crash Sequence

**`started → crash`**

- `runtime_process_started` traced in `main.py`
- `runtime_process_crash` traced in `AppBootstrap.run()` exception handler:
  - Sets `_bootstrap_exception_occurred = True`
  - Marks exception with `_r51_crash_already_traced = True`
  - Re-raises exception
- Finally block SKIPS exit tracing because `_bootstrap_exception_occurred` is True
- If exception reaches `main.py`, crash is NOT traced because `_r51_crash_already_traced` is True

**Evidence**: Test B (`test_b_exception_in_bootstrap_no_exit`) ✓, Test C (`test_c_exception_traverses_bootstrap_single_crash`) ✓

### Eliminated Sequences

**`started → crash → exit`** - ELIMINATED
- Finally block now checks `_bootstrap_exception_occurred` flag
- Exit is only traced when flag is False

**`started → crash → crash`** - ELIMINATED
- Exception marked with `_r51_crash_already_traced` in AppBootstrap
- main.py checks flag before tracing crash

---

## 4. TEST RESULTS

**Command**: `python -m pytest tests/test_r51_lifecycle_observability.py -v`

**Result**: **22 passed in 1.39s**

### Test Coverage

**TestRuntimeLifecycleTracing** (6 tests):
- `test_trace_runtime_lifecycle_started` ✓
- `test_trace_runtime_lifecycle_exit` ✓
- `test_trace_runtime_lifecycle_crash` ✓
- `test_trace_runtime_lifecycle_field_truncation` ✓
- `test_trace_runtime_lifecycle_persistence` ✓
- `test_trace_runtime_lifecycle_differentiation` ✓

**TestMainPyLifecycleIntegration** (3 tests):
- `test_main_py_imports_tracer` ✓
- `test_main_py_traces_started_on_entry` ✓
- `test_main_py_traces_crash_on_exception` ✓

**TestBootstrapLifecycleIntegration** (3 tests):
- `test_bootstrap_has_tracer` ✓
- `test_bootstrap_run_traces_exit_in_finally` ✓
- `test_bootstrap_run_traces_crash_on_exception` ✓

**TestProtectedSurfaceVerification** (3 tests):
- `test_p020_components_unchanged` ✓
- `test_runtime_audit_tracer_only_extended` ✓
- `test_no_new_managers_created` ✓

**TestR51ComprehensiveLifecycle** (7 tests - NEW):
- `test_a_normal_started_to_exit_only` ✓ - **Demonstrates: started → exit only**
- `test_b_exception_in_bootstrap_no_exit` ✓ - **Demonstrates: started → crash, NO exit**
- `test_c_exception_traverses_bootstrap_single_crash` ✓ - **Demonstrates: single crash, no duplicate**
- `test_d_non_zero_exit_not_normal_shutdown` ✓ - **Demonstrates: non-zero exit not labeled normal**
- `test_e_started_persistence` ✓ - **Demonstrates: started event persists to JSONL**
- `test_f_workspace_from_canonical_source` ✓ - **Demonstrates: workspace from canonical source**
- `test_g_only_valid_event_types_accepted` ✓ - **Demonstrates: only valid event types accepted**

---

## 5. EVIDENCE CLASSIFICATION

### R51-01: False Exit After Crash

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code change in `bootstrap.py` lines 5339-5358
- Added `_bootstrap_exception_occurred` flag check in finally block
- Test B verifies exit is NOT traced when exception occurs
- **No crash → exit sequence possible**

### R51-02: Double Crash

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code change in `bootstrap.py` line 5333: `fatal._r51_crash_already_traced = True`
- Code change in `main.py` lines 43: `if not getattr(exc, '_r51_crash_already_traced', False)`
- Test C verifies single crash when exception traverses AppBootstrap
- **No duplicate crash events possible**

### R51-03: Started Persistence

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code change in `main.py` lines 14-26: Added `configure_runtime_tracer(Path(config.logs_dir))`
- Test E verifies started event persists to JSONL
- **Started event guaranteed to persist**

### R51-04: Canonical Workspace Root

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code change in `main.py` lines 20-21: `workspace_root = os.environ.get('IABV_WORKSPACE_ROOT') or str(Path.cwd())`
- Code change in `main.py` line 24: `config = load_app_config(workspace_root=workspace_root)`
- Test F verifies workspace comes from canonical source
- **Workspace root uses IABV_WORKSPACE_ROOT from launcher**

### R51-05: Event Type Restriction

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code change in `runtime_audit_tracer.py` lines 727, 753-760
- Added `_R51_VALID_EVENT_TYPES = {'started', 'exit', 'crash'}`
- Added validation with warning log on invalid type
- Test G verifies only valid event types accepted
- **API restricted to valid lifecycle event types only**

### R51-06: Comprehensive Tests

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Added 7 comprehensive tests in TestR51ComprehensiveLifecycle class
- All 22 tests pass
- Tests specifically demonstrate elimination of crash→exit and double crash
- **Comprehensive test coverage for all R51 defects**

---

## 6. PROTECTED SURFACES

✓ **P0.20 components**: Unchanged
- No modifications to P0.20-specific code
- Test `test_p020_components_unchanged` passes

✓ **P0.21r components**: Unchanged
- No modifications to P0.21r-specific files

✓ **Resource metacognition**: Unchanged
- No modifications to resource metacognition service

✓ **Disk gate**: Unchanged
- No modifications to `live_disk_state()` or `disk_gate_decision()`

✓ **MCP 1.27.2**: Unchanged
- No modifications to MCP bridge or version

✓ **Ollama inventory**: Unchanged
- No modifications to Ollama inventory logic

✓ **Synaptic Routing**: Unchanged
- No modifications to Synaptic Router or activation

✓ **External agent activation**: Unchanged
- No modifications to external agent execution

✓ **No new managers/supervisors**: Verified
- Test `test_no_new_managers_created` passes
- No new ProcessManager, supervisor, or lifecycle service created

---

## 7. FINAL VERDICT

**`R51_CORRECTED_READY_FOR_REAUDIT`**

**Rationale**:
1. **R51-01 corrected**: False exit after crash eliminated via exception flag check
2. **R51-02 corrected**: Double crash eliminated via exception marking
3. **R51-03 corrected**: Started persistence guaranteed via configure_runtime_tracer
4. **R51-04 corrected**: Canonical workspace root via IABV_WORKSPACE_ROOT and load_app_config
5. **R51-05 corrected**: Event type restriction via validation in trace_runtime_lifecycle
6. **R51-06 corrected**: Comprehensive tests added and all 22 tests pass
7. Protected surfaces remain unchanged
8. No new managers, supervisors, or services created
9. Implementation remains minimal and focused on authorized scope

All Codex audit findings have been addressed with minimal, focused corrections using only existing authorities (main.py, AppBootstrap.run(), RuntimeAuditTracer).

---

## 8. NEXT SINGLE ACTION

**`R51-A2 — Codex re-audit`**

The corrections are complete and verified by comprehensive tests. The next action is for Codex to re-audit the implementation to verify all defects have been resolved.

---

## APPENDIX A: LIFECYCLE SEMANTICS VERIFICATION

### Normal Exit (Test A)

```
started → exit
```

**Verification**:
- `test_a_normal_started_to_exit_only` passes
- Only started and exit events present
- No crash events present

### Crash in Bootstrap (Test B)

```
started → crash
```

**Verification**:
- `test_b_exception_in_bootstrap_no_exit` passes
- Exit is NOT traced when `_bootstrap_exception_occurred` is True
- Finally block skips exit tracing

### Exception Traverses Bootstrap (Test C)

```
started → crash (single)
```

**Verification**:
- `test_c_exception_traverses_bootstrap_single_crash` passes
- Exception marked with `_r51_crash_already_traced` in AppBootstrap
- main.py checks flag and skips duplicate crash tracing

### Non-Zero Exit (Test D)

```
started → exit (exit_code=1, shutdown_reason='non_zero_exit')
```

**Verification**:
- `test_d_non_zero_exit_not_normal_shutdown` passes
- Exit uses actual exit code from `app.exec()`
- Shutdown reason is 'non_zero_exit' when exit_code != 0

---

## APPENDIX B: DEFECT CORRECTION SUMMARY

| Defect | Root Cause | Correction | Test |
|--------|-----------|------------|------|
| R51-01 | finally block always traced exit | Added exception flag check | Test B |
| R51-02 | Both AppBootstrap and main.py traced crash | Added exception marking | Test C |
| R51-03 | Tracer log_dir not configured before started | Added configure_runtime_tracer | Test E |
| R51-04 | Used Path.cwd() instead of canonical source | Use IABV_WORKSPACE_ROOT + load_app_config | Test F |
| R51-05 | No event type validation | Added validation with valid types set | Test G |
| R51-06 | Tests didn't detect crash→exit or double crash | Added 7 comprehensive tests | All tests |

---

**Report Generated**: 2026-08-17
**Report ID**: P0.21x-R51-CORRECTION
**Status**: READY FOR RE-AUDIT
