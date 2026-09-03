# IABV v1.5 Contract Map
**Date:** 2026-09-02
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## Evidence Labels

- **CLAIMED:** Documented but not verified
- **OBSERVED:** Code exists but behavior not verified
- **REPRODUCED:** Behavior reproduced in test
- **VERIFIED:** Behavior verified in production
- **PARTIAL:** Partially verified
- **NOT_VERIFIED:** Not verified
- **UNKNOWN:** Unknown status
- **STALE:** Evidence is outdated
- **CONTRADICTED:** Evidence contradicts claims

## Module Contracts

### bootstrap.py

**MODULE:** Bootstrap
**OWNER:** Core startup
**INPUT CONTRACT:** Configuration files, command-line args
**OUTPUT CONTRACT:** Initialized application, ready UI
**PERSISTENCE:** None (runtime only)
**SIDE EFFECTS:** Spawns background threads, initializes services
**RESOURCE COST:** High (initialization, tool probes, metacognition)
**THREADING EXPECTATION:** Main thread + background threads
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** Tracer, timeline
**LEARNING EFFECT:** None (runtime only)
**DEPENDENCIES:** All services
**CURRENT EVIDENCE STATUS:** OBSERVED

### AdaptiveTaskOrchestrator

**MODULE:** AdaptiveTaskOrchestrator
**OWNER:** Task orchestration
**INPUT CONTRACT:** Inference request, context
**OUTPUT CONTRACT:** Task execution result
**PERSISTENCE:** Via repositories
**SIDE EFFECTS:** Tool execution, expert calls
**RESOURCE COST:** High (cognitive work, external calls)
**THREADING EXPECTATION:** Synchronous (may spawn workers)
**AUTHORITY REQUIREMENT:** AutonomyGovernancePolicy
**OBSERVATION REQUIREMENT:** TaskOutcomeRecorder
**LEARNING EFFECT:** Updates experience
**DEPENDENCIES:** GoalEngine, IntentUnderstandingService, TaskContextAssembler
**CURRENT EVIDENCE STATUS:** OBSERVED

### AdaptiveResourceOrchestrator (ARO)

**MODULE:** AdaptiveResourceOrchestrator
**OWNER:** Resource governance
**INPUT CONTRACT:** Task metadata, resource snapshot
**OUTPUT CONTRACT:** should_run_task decision
**PERSISTENCE:** None (runtime only)
**SIDE EFFECTS:** PowerShell subprocess calls (blocking)
**RESOURCE COST:** Medium (resource probing)
**THREADING EXPECTATION:** Synchronous (blocking subprocess)
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** None
**DEPENDENCIES:** intelligent_resource_manager
**CURRENT EVIDENCE STATUS:** OBSERVED

### GoalEngine

**MODULE:** GoalEngine
**OWNER:** Goal management
**INPUT CONTRACT:** User request, session context
**OUTPUT CONTRACT:** Goal context, subtasks
**PERSISTENCE:** ObjectiveRepository
**SIDE EFFECTS:** Updates objectives
**RESOURCE COST:** Low
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** Updates from outcomes
**DEPENDENCIES:** ObjectiveRepository
**CURRENT EVIDENCE STATUS:** OBSERVED

### AdaptiveProtocolService

**MODULE:** AdaptiveProtocolService
**OWNER:** Adaptive learning
**INPUT CONTRACT:** old_rule, observation, actual_result, new_rule, rule_key
**OUTPUT CONTRACT:** ProtocolRecommendation
**PERSISTENCE:** rules.json (evolution/adaptive_protocol/)
**SIDE EFFECTS:** Persists rules, updates experience storage
**RESOURCE COST:** Low
**THREADING EXPECTATION:** Synchronous (thread-locked)
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** ExperienceStorageService
**LEARNING EFFECT:** Updates confidence based on outcomes
**DEPENDENCIES:** ExperienceStorageService (optional)
**CURRENT EVIDENCE STATUS:** OBSERVED
**KNOWN DEFECT:** Line 289 has typo `" rule_key"` causing deserialization failure

### CognitiveMetabolicTick

