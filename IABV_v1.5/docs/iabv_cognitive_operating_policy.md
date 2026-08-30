# IABV v1.5 — Cognitive Operating Policy

## 1. PURPOSE

This document defines the normative architectural contract for the cognitive operating layer of IABV v1.5.

The cognitive operating policy is a **pure, bounded policy layer** that determines cognitive envelopes for each work item. It does NOT execute, orchestrate, schedule, or plan. It only computes cognitive constraints based on normalized state.

The policy answers: **"Given this state, what cognitive envelope should govern this work?"**

## 2. SCOPE

The cognitive operating policy applies to:

- **Work items** from ControlMasterService.current_work_queue()
- **Internal metabolic state** from InternalMetabolicStateService.inspect()
- **Existing context/evidence** from TaskContextAssembler, GoalEngine, CapabilityReadinessService
- **Resource state** from ResourceAwareController
- **Reflection routing** from ReflectionRoutingService

The policy produces:

- **Time horizon** (SHORT, MEDIUM, LONG)
- **Reasoning depth** (LEVEL 0-3)
- **Time budget** (hard bounds)
- **Resource budget** (hard bounds)
- **Chunk size** (adaptive)
- **Parallelism** (allowed/forbidden)
- **Observation mode** (OBSERVE, REFLECT, ACT, DEFER)
- **Stopping conditions** (hard and soft bounds)
- **Tool/model selection envelope** (constraints, not hardcoded providers)

## 3. NON-GOALS

The cognitive operating policy is **NOT**:

- A new orchestrator
- A new scheduler
- A new memory system
- A new planner
- A new provider selector
- A replacement for ResourceAwareController
- A replacement for ReflectionRoutingService
- A replacement for TaskContextAssembler
- A replacement for ControlMasterService
- A replacement for AdaptiveTaskOrchestrator
- A replacement for InferenceService
- A replacement for TaskOutcomeRecorder

## 4. OWNERSHIP RULES

| Component | Owner | Responsibility |
|-----------|-------|----------------|
| InternalMetabolicStateService | Self-inspection | Provides read-only metabolic state snapshot |
| ControlMasterService | Governance | Owns work queue, prioritization, executive work projection |
| CognitivePolicy | This layer | Computes cognitive envelopes from normalized state |
| WorkQueueExecutor | Bridge | Bridges queue to canonical inference |
| AdaptiveTaskOrchestrator | Execution | Orchestrates request execution and decision-making |
| InferenceService | Provider boundary | Canonical inference execution |
| TaskOutcomeRecorder | Learning | Records outcomes and learning closure |
| ResourceAwareController | Resources | Resource-aware scheduling and control |
| ReflectionRoutingService | Reflection | Reflection routing and decision-making |

**Key Rule**: CognitivePolicy is READ-ONLY. It does not modify any state. It only computes constraints.

## 5. STATE VECTOR

The cognitive policy operates on a normalized state vector:

### Input State

| Symbol | Name | Description | Source |
|--------|------|-------------|--------|
| G | Goal Value | Importance and urgency of the work item | ControlMasterService work item priority |
| C | Complexity | Structural complexity of the task | Work item metadata, TaskContext |
| A | Ambiguity | Ambiguity in requirements or specification | Work item metadata, TaskContext |
| U | Uncertainty | Uncertainty in outcome or approach | InternalMetabolicState, TaskContext |
| R | Risk | Risk of failure or negative consequences | Work item metadata, InternalMetabolicState |
| V | Expected Value | Expected value of successful completion | Work item priority, GoalEngine |
| T | Available Time | Time budget for this work item | ResourceAwareController, work item deadline |
| E | Resource State | Current resource availability (RAM, CPU, GPU) | ResourceAwareController |
| M | Memory Relevance | Confidence in relevant memory/knowledge | KnowledgeRepository, GoalEngine |
| X | Prior Experience | Historical success on similar work | RunRepository, TaskOutcomeRecorder |

### Derived Outputs

