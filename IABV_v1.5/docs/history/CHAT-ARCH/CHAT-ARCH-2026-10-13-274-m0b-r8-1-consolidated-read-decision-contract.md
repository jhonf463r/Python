# CHAT-ARCH-2026-10-13-274 — M0B-R8.1 consolidated repository-read decision contract

- Episode ID: CHAT-ARCH-2026-10-13-274
- Review date: 2026-10-13, America/Bogota
- Continuity baseline before this entry: `main` at `c4825368b12884189e03e8407d605fcf12776507`
- R8 contract reviewed: Entry 272, blob `5a55a9dd4ca2d7e16ee727950111a093470bf8b4`
- Independent R8 review/addenda: Entry 273, blob `95af07a969cd25f0ce205fdaf4f9618562b8f15d`
- R5 governance/source reconciliation: Entry 269, blob `05fe1fe713e6282ba5e1e7338bec93ec92d99d53`
- Input: Owner-supplied M0B-R8.1 adversarial report; report says its reviewer read Entries 272/273 and relevant sections of continuity documents, **not code**.
- Result: `M0B_R8_1_CONSOLIDATED_CONTRACT_PROPOSED_PENDING_SECOND_CHALLENGE`
- Operational posture: `KEEP_BLOCKED`

## 1. Adjudication

The R8 architecture's five authority boundaries are retained, but Entry 272 plus Entry 273 was not ready to be treated as a consolidated design baseline. The adversarial report identified 12 documentary gaps (F-01–F-12). This entry consolidates the normative rules, including the two Entry 273 addenda, instead of treating a chain of amendments as the effective contract.

**This is a proposed contract, pending a second focused adversarial review. It is not code, an implemented capability, an authorization to implement, or permission to access local M0A.** No code was read for this episode and no source/runtime claim from the report is upgraded to an independently verified implementation fact.

## 2. Five separate authorities

The system MUST keep these separate:

1. **Diagnostic:** returns only the minimal metadata needed to explain an applicable block. It reads no repository file and grants no permission.
2. **Fresh approval evidence:** records the scope an authenticated Owner explicitly approved through a trusted interactive UI.
3. **Read decision:** a trusted issuer creates a distinct server-side decision after verifying the approval evidence, target, scope and policy.
4. **Reader verifier:** the actual file/list reader independently checks authority and constraints immediately before each operation.
5. **Operation ledger/receipt:** a durable, tamper-evident record of intent and outcome. A receipt is evidence, never authority.

No stage may be collapsed into an `approved` boolean. Diagnostic output, approval results, `approved_by`, `VALIDATED`, ApprovalMemory results, Devin action authorization and observation permissions are not repository-read authority.

## 3. Normative v1 approval policy (closes F-01 and F-02)

For `read_file` and `list_directory`, **fresh interactive Owner approval is mandatory and unconditional in v1**. An agent-configurable, project-configurable, memory-derived or caller-supplied policy cannot relax it. Automatic approvals, stored preapprovals, `auto_resolved=true`, absent UI events, missing principals and generic positive results MUST be rejected before issuance. No exception path is defined in v1. Any future exception requires a separately reviewed contract revision and Owner decision through a channel not controlled by the requesting agent; it cannot be activated by changing an ordinary policy value.

The trusted issuer, not the requester, creates the request ID, challenge nonce, `interactive_event_id`, canonical target evidence and scope digest. The nonce is visible only to the trusted approval UI/authority and MUST NOT be returned to, supplied by, or readable by the requesting agent. The UI returns its attestation directly to the issuer. The issuer re-derives diagnostic/block identifiers from authoritative server-side state; it MUST NOT accept a requester-echoed identifier as proof.

The approval UI MUST show the complete scope before confirmation: exact target/workspace/checkout, operation, exact path/listing entries or permitted directory target, byte and call budgets, expiry, purpose, and intended downstream recipient (including an external AI/provider if content will be sent there). It MUST show raw and normalized path forms, visibly escape control/non-printable and bidirectional characters, and refuse approval if any part is truncated, ambiguous or cannot be rendered safely. The digest is calculated by the issuer over the exact canonical scope displayed. The request path MUST enforce rate limits and deduplicate retries. Approval from an event the requesting agent can synthesize, intercept, replay or forge MUST fail verification.

