# Canonical continuity, space-time reasoning and anti-loop protocol

- Protocol ID: `CONTINUITY_SPACE_TIME_ANTI_LOOP_V1`
- Owner instruction date: 2026-10-23 (America/Bogota)
- Scope: project reasoning, memory navigation, decision traceability and next-action selection
- Intended audience: every new ChatGPT/Codex/other-AI coordination session working on IABV
- Status: baseline protocol adopted on live `main`; the live-`main` copy is authoritative, and branch-only amendments remain candidates until merged and fetched back
- Project North Star: `GOVERNED_IABV_CODEX_BRIDGE`
- Active technical frontier at creation: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`

## 1. Purpose

Keep the project moving toward its declared outcome without restarting completed investigations, asking the Owner to reconstruct the archive, confusing a design with an implemented capability, or substituting activity for progress.

Treat project continuity as a **time-aware evidence graph**, not as a pile of disconnected chat summaries. Each meaningful event has a date/checkpoint, source, provenance, scope, result, effect on the current state, dependencies and a next action. Reason forward from the latest accepted state while retaining the causal history that explains how the project arrived there.

This protocol improves navigation and reasoning. It does not create technical authority, change a security decision by implication, authorize protected reads, or override the canonical state router.

## 2. Authority hierarchy: which record wins

For every new chat:

1. Revalidate the live GitHub `main` reference. Never use a remembered SHA as if it were still current.
2. Read these five canonical files from live `main`, in exactly this order:
   1. `IABV_v1.5/AGENTS.md`
   2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
   3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
   4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
   5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`
3. Use `CURRENT-STATE.md` as the **sole authority for current route, active task and NEXT_ACTION**. The other front doors supply operating rules and navigation; they cannot silently replace that route.
4. Follow only the relevant handoffs, terminal receipts, accepted contracts and review records linked from those files or returned by a targeted archive lookup. Prefer the most recent accepted evidence, not merely the most recently modified prose.
5. Distinguish live-`main` canonical records from candidate-branch proposals. A change on a branch is not canonical until accepted into `main` and fetched back.
6. If records conflict, do not average them or silently choose the convenient statement. Identify the conflict, check chronology and adoption on `main`, preserve the more restrictive current gate until the conflict is resolved, and record the exact source/commit responsible for the result.

GitHub is the durable central project memory for records actually committed there; it is not guaranteed to contain every raw conversation, local file, private secret or event that nobody recorded. If a fact is absent, report that it was not found in the permitted records rather than claiming universal absence or asking the Owner to remember the archive.

## 3. Build the temporal state map before choosing work

Internally reconstruct this compact state map from the canonical files and only the relevant history:

- `PRIMARY_OUTCOME`: the end-to-end outcome the project is trying to achieve.
- `ACTIVE_TASK` / `NEXT_ACTION`: the current frontier and the one action allowed next by the canonical router.
- `LAST_TERMINAL_TASK`: last closed attempt and its exact terminal result.
- `OWNER_DECISIONS`: explicit decisions, their exact scope, date and receipt.
- `ESTABLISHED`: claims supported by accepted evidence, with source and provenance.
- `OWNER_REPORTED`: useful Owner-supplied reports that have not been independently verified.
- `UNKNOWN / NOT_INSPECTED / NOT_RUN`: unresolved observations; never silently promote them to true or false.
- `CLOSED_OR_REJECTED_PATHS`: alternatives already investigated, why they failed, and what genuinely new evidence would justify reopening them.
- `DEPENDENCY_EDGE`: the exact prerequisite that blocks the desired next stage.
- `AUTHORIZATION_BOUNDARY`: the precise read, edit, test, runtime, spend, merge or deployment actions currently permitted and forbidden.
- `EXPECTED_TRANSITION`: what concrete evidence/result would change the state after the proposed action.
- `NEXT_OWNER_INPUT`: leave empty unless a decision or fact only the Owner can supply is genuinely needed.

Use a dependency graph, not a flat checklist: an action is valuable when it resolves the earliest open dependency on the path to the North Star. Do not work on a downstream feature while its trust, authorization or contract prerequisite is still unsatisfied.

## 4. Objective-first next-action algorithm

Before performing or recommending any action, answer these questions in order:

1. **Outcome link:** Which explicit requirement of `PRIMARY_OUTCOME` does this action advance?
2. **Current frontier:** Which exact unresolved dependency or contradiction is it intended to resolve?
3. **Prior-art check:** Does a canonical receipt already answer this question or close this path?
4. **New information:** What genuinely new evidence, authorization or falsifiable test distinguishes this attempt from a prior failed/closed attempt?
5. **Route and actor:** Which supported tool, repository path or named actor can perform it under current permissions?
6. **Scope and risk:** Is it explicitly authorized? What side effects, privacy exposure, tunnel, runtime, cost or protected resource might it touch?
7. **State transition:** What exact evidence must be returned, where will it be recorded, and which state field could legitimately change?
8. **Stop condition:** What result means stop without trying alternate routes or repeating the action?

If the action cannot name a dependency it advances, new information it obtains, a permitted route and a measurable state transition, do not do it. Explain the blocker once in plain language and select the nearest safe, useful action that is actually authorized.

## 5. Anti-loop and Owner-burden rules

- Never ask the Owner to remember, locate or paste a document that the coordinator can search in the project archive through an already-supported, permitted GitHub route.
- Search the canonical index and targeted historical records before asking the Owner for context. Do not perform an indiscriminate repository-wide scan when a targeted query or known receipt is enough.
- Never repeat completed Entra/Authenticator setup, the already-ratified Option D decision, or another closed diagnostic/review just because a new chat started.
- A terminal failure remains terminal for its stated scope. Reopen it only when (a) new evidence changes a premise, (b) a specific correction fixes the identified failure mechanism, or (c) the Owner makes a new explicit decision that changes the permitted scope. A generic desire to progress is not evidence that a failed route now works.
- Do not disguise the same experiment as a different task, rerun a denied/unavailable reader, or move to another tool/AI/transport to bypass a denied route. Record `NOT_RUN` / `SUPPORTED_ROUTE_NOT_FOUND` accurately and stop.
- Do not report “no asset exists” from “could not inspect it.” Preserve `UNKNOWN; NOT_INSPECTED`.
- Do not ask the Owner to provide an independent root merely because the design requires one. First reconcile the existing records and permitted evidence routes. Ask only for a genuinely new fact/decision that the Owner alone controls, and explain exactly why it changes the decision path.
- One bounded next action at a time. Avoid presenting a large menu of hypothetical paths when canonical routing selects a single one.
- “Proceed” authorizes only the bounded action just described; it is not blanket permission for new credentials, protected access, implementation, tests, runtime, transport, tunnels, spending, deployment, merge or release unless those actions were explicitly included.

## 6. Provenance labels and reasoning discipline

Use exact epistemic labels where relevant:

- `DIRECT_GITHUB`: branch/ref/blob/commit/file actually fetched from GitHub during this turn.
- `OWNER_REPORTED`: result or setup the Owner supplied but the coordinator did not independently observe.
- `STATIC_REVIEW`: code/document inspection without executing the component.
- `RUNTIME_VERIFIED`: the named command or runtime path was actually executed and observed under the stated scope.
- `NOT_RUN`: execution was not performed.
- `NOT_INSPECTED`: content/resource was not read.
- `SUPPORTED_ROUTE_NOT_FOUND`: the attempted authorized path was not available; this does not prove global absence.
- `CANDIDATE_ONLY`: branch proposal or design not accepted as canonical.

Never blur these categories. A green unit test does not prove production runtime; a hash establishes object identity, not truth of the object’s claims; MFA authenticates a user to an identity system, not IABV authority; a static design is not implementation; a successful attempt does not prove durable delivery/persistence unless fetch-back evidence says so.

## 7. Delegating to another AI or asking the Owner to act

Delegate only if another actor has a capability the coordinator actually lacks and the task has a bounded, authorized scope. Place the full copy/paste task inline and identify near the top: recipient/tool, exact source/revision, specific objective, known findings, work already closed, permitted actions, forbidden side effects, first unresolved edge, stop conditions, required evidence schema and exact return artifact. Do not ask another AI to re-investigate the entire project.

When Owner action is truly required, explain in ordinary Spanish:
1. what one step will do;
2. why it advances the North Star now;
3. exactly what the Owner must click/copy/do (only if an Owner action is necessary);
4. what result to return;
5. what will not be changed or exposed.

Do not transfer archive archaeology to the Owner. Do not ask for secrets, tokens, private keys, recovery codes or protected data in chat or public GitHub.

## 8. Durable completion and handoff