| Symbol | Name | Description |
|--------|------|-------------|
| D | Reasoning Depth | LEVEL 0-3 (fast → expert) |
| H | Time Horizon | SHORT, MEDIUM, LONG |
| B | Budget | Time and resource budget bounds |
| K | Chunk Size | Adaptive chunk size for work decomposition |
| P | Parallelism | Allowed parallelism level |

**Important**: No arbitrary numeric coefficients are assigned. The policy uses qualitative thresholds and ordinal comparisons.

## 6. HORIZONS

### SHORT Horizon
- **Scope**: Current interaction / incident / urgent work
- **Timeframe**: Seconds to minutes
- **Characteristics**: Low latency, fast response, immediate action
- **Example**: Fixing a blocking bug, responding to user query

### MEDIUM Horizon
- **Scope**: Current work item / task / playbook
- **Timeframe**: Minutes to hours
- **Characteristics**: Normal contextual reasoning, moderate deliberation
- **Example**: Implementing a feature, resolving a pending issue

### LONG Horizon
- **Scope**: Architecture / evolution / strategic learning
- **Timeframe**: Hours to days
- **Characteristics**: Deep reflection, extensive evidence gathering
- **Example**: Architectural refactoring, strategic learning initiatives

**Anti-Starvation Rule**: Long-horizon work must not starve short-horizon work unless dependency or risk explicitly justifies it. SHORT horizon always has priority for urgent/interactive work.

## 7. REASONING DEPTH

### LEVEL 0: Fast / Existing Evidence
- **Characteristics**: Use existing evidence, no additional reasoning
- **Latency**: < 1 second
- **Use Case**: Trivial tasks, cached answers, well-known patterns

### LEVEL 1: Normal Contextual Reasoning
- **Characteristics**: Normal contextual reasoning with existing evidence
- **Latency**: 1-10 seconds
- **Use Case**: Standard development tasks, routine problem-solving

### LEVEL 2: Deep Reflection / Additional Evidence
- **Characteristics**: Deep reflection, gather additional evidence
- **Latency**: 10-60 seconds
- **Use Case**: Complex tasks, ambiguous requirements, high-risk work

### LEVEL 3: Expert / External Reasoning
- **Characteristics**: Expert reasoning, external providers, extensive deliberation
- **Latency**: 60+ seconds
- **Use Case**: Architectural decisions, novel problems, critical failures

**Boundedness**: Higher levels may improve or invalidate a previous decision, but must remain bounded by hard budget constraints.

## 8. TIME BUDGET

### Hard Bounds
- **Maximum Time**: Absolute time limit for this work item
- **Maximum Iterations**: Maximum number of reasoning cycles
- **Maximum Observations**: Maximum number of observation actions
- **Maximum Resource/Cost**: Maximum resource consumption
- **Maximum Replanning**: Maximum number of replanning cycles

### Soft Bounds
- **Confidence**: Target confidence threshold
- **MRV**: Marginal Reasoning Value threshold
- **MVI**: Marginal Value of Information threshold
- **Saturation**: Evidence saturation point

**Rule**: Hard bounds override soft criteria. When a hard bound is reached, the system must return the best valid state available.

## 9. RESOURCE BUDGET

### Resource Dimensions
- **RAM**: Memory consumption limit
- **CPU**: CPU time limit
- **GPU**: GPU utilization limit (if applicable)
- **Quota**: API quota limit (for remote providers)
- **Opportunity Cost**: Cost of blocking other work

### Pressure Classification
- **Critical**: < 2GB available RAM
- **High**: < 4GB available RAM
- **Moderate**: < 6GB available RAM
- **Low**: >= 6GB available RAM

**Rule**: Resource pressure reduces allowed depth and budget. CRITICAL pressure always results in DEFER policy for non-urgent work.

## 10. CHUNKING

### Adaptive Chunking

Chunk size K is a function of budget, depth, uncertainty, and risk:

```
K = f(B, D, U, R)
```

### Chunking Behavior

**Under Pressure**:
- Smaller chunks
- More frequent checkpoints
- Easier rollback

