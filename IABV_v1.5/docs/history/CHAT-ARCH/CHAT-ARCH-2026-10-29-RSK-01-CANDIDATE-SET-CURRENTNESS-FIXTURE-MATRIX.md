# RSK-01 — Candidate-Set Currentness and Provenance Fixture Matrix

**Date:** 2026-10-29  
**Task ID:** `RSK01_CANDIDATE_SET_FIXTURE_MATRIX_20261029`  
**Status:** `TEST/DESIGN FIXTURE SPECIFICATION ONLY / NOT EXECUTED`  
**Baseline:** `main@1430ad5062298a8dd5719ccb2882e2ce4877b283`  
**Related static result:** [RSK-01 corpus/currentness coverage delta](./CHAT-ARCH-2026-10-29-RSK-01-CORPUS-CURRENTNESS-COVERAGE-DELTA.md)

## 1. Purpose

Make the unresolved RSK-01 currentness/canonicalization question empirically discriminating without creating a new service first.

The fixture matrix is a **future test specification**, not a claim that the cases were run. It uses existing canonical source examples and one deliberately conflicting pair to verify whether an objective-conditioned retrieval path preserves source identity, authority, currentness, negative knowledge and provenance.

No code, tests, build, runtime or MCP operation was performed to create this matrix. The matrix does not authorize those operations.

## 2. Freeze and source manifest

Every execution of this matrix must pin the repository revision and re-fetch the named paths at that revision. These source/blob identifiers are the observations recovered during the static audit; they are not substitutes for revalidation on the day of a later run.

| Fixture ID | Source | Observed blob SHA | Intended semantic type |
|---|---|---|---|
| F1 | `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` | `b5fbf879e95d92869e51fa2ae29d4fce5ca56bdb` | Current canonical routing authority |
| F2 | `IABV_v1.5/docs/history/CHAT-ARCH/UNRESOLVED-KNOWLEDGE.md` | `c14be32f76284675b7d14cc0dc3417c01f926765` | Unresolved/negative knowledge; contains historical route material that is not a replacement for CURRENT-STATE |
| F3 | `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-03-030-RSK-01A-reconciliation.md` | `c2a6f3cbda99978c3f237557b423ff1572f02c3c` | Historical bounded static audit result; scope is tied to its target SHA |
| F4 | `IABV_v1.5/src/iabv_v15/services/system_identity_registry.py` | `8fa7ba60202d947a254352bb1d7927f76becf90a` | Code/source identity and subsystem evidence |
| F5 | `IABV_v1.5/src/iabv_v15/domain/models.py` | `a9033d21052c519e09f482097599c704a62ea916` | Model/schema evidence, including KnowledgeItem and EvidenceRef |
| F6 | F1 paired with the historical route/claim excerpt inside F2 | See F1 + F2 | Deliberately conflicting authority/currentness pair |

