# CHAT-ARCH 2026-10-08-158 — RQ21.43 HUMAN CAPABILITY ADJUDICATION

## 1. Status

RQ21.43 = **PARTIALLY CLOSED / DOMAIN ADJUDICATION ACCEPTED**.

Human/domain adjudication is now authoritative for the bounded semantic question addressed here. It closes one target task family as a realization-independent functional capability and deliberately leaves two families ambiguous.

This is a semantic contract decision, not implementation evidence.

Executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

No runtime or executable-source change was made.

## 2. Adjudicated results

| Task family | Demand state | Adjudicated capability position |
|---|---|---|
| `tools.local_workflow` | **AMBIGUOUS** | No single capability may represent the whole family; capability depends on the concrete functional operation and success predicate. |
| `tools.sandbox` | **KNOWN** | **Evaluate a candidate execution under effective isolation and produce an observable validation result.** |
| `system.metacognition` | **AMBIGUOUS** | At least three materially different metacognitive operations remain plausible; no single capability is yet authorized. |

## 3. Key semantic rule now adjudicated

`family / intent` is not equivalent to `capability`.

The semantic path is:

`concrete functional operation + success predicate → abstract capability → R_task`.

Capability identity must remain independent of:

- tool ID;
- provider;
- adapter;
- readiness status/score;
- availability;
- permission;
- execution scope.

Where a task family contains materially different functional effects, the family remains AMBIGUOUS until the concrete operation disambiguates demand.

## 4. tools.local_workflow

### Demand state
**AMBIGUOUS**.

The family label does not determine one functional competence. Candidate operations include reading/observing, modifying, executing, transforming, and other effects that can require different capabilities.

Therefore:

`tools.local_workflow → capability = tools.local_workflow`

is rejected.

The family remains an intent/task-family classifier, not an abstract capability identity.

A future concrete task must derive capability demand from its actual functional operation and success predicate.

## 5. tools.sandbox

### Demand state
**KNOWN**.

Adjudicated functional capability:

> Evaluate a candidate execution under effective isolation and produce an observable validation result.

Minimum functional components:

1. execute a candidate operation under controlled conditions;
2. prevent the externally protected effect the test is intended to avoid;
3. observe the resulting behavior;
4. produce an interpretable pass/fail validation result against the expected behavior.

The capability is realization-independent.

`tools.local.sandbox` is **not** adopted as the authoritative abstract identity because the existing ID mixes functional semantics with `local` context.

The capability itself is not defined by a particular sandbox mechanism, provider, adapter, tool card, readiness state, or permission state.

A realization that can execute directly against the protected real environment without effective isolation is a negative realization even when available and authorized.

## 6. system.metacognition

### Demand state
**AMBIGUOUS**.

The current family admits at least these materially distinct functional operations:

1. auto-observation / evaluation of current system state;
2. pre-action metacognitive discernment over evidence, contradictions, confidence, and risk;
3. reconstruction and communication of the system's own progress/evolution.

These cannot be collapsed into one capability without a further functional decision.

Existing names such as `system.metacognition`, `system.self_awareness`, `assistant.local.chat`, `TaskRole.TOOL_USE`, and `MetacognitiveDiscernmentFrame` are not authorized as abstract capability identity merely because they are related in name or structure.

## 7. Envelope / determinant dimensions

For `tools.local_workflow`, the functional effect on the target is determinant: reading, modification, execution, transformation, etc. are different demands.

For `tools.sandbox`, effective isolation and sufficient observability are determinant to the success predicate. `local`, provider, adapter and permission are not capability identity.

For `system.metacognition`, the object of self-evaluation and the functional purpose remain determinant because they distinguish the unresolved candidate operations.

No universal envelope ontology is introduced by this decision.

## 8. Consequence for R_task

The adjudication licenses the following bounded semantic consequence:

For a concrete sandbox-validation task whose success predicate matches the adjudicated definition:

`R_task = {C_SANDBOX_VALIDATION}`

where `C_SANDBOX_VALIDATION` is a semantic capability label representing:

`evaluate candidate execution under effective isolation + produce observable validation result`.

The exact machine-readable ID is **not yet authorized**. A human semantic decision exists, but the mapping to an existing canonical ID or a narrowly introduced implementation ID still requires independent falsification and code-facing reconciliation.

This distinction is deliberate:

human semantics are closed for the capability meaning; machine vocabulary is not yet globally promoted.

## 9. Reuse-first implication

- Semantic demand: existing task/session/request structures remain possible transport locations; implementation placement is not yet frozen.
- Capability identity: reuse is **not** yet authorized by string coincidence. The sandbox capability needs a canonical machine ID after semantic review.
- Readiness/evidence: reuse `CapabilityReadiness` remains valid as evidence/readiness only.
- ToolCard realization declaration: still a bounded extension candidate.
- Selection: existing selector/resolver paths remain the operative wiring surface.
- Negative outcome: existing `DEFERRED` remains a candidate but is not yet proven wired.

## 10. Knowledge Delta

- Human/domain meaning now closes one capability contract: sandbox validation under effective isolation with observable result.
- `tools.local_workflow` is confirmed as a family whose capability demand must be operation-specific.
- `system.metacognition` remains a family with multiple plausible capability demands.
- Domain semantics and machine capability vocabulary are now explicitly separated.

## 11. Method Delta

- When the semantic question is normative, the domain owner resolves meaning before implementation.
- A semantic capability may be closed while its machine ID remains unpromoted.
- A task-family label is never promoted directly to abstract capability identity.
- UNKNOWN and AMBIGUOUS remain different: this result uses AMBIGUOUS when multiple complete functional interpretations are known.

## 12. Routing Delta

Next actor is **SONNET / CLAUDE** for an independent, source-aware semantic falsification of the adjudicated table.

Scope must be limited to:
- test whether the sandbox capability is truly realization-independent;
- test whether its determinant dimensions can be separated from readiness/governance;
- test whether `tools.local_workflow = AMBIGUOUS` is justified;
- test whether `system.metacognition = AMBIGUOUS` is justified;
- identify the minimum counterexample that would invalidate any row.

Do not reopen generic source archaeology.
Do not implement.

After semantic falsification, if the sandbox row survives, route to CODEX for a code-facing implementation-contract reconciliation specifically around that one closed capability.

## 13. Epistemic boundary

**FACT / DOMAIN DECISION:** the table and definitions in this record were explicitly adjudicated by the human/domain owner.

**INFERENCE:** the sandbox definition is a viable realization-independent capability contract.

**UNPROVEN:** that any current ToolCard actually realizes the capability; that any current readiness ID is the correct machine ID; that the selector enforces the resulting contract; that runtime evidence will validate the route.

**LEARNING:** not demonstrated. Canonical storage is memory, not learning.

## 14. Stop condition

No implementation, runtime experiment, scoring change, or global capability-namespace promotion is authorized by this record.
