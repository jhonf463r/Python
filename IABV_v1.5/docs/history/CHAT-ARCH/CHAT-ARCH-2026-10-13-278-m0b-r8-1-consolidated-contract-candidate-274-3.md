# CHAT-ARCH-2026-10-13-278 — M0B-R8.1 consolidated contract candidate (post-C4 / amendment 274.3)

- Episode: CHAT-ARCH-2026-10-13-278
- Date: 2026-10-13 (America/Bogota)
- Status: `M0B_R8_1_CONSOLIDATED_CANDIDATE_274_3_PENDING_TARGETED_DELTA_REVIEW`
- Operational posture: `KEEP_BLOCKED`
- This is the single-file full-text consolidation candidate requested after C4. It is a design document; it is not accepted as a baseline, an implementation specification validated on the target OS, or authorization to unlock M0A.

## 0. How to read this consolidated candidate

This document embeds the operative base clauses from Entry 274, the clean historical C2 amendment text from Entry 275, the C3 clauses from Entry 276, and the C4 repair set from Entry 277. Source labels are preserved to maintain provenance. No external file is required to read the contract clauses included here.

Normative precedence for overlapping topics is: **(1) Entry 277 R1–R9; (2) Entry 276 C3 clauses/grammar; (3) clean historical Entry 275 C2 clauses; (4) Entry 274 base clauses.** Clauses are cumulative where compatible. A later, narrower clause supersedes a conflict; it does not silently waive unrelated restrictions. The one active conformance manifest is Section 6 below. Historical Entry 274 A1–A22 is not an active test matrix and must not be merged with the Entry 275 tests.

**Source integrity:** Entry 274 blob `5943a87d907436fc7ecac31534cbfcd31fe7de55`; clean Entry 275 blob `0945248916fa4f83cc0e7d9d354e39fe3720bb5a` at immutable commit `1e644ee663118b6567018cd2211c107e48489d4c`; Entry 276 blob `023272e14ec5c6ef26b904c47c3fed66eb93c532`; Entry 277 blob `b9e4071e0b8cbeb3354ec7218d46864419402a7b`. The current Entry 275 path in the repository is a supersession/provenance notice, not the clean contract body. The corrupt historical blob is never normative.

## 1. Authority boundaries retained from Entry 274

The five-authority model remains mandatory: diagnostic, fresh Owner approval evidence, server-side read decision, per-operation reader verifier, and durable operation ledger/receipt are separate authorities. No approval boolean, diagnostic result or receipt grants repository-read authority. The complete base rules for all five authorities and the rest of the unmodified R8.1 contract are embedded in Section 2; Sections 3–5 contain the later C2, C3 and C4 clauses.

## 2. Base contract clauses from Entry 274 (apply unless superseded below)

### [Entry 274 §2 (base clause)] Five separate authorities

The system MUST keep these separate:

1. **Diagnostic:** returns only the minimal metadata needed to explain an applicable block. It reads no repository file and grants no permission.
2. **Fresh approval evidence:** records the scope an authenticated Owner explicitly approved through a trusted interactive UI.
3. **Read decision:** a trusted issuer creates a distinct server-side decision after verifying the approval evidence, target, scope and policy.
4. **Reader verifier:** the actual file/list reader independently checks authority and constraints immediately before each operation.
5. **Operation ledger/receipt:** a durable, tamper-evident record of intent and outcome. A receipt is evidence, never authority.

No stage may be collapsed into an `approved` boolean. Diagnostic output, approval results, `approved_by`, `VALIDATED`, ApprovalMemory results, Devin action authorization and observation permissions are not repository-read authority.

---

### [Entry 274 §3 (base clause)] Normative v1 approval policy (closes F-01 and F-02)

For `read_file` and `list_directory`, **fresh interactive Owner approval is mandatory and unconditional in v1**. An agent-configurable, project-configurable, memory-derived or caller-supplied policy cannot relax it. Automatic approvals, stored preapprovals, `auto_resolved=true`, absent UI events, missing principals and generic positive results MUST be rejected before issuance. No exception path is defined in v1. Any future exception requires a separately reviewed contract revision and Owner decision through a channel not controlled by the requesting agent; it cannot be activated by changing an ordinary policy value.

The trusted issuer, not the requester, creates the request ID, challenge nonce, `interactive_event_id`, canonical target evidence and scope digest. The nonce is visible only to the trusted approval UI/authority and MUST NOT be returned to, supplied by, or readable by the requesting agent. The UI returns its attestation directly to the issuer. The issuer re-derives diagnostic/block identifiers from authoritative server-side state; it MUST NOT accept a requester-echoed identifier as proof.

The approval UI MUST show the complete scope before confirmation: exact target/workspace/checkout, operation, exact path/listing entries or permitted directory target, byte and call budgets, expiry, purpose, and intended downstream recipient (including an external AI/provider if content will be sent there). It MUST show raw and normalized path forms, visibly escape control/non-printable and bidirectional characters, and refuse approval if any part is truncated, ambiguous or cannot be rendered safely. The digest is calculated by the issuer over the exact canonical scope displayed. The request path MUST enforce rate limits and deduplicate retries. Approval from an event the requesting agent can synthesize, intercept, replay or forge MUST fail verification.

---

### [Entry 274 §4 (base clause)] Mandatory target, checkout and scope identity (closes F-06 and F-09)

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

---

### [Entry 274 §5 (base clause)] Approval receipt and server-side decision custody (closes F-03)

A valid approval receipt MUST bind a one-time challenge, the verified Owner principal and provenance, the direct interactive UI event, the exact scope digest, decision, timestamps and intended reader/audience. `approved_by` text alone is never identity evidence. Receipt verification MUST reject nonce/event replay, mismatched scope, expired challenges, unverified principals and attestations from an unintended UI/issuer.

In v1 the read decision MUST be an authoritative **server-side ledger record**, not a transferable bearer object. The issuer atomically records the decision and its finite budgets in the ledger and returns only a non-authoritative reference/ID to the intended requesting server session. The decision MUST be bound to the authenticated requesting connection/session and intended reader/target; another session cannot redeem it. Session identity comes from trusted server context, not from a caller-selected string.

An unknown `decision_id`, absent record, ledger inconsistency, ledger loss, failed atomic write or unavailable ledger MUST deny. After restart, the reader must recover authoritative budgets and unresolved intents before serving reads. If this cannot be done, it MUST remain unavailable for reads; it MUST NOT recreate budgets from the caller, a signed copied object or in-memory defaults. A self-contained signed bearer-token alternative is OUT OF SCOPE for v1.

---

### [Entry 274 §6 (base clause)] Read decision fields, timing and revocation (closes F-10 and part of F-11)

The server-side decision MUST record schema version, unique decision ID, authenticated Owner principal reference, approval receipt reference, request/session ID, issuer, intended reader, target/checkout binding, operation class, canonical explicit path allowlist, displayed purpose/recipient, finite atomic budgets, issue/approval timestamps, expiry, approval-policy version, status, and the separately verified governance-release attestation reference if one is ever supported.

Proposed conservative v1 timing defaults (design proposals, not existing code facts):
- approval challenge nonce TTL: at most 120 seconds;
- interactive approval-to-issuance interval: at most 60 seconds;
- decision lifetime: at most five minutes from trusted server issuance.

The issuer and reader MUST use a trusted server clock for recorded wall-clock evidence and a monotonic clock for in-process expiry/elapsed-time checks. The verifier checks freshness at issuance, when reserving each operation intent, and again before releasing staged content. Expiry or revocation during an operation means staged content is discarded and not delivered. The authoritative revocation source is mandatory; if it cannot be queried or its response is inconsistent, deny and do not release content. Revocation must be possible through an authenticated Owner/governance path outside the requesting agent's control. Renewal requires a new fresh approval and new issuance.

The field `purpose` explains user intent and is included in what the UI shows and in the scope digest; it does not independently grant authority.

---

### [Entry 274 §7 (base clause)] Separate governance-block release (closes F-04 and F-08)

**In v1, a repository-read decision cannot release a governance block.** The read issuer and reader MUST NOT have implicit authority to create or infer a block release. If any active block applies and no independently supported release attestation exists, return terminal `BLOCK_RELEASE_UNSUPPORTED` and deny. This is the required behavior for the currently unproven release mechanism; it is not a temporary permission to bypass the block.

A future release, if separately designed and authorized, MUST be a distinct artifact issued by the trusted authority that owns the relevant governance block. It must bind at least the block ID, block revision or content digest, target identity, exact operation/scope, authority/principal, issue time and expiry. The reader verifies that artifact independently. Reusing a block ID after its semantics/content change does not preserve an older release.

