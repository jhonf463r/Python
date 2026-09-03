# IABV v1.5 Architectural Damage Assessment
**Date:** 2026-09-02
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## Historical Patch Cycle Impact

### 1. Did the historical patch cycle structurally damage the architecture?

**Answer:** PARTIAL
**Evidence:** OBSERVED

**Details:**
- Resource governance duplication introduced (Patch A vs ARO)
- Adaptive protocol has critical serialization defect (line 289 typo)
- No new architectural components created (no new governors, monitors, schedulers)
- Existing architecture preserved but with inconsistencies

**Structural Damage:** PARTIAL - No structural damage, but introduced inconsistencies and defects

### 2. Which changes are architectural debt?

**Architectural Debt Items:**
1. **Resource governance duplication** - Patch A implements resource admission separately from ARO
2. **Adaptive protocol serialization defect** - Line 289 typo breaks persistence round-trip
3. **WorldModelService full refresh on every prompt** - ~60s work on every user prompt
4. **CognitiveMetabolicTick timeout not verified** - May not actually stop underlying work
5. **Four-state model not verified** - States claimed but not verified in code
6. **Verification/Adequacy gap** - No explicit verification service in self-development path

**Evidence:** OBSERVED

### 3. Which are normal incremental hardening?

**Incremental Hardening Items:**
1. **Patch A deferred metacognition admission** - Resource admission for deferred work
2. **Patch B ARO prebuild admission** - Resource admission for VM prebuild
3. **UI heartbeat watchdog** - Stall detection
4. **Freeze incident reporter** - Freeze diagnosis
5. **Repository services** - Structured persistence

**Evidence:** OBSERVED

### 4. Which modules are becoming too large?

**Large Modules:**
1. **bootstrap.py** - 5626 lines (contains startup, metacognition, ARO admission, prebuild logic)
2. **intelligent_resource_manager.py** - Contains ARO, resource snapshot, multiple responsibilities
3. **AdaptiveTaskOrchestrator** - Not audited for size, but likely large (handles inference, context, orchestration)

**Evidence:** PARTIAL

**Recommendation:** Consider splitting bootstrap.py into focused modules (startup, metacognition, ARO integration).

### 5. Which responsibilities should eventually become explicit contracts?

**Responsibilities Needing Explicit Contracts:**
1. **Resource admission** - Single canonical resource admission contract
2. **Tool selection** - Single canonical tool selection contract
3. **Context assembly** - Single canonical context assembly contract
4. **Verification** - Explicit verification service contract
5. **Adequacy assessment** - Explicit adequacy assessment contract
6. **Experience persistence** - Unified experience persistence contract

**Evidence:** OBSERVED

### 6. Which parts must NOT be refactored before first successful interaction?

**Critical Paths (Do Not Refactor):**
1. **Bootstrap startup sequence** - Phase A (tool probes) and Phase B (deferred metacognition)
2. **MainWindowBridge** - Python-QML interface
3. **Chat bridge** - Request acceptance and response return
4. **ToolRegistry** - Tool registration and lookup
5. **Repository services** - ObjectiveRepository, EpisodeRepository, etc.
6. **Expert providers** - OllamaExpertProvider (only verified provider)

**Evidence:** OBSERVED

**Reason:** These are the core paths required for first successful interaction. Refactoring them before verifying they work would introduce unnecessary risk.

### 7. What is the smallest architectural frontier remaining before IABV can interact with the user and provide useful development assistance?

**Smallest Architectural Frontier:**

**Critical Path to First Interaction:**
1. **Verification service** - Must verify results before persisting experience
2. **Adequacy assessment** - Must assess result adequacy before learning
3. **Adaptive protocol defect fix** - Must fix line 289 typo to enable persistence
4. **Resource governance unification** - Should unify Patch A and ARO admission (optional but recommended)
5. **WorldModelService caching** - Should cache world model to avoid ~60s refresh on every prompt (optional but recommended)

**Minimal Frontier for First Interaction:**
1. **Fix adaptive protocol defect** (line 289 typo) - CRITICAL
2. **Implement verification service** - CRITICAL
3. **Implement adequacy assessment** - CRITICAL

**Optional but Recommended:**
4. **Unify resource governance** - HIGH priority
5. **Cache world model** - HIGH priority

**Evidence:** OBSERVED

## Summary

**STRUCTURAL DAMAGE:** PARTIAL (no structural damage, but inconsistencies and defects)
**ARCHITECTURAL DEBT:** 6 items identified
**INCREMENTAL HARDENING:** 5 items identified
**LARGE MODULES:** 3 modules identified (bootstrap.py, intelligent_resource_manager.py, AdaptiveTaskOrchestrator)
**EXPLICIT CONTRACTS NEEDED:** 6 responsibilities identified
**DO NOT REFACTOR:** 6 critical paths identified
**SMALLEST FRONTIER:** 3 critical items (adaptive protocol fix, verification service, adequacy assessment)

**CRITICAL FINDING:** The smallest architectural frontier before IABV can interact with the user and provide useful development assistance is:
1. Fix adaptive protocol serialization defect (line 289 typo)
2. Implement verification service
3. Implement adequacy assessment

**SEVERITY:** HIGH - Without these 3 items, the system cannot reliably learn from interactions and improve its self-development capabilities.

**RECOMMENDATION:** Prioritize fixing the adaptive protocol defect and implementing verification/adequacy services before attempting first real interaction.
