# RSK-01 — Corpus, Currentness, and Candidate-Set Coverage Delta

**Date:** 2026-10-29  
**Task ID:** `RSK01_CORPUS_CURRENTNESS_COVERAGE_DELTA_20261029`  
**Status:** `STATIC_AUDIT_COMPLETE_FOR_LISTED_SURFACES / CANDIDATE / NOT_CANONICAL`  
**Repository:** `jhonf463r/Python`  
**Current main baseline:** `1430ad5062298a8dd5719ccb2882e2ce4877b283`  
**Prior RSK-01A audit baseline:** `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`  
**Action class:** read-only source/document archaeology  
**Product source changes:** `NONE`  
**Tests / build / runtime / MCP:** `NOT_RUN`  
**Canonical CURRENT-STATE changed:** `NO`  
**G1/G2/G3 / bridge / protected-read policy / tunnel / product PRs #555–#557:** `NOT_TOUCHED`  
**Separate MCO-01 and COORD-OVERLAP-AUDIT lanes:** `NOT_REPLACED`

> This record continues the RSK-01 product-knowledge lane. It does not replace `CURRENT-STATE.md`, re-run the separate coordinator-overlap review, authorize product implementation, or change the active G1/G2/G3 lane. It is a source-grounded result candidate until accepted through the existing canonical process.

## 1. Purpose and selection

The owner requested a new independent line of work after the continuity-documentation lane closed. The live canonical route continues to own active routing and permissions; it explicitly allows a separate owner objective to proceed through its own authorized lane but does not grant product-code, test, runtime, bridge or protected-read permission.

RSK-01 is the existing objective most directly connected to the product requirement that IABV know its own distributed structure and retrieve the relevant organs, evidence and prior decisions for a new task.

This delta deliberately does **not** repeat the earlier end-to-end trace of N03 or R01, the adversarial path search, or the blocked local-stdio experiment. It examines a separate still-open part of RSK-01: whether the existing corpus/retrieval surfaces represent source identity, currentness, relations and candidate-set coverage coherently enough to avoid stale, partial or consumer-specific answers.

## 2. Baseline and source comparison

The current live `main` observed for this task is `1430ad5062298a8dd5719ccb2882e2ce4877b283`. The normal read of `CURRENT-STATE.md` returned an empty payload; its exact blob `b5fbf879e95d92869e51fa2ae29d4fce5ca56bdb` was recovered. Its active header remains the UAAL-D021 documentation-closeout route, with the relevant distinction that this task is a separate owner objective and receives no implementation permission from that closeout.

The following twelve product-source files were fetched from both the earlier RSK source baseline and the current main baseline. Their blob SHAs matched exactly, so the findings previously established for these specific files remain source-current within this comparison:

| Surface | Current blob SHA | Comparison |
|---|---|---|
| `services/self_code_analysis.py` | `0bf627c43254de11427df2d9c99c6198048571ef` | Identical to prior baseline |
| `services/system_identity_registry.py` | `8fa7ba60202d947a254352bb1d7927f76becf90a` | Identical |
| `services/roles/embedding_index_service.py` | `55eae990d4ac2c97aafed3f394b2e27308272789` | Identical |
| `services/knowledge/knowledge_service.py` | `5041fa3a1f8f9b55230efd0117b946a65b2a5e90` | Identical |
| `services/knowledge/unified_memory_layer.py` | `0a2f3a09e14258b6fad3ff9f411e9bb34c08cad1` | Identical |
| `services/evolution/decision_audit_trail.py` | `01279436b70155ece4b680809a702255434742cc` | Identical |
| `services/evolution/code_audit_trail.py` | `d527301f5e51a8b9e5b114f4ff58bc2bfc134952` | Identical |
| `services/roles/local_role_router.py` | `2a811bb796d90a6c79017b049e8dc0382a0c9ead` | Identical |
| `services/roles/customer_support_service.py` | `69c164081e7461576ce7f330cd06579675e20919` | Identical |
| `domain/models.py` | `a9033d21052c519e09f482097599c704a62ea916` | Identical |
| `infra/persistence/knowledge_repository.py` | `209a1affa92ba79b54ffe70e6ecd7cf644a4f378` | Identical |
| `services/adaptive/task_context_assembler.py` | `c5a6852a6a82a0c60886ea4bb6c236f50fe4a57c` | Identical |

This is a comparison of named files, not proof that every file or every runtime path is unchanged.

## 3. Findings

### F1 — There are several retrieval entry points, not one demonstrated whole-organ candidate fabric

**Source evidence:**

- `TaskContextAssembler._knowledge_hits()` expands terms from the user goal and objective/project/task labels or IDs, calls `KnowledgeRepository.search(term, limit=5)`, deduplicates by `knowledge_id`, and stops at eight hits.
- `LocalRoleRouter._route_knowledge()` first calls `KnowledgeRepository.search(user_goal, limit=10)`, projects those hits into caller-supplied document dictionaries, then calls `EmbeddingIndexService.search(..., limit=5)`.
- `CustomerSupportService.build_context()` performs a separate repository search with limit 8, constructs its own document list and asks the same index service for up to four results.
- `EmbeddingIndexService.search(query, documents, limit)` receives its corpus from the caller. The implementation tokenizes the query/document text and scores lexical token overlap; it does not itself enumerate the repository, canonical Markdown, all evidence artifacts or the complete codebase.
- `refresh_metadata()` reports `index_mode='lexical-fallback'` and counts/last query. Metadata refresh is not itself evidence of a materialized whole-project index.

