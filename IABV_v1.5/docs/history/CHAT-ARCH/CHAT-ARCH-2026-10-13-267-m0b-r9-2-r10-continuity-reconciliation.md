# CHAT-ARCH-2026-10-13-267 — M0B R9.2/R10 continuity reconciliation: correlated adaptive return contract

- **Episode ID:** CHAT-ARCH-2026-10-13-267
- **Reconciliation time (America/Bogota):** 2026-10-13, approximately 20:20, for the newly supplied conversation material
- **Public GitHub baseline before this documentation write:** main at 559f4ea20a9a9163cd9a9839b11d9991933f8c07, verified through the GitHub commits endpoint
- **Inputs:** owner-supplied M0B-R9.2 report, R10 design text, and proposed future implementation package; focused independent read-only verification of relevant public source at the pinned baseline
- **Classification:** M0B_R9_2_R10_DESIGN_TARGET_RECONCILED_IMPLEMENTATION_AND_LOCAL_ACCESS_GATES_OPEN
- **Posture:** KEEP_BLOCKED for local M0A access, implementation, tests, and runtime/launch
- **Primary engineering edge:** RESULT_TO_ADAPTIVE_CONSUMER_CORRELATED_RECEIPT_CONTRACT_UNIMPLEMENTED
- **Independent access edge:** MCP_SERVER_AND_CHECKOUT_IDENTITY_UNRESOLVED

## 1. Evidence and provenance reconciliation

The current public main pointer was verified as 559f4ea20a9a9163cd9a9839b11d9991933f8c07 before this documentation-only write. The current public source objects for the two R9.2 anchors were independently fetched at that exact commit:

- [domain/models.py, ToolResult at line 1319](https://github.com/jhonf463r/Python/blob/559f4ea20a9a9163cd9a9839b11d9991933f8c07/IABV_v1.5/src/iabv_v15/domain/models.py#L1319-L1334), blob a9033d21052c519e09f482097599c704a62ea916. The reported blob SHA and line anchor match.
- [control_center_viewmodel.py, ingestExternalResponse at line 14239](https://github.com/jhonf463r/Python/blob/559f4ea20a9a9163cd9a9839b11d9991933f8c07/IABV_v1.5/src/iabv_v15/ui/viewmodels/control_center_viewmodel.py#L14239-L14256), blob 628848c631e36b47b4a5b63b9e68d62687625235. The reported blob SHA and line anchor match.

The historical R9.1 raw-query line discrepancy remains unresolved. It does not override the two current pinned blob/line verifications; its cause is not inferred and it must not trigger another general search absent new discriminating evidence.

The root README.md and IABV_v1.5/README.md fetches both returned 404 in this reconciliation. No README content was inferred; continuity was recovered from AGENTS.md and the canonical history documents.

The evidence above is public-source evidence only. No local M0A source was read, and the public checkout is not a substitute for the reported dirty local worktree.

## 2. Material source-level result: preliminary sandbox status can contaminate success metrics

At the pinned public baseline, ToolTeachService.execute_task calls the sandbox and immediately passes its result to ToolMemory.remember_result before proceeding to approval handling or the adapter's later run: [tool_teach_service.py lines 817–825](https://github.com/jhonf463r/Python/blob/559f4ea20a9a9163cd9a9839b11d9991933f8c07/IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py#L817-L825).

ToolValidator explicitly distinguishes awaiting external response as UNVALIDATED and a successful sandbox as SANDBOX_PASS: [tool_validator.py lines 11–39](https://github.com/jhonf463r/Python/blob/559f4ea20a9a9163cd9a9839b11d9991933f8c07/IABV_v1.5/src/iabv_v15/services/tools/tool_validator.py#L11-L39). However, ToolMemory increments the card's success_count whenever result.success is true, without conditioning that increment on validation status or stage: [tool_memory.py lines 35–49](https://github.com/jhonf463r/Python/blob/559f4ea20a9a9163cd9a9839b11d9991933f8c07/IABV_v1.5/src/iabv_v15/services/tools/tool_memory.py#L35-L49).

**PROVEN_BY_SOURCE:** the public implementation permits a successful preliminary sandbox result to increment the same card success counter used by ordinary results. This is a concrete metric-contamination risk; it does not prove a live runtime incident or that every adapter's sandbox result is successful. A future fix must define stage- and adapter-specific eligibility instead of treating every result.success as a final external consultation success.

ToolResult at the pinned source has result_id and task_id but no first-class execution_id, stage, or adaptive-consumer receipt fields in the inspected declaration. The viewmodel's ingestExternalResponse accepts text and uses the last active adaptive payload; the existing source path does not yet demonstrate an enforced, automatic, correlated handoff from every external ToolResult into that ingestion and a durable consumer receipt. See the linked source anchors above and the already supplied R9.2 route analysis. The latter route-wide finding is recorded as continuity input; this entry does not claim a local-runtime observation.

## 3. Consolidated M0B-R10 design target

The supplied R10 material carries the target label DESIGN_CONTRACT_ACCEPTED_PENDING_IMPLEMENTATION_AUTHORIZATION, while also describing the decision text as proposed/subject to owner confirmation. To avoid promoting a pasted proposal into an unambiguous implementation grant, this entry records the design target for continuity but does not infer permission to inspect M0A, edit code, run tests, launch Codex/App Server, or incur costs.

The minimum contract to evaluate/implement after the relevant approvals remains:

- task_id identifies the logical task.
- execution_id identifies one attempt, including preflight and sandbox attempts.
- result_id identifies the result produced by that attempt.
- stage distinguishes preflight, sandbox, and final execution.
- Adapter and destination remain bound to the authorized task.
- Authorization reference and approved-content digest are preserved where applicable.
- Capture provenance distinguishes automatic correlated capture from manual_user_supplied material.
- Validation state is explicit; a pending capture, wrong destination, preliminary stage, stale result, or mismatched task is ineligible as verified final success.
- evaluation_id and a durable consumer receipt link the adaptive evaluation to task, execution, result, and consumer.
- Duplicate delivery returns the existing receipt or remains incomplete; it cannot produce duplicate metrics or an equivalent second evaluation.
- Historical records missing stage or execution identity remain legacy/unattributable; do not invent their provenance or rewrite old counters.
- Rules remain adapter-specific: conversational capture is required for external-assistant consultations, not imposed on non-conversational adapters.
- A manual-response policy is still a separate owner/domain decision; manual input must never be relabeled as automatic verified capture.

## 4. Metacognitive and symbiosis delta

The system model is now explicitly three planes: (1) the user-facing IABV interface, which exposes status and decisions; (2) the background bridge/coordinator, which prepares, dispatches, correlates, validates and routes results; and (3) the executor environment, where Codex performs the work permitted to it. The target is not another chat screen: it is a governed background coordination path with visible state in the foreground.

The continuity method remains a traceable episode chain: objective and temporal context → evidence and provenance → hypothesis/causal boundary → authorized discriminating action → observation and verification → reconciliation → knowledge/method/routing delta → persistence → future reuse check. **Persistence is not proof of learning; learning is not proof of causal improvement.** Causal reuse requires a later decision trace showing that a validated prior result changed a decision and that the change improved the relevant outcome.

AI/tool-first retrieval remains mandatory: do not ask the owner to copy source code while an authorized automated route remains available. Conversely, one blocked local gate must not freeze independent public-source work, and must not be bypassed through another reader. Distinguish published source, local worktree, design hypothesis and runtime observation in every handoff.

## 5. Current gates and boundaries

- Public source/design review: may proceed when it adds discriminating evidence; do not repeat the R9.2 scan without a new question.
- Local M0A identity/content: UNPROVEN; direct MCP server/checkout identity and an applicable scoped read decision remain unresolved.
- Implementation: NOT AUTHORIZED by this design-only continuity update.
- Tests/builds/runtime and launch of IABV, Codex or App Server: NOT AUTHORIZED; existing Owner choice C / KEEP_BLOCKED remains operative.
- Install/update, new authentication, credential inspection, paid API/credits or extra spend: NOT AUTHORIZED.
- Documentation-only traceability update: explicitly requested in the current owner message and performed separately from source/code changes.

## 6. Next discriminating step

Do not restart a broad audit or repeat the raw-file lookup. The next engineering sequence, only after explicit applicable authorization, is: (1) establish the exact local M0A target and legitimate scoped read path; (2) compare that worktree against the pinned public route without overwriting dirty work; (3) implement the minimum stage/attempt/provenance contract and correct preliminary success eligibility; (4) wire the correlated validated result to the existing adaptive consumer and durable receipt; (5) execute only separately authorized offline tests; (6) later, under separate authority, verify a real Codex turn/return. Keep ChatGPT autonomous turn initiation and correlated return as a separate unproven edge.

No local checkout was read. No source code was changed. No tests or processes were run. No installation, authentication, API request to an AI model, paid usage or code promotion occurred in this episode. This entry and the related continuity-index updates are documentation-only.