Source links:
- [F1 — CURRENT-STATE](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
- [F2 — UNRESOLVED-KNOWLEDGE](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/docs/history/CHAT-ARCH/UNRESOLVED-KNOWLEDGE.md)
- [F3 — RSK-01A reconciliation](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-03-030-RSK-01A-reconciliation.md)
- [F4 — SystemIdentityRegistry](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/services/system_identity_registry.py)
- [F5 — domain models](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/domain/models.py)

## 3. Query matrix and expected adjudication

The expected outcomes are qualitative contract requirements. Do not invent numeric ranking thresholds before observing a real baseline.

| Case | Objective/query | Required relevant candidates | Expected classification and result | Failure that falsifies the current contract |
|---|---|---|---|---|
| Q1 — Current route | “What is the active task and next action on the pinned main?” | F1 first; optionally supporting route/method pointers | Answer must bind to the exact CURRENT-STATE blob and pinned main SHA. Only the top active-route section governs the live route. | A historical record is promoted to current authority, or answer has no revision-bound source. |
| Q2 — Negative/unresolved knowledge | “Which evidence says the canonical claim-to-retrieval edge remains unresolved?” | F2 and/or F3, depending on the exact claim asked | Return the relevant negative claim with its scope and provenance; label unresolved facts as unresolved. | Negative knowledge is omitted despite lexical relevance, or is mistaken for a current task route. |
| Q3 — Historical audit result | “What did RSK-01A establish about N03/R01?” | F3 and relevant dated receipts | State that it was a bounded static finding at its historical target SHA; do not promote it to live runtime proof. | A historical audit result is represented as proof of current runtime behavior or global absence. |
| Q4 — Code ownership | “What does the existing system identity registry represent?” | F4 plus, when helpful, F5 | Distinguish source/subsystem inventory evidence from operational proof or an all-organ semantic graph. | Mere class presence is returned as proof of all runtime dependencies or of a complete retrieval graph. |
| Q5 — Schema/provenance | “What provenance/currentness fields does KnowledgeItem require?” | F5 | Report only first-class declared fields; clearly distinguish them from optional generic payload/metadata. | Optional metadata is falsely described as a required/enforced field, or schema evidence is conflated with runtime population. |
| Q6 — Contradictory current vs historical route | “The current route says D021, but an older archived block names an earlier M1A task. Which governs now?” | F1 and the relevant historical excerpt in F2 | CURRENT-STATE controls current routing; preserve the old record as historical evidence and show the source/version distinction. | Similarity, volume, apparent recency or ranking score causes the historical route to displace F1. |
| Q7 — Duplicate claim | “The same routing claim appears in the current state and a historical audit. Is that two independent confirmations?” | F1 + F3 | Preserve both source identities but canonicalize the semantic claim and scope; do not count duplicate mentions as independent confirmations. | Repetition inflates confidence or evidence count without independent source lineage. |
| Q8 — Stale source revision | Re-run Q1 using a candidate record captured from a different pinned main SHA | F1 from current pinned SHA plus stale record | Mark the stale item historical/stale or reject it for current-route use; require a new fetch before asserting currentness. | A record from a prior main SHA is silently accepted as current. |

## 4. Consumer coverage

The matrix must be evaluated against the candidate sources and consumer boundaries separately. Do not assume one successful route proves another one.

| Consumer/surface | Current source path observed | Required observation |
|---|---|---|
| Task context assembly | `TaskContextAssembler._knowledge_hits()` → `KnowledgeRepository.search()` | Which source classes can enter this candidate set; whether provenance/currentness survives into TaskContext |
| Knowledge role | `LocalRoleRouter._route_knowledge()` → repository shortlist → caller-supplied docs → `EmbeddingIndexService.search()` | Candidate corpus before and after lexical ranking; source identities and rank rationale |
| Customer support role | `CustomerSupportService.build_context()` → repository shortlist → caller-supplied docs → `EmbeddingIndexService.search()` | Whether its narrower document list changes the expected candidate set or currentness outcome |
| System identity | `SystemIdentityRegistry.current_snapshot()` | Whether identity evidence is referenced as evidence or incorrectly treated as retrieved task knowledge |
| Decision/code audit evidence | `DecisionAuditTrail` / `CodeAuditTrail` | How a query points to a specific record, revision and observed scope without implying a universal cross-organ graph |

Record the exact consumer path, input candidate IDs, output IDs/order, source provenance, currentness classification, rejected candidates and reason. If a path cannot access a fixture source, report `NOT_IN_CANDIDATE_UNIVERSE` rather than infer that the source does not exist.

## 5. Minimum candidate envelope to evaluate

This is a contract checklist for review, not an authorization to add fields or a new class. For each candidate, determine whether the existing representation can consistently provide:

- stable identity for the semantic claim and the source artifact;
- source kind, canonical path, exact content/blob SHA and repository revision;
- event/observation time distinguished from record/update time;
- authority class and whether the source is canonical for the question;
- validity/currentness state: current, historical, superseded, unresolved, contradicted, or unverified;
- typed relations such as supersedes, contradicts, derived-from, supports or references;
- evidence adequacy and the specific scope the evidence can establish;
- the consumer that selected/rejected the candidate and the reason;
- traceability from selected candidate to the final answer/decision.

A JSON `metadata` field may physically hold extra values, but passing this checklist requires evidence that values are produced consistently and honored by consumers, not merely that arbitrary metadata can be serialized.

## 6. Metrics to record when execution becomes authorized

Do not invent results now. For a later controlled run, capture:
- `recall@k` and `precision@k` against the independently prepared expected set;
- stale/superseded item inclusion rate;
- duplicate amplification rate;
- provenance completeness and source-revision correctness;
- contradiction detection and authority-resolution correctness;
- latency and candidate-set size per consumer;
- whether the chosen evidence changes the downstream answer/routing decision correctly.

A text hit, successful serialization, persisted artifact or green unit test alone cannot establish end-to-end behavioral correctness.

## 7. Stop and interpretation rules

Stop the first fixture run after all cases are scored and the candidate universe/consumer path is known for each case. Preserve any partial or failed result; do not iterate until it turns green without recording the initial outcome.

Interpretation:
- Source never reaches candidate generation → ingestion/coverage gap for that source and path.
- Source reaches candidates but stale/current authority is misclassified → currentness/canonicalization gap.
- Correct source is selected but evidence/scope is overstated → adjudication/provenance gap.
- Multiple consumers return inconsistent candidate sets with no documented domain reason → shared-composition gap.
- The existing organs can express the needed contract, but the path does not connect them → composition remains the preferred remedy.
- Only if direct evidence shows no existing owner can express a required responsibility may a new component be considered.

## 8. Authorization boundary

```text
FIXTURE_MATRIX=SPECIFIED_NOT_EXECUTED
PRODUCT_CODE=NOT_MODIFIED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_USED
CURRENT_STATE=NOT_MODIFIED
G1/G2/G3=NOT_TOUCHED
IMPLEMENTATION_AUTHORIZATION=NOT_GRANTED
NEXT_GATE=REVIEW_CONTRACT_AND_OBTAIN_SEPARATE_AUTHORIZATION_FOR_ANY_EXECUTION
```

This matrix is ready for review. It does not declare the RSK-01 gap fixed or the system's whole-system retrieval fabric complete.