For every meaningful bounded task, leave a concise, durable record when authorized and useful. It must record:

- task ID, date/time zone, canonical base SHA and candidate ref/HEAD if any;
- precise objective and authorization scope;
- sources and blob/commit IDs, with provenance;
- prior work reused and why no closed path was repeated;
- action actually performed, not planned;
- exact results, failures and unrun steps;
- before/after state delta, including what did **not** change;
- decision/gate implications;
- one next action, its dependency edge, actor, permitted route and stop condition.

A documentation writeback must be made on an isolated documentation branch unless canonical policy explicitly directs otherwise, reviewed for scope, fetched back at the exact branch/commit, and compared against the expected paths/content. Never claim a candidate protocol is active before its acceptance on `main` is fetched and verified. Do not include private tenant/user identifiers or credentials in public history.

## 9. Required answer shape for each new chat

After preflight, give the Owner one clear operational summary in accessible Spanish:

1. **Where the project stands** — current North Star, active stage and source revision.
2. **What is already done** — decisions and results that must not be repeated.
3. **The true blocker** — one precise missing dependency, with evidence and provenance.
4. **The next step** — one action only, why it advances the outcome, who must execute it and what result is expected.
5. **Owner action** — say explicitly either “No tienes que hacer nada” or give the exact necessary action; never ask the Owner to redo archive research.
6. **Boundary** — what remains unauthorized/unknown and why.

Prefer plain-language explanations followed by technical identifiers when useful. Avoid presenting a status report as progress. Do not promise asynchronous work or imply that a future result will arrive without performing the action in the current turn.

## 10. Historical IABV checkpoint at protocol creation (2026-10-23; superseded by live CURRENT-STATE.md)

At the time this protocol was proposed, live `main` was `2a5ac42fabbd7c6a66591d127e379432495ad3bc`. Canonical routing remains:

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY; DO_NOT_REPEAT_SETUP
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

This protocol upgrade is process/documentation work only. It does not close G1, authorize inspection of trust assets, authorize implementation or tests, change the no-bootstrap decision, make the unauthenticated HTTP endpoint safe, or authorize a public tunnel, spend, deployment or release. Any technical work must still follow the current canonical `CURRENT-STATE.md`.

## 11. New-chat acceptance checklist

A chat is **not continuity-complete** until it has:

- [ ] revalidated live `main` and the five canonical files in the required order;
- [ ] identified the exact current routing authority and distinguished it from branch-only proposals;
- [ ] read the relevant terminal receipt(s) for the active frontier;
- [ ] carried forward completed work, Owner decisions, closed paths and negative results with their provenance;
- [ ] stated one dependency-linked next action or explained why no authorized action can advance the technical gate;
- [ ] avoided asking the Owner to search/remember the archive or redo completed setup;
- [ ] checked scope, route, side effects, cost and stop conditions before execution;
- [ ] recorded/fetched back any authorized durable writeback and made no unsupported claim of success.

If any item cannot be completed, state the exact uncompleted item and why. Do not improvise authority to appear productive.

## 12. Operational lessons added from the terminal G1 review (2026-10-24)

Apply these refinements together with sections 1–11. They improve evidence handling and chat continuity; they do not override live `CURRENT-STATE.md` or authorize any technical action.

### 12.1 Fresh state beats remembered state

- On every new chat, revalidate the live `main` ref, then read the five front doors in the exact order in section 2.
- Revalidate a PR's actual head/state before editing, reviewing, marking ready or merging. A user-reported SHA is a locator to verify, not proof of the current head.
- After a branch update, inspect the resulting diff and changed-file list again. Do not assume the update left a PR at the head previously reported.

### 12.2 Source custody and independent attribution are separate checks

- If a delegated executor says a supplied attachment is unavailable, inspect the actually available source/package through supported routes. Do not replace it with a file that merely has a similar display name.
- Before archiving, compare the exact source member, manifest checksum and destination bytes. A mismatch means stop and resolve provenance; do not continue on the substitute or silently rewrite it. Preserve the accepted report byte-for-byte.
- Hash equality establishes byte identity only. It does not authenticate a model invocation, the reported reviewer, or the truth of the report's claims. Model availability/selection is not execution evidence.

### 12.3 A route failure is not evidence of global absence

