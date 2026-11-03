# RSK-01 — Currentness, Provenance, and Candidate-Adjudication Contract Review

**Date:** 2026-10-29  
**Task ID:** `RSK01_CURRENTNESS_CONTRACT_REVIEW_20261029`  
**Status:** `ARCHITECTURE_CONTRACT_CANDIDATE / REVIEWED_STATICALLY / NOT_IMPLEMENTED`  
**Repository:** `jhonf463r/Python`  
**Observed main baseline:** `1430ad5062298a8dd5719ccb2882e2ce4877b283`  
**Related records:** [Corpus/currentness coverage delta](./CHAT-ARCH-2026-10-29-RSK-01-CORPUS-CURRENTNESS-COVERAGE-DELTA.md); [Candidate-set fixture matrix](./CHAT-ARCH-2026-10-29-RSK-01-CANDIDATE-SET-CURRENTNESS-FIXTURE-MATRIX.md)

## 1. Purpose and boundary

This review turns the RSK-01 static findings and proposed fixture matrix into a falsifiable architecture contract. It does not claim the current implementation already satisfies the contract.

This is a documentation-only candidate on the existing RSK-01 branch. It does not authorize or perform product changes, tests, builds, runtime execution, deployment, MCP/stdio configuration, protected reads, changes to `CURRENT-STATE.md`, or changes to G1/G2/G3. It neither owns nor replaces `COORD-OVERLAP-AUDIT-20261029`, MCO-01, or the separate G1/G2/G3 lane.

## 2. Review decision

**Decision: retain the matrix as a useful specification, with the clarifications below; do not implement a new organ on the current evidence.**

The static source review supports two distinct concerns:

1. **Candidate coverage/composition:** the inspected consumers build their candidate sets through different repository queries, caps and caller-provided document lists. The bounded evidence does not demonstrate that canonical project documents and operational knowledge form one shared candidate universe.
2. **Candidate semantics/adjudication:** the inspected shared model does not require consistent source-revision, authority, validity/supersession and typed-relation semantics, and the inspected repository search does not adjudicate those semantics.

The matrix is appropriately designed to distinguish those concerns. One successful consumer path must not be taken as proof that another path sees the same sources; equally, different candidate sets are not automatically a defect when their task scopes intentionally differ.

**Commonality must be required for source semantics, provenance, and explainable adjudication—not blindly identical candidate lists.**

A global graph, universal index, new registry, or new “brain” is not justified. First establish whether existing source owners and consumers can carry and honor the contract when composed.

## 3. Contract objective

For a pinned objective and a declared consumer, IABV should be able to explain:

- which source artifacts and semantic claims were eligible;
- which candidate records were generated and which candidate sources were not in that consumer's universe;
- the exact source revision observed, where available, and whether that observation is still suitable for the question;
- the scope and authority of each source for that question;
- how historical, superseded, unresolved, duplicate, or contradictory material was handled;
- why each candidate was selected, downgraded, rejected, or left unresolved; and
- which selected evidence supports the resulting answer or decision, without implying more than that evidence proves.

The target is a reproducible and auditable candidate-adjudication path, not a claim that every possible artifact must always be loaded into active context.

## 4. Minimal semantic contract to evaluate

This list defines the meanings the system must preserve. It does **not** mandate a new class, table, service, database, or serialization format. Existing owner schemas may satisfy it if evidence shows that the values are populated and consistently honored end to end.

| Contract element | Minimum meaning | Fail-closed interpretation when missing |
|---|---|---|
| Candidate identity | Stable identifier for the candidate claim/record, distinguishable from the source artifact identity | Do not count repeated appearances as independent evidence merely because they have different record IDs |
| Source identity | Source kind and a resolvable artifact reference; canonical path/reference where applicable | Mark source as unresolved/unverifiable if its target cannot be located |
| Source revision | Repository commit plus exact blob/content digest when the source is versioned; otherwise the strongest available immutable version reference | Do not assert currentness from an unpinned historical capture |
| Observation time | Time the source was observed/captured, distinguished from record creation/update time and from the event time the content describes | Treat unknown temporal status as unverified, not current |
| Authority and scope | Which source governs which question/domain and what its evidence can establish | Do not let lexical rank, repetition, or update time overrule an explicit canonical authority rule |
| Lifecycle/currentness | At least the ability to distinguish current, historical, superseded, unresolved, contradicted, and unverified material, whether represented as fields or derived decisions | Keep an unknown state unresolved; do not silently promote it to current |
| Typed relations | Expressible links such as `supersedes`, `contradicts`, `derived_from`, `supports`, and `references`, with source/claim endpoints | Do not infer supersession or independent corroboration from text similarity alone |
| Evidence scope | The exact claim and bounded conclusion supported by the source, including the baseline and limitations of historical audits | Do not convert a bounded static observation into proof of universal absence or current runtime behavior |
| Consumer trace | Consumer identifier/path, input candidate IDs, selected/rejected output and rationale | If coverage was not observable, report `NOT_OBSERVED`; do not infer absence |
| Answer/decision trace | Link from selected candidates to the answer, routing choice, or other decision they support | Do not claim a provenance-complete answer when the link is unavailable |