**Adjudication:** existing organs do retrieval and objective-conditioned assembly, but the code inspected does not establish a single authoritative candidate set shared by all consumers. Each path can search a different subset, apply a different cap and return a different shortlist. The service name `EmbeddingIndexService` must not be treated as proof of universal semantic indexing.

Sources:
- [TaskContextAssembler](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/services/adaptive/task_context_assembler.py)
- [KnowledgeRepository](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/infra/persistence/knowledge_repository.py)
- [EmbeddingIndexService](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/services/roles/embedding_index_service.py)
- [LocalRoleRouter](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/services/roles/local_role_router.py)
- [CustomerSupportService](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/services/roles/customer_support_service.py)

### F2 — The operational knowledge item does not enforce source identity, temporal validity or supersession as first-class fields

The current `KnowledgeItem` model contains `knowledge_id`, `title`, `summary`, `source_episode_id`, `task_label`, `confidence`, `tags`, `payload`, `created_at_utc` and `updated_at_utc`.

Those fields support useful operational learning, including the producer path `RunRecord → UnifiedMemoryLayer.remember_run() → KnowledgeRepository.upsert()`. However, the inspected schema does not declare first-class fields for:

- canonical source path/type and exact source revision or content digest;
- observed/event time versus record/update time;
- a validity interval or explicit stale/superseded state;
- a canonical authority class or source-precedence decision;
- a typed `supersedes` / `contradicts` / `derived_from` relation to another knowledge unit;
- a required evidence reference whose target can be independently fetched and checked.

A generic `payload` or `metadata` dictionary may carry extra values, but that is not equivalent to a typed, enforced and consistently consumed contract.

### F3 — Repository search orders by update time; update time is not semantic currentness

`KnowledgeRepository.search()` uses SQL `LIKE` matching over title, summary and tags, then orders results by `updated_at_utc DESC`. The search does not itself evaluate whether a record is authoritative, whether its claim has been superseded, whether its source revision still matches live main, or whether a later record explicitly contradicts it.

Recent update time can be a retrieval hint, but it cannot safely stand in for event time, evidence validity or canonical authority. The risk is that stale/highly repeated material remains retrievable while the system lacks a required arbitration step to mark it historical, superseded or unresolved.

Source: [KnowledgeRepository](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/src/iabv_v15/infra/persistence/knowledge_repository.py).

### F4 — Existing identity and audit organs provide partial dimensions, but are not shown composing into a single typed relation graph

`SystemIdentityRegistry` records subsystem names, paths, categories, statuses, dependencies, maturity, last verification and descriptive evidence. Its snapshot is assembled through separate registration methods and cached for five minutes. It is useful for system/subsystem identity and wiring, but it is not an index of every canonical claim, source blob, knowledge item and evidence artifact consumed by objective retrieval.

`SelfCodeAnalysis.holistic_metacognition_scan()` cross-references input summaries of sources such as Git state, tests and environment observations. It is primarily a diagnostic/self-analysis surface, not the general objective-conditioned retrieval index.

`DecisionAuditTrail` writes decision records to append-only JSONL and provides trend/self-examination summaries. `CodeAuditTrail` writes audit rounds and publishes relevant records to `ExperimentLab`. These are meaningful provenance and learning surfaces for their domains; the bounded review did not establish a shared typed relation model that connects each record to canonical source revisions, currentness decisions, consumer activation and later outcomes across all organs.