Distinguish `ROUTE_SURFACE_MISMATCH` or `ACTION_UNEXECUTABLE_NO_EVIDENCE` from `TECHNICAL_ABSENCE`. If a permitted reader or artifact route cannot be used, report the exact route as unavailable/not verified, preserve `UNKNOWN; NOT_INSPECTED`, and stop. Do not retry a denied reader or switch tool/provider/transport to bypass the restriction.

### 12.4 Terminal-review semantics and stop conditions

- `BLOCKED_NO_NONCIRCULAR_ROOT` is the terminal result for this review scope. It means the reviewed sources did not establish a qualifying root; it is not proof that authority assets do not exist.
- `PASS` on a bounded review/writeback checklist is not a G1 pass, implementation readiness, or gate closure. G1/G2/G3 remain `NOT_ESTABLISHED`; prerequisites remain `8; CLOSED=0`.
- Do not re-run broad Windows/TPM/Entra/OIDC/GBA inventories or the same adversarial review without genuinely new independent evidence about a pre-existing root, its custodian/mandate and independent verification channel, plus the exact Owner-to-principal, authority-to-issuer and issuer-to-server bindings.
- With no such evidence, `NEXT_REVIEW_TARGET=NONE_UNTIL_GENUINELY_NEW_INDEPENDENT_EVIDENCE` and `AUTOMATIC_FOLLOW_ON=FALSE`. No technical action can honestly close the current dependency. Do not invent a work item merely to appear productive.

### 12.5 Canonical adoption has an observable boundary

A successful branch update or open PR is not canonical. Canonical status requires the record to be adopted on live `main`, followed by fetch-back of the exact live files and verification that the intended route/hash appears there. PR lifecycle status belongs to live GitHub metadata; durable project records describe the evidence/result and must not retain a transient “pending” label as if it were current technical truth. `CURRENT-STATE.md` remains the sole current routing authority.

### 12.6 Handoff delta and first response in the next chat

Use [the terminal G1 new-chat continuity handoff](./CHAT-ARCH-2026-10-24-M1A-G1-terminal-review-new-chat-continuity-handoff.md) for the full causal chronology, source custody incident, evidence classification and exact copy/paste startup prompt. The first response in a new chat must state the verified live-main SHA, terminal review result, precise blocking dependency, fail-closed authorization boundary and whether any genuinely new evidence changes the route. Do not ask the Owner to repeat the reopening decision, Entra setup or archive research.

---

## 13. New calibration — localize the blocked edge; reconcile authorization before handoff (2026-10-24)

This calibration repairs a coordinator failure observed after the terminal G1 review. The route was treated too broadly as project-wide paralysis, while a later proposed handoff went too far in the opposite direction by requesting implementation despite canonical `IMPLEMENTATION=NOT_AUTHORIZED`. Apply both safeguards:

- **Localize every blocker.** State whether it is an `AUTHORITY_GATE`, `ROUTE_SURFACE_MISMATCH`, `ACTION_UNEXECUTABLE_NO_EVIDENCE`, `SOURCE_DEFECT`, `EVIDENCE_GAP`, or `AUTHORIZATION_GAP`. Name the exact object, operation, scope and source.
- **No invalid promotion.** `route unavailable → resource absent`, `signature verifies → key holder is authorized Owner`, `PR merged by actor → Owner-to-Windows identity bound`, `source written → source executed`, and `tests authored → tests passed` are all invalid inferences.
- **No all-or-nothing paralysis.** A gate blocks the operations whose prerequisites depend on that gate; it does not prove every separate task technically impossible. Nevertheless, an independent task may run only if it is separately authorized by the current route or by a new bounded Owner authorization. “Independent” never means “authorized.”
- **No authorization drift.** Before delegating, compare the proposed prompt with the live `CURRENT-STATE.md` fields for implementation, tests, build, runtime, transport, credentials/apps, public tunnel, cost, deployment and merge. If any requested side effect contradicts canonical state, do not issue the prompt as executable; either reduce it to the permitted scope or identify the exact authorization decision needed.
- **Keep terminal outcomes scoped.** `BLOCKED_NO_NONCIRCULAR_ROOT` means the reviewed evidence did not establish the required root. It does not establish absence. The terminal status and `AUTOMATIC_FOLLOW_ON=FALSE` still control routing: do not start unrelated technical tasks autonomously or bypass denied readers.
- **Make the next action discriminating.** An allowed action must produce named evidence that can change a state field or reduce a concrete uncertainty. If no action is authorized, report the precise missing prerequisite and stop rather than manufacturing a task to appear productive.
- **Review returned Codex work as a candidate.** Verify exact session, repository, branch, base/HEAD, changed files, source-level enforcement, crypto verification vs PEM-shape validation, durable one-time replay consumption, exact target binding, process/IPC boundary, G2/G3 fail-closed behavior, and the difference between written and executed tests. A local candidate is not canonical and no gate closes by intent alone.

