# CHAT-ARCH 2026-10-08-159 — RQ21.43A SEMANTIC FALSIFICATION

## 1. Status

RQ21.43A = **PASS WITH BOUNDED REPAIRS**.

The independent Sonnet/Claude challenge did not falsify any of the three human adjudications:

- `tools.local_workflow` remains **AMBIGUOUS**;
- `tools.sandbox` remains **KNOWN**;
- `system.metacognition` remains **AMBIGUOUS**.

The sandbox capability requires four local wording/contract repairs. These do not change the capability's identity or demand state.

No implementation, runtime execution, executable-source change, or repository code modification occurred in this review.

Executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

## 2. Sandbox contract after falsification

The surviving capability should be expressed as a single conjunctive functional capability, with the following bounded repairs:

### R1 — containment parameterization

Replace vague "effective isolation" with:

> containment of a declared set `E` of protected effects, where `E` is supplied by the task envelope.

Whether a realization actually achieves that containment is evidence about the realization, not part of capability identity.

### R2 — explicit expected behavior

The candidate and expected behavior specification `X` are inputs to the capability. Without `X`, no validation verdict can be justified.

### R3 — dynamic-validation scope

The adjudicated capability is **dynamic validation**: its predicate requires an actual execution under the declared containment conditions.

Static/formal validation is outside this capability unless the domain owner later broadens or splits the semantic contract.

### R4 — partial realizations do not satisfy C

A realization that supplies only observation, only execution, or execution-plus-observation is a partial realization and does not satisfy the full capability.

Observation must include sufficient evidence about the protected effects in `E`, including evidence of their absence.

## 3. Surviving formal boundary

For a concrete task:

`candidate + expected_behavior X + protected_effect_set E`

the capability determines whether the dynamic execution produces an interpretable validation result under the constraint that no protected effect in `E` occurred.

The capability is **necessary** for tasks whose success predicate includes dynamic validation without producing the protected effect.

It is **not automatically sufficient for the whole task**. Candidate generation, deployment, approval, and other functional demands may be separate requirements.

Thus:

`R_task = {C_SANDBOX_DYNAMIC_VALIDATION}`

does not imply universal task sufficiency.

The capability meaning remains independent of any particular tool, adapter, provider, sandbox mechanism, or assistant.

## 4. Falsification results

### tools.local_workflow

Minimum falsifier: a single realization-independent capability with its own success predicate that simultaneously and discriminatively covers materially different operations such as reading, modifying, executing and transforming.

Falsifier found: **NO**.

Result: **SURVIVES / AMBIGUOUS**.

Two concrete operations may share a capability (for example, faithful non-mutating observation of local state), but that does not make the whole family one capability.

Optional terminology noted by Sonnet/Claude:

- `AMBIGUOUS_HETEROGENEOUS`: family maps to multiple capabilities;
- `AMBIGUOUS_UNDERSPECIFIED`: one capability is intended but underdefined.

No new runtime state is required by this distinction. The family remains non-promotable as a capability.

### tools.sandbox

Minimum falsifier: a valid counterexample to the single conjunctive dynamic-validation capability.

Falsifier found: **NO**.

Result: **SURVIVES WITH R1-R4**.

Static/formal validation is explicitly outside scope, so it does not invalidate the dynamic capability.

### system.metacognition

Minimum falsifier: a non-circular abstract capability `K` for which the current A/B/C interpretations are all genuine instances.

Falsifier found: **NO**.

Counterexample supporting ambiguity: a changelog reconstruction can satisfy the historical-progress interpretation without auto-observation or pre-action discernment; a current health check can satisfy auto-observation without historical reconstruction.

Result: **SURVIVES / AMBIGUOUS**.

## 5. Machine vocabulary remains unresolved

The challenge did not promote any existing ID.

Conditional semantic classification:

| Candidate | Status | Reason |
| --- | --- | --- |
| `tools.local.sandbox` | **MIXED** | names a local mechanism/family and therefore carries realization context; it is not yet the abstract identity of dynamic validation |
| `tools.local.execution` | **PRECONDITION** | execution is a component of dynamic validation but does not imply containment plus observation plus verdict |
| `tools.local.registry` | **INVALID** | concerns inventory/declaration/discovery of realizations rather than the validation function |

Important boundary:

`semantic capability closed` ≠ `machine ID selected`.

## 6. Consequence for implementation readiness

The semantic layer is now sufficiently adjudicated for one narrow implementation-contract reconciliation:

`C_SANDBOX_DYNAMIC_VALIDATION`

Only the code-facing mapping and existing-organ composition remain open.

Still unresolved before implementation:

- machine-readable ID choice;
- whether a new bounded ID is needed or an existing ID can be semantically repurposed without contamination;
- exact request-side typed placement;
- exact realization declaration authoring;
- complete hard-gate closure across the known selection/fallback routes;
- DEFERRED propagation;
- actual runtime evidence that a realization satisfies the capability.

These are code-facing questions, not reasons to reopen the semantic meaning of the capability.

## 7. Knowledge / Method / Routing Delta

### Knowledge Delta

- independent adversarial review confirms the three human demand states;
- sandbox dynamic validation is a single conjunctive capability under a bounded envelope;
- static/formal validation is a separate semantic scope;
- existing sandbox readiness IDs remain unsuitable as automatic capability identity.

### Method Delta

- falsify the semantic predicate before choosing a machine vocabulary;
- treat envelope parameters as task inputs, not realization identity;
- distinguish partial realization from capability satisfaction;
- keep necessity/sufficiency separate.

### Routing Delta

Next actor:
**CODEX** for a source-aware, code-facing gap reconciliation limited to the sandbox capability.

Scope:
- locate the minimum existing request/session/task seam before selection;
- determine whether an existing machine ID can safely represent the adjudicated capability without semantic contamination;
- inspect realization seeds for candidates;
- identify the minimum declaration and eligibility-gate wiring points;
- report, do not implement.

`tools.local_workflow` and `system.metacognition` must remain unpromoted.

## 8. Epistemic boundary

**FACT:** the human/domain adjudication exists and survived independent semantic challenge with bounded repairs.

**INFERENCE:** the sandbox capability is a defensible realization-independent functional contract.

**UNPROVEN:** any current realization actually satisfies it; any current machine ID is semantically equivalent; selection currently enforces it; runtime evidence demonstrates it.

**LEARNING:** not demonstrated. The writeback is cumulative memory, not proof of autonomous learning.
