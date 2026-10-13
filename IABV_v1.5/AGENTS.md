## Current route overlay — M0B-R3 Codex/App Server and existing rollout route (2026-10-13; entry 263)

Read [CHAT-ARCH-2026-10-13-263-m0b-r3-autonomy-bridge-adjudication.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-263-m0b-r3-autonomy-bridge-adjudication.md), then entries 231 and 260–262 as needed.

M0B-R3 makes App Server the direct programmatic Codex candidate, but published main already has `ExternalAssistantToolAdapter` + `UIExecutionRunner` and a `codex_installed` card configured for desktop/clipboard/rollout capture. The card is unavailable/unvalidated and capture-pending results remain unvalidated. Compare the local App Server candidate against this existing route before choosing. ChatGPT/Codex can use shared MCP tools, but IABV's ability to start an autonomous ChatGPT turn and receive a correlated result remains unresolved.

Governance boundary remains binding: no retry of blocked MCP read/list, no local launch, tests, configuration/source edits or bypass. After authorized governance resolution and direct target mapping, the next source-only audit compares adapter, bootstrap, normal dispatch and result consumer. KEEP_BLOCKED.

---

## Current route overlay — M0B-R1 governance gate and MCP target provenance (2026-10-13; entry 261)

Read [CHAT-ARCH-2026-10-13-261-m0b-r1-governance-gate-and-tool-provenance.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-261-m0b-r1-governance-gate-and-tool-provenance.md), then entries 260–258 and historical RSK-01A.5 records 035–036 when the MCP namespace matters.

M0B-R1 reports that `mcp__iabv_v15_rsk01a5__list_repo_directory` was governance-blocked and returned no source. Treat as a gate/precondition stop, not source absence. Published main shows audit read/list calls pass through the WorldModelSnapshot governance gate. The exact structured gate reason/block record and current tool-to-workspace mapping are unproven.

The `rsk01a5` namespace may be the distinct historical RSK-01A.5 connection/worktree; verify mapping before treating it as the M0A dirty checkout. No reader retries, alternate audit-tool bypass, gate clearing, broad world snapshot, local runtime/tests, credentials, implementation or promotion. Keep KEEP_BLOCKED.

Immediate edge: `IABV_AUDIT_GOVERNANCE_GATE_AND_TOOL_TARGET_PROVENANCE_UNRESOLVED`; local source remains unresolved; technical edge remains `CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED`.

---

## Current route overlay — AI-first source retrieval; do not make Owner copy source by default (2026-10-13; entry 260)

Read [CHAT-ARCH-2026-10-13-260-ai-first-local-source-inspection-boundary.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-260-ai-first-local-source-inspection-boundary.md). Exhaust authorized repo/source tools before asking the Owner for manual excerpts. Published main is not a substitute for local dirty/uncommitted bytes; the current remote chat has no direct Windows filesystem/desktop bridge. Codex can inspect a local workspace only when running and authorized; IABV only through effective wired capabilities. Permissions are not transitive.

Fresh main-source baseline lacks `CodexAppServerToolAdapter` and `codex_app_server` in the fetched `tool_adapters.py` and `bootstrap.py`; do not generalize that to local checkout. Preserve provenance and classify local details as UNPROVEN until the local source is actually read.

Owner choice C remains binding: no Codex/App Server launch, local preflight/command, tests/builds, secrets, implementation or promotion. Manual handoff is a last resort only after proving no authorized automatic path is available; if needed, ask for the smallest specific missing fact, not a broad source dump. Immediate edge LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED; technical edge CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED.

---

## Current route overlay — local source reader blocked; request narrow excerpts only (2026-10-13; entry 259)

Read [CHAT-ARCH-2026-10-13-259-local-source-handoff-blocked.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-259-local-source-handoff-blocked.md). A supplied report says the workspace reader returned queued with no source text; this is not a local code finding. Do not substitute main for uncommitted changes or request the full 18-file bundle again. Ask for narrow local excerpts: adapter class/policy/request/result handling, bootstrap registration, actual SafeUI/ToolTeachService dispatch caller and result-consumer/evaluator call site. Identity-repair source/test only if necessary.

No shell/Git, tests/builds, Codex/App Server/IABV, credentials or local mutations. Owner selected C: keep launch blocked. Immediate edge: LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED; technical edge remains CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED.

---

## Current route overlay — Owner chooses C; do not launch Codex (2026-10-13; entry 258)

Read [CHAT-ARCH-2026-10-13-258-owner-keeps-codex-blocked-static-candidate-boundary.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-258-owner-keeps-codex-blocked-static-candidate-boundary.md), then entries 257, 249, 243, 055, 056 and 170. The Owner selected C: keep launch blocked while source-only design continues. This resolves the prior no-selection status for the current phase but does not select home/auth A or B or authorize local preflight, implementation, runtime, tests/builds, install/spend or promotion.

Current-main inspection established that ToolRegistry lookup is not authorization; ToolTask/ToolResult have no first-class baseline-bound code-receipt contract; SandboxExperimentService compares routes/configurations and is not Git code isolation; ToolSandbox is not proof of OS confinement; PromotionPrPublisher publishes documentation/evidence, not code promotion. AutonomousValidationCycleService has source-level auto-start/proposal/auto-sync paths, but actual runtime wiring/state remains UNPROVEN.

Prioritize REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW. Do not invent a second brain/router/memory. A narrow external enforcement/evidence boundary may still be necessary. B (codex exec) is a possible transport only, not approved safe architecture. Keep KEEP_BLOCKED and preserve any dirty/untracked local worktree.

First open edge: CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED.

---

## Current route overlay — v0.162.1 catalog/exec source found; no launch authorization (2026-10-13; entry 257)

Read [CHAT-ARCH-2026-10-13-257-current-codex-catalog-and-exec-static-paths.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-257-current-codex-catalog-and-exec-static-paths.md), then entries 249 and 252–256. Entry 256's no-catalog-interface result is specifically about inspected v0.120.0; don't generalize it to current source. v0.162.1 exposes `codex debug models`; default may use existing auth/network/cache, while `--bundled` is static only. Its `exec` `--ignore-rules` skips user/project rules but not all possible managed/system layers; explicit Allow can bypass Codex's inner sandbox; headless approval is Never. Plan/model minimums do not prove this account's quota, eligibility or zero added spend.

