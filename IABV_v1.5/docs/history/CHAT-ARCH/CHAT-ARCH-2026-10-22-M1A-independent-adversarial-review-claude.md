# M1A — Independent adversarial review of the Codex scope-model proposal

- Episode: `M1A_INDEPENDENT_ADVERSARIAL_REVIEW_OF_SCOPE_MODEL`
- Date reported: 2026-10-22, America/Bogota
- Reviewer/model: Claude / Sonnet 4.6, **Owner-supplied report; actual model invocation is not independently verified by this coordinator**
- Reference HEAD reported by the reviewer: `jhonf463r/Python @ 0ec95b487deb4d74ab286d40ed7ef0da6a7568ba`
- Proposal: [M1A Codex scope-model proposal](./CHAT-ARCH-2026-10-22-M1A-Codex-scope-model-proposal.md), blob `b30b9167302c3ad35ec09e9097a6062545a96ad4`
- Review instructions: [M1A independent adversarial-review handoff](./CHAT-ARCH-2026-10-22-M1A-independent-adversarial-review-handoff.md), blob `70c5637ccc145d96ba25dd8b238445507733ae8a`
- Normative contract: [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), blob `5943a87d907436fc7ecac31534cbfcd31fe7de55`

## 1. Provenance and verdict

The Owner pasted the review report into the coordination chat. Its statements about documents opened, reference HEAD, and Claude/Sonnet execution are recorded as `OWNER_REPORTED` unless independently checked below. This coordinator directly re-fetched the canonical proposal, review handoff, current-state route, and Entry 274 from public GitHub. This does not authenticate the reviewer's actual execution environment.

```text
INDEPENDENT_REVIEW_VERDICT=PASS_WITH_REPAIRS (OWNER_SUPPLIED REPORT)
DESIGN_STATUS=PROPOSED; NOT AUTHORITATIVE
CRITICAL_FINDINGS=3 (F-M1A-01..F-M1A-03)
ADDITIONAL_FINDINGS=4 (F-M1A-04..F-M1A-07)
OWNER_DECISIONS=OPEN; count requires reconciliation, see section 4
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_CHECKOUT_ACCESSED=NO (per supplied report; not independently verified)
BRIDGE=BRIDGE_NOT_READY
```

The report accepts the proposal's conservative architecture as a useful starting point but does not approve it as policy. It identifies three high-severity defects, four medium/low findings, and several bypass vectors.

## 2. High-severity findings

### F-M1A-01 — Selector semantics not defined normatively

**Affected:** proposal §A and §D; review handoff questions 1–3.

The table classifies “both valid exact selectors differ from the target” as `PROVEN_NOT_APPLICABLE`, but “one dimension differs while the other matches” as `BLOCK_SCOPE_UNEVALUABLE`. It does not define “consistent” or specify the missing case in which one selector is `GLOBAL` and the other valid exact selector mismatches.

A selector policy must explicitly define whether the two dimensions are conjunctive, alternatives, or governed by a conflict-aware rule, and must define how consistency is established by a trusted resolver rather than asserted by a producer. The choice for `GLOBAL` plus exact mismatch is a policy decision; it must not be silently inferred.

**Repair proposed by reviewer:** define the semantics and “consistent”; add an explicit decision-table row for `GLOBAL` plus exact mismatch. Owner/governance adjudication is required for the policy choice.

### F-M1A-02 — Incomplete decision table

**Affected:** proposal §D; review handoff §2.

Four gaps were identified:

1. One selector is `GLOBAL`, while the exact selector is valid but mismatches the resolved target.
2. One dimension is absent from the record entirely, rather than present but empty.
3. Catalogue aliases cannot be resolved uniquely, including conflicting canonical IDs across versions.
4. Multiple active blocks carry incompatible or different `policy_version` values.

**Repair proposed by reviewer:** absent selector → `BLOCK_SCOPE_UNEVALUABLE`; ambiguous alias → a fail-closed model/scope outcome; each block must be evaluated under its declared supported policy version, while an unsupported version must produce `SCOPE_VERSION_UNSUPPORTED`. The exact output-code mapping still needs to be made internally consistent and normative.

### F-M1A-03 — Catalogue and producer trust chain undefined

**Affected:** proposal §§A–C, §G items 1–3 and 6; Entry 274 §7.

The proposal names a catalogue digest, version, and `producer_id`, but does not define a verifiable trust root, who publishes/signs the catalogue, how the evaluator validates the signature or equivalent, how previously trusted catalogue versions are revoked, or how a producer is authorized to emit a given block type. A hash of attacker-controlled content does not authenticate its source.

