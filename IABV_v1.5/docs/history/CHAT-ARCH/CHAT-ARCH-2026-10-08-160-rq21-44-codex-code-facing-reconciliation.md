# CHAT-ARCH 2026-10-08-160 — RQ21.44 CODEX CODE-FACING RECONCILIATION

## 1. Status

RQ21.44 = **READY FOR MINIMAL CODE CONTRACT**.

The source-aware Codex reconciliation confirms that the semantic contract for `C_SANDBOX_DYNAMIC_VALIDATION` is sufficiently mapped to specify a bounded implementation contract for independent review.

This is **not implementation readiness**.

No machine-readable capability ID is authorized. No current ToolCard is proven to satisfy the complete capability. The existing selection graph does not enforce the complete demand-to-realization invariant.

Executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

The reconciliation was source-only. No implementation, runtime execution, or tests were performed.

## 2. Machine identity

The following existing identifiers are **not** semantically safe as the machine identity for `C_SANDBOX_DYNAMIC_VALIDATION`:

- `tools.local.sandbox` = readiness derived from available cards with `supports_sandbox`; it is inventory/readiness dependent.
- `tools.local.execution` = availability of local cards; it does not imply validation.
- `tools.local.registry` = inventory existence/precondition.
- browser readiness IDs are unrelated to dynamic candidate validation.
- `ToolCapability.TOOL_SANDBOX` is a broad routing enum and is not proven equivalent.

Therefore:

**Semantic capability closed; existing machine ID unresolved.**

Any future machine ID requires explicit semantic authorization. Do not select one by string similarity.

## 3. Demand placement

The earliest typed request object on the focal selection path is `InferenceRequest`. It carries the request before candidate selection, while `ToolTask` is constructed after realization selection.

Current source facts:

- `InferenceRequest` has `user_goal`, `allowed_tools`, and generic `goal_parameters`, but no typed demand/envelope.
- `AdaptiveSession` carries intent and parameters; `build_task_for_session()` reconstructs the request but does not currently preserve an independently typed validation demand.
- `build_task_from_request()` resolves suggested/explicit realization information before task construction.
- `ToolTask` has no first-class required capability/demand state/`E`/`X` contract.

Minimal code-contract consequence:

`InferenceRequest` (or a tightly bounded typed value carried by it) is the pre-selection demand carrier.

The frozen demand must later be echoed into `ToolTask`.

`ToolTask` is persistence/evidence linkage, not demand source.

## 4. Realization declaration

Existing `ToolCard.capabilities` is heterogeneous/action-oriented and cannot serve as the abstract capability realization vocabulary.

`CapabilityDescriptor` exists structurally but has no bounded operative producer/consumer in Python source.

Therefore the minimal realization contract remains a distinct declaration equivalent to:

`ToolCard.realizes_capability_ids: list[str]`

This is a bounded schema extension.

The declaration must be curated, not derived automatically from action enums, card labels, provider identity, adapter identity, availability, or readiness.

Important evidence limitation:

No inspected card was proven to realize the complete sandbox capability.

Examples:

- `playwright_browser` = possible candidate, but current evidence does not establish protected-effect containment `E` or validation against expected behavior `X`.
- `shell_command` = negative on current evidence; `sandbox=True` does not contain `subprocess.run()`.
- `ollama_llm`, `github_api`, external-assistant cards and `gh_cli` = negative or insufficient for the complete dynamic-validation contract on inspected evidence.
- `devin_api` = no evidence of protected-effect containment or expected-behavior validation.

Thus declaration ≠ proof.

## 5. Hard eligibility

No single existing selector filter currently enforces the invariant across all realization paths.

The source graph contains:

- candidate filtering in `InteractionModeSelector`;
- external preference;
- Synaptic authoritative selection;
- explicit/suggested tool preference;
- lexical revival;
- assistant-family fallback;
- `ToolRegistry.pick_card_for_task()` explicit/assistant/lexical/first-card resolution.

The best existing final enforcement seam is the call to `pick_card_for_task()` immediately before adapter execution, but that seam currently receives a `ToolTask` without a typed capability demand.

Minimal contract therefore requires two controls:

1. capability eligibility before ranking/candidate choice;
2. a final demand-aware resolver guard before an actual card reaches its adapter.

All preference and fallback routes must remain subordinate to the same invariant.

Candidate filtering alone is insufficient.

## 6. Deferred negative outcome

`ToolTaskStatus.DEFERRED` exists but is not a proven operational path.

