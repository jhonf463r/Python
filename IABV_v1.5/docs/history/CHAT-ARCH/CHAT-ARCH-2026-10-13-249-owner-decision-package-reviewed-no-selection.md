# CHAT-ARCH-2026-10-13-249 — Owner decision package reviewed; no home/auth option selected

- **Episode ID:** `CHAT-ARCH-2026-10-13-249`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline verified at intake:** `main @ d2fcbd3ecf43e08d2341c3851af74bb7be6614fd`
- **Input:** Owner-supplied decision-package report with remote-state and local-worktree claims
- **Related records:** entries 246–248.
- **Adjudication:** `CODEX_EXEC_OWNER_DECISION_PACKAGE_REVIEWED_NO_SELECTION`
- **First open edge:** `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`

## 1. Remote continuity and local provenance

This writer independently fetched the current GitHub default branch and canonical surfaces before this writeback. The remote main tip at intake is `d2fcbd3ecf43e08d2341c3851af74bb7be6614fd`, which matches the supplied report's remote SHA. The repository's latest entry 248 records design readiness, not implementation authorization.

Owner-supplied local checkout state:
- branch `codex/m0a-safe-ui-boot`;
- HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`;
- HEAD tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`;
- 56 tracked modified files and 6 untracked files.

This writer did not inspect the local checkout or independently observe its status. Preserve every dirty/untracked file, including `.pyc` changes. The older checkout's lack of entry 247/248 does not imply those records are absent from remote main.

## 2. Review of the decision package

The supplied package is consistent with the canonical decision boundary and is accepted as a **decision package**, not an actual Owner selection. It clearly keeps separate:
- the existing App Server path, which is integrated but not proven to provide a bounded coding/diff handoff;
- the installed CLI candidate, whose existence does not imply an IABV `exec` integration;
- the future home/authentication policy, which remains unselected and unproven;
- effective Windows confinement, no-extra-spend eligibility, output artifact production and consumer evaluation, each of which is a separate gate.

The report presents options A (existing authenticated home), B (already-existing dedicated authenticated home) and C (keep the route blocked). It **does not select one** on behalf of the Owner. No response explicitly approving A, B or C was included in the input. Therefore the Owner decision remains pending; do not interpret the report or this writeback as consent to implementation.

## 3. Technical adjudication

Current recommendation: retain the block until an Owner-approved, already-existing home/authentication pattern can satisfy the requirements without credential copying, new login/OAuth, installation or additional spend, and until effective OS-enforced confinement is demonstrable.

Option B is only a conditional preference if an already-existing dedicated authenticated home is proven to exist and meet all constraints. The package does not show that such a home exists. Option A also remains unselected and unproven; it requires a clear Owner decision and evidence that the chosen isolation boundary protects sensitive resources. Option C is the safe default while the decision/evidence is absent, but this is not a permanent architectural conclusion that the route can never work.

Do not inspect credential/session contents to choose an option. Authentication availability, plan entitlement, quota, cost, effective Windows sandbox, external integration policy and verified artifact handoff remain `UNPROVEN`.

## 4. First open edge and smallest next action

**First open edge:** `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`.

The next necessary input is an explicit Owner adjudication of one of these states:

- **A — conditional permission to consider an existing authenticated home**, only within an approved, demonstrably effective security boundary;
- **B — permission to consider an already-existing dedicated authenticated home**, provided it already exists and requires no credential copying, new login, install or extra spend;
- **C — maintain the block unless A or B can be proven compatible with all constraints.**

Even after A or B is selected, that selection is *not* permission to implement, run preflight, launch a CLI, start a coding turn, inspect secrets, or spend. Those stages require separate scope/authorization as described in entry 248. The candidate root/baseline, allowed commands and network/integrations, effective-confinement acceptance criteria, and independent consumer/verifier must then be specified.

## 5. Non-authorization and learning boundary

No implementation, CLI/App Server process, agent turn, test/build, credential/session inspection, installation, OAuth/API setup, network action beyond canonical repository read/write, extra spend, local file/config mutation, commit/push of product code or promotion is authorized by this record. The documentation writeback itself is not evidence of runtime operation, automatic model learning or causal reuse.
