# Knowledge Delta — Route-Blockage Generalization, Authorization Drift, and All-or-Nothing Bias

- **Knowledge Delta ID:** `IABV_KD_2026-10-24_ROUTE_GATE_CALIBRATION`
- **Observed:** 2026-10-24, America/Bogota
- **Canonical baseline checked:** `main` at `2d2b25cb81f5acf1dc08afad081d4d4af922abcb`
- **Status:** documentation candidate on `docs/iabv-knowledge-delta-route-gate-calibration-20261024` until adopted on live `main` and fetched back
- **Scope:** coordinator reasoning, task routing, authorization reconciliation, and evidence classification
- **Non-effect:** this record does not change the technical route in `CURRENT-STATE.md`, establish a root, close G1–G3, authorize product implementation, or authorize reads/tests/runtime/transport/deployment/spend.

## 1. What failed in the reasoning

The observed failure was not simply that a trust-root review ended blocked. The coordinator did not reliably keep four distinct questions separate:

1. **What is the canonical project state?** Current routing says the qualifying independent root and bindings are not established, governance stays blocked, protected reads stay fail-closed, product implementation is not authorized, and automatic follow-on is false.
2. **What did a specific attempt prove?** A terminal static review failed to establish a qualifying non-circular root. That does not prove trust assets are absent.
3. **What can a particular route do?** A reader, executor, tool, local checkout, or artifact may be unavailable in one surface. That is a route/capability observation, not proof of global technical absence.
4. **What action is authorized now?** A technically possible action is not automatically an allowed action. Independent work still needs an existing permission or a new, bounded explicit authorization.

The coordinator over-generalized a gate-specific failure into project-wide paralysis, while a later proposed implementation prompt made the opposite error: it asked for source implementation without reconciling the canonical `IMPLEMENTATION=NOT_AUTHORIZED` field. Both errors come from not evaluating scope, dependency, and authorization separately before selecting the next step.

## 2. Case facts and provenance

- **DIRECT_GITHUB:** live `main` was fetched at `2d2b25cb81f5acf1dc08afad081d4d4af922abcb`; the five mandatory canonical front doors were read in order.
- **DIRECT_GITHUB:** the canonical route still says `ACTIVE_TASK=M1A_G1_WAIT_FOR_INDEPENDENT_ROOT_EVIDENCE`, `G1/G2/G3=NOT_ESTABLISHED`, `IMPLEMENTATION=NOT_AUTHORIZED`, `AUTOMATIC_FOLLOW_ON=FALSE`, and to maintain fail-closed pending pre-existing independent-root and mandate evidence.
- **OWNER_REPORTED:** a local-only candidate was described on branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, local HEAD `22042285ffef8f4af819e93b6d4283a936bcfde3`. The GitHub connector did not find that branch or commit on remote GitHub; this corroborates that the change is not canonical, but does not inspect the local working tree.
- **OWNER_REPORTED:** the candidate report described PEM format/base64 checking but no cryptographic signature verification; generated nonce/expiry but no persistent one-time replay consumption; no proven Owner-to-Windows principal binding, protected issuer process/ACL/IPC, or reader enforcement; and tests written but not run. These are reported candidate properties, not independently executed findings.
- **Coordinator error:** the subsequent task prompt requested implementation without reconciling the canonical implementation authorization field. This document explicitly records that as an instruction-routing defect.
- **Not established:** no candidate source behavior, signature validation, replay resistance, OS isolation, protected-reader enforcement, tests, or runtime behavior is treated as verified here.

## 3. Corrected invariant: localize the blocker; never dilute authorization

Use this distinction in every future task:

| Blocker class | What it means | What it does not mean | Safe routing consequence |
|---|---|---|---|
| `AUTHORITY_GATE` | Authority, custodian, mandate, or required identity binding is unestablished. | That assets do not exist, or that every possible task is technically impossible. | Keep protected capability and gate claims blocked. Do not fabricate authority. Work elsewhere only if independently authorized and genuinely useful. |
| `ROUTE_SURFACE_MISMATCH` | The required action is unavailable in the current interface or actor. | Global absence of a file, service, or capability. | Record the exact unavailable route. Do not retry a denied reader or use another route to bypass the denial. Consider another route only if policy permits it and it is not a circumvention. |
| `ACTION_UNEXECUTABLE_NO_EVIDENCE` | The actor cannot perform or verify the requested operation with the current tool/permissions. | A successful or failed technical experiment. | Stop claiming execution; identify the exact missing capability and the closest authorized action. |
| `SOURCE_DEFECT` | Accessible source shows a missing or incorrect implementation mechanism. | Runtime confirmation of the defect or permission to modify code. | Static diagnosis may proceed only within scope; implementation requires authorization; tests/runtime require their own permissions. |
| `EVIDENCE_GAP` | Evidence needed to promote a claim/state is missing. | Proof that the claim is false. | Keep the state `UNKNOWN`, `NOT_ESTABLISHED`, `NOT_INSPECTED`, or `NOT_RUN` as appropriate. |
| `AUTHORIZATION_GAP` | Canonical state does not authorize the proposed action. | Permission implied by technical feasibility, a generic “proceed,” or an unrelated documentation request. | Do not execute or delegate the forbidden action. Ask for new authorization only when the Owner can genuinely change the permission and the route requires it. |

**Core rule:** a hard prerequisite for a protected operation blocks that operation. It does not automatically block documentation, evidence reconciliation, or another workstream; however, those workstreams must each fit the current canonical authorization. “Independent” is not a synonym for “authorized.”

## 4. Mandatory decision algorithm

Before proposing, delegating, or executing a step:

1. **Refresh authority:** fetch live `main`; read the five canonical files in their required order; record the exact `CURRENT-STATE.md` route and authorization fields.
2. **Bind action to state:** name the objective, the precise dependency edge, the action's scope, the performer/tool, and the expected evidence that would change state.
3. **Classify the blocker:** authority vs route/capability vs source defect vs evidence gap vs authorization gap. Do not use a vague label such as “blocked” without naming its object and scope.
4. **Check the negative inference:** ask “What does this result actually prove?” Explicitly reject `route unavailable → asset absent`, `signature valid → signer is authorized Owner`, `PR actor merged → Owner-to-Windows identity bound`, `code written → code executed`, and `tests authored → tests passed`.
5. **Reconcile authorization before handoff:** compare the task's proposed side effects against `IMPLEMENTATION`, `TESTS`, `BUILD`, `RUNTIME`, `REAL_TRANSPORT`, `CREDENTIAL_OR_APP_CREATION`, `PUBLIC_TUNNEL`, `COST_POLICY`, and merge/deployment rules in current state. Do not issue an executable prompt that contradicts those fields. A user's authorization applies only to the stated scope; documentation authorization does not imply product-code authorization.
6. **Choose one bounded action:** if allowed, choose the smallest action that creates discriminating evidence or closes a real dependency. If no safe action is authorized, state the precise missing authorization/evidence and stop—do not invent a work item just to look productive.
7. **Verify the transition:** record what actually happened, what was not run, the source revision, outputs, and what remains unresolved. A candidate branch/PR is not canonical.
8. **Persist and fetch back:** only an authorized and reviewed writeback becomes shared project knowledge after it is adopted on `main` and the exact live bytes/state are fetched back.

## 5. Specific trust-boundary lessons

- A cryptographic signature verification can prove that a signature validates under a public key and message, subject to the algorithm and implementation. It does **not** by itself prove the key belongs to the Owner, that the Owner is the relevant Windows principal, that the key holder has the required mandate, or that the request is bound to the exact MCP server and target.
- A GitHub PR merge actor is repository evidence. It is not a substitute for an independent Owner-to-Windows-principal binding or a protected local issuer.
- Nonce generation is not replay protection. Replay protection needs durable, atomic, one-time consumption and defined behavior for missing/corrupt/rolled-back state; these source claims still require tests and later runtime evidence before being promoted.
- A policy check in a bootstrap helper does not mediate a protected reader unless the reader's actual call path enforces the signed, bounded decision before opening/listing the target. A parallel helper alone does not close the enforcement gap.
- G1, G2 and G3 are separate requirements. A positive G1 candidate cannot imply publisher integrity/revocation (G2), canonical target resolution (G3), or close the eight implementation prerequisites.
- Do not bypass a denied reader. Keep the security boundary intact and make the next authorized step explicit.

## 6. Terminal result scope vs global status

A terminal result is terminal for the task, evidence set and authorization scope that produced it. It must not be silently reused as a conclusion about a broader claim.

