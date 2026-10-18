# IABV / UAAL / R10 — Start here for the current task (2026-10-18)

**Use this file as the current entrypoint before relying on older CHAT-ARCH routing text.** It supersedes earlier 2026-10-17 instructions that say the only possible next step is to recover the missing original Claude report. That original remains missing; a new, explicitly labeled coordinator reconciliation has now been regenerated and persisted.

## Canonical current report

Read first: [R10 v0.7.4 — Coordinator reconciliation regenerated from the available report](https://github.com/jhonf463r/Python/blob/6ccf63ad93ef4946c5fcccdc3f42951775f96e6e/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-18-r10-v074-reconciliation-regenerated.md).

Report source attachment in the 2026-10-18 ChatGPT session:
- `Markdown pegado(4).md`, 93,927 bytes, SHA-256 `d7a98f45056d1c9d19a021ce46aa053303ef2ac63f30d7cb1eb6a919749dc09e`.
- This hash identifies the supplied corrected reconciliation text only. It does **not** identify the missing original Claude report or the v0.7.4 ZIP.

## Current truth

- Original `R10_V0_7_4_CLAUDE_INDEPENDENT_DELTA_REVIEW_FULL_2026-10-17.md`: `NOT_RECOVERED / UNRESOLVED`; declared 42,216 bytes and prefix `d1968df6…` remain `OWNER_REPORTED / HASH_UNVERIFIED`.
- Supplied corrected reconciliation: available and hashed as a current-session attachment; it is not the lost original.
- v0.7.4 relay content commit: `ad5c094fa3e7e4d1989079983f8f6c05f3296551`.
- v0.7.4 relay index commit: `191803340e1c78c92125b871a6a41589dc874163`.
- v0.7.4 current verdict: `REQUIRES_REPAIRS / NOT_ACCEPTED`.
- Current independent text spot-check verified 99 rows (T123–T221), all `NOT_RUN`; three column pairs duplicate across 99/99 rows; 90 rows use generic no-crash text; the 24 rows T198–T221 repeat the generic falsifier.
- Material row repairs: T134, T179, T184, T200, T205, T210, T212; T221 must be split into discriminating sequential numeric cases (start with T221 and T222; continue numbering as needed). The full reasoning is in the linked report.
- R10 v0.7.2 = `FAIL`; v0.7.3 = `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.5 = `NOT_CREATED / NOT_REVIEWED`.
- All matrix tests = `NOT_RUN`; product code execution/build/runtime = `NOT_RUN`.
- Physical bridge = `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.

## Mandatory cross-chat persistence rule

The project must not rely on a critical report being remembered or reattached after a chat change. For every material decision/handoff:

1. Save the complete report or a sufficient, provenance-labeled decision record to the canonical GitHub continuity branch before closing the handoff.
2. Record exact path, immutable commit SHA, file SHA-256 where bytes are locally available, source provenance and what was not verified.
3. Update this Start Here file in a new sequential commit so the next chat has one durable entrypoint.
4. Verify the new report and pointer by reading them back from GitHub.
5. New chats read this file first, then the pinned report and relevant source artifacts. Never infer that an attachment, Windows path, temporary directory, or local file transfers between agents/chats.
6. A regenerated coordinator report must remain labeled as regenerated; it must never be relabeled as the missing original.
7. Do not start authoring v0.7.5 merely because a replacement report exists. The owner must explicitly accept this regenerated coordinator reconciliation as the documentary substitute for the missing original report first; governance remains blocked unless and until that decision is recorded.

## Next actor and stop conditions

**Current actor:** Owner decision on whether to accept the regenerated coordinator reconciliation as the substitute documentary basis for the lost original. No need to repeat searches already declared exhausted unless new evidence/source scope appears.

If that substitution is accepted, **next actor:** Codex local, documentary-only author of a new immutable R10 v0.7.5 candidate, using the actual commit-pinned v0.7.4 input artifacts. A separate Claude/Sonnet conversation must then perform an independent review of the exact resulting candidate and, where obtainable, the actual ZIP bytes. If binary access fails, the reviewer must disclose it rather than imply ZIP verification.

Restrictions remain:
- Preserve `handoff/r10-v074-review-20261017`.
- Keep PR #467 open, Draft and unmerged.
- Do not revisit `relay-staging\\IABV_v1.5\\data`; no contents or SQLite were inspected, per Codex's report, and no further traversal is authorized.
- Do not inspect or modify the dirty local IABV checkout, `data/`, SQLite, M0A, dispatcher, physical bridge or Packages B–E.
- No product code, tests, build, runtime, probes or new spend.

`GOVERNANCE = KEEP_BLOCKED`.