The historical [Systemic Integrity and Connectivity audit](https://github.com/jhonf463r/Python/blob/1430ad5062298a8dd5719ccb2882e2ce4877b283/IABV_v1.5/docs/history/CHAT-ARCH/SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md) had already described this general fragmentation: identity, context, source inspection and runtime chronology existed in separate organs, with no verified component shown combining producer, consumer, source reference, contract semantics, temporal ordering and runtime outcome into one cross-organ contract judgment. This record is supporting historical evidence; its full conclusions were not re-run as a new exhaustive audit here.

### F5 — Evidence references are useful, but the inspected shared model does not require source-verification metadata

The current `EvidenceRef` model has `evidence_id`, `kind`, `label`, `ref_id`, optional `path` and generic `metadata`. The audit and decision trails retain domain-specific records. This provides a base for provenance, but the inspected model does not require a source revision, source digest, observation timestamp, validity status or typed relation to the exact claim being retrieved.

This is a schema/composition observation, not a claim that no artifact anywhere carries such metadata. The missing proof is that the same enforced semantics are populated and consumed consistently across the candidate-generation, ranking and decision paths.

## 4. What this delta changes

This delta does not repeat the earlier bounded conclusion that canonical `CHAT-ARCH` claims N03 and R01 were not demonstrated to enter the operational retrieval/routing path. That prior conclusion remains relevant because the named retrieval files above have identical blob SHAs to the earlier audited baseline.

The new, more precise classification is:

- `B — MISSING_COMPOSITION:` remains supported for the audited canonical-document-to-operational-retrieval path.
- `C — CORPUS/CURRENTNESS/CANONICALIZATION:` gains direct source-level support as a contributing unresolved gap: candidate sources are consumer-dependent, the embedding service accepts caller-provided documents and uses lexical fallback, and the operational knowledge contract does not require authority/currentness/supersession semantics.
- `D — NEW_ORGAN_REQUIRED:` still not demonstrated. Existing owners can plausibly express the missing contract if correctly composed; no implementation or new service is justified by this result.
- Runtime effect and causal contribution remain untested here.

This is a bounded static result. It does not prove every ingestion path in the repository has been exhaustively searched, and it does not prove the runtime cannot receive external data through another path.

## 5. First open edge

`canonical source/document/code/evidence → normalized candidate with source identity + revision + authority/currentness + typed relations → objective-conditioned candidate set → selected consumer/decision`

The exact missing contract is not “more memory”. It is **consistent, verifiable source/candidate semantics across existing retrieval entry points**, followed by a decision consumer that can distinguish current authority from historical or conflicting material.

## 6. Next discriminating action

The read-only fixture plan is now prepared in the companion [RSK-01 candidate-set currentness and provenance matrix](./CHAT-ARCH-2026-10-29-RSK-01-CANDIDATE-SET-CURRENTNESS-FIXTURE-MATRIX.md). It contains six frozen-source candidates, eight objective queries, expected adjudications, falsifiers, consumer-by-consumer coverage and the evidence/metrics to collect. It is a specification only; it has **not** been executed.

The next causal step is to review that matrix/contract and obtain a separate, explicit authorization for any execution or implementation. Do not automatically turn the design into code. If execution is later authorized, pin the then-live main and re-fetch the listed fixtures first; record the actual candidate IDs, source SHAs, consumer path, exclusions, ranking rationale and resulting answer for every query.

Until such authorization:
- no new index/graph/brain/service;
- no changes to `CURRENT-STATE.md` or the other chat's canonical lane;
- no runtime/bridge/stdio setup;
- no source changes, tests, build or deployment;
- no merge of product candidates.

The RSK-01A.6 local-stdio experiment remains a distinct historical bridge-dependent step and was not retried here. The G1/G2/G3 lane must resolve its own current permissions before any action that would configure or exercise that bridge.

## 7. Relation to the other open lanes

- `COORD-OVERLAP-AUDIT-20261029` is owned by a separate chat; this record does not audit file/task overlap across chats.
- `MCO-01` addresses governed multi-AI work packets, branch isolation and non-interference; it does not supply the product's knowledge-retrieval semantics.
- `RSK-01` addresses the product's objective-conditioned retrieval, source semantics, relations and evidence; it does not authorize parallel runtime dispatch.
- The canonical G1/G2/G3 lane remains separate and unchanged.

## 8. Result and guard state

```text
TASK_ID=RSK01_CORPUS_CURRENTNESS_COVERAGE_DELTA_20261029
TASK_CLASS=READ_ONLY_STATIC_SOURCE_AUDIT
BASE_MAIN=1430ad5062298a8dd5719ccb2882e2ce4877b283
PRIOR_AUDIT_BASE=3de2bb4eddf4e43d9664e17b935d7a55b6ea9442
NAMED_SOURCE_FILES_COMPARED=12
MATCHING_BLOBS_ACROSS_BASELINES=12
CORPUS_AND_RETRIEVAL_DELTA=FOUND
CURRENTNESS_AND_SUPERSESSION_SCHEMA=NOT_FIRST_CLASS_IN_KNOWLEDGEITEM
UNIFIED_CANDIDATE_SET=NOT_DEMONSTRATED
CROSS_ORGAN_TYPED_RELATION_GRAPH=NOT_DEMONSTRATED
NEW_ORGAN_REQUIRED=NOT_DEMONSTRATED
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
TESTS_BUILD_RUNTIME=NOT_RUN
MCP_TRANSPORT=NOT_USED
CANONICAL_ROUTE_MODIFIED=NO
G1/G2/G3=NOT_TOUCHED
MCO01_AND_COORD_OVERLAP=NOT_REPLACED
RESULT=STATIC_DELTA_DOCUMENTED; PRODUCT_FIX_NOT_IMPLEMENTED
FIXTURE_MATRIX=SPECIFIED_NOT_EXECUTED
NEXT_ACTION=REVIEW_FIXTURE_MATRIX_CONTRACT_BEFORE_ANY_SEPARATE_EXECUTION_OR_IMPLEMENTATION_AUTHORIZATION
```

## 9. Stop condition

Stop this static audit at the above result. Do not repeat the N03/R01 source-to-routing trace or the unavailable local-stdio attempt unless genuinely new evidence changes their preconditions. The next stage is the discriminating fixture/contract review. Product implementation remains a separate authorization decision.
