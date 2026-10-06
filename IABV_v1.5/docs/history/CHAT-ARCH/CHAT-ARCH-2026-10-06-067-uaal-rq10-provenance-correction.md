# CHAT-ARCH-2026-10-06-067 — UAAL-RQ10 PROVENANCE CORRECTION / DIRTY WORKTREE

## STATUS

CANONICAL RECONCILIATION / PROVENANCE CORRECTION / ROUTING

## OBJECTIVE

Determine whether the RQ10 runtime observation is attributable to the executable baseline
`e46d8304167708bed0764d3bf2be8fd6643e8944`, or only to an uncommitted candidate overlay present in the Codex worktree.

## MATERIAL NEW EVIDENCE

Codex's RQ11 Phase 1 inspection reports that the candidate worktree:

`C:\Users\faber\.codex\worktrees\universal-ui-structure\Python\IABV_v1.5`

has uncommitted changes in:

- `src/iabv_v15/infra/mcp/server.py`
- `src/iabv_v15/services/adaptive/task_context_assembler.py`

relative to HEAD `e46d830...`.

Codex reports that the overlay:
- changes `cognitive_frame_translate` to use a no-refresh path;
- changes `build_perception_snapshot` so the observation path can avoid refresh;
- omits portable-context reconstruction for that safe observation path;
- exposes a projection of the produced PerceptionSnapshot.

Direct canonical GitHub inspection of the executable baseline `e46d830...` confirms that the baseline `TaskContextAssembler._world_model()` performs the normal `request_refresh(reason='perception_cycle', full=False)` after reading `current_model()`, and the baseline `cognitive_frame_translate` does not expose the reported `refresh=False` overlay parameter.

RQ05's canonical record already identifies the same two files as an **uncommitted candidate change** created to provide a no-refresh observation seam and explicitly states that candidate runtime behavior had not yet been proven.

## PROVENANCE CONSEQUENCE

The RQ10 result is therefore **NOT CLEANLY ATTRIBUTABLE to the executable baseline**.

It remains valid as reported runtime evidence from the candidate worktree, but its artifact identity is presently:

`e46d830 baseline + uncommitted candidate overlay ?`

The timing/identity relationship between the overlay and the exact RQ10 process start was not captured in the supplied RQ10 report. Therefore the stronger statement:

`RQ10 proves baseline e46d830 runtime behavior`

is not justified.

Do not silently promote the RQ10 result to baseline evidence.

## FACT / INFERENCE / ASSUMPTION

### FACTS

- Codex reports a dirty candidate worktree relative to `e46d830...`.
- The dirty files are precisely the two files previously identified by RQ05 as an uncommitted candidate observation seam.
- The canonical e46d830 source does not contain the reported no-refresh overlay behavior.
- RQ10 was reported as executed from that candidate workspace.
- No clean/dirty status, exact patch, or execution-time source fingerprint was captured as part of the RQ10 report.

### INFERENCE

RQ10 may have exercised the RQ05 candidate overlay rather than pure `e46d830...`.

### ASSUMPTION

None.

## RQ10 STATUS AFTER CORRECTION

RQ10 is reclassified from:

`LIVE-OBSERVED / PARTIALLY CLOSED against executable baseline`

to:

`LIVE-OBSERVED / CANDIDATE-VARIANT EVIDENCE / BASELINE ATTRIBUTION OPEN`.

Its runtime observation remains useful evidence for the candidate variant, but cannot yet close a baseline frontier.

The previously recorded RQ10 observations about:
`4350... → fa38... → PerceptionSnapshot fa38...`
remain preserved as reported candidate-runtime evidence.

## CURRENT FIRST OPEN EDGE

The first open edge is now a provenance edge:

`RQ10 runtime process → exact executable artifact / exact worktree diff → attribution`

Only after this edge is closed should the coordinator decide whether the RQ10 live PerceptionSnapshot observation can be transferred to the baseline frontier.

## MINIMUM NEXT ACTION

Static provenance reconciliation only.

Use the same Codex worktree to:

1. capture `git status --short`;
2. capture the complete diff of exactly:
   - `server.py`
   - `task_context_assembler.py`
3. identify whether those changes exactly match the RQ05 candidate described in its canonical record;
4. establish, from available session/runtime artifacts, whether the RQ10 MCP process could only have loaded the dirty overlay or whether a clean `e46d830...` process was used;
5. produce a source fingerprint for the executed files if available;
6. classify the RQ10 evidence as:
   - baseline-attributable,
   - candidate-overlay-attributable,
   - mixed/indeterminate.

No runtime execution is required for this phase.

## AUTHORIZATION

No fresh runtime authorization is required for this static provenance phase.

Do not start MCP.
Do not scan WorldModel.
Do not modify production code.
Do not commit the candidate overlay.
Do not alter the existing RQ10 runtime artifact.

## ROUTING DELTA

**Current actor: CODEX.**

Capability fit is repository/worktree provenance archaeology. This is not yet a Sonnet forensic audit because the primary problem is artifact attribution, and not a Devin Windows lifecycle problem.

## METHOD DELTA

A runtime report from a dirty worktree cannot inherit the clean baseline's evidentiary status merely because HEAD points to the baseline.

Reusable gate:

`runtime observation → executable fingerprint → clean/dirty status → exact diff → attribution`

before:

`runtime result → baseline Knowledge Delta`.

`HEAD SHA = baseline` does not imply `executed code = baseline` when the worktree is dirty.

## NEGATIVE KNOWLEDGE

Do not infer from RQ10 that baseline e46d830 safely avoids refresh during cognitive-frame translation.

Do not infer baseline MCP → PerceptionSnapshot continuity from a run whose exact executable artifact is unresolved.
