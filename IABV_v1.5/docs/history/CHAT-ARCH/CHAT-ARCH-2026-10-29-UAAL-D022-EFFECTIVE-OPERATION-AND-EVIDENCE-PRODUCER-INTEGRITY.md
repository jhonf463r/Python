# UAAL-D022 — Effective Operation Semantics and Evidence-Producer Integrity

**Date:** 2026-10-29
**Root:** `UAAL-ROOT-001`
**Parents:** `UAAL-D019` — Space-Time Anti-Loop and First-Open Causal Frontier; `UAAL-D020` — Verified Progress Utility and Cross-AI Memory Activation; `UAAL-D021` — Route Truth, Artifact Identity, and Verified-Progress Selection
**Status:** `PROPOSED_DOCUMENT_METHOD; NOT_CANONICAL_UNTIL_INTEGRATED; RUNTIME_ENFORCEMENT_AND_LATER_CAUSAL_REUSE_NOT_PROVEN`

## 1. Why this delta exists

The 2026-10-29 M1A GitHub CLI review exposed a general gap between *declared intent* and the *effective operation produced by a real adapter*:

- The adapter was described as read-only, but supplying `gh api -f key=value` changes the default HTTP method to POST unless `--method GET` is explicitly fixed.
- The request destination depended on inherited `GH_HOST` unless the canonical host was explicitly pinned.
- The internally validated `/repos/...` path was not the correct command-line endpoint form for the Windows target because `gh api` expects the leading slash omitted.
- Tests used fake API clients and verified the semantic core, but did not initially exercise the exact argv/environment contract that the real adapter constructs.

These were not merely formatting problems. Hidden CLI defaults, environment variables and platform-specific path rules can change the operation that produces evidence. That evidence is only useful if the effective method, destination and producer identity match the claimed operation.

## 2. Universal invariant

**Declared intent is not effective behavior.** A claim such as READ_ONLY, CANONICAL_HOST, VERIFIED_BINARY, or NO_SIDE_EFFECTS must be derived from the exact operation that will execute, including tool defaults, argument ordering, environment, path normalization, executable identity and failure behavior.

For every security-relevant adapter, model the effective operation as:

`OP = (principal, executable_identity, argv, method, destination, environment, endpoint, credential_source, expected_response)`

The operation is admissible only when all security-significant fields are fixed by trusted policy or validated inputs, not left to caller control or hidden defaults.

## 3. D022 algorithm — contract-to-operation reconciliation

Apply before admitting an adapter into a trust or authorization path.

### Gate A — declare the claim and its proof target

1. State the intended operation precisely: e.g. `HTTPS GET to github.com/repos/{owner}/{repo}/...`.
2. State the producer whose output will be used as evidence, its executable identity and the exact result expected.
3. Separate read-only metadata access from enrollment, protected reads, token creation, writes, publication and runtime activation.

### Gate B — resolve effective semantics

1. Inspect the real adapter API/CLI documentation or implementation for defaults activated by every argument.
2. Treat parameters that implicitly change method, endpoint, host, auth mode, shell, working directory or interactive behavior as security-relevant.
3. Make the required method and destination explicit in the generated invocation. Do not assume a path prefix or a human-readable label controls the actual destination.
4. Resolve platform-specific endpoint/path forms before execution; normalize only after validating the internal canonical form.
5. Apply trusted destination settings to both explicit command arguments and environment variables where the tool recognizes both.

### Gate C — bind producer and artifact

1. Pin the executable identity with the approved trust policy; for this M1A candidate, that means Authenticode `Valid`, the Owner-approved signer thumbprint and exact SHA-256.
2. Verify the same opened object that is hashed, and hold the handle across process creation when supported by the platform's sharing semantics.
3. Treat the resulting guarantee narrowly: it can reduce user-mode substitution, but does not prove repository/workflow build provenance or defend against every privileged actor.
4. Never let the API caller inject an arbitrary client, runner, executable path, verifier, policy or destination into a production trust path.

### Gate D — test the effective invocation contract

Synthetic tests must inspect the exact generated argv and child environment, not only fake the underlying HTTP response. At minimum assert:

- exact executable and endpoint;
- explicit expected method and canonical host;
- no caller-supplied parameter can override method or destination;
- no leading-slash or other platform-invalid endpoint leaks into argv;
- the child environment pins recognized destination variables and disables interactive prompts when a non-interactive security path is required;
- any verifier/policy/path/hash error causes zero subprocess/API calls;
- the pinned file handle stays open across the process-creation boundary.

Synthetic tests prove the tested contract with the doubles supplied. They do not prove that the real CLI ran, that credentials worked, that a private fetch-back succeeded, or that G1/G2/G3 are established.

### Gate E — preserve the evidence ladder

Keep these outcomes separate:

`SOURCE_STATIC_REVIEW` → `SYNTHETIC_TESTS` → `NATIVE_VERIFIER_RESULT` → `EXACT_HEAD_TEST_RECEIPT` → `AUTHENTICATED_FETCHBACK` → `AUTHORITY_DECISION` → `OPERATIONAL_ACTIVATION`

No result may skip a stage. A test report for parent commit N is not a test result for changed head N+1. An Actions `startup_failure` with no test jobs is not test evidence. A branch publication is not canonical integration. A successful signer check is not proof of build workflow provenance.

### Gate F — causal advance and anti-loop

When an independent review finds a defect:
1. bind it to the exact head and affected lines;
2. express the hidden default/condition and the counterexample;
3. predict the observable that would prove the repair;
4. patch only the implicated boundary and add a test for the real invocation contract;
5. verify the new live head and source delta;
6. do not repeat the prior test result as evidence for the new head;
7. after closure, route to the next dependency rather than reopening a fixed issue without new evidence.

A changed commit creates a new exact-head proof obligation; it does not automatically invalidate unrelated verified claims or authorize a broader task.

## 4. Acceptance checks for this method

1. A read-only API adapter with parameters but no explicit GET is rejected by review.
2. An environment-selected host is rejected unless the canonical host is fixed by policy.
3. A Windows-incompatible leading-slash endpoint is caught by synthetic argv assertions.
4. Injected method, hostname, arbitrary runner or alternate executable cannot override trusted policy.
5. Every error before invocation produces zero process calls.
6. Tests and hashes are tied to the exact commit they claim to validate.
7. Branch/PR evidence is not promoted to canonical main without authorized merge and fetch-back.
8. A source review, test report, native verification and private fetch-back remain distinct evidence classes.

## 5. M1A application and limits

The reviewed change from `c8177ea205a7046557b6f2fbaaf13c62b8f8aa77` to `3d29c0c0f4af657a889c44198d46fa59f07f021a` addresses three source-level request-contract findings: explicit `--method GET`, fixed `--hostname github.com` plus a pinned `GH_HOST`, and removal of the leading slash after internal path validation. This statement is based on exact remote source diff inspection, not a local test run or real CLI call.

For the current candidate, the latest focused code has been statically reviewed for these three fixes. The earlier `50 passed` report was for the parent head `c8177ea...`, not the new head `3d29c0c...`; therefore exact-head test execution is still `NOT_VERIFIED` until an exact-revision receipt is returned. Actions `startup_failure` contributes no successful test evidence.

The route also identified one small non-interactive hardening item: set `GH_PROMPT_DISABLED=1` and `GIT_TERMINAL_PROMPT=0` in the per-child environment, then assert those values synthetically. No `gh.exe` invocation or fetch-back is authorized by this method delta.

## 6. Invariants

```text
OWNER_TRUST_POLICY=APPROVED_FOR_EXACT_CANDIDATE_POLICY
GITHUB_CLIENT_PROVENANCE=FAIL_CLOSED_UNTIL_CANDIDATE_REVIEW
FETCHBACK=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_BOOTSTRAP=FALSE
AUTOMATIC_FOLLOW_ON=FALSE
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\\Python=DO_NOT_TOUCH
```

**Routing boundary:** UAAL-D022 is a proposed method, not canon until authorized integration/fetch-back. `CURRENT-STATE.md` remains the sole route authority. A single application does not prove `LATER_CAUSAL_REUSE`; runtime enforcement remains unproven.
