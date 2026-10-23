# M1A v1.0.0 targeted adversarial review — receipt and finding register

- Task ID: `M1A_CONSOLIDATED_SCOPE_CONTRACT_V1_TARGETED_ADVERSARIAL_REVIEW`
- Report disposition: `PASS_WITH_REPAIRS`
- Review mode: documentary/static only
- Reviewer attribution: `OWNER_REPORTED: Claude / Sonnet 4.6, active Antigravity session`
- Timestamp supplied with report: 2026-10-22, America/Bogota; exact clock time not supplied
- Provenance: owner-pasted report received in ChatGPT conversation. The reviewer/session attribution and claimed local `git hash-object` operations are not independently authenticated by this coordinator; retain them as attributed report claims, not as a transport receipt.
- Target contract: `IABV-OPERATIONAL-BLOCK-SCOPE v1.0.0`
- Target Git blob: `8181c7c0cf6036c76cf365510e8d9665cf84e57e`
- Reported input blobs: contract `8181c7c0cf6036c76cf365510e8d9665cf84e57e`; ledger `3425144a661c713eb8898c1eacefb2d791519bc0`; UAAL-ROOT-001 `2e42ce7dd1615f83cb690b226e2a27af90190751`; Entry 274 `5943a87d907436fc7ecac31534cbfcd31fe7de55`; overlay `788732f2908f63bae13be42a8359b069d42db633`.
- Scope limitations reported: no source/runtime/tests/build/transport/local checkout/data/SQLite/secrets/credentials inspection; the earlier report cited by the ledger was not re-fetched; the Central M1A reconciliation link in contract §1.1 was not inspected.
- Status: `REVIEW_RECEIVED; FINDINGS_REQUIRE_RECONCILIATION`. This is not implementation, test, runtime, permission, or bridge-readiness evidence.

## Verdict and high-level conclusion

The report returns `PASS_WITH_REPAIRS`, with eight findings: two HIGH, three MEDIUM, three LOW. It reports no finding that challenges the Owner-adopted seven-decision design baseline. The report says the Owner acceptance boundary in §1.2/§12 remains accurate and the 30 cases present in v1.0.0 are correctly counted, while several cases and matrix mappings need more precise discrimination.

The target v1.0.0 is preserved unchanged as the reviewed historical baseline. The repairs below are treated as technical clarifications of already-adopted fail-closed requirements, not a new governance ballot. A successor candidate remains non-adopted until its targeted review/reconciliation is complete.

## Immutable finding register and coordinator disposition

### F-M1A-01 — HIGH — Validation failure concurrent with selector mismatch
- Reported sections: §§3.1–3.2, §4, M1A-C10/C11.
- Counterexample: trusted assistant identity differs from `EXACT(a)`, but catalogue integrity validation simultaneously fails. An evaluator that checks mismatch first could return `PROVEN_NOT_APPLICABLE` and suppress `CATALOGUE_INTEGRITY_INVALID`.
- Required repair: make all trust/schema/version/producer/resolver checks strict preconditions to interpreting mismatch as non-applicability; a failed/unknown precondition forbids `PROVEN_NOT_APPLICABLE`; preserve every denial reason.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`. Add stage-level validation status/evidence and discriminating concurrent-failure cases. Does not change the Owner-approved selector model.

### F-M1A-02 — HIGH — No verifiable authority for completeness of the active-block set
- Reported sections: §6 steps 1/5, M1A-C20.
- Counterexample: evaluator trusts a list supplied by a block producer/evaluator; an applicable `GLOBAL/GLOBAL` block is omitted while a different exact-selector block is correctly declared non-applicable. The evaluator cannot distinguish a complete empty/partial result from omitted active blocks.
- Required repair: require an authenticated, versioned active-set snapshot/completeness attestation from the authorized catalogue/publisher trust path, binding revision/digest/epoch, scope and freshness/revocation; an unverified, missing or partial set yields `DENY / ACTIVE_BLOCK_SET_UNVERIFIABLE`. A verified explicit empty set is different from no response.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`, while explicitly making no claim that such a registry/snapshot exists today. Existing source-boundary limitations remain unresolved and fail-closed.

