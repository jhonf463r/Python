# M1A G1 — next handoff: Owner-controlled bootstrap and issuer boundary

- Date: 2026-10-24, America/Bogota
- Canonical baseline: `0876466a41d63ecc7a9283971118913fa9602f6c`
- Previous candidate result: `TASK_RESULT=SOURCE_CANDIDATE_ONLY`, Owner-reported Codex report in current conversation
- Destination: Codex, same Windows session that owns the isolated local candidate
- Scope: source-code modifications and source-test authoring only
- Canonical adoption status: this handoff is a documentation candidate until this PR merges and is fetched back from live `main`

## 1. Reconciled status of the prior candidate task

Codex reports that the latest local candidate keeps HEAD `6bc568e1c5a898afd65cc045c779c25a9cdc5489`, branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, and checkout `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`. It reports source wiring from `AppBootstrap` through `MCPBridgeService`, `FastMCPServerRunner`, and `IABVMCPServer` to the two MCP read routes, with an unconfigured coordinator as the safe fallback.

The report says the seven earlier staged files remain staged and unchanged, while nine paths have unstaged changes. No tests/build/runtime/MCP were executed, no commit was created, and nothing was published.

This is **OWNER_REPORTED**. The candidate branch and HEAD are not published on remote GitHub, so this coordinator did not independently inspect the local files or verify the report's code properties.

The active task `M1A_G1_REGISTER_READ_AUTHORIZATION_IN_APPBOOTSTRAP` can be treated as source-complete for task routing only on the basis of that report. This does not mean its behavior has been tested or independently accepted.

## 2. New immediate task

`ACTIVE_TASK=M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY`

The remaining key dependency is no longer another MCP injection layer. It is a real, explicit Owner-controlled trust bootstrap/enrollment boundary binding:

1. the authenticated Owner principal;
2. an issuer identity and protected issuer signing credential;
3. the exact server instance and policy revision; and
4. the reader-side trust record that the requester/reader cannot create or replace for itself.

The candidate must have no self-asserted root, no trust-on-first-use shortcut, no caller-supplied authoritative identity, no hard-coded credential/key/Owner identity, and no class-name-only isolation claim.

## 3. Required bounded source attempt

- Verify actual checkout identity and preserve all staged and unstaged changes. Do not reset, clean, discard, commit, push, or publish.
- Refresh the remote view of `main`. The latest canonical base is `0876466a41d63ecc7a9283971118913fa9602f6c`; the report's `origin/main=fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7` is stale relative to this commit. Because the worktree is dirty, do not merge/rebase until all index and working-tree deltas are safely preserved and the exact conflict/ancestry plan is known. Never sacrifice the candidate's staged or unstaged changes to synchronize documentation.
- Reconcile local branch ancestry and the candidate `CURRENT-STATE.md` additively to the latest canonical route. Keep the now-completed wiring task in history, make this task active in the candidate, and preserve the terminal root-review result as history.
- Inspect the existing `github_owner_merge_bootstrap.py`, `windows_crypto.py`, `read_authorization.py`, and the wired MCP composition only as needed to avoid duplicating the already reported work.
- Attempt a concrete source-level Owner-controlled bootstrap using documented Windows/API semantics only where the code can accurately represent them. If WebAuthn/Hello is considered, treat it as a candidate authentication factor, not an assumed capability or independent root. A challenge/response needs correct verification, relying-party/origin binding, credential registration semantics, freshness, and replay protection.
- A legitimate issuer credential must be protected by an actual platform boundary and tied to the authenticated Owner and exact server. If that cannot be achieved without enrollment, credentials, installation, ACL changes or a system probe that is not authorized here, do not fake it; implement only a truthful fail-closed contract and report the exact missing prerequisite.
- Keep G1/G2/G3 unestablished unless supported by independently verified evidence. This task is about G1 Owner/bootstrap/issuer boundary; do not expand into a broad G2/G3 reimplementation. Preserve the existing requirement that absent G2/G3 means deny.
- Add or update source tests only. Do not execute tests, builds, runtime, protected reads, or MCP transport.

## 4. Explicit exclusions

No tests executed, build, runtime, transport, production credential/key creation, Owner enrollment ceremony, platform probes/configuration, service installation/start, persistent ACL/trust-store changes, publication, product PR, merge, deployment, spending or release. Do not change the current protected-read fail-closed behavior.

## 5. Required output

Return `TASK_RESULT=SOURCE_CANDIDATE_ONLY` or one exact blocker terminal status. Include:
- checkout/path, branch, local HEAD, freshly fetched `origin/main`;
- separate hashes/status for staged and unstaged deltas, and proof nothing was discarded;
- exact source locations for Owner ceremony, assertion/signature verifier, issuer credential handling, server binding, reader trust-record verification, and the real process/OS boundary (or exact missing boundary);
- tests authored versus executed (execution must remain `NOT_RUN`);
- dependencies added (must be zero);
- what cannot truthfully be implemented without the forbidden enrollment/OS action.

Do not claim a root exists, do not close any gate, and do not publish the candidate. Stop for targeted static review of the exact delta.

## 6. Canonical guardrails

```text
OWNER_SOURCE_SCOPE=AUTHORIZED
SOURCE_TEST_AUTHORING=AUTHORIZED
TEST_EXECUTION=NOT_AUTHORIZED; NOT_RUN
BUILD=NOT_AUTHORIZED; NOT_RUN
RUNTIME=NOT_AUTHORIZED; NOT_RUN
REAL_TRANSPORT=NOT_AUTHORIZED; NOT_RUN
CREDENTIAL_OR_APP_CREATION=NOT_AUTHORIZED
WINDOWS_SERVICE_INSTALL=NOT_AUTHORIZED
PERSISTENT_WINDOWS_ACL_OR_TRUST_STORE_CHANGES=NOT_AUTHORIZED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
READ_LIST=FAIL_CLOSED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

This handoff narrows the next engineering action and does not claim that a root is available or that runtime behavior has been established.
