# M1F — CI runner startup blocker and three-suite test handoff

- **Receipt ID:** `IABV_M1F_CI_RUNNER_STARTUP_BLOCKER_RECEIPT_2026-10-25`
- **Observed at:** `2026-10-25T20:38:19-05:00` (`America/Bogota`).
- **Main at route observation:** `0876e1ff5590523876d36114786cb43febfbb58b`
- **Candidate PR:** [#531](https://github.com/jhonf463r/Python/pull/531), open draft, not merged.
- **Candidate branch/head:** `codex/iabv-m1f-authz-candidate-review-20261025` / `928fd7c7924919d71d305504784a6a2bc1589c16`.

## 1. Candidate source disposition

The source candidate was independently reconstructed from M1F and its original 13 target Git blob IDs were verified. The subsequent bridge-start fail-closed correction amends two files, whose exact fetched-back blob IDs are:
- `mcp_bridge_service.py`: `5c573dc9a7288d8b952cbf5c3002f3746d78356a`
- `test_mcp_bridge_service.py`: `1ef26acd54a9ccf1caab0f6a1ac2294b2989e570`

The other 11 files remain identical to their original target blobs. The preflight prevents the current unconfigured coordinator from starting the MCP server/tunnel. It checks dependency presence only; it is not an authorization certificate or formal G1–G8 acceptance.

## 2. Hosted CI runner evidence

The focused workflow runs seven observed attempts across initial workflow creation and its configuration fixes. Each ended before test steps started. The latest candidate attempt was [40254373973](https://github.com/jhonf463r/Python/actions/runs/40254373973): the Jobs API showed one `focused-candidate-tests` job with a blank `runner_name` and zero steps. The no-checkout/no-secrets one-step smoke attempt [40254520105](https://github.com/jhonf463r/Python/actions/runs/40254520105) also failed with a blank runner name and no steps. The temporary smoke workflow was removed from `main` using PR #539.

The direct workflow-log endpoint returned `BlobNotFound`. The exact GitHub-side reason for not assigning a runner could not be determined. Therefore:
- `TESTS=NOT_RUN` — not PASS and not source assertion FAIL.
- Hosted runner start failure is observed; its root cause is `NOT_VERIFIED`.
- This session's local container failed DNS resolution for `github.com` and `raw.githubusercontent.com`; no local repository clone or local tests ran.

## 3. Revised focused suite contract

The workflow is being updated to run exactly these suites on a supported hosted or Owner-provided isolated runner:
1. `IABV_v1.5/tests/test_mcp_bridge_service.py`
2. `IABV_v1.5/tests/test_read_authorization.py`
3. `IABV_v1.5/tests/test_windows_handle_reader.py`

The workflow uses a `pull_request` trigger filtered to the candidate source/test paths and a `push` trigger for the dedicated candidate branch. It grants only `contents: read`, persists no checkout credentials, references no secrets, and sets `IABV_DATA_DIR` to `runner.temp` at the pytest step so the shared autouse fixture writes only into that temporary data directory. The workflow-only path was removed from the `pull_request.paths` list so a workflow-maintenance PR does not run candidate test modules against a branch where those modules are not present.

### Safe fallback for the Owner's isolated Windows runner

If GitHub-hosted runner assignment remains unavailable, use a *new temporary clone*, not the existing local checkout, and keep all test data under a new temporary directory. The focused test import path was statically inspected: `conftest.py` imports the intent-learning singleton, which reads its data path from `IABV_DATA_DIR`; setting that variable before pytest is essential. The three suites do not directly import `AppBootstrap` or invoke `_auto_load_secrets()`. The complete transitive import graph has not been executed in this session, so monitor the test process and stop if an unexpected app bootstrap or secret-load path is reached.

PowerShell handoff (run in a disposable terminal with Git/Python 3.11 already available; do not run from or alter the original project checkout):

```powershell
$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/jhonf463r/Python.git'
$Work = Join-Path $env:TEMP ('IABV-M1F-CI-' + [guid]::NewGuid().ToString('N'))
$Data = Join-Path $env:TEMP ('IABV-M1F-TestData-' + [guid]::NewGuid().ToString('N'))
git clone $RepoUrl $Work
if ($LASTEXITCODE -ne 0) { throw 'Clone failed; stop without fallback to the original checkout.' }
Set-Location $Work
git fetch origin pull/531/head:refs/heads/iabv-m1f-candidate
if ($LASTEXITCODE -ne 0) { throw 'Could not fetch PR #531; stop.' }
git checkout --detach 928fd7c7924919d71d305504784a6a2bc1589c16
if ($LASTEXITCODE -ne 0) { throw 'Candidate SHA mismatch; stop.' }
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed; stop.' }
$Py = Join-Path $Work '.venv\Scripts\python.exe'
& $Py -m pip install --disable-pip-version-check 'pytest>=8,<9' 'pydantic>=2.7,<3' 'httpx>=0.27,<1'
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed; stop.' }
New-Item -ItemType Directory -Force -Path $Data | Out-Null
$env:PYTHONPATH = Join-Path $Work 'IABV_v1.5\src'
$env:IABV_DATA_DIR = $Data
& $Py -m pytest IABV_v1.5/tests/test_mcp_bridge_service.py IABV_v1.5/tests/test_read_authorization.py IABV_v1.5/tests/test_windows_handle_reader.py -q
$TestExit = $LASTEXITCODE
"TEST_EXIT_CODE=$TestExit"
"TEST_DATA_DIR=$Data"
"TEST_CANDIDATE_SHA=928fd7c7924919d71d305504784a6a2bc1589c16"
exit $TestExit
```

This is a test handoff, not an executed result. It uses a clean clone, an exact candidate SHA and isolated test-data location. It does not launch the application, MCP server, tunnel, protected reads or issuer. Preserve the full test log and exact exit code; review skipped tests separately. Native Windows ACL and true production IPC validation remain separate gates.

## 4. Unchanged acceptance state

```text
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
TESTS=NOT_RUN
NATIVE_WINDOWS_HANDLES_ACL=NOT_RUN
AUTHENTICATED_IPC=NOT_RUN
ROLLBACK_RESISTANCE=NOT_RUN
LIVE_MCP_TRANSPORT=NOT_RUN
NEXT_ACTION=RUN_THREE_FOCUSED_SUITES_ON_SUPPORTED_RUNNER; THEN ADJUDICATE RESULTS; CONTINUE_AUTHORITY_EVIDENCE_ROUTE
```

This receipt records an exact test route and evidence limit; it does not close any implementation prerequisite or enable the bridge.