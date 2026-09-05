# P0.21v: Clean Canonical Runtime + Module Fingerprint - Final Report

### Source of Truth
- **Commit**: 4256cee28d1a9712b3637d30f2abc71e015bea22
- **Worktree**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
- **Verification**: Source of truth verified ✓

### Canonical HEAD
- **Value**: 4256cee28d1a9712b3637d30f2abc71e015bea22
- **Verification**: HEAD verified ✓

### Git Status
- **Status**: clean (detached HEAD)
- **Verification**: Git status verified ✓

### Python
- **Version**: 3.13.2
- **Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe
- **PYTHONPATH**: empty
- **Verification**: Python verified ✓

### sys.path
- **Status**: NOT_OBSERVED
- **Reason**: Cannot query sys.path from external process without instrumentation
- **Verification**: sys.path not observable

### Module Fingerprints

**From filesystem (canonical worktree)**:
- **iabv_v15.domain.models.__file__**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\domain\models.py
- **iabv_v15.services.evolution.discernment_frame_service.__file__**: NOT_INSPECTED
- **iabv_v15.services.evolution.diagnostic_test_executor.__file__**: NOT_INSPECTED
- **iabv_v15.services.adaptive.task_outcome_recorder.__file__**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\services\adaptive\task_outcome_recorder.py
- **iabv_v15.services.adaptive.adaptive_task_orchestrator.__file__**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\services\adaptive\adaptive_task_orchestrator.py

**From loaded process**: NOT_OBSERVED (cannot inspect from external process)

### P0.21r Presence
- **Status**: P021R_ABSENT
- **Evidence**: No execution_fact field found in models.py (lines 1-3251)
- **Verification**: P0.21r execution_fact absent from canonical code ✓

### Feature Markers
- **Status**: NOT_OBSERVED
- **Reason**: No runtime_audit.jsonl file exists in new worktree
- **Verification**: Feature markers not observable

### Process Identity
- **PID**: 2968 ✓
- **PPID**: NOT_CAPTURED
- **Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe ✓
- **Command line**: "C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe" C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\main.py ✓
- **HEAD**: 4256cee28 (from git) ✓
- **Source root**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src ✓
- **CWD**: NOT_OBSERVED
- **UIBridge**: 127.0.0.1:18921 ✓

### SQLite Path
- **Expected**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\app.sqlite
- **Status**: NOT_OBSERVED (filesystem only, not from process)
- **Verification**: SQLite path not observable from process

### Contamination
- **IABV_v1.5_canonical**: EXISTS (C:\Python\IABV_v1.5_canonical)
- **IABV_v1.5_runtime_p020m**: EXISTS (C:\Python\IABV_v1.5_runtime_p020m)
- **IABV_v1.5_runtime_p020o**: EXISTS (C:\Python\IABV_v1.5_runtime_p020o)
- **OneDrive**: NOT_CHECKED
- **PYTHONPATH**: empty ✓
- **Verification**: CONTAMINATION_DETECTED (other IABV checkouts exist)

### Runtime Build Fingerprint
- **Status**: NOT_OBSERVED
- **Reason**: No runtime_audit.jsonl file exists in new worktree
- **Verification**: Runtime build fingerprint not observable

### Stop Conditions Check
- **HEAD incorrect**: NO (HEAD = 4256cee28) ✓
- **git dirty**: NO (git status = clean) ✓
- **P0.21r appears in module loaded**: NO (P0.21r absent from canonical code) ✓
- **other checkout appears**: YES (IABV_v1.5_canonical, p020m, p020o exist) ⚠️
- **multiple instances**: NO (single instance running) ✓
- **módulo crítico apunta fuera del worktree**: NOT_OBSERVED

### Final Verdict
**CANONICAL_BASELINE_RUNTIME_PARTIAL**

**Rationale**:
- Clean worktree created from commit 4256cee28 ✓
- HEAD verified ✓
- Git status clean ✓
- P0.21r execution_fact absent from canonical code ✓
- Single instance running ✓
- UIBridge available ✓
- **Contamination detected** (other IABV checkouts exist) ⚠️
- **sys.path not observable** (external process limitation) ✗
- **Runtime audit markers not observable** (no runtime_audit.jsonl) ✗
- **Module fingerprints from loaded process not observable** (external process limitation) ✗
- **SQLite connection not observable** (external process limitation) ✗

**Conclusion**:
A clean canonical baseline runtime was successfully created from commit 4256cee28 and started. The canonical code does not contain P0.21r execution_fact. However, contamination exists in the environment (other IABV checkouts: IABV_v1.5_canonical, p020m, p020o). Runtime-internal information (sys.path, loaded module fingerprints, SQLite connection) cannot be observed from the external process without instrumentation.

### Next Single Action
Remove the contaminated environment (delete or isolate IABV_v1.5_canonical, p020m, p020o checkouts) and restart the canonical baseline runtime to ensure a completely clean environment, then retry the module fingerprint capture with instrumentation to observe sys.path and loaded module identities from within the process.
