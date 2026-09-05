# IABV CANONICAL STATE

**CANONICAL ENTRY POINT FOR IABV DEVELOPMENT AND AUDIT**

**Last Updated:** 2026-09-04  
**Version:** 1.5  
**Repository:** jhonf463r/Python  
**IABV Location:** IABV_v1.5/  
**Current HEAD (main):** 0087fa66  
**Capability Gap Bridge Branch:** origin/iabv-bridge/capability-gap-self-diagnosis (abc99a19)

---

## CRITICAL: READ THIS FIRST

**Every new agent (Devin, Claude, Codex, ChatGPT, or future IABV) MUST read this document before implementing anything.**

This document is the single source of truth for:
- What IABV is
- What IABV wants to become
- Where IABV is currently
- What is actually verified vs what is only implemented
- What rules must be respected
- What has been learned (including mistakes)
- What the next single action is

**DO NOT rely on conversation history. DO NOT assume main is canonical. DO NOT assume a class exists means capability is proven.**

---

## A. IDENTITY

### What is IABV?

**IABV v1.5** is an experimental cognitive system designed to evolve toward self-awareness and self-development under human governance.

**Scope:** IABV is located in `IABV_v1.5/` within the `jhonf463r/Python` monorepo. The monorepo contains other projects (e.g., `wplay/`) that are NOT part of IABV unless explicitly proven otherwise.

**Version:** 1.5

**Workspace:** `C:\Users\faber\OneDrive\Documents\GitHub\Python\IABV_v1.5`

**Source:** `src/iabv_v15/`

**Tests:** `tests/`

**Data:** `data/`

**UI:** Python + PySide6 + QML

**Philosophy:** local-first, operational observability, governed autonomy, cumulative learning, portable context

---

## B. MASTER OBJECTIVE

The ultimate direction is:

```
OBJECTIVE → PERCEIVE → MODEL STATE → ASSESS CAPABILITIES/RESOURCES 
→ SELECT → GOVERN → EXECUTE → OBSERVE → VALIDATE → EXPERIENCE 
→ LEARN → REUSE → CONTINUE
```

### Strategic Phases (G0-G7)

**G0 — TRUSTWORTHY FOUNDATION** (CURRENT PRIORITY)
- Reliable startup
- Truthful readiness declaration
- Stable interaction
- Safe operation
- Safe termination
- NO false positives
- NO hidden freezes

**G1 — REAL COGNITIVE CONTINUITY**
- Semantic continuity across sessions
- Decision consumption from recovered state
- Evidence-based state reconciliation

**G2 — NEXT-BEST-WORK**
- Capability gap detection
- Work inventory comparison
- Cognitive arbitration
- Recommendation generation

**G3 — MEASURED CAPABILITY**
- Hypthesis-driven capability testing
- Evidence-based capability claims
- Uncertainty quantification

**G4 — FIRST COGNITIVE EXPERIMENT**
- Decision-only self-diagnosis
- Self-observation → gap → recommend (NO execution)
- Human audit/approval gate

**G5 — CONTROLLED EXECUTION + LEARNING**
- Governed sandbox changes
- Runtime observation
- Objective validation
- Experience accumulation

**G6 — ASSISTED DEVELOPMENT**
- IABV recommends its own development work
- Human audits and approves
- Governed execution under independent verification

**G7 — EMERGING SELF-DEVELOPMENT**
- Bounded self-modification under governance
- Independent verification required
- Human as authority + auditor + promotion gate

**IMPORTANT:** The first inflection is NOT autonomous programming. It is IABV's ability to observe itself, recognize what it knows/doesn't know, detect a capability gap, compare options, recommend a limited action, explain why, observe the result, learn, and use that learning later.

---

## C. CURRENT VERIFIED FRONTIER

### VERIFIED (Runtime Evidence)

