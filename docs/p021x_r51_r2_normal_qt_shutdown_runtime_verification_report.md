# P0.21x-R51-R2: Normal Qt Shutdown Runtime Verification Report

## A. RUNTIME IDENTITY

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

- **PID**: 5936
- **Workspace**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
- **HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22
- **Launcher**: launch_deterministic_runtime_p021v.ps1
- **Python Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe
- **Python Version**: (not captured in this experiment)
- **MCP Version**: (not captured in this experiment)
- **Runtime Audit Path**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\logs\runtime_audit.jsonl

---

## B. START EVENT

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

```json
{
  "ts": "2026-08-17T22:45:44.016+00:00",
  "elapsed_ms": 0.3,
  "kind": "runtime_process_started",
  "data": {
    "pid": 5936,
    "exit_code": null,
    "shutdown_reason": "",
    "exception_type": "",
    "exception_message": "",
    "workspace_root": "C:\\Python\\IABV_v1.5_runtime_p021v\\IABV_v1.5\\IABV_v1.5"
  },
  "seq": 1
}
```

**Verification**: ✓ PASS
- PID: 5936
- Workspace: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
- Timestamp: 2026-08-17T22:45:44.016+00:00
- Persisted in JSONL: YES

---

## C. SHUTDOWN

**Classification**: `EXTERNAL_PROCESS_EVIDENCE`

**Method**: User closed IABV window normally using the window's close button (X)

**Process State After Shutdown**:
- PID 5936: TERMINATED (confirmed via `Get-Process -Id 5936` - process not found)

---

## D. EXIT EVENT

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

**Result**: ✗ NOT FOUND

No `runtime_process_exit` event exists for PID 5936 in `runtime_audit.jsonl`.

**Search Results**:
- `runtime_process_exit` for PID 5936: 0 events
- `runtime_process_crash` for PID 5936: 0 events

---

## E. TERMINAL COUNTS

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

For PID 5936:
- **started**: 1
- **exit**: 0
- **crash**: 0
- **total terminal**: 0

---

## F. INVARIANTS

**Classification**: `DERIVED_EVIDENCE`

- **Invariant A** (`count(started) == 1`): ✓ PASS
- **Invariant B** (`count(terminal events) == 1`): ✗ FAIL (0 terminal events)
- **Invariant C** (`terminal event == runtime_process_exit`): ✗ FAIL (no terminal event)
- **Invariant D** (`count(crash) == 0`): ✓ PASS
- **Invariant E** (`started PID == exit PID`): ✗ FAIL (no exit event)
- **Invariant F** (`exit timestamp >= start timestamp`): ✗ FAIL (no exit event)
- **Invariant G** (`exit` event persisted after termination): ✗ FAIL (no exit event)

---

## G. PERSISTENCE

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

**Result**: ✗ FAIL

- `runtime_process_started` for PID 5936: PERSISTED ✓
- `runtime_process_exit` for PID 5936: NOT PERSISTED ✗

The start event survived the shutdown, but no exit event was ever written to the JSONL file.

---

## H. PROCESS CROSS-CHECK

**Classification**: `EXTERNAL_PROCESS_EVIDENCE`

**Result**: ✓ PASS

- PID 5936: TERMINATED (confirmed via `Get-Process -Id 5936`)
- No unexpected IABV processes found after shutdown

---

## I. ENVIRONMENT REPRODUCIBILITY

**Classification**: `HISTORICAL_EVIDENCE`

**Environment Discrepancy**:
- Launcher uses: `C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe`
- Previous report showed: `C:\Users\faber\miniconda3\python.exe`

This discrepancy was noted in A13 but not addressed. It remains as `ENVIRONMENT_REPRODUCIBILITY_DEBT` but does not affect the lifecycle verification failure.

---

## J. KNOWN DEBT

**Classification**: `HISTORICAL_EVIDENCE`

