# CHAT-ARCH 2026-10-08-161 — RQ21.44A CODE-CONTRACT VERIFICATION

## 1. Status

RQ21.44A = **PASS WITH BOUNDED REPAIRS / READY FOR MINIMAL CODE CONTRACT**.

Independent Sonnet/Claude verification did not find a contradiction that invalidates the bounded code-facing contract for `C_SANDBOX_DYNAMIC_VALIDATION`.

It did identify four local repairs to the contract text (RA, RB, RC, RI) and two substantive repairs that must be treated as implementation-contract constraints rather than optional wording:

- **RE:** realization eligibility must require declaration + evidence of the capability, not merely a declaration or `supports_sandbox`/availability signal; a governed test/acquisition path must exist so the system is not bootstrapped into permanent empty eligibility.
- **RF:** task envelope `E) and expected behavior `X) require explicit realization-side coverage; a realization cannot claim full capability without demonstrating it can satisfy the task's `E/X` contract.
- **RG:** `R_task = {C}` must not be interpreted as universal sufficiency for an arbitrary multi-function ToolTask. The current first slice must be treated as a validation step/task whose success predicate matches C, with broader composition left separate.
- **RH:** governed negative handling must also cover a non-empty but irresolvable `tool_id`, not only an empty one.

Additional wording repairs:

- **RA:** a machine namespace must exclude readiness/state/availability terms and realization-context terms such as locality/mechanism; machine-ID authorization is a separate owner action.
- **RB:** demand must never be inferred retroactively from ToolTask fields such as `sandbox_first`, `execution_scope`, `expected_outcome`, or `tool_id`.
- **RC:** because explicit/preference routes can bypass candidate filtering, the final resolution guard is an enforcement boundary, not merely a backstop.
- **RI:** existing readiness/evidence signals are reusable infrastructure but do not constitute evidence of the full C capability unless validation consumes and compares `X) and checks the protected-effect channel.

No implementation, runtime execution, or executable-source modification occurred.

Executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

## 2. Reconciled contract

The minimum code-facing contract is now:

`demand(C) → eligible realizations → governed selection → dynamic validation(C,E,X) → evidence/update`

with:

`eligible(c, task) = declaration(c,C) ∧ evidence(C,c,E,X) ∧ readiness(c) ∧ governance(c,task)`

where the exact representation of each term remains an implementation question.

The key semantic rule is:

**declaration alone is not capability proof.**

Likewise:

**availability/readiness is not capability identity or capability evidence.**

## 3. Machine-ID status

No existing machine ID is authorized.

Current bounded findings remain:

- `tools.local.sandbox` = readiness/inventory-derived; not safe;
- `tools.local.execution` = availability/precondition; not safe;
- `tools.local.registry` = inventory precondition; not safe;
- `ToolCapability.TOOL_SANDBOX` = broad routing enum; not proven equivalent.

A future machine ID may be newly introduced only as a bounded capability-identity label whose namespace is separate from readiness and whose semantics are explicitly authorized by the domain owner.

This is **not** authorization to create it yet.

## 4. Demand placement

`InferenceRequest` remains the earliest typed request carrier on the focal path.

The demand must be present before:

- candidate enumeration;
- explicit/suggested tool preference;
- external preference;
- Synaptic selection;
- lexical/family fallback.

The task remains an immutable/frozen semantic echo, not the origin.

No demand may be inferred retroactively from existing ToolTask defaults or routing fields.

## 5. Realization declaration

A bounded separate declaration remains the correct structural extension:

`ToolCard.realizes_capability_ids`

but it is only a **claim**.

For a realization to be eligible for C, the implementation contract must additionally establish evidence that the realization can satisfy the requested `E) and `X) under dynamic execution.

No current card is proven to do so.

## 6. Two-gate enforcement

The contract requires:

### Gate 1 — candidate eligibility

Before ranking, eliminate cards whose capability declaration/evidence/governance/readiness do not satisfy the task.

### Gate 2 — final resolution

Immediately before adapter invocation, re-check the selected card against the frozen demand and task envelope.

Gate 2 is an enforcement boundary because explicit tool IDs and several preference/fallback paths can bypass candidate filtering.

If Gate 2 rejects, it must not re-enter generic fallback.

## 7. Envelope E/X

The first implementation slice must carry:

- candidate;
- expected behavior `X);
- protected effect set `E).

Current fields are insufficient:

- `ToolTask.expected_outcome` exists but is not the actual validation predicate;
- `execution_scope` is coarse governance/policy;
- `sandbox_first` is policy and must not become demand;
- `supports_sandbox` is card metadata/readiness signal;
- current validator success does not compare against `X).

