# IABV G1 — Current Directory Tree Delta: Independent Static Review

**Review date:** 2026-10-25  
**Task:** `M1A_G1_BUILD_CURRENT_DIRECTORY_DELTA_WITH_PRESERVED_GIT_STATES_20261025`  
**Disposition:** `NOT_ACCEPTED_FOR_INTEGRATION — BASELINE_LINKAGE_UNRECONCILED; SOURCE_CANDIDATE_ONLY`  
**Review scope:** Dropbox-delivered Base64 ZIP, manifest, current directory tree diff, preserved staged/unstaged state report, and static reading of the eight differing file sections. No product source was edited and no tests, build, runtime, MCP transport, or protected reads were executed.

## 1. Artifact transfer and integrity — independently verified

Retrieved the object from Dropbox at:

`/IABV-IA-BRIDGE/INBOX/IABV_G1_CURRENT_TREE_DELTA_30d64e4a5db64f2490bb02b24c097b45.zip.b64.txt`

Dropbox metadata: 181,640 bytes, text/plain, object ID `id:5f9kJIcSlJAAAAAAAAADog`.

The Base64 text was read from Dropbox, whitespace-normalized only at the trailing boundary, decoded, and checked:

- Decoded ZIP size: **136,229 bytes**.
- Independently computed ZIP SHA-256: `3c60ff2df78bff45c6632e1d85ba93ef97172f7ab1564bfb03f995eb183fb217`.
- Expected ZIP SHA-256: `3C60FF2DF78BFF45C6632E1D85BA93EF97172F7AB1564BFB03F995EB183FB217` — **match**.
- ZIP members: 26 total; exactly one `manifest.json`.
- Non-manifest members declared by manifest: 25; **all 25 member sizes and SHA-256 values match the manifest**.
- `historical/HISTORICAL_TASK_ONLY_DIFF.original.diff` is 117,226 bytes and its SHA-256 matches the preserved original diff hash `6950FB87DCD6F57573F88BBD58B0B880BD0437E69EB5830D9F55A22AD9AA5F93`.
- Preserved original ZIP identity in the manifest is `IABV_G1_STATIC_REVIEW_DIFF_20261025_4e84c57215e140c69edb8a191dc73b57.zip`, 118,788 bytes, SHA-256 `915EFA1541AAB2546522261A8C60BFA00E4004809156CDD5CFD50B01F9620C33`.

The package's integrity is now independently verified. This confirms artifact integrity, not correctness of the source code or truth of historical attribution statements.

## 2. What the current directory comparison establishes

Both labelled folders report independent Git clones with separate `.git`/common directories, the same branch and HEAD `6bc568e1c5a898afd65cc045c779c25a9cdc5489`, and the same index entries on common tracked paths. The package reports differing working-tree bytes and file identities. The two folders therefore must not be treated as a single physical checkout or as evidence that Dropbox synchronization caused the earlier differences.

The 14-path Git status union is now reconciled, including `IABV_v1.5/src/iabv_v15/services/security/github_owner_merge_bootstrap.py` as `MM` in both clones. The earlier eight-row table omission is corrected.

The direct current working-tree comparison shows **8 different files and 6 identical files** among the 14 affected/status-union paths. The eight differing files and line counts are:

| File | Added | Deleted |
|---|---:|---:|
| `IABV_v1.5/src/iabv_v15/bootstrap.py` | 9 | 2 |
| `IABV_v1.5/src/iabv_v15/infra/mcp/server.py` | 25 | 32 |
| `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py` | 155 | 81 |
| `IABV_v1.5/src/iabv_v15/services/security/read_authorization.py` | 132 | 29 |
| `IABV_v1.5/tests/test_bootstrap_defer_init.py` | 1 | 0 |
| `IABV_v1.5/tests/test_mcp_server.py` | 51 | 8 |
| `IABV_v1.5/tests/test_read_authorization.py` | 60 | 3 |
| `IABV_v1.5/tests/test_windows_handle_reader.py` | 40 | 1 |

Total: **473 additions, 156 deletions**. This exactly matches the eight paths in the preserved historical diff inventory. The six extra paths in the 14-path status union are state-dirty but byte-identical between the two present working trees; they must not be misreported as six extra content changes.

The package reports that initial/final status and working-tree hashes did not change during packaging. I verified the package and its internal hashes independently, but did not directly inspect the Windows filesystem before and after packaging; the local preservation check itself remains producer-reported evidence.

