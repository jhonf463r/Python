# CHAT-ARCH-2026-10-13-276 — M0B-R8.1-C3 adjudication and amendment 274.2

- Episode: CHAT-ARCH-2026-10-13-276
- Date: 2026-10-13 (America/Bogota)
- Input: Owner-supplied Sonnet/Claude C3 report, verdict `PASS_WITH_REPAIRS`
- Prior canonical contract: Entry 274 plus Entry 275
- Status: `M0B_R8_1_AMENDMENT_274_2_PROPOSED_PENDING_TARGETED_REVIEW`
- Operational posture: `KEEP_BLOCKED`

## 0. Effective grammar and Entry 275 integrity status

The current path for Entry 275 is now a short supersession/provenance notice, not a full-text restoration. The clean historical body remains retrievable at commit `1e644ee663118b6567018cd2211c107e48489d4c`, blob `0945248916fa4f83cc0e7d9d354e39fe3720bb5a`. The corrupted blob is retained only in Git history. The effective review inputs are the clean historical Entry 275 body, Entry 274 and this amendment; do not cite the corrupted blob as valid contract text.

**Proposed v1 path grammar (full-string match):** accept only slash-separated relative paths, with no leading slash and no backslash in caller input. Each component MUST match `^[A-Za-z0-9][A-Za-z0-9._ -]{0,126}[A-Za-z0-9_-]$`, or be one alphanumeric character. Total path length is at most 240 ASCII characters and nesting is at most 16 components. Before any filesystem lookup, reject colon/ADS, wildcards, traversal, trailing dot/space, any `~` short-name pattern, controls, non-ASCII/Unicode (including bidi/confusables), absolute/UNC/device paths and reserved Windows device basenames case-insensitively (`CON`, `PRN`, `AUX`, `NUL`, `CONIN$`, `CONOUT$`, `CLOCK$`, `COM1`–`COM9`, `LPT1`–`LPT9`, including when followed by an extension). Unsupported input returns `PATH_FORM_UNSUPPORTED`. Expanding the grammar requires a separately reviewed contract change.

For directory listings, count actual raw entries, excluding only exact structural pseudo-names `.` and `..` if a platform returns them. The 201st actual entry denies the entire listing. Any invalid, sensitive, reparse/link or unsupported entry denies the whole listing; do not silently omit entries or disclose partial names. Require a stable enumeration view; if concurrent mutation cannot be excluded or detected reliably, discard and deny.

To prevent recurrence of the Entry 275 edit defect, do not use replacement-string interpolation when inserted text contains a dollar sign directly before a Markdown backtick. Use a callback/literal-safe edit and verify the written blob: exactly one header, complete regex and reserved names, and expected section count.

## 1. Integrity incident and source provenance — C3-01

C3 identified that the current `main` copy of Entry 275 became corrupted in the path-grammar section: five copies of the preamble appear at offsets reported by the reviewer; the regex and reserved-name tokens were truncated. This is not a design counterexample; it is a documentation-integrity failure in the canonical artifact.

The cause is consistent with a JavaScript replacement-string hazard: in a replacement string, the sequence `$\u0060` (dollar followed by backtick) expands to the prefix preceding the matched text. The attempted grammar edit included regex/device names ending with a dollar sign immediately before Markdown backticks, so the replacement inserted previous document content. This is the likely cause, not a runtime-code finding.

The original clean blob is still retrievable at historical commit `1e644ee663118b6567018cd2211c107e48489d4c`, blob `0945248916fa4f83cc0e7d9d354e39fe3720bb5a` (35,546 characters, one header). The corrupted current blob is `3106d55393e0a4f3f4488decfff94ef6071c47d1` (94,436 characters, five headers). The historical clean blob predates the intended restrictive grammar update, so it must be restored to a separate recovery artifact and then amended with a safe full-match grammar. Do not cite the corrupted current blob as a valid contract.

The full recovery-copy write was blocked. Subsequently, the current Entry 275 path was changed to a short supersession/provenance notice pointing to the clean historical blob and Entry 276. This contains the corrupted current text but is not a byte-for-byte restoration of the contract. The full clean body remains available in immutable history; this Entry 276 supplies the proposed path-grammar replacement.

## 2. Consolidated amendment 274.2 — C3-02 through C3-11

The following rules are proposed as one amendment to Entry 274/275. Where they conflict with Entries 274 or 275, these rules take precedence. They are contract requirements, not claims about an implementation.

### C3-02 — trusted Owner enrollment

The Owner's user-verification credential and verification root must be enrolled outside requester control, in a protected trust store the requesting agent cannot write or replace. A well-formed attestation from an unregistered credential is rejected with `APPROVAL_CHANNEL_UNTRUSTED`. If the supported platform cannot isolate enrollment and user verification from arbitrary same-user requester code, v1 does not issue a read decision.

### C3-03 — rollback protection for registrations and block state

The anti-rollback boundary covers the checkout/workspace registry and lifecycle lineage, deletion tombstones, active-block set, and version of the authoritative scope model—not only the read-decision ledger. They share a protected monotonic epoch/anchor recorded in each issuance and operation intent and checked before every operation. Rollback, missing lineage or stale block state denies with `REGISTRY_ROLLBACK` or `BLOCK_SCOPE_UNEVALUABLE`. Registration and tombstone mutation must be authority-controlled and outside requester write access.

