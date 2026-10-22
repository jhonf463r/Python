# Independent documentary review — governed builder-grant contract

- **Date:** 2026-10-22, America/Bogota.
- **Provenance:** review result pasted by the Owner, attributed to the independent OpenCode review of the self-contained inline packet.
- **Evidence classification:** `OWNER_SUPPLIED_INDEPENDENT_REVIEW`. The review's text is preserved; reviewer-session identity and its actions are not independently instrument-verified by this coordinator.
- **Scope:** documentary contract only. No local checkout, alternate reader, URL retrieval, commands, tests, builds, probes, services, repository writes or transport were reported by the reviewer.

## Verdict and interpretation

```
REVIEW_VERDICT=PASS_WITH_REPAIRS
CONTRACT_BASELINE=DEFENSIBLE_REQUIREMENTS_ONLY
READY_FOR_IMPLEMENTATION=NO
OWNER_AUTHORITY_DECISION=PENDING
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

The review explicitly defines PASS_WITH_REPAIRS as approval of a defensible requirements baseline, not implementation approval. Treating it as “implementable with minor repairs” would make the applied verdict FAIL. The five HIGH findings are blocking conditions, not optional improvements. If any remains unaddressed in the successor, the verdict decays to FAIL. The reviewer states that the review must not be repeated until a successor draft resolves or explicitly declares non-implementable the five HIGH findings.

## Evidence classification

| Class | Content |
|---|---|
| Verified in the inline review packet | Only the supplied contract text and its structure |
| OWNER_REPORTED | Attribution to Codex; the 176-tool inventory result; reported input/session circumstances |
| PROPOSED | All grant clauses, capability matrix, exclusions, receipts and acceptance scenarios |
| UNRESOLVED | Issuer, principal identity, root resolver, revocation, independent block-release authority, ledger custody and enforcer existence |
| Not verified by this review | Claims concerning Entry 266, Entry 274, issue #470 and commit `45043acf61871d55822c4a140a8da5ba9c51e043`; these are treated as provenance claims, not as independently checked facts |

## Findings

### BA-01 — Confirmed · HIGH · Physical isolation and filesystem containment

**Clauses:** §2, bullet 4 (filesystem identity vs textual path); §4 closing paragraph (denylisted categories even inside the candidate).

**Scenario:** a disposable clone at `…\\candidate` leaves four gaps: (a) an internal hard link points to an external file; (b) a junction/reparse point is created after root verification; (c) another checkout is accessed without a shared textual prefix; (d) a time-of-check/time-of-use race replaces the target between root verification and open. A category/name denylist does not close these routes.

**Minimum repair proposed by reviewer:** make “disposable and sanitized” a construction invariant, not merely an enforcement rule. Materialize the candidate in a volume/namespace where secrets, user-profile files and live data are unreachable by any path. Record filesystem identity (volume serial + root file ID); open by handle and verify identity after open, not only before; reject entries with link count greater than one and reparse points; make name denylisting explicitly secondary. Name TOCTOU directly in the contract.

**Non-executed acceptance criteria:** internal hard link to external target fails; junction inserted between check and open fails; root renamed/replaced mid-session makes the next operation fail closed and produce a receipt.

### BA-02 — Textual defect refuted · MEDIUM residual · M1 labeling

**Clauses:** contract preamble (“not an available capability or authorization to read the current checkout”), §2 compatibility condition, §5 component table (current local checkout read = `NOT_RUN`).

The contract text does preserve the M1 boundary. This is not a textual defect in the draft. Residual risk: its title and verdict can be quoted out of context as progress on M1.

**Minimum repair:** place the no-M1-implication inside the successor's verdict line and prohibit citing the builder-grant verdict in any M1 state field.

**Non-executed acceptance:** audit the M1 record and confirm the reader contract remains `UNRESOLVED`; no field treats builder-grant design as evidence.

### BA-03 — Partially confirmed · HIGH · Payload and execution boundary

**Clauses:** §3 capability matrix and closing rule (“test/build grants are not inferred”).

The distinction between capabilities is correct at the operation level, but does not bind the payload that an authorized test/build executes. Under a valid pytest grant, constructor-controlled `conftest.py`, `pyproject.toml` backend, git hooks, `.codex/config.toml` or `sitecustomize.py` can read environment secrets and exfiltrate them. A receipt saying “pytest, exit 0” would not prove safety. The contract also does not state whether file read/write is a mediated file API or access through a general process/shell.

**Minimum repair:** (a) serve ordinary development-grant read/write through a mediated file API, never a shell/arbitrary process; (b) bind test/build grants to an approved manifest of entrypoint and auto-loaded configuration hashes, checked again at execution; (c) exclude writes to auto-loaded files and hooks from the ordinary grant; (d) construct test/build environments inside the enforcer with no inherited secrets.

**Non-executed acceptance:** a modified `conftest.py` after approval makes execution reject on hash mismatch; process spawn from the ordinary development grant is rejected.

### BA-04 — Confirmed · HIGH · Independent receipt integrity

**Clause:** §6 (“not depend only on text emitted by the agent”; fail closed when a durable receipt is missing or identity ambiguous).

Open gaps: ledger custody/location is unspecified and the builder could rewrite it if it falls within the candidate; append-only behavior, hash chaining, signature and truncation detection are absent; non-reusable IDs do not stop replay of an old allow decision; no ordering rule requires a durable receipt before the effect, so an operation can happen before persistence failure.

**Minimum repair:** ledger custody outside the candidate and outside builder write scope; append-only records with a hash chain and issuer signature; two-phase operation accounting (durable reservation before effect, closure after); monotonic sequence and signed watermark for truncation/replay detection; deny if the pre-effect durable reservation fails.

**Non-executed acceptance:** stopping the ledger mid-operation denies subsequent operations and prevents content delivery; deleting the last N records is detected as truncation; replay of an old allow is denied due to monotonic sequence; writing the ledger path via ordinary builder grant is denied.

### BA-05 — Confirmed · HIGH · Trusted authority unavailable

**Clauses:** §1 (issuer and block authority unnamed; enforcer/ledger unproven), §7 and open administrative decisions.

Without a trusted issuer, the only apparent “approval” is a conversational instruction, which the contract itself says is insufficient technical identity proof. There is no executable route to a valid grant. Implementing one would require inventing the issuer, contrary to the governance boundary.

**Minimum repair:** an Owner decision is required. The successor must name a real, verifiable principal and authentication mechanism backed by authoritative evidence, or record `AUTHORITY_UNAVAILABLE` and stop. No provisional issuer.

**Non-executed acceptance:** successor identifies a verifiable principal/authentication mechanism or records `AUTHORITY_UNAVAILABLE` without an implementation artifact.

### BA-06 — New · HIGH · Expiry, revocation and in-flight operations

**Clauses:** §2 (“start, expiry and revocation”) and §6 (“validity”).

No authoritative clock, maximum decision age, revocation propagation bound or in-flight operation rule is specified. Expiry and receipt failures occur only in non-normative scenarios, not enforceable contract clauses.

**Scenario:** agent caches a valid-grant decision; the Owner revokes but nothing forces revalidation. Or host time moves backwards and the grant survives expiry.

**Minimum repair:** expiry against issuer-authoritative time rather than host time; bounded and receipted revalidation interval; revocation checked every operation or via a bounded interval with declared maximum staleness; abort and record in-flight writes on expiry.

**Non-executed acceptance:** use a cached grant after revocation → `GRANT_REVOKED`; move local clock back 24 hours → deny without changes.

### BA-07 — New · MEDIUM · Scope intersection

**Clause:** §3, row 1 (“inside the registered candidate and agreed work areas”).

**Scenario:** work areas are undefined and could be interpreted outside the root, conflicting with §2.

**Minimum repair:** scope equals `candidate_root ∩ declared_work_areas`; areas are expressed relative to the candidate. Out-of-root areas are rejected at issuance.

**Non-executed acceptance:** a grant naming an out-of-root area is rejected.

### BA-08 — New · MEDIUM · Session liveness

**Clause:** §2 (“ordinary authorized operations during the complete session”).

**Scenario:** a long-lived session grant is captured and reused by a new process after its original session ends.

**Minimum repair:** bind grant to a live session with a liveness check; invalidate it at session closure.

**Non-executed acceptance:** reuse after session termination is denied.

## Answers to required adversarial questions

- **Self-grant:** text prohibits it, but it cannot be enforced while principal binding and issuer are unresolved. The reader and running IABV are textually prohibited from releasing their own block; the mechanism remains unresolved.
- **Root substitution:** possible under the supplied contract; hard links and TOCTOU are not closed.
- **Secrets:** not proven absent; §4 is a denylist applied within the candidate.
- **Capability separation:** correct at the operation level, incomplete at payload level; shell/file-write boundary and grant clock/revocation are not specified.
- **Expiry/revocation/ledger:** the missing-receipt fail-closed rule is present, but expiry scenarios are non-normative; pre-effect order, anti-replay and anti-truncation are missing.
- **Independent verification:** receipt fields are listed, but custody, authentication, tamper detection and truncation detection are not specified.
- **M1 misinterpretation:** contract text preserves the boundary, with a residual labeling risk.
- **Minimum coherent implementable slice:** reviewer proposes considering (i) a pinned commit plus sanitized candidate created by an already-existing verified mechanism; (ii) grant schema; (iii) denial mapped to existing `operational_block_active` semantics, without a new API; (iv) receipt schema and verifier. Everything else—issuer, UI, revocation endpoint, release authority—is a named dependency, not something that may be invented. The reviewer mentions a schema plus always-deny enforcer skeleton and receipt verifier, with emission represented by a negative stub; this is a proposal only and is not authorized under the current governance.

## Exit condition

None of the eight findings is resolved by this review. BA-05 requires an Owner/authority decision. BA-01, BA-03, BA-04 and BA-06 require verifiable specification. Do not repeat the review until a successor draft resolves or explicitly declares non-implementable the five HIGH findings.

This verdict does not authorize implementation:

```
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```
