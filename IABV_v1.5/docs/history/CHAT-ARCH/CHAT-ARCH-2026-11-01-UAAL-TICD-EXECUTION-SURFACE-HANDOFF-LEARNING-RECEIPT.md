# UAAL/TICD — Execution-surface handoff learning receipt

**Date:** 2026-11-01 (America/Bogota)
**Task episode:** `TICD_LOCAL_MSI_MAINTENANCE_SETUP_2026_11_01` → R2 correction → R3 proposal
**Project:** `IABV-TICD-LAB` / `jhonf463r/Python`
**Status:** `TRANSCRIPT_RECONCILED; ROOT_CAUSE_IDENTIFIED; DOCUMENTATION_PROPOSAL_ADDED_TO_DRAFT_PR; LOCAL_TASK_NOT_CREATED; R3_RESULT_NOT_RECEIVED; LATER_CAUSAL_REUSE_NOT_TESTED`
**Source artifact:** owner-supplied chat transcript, inspected in the originating private conversation; source content/digest verified there but the private attachment hash and payload are not republished in this public repository.
**Evidence class:** the pasted conversation is directly available to this coordinator; local observations and Codex results inside it remain actor-reported unless independently inspected from the MSI.

## 1. Episode reconstruction

1. A local state-reconciliation report was created outside the eight original documents. The supplied transcript reports the eight original hashes unchanged and tests/build/runtime not run.
2. The Owner identified the central product requirement: participating AIs should recover shared files and context through existing authorized routes rather than making the Owner carry the same files between chats.
3. A draft documentation proposal, PR #595, was created to operationalize D021 task-conditioned profiles, artifact manifests, local toolchain maintenance and the cloud/local split. It remained a draft; it was not merged to `main`.
4. The local-maintenance prompt was aimed at T3 Scheduled Tasks on the MSI. The Codex operator's supplied report says the UI exposed weekdays or minute intervals but no monthly day-of-month selector. No task or report was created.
5. The next assistant response proposed Windows Task Scheduler plus `codex exec`, but the first instruction incorrectly told the recipient to paste into the same T3/Codex thread and required the T3 thread's `Supervised` permission.
6. The Owner clarified that the recipient was the external Codex application, not the Codex provider inside T3. The external Codex report showed `Full Access` on its own surface, correctly noted that this did not establish T3 permission, and stopped without creating files or tasks.
7. The corrected R3 prompt then explicitly identified external Codex on Windows as the operator, Codex CLI as a read-only child process, Windows Task Scheduler as the scheduler, and T3 as uninvolved. The pasted transcript ends with that prompt; it contains no R3 execution result.

## 2. Root cause and causal classification

**Primary cause:** `HANDOFF_TARGET_AND_PERMISSION_DOMAIN_MISMATCH`.

The handoff mixed three distinct execution/control surfaces: external Codex Desktop, the Codex provider inside a T3 thread, and Windows Task Scheduler. It also imported a T3-specific `Supervised` requirement into an operation whose selected executor was external Codex. That produced a false precondition and a blocked attempt before the intended Windows-native path was evaluated.

**Contributing defects:**

- The handoff header did not declare the exact destination actor, app, execution surface, control plane and excluded surfaces.
- The phrase `T3/Codex` and the instruction to use the same T3/Codex thread contradicted the actual external-Codex target.
- Permission was treated as a tool-independent property instead of being scoped to a particular application/thread/process and operation.
- The scheduler capability comparison was too narrow: a limitation observed in T3's UI was allowed to dominate an alternative Windows-native scheduler route.
- The proposed architecture did not initially distinguish the outer operator's bounded writes (runner/task creation) from the child Codex process's read-only sandbox.

**Not the cause:** the R2 report does not show a Codex CLI failure, a Windows Task Scheduler failure, an authentication failure or a failed inventory. Those operations were not run. It also does not prove that every T3 version or backend lacks monthly scheduling; it records the form observed in the supplied local session.

## 3. Durable lessons

