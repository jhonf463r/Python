# IABV M1A — Consolidated operational-block scope contract v1.0.0

- **Contract ID:** `IABV-OPERATIONAL-BLOCK-SCOPE`
- **Contract version:** `1.0.0`
- **Schema ID:** `iabv.operational_block_scope`
- **Schema version:** `1.0.0`
- **Policy version:** `1.0.0`
- **Catalogue versioning:** independently versioned; each evaluation must bind the exact catalogue revision.
- **Effective design status:** `NORMATIVE_DESIGN_BASELINE_ADOPTED`
- **Owner acceptance receipt:** exact chat response `ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE`, received 2026-10-22 (America/Bogota).
- **Implementation status:** `NOT_IMPLEMENTED`; no source code, runtime, or tests are claimed.
- **Operational posture:** `GOVERNANCE=KEEP_BLOCKED`; `READ_LIST=FAIL_CLOSED`; `IMPLEMENTATION=NOT_AUTHORIZED`; `TESTS=NOT_RUN`; `BRIDGE=BRIDGE_NOT_READY`.
- **Canonical route:** [CURRENT-STATE.md](./CURRENT-STATE.md).
- **Decision ledger:** [M1A normalized scope decision ledger](./CHAT-ARCH-2026-10-22-M1A-normalized-scope-decision-ledger-and-design-amendment.md).

## 1. Purpose, authority and scope

This contract adopts the M1A recommended design baseline following the Owner's exact acceptance token. It defines how typed assistant and operation/target selectors constrain the applicability of an operational block. It is a normative **design contract**, not evidence that its trust infrastructure or evaluator exists in deployed/local code.

### 1.1 Parent contracts

This child contract is traceable to:
- [UAAL-ROOT-001 — Universal Adaptive Algorithm Constitution](./UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md): objective → perceive/represent/interpret → maintain uncertainty → infer capability → discover realizations → check constraints/access/resources → select → govern → act → observe → verify → update reusable knowledge → reuse/adapt.
- [Entry 274 — consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), especially its separate diagnostic, fresh approval, read decision, reader verifier and operation-ledger/receipt authorities; mandatory fail-closed behavior; trusted server-side target identity; and independent block release.
- [The construction-completeness/traceability overlay](./CHAT-ARCH-2026-10-22-UAAL-construction-completeness-traceability-overlay.md): bidirectional traceability, state-space closure, authority-plane separation, bounded handoff, reconciliation and fetch-back requirements.
- [Central M1A reconciliation](./CHAT-ARCH-2026-10-22-central-space-time-coordinator-m1a-reconciliation.md) and [the normalized ledger](./CHAT-ARCH-2026-10-22-M1A-normalized-scope-decision-ledger-and-design-amendment.md): derivation history and normalized decisions.

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

The terms **MUST**, **MUST NOT**, **SHOULD** and **MAY** express requirements of this design contract.

A conforming implementation shall represent the two selector dimensions as typed, independent fields; it must not encode them only as ambiguous free-form strings. Conceptual selector form:

- `GLOBAL`: matches every valid value in that selector's own dimension only.
- `EXACT(canonical_id)`: matches only a trusted, canonical, registered ID for that dimension.
- No missing, empty, wildcard-like, alias-only or unrecognized value is implicitly equivalent to `GLOBAL`, `NONE` or `EXACT`.

Every block evaluation must bind, at minimum:
- immutable block ID and revision/content digest;
- schema ID/version, policy version and exact catalogue revision;
- authenticated producer principal/reference and authorized producer class;
- typed assistant selector and typed target selector;
- trusted resolved assistant ID and canonical target-scope ID (including resolver/catalogue revision);
- provenance/integrity/authorization evidence references;
- evaluation result, all reason codes and relevant timestamps;
- independent block-release artifact reference, if one exists and verifies.

The conceptual model ID is `iabv.operational_block_scope`; schema and policy version `1.0.0` describe this **design contract** only. They do not assert that a live catalogue carrying those versions has been published or authenticated. Catalogue revision, publisher signature/attestation, trust anchor and revocation state must be separate explicit evidence.

## 3. Selector semantics

### 3.1 Matching rule

For a fully authenticated, supported and internally consistent block (b), define:
- (A(b,r)): its assistant selector matches the trusted assistant identity for request (r).
- (T(b,r)): its target selector matches the trusted canonical target identity for request (r).

