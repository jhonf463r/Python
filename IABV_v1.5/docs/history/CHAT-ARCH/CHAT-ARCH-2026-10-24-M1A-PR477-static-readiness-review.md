# M1A PR #477 — bounded static readiness review and continuity handoff

- **Task:** `M1A_PR477_BOUNDED_STATIC_READINESS_REVIEW`
- **Date:** 2026-10-24 (America/Bogota)
- **North Star:** `GOVERNED_IABV_CODEX_BRIDGE`
- **Review mode:** static GitHub diff/source review only. No code, test, application, transport, protected read, or product state was executed or changed by this reviewer.
- **Disposition:** `STATIC_REVIEW=PASS_WITH_LIMITATIONS`; `MERGE_RECOMMENDATION=DO_NOT_MARK_READY_OR_MERGE_YET`.
- **Provenance:** exact refs/files below are `DIRECT_GITHUB`; the one-test STDIO execution is `OWNER_REPORTED_RESULT_WITH_DETAILED_OUTPUT`, not CI and not executed by this reviewer.
- **Record status:** documentation-only candidate; not canonical until this branch is accepted into live `main` and fetched back.

## 1. Revalidated refs and PR metadata

- Repository: `jhonf463r/Python`.
- Base/live-main reference established during preflight: `c3bc9d8b4f727483081cf24650d4e7209687024c`.
- Base CURRENT-STATE blob: `809ea431068de28c55e681c93c447000a986e3ab`.
- PR: [#477 — IABV: consolidate MCP candidates and fail closed by profile](https://github.com/jhonf463r/Python/pull/477).
- Candidate branch: `codex/iabv-mcp-governed-restricted-consolidation-20261024`.
- Candidate HEAD: `47e9458836369a67d4629398b62a93d99e18cc74`.
- GitHub metadata at review: OPEN, DRAFT, UNMERGED; base branch `main`; 43 changed files; 2,723 additions; 1,772 deletions; 64 commits ahead of the specified base; comparison status `ahead`, `behind_by=0`.
- The diff endpoint returned patches for all 43 changed files (about 306k patch characters). The review inspected the full patch inventory plus relevant server, startup, service, adapter, test and documentation content.
- GitHub review submissions, review threads, commit combined-status checks and PR-associated workflow runs returned empty results for this HEAD in the queried connector surfaces. Record as `NO_RESULTS_RETURNED_BY_QUERIED_GITHUB_SURFACES`; do not infer that no CI or review activity exists anywhere else.

## 2. Reconciled evidence from the preceding task

Task `M1A_MCP_LOCAL_RESTRICTED_STDIO_BOUNDED_TEST` was supplied by the Owner as:

```text
RESULT=PASS
BASE_SHA=c3bc9d8b4f727483081cf24650d4e7209687024c
PR=477
HEAD=47e9458836369a67d4629398b62a93d99e18cc74
TEST_PATH=IABV_v1.5/tests/test_mcp_local_restricted_stdio.py
TEST_BLOB=25b4cedf8f988acb754aa5faa6d130fad8e93473
TEST_EXIT_CODE=0
TEST_OUTPUT=1 passed in 2.69s
TOOLS_EXPOSED=exactly bridge_health
BRIDGE_HEALTH={"status":"ok"}
FORBIDDEN_READ_REJECTED=YES
SYNTHETIC_WORKSPACE_EMPTY_AT_END=YES
POST_GIT_STATUS_SHORT=empty
FILES_CHANGED=0
DEPENDENCIES=pytest 9.0.3 and mcp importable; no installs/updates
NETWORK_TRANSPORT=NOT_USED_BY_TEST (Git remote was used to obtain the isolated clone)
PROTECTED_READS=NOT_RUN
```

A separate temporary clone reportedly failed while materializing long paths; it was not used for this test and reportedly remained untouched after failure. The test run itself was reported from the preserved isolated checkout `C:\Users\faber\AppData\Local\Temp\iabv-1047925d66e241ba89db742d12f27141`.

Interpretation: this is a real client/server STDIO test as reported by the Owner, limited to initialization, listing the one diagnostic tool, a health call, a rejected call to a tool that is not registered, and the empty synthetic workspace assertion. It does **not** prove protected-read authorization: `read_repo_file` is absent from the restricted profile, so the negative assertion is not a test of the full tool's internal authorization. It does not prove full AppBootstrap, complete application health, a real repository read, network transport, IABV→Codex delegation, downstream ingestion, persistence, G1/G2/G3, or production runtime.

The separate report that PR #477 had 19 focused tests pass remains reported in the candidate's verification narrative; this review did not run them and did not find a matching status check in the queried GitHub surfaces. The new STDIO result must not be retroactively relabelled as CI.

## 3. Positive static findings

### P-01 — Restricted server profile fails closed through the intended entrypoints

Candidate source:
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`, blob `a52d96a4d94350ea59a3ea029801157aa515adf9`.
- `SUPPORTED_TRANSPORTS={"stdio"}`, `SUPPORTED_PROFILES={local_restricted}`: lines 76–84.
- Public constructor rejects unsupported profiles and injected MCP registries for the restricted profile: lines 127–155.
- Restricted profile registers only `bridge_health` and returns before full registry registration: lines 480–492.
- Wrapper `run()` checks profile and transport before calling FastMCP: lines 3174–3191.
- `create_server()` and `main()` validate profile/transport and do not instantiate `AppBootstrap`: lines 3288–3345.
- `bridge_health` returns only `{"status":"ok"}`: lines 483–489.

Disposition: positive static evidence for these wrapper/factory/CLI execution routes. Not proof of a universal transport invariant; see F-01.

### P-02 — UI bridge and legacy startup paths do not launch MCP/tunnels through reviewed hooks

- `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py`, blob `e2d6066e566a12a1868f19818e9a98f05e55154c`: runner shims refuse startup (lines 95–138); `_start_locked()` enters fail-closed state before calling runners or World Model (lines 285–303).
- `IABV_v1.5/src/iabv_v15/bootstrap.py`, blob `d70a2a199f238cbd037deb9574985fe59bab8a28`: legacy launch hooks return without creating subprocesses (around lines 4377–4414); main launch block logs that MCP/tunnel auto-start is disabled.
- `IABV_v1.5/scripts/run_mcp_bridge.ps1`: defaults to STDIO, rejects other transports, sets `IABV_MCP_PROFILE=local_restricted` and does not invoke Cloudflare.
- `IABV_v1.5/scripts/iabv_bootstrap.ps1` and `scripts/start_iabv.ps1`: the bridge/tunnel delegation and port-killing operations are removed.
- `IABV_v1.5/src/iabv_v15/services/common_sense_engine.py`: the tunnel-start executor and its registration were removed.
- `IABV_v1.5/tests/test_bootstrap_mcp_autostart_disabled.py`, `test_mcp_bridge_launcher.py`, `test_common_sense_tunnel_disabled.py`: added static/mocked regression guards; none was run during this review.

Disposition: positive static evidence for the reviewed in-repository paths, not runtime evidence that no process/tunnel is currently active.

### P-03 — Generic shell execution and direct tunnel launch through that adapter are blocked in source

- `IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py`, blob `5217b8deae01f34ec4402b82c651e9995ae94514`, lines 1734–1755: generic `ShellToolAdapter.run()` unconditionally returns `generic_shell_execution_disabled` and does not call subprocess.
- `IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py`, blob `2dd506817cfd336080b09619c49b2a12049636c6`, lines 775–802: `shell_command` is rejected before adapter availability, sandbox, approval evaluation or adapter invocation.
- `LocalCliToolAdapter` implements a fixed Cloudflared verb/subcommand guard in `tool_adapters.py`, lines 2597–2757. For Cloudflared identified by card ID, resolved executable, command name or tool family, only the enumerated first tokens are admitted and `tunnel` is limited to `list`/ `info`. The added tests mock subprocess to assert prohibited verbs are rejected before invocation.
- The inspection commands `cloudflared tunnel list/info` may still make outbound control-plane requests if executed via an approved local task. They are not a server/tunnel-launch path, but are not synonymous with “no network activity anywhere in the application.”

Disposition: positive static closure of the previously recorded generic-shell and Cloudflared tunnel-launch paths in this candidate. This does not prove all possible local code, plugins, user extensions or external processes cannot launch a tunnel.

## 4. Findings and limitations

### F-01 — Underlying FastMCP instance remains directly accessible (hardening gap)

**Source:** `server.py` blob `a52d96a4d94350ea59a3ea029801157aa515adf9`, lines 143–155 and 3288–3302.

The wrapper stores the raw SDK instance in public attribute `self.mcp`. The methods `IABVMCPServer.run()`, `create_server()` and `main()` impose the STDIO-only guard, but a programmatic caller holding a returned server object could invoke the SDK instance directly instead of using the wrapper's guarded method.

Important scope distinction: under normal construction, that raw instance has only `bridge_health` registered. The static review did not identify an in-repository product caller that runs the raw instance directly, and this finding does not prove an active network listener or direct access to protected data. It means the absolute assertion “no path can run network transports” is stronger than the demonstrated boundary: the underlying server object itself is not encapsulated by the wrapper.

**Recommendation for a separately authorized code change:** encapsulate the SDK runner so callers cannot bypass the wrapper's profile/transport checks; keep one guarded execution boundary and add a regression test that proves the public object/API cannot start a network transport. Do not run a network transport to test this.

Disposition: `STATIC_HARDENING_FINDING; ACTIVE_PRODUCT_BYPASS_NOT_DEMONSTRATED`. This limits acceptance of the universal transport-prohibition claim.

### F-02 — Governance helper has latent fail-open semantics

**Source:** `mcp_bridge_service.py` blob `e2d6066e566a12a1868f19818e9a98f05e55154c`, lines 305–337.

`_governance_gate_block()` returns `None` if World Model is missing, lookup raises, or snapshot is absent. In isolation this treats an unknown/unavailable governance assessment as no block. The current `_start_locked()` route fails closed before invoking it, and no active caller was found in the reviewed service, so this is not a demonstrated current startup bypass.

Disposition: `LATENT_FAIL_OPEN_HELPER; CURRENT_START_PATH_FAILS_CLOSED`. Before a future reactivation, change the helper's contract to distinguish `blocked`, `clear` and `unknown/error`, with unknown/error blocking.

### F-03 — Formal CI/review evidence is absent from the queried surfaces

For the reviewed HEAD, the GitHub connector returned empty lists for PR reviews, review threads, combined commit status and PR-associated workflow runs. The report `19 passed` is supplied in PR narrative, and the one real STDIO test is supplied by the Owner. Both should remain separately labelled.

Disposition: `VALIDATION_EVIDENCE_INCOMPLETE_FOR_FORMAL_ACCEPTANCE`. This is not a claim that no checks ran anywhere; it records what the queried GitHub surfaces returned. Do not run tests as part of this review.

### F-04 — No full bridge functionality or protected-read proof

The only tool in `local_restricted` is `bridge_health`. The STDIO test's rejection of `read_repo_file` confirms that it is not exposed by the restricted profile, not that an enabled protected reader correctly authorizes or rejects a real read. This is consistent with the deliberate no-bootstrap decision; it is a capability boundary, not a reason to bypass it.

Disposition: `EXPECTED_RESTRICTION; BRIDGE_NOT_READY`.

### F-05 — Startup script retains its pre-existing AutoPull behavior

`IABV_v1.5/scripts/start_iabv.ps1` still defaults `$AutoPull = $true` and may fetch/pull `origin/main` and relaunch after critical file changes (candidate blob `55322d750365387c3cff9674f983b239409b2398`, around lines 118–219). This review did not execute the script. This behavior is not evidence that the review altered any checkout, and was not introduced by the static review; it is operationally relevant to any future manual launch or test task. Before authorizing such a task, explicitly decide whether AutoPull is allowed or use the documented `-NoAutoPull` path in a controlled checkout.

Disposition: `PREEXISTING_OPERATIONAL_SIDE_EFFECT_TO_SCOPE_BEFORE_FUTURE_EXECUTION`.

## 5. Evidence boundary and corrections to reasoning

This review adds these durable lessons:

1. **Review wrapper and underlying engine separately.** Guarding `IABVMCPServer.run()` does not encapsulate the public `self.mcp` SDK object; an absolute guarantee requires tracing every callable reference and supported entrypoint, not only the wrapper's normal methods.
2. **Separate active paths from theoretical/API escape hatches.** A direct SDK bypass is a hardening gap, not a proven product exposure when no product caller was found and the registry remains health-only.
3. **Negative tool-call tests must be interpreted precisely.** Calling an unregistered tool proves non-exposure in that profile; it does not test internal authorization of the unregistered tool.
4. **Keep provenance stages distinct:** source inspection, reported focused unit tests, Owner-reported isolated real STDIO handshake, GitHub CI status, production runtime and protected-reader authorization are different evidence classes.
5. **An empty GitHub status/workflow query means only “no results returned by those surfaces.”** Do not convert it into proof that CI/review does not exist globally.
6. **A passing health-only test is bounded progress, not full bridge readiness.** Do not promote G1/G2/G3, protected-reader permission, AppBootstrap health, bidirectional IABV symbiosis or causal reuse from that result.
7. **Close the exact historical defect, then stop.** The old tunnel-start hazards recorded for Common Sense, generic shell and Cloudflared CLI are statically addressed by this candidate. Do not rerun those investigations unless new evidence reveals a new launch route.
8. **Continuity updates stay append-only and subordinate to the route authority.** Record this review without overwriting Option D, inspecting trust assets, changing `NEXT_ACTION`, or turning documentation into implementation authorization.

## 6. Canonical governance preserved

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
LAST_TERMINAL_TASK=M1A_PR477_BOUNDED_STATIC_READINESS_REVIEW
REVIEW_RESULT=PASS_WITH_LIMITATIONS
MERGE_RECOMMENDATION=DO_NOT_MARK_READY_OR_MERGE_YET
REVIEWED_MAIN_SHA=c3bc9d8b4f727483081cf24650d4e7209687024c
REVIEWED_PR=477
REVIEWED_PR_HEAD=47e9458836369a67d4629398b62a93d99e18cc74
OWNER_REPORTED_STDIO_TEST=PASS; 1 PASSED; NOT_CI
CI_STATUS=NO_RESULTS_RETURNED_BY_QUERIED_GITHUB_SURFACES
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN_BY_THIS_REVIEWER
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=NOT_RUN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

The review authorization did not allow source changes, tests, an application or transport launch, protected reads, PR state changes, merge or deployment. None was performed.

## 7. Follow-up dependency, only if explicitly authorized later

The immediate static-review follow-up would be a single bounded code-design/review task for F-01: define and implement an encapsulated, single guarded MCP execution boundary, with targeted regression coverage, in an isolated candidate. That work is **not authorized by this receipt** and must not happen automatically. The latent governance helper F-02 can be handled only under a future explicit scope, before any attempt to re-enable the bridge.

The canonical route is unchanged. Continue to maintain no-bootstrap/fail-closed; reopen the trust-bootstrap path only on genuinely new authority evidence or a new explicit Owner decision that changes its basis.
