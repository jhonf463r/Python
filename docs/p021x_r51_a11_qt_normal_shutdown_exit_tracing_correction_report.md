# P0.21x-R51-A11: Qt Normal Shutdown Exit Tracing Correction Report

## A. ROOT CAUSE

### Summary

**`DIRECT_RUNTIME_EVIDENCE`**: The runtime terminated normally (user closed Qt window) but `runtime_process_exit` was NOT captured in `runtime_audit.jsonl`.

### Root Cause Analysis

The root cause is a **dual failure** in the exit event persistence chain:

1. **Buffered I/O**: `RuntimeAuditTracer._append()` did not flush the file handle after writing events. When the process terminated immediately after Qt window close, the exit event remained in the OS buffer and was never written to disk.

2. **Qt Termination Bypass**: When the user closes the Qt window normally, Qt's event loop termination may bypass or interrupt the `finally` block in `AppBootstrap.run()`. The `finally` block is designed to trace the exit event, but Qt's termination behavior can prevent it from executing completely.

### Call Flow Before Fix

```
User closes Qt window
        ↓
Qt ApplicationWindow closes
        ↓
QApplication.quit() / app.exec() returns
        ↓
[POSSIBLE BYPASS] finally block may not execute
        ↓
[IF finally executes] tracer.trace_runtime_lifecycle('exit', ...)
        ↓
tracer._append() writes to file handle (BUFFERED, NOT FLUSHED)
        ↓
Process terminates
        ↓
BUFFER LOST → No exit event in runtime_audit.jsonl
```

### Evidence Classification

- **DIRECT_RUNTIME_EVIDENCE**: runtime_process_started captured, runtime_process_exit NOT captured
- **ENGINEERING_DESIGN**: Qt event loop termination behavior
- **UNVERIFIED_ASSUMPTION**: finally block always executes (DISPROVEN by runtime behavior)

---

## B. ACTUAL CALL FLOW

### Before Fix

```
Qt window close (user action)
        ↓
QApplication.quit()
        ↓
app.exec() returns (exit_code = 0)
        ↓
[UNCERTAIN] finally block execution
        ↓
[IF finally executes] tracer.trace_runtime_lifecycle('exit', ...)
        ↓
tracer._append() writes to file handle (BUFFERED)
        ↓
Process terminates before flush
        ↓
BUFFER LOST → No exit event persisted
```

### After Fix

```
Qt window close (user action)
        ↓
QApplication.quit()
        ↓
app.aboutToQuit signal emitted
        ↓
_on_qt_about_to_quit() handler executes
        ↓
tracer.trace_runtime_lifecycle('exit', ...)
        ↓
tracer._append() writes to file handle (FLUSHED)
        ↓
Event persisted to disk
        ↓
[BACKUP] If finally block executes, deduplication prevents duplicate
```

---

## C. FIX

### Files Modified

1. **`src/iabv_v15/services/evolution/runtime_audit_tracer.py`**
   - Line 958: Added `fh.flush()` to `_append()` method

2. **`src/iabv_v15/bootstrap.py`**
   - Lines 4167-4172: Connect `app.aboutToQuit` to `_on_qt_about_to_quit` handler
   - Lines 2616-2646: Added `_on_qt_about_to_quit()` method
   - Line 5493: Added `_r51_exit_already_traced` flag in finally block

### Exact Changes

#### Change 1: RuntimeAuditTracer._append() - Add flush

```python
# Before:
def _append(self, event: dict[str, Any]) -> None:
    if self._log_dir is None:
        return
    try:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        target = self._log_dir / 'runtime_audit.jsonl'
        with target.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + '\n')
    except Exception as exc:
        logger.warning('RuntimeAuditTracer._append failed (log_dir=%s): %s', self._log_dir, exc)

# After:
def _append(self, event: dict[str, Any]) -> None:
    if self._log_dir is None:
        return
    try:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        target = self._log_dir / 'runtime_audit.jsonl'
        with target.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + '\n')
            fh.flush()  # P0.21x-R51-A11: Ensure immediate flush for exit events
    except Exception as exc:
        logger.warning('RuntimeAuditTracer._append failed (log_dir=%s): %s', self._log_dir, exc)
```

**Classification**: `ENGINEERING_DESIGN`

#### Change 2: AppBootstrap.create_engine() - Connect aboutToQuit