## 4. Mandatory target, checkout and scope identity (closes F-06 and F-09)

The server MUST derive identity from its own trusted execution context or a trusted target resolver. The requester cannot assert identity strings as proof.

The mandatory target binding for v1 is:

- authenticated MCP server instance and reader identity;
- server-side workspace registration ID;
- checkout-root filesystem identity, including volume/device and stable file-object ID, not merely a path string;
- trusted worktree/repository-control-directory identity (including worktree-specific Git directory identity where applicable);
- a server-issued checkout registration/lifecycle ID that distinguishes a deleted/recreated root at the same pathname;
- the server-known HEAD/ref state, including detached state, as metadata where applicable;
- identity of each expressly authorized path object as bound/observed by the trusted resolver, plus a result digest for bytes actually staged/read.

A canonical repository ID is useful provenance but MUST NOT substitute for checkout identity. If a mandatory identity component is unavailable, unstable or contradictory, deny. Dirty or detached worktrees are not automatically denied; their state must not be silently treated as clean.

**No pre-authorization whole-worktree content scan is allowed to calculate identity.** The resolver MUST NOT recursively read files, open sensitive/unapproved paths, spawn Git/shell processes or use an arbitrary repository hook to compute a dirty-state fingerprint. The contract's state binding is scope-local: stable root/worktree identity, trusted ref metadata, and the specifically allowed path objects. Changes to an authorized path, root identity, worktree identity or relevant trusted ref binding invalidate the decision. Changes outside the authorized path scope neither expand the grant nor cause the system to read those paths merely to recompute a global dirty-tree digest. If the implementation cannot establish the required identity without out-of-scope I/O, it MUST deny.

Before approval, the resolver may obtain only the metadata necessary to present/identify the target and allowed path objects; it MUST NOT expose repository contents as part of identity discovery. The reader rechecks the target and authorized-object binding at operation time and after staging, before delivering content. This is a scoped authorization contract, not proof that any current resolver implements it.

## 5. Approval receipt and server-side decision custody (closes F-03)

A valid approval receipt MUST bind a one-time challenge, the verified Owner principal and provenance, the direct interactive UI event, the exact scope digest, decision, timestamps and intended reader/audience. `approved_by` text alone is never identity evidence. Receipt verification MUST reject nonce/event replay, mismatched scope, expired challenges, unverified principals and attestations from an unintended UI/issuer.

In v1 the read decision MUST be an authoritative **server-side ledger record**, not a transferable bearer object. The issuer atomically records the decision and its finite budgets in the ledger and returns only a non-authoritative reference/ID to the intended requesting server session. The decision MUST be bound to the authenticated requesting connection/session and intended reader/target; another session cannot redeem it. Session identity comes from trusted server context, not from a caller-selected string.

An unknown `decision_id`, absent record, ledger inconsistency, ledger loss, failed atomic write or unavailable ledger MUST deny. After restart, the reader must recover authoritative budgets and unresolved intents before serving reads. If this cannot be done, it MUST remain unavailable for reads; it MUST NOT recreate budgets from the caller, a signed copied object or in-memory defaults. A self-contained signed bearer-token alternative is OUT OF SCOPE for v1.

## 6. Read decision fields, timing and revocation (closes F-10 and part of F-11)

The server-side decision MUST record schema version, unique decision ID, authenticated Owner principal reference, approval receipt reference, request/session ID, issuer, intended reader, target/checkout binding, operation class, canonical explicit path allowlist, displayed purpose/recipient, finite atomic budgets, issue/approval timestamps, expiry, approval-policy version, status, and the separately verified governance-release attestation reference if one is ever supported.

