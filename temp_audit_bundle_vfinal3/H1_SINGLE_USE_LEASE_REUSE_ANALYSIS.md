# H-1 Single-Use Lease Reuse Analysis

**Date:** 2026-08-24  
**Task:** H-1 — Fix Single-Use Lease Reuse in GitHubRemoteService

---

## Current State

**Location:** `src/iabv_v15/services/tools/github_remote_service.py`

**Previous Issue:** GitHubRemoteService reused the same lease_id for both PUSH and CREATE_PR actions.

---

## Evidence of Previous Issue

### Lines 305-325: PUSH Authorization (Previous)

```python
push_auth_result = self.capability_action_bridge.authorize_action(
    ActionRequest(
        lease_id=lease_id,
        execution_id=f'git_push_{head}_{int(self._clock())}',
        action=action,
        target=target,
    )
)
```

### Line 375: Lease Reuse (Previous)

```python
lease_id=lease_id,  # Reuse same lease for PR creation
```

### Lines 384-403: CREATE_PR Authorization with Same Lease (Previous)

```python
pr_auth_result = self.capability_action_bridge.authorize_action(
    ActionRequest(
        lease_id=pr_task.lease_id,  # Same lease_id as PUSH
        execution_id=pr_task.execution_id,
        action=pr_task.action,
        target=pr_task.target,
    )
)
```

---

## Problem

The canonical lease consumption is single-use. Therefore:

1. First authorization (PUSH) → lease consumed → success
2. Second authorization (CREATE_PR) → lease already consumed → failure

**Result:** git push succeeds, but PR creation fails.

---

## Analysis

PUSH and CREATE_PR are two distinct operations:

- **PUSH**: Upload local branch to remote repository
- **CREATE_PR**: Create a pull request on GitHub

These should be treated as separate authorized actions, each requiring its own valid capability/lease.

---

## Changes Applied

### Step 1: Updated publish_branch_as_pr signature

Added parameter:
- `pr_lease_id: str | None = None`

### Step 2: Use separate leases

```python
# Use lease_id for PUSH (unchanged)
push_auth_result = self.capability_action_bridge.authorize_action(
    ActionRequest(
        lease_id=lease_id,
        execution_id=f'git_push_{head}_{int(self._clock())}',
        action='PUSH',
        target=target,
    )
)

# Use pr_lease_id for CREATE_PR (NEW)
actual_pr_lease_id = pr_lease_id or (approval_context.get('pr_lease_id') if approval_context else None)
if actual_pr_lease_id is None:
    # Missing PR capability - reject PR creation (fail-closed)
    return self._finalize(
        evidence,
        PublishResult(
            success=False, branch=head, base=base_name,
            pushed=True,
            error="PR creation requires separate capability (pr_lease_id). No capability provided.",
        ),
    )

pr_task = ToolTask(
    ...
    lease_id=actual_pr_lease_id,  # H-1: Use separate lease for PR creation
    action='CREATE_PR',
    target=target,
    execution_id=f'create_pr_{head}_{int(self._clock())}',
)
```

---

## H-1 Status

**Status:** ✅ COMPLETE

The single-use lease reuse issue has been fixed. PUSH and CREATE_PR now use separate lease_ids. The caller must provide two separate leases when calling publish_branch_as_pr.

---

## Next Steps

1. Update callers to provide separate lease_ids
2. Create tests for H-1 fix
3. Proceed to PART 1: Complete side-effect inventory after fixes
