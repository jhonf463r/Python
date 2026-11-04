# IABV — Repository Migration, Recovery and Continuity Plan R1

**TASK_ID:** IABV_REPOSITORY_MIGRATION_AND_RECOVERY_R1_20261104  
**Date:** 2026-11-04 (America/Bogota)  
**Owner:** Issue #454 — IABV master objective / repository maintenance control plane  
**Status:** PLAN_RECORDED; REMOTE_BASELINE_PARTIALLY_VERIFIED; LAPTOP_AUDIT_NOT_RUN; MIGRATION_NOT_AUTHORIZED_OR_STARTED  
**Source repository:** jhonf463r/Python  
**Canonical baseline observed:** main=56e4d8b11846a8d8f3cb8cda08efd773ec235651  
**Scope:** preserve the complete monorepo and its evidence/history while establishing an independent, usable development and test route. This is not a request to bypass GitHub account enforcement.

---

## 1. Executive decision

Do **not** transfer or delete the current repository now. First create and verify an independent recovery copy, then test a destination in parallel, and only then decide whether to cut over.

Recommended sequence:

1. Keep jhonf463r/Python as the current canonical source while Support case #4910849 is unresolved.
2. Audit every local clone, worktree, branch, stash, dirty tree, untracked/ignored path, LFS object and relevant local runtime store on the Windows laptop.
3. Create at least one full remote mirror plus an encrypted local recovery copy. Preserve Git refs and non-GitHub data separately.
4. Pilot **GitLab.com as a private secondary destination**, importing GitHub issues/PRs where supported and validating an isolated Windows runner for the exact IABV test set.
5. Keep **Forgejo** as the stronger self-managed/long-term portability option if the Owner is willing to operate a Linux host and runner.
6. Retain GitHub as a possible destination under a properly administered organization only if GitHub Support clarifies that the transfer is permitted and the account-level restriction is resolved through the normal process.
7. Do not switch canonical remotes, close source PRs, delete branches, purge history or make the destination authoritative until the acceptance gates in §9 pass.

A new GitHub personal account must **not** be used merely to evade an account-level billing/platform restriction. Any ownership transfer must be legitimate, policy-compliant and reconciled with Support.

## 2. Verified starting state and evidence boundary

### 2.1 Remote repository

| Item | Observed value | Evidence class |
|---|---|---|
| Repository | jhonf463r/Python | VERIFIED |
| Current visibility | PRIVATE | VERIFIED |
| Default branch | main | VERIFIED |
| Main SHA | 56e4d8b11846a8d8f3cb8cda08efd773ec235651 | VERIFIED |
| GitHub repository size metadata | 269777 KB (~263.5 MiB) | VERIFIED |
| Main recursive tree baseline | 25,689 entries; 17,923 blobs; 525,178,923 bytes; truncated=false | VERIFIED from #454/#605 receipt |
| Main branch protection | protected=false | VERIFIED |
| Local laptop state | Not inspected in this task | UNKNOWN / NOT_RUN |
| Migration destination | Not created | NOT_STARTED |

The root repository is a monorepo. The migration unit is the **whole repository**, not just IABV_v1.5, until a separate dependency-closure review proves a split is safe. Preserve the separate wplay project/domain and other repository areas; do not relabel them as IABV organs.

### 2.2 IABV candidates and current blockers

- PR #591: open Draft; head 01d4e70eac7afd80bde80a6844db784926f57c76; base a64f9e331ccbf13225ed5a3d945e16586e8756db. It has a dedicated focused workflow, but run #41522096790 was blocked before steps by the account-level billing/platform restriction. Its tests remain NOT_RUN.
- PR #602: open Draft; head 7b251c7099b2d90e77300e7edc8a40820a3851d9; base 56e4d8b11846a8d8f3cb8cda08efd773ec235651. Its tests remain NOT_RUN; its changed paths are not covered by a matching workflow on live main.
- #591 and #602 overlap in six central source/test paths. They must be reconciled into one exact-base candidate; do not merge them sequentially.
- Keep both candidates Draft/open/unmerged until that reconciliation and exact-HEAD validation are complete.
- The canonical CURRENT-STATE.md active route remains M1A/G1 root-decision authentication and root-handle provenance, task-local and blocked. That is not a project-wide development stop. Any independent lane still requires its own current Owner objective and authorization.

