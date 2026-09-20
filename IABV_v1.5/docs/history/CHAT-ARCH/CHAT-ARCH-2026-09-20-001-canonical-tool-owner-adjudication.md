# IABV v1.5 — CANONICAL TOOL OWNER ADJUDICATION — 2026-09-20

## PURPOSE

Preserve the independent Codex adjudication that closes the technical ownership ambiguity around `assistant_kind ↔ tool_id` for the I0 universal resource seam.

## PROVENANCE

- Repository: `jhonf463r/Python`
- Canonical main at adjudication: `6dd3e8dc4ed282b315590e609a16ada8709ff3a1`
- Experimental branch under examination: `i0-authorization-boundary-preserve-2026-09-19`
- Experimental commit under examination: `bc7454e1c5dfaa7793baa8a23ec3cbeed1d4afcd`
- Actor: Codex
- Role: bounded technical/ownership adjudication
- Implementation performed: NO

## ADJUDICATION

**CANONICAL OWNER = ToolCard declaration + ToolRegistry resolution**

`ToolCard` is the canonical declarative record of a tool. The relevant dimensions include:

- `tool_id`
- `adapter_key`
- `capabilities`
- `availability`
- `metadata.assistant_kind`

`ToolRegistry` is the legitimate runtime query owner for:

`assistant_kind → candidate ToolCard(s) → canonical tool_id(s)`

The resource scanner is not the semantic owner of assistant aliases.

## DIRECT EVIDENCE

The current Devin ToolCard declares:

`assistant_kind=devin`
`tool_id=devin_api`
`adapter_key=devin_api`

The current registry already searches ToolCards by `metadata["assistant_kind"]` inside `pick_card_for_task()`.

The experimental resource path currently passes `assistant_kind` directly into resource ranking, while `universal_resource_to_worker()` projects:

`worker["tool"] = resource.tool_id`

and the ranking boundary compares the target against the worker tool identity. Therefore:

`devin != devin_api`

can exclude the correct universal resource before selection and prevent `credential_ref` propagation.

## DEPENDENCY DIRECTION

The desired direction is:

`Autonomy / router → ToolRegistry resolver → canonical tool_id set → account_resource_scanner ranking → UniversalResource → credential_ref`

The scanner must not import or call `ToolTeachService`.

## REJECTED OWNERS

### ToolTeachService

Rejected as canonical owner because it is a task-construction/execution layer and the scanner must not depend upward on it.

### Static domain mapping

Rejected because a static dictionary would duplicate mutable ToolCard catalog knowledge and cannot naturally express one-to-many assistant families.

### Scanner/provider matching

Rejected because it would make resource infrastructure interpret assistant aliases and become a second semantic resolver.

### Metadata-only consumers

Insufficient because the authoritative datum exists in the ToolCard, but runtime consumers need a centralized registry query.

## DUPLICATION FINDINGS

- `ToolTeachService._assistant_family_for_tool_id()`: scoped helper/prefix heuristic; it must not become global semantic authority.
- `TaskContextAssembler._assistant_kind_from_tool_id()`: legitimate historical-trace reconstruction scope, but incomplete and must not define global catalog identity.
- Adapter telemetry using `assistant_kind="devin_api"`: contract misuse if the field is intended to represent assistant identity; it is not the owner of selection and does not explain the resource-ranking seam.
- `ToolCard.metadata["assistant_kind"]`: canonical declaration.
- `ToolRegistry`: canonical lookup/resolution.

## MINIMAL FIX

The next implementation should:

1. expose/reuse a ToolRegistry query that resolves an `assistant_kind` to the matching ToolCard/tool_id set;
2. have the existing caller above resource ranking resolve the assistant identity before calling the scanner/ranker;
3. let `rank_workers_for_target()` operate on normalized tool identity or a permitted tool-id set;
4. preserve direct tool-id callers and legacy behavior where semantically valid;
5. propagate the selected universal resource unchanged, including `resource_id`, `provider`, `tool_id`, and `credential_ref`.

Do not put the mapping inside `account_resource_scanner.py`.

Do not add a new mapping service/class.

Do not make the scanner depend on `ToolTeachService`.

Do not change governance authority.

Do not change `SynapticRouter` ownership.

## GENERALIZATION

The design must support one assistant family mapping to multiple ToolCards, for example web/installed/API variants, rather than assuming a one-to-one static mapping.

The universal substrate should therefore support:

`assistant_kind → {tool_id_1, tool_id_2, ...}`

followed by resource ranking among the eligible normalized tool identities.

## CURRENT OPEN GATE

The ownership ambiguity is closed.

The implementation seam remains open:

`assistant_kind → ToolRegistry resolution → normalized tool identity set → rank_workers_for_target() → selected UniversalResource → credential_ref`

This is an implementation task, not an architecture task.

## NEXT ACTOR

**DEVIN**

Implement only the bounded catalog-resolver/resource-ranking seam described above, then provide exact commit/branch provenance and focused test evidence.

After implementation:

**SONNET** independently audits the artifact.

After artifact closure:

**DEVIN** performs the controlled Windows/runtime I0 connection phase.

After runtime:

**SONNET** independently audits the runtime evidence.

Opus remains reserved for a new, genuine architecture/ownership contradiction.
