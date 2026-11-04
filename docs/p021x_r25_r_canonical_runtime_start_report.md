# P0.21x-R25-R: Canonical Runtime Start for External Tool Approval - Final Report

### SOURCE OF TRUTH
**Repository**: IABV v1.5
**HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22
**Runtime Worktree**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5

==================================================
1. PRECHECK
==================================================

**HEAD Exact**: YES (4256cee28d1a9712b3637d30f2abc71e015bea22)
**Worktree Correct**: YES (C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5)
**No Other IABV Instance**: YES (no python processes found before launch)
**UI Bridge Port Available**: YES (port 5000 not in use)
**Runtime Data Root Correct**: YES (data directory exists)
**app.sqlite Exists**: YES (C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\app.sqlite)
**runtime_audit.jsonl Available**: YES (C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\data\logs\runtime_audit.jsonl)

**Conclusion**: All prechecks passed.

==================================================
2. LAUNCH
==================================================

**Launcher Used**: launch_deterministic_runtime_p021v.ps1
**Launch Method**: Canonical launcher
**Code Modifications**: NONE
**Manual Configuration**: NONE

**Launch Log Summary**:
- Startup self-check: 4/4 checks passed
- Startup health: 4 findings detected (HIGH: startup_false_ready, startup_chat_bridge_missing; MEDIUM: startup_memory_spike, startup_priority_inversion)
- MCP server: Died 3 times, gave up after max restarts
- Autonomy: 12 pending tasks, 2 blocked tasks

**Conclusion**: Runtime launched successfully but MCP server failed to start.

==================================================
3. LIVE IDENTITY
==================================================

**PID**: 29784
**PPID**: 13460
**Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe
**Command Line**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\main.py
**Source Root**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
**HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22
**Timestamp UTC**: 2026-08-16T23:01:45.447749+00:00
**Creation Date**: 16/08/2026 6:00:00 p.m.
**UI Bridge**: NOT_DETECTED (no listening ports found on 5000, 8000, 3000, 8080)
**Main Window**: NOT_DETECTED

**Conclusion**: Runtime process is alive but UI Bridge is not accessible.

==================================================
4. APPROVAL CHECKPOINT
==================================================

**ToolCard: codex_installed**:
- tool_id: codex_installed
- validation_status: unvalidated
- adapter_key: external_assistant
- available: 1

**Approval Checkpoints**: 0 entries

**UI Bridge Status**: NOT_AVAILABLE
- MCP server died 3 times and gave up
- No listening ports detected
- UI Bridge likely depends on MCP server

**Checkpoint Visibility**: NOT_VISIBLE
- UI Bridge not accessible
- Approval checkpoint cannot be presented via UI

**Conclusion**: Approval checkpoint is unavailable due to MCP server failure affecting UI Bridge functionality.

==================================================
5. STOP PROCEDURE
==================================================

**Runtime Identity**:
- PID: 29784
- HEAD: 4256cee28d1a9712b3637d30f2abc71e015bea22
- Status: ALIVE

**Checkpoint Visible**: NO
- UI Bridge not accessible
- MCP server failed

**Approval State Before Action**: 0 approval checkpoints
**Validation State Before Action**: codex_installed validation_status = unvalidated

**Exact Next Human Action**: NOT_APPLICABLE (checkpoint not visible)

**Conclusion**: Procedure stopped because approval checkpoint is not visible to human operator.

==================================================
6. FINAL VERDICT
================================================##

**APPROVAL_CHECKPOINT_UNAVAILABLE**

**Rationale**:
The IABV runtime launched successfully (PID 29784, HEAD 4256cee28d1a9712b3637d30f2abc71e015bea22) and the main process is alive. However, the MCP server died 3 times during startup and gave up after max restarts. The MCP server failure prevents the UI Bridge from functioning, which means the approval checkpoint for codex_installed validation cannot be presented to the human operator via the UI. Without the UI Bridge, the approval mechanism is inaccessible. The ToolCard for codex_installed exists with validation_status=unvalidated, but the approval checkpoint cannot be presented because the UI Bridge is not available due to the MCP server failure.

==================================================
7. NEXT_SINGLE_ACTION
================================================##

Fix the MCP server startup issue (likely a missing dependency or configuration problem) to restore UI Bridge functionality, then restart the runtime to enable the approval checkpoint presentation for codex_installed validation.
