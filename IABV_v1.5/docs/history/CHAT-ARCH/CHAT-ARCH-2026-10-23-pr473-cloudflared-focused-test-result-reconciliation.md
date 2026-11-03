# PR #473 — Cloudflared focused-test result and evidence reconciliation

Updated: 2026-10-23 (America/Bogota).
Repository: `jhonf463r/Python`.
PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
Candidate branch: `codex/iabv-phase1-bridge-hardening-20261023`.

## 1. Disposition

```text
FOCUSED_TESTS=PASS_REPORTED_BY_CODEX
TEST_SELECTION_NODES=8
PARAMETRIZED_CASES_REPORTED=16
REPORTED_DURATION=2.30s
REPORTED_EXIT_CODE=0
INDEPENDENT_COORDINATOR_EXECUTION=NOT_RUN
GLOBAL_PUBLIC_TUNNEL_PROHIBITION=NOT_ESTABLISHED
IMPLEMENTATION=NOT_AUTHORIZED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

This receipt records the bounded run reported by the Owner from Codex. The coordinator did not independently execute pytest. The returned console excerpt was:

```text
................                                                         [100%]
16 passed in 2.30s
PYTEST_EXIT_CODE=0
```

## 2. Remotely verified source baseline at reconciliation

GitHub was revalidated after the result was supplied:

- Live `main`: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- PR #473 head: `d09b514116bcb8867004d3327a7fc5cdb3810e75`.
- PR state: `OPEN / DRAFT / UNMERGED`; base is `main`.
- Candidate branch ref and PR endpoint agree on the HEAD.
- The branch-to-PR metadata currently reports 36 changed files.

The relevant source/test blobs fetched from GitHub at the candidate HEAD are:

- `IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py`: `5217b8deae01f34ec4402b82c651e9995ae94514`.
- `IABV_v1.5/src/iabv_v15/services/tools/tool_registry.py`: `0599ae4ecd77d85cdee05a04fadcccaad2d5bea2`.
- `IABV_v1.5/tests/test_local_cli_adapter.py`: `fe53c660fd723ab82bde96b3077b25ca07cc24c2`.

The report states that Codex ran from a new sibling worktree,
`C:\Users\faber\.codex\worktrees\iabv-phase1-cloudflared-tests-d09b514\Python`,
detached at this exact HEAD, with a clean tree and the expected blobs. Those local worktree properties remain `OWNER_REPORTED`; GitHub verifies the remote HEAD/blob identities, not the local filesystem state.

## 3. Canonical preflight

Immediately before reconciliation, the five required documents were fetched from live `main` in the mandated order:

1. `IABV_v1.5/AGENTS.md` — blob `7fde748574fb8916e94332b99aa512fc44823bcc`.
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md` — blob `af29123091ae6090509b1039176458825e4b1a91`.
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — blob `f95f5bc69b98a7039d173089aa9b8d4d929812e9`.
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md` — blob `e073fe2d600c0b7b3051a10711ef21e2897b1ac3`.
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md` — blob `4e497fb70f58a1a42d29470068e7a13b81cadc2f`.

The canonical `CURRENT-STATE.md` remains the sole routing authority and retains:

```text
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

The narrow test authorization conveyed for this run does not authorize product implementation, other tests, build, runtime, real transport, public tunnel use, merge, deployment, protected reads, spending or block release. This candidate-only evidence receipt does not change live `main` or its routing.

## 4. Reported test execution

Interpreter: `C:\Python314\python.exe`, Python 3.14.4.

Environment reported by Codex:

- `PYTHONDONTWRITEBYTECODE=1`.
- `PYTHONPATH` pointed to this worktree's `IABV_v1.5/src`.
- Working directory was this worktree's `IABV_v1.5`.
- Pytest cache disabled with `-p no:cacheprovider`.

Command shape reported: `C:\Python314\python.exe -m pytest -q -p no:cacheprovider` with exactly these eight node selectors:

1. `tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it`
2. `tests/test_local_cli_adapter.py::test_cloudflared_access_verbs_are_blocked_even_if_card_metadata_lists_them`
3. `tests/test_local_cli_adapter.py::test_cloudflared_guard_uses_executable_identity_not_only_tool_id`
4. `tests/test_local_cli_adapter.py::test_cloudflared_inspection_sandbox_never_invokes_process`
5. `tests/test_local_cli_adapter.py::test_cloudflared_declared_tunnel_inspection_subcommands_reach_mocked_process`
6. `tests/test_tool_teach_service.py::test_generic_shell_tunnel_is_blocked_before_sandbox_or_approval`
7. `tests/test_tool_teach_service.py::test_shell_adapter_rejects_commands_in_sandbox_without_subprocess`
8. `tests/test_common_sense_tunnel_disabled.py`

Codex reports eight selected nodes expanding to 16 parametrized cases, all passing with exit code 0 in 2.30 seconds. The exact individual-case breakdown was not supplied; do not infer it.

## 5. Scope and limitations

The reported execution started only the local Python/pytest process. The report states that Cloudflare, tunnels, IABV, AppBootstrap and MCP were not started; process-related cases used mocks. It also reports the worktree remained clean (`WORKTREE_STATUS_COUNT=0`) and no code or tests were modified.

These are supplied execution facts, not an independent replay by the coordinator. The run does not prove:
- absence of every possible tunnel-launch path throughout the application;
- state of any real local process or tunnel;
- application, MCP or transport behavior at runtime;
- closure of G1, G2, G3, or any of the eight implementation prerequisites.

No code was changed by this reconciliation. It is a candidate-branch evidence record only. PR #473 must remain open, Draft and unmerged.

## 6. Preserved invariants and stop condition

```text
RATIFIED_OPTION_D_NO_BOOTSTRAP
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
PUBLIC_TUNNEL=PROHIBITED
REAL_TRANSPORT=NOT_RUN
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

Result: bounded focused tests are reported passing; overall security acceptance and global public-tunnel prohibition remain unestablished. Stop after this reconciliation. The next actor is Owner/governance unless genuinely new authority evidence or a separate explicit Owner decision changes the canonical route.
