# IABV v1.5 Duplicated Responsibilities Report
**Date:** 2026-09-02
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## Duplicated Responsibilities

### 1. Resource Governance

**DUPLICATION:** Resource admission logic
**LOCATION A:** `bootstrap.py` - Patch A deferred metacognition admission (lines 1933-2064)
**LOCATION B:** `bootstrap.py` - ARO prebuild admission (lines 3963-4202) + `intelligent_resource_manager.py` - AdaptiveResourceOrchestrator
**SEMANTIC OVERLAP:** Both locations implement resource/stall admission using `take_resource_snapshot()`
**RISK:** HIGH - Inconsistent admission policies, maintenance burden, potential for conflicting decisions
**WHICH ONE APPEARS CANONICAL:** AdaptiveResourceOrchestrator (centralized resource governance)
**EVIDENCE:** OBSERVED

**Details:**
- Patch A adds inline resource checks in `_bg_metacognition` and `_deferred_auto_install_missing_tools`
- ARO provides centralized `should_run_task()` method for admission decisions
- Both use `take_resource_snapshot()` but implement different policy logic
- Patch A uses fail-open semantics on exception
- ARO policy engine not reused by Patch A

### 2. Tool Selection Logic

**DUPLICATION:** Tool selection and routing
**LOCATION A:** `ToolRegistry` - Central tool registration and lookup
**LOCATION B:** `InteractionModeSelector` - Mode-based tool selection
**LOCATION C:** `AdaptiveTaskOrchestrator` - Task-specific tool selection
**SEMANTIC OVERLAP:** Multiple paths for selecting tools based on context
**RISK:** MEDIUM - Potential for inconsistent tool selection
**WHICH ONE APPEARS CANONICAL:** ToolRegistry (central registration)
**EVIDENCE:** PARTIAL

**Details:**
- ToolRegistry maintains tool availability and capabilities
- InteractionModeSelector selects tools based on interaction mode
- AdaptiveTaskOrchestrator may select tools based on task requirements
- No clear single source of truth for tool selection decisions

### 3. Learning / Experience Storage

**DUPLICATION:** Experience persistence
**LOCATION A:** `AdaptiveProtocolService` - Rule learning via `rules.json`
**LOCATION B:** ExperienceStorageService (if exists) - General experience storage
**LOCATION C:** Repository services (ObjectiveRepository, EpisodeRepository, etc.) - Domain-specific persistence
**SEMANTIC OVERLAP:** Multiple mechanisms for storing learned behavior
**RISK:** MEDIUM - Fragmented learning, inconsistent experience retrieval
**WHICH ONE APPEARS CANONICAL:** Repository services (structured persistence)
**EVIDENCE:** PARTIAL

**Details:**
- AdaptiveProtocolService stores adaptive rules separately
- Repository services store structured domain data
- No unified experience retrieval mechanism
- Potential for learning to be siloed in different stores

### 4. Resource Monitoring

**DUPLICATION:** Resource pressure classification
**LOCATION A:** `intelligent_resource_manager.py` - `take_resource_snapshot()`
**LOCATION B:** `ResourceMetacognitionService` - Resource observation
**LOCATION C:** `AdaptiveResourceOrchestrator` - Resource-based admission
**SEMANTIC OVERLAP:** Multiple components classify resource pressure
**RISK:** LOW - Consistent snapshot usage, but multiple classification points
**WHICH ONE APPEARS CANONICAL:** `take_resource_snapshot()` (central snapshot function)
**EVIDENCE:** OBSERVED

**Details:**
- All components use `take_resource_snapshot()` as source
- Classification logic may be duplicated
- Consistent pressure thresholds (critical, high, moderate, low)

### 5. Task Context Assembly

**DUPLICATION:** Context assembly
**LOCATION A:** `TaskContextAssembler` - Explicit context assembly service
**LOCATION B:** `AdaptiveTaskOrchestrator` - Inline context assembly
**LOCATION C:** `WorldModelService` - Environment context
**SEMANTIC OVERLAP:** Multiple paths for assembling task context
**RISK:** MEDIUM - Inconsistent context, missing context elements
**WHICH ONE APPEARS CANONICAL:** TaskContextAssembler (explicit service)
**EVIDENCE:** PARTIAL

**Details:**
- TaskContextAssembler provides explicit context assembly
- AdaptiveTaskOrchestrator may assemble context inline
- WorldModelService provides environment context
- No clear single source of truth for complete task context

## No Duplicate Architecture Found

**Second Monitor/Scheduler/Watchdog:** NOT FOUND
**UniversalStabilityGovernor:** NOT_FOUND
**Additional orchestrators beyond ATO and ARO:** NOT_FOUND
**Parallel memory systems:** NOT_FOUND (repository services appear unified)
**Duplicate runtime identity logic:** NOT_FOUND

## Summary

**TOTAL DUPLICATIONS FOUND:** 5
**HIGH RISK:** 1 (resource governance)
**MEDIUM RISK:** 3 (tool selection, experience storage, context assembly)
**LOW RISK:** 1 (resource monitoring)

**CRITICAL ISSUE:** Resource governance duplication is the highest risk. Patch A implements resource admission separately from ARO, creating two parallel admission paths with potentially inconsistent policies.
