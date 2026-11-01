# UAAL — Control Master signal-intake reconciliation R1

**Date:** 2026-10-31 (America/Bogota)  
**Task:** `IABV_CONTROL_MASTER_SIGNAL_INTAKE_GAP_RECONCILIATION_R1_20261031`  
**Scope:** documentation/method refinement only; live Control Master runtime was not accessed.  
**Base:** `main@f39daa5231c5c85c83a7545879aa522286525fef`  
**Decision:** add a mandatory Control Master signal-intake gate to D021 and the existing Space-Time/new-chat front doors. Do not create another router, memory, coordinator or service.

## 1. Why this reconciliation was opened

The Owner identified a repeated coordination failure: participating chats were not consistently consulting the IABV Control Master/evolution panel before selecting their next action. The intended consequence is that the panel's priorities, dependencies, evidence and next-action cues influence the next decision through the existing UAAL chain.

The repository already contains a Control Master service and digest path. The gap is therefore not accurately described as “no control panel exists.” The relevant question is whether the current signal is fresh, is actually received by the session, survives every applicable prompt path, changes action selection, and is reconciled with the canonical task route.

## 2. Verified repository observations

All observations below are static GitHub observations at the exact base commit. They do not prove the local app is running or that a current runtime state was observed.

| Observation | Exact source | Evidence |
|---|---|---|
| The canonical IABV route is a separate authority from the Control Master panel. | `docs/history/CHAT-ARCH/CURRENT-STATE.md` | Current-state path blob at base: `63e1b459a13e23e1012da81826dc50727b688d8c`; normal content read returned an empty body, exact blob retrieval recovered 1,074,956 characters / 15,079 lines. |
| The versioned Control Master snapshot is old. | `data/evolution/control_master/latest.json`, `latest.md` | JSON blob `d76d521e6f8d73e874a21ffe1b720dcdbcd48293`; Markdown blob `e97700bcafb5b33fcf5b3712b8fe97d18ce5b244`; Markdown states `Generado: 2026-04-19T19:23:46.389095+00:00`. |
| The stored snapshot reports four active objectives and zero completed objectives. | `data/evolution/control_master/latest.md` | The dated snapshot is not evidence of the present runtime queue on 2026-10-31. |
| The CLI export route exists in source. | `src/iabv_v15/__main__.py`; `src/iabv_v15/cli/control_master.py` | Blobs `6710dd5600fbc35c298b88afc83183ef759615ca` and `077557fa07c08d4c00834a03daa5670f97e6bcbd`; `python -m iabv_v15 cm export-digest` is wired through the existing CLI. |
| The objective record for CLI export still describes the entrypoint as missing and remains active/progress 0. | `data/evolution/objectives/obj-super-sync-cli-export.json` | Blob `f2bd144eef17d25e7e7a14ca79f1ca39bb9e9d38`; this is a source-vs-governance-record reconciliation gap, not sufficient evidence to mark the objective complete because no CLI execution or acceptance verification was performed. |
| The service projects a unified priority queue. | `src/iabv_v15/services/evolution/control_master_service.py` | Blob `d6a7b8d61e6e20f3a55e5359eb0023ef58757cb2`; `current_work_queue()` aggregates objectives, platform pending items, pending issues, high/critical OSES findings and failed/stalled runtime-audit episodes, with `next_action`, dependencies, evidence refs and priority breakdown. |
| The digest is built and can be injected into a full local prompt. | `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`; `src/iabv_v15/services/llm/system_prompt_builder.py` | Blobs `41f6f7b6157226a1c6004591ddff4e36ff6f6da5` and `8dfded0bfb1e08fbb691e293f566a1551bf71ed3`; the full local-chat path calls `_control_master_digest()` and passes `control_master_digest` into `build()`. |
| The compact local prompt omits the digest parameter. | `src/iabv_v15/services/llm/system_prompt_builder.py` | Same blob; `build_compact()` accepts world model, environment self-model and governance rules, but not `control_master_digest`. |
| Several read failures can degrade silently. | `adaptive_task_orchestrator.py`; `evolution_center_viewmodel.py` | Orchestrator exceptions can return `None` and queue errors can become `[]`; Evolution Center digest errors can become `{}`. This is a static source observation, not a reproduced runtime incident. |
| Outcome propagation is opt-in by task metadata. | `src/iabv_v15/services/adaptive/task_outcome_recorder.py` | Blob `fddf3f90e15b4ec74ad813441ceeac18458e0118`; propagation requires `control_master_objective_id` or `control_master_unresolved`. It is not universal auto-linking. |
| The existing Evolution Center view model exposes a Control Master digest property. | `src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py` | Blob `af40921e7e56ccb53b059f1b08f19644f4a07a6b`; the view model reads state plus work queue and exposes `controlMasterDigest` / `controlMasterBrief`. This alone does not prove current UI rendering or a fresh local snapshot. |

