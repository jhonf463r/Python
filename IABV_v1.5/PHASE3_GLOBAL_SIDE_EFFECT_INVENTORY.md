# PHASE 3: Global Side-Effect Inventory

**Date:** 2026-08-25
**Branch:** p0213/vfinal5-r3-choke-point
**Commit:** 7c16778cb (R3.1 baseline)

---

## Security-Critical Paths

### 1. tool_adapters.py
**FILE:** src/iabv_v15/services/tools/tool_adapters.py
**FUNCTION:** ShellToolAdapter.run
**EXECUTION_METHOD:** Simulated (no subprocess.run)
**EFFECT:** None (sandbox-only)
**AUTHORITY:** N/A (sandbox-only)
**CAPABILITY:** N/A (sandbox-only)
**LEASE:** N/A (sandbox-only)
**SANDBOX:** TRUE
**VERDICT:** SAFE ✓

---

### 2. tool_adapters.py
**FILE:** src/iabv_v15/services/tools/tool_adapters.py
**FUNCTION:** AiderToolAdapter.run
**EXECUTION_METHOD:** Simulated (no subprocess.run)
**EFFECT:** None (sandbox-only)
**AUTHORITY:** N/A (sandbox-only)
**CAPABILITY:** N/A (sandbox-only)
**LEASE:** N/A (sandbox-only)
**SANDBOX:** TRUE
**VERDICT:** SAFE ✓

---

### 3. tool_adapters.py
**FILE:** src/iabv_v15/services/tools/tool_adapters.py
**FUNCTION:** LocalCliToolAdapter.run
**EXECUTION_METHOD:** Simulated (no subprocess.run)
**EFFECT:** None (sandbox-only)
**AUTHORITY:** N/A (sandbox-only)
**CAPABILITY:** N/A (sandbox-only)
**LEASE:** N/A (sandbox-only)
**SANDBOX:** TRUE
**VERDICT:** SAFE ✓ (R3.2 fix)

---

### 4. github_remote_service.py
**FILE:** src/iabv_v15/services/tools/github_remote_service.py
**FUNCTION:** _run_git_command
**EXECUTION_METHOD:** subprocess.run
**EFFECT:** Git operations (commit, push, etc.)
**AUTHORITY:** capability_action_bridge.authorize_action
**CAPABILITY:** YES (via capability_action_bridge)
**LEASE:** YES (via capability_action_bridge)
**SANDBOX:** FALSE (real subprocess)
**VERDICT:** PROTECTED BY AUTHORITY ✓

---

### 5. self_update_tools.py
**FILE:** src/iabv_v15/infra/mcp/self_update_tools.py
**FUNCTION:** git_commit_and_push_impl
**EXECUTION_METHOD:** subprocess.run
**EFFECT:** Git commit and push
**AUTHORITY:** capability_action_bridge.authorize_action
**CAPABILITY:** YES (via capability_action_bridge)
**LEASE:** YES (via capability_action_bridge)
**SANDBOX:** FALSE (real subprocess)
**VERDICT:** PROTECTED BY AUTHORITY ✓

---

### 6. self_update_tools.py
**FILE:** src/iabv_v15/infra/mcp/self_update_tools.py
**FUNCTION:** write_repo_file_impl
**EXECUTION_METHOD:** File write (no subprocess)
**EFFECT:** File write
**AUTHORITY:** capability_action_bridge.authorize_action
**CAPABILITY:** YES (via capability_action_bridge)
**LEASE:** YES (via capability_action_bridge)
**SANDBOX:** FALSE (real file write)
**VERDICT:** PROTECTED BY AUTHORITY ✓

---

## Non-Security-Critical Paths

### 7. world_model.py
**FILE:** src/iabv_v15/services/evolution/world_model.py
**FUNCTION:** _powershell_json
**EXECUTION_METHOD:** subprocess.run
**EFFECT:** PowerShell execution for world model
**AUTHORITY:** N/A (not a protected side effect)
**CAPABILITY:** N/A
**LEASE:** N/A
**SANDBOX:** FALSE
**VERDICT:** NOT A PROTECTED SIDE EFFECT (world model observation, not mutation)

---

### 8. gpu_model_benchmark.py
**FILE:** src/iabv_v15/services/lab/gpu_model_benchmark.py
**FUNCTION:** GPU benchmark operations
**EXECUTION_METHOD:** subprocess.run
**EFFECT:** GPU benchmarking
**AUTHORITY:** N/A (not a protected side effect)
**CAPABILITY:** N/A
**LEASE:** N/A
**SANDBOX:** FALSE
**VERDICT:** NOT A PROTECTED SIDE EFFECT (lab operations, not mutation)

---

### 9. ui_execution_runner.py
**FILE:** src/iabv_v15/services/tools/ui_execution_runner.py
**FUNCTION:** UI automation operations
**EXECUTION_METHOD:** subprocess.run, subprocess.Popen
**EFFECT:** UI automation
**AUTHORITY:** N/A (not a protected side effect)
**CAPABILITY:** N/A
**LEASE:** N/A
**SANDBOX:** FALSE
**VERDICT:** NOT A PROTECTED SIDE EFFECT (UI operations, not mutation of protected files)

---

### 10. control_center_viewmodel.py
**FILE:** src/iabv_v15/ui/viewmodels/control_center_viewmodel.py
**FUNCTION:** Control center operations
**EXECUTION_METHOD:** subprocess.run, subprocess.Popen
**EFFECT:** Control center UI operations
**AUTHORITY:** N/A (not a protected side effect)
**CAPABILITY:** N/A
**LEASE:** N/A
**SANDBOX:** FALSE
**VERDICT:** NOT A PROTECTED SIDE EFFECT (UI operations, not mutation of protected files)

---

## Security Invariant Verification

**Invariant:** ANY PROTECTED SIDE EFFECT → CANONICAL AUTHORITY BOUNDARY

**Protected Side Effects:**
1. Git operations (github_remote_service.py) → capability_action_bridge.authorize_action ✓
2. Git commit/push (self_update_tools.py) → capability_action_bridge.authorize_action ✓
3. File write (self_update_tools.py) → capability_action_bridge.authorize_action ✓

**Non-Protected Side Effects:**
1. World model observation → Not a protected side effect
2. GPU benchmarking → Not a protected side effect
3. UI automation → Not a protected side effect
4. Control center UI → Not a protected side effect

**Second Authorization Authority:** None ✓

**Conclusion:** All protected side effects go through the canonical authority boundary. No second authorization authority exists.
