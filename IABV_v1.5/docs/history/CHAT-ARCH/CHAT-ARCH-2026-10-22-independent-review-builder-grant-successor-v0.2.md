# Independent documentary review — builder-grant successor v0.2

- **Date:** 2026-10-22, America/Bogota.
- **Provenance:** review result pasted by the Owner, attributed to the existing independent OpenCode session.
- **Evidence classification:** `OWNER_SUPPLIED_INDEPENDENT_REVIEW`. The review text is preserved as received; reviewer identity/actions are not independently instrument-verified by this coordinator.
- **Review basis:** supplied inline successor v0.2 only.
- **Execution:** none reported. No URL recovery, alternate reader, local checkout, commands, tests, builds, probes, processes, or transport; no implementation.

## Verdict and interpretation

```
REVIEW_VERDICT=PASS_WITH_REPAIRS
VERDICT_MEANING=SUCCESSOR_CLOSES_PRIOR_FINDINGS_AS_DOCUMENTARY_REQUIREMENTS_NOT_RUNTIME_PROOF
READY_FOR_IMPLEMENTATION=NO
NEXT_SUCCESSOR=v0.3_DOCUMENTARY_ONLY
SUCCESSOR_REVIEW=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

The review confirms that the successor v0.2 closes the five prior HIGH findings at the textual requirements level or declares the underlying mechanisms not implementable with current evidence. That prevents the predecessor's explicit FAIL condition from firing. It does not establish any runtime mechanism or authorize implementation.

## Adjudication of BA-01–BA-08

| ID | Status in v0.2 | Review adjudication |
|---|---|---|
| BA-01 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | **Closed textually.** §2 names TOCTOU, symlinks, junctions/reparse points, hard links, aliases, alternate checkouts and root substitution; requires post-open verification; denylist is secondary; fail closed if object identity cannot be established. |
| BA-02 | `TEXTUAL_BOUNDARY_PRESERVED_LABELING_REPAIR_REQUIRED` | **Closed in substance.** §0, §3 and acceptance case 17 preserve the M1 boundary. Residual state-label ambiguity becomes R-03. |
| BA-03 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | **Closed textually.** Mediated file API; no shell; separate test/build grants bound to payload/configuration hashes; execution-time recheck; enforcer-built isolated environment; self-authored command string is not approval. |
| BA-04 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | **Closed textually.** Independent custody, signatures, append-only, hash chain, monotonic sequence/watermark, pre-effect durable intent and indeterminate state after close-record failure. |
| BA-05 | `AUTHORITY_UNAVAILABLE` | **Closed as a hard stop.** Denies issuance and forbids provisional issuer, permissive stub or invented API; does not claim global impossibility. |
| BA-06 | `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE` | **Closed textually.** Issuer-authoritative time, bounded and recorded revocation freshness, expiry semantics and in-flight write handling. |
| BA-07 | `PROPOSED_SCOPE_INTERSECTION_NOT_IMPLEMENTED` | **Closed as a requirement.** Effective scope is candidate root intersected with relative work areas; out-of-root targets rejected. |
| BA-08 | `PROPOSED_SESSION_BINDING_NOT_IMPLEMENTED` | **Closed as a requirement.** Live-session binding, invalidation at closure and rejection of replay in a new process/session. |

## New repairs R-01–R-04

### R-01 — HIGH — Unassigned authority for indeterminate-operation reconciliation

**Clauses:** §5 (indeterminate state, suspended access until reconciliation) and §8 (capability inventory).

**Failure scenario:** a completion receipt fails after an effect. The state becomes indeterminate and access suspends, but no authority is assigned to reconcile it. Letting the builder close the state would create an unowned privileged act and contradict BA-05.

**Required repair:** enumerate an independent indeterminate-operation reconciliation authority in §1 and §8 as `UNRESOLVED`; until a verified holder exists, indeterminate state remains denied indefinitely. The constructor, enforcer, reader and IABV cannot reconcile it. Reconciliation cannot emit a retroactive success receipt.

**Non-executed acceptance:** ledger failure after effect → next operation returns `INDETERMINATE_DENY`; builder closure attempt is denied; resolution without an authenticated holder is denied and leaves state unchanged.

### R-02 — MEDIUM — Undefined link-count and handle-containment rules

**Clauses:** §2 (“link count exceeding the approved invariant”; handle identity and containment after open).

**Failure scenario:** “approved invariant” is undefined, permitting inconsistent implementations. “Containment after open” does not fix whether the proof is handle-derived or path-derived.

**Required repair:** specify `link_count == 1` (unless a separate justified platform exception is explicitly approved) and verify containment from the opened handle/object, e.g. final handle-derived path with volume identity or an opened-parent chain, not solely from a previously stored path.

**Non-executed acceptance:** internal file with link_count 2 is rejected; a handle resolving outside the candidate root is rejected even when the requested pathname looked internal.

### R-03 — LOW — Ambiguous BA-02 state label

**Clause:** §3 `BA02_STATUS=TEXTUAL_BOUNDARY_PRESERVED_LABELING_REPAIR_REQUIRED`.

**Failure scenario:** a reader can interpret it as both closed and pending.

**Required repair:** replace with the single-meaning token `TEXTUAL_BOUNDARY_PRESERVED_AND_ENFORCED_BY_LABEL_RULE`.

**Non-executed acceptance:** the status token conveys no simultaneous closure/pending meanings.

### R-04 — LOW — Enforcer-mode token presupposes an unverified component

**Clauses:** §1 `ENFORCER_MODE=DENY_ALL_PRIVILEGED_OPERATIONS`; §8 says no independent enforcer has been established.

**Failure scenario:** the token can be quoted as if an enforcer operationally exists.

**Required repair:** label it as the required mode of any future enforcer; absent a verified enforcer, state that no privileged operation route is available.

**Non-executed acceptance:** the state never implies an enforcer exists.

## Required reading of the verdict

`PASS_WITH_REPAIRS` means v0.2 closes the prior five HIGH findings textually and declares each unverified mechanism non-implementable on current evidence, without inventing an issuer, API, operator or permission, and without claiming global impossibility. It does not mean controls exist or the contract is ready as a complete baseline. R-01 must be repaired before the successor baseline is treated as closed.

The review makes no runtime claim. All `NOT_IMPLEMENTABLE_WITH_CURRENT_EVIDENCE`, `AUTHORITY_UNAVAILABLE` and `PROPOSED_*` states are documentary dispositions rather than observed runtime facts. The verdict authorizes no implementation.

```
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```
