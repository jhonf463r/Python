# M1A — Normalized scope decision ledger and proposed design amendment

- Date: 2026-10-22, America/Bogota.
- Task: `M1A_COORDINATOR_DERIVE_SCOPE_SEMANTICS_AND_NORMALIZE_DECISION_LEDGER`.
- Parent concept: `UAAL-ROOT-001` in [the Universal Adaptive Algorithm Constitution](./UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md).
- Normative dependency: [Entry 274 — consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md).
- Source proposal (preserved unchanged): [Codex M1A proposal](./CHAT-ARCH-2026-10-22-M1A-Codex-scope-model-proposal.md), blob `b30b9167302c3ad35ec09e9097a6062545a96ad4`.
- Independent review report (preserved unchanged): [Claude/Sonnet-attributed review](./CHAT-ARCH-2026-10-22-M1A-independent-adversarial-review-claude.md), blob currently recorded in GitHub history; execution attribution stays `OWNER_SUPPLIED`.
- Design-authority status: `PROPOSED`; not policy, code or implementation.
- Operational posture: `GOVERNANCE=KEEP_BLOCKED`; `IMPLEMENTATION=NOT_AUTHORIZED`; `TESTS=NOT_RUN`; `READ_LIST=FAIL_CLOSED`; `BRIDGE=BRIDGE_NOT_READY`.

## 1. Why this is an amendment, not a parallel algorithm

The existing UAAL root already supplies the general construction/evolution cycle:

`OBJECTIVE → PERCEIVE → REPRESENT → INTERPRET → MAINTAIN UNCERTAINTY → INFER REQUIRED CAPABILITY → DISCOVER REALIZATIONS → CHECK CONSTRAINTS/ACCESS/RESOURCES → SELECT → GOVERN → ACT → OBSERVE → VERIFY → UPDATE WORLD/SELF MODEL → STORE REUSABLE KNOWLEDGE → REUSE → ADAPT → NEXT DECISION`.

This M1A artifact specializes only one bounded child: **how an operational block's typed assistant and target selectors are resolved and evaluated under trusted authority**. It does not create a second universal coordinator, duplicate provider/actor selection, or replace the memory protocol, Control Tower, goal-lock, or Entry 274. Those existing assets remain responsible for global routing, retrieval/provenance, anti-drift, and separate authorization.

The evidence trail remains layered:
- Codex proposal: owner-supplied design input, not approved policy.
- Sonnet/Claude-attributed report: owner-supplied review output; model invocation is not independently authenticated by this coordinator.
- Public GitHub artifacts: re-fetched and verified as documents; they do not prove local checkout or runtime state.
- Pinned M1 source baseline: the previously bounded checks found only string fields/producers and no authoritative versioned scope model or trusted operation-to-target resolver in the named source paths. Do not repeat a broad source scan; reopen source mapping only when an authorized scope or new contradictory evidence requires it.

## 2. Recommended selector semantics (derived candidate; adoption pending)

**Recommendation:** treat the two selectors as independent, conjunctive constraints over two separate dimensions. This is the clearest formal model for a block that names both an assistant and an operation/target scope. Since it changes a governance-sensitive decision rule, it remains `PROPOSED` until explicitly adopted by the authorized Owner/governance authority or superseded by a proven existing authoritative contract.

Definitions:
- `GLOBAL` matches every valid value in **its own dimension only**.
- `EXACT(x)` matches only when a trusted resolver has produced the same registered canonical ID `x` for that dimension.
- A well-formed block applies only if **both** dimensions match.
- If block metadata, model/version, producer provenance and target identity are complete, valid, trusted and internally consistent, an exact mismatch in either dimension proves the request lies outside the intersection. It is `PROVEN_NOT_APPLICABLE` for that block, whether the other selector matches, mismatches or is `GLOBAL`.
- Missing/unknown/malformed/untrusted/contradictory metadata is not a valid mismatch. It is unevaluable and cannot be used to establish non-applicability.
- A block-level `consistent` boolean supplied by a producer is never evidence. Consistency is derived by validating required fields, canonical IDs, declared catalogue/schema/policy versions, integrity/provenance, producer authorization and trusted target resolution.

### Complete core decision table

Every row assumes that all catalogue/policy versions, integrity checks, producer credentials, and operation/target identity are valid, unless the row explicitly describes a failure.