The detailed incident-derived checks and evidence labels are recorded in [Route-gate calibration knowledge delta](./CHAT-ARCH-2026-10-24-ROUTE-GATE-CALIBRATION-KNOWLEDGE-DELTA.md). This section is a reasoning/navigation calibration only; it does not change the current technical route or authorize implementation, tests, protected reads, runtime, transport, credentials, spending or deployment.

## 14. Explicit Owner decision transition — do not freeze a historical NEXT_ACTION

The canonical `CURRENT-STATE.md` remains the single route authority, but its current fields are mutable state, not an immutable veto against a later explicit Owner decision. When a new Owner instruction changes the allowed scope, preserve the old terminal result as history, create a provenance-labeled decision receipt, and add a new current routing block at the top of `CURRENT-STATE.md`. Do not keep repeating the old `NEXT_ACTION` while pretending the new decision never happened.

Separate:
- **Review outcome:** what the evaluated evidence established or failed to establish.
- **Authorization event:** which next actions the Owner now permits and which are still forbidden.
- **Technical state:** which roots/bindings/code/tests/runtime properties are actually established.

A new authorization changes only the second category. It does not establish a root or close a gate. In this incident, the root review remains terminal, but bounded source construction and source-test authoring are newly authorized; test execution/build/runtime/transport, credentials, service installation, persistent OS changes, publishing, deployment, cost and protected-read release remain unauthorized. Keep all real protected reads fail-closed until independent root/mandate and G1/G2/G3 requirements are verified.

**Required transition:** record the Owner decision and exact scope; verify the current baseline; add an additive routing override plus link to the receipt; preserve previous state below as history; validate that every new field matches the authorized scope; then hand off one bounded task. If an update fails in one tool surface, record the exact write failure and keep candidate status; do not reinterpret a tooling issue as proof that no authorized engineering task exists. Do not bypass denied readers or credentials.

The detailed incident and required Codex handoff fields are in [the route-gate calibration knowledge delta](./CHAT-ARCH-2026-10-24-ROUTE-GATE-CALIBRATION-KNOWLEDGE-DELTA.md), sections 10 and 7. This rule is navigation and authorization reconciliation; it does not permit any side effect excluded by the latest Owner decision.



The related [continuity algorithms static audit](./CHAT-ARCH-2026-10-24-CONTINUITY-ALGORITHMS-STATIC-AUDIT.md) is a separate workstream. Do not preempt the active trust-organ wiring task with an unrelated context refactor; schedule it only after the current candidate delta is reviewed and the next scope is reconciled.


## 15. Transcript chronology is evidence, not routing authority (2026-10-24)

A copied chat transcript and live GitHub can describe different points in the task sequence. The final prompt visible in a transcript is not necessarily the current task: a later report or documentation adoption may already have advanced the canonical route. This exact mismatch is a known coordination hazard and must be handled as an explicit intake step, not by guessing which chronology is newest.

When the Owner supplies a Codex response:

1. Extract its exact `TASK=` identifier and compare it with the prompt it claims to answer. Do not infer task identity from the message order alone.
2. Refresh live `refs/heads/main` and read `CURRENT-STATE.md`; recorded SHAs are historical snapshots. Current state governs the next action, while the response is evidence about the task it actually executed.
3. If the response belongs to a task already superseded by the current route, evaluate it against that task's acceptance criteria and record any genuinely new delta, contradiction, or blocker. Do not rewind `ACTIVE_TASK`, reissue the same prompt, or treat an Owner-reported local change as canonical merely because it came last in the transcript.
4. Reconcile checkout path, branch, HEAD before/after, base/main freshness, worktree status, staged/unstaged changes, exact blobs/diff, source locations, and checks written versus checks executed. A reused branch name does not prove the candidate is unchanged.
5. Preserve provenance: GitHub main/PR state may be directly verified; local Codex claims remain `OWNER_REPORTED` until the source delta is accessible and reviewed. Never promote written tests to passed tests or source intent to runtime behavior.
6. Choose the follow-on only after intake, from the live route and the Owner's exact authorization. A new report can refine the evidence state; it does not itself create root authority, change security facts, or expand permissions.

