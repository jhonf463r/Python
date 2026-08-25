# VFINAL5-R2.1 PHASE 9: Real MCP Path Verification

**Date:** 2026-08-25
**Status:** VERIFIED - MCP WRAPPERS WORK CORRECTLY WITH CANONICALIZATION

---

## MCP Self-Update Tool Flow

### write_repo_file Tool
**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py:write_repo_file`

**Current Flow:**
1. User provides `relative_path` (may contain backslashes on Windows)
2. Wrapper constructs target as `f'file:{relative_path}'`
3. Target is passed to `acquire_capability_for_existing_execution`
4. Authority canonicalizes target in `apply_authorization_policy` (registration)
5. Authority checks security-critical paths against canonical target
6. If authorized, lease is issued with canonical target
7. On consumption, authority canonicalizes requested_target and compares to authorized_target

---

## Canonicalization Location

### Authority-Level Canonicalization (VFINAL5-R2.1)
**Location:** `authority_protocol.py:canonicalize_target`

**Applied at:**
1. `apply_authorization_policy` - during registration (before lease issuance)
2. `handle_consume_lease` - during consumption (before validation)

**Benefits:**
- Single source of truth for canonicalization
- Authority enforces platform-independent policy
- Client cannot bypass canonicalization
- Consistent behavior across all clients

### MCP Wrapper (No Changes Required)
**Location:** `self_update_tools.py:write_repo_file`

**Current Behavior:**
- Passes raw target to authority
- Authority handles canonicalization
- No changes needed

---

## Verification Test Cases

### Test 1: Forward slash path
```
User calls: write_repo_file("src/iabv_v15/example.py", ...)
Wrapper target: "file:src/iabv_v15/example.py"
Authority canonical: "file:src/iabv_v15/example.py"
Result: ✓ Works correctly
```

### Test 2: Backslash path (Windows)
```
User calls: write_repo_file("src\\iabv_v15\\example.py", ...)
Wrapper target: "file:src\\iabv_v15\\example.py"
Authority canonical: "file:src/iabv_v15/example.py"
Result: ✓ Works correctly (canonicalized at authority)
```

### Test 3: Mixed separator path
```
User calls: write_repo_file("src/iabv_v15\\example.py", ...)
Wrapper target: "file:src/iabv_v15\\example.py"
Authority canonical: "file:src/iabv_v15/example.py"
Result: ✓ Works correctly (canonicalized at authority)
```

### Test 4: Security-critical path (backslash bypass attempt)
```
User calls: write_repo_file("src\\iabv_v15\\services\\trust\\foo.py", ...)
Wrapper target: "file:src\\iabv_v15\\services\\trust\\foo.py"
Authority canonical: "file:src/iabv_v15/services/trust/foo.py"
Policy check: "services/trust/" in canonical target
Result: ✓ REJECTED (canonical target is security-critical)
```

---

## Execution Causality

### Causal Attribution Preserved
The execution causality chain remains intact:

```
ToolTask
→ trusted context (execution_id, run_id, session_id, episode_id)
→ MCP wrapper (write_repo_file)
→ target construction (file:relative_path)
→ capability acquisition (acquire_capability_for_existing_execution)
→ authority (canonicalization + policy check)
→ lease issuance (with canonical target)
→ lease consumption (canonical target validation)
→ ActionRequest
→ AuthorityService
→ safe target validation
→ effect
→ observation
→ persistence
```

**VFINAL5-R2.1 Enhancement:**
- Canonicalization happens at authority boundary
- Policy evaluation uses canonical target
- Lease consistency enforced with canonical targets
- Causality preserved through all stages

---

## Conclusion

The MCP self-update wrappers work correctly with VFINAL5-R2.1 canonicalization:

1. **No changes required** to MCP wrappers
2. **Canonicalization happens at authority level** (correct design)
3. **Windows backslash bypass is fixed** (canonicalized before policy check)
4. **Execution causality is preserved** (canonical target flows through entire chain)
5. **Lease consistency is enforced** (canonical targets at issue and consume)

**PHASE 9 STATUS: COMPLETE - NO MCP WRAPPER CHANGES REQUIRED**