Proposed conservative v1 timing defaults (design proposals, not existing code facts):
- approval challenge nonce TTL: at most 120 seconds;
- interactive approval-to-issuance interval: at most 60 seconds;
- decision lifetime: at most five minutes from trusted server issuance.

The issuer and reader MUST use a trusted server clock for recorded wall-clock evidence and a monotonic clock for in-process expiry/elapsed-time checks. The verifier checks freshness at issuance, when reserving each operation intent, and again before releasing staged content. Expiry or revocation during an operation means staged content is discarded and not delivered. The authoritative revocation source is mandatory; if it cannot be queried or its response is inconsistent, deny and do not release content. Revocation must be possible through an authenticated Owner/governance path outside the requesting agent's control. Renewal requires a new fresh approval and new issuance.

The field `purpose` explains user intent and is included in what the UI shows and in the scope digest; it does not independently grant authority.

## 7. Separate governance-block release (closes F-04 and F-08)

**In v1, a repository-read decision cannot release a governance block.** The read issuer and reader MUST NOT have implicit authority to create or infer a block release. If any active block applies and no independently supported release attestation exists, return terminal `BLOCK_RELEASE_UNSUPPORTED` and deny. This is the required behavior for the currently unproven release mechanism; it is not a temporary permission to bypass the block.

A future release, if separately designed and authorized, MUST be a distinct artifact issued by the trusted authority that owns the relevant governance block. It must bind at least the block ID, block revision or content digest, target identity, exact operation/scope, authority/principal, issue time and expiry. The reader verifies that artifact independently. Reusing a block ID after its semantics/content change does not preserve an older release.

The applicability evaluator MUST use the authoritative, versioned set of supported scope dimensions. The server derives assistant and target identity. It MUST define combination semantics explicitly:

- every active block that applies to the request MUST be accounted for;
- an applicable block without a valid independent release causes denial;
- unknown/malformed/unsupported scope, incomplete target identity, partially evaluable/conflicting block metadata or unavailable authoritative scope semantics fail closed as `BLOCK_SCOPE_UNEVALUABLE` (or a more specific stable denial code);
- a block can be declared non-applicable only when trusted target identity is established and the authoritative scope model proves the mismatch;
- where multiple blocks apply, all must be independently released; one release cannot cover another block unless its artifact explicitly and validly names it.

The known `assistant_kind` versus `target_scope` discrepancy from Entry 269 is an independent hazard. It is not a demonstrated cause of the M0A denial. Before any implementation planning, the authoritative scope model and combination semantics are a prerequisite; do not invent production scope dimensions from the test matrix.

## 8. Race-resistant reader/path enforcement (consolidates 272 §4.2/§4.4 and 273 §3; closes F-07)

The reader performs string normalization and traversal checks only as early rejection. Such string checks MUST NOT be the final containment proof.

The reader MUST pin the approved root using a handle and stable root identity, then perform traversal/open/list operations relative to that pinned root using race-resistant handle-based operations or a platform-equivalent implementation that meets all of these acceptance criteria:

1. no path component can be swapped after checking to redirect an operation outside the approved root;
2. reparse points/symlinks/junctions cannot silently redirect reads or listings outside the approved root;
3. the actual opened object identity and containment are checked before any content is read;
4. the same verified handle/object is used for reading/enumeration, with no second name-based resolution;
5. final allowlist and sensitive-path policy are applied to the actual resolved object/path, accounting for platform aliases, case normalization, device paths, alternate data streams, short names, trailing dots/spaces and Unicode/control/bidi confusables;
6. path/root/target change during an operation prevents release of staged content;
7. if equivalence cannot be demonstrated on the target platform, deny with `CONTAINMENT_UNPROVEN`.

The v1 default is to reject any link/reparse traversal in authorized paths and directory listings; do not disclose link targets. Hard-linked objects MUST be denied unless the implementation can prove they do not defeat checkout containment or permit content to be read outside the approved object scope. Use least access on open and close the handle without reading whenever type, identity, allowlist or containment verification fails.