- **WorldModelService:** Live source of windows, focus, tools, network, processes, blocks (P1 CLOSED)
- **PortableContextService:** Generates portable context from live state + persisted learning (P3 CLOSED)
- **OperationalSelfExaminationService:** Detects patterns, risks, recommended adjustments (P4 CLOSED)
- **ExperimentLab:** Compares routes, assistants, configurations (P2 CORE CLOSED)
- **DecisionAuditTrail:** Records cloud decisions (provider, latency, confidence, result, trend)
- **Universal Continuity:** AccountInventoryEntry/AccountInventorySnapshot extended with universal fields, automatic count generation, 14 tests passing
- **Windows WorldModel:** Real windows/focus via Win32, active Codex thread via `%USERPROFILE%\.codex\state_5.sqlite` (N4 VALIDATED)

### PARTIALLY VERIFIED

- **Neuroplasticity:** Core closed (ExperimentLab, StrategySelector, AdaptiveWeightLayer influence future decisions), but full cognitive loop not runtime-verified
- **Resource Metacognition:** Evidence of observing resource pressure and deferring non-essential work, but destructive resource-liberation path identified as unsafe parallel authority
- **Lifecycle:** R51 established clearer distinction between normal/controlled termination vs crash, recent evidence of one started + one exit with zero crash, but historical freeze/shutdown problem remains distinct

### STATIC ONLY (Implementation Exists, Not Runtime Verified)

- **Capability Gap Bridge:** Exists in branch `origin/iabv-bridge/capability-gap-self-diagnosis` (abc99a19), 25 tests pass deterministically, but:
  - NOT integrated with AdaptiveTaskOrchestrator
  - NO runtime verification that freshness classification matches actual tool availability
  - NO runtime verification that capability gaps reflect real operational state
  - NO runtime verification that work candidates integrate with ControlMasterService
  - Status: COMPATIBLE_PROJECTION (not production consumer)

- **AdaptiveTaskOrchestrator:** Entry point for inference requests, but full cognitive loop (self-diagnosis endpoint) not integrated

- **ControlMasterService:** Governance layer with work queue projection, but cognitive arbitration not integrated

### HISTORICAL

- Many audit reports, architectural decisions, and historical evidence exist in root-level .md files
- These provide context but may not reflect current state
- Always prioritize live evidence over historical claims

### UNRESOLVED

- **Birth Gate:** READY declaration may occur before all conditions are met (INIT_COMPLETE + PAGE_READY + CHAT_READY + CORE_SERVICES + NO_FAILURE)
- **Stability:** Heartbeat stall, startup freeze, RAM pressure issues observed historically
- **False Success:** Inference failures/timeouts may be represented as COMPLETED
- **Self-Report Truthfulness:** Historical incident where mcp_client self-report contradicted observed state
- **Capability Gap Integration:** Bridge exists but not connected to cognitive flow
- **Decision-Only Experiment:** Not ready - needs integration with AdaptiveTaskOrchestrator

### NOT IMPLEMENTED

- Self-modification
- Autonomous code generation
- Autonomous merge
- Autonomous GitHub promotion
- Autonomous Devin orchestration
- Autonomous external-agent execution
- Automatic learning from unverified results
- Unrestricted model selection

---

## D. BIRTH / STABILITY PRIORITY

### CURRENT PRIMARY PRIORITY

**BIRTH + STABILITY + TRUTHFUL READINESS**

Before any cognitive autonomy expansion, IABV must achieve:

```
START → INIT → VERIFIED READY → STABLE INTERACTION → SAFE OPERATION → SAFE TERMINATION
```

### Birth Gate Contract

**READY MUST ONLY OCCUR WHEN:**

```
INITIALIZATION COMPLETE
+ PAGE/UI READY
+ CHAT BRIDGE READY
+ REQUIRED CORE SERVICES AVAILABLE
+ NO CRITICAL STARTUP FAILURE
```

**No alternative paths may declare READY before these conditions.**

### Historical Problems (Must NOT Repeat)

- Shell READY alone could declare readiness
- Page READY alone could declare readiness
- Deferred callbacks (QTimer.singleShot) could declare readiness
- Fallback paths could declare readiness
- Startup races could declare readiness
- Stale persisted readiness state could cause false readiness
- Chat bridge false positives based on markers alone

### Chat-First / Interaction Contract

Must verify:
- Bridge exists
- Bridge is connected
- Input arrives
- Message is processed
- System responds
- No false "operational" from timestamp alone
- Process does not freeze