**Threat example:** a producer invents an official-sounding ID, creates its own catalogue and digest, and submits a global block. Digest equality alone cannot distinguish this from an authorized catalogue.

**Repair proposed by reviewer:** make a verifiable trust chain an explicit prerequisite; define producer authorization and revocation; state that no block becomes authoritative without those checks. The trust root, authorized issuers, and revocation mechanism remain Owner/governance decisions. Until the model is adjudicated and the trust chain established, the proposal remains non-authoritative and the existing denial remains in force.

## 3. Additional findings and bypass vectors

### F-M1A-04 — `BlockEvaluation` must never be bearer authority (MEDIUM)

Entry 274 §2 defines an operation receipt as evidence, never authority; §§5 and 7 require server-side decision custody and independent block-release authority. The proposal should state explicitly that a `BlockEvaluation` is diagnostic, is not a transferable bearer object, cannot be redeemed downstream as permission, and cannot be reused instead of a fresh authoritative server-side evaluation. This is a clarification consistent with Entry 274, not a new policy grant.

### F-M1A-05 — Legacy-record parsing and coexistence ambiguous (MEDIUM)

The proposal says free-form legacy records are not automatically valid under the new model, but also says to preserve legacy records as blocking. It does not distinguish a record that cannot be deserialized as `OperationalBlockV1` (for example, no recognized `schema_id`) from a recognized record whose required selector field is absent, empty, or unregistered.

Reviewer-proposed distinction: unrecognized/unparseable schema → `SCOPE_MODEL_UNAVAILABLE`; recognized schema with absent/empty/unregistered selector → `BLOCK_SCOPE_UNEVALUABLE`. Do not reinterpret empty string, `None`, or wildcard as `GLOBAL`; no automatic migration.

### F-M1A-06 — Synthetic conformance matrix misses critical cross-products (MEDIUM)

The proposed future test inventory should add, without running any tests in this task:

- Unknown target plus assistant mismatch, in both evaluation orders; outcome must not depend on ordering.
- A producer emitting a selector ID not present in the catalogue; document the exact fail-closed outcome.
- A block declaring a catalogue/schema version newer than the evaluator's loaded version; expected result `SCOPE_VERSION_UNSUPPORTED`.
- Cross-product cases for missing dimensions, alias conflict, different policy versions, client scope versus server-resolved target, and multiple active blocks including one unevaluable block.

Tests remain merely proposed and are not authorized or executed by this review.

### F-M1A-07 — Acceptance criterion depends on unresolved trust decisions (LOW)

The proposal's catalogue-authority acceptance criterion cannot be satisfied until the Owner/governance resolves the existing catalogue ownership, identity, resolver, and versioning/revocation decisions (proposal §G items 1, 2, 3, and 6). Record this dependency as a gate before any implementation authorization.

### Vector 1 — Attacker-controlled catalogue digest

Covered by F-M1A-03. A digest proves equality to some bytes, not that those bytes came from an authorized publisher.

### Vector 2 — Caller-supplied `operation_scope` influences evaluation

The proposal says caller arguments must not choose or override the target, but should state unambiguously that the evaluator derives the target only from a trusted server-side operation/target registry. A caller-supplied value is ignored for the authoritative decision; optional anomaly comparison must not influence that decision.

### Vector 3 — Legacy empty field interpreted as global

Covered by F-M1A-05. Empty/wildcard/absent legacy metadata must never silently acquire global semantics during coexistence or migration.

### Vector 4 — Short-circuit while evaluating multiple active blocks

The proposal says to evaluate all blocks but does not explicitly prohibit returning early after a non-applicability result. State that the full set of active blocks must be accounted for before a final decision; no block may be skipped due to ordering. A positive applicable result may already imply denial, but skipping remaining blocks would lose diagnostic completeness and could become dangerous if outcome aggregation changes.

## 4. Coordinator reconciliation: important internal inconsistency in the supplied review

The report's body and its final count do not agree:

- The report explicitly says no Owner decision is required to clarify caller-supplied `operation_scope` (Vector 2) and to prohibit short-circuit evaluation (Vector 4).
- F-M1A-04, F-M1A-05, and F-M1A-06 are presented as documentary/technical clarifications consistent with existing conservative intent.
- F-M1A-07 points to dependency on already-open decisions in proposal §G, rather than clearly defining a new independent policy choice.
- Yet the report's final posture says that four additional `OWNER_DECISION_REQUIRED` items include “caller-scope clarified” and “short-circuit prohibited.”

