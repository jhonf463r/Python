# M1 — Minimal governed scoped-read route: documentary design proposal

- **Episode ID:** `EP-20261022-M1-GOVERNANCE-ROUTE-MINIMAL-DESIGN-01`
- **Date:** 2026-10-22, America/Bogota.
- **Artifact type:** proposed documentary design for owner/competent-authority review.
- **Decision provenance:** the Owner explicitly authorized Option 2 (documentary design only) in this coordination session. This record documents that scope; it is not a runtime grant, implementation approval, or operational-block release.
- **North star:** `GOVERNED_IABV_CODEX_BRIDGE`.
- **Active task:** `M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`.
- **Canonical routing authority:** [CURRENT-STATE.md](./CURRENT-STATE.md).
- **Related adjudication:** [Issue #470](https://github.com/jhonf463r/Python/issues/470).
- **Normative design inputs reused:** [Entry 266 — observation approval is not audit release](./CHAT-ARCH-2026-10-13-266-observation-approval-is-not-audit-release.md); [Entry 274 — consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md); [builder-grant successor v0.2](./CHAT-ARCH-2026-10-22-builder-grant-contract-successor-v0.2.md); [independent review of builder-grant contract](./CHAT-ARCH-2026-10-22-independent-review-builder-grant-contract.md); [M1 governance-surface inventory follow-up](./CHAT-ARCH-2026-10-22-governance-surface-inventory-followup.md).

## 1. Executive disposition

**Design result:** `PROPOSED_MINIMAL_GOVERNED_SCOPED_READ_ROUTE`  
**Design readiness:** `READY_FOR_OWNER_AUTHORITY_REVIEW_ONLY`  
**Supported route:** `UNRESOLVED`  
**Issuer / authenticated principal:** `UNRESOLVED`  
**Live MCP server identity:** `UNVERIFIED`  
**Actual checkout identity:** `UNVERIFIED`  
**Independent block-release authority:** `UNRESOLVED`  
**Implementation readiness:** `NO`

The smallest coherent mechanism is not a permission flag or a new reader call. It is a chain of independently verifiable authority and enforcement boundaries:

1. identify the actual MCP server/session and checkout using trusted evidence;
2. obtain fresh, authenticated Owner approval of the complete finite scope through an already-supported trusted interface;
3. have a separately trusted issuer create a server-side, session-bound read decision;
4. have the actual reader revalidate identity, exact scope, expiry/revocation, the applicable operational block, and receipt-store health immediately before every operation;
5. enforce filesystem containment on the opened object, not only on a caller-supplied path;
6. record durable pre-effect intent and post-effect outcome in an independently protected, verifiable ledger; and
7. require a separate authenticated decision from the competent block owner to release an applicable `operational_block_active` restriction.

These are proposed contractual roles and ordering constraints, **not names of existing APIs or proof that any component is present**. The sources reviewed and the supplied session inventories do not identify an existing issuer, administrative operation, root resolver, receipt authority, or independent block-release operation. Therefore this design does not create a usable route and does not complete M1.

## 2. Evidence boundary and provenance

### Bounded surface results reused

| Surface or evidence | Result | Provenance / meaning |
|---|---|---|
| ChatGPT callable-tool catalogue in the current session | `NOT_FOUND_IN_CHECKED_SESSION_SURFACE` | Directly examined in this session; no IABV governance-owned scoped-read or block-release action was exposed. |
| Existing Codex session, reported 176-tool inventory | `NOT_FOUND_IN_CODEX_SESSION_SURFACE` | Owner-reported result; not independently executed in this ChatGPT session. |
| Antigravity / Opus 4.6 session inventory | `NOT_FOUND_IN_ANTIGRAVITY_SESSION_SURFACE` | Owner-supplied result; the supplied account says the inventory did not execute commands, read files, or use MCP. |
| Issue #470 current body/comments | No verified callable issuer, administrative operation, or independent block-release authority identified | Fetched from GitHub; issue content records the unresolved dependency but is not itself an authority. |
| Entry 274 | Proposed repository-read contract | Normative documentary input, not proof of an implemented capability. |
| Builder-grant successor v0.2 | Proposed builder-session grant with explicit non-implementability dispositions | Reused, not redrafted or reviewed again here. It is distinct from exact-path repository reading. |

`GLOBAL_ROUTE_EXISTENCE=UNRESOLVED`. The negative results are limited to the named session surfaces and current issue content. They do not prove a route is absent everywhere. No additional tool inventory, broad source scan, alternative-reader attempt, or subagent/MCP probe is part of this design.

### Existing contracts retained

- Entry 274's five distinct authorities remain separate: diagnostic, fresh approval evidence, server-side read decision, per-operation reader verifier, and durable operation ledger/receipt.
- Entry 266 remains controlling for the distinction between observation permission and repository-read authority or audit-gate release.
- Builder-grant v0.2 is used only as existing evidence for containment, root/session binding, authoritative time, revocation, receipt integrity and independent block custody. A broad builder-session grant does not substitute for Entry 274's exact-path read decision.
- No `approved` boolean, conversational statement, issue comment, model-generated verdict, diagnostic result, `approved_by` string, `VALIDATED` label, or receipt alone may grant access or release a block.

## 3. Minimal conceptual architecture and trust boundaries

The names below describe responsibilities in this proposal. They are **not existing class names, API endpoints, tools, or verified implementation components**.

| Boundary | Minimum responsibility | Trust requirement | Deny condition |
|---|---|---|---|
| A. Target identity resolver | Establish exact server instance/session and actual checkout/root identity from approved, authoritative sources | Evidence anchored outside the requesting agent's own claims | Server, process/session, checkout, root object, or revision binding is missing, ambiguous, stale, or contradictory |
| B. Owner approval authority | Present the complete proposed operation and scope; capture a fresh explicit human decision | Authenticated Owner principal; approval event delivered directly to the trusted issuer | Principal, event, target, scope digest, or audience cannot be verified |
| C. Read-decision issuer | Validate approval evidence and policy; create the authoritative, finite decision in server-side custody | Existing, supported issuer with independently verified identity and permission to issue this decision | Issuer or policy authority unknown; approval replayed; request-supplied identity treated as proof |
| D. Per-operation reader verifier | Revalidate decision, target, path/object, budgets, time/revocation, block state, and receipt availability immediately before each read | Enforcement on the actual reader path; no caller-controlled bypass | Any check unavailable, out of scope, stale, or inconsistent |
| E. Independent receipt custodian/verifier | Preserve a tamper-evident intent/outcome history independent of requester and reader write authority | Separately controlled durable store, integrity verification, trusted time/sequence basis | Store unavailable, integrity/watermark failure, missing intent/outcome, or unclear custody |
| F. Operational-block authority | Decide whether an applicable block may be released and issue its own verifiable release record, or preserve the block | Principal and operation independent of the read issuer, reader, requester, and grant consumer | Authority or applicability unresolved, or no valid release evidence for an applicable block |
| G. Independent reconciliation | Check that target, read decision, operation receipts and separate block decision agree | Reviewer/system other than the components being verified, with access to authoritative receipts | Missing evidence, conflicting identity, or circular/self-issued proof |

**No implicit trust:** a component cannot prove its own identity solely by reporting a name; a reader cannot issue its own authority; a requester cannot choose a principal ID, session ID, checkout ID, scope digest, receipt sequence or block-release result and have that choice accepted as evidence.

## 4. Server and checkout identity contract

Both identities must be bound, because a correct permission applied to the wrong endpoint or checkout is still unauthorized access.

### 4.1 MCP server and session

Before approval is considered usable, the responsible authority must identify an existing supported way to verify at least:

- the canonical server/service identity and the trust anchor used to recognize it;
- the concrete server instance and endpoint/transport to which the decision applies;
- the executing server process or otherwise unforgeable runtime/session identity, to the extent supported by the platform;
- the server build/source revision or other trusted version evidence needed to know which enforcement policy is running;
- the authenticated requester and reader-session binding; and
- the method for detecting replacement, restart, endpoint substitution, session change, or loss of liveness.

A display name, endpoint string, process name, self-reported version, remembered conversation, or successful connection is not sufficient by itself. Use only an existing, supportable trust mechanism that the competent authority can identify and explain. Do not invent a certificate issuer, service registry, signature key, API, or new paid dependency.

### 4.2 Actual checkout and filesystem root

The decision must bind to the intended repository/workspace **and the actual checkout**, not merely to the public repository name, branch label or textual path. Evidence required by the adopted platform contract should include:

- canonical repository identity and trusted commit/ref metadata where applicable;
- the exact workspace/checkout lifecycle identity;
- the normalized root path plus stable filesystem/volume identity and root-object identity;
- worktree identity and whether relevant source state is known to be clean, dirty or detached, without silently assuming cleanliness;
- the identity of each allowed filesystem object at open/read time; and
- revalidation that the object actually opened remains beneath the bound root and matches the approved object/path policy.

Path-prefix checks alone are insufficient. The future enforcer must handle path normalization, case/Unicode aliases as relevant to the platform, parent traversal, symbolic links, Windows junctions/reparse points, hard links, root replacement, alternate checkout paths, and time-of-check/time-of-use races. The opened handle/object and containment must be verified at operation time; checking a string before opening is not enough.

Identity resolution must not perform a recursive pre-authorization content scan, read disallowed paths, execute Git/shell hooks, or launch a process to fingerprint the whole worktree. If the required binding cannot be established using already authorized metadata and the supported resolver, deny. This design itself did not inspect the actual local checkout.

## 5. Trusted principal, approval and scoped decision

### 5.1 Trusted issuer and authenticated Owner principal

The Owner/competent authority must identify the existing supported issuer and authentication chain, including who owns the trust anchor, how the human principal is authenticated, how the issuer is authorized to issue read decisions, and how decision records can be independently verified.

The approval mechanism must bind a fresh, single-use challenge to the authenticated Owner, the direct trusted UI event, the intended requester/reader, the actual target, and a digest of the exact displayed scope. The requester must not be able to synthesize the approval event, choose or echo the nonce, or replace the scope between approval and issuance. Replays, mismatched targets, expired challenges, unknown principals, and unavailable identity services deny.

The UI must display, before confirmation, the exact server/checkout, operation class, every permitted path or directory-listing target, byte/call/entry limits, purpose, expiry, and intended recipient/audience (including any external AI/provider that will receive content). Raw and canonical path forms must be made unambiguous and safely rendered. Truncated or ambiguous scope is not approvable.

If no existing trusted issuer/principal mechanism can be identified, record `AUTHORITY_UNAVAILABLE`; do not create a self-signed grant or substitute conversational approval.

### 5.2 Decision contents and exact allowlist

A decision must be an authoritative server-side record and must bind at least:

- schema/policy version and non-reusable decision identifier;
- authenticated Owner-principal and approval-evidence references;
- issuer identity, intended MCP server instance, requesting connection/session and reader identity;
- repository, actual checkout/worktree lifecycle, root-object binding, and trusted revision metadata required by the policy;
- purpose, audience/recipient, operation class, and a finite **explicit** allowlist;
- bounded per-operation and aggregate budgets (for example, maximum calls, files/entries, bytes per file, total bytes, listing depth and total response size);
- issue/approval times, not-before time if used, expiry, maximum decision age, authoritative time source, and current revocation epoch/version;
- the required independent block-release evidence reference when a block applies;
- decision status, atomic budget accounting and references to its durable operation receipts.

No wildcard, prefix rule, parent traversal, implicit directory recursion, arbitrary glob, unbounded output, “all repository” scope or inference from a filename prefix is permitted. A directory listing is a separate capability whose target, depth, entry count and returned metadata are explicitly scoped; permission to list a directory does not imply permission to read every listed file. Any additional file or capability requires a new decision and explicit approval.

The exact source-path allowlist for the proposed IABV→Codex audit is **not defined by this document**. It must be evidence-backed and explicitly approved before a future decision is issued; it must not be silently enlarged to include a complete bridge/Ollama trace. A scope that is incomplete for the objective must be labelled incomplete, not stretched by inference.

### 5.3 Decision custody and non-transferability

The authoritative decision and remaining budgets live in trusted server-side custody. The requester may receive a reference/identifier, but that reference is not itself a transferable bearer grant. The decision is bound to its authenticated reader and session. A missing or inconsistent ledger entry, changed session, missing budget state, replay, or untrusted restart recovery denies. Do not reconstruct permission from caller-supplied fields, an in-memory default, a copied signed object or a chat transcript.

## 6. Per-operation enforcement and filesystem containment

For every read/list operation, the actual enforcement point must independently and freshly verify all of the following immediately before any content effect:

1. trusted issuer and authenticated Owner approval;
2. active server/session binding and actual checkout/root/object identity;
3. exact operation and path membership in the approved scope, including canonicalization and handle-level containment;
4. decision validity, budget availability, authoritative expiry, current revocation and session liveness;
5. the effective operational-block state and the independent release evidence if a relevant block applies;
6. healthy, writable and independently verifiable receipt custody; and
7. recipient/audience binding and any required response-size constraints.

All checks must run on the reader's real execution path, not only in a UI or request wrapper. Validation must be repeated for every operation; one initial “allow” cannot authorize later calls. Recheck relevant identity and scope after opening/staging and before delivering content. Any changed root, checkout, target object, session, path meaning or policy invalidates the decision.

The operation must fail closed on unsupported filesystem guarantees. In particular, a successful prefix comparison cannot be treated as proof against symlinks/reparse points, hard links, root substitution or TOCTOU races. If stable handle identity and containment cannot be enforced on the actual platform, the route is not implementable with current evidence.

A read grant authorizes only the explicit read/list operations in that grant. It never authorizes editing source/configuration, running tests/builds, launching processes, installing/updating, changing credentials/environment, starting IABV/Codex/Ollama, merging candidates, deployment, or real transport.

## 7. Durable and independently verifiable operation receipt

Every attempted privileged operation needs durable evidence. The requester, reader and builder must not be able to rewrite, delete, truncate, replay or forge that evidence. The contract must identify an existing independent custodian, its access boundary, integrity verifier, authoritative time/sequence source, recovery rules, and how an independent reviewer obtains verification evidence without gaining additional source access.

At minimum, a receipt chain records:

- operation and decision IDs, policy version, issuer and authenticated-principal references;
- reader/session, server instance, checkout/root and target-object binding;
- exact operation, canonical path/scope reference, bounded budget delta and recipient/audience;
- trusted time, monotonic sequence/epoch and status;
- a durable pre-effect intent/reservation before content access;
- allow/deny result and stable denial reason;
- post-effect outcome, byte/entry counts and a digest of delivered content/metadata where the contract requires it, without logging secret values; and
- integrity linkage to prior records, an independently protected signature or equivalent authenticated integrity mechanism, and a trusted watermark/anti-rollback check.

**Ordering:** verify the decision and all gates → durably persist pre-effect intent → only then access the approved object → revalidate before delivery → durably record completion/denial/failure correlated to that intent. If the pre-effect receipt is not durable, do not begin the read. If completion evidence cannot be persisted or verified, suspend further reads and mark the outcome indeterminate pending reconciliation; never claim success solely because bytes may have been read.

A hash chain, signature, append-only label or unique ID is not sufficient unless its key/custody, sequence and rollback-detection authority are themselves trusted and independently verifiable. If the receipt service is unavailable, its integrity fails, the history is truncated, or custody is unresolved, deny and stop. Do not introduce a new ledger service or key system by assumption.

## 8. Independent operational-block release

The read-decision control plane and operational-block control plane are separate.

- The authority responsible for the active block must be identified independently of the requester, reader, read-decision issuer and receipt consumer.
- It must make an explicit, authenticated decision tied to the specific block identity, target/server/checkout, the reason/scope being released, decision time, expiry or revocation semantics, and permitted consequence.
- The block-release record must be independently verifiable at the enforcement point and at reconciliation.
- Issuing, renewing, consuming or verifying a read decision must not mutate the block state.
- A receipt proves a recorded event; it does not authorize a release. The read issuer cannot sign a release merely because it issued the read decision.
- Observation permission (including `approve_observation_permission` / `observe_window_content:codex`) is not repository-read permission or audit-block release.
- If block applicability is unknown, the block identity cannot be tied to the actual server/checkout, or no valid independent release is available for an applicable block, deny. Preserve the terminal denial `BLOCK_RELEASE_UNSUPPORTED` where that is the governing contract result; incomplete/unevaluable scope must not be misclassified as a grant.

The design does not claim a block-release API exists, and it does not decide that the known active restriction is or is not applicable to a live server. That requires trusted identity/policy evidence from the competent authority. A source-code candidate's static verdict, a route-design document, a UI affordance or an approval comment cannot release the current restriction.

## 9. Minimal protocol and failure behavior

The normative order is:

1. **Request:** a caller asks for a finite read scope. Caller-supplied IDs are request data, not authority.
2. **Bounded diagnostic (if an existing supported diagnostic is available):** returns only the minimum block/target metadata needed to explain denial; it reads no repository content and grants nothing. Do not invent a diagnostic endpoint.
3. **Resolve target:** an established trusted resolver binds the actual MCP server/session and checkout/root. Unknown identity stops the flow.
4. **Approve scope:** the trusted interface displays the complete target, paths, operation, budget, purpose, expiry and recipient; the authenticated Owner explicitly approves or denies.
5. **Issue decision:** the trusted issuer validates the fresh approval and writes the authoritative session-bound decision. If its existence or authority cannot be verified, stop.
6. **Check block independently:** verify either authoritative evidence that no applicable block prevents this operation or a separate valid release decision from the competent block authority. A read decision cannot supply this proof itself.
7. **Execute one operation:** the real reader repeats every per-operation check and writes the pre-effect intent before accessing only the approved object.
8. **Finalize receipt:** durably record the result and verify the receipt chain before treating the operation as complete.
9. **Reconcile:** an independent checker verifies the chain, target, path/scope, budget, block evidence and delivered-result status. Any gap leaves M1 unresolved and prevents the result from being used as proof of governed access.

Mandatory fail-closed outcomes include `AUTHORITY_UNAVAILABLE`, `TARGET_IDENTITY_UNVERIFIED`, `CHECKOUT_IDENTITY_UNVERIFIED`, `SCOPE_INVALID_OR_UNKNOWN`, `DECISION_EXPIRED`, `DECISION_REVOKED`, `SESSION_NOT_LIVE`, `BLOCK_RELEASE_UNSUPPORTED`, `RECEIPT_STORE_UNAVAILABLE`, `RECEIPT_INTEGRITY_FAILURE`, and `OUTCOME_INDETERMINATE`. These are proposed semantic labels unless an existing contract already defines the governing name; no API or current implementation is asserted by listing them here. Where the existing Entry 274 contract defines precedence or a denial name, that existing contract takes precedence over a new label in this proposal.

Unknown status, missing state, disagreement between authorities, stale revocation, untrusted time, failed receipt persistence, or inability to prove the actual enforcement path must never default to allow.

## 10. Decisions the Owner / competent authority must supply

These are real unresolved decisions, not fields the coordinator may fill by inference.

| ID | Required decision/evidence | Responsible party | Current status |
|---|---|---|---|
| D-01 | Name the accountable governance authority for the live MCP server, actual checkout and current operational block; provide an authoritative contact/control surface | Owner / competent governance authority | `UNRESOLVED` |
| D-02 | Identify an already-supported issuer operation and its authoritative trust anchor; provide evidence of its identity, permission and lifecycle | Owner / issuer authority | `NOT_IDENTIFIED` |
| D-03 | Identify the authenticated Owner-principal mechanism and supported approval interface, including fresh-event and session binding | Owner / identity authority | `NOT_IDENTIFIED` |
| D-04 | Identify how the live MCP server instance, enforcement revision and authenticated reader session are independently verified | Server/operator authority | `UNVERIFIED` |
| D-05 | Identify the supported checkout/root/object resolver and its handle-level containment guarantees without out-of-scope reads | Checkout/operator authority | `UNVERIFIED` |
| D-06 | Decide the purpose, intended audience/recipient, precise first-phase path allowlist and finite operation/output budgets | Owner; grounded in a future authorized scope review | `NOT_DECIDED` |
| D-07 | Identify authoritative clock, session-liveness and revocation sources plus maximum accepted freshness/staleness | Issuer/enforcer authority | `NOT_IDENTIFIED` |
| D-08 | Identify the independently controlled durable ledger/receipt store, integrity key custody, watermark/anti-rollback and recovery procedure | Governance/audit authority | `NOT_IDENTIFIED` |
| D-09 | Identify who owns `operational_block_active`, how block applicability is determined for the real target, and the separate authenticated release decision/evidence | Operational-block owner, independently of read issuer | `NOT_IDENTIFIED` |
| D-10 | Identify the independent verifier/reviewer and the authoritative evidence they will inspect to accept identity, scope, decision, block release and receipt integrity | Owner / governance authority | `NOT_DECIDED` |
| D-11 | State whether any current supported mechanism can satisfy these requirements without new spend or new external service; if not, maintain the hard stop or separately authorize a future design-only dependency resolution | Owner / competent authority | `UNRESOLVED` |

A decision to use a mechanism is not proof that it exists. Each claimed capability requires source-backed or administrator-issued evidence from the responsible authority and independent validation appropriate to the trust boundary. If the Owner cannot identify the competent authority, this remains an external governance dependency; route discovery is not replaced by another broad AI inventory.

## 11. Acceptance criteria for a future authority-reviewed route

This proposal is acceptable for consideration only if a named authority can answer all of these with verifiable evidence:

- [ ] The issuer, authenticated Owner principal and trust anchor are identified, and the issuer is permitted to issue this exact class of read decision.
- [ ] The target resolver identifies the actual MCP server/session, enforcement revision, checkout lifecycle and filesystem root/object.
- [ ] The approved operation/path allowlist, budgets, purpose, recipient, expiry and revocation are finite and displayed before approval.
- [ ] The live reader rechecks every condition at operation time and enforces object-level containment against path substitution and TOCTOU.
- [ ] Every operation is tied to a server-side decision, non-transferable session, atomic budgets and a durable pre-effect intent.
- [ ] The receipt custody/integrity/rollback model is independently verifiable and survives the documented failure/recovery cases.
- [ ] A separately authenticated authority can release the applicable operational block, and the receipt is distinct from the read decision.
- [ ] Unknown, stale, missing, contradictory, unverified or unavailable states deny, with deterministic reason and recoverable evidence when the trusted ledger is healthy.
- [ ] The authorized first-phase scope is explicitly labeled partial and is not silently expanded to source execution, tests/builds, startup or transport.
- [ ] The actual implementation path and controls have been verified under a separately approved plan, with conformance evidence and a separate explicit decision authorizing any local read.

The last item is not satisfied by this document. No implementation/test authorization is granted here, and no implementation or operational test is requested by this design.

## 12. No-go conditions

M1 remains blocked if any of these hold: no named trusted issuer; no authenticated principal; no independently trusted live-server or checkout identity; no exact scope; no supported per-operation enforcement; no authoritative expiry/revocation; no independent tamper-evident receipt custody; no separate block-release authority/evidence when required; or no independent verification route.

Do not resolve any no-go condition through a guessed API, agent-defined trust root, new bearer token, self-approval, local file/process access, a second reader, an unapproved subagent/MCP tool, or a route inferred from the existence of generic infrastructure tools. Do not inspect `data/`, SQLite, secrets, `.env`, the local worktree, or any out-of-scope repository file to make this design more concrete.

If authoritative evidence shows an existing route cannot meet a requirement, the route is unsupported for M1. A new mechanism may only be considered as a **separate documentary design and authorization decision**; this Option 2 approval does not authorize its implementation.

## 13. State after this design

```
M1_DESIGN=PROPOSED_FOR_OWNER_AUTHORITY_REVIEW
M1=OPEN
SUPPORTED_SCOPED_READ_ROUTE=UNRESOLVED
GLOBAL_ROUTE_EXISTENCE=UNRESOLVED
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
TESTS=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
CANDIDATE_MERGED=NO
LOCAL_WORKTREE=UNTOUCHED
```

**Conclusion:** this is the smallest proposed trust-and-enforcement chain that could support a governed strictly read-only inspection if the required authorities and mechanisms already exist and can be verified. It defines what must connect; it does not claim those components exist. The active dependency is now explicit: the Owner or competent governance authority must provide authoritative identity/route/release evidence or maintain the stop. M1 cannot be marked complete, and no local read can begin, solely because the design has been saved or reviewed.
