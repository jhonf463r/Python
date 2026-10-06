# CHAT-ARCH-2026-10-06-101 — UAAL-RQ13 PERSISTED PACKAGE RECOVERY / SOURCE CORRELATION

## Episode

Date: 2026-10-06
Related runtime: PID `26220`
Harness SHA:
`50779B1DD321258729E1BB9ABEBA4D04ACBBFCC45CF0FDFDD0555AE5F6C1FA37`
Baseline:
`e46d8304167708bed0764d3bf2be8fd6643e8944`

## FACT

For the single runtime already executed, forensic read-only inspection recovered:

- `portable_context/latest.json`, 229,015 bytes, SHA-256
  `C777CF29353A7E9F09202A662BC1C8869BBADF6258C0D97281BCA2E0B510A171`;
- historical JSON
  `d3efa58a-7dd1-44e4-9302-055e3be8e510.json`, 228,691 bytes, SHA-256
  `00B8A2FFC9E37529BF963C95745CE90F73C6BC1D67616EFA206A539223684E5C`;
- both contain package ID `d3efa58a-7dd1-44e4-9302-055e3be8e510`;
- persisted `active_objective_id` is
  `f8b087e1-c1fe-477a-80e9-faaaedb61740`;
- persisted `site_id` is empty;
- package internal timestamp is `2026-10-06T20:07:17.664505Z`;
- the package files were created around `20:08:44.52Z`;
- the incident report directly identifies PID `26220`.

Runtime identity evidence from the same run already established:
- PCS object ID `1536859679984`;
- ObjectiveRepository object ID `1536829743392`;
- `pcs.objective_repository is boot.objective_repository == true`;
- common storage object ID `1536828289616`.

No serialized `LATEST_ACTIVE_TRACE` or exact returned package object was recoverable.

## SOURCE CORRELATION

Baseline source inspection establishes:

1. `current_package(refresh=True)` bypasses the cache freshness-return path and calls `build_package(...)`.
2. `build_package()` constructs one `PortableContextPackage` object.
3. It persists `latest.json`.
4. It updates package metadata with archive paths and persists `latest.json` again.
5. It then returns that same in-memory `package` object.

Therefore the baseline source contract establishes a direct semantic relationship:
`build_package package object → latest.json persistence → return package`.

However, this does NOT retroactively prove that the runtime-returned object was captured or that no concurrent overwrite occurred between target completion and forensic read-back.

Baseline source also establishes that when `task_context=None`, `_goal_context()` queries `_latest_objective()` for OBJECTIVE/PROJECT/TASK through the injected ObjectiveRepository, and maps the resulting node metadata into package `active_objective_id` and `site_id`. Exceptions in `_latest_objective()` are collapsed to `None`.

The recovered package's `active_objective_id` exactly matches the controlled TASK ID established earlier:
`f8b087e1-c1fe-477a-80e9-faaaedb61740`.

This makes the active-objective attribution **strongly supported by source semantics + persisted artifact + temporal correlation**, but it does not replace direct runtime capture of `latest_active()` success/return.

## CLASSIFICATION

`RECOVERABLE PERSISTED ONLY / SOURCE-ASSISTED PACKAGE CORRELATION`

RQ13 package evidence has advanced from merely “package existed” to:
- runtime repository identity observed;
- persisted package recovered;
- persisted objective attribution matches the controlled TASK;
- baseline source links package construction/persistence/return semantics.

Still open:
`runtime returned package object ↔ persisted package exact equality`.

## METHOD DELTA

New invariant:
`source-level return/persistence semantics + persisted artifact ≠ direct runtime return capture`.

For one-shot evidence experiments, a post-target reporting failure should be classified separately from target failure. Recovery may strengthen attribution, but must never fabricate an unobserved return value.

## ROUTING DELTA

The forensic recovery edge is exhausted for the key returned-object question: exact target return data was not serialized.

Next first open edge:
`external harness reporting correction (event-key collision) → self-test → new harness SHA → fresh human authorization → one new bounded RQ13 run capturing return/persisted correspondence`.

The next runtime, if authorized, is a new observation episode. It must not be presented as the same PID/run.

Do not rerun the old run. Do not infer the old returned package from the persisted package alone.

## LEARNING STATUS

No new IABV causal-learning evidence.

Project status remains:
- lower-layer adaptive learning mechanism: PRESENT/OBSERVED;
- selector-level learned-state influence: EVIDENCED;
- strong causal future-decision learning: NOT PROVEN.