Conversely, the coordinator must not use this principle to evade the current router: if `CURRENT-STATE.md` selects waiting and says automatic follow-on is false, the coordinator may not autonomously start unrelated technical work. Only a genuinely new qualifying evidence event or an explicit new Owner decision that changes scope can change the route. This is the balance that was missing: **do not globalize a narrow negative finding, and do not treat a narrow permission as blanket authorization.**

## 7. Required handoff fields when Codex returns

When the next Codex result is provided, do not restart broad research and do not assume its candidate is canonical. Evaluate the result against:

- exact destination/session, repository, branch, base SHA and HEAD;
- clean/dirty worktree and exact changed paths/blob hashes;
- source-diff claims tied to concrete code locations;
- which checks/tests were written vs actually run, exact command and exit/result if run;
- which network/runtime/credential/service/deployment effects actually occurred or were not run;
- cryptographic validation (not just PEM shape), challenge binding, durable replay consumption, rollback/corruption behavior, issuer process boundary and IPC authentication, revocation/expiry;
- enforcement on the protected reader before access, including exact server-resolved target and operation binding;
- G2/G3 behavior remaining fail-closed if either is absent;
- differences from the prior candidate, not just a new attempt number;
- authorization consistency with live `CURRENT-STATE.md`.

Do not mark any gate closed from source intent, a written test, an owner-pasted report, or a branch that is not canonical. Static review should examine the returned delta and exact evidence; do not rerun the entire history.

## 8. Current state and expected behavior

This knowledge delta is a coordinator-reasoning correction only. It does not change the current route:

```text
ACTIVE_TASK=M1A_G1_WAIT_FOR_INDEPENDENT_ROOT_EVIDENCE
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION=NOT_AUTHORIZED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_FAIL_CLOSED_PENDING_PREEXISTING_INDEPENDENT_ROOT_AND_MANDATE_EVIDENCE
```

The next user-supplied Codex result may be inspected for provenance, exact candidate state, and whether any action exceeded the current authorization. That narrow intake check must not automatically reopen the terminal G1 review, designate a new technical review target, or authorize implementation, tests, transport, or release. A fuller source review requires a scope that is allowed by the live router or a new explicit bounded Owner authorization; it must not be treated as canonical adoption. This document is a durable protocol/memory artifact; it does not automatically train model weights or change the running IABV algorithms.

## 9. Follow-up calibration — unconditional MCP denial is containment, not a positive authorization path (2026-10-24)

### Report provenance and remote verification

- **OWNER_REPORTED:** Codex reports candidate branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, local HEAD `9803a282760824eae630a27561f6aed6c4b6a6bd`, prior local HEAD `22042285ffef8f4af819e93b6d4283a936bcfde3`, clean tree, and no push/PR.
- **OWNER_REPORTED:** two files changed: `server.py` and `test_mcp_server.py`; source blobs reported as `fbce8d52ddc121033f5bb87bb92be2aee52da8c0` and `88b0a2a1570d7f5bfebcf09b850cd7db24640c65`. The earlier local-only verifier and tests are reported unchanged at blobs `cf58b6c08954dc0c3e2e3b8d6e9e240a1b4c3c72` and `0521a9da88853ea784fee8d4faced15c854a0899`.
- **DIRECT_GITHUB:** a search of remote branches did not find the stated candidate branch; the reported HEAD lookup returned no commit; PR search returned no PR. This corroborates non-publication, but does not inspect the local checkout or verify the pasted source claims.
- **OWNER_REPORTED:** the new server guard unconditionally denies `read_repo_file` and `list_repo_directory` before audit helpers; targeted tests were written but not run; only `git diff --check` passed. No build or runtime was observed.
- The candidate was based on `2d2b25cb81f5acf1dc08afad081d4d4af922abcb`. Live `main` subsequently advanced to `476273ade3c37d273c84322e68e09a48dc054594` through a documentation-only knowledge-calibration PR. Do not treat the candidate base as current main, and do not rebase/publish the local branch without a separately authorized task.

### Correct interpretation of the technical delta

If the report accurately describes the candidate source, the unconditional guards are **route-level containment** for those two MCP tool routes. They are not a functional positive authorization path and do not establish the requested vertical slice.

Use precise labels:

```text
MCP_READ_LIST_GUARD=OWNER_REPORTED_UNCONDITIONAL_DENY_BEFORE_AUDIT_HELPERS
SOURCE_INDEPENDENTLY_INSPECTED=FALSE
TARGETED_TESTS=WRITTEN; NOT_RUN
DIFF_CHECK=OWNER_REPORTED_PASS
BUILD=NOT_RUN
RUNTIME=NOT_RUN
PROTECTED_ISSUER=NOT_IMPLEMENTED
CRYPTOGRAPHIC_SIGNATURE_VERIFICATION=NOT_IMPLEMENTED
DURABLE_ATOMIC_ANTI_REPLAY=NOT_IMPLEMENTED
OWNER_TO_WINDOWS_PRINCIPAL_BINDING=NOT_ESTABLISHED
G2_CATALOG_INTEGRITY_REVOCATION=NOT_IMPLEMENTED
G3_VERSIONED_TARGET_RESOLVER=NOT_IMPLEMENTED
G1_G2_G3=NOT_ESTABLISHED
```

Do not describe the two guards as end-to-end security enforcement for the entire process: the report itself says the underlying helpers remain importable by in-process code and that only the named MCP routes are covered. Do not assume this containment should be removed; it remains a reported fail-closed behavior of the candidate, not independently verified canonical source.

### Reusable inference

- `unconditional deny` proves denial behavior only if source/tests/runtime evidence establish it; it does not prove that a legitimate authorized path exists.
- A deny-before-helper guard can reduce exposure through named entry points, but without a protected issuer and an authenticated, scoped decision it is a **kill switch / containment shim**, not an authorization architecture.
- Written tests remain unexecuted evidence. `git diff --check` checks patch hygiene, not program behavior or security properties.
- Adding source guards is a changed candidate, but does not supply the missing independent root, its mandate/custodian/channel, or Owner-to-principal / issuer-to-server bindings. It therefore does not satisfy the canonical condition for reopening the terminal G1 review.
- Do not issue another implementation prompt based on this report. Keep the local candidate unpromoted and the canonical route unchanged unless genuinely new independent root-and-mandate evidence arrives or the Owner explicitly authorizes a new, bounded scope.

This subsection is an intake and memory record of an Owner-supplied report. It does not certify the candidate, authorize source edits/tests/runtime/publishing, close any gate, or alter `CURRENT-STATE.md`.

## 10. Follow-up calibration — stale-route inertia after a new explicit Owner decision (2026-10-24)

### The joint-reasoning defect

The coordinator correctly treated `CURRENT-STATE.md` as the sole source of current routing, but then incorrectly treated its old `NEXT_ACTION` as immutable after the Owner explicitly changed the authorized work scope. That is a state-machine error, not evidence that the project has no next step.

Three different propositions were collapsed:

1. `ROOT_REVIEW_TERMINAL`: the reviewed evidence did not establish a qualifying independent trust root; that terminal result remains valid for the same evidence set.
2. `SOURCE_CONSTRUCTION_AUTHORIZATION`: the Owner can explicitly authorize a bounded implementation task without claiming the root already exists.
3. `CANONICAL_ROUTE_UPDATE`: the new decision must be captured in the current routing record, preserving the old terminal result as history and explicitly listing the new task's boundaries.

A new Owner directive changes permitted scope, not technical truth. It does not create authority assets, make the issuer safe, or close G1–G3. But the old terminal review and its old wait-state must not be repeated as though the new instruction never occurred.

### Correct state transition

```text
TERMINAL_ROOT_REVIEW=RETAIN_AS_HISTORICAL_RESULT
NEW_OWNER_DECISION=BOUNDED_SOURCE_CONSTRUCTION_AND_SOURCE_TEST_AUTHORING
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1_G2_G3=NOT_ESTABLISHED
SOURCE_IMPLEMENTATION=AUTHORIZED_WITH_EXPLICIT_BOUNDS
TEST_EXECUTION_BUILD_RUNTIME_TRANSPORT=NOT_AUTHORIZED
PROTECTED_READS=FAIL_CLOSED
NEXT_ACTION=CONTINUE_EXISTING_LOCAL_CANDIDATE_WITH_BOUNDED_SOURCE_WORK
```

This is a **proposed branch-level routing transition** until the changed state record is reviewed and adopted on live `main`. It does not declare the running bridge ready.

### Mandatory algorithm when the route and a new Owner instruction appear to conflict

