# CHAT-ARCH 2026-10-08-150 — RQ21.36 PROVISIONAL SEMANTIC CONTRACT

## 1. Provenance / epistemic status

This record reconciles the RQ21.36 semantic response supplied in the current conversation.

Important correction:
The response is **not yet a completed human/domain adjudication**. It is an **AI-proposed semantic contract** intended for human/domain acceptance and independent adversarial challenge.

Status:
**PROVISIONAL / AI-PROPOSED / INDEPENDENT CHALLENGE REQUIRED**

Executable baseline governing the source archaeology remains:
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- TREE: `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

No executable implementation is authorized by this record.

## 2. Proposed semantic contract

### Operation

An operation is a semantic unit of work characterized by:
- object/state acted upon;
- intended functional effect, including deliberate non-modification where relevant;
- relevant input conditions;
- observable success criterion.

Two operations are materially distinct when their required functional outcome, relevant necessary conditions, or verifiable success criterion differ in a way that can alter required capabilities.

Tool/provider identity alone does not define an operation.

### Capability

A capability is an abstract functional competence required to produce the demanded result under relevant task conditions, independent of a concrete tool, provider or implementation.

The proposal excludes from capability identity:
- tool_id;
- assistant/provider identity;
- execution adapter;
- task role;
- routing preference;
- availability;
- readiness;
- policy/authorization/scope state.

These may constrain whether or how a realization may execute without redefining the functional demand.

### R_task

`R_task` is the set of abstract functional capabilities required by a task.

Minimum semantics:
- requirements are conjunctive;
- a realization must satisfy every required capability;
- OR, weighting and ranking semantics are not part of the minimum contract.

Important unresolved semantic check:
`R_task = ∅` must not be casually interpreted as "anything is valid"; the relationship between an empty requirement set, a fully interpreted capability-neutral task, and unresolved/unknown demand must be independently challenged.

### Realization

A realization is a concrete entity, mechanism or process that can satisfy one or more capabilities under relevant conditions.

Possible realizations include tools, humans, external AIs, scripts and services.

### Readiness

Readiness is the current state of a realization/context satisfying the operational preconditions needed to execute the required capability.

### Availability

Availability is the current ability/accessibility to use or assign a realization.

### Preference

Preference is a non-correctness-determining criterion used to order or choose among already eligible realizations.

Core rule:
preference cannot create capability eligibility.

## 3. Proposed minimum causal chain

```
Task
  ↓
semantic interpretation
  ↓
R_task
  ↓
capability-satisfaction filter
  ↓
eligible realizations
  ↓
readiness/availability/governance checks
  ↓
governed preference/selection
  ↓
execution
```

Demand must not be inferred retrospectively from realization-specific actions.

## 4. Proposed uncertainty semantics

### KNOWN
Sufficient evidence exists to determine the required capability set.

### AMBIGUOUS
Multiple materially different interpretations remain plausible and can produce different capability requirements.

Expected route:
```
AMBIGUOUS → information need → discriminating observation → refined interpretation → R_task
```

### UNKNOWN
Insufficient evidence exists to determine the required capability set.

Expected route:
```
UNKNOWN → information need → discriminating observation → KNOWN/AMBIGUOUS
```

UNKNOWN must not be silently converted into `R_task = ∅`.

## 5. Proposed realization-independence principle

The same functional demand may map to multiple concrete realizations:

```
R_task = X
  ├── Tool A
  ├── Tool B
  ├── Human
  ├── External AI
  └── Script
```

when each realization independently satisfies the same functional contract.

Changing provider/tool/implementation does not by itself change capability identity.

## 6. Proposed falsification conditions

The contract should be rejected or refined if evidence demonstrates:

1. two functionally equivalent tasks are separated only because of tool/provider/mode/implementation identity;
2. two materially distinct operations are grouped under one capability although a realization can satisfy one but not the other under otherwise comparable conditions;
3. capability identity changes solely because a realization becomes available/unavailable or ready/not-ready;
4. routing preference is required to determine capability identity;
5. post-selection actions are the only evidence offered for the demand that caused the selection;
6. the contract cannot preserve the same capability across multiple genuinely equivalent realizations.

## 7. Key independent-challenge questions

The adversarial review must specifically test:

### A. Granularity
Is the proposed functional granularity neither too coarse nor too fine?

### B. Empty-set semantics
Is `R_task = ∅` sufficiently distinguished from UNKNOWN and from a task whose capability dimension is genuinely empty?

### C. Preconditions versus capabilities
Are permissions, authorization, execution scope, safety constraints and contextual prerequisites correctly kept separate from functional capability while still being represented as necessary execution conditions?

### D. Verification as capability
Does "verify result" belong in `R_task` only when verification is itself an explicit task objective/requirement, rather than being universally inserted into every task?

### E. Capability versus task success
Does the definition avoid encoding the entire task into a capability, while still being concrete enough to discriminate realizations?

### F. Composition
Does conjunctive `R_task` compose correctly when different realizations each satisfy only subsets of the requirement?

### G. Uncertainty
Can UNKNOWN/AMBIGUOUS remain epistemic states without accidentally becoming selection semantics?

## 8. FACT / INFERENCE / DESIGN PROPOSAL / UNPROVEN

FACT:
- RQ21.35 closed the bounded source archaeology as C.
- Existing pre-selection semantic objects were insufficient for exact `R_task`.
- `ToolActionType` in the traced path is post-selection.

INFERENCE:
- a realization-independent abstract demand contract is the appropriate missing semantic edge.

DESIGN PROPOSAL:
- the operation/capability/R_task/realization/readiness/availability/preference definitions in this record.

UNPROVEN:
- that this exact proposed semantic contract is the best contract for IABV;
- that the proposed examples cover the relevant capability domain;
- that the empty-set semantics are fully resolved;
- that verification should or should not be a capability in every class of task;
- that the contract will support later adaptive reuse without refinement.

## 9. Symbiosis / cumulative-development delta

Knowledge Delta:
The project has moved from source-level "what exists" archaeology to an explicit provisional semantic contract for the missing demand-side bridge.

Method Delta:
When source archaeology closes the implementation-independent behavior but cannot decide normative semantics, record the semantic proposal explicitly, label it provisional, and subject it to independent adversarial falsification rather than silently treating AI synthesis as domain truth.

Routing Delta:
Next actor = **SONNET/CLAUDE**, because the remaining uncertainty is adversarial semantic-contract validity rather than source archaeology.

Implementation status:
**DO NOT IMPLEMENT.**
