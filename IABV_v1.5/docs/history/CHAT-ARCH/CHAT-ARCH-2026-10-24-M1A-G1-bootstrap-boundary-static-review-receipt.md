# Static review receipt — Owner-controlled bootstrap boundary source delta

- Date: 2026-10-24, America/Bogota
- Task reviewed: `M1A_G1_REVIEW_OWNER_CONTROLLED_BOOTSTRAP_BOUNDARY_SOURCE_DELTA`
- Result: `STATIC_REVIEW=FINDINGS_REQUIRE_BOUNDED_SOURCE_CORRECTION`
- Evidence basis: the Owner supplied the full reported staged and unstaged diffs for the three scoped paths in the conversation.
- Provenance limit: the actual Windows worktree was not directly accessible to this reviewer. Reported branch, HEAD, blob hashes and clean status remain `OWNER_REPORTED`; the published GitHub repo did not contain the reported candidate branch or HEAD.
- Execution: no tests, build, runtime, MCP or transport were executed.

## Scope reviewed

The two source deltas were treated separately. The staged/pre-existing delta:
- replaces shape-only public-key PEM parsing with `validate_rsa_sha256_public_key_pem`;
- adds an RFC 7515 public test vector and a Windows-CNG signature verification test, skipped on non-Windows platforms.

The unstaged task delta:
- adds `server_id` and `issuer_id` to `G1EnrollmentChallenge` and its manifest/validation;
- adds typed Owner, issuer, challenge-store, trust-registry and boundary contracts;
- adds `validate_owner_bootstrap_evidence`;
- adds synthetic-fixture validation tests;
- adds a local candidate route record in `CURRENT-STATE.md`.

## Positive findings

1. The challenge binds `server_id` and `issuer_id` and includes them in the expected manifest.
2. The validator checks the challenge's current validity, owner subject/trust-anchor/challenge/nonce/relying-party bindings, issuer/server/instance/fingerprint/key/revocation/validity bindings, and some merge-evidence bindings.
3. Interfaces are explicitly documented as contracts rather than security boundaries. Comments state that a Python Protocol, process label or key reference does not establish OS isolation.
4. The report and code keep the production positive path disabled because real adapters and protected state are absent.

## Findings requiring a targeted source correction

### F-01 — Manifest digest is checked only for syntax, not bound to the challenge (material)

In `validate_owner_bootstrap_evidence()`, the final merge predicate requires `_SHA256_RE.fullmatch(merge.manifest_sha256)` but does not recompute the canonical manifest digest from `challenge.expected_manifest()` and compare it with the evidence. The supplied positive fixture sets `manifest_sha256="e"*64`, which is a well-formed but arbitrary digest, and the validator accepts it. This undermines the claimed consistency check between the merge evidence and the exact challenge manifest.

**Required correction:** compute the canonical digest using the same serialization already asserted by `test_owner_merge_manifest_is_verified_at_merge_and_current_main` (`hashlib.sha256(json.dumps(challenge.expected_manifest(), sort_keys=True).encode()).hexdigest()`) and require exact equality. A mismatched but correctly formatted SHA-256 must be rejected. Update the positive fixture to use the expected computed value.

### F-02 — Merge metadata fields are incompletely validated

The same predicate validates SHA-1 format for `merge_commit_sha` and `main_sha`, but omits format validation for `manifest_git_blob_sha` and does not require `pull_request_number` to be a positive integer. This is a gap in the helper's own evidence-consistency contract.

**Required correction:** require the manifest Git blob SHA to match the expected 40-hex SHA-1 form; require `type(pull_request_number) is int` and `pull_request_number > 0`; add source tests for malformed blob SHA, zero/negative/non-integer PR numbers, and an incorrect but well-formed manifest digest. Malformed values should fail closed with the module's typed verification error rather than leaking a `TypeError` from regex handling.

## Deferred contract concern (not part of the minimum correction)

