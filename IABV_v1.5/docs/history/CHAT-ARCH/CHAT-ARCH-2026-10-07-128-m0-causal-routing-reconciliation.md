# CHAT-ARCH-2026-10-07-128 — M0 CAUSAL ROUTING / STATIC HANDOFF RECONCILIATION

## CLASSIFICATION

`RECONCILIATION / ROUTING / M0 / HANDOFF / UI-EXECUTION / PROVENANCE / SYMBIOSIS`

## PURPOSE

Reconcile the independent Codex static audit of the M0 product-front branch against the canonical GitHub state after RQ15 episode 127.

M0 objective:

`HUMAN OBJECTIVE → IABV INTERPRETS → IDENTIFIES REQUIRED CAPABILITY → SELECTS/GOVERNS EXTERNAL REALIZATION → DELIVERS PROMPT → EXTERNAL AI EXECUTES → IABV CAPTURES/INGESTS RESULT → RESULT CAN AFFECT NEXT DECISION`

The practical product objective is to remove routine manual prompt/result transport while keeping human authority for deep conceptual decisions and governed interventions.

## WRITEBACK BASELINE

Canonical repository:
`jhonf463r/Python`

Main at reconciliation:
- HEAD: `268c5748c3300cf9847c62deb7254df6c7b14024`
- tree: `02ca12005dd547a5dc0cc34a1162c1cff6120143`
- parent: `01ac79ef85aa0ddf03da1a3d19186dc263f61fb5`

The M0 static audit was performed against:
- HEAD: `74b366c9a869933629346a552174206420d6aa9d`
- tree: `d2683eeee66bb3124545fb1760cfd4afc65ba99e`

GitHub compare from the audit snapshot to current main:
- `ahead_by = 12`
- `12` commits ahead
- **none of the 12 commits changed the focal M0 production Python sources**.

Therefore the Codex source findings remain attributable to the current main source state for the audited M0 surfaces. The current main changes since the snapshot were documentation/history writebacks, not M0 production implementation changes.

## CURRENT WORKTREE / EXECUTION BOUNDARY

The Codex audit used:
`C:\temp\iabv-blind-74b366c9`

The worktree was dirty in non-source data/log/cache areas, with no tracked executable Python source modifications under `IABV_v1.5/src`.

No:
- IABV runtime,
- provider,
- Codex runtime,
- UI interaction,
- external consultation,
- production modification

occurred during the Codex audit.

## VERIFIED STATIC HANDOFF GRAPH

The source contains a composed external-consultation path:

`ControlCenterViewModel.sendChat()`
→ ordinary inference path / post-response governance
→ `AutonomousEvolutionService.plan_or_execute()`
→ consultation predicates / `should_consult`
→ `ToolTeachService.execute_external_consultation()`
→ `ToolTask`
→ `ToolRegistry.pick_card_for_task()`
→ `ToolApprovalPolicy`
→ `ExternalAssistantToolAdapter.run()`
→ `UIExecutionRunner.capture_response_from_app()`
→ Codex application/session
→ automatic rollout/thread capture when available
→ `ToolResult`
→ consultation response ingestion path
→ persisted task/result / autonomous consultation state.

The exact downstream call chain is conditionally entered; its static presence does not prove runtime traversal.

## IMPORTANT STATIC FINDING — AUTOMATIC CODEX CAPTURE ALREADY EXISTS

The `codex_installed` ToolCard declares:

- `assistant_kind = codex`
- `capabilities = launch_app, llm_query, consult_external, code_assistance`
- `task_affinities = code_review, diagnostics, surgical_fix, architecture_audit`
- `launch_mode = desktop_app`
- `response_capture_mode = clipboard_capture`
- `background_capture_mode = codex_rollout`
- `requires_human_approval = true`.

The existing `ExternalAssistantToolAdapter` and `UIExecutionRunner` contain automatic Codex rollout/thread capture and verification logic.

Therefore:

`manual_pasteback` is **a fallback path**, not a structural requirement of the Codex route.

This is a major product-relevant deduction because it means the existing architecture is already attempting to eliminate manual copy/paste once the external consultation path is successfully entered and the runtime capture contract succeeds.

## CRITICAL ROUTING FINDING

The previously supplied blind runtime objective was interpreted as a local:

`KNOWLEDGE → KNOWLEDGE_SEARCH + EMBEDDINGS`

route.

The static source supports this result:
generic `general.assistance` falls into a local assistance/knowledge path rather than automatically entering the external consultation machinery.