A generic `payload` or `metadata` map can physically store extra values but does not, by itself, satisfy this contract. To count as satisfying it, evidence must show consistent production, validation and consumption of those semantics across the relevant path.

## 5. Authority and ranking rule

Candidate ranking may order candidates **within** a compatible authority/currentness class. Ranking alone must not decide canonical authority or turn stale evidence into current evidence.

For questions about the active route, a result must be bound to the exact pinned `CURRENT-STATE.md` source revision and respect the declared current-state authority boundary. An archived route, historical handoff, old audit, or duplicate statement may be relevant historical evidence, but it must not displace current routing authority merely because it contains a more prominent lexical match, appears repeatedly, or has a later operational record-update timestamp.

This example is specific to the repository's existing routing protocol. It is not a claim that one document must govern unrelated technical domains.

If two sources make incompatible claims and the authority rule cannot resolve them, the result must surface the conflict as unresolved and preserve both source identities. It must not invent a reconciliation or suppress the less convenient source.

## 6. Candidate-universe and consumer contract

Evaluate the same frozen fixtures against the declared consumers independently:

- `TaskContextAssembler._knowledge_hits()`;
- `LocalRoleRouter._route_knowledge()`;
- `CustomerSupportService.build_context()`;
- `SystemIdentityRegistry.current_snapshot()`;
- the relevant `DecisionAuditTrail` and `CodeAuditTrail` surfaces.

For each consumer, record its actual input universe before ranking, candidate IDs and order after retrieval/ranking, provenance retained or lost, rejected/omitted candidates and the reason. Where a source is outside the path's candidate universe, use `NOT_IN_CANDIDATE_UNIVERSE`; where the path was not inspected or could not be observed, use `NOT_OBSERVED`. Do not collapse these states into “the source does not exist.”

A consumer may intentionally serve a narrower domain or use a different result limit. That is not automatically a failure. It becomes a composition failure when a source is required for that objective, is available to the declared system boundary, and is omitted or semantically degraded without a documented scope reason.

A shared candidate service is only one possible implementation. The contract can also be satisfied by reusable owner APIs and thin composition layers, if their behavior is demonstrably consistent. Architecture choice follows evidence; the contract does not prescribe a new organ.

## 7. Acceptance criteria for a future controlled evaluation

These are qualitative acceptance criteria, not results. The current fixture matrix is **not executed**, and no pass/fail values are asserted here.

| ID | Criterion | Minimum evidence needed |
|---|---|---|
| AC-01 | Revision-bound current-source answer | The selected source reference matches the pinned revision/blob; final answer records that reference |
| AC-02 | Historical/current separation | Historical route evidence remains marked historical and does not displace the pinned active route |
| AC-03 | Stale-source detection | A candidate captured from another revision is rejected for current-route use or explicitly labeled stale/historical pending refetch |
| AC-04 | Negative-knowledge fidelity | Unresolved/negative claims retain their scope and are not misrepresented as definitive positive facts |
| AC-05 | Conflict handling | Contradictory sources remain visible with source identity and an explicit authority decision or unresolved status |
| AC-06 | Duplicate independence | Repeated mentions of one lineage do not inflate independent evidence counts or confidence |
| AC-07 | Schema honesty | The answer distinguishes required first-class fields from optional `payload`/`metadata` and from runtime population |
| AC-08 | Consumer-level coverage | For every consumer and query, the candidate universe and retrieval outcome are observable or explicitly marked `NOT_OBSERVED` |
| AC-09 | Reasoned exclusion | A missing expected candidate has an evidence-based exclusion/coverage reason rather than an invented explanation |
| AC-10 | Bounded conclusions | Historical static audit findings retain target revision and limitations; no unsupported claim of runtime or universal absence is made |
| AC-11 | Traceable decision | Evidence selected for the output can be traced from source revision through candidate selection to the answer/decision |
| AC-12 | Reproducibility | Fixture revision, inputs, consumer path, candidate IDs/order and adjudication outcome are recorded so an independent review can repeat the case |

