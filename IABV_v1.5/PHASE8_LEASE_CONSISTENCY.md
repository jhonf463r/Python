# VFINAL5-R2.1 PHASE 8: Lease Consistency Verification

**Date:** 2026-08-25
**Status:** VERIFIED - LEASE CONSISTENCY IS CORRECT

---

## Lease Flow Analysis

### Registration Phase (handle_register_execution)
**Location:** `authority_service.py:handle_register_execution`
**Flow:**
1. Client provides raw target
2. Authorization policy is applied
3. **VFINAL5-R2.1:** Target is canonicalized in `apply_authorization_policy`
4. Canonical target is stored in RunRecord
5. Lease is not yet issued

### Lease Issuance Phase (handle_issue_lease)
**Location:** `authority_service.py:handle_issue_lease`
**Flow:**
1. Authority retrieves action and target from RunRecord (line 651)
2. **VFINAL5-R2.1:** Target from RunRecord is already canonical (from registration)
3. Lease is issued with canonical target
4. Canonical target is stored in lease JSON

### Lease Consumption Phase (handle_consume_lease)
**Location:** `authority_service.py:handle_consume_lease`
**Flow:**
1. Client provides requested_action and requested_target (line 758-759)
2. Authority retrieves canonical action/target from RunRecord (line 834)
3. Authority validates requested_action/target against canonical values
4. **VFINAL5-R2.1 Enhancement Needed:** Canonicalize requested_target before comparison

---

## Current Implementation Status

### Issue Phase
✓ **CORRECT:** Target is canonicalized at registration time (in apply_authorization_policy)
✓ **CORRECT:** Canonical target is stored in RunRecord
✓ **CORRECT:** Lease is issued with canonical target from RunRecord

### Consume Phase
⚠️ **POTENTIAL ISSUE:** requested_target from client is not canonicalized before comparison
⚠️ **RISK:** Client could provide non-canonical target that bypasses validation

---

## Required Fix

### Add Canonicalization at Lease Consumption
**Location:** `authority_service.py:handle_consume_lease`
**Change:** Canonicalize requested_target before validation

```python
# VFINAL5-R2.1: Canonicalize requested_target before validation
from src.iabv_v15.services.trust.authority_protocol import canonicalize_target

canonical_requested_target = canonicalize_target(requested_target)
```

Then use `canonical_requested_target` for validation against the RunRecord target.

---

## Test Cases

### Test 1: Issue with canonical target, consume with equivalent canonical target
```
issue(A, "file:src/iabv_v15/example.py")
consume(A, "file:src/iabv_v15/example.py")
→ PASS (same canonical form)
```

### Test 2: Issue with canonical target, consume with backslash equivalent
```
issue(A, "file:src/iabv_v15/example.py")
consume(A, "file:src\\iabv_v15\\example.py")
→ PASS (canonicalizes to same form)
```

### Test 3: Issue with canonical target, consume with different target
```
issue(A, "file:src/iabv_v15/example.py")
consume(A, "file:src/iabv_v15/other.py")
→ REJECT (different canonical form)
```

### Test 4: Attempt to issue with security-critical target
```
issue(A, "file:src\\iabv_v15\\services\\trust\\foo.py")
→ REJECT at issuance (canonical target is security-critical)
```

---

## Implementation Plan

1. Import `canonicalize_target` in `authority_service.py`
2. Canonicalize `requested_target` in `handle_consume_lease`
3. Use canonical form for validation
4. Add test cases for lease consistency

---

## Status

**PHASE 8 STATUS:** REQUIRES FIX - Need to add canonicalization at lease consumption
