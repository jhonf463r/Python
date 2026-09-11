# IABV v1.5 — CHAT-ARCH: Canonical Historical Knowledge Entry Point

## PURPOSE

This directory is the canonical entry point for durable knowledge recovered from ChatGPT / Claude / Devin / Codex and related engineering conversations.

The purpose is **not** to reproduce chats. The purpose is to preserve enough structured knowledge that a future AI can reconstruct the relevant state of IABV for a new objective without depending on the deleted chat transcript.

The repository is the durable source of truth for historical observations, evidence, claims and epistemic status, false positives and refuted interpretations, negative knowledge and anti-patterns, experiments and their limits, decisions and rejected alternatives, ideas that never became tasks or code, architectural deductions and latent knowledge, cross-IA interactions and learning transfer, provenance and branch/commit relationships, current gates and blockers, and the evolution of the engineering method.

## CRITICAL RULE

**Do not read every archive on every new task.**

A future chat must first identify its current objective, then use the objective-routing index to discover relevant historical records, reconcile those records against current repository/runtime evidence, and activate only the context that can materially change the current decision.

The complete archive remains available for deep reconstruction, but selective activation is the default.

## CANONICAL NAVIGATION LAYER

Read these files first when continuity is required:

1. `CONTEXT-INDEX.md` — objective → historical knowledge routing map.
2. `CURRENT-STATE.md` — reconciled current project state and active frontiers.
3. `SYMBIOSIS-MAP.md` — cross-IA learning, role evolution, and collaboration dynamics.
4. `ARCHIVE-REGISTRY.md` — registry of historical records, including legacy records outside this directory.

## TWO-LAYER HISTORY MODEL

### Layer A — Canonical navigation / synthesis

The files above are maintained as navigation and reconciliation artifacts. They do not replace source history. They answer: where to look for a given objective, which history matters, what is proven/disproven/unresolved, which ideas remain unimplemented, which failures must not be repeated, what was learned across AIs, and which current branch/commit/runtime is authoritative.

### Layer B — Source historical records

Existing `CHAT-ARCH-*` files under all of these locations remain historical source records unless explicitly superseded by evidence:

- `IABV_v1.5/docs/history/CHAT-ARCH/`
- `IABV_v1.5/docs/history/`
- `IABV_v1.5/docs/CHAT-ARCH-*.md`

They are not silently rewritten merely to normalize names or IDs.

## SOURCE-HIERARCHY RULE

For current technical truth, current source/contracts/runtime evidence outranks historical conversation claims.

For historical reasoning and project evolution, archive records preserve what was believed, discovered, rejected, and learned at the time.

When sources disagree, record the reconciliation. Never silently erase the disagreement.

## EPISTEMIC LADDER

Always distinguish:

`idea → design → code exists → wired → test passes → production path exercised → runtime observed → adversarially verified → causal effect demonstrated → independently reproduced`

A historical claim never upgrades itself merely because later prose repeats it.

## CROSS-CHAT CONTINUITY CONTRACT

A new chat should be able to reconstruct from GitHub alone, for its active objective:

1. the relevant historical records;
2. the important experiments and their limits;
3. current source/branch/commit state;
4. relevant false positives and negative knowledge;
5. relevant unimplemented ideas and deductions;
6. applicable cross-IA collaboration lessons;
7. the active gate/blocker and its last independently verified state;
8. the smallest unresolved uncertainty driving the next action.

It should **not** need the previous chat to know these things.

## MEMORY WRITEBACK RULE

A chat creates durable history when it produces materially new knowledge: a verified observation, correction, experiment, failure mode, architectural deduction, decision, rejected option, cross-IA learning, or other knowledge that changes future work.

Routine repetition does not require a new archive record.

When new knowledge changes the active model, update the relevant synthesis layer and preserve the source evidence supporting the change.

## DELETION SAFETY

An archived chat is not safely deletable merely because an archive file exists.

Deletion is safe only when the durable repository state contains enough provenance and knowledge to reconstruct the material content of the chat and the remote copy has been independently read back.

`DELETE_SAFE=YES` must never be inferred from local file existence alone.

## CURRENT REPOSITORY FACT

At creation time, GitHub `main` pointed to:

`4597e3323d397c57f6759fcc03402ebe5a80d6c9`

The latest recorded P0-B validation target is **not** main. The relevant branch target is:

`origin/audit/p0-b-repopath-on-hardened-base`

`c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3`

This distinction is intentional and must be preserved by future continuity work.