The block applies if and only if both predicates match: `A(b,r) AND T(b,r)`. 

- `GLOBAL` makes its own predicate true for any valid identity in that dimension; it does not broaden the other predicate.
- `EXACT(x)` is true only when the trusted canonical identity in that same dimension equals the catalogue's canonical ID `x`.
- A valid exact mismatch in either independent dimension proves the request falls outside the intersection, but only when the entire block, producer, catalogue/version, identities and resolver result have first passed validation.
- A mismatch is **not** proof of non-applicability when any mandatory input is absent, malformed, unauthenticated, unsupported, conflicting, stale, revoked or unresolved.

### 3.2 Complete valid-state table

All rows below assume the block metadata, authorized producer, catalogue integrity/revision, supported versions, assistant identity and target identity are validated unless the row says otherwise.

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
| Complete valid exact mismatch with all trust checks satisfied | `PROVEN_NOT_APPLICABLE` for that block only |

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

### 5.2 Producer authorization

Only an authenticated and allowlisted producer may create a block in its permitted class. Producer identity and authorization are separate checks. Schema validity alone is insufficient. The policy must define the effects of producer revocation on existing versus newly issued blocks; no unapproved automatic release of existing blocks is allowed.

### 5.3 Target identity and resolver

The authoritative operation-to-target mapping is governed by the Owner and resolved server-side from the registered operation/route and its actual implementation identity. The requester's `operation_scope` value MUST NOT establish or alter the authoritative target. It may be compared for anomaly telemetry only.

Every resolver result must bind its registry/catalogue revision and the registered implementation/call site. A guessed label, a test name, a free-form caller string or a prefix match does not establish a target identity. When the mapping or the implementation binding has not been verified, return `TARGET_IDENTITY_UNTRUSTED` and deny the protected read/list operation.

**Current evidence limitation:** the previously bounded public-source review found no authoritative versioned scope registry or trusted operation-to-target resolver in the inspected `models.py`, `world_model_service.py` and `server.py` paths. This is a bounded result, not proof of global absence. No broad scan is licensed by this contract.

## 6. Evaluation and all-block aggregation

The evaluation algorithm is:

1. Establish the complete active-block set and the applicable authenticated authority/catalogue revisions. If completeness cannot be established, deny.
2. Validate schema, required fields, canonical IDs, version compatibility, integrity, producer identity/permission and revocation for the set; do not trust producer-supplied consistency fields.
3. Resolve assistant and operation/target identity from trusted server-side sources; ignore caller-supplied target metadata as authority.
4. Evaluate every active block against the two conjunctive selector dimensions. Preserve the outcome and reason evidence for every block; no ordering-dependent short-circuit may hide an unevaluable or applicable block.
5. If any block applies without its own valid independent release artifact, deny. If any block cannot be evaluated safely, deny. If the active set, catalogue, producer state or target identity is unavailable, deny.
6. If all active blocks are safely evaluated and none applies, emit `SCOPE_GATE_PASSED_TO_NEXT_GATE` with `gate_reason=NO_APPLICABLE_BLOCKS_PROVEN`. If one or more blocks apply but every applicable block has its own valid independent release and no block is unevaluable, the gate may emit the same non-authorizing `SCOPE_GATE_PASSED_TO_NEXT_GATE` with `gate_reason=ALL_APPLICABLE_BLOCKS_INDEPENDENTLY_RELEASED`. An absent/unverifiable release is denial. Neither gate result is read permission; Entry 274's independent reader and approval checks still apply.

For any denial, preserve all reason codes and per-block results. Use deterministic ordering for serialization (canonical block ID, then stable reason-code order); do not silently discard secondary denials. This contract does not require a single primary denial code: consumers MUST use `decision=DENY` and the complete reason list, not infer precedence from one representative code. The `NO_APPLICABLE_BLOCKS_PROVEN` result is only a scope-gate result and is never read authorization.

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

The overall scope-gate decision is `DENY` or `SCOPE_GATE_PASSED_TO_NEXT_GATE`. The latter is never authorization; its required `gate_reason` is either `NO_APPLICABLE_BLOCKS_PROVEN` or `ALL_APPLICABLE_BLOCKS_INDEPENDENTLY_RELEASED`, with all per-block results preserved. A missing/unverifiable required release is denial reason `BLOCK_RELEASE_UNSUPPORTED`. These labels are design vocabulary, not claims about codes already present in source.

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