For a file, read at most the permitted cap plus one byte to detect overflow. If the cap is exceeded, deny with `FILE_LIMIT_EXCEEDED` and release no content. A pre-read size check alone is insufficient.

For a directory list, the exact directory itself must be explicitly allowed. Enumerate no more than 201 entries to detect overflow; if more than 200 would be returned, deny the entire listing with `LIST_LIMIT_EXCEEDED` and disclose no partial names. If within the cap, validate every entry, sort deterministically, and omit/reject reparse points without resolving or revealing their destinations. A directory listing never grants traversal or file reading.

## 9. Budgets and mandatory durable audit ledger (closes F-05 and F-11)

Durable accounting is **unconditional for every operation that can return repository content**. Policy may impose stricter requirements but cannot disable intent/completion records for v1.

Before opening/reading content, the reader MUST atomically reserve the request/session-bound operation ID and the maximum permitted byte/entry/call budget in a durable, append-only or tamper-evident ledger controlled by the trusted authority and outside the requesting agent's write/delete scope. Concurrent operations must not overspend shared budgets. Denied attempts remain denied even if their denial record cannot be written; a failed or absent ledger never authorizes a read.

The record lifecycle is:
1. durably commit an intent and budget reservation;
2. perform the operation through the verified handle;
3. stage the result and recheck target, policy, expiry, revocation and blocks;
4. durably commit completion with stable result code, actual byte/entry consumption, object/target identity reference and a safe digest;
5. only then release staged content to the caller.

Receipts MUST NOT include file contents, secrets, credentials or unnecessary personal data. Count bytes actually read and entries actually consumed. A reservation is not refunded after an internal content read; if the completion commit fails, the reserved budget remains charged/unresolved. No content is delivered when completion cannot be durably committed.

If a process crashes after intent but before completion, that intent is `UNRESOLVED` at recovery. The reader MUST NOT serve new read requests until the ledger is recovered and the intent has been reconciled through an authenticated Owner/governance procedure, with its own durable audit record. The system must preserve a persistent halt or fail-stop the reader if it cannot durably persist that halt. An unavailable ledger or revocation source means no reads, including after restart. There is no in-memory-only budget reset or silent orphan-intent cleanup.

## 10. Scope and hard limits (resolves remaining F-11 ambiguities)

V1 supports only `read_file` and non-recursive `list_directory`, over exact relative file paths or exact directory paths explicitly displayed and approved. **Directory-prefix grants and wildcard grants are excluded from v1.** A separately named directory-list operation does not grant access to children.

Initial hard ceilings remain:
- maximum bytes read from one file: 1 MiB;
- maximum entries disclosed from one listing: 200.

A request above a hard ceiling is denied as a whole; no partial content/listing is disclosed. Decisions may lower the ceilings but cannot raise them in v1. All finite aggregate budgets (bytes, read calls, list calls, entries) are reserved atomically before operations. On success, account actual bytes and entries. After internal content has been read, never refund the reservation merely because the completion record failed.

No command execution, recursive scan, write/edit, build, test, process launch, credential access or network operation is authorized by this read decision.

## 11. Required conformance matrix (consolidates F-12)

These cases are proposed; none has been executed. Fixtures must be synthetic and isolated from M0A and real secrets. OS race guarantees require a real temporary filesystem on the eventual target platform with a controlled substitution hook; mocked/intercepted I/O alone is insufficient to prove TOCTOU resistance.

