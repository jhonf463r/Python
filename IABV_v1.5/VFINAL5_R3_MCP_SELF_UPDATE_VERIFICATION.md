# VFINAL5-R3 MCP Self-Update Verification

**Date:** 2026-08-25
**Status:** VERIFIED - AUTHORITY BOUNDARY ENFORCED

---

## MCP Self-Update Tools

All MCP self-update tools are properly wired through the authority boundary:

### 1. write_repo_file
**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py:write_repo_file`

**Authority Flow:**
```
write_repo_file (MCP tool)
→ acquire_capability_for_existing_execution
→ AuthorityService.register_execution
→ AuthorityService.issue_lease
→ AuthorityService.consume_lease
→ CapabilityActionBridge.authorize_action
→ write_repo_file_impl (file write)
```

**Required Context:**
- execution_id (required)
- run_id (required)
- session_id (required)
- episode_id (required)

**Authorization:**
- Action: WRITE_REPOSITORY_FILE
- Target: file:{relative_path}
- Scope: self_update

**Fail-Closed:**
- Missing execution_id → REJECT
- Missing run_id → REJECT
- Authority unavailable → REJECT
- Capability acquisition failed → REJECT

---

### 2. apply_text_patch
**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py:apply_text_patch`

**Authority Flow:**
```
apply_text_patch (MCP tool)
→ acquire_capability_for_existing_execution
→ AuthorityService.register_execution
→ AuthorityService.issue_lease
→ AuthorityService.consume_lease
→ CapabilityActionBridge.authorize_action
→ apply_text_patch_impl (patch application)
```

**Required Context:**
- execution_id (required)
- run_id (required)
- session_id (required)
- episode_id (required)

**Authorization:**
- Action: APPLY_PATCH
- Target: file:{relative_path}
- Scope: self_update

**Fail-Closed:**
- Missing execution_id → REJECT
- Missing run_id → REJECT
- Authority unavailable → REJECT
- Capability acquisition failed → REJECT

---

### 3. git_commit_and_push
**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py:git_commit_and_push`

**Authority Flow:**
```
git_commit_and_push (MCP tool)
→ acquire_capability_for_existing_execution
→ AuthorityService.register_execution
→ AuthorityService.issue_lease
→ AuthorityService.consume_lease
→ CapabilityActionBridge.authorize_action
→ git_commit_and_push_impl (git operations)
```

**Required Context:**
- execution_id (required)
- run_id (required)
- session_id (required)
- episode_id (required)

**Authorization:**
- Action: GIT_COMMIT_AND_PUSH
- Target: repository:*
- Scope: self_update

**Fail-Closed:**
- Missing execution_id → REJECT
- Missing run_id → REJECT
- Authority unavailable → REJECT
- Capability acquisition failed → REJECT

---

## VFINAL5-R3 Enhancements

### Choke Point Enforcement
- **issue_lease:** Now validates session_id and episode_id for self_update scope
- **consume_lease:** Now validates session_id and episode_id for self_update scope
- **execution_id:** Now validated against canonical run record

### Platform-Independent Target Policy
- **canonicalize_target:** Now applies case-insensitive normalization on ALL platforms
- **Security policy:** Consistent across Windows, Linux, CI, container

---

## Conclusion

All MCP self-update tools are properly wired through the authority boundary with:
- Required execution context (execution_id, run_id, session_id, episode_id)
- Capability acquisition via acquire_capability_for_existing_execution
- Lease issuance and consumption through AuthorityService
- Action/target binding validation
- Fail-closed behavior when authority unavailable

**Status:** VERIFIED - MCP self-update authority boundary is properly enforced