## 3. Distinguish the existing panels

The protocol must not collapse these distinct organs:

- **ControlMasterService / ControlMasterDigest:** governance state, objectives, work queue, risks, decisions, unresolved items and next actions. This is the signal relevant to selecting project work.
- **Evolution Center:** a view-model/UI surface that exposes the digest and other evolution/self-examination signals. A visible panel is only as current as the source and observation time.
- **ProactiveDashboardService:** pending human approvals and learned approval policies. It is not the canonical work-priority router and does not replace the Control Master queue.
- **DashboardPage:** summary counts/provider health. It is not the authority for task priority.

## 4. First open causal edge

`CONTROL_MASTER_SIGNAL_TO_PARTICIPATING_CHAT_DECISION_BINDING_NOT_ESTABLISHED`

Sub-edges:

1. A fresh, source-bound runtime digest is not available to this cloud session.
2. The committed `latest.json/md` snapshot is dated 2026-04-19 and cannot be treated as current on 2026-10-31.
3. The compact local prompt omits the digest even though the full prompt path includes it.
4. Error fallbacks can conceal unavailable state as empty/null data.
5. The cross-chat handoff does not yet require a correlated Control Master signal receipt or record how it changed the next action.

## 5. Method decision

Add D021 §6D — Control Master signal intake and decision binding — and wire it into the existing front doors and new-chat kit.

Mandatory semantics:

- `CURRENT-STATE.md` remains the sole authority for IABV active task, canonical next action, technical gates and permissions.
- A Control Master signal is an additional governance/priority input, never a competing router or source of authorization.
- Record source, workspace/project scope, generation time, observation time, state ID, digest identity and queue item IDs/evidence refs.
- Classify the signal as `FRESH`, `STALE`, `UNAVAILABLE`, `UNVERIFIED`, `CONFLICTED` or `NOT_APPLICABLE`.
- A successfully retrieved empty queue is different from a failed read. Never convert exceptions, missing properties or blank payloads into “no pending work.”
- A stale committed snapshot may be used as historical evidence only. It must not guide a current action as if it were live.
- Reconcile applicable work-queue entries against the current objective, dependencies, acceptance, terminal fingerprints and exact authority. The highest score is not permission and does not override D019/D020 or the Owner's current objective.
- Every material IABV session must state whether the Control Master signal was actually retrieved and whether it changed or confirmed the chosen next action.
- If the local runtime/panel is not already available through an authorized read path, do not start it, run a CLI, open protected data, inspect secrets or invent its contents. Mark the signal unavailable and proceed only on independently sufficient evidence within authority.

## 6. Limits and non-claims

- No local Evolution Center window or live local database was observed in this session.
- No runtime, CLI, test, build, product source, permission, credential, protected-read or tunnel operation was performed.
- Static source wiring does not prove runtime invocation, UI display, fresh digest delivery, decision influence or automatic cross-session synchronization.
- No Control Master snapshot was refreshed or overwritten.
- No M1A gate, Option D boundary, protected-read restriction or product authorization changed.
- PR #589 is a separate open authorization-protocol candidate and was not merged or modified by this task.

## 7. Acceptance criteria for a later causal demonstration

A later, non-identical session must:

1. Retrieve the live canonical route from an exact main SHA.
2. Retrieve a Control Master digest from a supported authorized source in the same task episode, or explicitly record why it is unavailable.
3. Preserve provenance and timestamps and distinguish a true empty queue from a failed read.
4. Show which queue/objective signal was considered and why it was relevant or rejected.
5. Record one next action whose selection was changed or explicitly confirmed by that signal.
6. Verify the selected action's observable outcome and owning-record update/fetch-back.
7. Repeat on a separate non-identical task before claiming generalized causal reuse.

Until then:
```text
CONTROL_MASTER_SIGNAL_INTAKE=DOCUMENTED_CANDIDATE
LIVE_RUNTIME_SIGNAL=NOT_OBSERVED
CROSS_CHAT_SIGNAL_DELIVERY=NOT_PROVEN
COMPACT_PROMPT_COVERAGE=SOURCE_GAP_OBSERVED
SILENT_EMPTY_DEGRADATION=SOURCE_GAP_OBSERVED
CAUSAL_DECISION_INFLUENCE=NOT_PROVEN
GENERALIZATION=NOT_TESTED
M1A_G1=BLOCKED; UNCHANGED
OPTION_D=RATIFIED_NO_BOOTSTRAP
PROTECTED_READS=FAIL_CLOSED
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
TESTS_BUILD_RUNTIME=NOT_RUN
```


## 8. ChatGPT-native transport review and failure correction

OpenAI's official product documentation was checked for Projects, memory, connected apps and GitHub. A ChatGPT Project can share its files, instructions and chats among chats inside that Project. Project-only memory scopes cross-chat references to that Project. ChatGPT's GitHub connection retrieves permitted repository content on demand and does not create a continuously synchronized GitHub index; availability varies by plan/workspace/product surface, and the standard GitHub app is read-only.

Sources:
- https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- https://help.openai.com/en/articles/8590148-memory-in-chatgpt
- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt

**Failure found:** the coordinator asked the Owner to upload a current digest before fully checking the native ChatGPT Project route and did not consistently prioritize already-available canonical GitHub retrieval. This introduced avoidable manual relay. The correction is the retrieval ladder: Project Sources/relevant chats → authorized GitHub → another already-connected authorized source → one narrowly identified Owner-local artifact only when the evidence is proven to exist solely in an inaccessible local/runtime source.

**Boundary:** a ChatGPT Project shares context only among chats inside that Project. It does not automatically deliver files to Codex/Claude or expose the Owner's local filesystem/runtime. The committed Control Master snapshot remains stale (2026-04-19); no live local Control Master digest was retrieved. Therefore LIVE_RUNTIME_SIGNAL=NOT_OBSERVED. No runtime, CLI, protected read, bridge, implementation, test, build, credential, permission or tunnel operation was performed. M1A/Option D gates remain unchanged.

The copy-ready one-time Project configuration is in CHAT-ARCH-2026-10-31-CHATGPT-PROJECT-INSTRUCTIONS-R1.md. This GitHub change does not configure native ChatGPT Project settings.

## 9. Acceptance evidence and limits

CHATGPT_PROJECT_NATIVE_CONTEXT=DOCUMENTED_FROM_OFFICIAL_OPENAI_HELP
PROJECT_SETUP_IN_OWNER_UI=NOT_CONFIGURED_BY_THIS_SESSION
PROJECT_SHARED_CONTEXT_CONSUMPTION=NOT_OBSERVED
GITHUB_CONNECTOR_IN_CURRENT_SESSION=AVAILABLE_AND_USED_FOR_REPOSITORY_ACCESS
CROSS_PRODUCT_GITHUB_ACCESS=SESSION_SPECIFIC; NOT_ASSUMED
LIVE_LOCAL_CONTROL_MASTER_DIGEST=NOT_OBSERVED
OWNER_MANUAL_RELAY_REDUCTION=PROTOCOL_DESIGNED; CAUSAL_REUSE_NOT_YET_VERIFIED
MAIN_ADOPTION=NOT_MERGED
M1A_G1=BLOCKED; UNCHANGED
OPTION_D=RATIFIED_NO_BOOTSTRAP
PROTECTED_READS=FAIL_CLOSED
LOCAL_RUNTIME/CLI/BRIDGE=NOT_RUN