### F-M1A-03 — MEDIUM — Legacy unevaluable-state aggregation ambiguity
- Reported sections: §§6, 6.1, 8; M1A-C22.
- Counterexample: an authenticated but semantically ambiguous legacy block returns `LEGACY_SCOPE_UNEVALUABLE` while another block is validly non-applicable. A consumer that recognizes only `BLOCK_SCOPE_UNEVALUABLE` could omit the legacy block from denial aggregation.
- Required repair: only `BLOCK_APPLIES` and `PROVEN_NOT_APPLICABLE` are non-denial per-block outcomes; every other vocabulary value, including legacy/scope/catalogue/producer/release failures, forces overall `DENY`. Preserve all per-block reasons.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`.

### F-M1A-04 — MEDIUM — “Passed validation” has no independently inspectable result field
- Reported sections: §§2, 3.1–3.2, §6; C03/C05/C07–C10.
- Counterexample: a mismatch evaluation claims `PROVEN_NOT_APPLICABLE`, but the result contains no explicit, auditable record that the prerequisite catalogue, producer, version, block, and identity checks actually passed.
- Required repair: include a per-block `pre_selector_validation_status` (`PASSED`, `FAILED`, `UNKNOWN`), per-stage results and evidence references. A consumer must reject `PROVEN_NOT_APPLICABLE` unless all mandatory stages are explicitly `PASSED` with references.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`. This is evidence structure, not a permission-bearing receipt; Entry 274's independent reader and authorization checks remain separate.

### F-M1A-05 — MEDIUM — Freshness/revocation of block-release artifact
- Reported sections: §6 step 6, §7; M1A-C30.
- Counterexample: a cached release artifact was valid 12 hours ago but has since been revoked; evaluation uses stale cached status and passes the scope gate.
- Required repair: verify the release artifact's authority, block/scope binding, expiry and current revocation status at the protected decision boundary, and re-check under Entry 274 immediately before operation/content release. A stale cache or unavailable authoritative revocation source cannot establish a valid release; deny with `BLOCK_RELEASE_UNSUPPORTED`.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`, explicitly derived from the already-adopted independent release boundary and Entry 274's current revocation/freshness requirements.

### F-M1A-06 — LOW — Traceability matrix under-specifies C23/C24
- Reported section: §11 vs. §9 cases C23/C24/C29.
- Counterexample: the grouped C20–C24 mapping does not let an auditor derive from the matrix alone the distinct invariant for partial multi-block release versus order-independent aggregation.
- Required repair: split the traceability row into active-set completeness, mixed-result aggregation/order determinism, and partial-release invariants; map C29's no-applicable-blocks pass semantics explicitly.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`.

### F-M1A-07 — LOW — Parent reconciliation document outside the bounded review inputs
- Reported section: §1.1.
- Counterexample: §1.1 links a “Central M1A reconciliation” document that was not in the five permitted inputs; its contents were not reviewed, so it cannot silently add normative obligations by reference.
- Required repair: label that linked artifact derivation history/context only, with no additional normative requirements incorporated by reference. If later review genuinely depends on a normative clause from it, add it explicitly to that review's authorized input set first.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`; no retrieval/inspection of that extra document is undertaken for this task.

### F-M1A-08 — LOW — Matrix mapping is not granular enough for all 30 cases
- Reported sections: §§9, 11, 12.
- Counterexample: the matrix groups case ranges without individually exposing the invariants tested by C23/C24/C26/C29/C30.
- Required repair: add explicit per-rule case coverage for partial release, order determinism, evidence-not-authority, gate-pass semantics, and independent release. The successor candidate has additional discriminating cases; its count must be recomputed and declared separately from governance decisions.
- Coordinator disposition: `ACCEPTED_FOR_V1_0_1_CANDIDATE`.

## Reconciliation totals

| Category | Count | Result |
|---|---:|---|
| HIGH | 2 | Repair required before considering the successor closed |
| MEDIUM | 3 | Repair required |
| LOW | 3 | Traceability/editorial repair |
| Total findings | 8 | All receive an explicit disposition |
| Challenges to OG-M1A-01..07 | 0 | Accepted design choices remain unchanged |
| Additional Owner governance decisions created | 0 | Engineering acceptance cases are not governance ballots |
| Runtime/source/test claims verified by this review | 0 | Documentary review only |

## Non-negotiable boundary

The report does not prove an actual runtime principal/trust anchor, catalogue publisher or active-block registry, producer allowlist, target resolver/call-site bindings, revocation service, or independent release mechanism. It does not authorize implementation, tests, builds, runtime, transport, merge, deployment, read access, or release of any block.

```text
REVIEW_VERDICT=PASS_WITH_REPAIRS
REVIEW_DISPATCH=REVIEW_RECEIVED_FROM_OWNER_PASTED_REPORT
CONTRACT_V1_0_0_BLOB=8181c7c0cf6036c76cf365510e8d9665cf84e57e
FINDINGS=8
FINDINGS_HIGH=2
FINDINGS_MEDIUM=3
FINDINGS_LOW=3
OWNER_DECISIONS=OG-M1A-01..OG-M1A-07; UNCHANGED
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```
