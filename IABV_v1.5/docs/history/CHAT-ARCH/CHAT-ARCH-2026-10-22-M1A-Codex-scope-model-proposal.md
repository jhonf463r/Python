# M1A — Operational-block scope model proposal (Owner-supplied Codex response, 2026-10-22)

## Provenance and status

This document preserves the proposal pasted by the Owner from Codex. It is `OWNER_SUPPLIED`, not independently authored or accepted by the coordinator. Design verdict reported by its author: `PASS_WITH_REPAIRS`.

```text
DESIGN_VERDICT=PASS_WITH_REPAIRS
SCOPE_MODEL=PROPOSED_PENDING_INDEPENDENT_REVIEW_AND_OWNER_ADJUDICATION
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

The proposal defines a policy for review but does not establish a current policy. The owner or competent authority still needs to designate who controls the catalogue, resolves targets, and adjudicates scope decisions. Proposed scopes cannot authorize routes or reads until that decision is independently reviewed and explicitly adjudicated.

## Sources and evidence limits

The proposal cites:
- [CURRENT-STATE.md](./CURRENT-STATE.md) and [AGENTS.md](../../AGENTS.md), which limit the task to design and preserve the block.
- [M1 authority-check receipt](./CHAT-ARCH-2026-10-22-M1-Codex-authority-check-receipt.md) and [M1 static review handoff](./CHAT-ARCH-2026-10-22-M1-scoped-read-review-and-next-chat-handoff.md), which record the blocker and the candidate's provenance limitations.
- [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), a normative documentary contract, not proof of implementation.
- Pinned public source at `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`:
  - `domain/models.py`, blob `a9033d21052c519e09f482097599c704a62ea916`;
  - `world_model_service.py`, blob `ba0b5f5d6233330b549e09863975c77c0db735d6`;
  - `server.py`, blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`.

Evidence distinction: documentary requirements are not accepted runtime policy. The candidate directory, any active server and runtime behavior are not independently verified by this coordinator.

## A. Proposed model and versioning

Provisional, not approved:
- `schema_id = "iabv.operational_block_scope"`
- `schema_version = "1.0.0"`
- `policy_id = "iabv.operational_block_applicability"`
- `policy_version = "1.0.0"`

Schema version defines structure and types; policy version defines dimension-combination semantics. A server would declare both versions plus the catalogue revision/digest it loaded. Missing, unknown, future or incompatible versions are rejected with stable outcomes such as `SCOPE_MODEL_UNAVAILABLE` or `SCOPE_VERSION_UNSUPPORTED`; never silently interpreted as current. Minor versions may add non-semantic optional fields; changes to types, catalogue meaning or combination rules require an appropriate reviewed version increment. No automatic migration of legacy records is proposed.

Suggested structure:

```text
OperationalBlockV1 {
  schema_id, schema_version, policy_version, registry_digest,
  block_id, block_revision, status,
  assistant_selector: GLOBAL | EXACT(registered_assistant_id),
  target_selector: GLOBAL | EXACT(registered_target_scope_id),
  evidence_refs, producer_id, issued_at, provenance
}
```

`GLOBAL` is a typed explicit selector, not equivalent to an empty string or `*`. Exact IDs must exist in the catalogue loaded for the declared version. Legacy free-form string records are not automatically valid in this model.

Suggested structured decision:

```text
BlockEvaluation {
  result_code, block_id, block_revision,
  schema_version, policy_version, resolved_operation_id,
  resolved_assistant_id, resolved_target_scope_id, evidence_refs
}
```

The evaluator returns structured outcomes for every block rather than reducing uncertainty to a boolean.

## B. Proposed typed catalogue

Assistant/route identity and operational purpose are separate dimensions. Existing examples must not become an official catalogue by assumption.

| Dimension | Proposed form | Current evidence | Disposition |
|---|---|---|---|
| Assistant/route | Registered ID, e.g. `assistant:<id>` | `HEAD_SOURCE`: values are read from `tool.assistant_kind`; registered route labels include `audit`, `gpu_benchmark`, `site_crawler`, `chatgpt_web` | Examples only, not an official catalogue |
| Operational purpose | Registered ID, e.g. `operation:<id>` or `target:<id>` | `HEAD_SOURCE`: `consult_external`, `consult_<assistant_kind>`, `heavy_local_model`, `ui_focus_interaction` | Examples only |
| Global scope | Typed `GLOBAL` selector | `HEAD_SOURCE`: some records have empty fields; this does not establish authoritative global semantics | `PROPOSED`; legacy empty values remain ambiguous |
| Alias/deprecation | Versioned `alias → canonical ID` registry | `UNRESOLVED`: no authoritative registry found in bounded sources | Requires authority decision |