The applicability evaluator MUST use the authoritative, versioned set of supported scope dimensions. The server derives assistant and target identity. It MUST define combination semantics explicitly:

- every active block that applies to the request MUST be accounted for;
- an applicable block without a valid independent release causes denial;
- unknown/malformed/unsupported scope, incomplete target identity, partially evaluable/conflicting block metadata or unavailable authoritative scope semantics fail closed as `BLOCK_SCOPE_UNEVALUABLE` (or a more specific stable denial code);
- a block can be declared non-applicable only when trusted target identity is established and the authoritative scope model proves the mismatch;
- where multiple blocks apply, all must be independently released; one release cannot cover another block unless its artifact explicitly and validly names it.

The known `assistant_kind` versus `target_scope` discrepancy from Entry 269 is an independent hazard. It is not a demonstrated cause of the M0A denial. Before any implementation planning, the authoritative scope model and combination semantics are a prerequisite; do not invent production scope dimensions from the test matrix.

---

### [Entry 274 §8 (base clause)] Race-resistant reader/path enforcement (consolidates 272 §4.2/§4.4 and 273 §3; closes F-07)

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

---

### [Entry 274 §9 (base clause)] Budgets and mandatory durable audit ledger (closes F-05 and F-11)

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

---

### [Entry 274 §10 (base clause)] Scope and hard limits (resolves remaining F-11 ambiguities)

V1 supports only `read_file` and non-recursive `list_directory`, over exact relative file paths or exact directory paths explicitly displayed and approved. **Directory-prefix grants and wildcard grants are excluded from v1.** A separately named directory-list operation does not grant access to children.

Initial hard ceilings remain:
- maximum bytes read from one file: 1 MiB;
- maximum entries disclosed from one listing: 200.

A request above a hard ceiling is denied as a whole; no partial content/listing is disclosed. Decisions may lower the ceilings but cannot raise them in v1. All finite aggregate budgets (bytes, read calls, list calls, entries) are reserved atomically before operations. On success, account actual bytes and entries. After internal content has been read, never refund the reservation merely because the completion record failed.

No command execution, recursive scan, write/edit, build, test, process launch, credential access or network operation is authorized by this read decision.

---

## 3. C2 clauses from clean historical Entry 275 (supersede conflicting base clauses)

### [clean historical Entry 275 §2 (C2 amendment)] Threat model and non-negotiable approval provenance — C2-01, C2-11

#### 2.1 Threat model

The requester/agent is untrusted. Assume it can submit arbitrary prompts, paths and metadata; retry requests; create or replace files and directories in the worktree; create symlinks/junctions/reparse points when OS permissions allow; run code under the agent's permitted OS principal; attempt same-user UI automation; and exploit shared or multiplexed connections. Do not assume the agent will obey UI conventions or protect any nonce, decision ID, policy setting, ledger path, or returned diagnostic.

The trusted approval authority, trusted UI/authenticator, issuing service, reader verifier and authoritative ledger must be separated from requester-controlled code by an enforceable integrity boundary. A different process running under the same OS user is not, by itself, proof of that separation.

#### 2.2 Meaning of fresh interactive approval

For v1 `read_file` and `list_directory`, recent Owner approval through an independent, authenticated user-verification channel is mandatory and cannot be weakened by agent/project configuration, stored policy, ApprovalMemory, prompt text, tool output, or a caller-supplied policy version.

The approval event MUST attest to the Owner's deliberate confirmation of the exact challenge nonce and the canonical scope digest. The trusted UI/authenticator MUST provide an independently verifiable user-presence/user-verification attestation, bound to the challenge and scope. Merely observing a click, key event, UI automation event, foreground window or generic positive ApprovalResult is insufficient.

If the requester can synthesize the event, read the nonce, control the trusted UI's input path, alter the displayed scope, impersonate the Owner, or if the platform cannot establish the stated isolation, issuance MUST fail closed with `APPROVAL_CHANNEL_UNTRUSTED`. Do not invent a claim that same-user desktop automation can always be prevented: the implementation must demonstrate an enforcement boundary suited to this threat model. If no such boundary is available, v1 cannot issue a read decision.

The nonce is generated by the issuer and visible only to the trusted approval surface/authority; it MUST never be returned to the requesting agent. The approval surface returns its attestation directly to the issuer. Event IDs, request IDs, block IDs, target identities and the displayed-scope digest are derived or verified by trusted components, never accepted from echoed requester fields as proof.

The approval UI MUST display the entire target, exact operations and paths, limits, expiration, purpose label and server-derived recipient before confirmation. It MUST show both the raw requested path and its canonical accepted form; escape non-printable, control and bidirectional characters; and refuse approval if content is truncated, ambiguous or cannot be safely rendered. It must disclose whether the staged repository content will be sent to an external AI/provider and identify the recipient from server configuration. Rate limiting and request deduplication are mandatory.

#### 2.3 Untrusted purpose and recipient identity

Requester-supplied `purpose` is untrusted explanatory text, not a statement of fact. In the UI it MUST be labeled “solicitante — no verificado”, be length- and character-bounded, and be visually separated from server-verified target, scope and recipient facts. It MUST NOT determine recipient identity or authorization.

The intended downstream recipient is derived by the server from the authenticated request/session and configured destination/provider. A caller-supplied recipient label is never proof. V1 MUST either bind decisions to a unique authenticated agent identity in addition to the session/connection, or reject multiplexed/shared connections that cannot distinguish which agent is redeeming the decision.

The v1 policy identifier is fixed by this contract (for example, `M0B-R8.1-v1-owner-human-required`) and is not caller-editable. No relaxed policy/exception path exists in v1.

---

### [clean historical Entry 275 §3 (C2 amendment)] Server-side ledger, nonce atomicity, replay and recovery — C2-04, C2-05

#### 3.1 Authoritative state only

V1 uses a server-side authoritative ledger, not a transferable bearer grant. The decision is bound to the authenticated Owner principal reference, trusted approval event, unique requester agent/session, intended reader, exact target, scope digest and budgets. An unknown decision ID, absent record, wrong session/agent, unavailable ledger, conflicting record, invalid integrity chain or missing anti-rollback evidence means deny before content access.

The issuer MUST atomically consume the one-time approval nonce/event and create the decision/budget record in the same ledger transaction. The nonce/event is permanently recorded as consumed, including when a reply to the requester is lost. Retrying the same issuance request MUST return the same result/decision reference when the original transaction committed; it MUST NOT create a second decision or reset budgets. If commit status cannot be established, fail closed and reconcile rather than guess.

Operation IDs are generated by the trusted server, not the requester. Each operation ID is bound to one decision and one operation request; repeat submissions are idempotent and cannot cause another content delivery or double-refund. Reusing an ID with different parameters is a denial and audit event.

#### 3.2 Ledger integrity and durability

The ledger MUST be append-only **and** tamper-evident, integrity-chained, and protected against rollback to a previous valid-looking state. Recovery verifies an independent monotonic/anti-rollback anchor that the requesting agent cannot write, delete or roll back together with the ledger. If the platform cannot supply a credible independent anchor, integrity boundary or authoritative storage, reads remain disabled. A copy or snapshot restore that does not match the anchor MUST be detected and fail closed.

“Durable commit” is a normative platform requirement: an acknowledged intent/completion/release-state commit must use a documented storage/flush protocol whose claimed crash/power-loss properties are separately established for the target platform and storage profile. The ledger MUST reside on a supported, locally mounted durable storage profile controlled by the trusted authority—not a requester-writable directory or an unverified network/sync folder. The contract alone does not prove these storage guarantees.

After any process restart, all previously ACTIVE decisions expire. The service does not resume their remaining lifetime from in-memory monotonic-clock values or reconstruct budgets from callers. It recovers the ledger solely for reconciliation/audit and requires a new approval/issuance for further reads. Previously consumed nonces stay consumed. Any unresolved intent or incomplete release sequence blocks new reads until an authenticated Owner/governance reconciliation is durably recorded.

#### 3.3 Clock and freshness

The issuer records approval and issue times using trusted server time; in-process elapsed time also uses a monotonic clock. V1 defaults are proposals, not existing code facts:
- approval challenge nonce lifetime: at most 120 seconds;
- approval-to-issuance interval: at most 60 seconds;
- issued decision lifetime: at most five minutes.

Expiry is checked when issuing, reserving every operation, and at the final release gate. A backward wall-clock adjustment MUST NOT revive a decision; a restart expires all active decisions regardless of displayed expiry. If reliable time/expiry cannot be established, deny. The nonce's consumed state is durable and transactionally linked to issuance.

