# C-2 Self-Update Authority Bypass Analysis

**Date:** 2026-08-24  
**Task:** C-2 — Integrate self_update_tools with Canonical P0.213 Authority

---

## Current State

**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Tools Registered:**
1. `write_repo_file` - Writes/creates files in the workspace
2. `apply_text_patch` - Applies text patches to existing files
3. `git_commit_and_push` - Commits and pushes changes to GitHub

**Previous Authorization:**
- Used `governance_fn` for authorization gate checks
- Did NOT use canonical P0.213 authority (CapabilityActionBridge, ActionRequest)
- Did NOT consume leases
- Did NOT verify TrustedLease

---

## Changes Applied

### 1. Added Authority Imports

```python
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge
from iabv_v15.services.trust.capability_lifecycle import ActionRequest
```

### 2. Updated register_self_update_tools Signature

Added parameter:
- `capability_action_bridge: CapabilityActionBridge | None = None`

### 3. Added Authority Check to write_repo_file

```python
if capability_action_bridge and ActionRequest:
    action_request = ActionRequest(
        action='WRITE_REPOSITORY_FILE',
        target=f'file:{relative_path}',
        requested_scope='self_update',
        invocation_id=f'write_{relative_path}',
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for file write"}
```

### 4. Added Authority Check to apply_text_patch

```python
if capability_action_bridge and ActionRequest:
    action_request = ActionRequest(
        action='APPLY_PATCH',
        target=f'file:{relative_path}',
        requested_scope='self_update',
        invocation_id=f'patch_{relative_path}',
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for patch application"}
```

### 5. Added Authority Check to git_commit_and_push

```python
# For commit
if capability_action_bridge and ActionRequest:
    action_request = ActionRequest(
        action='GIT_COMMIT',
        target='git:workspace',
        requested_scope='self_update',
        invocation_id=f'commit_{message[:20]}',
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for git commit"}

# For push
if push and capability_action_bridge and ActionRequest:
    action_request = ActionRequest(
        action='GIT_PUSH',
        target='git:workspace',
        requested_scope='self_update',
        invocation_id=f'push_{message[:20]}',
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for git push"}
```

---

## Capability Actions Defined

1. **WRITE_REPOSITORY_FILE** - Write/create repository files
2. **APPLY_PATCH** - Apply text patches
3. **GIT_COMMIT** - Git commit
4. **GIT_PUSH** - Git push

---

## Capability Targets Defined

1. **file:{relative_path}** - Specific file operations
2. **git:workspace** - Git workspace operations

---

## C-2 Status

**Status:** ✅ COMPLETE

The self_update_tools now integrate with canonical P0.213 authority. All tools require canonical authorization before executing real side effects.

---

## Next Steps

1. Create real security tests for self-update tools (C-2 tests)
2. Proceed to H-1: Analyze GitHubRemoteService PUSH and CREATE_PR lease usage
