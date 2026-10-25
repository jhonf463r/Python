# Integrated authorization-to-handle G3 candidate — partial terminal result receipt

- Task: `M1A_G1_G3_INTEGRATED_AUTHORIZATION_TO_HANDLE_SOURCE_CANDIDATE_20261025`
- Reported terminal result: `PARTIAL_G3_HANDLE_CONTRACT_SOURCE_ONLY`
- Date: 2026-10-25 (America/Bogota).
- Provenance: complete terminal report pasted by the Owner in chat. Windows checkout, source content, raw diff bytes, worktree status and hashes below are `OWNER_SUPPLIED_CODEX_REPORT`; they are not independently authenticated by this receipt.
- Current canonical main at reconciliation baseline: `700a9b3ab482c1781d5c33b9b81253ab03e5c8a3`.

## 1. Reported candidate finding

Codex reports that source code now carries an opened capability through the authorization decision, permission, server guard and reader helper; helpers consume the handle/capability they receive rather than resolving the target again by path. It also reports source tests for object binding, denial when the approved root is unavailable, synthetic-ALLOW rejection, ambiguous paths and helper/handle identity.

This is only a source-level claim from the report. The six task diff artifacts were referenced through paths under `C:\Users\faber\AppData\Local\Temp\iabv-integrated-g3-baseline-6d066db1b6674bb3a04b0114cfdbbf5f\task-diffs\`. They were not attached as bytes or accessible to this reconciliation workflow. Consequently no independent line-by-line review, checksum recomputation or diff completeness check has been performed here. Do not treat the reported source linkage as an independently verified invariant.

## 2. Reported files and hashes

| Candidate file | Reported final SHA-256 | Reported diff artifact |
|---|---|---|
| `src/iabv15/services/security/read_authorization.py` | `b70ec24a33dc5a115d6ee09c32f0eecbff8e6d2ae3504f7f0bbe9827584903e3` | `src__iabv_v15__services__security__read_authorization.py.diff` |
| `src/iabv15/infra/mcp/server.py` | `78abb11646f80aa4bf8f7fef74b189c76896145ec7632bbab2731b179215f8ce` | `src__iabv_v15__infra__mcp__server.py.diff` |
| `src/iabv15/infra/mcp/windows_handle_reader.py` (new) | `d0910df59dcb734c8ebdf744872e1afd9c95c128fbff0713b4fa6b516051cbe7` | `src__iabv_v15__infra__mcp__windows_handle_reader.py.diff` |
| `tests/test_read_authorization.py` | `c1c7efe4b67857a9aad8d150b3591d614b9d5160a473ab4a52f7fd6a1afbf3bd` | `tests__test_read_authorization.py.diff` |
| `tests/test_mcp_server.py` | `e295e935f5752e0f3b1b18bd00cbda944920d18a30255fe9df297fb0606f76dd` | `tests__test_mcp_server.py.diff` |
| `tests/test_windows_handle_reader.py` (new) | `1558163d87414d2c9f1601329667f2e58e3ddd577954cf070ed38cc2ac627bd4` | `tests__test_windows_handle_reader.py.diff` |

The report says `audit_tools/__init__.py` and `test_mcp_audit_tools.py` were inspected and left unchanged. It reports six complete task diffs totaling `+798/-48`; this count and all hashes are not recomputed here.

## 3. Reported preservation and limits

- Checkout: `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`
- Branch: `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`
- HEAD before/after: `6bc568e1c5a898afd65cc045c779c25a9cdc5489`
- Remote main as read by Codex: `700a9b3ab482c1781d5c33b9b81253ab03e5c8a3`; local `origin/main` was reported stale at `2cecd5e9b9e175584d65bbb1198a53bc2346d095`.
- Index SHA-256 before/after: `8a32e6f7b2d642ee4a0217f96df037497cf47ecac52cecbea08717d4b8cb301a`.
- Pre-existing status: 7 staged routes, 11 unstaged routes, 12 unique routes. The same entries reportedly remain, with two newly created untracked files; prior work was not discarded.
- Staged and unstaged pre-existing diffs were reportedly preserved outside checkout as `preexisting-staged.diff` and `preexisting-unstaged.diff`.

These are reported preservation facts, not independently verified local facts.

## 4. Blocking dependency and adjudication

The report explicitly states:

- `APPROVED_WORKSPACE_ROOT_UNAVAILABLE`: the current composition has no production provider of an approved root identity.
- Native `ctypes` structures, `NtCreateFile`, information classes, rights and filesystem semantics were not validated in runtime.
- The source tests were authored but not run; no tests, build, runtime, MCP, real transport or protected reads were executed.
- G1, G2, root/mandate, Owner-to-Windows-principal, issuer/server binding and durable replay/rollback protection remain unestablished.

Therefore the appropriate adjudication is `PARTIAL_G3_HANDLE_CONTRACT_SOURCE_ONLY`, not a G3 pass. `G3_SAME_OBJECT=NOT_ESTABLISHED`. Protected reads remain `FAIL_CLOSED`; the bridge is not ready. A file ID or source-level capability contract is not authority, and a handle is not an immutable content snapshot.

## 5. Continuity and next boundary

The living `CONTINUITY_SPACE_TIME_ANTI_LOOP` revision 2.0 requires distinguishing report-attributed facts from directly observed evidence, preserving the event history, updating the sole current route and not starting an automatic follow-on. The candidate task's one authorization is consumed.

Next: obtain the six exact diff artifacts through an accessible attachment or an authorized evidence route, then obtain an explicit Owner decision for one bounded static review. Do not begin another implementation task until that review is completed, the evidence is reconciled, and a new explicit Owner decision permits any further action.

~~~text
TASK=M1A_G1_G3_INTEGRATED_AUTHORIZATION_TO_HANDLE_SOURCE_CANDIDATE_20261025
TASK_RESULT=PARTIAL_G3_HANDLE_CONTRACT_SOURCE_ONLY
RESULT_PROVENANCE=OWNER_SUPPLIED_CODEX_REPORT
SOURCE_DELTA_REPORTED=6_FILES; +798/-48
SOURCE_DIFFS=NOT_ACCESSIBLE_TO_THIS_REVIEW; NOT_INDEPENDENTLY_VERIFIED
SOURCE_TESTS=AUTHORED; NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
WORKSPACE_ROOT_IDENTITY_BOUND_TO_APPROVED_POLICY=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OBTAIN_DIFF_ARTIFACTS_AND_OWNER_DECISION_FOR_BOUNDED_STATIC_REVIEW
~~~
