# Owner decision receipt — one integrated fail-closed authorization-organ completion candidate

- Date: 2026-10-25, America/Bogota.
- Decision provenance: explicit Owner message in the current conversation reiterating the project objective: finish the authorization organ properly, use the accumulated work, and stop letting stale wait states divert the work.
- Canonical base before this documentation transition: `main=e9a51a58723a48664119bdbbcb02222a6c92edaa`.
- Prior terminal result: `NO_NEW_EVIDENCE_RECOVERABLE_FROM_EXISTING_SESSION_ARTIFACTS`, reported by Codex in the current conversation.
- Prior terminal source result remains: `BLOCKED_APPROVED_WORKSPACE_ROOT_PROVIDER_ABSENT`, reported by Codex; the local source state was not independently inspected in this ChatGPT session.
- Decision: **AUTHORIZED — exactly one integrated, isolated source candidate for fail-closed authorization-organ completion**, with focused test authoring, execution against synthetic temporary fixtures, and local candidate build/checks.
- Task ID: `M1A_G1_INTEGRATED_FAIL_CLOSED_AUTHORIZATION_ORGAN_COMPLETION_20261025`.

## 1. Why this is a new route rather than a repeat

The newest evidence-recovery task returned no additional recoverable artifact. It does not answer the implementation question and must not be repeated. The prior G3 attempt stopped at the missing approved-workspace-root provider before creating a candidate or changing code. That is a terminal result for that earlier authorization, not a veto over this newly authorized and differently scoped integrated task.

The route-gate calibration rule applies: a missing root blocks a positive protected-read authorization; it does not prevent implementing a well-formed organ whose production path remains deny-only until a genuine root, mandate, issuer and host boundary are supplied. The task must not stop the entire source effort just because the positive-authority dependency is absent. It must separately classify source-correctable defects and external authority/platform prerequisites.

## 2. Exact task scope

Use the existing Windows Codex session and the already reported local candidate as context, but preserve its original checkout, index, staged/unstaged changes and untracked files byte-for-byte. Create a distinct isolated working candidate preserving the complete baseline before edits. Do not switch, clean, reset, stash or rewrite the original checkout.

Within that isolated candidate, complete the source-level authorization path across only the direct authorization-organ dependencies, based on the existing code and the prior R-01–R-08 static findings:

- align replay-consumer call/signature contracts and atomic consume-once semantics;
- carry the opened-target capability, target-binding identifier, approved-root/policy binding and coordinator issuance seal through the decision/permit/guard path;
- make file reading and directory enumeration consume the exact authorized object/handle, with no post-authorization path-based re-resolution or fallback;
- define explicit ownership, borrow/lifetime, close-once and error cleanup semantics;
- make revocation, manifest versioning, expected-registry identity and authority/dependency errors strict and fail-closed;
- wire the production composition transparently: missing real providers stay unavailable and deny; no fixture, mock, path string, caller-supplied key or self-asserted ID may stand in for real authority;
- address the source-level unsafe transport defaults relevant to this organ without launching or exposing a server;
- add and execute focused tests using only synthetic data and temporary test paths; run local static checks/build only in the isolated candidate, recording exact commands and results.

If some code-level contract cannot be completed without a real independent root or protected Windows/IPC provision, finish the separable source work, leave the live production route deny-only, and classify that dependency precisely. Do not return only the earlier root-provider blocker while leaving independent source defects untouched.

## 3. Non-negotiable exclusions

- No creation, enrollment, or invention of a trust root, mandate, Owner assertion, production credential/provider, issuer identity, registry, or authority material.
- No changes to system trust stores, registry, service installation/state, OS ACLs, accounts, credentials, TPM, Entra/Authenticator, persistent Windows state, or IPC/server provisioning.
- No access to protected repository contents or real protected reads; no live MCP handler invocation, real transport, server/bridge launch, public tunnel, deployment, or spending.
- No source diffs or candidate security changes published to this public repository. No staging, commit, push, or merge of product code.
- No modifications to the original checkout. No bypass if the isolated worktree, tests, or a supported local action are denied.

Testing permission is limited to candidate unit/source tests, build/static checks and native-handle tests against synthetic files in a disposable temporary directory. It does not authorize protected reads, production runtime, or a real service/transport.

## 4. Required acceptance evidence

Return one integrated candidate, not a chain of micro-patches. Report the exact checkout/path, repository, branch, base/HEAD, full pre-edit status and preservation hashes, changed paths, full exact diffs against the pre-edit baseline, per-file hashes and a per-requirement adjudication.

For R-01–R-08 separately classify:
- `SOURCE_CORRECTED_AND_TESTED_IN_CANDIDATE`
- `PARTIAL_SOURCE_CANDIDATE`
- `EXTERNAL_AUTHORITY_OR_PLATFORM_PREREQUISITE`
- `NOT_ESTABLISHED`

Give exact test/build/static-check commands, exit codes and outputs. Distinguish tests authored from tests run. Do not generate or publish a security bundle if the tool policy disallows it; record the exact boundary and do not try an alternate path to bypass the denial.

Retain:
```text
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED where not reached
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED until independently evidenced
G1=NOT_ESTABLISHED unless new admissible evidence supports a narrower claim
G2=NOT_ESTABLISHED unless new admissible evidence supports a narrower claim
G3_SAME_OBJECT=NOT_ESTABLISHED until exact-object behavior is supported by the actual candidate evidence
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY until all required gates are separately adjudicated
COST_POLICY=ZERO_BUDGET
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
```

Stop after this one task and return the complete terminal hand-back for independent review. This decision authorizes one candidate and its bounded tests only; it does not establish trust authority, release protected reads, adopt the candidate into main, or authorize a follow-on action.