---

### [clean historical Entry 275 §4 (C2 amendment)] Target identity, scope-local object binding and no pre-approval oracle — C2-02, C2-06, C2-07, C2-08

#### 4.1 Trusted registration and block lineage

Checkout/workspace registrations and lifecycle IDs MUST be created, replaced and retired only by a trusted server/authority outside requester control. The registry retains durable lineage/tombstones so deleting/recreating a directory or obtaining a new registration ID cannot erase the relation to an existing resource/workspace/checkout-scoped block.

A new lifecycle ID or a changed path does not, by itself, prove that an existing block is non-applicable. The evaluator MUST use the authoritative block's declared scope dimensions and the trusted target-identity/registration lineage. It may conclude “non-applicable” only when every scope dimension actually referenced by that block has been evaluated against trustworthy current and historical identity evidence and the authoritative, versioned scope model proves the mismatch. If a relevant identifier overlaps, lineage is missing/ambiguous, registration provenance is requester-controlled, or any referenced dimension cannot be evaluated, the block remains applicable for denial. Do not require every unrelated identity field to differ; instead require complete evidence for the fields the authoritative block actually scopes.

The intent record MUST capture every block evaluated: block ID, revision/content digest, declared scope, result (applicable/non-applicable/unevaluable), scope-model version and release-attestation reference when valid. A missing block-evaluation record is a denial. These audit fields do not grant release authority.

#### 4.2 Minimal identity; no whole-tree fingerprint

The server establishes identity from trusted execution context and a controlled registration, including server instance/reader, workspace registration, root volume/device and stable file-object identity, worktree-specific control-directory identity as supported, checkout lifecycle ID, and trusted ref/HEAD metadata where applicable. A repository ID or canonical root path alone is insufficient. Required identity cannot be downgraded to a path string. If a required component or lineage is missing, unstable or contradictory, deny.

Identity acquisition MUST NOT recursively read the worktree, read sensitive/unapproved file contents, traverse arbitrary links, invoke Git/shell subprocesses, run repository hooks, or enumerate unapproved paths to calculate a global dirty-tree fingerprint. V1 binds root/worktree identity and each exact approved path object, not the whole tree's contents. Changes to an approved object or trusted target/root/ref binding invalidate the decision; the implementation does not inspect unrelated files to discover changes outside the approved scope.

#### 4.3 Safe pre-approval path preview

The target and every path object MUST be bound to the scope shown for Owner approval, then compared to the same identity at use time. A nonexistent path is not approvable in v1. Before any OS path lookup, the resolver rejects absolute, UNC/network, device, alternate-data-stream, traversal, wildcard, unsupported Unicode/control/bidirectional and other out-of-grammar forms. The pre-approval resolver follows the same pinned-root, handle-relative, least-access and no-reparse rules as the reader. It may obtain only the minimum metadata needed to identify the already existing target object; it MUST NOT read content or follow a link to discover a destination. If safe metadata-only identity cannot be obtained before approval, do not present that path as approvable.

For failures at or after the first untrusted path component, diagnostics shown to the requester MUST use a uniform non-oracular denial category (for example, `PATH_SCOPE_UNAVAILABLE`) rather than revealing whether an external target exists, its size, type or content. Detailed reason evidence may be retained in the protected audit record if policy permits; it is not returned as an existence oracle to the requester.

Object identity is not a claim of immutable content. The contract authorizes a bounded read of the current content of the exact approved object at operation time; the UI must not imply approval of an unseen content hash. To prevent in-place concurrent change during staging, the reader must acquire platform-supported access/share/locking semantics that deny conflicting write/delete access while the handle is held, and compare supported object/change metadata before and after the read. If that protection cannot be acquired, if content changes, or if the target platform cannot supply adequate object binding, discard staged content and deny. A later adversarial implementation review must establish actual platform behavior; this text does not prove it.

#### 4.4 Closed v1 path grammar and object authorization

V1 accepts only relative path components in a documented conservative character grammar (ASCII letters/digits plus explicitly permitted simple punctuation; no colon, wildcard, slash tricks, traversal, trailing dot/space, reserved device names, short-name alias patterns, control characters, bidirectional controls or non-normalized Unicode). Unsupported forms return `PATH_FORM_UNSUPPORTED`. Any expansion of the grammar requires a separately reviewed change.

Authorization is the conjunction of (1) a canonical path admitted by that grammar, (2) exact path/object identity bound during approval, (3) containment beneath the pinned root handle, and (4) the existing sensitive-file and workspace-containment policy applied to the actual resolved object. An exact allowlist never weakens an existing reader denial. V1 rejects hard-linked objects when link count is not exactly one or cannot be queried reliably; it rejects non-local/unsupported filesystems when stable object identity/containment guarantees cannot be established. Do not use a vague “canonical policy can prove it” exception.

---

### [clean historical Entry 275 §5 (C2 amendment)] Separate governance-block authority and deterministic combination — C2-02

A read decision MUST NOT clear or release an applicable governance block. In v1, absence of an independently supported governance-owned release is a terminal `BLOCK_RELEASE_UNSUPPORTED`, and the reader denies. The read issuer cannot emit a release artifact on behalf of the authority that owns a block.

A future release, if separately designed and authorized, MUST be issued by that trusted block-owning authority and bind at least the block ID, immutable revision/content digest, target identity, exact operation/scope, issuer/principal, issuance time and expiry. The reader verifies it independently. An old release cannot apply to a changed block revision merely because the ID was reused.

The authoritative, versioned scope model and supported dimensions are implementation prerequisites, not invented by this amendment. For a request, the server enumerates all relevant active blocks and evaluates every one:
- any applicable block lacking a valid independent release => deny with `BLOCK_RELEASE_UNSUPPORTED`;
- unknown/malformed/unsupported scope, incomplete identity/lineage, conflicting evidence or unavailable scope semantics => deny with `BLOCK_SCOPE_UNEVALUABLE`;
- a block is non-applicable only with complete trusted evidence under the authoritative model;
- all applicable blocks require their own valid release; one release cannot clear another block unless its authority artifact explicitly and validly covers it.

The `assistant_kind` versus `target_scope` discrepancy recorded in Entry 269 remains an independent risk and is not proven to have caused the reported M0A refusal. Conformance must test both over-blocking and under-blocking directions. Until the authoritative scope model and supported release mechanism exist and are verified, no read decision can overcome the current block.

---

### [clean historical Entry 275 §6 (C2 amendment)] Reader containment and existing denial policy — C2-03, C2-07, C2-08, C2-09

Entry 274's §8 rules are tightened as follows:

- Existing sensitive-file denial, workspace-root containment and all current reader restrictions remain mandatory. A new decision may narrow the effective permissions only; it MUST NOT weaken, override or replace an existing reader denial. An allowlisted sensitive file MUST still be denied.
- The approved root is pinned once using a handle and stable root identity. Each operation is relative to that pinned root, without a second name-based resolution after verification. The actual opened object/handle is checked for identity, type, containment, allowlist and sensitive-path policy before reading any content. The same verified handle is used for the operation.
- V1 rejects reparse points/symlinks/junctions in path traversal and in listed entries; it does not follow or disclose their targets. A path or root substitution, unsupported handle semantics, unprovable containment, unexpected object identity/type or concurrent mutation causes denial/discard with no content release. If same-object containment cannot be established on the platform, return `CONTAINMENT_UNPROVEN`.
- File reads are bounded by bytes actually read, not only a pre-read size check. The reader may attempt at most cap+1 bytes to identify overflow; any overflow returns `FILE_LIMIT_EXCEEDED` and discloses no partial content.
- Listing is non-recursive. Count raw directory entries before filtering. Enumerate no more than 201 raw entries to distinguish an allowed 200 from overflow. Exactly 200 raw entries may pass only if every entry is valid under the policy; the 201st raw entry causes `LIST_LIMIT_EXCEEDED` and no names are disclosed. Do not omit unsafe entries and then return a misleading partial listing. Any unsupported, sensitive, link/reparse or invalid entry causes the whole listing to fail. Sort a valid in-limit result deterministically. A directory list never authorizes traversal or file reads.
- V1 does not allow directory-prefix or wildcard grants. Only exact existing file objects and exact directory-list targets displayed and approved are in scope.

The fixed v1 ceilings remain 1 MiB per file and 200 raw entries per directory listing. An over-cap request is denied as a whole; no partial contents/listing are returned. A precisely-at-cap positive fixture is required in the conformance suite.

---

