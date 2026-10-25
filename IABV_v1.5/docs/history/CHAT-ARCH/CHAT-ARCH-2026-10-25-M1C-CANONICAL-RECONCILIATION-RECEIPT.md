# M1C — canonical reconciliation after M1B

Date: 2026-10-25  
Task: `M1C_G1_CANONICAL_RECONCILIATION_AFTER_M1B_20261025`  
Outcome: PR #526 and PR #527 merged as documentation-only changes; five canonical front doors fetched back from live `main`. This receipt records the finalized M1C reconciliation history and verified governance state.

## Authority and scope

The Owner explicitly authorized the M1C documentation reconciliation and subsequently authorized the documentation-only PR merges. No product source changes, candidate integration, protected reads, test execution, runtime or trust provisioning occurred in M1C.

## Canonical baseline inspected

Repository: `jhonf463r/Python`  
Base `main` SHA: `4ac6045792e93c9a3033ebbfb7a34792dbf94f61`  
Prior M1B candidate base/HEAD reported by Codex: `1c86dcb43ceabf149dae3edb8b5f9530536e4ff6`. GitHub history confirms that SHA is an ancestor of `main`. At the time of the original M1C evidence reconciliation, it was three commits behind the head, through documentation-only PRs #525, #526 and #527. PR #528 subsequently merged the final route-status normalization. These commit counts and SHAs are a chronology of the observed reconciliation, not a claim about the current moving `main` head. The five canons were fetched from live `main` after the merges; source and test paths for M1B return 404 on `main`.

## M1B evidence reconciliation

Dropbox files observed:
- Report: `/IABV-IA-BRIDGE/OUTBOX/M1B_G1_OPENED_TARGET_CLOSE_RESULT_20261025.md`, file ID `id:5f9kJIcSlJAAAAAAAAADqw`, metadata size 6,462 bytes. Its readable text describes `SOURCE_CANDIDATE_ONLY` and reports one focused run of 17 passing tests, exit code 0.
- Patch: `/IABV-IA-BRIDGE/OUTBOX/M1B_G1_OPENED_TARGET_CLOSE.patch`, file ID `id:5f9kJIcSlJAAAAAAAAADqA`, metadata size 10,298 bytes. ChatGPT retrieved and inspected the patch text; the extracted text length differs by a trailing newline from metadata, so this receipt does not claim a fresh exact-byte SHA-256 computation.
- Evidence payload: `/IABV-IA-BRIDGE/OUTBOX/M1B_G1_OPENED_TARGET_CLOSE_EVIDENCE_20261025.zip.b64.txt`, file ID `id:5f9kJIcSlJAAAAAAAAADqg`, metadata size 11,040 bytes. This is Base64 text, not a binary ZIP in Dropbox. Metadata was checked; ChatGPT did not independently reconstruct the ZIP or validate all member hashes during this task.
- Superseded Base64: `/IABV-IA-BRIDGE/OUTBOX/M1B_G1_OPENED_TARGET_CLOSE_EVIDENCE_20261025_SUPERSEDED.zip.b64.txt`, file ID `id:5f9kJIcSlJAAAAAAAAADqQ`, metadata size 11,052 bytes. It remains preserved.

Codex-reported source candidate:
- Temporary checkout: `C:\Users\faber\AppData\Local\Temp\M1B_G1_OPENED_TARGET_CLOSE_20261025_twyfvhdo`
- Local branch reported: `codex/m1b-g1-opened-target-close-20261025`
- Candidate files: `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py` and `IABV_v1.5/tests/test_windows_handle_reader.py`
- Reported patch SHA-256: `1BB062B663AD218C6F853A4982EBB03BD963D8F8A1086D377BDC20ECD8D268B4`
- Reported local ZIP: 8,280 bytes; SHA-256 `E148616F39797718BB9970C3D3B16BB45DE8ECE88C62CA9AECE8B5DD6E2C8AF3`
- Reported Base64 SHA-256: `18561976BF5B3ED743C7041A6B9B1523260FC216F7829C1809E8844C2AA4DE06`

Those hashes and the test result above are reproduced as claims made in the Codex report; this reconciliation did not independently rehash those local artifacts or rerun the tests.

## Narrow static review

ChatGPT recovered the patch text from Dropbox and inspected the change to `OpenedTargetCapability.close()`. The visible source change uses a `_closing` state to serialize close calls, waits/rechecks while another close or active operation exists, clears the transient flag and notifies waiters when the underlying close raises, and marks `_closed` only following underlying success. The added test text exercises synthetic fail-then-success and idempotence, and includes a concurrent waiter/retry case.

Review verdict: `NARROW_STATIC_REVIEW_FAVORABLE`. Scope: visible diff only. The tests were not independently executed by ChatGPT; this is not whole-organ acceptance, production verification, or proof of Windows kernel/ABI semantics.

## Canonical paths changed by this PR

- `IABV_v1.5/AGENTS.md`
- `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
- `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
- `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
- `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`
- This reconciliation receipt.

The prior current-route snapshot remains in each canonical document as historical context; no historical receipt or Dropbox artifact was deleted. No product code or tests were changed by M1C. No build, test, runtime, MCP transport or protected read was executed by M1C.

## Governance and next edge

```text
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
PROTECTED_READS=FAIL_CLOSED
M1B_SOURCE_CANDIDATE_IN_MAIN=FALSE
AUTOMATIC_FOLLOW_ON=FALSE
M1C_DOCUMENTATION_RECONCILIATION=COMPLETE; PR_526_AND_527_MERGED; FIVE_CANONS_FETCHED_BACK
NEXT_ACTION=PLAN_NEXT_BOUNDED_AUTHORIZATION_ORGAN_STEP; KEEP_PROTECTED_READS_FAIL_CLOSED
```

The next technical decision must remain separate. It must address governed source-candidate integration, same-object end-to-end authorization/consumer binding, and legitimate approved-workspace-root/authority evidence. This receipt does not establish any of them and does not authorize protected reads.


## PR #526 merge and fetch-back verification

PR [#526](https://github.com/jhonf463r/Python/pull/526) was squash-merged as `452961e4c2d26a2a675eebf1ce97808149fbdce1` at 2026-10-25T22:53:39Z. The five canonical front doors were fetched from live `main` and confirmed to contain the M1B reconciliation, the unintegrated source-candidate status, and fail-closed governance. This follow-up PR corrects lifecycle labels that still said PR #526 was open.
