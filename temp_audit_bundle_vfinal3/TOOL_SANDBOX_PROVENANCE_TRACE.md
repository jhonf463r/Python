# TOOL_SANDBOX Provenance Trace - PART 8

**Date:** 2026-08-23  
**Task:** PART 8 — Trace TOOL_SANDBOX Provenance from user_goal to adapter.run

---

## Provenance Chain

### 1. User Input → Request
**Entry Points:**
- `tool_teach_service.execute_external_consultation()`
- `tool_teach_service.execute_task()`
- UI interactions (via request objects)

**Request Fields:**
- `request.task_role`: User-specified role (optional)
- `request.user_goal`: User's goal
- `request.goal_parameters`: Additional parameters

### 2. Request → Task
**Location:** `tool_teach_service.py`

**Lines 560, 598, 1409:**
```python
requested_by_role=request.task_role if request.task_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} else TaskRole.TOOL_USE
```

**Security Control:**
- User can only set `TaskRole.TOOL_USE` or `TaskRole.TOOL_SANDBOX`
- Any other role defaults to `TaskRole.TOOL_USE`
- This prevents arbitrary role manipulation

**Line 517:**
```python
detected_role = request.task_role if request.task_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} else TaskRole.TOOL_USE
```

**Line 668:**
```python
task_role=session.intent.detected_role
```

**Alternative Path:** Intent detection can override user-specified role

### 3. Task → Sandbox Mode
**Location:** `tool_teach_service.py`

**Line 873:**
```python
is_sandbox_mode = task.requested_by_role == TaskRole.TOOL_SANDBOX or task.metadata.get('execution_scope') == 'read_only'
```

**Sandbox Mode Triggers:**
1. `task.requested_by_role == TaskRole.TOOL_SANDBOX`
2. `task.metadata.get('execution_scope') == 'read_only'`

### 4. Sandbox Mode → Adapter
**Location:** `tool_teach_service.py`

**Line 877:**
```python
payload = adapter.run(card, task, sandbox=True)
```

**Line 908 (real execution):**
```python
payload = adapter.run(card, task, sandbox=False)
```

---

## Security Analysis

### User Input Control

**Can user set sandbox=False when they should have sandbox=True?**

**Path 1: Direct task_role**
- User sets `request.task_role = TaskRole.TOOL_USE`
- System accepts `TaskRole.TOOL_USE` → `requested_by_role = TaskRole.TOOL_USE`
- `is_sandbox_mode = False` (not TOOL_SANDBOX)
- Result: **YES, user can bypass sandbox by setting TOOL_USE**

**Path 2: Intent detection**
- System detects intent → `session.intent.detected_role`
- This can override user-specified role
- If intent is not TOOL_SANDBOX, sandbox is not enforced
- Result: **YES, intent detection can bypass sandbox**

**Path 3: execution_scope metadata**
- User can set `execution_scope` in metadata
- If not set to 'read_only', sandbox is not enforced
- Result: **YES, user can bypass sandbox by not setting execution_scope**

### Authority Authorization

**CRITICAL-1 FIX (Line 870-873):**
```python
# CRITICAL-1 FIX: TOOL_SANDBOX must use sandbox=True (TRUE SANDBOX semantics)
# TOOL_SANDBOX role is for sandboxed simulation only, not real execution
# All real execution (sandbox=False) requires authority authorization regardless of role
is_sandbox_mode = task.requested_by_role == TaskRole.TOOL_SANDBOX or task.metadata.get('execution_scope') == 'read_only'
```

**Authorization Check (Lines 970-1004):**
- Real execution (sandbox=False) requires capability authorization
- Authority authorization is enforced via `CapabilityActionBridge.authorize_action()`
- This prevents unauthorized real execution

**Security Invariant:**
- Sandbox mode → No authority required (simulated execution)
- Real execution → Authority required (capability authorization)

---

## Critical Findings

**FINDING 1: User can bypass sandbox by setting TOOL_USE**
- User sets `request.task_role = TaskRole.TOOL_USE`
- System accepts this role
- Sandbox is not enforced
- **MITIGATION:** Authority authorization is still required for real execution

**FINDING 2: Intent detection can override user role**
- System detects intent → sets `detected_role`
- This can bypass user-specified TOOL_SANDBOX
- **MITIGATION:** Authority authorization is still required for real execution

**FINDING 3: execution_scope metadata is user-controllable**
- User can set `execution_scope` in metadata
- If not set to 'read_only', sandbox is not enforced
- **MITIGATION:** Authority authorization is still required for real execution

**FINDING 4: Authority authorization is the real security boundary**
- Sandbox mode is for simulation only
- Real execution (sandbox=False) always requires authority authorization
- This is enforced via `CapabilityActionBridge.authorize_action()`
- **CONCLUSION:** The sandbox bypass is mitigated by authority authorization

---

## Security Invariant Verification

**Invariant:** "sandbox=True → no real side effects"

**Verification:**
1. **ShellToolAdapter:** ✅ FIXED (PART 5) - sandbox=True returns simulated result
2. **LocalCliToolAdapter:** ✅ FIXED (PART 6) - sandbox=True returns simulated result
3. **Other adapters:** ⚠️ PARTIAL/NO_SANDBOX (PART 4)

**Invariant:** "sandbox=False → authority authorization required"

**Verification:**
1. **ToolTeachService.execute_task():** ✅ ENFORCED (Lines 970-1004)
2. **GitHubRemoteService.publish_branch_as_pr():** ✅ ENFORCED (Lines 305-314, 385-392)
3. **ToolRollbackManager.attempt():** ✅ ENFORCED (Lines 70-78)

**Invariant:** "TOOL_SANDBOX role → sandbox=True"

**Verification:**
1. **ToolTeachService.execute_task():** ✅ ENFORCED (Line 873, 877)
2. **ToolTeachService.execute_external_consultation():** ✅ ENFORCED (Line 743)

---

## Recommendations

**SHORT TERM (for V11 audit):**
1. Document that sandbox mode is not a security boundary
2. Document that authority authorization is the real security boundary
3. Note that 3 adapters still need sandbox fixes (PART 4 findings)

**LONG TERM:**
1. Fix remaining adapters with NO_SANDBOX distinction (AiderToolAdapter, DesktopHumanToolAdapter, DevinApiToolAdapter)
2. Review PARTIAL_SANDBOX adapters (MCPToolAdapter, OllamaToolAdapter, PlaywrightToolAdapter)
3. Consider making sandbox mode a stronger security boundary

---

## Conclusion

**TOOL_SANDBOX Provenance:**
- User can set `task_role` to TOOL_USE or TOOL_SANDBOX
- Intent detection can override user role
- `execution_scope` metadata can bypass sandbox
- **BUT:** Authority authorization is always required for real execution

**Security Boundary:**
- Sandbox mode is NOT a security boundary
- Authority authorization IS the security boundary
- The CRITICAL-1 fix ensures that real execution always requires authority authorization

**Risk Assessment:**
- **HIGH RISK:** 3 adapters with NO_SANDBOX distinction (PART 4)
- **MEDIUM RISK:** 3 adapters with PARTIAL_SANDBOX (PART 4)
- **LOW RISK:** Sandbox bypass is mitigated by authority authorization

---

## Next Steps

Proceed with:
- PART 9: Repeat exhaustive side-effect inventory with sandbox classification
