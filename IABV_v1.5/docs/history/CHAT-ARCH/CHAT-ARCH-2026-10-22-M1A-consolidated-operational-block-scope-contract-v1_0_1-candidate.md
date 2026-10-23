# IABV M1A — Consolidated operational-block scope contract v1.0.1 (candidate)

- **Contract ID:** `IABV-OPERATIONAL-BLOCK-SCOPE`
- **Contract version:** `1.0.1`
- **Schema ID:** `iabv.operational_block_scope`
- **Schema version:** `1.0.1`
- **Policy version:** `1.0.1`
- **Catalogue versioning:** independently versioned; each evaluation must bind the exact catalogue revision.
- **Effective design status:** `CANDIDATE_SUCCESSOR_PENDING_TARGETED_REVIEW; NOT_YET_ADOPTED`
- **Predecessor baseline:** v1.0.0, immutable reviewed blob `8181c7c0cf6036c76cf365510e8d9665cf84e57e`; remains the Owner-adopted baseline until this candidate is reviewed and canonically accepted.
- **Candidate scope:** eight finding repairs; selector policy and all seven Owner-adopted decisions remain unchanged.
- **Conformance coverage:** 38 proposed design cases in this candidate; none executed.
- **Owner acceptance receipt:** exact chat response `ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE`, received 2026-10-22 (America/Bogota).
- **Implementation status:** `NOT_IMPLEMENTED`; no source code, runtime, or tests are claimed.
- **Operational posture:** `GOVERNANCE=KEEP_BLOCKED`; `READ_LIST=FAIL_CLOSED`; `IMPLEMENTATION=NOT_AUTHORIZED`; `TESTS=NOT_RUN`; `BRIDGE=BRIDGE_NOT_READY`.
- **Canonical route:** [CURRENT-STATE.md](./CURRENT-STATE.md).
- **Decision ledger:** [M1A normalized scope decision ledger](./CHAT-ARCH-2026-10-22-M1A-normalized-scope-decision-ledger-and-design-amendment.md).

## 1. Purpose, authority and scope

This candidate preserves the M1A design baseline adopted by the Owner's exact acceptance token and proposes minimal completeness/traceability repairs from the targeted review of v1.0.0. It defines how typed assistant and operation/target selectors constrain the applicability of an operational block. It is a documentary successor candidate, not yet adopted as a replacement for v1.0.0, and not evidence that its trust infrastructure or evaluator exists in deployed/local code. It does not reopen or replace the seven adopted design choices. The v1.0.0 baseline remains authoritative until this exact candidate has been independently reviewed and its route updated in CURRENT-STATE.md.

### 1.1 Parent contracts

This child contract is traceable to:
- [UAAL-ROOT-001 — Universal Adaptive Algorithm Constitution](./UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md): objective → perceive/represent/interpret → maintain uncertainty → infer capability → discover realizations → check constraints/access/resources → select → govern → act → observe → verify → update reusable knowledge → reuse/adapt.
- [Entry 274 — consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), especially its separate diagnostic, fresh approval, read decision, reader verifier and operation-ledger/receipt authorities; mandatory fail-closed behavior; trusted server-side target identity; and independent block release.
- [The construction-completeness/traceability overlay](./CHAT-ARCH-2026-10-22-UAAL-construction-completeness-traceability-overlay.md): bidirectional traceability, state-space closure, authority-plane separation, bounded handoff, reconciliation and fetch-back requirements.
- [Central M1A reconciliation](./CHAT-ARCH-2026-10-22-central-space-time-coordinator-m1a-reconciliation.md): historical derivation context only; this link incorporates no additional normative requirements by reference, and the referenced document was outside the five-input v1.0.0 review scope. [The normalized ledger](./CHAT-ARCH-2026-10-22-M1A-normalized-scope-decision-ledger-and-design-amendment.md) records the adopted design decisions.

This contract extends these existing organs. It creates no independent task router, authorization issuer, or block-release path.

### 1.2 Owner-adopted design decisions

The acceptance adopts the seven bundled defaults in the normalized ledger:
- `OG-M1A-01`: conjunctive assistant and target selectors.
- `OG-M1A-02`: accountable catalogue/policy governance ownership.
- `OG-M1A-03`: authenticated, allowlisted producer authority by block class.
- `OG-M1A-04`: Owner/governance-controlled, versioned server-side operation-to-target resolver.
- `OG-M1A-05`: integrity-protected catalogue publication, versioning, revocation and audit lifecycle.
- `OG-M1A-06`: independent block-specific release authority/artifact.
- `OG-M1A-07`: no automatic legacy migration; legacy blocks remain blocking.

