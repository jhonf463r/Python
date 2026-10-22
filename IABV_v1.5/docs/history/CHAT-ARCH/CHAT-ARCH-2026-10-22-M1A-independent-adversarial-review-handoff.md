# M1A — Independent adversarial review handoff (2026-10-22)

## Goal and routing

The Owner supplied Codex's complete proposed operational-block scope model in chat. It is archived at [M1A Codex scope-model proposal](./CHAT-ARCH-2026-10-22-M1A-Codex-scope-model-proposal.md).

**Next actor:** an independent adversarial reviewer, preferably Sonnet 4.6 in Antigravity if the user confirms that it can be invoked. The claimed availability comes from prior Owner report and is `OWNER_REPORTED`, not independently tested by this coordinator. If that is unavailable, use a distinct configured OpenCode/other reviewer, not the same Codex session as sole reviewer.

**Review task:** attempt to falsify the proposal, not rewrite or implement it. Return specific findings with counterexamples and exact sections; include verdict `PASS`, `PASS_WITH_REPAIRS`, or `FAIL`. The proposal is not accepted policy.

## Required reading

1. [CURRENT-STATE.md](./CURRENT-STATE.md)
2. [AGENTS.md](../../AGENTS.md)
3. [M1A Codex scope-model proposal](./CHAT-ARCH-2026-10-22-M1A-Codex-scope-model-proposal.md)
4. [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md)
5. [M1 static-review handoff](./CHAT-ARCH-2026-10-22-M1-scoped-read-review-and-next-chat-handoff.md)
6. [M1 authority receipt](./CHAT-ARCH-2026-10-22-M1-Codex-authority-check-receipt.md)

Read only the cited public GitHub documents and directly relevant pinned sources if a claim needs checking. Do not perform a broad scan or inspect a local candidate.

## Highest-priority falsification questions

1. **Formal dimension semantics:** Does the proposal ever define whether `assistant_selector` and `target_selector` are conjunctive constraints, alternatives, or a conflict-aware policy? Is a mismatch in one dimension sufficient to prove non-applicability? The table says "both exact selectors differ" means `PROVEN_NOT_APPLICABLE`, while "one differs and one matches" means `BLOCK_SCOPE_UNEVALUABLE`. Determine whether that distinction follows from a coherent formal model or leaves policy undefined.
2. **Incomplete decision table:** What result applies when one selector is `GLOBAL` and the exact selector is valid but mismatches? What if assistant resolves but target is absent; target resolves but assistant does not; one dimension is unknown and the other is global; duplicate aliases resolve to conflicting IDs; multiple records use different policy versions; a valid non-applicability result coexists with another unevaluable active block?
3. **Meaning of conflict:** Is "one dimension matches and the other differs" actually a conflict or simply non-applicability under conjunction? What makes it conflict, and who approved that interpretation?
4. **Trusted operation mapping:** How is the operation registry authenticated and bound to the registered tool's actual implementation? Could a renamed/wrapped tool or misconfigured metadata claim a benign target? What source proves the resolver identity rather than just trusting another local table?
5. **Catalogue authority:** The schema proposes fields and digest but not a complete trust chain. Who signs/publishes it, how the signature/version is checked, how revocation works, and what happens when integrity protection is unavailable? Do not invent a principal; record decisions needed.
6. **Global/wildcard migration:** Can old empty values or `*` be misread while legacy and typed records coexist? Is explicit `GLOBAL` actually protected against untrusted producers? Are ambiguous legacy records always blocking across the transition?
7. **Stable outcomes and enforcement:** Does each status have a deterministic effect? Does `NO_APPLICABLE_BLOCKS_PROVEN` still defer to all other gates? Does a read approval ever incorrectly release an operational block? Are receipts diagnostic only or being confused with authority?
8. **Conformance matrix sufficiency:** Identify missing synthetic counterexamples, especially cross-product pairs, multiple blocks, stale policy versions, unknown target + assistant mismatch, and a producer emitting a newly seen value.

## Evidence and output requirements

- Treat the proposal as `OWNER_SUPPLIED` / `PROPOSED`; its self-reported `PASS_WITH_REPAIRS` is not the independent review verdict.
- Distinguish source facts (`HEAD_SOURCE`) from proposal, report and unresolved governance decisions.
- For every finding, state severity, exact proposal section/table row, a concrete counterexample, required repair, and whether it can be fixed without an Owner decision.
- Recommend the minimal repairs needed before Owner adjudication. Do not silently decide policy for the Owner.
- If the design is internally coherent only after selecting an unapproved semantic alternative, return `OWNER_DECISION_REQUIRED` rather than approval.
- Do not edit the proposal, modify source or tests, or make commits/PRs.

## Hard constraints

Design review only. No tests, builds, lint, scripts, runtime, process launches, MCP calls or transport. Do not access a local checkout, candidate filesystem, `data/`, SQLite, secrets or `.env`. No code edits, publication, merge, or block release. Keep `GOVERNANCE=KEEP_BLOCKED`, readers/listings closed, `IMPLEMENTATION=NOT_AUTHORIZED`, and `BRIDGE=BRIDGE_NOT_READY`.

## State after review

The review does not make the model authoritative. The next routing edge after an independent review is explicit Owner/governance adjudication of the unresolved policy decisions; implementation requires a separate authorization.