1. Refresh `main` and read the five canonical front doors in order.
2. Parse the new Owner message as a decision event: exact scope, permitted effects, explicit exclusions, timestamp/provenance, and what technical facts it does not assert.
3. Do not use a historical terminal result or old `NEXT_ACTION` to silently erase that new decision. Preserve the result but scope it to the evidence reviewed.
4. Create a small additive route transition that places the new task at the top of `CURRENT-STATE.md`, links the decision receipt, and preserves old blocks as historical records. Do not rewrite or erase the audit trail.
5. If the state update cannot be performed in the current surface, label the result `ROUTE_SURFACE_MISMATCH` or `ACTION_UNEXECUTABLE_NO_EVIDENCE`; do not tell the Owner the technical route is impossible. Use the authorized repo checkout as the normal editing surface only when the Owner authorized that task, preserve candidate-only status, and return the diff for canonical review. Do not bypass a denied reader or credential boundary.
6. Only after the proposed transition's authorization fields match the Owner's exact scope, prepare the next work prompt. Do not include tests/build/runtime/transport/credential/OS changes unless separately authorized.
7. Keep source implementation, source test authoring, test execution, runtime validation, authority-root establishment, gate closure, and canonical adoption as different stages.

### The architectural insight

The root/mandate dependency blocks issuing a positive protected-read authorization; it does not block constructing a fail-closed authorization organ whose missing-root behavior is denial. The source task must implement the whole path without hard-coded success: real crypto verification, trust-anchor/mandate verification inputs, replay-safe challenge handling, issuer boundary, exact target binding, G2 policy/revocation, G3 resolver, and reader enforcement. Where a real root or OS isolation boundary is unavailable, the implementation must explicitly remain unable to authorize a read.

The Owner decision receipt is [bounded source implementation authorization](./CHAT-ARCH-2026-10-24-M1A-G1-owner-bounded-source-implementation-authorization.md). This section corrects routing behavior; it is not itself an implementation or a gate pass.



## 11. Follow-up calibration — transcript task versus live route (2026-10-24)

### Observed coordination risk

The supplied conversation ends with a detailed prompt for `M1A_G1_REGISTER_READ_AUTHORIZATION_IN_APPBOOTSTRAP`. Live `main`, however, already records that task as source-complete for routing purposes based on an `OWNER_REPORTED` Codex result, and selects `M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY` as the next task. The mismatch creates a predictable trap: following transcript chronology alone can reopen a completed composition edge, while following only the latest route without receiving the promised report can miss new evidence about the prior task.

Neither mistake is acceptable. The transcript identifies what a response may be answering; the live router identifies what task is currently next. Treat these as separate dimensions and reconcile both.

### Required Codex-result intake procedure

1. **Bind the result to a task ID.** Extract the exact `TASK=` and compare it with the prompt answered. Do not infer task identity solely from position in the chat or from a branch name.
2. **Refresh canonical authority.** Fetch live `refs/heads/main` and read `CURRENT-STATE.md` before choosing the next action. Commit SHAs recorded in previous prompts or reports are historical observations, not current aliases.
3. **Audit the reported candidate identity.** Compare repository, checkout, branch, HEAD before and after, current remote main, clean/dirty state, and staged versus unstaged diffs. Preserve the existing work; do not reset, clean, overwrite, or infer unchanged content from a reused branch name.
4. **Test the report against its original acceptance criteria.** For the AppBootstrap task, the discriminating edge was explicit registration/injection through `AppBootstrap → MCPBridgeService → FastMCPServerRunner → IABVMCPServer → read_repo_file/list_repo_directory`, with missing providers and composition failures staying DENY before resource helpers. Source location and diff evidence are required; class additions or self-reported completion alone do not establish this.
5. **Keep evidence categories separate.** State what was directly observed in GitHub, what Codex reports locally, what source was independently inspected, which tests were written, and which tests/build/runtime/transport were actually run. In the authorized candidate scope here, execution remains `NOT_AUTHORIZED; NOT_RUN`.
6. **Do not rewind routing by transcript order.** If the response belongs to the prior AppBootstrap task, intake it against that task, reconcile any new delta or contradiction, and then continue from the current bootstrap/issuer boundary route. Do not reissue AppBootstrap wiring or restart broad research unless the current canonical state and new evidence justify it.
7. **Do not promote technical claims by implication.** The AppBootstrap wiring report does not establish an independent trust root, Owner-to-Windows-principal binding, a protected issuer/IPC boundary, production G1/G2/G3 providers, or a positive protected-read path.

### State transition invariants