Even `NO_APPLICABLE_BLOCKS_PROVEN` cannot bypass Entry 274's other requirements: fresh interactive approval, authenticated issuer/session, exact target/path scope, budgets, expiry/revocation, path containment and durable ledger requirements remain separate and mandatory.

## 8. Versioning, legacy treatment and migration

This design is schema/policy version `1.0.0`. A live implementation must bind the exact schema, policy and catalogue revisions used for each evaluation, and reject unsupported or revoked versions.

No automatic legacy migration is permitted. Existing blocks remain blocking unless a separately authorized migration establishes authenticated provenance and unambiguous typed selectors, or the independent authorized block owner issues a valid release. Empty, missing, wildcard or free-form values MUST NOT be rewritten or interpreted as `GLOBAL` or `NONE` by default. A recognized schema missing mandatory fields is malformed/incomplete and returns `BLOCK_SCOPE_UNEVALUABLE`. An absent/unrecognized schema without authenticated legacy classification returns `SCOPE_MODEL_UNAVAILABLE`. An authenticated, identifiable legacy record with ambiguous prior selector semantics returns `LEGACY_SCOPE_UNEVALUABLE`. All fail closed, but the reason remains distinguishable.

Migration work, if proposed later, needs its own bounded design, data-integrity plan, authority, evidence and explicit authorization. It is not included in this design acceptance.

## 9. Conformance and falsification matrix

These cases are **required design acceptance cases; none has been executed**. Source/runtime implementation and test execution are separately gated.

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
| M1A-C30 | One or more blocks apply, each has a valid independent release, and no block is unevaluable | `SCOPE_GATE_PASSED_TO_NEXT_GATE` with `gate_reason=ALL_APPLICABLE_BLOCKS_INDEPENDENTLY_RELEASED`; still no read permission |

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
| Conjunctive independent selectors; `GLOBAL` dimension-local | UAAL-ROOT-001 → M1A ledger §2; OG-M1A-01 | M1A-C01–C10 |
| Owner accountability vs unverified actual principal/trust anchor | Ledger §8; OG-M1A-02 | Authenticated principal/trust-anchor evidence |
| Producer identity and authorization are distinct | Entry 274 authority/provenance boundary; OG-M1A-03 | Producer principal and allowlist evidence; C18–C19 |
| Server-side operation-to-target resolver; caller scope not authority | Entry 274 §4/§7; OG-M1A-04 | Registry and real call-site bindings; C11 |
| Integrity, versioning, lifecycle and revocation | Entry 274 §6/§7; OG-M1A-05 | Trusted catalogue/revocation evidence; C14–C19 |
| Independent per-block release | Entry 274 §7; OG-M1A-06 | Independent release authority/artifact; C21–C25, C28 |
| Legacy stays blocking; no automatic migration | Ledger OG-M1A-07; Entry 274 fail-closed rules | Version/parser tests and migration authorization; C13, C27 |
| All active blocks accounted; reasons preserved; deterministic result | Ledger §3 and construction completeness overlay | C20–C24 |
| Evaluation/receipt is evidence, not authorization | Entry 274 §2, §5, §7 | C25–C26 |
| Design adoption is not implementation approval | UAAL evidence-layer distinction; Owner acceptance receipt | All gates in §10 remain separate |

## 12. Acceptance and change control

This v1.0.0 design baseline is adopted under the explicit Owner response `ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE`. The preserved Codex proposal and the Owner-supplied Claude/Sonnet-attributed review remain immutable historical inputs; the review invocation itself is not independently authenticated.

Changes to selector semantics, trust ownership, producer authority, catalogue lifecycle, release authority or legacy treatment require a new explicit governance decision. Technical corrections that follow this contract may be derived, documented and reviewed without reopening the accepted policy, unless they change its normative meaning. Any new version must identify the delta, trace affected requirements/cases, preserve history, and be fetched back from GitHub.

**Current truth:**

```text
CONTRACT=IABV-OPERATIONAL-BLOCK-SCOPE
CONTRACT_VERSION=1.0.0
SCHEMA_ID=iabv.operational_block_scope
SCHEMA_VERSION=1.0.0
POLICY_VERSION=1.0.0
OWNER_DESIGN_ACCEPTANCE=RECEIVED_EXACT_TOKEN_2026-10-22
DESIGN_BASELINE=NORMATIVE_DESIGN_BASELINE_ADOPTED
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
