# M1F — focused CI runner startup blocker and current candidate status

- **Receipt ID:** `IABV_M1F_CI_RUNNER_STARTUP_BLOCKER_RECEIPT_2026-10-25`
- **Observed at:** `2026-10-25T20:32:28-05:00` (`America/Bogota`).
- **Repository:** `jhonf463r/Python`
- **Live main:** `f00e3aa09b0efba10efab56735aca3c40fd71509`
- **Candidate PR:** [#531](https://github.com/jhonf463r/Python/pull/531), open draft, not merged.
- **Candidate branch:** `codex/iabv-m1f-authz-candidate-review-20261025`
- **Candidate head:** `928fd7c7924919d71d305504784a6a2bc1589c16`
- **Product scope:** fail-closed bridge-start dependency preflight and two candidate regression tests. No product source change was merged.

## 1. Candidate fetch-back

The candidate PR was fetched back from GitHub as `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`, with 13 source/test paths. Original M1F reconstruction had independently matched all 13 declared target Git blob IDs. The explicit follow-on patch changes two files:

| File | Fetched-back candidate blob |
|---|---|
| `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py` | `5c573dc9a7288d8b952cbf5c3002f3746d78356a` |
| `IABV_v1.5/tests/test_mcp_bridge_service.py` | `1ef26acd54a9ccf1caab0f6a1ac2294b2989e570` |

The other 11 files still match their original M1F target blob IDs.

The bridge-start preflight blocks startup when the coordinator is missing/unconfigured or cannot report mandatory requirements. It does not authenticate those providers or establish G1–G8. The production composition still constructs `ReadAuthorizationCoordinator.unconfigured()`; protected reads and bridge readiness remain blocked.

## 2. Focused workflow results

The intended focused workflow is `.github/workflows/iabv-authorization-focused-tests.yml`. It requests read-only contents permission, does not reference secrets, disables credential persistence on checkout, directs `IABV_DATA_DIR` to a runner-temporary path, and runs only:
- `IABV_v1.5/tests/test_mcp_bridge_service.py`
- `IABV_v1.5/tests/test_read_authorization.py`

The observed workflow runs were:

| Run ID | Head | GitHub conclusion | Jobs | Runner / steps |
|---|---|---|---:|---|
| `40253692813` | `27c079dac26a80451575728f8a01d997779020a6` | `failure` | 0 | none |
| `40253726614` | `4096f616c1aa3c7001ab54ff6259cd7f6c4bbfe5` | `failure` | 0 | none |
| `40253775893` | `5efb873ae1c63b951ab9d9337420c37d54dc0d53` | `failure` | 0 | none |
| `40253948337` | `f80a2caa845e647ec2799b608f1ea4b7eb183c7c` | `failure` | 0 | none |
| `40254119170` | `583aaf1c8582371c249891c81cfaabfdca039386` | `failure` | 0 | none |
| `40254285462` | `5bcab1366828d6e0f213be1c278c4c98549b15d5` | `failure` | 1 | runner name empty; 0 steps |
| `40254373973` | `928fd7c7924919d71d305504784a6a2bc1589c16` | `failure` | 1 | runner name empty; 0 steps |

Latest candidate run: [40254373973](https://github.com/jhonf463r/Python/actions/runs/40254373973).

A separate smoke workflow with no checkout, no third-party actions, no secrets and one `echo`/Python-version step was merged temporarily and run once:
- [Smoke run 40254520105](https://github.com/jhonf463r/Python/actions/runs/40254520105)
- Result: `failure`; one job, blank `runner_name`, zero steps.
- Its temporary workflow was removed via [PR #539](https://github.com/jhonf463r/Python/pull/539), merge commit `f00e3aa09b0efba10efab56735aca3c40fd71509`.

The empty `runner_name` and `steps=[]` are direct API observations. Downloading logs returned `BlobNotFound`; the reason GitHub failed to assign a runner could not be read from this session. Therefore the workflow conclusion is not evidence of a failing source assertion. Tests remain `NOT_RUN`, not `FAIL` and not `PASS`.

The local container also cannot resolve `github.com` or `raw.githubusercontent.com`; a local clone/alternate run was unavailable. No tests were executed locally, no secrets were read, and no Owner Windows runtime was invoked.

## 3. Current acceptance state

```text
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
APPROVED_WORKSPACE_ROOT_PROVIDER=NOT_WIRED_IN_CANDIDATE_COMPOSITION
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
SOURCE_CANDIDATE=PR_531_OPEN_DRAFT
BRIDGE_START_GUARD=PATCHED; FETCHBACK_VERIFIED
FOCUSED_TESTS=NOT_RUN
HOSTED_RUNNER=NOT_ASSIGNED_IN_OBSERVED_RUNS; ROOT_CAUSE=NOT_VERIFIED
NATIVE_WINDOWS_HANDLES_ACL=NOT_RUN
AUTHENTICATED_IPC=NOT_RUN
ROLLBACK_RESISTANCE=NOT_RUN
LIVE_MCP_TRANSPORT=NOT_RUN
NEXT_ACTION=PROVIDE_A_SUPPORTED_TEST_RUNNER_OR_RESTORE_GITHUB_HOSTED_RUNNER_EXECUTION; THEN_RUN_FOCUSED_TESTS
```

This receipt updates evidence provenance only. It does not close any prerequisite, authorize a positive read, or make the bridge ready.