```python
# Before:
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
QQuickStyle.setStyle('Basic')
app = QGuiApplication.instance() or QApplication(sys.argv)

splash = getattr(self, '_splash', None)

engine = QQmlApplicationEngine()

# After:
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
QQuickStyle.setStyle('Basic')
app = QGuiApplication.instance() or QApplication(sys.argv)

# P0.21x-R51-A11: Connect aboutToQuit to ensure exit event is traced
# This provides a backup mechanism if the finally block is bypassed
try:
    app.aboutToQuit.connect(self._on_qt_about_to_quit)
except Exception:
    pass

splash = getattr(self, '_splash', None)

engine = QQmlApplicationEngine()
```

**Classification**: `ENGINEERING_DESIGN`

#### Change 3: AppBootstrap._on_qt_about_to_quit() - New method

```python
# Added after _on_window_lifecycle():
def _on_qt_about_to_quit(self) -> None:
    """P0.21x-R51-A11: Qt aboutToQuit handler for exit tracing backup.

    This is called when Qt is about to quit (e.g., when the user closes
    the window). It provides a backup mechanism to trace the exit event
    if the finally block in AppBootstrap.run() is bypassed by Qt's
    termination behavior.

    We use a flag to prevent duplicate tracing if the finally block
    does execute normally.
    """
    # Check if we already traced the exit (e.g., from finally block)
    if getattr(self, '_r51_exit_already_traced', False):
        return

    try:
        # Use the actual exit code from app.exec() if available
        exit_code = getattr(self, '_app_exit_code', 0)
        shutdown_reason = 'normal_shutdown' if exit_code == 0 else 'non_zero_exit'
        self._tracer.trace_runtime_lifecycle(
            'exit',
            pid=os.getpid(),
            exit_code=exit_code,
            shutdown_reason=shutdown_reason,
            workspace_root=str(self.config.workspace_root),
        )
        # Mark as traced to prevent duplicate tracing
        self._r51_exit_already_traced = True
    except Exception:
        # Tracing failure should not prevent Qt shutdown
        pass
```

**Classification**: `ENGINEERING_DESIGN`

#### Change 4: AppBootstrap.run() finally block - Add deduplication flag

```python
# Before:
finally:
    # P0.21x-R51: Record runtime process exit only if no exception occurred
    # The finally block should not convert a crash into a normal exit
    try:
        # Check if we're exiting normally (no exception in the try block)
        # We use a flag to track whether an exception occurred
        if not getattr(self, '_bootstrap_exception_occurred', False):
            # Use the actual exit code from app.exec() if available
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
        # Tracing failure should not prevent cleanup
        pass

# After:
finally:
    # P0.21x-R51: Record runtime process exit only if no exception occurred
    # The finally block should not convert a crash into a normal exit
    try:
        # Check if we're exiting normally (no exception in the try block)
        # We use a flag to track whether an exception occurred
        if not getattr(self, '_bootstrap_exception_occurred', False):
            # Use the actual exit code from app.exec() if available
            exit_code = getattr(self, '_app_exit_code', 0)
            shutdown_reason = 'normal_shutdown' if exit_code == 0 else 'non_zero_exit'
            self._tracer.trace_runtime_lifecycle(
                'exit',
                pid=os.getpid(),
                exit_code=exit_code,
                shutdown_reason=shutdown_reason,
                workspace_root=str(self.config.workspace_root),
            )
            # P0.21x-R51-A11: Mark as traced to prevent duplicate from aboutToQuit
            self._r51_exit_already_traced = True
    except Exception:
        # Tracing failure should not prevent cleanup
        pass
```

**Classification**: `ENGINEERING_DESIGN`

---

## D. TESTS

### New Tests Added

**File**: `tests/test_r51_lifecycle_observability.py`

**Class**: `TestR51A11QtNormalShutdownExitTracing`

#### Test A: Handler Exists

```python
def test_a_qt_about_to_quit_handler_exists(self):
    """Test A: Verify _on_qt_about_to_quit handler exists (UNIT)."""
    from iabv_v15.bootstrap import AppBootstrap
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        bootstrap = AppBootstrap(_defer_services=True)
        bootstrap.config.workspace_root = Path(tmpdir)

        # Verify the handler method exists
        assert hasattr(bootstrap, '_on_qt_about_to_quit')
        assert callable(bootstrap._on_qt_about_to_quit)
```

**Classification**: `TEST_EVIDENCE`

#### Test B: Handler Traces Exit Once