**Must distinguish:**
- DIRECT_RUNTIME_EVIDENCE
- STATIC_SOURCE_EVIDENCE
- PERSISTED/STALE_STATE

### Stability Rules

- NO killing random processes to liberate memory
- NO infinite loops
- NO parallel schedulers
- NO unbounded background cognition
- NO blocking UI waiting for long work
- NO hiding failures via fallbacks
- NO premature readiness declaration
- NO confusing persisted state with live state

### Resource Safety

- RAM pressure classification: critical (<2GB), high (<4GB), moderate (<6GB), low
- CRITICAL pressure must result in DEFERRED policy
- Resource pressure ≠ permission to kill random processes
- Must distinguish OBSERVED RESOURCE STATE from PERSISTED RESOURCE STATE
- Resolve contradictions in favor of live evidence

### False Success Prevention

Must separate:
- EXECUTION STARTED
- EXECUTION FAILED
- EXECUTION ABORTED
- EXECUTION COMPLETED
- OBJECTIVE VERIFIED

**NEVER assume COMPLETED == OBJECTIVE SATISFIED**

---

## E. EVIDENCE TAXONOMY

All assertions must be classified as:

**DIRECT_RUNTIME_EVIDENCE**
- Live observation during actual execution
- Highest priority

**STATIC_SOURCE_EVIDENCE**
- Code contracts, implementation details
- Second priority

**TEST_EVIDENCE**
- Automated test results
- Third priority

**DERIVED_EVIDENCE**
- Computed from other evidence
- Fourth priority

**ENGINEERING_DESIGN**
- Architectural decisions, design documents
- Fifth priority

**HISTORICAL_EVIDENCE**
- Past observations, may be stale
- Sixth priority

**UNVERIFIED_ASSUMPTION**
- Claims without evidence
- Lowest priority

---

## F. CAPABILITY MODEL

### Capability ≠ Class Exists

A capability is only DEMONSTRATED when there is adequate evidence of:
- Implementation
- Production call site
- Runtime availability
- Validation
- Provenance
- Freshness
- Uncertainty
- Limitations

### Capability Gap Bridge State

**Branch:** `origin/iabv-bridge/capability-gap-self-diagnosis`  
**HEAD:** `abc99a19c0849126b326a1584ad2aa1d1baa5622`  
**Status:** COMPATIBLE_PROJECTION (not production consumer)

**What it does (STATICALLY):**
- Classifies freshness: FRESH/STALE/UNKNOWN with explicit reference_time
- Tracks provenance: source, timestamp (None if missing, NOT fabricated), evidence_type
- Preserves UNKNOWN: strict UNKNOWN handling (no false confidence)
- GAP vs TRUTH: MISSING only when fresh false, UNCERTAIN otherwise
- Heuristic scoring (renamed from confidence to avoid false calibration claim)
- Evidence type discipline: derived instead of fabricated runtime_evaluation
- GPU/RAM freshness discipline: stale → UNCERTAIN, not MISSING
- Decision record structure: separates decision_timestamp from evidence_timestamps
- 25 tests pass deterministically

**What it does NOT do (RUNTIME REQUIRED):**
- NOT integrated with AdaptiveTaskOrchestrator
- NO runtime verification of freshness classification vs actual tool availability
- NO runtime verification that capability gaps reflect real operational state
- NO runtime verification that work candidates integrate with ControlMasterService
- NO runtime verification that decision records are consumed correctly
- NO actual LLM endpoint integration
- NOT decision-only experiment ready

**Epistemological Corrections Made:**
- Added reference_time parameter for determinism
- Removed timestamp fallback to now (no fabricated provenance)
- Propagate existing metadata instead of fabricating
- Renamed confidence to heuristic_score (not calibrated probability)
- Applied freshness discipline to GPU/RAM (stale → UNCERTAIN, not MISSING)
- Changed ControlMaster relationship to COMPATIBLE_PROJECTION
- Separated decision timestamp from evidence timestamp
- Fixed GAP vs TRUTH: MISSING only when fresh false, UNKNOWN otherwise