Each entry should identify stable ID, description, dimension, registering authority, provenance, status, introduction version, aliases and deprecation version/date. A new string does not become valid merely because it occurs in tests or a producer. Catalogue ownership and its authoritative data source are `OWNER_DECISION_REQUIRED`.

## C. Proposed trusted target resolution

The client invokes a registered operation; the server resolves the operation from an approved, versioned internal operation registry, then derives its assistant/route and operational purpose. Caller-supplied arguments such as `operation_scope` must not choose or override the target to be evaluated.

Resolution fails closed if the operation is unregistered, unmapped, version-incompatible or inconsistent with trusted server configuration. Targets must not be guessed from names, prefixes or client-provided text. Which component owns and distributes this registry, how its version is authenticated, and which identity sources can be trusted are `OWNER_DECISION_REQUIRED`. No existing trusted resolver is evidenced in the inspected sources.

## D. Proposed combination rules

The proposal says both dimensions must be evaluated. Non-applicability may be declared only when a trusted operation target is resolved and the versioned model proves that the block does not apply. A mismatch on one dimension must not hide an unknown or contradictory second dimension.

| Active block and resolved target | Proposed outcome |
|---|---|
| Both selectors are `GLOBAL` | `BLOCK_APPLIES` |
| One selector is `GLOBAL`, the other matches exactly | `BLOCK_APPLIES` |
| Both exact, valid, consistent selectors match | `BLOCK_APPLIES` |
| Both exact, valid and consistent selectors differ from target | `PROVEN_NOT_APPLICABLE` |
| One dimension differs while the other matches | `BLOCK_SCOPE_UNEVALUABLE`; resolve apparent contradiction rather than discard |
| One dimension differs while the other is empty, unknown, malformed or unregistered | `BLOCK_SCOPE_UNEVALUABLE` |
| Empty or wildcard in a legacy record with no authenticated semantics | `BLOCK_SCOPE_UNEVALUABLE`; do not assume global or none |
| Unknown ID, missing version or catalogue digest mismatch | `SCOPE_MODEL_UNAVAILABLE` or `SCOPE_VERSION_UNSUPPORTED` |
| Trusted operation or route identity is missing | `TARGET_IDENTITY_UNTRUSTED` |
| Dimensions conflict or a producer has no mapping | `BLOCK_SCOPE_UNEVALUABLE` |
| Multiple active blocks | Evaluate all; if one applies, deny unless an independent valid release covers that block. If any cannot be evaluated, deny |
| No active blocks and model/target valid | `NO_APPLICABLE_BLOCKS_PROVEN`; continue only through remaining gates |
| Applicable block with no verified independent-release mechanism | `BLOCK_RELEASE_UNSUPPORTED`; deny |

The table intentionally proposes conservative handling. The distinction between conjunctive matching, conflicting dimensions and proof of non-applicability needs adversarial review and explicit policy adjudication; the table is not adopted policy.

## E. Proposed results and authority limits

- `BLOCK_APPLIES`: confirmed applicable block.
- `PROVEN_NOT_APPLICABLE`: mismatch proven by the trusted model and target.
- `BLOCK_SCOPE_UNEVALUABLE`: partial, unknown, malformed or contradictory scope.
- `SCOPE_MODEL_UNAVAILABLE`: model/catalogue absent.
- `SCOPE_VERSION_UNSUPPORTED`: unsupported version.
- `TARGET_IDENTITY_UNTRUSTED`: operation/target was not resolved by a trusted source.
- `BLOCK_RELEASE_UNSUPPORTED`: independent release mechanism unavailable.
- `NO_APPLICABLE_BLOCKS_PROVEN`: no block applies under a valid model and trusted target.

A read approval does not change block applicability. The authority for approving a read and any authority that releases an operational block must be independent. The owner of that release authority and any implementing mechanism remain `UNRESOLVED`; absent evidence, an applicable block stays active.

## F. Proposed producer/operation mapping

| Observed source | Evidence status | Future mapping |
|---|---|---|
| `_block_records()` emits `consult_external` for network state | `HEAD_SOURCE` | `PROPOSED`: map to an approved external-operation purpose ID; authority pending |
| `route_scope = f"consult_{tool.assistant_kind}"` | `HEAD_SOURCE` | `UNRESOLVED`: string construction does not prove registered identity |
| `gate.required_for[0]` copied to `target_scope` | `HEAD_SOURCE` | `UNRESOLVED`: upstream contract is not shown to guarantee a registered ID |
| RAM/CPU/throttling risks produce `heavy_local_model` | `HEAD_SOURCE` | `PROPOSED`: map to a reviewed heavy-local-model purpose |
| Unconfirmed UI focus produces `ui_focus_interaction` | `HEAD_SOURCE` | `PROPOSED`: map to a reviewed UI-interaction purpose |
| MCP audit tools use `assistant_kind="audit"` | `HEAD_SOURCE` | Route identity observed; repository-read purpose is not established by this field |
| `read_repo_file` / `list_repo_directory` invoke gate with `audit`, without `operation_scope` in pinned base | `HEAD_SOURCE` | `PROPOSED`: register read and listing operations separately; do not wire until mapping approved |
| Labels inferred only from tests or names | `NOT_FOUND_IN_BOUNDED_SOURCES` | Exclude absent provenance and authority |