| Case | Condition | Required result |
|---|---|---|
| A1 | Missing/unknown decision or missing server-side ledger record | Deny before content access |
| A2 | ApprovalMemory auto-resolution, relaxed caller policy, forged/missing UI event or principal | Reject at issuance; no decision |
| A3 | Nonce/event replay or wrong requester session | Deny; no cross-session redemption |
| A4 | Incomplete/truncated/ambiguous UI rendering or raw/normalized path mismatch | No approval accepted |
| A5 | Scope/target/path/budget changed after approval | Digest or target binding mismatch; deny |
| A6 | Wrong server/workspace/root/worktree/checkout lifecycle identity | Deny before reading |
| A7 | Dirty or detached checkout with provable target identity | Do not require clean state; bind supported target/path metadata |
| A8 | Requested allowed-path object replaced or mutated between authorization and delivery | Deny or discard staged content; no unverified bytes delivered |
| A9 | Path substitution between pre-check and open; root replaced; symlink/junction/reparse escape | Read only the exact verified object or deny; never disclose outside-root content |
| A10 | Hard-link alias whose containment cannot be proven | Deny |
| A11 | Global, assistant-scoped, resource/workspace/checkout-scoped, nonmatching, multiple or partially known blocks | Explicit model-based result; all applicable blocks require separate valid release |
| A12 | Unknown scope, no trusted target identity or no authoritative scope semantics | `BLOCK_SCOPE_UNEVALUABLE`; deny |
| A13 | No independent supported block release | `BLOCK_RELEASE_UNSUPPORTED`; deny |
| A14 | Same block ID but changed revision/digest after release | Old release invalid; deny |
| A15 | Unknown/down revocation source, expiry during operation or expired nonce | Deny or discard staged content |
| A16 | Request above 1 MiB or listing above 200 entries | Deny whole operation; release no partial result |
| A17 | Parallel calls consume final shared budget | Atomic ledger admits only operations within budget |
| A18 | Crash/restart after intent, lost ledger, or orphan intent | No read until durable Owner/governance reconciliation |
| A19 | Audit sink unavailable before read | Deny before content access |
| A20 | Completion commit fails after internal read | Deliver no content, keep budget charged, persistent halt/fail-stop, unresolved reconciliation |
| A21 | Alias path, ADS, short name, Unicode confusable, trailing dot/space or path traversal | Deny unless canonical policy can prove exact safe identity |
| A22 | Successful fully authorized operation | Read exactly permitted object within limits, durable completion first, then release content |

## 12. Resolution map for adversarial findings F-01–F-12

- **F-01 approval policy conditionality:** closed at contract level; fresh interactive approval is unconditional for v1 and cannot be agent-relaxed.
- **F-02 requester/UI channel and scope display:** closed at contract level with issuer-only nonce, direct UI-to-issuer attestation, full safe display, scope digest, rate limiting and deduplication.
- **F-03 decision replay/ledger custody:** closed at contract level by server-side ledger authority, session binding, atomic budget persistence and fail-closed recovery; bearer-object alternatives excluded from v1.
- **F-04 read issuer implicitly releasing governance blocks:** closed at contract level; separate governance-owned release artifact required, with v1 terminal `BLOCK_RELEASE_UNSUPPORTED` absent a proven mechanism.
- **F-05 optional audit:** closed at contract level; durable intent/completion and persistent unresolved recovery are mandatory for content delivery.
- **F-06 global checkout-state fingerprint requiring unauthorized reads/processes:** closed at contract level by scoped identity/path-object binding; no full-tree scan or Git subprocess. Relevant authorized-object/target changes invalidate; unrelated paths are never read to recompute a global digest.
- **F-07 TOCTOU acceptance gaps:** closed as normative acceptance criteria, not as an implementation claim; root handle pinning, same-object operations and OS-level race tests required.
- **F-08 block combination/dimensions:** policy now says every applicable block must be separately released; supported scope model and dimension enumeration remain a prerequisite, and unknown scope denies.
- **F-09 optional checkout identifiers:** closed at contract level; checkout-root object identity and server-issued lifecycle/worktree identity are mandatory; path strings or repository IDs alone are insufficient.
- **F-10 revocation/freshness/time:** closed at contract level with mandatory authoritative revocation, fail-closed outage, specified proposed timing defaults, trusted/monotonic clocks and check-before-delivery.
- **F-11 prefixes/caps/accounting ambiguity:** closed at contract level: no prefix/wildcard grants in v1, reject over-cap requests as a whole, exact budget/receipt semantics.
- **F-12 conformance gaps:** addressed by matrix A1–A22, including failure-after-read, session replay, ledger restart, policy flip and real filesystem race cases.

