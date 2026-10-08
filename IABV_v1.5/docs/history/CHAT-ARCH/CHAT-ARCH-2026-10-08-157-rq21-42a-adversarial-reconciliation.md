# CHAT-ARCH 2026-10-08-157 — RQ21.42A ADVERSARIAL RECONCILIATION

## 1. Status

RQ21.42A = **PASS WITH BOUNDED REPAIRS / IMPLEMENTATION NOT READY**.

The Sonnet/Claude source-aware adversarial challenge materially validates the shape of the RQ21.42 code-facing proposal, but it also establishes that the proposal cannot be implemented verbatim against the current readiness vocabulary and selection graph.

This record supersedes the routing pointer that treated RQ21.42 as merely awaiting adversarial review.

Executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

The inspected adversarial pass was read-only/static. No runtime, tests, executable-source edits, or implementation were performed.

## 2. Reconciled verdict

### FACT

The current code-facing proposal cannot yet be treated as an implementation contract because:

1. the readiness producer has semantic fallthroughs that can manufacture concrete-looking capability identity from uncertainty;
2. the current selection graph has multiple realization/fallback routes and no single already-existing hard capability gate;
3. `ToolTaskStatus.DEFERRED` exists but is not currently proven to propagate a known-demand/no-realization outcome;
4. the current session-reachable readiness IDs do not presently provide a validated functional capability namespace for the target `tools.*` / `system.metacognition` task population;
5. `ToolCard.capabilities` is heterogeneous and cannot safely be promoted to the abstract realization vocabulary.

### INFERENCE

A bounded extension is still sufficient in principle. No second router, universal capability registry, or new readiness subsystem is justified by the evidence.

### DESIGN JUDGMENT

The first implementation slice should not authorize any capability ID merely because it exists in `CapabilityReadiness.capability_id`.

Reuse of the readiness-ID namespace is conditional: an ID becomes authoritative only after an explicit semantic/domain decision establishes that it denotes a realization-independent functional capability rather than readiness, availability, site context, governance, or an empty fallback label.

### UNPROVEN

- exact capability demand for `tools.local_workflow`;
- exact capability demand for `tools.sandbox`;
- exact capability demand for `system.metacognition`;
- whether any existing readiness ID is the correct abstract capability identity for those tasks;
- exact common implementation choke point after the domain contract is fixed;
- whether a first slice can legitimately omit envelope dimensions for the chosen domain capability.

## 3. Capability-ID adjudication

The adversarial source pass classifies the current readiness IDs into distinct semantic classes.

Safe reuse candidates are **bounded, not globally authorized**.

Most important correction to RQ21.42:

> The existence of a readiness ID is not evidence that the ID is a capability identity.

Current examples separate into:

- plausible functional capability: `browser.generic.navigation`;
- functional capability with site specialization: `browser.search.google`;
- mixed task/site/session evidence: `wplay.login`, `wplay.navigate.casino`, `wplay.session.restore`;
- environment/availability/precondition semantics: `tools.local.registry`, `tools.local.execution`, `tools.local.sandbox`;
- concrete-looking fallthrough labels without established functional semantics: `assistant.local.chat`, `knowledge.query.local`, `customer.support.local`, `analytics.report.local`, `project.review.local`, `research.local.memory`.

Therefore:

**Do not put `tools.local.*` into R_task merely because the readiness service emits them.**

**Do not use `assistant.local.chat` as an UNKNOWN sentinel.**

**Do not infer a universal capability vocabulary from literal string overlap with `ToolCapability` or `ToolCard.capabilities`.**

A further operational limitation remains: the functionally plausible browser/readiness IDs do not reach the focal session execution population that needs the new contract. This means that namespace reuse is not yet useful as an implementation authorization for the current `tools.*` frontier.

## 4. Demand placement

The semantic requirement remains pre-selection and must later be persisted on `ToolTask`.

The adversarial comparison supports this bounded rule:

`semantic/domain interpretation → typed demand on the request before selection → eligibility/routing → realization → task persistence`.

Do not reuse `goal_parameters` as the authoritative semantic contract merely because it transports arbitrary values.

Do not use `ToolTask` as the origin because selection occurs before task construction in the focal path.

The exact typed field/model placement is still open. The most conservative source-compatible direction is a typed demand value carried by the request before selection, with the final task storing the frozen copy that actually authorized the decision.

## 5. Hard-gate reconciliation

There is no single pre-existing common choke point covering every current realization path.

The minimal conceptual requirement is two-stage:

1. candidate eligibility before ranking/selection;
2. final resolution guard before a concrete card becomes authoritative.

The source pass identifies bypass classes that must be closed, including:

- explicit tool preference;
- external preference/decision paths;
- Synaptic authority;
- lexical revival;
- family fallback / registry enumeration;
- `ToolRegistry.pick_card_for_task` resolution, including the existing first-card path.

The important method correction is:

> A hard capability rule is not implemented merely because one selector filters candidates.

Every route that can produce a concrete realization must either consume the same eligibility result or be forced through a resolver that re-applies the invariant.

No source evidence currently authorizes choosing a single line and declaring the bypass problem solved.

## 6. UNKNOWN / AMBIGUOUS / EMPTY

This distinction is now mandatory at the code-facing seam.

- **UNKNOWN** = no complete justified requirement set; a necessary lower bound may exist but cannot certify sufficiency.
- **AMBIGUOUS** = at least two complete plausible requirement sets remain.
- **EMPTY_CAPABILITY_DEMAND** = an explicit success-predicate judgment that this capability dimension requires no functional competence.
- **absence of a mapped readiness ID** is none of the above by itself.