| Assistant selector | Target selector | Resolved assistant | Resolved target scope | Per-block outcome |
|---|---|---|---|---|
| `GLOBAL` | `GLOBAL` | Any registered assistant | Any registered target | `BLOCK_APPLIES` |
| `EXACT(a)` | `GLOBAL` | `a` | Any registered target | `BLOCK_APPLIES` |
| `EXACT(a)` | `GLOBAL` | Registered assistant other than `a` | Any registered target | `PROVEN_NOT_APPLICABLE` |
| `GLOBAL` | `EXACT(t)` | Any registered assistant | `t` | `BLOCK_APPLIES` |
| `GLOBAL` | `EXACT(t)` | Any registered assistant | Registered target other than `t` | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | `a` | `t` | `BLOCK_APPLIES` |
| `EXACT(a)` | `EXACT(t)` | Valid registered assistant other than `a` | Valid registered target | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | Valid registered assistant | Valid registered target other than `t` | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | Both exact selectors mismatch validly | Both identities valid and trusted | `PROVEN_NOT_APPLICABLE` |
| Selector field absent, empty, malformed or unregistered | Any | Any | Any | `BLOCK_SCOPE_UNEVALUABLE`; deny |
| Schema absent/unrecognized or catalogue cannot be authenticated/loaded | Any | Any | Any | `SCOPE_MODEL_UNAVAILABLE`; deny |
| Declared schema/policy/catalogue version not supported by this evaluator | Any | Any | Any | `SCOPE_VERSION_UNSUPPORTED`; deny |
| Catalogue alias resolves ambiguously or contradictorily | Any | Any | Any | Model/selector resolution unavailable; deny and preserve the exact failure evidence |
| Block's producer cannot be authenticated/authorized for this block class | Any | Any | Any | Block set is not trusted/complete; deny; do not accept the producer-supplied block as valid authority |
| Trusted operation-to-target mapping absent or caller is the only source of target | Any | Any | Untrusted or unresolved | `TARGET_IDENTITY_UNTRUSTED`; deny |
| Conflicting metadata, duplicate canonical IDs, incompatible semantics, or invalid provenance | Any | Any | Any | `BLOCK_SCOPE_UNEVALUABLE` or model unavailable as dictated by the precise failure class; deny; never prove non-applicability |
| Legacy record with unauthenticated empty/wildcard meaning | Any | Any | Any | `BLOCK_SCOPE_UNEVALUABLE` or `SCOPE_MODEL_UNAVAILABLE` according to whether the recognized schema can be parsed; deny; never infer `GLOBAL` or `NONE` |

The previous row “one dimension differs while the other matches → `BLOCK_SCOPE_UNEVALUABLE`” is replaced in this candidate by two distinct states: a **valid exact mismatch** proves non-applicability under conjunction; an **incomplete, conflicting or untrusted evaluation** remains unevaluable and blocking. This resolves the ambiguity without giving `GLOBAL` control over both dimensions.

## 3. All-block aggregation and receipt semantics

The evaluator must process the complete active-block set; no short-circuit or ordering rule may omit an active block from accounting. Each per-block result is preserved with its block ID/revision, declared versions, selector IDs, trusted target identity, producer/authority evidence, catalogue digest/version and evidence references.

The overall operation must be denied when:
- any active block applies and lacks a valid independent release artifact;
- any block cannot be evaluated safely;
- the catalogue/policy/producer/target authority is unavailable or integrity checks fail;
- the complete active-block set cannot be established.

If all active blocks are validly evaluated and none applies, the evaluator may report `NO_APPLICABLE_BLOCKS_PROVEN`; this is only one gate result and never overrides other governance, consent, path, session, budget, expiry, revocation or reader checks.

For mixed outcomes (for example, one block applies and another is unevaluable), preserve all outcomes and the overall `DENY` decision. Do not invent a primary denial-code precedence silently: the public contract must define one if a consumer requires a single code. A primary status must not erase secondary denial reasons.

A `BlockEvaluation` and any receipt are diagnostic/audit evidence, never a transferable bearer object, never read authority, and never a governance-block release. The downstream reader must evaluate authority at the server-side decision boundary; it cannot redeem a prior `PROVEN_NOT_APPLICABLE` object as permission. Entry 274 §2/§5/§7 remains controlling: a read decision cannot release a block, and release requires its own independently verified artifact from the authority that owns that block.

## 4. Trusted resolver, catalogue, producer and revocation requirements

