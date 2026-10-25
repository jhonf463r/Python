# G3 native-handle source candidate — terminal authorization-binding blocker

Date: 2026-10-25, America/Bogota.

Task: M1A_G1_G3_NTCREATEFILE_HANDLE_RELATIVE_SOURCE_CANDIDATE_20261025.

Terminal result: BLOCKED_ON_NATIVE_HANDLE_BINDING_DETAILS.

Provenance: the Owner supplied the complete Codex terminal report in this conversation. All local checkout, branch/HEAD, status/index, source line, hash, backup and preservation claims in this receipt are OWNER_SUPPLIED_CODEX_REPORT. They were not independently re-observed from this documentation workflow. GitHub main and canonical docs were independently retrieved for the reconciliation.

## 1. Source-candidate result

Codex reports no source changes. The proposed native Windows APIs do not close the missing link between the authorization decision and the object the reader ultimately consumes. The task acceptance contract prohibited changing the resolver/coordinator contract, but that contract is the precise source seam that needs to change. A native handle created after a path-string authorization would not establish that the decision applied to the same object.

Reported findings:
- ReadAuthorizationCoordinator.decide_mcp_read() takes operation and requested_relative_target as strings (read_authorization.py:465–470).
- The resolver returns a textual canonical_target (reported at :149–160 and :605–617), and the resulting permission retains that text rather than an identity-bearing open object (reported at :635–645).
- The workspace in server.py is obtained as a textual path and has a fallback to os.getcwd() (reported at :260–274); a policy-approved root identity that can be bound to the native handle is not established.
- The guard continues denying even when presented a synthetic ALLOW if the operation's target object is not bound (server.py:298–304 and :348–359).
- The candidate stays fail-closed before the protected reader helpers are called.

The correct result is no implementation, not a path wrapper, a copied file ID, or a native handle unrelated to the authorization decision. This task did not prove that the OS primitive is unavailable; it identified a missing application-level contract plus missing trusted-root binding.

## 2. Reported preservation and hashes

- Checkout: C:/Users/faber/AppData/Local/Temp/iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27
- Repository: https://github.com/jhonf463r/Python.git
- Branch: codex/m1a-g1-owner-governed-bootstrap-organ-20261024
- HEAD: 6bc568e1c5a898afd65cc045c779c25a9cdc5489
- Remote main before/after according to Codex: b5e65210a72f0e22f07d8bc9332b8173f37b7560
- Status before/after: 7 staged routes, 11 unstaged routes, 12 unique routes; reported complete list: CURRENT-STATE.md, bootstrap.py, server.py, mcp_bridge_service.py, github_owner_merge_bootstrap.py, read_authorization.py, windows_crypto.py, test_bootstrap_defer_init.py, test_github_owner_merge_bootstrap.py, test_mcp_bridge_service.py, test_mcp_server.py, test_read_authorization.py.
- Index SHA-256 before/after: 8a32e6f7b2d642ee4a0217f96df037497cf47ecac52cecbea08717d4b8cb301a.
- Task diff is reported empty; SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.

Reported pre-edit and post-task working-tree SHA-256 values (identical):
- audit_tools/__init__.py: 5208cc69baed737482c373da73691420ee428b4e968faecc245de10d23b5b9b7
- server.py: 4d1327b40a336edd523ea620079ae86857b0855b4d5df95f86d92e4eee73944f
- test_mcp_audit_tools.py: cb4575748dcf3789e6987f252bc485bb26b5ce26de5876e56465991e066f8d97
- test_mcp_server.py: a16af49a5748cf62f1b12391a5e64aaaf49b3f3459d057e1707315e0a914bc80

The report says byte-for-byte backups exist outside the checkout in C:/Users/faber/AppData/Local/Temp/iabv-ntcreatefile-source-baseline-1e57700426c9414d97e4172f154d90a6, with initial staged/unstaged diff hashes 8d5dbaf08524b39768ba945f1d05e14c3ef5f6f7239404726993be2498ff0ae5 and e1bac0ebcc4e44c4ea75434512f7aa469b2b097d388617d510d90035e4e0b6b5. Those Windows-local backup files are not available to this reconciliation environment, so their content has not been independently fetched or rehashed here.

No code or tests were added. No tests/build/runtime/MCP/real transport/protected reads were run. No stage/commit/push/publication was performed according to the report.

## 3. Terminal gates

~~~text
TASK=M1A_G1_G3_NTCREATEFILE_HANDLE_RELATIVE_SOURCE_CANDIDATE_20261025
TASK_RESULT=BLOCKED_ON_NATIVE_HANDLE_BINDING_DETAILS
SOURCE_DELTA=NONE
FILES_CHANGED=0
SOURCE_DIFF_SHA256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
SOURCE_TESTS=AUTHORED_OR_UNCHANGED; NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_REQUIRED_TO_AUTHORIZE_AN_INTEGRATED_AUTHORIZATION_TO_HANDLE_CONTRACT_TASK_OR_KEEP_BLOCKED
STOP_CONDITION=ONE_AUTHORIZED_TASK_CONSUMED; NO_FOLLOW_ON_WITHOUT_NEW_EXPLICIT_SCOPE
~~~

## 4. Exact next decision boundary

The next useful source candidate cannot be only an audit_tools/NT API wrapper. Its contract must span the seam that is currently missing:

1. The server obtains an approved workspace-root capability through an explicit policy/configuration dependency. An os.getcwd() fallback or a path string alone is not accepted as an authorization root.
2. The resolver performs the safe handle-relative walk and produces an owned OpenedTarget capability, not only canonical_target text.
3. The authorization coordinator evaluates that same target capability (or an immutable identity-bearing token bound to its open object), operation, policy, and limits. It must not authorize a textual target and then bind a separate object after the decision.
4. The final permission/decision must be bound to that target capability and consumed by the reader; the guard verifies that exact binding.
5. File read and directory enumeration use the exact same authorized object handle. Any API/provider/type/identity error denies. The target capability has explicit ownership and close-once lifecycle semantics.

This integrated source scope necessarily touches the resolver/coordinator contract that the prior task was forbidden to modify. It also needs a precise policy answer for how an approved workspace root identity is supplied; it must not invent an independent IABV authority root. A further task requires a new explicit Owner authorization. Until then, no automatic follow-on is permitted.