### C3-04 — pre-approval oracle prevention

A syntactically valid request receives the same external status, `APPROVAL_PENDING`, independent of whether the path exists or its size. The trusted approval surface resolves the target through the same contained, metadata-only resolver used by the reader. Sensitive-path denials are applied before target lookup. A caller-facing error after an untrusted component must not reveal existence, type or size. Detailed protected audit evidence may be retained server-side. Timing equivalence is a target-platform requirement to validate, not claimed proven.

### C3-05 and C3-06 — handoff states and idempotency

The audit state machine distinguishes `INTENT_COMMITTED`, `CONTENT_STAGED`, `RELEASE_AUTHORIZED`, `HANDOFF_RETURNED`, `DELIVERED` only where a trustworthy transport acknowledgement exists, `DISCARDED` and `UNRESOLVED`. `HANDOFF_RETURNED` means the local handoff call returned; it does not claim the recipient received the data. On recovery, `RELEASE_AUTHORIZED` without a handoff-returned or discarded state is unresolved and blocks new reads until durable Owner/governance reconciliation. No exactly-once delivery claim is allowed without transport evidence.

The requester may supply a non-authoritative `client_request_token` only as an idempotency lookup key, scoped to authenticated agent + session + canonical scope digest. Reusing it with different scope is denied and audited. The issuer-generated nonce is consumed atomically with decision creation; retry after a lost reply returns the same committed decision/state, never a new budget. The caller token is not authority.

### C3-07 — server-controlled destination and agent identity

The destination/provider is read from a protected server configuration store, and its identity/digest is included in the approved scope. The UI labels it as the intended recipient and clearly states that downstream copying/retransmission after content is handed to the requester is not controlled by this contract. Decisions bind to an authenticated agent principal/session that cannot be redeemed by another local process merely by copying a bearer token. If the connection multiplexes agents and the reader cannot distinguish them, v1 rejects it.

### C3-08 — clock and suspension

Expiry uses trusted server time plus a monotonic elapsed-time source whose semantics include system suspend, as proven for the target platform. If the clock jumps, suspend semantics are unknown, or monotonic/wall-clock observations disagree beyond the defined tolerance, all active decisions and pending nonces expire; fail closed. No active decision survives process/host restart.

### C3-09 — raw listing semantics

Directory entries named exactly `.` and `..`, if the platform emits them, are excluded from the raw-entry count as structural pseudo-entries before applying the 200-entry ceiling. Every actual filesystem entry counts before filtering. The 201st actual entry denies the entire listing; any invalid/sensitive/reparse/unsupported entry among an in-limit listing also denies the whole listing, with no silent omission or partial names.

### C3-10 — deterministic block verdict precedence

For each request, evaluate all blocks using the authoritative scope model and record each block ID, immutable revision/digest, scope, result and model version. If any required scope/identity evidence is unavailable or inconsistent, return `BLOCK_SCOPE_UNEVALUABLE` (this code dominates a simultaneous applicable-block result). Otherwise, if one or more blocks are applicable and any lacks a valid independent governance-owned release, return `BLOCK_RELEASE_UNSUPPORTED`. A block is non-applicable only when every dimension that block actually references is evaluated from trusted current and historical identity evidence and the model proves a mismatch. A new registration ID alone is insufficient. Every applicable block must have its own valid release.

### C3-11 — one authoritative conformance suite

The effective test specification is the union of Entry 274 and Entry 275, with this amendment's rules taking precedence. Give each case one globally unique ID; remove duplicate/contradictory IDs when publishing the consolidated matrix. The Entry 275 matrix must replace—not merely append to—the earlier Entry 274 matrix. A report with duplicate IDs, unspecified expected outcomes or no positive cases fails schema validation.

Add mandatory discriminating cases: unregistered Owner credential; registry/tombstone rollback; path-existence side channel across existing, missing and sensitive paths; unresolved handoff after crashes at each state boundary; retry after lost issuance response; copied session token; clock jump/suspend; 200 actual entries plus structural pseudo-entries versus 201 actual entries; simultaneous applicable and unevaluable blocks; and explicit regression cases for sensitive-path denial, non-allowlisted file, unapproved listing and diagnostic-only zero-file-read behavior. Preserve positive-path and exact-boundary cases so a deny-all implementation cannot pass.

## 3. Operational rule

The read decision never releases its own governance block. If any applicable block exists without an independently supported governance-owned release, return terminal `BLOCK_RELEASE_UNSUPPORTED`. If block scope cannot be evaluated, return `BLOCK_SCOPE_UNEVALUABLE`. This contract cannot unlock M0A.

No code has been inspected or modified in this episode. The C3 report also states it did not read code. OS behavior, credential enrollment, ledger integrity, rollback protection, target identity, revocation, actual block scope and any implementation remain `UNPROVEN`.

## 4. Next actor

**Next actor: Sonnet/Claude**, one targeted review of the clean historical Entry 275 body (commit `1e644ee663118b6567018cd2211c107e48489d4c`) plus Entry 274 and this Entry 276. Do not use the superseded current Entry 275 notice as the contract text and do not perform a broad audit. Challenge the grammar in Section 0 and whether C3-02 through C3-11 close the reported cases.

Current posture remains `KEEP_BLOCKED`. No implementation, testing/runtime, local M0A read, reader retry/bypass, credential inspection or launch is authorized.
