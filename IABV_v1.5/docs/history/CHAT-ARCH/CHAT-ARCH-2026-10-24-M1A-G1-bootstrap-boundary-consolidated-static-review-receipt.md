# Consolidated static review receipt — Owner-controlled bootstrap/issuer candidate

- Review date: 2026-10-24 (America/Bogota)
- Canonical live-main snapshot observed during consolidation: `main=2cecd5e9b9e175584d65bbb1198a53bc2346d095`; `CURRENT-STATE.md` blob `c577ab49c5dd16993502c7199560dc94b586a815`.
- Current source candidate: checkout `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`; branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`; HEAD `6bc568e1c5a898afd65cc045c779c25a9cdc5489`. These local details are `OWNER_REPORTED`; the branch/HEAD are not present on remote GitHub and the checkout was not accessed directly by this reviewer.
- Documentation vehicle: [PR #493](https://github.com/jhonf463r/Python/pull/493), branch `docs/iabv-transcript-route-intake-calibration-20261024`. It is open and unmerged; all contents here are proposals until adopted on live main and fetched back.

## Consolidated verdict

```text
TASK_RESULT=SOURCE_CANDIDATE_ONLY
STATIC_REVIEW=F01_F02_F03_CORRECTIONS_PRESENT_IN_SUPPLIED_DIFF
EVIDENCE_BASIS=OWNER_SUPPLIED_SOURCE_AND_TEST_DIFFS
LOCAL_CHECKOUT_INDEPENDENTLY_VERIFIED=NO
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
SOURCE_CANDIDATE_PUBLISHED=NO
CANONICAL_ADOPTION=NO
```

The verdict covers the exact source/test hunks and test diff pasted in the conversation. It does **not** certify every staged/unstaged path in the local dirty candidate, does not establish source execution, and is not a production security-boundary pass.

## Findings resolved in the supplied delta

### F-01 — canonical manifest digest binding

The supplied `validate_owner_bootstrap_evidence()` computes the SHA-256 of `json.dumps(challenge.expected_manifest(), sort_keys=True).encode()` and requires equality with `merge.manifest_sha256`. The positive synthetic fixture computes that same digest, and a test rejects another well-formed SHA-256 digest.

### F-02 — merge metadata validation

The supplied validator requires `manifest_git_blob_sha` to be a string matching the SHA-1 pattern and requires `pull_request_number` to have exact `int` type and be greater than zero. Relevant runtime types are checked before regex operations. The supplied tests cover malformed blob SHA and invalid PR numbers including booleans and non-integer values.

### Enrollment outcome contract

The supplied diff introduces `OwnerBootstrapChallengeConsumption`, `OwnerBootstrapTrustRegistryPersistence` and `OwnerBootstrapEnrollmentReceipt`, changes `OwnerControlledBootstrapBoundary.enroll()` to return the receipt type, and adds `validate_owner_bootstrap_enrollment_receipt()`. In the supplied source, the validator binds receipt fields to challenge, Owner, issuer and merge evidence; checks the declared outcomes `CONSUMED_ONCE`, `PERSISTED` and `ENROLLED`; enforces required references, exact integer checks for the relevant version/time fields, and event-time order consumption → persistence → receipt.

### F-03 — expected registry identity

The supplied correction adds required `expected_registry_id: str`, rejects values whose exact type is not `str` or which contain only whitespace, documents that future callers must source the expected value from host trust configuration/provider context, and requires exact equality with `persistence.registry_id`. Invalid expected IDs raise `ENROLLMENT_RECEIPT_INVALID`; a mismatch raises `ENROLLMENT_TRUST_REGISTRY_ID_MISMATCH`.

The complete supplied test diff includes a matching synthetic receipt, a mismatch between two syntactically valid registry identifiers, and parameterized rejection of blank/non-string expected values. Thus F-03 is corrected in the supplied source contract. This is a static diff finding only: tests remain `NOT_RUN`.

## Evidence custody and local candidate report

Codex reported the latest worktree blobs as:
- source `github_owner_merge_bootstrap.py`: `a5d14a14f31b87f181d7748e63f2f1e44b1948db`;
- tests `test_github_owner_merge_bootstrap.py`: `a5c1c182926271457d353b981fd701f3487e0cf4`;
- index blobs reportedly preserved: source `efc1db55155fc15c57f55f904b7d1379257e6716`, tests `fef0d1f1d6d658d8c2612f38996c82e2b2254087`;
- HEAD blobs reportedly preserved: source `cf58b6c08954dc0c3e2e3b8d6e9e240a1b4c3c72`, tests `0521a9da88853ea784fee8d4faced15c854a0899`.

These are owner-reported hashes and have not been read back from the Windows filesystem. The reported tree has 7 staged paths and 11 unstaged paths across 12 unique paths; the exact `git status --short` was reported unchanged. The reported staged patch SHA-256 was `DA6B9757009A65CDAED2399081A5D5441F5601EB7F781A5ADC19562AB8CA467D`. Codex reported `git diff --check` clean with LF/CRLF warnings. No tests, build, runtime, MCP or transport ran.

The conversation supplied the exact F-03 module correction hunk and full test diff, plus earlier source/test diffs for F-01/F-02 and the receipt validator. The full aggregate staged+unstaged diff across all 12 dirty paths has **not** been reviewed as one candidate; this receipt must not be read as a whole-candidate approval.

## Residual trust and implementation boundaries

1. `expected_registry_id` is not trustworthy merely because the validator accepts it. A future production caller must derive it from independently trusted host configuration/provider context, not from a receipt, request or untrusted issuer metadata.
2. `CONSUMED_ONCE`, `PERSISTED` and `ENROLLED` are status claims in value objects. They do not independently prove durable challenge consumption or a successful protected registry write.
3. No production Owner assertion verifier, independently provisioned root, durable anti-replay store, protected trust registry, or authenticated issuer process/IPC/OS boundary is established.
4. The module/test diff review does not prove the end-to-end composition of the 12-path dirty candidate.

## Canonical state and gates

Live `main` remains at the observed snapshot above unless a fresh fetch proves otherwise. The canonical `CURRENT-STATE.md` still routes to `M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY`, with source-only changes and source-test authoring authorized but test execution, build, runtime, real transport, credentials/enrollment, service installation, persistent Windows ACL/trust-store changes, publication/deployment/spend and protected reads excluded.

```text
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
ROOT_CUSTODIAN_AND_INDEPENDENT_VERIFICATION_CHANNEL=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
BOOTSTRAP_AUTHORITY_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

## Reconciled next action

Do not continue issuing narrow source-contract corrections based only on one hunk at a time. The next bounded review should inspect the **complete current staged and unstaged delta** of the reported 12-path checkout, without modifying it or executing tests. This single consolidated review must determine which source-only composition edges are actually present, which are absent, and whether the remaining gaps inherently require excluded root/credential/OS/IPC operations. Only after that review should another implementation assignment be considered. If a complete diff cannot be provided, report that exact evidence limit rather than claiming whole-candidate review.

This receipt is documentation-only. It does not publish the source candidate, grant trust, close a gate or alter the live-main route.
