# PR #473 — local verification worktree mismatch and safe reselection

- Date: 2026-10-23, America/Bogota.
- Repository: jhonf463r/Python.
- PR #473: OPEN / DRAFT / UNMERGED.
- Live main: 2a5ac42fabbd7c6a66591d127e379432495ad3bc.
- Candidate branch: codex/iabv-phase1-bridge-hardening-20261023.
- Remote candidate HEAD at this receipt's preflight: 52ceb9d362d15191147da5d44de4d3d4ee9a518d.

## Reported local preflight

The Codex verification attempt reported a clean local worktree, but the checked-out revision was older than the current PR head:

LOCAL_HEAD=cb1a8b545bc29b13b6da1ada0f0204601805f7dc
LOCAL_TOOL_ADAPTERS_BLOB=4e412ab8e5dfdf86af6f93ec04c15b0ed6434ca8
EXPECTED_REMOTE_TOOL_ADAPTERS_BLOB=5217b8deae01f34ec4407d0f2651612c47752034d
LOCAL_TEST_LOCAL_CLI_ADAPTER_BLOB=e9de76b25114e3b243f30e8e4830cdd651d75708
EXPECTED_REMOTE_TEST_LOCAL_CLI_ADAPTER_BLOB=fe53c660fd723ab82bde96b3077b25ca07cc24c2
TESTS=NOT_RUN
FILES_CHANGED_BY_CODEX_ATTEMPT=NO
INTERPRETER_AVAILABILITY=NOT_CHECKED
CANONICAL_DOCS_READ_BY_CODEX_ATTEMPT=NO

## Independent reconciliation

The live GitHub responses confirm:
- Live main is still 2a5ac42fabbd7c6a66591d127e379432495ad3bc.
- The candidate branch and PR #473 both point to 52ceb9d362d15191147da5d44de4d3d4ee9a518d.
- At that candidate HEAD, the exact fetched blob for IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py is 5217b8deae01f34ec4407d0f2651612c47752034d.
- At that candidate HEAD, the exact fetched blob for IABV_v1.5/tests/test_local_cli_adapter.py is fe53c660fd723ab82bde96b3077b25ca07cc24c2.
- GitHub comparison reports that candidate HEAD is 18 commits beyond the reported local HEAD, with no divergence.

The existing local worktree is therefore a clean, older ancestor of the remote candidate, not a safe place to run the targeted verification unchanged. Preserve it; do not reset or overwrite it.

## Safe resolution

Do not repeat the test attempt in cb1a8b5.... Do not reset, rebase, checkout over files, cherry-pick, clean, or overwrite the existing worktree.

After reading the five canonical files in order from live main and revalidating the remote refs, create a new, empty, sibling worktree detached at the exact current PR HEAD. Fetch the remote branch normally first and verify the fetched branch SHA is still 52ceb9d362d15191147da5d44de4d3d4ee9a518d. If main, the candidate branch, PR state, or target blobs have changed, stop and reconcile the new state before testing. Never assume the previously expected HEAD is still current.

In the new worktree, verify:
HEAD=52ceb9d362d15191147da5d44de4d3d4ee9a518d
IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py=5217b8deae01f34ec4407d0f2651612c47752034d
IABV_v1.5/tests/test_local_cli_adapter.py=fe53c660fd723ab82bde96b3077b25ca07cc24c2
WORKTREE=NEW, CLEAN, DETACHED

Then repeat the canonical preflight in order, including the active CURRENT-STATE.md routing, and confirm that the applicable bounded Phase 1 test authorization remains in force. Do not run tests unless that preflight establishes the authorization remains valid.

## Focused tests, only after preflight and authorization pass

The intended narrow selection is:
- tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it
- tests/test_local_cli_adapter.py::test_cloudflared_access_verbs_are_blocked_even_if_card_metadata_lists_them
- tests/test_local_cli_adapter.py::test_cloudflared_guard_uses_executable_identity_not_only_tool_id
- tests/test_local_cli_adapter.py::test_cloudflared_inspection_sandbox_never_invokes_process
- tests/test_local_cli_adapter.py::test_cloudflared_declared_tunnel_inspection_subcommands_reach_mocked_process
- tests/test_tool_teach_service.py::test_generic_shell_tunnel_is_blocked_before_sandbox_or_approval
- tests/test_tool_teach_service.py::test_shell_adapter_rejects_commands_in_sandbox_without_subprocess
- tests/test_common_sense_tunnel_disabled.py::test_common_sense_reasoning_never_launches_tunnel_even_when_execute_true

Report the exact interpreter/version, command, selection, count, output, exit code and worktree HEAD/blob identities. Keep tests mock-bounded; do not start Cloudflare, the application or MCP; do not run a real transport, build or deploy; do not access protected data, SQLite or credentials.

## Governance and continuity

PR_473=OPEN_DRAFT_UNMERGED
LIVE_MAIN=2a5ac42fabbd7c6a66591d127e379432495ad3bc
REMOTE_CANDIDATE_AT_RECEIPT=52ceb9d362d15191147da5d44de4d3d4ee9a518d
LOCAL_OLD_WORKTREE=cb1a8b545bc29b13b6da1ada0f0204601805f7dc; PRESERVE
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROCESS_OR_TUNNEL_STATE=NOT_INSPECTED
RATIFIED_OPTION_D_NO_BOOTSTRAP=REMAINS_IN_FORCE
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
PUBLIC_TUNNEL=PROHIBITED
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=REVALIDATE_MAIN_AND_PR; READ_CANONICAL_PREFLIGHT; CREATE_NEW_DETACHED_WORKTREE_AT_EXACT_CURRENT_PR_HEAD; VERIFY_BLOBS; THEN_FOCUSED_TESTS_ONLY_IF_AUTHORIZED

This record documents the failed preflight only. It does not change product code, test results, global routing on main, trust status, or any governance block. Keep the PR Draft and unmerged.
