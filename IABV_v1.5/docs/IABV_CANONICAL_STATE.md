# IABV CANONICAL STATE

**CANONICAL ENTRY POINT FOR IABV DEVELOPMENT AND AUDIT**

**Last Updated:** 2026-09-04  
**Last Reconciled Against Main:** 80e1c9ffbe58925754394f7bb5e8494887eeb62b (2026-09-04)  
**Version:** 1.5  
**Repository:** jhonf463r/Python  
**IABV Location:** IABV_v1.5/  
**Documentation Branch:** docs/interaction-experience-architecture  
**Documentation SHA:** e8c648bb9cd112bfe879ec89e0a4c9881cbbb0eb  
**Capability Gap Bridge Branch:** origin/iabv-bridge/capability-gap-self-diagnosis (abc99a19)

**IMPORTANT:** The SHA recorded above for main (80e1c9ff) is a reconciliation anchor, NOT a permanent current-main truth. The repository HEAD must always be independently checked.

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

**DO NOT rely on conversation history. DO NOT assume main is canonical. DO NOT assume a class exists means capability is proven. DO NOT assume this document's stored main SHA represents current repository state.**

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

## A1. CANONICAL DOCUMENT LOCATION

**Current Location:**
- Branch: `docs/interaction-experience-architecture`
- SHA: `e8c648bb9cd112bfe879ec89e0a4c9881cbbb0eb`
- Path: `IABV_v1.5/docs/IABV_CANONICAL_STATE.md`

**Verification Protocol:**
```bash
git fetch origin
git rev-parse origin/docs/interaction-experience-architecture
git checkout docs/interaction-experience-architecture
```

**Important:**
- This document currently lives in `docs/interaction-experience-architecture` and is NOT present in `main`
- "Canonical" is currently a documentation concept, not a guarantee that any checkout of `main` contains it
- If the document does not exist in your checkout, switch to the canonical branch
- Do NOT assume the checkout current branch contains the canonical version

**What to do if document is missing:**
1. Check if branch `docs/interaction-experience-architecture` exists remotely
2. Checkout that branch
3. Verify SHA matches expected value
4. If SHA differs, review changes before proceeding

**Historical Parent:**
- Previous canonical branch: `docs/canonical-state-constitution` (SHA: a3edf621b86c51dcc7bff68ad3a547734535f810)
- This branch contains the canonical state before Interaction Experience Architecture was added

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
- **Repository Hygiene:** Remote main branch contains `__pycache__` and possibly `.vendor_*` artifacts (REPOSITORY HYGIENE / UNRESOLVED)

### NOT IMPLEMENTED

- Self-modification
- Autonomous code generation
- Autonomous merge
- Autonomous GitHub promotion
- Autonomous Devin orchestration
- Autonomous external-agent execution
- Automatic learning from unverified results
- Unrestricted model selection

### DELTA ANALYSIS (0087fa66 → 80e1c9ff)

**Files Added/Modified:** ~40 files including:
- Historical documentation in `docs/history/` (30+ conversation archaeology files)
- `organism_state_snapshot.py` - organism state snapshot service
- `agent_handoff_trail.py` - agent handoff tracking
- `reproducibility_validation_service.py` - reproducibility validation
- Environment self-awareness service modifications
- Deletions: `active_perception.py`, `environment_baseline.py`, `resource_guard.py`, lesson retrieval services

**Classification:**
- HISTORICAL: Documentation archaeology files (CHAT-ARCH-2026-*) - preserve as context, not frontier
- RELEVANT TO FRONTIER: organism_state_snapshot, agent_handoff_trail, reproducibility_validation - NEW SERVICES, NOT YET RUNTIME VERIFIED
- NO IMPACT: Historical conversation records, P0.213 reconciliation documentation

**Frontier Impact:**
- New services exist but are NOT runtime verified
- No change to G0 (Birth/Stability) priority
- No change to Capability Gap Bridge status (still COMPATIBLE_PROJECTION, not integrated)
- No change to decision-only experiment readiness

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
- PerceptionSnapshot: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- AdaptiveTaskOrchestrator: EXISTS, WIRED, PARTIALLY VERIFIED (entry point works, self-diagnosis not integrated)
- TaskContextAssembler: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- AutonomyGovernancePolicy: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- IntentUnderstandingService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- LocalRoleRouter: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)

