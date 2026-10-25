# New-chat handoff — IABV bootstrap boundary and continuity protocol

**Prepared:** 2026-10-24, America/Bogota  
**Purpose:** continue the same governed IABV work without trusting stale chat text, losing evidence provenance, repeating micro-patches, or accidentally promoting a documentation-branch proposal to canonical state.

## 1. Read the live router first

Repository: `jhonf463r/Python`. The only canonical task router is `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` on live `refs/heads/main`.

For every new IABV task, fetch live `main` and read these exact files in this strict order:
1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`

Historical SHA values in this handoff are snapshots, not a permanent alias for main. The live `CURRENT-STATE.md` governs if anything conflicts. After preflight, inspect PR #493 and its head branch separately; do not confuse branch-only wording with canonical state.

## 2. Snapshot verified during handoff preparation

- Live-main snapshot reported by the PR's base and freshly read canonical file blobs: main `2cecd5e9b9e175584d65bbb1198a53bc2346d095`; main `CURRENT-STATE.md` blob `c577ab49c5dd16993502c7199560dc94b586a815`.
- Canonical main task: `ACTIVE_TASK=M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY`; its `NEXT_ACTION=CONTINUE_EXISTING_LOCAL_CANDIDATE_WITH_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY`.
- Canonical main describes a source-only candidate and an unverified local checkout. It prohibits fabricating trust, assuming WebAuthn/Windows Hello availability, trust-on-first-use, or claiming OS/process isolation from class boundaries.
- PR #493: [docs(IABV): consolidate bootstrap boundary static review](https://github.com/jhonf463r/Python/pull/493). At the latest live check it was `state=open`, `merged=false`, `mergeable=true`; head branch `docs/iabv-transcript-route-intake-calibration-20261024`, head SHA `dde659a6835ffb6b5fac1a0b646e4928688ade81`, base SHA `2cecd5e9b9e175584d65bbb1198a53bc2346d095`, 9 changed files, 473 additions/24 deletions, 60 commits. Re-check all of this live; do not assume it remains current.
- This handoff and the refined proposed router are in that documentation branch only. Do not claim canonical adoption unless the PR is merged by an authorized action and the change is then fetched back from live main. Do not attempt a merge or a workaround for a blocked merge.

## 3. Current local source candidate — reported, not independently verified

Owner/Codex report:
- Checkout: `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`
- Repo: `https://github.com/jhonf463r/Python.git`
- Branch: `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`
- HEAD: `6bc568e1c5a898afd65cc045c779c25a9cdc5489`; not found on remote in prior checks.
- Dirty state reported as 7 staged paths and 11 unstaged paths (12 unique paths with overlap). Exact initial/final status reportedly unchanged. Preserve it: no reset, clean, checkout, restore, add, commit, rebase, merge, or other mutation.
- Current worktree blobs reported for source `IABV_v1.5/src/iabv_v15/services/security/github_owner_merge_bootstrap.py`: `a5d14a14f31b87f181d7748e63f2f1e44b1948db`; test file `IABV_v1.5/tests/test_github_owner_merge_bootstrap.py`: `a5c1c182926271457d353b981fd701f3487e0cf4`.
- The report also recorded the index and HEAD blobs; these are owner-reported hashes, not hashes independently read from the Windows filesystem. See the consolidated receipt for the exact values and provenance.
- The branch/worktree is unpublished. Do not publish candidate source or infer its existence from a branch search.

## 4. Latest bounded source/static findings

