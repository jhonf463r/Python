# ToolAdapter Sandbox Semantics Audit - PART 4

**Date:** 2026-08-23  
**Task:** PART 4 — Audit ToolAdapter Base Contract and Sandbox Semantics

---

## Base Contract

**ToolAdapter.run() signature:**
```python
def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]
```

**Sandbox Parameter:** `sandbox: bool = False`

**Intended Semantics:**
- `sandbox=True`: Isolated simulation, no real side effects
- `sandbox=False`: Real execution with capability authorization

---

## Adapter Classification

### ShellToolAdapter
**Status:** ✅ FIXED (PART 5)
**Classification:** TRUE_SANDBOX
**Behavior:**
- `sandbox=True`: Returns simulated result, NO subprocess execution
- `sandbox=False`: Executes real subprocess
**Security:** ✅ CORRECT

### LocalCliToolAdapter
**Status:** ✅ FIXED (PART 6)
**Classification:** TRUE_SANDBOX
**Behavior:**
- `sandbox=True`: Returns simulated result, NO subprocess execution
- `sandbox=False`: Executes real subprocess
**Security:** ✅ CORRECT

### MCPToolAdapter
**Status:** ⚠️ PARTIAL_SANDBOX
**Classification:** PARTIAL_SANDBOX
**Behavior:**
- `sandbox=True`: Sends 'initialize' probe to MCP server (network call)
- `sandbox=False`: Sends real tool execution to MCP server
**Security:** ⚠️ NETWORK CALL IN SANDBOX MODE
**Recommendation:** Consider rejecting sandbox mode for MCP adapter or making it truly isolated

### OllamaToolAdapter
**Status:** ⚠️ PARTIAL_SANDBOX
**Classification:** PARTIAL_SANDBOX
**Behavior:**
- `sandbox=True`: Calls LLM provider (network/local subprocess)
- `sandbox=False`: Calls LLM provider (network/local subprocess)
**Security:** ⚠️ NO SANDBOX DISTINCTION
**Recommendation:** Add sandbox distinction or reject sandbox mode

### GitHubApiToolAdapter
**Status:** ✅ TRUE_SANDBOX
**Classification:** TRUE_SANDBOX
**Behavior:**
- `sandbox=True`: Returns dry-run results, NO network calls
- `sandbox=False`: Makes real GitHub API calls
**Security:** ✅ CORRECT

### AiderToolAdapter
**Status:** ⚠️ NO_SANDBOX
**Classification:** NO_SANDBOX
**Behavior:**
- `sandbox=True`: Executes aider subprocess (REAL EXECUTION)
- `sandbox=False`: Executes aider subprocess (REAL EXECUTION)
**Security:** ❌ CRITICAL BYPASS
**Recommendation:** FIX REQUIRED - Add sandbox check

### PlaywrightToolAdapter (via ExternalAssistantToolAdapter)
**Status:** ⚠️ PARTIAL_SANDBOX
**Classification:** PARTIAL_SANDBOX
**Behavior:**
- `sandbox=True`: Returns early, but may have side effects from super().run()
- `sandbox=False`: Full execution with telemetry
**Security:** ⚠️ NEEDS REVIEW
**Recommendation:** Verify sandbox isolation

### DesktopHumanToolAdapter
**Status:** ⚠️ NO_SANDBOX
**Classification:** NO_SANDBOX
**Behavior:**
- `sandbox=True`: Delegates to UIExecutionRunner (REAL EXECUTION)
- `sandbox=False`: Delegates to UIExecutionRunner (REAL EXECUTION)
**Security:** ❌ CRITICAL BYPASS
**Recommendation:** FIX REQUIRED - Add sandbox check

### DevinApiToolAdapter
**Status:** ⚠️ NO_SANDBOX
**Classification:** NO_SANDBOX
**Behavior:**
- `sandbox=True`: Makes real API calls to Devin (REAL EXECUTION)
- `sandbox=False`: Makes real API calls to Devin (REAL EXECUTION)
**Security:** ❌ CRITICAL BYPASS
**Recommendation:** FIX REQUIRED - Add sandbox check

---

## Summary

**Total Adapters Audited:** 9

**TRUE_SANDBOX (Correct):** 3
- ShellToolAdapter ✅
- LocalCliToolAdapter ✅
- GitHubApiToolAdapter ✅

**PARTIAL_SANDBOX (Needs Review):** 3
- MCPToolAdapter ⚠️ (network call in sandbox)
- OllamaToolAdapter ⚠️ (no sandbox distinction)
- PlaywrightToolAdapter ⚠️ (needs review)

**NO_SANDBOX (Critical Bypass):** 3
- AiderToolAdapter ❌
- DesktopHumanToolAdapter ❌
- DevinApiToolAdapter ❌

---

## Critical Findings

**CRITICAL:** 3 adapters execute real subprocesses/network calls in sandbox mode:
1. AiderToolAdapter
2. DesktopHumanToolAdapter
3. DevinApiToolAdapter

These adapters must be fixed to either:
- Reject sandbox mode (raise error)
- Implement true sandbox simulation

---

## Recommendations

1. **Fix AiderToolAdapter**: Add sandbox check before subprocess execution
2. **Fix DesktopHumanToolAdapter**: Add sandbox check before UIExecutionRunner
3. **Fix DevinApiToolAdapter**: Add sandbox check before API calls
4. **Review MCPToolAdapter**: Consider rejecting sandbox mode or making it truly isolated
5. **Review OllamaToolAdapter**: Add sandbox distinction or reject sandbox mode
6. **Review PlaywrightToolAdapter**: Verify sandbox isolation

---

## Next Steps

Proceed with:
- PART 7: Audit tool_registry.py and adapter reachability
- PART 8: Trace TOOL_SANDBOX provenance
- PART 9: Repeat exhaustive side-effect inventory with sandbox classification