Acceptance establishes the intended design policy, but it does **not** identify or prove the real authenticated runtime principal, cryptographic trust root, producer credentials, resolver call-site mappings, catalogue publisher, revocation service or independent release mechanism. Those remain implementation prerequisites. No implementation permission is granted by this contract.

## 2. Normative vocabulary and data model

The terms **MUST**, **MUST NOT**, **SHOULD** and **MAY** express requirements of this candidate design text. They do not imply implementation or operational authorization.

A conforming implementation shall represent the two selector dimensions as typed, independent fields; it must not encode them only as ambiguous free-form strings. Conceptual selector form:

- `GLOBAL`: matches every valid value in that selector's own dimension only.
- `EXACT(canonical_id)`: matches only a trusted, canonical, registered ID for that dimension.
- No missing, empty, wildcard-like, alias-only or unrecognized value is implicitly equivalent to `GLOBAL`, `NONE` or `EXACT`.

Every per-block evaluation and overall request evaluation must bind, at minimum:
- immutable block ID and revision/content digest;
- a reference to the authenticated, complete active-block-set snapshot/attestation used for the decision, including its catalogue revision/digest, scope, epoch/sequence, time/freshness and revocation evidence;
- `pre_selector_validation_status` with exactly one of `PASSED`, `FAILED`, or `UNKNOWN`, plus the result and evidence reference for each mandatory pre-selector check;
- schema ID/version, policy version and exact catalogue revision;
- authenticated producer principal/reference and authorized producer class;
- typed assistant selector and typed target selector;
- trusted resolved assistant ID and canonical target-scope ID (including resolver/catalogue revision);
- provenance/integrity/authorization evidence references, including stage-level evidence for every mandatory pre-selector check;
- evaluation result, all reason codes and relevant timestamps;
- independent block-release artifact reference, if one exists and verifies.

The conceptual model ID is `iabv.operational_block_scope`; schema and policy version `1.0.1` are **proposed for this non-adopted successor candidate only**. They do not assert that a live catalogue carrying those versions has been published or authenticated, or that v1.0.1 has superseded the Owner-adopted v1.0.0 baseline. Catalogue revision, publisher signature/attestation, trust anchor and revocation state must be separate explicit evidence.

## 3. Selector semantics

### 3.1 Matching rule

**Mandatory pre-selector validation gate.** Selector predicates are not eligible to establish non-applicability until the evaluator has authenticated the complete active-block-set snapshot and all mandatory per-block preconditions have passed: block metadata and required fields; schema/policy/catalogue version support; catalogue publisher/trust-root, integrity and revocation state; producer principal authentication and authorization for the block class; and trusted assistant plus server-resolved target identity/implementation binding. The per-block record MUST set `pre_selector_validation_status=PASSED` only if each required check is explicitly `PASSED` with its evidence reference.

If any mandatory check is `FAILED`, `UNKNOWN`, missing, stale, conflicting, revoked or lacks required evidence, the per-block record MUST have status `FAILED` or `UNKNOWN`, preserve every applicable denial reason, and MUST NOT emit `PROVEN_NOT_APPLICABLE`. An independently observable selector mismatch may be retained as diagnostic detail, but MUST NOT suppress a validation failure or change the denial result. Validation and aggregation must continue across all active blocks to preserve all applicable reasons; no early mismatch may short-circuit trust checks.

For a block (b) whose mandatory pre-selector validation status is `PASSED`, define:
- (A(b,r)): its assistant selector matches the trusted assistant identity for request (r).
- (T(b,r)): its target selector matches the trusted canonical target identity for request (r).

The block applies if and only if both predicates match: `A(b,r) AND T(b,r)`. 

- `GLOBAL` makes its own predicate true for any valid identity in that dimension; it does not broaden the other predicate.
- `EXACT(x)` is true only when the trusted canonical identity in that same dimension equals the catalogue's canonical ID `x`.
- A valid exact mismatch in either independent dimension proves the request falls outside the intersection, but only when the entire block, producer, catalogue/version, identities and resolver result have first passed validation.
- A mismatch is **not** proof of non-applicability when any mandatory input is absent, malformed, unauthenticated, unsupported, conflicting, stale, revoked or unresolved.

### 3.2 Complete valid-state table

All rows below assume the complete active-block set is authenticated and complete, and the per-block `pre_selector_validation_status=PASSED` with every mandatory check and evidence reference present. Rows describe selector evaluation only after that gate; a mismatch concurrent with any failed/unknown precondition follows §4 and cannot produce `PROVEN_NOT_APPLICABLE`.