---

## G. ARCHITECTURE MAP

### Key Components

**Perception & Decision**
- PerceptionSnapshot: EXISTS, WIRED, RUNTIME VERIFIED
- AdaptiveTaskOrchestrator: EXISTS, WIRED, PARTIALLY VERIFIED (entry point works, self-diagnosis not integrated)
- TaskContextAssembler: EXISTS, WIRED, RUNTIME VERIFIED
- AutonomyGovernancePolicy: EXISTS, WIRED, RUNTIME VERIFIED
- IntentUnderstandingService: EXISTS, WIRED, RUNTIME VERIFIED
- LocalRoleRouter: EXISTS, WIRED, RUNTIME VERIFIED

**Environment Models**
- EnvironmentSelfModel: EXISTS, WIRED, RUNTIME VERIFIED
- WorldModelSnapshot: EXISTS, WIRED, RUNTIME VERIFIED (P1 CLOSED)
- UniversalPerceptionSignal: EXISTS, WIRED, RUNTIME VERIFIED

**Cloud Reasoning & Audit**
- CloudReasoningPlannerService: EXISTS, WIRED, RUNTIME VERIFIED
- DecisionAuditTrail: EXISTS, WIRED, RUNTIME VERIFIED
- ApiKeyDiscoveryService: EXISTS, WIRED, RUNTIME VERIFIED

**Learning & Context**
- ExperimentLab: EXISTS, WIRED, RUNTIME VERIFIED (P2 CORE CLOSED)
- StrategySelector: EXISTS, WIRED, RUNTIME VERIFIED
- AdaptiveWeightLayer: EXISTS, WIRED, RUNTIME VERIFIED
- TaskOutcomeRecorder: EXISTS, WIRED, RUNTIME VERIFIED
- PortableContextService: EXISTS, WIRED, RUNTIME VERIFIED (P3 CLOSED)
- OperationalSelfExaminationService: EXISTS, WIRED, RUNTIME VERIFIED (P4 CLOSED)

**Governance**
- ControlMasterService: EXISTS, WIRED, PARTIALLY VERIFIED (governance layer exists, cognitive arbitration not integrated)
- GoalEngine: EXISTS, WIRED, RUNTIME VERIFIED
- ApprovalGateService: EXISTS, WIRED, RUNTIME VERIFIED
- CapabilityReadinessService: EXISTS, WIRED, RUNTIME VERIFIED

**Tools & Execution**
- ToolTeachService: EXISTS, WIRED, RUNTIME VERIFIED
- ToolRegistry: EXISTS, WIRED, RUNTIME VERIFIED
- AutonomousEvolutionService: EXISTS, WIRED, RUNTIME VERIFIED
- UIExecutionRunner: EXISTS, WIRED, RUNTIME VERIFIED

**UI**
- ControlCenterViewModel: EXISTS, WIRED, RUNTIME VERIFIED
- EvolutionCenterViewModel: EXISTS, WIRED, RUNTIME VERIFIED
- MainWindowBridge: EXISTS, WIRED, RUNTIME VERIFIED (signals: shellLoaderReady, pageLoaderReady)

**Evolution**
- CapabilityGapBridge: EXISTS (in branch), NOT WIRED, STATIC ONLY (25 tests pass, not integrated)

**Status Legend:**
- EXISTS: Code exists
- WIRED: Connected to system
- RUNTIME VERIFIED: Actually works in production
- PARTIALLY VERIFIED: Some aspects verified, others not
- STATIC ONLY: Tests pass, but not runtime-verified

---

## H. CANONICAL ARCHITECTURE RULES

### NO SECOND BRAIN
- Do NOT create another cognitive architecture parallel to AdaptiveTaskOrchestrator
- Extend existing services instead

### NO SECOND QUEUE
- Reuse ControlMasterService.current_work_queue()
- Do NOT create another work queue

### NO SECOND MEMORY
- Reuse existing memory/context/experience
- Do NOT duplicate PortableContext, ExperimentLab, or learning mechanisms

### NO PARALLEL AUTHORITY
- Do NOT create a second authority layer
- Extend existing Authority/Capability/Lease structures

