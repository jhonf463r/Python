# P0.21x-R51-A3: Close BaseException Terminal-State Gap - Correction Report

## 1. FILES MODIFIED

### Modified Files

1. **`src/iabv_v15/bootstrap.py`**
   - **Lines Modified**: 5313
   - **Change**: Changed `except Exception as fatal:` to `except BaseException as fatal:`
   - **Purpose**: Catch KeyboardInterrupt, SystemExit, and other BaseException subclasses to prevent false exit

2. **`src/iabv_v15/main.py`**
   - **Lines Modified**: 43
   - **Change**: Changed `except Exception as exc:` to `except BaseException as exc:`
   - **Purpose**: Catch KeyboardInterrupt, SystemExit, and other BaseException subclasses at top level

3. **`tests/test_r51_lifecycle_observability.py`**
   - **Lines Modified**: 253, 465-614
   - **Changes**:
     - Updated test to check for `BaseException` instead of `Exception`
     - Added Test H for KeyboardInterrupt
     - Added Test I for SystemExit
     - Added Test J for BaseException
     - Added Test K for regular Exception
     - Added Test L for normal exit
     - Added Test M for no crash+exit coexistence
   - **Purpose**: Comprehensive tests for BaseException handling

---

## 2. EXACT METHODS

### bootstrap.py

**Line 5313**: Changed exception handler

```python
# Before:
except Exception as fatal:

# After:
except BaseException as fatal:
    # P0.21x-R51-A3: Catch BaseException to handle KeyboardInterrupt, SystemExit, etc.
```

### main.py

**Line 43**: Changed exception handler

```python
# Before:
except Exception as exc:

# After:
except BaseException as exc:
    # P0.21x-R51-A3: Catch BaseException to handle KeyboardInterrupt, SystemExit, etc.
```

### test_r51_lifecycle_observability.py

**Line 253**: Updated structural test

```python
# Before:
assert 'except Exception as fatal:' in source

# After:
assert 'except BaseException as fatal:' in source
```

**Lines 465-614**: Added 6 new tests (H, I, J, K, L, M)

---

## 3. BASEEXCEPTION SEMANTICS

### Python Exception Hierarchy

```
BaseException
 ├── SystemExit
 ├── KeyboardInterrupt
 ├── GeneratorExit
 ├── Exception
 │    ├── RuntimeError
 │    ├── ValueError
 │    └── ... (all regular exceptions)
 └── ... (other BaseException subclasses)
```

### Semantics

**Exception**: Represents regular application errors that should be caught and handled.

**BaseException**: Represents all exceptions including:
- `KeyboardInterrupt`: User pressed Ctrl+C
- `SystemExit`: `sys.exit()` was called
- `GeneratorExit`: Generator cleanup
- Other system-level exceptions

### Solution

Changed both `bootstrap.py` and `main.py` to catch `BaseException` instead of `Exception`. This ensures that:

1. `KeyboardInterrupt` is caught → sets `_bootstrap_exception_occurred = True` → finally skips exit
2. `SystemExit` is caught → sets `_bootstrap_exception_occurred = True` → finally skips exit
3. Any other `BaseException` is caught → sets `_bootstrap_exception_occurred = True` → finally skips exit

The existing exception flag mechanism (`_bootstrap_exception_occurred`) already prevents false exit. The only change needed was to broaden the catch to include `BaseException` subclasses.

---

## 4. NORMAL EXIT SEMANTICS

### When is `runtime_process_exit` emitted?

`runtime_process_exit` is emitted ONLY when:

1. `AppBootstrap.run()` completes normally (no exception)
2. `_bootstrap_exception_occurred` flag is False
3. The finally block executes and checks the flag

### Evidence

**Code**: `bootstrap.py` lines 5339-5358