| Assistant selector | Target selector | Trusted resolved values | Per-block result |
|---|---|---|---|
| `GLOBAL` | `GLOBAL` | Any valid assistant and target | `BLOCK_APPLIES` |
| `EXACT(a)` | `GLOBAL` | Assistant = `a`; any valid target | `BLOCK_APPLIES` |
| `EXACT(a)` | `GLOBAL` | Valid assistant ≠ `a`; any valid target | `PROVEN_NOT_APPLICABLE` |
| `GLOBAL` | `EXACT(t)` | Any valid assistant; target = `t` | `BLOCK_APPLIES` |
| `GLOBAL` | `EXACT(t)` | Any valid assistant; valid target ≠ `t` | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | Assistant = `a`; target = `t` | `BLOCK_APPLIES` |
| `EXACT(a)` | `EXACT(t)` | Assistant mismatch; target matches | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | Assistant matches; target mismatch | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | Both valid exact selectors mismatch | `PROVEN_NOT_APPLICABLE` |

A valid mismatch in a single dimension does not need an artificial `BLOCK_SCOPE_UNEVALUABLE` result. The latter is reserved for inability to establish a trusted, complete, valid interpretation.

## 4. Fail-closed data, schema and trust states

No invalid or unknown state may be converted into non-applicability, permission or success.

| Condition | Required result |
|---|---|
| Missing required selector, empty or malformed selector, unknown canonical ID | `BLOCK_SCOPE_UNEVALUABLE`; deny |
| Recognized schema with mandatory fields missing | `BLOCK_SCOPE_UNEVALUABLE`; deny |
| Absent or unrecognized schema/catalogue that cannot be authenticated, without trusted evidence identifying a supported legacy schema | `SCOPE_MODEL_UNAVAILABLE`; deny |
| Unsupported schema or policy version | `SCOPE_VERSION_UNSUPPORTED`; deny |
| Catalogue signature/integrity/trust validation fails | `CATALOGUE_INTEGRITY_INVALID`; deny |
| Catalogue or producer is revoked | `CATALOGUE_REVOKED` or `PRODUCER_UNAUTHORIZED`; deny |
| Alias ambiguous, noncanonical or conflicting across catalogue revisions | `SCOPE_MODEL_UNAVAILABLE`; deny |
| Producer principal not authenticated or not allowlisted for the block class | `PRODUCER_UNAUTHORIZED`; deny; producer's string ID is not proof |
| Target identity only supplied by caller or operation mapping unavailable | `TARGET_IDENTITY_UNTRUSTED`; deny |
| Duplicate canonical IDs, conflicting provenance or incompatible selector semantics | `BLOCK_SCOPE_UNEVALUABLE` or `SCOPE_MODEL_UNAVAILABLE` according to the specific failure; deny |
| Authenticated, identifiable legacy record whose prior selector semantics are ambiguous | `LEGACY_SCOPE_UNEVALUABLE`; deny; no automatic migration |
| Empty/wildcard selector in a recognized schema with known selector semantics | `BLOCK_SCOPE_UNEVALUABLE`; deny |
| Active-block set absent, partial, stale, unauthenticated or lacking a verifiable completeness attestation | `ACTIVE_BLOCK_SET_UNVERIFIABLE`; deny |
| Complete valid exact mismatch with all trust checks satisfied and per-stage status `PASSED` | `PROVEN_NOT_APPLICABLE` for that block only |
| Any selector mismatch concurrent with failed/unknown/missing pre-selector validation | Applicable validation denial code(s); `DENY`; never `PROVEN_NOT_APPLICABLE` |

A block-supplied `consistent=true` flag has no authority. Consistency is independently derived from field/schema validation, canonical identifiers, version compatibility, producer authorization, catalogue integrity and trusted identity resolution. Missing trust infrastructure means the protected operation stays denied; it does not mean all arbitrary incoming records become authoritative.

## 5. Trusted catalogue, producer and target resolver

### 5.1 Catalogue authority and lifecycle

The accountable policy owner is the IABV human Project Owner/governance authority as adopted in the design. Runtime publisher/principal identity and trust-anchor binding still require evidence from an authorized engineering/gov­ernance source.

A catalogue must be:
- versioned and integrity-protected;
- published or attested by a verifiably authorized publisher rooted in an established trust anchor;
- canonical in its IDs and aliases, with alias resolution unique within a specified revision;
- governed by explicit compatibility, publication, retirement, revocation and audit rules;
- rejected deterministically if unsupported, revoked, ambiguous or inconsistent.

A digest proves which bytes were hashed; it does not prove who authorized them. A version number or `producer_id` string is likewise not authority. The cryptographic mechanism and real trust-anchor material have not been selected or verified in the current authorized evidence.

