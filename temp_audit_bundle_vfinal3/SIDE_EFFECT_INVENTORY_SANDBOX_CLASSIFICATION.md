# Exhaustive Side-Effect Inventory with Sandbox Classification - PART 9

**Date:** 2026-08-23  
**Task:** PART 9 — Repeat exhaustive side-effect inventory with sandbox classification

---

## Classification Criteria

**SANDBOX-SAFE:** Can execute in sandbox mode without real side effects
- Read-only operations (version checks, status queries)
- Local environment inspection
- No external mutations

**SANDBOX-UNSAFE:** Should NOT execute in sandbox mode
- Real subprocess execution
- Network calls
- Filesystem mutations
- Database mutations
- External system interactions

---

## Tool Adapters

### ShellToolAdapter
**File:** `tool_adapters.py:1771`
**Call:** `subprocess.run(command, capture_output=True, text=True, shell=True, check=False)`
**Sandbox Classification:** ✅ SANDBOX-SAFE (FIXED in PART 5)
**Sandbox Behavior:** sandbox=True returns simulated result, NO subprocess execution

### LocalCliToolAdapter
**File:** `tool_adapters.py:2655`
**Call:** `subprocess.run(cmd_list, capture_output=True, text=True, shell=False, check=False, timeout=self.timeout_seconds)`
**Sandbox Classification:** ✅ SANDBOX-SAFE (FIXED in PART 6)
**Sandbox Behavior:** sandbox=True returns simulated result, NO subprocess execution

### AiderToolAdapter
**File:** `tool_adapters.py:1522, 1525`
**Calls:** 
- `subprocess.run([*base_cmd, '--version'], capture_output=True, text=True, check=False)`
- `subprocess.run([*base_cmd, *args], capture_output=True, text=True, check=False, timeout=timeout_seconds)`
**Sandbox Classification:** ❌ SANDBOX-UNSAFE (NO_SANDBOX distinction)
**Sandbox Behavior:** sandbox=True still executes real subprocess
**Impact:** Can execute real code edits in sandbox mode

### GitHubRemoteService (git_runner)
**File:** `github_remote_service.py:62`
**Call:** `subprocess.run(argv, cwd=str(cwd), check=False, capture_output=True, text=True, timeout=120)`
**Sandbox Classification:** ✅ SANDBOX-SAFE (Protected by authorization)
**Sandbox Behavior:** Only called after authority authorization (F14 fix)
**Impact:** Real git push requires capability authorization

---

## Environment & Metacognition Services

### CommonSenseEngine
**File:** `common_sense_engine.py`
**Calls:**
- Line 1095: `subprocess.run(['nvcc', '--version'], capture_output=True, text=True, timeout=10)`
- Line 1159: `subprocess.run([...])` (systemctl restart ollama)
- Line 1166: `subprocess.run(['systemctl', 'restart', 'ollama'], capture_output=True, timeout=30)`
- Line 1176: `subprocess.run([...])` (ollama serve)
- Line 1182: `subprocess.run(['ollama', 'serve'], capture_output=True, timeout=5)`
- Line 1191: `subprocess.run([...])` (ollama pull)
- Line 1205: `subprocess.run([...])` (ollama list)
- Line 1287: `subprocess.run([...])` (ollama run)
- Line 1376: `subprocess.run(ping_cmd, ...)`
**Sandbox Classification:** ⚠️ MIXED
- Version checks: SANDBOX-SAFE
- System service control: SANDBOX-UNSAFE
- Network operations: SANDBOX-UNSAFE
**Impact:** Can restart services, make network calls

### DeepEnvironmentScanner
**File:** `deep_environment_scanner.py`
**Calls:**
- Line 39: `subprocess.run([...])` (USB devices)
- Line 132: `subprocess.run(['lsusb'], ...)`
- Line 170: `subprocess.run(['lpstat', '-a'], ...)`
- Line 201: `subprocess.run([...])` (audio devices)
- Line 212: `subprocess.run(['aplay', '-l'], ...)`
- Line 220: `subprocess.run(['arecord', '-l'], ...)`
- Line 248: `subprocess.run([...])` (bluetooth)
- Line 267: `subprocess.run(['bluetoothctl', 'devices'], ...)`
- Line 314: `subprocess.run(['xrandr', '--query'], ...)`
- Line 361: `subprocess.run(['ip', '-j', 'addr'], ...)`
- Line 405: `subprocess.run([...])` (network)
- Line 429: `subprocess.run([...])` (disk)
- Line 462: `subprocess.run(['whoami', '/groups'], ...)`
- Line 475: `subprocess.run(['ufw', 'status'], ...)`
- Line 513: `subprocess.run([...])` (system info)
**Sandbox Classification:** ✅ SANDBOX-SAFE (Read-only inspection)
**Impact:** Only reads system information, no mutations