### NO PARALLEL SCHEDULER
- Do NOT create another scheduler because an existing capability is incomplete
- Prove insufficiency before proposing new scheduler

### NO SPECULATIVE AUTONOMY
- Do NOT expand autonomy just because an API exists
- Require evidence and governance

### FAIL CLOSED
- Authorization/capability/lease failures must negate the action
- No silent bypasses

---

## I. LEARNING RULES

### Learning Pipeline

```
OBSERVE → CLAIM → AUDIT → COUNTEREVIDENCE → RECONCILE 
→ UPDATE KNOWLEDGE/UNCERTAINTY → NEXT ACTION → VERIFY → GENERALIZE
```

### Critical Distinctions

**VERIFIED ≠ ELIGIBLE**
- Verification does not automatically make something eligible for learning

**AUTHORIZED ≠ ACCEPTED_FOR_LEARNING**
- Authorization does not automatically accept for learning

**Do NOT allow automatic positive learning from:**
- Session created
- Response received
- Test passed
- Execution completed

**Learning requires:**
- Independent verification
- Evidence-based validation
- Governance approval

---

## J. CONTINUITY RULES

### Critical Distinctions

**PERSISTENCE ≠ SEMANTIC CONTINUITY**
- Checkpoint does NOT prove cognitive continuity
- Recovered state must actually modify next decision

**PROCESS RECOVERY ≠ DECISION CONSUMPTION**
- Process restart does NOT guarantee decision consumption
- Must verify semantic progress

**RUN_ID CHANGE ≠ SEMANTIC PROGRESS**
- New run ID does NOT equal semantic advancement
- Must verify actual learning application

---

## K. SELF-REPORT TRUTHFULNESS

### Required Distinctions

IABV must distinguish:
- LIVE OBSERVATION
- PERSISTED KNOWLEDGE
- STALE KNOWLEDGE
- INFERENCE
- UNKNOWN

### Historical Incident

Self-report about `mcp_client` contradicted observed state:
- SELF-REPORT: mcp_client unavailable
- EVIDENCE: mcp listener operational
- STATUS: CONTRADICTION / UNRESOLVED

### Required Design

When persisted state contradicts live evidence:
- IABV must recognize the contradiction
- Do NOT automatically resolve in favor of one source
- Keep contradiction explicit
- Require resolution decision

---

## L. AGENT ROLES

### DEVIN
- Implementation / correction / repository changes
- Makes code changes
- Runs tests
- Commits and pushes

### CLAUDE
- Independent broad architectural/repository audit
- Adversarial verification
- Cross-checks other agents' work

### CODEX
- Runtime/source/adversarial verification
- Tests actual behavior
- Validates claims

### CHATGPT
- Synthesis / historical reconciliation / sequencing / evidence interpretation
- Makes sense of complex histories
- Provides synthesis

### IABV (Future)
- Experimental subject and decision-maker
- Once runtime foundation is verified
- NOT currently in this role

**Do NOT exchange roles arbitrarily.**

---

## M. NEW CHAT BOOTSTRAP PROTOCOL

**Every new agent MUST:**