**Active-block-set completeness is a separate, mandatory trust claim.** A protected evaluation MUST use a complete, authenticated, versioned snapshot of all active blocks within the applicable authority/scope at a defined catalogue revision or epoch. The attestation MUST bind at least the publisher/root identity, catalogue revision and digest, request-relevant scope, completeness/sequence marker, retrieval or issue time, freshness/expiry and current revocation evidence; an empty set is valid only when it is an explicitly authenticated complete snapshot, not when a response is absent. The set and its completeness claim must be verifiable under the approved publisher/trust-anchor path. The evaluator may verify this evidence but MUST NOT make its own list complete merely by asserting that it is complete; a producer-supplied list, partial response, cache with unverified freshness, missing response or evaluator self-assertion is insufficient. Publisher authorization is checked separately from each producer's authorization; any shared principal would need explicit authority for both roles, never an assumed equivalence.

If the snapshot, completeness attestation, freshness, integrity, publisher authority or revocation state cannot be verified, return `ACTIVE_BLOCK_SET_UNVERIFIABLE` and deny. This is a normative requirement, **not** a claim that an active-block registry, snapshot service or trust root is currently implemented or established. Until such evidence exists, the protected operation remains denied.

### 5.2 Producer authorization

Only an authenticated and allowlisted producer may create a block in its permitted class. Producer identity and authorization are separate checks. Schema validity alone is insufficient. The policy must define the effects of producer revocation on existing versus newly issued blocks; no unapproved automatic release of existing blocks is allowed.

### 5.3 Target identity and resolver

The authoritative operation-to-target mapping is governed by the Owner and resolved server-side from the registered operation/route and its actual implementation identity. The requester's `operation_scope` value MUST NOT establish or alter the authoritative target. It may be compared for anomaly telemetry only.

Every resolver result must bind its registry/catalogue revision and the registered implementation/call site. A guessed label, a test name, a free-form caller string or a prefix match does not establish a target identity. When the mapping or the implementation binding has not been verified, return `TARGET_IDENTITY_UNTRUSTED` and deny the protected read/list operation.

**Current evidence limitation:** the previously bounded public-source review found no authoritative versioned scope registry or trusted operation-to-target resolver in the inspected `models.py`, `world_model_service.py` and `server.py` paths. This is a bounded result, not proof of global absence. No broad scan is licensed by this contract.

## 6. Evaluation and all-block aggregation

The evaluation algorithm is normative, deterministic and fail-closed:

1. **Authenticate completeness first.** Obtain and verify the authoritative active-block-set snapshot/completeness attestation defined in §5.1, including its applicable authority/catalogue revision, scope, integrity, freshness and revocation status. If it is missing, partial, inconsistent, stale or unverifiable, the overall result is `DENY` with `ACTIVE_BLOCK_SET_UNVERIFIABLE`; do not interpret absence as an empty set.
2. **Validate every block without short-circuiting the set.** For every block in the authenticated snapshot, check required metadata/schema, supported versions, canonical IDs, catalogue publisher/trust, catalogue integrity/revocation, producer principal/authorization, and the trusted identity/resolver bindings. Store each check's `PASSED`/`FAILED`/`UNKNOWN` outcome and evidence reference, and preserve all denial reasons.
3. **Resolve trusted identities.** Resolve assistant and operation/target identity from trusted server-side sources; ignore caller-supplied target metadata as authority. Bind resolver and registered call-site revision/evidence in the record.
4. **Gate selector evaluation on explicit validation.** For a particular block, evaluate its selector predicates only if every required pre-selector check is explicitly `PASSED` and `pre_selector_validation_status=PASSED`. Otherwise record the specific denial result(s) and do not emit `PROVEN_NOT_APPLICABLE`, even if one selector mismatch is observable.
5. **Aggregate every active block.** Preserve a per-block result and every applicable reason. A result can proceed only if every block result is exactly `BLOCK_APPLIES` or `PROVEN_NOT_APPLICABLE`, the active-block set remains verified, no mandatory check is failed/unknown, and every `BLOCK_APPLIES` block has its own independently authorized, currently valid release. Any other per-block state—including `BLOCK_SCOPE_UNEVALUABLE`, `SCOPE_MODEL_UNAVAILABLE`, `SCOPE_VERSION_UNSUPPORTED`, `CATALOGUE_INTEGRITY_INVALID`, `CATALOGUE_REVOKED`, `PRODUCER_UNAUTHORIZED`, `TARGET_IDENTITY_UNTRUSTED`, `LEGACY_SCOPE_UNEVALUABLE`, or `BLOCK_RELEASE_UNSUPPORTED`—forces `DENY`.
6. **Emit a non-authorizing gate result only after complete aggregation.** If all active blocks are safely evaluated and none applies, emit `SCOPE_GATE_PASSED_TO_NEXT_GATE` with `gate_reason=NO_APPLICABLE_BLOCKS_PROVEN`. If one or more blocks apply but every applicable block has its own independently verified, unexpired and unrevoked release, and no block is unevaluable, the gate may emit the same non-authorizing result with `gate_reason=ALL_APPLICABLE_BLOCKS_INDEPENDENTLY_RELEASED`. Any absent, stale, unverifiable or unverifiably unrevoked required release is denial. Neither gate result is read permission; Entry 274's independent reader and approval checks still apply.

