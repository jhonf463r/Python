# CHAT-ARCH-2026-10-13-258 — Owner keeps Codex launch blocked; static candidate-boundary design continues

- **Episode ID:** CHAT-ARCH-2026-10-13-258
- **Timestamp (America/Bogota):** 2026-10-13T16:32:00-05:00 (decision context; documentation writeback follows this review)
- **Canonical remote baseline before this writeback:** main @ a26346b4f7b9d2f6abbbddf7de951143303d8ce0
- **Parent tree:** 16d21432a75eac2c57492bb79a3925264b342598
- **Owner decision:** C — keep Codex launch blocked while static design and verification continue.
- **Classification:** OWNER_SELECTED_KEEP_BLOCKED_CONTINUE_STATIC_DESIGN
- **Operational result:** KEEP_BLOCKED
- **First open edge:** CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED

## 1. Owner decision and scope

The Owner answered “sí, procede” to the explicit choice: keep Codex launch blocked while preparation and verification continue, with no execution or implementation authorized. This resolves entry 249's owner-choice gate for the current phase as **C: remain blocked unless a route is proved compatible with all constraints**.

This is not a selection of home/auth option A or B. It is not permission to inspect credential contents, perform local preflight, launch a CLI or App Server, initiate a model turn, implement an adapter, run tests/builds, spend, or promote code. It does not select architecture-alternative C (an external executor); that is a separate design candidate. The dirty local worktree remains outside this remote review and must not be reset, cleaned, or treated as equal to main.

No source code or runtime behavior was changed. This episode and its projections are documentary continuity only.

## 2. Current-main static source findings

Source review was performed against the published main snapshot identified above, not against the Owner's uncommitted Windows checkout. Findings are bounded to those exact published sources.

### 2.1 Tool selection is not authorization

The published ToolRegistry picker selects a ToolCard by an existing task.tool_id where possible, then preferred assistant kind, lexical overlap against the task text/card description/capabilities, and finally a first-card fallback. This is a routing/availability mechanism. It does not prove that the selected tool is authorized for a candidate root, file scope, command allowlist, network policy, cost ceiling, or publication rule.

Source: [tool_registry.py](../../src/iabv_v15/services/tools/tool_registry.py).

### 2.2 Existing task/result contracts are generic, not a verified coding receipt

The published ToolTask includes task identity, tool ID, objective, actions, generic execution scope, approval and metadata; it has no first-class candidate root, immutable baseline/tree identity, prompt digest, allowed-command manifest, or one-use execution grant. Metadata can carry information, but its presence does not itself enforce it.

ToolResult includes task/result identity, status, output, extracted data, a generic list of artifact strings and metadata. It does not itself define a typed, independently verifiable candidate receipt binding baseline, candidate tree, diff digest, allowed scope and test evidence. CodexTaskSpec represents a planned coding task and contains file scope, constraints, acceptance criteria and test plan; its existence does not execute code or materialize a Git candidate.

Sources: [models.py](../../src/iabv_v15/domain/models.py), [tool_validator.py](../../src/iabv_v15/services/tools/tool_validator.py).

### 2.3 The existing sandbox services are not Git code isolation

The published SandboxExperimentService validates route/configuration recommendations. It derives a candidate route/configuration from ranked alternatives, computes heuristic evidence strength from recommendation confidence, blockers and alternative presence, and records ExperimentLab outcomes. When a baseline is blocked and an alternative exists, it can set promote_to_primary and record promotion. Its source path does not create an isolated Git worktree, apply a patch, observe a changed-file set, compute a candidate diff digest or validate code.

ToolSandbox calls the adapter with sandbox=True and wraps the returned payload. That flag and result label do not establish OS-enforced filesystem, credential, process or network containment.

Sources: [sandbox_experiment_service.py](../../src/iabv_v15/services/self_teach/sandbox_experiment_service.py), [tool_sandbox.py](../../src/iabv_v15/services/tools/tool_sandbox.py).

### 2.4 Autonomous validation is real as a code path, but is not the missing Codex development bridge

The published AutonomousValidationCycleService defaults auto_start to enabled outside its test mode unless explicitly configured otherwise. Its loop contains proactive proposal execution when the sync pulse is action_ready and confidence crosses a threshold, and a conditional Git auto-sync path when a wired sync service reports safe new commits. This is source-level capability only: the current process state and effective runtime wiring were not inspected here.

These behaviors do not demonstrate an authorized Codex code-edit task, isolated candidate, independent diff verification, or owner-approved code promotion. Any future Codex coding route must be an explicit separate operation with its own pre-dispatch authorization and fail-closed gates; it must not be silently added to the periodic autonomous proposal path.