`OwnerControlledBootstrapBoundary.enroll()` returns `OwnerMergeVerificationEvidence`, which describes merge evidence rather than an explicit receipt that a trust record was committed. Because no production implementation exists, this does not create an enabled path now. Before a real caller is implemented, define an explicit result/receipt contract if callers need to distinguish verified GitHub merge evidence from successful challenge consumption and protected-registry persistence. Do not interpret this return type as proof of enrollment.

## Limits and resulting state

This is a static review of supplied diff text, not execution or direct checkout verification. It identifies a source-contract defect, not a demonstrated runtime exploit. No positive production bootstrap path is established.

```text
SOURCE_DIFF_DIRECTLY_SUPPLIED=YES
LOCAL_BLOB_INTEGRITY_INDEPENDENTLY_VERIFIED=NO
MANIFEST_DIGEST_BOUND_TO_CHALLENGE=NO; SOURCE_CORRECTION_REQUIRED
MANIFEST_GIT_BLOB_SHA_VALIDATED_IN_HELPER=NO; SOURCE_CORRECTION_REQUIRED
POSITIVE_PULL_REQUEST_NUMBER_VALIDATED=NO; SOURCE_CORRECTION_REQUIRED
TESTS=SOURCE_AUTHORED; NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
INDEPENDENT_ROOT=NOT_ESTABLISHED
OWNER_ASSERTION_VERIFIER=NOT_IMPLEMENTED
DURABLE_CHALLENGE_REPLAY_STORE=NOT_IMPLEMENTED
PROTECTED_TRUST_REGISTRY=NOT_IMPLEMENTED
AUTHENTICATED_PROCESS_IPC_OS_BOUNDARY=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

This receipt records only the supplied source diff and the bounded review findings. It does not establish authority, authorize protected reads, close gates, or claim canonical adoption.

## Follow-up review — evidence-consistency correction (2026-10-24)

- Follow-up task reported by Codex: `M1A_G1_FIX_BOOTSTRAP_EVIDENCE_CONSISTENCY_VALIDATION`.
- Report disposition: `TASK_RESULT=SOURCE_CANDIDATE_ONLY`; checkout, branch HEAD, file blobs, backup integrity and git status remain `OWNER_REPORTED` because this reviewer has only the supplied report/diff, not the Windows worktree.
- Targeted static result: `STATIC_REVIEW=F01_F02_CORRECTIONS_PRESENT_IN_SUPPLIED_DIFF`; this is not a test pass, production-boundary pass, or gate closure.

### Targeted findings

1. **Manifest digest binding — corrected in the supplied diff.** The validator recomputes `sha256(json.dumps(challenge.expected_manifest(), sort_keys=True).encode()).hexdigest()` and requires exact equality with `merge.manifest_sha256`. The positive fixture now computes the same expected digest; a test rejects a different but well-formed SHA-256 digest.
2. **Merge metadata validation — corrected in the supplied diff.** `manifest_git_blob_sha` must be a string matching the SHA-1 regex. `pull_request_number` must satisfy `type(value) is int` and be greater than zero, rejecting booleans as well. The predicate checks relevant runtime types before invoking regexes and includes malformed-field tests.
3. **Written versus executed checks.** Codex reports `git diff --check` passed, but that remains report evidence. All source tests are `NOT_RUN`; no build, runtime, MCP or transport was executed. The local candidate is still uncommitted/unpublished and has not been independently reconciled against GitHub.

### Residual boundary-contract issue — next bounded task

`OwnerControlledBootstrapBoundary.enroll()` still declares a return type of `OwnerMergeVerificationEvidence`. That type represents repository merge evidence, not an explicit enrollment outcome confirming that the one-use challenge was consumed and the protected registry write was completed. Since no production implementation exists, this is not evidence of a successful enrollment; nevertheless, the API contract should not let a caller mistake merge verification for an enrollment receipt. The next source-only task should define an explicit typed enrollment receipt/outcome and tests for its bindings and success semantics, without pretending a Python protocol creates a security boundary.

The real Owner assertion verifier, independently provisioned trust root, durable anti-replay consumption, protected registry, and authenticated issuer process/IPC/OS boundary remain absent. `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`; G1/G2/G3 remain unestablished; 8 prerequisites remain open / 0 closed; governance remains blocked; protected reads remain fail-closed. No root/credential/enrollment/OS action, test execution, build, runtime, transport, publish, merge, deployment or spend is authorized by this receipt.

## Enrollment receipt source attempt — intake only (2026-10-24)

- Reported task: `M1A_G1_DEFINE_EXPLICIT_BOOTSTRAP_ENROLLMENT_RECEIPT_CONTRACT`.
- Reported result: `TASK_RESULT=SOURCE_CANDIDATE_ONLY`.
- **Static-review disposition: `EXACT_DIFF_REQUIRED; NOT_REVIEWED`.** The user supplied a summary, not the exact unstaged source/test diff. The local Windows path and files are inaccessible to this reviewer, and the candidate branch/HEAD are not on GitHub. The summary cannot establish that the implementation actually contains the described predicates or tests.

### Owner-reported identity and checks

- Checkout: `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`.
- Branch: `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`.
- HEAD before/after: `6bc568e1c5a898afd65cc045c779c25a9cdc5489`.
- Source working-tree blob: `84e950934abb5969af3621a97d79d12123927234`; test working-tree blob: `7350da4ed4560639678edd584af49ee018847468`.
- Index blobs reportedly preserved: source `efc1db55155fc15c57f55f904b7d1379257e6716`; tests `fef0d1f1d6d658d8c2612f38996c82e2b2254087`.
- HEAD blobs reportedly preserved: source `cf58b6c08954dc0c3e2e3b8d6e9e240a1b4c3c72`; tests `0521a9da88853ea784fee8d4faced15c854a0899`.
- Report says 7 staged / 11 unstaged paths, status identical before/after, staged-patch SHA-256 `DA6B9757009A65CDAED2399081A5D5441F5601EB7F781A5ADC19562AB8CA467D`, and `git diff --check` clean with LF/CRLF warnings. All of these are `OWNER_REPORTED`, not independently verified.
- Tests/build/runtime/MCP/transport: `NOT_RUN`; new dependencies: 0.

### Required exact review surface

The source/test diff must be provided from the same checkout, without changing the worktree. Static review must verify the exact shapes and predicates for `OwnerBootstrapChallengeConsumption`, `OwnerBootstrapTrustRegistryPersistence`, `OwnerBootstrapEnrollmentReceipt`, `validate_owner_bootstrap_enrollment_receipt()`, the `enroll()` return annotation and associated tests. In particular, review whether success-status fields and nonempty references are merely self-asserted, whether Owner/issuer/server/merge bindings are validated, whether time fields reject booleans and invalid order, and whether failure between challenge consumption and registry persistence is represented without permitting a fake successful receipt.

Even if the validator is internally consistent, synthetic fields marked `CONSUMED_ONCE`, `PERSISTED` and `ENROLLED` do not prove durable actions occurred. A production result must originate from trusted issuer-owned operations. There is still no real Owner verifier, independent root, durable replay store, protected registry or authenticated process/IPC/OS boundary. G1/G2/G3 remain unestablished; eight prerequisites remain open; protected reads fail-closed.

Next action: obtain the exact unstaged diff for the two authorized paths and conduct a bounded static review. Do not run tests/build/runtime/transport, modify credentials or OS state, publish or merge, or change gate status.

## Enrollment receipt contract — partial static review and F-03 (2026-10-24)

- Result intake: `TASK_RESULT=SOURCE_REVIEW_BUNDLE_ONLY`; `TESTS=NOT_RUN`.
- Evidence basis: the user supplied a long module diff that exposes `validate_owner_bootstrap_enrollment_receipt()` and related dataclasses, but the test diff is explicitly incomplete (the output contains an ellipsis and is not a full export). The claimed Windows checkout and hashes remain `OWNER_REPORTED`; this reviewer did not access the local worktree. The candidate branch/HEAD is not present on remote GitHub.
- Disposition: `STATIC_REVIEW=PARTIAL_MODULE_REVIEW; F03_EXPECTED_REGISTRY_BINDING_MISSING; TEST_DIFF_INCOMPLETE`.

### Positive source-contract observations

The supplied module diff shows explicit dataclasses for challenge consumption, trust-registry persistence and enrollment receipt. The validator checks bindings from receipt to challenge, Owner, issuer and merge evidence; rejects missing sub-record objects; checks exact integer types for version/time fields; requires the outcomes `CONSUMED_ONCE`, `PERSISTED` and `ENROLLED`; and enforces chronology from challenge issue through consumption, persistence and receipt issue. Comments correctly state that these metadata do not prove durable operations. These are static observations from the provided source, not execution evidence.

### F-03 — missing trusted registry target binding

The validator accepts any nonempty `persistence.registry_id`. Its signature has no trusted expected-registry identity, and no comparison binds the ID to a value obtained from trusted host configuration/provider context. Therefore a receipt naming a different well-formed registry is not rejected on this dimension. Add an `expected_registry_id` or equivalent trusted registry identity parameter and require strict exact equality; the expected value must not come from the receipt, caller request, or untrusted issuer metadata. Add a negative test for a mismatching but syntactically valid registry ID. This strengthens only the source contract; it does not create a root of trust or prove the registry implementation is protected.

### Evidence limitation and next action

The test-diff export is incomplete, so no conclusion is made that all new tests have the asserted coverage. The next bounded task is to add the expected-registry binding and corresponding source tests, then return the complete exact test diff in the same review bundle. Preserve all staged/unstaged paths. No tests/build/runtime/MCP/transport are authorized or claimed. Keep authority assets unknown/not inspected, G1/G2/G3 unestablished, 8 prerequisites open / 0 closed, governance blocked, protected reads fail-closed.

## Follow-up F-03 correction — expected registry identity (2026-10-24)

- Result: `TASK_RESULT=SOURCE_CANDIDATE_ONLY`; `TESTS=NOT_RUN`.
- Evidence: user supplied the exact validator correction hunk and the full reported test diff. The local Windows worktree itself was not independently accessed; all local identity, hashes and preservation results remain `OWNER_REPORTED`.
- Static disposition: `STATIC_REVIEW=F03_CORRECTION_PRESENT_IN_SUPPLIED_DIFF; FULL_TEST_DIFF_REVIEWED; TESTS_NOT_RUN`.

### Correction present in the supplied diff

The validator now has required `expected_registry_id: str`, documents that future callers must obtain it from host trust configuration/provider context, rejects values whose exact type is not `str` or which are whitespace-only, and requires exact equality with `persistence.registry_id`. Invalid expected IDs produce `ENROLLMENT_RECEIPT_INVALID`; a mismatch produces `ENROLLMENT_TRUST_REGISTRY_ID_MISMATCH`.

The full supplied test diff includes a successful synthetic receipt using the matching ID, a negative case with a different well-formed expected ID, and parameterized rejection of blank/non-string expected IDs including `None`, integer and boolean. The test suite was not executed.

### Remaining evidence boundary

This closes F-03 at the supplied-source-contract level only. The `expected_registry_id` argument is not inherently trusted: future production code must source it from a trusted host configuration/provider, not from the receipt, request or untrusted issuer metadata. A typed receipt or status string does not prove durable challenge consumption or protected registry persistence. The local source/test blobs reported for this version are source `a5d14a14f31b87f181d7748e63f2f1e44b1948db` and tests `a5c1c182926271457d353b981fd701f3487e0cf4`; index/HEAD hashes are reported in the task intake, but none was independently read from the local filesystem.

G1/G2/G3 remain unestablished; eight prerequisites remain open / zero closed; governance remains blocked; protected reads remain fail-closed; bridge remains not ready. No tests/build/runtime/MCP/transport were executed. No publication or merge of the source candidate occurred.
