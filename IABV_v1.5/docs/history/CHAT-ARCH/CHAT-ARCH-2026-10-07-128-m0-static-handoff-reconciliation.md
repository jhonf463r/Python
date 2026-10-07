# CHAT-ARCH-2026-10-07-128 — M0 STATIC HANDOFF / EXTERNAL-AI COORDINATION RECONCILIATION

## CLASSIFICATION

`RECONCILIATION / ROUTING / M0 / EXTERNAL-AI / SYMBIOSIS / STATIC-ARCHAEOLOGY`

## PURPOSE

Close the static/source-level question:

> Is the existing IABV architecture structurally capable of serving as the user's development interface and delegating a governed technical subtask to an external AI, receiving the response, and ingesting it — without introducing a new coordinator/bus/brain?

This record is separate from RQ15 runtime perception and does not supersede the current universal technical frontier.

## VERIFIED SNAPSHOT

Repository:
`jhonf463r/Python`

Reference snapshot audited by Codex:
- HEAD `74b366c9a869933629346a552174206420d6aa9d`
- tree `d2683eeee66bb3124545fb1760cfd4afc65ba99e`
- isolated analysis worktree `C:\temp\iabv-blind-74b366c9`
- no production source changes made by the audit
- no IABV runtime, provider, or Codex execution during the static audit

Focal source blobs:
- `bootstrap.py` `e4befa6b683fc87aed7481f377f1332f5753e2c3`
- `control_center_viewmodel.py` `628848c631e36b47b4a5b63b9e68d62687625235`
- `inference_service.py` `6bde63ce6ffa37b41763400d759a8348cb1165c3`
- `adaptive_task_orchestrator.py` `41f6f7b6157226a1c6004591ddff4e36ff6f6da5`
- `intent_understanding_service.py` `3399dccd36fa92dfd804330f53833ccb50056577`
- `capability_readiness_service.py` `b4f60d1fb58183765ff232cc58f0c2ef3f1c9704`
- `autonomy_governance_policy.py` `a88a0cf30d0a2f129b68d746c0175461851d40c0`
- `autonomous_evolution_service.py` `bf71757e8b90a35ce5c46cc0e6b5a781abbcd7ad`
- `tool_teach_service.py` `7f0412627c98074b1e3df0d0f6e76ab5998e3505`
- `tool_registry.py` `17a0f7cc82dfb6722d4f2d7b231ac61551eb7ac2`
- `tool_approval_policy.py` `b5bd3cba40caa89fcc6a5cd72146281c07c26ea1`
- `tool_adapters.py` `f8ce508342d2da96f30b2152ffa242f08b187987`
- `ui_execution_runner.py` `a8917e38ce7b9975ae2930f8fed2f272682d3284`

## STATIC END-TO-END GRAPH

Normal UI path:

`ControlCenterViewModel.sendChat()`
→ shortcut intent analysis
→ normal `InferenceService.infer_task()`
→ `AdaptiveTaskOrchestrator.handle_request()`
→ intent/context/capability/governance
→ local/external decision
→ result
→ post-response autonomous-evolution path when eligible.

External consultation path, when reached:

`AutonomousEvolutionService.plan_or_execute()`
→ consultation assessment
→ `ToolTeachService.execute_external_consultation()`
→ generated prompt/context pack
→ `ToolRegistry.pick_card_for_task()`
→ `ToolApprovalPolicy.evaluate()`
→ `ExternalAssistantToolAdapter.run()`
→ `UIExecutionRunner.capture_response_from_app()`
→ Codex app/session/rollout capture
→ `ToolResult`
→ `ToolTeachService` / `AutonomousEvolutionService` response ingestion
→ possible later decision use.

## VERIFIED STATIC CAPABILITIES

The snapshot contains an existing `codex_installed` ToolCard with:
- assistant kind `codex`
- capabilities including `launch_app`, `llm_query`, `consult_external`, `code_assistance`
- affinities including `code_review`, `diagnostics`, `surgical_fix`, `architecture_audit`
- desktop launch metadata
- `response_capture_mode=clipboard_capture`
- `background_capture_mode=codex_rollout`
- human approval required.

The existing `ExternalAssistantToolAdapter` contains a Codex rollout capture route. Automatic response capture is implemented in source; `manual_pasteback` is a fallback when automatic capture cannot provide a verified usable response. It is not a structural requirement of the Codex ToolCard.

The external consultation builder preserves:
- user goal,
- context pack,
- assistant preference,
- diagnostic category,
- incident metadata,
- goal parameters,
- session/thread information,
- provenance/trace fields.

The result path records capture state, assistant identity, session/thread information, external-state flags and response-ingestion metadata.

## CRITICAL ROUTING FINDING

The prior blind M0 objective did NOT demonstrate autonomous external-AI selection.

Reported runtime route:
`KNOWLEDGE`
with `KNOWLEDGE_SEARCH + EMBEDDINGS`
and local Ollama.

Codex source archaeology shows this is consistent with the generic/local intent path.

The audited external consultation machinery is downstream and can be activated by explicit technical consultation predicates such as:
- `need_codex_fix`
- `need_adapter`
- an explicit `consult_codex` action
- certain technical incident/diagnostic conditions
- governance-bearing decision context.

