# Terminal receipt — G3 static review failed at source-contract level

- Date: 2026-10-25 (America/Bogota).
- Task: `M1A_G1_TRANSFER_PRODUCER_ZIP_AND_PERFORM_ONE_AUTHORIZED_STATIC_REVIEW_20261025`.
- Result: `FAIL_STATIC_REVIEW_SOURCE_CONTRACT`.
- Documentary baseline observed before this transition: `main=50d056aa816e1fae43e4277773ac5cfb1f38dcd4`.
- Scope of this receipt: reconcile the supplied terminal review report and route the next decision. This receipt does not modify or validate product code.

## Evidence identity and provenance

The prior review report supplied by the Owner states that it independently checked the ZIP archive and all manifest-member hashes:

- ZIP: `IABV_G3_STATIC_REVIEW_EVIDENCE_20261025_3d0c265fc41443739b5e65ef3d4a23d3.zip`
- Reported size: `91,213 bytes`
- Reported SHA-256: `9f9a3e575fa8c6d03b33ae9bdb73bfbf8a4680642b7a65d39fce44e154febe66`
- Reported entries: 13 total (12 artifact members plus `manifest.json`); the report says the 12 manifest-listed artifacts match their declared sizes and SHA-256 values.
- Provenance limit: this documentation reconciliation relies on the supplied prior-review text; the ZIP bytes were not re-opened or re-hashed during this GitHub update. Archive/member verification is therefore recorded as a result reported by that review, not as a new test performed by this transition.
- The report identifies actual candidate paths under `src/iabv_v15`, whereas the initial request named `src/iabv15`. Preserve that difference; do not silently normalize the path.
- `preexisting-staged.diff` and `preexisting-unstaged.diff` were absent and were not reconstructed. The review cannot certify byte-for-byte preservation of prior staged/unstaged work.

## Static findings

The supplied review report identifies six source/validation blockers:

1. **Replay consumer signature mismatch.** In `read_authorization.py`, the call to `self._replay.consume_once()` passes `opened_target`, `target_binding_id` and `_issuance_seal`, while the reported `ReplayConsumer`, `SQLiteReplayConsumer.consume_once()` and test `_Replay.consume_once()` contracts do not accept those arguments. The exception path maps the mismatch to `AUTHORITY_DEPENDENCY_FAILED`; as statically reported, the positive authorization path cannot complete against the included implementations.
2. **Permit does not carry the opened-object binding.** The reported `ReadPermit` constructor leaves `opened_target`, `target_binding_id` and `_issuance_seal` at defaults (`None`, empty string and `None`). The server guard requires the coordinator-issued seal and matching opened object/binding, so the permit does not meet the guard contract.
3. **Approved workspace-root provider is absent in the reported composition.** The candidate expects an approved provider exposing `current_workspace_root()` and a valid `WorkspaceRootCapability`; the report says `AppBootstrap` does not supply it. The reported safe response is `APPROVED_WORKSPACE_ROOT_UNAVAILABLE`, which blocks integration closure.
4. **Root policy identity is not bound end-to-end.** `policy_binding_id` / `root_binding_id` are not shown to remain a verified link through resolution, authorization decision, permit and final guard. `target_binding_id` alone is not proof of approved-root identity.
5. **Handle ownership/lifetime requires repair.** The report flags a possible borrow/close synchronization race and a child-handle cleanup gap if closing the previous handle fails after a child has opened. These are static risks, not observed runtime races.
6. **Windows ABI/kernel semantics remain unvalidated.** The included tests reportedly validate naming and mocked calls, but do not establish real Windows relative opens, reparse-point behavior, cleanup after failures or native ABI semantics. The tests were not run during the review.

## Terminal verdict and limits

```text
TASK_RESULT=FAIL_STATIC_REVIEW_SOURCE_CONTRACT
BUNDLE_ARCHIVE_AND_MEMBER_HASHES=REPORTED_INDEPENDENTLY_VERIFIED_BY_PRIOR_REVIEW
RAW_ZIP_REOPENED_DURING_THIS_DOCUMENTARY_UPDATE=NO
PRESERVATION_DIFFS=PREEXISTING_STAGED_UNSTAGED_NOT_AVAILABLE; NOT_RECONSTRUCTED
PREEXISTING_WORK_PRESERVATION=NOT_VERIFIABLE_INDEPENDENTLY
APPROVED_WORKSPACE_ROOT=UNAVAILABLE_IN_REPORTED_COMPOSITION
WORKSPACE_ROOT_IDENTITY_BOUND_TO_APPROVED_POLICY=NOT_ESTABLISHED
NATIVE_WINDOWS_SEMANTICS=NOT_RUNTIME_VALIDATED
SOURCE_TESTS=AUTHORED; NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CODE_MODIFICATION=NOT_PERFORMED
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_PERFORMED
AUTOMATIC_FOLLOW_ON=FALSE
```

## Fastest safe next step

The Owner's priority is to finish the authorization-to-handle organ quickly enough for it to receive genuine trust-backed authorizations and allow downstream PEI work to proceed. The next candidate should be one narrow, integrated remediation—not another broad API exploration or a repeated review loop—and should address the replay-consumer contract, permit/object/seal binding, approved-root provider composition, root-policy binding, and handle cleanup as one path.

The remediation must use an existing, genuinely trusted root/provider if one is available. It must not invent a provider, treat a workspace path as trust authority, substitute the workspace root for the independent IABV trust root, or weaken fail-closed behavior. If the approved provider or its authority chain is unavailable, the task must return that exact blocker rather than claim completion. The missing pre-existing diffs also remain a custody limitation; any future source work must preserve the original checkout and its unknown prior changes, preferably by working in a separate bounded candidate/worktree with explicit provenance.

This review does **not** authorize the follow-on source task. The next route is an explicit Owner decision on one bounded source-remediation candidate. A source-only repair would not itself establish G1/G2, real Windows semantics, or permit protected reads; those gates require their own evidence and authority.

## Canonical route links

- [CURRENT-STATE.md](./CURRENT-STATE.md) — sole routing authority.
- [Consolidated new-chat handoff](./CHAT-ARCH-2026-10-25-M1A-G1-CONSOLIDATED-NEW-CHAT-HANDOFF.md).
- [Living Space-Time protocol, revision 2.1 routing and evidence rules](./CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md).
