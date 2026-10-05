# CHAT-ARCH-2026-10-04-050 — IABV → CODEX APPROVAL GATE RESULT

## OBJECTIVE

Reconcile the first clean-target IABV runtime attempt after the workspace provenance gate, without weakening governance or creating a new coordinator.

## RUNTIME RESULT — CODEX REPORTED

The experiment was executed from a disposable clone of the repository at the authorized target commit:

- target SHA: `be97b989559cc04cebc9eb62890d6bc73e03dd7a`
- reported parent: `7bf3863ee2f9882cd338065db65a988588c50552`
- initial worktree verification: clean
- `C:/Python` was not modified

The normal non-deferred bootstrap stalled, but the Windows deferred-services path completed wiring and produced a live WorldModel snapshot. One invocation of `AutonomousEvolutionService.plan_or_execute` with a supported technical category then reached Codex selection.

Reported persisted records:

- task: `f7689caf-00ef-4a49-a7d4-c38e27fd6ec8`
- result: `15c940dc-65f6-4285-bf6f-1b8f02a4d5b1`

Reported runtime state:

- selected tool: `codex_installed`
- adapter: `external_assistant`
- approval: `pending`
- execution state: `waiting_approval`
- sandbox: passed
- real launch: not reached
- response captured: false
- rollout path: absent

## INDEPENDENT SOURCE RECONCILIATION

Remote `main` is now directly verified as:

`598fec7995a4f46ba0af2f05d64fe848b4f28d57`

and is identical to this recorded state.

Source inspection at the authorized target confirms:

1. `AutonomousEvolutionService.plan_or_execute()` invokes `ToolTeachService.execute_external_consultation()` with `approved=False`, preserving governance evaluation.
2. `ToolApprovalPolicy` sets approval required when the ToolCard requires human approval, supports writes, execution scope is write/destructive, or an action is destructive.
3. `codex_installed` has `requires_human_approval=True`.
4. `execute_task()` correctly returns `waiting_approval` after a successful sandbox when approval is still pending, and does not invoke the real adapter.
5. `ToolTeachService._build_external_consultation_request()` records `prompt_template_id='codex_consult_v1'`, but the actual prompt sent to the task is `consultation_metadata['context_pack']`.
6. `AutonomousEvolutionService._build_context_pack()` explicitly emits the Codex diagnostic output contract:
   - probable root cause;
   - recommended vertical change;
   - suggested tests;
   - file scope;
   followed by the structured incident packet.

Therefore the reported mismatch between a fixed-ack probe objective and the generated diagnostic consultation is **experiment-contract mismatch**, not yet evidence of a runtime prompt-generation defect.

## VERIFICATION STATUS

**SOURCE-RECONCILED, RUNTIME ARTIFACT NOT INDEPENDENTLY READ BACK HERE.**

The task/result JSON paths were reported by Codex, but their bytes were not independently retrieved in this ChatGPT session. Do not promote their internal fields beyond the reported observation unless independently inspected later.

## WHAT THIS PROVES

The clean target removed the previous provenance/workspace blocker.

The production decision path on the authorized target can:

`supported technical deficit → AutonomousEvolutionService → consult_codex → codex_installed → external_assistant`

and the existing human-approval governance gate is reached and enforced before real launch.

This is the first direct runtime evidence in this experiment series that the Codex selection seam is not merely static source composition.

## WHAT THIS DOES NOT PROVE

It does not prove:

- human approval was granted;
- real Codex process launch;
- prompt delivery to Codex;
- response generation;
- verified rollout/session capture;
- automatic ingestion into IABV;
- learning;
- causal reuse;
- changed future decisions;
- autonomous GitHub-memory consumption.

## KNOWLEDGE DELTA

`selection can materialize a governed Codex Task/Result in runtime; governance blocks launch until explicit approval`.

The prior workspace gate is now closed for this target.

The remaining content-format discrepancy is explained by an existing production contract: Codex consultation context is deliberately diagnostic, while `codex_consult_v1` is currently only an identifier in task metadata.

## METHOD DELTA

For dispatch experiments, distinguish two objectives:

- **dispatch/capture proof**: response content is secondary; use the existing consultation contract and verify launch/capture provenance;
- **exact-payload probe**: requires an independently justified prompt contract and should not be mixed into the dispatch proof.

Do not alter production code solely to force a fixed-ack oracle when the minimum causal question is launch/capture.

## RELATION DELTA

The causal order is now evidenced as:

`runtime decision → tool-family selection → ToolCard → approval policy → sandbox → approval gate → (blocked before adapter.run)`.

Governance is causally upstream of external execution.

## ROUTING DELTA

The next actor for the immediate open edge is **the human approval boundary**, because the existing production policy intentionally requires explicit approval.

After approval is actually recorded, route back to **Codex** for one continuation run that observes whether the same task reaches the real adapter, launches Codex, and captures a response with verified session/rollout provenance.

No code change is justified yet.

## NEW OPEN EDGE

`valid human approval → existing pending task → adapter.run outside sandbox → Codex launch → response generation → verified session/rollout capture`

## EXPERIMENT ORACLE

For the next continuation, do **not** require the response to equal the fixed acknowledgment. The current production contract is the diagnostic consultation format. The minimum success criterion remains the chain:

`IABV decision → Codex selected → launch → response → verified capture`

Any prompt-contract refinement is a separate edge after dispatch/capture unless it becomes necessary to make the test discriminating.

## WRITEBACK

This record is the canonical reconciliation target for the reported runtime result.

END OF RECORD