The current readiness fallthrough to `assistant.local.chat` is therefore semantically invalid for demand construction.

Likewise, "no capability was derived" must not be silently equated with EMPTY. Lack of knowledge and a proved empty demand are different states.

## 7. Negative outcome / DEFERRED

`ToolTaskStatus.DEFERRED` is a reusable state candidate, not a proven propagation path.

The main bypass hazard is the present meaning of an empty `tool_id`: it can trigger unconstrained card resolution.

Therefore any future implementation must guarantee:

`KNOWN demand + eligible set = ∅ → governed negative`

and must prevent:

`KNOWN demand + eligible set = ∅ → clear tool id → generic fallback`.

This requires guarding both the final resolver and any earlier revival/fallback route that can replace an excluded realization.

No implementation is authorized yet.

## 8. Realization declaration

The adversarial result supports the separation:

`ToolCard.capabilities` = existing heterogeneous/action-oriented labels

versus

`ToolCard.realizes_capability_ids` = explicit abstract realization declaration.

This is a bounded extension, not a reinterpretation of the existing list.

The declaration must be manually authored/validated for the selected first-slice domain. It cannot be derived automatically from:

- `ToolActionType`;
- `ToolCapability`;
- `AssistantStrength`;
- provider identity;
- current availability;
- readiness score.

A declaration is also not evidence. Existing validation/availability/success evidence remains a separate readiness/evidence layer.

## 9. Envelope decision

The adversarial review does **not** justify a full envelope ontology in the first slice.

However, it also does not justify pretending that capability identity alone is universally sufficient.

Therefore the envelope remains deferred until a human/domain capability is selected and its determinant dimensions are known.

Potential dimensions already represented elsewhere — site, governance, approval, write effects, channel/human-in-the-loop — must remain separate from abstract functional identity unless the domain contract proves that a particular dimension is functionally determinant.

## 10. Reuse-first matrix after RQ21.42A

| Layer | Reconciled treatment |
| --- | --- |
| Semantic demand | bounded EXTEND |
| Capability identity | **CONDITIONAL REUSE**, pending domain adjudication |
| Readiness/evidence | REUSE |
| ToolCard realization declaration | bounded EXTEND |
| Selection | WIRE/REPAIR existing selector + resolver paths |
| Negative outcome | WIRE/REPAIR existing DEFERRED state |
| Observation/result linkage | REUSE task/result linkage; learning remains unproven |

No new universal capability registry is justified.

## 11. First open causal edge

The previous open edge was expressed as code-facing semantic translation.

RQ21.42A moves it one step upstream:

`domain operation / success predicate → realization-independent functional capability identity → R_task for the target task population`.

The unresolved question is now normative/domain-specific, not another generic source-archaeology question.

This is the point at which further broad Codex archaeology would have diminishing information value.

## 12. Required domain adjudication

The minimum next decision is not "which model field should be added?"

It is:

> For each target task family, what functional competence is actually necessary for success, independent of which tool eventually realizes it?

The first bounded table should cover only:

1. `tools.local_workflow`;
2. `tools.sandbox`;
3. `system.metacognition`.

For each, adjudicate:

- success predicate;
- concrete operation(s);
- whether capability demand is KNOWN, UNKNOWN, AMBIGUOUS or EMPTY;
- capability identity if KNOWN;
- determinant dimensions, if any;
- one positive realization example;
- one negative realization example;
- whether the candidate capability is realization-independent.

Do not define a universal ontology. Do not add capabilities merely to fill missing implementation slots.

## 13. Next routing

**NEXT ACTOR: HUMAN / DOMAIN OWNER**, with ChatGPT acting as coordinator and contract recorder.

Reason:

- the remaining uncertainty is normative functional meaning;
- source archaeology has already bounded the available representations;
- Sonnet/Claude has independently challenged the code-facing contract;
- Codex implementation work is blocked until the domain table closes the capability identity for at least one target task family.

After domain adjudication:

**NEXT ACTOR: SONNET/CLAUDE** for one focused semantic falsification of the adjudicated capability table, not another general code archaeology pass.

Only after that should **CODEX** receive an implementation-contract prompt.

## 14. Knowledge / Method / Routing Delta

### Knowledge Delta
- readiness ID, capability identity, availability and governance are empirically mixed in the current producer;
- current session-reachable readiness does not yet expose a validated functional capability namespace for the target tools.* task population;
- ToolCard action labels are not an abstract realization vocabulary;
- the selection graph has multiple bypass routes and DEFERRED is currently unconsumed.

### Method Delta
- capability-ID reuse now requires semantic class adjudication before implementation;
- "no mapped capability" must never be silently converted to UNKNOWN, EMPTY, or a concrete fallback without an explicit contract;
- hard eligibility is an invariant over the complete realization graph, not a feature of one selector;
- bounded negative source evidence must remain bounded.

### Routing Delta
- stop generic Codex archaeology for the current semantic question;
- route the next material decision to a human/domain actor;
- then route the minimal adjudication artifact to Sonnet/Claude;
- only after semantic closure route a minimal implementation contract to Codex.

## 15. Developmental status

Implemented: **NO**.

Proven: **static source findings above, within the bounded inspected surface**.

Causally proven capability learning: **NO**.

Learning/reuse remains future work. Persisting this record only creates canonical memory; it does not demonstrate that IABV learned.

## 16. Explicit stop condition

No implementation, runtime experiment, scoring change, capability-ID promotion, or namespace unification is authorized by this record.