Source: [autonomous_validation_cycle.py](../../src/iabv_v15/services/self_teach/autonomous_validation_cycle.py).

### 2.5 “Promotion” currently describes route/evidence publication, not code incorporation

The published PromotionPrPublisher documentation describes generating markdown/JSON evidence, preparing a Git branch/commit, and publishing a documentation PR about a chosen route/tool. It explicitly does not change executable logic. This is useful audit infrastructure, but its name must not be taken as a production-code promotion contract.

Sources: [promotion_pr_publisher.py](../../src/iabv_v15/services/self_teach/promotion_pr_publisher.py), historical contract [entry 055](./CHAT-ARCH-2026-10-05-055-self-code-candidate-diff-reconciliation.md).

## 3. Historical reconciliation — do not repeat the same archaeology

Entry 055 already established the distinction:
- ToolEvolutionProposal is not a code patch.
- CodexTaskSpec is not code execution.
- ToolSandbox is not Git isolation.
- A promotion decision is not code incorporation.

It also named the missing edge: a verified improvement proposal must become a materialized isolated code candidate with baseline, diff, scope and provenance. Entry 056 corrected historical baseline authority without changing that frontier. Entry 170 reported that the then-audited substrate was insufficient for the broader containment/effect-observation contract and called for a distinct containment/evidence trust boundary. Those are historical records, not fresh observations of the current Windows environment, but the current-main source review is consistent with their key separation.

Sources: [entry 055](./CHAT-ARCH-2026-10-05-055-self-code-candidate-diff-reconciliation.md), [entry 056](./CHAT-ARCH-2026-10-05-056-self-code-baseline-authority-reconciliation.md), [entry 170](./CHAT-ARCH-2026-10-08-170-rq21-52-codex-substrate-feasibility.md).

## 4. Architecture adjudication

Keep owner operational choice C. Treat B (Codex exec as a possible non-interactive invocation protocol) as a **conditional transport candidate only**, not the selected or approved architecture.

A future route requires both:
1. A trusted control/authorization path that pins the executable/version, exact task/prompt digest, baseline and one-use grant; and
2. A separate enforcement/evidence boundary that constrains the process and descendants and produces a candidate receipt independently of agent narration.

The architecture must explicitly solve the control-plane/authentication versus untrusted tool-execution boundary. If the same process/context can access its auth material and execute agent-directed shell/tools, simply putting its working directory in a candidate worktree is insufficient. Conversely, isolating the entire authenticated Codex process without a supported way to retain authorized remote communication may break the access path. Do not resolve this by copying secrets, creating a new login/home, allowing broad host reads, or assuming that an API/token broker exists. The exact approved design remains UNPROVEN.

App Server remains potentially useful for controlled text transport only where effect-capable tools are demonstrably disabled before any effect. The currently reported adapter path is not accepted as a coding bridge. An external isolated executor remains a design alternative if a safe and authorized control-plane/tool-executor separation can be specified.

## 5. Minimum candidate receipt contract

Before considering any implementation, freeze a contract that can represent and verify at least:

- One-use authorization ID, task ID, operation ID, exact prompt digest, allowed paths and command policy.
- Immutable baseline commit and tree identity.
- Candidate ID/root, candidate tree identity and changed-file manifest.
- Independently computed diff bytes/digest and an explicit in-scope/out-of-scope result.
- Effective executor identity/version and a non-secret policy/configuration fingerprint.
- Codex invocation/thread/turn identifiers when available, dispatch-once marker, terminal status and failure/timeout/cancel/late-event handling.
- Validation commands and their bounded output/status, with evidence digests.
- A receipt generated outside the untrusted agent's own narrative; mismatched identity, missing evidence, unexpected files, unknown terminal state, uncertain timeout or duplicate dispatch must fail closed.
- Separate owner decision for promote/reject/revert. No automatic commit, push, PR publication of code, main mutation, or reuse claim.

Do not assume all these fields belong directly in ToolResult; a focused typed receipt may be needed, with ToolResult acting as the existing task/result envelope.

## 6. Existing IABV organs: reuse without semantic overreach