Historical checkpoint at the reviewed baseline (2026-10-24): the pasted transcript ended with an AppBootstrap registration prompt, while the then-live `CURRENT-STATE.md` routed to `M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY`. That source attempt was subsequently reviewed as one whole supplied diff bundle, and the bounded source-only attempt is now terminal for the evidence available. After documentation-only PR #493 was adopted and the route was fetched back, the current action became waiting for genuinely new independent root/mandate and authenticated Owner-to-host/issuer-boundary evidence. Treat the AppBootstrap prompt and the earlier source-task instructions in sections 16–20 as historical evidence, not active tasks. Always derive the present action from live `CURRENT-STATE.md`. See [route-gate calibration, section 11](./CHAT-ARCH-2026-10-24-ROUTE-GATE-CALIBRATION-KNOWLEDGE-DELTA.md#11-follow-up-calibration--transcript-task-versus-live-route-2026-10-24).

This protocol update is durable project guidance, not model-weight training. It does not change the active technical route, Owner authorization, the eight open prerequisites, or fail-closed behavior.


## 16. Bootstrap/issuer candidate result — review before asking for new authority material (2026-10-24)

The current Owner-reported result for `M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY` says the candidate gained typed challenge/evidence contracts and source tests but not a real Owner assertion verifier, independent root, durable challenge/replay store, protected registry, or authenticated isolated issuer/IPC/OS boundary. It remains `SOURCE_CANDIDATE_ONLY`; the exact local patch has not been independently inspected and no tests/build/runtime/MCP/transport were run.

The next discriminating action is not a second implementation attempt and not a request for the Owner to supply trust assets before reviewing the change. First obtain the exact patch for the reported three paths from the same local Codex checkout, preserving separation of the pre-existing staged index and the new unstaged delta. Inspect that source delta against the current handoff acceptance criteria. If exact source is unavailable, state `ACTION_UNEXECUTABLE_NO_EVIDENCE` for independent source review; do not replace it with a narrative summary or infer global absence.

The source report is internally precise about what is missing, but that precision is still reported evidence, not independent proof. Signature verification with a caller-supplied public key does not establish that key as the Owner's trusted key. Challenge fields binding `server_id` and `issuer_id` do not themselves provide authenticated process identity or a protected issuer. Source tests written are not test results. Keep G1/G2/G3 not established, all eight implementation prerequisites open, and protected reads fail-closed.

Required intake artifacts: current main ref, candidate path/branch/HEAD, status before any command, index diff and worktree diff for all three paths, the exact reported blob/hash values, source locations, and explicit statement that no files were modified during diff extraction. Do not merge/rebase, stage, commit, publish, execute tests, build, start runtime, or use MCP transport in the review-preparation step.


## 17. Source-evidence consistency review and minimum repair (2026-10-24)

The static review of the supplied bootstrap-boundary diffs found that `validate_owner_bootstrap_evidence()` accepts a syntactically valid `manifest_sha256` without confirming it is the canonical digest of `challenge.expected_manifest()`. The positive test fixture uses the arbitrary value `"e"*64`, so it does not test actual digest binding. The helper also omits validation of the Git blob SHA format and a positive pull-request number. See the [review receipt](./CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-static-review-receipt.md).

The next task is a minimum source-only correction: compute the same canonical manifest digest already used by the existing manifest verification test; require exact equality; validate `manifest_git_blob_sha` as 40 hexadecimal characters; require `type(pull_request_number) is int` and a positive value; and add source tests for malformed/wrong values and a positive fixture with the correct digest. Unexpected malformed evidence should produce a controlled fail-closed verification error.

Do not broaden this repair into a production issuer, root enrollment, registry or process-boundary implementation. Do not execute tests/build/runtime/transport or alter the dirty candidate's previous staged/unstaged work. The source fix does not establish signature provenance, root authority, IPC/OS isolation, G1/G2/G3 or positive protected reads. After the exact repair diff is returned, inspect only that delta and preserve the same evidence distinctions.

## 16. Source evidence correction versus enrollment outcome (2026-10-24)