### 2.3 Support case

Ticket #4910849 received a corrected follow-up email on 2026-11-04. Gmail confirmed the new message is in Sent and in the existing ticket thread. The follow-up asks for the specific restriction, billing retry/authorization outcomes, required remediation, expected restoration and whether the unstarted run incurred charges. No human diagnosis or account-side resolution is yet established.

References:
- Ticket: https://support.github.com/ticket/4910849
- Relevant run: https://github.com/jhonf463r/Python/actions/runs/41522096790
- PR #591: https://github.com/jhonf463r/Python/pull/591
- PR #602: https://github.com/jhonf463r/Python/pull/602

---

## 3. Destination options — current assessment

### Option A — Keep GitHub, but separate canonical ownership from continuity/CI

**Possible form:** transfer the repository to an Owner-controlled GitHub organization or another legitimate account with explicit administrative and billing responsibility, or continue using the current account after Support resolves the restriction.

**Advantages**
- GitHub repository transfer preserves Git history and, according to GitHub's current transfer documentation, issues, pull requests, wiki, stars and watchers; webhooks, services, secrets and deploy keys are listed as remaining associated. LFS objects are moved in the background.
- GitHub remains the closest semantic match for the current PR, review, issue, Actions and automation model.

**Risks / checks**
- A repository transfer is not evidence that an account-level restriction will disappear. Ask Support to confirm the restriction's scope and whether an organization transfer is permitted before acting.
- Do not create another personal account just to get around an enforcement/billing restriction.
- Transferring a private repository to a GitHub Free user or Free organization removes access to features such as protected branches and GitHub Pages. This matters because current main is already unprotected.
- Packages may lose repository links or access depending on registry and permission model. Actions history/logs/artifacts, organization policy, environments, variables, rulesets and integrations must be separately inventoried; do not assume every operational surface migrates.
- An ownership transfer is not a robust independent backup: it remains on GitHub and may remain subject to account/platform policies.

**Disposition:** viable only after Support clarification and target-plan review; not the immediate continuity solution.

Official source: https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository

### Option B — GitLab.com as the first secondary pilot

**Advantages**
- GitLab's GitHub importer supports importing from GitHub.com and can import project work items, including issues, merge requests (the target equivalent of PRs), comments and events. GitLab marks imported items.
- A private destination namespace can be used.
- GitLab.com Free currently provides 400 compute minutes/month for instance runners.
- GitLab Runner has an officially documented Windows installation path. This makes a dedicated Windows test runner a realistic candidate for IABV's Windows-oriented focused test contract.

**Limitations**
- Importing GitHub does not migrate GitHub groups or organizations.
- Not every GitHub item is included by default. Attachments and some old/private Markdown attachments have known import limitations; links/references may need reconciliation.
- GitHub Actions workflow files do not become a validated GitLab pipeline automatically. The test contract must be translated into .gitlab-ci.yml.
- The 400-minute quota applies to GitLab.com instance runners. GitLab documents separate project runners; the exact runner type, security isolation and any quota treatment must be verified in a pilot.
- The GitLab Shell executor is documented but is in maintenance mode and has limited isolation. If used for a temporary Windows runner, run it under an unprivileged dedicated account, on an isolated host/VM, with no Owner secrets or protected local data exposed to jobs.

**Disposition:** **recommended first pilot** for an independently hosted private mirror plus Windows test execution, subject to an importer dry run and runner security review.

Official sources:
- https://docs.gitlab.com/user/project/import/github/
- https://docs.gitlab.com/ci/pipelines/compute_minutes/
- https://docs.gitlab.com/runner/install/windows/
- https://docs.gitlab.com/runner/executors/shell/

### Option C — Forgejo, self-managed or a managed Forgejo host

**Advantages**
- Forgejo is an open-source forge that can be self-hosted; control over the hosting, database and runner can be retained.
- The documented GitHub migrator can import Git history, branches, tags and supported issue/PR metadata, comments, labels, milestones, releases and wiki data. Git LFS migration must be enabled and authenticated.
- Forgejo Actions can run workflows using a separately installed Forgejo Runner. It can read workflows from .forgejo/workflows and may discover .github/workflows when the former is absent.