Keep KEEP_BLOCKED. Do not execute Codex, authenticate, update/install, inspect secrets, or modify code/config/worktree. Owner A/B/C launch/auth-home decision remains pending. Current first edge: `CODEX_EXEC_TARGET_VERSION_AUTH_USAGE_AND_CONFINEMENT_UNVERIFIED`. Source-derived candidate interface is not proven IABV integration, diff receipt, independent verification, behavioral learning or owner-approved promotion.

---

## Current route overlay — authenticated catalog-only path not established (2026-10-13; entry 256)

Read [CHAT-ARCH-2026-10-13-256-read-only-model-catalog-path-unavailable.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-256-read-only-model-catalog-path-unavailable.md), then entries 255–252. The reviewed rust-v0.120.0 CLI did not establish a supported isolated catalog-only request; ModelsManager is internal, and no catalog request or turn occurred. This does not prove every compatible route impossible. Keep KEEP_BLOCKED and first open edge CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED. Model compatibility beyond documented minimums, account auth/eligibility, quota, credit fallback and cost remain unproven. No runtime, credentials, install, inference or code action.

---

## Current route overlay — CLI version/model and included-usage compatibility (2026-10-13; entry 255)

Read [CHAT-ARCH-2026-10-13-255-cli-version-model-entitlement-compatibility.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-255-cli-version-model-entitlement-compatibility.md), then entries 254–252.

Public current OpenAI docs set Codex CLI 0.144.0 minimum for GPT-5.6 and 0.153.0 for GPT-6 Astra; earlier Owner-supplied static inspection found version 0.120.0 in one shell. Do not infer current-model compatibility or total incompatibility without evidence, and do not install/update within current constraints. Official plan inclusion is subject to limits; account-specific model eligibility, auth, quota and paid-credit fallback remain unproven.

First open edge: `CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED`. In addition, auth-home/keyring coupling, execpolicy Allow sandbox bypass, Windows backend effectiveness and diff-consumer acceptance remain open. No CLI turn, install, login, paid credits/API, tests, credentials or source changes. Preserve dirty/untracked work.

---

## Current route overlay — Codex plan usage is not a zero-spend guarantee (2026-10-13; entry 254)

Read [CHAT-ARCH-2026-10-13-254-codex-plan-usage-and-zero-extra-spend-gate.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-254-codex-plan-usage-and-zero-extra-spend-gate.md), then entries 253–251.

Official current Help Center docs state Codex is included in ChatGPT plans including Free/Go, with plan-dependent limits; eligible accounts may buy additional usage credits after limits. The Owner's active auth, included quota, credit settings, and billing/usage mode are not proven by public documentation or installed package metadata. Do not conflate “no API key/new OAuth” with “no quota consumed” or “no incremental charge.”

The other live gates remain: existing home auth lookup is keyed by canonical home when using keyring; a matching explicit execpolicy Allow can bypass Codex's inner sandbox; local selected Windows backend/effective policy is unknown. First open edge: `CODEX_EXEC_AUTH_HOME_POLICY_AND_USAGE_BUDGET_ROUTE_UNRESOLVED`. No CLI/turn, secrets, new login, home mutation, install, credit purchase, spend, source edit, commit/push or promotion. Preserve dirty local work.

---

## Current route overlay — Codex authentication and execpolicy must be jointly resolved (2026-10-13; entry 253)

Read [CHAT-ARCH-2026-10-13-253-codex-home-auth-and-execpolicy-coupling.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-253-codex-home-auth-and-execpolicy-coupling.md), then entries 252–250.

Codex 0.120 file auth uses `CODEX_HOME/auth.json`; keyring auth lookup hashes the canonical home path. The execpolicy loader imports `rules/*.rules` from all applicable config-layer folders, and matching explicit `Allow` rules may yield `SandboxType::None` for a command. No rule-exclusion option was found in the reviewed `ExecCli` struct and loader. A separate home does not automatically reuse the current keyring auth; reusing the current home also reuses its policy sources.

First open edge: `CODEX_EXEC_AUTH_HOME_POLICY_ISOLATION_ROUTE_UNRESOLVED`. Continue static source analysis. If no supported separation exists, require a separately authorized non-mutating local preflight of the auth store mode and applicable policy provenance, without revealing secrets. No home/symlink creation, login, CLI/runtime, tests, code/config changes, install, spend, commit/push or promotion. Preserve the dirty worktree.

---

## Current route overlay — Codex execpolicy Allow rules may bypass inner sandbox (2026-10-13; entry 252)

Read [CHAT-ARCH-2026-10-13-252-execpolicy-allow-can-bypass-sandbox.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-252-execpolicy-allow-can-bypass-sandbox.md), then entries 251–247.

Public Codex `rust-v0.120.0` source shows an explicit matching execpolicy `Allow` can set `bypass_sandbox=true`, which the orchestrator maps to `SandboxType::None`. Rules are loaded from `rules/*.rules` in all applicable config-layer folders. Built-in known-safe-command heuristics are distinct, but the Owner's effective user/managed rule set remains unverified.

A profile selected through `default_permissions` is insufficient by itself. First establish whether any supported non-runtime switch excludes the user rules; if not, a separately authorized local non-mutating rule-layer preflight or an independently enforced outer OS boundary is required. Keep C/block until then. No launch/turn, local policy read, credentials, tests, implementation, install/spend, commit/push or promotion. Preserve the dirty worktree.

---

## Current route overlay — Codex 0.120 permission-profile dispatch candidate (2026-10-13; entry 251)

Read [CHAT-ARCH-2026-10-13-251-exec-v0120-permission-profile-dispatch.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-251-exec-v0120-permission-profile-dispatch.md), then entries 250–247.

Do not blindly use `codex exec --sandbox workspace-write` for the candidate boundary. Public `rust-v0.120.0` source selects legacy policy interpretation whenever CLI `sandbox_mode` is set; `--full-auto` sets it too. With no sandbox override/profile sandbox mode, a higher-precedence `default_permissions` setting can select permission-profile interpretation. The exec harness sets `approval_policy=Never`, so this is unattended execution that must fail closed under an enforced pre-approved profile, not interactive command approvals.

