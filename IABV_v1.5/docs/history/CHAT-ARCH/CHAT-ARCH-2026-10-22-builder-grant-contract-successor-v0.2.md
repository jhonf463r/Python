# Builder-session grant contract — documentary successor v0.2

- **Date:** 2026-10-22, America/Bogota.
- **Predecessor:** [Owner-supplied contract draft](./CHAT-ARCH-2026-10-22-owner-supplied-low-friction-builder-grant-contract-draft.md).
- **Independent review:** [review record and BA-01–BA-08 findings](./CHAT-ARCH-2026-10-22-independent-review-builder-grant-contract.md).
- **Artifact type:** documentary successor draft; not implementation, authorization, or evidence of existing capability.
- **Status:** `SUCCESSOR_DRAFT=DOCUMENTARY_ONLY`; `READY_FOR_IMPLEMENTATION=NO`; `OWNER_AUTHORITY_DECISION=PENDING`.
- **M1 status:** `OPEN`; this builder-grant contract is not evidence that a supported governance-owned scoped-read route exists.

## 0. Precedence, interpretation and state separation

The builder-session grant is a proposed authorization class for ordinary source/documentation work in a sanitized disposable candidate. It is distinct from Entry 274's proposed exact-path repository-reader contract. It is not available unless an existing trusted issuer, enforcer, root/session binding and receipt mechanism are independently identified and verified.

The verdict on this contract must always carry the non-implication in the same line:

```
SUCCESSOR_DESIGN_VERDICT=DOCUMENTARY_ONLY_M1_UNRESOLVED
BUILDER_GRANT=PROPOSED_NOT_IMPLEMENTED
SUPPORTED_M1_READ_ROUTE=UNRESOLVED
AUTHORITY=UNAVAILABLE_UNLESS_VERIFIED
IMPLEMENTATION=NOT_AUTHORIZED
GOVERNANCE=KEEP_BLOCKED
```

No reviewer may cite the builder-grant design as M1 progress, as proof of a route, or as authorization to read the current dirty checkout. Observation approval is not repository-read authority. A grant to construct does not release an operational block. Tests, builds, processes, network, merge, deployment, IABV/Codex/Ollama startup and real transport remain separately gated.

## 1. Authority prerequisite (BA-05) — hard stop

A valid grant requires a named, authenticated Owner/developer principal and a real supported issuer whose identity and authorization chain are verifiable through authoritative evidence. The builder, repository reader and running IABV may not issue, extend, consume their own privileged decision or release the operational block.

The issuer, principal-binding mechanism, root resolver, revocation authority, ledger custodian and independent block-release authority are currently `UNRESOLVED`. No conceptual class, stub, chat utterance, issue, or owner-supplied model output counts as an issuer or authentication mechanism.

If the competent authority and supported issuer cannot be named and verified, the normative result is:

```
AUTHORITY_UNAVAILABLE
GRANT_ISSUANCE=DENIED
ENFORCER_MODE=DENY_ALL_PRIVILEGED_OPERATIONS
IMPLEMENTATION=NOT_AUTHORIZED
```

No provisional issuer, self-signed builder grant, temporary permissive fallback, silent bypass or invented API is permitted. This is an explicit non-implementability disposition under current evidence, not a claim that no such authority exists globally. The Owner/competent authority may later provide a source-backed and verifiable decision; until then stop.

## 2. Candidate materialization and containment (BA-01) — not implementable on current evidence

Before any future authorization, the named candidate must be disposable and sanitized by construction, not only filtered by pathname. Secrets, credentials, user profile files, live/user data, production data, `data/`, SQLite and authentication files must be absent from or inaccessible inside the candidate by independent OS/sandbox/namespace enforcement.

