# CHAT-ARCH-2026-10-13-239 — Target protocol tool-surface audit remains blocked

Date: 2026-10-13 (America/Bogota)
Classification: Owner-supplied second static audit / protocol-target adjudication; result `APP_SERVER_STATICALLY_BLOCKED`.
Remote canonical baseline at intake: `main @ 082710831252bc44f7382d5817760cd92c0a6094`.
No local source, processes, tests, or runtime were independently examined or executed by this documentation writeback. Local line references and git state below are the Owner's supplied observations.

## 1. Decision

**Option B is supported:** the available evidence does not establish a target-protocol contract that makes all effect-capable tools unavailable before a turn starts. Keep Codex App Server blocked for a real text-only turn. A new authorization to send a prompt would not close this safety gap.

## 2. Owner-reported worktree

- Worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`
- Branch: `codex/m0a-safe-ui-boot`
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- 56 tracked files modified; 6 untracked files.
- Existing `.pyc` changes and the untracked task-ID test were preserved.
- The report says this audit did not modify files, run tests/processes, or make external calls.

These are report-supplied measurements and are not the status of remote `main`. Preserve the entire dirty worktree. This documentation writeback does not commit or publish the local code changes.

## 3. Target CLI / protocol identity

The adapter validates the reported `userAgent` against expected version `0.120.0` at `IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py:2453` and `:2523`, according to the Owner's source report. The launcher resolver selects `codex.cmd`, `codex.ps1`, or `codex` dynamically from `PATH` at `:2613`. The reviewed repository manifests do not pin the executable version.

Therefore:
- expected/validated user-agent version: `PROVEN_BY_SOURCE` according to the supplied audit;
- executable identity and effective protocol version actually reached: `UNPROVEN`;
- user-agent validation alone does not authenticate which executable supplied it.

The public upstream schema/readme references recorded in 238 are supplementary, not authoritative proof about the dynamically resolved local executable. No CLI execution is permitted just to discover its version in this tranche.

## 4. Findings matrix

| Claim | Exact evidence supplied | State | Risk |
|---|---|---|---|
| Config selects `IABV_CODEX_HOME` | `infra/config.py:55`; `bootstrap.py:666` | `PROVEN_BY_SOURCE` per report | Cannot prove a valid login/session, quota or billing mode. |
| Child receives a restricted environment with `CODEX_HOME` | `services/tools/tool_adapters.py:2844` | `PROVEN_BY_SOURCE` per report | No proof of authentication, entitlement or cost. |
| Task ID is checked before dispatch in the normal SafeUI route | `ui/viewmodels/control_center_viewmodel.py:11749`; `services/tools/tool_teach_service.py:612, 794` | `PROVEN_BY_SOURCE` per report; earlier 32-test PASS is `OWNER_REPORTED` | Adapter itself does not revalidate task identity in `_authorization_error()` at `:3378`; normal path depends on earlier SafeUI/ToolTeach guards. |
| Expected CLI version is `0.120.0`, but resolver is dynamic | `tool_adapters.py:2453, 2523, 2613`; no manifest pin reported | Expected version and resolver `PROVEN_BY_SOURCE`; actual executable/version `UNPROVEN` | Request/schema interpretation may be for a different CLI/protocol contract. |
| Normal SafeUI dispatch skips adapter `preflight()` | Definition at `tool_adapters.py:3147`; normal `run()` reaches `_exchange()` at `:3414`; bounded search found definition but no invocation | `PROVEN_BY_SOURCE` per report | Preflight is not a normal-path dispatch barrier. |
| Preflight obtains config/MCP inventory but does not fail closed on a nonempty inventory or prove effective tool surface | `tool_adapters.py:3135, 3174, 4017` | `PROVEN_BY_SOURCE` per report | Counting MCP servers does not establish absence of server-side tools, built-ins or application capabilities. |
| Requested thread/turn policy limits execution | `tool_adapters.py:3512, 4029`: requests read-only sandbox, `on-request`, `turn_scope`/sandbox policy; report says no explicit empty tool list | Request parameters `PROVEN_BY_SOURCE`; actual effect `UNPROVEN` | Sandbox/approval settings are not proven to remove all tools. |
| Client rejects approval requests and disallowed event types | `tool_adapters.py:3794, 4086` | Client-side reaction `PROVEN_BY_SOURCE` per report | Happens after receipt; does not prove there was no earlier server-side effect. |
| Terminal task/thread/turn correlation and existing-consumer wiring exist | `tool_adapters.py:4076`; `tool_teach_service.py:986`; `tool_memory.py:31`; `control_center_viewmodel.py:15314` | Wiring `PROVEN_BY_SOURCE`; real exchange/consumer evaluation `UNPROVEN` | Persisted wiring is not evidence of an actual response or evaluation. |

## 5. Authentication and cost

The reported code uses local CLI App Server over stdio, passes configured `CODEX_HOME` through a restricted environment, and does not create/pass an API key in that path. The existence of a valid signed-in session, the auth route used by the home, account eligibility, quota and billing effects remain `UNPROVEN`. No credential/session inspection is permitted.

## 6. Primary blocker

No source evidence supplied establishes a server-enforced, pre-turn guarantee that removes every effect-capable tool from the model-visible and server-executable surface, including:
- built-in tools;
- MCP tools;
- app/plugin/integration capabilities;
- any other effect-capable server tool.

The normal path reportedly does not invoke `preflight()`; that method's inventory count does not fail closed on a nonempty result and does not establish the effective server-side surface. Requested sandbox/approval fields are parameters, not observed enforcement. Post-receipt rejection of approvals or event types is not pre-effect prevention.

The contract/version gap matters: the code expects `0.120.0` yet dynamically resolves the actual executable and does not pin the version in the reviewed manifests. Current upstream `main` schema must not be treated as the target implementation until compatibility is grounded in existing files.

## 7. Minimum next step — read-only, no implementation

Result remains `APP_SERVER_STATICALLY_BLOCKED`.

Next edge: `CODEX_APP_SERVER_SERVER_ENFORCED_TOOL_SUPPRESSION_UNAVAILABLE_OR_UNPROVEN`.

Use only existing source, manifests and configuration references to:
1. establish whether a specific CLI/protocol contract is pinned or otherwise identifiable without invoking the executable;
2. match the request shapes used by the adapter to that contract;
3. establish whether it offers a server-enforced mechanism that removes or safely limits all effect-capable tools *before* `turn/start`;
4. establish that normal SafeUI dispatch fails closed when it cannot prove the required tool surface, including unexpected/nonempty MCP or integration inventories.

Do not run the CLI for version discovery, start App Server, send a prompt, execute tests/builds, make network/UI/CDP calls, read credential or session contents, edit source/config, or incur costs. If the contract or guarantee cannot be established statically, keep the route blocked and report the missing capability precisely. No source-edit authorization is granted by this record.

## 8. Evidence ladder

- Task identity: integrated in normal SafeUI source per supplied audit; focused tests previously reported as passing, not independently rerun here.
- Actual executable/protocol version: `UNPROVEN`.
- Auth/session/entitlement/quota/cost: `UNPROVEN`.
- Server-enforced no-tools-before-effects: `UNPROVEN` (primary blocker).
- Actual terminal response and consumer evaluation: `UNPROVEN`.
- M0-B capability selection, D016 controlled self-development and causal reuse: not established.

Do not authorize the real turn until the tool-surface property and remaining safety gates are resolved separately.