- The authoritative target comes only from a trusted server-side registry binding the registered operation/route and its actual implementation identity to a canonical target-scope ID. Caller-supplied `operation_scope` is ignored for the authoritative decision. Comparing it for anomaly detection is optional and has no effect on the decision.
- A canonical registry ID is not a raw label or free-form string. Catalogue aliases must resolve uniquely under one explicit catalogue version to one canonical ID. Ambiguity or cross-version contradiction is a denial condition.
- A `registry_digest` proves the bytes that were hashed; it does not prove the bytes were approved by a trusted publisher. The evaluator needs a verifiable trust anchor and a validated publication/version process before treating a catalogue as authoritative.
- `producer_id` is an identity claim, not authority. Producer identity and permission to emit a given block class must be checked separately from schema validity. Producer revocation must invalidate the producer's ability to issue new blocks; treatment of previously issued blocks must be defined by the approved revocation policy.
- Catalogue/model versions need an explicit monotonic lifecycle: publication, compatibility, retirement/revocation, audit log, and deterministic behavior when an old or revoked version appears. A stale, future, unknown, or revoked policy version cannot be silently evaluated under the currently loaded policy.
- If the current model cannot authenticate the catalogue, block producers, trusted operation registry, or relevant version, protected operations do not receive permission. Fail-closed means denying the operation on missing authority; it does not mean blindly trusting an attacker-created block.
- Existing blocks remain active/blocking through migration unless the authorized owner of those blocks issues a distinct valid release. Legacy empty strings, `None`, wildcards or unknown schema are not automatically converted to `GLOBAL`, `NONE` or a typed record.

These are requirements for a future authority-backed design; the existence of this document does not demonstrate that a trust chain or resolver is already implemented.

## 5. Normalized Owner/governance decision ledger

The supplied review's “7 existing + 4 additional = 11 decisions” summary is not adopted. Its body calls some items technical clarifications, while the final summary miscounts them as new Owner decisions. Keep the seven original topics but express them as a deduplicated decision ledger; do not reopen them as independent questions in every chat.

| ID | Genuine Owner/governance decision | Coordinator recommendation | Dependency / current status |
|---|---|---|---|
| OG-M1A-01 | Adopt or replace the two-dimensional selector semantics. | Adopt independent conjunctive selectors and the table in §2, unless an existing authoritative contract proves a different policy. | `PENDING`; policy choice cannot be inferred from code or test names. |
| OG-M1A-02 | Designate the accountable catalogue/policy owner and authorized publisher/root identity. | A named, verifiable governance principal owns the catalogue, not a caller, generic AI, or the producer being evaluated. | `PENDING`; no trust root evidenced in the bounded sources. |
| OG-M1A-03 | Define which identities may issue each class of operational block and how producer identity/permission is verified. | Explicit allowlisted producer authorization bound to authenticated provenance; schema validity alone is insufficient. | `PENDING`; must be separate from `producer_id` text. |
| OG-M1A-04 | Designate the trusted operation-to-target registry/resolver owner and the binding source for real registered implementations. | Server-side resolution; ignore caller-supplied target for the decision; no locally guessed route labels. | `PENDING`; existing source review found no authoritative versioned resolver in the bounded paths. |
| OG-M1A-05 | Approve catalogue versioning, distribution, retirement/revocation and audit responsibility. | Versioned, integrity-verified publication and explicit revocation; revoked/unsupported versions fail closed. | `PENDING`; a digest by itself is not an authority chain. |
| OG-M1A-06 | Designate who can independently release a particular governance block and the proof required. | Release is a separate block-bound artifact issued by the trusted owner of that block; the reader/read approval cannot release it. | `PENDING`; Entry 274 forbids a read decision from releasing a block. |
| OG-M1A-07 | Approve treatment/migration of versionless legacy records. | Preserve legacy blocks as blocking; no automatic migration or wildcard/empty-to-GLOBAL coercion. | `PENDING` for any future migration; interim behavior is fail-closed. |

### Not new Owner decisions

These are derived engineering/documentary requirements under the existing Entry 274 and fail-closed intent. They must be included in the amended design and later acceptance matrix, but they are not separate governance ballots unless the Owner changes policy:
- make both selector fields required and distinguish absent from empty;
- define the meaning of “consistent” algorithmically;
- add the `GLOBAL` + valid exact-mismatch rows;
- ignore caller-supplied `operation_scope` for authority;
- make `BlockEvaluation` non-bearer and non-authorizing;
- evaluate/account for every active block and preserve every denial reason;
- distinguish parse/schema failure from recognized schema with incomplete fields;
- add synthetic cases for unknown-target+assistant-mismatch, alias conflicts, unauthorized producer, stale/future/revoked versions, mixed policy versions and multi-block aggregation;
- make acceptance of the catalogue trust criterion a prerequisite for any implementation authorization.

These repairs may still require independent review of the revised document; that is quality assurance, not a new policy choice.

## 6. Implementation acceptance gates — not authorized now

No implementation work follows from this amendment. If separately authorized in the future, minimum documentary gates are:
1. Owner/governance adjudicates OG-M1A-01..07 or explicitly delegates named decisions.
2. Catalogue and producer trust root, authorization checks, version lifecycle and revocation are demonstrable from an authorized source.
3. Trusted operation-to-target mappings are tied to real registered call sites/implementation identity; caller input cannot choose the target.
4. Selector evaluator consumes only authenticated typed records and has a complete deterministic decision table.
5. All active blocks are evaluated and all outcomes retained; no ordering-based bypass.
6. Entry 274's authority boundaries remain intact; independent release remains separate.
7. Synthetic conformance cases cover the decision table, cross-product failures, legacy formats, trust/version errors, multiple blocks and result-code precedence. Tests are only proposed here and must be separately authorized before execution.
8. Full source/runtime/testing state is independently verified against the exact candidate and revision; no claims derived solely from owner reports or proposal text.