### [clean historical Entry 275 §7 (C2 amendment)] Atomic budgets, receipts and actual delivery state — C2-05, C2-06

For every operation, the server generates a unique idempotency/operation ID and durably records the intent and budget reservation before opening or reading repository content. Reservations and cumulative byte/call/entry budgets are atomic across concurrency. A lost response/retry with the same ID cannot re-read or re-deliver content; it retrieves the same terminal/ unresolved state. Different arguments with the same ID are rejected.

The auditable state machine is:

1. `INTENT_COMMITTED`: intent, selected decision, exact target/path binding, applicable block IDs/revisions/scope verdicts, operation ID, maximum reservation and initial status are durable.
2. `CONTENT_STAGED`: the operation ran through the verified handle; the staged result is not yet caller-visible.
3. `RELEASE_AUTHORIZED`: after staging, the reader rechecks target/object identity and content-change protection, policy, all applicable blocks/release attestations, expiry, authoritative revocation and budgets; this decision and the safe result digest/status are durably committed immediately before content handoff.
4. `DELIVERY_ACKNOWLEDGED`, where the transport provides a trustworthy acknowledgement; otherwise delivery status is not claimed beyond the durable release authorization.
5. `DISCARDED`: the operation fails validation or the final gate, or staged output is intentionally withheld; no content is delivered.
6. `UNRESOLVED`: a crash, failed final record or uncertain handoff prevents a reliable terminal outcome. This remains blocking on restart until Owner/governance reconciliation is durably recorded.

A durable `CONTENT_STAGED`/completion record is not equivalent to delivery. The final freshness/revocation/block check occurs as close as supported to handoff as possible. Expiry, revocation, target change or governance change before handoff discards the content. A handoff can race with process failure; v1 MUST NOT claim exactly-once delivery without a transport that proves it. If a crash occurs after `RELEASE_AUTHORIZED` and delivery outcome is uncertain, retain the release intent, charge the reservation, halt further reads and reconcile. Never automatically replay a possibly delivered response.

#### 7.1 Explicit accounting by outcome

- Denial before any content I/O: zero content bytes/entries consumed; attempt/rate-limit counters may still advance.
- Successful operation whose completion and final gate commit: charge actual bytes read and raw entries enumerated, with the operation/list call count.
- Failure after any content I/O, overflow detection, crash or uncertain result: retain the maximum reservation for that operation, never refund it automatically; set the result `DISCARDED` or `UNRESOLVED` as supported by evidence.
- Repeating an operation ID never doubles content delivery. The ledger's single record and accounting are idempotent.
- Completion/release authorization MUST be durable before content can leave the reader. A missing or failed completion commit means no delivery. A failed post-read commit means no delivery, charged reservation, persistent halt/fail-stop and reconciliation.
- A deny path remains denied even if it cannot write its denial receipt. It does not fall back to another reader or disclose protected reason metadata.

A durable ledger commit must be verified to survive the declared failure class. If the implementation only demonstrates process-crash consistency but not host/power-loss or rollback guarantees, the supported failure model must say so, and the stronger v1 contract remains unfulfilled until adequate durable/anti-rollback protection exists.

---

### [clean historical Entry 275 §8 (C2 amendment)] Revocation and restart semantics — C2-04, C2-05, C2-06

The revocation source is mandatory, authoritative and protected from requester writes. Source outage, timeout, inconsistent response or inability to establish current status means deny and no content release. The reader checks revocation and expiry at decision issuance, before reservation, after staging and at the final release gate.

After restart, previous active decisions are expired and cannot be resumed. The consumed nonce and all budget/intent/release records remain in the authoritative ledger. If the ledger's anti-rollback anchor, nonce record, budget state, revocation source or unresolved-operation recovery is unavailable, reads remain disabled. A wall-clock rollback cannot reactivate a grant. Reconciliation of an orphan intent or uncertain delivery requires authenticated Owner/governance action and a durable append-only record; it is never an automatic cleanup.

---

## 4. C3 clauses from Entry 276 (supersede C2/base where stated)

### [Entry 276 §0 (C3 grammar and integrity route)] Effective grammar and Entry 275 integrity status

The current path for Entry 275 is now a short supersession/provenance notice, not a full-text restoration. The clean historical body remains retrievable at commit `1e644ee663118b6567018cd2211c107e48489d4c`, blob `0945248916fa4f83cc0e7d9d354e39fe3720bb5a`. The corrupted blob is retained only in Git history. The effective review inputs are the clean historical Entry 275 body, Entry 274 and this amendment; do not cite the corrupted blob as valid contract text.

**Proposed v1 path grammar (full-string match):** accept only slash-separated relative paths, with no leading slash and no backslash in caller input. Each component MUST match <code>^[A-Za-z0-9][A-Za-z0-9._ -]{0,126}[A-Za-z0-9_-]&#36;</code>, or be one alphanumeric character. Total path length is at most 240 ASCII characters and nesting is at most 16 components. Before any filesystem lookup, reject colon/ADS, wildcards, traversal, trailing dot/space, any `~` short-name pattern, controls, non-ASCII/Unicode (including bidi/confusables), absolute/UNC/device paths and reserved Windows device basenames case-insensitively (`CON`, `PRN`, `AUX`, `NUL`, <code>CONIN&#36;</code>, <code>CONOUT&#36;</code>, <code>CLOCK&#36;</code>, `COM1`–`COM9`, `LPT1`–`LPT9`, including when followed by an extension). Unsupported input returns `PATH_FORM_UNSUPPORTED`. Expanding the grammar requires a separately reviewed contract change.

For directory listings, count actual raw entries, excluding only exact structural pseudo-names `.` and `..` if a platform returns them. The 201st actual entry denies the entire listing. Any invalid, sensitive, reparse/link or unsupported entry denies the whole listing; do not silently omit entries or disclose partial names. Require a stable enumeration view; if concurrent mutation cannot be excluded or detected reliably, discard and deny.

To prevent recurrence of the Entry 275 edit defect, do not use replacement-string interpolation when inserted text contains a dollar sign directly before a Markdown backtick. Use a callback/literal-safe edit and verify the written blob: exactly one header, complete regex and reserved names, and expected section count.

---

### [Entry 276 §2 (C3-02–C3-11 normative amendments; test rows moved to the final manifest)] Consolidated amendment 274.2 — C3-02 through C3-11

The following rules are proposed as one amendment to Entry 274/275. Where they conflict with Entries 274 or 275, these rules take precedence. They are contract requirements, not claims about an implementation.

#### C3-02 — trusted Owner enrollment

The Owner's user-verification credential and verification root must be enrolled outside requester control, in a protected trust store the requesting agent cannot write or replace. A well-formed attestation from an unregistered credential is rejected with `APPROVAL_CHANNEL_UNTRUSTED`. If the supported platform cannot isolate enrollment and user verification from arbitrary same-user requester code, v1 does not issue a read decision.

#### C3-03 — rollback protection for registrations and block state

The anti-rollback boundary covers the checkout/workspace registry and lifecycle lineage, deletion tombstones, active-block set, and version of the authoritative scope model—not only the read-decision ledger. They share a protected monotonic epoch/anchor recorded in each issuance and operation intent and checked before every operation. Rollback, missing lineage or stale block state denies with `REGISTRY_ROLLBACK` or `BLOCK_SCOPE_UNEVALUABLE`. Registration and tombstone mutation must be authority-controlled and outside requester write access.

#### C3-04 — pre-approval oracle prevention

A syntactically valid request receives the same external status, `APPROVAL_PENDING`, independent of whether the path exists or its size. The trusted approval surface resolves the target through the same contained, metadata-only resolver used by the reader. Sensitive-path denials are applied before target lookup. A caller-facing error after an untrusted component must not reveal existence, type or size. Detailed protected audit evidence may be retained server-side. Timing equivalence is a target-platform requirement to validate, not claimed proven.

#### C3-05 and C3-06 — handoff states and idempotency

The audit state machine distinguishes `INTENT_COMMITTED`, `CONTENT_STAGED`, `RELEASE_AUTHORIZED`, `HANDOFF_RETURNED`, `DELIVERED` only where a trustworthy transport acknowledgement exists, `DISCARDED` and `UNRESOLVED`. `HANDOFF_RETURNED` means the local handoff call returned; it does not claim the recipient received the data. On recovery, `RELEASE_AUTHORIZED` without a handoff-returned or discarded state is unresolved and blocks new reads until durable Owner/governance reconciliation. No exactly-once delivery claim is allowed without transport evidence.

