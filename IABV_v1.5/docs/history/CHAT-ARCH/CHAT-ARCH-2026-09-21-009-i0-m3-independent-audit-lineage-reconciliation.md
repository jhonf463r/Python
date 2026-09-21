# IABV v1.5 — I0 M3 INDEPENDENT AUDIT / LINEAGE RECONCILIATION
## Canonical source record — 2026-09-21

## 1. SOURCE

Source: user-supplied independent Claude/Sonnet audit of I0 M3 commit `7753ce5632370b2a03726aeff63dbcd1ac7afc42`, followed by direct GitHub reconciliation in ChatGPT.

This record separates:
- what the independent auditor reports as executed;
- what GitHub directly verifies;
- what remains only reported;
- what the audit discovered about ancestry and baseline drift.

## 2. M3 INDEPENDENT AUDIT RESULT

Claude reports a clean detached worktree checkout of remote SHA `7753ce5632370b2a03726aeff63dbcd1ac7afc42` and independently reproduced the requested M3 mutation:
`self._headers(effective_key)` → `self._headers()` for GET polling only.

Reported observations:
- POST assertion passes under mutation because POST remains correct;
- GET header becomes `Bearer constructor-key`;
- test fails at the GET assertion line;
- mutation failure is therefore attributed to GET propagation;
- false-positive vectors were checked;
- adapter persistent key remains unchanged after invocation override;
- negative leak test remains scoped to result metadata and persistent adapter state.

Direct GitHub verification confirms the audited SHA and its test diff contain the intended polling/call-args assertions.

Epistemic status:
`M3 = CLOSED AT UNIT/MUTATION LEVEL / INDEPENDENTLY VERIFIED BY AUDITOR REPORT`.

The raw detached-worktree execution and traceback are not separately archived in GitHub by this record, so the execution transcript remains second-order evidence from the independent auditor.

## 3. PROVENANCE / LINEAGE DISCOVERY

The direct parent of `7753ce563...` is:
`6c8be71c7dc2718802c83f79e03f90bedf3e818b`.

The historical commit previously described as the prior correction:
`64260e424b75fc4b0c3677c7a5d85b870ee7cc8c`
is NOT the direct parent.

GitHub compare:
`64260e424... → 7753ce563...`
shows:
- 8 commits ahead;
- 8-commit cumulative change surface;
- production and test files changed between those points, including:
  - `bootstrap.py`
  - `tool_adapters.py`
  - `tool_teach_service.py`
  - `authority_server.py`
  - `credential_registry.py`
  - multiple I0 tests including canonical composition/discovery/real execution/tool-teach tests
  - `test_i0_credential_seam.py`.

Therefore the claim:
`production seam unchanged since 64260e424`
is not literally valid for the cumulative branch lineage.

A narrower claim is valid:
`7753ce563` itself modifies only `tests/test_i0_credential_seam.py` relative to its direct parent `6c8be71c...`.

At direct source read-back, `credential_registry.py` at `7753...` also contains `resolve_credential_secret(credential_id)`, while the same file at `64260...` did not. This confirms that production-side evolution occurred in the intervening ancestry.

## 4. CORRECT INTERPRETATION

Do NOT downgrade M3 itself merely because the branch contains intervening production changes.

The strongest supported claim is:
`At the exact audited revision 7753ce563..., the per-invocation GET test is causally mutation-sensitive and was independently reproduced according to the audit report.`

Do NOT generalize backward to:
`the same proof applies unchanged to the 64260e424 production state`
unless that cross-revision invariance is separately established.

Do NOT treat the commit message phrase `Production source unchanged` as a statement about the entire ancestry. It is accurate only as a parent-relative diff statement for `7753...` vs `6c8...`.

## 5. NEW REUSABLE GIT / EPISTEMIC INVARIANT

`commit-local diff scope != cumulative branch lineage scope`.

Also preserve:
`direct parent != named historical baseline`
and:
`commit message claim != ancestry-wide invariant`.

For any material evidence claim, reconcile both:
1. immediate diff: `parent → head`;
2. cumulative lineage: `named baseline → head`.

When they differ materially, the claim must state which scope it covers.

## 6. I0 STATUS

M3:
`UNIT/MUTATION CLOSED`
`INDEPENDENT AUDIT REPORTED/REPRODUCED`
`REMOTE ARTIFACT VERIFIED`.

Next open edge:
`real Windows runtime credential binding / execution`.

But the runtime experiment must use an explicitly pinned implementation revision and must not silently assume the historical `64260...` baseline.

Current I0 full closure:
`NOT PROVEN`.

## 7. SYMBIOSIS / LEARNING LESSON

This audit is a stronger example of symbiotic verification because the external auditor did not merely agree with the implementer; it independently:
- reconstructed the source;
- checked the call path;
- introduced the discriminating mutation;
- observed the exact failure;
- checked false-positive vectors;
- surfaced a previously unstated lineage contradiction.

The durable knowledge is therefore not "Claude agreed"; it is:
`independent challenge → causal reproduction → provenance refinement → narrower claim`.

This is a measurable `ΔK` and `Δπ`, but not yet evidence of IABV changing a future decision because of the knowledge.

## 8. NEXT ACTION

Before real Windows execution:
`pin exact implementation revision → secure credential availability → execute real path → preserve raw non-secret artifact → independent runtime audit`.

Do not reopen M3 unless contradictory evidence appears.