```text
TRANSCRIPT_LAST_PROMPT != CANONICAL_NEXT_ACTION_BY_DEFAULT
CODEX_RESULT_TASK_ID = EXPLICITLY_MATCHED
LIVE_MAIN = REFRESHED_BEFORE_ROUTE_DECISION
LOCAL_CANDIDATE_FACTS = OWNER_REPORTED_UNTIL_INDEPENDENTLY_INSPECTED
SUPERSEDED_TASK_RESULT = INTAKE_AND_RECONCILE; DO_NOT_REWIND_ROUTE
ACTIVE_TASK = M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY
OWNER_SOURCE_SCOPE = SOURCE_CODE_AND_SOURCE_TEST_AUTHORING_ONLY
TEST_EXECUTION_BUILD_RUNTIME_TRANSPORT = NOT_AUTHORIZED; NOT_RUN
G1_G2_G3 = NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES = 8; CLOSED = 0
READ_LIST = FAIL_CLOSED
GOVERNANCE = KEEP_BLOCKED
BRIDGE = BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON = FALSE
```

This calibration improves task-result intake and continuity only. It does not change the route, widen Owner authorization, certify local code, close a gate, or turn documentation into model-weight training. It supplements section 10's stale-route-inertia rule: section 10 handles a new Owner decision that changes scope; section 11 handles a new report that may refer to an older prompt while the current route has already advanced.


## 12. Follow-up calibration — Owner-controlled bootstrap boundary result intake (2026-10-24)

### Reported outcome and provenance

The Owner supplied a Codex report for `M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY` with `TASK_RESULT=SOURCE_CANDIDATE_ONLY`. It reports three existing paths changed and no new files:

- `github_owner_merge_bootstrap.py`, reported working-tree blob `97d0295028e9da203548f26e86f3c1f75bc303b1`;
- `test_github_owner_merge_bootstrap.py`, reported working-tree blob `1e32059a99091ccca4636b34ba00b80faeeecd9c`;
- candidate `CURRENT-STATE.md`, reported working-tree blob `b62b6e3728a18e156db8d52bc070ff97a601211b`.

The report says the local HEAD remained `6bc568e1c5a898afd65cc045c779c25a9cdc5489`, main at task time was `2cecd5e9b9e175584d65bbb1198a53bc2346d095`, and the branch diverged by 9 local commits and 4 remote commits, with overlapping local changes. No merge/rebase, test/build/runtime/MCP/transport or publication occurred. It reports seven staged paths retained, eleven unstaged paths at end, and no dependency changes. These are `OWNER_REPORTED`; GitHub did not find the candidate branch or HEAD, so it cannot inspect the local worktree or independently validate the blob claims. The exact diff was not attached to this intake.

### Correct interpretation

The report describes a useful narrowing of the boundary contract: `G1EnrollmentChallenge` binds `server_id` and `issuer_id`; typed verifier, credential-provider, challenge-store, trust-registry and boundary interfaces are present in source; source tests reportedly cover challenge bindings, expiry, Owner/issuer identity, server identity and policy version. However, the report expressly says that a real Owner assertion verifier, independent provisioned root, persistent challenge/replay store, protected trust registry, authenticated process/IPC and OS isolation do not exist. Validation against a public key supplied to a signature verifier does not authenticate the trustworthiness of that key. Therefore the result does not establish a usable positive authorization path or close G1/G2/G3.

Do not overstate the candidate as security-complete; do not dismiss the source-contract work as zero progress either. It advances the explicit contract and records exact missing dependencies, while leaving the actual trust and isolation boundary unimplemented. Tests are written but `NOT_RUN`; `git diff --check` (reported PASS) is patch hygiene only, not behavioral evidence.

### Next discriminating action

The bootstrap handoff's stop condition is targeted static review of the exact source delta. Therefore:

1. Obtain a read-only source-diff package from the same local Codex checkout, distinguishing `git diff --cached` (pre-existing staged work) from `git diff` (unstaged delta), with status, paths, before/after hashes and no staging/edits.
2. Have an independent reviewer inspect the exact three-path delta against the bounded handoff: challenge binding and validation, evidence/identity source, store interface truthfulness, trust-registry semantics, fail-closed behavior, and whether candidate `CURRENT-STATE.md` preserves chronology and gates.
3. Only after that review decide whether the candidate contract is source-correct within its scope or whether there is a specific source defect. If the boundary still requires disallowed enrollment/credential/ACL/process actions, record the exact authorization/evidence gap and preserve DENY; do not ask the Owner for root material prematurely or re-run broad platform research.