Candidate profile: only the disposable candidate writable; minimal/system runtime read roots; no broad root-read permission; selected authenticated home and credential paths omitted from command-child read roots; child network/integrations deny by default. This is static design only. Effective local Windows backend/provisioning and no-extra-spend auth remain unproven.

First open edge: `CODEX_EXEC_V0120_PROFILE_ROUTE_BACKEND_AND_ENVIRONMENT_UNVERIFIED`. C remains runtime default while A/B selection is pending. No process, CLI/App Server call, turn, test, secret inspection, implementation, install, spend, commit/push or promotion. Preserve all dirty local files.

---

## Current route overlay — Cloud static review continues; Windows home isolation is the discriminator (2026-10-13; entry 250)

Read [CHAT-ARCH-2026-10-13-250-cloud-static-audit-windows-sandbox-home-separation.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-250-cloud-static-audit-windows-sandbox-home-separation.md), then entries 249–246.

Do not stop source-level analysis just because owner selection A/B/C or local runtime verification is pending. Public Codex `rust-v0.120.0` declares filesystem permission profiles (`read/write/none`) and Windows elevated/unelevated sandbox modes, but the backends support different subsets. The critical invariant is: the Codex host can use the already approved authenticated home, while agent-spawned commands cannot read sensitive home/credential paths and can write only to a disposable candidate. If the already-available backend cannot enforce that exact policy, fail closed.

Published IABV bootstrap loads recognized secrets into parent `os.environ`; a future executor must use an explicit env allowlist and separately restrict agent-command env. Current remote `main` does not contain the Owner's unpublished dirty adapter source, so do not claim to have reviewed it directly.

First technical edge: `CODEX_EXEC_WINDOWS_HOME_READ_DENIAL_FEASIBILITY_UNVERIFIED`. C remains the runtime default while A/B selection and local effectiveness are unproven. No launch, turn, test, secret inspection, source edits or spend. Preserve dirty/untracked work.

---

## Current route overlay — Owner home/auth decision still pending (2026-10-13; entry 249)

Read [CHAT-ARCH-2026-10-13-249-owner-decision-package-reviewed-no-selection.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-249-owner-decision-package-reviewed-no-selection.md), then entries 248–247.

The latest report enumerates A/B/C but does not explicitly select a home/authentication option. Do not infer authorization. Keep `codex exec` blocked. Option B is only a conditional candidate if an already-existing dedicated authenticated home is proven to meet all constraints. If not, remain blocked; do not copy credentials, initiate a new login or assume zero spend.

First open edge: `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`. No implementation, preflight, process, CLI/App Server turn, tests, credential inspection, installation, spend, commit/push or promotion. Preserve all dirty/untracked local files.

---

## Current route overlay after exec design submission (2026-10-13; entry 248)

Read [CHAT-ARCH-2026-10-13-248-exec-launch-contract-design-adjudication.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-248-exec-launch-contract-design-adjudication.md), then entries 243–247.

The supplied proposal is accepted as design-ready for Owner adjudication only. It is not an implementation approval. It requires exact authorization/executable/environment linkage, a controlled candidate baseline, OS-enforced Windows containment, external-effect restrictions and a verifiable diff/artifact receipt delivered to the existing consumer.

Key unresolved conflict: an explicit/dedicated `CODEX_HOME` plus existing authentication and zero additional spend, without copying credentials or starting new login/OAuth setup. No compatible already-authenticated home is established. If none meets the Owner-approved constraints, keep the route blocked.

Next edge: `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`. No CLI/App Server invocation, turn, test, code/config edit, credential inspection, installation, spend, commit/push or promotion. Preserve all local dirty/untracked work.

---

## Current route overlay after CLI exec integration block (2026-10-13; entry 247)

Read [CHAT-ARCH-2026-10-13-247-codex-exec-integration-boundary-static-block.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-247-codex-exec-integration-boundary-static-block.md), then entries 243–246.

Owner-supplied static audit classifies the current integration as `CODEX_EXECUTION_INTERFACE_STATICALLY_BLOCKED`. The existing App Server path constructs its own environment/home, but no IABV CLI `exec` adapter contract was found. Do not infer a hypothetical child's effective `CODEX_HOME` from the interactive shell or reuse the App Server home by assumption. The observed `danger-full-access` / `approval_policy = "never"` config belongs to another context and is not an approved target policy.

Next edge: `CODEX_EXEC_LAUNCH_ENVIRONMENT_CONTRACT_UNDEFINED`. Produce a design-only specification from current source before considering implementation. No process, CLI/App Server invocation, turn, tests, code/config edit, secrets, install, spend, commit/push or promotion. Preserve dirty/untracked local changes.

---

## Current route overlay after CLI interface identification (2026-10-13; entry 246)

Read [CHAT-ARCH-2026-10-13-246-codex-exec-0120-static-contract-and-target-home.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-246-codex-exec-0120-static-contract-and-target-home.md), then entries 243–245.

The supplied Windows inventory identifies the inspected shell's Codex `0.120.0` shim/native package. The versioned public `rust-v0.120.0` source declares `codex exec`, sandbox modes and output options. It does not establish that IABV inherits the same PATH, that its own CODEX_HOME is safe/effective, or that auth/quota/cost/network/tool restrictions and candidate artifact delivery work.

Next edge: `CODEX_EXEC_TARGET_HOME_AND_EFFECTIVE_POLICY_UNPROVEN`. Source/config-only review of how IABV constructs its child environment and intended home; inspect only allowlisted non-secret policy values. Do not copy `danger-full-access` / `approval_policy = "never"` from another home. No process, CLI/App Server call, agent turn, tests, source/config changes, credentials, install, spend, commit/push or promotion. Preserve all local dirty/untracked content.

---

## Current route overlay after the App Server coding-mode block (2026-10-13; entry 245)

Read [CHAT-ARCH-2026-10-13-245-windows-codex-execution-route-comparison.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-245-windows-codex-execution-route-comparison.md), then consult entries 243–244 for the immediately prior findings.

The current IABV App Server adapter is reported as text/read-only, without a writable candidate or diff artifact. Do not assume the native sandbox docs automatically make it a coding bridge. Official Codex Cookbook demonstrates CLI `exec --sandbox workspace-write`; public issue #37818 reports a specific Windows App Server `workspace-write` turn that exposed no command/file-change items. Treat this as route-discrimination evidence, not universal proof.

