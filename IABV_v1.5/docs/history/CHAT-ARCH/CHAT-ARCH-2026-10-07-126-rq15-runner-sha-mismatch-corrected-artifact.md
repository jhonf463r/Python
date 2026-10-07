# CHAT-ARCH-2026-10-07-126 — RQ15 RUNNER SHA MISMATCH / NEW CORRECTED ARTIFACT

## Classification

`RECONCILIATION / ROUTING / EXPERIMENT-READINESS / PROVENANCE / SYMBIOSIS`

## Trigger

Devin reached the RQ15 execution gate and correctly stopped before runtime because the artifact on disk did not match the runner SHA explicitly bound by the current authorization.

## FACT

Authorized runner SHA:
`E70D9215B4528ECBC315C0DCA0953AD832071F2E57FB255003698569072F5485`

Runner currently present:
`E231D144714115478DA3B0FCCF5FEC0EE0D7FCC0193E0D21977A90E5058CC15E`

The current runner is reported to be a corrected revision of the previous runner, changing the tree-provenance check from `git rev-parse HEAD^{tree}` to `git cat-file -p HEAD`.

Target provenance remains:
- HEAD `8425f03eb45abd11951938f6e3234459c1585b55`
- tree `1d46e59195d01c1cec6806f264ef75f31541e806`
- clean worktree.

No runtime, oracle, sensor or IABV activity occurred.

## CLASSIFICATION

`RQ15 BLOCKED AT RUNNER IDENTITY / AUTHORIZATION MATCH`

The mismatch is a precondition failure, not sensor evidence.

The corrected runner must be treated as a new experimental artifact. Its new SHA cannot inherit the authorization bound to `E70D...`.

## IMPORTANT NEGATIVE KNOWLEDGE

Do not:
- execute `E231D...` under the old authorization;
- restore `E70D...` merely to satisfy the old hash if the corrected artifact is the intended evidence-complete runner;
- infer that the correction is safe or evidence-complete solely because it fixes a provenance command;
- interpret this stop as Windows sensor failure;
- retry the old Codex execution channel.

## METHOD DELTA

A material runner correction creates a new identity boundary:

`artifact modification → new exact SHA → readiness/self-test against full evidence contract → fresh authorization → live execution`.

A narrower fix does not inherit authorization merely because its target repository and nominal purpose are unchanged.

## ROUTING DELTA

The next action is **not live execution**.

The immediate edge is:
`corrected runner E231D... → full readiness/evidence-contract self-test`.

Capability-fit actor: **DEVIN**, because the corrected runner is already present in its Windows execution workspace and the required action is artifact verification/readiness, not UI interaction.

Only after the corrected runner passes its full readiness contract should a fresh human authorization be issued for `E231D...`.

## CURRENT CANONICAL FRONTIER

The project-wide technical frontier remains:
`independent Windows process identity → existing IABV process observation helper`.

M0 remains a secondary UI-bound branch:
`human/UI-capable execution surface → ControlCenterViewModel.sendChat()`.

## STOP

No live execution.
No production changes.
No harness modification during readiness verification unless separately treated as a new artifact.