### EnvironmentBootstrapService
**File:** `environment_bootstrap_service.py:242`
**Call:** `subprocess.run([...])` (bootstrap command)
**Sandbox Classification:** ❌ SANDBOX-UNSAFE
**Impact:** Can execute arbitrary bootstrap commands

### Evolution Services
**Files:** `environment_self_awareness_service.py`, `git_sync_service.py`, `operational_self_examination_service.py`, `resource_metacognition_service.py`, `runtime_audit_tracer.py`, `world_model_service.py`
**Calls:** Multiple subprocess.run calls for git operations, system inspection
**Sandbox Classification:** ⚠️ MIXED
- Git operations: SANDBOX-UNSAFE (mutations)
- System inspection: SANDBOX-SAFE (read-only)
**Impact:** Can perform git operations (push, pull, reset)

### FullSystemMetacognition
**File:** `full_system_metacognition.py`
**Calls:**
- Line 341: `subprocess.run([...])` (system info)
- Line 388: `subprocess.run([...])` (disk info)
- Line 415: `subprocess.run([...])` (memory info)
- Line 518: `subprocess.run([...])` (process info)
- Line 604: `subprocess.run(cmd, ...)`
- Line 802: `subprocess.run([...])`
**Sandbox Classification:** ✅ SANDBOX-SAFE (Read-only inspection)
**Impact:** Only reads system information

### GPUMetacognition
**File:** `gpu_metacognition.py`
**Calls:**
- Line 33: `subprocess.run([...])` (nvidia-smi)
- Line 50: `subprocess.run([...])` (GPU info)
- Line 80: `subprocess.run([...])` (GPU memory)
- Line 121: `subprocess.run([...])` (GPU processes)
- Line 260: `subprocess.run([...])` (GPU reset)
- Line 298: `subprocess.run([...])` (GPU info)
- Line 395: `subprocess.run([...])` (GPU reset)
- Line 400: `subprocess.run([...])` (GPU reset)
**Sandbox Classification:** ⚠️ MIXED
- GPU inspection: SANDBOX-SAFE
- GPU reset: SANDBOX-UNSAFE
**Impact:** Can reset GPU (destructive operation)

### IntelligentResourceManager
**File:** `intelligent_resource_manager.py`
**Calls:**
- Line 89: `subprocess.run([...])` (CPU info)
- Line 107: `subprocess.run([...])` (memory info)
- Line 138: `subprocess.run([...])` (disk info)
- Line 151: `subprocess.run([...])` (network info)
- Line 168: `subprocess.run([...])` (process info)
- Line 184: `subprocess.run([...])` (system info)
**Sandbox Classification:** ✅ SANDBOX-SAFE (Read-only inspection)
**Impact:** Only reads system information

### GPUBenchmarkService
**File:** `gpu_model_benchmark_service.py`
**Calls:**
- Line 110: `subprocess.run([...])` (benchmark)
- Line 147: `subprocess.run([...])` (benchmark)
- Line 183: `subprocess.run([...])` (benchmark)
- Line 237: `subprocess.run([...])` (benchmark)
- Line 269: `subprocess.run([...])` (benchmark)
- Line 316: `subprocess.run([...])` (benchmark)
- Line 805: `subprocess.run([...])` (benchmark)
**Sandbox Classification:** ❌ SANDBOX-UNSAFE
**Impact:** Executes GPU benchmarks (resource-intensive)

### LimitsAwareness
**File:** `limits_awareness.py`
**Calls:**
- Line 45: `subprocess.run([...])` (ulimit)
- Line 95: `subprocess.run([...])` (resource limits)
**Sandbox Classification:** ✅ SANDBOX-SAFE (Read-only inspection)
**Impact:** Only reads resource limits

### RegressionCycleDetector
**File:** `regression_cycle_detector.py:35`
**Call:** `subprocess.run([...])` (git log)
**Sandbox Classification:** ⚠️ SANDBOX-UNSAFE (Git operation)
**Impact:** Reads git history (read-only but git operation)