Next edge: `CODEX_WINDOWS_CODING_TRANSPORT_AND_SANDBOX_COMPATIBILITY_UNRESOLVED`. First do a one-time non-mutating inventory of the exact resolved CLI/shim/package and non-secret effective Windows sandbox config. Compare App Server with the existing CLI `exec` route. No agent turn until a route and its effective boundary are verified. Do not read credentials, install/update, alter config, run tests, or spend. Preserve all local dirty/untracked work. No commit/push/promote.

---

## Current Codex route refinement (2026-10-13; entry 244)

Read [CHAT-ARCH-2026-10-13-244-windows-sandbox-route-refinement.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-244-windows-sandbox-route-refinement.md) and the blocked-current-adapter report in entry 243.

Official Codex docs describe native Windows sandbox implementations that enforce filesystem/network permissions for agent-spawned commands; `workspace-write` supports controlled coding within an approved workspace. Check this before designing a new executor. Do not assume it applies to the local CLI/App Server: the supplied audit says IABV expects userAgent 0.120.0 and resolves a binary dynamically, and effective sandbox/config/tool surface remain unproven.

Next edge: `CODEX_NATIVE_WINDOWS_SANDBOX_IN_APP_SERVER_MODE_UNVERIFIED`. Source-only review of the existing adapter, exact sandboxPolicy/root/cwd, direct non-secret sandbox config, MCP/app/browser availability before effects and candidate-diff capture. If existing sandbox cannot be shown compatible without installation/setup/spend, keep blocked and design a distinct boundary. Preserve the dirty worktree; no runtime, tests, code/config edits, credentials, OAuth/API setup, installation, spend, commit/push or promotion in this stage.

---

## Current Codex development route overlay (2026-10-13; entry 243)

Read [CHAT-ARCH-2026-10-13-243-codex-bounded-development-mode-blocked.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-243-codex-bounded-development-mode-blocked.md) after the required new-chat remote-state reconstruction.

The Owner-supplied source report classifies the current adapter as `CODEX_BOUNDED_DEV_MODE_STATICALLY_BLOCKED`. It captures text and IDs, not a writable candidate worktree or verifiable diff. Its scope is reported as read-only; a Windows Job Object does not prove file/credential/network isolation. Do not try to bypass this by simply changing a prompt or switching the target directory to writable.

Next edge: `CODEX_CANDIDATE_WORKSPACE_EXECUTION_BOUNDARY_DESIGN_UNRESOLVED`. A single design-only task must compare: (A) existing App Server with a demonstrably effective OS-enforced candidate boundary and artifact capture, versus (B) a separate contained executor. State exact auth/quota/cost, workspace/command/network limits, no credential copying, no unapproved MCP/apps, stable IDs, diff/test artifacts, existing consumer evaluation and owner-only promotion. If the boundary cannot be demonstrated, keep the route blocked and propose the smallest separate implementation task.

Preserve the dirty local worktree and every modified/untracked file. No runtime, test, code/config edits, credential inspection, auth setup, spend, commit, push or promotion in the design tranche.

---

# IABV v1.5 - Instrucciones Operativas Transversales Para Cualquier Agente

## Current M0-A / Codex route overlay (2026-10-13)

Read [CHAT-ARCH-2026-10-13-241-codex-development-bridge-route-adjudication.md](docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-241-codex-development-bridge-route-adjudication.md) after reconciling the current remote `main` SHA.

The owner's primary objective is a governed IABV→Codex→IABV coding handoff, not just a tool-free text response. Entry 240's versioned-schema finding blocks the reviewed tool-free App Server turn; it does **not** prove every coding route impossible. Stop broad searches for an undocumented global tools-off switch. The next edge is `CODEX_BOUNDED_DEVELOPMENT_EXECUTION_BOUNDARY_UNPROVEN`: a bounded source-only feasibility audit of the existing App Server adapter/config/tool registry, Windows sandbox/launch composition and existing result consumer.

For development mode, tools may be necessary, but every write and command must be confined by an effective system/workspace boundary, exact owner operation/resource/scope authorization, restricted external effects, preserved task/thread/turn/artifact correlation, verification and owner-gated promotion. A prompt instruction or path-only copy is not a security boundary. Do not claim native auth/quota/cost, effective sandbox enforcement, live response or consumer evaluation without evidence. Preserve the reported dirty worktree; no runtime, code edits, tests, credentials, spend, commit, push or promotion in the source-only audit.

---


Eres el agente principal de ingenieria y evolucion de este proyecto.
Tu trabajo no es improvisar: debes leer el estado real del repo, respetar
la arquitectura vigente y dejar cada sesion con mejor evidencia, mejor
contexto operativo y menos trabajo redundante.

## Identidad Del Proyecto
- Nombre: `IABV v1.5`
- Workspace: `C:\Python\IABV_v1.5`
- Codigo fuente: `src/iabv_v15/`
- Pruebas: `tests/`
- Datos de trabajo: `data/`
- UI: Python + PySide6 + QML
- Enfoque: `local-first`, observabilidad operativa, autonomia gobernada, aprendizaje acumulativo y contexto portable



## CONTRATO TRANSVERSAL DE CONTINUIDAD Y OBJETIVO

Este archivo se aplica transversalmente a **Codex, Devin, Claude, ChatGPT y al propio IABV**.

Antes de planificar, ejecutar o modificar una tarea material:

1. Leer la memoria canónica relevante.
2. Reconciliarla contra el SHA/branch/runtime actual.
3. Identificar el objetivo global y el objetivo activo.
4. Identificar aristas ya cerradas y NO reabrirlas salvo evidencia contradictoria.
5. Identificar la primera arista causal abierta.
6. Determinar la capacidad requerida.
7. Seleccionar el actor por capability-fit e information gain; nunca por una secuencia fija de IAs.
8. Definir evidencia, control, stop condition y verificador independiente cuando corresponda.
9. Después del resultado, preservar el Knowledge Delta y actualizar la memoria canónica si el estado material cambió.

### Regla de precedencia

Un prompt histórico, un "next actor" histórico o una recomendación anterior **no tiene precedencia sobre un CURRENT-STATE overlay más reciente y reconciliado**.