**Limitations**
- Forgejo Actions is familiar to GitHub Actions users but is explicitly **not designed to be fully compatible**. Each workflow needs a compatibility review and actual run.
- Forgejo needs a runner; the server itself does not execute the jobs.
- The current Forgejo Runner project states that supported/tested architectures and operating systems are Linux amd64 and arm64; Windows support is still listed as work in progress. That makes Forgejo a weaker immediate fit for the current Windows-native test lane unless a Linux test route is independently shown equivalent.
- Self-hosting adds responsibility for backups, upgrades, TLS, access control, monitoring and runner isolation.

**Disposition:** strong long-term independence option if a Linux host/VPS and its operations are acceptable; not the first choice for the immediate Windows Actions replacement.

Official sources:
- https://forgejo.org/docs/latest/user/actions/overview/
- https://forgejo.org/docs/latest/admin/actions/
- https://codeberg.org/forgejo/forgejo-runner

### Option D — Codeberg-hosted Forgejo

Codeberg documents a GitHub migration tool that can bring repository data and supported metadata such as issues, labels, wiki, releases and milestones. It requires an access token for private sources/metadata. It is a community-hosted service, not a substitute for owning the backup. Verify its current project-size, usage and CI policies before selecting it for a large operational monorepo.

**Disposition:** useful for an open-source/community mirror where its policies fit; do not choose it as the only private recovery destination without confirming current eligibility, capacity and CI availability.

Official source: https://docs.codeberg.org/advanced/migrating-repos/

### Option E — Bitbucket Cloud

Current Free limits are up to five users, 50 Pipelines build minutes/month and 1 GB LFS storage. Atlassian also documents a repository-size soft limit of 2 GB and hard limit of 4 GB. There is a material LFS transfer limitation: once a repository has LFS objects, transfer is disabled; creating a new repository and pushing preserves Git history/LFS pointers only if LFS objects are transferred separately, and issue/PR metadata is not copied by that workaround.

**Disposition:** not recommended as the first destination for IABV's current test workload and evidence history.

Official sources:
- https://support.atlassian.com/bitbucket-cloud/docs/limitations-of-bitbucket-pipelines/
- https://support.atlassian.com/bitbucket-cloud/docs/current-limitations-for-git-lfs-with-bitbucket/

### Decision matrix

| Candidate | Git refs/history | Issues/PR metadata | Independent CI | Windows fit | Operational burden | Current disposition |
|---|---|---|---|---|---|---|
| GitHub organization/account transfer | Strong | Strong | Still GitHub | Strong | Low–medium | Wait for Support and plan confirmation |
| GitLab.com | Strong importer | Supported, with known gaps | GitLab CI + Runner | Runner exists for Windows | Medium | First pilot |
| Self-managed Forgejo | Strong migrator/mirror | Supported metadata | Forgejo Actions + Runner | Runner Windows support not established | High | Long-term alternative |
| Codeberg | Supported migrator | Supported metadata | Verify service-specific CI limits | Verify | Medium | Optional secondary mirror |
| Bitbucket Cloud Free | Git import/push | Metadata weak in LFS fallback | 50 min/month Free | Needs validation | Low–medium | Not preferred |

---

## 4. Migration invariants — non-negotiable

1. **No source deletion:** do not delete, archive, rename or transfer the current repository until destination acceptance.
2. **No history rewriting:** no force-push, rebase of unrelated PR branches, filter-repo, squash or mass cleanup during the backup/migration window.
3. **Full monorepo first:** preserve all projects and paths; an IABV-only split requires a separate dependency-closure decision.
4. **Refs are data:** branches, tags, notes, stashes, local branches, remote-tracking refs and candidate heads require inventories. A shallow clone is not sufficient.
5. **Git is not the whole platform:** issues, PRs/reviews, comments, attachments, releases/assets, wiki, projects/discussions, Actions logs/artifacts, packages, webhooks, environments, variables, rulesets and permissions each need their own inventory/export/reconstruction status.
6. **Local state is not remote state:** dirty worktrees, untracked files, ignored files, local databases, LFS caches, local branches, stashes and reflogs may exist only on the laptop.
7. **Sensitive state stays out of migration:** credentials, browser profiles/cookies, OAuth tokens, private keys, local secret stores and raw external-assistant sessions are not to be uploaded to a new forge. Preserve only in encrypted, access-controlled backup where retention is justified; rotate/reissue secrets through their owners.
8. **No guessed completeness:** classify each category as VERIFIED, OWNER_REPORTED, UNKNOWN, NOT_RUN, NOT_APPLICABLE, or BLOCKED.
9. **No account-control circumvention:** a new GitHub account or alternate owner cannot be used to evade a restriction; get Support's direction.
10. **Rollback remains possible:** retain the source repository and encrypted local copy for a defined retention window after cutover.

