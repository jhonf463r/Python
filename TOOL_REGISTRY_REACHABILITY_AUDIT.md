# Tool Registry and Adapter Reachability Audit - PART 7

**Date:** 2026-08-23  
**Task:** PART 7 — Audit tool_registry.py and Adapter Reachability

---

## Tool Registry Analysis

**File:** `src/iabv_v15/services/tools/tool_registry.py`

**Purpose:** Central registry for ToolCard definitions and adapter availability checking.

**Key Methods:**
- `pick_card_for_task()`: Selects appropriate ToolCard for a given task
- `refresh_card()`: Checks adapter availability via `adapter.is_available()`
- `_seed_defaults()`: Registers default ToolCard definitions

---

## Registered Adapters

### 1. playwright_browser
**Adapter Key:** `playwright`
**Tool Type:** `ToolType.BROWSER`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** open_url, click, type_text, extract_text, screenshot
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** HIGH - Available for web automation tasks

### 2. ollama_llm
**Adapter Key:** `ollama`
**Tool Type:** `ToolType.LLM_LOCAL`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** llm_query, summarize, classify
**Reachability:** HIGH - Default LLM provider for local inference
**Security Note:** ⚠️ OllamaToolAdapter has NO sandbox distinction (PART 4)

### 3. shell_command
**Adapter Key:** `shell`
**Tool Type:** `ToolType.SHELL`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** run_command, inspect_environment
**Reachability:** HIGH - Available for shell command execution
**Security Note:** ✅ ShellToolAdapter FIXED (PART 5)

### 4. desktop_human_runner
**Adapter Key:** `desktop_human`
**Tool Type:** `ToolType.CUSTOM`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** launch_app, focus_window, click, type_text, scroll, screenshot, wait_for_window, wait_for_change
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** HIGH - Available for desktop automation
**Security Note:** ❌ DesktopHumanToolAdapter has NO sandbox distinction (PART 4)

### 5. aider_coder
**Adapter Key:** `aider`
**Tool Type:** `ToolType.CODE_EDITOR`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** edit_code, plan_patch
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** HIGH - Available for code editing
**Security Note:** ❌ AiderToolAdapter has NO sandbox distinction (PART 4)

### 6. mcp_client
**Adapter Key:** `mcp`
**Tool Type:** `ToolType.MCP_CLIENT`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** mcp_call
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** MEDIUM - MCP server must be configured
**Security Note:** ⚠️ MCPToolAdapter has PARTIAL sandbox (network call in sandbox)

### 7. codex_installed
**Adapter Key:** `external_assistant`
**Tool Type:** `ToolType.CUSTOM`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** launch_app, llm_query, consult_external, code_assistance
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** MEDIUM - Requires Codex installation
**Security Note:** ⚠️ ExternalAssistantToolAdapter needs review

### 8. chatgpt_installed
**Adapter Key:** `external_assistant`
**Tool Type:** `ToolType.CUSTOM`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** launch_app, llm_query, consult_external, explain_issue
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** MEDIUM - Requires ChatGPT installation
**Security Note:** ⚠️ ExternalAssistantToolAdapter needs review

### 9. chatgpt_web_assisted
**Adapter Key:** `external_assistant`
**Tool Type:** `ToolType.LLM_WEB_UI`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** launch_app, llm_query, consult_external, web_assisted
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** HIGH - Web-based, no installation required
**Security Note:** ⚠️ ExternalAssistantToolAdapter needs review

### 10. claude_installed
**Adapter Key:** `external_assistant`
**Tool Type:** `ToolType.CUSTOM`
**Sandbox Support:** ✅ `supports_sandbox=True`
**Capabilities:** launch_app, llm_query, consult_external, explain_issue
**Requires Approval:** ✅ `requires_human_approval=True`
**Reachability:** MEDIUM - Requires Claude installation
**Security Note:** ⚠️ ExternalAssistantToolAdapter needs review

---

## Adapter Reachability Analysis

### HIGH Reachability (Always Available)
1. **shell_command** - ShellToolAdapter
   - ✅ FIXED (PART 5)
   - Reachable from: user tasks, autonomous evolution, external consultation
   - Security: sandbox=True now returns simulated result

2. **ollama_llm** - OllamaToolAdapter
   - ❌ NO SANDBOX DISTINCTION (PART 4)
   - Reachable from: LLM queries, reasoning tasks
   - Security: sandbox=True still calls LLM provider