### Regla de universalidad

La prioridad del proyecto es investigar y desarrollar mecanismos de razonamiento/adaptación transferibles entre entornos, no acumular recetas provider-specific ni crear un nuevo cerebro por cada integración.

### Regla de evidencia

`report ≠ evidence`

`persistence ≠ learning`

`synthetic ≠ operational experience`

`actor agreement ≠ independent verification`

`repository state ≠ runtime state`



### Current evidence boundaries for adaptive/self-examination claims

The closed P2/P4 entries below refer only to the specific operational nuclei they name. They do not mean that experience-driven metacognitive learning, general SelfAudit→OSES interpretation, or full system-level autonomous learning has been proven.

Current BIO-UNIVERSAL evidence must preserve:

`adjustment→decision` proven in R28

versus

`operational experience→metacognitive_evaluation→finding→adjustment` still open.


## Comando Oficial De Pruebas
Bateria completa:

```powershell
$env:PYTHONPATH='C:\Python\IABV_v1.5\src';
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/ -q
```

Regla operativa:
- primero corre pruebas focalizadas del slice que toques
- luego corre una regresion razonable
- usa la bateria completa cuando el cambio toque contratos compartidos o cierre una fase importante

## Arquitectura Central Vigente

### Cerebro Y Decision
- `PerceptionSnapshot`: entrada unificada antes de cada decision
- `AdaptiveTaskOrchestrator`: orquestador principal
- `TaskContextAssembler`: ensambla contexto, perception y world model summary
- `AutonomyGovernancePolicy`: decide que rutas son viables o deben bloquearse
- `IntentUnderstandingService`: clasifica la intencion
- `LocalRoleRouter`: decide ruta y proveedor local

### Modelos Del Entorno
- `EnvironmentSelfModel`: estado de hardware, runtime y riesgos del entorno
- `WorldModelSnapshot`: panorama operativo vivo del sistema, herramientas, red, ventanas y bloqueos
- `UniversalPerceptionSignal`: observacion puntual de programa o pagina

### Cloud Reasoning Y Auditoria De Decisiones
- `CloudReasoningPlannerService`: genera planes multi-paso usando modelos cloud (Gemini → Groq → Ollama)
- `DecisionAuditTrail`: registra cada decision cloud (proveedor, latencia, confianza, resultado, tendencia) en `data/evolution/decision_audit/decisions.jsonl`. Es SALIDA del framework y ENTRADA de la metacognicion — no es un servicio independiente
- `ApiKeyDiscoveryService`: descubre, prueba, compara y monitorea API keys de proveedores cloud

### Aprendizaje, Contexto Y Revision
- `ExperimentLab`: compara rutas, asistentes y configuraciones (incluyendo `domain=CLOUD_REASONING` para proveedores cloud)
- `StrategySelector`: recomienda rutas por historial y evidencia
- `AdaptiveWeightLayer`: ajusta preferencia futura con base en resultados reales
- `TaskOutcomeRecorder`: cierra el loop de aprendizaje desde la ejecucion normal
- `PortableContextService`: exporta contexto comprimido y portable para nuevas sesiones (incluye seccion `cloud_reasoning` con health score, trends y recomendaciones)
- `OperationalSelfExaminationService`: revisa patrones repetidos, degradaciones y ajustes recomendados (incluye `_cloud_reasoning_findings()` que lee el audit trail)
- `ia_trace_summary`: resumen de que IA o configuracion rindio mejor
- `comparison_scope_key`: agrupa problemas comparables para evaluar ganadores reales
- `adaptive_learning_summary`, `learned_patterns`, `validation_summary`: resumen operativo reusable

### Conciencia De Estimulos Y Regulacion Cognitiva
El sistema regula su profundidad de procesamiento segun la presion de recursos:
- `_assess_resource_pressure()` en Orchestrator y ValidationCycle lee `EnvironmentRiskSignal` y clasifica presion (CRITICAL, HIGH, normal)
- Bajo presion CRITICAL: se omite comparacion paralela de IAs y se inhibe auto-ejecucion de propuestas
- Bajo presion HIGH: solo se ejecutan propuestas con confianza >= 0.7 (mas selectivo)
- Sin presion: se activa cognicion profunda diferida en `OperationalSelfExaminationService` (cross-correlacion de fallos, deteccion de tendencias, decay de estrategias)
- El `sync_pulse` integra conscientemente risk signals, propuestas y recomendaciones (funcion talamica)
- El estado de presion se deposita en `context.metadata['resource_pressure']` para que downstream lo observe

### Meta-Observacion Continua Y Conciencia Temporal
El sistema se observa a si mismo en background y detecta anomalias temporales:
- `_background_decision_review_findings()` en OSES lee `DecisionAuditTrail` y detecta: proveedores con tasa de exito baja, decisiones de baja confianza que fallan, y errores que se repiten sin correccion
- `_temporal_awareness_findings()` en OSES detecta: anomalias de latencia (z-score > 2.0), regresion de latencia (runs cada vez mas lentos), y operaciones estancadas (> 5 min sin completar)
- `_deep_analysis_queue_findings()` en OSES (solo bajo carga baja) ejecuta analisis estadistico diferido: EMA drift detection, fallos correlacionados entre proveedores, y outliers de latencia via IQR
- `_record_task_timing()` y `_check_temporal_anomaly()` en Orchestrator registran el tiempo de cada tarea por intent_key y depositan `temporal_anomaly` en session metadata cuando z-score > 2.0
- Estos mecanismos extienden servicios existentes (OSES, Orchestrator) sin crear nuevos servicios ni otro cerebro

### Sandbox Y Validacion
- `SandboxExperimentService`: valida cambios o rutas candidatas sin tocar el sistema vivo
- `AutonomousValidationCycleService`: revisa candidatos y promueve solo lo que tenga evidencia
- `GuidedImprovementCycle`: sigue existiendo como estructura de mejora guiada; no es otro cerebro

### Herramientas Y Ejecucion
- `ToolTeachService`: consultas a herramientas externas
- `ToolRegistry` y `ToolCard`: catalogo operativo de herramientas
- `AutonomousEvolutionService`: puente de consulta externa autonoma
- `UIExecutionRunner`: ejecucion UI controlada