---

## 5. Phase 0 — remote snapshot and platform inventory

Perform this before importing to any provider.

### 5.1 Git objects and references

From a trusted Windows or Linux machine with current Git:

~~~powershell
git clone --mirror https://github.com/jhonf463r/Python.git Python.git-mirror
Set-Location .\Python.git-mirror

git show-ref --head | Sort-Object | Out-File ..\remote-refs.txt -Encoding utf8
git for-each-ref --format='%(refname) %(objectname) %(objecttype)' |
  Sort-Object | Out-File ..\remote-ref-manifest.txt -Encoding utf8

git bundle create ..\Python-all-advertised-refs.bundle --all
git bundle verify ..\Python-all-advertised-refs.bundle
git fsck --full
~~~

Notes:
- Run the mirror clone from an account authorized to read every intended ref.
- Save the exact command, tool versions, start/end UTC time and exit codes.
- git clone --mirror captures advertised refs, not laptop-only dirty changes, untracked files or ignored data.
- git bundle --all captures reachable refs in that local mirror; it is an additional portable backup, not a replacement for the mirror directory.
- Record any refs that the hosting service does not advertise or that the token cannot read.

### 5.2 Git LFS, submodules and other object systems

~~~powershell
git lfs version
git lfs ls-files --all
git lfs fetch --all origin
git lfs fsck

git submodule status --recursive
~~~

If the repository uses LFS, verify every pointer has a corresponding object and preserve the LFS object store separately. Clone and inventory each submodule at its pinned commit; a superproject mirror alone does not guarantee that external submodule repositories remain accessible.

Also inventory GitHub Packages/registries and other artifact stores. Do not assume package data is part of Git history.

### 5.3 GitHub platform data — separate exports

Create a dated, machine-readable manifest and separately export or record:

- Open/closed issues and their comments, labels, milestones, assignees and events.
- Open/closed PRs, base/head refs and SHAs, review submissions, inline review threads, comments, requested reviewers and merge status.
- Release tags, release notes and binary assets.
- Wiki repository and pages, if enabled.
- Projects/boards, Discussions and attached files, if used.
- Actions workflows, all workflow runs, jobs, check results, annotations, logs and downloadable artifacts while still available.
- Packages and registry artifacts, including owner/scope/permissions.
- Webhooks, deploy keys, GitHub Apps/OAuth integrations, environments, variables, secret names (never secret values), branch rules/rulesets, default branch, repository settings and collaborator permissions.
- Repository size, LFS usage, current visibility, main protection, all branch names/SHAs and tag names/SHAs.

Use native provider export/import tools where possible and retain raw JSON/CSV/ZIP outputs with a manifest. GitHub's repository transfer and GitLab import do not imply that every GitHub-only feature or CI record is portable.

---

## 6. Phase 1 — Windows laptop forensic audit and recovery capture

**Current status: NOT RUN.** No direct inspection of the laptop or its drives has occurred in this task. Do not mark this phase complete until the Owner or an authorized local operator returns the manifests and checksums.

### 6.1 Locate all workspaces

At minimum, inspect the known historical locations if they still exist, then search the Owner's development roots:

- C:\Python\IABV_v1.5
- C:\Temp\IABV_TASKSCOPED_APPROVAL\IABV_v1.5 (historical candidate workspace; existence/currentness unknown)
- Other clones/worktrees under the Owner's source/repository folders, Desktop/Documents and any secondary drive.

A read-only helper is included at:

**IABV_v1.5/tools/migration/Invoke-IabvLocalInventory.ps1**

Review its source before running. It inventories repository paths, HEAD, branches, refs, reflogs, worktrees, stashes, dirty status, untracked/ignored paths, object-store size, LFS pointers, submodules and sanitized remotes. It writes a JSON metadata report only; it does not read source-file contents, copy or archive repositories, fetch/push, download LFS objects, upload data or clean working trees. The optional **-RunFsck** switch performs a read-only unreachable-object check and may take longer.