**MODULE:** CognitiveMetabolicTick
**OWNER:** Cognitive work bounding
**INPUT CONTRACT:** Work item, timeout
**OUTPUT CONTRACT:** Work result or timeout
**PERSISTENCE:** None (runtime only)
**SIDE EFFECTS:** Spawns workers, may cancel work
**RESOURCE COST:** Medium (thread pool)
**THREADING EXPECTATION:** ThreadPoolExecutor
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** None
**DEPENDENCIES:** None
**CURRENT EVIDENCE STATUS:** OBSERVED

### AgentHandoffTrail

**MODULE:** AgentHandoffTrail
**OWNER:** AI handoff tracking
**INPUT CONTRACT:** Handoff events
**OUTPUT CONTRACT:** Handoff history
**PERSISTENCE:** Via repositories
**SIDE EFFECTS:** Records handoffs
**RESOURCE COST:** Low
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** None
**DEPENDENCIES:** Repository services
**CURRENT EVIDENCE STATUS:** OBSERVED

### WorldModelService

**MODULE:** WorldModelService
**OWNER:** Environment modeling
**INPUT CONTRACT:** Environment scan results
**OUTPUT CONTRACT:** World model state
**PERSISTENCE:** Cached state
**SIDE EFFECTS:** Updates world model
**RESOURCE COST:** High (full refresh on every prompt)
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** None
**DEPENDENCIES:** Environment scanning
**CURRENT EVIDENCE STATUS:** OBSERVED
**KNOWN ISSUE:** Full refresh on every prompt (~60s work)

### ResourceMetacognitionService

**MODULE:** ResourceMetacognitionService
**OWNER:** Resource observation
**INPUT CONTRACT:** Resource snapshots
**OUTPUT CONTRACT:** Resource pressure classification
**PERSISTENCE:** None (runtime only)
**SIDE EFFECTS:** May close processes to liberate RAM
**RESOURCE COST:** Medium
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** None
**DEPENDENCIES:** intelligent_resource_manager
**CURRENT EVIDENCE STATUS:** OBSERVED

### FreezeIncidentReporter

**MODULE:** FreezeIncidentReporter
**OWNER:** Freeze detection
**INPUT CONTRACT:** Stall events, resource snapshots
**OUTPUT CONTRACT:** Freeze diagnosis
**PERSISTENCE:** Freeze reports
**SIDE EFFECTS:** Logs freeze incidents
**RESOURCE COST:** Low
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** UIHeartbeatWatchdog
**LEARNING EFFECT:** None
**DEPENDENCIES:** UIHeartbeatWatchdog, intelligent_resource_manager
**CURRENT EVIDENCE STATUS:** OBSERVED

### ToolRegistry

**MODULE:** ToolRegistry
**OWNER:** Tool management
**INPUT CONTRACT:** Tool definitions
**OUTPUT CONTRACT:** Tool availability
**PERSISTENCE:** Tool records
**SIDE EFFECTS:** Registers tools
**RESOURCE COST:** Low
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** None
**OBSERVATION REQUIREMENT:** None
**LEARNING EFFECT:** None
**DEPENDENCIES:** ToolRecordRepository
**CURRENT EVIDENCE STATUS:** OBSERVED

### ToolTeachService

**MODULE:** ToolTeachService
**OWNER:** Tool learning
**INPUT CONTRACT:** User tool examples
**OUTPUT CONTRACT:** Learned tool adapters
**PERSISTENCE:** Tool adapters
**SIDE EFFECTS:** Generates tool code
**RESOURCE COST:** High (code generation)
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** AutonomyGovernancePolicy
**OBSERVATION REQUIREMENT:** ToolEvolutionMonitor
**LEARNING EFFECT:** Updates tool capabilities
**DEPENDENCIES:** Expert providers, repositories
**CURRENT EVIDENCE STATUS:** OBSERVED

### ControlMasterService

**MODULE:** ControlMasterService
**OWNER:** Governance layer
**INPUT CONTRACT:** StructuredNeeds, objectives, pending issues
**OUTPUT CONTRACT:** Governance decisions
**PERSISTENCE:** Decision audit
**SIDE EFFECTS:** Executes autonomous decisions
**RESOURCE COST:** Medium
**THREADING EXPECTATION:** Synchronous
**AUTHORITY REQUIREMENT:** AutonomyGovernancePolicy
**OBSERVATION REQUIREMENT:** PostActionObserver
**LEARNING EFFECT:** Updates from outcomes
**DEPENDENCIES:** All services
**CURRENT EVIDENCE STATUS:** OBSERVED
