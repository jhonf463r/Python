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
2. Read `README.md`, then `CURRENT-STATE.md`, then `CONTEXT-INDEX.md`, then `MEMORY-OPERATING-PROTOCOL.md`; retrieve only the objective-relevant protocol lineage after that.
3. Bind each read to the exact ref and blob. If the normal file endpoint returns empty content unexpectedly, fetch the identified blob. Empty transport output is `RETRIEVAL_FAILED`, not an empty canonical state.
4. Treat `CURRENT-STATE.md` as the only routing authority. Other entry blocks are navigational snapshots; repeated stale copies do not gain authority by majority.

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

## 4. Acceptance tests for the method (reasoning checks, not product tests)

1. **Existing publication:** when PR #555 already contains the candidate, select reuse/review; do not ask Codex to publish a duplicate.
2. **Cross-revision hashes:** when R3 and R4 hashes differ but the current local hashes match the R4 remote source, classify `DIFFERENT_REVISION`, not source divergence.
3. **Empty read:** if a normal contents response is empty but the blob is readable, record endpoint failure and use the exact blob.
4. **Stale entry snapshots:** if README/MOP/AGENTS disagree with the live canonical route, follow CURRENT-STATE and reconcile stale snapshots before selecting an action.
5. **Actions without jobs:** workflow `startup_failure` with an empty jobs list means no test execution is evidenced; preserve `TESTS=NOT_RUN`.
6. **Draft writeback:** changes on a PR branch remain proposed until reviewed/integrated under authorization and fetched back from main.

These are documentary acceptance cases. This session did not execute tests, builds or runtime.

## 5. Outcome of this audit and limits

Observed:
- M1B R4 is published in draft PR #555; exact source SHA-256 values were independently computed from remote text and match the R4 values in that PR.
- PR #555 has a static review reporting no blocking functional defect and recording residual limitations.
- M1B's 34 targeted passing tests remain `OWNER_CODEX_REPORTED`; not rerun here.
- PR #556 remains a separate M1A source-only parallel line.
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

**Next operational edge:** reuse PR #555 and its recorded review/limitations; do not republish or re-run unchanged tests. Any integration decision remains separate and unauthorized by this method document.
