# M1A G1 — Independent clone and working-tree divergence diagnostic receipt

- Date/time reported by the producing Windows Codex session: 2026-10-25, 3:44 PM America/Bogota.
- Task: `M1A_G1_DIAGNOSE_SHARED_CHECKOUT_AND_FILESYNC_RELATIONSHIP_20261025`.
- Result: `INDEPENDENT_REPOSITORIES_CONFIRMED`; `WORKTREE_CHANGES_EXPLAINED`.
- Source of local observations: Owner-supplied Codex diagnostic report. ChatGPT did not access the two local Windows directories or independently inspect their NTFS metadata.
- Scope: reconcile the local checkout/filesystem evidence and define the next bounded evidence action. No source or Git state was changed by the reported diagnostic. Tests/build/runtime/MCP/real transport were not run.

## 1. Confirmed by the producer's report

The two temporary directories are independent Git repositories/clones, with separate `.git` directories and Git common directories. Each `git worktree list --porcelain` reportedly lists only its own checkout. Both report branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, HEAD `6bc568e1c5a898afd65cc045c779c25a9cdc5489`, and merge-base with local `origin/main` `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`.

For the six tracked paths in the eight-row table, index blob IDs and file modes reportedly match across clones. Two additional paths are untracked (`??`) in both and therefore have no index entry. All eight listed working-tree file contents differ between the clones, and their NTFS file identifiers differ. No relevant reparse point/junction/symlink was observed in the inspected paths.

The statuses include `M`, `MM`, `AM` and `??`. The report says the staged diffs for three `MM` paths were identical, but names `github_owner_merge_bootstrap.py` as the third path while its eight-row table lists only two `MM` paths. This path inventory mismatch must be reconciled in the next package; do not omit the named file or assume it is a typo.

## 2. Interpretation — keep facts separate from hypotheses

The evidence explains the present divergence as different working-tree contents in two independent clones, despite matching indexed content for tracked paths. The same HEAD and index do not mean the live files are shared or byte-identical. The observed difference is compatible with distinct unstaged edits and untracked files.

The report did not establish who created the differences or when. It does not prove the labelled pre-task tree was an unchanged snapshot captured before candidate work, so it cannot establish the historical task-only delta or authenticate `fed7d509...` as the base of the original diff.

Dropbox or another synchronization mechanism remains `UNKNOWN`. The local configuration locations inspected did not reveal a Dropbox root, but no general synchronization-service investigation was completed. Distinct NTFS identifiers and separate Git directories argue against the pairs being the same physical files or a shared Git worktree; they do not prove that no copying or synchronization ever occurred.

## 3. Next bounded action — one current directory-to-directory evidence package

Do not repeat the Dropbox search, broad repository inventory, implementation or tests. Use the same Windows Codex session that can read both surviving directories.

Produce one ZIP outside both clones containing:
1. A repository-relative working-tree delta between the two directories for the union of **all** paths reported by `git status --porcelain=v2 --untracked-files=all` in either clone. Include the separately mentioned `github_owner_merge_bootstrap.py` if present.
2. A reconciled path table for both clones: tracked/staged/unstaged/untracked status, index blob/mode when present, current working-tree content hash, existence and result of direct pairwise comparison.
3. The staged and unstaged diff from each clone as separate named members, plus identities/status summaries for both clone roots. Keep the original staged/unstaged preservation data separate; do not combine them into the candidate delta.
4. An explicit statement of comparison semantics: this is a delta between the **currently observed, pre-task-labelled and candidate-labelled directory contents**, not proof of a historical task-only diff unless a contemporaneous provenance receipt establishes that.
5. A manifest with member sizes and SHA-256 values, plus the original ZIP/diff SHA-256 identifiers for reference. Do not alter or replace the original artifact.

Stop if either directory or a needed file has disappeared. Do not reconstruct missing files or silently choose a new base. No source edit, tests, build, runtime, MCP, transport, commit, push, merge or gate change is authorized by this diagnostic.

## 4. Canonical state to preserve

```text
DIAGNOSTIC=INDEPENDENT_REPOSITORIES_CONFIRMED; WORKTREE_CHANGES_EXPLAINED
INDEX_CONTENTS=REPORTED_IDENTICAL_FOR_SIX_TRACKED_PATHS
WORKTREE_CONTENTS=REPORTED_DIFFERENT_FOR_ALL_EIGHT_LISTED_PATHS
UNTRACKED_PATHS=2_REPORTED
FILESYSTEM_ALIAS=NOT_OBSERVED_IN_INSPECTED_PATHS
DROPBOX_OR_SYNC=UNKNOWN
PATH_INVENTORY=RECONCILE_GITHUB_OWNER_MERGE_BOOTSTRAP_PY_MENTION
HISTORICAL_PRETASK_TREE=UNVERIFIED
ORIGINAL_ZIP_AND_DIFF=KEEP_BYTE_IDENTICAL
NEXT_ACTION=PRODUCER_GENERATE_ONE_CURRENT_DIRECTORY_TO_DIRECTORY_DELTA_AND_PRESERVATION_PACKAGE
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTOMATIC_FOLLOW_ON=FALSE
```

This receipt records producer-reported local findings and a safer next evidence action; it does not independently authenticate the local report or accept the candidate.
