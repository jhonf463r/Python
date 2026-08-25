# Audit Self-Update Call Graph

**Version:** VFINAL5-R2.2
**Date:** 2026-08-25

---

## Overview

This document describes the self-update call graph for the C2 authority service, focusing on the VFINAL5-R2.1 and VFINAL5-R2.2 enhancements for canonical target normalization, required context fields, and Windows case-insensitive path normalization.

---

## Self-Update Call Flow

### 1. MCP Tool Invocation
**Entry Point:** `self_update_tools.py:write_repo_file`

**Flow:**
```
User Request
→ write_repo_file(relative_path, content, execution_id, run_id, session_id, episode_id)
→ Target construction: f'file:{relative_path}'
→ acquire_capability_for_existing_execution(...)
```

**VFINAL5-R2.1 Context:**
- execution_id is REQUIRED
- run_id is REQUIRED
- session_id is REQUIRED (for self_update)
- episode_id is REQUIRED (for self_update)
- relative_path may contain backslashes (Windows)

### 2. Capability Acquisition
**Location:** `capability_lifecycle.py:acquire_capability_for_existing_execution`

**Flow:**
```
acquire_capability_for_existing_execution(
    execution_id, run_id, action, target, requested_scope,
    invocation_id, episode_id, session_id
)
→ verify_execution_context(execution_id, run_id, session_id, episode_id)
→ issue_lease(run_id, execution_id)
→ return lease_id, execution_id
```

**VFINAL5-R2.1 Context:**
- session_id and episode_id are passed to verify_execution_context
- Authority validates these fields are present for self_update scope

### 3. Execution Context Verification
**Location:** `authority_service.py:handle_verify_execution_context`

**Flow:**
```
handle_verify_execution_context(execution_id, run_id, session_id, episode_id)
→ Retrieve RunRecord from database
→ Verify session_id matches canonical record (VFINAL5-R2.1: REQUIRED)
→ Verify episode_id matches canonical record (VFINAL5-R2.1: REQUIRED)
→ Return valid/invalid
```

**VFINAL5-R2.1 Changes:**
- session_id is REQUIRED for self_update scope
- episode_id is REQUIRED for self_update scope
- Validation fails if these fields are missing

### 4. Lease Issuance
**Location:** `authority_service.py:handle_issue_lease`

**Flow:**
```
handle_issue_lease(run_id, execution_id)
→ Retrieve RunRecord from database
→ Verify client PID matches
→ Verify generation matches
→ Generate lease with canonical target from RunRecord
→ Return lease_id
```

**VFINAL5-R2.1 Context:**
- RunRecord contains canonical target (from registration)
- Canonical target was normalized at registration time

### 5. Lease Consumption
**Location:** `authority_service.py:handle_consume_lease`

**Flow:**
```
handle_consume_lease(lease_id, execution_id, requested_action, requested_target)
→ Retrieve lease from database
→ Verify lease not consumed
→ Verify lease not expired
→ Verify generation matches
→ Verify execution_id matches
→ Verify signature valid
→ Retrieve RunRecord for binding
→ Verify action matches (VFINAL5-R2.1: canonical comparison)
→ Verify target matches (VFINAL5-R2.1: canonical comparison)
→ Atomically consume lease
```

**VFINAL5-R2.1 Changes:**
- requested_target is canonicalized before comparison
- authorized_target from RunRecord is canonicalized before comparison
- Canonical forms are compared for platform-independent validation

### 6. Authorization Policy
**Location:** `authority_protocol.py:apply_authorization_policy`

**Flow:**
```
apply_authorization_policy(AuthorizationPolicyInput)
→ VFINAL5-R2.1: canonicalize_target(input.target)
→ Check if action is allowed for self_update scope
→ Check if target matches expected scope
→ VFINAL5-R2.1: Check if target contains security-critical paths (using canonical target)
→ Return authorization decision
```

**VFINAL5-R2.1 Changes:**
- Target is canonicalized before policy evaluation
- Security-critical path checks use canonical target
- Canonical target is stored in authorization decision constraints

### 7. Canonical Target Normalization
**Location:** `authority_protocol.py:canonicalize_target`

