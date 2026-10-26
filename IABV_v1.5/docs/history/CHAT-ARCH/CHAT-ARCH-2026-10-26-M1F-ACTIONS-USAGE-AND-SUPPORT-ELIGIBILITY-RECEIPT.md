# M1F — GitHub Actions usage diagnosis and support route receipt

Date: 2026-10-26  
Task: `M1F_GITHUB_ACTIONS_USAGE_DIAGNOSIS_AND_SUPPORT_ROUTE_RECONCILIATION_20261026`  
Scope: Read-only infrastructure diagnosis, support eligibility discovery, and canonical continuity writeback.

## Executive result

The usage/budget hypothesis remains `UNKNOWN`. Codex's authorized read-only command

```text
gh api repos/jhonf463r/Python/actions/billing/usage --jq '{total_minutes_used,included_minutes}'
```

returned HTTP 404 and produced no minute values. This does not establish that Actions usage is blocked or unblocked. Do not try alternate billing endpoints, inspect payment details, change budgets, or repeat the same query unless materially new authorized access evidence becomes available.

The next route is support escalation through the available free channel. The authenticated GitHub Support portal was inspected with the TinyFish browser profile. It identified the signed-in account as personal GitHub Free and displayed `Technical support not included`; GitHub Actions was not listed as a standalone product category. Copilot in GitHub Support was visible as an informational option, but an attempt to start a browser-driven Copilot query was blocked before it was sent, so there is no Copilot response. No support ticket was sent and no public Community post was published.

## Live repository and run evidence

Read-only preflight immediately before this documentation writeback:

- `main` before writeback: `98615768b9ecff77ecfe3418bb39a8ece9f53e07`.
- PR #531: `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`.
- Candidate HEAD: `50cbd2b8b3d643d05726290c76ef13f85731949e`.
- Diagnostic run: [40386434070](https://github.com/jhonf463r/Python/actions/runs/40386434070).
- Current run metadata fetch confirmed `conclusion=startup_failure`, `event=push`, `workflow_id=397336571`, `path=BuildFailed`, empty workflow name, and diagnostic head `8b03ac4bb147db39efb23fa6e02d256ec41e5f2e`.
- A live Jobs API read returned `jobs=[]`. No test step ran.
- The earlier Codex report states that a direct workflow-ID read returned `state=deleted`, with workflow created/updated at `2026-10-26T17:14:54Z), before the failing run at `2026-10-26T19:24:19Z`. The current GitHub connector rejected a re-fetch of that workflow endpoint, so the deleted-state detail remains Codex-reported rather than independently re-established by this writer.
- Codex previously reported `actions/permissions: enabled=true` and `allowed_actions=all`. Those repository-level settings do not establish the state of account/organization controls, usage limits, concurrency, or hosted-runner capacity.
- Related pre-step runs reported earlier: `40258140268`, `40258135717`, and `40257696172`. These are infrastructure observations, not test failures.

## Support eligibility and attempted contact

The authenticated portal inspection reported:

- Account plan shown by the portal: personal GitHub Free.
- Direct technical support: not included for this account's observed plan.
- GitHub Actions: not exposed as a standalone contact category.
- Copilot in GitHub Support: offered for information-only help; not guaranteed to identify backend causes or alter settings.

A browser attempt to submit the diagnostic question to Copilot did not execute and produced no Copilot answer. No support ticket was sent. No public post was published.

## Evidence-led diagnosis

Confirmed:

1. The run exists and completed as `startup_failure`.
2. The Jobs API returns zero jobs for run `40386434070`.
3. The run metadata points to workflow ID `397336571`, path `BuildFailed`, with an empty name.
4. Codex's usage query returned HTTP 404 without usage figures.
5. The support portal does not offer direct technical support for the observed Free-plan account.

Not confirmed:

- Whether minutes, budgets, concurrency, organization/account policy, or hosted-runner availability are blocking execution.
- Why workflow metadata was associated with a `BuildFailed`/deleted record.
- Whether a GitHub backend/dispatch defect caused the run.
- Any causal relation to a prior GitHub Status incident.

Canonical decision:

```text
ROOT_CAUSE=UNKNOWN
ACTIONS_USAGE_BLOCK=UNKNOWN
TESTS=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
CAUSAL_REUSE=NOT_ESTABLISHED
ALGORITHM_LEARNED=NOT_PROVEN
```

## Next action — no repeated experiments

Prepare a sanitized question for GitHub Community Discussions in the Actions category, the free route identified by the Support portal. Because this is a public venue, publication requires explicit Owner authorization. Until that authorization is given:

- Do not publish the draft below.
- Do not disclose the private repository name, exact run URL, branch name, commit SHA, account identifier, source, logs, secrets, or protected data.
- Do not rerun workflows/tests, create branches, modify the candidate, alter Actions settings/budgets, or merge PR #531.

### Sanitized public-draft proposal (prepared, NOT published)

**Title:** GitHub Actions workflow ends in startup_failure before job creation

**Body:**

> I'm seeing a GitHub Actions startup issue in a private repository. A workflow run completes with conclusion `startup_failure`, and the Jobs API returns an empty list. There is no job ID, runner name, step record, or downloadable job log. In the run metadata, the workflow association has an empty workflow name and a path shown as `BuildFailed`; a prior read reported the associated workflow record as deleted.
>
> Repository-level Actions settings were previously checked through an authenticated read-only session and reported as enabled with all actions allowed. A read-only query to the repository Actions usage endpoint returned HTTP 404 and no usage values, so usage/budget status is unknown—not confirmed blocked or unblocked. Related hosted Windows and Ubuntu runs also stopped before executing steps. No test suite ran, and no further runs have been attempted after this diagnosis.
>
> Which documented troubleshooting checks are appropriate for a `startup_failure` with zero jobs and no job logs? Is there a supported diagnostic path for an unexpected workflow metadata/dispatch state in a private repository?

This is a draft only. It deliberately omits private repository identifiers and exact run references. If Community maintainers need correlation IDs, request a safe/private follow-up route rather than posting them publicly.

## Canonical next-action key

```text
LAST_TERMINAL_TASK=M1F_GITHUB_ACTIONS_USAGE_DIAGNOSIS_AND_SUPPORT_ROUTE_RECONCILIATION_20261026
LAST_TERMINAL_RESULT=USAGE_QUERY_HTTP_404_NO_VALUES; SUPPORT_FREE_PLAN_TECHNICAL_SUPPORT_NOT_INCLUDED
ACTIONS_USAGE_BLOCK=UNKNOWN
ROOT_CAUSE=UNKNOWN
SUPPORT_TICKET=NOT_SENT
COPILOT_SUPPORT_QUERY=NOT_SENT; NO_RESPONSE
COMMUNITY_POST=NOT_PUBLISHED; OWNER_AUTHORIZATION_REQUIRED
PR531=OPEN_DRAFT_UNMERGED
CANDIDATE_HEAD=50cbd2b8b3d643d05726290c76ef13f85731949e
TESTS=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=OBTAIN_EXPLICIT_OWNER_AUTHORIZATION_TO_PUBLISH_SANITIZED_GITHUB_COMMUNITY_ACTIONS_DISCUSSION
```

This receipt records project continuity, not model-weight training and not proof of algorithmic learning. Future agents must fetch this receipt and the updated `CURRENT-STATE.md` before selecting a new action.