**Under Stable Resources and Low Uncertainty**:
- Larger chunks allowed
- Fewer checkpoints
- Higher efficiency

**No Universal Chunk Size**: Chunk size is adaptive and context-dependent. It is not hardcoded.

### Persist/Resume

Chunk persistence and resume must use existing GoalEngine/subtask identity. No new persistence system is introduced.

## 11. PARALLELISM

### Parallelism Function

Parallelism P is a function of independence, dependency graph, resource state, and risk:

```
P = f(independence, dependency_graph, E, R)
```

### Parallelism Forbidden When

- Dependencies conflict
- Resources are insufficient
- Risk is too high
- Work is not independently verifiable

### Dependency Graph

Reuse AdaptivePlannerService where applicable for dependency analysis. Do not build a new scheduler in this commit.

## 12. OBSERVATION VS REASONING

### Observation Mode

The policy chooses between:

- **OBSERVE**: Gather more information before reasoning
- **REFLECT**: Reason with existing evidence
- **ACT**: Execute with current evidence
- **DEFER**: Defer work to later

### Decision Criteria

The decision is based on comparing MRV (Marginal Reasoning Value) and MVI (Marginal Value of Information).

## 13. MRV (Marginal Reasoning Value)

### Definition

```
MRV_k = ExpectedQualityGain(reason_k) / ExpectedReasoningCost(reason_k)
```

### Expected Quality Gain

Expected gain may use:
- Uncertainty reduction
- Confidence increase
- Requirement coverage
- Risk reduction
- Historical success

### Reasoning Cost

Reasoning cost may include:
- Latency
- CPU
- RAM
- GPU
- Quota
- Opportunity cost
- Risk of blocking urgent work

**No Arbitrary Production Weights**: The policy does not assign arbitrary numeric coefficients. It uses qualitative comparisons and thresholds.

## 14. MVI (Marginal Value of Information)

### Definition

```
MVI_k = ExpectedDecisionQualityGain(observation_k) / Cost(observation_k)
```

### Policy Choice

```
if MVI sufficiently exceeds MRV:
    OBSERVE

elif MRV sufficiently exceeds marginal action cost:
    REFLECT / REASON

elif evidence is sufficient:
    ACT

else:
    DEFER / REPLAN
```

### Hysteresis / No-Repeat Rules

Introduce hysteresis and no-repeat rules so the system cannot oscillate indefinitely between OBSERVE and REFLECT. Once a mode is chosen, the system must persist for a minimum duration or until a significant state change.

## 15. PREMATURE CLOSURE

### Prevention

The policy prevents premature closure by:

- Requiring minimum evidence thresholds
- Checking for marginal value before stopping
- Validating that stopping conditions are met
- Ensuring hard bounds are not the only reason for stopping

### Validation

Before returning a decision, the policy validates:
- Evidence is sufficient for the chosen action
- Confidence is above minimum threshold
- No critical information is missing
- Risk is acceptable

## 16. UNBOUNDED DELIBERATION

### Prevention

The policy prevents unbounded deliberation by:

- Enforcing hard time bounds
- Enforcing hard iteration bounds
- Enforcing hard resource bounds
- Detecting repeated equivalent reasoning
- Detecting repeated equivalent observation

### Stopping Conditions

The system must stop when:
- Sufficient evidence is gathered
- Acceptable confidence is reached
- Marginal gain falls below threshold
- Hard budget is reached
- Resource pressure is detected
- Repeated equivalent reasoning is detected
- Repeated equivalent observation is detected
- Deadline is exhausted

### Return Best Valid State

When stopping, the system returns the best valid state available before stopping. It does not return an incomplete or invalid state.

## 17. ANYTIME COGNITION

### Principle

The policy supports anytime cognition: it can return a valid decision at any time, with quality improving as more resources are allocated.

### Quality-Time Tradeoff

The policy explicitly represents the quality-time tradeoff through MRV and MVI. It can recommend stopping early if marginal value is low.

### Graceful Degradation