“Closed” above means **the text gap has a normative proposed resolution**. It does not mean the implementation or real platform behavior is proven. The next adversarial review may reopen any item with a concrete counterexample.

## 13. Provenance and remaining unknowns

- `PROVEN_BY_SOURCE` (document text only): Entries 272/273 contain the clauses identified by the reviewer. The report states that no code was read; it cannot prove runtime or code behavior.
- `OWNER_REPORTED`: prior sessions report a blocked local M0A reader and distinguish M0A from other worktrees. This episode did not inspect local M0A or independently reproduce the block.
- `PROPOSED`: every normative rule and timing default in this consolidated R8.1 document, plus conformance matrix A1–A22.
- `UNPROVEN`: authenticated Owner principal provenance; production issuer, ledger integrity and verifier; actual server/workspace/checkout identity; target-platform handle-based containment implementation; authoritative block-scope model; any independent block-release mechanism; real revocation source; and whether a compliant local implementation exists.

No technical fact is elevated from a proposed contract to an existing capability.

## 14. Current status and next actor

- Status: `M0B_R8_1_CONSOLIDATED_CONTRACT_PROPOSED_PENDING_SECOND_CHALLENGE`.
- Next actor: **Sonnet/Claude**, one focused adversarial review of this consolidated Entry 274.
- Review scope: verify closure of F-01–F-12, look for contradictions introduced by consolidation, and challenge session/ledger custody, in-scope state identity, OS path containment and governance-block combination only. Do not start broad source archaeology or implementation.
- If the review passes, ChatGPT/coordinator may register R8.1 as the accepted design baseline. That still does not authorize implementation, testing, runtime or local M0A access.
- If repairs remain, add only concrete counterexample-driven amendments, then perform one targeted re-review.

Operational state remains **`KEEP_BLOCKED`**. No local M0A access, reader retry/bypass, code modification, test/build/runtime, credential inspection, authentication, software installation/update or IABV/Codex App Server launch is authorized by this contract.

## 15. Exact next prompt — Sonnet/Claude

> **M0B-R8.1-C2 — second focused adversarial review**
>
> Read the canonical CHAT-ARCH README, CURRENT-STATE, CONTEXT-INDEX and MEMORY-OPERATING-PROTOCOL route, then read Entry 274 in full. Entries 272 and 273 are historical source documents; Entry 274 is the proposed consolidated contract.
>
> Review Entry 274 against the previously reported F-01–F-12. Do not repeat or broaden the old research. Try to falsify the proposed closures with concrete counterexamples, especially:
>
> 1. whether a requester can alter approval policy, forge/replay UI evidence, redeem a decision from another session, or bypass issuer/ledger custody;
> 2. whether scope-local checkout/path identity can be proven without reading unapproved paths or spawning Git, and whether the same opened filesystem object is kept contained despite root/path substitution;
> 3. whether every applicable governance block is accounted for, whether multi-block combination is unambiguous, and whether a missing block-release mechanism still denies;
> 4. whether budget reservations, intent/completion receipts, crashes, restart, revocation outage and expiry can ever result in content being delivered without a durable completion;
> 5. whether path canonicalization, link/reparse, hard-link, ADS, Unicode alias, list cap and byte cap rules conflict or leave a concrete disclosure path;
> 6. whether the test matrix discriminates the counterexamples and honestly distinguishes simulated tests from OS-level guarantees.
>
> For each defect, cite the exact Entry 274 section, severity, condition, consequence, minimum text repair and a discriminating test. Classify code/runtime statements as `UNPROVEN` unless you actually verify source code; do not infer them from the contract. Do not access local M0A, inspect secrets, invoke the blocked reader, execute tests/builds, modify code or launch IABV/Codex/App Server.
>
> Return exactly one verdict: `PASS`, `PASS_WITH_REPAIRS`, or `FAIL`. This is contract review only and does not authorize implementation or local access. Keep `KEEP_BLOCKED`.