**Environment Models**
- EnvironmentSelfModel: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- WorldModelSnapshot: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, P1 CLOSED per AGENTS.md but no runtime artifact reference)
- UniversalPerceptionSignal: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)

**Cloud Reasoning & Audit**
- CloudReasoningPlannerService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- DecisionAuditTrail: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- ApiKeyDiscoveryService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)

**Learning & Context**
- ExperimentLab: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, P2 CORE CLOSED per AGENTS.md but no runtime artifact reference)
- StrategySelector: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- AdaptiveWeightLayer: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- TaskOutcomeRecorder: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- PortableContextService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, P3 CLOSED per AGENTS.md but no runtime artifact reference)
- OperationalSelfExaminationService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, P4 CLOSED per AGENTS.md but no runtime artifact reference)

**Governance**
- ControlMasterService: EXISTS, WIRED, PARTIALLY VERIFIED (governance layer exists, cognitive arbitration not integrated)
- GoalEngine: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- ApprovalGateService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- CapabilityReadinessService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)

**Tools & Execution**
- ToolTeachService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- ToolRegistry: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- AutonomousEvolutionService: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- UIExecutionRunner: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)

**UI**
- ControlCenterViewModel: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- EvolutionCenterViewModel: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, no runtime artifact reference)
- MainWindowBridge: EXISTS, WIRED, STATIC SOURCE EVIDENCE (code exists, signals documented but no runtime artifact reference)

**Evolution**
- CapabilityGapBridge: EXISTS (in branch), NOT WIRED, STATIC ONLY (25 tests pass, not integrated)

**Status Legend:**
- EXISTS: Code exists
- WIRED: Connected to system
- RUNTIME VERIFIED: Actually works in production (requires concrete evidence: commit, runtime artifact, execution ID, log, report, date, test/runtime provenance)
- PARTIALLY VERIFIED: Some aspects verified, others not
- STATIC SOURCE EVIDENCE: Code exists and can be inspected, but no runtime artifact reference available
- STATIC ONLY: Tests pass, but not runtime-verified
- UNRESOLVED: Cannot be verified with available evidence

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

**CRITICAL:** Until G0 is runtime verified, IABV must NOT be treated as an autonomous development agent.

**Do NOT exchange roles arbitrarily.**

---

## M. NEW CHAT BOOTSTRAP PROTOCOL

**Every new agent MUST:**

1. **Locate IABV_CANONICAL_STATE.md**
   - If not present, checkout branch `docs/interaction-experience-architecture`
   - Verify document SHA matches expected value

2. **Verify branch containing the document**
   - Confirm current branch is `docs/interaction-experience-architecture` or equivalent

3. **Verify canonical document SHA**
   - `git rev-parse HEAD` should match documented SHA
   - If different, review changes before proceeding

4. **Verify origin/main current HEAD**
   - `git fetch origin`
   - `git rev-parse origin/main`

5. **Compare documented frontier commit vs current main**
   - Documented reconciliation anchor: 80e1c9ffbe58925754394f7bb5e8494887eeb62b
   - If different: `DOCUMENTATION_STALE_DELTA = TRUE`
   - Review git log between commits to identify relevant changes

6. **Identify stale delta**
   - Classify changes: RELEVANT TO FRONTIER / HISTORICAL / PARALLEL / NO IMPACT
   - Only update frontier based on demonstrated evidence

7. **Read current frontier** (Section C)

8. **Read unresolved** (Section C)

