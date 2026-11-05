# Space-Time / Control Master reconciled implementation R2

Date: 2026-11-04 (America/Bogota)
Task: `IABV_SPACE_TIME_CONTROL_MASTER_RECONCILED_R2_20261104`
Base: `main@56e4d8b11846a8d8f3cb8cda08efd773ec235651`
Related candidates: PR #591 (source diagnostics) and PR #602 (temporal provenance / prompt parity)
Status: isolated combined candidate; tests/build/runtime NOT RUN.

## Advance contract

Objective: complete the independent Lane B implementation of Space-Time 2.7 by preserving whole-context freshness, timestamp provenance, queue semantics, source diagnostics and prompt delivery without creating another coordinator, router, memory store or authority source.

Target edge: the Control Master digest and Portable Context must expose the strongest supported source/time state to full and compact prompt consumers without converting partial/failed reads or ambiguous timestamps into fresh, empty or available states.

## Integration decision

One candidate is based directly on the exact current main SHA. PR #591 and PR #602 were not merged sequentially because their bases differ and six code/test paths overlap.

Included:
- Whole-context generation time is distinct from partial section update time.
- Portable-context freshness reports FRESH, STALE or UNVERIFIED; future and timezone-naive timestamps are UNVERIFIED.
- Queue states remain AVAILABLE, EMPTY_QUEUE, UNAVAILABLE and UNVERIFIED.
- Configured Control Master source-reader failures are recorded with stable diagnostic codes.
- Per-source coverage distinguishes READ_OK, READ_PARTIAL, READ_FAILED, READER_UNAVAILABLE, NOT_CONFIGURED and NO_FILE.
- signal_status, signal_reason and work_queue_status remain orthogonal. A successfully read empty queue is signal AVAILABLE + queue EMPTY_QUEUE.
- Full and compact prompts both receive the digest; next actions remain prioritized in compact prompts.
- ExperimentRecommendation.created_at_utc is preserved in task insight projection.

Source coverage semantics:
- NOT_CONFIGURED means no reader dependency was wired in this service instance. This records wiring only; it does not establish that the source is optional or out of scope, and it is not evidence that the source was empty.
- NO_FILE means runtime_audit.jsonl did not exist at the inspected workspace path. This records path state only; it does not establish that the source is optional or out of scope, and it is not a read failure.
- READ_OK means a configured reader returned successfully.
- READ_PARTIAL, READ_FAILED or READER_UNAVAILABLE are diagnostics; any recorded source error makes the unified signal and queue UNAVAILABLE, never EMPTY_QUEUE.
- NOT_CONFIGURED, NO_FILE or unknown coverage states do not establish that the source is optional/not-applicable. Until an explicit source-applicability policy exists, the unified signal and queue remain UNVERIFIED and do not expose partial items as actionable context.
- EMPTY_QUEUE / AVAILABLE are emitted only when the queue is a list and every source in the observed coverage map is READ_OK. A real source read failure is UNAVAILABLE; unresolved applicability/coverage is UNVERIFIED.
- signal_status describes availability of the successfully obtained and sufficiently covered configured-source projection; it is not an Owner authority or permission signal.

Excluded:
- The public projector and publisher from #591.
- The control-master-live branch, remote receiver, public disclosure dialog and Evolution Center UI.
- Any change to CURRENT-STATE routing, M1A G1–G8, Option D, protected reads, MCP allowlist, bridge, tunnel or production activation.
- Any claim of a live local Control Master read where no authorized runtime read surface was used.

## Acceptance matrix

| Contract | Required evidence |
|---|---|
| Full-context freshness | Full generation time is distinct from updated_at; section-only writes preserve it. |
| Timestamp provenance | Explicit offset/Z required; naive, invalid and future timestamps are UNVERIFIED. |
| Queue semantics | All four queue states remain distinct. |
| Source diagnostics | Configured read failures and missing reader methods are recorded with stable codes. |
| Source coverage | Optional/unconfigured/no-file states are explicit, not silently represented as empty reads. |
| Signal semantics | signal_status and signal_reason are independent from queue content/state. |
| Prompt parity | Full and compact prompts receive signal and queue status; compact prompt prioritizes next actions. |
| Recommendation provenance | Original ExperimentRecommendation.created_at_utc reaches TaskContext. |

## Verification boundary

- Candidate source and regression tests are on this isolated branch only.
- Tests/build/runtime are NOT RUN. GitHub Actions billing restriction and Support ticket #4910849 remain an external execution blocker.
- Static inspection and GitHub fetch-back do not substitute for execution.
- The committed Control Master snapshot remains historical/STALE; no live digest was retrieved in this task.
- No publication, remote receive/ACK or cross-session causal-consumption proof is included.

## M1A boundary

