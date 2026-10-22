# IABV — Adjudication of inferred evolution summary and `probe_consumed`

- **Date:** 2026-10-22, America/Bogota.
- **Purpose:** reconcile an owner-pasted IABV chat message tagged `inferido` against published main source; prevent an inferred status summary from being mistaken for verified tool selection, active sandbox execution, or completed diagnostic testing.
- **Evidence provenance:** the pasted chat text is `OWNER_REPORTED`. Source-code behavior below is `HEAD_SOURCE`, fetched from the repository's current public `main` through the GitHub connector. The local runtime, its in-memory state, the actual persisted local decision log, current experiments, and exact UI-to-summary call path were **not** inspected. No local `data/`/SQLite access, commands, tests, builds, launches, or process mutations were performed.

## 1. Owner-pasted message

The owner reports seeing the evidence tag **`inferido`** above this repeated text:

> En el estado evolutivo actual va ganando ollama para general, hay 8 propuesta(s) en sandbox/validacion, aparecio como discovery Ollama local, ya se descartaron 3 candidato(s). La ultima decision fuerte fue probe_consumed.

This must be preserved as a reported chat output, not treated as a runtime receipt.

## 2. Meaning of the UI evidence tag

Published QML source documents the optional field `evidenceTag` with values `observed`, `inferred`, or `unresolved`, and maps those values to the visible labels “observado”, “inferido”, and “sin confirmar” in `ChatMessageDelegate.qml` ([source](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/ui/qml/components/ChatMessageDelegate.qml)).

The tag therefore explicitly distinguishes an inferred statement from an observed one; it is not a correctness guarantee, confidence percentage, timestamp, provenance receipt, or validation verdict. The exact runtime payload and the path that attached `evidenceTag=inferred` to this particular message were not inspected, so no additional inference about the tag's assignment mechanism should be made.

## 3. Static-source finding: `probe_consumed` is a diagnostic-signal record, not a winner decision

In public main, `AutonomousValidationCycleService._consume_auto_probes()` documents that:

- pending structured probes come from `OperationalSelfExamination` findings;
- the cycle appends a decision-log record with `decision='probe_consumed'` and the finding ID;
- “la ejecución real del probe sigue siendo responsabilidad del orquestador / ToolTeachService / runner de pytest”; this method only exposes the structured signal;
- “No se modifica estado real; solo se surfacea la señal” and the method “no decide ruta ni se dispara nada.”

Source: [autonomous_validation_cycle.py, probe loading/consumption](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/self_teach/autonomous_validation_cycle.py#L1855-L1957).

The status summary returns the final entry in the decision log as `last_decision`, without restricting it to a promotion, discard, or completed experiment. Consequently `probe_consumed` can appear as the last decision/event even though it is not a selection win, sandbox pass, executed probe, resource fix, or bridge/read authorization.

**Adjudication:** describing `probe_consumed` as “la última decisión fuerte” is semantically misleading unless another, separately verified layer defines and evidences what “fuerte” means. The published method itself defines no such strength and does not establish that the underlying test/probe ran.

## 4. Static-source finding: “8 proposals in sandbox/validation” can overstate active execution

In `decision_log_summary()`, public main builds `in_validation` by collecting entries whose decision is exactly `deferred` and whose `proposal_key` is non-empty. It deduplicates the strings and truncates the displayed collection to eight. It does not, in this function, query an active sandbox worker or verify that each deferred proposal currently has a running experiment.

Source: [autonomous_validation_cycle.py, decision-log summary](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/self_teach/autonomous_validation_cycle.py#L123-L184).

Separately, `ToolDiscoveryService.build_status()` constructs discovery signals from recommendations / experiment runs and available tool-registry cards, then reconciles matching proposal keys against the latest decision log. A signal marked `detected` is a detected candidate signal, not itself a promotion or proof of measured superiority.

Source: [tool_discovery_service.py, discovery status and reconciliation](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/tool_discovery_service.py#L55-L145) and [decision reconciliation](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/tool_discovery_service.py#L360-L390).

**Adjudication:** the phrase “8 propuestas en sandbox/validación” is not proven to mean eight currently executing sandbox runs. From the summary method alone, it can mean up to eight distinct proposal keys with `deferred` decision-log entries. Confirming the actual live status would require an authorized, correlated source of active-run state; this document does not request or authorize reading local `data/` or SQLite.

## 5. Static-source finding: discovery is not evidence that Ollama is the winning general route

`ToolDiscoveryService` builds signals by comparing registry cards with recommendation/run context. The reported discovery “Ollama local” is compatible with a candidate being detected for evaluation; it does not by itself mean that it was promoted, that an experiment passed, or that it is objectively superior.

The public validation summary only records `winning_by_problem` when a logged proposal was marked `promoted` (candidate tool/kind/route) or `discarded` (current tool/kind/route). The exact live decision entries behind this user-pasted summary were not available for authorized inspection in this task.

**Adjudication:** “Ollama va ganando para general” remains `INFERRED / OWNER_REPORTED` until it is tied to an identifiable subject key, proposal key, current and candidate routes/config signatures, baseline and candidate metrics, sample/run IDs, explicit sandbox verdict, timestamps, and a verified promotion/consumer receipt. No current-runtime or local persistence state is asserted here.

## 6. How to handle “3 candidates discarded”

The summary method collects discarded entries into a returned list containing their subject, proposal key, candidate assistant kind/route, reason, and decision, then returns only the last six records. A UI statement that three candidates were discarded does not by itself establish that three distinct alternatives were fully evaluated in the current validation window; the underlying IDs and verdicts were not provided in the pasted message.

Do not infer success/failure denominators, active candidate counts, or an exhaustive lifetime count from this one-line summary.

## 7. Next action — clarification only, no new scan

Do **not** run a broad autoscan, tests, new probes, sandbox runs, local `data/`/SQLite reads, branch operations, GPU/provider changes, model reload, credential operations, or a workaround for the blocked local reader.

If asking IABV to clarify this message, constrain the request to the current message context and evidence references that are already attached to it. It should provide, without invoking tools or reading additional files:

- whether “8 proposals” refers to current active execution or merely `deferred` entries / a capped summary;
- whether “Ollama wins general” is a measured promotion, a historical decision-log value, or only a candidate-score/discovery inference;
- which visible identifiers, timestamps, verdicts, and run/receipt IDs already support each claim;
- what precisely `probe_consumed` means in this output and whether there is a separate receipt showing actual probe execution.

For any field not already backed by available evidence, it must say `UNRESOLVED` and leave the original state untouched.

This clarification does not change the bridge's active blocker. The canonical route remains `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`; `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `LOCAL_SOURCE_READ=NOT_RUN`, and `REAL_TRANSPORT=NOT_RUN`. No inference, discovery signal, proposal count, or `probe_consumed` entry grants read permission or releases that gate.

## 8. Continuity lesson

A visible `inferido` tag is a useful epistemic distinction only if the surrounding system preserves the supporting basis. The UI must not let “detected”, “deferred”, “probe consumed”, “promoted”, “sandbox experiment completed”, and “later decision reused verified learning” collapse into one generic success narrative. Keep those states separate and require correlated evidence for each transition.

This is public-source static adjudication only; it is not an implementation verdict or proof that the current local runtime behaves exactly like published main.
