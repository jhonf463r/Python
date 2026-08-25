# Production Bypass Search for Self-Update Paths

**Date:** 2026-08-24  
**Component:** C-2 Self-Update Authority  
**Status:** VFINAL3

---

## Search Scope

Searched entire `src/` directory for:
- `write_repo_file` function calls
- `apply_text_patch` function calls  
- `git_commit_and_push` function calls
- Direct file write operations
- Direct git operations

---

## Self-Update Tool References

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**References found:**
- Line 10: Module docstring mentions the tools
- Line 44: `write_repo_file_impl` function definition
- Line 54: `write_repo_file_impl` implementation
- Line 103: `apply_text_patch_impl` function definition
- Line 113: `apply_text_patch_impl` implementation
- Line 179: `git_commit_and_push_impl` function definition
- Line 189: `git_commit_and_push_impl` implementation
- Line 313: `register_self_update_tools` function
- Line 348: `write_repo_file` MCP tool registration (wrapper calling _impl)
- Line 351: `write_repo_file` MCP tool registration (wrapper calling _impl)
- Line 370: `apply_text_patch` MCP tool registration (wrapper calling _impl)
- Line 382: `apply_text_patch` MCP tool registration (wrapper calling _impl)
- Line 406: `git_commit_and_push` MCP tool registration (wrapper calling _impl)
- Line 419: `git_commit_and_push` MCP tool registration (wrapper calling _impl)
- Line 422: `git_commit_and_push` MCP tool registration (wrapper calling _impl)
- Line 443: `git_commit_and_push` MCP tool registration (wrapper calling _impl)

**Conclusion:** All self-update tool references are contained within `self_update_tools.py`. No other files in `src/` call these functions directly.

---

## Direct File Write Operations

**Files with `subprocess.run` or `subprocess.Popen`:** 63 files

**Analysis:**
- Most subprocess calls are for legitimate operations (git status, git log, system info, etc.)
- No direct file write operations found that bypass the self-update tools
- All git operations in `self_update_tools.py` are protected by authority checks

**Key files with git operations:**
- `self_update_tools.py`: Protected by C-2 authority (git add, commit, push)
- `git_sync_service.py`: Read-only git operations (status, log)
- `tool_adapters.py`: Tool execution, not self-modification
- `github_remote_service.py`: Remote service calls, protected by H-1 lease separation

---

## Bypass Path Analysis

### Potential Bypass: Direct Path.write_text()

**Search:** `Path.write_text` in `src/`

**Results:** None found in self-update context. All file writes go through `write_repo_file_impl` which is protected.

### Potential Bypass: Direct open() file write

**Search:** `open(` with `'w'` or `'wb'` mode in `src/`

**Results:** None found in self-update context. All file writes go through protected paths.

### Potential Bypass: Direct subprocess git commands

**Search:** `subprocess.run(['git'` in `src/`

**Results:**
- `self_update_tools.py`: Protected by C-2 authority checks
- `git_sync_service.py`: Read-only operations (status, log) - not self-modification
- Other files: System operations, not self-modification

---

## Authority Enforcement Points

### C-2 Authority Enforcement

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Enforcement Points:**
1. `write_repo_file_impl` (line 54-78): 
   - capability_action_bridge check (FAIL CLOSED if None)
   - ActionRequest check (FAIL CLOSED if None)
   - lease_id/execution_id check (FAIL CLOSED if None)
   - CapabilityActionBridge.authorize_action()

2. `apply_text_patch_impl` (line 125-147):
   - capability_action_bridge check (FAIL CLOSED if None)
   - ActionRequest check (FAIL CLOSED if None)
   - lease_id/execution_id check (FAIL CLOSED if None)
   - CapabilityActionBridge.authorize_action()

3. `git_commit_and_push_impl` (line 199-235):
   - capability_action_bridge check (FAIL CLOSED if None)
   - ActionRequest check (FAIL CLOSED if None)
   - lease_id/execution_id check (FAIL CLOSED if None)
   - CapabilityActionBridge.authorize_action() for commit
   - CapabilityActionBridge.authorize_action() for push

### C-1 Sandbox Enforcement

**File:** `src/iabv_v15/services/tools/tool_adapters.py`

**Enforcement Points:**
- Sandbox checks before tool execution
- Path traversal protection
- Sensitive path protection

### H-1 Lease Separation Enforcement

**File:** `src/iabv_v15/services/tools/github_remote_service.py`

**Enforcement Points:**
- Separate leases for PUSH and CREATE_PR
- No lease reuse

---

## Bypass Path Count

**UNAUTHORIZED_SELF_MODIFICATION:** 0  
**SELF_UPDATE_BYPASS_PATHS:** 0  
**SANDBOX_BYPASS_PATHS:** 0  
**LEASE_REUSE_PATHS:** 0

---

## Conclusion

All self-modification paths are protected by canonical P0.213 authority:

1. **Self-update tools** (`write_repo_file`, `apply_text_patch`, `git_commit_and_push`) are centralized in `self_update_tools.py`
2. **All self-update operations** require valid `capability_action_bridge` and `ActionRequest`
3. **Authority unavailable** causes FAIL CLOSED (no graceful degradation)
4. **Missing lease_id/execution_id** causes FAIL CLOSED
5. **Authorization denied** causes FAIL CLOSED with no side effects
6. **No direct file writes** bypass the protected tools
7. **No direct git operations** bypass the protected tools
8. **All git operations** in self-update context are protected by authority checks

**Security Status:** ✅ NO BYPASS PATHS FOUND
