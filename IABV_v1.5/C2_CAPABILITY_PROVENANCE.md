# C2 Capability Provenance

**Version:** VFINAL5-R2.2
**Date:** 2026-08-25

---

## Overview

This document describes the capability provenance tracking in the C2 authority service, focusing on how capabilities are issued, validated, and consumed with proper causal attribution, including VFINAL5-R2.2 Windows case-insensitive path normalization.

---

## Capability Lifecycle

### 1. Registration Phase
**Location:** `authority_service.py:handle_register_execution`

**Flow:**
1. Client provides invocation context (invocation_id, action, target, requested_scope, task_context, session_id, episode_id)
2. Authority validates client identity (OS-level authentication)
3. Authority applies authorization policy (apply_authorization_policy)
4. **VFINAL5-R2.1:** Target is canonicalized before policy evaluation
5. Authority creates canonical RunRecord with:
   - run_id (authority-owned)
   - execution_id (authority-owned)
   - consumer_pid (OS-verified)
   - generation (authority generation)
   - authorized_scope (policy decision)
   - action (requested action)
   - target (canonical target)
   - session_id (provided context)
   - episode_id (provided context)

### 2. Lease Issuance Phase
**Location:** `authority_service.py:handle_issue_lease`

**Flow:**
1. Client requests lease for existing execution (run_id, execution_id)
2. Authority retrieves canonical RunRecord
3. Authority validates:
   - Client PID matches RunRecord
   - Generation matches
   - RunRecord exists
4. Authority issues lease with:
   - lease_id (authority-owned)
   - execution_id (from RunRecord)
   - authorized_scope (from RunRecord)
   - signature (HMAC-SHA256 with authority secret)
   - expires_at (TTL-based)

### 3. Lease Consumption Phase
**Location:** `authority_service.py:handle_consume_lease`

**Flow:**
1. Client requests lease consumption (lease_id, execution_id, requested_action, requested_target)
2. Authority retrieves lease state
3. Authority validates:
   - Lease not consumed
   - Lease not expired
   - Generation matches
   - Execution ID matches
   - Signature valid
4. Authority retrieves RunRecord for binding
5. Authority validates:
   - Client PID matches RunRecord
   - Generation matches
   - Authorized scope matches
   - **VFINAL5-R2.1:** Action matches (canonical comparison)
   - **VFINAL5-R2.1:** Target matches (canonical comparison)
6. Authority atomically consumes lease (single-use enforcement)

---

## Canonical Target Provenance

### VFINAL5-R2.1 Enhancement

**Before:**
- Target stored in RunRecord as provided by client
- Target comparison was raw string comparison
- Windows backslash paths could bypass security checks

**After:**
- Target is canonicalized at registration (apply_authorization_policy)
- Canonical target stored in RunRecord
- Canonical target used for policy evaluation
- Canonical target used for lease consumption validation
- Platform-independent policy evaluation

### Canonicalization Function
**Location:** `authority_protocol.py:canonicalize_target`

**Normalizes:**
- Path separators (/ and \) to forward slash
- Redundant separators (// -> /)
- Current directory components (.)
- Parent directory components (..)
- Mixed separators

**Invariant:**
```
canonical_target(raw_variant_1) == canonical_target(raw_variant_2)
```
for semantically identical paths.

---

## Provenance Chain

The complete provenance chain for a capability:

```
1. Client Request
   → invocation_id, action, target, requested_scope, task_context
   → session_id, episode_id (VFINAL5-R2.1: required for self_update)

2. Registration
   → canonicalize_target(target)
   → apply_authorization_policy(canonical_target)
   → RunRecord created with canonical target

3. Lease Issuance
   → RunRecord retrieved
   → Lease issued with RunRecord binding

4. Lease Consumption
   → canonicalize_target(requested_target)
   → Compare with canonical target from RunRecord
   → Consume if match

5. Side Effect
   → Authorized operation executed
   → Observation recorded
   → Persistence updated
```

---

## Security Properties

### Causal Attribution
- **Property:** Every capability is traceable to its origin
- **Implementation:** RunRecord database stores full context
- **VFINAL5-R2.1:** Enhanced with required session_id/episode_id

### Single-Use Enforcement
- **Property:** Each lease can be consumed only once
- **Implementation:** Atomic UPDATE with WHERE clause
- **Status:** Existing enforcement (no change)

### Replay Protection
- **Property:** Replayed leases are rejected
- **Implementation:** Consumed flag check
- **Status:** Existing enforcement (no change)

### Platform Independence
- **Property:** Policy evaluation is platform-independent
- **Implementation:** Canonical target normalization
- **VFINAL5-R2.1:** New enhancement

---

## VFINAL5-R2.1 Changes

### Required Context Fields
- session_id is REQUIRED for self_update scope
- episode_id is REQUIRED for self_update scope
- Validation fails if these fields are missing

### Canonical Target Normalization
- Target is canonicalized before policy evaluation
- Canonical target is stored in RunRecord
- Canonical target is used for lease consumption validation
- Prevents Windows backslash bypass

### Lease Consistency
- Canonical targets used at issue and consume
- Ensures consistent target representation across lifecycle
- Prevents target manipulation attacks

---

## Test Coverage

### Unit Tests
- `test_vfinal5_r2_1_canonical_target.py`: Canonical target normalization
- `test_vfinal5_r2_1_security_regression.py`: Security regression tests

### Integration Tests
- `test_c2_vfinal5_authority_e2e.py`: C2 authority E2E tests
  - test_register_execution_creates_new_execution
  - test_verify_existing_execution_context
  - test_acquire_capability_for_existing_execution
  - test_causal_attribution_preservation

---

## Conclusion

The VFINAL5-R2.1 enhancements strengthen capability provenance by:
1. Requiring session_id and episode_id for self_update operations
2. Implementing canonical target normalization for platform-independent policy evaluation
3. Enforcing lease consistency with canonical targets

These changes ensure:
- Complete causal attribution for all capabilities
- Platform-independent security policy evaluation
- Prevention of Windows backslash bypass attacks
