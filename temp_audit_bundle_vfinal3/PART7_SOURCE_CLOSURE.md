# PART 7: Complete Source Closure

**Date:** 2026-08-24  
**Task:** PART 7 — Complete Source Closure (Include self_update_tools, MCP Registration)

---

## Source Closure Status

### self_update_tools.py
**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Status:** ✅ INCLUDED

**Changes Applied:**
- Added CapabilityActionBridge and ActionRequest imports
- Updated register_self_update_tools signature to accept capability_action_bridge
- Added authority checks to write_repo_file (WRITE_REPOSITORY_FILE)
- Added authority checks to apply_text_patch (APPLY_PATCH)
- Added authority checks to git_commit_and_push (GIT_COMMIT, GIT_PUSH)

**MCP Registration:** ✅ REGISTERED
- File is imported by MCP server
- Tools are registered via register_self_update_tools

---

### MCP Server Registration
**Location:** `src/iabv_v15/infra/mcp/server.py`

**Status:** ✅ UPDATED (C-2 fixed)

**Changes Applied:**
- Updated register_self_update_tools call to pass capability_action_bridge
- Line 3184: capability_action_bridge=self.capability_action_bridge

**Registration Flow:**
1. MCP server starts
2. Imports register_self_update_tools
3. Calls register_self_update_tools with capability_action_bridge
4. Self-update tools are registered with canonical authority

---

### tool_adapters.py
**Location:** `src/iabv_v15/services/tools/tool_adapters.py`

**Status:** ✅ UPDATED (C-1 fixed)

**Changes Applied:**
- PlaywrightToolAdapter: sandbox=True returns simulated result
- SiteExplorerToolAdapter: sandbox=True returns simulated result
- DevinApiToolAdapter: sandbox=True returns simulated result
- OllamaToolAdapter: sandbox=True returns simulated result
- MCPToolAdapter: sandbox=True returns simulated result
- AiderToolAdapter: sandbox=True returns simulated result

**Source Closure:** ✅ COMPLETE
- All adapters are in the same file
- All adapters are imported by tool_registry
- All adapters are registered in ToolRegistry

---

### github_remote_service.py
**Location:** `src/iabv_v15/services/tools/github_remote_service.py`

**Status:** ✅ UPDATED (H-1 fixed)

**Changes Applied:**
- Added pr_lease_id parameter to publish_branch_as_pr
- Use separate lease_id for PUSH
- Use separate pr_lease_id for CREATE_PR
- Fail closed if pr_lease_id is not provided

**Source Closure:** ✅ COMPLETE
- File is imported by evolution services
- Service is instantiated with capability_action_bridge
- Authority checks are in place

---

## Source Closure Verification

### All Modified Files
1. ✅ `src/iabv_v15/infra/mcp/self_update_tools.py` - Modified
2. ✅ `src/iabv_v15/infra/mcp/server.py` - Modified
3. ✅ `src/iabv_v15/services/tools/tool_adapters.py` - Modified
4. ✅ `src/iabv_v15/services/tools/github_remote_service.py` - Modified

### All Imported Files
1. ✅ `src/iabv_v15/services/trust/capability_action_bridge.py` - Imported
2. ✅ `src/iabv_v15/services/trust/capability_lifecycle.py` - Imported
3. ✅ `src/iabv_v15/services/trust/authority_client.py` - Imported

### All Registered Tools
1. ✅ write_repo_file - Registered via MCP
2. ✅ apply_text_patch - Registered via MCP
3. ✅ git_commit_and_push - Registered via MCP

### All Adapters
1. ✅ ShellToolAdapter - Registered in ToolRegistry
2. ✅ LocalCliToolAdapter - Registered in ToolRegistry
3. ✅ PlaywrightToolAdapter - Registered in ToolRegistry
4. ✅ SiteExplorerToolAdapter - Registered in ToolRegistry
5. ✅ DevinApiToolAdapter - Registered in ToolRegistry
6. ✅ OllamaToolAdapter - Registered in ToolRegistry
7. ✅ MCPToolAdapter - Registered in ToolRegistry
8. ✅ AiderToolAdapter - Registered in ToolRegistry
9. ✅ GitHubApiToolAdapter - Registered in ToolRegistry

---

## Source Closure Summary

**Modified Files:** 4
- self_update_tools.py
- server.py
- tool_adapters.py
- github_remote_service.py

**Imported Authority Files:** 3
- capability_action_bridge.py
- capability_lifecycle.py
- authority_client.py

**Registered Self-Update Tools:** 3
- write_repo_file
- apply_text_patch
- git_commit_and_push

**Registered Adapters:** 9
- All adapters registered in ToolRegistry

---

## PART 7 Status

**Status:** ✅ COMPLETE

All source files have been closed. All modified files are included. All imports are resolved. All tools are registered. Source closure is complete.
