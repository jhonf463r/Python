# P0.21x-R8: Atomic Runtime Data-Root Capture + Baseline Persistence Read - Final Report

### Baseline
- **HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22 ✓
- **Worktree**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5 ✓
- **Git status**: Clean (only __pycache__ changes, no source code modifications) ✓

### Process Identity
- **PID**: 2356 ✓
- **PPID**: 3312 ✓
- **Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe ✓
- **Command line**: "C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe" C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\main.py ✓
- **Start timestamp**: 16/08/2026 3:50:41 p.m. ✓
- **Classification**: LIVE_PROCESS_EVIDENCE

### Effective CWD
- **Real CWD**: UNRESOLVED
- **Reason**: Windows WMI returned empty WorkingDirectory
- **Classification**: CWD_UNRESOLVED

### Effective App Configuration
- **Source**: CONFIG_DERIVED from command line + load_app_config() logic
- **workspace_root**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
- **sqlite_path**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\app.sqlite
- **logs_dir**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\logs
- **Classification**: CONFIG_DERIVED

### SQLite Read
- **Path**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\app.sqlite
- **Existence**: YES ✓
- **Size**: Valid SQLite file ✓
- **SQLite header**: Valid ✓
- **Tables**: NONE (empty database) ✗
- **run_records**: NOT_EXISTS ✗
- **Classification**: FILESYSTEM_ONLY

### Runtime Audit
- **Path**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\logs\runtime_audit.jsonl
- **Existence**: NO ✗
- **boot_start**: NOT_FOUND
- **HEAD**: NOT_FOUND
- **workspace**: NOT_FOUND
- **feature markers**: NOT_FOUND
- **Classification**: FILESYSTEM_ONLY

### Process Survival
- **Status**: ALIVE throughout capture ✓
- **Death timestamp**: N/A
- **Duration**: >30 seconds
- **Classification**: PROCESS_SURVIVED

### Final Matrix

| Dato | Valor | Fuente | Fuerza |
|------|-------|--------|--------|
| PID | 2356 | LIVE_PROCESS_EVIDENCE | HIGH |
| CWD | UNRESOLVED | UNRESOLVED | NONE |
| workspace_root | C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5 | CONFIG_DERIVED | MEDIUM |
| sqlite_path | C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\app.sqlite | CONFIG_DERIVED | MEDIUM |
| logs_dir | C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\logs | CONFIG_DERIVED | MEDIUM |
| SQLite existence | YES | FILESYSTEM_ONLY | LOW |
| SQLite schema | EMPTY | FILESYSTEM_ONLY | LOW |
| RunRecord count | 0 | FILESYSTEM_ONLY | LOW |
| runtime_audit | NOT_FOUND | FILESYSTEM_ONLY | LOW |
| HEAD | 4256cee28 | FILESYSTEM_ONLY | LOW |
| source root | C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5 | FILESYSTEM_ONLY | LOW |
| process survival | ALIVE | LIVE_PROCESS_EVIDENCE | HIGH |

### Final Verdict
**PROCESS_DATA_ROOT_PARTIAL**

**Rationale**:
- Process identity captured (PID, PPID, executable, command line, start timestamp) ✓
- **Real CWD unresolved** (Windows WMI limitation) ✗
- Effective configuration derived from command line and config.py ✓
- SQLite database exists but empty (no schema) ✗
- Runtime audit not found ✗
- Process survived throughout capture ✓

**Conclusion**:
The runtime process was successfully started and its identity captured. The effective data-root configuration was derived from the command line and config.py logic, but the real CWD could not be obtained due to Windows WMI limitations. The SQLite database exists but has no schema (empty), and the runtime audit file does not exist. The process survived throughout the capture operation. The data-root identity is partially verified: process identity is strong, but persistence artifacts are missing or empty.

### NEXT_SINGLE_ACTION
Investigate why the SQLite database has no schema and why runtime_audit.jsonl is not being created by examining the database initialization code and runtime audit tracer initialization logic to determine if this is a configuration issue, initialization failure, or intentional behavior in the baseline runtime.