The grant is bound to the repository identity, pinned source commit, stable candidate ID, live session ID, and filesystem identity of the candidate root (at minimum the platform's volume/filesystem identity plus root object/file ID). A textual path is not an authority anchor.

Every file operation must be mediated through a supported file-operation interface; the enforcer must open the target and verify the opened object/handle's identity and its containment against the trusted candidate root after open. Authorization based solely on a pre-open path check is prohibited. The design must explicitly resist time-of-check/time-of-use (TOCTOU) races, symbolic links, Windows junctions/reparse points, hard links, path aliases, alternate checkout paths and root replacement. A reparse point or hard-linked file with a link count exceeding the approved invariant is rejected. If the platform cannot establish the required object identity and containment, fail closed.

A denylist for `.env`, `data/`, SQLite or known secret names is secondary defense only; it cannot substitute for physical isolation. No implementation may claim these properties until a supported mechanism is identified and its guarantees are documented.

`BA01_STATUS=NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE`.

## 3. Ordinary development grant and scope intersection (BA-02 / BA-07)

Once a real trusted grant mechanism is established, ordinary source/documentation read/write may be granted once for a bounded session without prompting per file, but only within this intersection:

```
EFFECTIVE_SCOPE = VERIFIED_CANDIDATE_ROOT ∩ DECLARED_WORK_AREAS
```

All work-area entries are relative to the candidate root; absolute paths, parent traversal, empty/ambiguous roots, alternate checkouts and areas resolving outside the root are rejected at grant issuance. The enforcer resolves the target against the verified root for each operation and denies if identity, root, area, candidate or session changes.

The successor and all status records must state in the same decision line that the builder grant does not satisfy, unlock or prove M1. Never use `BUILDER_GRANT=PASS` as an M1 field or criterion.

`BA02_STATUS=TEXTUAL_BOUNDARY_PRESERVED_LABELING_REPAIR_REQUIRED`  
`BA07_STATUS=PROPOSED_SCOPE_INTERSECTION_NOT_IMPLEMENTED`.

## 4. Mediated file operations and execution payloads (BA-03) — not implementable on current evidence

The ordinary development grant authorizes file operations only through a mediated file API. It does not provide a shell, arbitrary child-process creation, arbitrary tool calls, network access, system configuration access, or any general-purpose command-execution surface. If the existing platform cannot enforce file mediation independently from process execution, the development grant must not be enabled.

Writing the source or test files does not authorize their execution. A separate test/build grant must bind at least: candidate and source commit; authorized tool/executable identity; exact approved invocation policy; environment and arguments; allowed output locations; resource and duration bounds; network/process policy; and a manifest of hashes covering test/build entrypoints, hooks, backends and automatically loaded configuration. The enforcer rechecks the approved manifest at execution; a changed auto-loaded file invalidates the grant until separately re-reviewed and authorized.

The test/build environment must be constructed by the enforcer with no inherited secrets or credentials. Writes to executable hooks and automatically loaded code/configuration that could escape the candidate policy are excluded from the ordinary grant or trigger reauthorization. A self-authored command string from the builder is not an approval artifact. Test/build grants never inherit permission from the ordinary file grant.

If no existing supported enforcer can bind execution to the approved payload and isolated environment, test/build authorization is not implementable under current evidence and must remain denied.

`BA03_STATUS=NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE`.

## 5. Durable receipt integrity and effect ordering (BA-04) — not implementable on current evidence

Every privileged operation requires an independent, durable, verifiable receipt. The ledger must be outside the candidate and outside builder write scope. The builder cannot alter, delete, truncate, replay or forge decision or operation records.

A conforming future mechanism must specify and enforce: authenticated issuer signatures; append-only receipt storage; hash chaining; monotonic sequence numbers and a signed/trusted watermark to detect truncation or rollback; decision ID, grant ID, session, candidate, source commit, capability, operation, target object identity, time basis, decision, effect status and denial code; and verified revocation/expiry status. Do not log secret values.

The operation protocol is two-phase: (1) verify grant, scope, block state and receipt store; (2) persist a durable pre-effect reservation/intent; (3) only then perform the authorized effect; (4) persist a completion/failure record correlated to the reservation. If the pre-effect record is not durable, the effect does not begin. If completion recording fails, the state is marked indeterminate, access is suspended, and no further privileged operation proceeds until reconciliation. In-flight writes at revocation or expiry are aborted where safely possible and otherwise marked indeterminate without reporting success.

Non-reusable IDs are not anti-replay by themselves. Missing ledger state, ambiguous sequence, failed signature, invalid chain, truncation, replay, storage rollback or unverifiable custody fails closed. If no existing independent custody and integrity mechanism can meet these conditions, receipt-dependent access is not implementable under current evidence.

`BA04_STATUS=NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE`.

## 6. Authoritative time, expiry, revocation and session liveness (BA-06 / BA-08)

Grant expiry must be evaluated against issuer-authoritative time, not an untrusted host clock. Each grant declares start, expiry, maximum decision age, revocation semantics, a live session ID and a revocation epoch/version.

The enforcer verifies the grant/session binding and current revocation state for every privileged operation, or uses a bounded revalidation interval explicitly approved in the contract with a recorded maximum staleness. If authoritative time, live session status, revocation status or freshness cannot be verified, deny. Revocation must invalidate cached allows within the declared and enforced bound; the builder cannot extend validity by caching or moving the local clock.

Closing or losing the bound session invalidates the grant. A grant may not be replayed in a new process/session. On expiry/revocation, reject new operations, abort in-flight writes where safely possible, and record any unresolved effect as indeterminate. Clock rollback, missed heartbeats, stale revocation, unknown time source, or ambiguous in-flight completion fails closed.

Required semantic denials include `GRANT_EXPIRED`, `GRANT_REVOKED`, `SESSION_NOT_LIVE`, and `AUTHORITY_UNAVAILABLE`, all accompanied by durable evidence if the trusted ledger is available; failure to write the necessary pre-effect denial/receipt must never turn a denied request into an allowed effect.

If no existing supported authoritative time/session/revocation mechanism can satisfy this, the grant is not implementable under current evidence.

`BA06_STATUS=NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE`  
`BA08_STATUS=PROPOSED_SESSION_BINDING_NOT_IMPLEMENTED`.

## 7. Independent operational-block authority

A builder grant and the operational governance gate are separate control planes. Before any privileged operation the enforcer must verify both (a) a valid scoped builder grant and (b) that no applicable operational block remains, or that a separately authenticated decision from the independent block owner validly released the specific block.

A read decision cannot release its own block. The builder, issuer of an unrelated grant, reader and running IABV cannot self-release. If the block authority, current block state, target applicability or authenticated release receipt is unresolved, deny with `BLOCK_RELEASE_UNSUPPORTED`. This contract does not declare a supported release operation to exist.

## 8. Decisions and capabilities explicitly not established

Current evidence does not establish that any of these exists: trusted builder-grant issuer; developer-principal binding; candidate namespace/materializer; handle-safe file API; independent sandbox/enforcer; isolated test/build executor; authoritative clock or session-liveness source; revocation service; protected append-only ledger; receipt signer/verifier; or independent operational-block release authority.

Consequently:

| Finding | Successor status | Required evidence before implementation |
|---|---|---|
| BA-01 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | Existing isolated candidate/root identity and race-resistant handle-containment mechanism source-verified |
| BA-02 | `TEXTUAL_BOUNDARY_PRESERVED_LABELING_REPAIR_REQUIRED` | M1 state never cites builder grant as route/read evidence |
| BA-03 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | Existing mediated file surface and execution-payload isolation source-verified |
| BA-04 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | Existing independently controlled durable ledger and ordering/integrity semantics source-verified |
| BA-05 | `AUTHORITY_UNAVAILABLE` until proof supplied | Owner/competent authority supplies a verifiable principal and existing authentication/issuer chain, or maintains hard stop |
| BA-06 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | Existing authoritative time, revocation and in-flight-operation semantics source-verified |
| BA-07 | `PROPOSED_SCOPE_INTERSECTION_NOT_IMPLEMENTED` | Effective scope defined as root intersection relative areas |
| BA-08 | `PROPOSED_SESSION_BINDING_NOT_IMPLEMENTED` | Existing verifiable live-session binding and closure invalidation source-verified |

The status `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` means “do not implement based on available evidence”; it does not assert global impossibility. No missing issuer, enforcer, clock, ledger or route may be replaced by a guessed API, temporary permissive stub, agent self-authorization or new paid service.

## 9. Non-executed acceptance criteria

These are requirements only; no cases below have been executed.

1. Hard link inside candidate to an external target → deny.
2. Reparse point/junction inserted between root validation and open → deny; no external bytes delivered.
3. Candidate root is renamed/replaced or a new checkout is substituted mid-session → next operation fails closed.
4. Candidate contains or can reach a real secret/live-data path → candidate creation/registration is rejected.
5. Builder attempts shell/process spawn using ordinary file grant → deny.
6. An auto-loaded test/build entrypoint hash changes after approval → refuse test/build until separately reviewed and reauthorized.
7. Test/build attempts to read inherited secrets or perform unapproved egress → isolated environment prevents reachability and policy denies.
8. Receipt store unavailable before effect → operation does not begin.
9. Receipt chain is truncated, signed watermark mismatches, or prior allow is replayed → deny and report integrity failure.
10. Builder tries to write/delete the ledger → deny.
11. Grant revoked but client caches prior allow → `GRANT_REVOKED`; no content/effect delivered.
12. Host clock rolls backwards by 24 hours → authoritative expiry still denies.
13. Session closes, loses liveness or grant is reused by a new session → `SESSION_NOT_LIVE`; deny.
14. Declared work area resolves outside candidate root → grant issuance denied.
15. Operational block is present and independent release cannot be verified → `BLOCK_RELEASE_UNSUPPORTED`.
16. Authority/issuer cannot be verified → `AUTHORITY_UNAVAILABLE`; no grant, no implementation.
17. Any field in M1 says the builder grant establishes a supported reader route → contract state is rejected as inconsistent.
18. Missing/ambiguous pre-effect reservation, signer, root or policy → fail closed; no successful receipt is claimed.

## 10. Review gate and next actor

This successor is a documentary revision of the requirements, not implementation and not proof that the previously named mechanisms exist. The five HIGH findings are handled by normative requirements plus explicit non-implementability dispositions: BA-01, BA-03, BA-04 and BA-06 cannot be implemented from current evidence; BA-05 is `AUTHORITY_UNAVAILABLE` until a trusted existing authority is verified. BA-02 is a state-label repair; BA-07 and BA-08 are normative scope/session provisions.

Do not repeat the independent review until this successor can be supplied inline to the same existing OpenCode session. A follow-up verdict must assess whether this successor accurately closes the textual gaps while preserving the non-implementability conditions; it must not imply the underlying controls now exist. If a review input is missing, return `REVIEW_BLOCKED_INPUT_UNAVAILABLE` and stop.

```
SUCCESSOR_DRAFT=READY_FOR_DOCUMENTARY_REVIEW_ONLY
READY_FOR_IMPLEMENTATION=NO
M1=OPEN
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```
