# IABV v1.5 — 2026-09-17 Symbiosis Causal Execution / Learning Checkpoint

## PURPOSE

This is a canonical operational-memory checkpoint distilled from the 2026-09-17 cross-IA investigation. It preserves current causal state, negative knowledge, provenance discrepancies, dynamic role routing and the smallest next evidentiary action so future chats do not require replaying the source conversation.

## SOURCE / PROVENANCE

Source: 2026-09-17 conversation reconstruction supplied as `chat (2)(1).txt`.

Independent GitHub read-back performed against `jhonf463r/Python` on 2026-09-17.

### Canonical code baseline

`main = 4b04566686c40cc6d48d64edb411b36867c54dcf`

This is the P0-B code baseline currently named by the investigation. It must not be inferred from older or later experimental branches.

### Experimental causal-routing branch

`p0b-first-causal-break = 2d472ccaaf5a37773fed1d8e389e580812599c03`

This branch contains the authority-contract correction for non-empty `preferred_assistant_kind`: semantic match only, no fallback for an explicitly preferred but unknown assistant. The branch is experimental and is not `main`.

### Experimental learning branch

`codex/world-grounded-learning-bridge = 55d3e2c93807202ec5d0177eda163e8de10418ef`

The remote tip is `55d3e2c...`; its committed diff only scopes the G3 learning observation wrapper. The reported `tests/test_l5_causal_decision.py` is not present at that remote tip on GitHub. Therefore any L5 evidence produced from that file must retain an explicit artifact/provenance discrepancy until independently resolved.

## CURRENT CAUSAL STATE

### Synaptic selection / dispatch

The following chain has runtime evidence in the recorded experiments:

`candidate resolution → SynapticRouter.decide() → assistant identity → semantic ToolCard → ToolTask.tool_id → execute_task() → correct ToolCard → correct adapter → adapter.run()`

The key operational interpretation is:

`baseline selection → optional Synaptic override → ToolTask.tool_id → operational authority`

Do **not** describe the unknown-assistant case as “Synaptic failure followed by a secondary selector”. The observed behavior is: unknown Synaptic candidate has no semantic ToolCard, therefore no override occurs, and the valid baseline `tool_id` remains authoritative.

`ToolTask.metadata` already preserves `synaptic_preferred_assistant_kind` and `synaptic_routing_decision` for this path; new tracing infrastructure is not justified merely to reconstruct that decision.

### L3 / L4 learning state

G3 runtime evidence established:

- real planner path;
- real filesystem mutation;
- independent filesystem observation and SHA verification;
- `VerifiedTransition` creation;
- SQLite persistence;
- fresh `AppDatabase` + `ToolRecordRepository` reader;
- `verified_transition_success_count: 0 → 1`;
- failure counter remained `0 → 0`.

Adjudication:

`L0 = PROVEN`

`L1 = PROVEN`

`L2 = PROVEN`

`L3 = PROVEN`

`L4 = PROVEN / strongly supported`

`L5 = NOT YET ACCEPTED`

`L6 = NOT PROVEN`

`L7 = NOT PROVEN`

The important epistemic boundary is that persistence and selector capability are not yet, by themselves, proof of a future production decision caused by the concrete prior experience.

### Reported L5 experiment

Devin reported a matched control/treatment experiment with:

Control: `learned_pattern = 0.0`, `total_score = 7.545`, no selected pattern.

Treatment: fresh reload, `learned_pattern = 1.0`, `total_score = 10.095`, selected pattern `8e8f6695-8bdb-4d6b-922d-fa6a11728245`.

The report attributed the difference to persisted verified experience.

This remains **CANDIDATE / PENDING INDEPENDENT AUDIT**, because the remote branch at `55d3e2c...` does not contain the reported L5 test file. Claude must first determine whether the experiment ran against committed code, uncommitted working-tree code, or another artifact, then audit the causal chain and the exact selector path.

## CURRENT OPEN EDGE

The current learning edge is:

`verified prior experience → persistence → reload → future selector decision → decision difference`

The current execution edge is:

`adapter.run() → authorization → transport → external effect → observable result → independent verification`

Do not collapse these into one claim. They are separate experiments with separate evidence requirements.

## AUTHORITY SEPARATION

