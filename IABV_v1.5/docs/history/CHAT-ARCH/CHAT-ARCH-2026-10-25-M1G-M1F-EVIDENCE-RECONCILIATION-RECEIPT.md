# M1F — Evidence reconciliation and bounded independent static review

Review date: 2026-10-25 (America/Bogota). Dropbox server timestamps for the corrected evidence are on 2026-10-26 UTC.

## Disposition

DISPOSITION=BOUNDED_STATIC_REVIEW_FAVORABLE_FOR_M1E_HANDLE_CLEANUP
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
PRODUCT_SOURCE_INTEGRATION=NOT_AUTHORIZED
PROTECTED_READS=FAIL_CLOSED

This review checked the exact M1E relative diff, the consolidated M1F diff and the corrected M1F evidence archive fetched from the shared Dropbox bridge. The M1F candidate was reconstructed by Codex in a fresh clean-base clone; ChatGPT did not execute any product tests and did not perform native Windows or production authorization tests.

## Baseline and candidate provenance

Repository: jhonf463r/Python
Verified main and reported clean detached reconstruction HEAD: 74b9a3900b39ed2009fccf4ba0be20faf7d9dac8

M1F report: /IABV-IA-BRIDGE/OUTBOX/M1F_G1_RECONSTRUCTION_RESULT_20261025_CORRECTED.md
M1F consolidated diff: /IABV-IA-BRIDGE/OUTBOX/M1F_M1D_PLUS_M1E_CANDIDATE_VS_MAIN.diff
M1F corrected evidence archive encoded as Base64: /IABV-IA-BRIDGE/OUTBOX/M1F_G1_RECONSTRUCTION_EVIDENCE_20261025_CORRECTED.zip.b64.txt

## Artifact identities

| Artifact | Size | SHA-256 | Verification |
|---|---:|---|---|
| M1D evidence ZIP after Base64 decoding | 56,468 bytes | 8b842c1d7aea09ae0bd709eb5ef4e5ce3c3cd5137c5f0561317c97ecdac22954 | Previously independently verified during M1D reconciliation |
| M1D candidate-vs-main diff | 236,488 bytes | 2d81795259bf27841ca0cc77c06144a4007a198f76a644986966a6023c3af722 | Previously independently verified |
| M1E cleanup diff | 38,025 bytes | e7a996ec45222ce625ee9c80950ce2951dd8e0cfbf5529cca89e775090c34373 | Recomputed from Dropbox text after removing one extraction-added terminal newline; match |
| M1E evidence ZIP after Base64 decoding | 11,557 bytes | 60ff35ff9e0f6e69061f2a4ca3338a5d8809961c251df5c8c3137bf8673e7711 | Independently decoded and hashed earlier in this review sequence |
| M1F consolidated diff | 249,105 UTF-8 bytes | 29902d05a6f65e74ca251af174917074f2939a018ddd241c95da39eb87dd0021 | Recomputed from Dropbox text after removing one extraction-added terminal newline; match |
| M1F corrected evidence ZIP after Base64 decoding | 56,546 bytes | 7c161a009a50da8133b173d7b282964ad4678818f713d2fb793e4a59ce22590f | Independently decoded from the Dropbox Base64 text; size and SHA-256 match the declared local archive |
| M1F corrected report | 4,356 bytes declared by producer | 5f4385f276ba4775105dc2292cbf01a837ddcf42c38412674a35ee7ed9817e45 reported by producer | Dropbox extraction normalizes a line ending/control character; this file hash is producer-reported, not independently recomputed from raw bytes in this review |
| M1F manifest | SHA-256 03f4a04b7a72c324d4218681a30af013cde81832b54d5105a6030e965a47f0ca reported by producer | Producer-reported | The ZIP identity was independently verified, but its member hashes were not separately unpacked and recalculated in this review |

The M1E patch's original bytes were preserved. Codex reports that its paths contain m1d-baseline/m1e-candidate prefixes and its second section separator is encoded as literal backslash-n characters; a separate temporary normalized application copy was used for the clean-base reconstruction. That application detail does not change the original evidence identity.

## Static observations

1. In _open_component, M1E creates one OwnedWindowsHandle wrapper and uses that same wrapper during validation and cleanup. When validation and close both fail, WindowsHandleCleanupError retains the operation error, cleanup error and still-owned handle instead of suppressing the close failure or wrapping the same native handle twice.
2. In open_target, M1E registers the new child handle in owned_handles before borrowing it or closing the previous parent. If the parent close fails after the child has opened, the exception path attempts reverse-order cleanup and retains handle references when cleanup fails.
3. The added regression cases exercise those failure paths using synthetic handles/mocked APIs. In this bounded review, I found no additional blocker in the two M1E cleanup paths that requires another immediate rewrite.
4. The M1F report declares 13 Python files AST-parsed, full-delta whitespace check exit 0, and the sole focused test command completed with 24 passed in 0.85 seconds. These are implementer-reported results; ChatGPT did not rerun the tests.
5. The consolidated diff identifies 13 candidate paths on a clean detached base. M1E changes only windows_handle_reader.py and test_windows_handle_reader.py relative to M1D. The candidate remains isolated and is absent from main.

## Unresolved production and verification gates

- AppBootstrap still uses ReadAuthorizationCoordinator.unconfigured(); the candidate composition does not wire a production approved_workspace_root_provider or real authority chain.
- G1 independent trust root/Owner mandate, G2 production policy provider, G3 approved target resolver and same-object claim in real Windows execution remain NOT_ESTABLISHED.
- Authenticated issuer IPC, owner/process identity, production root provenance, service-owned/rollback-resistant replay state and native OS ACL/handle guarantees are not established by synthetic tests.
- Real protected file reads and directory enumeration, actual MCP transport and production server startup were not executed.
- The M1D source package reported one preliminary bootstrap invocation that might have read a local secrets script before it was stubbed. This is retained as a prior-run limitation; M1F did not inspect secrets or repeat that invocation.
- Authority assets remain UNKNOWN; NOT_INSPECTED. No claim is made that all possible trust assets are absent.

## Evidence classification

Artifact identity verification is not code correctness. Producer-reported tests are not independently rerun. Bounded static review is not whole-organ acceptance. Dropbox transfer is not canonical adoption. Canonical documentation adoption does not integrate product source.

## Route after reconciliation

No new source correction is selected by this review. The next decision is an Owner decision on genuinely new independently verifiable authority evidence or one specifically identified bounded prerequisite action. Do not repeat broad source inventories, fabricate an authority provider, substitute a workspace path for trust authority, activate positive protected reads, or automatically begin another source task.

~~~text
M1D_SOURCE_CANDIDATE_IN_MAIN=FALSE
M1F_SOURCE_CANDIDATE_IN_MAIN=FALSE
M1F_STATIC_REVIEW=BOUNDED_FAVORABLE_FOR_M1E_CLEANUP
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_SOURCE_COMMIT_PUSH_MERGE=NOT_PERFORMED
AUTOMATIC_FOLLOW_ON=FALSE
~~~

## Change history

This receipt documents evidence reconciliation and route selection only. No product source was edited, staged, committed, pushed, merged, executed or read by ChatGPT during this review.