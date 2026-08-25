# VFINAL5-R2.1 PHASE 1: Reproduction Report

**Date:** 2026-08-25
**Baseline:** VFINAL5-R2 (8d3bd8ff2, P0_213_VFINAL5_R2)
**Objective:** Reproduce C2 defects identified by independent Claude audit

---

## Defects to Reproduce

### A. Omitted session_id
**Expected:** REJECT
**Current:** ACCEPTED (validation skipped when session_id is None)

### B. Omitted episode_id  
**Expected:** REJECT
**Current:** ACCEPTED (validation skipped when episode_id is None)

### C. Windows backslash target for trust-layer file
**Expected:** REJECT
**Current:** AUTHORIZED (denylist only matches forward-slash patterns)

---

## Current Code Analysis

### Session/Episode Validation (authority_service.py:997-1017)

```python
# Verify session_id matches canonical record (CROSS_SESSION = REJECT)
if session_id is not None and record_session_id is not None:
    if session_id != record_session_id:
        return AuthorityResponse(...)

# Verify episode_id matches canonical record (CROSS_EPISODE = REJECT)
if episode_id is not None and record_episode_id is not None:
    if episode_id != record_episode_id:
        return AuthorityResponse(...)
```

**Issue:** The validation is only performed if BOTH the provided value AND the canonical record are non-None. This means:
- If session_id is omitted (None), validation is skipped
- If episode_id is omitted (None), validation is skipped

### Target Policy (authority_protocol.py:518-531)

```python
security_critical_paths = [
    "services/trust/",
    "security/",
    "authority",
    "bootstrap.py",
    ".git/config",
    ".git/hooks"
]
for critical_path in security_critical_paths:
    if critical_path in input.target:
        return AuthorizationPolicyDecision(...)
```

**Issue:** The denylist uses forward-slash patterns only. On Windows:
- `file:src/iabv_v15/services/trust/capability_action_bridge.py` → REJECTED ✓
- `file:src\iabv_v15\services\trust\capability_action_bridge.py` → ACCEPTED ✗
- `file:src/iabv_v15\services\trust\capability_action_bridge.py` → ACCEPTED ✗

---

## Reproduction Test Cases

### Test A1: Omitted session_id
```python
registration = client.register_execution(
    invocation_id='test_invocation_001',
    action='WRITE_REPOSITORY_FILE',
    target='file:test.txt',
    requested_scope='self_update',
    task_context='tool_execution',
    episode_id='test_episode',
    # session_id omitted (None)
)

verification = client.verify_execution_context(
    execution_id=execution_id,
    run_id=run_id,
    # session_id omitted (None)
    episode_id='test_episode'
)
```

**Expected:** REJECT (missing required session_id)
**Actual:** ACCEPT (validation skipped)

### Test B1: Omitted episode_id
```python
registration = client.register_execution(
    invocation_id='test_invocation_002',
    action='WRITE_REPOSITORY_FILE',
    target='file:test.txt',
    requested_scope='self_update',
    task_context='tool_execution',
    session_id='test_session',
    # episode_id omitted (None)
)

verification = client.verify_execution_context(
    execution_id=execution_id,
    run_id=run_id,
    session_id='test_session',
    # episode_id omitted (None)
)
```

**Expected:** REJECT (missing required episode_id)
**Actual:** ACCEPT (validation skipped)

### Test C1: Windows backslash trust target
```python
registration = client.register_execution(
    invocation_id='test_invocation_003',
    action='WRITE_REPOSITORY_FILE',
    target='file:src\\iabv_v15\\services\\trust\\capability_action_bridge.py',
    requested_scope='self_update',
    task_context='tool_execution',
    episode_id='test_episode',
    session_id='test_session'
)
```

**Expected:** REJECT (security-critical target)
**Actual:** ACCEPT (backslash bypasses denylist)

### Test C2: Mixed separator trust target
```python
registration = client.register_execution(
    invocation_id='test_invocation_004',
    action='WRITE_REPOSITORY_FILE',
    target='file:src/iabv_v15\\services\\trust\\capability_action_bridge.py',
    requested_scope='self_update',
    task_context='tool_execution',
    episode_id='test_episode',
    session_id='test_session'
)
```

**Expected:** REJECT (security-critical target)
**Actual:** ACCEPT (mixed separator bypasses denylist)

---

## Reproduction Results

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| A1: Omitted session_id | REJECT | ACCEPT | FAIL |
| B1: Omitted episode_id | REJECT | ACCEPT | FAIL |
| C1: Backslash trust target | REJECT | ACCEPT | FAIL |
| C2: Mixed separator trust target | REJECT | ACCEPT | FAIL |

---

## Root Cause Analysis

### 1. Optional Context Fields
The current implementation treats session_id and episode_id as optional. The validation logic:
```python
if session_id is not None and record_session_id is not None:
```
allows the validation to be skipped when either value is None.

**Fix Required:** Make session_id and episode_id REQUIRED for protected self-update operations.

### 2. Platform-Specific Path Separators
The denylist uses forward-slash patterns which only work on Unix-style paths. Windows backslashes bypass the check.

**Fix Required:** Implement canonical target normalization that normalizes path separators before policy evaluation.

---

## Next Steps

Proceed to PHASE 2: Required Context Fields