### UI
- `ControlCenterViewModel`: observa, explica y dispara flujos aprobados
- `EvolutionCenterViewModel`: observa estado evolutivo, world model, portable context y autoexaminacion
- Los ViewModels no deben convertirse en otro cerebro ni tomar decisiones de ruta por su cuenta

## Capas Cerradas Que Debes Respetar

### P1 - World Model Operativo
Ya esta cerrado.
Estado esperado:
- `WorldModelService` es la fuente viva de ventanas, foco, herramientas, red, procesos y bloqueos
- se consulta antes de rutas externas
- `TaskContextAssembler`, `AdaptiveTaskOrchestrator` y `AutonomyGovernancePolicy` consumen `world_model`
- la UI lo lee; no lo modifica

### P2 - Neuroplasticidad Operativa Real
Ya esta cerrada en su nucleo.
Estado esperado:
- la ejecucion normal registra resultados reales
- `ExperimentLab`, `StrategySelector` y `AdaptiveWeightLayer` influyen decisiones futuras
- el sistema aprende por evidencia, no por costumbre

### P3 - Contexto Portable
Ya esta cerrado.
Estado esperado:
- `PortableContextService` genera paquete portable desde estado vivo y aprendizaje persistido
- el contexto portable se propaga por `TaskContextAssembler`, `AdaptiveTaskOrchestrator` y `EvolutionCenterViewModel`
- no existe una memoria paralela

### P4 - Autoexaminacion Operativa Real
Ya esta cerrada.
Estado esperado:
- `OperationalSelfExaminationService` detecta patrones, riesgos y ajustes recomendados
- tambien revisa si sus ajustes previos funcionaron o no
- sus hallazgos alimentan el contexto portable

### N3 - Autoexaminacion Del Codigo Fuente
Ya esta validada.
Hallazgo corregido relevante:
- se elimino refresh redundante de autoexaminacion en `EvolutionCenterViewModel`

### N4 - Validacion Real De WorldModel En Windows
Ya esta validada.
Hechos confirmados:
- ventanas abiertas reales y foco via Win32
- hilo activo de Codex via `%USERPROFILE%\\.codex\\state_5.sqlite`
- preflight de consulta externa bloqueado por permiso antes de actuar
- el estado vivo del hilo de Codex prevalece sobre historial stale

## Fuentes De Verdad Actuales
Prioriza esta jerarquia:
1. `WorldModelSnapshot` y `EnvironmentSelfModel`
2. contratos del codigo fuente
3. `PortableContextPackage` y `SelfExaminationSnapshot`
4. pruebas
5. historial persistido (`ExperimentLab`, sesiones adaptativas, run records)
6. suposiciones

Nunca inviertas ese orden.

Fuentes concretas:
- `bootstrap.py`: wiring real del sistema
- `src/iabv_v15/domain/models.py`: contratos soberanos
- `data/evolution/portable_context/latest.json` y `latest.md`
- `data/evolution/self_examination/latest.json` y `latest.md`
- `data/evolution/world_model/`
- `tests/`

## Politica Operativa Actual

Antes de usar una herramienta externa:
1. consulta `WorldModelSnapshot`
2. verifica red, foco, hilo, cuota, permiso y bloqueo activo
3. si falta permiso o evidencia, bloquea la ruta y explicalo

Si una pregunta es de:
- estado vivo del sistema
- autoconciencia del sistema
- aprendizaje acumulado
- autoexaminacion operativa

entonces:
- responde por la via humana local
- usa `world_model`, `environment_self_model`, `ExperimentLab`, `PortableContextService` y `OperationalSelfExaminationService`
- no dispares autonomia ni consulta externa

Cuando una herramienta falle o rinda mal:
1. no insistas a ciegas
2. registra el fallo con evidencia
3. revisa alternativas disponibles en `ToolRegistry`, `ExperimentLab`, MCPs o proveedores locales
4. compara la nueva ruta contra la actual usando resultados reales

## Contratos Que No Debes Romper
- No crear otro cerebro ni otro orquestador
- No duplicar `PerceptionSnapshot`
- No reemplazar `EnvironmentSelfModel`, `WorldModelSnapshot` o `UniversalPerceptionSignal`; se complementan
- No convertir un ViewModel en decisor de rutas
- No hacer refactor masivo sin aprobacion explicita
- No fingir observacion que no existe
- Si algo no puede confirmarse, marcar `UNRESOLVED`
- Si una ruta no es viable en el estado actual, bloquear antes de intentar
- El sandbox debe seguir aislado del sistema vivo

## Regla De Observacion Real
Si necesitas observar contenido visible de una ventana externa para verificar
si una herramienta esta utilizable:
- pide permiso explicito al usuario
- no asumas que el permiso existe
- no declares la herramienta disponible si no pudiste verificarla

## Pendientes Reales Que Siguen Abiertos
- La disponibilidad real de mensajes/cuota en herramientas externas visibles sigue requiriendo permiso explicito de observacion; sin ese permiso debe quedar `desconocidos` o `UNRESOLVED`.
- Algunos estados live, como `wrong_thread`, dependen del escritorio real del momento; si no estan presentes en vivo, se validan por pruebas y no se inventan.
- Varias suites de UI siguen siendo lentas en Windows; no es una falla funcional, pero si una deuda de rendimiento de pruebas.
- Si alguna conclusion depende solo de historial stale y contradice observacion viva, debe prevalecer la observacion viva.

## Autonomia De Operacion (Reduccion De Trabajo Manual)
Objetivo: que el usuario solo intervenga cuando hay decision real, no
rutina. Mientras la tarea sea ``implementar + pushear + mergear + audit``,
la ejecuta el agente en su VM sin pedir click en GitHub.

