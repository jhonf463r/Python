# M1A — Design a proposed versioned operational-block scope model (2026-10-22)

## Routing and authorization

The Owner has explicitly asked the coordinator to proceed toward a solution and provide the next AI prompt. This authorizes the next **design-only proposal task**, not source-code implementation, adoption of a new policy, tests, runtime, transport, or release of any block.

- North star: `GOVERNED_IABV_CODEX_BRIDGE`
- Prior active task: `M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`
- Prior M1 code repair disposition: `BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE`
- New active task: `M1A_DESIGN_PROPOSED_VERSIONED_OPERATIONAL_BLOCK_SCOPE_MODEL`
- First actor: Codex in the existing development session, as design author only.
- Next actor: independent adversarial reviewer (prefer Sonnet 4.6 in Antigravity if available; otherwise configured OpenCode or another independently invoked reviewer). Availability is `OWNER_REPORTED` until actually verified.
- Deliverable: a complete proposal in Codex's response; do not modify the candidate or claim the proposal is authoritative.
- Governance remains: `KEEP_BLOCKED`.

## Plain-language problem statement

The system currently carries `assistant_kind` and `target_scope` as strings. WorldModel creates examples of target strings; the MCP route gate uses local matching logic and the candidate contains a coded known-scope list. This is not the same thing as a governed, versioned policy specifying which labels are valid, what a real registered operation targets, how both dimensions combine, and what must happen when one dimension is unknown or inconsistent.

The gap is not solved by adding more strings to an allowlist. We need a reviewed proposal for a canonical model, a trusted resolution path, explicit decision semantics and a versioning/migration scheme. Until the proposal receives independent review and explicit Owner/governance adjudication, it is only a proposal and MUST NOT control runtime behavior.

## Allowed evidence set

Read these public GitHub sources, plus any precise definition they directly reference if needed:
1. [CURRENT-STATE.md](./CURRENT-STATE.md)
2. [AGENTS.md](../../AGENTS.md)
3. [M1 authority-check receipt](./CHAT-ARCH-2026-10-22-M1-Codex-authority-check-receipt.md)
4. [M1 scoped-read review and continuity handoff](./CHAT-ARCH-2026-10-22-M1-scoped-read-review-and-next-chat-handoff.md)
5. [Entry 274 — consolidated read-decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md)
6. Pinned public source at base `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`:
   - `IABV_v1.5/src/iabv_v15/domain/models.py`, blob `a9033d21052c519e09f482097599c704a62ea916`
   - `IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py`, blob `ba0b5f5d6233330b549e09863975c77c0db735d6`
   - `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`, blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`

Do not rerun broad inventories, tool inventories or the previous general audit. Do not inspect any local checkout or the candidate filesystem. The prior candidate identity is only `OWNER_REPORTED`.

## Design questions the proposal must answer

The proposal must define and justify, without hiding unresolved governance choices:

1. **Schema and policy versioning.** Give the proposed schema ID/version, policy version, compatibility rules, how a running server declares its version, and how unknown/future versions are rejected. Mark all proposed version strings as placeholders until accepted.
2. **Typed vocabulary.** Define the difference between an assistant/route identity and an operational target scope. Propose canonical identifiers, provenance/ownership for each identifier, alias/deprecation rules, and whether free-form strings can ever authorize a mismatch. Do not treat examples in the code as a complete registry.
3. **Trusted operation-to-target resolution.** Propose how each registered tool's operation identity maps to its target scope. The requesting caller must not be able to choose an arbitrary target label. State which identity source can be trusted, what evidence is still missing, and which operations remain unresolved.
4. **Dimension-combination semantics.** Provide a decision table for `assistant_kind` and `target_scope`, including global/empty/wildcard metadata, known mismatch, unknown or malformed values, partially evaluable records, conflicts, missing operation identity, and multiple simultaneously active blocks. Do not assume a mismatch on one dimension makes the other dimension irrelevant. Every non-applicability decision must be justified by the proposed authority model.
5. **Fail-closed stable outcomes.** Distinguish confirmed applicable block, proven non-applicable block, unevaluable block metadata, missing scope model/version, untrusted target resolver and independent release unsupported. Do not merge these into an ambiguous boolean.
6. **Producers and migration.** Map observed `_block_records()` producers to proposed identifiers using evidence, and mark each mapping as CONFIRMED, PROPOSED or UNRESOLVED. Explain what happens to unmapped producers: they must not be silently treated as non-applicable. Define an incremental migration path that keeps reads denied until the required model is implemented and reviewed.
7. **Governance ownership.** Identify who is supposed to own policy approval, scope registration, target resolution and any separate block-release attestation. Do not invent a principal, identity provider, signing key or runtime authority. Mark missing decision owners as explicit Owner/governance questions.
8. **Conformance cases (not executed).** Propose synthetic tests that distinguish unknown from non-applicable, cover cross-dimension combinations and real registered call sites, and verify fail-closed behavior. Tests may be specified only; do not create or execute them.
9. **Acceptance criteria and no-go conditions.** Specify what an independent reviewer must be able to verify before the model can be accepted and before a separate implementation task may be opened.

## Required output from Codex

Return a complete, self-contained Markdown proposal with:
- a short executive explanation in plain Spanish;
- sources and exact symbols/line locations where available;
- a proposed model specification and decision table;
- a registry/mapping table that clearly separates observed evidence from proposed and unresolved entries;
- explicit Owner/governance decisions needed;
- a threat/ambiguity analysis;
- migration and acceptance criteria;
- a concise reviewer checklist;
- an evidence ledger using `HEAD_SOURCE`, `OWNER_REPORTED`, `PROPOSED`, `UNRESOLVED` and `NOT_FOUND_IN_BOUNDED_SOURCES` accurately.

If there are multiple defensible policy choices, present them as alternatives and recommend one with rationale, but do not silently convert that recommendation into approved policy. Any mandatory Owner decision must be plainly marked `OWNER_DECISION_REQUIRED`.

## Hard exclusions

- Design/documentation only. Do not modify code, tests, candidate files or canonical documents.
- No test/build/lint/script/runtime/process/MCP/transport execution.
- Do not access the Owner's dirty checkout, any `data/`, SQLite, secrets, `.env` or local candidate filesystem.
- No authentication/setup/install/new spend or configuration changes.
- No commit, push, PR, merge, deploy or live-block release.
- Do not state or imply that the proposed policy is already authoritative.
- Keep reader/list tools fail-closed and `GOVERNANCE=KEEP_BLOCKED`.

## Stop condition

If the bounded public sources are insufficient to make a grounded proposal, state exactly which policy choices require the Owner/governance authority. Do not invent current facts or claim a working capability. Stop after delivering the proposal for independent review.
