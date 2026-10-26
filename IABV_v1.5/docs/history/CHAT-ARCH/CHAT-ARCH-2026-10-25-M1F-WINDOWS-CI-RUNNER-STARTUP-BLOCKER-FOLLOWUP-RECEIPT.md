# M1F follow-up — Windows CI runner assignment blocker and safe test handoff

- **Receipt ID:** `IABV_M1F_WINDOWS_CI_RUNNER_BLOCKER_FOLLOWUP_2026-10-25`
- **Observed at:** `2026-10-25T20:48:13-05:00` (`America/Bogota`).
- **Live main at observation:** `7ddfe285b1a3267f9ef6f57f862cca78bc8438c2`.
- **Candidate PR:** [#531](https://github.com/jhonf463r/Python/pull/531), open draft, not merged.
- **Candidate branch/head:** `codex/iabv-m1f-authz-candidate-review-20261025` / `775ed09ba1d47e84edad6dbafea09264f2b1746b`.

## 1. Current candidate and static observations

The source PR has 13 modified paths and is kept separate from `main`. The two explicit bridge-start guard file blobs fetched back are:
- `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py`: `5c573dc9a7288d8b952cbf5c3002f3746d78356a`.
- `IABV_v1.5/tests/test_mcp_bridge_service.py`: `1ef26acd54a9ccf1caab0f6a1ac2294b2989e570`.

Directed static inspection of the exact current candidate established:
- The `ReplayConsumer.consume_once` protocol and the coordinator call share the same parameters: `challenge_id`, `nonce`, `decision_id`, `expires_at_epoch`, `now_epoch`.
- The permit minted after signature/replay checks carries the same open target object, target/root/policy binding identifiers, coordinator binding identifier, and coordinator-issued seal. The server guard requires those bindings and current permit validity.
- The protected read/list call sites open a target capability, pass that same object to the coordinator, and consume the same handle without reopening the text path.
- The bridge lifecycle checks mandatory provider presence before starting the server or tunnel.

These observations establish source structure only. They do not prove Windows ABI/kernel semantics, issuer-process authentication, durable anti-rollback replay, trusted-root custody, or actual execution. Production composition remains `ReadAuthorizationCoordinator.unconfigured()` and the approved root provider is absent.

## 2. Hosted CI evidence

Current workflow blob at the observed `main`: `fc3ff9c6d04a16a391a19b7e0792d6f3c482995c`. It is configured for `windows-latest`, uses Python 3.11, installs the project/dev dependencies with `pip install -e "IABV_v1.5[dev]"`, has read-only contents permission, disables checkout credential persistence, uses no secrets, sets `IABV_DATA_DIR` only at the pytest step to a fresh `runner.temp` child path, and runs the three focused suites:
1. `test_mcp_bridge_service.py`
2. `test_read_authorization.py`
3. `test_windows_handle_reader.py`

For candidate head `775ed09ba1d47e84edad6dbafea09264f2b1746b`:
- [Push run #40255921596](https://github.com/jhonf463r/Python/actions/runs/40255921596): failed before any step.
- [Pull-request run #40255925416](https://github.com/jhonf463r/Python/actions/runs/40255925416): failed before any step.
- Pull-request job: `runner_name=""`; `steps=[]`; downloaded log endpoint returned `BlobNotFound`.

The independent minimal no-checkout/no-secret smoke run [#40254520105](https://github.com/jhonf463r/Python/actions/runs/40254520105) also had a blank runner name and zero steps. The temporary workflow was removed from `main`. This supports the narrow statement `HOSTED_RUNNER_ASSIGNMENT_FAILED_BEFORE_FIRST_STEP`; it does not identify why GitHub failed to assign a runner.

The local tool container could not resolve `github.com` during `git ls-remote`. No clone or test execution occurred in this session. Thus `TESTS=NOT_RUN`, not PASS and not a source assertion FAIL.

## 3. Owner isolated Windows execution handoff

The following performs tests in a new temporary clone, not in the existing project checkout. It uses the exact candidate head above and keeps pytest's intent-learning data under a unique temporary directory. It does not start AppBootstrap, the MCP server, Cloudflared, an issuer process, or make a protected read.

Run from a disposable PowerShell terminal with Git and Python 3.11 installed:

```powershell
$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/jhonf463r/Python.git'
$CandidateSha = '775ed09ba1d47e84edad6dbafea09264f2b1746b'
$Work = Join-Path $env:TEMP ('IABV-M1F-CI-' + [guid]::NewGuid().ToString('N'))
$Data = Join-Path $env:TEMP ('IABV-M1F-TestData-' + [guid]::NewGuid().ToString('N'))
$Log = Join-Path $env:TEMP ('IABV-M1F-pytest-' + [guid]::NewGuid().ToString('N') + '.log')

git clone $RepoUrl $Work
if ($LASTEXITCODE -ne 0) { throw 'Clone failed; stop without using the original checkout.' }
Set-Location $Work
git fetch origin pull/531/head:refs/heads/iabv-m1f-candidate
if ($LASTEXITCODE -ne 0) { throw 'Could not fetch PR #531; stop.' }
git checkout --detach $CandidateSha
if ($LASTEXITCODE -ne 0) { throw 'Could not check out the exact candidate SHA; stop.' }
if ((git rev-parse HEAD).Trim() -ne $CandidateSha) { throw 'HEAD does not match the approved candidate SHA; stop.' }

py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed; stop.' }
$Py = Join-Path $Work '.venv\Scripts\python.exe'
& $Py -m pip install --disable-pip-version-check -e 'IABV_v1.5[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed; stop.' }

New-Item -ItemType Directory -Force -Path $Data | Out-Null
$env:PYTHONPATH = Join-Path $Work 'IABV_v1.5\src'
$env:IABV_DATA_DIR = $Data
& $Py -m pytest `
  IABV_v1.5/tests/test_mcp_bridge_service.py `
  IABV_v1.5/tests/test_read_authorization.py `
  IABV_v1.5/tests/test_windows_handle_reader.py -q 2>&1 | `
  Tee-Object -FilePath $Log
$TestExit = $LASTEXITCODE
"TEST_EXIT_CODE=$TestExit"
"TEST_CANDIDATE_SHA=$CandidateSha"
"TEST_LOG=$Log"
"TEST_DATA_DIR=$Data"
exit $TestExit
```

### Handling the outcome

- Capture the entire log plus the exact exit code. A nonzero exit must be reconciled by test name and traceback; do not silently retry or discard a failure.
- If the test process tries to construct `AppBootstrap`, access original user data, launch a server/tunnel, read secrets, or make a protected read, stop and record that unexpected path. The temporary data override is mandatory.
- Windows CNG-backed synthetic signature-chain tests are expected to run here rather than be skipped as on Linux. They are still synthetic contract tests; they cannot qualify a production root or authenticated IPC boundary.
- Do not mark native ACL, real process identity, durable rollback protection, or live MCP transport as verified from this suite.

## 4. Gate disposition

```text
CANDIDATE_HEAD=775ed09ba1d47e84edad6dbafea09264f2b1746b
BRIDGE_START_GUARD=PATCHED; FETCHBACK_VERIFIED
REPLAY_CONTRACT=STATICALLY_CONSISTENT
PERMIT_OBJECT_BINDING=STATICALLY_PRESENT
TESTS=NOT_RUN
HOSTED_RUNNER_ASSIGNMENT=FAILED_BEFORE_FIRST_STEP
HOSTED_FAILURE_ROOT_CAUSE=NOT_VERIFIED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
NEXT_ACTION=RUN_THREE_FOCUSED_SUITES_ON_EXACT_SHA_IN_ISOLATED_WINDOWS_CLONE; RECONCILE_TEST_LOG; CONTINUE_AUTHORITY_PROVISIONING_EVIDENCE
```

This handoff is prepared but not executed. It does not constitute a test result or close any prerequisite.