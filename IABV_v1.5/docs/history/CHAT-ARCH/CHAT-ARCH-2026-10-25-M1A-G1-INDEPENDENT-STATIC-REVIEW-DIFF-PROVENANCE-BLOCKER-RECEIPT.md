# M1A G1 — Independent candidate diff review and provenance blocker receipt

- Date: 2026-10-25, America/Bogota.
- Task reviewed: `M1A_G1_INDEPENDENT_STATIC_REVIEW_OF_INTEGRATED_ORGAN_CANDIDATE_20261025`.
- Review disposition: `PARTIAL_STATIC_REVIEW; ACCEPTANCE_BLOCKED_BY_UNRECONCILED_PRETASK_BASELINE`.
- Live-main baseline observed before this documentary update: `74b47561ebddfc113bd8cf869430c3991f206003`.
- Scope: inspect the Owner-supplied ZIP, verify bytes, inspect the unified diff and compare its provenance metadata against the declared Git base. No product source was changed. No tests, build, runtime, MCP or real transport were run.

## 1. Evidence integrity verified

Received artifact: `IABV_G1_STATIC_REVIEW_DIFF_20261025_4e84c57215e140c69edb8a191dc73b57.zip`.

- ZIP size: 118,788 bytes.
- ZIP SHA-256: `915efa1541aab2546522261a8c60bfa00e4004809156cdd5cfd50b01f9620c33`.
- Members: `candidate-vs-pretask-checkout.diff` and `manifest.json`.
- Diff size: 117,226 bytes.
- Diff SHA-256: `6950fb87dcd6f57573f88bbd58b0b880bd0437e69eb5830d9f55a22ad9aa5f93`.
- The diff digest matches the expected digest recorded in the manifest and the Owner's message.

This establishes byte identity of the received artifact, not source ancestry, correctness, security or test execution.

## 2. What the diff actually contains

- Eight changed file paths.
- The diff file contains 2,427 physical lines.
- Counting diff line markers yields 473 added lines and 156 deleted lines; these are patch counts, not a test or quality score.
- The `diff --git` / `---` / `+++` headers embed absolute paths under two Windows temporary directories rather than repository-relative paths.
- The artifact does not contain the complete pre-task checkout, a Git bundle, or a per-file source snapshot that would let this reviewer reconstruct the exact old-side tree independently.

The earlier UI summary of four files / +33/-12 does not describe the contents observed in this ZIP. An earlier report's 2,411-line count also differs from the 2,427 physical lines counted in the received patch. Preserve these as unreconciled prior summaries; do not silently substitute them for the observed counts.

## 3. Baseline/provenance blocker

The manifest reports:
- Candidate branch: `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`.
- Candidate HEAD: `6bc568e1c5a898afd65cc045c779c25a9cdc5489`.
- Declared base revision: `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`.
- Basis: merge-base against local `refs/remotes/origin/main`, which the manifest says was `2cecd5e9b9e175584d65bbb1198a53bc2346d095`.
- Live `main` at packaging: `74b47561ebddfc113bd8cf869430c3991f206003`.

The candidate HEAD was not available as a commit through the GitHub connector when queried. The old-side abbreviated index identifiers in the patch also do not match the queried tracked blobs for several paths at the declared base, and some old-side paths are absent from that Git tree. Because the patch was generated from a temporary pre-task directory and no corresponding complete pre-task source tree was included, this does **not** prove corruption or intentional alteration. It means the declared base-to-patch relationship cannot be independently established from this packet. Line-ending normalization, a sparse/local checkout, pre-existing worktree changes, or an incorrectly stated base must be distinguished by the producer rather than guessed by the reviewer.

Disposition: `PRETASK_BASELINE_UNRECONCILED`. The patch can be inspected as an artifact, but it is not yet an accepted, reproducible repository-relative candidate diff.

## 4. Bounded static observations

The diff appears to strengthen authorization-to-open-object binding, trusted-root/policy binding and fail-closed handling in replay protection, and it removes an explicit disabling of MCP DNS-rebinding protection. These are promising source-level changes, not proof that the implementation is correct or that a trusted authority is provisioned.

A concurrency test that relies on a fixed short sleep is not a deterministic proof that the competing operation reached its intended wait state. This is a test-design observation only; no test was executed here.

The source still does not establish a productive approved-workspace-root provider or an independent trust root. No positive protected-read authority is established by this diff review.

## 5. Required next action — one producer-generated corrected evidence package

Use the existing Windows Codex session that owns the temporary checkouts. Do not ask the Owner to rebuild the patch manually.

The producer should:
1. Inspect, read-only, the exact pre-task and candidate directories named by the manifest.
2. Record full `git rev-parse HEAD`, branch/ref, merge-base, `git status --short --branch`, and whether each path is tracked, staged, unstaged, untracked or ignored. Preserve and separately hash any pre-existing staged/unstaged diffs; do not fold them into the candidate diff.
3. Determine whether the true comparison is commit-to-commit, commit-to-working-tree or tree-to-tree. State the exact endpoints and evidence. Do not label `fed7d509...` as the source baseline unless the source tree actually corresponds to it.
4. Produce a repository-relative, full-index, binary-capable unified diff from the verified endpoints. Include per-file status and `--stat` / `--numstat` output so counts reconcile.
5. Package one ZIP outside all checkouts containing the corrected diff, manifest, small provenance report and necessary non-secret source/identity evidence for the eight paths. Do not publish the evidence package or dirty-worktree material to public GitHub.
6. Recompute ZIP/member SHA-256 values after packaging and stop if the base/candidate relationship remains unprovable.

This is evidence packaging only: no source edit, test, build, runtime, MCP, transport, commit, push or merge is authorized by this receipt.

## 6. Gate and routing state

```text
ZIP_INTEGRITY=VERIFIED
DIFF_BYTES=VERIFIED
PATCH_CONTENT_REVIEW=PARTIAL
PRETASK_BASELINE_PROVENANCE=UNRECONCILED
CANDIDATE_ACCEPTED=FALSE
CODEX_REPORTED_TESTS=264_PASS; NOT_INDEPENDENTLY_VERIFIED
TESTS_RUN_BY_THIS_REVIEW=FALSE
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=ONE_CORRECTED_PRODUCER_GENERATED_DIFF_PROVENANCE_PACKAGE
```

This receipt updates evidence custody and the next routing decision only. It does not accept the candidate, certify the implementation, dispatch Codex, or close a trust gate.