The requester may supply a non-authoritative `client_request_token` only as an idempotency lookup key, scoped to authenticated agent + session + canonical scope digest. Reusing it with different scope is denied and audited. The issuer-generated nonce is consumed atomically with decision creation; retry after a lost reply returns the same committed decision/state, never a new budget. The caller token is not authority.

#### C3-07 — server-controlled destination and agent identity

The destination/provider is read from a protected server configuration store, and its identity/digest is included in the approved scope. The UI labels it as the intended recipient and clearly states that downstream copying/retransmission after content is handed to the requester is not controlled by this contract. Decisions bind to an authenticated agent principal/session that cannot be redeemed by another local process merely by copying a bearer token. If the connection multiplexes agents and the reader cannot distinguish them, v1 rejects it.

#### C3-08 — clock and suspension

Expiry uses trusted server time plus a monotonic elapsed-time source whose semantics include system suspend, as proven for the target platform. If the clock jumps, suspend semantics are unknown, or monotonic/wall-clock observations disagree beyond the defined tolerance, all active decisions and pending nonces expire; fail closed. No active decision survives process/host restart.

#### C3-09 — raw listing semantics

Directory entries named exactly `.` and `..`, if the platform emits them, are excluded from the raw-entry count as structural pseudo-entries before applying the 200-entry ceiling. Every actual filesystem entry counts before filtering. The 201st actual entry denies the entire listing; any invalid/sensitive/reparse/unsupported entry among an in-limit listing also denies the whole listing, with no silent omission or partial names.

#### C3-10 — deterministic block verdict precedence

For each request, evaluate all blocks using the authoritative scope model and record each block ID, immutable revision/digest, scope, result and model version. If any required scope/identity evidence is unavailable or inconsistent, return `BLOCK_SCOPE_UNEVALUABLE` (this code dominates a simultaneous applicable-block result). Otherwise, if one or more blocks are applicable and any lacks a valid independent governance-owned release, return `BLOCK_RELEASE_UNSUPPORTED`. A block is non-applicable only when every dimension that block actually references is evaluated from trusted current and historical identity evidence and the model proves a mismatch. A new registration ID alone is insufficient. Every applicable block must have its own valid release.

#### C3-11 — one authoritative conformance suite

The effective suite uses the clean historical Entry 275 matrix (A1–A35) as the sole base matrix; it entirely replaces Entry 274's historical A1–A22 matrix rather than merging those reused IDs. This amendment adds only new IDs A36 onward. The final published manifest MUST contain one globally unique ID per case, a traceability link to the relevant historical requirement, explicit setup and expected result, and a positive/negative/boundary classification. Duplicate IDs, ambiguous outcomes or absence of positive cases fail manifest validation.

Add mandatory discriminating cases: unregistered Owner credential; registry/tombstone rollback; path-existence side channel across existing, missing and sensitive paths; unresolved handoff after crashes at each state boundary; retry after lost issuance response; copied session token; clock jump/suspend; 200 actual entries plus structural pseudo-entries versus 201 actual entries; simultaneous applicable and unevaluable blocks; and explicit regression cases for sensitive-path denial, non-allowlisted file, unapproved listing and diagnostic-only zero-file-read behavior. Preserve positive-path and exact-boundary cases so a deny-all implementation cannot pass.

---

## 5. C4 amendment 274.3 from Entry 277 (highest precedence)

### [Entry 277 R1 (C4 amendment)] R1 — broaden anti-rollback and re-check at final release (high)

The independently protected monotonic epoch/anchor MUST cover, as one coherent authority state:
1. workspace/checkout registration, lifecycle lineage and deletion tombstones;
2. active governance-block set, block revisions and authoritative scope-model version;
3. Owner trust roots, enrolled credentials, rotation/revocation state and authoritative revocation-source state/version;
4. protected destination/provider configuration and binding between destination, authenticated agent and session;
5. every policy/configuration value whose rollback could widen an approval.

Owner credential enrollment, rotation and revocation are authenticated, Owner-verified, durably ledgered events. Each increments the protected epoch and expires all active decisions and pending challenges/nonces. Destination, block-set, scope-model and registration changes that increment the same epoch also invalidate those decisions/nonces. Restoring a data snapshot must not restore the independent anchor.

The issuer and reader MUST compare the epoch in the approval/intent with the current protected epoch at issuance, before every reserved operation, and immediately before the `RELEASE_AUTHORIZED` gate and handoff. Any change means discard staged content, emit no bytes/names, record the stale epoch and safely detected causes, and select the primary denial under R2. If the epoch or its protection cannot be checked, fail closed.

**Tests:** (a) restore a trust-store snapshot containing a credential revoked after that snapshot while the protected anchor remains newer — `REGISTRY_ROLLBACK`; (b) change credential, block or destination epoch after intent commit but before `RELEASE_AUTHORIZED` — `DISCARDED`, no content, no active decision or nonce preserved.

---

### [Entry 277 R2 (C4 amendment)] R2 — deterministic denial-code precedence (medium)

Every fixed fixture MUST select exactly one primary denial code or lifecycle status. The protected audit may record every safely detected condition in a fixed order, but requester-visible results must not create an object-existence oracle. A manifest containing “X or Y”, duplicate IDs, or an unassigned error code is invalid.

The following total order applies when multiple conditions are present. Check gates in the listed order and select the first failing gate's primary code; do not perform a lookup prohibited by an earlier gate:

1. Authoritative ledger cannot be read — `LEDGER_UNAVAILABLE`.
2. Ledger integrity chain, independent anti-rollback anchor or durable-state authenticity cannot be verified — `LEDGER_INTEGRITY_UNPROVEN`.
3. An unreconciled prior intent/handoff makes the reader unavailable — lifecycle status `UNRESOLVED`; this gate takes precedence over all later checks.
4. A covered registry/trust/destination epoch or lifecycle lineage is stale, rolled back or inconsistent with the independent anchor — `REGISTRY_ROLLBACK`.
5. Owner credential, requester principal/session, approval UI/attestation or agent binding is untrusted — `APPROVAL_CHANNEL_UNTRUSTED`.
6. Caller path syntax/grammar is unsupported, checked before filesystem lookup — `PATH_FORM_UNSUPPORTED`.
7. Target scope cannot be safely resolved in the permitted phase, or a sensitive-name rule rejects before lookup — `PATH_SCOPE_UNAVAILABLE`. The requester sees only R3's uniform pre-approval state until the permitted disclosure phase.
8. The reader cannot prove actual-object identity/containment — `CONTAINMENT_UNPROVEN`.
9. Block scope/identity evidence is absent, stale or contradictory — `BLOCK_SCOPE_UNEVALUABLE`.
10. One or more blocks apply and any lacks independent governance-owned release — `BLOCK_RELEASE_UNSUPPORTED`.
11. Decision expiry, backward-clock step, unknown suspend semantics or clock disagreement invalidates freshness — `DECISION_EXPIRED`.
12. An authoritative current revocation check proves the decision revoked — `DECISION_REVOKED`.
13. The revocation source is unavailable, stale, unauthenticated or unable to prove freshness — `REVOCATION_UNAVAILABLE`.
14. The operation's pre-reserved aggregate budget is insufficient — `BUDGET_EXCEEDED`.
15. A verified file read exceeds its hard byte ceiling — `FILE_LIMIT_EXCEEDED`.
16. A directory has more than 200 actual entries — `LIST_LIMIT_EXCEEDED`.

These are proposed stable result-code names, not claims that any implementation already emits them. The final consolidated contract and conformance manifest MUST use these names consistently; it MUST map every named denial in Entries 274–277 to exactly one row in this order. A new/unmapped code invalidates the artifact. `DISCARDED` is an operation outcome, not a competing denial code; for example, a final epoch mismatch selects `REGISTRY_ROLLBACK` and the durable operation state is `DISCARDED`. `APPROVAL_PENDING` is a pre-approval public state, not a denial code.

The ordering preserves the C3-10 rule: after earlier gates pass, `BLOCK_SCOPE_UNEVALUABLE` dominates a simultaneously applicable-but-unreleased block; otherwise the result is `BLOCK_RELEASE_UNSUPPORTED`. A stale registry/trust/destination epoch is detected before block combination and yields `REGISTRY_ROLLBACK`. For a list operation, establish the target scope and containment first, then count actual entries; if the 201st actual entry is found, `LIST_LIMIT_EXCEEDED` is selected before per-entry validity checks. If there are at most 200, any invalid/sensitive/link/reparse/unsupported actual entry fails the complete list and is mapped by the above containment/path stages. Thus one fixture still has one result.