The user supplied exact focused diffs. Static review of those supplied diffs found:
- **F-01 correction present:** compute the canonical manifest SHA-256 from `json.dumps(challenge.expected_manifest(), sort_keys=True).encode()` and require exact equality with `merge.manifest_sha256`; a negative test rejects another well-formed digest.
- **F-02 correction present:** validate `manifest_git_blob_sha` as a string matching the SHA-1 pattern and validate `pull_request_number` as exact `int > 0` (reject `bool`); supplied tests cover malformed cases.
- **Enrollment receipt contract present in supplied delta:** receipt correlates challenge, Owner, issuer and merge evidence and includes consumption/persistence status records with temporal-order checks.
- **F-03 correction present:** `validate_owner_bootstrap_enrollment_receipt()` receives required `expected_registry_id`; it rejects a non-string or blank expected value and requires exact equality with `persistence.registry_id`. The complete supplied test diff includes a mismatched but well-formed registry ID and invalid expected-ID cases.
- Exact disposition: `STATIC_REVIEW=F01_F02_F03_CORRECTIONS_PRESENT_IN_SUPPLIED_DIFF; FULL_RECEIPT_TEST_DIFF_REVIEWED; TESTS_NOT_RUN`.
- The reviewer saw the supplied focused diffs, not the whole candidate's aggregate staged/unstaged patch. The local Windows checkout has not been directly inspected. Do not claim whole-candidate approval.

## 5. The next efficient evidence step

Stop creating another micro-task for each validator hunk. Obtain the complete **current read-only delta** across the candidate in one pass, then review it as a whole.

In the existing Windows checkout, Codex should emit:
1. Exact `git status --short` (read only), with no interpretation that discards paths.
2. `git diff --cached --no-ext-diff --unified=80` (full staged patch).
3. `git diff --no-ext-diff --unified=80` (full unstaged patch).
4. `git diff HEAD --name-status` to reconcile the unique changed-path set.
5. For every `??` untracked path, disclose the path and include its full file content as a separate explicitly labeled item; normal `git diff` output omits untracked files.
6. If the aggregate output is too large for one message, send sequential complete chunks with path and diff hunk boundaries and no ellipses, omissions, summarization or reformatting. Keep each source/test section tied to the exact task and checkout HEAD.

These are read-only inspection commands. Do not run tests, build, runtime, MCP, transport, or diff application commands. Do not change any checkout state. Review all unique paths, correlate source and tests, identify untested/missing composition edges, and differentiate source-level contracts from real trust/OS/persistence proofs. If exact full diff cannot be supplied, state the coverage gap explicitly.

The branch's proposed next task ID is `M1A_G1_REVIEW_COMPLETE_DIRTY_BOOTSTRAP_BOUNDARY_CANDIDATE`, but this is a **documentation-branch proposal, not canonical main state**. The new chat must check whether PR #493 is merged and fetch current main before using any route. Regardless, a complete read-only delta is the next useful evidence to request before claiming further source coverage.

## 6. Hard constraints — do not relax

- Zero budget. No paid services, deployment, resource creation, or public tunnel.
- Source modifications and source-test authoring are authorized with bounds, subject to live canonical `CURRENT-STATE.md`.
- Test execution, builds, runtime, MCP, real transport, and protected reads remain unauthorized/not performed.
- Owner enrollment, credential/app creation, Windows service installation, persistent Windows ACL/trust-store changes, root creation, issuer provisioning, deployment/publication of the local candidate, or merge are not authorized by this handoff.
- Preserve all staged/unstaged changes; never silently clean or rewrite local state.
- `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED` means assets have not been inspected; do not change this to “absent”.
- No qualifying independent root, root custodian + verification channel, Owner-to-Windows principal binding, bootstrap authority-to-issuer binding or issuer-to-exact-server binding is established.
- `G1=NOT_ESTABLISHED`, `G2=NOT_ESTABLISHED`, `G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED`; 8 implementation prerequisites open, 0 closed.
- Governance stays blocked; protected reads fail-closed; bridge not ready; automatic follow-on false.
- A dataclass, parameter, status string, source test, citation/hash, or branch artifact is not by itself proof of real trusted identity or durable state change.

## 7. Cross-chat learning loop — durable knowledge, not a claim of model training