For any denial, preserve all reason codes and per-block results. Use deterministic ordering for serialization (canonical block ID, then stable reason-code order); do not silently discard secondary denials. This contract does not require one primary denial code: consumers MUST use `decision=DENY` and the complete reason list, not infer precedence from one representative code. The `NO_APPLICABLE_BLOCKS_PROVEN` result is only a scope-gate result and is never read authorization. A known empty complete snapshot is not equivalent to an unavailable or missing snapshot.

### 6.1 Per-block result vocabulary

- `BLOCK_APPLIES`
- `PROVEN_NOT_APPLICABLE`
- `BLOCK_SCOPE_UNEVALUABLE`
- `SCOPE_MODEL_UNAVAILABLE`
- `SCOPE_VERSION_UNSUPPORTED`
- `CATALOGUE_INTEGRITY_INVALID`
- `CATALOGUE_REVOKED`
- `PRODUCER_UNAUTHORIZED`
- `TARGET_IDENTITY_UNTRUSTED`
- `LEGACY_SCOPE_UNEVALUABLE`
- `BLOCK_RELEASE_UNSUPPORTED`

Only `BLOCK_APPLIES` and `PROVEN_NOT_APPLICABLE` avoid an intrinsic per-block unevaluable/validation denial. `BLOCK_APPLIES` still forces overall `DENY` unless that specific block has its own valid independent release. All other per-block vocabulary values require denial; an applicable block with an absent/unverifiable release also carries `BLOCK_RELEASE_UNSUPPORTED`.

The set-level denial reason `ACTIVE_BLOCK_SET_UNVERIFIABLE` is not a per-block result: it records that the evaluator could not authenticate a complete active set and therefore cannot make an exhaustive applicability claim. When set completeness fails, the overall decision is `DENY`, the set-level reason is preserved, and no absent/unseen block may be fabricated as an individual per-block result. This vocabulary separation is normative; it does not claim an implementation exists.

The overall scope-gate decision is `DENY` or `SCOPE_GATE_PASSED_TO_NEXT_GATE`. The latter is never authorization; its required `gate_reason` is either `NO_APPLICABLE_BLOCKS_PROVEN` or `ALL_APPLICABLE_BLOCKS_INDEPENDENTLY_RELEASED`, with all per-block results preserved. These labels are design vocabulary, not claims about codes already present in source.

## 7. Independent block release and Entry 274 boundary

A scope evaluation, diagnostic, approval receipt, `BlockEvaluation`, decision ID, signature or audit receipt is evidence and MUST NOT itself be treated as permission, a bearer capability or a release.

Consistent with Entry 274:
- diagnostic metadata does not grant permission;
- fresh Owner approval evidence is separate from the read decision;
- a trusted issuer creates the server-side read decision after checking policy and scope;
- the reader re-verifies immediately before each operation;
- the durable operation ledger/receipt records intent/outcome but is never authority;
- read approval cannot release an operational/governance block.

A block release, if ever supported, must be a distinct artifact from the independently authenticated authority designated for that particular block. It must bind at least block ID/revision/digest, target/operation/scope, authority identity, issue/expiry and revocation status. Reader, requesting agent, ordinary read issuer, block producer and diagnostic receipt do not acquire release authority by implication. If a verifiable independent release mechanism is unavailable, return `BLOCK_RELEASE_UNSUPPORTED` and deny.

**Freshness and revocation are evaluated, not inferred from cached history.** The verifier MUST validate the release artifact's authenticity, designated authority, exact block/revision/content digest and target/operation/scope binding, validity interval, and current revocation status at the protected decision boundary. A previously cached `valid` result without a current authoritative revocation/freshness check is not a valid release. The downstream reader MUST repeat the applicable verification immediately before each protected operation and before releasing staged content, consistent with Entry 274. If the authoritative revocation source is unavailable, stale, inconsistent or unverifiable, the release is not confirmed: return `BLOCK_RELEASE_UNSUPPORTED` and deny. This does not assert that a revocation service currently exists.

