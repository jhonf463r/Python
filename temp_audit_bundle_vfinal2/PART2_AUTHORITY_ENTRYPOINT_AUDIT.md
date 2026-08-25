# PART 2: Complete Authority Entrypoint Audit

**Date:** 2026-08-24  
**Task:** PART 2 — Complete Authority Entrypoint Audit

---

## Authority Entrypoints

### 1. ToolTeachService
**Location:** `src/iabv_v15/services/tools/tool_teach_service.py`

**Capabilities:**
- Executes tools via adapter.run()
- Manages sandbox mode
- Calls CapabilityActionBridge for authorization

**Authority:** ✅ CANONICAL P0.213
- Uses CapabilityActionBridge.authorize_action()
- Consumes leases
- Fails closed when authority unavailable

---

### 2. GitHubRemoteService
**Location:** `src/iabv_v15/services/tools/github_remote_service.py`

**Capabilities:**
- git push
- create PR

**Authority:** ✅ CANONICAL P0.213 (F17 fixed)
- Uses CapabilityActionBridge.authorize_action()
- Separate lease_ids for PUSH and CREATE_PR (H-1 fixed)
- Fails closed when authority unavailable

---

### 3. ToolRollbackManager
**Location:** `src/iabv_v15/services/tools/tool_rollback_manager.py`

**Capabilities:**
- Rollbacks tool operations
- Reverts changes

**Authority:** ✅ CANONICAL P0.213 (F15 fixed)
- Uses CapabilityActionBridge.authorize_action()
- Consumes leases

---

### 4. AutonomousEvolutionService
**Location:** `src/iabv_v15/services/evolution/autonomous_evolution_service.py`

**Capabilities:**
- Autonomous development operations
- Code modifications

**Authority:** ✅ CANONICAL P0.213 (F16 fixed)
- Uses CapabilityActionBridge.authorize_action()
- Consumes leases

---

### 5. Self-Update Tools
**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Capabilities:**
- write_repo_file
- apply_text_patch
- git_commit_and_push

**Authority:** ✅ CANONICAL P0.213 (C-2 fixed)
- Uses CapabilityActionBridge.authorize_action()
- Actions: WRITE_REPOSITORY_FILE, APPLY_PATCH, GIT_COMMIT, GIT_PUSH
- Fails closed when authority unavailable

---

### 6. MCP Server Tools
**Location:** `src/iabv_v15/infra/mcp/`

**Capabilities:**
- Various MCP-registered tools

**Authority:** ✅ CANONICAL P0.213
- MCP tools are called via ToolTeachService
- ToolTeachService provides canonical authority

---

### 7. Adapters

#### ShellToolAdapter
**Capabilities:** Shell command execution
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real subprocess execution in sandbox

#### LocalCliToolAdapter
**Capabilities:** Local CLI execution
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real subprocess execution in sandbox

#### PlaywrightToolAdapter
**Capabilities:** Browser automation
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real browser actions in sandbox

#### SiteExplorerToolAdapter
**Capabilities:** Web exploration
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real exploration in sandbox

#### DevinApiToolAdapter
**Capabilities:** Remote Devin API calls
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real API calls in sandbox

#### OllamaToolAdapter
**Capabilities:** Local LLM calls
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real LLM calls in sandbox

#### MCPToolAdapter
**Capabilities:** MCP tool calls
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real HTTP calls in sandbox

#### AiderToolAdapter
**Capabilities:** Code editing via aider
**Authority:** ✅ SANDBOX SAFE (C-1 fixed)
- sandbox=True returns simulated result
- No real subprocess execution in sandbox

#### GitHubApiToolAdapter
**Capabilities:** GitHub API calls
**Authority:** ✅ SANDBOX SAFE
- sandbox=True returns dry-run plan
- No real API calls in sandbox

---

### 8. Bootstrap Process
**Location:** `src/iabv_v15/bootstrap.py`

**Capabilities:**
- MCP subprocess startup
- Tunnel subprocess startup

**Authority:** ℹ️ INFRASTRUCTURE
- Bootstrap process, not user-initiated
- Not subject to P0.213 authority (infrastructure startup)

---

### 9. Subprocess Wrappers

#### Account Resource Scanner
**Location:** `src/iabv_v15/services/account_resource_scanner.py`
**Authority:** ✅ CANONICAL P0.213
- Called via ToolTeachService

#### Auto Correction Engine
**Location:** `src/iabv_v15/services/auto_correction_engine.py`
**Authority:** ✅ CANONICAL P0.213
- Called via ToolTeachService

#### Common Sense Engine
**Location:** `src/iabv_v15/services/common_sense_engine.py`
**Authority:** ✅ CANONICAL P0.213
- Called via ToolTeachService

#### Deep Environment Scanner
**Location:** `src/iabv_v15/services/deep_environment_scanner.py`
**Authority:** ✅ CANONICAL P0.213
- Called via ToolTeachService

#### Full System Metacognition
**Location:** `src/iabv_v15/services/full_system_metacognition.py`
**Authority:** ✅ CANONICAL P0.213
- Called via ToolTeachService

---

### 10. Repository Mutation Helpers

#### Git Sync Service
**Location:** `src/iabv_v15/services/evolution/git_sync_service.py`
**Authority:** ✅ CANONICAL P0.213
- Called via ToolTeachService

---

## Summary

**Protected Operations:** All protected operations are governed by canonical P0.213 authority.

**Bypass Paths:** 0

**Fail-Closed:** All authority checks fail closed when authority is unavailable.

**Sandbox Safety:** All adapters return simulated results when sandbox=True (C-1 fixed).

**Self-Update Authority:** Self-update tools now require canonical P0.213 authority (C-2 fixed).

**GitHub Authority:** GitHubRemoteService uses separate lease_ids for PUSH and CREATE_PR (H-1 fixed).

---

## PART 2 Status

**Status:** ✅ COMPLETE

All production services capable of changing protected resources are governed by canonical P0.213 authority. No bypass paths remain.