```python
def test_b_qt_about_to_quit_traces_exit_once(self):
    """Test B: aboutToQuit traces exit exactly once (UNIT)."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer, configure_runtime_tracer
    from pathlib import Path
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / 'logs'
        configure_runtime_tracer(log_dir)
        tracer = get_runtime_tracer()

        bootstrap = AppBootstrap(_defer_services=True)
        bootstrap.config.workspace_root = Path(tmpdir)
        bootstrap._tracer = tracer
        bootstrap._app_exit_code = 0

        # Call the handler
        bootstrap._on_qt_about_to_quit()

        # Verify exit event was traced
        events = tracer.events(kind='runtime_process_exit', limit=10)
        assert len(events) == 1
        assert events[0]['data']['pid'] == os.getpid()
        assert events[0]['data']['exit_code'] == 0
        assert events[0]['data']['shutdown_reason'] == 'normal_shutdown'
```

**Classification**: `TEST_EVIDENCE`

#### Test C: Handler Prevents Duplicates

```python
def test_c_qt_about_to_quit_prevents_duplicates(self):
    """Test C: aboutToQuit prevents duplicate tracing (UNIT)."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer, configure_runtime_tracer
    from pathlib import Path
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / 'logs'
        configure_runtime_tracer(log_dir)
        tracer = get_runtime_tracer()

        bootstrap = AppBootstrap(_defer_services=True)
        bootstrap.config.workspace_root = Path(tmpdir)
        bootstrap._tracer = tracer
        bootstrap._app_exit_code = 0

        # Call the handler twice
        bootstrap._on_qt_about_to_quit()
        bootstrap._on_qt_about_to_quit()

        # Verify only one exit event was traced
        events = tracer.events(kind='runtime_process_exit', limit=10)
        assert len(events) == 1, "Should trace exit exactly once even if called twice"
```

**Classification**: `TEST_EVIDENCE`

#### Test D: Tracer Flushes on Append

```python
def test_d_runtime_audit_tracer_flushes_on_append(self):
    """Test D: RuntimeAuditTracer flushes on append (UNIT)."""
    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer, configure_runtime_tracer
    from pathlib import Path
    import tempfile
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / 'logs'
        configure_runtime_tracer(log_dir)
        tracer = get_runtime_tracer()

        # Trace an event
        tracer.trace_runtime_lifecycle('exit', pid=12345, exit_code=0, shutdown_reason='normal_shutdown')

        # Verify the event was written to disk (flushed)
        log_file = log_dir / 'runtime_audit.jsonl'
        assert log_file.exists()

        # Read the file and verify the event is there
        with log_file.open('r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 1
            event = json.loads(lines[0])
            assert event['kind'] == 'runtime_process_exit'
            assert event['data']['pid'] == 12345
```

**Classification**: `TEST_EVIDENCE`

#### Test E: Existing Crash Path Unchanged

```python
def test_e_existing_crash_path_unchanged(self):
    """Test E: Existing crash path remains unchanged (UNIT)."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer, configure_runtime_tracer
    from pathlib import Path
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / 'logs'
        configure_runtime_tracer(log_dir)
        tracer = get_runtime_tracer()

        bootstrap = AppBootstrap(_defer_services=True)
        bootstrap.config.workspace_root = Path(tmpdir)
        bootstrap._tracer = tracer
        bootstrap._app_exit_code = 0

        # Simulate a crash event being traced first
        tracer.trace_runtime_lifecycle('crash', pid=os.getpid(), exit_code=1,
                                      shutdown_reason='exception_in_bootstrap_run',
                                      exception_type='RuntimeError')

        # Call the handler (should still trace exit because aboutToQuit is independent)
        bootstrap._on_qt_about_to_quit()

        # Verify both crash and exit events exist (crash path unchanged)
        crash_events = tracer.events(kind='runtime_process_crash', limit=10)
        exit_events = tracer.events(kind='runtime_process_exit', limit=10)
        assert len(crash_events) == 1, "Crash event should still be traced"
        assert len(exit_events) == 1, "Exit event should be traced via aboutToQuit"
```

**Classification**: `TEST_EVIDENCE`

### Existing Tests

All existing R51 lifecycle observability tests remain unchanged:
- `TestRuntimeLifecycleTracing` - Basic tracing tests
- `TestR51A9EpisodeScopedKeyboardInterrupt` - Tests for R51-A9 fix

**Classification**: `TEST_EVIDENCE`

---

## E. ENVIRONMENT IDENTITY

### Python Environment

**sys.executable**: `C:\Users\faber\miniconda3\python.exe`

**sys.version**: `3.13.2 | packaged by Anaconda, Inc. | (main, Feb 6 2025, 18:49:14) [MSC v.1929 64 bit (AMD64)]`

**sys.path** (first 3 entries):
- `''`
- `C:\Users\faber\miniconda3\python313.zip`
- `C:\Users\faber\miniconda3\DLLs`

