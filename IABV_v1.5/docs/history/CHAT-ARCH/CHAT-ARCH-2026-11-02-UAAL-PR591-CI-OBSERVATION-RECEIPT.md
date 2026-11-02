# UAAL-D021 — PR #591 CI observation receipt

**Evidence date:** 2026-11-02  
**Purpose:** preserve dated workflow/run observations moved out of normative D021 §6F.2. Historical evidence only; not current route authority, not a test PASS, and not authorization to rerun or alter PR #591.

## Candidate binding

- Repository: jhonf463r/Python
- PR: #591 — https://github.com/jhonf463r/Python/pull/591
- Observed PR state: OPEN, DRAFT, not merged
- Base: main at a64f9e331ccbf13225ed3a5d945e16586e8756db
- Actual source branch: iabv/control-master-signal-bridge-r1-20261031-review
- Actual source HEAD: 01d4e70eac7afd80bde80a6844db784926f57c76
- Observed changed paths: 16
- Last metadata update at this observation: 2026-11-02T20:46:34Z

These refs describe only the observed PR #591 snapshot. Refresh them before any later decision; they do not identify PR #598 or the M1A protected-read bridge.

## Workflow revisions observed

1. Existing M1A-focused workflow on the PR #598 pinned base:
   - Path: .github/workflows/iabv-authorization-focused-tests.yml
   - Blob SHA: fc3ff9c6d04a16a391a19b7e0792d6f3c482995c
   - Its push trigger is restricted to the named M1A candidate branch. Its pull_request trigger targets main and requires a fixed set of M1A authorization source/test paths.
   - The documentation-only paths in PR #591 and PR #598 do not themselves satisfy that workflow's path list. This describes this workflow revision only, not all repository workflows.

2. PR #591 branch-only Control Master workflow:
   - Path: .github/workflows/iabv-control-master-focused-tests.yml
   - Blob SHA at the observed PR #591 HEAD: baadd228fe983dae73be88780775517e1ce9691e
   - It defines a pull_request workflow for Control Master source/test paths and uses a Windows runner/Python 3.11. It exists on PR #591's candidate tree, not canonical main.

## Run observations and limits

- Earlier runs 41518778170 and 41518883184 exposed a runner.temp job-environment scope error. The recorded correction moved IABV_DATA_DIR into the pytest-step environment.
- Runs 41519019291 and 41519008799 were previously observed as accepted events whose jobs did not start under a GitHub-reported account/platform restriction. They did not execute test steps; they were not test failures.
- A later aggregate-PR-path observation recorded that a D021-only commit still triggered the pull_request workflow because the PR's three-dot aggregate diff retained matching source/test/workflow paths. This falsified the assumption that the latest commit's changed paths alone determine a pull_request path-filter result.
- Latest refreshed PR metadata at this receipt: PR #591 remained OPEN/DRAFT at the base/head above. The connector returned one associated pull_request run:
  - Run ID: 41522096790
  - Name: IABV Control Master focused tests
  - Run status/conclusion: completed/failure
  - Job ID: 125540433553
  - Job status/conclusion: completed/failure
  - Returned job steps field: null
  - Combined commit status list: empty
- The latest job payload did not expose step-level execution evidence. The conclusion failure alone does not establish that pytest ran or that a test failed. Cause is NOT_ASSESSED; do not reinterpret it as a test failure or a passing test.

## Current interpretation

- Workflow applicability is event-, branch-, path- and workflow-revision-specific. Recompute it against the exact candidate and aggregate PR diff for each task.
- A workflow run, job conclusion, status-check list and actual test execution are different evidence objects. Retrieve job steps/logs and bind the test command to exact HEAD before claiming execution.
- Where a platform/account restriction is directly observed before job startup, classify ACTIONS_ACCOUNT_RESTRICTION and RUNNER_JOB_NOT_STARTED; do not infer this cause for a later run whose step/log evidence is unavailable.
- PR #591 remains a separate frozen candidate under its route. This receipt does not authorize a new workflow, branch synchronization, rebase, test dispatch, runner workaround, merge, runtime action or protected read.

## Source references

- PR metadata: https://api.github.com/repos/jhonf463r/Python/pulls/591
- PR #591 Actions run 41522096790: https://github.com/jhonf463r/Python/actions/runs/41522096790
- Existing M1A workflow: https://github.com/jhonf463r/Python/blob/56e4d8b11846a8d8f3cb8cda945e16586e8756db/.github/workflows/iabv-authorization-focused-tests.yml
- PR #591 branch workflow: https://github.com/jhonf463r/Python/blob/01d4e70eac7afd80bde80a6844db784926f57c76/.github/workflows/iabv-control-master-focused-tests.yml
- Official GitHub path-filter comparison semantics: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
