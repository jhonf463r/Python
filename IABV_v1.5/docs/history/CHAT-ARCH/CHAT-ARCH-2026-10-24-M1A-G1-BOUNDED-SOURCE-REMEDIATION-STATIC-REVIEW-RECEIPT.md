# Bounded source-organ remediation — static review and route reconciliation receipt

- Date: 2026-10-24, America/Bogota
- Canonical baseline: `main=1afe60c3cc7372a90ad6f8507904f2aa44c88ae7`.
- Task: `M1A_G1_BOUNDED_SOURCE_ORGAN_REMEDIATION`.
- Reported task result: `BOUNDED_SOURCE_ORGAN_REMEDIATION_CANDIDATE_ONLY`.
- Review result: `PASS_WITH_NOTES_FOR_PASTED_PATCH_TEXT_ONLY`.

## 1. Evidence custody and limits

The Owner supplied the five-file patch text in the ChatGPT conversation. The Codex hand-back reports that the Windows checkout was `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`, branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, HEAD `6bc568e1c5a898afd65cc045c779c25a9cdc5489`; the checkout, branch, HEAD, staged/index preservation, file hashes and before/after status were not directly observed by this reviewer.

Codex reported the complete task diff at SHA-256 `82c46f0d8574343dd94d52aa2642109a9f0b06558c4664b2bbfc62c40b34a460`. This hash was not recomputed because the raw diff file was not made available as a file artifact here. Static review is therefore limited to the pasted patch text, not byte-level certification of the full diff or direct inspection of the Windows worktree.

Codex reports `git diff --check=0`, with LF/CRLF conversion warnings. Tests, build, runtime, MCP, real transport and protected reads were not run. This receipt does not claim otherwise.

## 2. Narrow source-delta adjudication

### `read_authorization.py`

The visible delta requires `type(mandate.revoked) is bool` and then requires `mandate.revoked is False`; malformed falsy values therefore cannot pass this check. The former truthiness-only condition is removed. This is a reasonable fail-closed correction at the reviewed source boundary.

### `test_read_authorization.py`

The visible tests cover exact `False`, exact `True`, and falsy non-booleans `0`, `""`, `None`, and `[]`. They are test-authored evidence only; they have not been executed. The positive synthetic-chain test does not establish independent authority or authorize production reads.

### `github_owner_merge_bootstrap.py`

The visible delta changes `MANIFEST_SCHEMA_VERSION` from 1 to 2, explicitly requires an exact integer schema version, rejects unsupported versions with `MANIFEST_SCHEMA_VERSION_UNSUPPORTED`, and then validates the exact schema and challenge binding. This reconciles the required `server_id` and `issuer_id` additions with the in-source schema version.

The candidate report states that only the candidate's module and tests were searched for consumers. It does not establish the absence of external consumers or deployed v1 manifests. No compatibility fallback was added; version mismatch remains a fail-closed outcome.

### `test_github_owner_merge_bootstrap.py`

The visible tests assert that `expected_manifest()` uses version 2 and carries `server_id`/`issuer_id`, and that a historical v1 shape is rejected with the explicit unsupported-version code. This is suitable focused source coverage, not proof of runtime behavior.

### `test_mcp_server.py`

The visible parametrized test covers `read_repo_file` and `list_repo_directory`, supplies a synthetic `ALLOW` with an empty canonical target, and requires the exact reason `AUTHORITY_TARGET_INVALID`. The forbidden-reader sentinel should fail the test if either read helper is reached. It has not been executed.

## 3. Blocking boundary that remains open

The same-object invariant was not implemented. The reviewed report identifies that the resolver supplies a canonical string while the helper receives and independently resolves the original relative path. The authorization result is therefore not proven to identify the exact filesystem object consumed by the reader. The existing deny-only guard remains necessary; synthetic `ALLOW`, test fixtures or extra schema fields cannot substitute for a trustworthy handle-based contract.

No qualifying independent root, Owner-to-Windows principal binding, protected issuer credential/process/IPC boundary, or exact-target G3 binding was established by this remediation. Authority assets remain `UNKNOWN; NOT_INSPECTED`, not absent.

## 4. Final disposition

```text
TASK_RESULT=BOUNDED_SOURCE_ORGAN_REMEDIATION_CANDIDATE_ONLY; OWNER/CODEX_REPORTED
STATIC_REVIEW=PASS_WITH_NOTES_FOR_PASTED_PATCH_TEXT_ONLY
RAW_DIFF_SHA256=REPORTED_NOT_RECOMPUTED
LOCAL_CHECKOUT=OWNER_REPORTED; NOT_DIRECTLY_OBSERVED
SOURCE_DEFECTS_REPORTED_CORRECTED=MANDATE_REVOKED_STRICT_BOOL; MANIFEST_SCHEMA_VERSION_2; AUTHORITY_TARGET_INVALID_TEST
SOURCE_TESTS=AUTHORED; NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
SAME_OBJECT_BINDING=NOT_ESTABLISHED; DENY_ONLY
PROTECTED_READS=FAIL_CLOSED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=WAIT_FOR_GENUINELY_NEW_INDEPENDENT_ROOT_AND_AUTHENTICATED_OWNER_ISSUER_OS_BOUNDARY_EVIDENCE
```

The bounded source task is terminal for the evidence and permissions available. Do not repeat the whole-candidate review or start another source-only micro-patch loop. Reopen only if genuinely new, independently verifiable root/mandate/Owner-host/protected-issuer/G3 evidence appears or a new explicit Owner decision changes the permitted scope.

## 5. Canonical routing

`CURRENT-STATE.md` remains the sole task router. This receipt becomes canonical only if its documentation-only pull request is merged and its presence is fetched back from live `main`. The PR contains documentation/history only; it does not publish the local product-source candidate or change product code.