The bootstrap-boundary correction task is reported as `SOURCE_CANDIDATE_ONLY`. The exact pasted diff now contains the required canonical manifest-digest equality check, SHA-1 format validation for `manifest_git_blob_sha`, and exact positive-integer validation for `pull_request_number`; tests for these cases are written but `NOT_RUN`. Treat this as targeted static review only because the local worktree was not directly accessible and the candidate remains unpublished.

Do not infer that the broader bootstrap boundary is implemented. A separate contract mismatch remains: `OwnerControlledBootstrapBoundary.enroll()` returns `OwnerMergeVerificationEvidence`, which describes repository merge proof and is not an enrollment receipt confirming successful one-use challenge consumption and protected registry persistence. The next bounded, authorized source step is to define an explicit typed enrollment outcome/receipt and focused source tests. Do not add a production trust root/verifier/OS boundary or claim positive authorization; keep G1/G2/G3 unestablished, all eight prerequisites open, and protected reads fail-closed.

## 17. Enrollment-receipt summary is not a reviewable source delta (2026-10-24)

When Codex reports a multi-file source change but supplies only summary prose, classify the result as `OWNER_REPORTED` and the static review as `NOT_PERFORMED_EXACT_DIFF_REQUIRED`. Local paths, blob IDs and command summaries do not expose the implementation to this reviewer. Do not infer code correctness from described type names or reported test coverage.

For the enrollment receipt contract, obtain the exact unstaged diff from the same checkout for the two authorized files. Review the actual type definitions, validator and tests, including strict booleans-versus-integers handling, Owner/issuer/server/merge bindings, validity and event-time ordering, empty/malformed references, and behavior if challenge consumption succeeds but registry persistence fails. Status fields such as `CONSUMED_ONCE`, `PERSISTED`, and `ENROLLED` are only claims unless produced by trusted issuer-owned operations. Preserve staged/unstaged state and keep tests/build/runtime/transport unexecuted; do not claim G1/G2/G3 progress from source shape alone.

## 18. Receipt persistence target must be independently bound (2026-10-24)

Static review of the supplied enrollment receipt module found that the validator verifies multiple internal field bindings and event-time order, but accepts any nonempty `persistence.registry_id`. A receipt must be checked against an expected registry identity supplied by future trusted host/provider configuration, not a value copied from the receipt or request. Add an exact equality predicate and a negative test using a different well-formed registry identifier.

The test diff supplied for the prior task is incomplete (contains an ellipsis), so describe the review as partial and do not assert that all negative tests exist. Obtain the complete diff after the correction. Keep the distinction between typed status claims and trusted durable actions; do not infer root, registry protection, or runtime enrollment from a dataclass or source test.

## 19. Expected registry identity binding — static correction result (2026-10-24)

The latest supplied F-03 correction adds `expected_registry_id` to `validate_owner_bootstrap_enrollment_receipt()`, rejects non-string/blank values, and requires exact equality with the persisted receipt's `registry_id`. The full supplied test diff contains a mismatched but well-formed identifier case and invalid expected-ID cases. This is a static review of the pasted diff only; tests remain `NOT_RUN`, and local worktree identity and hashes remain `OWNER_REPORTED`.

A caller-supplied `expected_registry_id` is not automatically trusted. A future production boundary must source it from host-owned trust configuration/provider context and must not derive it from the receipt, request or untrusted issuer metadata. The typed receipt and outcome labels still do not prove durable challenge consumption or protected registry persistence. Keep G1/G2/G3 unestablished and protected reads fail-closed.

## 20. Consolidated candidate review before further source changes (2026-10-24)

After narrow contract corrections have been reviewed, do not perpetuate micro-patch routing when the dirty worktree spans several staged/unstaged source and test files. Preserve the candidate and obtain the complete current staged and unstaged diff across all reported modified paths for one bounded static review. The review must establish source-composition coverage and distinguish remaining source defects from obligations that require excluded authority-root, credential/enrollment, OS/ACL/trust-store, authenticated IPC or runtime actions. If the complete diff cannot be emitted, report the exact coverage limit instead of implying whole-candidate review.

For the current bootstrap candidate, F-01/F-02/F-03 are present in the supplied focused deltas, but this is not a review of all 12 dirty paths. Tests/build/runtime/MCP/transport remain `NOT_RUN`; local identity/hashes/status remain `OWNER_REPORTED`; G1/G2/G3 and all eight prerequisites remain unresolved. The [consolidated review receipt](./CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-consolidated-static-review-receipt.md) is documentary evidence only; live `CURRENT-STATE.md` continues to govern routing.