3. **chatgpt_web_assisted** - ExternalAssistantToolAdapter
   - ⚠️ NEEDS REVIEW (PART 4)
   - Reachable from: web-based LLM queries
   - Security: sandbox behavior unclear

### MEDIUM Reachability (Requires Installation/Configuration)
4. **playwright_browser** - PlaywrightToolAdapter
   - ⚠️ NEEDS REVIEW (PART 4)
   - Reachable from: web automation tasks
   - Security: sandbox behavior unclear

5. **desktop_human_runner** - DesktopHumanToolAdapter
   - ❌ NO SANDBOX DISTINCTION (PART 4)
   - Reachable from: desktop automation tasks
   - Security: sandbox=True still executes real UI

6. **aider_coder** - AiderToolAdapter
   - ❌ NO SANDBOX DISTINCTION (PART 4)
   - Reachable from: code editing tasks
   - Security: sandbox=True still executes aider subprocess

7. **mcp_client** - MCPToolAdapter
   - ⚠️ PARTIAL SANDBOX (PART 4)
   - Reachable from: MCP tool calls
   - Security: sandbox=True makes network call

8. **codex_installed** - ExternalAssistantToolAdapter
   - ⚠️ NEEDS REVIEW (PART 4)
   - Reachable from: Codex consultations
   - Security: sandbox behavior unclear

9. **chatgpt_installed** - ExternalAssistantToolAdapter
   - ⚠️ NEEDS REVIEW (PART 4)
   - Reachable from: ChatGPT consultations
   - Security: sandbox behavior unclear

10. **claude_installed** - ExternalAssistantToolAdapter
    - ⚠️ NEEDS REVIEW (PART 4)
    - Reachable from: Claude consultations
    - Security: sandbox behavior unclear

---

## Critical Findings

**HIGH RISK Adapters (Reachable + No Sandbox Distinction):**
1. **ollama_llm** - OllamaToolAdapter
   - Reachable from: LLM queries
   - Issue: sandbox=True still calls LLM provider
   - Impact: Can bypass authority for LLM inference

2. **desktop_human_runner** - DesktopHumanToolAdapter
   - Reachable from: desktop automation
   - Issue: sandbox=True still executes real UI
   - Impact: Can bypass authority for desktop automation

3. **aider_coder** - AiderToolAdapter
   - Reachable from: code editing
   - Issue: sandbox=True still executes aider subprocess
   - Impact: Can bypass authority for code editing

**MEDIUM RISK Adapters (Reachable + Partial Sandbox/Needs Review):**
4. **playwright_browser** - PlaywrightToolAdapter
   - Reachable from: web automation
   - Issue: sandbox behavior unclear
   - Impact: Potential bypass for web automation

5. **mcp_client** - MCPToolAdapter
   - Reachable from: MCP tool calls
   - Issue: sandbox=True makes network call
   - Impact: Can bypass authority for MCP tools

6. **external_assistant** (codex, chatgpt, claude) - ExternalAssistantToolAdapter
   - Reachable from: external consultations
   - Issue: sandbox behavior unclear
   - Impact: Potential bypass for external consultations

---

## Security Implications

**TOOL_SANDBOX Role:**
- If TOOL_SANDBOX role reaches any of the HIGH RISK adapters, it can execute real side effects
- The `supports_sandbox=True` flag in ToolCard does NOT guarantee sandbox isolation
- The adapter implementation determines actual sandbox behavior

**User-Controlled Text Classification:**
- User can request "sandbox" mode
- System may classify task as sandbox
- If adapter doesn't respect sandbox flag, real execution occurs
- This is a CRITICAL security bypass

---

## Recommendations

1. **Fix HIGH RISK adapters:**
   - OllamaToolAdapter: Add sandbox distinction or reject sandbox mode
   - DesktopHumanToolAdapter: Add sandbox check before UIExecutionRunner
   - AiderToolAdapter: Add sandbox check before subprocess execution

2. **Review MEDIUM RISK adapters:**
   - PlaywrightToolAdapter: Verify sandbox isolation
   - MCPToolAdapter: Consider rejecting sandbox mode or making it truly isolated
   - ExternalAssistantToolAdapter: Add sandbox distinction

3. **ToolCard Metadata:**
   - The `supports_sandbox=True` flag is misleading
   - Consider adding `sandbox_isolation_level` metadata
   - Document actual sandbox behavior in ToolCard

---

## Next Steps

Proceed with:
- PART 8: Trace TOOL_SANDBOX provenance from user_goal to adapter.run
- PART 9: Repeat exhaustive side-effect inventory with sandbox classification