Example (run from PowerShell after reviewing the helper source):

~~~powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\IABV_v1.5\tools\migration\Invoke-IabvLocalInventory.ps1
# After inspecting the first report, optionally repeat with:
.\IABV_v1.5\tools\migration\Invoke-IabvLocalInventory.ps1 -RunFsck
~~~

The helper is source-reviewed/fetched back but has **not** been executed on the Owner's laptop or validated in Windows PowerShell. Keep its output local and private; untracked/ignored filenames and ref names can disclose sensitive project context. Sanitize before sharing. This helper is an inventory, not a backup.

Do not assume these paths are current. Inventory all discovered .git directories **and** .git worktree pointer files. In every common Git directory, record:

~~~powershell
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git rev-parse HEAD
git branch -avv
git tag --list
git remote -v
git status --porcelain=v2 --branch
git worktree list --porcelain
git stash list
git reflog --all --date=iso
git count-objects -vH
git fsck --full --no-reflogs --unreachable
~~~

Sanitize remote URLs before putting them in a manifest. Never preserve embedded username/password/token values in the report.

### 6.2 Capture state that a normal push misses

For each local repository/worktree:

- Preserve current HEAD and branch name.
- Capture staged and unstaged tracked changes separately (git diff --cached --binary, git diff --binary).
- Inventory every untracked and ignored path. Do not silently exclude ignored files: some may be fixtures or uncommitted project knowledge.
- Preserve stash entries and reflogs; inspect unreachable-object reports before any cleanup.
- Preserve local branches and remotes not present on GitHub.
- Copy each worktree and its common Git directory into an encrypted offline recovery archive before changing remotes or cleaning anything.
- Record LFS objects available locally and their hashes/availability.
- Record submodules and their worktree status.
- Note local config differences without copying credentials, access tokens or credential-helper data.

Do not run git clean, reset --hard, gc --prune, branch deletion, worktree removal, or any cleanup during the audit.

### 6.3 Classify non-Git data

Use the existing #605 inventory as the starting index, not as permission to delete or bulk-upload:

- data/evolution/: persisted evolution/session/dossier data with consumers. Preserve until provenance, sensitivity and restore requirements are mapped.
- data/test_runs/: tracked test workspaces and generated runs. Some contents may be evidence/fixtures; some may carry potentially sensitive session or browser context. Do not blanket-delete or import unreviewed payloads.
- .vendor_deps/ and .vendor_pytest/: consumers/provenance remain unresolved. Preserve in the recovery copy until a clean-install and compatibility test proves whether they are needed.
- .tmp_tests/, tmp_*, audit_live_workspace*/: producer, consumer and retention are not fully established. Preserve as classified evidence until reviewed.
- Browser profiles, cookie stores, external-assistant profiles, local credentials, screenshots and raw logs: treat as potentially sensitive. Do not upload these to GitLab, Forgejo, Codeberg, Bitbucket or another GitHub account.
- SQLite databases: identify the application and writers before copying. For SQLite/WAL databases, use a database-consistent backup while the application is stopped or via SQLite's online backup mechanism; do not copy a live DB file and assume WAL state is captured.
- Model files, Ollama caches and other large local dependencies: record path, size, version and reproducibility. Do not upload caches until licensing, provenance and need are established.

### 6.4 Recovery archive design

Create two different outputs:

**A. Encrypted raw recovery archive (offline / restricted):** full local clones, common Git directories, worktrees, dirty trees, local branches, stashes, ignored/untracked data and only the local operational data that is justified for retention. Encrypt before moving it off the laptop. Never put this raw archive in a public or ordinary project repository.

**B. Sanitized migration manifest (shareable with the Owner / destination):** paths, sizes, hashes, repo identity, refs/SHAs, classifications, source owner, sensitivity class, restore instruction and whether the item is eligible for upload. Do not include secret contents, browser cookies, tokens, private keys or raw user conversation payloads.

Generate SHA-256 checksums for every archive and manifest. Store the manifest beside the archive and in a separate backup location.

### 6.5 Backup topology

Use a 3-2-1 style target where practical:
- one encrypted local copy on a separate physical drive;
- one second independent copy in a different location/provider under private access;
- one working source that remains unchanged until migration acceptance.