Even `NO_APPLICABLE_BLOCKS_PROVEN` cannot bypass Entry 274's other requirements: fresh interactive approval, authenticated issuer/session, exact target/path scope, budgets, expiry/revocation, path containment and durable ledger requirements remain separate and mandatory.

## 8. Versioning, legacy treatment and migration

This non-adopted successor candidate proposes schema/policy version `1.0.1`; the currently accepted baseline remains v1.0.0 until a separate canonical routing update accepts a reviewed successor. A live implementation must bind the exact schema, policy and catalogue revisions used for each evaluation, and reject unsupported or revoked versions.

No automatic legacy migration is permitted. Existing blocks remain blocking unless a separately authorized migration establishes authenticated provenance and unambiguous typed selectors, or the independent authorized block owner issues a valid release. Empty, missing, wildcard or free-form values MUST NOT be rewritten or interpreted as `GLOBAL` or `NONE` by default. A recognized schema missing mandatory fields is malformed/incomplete and returns `BLOCK_SCOPE_UNEVALUABLE`. An absent/unrecognized schema without authenticated legacy classification returns `SCOPE_MODEL_UNAVAILABLE`. An authenticated, identifiable legacy record with ambiguous prior selector semantics returns `LEGACY_SCOPE_UNEVALUABLE`. All fail closed, but the reason remains distinguishable.

Migration work, if proposed later, needs its own bounded design, data-integrity plan, authority, evidence and explicit authorization. It is not included in this design acceptance.

## 9. Conformance and falsification matrix

These 38 cases are **required design acceptance cases; none has been executed**. Cases C31–C38 are additional discriminators introduced by the v1.0.0 findings. Source/runtime implementation and test execution are separately gated.