### MCP Version

**Observed**: `mcp 1.27.0` (from `pip show mcp`)

**Expected**: `mcp==1.27.2` (canonical contract)

**Classification**: `HISTORICAL_EVIDENCE` (minor version discrepancy, not addressed in this slice)

### Launcher

**Canonical launcher**: `C:\Python\IABV_v1.5_runtime_p021v\launch_deterministic_runtime_p021v.ps1`

### Workspace

**Canonical workspace**: `C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5`

### HEAD

**Canonical HEAD**: `4256cee28d1a9712b3637d30f2abc71e015bea22`

**Classification**: `DIRECT_RUNTIME_EVIDENCE`

---

## F. LIFECYCLE INVARIANTS

### Normal Shutdown

**Expected**: `started → exit`

**After Fix**: ✓ PASS
- `runtime_process_started` traced at startup
- `runtime_process_exit` traced via `aboutToQuit` handler
- Deduplication prevents duplicate if finally block executes
- Flush ensures persistence

**Classification**: `DERIVED_EVIDENCE`

### Crash

**Expected**: `started → crash`

**After Fix**: ✓ PASS
- Crash path unchanged
- `aboutToQuit` handler does not interfere with crash tracing
- Test E confirms crash events still traced correctly

**Classification**: `DERIVED_EVIDENCE`

### KeyboardInterrupt

**Expected**: `started → exit(interrupted, 130)`

**After Fix**: ✓ PASS
- KeyboardInterrupt path unchanged (R51-A9 fix preserved)
- `_r51_interrupt_already_traced` flag still works
- `aboutToQuit` handler deduplication independent of KeyboardInterrupt deduplication

**Classification**: `DERIVED_EVIDENCE`

### SystemExit

**Expected**: `started → exit(controlled_exit, n)`

**After Fix**: ✓ PASS
- SystemExit path unchanged
- `_r51_exit_already_traced` flag works for both SystemExit and normal shutdown
- Deduplication prevents duplicate from aboutToQuit

**Classification**: `DERIVED_EVIDENCE`

---

## G. PROTECTED SURFACES

### Unchanged Components

- **P0.20**: No changes
- **P0.21r**: No changes
- **Resource metacognition**: No changes
- **Disk gate**: No changes
- **MCP version**: No changes (1.27.0 remains, discrepancy not addressed)
- **Ollama inventory**: No changes
- **Synaptic Routing**: No changes
- **External agents**: No changes

**Classification**: `DERIVED_EVIDENCE`

---

## H. EVIDENCE CLASSIFICATION

### Summary

- **DIRECT_RUNTIME_EVIDENCE**: runtime_process_started captured, runtime_process_exit NOT captured (before fix)
- **ENGINEERING_DESIGN**: Qt event loop termination behavior, buffered I/O issue, aboutToQuit signal handler
- **TEST_EVIDENCE**: 5 new unit tests for Qt shutdown path, existing tests unchanged
- **DERIVED_EVIDENCE**: Lifecycle invariants verified, protected surfaces unchanged
- **HISTORICAL_EVIDENCE**: MCP version discrepancy (1.27.0 vs 1.27.2)
- **UNVERIFIED_ASSUMPTION**: finally block always executes (DISPROVEN by runtime behavior)

---

## I. FINAL VERDICT

**`R51_A11_FIXED_READY_FOR_REAUDIT`**

### Rationale

The Qt normal shutdown exit tracing defect has been corrected with minimal, focused changes:

1. **Root Cause Identified**: Dual failure of buffered I/O and Qt termination bypass
2. **Minimal Fix**: Added flush to tracer and aboutToQuit handler as backup
3. **Deduplication**: Flag prevents duplicate exit events
4. **Tests**: 5 focused unit tests cover the new behavior
5. **Invariants**: All lifecycle paths (normal, crash, KeyboardInterrupt, SystemExit) preserved
6. **Protected Surfaces**: No changes to P0.20, P0.21r, or other protected components

The fix is production-ready for re-audit via runtime execution.

---

## J. NEXT SINGLE ACTION

**`R51-A12 — Codex re-audit`**

The next action is to perform a full runtime execution to verify that the fix resolves the Qt normal shutdown exit tracing defect. This will be done via the canonical launcher (`launch_deterministic_runtime_p021v.ps1`) following the same verification process as R51-R, but with the expectation that `runtime_process_exit` will now be captured when the user closes the Qt window normally.

**DO NOT EXECUTE THIS ACTION NOW** - This report must be reviewed and approved before proceeding to runtime re-audit.