Only after the actual observations are available should quantitative metrics be computed. Candidate recall/precision, stale inclusion, duplicate amplification, provenance completeness, conflict adjudication and latency are useful measures, but their denominators and expected sets must be independently fixed before execution. Do not choose thresholds after seeing the outputs merely to turn the result green.

## 8. How to interpret outcomes without jumping to architecture

| Observed outcome | Supported diagnosis | Not yet supported |
|---|---|---|
| Required source never enters one relevant candidate universe | Coverage/ingestion/composition gap for that source and consumer path | That a new global index is required |
| Candidate arrives but source revision/currentness is unknown or wrong | Provenance/currentness contract gap | That the storage engine itself must be replaced |
| Current and historical items are both visible but the older item wins solely by rank/update time | Authority/canonicalization gap | That a graph database is necessary |
| Source is selected but the final answer overstates what it proves | Evidence-scope/adjudication gap | That more retrieval volume will fix it |
| Consumer outputs differ because their domains/limits are intentionally different and semantics are preserved | Potentially valid consumer-specific behavior | That candidate lists must be made identical |
| Consumers have incompatible behavior with no documented scope distinction | Shared-composition or owner-contract gap | That the first remedy must be a new service |
| Existing organs can express and expose the needed source and relation semantics but consumers do not compose them | Prefer connecting/composing existing owners | Need for a second authority/brain |
| A specific required responsibility cannot be represented or enforced by any inspected existing owner, after an authorized discriminating evaluation | Evidence to consider a narrow ownership gap | Automatic authorization to implement a new organ |

## 9. Revised evaluation protocol

When a separate execution authorization is granted, the evaluator should:

1. Pin the then-live `main` SHA and re-fetch each fixture, recording exact blob/content identities. If any fixture changed, update the expectation before execution and record why.
2. Freeze the query wording, expected semantic candidates, authority rule, consumer list and criteria before observing outputs.
3. Run each fixture/query/consumer combination once, preserving the initial outputs and failures. Do not silently rerun or tune until green.
4. Capture candidate universe, retrieval/ranking output, source revision, currentness/authority classification, exclusions, rationale, final answer/decision and trace completeness.
5. Score the result against the predeclared criteria; label unobservable paths as such. Keep static evidence separate from runtime behavior and separate from conclusions about all repository paths.
6. Produce a decision record selecting one next path: close as existing composition adequate; repair a bounded source/consumer contract; perform a narrower follow-up audit; or document an evidenced ownership gap for owner review.

This protocol is a future plan only. It does not authorize execution itself.

## 10. Authorization and stop conditions

Current state:

```text
TASK_ID=RSK01_CURRENTNESS_CONTRACT_REVIEW_20261029
TASK_CLASS=STATIC_ARCHITECTURE_CONTRACT_REVIEW
SOURCE_BASELINE=1430ad5062298a8dd5719ccb2882e2ce4877b283
MATRIX=SPECIFIED_NOT_EXECUTED
CONTRACT=DOCUMENTED_AS_CANDIDATE
PRODUCT_CODE=NOT_MODIFIED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP/STDIO/BRIDGE=NOT_USED
CURRENT_STATE=NOT_MODIFIED
G1/G2/G3=NOT_TOUCHED
COORD_OVERLAP_LANE=NOT_TOUCHED
IMPLEMENTATION_AUTHORIZATION=NOT_GRANTED
EXECUTION_AUTHORIZATION=NOT_GRANTED
NEW_ORGAN_REQUIRED=NOT_DEMONSTRATED
NEXT_GATE=OWNER_REVIEW_OF_CONTRACT_AND_SEPARATE_EXPLICIT_AUTHORIZATION_FOR_ANY_EXECUTION
```

Stop the current documentation review here. Do not proceed into product changes, run the matrix, configure the bridge, or merge the candidate without the relevant separate authorization and the current canonical route's applicable controls.

## 11. Result

The RSK-01 lane is **not complete**. Its current safe deliverables are a bounded static source delta, a discriminating but unexecuted fixture matrix, and this candidate contract review. The unresolved question is empirical: do the existing owners and consumers meet the contract when evaluated on frozen fixtures, and if not, where exactly does the first failure occur? Until that is answered with authorized evidence, composition is the preferred hypothesis and a new organ remains unproven.