1. Read this document (IABV_CANONICAL_STATE.md)
2. Verify current branch
3. Verify HEAD SHA
4. Review current frontier (Section C)
5. Review unresolved (Section C)
6. Review recent evidence (Issues #454, #450)
7. Review agent role (Section L)
8. Review next single action (Section O)
9. **NOT implement before completing these steps**

---

## N. BRANCH DISCIPLINE

### Historical and Experimental Branches

- `p0213/*` - P0.213 trust implementation (multiple variants)
- `iabv-impl/*` - Implementation work (lifecycle, observability, terminality)
- `iabv-bridge/*` - Bridge work (capability-gap-self-diagnosis)
- `iabv-auto/*` - Automation work
- `codex/*` - Codex-specific fixes
- `devin/*` - Devin-specific work
- `main` - Main branch (may not be canonical for all purposes)
- `audit/*` - Audit branches

### Rule

**BRANCH ≠ CANONICAL ARCHITECTURE**
- Do NOT assume a branch is canonical just because it has more code
- Verify evidence and integration status
- Check Issues #454, #450 for current strategic direction

---

## O. CHANGE DISCIPLINE

### Every Significant Change Must Declare

**WHAT CHANGED**
- Files modified
- Lines added/removed

**WHY**
- Rationale for change
- Problem being solved

**EVIDENCE BEFORE**
- State before change
- Tests before change

**EVIDENCE AFTER**
- State after change
- Tests after change

**IMPACT**
- What components are affected
- What contracts change

**REGRESSION RISK**
- What could break
- How to verify

**WHAT REMAINS UNRESOLVED**
- What still needs work
- What couldn't be addressed

**RUNTIME VALIDATION**
- How to verify in production
- What evidence to collect

**NEXT ACTION**
- Single next step

---

## P. SECURITY / GOVERNANCE MEMORY (P0.213)

### Key Lessons

- Transport-derived identity
- No caller-controlled identity
- Exactly-once issuance vs redemption
- Canonical transaction boundary
- Inactive authority paths must prove inert
- Capability/lease/execution context
- Fail closed
- Provenance
- Secret isolation

### Current Status

- P0.213 V5 Phase 3: Implementation remains gated
- Independent Claude audit could not certify design (critical evidence blocks missing)
- Devin evidence-closure package produced to address gaps
- Next step: Independent Claude adversarial re-audit
- See Issue #450 for full details

**Do NOT mark P0.213 "closed" without evidence.**

---

## Q. HISTORICAL INCIDENTS / LESSONS NOT TO REPEAT

### False READY
- **Incident:** READY declared before page loader + chat bridge ready
- **Lesson:** READY requires ALL conditions (INIT + PAGE + CHAT + SERVICES + NO_FAILURE)
- **Invariant:** No alternative READY paths

### Startup Race
- **Incident:** Deferred callbacks declared readiness prematurely
- **Lesson:** Explicit gate conditions, no implicit readiness
- **Invariant:** All readiness signals must be explicit

### Chat Bridge False Positive
- **Incident:** Chat bridge operational based on stale marker
- **Lesson:** Distinguish live evidence from persisted state
- **Invariant:** Operational requires live verification

### Memory Pressure
- **Incident:** System killed random processes to liberate memory
- **Lesson:** Resource pressure ≠ permission for destructive action
- **Invariant:** Safe defer only, no destructive liberation

### Heartbeat/Freeze
- **Incident:** Heartbeat stall, startup freeze, UI event loop stall
- **Lesson:** Monitor heartbeat gap, detect stalls, diagnose root cause
- **Invariant:** 2s threshold, explicit stall detection

### Fabricated COMPLETED
- **Incident:** Inference failure represented as COMPLETED
- **Lesson:** Separate EXECUTION COMPLETED from OBJECTIVE VERIFIED
- **Invariant:** Never assume COMPLETED == SUCCESS

### Stale Self-Model
- **Incident:** Stale self-model contradicted live observation
- **Lesson:** Resolve contradictions in favor of live evidence
- **Invariant:** Live evidence > persisted state

### Test Count ≠ Objective Proof
- **Incident:** Many green tests claimed objective satisfaction
- **Lesson:** Test pass ≠ objective verified
- **Invariant:** Verify actual behavior, not just test coverage

### Implementation Summary ≠ Runtime Evidence
- **Incident:** Documentation claimed capability not runtime-verified
- **Lesson:** Implementation ≠ verified behavior
- **Invariant:** Require runtime evidence for capability claims

### Branch History ≠ Current Canonical Truth
- **Incident:** Historical branch assumed canonical
- **Lesson:** Branch ≠ canonical architecture
- **Invariant:** Verify evidence and integration status

### Parallel Architecture Without Proof
- **Incident:** New architecture proposed without proving insufficiency
- **Lesson:** Extend existing infrastructure first
- **Invariant:** Prove insufficiency before proposing parallel system

---

## R. CURRENT ROADMAP

### NOW
**Birth + Stability + Truthful Readiness**
- Reliable startup
- Verified READY gate
- Stable interaction
- Safe operation
- Safe termination

### NEXT
**Runtime Verification of Birth/Stability**
- Actual runtime testing
- Evidence collection
- Freeze diagnosis

### THEN
**Reliable Self-Observation**
- Capability gap detection
- State introspection
- Evidence-based claims

### THEN
**Decision-Only Self-Diagnosis**
- Integrate CapabilityGapBridge with AdaptiveTaskOrchestrator
- Self-diagnosis endpoint
- Recommendation (NO execution)

### THEN
**Next-Best-Work Recommendation**
- Cognitive arbitration
- Work inventory comparison
- Recommendation generation

### THEN
**Measured Experiment/Learning Loop**
- Sandbox changes
- Runtime observation
- Objective validation
- Experience accumulation

### THEN
**Controlled Development Assistance**
- IABV recommends development work
- Human audits and approves
- Governed execution

### LATER
**Controlled Self-Development**
- Bounded self-modification
- Independent verification
- Human as authority + auditor

---

## S. FIRST IABV INTERACTION TARGET

### Query

> "Evalúa tu estado actual. Identifica qué capacidades tienes, qué capacidades no están demostradas, cuál es tu principal capability gap y qué acción limitada recomiendas para avanzar."

### Expected Output Structure

- State considered current
- Available capabilities
- Uncertainties
- Principal capability gap
- Evidence used
- Evidence freshness
- Alternatives considered
- Recommended work
- Rationale
- What NOT recommended yet
- Uncertainty level
- Governance constraints

### Critical Constraint

**NO EXECUTION**
- This is decision-only
- OBSERVE → ASSESS → GAP → RECOMMEND
- NOT: OBSERVE → EXECUTE

---

## T. SELF-DEVELOPMENT TARGET

### Future Target (NOT IMPLEMENTED / NOT VERIFIED)

```
GAP → PROPOSAL → SANDBOX CHANGE → TEST → RUNTIME OBSERVATION 
→ OBJECTIVE VALIDATION → PROMOTE/REJECT → EXPERIENCE → REASSESS
```

### Current Status

**FUTURE TARGET — NOT IMPLEMENTED / NOT VERIFIED**

Do NOT claim self-development capability exists.

---

## U. HUMAN ROLE

### Transition Target

**CURRENT**
Human + external AIs develop IABV

**INTERMEDIATE**
IABV observes itself and recommends its own next work

**LATER**
Human audits IABV proposals

**FUTURE**
IABV performs bounded development under governance and independent verification

### Important

The goal is NOT to eliminate the human.
The goal is for the human to progress from:
- Doing every modification
→ To being AUTHORITY + AUDITOR + PROMOTION GATE

---

## V. IMPORTANT: NO FABRICATION

If you cannot verify something:
- Write `UNKNOWN`
- Write `UNRESOLVED`

**DO NOT fill gaps with:**
- Assumptions
- "Likely"
- "Probably"
- "Inferred completion"

---

## W. DOCUMENTATION INDEX

### Canonical Entry Point
- **IABV_CANONICAL_STATE.md** (this file) - PURPOSE: Single source of truth for IABV development - STATUS: CANONICAL - LAST VERIFIED: 2026-09-04

### Architecture Documentation
- **AGENTS.md** - PURPOSE: Instructions for agents - STATUS: CANONICAL - LAST VERIFIED: 2026-07-26
- **ARCHITECTURAL_DECISIONS.md** - PURPOSE: Architectural decisions - STATUS: CANONICAL - LAST VERIFIED: 2026-07-26
- **ARCHITECT_REVIEW_GUIDE.md** - PURPOSE: Architect review guide - STATUS: HISTORICAL
- **PROJECT_STATUS.md** - PURPOSE: Project status - STATUS: HISTORICAL (2026-07-26)
- **ENTRY_POINTS.md** - PURPOSE: System entry points - STATUS: CANONICAL - LAST VERIFIED: 2026-07-26
- **CURRENT_RUNTIME.md** - PURPOSE: Runtime state - STATUS: HISTORICAL (2026-07-26)
- **SYMBOL_INDEX.md** - PURPOSE: Symbol index - STATUS: HISTORICAL
- **COMPONENT_DEPENDENCY_GRAPH.md** - PURPOSE: Component dependencies - STATUS: HISTORICAL

### Audit Reports (Historical)
- **AUDITORIA_PERCEPCION_RUNTIME_UNIVERSAL_REPORTE_FINAL.md** - PURPOSE: Runtime perception audit - STATUS: HISTORICAL
- **AUDIT_METACOGNICION_PROFUNDO.md** - PURPOSE: Metacognition audit - STATUS: HISTORICAL
- **AUTONOMY_CYCLE_AUDIT.md** - PURPOSE: Autonomy cycle audit - STATUS: HISTORICAL
- **AUTONOMY_VALIDATION_REPORT.md** - PURPOSE: Autonomy validation - STATUS: HISTORICAL
- **BOOTSTRAP_VISIBILITY_REPORT.md** - PURPOSE: Bootstrap visibility - STATUS: HISTORICAL
- **BUILD_INVENTORY_SNAPSHOT_UNIVERSALIZATION_REPORT.md** - PURPOSE: Universalization report - STATUS: HISTORICAL
- **CONTROL_CENTER_VIEWMODEL_UNIVERSALIZATION_REPORT.md** - PURPOSE: ViewModel universalization - STATUS: HISTORICAL
- **PORTABLE_CONTEXT_UNIVERSALIZATION_REPORT.md** - PURPOSE: Portable context universalization - STATUS: HISTORICAL
- **RECONCILIATION_AUDIT_REPORT.md** - PURPOSE: Reconciliation audit - STATUS: HISTORICAL
- **UI_INTEGRATION_REPORT.md** - PURPOSE: UI integration - STATUS: HISTORICAL
- **UNIVERSAL_CONTINUITY_REEXPRESSED_REPORT.md** - PURPOSE: Continuity reexpression - STATUS: HISTORICAL

### Other Documentation
- **TOOLS_CANONICAL_POLICY.md** - PURPOSE: Tools policy - STATUS: HISTORICAL
- **TEST_SUMMARY.md** - PURPOSE: Test summary - STATUS: HISTORICAL
- **TECHNICAL_DEBT_REGISTRATION_REPORT.md** - PURPOSE: Technical debt - STATUS: HISTORICAL

### docs/ Directory
- **ROADMAP_ALGORITHMIC_AUDIT_PLATFORM.md** - PURPOSE: Algorithmic audit roadmap - STATUS: EXPERIMENTAL
- **mcp-bridge.md** - PURPOSE: MCP bridge documentation - STATUS: EXPERIMENTAL
- **windsurf_diagnostic_prompt.md** - PURPOSE: Windsurf diagnostics - STATUS: EXPERIMENTAL
- **windsurf_live_report_prompt.md** - PURPOSE: Windsurf reporting - STATUS: EXPERIMENTAL

---

## X. STRATEGIC ALIGNMENT

### Relation to Current Frontier

This document aligns with:
- Issue #454: MASTER OBJECTIVE - camino a la inflexión cognitiva
- Issue #450: Persistent Cognitive Knowledge + Organism Integrity Backlog
- Issue #451: Cognitive Priority Arbitration / Next-Best-Work
- Branch: origin/iabv-bridge/capability-gap-self-diagnosis (abc99a19)

### Current Strategic Layer

This work supports:
- **G0 (Birth/Stability)** - by documenting what must be verified
- **G2 (Next-Best-Work)** - by documenting Capability Gap Bridge status
- **G3 (Measured Capability)** - by defining evidence taxonomy

---

## Y. NEXT SINGLE ACTION

**Integrate capability_gap_bridge with AdaptiveTaskOrchestrator to expose a self-diagnosis endpoint that can be called by the LLM to enable the decision-only self-development experiment.**

This is the explicitly stated next action in Issue #454 (comment from 2026-09-04).

---

## Z. FINAL REMINDER

**This document is the CANONICAL ENTRY POINT.**

**Every new agent MUST read this before implementing.**

**DO NOT rely on conversation history.**

**DO NOT assume main is canonical.**

**DO NOT assume implementation equals verification.**

**When in doubt: UNKNOWN or UNRESOLVED.**