```python
finally:
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

### No Hardcoded exit_code=0

The exit code is captured from the actual `app.exec()` return value:

**Code**: `bootstrap.py` lines 5310-5312

```python
exit_code = app.exec()
self._app_exit_code = exit_code
return exit_code
```

---

## 5. CRASH SEMANTICS

### When is `runtime_process_crash` emitted?

`runtime_process_crash` is emitted when:

1. Any `BaseException` (including `Exception`, `KeyboardInterrupt`, `SystemExit`) occurs in `AppBootstrap.run()`
2. The exception handler sets `_bootstrap_exception_occurred = True`
3. The exception handler traces crash with exception details
4. The exception handler marks the exception with `_r51_crash_already_traced = True`
5. The exception is re-raised

### Non-Normal Termination Classification

All `BaseException` subclasses are classified as crash:

- `KeyboardInterrupt` → `runtime_process_crash` with `exception_type='KeyboardInterrupt'`
- `SystemExit` → `runtime_process_crash` with `exception_type='SystemExit'`
- `Exception` → `runtime_process_crash` with `exception_type='RuntimeError'` (or specific type)
- Custom `BaseException` → `runtime_process_crash` with `exception_type='CustomBaseException'`

**No "external termination" category invented** - all non-normal terminations are honestly classified as crash with their actual exception type.

---

## 6. DUPLICATE PROTECTION

### Existing Mechanism (Preserved)

The duplicate crash protection from R51-A2 is preserved:

1. **AppBootstrap marks exception**: `fatal._r51_crash_already_traced = True`
2. **main.py checks flag**: `if not getattr(exc, '_r51_crash_already_traced', False)`

### Verification

**Test K**: Regular Exception → single crash, no duplicate ✓
**Test M**: Never both crash and exit in same flow ✓

The BaseException change does not reintroduce duplicate crashes because:
- The exception marking mechanism works for any exception type
- The flag check in main.py works for any exception type
- The exception flag in finally works for any exception type

---

## 7. TESTS

**Command**: `python -m pytest tests/test_r51_lifecycle_observability.py -v`

**Result**: **28 passed in 1.68s**

### New Tests (H, I, J, K, L, M)

**Test H**: `test_h_keyboard_interrupt_no_false_exit` ✓
- Simulates KeyboardInterrupt in AppBootstrap
- Verifies exit is NOT traced when exception flag is set
- **Evidence**: KeyboardInterrupt does not produce false exit

**Test I**: `test_i_system_exit_no_false_exit` ✓
- Simulates SystemExit in AppBootstrap
- Verifies exit is NOT traced when exception flag is set
- **Evidence**: SystemExit does not produce false exit

**Test J**: `test_j_baseexception_no_false_exit` ✓
- Simulates custom BaseException in AppBootstrap
- Verifies exit is NOT traced when exception flag is set
- **Evidence**: BaseException does not produce false exit

**Test K**: `test_k_regular_exception_single_crash` ✓
- Verifies regular Exception still produces single crash
- Verifies exception marking prevents duplicate
- **Evidence**: Regular Exception behavior preserved

**Test L**: `test_l_normal_exit_single_exit` ✓
- Verifies normal exit produces single exit
- Verifies no crash events in normal flow
- **Evidence**: Normal exit behavior preserved

**Test M**: `test_m_no_crash_exit_coexistence` ✓
- Verifies crash flow does not have exit
- Verifies normal flow does not have crash
- **Evidence**: Crash and exit never coexist

### All Tests Summary

- 6 original RuntimeLifecycleTracing tests ✓
- 3 original MainPyLifecycleIntegration tests ✓
- 3 original BootstrapLifecycleIntegration tests ✓
- 3 original ProtectedSurfaceVerification tests ✓
- 7 original R51ComprehensiveLifecycle tests ✓
- 6 new R51-A3 tests (H, I, J, K, L, M) ✓

**Total**: 28 tests passed

---

## 8. PROTECTED SURFACES

✓ **P0.20 components**: Unchanged
- No modifications to P0.20-specific code

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
- No new ProcessManager, supervisor, or lifecycle service created
- Only changed exception catch type from Exception to BaseException

---

## 9. SCOPE COMPLIANCE

### Changes Limited To

✓ `main.py` - Changed exception catch from Exception to BaseException
✓ `bootstrap.py` - Changed exception catch from Exception to BaseException
✓ `test_r51_lifecycle_observability.py` - Added 6 new tests, updated 1 existing test

### No Changes To

✓ `runtime_audit_tracer.py` - No changes needed (already supports all exception types)
✓ P0.20 - No modifications
✓ P0.21r - No modifications
✓ Resource metacognition - No modifications
✓ Disk gate - No modifications
✓ Ollama inventory - No modifications
✓ MCP 1.27.2 - No modifications
✓ Synaptic Routing - No modifications
✓ External agents - No modifications

### No New Components

✓ No LifecycleManager created
✓ No ProcessManager created
✓ No watchdog created
✓ No supervisor created
✓ No new logger created
✓ No new database created
✓ No new memory created

---

## 10. EVIDENCE CLASSIFICATION

### BaseException Gap Fix

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code change in `bootstrap.py` line 5313: `except BaseException as fatal:`
- Code change in `main.py` line 43: `except BaseException as exc:`
- Test H verifies KeyboardInterrupt does not produce false exit
- Test I verifies SystemExit does not produce false exit
- Test J verifies BaseException does not produce false exit
- **KeyboardInterrupt and SystemExit now caught and prevent false exit**

### Normal Exit Semantics

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code in `bootstrap.py` lines 5339-5358 checks `_bootstrap_exception_occurred` flag
- Exit only traced when flag is False
- Exit code captured from actual `app.exec()` return value
- Test L verifies normal exit produces single exit
- **Exit only emitted when no exception occurred**

### Crash Semantics

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Code in `bootstrap.py` lines 5313-5333 catches all BaseException
- All BaseException subclasses classified as crash with actual type
- No "external termination" category invented
- Test K verifies regular Exception produces single crash
- **All non-normal terminations honestly classified as crash**

### Duplicate Protection

**Classification**: `ENGINEERING_DESIGN`

**Evidence**:
- Exception marking mechanism preserved from R51-A2
- Test K verifies single crash for regular Exception
- Test M verifies crash and exit never coexist
- **Duplicate crash protection preserved**

### Test Coverage

**Classification**: `TEST_EVIDENCE`

**Evidence**:
- 28 tests pass
- 6 new tests specifically for BaseException handling
- Tests demonstrate elimination of false exit for KeyboardInterrupt, SystemExit, BaseException
- Tests verify no crash+exit coexistence
- **Comprehensive test coverage for BaseException gap**

---

## 11. FINAL VERDICT

**`R51_A3_READY_FOR_REAUDIT`**

**Rationale**:
1. **BaseException gap closed**: Changed catch from Exception to BaseException in both bootstrap.py and main.py
2. **False exit eliminated**: KeyboardInterrupt, SystemExit, and other BaseException subclasses now set exception flag, preventing false exit
3. **Normal exit preserved**: Exit only emitted when no exception occurred, using actual exit code
4. **Crash semantics honest**: All non-normal terminations classified as crash with actual exception type
5. **Duplicate protection preserved**: Exception marking mechanism works for all exception types
6. **Comprehensive tests**: 6 new tests (H, I, J, K, L, M) verify BaseException handling
7. **Protected surfaces unchanged**: No modifications to protected components
8. **Scope compliance**: Changes limited to main.py, bootstrap.py, and tests
9. **No new components**: No managers, supervisors, or services created
10. **Minimal change**: Only changed exception catch type, leveraging existing flag mechanism

The BaseException terminal-state gap is closed with a minimal, focused change that leverages the existing exception flag mechanism from R51-A2. All 28 tests pass, demonstrating that KeyboardInterrupt, SystemExit, and other BaseException subclasses no longer produce false exit events.

---

## 12. NEXT SINGLE ACTION

**`R51-A4 — Codex re-audit`**

The BaseException gap correction is complete and verified by comprehensive tests. The next action is for Codex to re-audit the implementation to verify the terminal-state gap has been closed.

---

## APPENDIX A: LIFECYCLE SEMANTICS FINAL

### Normal Exit

```
started → exit
```

**Conditions**:
- No exception occurs in AppBootstrap.run()
- `_bootstrap_exception_occurred` flag is False
- Finally block traces exit with actual exit code

**Evidence**: Test L ✓

### Crash (Any BaseException)

```
started → crash
```

**Conditions**:
- Any BaseException occurs (Exception, KeyboardInterrupt, SystemExit, etc.)
- Exception handler sets `_bootstrap_exception_occurred = True`
- Exception handler traces crash
- Exception handler marks exception with `_r51_crash_already_traced`
- Finally block skips exit due to exception flag

**Evidence**: Test H (KeyboardInterrupt) ✓, Test I (SystemExit) ✓, Test J (BaseException) ✓, Test K (Exception) ✓

### Eliminated Sequences

```
started → crash → exit (ELIMINATED)
```
- Exception flag prevents exit in finally

```
started → crash → crash (ELIMINATED)
```
- Exception marking prevents duplicate crash in main.py

```
started → KeyboardInterrupt → exit (ELIMINATED)
```
- BaseException catch sets flag, prevents exit

```
started → SystemExit → exit (ELIMINATED)
```
- BaseException catch sets flag, prevents exit

---

## APPENDIX B: DEFECT CORRECTION SUMMARY

| Defect | Root Cause | Correction | Test |
|--------|-----------|------------|------|
| R51-A2: BaseException gap | Only Exception caught, not BaseException | Changed catch to BaseException | Test H, I, J |

---

**Report Generated**: 2026-08-17
**Report ID**: P0.21x-R51-A3-CORRECTION
**Status**: READY FOR RE-AUDIT