## 21. Cross-chat evidence learning loop (2026-10-24)

Treat each chat/Codex interaction as a potential project-knowledge update, not as automatic truth. The loop is: (1) preflight live `main` in the strict five-file order and identify the exact current task; (2) reconcile the supplied result to that task's acceptance criteria; (3) preserve exact provenance and classify evidence level; (4) record defects only when the full relevant diff is available; (5) consolidate narrow fixes into one whole-delta review before another micro-task; (6) update the review receipt, `CURRENT-STATE.md` proposal, context index and handoff together; (7) clearly label branch-only documentation and never imply canonical adoption before merge/fetch-back; (8) end with one bounded evidence request and a paste-ready next-chat prompt.

Evidence classes must remain distinct: `OWNER_REPORTED`; supplied-diff static review; direct repository verification; tests actually executed; runtime/transport verified; canonical merge and fetch-back. Hashes prove bytes only. Source status strings and typed records do not prove that operations occurred. Unknown/not-inspected is not absent. A new chat must check live refs rather than inherit yesterday's SHAs as current.

This loop improves continuity by writing lessons into versioned project records. It does not update model weights or establish that the underlying model has learned across chats. Use the [consolidated new-chat handoff](./CHAT-ARCH-2026-10-24-M1A-G1-CONSOLIDATED-NEW-CHAT-HANDOFF.md) as the current prompt template.

## 22. Post-PR #493 route reconciliation and Owner continuity directive (2026-10-24)

The Owner authorized a documentation-only integration of PR #493 to preserve the Mente Espacio-Tiempo directive and reconcile the terminal whole-candidate review. GitHub reports the squash merge succeeded at `3235219304f87210dd235e0a657111e8981b13b4`. Follow-up documentation commits reconciled the adopted `CURRENT-STATE.md` and replaced obsolete front-door task instructions with explicit historical checkpoints. Fetch-back from live `main` confirmed the route and all five entry-point documents.

The current route is:

```text
ACTIVE_TASK=M1A_G1_WAIT_FOR_GENUINELY_NEW_INDEPENDENT_ROOT_AND_MANDATE_EVIDENCE
PREVIOUS_TASK=M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY
PREVIOUS_TASK_RESULT=TERMINAL_FOR_CURRENT_SOURCE_EVIDENCE; BOUNDARY_NOT_ESTABLISHED
NEXT_ACTION=WAIT_FOR_GENUINELY_NEW_INDEPENDENT_ROOT_AND_AUTHENTICATED_OWNER_ISSUER_OS_BOUNDARY_EVIDENCE
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
PROTECTED_READS=FAIL_CLOSED
AUTOMATIC_FOLLOW_ON=FALSE
```

The complete supplied staged/unstaged diff bundle was byte-verified and received static review. This verifies the attached patch artifacts, not the Windows worktree identity or executed behavior. No tests, build, runtime, MCP, real transport, or protected read was executed. Do not ask the Owner for the same diffs again, repeat the whole-candidate review, restart source-only micro-patches, or treat a prior transcript's last prompt as the current route. Reopen only when genuinely new, independently verifiable evidence changes the root/mandate/identity-boundary premise, or a new explicit Owner decision changes the permitted scope. Unknown authority assets must remain `UNKNOWN; NOT_INSPECTED`, never silently converted to present or absent.

The Mente Espacio-Tiempo audit remains static. It identified source-level risks involving persisted-context freshness (including a 24-hour minimum age behavior), initial perception preceding attachment of session-goal context, and missing durable proof linking a briefing package to its destination and confirmation. These findings do not prove that the live Windows package is stale or that a specific delivery failed. Do not create another memory/orchestrator. Reuse the existing protocol, improve its source/runtime evidence contract only under a newly authorized route, and verify any later implementation independently.

The reusable continuity lesson is an explicit loop: `live main → five-file intake → match supplied result to exact TASK/acceptance criteria → provenance/evidence classification → reconcile with current route → one authorized action → durable receipt → fetch-back → later non-identical reuse`. Writing a memory is not itself learning; retrieval alone is not reuse; a later decision must observably change because it used the retained lesson. This protocol changes project guidance only; it does not change model weights or prove autonomous learning.