| ID | Scenario | Expected result |
|---|---|---|
| M1A-C01 | `GLOBAL/GLOBAL`, all authority checks valid | `BLOCK_APPLIES` |
| M1A-C02 | `EXACT(a)/GLOBAL`, assistant matches | `BLOCK_APPLIES` |
| M1A-C03 | `EXACT(a)/GLOBAL`, trusted assistant mismatch | `PROVEN_NOT_APPLICABLE` |
| M1A-C04 | `GLOBAL/EXACT(t)`, target matches | `BLOCK_APPLIES` |
| M1A-C05 | `GLOBAL/EXACT(t)`, trusted target mismatch | `PROVEN_NOT_APPLICABLE` |
| M1A-C06 | `EXACT/EXACT`, both match | `BLOCK_APPLIES` |
| M1A-C07 | `EXACT/EXACT`, only assistant mismatches validly | `PROVEN_NOT_APPLICABLE` |
| M1A-C08 | `EXACT/EXACT`, only target mismatches validly | `PROVEN_NOT_APPLICABLE` |
| M1A-C09 | `EXACT/EXACT`, both mismatch validly | `PROVEN_NOT_APPLICABLE` |
| M1A-C10 | Exact mismatch claimed but another required selector/schema field is absent | `BLOCK_SCOPE_UNEVALUABLE`, never non-applicable |
| M1A-C11 | Assistant mismatch but target identity is caller-supplied/unresolved | `TARGET_IDENTITY_UNTRUSTED`, deny |
| M1A-C12 | Missing, empty, malformed or unknown selector ID | Fail-closed unevaluable |
| M1A-C13 | Recognized schema is missing a mandatory field | `BLOCK_SCOPE_UNEVALUABLE` |
| M1A-C14 | Schema absent/unrecognized or catalogue unauthenticated | `SCOPE_MODEL_UNAVAILABLE` |
| M1A-C15 | Unsupported/mixed schema or policy revisions | `SCOPE_VERSION_UNSUPPORTED`, deny |
| M1A-C16 | Catalogue digest valid but publisher/trust-root proof absent | `CATALOGUE_INTEGRITY_INVALID`/unavailable, deny |
| M1A-C17 | Ambiguous/conflicting aliases across catalogue revisions | `SCOPE_MODEL_UNAVAILABLE`, deny |
| M1A-C18 | Producer string is present but principal/allowlist authorization fails | `PRODUCER_UNAUTHORIZED`, deny |
| M1A-C19 | Catalogue, producer or policy is revoked | Deny; preserve exact revocation reason |
| M1A-C20 | Active-block set cannot be proven complete | `DENY` |
| M1A-C21 | One applicable unreleased block plus one non-applicable block | `DENY`; preserve both per-block results |
| M1A-C22 | One unevaluable block plus all other blocks non-applicable | `DENY`; no short-circuit that hides it |
| M1A-C23 | Two applicable blocks, only one independent release exists | `DENY` |
| M1A-C24 | Reordered active-block input produces different outcome/reasons | Reject implementation; aggregation must be deterministic |
| M1A-C25 | Receipt/evaluation object is presented as bearer permission or block release | Reject; no authorization is conferred |
| M1A-C26 | All blocks validly non-applicable, but Entry 274 fresh approval/session/reader gate absent | Scope gate may report `NO_APPLICABLE_BLOCKS_PROVEN`; overall read still denied |
| M1A-C27 | Legacy record has ambiguous empty/wildcard semantics | `LEGACY_SCOPE_UNEVALUABLE`, deny; do not auto-migrate |
| M1A-C28 | Independent release absent/unverifiable for an applicable block | `BLOCK_RELEASE_UNSUPPORTED`, deny |
| M1A-C29 | No applicable blocks; complete trusted active-block set evaluated | `SCOPE_GATE_PASSED_TO_NEXT_GATE` with `gate_reason=NO_APPLICABLE_BLOCKS_PROVEN`; still no read permission |
| M1A-C30 | One or more blocks apply, each has a valid independently verified and currently unrevoked release, and no block is unevaluable | `SCOPE_GATE_PASSED_TO_NEXT_GATE` with `gate_reason=ALL_APPLICABLE_BLOCKS_INDEPENDENTLY_RELEASED`; still no read permission |
| M1A-C31 | Exact-selector mismatch is observable but catalogue signature/integrity fails in the same evaluation | `DENY`, preserve `CATALOGUE_INTEGRITY_INVALID`; never `PROVEN_NOT_APPLICABLE` |
| M1A-C32 | Exact-selector mismatch is observable but producer authentication/allowlist fails in the same evaluation | `DENY`, preserve `PRODUCER_UNAUTHORIZED`; never `PROVEN_NOT_APPLICABLE` |
| M1A-C33 | Active-block list is producer-supplied, evaluator-self-asserted, partial or lacks authenticated completeness evidence | `DENY` with `ACTIVE_BLOCK_SET_UNVERIFIABLE`; no `NO_APPLICABLE_BLOCKS_PROVEN` |
| M1A-C34 | Compare an authenticated, complete, current explicit empty-set snapshot with a missing/timeout/partial active-set response | Explicit authenticated empty snapshot may pass the scope gate only; missing/unverifiable response `DENY` with `ACTIVE_BLOCK_SET_UNVERIFIABLE` |
| M1A-C35 | One block is `LEGACY_SCOPE_UNEVALUABLE` and another has a valid exact mismatch | Overall `DENY`; preserve legacy failure and the other per-block result; never treat the legacy state as non-denial |
| M1A-C36 | Exact mismatch exists but `pre_selector_validation_status` is missing/`UNKNOWN`, or one mandatory stage lacks evidence | Reject `PROVEN_NOT_APPLICABLE`; `DENY` with the applicable validation reason(s) |
| M1A-C37 | A cached independent release was revoked, expires, or its authoritative revocation source cannot be queried at decision time | `DENY` with `BLOCK_RELEASE_UNSUPPORTED`; cache alone cannot pass C30 |
| M1A-C38 | Exact mismatch with an authenticated complete active set and every mandatory pre-selector stage explicitly `PASSED` with evidence references | `PROVEN_NOT_APPLICABLE` for that block; still no read permission by itself |

A proposed implementation is not conformant if it omits any applicable case, silently converts unknown to non-applicable, lets caller-provided scope control the result, trusts producer fields, short-circuits accounting of active blocks, or allows a diagnostic/receipt to grant or release authority.

## 10. Required evidence before any future implementation acceptance

A separate future implementation authorization would still require, in order:

1. Evidence of the real authenticated Owner/governance principal and trust anchor; this document's Owner acceptance token is a normative design receipt, not a runtime credential.
2. Authorized publisher catalogue, producer allowlist/class policy, integrity validation and revocation lifecycle with their real authority bindings.
3. Versioned server-side operation-to-target registry bound to actual registered implementation/call sites.
4. Typed schema/evaluator wiring at every relevant real read/list decision point, with no open-prefix or caller-controlled scope acceptance.
5. Complete deterministic per-block aggregation and independently verified block release path, or continued terminal denial if release cannot be supported.
6. Integration with Entry 274's fresh interactive approval, server-side ledger, immediate reader verification, race-resistant containment, budgets, expiry/revocation and durable receipt requirements.
7. Separately authorized synthetic conformance tests with correlated candidate/commit/command/result receipts; static review alone is not test execution.
8. Independent verification that any PASS applies to the exact candidate and revision. No local/runtime claim may be inferred from public documentation.

