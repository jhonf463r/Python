# CHAT-ARCH-2026-10-07-125 — M0 UI ENTRYPOINT / EXECUTION-CHANNEL BLOCK

## Classification

`RECONCILIATION / ROUTING / M0 / WINDOWS-UI / EXECUTION-CHANNEL / SYMBIOSIS`

## Trigger

Devin attempted the previously specified M0 live experiment whose exact production entrypoint is the interactive PySide6 + QML route `ControlCenterViewModel.sendChat()`.

The experiment contract explicitly prohibited:
- private consultation calls;
- direct `ToolTeachService` calls;
- direct `ExternalAssistantToolAdapter` calls;
- artificial CLI substitutes;
- unit-test substitution.

Devin's execution channel cannot interact with the PySide6 + QML UI.

## FACT

Experiment provenance reported by Devin:
- HEAD: `74b366c9a869933629346a552174206420d6aa9d`
- tree: `d2683eeee66bb3124545fb1760cfd4afc65ba99e`
- worktree: `C:\temp\iabv-blind-74b366c9\IABV_v1.5`
- Python: `C:\Users\faber\miniconda3\python.exe`, 3.13.2
- no IABV runtime was executed;
- no UI interaction occurred;
- no external consultation occurred;
- no artifacts or runtime evidence were generated.

## CORRECT CLASSIFICATION

`M0 BLOCKED AT EXECUTION CHANNEL / UI ENTRYPOINT`

The reported `M0 REQUIRES PRODUCTION WIRE/REPAIR` classification is not justified.

No evidence shows a production architectural defect. The observed limitation is an actor/channel capability mismatch.

## WHAT REMAINS UNPROVEN

The following remain unobserved:
`sendChat() → explicit external intent → consultation → Codex delivery → Codex response → capture → ingestion`.

Therefore this episode neither proves nor refutes the functional M0 handoff.

## METHOD DELTA

A UI-bound experiment must satisfy:
`required UI interaction capability → actor/channel readiness → authorization → execution`.

A CLI or private-method substitute is not equivalent merely because it reaches similar downstream functions. Such a substitute would require a separate behavioral-equivalence/readiness analysis and explicit authorization.

New invariant:
`UI-unobservable actor ≠ M0 architectural failure`.

## ROUTING DELTA

M0 is now a **secondary product-front branch blocked at the UI execution surface**.

Do not modify production to accommodate the blocked actor.
Do not invent a CLI solely to fit the actor.
Do not classify the M0 functional path as broken.

## CURRENT CANONICAL FRONTIER

This episode does **not** supersede the current technical routing authority.

The canonical technical frontier remains RQ15:
`independent Windows process identity → existing IABV process observation helper`.

RQ15 is currently blocked specifically at the Codex execution channel; Devin remains capability-fit for that non-UI Windows runner.

## NEXT EDGE

For the M0 branch:
`human/UI-capable execution surface → real ControlCenterViewModel.sendChat() observation`.

For the project-wide technical frontier:
`Devin execution channel → exact authorized RQ15 evidence-complete runner → one bounded live observation`.

## STOP

No production code change.
No new CLI.
No retry through the same unavailable UI channel.
No claim of M0 failure.