Proposed semantic mappings are not decisions that those mappings should become operative. The reported candidate diff does not prove the mapping trustworthy or connected to production call sites.

## G. Owner/governance decisions required

1. `OWNER_DECISION_REQUIRED`: who owns the catalogue and can approve additions, aliases, deprecations and version changes.
2. `OWNER_DECISION_REQUIRED`: what authenticated identity approves policy and how it is verified independently of the requesting agent.
3. `OWNER_DECISION_REQUIRED`: which trusted component registers and resolves operations and targets.
4. `OWNER_DECISION_REQUIRED`: whether to adopt the proposed handling of global/exact selectors and conflicts, or a reviewed alternative.
5. `OWNER_DECISION_REQUIRED`: who may issue independent block releases and whether a legitimate mechanism exists.
6. `OWNER_DECISION_REQUIRED`: how the catalogue is versioned, distributed, revoked and audited.
7. `OWNER_DECISION_REQUIRED`: how to handle legacy records without versions; proposal treats them as unevaluable and blocking until migration is approved.

No authority is inferred for Codex, the file reader, the active MCP server or the Owner without an explicit decision. Conversational acceptance of design work does not make the rules current policy.

## H. Proposed migration and validation

1. Preserve current safe state; reads/listings remain denied absent a verifiable read decision.
2. Independently review the design and resolve governance questions before implementation authorization.
3. Define approved catalogue entries and a complete operation-to-route/purpose registry. Unmapped producers remain unevaluable, never silently non-applicable.
4. Preserve legacy records as blocking; transformations require approved rules, provenance and auditability. Do not silently reinterpret empty strings or wildcards.
5. Use a separate implementation authorization after policy acceptance; each operation must consult trusted model/resolver and produce a correlatable decision/receipt.
6. Proposed synthetic tests (not created or executed): every combination row and both dimension evaluation orders; cross-product match/mismatch/conflict; typed global versus legacy empty/wildcard; unknown/malformed/missing/future/incompatible versions; client-supplied target differing from server-resolved target; every real producer and registered call site; multiple blocks and invalid/expired/wrong-block releases; no read/list when model, resolver, ledger or independent decision is unavailable.
7. Acceptance criteria: independent adversarial review, recorded Owner/governance decisions, catalogue version and authority verifiable, target not caller-controlled, unknown/conflict cases fail closed, discriminating tests pass in a separately authorized phase, and read authority stays separate from block release. Approval of the model alone does not authorize execution, tests, transport, local access or release.

## Threats and ambiguities identified by the proposal

- Free-form strings do not prove provenance.
- `required_for[0]` and `tool.assistant_kind` may propagate unregistered values.
- Client-controlled scope selection can bypass a gate.
- A local gate list can diverge from producer or consumers.
- Empty and wildcard legacy values may be misinterpreted as authority.
- Dimension precedence can conceal a coincident or unevaluable second dimension.
- Versioning without authorized publication, revocation and verification is only nominal.
- Scope evaluation does not prove read approval, live checkout identity, filesystem containment, durable receipts or independent block release.

## Evidence ledger

| Claim | Evidence status |
|---|---|
| `OperationalBlockRecord.assistant_kind` and `target_scope` are strings in pinned blob | `HEAD_SOURCE` |
| `_block_records()` emits literal and upstream-derived labels | `HEAD_SOURCE` |
| Pinned base implements local matching but no proven versioned catalogue | `HEAD_SOURCE` |
| Read/list call sites use `audit` in pinned base | `HEAD_SOURCE` |
| Entry 274 requires versioned authority, explicit rules and fail-closed uncertainty | `HEAD_SOURCE` for documentary requirement; not implemented capability |
| Prior local candidate root/status | `OWNER_REPORTED`; not re-inspected for this proposal |
| Proposed schema/catalogue/resolver/combination | `PROPOSED` |
| Catalogue owner, resolver authority and release principal | `UNRESOLVED` |
| Authenticated issuer / independent release implementation | `UNRESOLVED` |
| Implementation, tests and live runtime behavior | `NOT_FOUND_IN_BOUNDED_SOURCES` / `UNPROVEN` |

## Proposal's own next step

The proposal itself calls for an independent adversarial reviewer to try to falsify its dimension semantics, target resolution and legacy migration. The owner or competent authority must then adjudicate the governance decisions. Until both steps occur, the document remains a proposal; M1 is blocked, reads/listings remain closed, and no implementation is authorized.