Retire the ambiguous active alias `A29` and replace it with `277-A29a` and `277-A29b`. Retire `276-A47` as an ambiguous “X or Y” fixture and replace it with `277-A47a` and `277-A47b`. Each replacement has one fixed setup and one expected result.

---

### [Entry 277 R3 (C4 amendment)] R3 — close pre-approval existence and block oracles (medium)

Before Owner confirmation, requester-visible state, response shape and timing envelope for a syntactically valid, non-sensitive-by-name request MUST be indistinguishable across existing, missing and differently sized targets. Keep the state `APPROVAL_PENDING` for the same approval window; do not return a requester-visible path result early. Detailed information may be available in the protected Owner UI/audit. The Owner's decision remains a possible side channel; timing equivalence and the information inferred from Owner choices remain `UNPROVEN` until tested.

Names denied as sensitive MUST be rejected before target lookup. Existing and nonexistent sensitive-name cases must have the same requester-visible status/shape and perform no lookup. Object-dependent `BLOCK_*` codes and detailed path/scope errors MUST NOT be exposed to the requester before the approval window closes. `PATH_SCOPE_UNAVAILABLE` may be returned in the post-approval decision/result channel only; Owner/audit detail is separate.

**Test:** expand Entry 276 `A37` to compare full externally observable state sequences, response shape and timing envelope for (1) normal existing, (2) normal missing, (3) sensitive existing and (4) sensitive missing targets. Require equivalence within each pair, prove sensitive-name denial precedes lookup, and prohibit object-dependent `BLOCK_*` results before approval. Owner-choice leakage remains `UNPROVEN`.

---

### [Entry 277 R4 (C4 amendment)] R4 — idempotency key excludes the scope digest (medium)

The uniqueness key is exactly `(authenticated principal, session, client_request_token)`. The canonical scope digest is an immutable attribute of that key, not part of the key itself. Reuse with a different digest is denied and audited; it cannot create a parallel decision, fresh nonce or new budget. The caller token is only an idempotency hint and never authority.

A retry returns the current persisted status, not the original issuance-time response. After process/host restart, a formerly active decision is `EXPIRED` under clean Entry 275 `3.2`. Retrying the original key returns `EXPIRED` and cannot reactivate the decision, create a nonce, restore/reset budget or issue a new decision.

**Tests:** extend `A42` through restart: same principal/session/token/digest returns `EXPIRED` with no new nonce, decision or budget. Extend `A43`: same key with a different digest denies, audits the mismatch and cannot create a second ledger key.

---

### [Entry 277 R5 (C4 amendment)] R5 — consistent definition of actual directory entries (medium)

Across Entries 274, clean 275, 276 and the final consolidation, “raw entry”, “enumerated entry” and “entry consumed” mean an actual directory entry. Exact structural pseudo-names `.` and `..`, if emitted by the platform, are excluded from the listing ceiling, enumeration-count limit and entry budget.

Enumerate actual entries until the 201st actual entry is observed, then deny the entire listing with `LIST_LIMIT_EXCEEDED` and disclose no names. Exactly 200 valid actual entries may pass if every other gate passes. Any invalid, sensitive, link/reparse or unsupported actual entry in an in-limit listing denies the whole list; never filter an unsafe actual entry and return a partial list. Unsupported counting or unstable enumeration fails closed.

**Tests:** (a) `.`, `..` plus 199 valid actual entries: permit if all gates pass, charge 199; (b) 200 actual entries plus pseudo-names: the boundary may pass; (c) 201 actual entries plus pseudo-names: deny whole list and disclose no names. Reconcile 274 `8`, clean 275 `6`/`7.1` and 276 `C3-09`/`A40` to this definition.

---

### [Entry 277 R6 (C4 amendment)] R6 — path grammar, reserved basenames and positive boundaries (medium)

#### 7.1 Full-component match

