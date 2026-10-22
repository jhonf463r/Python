# M1 — Codex report of partial isolated implementation (2026-10-22)

## Provenance and verdict

Provenance: `OWNER_REPORTED` — the Owner pasted a result attributed to the existing Codex development session. This coordinator has not independently fetched the candidate's local diff; the reported working-tree blobs are not yet available from the published repository. Treat implementation details and local environment claims below as reported, not independently source-confirmed.

```
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
M1_STATUS=IMPLEMENTATION_STATIC_PARTIAL
CANDIDATE_SOURCE=OWNER_REPORTED_LOCAL_DIRTY_CANDIDATE
CANDIDATE_BASE_AND_HEAD=cb2f2b02ade297660431e7bbd5d0dce75d10e39c
CANDIDATE_COMMIT=NONE_REPORTED
CHANGED_FILES=2_REPORTED
TARGET_SCOPE_REPAIR=OWNER_REPORTED_NOT_INDEPENDENTLY_REVIEWED
SCOPED_READ_REQUEST_APPROVAL_FLOW=NOT_IMPLEMENTED
READ_AND_LIST_AUTHORITY_CHECK=FAIL_CLOSED_REPORTED
TESTS=NOT_RUN
GIT_DIFF_CHECK=PASS_REPORTED
ACTIVE_SERVER_IDENTITY=UNVERIFIED
LIVE_CHECKOUT_IDENTITY=UNVERIFIED
REAL_LOCAL_READ=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
```

## Candidate identity as reported

- Folder: `C:\temp\IABV_M1_GOVERNED_READ_CANDIDATE_20261022`
- Local branch: `codex/m1-governed-scoped-read-route-20261022`
- Base and current HEAD: `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`; two modified files, no commit.
- Sparse clone reportedly contained `IABV_v1.5/src` and `IABV_v1.5/tests`; `IABV_v1.5/data` reportedly absent.
- Owner's dirty checkout, data and SQLite were reportedly not inspected or modified.

These are not independently verified by this coordinator. The candidate diff has not been published, and no PR/commit exists from which to verify it.

## Changes reported

1. `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`: `_governance_block_for_route` reportedly separates `assistant_kind` and `target_scope`, uses finite known scopes and fails closed on unknown scopes. The author reports reconciling only the relevant logic from Sonnet-reviewed candidate `b7c3fffaec4ff3b78b1ca03ae64ead949236f504`, not adopting that branch wholesale.
2. The MCP reader/listing tools reportedly return `scoped_read_authority_unavailable` if the route gate permits the route but no verifiable scoped-read decision exists. A target-scope match correction therefore does not, by itself, grant content access.
3. `IABV_v1.5/tests/test_mcp_server.py`: nine regression tests reportedly added and four existing tests adjusted for global/applicable/unknown/non-applicable scopes and denial without scoped authority. The tests were not run.

Reported working-tree blob IDs:
- `server.py`: `14eaa660b6f3ef66ae44638a551407ac37e8aa71`
- `test_mcp_server.py`: `8ebd2c737ce6a3f3ef2336912a2ec9823ecc138d`

Those object IDs are supplied by the Owner's pasted Codex report; they have not been resolved from the remote repository or inspected independently.

## Administrative route deliberately not implemented

Codex reports that the checked source did not demonstrate a trusted Owner-principal enrollment/verification route, secure/correlated IPC between the MCP paths and Control Center, independently verifiable custody/integrity of operation receipts, or race-resistant opened-object containment. Active MCP transport authentication remains unverified. No remote administrative MCP grant or block-release operation was added, and the existing observation permission was not reused.

This conservative stop is appropriate. A request record or UI click is not authority; a read grant cannot release a governance block. A source-level correction cannot establish that it explains any live server denial because live server/checkout identity and active block state remain unverified.

## Independent adjudication and next action

Do **not** label M1 `PASS`. Current classification is `IMPLEMENTATION_STATIC=PARTIAL`; the scope fix, new error path and tests remain owner-reported until the exact diff is independently reviewed. The minimum next artifact is the full unified diff for these two paths from the isolated candidate, supplied as text/patch without running tests or publishing/merging it. Review the diff for scope truth tables, denial paths, compatibility/regression risk and test coverage. Test execution remains unauthorized. Do not inspect the Owner's actual dirty checkout, `data/`, SQLite, secrets or live runtime.

Until a supported authority/issuer, authenticated Owner principal, server/checkout identity, trustworthy per-operation decision/receipt and independent block-release authority are evidenced and separately authorized:

```
SUPPORTED_SCOPED_READ_ROUTE=NOT_IMPLEMENTED_OR_VERIFIED
SCOPED_READ_REQUEST_APPROVAL_FLOW=NOT_IMPLEMENTED
GOVERNANCE=KEEP_BLOCKED
REAL_LOCAL_READ=NOT_RUN
TESTS=NOT_RUN
REAL_TRANSPORT=NOT_RUN
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
```