A mirror on a second forge is not an independent backup if it shares the same laptop credentials or if the mirror is the only copy. Verify archive decryption and bundle restoration on a separate folder/device.

---

## 7. Phase 2 — destination pilot (no canonical cutover)

### 7.1 GitLab.com pilot

1. Create a **private** destination project in an Owner-controlled namespace.
2. Run GitLab's GitHub importer on the private source; authorize only the migration scope required.
3. Record imported issue/PR/comment/label/milestone counts and all import warnings.
4. Export/import any missed attachments, releases, wiki, Projects/Discussions and other metadata separately.
5. Compare all branch/tag names and commit SHAs against the source manifest. Check LFS object completeness.
6. Create a GitLab CI pipeline for the exact four focused suites currently associated with #591:
   - test_canonical_work_queue.py
   - test_control_master_signal_projector.py
   - test_system_prompt_builder.py
   - test_evolution_center_viewmodel.py
7. Use an isolated Windows runner only after its service account, executor, permissions, workspace cleanup and secrets boundary have been reviewed. Start with no deployment credentials and no production access.
8. Run tests on the exact reconciled candidate SHA, store complete logs/artifacts and publish a receipt mapping commit SHA → runner identity/version → environment → command → exit code → test results.
9. Keep imported PRs as historical records or explicitly map them to the reconciled candidate; do not blindly merge imported PRs.

### 7.2 Forgejo pilot

If selected later:
1. Stand up a private Forgejo instance on a maintained Linux host/VPS with TLS, backups, updates and administrative access.
2. Import repository and supported metadata using Forgejo's GitHub migrator; separately verify LFS, attachments and release assets.
3. Install a supported Linux Forgejo Runner; test current workflows and adapt them because Forgejo Actions is not fully GitHub Actions compatible.
4. Do not claim the Windows-specific suite passes from a Linux-only runner unless the required Windows behavior has been isolated and separately verified.
5. Test restore from a Forgejo backup plus Git mirror.

---

## 8. Phase 3 — final cutover (not authorized yet)

Cutover is a separate Owner decision after Phases 0–2 have evidence.

1. Announce a short write freeze; stop new pushes and PR updates for the agreed cutover window.
2. Take a final mirror/bundle and final local dirty-state snapshot.
3. Push final refs and LFS objects to the destination; re-run exact ref comparison.
4. Import/export final issue/PR comments, reviews, attachments and releases created since the first import.
5. Verify branch rules, default branch, CI variables/secrets (reissued from the secret owner, never copied from a raw dump), deploy keys, webhooks, Apps, registry access and permissions.
6. Update every local clone's origin only after the destination is accepted; keep the previous origin as a named read-only remote during transition.
7. Run a clean clone from the destination, install from declared package metadata, execute focused tests, then broader test suites and runtime smoke tests.
8. Leave the original GitHub repository private and read-only as a rollback/archive source for an Owner-approved retention period. Do not delete it during cutover.
9. Close or retarget old PRs only after each one has a documented disposition and its branch/commit evidence is preserved.

Rollback trigger: a missing ref/commit/LFS object, lost issue/PR discussion needed for traceability, failed restore, inability to reproduce the accepted test, incorrect permissions or unresolved provenance gap. Roll back by returning to the preserved source remote; do not rewrite history to hide the mismatch.

---

## 9. Acceptance gates and migration ledger

No cutover until all applicable rows pass:

| Gate | Acceptance evidence | Current status |
|---|---|---|
| G0 — Source identity | Main SHA, tree SHA, repo visibility, source URL | PARTIAL_VERIFIED |
| G1 — Remote refs | Full branch/tag/ref manifest and destination SHA parity | NOT_RUN |
| G2 — Local recovery | All laptop clones/worktrees/dirty/untracked/ignored/stashes/reflogs inventoried | NOT_RUN |
| G3 — LFS/submodules | Object-level completeness and submodule commit map | UNKNOWN |
| G4 — Platform metadata | Issues, PRs, reviews, comments, releases, wiki, boards, artifacts inventory | PARTIAL; EXPORT_NOT_RUN |
| G5 — Sensitive data | Classification, encrypted raw backup, sanitized export manifest | NOT_RUN |
| G6 — Destination | Private project, access control, runner, restore tested | NOT_STARTED |
| G7 — Exact-HEAD tests | Four focused suites run and fetch-back receipt on exact candidate SHA | NOT_RUN |
| G8 — Reproducible build | Clean clone install/build/runtime result | NOT_RUN |
| G9 — Cutover | Final delta sync, remote update, rollback proof, Owner approval | NOT_AUTHORIZED |