Current canonical route transition is proposed as `M1A_G1_REVIEW_OWNER_CONTROLLED_BOOTSTRAP_BOUNDARY_SOURCE_DELTA`, with `NEXT_ACTION=OBTAIN_EXACT_STAGED_AND_UNSTAGED_SOURCE_DIFF_FOR_INDEPENDENT_STATIC_REVIEW`. This routing proposal remains noncanonical until its documentation PR is merged and fetched back. The local candidate remains uncommitted/unpublished; the PR does not modify it.

```text
LATEST_CODEX_RESULT=SOURCE_CANDIDATE_ONLY; OWNER_REPORTED
SOURCE_PATCH_AVAILABLE_TO_REVIEWER=FALSE
EXACT_DIFF=NOT_ATTACHED
TESTS=WRITTEN; NOT_RUN
BUILD_RUNTIME_MCP_TRANSPORT=NOT_RUN
INDEPENDENT_ROOT=NOT_ESTABLISHED
OWNER_ASSERTION_VERIFIER=NOT_IMPLEMENTED
DURABLE_CHALLENGE_REPLAY_STORE=NOT_IMPLEMENTED
PROTECTED_TRUST_REGISTRY=NOT_IMPLEMENTED
AUTHENTICATED_PROCESS_IPC_OS_BOUNDARY=NOT_ESTABLISHED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
READ_LIST=FAIL_CLOSED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```


## 13. Follow-up calibration — manifest evidence must be bound, not merely well-shaped (2026-10-24)

The supplied source diff for the Owner-controlled bootstrap boundary showed that `validate_owner_bootstrap_evidence()` validated `manifest_sha256` only by a SHA-256 regular expression. The synthetic positive fixture uses `"e"*64`, so a well-formed but incorrect digest is accepted. The helper also fails to check `manifest_git_blob_sha` shape and positive `pull_request_number`.

This is a source-contract defect, not evidence of a runtime exploit: the production bootstrap adapter is absent and the protected-read positive path remains disabled. The minimum repair is to recompute the canonical challenge manifest digest and compare exact equality, validate SHA-1 blob syntax, validate a positive exact integer PR number, and test each mismatch. This is consistent with the project invariant that a data shape or matching identifier is not proof that evidence corresponds to the exact authorized object.

The review was based on Owner-supplied diffs in chat. The local source blob identities have not been independently fetched from the checkout, and none of the source tests were executed. See `CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-static-review-receipt.md`. The route in live `CURRENT-STATE.md` remains authoritative; the next bounded repair route described here is a proposal until adopted on main and fetched back.

## 12. Follow-up calibration — source validation is not enrollment success (2026-10-24)

The reported source correction closes two narrow static-review findings in the pasted delta: the manifest digest must equal the canonical digest of `challenge.expected_manifest()`, and merge metadata requires a valid SHA-1 blob form plus an exact positive pull-request integer. The corresponding source tests are written, not executed; local file hashes and preservation remain `OWNER_REPORTED`.

A correct merge-evidence predicate is not a production enrollment. In particular, the current `OwnerControlledBootstrapBoundary.enroll()` return type is `OwnerMergeVerificationEvidence`, which does not itself state that the one-use challenge was consumed or the protected registry write persisted. Require a separate typed enrollment outcome/receipt contract before callers can treat enrollment as successful. The receipt is a source-level contract, not an OS isolation claim; tests remain unexecuted, and root, verifier, replay store, registry protection, issuer process binding and G1/G2/G3 stay unresolved.

## 13. Follow-up calibration — require exact source delta for receipt review (2026-10-24)

The latest Codex result claims an explicit enrollment receipt contract, supporting consumption/persistence records and source tests. The supplied message contains only a summary, so there is no independent source-level basis to accept those claims yet. Record `TASK_RESULT=SOURCE_CANDIDATE_ONLY`, not a static pass. Obtain the exact unstaged diff for the two authorized source/test files before reviewing it.

The review should discriminate between typed status claims and actual trusted operations; validate exact challenge/Owner/issuer/server/merge bindings, strict value/time semantics, and failure after challenge consumption but before registry persistence. Synthetic `CONSUMED_ONCE`, `PERSISTED`, and `ENROLLED` fields cannot establish durable consumption or write success. Keep all security gates fail-closed and all runtime/test claims unchanged.
