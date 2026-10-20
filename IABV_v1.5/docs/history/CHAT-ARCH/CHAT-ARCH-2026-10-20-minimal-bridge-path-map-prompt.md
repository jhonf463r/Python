# Prompt — IABV→Codex minimal bridge path map (source-backed, no execution)

**Destino:** Claude / Sonnet.  
**Modo:** `STATIC_SOURCE_MAPPING` only.  
**Primary outcome:** build the governed IABV→Codex bridge. This task is not a general gate triage, not a new contract-wide review, and not an implementation authorization.

## Read these attachments first

1. `CHAT-ARCH-2026-10-20-protocol-anti-drift-and-bridge-goal-lock.md` — active goal-lock and anti-drift rules.
2. `IABV_CODEX_contract_review_bundle_v11_2026-10-20.md` — context for the required bridge contract; do not repeat N-88.
3. `IABV_FRONTIER_STATIC_READ_ADJUDICATION_2026-10-19.md` — records that the bounded consumer/loader document lookup did not identify either component.
4. `IABV_OWNER_GATE_DECISION_SECOND_HUMAN_UNAVAILABLE_2026-10-20.md` — the quorum decision is settled and must not be asked again.

The published GitHub source baseline is `jhonf463r/Python @ d3a4212b6de36254bf45d5e655d684d0640a0706`. It is not evidence about the private/local dirty checkout. Verify each fetched file's blob SHA and report exact source URLs.

## Task

Produce one artifact named `IABV_CODEX_MINIMAL_BRIDGE_PATH_MAP` that traces the *actual existing public-source links*, not intended architecture, across:

`IABV task/intention → typed authorization/correlation → dispatch/adapter → Codex transport and executable resolution → bounded candidate → terminal status and independently verifiable baseline/diff/changed-path receipt → identified IABV verifier/consumer → separate owner decision`.

Use source-backed call chains. Start with the previously identified public paths that directly concern task execution and learning, including:

- `IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py`
- `IABV_v1.5/src/iabv_v15/services/tools/tool_memory.py`
- `IABV_v1.5/src/iabv_v15/services/tools/interaction_learning_service.py`
- `IABV_v1.5/src/iabv_v15/services/adaptive/task_context_assembler.py`
- `IABV_v1.5/src/iabv_v15/services/tools/interaction_mode_selector.py`

Follow only direct imports/callers/callees from this route and the already-documented Codex adapter/transport references in the canonical public handoff/README. Keep the investigation bounded to direct bridge connectivity; do not perform a broad repository or identity/auth audit. If a required path cannot be located in this scope, label it `NOT_FOUND_IN_BOUNDED_SCOPE` and stop searching that branch.

## Required output

### A. End-to-end edge table
For each edge, give:
- producer/caller and consumer/callee;
- exact path, pinned blob SHA, line/symbol anchor and source link;
- data and correlation identifiers actually passed (task, proposal, thread, turn, attempt, result, baseline, diff, receipt);
- whether the edge is linked in source, only proposed, owner-reported, or unresolved;
- concrete consequence for the bridge.

### B. Smallest technical gap set
Name only the missing links that prevent the source-backed end-to-end path. Distinguish:
- existing components actually called;
- components that exist but are not linked;
- contracts/types that are absent in inspected scope;
- proposed controls with no implementation evidence.
Do not turn this into a global satisfaction matrix.

### C. Minimum next engineering slice
Select one smallest, coherent bridge slice with:
- exact files/call sites to connect;
- minimum typed request/result/receipt fields;
- correlation and idempotency semantics;
- required independent consumer/check;
- acceptance oracles to be tested only after separate authorization;
- known blockers that make this slice non-executable under current permissions.

It must be specific enough to guide a later implementation task without inventing a consumer or a safe runtime.

### D. Decision and handoff
Return `BRIDGE_PATH_MAP = COMPLETE` or `INCOMPLETE`; `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = NOT_AUTHORIZED`; `BRIDGE_NOT_READY`. Then give one exact next actor/task. If no existing source chain can be found, say so and identify the smallest missing artifact/identity; do not initiate another broad audit.

## Non-negotiable boundaries

- Do not execute code, tests, builds, runtime, preflight, canary, Codex CLI/App Server or a model turn via Codex.
- Do not inspect local checkout, M0A, `data/`, SQLite, credentials, secrets or private config.
- No auth, installs/updates, quota checks, new plan, extra spend, source edits, GitHub writes, commit/push/merge or promotion.
- Do not re-review FS-V10-01/FS-V10-02, re-open N-88, re-open FS-01, re-triage global gates, or ask whether a second human exists.
- `SECOND_INDEPENDENT_HUMAN = UNAVAILABLE` is settled. Quorum-dependent acts remain blocked; do not infer an exception.
- Do not equate source declarations or a design proposal with actual connectivity, enforcement or runtime behavior.

**Success means progress toward the actual bridge, not another collection of blockers.**