9. **Read recent Issues/evidence** (Issues #454, #450)

10. **Determine own agent role** (Section L)

11. **Inspect next single action** (Section Y)

12. **Do NOT implement until repository state is reconciled**

**IMPORTANT:** The document is the entry point to reasoning, NOT a substitute for Git verification.

---

## N. BRANCH DISCIPLINE

### CRITICAL RULE: CANONICAL DOCUMENT != CURRENT CODE BRANCH

**The canonical document describes the verified state known when it was last reconciled.**
**The repository HEAD must always be independently checked.**

**Verification Protocol:**
```bash
git fetch origin
git rev-parse origin/main
```

**Compare documented frontier commit vs current main:**
- If different: `DOCUMENTATION_STALE_DELTA = TRUE`
- Agent must review changes before implementing
- DO NOT assume document already represents new HEAD until audited

**This prevents agents from thinking:**
- canonical document → automatically equals main

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

### LOCAL WORKTREE SAFETY

**NEVER PERFORM DESTRUCTIVE CLEANUP BEFORE INSPECTION**

Do NOT automatically execute:
```bash
git clean -fd
git reset --hard
git stash drop
```

Without:
1. `git status` - identify what exists
2. Identify artifacts - distinguish source from runtime artifacts
3. Verify if unbacked information exists
4. Conserve or backup when appropriate

**Runtime artifacts to preserve:**
- `__pycache__` - may contain useful compilation state
- `.vendor_deps` - may contain dependency state
- `.execution_backups` - may contain execution evidence
- `.env` - may contain local configuration
- Runtime data directories

**Only clean after:**
- Explicit inspection confirms safety
- No unbacked information at risk
- User approval obtained

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

## R1. HUMAN-MACHINE INTERACTION EXPERIENCE MODEL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Strategic Principle

The interaction between human and IABV is not merely input/output. It is a future fundamental unit of observation, experimentation, and learning.

### Conceptual Flow

```
HUMAN INTENT
    ↓
CONTEXT
    ↓
IABV SELF / ENVIRONMENT OBSERVATION
    ↓
CAPABILITY ASSESSMENT
    ↓
RESOURCE ASSESSMENT
    ↓
DECISION
    ↓
GOVERNANCE
    ↓
ACTION
    ↓
OBSERVATION
    ↓
EXPECTED vs ACTUAL
    ↓
DISCREPANCY
    ↓
CAUSAL ANALYSIS
    ↓
EXPERIENCE
    ↓
GENERALIZED LESSON
    ↓
FUTURE DECISION
```

### Future Goal

Eventually enable IABV to say:
> "This was what the human intended. This was my state. These were my capabilities. These were my conditions. This was my decision. This is what I expected to happen. This is what actually happened. Here is the evidence. Here exists a discrepancy. These are the possible causes. This cause is demonstrated. This other remains unknown. This is what I legitimately learned. And this learning must influence my next decision."

**This is NOT biological consciousness.** This is evidence-based self-observation + contextual experience + controlled learning.

---

## R2. CONTEXT MODEL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

Future interaction experiences will contain context when real evidence exists:

### HUMAN CONTEXT
- objective
- intent
- requested action
- constraints
- interaction modality

### TEMPORAL CONTEXT
- timestamp
- duration
- sequence position
- prior relevant events

### SYSTEM CONTEXT
- process identity
- session identity
- lifecycle state
- current cognitive process

### HARDWARE / ENVIRONMENT CONTEXT
- CPU
- RAM
- GPU
- disk
- OS
- device
- network conditions
- relevant runtime pressure

### SOFTWARE / CAPABILITY CONTEXT
- models available
- model selected
- tools available
- tool selected
- provider
- version
- capability state
- freshness

### GOVERNANCE CONTEXT
- permissions
- authority
- capabilities
- leases
- approval requirements
- resource constraints

### KNOWLEDGE CONTEXT
- relevant memory
- previous experience
- known limitations
- known errors
- uncertainty

**Do NOT register a field as available simply because it conceptually exists.** Only when real evidence demonstrates availability.

---

## R3. EVIDENCE MODEL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

For each future interaction, distinguish:

- **OBSERVED** - Direct runtime evidence
- **EXPECTED** - Predicted outcome
- **INFERRED** - Derived from other evidence
- **VALIDATED** - Independently verified
- **UNKNOWN** - No evidence available
- **UNRESOLVED** - Contradictory evidence

Use established evidence taxonomy:
- DIRECT_RUNTIME_EVIDENCE
- STATIC_SOURCE_EVIDENCE
- TEST_EVIDENCE
- DERIVED_EVIDENCE
- ENGINEERING_DESIGN
- HISTORICAL_EVIDENCE
- UNVERIFIED_ASSUMPTION

---

## R4. DISCREPANCY MODEL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

Future interactions must distinguish:

### SUCCESS
Observed result matches validated objective.

### PARTIAL
Only part of the result could be validated.

### FAILURE
Result contrary to objective.

### CONTRADICTION
Two sources present incompatible states.

### UNKNOWN
Insufficient evidence.

**Do NOT automatically assume:**
- response received = success
- execution completed = objective satisfied

---

## R5. CAUSAL DISCIPLINE

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Critical Invariants

**CORRELATION ≠ CAUSATION**
**TEMPORAL PROXIMITY ≠ CAUSALITY**

An interaction occurring after a change does NOT prove the change caused the difference.

### Future Experience Must Record
- observation
- candidate cause
- evidence
- counterevidence
- confidence
- unresolved causality

**Never fabricate cause.**

---

## R6. CONTEXT-DEPENDENT BIAS / FRICTION

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Future Capability

Study how the same algorithm behaves differently under different circumstances:

```
ALGORITHM
+
CONTEXT
+
RESOURCES
+
DEVICE
+
MODEL
+
TOOL
+
TIME
+
HUMAN INTENT
```

→
**OBSERVED BEHAVIOR**

### Future Questions
- Does the failure belong to the algorithm?
- The model?
- The tool?
- The resource?
- The environment?
- The context?
- The persisted state?
- An ambiguous human interaction?
- A combination of factors?
- Or simply insufficient evidence?

**Do NOT implement a cause classifier now.** Only document the objective.

---

## R7. SELF-REPORT TRUTHFULNESS (Enhanced)

**Connection to Historical Incident (mcp_client)**

### Principle

IABV must differentiate what it believes it knows from what it is observing now.

### Model

```
PERSISTED BELIEF
       +
LIVE OBSERVATION
       ↓
RECONCILIATION
       ↓
CONSISTENT STATE
or
EXPLICIT CONTRADICTION
```

### Required Behavior
- Do NOT silently overwrite contradiction
- Do NOT assert a causal explanation not demonstrated
- Keep contradictions explicit
- Require resolution decision

---

## R8. EXPERIENCE MODEL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Target Schema

```
experience_id
objective
human_intent
context
system_state
capabilities
resources
decision
action
expected_result
observed_result
evidence
discrepancy
candidate_causes
validated_cause
uncertainty
outcome
lesson
generalization
applicability
next_decision
```

**All fields are TARGET SCHEMA / NOT YET IMPLEMENTED.**

Do NOT create new persistence if existing infrastructure can eventually represent these concepts.

---

## R9. LEARNING RULE (Enhanced)

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Pipeline

```
OBSERVE
→
FORM CLAIM
→
INDEPENDENT AUDIT
→
COUNTEREVIDENCE
→
RECONCILE
→
UPDATE KNOWLEDGE / UNCERTAINTY
→
SELECT NEXT ACTION
→
VERIFY
→
GENERALIZE LESSON
```

### Preserve Existing Invariants

**VERIFIED ≠ ELIGIBLE**
- Verification does not automatically make something eligible for learning.

**AUTHORIZED ≠ ACCEPTED_FOR_LEARNING**
- Authorization does not automatically accept for learning.

### Do NOT Automatically Convert
- Successful interaction → positive learning
- Response received → learning
- Execution completed → learning

**Learning requires:**
- Independent verification
- Evidence-based validation
- Governance approval

---

## R10. ALGORITHM UNDER TEST

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### New Concept

Each relevant interaction can serve as observation of one or more organism algorithms.

### Future Experience Will Indicate
- algorithm
- category
- version
- input conditions
- context
- expected behavior
- actual behavior
- deviations
- evidence
- outcome

### Enables Study Of

`ALGORITHM × CONTEXT × RESOURCE × ENVIRONMENT × HUMAN INTERACTION`

Without assuming a deviation is necessarily an algorithm bug.

---

## R11. SPACE-TIME-DEVICE MODEL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Principle

IABV behavior must be analyzable with respect to the concrete environment where it occurred.

### Conceptual Context

```
SPACE
TIME
DEVICE
PROCESS
SESSION
RESOURCES
MODEL
TOOLS
HUMAN
OBJECTIVE
GOVERNANCE
``

**This is NOT biological spatial/temporal consciousness.** This is experimental contextualization architecture.

---

## R12. TRANSITION TOWARD SELF-DEVELOPMENT

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Stages

**Stage 1:** IABV IS BUILT BY HUMANS

**Stage 2:** IABV OBSERVES ITSELF

**Stage 3:** IABV IDENTIFIES ITS GAPS

**Stage 4:** IABV RECOMMENDS NEXT WORK

**Stage 5:** IABV PARTICIPATES IN A CONTROLLED EXPERIMENT

**Stage 6:** IABV PROPOSES A DEVELOPMENT CHANGE

**Stage 7:** IABV DEVELOPS/TESTS/VALIDATES IN SANDBOX

**Stage 8:** IABV PRODUCES EVIDENCE FOR PROMOTION OR REJECTION

**Stage 9:** IABV LEARNS FROM THE RESULT

**Stages 4–9 = FUTURE TARGET.**

---

## R13. BIRTH GATE REMAINS THE FOUNDATION

**CRITICAL RULE**

Do NOT interpret the existence of this Interaction Experience Architecture as evidence of runtime metacognition.

### Required Sequence

```
BIRTH
→
STABILITY
→
SELF-OBSERVATION
→
INTERACTION EXPERIENCE
→
SELF-DIAGNOSIS
→
RECOMMENDATION
→
LEARNING
→
ASSISTED DEVELOPMENT
→
SELF-DEVELOPMENT
```

Each stage requires independent verification before proceeding to the next.

---

## R14. DUAL-FRAME / MULTI-AGENT EVIDENCE PROTOCOL

**STATUS: FUTURE ARCHITECTURAL TARGET / NOT IMPLEMENTED**

### Strategic Principle

External AIs and tools that audit, test, or develop IABV should be able to use, when evidence and interfaces permit, IABV's own observation, context, state, and diagnostic capabilities as an additional information source about the system being studied.

**This does NOT mean blindly trusting IABV.**

The goal is to establish a model of:

```
EXTERNAL OBSERVATION + IABV SELF-OBSERVATION + REPOSITORY EVIDENCE + RUNTIME EVIDENCE
```

to produce a more complete representation of reality.

### Two Perspectives

**EXTERNAL FRAME** (External AI):
- Observes
- Inspects
- Formulates hypotheses
- Executes tests when appropriate
- Analyzes evidence
- Audits results

**IABV FRAME** (IABV):
- Observes its own state
- Observes environment
- Records resources
- Records capabilities
- Declares uncertainty
- Preserves experience
- Identifies contradictions
- Explains what it believes it knows

**Neither frame should be considered infallible.**

### Triangulation Model

```
EXTERNAL OBSERVATION
        +
IABV SELF-OBSERVATION
        +
REPOSITORY STATE
        +
RUNTIME STATE
        ↓
EVIDENCE RECONCILIATION
        ↓
CONSISTENT STATE
or
CONTRADICTION
or
UNKNOWN
```

The existence of four sources does NOT imply equal epistemological weight. Weight depends on available evidence.

### IABV-AS-INSTRUMENT

Claude / Codex / Devin / ChatGPT / future agents may, when real infrastructure exists:
- Query IABV state
- Query capabilities
- Query resources
- Query context
- Query relevant experience
- Query self-report
- Query previous observations
- Use this data as additional evidence

**But:**
- `IABV SELF-REPORT ≠ TRUTH`
- `IABV OBSERVATION ≠ AUTOMATIC VALIDATION`

External AI must be able to contrast what IABV declares with independent evidence.

### External AI as Auxiliary Capability

Complementarily, IABV may eventually use external agents to:
- Obtain a second perspective
- Investigate contradictions
- Verify hypotheses
- Perform specialized audits
- Obtain evidence IABV cannot produce itself
- Compare models/interpretations
- Evaluate proposals

This should be viewed as:
- `EXTERNAL AGENT = AUXILIARY EVIDENCE / CAPABILITY`

NOT:
- `EXTERNAL AGENT = AUTHORITY`

### Dual Audit

Future goal:

```
IABV CLAIM
      ↓
EXTERNAL AUDIT
      ↓
COUNTEREVIDENCE
      ↓
RECONCILIATION
```

Simultaneously:

```
EXTERNAL AGENT CLAIM
      ↓
IABV OBSERVATION
      ↓
COUNTEREVIDENCE
      ↓
RECONCILIATION
```

This enables:
- IABV to audit external claims
- External agents to audit IABV claims

### Disagreement Matrix

Future matrix:

| External      | IABV          | Interpretation                   |
| ------------- | ------------- | -------------------------------- |
| correct       | correct       | agreement                        |
| correct       | incorrect     | IABV calibration problem         |
| incorrect     | correct       | external-agent reasoning problem |
| incorrect     | incorrect     | insufficient/shared evidence     |
| unknown       | unknown       | unresolved                       |
| contradictory | contradictory | evidence reconciliation required  |

Do NOT automatically assume which side is correct.

### IABV-AS-INSTRUMENT Principle

IABV may progressively become an instrument that helps other intelligences study the system containing IABV.

Future examples:
- Auditor queries resource state through IABV
- Auditor queries capabilities IABV believes available
- Auditor requests contextual reconstruction
- Auditor compares self-report with runtime
- Auditor uses IABV experience to understand an anomaly

This should NOT substitute independent evidence.

### Multi-Agent Learning

Future goal:

```
OBSERVE
→
CLAIM
→
SECOND PERSPECTIVE
→
COUNTEREVIDENCE
→
RECONCILE
→
UPDATE
→
GENERALIZE
```

Accumulated experience should preserve:
- Agent
- Perspective
- Claim
- Evidence
- Counterevidence
- Resolution
- Uncertainty
- Lesson
- Applicability

### Human-IABV-Agent Triad

Future architecture:

```
             HUMAN
            /     \
           /       \
       IABV ------- EXTERNAL AI
```

Each vertex contributes:

**HUMAN:** intent / authority / governance / judgment

**IABV:** self-state / context / experience / internal observations

**EXTERNAL AI:** independent analysis / alternative hypotheses / specialized capabilities

Goal: Enable evidence exchange without losing traceability.

### Context Expansion (Connection to R1-R13)

Future audit may analyze:

```
HUMAN INTENT
+
IABV STATE
+
EXTERNAL AGENT STATE
+
DEVICE
+
RESOURCES
+
MODEL
+
TOOLS
+
TIME
+
ENVIRONMENT
+
GOVERNANCE
```

and study how these conditions influence results.

### Bias / Friction Analysis

Interaction between:

`HUMAN × IABV × EXTERNAL AI`

may generate frictions not necessarily belonging to a single component.

Therefore:

`observed failure ≠ algorithm bug`

Must study:

`algorithm × model × tool × context × resource × human × agent`

### IABV Learning from the Audit Itself

Future goal: When external AI audits IABV, the result should eventually become IABV experience.

Conceptual example:

```
Claude observes X
        ↓
Claude claims Y
        ↓
IABV observes Z
        ↓
Contradiction
        ↓
Evidence reconciliation
        ↓
Validated conclusion
        ↓
Experience
        ↓
Future decision
```

### Security / Governance

External AI use of IABV must respect:
- Authority
- Capability
- Lease
- Execution context
- Approval gates
- Secret isolation
- Resource limits

External AI does NOT obtain authority simply by querying IABV.

Maintain:

`INFORMATION ACCESS ≠ EXECUTION AUTHORITY`

### Epistemic Safety

Maintain:

- `CLAIM ≠ TRUTH`
- `SELF-REPORT ≠ TRUTH`
- `SECOND OPINION ≠ TRUTH`
- `RECOMMENDATION ≠ PROOF`
- `PERSISTED EXPERIENCE ≠ CURRENT STATE`
- `HISTORICAL EVIDENCE ≠ CURRENT RUNTIME`

All sources must preserve provenance.

### Relation to Future Self-Development

This architecture enables:

```
IABV OBSERVES ITSELF
        ↓
IABV OBSERVES EXTERNAL AUDIT
        ↓
IABV COMPARES PERSPECTIVES
        ↓
IABV IDENTIFIES GAP
        ↓
IABV SELECTS NEXT EXPERIMENT
        ↓
IABV USES EXTERNAL CAPABILITY
        ↓
IABV VALIDATES
        ↓
IABV LEARNS
        ↓
IABV IMPROVES FUTURE DECISION
```

This is a goal AFTER G0.

### No Confusion with Superiority

Do NOT record:
> IABV is superior to Claude/Codex/Devin.

Correct hypothesis:
> IABV may evolve toward a system capable of integrating its own observations and external perspectives in a cumulative and verifiable manner.

Any future superiority must be demonstrated experimentally.

---

## R. CURRENT ROADMAP

### NOW
**Birth + Stability + Truthful Readiness** (G0)
- Reliable startup
- Verified READY gate
- Stable interaction
- Safe operation
- Safe termination

### NEXT
**Independent Runtime Proof of Birth + Stability**
- Actual runtime testing
- Evidence collection
- Freeze diagnosis

### AFTER FOUNDATION
**Self-Observation and Truthful State Reconciliation**
- Capability gap detection
- State introspection
- Evidence-based claims

### THEN
**Capability Gap / Decision-Only Experiment**
- Integrate CapabilityGapBridge with AdaptiveTaskOrchestrator
- Self-diagnosis endpoint
- Recommendation (NO execution)

### THEN
**Interaction Experience Measurement**
- Context capture
- Evidence collection
- Discrepancy detection

### THEN
**Learning / Causal Validation**
- Independent verification
- Evidence-based validation
- Governance approval

### LATER
**Assisted Development**
- IABV recommends development work
- Human audits and approves
- Governed execution

### FUTURE
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
- **IABV_CANONICAL_STATE.md** (this file) - PURPOSE: Single source of truth for IABV development - STATUS: CANONICAL - LAST VERIFIED: 2026-09-04 - LOCATION: docs/interaction-experience-architecture branch

### Architecture Documentation
- **AGENTS.md** - PURPOSE: Instructions for agents - STATUS: CANONICAL - LAST VERIFIED: 2026-07-26 - LOCATION: IABV_v1.5/
- **ARCHITECTURAL_DECISIONS.md** - PURPOSE: Architectural decisions - STATUS: CANONICAL - LAST VERIFIED: 2026-07-26 - LOCATION: IABV_v1.5/
- **ARCHITECT_REVIEW_GUIDE.md** - PURPOSE: Architect review guide - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **PROJECT_STATUS.md** - PURPOSE: Project status - STATUS: HISTORICAL (2026-07-26) - LOCATION: IABV_v1.5/
- **ENTRY_POINTS.md** - PURPOSE: System entry points - STATUS: CANONICAL - LAST VERIFIED: 2026-07-26 - LOCATION: IABV_v1.5/
- **CURRENT_RUNTIME.md** - PURPOSE: Runtime state - STATUS: HISTORICAL (2026-07-26) - LOCATION: IABV_v1.5/
- **SYMBOL_INDEX.md** - PURPOSE: Symbol index - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **COMPONENT_DEPENDENCY_GRAPH.md** - PURPOSE: Component dependencies - STATUS: HISTORICAL - LOCATION: IABV_v1.5/

### Audit Reports (Historical)
- **AUDITORIA_PERCEPCION_RUNTIME_UNIVERSAL_REPORTE_FINAL.md** - PURPOSE: Runtime perception audit - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **AUDIT_METACOGNICION_PROFUNDO.md** - PURPOSE: Metacognition audit - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **AUTONOMY_CYCLE_AUDIT.md** - PURPOSE: Autonomy cycle audit - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **AUTONOMY_VALIDATION_REPORT.md** - PURPOSE: Autonomy validation - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **BOOTSTRAP_VISIBILITY_REPORT.md** - PURPOSE: Bootstrap visibility - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **BUILD_INVENTORY_SNAPSHOT_UNIVERSALIZATION_REPORT.md** - PURPOSE: Universalization report - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **CONTROL_CENTER_VIEWMODEL_UNIVERSALIZATION_REPORT.md** - PURPOSE: ViewModel universalization - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **PORTABLE_CONTEXT_UNIVERSALIZATION_REPORT.md** - PURPOSE: Portable context universalization - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **RECONCILIATION_AUDIT_REPORT.md** - PURPOSE: Reconciliation audit - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **UI_INTEGRATION_REPORT.md** - PURPOSE: UI integration - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **UNIVERSAL_CONTINUITY_REEXPRESSED_REPORT.md** - PURPOSE: Continuity reexpression - STATUS: HISTORICAL - LOCATION: IABV_v1.5/

### Other Documentation
- **TOOLS_CANONICAL_POLICY.md** - PURPOSE: Tools policy - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **TEST_SUMMARY.md** - PURPOSE: Test summary - STATUS: HISTORICAL - LOCATION: IABV_v1.5/
- **TECHNICAL_DEBT_REGISTRATION_REPORT.md** - PURPOSE: Technical debt - STATUS: HISTORICAL - LOCATION: IABV_v1.5/

### docs/ Directory
- **ROADMAP_ALGORITHMIC_AUDIT_PLATFORM.md** - PURPOSE: Algorithmic audit roadmap - STATUS: EXPERIMENTAL - LOCATION: IABV_v1.5/docs/
- **mcp-bridge.md** - PURPOSE: MCP bridge documentation - STATUS: EXPERIMENTAL - LOCATION: IABV_v1.5/docs/
- **windsurf_diagnostic_prompt.md** - PURPOSE: Windsurf diagnostics - STATUS: EXPERIMENTAL - LOCATION: IABV_v1.5/docs/
- **windsurf_live_report_prompt.md** - PURPOSE: Windsurf reporting - STATUS: EXPERIMENTAL - LOCATION: IABV_v1.5/docs/

### docs/history/ Directory (Added in delta 0087fa66 → 80e1c9ff)
- **2026-09-01_conversation_knowledge_sync.md** - PURPOSE: Conversation archaeology - STATUS: HISTORICAL - LOCATION: IABV_v1.5/docs/history/
- **2026-09-03_* (30+ files)** - PURPOSE: P0.213 and conversation archaeology - STATUS: HISTORICAL - LOCATION: IABV_v1.5/docs/history/

### New Services (Added in delta 0081fa66 → 80e1c9ff, NOT RUNTIME VERIFIED)
- **organism_state_snapshot.py** - PURPOSE: Organism state snapshot service - STATUS: STATIC ONLY - LOCATION: src/iabv_v15/services/evolution/
- **agent_handoff_trail.py** - PURPOSE: Agent handoff tracking - STATUS: STATIC ONLY - LOCATION: src/iabv_v15/services/evolution/
- **reproducibility_validation_service.py** - PURPOSE: Reproducibility validation - STATUS: STATIC ONLY - LOCATION: src/iabv_v15/services/learning/

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

## Y. CURRENT SINGLE ACTION

**Obtain independent runtime verification of Birth Gate + Stability + Truthful Readiness.**

The Capability Gap Bridge integration remains as the next stage AFTER the foundation (G0) is runtime verified.

**Priority Sequence:**
1. NOW: Birth + Stability + Truthful Readiness (G0)
2. NEXT: Independent runtime proof of Birth + Stability
3. AFTER FOUNDATION: Self-observation and truthful state reconciliation
4. THEN: Capability gap / decision-only experiment (bridge integration)

**Rationale:** No cognitive autonomy expansion before reliable startup, truthful readiness, stable interaction, safe operation, and safe termination are independently verified.

---

## Z. FINAL REMINDER

**This document is the CANONICAL ENTRY POINT.**

**Every new agent MUST read this before implementing.**

**DO NOT rely on conversation history.**

**DO NOT assume main is canonical.**

**DO NOT assume implementation equals verification.**

**When in doubt: UNKNOWN or UNRESOLVED.**
