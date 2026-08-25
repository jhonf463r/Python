# TOOL_SANDBOX Semantics Verification

**Date:** 2026-08-23  
**Objective:** Verify TOOL_SANDBOX uses sandbox=True or capability required

---

## Production Code Verification

### File: src/iabv_v15/services/tools/tool_teach_service.py

### Lines 870-877

```python
# CRITICAL-1 FIX: TOOL_SANDBOX must use sandbox=True (TRUE SANDBOX semantics)
# TOOL_SANDBOX role is for sandboxed simulation only, not real execution
# All real execution (sandbox=False) requires authority authorization regardless of role
is_sandbox_mode = task.requested_by_role == TaskRole.TOOL_SANDBOX or task.metadata.get('execution_scope') == 'read_only'

if is_sandbox_mode:
    # Sandbox mode: use sandbox=True for isolated simulation
    payload = adapter.run(card, task, sandbox=True)
```

---

## Analysis

### TOOL_SANDBOX Role

**Condition:** `task.requested_by_role == TaskRole.TOOL_SANDBOX`

**Behavior:**
- Uses `sandbox=True` (line 877)
- Isolated simulation only
- No real execution
- No capability required (exempt by design)

### Read-Only Execution Scope

**Condition:** `task.metadata.get('execution_scope') == 'read_only'`

**Behavior:**
- Uses `sandbox=True` (line 877)
- Isolated simulation only
- No real execution
- No capability required (exempt by design)

### Real Execution

**Condition:** Not TOOL_SANDBOX and not read_only

**Behavior:**
- Uses `sandbox=False` (real execution)
- Requires capability authorization (lines 877+)
- Authority enforced before execution

---

## Forbidden State Check

**Forbidden State:**
```
TOOL_SANDBOX
→ no authority
→ sandbox=False
```

**Verification:**
- TOOL_SANDBOX role → `is_sandbox_mode = True` → `sandbox=True` ✅
- Read-only scope → `is_sandbox_mode = True` → `sandbox=True` ✅
- Real execution → `is_sandbox_mode = False` → requires authority ✅

**Result:** ✅ Forbidden state does not exist

---

## Security Invariants

1. **TOOL_SANDBOX uses sandbox=True** ✅
2. **Read-only execution uses sandbox=True** ✅
3. **Real execution requires capability authorization** ✅
4. **Real execution uses sandbox=False** ✅
5. **No authority + sandbox=False is impossible** ✅

---

## Conclusion

**TOOL_SANDBOX Semantics:** ✅ VERIFIED

**Implementation:**
- TOOL_SANDBOX role → sandbox=True (isolated simulation)
- Read-only scope → sandbox=True (isolated simulation)
- Real execution → sandbox=False (requires capability authorization)

**Forbidden State:** Does not exist ✅