Under resource pressure, the policy gracefully degrades:
- Lower reasoning depth
- Smaller chunks
- Reduced parallelism
- Earlier stopping

## 18. STOPPING RULES

### Stopping Conditions

The policy defines stopping conditions for:

- **Sufficient Evidence**: Evidence threshold is met
- **Acceptable Confidence**: Confidence threshold is met
- **Low Marginal Gain**: MRV falls below threshold
- **Hard Budget Reached**: Time or resource hard bound is reached
- **Resource Pressure**: Critical resource pressure is detected
- **Repeated Equivalent Reasoning**: Same reasoning cycle repeats
- **Repeated Equivalent Observation**: Same observation repeats
- **Deadline Exhaustion**: Time deadline is exhausted

### Return Best Valid State

When stopping, return the best valid state available. Do not return an incomplete or invalid state.

## 19. TOOL/MODEL SELECTION ENVELOPE

### Constraints, Not Hardcoded Providers

The policy itself **MUST NOT** choose a named provider directly. It produces constraints such as:

- **REQUIRED_CAPABILITY**: Required tool capabilities
- **MAX_COST**: Maximum cost allowed
- **MAX_LATENCY**: Maximum latency allowed
- **MAX_RISK**: Maximum risk allowed
- **ALLOWED_LOCAL**: Whether local providers are allowed
- **ALLOWED_REMOTE**: Whether remote providers are allowed
- **MIN_REASONING_LEVEL**: Minimum reasoning level required
- **REQUIRED_EXECUTION_CAPABILITY**: Required execution capabilities

### Existing Selectors

Existing selectors (e.g., AdaptiveTaskOrchestrator, InferenceService) may use these constraints to choose specific providers. This prevents the policy from replacing the provider/model selector.

### No Hardcoded Rules

No fixed rules such as:
- "coding → Devin"
- "always use Ollama for X"
- "always use remote for Y"

Tool/model selection is determined by capability, required depth, horizon, resource state, time, risk, experience, and availability.

## 20. LOCAL VS REMOTE POLICY

### LOCAL Providers

- **Examples**: Ollama, local resources
- **Characteristics**: Lower latency, no quota, limited capability
- **Use Case**: Fast reasoning, low-risk work, offline work

### REMOTE Providers

- **Examples**: Devin, other remote providers
- **Characteristics**: Higher latency, quota limits, higher capability
- **Use Case**: Expert reasoning, high-risk work, capability-intensive work

### TOOLS

- **Examples**: GitHub, web, sandbox, adapters
- **Characteristics**: External dependencies, variable latency
- **Use Case**: Information gathering, external execution

### Selection Criteria

Selection depends on:
- Capability required
- Required depth
- Horizon
- Resource state
- Time available
- Risk tolerance
- Prior experience
- Availability

**No Fixed Rules**: No fixed mapping between task type and provider. Selection is based on constraints and context.

## 21. VALIDATION

### Decision Validation

Before returning a decision, the policy validates:
- Decision is consistent with state vector
- Decision respects hard bounds
- Decision is deterministic for normalized inputs
- Decision is side-effect free
- Decision is serializable/loggable without credentials

### Evidence Validation

The policy validates:
- Evidence is sufficient for chosen action
- Evidence is relevant to the work item
- Evidence is from reliable sources
- Evidence is not stale

### Risk Validation

The policy validates:
- Risk is acceptable for chosen action
- Risk mitigation is in place
- Risk does not exceed hard bounds

## 22. LEARNING

### Learning Feedback

The policy does not learn directly. Learning is handled by:
- TaskOutcomeRecorder
- ExperimentLab
- AdaptiveWeightLayer
- AutonomousValidationCycleService
- SelfDiscoveryService

### Policy Updates

Policy updates are handled by:
- Manual review and adjustment
- ExperimentLab validation
- AutonomousValidationCycleService validation

The policy itself does not automatically update based on outcomes. This prevents runaway self-modification.

## 23. TRACEABILITY

### Decision Trace