**Flow:**
```
canonicalize_target(target)
→ Extract prefix (file:, repository:, remote:)
→ Normalize path separators (\ to /)
→ Remove redundant separators (// to /)
→ Normalize current directory (.)
→ Normalize parent directory (..)
→ Reconstruct target with prefix
→ Return canonical target
```

**VFINAL5-R2.1 New Function:**
- Platform-independent path normalization
- Prevents Windows backslash bypass
- Ensures consistent target representation

---

## Complete Call Graph

```
User Request
  ↓
write_repo_file(relative_path, content, execution_id, run_id, session_id, episode_id)
  ↓
acquire_capability_for_existing_execution(execution_id, run_id, action, target, ...)
  ↓
verify_execution_context(execution_id, run_id, session_id, episode_id)
  ↓
handle_verify_execution_context(execution_id, run_id, session_id, episode_id)
  ↓
[Authority Service]
  ↓
handle_register_execution(invocation_id, action, target, requested_scope, task_context, session_id, episode_id)
  ↓
canonicalize_target(target) [VFINAL5-R2.1]
  ↓
apply_authorization_policy(AuthorizationPolicyInput with canonical target)
  ↓
[Policy Decision: ALLOW/DENY based on canonical target]
  ↓
Create RunRecord with canonical target
  ↓
handle_issue_lease(run_id, execution_id)
  ↓
Issue lease with RunRecord binding
  ↓
handle_consume_lease(lease_id, execution_id, requested_action, requested_target)
  ↓
canonicalize_target(requested_target) [VFINAL5-R2.1]
  ↓
canonicalize_target(authorized_target from RunRecord) [VFINAL5-R2.1]
  ↓
Compare canonical targets
  ↓
[Lease Consumption: ALLOW/DENY]
  ↓
write_repo_file_impl(...) [Side Effect]
  ↓
Observation & Persistence
```

---

## VFINAL5-R2.1 Enhancements

### 1. Required Context Fields
**Location:** `authority_service.py:handle_verify_execution_context`

**Change:**
- session_id is REQUIRED for self_update scope
- episode_id is REQUIRED for self_update scope
- Validation fails if these fields are missing

**Impact:**
- Prevents omission of required context fields
- Ensures complete causal attribution

### 2. Canonical Target Normalization
**Location:** `authority_protocol.py:canonicalize_target`

**Change:**
- New function for platform-independent path normalization
- Normalizes path separators, redundant separators, . and .. components

**Impact:**
- Prevents Windows backslash bypass
- Ensures consistent target representation
- Platform-independent policy evaluation

### 3. Lease Consistency
**Location:** `authority_service.py:handle_consume_lease`

**Change:**
- Canonicalize requested_target before comparison
- Canonicalize authorized_target from RunRecord before comparison
- Compare canonical forms

**Impact:**
- Ensures lease consistency across lifecycle
- Prevents target manipulation attacks
- Platform-independent validation

---

## Security Boundaries

### 1. Authorization Boundary
**Location:** `apply_authorization_policy`

**Timing:** Before lease issuance

**Decision:** ALLOW/DENY based on canonical target

**VFINAL5-R2.1:** Enhanced with canonical target normalization

### 2. Context Validation Boundary
**Location:** `handle_verify_execution_context`

**Timing:** Before lease consumption

**Decision:** VALID/INVALID based on session_id/episode_id

**VFINAL5-R2.1:** Enhanced with required field validation

### 3. Lease Consumption Boundary
**Location:** `handle_consume_lease`

**Timing:** Before side effects

**Decision:** CONSUME/REJECT based on lease validity and target matching

**VFINAL5-R2.1:** Enhanced with canonical target comparison

---

## Conclusion

The VFINAL5-R2.1 enhancements strengthen the self-update call graph by:
1. Requiring session_id and episode_id for self_update operations
2. Implementing canonical target normalization for platform-independent policy evaluation
3. Enforcing lease consistency with canonical targets

These changes ensure:
- Complete causal attribution for all self-update operations
- Platform-independent security policy evaluation
- Prevention of Windows backslash bypass attacks
- Consistent target representation across the capability lifecycle