The source does contain explicit predicates capable of producing Codex consultation, including technical diagnostic categories/actions such as `need_codex_fix`, `need_adapter` and `consult_codex`, but the blind objective did not demonstrate that it reached one of those predicates.

Therefore there are two distinct M0 questions:

### M0-A — MEDIATED HANDOFF

Can IABV carry an explicitly directed external consultation through:

`objective + explicit external preference`
→ governance
→ Codex
→ automatic capture
→ ingestion?

This isolates the transport/execution/ingestion circuit.

### M0-B — SELECTIVE ROUTING

Can IABV receive an objective without naming Codex and infer:

`objective → required external capability → candidate → Codex`

before falling into local KNOWLEDGE?

This isolates the semantic/routing circuit.

These must not be conflated.

A failure of M0-B does not prove that M0-A infrastructure is broken.

A successful M0-A does not prove that M0-B autonomous capability inference exists.

## M0 STATE MATRIX

| Edge | State | Adjudication |
|---|---|---|
| Objective ingestion | OBSERVED | Existing UI/inference runtime path has been observed previously. |
| Interpretation | OBSERVED | Blind run produced KNOWLEDGE. Intended external-review meaning was not demonstrated. |
| Required capability inference | OBSERVED / INSUFFICIENT | Local knowledge capability was inferred; external code-assistance need was not observed. |
| External consultation decision | DEFINED | Static predicates exist; blind run did not enter them. |
| Candidate discovery | DEFINED | Codex ToolCard and registry path exist. |
| Codex selection | DEFINED | Preference/selection mechanisms exist; no blind-run selection occurred. |
| Governance | DEFINED | Codex requires human approval; policy path exists. |
| Prompt construction | DEFINED | Consultation request builds task/context/prompt. |
| Prompt delivery | DEFINED | Desktop runner contains delivery logic; no live delivery evidence. |
| Codex execution | UNPROVEN | No M0 Codex execution yet. |
| Automatic capture | DEFINED | Codex rollout/thread capture exists; runtime success unobserved. |
| Manual pasteback fallback | DEFINED | Fallback exists; it is not structurally required by the Codex card. |
| Response ingestion | DEFINED | Ingestion path exists; no Codex result ingested in M0. |
| Next-decision influence | UNPROVEN | No causal evidence that an ingested external response altered a later IABV decision. |

## EPISTEMIC SEPARATION

### FACT

1. Current main is `268c5748...`.
2. The M0 audit snapshot `74b366c9...` is 12 commits behind current main.
3. None of those 12 commits changed the audited M0 production Python source files.
4. The existing architecture contains explicit external consultation, Codex selection, desktop delivery and automatic rollout-capture mechanisms.
5. `manual_pasteback` is implemented as fallback behavior.
6. The previously observed blind objective took a local KNOWLEDGE route.
7. A prior Devin attempt could not interact with the required PySide6 + QML `sendChat()` UI entrypoint.

### INFERENCE

1. The external-AI infrastructure is materially closer to functional M0 than an architecture-gap interpretation would suggest.
2. The current semantic weakness is earlier than the external adapter: the generic objective does not reliably become an external code-assistance capability requirement.
3. The product goal “remove manual prompt copying” may be achievable first through M0-A, before M0-B autonomous actor inference is solved.
4. The current M0 execution blocker is actor/channel-specific: the previously selected Windows actor was not UI-capable.
5. The next M0 evidence should therefore isolate semantic routing from execution-channel capability instead of modifying production prematurely.

### ASSUMPTION

None beyond the explicitly bounded interpretation that the reported blind runtime result came from the stated snapshot and normal UI processing. The exact runtime intent metadata for that earlier run remains incomplete.

## FIRST OPEN EDGES — TWO LEVELS

### Immediate experiment-readiness edge

`UI-capable Windows execution surface → real ControlCenterViewModel.sendChat()`

This is an execution-channel requirement, not evidence of a production defect.

### First production semantic edge

`OBJECTIVE → REQUIRED CAPABILITY`

Specifically:

`generic development/review objective → external code-review/code-assistance requirement`

The latter is the first causal production edge not yet demonstrated by runtime evidence.

Do not modify the classifier merely from this static conclusion.

## ROUTING CONSEQUENCE

The next M0 execution should be chosen by **capability + execution-channel admissibility**, not by agent identity.

The actor must be able to:
- launch/use the real PySide6 + QML interface,
- submit one bounded objective through `sendChat()`,
- observe the generated consultation decision,
- and preserve runtime evidence.

