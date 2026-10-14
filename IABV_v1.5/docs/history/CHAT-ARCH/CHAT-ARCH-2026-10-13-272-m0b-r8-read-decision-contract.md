# CHAT-ARCH-2026-10-13-272 — M0B-R8 contract for a dedicated repository-read decision

- Episode ID: CHAT-ARCH-2026-10-13-272
- Reported local time (America/Bogota): 2026-10-13, after Entry 271
- Documentation baseline before this write: `main` verified identical to `19bd5559c98fa771092f840dd3c2554fbcd9cd50`
- Source baseline used for prior findings: `559f4ea20a9a9163cd9a9839b11d9991933f8c07`
- Source inputs: Entries 269–271; R5 contract design; R6/R7 bounded public-source reconciliations
- Result: `M0B_R8_READ_DECISION_CONTRACT_SPECIFIED_NOT_IMPLEMENTED`
- Governance posture: `KEEP_BLOCKED` for local M0A read, source implementation, tests/runtime, and IABV/Codex/App Server launch.
- Work in this entry: contract design and documentation only. No source code, local checkout, runtime, tests, credentials or authentication were accessed.

## 1. Decision summary

R8 specifies a *proposed contract*, not an existing capability. The reuse search is complete within the approved bounded scope and found a partial generic approval workflow, but no verified human-principal-to-repository-read authority chain. R8 does not reinterpret `HumanApprovalBroker`, `ApprovalMemory`, `ExternalActionAuthorization`, the `approved_by` field, status `VALIDATED`, or observation permissions as a read grant.

The proposed boundary has three separate operations:

1. **Read-only diagnostic** — reports the narrow, applicable block/permission reason and identifying references. It never reads repository content and never grants permission.
2. **Interactive request and decision issuance** — presents the exact target, operation, allowed paths, limits and expiry; accepts only a fresh, interactive approval with independently verified principal provenance; then issues a distinct repository-read decision through a trusted authority. A positive generic `ApprovalResult` is necessary at most, not sufficient.
3. **Guarded reader** — independently verifies the decision, current target identity, path, operation, time, revocation, budget and any separately required block release immediately before every file read or directory listing. Any missing or mismatched element denies the operation.

This contract is intentionally reuse-first but it does not claim the currently inspected broker can satisfy the identity/provenance requirement. The trusted principal source, legitimate issuer, decision-integrity mechanism and local target identity remain unproven. Contract acceptance cannot unlock local M0A.

## 2. Normative terms and separation of concerns

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** express requirements of this proposed design.

- A **diagnostic** is descriptive evidence only. It MUST NOT return a bearer capability or implicitly authorize a retry.
- An **approval receipt** records the direct approval event and the identity/scope the user actually accepted. It is evidence supplied to the issuer, not a reader grant.
- A **read decision** is the independent, narrowly scoped authority object produced after receipt and identity verification. It MUST be bound to the current execution target and a finite read budget.
- The **issuer** validates approval provenance, target proof and policy; it constructs the decision using a trusted local authority boundary.
- The **verifier** is enforced at the reader boundary, not merely by the requesting client. It rechecks decision integrity, target identity and all constraints for every read/list operation.
- A **read receipt** is an audit record of an attempted/allowed/denied operation. It is not itself permission.
- An existing governance block remains in force unless an independently authorized decision explicitly resolves the specific applicable block through a proven supported mechanism. No implicit override is permitted.

The diagnostic, approval event, read decision, and operation receipt are separate contracts and must not be collapsed into one `approved` boolean.

## 3. Proposed data contracts

The following fields describe semantics, not a request to implement these structures immediately. Names are illustrative and subject to schema review.

### 3.1 Target identity evidence

The server MUST obtain target identity from its own execution context or a trusted server-side resolver; it MUST NOT trust caller-supplied identity strings as proof.

The identity bundle should include:

- `server_instance_id`: identity of the actual MCP server process/instance handling the read request.
- `workspace_id`: server-side workspace identity.
- `repository_id`: canonical repository identity where available.
- `checkout_id`: stable identity of the exact worktree/checkout, including canonical root identity and Git worktree/common-directory identity as available.
- `checkout_state_id`: server-produced fingerprint or version for the checkout state to which the grant is bound. It must account for a detached HEAD and dirty worktree; a clean checkout MUST NOT be a precondition merely to preserve evidence.
- `head_ref_state`: commit/ref identity as supporting metadata, including detached state. HEAD alone is insufficient because it does not represent dirty working-tree content.
- `identity_observed_at` and `identity_provenance`: when and how the server established the identity.