```text
M1A_G1=BLOCKED_NO_NEW_INDEPENDENT_ROOT_EVIDENCE
G1/G2/G3=NOT_ESTABLISHED
G4/G5/G6/G7/G8=OPEN
OPTION_D=RATIFIED_NO_BOOTSTRAP
PROTECTED_READS=FAIL_CLOSED
MCP_TOOL_ALLOWLIST=EMPTY
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
```

No credentials, authority assets, protected data, local checkout, secrets, branch-protection settings or production state were accessed or changed.


## Historical R2 revalidation snapshot — 2026-11-04 (superseded)

This section records the state observed at the then-current branch tip `e335a6e6f47b346f9e112ea684d7c92d31bb1ef1` (4 commits ahead). It is historical evidence only; it does not describe the later `eecf456…` or `c08b00a…` candidate tips. Use the latest PR #610 metadata and issue #454 writebacks for current refs.

- PR #610 was re-fetched: OPEN, Draft, unmerged; base `main@56e4d8b11846a8d8f3cb8cda08efd773ec235651`; HEAD `e335a6e6f47b346f9e112ea684d7c92d31bb1ef1`.
- Exact compare: 4 commits ahead / 0 behind; 14 changed paths. No review submissions or inline review threads were present at revalidation.
- PR-associated Actions runs `41935888528` and `41935825437` ended `startup_failure`; both returned zero jobs. No job or test step ran. No retry was attempted.
- The current assistant execution environment exposed no repository checkout or project-runtime executor. Its isolated container contained no IABV checkout. This is scoped to this execution surface; it is not a claim about the Owner's Windows machine.
- Static reinspection covered the queue projection, source diagnostics, digest builder, orchestrator handoff, full/compact prompt rendering, PortableContext freshness and regression patches. This is a static model review, not an independent human review and not runtime evidence.
- The source-applicability policy remains unestablished. `NOT_CONFIGURED` and `NO_FILE` stay `UNVERIFIED`; no source was reclassified as optional.
- Tests/build/runtime remain `NOT_RUN`; the committed Control Master snapshot remains historical/STALE; no live digest was retrieved.

## Source-coverage correction — 2026-11-04

Implementation follow-up was made on the same PR branch, with implementation commit `c08b00ae654e8dc453ce430549c7afc3256ce37a` (child of the previously revalidated `eecf4563f6c31c666a926c8821ba03af1ef733d0`).

- The prior `tests_state=READ_OK` declaration was unsound: it read `ControlMasterState.current_tests_state`, a best-effort mirror whose default is an empty dictionary.
- Queue coverage now reads the existing P0.29 canonical artifact `data/evolution/test_evidence/latest.json`; no new evidence store or coordinator was introduced.
- Missing artifact is `NO_FILE`; invalid JSON/read failure is `READ_FAILED`; incomplete, naive, future-dated or older-than-24-hour evidence is `UNVERIFIED`; only a well-formed record with an explicit timezone and a valid age is `READ_OK`.
- A failed or timed-out test record creates a queue item with a reference to the canonical evidence artifact.
- Regression cases were added for missing evidence, fresh passing evidence, failed evidence with artifact reference, and naive/future/stale timestamps. These tests are authored but **NOT RUN**.

The review comment on the former line-349 declaration was replied to and its now-outdated thread resolved after this source-level correction. The review is `COMMENTED`, authored under the PR author's own identity; this is not independent human approval. The attempted `REQUEST_CHANGES` action was rejected by GitHub because an author cannot request changes on their own pull request.