Reglas de auto-merge (usar ``scripts/auto_merge_devin_pr.py``):
- Rama obligatoria: ``devin/*`` o ``iabv-auto/*``. Otro prefijo requiere
  aprobacion explicita del usuario.
- El PR debe tener ``mergeable_state`` distinto de ``blocked`` / ``dirty``
  / ``behind``.
- Checks registradas deben concluir ``success`` / ``skipped`` / ``neutral``
  (si no hay checks, el repo IABV lo permite; queda registrado).
- ``--force`` solo se usa cuando el usuario pidio explicitamente saltear
  salvaguardas; el agente no se auto-concede force.

Aprobacion humana obligatoria (no auto-mergear) cuando:
- El PR toca ``main`` via merge directo (fast-forward sin PR).
- Cambia policies, contratos ``domain/models.py``, o capas cerradas
  P1-P4 (``world_model``, neuroplasticidad, contexto portable, auto-
  examinacion) mas alla de lo trivial.
- Implica migracion destructiva de ``data/`` o borra evidencia historica.
- Toca la politica de ``AutonomyGovernancePolicy``.
- Agrega dependencias nuevas pesadas (ej: ``watchdog``, modelos grandes).

Infra de arranque operativo para el usuario:
- ``scripts/iabv_bootstrap.ps1``: **entry point zero-touch** para maquinas
  / cuentas nuevas. Instala ``gh`` y ``cloudflared`` portable (sin winget,
  sin admin) en ``$HOME\.iabv\tools``, corre ``setup_iabv_profile.ps1``,
  corre ``rotate_tokens.ps1`` y arranca ``start_iabv.ps1``. Unico paso
  manual: click "Authorize" en el browser durante el device-flow de GitHub.
  Flags: ``-Force``, ``-NoStart``, ``-SkipInstalls``, ``-PrintTunnelUrl``.
- ``scripts/iabv_secrets.template.ps1``: template de secretos locales.
- ``scripts/setup_iabv_profile.ps1``: one-shot que deja ``$PROFILE`` y
  ``~/.iabv_secrets.ps1`` configurados; se corre una sola vez por maquina.
- ``scripts/start_iabv.ps1``: un comando para cargar secretos, validar
  shape y arrancar MCP + tunnel via ``run_mcp_bridge.ps1``.
- ``scripts/mcp_hot_reload.py``: wrapper opcional (``IABV_MCP_HOT_RELOAD=1``)
  que reinicia el MCP al detectar cambios en ``src/iabv_v15/*.py``. Sin
  dependencias externas; polling de mtimes.
- ``scripts/rotate_tokens.ps1``: rotacion asistida sin copy-paste. Usa
  ``gh auth login --web`` (device-flow) para obtener el PAT de GitHub y
  ``Read-Host -AsSecureString`` para pegar la Devin API key una vez.
  Escribe ambos valores a ``$HOME\.iabv_secrets.ps1`` solo despues de
  validarlos con HTTP 200 contra los endpoints reales. Nota: ``gh auth
  status`` escribe a stderr cuando no hay login; el script baja
  ``$ErrorActionPreference`` localmente alrededor de esa llamada para no
  matarse antes de leer el exit code.

## Principio Central De Autonomia — UNA SOLA VENTANA

IABV es **una unica ventana** con la que el usuario interactua al prender
su laptop. Todo lo demas lo hace el programa solo.

Reglas absolutas:
1. **El usuario NUNCA debe abrir PowerShell para configurar tokens.** Si
   falta un secreto, IABV abre el browser a la pagina correcta (GitHub
   settings, Devin API keys, etc.) y le pide al usuario que pegue el
   token en un dialogo dentro de la UI. IABV lo guarda automaticamente
   en ``~/.iabv_secrets.ps1`` via ``save_secret_to_profile()``.
2. **El usuario NUNCA debe instalar herramientas manualmente.** Si falta
   algo (gh, cloudflared, paquete pip), IABV lo instala solo. Si necesita
   admin, lo explica en la UI y ofrece un boton para elevacion.
3. **El usuario NUNCA debe editar archivos de configuracion.** Todo se
   configura desde la UI o se auto-detecta.
4. **Cada sesion de agente debe entender este principio.** No sugerir al
   usuario que ejecute comandos manuales, edite archivos, o copie tokens
   en una terminal. Si el agente necesita algo del usuario, lo pide via
   la UI de IABV o via un mecanismo automatico (device-flow, browser).

Funciones clave para autonomia de secretos:
- ``auto_correction_engine.auto_provision_missing_secrets()``: detecta
  secretos faltantes y abre el browser automaticamente para crearlos.
- ``auto_correction_engine.save_secret_to_profile(name, value)``: guarda
  un token en ``~/.iabv_secrets.ps1`` y lo activa en ``os.environ``.
  Llamado desde la UI cuando el usuario pega un token.
- ``auto_correction_engine._SECRET_PROVIDERS``: mapa de patrones de
  nombre de secreto a URLs de creacion (GitHub, Devin, OpenAI, etc.).

El bootstrap desde PowerShell (``iabv_bootstrap.ps1``) existe como
fallback para la primera instalacion o maquinas sin UI. Pero una vez
que la UI esta corriendo, **todo pasa por la ventana**.

## Contrato De Pre-Scan Metacognitivo

**OBLIGATORIO antes de modificar, planificar o evolucionar codigo.**

Cualquier agente (Devin, Codex, Claude, ChatGPT, o el propio IABV) debe
leer el panorama completo antes de tocar el codigo. Esto previene:
- duplicar logica que ya existe en los algoritmos de metacognicion
- romper la cadena de retroalimentacion entre servicios
- crear codigo aparte que deberia estar integrado en OSES, ExperimentLab o ValidationCycle

### Lecturas obligatorias antes de planificar cambios

1. **Audit trail**: `DecisionAuditTrail.self_examination_summary()` — estado de salud cloud, tendencias por proveedor, recomendaciones
2. **OSES**: `OperationalSelfExaminationService.current_review()` — hallazgos de degradacion, patrones repetidos, ajustes previos y si funcionaron
3. **Contexto portable**: `PortableContextService.build_package()` — incluye seccion `cloud_reasoning` con health score y trends
4. **Ciclo de validacion**: `AutonomousValidationCycleService` — estado actual de experimentos sandbox y candidatos en evaluacion
5. **ExperimentLab**: comparaciones activas, especialmente `domain=CLOUD_REASONING` para proveedores cloud

### Pipeline de decision cloud (no romper esta cadena)

```
CloudReasoningPlanner.generate_plan()
    → mide latencia, confianza, proveedor
    → DecisionAuditTrail.record() [SALIDA del framework]
    → OSES._cloud_reasoning_findings() [ENTRADA a metacognicion]
    → PortableContextService._cloud_reasoning_section() [exporta al contexto]
    → proxima sesion lee contexto → panorama completo
    → AdaptiveTaskOrchestrator.generate_cloud_plan() [pre-scan: lee audit + OSES]

AutonomousValidationCycle._cloud_provider_health_pass()
    → ApiKeyDiscoveryService.compare_all()
    → ExperimentLab.run_experiment(domain=CLOUD_REASONING) [comparacion real]
    → DecisionAuditTrail.record(phase=KEY_VALIDATION)
    → StrategySelector + AdaptiveWeightLayer [razonan sobre calidad]
```

### Regla: no crear codigo aparte

Si necesitas agregar logica de monitoreo, comparacion o decision sobre
proveedores cloud:
- NO crees un servicio nuevo. Usa `DecisionAuditTrail` para registrar,
  `OSES._cloud_reasoning_findings()` para analizar, `ExperimentLab` para
  comparar, y `PortableContextService` para exportar.
- Si el audit trail no tiene un campo que necesitas, extiende
  `DecisionRecord` (no crees otro modelo).
- Si OSES no detecta un patron que importa, agrega un hallazgo en
  `_cloud_reasoning_findings()` (no crees otro analizador).

## Forma De Trabajo En Sesiones Nuevas
1. lee este archivo primero
2. **ejecuta el pre-scan metacognitivo** (ver seccion anterior) para entender el estado actual del sistema antes de planificar cambios
3. inspecciona `bootstrap.py` y los archivos del slice relevante
4. identifica contratos involucrados
5. busca el cambio minimo que preserve arquitectura
6. valida con pruebas focalizadas y luego regresion razonable
7. si algo falla, diagnostica y corrige antes de seguir
8. reporta resultado, pruebas, riesgos y `UNRESOLVED`

## Prompt De Arranque
Al empezar una sesion nueva:
- lee `AGENTS.md`
- ejecuta el pre-scan metacognitivo: lee audit trail, OSES findings, contexto portable y estado de validacion
- despues inspecciona los archivos relevantes del repo
- usa primero estado vivo y contratos reales
- evita releer todo el historial si `PortableContextService` o `OperationalSelfExaminationService` ya condensan lo necesario
- trabaja con cambios minimos, verificables y guiados por evidencia real

## Salida Esperada Al Terminar
- que cambiaste
- por que era el cambio correcto
- que pruebas corriste
- que resultado dieron
- que quedo `UNRESOLVED`
- cual es el siguiente paso recomendado

## 2026-10-03 ACTIVE EVOLUTION RULE — UNIVERSAL ADAPTATION / NO BRUTE-FORCE PATCHING

When handling a material runtime problem, treat it as a possible observation about the general algorithm, not merely as a local defect.

Before implementation, agents must ask:
1. What universal mechanism could explain the symptom?
2. Which existing organ/contract already owns that mechanism?
3. What belongs to the invariant algorithm and what belongs to the device/tool/provider realization?
4. What is the smallest experiment that separates these explanations?
5. What verified Knowledge Delta should be persisted for future routing?

The project preference is:

`objective → state → causal frontier → capability → actor-fit → discriminating experiment → observation → verification → reconciliation → Knowledge Delta → reusable adaptation`.

Do not interpret repeated local patches as progress if they increase special-case logic without a demonstrated reusable principle. Adapters are allowed when they implement a shared capability contract; they must not become separate reasoning algorithms for each tool/device.

For laptop assistance, preserve the distinction:

`current live observation ≠ stale snapshot`
`metacognition exists ≠ metacognition is operationally useful`
`diagnosis ≠ action`
`action ≠ verification`

The user's long-horizon goal is an adaptive laptop assistant that can reason over environmental and temporal context, select viable realizations, diagnose routine problems from evidence, and retain verified knowledge so the user is interrupted mainly for genuine decisions. This is a design objective, not a claim of completed capability.

## 2026-10-03 ACTIVE EVOLUTION RULE — INFERENCE CONTRACT BEFORE PROVIDER PATCH

When an LLM/provider is slow, unavailable or semantically inadequate, first reconcile the universal inference contract before changing provider-specific parameters.

Required sequence:
`required capability → response contract → current constraints → candidate realizations → selection/configuration → validated result → fallback/degradation → future evidence`.

Provider-specific knobs are realization details. Before implementation, prove which existing organ owns each edge and whether the change closes a real cross-organ gap without duplicating decision authority.
## 2026-10-03 ACTIVE EVOLUTION RULE — INDEPENDENT CONTRACT CONFIRMATION BEFORE IMPLEMENTATION

After source archaeology identifies a cross-organ gap, obtain independent contract verification before implementation when the proposed change could affect shared routing/decision ownership.

For BIO-04, treat the independent confirmation as closure of the architectural-question stage, not closure of runtime behavior.

Implementation must:
- reuse existing owners;
- keep OSES semantic contract ownership explicit;
- keep provider-specific translation in adapters;
- avoid promoting a narrower selector to universal authority without evidence;
- add only the smallest contract/wiring necessary;
- verify structured response validity and fallback behavior;
- remain universal across local and cloud realizations.

## REGLA OPERATIVA — IA DESTINO OBLIGATORIA

Toda salida de planificación, reconciliación o routing que deje trabajo abierto debe terminar explicitando:

- **IA DESTINO:** nombre/actor concreto al que se debe enviar el siguiente paso;
- **CAPACIDAD:** por qué esa IA es adecuada;
- **OBJETIVO DEL RELEVO:** primera arista que debe cerrar;
- **PROMPT / ACCIÓN:** instrucción completa y copiable;
- **VERIFICADOR POSTERIOR:** IA siguiente sólo si ya puede determinarse por la frontera actual.

No es suficiente escribir únicamente `capability-fit`, `next actor` o `independent verifier`.

La selección sigue siendo dinámica y nunca una secuencia fija, pero el resultado operativo debe materializarse en una IA concreta:

`objective → current truth → first open edge → required capability → capability-fit → IA DESTINO CONCRETA → prompt/action`.

Si la IA concreta no puede determinarse con evidencia suficiente, debe declararse explícitamente `DESTINO NO DETERMINABLE` y explicar qué dato falta; no dejar un actor genérico como si fuera un handoff ejecutable.