## 7. Current state and next transition

```text
PARENT_CONCEPT=UAAL-ROOT-001
M1A_SCOPE_MODEL=PROPOSED; NON_AUTHORITATIVE
SELECTOR_SEMANTICS=CONJUNCTIVE_RECOMMENDATION; PENDING_ADOPTION
OWNER_GOVERNANCE_DECISIONS=OG-M1A-01..OG-M1A-07; PENDING
TECHNICAL_REPAIRS=DERIVED_AND_DOCUMENTED; NOT_IMPLEMENTED
TRUSTED_CATALOGUE_AND_RESOLVER=NOT_ESTABLISHED_IN_BOUNDED_SOURCE_SET
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```

Next transition: carry this normalized decision ledger and technical recommendation into the canonical front door. Present the Owner with the recommended semantic baseline and the genuinely unresolved authority decisions as one consolidated governance decision point. Do not send Codex another implementation task; do not repeat the same general Sonnet review; do not perform a broad source scan. Any future source implementation, tests, runtime, transport or block release requires separate authorization.


## 8. Owner decision made practical — one bundled design-baseline choice

To avoid burdening the Owner with seven disconnected policy questions, the coordinator recommends one consolidated design decision. The Owner may accept this complete *design baseline* or name only the clause(s) to change. Accepting this package does **not** authorize implementation, reads, tests, runtime, transport, merging, or block release.

### Recommended defaults bundled for approval

1. **Selector semantics:** adopt the conjunctive model and §2 table; `GLOBAL` applies only to its own dimension; exact mismatch proves non-applicability only after complete trusted resolution.
2. **Accountability:** the human IABV Project Owner/governance authority is the accountable owner of this scope policy and catalogue lifecycle. The actual authenticated runtime principal / trust anchor remains a separate evidence requirement and must not be guessed.
3. **Producer authorization:** no producer gains authority from a string ID or schema validity. Only an authenticated, explicitly allowlisted producer may issue a defined block class. Until the allowlist and credential/provenance verification are established, newly supplied untrusted records cannot authorize any permissive result; existing blocks remain active.
4. **Target resolver:** the authoritative operation-to-target registry belongs under the Owner/governance-controlled policy, is versioned, and is resolved server-side from the registered operation/implementation. Caller-supplied `operation_scope` is ignored for the authoritative decision. Until the actual registry and call-site bindings are evidenced, target identity is not established and protected reads remain denied.
5. **Catalogue integrity and revocation:** require a versioned integrity-protected publication plus verifiable authorization/trust anchor, explicit retirement/revocation, and deterministic rejection of unsupported or revoked versions. A digest alone is insufficient. The cryptographic mechanism and real trust-root material must be selected/verified in a future authorized engineering design; none is claimed implemented here.
6. **Independent block release:** only a separately authenticated governance authority designated for the specific block may issue an independently verifiable block-bound release artifact. The reader, read issuer, requesting agent, block producer or diagnostic receipt cannot release the block. If the real authority/mechanism is not available, release remains unsupported and denial continues.
7. **Legacy records:** no automatic migration. Preserve all existing blocks as blocking until a separately approved migration maps their provenance/scope or an independent valid release is supplied. Empty, missing, wildcard or free-form values must never be silently reinterpreted as `GLOBAL` or `NONE`.

### One-response acceptance protocol

The Owner can respond with exactly one of these:

- `ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE` — adopt the seven defaults above **as the normative design baseline only**. Exact runtime principal IDs, trust anchors, producer bindings, resolver mappings, implementation and tests remain unverified/unimplemented and gated.
- `ACCEPT_WITH_AMENDMENTS: ...` — accept the package except for the explicitly named clauses and replacement rules.
- `REJECT_M1A_BASELINE: ...` — preserve the current proposed state and provide the reason or alternative contract.

Silence, “proceed,” a model's review verdict, or saving this document is not policy adoption. On acceptance, the coordinator must update the decision ledger and write one consolidated versioned contract that traces directly to UAAL-ROOT-001 and Entry 274; only then should any implementation-specific authorization be considered separately.

```text
BUNDLED_OWNER_DECISION=NOT_RECEIVED
DESIGN_BASELINE_ADOPTION=PENDING
IMPLEMENTATION_AUTHORITY=NOT_GRANTED
TRUST_ANCHOR_VERIFICATION=REQUIRED_BEFORE_IMPLEMENTATION
READ_LIST=FAIL_CLOSED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
```