The experiment must not call:
- private consultation methods,
- `ToolTeachService` directly,
- `ExternalAssistantToolAdapter` directly,
- artificial CLI substitutes.

Those would bypass the open semantic/UI boundary.

## MINIMUM DISCRIMINATING M0 EXPERIMENT

Two-stage sequence:

### Stage A — explicit external preference

Use the normal UI but explicitly request a technical consultation through an external assistant.

Purpose:
prove or disprove the already-built circuit:

`UI → external consultation → governance → Codex → prompt delivery → automatic capture → ingestion`

No autonomous actor inference is claimed.

### Stage B — assistant-unnamed objective

Repeat with an objective whose desired outcome clearly requires independent technical review but does not name Codex.

Purpose:
test:

`OBJECTIVE → REQUIRED CAPABILITY → EXTERNAL CONSULTATION`

Stop at the first divergent edge.

This decomposition maximizes information gain and avoids confusing two separate unknowns.

## STOP CONDITIONS

Stop after the first of:
- UI entrypoint cannot be reached;
- governance denies the action;
- no external consultation decision;
- Codex card not selected/available;
- prompt not delivered;
- response not captured;
- response captured but not ingested;
- response ingested but absent from the next decision's actual inputs;
- one complete round trip plus one subsequent decision-input check.

No retries, no production changes, no new architecture during the discriminating run.

## KNOWLEDGE DELTA

1. IABV already contains a semantically meaningful external-consultation subsystem; the main missing proof is causal traversal, not existence of components.
2. Codex automatic response capture is already designed into the existing realization; manual copy/paste is a fallback, not the intended mature path.
3. The current blind routing failure occurs before external candidate execution: generic objectives can remain local KNOWLEDGE.
4. M0 therefore decomposes naturally into mediated handoff and intelligent actor selection.
5. The distinction prevents premature classifier modification and prevents treating a blocked UI actor as a production failure.
6. The main repository has now been verified to preserve the audited M0 production source unchanged across the 12 commits between the audit snapshot and current main.

## METHOD DELTA

For development-assistance maturity, separate:

`MEDIATED COLLABORATION`
from
`AUTONOMOUS RESOURCE SELECTION`.

Recommended progression:

`M0-A: explicit governed external handoff`
→
`M0-B: objective-driven external capability inference`
→
`M1: dynamic actor/resource selection`
→
`M2+: experience-informed routing and reuse`.

Do not require M0-B to prove the basic handoff infrastructure.

New invariant:

`UI-channel blocked ≠ production-path broken`

and:

`external-path defined ≠ external-path causally traversed`.

## ROUTING DELTA

Current project-wide technical frontier remains the post-RQ15 universal seam:

`live PerceptionSnapshot environment/world evidence → capability/affordance representation → realization selection`

with CODEX as the current static-archaeology actor.

M0 remains a **secondary product-front branch**.

For M0 specifically:
- first requirement is a genuinely UI-capable execution channel;
- after that, discriminate M0-A before changing semantic routing;
- only if M0-B still fails should a minimal `WIRE/REPAIR` of objective-to-capability representation be considered.

No `NEW` architecture is justified.

## ALGORITHM DELTA

The practical universal algorithm now has a more precise collaboration seam:

`OBJECTIVE
→ INTERPRET
→ REQUIRED CAPABILITY
→ DISCOVER/SELECT REALIZATION
→ GOVERN
→ HANDOFF
→ ACTOR EXECUTION
→ OBSERVE RESULT
→ VERIFY
→ INGEST
→ NEXT DECISION`

For M0, the external realization branch is already substantially implemented statically. The missing proof is the transition from objective semantics into that branch and then its runtime round trip.

## FINAL VERDICT

`M0 REQUIRES LIVE DISCRIMINATION — NO PRODUCTION REPAIR JUSTIFIED YET`

More specifically:

- static external handoff infrastructure: **substantially ready**;
- manual pasteback elimination mechanism: **implemented as an automatic-capture-first design**;
- generic objective → external capability routing: **not proven**;
- end-to-end M0 runtime: **not proven**;
- previous M0 execution attempt: **blocked by UI execution-channel capability**;
- architectural gap: **not established**.

## STOP

Do not modify production from this reconciliation.
Do not reopen RQ15.
Do not create a new coordinator/bus/memory/observer.
Do not treat M0 as failed.
Do not inherit any historical “next actor” without recomputing execution-channel admissibility.

The next material M0 action is one UI-capable, normally submitted, bounded experiment that separates M0-A from M0-B.
