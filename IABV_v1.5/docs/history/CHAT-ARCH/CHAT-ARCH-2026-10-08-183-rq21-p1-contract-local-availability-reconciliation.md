# CHAT-ARCH-2026-10-08-183 — RQ21 P1 CONTRACT LOCAL-AVAILABILITY RECONCILIATION

## PURPOSE

Reconcile Codex's `STOP_READINESS_MISMATCH` before P1 execution. Determine whether the canonical contract is missing from the remote repository or only unavailable in Codex's local checkout, then route the minimum corrective action.

## PROVENANCE

- User-pasted Codex report time: approximately 2026-10-08 19:43 America/Bogota.
- Codex reported local root: `C:\Python`.
- Codex reported that it could not find `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-08-182-rq21-p1-load-only-owner-authorization-and-experiment-contract.md` by exact filename or patterns.
- Codex reported host `MSI`, Windows `10.0.26300.9550`, x64, PowerShell `7.6.5`, MEDIUM integrity `S-1-16-8192`.
- Codex says it did not run the diagnostic script, did not call `LoadLibraryExW` or `GetProcAddress`, did not load the DLL, and did not launch a candidate.
- Remote `main` read-back before this reconciliation: `384db92d380ddb49e5f437e2ada35b2af677a75d`.
- Pinned executable baseline remains `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`.

## INDEPENDENT CANONICAL READ-BACK

The exact contract **exists on remote GitHub `main`** at:

`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-08-182-rq21-p1-load-only-owner-authorization-and-experiment-contract.md`

URL:
https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-08-182-rq21-p1-load-only-owner-authorization-and-experiment-contract.md

Remote blob SHA:
`7184f7822920ee9068a21ab75c3564b10e32ea83`.

The record explicitly includes the Human Domain Owner authorization `P1_LOAD_ONLY = AUTORIZADO`, the exact target preconditions, the restricted `LoadLibraryExW` flags `0x00000900`, the two exact `GetProcAddress` names, evidence requirements and stop rules. The owner authorization is still valid for this bounded experiment; the previous run performed no load and consumed no execution authorization.

## ADJUDICATION

**Classification: LOCAL-CHECKOUT CONTRACT-AVAILABILITY BLOCKER; NOT A REMOTE CANONICAL ABSENCE.**

Codex correctly stopped because its first execution contract required that it read the frozen file and that file was not found in its local `C:\Python` tree. Our independent remote read-back establishes the canonical file exists at the expected repository path. Therefore the next action is to retrieve/read that exact remote canonical document through a read-only GitHub-capable route, without updating the IABV worktree or Git refs. If saved for verification, use a temporary location outside the repository and verify the file's Git blob SHA against `7184f7822920ee9068a21ab75c3564b10e32ea83` with `git hash-object`.

After the exact contract has been read and verified, Codex may resume the already-authorized bounded P1 probe in the same session, but only after it rechecks the target/file/token preconditions inside the fresh diagnostic process. If canonical access/hash validation fails, or any run-time readiness check mismatches, stop without loading.

No new authorization is granted by this record; it reaffirms routing under the existing explicit authorization and its scope. P1 has not yet executed.

## NEXT EDGE

`remote canonical contract exists → Codex reads/verifies exact remote contract → child-process readiness recheck → single restricted LoadLibraryExW → two GetProcAddress checks → raw evidence → independent reconciliation`.

Do not ask the user to manually copy the contract or repeat PowerShell token/hash/signature checks. Do not run another broad search across the local repo; the exact missing location was already checked. Do not fetch/pull/update the working tree, change Git refs, modify source, install tools, elevate, invoke either export, launch a candidate or run another experiment.

## DELTAS

### Knowledge Delta
The blocker is local contract availability, not remote canonical absence. Host identity and MEDIUM integrity were reported by Codex, but the load-test child preconditions remain untested because the diagnostic was not created or executed.

### Method Delta
When an actor reports a required canonical artifact missing locally, first distinguish remote source-of-truth existence from checkout materialization. Prefer exact remote read-back or a verified temporary copy over user-mediated manual copying or worktree mutation. A prior stop must be preserved as a no-execution result; it is not an API failure.

### Routing Delta
Codex remains the capability-fit actor. Next: read the exact remote contract URL, verify its Git blob SHA if materialized, then perform the preauthorized load-only probe if all frozen readiness gates pass. No other actor is required at this edge.

END OF RECORD