Required manifest fields:

~~~text
MIGRATION_RECEIPT:
  task_id
  source_repository
  source_visibility
  source_main_sha
  source_tree_sha
  observed_at_utc
  source_refs_manifest_sha256
  local_workspaces_manifest_sha256
  local_archive_sha256
  git_bundle_sha256
  lfs_manifest_sha256
  submodule_manifest_sha256
  platform_metadata_manifest_sha256
  sensitive_data_classification_ref
  destination_provider_and_project
  destination_visibility
  imported_refs_and_sha_parity
  imported_metadata_counts_and_exceptions
  CI_runner_identity_and_version
  exact_candidate_sha
  test_commands_and_exit_codes
  restore_test_result
  rollback_remote
  owner_cutover_authorization
  acceptance_status
~~~

---

## 10. Immediate next actions

1. Keep #591 and #602 open Draft; freeze their semantics and do not trigger more GitHub Actions while the restriction is unchanged.
2. Await GitHub Support's specific response to #4910849; do not create a new GitHub identity to bypass the restriction.
3. Start Phase 0 from a trusted machine and collect a complete remote refs/LFS/platform manifest.
4. Run Phase 1 locally on the Windows laptop; the laptop audit is the critical missing evidence. Return the sanitized manifests and checksum report before any upload or cleanup.
5. Only after the local inventory, decide whether GitLab.com is enough or whether a managed/self-hosted Forgejo mirror is also warranted.
6. The first destination remains a **secondary private mirror and test pilot**, not the new canonical source. Decide canonical cutover only after all acceptance gates pass.

## 11. Explicit non-actions and current status

~~~text
SUPPORT_4910849=FOLLOWUP_SENT_2026-11-04; HUMAN_DIAGNOSIS_PENDING
CURRENT_GITHUB_REPOSITORY=PRIVATE; PRESERVED
MAIN=56e4d8b11846a8d8f3cb8cda08efd773ec235651; NOT_MODIFIED
MAIN_PROTECTION=UNPROTECTED; NO_SETTING_CHANGED
PR591=OPEN_DRAFT; TESTS_NOT_RUN
PR602=OPEN_DRAFT; TESTS_NOT_RUN
LAPTOP_AUDIT=NOT_RUN
REMOTE_MIRROR=NOT_CREATED
DESTINATION_REPOSITORY=NOT_CREATED
GIT_LFS_COMPLETENESS=UNKNOWN
LOCAL_DIRTY_OR_UNTRACKED_STATE=UNKNOWN
MIGRATION=NOT_STARTED
CANONICAL_CUTOVER=NOT_AUTHORIZED
HISTORY_PURGE=NOT_AUTHORIZED
SECRET_OR_PROFILE_UPLOAD=NOT_AUTHORIZED
~~~

---

## 12. External documentation checked (2026-11-04)

- GitHub repository transfer: https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository
- GitLab GitHub importer: https://docs.gitlab.com/user/project/import/github/
- GitLab compute minutes: https://docs.gitlab.com/ci/pipelines/compute_minutes/
- GitLab Runner on Windows: https://docs.gitlab.com/runner/install/windows/
- GitLab Shell executor: https://docs.gitlab.com/runner/executors/shell/
- Forgejo Actions: https://forgejo.org/docs/latest/user/actions/overview/
- Forgejo Runner supported architectures: https://codeberg.org/forgejo/forgejo-runner
- Codeberg migration: https://docs.codeberg.org/advanced/migrating-repos/
- Bitbucket Pipelines limitations: https://support.atlassian.com/bitbucket-cloud/docs/limitations-of-bitbucket-pipelines/
- Bitbucket LFS transfer limitations: https://support.atlassian.com/bitbucket-cloud/docs/current-limitations-for-git-lfs-with-bitbucket/

This record is a migration plan and continuity handoff. It is not evidence that a laptop backup exists, a migration was executed, an alternate runner passed, a provider import is complete, or a canonical cutover was authorized.
