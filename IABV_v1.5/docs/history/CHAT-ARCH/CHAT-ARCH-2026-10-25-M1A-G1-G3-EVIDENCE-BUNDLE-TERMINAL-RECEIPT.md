# G3 evidence bundle terminal result and transfer route receipt

- Date: 2026-10-25 (America/Bogota).
- Task: `M1A_G1_PREPARE_SINGLE_G3_REVIEW_EVIDENCE_BUNDLE_20261025`.
- Terminal result: `EVIDENCE_BUNDLE_READY`.
- Provenance: Owner-pasted Codex terminal report; not independently authenticated until ZIP bytes and manifest are received.
- Canonical baseline before this route transition: `4d26900e26950cd0493d3f35e788fd781a993957`.
- Authorized review scope: one bounded independent static review, already explicitly authorized by the Owner.

## Reported package identity

- Filename: `IABV_G3_STATIC_REVIEW_EVIDENCE_20261025_3d0c265fc41443739b5e65ef3d4a23d3.zip`
- Local Windows path: `C:\Users\faber\AppData\Local\Temp\IABV_G3_STATIC_REVIEW_EVIDENCE_20261025_3d0c265fc41443739b5e65ef3d4a23d3.zip`
- Reported size: 91,213 bytes.
- Reported SHA-256: `9f9a3e575fa8c6d03b33ae9bdb73bfbf8a4680642b7a65d39fce44e154febe66`.
- Reported members: the six task-specific diffs, six current source/test files, and `manifest.json`.
- Reported validation: the ZIP could be listed; member hashes matched the manifest as measured by the producer; checkout and index identity were reported unchanged during packaging. All remain `OWNER_SUPPLIED_CODEX_REPORT` until independently checked.

## Discrepancies and limits

- The initial task prompt used `src/iabv15`, while the producing checkout's observed source paths were reported under `src/iabv_v15`. The bundle reportedly includes the three code files from the observed checkout path. Review must bind to the member paths actually present, not normalize them silently.
- `preexisting-staged.diff` and `preexisting-unstaged.diff` were reported unavailable and were not reconstructed. Initial status was not reconstructed either.
- The report states the worktree already had staged/unstaged changes and that status/index identity stayed unchanged during packaging. That supports only the reported no-new-mutation observation during packaging; it is not a replacement for the original diffs and does not prove preservation of every prior change.
- No tests, build, runtime, MCP, real transport or protected read were run.
- Repository `jhonf463r/Python` is public. The package is not to be published to a public branch/PR as a shortcut.

## Transfer and review routing

No connected private machine-to-machine route was verified. The producer-generated ZIP is already assembled; the one remaining transfer is to attach that exact single ZIP to the current ChatGPT conversation. Do not ask the Owner to collect individual members or reconstruct missing prior diffs.

Upon receipt, independently recompute the archive hash, verify member hashes/sizes against the manifest, inspect the exact six diffs and source bytes, and issue the authorized source-level static review. The preservation criterion remains `NOT_VERIFIED` because the two prior-work diffs are absent. Do not fabricate them, claim full preservation review, or infer runtime security. If the ZIP itself is incomplete or mismatched, stop and report exact mismatches.

```text
TASK=M1A_G1_PREPARE_SINGLE_G3_REVIEW_EVIDENCE_BUNDLE_20261025
TASK_RESULT=EVIDENCE_BUNDLE_READY
RESULT_PROVENANCE=OWNER_SUPPLIED_CODEX_REPORT
BUNDLE_BYTES=NOT_RECEIVED_BY_REVIEWER
BUNDLE_SHA256_REPORTED=9f9a3e575fa8c6d03b33ae9bdb73bfbf8a4680642b7a65d39fce44e154febe66
BUNDLE_SIZE_BYTES_REPORTED=91213
MEMBERS_REPORTED=6_TASK_DIFFS; 6_CURRENT_SOURCE_FILES; MANIFEST_JSON
MEMBER_HASHES=PRODUCER_VALIDATED; REVIEWER_NOT_YET_VERIFIED
PRESERVATION_DIFFS=NOT_AVAILABLE; NOT_RECONSTRUCTED
PRESERVATION_VERIFICATION=NOT_ESTABLISHED
OWNER_DECISION=ONE_BOUNDED_INDEPENDENT_STATIC_REVIEW; ALREADY_AUTHORIZED
STATIC_REVIEW=NOT_STARTED; AWAITING_ZIP_BYTES
G3_SAME_OBJECT=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
COST_POLICY=ZERO_BUDGET
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=TRANSFER_ONE_EXISTING_ZIP_TO_CURRENT_CHAT
```