Current facts:

- no producer/consumer of `DEFERRED` was found in the bounded production search;
- `ToolTask.status` defaults to `PENDING`;
- execution failure currently produces a blocked `ToolResult`, not a known-demand deferred task;
- empty `tool_id` can allow generic registry fallback.

Minimal future contract:

`KNOWN demand + eligible set = empty → governed negative outcome`

and never:

`KNOWN demand + eligible set = empty → generic fallback`.

The negative path must preserve demand and unmet reason and stop before adapter execution.

## 7. Envelope E / expected behavior X

Current source structures do not represent the complete sandbox contract.

Facts:

- `ToolTask.expected_outcome` exists but the generic validator does not consume it as an expected-behavior predicate;
- `execution_scope` is coarse read/write/destructive scope;
- `sandbox_first`, `supports_sandbox` and approval fields describe policy/governance/readiness rather than the protected-effect set `E`;
- `ToolValidator` derives validation from `result.success`, not from comparison with expected behavior `X`.

Therefore the minimum envelope decision is:

**BOUNDED EXTEND**

The contract needs explicit task inputs corresponding to candidate, expected behavior `X), and protected effects `E), without promoting those dimensions to capability identity.

## 8. Reuse-first matrix

| Layer | Classification |
|---|---|
| semantic capability meaning | CLOSED / DO NOT CHANGE |
| machine capability identity | BOUNDED EXTEND |
| request-side demand | BOUNDED EXTEND |
| ToolTask persistence | BOUNDED EXTEND |
| ToolCard realization declaration | BOUNDED EXTEND |
| candidate eligibility | EXTEND |
| final resolution guard | WIRE-REPAIR |
| DEFERRED propagation | EXTEND |
| readiness/evidence | REUSE |
| universal registry/router | SHOULD NOT BE ADDED |

## 9. Minimal implementation contract

A later implementation prompt may require exactly:

1. **Authorized machine ID**
   - must be supplied/approved independently;
   - must semantically denote `C_SANDBOX_DYNAMIC_VALIDATION);
   - no reuse of the three `tools.local.*` IDs without explicit semantic reauthorization.

2. **Typed pre-selection demand**
   - exists before candidate enumeration and preference resolution;
   - carries the known capability requirement;
   - preserves demand-state semantics;
   - carries `E` and `X` as task inputs;
   - survives session→request projection;
   - is echoed/frozen on `ToolTask`.

3. **Independent realization declaration**
   - separate from `ToolCard.capabilities`;
   - curated for each realization;
   - not inferred from labels or provider;
   - never treated as evidence by itself.

4. **Hard eligibility**
   - filter candidates before ranking;
   - enforce again at the final card-resolution seam;
   - constrain explicit preference, external preference, Synaptic routing, family fallback, lexical revival and first-card fallback.

5. **Governed negative**
   - known demand with no eligible realization cannot execute;
   - no unconstrained fallback;
   - preserve demand + unmet reason;
   - defer/blocked outcome must be explicit.

6. **Dynamic validation**
   - candidate and expected behavior `X` are inputs;
   - protected effects `E` are task-envelope inputs;
   - dynamic execution is required;
   - evidence must cover both observed behavior and non-occurrence of protected effects;
   - pass/fail must be interpreted against `X);
   - `sandbox=True`, `ToolResult.success` or `validated=True` alone do not prove the contract.

## 10. Remaining uncertainty

- exact authorized machine ID;
- whether any current card can actually realize the complete capability;
- exact shape of `E` and `X` in the bounded implementation;
- exact cross-route wiring required to guarantee the hard invariant;
- precise DEFERRED persistence/consumer behavior;
- runtime evidence of actual containment and validation.

These are implementation/evidence uncertainties, not unresolved semantic meaning.

## 11. Next actor

**SONNET/CLAUDE — independent code-contract verification.**

The next review should test whether this minimal contract is internally consistent with the source findings and whether any repair is still required before a Codex implementation prompt is issued.

Do not select a machine ID during that review.
Do not implement.
Do not execute runtime.

## 12. Epistemic boundary

**FACT:** source mapping above was established in the bounded read-only reconciliation.

**INFERENCE:** a bounded code contract is now definable.

**DESIGN JUDGMENT:** use a distinct realization declaration and two-stage eligibility enforcement.

**UNPROVEN:** implementation correctness, machine-ID equivalence, current realization capability, containment, runtime validation, and learned reuse.

**LEARNING:** not demonstrated.