A generic objective containing phrases such as “recurso externo especializado” does not by itself prove that the intent layer will infer `code_assistance` or `consult_codex`.

Therefore the earliest currently supported M0 problem is:

`OBJECTIVE → REQUIRED CAPABILITY / EXTERNAL CONSULTATION INTENT`

not absence of an external tool adapter.

## STATE MATRIX

| Edge | State | Meaning |
|---|---|---|
| Objective ingestion | OBSERVED | UI/orchestrator path has been observed in prior reported run |
| Interpretation | OBSERVED | `KNOWLEDGE` observed, but intended external technical meaning not recovered |
| Required capability | OBSERVED/INCOMPLETE | local knowledge capability selected; external code capability not observed for the blind objective |
| External consultation decision | DEFINED | consultation predicates exist |
| Candidate discovery | DEFINED | Codex ToolCard exists |
| Codex selection | DEFINED | selector can choose by preference/criteria |
| Governance | DEFINED | approval policy exists; Codex card requires human approval |
| Prompt construction | DEFINED | consultation builder creates prompt/context |
| Prompt delivery | DEFINED | desktop runner path exists |
| Codex execution | UNPROVEN | no successful M0 runtime observation |
| Automatic capture | DEFINED | Codex rollout capture/correlation exists |
| Manual pasteback | DEFINED | fallback only |
| Response ingestion | DEFINED | ingestion path exists |
| Next-decision influence | UNPROVEN | no causal future-decision reuse proven |

## IMPORTANT EPISTEMIC LIMITS

`defined ≠ wired ≠ invoked ≠ observed ≠ caused`

`prompt prepared ≠ prompt delivered`

`response captured ≠ response ingested`

`response ingested ≠ next decision consumed it`

`external adapter exists ≠ autonomous external routing exists`

The Codex audit was source/static archaeology. It did not prove the live M0 round trip.

## M0 LIVE FRONTIER

A live M0 test must use the actual production UI entrypoint:

`ControlCenterViewModel.sendChat()`

and must not replace it with:
- private consultation calls,
- direct `ToolTeachService` invocation,
- direct adapter invocation,
- artificial CLI substitutes,
- unit-test-only substitution.

The earlier Devin attempt established only:

`M0 BLOCKED AT EXECUTION CHANNEL / UI ENTRYPOINT`

because that execution channel could not interact with the PySide6 + QML UI.

This is an actor/channel limitation, not evidence of a production defect.

## MINIMUM DISCRIMINATING LIVE TEST

The correct next M0 experiment is one normally submitted, technically explicit but assistant-unnamed objective that should be capable of reaching the existing external-consultation predicates.

Capture before provider execution:
- intent key/role/confidence,
- conversation analysis/hypotheses,
- required capabilities,
- consultation assessment and `should_consult`,
- diagnostic category/action,
- selected ToolCard and availability,
- approval decision,
- generated prompt marker,
- Codex launch/session identity,
- capture result,
- ingestion result,
- whether the next decision consumed the ingested result.

Stop at the first failed edge.

## ACTOR ROUTING

- Static audit: CODEX — completed.
- Live M0 UI execution: requires a UI-capable Windows channel.
- Devin is not suitable for the already-observed PySide6 + QML channel limitation.
- Do not modify production merely to make an unsuitable actor fit the experiment.
- Do not create a CLI substitute without a separate behavioral-equivalence/readiness decision.
- Sonnet/Claude is conditional only if a contradiction/anomaly appears.

## KNOWLEDGE DELTA

1. IABV already has a substantial governed external-AI consultation path; the immediate blocker is not absence of a new “agent bus”.
2. Codex automatic rollout capture exists statically; manual pasteback is a fallback, not the architectural dependency.
3. The prior blind objective exposed a semantic routing gap before external consultation.
4. The practical M0 question is therefore a routing/entrypoint problem followed by a runtime handoff proof, not an architecture-build problem.
5. RQ15 remains a separate technical frontier and must not be conflated with M0.

## METHOD DELTA

For M0, discriminate in order:

`OBJECTIVE → REQUIRED CAPABILITY → CONSULTATION DECISION → CANDIDATE → GOVERNANCE → DELIVERY → EXECUTION → CAPTURE → INGESTION → NEXT-DECISION IMPACT`

Do not debug downstream handoff machinery before proving the upstream objective-to-capability edge.

For UI-bound experiments:

`UI capability → execution-channel readiness → authorization → production entrypoint`

A non-UI-capable actor cannot establish a UI architectural failure.

## ROUTING DELTA

Capability-fit remains two-dimensional:

`actor capability × execution-channel admissibility`

Static audit capability and Windows UI execution capability are distinct.

Do not select Devin or Codex merely because they handled a prior step. Recompute from the first open edge.

## ALGORITHM DELTA

M0 gives a concrete realization of the universal algorithm:

`OBJECTIVE → INTERPRET → INFER CAPABILITY → DISCOVER/SELECT REALIZATION → GOVERN → HANDOFF → ACT → OBSERVE → VERIFY → INGEST`

but only the early local-routing portion is observed for the prior blind objective. The external branch remains a candidate composition awaiting a valid live UI execution.

## STOP

No production implementation is justified by this record alone.

Next step is one UI-capable, provenance-bounded live M0 observation after the exact entrypoint and evidence contract are satisfied.