If the server cannot distinguish the intended checkout from another workspace, if identity is caller asserted only, or if the identity changes between approval and use, the grant MUST be denied. The identity resolver and state fingerprint do not currently have a proven implementation in the inspected route; they are requirements, not claims about M0A.

### 3.2 Approval receipt

A candidate receipt MUST bind one direct interactive confirmation to the exact scope displayed to the Owner:

- `approval_request_id` and one-time `challenge_nonce`;
- `principal_id` plus authenticated-principal provenance from a trusted identity source;
- `approval_mode = fresh_interactive`;
- `interactive_event_id` and `approved_at`, backed by the trusted UI/authority flow;
- `scope_digest`, computed over the target identity, permitted operation classes, exact allowed paths, resource limits, expiry and purpose actually shown to the approver;
- `decision = allow` or `deny`;
- `issuer/audience` binding identifying the intended reader or authority service;
- integrity/authenticity evidence checked by the issuer.

The approval system MUST reject the receipt if the principal is missing/unverified, the nonce is stale/replayed, the scope digest differs, or the receipt is expired. Free-form `approved_by` is descriptive metadata only and MUST NOT be accepted as identity evidence.

**Fresh-human rule:** `ApprovalResult.approved = true` alone is insufficient. Where direct contemporaneous Owner approval is required, the issuer MUST reject `auto_resolved = true`, any ApprovalMemory match, a stored preapproval policy, a missing UI event, or an unverified/absent authenticated principal. The current HumanApprovalBroker result schema does not itself establish all this evidence; no existing adapter may be assumed.

### 3.3 Read decision

A decision, if legitimately issuable, MUST contain at least:

- `schema_version`, unique `decision_id`, `decision = allow/deny`, and an unambiguous decision `purpose`;
- `issuer_id`, `audience` / intended reader, verified `principal_id`, and reference to the approval receipt;
- full target binding: `server_instance_id`, `workspace_id`, `repository_id`, `checkout_id`, `checkout_state_id`;
- allowed operation class(es): initially only `read_file` and `list_directory`;
- exact relative path allowlist and, only if explicitly needed, explicit directory-listing entries; no wildcard expansion by default;
- finite budgets: per-file bytes, cumulative bytes, read-call count, listing-call count, entries per listing and cumulative entries;
- `issued_at`, short `expires_at`, optional revocation state/reference, and a reason code;
- explicit references to the only block IDs the authority is permitted to release, if any, plus evidence that this release decision is supported by the governance system;
- integrity/authenticity protection verifiable by the reader-side verifier.

For initial policy review, propose a **maximum five-minute lifetime**, one checkout-state binding, and finite per-decision read budgets. These are conservative design defaults to be reviewed; they are not claims about existing configuration. A single decision may cover several reads only within its exact allowlist and atomic cumulative budgets. Budget checks MUST be concurrency-safe so parallel calls cannot exceed the total allowance. Expiry or identity change invalidates the decision. Renewal requires a new approval/issuance cycle; automatic renewal is not allowed.

The decision MUST be issued and held in a trusted server-side authority boundary or have equivalent authenticity protections. The reader MUST NOT accept an arbitrary client-supplied JSON object as sufficient proof of authority.

### 3.4 Read-operation receipt

For every attempt, including denied attempts, the reader SHOULD emit a durable, correlatable record containing:

- `decision_id`, `approval_request_id`, `operation_id`, and a unique `result_id`;
- operation type; normalized relative path or a policy-approved path reference; target/checkout identity reference;
- allowed/denied result, stable reason code, timestamp, bytes/entries consumed and remaining budget;
- verifier and reader version identifiers; relevant block/revocation reference;
- result/content digest where useful and safe, without copying file contents into the audit stream.

Receipts MUST NOT contain secret contents, authorization tokens, credentials, or unnecessary personal data. Receipt persistence failure must follow an explicit fail-closed policy; for this safety gate, inability to durably record a successful read receipt MUST deny the read or prevent further reads until the required audit guarantee is restored. The operation receipt is evidence of what happened, not an authorization for a later operation.

## 4. Scope and reader enforcement

### 4.1 Allowed operations

Initial scope is limited to repository file reads and single-directory listings using the already existing normal reader. The decision MUST NOT authorize shell commands, process execution, recursive scanning, writes, edits, builds, tests, launches, credential access, or network operations. These require independent authorization and are outside this contract.