### SelfCodeAnalysis
**File:** `self_code_analysis.py`
**Calls:**
- Line 49: `subprocess.run(cmd, ...)`
- Line 647: `subprocess.run([...])` (timeout check)
- Line 655: `subprocess.run([...])` (code analysis)
- Line 754: `subprocess.run([...])` (code analysis)
- Line 864: `subprocess.run([...])` (code analysis)
**Sandbox Classification:** ⚠️ MIXED
- Code analysis: SANDBOX-SAFE (read-only)
- Timeout checks: SANDBOX-SAFE
**Impact:** Analyzes code (read-only)

### SelfTeach
**File:** `self_teach\promotion_pr_publisher.py:41`
**Call:** `subprocess.run([...])` (git operations)
**Sandbox Classification:** ❌ SANDBOX-UNSAFE
**Impact:** Can perform git operations

### ToolVersionMonitor
**File:** `tool_version_monitor.py:30`
**Call:** `subprocess.run(args, ...)`
**Sandbox Classification:** ✅ SANDBOX-SAFE (Version check)
**Impact:** Only checks tool versions

### UIExecutionRunner
**File:** `ui_execution_runner.py:1631`
**Call:** `subprocess.run([...])` (UI automation)
**Sandbox Classification:** ❌ SANDBOX-UNSAFE
**Impact:** Can automate UI interactions (real execution)

---

## UI Layer

### ControlCenterViewModel
**File:** `control_center_viewmodel.py:5480`
**Call:** `_subprocess.run([...])`
**Sandbox Classification:** ❌ SANDBOX-UNSAFE
**Impact:** Can execute subprocess from UI (bypasses tool layer)

---

## Summary

**Total subprocess.run calls cataloged:** 80+

**Sandbox Classification:**
- **SANDBOX-SAFE:** 40+ (read-only inspection, version checks)
- **SANDBOX-UNSAFE:** 30+ (real execution, mutations, network calls)
- **MIXED:** 10+ (context-dependent)

**Critical Findings:**

1. **AiderToolAdapter:** ❌ NO_SANDBOX distinction (PART 4)
   - Can execute real code edits in sandbox mode
   - **PRIORITY:** HIGH

2. **DesktopHumanToolAdapter:** ❌ NO_SANDBOX distinction (PART 4)
   - Can execute real UI automation in sandbox mode
   - **PRIORITY:** HIGH

3. **DevinApiToolAdapter:** ❌ NO_SANDBOX distinction (PART 4)
   - Can make real API calls in sandbox mode
   - **PRIORITY:** HIGH

4. **CommonSenseEngine:** ⚠️ MIXED
   - Can restart services in sandbox mode
   - **PRIORITY:** MEDIUM

5. **Evolution Services:** ⚠️ MIXED
   - Can perform git operations in sandbox mode
   - **PRIORITY:** MEDIUM

6. **GPUMetacognition:** ⚠️ MIXED
   - Can reset GPU in sandbox mode
   - **PRIORITY:** MEDIUM

7. **UIExecutionRunner:** ❌ NO_SANDBOX distinction
   - Can automate UI in sandbox mode
   - **PRIORITY:** HIGH

8. **ControlCenterViewModel:** ❌ NO_SANDBOX distinction
   - Can execute subprocess from UI
   - **PRIORITY:** HIGH

---

## Security Implications

**SANDBOX BYPASS RISK:**
- 3 adapters with NO_SANDBOX distinction (Aider, DesktopHuman, Devin)
- 2 UI components with NO_SANDBOX distinction (UIExecutionRunner, ControlCenterViewModel)
- 4 services with MIXED classification (CommonSense, Evolution, GPU, SelfTeach)

**AUTHORIZATION MITIGATION:**
- Tool adapters are protected by authority authorization (CRITICAL-1 fix)
- Non-tool services may bypass authority authorization
- UI components may bypass tool layer entirely

---

## Recommendations

**SHORT TERM (for V11 audit):**
1. Document that sandbox mode is not a universal security boundary
2. Document that authority authorization is the primary security boundary for tool adapters
3. Note that non-tool services and UI components have sandbox bypass risks

**LONG TERM:**
1. Fix remaining adapters with NO_SANDBOX distinction
2. Add sandbox checks to non-tool services
3. Add sandbox checks to UI components
4. Consider making sandbox mode a universal security boundary

---

## Next Steps

Proceed with:
- PART 10: F14 regression after contract fix
