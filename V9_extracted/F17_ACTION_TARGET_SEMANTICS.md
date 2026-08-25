# F17: GitHub Remote Operation Action/Target Semantics

**Date:** 2026-08-23  
**Objective:** Determine canonical P0.213 action and target for GitHub remote operations

---

## Analysis

### Current Execution Order (CRITICAL BUG)

```
1. AutonomyGovernancePolicy / approval
2. git push --set-upstream origin branch  ← REAL SIDE EFFECT, NO AUTHORIZATION
3. build ToolTask
4. capability/authority checks          ← TOO LATE
5. CapabilityActionBridge
6. adapter.run(... sandbox=False) to create PR
```

**Problem:** git push executes BEFORE capability/authority authorization.

---

## GitHub Remote Operations

### Operation 1: git push

**Side Effect:** Pushes branch to remote GitHub repository  
**Security Impact:** External repository mutation  
**Current Authorization:** NONE (executes before authorization)

**Canonical Action:** `PUSH`  
**Canonical Target:** `github_remote:{repo_name}`

**Rationale:**
- `PUSH` is the canonical action for git push operations
- Target must identify the specific GitHub repository being modified
- This is a distinct security-relevant action from PR creation
- Capability must cover the actual side effect being performed

---

### Operation 2: create PR

**Side Effect:** Creates pull request on GitHub  
**Security Impact:** External repository mutation, code review workflow  
**Current Authorization:** Partial (only protects adapter.run, not git push)

**Canonical Action:** `CREATE_PR`  
**Canonical Target:** `github_remote:{repo_name}`

**Rationale:**
- `CREATE_PR` is the canonical action for PR creation
- Target must identify the specific GitHub repository
- This is a distinct action from git push
- Both operations require separate authorization

---

## Capability Semantics

### Single Capability vs Separate Capabilities

**Question:** Should git push and PR creation use the same capability or separate capabilities?

**Analysis:**
- Both operations mutate the same external repository
- Both are security-relevant side effects
- git push is a prerequisite for PR creation
- However, they are distinct operations with distinct security implications

**Decision:** **SEPARATE CAPABILITIES**

**Rationale:**
1. **Granular authorization:** Different policies may apply to push vs PR creation
2. **Auditability:** Separate capabilities enable fine-grained audit trails
3. **Revocation:** Capability for push can be revoked without affecting PR creation capability
4. **Security principle:** Least privilege - authorize only the specific operation being performed

---

## Proposed Capability Structure

### Capability 1: git push

```
AUTHORIZED_ACTION=PUSH
AUTHORIZED_TARGET=github_remote:{repo_name}
```

**Acquisition Point:** BEFORE git push  
**Authorization Point:** BEFORE git push  
**Side Effect:** git push --set-upstream origin branch

---

### Capability 2: create PR

```
AUTHORIZED_ACTION=CREATE_PR
AUTHORIZED_TARGET=github_remote:{repo_name}
```

**Acquisition Point:** BEFORE adapter.run  
**Authorization Point:** BEFORE adapter.run  
**Side Effect:** GitHub API call to create PR

---

## Correct Execution Order

```
REQUEST
→ build authoritative action/target for git push
→ acquire capability for PUSH
→ CapabilityActionBridge.authorize_action(PUSH, github_remote:{repo})
→ AUTHORIZED for PUSH
→ git push --set-upstream origin branch
→ build authoritative action/target for create PR
→ acquire capability for CREATE_PR
→ CapabilityActionBridge.authorize_action(CREATE_PR, github_remote:{repo})
→ AUTHORIZED for CREATE_PR
→ adapter.run(... sandbox=False) to create PR
→ result
→ observation
```

---

## Implementation Strategy

### Option A: Sequential Authorization (Recommended)

Authorize git push first, then authorize PR creation. If either fails, reject entire operation.

**Pros:**
- Clear separation of concerns
- Each operation explicitly authorized
- Fail-fast on first authorization failure

**Cons:**
- Two authorization calls per operation
- Slightly more complex

---

### Option B: Single Authorization for Combined Operation

Authorize a combined "PUBLISH_BRANCH_AS_PR" action that covers both git push and PR creation.

**Pros:**
- Single authorization call
- Simpler implementation

**Cons:**
- Less granular
- Harder to audit which specific operation failed
- Violates principle of authorizing specific side effects

**Decision:** **OPTION A - Sequential Authorization**

---

## Final Semantics

### AUTHORIZED_ACTION

For git push: `PUSH`  
For create PR: `CREATE_PR`

### AUTHORIZED_TARGET

For both: `github_remote:{repo_name}`

Where `{repo_name}` is the specific GitHub repository being modified.

---

## Implementation Requirements

1. **git push authorization:**
   - Acquire capability for PUSH action before git push
   - Authorize PUSH action before git push
   - Reject git push if authorization fails

2. **PR creation authorization:**
   - Acquire capability for CREATE_PR action before adapter.run
   - Authorize CREATE_PR action before adapter.run
   - Reject PR creation if authorization fails

3. **Fail-closed behavior:**
   - If git push authorization fails, no git push, no PR creation
   - If PR creation authorization fails, git push already occurred (this is acceptable as push is a separate authorized operation)

---

## Conclusion

**AUTHORIZED_ACTION (git push):** `PUSH`  
**AUTHORIZED_TARGET (git push):** `github_remote:{repo_name}`

**AUTHORIZED_ACTION (create PR):** `CREATE_PR`  
**AUTHORIZED_TARGET (create PR):** `github_remote:{repo_name}`

**Authorization Strategy:** Sequential authorization with separate capabilities for each operation.