An explicit directory listing is a read operation in its own right because filenames and structure may be sensitive. Listing one directory MUST NOT implicitly authorize traversal into descendants or reading any listed file.

### 4.2 Paths and existing guardrails

- Paths MUST be relative to the proven checkout root and normalized before comparison.
- Absolute paths, traversal segments, device paths, alternate data streams, and any path form that escapes the root MUST be rejected.
- Symlinks, junctions, mount/reparse points, case folding and platform-specific path normalization MUST not permit an allowlisted-looking path to resolve outside the approved root. If containment cannot be proved, deny.
- Exact path matches are the default. Any directory-prefix grant must be explicitly shown and approved as a bounded directory scope; no implicit globs.
- Existing sensitive-file denial and workspace-containment controls remain mandatory. The decision can narrow existing access but cannot weaken current reader restrictions.
- Preserve established ceilings: at most **1 MiB per file** and **200 entries per directory listing**. The decision may specify lower values; it MUST NOT raise those ceilings without a separate, evidence-backed design and authorization.
- Enforce both per-call limits and aggregate decision budgets before reading data or returning directory entries.
- No broad world-model snapshot, hidden fallback reader, alternate tool or route-around is a substitute for the authorized reader.

### 4.3 Applicable governance blocks

A read decision does not globally disable the audit block. If a block applies to the target operation, the verifier MUST deny unless the decision references that exact block and a supported trusted authority explicitly issued a release for it. An unknown block identifier, ambiguous target scope, or missing release semantics means deny. A generic `approved=True` or a read grant for different paths cannot release the block.

The implementation must keep diagnostic permission and read permission distinct. Diagnostic output may include relevant block IDs/statuses/categories and reason/provenance codes, but MUST not expose file content or be accepted as a grant.

### 4.4 Revalidation for every operation

Immediately before each read/list, the server-side verifier MUST check:

1. decision schema, authenticity/integrity, issuer and audience;
2. decision status, not revoked, not expired, and expected target binding;
3. identity of the actual server, workspace, repository and checkout state;
4. valid reference to a fresh interactive approval receipt and trusted principal;
5. operation and normalized path within the exact allowlist;
6. no disallowed sensitive path and no root/containment escape;
7. applicable governance block and any explicit supported release;
8. atomic remaining budgets, per-file/per-list limits and aggregate limits;
9. durable receipt/audit capability if required by policy.

Any failure is a denial, with a stable reason code and without reading file contents. Decision state cannot be cached across a target identity change. If the worktree state changes while a decision is active, the checkout-state binding must fail and require a new decision.

## 5. Proposed state model

Proposed state transitions:

- `REQUESTED` → request created, target and exact scope prepared.
- `AWAITING_INTERACTIVE_OWNER` → request presented with target, paths, limits, expiry and purpose.
- `DENIED` → rejection, timeout, cancellation, automatic preapproval, absent UI, unverified principal or incomplete evidence.
- `ISSUED` → only after direct fresh approval, trusted principal verification, validated scope and target binding, and successful decision issuance.
- `ACTIVE` → decision verified by the target reader and within expiry/budget.
- `REVOKED` / `EXPIRED` / `EXHAUSTED` → no further access.
- `CONSUMED` → when policy specifies single-operation use or all finite budgets are exhausted.

No state may transition from generic `APPROVED` straight to `ISSUED` without the required identity, target, scope, interactive event and decision-integrity checks. Missing/unknown status MUST be denial. The state labels above are proposed; they do not describe any current implementation.

## 6. Fail-closed cases

The verifier MUST deny when any of the following holds:

- target identity, checkout state, owner principal, issuer, audience or integrity evidence is missing or cannot be independently verified;
- receipt is from ApprovalMemory, is marked `auto_resolved`, lacks a direct event or has a replayed challenge;
- approval's displayed-scope digest differs from the requested operation or any path/limit was changed after confirmation;
- path is not explicitly allowed, resolves outside the checkout, hits a denied sensitive path or cannot be safely normalized;
- the decision is stale, expired, revoked, exhausted, or intended for another server/workspace/checkout;
- a required governance block-release mechanism is absent or does not match the active block;
- the read/list call would exceed a per-call or total budget, or concurrent consumption cannot be updated atomically;
- the reader cannot durably account for the decision/operation under the configured audit requirement;
- implementation encounters any unmodeled status or inconsistent metadata.