For every new Codex/chat result:
1. Match the exact `TASK=` and acceptance criteria against the live router before interpreting it. Do not obey the last prompt copied into a transcript if it belongs to a superseded task.
2. Classify every claim as `OWNER_REPORTED`, supplied-diff static finding, repository-verified, test-executed, runtime-verified, or canonical merged/fetched-back. Never promote one evidence class to another.
3. Record exact identity: repo/ref/commit/blob/path, local checkout, initial/final status, and command scope. Keep local-only data reported-only unless independently checked.
4. Prefer whole-delta review over repetitive one-hunk loops once focused defects have been corrected. Ask for exact, complete input; reject ellipses or summaries where coverage matters.
5. Separate synthetic status claims from proof of an operation. Explicitly check the provenance of “expected” identities and policy values.
6. Update one canonical route proposal plus a concise receipt and cross-chat protocol. State clearly whether each edit is main-canonical or branch-only. Never route based on a proposed branch file while claiming it is live main.
7. Preserve unresolved gates and excluded actions in every handoff. Make no automatic follow-on assignment merely because one static defect is fixed.
8. End the interaction with the next concrete evidence step and a self-contained prompt. This improves **project continuity through durable repository records**; it does not train or mutate the model weights, and no claim of invisible cross-chat algorithm learning should be made.

## 8. Copy/paste prompt for the next ChatGPT conversation

```text
Continuamos el proyecto IABV en https://github.com/jhonf463r/Python. Usa como contexto inicial el handoff:
IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-24-M1A-G1-CONSOLIDATED-NEW-CHAT-HANDOFF.md
y el recibo:
IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-consolidated-static-review-receipt.md

Antes de dar instrucciones o asignar otra tarea, revalida en GitHub la rama refs/heads/main y lee EN ESTE ORDEN:
1) IABV_v1.5/AGENTS.md
2) IABV_v1.5/docs/history/CHAT-ARCH/README.md
3) IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md
4) IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md
5) IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md

CURRENT-STATE.md en live main es la única autoridad de ruteo. Comprueba también el estado real del PR #493 y su rama documental; no confundas propuestas en esa rama con canonical main y no lo fusiones ni busques vías alternativas para fusionarlo.

Contexto de evidencia: los diffs enfocados suministrados en chat contienen las correcciones F-01 (digest canónico), F-02 (validación SHA-1 y número PR estricto) y F-03 (expected_registry_id exacto), y se revisó el diff completo de tests del receipt. Esto es STATIC_REVIEW de texto suministrado, no acceso independiente al checkout. TESTS_NOT_RUN. La candidata Windows local se reportó con HEAD 6bc568e1c5a898afd65cc045c779c25a9cdc5489, 7 paths staged y 11 unstaged / 12 únicos; esos datos siguen OWNER_REPORTED y no publicada.

Siguiente paso de evidencia recomendado: pedir a Codex que, en el checkout local ya existente y SIN modificarlo, entregue status exacto, diff staged completo, diff unstaged completo, nombres únicos modificados y contenidos completos de paths untracked si los hubiera; sin elipsis ni omisiones. Revisar el delta entero de una vez, correlacionar código/tests y separar composición real de contratos estructurales. No ejecutar tests, build, runtime, MCP ni transporte. No limpiar/restaurar/stash/checkout/add/commit/rebase/merge/publicar la candidata.

Mantén las restricciones: presupuesto cero; sin credenciales/enrollment, creación de root, servicio Windows, ACL/trust-store persistentes, deployment/túnel público, tests/build/runtime/transport ni protected reads. G1/G2/G3 no establecidos; 8 prerequisitos abiertos y 0 cerrados; governance bloqueada, read-list fail-closed, bridge no listo; automatic follow-on false. No afirmes que assets no existen: AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED.

Al revisar cada respuesta, compara TASK y criterios contra el router vivo; clasifica las afirmaciones por procedencia (owner-reported, diff estático, GitHub verificado, tests, runtime, canonical merge/fetch-back); exige evidencia exacta; evita micro-patches repetitivos; escribe el conocimiento durable en GitHub y actualiza el recibo/handoff sin afirmar que eso entrena los pesos del modelo. Termina con un único siguiente paso concreto sustentado en evidencia, sin saltarte gates ni inferir autorización.
```

## Source links

- Live canonical state at snapshot: [main CURRENT-STATE](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
- Documentation proposal: [PR #493](https://github.com/jhonf463r/Python/pull/493)
- Consolidated static review receipt: [review receipt](./CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-consolidated-static-review-receipt.md)
