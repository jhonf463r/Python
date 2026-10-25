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
- PR #493: [docs(IABV): consolidate bootstrap boundary static review](https://github.com/jhonf463r/Python/pull/493). Live pre-writeback check on 2026-10-24 (America/Bogota): `state=open`, `merged=false`, `mergeable=true`; head branch `docs/iabv-transcript-route-intake-calibration-20261024`, head SHA `cddeb24710dc5b394ed26ced5fb906e2a09f5f5d`, base SHA `2cecd5e9b9e175584d65bbb1198a53bc2346d095`, 10 changed files, 601 additions/24 deletions, 69 commits. This snapshot precedes the receipt/handoff commits that advance the PR head. Re-fetch PR metadata before treating any recorded SHA or count as current; do not merge this proposal.
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

## 5. Latest candidate-wide review report and next source task

The Owner supplied Codex's `TASK_RESULT=SOURCE_REVIEW_BUNDLE_ONLY` report. It describes a local review of the 12-path dirty candidate and reports no repo/index edits. The patch files were said to be exported outside the checkout:
- staged HEAD→index, 63,238 bytes, SHA-256 `d220b3c57325799e953a0c2534d7bcfa6088f5297b361855c23021f0097909b1`;
- unstaged index→worktree, 87,643 bytes, SHA-256 `59cb23aefa3205ccad22746f9d3afb7deaa1b604fc3e68eb510d9d23a332e4c6`.

They reside at a Windows-local `C:\Users\faber\AppData\Local\Temp\iabv-bootstrap-static-review-7de272ded2fa461ba0c97e272dfb4255\` path and were not attached as downloadable patch bytes here. Distinguish Codex's reported inspection from a direct independent review of those bytes. Main remains authoritative; the receipt records the current limitations/provenance.

The report says source wiring reaches both `read_repo_file` and `list_repo_directory`, with providers absent and fail-closed denial in the current composition. It also reports that the enrollment boundary remains interfaces/validators rather than a concrete issuer/enrollment producer. The full set of findings is in the [consolidated static-review receipt](./CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-consolidated-static-review-receipt.md).

**First actionable source defect: R-03, exact authorized-target binding.** The reported code verifies that `permit.canonical_target` is nonempty, but calls the read/list helper using the original `relative_path`, which is resolved independently. A future ALLOW decision could therefore describe a different target from the object the helper consumes. This is conditional on a positive path that is currently unavailable; do not enable that path.

Next proposed task: `M1A_G1_BIND_AUTHORIZED_CANONICAL_TARGET_TO_READ_OPERATION`. On the existing checkout, inspect the actual helper implementation, make the smallest source-only change that causes the operation to consume the exact target validated by the coordinator, and add focused source tests. If the existing abstractions cannot guarantee same-target identity, retain fail-closed denial and report that exact blocker. Preserve all preexisting staged and unstaged state, write all new modifications unstaged, and do not run tests/build/runtime/MCP/transport or perform credentials/root/enrollment/OS/ACL/trust-store/service/deployment actions. Do not publish or merge the candidate.

This next task is a bounded narrowing within the source implementation and source-test authoring scope recorded in live main; it does not alter the canonical route or authorize a positive read. After every task, refresh live main and read the five required files before further routing.

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
Continuamos el proyecto IABV en https://github.com/jhonf463r/Python. La documentación que sigue está en la rama propuesta `docs/iabv-transcript-route-intake-calibration-20261024`, dentro del PR #493, no en canonical main.

Handoff: https://github.com/jhonf463r/Python/blob/docs/iabv-transcript-route-intake-calibration-20261024/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-24-M1A-G1-CONSOLIDATED-NEW-CHAT-HANDOFF.md
Recibo: https://github.com/jhonf463r/Python/blob/docs/iabv-transcript-route-intake-calibration-20261024/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-consolidated-static-review-receipt.md

Antes de asignar cualquier trabajo, refresca `refs/heads/main` en GitHub y lee, en este orden estricto:
1) `IABV_v1.5/AGENTS.md`
2) `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3) `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
4) `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
5) `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`

Comprueba el estado vivo del PR #493. Nunca trates una propuesta del PR como canónica antes de que se integre por una acción autorizada y se verifique su presencia en main.

La última respuesta de Codex es `TASK_RESULT=SOURCE_REVIEW_BUNDLE_ONLY`. Reporta inspección local de 12 rutas; 7 estados staged y 11 unstaged con solapamiento; sin cambios de repositorio por la revisión; pruebas/build/runtime/MCP/transporte no ejecutados. Reporta parches completos fuera del checkout con SHA-256 staged `d220b3c57325799e953a0c2534d7bcfa6088f5297b361855c23021f0097909b1` y unstaged `59cb23aefa3205ccad22746f9d3afb7deaa1b604fc3e68eb510d9d23a332e4c6`. Los bytes están en una ruta local de Windows no adjunta al chat; distingue la revisión local reportada por Codex de cualquier revisión independiente de esos bytes.

Hallazgo prioritario reportado: `R-03`. El coordinador valida `permit.canonical_target`, pero el handler llama al helper con `relative_path` original, que el helper resuelve de nuevo. La autorización y el objeto operado pueden divergir en un futuro camino positivo. El wiring actual sigue fail-closed porque faltan los proveedores productivos; no habilites un ALLOW ni afirmes que se ha explotado.

Tarea acotada: `M1A_G1_BIND_AUTHORIZED_CANONICAL_TARGET_TO_READ_OPERATION`. En el checkout existente:
- preserva todas las modificaciones staged/unstaged; no uses reset, clean, checkout, restore, stash, add, commit, rebase ni merge;
- inspecciona la implementación del helper existente y reutiliza sus mecanismos; minimiza el alcance al handler/helper necesario y sus pruebas fuente;
- haz que el objeto operado sea exactamente el objeto cuya identidad/ruta se autorizó. No basta con comprobar que `canonical_target` no está vacío y luego re-resolver `relative_path`;
- añade pruebas fuente para destino distinto/reescrito y denegación antes del helper; escribir pruebas no significa ejecutarlas;
- si las abstracciones existentes no permiten asegurar la identidad del destino, conserva el fail-closed y devuelve el blocker preciso en vez de inventar una garantía;
- no ejecutes pruebas, build, runtime, MCP ni transporte. No crees root/credenciales/enrollment ni modifiques ACL, trust store, servicios o configuración persistente; no publiques ni integres el candidato.

Devuelve `TASK_RESULT=SOURCE_CANDIDATE_ONLY`, los diffs exactos de todas las rutas tocadas, hashes del árbol de trabajo/índice/HEAD, estado inicial/final y las pruebas marcadas `NOT_RUN`. No cierres G1/G2/G3: siguen `NOT_ESTABLISHED`, 8 prerrequisitos abiertos/0 cerrados, gobernanza bloqueada, lecturas protegidas fail-closed y presupuesto cero.

Al interpretar el resultado, clasifica cada afirmación por procedencia: reporte del Owner/Codex, diff exacto inspeccionado, repositorio verificado, tests ejecutados, runtime y adopción canónica. No confundas tests escritos con ejecutados, ni hashes reportados con bytes verificados. No repitas la revisión completa ni microparches F-01/F-02/F-03 salvo evidencia nueva de regresión.
```

## Source links

- Live canonical state at snapshot: [main CURRENT-STATE](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
- Documentation proposal: [PR #493](https://github.com/jhonf463r/Python/pull/493)
- Consolidated static review receipt: [review receipt](./CHAT-ARCH-2026-10-24-M1A-G1-bootstrap-boundary-consolidated-static-review-receipt.md)