The recorded G3 learning experiment uses an always-authorized mock container. Therefore:

`REAL AUTHORITY / AUTHORITY IPC = NOT PROVEN BY G3`

Learning evidence must not receive authority credit from another experiment unless the same causal path genuinely exercises the real authority mechanism.

## NEGATIVE KNOWLEDGE / FALSE-POSITIVE CONTROLS

Preserve these as active constraints:

- `implemented != proven`
- `wired != invoked != observed != caused`
- `test pass != production proof`
- `decision != action`
- `selection proven != execution proven`
- `execution proven != outcome proven`
- `outcome proven != verification proven`
- `verification proven != learning proven`
- `learning proven != behavioral change proven`
- `adapter.run() invoked != external action occurred`
- `report != evidence`
- `commit SHA != uncommitted working tree`
- `same label != same causal state`
- `persistence != reuse`
- `source trace != runtime causality`

Specific recurring traps from this cycle:

1. treating `55d3e2c...` as containing the unreported/uncommitted L5 test;
2. treating source-level selector consumption as future decision causality;
3. treating a different control/treatment result as causal without controlling variables;
4. treating an authorization object or mock approval as proof of legitimate authority;
5. treating adapter invocation as proof of external effect.

## DYNAMIC SYMBIOSIS / ROLE ROUTING

The current collaboration method is capability-driven, not a fixed AI sequence.

### Current best-fit routing

`ChatGPT → adjudication / context synthesis / evidence-boundary definition`

`Sonnet → independent forensic audit of the latest critical claim`

`Devin → Windows runtime execution and minimal local/test fixture implementation when necessary`

`Opus 5 → reserve for a genuine architectural contradiction, policy adjudication or higher-order causal ambiguity`

`Codex → reserve for implementation breadth/ambiguity that exceeds Devin's local test/runtime scope`

This routing is a method change, not a permanent identity assignment. The next actor should be chosen from the current uncertainty and available evidence.

## MESSAGE-EFFICIENCY LESSON

Do not spend an additional AI intervention merely to repeat an edge already closed by stronger evidence.

In this cycle, Sonnet's runtime observation of `ToolTask.tool_id → execute_task() → adapter` superseded the need for additional Opus adjudication of that same edge.

Likewise, Codex should not be re-engaged simply because it historically implemented tests when Devin has the exact Windows environment and can perform a strictly local test/fixture change.

A new external intervention is justified when it reduces a material uncertainty that the current actor cannot close with existing evidence/capability.

## NEXT ACTOR / NEXT ACTION

Current next actor: **SONNET**.

Current minimum experiment: independently audit the reported L5 experiment, beginning with exact artifact provenance and then verifying whether:

`real verified experience → real persistence → real reload → real future selector invocation → controlled causal difference → changed decision`

is genuinely demonstrated.

If Sonnet confirms the causal claim, the next experimental boundary is L6: demonstrate a real behavioral change caused by the changed decision while controlling the relevant environment. If Sonnet finds a contradiction or architectural ambiguity, route that specific question to Opus before implementation. If Sonnet finds a concrete local code/test defect, route the minimal correction to Devin.

## IABV INFLECTION CRITERION

The current target is not “IABV selects the right assistant”. That capability has substantial runtime evidence.

The stronger target is:

`PERCEPTION → CONTEXT → STATE → SELECTION → ACTION → RESULT → VERIFICATION → KNOWLEDGE → POLICY CHANGE → FUTURE SELECTION DIFFERENCE`

Only the edges already explicitly evidenced may be marked closed. Do not declare the full cognitive loop closed until downstream behavioral reuse and independently verified world effects are observed.

## WRITEBACK RULE

Future material changes from this checkpoint must update:

- `CURRENT-STATE.md` for current truth and active gate;
- `CONTEXT-INDEX.md` for objective routing;
- `SYMBIOSIS-MAP.md` for cross-IA method/capability changes;
- `UNRESOLVED-KNOWLEDGE.md` for new or resolved latent questions;
- `ARCHIVE-REGISTRY.md` for this source record;
- this checkpoint only when a new reconciliation supersedes or materially changes its claims.

Do not silently rewrite historical source evidence to remove contradictions; supersession must retain provenance.
