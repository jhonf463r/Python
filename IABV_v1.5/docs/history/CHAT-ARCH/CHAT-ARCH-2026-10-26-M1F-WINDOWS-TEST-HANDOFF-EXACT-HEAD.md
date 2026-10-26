# M1F Windows test handoff — exact PR #531 HEAD (2026-10-26)

**STATUS:** Prepared execution handoff; not executed by this record.
**Live main observed before this handoff:** `cc6b0666988ab4a9f01bacf8b9b211204febf1eb`.
**PR:** [#531](https://github.com/jhonf463r/Python/pull/531), `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`.
**Exact candidate HEAD:** `50cbd2b8b3d643d05726290c76ef13f85731949e`.
**Execution evidence:** candidate's latest observed workflow run [#40258140268](https://github.com/jhonf463r/Python/actions/runs/40258140268) reported `runner_id=0`, blank `runner_name` and `steps=[]`. The test suites did not run. Do not rerun that workflow blindly.

## Purpose and boundaries

Execute the existing canonical next action: run the three focused suites on an isolated Windows clone at the exact PR HEAD. This is test execution, not permission to merge PR #531, enable protected reads, start the bridge, launch Cloudflared, start IABV/AppBootstrap, authenticate an issuer, inspect secrets or access protected project data.

Do not use or modify the existing user checkout. Use a fresh disposable clone and venv, and set a fresh temporary `IABV_DATA_DIR` before pytest. Stop if a setup/import path unexpectedly attempts to read secrets, use the original checkout or launch an operational service.

## PowerShell procedure

Run in a disposable Windows PowerShell session with Git and Python 3.11 installed. It installs the declared project/dev dependencies into the disposable venv; it does not modify the original checkout.

```powershell
$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/jhonf463r/Python.git'
$CandidateSha = '50cbd2b8b3d643d05726290c76ef13f85731949e'
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
if ((git status --porcelain).Length -ne 0) { throw 'Fresh checkout is not clean; stop.' }

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
  IABV_v1.5/tests/test_windows_handle_reader.py -q 2>&1 |
  Tee-Object -FilePath $Log
$TestExit = $LASTEXITCODE
"TEST_EXIT_CODE=$TestExit"
"TEST_CANDIDATE_SHA=$CandidateSha"
"TEST_LOG=$Log"
"TEST_DATA_DIR=$Data"
exit $TestExit
```

## Required receipt

Return the complete test output or a retained log, exact exit code, exact tested SHA and environment facts. Distinguish:
- clone/dependency/setup failure (tests not run);
- test collection failure;
- assertion/test failure;
- all three suites actually executed and passed.

If any suite fails, preserve the traceback and classify the first causal failure; do not conceal it with a blind retry or patch loop. If the runner/host fails before steps, record `TESTS=NOT_RUN`, not PASS and not a product assertion failure.

Even a successful test run proves only these focused tests at this candidate SHA. It does not establish a trusted root, authenticated issuer, native production authorization, durable anti-rollback, G1/G2/G3, whole-organ acceptance or live protected-read safety.

## Required final state

```text
TEST_CANDIDATE_SHA=50cbd2b8b3d643d05726290c76ef13f85731949e
TESTS=NOT_RUN_UNTIL_EXECUTED
PR531=OPEN_DRAFT_UNMERGED
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```

This handoff is prepared, not executed. Revalidate live `main`, PR #531 and this exact HEAD immediately before the next execution; if the candidate HEAD changes, create a new handoff for that exact SHA rather than running these commands against an unreviewed target.