At the moment of the implementation commit readback, no workflow run or status check had been returned for `c08b00a…`. Earlier run `41938573679` (#527) belongs to the preceding `eecf456…` HEAD and ended `startup_failure` with zero jobs. No dispatch or retry was made.

This correction closes the specific false-`READ_OK` defect at source level only. It does not establish source-applicability policy, live Control Master state, runtime success, independent acceptance, or the full D021 temporal contract of origin/scope, generation/observation times, per-source freshness, evidence/dependency linkage and causal influence. The Space-Time organ remains `PARTIAL`; PR #610 remains Draft and unmerged.

## D021 task-bound Control Master intake — 2026-11-04

Implementation is now present on the same isolated PR branch. The exact code HEAD before this receipt update is `f33d4c8f38ebc2d9e706bccbeab192337157deec` (11 commits ahead, 0 behind; 17 paths). Base remains `main@56e4d8b11846a8d8f3cb8cda08efd773ec235651`.

### Source-level implementation

- `ControlMasterService.current_state()` captures the persisted source snapshot before rebuilding its projection. The digest carries the source state ID, normalized SHA-256 content digest, source object `control_master/latest.json`, hashed workspace-scope ID and source generation time. Missing source produces `UNAVAILABLE`; ambiguous time or scope produces `UNVERIFIED`. No freshness TTL was invented.
- The ephemeral observation envelope is removed by `save_state()` before persistence; observation provenance is not written back as governance state.
- `ControlMasterDigest` now distinguishes source generation, digest generation and task observation; carries D021 freshness separately from transport availability and work-queue state; and retains source evidence refs plus bounded per-item IDs, priorities, next actions, dependencies and evidence refs.
- `signal_status` is derived from whether the source snapshot was actually read (`READ_OK`, `NO_SOURCE_SNAPSHOT`, `READ_FAILED`), independently from `work_queue_status`. Thus a readable Control Master source can be `AVAILABLE` while queue coverage is `UNVERIFIED`. A missing source remains `UNAVAILABLE`.
- The existing `AdaptiveTaskOrchestrator` retrieves the digest once at the start of request handling, places the same digest/intake in `request.metadata` before intent classification, then binds it to the existing PerceptionSnapshot, TaskContext, AdaptiveSession and DecisionContext. The prompt consumer reuses the task-bound digest rather than making a second read.
- The receipt preserves `PROJECT_ID`, `TASK_ID` and its origin, actor session binding, operating context, memory scope, source object/revision digest, event/observation/record times, source/state/digest IDs, freshness, queue status, item identities/priorities/actions/dependencies and source/queue evidence refs.
- Verification and supersession/conflict checks are explicit: `VERIFICATION_STATUS=NOT_VERIFIED`, `VERIFIED_AT=null`, `SUPERSESSION_CONFLICT_CHECK=NOT_EVALUATED`. Signal consideration and causal influence remain `NOT_EVALUATED`.
- The local-chat path records prompt hash, prompt mode, provider and whether the final prompt contained the exact digest ID. A completed provider call is not treated as evidence that the model considered the signal or that it changed a decision.
- Full and compact prompt sections preserve source identity/freshness/times and priority actions. Both state that Control Master grants no authority/permissions and does not replace `CURRENT-STATE.md`; both prohibit inferring causal influence from mere inclusion/delivery.
- Existing bootstrap wiring was re-read from main: `bootstrap.py` constructs `ControlMasterService` and `ControlMasterDigestBuilder` and assigns them to `AdaptiveTaskOrchestrator`. This confirms static wiring only, not a live runtime.

### Regression coverage authored (not executed)

New/extended tests cover source absence and actual source generation preservation, removal of ephemeral provenance on save, digest source identity/time/scope/evidence/queue lineage, independent signal-versus-queue statuses, full/compact prompt boundaries and priority order, and a task-level probe asserting one source/queue read and that the classifier receives the task-bound digest before routing. The prior canonical TestEvidence regressions remain.

### Current verification boundary

- Latest HEAD at time of this receipt: `f33d4c8f38ebc2d9e706bccbeab192337157deec`.
- Associated Actions run #541 (`41943291373`) ended `startup_failure`; jobs endpoint returned zero jobs. No test/build step ran. Combined status checks are empty.
- `TESTS/BUILD/RUNTIME=NOT_RUN`; no independent reviewer acceptance is claimed.
- Repository is PRIVATE; PR #610 remains OPEN / DRAFT / UNMERGED; `mergeable=true` is only GitHub metadata.
- The full D021 lifecycle is not complete: no verified route reconciliation against a task-pinned authoritative `CURRENT-STATE.md`, no supersession/conflict adjudication, no verified signal-consideration/influence outcome, no cross-session causal-reuse proof and no real-task non-identical continuity experiment. The intake records these as not evaluated, not as successful.
- Live local Control Master state was not accessible in this ChatGPT execution surface; the committed snapshot previously examined remains historical/STALE.
- Source applicability policy for queue sources remains NOT_ESTABLISHED.

```text
D021_SOURCE_PROVENANCE=IMPLEMENTED_SOURCE_LEVEL
D021_TASK_SESSION_BINDING=IMPLEMENTED_SOURCE_LEVEL
D021_PROMPT_DELIVERY_RECEIPT=IMPLEMENTED_SOURCE_LEVEL
D021_SIGNAL_INFLUENCE=NOT_EVALUATED
D021_VERIFICATION_AND_CONFLICT_CHECK=NOT_EVALUATED
D021_CROSS_SESSION_CAUSAL_REUSE=NOT_PROVEN
D021_REAL_TASK_CONTINUITY_EXPERIMENT=NOT_RUN
TESTS/BUILD/RUNTIME=NOT_RUN
SPACE_TIME_ORGAN=PARTIAL
BRIDGE=BRIDGE_NOT_READY
M1A=UNCHANGED
MERGE=NOT_AUTHORIZED
```

## D021 lifecycle-state alignment and current route reconciliation — 2026-11-04

Implementation commit: `1b092edf6d81ebd09a7bc5ebe32f805b510ea417`.
Follow-up semantic-precision commit: `f2ada0ea105a10a38082742d6244806a19434d5b`.
These are direct descendants on the same PR branch; no new branch or coordinator was introduced.

### D021 §6D.6 intake states

The existing `AdaptiveTaskOrchestrator` intake now emits the exact lifecycle fields required by D021:

- `CONTROL_MASTER_SIGNAL_RETRIEVED=REPORTED` when the Control Master service reports a payload; `NOT_AVAILABLE` when its signal status is UNAVAILABLE. It is not promoted to VERIFIED without independent verification.
- `ROUTE_RECONCILED=NOT_RUN` in the product intake because the runtime consumer has not performed the authoritative `CURRENT-STATE.md` comparison.
- `SIGNAL_CONSIDERED=NO` with `SIGNAL_CONSIDERATION_EVIDENCE=NOT_AVAILABLE` until consumer-side evidence exists. Prompt delivery alone does not satisfy consideration.
- `SIGNAL_INFLUENCE=UNAVAILABLE`; the legacy `CONTROL_MASTER_DECISION_INFLUENCE` mirrors this conservative state. No changed/confirmed/no-effect causal result is inferred.
- `ACTION_OUTCOME=NOT_RUN` and `LATER_CAUSAL_REUSE=NOT_TESTED`.

The local-chat completion path preserves these states; a returned provider response updates prompt-delivery evidence but does not upgrade consideration or causal influence. Regression tests assert the available-source and unavailable-source cases.

### Current coordination episode — route reconciliation

The exact `main` ref used for the candidate remains `56e4d8b11846a8d8f3cb8cda08efd773ec235651`.

- `CURRENT-STATE.md` exact Git blob `63e1b459a13e23e1012da81826dc50727b688d8c` was fetched through the Git Blob API (tree metadata reports 1,081,478 bytes). The ordinary file-content route returned an empty body, so only the exact blob fetch is treated as content evidence.
- Its active header remains `IABV_M1A_OWNER_ISSUER_MECHANISM_INPUT_GATE_R1_20261030`, with the root issuer/provenance edge blocked, M1A G1–G3 not established, protected reads fail-closed, and the separate Lane B route permitted only when supported by the Owner's current objective and its own authorization.
- The committed Control Master snapshot is blob `d76d521e6f8d73e874a21ffe1b720dcdbcd48293`, state ID `dc840807-ef2a-4e7a-8f11-4c6362ccbcb7`, `last_updated=2026-04-19T19:23:46.389095Z`. It lists historical Super Sync objectives and is not a live November 2026 runtime read.
- For this coordination task the snapshot is `STALE`; its usefulness as a current priority signal is `UNAVAILABLE`. The task is allowed to continue as a separately authorized Lane B Space-Time development because the Owner explicitly requested continuation. The M1A blocked route is not bypassed or changed.
- Episode-level reconciliation: `CONTROL_MASTER_SIGNAL_RETRIEVED=REPORTED` (committed snapshot only), `ROUTE_RECONCILED=PARTIAL`, `SIGNAL_CONSIDERED=YES` (considered and excluded as stale), `SIGNAL_INFLUENCE=UNAVAILABLE`, `ACTION_OUTCOME=PARTIAL` (isolated candidate commits; no tests), `LATER_CAUSAL_REUSE=NOT_TESTED`.

### Execution boundary for the preceding code HEAD

At code HEAD `f2ada0ea105a10a38082742d6244806a19434d5b`, GitHub Actions run #549 (`41944077000`) ended `startup_failure`; the jobs endpoint returned zero jobs. No runner, test or build step ran; combined statuses were empty. Tests/build/runtime remain `NOT_RUN`. This run belongs to the code HEAD above; the receipt-only commit that follows has its own run state.

The Space-Time organ remains `PARTIAL`. The D021 lifecycle fields now distinguish retrieval, route reconciliation, consideration, influence, action outcome and later reuse; they do not make those stages automatically occur. M1A, `main`, protected reads, Option D, MCP allowlist, tunnel, bridge and production authorization remain unchanged.

## D021 §6D.5 consumer parity — shared reader, Evolution Center and CLI — 2026-11-04

Code implementation commit: `93497b8a2f13d5e8a9b6ffcb2de536c96f770777`.
Base remains `main@56e4d8b11846a8d8f3cb8cda08efd773ec235651`.
At code read-back: 16 commits ahead / 0 behind; 24 changed paths; repository PRIVATE.

### Shared read contract

A single existing `ControlMasterDigestBuilder.build_from_service()` adapter now owns the state/queue read classification and is reused by:
- `AdaptiveTaskOrchestrator._control_master_digest()`;
- `EvolutionCenterViewModel.refresh()`;
- `AppBootstrap.export_control_master_digest()`, and therefore the existing CLI export command.

This is a method on the existing builder, not a new service, coordinator, router or authority source. It preserves the caller's `refresh` argument when used by the bootstrap export path.

- State read failure / missing service / builder failure is explicit UNAVAILABLE.
- A queue exception remains `work_queue_status=UNAVAILABLE`; it cannot become `EMPTY_QUEUE`.
- `EMPTY_QUEUE` is produced only when the queue read returns a list and the observed source-coverage map contains only `READ_OK` entries. `NOT_CONFIGURED`, `NO_FILE`, unknown states or missing coverage remain UNVERIFIED. Source applicability policy is still NOT_ESTABLISHED; this adapter does not invent it.
- Source signal availability remains orthogonal to queue status: a successful state read can be AVAILABLE while queue coverage is UNAVAILABLE/UNVERIFIED.

### Evolution Center UI

The view-model now exposes an explicit digest status even when the service is absent; it no longer catches a queue error and substitutes an empty list. The Control Master panel in `EvolutionCenterPage.qml` now consumes the already exposed `controlMasterDigest` and `controlMasterBrief` properties.

The panel shows:
- signal availability, D021 freshness and queue state separately;
- source object, state ID, workspace-scope ID, digest ID and source revision/content digest;
- source-generation and observation times;
- source evidence refs and signal/coverage diagnostic reason;
- structured queue item ID, priority, next action, dependencies and evidence refs;
- explicit statement that Control Master is a priority signal, grants no permissions and does not replace `CURRENT-STATE.md`.

The panel's truth badge follows the digest's evidence status, not merely whether a service object is wired.

### CLI/export Markdown

`AppBootstrap.export_control_master_digest()` uses the same reader, including its `refresh` option. The existing CLI JSON payload therefore preserves the complete digest model. Its Markdown formatter now includes signal/freshness/queue status, source/state/scope identity, source digest, source/digest/observation times, signal reason, source evidence and structured queue item IDs/priorities/actions/dependencies/evidence refs. It explicitly states when a queue is UNAVAILABLE/UNVERIFIED rather than inferring emptiness.

### Regression coverage authored (not run)

- Shared reader: all six currently instrumented queue sources READ_OK + actual empty list => EMPTY_QUEUE; queue exception => UNAVAILABLE, not EMPTY_QUEUE.
- Evolution Center: queue exception preserves a readable source and its generation/scope while marking queue UNAVAILABLE; missing service becomes explicit UNAVAILABLE/unresolved.
- Bootstrap export: queue exception cannot turn into empty queue.
- Orchestrator no-service case expects explicit UNAVAILABLE digest rather than `None`.
- CLI Markdown output preserves source, freshness, queue state, times, source/item evidence and dependencies.

All are authored tests only. No local IABV execution occurred.

### Exact execution boundary

For code HEAD `93497b8a2f13d5e8a9b6ffcb2de536c96f770777`, GitHub Actions run #554 (`41945438345`) ended `startup_failure`; the jobs endpoint returned zero jobs. No runner job, test step or build step ran. Combined status checks are empty. No dispatch/retry was attempted. `TESTS/BUILD/RUNTIME=NOT_RUN`.

### Current status

```text
D021_SHARED_READ_CLASSIFICATION=IMPLEMENTED_SOURCE_LEVEL
D021_ORCHESTRATOR_CONSUMER=IMPLEMENTED_SOURCE_LEVEL
D021_EVOLUTION_CENTER_STATUS_AND_EVIDENCE_PANEL=IMPLEMENTED_SOURCE_LEVEL
D021_BOOTSTRAP_EXPORT_AND_CLI_MARKDOWN=IMPLEMENTED_SOURCE_LEVEL
D021_EMPTY_VS_FAILED_QUEUE=EXPLICIT_CONSERVATIVE_STATES
SOURCE_APPLICABILITY_POLICY=NOT_ESTABLISHED
TESTS/BUILD/RUNTIME=NOT_RUN
RUN_554=startup_failure; JOBS=0
INDEPENDENT_ACCEPTANCE=NOT_ESTABLISHED
SPACE_TIME_ORGAN=PARTIAL
BRIDGE=BRIDGE_NOT_READY
M1A=UNCHANGED
MAIN=UNCHANGED
MERGE=NOT_AUTHORIZED
```

The D021 consumer surface is statically integrated across the orchestrator, dashboard/view-model and CLI export. This does not prove a live runtime read, model consideration, causal influence, cross-session reuse or completion of the Space-Time organ. No merge or production activation is authorized.

## R18.9 — Closed-source-set completeness before EMPTY_QUEUE — 2026-11-04

Code HEAD before this receipt update: `02947d3b0e0b6963df35ef9ad3ceb2a8ca129f36`.
Base: `main@56e4d8b11846a8d8f3cb8cda08efd773ec235651`.
Compare: `20_AHEAD_0_BEHIND`; 24 changed paths.
PR #610 remains OPEN / DRAFT / UNMERGED; no merge, dispatch or production activation.

### New gap and correction

Static review found that `ControlMasterDigestBuilder.build_from_service()` validated the statuses of keys present in `last_work_queue_source_coverage`, but did not prove that all six source projectors invoked by `ControlMasterService.current_work_queue()` had each recorded a status. The earlier positive EMPTY_QUEUE unit fixture also used abstract/mismatched source keys rather than the service's actual source names.

The existing service invokes exactly these six projectors:
- `objective_repository`
- `platform_pending_queue`
- `pending_issue_repository`
- `self_examination_service`
- `runtime_audit`
- `tests_state`

The builder now holds this expected key set explicitly. A missing key or an unexpected/unregistered key forces `work_queue_status=UNVERIFIED`; an observed read failure still forces `UNAVAILABLE`; `NOT_CONFIGURED` and `NO_FILE` remain unresolved/UNVERIFIED. Only the exact expected set, with every entry `READ_OK`, can progress to `EMPTY_QUEUE` or `AVAILABLE`.

This is a completeness check over the six readers already called by the service. It does **not** decide which sources are optional or not applicable; that policy remains NOT_ESTABLISHED. No source was removed or treated as optional.

### Regression coverage authored

- Corrected the positive EMPTY_QUEUE fixture to use the six actual service source keys.
- Added a builder regression where five sources report READ_OK but `tests_state` is missing; it must stay UNVERIFIED.
- Added a regression where an unregistered source is added to an otherwise complete READ_OK map; it must stay UNVERIFIED.
- Added a service regression asserting `current_work_queue()` emits a coverage entry for each of the six invoked projectors, even when some are not configured or have no file.

These tests are authored and fetched back from the exact HEAD; **they have not been executed**.

### CI and acceptance boundary

The newest Actions run for code/test HEAD `02947d3…` is #564 (`41947273240`): `startup_failure`, jobs endpoint returned zero jobs. No runner, pytest, build or runtime step ran. Combined status checks are empty. Earlier current-candidate runs #560 (`41945907927`) and #562 (`41947165220`) also ended startup_failure with zero jobs. No manual dispatch/retry was performed.

```text
PR610=OPEN_DRAFT_UNMERGED
CODE_HEAD=02947d3b0e0b6963df35ef9ad3ceb2a8ca129f36
MAIN=56e4d8b11846a8d8f3cb8cda08efd773ec235651
COMPARE=20_AHEAD_0_BEHIND; CHANGED_PATHS=24
EXPECTED_QUEUE_SOURCE_SET=6_REGISTERED_KEYS
EMPTY_QUEUE_REQUIRES=EXACT_KEY_SET + ALL_READ_OK + NO_SOURCE_ERRORS
MISSING_OR_UNEXPECTED_SOURCE=UNVERIFIED
READ_FAILURE=UNAVAILABLE
SOURCE_APPLICABILITY_POLICY=NOT_ESTABLISHED
RUN_564=startup_failure; JOBS=0
TESTS/BUILD/RUNTIME=NOT_RUN
INDEPENDENT_ACCEPTANCE=NOT_ESTABLISHED
SPACE_TIME_ORGAN=PARTIAL
BRIDGE=BRIDGE_NOT_READY
M1A=UNCHANGED
MERGE=NOT_AUTHORIZED
```


## R18.10 — Integridad de lectura de los repositorios que alimentan la cola — 2026-11-04

PR: #610. Code/test HEAD examined: `02947d3b0e0b6963df35ef9ad3ceb2a8ca129f36`.
Base: `main@56e4d8b11846a8d8f3cb8cda08efd773ec235651`.
Related owner: #605, R20.3–R20.5:
- https://github.com/jhonf463r/Python/issues/605#issuecomment-6646604135
- https://github.com/jhonf463r/Python/issues/605#issuecomment-6646877238
- https://github.com/jhonf463r/Python/issues/605#issuecomment-6646977758

### Hallazgo

La corrección R18.9 cierra la completitud del conjunto de seis projectors llamados por `ControlMasterService.current_work_queue()`; no cierra todavía la integridad de lectura debajo de esos projectors.

1. `ObjectiveRepository.list_recent()` delega en `_collect()`. `_load()` normaliza FileNotFoundError, JSONDecodeError, OSError, errores de validación y excepciones generales a `None`. `_collect()` convierte todo `None` en orphan y ejecuta `_prune_orphans()`, que borra la fila SQLite. El projector de Control Master puede recibir entonces una lista vacía y registrar `objective_repository=READ_OK`, aunque se haya ocultado un error de artefacto y alterado el índice.
2. `PendingIssueRepository.list_recent()` usa `_load_optional()`; FileNotFoundError se convierte en `None` y la fila se omite sin diagnóstico. El projector de Control Master registra `pending_issue_repository=READ_OK` para esa devolución normal, aunque el índice señalaba un artefacto que no pudo leerse.
3. Los blobs de ambos repositorios son idénticos en `main` y en el code HEAD de #610:
   - `objective_repository.py`: `40e70a551df50e8f3c8277e4f82450c26e2b599f`.
   - `pending_issue_repository.py`: `4c7efa43995f1eae729ecf43a40cd38dd0377552`.
   Por tanto, no son cambios introducidos por PR #610.

### Adjudicación

R18.9 prueba el conjunto de seis projectors y sus estados declarados; no prueba la lectura íntegra de las filas/artefactos que esos repositorios indexan. En consecuencia, `EMPTY_QUEUE` end-to-end todavía no puede darse por demostrado mientras un loader pueda ocultar un error o una ausencia de artefacto sin exponerlo a la cobertura de fuente.

Este hallazgo enlaza con el owner técnico ya existente #605; no se crea un coordinador ni se duplica allí una reparación. La remediación debe seguir ese carril: resultados tipados FOUND / CONFIRMED_NOT_FOUND / READ_FAILED / CORRUPT / SCHEMA_UNSUPPORTED; ninguna poda de índice por un fallo distinto a ausencia confirmada; y tests negativos que comprueben la conservación de filas ante I/O/JSON/schema failures. Para PendingIssueRepository también debe distinguirse una ausencia confirmada de un registro indexado cuyo payload falta, y esa condición debe llegar al consumidor como cobertura no verificada.

### Límites de evidencia

- Es revisión estática de fuentes y fetch-back; no se abrió la SQLite de Owner ni se inspeccionaron artefactos locales.
- No se ejecutó fault injection, tests, build ni runtime; no se observó borrado real durante esta revisión.
- No se cambió código de los repositorios ni de #610.
- No se hizo comentario ni cambio de código en #605; se conserva como dependencia de propietario técnico.
- M1A, G1/G2/G3, Option D, protected reads, MCP allowlist, túnel y puente permanecen intactos.

```text
R18.9_PROJECTOR_SET_COMPLETENESS=IMPLEMENTED_SOURCE_LEVEL
OBJECTIVE_READER_ERROR_NORMALIZATION=SOURCE_VERIFIED
OBJECTIVE_READ_SIDE_INDEX_PRUNE=SOURCE_VERIFIED
PENDING_ISSUE_MISSING_ARTIFACT_SUPPRESSION=SOURCE_VERIFIED
D021_QUEUE_STORAGE_READ_INTEGRITY=BLOCKED_BY_605
EMPTY_QUEUE_END_TO_END=NOT_ESTABLISHED
TESTS/BUILD/RUNTIME=NOT_RUN
OWNER_DB/ARTIFACTS=NOT_OPENED
CODE_CHANGES=NONE
SPACE_TIME_ORGAN=PARTIAL
BRIDGE=BRIDGE_NOT_READY
M1A=UNCHANGED
MERGE=NOT_AUTHORIZED
```


## R18.11 — Segunda pasada de integridad de los seis projectors — 2026-11-04

HEAD de código examinado: `02947d3b0e0b6963df35ef9ad3ceb2a8ca129f36`.
Recepción documental previa: `5c68dbf4341ee75db5edc3b8d0a1c8a564d309b8`.
Método: fetch-back del código de servicio, cada projector y los consumidores inmediatos. Solo revisión estática; no tests ni fault injection.

### Dos fuentes adicionales con errores internos ocultos

**1. platform_pending_queue**

`PlatformPendingQueue.list_all()` enumera `task_*.json`, valida y agrega cada archivo; cualquier excepción de lectura/JSON/schema se captura con `except Exception: continue`. El archivo omitido no genera diagnóstico ni contador de incompletitud. `ControlMasterService._project_platform_pending_items()` solo puede observar la lista devuelta; al no propagarse excepción, registra `platform_pending_queue=READ_OK`. Un task persistido ilegible puede desaparecer del resumen sin volver la fuente UNVERIFIED.

Blobs:
- `platform_pending_queue.py`: `48a262d677f4bd8a01dfe2d74afac8e1e306fe59`.
- `control_master_service.py`: `7170eff8f875f0d2e6402f57348eec768949afa2`.

**2. self_examination_service / OSES**

`OperationalSelfExaminationService.current_review()` devuelve el review cacheado cuando es fresco o llama `build_review()`. Este último reúne runs, adaptive sessions, experiment runs, recommendations, scenario runs, project health, backlog, WorldModel y validation snapshot. Los helpers `_recent_runs()`, `_recent_adaptive_sessions()`, `_recent_experiment_runs()`, `_recent_recommendations()`, `_recent_scenario_runs()`, `_project_health_snapshot()` y `_improvement_backlog()` convierten excepciones en `[]`/`{}` sin una cobertura de origen que llegue al snapshot. El adaptador de Control Master registra `self_examination_service=READ_OK` tan pronto como obtiene un snapshot, por lo que el estado significa que el servicio devolvió un objeto, no que todas sus fuentes internas se leyeron completas.

El loader del último review también convierte cualquier excepción a `None` y fuerza una reconstrucción sin propagar el motivo. WorldModel y validation snapshot sí conservan algunos marcadores `unresolved_fields`, pero eso no subsana los helpers que suprimen errores devolviendo colecciones vacías.

Blob OSES:
- `operational_self_examination_service.py`: `054b1e4560b3990b691e39d2471db77f341b38bc`.

### Dos lectores con clasificación explícita en el adaptador

**3. tests_state / TestEvidence**

El projector directo distingue FileNotFoundError=`NO_FILE`, OSError=`READ_FAILED`, JSON inválido=`READ_FAILED`, estructura/campos/fecha no verificables=`UNVERIFIED`; solo registra `READ_OK` tras validar evidence_id, timestamp timezone-aware, frescura de 24 h, contadores, returncode y timed_out. La función auxiliar best-effort de otro módulo no sustituye este consumidor directo.

**4. runtime_audit**

El projector distingue archivo ausente, error de lectura e invalid JSON line; este último genera diagnóstico y `READ_PARTIAL`. No lo clasifico con los mismos defectos probados en los otros cuatro lectores.

### Adjudicación integrada

La evidencia está acotada: cuatro de las seis claves esperadas pueden subrepresentar lecturas internas fallidas:
- `objective_repository`: error normalizado a None + poda SQLite, R18.10 / owner #605 R20.3–R20.5.
- `pending_issue_repository`: artefacto ausente omitido sin diagnóstico, R18.10.
- `platform_pending_queue`: task JSON ilegible/corrupto omitido sin diagnóstico, R18.11.
- `self_examination_service`: errores de sus fuentes internas normalizados a colecciones vacías y snapshot no marcado parcial, R18.11.

`tests_state` y `runtime_audit` tienen clasificación explícita de error en el adaptador; no declaro que eso pruebe su runtime ni todas sus capas externas.

La compuerta R18.9 es una condición de completitud del conjunto de projectors, no de completitud del contenido que cada projector puede leer. Por ello `EMPTY_QUEUE_END_TO_END=NOT_ESTABLISHED` hasta que los cuatro contratos anteriores expongan resultados de lectura tipados/coverage y existan pruebas negativas. No se debe añadir un segundo lector o coordinador en #610 para evitar los fallos internos: las correcciones deben hacerse en sus owners y contratos existentes.

### Límites y ownership

- Solo revisión estática + fetch-back. No se abrió workspace, SQLite ni artefactos locales; no hubo fault injection ni ejecución.
- No se cambió código fuente ni tests.
- ObjectiveRepository sigue enlazado a #605. La asignación de owner para PlatformPendingQueue y la agregación OSES no se da por adjudicada por este recibo; requieren seguir la ruta de persistencia/servicio existente, sin crear otro coordinador.
- M1A, G1/G2/G3, Option D, protected reads, MCP allowlist, túnel y puente sin cambios.

```text
EXPECTED_PROJECTORS=6
SOURCE_LEVEL_READ_INTEGRITY=4_INSUFFICIENT / 2_EXPLICIT_ADAPTER_CLASSIFICATION
OBJECTIVE_REPOSITORY=HIDDEN_READ_FAILURE + INDEX_PRUNE
PENDING_ISSUE_REPOSITORY=MISSING_ARTIFACT_OMITTED
PLATFORM_PENDING_QUEUE=PER_FILE_EXCEPTION_SWALLOWED
SELF_EXAMINATION_SERVICE=INTERNAL_SOURCE_ERRORS_COLLAPSED_TO_EMPTY
TESTS_STATE=EXPLICIT_READ/JSON/TIME/SCHEMA_SHAPE_CLASSIFICATION
RUNTIME_AUDIT=READ_FAILED_OR_READ_PARTIAL
EMPTY_QUEUE_END_TO_END=NOT_ESTABLISHED
TESTS/BUILD/RUNTIME=NOT_RUN
CODE_CHANGES=NONE
SPACE_TIME_ORGAN=PARTIAL
BRIDGE=BRIDGE_NOT_READY
M1A=UNCHANGED
MERGE=NOT_AUTHORIZED
```