1. Every actionable handoff must bind `DESTINATION_ACTOR_TYPE`, `DESTINATION_APP_AND_VERSION`, `EXECUTION_SURFACE`, `CONTROL_PLANE`, `HOST_AND_OS`, `PROCESS_ACTOR`, `SCHEDULER_OR_TRIGGER_OWNER`, `T3_INVOLVEMENT`, `PERMISSION_DOMAIN`, `PERMISSION_SOURCE_AND_SCOPE`, `OWNER_AUTHORIZATION_SCOPE`, and exact side effects.
2. Permission is local to its surface. `CODEX_EXTERNAL_DESKTOP Full Access` is not evidence of T3 `Supervised`, Windows administrator privileges, Task Scheduler rights, or Codex CLI sandbox settings. T3 `Supervised` is not evidence about external Codex.
3. The top of every user-mediated prompt must state plainly where to paste/run it and name applications explicitly. Avoid ambiguous `T3/Codex` shorthand.
4. A permission check is relevant only if its application/process is part of the chosen execution path. Do not query T3 when `T3_INVOLVEMENT=NONE`.
5. Use capability-matched alternatives. A T3 scheduler UI limitation does not block Windows Task Scheduler; a provider's desktop UI and a non-interactive CLI are different execution mechanisms.
6. For a two-process architecture, bind outer and child boundaries separately. The external operator may create only the explicitly authorized runner and scheduled task; `codex exec` must independently run with an explicit read-only sandbox. Child sandbox settings do not constrain the outer process.
7. A prompt being prepared or pasted is not task completion. The Windows task must be inspected, started and observed; report and manifest must be read back and hashes recomputed. A successful immediate run does not yet prove recurring execution on a later monthly boundary.
8. Reuse the existing D021/UAAL stores and receipt mechanism. Do not add a second memory database, router, scheduler service or orchestration framework to remember this lesson.

## 4. R3 state at transcript cutoff

```text
R2_OUTCOME=BLOCKED
R2_ROOT_CAUSE=HANDOFF_TARGET_AND_PERMISSION_DOMAIN_MISMATCH
R2_SIDE_EFFECTS=NONE_REPORTED
R3_DESTINATION_ACTOR=CODEX_EXTERNAL_DESKTOP
R3_EXECUTION_SURFACE=CODEX_DESKTOP_ON_WINDOWS
R3_PROCESS_ACTOR=CODEX_CLI_CHILD
R3_SCHEDULER=WINDOWS_TASK_SCHEDULER
R3_T3_INVOLVEMENT=NONE
R3_OWNER_AUTHORIZATION=RECEIVED_FOR_ONE_RUNNER_ONE_TASK_AND_IMMEDIATE_TEST
R3_PROMPT=PREPARED_AND_SUPPLIED_TO_OWNER
R3_EXECUTION_RESULT=NOT_PRESENT_IN_SOURCE_TRANSCRIPT
WINDOWS_TASK=NOT_CREATED_AS_OF_TRANSCRIPT_CUTOFF
RUNNER=NOT_CREATED_AS_OF_TRANSCRIPT_CUTOFF
REPORT=NOT_CREATED_AS_OF_TRANSCRIPT_CUTOFF
CANONICAL_MAIN_CHANGED=NO
PRODUCT_RUNTIME_CHANGED=NO
CROSS_SESSION_CAUSAL_REUSE=NOT_TESTED
```

## 5. Protocol changes proposed

- D021 §6C.5.2: execution-surface routing and permission provenance.
- New-Chat Boot and Handoff Kit §6.4: mandatory target block and surface-match check.
- TICD Toolchain Lifecycle policy §6: separate T3 scheduling from Windows-native scheduling, and separate outer operator writes from read-only Codex CLI child.

These changes are in the draft branch/PR #595 only. They are not canonical `main` policy until independently reviewed and merged.

## 6. Next verification

Await and reconcile the R3 operator receipt. Verify the actual scheduled task, user/logon mode, exact monthly trigger, runner path, CLI version/flags, immediate run result, Task Scheduler status, report and manifest hashes. Check for modifications outside the authorized runner, task and report directory. If any preflight condition fails, preserve `BLOCKED`/`PARTIAL`; do not silently weaken the sandbox or involve T3.

After a later non-identical handoff, test whether the surface-binding fields prevent the same mismatch. Until then: `METHOD_DOCUMENTED_IN_DRAFT=YES; METHOD_CANONICAL=NO; LATER_CAUSAL_REUSE=NOT_TESTED; AUTOMATIC_CROSS_CHAT_BOOT=NOT_PROVEN`.

## 7. Official CLI reference checked for the R3 design

- [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Codex CLI command-line reference](https://learn.chatgpt.com/docs/cli/reference)
- [Codex agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security)

The CLI reference documents `codex exec`, `--sandbox read-only`, `--ask-for-approval never`, `--ephemeral`, `--cd` and `-` for stdin prompt input. These flags constrain the child CLI invocation; they do not sandbox the external operator or the Windows task-registration process.