Denied attempts must not fall back to another path or tool.

## 7. Non-executed conformance-test specification

These are future acceptance tests, **not executed now** and not authorization to run tests. The eventual implementation is nonconforming unless it can demonstrate at least the following:

| Case | Setup | Required result |
|---|---|---|
| Missing decision | Read request has no decision | Deny before content access |
| Generic positive approval | ApprovalResult approved, but no verified receipt/principal | Deny |
| ApprovalMemory | `approved=true, auto_resolved=true` | Deny for fresh-human-required policy |
| Replay | Reuse approval nonce/event | Deny second issuance |
| Altered scope | Change target/path/budget after prompt | Scope digest mismatch; deny |
| Wrong server/workspace/checkout | Decision issued for a different target | Deny before content access |
| Dirty/detached target | Identity correctly reports dirty/detached worktree | Bind exact state; do not infer another checkout or require clean state |
| State changes | Checkout-state identity differs after approval | Deny; require a new decision |
| Path traversal/absolute path | `../`, absolute/device path or root escape | Deny |
| Link escape | Symlink/junction points outside root | Deny |
| Non-allowlisted file | Valid decision but path absent from allowlist | Deny |
| Directory listing | Parent is not an expressly allowed listing target | Deny; no recursive listing |
| Sensitive file | Path hits existing secret-sensitive rule | Deny even if decision lists it |
| Size/list cap | Request exceeds 1 MiB/file or 200 entries/list | Deny or return no more than the existing cap without weakening it |
| Aggregate budget | Total bytes/read/list count reached, including parallel calls | Deny subsequent call atomically |
| Expiry/revocation | Decision expires or is revoked between calls | Deny next call |
| Active governance block | No explicit supported release for the applicable block | Deny |
| Diagnostic-only call | Request diagnostic with no read grant | Return narrow status; read zero files; issue no grant |
| Audit receipt unavailable | Required durable record cannot be committed | Fail closed for content access |
| Client forgery | Caller submits a hand-built decision object | Reject unless verified by the trusted issuer/integrity boundary |
| Happy path | All required evidence valid and scope/budget exact | Permit only the specified file/list operation; emit a durable receipt |

Test harnesses must use controlled fixtures/intercepted I/O and must not inspect real secrets or attempt access to the blocked local M0A checkout. Any future test execution requires separate authorization.

## 8. Unresolved prerequisites and decision gates

The contract is designed, not implemented. These prerequisites remain open:

1. **Trusted principal provenance:** a supported way to verify the authenticated Owner and bind a current interactive event to that principal.
2. **Issuer and integrity boundary:** a legitimate source of a read-decision object, plus an independent verifier. Do not invent a trust root or accept unsigned caller-created data.
3. **Target identity source:** server-side proof of exact MCP instance/workspace/checkout and change detection, preserving dirty/detached worktree state.
4. **Block-release semantics:** a legitimate, auditable way to resolve the actual applicable block, or a decision to leave the reader denied.
5. **Durable accounting:** receipt persistence and atomic budgets at the point of read.
6. **Owner authorization:** a distinct approval to implement the specified contract and, separately, any eventual test/runtime operation or local M0A inspection.

This contract-only task does not resolve any of those prerequisites by declaration. The current source evidence still says the existing broker result and Devin action authorization are insufficient for repository read. The Owner does not need to collect code manually. Any future work should be AI-led within a specifically granted scope and should stop if a required trust source cannot be established.

## 9. Current posture and next action

- Status: `M0B_R8_READ_DECISION_CONTRACT_SPECIFIED_NOT_IMPLEMENTED`
- Next technical action: independent review of this contract for internal completeness and compatibility with R5's diagnostic/read separation. If adopted, record it as a design baseline.
- Do not perform another broad search of the same approval symbols.
- Do not implement, run tests/builds, launch IABV/Codex App Server, inspect credentials or access local M0A based on this document.
- Any implementation authorization must name a scope and preserve all unresolved prerequisites. A separate local read authorization is still required.
- Operational state remains `KEEP_BLOCKED`.

## 10. Continuity route

Recover in order: `docs/history/CHAT-ARCH/README.md → CURRENT-STATE.md → CONTEXT-INDEX.md → MEMORY-OPERATING-PROTOCOL.md → Entry 272 → Entries 271–269 and exact source blobs`. Entry 272 advances the next-action decision from source reuse search to contract design only. Entry 271 remains canonical for the current evidence that the generic approval workflow is incomplete.
