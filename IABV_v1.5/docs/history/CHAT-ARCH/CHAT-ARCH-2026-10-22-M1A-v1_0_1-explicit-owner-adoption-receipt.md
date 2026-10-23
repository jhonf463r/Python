# M1A v1.0.1 — explicit Owner adoption receipt

- **Record date:** 2026-10-22, America/Bogota.
- **Decision source:** exact Owner message in the active conversation: `ACCEPT_M1A_V1_0_1_SUCCESSOR_BASELINE`.
- **Decision type:** normative design adoption only.
- **Adopted artifact:** `IABV-OPERATIONAL-BLOCK-SCOPE v1.0.1`, immutable reviewed blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`.
- **Predecessor:** v1.0.0 blob `8181c7c0cf6036c76cf365510e8d9665cf84e57e`, preserved unchanged as the historical predecessor.
- **Review provenance:** `OWNER_REPORTED_PASS_WITH_REPAIRS`; `REVIEW_TIMESTAMP=UNVERIFIABLE`; reviewer/session invocation remains `OWNER_REPORTED`.
- **Review boundary:** the supplied review reported F-M1A-01 through F-M1A-08 passing on this exact blob. The coordinator did not independently re-perform the adversarial review. FN-M1A-V101-01 remains a nonblocking C30 traceability clarification; FN-M1A-V101-02 was not confirmed as a contract defect after the bounded overlay cross-check.
- **Prior prerequisite matrix:** blob `608a5c7f3c2be8ad794b21bfcb66657217584a58`, which mapped eight implementation gates and closed none.

## Decision and effect

The Owner supplied the exact acceptance token required by the canonical decision gate. This receipt records effective adoption of v1.0.1 as the **current normative design baseline**. The reviewed artifact remains byte-for-byte unchanged; this separate receipt records the adoption without mutating the reviewed blob.

The earlier `ok procede` was correctly treated as authorization for bounded documentary continuation only under UAAL construction-completeness overlay C1. That historical interpretation remains valid for the earlier message. This later exact token is the separate explicit policy decision that closes the design-adoption gate.

Adoption is limited to normative design. It does not prove runtime capability and does not authorize implementation, code changes, local checkout access, protected reads, tests, builds, runtime, transport, merge, deployment, or release of any operational block.

## Next authority frontier

The next unresolved dependency is a legitimate, supported, governance-owned evidence route and a named accountable producer for G1–G3: runtime principal/trust anchor; catalogue, producer and revocation authority; and the operation-to-target resolver. The currently available evidence does not establish that route or those producers.

The next task is `M1A_V1_0_1_G1_G3_AUTHORITY_EVIDENCE_ROUTE`, status `WAITING_AUTHORITY`. Do not repeat broad scans, bypass a denied reader, invent an operator, or ask another reviewer to repeat the same contract review. The next concrete investigation should be a metadata-only inventory of the explicitly exposed tools in the already-existing Codex UI session, not a local source read.

```text
OWNER_DECISION=ACCEPT_M1A_V1_0_1_SUCCESSOR_BASELINE
V1_0_1_ADOPTION=ACCEPTED_NORMATIVE_DESIGN_ONLY
V1_0_1_BLOB=7c72474a5f7c114c02320c177d6ea2aea68ad28f
V1_0_0_PREDECESSOR_BLOB=8181c7c0cf6036c76cf365510e8d9665cf84e57e
REVIEW_VERDICT=OWNER_REPORTED_PASS_WITH_REPAIRS
REVIEW_TIMESTAMP=UNVERIFIABLE
REVIEW_SESSION_ATTRIBUTION=OWNER_REPORTED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
ACTIVE_TASK=M1A_V1_0_1_G1_G3_AUTHORITY_EVIDENCE_ROUTE
STATUS=WAITING_AUTHORITY
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```
