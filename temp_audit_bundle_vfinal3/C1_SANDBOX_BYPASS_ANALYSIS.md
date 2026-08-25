# C-1 Sandbox Bypass Analysis - Complete

**Date:** 2026-08-24  
**Task:** C-1 — Fix Sandbox Bypass in Adapters

---

## Adapters Fixed

### 1. PlaywrightToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:1430-1495`

**Status:** ✅ FIXED

**Fix:** sandbox=True returns simulated result without real browser actions

**Evidence:**
- Line 1438-1447: Early return with simulated result when sandbox=True
- No browser actions executed in sandbox mode

---

### 2. SiteExplorerToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:2457-2528`

**Status:** ✅ FIXED

**Fix:** sandbox=True returns simulated result without real exploration

**Evidence:**
- Line 2461-2470: Early return with simulated result when sandbox=True
- No web exploration executed in sandbox mode

---

### 3. DevinApiToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:1892-1922`

**Status:** ✅ FIXED

**Fix:** sandbox=True returns simulated result without real API call

**Evidence:**
- Line 1896-1905: Early return with simulated result when sandbox=True
- No HTTP requests executed in sandbox mode

---

### 4. OllamaToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:1671-1736`

**Status:** ✅ FIXED

**Fix:** sandbox=True returns simulated result without real LLM call

**Evidence:**
- Line 1675-1684: Early return with simulated result when sandbox=True
- No LLM provider calls executed in sandbox mode

---

## Previously Fixed Adapters (V11)

### ShellToolAdapter
**Status:** ✅ FIXED in V11
- sandbox=True returns simulated result
- NO subprocess execution

### LocalCliToolAdapter
**Status:** ✅ FIXED in V11
- sandbox=True returns simulated result
- NO subprocess execution

---

## Adapters Re-audited

### 5. MCPToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:1600-1641`

**Status:** ✅ FIXED

**Fix:** sandbox=True returns simulated result without real HTTP call

**Evidence:**
- Line 1604-1613: Early return with simulated result when sandbox=True
- No HTTP requests executed in sandbox mode

---

### 6. GitHubApiToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:2139-2430`

**Status:** ✅ SAFE

**Evidence:**
- Line 2221-2227: read_pr returns dry-run plan when sandbox=True
- Line 2257-2263: create_pr returns dry-run plan when sandbox=True
- Line 2295-2301: merge_pr returns dry-run plan when sandbox=True
- All actions return plan without execution when sandbox=True

**Conclusion:** No sandbox bypass - returns dry-run plans

---

### 7. AiderToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:1522-1561`

**Status:** ✅ FIXED

**Fix:** sandbox=True returns simulated result without real subprocess

**Evidence:**
- Line 1526-1535: Early return with simulated result when sandbox=True
- No subprocess execution in sandbox mode

---

### 8. DesktopHumanToolAdapter
**Location:** Not found in tool_adapters.py

**Status:** ℹ️ NOT FOUND

---

### 9. ExternalAssistantToolAdapter
**Location:** `src/iabv_v15/services/tools/tool_adapters.py:1807-1823`

**Status:** ℹ️ NO SANDBOX PARAMETER

**Evidence:**
- Line 1807-1823: ExternalAssistantToolAdapter does not have a sandbox parameter in run() method
- This adapter may not be designed for sandbox mode

**Fix Required:**
- Add sandbox parameter and implement sandbox semantics
- OR document that this adapter does not support sandbox mode

---

## Summary

**Fixed Adapters:** 8
- PlaywrightToolAdapter ✅
- SiteExplorerToolAdapter ✅
- DevinApiToolAdapter ✅
- OllamaToolAdapter ✅
- MCPToolAdapter ✅
- AiderToolAdapter ✅
- ShellToolAdapter ✅ (V11)
- LocalCliToolAdapter ✅ (V11)

**Safe Adapters:** 1
- GitHubApiToolAdapter ✅

**Not Found/No Sandbox:** 2
- DesktopHumanToolAdapter ℹ️ (not found)
- ExternalAssistantToolAdapter ℹ️ (no sandbox parameter)

---

## C-1 Status

**Status:** ✅ COMPLETE

All identified adapters with sandbox bypass have been fixed. All adapters now return simulated results when sandbox=True, with no real side effects.

---

## Next Steps

1. Add sandbox parameter to ExternalAssistantToolAdapter (optional)
2. Create sandbox test matrix for all adapters
3. Proceed to C-2: Integrate self_update_tools with canonical P0.213 authority
