# UAAL-D021 — Route Truth, Artifact Identity, and Verified-Progress Selection

**Date:** 2026-10-28
**Root:** `UAAL-ROOT-001`
**Parents:** `UAAL-D019` — Space-Time Anti-Loop and First-Open Causal Frontier; `UAAL-D020` — Verified Progress Utility, Strategy Switching, and Preparation-Debt Control
**Status:** `PROPOSED_DOCUMENT_METHOD; NOT_CANONICAL_UNTIL_INTEGRATED; RUNTIME_ENFORCEMENT_AND_LATER_CAUSAL_REUSE_NOT_PROVEN`

## 1. Why this refinement exists

The interaction exposed a protocol execution failure, not a single bad hash.

- The canonical route and several entry snapshots still described M1B as unpublished, while the live repository already contained [PR #555](https://github.com/jhonf463r/Python/pull/555) with the exact R4 reader and test files.
- The assistant selected a new publication task from a stale receipt without first querying the existing M1B branch/PR and its review. Codex correctly stopped when the older R3 hashes did not match the current R4 files.
- That mismatch was initially treated as a candidate discrepancy before its revision lineage was checked. The actual R4 local hashes later matched the remotely retrieved files.
- The active task remained M1B, but the most recent conversational activity was M1A/R7. Conversational recency displaced the canonical route in action selection.
- Documentation work accumulated around the deviation. Some continuity corrections were useful, but a draft-branch writeback is not a canonical update and continuity notes do not substitute for crossing the target edge.

This is an observed failure analysis for this episode, not a measured repository-wide frequency or proof of runtime enforcement.

## 2. Organ-level map of the failure

The biosophy/organ metaphor is a functional systems map, not a claim of consciousness or biological equivalence.

| Functional organ | Evidence in this episode | Failure mode | Required control |
|---|---|---|---|
| Perception / ingress | The normal contents read for `CURRENT-STATE.md` returned an empty body; fetching its exact blob recovered the content. | Transport failure can be misread as empty state. | Require source/ref/blob identity; recover the exact blob before interpreting empty output. |
| Task-local world model / inference | The exact source showed that the route, memory intake and action selector can disagree about the same live project state; the conversation's recent topic was not the active dependency. | Stored records can be retrieved without being reconciled into a time-aware causal model; plausible narrative can outrank a discriminating observation. | Build the minimum objective-conditioned state/causal model, retain competing hypotheses and falsifiers, and choose the smallest authorized observation that changes the decision. |
| State representation / routing | `CURRENT-STATE.md`, `README.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md` and `AGENTS.md` retained the old M1B R3 “local/unpublished” snapshot. | Duplicated entry snapshots drifted together and looked authoritative by repetition. | Canonical route wins; snapshots are caches. Detect mismatch and correct entry overlays from verified evidence. |
| Identity / provenance | R3 hashes `e3811a…` / `a7459f…` differed from R4 hashes `fcd743…` / `e86a7c…`. | Hashes were used without binding each digest to an artifact revision and evidence stage. | Bind each digest to repository, path, commit/ref, byte count, hash algorithm, digest, revision label and evidence stage (R1/R2/R3/R4). |
| Selector / action | PR #555 already existed, but the proposed prompt asked to publish the candidate again. | Existing realization discovery was omitted; the latest topic outranked the active objective. | Enumerate existing branches, commits, PRs, paths, reviews and statuses before create/publish/retest/prompt actions. |
| Execution / observation | R7 Actions ended `startup_failure` with no jobs; tests/build/runtime were not run in this session. | A workflow state could be mistaken for a test result unless stages stay distinct. | Keep tests `NOT_RUN` absent command/job evidence; workflow presence is not proof of execution. |
| Memory / learning | R8 writeback was on a draft branch, not `main`. | Branch persistence may be mistaken for canonical update or learning. | Separate local → branch/PR → review → main fetch-back → later causal reuse. |
| Governance | Option D and G1/G2/G3 and bridge gates remained closed. | This part worked and must not be weakened by process pressure. | Preserve authorization gates while improving route efficiency. |

## 3. UAAL-D021 algorithm

Apply this before any material handoff, publication, retest, new branch or protocol writeback.

### Gate A — current route and source integrity

1. Read the live `main` SHA.
2. Read `README.md`, then `CURRENT-STATE.md`, then `CONTEXT-INDEX.md`, then `MEMORY-OPERATING-PROTOCOL.md`. Read `AGENTS.md` before any repository mutation or command execution. Retrieve only objective-relevant protocol lineage after the four-file route intake.
3. Bind each read to the exact ref and blob. If the normal file endpoint returns empty content unexpectedly, fetch the identified blob. Empty transport output is `RETRIEVAL_FAILED`, not an empty canonical state.
4. Treat `CURRENT-STATE.md` as the only routing authority. Other entry blocks are navigational snapshots; repeated stale copies do not gain authority by majority.
5. Keep entry documents as pointers rather than synchronized copies of volatile task status or hashes. The only task status/`NEXT_ACTION` record belongs in `CURRENT-STATE.md`; if an entry copy is needed for a dated receipt, label it as a timestamped snapshot and never as a parallel authority.

### Gate B — route-realization discovery before action

Before proposing to create, publish, update, reimplement, retest, clone, or ask another actor to do so, query supported surfaces for existing realizations: branch, commit, PR, exact changed paths, review, workflow/jobs and current file blobs. If an exact route already exists, assess whether it can be reused or reviewed before creating another one.

A missing local artifact does not prove it is absent from GitHub. A stale receipt does not supersede a live remote branch/PR. If the inventory itself is incomplete, record that limitation and choose a read action to resolve it before writing.

### Gate C — revision-bound artifact identity

Use this identity tuple for every code/document artifact:

```text
ARTIFACT_ID = {
  repository,
  path,
  base_commit,
  candidate_commit_or_ref,
  git_blob_sha,
  byte_length,
  hash_algorithm,
  content_digest,
  revision_label,
  evidence_stage
}
```

- Compare content hashes only when the artifact path and revision scope are the same.
- A digest from R3 must never be used as the expected digest for R4 unless byte identity is explicitly established.
- On mismatch, classify first: `SAME_REVISION_BYTE_DIVERGENCE`, `DIFFERENT_REVISION`, `LINE_ENDING_OR_ENCODING_VARIANCE`, or `IDENTITY_UNRESOLVED`.
- Do not publish, rewrite, reformat or reimplement until the mismatch class is known and a minimal authorized correction is justified.
- Git blob SHA and file SHA-256 identify different things; record their algorithms and do not conflate them.

### Gate D0 — objective-conditioned system landscape and cross-domain transfer

D019 already supplies the causal-frontier loop and D020 supplies progress-utility selection. This gate makes them portable across different problem domains by requiring a minimum sufficient model of the *specific system path* affected by the Owner's objective. It is a diagnostic frame, not a new router, memory store, universal service, or claim that the system is conscious.

#### Normalize the objective before diagnosing the solution

Create a compact `OBJECTIVE_CONTRACT` before choosing a tool, actor, code change or research branch:

```text
OBJECTIVE_CONTRACT = {
  desired_observable_outcome,
  acceptance_oracle_and_failure_condition,
  target_object_or_system_and_revision,
  scope_and_explicit_no_go,
  authorized_effect_budget_and_hard_constraints,
  current_observation_and_provenance,
  stop_or_switch_condition
}
```

Use the Owner's actual objective, not merely the latest noun/topic in conversation. Do not silently replace a desired outcome with a convenient subtask. If a field is not needed for this decision, mark it not applicable; if material and unknown, keep it unknown and select a bounded discriminating read or ask one necessary question. Do not invent an acceptance oracle.

#### Map the minimum sufficient causal landscape

Trace only the path capable of changing the target outcome, but trace it end to end far enough to distinguish a local symptom from an operative cause:

```text
DESIRED_OUTCOME
  <- ACCEPTANCE_ORACLE / OBSERVATION
  <- EFFECTIVE_OPERATION / SELECTED_REALIZATION
  <- CONSUMER_OR_DECISION
  <- TRANSFORMATION / CONTRACT
  <- PRODUCER / SOURCE_OF_TRUTH
  <- PRECONDITIONS / IDENTITY / AUTHORITY / ENVIRONMENT
```

Persistence, later retrieval and feedback are downstream edges when the objective concerns continuity, learning or coordination. Include them only when they affect the target outcome. Name the actual producer, transformation and consumer; a class, registry entry, document, protocol, comment or test double proves existence at its own layer, not that the normal caller reaches it or consumes its result.

This is a *minimum sufficient landscape*, not permission to launch another broad inventory. Stop expanding when the required claim can be adjudicated or when a specific missing edge is identified. Record excluded surfaces and coverage, for example `13/33 files inspected in depth; remaining files UNKNOWN`, so a bounded review cannot silently become a claim about the full system.

#### Bounded evidence acquisition

For every material claim, make a small retrieval plan: `CLAIM → REQUIRED_SOURCE → EXACT_REF/IDENTITY → DEPTH_NEEDED → STOP_CONDITION`. Retrieve only enough source to decide the claim or expose the next missing edge.

- Verify the source ref and blob/object identity before interpreting content. An empty, truncated or failed response is `RETRIEVAL_FAILED`, not proof that the source is empty or absent.
- For large files, retrieve the exact blob once and extract the relevant headings, line ranges or symbols. Do not repeatedly dump an entire large continuity file or historical corpus when the task needs only one current route field.
- Batch only modest independent reads. If a bulk request returns a transport/protocol error, classify the result as retrieval failure and retry with smaller batches or targeted ranges; do not repeat the same oversized request unchanged.
- Maintain a claim-scoped coverage ledger: `READ_EXACT`, `READ_TARGETED`, `SEARCH_ONLY`, `NOT_READ`, `RETRIEVAL_FAILED`. Only `READ_EXACT` or a sufficiently documented `READ_TARGETED` scope can support claims about the portions actually inspected. Search excerpts discover locations; they do not substitute for required full-source review.
- Stop when the decision is supported. If a review is limited to high-risk paths, label it scoped and retain the unread paths as `UNKNOWN`; do not broaden its verdict by implication.


#### Classify the failure using diagnostic lenses, not a single rigid taxonomy

Apply only the lenses relevant to the objective, allowing several at once:

- objective/domain semantics and acceptance;
- canonical state, route and temporal freshness;
- artifact, actor, executable or evidence provenance;
- data/schema/contract shape and identity binding;
- required capability versus selected realization and caller-to-consumer wiring;
- authorization, prerequisites and resource/environment constraints;
- effective operation, hidden defaults and side effects;
- execution stage, observation and independent oracle;
- persistence, reconciliation, feedback and later reuse.

For each candidate explanation, record `OBSERVED`, `INFERENCE`, `HYPOTHESIS` or `UNKNOWN`, the exact affected edge, supporting source, expected distinguishing observation and a falsifier. Do not promote the most narratively plausible explanation to root cause without discriminating evidence.

#### Transfer invariants, not recipes

When moving from one domain to another, preserve the structure of a proven rule only after mapping its semantics into the new domain:

```text
SOURCE_EPISODE
  -> CANDIDATE_INVARIANT
  -> TARGET_DOMAIN_MAPPING
  -> DOMAIN_SPECIFIC_CONSTRAINTS
  -> POSITIVE_CASE_AND_NON_MATCH_OR_FALSIFIER
  -> BOUNDED_DISCRIMINATING_CHECK
  -> VERIFIED_TRANSFER_OR_RETAINED_HYPOTHESIS
```

Example: “declared intent is not effective behavior” can transfer from CLI invocation to a different adapter, but the actual fields that define effective behavior must be re-derived for that adapter. GitHub host/argv details do not transfer literally to a database, a file reader or a planning problem. Similar names and analogies are candidate-generation aids, not equivalence proof. If the semantic mapping cannot be demonstrated, keep the proposed transfer as `HYPOTHESIS`, not an active invariant.

A later non-identical application must show which decision changed because of the invariant, what evidence supported that decision, and what outcome followed. Retrieval, agreement, a link or a new document does not establish transfer or learning.

#### Choose the smallest action that changes the decision

For each admissible candidate route, state: target edge; prior attempt and terminal stage; causal difference; predicted observation for each plausible result; verification source; cost/Owner burden; reversibility; and stop/switch condition. Hard authorization and safety constraints filter candidates first. Among the rest, prioritize direct edge closure, then decision-changing information gain, reuse of an existing realization, and minimum side effects/preparation.

If a task-local edge is terminal, keep it closed while selecting independent authorized progress under D019's dual-track rule. Do not treat the blocked edge as a project-wide stop, and do not manufacture activity when all remaining actions are unauthorized or low-information.

### Gate D — advance contract and action choice

Extend UAAL-D020's `ADVANCE_CONTRACT` with:

```text
ROUTE_ADVANCE_CONTRACT = {
  objective_and_acceptance,
  active_route_from_current_state,
  first_open_dependency_edge,
  exact_source_revision_and_evidence_stage,
  prior_attempt_fingerprint_and_result,
  existing_realizations_checked,
  viable_authorized_action_comparison,
  expected_decision_or_dependency_change,
  observable_success_and_stop_or_switch_condition,
  verification_source,
  writeback_target_and_canonicalization_boundary
}
```

Choose lexicographically, not by activity volume:

1. Hard authorization and safety constraints.
2. Direct closure of the first open edge.
3. The smallest action that materially discriminates the next decision.
4. Reuse of an existing reviewed artifact/route.
5. Necessary preparation only when its causal necessity is demonstrated.
6. Minimum new dependencies, human coordination, mutation and verification burden.

The current chat's last topic, a convenient actor or a prepared prompt is not a routing signal. A prompt is preparation until it causes an observable, verified state transition or is a proven necessary prerequisite.

### Gate E — progress label and anti-loop

Use one terminal label per attempt:

- `EDGE_CLOSED` — the target dependency is independently verified closed.
- `UNCERTAINTY_REDUCED` — new evidence changes which action is correct.
- `SAFETY_PRESERVED` — an unsafe transition was prevented; the target remains open.
- `PREPARATION_ONLY` — an artifact or plan exists but no target-edge change is evidenced.
- `NO_PROGRESS` — no meaningful edge or decision change.
- `BLOCKED` — an exact missing prerequisite prevents the next useful action.

After two preparation-only attempts, switch strategy before preparing a third. Before another action at the same edge, state the causal delta and predicted observable. A new task ID, rewritten prompt, new branch name or repeated summary is not a causal delta.

### Gate F — writeback and cross-AI learning

Keep these stages separate:

```text
LOCAL_CHANGE
→ PUBLISHED_BRANCH
→ PR_DIFF_FETCHBACK_VERIFIED
→ INDEPENDENT_REVIEW
→ MERGED_TO_MAIN (only if authorized)
→ CANONICAL_FETCHBACK_VERIFIED
→ LATER_NONIDENTICAL_CAUSAL_REUSE
```

A draft PR or its fetch-back proves that the branch artifact is published; it does not make the rule canonical for sessions entering from `main`. A method is not proven learned or causally reused until a later non-identical task shows that the retrieved method changed selection and the resulting outcome is independently evidenced.


## 3A. Extension from the G1 enrollment preflight — scoped fetch evidence and non-circular identity

This interaction added one precise case to the route-truth contract: closing an authenticated fetch route for an existing canonical file is not the same as proving an as-yet-uncreated enrollment manifest, the repository's branch rules, or the resulting authority.

### Evidence must be scoped to the exact object and claim

Record separate assertions rather than collapsing them into `GITHUB_ACCESS=TRUE`:

- `REPOSITORY_METADATA`: repository ID, private/public visibility and default branch.
- `MAIN_REF`: exact live canonical `main` commit SHA, preferably confirmed by two independent supported read routes when available.
- `EXISTING_FILE_FETCHBACK`: path, exact ref, Git blob SHA, byte length and whether the exact bytes were actually recovered. If the Contents endpoint returns an empty body, fetch its blob; the blob read closes the retrieval problem only for that file/ref.
- `BRANCH_RULESET`: independently inspectable configuration. HTTP 403 means `UNKNOWN / NOT_AUTHORIZED_TO_INSPECT`, not “rules absent”, “rules disabled”, or “Owner can bypass”.
- `FUTURE_MANIFEST_FETCHBACK`: `NOT_APPLICABLE_YET` until the manifest exists at an exact canonical commit. A CURRENT-STATE read is not a proxy for this later proof.
- `AUTHORITY_ESTABLISHED`: a separate G1 decision requiring the approved manifest, verified key/identity binding, freshness/version/revocation semantics and local receipt. Fetch access alone never establishes G1.

Keep provenance per assertion: `VERIFIED`, `OWNER_CODEX_REPORTED`, `INFERENCE`, `UNKNOWN`, or `NOT_RUN`. If two actors report the same local event, do not label it independently verified unless another actor actually fetched the relevant data. Do not claim the ChatGPT session executed a local command.

### Non-circular enrollment-manifest contract

A manifest cannot truthfully contain its own containing commit SHA, Git blob SHA, or whole-content digest: those identifiers depend on the bytes/commit that would contain the value, creating a self-reference. The manifest should instead contain a stable enrollment ID and schema/version, repository ID and canonical path, public-key identity/thumbprint, Windows SID, exact server/code revision, one workspace root, `ROOT_ENROLLMENT_ONLY` profile, and policy freshness/revocation references. It must contain no private key or credential.

After the exact manifest PR is merged, the local receipt records independently observed metadata: canonical merge commit SHA, PR/merge actor metadata, manifest blob SHA, SHA-256 of the exact fetched bytes, key identifier, Windows SID, code revision and workspace binding. Then compare the fetched public key/bindings to the local CNG key and enrollment request. The receipt records what was verified; it does not replace Owner approval or create authority by itself.

For a private repository, use only an already-authenticated supported Git/API route. Do not expose secrets in tool output, logs, source, chat or manifest. A blocked ruleset API, a public-key fingerprint, an Entra login, or possession of a GitHub App PEM is not interchangeable evidence for the other claims.

### Effect boundaries remain distinct

Even a successful G1 enrollment authorizes no MCP tool by itself. Keep `G2`, `G3`, each tool's operation-specific capability checks, protected reads, side effects, transport and bridge activation as separate acceptance gates. The one-time enrollment implementation and its synthetic tests must not create a key, merge a manifest, launch the bridge or read protected content; the actual one-time enrollment is a separate precisely bounded operation after the candidate has been reviewed.

## 3B. Extension — effective operation semantics and evidence producer (UAAL-D022)

UAAL-D021 route truth and revision binding extend to the actual command that produces evidence. Before a CLI/API adapter may serve as a trust producer, resolve defaults and environment semantics, fix method and destination, normalize platform-specific endpoint syntax after validating the internal path, bind executable identity, and assert exact argv/environment with synthetic tests. See UAAL-D022. This is a proposed method; no runtime enforcement is implied.

## 4. Acceptance tests for the method (reasoning checks, not product tests)

1. **Existing publication:** when PR #555 already contains the candidate, select reuse/review; do not ask Codex to publish a duplicate.
2. **Cross-revision hashes:** when R3 and R4 hashes differ but the current local hashes match the R4 remote source, classify `DIFFERENT_REVISION`, not source divergence.
3. **Empty read:** if a normal contents response is empty but the blob is readable, record endpoint failure and use the exact blob.
4. **Stale entry snapshots:** if README/MOP/AGENTS disagree with the live canonical route, follow CURRENT-STATE and reconcile stale snapshots before selecting an action.
5. **Actions without jobs:** workflow `startup_failure` with an empty jobs list means no test execution is evidenced; preserve `TESTS=NOT_RUN`.
6. **Draft writeback:** changes on a PR branch remain proposed until reviewed/integrated under authorization and fetched back from main.
7. **Historical route conflict:** when the current top addendum identifies an existing published PR but a retained older block still says `SOURCE_PUBLICATION=NOT_DONE` or prescribes publishing it, the latest explicit route/supersession boundary controls. Preserve the older block as history, but never let its stale action compete with the current `NEXT_ACTION`.
8. **Scoped fetch-back:** verifying authenticated access to CURRENT-STATE does not verify bytes of a future manifest, branch-protection rules or G1 authority.
9. **403 on governance metadata:** classify unavailable branch protection/ruleset inspection as `UNKNOWN`; do not infer either the presence or absence of protection.
10. **Non-self-referential manifest:** reject a design that embeds its own containing commit SHA, Git blob SHA or whole-content digest. Store those identities in a post-merge receipt.
11. **G1 vs capability:** a valid Owner-approved enrollment may establish a narrow local issuer identity only; it must not populate the MCP tool allowlist or imply G2/G3/read authorization.

12. **Objective normalization and route fidelity:** when the latest topic differs from the active objective, state the desired observable outcome and acceptance oracle, then route by CURRENT-STATE and the Owner's explicit scope—not conversational recency.
13. **Minimum sufficient landscape:** trace the relevant producer → transformation/contract → normal caller/consumer → effective operation → observation/oracle path; record untouched surfaces as UNKNOWN instead of implying a full-system audit.
14. **Cross-domain transfer:** when reusing a method in another domain, supply a semantic mapping plus a non-match, counterexample or falsifier. Without that, keep the transfer a hypothesis rather than treating analogy as proof.
15. **Review coverage:** a result based on 13 of 33 files inspected in depth must remain a scoped review; list unread files as UNKNOWN and never upgrade it to a full-PR audit.
16. **Task-local blocker:** after a route is terminal, preserve that result while checking for a separately authorized independent lane. Wait globally only when no admissible useful action remains.
17. **Method activation:** mentioning or linking D019/D020/D021/D022 is insufficient. The task receipt must show which decision the activated rule changed, why the chosen action differed from the prior route, and the evidence for the resulting outcome.
18. **Resource-constrained realization switch:** a terminal acquisition failure such as “No space left on device” closes that exact acquisition attempt, not automatically the objective. Before repeating it, compare the operation and preconditions against the failed attempt. Where the claim is limited to two exact, self-contained source/test files, a smaller API-backed harness may be used only after verifying exact ref, Git blob IDs, byte hashes, dependencies, and the limits imposed by the absent repository configuration. A harness pass supports only the files and execution context actually tested; it must not be promoted to a full-checkout/repository result. A cleanup attempt rejected by policy remains CLEANUP_BLOCKED; do not silently bypass it.

These are documentary acceptance cases. This session did not execute tests, builds or runtime.

## 5. Outcome of this audit and limits

Observed:
- M1B R4 is published in draft PR #555; exact source SHA-256 values were independently computed from remote text and match the R4 values in that PR.
- Claude/Sonnet R2 independently reviewed the exact delta from `6c601c99bb9cc2111f9dde2f6986aefcc0393785` to `c36ee5ed177a3b5afee764c277cc4a8b243594c8` and returned `PASS`, with F-01 and F-02 `CLOSED_BY_STATIC_REVIEW`. The result is limited to the two exact files; the reported Codex pytest results remain `OWNER_REPORTED`, and the residual TOCTOU limitation is unchanged. The full receipt is [M1B F-01/F-02 static review R2](CHAT-ARCH-2026-10-28-M1B-F01-F02-STATIC-REVIEW-R2-RECEIPT.md).
- The original M1B R4 receipt reported 34 passing cases before F-01/F-02. After the exact-head correction at c36ee5ed177a3b5afee764c277cc4a8b243594c8, Codex reports 3/3 focused cases and 37/37 full reader-file cases passing through an API-backed minimal harness. This session independently reconciled the published HEAD and file identities but did not rerun pytest; the result remains OWNER_CODEX_REPORTED, scoped to that harness rather than a full repository checkout. See [the exact-head validation receipt](CHAT-ARCH-2026-10-28-M1B-F01-F02-TARGETED-VALIDATION-RECEIPT.md).
- PR #556 remains a separate M1A source-only parallel line.
- This audit also found that the first M1B route correction left an older `PUBLISH_EXISTING_LOCAL_FILES` action in the historical tail of `CURRENT-STATE.md`. The same PR branch now marks that tail as non-operative history and records the live next action at the top. This is `METHOD_APPLIED` with branch fetch-back evidence for this episode; `LATER_CAUSAL_REUSE=NOT_PROVEN`.
- This method refinement is proposed in the documentation PR branch. It is not yet on `main`, and automatic runtime enforcement is not established.

Security invariants remain untouched:
```text
OPTION_D=RATIFIED_NO_BOOTSTRAP
G1/G2/G3=NOT_ESTABLISHED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
MERGE=NOT_AUTHORIZED
```

**Routing boundary:** this document defines a method; it does not choose the currently active project task. Always consult the newest top entry in `CURRENT-STATE.md`. For the current M1A enrollment work, the existing authenticated fetchback for an existing canonical file is closed, while manifest-specific fetchback is not applicable until a manifest exists; see the current route record. Do not revive this document's historical M1B examples as the active task.

## 6. M1B F-01/F-02 validation and resource-bound method delta (2026-10-28)

The first isolated full clone failed before materializing the two target files because the Windows volumes reported insufficient free space. That is an acquisition/environment failure, not a source-test failure. Repeating the same full clone without changed resource conditions would not be a discriminating action.

Codex switched to a bounded realization: retrieve only the exact reader and test file bytes through the authenticated GitHub API, bind them to the candidate HEAD and Git blob IDs, verify SHA-256, and assemble a minimal package-shaped harness. The focused test then reported 3 passed / 34 deselected, and the entire reader test file reported 37 passed. The harness did not load repository-level pytest configuration; this evidence does not claim a full checkout or full repository test run. The precise receipt captures the commands, environment, hashes, residual cleanup block and evidence labels.

The method change is the important reusable delta: a blocked realization does not automatically close the objective. Choose the smallest valid alternate realization only when its coverage is adequate for the claim, preserve exact-source provenance, disclose environmental/configuration differences, and keep the original failed route closed. Do not bypass cleanup policy to improve the receipt.

This is reported execution evidence from Codex, not an independent pytest rerun in this session. The test result does not address the residual filesystem TOCTOU limitation or establish bridge authority/readiness. This section and D021 remain proposals on the draft documentation branch until authorized integration and canonical fetch-back.

## 7. Independent static delta review R2 (2026-10-28)

Claude/Sonnet reports a read-only static comparison of the exact R1 and R2 contents from GitHub. The declared/current HEAD is `c36ee5ed177a3b5afee764c277cc4a8b243594c8`, base `79ab8c50eaa7518120d5ebed9db4747d395a21cb`; both SHA-256 identities match the published source and test blobs recorded in the detailed receipt.

The reviewer reports that the complete two-file diff consists only of the `parse_constant` rejection function and parser argument in the reader, plus the three-value parametrized test. The `ValueError` falls into the pre-existing R1 fail-closed handler, producing `UNAVAILABLE`, `ARTIFACT_INVALID_OR_UNREADABLE`, and no content. No regressions were found within the reviewed delta.

Disposition: `F01=CLOSED_BY_STATIC_REVIEW`; `F02=CLOSED_BY_STATIC_REVIEW`; `VERDICT=PASS` for the bounded delta. This closes the two R1 findings within the reviewed scope; it does not certify the full reader's security properties or the whole PR.

Evidence boundary: the review did not run pytest or the module. Codex reports the focused three cases and the full reader test file passed in a minimal harness, but those results remain `OWNER_REPORTED` and are not full-repository verification. The harness omitted repository pytest configuration. The `resolve() -> open()` TOCTOU issue remains a previously known residual limitation; the new test lines' exact CRLF/LF status remains `UNKNOWN` in Claude's receipt.

The next project question is not whether to reimplement F-01/F-02. It is the authorized lifecycle decision for the existing candidate and the distinct G1 prerequisites. No static review or passing reader-test result establishes G1/G2/G3, authorizes protected reads, or activates the bridge. This is evidence and method documentation on the draft branch; canonical adoption requires separate authorized integration and main fetch-back.



## 8. Perception, provisional world model, and discriminating feedback (2026-10-29)

This amendment consolidates the organ-level lesson that surfaced after the R2 static review. The failure was not just stale storage: the coordinator had access to multiple records but did not consistently construct a current task-local representation from source identity, temporal validity, causal dependencies and allowed effects before selecting the next action. That diagnosis is an inference from this bounded episode, not a measured claim about every session or a runtime defect finding.

### 8.1 What this organ is responsible for

**Perception** gathers observations from authorized sources and establishes their identity, scope, time and retrieval outcome. **The world model** organizes those observations into a provisional explanation of the task-relevant system: what objects/actors exist, which exact versions are current, how the effective operation reaches its producer/consumer, what dependencies and constraints govern the desired outcome, and which claims remain uncertain.

Memory supplies candidate evidence; it does not decide current truth by recency or repetition. The model must reconcile source revisions, contradictions, current route and prior terminal results. Treat the most recent conversational topic as an observation about conversation order, not proof of the project's active objective. A hypothesis is useful only when it can affect the next decision and exposes an observation that could support or falsify it.

### 8.2 Perception-to-action loop

```text
OWNER OBJECTIVE + ACCEPTANCE ORACLE
  -> exact, authorized observation plan
  -> retrieve relevant sources and bind ref/blob/identity/time/scope
  -> construct minimum task-local state and producer/consumer causal path
  -> distinguish VERIFIED / OWNER_REPORTED / INFERENCE / HYPOTHESIS / UNKNOWN / NOT_RUN
  -> retain plausible rival hypotheses and a falsifier for each material one
  -> identify the first open causal/evidential edge
  -> filter out unauthorized or prerequisite-missing actions
  -> select the smallest discriminating realization and capability-fit actor
  -> observe the actual transition and compare to the acceptance oracle
  -> update the world model, evidence graph, route and owning method
  -> prove later causal reuse before claiming cross-chat learning
```

The loop is objective-conditioned and bounded. It is not a request to scan the whole repository or produce a full digital twin. Expand the model only until it distinguishes the leading explanations, exposes the first open edge, or reaches an explicitly evidenced wait condition. If no admissible observation separates the hypotheses, retain `UNKNOWN` and state the exact missing input.

### 8.3 Minimal world-model receipt

For material tasks and actor handoffs, use the compact fields defined in the living [Space-Time continuity protocol, §3–4](CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md):

- `OBJECTIVE_AND_ACCEPTANCE`: concrete wanted transition and observable acceptance/failure condition.
- `SOURCE_IDENTITY_AND_TIME`: exact repo/ref/commit/blob or other object identity, provenance, event time, observed time and currentness.
- `OBSERVATIONS`: claims actually seen, preserving `VERIFIED` versus `OWNER_REPORTED` and exact coverage.
- `MODEL`: causal/dependency chain, current constraints, competing `HYPOTHESIS` values, predicted observation and falsifier.
- `UNCERTAINTY`: `UNKNOWN` facts, `NOT_RUN` operations, failed acquisition routes and alternative source/realization candidates.
- `FIRST_OPEN_EDGE`: exact unresolved boundary that blocks the outcome; previously closed edges stay closed unless evidence changes.
- `ACTION_CONTRACT`: authorized actor and why that actor fits, exact bounded inputs, side effects/no-go constraints, expected observable and stop/switch condition.
- `RESULT_AND_UPDATE`: what was actually executed/observed/verified, which model claim changed, where the record was written and whether canonical fetch-back occurred.
- `REUSE`: `NOT_PROVEN` until a later non-identical task demonstrates causal reuse and an attributable improvement.

Do not copy the live `ACTIVE_TASK`/`NEXT_ACTION` into the receipt as an alternative authority. Link to `CURRENT-STATE.md`; update the router only through its authorized write path. For handoff prompts, explicitly put `DESTINO: CLAUDE/SONNET` or `DESTINO: CODEX` in the header and give the capability-fit reason; never leave the recipient implicit.

### 8.4 Required interpretation controls

1. **Observation is scoped.** A file fetch proves the fetched bytes at that ref, not that a consumer loaded them. A static code path does not prove the route executed. A reported test run stays `OWNER_REPORTED` until separately verified.
2. **Failure is route-bounded.** Empty/truncated transport response means `RETRIEVAL_FAILED`, not an empty source. Lack of a supported route is not global absence. A task-local authorization blocker is not project-wide paralysis.
3. **Hypotheses make predictions.** When two explanations imply different actions, record what each predicts and test the smallest permitted observation that separates them. Do not use invented numerical confidence to hide missing evidence.
4. **World model and authority are separate.** A better explanation cannot authorize credentials, enrollment, protected reads, code activation, tests/runtime, tunnel or merge. Apply hard authorization and precondition gates before ranking candidate actions.
5. **Writeback is not learning.** Keep `MEMORY_RETRIEVED → METHOD_ACTIVATED → METHOD_APPLIED → OUTCOME_VERIFIED → LATER_CAUSAL_REUSE` as separate claims, each with its own evidence.
6. **Transfer is not analogy-only.** To reuse a rule in another domain, map the semantics, name a non-match/falsifier and seek a domain-specific discriminating observation. Otherwise retain `HYPOTHESIS`.

### 8.5 Acceptance checks for this protocol refinement

- [ ] The current objective and acceptance oracle were set before action selection.
- [ ] Each material claim is linked to an exact source/object revision and observation scope.
- [ ] Reports, inferences, hypotheses, unknowns and unrun actions remain distinct.
- [ ] The model exposes the relevant producer/consumer path, current constraints and first open edge.
- [ ] Material competing hypotheses include predictions and falsifiers.
- [ ] The chosen action is authorized and can reduce the identified uncertainty or close an edge.
- [ ] The expected observation, stop/switch condition and result stage were recorded.
- [ ] Any writeback is fetched back from the exact branch/ref; canonical adoption is not claimed before authorized `main` integration.
- [ ] Later causal reuse remains `NOT_PROVEN` until a non-identical later task shows the method changes a decision and improves the outcome.

These checks are documentation-level acceptance criteria. This PR does not provide runtime enforcement, does not change G1/G2/G3, and does not prove that any later session will retrieve or use the method.

### 8.6 Cross-chat response adjudication and state-transition acceptance

This section makes the cross-chat handoff testable. It tests the operating method, not product code, and cannot establish runtime enforcement or model-weight learning.

**Required transition algorithm**

- Input: the original task contract, last world-model snapshot, live route, and one returned actor receipt.
- Rebind the receipt to the exact target revision, source paths/blobs, scope and evidence stage. If the target differs, mark the old verdict revision-bound and stop any silent retargeting.
- Split the receipt into directly observed source facts, actor-reported execution, inference, hypotheses, unknowns and not-run items.
- Compare the reported outcome with the original acceptance oracle and expected distinguishing observation.
- Decide each claimed edge independently: CLOSED_AT_REVIEW_SCOPE, PARTIAL, OPEN, BLOCKED, or UNKNOWN. A static closure does not imply runtime, integration or authority closure.
- Update the task-local model and preserve prior terminal results. Select one next action from the earliest open edge, after hard authorization and prerequisite filters; name the actor only if its capability and access fit that edge.
- Permit another handoff only after this adjudication is complete. If a receipt is incomplete, request or retrieve only the missing evidence, rather than repeating the whole task.
- Record the transition in the owning receipt/method. Keep branch-only changes candidate-only; only authorized merge plus exact live-main fetch-back establishes canonical adoption.

**Discriminating reasoning cases**

| Input condition | Required model/route update | Prohibited conclusion or action |
|---|---|---|
| Reviewer reports PASS on HEAD A, while the live candidate is now HEAD B | Bind the verdict to A; inspect the delta or re-review only the changed scope on B | Claim that B is reviewed without revalidation |
| Static reviewer closes a source defect; another actor reports tests passed in a reduced harness | Close the source finding at static scope; keep execution status OWNER_REPORTED unless corroborated; retain harness/configuration limits | Promote to full repository, native runtime or authorization pass |
| Targeted action is NOT_RUN because a large checkout ran out of space | Close that acquisition attempt; identify the minimum evidence needed and only then choose an alternate authorized acquisition route | Retry the same full clone without a changed resource/precondition |
| A receipt omits exact target hashes or says tests passed without commands/output/scope | Mark the corresponding claim incomplete/UNKNOWN and seek the precise missing evidence from the producer when feasible | Create a new broad task or infer success from the headline |
| A draft-branch method update is fetched back but main has not changed | Mark writeback verified on branch; retain canonical adoption as NOT_ESTABLISHED | State that all new chats or the product runtime now consume the rule |
| A terminal technical route remains blocked while the Owner explicitly authorizes a documentation-method task | Keep technical route blocked and execute only the bounded documentary task; return to the active technical route afterward | Retry the blocked technical operation or infer new technical authority |

**Acceptance checklist**

- [ ] The returned receipt was reconciled before any new unrelated handoff was prepared.
- [ ] The task identity and exact revision were checked against live refs.
- [ ] Every material result stayed within its demonstrated evidence stage and scope.
- [ ] The original acceptance oracle was explicitly compared with the observed result.
- [ ] The world model records what changed, what did not, contradictions and the first open edge.
- [ ] The next action is the smallest authorized discriminating step, not a duplicate terminal action.
- [ ] The receiving actor is explicitly named with a capability/access rationale.
- [ ] Canonical state and branch proposal are not conflated; later causal reuse remains NOT_PROVEN.

**Pass criterion:** all applicable checks above are satisfied, or each unsatisfied check is explicitly represented as UNKNOWN/NOT_RUN with the exact missing evidence and a justified stop condition. This is a reasoning-method acceptance check only; it does not claim that a later session has consumed the rule or improved its behavior.

### 8.7 Applied adjudication case — Claude M1A Windows reader R1 (2026-10-29)

The return-adjudication gate was applied to `M1A_G1_REMAINING_WINDOWS_SECURITY_SURFACE_STATIC_REVIEW_R1_20261029`. The coordinator rebound the report to live PR #556 HEAD `e1b430956146c4aa0cadc1df2c3df92150b7f7ea`, independently fetched all seven expected Git blobs, inspected the exact overflow branch and `_FILE_STANDARD_INFO` use, and followed the directory-listing result into the server call site. Receipt: [Claude R1 M1A Windows reader adjudication](https://github.com/jhonf463r/Python/blob/codex/iabv-m1a-r7-continuity-r8-20261028/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-M1A-G1-WINDOWS-HANDLE-READER-CLAUDE-R1-ADJUDICATION-RECEIPT.md).

- `F-556-01=STATIC_DEFECT_CONFIRMED`: the cap+1 branch returns `cap` collected names with `truncated=True` before sorting; the caller returns that result. The test file has no cap+1 conformance case. Prior-art contract documents require whole-list denial/no names beyond the 200-entry ceiling; those documents are cited as prior design evidence, not promoted to canonical runtime truth.
- `F-556-02=STATIC_GAP_CONFIRMED`: `NumberOfLinks` is declared but not evaluated after `_FILE_STANDARD_INFO` is queried. The precise native exploitability/containment impact remains `INFERENCE` pending contract-specific and native-Windows validation. Prior-art design requires hard-link denial unless containment is proved.
- `F-556-03=is_sensitive_path` and the private-key possession behavior of external consumers remain `UNKNOWN` in this bounded adjudication. H-01/H-02 are not reopened.
- `TESTS=NOT_RUN`; no source edit, native Windows execution, MCP/runtime, protected read, credential/enrollment, merge, tunnel or bridge activation was performed.
- `FIRST_OPEN_EDGE=F-556-01/F-556-02`. The next useful step is a narrow Codex repair/test handoff on the same PR #556 candidate, but the present coordinator scope is read-only/documentation. Therefore `CODE_CHANGE_AND_TEST_EXECUTION=NOT_AUTHORIZED_IN_THIS_STEP`; prepare the exact bounded task but do not execute source edits or tests until the Owner explicitly authorizes those effects.

This case demonstrates `MEMORY_RETRIEVED` and `METHOD_APPLIED` for this session (the route changed from awaiting Claude to a bounded repair handoff). Branch receipt fetch-back is verified. `RUNTIME_ENFORCEMENT=NOT_PROVEN`, `CANONICAL_ADOPTION=NOT_ESTABLISHED`, and `LATER_CAUSAL_REUSE=NOT_PROVEN`.


### 8.8 Applied adjudication case — Codex local F-556 repair receipt (2026-10-29)

The method was applied to the Owner-provided result for `M1A_G1_F556_01_02_BOUNDED_REPAIR_AND_CONFORMANCE_20261029`. The result reports both focal fixes and 30 targeted tests passing in the existing isolated worktree. The final source/test diff remains local, uncommitted and unavailable to the independent reviewer through GitHub. Receipt: [M1A F-556 Codex local repair](https://github.com/jhonf463r/Python/blob/codex/iabv-m1a-r7-continuity-r8-20261028/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-M1A-G1-F556-01-02-CODEX-LOCAL-REPAIR-RECEIPT.md).

**Adjudication**
- `F-556-01` and `F-556-02` move from `CONFIRMED_STATIC_DEFECT/GAP` to `FIX_REPORTED_LOCAL; INDEPENDENT_DIFF_REVIEW_PENDING`, not CLOSED. The report's code snippet and test summary are not a substitute for reading the exact final diff.
- `30 passed`, environment, SHA-256 values, local Git blob IDs, the CRLF/LF normalization explanation and `git diff --check=0` are `OWNER_CODEX_REPORTED` in this session. Do not relabel them as independently executed or byte-verified.
- The minimal causal gap is artifact visibility, not the absence of another test run: the exact final local bytes must be made visible to a reviewer without mutating or publishing the candidate. Therefore the next action is to print/export the complete two-file unified diff from the existing worktree and review that exact text. Do not rerun the same focused suite unless the diff exposes a specific new concern or the candidate changes.
- The final diff review must verify that cap+1 cannot leak partial names on any path; exactly-cap success remains sorted; `NumberOfLinks` is enforced before the sensitive operation; query failure stays fail-closed; handles close on every rejection path; and `AUTHORIZED_DIRECTORY_ENTRY_LIMIT_EXCEEDED` follows the existing error/response contract. Confirm what caller stubs prove and what they do not.
- Native Windows semantics remain `UNKNOWN`; synthetic native-call simulations do not establish OS-level hard-link containment. No G1/G2/G3, protected-read or bridge claim is elevated.

```text
METHOD_RETRIEVED=VERIFIED_IN_CURRENT_SESSION
METHOD_ACTIVATED=VERIFIED_FOR_RECEIPT_ADJUDICATION
METHOD_APPLIED=NEXT_EDGE_CHANGED_FROM_TEST_RERUN_TO_EXACT_DIFF_VISIBILITY
OUTCOME_VERIFIED=DOCUMENTARY_FETCHBACK_ONLY; LOCAL_TESTS=OWNER_CODEX_REPORTED
F556_01/F556_02=FIX_REPORTED_LOCAL; INDEPENDENT_DIFF_REVIEW_PENDING
NEXT_ACTION=EXPOSE_EXACT_UNIFIED_DIFF; REVIEW_ACTUAL_BYTES; NO_REPEATED_TESTS_WITHOUT_CAUSAL_DELTA
NATIVE_WINDOWS_VALIDATION=NOT_RUN
CANONICAL_MAIN_ADOPTION=NOT_ESTABLISHED
LATER_CAUSAL_REUSE=NOT_PROVEN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
```

This is a second same-session application of the adjudication method, not evidence that a future AI session will reuse it. Cross-session causal reuse remains `NOT_PROVEN`.


### 8.9 Applied adjudication case — Codex's exact F-556 repair diff (2026-10-29)

The Owner then supplied the full patch text previously exported in eight consecutive blocks. It was adjudicated against the original acceptance oracle and the exact shown source changes. Receipt: [Independent static diff adjudication — F-556-01/F-556-02](https://github.com/jhonf463r/Python/blob/codex/iabv-m1a-r7-continuity-r8-20261028/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-M1A-G1-F556-01-02-INDEPENDENT-STATIC-DIFF-ADJUDICATION.md).

- The cap+1 branch raises `AUTHORIZED_DIRECTORY_ENTRY_LIMIT_EXCEEDED` rather than returning accumulated entries. The complete-success path sorts only after enumeration completes. The added synthetic server-stub test asserts the denial response includes no `entries` and no tested secret names. `F556_01=CLOSED_AT_STATIC_REVIEW_SCOPE`.
- `_open_component` now checks `NumberOfLinks != 1` after standard-info query and before accepting the target. The existing exception handler closes the handle on rejection/query failure; synthetic tests cover one-link file success, multi-link denial/closure and metadata query error/closure. `F556_02=CLOSED_AT_STATIC_REVIEW_SCOPE`.
- Codex's `30 passed`, `git diff --check=0`, external patch hash, size and line count remain `OWNER_CODEX_REPORTED`. They were not rerun or recomputed by the static reviewer.
- The source fix is not published to the remote code candidate. The reviewer did not execute tests, native Windows API calls or runtime. The static policy gate is distinct from native conformance.
- The check is applied to directory components as well as files; added tests use a file component, not real Windows directories. Native `NumberOfLinks` observations across supported filesystems and relevant concurrency assumptions remain `UNKNOWN`. Microsoft documents the field as the number of links and says NTFS hard links cannot reference directories, but that doesn't replace platform conformance evidence.
- A few added blank-line markers visibly appear as `+ ` in the pasted diff, while Codex reports a clean `git diff --check`. Without the actual binary artifact in this session, this remains a transport-versus-bytes uncertainty, not a confirmed source defect.

The method correctly changes the state from a generic "diff still needed" to a static-scope disposition and a distinct native-conformance frontier. It does not authorize runtime. This remains another same-session application, not evidence that a later AI session will consume the method or improve behavior.

```text
F556_01=CLOSED_AT_STATIC_REVIEW_SCOPE
F556_02=CLOSED_AT_STATIC_REVIEW_SCOPE
LOCAL_TESTS=30_PASSED; OWNER_CODEX_REPORTED
TESTS_RERUN_BY_REVIEWER=FALSE
PATCH_SHA256_RECOMPUTED=FALSE
NATIVE_WINDOWS_CONFORMANCE=NOT_RUN
NEXT_EDGE=NATIVE_NUMBEROFLINKS_CONFORMANCE_FOR_FILES_AND_DIRECTORIES; AUTHORIZATION_REQUIRED
CANONICAL_MAIN_ADOPTION=NOT_ESTABLISHED
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
LATER_CAUSAL_REUSE=NOT_PROVEN
```


### 8.10 Owner-authorized native link-count conformance probe — pre-execution state (2026-10-29)

The Owner explicitly authorized a single bounded native Windows/filesystem observation after static review closed the F-556 findings at source scope. Exact preconditions, allowed observations and stop conditions are recorded in [M1A native link-count probe authorization](https://github.com/jhonf463r/Python/blob/codex/iabv-m1a-r7-continuity-r8-20261028/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-M1A-G1-NATIVE-LINK-COUNT-CONFORMANCE-AUTHORIZATION.md).

The action was selected for decision-changing information gain: the code checks \`NumberOfLinks != 1\` unconditionally, including directory components. A controlled native fixture can distinguish a successful single-link file path, denial of an actual hard-linked file, and whether ordinary directories are rejected by the same predicate. Microsoft describes \`NumberOfLinks\` as the count of links to the file, and \`CreateHardLink\` is documented as supporting files rather than directories. Native observations must be bound to the actual Windows version, filesystem and exact uncommitted reader bytes; no conclusion can be transferred to other filesystems without evidence.

This is a planned execution, not an observation:
- \`OWNER_AUTHORIZATION=EXPLICIT\`
- \`METHOD_APPLIED=SELECTED_NATIVE_DISCRIMINATING_PROBE_OVER_REPEATING_STATIC_REVIEW\`
- \`NATIVE_PROBE=AUTHORIZED; NOT_RUN_AT_THIS_RECORD\`
- \`SOURCE_CHANGES=FORBIDDEN\`
- \`SERVER/MCP/PROTECTED_READS/CREDENTIALS/ENROLLMENT/TUNNEL/PUBLICATION/MERGE=FORBIDDEN\`
- \`C:\\Python=DO_NOT_TOUCH\`
- \`G1/G2/G3=NOT_ESTABLISHED\`

The controlled fixture is allowed only under a newly created unique TEMP subdirectory and may be removed only after all test-owned handles are closed. If the hard-link API is unsupported or creation fails, the multi-link case is partial, not a pass. If ordinary directories have a native link count other than one and the candidate rejects them, record the compatibility finding and stop; do not change source during this probe. Later causal reuse of this rule remains \`NOT_PROVEN\`.