Until these are satisfied and permissions are separately granted, `READ_LIST=FAIL_CLOSED` and `GOVERNANCE=KEEP_BLOCKED`.

## 11. Traceability matrix

| Contract rule | Parent / ledger trace | Required verification |
|---|---|---|
| Conjunctive independent selectors; `GLOBAL` dimension-local; mismatch only after all mandatory validation passes | UAAL-ROOT-001 → M1A ledger §2; OG-M1A-01 | C01–C10, C31–C32, C36, C38 |
| Explicit pre-selector validation status and stage evidence; validation failure cannot be hidden by mismatch | Construction-completeness overlay C2/C3/C7; Entry 274 evidence/authority separation | C10, C12–C19, C31–C32, C36, C38 |
| Authoritative active-block set and proof of completeness, including explicit empty snapshot vs missing result | §5.1 catalogue authority/lifecycle; OG-M1A-02/05; construction overlay C3/C5/C7 | C20, C33–C34 |
| All-block accounting, mixed result states, complete reason preservation and order-independence | M1A ledger §3; construction overlay; Entry 274 fail-closed aggregation | C21–C24, C35 |
| Independent per-block release, exact binding, freshness and revocation at the protected boundary | Entry 274 §6–§7; OG-M1A-06 | C21, C23, C28, C30, C37 |
| Diagnostic evaluation/receipt is evidence, not authorization or release | Entry 274 §§2, 5, 7 | C25–C26 |
| Legacy records remain blocking; no automatic migration; legacy failure always denies | Ledger OG-M1A-07; Entry 274 fail-closed rules | C13, C27, C35 |
| Scope-gate pass reasons are explicit and never imply read permission | Entry 274 separate authority planes; §§6–7 | C26, C29–C30, C34 |
| Owner decision adopts design only; runtime authorities and implementation gates remain separate | Owner acceptance receipt; UAAL evidence-layer distinction | §10 gates; §12 truth block |

## 12. Candidate status, acceptance and change control

The v1.0.0 predecessor is the Owner-adopted design baseline under the exact response `ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE`. The targeted report received for that immutable v1.0.0 artifact returned `PASS_WITH_REPAIRS` with eight findings (F-M1A-01..08); the complete reconciled receipt is [the M1A v1.0.0 review finding register](./CHAT-ARCH-2026-10-22-M1A-contract-v1-sonnet-review-receipt-and-finding-register.md). The preserved Codex proposal, earlier review inputs, and v1.0.0 itself remain unchanged.

This v1.0.1 document is a **successor candidate, not yet adopted**. Its intended changes are technical completeness/traceability repairs derived from existing fail-closed and authority-separation requirements; the seven Owner decisions OG-M1A-01..07 are unchanged. Do not infer that a registry, stage validator, release verifier, revocation service or any other runtime mechanism exists. A new targeted review must verify this exact candidate and all relevant clauses/cases. If it exposes a need to change an adopted design choice or a higher-authority conflict, stop and route that point to governance rather than silently changing policy. Fetch-back and canonical routing update are required before this candidate can be treated as a reviewed successor.

**Current truth:**

```text
CONTRACT=IABV-OPERATIONAL-BLOCK-SCOPE
CONTRACT_VERSION=1.0.1
PREDECESSOR_CONTRACT_VERSION=1.0.0
PREDECESSOR_CONTRACT_BLOB=8181c7c0cf6036c76cf365510e8d9665cf84e57e
SCHEMA_ID=iabv.operational_block_scope
SCHEMA_VERSION=1.0.1
POLICY_VERSION=1.0.1
OWNER_DESIGN_ACCEPTANCE=ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE (v1.0.0 baseline; choices unchanged)
CANDIDATE_STATUS=NOT_ADOPTED_PENDING_TARGETED_REVIEW
SUCCESSOR_STATUS=NOT_ADOPTED_PENDING_TARGETED_REVIEW
DESIGN_BASELINE=NORMATIVE_DESIGN_BASELINE_ADOPTED_V1.0.0
REAL_TRUST_ANCHOR=UNVERIFIED
TRUSTED_CATALOGUE=NOT_ESTABLISHED
TRUSTED_OPERATION_TARGET_RESOLVER=NOT_ESTABLISHED
PRODUCER_ALLOWLIST=NOT_ESTABLISHED
INDEPENDENT_BLOCK_RELEASE_MECHANISM=NOT_ESTABLISHED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
READ_LIST=FAIL_CLOSED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
```