## 3. Baseline/provenance status — still unresolved

The package explicitly labels its main comparison `CURRENT_DIRECTORY_TREE_DELTA`, not `HISTORICAL_TASK_ONLY_DIFF`. It declares base `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7` but does not provide a contemporaneous pre-task snapshot/receipt proving that the present `PRETASK_LABELLED` working tree represented that revision at task start.

The package repairs the present two-tree path inventory and gives an independently checkable current delta. It **does not** establish that the pre-task-labelled working tree was historically pristine, that it corresponded to the declared base commit, or that all staged/unstaged changes in the dirty clone are task-exclusive. The original diff's old-side blob IDs previously failed to reconcile with the declared base for four paths, and four other old-side paths were absent from that base. This remains a provenance blocker, not proof of corruption.

## 4. Static source-review findings

### Positive properties in the eight-path delta

1. `ReadPermit` binds the permit to the opened-target object and carries the target, root, and policy binding IDs. Coordinator/guard checks compare those bindings with the same opened target, plus workspace, checkout, operation, and expiry.
2. G2 policy signed data now includes root, policy, workspace, and checkout bindings; target resolution checks the opened-target and binding identity.
3. Replay-store transaction/integrity failures are translated to explicit denials rather than positive authorization.
4. Handle/target close coordination adds borrowing/active-operation counters so closing can wait for an active read/enumeration.
5. MCP server construction no longer explicitly disables DNS-rebinding protection or configures wildcard hosts/origins; SDK defaults are retained.
6. Approved-root resolution exceptions return a governance-blocked result. Bootstrap explicitly sets `approved_workspace_root_provider = None` instead of using the workspace path or current directory as an authority root.

These are bounded observations from changed hunks, not proof that the complete dirty checkout is vulnerability-free.

### Findings that still prevent acceptance

**B-01 — Baseline linkage.** The direct comparison is verifiable as a present two-directory delta but is not established as a patch against `fed7d509...` or current `main`. Do not apply, merge, or promote the dirty candidate as though that relationship were proven.

**B-02 — Production authority is not provisioned.** The changed bootstrap deliberately leaves `approved_workspace_root_provider = None`, and the coordinator remains unconfigured. The current route still says `G1/G2/G3=NOT_ESTABLISHED`, `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`, and `PROTECTED_READS=FAIL_CLOSED`. This is appropriately deny-only but is not a working positive protected-read path.

**B-03 — Handle close failure may leak the native handle.** `OwnedWindowsHandle.close()` marks `_closed = True` before calling native `CloseHandle`. If `CloseHandle` returns false or raises, the method reports a failure but the object remains marked closed; subsequent `close()` calls return without retrying. This is fail-closed for use but does not provide complete cleanup/retry semantics and can leave a native handle open. The state transition should distinguish “close requested/in progress” from “native close succeeded,” while preventing new borrows throughout.

**B-04 — The concurrency test is not deterministic evidence.** `test_closing_opened_target_waits_for_active_read_and_closes_once` signals `close_started` immediately before invoking `target.close()`. A 50 ms assertion can pass because the closer was not scheduled, rather than proving it entered the condition-wait path. Use a deterministic synchronization hook/barrier at the wait boundary if the test is to prove the race is closed.

**B-05 — Native/production semantics remain unverified.** The changed tests use synthetic handles and mocked Win32 APIs. They do not establish real Windows handle/ACL behavior, authenticated issuer IPC peer identity, or production root-provider authenticity. No test/build/runtime or real transport was run during this review.

## 5. Disposition and next action

**Disposition:** `NOT_ACCEPTED_FOR_INTEGRATION — BASELINE_LINKAGE_UNRECONCILED; SOURCE_CANDIDATE_ONLY`.

The new package closes the *delivery and current directory-delta evidence* gap. It does not close source acceptance or production authorization gates. The next bounded development action, if separately authorized, should remain in an isolated candidate: correct the `OwnedWindowsHandle.close()` failure-state semantics and replace the timing-based concurrency assertion with deterministic synchronization, then run only candidate tests/analysis that the active route explicitly permits. In parallel, integration requires a clean, reproducible patch against a verified base; do not infer that from the dirty clone label.

Do not provision or invent the independent trust root, mandate issuer, or OS-authenticated IPC provider to force positive reads. Keep:

```text
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
```

No source edits, tests, build, runtime, MCP transport, or protected reads were performed in this review.