Therefore E/X representation is **BOUNDED EXTEND**.

The realization side must declare or otherwise prove its coverage for the relevant E/X constraints before it becomes eligible.

## 8. Negative/deferred outcome

The intended invariant is:

`KNOWN demand + eligible set = empty → governed negative`

and also:

`KNOWN demand + non-empty but unresolved requested realization → governed negative`

Neither case may fall through to:

- lexical selection;
- family fallback;
- first-card fallback;
- unconstrained registry resolution.

Existing `ToolTaskStatus.DEFERRED` is a reusable state candidate, but propagation remains unimplemented/unproven.

## 9. Validation bootstrap requirement

A new but bounded implication is now explicit:

If no realization has evidence of C, eligibility is empty under the hard evidence rule.

Therefore a practical implementation cannot both:

1. require prior evidence for eligibility, and
2. have no governed way to execute a candidate in order to acquire that evidence.

The contract must distinguish:

`capability-eligibility evidence`

from:

`governed capability-test/acquisition path`

A test/acquisition execution may produce evidence for future eligibility, but its own declaration or execution result must not be treated as proof merely because it happened.

This is a readiness/learning control issue, not a reason to weaken the hard capability invariant.

## 10. Minimal code-contract readiness

The source and adversarial reviews are now sufficient to draft an implementation contract, but not to authorize implementation.

Still unresolved:

1. owner-authorized machine ID;
2. exact representation of E and X;
3. exact evidence type/producer for C;
4. exact test/acquisition route;
5. exact mutation/persistence mechanics for frozen demand;
6. complete adapter-call-site closure;
7. DEFERRED persistence and consumer semantics;
8. runtime proof of actual effect containment and validation.

## 11. Knowledge / Method / Routing Delta

### Knowledge Delta

- code-contract verification found no invalidating contradiction;
- declaration and evidence are distinct;
- E/X require realization-side coverage;
- hard eligibility can create an empty set by design, requiring a governed evidence-acquisition path;
- unresolved `tool_id` is another fallback-resurrection route.

### Method Delta

- never equate declaration with evidence;
- a hard capability filter must not be weakened to solve bootstrap;
- distinguish eligibility from capability-test/acquisition;
- final resolver guard is an enforcement boundary;
- negative paths must include both empty and explicitly irresolvable requested realizations.

### Routing Delta

The next actor is again **CHATGPT / HUMAN DOMAIN OWNER**.

The remaining decisions are partly normative:
- authorize or reject creation of a separate machine capability ID;
- decide the bounded implementation representation of E/X;
- decide whether the first slice is a dedicated validation ToolTask or a composition inside a broader task.

Only after those are explicitly fixed should a final independent implementation contract be sent to Codex.

## 12. Epistemic boundary

**FACT:** source-aware code-contract verification established the findings above within its bounded inspected surface.

**INFERENCE:** a bounded implementation contract can now be specified.

**DESIGN JUDGMENT:** require declaration + evidence + readiness/governance at eligibility, with a governed acquisition path.

**UNPROVEN:** actual implementation correctness, machine-ID equivalence, current realization satisfaction, runtime containment, and learned reuse.

**LEARNING:** not demonstrated.

## 13. Stop condition

No implementation.
No runtime.
No tests.
No machine-ID promotion.
No capability namespace unification.