Do not use a dollar end-of-line anchor to simulate full-string validation. Validate each component with a genuine full-match operation (for example, the engine's fullmatch API) on ASCII input, then apply length, depth, reserved-name, sensitivity, allowlist, pinned-root containment and object-identity checks. The component language is either one ASCII alphanumeric character, or an ASCII alphanumeric first character, zero to 126 interior characters from letters/digits/dot/underscore/hyphen/ordinary space, and a final character from letters/digits/underscore/hyphen. Maximum component length is 128. A newline or other unconsumed suffix must not pass.

Caller input is slash-separated relative components only: no leading slash, backslash or empty component. Total path length is at most 240 ASCII characters including separators; depth is at most 16 components. Reject colon/ADS, wildcards, traversal, trailing dot/space, tilde short-name patterns, controls, non-ASCII/Unicode (including bidi/confusables), absolute/UNC/device forms and any unsupported syntax with `PATH_FORM_UNSUPPORTED` before lookup. Expansion requires a separately reviewed contract change.

#### 7.2 Reserved names

For the reserved-name check only, compare case-insensitively the component text before its first period after stripping trailing ASCII spaces from that comparison substring. Do not rewrite/normalize the path before actual filesystem lookup. Conservatively reject `CON`, `PRN`, `AUX`, `NUL`, `COM0`–`COM9` and `LPT0`–`LPT9`, along with the special names CONIN$, CONOUT$ and CLOCK$. Dollar-sign forms are already rejected by the grammar; mentioning them is defense-in-depth, not accepted syntax. Thus `con.txt`, `CON .txt` and `NUL  .x` are rejected. Do not over-reject `CONSOLE`, `COM10`, `LPT10` or `NULL` under the reserved-name rule alone; other controls still apply.

#### 7.3 Platform path ceiling and v1 utility limitation

A relative path within 240 characters does not prove that root-plus-relative path semantics are supported by the target OS/filesystem primitives. If the full target exceeds the platform's proven support, deny with uniform `PATH_SCOPE_UNAVAILABLE`. Do not assume a long-path prefix or change OS configuration. Such a mode requires separate contract review and platform evidence.

Dot-prefixed components such as `.git` and `.env` are outside this deliberately restrictive v1 grammar. Under whole-listing rules, any such actual invalid entry causes the directory listing to fail closed rather than be omitted. This reduces utility but does not permit silent filtering; positive listing fixtures must not assume a repository root containing these entries can be listed.

#### 7.4 Required discriminating tests

The final suite MUST include both positive and negative cases; deny-all fails. Test: one-character alphanumeric (allow); valid 128-character component (allow); 129-character component (reject); path exactly 240 ASCII characters (allow if otherwise valid); 241 characters (reject); 16 components (allow if total length is valid); 17 (reject); interior space (allow); final hyphen and underscore (allow); trailing dot/space (reject); reserved examples and near-misses above; newline-suffix rejection by fullmatch. Every fixture needs one expected result.

---

### [Entry 277 R7 (C4 amendment)] R7 — process/session binding, crash recovery and clock regressions (medium)

If the platform cannot bind an approval/session to a unique authenticated agent/process strongly enough to prevent a different local process/agent from redeeming a copied token, v1 issues no decision. A copied bearer-like value never proves identity.

`DELIVERY_ACKNOWLEDGED` in clean Entry 275 and `DELIVERED` in Entry 276 are not synonyms. Use `DELIVERED` only when the contract-defined trusted transport acknowledgement proves delivery; use `HANDOFF_RETURNED` when the local handoff API returns without trusted acknowledgement. A crash or missing durable terminal record is `UNRESOLVED`, blocks new reads and requires durable Owner/governance reconciliation. Never automatically replay a possibly delivered response or claim exactly-once without transport proof.

- `277-A48` — Copy a valid session/token value to a different local process or agent principal. Expected: reject before content access; if process/agent distinction cannot be proven, issue no decision.
- `277-A49` — Two crash fixtures: (a) after `RELEASE_AUTHORIZED` and before `HANDOFF_RETURNED`; (b) after `HANDOFF_RETURNED` and before durable final state/ack. Expected: `UNRESOLVED`, reads halted pending reconciliation, reservation retained, no automatic replay and no `DELIVERED` without trusted acknowledgement.
- `277-A50` — Move wall clock backwards after issuance. Expected: all active decisions and pending nonces expire, fail closed and never revive. A tolerance does not forgive a detected backward step.

---

### [Entry 277 R8 (C4 amendment)] R8 — unique test IDs and matrix ownership (low)

The clean historical Entry 275 matrix A1–A35 is the sole active base and wholly replaces Entry 274's historical A1–A22. Do not merge them by bare number. Qualify retired cases as `274-A1` through `274-A22`, the active base as `275-A1` through `275-A35`, and Entry 276 supplements as `276-A36` through `276-A46`. Retire active alias `275-A29` and `276-A47`; replace them with `277-A29a`, `277-A29b`, `277-A47a` and `277-A47b`. New test cases introduced here use `277-A48` onward.

The final manifest MUST use qualified globally unique IDs, with one setup, one expected result, traceability and positive/negative/boundary classification. Duplicate IDs, bare ambiguous references, “X or Y”, unassigned codes, or no positive/exact-boundary tests invalidate the artifact.

Replacement fixtures:
- `277-A29a` — Submit forbidden lexical syntax/alias (ADS, UNC/device, traversal, tilde alias, trailing dot/space, reserved device basename, control/bidi/Unicode). Expected: `PATH_FORM_UNSUPPORTED` before lookup; no filesystem existence disclosure.
- `277-A29b` — Submit syntactically valid path whose scope cannot safely be established at the permitted stage. Expected: uniform `PATH_SCOPE_UNAVAILABLE`; no existence/type/size disclosure.
- `277-A47a` — Roll back/miss workspace registration or checkout-lineage/tombstone epoch against independent anchor. Expected: `REGISTRY_ROLLBACK`.
- `277-A47b` — Registry/trust/destination epoch is current, but only active-block-set or scope-model epoch is stale/missing. Expected: `BLOCK_SCOPE_UNEVALUABLE`.

---

### [Entry 277 R9 (C4 amendment)] R9 — clock tolerance and revocation freshness (low)

Set the proposed `CLOCK_DISAGREEMENT_TOLERANCE` to 2 seconds for disagreement between elapsed-time and wall-clock observations, but only on a platform whose monotonic source's suspend semantics have been established. A disagreement greater than two seconds expires every active decision and pending nonce. Independently, any detected backward wall-clock step expires every active decision and pending nonce regardless of magnitude; the tolerance never revives a grant. If clock comparison or suspend semantics cannot be established, fail closed.

At `RELEASE_AUTHORIZED`, cached revocation data is not acceptable. The verifier must query the authoritative revocation source at the gate with proposed `REVOCATION_MAX_STALENESS = 0 seconds`. The response must include an authenticated current version/time marker with independently established semantics. Missing/stale marker, unavailable/inconsistent source or inability to establish freshness means deny and discard staged content. Zero cache age does not prove linearizability or eliminate every race after the query; those properties remain `UNPROVEN` until established.

**Test:** extend `A39` with exact two-second boundary, greater-than-two-second discrepancy, unknown suspend semantics, missing/stale revocation version and stale trust/revocation epoch. Extend `277-A50` with backward wall-clock movement smaller than two seconds. Each setup has one expected result.

---

## 6. Single authoritative conformance manifest

All cases in this manifest are proposed and non-executed. Fixtures must be synthetic and isolated from M0A and real secrets. Filesystem race tests require the target platform's real temporary filesystem and controlled substitution points; mocked I/O alone does not establish OS race guarantees. Ledger tests must distinguish process restart, interrupted transactions and actual power-loss claims.

Stable test identity is namespaced by source. Entry 275 A1–A35 is the only active base matrix, except A29 which is retired and split below. Entry 276 A36–A46 supplements it; Entry 276 A47 is retired and split below. New/rewritten cases use Entry 277 identifiers. The old Entry 274 A1–A22 matrix is historical only and is excluded from the active manifest.

| Qualified ID | Condition / setup | Exactly one expected result |
|---|---|---|
| 275-A1 | Missing/unknown decision or missing ledger record | `LEDGER_INTEGRITY_UNPROVEN`; deny before content I/O |
| 275-A2 | Same-OS-user UI automation/synthetic event attempts approval | No trusted attestation; no decision |
| 275-A3 | ApprovalMemory, relaxed policy, forged/missing UI event, missing principal | Reject at issuance |
| 275-A4 | Nonce/event replay, including after issuance crash/restart | Nonce consumed atomically; no second decision |
| 275-A5 | Wrong requester session/agent on shared or multiplexed transport | Deny |
| 275-A6 | Truncated UI, unsafe bidi/control path, altered raw/canonical form | Approval rejected |
| 275-A7 | Scope, target, recipient, path, budget or requester-supplied purpose altered | Server-derived facts prevail; digest mismatch denies |
| 275-A8 | Wrong server/workspace/root/worktree/lifecycle identity | Deny before content I/O |
| 275-A9 | Dirty/detached checkout with proven minimum identity | Do not require a clean tree; no out-of-scope scan |
| 275-A10 | Requested object/path changes between preview, approval, open and release | `PATH_SCOPE_UNAVAILABLE` as primary result; if content is staged, lifecycle status `DISCARDED`; no unverified bytes delivered |
| 275-A11 | Root/path substitution or link/reparse escape where exact containment cannot be proven | `CONTAINMENT_UNPROVEN`; no outside-root content/names |
| 275-A12 | Unknown or incomplete lineage for a block-scoped identity | `BLOCK_SCOPE_UNEVALUABLE` under C3-10; `BLOCK_RELEASE_UNSUPPORTED` applies only when scope is evaluable and the block is applicable but unreleased |
| 275-A13 | All block types and scope dimensions | Table has explicit result per dimension/combination; every applicable block requires independent release |
| 275-A14 | Missing/unsupported scope model or partial target identity | `BLOCK_SCOPE_UNEVALUABLE`; deny |
| 275-A15 | No supported independent block release | `BLOCK_RELEASE_UNSUPPORTED`; deny |
| 275-A16 | Same block ID but changed revision/digest | Old release does not apply |
| 275-A17 [RETIRED] | Revocation source unavailable OR decision expires during staging/handoff | Composite retired; see 278-A17a and 278-A17b |
| 275-A18 | Existing sensitive-file rule with file on allowlist | Deny despite allowlist |
| 275-A19 | Valid in-root file absent from exact allowlist | Deny before content I/O |
| 275-A20 | Listing target directory not explicitly allowed | Deny; disclose no names |
| 275-A21 | Diagnostic-only request | Metadata only; zero file reads, no decision issued |
| 275-A22 [RETIRED] | Ledger rollback/integrity failure OR ledger unavailable | Composite retired; see 278-A22a and 278-A22b |
| 275-A23 | Concurrent operations compete for last budget units | Atomic reservations never overspend |
| 275-A24 | Crash between intent, stage, release authorization and response | Correct durable state; no automatic replay; unresolved state halts reads |
| 275-A25 | Completion/release record fails after internal read | No content delivery; maximum reservation charged; persistent halt |
| 275-A26 [RETIRED] | Exact 1 MiB file AND valid exact-200-entry directory | Composite retired; see 278-A26a and 278-A26b |
| 275-A27 [RETIRED] | File over 1 MiB OR directory with 201 actual entries | Composite retired; see 278-A27a and 278-A27b |
| 275-A28 | Directory contains 201 raw entries including link/reparse entries | Overflow detected from raw count; deny whole listing |
| 275-A29 [RETIRED] | Historical combined alias-class case | Superseded by 277-A29a and 277-A29b; not active |
| 275-A30 | Hard link with nlink not 1/unavailable or unsupported volume | Deny |
| 275-A31 | Concurrent writer/replacement during staging | Deny/discard if exclusion or stable-object guarantee fails |
| 275-A32 | Listing encounters one invalid, sensitive or reparse entry within 200 | Deny entire listing; no silent omission/partial names |
| 275-A33 | Restored old ledger, duplicate operation ID and retry after lost reply | Rollback/integrity failure selects `LEDGER_INTEGRITY_UNPROVEN`; retry remains idempotent with no fresh budget or re-delivery |
| 275-A34 | Happy path with all evidence/authority available | Exact object only; durable release authorization before output; appropriate receipt status afterward |
| 275-A35 [RETIRED] | Outside-allowlist file OR directory-prefix/wildcard OR sensitive path in a list | Composite retired; 275-A18/A19/A20/A32 and 278-A35a/b cover the distinct conditions |
| 276-A36 | Well-formed Owner attestation signed by a credential not enrolled in the protected trust store | `APPROVAL_CHANNEL_UNTRUSTED`; no decision |
| 276-A37 | Before Owner confirmation, compare normal existing, normal nonexistent, sensitive existing and sensitive nonexistent paths | Requester-visible status/shape do not disclose existence; sensitive-name denial before lookup |
| 276-A38 | Server-protected destination/provider configuration changes after approval preview but before content release | Digest mismatch; staged content discarded and no delivery |
| 276-A39 | Monotonic clock stalls or suspend semantics are unknown while wall time advances beyond tolerance | Active decisions and pending nonces expire; fail closed |
| 276-A40 [RETIRED] | Structural pseudo-entries plus 200 actual entries OR 201 actual entries | Composite retired; see 278-A40a and 278-A40b |
| 276-A41 | One applicable block plus another block whose scope evidence cannot be evaluated | Deterministic `BLOCK_SCOPE_UNEVALUABLE` precedence; no read or release inference |
| 276-A42 | Decision issuance committed but reply lost; retry uses same request token and same scope | Same decision/state returned; nonce consumed and budget unchanged |
| 276-A43 | Same request token reused with different scope digest | Deny and audit; no new decision or reset budget |
| 276-A44 | Contract artifact contains duplicate top-level headers, malformed full-match regex, missing reserved-name suffixes or duplicate test IDs | Artifact/manifest validation fails; not adoptable |
| 276-A45 | Test suite has no positive path or exact-limit boundary case | Manifest validation fails; deny-all implementation cannot pass |
| 276-A46 | Local handoff returns but recipient acknowledgement is unavailable | Record `HANDOFF_RETURNED`, not `DELIVERED` |
| 276-A47 [RETIRED] | Combined registry/block epoch case with ambiguous expected code | Superseded by 277-A47a and 277-A47b; not active |
| 277-A29a | Forbidden lexical syntax/alias: ADS, UNC/device, traversal, tilde short-name alias, trailing dot/space, reserved basename, control/bidi/Unicode | `PATH_FORM_UNSUPPORTED` before lookup; no existence disclosure |
| 277-A29b | Syntactically valid path whose scope cannot safely be established at its permitted resolution phase | Uniform `PATH_SCOPE_UNAVAILABLE`; do not disclose existence/type/size |
| 277-A47a | Workspace registration or checkout-lineage/tombstone epoch rolled back relative to independent anchor | `REGISTRY_ROLLBACK` |
| 277-A47b | Registry/trust/destination epoch current; only active-block-set or scope-model epoch is stale/missing | `BLOCK_SCOPE_UNEVALUABLE` |
| 277-A48 | A session/token value is copied to another local process or agent principal | Reject before content access; if process/agent distinction cannot be proved, issue no decision (`APPROVAL_CHANNEL_UNTRUSTED`) |
| 277-A49 [RETIRED] | Crash at either handoff transition | Composite retired; see 278-A49a and 278-A49b |
| 277-A50 | Wall clock moves backwards after issuance, even if the delta is under two seconds | Expire all active decisions and pending nonces; fail closed; do not revive |
| 277-A51 | Restored trust-store snapshot predates a credential revocation and its epoch is older than independent anchor | `REGISTRY_ROLLBACK` before approval/content access |
| 277-A52 | Covered authority epoch changes after operation intent commit but before final release gate | `REGISTRY_ROLLBACK` primary code; durable operation state `DISCARDED`; no content, decision, nonce or budget reset |
| 277-A53 | Retry committed issuance after process restart with same principal/session/token/digest | Return current state `EXPIRED`; no reactivation, new nonce or budget reset |
| 277-A54 | Directory contains 199 valid actual entries and structural `.` and `..` pseudo-entries | Count/charge exactly 199 actual entries; listing may pass if all gates pass |
| 277-A55 | Conformance manifest runs all positive, negative and exact-boundary grammar subcases; each subcase has a fixed setup/result | Manifest passes only if every required subcase has its specified result; deny-all fails |
| 277-A56 [RETIRED] | Clock/suspend failure OR revocation freshness failure | Composite retired; see 278-A56a and 278-A56b |
| 277-A57 | Relative path is syntactically valid and ≤240 characters, but root-plus-relative exceeds proven platform support | Uniform `PATH_SCOPE_UNAVAILABLE`; no unsupported lookup or assumed long-path mode |
| 277-A58 | Full external state-sequence comparison for normal-existing/missing and sensitive-existing/missing targets | No existence oracle; no object-dependent `BLOCK_*` code before Owner confirmation; sensitive-name rejection precedes lookup |


| 278-A17a | Authoritative revocation source unavailable/stale at a required gate while the decision has not independently expired | `REVOCATION_UNAVAILABLE`; discard staged content, deliver nothing |
| 278-A17b | Decision expires during staging/handoff while the revocation source is otherwise available | `DECISION_EXPIRED`; discard staged content, deliver nothing |
| 278-A22a | Restored ledger/anchor mismatch or integrity-chain failure | `LEDGER_INTEGRITY_UNPROVEN`; no reads pending recovery/reconciliation |
| 278-A22b | Authoritative ledger cannot be accessed | `LEDGER_UNAVAILABLE`; no reads |
| 278-A26a | Exact 1 MiB file and all authorization/identity/ledger gates pass | Positive boundary: allow exact bytes; commit durable completion before release |
| 278-A26b | Exactly 200 valid actual directory entries; structural pseudo-names excluded | Positive boundary: permit listing and charge exactly 200 actual entries |
| 278-A27a | File requires reading more than 1 MiB to detect overflow | `FILE_LIMIT_EXCEEDED`; no partial content |
| 278-A27b | Directory contains 201 actual entries, regardless of structural pseudo-names | `LIST_LIMIT_EXCEEDED`; no partial names |
| 278-A35a | Caller attempts a directory-prefix grant instead of an exact approved target | `PATH_SCOPE_UNAVAILABLE`; no prefix grant or child traversal authority |
| 278-A35b | Caller includes a wildcard in a path request | `PATH_FORM_UNSUPPORTED` before lookup |
| 278-A40a | Directory has structural `.` and `..` plus exactly 200 valid actual entries | Allow if all other gates pass; count/charge exactly 200 actual entries |
| 278-A40b | Directory has 201 actual entries plus any structural pseudo-names | `LIST_LIMIT_EXCEEDED`; deny the complete listing |
| 278-A49a | Crash after `RELEASE_AUTHORIZED` and before `HANDOFF_RETURNED` | `UNRESOLVED`; reservation retained, reader halted pending reconciliation, no automatic replay |
| 278-A49b | Crash after `HANDOFF_RETURNED` and before durable final state/acknowledgement | `UNRESOLVED`; not `DELIVERED`, reservation retained, no automatic replay |
| 278-A56a | Clock disagreement exceeds two seconds, or suspend semantics are not established | `DECISION_EXPIRED`; all active decisions and pending nonces expire |
| 278-A56b | Final-gate revocation response is cached, stale, missing or lacks authenticated freshness | `REVOCATION_UNAVAILABLE`; discard, deliver nothing |
Required acceptance evidence inherited from the C2 matrix: filesystem-race claims require (a) static review proving the same verified handle is used with no post-verification name-based reopen; (b) target-platform documentation/semantics for selected primitives; and (c) controlled real-filesystem substitution stress tests across defined race points and iterations. Stress tests are evidence, not formal proof of absence of every race; if primitives cannot meet the conditions, v1 fails closed. Ledger durability/anti-rollback tests include process restart, interrupted transaction/recovery, restored older ledger and anchor mismatch. A test that cannot simulate hardware power loss MUST NOT claim to prove power-loss durability.


## 7. Evidence, status and unresolved platform gates

- `PROVEN_BY_SOURCE`: the source documents/objects named in Section 0 were fetched from the linked public repository at the recorded paths/SHAs. This proves text and provenance only, not implementation behavior.
- `OWNER_REPORTED`: the C2, C3 and C4 review reports and prior local M0A denial reports. The coordinator has not accessed M0A, run the blocked reader, or inspected credentials.
- `PROPOSED`: all normative clauses and conformance cases in this candidate.
- `UNPROVEN`: every implementation/runtime property; Windows path/reserved-name behavior; actual same-user isolation of the Owner UI; stable filesystem handles/containment; anti-rollback anchors; trustworthy time/suspend semantics; authoritative revocation freshness; delivery acknowledgement; production scope applicability; and any ability to honor this contract on the target platform.

## 8. Next action and operational boundary

**Next actor:** Sonnet/Claude, one targeted delta review of this complete Entry 278 artifact only. Inspect the consolidated precedence, the C2/C3 clauses as now embedded, the R1–R9 C4 repairs, and the active manifest in Section 6. Challenge the merger and any remaining contradiction; report `PASS`, `PASS_WITH_REPAIRS` or `FAIL`, each surviving counterexample, its exact section, a minimal text fix and one discriminating test. No broad source archaeology.

The result of that review can accept only a design baseline. It cannot authorize implementation or block release. No code/tests/build/runtime, local M0A access, blocked-reader retry/bypass, source/config edit for the product, credential inspection, authentication, installation/update or launch. Where an applicable governance block lacks independent supported release, the terminal result remains `BLOCK_RELEASE_UNSUPPORTED`. `KEEP_BLOCKED`.