| Existing organ | Reusable role supported by source | Role not established |
|---|---|---|
| ToolTeachService | Existing task/adaptor execution and result persistence path | Candidate-specific authorization and secure code receipt |
| ToolRegistry | ToolCard/adaptor lookup and availability | Security-policy enforcement or capability authorization |
| ToolTask / ToolResult | Task identity and generic result/artifact envelope | Baseline-bound candidate provenance and independently verified diff |
| ToolValidator / ToolSandbox | Generic result-state validation and adapter sandbox call | OS containment or code correctness verification |
| SandboxExperimentService / ExperimentLab | Route/configuration comparison and experience recording | Git worktree isolation, code patching or code-candidate validation |
| AutonomousValidationCycleService | Existing proposal evaluation/scheduling and possible autonomous operations | Authorization for a separate Codex code-writing action |
| PromotionPrPublisher | Documentation/evidence PR trail | Production-code promotion |
| Existing independent validation consumer | Candidate reuse target only if its precise contract is identified | Consumption of a verified Codex code receipt is not proven |

Reuse existing organs for orchestration, audit and memory where appropriate. Do not create another brain/router/memory. A separate narrow containment/evidence boundary may nevertheless be required because the current organ called “sandbox” does not meet the code-candidate contract.

## 7. Evidence classification

### PROVEN_BY_SOURCE (published main at the inspected baseline)
- ToolRegistry selects tool cards through tool ID/preference/lexical/fallback paths; this is routing, not authorization.
- ToolTask, ToolResult and CodexTaskSpec are generic/planning contracts and do not encode the complete candidate-bound receipt described above.
- SandboxExperimentService compares route/configuration recommendations and records heuristic outcomes; its inspected path does not materialize a Git code candidate.
- ToolSandbox wraps adapter output after calling the adapter with sandbox=True; this is not proof of OS containment.
- AutonomousValidationCycleService contains auto-start, proposal execution and conditional auto-sync code paths.
- PromotionPrPublisher describes documentation/evidence publication rather than executable-code promotion.
- Historical entries 055, 056 and 170 distinguish the materialized candidate/diff and containment evidence from route/configuration validation.

### OWNER_REPORTED
- The local Windows checkout was previously reported as branch codex/m0a-safe-ui-boot at HEAD 5b1d89022ee4cdc63c1f88e050f086b40a42875c, with dirty and untracked files.
- The local CLI was previously reported as 0.120.0.
- Prior reports describe a local CodexAppServerToolAdapter and synthetic identity-repair tests.

These are not remeasured in this episode.

### INFERRED
- A minimal future route should reuse ToolTeachService/ToolRegistry and ToolResult as orchestration/envelope where feasible, but isolate candidate materialization and trusted receipt generation behind a distinct enforcement boundary.
- B remains a useful interface candidate only if an independently enforced Windows/OS boundary and an authorized, non-exposing auth/usage route can be shown.
- The current route-promotion experiment should not be reused as code-promotion authority without a separate typed code-candidate validation contract.

### UNPROVEN
- Current local checkout contents, branch/HEAD and actual adapter wiring.
- Effective child executable path/version, home/auth mode, account/model eligibility, included quota and no-additional-spend stop.
- Effective Windows filesystem/credential/process/network boundary, including behavior when Codex's own sandbox is bypassed.
- Ability to retain authorized remote communication without making secrets accessible to agent-directed child commands.
- Actual candidate materialization, diff receipt, independent validation, result-consumer integration and causal reuse.
- Whether the running local IABV process has its autonomous loop enabled or any auto-sync/proposal actions currently active.

## 8. Next discriminating step and stop rule

Next step is not another public model-catalog search and not an implementation task. It is a static review of the **actual permitted local checkout** only when the source reader can access the requested files without launching code, using Git, running tests, starting Codex/App Server/IABV, or inspecting secrets. Compare its current adapter/dispatch/authorization implementation against this remote-main source and return exact file/line evidence or keep each claim UNPROVEN. If the local source remains inaccessible, the Owner may provide the relevant text/diff through the approved workspace; do not mutate or clean the dirty worktree to make it readable.

After the local source parity is understood, prepare a design-only enforcement decision covering how control-plane authentication is separated from constrained tool execution and how the independent receipt is generated. A non-mutating local preflight, implementation, tests, and runtime operation each require a separate authorization with explicit scope; C remains operative until the requirements are objectively demonstrated.

Hard stops: any need to inspect credential contents, copy auth material, create a new login/home, install/update, use an API key/paid credits, exceed the usage ceiling, grant broad host reads/network, trust only Codex's inner sandbox, or promote without independent receipt. Keep KEEP_BLOCKED.

No application/CLI/App Server process, authenticated request, model turn, test/build, credential inspection, local worktree mutation, install/update, spend, commit/push of product code, or promotion was performed. This record and its writeback are documentation, not runtime learning or proof of an operational IABV-to-Codex-to-IABV loop.