Therefore, **do not record “7 existing + 4 new = 11 Owner decisions” as a verified tally**. Normalize the ledger by decision type:
1. **Clearly requires Owner/governance adjudication:** the `GLOBAL` + exact-mismatch semantics (F-M1A-01/F-M1A-02).
2. **Already open in proposal §G and implicated by F-M1A-03/F-M1A-07:** catalogue owner and authorized publisher/principal, trusted resolver/operation registry, independent block-release authority, catalogue lifecycle/versioning/revocation, and legacy treatment.
3. **Proposed design repairs that appear derivable from the existing fail-closed/Entry 274 requirements, but must still be reviewed in a revised proposal:** explicit missing-field and alias-conflict outcomes, non-bearer diagnostic receipts, caller-supplied scope ignored for authority, complete multi-block evaluation, and added synthetic test cases.
4. **Not settled by this report:** exact result-code precedence when one active block applies and another is unevaluable, and whether a catalogue trust-chain failure maps to `SCOPE_MODEL_UNAVAILABLE`, `BLOCK_SCOPE_UNEVALUABLE`, or a separately approved status. Avoid inventing that semantic mapping.

A second related precision issue: “conjunctive” alone does not automatically justify `BLOCK_SCOPE_UNEVALUABLE` for every one-dimension mismatch. Under ordinary conjunction, a trusted and well-formed exact mismatch may mean the intersection is empty; the proposal intentionally treats some partial mismatch combinations as unevaluable. The revised design must distinguish a valid non-match from inconsistent/untrusted metadata and obtain Owner/governance approval for the selected rule. Until then, neither `PROVEN_NOT_APPLICABLE` nor any other proposed result authorizes an operation.

## 5. Coherence with Entry 274

The review confirms these existing normative constraints:

- Entry 274 §2: diagnostic, fresh approval, read decision, reader verifier, and durable operation ledger/receipt are separate authorities; a receipt is evidence, never authority.
- Entry 274 §5: the read decision is a server-side ledger record, not a transferable bearer object.
- Entry 274 §7: a repository-read decision cannot release a governance block; without separately verified independent release authority, deny with `BLOCK_RELEASE_UNSUPPORTED`.
- Scope applicability requires an authoritative, versioned scope vocabulary and explicit combination semantics; unknown, malformed, unsupported, incomplete, or conflicting scope must fail closed.

These are documentary requirements. They do not prove that any corresponding implementation exists.

## 6. Evidence classification and source boundary

Reviewer-reported source list:

- M1A proposal, blob prefix `b30b9167`: `HEAD_SOURCE` as reported and re-fetched by coordinator.
- M1A handoff, blob prefix `70c5637c`: `HEAD_SOURCE` as reported and re-fetched by coordinator.
- CURRENT-STATE at report's reference, blob prefix `ff33fe1f`: `HEAD_SOURCE` as reported and re-fetched by coordinator.
- Entry 274, blob prefix `5943a87d`: `HEAD_SOURCE` as reported and re-fetched by coordinator.
- Pinned `domain/models.py`, `world_model_service.py`, and `server.py` blobs at base `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`: the report says these were not directly re-inspected in that reviewer session. Preserve the prior coordinator's bounded review provenance; do not attribute direct reinspection to this report.

Claims about no catalogue signer/revocation mechanism are findings about the proposal's contents and bounded evidence, not proof that no such mechanism exists anywhere in all possible systems. The review's runtime, implementation, test, local-checkout, SQLite, secret, and transport statuses remain unverified reports; no such activity was authorized by this coordination task.

## 7. Final state and routing

```text
INDEPENDENT_REVIEW_VERDICT=PASS_WITH_REPAIRS (OWNER_SUPPLIED)
CRITICAL_BLOCKERS=F-M1A-01;F-M1A-02;F-M1A-03
SCOPE_MODEL=PROPOSED; NON_AUTHORITATIVE
OWNER_GOVERNANCE_ADJUDICATION=PENDING
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
```

Next routing step: update the canonical decision ledger to record this review and reconcile the existing Owner-decision list. Do not jump to implementation. Prepare a revised **design-only** proposal incorporating the non-policy clarifications and explicitly isolating choices that require Owner/governance adjudication; that revision must be separately authorized as design work before an actor edits the proposal. The Owner can then adjudicate the narrow unresolved policy choices from a clear decision table. Any later implementation requires separate authorization.

No source implementation, tests, build, runtime, MCP call, transport, local checkout read, code commit, merge, or block release follows from this review.