Each CognitivePolicyDecision includes:
- Input state vector snapshot
- MRV calculations
- MVI calculations
- Horizon reasoning
- Depth reasoning
- Budget reasoning
- Chunking reasoning
- Parallelism reasoning
- Observation mode reasoning
- Stopping condition checks

### Logging

The decision is serializable/loggable without credentials. It can be logged for audit and debugging.

### Reproducibility

Given the same normalized input state, the policy produces the same output. This enables reproducibility and debugging.

## 24. FALSIFIABLE TEST REQUIREMENTS

### Behavioral Tests

Future behavioral tests must verify:

A. More reasoning should improve quality only when justified.
B. Reasoning should stop when marginal value falls.
C. Observation should beat reasoning when information value is higher.
D. Resource pressure should lower cognitive cost.
E. Long-term work must not starve short-term work.
F. Tool choice should change when required capability changes.
G. Tool choice should change when resources change.
H. Ollama and Devin must be selectable under different envelopes.
I. Uncertainty must increase evidence requirements.
J. Hard bounds must stop deliberation.

### Unit Tests

Unit tests must verify:
- Policy is deterministic for normalized identical inputs
- Policy is side-effect free
- Policy returns short horizon for urgent low-latency work
- Policy can return medium horizon for normal work
- Policy can return long horizon for architectural work
- Resource pressure reduces allowed depth/budget
- Higher uncertainty increases evidence requirement
- High risk increases stopping/validation constraints
- Low MRV permits stopping
- MVI > MRV prefers observation
- Sufficient evidence allows action
- Insufficient evidence cannot directly authorize action
- Hard budget overrides MRV
- Chunk size responds to budget
- Parallelism is restricted by dependency/resource conditions
- Tool selection output is constraints, not hardcoded provider identity
- No provider executes during policy evaluation
- No Ollama executes during policy evaluation
- No Devin executes during policy evaluation
- Existing governance remains unchanged
- Context reuse remains unchanged

### Test Fixtures

Tests should use controlled deterministic fixtures, not random or production data.

## 25. INTEGRATION POINT

### Minimal Integration Seam

The policy provides the smallest integration seam:

```
WorkItem
+ InternalMetabolicState
+ existing TaskContext/evidence
→ CognitivePolicyDecision
```

This decision can later be consumed by:
- WorkQueueExecutor
- AdaptiveTaskOrchestrator

### Observable Before Execution

The decision must be observable before execution. This enables:
- Validation before execution
- Human review before execution
- Governance checks before execution

### No Autonomous Execution

Do NOT automatically activate the whole WorkQueueExecutor loop yet. The policy is a pure decision layer, not an execution layer.

## 26. FUTURE EXECUTION ORDER

The policy output supports this future flow:

```
WorkItem
→ cognitive policy
→ horizon
→ depth
→ budget
→ observe/reason/act/defer
→ tool/model constraints
→ existing WorkQueueExecutor
→ existing governance
→ existing inference
→ validation
→ outcome
→ learning
```

Do not connect the autonomous execution loop in this commit.

## 27. ARCHITECTURAL SUMMARY

### Pure Policy Layer

The cognitive operating policy is a **pure, bounded policy layer** that:

- Computes cognitive envelopes from normalized state
- Does NOT execute, orchestrate, schedule, or plan
- Is READ-ONLY and SIDE-EFFECT FREE
- Is DETERMINISTIC for normalized inputs
- Produces constraints, not hardcoded provider names

### Integration

The policy integrates with existing services:
- InternalMetabolicStateService (read-only)
- ControlMasterService (work item source)
- ResourceAwareController (resource state)
- TaskContextAssembler (context)
- GoalEngine (goal context)
- CapabilityReadinessService (capability state)

### Output

The policy produces:
- CognitivePolicyDecision (immutable, serializable)
- Constraints for existing selectors
- Recommendations for existing orchestrators

### No New Master

The policy does NOT become a new master algorithm. It is a bounded decision layer that supports existing masters (ControlMasterService, AdaptiveTaskOrchestrator).
