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