- **traceback_ref**: Not addressed in R51-R2 (separate concern)
- **fsync vs flush**: Not addressed in R51-R2 (separate concern)
- **MCP version discrepancy**: Not addressed in R51-R2 (separate concern)

These debts are not converted into lifecycle failures because they do not affect the normal shutdown experiment.

---

## K. CRITICAL FALSE-GREEN CHECK

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

### A. `started → exit`
✗ FAIL - exit event missing

### B. `started → exit → exit`
✗ FAIL - no exit events at all

### C. `started → crash`
✗ FAIL - crash event missing

### D. `started → exit → crash`
✗ FAIL - no terminal events

### E. `started` belonging to another PID/episode
✗ PASS - only one `runtime_process_started` for PID 5936

### F. `exit` belonging to another PID/episode
✗ PASS - no exit events found

### G. exit persisted only in memory and not in disk
✗ FAIL - no exit event exists anywhere

### H. exit generated before the shutdown real
✗ FAIL - no exit event exists anywhere

---

## L. ABOUTTOQUIT CORRELATION

**Classification**: `UNVERIFIED_ASSUMPTION`

The `aboutToQuit` signal behavior could not be directly observed in this experiment. However, based on the A13 fix design:

- `aboutToQuit` should have marked `_qt_about_to_quit_fired = True`
- `aboutToQuit` should NOT have emitted a terminal event
- The finally block should have emitted the terminal event

**Analysis**: The absence of any terminal event suggests that either:
1. The finally block did not execute
2. The finally block executed but the event was not persisted
3. The tracer failed to write the event

This indicates that the A13 fix (removing the backup emission from `aboutToQuit`) exposed the original problem: the finally block is not reliably emitting/persisting the exit event during normal Qt shutdown.

---

## M. ROOT CAUSE ANALYSIS

**Classification**: `DERIVED_EVIDENCE`

**Problem**: A13 removed the backup exit event emission from `aboutToQuit`, relying solely on the finally block. However, the runtime verification shows that the finally block is not reliably emitting/persisting the exit event during normal Qt shutdown.

**Original A11 Problem**: Dual exit events (aboutToQuit + finally)
**A13 Fix**: Removed aboutToQuit emission, kept only finally block
**A13 Result**: No exit event at all (finally block not working)

**Conclusion**: The original problem was NOT dual emission. The original problem was that the finally block is not reliably executing or persisting the exit event during normal Qt shutdown. The A11 "backup" via aboutToQuit was actually masking the real issue.

---

## N. FINAL VERDICT

**`R51_RUNTIME_NORMAL_LIFECYCLE_FAILED`**

### Rationale

The runtime verification demonstrates that the A13 fix did NOT resolve the Qt normal shutdown exit tracing defect:

1. **No Exit Event**: `runtime_process_exit` is completely missing for PID 5936
2. **Invariant Violation**: `count(terminal events) == 0` (expected 1)
3. **Persistence Failure**: Exit event was never written to `runtime_audit.jsonl`
4. **A13 Regression**: By removing the aboutToQuit backup emission, A13 exposed the real problem - the finally block is not reliably emitting/persisting the exit event

The evidence is clear: normal Qt window close → process termination → NO exit event persisted.

---

## O. NEXT SINGLE ACTION

**`R51-A15 — Restore aboutToQuit backup emission with deduplication`**

The next action must restore the aboutToQuit handler to emit the exit event as a backup mechanism, while implementing proper deduplication to prevent dual events. This acknowledges that the finally block cannot be relied upon for normal Qt shutdown.

The fix should:
1. Restore `aboutToQuit` to emit `runtime_process_exit` with the actual exit code
2. Keep the finally block emission
3. Implement episode-scoped deduplication to ensure exactly one terminal event
4. Ensure crash safety (no exit during crash)

DO NOT EXECUTE THIS ACTION NOW - This report must be reviewed and approved before proceeding to A15.
